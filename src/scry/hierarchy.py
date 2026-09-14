from __future__ import annotations

import asyncio
import json
import logging
from typing import Sequence

from scry.config import Config, HierarchyConfig, config_hash
from scry.interpret import render_transition_line
from scry.jsonl import sha256_obj, write_jsonl
from scry.prompts import stage6
from scry.providers import get_provider, text_block
from scry.providers.base import VlmProvider
from scry.run import Run
from scry.schemas import FrameRecord, HierNode, Interpretation, SegmentStart, Transition, VlmBoundaries, VlmElaboration

log = logging.getLogger(__name__)


# ---------- pure helpers ----------
def repair_boundaries(segments: list[SegmentStart], ids: list[str]) -> list[tuple[int, str]]:
    pos = {i: k for k, i in enumerate(ids)}
    starts: dict[int, str] = {}
    for s in segments:
        k = pos.get(s.start_id)
        if k is not None and k not in starts:
            starts[k] = s.label
    if 0 not in starts:
        starts[0] = "segment 1"
    return sorted(starts.items())


def fallback_segments(n: int, size: int) -> list[tuple[int, str]]:
    return [(k, f"segment {k // size + 1}") for k in range(0, n, size)]


def window_ranges(n: int, window: int, overlap: int) -> list[tuple[int, int]]:
    if n <= window:
        return [(0, n)]
    out, start = [], 0
    while True:
        end = min(start + window, n)
        out.append((start, end))
        if end == n:
            return out
        start = end - overlap


def merge_window_boundaries(per_window: list[tuple[int, int, list[tuple[int, str]]]], n: int, overlap: int) -> list[tuple[int, str]]:
    found: dict[int, tuple[str, int]] = {}
    for wi, (ws, we, bounds) in enumerate(per_window):
        prev_overlap_end = ws + overlap if wi > 0 else ws
        next_overlap_start = we - overlap if wi < len(per_window) - 1 else we
        for s, label in bounds:
            in_overlap = s < prev_overlap_end or s >= next_overlap_start
            if not in_overlap:
                found[s] = (label, 2)
            else:
                strong = (s - ws >= 25) and (we - s >= 25)
                cur = found.get(s)
                votes = (cur[1] if cur else 0) + (1 if not strong else 2)
                found[s] = (label if not cur else cur[0], votes)
    out = [(s, lab) for s, (lab, v) in found.items() if v >= 2]
    if not out or out[0][0] != 0:
        out.append((0, "segment 1"))
    return sorted(set(out))


def propagate(children: Sequence[HierNode | Transition]) -> tuple[tuple[int, int], tuple[float, float]]:
    first, last = children[0], children[-1]
    f0 = first.from_frame if isinstance(first, Transition) else first.frames[0]
    f1 = last.to_frame if isinstance(last, Transition) else last.frames[1]
    return (f0, f1), (first.t[0], last.t[1])


# ---------- rendering ----------
def _item_line(item: HierNode | Transition, frames: dict[int, FrameRecord], interps: dict[str, Interpretation]) -> str:
    if isinstance(item, Transition):
        line = render_transition_line(item, frames)
        ip = interps.get(item.id)
        if ip and ip.action:
            line += f" — {ip.action}"
        return line
    return f"{item.id} [f{item.frames[0]}→f{item.frames[1]}, {item.t[0]:.1f}–{item.t[1]:.1f}s] {item.label}"


def _item_full(item: HierNode | Transition, frames: dict[int, FrameRecord], interps: dict[str, Interpretation]) -> str:
    if isinstance(item, Transition):
        ip = interps.get(item.id)
        parts = [render_transition_line(item, frames)]
        if ip and ip.action:
            parts.append(f"  action: {ip.action}\n  result: {ip.result}")
        return "\n".join(parts)
    return f"{item.id} {item.label}\n  {item.description}"


def _state_line(f: FrameRecord) -> str:
    names = ", ".join(f"{r.app}: {r.name}" for r in f.regions if r.parent is None)
    foc = f.region(f.focused_region).name if f.focused_region and f.region(f.focused_region) else "unknown"
    return f"frame {f.frame} (t={f.t_settled:.1f}s): windows [{names}]; focused: {foc}"


# ---------- level builder ----------
async def _boundaries(provider: VlmProvider, cfg: Config, level: str, lines: list[str], suggestion: str | None,
                      retry: bool = False) -> tuple[list[SegmentStart] | None, str | None]:
    text = "\n".join(lines)
    if suggestion:
        text += "\n\nSuggested boundaries from a coarse outline (reconcile against the items; the items win):\n" + suggestion
    if retry:  # a changed request, or the call cache would hand back the failed answer (§13.1)
        text += "\n\n(Retry: the previous answer contained no valid start ids. Use the ids exactly as listed above.)"
    res = await provider.complete(stage=f"stage6-boundary-{level}", system=stage6.BOUNDARY_SYSTEM, blocks=[text_block(text)],
                                  output_model=VlmBoundaries, effort=cfg.model.effort_stage6, prompt_version=stage6.VERSION,
                                  input_hashes=[sha256_obj(text), "retry" if retry else "first"])
    return (res.parsed.segments if res.parsed else None), res.error


async def _elaborate(provider: VlmProvider, cfg: Config, level: str, seg_id: str, items_text: str, start_state: str, end_state: str) -> VlmElaboration:
    text = f"Segment {seg_id}\nStart state: {start_state}\nEnd state: {end_state}\n\nItems:\n{items_text}"
    res = await provider.complete(stage=f"stage6-elaborate-{level}", system=stage6.ELABORATE_SYSTEM, blocks=[text_block(text)],
                                  output_model=VlmElaboration, effort=cfg.model.effort_stage6, prompt_version=stage6.VERSION,
                                  input_hashes=[sha256_obj(text)])
    if res.parsed is None:
        return VlmElaboration(label=seg_id, description=f"(elaboration failed: {res.error})", refs=[])
    return res.parsed


async def build_level(provider: VlmProvider, cfg: Config, level: str, prefix: str, items: list, frames: dict[int, FrameRecord],
                      interps: dict[str, Interpretation], suggestion: str | None, fallback_size: int,
                      chapter_starts: list[tuple[int, str]] | None = None) -> list[HierNode]:
    hc: HierarchyConfig = cfg.hierarchy
    ids = [it.id for it in items]
    lines = [_item_line(it, frames, interps) for it in items]
    per_window = []
    seg_conf = "high"
    for ws, we in window_ranges(len(items), hc.window, hc.overlap):
        segs, err = await _boundaries(provider, cfg, level, lines[ws:we], suggestion)
        if segs is None or len(segs) == 0:
            segs, err = await _boundaries(provider, cfg, level, lines[ws:we], suggestion, retry=True)  # one re-prompt
        if segs is None or len(segs) == 0:
            log.warning("boundary call failed for %s window %d-%d: %s; using fallback", level, ws, we, err)
            if chapter_starts:  # §13.1: Stage 0 chapter boundaries when the outline exists
                fb = [(k - ws, lab) for k, lab in chapter_starts if ws <= k < we]
            else:
                fb = fallback_segments(we - ws, fallback_size)
            if not fb or fb[0][0] != 0:
                fb = [(0, "segment 1")] + fb
            bounds = [(ws + k, lab) for k, lab in fb]
            seg_conf = "low"
        else:
            bounds = [(ws + k, lab) for k, lab in repair_boundaries(segs, ids[ws:we])]
        per_window.append((ws, we, bounds))
    bounds = merge_window_boundaries(per_window, len(items), hc.overlap) if len(per_window) > 1 else per_window[0][2]
    starts = [s for s, _ in bounds] + [len(items)]
    nodes: list[HierNode] = []
    tasks = []
    for k, (s, label) in enumerate(bounds):
        e = starts[k + 1]
        chunk = items[s:e]
        frames_rng, t_rng = propagate(chunk)
        items_text = "\n".join(_item_full(it, frames, interps) for it in chunk)
        if len(chunk) > 80:  # map-reduce within the segment (§13.2)
            parts = [chunk[i:i + 60] for i in range(0, len(chunk), 60)]
            summaries = await asyncio.gather(*(_elaborate(provider, cfg, level, f"{prefix}{k + 1} part {p + 1}",
                                                          "\n".join(_item_full(it, frames, interps) for it in part),
                                                          _state_line(frames[part[0].from_frame if isinstance(part[0], Transition) else part[0].frames[0]]),
                                                          _state_line(frames[part[-1].to_frame if isinstance(part[-1], Transition) else part[-1].frames[1]]))
                                               for p, part in enumerate(parts)))
            items_text = "\n".join(f"part {p + 1}: {s_.description}" for p, s_ in enumerate(summaries))
        tasks.append(_elaborate(provider, cfg, level, f"{prefix}{k + 1}", items_text, _state_line(frames[frames_rng[0]]), _state_line(frames[frames_rng[1]])))
        nodes.append(HierNode(id=f"{prefix}{k + 1}", level=level, children=(chunk[0].id, chunk[-1].id), frames=frames_rng, t=t_rng,
                              label=label, description="", segmentation_conf=seg_conf))
    elabs = await asyncio.gather(*tasks)
    for k, (node, el) in enumerate(zip(nodes, elabs)):
        child_ids = {it.id for it in items[starts[k]:starts[k + 1]]}
        node.label = el.label or node.label
        node.description = el.description
        node.refs = [r for r in el.refs if r in child_ids]
    return nodes


async def _hierarchy(run: Run, cfg: Config, provider: VlmProvider) -> tuple[list[HierNode], list[HierNode], HierNode]:
    frames = {f.frame: f for f in run.load_frames()}
    interps = run.load_interpretations()
    ts = [t for t in run.load_transitions() if t.kind != "trivial"]
    steps = await build_level(provider, cfg, "step", "S", ts, frames, interps, None, cfg.hierarchy.fallback_step_transitions)
    outline = run.load_outline()
    suggestion = "\n".join(f"{c.start_s:.0f}s–{c.end_s:.0f}s: {c.title}" for c in outline) if outline else None
    chapter_starts = None
    if outline:  # map chapter start times to the first step starting at or after them (§13.1 fallback)
        idx = sorted({k for k in (next((k for k, st in enumerate(steps) if st.t[0] >= c.start_s), None) for c in outline) if k is not None})
        chapter_starts = [(k, f"chapter {i + 1}") for i, k in enumerate(idx)] or None
    sections = await build_level(provider, cfg, "section", "C", steps, frames, interps, suggestion, cfg.hierarchy.fallback_section_steps, chapter_starts)
    frames_rng, t_rng = propagate(sections)
    el = await _elaborate(provider, cfg, "video", "video", "\n".join(_item_full(s, frames, interps) for s in sections),
                          _state_line(frames[frames_rng[0]]), _state_line(frames[frames_rng[1]]))
    video = HierNode(id="V", level="video", children=(sections[0].id, sections[-1].id), frames=frames_rng, t=t_rng,
                     label=el.label, description=el.description, refs=[r for r in el.refs if r in {s.id for s in sections}])
    return steps, sections, video


def run_hierarchy(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None:
    inputs = [run.transitions, run.interpretations, run.frames]
    ch = config_hash(cfg, "model", "hierarchy") + stage6.VERSION
    if run.stage_up_to_date("hierarchy", inputs, ch):
        log.info("hierarchy up to date")
        return
    if not [t for t in run.load_transitions() if t.kind != "trivial"]:
        log.warning("no non-trivial transitions; skipping hierarchy")
        return
    provider = provider or get_provider(cfg, run)
    steps, sections, video = asyncio.run(_hierarchy(run, cfg, provider))
    write_jsonl(run.steps, steps)
    write_jsonl(run.sections, sections)
    run.video.write_text(video.model_dump_json(indent=2))
    usage: dict = {}
    for k, u in getattr(provider, "usage_by_stage", {}).items():
        if k.startswith("stage6"):
            for kk, v in u.items():
                usage[kk] = usage.get(kk, 0) + v
    run.stage_done("hierarchy", inputs, ch, steps=len(steps), sections=len(sections),
                   low_conf=sum(n.segmentation_conf == "low" for n in steps + sections), usage=usage, model=provider.model,
                   cache=getattr(provider, "stats", {}))
