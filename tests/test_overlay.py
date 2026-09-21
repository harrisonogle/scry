from pathlib import Path

from PIL import Image

from scry.config import OverlayConfig
from scry.overlay import draw_overlay, place_label
from scry.schemas import Box


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
    boxes = [Box(id="b1", bbox=(10, 10, 120, 28), text="a", conf=1.0),
             Box(id="b2", bbox=(10, 40, 200, 58), text="b", conf=1.0)]
    out = tmp_path / "o.png"
    clashes = draw_overlay(src, boxes, out, OverlayConfig())
    im = Image.open(out)
    assert im.size == (320, 120) and clashes == 0
    assert im.getpixel((10, 10)) != (10, 10, 10)  # a rectangle was drawn


def test_labels_are_opaque_high_contrast_tags(tmp_path: Path):
    src = tmp_path / "f.png"
    Image.new("RGB", (320, 120), (200, 200, 200)).save(src)
    out = tmp_path / "o.png"
    draw_overlay(src, [Box(id="b7", bbox=(10, 10, 120, 28), text="a", conf=1.0)], out, OverlayConfig())
    im = Image.open(out).convert("RGB")
    tag = {im.getpixel((x, y)) for x in range(122, 140) for y in range(6, 34)}  # the label sits right of the box
    assert (255, 255, 0) in tag  # opaque backing, not blended with the frame
    assert min(sum(c) for c in tag) < 250  # dark digit pixels on it


def _tag_rows(im: Image.Image, xs: range, ys: range) -> set[int]:
    return {y for x in xs for y in ys if im.getpixel((x, y)) == (255, 255, 0)}


def test_draw_overlay_scale_halves_the_image_and_boxes_but_not_the_tags(tmp_path: Path):
    src = tmp_path / "f.png"
    Image.new("RGB", (320, 120), (200, 200, 200)).save(src)
    boxes = [Box(id="b7", bbox=(10, 11, 121, 29), text="a", conf=1.0)]
    full, half = tmp_path / "full.png", tmp_path / "half.png"
    draw_overlay(src, boxes, full, OverlayConfig())
    clashes = draw_overlay(src, boxes, half, OverlayConfig(), scale=0.5)
    im = Image.open(half).convert("RGB")
    assert im.size == (160, 60) and clashes == 0
    # the box is scaled outward: (10,11,121,29) → (5,5,61,15), drawn as an outline through (5,5) and (60,14)
    assert im.getpixel((5, 5)) == (255, 0, 255) and im.getpixel((60, 14)) == (255, 0, 255)
    assert im.getpixel((30, 10)) == (200, 200, 200)  # interior untouched
    # the tag still sits right of the (scaled) box, and it is as tall as at full size: font_size is not scaled
    half_rows = _tag_rows(im, range(63, 90), range(0, 30))
    full_rows = _tag_rows(Image.open(full).convert("RGB"), range(123, 150), range(0, 50))
    assert half_rows and len(half_rows) == len(full_rows)


def test_overlay_of_a_frame_without_boxes_is_the_frame(tmp_path: Path):
    src, out = tmp_path / "f.png", tmp_path / "o.png"
    Image.new("RGB", (64, 32), (9, 9, 9)).save(src)
    assert draw_overlay(src, [], out, OverlayConfig()) == 0
    im = Image.open(out).convert("RGB")
    assert im.size == (64, 32)
    assert {im.getpixel((x, y)) for x in range(64) for y in range(32)} == {(9, 9, 9)}
