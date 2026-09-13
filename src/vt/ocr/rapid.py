from __future__ import annotations

from pathlib import Path

from vt.config import OcrConfig
from vt.ocr.base import RawLine


class RapidEngine:
    name = "rapidocr"

    def __init__(self, cfg: OcrConfig):
        from rapidocr_onnxruntime import RapidOCR  # optional extra: uv sync --extra rapid

        self._ocr = RapidOCR()
        self.cfg = cfg

    def settings(self) -> dict:
        return {"engine": self.name}

    def recognize(self, png: Path) -> list[RawLine]:
        result, _ = self._ocr(str(png))
        out: list[RawLine] = []
        for quad, text, conf in result or []:
            xs = [int(round(p[0])) for p in quad]
            ys = [int(round(p[1])) for p in quad]
            out.append(RawLine(str(text), float(conf), (min(xs), min(ys), max(xs), max(ys)), None))
        return out
