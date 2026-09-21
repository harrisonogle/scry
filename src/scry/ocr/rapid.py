"""RapidOCR adapter.

rapidocr 3.9 ships its default PP-OCRv6 small detector/recogniser inside the wheel (``rapidocr/models/``), so the
engine works offline; other model variants are downloaded on first use. Per-word boxes come from the recogniser's
CTC columns (``return_word_box=True``): rapidocr splits a line into "pieces" at spaces, at a script change, and at
wide column gaps, and reports the text of each piece without spaces. The pieces are regrouped here into the
whitespace tokens of the final line text, so ``RawLine.words`` holds one entry per whitespace token.

The spacing guard (``rebuild_spaces``) protects against the recogniser dropping spaces: pieces separated by a gap of
at least ``gap_ratio`` times the line height get a space; the rebuilt text replaces the engine's only when it has
strictly more spaces and the same non-space characters. Measured on 18-px terminal text, inter-word gaps are about
10 px (0.45 of the line height) versus 0-3 px inside a word; in small proportional UI text genuine spaces produce
gaps of 0.1-0.35 of the line height, so the guard cannot recover dropped spaces there, but never removes any.
"""
from __future__ import annotations

from importlib import metadata
from pathlib import Path

from scry.config import OcrConfig
from scry.ocr.base import RawLine
from scry.schemas import BBox, RawWord

DEFAULT_GAP_RATIO = 0.25


def rebuild_spaces(words: list[RawWord], line_height: int, gap_ratio: float = DEFAULT_GAP_RATIO) -> str:
    """Join word texts with a single space wherever the horizontal gap between consecutive boxes is at least
    ``gap_ratio * line_height`` (and positive); no space otherwise. Pure; words are taken in the order given."""
    if not words:
        return ""
    threshold = gap_ratio * line_height
    parts = [words[0].text]
    for prev, cur in zip(words, words[1:]):
        gap = cur.bbox[0] - prev.bbox[2]
        if gap > 0 and gap >= threshold:
            parts.append(" ")
        parts.append(cur.text)
    return "".join(parts)


def regroup_words(text: str, pieces: list[RawWord]) -> list[RawWord] | None:
    """Merge consecutive recogniser pieces into the whitespace tokens of ``text`` (bbox = union). None when the
    pieces do not spell the tokens exactly, so the caller can keep the pieces as they are."""
    out: list[RawWord] = []
    i = 0
    for tok in text.split():
        acc = ""
        x0 = y0 = x1 = y1 = None
        while i < len(pieces) and len(acc) < len(tok):
            p = pieces[i]
            acc += p.text
            bx0, by0, bx1, by1 = p.bbox
            x0 = bx0 if x0 is None else min(x0, bx0)
            y0 = by0 if y0 is None else min(y0, by0)
            x1 = bx1 if x1 is None else max(x1, bx1)
            y1 = by1 if y1 is None else max(y1, by1)
            i += 1
        if acc != tok or x0 is None:
            return None
        out.append(RawWord(text=tok, bbox=(x0, y0, x1, y1)))
    return out if i == len(pieces) else None


def _quad_to_bbox(quad, W: int, H: int) -> BBox:
    xs = [float(p[0]) for p in quad]
    ys = [float(p[1]) for p in quad]
    clamp = lambda v, hi: int(min(max(round(v), 0), hi))
    return (clamp(min(xs), W), clamp(min(ys), H), clamp(max(xs), W), clamp(max(ys), H))


def _model_file(section) -> str:
    """File name of the model rapidocr resolves for a Det/Cls/Rec config section (same lookup rapidocr uses)."""
    from rapidocr.inference_engine.base import FileInfo, InferSession

    info = InferSession.get_model_url(FileInfo(engine_type=section.engine_type, ocr_version=section.ocr_version,
                                               task_type=section.task_type, lang_type=section.lang_type,
                                               model_type=section.model_type))
    return Path(str(info["model_dir"])).name


def default_models() -> dict[str, Path]:
    """Paths of the det/cls/rec models rapidocr's default config would load (no engine is built, nothing is
    downloaded). Empty when rapidocr is not importable or its internals changed."""
    try:
        import rapidocr
        from rapidocr.main import DEFAULT_CFG_PATH
        from rapidocr.utils.parse_parameters import ParseParams

        cfg = ParseParams.load(DEFAULT_CFG_PATH)
        root = Path(rapidocr.__file__).resolve().parent / "models"
        if cfg.Global.model_root_dir is not None:
            root = Path(str(cfg.Global.model_root_dir))
        return {task: root / _model_file(cfg[task.capitalize()]) for task in ("det", "cls", "rec")}
    except Exception:
        return {}


def models_available() -> bool:
    """True when rapidocr is importable and its default models are on disk, so building the engine needs no network."""
    paths = default_models()
    return bool(paths) and all(p.is_file() for p in paths.values())


class RapidEngine:
    name = "rapidocr"

    def __init__(self, cfg: OcrConfig, gap_ratio: float | None = None):
        from rapidocr import RapidOCR

        self.cfg = cfg
        self.gap_ratio = float(gap_ratio if gap_ratio is not None else cfg.gap_ratio)
        # use_cls off: screens are never rotated and the orientation classifier flipped ~3 % of lines into garbage;
        # rec_batch_num 1: PP-OCR pads a batch to its widest crop and the space decision depends on that width,
        # so the same pixels read differently next to different neighbours (ledger L43).
        self._ocr = RapidOCR(params={"Global.log_level": "warning", "Global.use_cls": False, "Rec.rec_batch_num": 1})
        self.space_guard_fired = 0
        self.version = metadata.version("rapidocr")
        try:
            self.runtime = "onnxruntime " + metadata.version("onnxruntime")
        except metadata.PackageNotFoundError:
            self.runtime = str(self._ocr.cfg.Rec.engine_type.value)
        rc = self._ocr.cfg
        self.models = {}
        for task in ("det", "cls", "rec"):
            sec = rc[task.capitalize()]
            try:
                self.models[task] = _model_file(sec)
            except Exception:
                self.models[task] = f"{sec.ocr_version.value}_{task}_{sec.model_type.value}"
        self.rec_lang = str(rc.Rec.lang_type.value)

    def settings(self) -> dict:
        return {"engine": self.name, "version": self.version, "runtime": self.runtime,
                "det_model": self.models["det"], "rec_model": self.models["rec"], "cls_model": self.models["cls"],
                "rec_lang": self.rec_lang, "word_boxes": True, "use_cls": False, "rec_batch_num": 1, "gap_ratio": self.gap_ratio,
                "space_guard_fired": self.space_guard_fired}

    def recognize(self, png: Path) -> list[RawLine]:
        try:
            res = self._ocr(str(png), return_word_box=True)
            word_results = res.word_results or ()
        except IndexError:  # rapidocr's word-box bookkeeping desynced from its line list; keep the lines at least
            res = self._ocr(str(png), return_word_box=False)
            word_results = ()
        if res.boxes is None or res.txts is None or len(res.boxes) == 0:
            return []
        H, W = res.img.shape[:2]
        aligned = len(word_results) == len(res.boxes)
        out: list[RawLine] = []
        for i, (quad, text, conf) in enumerate(zip(res.boxes, res.txts, res.scores)):
            bbox = _quad_to_bbox(quad, W, H)
            text = str(text)
            words: list[RawWord] | None = None
            if aligned:
                pieces = [RawWord(text=str(w), bbox=_quad_to_bbox(q, W, H)) for w, _, q in word_results[i]
                          if q is not None and str(w)]
                if pieces:
                    text, words = self._guard(text, pieces, bbox)
            out.append(RawLine(text, float(conf), bbox, words or None))
        return out

    def _guard(self, text: str, pieces: list[RawWord], bbox: BBox) -> tuple[str, list[RawWord]]:
        rebuilt = rebuild_spaces(pieces, bbox[3] - bbox[1], self.gap_ratio)
        if rebuilt.count(" ") > text.count(" ") and "".join(rebuilt.split()) == "".join(text.split()):
            text = rebuilt
            self.space_guard_fired += 1
        return text, regroup_words(text, pieces) or pieces
