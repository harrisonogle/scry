from __future__ import annotations

import asyncio
import base64
import io
import logging
from pathlib import Path

from PIL import Image

from scry.config import Config, Stage5Config, config_hash
from scry.jsonl import sha256_obj, write_jsonl
from scry.overlay import scale_image
from scry.prompts import stage5
from scry.providers import get_provider, image_block, text_block
from scry.providers.base import VlmProvider
from scry.run import Run
from scry.schemas import BBox, FrameRecord, Interpretation, OutlineChapter, Transition, VlmInterpretation, VlmRefs

log = logging.getLogger(__name__)


def prompt_version(s5: Stage5Config | None = None) -> str:
    """stage5.VERSION plus the image mode and its parameters, so one mode never hits another mode's cache entries;
    "full" keeps the bare version (its calls are unchanged)."""
    if s5 is None or s5.images == "full":
        return stage5.VERSION
    if s5.images == "text":
        return stage5.VERSION + "+text"
    if s5.images == "scaled":
        return stage5.VERSION + f"+scaled{s5.scale:g}"
    return stage5.VERSION + f"+crops{s5.scale:g}p{s5.crop_pad}m{s5.crop_max}f{s5.crop_max_fraction:g}"


def image_mode(t: Transition, s5: Stage5Config) -> str:
    """The mode a transition is actually sent in: "crops" needs changed-pixel components covering at most
    crop_max_fraction of the screen, otherwise the transition falls back to "scaled"."""
    if s5.images == "crops" and (t.pixels is None or not t.pixels.components or t.pixels.changed_fraction > s5.crop_max_fraction):
        return "scaled"
    return s5.images


def _union(a: BBox, b: BBox) -> BBox:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _overlaps(a: BBox, b: BBox) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _area(b: BBox) -> int:
    return (b[2] - b[0]) * (b[3] - b[1])


def _merge_overlapping(boxes: list[BBox]) -> list[BBox]:
    boxes = list(boxes)
    merged = True
    while merged:
        merged = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                if _overlaps(boxes[i], boxes[j]):
                    boxes[i] = _union(boxes[i], boxes[j])
                    del boxes[j]
                    merged = True
                    break
            if merged:
                break
    return boxes


def crop_boxes(components: list[BBox], width: int, height: int, pad: int, cap: int) -> list[BBox]:
    """The crop rectangles for one frame: every changed-pixel component grown by `pad` and clamped to the frame,
    overlapping rectangles merged, and while more than `cap` remain the pair whose union adds the least area merged —
    so every changed pixel stays inside some crop. Reading order (top to bottom, then left to right)."""
    boxes = [(max(0, x0 - pad), max(0, y0 - pad), min(width, x1 + pad), min(height, y1 + pad)) for x0, y0, x1, y1 in components]
    boxes = _merge_overlapping([b for b in boxes if b[2] > b[0] and b[3] > b[1]])
    while len(boxes) > cap:
        i, j = min(((i, j) for i in range(len(boxes)) for j in range(i + 1, len(boxes))),
                   key=lambda ij: _area(_union(boxes[ij[0]], boxes[ij[1]])) - _area(boxes[ij[0]]) - _area(boxes[ij[1]]))
        boxes[i] = _union(boxes[i], boxes[j])
        del boxes[j]
        boxes = _merge_overlapping(boxes)  # the union may now overlap a third rectangle
    return sorted(boxes, key=lambda b: (b[1], b[0]))


def _png_block(img: Image.Image) -> dict:
    """An in-memory PIL image as an image block (never written to disk)."""
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=1)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.standard_b64encode(buf.getvalue()).decode()}}


def _open(png: Path) -> Image.Image:
    return Image.open(png).convert("RGB")


def _box_text(b: BBox) -> str:
    return f"{b[0]},{b[1]},{b[2]},{b[3]}"


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
    if not out:
        out.append("No text changes were computed; look for non-textual change.")
    if t.pixels is not None:
        out.append(f"Pixels changed: {100 * t.pixels.changed_fraction:.2f}% of the screen in {len(t.pixels.components)} areas")
    for e in t.events:
        if e.type == "typed":
            out.append(f'Coalesced event: typed "{e.text}" (line now: "{e.line}") over frames {e.frames[0]}→{e.frames[1]}')
        elif e.type == "output_appended":
            out.append(f"Coalesced event: {e.lines} output lines appended over frames {e.frames[0]}→{e.frames[1]}")
    if t.kind == "unsettled":
        out.append("One of these frames was captured while the screen was still changing.")
    return "\n".join(out)


def build_blocks(t: Transition, frames: dict[int, FrameRecord], run: Run, chapter: OutlineChapter | None, previous: list[Transition],
                 s5: Stage5Config | None = None) -> list[dict]:
    """The content blocks of one Stage 5 call (§12). The image mode (`[stage5] images`) decides what sits between the
    context and the computed changes: full = both frames (and the transient frame) at native resolution; scaled = the
    same frames downscaled by `scale`; crops = the after-frame downscaled for context plus full-resolution crops of the
    changed areas, each from both frames (a transient frame is sent downscaled with a full-resolution crop of its region);
    text = no images."""
    s5 = s5 or Stage5Config()
    mode = image_mode(t, s5)
    a, b = frames[t.from_frame], frames[t.to_frame]
    mid = frames[t.transient.frame] if t.transient is not None else None
    ctx = []
    if chapter is not None:
        ctx.append(f"Global outline chapter for this pair: {chapter.title} — {chapter.gist}")
    if previous:
        ctx.append("Preceding transitions:\n" + "\n".join(render_transition_line(p, frames) for p in previous))
    blocks = [text_block("\n".join(ctx) if ctx else "No preceding context.")]
    note = f"Transient frame {mid.frame}: region '{t.transient.name}' appeared for {t.transient.hold_s:.1f}s between the two frames" if mid else ""
    if mode == "full":
        blocks += [text_block(f"Frame {a.frame} (t={a.t_settled:.2f}s):"), image_block(run.root / a.png)]
        if mid is not None:
            blocks += [text_block(note + ":"), image_block(run.root / mid.png)]
        blocks += [text_block(f"Frame {b.frame} (t={b.t_settled:.2f}s):"), image_block(run.root / b.png)]
    elif mode == "scaled":
        tail = f", downscaled by {s5.scale:g}:"
        blocks += [text_block(f"Frame {a.frame} (t={a.t_settled:.2f}s){tail}"), _png_block(scale_image(_open(run.root / a.png), s5.scale))]
        if mid is not None:
            blocks += [text_block(note + tail), _png_block(scale_image(_open(run.root / mid.png), s5.scale))]
        blocks += [text_block(f"Frame {b.frame} (t={b.t_settled:.2f}s){tail}"), _png_block(scale_image(_open(run.root / b.png), s5.scale))]
    elif mode == "crops":
        boxes = crop_boxes(t.pixels.components, b.width, b.height, s5.crop_pad, s5.crop_max)
        ia, ib = _open(run.root / a.png), _open(run.root / b.png)
        blocks += [text_block(f"Frame {b.frame} (t={b.t_settled:.2f}s), the whole screen downscaled by {s5.scale:g} for context:"),
                   _png_block(scale_image(ib, s5.scale))]
        if mid is not None:
            im = _open(run.root / mid.png)
            blocks += [text_block(note + f", downscaled by {s5.scale:g}:"), _png_block(scale_image(im, s5.scale))]
            reg = mid.region(t.transient.region)
            if reg is not None and reg.bbox is not None:
                rb = crop_boxes([reg.bbox], mid.width, mid.height, s5.crop_pad, 1)[0]
                blocks += [text_block(f"Region '{t.transient.name}' of frame {mid.frame} at full resolution ({_box_text(rb)} of the {mid.width}x{mid.height} frame):"),
                           _png_block(im.crop(rb))]
        blocks.append(text_block(f"Between frame {a.frame} (t={a.t_settled:.2f}s) and frame {b.frame} the pixels changed only inside the "
                                 f"{len(boxes)} area(s) below, shown at full resolution as x0,y0,x1,y1 of the {b.width}x{b.height} frame, "
                                 f"each first from frame {a.frame} (before) and then from frame {b.frame} (after):"))
        for k, box in enumerate(boxes, 1):
            blocks += [text_block(f"Area {k} ({_box_text(box)}) in frame {a.frame} (before):"), _png_block(ia.crop(box)),
                       text_block(f"Area {k} in frame {b.frame} (after):"), _png_block(ib.crop(box))]
    else:  # text
        blocks.append(text_block(f"Frame {a.frame} (t={a.t_settled:.2f}s) and frame {b.frame} (t={b.t_settled:.2f}s): no screenshots are "
                                 "attached for this transition, so interpret from the computed changes alone."))
        if mid is not None:
            blocks.append(text_block(note + " (not shown)."))
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
    sem = asyncio.Semaphore(cfg.model.concurrency * 2)  # bound the fan-out: up to three base64 PNGs per request
    version = prompt_version(cfg.stage5)

    async def one(i: int, t: Transition) -> Interpretation:
        if t.kind == "trivial":
            return Interpretation(id=t.id, error="trivial")
        async with sem:
            chapter = run.chapter_of(frames[t.to_frame].t_settled)
            blocks = build_blocks(t, frames, run, chapter, ts[max(0, i - 3):i], cfg.stage5)
            res = await provider.complete(stage="stage5", system=stage5.SYSTEM, blocks=blocks, output_model=VlmInterpretation,
                                          effort=cfg.model.effort_stage5, prompt_version=version,
                                          input_hashes=[frames[t.from_frame].sha256, frames[t.to_frame].sha256, sha256_obj(t.model_dump())])
        if res.parsed is None:
            return Interpretation(id=t.id, error=res.error, model=provider.model, prompt_version=version)
        p: VlmInterpretation = res.parsed
        scope = [frames[t.from_frame], frames[t.to_frame]] + ([frames[t.transient.frame]] if t.transient else [])
        valid, bad = validate_refs(p.refs.lines, scope)
        return Interpretation(id=t.id, action=p.action, result=p.result, description=p.description, confidence=p.confidence,
                              refs=VlmRefs(lines=valid), invalid_refs=bad, model=provider.model, prompt_version=version)

    return list(await asyncio.gather(*(one(i, t) for i, t in enumerate(ts))))


def run_interpret(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None:
    inputs = [run.transitions, run.frames]
    ch = config_hash(cfg, "model", "stage5") + prompt_version(cfg.stage5)
    if run.stage_up_to_date("interpret", inputs, ch):
        log.info("interpret up to date")
        return
    provider = provider or get_provider(cfg, run)
    from scry.perceive import _run_with_batches

    records = asyncio.run(_run_with_batches(run, cfg, provider, _interpret_all))
    write_jsonl(run.interpretations, records)
    fallbacks = sum(1 for t in run.load_transitions() if t.kind != "trivial" and image_mode(t, cfg.stage5) != cfg.stage5.images)
    run.stage_done("interpret", inputs, ch, transitions=len(records), errors=sum(r.error not in (None, "trivial") for r in records),
                   invalid_refs=sum(r.invalid_refs for r in records), model=provider.model, images=cfg.stage5.images, image_fallbacks=fallbacks,
                   usage=getattr(provider, "usage_by_stage", {}).get("stage5", {}), cache=getattr(provider, "stats", {}))
