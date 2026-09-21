from __future__ import annotations

import statistics
from typing import Literal

from pydantic import BaseModel, Field

BBox = tuple[int, int, int, int]  # x0, y0, x1, y1 in original-frame pixels; x1/y1 exclusive


# ---------- Stage 1 (§7.6) ----------
class Stage1Record(BaseModel):
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


# ---------- Stage 2a (§8.1) ----------
class RawWord(BaseModel):
    text: str
    bbox: BBox


class OcrLine(BaseModel):
    id: str
    bbox: BBox
    text: str
    conf: float
    words: list[RawWord] | None = None
    in_churn: bool = False
    confusable: bool = False


class OcrFrame(BaseModel):
    frame: int
    engine: str
    settings: dict = {}
    seconds: float = 0.0
    lines: list[OcrLine] = []


# ---------- Stage 2c VLM output (§8.3) ----------
class VlmRegion(BaseModel):
    id: str = Field(description="Region id you assign: r1, r2, … unique in this frame.")
    kind: Literal["window", "pane", "popup"] = Field(description="window = top-level application window; pane = an area inside a window; popup = menu, dialog, tooltip, toast.")
    name: str = Field(description="Short human name for the region, e.g. 'Windows Terminal — pwsh', 'left navigation', 'Save dialog'.")
    app: str = Field(description="Application the region belongs to, e.g. 'Windows Terminal', 'Browser', 'VS Code', 'Notepad'.")
    parent: str | None = Field(description="Id of the enclosing region, or null for a top-level window.")
    conf: float = Field(description="Your 0-1 confidence that this region exists as described and its marks are grouped correctly.")
    occludes: list[str] = Field(default_factory=list, description="Ids of regions this region visually covers, in whole or in part.")
    rows: list[list[str]] = Field(default_factory=list, description="The region's visual lines in reading order. Each row lists the mark numbers (as 'l7') that sit on that one visual line, left to right; [] for a line the boxes missed. Every mark appears in exactly one row of exactly one region, or in unassigned_line_ids.")
    vlm_lines: list[str] = Field(default_factory=list, description="Verbatim text of each row, one entry per row, same order and length as rows. Transcribe from the clean image. Preserve case, punctuation, whitespace and symbols; never correct, complete or normalize code, commands, paths or identifiers; use ? for a character you cannot resolve; do not transcribe icons.")


class VlmPerception(BaseModel):
    regions: list[VlmRegion]
    focused_region: str | None = Field(description="Id of the window that has keyboard focus, or null if unclear.")
    focused_conf: float = Field(description="0-1 confidence in focused_region.")
    focused_cues: list[str] = Field(default_factory=list, description="Visual cues used: title bar highlight, caret visible, dialog modality, …")
    description: str = Field(description="Anything the rows cannot express: selections, highlights, toggles, icons, diagram relationships, dialogs, animating regions.")
    unassigned_line_ids: list[str] = Field(default_factory=list, description="Marks that belong to no region.")


class PerceptionRecord(BaseModel):
    frame: int
    model: str
    prompt_version: str
    output: VlmPerception | None
    error: str | None = None
    usage: dict = {}
    repairs: int = 0
    label_clashes: int = 0


# ---------- Stage 3 merged state (§10.1) ----------
class Line(BaseModel):
    id: str
    marks: list[str] = []
    bbox: BBox | None
    ocr: str | None
    ocr_conf: float | None
    vlm: str | None
    agree: bool | None
    in_churn: bool | None
    ocr_glyph_stripped: str | None = None
    confusable: bool = False
    row_rejected: bool = False

    @property
    def fused(self) -> str:
        if self.agree and self.vlm is not None and self.ocr_glyph_stripped is not None:
            return self.vlm
        if self.agree and self.ocr is not None:
            return self.ocr
        if self.ocr is None:
            return self.vlm or ""
        return self.ocr

    @property
    def uncertain(self) -> bool:
        return not self.agree and self.ocr is not None and self.vlm is not None


class Region(BaseModel):
    id: str
    kind: str
    name: str
    app: str
    parent: str | None
    bbox: BBox | None
    conf: float
    layout_conf: float
    occludes: list[str] = []
    lines: list[Line] = []


class FrameRecord(BaseModel):
    video_id: str
    frame: int
    t_change: float
    t_settled: float
    t_end: float
    settled: bool
    png: str
    overlay: str | None
    sha256: str
    width: int
    height: int
    churn_regions: list[BBox] = []
    caret: BBox | None = None
    focused_region: str | None = None
    focused_conf: float | None = None
    focused_signals: list[str] = []
    description: str = ""
    regions: list[Region] = []
    unassigned_lines: list[Line] = []
    grouping_repairs: int = 0
    rows_rejected: int = 0
    label_clashes: int = 0
    vlm_model: str | None = None
    prompt_version: str | None = None
    error: str | None = None

    def region(self, rid: str) -> Region | None:
        return next((r for r in self.regions if r.id == rid), None)

    def line_ids(self) -> set[str]:
        ids = {ln.id for r in self.regions for ln in r.lines}
        ids |= {ln.id for ln in self.unassigned_lines}
        return ids

    # ---------- diff units (§11.1): windows and popups; panes fold into their nearest ancestor unit ----------
    def unit_of(self, rid: str) -> str | None:
        """The unit a region folds into: itself for a parent-null region or a popup, else its nearest ancestor unit."""
        by_id = {r.id: r for r in self.regions}
        if rid not in by_id:
            return None
        seen = {rid}
        while by_id[rid].parent in by_id and by_id[rid].kind != "popup" and by_id[rid].parent not in seen:
            rid = by_id[rid].parent
            seen.add(rid)
        return rid

    def units(self) -> list[Region]:
        return [r for r in self.regions if self.unit_of(r.id) == r.id]

    def unit_line_sources(self, unit_id: str) -> list[tuple[Line, str]]:
        """The unit's line list with the id of the region each line came from: its own lines plus those of every region
        folding into it, in row order — lines whose y centres lie within half the median line height of a row's first
        line form one row, rows top to bottom, lines within a row by x0 (raw y-centre order flips on 1-px OCR jitter);
        lines without a bbox last, in stored order."""
        items = [(ln, r.id) for r in self.regions if self.unit_of(r.id) == unit_id for ln in r.lines]
        boxed = sorted((it for it in items if it[0].bbox), key=lambda it: (it[0].bbox[1] + it[0].bbox[3]) / 2)
        hs = [it[0].bbox[3] - it[0].bbox[1] for it in boxed]
        half_h = 0.5 * (statistics.median(hs) if hs else 16.0)
        rows: list[list[tuple[Line, str]]] = []
        row_yc = None
        for it in boxed:
            yc = (it[0].bbox[1] + it[0].bbox[3]) / 2
            if row_yc is None or yc - row_yc >= half_h:
                rows.append([])
                row_yc = yc
            rows[-1].append(it)
        return [it for row in rows for it in sorted(row, key=lambda it: it[0].bbox[0])] + [it for it in items if not it[0].bbox]

    def unit_lines(self, unit_id: str) -> list[Line]:
        return [ln for ln, _ in self.unit_line_sources(unit_id)]


# ---------- Stage 4 (§10.2) ----------
class DiffOp(BaseModel):
    op: Literal["insert", "delete", "modify"]
    old: str | None = None
    new: str | None = None
    old_index: int | None = None
    new_index: int | None = None
    char_diff: list[list[str]] | None = None
    y: int | None = None
    uncertain: bool = False
    clock: bool = False
    in_churn: bool = False
    pane: str | None = None  # region the new line (old line for a delete) came from, when it is not the unit itself (§11.1)


class RegionDiff(BaseModel):
    from_region: str | None
    ops: list[DiffOp] = []


class Event(BaseModel):
    type: Literal["typed", "output_appended", "appeared", "disappeared"]
    region: str
    text: str | None = None
    line: str | None = None
    lines: int | None = None
    frames: tuple[int, int]


class Correspondence(BaseModel):
    matched: list[tuple[str, str, float]] = []
    appeared: list[str] = []
    disappeared: list[str] = []


class TransientInfo(BaseModel):
    frame: int
    region: str
    name: str
    hold_s: float


class Transition(BaseModel):
    id: str
    from_frame: int
    to_frame: int
    intermediate_frames: list[int] = []
    t: tuple[float, float]
    kind: Literal["single", "coalesced", "transient_merged", "unsettled", "trivial"]
    regions: Correspondence = Correspondence()
    computed_diff: dict[str, RegionDiff] = {}
    events: list[Event] = []
    transient: TransientInfo | None = None


class FocusRecord(BaseModel):
    frame: int
    focused_region: str | None
    focused_conf: float | None
    focused_signals: list[str]


# ---------- Stage 5 (§12) ----------
class VlmRefs(BaseModel):
    lines: list[str] = Field(default_factory=list, description="Line references your statements rest on, as '<frame>:<line_id>' using the frame numbers given, e.g. '16:l3'.")


class VlmInterpretation(BaseModel):
    action: str = Field(description="The single user action that best explains the change (typed, clicked, selected, navigated, pressed a key). If none is evident, say so.")
    result: str = Field(description="What visibly changed as a consequence, including non-textual changes visible in the images.")
    description: str = Field(description="Anything else visible and relevant.")
    confidence: float = Field(description="0-1 confidence in action and result.")
    refs: VlmRefs = Field(default_factory=VlmRefs)


class Interpretation(BaseModel):
    id: str
    action: str | None = None
    result: str | None = None
    description: str | None = None
    confidence: float | None = None
    refs: VlmRefs = VlmRefs()
    invalid_refs: int = 0
    model: str | None = None
    prompt_version: str | None = None
    error: str | None = None


# ---------- Stage 6 (§10.3, §13) ----------
class SegmentStart(BaseModel):
    start_id: str = Field(description="Id of the first item of a new segment, exactly as listed.")
    label: str = Field(description="Short label for the segment that starts here.")


class VlmBoundaries(BaseModel):
    segments: list[SegmentStart]


class VlmElaboration(BaseModel):
    label: str = Field(description="Short label for this segment.")
    description: str = Field(description="Description for a reader who will follow it. Every sentence carries the child ids it rests on in brackets, e.g. [T13]. Quote commands exactly.")
    refs: list[str] = Field(default_factory=list, description="Every child id cited in description.")


class HierNode(BaseModel):
    id: str
    level: Literal["step", "section", "video"]
    children: tuple[str, str]
    frames: tuple[int, int]
    t: tuple[float, float]
    label: str
    description: str
    refs: list[str] = []
    segmentation_conf: Literal["high", "low"] = "high"


# ---------- Stage 0 (§10.4) ----------
class OutlineChapter(BaseModel):
    id: str
    start_s: float
    end_s: float
    title: str
    gist: str
