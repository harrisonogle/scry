import numpy as np
import pytest
from track_fixtures import black, frame, lit, make_run, mk, typing_run

from scry.config import Config
from scry.schemas import Revert
from scry.track.stage import run_track, transition_kind


TOOLTIP = (100, 120, 300, 380)


def tooltip_box():
    return mk("b1", 305, 101, 375, 119, "Cloud Shell")


def test_full_revert_has_share_one(tmp_path):
    run = make_run(tmp_path / "r", [black(), lit(TOOLTIP), black()], [[], [tooltip_box()], []], t_change=[0.0, 1.0, 3.8])
    run_track(run, Config())
    t1, t2 = run.load_changes()
    assert (t1.id, t2.id) == ("T1", "T2")
    assert [(r.kind, r.after.box) for r in t1.records] == [("appeared", "1:b1")] and t1.reverts is None  # no previous transition
    [r] = t2.records
    assert r.kind == "removed" and r.before.box == "1:b1" and r.continues == "T1/0"
    assert t2.reverts == Revert(of="T1", share=1.0, hold_s=2.8)  # held from t_change 1.0 to 3.8
    assert run.manifest_read()["stages"]["track"]["reverts"] == 1  # transitions that carry one


def test_revert_while_something_else_changes(tmp_path):
    # T1 lit the tooltip: 20 × 80 = 1,600 changed pixels. Frame 2 keeps its left 30 columns lit (20 × 30 = 600 pixels
    # still differ from frame 0) and lights a block elsewhere, which is outside T1's pixels and does not enter.
    # Back to frame 0: 1,600 − 600 = 1,000 pixels; share = 1,000 / 1,600 = 0.625.
    run = make_run(tmp_path / "r", [black(), lit(TOOLTIP), lit((100, 120, 300, 330), (20, 40, 20, 100))],
                   [[], [tooltip_box()], [mk("b1", 30, 21, 90, 39, "Saved")]], t_change=[0.0, 1.0, 3.8])
    run_track(run, Config())
    _, t2 = run.load_changes()
    assert t2.pixels.components == 2
    assert t2.reverts == Revert(of="T1", share=0.625, hold_s=2.8)


def test_nothing_to_revert_gives_no_field(tmp_path):
    # T1: no previous transition. T2: T1 changed no pixels. T3: none of T2's pixels came back (share 0).
    run = make_run(tmp_path / "r", [black(), black(), lit(TOOLTIP), lit(TOOLTIP, (20, 40, 20, 100))], [[], [], [], []])
    run_track(run, Config())
    assert [c.reverts for c in run.load_changes()] == [None, None, None]
    assert '"reverts":null' in run.changes.read_text()


def test_continues_links_consecutive_growth(tmp_path):
    run = typing_run(tmp_path / "r")
    run_track(run, Config())
    t1, t2 = run.load_changes()
    assert t1.records[0].kind == "appended" and t1.records[0].continues is None
    assert t2.records[0].kind == "appended" and t2.records[0].continues == "T1/0"
    lifetimes = run.load_lifetimes()
    assert len(lifetimes) == 3 and all(l.sightings == 1 for l in lifetimes)


def test_unsettled_kind():
    assert transition_kind(frame(0), frame(1, settled=False)) == "unsettled"
    assert transition_kind(frame(0, settled=False), frame(1)) == "unsettled"
    assert transition_kind(frame(0), frame(1)) == "single"


def test_size_mismatch_and_missing_png_degrade(tmp_path):
    bs = [mk("b1", 10, 10, 110, 28, "Title"), mk("b2", 10, 50, 130, 68, "PS>")]
    run = make_run(tmp_path / "r", [black(), np.zeros((100, 200), np.uint8), None], [bs, bs, bs])
    run_track(run, Config())
    t1, t2 = run.load_changes()
    for t in (t1, t2):
        assert t.pixels is None and t.records == [] and t.same_place == 2 and t.reverts is None


def test_zero_and_one_frame_runs(tmp_path):
    run = make_run(tmp_path / "zero", [], [])
    run_track(run, Config())
    assert run.changes.exists() and run.changes.read_text() == "" and run.lifetimes.exists() and run.lifetimes.read_text() == ""
    st = run.manifest_read()["stages"]["track"]
    assert st["transitions"] == 0 and st["lifetimes"] == 0

    run = make_run(tmp_path / "one", [black()], [[mk("b1", 10, 10, 30, 28, "a"), mk("b2", 10, 50, 30, 68, "b")]])
    run_track(run, Config())
    assert run.changes.read_text() == ""
    assert [(l.text, l.sightings) for l in run.load_lifetimes()] == [("a", 1), ("b", 1)]


def test_missing_boxes_record_is_an_error(tmp_path):
    run = make_run(tmp_path / "r", [black(), black()], [[]])
    with pytest.raises(ValueError, match="scry read"):
        run_track(run, Config())


def test_skips_when_up_to_date_and_reruns_on_margin_change(tmp_path):
    run = make_run(tmp_path / "r", [black(), lit(TOOLTIP)], [[], [tooltip_box()]])
    cfg = Config()
    run_track(run, cfg)
    assert run.manifest_read()["stages"]["track"]["margin"] == 0.5
    run.changes.unlink()
    run_track(run, cfg)
    assert not run.changes.exists()  # up to date: the stage did not run
    cfg.track.margin = 0.0
    run_track(run, cfg)
    assert run.changes.exists() and run.manifest_read()["stages"]["track"]["margin"] == 0.0
