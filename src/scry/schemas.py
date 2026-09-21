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
# VlmRegionGroupOnly / VlmPerceptionGroupOnly are the group-only output (`[model] stage2c_transcribe = false`): the same
# fields without vlm_lines. The transcribing models extend them, so their JSON schemas (and cache keys) are unchanged.
class VlmRegionGroupOnly(BaseModel):
    id: str = Field(description="Region id you assign: r1, r2, … unique in this frame.")
    kind: Literal["window", "pane", "popup"] = Field(description="window = top-level application window; pane = an area inside a window; popup = menu, dialog, tooltip, toast.")
    name: str = Field(description="Short human name for the region, e.g. 'Windows Terminal — pwsh', 'left navigation', 'Save dialog'.")
    app: str = Field(description="Application the region belongs to, e.g. 'Windows Terminal', 'Browser', 'VS Code', 'Notepad'.")
    parent: str | None = Field(description="Id of the enclosing region, or null for a top-level window.")
    conf: float = Field(description="Your 0-1 confidence that this region exists as described and its marks are grouped correctly.")
    occludes: list[str] = Field(default_factory=list, description="Ids of regions this region visually covers, in whole or in part.")
    rows: list[list[str]] = Field(default_factory=list, description="The region's visual lines in reading order. Each row lists the mark numbers (as 'l7') that sit on that one visual line, left to right; [] for a line the boxes missed. Every mark appears in exactly one row of exactly one region, or in unassigned_line_ids.")


class VlmRegion(VlmRegionGroupOnly):
    vlm_lines: list[str] = Field(default_factory=list, description="Verbatim text of each row, one entry per row, same order and length as rows. Transcribe from the clean image. Preserve case, punctuation, whitespace and symbols; never correct, complete or normalize code, commands, paths or identifiers; use ? for a character you cannot resolve; do not transcribe icons.")


class VlmPerceptionGroupOnly(BaseModel):
    regions: list[VlmRegionGroupOnly]
    focused_region: str | None = Field(description="Id of the window that has keyboard focus, or null if unclear.")
    focused_conf: float = Field(description="0-1 confidence in focused_region.")
    focused_cues: list[str] = Field(default_factory=list, description="Visual cues used: title bar highlight, caret visible, dialog modality, …")
    description: str = Field(description="Anything the rows cannot express: selections, highlights, toggles, icons, diagram relationships, dialogs, animating regions.")
    unassigned_line_ids: list[str] = Field(default_factory=list, description="Marks that belong to no region.")


class VlmPerception(VlmPerceptionGroupOnly):
    regions: list[VlmRegion]


def perception_from_group_only(out: VlmPerceptionGroupOnly) -> VlmPerception:
    """Group-only output in the usual shape: an empty transcription per row, which Stage 3 treats as no reading (§8.3)."""
    regions = [VlmRegion(**r.model_dump(), vlm_lines=[""] * len(r.rows)) for r in out.regions]
    return VlmPerception(**out.model_dump(exclude={"regions"}), regions=regions)


# Structural variants (`[model] stage2c_panes = false`, `stage2c_rows = "boxes"`). NoPanes: kind is window|popup and
# parent a window id or null. Boxes: one mark per row, plus the region's associations (label-and-value pairs, table
# rows). Each is its own model, so its schema hash, and with it the cache key, differs from the default; VlmRegion and
# VlmPerception themselves are unchanged, and every variant is stored in their shape (perception_from_variant).
class VlmRegionNoPanes(VlmRegion):
    kind: Literal["window", "popup"] = Field(description="window = top-level application window; popup = menu, dialog, tooltip, toast. There are no panes: everything inside a window is the window's own rows.")
    parent: str | None = Field(description="For a popup, the id of the window it belongs to, or null; null for a window.")


class VlmRegionBoxes(VlmRegion):
    rows: list[list[str]] = Field(default_factory=list, description="One row per mark in reading order (top to bottom, left to right along a visual line), each row a list holding exactly that one mark id (as 'l7'); [] for a line the boxes missed. Every mark appears in exactly one row of exactly one region, or in unassigned_line_ids.")
    vlm_lines: list[str] = Field(default_factory=list, description="Verbatim text of each row's mark, one entry per row, same order and length as rows. Transcribe from the clean image. Preserve case, punctuation, whitespace and symbols; never correct, complete or normalize code, commands, paths or identifiers; use ? for a character you cannot resolve; do not transcribe icons.")
    associations: list[list[str]] = Field(default_factory=list, description="Groups of this region's mark ids that belong together as one label-and-value pair or one table row, each listed left to right. A mark belongs to at most one group; marks that stand alone are not listed.")


class VlmRegionNoPanesBoxes(VlmRegionNoPanes, VlmRegionBoxes):
    pass


class VlmPerceptionNoPanes(VlmPerception):
    regions: list[VlmRegionNoPanes]


class VlmPerceptionBoxes(VlmPerception):
    regions: list[VlmRegionBoxes]


class VlmPerceptionNoPanesBoxes(VlmPerception):
    regions: list[VlmRegionNoPanesBoxes]


def perception_model(transcribe: bool = True, panes: bool = True, rows: str = "lines") -> type[BaseModel]:
    """The Stage 2c output model for a configuration (§8.3); the group-only model has no structural variants."""
    if not transcribe:
        return VlmPerceptionGroupOnly
    return {(True, "lines"): VlmPerception, (False, "lines"): VlmPerceptionNoPanes,
            (True, "boxes"): VlmPerceptionBoxes, (False, "boxes"): VlmPerceptionNoPanesBoxes}[(panes, rows)]


def perception_from_variant(out: BaseModel) -> tuple[VlmPerception, dict[str, list[list[str]]]]:
    """Any Stage 2c output in the usual shape (what the record stores and Stage 3 reads), plus the associations of the
    boxes variant, which VlmPerception does not carry: {region id: [[mark ids, left to right], ...]}."""
    if not isinstance(out, VlmPerception):
        return perception_from_group_only(out), {}
    assoc = {r.id: [list(g) for g in r.associations] for r in out.regions if getattr(r, "associations", None)}
    return VlmPerception.model_validate(out.model_dump()), assoc


class PerceptionRecord(BaseModel):
    frame: int
    model: str
    prompt_version: str
    output: VlmPerception | None
    error: str | None = None
    usage: dict = {}
    repairs: int = 0
    label_clashes: int = 0
    associations: dict[str, list[list[str]]] = {}  # boxes variant: per region id, the model's mark groups (perception_from_variant)


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
    associations: list[list[str]] = []  # boxes variant: mark groups that read as one label-and-value pair or table row, left to right


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
    under_change: bool | None = None  # the line's box meets a changed-pixel component (§11.2 pixel gate); None when the line has no box


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


class PixelChange(BaseModel):
    """Changed pixels between the two frames' PNGs, by Stage 1's rule (§11.2 pixel gate)."""
    changed_fraction: float  # changed pixels / screen
    components: list[BBox] = []  # tight boxes of the changed components
    vetoed: int = 0  # ops dropped by the gate


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
    pixels: PixelChange | None = None


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
