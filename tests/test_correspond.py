from scry.config import DiffConfig
from scry.correspond import correspond
from scry.diff import diff_pair
from scry.schemas import FrameRecord, Line, Region


def ln(i, text, y):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(10, y, 300, y + 18), ocr=text, ocr_conf=1, vlm=text, agree=True, in_churn=False)


def reg(rid, name, app, lines, bbox):
    return Region(id=rid, kind="window", name=name, app=app, parent=None, bbox=bbox, conf=0.9, layout_conf=0.9, lines=lines)


def sub(rid, parent, name, lines, bbox, kind="pane"):
    return Region(id=rid, kind=kind, name=name, app="Browser", parent=parent, bbox=bbox, conf=0.9, layout_conf=0.9, lines=lines)


def frame(n, regions):
    return FrameRecord(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=True, png="", overlay=None,
                       sha256="", width=1920, height=1080, regions=regions)


def test_correspondence_by_text_survives_renaming_and_growth():
    a = frame(1, [reg("r1", "Windows Terminal — pwsh", "Windows Terminal", [ln(1, "PS> ls", 40)], (10, 40, 300, 58)),
                  reg("r2", "Azure Portal", "Browser", [ln(5, "Home", 10)], (10, 10, 300, 28))])
    b = frame(2, [reg("r9", "Azure Portal", "Browser", [ln(5, "Home", 10)], (10, 10, 300, 28)),
                  reg("r4", "Terminal", "Windows Terminal", [ln(1, "PS> ls", 40)] + [ln(10 + k, f"line {k}", 60 + 18 * k) for k in range(30)], (10, 40, 300, 600))])
    c = correspond(a, b, DiffConfig())
    assert sorted((m[0], m[1]) for m in c.matched) == [("r1", "r4"), ("r2", "r9")]
    assert c.appeared == [] and c.disappeared == []


def test_empty_regions_match_only_on_app_and_name():
    a = frame(1, [reg("r1", "Toolbar", "App", [], None)])
    b = frame(2, [reg("r2", "Toolbar", "App", [], None), reg("r3", "Other", "App", [], None)])
    c = correspond(a, b, DiffConfig())
    assert [(m[0], m[1]) for m in c.matched] == [("r1", "r2")]
    assert c.appeared == ["r3"]


def test_panes_fold_into_their_window_so_a_resplit_page_is_not_a_change():
    lines = [ln(k, t, 100 + 20 * k) for k, t in enumerate("abcde", start=1)]
    a = frame(1, [reg("r1", "Azure Portal", "Browser", [], (10, 120, 300, 218)),
                  sub("r2", "r1", "top bar", lines[:2], (10, 120, 300, 158)),
                  sub("r3", "r1", "left navigation", [lines[2]], (10, 160, 300, 178)),
                  sub("r4", "r3", "nested list", lines[3:], (10, 180, 300, 218))])
    b = frame(2, [reg("r1", "Azure Portal", "Browser", [], (10, 120, 300, 218)),
                  sub("r2", "r1", "page content", list(reversed(lines)), (10, 120, 300, 218))])
    assert [u.id for u in a.units()] == ["r1"] and a.unit_of("r4") == "r1" and a.unit_of("r9") is None
    assert [l.id for l in a.unit_lines("r1")] == [l.id for l in lines]  # ordered by y centre, whatever the pane order
    assert [(l.id, src) for l, src in a.unit_line_sources("r1")][:3] == [("l1", "r2"), ("l2", "r2"), ("l3", "r3")]
    assert [l.id for l in b.unit_lines("r1")] == [l.id for l in lines]
    c = correspond(a, b, DiffConfig())
    assert [(m[0], m[1]) for m in c.matched] == [("r1", "r1")] and c.appeared == [] and c.disappeared == []
    assert diff_pair(a, b, DiffConfig()).computed_diff == {}


def test_popup_inside_a_window_is_its_own_unit_and_still_appears_and_disappears():
    win = reg("r1", "Azure Portal", "Browser", [ln(1, "Home", 10)], (10, 10, 300, 28))
    tip = sub("r2", "r1", "Cloud Shell tooltip", [ln(9, "Open Cloud Shell", 40)], (10, 40, 300, 58), kind="popup")
    a, b = frame(1, [win]), frame(2, [win, tip])
    assert [u.id for u in b.units()] == ["r1", "r2"] and b.unit_of("r2") == "r2" and b.unit_lines("r1") == win.lines
    c = correspond(a, b, DiffConfig())
    assert [(m[0], m[1]) for m in c.matched] == [("r1", "r1")] and c.appeared == ["r2"] and c.disappeared == []
    assert correspond(b, a, DiffConfig()).disappeared == ["r2"]
