"""A transition's change records as text: one line per record, each with the box ids a reader may cite. `interpret`,
`summarize` and `ask` all read a change through this module, so the model and the agent get the same account. The text
says that text appeared, changed, moved or was removed at a place, with before and after; who or what changed it is
not known here and is never stated. Pure functions, no I/O."""
from __future__ import annotations

from typing import TYPE_CHECKING

from scry.schemas import BoxChange, Change, FrameBoxes, parse_box_ref

if TYPE_CHECKING:
    from scry.annotate.join import Labels

PAIR_KINDS = ("reread", "appended", "truncated", "changed")  # records with a before and an after
LINE_RECORDS = 3  # pair records quoted in a one-line summary
LINE_TEXT_CHARS = 80  # characters of each quoted text in a one-line summary
LINK_ROLES = {"run": "part of a wrapped text", "member": "table cell", "header": "table heading"}


def text_of(ref: str, boxes: dict[int, FrameBoxes]) -> str:
    """The OCR text of the box a ref names. A miss means the run directory is inconsistent."""
    frame, box_id = parse_box_ref(ref)
    fb = boxes.get(frame)
    box = next((b for b in fb.boxes if b.id == box_id), None) if fb is not None else None
    if box is None:
        raise ValueError(f"no box {ref} in boxes.jsonl")
    return box.text


def box_label(ref: str, labels: Labels | None, boxes: dict[int, FrameBoxes]) -> str:
    """Where a model placed the box: its container, its pane and its role in a link, the parts that exist joined with
    ", "; "" without labels."""
    label = labels.box(ref) if labels is not None else None
    if label is None:
        return ""
    parts = []
    if label.container is not None:
        c = label.container
        parts.append(" ".join(x for x in (c.app or c.name, c.kind) if x))
    if label.pane:
        parts.append(label.pane)
    if label.link is not None:
        link = label.link
        if link.role == "value":
            parts.append('value of "' + " ".join(text_of(r, boxes) for r in link.key) + '"')
        elif link.role == "key":
            parts.append('label of "' + " ".join(text_of(r, boxes) for r in link.value) + '"')
        else:
            parts.append(LINK_ROLES[link.role])
    return ", ".join(parts)


def _runs(record: BoxChange, op: str) -> str:
    return "".join(text for o, text in record.char_diff if o == op)


def _body(r: BoxChange) -> str:
    before = f'"{r.before.text}"' if r.before is not None else ""
    after = f'"{r.after.text}"' if r.after is not None else ""
    if r.kind == "appended":
        return f'{before} → appended "{_runs(r, "+")}"; now {after}'
    if r.kind == "truncated":
        return f'{before} → truncated, removed "{_runs(r, "-")}"; now {after}'
    if r.kind == "changed":
        return f"at this place {before} was replaced by {after}"
    if r.kind == "reread":
        return f"{before} re-read as {after} (same text)"
    if r.kind == "appeared":
        return f"appeared {after}"
    return f"removed {before}"


def render_change(c: Change, boxes: dict[int, FrameBoxes], labels: Labels | None) -> tuple[str, list[str]]:
    """The change text and the citable ids: exactly the refs printed inside square brackets, in order of first
    appearance. Nothing is capped: every listed id is citable."""
    out = [f"Transition {c.id}: frame {c.from_frame} → frame {c.to_frame}, t={c.t[0]:.2f}–{c.t[1]:.2f}s."]
    if c.pixels is None:
        out.append("Pixels: no comparison is available for this pair.")
    else:
        out.append(f"Pixels changed: {100 * c.pixels.changed_fraction:.2f}% of the screen; changed areas: {c.pixels.components}.")
    ids: list[str] = []
    if c.records:
        out.append("Text changes:")
    for r in c.records:
        refs = [t.box for t in (r.after, r.before) if t is not None]
        ids += [ref for ref in refs if ref not in ids]
        label = box_label(refs[0], labels, boxes)
        suffix = f"; continues {r.continues.split('/')[0]}" if r.continues else ""
        suffix += " [area was animating]" if r.in_churn else ""
        out.append(f"[{', '.join(refs)}] " + (f"{label}: " if label else "") + _body(r) + suffix)
        for ref in refs:
            read = labels.box(ref) if labels is not None else None
            if read is not None and read.agree is False and read.vlm:
                out.append(f'    model reads {ref}: "{read.vlm}"')
    if c.moved:
        out.append(f"Texts that only moved: {len(c.moved)}.")
    if c.same_place > 0:
        out.append(f"Boxes with a visual change over unchanged text: {c.same_place}.")
    if c.pixels is not None and c.pixels.textless > 0:
        out.append(f"Changed areas without text: {c.pixels.textless}.")
    if c.reverts is not None:
        out.append(f"Undoes {100 * c.reverts.share:.0f}% of {c.reverts.of}'s change after {c.reverts.hold_s:.1f} s.")
    if c.kind == "unsettled":
        out.append("One of these frames was captured while the screen was still changing.")
    if not c.records:
        out.append("No text change was recorded; look for a change that is not text.")
    return "\n".join(out), ids


def _cut(s: str) -> str:
    return s if len(s) <= LINE_TEXT_CHARS else s[:LINE_TEXT_CHARS - 1] + "…"


def render_change_line(c: Change) -> str:
    """One mechanical line per change: it exists before any model call."""
    pairs = [r for r in c.records if r.kind in PAIR_KINDS]
    parts = [f'{r.kind} "{_cut(r.after.text)}"' for r in pairs[:LINE_RECORDS]]
    if len(pairs) > LINE_RECORDS:
        parts.append(f"+{len(pairs) - LINE_RECORDS} more text changes")
    counts = (("appeared", sum(r.kind == "appeared" for r in c.records)), ("removed", sum(r.kind == "removed" for r in c.records)),
              ("moved", len(c.moved)))
    parts += [f"{name} {n}" for name, n in counts if n > 0]
    if c.reverts is not None:
        parts.append(f"undoes {c.reverts.of}")
    return f"{c.id} [f{c.from_frame}→f{c.to_frame}, {c.t[0]:.1f}–{c.t[1]:.1f}s] " + ("; ".join(parts) or "no text change")
