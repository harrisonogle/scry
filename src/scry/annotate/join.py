"""The joined view: labels per box and per frame, resolved on read from annotations.jsonl, boxes.jsonl and
lifetimes.jsonl. Nothing here writes a file or alters a measured record; one set of rules serves every-frame and
incremental records, and the join never asks which mode wrote them."""
from __future__ import annotations

from bisect import bisect_right
from typing import Literal

from pydantic import BaseModel

from scry.schemas import (Annotation, Container, FrameBoxes, Lifetime, Link, Missed, PairLink, RecordLink, RunLink, box_ref,
                          link_members, link_refs, parse_box_ref)
from scry.textdiff import norm

GLYPH_MAX_LEN = 2  # characters; the icon-glyph strip of `agree`


def agreement(ocr: str, vlm: str, glyph_max_len: int = GLYPH_MAX_LEN) -> bool:
    """Equal after `norm` (whitespace collapsed, quotes straightened, nothing else), or equal after dropping one leading
    or trailing OCR token of at most `glyph_max_len` characters (an icon read as a glyph). It only flags: no recorded
    text is altered."""
    if norm(ocr) == norm(vlm):
        return True
    tokens = ocr.split()
    if len(tokens) >= 2:
        if len(tokens[0]) <= glyph_max_len and norm(" ".join(tokens[1:])) == norm(vlm):
            return True
        if len(tokens[-1]) <= glyph_max_len and norm(" ".join(tokens[:-1])) == norm(vlm):
            return True
    return False


class BoxLink(BaseModel):
    """The link a box is in, with the box's role in it; every id is a box ref of the box's own frame."""
    kind: Literal["run", "pair", "record"]
    role: Literal["run", "key", "value", "member", "header"]
    boxes: list[str] = []
    joiner: str | None = None
    key: list[str] = []
    value: list[str] = []
    members: list[list[str]] = []
    header: list[str] = []


class BoxLabel(BaseModel):
    source: str  # ref of the target box the labels were read from
    container: Container | None  # an object of the source's record: container ids are local to a record
    pane: str | None
    link: BoxLink | None
    vlm: str | None
    agree: bool | None
    non_text: bool


class FrameLabel(BaseModel):
    containers: list[Container] = []
    links: list[Link] = []  # the links in force, every id a box ref of that frame
    description: str | None = None
    description_frame: int | None = None  # the frame of the record the screen-level labels come from
    missed: list[Missed] = []


class LifetimeLink(BaseModel):
    """A relation between lifetimes, as the records proposed it; every id is a lifetime id. Nothing is picked: a
    lifetime that was paired in 20 records and put in a run in 1 has both, with their counts."""
    kind: Literal["run", "pair", "record"]
    boxes: list[str] = []
    joiner: str | None = None
    key: list[str] = []
    value: list[str] = []
    members: list[list[str]] = []
    header: list[str] = []
    records: int  # how many records proposed it
    first_frame: int  # the frame of the first


class LifetimeLabel(BaseModel):
    vlm: str | None  # the model's majority reading; a tie goes to the reading seen first
    vlm_readings: dict[str, int]  # every reading exactly as returned → how many records gave it
    agree: bool | None  # the two majority readings compared
    non_text: bool
    container: Container | None  # that of the lifetime's latest labelled box
    links: list[LifetimeLink] = []


def _renamed(link: Link, name: dict[str, str]) -> Link:
    """The link with every id replaced through `name`."""
    if link.kind == "run":
        return RunLink(boxes=[name[y] for y in link.boxes], joiner=link.joiner)
    if link.kind == "pair":
        return PairLink(key=[name[y] for y in link.key], value=[name[y] for y in link.value])
    return RecordLink(members=[[name[y] for y in cell] for cell in link.members], header=[name[y] for y in link.header])


def _role(link: Link, ref: str) -> str:
    if link.kind == "pair":
        return "key" if ref in link.key else "value"
    return "run" if link.kind == "run" else "member"


class Labels:
    """Labels per box, per frame and per lifetime. `relinked` counts the links refused because one of their boxes
    already had a link in force."""

    def __init__(self, annotations: list[Annotation], frames: list[FrameBoxes], lifetimes: list[Lifetime]):
        frames = sorted(frames, key=lambda fb: fb.frame)
        self._ocr = {box_ref(fb.frame, b.id): b.text for fb in frames for b in fb.boxes}
        self._records = {a.frame: a for a in annotations if a.error is None}  # the successful records
        self._record_frames = sorted(self._records)
        self._life_of = {ref: l for l in lifetimes for ref in l.boxes}
        self._box_at = {l.id: {parse_box_ref(ref)[0]: ref for ref in l.boxes} for l in lifetimes}
        self._source = self._sources(lifetimes)
        self.relinked = 0
        self._accepted: list[tuple[int, Link]] = []  # (record frame, link), record order then stored order
        self._links = self._links_in_force(frames)
        self._boxes = {ref: self._box_label(ref) for ref in self._ocr}
        lifetime_links = self._lifetime_links()
        self._lifetimes = {l.id: self._lifetime_label(l, lifetime_links.get(l.id, [])) for l in lifetimes}

    # ---- rule 1: a box's labels are resolved through its lifetime to the record that labelled it
    def _sources(self, lifetimes: list[Lifetime]) -> dict[str, str]:
        def labelled(ref: str) -> bool:
            frame, box = parse_box_ref(ref)
            return frame in self._records and box in self._records[frame].targets

        source = {ref: ref for ref in self._ocr if labelled(ref)}
        for l in lifetimes:
            latest = None
            for ref in l.boxes:
                if source.get(ref) == ref:
                    latest = ref
                elif latest is not None:
                    source[ref] = latest
        return source

    # ---- rule 4: links are accepted once, then in force
    def _at(self, g: int, link: Link, f: int) -> Link | None:
        """The link of record g as it stands at frame f >= g, every id a box ref of f; None when it is not in force:
        a box it names has no box at f, or a target member no longer draws its labels from record g."""
        name: dict[str, str] = {}
        for y in link_refs(link):
            ref = box_ref(g, y)
            if f != g:
                life = self._life_of.get(ref)
                ref = self._box_at[life.id].get(f) if life is not None else None
            if ref is None:
                return None
            name[y] = ref
        targets = self._records[g].targets
        if any(y in targets and self._source.get(name[y]) != box_ref(g, y) for y in link_members(link)):
            return None
        return _renamed(link, name)

    def _links_in_force(self, frames: list[FrameBoxes]) -> dict[int, list[Link]]:
        """Per frame, the links in force, in record order then stored order. A link that has left force never returns
        (a lifetime never resumes and a source only moves forward), so one pass over the frames carries the list."""
        active: list[tuple[int, Link]] = []
        in_force: dict[int, list[Link]] = {}
        for fb in frames:
            f = fb.frame
            standing = [(g, link, at) for g, link in active if (at := self._at(g, link, f)) is not None]
            active = [(g, link) for g, link, _ in standing]
            here = [at for _, _, at in standing]
            if f in self._records:
                taken = {m for at in here for m in link_members(at)}  # by links of earlier records; headers are exempt
                for link in self._records[f].links:
                    at = self._at(f, link, f)
                    if any(m in taken for m in link_members(at)):
                        self.relinked += 1  # the earlier link stands; this one is refused for good
                    else:
                        active.append((f, link))
                        self._accepted.append((f, link))
                        here.append(at)
            in_force[f] = here
        return in_force

    # ---- rules 2 and 5
    def _box_label(self, ref: str) -> BoxLabel | None:
        source = self._source.get(ref)
        if source is None:
            return None
        g, y = parse_box_ref(source)
        record = self._records[g]
        assign = next((a for a in record.assign if a.box == y), None)
        container = next((c for c in record.containers if c.id == assign.container), None) if assign is not None else None
        vlm = next((t.text for t in record.texts if t.box == y), None) if record.texts is not None else None
        non_text = vlm is not None and vlm.strip() == ""
        agree = None if vlm is None or non_text else agreement(self._ocr[source], vlm)  # both readers read frame g's pixels
        links = self._links.get(parse_box_ref(ref)[0], [])
        link = next((l for l in links if ref in link_members(l)), None)  # as a member first, failing that as a header
        if link is not None:
            box_link = BoxLink(role=_role(link, ref), **link.model_dump())
        else:
            link = next((l for l in links if l.kind == "record" and ref in l.header), None)
            box_link = BoxLink(role="header", **link.model_dump()) if link is not None else None
        return BoxLabel(source=source, container=container, pane=assign.pane if assign is not None else None, link=box_link,
                        vlm=vlm, agree=agree, non_text=non_text)

    def box(self, ref: str) -> BoxLabel | None:
        """The labels of a box, None when no record labelled it or an earlier box of its lifetime. A ref that is not
        in boxes.jsonl raises KeyError."""
        return self._boxes[ref]

    # ---- labels per lifetime
    def _lifetime_links(self) -> dict[str, list[LifetimeLink]]:
        """Every accepted link with its ids as lifetime ids; relations equal in kind, joiner and structure are one
        LifetimeLink. Per lifetime, all those naming it, header included, by first frame then stored order."""
        merged: dict[str, LifetimeLink] = {}
        per_lifetime: dict[str, list[LifetimeLink]] = {}
        for g, link in self._accepted:
            lives = {y: self._life_of.get(box_ref(g, y)) for y in link_refs(link)}
            if any(l is None for l in lives.values()):
                continue
            relation = _renamed(link, {y: l.id for y, l in lives.items()})
            key = relation.model_dump_json()
            if key in merged:
                merged[key].records += 1
            else:
                merged[key] = LifetimeLink(**relation.model_dump(), records=1, first_frame=g)
                for lifetime_id in link_refs(relation):
                    per_lifetime.setdefault(lifetime_id, []).append(merged[key])
        return per_lifetime

    def _lifetime_label(self, life: Lifetime, links: list[LifetimeLink]) -> LifetimeLabel | None:
        readings: dict[str, int] = {}  # in frame order, so the first key is the reading seen first
        for ref in life.boxes:
            frame, box = parse_box_ref(ref)
            record = self._records.get(frame)
            if record is not None and box in record.targets and record.texts is not None:
                for t in record.texts:
                    if t.box == box:
                        readings[t.text] = readings.get(t.text, 0) + 1
        latest = self._boxes.get(life.boxes[-1])  # the last box draws its labels from the latest labelled box
        if latest is None and not links:
            return None
        vlm = None
        for text, n in readings.items():
            if text.strip() and (vlm is None or n > readings[vlm]):
                vlm = text
        return LifetimeLabel(vlm=vlm, vlm_readings=readings, agree=None if vlm is None else agreement(life.text, vlm),
                             non_text=bool(readings) and vlm is None, container=latest.container if latest is not None else None,
                             links=links)

    def lifetime(self, lifetime_id: str) -> LifetimeLabel | None:
        """The labels of a lifetime, None when it has no labelled box and no link. An unknown id raises KeyError."""
        return self._lifetimes[lifetime_id]

    # ---- rule 6: screen-level labels are those of the latest successful record at or before the frame
    def frame(self, frame: int) -> FrameLabel:
        i = bisect_right(self._record_frames, frame)
        if i == 0:
            return FrameLabel()
        r = self._records[self._record_frames[i - 1]]
        return FrameLabel(containers=r.containers, links=self._links.get(frame, []), description=r.description,
                          description_frame=r.frame, missed=r.missed)


def build_labels(annotations: list[Annotation], frames: list[FrameBoxes], lifetimes: list[Lifetime]) -> Labels:
    return Labels(annotations, frames, lifetimes)
