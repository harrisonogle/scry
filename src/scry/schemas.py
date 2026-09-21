from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

BBox = tuple[int, int, int, int]  # x0, y0, x1, y1 in original-frame pixels; x1/y1 exclusive


# ---------- decode ----------
class Frame(BaseModel):
    video_id: str
    frame: int
    t_change: float
    t_settled: float
    t_end: float
    settled: bool
    churn_regions: list[BBox] = []
    caret: BBox | None = None
    width: int
    height: int
    sha256: str
    png: str


# ---------- OCR ----------
class RawWord(BaseModel):
    text: str
    bbox: BBox


# ---------- read: boxes.jsonl ----------
class Box(BaseModel):
    id: str  # "b<n>", n from 1, in reading order (top edge, then left edge)
    bbox: BBox
    text: str
    conf: float
    words: list[RawWord] | None = None
    in_churn: bool = False


class FrameBoxes(BaseModel):
    frame: int
    png: str
    engine: dict  # the adapter's whole settings() dict
    seconds: float = 0.0  # wall time of the OCR call
    boxes: list[Box] = []


def box_ref(frame: int, box_id: str) -> str:
    """A box named across frames: "<frame>:<box id>", e.g. "154:b31"."""
    return f"{frame}:{box_id}"


def parse_box_ref(ref: str) -> tuple[int, str]:
    frame, sep, box_id = ref.partition(":")
    if not sep or not box_id:
        raise ValueError(f"not a box ref: {ref!r}")
    return int(frame), box_id


# ---------- track: changes.jsonl ----------
class PixelStats(BaseModel):
    changed_fraction: float  # changed pixels / screen
    components: int
    textless: int  # components that touch no box of either frame
    textless_area: int  # their changed pixels
    touched_share: float  # touched boxes / boxes, both frames
    rect_only: int  # boxes a rectangle test would have called touched and the pixel test does not (H6)


class BoxText(BaseModel):
    box: str  # box ref
    text: str


class BoxChange(BaseModel):
    kind: Literal["reread", "appended", "truncated", "changed", "appeared", "removed"]
    rect: BBox
    before: BoxText | None  # null for an appeared record
    after: BoxText | None  # null for a removed record
    char_diff: list[list[str]] = []
    continues: str | None = None  # "T8/0": the previous change's id and the index of its record
    in_churn: bool = False


class Revert(BaseModel):
    """What a transition undid of the one before it: one per transition, present only when share > 0 (ledger L51)."""
    of: str  # the previous change's id
    share: float  # of the pixels the previous change changed, the share that is back to what it was before it; 4 places
    hold_s: float  # how long the previous change stood


class Change(BaseModel):
    id: str  # "T<n>", n from 1
    from_frame: int
    to_frame: int
    t: tuple[float, float]
    kind: Literal["single", "unsettled"]
    pixels: PixelStats | None
    records: list[BoxChange] = []
    moved: list[tuple[str, str]] = []  # box refs: earlier, later
    same_place: int = 0
    unchanged: int = 0
    variants: int = 0
    flicker_new: list[str] = []
    flicker_lost: list[str] = []
    reverts: Revert | None = None


# ---------- track: lifetimes.jsonl ----------
class FrameTime(BaseModel):
    frame: int
    t: float


class Lifetime(BaseModel):
    id: str  # "L<n>", n from 1
    text: str  # the majority reading
    readings: dict[str, list[int]]  # reading → the frames at which it was sighted, ascending
    unstable: bool
    sightings: int
    first: FrameTime
    last: FrameTime
    moved: bool = False
    boxes: list[str]  # box refs, frame order


# ---------- annotate: annotations.jsonl (labels: proposals of a model, never measurements) ----------
class Container(BaseModel):
    id: str  # "c<n>", local to the record
    kind: Literal["window", "popup"]
    app: str
    name: str
    owner: str | None = None
    covers: list[str] = []
    rect: BBox | None = None  # set only under the arms where the model draws containers


class Assign(BaseModel):
    box: str  # frame-local box id, e.g. "b33"
    container: str
    pane: str | None = None


class RunLink(BaseModel):
    kind: Literal["run"] = "run"
    boxes: list[str]
    joiner: Literal["", " "]


class PairLink(BaseModel):
    kind: Literal["pair"] = "pair"
    key: list[str]
    value: list[str]


class RecordLink(BaseModel):
    kind: Literal["record"] = "record"
    members: list[list[str]]  # the row's cells, left to right
    header: list[str] = []


Link = Annotated[RunLink | PairLink | RecordLink, Field(discriminator="kind")]


class TextReading(BaseModel):
    box: str
    text: str


class Missed(BaseModel):
    id: str  # "m<n>", n from 1 in the record
    text: str
    container: str | None = None


class Annotation(BaseModel):
    """One record per call. A failed call has `error` set, no description, `texts` None, empty lists, and its targets."""
    frame: int
    targets: list[str]
    containers: list[Container] = []
    assign: list[Assign] = []
    links: list[Link] = []
    texts: list[TextReading] | None = None  # None: the call did not transcribe; a list, possibly empty: it did
    missed: list[Missed] = []
    unassigned: list[str] = []
    description: str | None = None
    repairs: int = 0
    repair_counts: dict[str, int] = {}
    label_clashes: int = 0
    model: str
    prompt_version: str
    usage: dict = {}
    error: str | None = None


def link_members(link: RunLink | PairLink | RecordLink) -> list[str]:
    if link.kind == "run":
        return list(link.boxes)
    if link.kind == "pair":
        return link.key + link.value
    return [b for cell in link.members for b in cell]


def link_refs(link: RunLink | PairLink | RecordLink) -> list[str]:
    """The members plus, for a record, its header."""
    return link_members(link) + (link.header if link.kind == "record" else [])


# ---------- interpret: interpretations.jsonl (a model's judgement of one transition, never a measurement) ----------
Submitted = Literal["yes", "no", "unclear"]


class Interpretation(BaseModel):
    """One record per change. A record without a call or without an answer has `error` set and no model fields."""
    id: str  # the change's id
    action: str | None = None
    result: str | None = None
    description: str | None = None
    confidence: float | None = None
    entered_text: str | None = None  # the user's input as the later frame shows it; the whole submitted text on a submission
    submitted: Submitted | None = None
    citations: list[str] = []  # box refs "<frame>:<box id>", validated against the ids the call was handed
    invalid_citations: int = 0  # cited entries that were not among them
    usage: dict = {}  # of the call that produced the record, served from the call cache or not
    model: str | None = None
    prompt_version: str | None = None  # names the image mode too
    error: str | None = None


# ---------- summarize: steps.jsonl, sections.jsonl, video.json ----------
class SegmentStart(BaseModel):
    start_id: str = Field(description="Id of the first item of a new segment, exactly as listed.")
    label: str = Field(description="Short label for the segment that starts here.")


class ModelBoundaries(BaseModel):
    segments: list[SegmentStart]


class ModelElaboration(BaseModel):
    label: str = Field(description="Short label for this segment.")
    description: str = Field(description="Description for a reader who will follow it. Every sentence carries the child ids it rests on in brackets, e.g. [T13]. Quote commands exactly.")
    refs: list[str] = Field(default_factory=list, description="Every child id cited in description.")


class HierNode(BaseModel):
    id: str  # "S<n>" a step, "C<n>" a section, "V" the video
    level: Literal["step", "section", "video"]
    children: tuple[str, str]  # first and last child id
    frames: tuple[int, int]
    t: tuple[float, float]
    label: str
    description: str
    refs: list[str] = []
    segmentation_conf: Literal["high", "low"] = "high"


# ---------- outline ----------
class OutlineChapter(BaseModel):
    id: str
    start_s: float
    end_s: float
    title: str
    gist: str
