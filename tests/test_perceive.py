from scry.perceive import repair
from scry.schemas import VlmPerception, VlmRegion


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


def test_build_blocks_lists_mark_boxes_only_when_asked(tmp_path):
    from PIL import Image

    from scry.perceive import build_blocks, prompt_version
    from scry.schemas import OcrFrame, OcrLine, Stage1Record
    png = tmp_path / "f.png"
    Image.new("RGB", (8, 8)).save(png)
    rec = Stage1Record(video_id="v", frame=3, t_change=0, t_settled=1.0, t_end=2, settled=True, width=8, height=8, sha256="x", png="f.png")
    ocr = OcrFrame(frame=3, engine="e", settings={}, seconds=0, lines=[OcrLine(id="l1", bbox=(1, 2, 3, 4), text="a", conf=1.0),
                                                                     OcrLine(id="l2", bbox=(5, 6, 7, 8), text="b", conf=1.0)])
    plain = [b["text"] for b in build_blocks(rec, ocr, png, png) if b["type"] == "text"]
    coords = [b["text"] for b in build_blocks(rec, ocr, png, png, coords=True) if b["type"] == "text"]
    assert any(t == "Marks present: l1, l2." for t in plain)
    assert any("l1: 1,2,3,4; l2: 5,6,7,8" in t for t in coords)
    assert prompt_version(False) != prompt_version(True)  # distinct cache keys for the two prompts
