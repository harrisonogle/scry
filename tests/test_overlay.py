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
    lines = [Box(id="b1", bbox=(10, 10, 120, 28), text="a", conf=1.0),
         Box(id="b2", bbox=(10, 40, 200, 58), text="b", conf=1.0)]
    out = tmp_path / "o.png"
    clashes = draw_overlay(src, lines, out, OverlayConfig())
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
    lines = [Box(id="b7", bbox=(10, 11, 121, 29), text="a", conf=1.0)]
    full, half = tmp_path / "full.png", tmp_path / "half.png"
    draw_overlay(src, lines, full, OverlayConfig())
    clashes = draw_overlay(src, lines, half, OverlayConfig(scale=0.5))
    im = Image.open(half).convert("RGB")
    assert im.size == (160, 60) and clashes == 0
    # the box is scaled outward: (10,11,121,29) → (5,5,61,15), drawn as an outline through (5,5) and (60,14)
    assert im.getpixel((5, 5)) == (255, 0, 255) and im.getpixel((60, 14)) == (255, 0, 255)
    assert im.getpixel((30, 10)) == (200, 200, 200)  # interior untouched
    # the tag still sits right of the (scaled) box, and it is as tall as at full size: font_size is not scaled
    half_rows = _tag_rows(im, range(63, 90), range(0, 30))
    full_rows = _tag_rows(Image.open(full).convert("RGB"), range(123, 150), range(0, 50))
    assert half_rows and len(half_rows) == len(full_rows)


def test_overlay_scale_is_bounded():
    import pytest
    from pydantic import ValidationError
    assert OverlayConfig().scale == 1.0
    for bad in (0, -0.5, 1.5):
        with pytest.raises(ValidationError):
            OverlayConfig(scale=bad)


def _bg(tmp_path: Path, color=(10, 10, 10)) -> Path:
    src = tmp_path / "f.png"
    Image.new("RGB", (320, 120), color).save(src)
    return src


def test_mask_opaque_fills_the_box_grey_and_keeps_the_outside_tag(tmp_path: Path):
    from scry.overlay import MASK_FILL
    src, out = _bg(tmp_path), tmp_path / "o.png"
    clashes = draw_overlay(src, [Box(id="b7", bbox=(10, 10, 120, 28), text="Hello", conf=1.0)], out, OverlayConfig(mask="opaque"))
    im = Image.open(out).convert("RGB")
    assert clashes == 0 and im.size == (320, 120)
    assert im.getpixel((60, 19)) == MASK_FILL[:3] and im.getpixel((118, 26)) == MASK_FILL[:3]  # interior covered
    assert im.getpixel((10, 10)) == (255, 0, 255) and im.getpixel((119, 27)) == (255, 0, 255)  # outline still drawn
    assert im.getpixel((200, 100)) == (10, 10, 10) and im.getpixel((9, 19)) == (10, 10, 10)    # outside untouched
    tag = {im.getpixel((x, y)) for x in range(122, 140) for y in range(6, 34)}
    assert (255, 255, 0) in tag and min(sum(c) for c in tag) < 250  # the tag sits right of the box, as with no mask


def test_mask_opaque_label_draws_the_tag_inside_the_box_and_no_outside_tag(tmp_path: Path):
    from scry.overlay import MASK_FILL
    src, out = _bg(tmp_path), tmp_path / "o.png"
    clashes = draw_overlay(src, [Box(id="b7", bbox=(10, 10, 120, 28), text="Hello", conf=1.0)], out, OverlayConfig(mask="opaque_label"))
    im = Image.open(out).convert("RGB")
    assert clashes == 0
    left = {im.getpixel((x, y)) for x in range(11, 30) for y in range(11, 27)}    # the digit: black on the grey, left-aligned
    right = {im.getpixel((x, y)) for x in range(80, 119) for y in range(11, 27)}  # the rest of the box: plain grey
    assert (0, 0, 0) in left and MASK_FILL[:3] in left and right == {MASK_FILL[:3]}
    assert (255, 255, 0) not in {im.getpixel((x, y)) for x in range(im.width) for y in range(im.height)}  # no outside tag
    assert im.getpixel((200, 100)) == (10, 10, 10)


def test_mask_rendered_sets_white_boxes_with_dark_text_clipped_to_the_box(tmp_path: Path):
    src, out = _bg(tmp_path), tmp_path / "o.png"
    lines = [Box(id="b1", bbox=(10, 10, 120, 28), text="Hello", conf=1.0),
         Box(id="b2", bbox=(10, 50, 60, 68), text="a very long line that cannot possibly fit", conf=1.0)]
    draw_overlay(src, lines, out, OverlayConfig(mask="rendered"))
    im = Image.open(out).convert("RGB")
    box = {im.getpixel((x, y)) for x in range(11, 119) for y in range(11, 27)}
    assert (255, 255, 255) in box and (0, 0, 0) in box                # white fill, dark glyphs
    assert (10, 10, 10) not in box
    assert im.getpixel((200, 100)) == (10, 10, 10) and im.getpixel((9, 19)) == (10, 10, 10)
    tag = {im.getpixel((x, y)) for x in range(122, 140) for y in range(6, 34)}
    assert (255, 255, 0) in tag                                        # the outside tag stays
    # the long line is shrunk then clipped: nothing spills past the box's right edge (its tag starts at x = 62)
    assert {im.getpixel((61, y)) for y in range(50, 68)} == {(10, 10, 10)}
    assert (255, 255, 255) not in {im.getpixel((x, y)) for x in range(61, 120) for y in range(46, 72)}
    assert min(sum(c) for c in {im.getpixel((x, y)) for x in range(11, 59) for y in range(51, 67)}) < 300  # dark 6-pt glyphs inside


def test_mask_image_masks_the_clean_frame_over_the_overlay_rectangles(tmp_path: Path):
    from scry.overlay import MASK_FILL, mask_image, scale_image
    src, out = _bg(tmp_path), tmp_path / "o.png"
    lines = [Box(id="b7", bbox=(10, 11, 121, 29), text="Hello", conf=1.0)]
    for mode in ("opaque", "opaque_label", "rendered"):
        cfg = OverlayConfig(mask=mode, scale=0.5)
        draw_overlay(src, lines, out, cfg)
        ov = Image.open(out).convert("RGB")
        clean = mask_image(scale_image(Image.open(src).convert("RGBA"), 0.5), lines, cfg).convert("RGB")
        assert clean.size == ov.size == (160, 60)
        # the box scales to (5,5,61,15); inside the outline the clean frame and the overlay carry the same pixels,
        # except where opaque_label wrote its digit
        interior = [(x, y) for x in range(6, 60) for y in range(6, 14)]
        same = [clean.getpixel(p) == ov.getpixel(p) for p in interior]
        assert all(same) if mode != "opaque_label" else (sum(same) > len(same) // 2 and clean.getpixel((30, 10)) == MASK_FILL[:3])
        assert clean.getpixel((4, 10)) == (10, 10, 10) and clean.getpixel((61, 10)) == (10, 10, 10)  # up to the box edges
        assert clean.getpixel((5, 5)) != (255, 0, 255)  # no outline, no tag on the clean frame
    plain = mask_image(Image.open(src).convert("RGBA"), lines, OverlayConfig()).convert("RGB")
    assert plain.getpixel((60, 20)) == (10, 10, 10)


def test_overlay_mask_is_validated():
    import pytest
    from pydantic import ValidationError
    assert OverlayConfig().mask == "none"
    with pytest.raises(ValidationError):
        OverlayConfig(mask="blur")
