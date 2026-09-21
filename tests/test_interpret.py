from scry.interpret import render_diff, render_transition_line, validate_refs
from scry.schemas import DiffOp, Event, FrameRecord, Line, Region, RegionDiff, Transition


def ln(i, text, y, agree=True, vlm=None):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(10, y, 300, y + 18), ocr=text, ocr_conf=1, vlm=vlm or text, agree=agree, in_churn=False)


def frame(n, lines):
    reg = Region(id="r1", kind="window", name="Terminal", app="Windows Terminal", parent=None, bbox=(10, 40, 300, 400), conf=0.9, layout_conf=0.4, lines=lines)
    return FrameRecord(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=True, png="", overlay=None, sha256="", width=1, height=1, regions=[reg])


def test_render_diff_shows_both_readings_and_uncertain_grouping():
    a = frame(1, [ln(1, "PS> gi", 40)])
    b = frame(2, [ln(1, "PS> git status", 40), ln(2, "On branch maln", 60, agree=False, vlm="On branch main")])
    t = Transition(id="T1", from_frame=1, to_frame=2, t=(2.0, 2.1), kind="single",
                   computed_diff={"r1": RegionDiff(from_region="r1", ops=[DiffOp(op="modify", old="PS> gi", new="PS> git status", old_index=0, new_index=0, y=40),
                                                                       DiffOp(op="insert", new="On branch maln", new_index=1, y=60, uncertain=True)])},
                   events=[Event(type="typed", region="r1", text="t status", line="PS> git status", frames=(1, 2))])
    text = render_diff(t, {1: a, 2: b})
    assert "Terminal" in text and "modify" in text and "PS> git status" in text
    assert "OCR: On branch maln" in text and "VLM: On branch main" in text
    assert "grouping uncertain" in text
    assert 'typed "t status"' in render_transition_line(t, {1: a, 2: b})


def test_render_diff_names_the_pane_an_op_came_from():
    nav = Region(id="r2", kind="pane", name="left navigation", app="Azure Portal", parent="r1", bbox=(10, 60, 100, 400), conf=0.9, layout_conf=0.9,
                 lines=[ln(2, "Overview", 60), ln(3, "Node pools", 80)])
    a, b = frame(1, [ln(1, "title", 40)]), frame(2, [ln(1, "title", 40)])
    b.regions.append(nav)
    t = Transition(id="T1", from_frame=1, to_frame=2, t=(2.0, 2.1), kind="single",
                   computed_diff={"r1": RegionDiff(from_region="r1", ops=[DiffOp(op="insert", new="Node pools", new_index=2, y=80, pane="r2"),
                                                                       DiffOp(op="delete", old="gone", old_index=1, y=60, pane="r7")])})
    text = render_diff(t, {1: a, 2: b})
    assert '  insert: "Node pools" [pane: left navigation]' in text
    assert '  delete: "gone" [pane: r7]' in text  # an id the from-frame does not know is shown as is
    assert "readings disagree" not in text


def test_validate_refs_drops_unknown_frames_and_lines():
    a = frame(1, [ln(1, "x", 40)])
    b = frame(2, [ln(1, "x", 40), ln(2, "y", 60)])
    valid, bad = validate_refs(["2:l2", "1:l1", "3:l1", "2:l9", "junk"], [a, b])
    assert valid == ["2:l2", "1:l1"] and bad == 3
