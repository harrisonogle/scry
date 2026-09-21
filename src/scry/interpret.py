"""The interpret stage: one model call per transition saying what the user did, from the two frames and the change
text → interpretations.jsonl. Whether something was entered or submitted is the model's judgement from the frames;
nothing measured says it. Every transition is interpreted: nothing is folded and none is skipped."""
from __future__ import annotations

from typing import TYPE_CHECKING

from scry.annotate.blocks import frame_block
from scry.changetext import render_change, render_change_line
from scry.config import InterpretConfig
from scry.prompts.interpret import VERSION
from scry.providers import text_block
from scry.run import Run
from scry.schemas import Change, Frame, FrameBoxes, OutlineChapter

if TYPE_CHECKING:
    from scry.annotate.join import Labels


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
