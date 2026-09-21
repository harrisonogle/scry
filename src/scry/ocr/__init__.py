from __future__ import annotations

from scry.config import ReadConfig
from scry.ocr.base import OcrEngine, RawLine  # noqa: F401


def get_engine(cfg: ReadConfig) -> OcrEngine:
    if cfg.engine == "rapid":
        from scry.ocr.rapid import RapidEngine

        return RapidEngine(cfg)
    raise ValueError(f"unknown OCR engine {cfg.engine}")
