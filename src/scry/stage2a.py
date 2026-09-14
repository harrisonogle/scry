from __future__ import annotations

import logging
import re
import time
import unicodedata

from scry.config import Config, config_hash
from scry.jsonl import write_jsonl
from scry.ocr import get_engine
from scry.ocr.base import RawLine
from scry.run import Run
from scry.schemas import BBox, OcrFrame, OcrLine

log = logging.getLogger(__name__)
_TOKEN = re.compile(r"\S+")


def is_confusable(text: str) -> bool:
    """A token mixing ASCII letters/digits with non-ASCII letters (Cyrillic е in a GUID)."""
    for tok in _TOKEN.findall(text):
        has_ascii = any(ch.isascii() and ch.isalnum() for ch in tok)
        has_foreign = any((not ch.isascii()) and unicodedata.category(ch).startswith("L")
                          and not unicodedata.name(ch, "").startswith("LATIN") for ch in tok)  # accented Latin is not confusable
        if has_ascii and has_foreign:
            return True
    return False


def _intersects(a: BBox, b: BBox) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def assign_ids(raw: list[RawLine], churn: list[BBox]) -> list[OcrLine]:
    ordered = sorted(raw, key=lambda l: (l.bbox[1], l.bbox[0]))
    out: list[OcrLine] = []
    for i, l in enumerate(ordered, start=1):
        out.append(OcrLine(id=f"l{i}", bbox=l.bbox, text=l.text, conf=l.conf, words=l.words,
                           in_churn=any(_intersects(l.bbox, c) for c in churn), confusable=is_confusable(l.text)))
    return out


def run_ocr(run: Run, cfg: Config) -> None:
    inputs = [run.stage1]
    ch = config_hash(cfg, "ocr")
    if run.stage_up_to_date("ocr", inputs, ch):
        log.info("ocr up to date")
        return
    engine = get_engine(cfg.ocr)
    frames = []
    for rec in run.load_stage1():
        t0 = time.time()
        raw = engine.recognize(run.root / rec.png)
        frames.append(OcrFrame(frame=rec.frame, engine=engine.name, settings=engine.settings(),
                               seconds=round(time.time() - t0, 3), lines=assign_ids(raw, rec.churn_regions)))
    write_jsonl(run.ocr, frames)
    run.stage_done("ocr", inputs, ch, frames=len(frames), lines=sum(len(f.lines) for f in frames),
                   seconds=round(sum(f.seconds for f in frames), 1), engine=engine.settings())
