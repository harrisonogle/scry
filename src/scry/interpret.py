"""The interpret stage: one model call per transition saying what the user did, from the two frames and the change
text → interpretations.jsonl. Whether something was entered or submitted is the model's judgement from the frames;
nothing measured says it. Every transition is interpreted: nothing is folded and none is skipped."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from scry.annotate.blocks import frame_block
from scry.changetext import render_change, render_change_line
from scry.config import Config, InterpretConfig, config_hash
from scry.costs import add_usage, estimate_cost
from scry.jsonl import sha256_obj, write_jsonl
from scry.prompts.interpret import SYSTEM, VERSION
from scry.providers import VlmProvider, get_provider, text_block
from scry.providers.batch import run_with_batches
from scry.run import Run
from scry.schemas import Change, Frame, FrameBoxes, Interpretation, ModelInterpretation, OutlineChapter

if TYPE_CHECKING:
    from scry.annotate.join import Labels

log = logging.getLogger(__name__)


def validate_citations(cited: list[str], allowed: list[str]) -> tuple[list[str], int]:
    """(the cited ids that were handed to the call, first occurrence only, in cited order; how many cited entries,
    repeats included, were not handed). Exact string equality; no re-prompt."""
    valid: list[str] = []
    for ref in cited:
        if ref in allowed and ref not in valid:
            valid.append(ref)
    return valid, sum(ref not in allowed for ref in cited)


def prompt_version(ic: InterpretConfig) -> str:
    """VERSION plus the image mode, so one mode never hits another's cache entries."""
    return VERSION + ("+full" if ic.images == "full" else f"+scaled{ic.scale:g}")


def context_text(chapter: OutlineChapter | None, previous: list[Change]) -> str:
    lines = []
    if chapter is not None:
        lines.append(f"Chapter: {chapter.title} — {chapter.gist}")
    if previous:
        lines += ["Preceding transitions:", *(render_change_line(p) for p in previous)]
    return "\n".join(lines) if lines else "No preceding context."


def build_blocks(c: Change, previous: list[Change], frames: dict[int, Frame], boxes: dict[int, FrameBoxes], labels: Labels | None,
                 run: Run, chapter: OutlineChapter | None, ic: InterpretConfig) -> tuple[list[dict], list[str], str]:
    """The content blocks of one call, the ids it may cite, and the text the call cache hashes with the two frames."""
    context = context_text(chapter, previous)
    change_text, ids = render_change(c, boxes, labels)
    scale = 1.0 if ic.images == "full" else ic.scale
    tail = ":" if ic.images == "full" else f", downscaled by {ic.scale:g}:"
    blocks = [text_block(context)]
    for name, f in (("a", frames[c.from_frame]), ("b", frames[c.to_frame])):
        blocks += [text_block(f"Frame {name} = frame {f.frame} (t={f.t_settled:.2f}s){tail}"), frame_block(run.root / f.png, scale)]
    blocks += [text_block("Changes:\n" + change_text), text_block("Return the JSON object.")]
    return blocks, ids, context + "\n" + change_text


async def _interpret_all(run: Run, cfg: Config, provider: VlmProvider) -> list[Interpretation]:
    frames = {f.frame: f for f in run.load_frames()}
    boxes = {fb.frame: fb for fb in run.load_boxes()}
    labels = run.load_labels()
    changes = run.load_changes()
    version = prompt_version(cfg.interpret)
    sem = asyncio.Semaphore(cfg.model.concurrency * 2)  # bounds the transitions in flight: two image payloads each

    async def one(i: int, c: Change) -> Interpretation:
        a, b = frames[c.from_frame], frames[c.to_frame]
        if not (run.root / a.png).exists() or not (run.root / b.png).exists():
            return Interpretation(id=c.id, error="missing_png")  # a call without its frames would be a text-only call
        async with sem:
            previous = changes[max(0, i - cfg.interpret.context_transitions):i]
            blocks, ids, hashed = build_blocks(c, previous, frames, boxes, labels, run, run.chapter_of(b.t_settled), cfg.interpret)
            res = await provider.complete(stage="interpret", system=SYSTEM, blocks=blocks, output_model=ModelInterpretation,
                                          effort=cfg.model.effort_interpret, prompt_version=version,
                                          input_hashes=[a.sha256, b.sha256, sha256_obj(hashed)])
        base = dict(id=c.id, usage=res.usage, model=provider.model, prompt_version=version)
        if res.parsed is None:
            return Interpretation(**base, error=res.error)
        p: ModelInterpretation = res.parsed
        citations, invalid = validate_citations(p.citations, ids)
        return Interpretation(**base, action=p.action, result=p.result, description=p.description, confidence=p.confidence,
                              entered_text=p.entered_text if p.entered_text and p.entered_text.strip() else None,
                              submitted=p.submitted, citations=citations, invalid_citations=invalid)

    return list(await asyncio.gather(*(one(i, c) for i, c in enumerate(changes))))


def run_interpret(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None:
    inputs = [run.changes, run.frames, run.boxes, run.annotations, run.outline]
    ch = config_hash(cfg, "model", "interpret") + prompt_version(cfg.interpret)
    if run.stage_up_to_date("interpret", inputs, ch):
        log.info("interpret up to date")
        return
    provider = provider or get_provider(cfg, run)
    records: list[Interpretation] = asyncio.run(run_with_batches(run, cfg, provider, _interpret_all))
    write_jsonl(run.interpretations, records)
    usage = add_usage({}, {})
    for r in records:
        add_usage(usage, r.usage)  # cache hits included: the cost is what a cold run would pay
    done = [r for r in records if r.error is None]
    run.stage_done("interpret", inputs, ch, transitions=len(records), interpreted=len(done), errors=len(records) - len(done),
                   invalid_citations=sum(r.invalid_citations for r in records),
                   entered=sum(r.entered_text is not None for r in records),
                   submitted={v: sum(r.submitted == v for r in records) for v in ("yes", "no", "unclear")},
                   images=cfg.interpret.images, labels=bool(run.load_annotations()), usage=usage,
                   cost_usd=estimate_cost(usage, provider.model, batch=cfg.model.mode == "batch"),  # at the price paid (L52)
                   model=provider.model, cache=getattr(provider, "stats", {}))
