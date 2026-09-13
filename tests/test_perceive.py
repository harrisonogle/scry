from vt.perceive import repair
from vt.schemas import VlmPerception, VlmRegion


def region(rid, rows, lines, parent=None):
    return VlmRegion(id=rid, kind="window", name=rid, app="x", parent=parent, conf=0.9, rows=rows, vlm_lines=lines)


def test_repair_missing_duplicate_unknown_and_lengths():
    out = VlmPerception(
        regions=[region("r1", [["l1"], ["l2", "l9"]], ["a", "b"]), region("r2", [["l2"], ["l3"]], ["c"], parent="zz")],
        focused_region="r7", focused_conf=0.5, description="", unassigned_line_ids=[])
    fixed, n = repair(out, ["l1", "l2", "l3", "l4"])
    r1, r2 = fixed.regions
    assert r1.rows == [["l1"], ["l2"]] and r1.vlm_lines == ["a", "b"]   # unknown l9 dropped
    assert r2.rows == [] and r2.vlm_lines == []                          # duplicate l2 emptied its row; l3's row lost its text
    assert fixed.unassigned_line_ids == ["l3", "l4"]                     # l3 released by the length repair; l4 was missing
    assert fixed.focused_region is None and r2.parent is None
    assert n == 7


def test_repair_breaks_parent_cycles():
    out = VlmPerception(regions=[region("r1", [["l1"]], ["a"], parent="r2"), region("r2", [["l2"]], ["b"], parent="r1"),
                                 region("r3", [["l3"]], ["c"], parent="r3")],
                        focused_region=None, focused_conf=0.0, description="", unassigned_line_ids=[])
    fixed, n = repair(out, ["l1", "l2", "l3"])
    parents = [r.parent for r in fixed.regions]
    assert parents.count(None) >= 2 and n >= 2
