from pathlib import Path

from PIL import Image

from vt.config import OverlayConfig
from vt.overlay import draw_overlay, place_label
from vt.schemas import OcrLine


def test_place_label_prefers_right_then_left_then_above_then_below():
    W, H = 400, 200
    box = (100, 50, 200, 66)
    lw, lh = 14, 10
    # nothing around: right of the box
    x, y, clash = place_label(box, lw, lh, [box], W, H)
    assert (x, y, clash) == (202, 53, False)
    # a box immediately right → left gutter
    right = (202, 50, 300, 66)
    x, y, clash = place_label(box, lw, lh, [box, right], W, H)
    assert (x, y, clash) == (84, 53, False)
    # boxes right and left → above
    left = (60, 50, 98, 66)
    x, y, clash = place_label(box, lw, lh, [box, right, left], W, H)
    assert (x, y, clash) == (100, 39, False)
    # right, left, above and below occupied → least-overlap fallback, clash counted
    above = (100, 34, 200, 49)
    below = (100, 67, 200, 83)
    x, y, clash = place_label(box, lw, lh, [box, right, left, above, below], W, H)
    assert clash is True


def test_place_label_never_leaves_the_image():
    x, y, clash = place_label((0, 0, 50, 16), 14, 10, [(0, 0, 50, 16)], 400, 200)
    assert x >= 0 and y >= 0


def test_draw_overlay_keeps_dimensions(tmp_path: Path):
    src = tmp_path / "f.png"
    Image.new("RGB", (320, 120), (10, 10, 10)).save(src)
    lines = [OcrLine(id="l1", bbox=(10, 10, 120, 28), text="a", conf=1.0),
             OcrLine(id="l2", bbox=(10, 40, 200, 58), text="b", conf=1.0)]
    out = tmp_path / "o.png"
    clashes = draw_overlay(src, lines, out, OverlayConfig())
    im = Image.open(out)
    assert im.size == (320, 120) and clashes == 0
    assert im.getpixel((10, 10)) != (10, 10, 10)  # a rectangle was drawn
