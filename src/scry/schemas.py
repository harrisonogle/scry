from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

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


# ---------- outline ----------
class OutlineChapter(BaseModel):
    id: str
    start_s: float
    end_s: float
    title: str
    gist: str
