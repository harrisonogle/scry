"""Validation is repair, never abort (spec §6): a bad label is dropped and counted, and the run continues. Every
dropped item adds 1 to exactly one key: the first check it fails, in the order written here. `rect_unplaced` is raised
before repair, in the conversion (`to_proposal` under reference = "coords"): a rectangle that named no box."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from scry.annotate.proposal import Proposal
from scry.schemas import Assign, Container, Link, Missed, RecordLink, TextReading, link_members, link_refs

REPAIR_KEYS: tuple[str, ...] = (
    "dup_container", "bad_owner", "bad_covers", "bad_rect", "unknown_box", "not_target", "unknown_container",
    "second_assignment", "unplaced", "outside", "ambiguous", "link_unsnapped", "link_unknown_box", "link_malformed",
    "link_already_linked", "text_unknown_box", "text_not_target", "second_text", "text_missing", "missed_empty",
    "missed_unknown_container", "rect_unplaced")


@dataclass
class Repaired:
    containers: list[Container]
    assign: list[Assign]
    unassigned: list[str]
    links: list[Link]
    texts: list[TextReading] | None
    missed: list[Missed]
    counts: dict[str, int]  # non-zero keys only


def repair_containers(containers: list[Container]) -> tuple[list[Container], dict[str, int]]:
    """A second container with an id already used is dropped; an owner must be another container, a window, and only a
    popup has one; covers keeps ids of other containers, once each. Running it on its own result changes nothing."""
    counts: Counter[str] = Counter()
    result: list[Container] = []
    for c in containers:
        if any(c.id == kept.id for kept in result):
            counts["dup_container"] += 1
        else:
            result.append(c.model_copy(deep=True))
    by_id = {c.id: c for c in result}
    for c in result:
        if c.owner is not None:
            owner = by_id.get(c.owner)
            if c.kind != "popup" or owner is None or owner is c or owner.kind != "window":
                c.owner = None
                counts["bad_owner"] += 1
        covers: list[str] = []
        for cid in c.covers:
            if cid not in by_id or cid == c.id or cid in covers:
                counts["bad_covers"] += 1
            else:
                covers.append(cid)
        c.covers = covers
    return result, dict(counts)


def _malformed(link: Link) -> bool:
    refs = link_refs(link)
    if len(set(refs)) != len(refs):  # so a key and value in one box are never a pair, and a header box is never a cell
        return True
    if link.kind == "run":
        return len(link.boxes) < 2
    if link.kind == "pair":
        return not link.key or not link.value
    return len(link.members) < 2


def repair(p: Proposal, targets: Sequence[str], frame_boxes: Sequence[str]) -> Repaired:
    """One function for every mode: nothing about earlier records is passed in."""
    on_frame, is_target = set(frame_boxes), set(targets)
    containers, container_counts = repair_containers(p.containers)
    counts: Counter[str] = Counter(container_counts)
    container_ids = {c.id for c in containers}

    assign: list[Assign] = []
    assigned: set[str] = set()
    for a in p.assign:
        if a.box not in on_frame:
            counts["unknown_box"] += 1
        elif a.box not in is_target:
            counts["not_target"] += 1
        elif a.container not in container_ids:
            counts["unknown_container"] += 1
        elif a.box in assigned:
            counts["second_assignment"] += 1
        else:
            assigned.add(a.box)
            assign.append(Assign(box=a.box, container=a.container, pane=(a.pane or "").strip() or None))
    unassigned: list[str] = []
    for b in p.unassigned:
        if b in is_target and b not in assigned and b not in unassigned:
            unassigned.append(b)
    for b in targets:
        if b not in assigned and b not in unassigned:
            unassigned.append(b)
            counts["unplaced"] += 1

    links: list[Link] = []
    linked: set[str] = set()  # members of the links kept so far; header ids never enter it
    for link in p.links:
        if link.kind == "record":
            link = RecordLink(members=[cell for cell in link.members if cell], header=link.header)
        if any(ref not in on_frame for ref in link_refs(link)):
            counts["link_unknown_box"] += 1
        elif _malformed(link):
            counts["link_malformed"] += 1
        elif any(m in linked for m in link_members(link)):
            counts["link_already_linked"] += 1
        else:
            linked.update(link_members(link))
            links.append(link)

    texts: list[TextReading] | None = None
    if p.texts is not None:
        texts = []
        for t in p.texts:
            if t.box not in on_frame:
                counts["text_unknown_box"] += 1
            elif t.box not in is_target:
                counts["text_not_target"] += 1
            elif any(t.box == kept.box for kept in texts):
                counts["second_text"] += 1
            else:
                texts.append(t)
        counts["text_missing"] += len(is_target - {t.box for t in texts})  # nothing is invented for them

    missed: list[Missed] = []
    for text, container in p.missed:
        if not text.strip():
            counts["missed_empty"] += 1
            continue
        if container is not None and container not in container_ids:
            container = None
            counts["missed_unknown_container"] += 1
        missed.append(Missed(id=f"m{len(missed) + 1}", text=text, container=container))

    return Repaired(containers, assign, unassigned, links, texts, missed, {k: n for k, n in counts.items() if n})
