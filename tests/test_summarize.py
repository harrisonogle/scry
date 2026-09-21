from pathlib import Path

from fakes import AnswerProvider
from minirun import call_text, mini_interpretations, mini_run, summarize_answers

from scry.config import Config, SummarizeConfig
from scry.jsonl import write_jsonl
from scry.schemas import Change, HierNode, Interpretation, ModelBoundaries, SegmentStart
from scry.summarize import (fallback_segments, item_full, item_line, merge_window_boundaries, propagate, repair_boundaries,
                            run_summarize, state_line, window_ranges)

LINE_T1 = ('T1 [f10→f11, 24.0–24.4s] appended "C:\\src> git status" — The user typed " st" in the terminal; the shell offers '
           '"atus" as a completion. [entered "git st", submitted: no]')
LINE_T2 = 'T2 [f11→f12, 26.0–26.4s] appeared 2 — The user pressed Enter. [entered "git status", submitted: yes]'
LINE_T3 = 'T3 [f12→f13, 30.0–30.4s] changed "Succeeded" — No user action is evident; the portal refreshed.'


def test_repair_boundaries_sorts_dedups_drops_unknown_and_forces_first():
    ids = [f"T{i}" for i in range(1, 11)]
    segs = [SegmentStart(start_id="T5", label="b"), SegmentStart(start_id="T9", label="c"), SegmentStart(start_id="T5", label="dup"),
            SegmentStart(start_id="T99", label="x")]
    assert repair_boundaries(segs, ids) == [(0, "segment 1"), (4, "b"), (8, "c")]
    assert repair_boundaries([], ids) == [(0, "segment 1")]


def test_fallback_and_windows():
    assert fallback_segments(45, 20) == [(0, "segment 1"), (20, "segment 2"), (40, "segment 3")]
    assert window_ranges(10, 2000, 200) == [(0, 10)]
    assert window_ranges(5000, 2000, 200) == [(0, 2000), (1800, 3800), (3600, 5000)]


def test_merge_window_boundaries_keeps_non_overlap_and_agreed_overlap():
    per = [(0, 2000, [(0, "a"), (1000, "b"), (1900, "c")]), (1800, 3800, [(1800, "c?"), (1900, "c"), (2500, "d")])]
    assert [s for s, _ in merge_window_boundaries(per, 3800, 200)] == [0, 1000, 1900, 2500]


def test_propagate_from_changes_and_nodes():
    changes = [Change(id="T1", from_frame=0, to_frame=5, t=(1.0, 2.0), kind="single", pixels=None),
               Change(id="T2", from_frame=5, to_frame=9, t=(2.5, 4.0), kind="single", pixels=None)]
    assert propagate(changes) == ((0, 9), (1.0, 4.0))  # frame 0 is a frame, not a missing value
    steps = [HierNode(id="S1", level="step", children=("T1", "T2"), frames=(0, 9), t=(1.0, 4.0), label="l", description="d")]
    assert propagate(steps) == ((0, 9), (1.0, 4.0))


def _mini(tmp_path: Path, labels: bool = False):
    run = mini_run(tmp_path, labels=labels)
    mini_interpretations(run)
    return run, {c.id: c for c in run.load_changes()}, run.load_interpretations()


def test_item_line(tmp_path: Path):
    _, changes, interps = _mini(tmp_path)
    assert item_line(changes["T1"], interps) == LINE_T1
    assert item_line(changes["T2"], interps) == LINE_T2
    assert item_line(changes["T3"], interps) == LINE_T3
    assert item_line(changes["T1"], {}) == 'T1 [f10→f11, 24.0–24.4s] appended "C:\\src> git status"'
    form = {"T3": Interpretation(id="T3", action="The user clicked Save.", entered_text=None, submitted="yes")}
    assert item_line(changes["T3"], form).endswith(" — The user clicked Save. [submitted: yes]")
    step = HierNode(id="S1", level="step", children=("T1", "T2"), frames=(10, 12), t=(24.0, 26.4), label="Run git status", description="d")
    assert item_line(step, interps) == "S1 [f10→f12, 24.0–26.4s] Run git status"


def test_item_full(tmp_path: Path):
    _, changes, interps = _mini(tmp_path)
    assert item_full(changes["T1"], interps) == (
        'T1 [f10→f11, 24.0–24.4s] appended "C:\\src> git status"\n'
        '  action: The user typed " st" in the terminal; the shell offers "atus" as a completion.\n'
        '  result: The command line now reads git st with a greyed suggestion.\n'
        '  entered: "git st"; submitted: no\n'
        '  text: "C:\\src> git" → "C:\\src> git status"')
    assert item_full(changes["T3"], interps).split("\n") == [
        'T3 [f12→f13, 30.0–30.4s] changed "Succeeded"', "  action: No user action is evident; the portal refreshed.",
        "  result: The Status value changed from Creating to Succeeded.", '  text: "Creating" → "Succeeded"']
    assert item_full(changes["T2"], interps).split("\n") == [
        "T2 [f11→f12, 26.0–26.4s] appeared 2", "  action: The user pressed Enter.",
        '  result: Git printed "On branch main" and a new prompt appeared.', '  entered: "git status"; submitted: yes']
    refused = {"T1": Interpretation(id="T1", error="refusal")}
    assert item_full(changes["T1"], refused).split("\n") == ['T1 [f10→f11, 24.0–24.4s] appended "C:\\src> git status"',
                                                             '  text: "C:\\src> git" → "C:\\src> git status"']


def test_state_line(tmp_path: Path):
    run = mini_run(tmp_path, labels=True)
    frame = run.load_frames()[0]
    with_labels = state_line(frame, run.load_labels())
    assert with_labels == "frame 10 (t=20.4s): windows [Azure Portal: Resource overview, Windows Terminal: PowerShell]"
    assert state_line(frame, None) == "frame 10 (t=20.4s)"
    assert "focus" not in with_labels + state_line(frame, None)


def test_run_summarize_builds_three_levels(tmp_path: Path):
    run, _, _ = _mini(tmp_path)
    provider = AnswerProvider(summarize_answers)
    run_summarize(run, Config(), provider)
    s1, s2 = run.load_steps()
    assert (s1.id, s1.children, s1.frames, s1.t, s1.refs, s1.label) == ("S1", ("T1", "T2"), (10, 12), (24.0, 26.4), ["T1", "T2"], "Run git status")
    assert (s2.id, s2.children, s2.frames, s2.t, s2.label) == ("S2", ("T3", "T3"), (12, 13), (30.0, 30.4), "Watch the deployment")
    (c1,) = run.load_sections()
    assert (c1.id, c1.children, c1.frames, c1.t) == ("C1", ("S1", "S2"), (10, 13), (24.0, 30.4))
    video = run.load_video()
    assert (video.id, video.level, video.children, video.label) == ("V", "video", ("C1", "C1"), "A short demo")
    by_stage = {}
    for kw in provider.calls:
        by_stage.setdefault(kw["stage"], []).append(call_text(kw))
    assert by_stage["summarize-boundary-step"] == ["\n".join([LINE_T1, LINE_T2, LINE_T3])]
    first = next(t for t in by_stage["summarize-elaborate-step"] if t.startswith("Segment S1\n"))
    assert first.startswith("Segment S1\nStart state: frame 10 (t=20.4s)\nEnd state: frame 12 (t=26.4s)\n\nItems:\nT1 [f10→f11")
    assert by_stage["summarize-elaborate-video"][0].startswith("Segment V\n")
    stats = run.manifest_read()["stages"]["summarize"]
    assert (stats["steps"], stats["sections"], stats["low_conf"], stats["invalid_refs"], stats["calls"]) == (2, 1, 0, 1, 6)
    assert (stats["usage"]["input_tokens"], stats["usage"]["cache_creation_input_tokens"], stats["cost_usd"]) == (600, 2400, 0.024)
    run_summarize(run, Config(), provider)
    assert len(provider.calls) == 6


def test_boundary_retry_then_fallback(tmp_path: Path):
    def answer(kw: dict):
        return ModelBoundaries(segments=[]) if kw["stage"] == "summarize-boundary-step" else summarize_answers(kw)

    run, _, _ = _mini(tmp_path)
    provider = AnswerProvider(answer)
    run_summarize(run, Config(summarize=SummarizeConfig(fallback_step_transitions=2)), provider)
    boundary = [call_text(kw) for kw in provider.calls if kw["stage"] == "summarize-boundary-step"]
    assert len(boundary) == 2
    assert boundary[1].endswith("(Retry: the previous answer contained no valid start ids. Use the ids exactly as listed above.)")
    steps = run.load_steps()
    assert [(s.id, s.children, s.segmentation_conf) for s in steps] == [("S1", ("T1", "T2"), "low"), ("S2", ("T3", "T3"), "low")]
    assert run.manifest_read()["stages"]["summarize"]["low_conf"] == 2


def test_summarize_with_a_failed_interpretation(tmp_path: Path):
    run, _, interps = _mini(tmp_path)
    interps["T2"] = Interpretation(id="T2", error="refusal")
    write_jsonl(run.interpretations, interps.values())
    provider = AnswerProvider(summarize_answers)
    run_summarize(run, Config(), provider)
    boundary = next(call_text(kw) for kw in provider.calls if kw["stage"] == "summarize-boundary-step")
    assert boundary.split("\n")[1] == "T2 [f11→f12, 26.0–26.4s] appeared 2"
    assert run.load_video() is not None


def test_no_transitions_writes_nothing(tmp_path: Path):
    run = mini_run(tmp_path)
    write_jsonl(run.changes, [])
    provider = AnswerProvider(summarize_answers)
    run_summarize(run, Config(), provider)
    assert provider.calls == [] and not run.steps.exists()
    assert "summarize" not in run.manifest_read().get("stages", {})
