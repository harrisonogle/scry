from __future__ import annotations

import asyncio
import logging

from scry.config import Config, config_hash
from scry.jsonl import sha256_obj, write_jsonl
from scry.prompts import stage5
from scry.providers import get_provider, image_block, text_block
from scry.providers.base import VlmProvider
from scry.run import Run
from scry.schemas import FrameRecord, Interpretation, OutlineChapter, Transition, VlmInterpretation, VlmRefs

log = logging.getLogger(__name__)


def _region_name(f: FrameRecord, rid: str) -> str:
    if rid == "r0":
        return "unassigned lines"
    r = f.region(rid)
    return f"{r.app}: {r.name}" if r else rid


def render_transition_line(t: Transition, frames: dict[int, FrameRecord]) -> str:
    b = frames[t.to_frame]
    parts = []
    for e in t.events:
        name = _region_name(b, e.region)
        if e.type == "typed":
            parts.append(f'{name}: typed "{e.text}"')
        elif e.type == "output_appended":
            parts.append(f"{name}: {e.lines} lines appended")
    if not parts:
        n = sum(len(rd.ops) for rd in t.computed_diff.values())
        parts.append(f"{n} text changes" + (f"; appeared: {', '.join(_region_name(b, r) for r in t.regions.appeared)}" if t.regions.appeared else ""))
    return f"{t.id} [f{t.from_frame}→f{t.to_frame}, {t.t[0]:.1f}–{t.t[1]:.1f}s] " + "; ".join(parts)


def render_diff(t: Transition, frames: dict[int, FrameRecord]) -> str:
    a, b = frames[t.from_frame], frames[t.to_frame]
    out = []
    if t.regions.appeared:
        out.append("Regions that appeared in frame b: " + ", ".join(_region_name(b, r) for r in t.regions.appeared))
    if t.regions.disappeared:
        out.append("Regions that disappeared after frame a: " + ", ".join(_region_name(a, r) for r in t.regions.disappeared))
    for rid, rd in t.computed_diff.items():  # keyed by unit (§11.1); indices are positions in the unit's line list
        reg = b.region(rid)
        head = _region_name(b, rid)
        if reg is not None and reg.layout_conf < 0.5:
            head += " (grouping uncertain; text may belong to an adjacent window)"
        out.append(f"Region {head}:")
        lines = b.unit_lines(rid)
        for o in rd.ops:
            flag = " [uncertain reading]" if o.uncertain else ""
            churn = " [region was animating]" if o.in_churn else ""
            pane = ""
            if o.pane:
                pr = (a if o.op == "delete" else b).region(o.pane)
                pane = f" [pane: {pr.name if pr else o.pane}]"
            if o.op == "modify":
                out.append(f'  modify: "{o.old}" -> "{o.new}"{flag}{churn}{pane}')
            elif o.op == "insert":
                out.append(f'  insert: "{o.new}"{flag}{churn}{pane}')
            else:
                out.append(f'  delete: "{o.old}"{flag}{churn}{pane}')
            src = None
            if o.new_index is not None and reg is not None and o.new_index < len(lines):
                src = lines[o.new_index]
            if src is not None and src.agree is False and src.ocr and src.vlm:
                out.append(f"    readings disagree — OCR: {src.ocr} | VLM: {src.vlm}")
    for e in t.events:
        if e.type == "typed":
            out.append(f'Coalesced event: typed "{e.text}" (line now: "{e.line}") over frames {e.frames[0]}→{e.frames[1]}')
        elif e.type == "output_appended":
            out.append(f"Coalesced event: {e.lines} output lines appended over frames {e.frames[0]}→{e.frames[1]}")
    if t.kind == "unsettled":
        out.append("One of these frames was captured while the screen was still changing.")
    return "\n".join(out) if out else "No text changes were computed; look for non-textual change."


def build_blocks(t: Transition, frames: dict[int, FrameRecord], run: Run, chapter: OutlineChapter | None, previous: list[Transition]) -> list[dict]:
    a, b = frames[t.from_frame], frames[t.to_frame]
    ctx = []
    if chapter is not None:
        ctx.append(f"Global outline chapter for this pair: {chapter.title} — {chapter.gist}")
    if previous:
        ctx.append("Preceding transitions:\n" + "\n".join(render_transition_line(p, frames) for p in previous))
    blocks = [text_block("\n".join(ctx) if ctx else "No preceding context.")]
    blocks += [text_block(f"Frame {a.frame} (t={a.t_settled:.2f}s):"), image_block(run.root / a.png)]
    if t.transient is not None:
        mid = frames[t.transient.frame]
        blocks += [text_block(f"Transient frame {mid.frame}: region '{t.transient.name}' appeared for {t.transient.hold_s:.1f}s between the two frames:"),
                   image_block(run.root / mid.png)]
    blocks += [text_block(f"Frame {b.frame} (t={b.t_settled:.2f}s):"), image_block(run.root / b.png)]
    blocks.append(text_block("Computed changes:\n" + render_diff(t, frames)))
    blocks.append(text_block("Return the JSON object."))
    return blocks


def validate_refs(refs: list[str], frames: list[FrameRecord]) -> tuple[list[str], int]:
    ids = {f.frame: f.line_ids() for f in frames}
    valid, bad = [], 0
    for r in refs:
        try:
            fr, lid = r.split(":", 1)
            if int(fr) in ids and lid in ids[int(fr)]:
                valid.append(r)
                continue
        except ValueError:
            pass
        bad += 1
    return valid, bad


async def _interpret_all(run: Run, cfg: Config, provider: VlmProvider) -> list[Interpretation]:
    frames_list = run.load_frames()
    frames = {f.frame: f for f in frames_list}
    ts = run.load_transitions()
    sem = asyncio.Semaphore(cfg.model.concurrency * 2)  # bound the fan-out: three base64 PNGs per request

    async def one(i: int, t: Transition) -> Interpretation:
        if t.kind == "trivial":
            return Interpretation(id=t.id, error="trivial")
        async with sem:
            chapter = run.chapter_of(frames[t.to_frame].t_settled)
            blocks = build_blocks(t, frames, run, chapter, ts[max(0, i - 3):i])
            res = await provider.complete(stage="stage5", system=stage5.SYSTEM, blocks=blocks, output_model=VlmInterpretation,
                                          effort=cfg.model.effort_stage5, prompt_version=stage5.VERSION,
                                          input_hashes=[frames[t.from_frame].sha256, frames[t.to_frame].sha256, sha256_obj(t.model_dump())])
        if res.parsed is None:
            return Interpretation(id=t.id, error=res.error, model=provider.model, prompt_version=stage5.VERSION)
        p: VlmInterpretation = res.parsed
        scope = [frames[t.from_frame], frames[t.to_frame]] + ([frames[t.transient.frame]] if t.transient else [])
        valid, bad = validate_refs(p.refs.lines, scope)
        return Interpretation(id=t.id, action=p.action, result=p.result, description=p.description, confidence=p.confidence,
                              refs=VlmRefs(lines=valid), invalid_refs=bad, model=provider.model, prompt_version=stage5.VERSION)

    return list(await asyncio.gather(*(one(i, t) for i, t in enumerate(ts))))


def run_interpret(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None:
    inputs = [run.transitions, run.frames]
    ch = config_hash(cfg, "model") + stage5.VERSION
    if run.stage_up_to_date("interpret", inputs, ch):
        log.info("interpret up to date")
        return
    provider = provider or get_provider(cfg, run)
    from scry.perceive import _run_with_batches

    records = asyncio.run(_run_with_batches(run, cfg, provider, _interpret_all))
    write_jsonl(run.interpretations, records)
    run.stage_done("interpret", inputs, ch, transitions=len(records), errors=sum(r.error not in (None, "trivial") for r in records),
                   invalid_refs=sum(r.invalid_refs for r in records), model=provider.model,
                   usage=getattr(provider, "usage_by_stage", {}).get("stage5", {}), cache=getattr(provider, "stats", {}))
