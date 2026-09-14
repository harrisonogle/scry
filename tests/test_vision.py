import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Apple Vision is macOS only")


def test_vision_reads_terminal_text(tmp_path: Path):
    from scry.config import OcrConfig
    from scry.ocr.vision import VisionEngine

    img = Image.new("RGB", (900, 120), (12, 12, 12))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
    d.text((20, 20), "PS C:\\src> git status", fill=(230, 230, 230), font=font)
    d.text((20, 60), "az aks create --resource-group rg-demo --name aks-demo-01", fill=(230, 230, 230), font=font)
    png = tmp_path / "t.png"
    img.save(png)
    eng = VisionEngine(OcrConfig())
    lines = sorted(eng.recognize(png), key=lambda l: (l.bbox[1], l.bbox[0]))
    assert lines[0].text == "PS C:\\src> git status"
    x0, y0, x1, y1 = lines[0].bbox
    assert 10 <= x0 <= 30 and 10 <= y0 <= 30 and 200 <= x1 <= 280 and 36 <= y1 <= 50
    assert lines[0].words and lines[0].words[0].text == "PS"
    # Vision may split the long line into fragments and has been seen to read "--" as "-" (design §5.4):
    joined = " ".join(l.text for l in lines[1:])
    assert "rg-demo" in joined and "aks-demo-01" in joined
    assert eng.settings()["language_correction"] is False
