from __future__ import annotations

from vt.config import OcrConfig
from vt.ocr.base import OcrEngine, RawLine  # noqa: F401


def get_engine(cfg: OcrConfig) -> OcrEngine:
    if cfg.engine == "vision":
        from vt.ocr.vision import VisionEngine

        return VisionEngine(cfg)
    if cfg.engine == "rapid":
        from vt.ocr.rapid import RapidEngine

        return RapidEngine(cfg)
    raise ValueError(f"unknown OCR engine {cfg.engine}")
