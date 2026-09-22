"""From the model's answer, whatever the referencing arm, to one arm-independent proposal (plan 2, D1). Under
reference = "coords" the answer names boxes by their rectangles; each is matched back to a box id here, and repair,
records, join and everything downstream see today's proposal by id."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from pydantic import BaseModel

from scry.schemas import Assign, Box, Container, Link, PairLink, RecordLink, RunLink, TextReading


@dataclass
class Proposal:
    containers: list[Container]
    assign: list[Assign]
    unassigned: list[str]
    links: list[Link]  # runs, then pairs, then records, each in returned order
    texts: list[TextReading] | None  # None: the answer class has no texts (group-only)
    missed: list[tuple[str, str | None]]  # text, container id
    description: str


def _overlap(a: Sequence[int], b: Sequence[int]) -> int:
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def _centre_distance(a: Sequence[int], b: Sequence[int]) -> float:
    return math.hypot((a[0] + a[2]) - (b[0] + b[2]), (a[1] + a[3]) - (b[1] + b[3])) / 2


def snap_rect(rect: Sequence[int], boxes: list[Box], margin_px: int) -> str | None:
    """The box a returned rectangle names: the box whose rectangle it equals; otherwise the box it overlaps most, if it
    overlaps any; otherwise the nearest box by centre distance, if that is at most the track margin in pixels; otherwise
    None (the reference is dropped and counted). Ties go to reading order; a list that is not four numbers names nothing."""
    if len(rect) != 4 or not boxes:
        return None
    rect = tuple(rect)
    for b in boxes:
        if b.bbox == rect:
            return b.id
    area, best = max((_overlap(rect, b.bbox), -i) for i, b in enumerate(boxes))
    if area > 0:
        return boxes[-best].id
    distance, best = min((_centre_distance(rect, b.bbox), i) for i, b in enumerate(boxes))
    return boxes[best].id if distance <= margin_px else None


def _by_rect(out: BaseModel, boxes: list[Box], margin_px: int) -> tuple[Proposal, dict[str, int]]:
    unplaced = 0

    def one(r) -> str | None:
        nonlocal unplaced
        box = snap_rect(r.root, boxes, margin_px)
        unplaced += box is None
        return box

    def many(rects) -> list[str]:
        return [box for box in map(one, rects) if box is not None]

    def link_lists(*groups: list) -> list[list[str]]:
        """Each group's rectangles as ids, in order, a box kept at its first occurrence in the whole link."""
        seen: set[str] = set()
        result = []
        for group in groups:
            ids = []
            for box in many(group):
                if box not in seen:
                    seen.add(box)
                    ids.append(box)
            result.append(ids)
        return result

    links: list[Link] = []
    for r in out.runs:
        links.append(RunLink(boxes=link_lists(r.boxes)[0], joiner=r.joiner))
    for pr in out.pairs:
        key, value = link_lists(pr.key, pr.value)
        links.append(PairLink(key=key, value=value))
    for rec in out.records:
        *members, header = link_lists(*rec.members, rec.header)
        links.append(RecordLink(members=members, header=header))
    assign: list[Assign] = []
    for a in out.assign:
        box = one(a.rect)
        if box is not None:
            assign.append(Assign(box=box, container=a.container))
    texts: list[TextReading] | None = None
    if hasattr(out, "texts"):
        texts = []
        for t in out.texts:
            box = one(t.rect)
            if box is not None:
                texts.append(TextReading(box=box, text=t.text))
    proposal = Proposal(
        containers=[Container(id=c.id, kind=c.kind, app=c.app, name=c.name, owner=c.owner, covers=c.covers) for c in out.containers],
        assign=assign, unassigned=many(out.unassigned), links=links, texts=texts,
        missed=[(m.text, m.container) for m in getattr(out, "missed", [])], description=out.description)
    return proposal, ({"rect_unplaced": unplaced} if unplaced else {})


def to_proposal(arm: str, out: BaseModel, boxes: list[Box], frame_size: tuple[int, int], margin_px: int,
                reference: str = "ids") -> tuple[Proposal, dict[str, int]]:
    """The proposal and the counts raised during conversion: none under ids (a field-for-field copy); under coords
    `rect_unplaced`, the references that matched no box."""
    if arm != "A":
        raise ValueError(f"no conversion for arm {arm!r}")
    if reference == "coords":
        return _by_rect(out, boxes, margin_px)
    if reference != "ids":
        raise ValueError(f"no conversion for reference {reference!r}")
    links: list[Link] = ([RunLink(boxes=r.boxes, joiner=r.joiner) for r in out.runs]
                         + [PairLink(key=p.key, value=p.value) for p in out.pairs]
                         + [RecordLink(members=r.members, header=r.header) for r in out.records])
    texts = [TextReading(box=t.box, text=t.text) for t in out.texts] if hasattr(out, "texts") else None
    return Proposal(
        containers=[Container(id=c.id, kind=c.kind, app=c.app, name=c.name, owner=c.owner, covers=c.covers) for c in out.containers],
        assign=[Assign(box=a.box, container=a.container, pane=getattr(a, "pane", None)) for a in out.assign],
        unassigned=list(out.unassigned), links=links, texts=texts,
        missed=[(m.text, m.container) for m in getattr(out, "missed", [])], description=out.description), {}
