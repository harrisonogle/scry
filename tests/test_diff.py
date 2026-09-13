from vt.config import DiffConfig
from vt.diff import diff_pair, diff_region
from vt.schemas import FrameRecord, Line, Region


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
