"""From the model's answer, whatever the referencing arm, to one arm-independent proposal (plan 2, D1)."""
from __future__ import annotations

from dataclasses import dataclass

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


def to_proposal(arm: str, out: BaseModel, boxes: list[Box], frame_size: tuple[int, int], margin_px: int) -> tuple[Proposal, dict[str, int]]:
    """The proposal and the counts raised during conversion (none for arm A, which is a field-for-field copy)."""
    if arm != "A":
        raise ValueError(f"no conversion for arm {arm!r}")
    links: list[Link] = ([RunLink(boxes=r.boxes, joiner=r.joiner) for r in out.runs]
                         + [PairLink(key=p.key, value=p.value) for p in out.pairs]
                         + [RecordLink(members=r.members, header=r.header) for r in out.records])
    texts = [TextReading(box=t.box, text=t.text) for t in out.texts] if hasattr(out, "texts") else None
    return Proposal(
        containers=[Container(id=c.id, kind=c.kind, app=c.app, name=c.name, owner=c.owner, covers=c.covers) for c in out.containers],
        assign=[Assign(box=a.box, container=a.container, pane=getattr(a, "pane", None)) for a in out.assign],
        unassigned=list(out.unassigned), links=links, texts=texts,
        missed=[(m.text, m.container) for m in getattr(out, "missed", [])], description=out.description), {}
