from __future__ import annotations

import re
from pathlib import Path

from vt.config import OcrConfig
from vt.ocr.base import RawLine
from vt.schemas import BBox, RawWord


def _to_pixels(rect, W: int, H: int) -> BBox:
    x0 = rect.origin.x * W
    y0 = (1.0 - rect.origin.y - rect.size.height) * H
    x1 = (rect.origin.x + rect.size.width) * W
    y1 = (1.0 - rect.origin.y) * H
    clamp = lambda v, hi: int(min(max(round(v), 0), hi))
    return (clamp(x0, W), clamp(y0, H), clamp(x1, W), clamp(y1, H))


class VisionEngine:
    name = "apple-vision"

    def __init__(self, cfg: OcrConfig):
        import Foundation  # noqa: F401  (PyObjC)
        import Quartz
        import Vision

        self._F, self._Q, self._V = Foundation, Quartz, Vision
        self.cfg = cfg
        self._revision = int(self._make_request().revision())

    def _make_request(self):
        V = self._V
        req = V.VNRecognizeTextRequest.alloc().init()
        req.setRecognitionLevel_(V.VNRequestTextRecognitionLevelAccurate)
        req.setUsesLanguageCorrection_(bool(self.cfg.language_correction))
        req.setRecognitionLanguages_(list(self.cfg.languages))
        req.setAutomaticallyDetectsLanguage_(False)
        req.setMinimumTextHeight_(float(self.cfg.minimum_text_height))
        return req

    def settings(self) -> dict:
        return {"engine": self.name, "revision": self._revision, "level": "accurate",
                "language_correction": bool(self.cfg.language_correction), "languages": list(self.cfg.languages),
                "minimum_text_height": float(self.cfg.minimum_text_height)}

    def recognize(self, png: Path) -> list[RawLine]:
        F, Q = self._F, self._Q
        src = Q.CGImageSourceCreateWithURL(F.NSURL.fileURLWithPath_(str(png)), None)
        cg = Q.CGImageSourceCreateImageAtIndex(src, 0, None)
        if cg is None:
            raise RuntimeError(f"cannot load {png}")
        W, H = Q.CGImageGetWidth(cg), Q.CGImageGetHeight(cg)
        req = self._make_request()
        handler = self._V.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, None)
        ok, err = handler.performRequests_error_([req], None)
        if not ok:
            raise RuntimeError(f"Vision failed on {png}: {err}")
        out: list[RawLine] = []
        for obs in req.results() or []:
            cands = obs.topCandidates_(1)
            if not cands:
                continue
            cand = cands[0]
            text = str(cand.string())
            bbox = _to_pixels(obs.boundingBox(), W, H)
            words: list[RawWord] = []
            for m in re.finditer(r"\S+", text):
                rect_obs, _ = cand.boundingBoxForRange_error_(F.NSMakeRange(m.start(), m.end() - m.start()), None)
                if rect_obs is not None:
                    words.append(RawWord(text=m.group(), bbox=_to_pixels(rect_obs.boundingBox(), W, H)))
            out.append(RawLine(text, float(cand.confidence()), bbox, words or None))
        return out
