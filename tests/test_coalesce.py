from scry.coalesce import coalesce, merge_transients, retrospective_focus, tag_trivial
from scry.config import DiffConfig
from scry.diff import diff_pair
from scry.schemas import FrameRecord, Line, PixelChange, Region

CFG = DiffConfig()


def ln(i, text, y):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(10, y, 300, y + 18), ocr=text, ocr_conf=1, vlm=text, agree=True, in_churn=False)


def term(lines, rid="r1"):
    return Region(id=rid, kind="window", name="Terminal", app="T", parent=None, bbox=(10, 40, 300, 400), conf=0.9, layout_conf=0.9, lines=lines)


def frame(n, regions, t0=None):
    t0 = n * 2.0 if t0 is None else t0
    return FrameRecord(video_id="v", frame=n, t_change=t0, t_settled=t0 + 0.2, t_end=t0 + 2.0, settled=True, png="", overlay=None,
                       sha256="", width=1920, height=1080, regions=regions)


def singles(frames):
    ts = [diff_pair(a, b, CFG) for a, b in zip(frames, frames[1:])]
    for i, t in enumerate(ts):
        t.id = f"T{i}"
    return ts


def test_typing_then_output_becomes_one_command_transition():
    # The title line persists: a unit is scored by text containment and the IoU of its lines' boxes (§11.1), so a lone
    # prompt line that is rewritten and then grows would not match itself when the run is rebuilt over (0, 5).
    title = ln(0, "Windows PowerShell", 20)
    frames = [frame(0, [term([title, ln(1, "PS> ", 40)])]),
              frame(1, [term([title, ln(1, "PS> git", 40)])]),
              frame(2, [term([title, ln(1, "PS> git stat", 40)])]),
              frame(3, [term([title, ln(1, "PS> git status", 40)])]),
              frame(4, [term([title, ln(1, "PS> git status", 40), ln(2, "On branch main", 60)])]),
              frame(5, [term([title, ln(1, "PS> git status", 40), ln(2, "On branch main", 60), ln(3, "clean", 80)])])]
    out = coalesce(frames, singles(frames), CFG)
    assert len(out) == 1
    t = out[0]
    assert (t.from_frame, t.to_frame) == (0, 5) and t.kind == "coalesced" and t.intermediate_frames == [1, 2, 3, 4]
    assert [e.type for e in t.events] == ["typed", "output_appended"]
    assert t.events[0].text == "git status" and t.events[0].line == "PS> git status" and t.events[0].frames == (0, 3)
    assert t.events[1].lines == 2 and t.events[1].text == "On branch main\nclean" and t.events[1].frames == (3, 5)
    assert t.t == (frames[0].t_end, frames[5].t_settled)
    assert [o.op for o in t.computed_diff["r1"].ops] == ["modify", "insert", "insert"]


def test_backspace_and_scrolloff_are_tolerated():
    # x0 persists so the rebuilt (0, 3) diff still matches the terminal to itself (see the test above); a title line
    # would not do here because Rule 2 wants the scrolled-off deletes at the head of the list.
    frames = [frame(0, [term([ln(1, "PS> git stauts", 40), ln(5, "x0", 60)])]),
              frame(1, [term([ln(1, "PS> git status", 40), ln(5, "x0", 60)])]),
              frame(2, [term([ln(1, "PS> git status", 40), ln(5, "x0", 60), ln(2, "x1", 80), ln(3, "x2", 100)])]),
              frame(3, [term([ln(5, "x0", 40), ln(2, "x1", 60), ln(3, "x2", 80), ln(4, "x3", 100)])])]
    out = coalesce(frames, singles(frames), CFG)
    assert len(out) == 1 and [e.type for e in out[0].events] == ["typed", "output_appended"]
    assert out[0].events[1].lines == 3
    assert [(m[0], m[1]) for m in out[0].regions.matched] == [("r1", "r1")] and out[0].regions.appeared == []


def test_transient_toast_is_merged_across_three_frames():
    toast = Region(id="r5", kind="popup", name="toast", app="Editor", parent=None, bbox=(800, 900, 1000, 930), conf=0.9, layout_conf=0.9,
                   lines=[ln(20, "Saved", 900)])
    frames = [frame(0, [term([ln(1, "code", 40)])]), frame(1, [term([ln(1, "code", 40)]), toast], t0=2.0),
              frame(2, [term([ln(1, "code", 40)])], t0=3.0)]
    out = merge_transients(frames, singles(frames), CFG)
    assert len(out) == 1 and out[0].kind == "transient_merged" and out[0].intermediate_frames == [1]
    assert out[0].transient.name == "toast" and abs(out[0].transient.hold_s - 1.0) < 1e-6


def test_clock_only_transition_is_trivial():
    frames = [frame(0, [term([ln(1, "Tue 14:02", 40)])]), frame(1, [term([ln(1, "Tue 14:03", 40)])])]
    t = tag_trivial(singles(frames)[0])
    assert t.kind == "trivial"


def test_output_rule_on_a_gated_transition_needs_a_boxed_insert_under_changed_pixels():
    frames = [frame(0, [term([ln(1, "PS> ls", 40)])]), frame(1, [term([ln(1, "PS> ls", 40), ln(2, "a.txt", 60), ln(3, "b.txt", 80)])])]
    t = singles(frames)[0]
    t.pixels = PixelChange(changed_fraction=0.001)  # gated
    ins = t.computed_diff["r1"].ops
    ins[0].under_change = ins[1].under_change = None  # VLM-only rows without a box: never vetoed, never evidence
    assert coalesce(frames, [t], CFG)[0].events == []
    ins[0].under_change = True  # one boxed insert under changed pixels carries the no-box one along
    out = coalesce(frames, [t], CFG)
    assert [e.type for e in out[0].events] == ["output_appended"] and out[0].events[0].lines == 2
    for pixels in (PixelChange(changed_fraction=0.3), None):  # above the threshold, or no pixel evidence: the old rule
        t.events, t.pixels, ins[0].under_change = [], pixels, None
        assert [e.type for e in coalesce(frames, [t], CFG)[0].events] == ["output_appended"]


def test_typed_rule_on_a_gated_transition_needs_the_modify_under_changed_pixels():
    # a modify can sit on a no-box line: _ys carries the last boxed y forward, so two adjacent VLM-only rows pair by y
    frames = [frame(0, [term([ln(1, "PS> ", 40)])]), frame(1, [term([ln(1, "PS> ls", 40)])])]
    t = singles(frames)[0]
    t.pixels = PixelChange(changed_fraction=0.001)
    t.computed_diff["r1"].ops[0].under_change = None
    assert coalesce(frames, [t], CFG)[0].events == []
    t.computed_diff["r1"].ops[0].under_change = True
    assert [e.type for e in coalesce(frames, [t], CFG)[0].events] == ["typed"]


def test_retrospective_focus_attributes_typing_to_from_frame():
    frames = [frame(0, [term([ln(1, "PS> ", 40)])]), frame(1, [term([ln(1, "PS> ls", 40)])])]
    frames[0].focused_region, frames[0].focused_conf, frames[0].focused_signals = None, None, []
    out = coalesce(frames, singles(frames), CFG)
    focus = retrospective_focus(frames, out)
    assert focus[0].frame == 0 and focus[0].focused_region == "r1" and focus[0].focused_conf == 0.7 and focus[0].focused_signals == ["retro"]
