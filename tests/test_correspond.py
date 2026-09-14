from scry.config import DiffConfig
from scry.correspond import correspond, score
from scry.schemas import FrameRecord, Line, Region


def ln(i, text, y):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(10, y, 300, y + 18), ocr=text, ocr_conf=1, vlm=text, agree=True, in_churn=False)


def reg(rid, name, app, lines, bbox):
    return Region(id=rid, kind="window", name=name, app=app, parent=None, bbox=bbox, conf=0.9, layout_conf=0.9, lines=lines)


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
