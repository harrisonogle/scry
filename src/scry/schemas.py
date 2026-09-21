from __future__ import annotations

from pydantic import BaseModel

BBox = tuple[int, int, int, int]  # x0, y0, x1, y1 in original-frame pixels; x1/y1 exclusive


# ---------- decode ----------
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


# ---------- OCR ----------
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


# ---------- outline ----------
class OutlineChapter(BaseModel):
    id: str
    start_s: float
    end_s: float
    title: str
    gist: str
