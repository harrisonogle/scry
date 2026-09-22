from pathlib import Path

import numpy as np
from PIL import Image

from scry.config import DetectParams
from scry.detect import change_map, label_components
from scry.schemas import Box, Frame
from scry.track.pixels import PixelDiff, PixelSource, grow, margin_px, touched, touched_by, touched_by_rect


def _diff(prev: np.ndarray, cur: np.ndarray) -> PixelDiff:
    changed = change_map(prev, cur, 12)
    labels, comps = label_components(changed, 8)
    return PixelDiff(labels, comps, round(float(changed.mean()), 6))


def _two_glyphs() -> PixelDiff:
    prev = np.zeros((60, 160), np.uint8)
    cur = prev.copy()
    cur[20:30, 40:41] = 255
    cur[20:30, 100:106] = 255
    for x in (5, 30, 55):
        cur[10, x] = 40
    return _diff(prev, cur)


def test_touch_margin_edges():
    d = _two_glyphs()
    box = (50, 18, 90, 32)
    assert touched(box, d, 9) is False  # grown (41,9,99,41): the stem at x = 40 is outside
    assert touched(box, d, 10) is True  # grown (40,8,100,42): x = 40 is inside; x = 100 is not, x1 is exclusive
    assert touched_by(box, d, 10) == {1}


def test_touch_is_on_pixels_not_rectangles():
    prev = np.zeros((60, 160), np.uint8)
    cur = prev.copy()
    cur[10:50, 20:21] = 255
    cur[10:50, 139:140] = 255
    cur[10:11, 20:140] = 255
    cur[49:50, 20:140] = 255
    d = _diff(prev, cur)
    assert len(d.components) == 1 and d.components[0].bbox == (20, 10, 140, 50) and d.components[0].area == 316
    box = (60, 25, 100, 35)
    assert touched(box, d, 5) is False
    assert touched_by_rect(box, d, 5) is True


def test_grow_clips():
    assert grow((2, 3, 10, 12), 5, (60, 160)) == (0, 0, 15, 17)


def _boxes(heights: list[int]) -> list[Box]:
    return [Box(id=f"b{i}", bbox=(0, 0, 10, h), text="x", conf=1.0) for i, h in enumerate(heights, start=1)]


def test_margin_px():
    assert margin_px(_boxes([10, 20]), _boxes([30]), 0.5) == 10
    assert margin_px(_boxes([21]), [], 0.5) == 11
    assert margin_px([], [], 0.5) == 0
    assert margin_px(_boxes([10, 20]), _boxes([30]), 0) == 0


def _frame(n: int, png: str, w: int = 60, h: int = 40) -> Frame:
    return Frame(video_id="v", frame=n, t_change=n, t_settled=n, t_end=n + 1, settled=True, width=w, height=h, sha256="", png=png)


def test_pixel_source_diff_and_degenerate(tmp_path: Path):
    black = np.zeros((40, 60), np.uint8)
    lit = black.copy()
    lit[10:20, 10:30] = 255
    Image.fromarray(black, "L").save(tmp_path / "a.png")
    Image.fromarray(lit, "L").save(tmp_path / "b.png")
    Image.fromarray(np.zeros((20, 30), np.uint8), "L").save(tmp_path / "small.png")
    src = PixelSource(tmp_path, DetectParams())
    d = src.diff(_frame(0, "a.png"), _frame(1, "b.png"))
    assert len(d.components) == 1 and d.components[0].bbox == (10, 10, 30, 20) and d.components[0].area == 200
    assert d.changed_fraction == 0.083333
    assert src.diff(_frame(0, "a.png"), _frame(2, "missing.png")) is None
    assert src.diff(_frame(0, "a.png"), _frame(3, "small.png", 30, 20)) is None
