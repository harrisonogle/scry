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


def _tags_overlap(a, b, lw, lh) -> bool:
    return a[0] < b[0] + lw and b[0] < a[0] + lw and a[1] < b[1] + lh and b[1] < a[1] + lh


def test_place_label_avoids_the_tags_already_placed():
    W, H, lw, lh = 400, 200, 14, 10
    a, b = (100, 50, 200, 66), (218, 50, 300, 66)  # b's left gutter is where a's tag sits: right of a
    ta = place_label(a, lw, lh, [a, b], W, H)
    assert ta == (202, 53, False)
    wall = (302, 40, 380, 76)  # b cannot go right, so without `placed` it takes the left gutter, on top of a's tag
    assert place_label(b, lw, lh, [a, b, wall], W, H)[:2] == (202, 53)
    tb = place_label(b, lw, lh, [a, b, wall], W, H, [(ta[0], ta[1], ta[0] + lw, ta[1] + lh)])
    assert tb == (218, 39, False)  # above instead, and no clash
    assert not _tags_overlap(ta, tb, lw, lh)


def test_draw_overlay_hands_each_tag_the_tags_before_it(tmp_path: Path):
    src, out = tmp_path / "f.png", tmp_path / "o.png"
    Image.new("RGB", (480, 120), (200, 200, 200)).save(src)
    boxes = [Box(id=f"b{i}", bbox=bb, text="t", conf=1.0)  # the same arrangement as above
             for i, bb in enumerate([(100, 50, 200, 66), (218, 50, 300, 66), (302, 40, 380, 76)], start=1)]
    assert draw_overlay(src, boxes, out, OverlayConfig()) == 0
    im = Image.open(out).convert("RGB")
    assert im.getpixel((218, 48)) == (255, 255, 0)  # b2's tag went above its box, not onto b1's tag in the gutter


def test_a_tag_that_can_only_sit_on_another_tag_is_a_clash():
    W, H, lw, lh = 400, 200, 14, 10
    box = (100, 50, 200, 66)
    placed = [(202, 53, 216, 63), (84, 53, 98, 63), (100, 39, 114, 49), (100, 67, 114, 77)]  # a tag in every slot
    x, y, clash = place_label(box, lw, lh, [box], W, H, placed)
    assert clash is True and (x, y) == (202, 53)  # the earliest among equally bad slots
