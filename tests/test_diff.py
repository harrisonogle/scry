from pathlib import Path

import numpy as np
from PIL import Image

from scry.coalesce import tag_trivial
from scry.config import DetectParams, DiffConfig
from scry.diff import PixelSource, diff_pair, diff_region
from scry.schemas import FrameRecord, Line, Region


def ln(i, text, y, agree=True, vlm=None):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(10, y, 300, y + 18), ocr=text, ocr_conf=1, vlm=vlm or text, agree=agree, in_churn=False)


def reg(rid, lines):
    return Region(id=rid, kind="window", name="T", app="T", parent=None, bbox=(10, 40, 300, 400), conf=0.9, layout_conf=0.9, lines=lines)


def frame(n, regions, unassigned=(), settled=True):
    return FrameRecord(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=settled, png="", overlay=None,
                       sha256="", width=1920, height=1080, regions=regions, unassigned_lines=list(unassigned))


def test_diff_region_modify_insert_and_uncertain():
    prev = [ln(1, "PS> gi", 40), ln(2, "old", 60, agree=False, vlm="o1d")]
    cur = [ln(1, "PS> git status", 40), ln(2, "old", 60, agree=False, vlm="o1d"), ln(3, "On branch main", 80)]
    ops = diff_region(prev, cur, DiffConfig())
    assert [o.op for o in ops] == ["modify", "insert"]
    assert ops[0].new == "PS> git status" and ops[0].char_diff == [["=", "PS> gi"], ["+", "t status"]]
    assert ops[1].new == "On branch main" and ops[1].new_index == 2 and ops[1].y == 80


def test_diff_pair_builds_transition_with_r0_and_unsettled_kind():
    a = frame(1, [reg("r1", [ln(1, "a", 40)])], unassigned=[ln(9, "stray", 900)])
    b = frame(2, [reg("r1", [ln(1, "a", 40), ln(2, "b", 60)])], unassigned=[ln(9, "stray2", 900)], settled=False)
    t = diff_pair(a, b, DiffConfig())
    assert t.kind == "unsettled" and t.t == (2.0, 2.1) and (t.from_frame, t.to_frame) == (1, 2)
    assert "r1" in t.computed_diff and t.computed_diff["r1"].from_region == "r1"
    assert [o.op for o in t.computed_diff["r1"].ops] == ["insert"]
    assert [o.op for o in t.computed_diff["r0"].ops] == ["modify"]
    assert t.computed_diff["r1"].ops[0].pane is None  # the unit's own line


def test_ops_carry_the_pane_a_line_came_from():
    def nav(lines):
        return Region(id="r2", kind="pane", name="left navigation", app="T", parent="r1", bbox=(10, 40, 100, 400), conf=0.9, layout_conf=0.9, lines=lines)

    a = frame(1, [reg("r1", [ln(1, "title", 20)]), nav([ln(2, "Overview", 40)])])
    b = frame(2, [reg("r1", [ln(1, "title", 20)]), nav([ln(2, "Overview", 40), ln(3, "Node pools", 60)])])
    c = frame(3, [reg("r1", [ln(1, "title — edited", 20), ln(2, "Overview", 40)])])
    assert [(o.op, o.new, o.new_index, o.pane) for o in diff_pair(a, b, DiffConfig()).computed_diff["r1"].ops] == [("insert", "Node pools", 2, "r2")]
    ops = diff_pair(b, c, DiffConfig()).computed_diff["r1"].ops  # a delete names the from-frame pane; the unit's own line none
    assert [(o.op, o.old, o.pane) for o in ops] == [("modify", "title", None), ("delete", "Node pools", "r2")]


# ---------- §11.2 pixel gate: synthetic PNG pairs, 320×120 white frames with black boxes ----------
def write_png(path: Path, dark: list[tuple[int, int, int, int]]) -> None:
    img = np.full((120, 320), 255, np.uint8)
    for x0, y0, x1, y1 in dark:
        img[y0:y1, x0:x1] = 0
    Image.fromarray(img).convert("RGB").save(path)


def pixel_pair(tmp_path: Path, a_lines, b_lines, b_dark):
    """Frame a is blank; frame b has the given boxes painted. Line boxes are (10, y, 300, y + 18); an unchanged line
    between two changed ones keeps Myers from emitting delete, delete, insert, insert, which pair_modifies does not pair."""
    write_png(tmp_path / "a.png", [])
    write_png(tmp_path / "b.png", b_dark)
    a, b = frame(1, [reg("r1", a_lines)]), frame(2, [reg("r1", b_lines)])
    a.png, b.png = "a.png", "b.png"
    return a, b, PixelSource(tmp_path, DetectParams())


def test_pixel_gate_keeps_the_op_under_changed_pixels_and_vetoes_the_jitter(tmp_path: Path):
    # line 1's box gains 600 px of ink (1.56 % of the frame); line 3 is pixel-identical but OCR read it differently
    a, b, px = pixel_pair(tmp_path, [ln(1, "PS> ", 40), ln(2, "keep", 60), ln(3, "old", 80)], [ln(1, "PS> git", 40), ln(2, "keep", 60), ln(3, "o1d", 80)], [(20, 44, 80, 54)])
    t = diff_pair(a, b, DiffConfig(), px)
    assert t.pixels.changed_fraction == 600 / 38400 and t.pixels.components == [(20, 44, 80, 54)] and t.pixels.vetoed == 1
    assert [(o.op, o.new, o.under_change) for o in t.computed_diff["r1"].ops] == [("modify", "PS> git", True)]
    assert diff_pair(a, b, DiffConfig()).pixels is None  # without a pixel source nothing is measured or vetoed


def test_pixel_gate_leaves_a_transition_above_the_threshold_alone(tmp_path: Path):
    a, b, px = pixel_pair(tmp_path, [ln(1, "PS> ", 40), ln(2, "keep", 60), ln(3, "old", 80)], [ln(1, "PS> git", 40), ln(2, "keep", 60), ln(3, "o1d", 80)],
                          [(20, 44, 80, 54), (0, 110, 320, 120)])  # 9.9 % of the frame changed, 12 px below the last line (outside the 9-px margin)
    t = diff_pair(a, b, DiffConfig(), px)
    assert t.pixels.changed_fraction > 0.05 and len(t.pixels.components) == 2 and t.pixels.vetoed == 0
    assert [(o.new, o.under_change) for o in t.computed_diff["r1"].ops] == [("PS> git", True), ("o1d", False)]


def test_pixel_gate_off_still_marks_under_change(tmp_path: Path):
    a, b, px = pixel_pair(tmp_path, [ln(1, "PS> ", 40), ln(2, "keep", 60), ln(3, "old", 80)], [ln(1, "PS> git", 40), ln(2, "keep", 60), ln(3, "o1d", 80)], [(20, 44, 80, 54)])
    t = diff_pair(a, b, DiffConfig(pixel_gate_max_fraction=0), px)
    assert t.pixels.vetoed == 0 and [o.under_change for o in t.computed_diff["r1"].ops] == [True, False]


def test_transition_with_every_op_vetoed_is_not_trivial(tmp_path: Path):
    a, b, px = pixel_pair(tmp_path, [ln(1, "old", 40)], [ln(1, "o1d", 40)], [(0, 100, 60, 110)])  # ink below every line
    t = tag_trivial(diff_pair(a, b, DiffConfig(), px))
    assert t.computed_diff == {} and t.pixels.vetoed == 1 and t.pixels.changed_fraction > 0
    assert t.kind == "single"  # something visual changed; Stage 5 still looks


def test_pixel_gate_margin_counts_a_change_just_outside_the_line_box(tmp_path: Path):
    """§11.2 (ledger L38): ink 2 px below the line's box (10, 40, 300, 58) is within half a line height (9 px) with the
    default margin and outside it at 0."""
    a, b, px = pixel_pair(tmp_path, [ln(1, "old", 40)], [ln(1, "o1d", 40)], [(20, 60, 80, 64)])
    t = diff_pair(a, b, DiffConfig(), px)
    assert t.pixels.components == [(20, 60, 80, 64)] and t.pixels.vetoed == 0
    assert [(o.op, o.under_change) for o in t.computed_diff["r1"].ops] == [("modify", True)]
    t = diff_pair(a, b, DiffConfig(pixel_gate_margin_lines=0), px)
    assert t.pixels.vetoed == 1 and t.computed_diff == {}
