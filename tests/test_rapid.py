from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from scry.ocr.rapid import models_available, rebuild_spaces, regroup_words
from scry.schemas import RawWord


def _w(text: str, x0: int, x1: int) -> RawWord:
    return RawWord(text=text, bbox=(x0, 10, x1, 30))


def test_rebuild_spaces_gap_at_or_above_ratio_gets_a_space():
    words = [_w("az", 100, 114), _w("login", 124, 163)]        # 10-px gap on a 20-px line = 0.5
    assert rebuild_spaces(words, 20) == "az login"
    assert rebuild_spaces(words, 20, gap_ratio=0.5) == "az login"    # exactly at the ratio still counts


def test_rebuild_spaces_gap_below_ratio_joins():
    words = [_w("Ci", 100, 114), _w("\\src", 116, 150)]          # 2-px gap on a 20-px line = 0.1
    assert rebuild_spaces(words, 20) == "Ci\\src"
    assert rebuild_spaces(words, 20, gap_ratio=0.05) == "Ci \\src"
    assert rebuild_spaces([_w("ab", 0, 20), _w("cd", 20, 40)], 20) == "abcd"   # touching boxes never get a space


def test_rebuild_spaces_single_word_and_empty():
    assert rebuild_spaces([_w("alone", 5, 50)], 20) == "alone"
    assert rebuild_spaces([], 20) == ""


def test_rebuild_spaces_mixed_gaps():
    words = [_w("PS", 0, 15), _w("C:\\", 25, 60), _w("Users", 61, 100), _w("az", 112, 126)]
    assert rebuild_spaces(words, 22) == "PS C:\\Users az"


def test_regroup_words_merges_pieces_into_tokens():
    pieces = [_w("PS", 0, 15), _w("C:\\", 25, 60), _w("Users", 61, 100)]
    words = regroup_words("PS C:\\Users", pieces)
    assert [w.text for w in words] == ["PS", "C:\\Users"]
    assert words[1].bbox == (25, 10, 100, 30)
    assert regroup_words("PS C:\\User", pieces) is None       # pieces do not spell the tokens: caller keeps pieces


@pytest.mark.skipif(not models_available(), reason="rapidocr or its bundled default models are not available offline")
def test_rapid_reads_terminal_text_with_spaces_and_word_boxes(tmp_path: Path):
    from scry.config import OcrConfig
    from scry.ocr.rapid import RapidEngine

    img = Image.new("RGB", (1920, 200), (12, 12, 12))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
    d.text((40, 80), "PS C:\\Users\\msadmin> az login", fill=(230, 230, 230), font=font)
    png = tmp_path / "t.png"
    img.save(png)

    eng = RapidEngine(OcrConfig(engine="rapid"))
    lines = eng.recognize(png)
    hits = [ln for ln in lines if "az login" in ln.text]
    assert hits, [ln.text for ln in lines]
    ln = hits[0]
    assert ln.words and [w.text for w in ln.words] == ln.text.split()
    assert ln.words[-1].text == "login"
    x0, y0, x1, y1 = ln.bbox
    assert 20 <= x0 <= 60 and 60 <= y0 <= 90 and 300 <= x1 <= 400 and 95 <= y1 <= 120
    assert all(x0 <= w.bbox[0] < w.bbox[2] <= x1 for w in ln.words)
    s = eng.settings()
    assert s["engine"] == "rapidocr" and s["version"].startswith("3.") and s["rec_model"].endswith(".onnx")
    assert s["word_boxes"] is True and s["space_guard_fired"] >= 0


def test_get_engine_knows_only_rapid():
    import pydantic

    from scry.config import OcrConfig
    from scry.ocr import get_engine
    from scry.ocr.rapid import RapidEngine

    with pytest.raises(pydantic.ValidationError):
        OcrConfig(engine="vision")
    if not models_available():
        pytest.skip("rapidocr or its bundled default models are not available offline")
    assert isinstance(get_engine(OcrConfig()), RapidEngine)


@pytest.mark.skipif(not models_available(), reason="rapidocr or its bundled default models are not available offline")
def test_gap_ratio_comes_from_config():
    from scry.config import OcrConfig
    from scry.ocr.rapid import RapidEngine

    assert RapidEngine(OcrConfig(gap_ratio=0.4)).gap_ratio == 0.4
