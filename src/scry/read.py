from __future__ import annotations

import logging
import time

from scry.config import Config, config_hash
from scry.jsonl import write_jsonl
from scry.ocr import get_engine
from scry.ocr.base import OcrEngine, RawLine
from scry.run import Run
from scry.schemas import BBox, Box, FrameBoxes

log = logging.getLogger(__name__)


def _intersects(a: BBox, b: BBox) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def assign_ids(raw: list[RawLine], churn: list[BBox]) -> tuple[list[Box], int]:
    """The frame's boxes in reading order, and how many raw lines were dropped for having no text. Reading order is the
    top edge, then the left edge; it is the pipeline's only definition of reading order. Text, conf, bbox and words are
    the adapter's, unaltered."""
    kept = [l for l in raw if l.text.strip()]
    ordered = sorted(kept, key=lambda l: (l.bbox[1], l.bbox[0]))
    boxes = [Box(id=f"b{i}", bbox=l.bbox, text=l.text, conf=l.conf, words=l.words,
                 in_churn=any(_intersects(l.bbox, c) for c in churn)) for i, l in enumerate(ordered, start=1)]
    return boxes, len(raw) - len(kept)


def read_config_hash(cfg: Config) -> str:
    """The config hash `read` writes to the manifest and checks itself against: the [read] section, nothing else. The
    harness imports a source's boxes into a subset only when the subset's config hashes the same here (scry.subset)."""
    return config_hash(cfg, "read")


def run_read(run: Run, cfg: Config, engine: OcrEngine | None = None) -> None:
    """read: OCR boxes per emitted frame → boxes.jsonl. One pass of one engine; nothing is re-read or corrected."""
    inputs = [run.frames]
    ch = read_config_hash(cfg)
    if run.stage_up_to_date("read", inputs, ch):
        log.info("read up to date")
        return
    engine = engine or get_engine(cfg.read)
    records: list[FrameBoxes] = []
    dropped = 0
    total = 0.0  # wall time of the OCR calls: it goes to the manifest, never into boxes.jsonl (ledger L56)
    for rec in run.load_frames():
        t0 = time.perf_counter()
        raw = engine.recognize(run.root / rec.png)
        seconds = time.perf_counter() - t0
        total += seconds
        boxes, d = assign_ids(raw, rec.churn_regions)
        dropped += d
        records.append(FrameBoxes(frame=rec.frame, png=rec.png, engine=engine.settings(), boxes=boxes))
        log.debug("frame %d: %d boxes in %.2fs", rec.frame, len(boxes), seconds)
    write_jsonl(run.boxes, records)
    run.stage_done("read", inputs, ch, frames=len(records), boxes=sum(len(r.boxes) for r in records), dropped_empty=dropped,
                   seconds=round(total, 1), seconds_per_frame=round(total / len(records), 3) if records else None,
                   engine=engine.settings())
