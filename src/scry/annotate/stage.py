"""The annotate stage: one model call per frame that proposes labels for OCR boxes (containers, typed links,
optionally a second reading, a screen description) → annotations.jsonl. Labels are proposals: nothing here alters or
gates a measured record, and every request is built from measured records only, so no call depends on another.

An incremental call is the every-frame call with a shorter target list: the same system prompt, schema, images and
prompt version; in the user turn only the `Targets:` line differs, naming fewer boxes (the sentence that keeps the
description about the screen is in the shared system prompt, ledger L59). Which frames get a call and which boxes are
targets is `plan_calls`' answer, read from track's records alone; what the labels mean at a later frame is the join's
(`scry.annotate.join`)."""
from __future__ import annotations

import asyncio
import logging
from collections import Counter

from scry.annotate.blocks import build_blocks, input_hashes
from scry.annotate.output import output_model
from scry.annotate.proposal import to_proposal
from scry.annotate.repair import repair
from scry.annotate.targets import CallPlan, plan_calls
from scry.config import Config, config_hash
from scry.costs import add_usage, estimate_cost
from scry.jsonl import write_jsonl
from scry.overlay import draw_overlay
from scry.prompts.annotate import prompt_version, system_prompt
from scry.providers import VlmProvider, get_provider, is_transient
from scry.providers.batch import run_with_batches
from scry.run import Run
from scry.schemas import Annotation, Frame, FrameBoxes
from scry.textdiff import similarity
from scry.track.pixels import margin_px

log = logging.getLogger(__name__)
ARM, PANE = "A", False  # the referencing arm and the pane label are evaluation switches that have not landed


def mark_match(annotations: list[Annotation], frames: list[FrameBoxes], threshold: float = 0.8) -> tuple[int, int]:
    """(hits, total) over the texts of successful transcribing records: a text counts when it is not empty and names a
    box of its frame; it is a hit when it resembles that box's OCR text. A diagnostic (it caught unreadable overlay
    tags); no pipeline decision rests on it."""
    ocr = {(fb.frame, b.id): b.text for fb in frames for b in fb.boxes}
    hits = total = 0
    for a in annotations:
        if a.error is not None or a.texts is None:
            continue
        for t in a.texts:
            if t.text.strip() and (a.frame, t.box) in ocr:
                total += 1
                hits += similarity(ocr[(a.frame, t.box)], t.text) >= threshold
    return hits, total


async def _annotate_all(run: Run, cfg: Config, provider: VlmProvider, frames: dict[int, Frame], boxes: dict[int, FrameBoxes],
                        plans: list[CallPlan]) -> list[Annotation]:
    a = cfg.annotate
    version = prompt_version(ARM, a.transcribe, PANE, a.scale)
    system, model = system_prompt(ARM, a.transcribe, PANE), output_model(ARM, a.transcribe, PANE)
    sem = asyncio.Semaphore(cfg.model.concurrency * 2)  # bounds the frames in flight: image payloads are built inside it

    async def one(plan: CallPlan) -> Annotation:
        frame, fb = frames[plan.frame], boxes[plan.frame]
        base = dict(frame=plan.frame, targets=list(plan.targets), model=provider.model, prompt_version=version)
        async with sem:
            frame_png = run.root / frame.png
            if not frame_png.exists():
                return Annotation(**base, error="missing_png")
            overlay_png = run.overlays_dir / f"{plan.frame:05d}.png"
            clashes = draw_overlay(frame_png, fb.boxes, overlay_png, cfg.overlay, scale=a.scale)  # every box numbered
            blocks = build_blocks(frame, fb, plan, ARM, a.scale, frame_png, overlay_png)
            res = await provider.complete(stage="annotate", system=system, blocks=blocks, output_model=model,
                                          effort=cfg.model.effort_annotate, prompt_version=version,
                                          input_hashes=input_hashes(frame, overlay_png, blocks))
        if res.parsed is None:
            return Annotation(**base, label_clashes=clashes, usage=res.usage, error=res.error)
        proposal, converted = to_proposal(ARM, res.parsed, fb.boxes, (frame.width, frame.height),
                                          margin_px(fb.boxes, [], cfg.track.margin))
        fixed = repair(proposal, plan.targets, [b.id for b in fb.boxes])
        counts = Counter(converted) + Counter(fixed.counts)
        return Annotation(**base, containers=fixed.containers, assign=fixed.assign, links=fixed.links, texts=fixed.texts,
                          missed=fixed.missed, unassigned=fixed.unassigned, description=proposal.description,
                          repairs=sum(counts.values()), repair_counts=dict(counts), label_clashes=clashes, usage=res.usage)

    return list(await asyncio.gather(*(one(p) for p in plans)))


def run_annotate(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None:
    a = cfg.annotate
    inputs = [run.frames, run.boxes] + ([run.changes, run.lifetimes] if a.mode == "incremental" else [])
    version = prompt_version(ARM, a.transcribe, PANE, a.scale)
    ch = config_hash(cfg, "annotate", "model", "overlay", "track") + version
    frames = run.load_frames()
    if a.mode == "off":  # the "no annotation" base: no stale labels to read; the call cache keeps every paid answer
        run.annotations.unlink(missing_ok=True)
        run.stage_done("annotate", inputs, ch, skipped=True, frames=len(frames), calls=0, usage=add_usage({}, {}), cost_usd=0.0,
                       model=cfg.model.model)
        return
    last = run.manifest_read().get("stages", {}).get("annotate", {})
    if run.stage_up_to_date("annotate", inputs, ch) and run.annotations.exists() and last.get("transient_errors", 0) == 0:
        log.info("annotate up to date")
        return
    boxes = {fb.frame: fb for fb in run.load_boxes()}
    for f in frames:
        if f.frame not in boxes:
            raise ValueError(f"frame {f.frame} has no record in {run.boxes.name}: run `scry read` first")
    frame_boxes = [boxes[f.frame] for f in frames]
    changes, lifetimes = [], []
    if a.mode == "incremental":  # the call frames and the targets come from track's records
        for path in (run.changes, run.lifetimes):
            if not path.exists():
                raise ValueError(f"{path.name} is missing: run `scry track` first")
        changes, lifetimes = run.load_changes(), run.load_lifetimes()
    plans = plan_calls(frame_boxes, changes, lifetimes, a.mode)
    provider = provider or get_provider(cfg, run)

    async def stage_fn(run: Run, cfg: Config, provider: VlmProvider) -> list[Annotation]:
        return await _annotate_all(run, cfg, provider, {f.frame: f for f in frames}, boxes, plans)

    records: list[Annotation] = asyncio.run(run_with_batches(run, cfg, provider, stage_fn))
    records.sort(key=lambda r: r.frame)
    write_jsonl(run.annotations, records)

    usage: dict = add_usage({}, {})
    repair_counts: Counter[str] = Counter()
    for r in records:
        add_usage(usage, r.usage)  # cache hits included: the cost is what a cold run would pay
        repair_counts.update(r.repair_counts)
    failed = [r for r in records if r.error is not None]
    hits, total = mark_match(records, frame_boxes) if a.transcribe else (0, 0)
    cost = estimate_cost(usage, provider.model, batch=cfg.model.mode == "batch")  # one figure, at the price paid (L52)
    run.stage_done("annotate", inputs, ch, mode=a.mode, arm=ARM, transcribe=a.transcribe, prompt_version=version,
                   model=provider.model, frames=len(frames), calls=len(records), skipped_frames=len(frames) - len(records),
                   boxes=sum(len(boxes[r.frame].boxes) for r in records), targets=sum(len(r.targets) for r in records),
                   errors=len(failed), transient_errors=sum(is_transient(r.error) for r in failed),
                   failed_targets=sum(len(r.targets) for r in failed), repairs=sum(r.repairs for r in records),
                   repair_counts=dict(repair_counts), label_clashes=sum(r.label_clashes for r in records),
                   mark_match={"hits": hits, "total": total} if a.transcribe else None, usage=usage,
                   usage_lost=getattr(provider, "stats", {}).get("usage_lost", 0), cache=getattr(provider, "stats", {}),
                   cost_usd=cost, cost_per_frame_usd=round(cost / len(frames), 5) if frames else None,
                   cost_per_call_usd=round(cost / len(records), 5) if records else None)
