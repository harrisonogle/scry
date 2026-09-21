"""The summarize stage: steps over the transitions, sections over the steps, one summary of the video → steps.jsonl,
sections.jsonl, video.json. Two passes per level: a boundary call over one-line items, then one elaboration call per
segment. Every transition is an item. Ends, frame ranges and time ranges are derived in code, never by the model; that
something was submitted comes only from an interpretation, never from a duration."""
from __future__ import annotations

import asyncio
import inspect
import logging
from typing import TYPE_CHECKING, Sequence

from scry.changetext import PAIR_KINDS, render_change_line
from scry.config import Config, config_hash
from scry.costs import add_usage, estimate_cost
from scry.jsonl import sha256_obj, write_jsonl
from scry.prompts.summarize import BOUNDARY_SYSTEM, ELABORATE_SYSTEM, VERSION
from scry.providers import VlmProvider, get_provider, text_block
from scry.run import Run
from scry.schemas import Change, Frame, HierNode, Interpretation, ModelBoundaries, ModelElaboration, SegmentStart

if TYPE_CHECKING:
    from scry.annotate.join import Labels

log = logging.getLogger(__name__)

SEGMENT_MAX_ITEMS = 80  # children; a longer segment is first summarised in parts
SEGMENT_PART_ITEMS = 60  # children per part
OVERLAP_EDGE = 25  # items; a boundary this far from both edges of a window gets that window's full vote


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
                strong = (s - ws >= OVERLAP_EDGE) and (we - s >= OVERLAP_EDGE)
                cur = found.get(s)
                votes = (cur[1] if cur else 0) + (1 if not strong else 2)
                found[s] = (label if not cur else cur[0], votes)
    out = [(s, lab) for s, (lab, v) in found.items() if v >= 2]
    if not out or out[0][0] != 0:
        out.append((0, "segment 1"))
    return sorted(set(out))


def propagate(children: Sequence[HierNode | Change]) -> tuple[tuple[int, int], tuple[float, float]]:
    """The frame range and time range of a run of children, decided by the child's type: frame 0 is a frame."""
    first, last = children[0], children[-1]
    f0 = first.from_frame if isinstance(first, Change) else first.frames[0]
    f1 = last.to_frame if isinstance(last, Change) else last.frames[1]
    return (f0, f1), (first.t[0], last.t[1])


# ---------- rendering ----------
def item_line(item: HierNode | Change, interps: dict[str, Interpretation]) -> str:
    if isinstance(item, HierNode):
        return f"{item.id} [f{item.frames[0]}→f{item.frames[1]}, {item.t[0]:.1f}–{item.t[1]:.1f}s] {item.label}"
    line = render_change_line(item)
    ip = interps.get(item.id)
    if ip is not None and ip.action:
        line += f" — {ip.action}"
        if ip.entered_text is not None:
            line += f' [entered "{ip.entered_text}", submitted: {ip.submitted}]'
        elif ip.submitted == "yes":
            line += " [submitted: yes]"
    return line


def item_full(item: HierNode | Change, interps: dict[str, Interpretation]) -> str:
    if isinstance(item, HierNode):
        return f"{item.id} {item.label}\n  {item.description}"
    parts = [render_change_line(item)]
    ip = interps.get(item.id)
    if ip is not None and ip.action:
        parts += [f"  action: {ip.action}", f"  result: {ip.result}"]
        if ip.entered_text is not None or ip.submitted == "yes":
            entered = f'"{ip.entered_text}"' if ip.entered_text is not None else "null"
            parts.append(f"  entered: {entered}; submitted: {ip.submitted}")
    # appeared and removed texts are not listed: a page load would put a whole screen into one item
    parts += [f'  text: "{r.before.text}" → "{r.after.text}"' for r in item.records if r.kind in PAIR_KINDS]
    return "\n".join(parts)


def state_line(frame: Frame, labels: Labels | None) -> str:
    head = f"frame {frame.frame} (t={frame.t_settled:.1f}s)"
    containers = labels.frame(frame.frame).containers if labels is not None else []
    return head + (f": windows [{', '.join(f'{c.app}: {c.name}' for c in containers)}]" if containers else "")


# ---------- level builder ----------
async def _complete(provider: VlmProvider, meter: dict, **kw):
    res = await provider.complete(**kw)
    add_usage(meter["usage"], res.usage)  # cache hits included: the cost is what a cold run would pay
    meter["calls"] += 1
    return res


async def _boundaries(provider: VlmProvider, cfg: Config, level: str, lines: list[str], suggestion: str | None, meter: dict,
                      retry: bool = False) -> tuple[list[SegmentStart] | None, str | None]:
    text = "\n".join(lines)
    if suggestion:
        text += "\n\nSuggested boundaries from a coarse outline (reconcile against the items; the items win):\n" + suggestion
    if retry:  # a changed request, or the call cache would hand back the failed answer
        text += "\n\n(Retry: the previous answer contained no valid start ids. Use the ids exactly as listed above.)"
    res = await _complete(provider, meter, stage=f"summarize-boundary-{level}", system=BOUNDARY_SYSTEM, blocks=[text_block(text)],
                          output_model=ModelBoundaries, effort=cfg.model.effort_summarize, prompt_version=VERSION,
                          input_hashes=[sha256_obj(text), "retry" if retry else "first"])
    return (res.parsed.segments if res.parsed else None), res.error


async def _elaborate(provider: VlmProvider, cfg: Config, level: str, seg_id: str, items_text: str, start_state: str, end_state: str,
                     meter: dict) -> ModelElaboration:
    text = f"Segment {seg_id}\nStart state: {start_state}\nEnd state: {end_state}\n\nItems:\n{items_text}"
    res = await _complete(provider, meter, stage=f"summarize-elaborate-{level}", system=ELABORATE_SYSTEM, blocks=[text_block(text)],
                          output_model=ModelElaboration, effort=cfg.model.effort_summarize, prompt_version=VERSION,
                          input_hashes=[sha256_obj(text)])
    if res.parsed is None:
        return ModelElaboration(label=seg_id, description=f"(elaboration failed: {res.error})", refs=[])
    return res.parsed


def _apply(node: HierNode, el: ModelElaboration, child_ids: list[str], meter: dict) -> None:
    """The elaboration onto its node: refs outside the node's children are dropped and counted."""
    node.label = el.label or node.label
    node.description = el.description
    node.refs = [r for r in el.refs if r in child_ids]
    meter["invalid_refs"] += len(el.refs) - len(node.refs)


async def build_level(provider: VlmProvider, cfg: Config, level: str, prefix: str, items: list, frames: dict[int, Frame],
                      interps: dict[str, Interpretation], labels: Labels | None, suggestion: str | None, fallback_size: int,
                      chapter_starts: list[tuple[int, str]] | None, meter: dict) -> list[HierNode]:
    sc = cfg.summarize
    ids = [it.id for it in items]
    lines = [item_line(it, interps) for it in items]
    per_window = []
    seg_conf = "high"
    for ws, we in window_ranges(len(items), sc.window, sc.overlap):
        segs, err = await _boundaries(provider, cfg, level, lines[ws:we], suggestion, meter)
        if not segs:
            segs, err = await _boundaries(provider, cfg, level, lines[ws:we], suggestion, meter, retry=True)  # one re-prompt
        if not segs:
            log.warning("boundary call failed for %s window %d-%d: %s; using fallback", level, ws, we, err)
            if chapter_starts:  # the outline's chapters, when it exists
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
    bounds = merge_window_boundaries(per_window, len(items), sc.overlap) if len(per_window) > 1 else per_window[0][2]
    starts = [s for s, _ in bounds] + [len(items)]

    def states(chunk: list) -> tuple[str, str]:
        (f0, f1), _ = propagate(chunk)
        return state_line(frames[f0], labels), state_line(frames[f1], labels)

    nodes: list[HierNode] = []
    tasks = []
    for k, (s, label) in enumerate(bounds):
        chunk = items[s:starts[k + 1]]
        node_id = f"{prefix}{k + 1}"
        frames_rng, t_rng = propagate(chunk)
        items_text = "\n".join(item_full(it, interps) for it in chunk)
        if len(chunk) > SEGMENT_MAX_ITEMS:  # map-reduce within the segment
            parts = [chunk[i:i + SEGMENT_PART_ITEMS] for i in range(0, len(chunk), SEGMENT_PART_ITEMS)]
            summaries = await asyncio.gather(*(_elaborate(provider, cfg, level, f"{node_id} part {p + 1}",
                                                          "\n".join(item_full(it, interps) for it in part), *states(part), meter)
                                               for p, part in enumerate(parts)))
            items_text = "\n".join(f"part {p + 1}: {s_.description}" for p, s_ in enumerate(summaries))
        tasks.append(_elaborate(provider, cfg, level, node_id, items_text, *states(chunk), meter))
        nodes.append(HierNode(id=node_id, level=level, children=(chunk[0].id, chunk[-1].id), frames=frames_rng, t=t_rng,
                              label=label, description="", segmentation_conf=seg_conf))
    for k, el in enumerate(await asyncio.gather(*tasks)):
        _apply(nodes[k], el, ids[starts[k]:starts[k + 1]], meter)
    return nodes


async def _summarize(run: Run, cfg: Config, provider: VlmProvider, changes: list[Change],
                     meter: dict) -> tuple[list[HierNode], list[HierNode], HierNode]:
    frames = {f.frame: f for f in run.load_frames()}
    interps = run.load_interpretations()
    labels = run.load_labels()
    sc = cfg.summarize
    steps = await build_level(provider, cfg, "step", "S", changes, frames, interps, labels, None, sc.fallback_step_transitions, None, meter)
    outline = run.load_outline()
    suggestion = "\n".join(f"{c.start_s:.0f}s–{c.end_s:.0f}s: {c.title}" for c in outline) if outline else None
    chapter_starts = None
    if outline:  # each chapter's start mapped to the first step starting at or after it (the fallback of a failed boundary call)
        idx = sorted({k for k in (next((k for k, st in enumerate(steps) if st.t[0] >= c.start_s), None) for c in outline) if k is not None})
        chapter_starts = [(k, f"chapter {i + 1}") for i, k in enumerate(idx)] or None
    sections = await build_level(provider, cfg, "section", "C", steps, frames, interps, labels, suggestion, sc.fallback_section_steps,
                                 chapter_starts, meter)
    frames_rng, t_rng = propagate(sections)
    el = await _elaborate(provider, cfg, "video", "V", "\n".join(item_full(s, interps) for s in sections),
                          state_line(frames[frames_rng[0]], labels), state_line(frames[frames_rng[1]], labels), meter)
    video = HierNode(id="V", level="video", children=(sections[0].id, sections[-1].id), frames=frames_rng, t=t_rng, label="",
                     description="")
    _apply(video, el, [s.id for s in sections], meter)
    return steps, sections, video


def run_summarize(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None:
    inputs = [run.changes, run.interpretations, run.frames, run.annotations, run.outline]
    ch = config_hash(cfg, "model", "summarize") + VERSION
    if run.stage_up_to_date("summarize", inputs, ch):
        log.info("summarize up to date")
        return
    changes = run.load_changes()
    if not changes:
        log.warning("no transitions; nothing to summarize")
        return
    provider = provider or get_provider(cfg, run)
    meter = {"usage": add_usage({}, {}), "calls": 0, "invalid_refs": 0}

    async def stage() -> tuple[list[HierNode], list[HierNode], HierNode]:
        # The calls depend on one another level by level, so this stage never uses the batch path; like a batched
        # stage it closes the provider's client inside the loop that used it.
        try:
            return await _summarize(run, cfg, provider, changes, meter)
        finally:
            close = getattr(getattr(provider, "client", None), "close", None)
            closing = close() if close is not None else None
            if inspect.isawaitable(closing):
                await closing

    steps, sections, video = asyncio.run(stage())
    write_jsonl(run.steps, steps)
    write_jsonl(run.sections, sections)
    run.video.write_text(video.model_dump_json(indent=2))
    run.stage_done("summarize", inputs, ch, steps=len(steps), sections=len(sections),
                   low_conf=sum(n.segmentation_conf == "low" for n in steps + sections), invalid_refs=meter["invalid_refs"],
                   calls=meter["calls"], usage=meter["usage"], cost_usd=estimate_cost(meter["usage"], provider.model),
                   model=provider.model, cache=getattr(provider, "stats", {}))
