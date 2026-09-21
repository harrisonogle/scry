from __future__ import annotations

import asyncio
import base64
import io
import logging
from pathlib import Path

from PIL import Image

from scry.config import Config, config_hash
from scry.jsonl import sha256_file, write_jsonl
from scry.overlay import scale_image
from scry.prompts import stage2c
from scry.providers import get_provider, image_block, text_block
from scry.providers.base import VlmProvider
from scry.run import Run
from scry.schemas import (OcrFrame, PerceptionRecord, Stage1Record, VlmPerception, VlmPerceptionGroupOnly,
                          perception_from_group_only)

log = logging.getLogger(__name__)


def prompt_version(coords: bool, transcribe: bool = True, scale: float = 1.0) -> str:
    return (stage2c.VERSION + ("+coords" if coords else "") + ("" if transcribe else "+grouponly")
            + ("" if scale == 1.0 else f"+s{scale:g}"))  # scaled runs never hit full-resolution cache entries


def system_prompt(transcribe: bool) -> str:
    return stage2c.SYSTEM if transcribe else stage2c.SYSTEM_GROUP_ONLY


def marks_text(ocr: OcrFrame, coords: bool, scale: float = 1.0, frame_size: tuple[int, int] = (0, 0)) -> str:
    ids = [ln.id for ln in ocr.lines]
    if not ids:
        return "Marks present: none."
    if not coords:
        return f"Marks present: {', '.join(ids)}."
    boxes = "; ".join(f"{ln.id}: {ln.bbox[0]},{ln.bbox[1]},{ln.bbox[2]},{ln.bbox[3]}" for ln in ocr.lines)
    space = ("pixels in Image 1" if scale == 1.0 else  # the boxes stay in the original frame's pixels when the images shrink
             f"pixels of the original {frame_size[0]}x{frame_size[1]} frame; the images are scaled by {scale:g}")
    return (f"Marks present, as id: x0,y0,x1,y1 ({space}, top-left origin, x1 and y1 exclusive), in top-to-bottom "
            f"order: {boxes}. Use these boxes together with Image 2 to tell which number belongs to which line.")


def frame_block(frame_png: Path, scale: float) -> dict:
    """The clean frame as an image block, downscaled in memory to the overlay's size when scale < 1 (never written)."""
    if scale == 1.0:
        return image_block(frame_png)
    buf = io.BytesIO()
    scale_image(Image.open(frame_png).convert("RGB"), scale).save(buf, format="PNG", compress_level=1)
    data = base64.standard_b64encode(buf.getvalue()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}


def build_blocks(rec: Stage1Record, ocr: OcrFrame, frame_png: Path, overlay_png: Path, coords: bool = False,
                 scale: float = 1.0) -> list[dict]:
    animating = [ln.id for ln in ocr.lines if ln.in_churn]
    blocks = [
        text_block(f"Image 1 (clean frame {rec.frame}, t={rec.t_settled:.2f}s):"), frame_block(frame_png, scale),
        text_block("Image 2 (same frame with numbered boxes):"), image_block(overlay_png),
        text_block(marks_text(ocr, coords, scale, (rec.width, rec.height))),
    ]
    if animating:
        blocks.append(text_block(f"Marks inside animating regions (low confidence): {', '.join(animating)}."))
    if not rec.settled:
        blocks.append(text_block("This frame was captured while the screen was still changing (not settled)."))
    blocks.append(text_block("Return the JSON object."))
    return blocks


def repair(out: VlmPerception, mark_ids: list[str]) -> tuple[VlmPerception, int]:
    """§8.3: validation by repair, never by abort. Returns the repaired output and the number of repairs.
    Rules: unknown or already-placed marks are dropped; a row whose marks were all dropped is removed together with its
    text; rows cut by the rows/vlm_lines length repair release their marks to unassigned_line_ids; parents naming unknown
    regions or closing a cycle become null; a focused_region naming no region becomes null; every mark ends up exactly once."""
    known = set(mark_ids)
    region_ids = {r.id for r in out.regions}
    repairs = 0
    seen: set[str] = set()
    for r in out.regions:
        new_rows: list[list[str]] = []
        new_lines: list[str] = []
        for k, row in enumerate(r.rows):
            kept = [m for m in row if m in known and m not in seen]
            repairs += len(row) - len(kept)
            seen.update(kept)
            if row and not kept:
                continue
            new_rows.append(kept)
            if k < len(r.vlm_lines):
                new_lines.append(r.vlm_lines[k])
        if len(new_lines) != len(new_rows):
            repairs += 1
            n = min(len(new_lines), len(new_rows))
            for row in new_rows[n:]:
                seen.difference_update(row)
            new_rows, new_lines = new_rows[:n], new_lines[:n]
        r.rows, r.vlm_lines = new_rows, new_lines
        if r.parent is not None and r.parent not in region_ids:
            r.parent = None
            repairs += 1
    by_id = {r.id: r for r in out.regions}
    for r in out.regions:
        seen_ids, p = {r.id}, r.parent
        while p is not None and p in by_id and p not in seen_ids:
            seen_ids.add(p)
            p = by_id[p].parent
        if p is not None and p in seen_ids:  # r's parent chain closes a cycle
            r.parent = None
            repairs += 1
    unassigned = [m for m in out.unassigned_line_ids if m in known and m not in seen]
    seen.update(unassigned)
    for m in mark_ids:
        if m not in seen:
            unassigned.append(m)
            repairs += 1
    out.unassigned_line_ids = unassigned
    if out.focused_region is not None and out.focused_region not in region_ids:
        out.focused_region = None
        repairs += 1
    return out, repairs


async def _perceive_all(run: Run, cfg: Config, provider: VlmProvider) -> list[PerceptionRecord]:
    s1 = {r.frame: r for r in run.load_stage1()}
    clashes = run.manifest_read().get("overlay_clashes", {})
    sem = asyncio.Semaphore(cfg.model.concurrency * 2)  # bound the fan-out: image payloads are built lazily
    coords, transcribe, scale = cfg.model.stage2c_mark_coords, cfg.model.stage2c_transcribe, cfg.overlay.scale
    version = prompt_version(coords, transcribe, scale)

    async def one(of: OcrFrame) -> PerceptionRecord:
        async with sem:
            rec = s1[of.frame]
            frame_png = run.root / rec.png
            overlay_png = run.overlays_dir / f"{of.frame:05d}.png"
            blocks = build_blocks(rec, of, frame_png, overlay_png, coords=coords, scale=scale)
            res = await provider.complete(stage="stage2c", system=system_prompt(transcribe), blocks=blocks,
                                          output_model=VlmPerception if transcribe else VlmPerceptionGroupOnly,
                                          effort=cfg.model.effort_stage2c, prompt_version=version,
                                          input_hashes=[rec.sha256, sha256_file(overlay_png)])
        parsed = res.parsed if transcribe or res.parsed is None else perception_from_group_only(res.parsed)
        out, repairs = (repair(parsed, [ln.id for ln in of.lines]) if parsed is not None else (None, 0))
        return PerceptionRecord(frame=of.frame, model=provider.model, prompt_version=version, output=out,
                                error=res.error, usage=res.usage, repairs=repairs, label_clashes=int(clashes.get(str(of.frame), 0)))

    return list(await asyncio.gather(*(one(of) for of in run.load_ocr())))


async def _run_with_batches(run: Run, cfg: Config, provider: VlmProvider, stage_fn) -> list:
    """One event loop for the whole stage; in batch mode collect cache misses, run the batches, then re-run (all hits)."""
    if cfg.model.mode == "batch" and hasattr(provider, "collecting"):
        provider.collecting = True
        await stage_fn(run, cfg, provider)
        provider.collecting = False
        await provider.run_batches(run)
    return await stage_fn(run, cfg, provider)


def run_perceive(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None:
    inputs = [run.ocr]
    ch = config_hash(cfg, "model", "overlay") + prompt_version(cfg.model.stage2c_mark_coords, cfg.model.stage2c_transcribe, cfg.overlay.scale)
    if run.stage_up_to_date("perceive", inputs, ch):
        log.info("perceive up to date")
        return
    provider = provider or get_provider(cfg, run)
    records = asyncio.run(_run_with_batches(run, cfg, provider, _perceive_all))
    records.sort(key=lambda r: r.frame)
    write_jsonl(run.perception, records)
    usage = {k: sum(r.usage.get(k, 0) for r in records) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens")}
    run.stage_done("perceive", inputs, ch, frames=len(records), errors=sum(r.error is not None for r in records),
                   repairs=sum(r.repairs for r in records), usage=usage, model=provider.model, cache=getattr(provider, "stats", {}))
