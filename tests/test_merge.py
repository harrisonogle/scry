from scry.config import MergeConfig
from scry.merge import agreement, build_region_lines, caret_region, combine_focus, layout_conf, merge_frame
from scry.schemas import (Line, OcrFrame, OcrLine, PerceptionRecord, Region, Stage1Record, VlmPerception, VlmRegion)

CFG = MergeConfig()


def ocr(id, x0, y0, x1, y1, text):
    return OcrLine(id=id, bbox=(x0, y0, x1, y1), text=text, conf=1.0)


def test_rows_join_fragments_and_reject_implausible_rows():
    by_id = {l.id: l for l in [ocr("l1", 10, 40, 60, 58, "PS C:\\src>"), ocr("l2", 70, 40, 200, 58, "git status"),
                                ocr("l3", 10, 60, 120, 78, "On branch main"), ocr("l4", 10, 400, 80, 418, "far away")]}
    vr = VlmRegion(id="r1", kind="window", name="Terminal", app="Windows Terminal", parent=None, conf=0.9,
                   rows=[["l1", "l2"], ["l3"], ["l4", "l1"], []],
                   vlm_lines=["PS C:\\src> git status", "On branch main", "nonsense", "nothing to commit"])
    lines, rejected, pending = build_region_lines(vr, by_id, CFG)
    assert lines[0].marks == ["l1", "l2"] and lines[0].ocr == "PS C:\\src> git status" and lines[0].bbox == (10, 40, 200, 58)
    assert lines[0].agree is True
    assert lines[1].agree is True
    assert rejected == 1
    assert [l.row_rejected for l in lines].count(True) == 1  # l4 split out; the duplicate l1 was already consumed by row 0
    assert pending == [(2, "nonsense")]
    vlm_only = [l for l in lines if l.marks == []]
    assert len(vlm_only) == 1 and vlm_only[0].vlm == "nothing to commit" and vlm_only[0].bbox is None and vlm_only[0].agree is None


def test_agreement_glyph_strip_and_short_lines():
    assert agreement("P Search resources", "Search resources", CFG) == (True, "P")
    assert agreement("Learn more B'", "Learn more", CFG) == (True, "B'")
    assert agreement("• Zone 1", "Zone 1", CFG) == (True, "•")
    assert agreement("git status", "git status", CFG) == (True, None)
    assert agreement("On branch maln", "On branch main", CFG) == (False, None)


def _line(i, bbox, text):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=bbox, ocr=text, ocr_conf=1, vlm=text, agree=True, in_churn=False)


def test_layout_conf_does_not_penalize_foreground_over_background():
    term = Region(id="r1", kind="window", name="Terminal", app="T", parent=None, bbox=(12, 40, 540, 78), conf=0.95, layout_conf=0,
                  occludes=["r2"], lines=[_line(3, (12, 40, 300, 58), "a"), _line(4, (12, 60, 540, 78), "b")])
    browser = Region(id="r2", kind="window", name="Portal", app="B", parent=None, bbox=(0, 0, 1920, 1080), conf=0.9, layout_conf=0,
                     lines=[_line(1, (64, 17, 181, 33), "Azure"), _line(9, (20, 1000, 200, 1018), "z")])
    nav = Region(id="r5", kind="pane", name="nav", app="B", parent="r2", bbox=(20, 40, 200, 58), conf=0.9, layout_conf=0,
                 lines=[_line(6, (20, 42, 200, 58), "Overview")])  # behind the terminal: occlusion extends to the browser's panes
    assert layout_conf(term, [term, browser, nav]) >= 0.9
    # interleaved text from an unrelated region on the same rows is penalized
    other = Region(id="r3", kind="pane", name="x", app="B", parent=None, bbox=(280, 42, 500, 58), conf=0.9, layout_conf=0,
                   lines=[_line(7, (280, 42, 500, 58), "q")])
    assert layout_conf(term, [term, browser, other]) <= 0.7
    single = Region(id="r4", kind="pane", name="s", app="B", parent=None, bbox=(0, 0, 10, 10), conf=0.95, layout_conf=0,
                    lines=[_line(8, (0, 0, 10, 10), "s")])
    assert layout_conf(single, [single]) <= 0.6
    # a window whose text lives in its panes is not "scattered"
    win = Region(id="r6", kind="window", name="Editor", app="E", parent=None, bbox=(0, 0, 800, 600), conf=0.95, layout_conf=0,
                 lines=[_line(10, (0, 0, 300, 18), "title")])
    pane = Region(id="r7", kind="pane", name="editor", app="E", parent="r6", bbox=(0, 30, 800, 600), conf=0.9, layout_conf=0,
                  lines=[_line(11 + k, (0, 30 + 18 * k, 800, 48 + 18 * k), f"line {k}") for k in range(30)])
    assert layout_conf(win, [win, pane]) >= 0.9


def test_caret_region_and_focus_combination():
    term = Region(id="r1", kind="window", name="T", app="T", parent=None, bbox=(12, 40, 640, 300), conf=0.9, layout_conf=0.9,
                  lines=[_line(3, (12, 40, 300, 58), "a")])
    pane = Region(id="r3", kind="pane", name="p", app="T", parent="r1", bbox=(12, 60, 300, 78), conf=0.9, layout_conf=0.9,
                  lines=[_line(4, (12, 60, 300, 78), "b")])
    assert caret_region((318, 41, 320, 59), [term, pane]) == "r1"    # inside, compared at root-window level
    assert caret_region((20, 90, 22, 108), [term, pane]) == "r1"     # just below the pane: within two line heights
    assert caret_region((900, 900, 902, 918), [term, pane]) is None
    assert combine_focus("r1", None, "r1", 0.8) == ("r1", 0.9, ["caret", "vlm"])
    assert combine_focus("r1", None, None, 0.0) == ("r1", 0.7, ["caret"])
    assert combine_focus("r1", None, "r2", 0.8) == ("r1", 0.6, ["caret", "vlm:r2@0.3"])
    assert combine_focus("r1", "r2", "r2", 0.8) == ("r2", 0.6, ["retro", "vlm"])
    assert combine_focus(None, None, "r2", 0.8) == ("r2", 0.5, ["vlm"])
    assert combine_focus(None, None, None, 0.0) == (None, None, [])


def test_merge_frame_end_to_end_with_perception_error_falls_back_to_ocr_only():
    s1 = Stage1Record(video_id="v", frame=3, t_change=1, t_settled=1.2, t_end=5, settled=True, width=100, height=100, sha256="x", png="frames/00003.png")
    of = OcrFrame(frame=3, engine="e", lines=[ocr("l1", 0, 0, 50, 10, "hello"), ocr("l2", 0, 20, 50, 30, "world")])
    perc = PerceptionRecord(frame=3, model="m", prompt_version="v", output=None, error="refusal")
    fr = merge_frame(s1, of, perc, CFG)
    assert fr.error == "refusal" and len(fr.regions) == 1 and [l.ocr for l in fr.regions[0].lines] == ["hello", "world"]
    assert fr.regions[0].kind == "unknown"
