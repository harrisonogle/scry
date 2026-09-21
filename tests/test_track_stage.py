from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from track_fixtures import SHAPE, frame, mk

from scry.config import Config
from scry.jsonl import write_jsonl
from scry.run import Run
from scry.schemas import FrameBoxes, Revert
from scry.track.stage import run_track, transition_kind


def black() -> np.ndarray:
    return np.zeros(SHAPE, np.uint8)


def lit(*blocks, v=200) -> np.ndarray:
    img = black()
    for y0, y1, x0, x1 in blocks:
        img[y0:y1, x0:x1] = v
    return img


def make_run(root: Path, images: list, boxes: list[list], t_change: list[float] | None = None, settled: list[bool] | None = None) -> Run:
    """A run directory written by hand: L-mode PNGs from arrays (None = no file), frames.jsonl and boxes.jsonl."""
    run = Run(root)
    frames = []
    for n, img in enumerate(images):
        f = frame(n, t_change=None if t_change is None else t_change[n], settled=True if settled is None else settled[n])
        if img is not None:
            Image.fromarray(img, "L").save(run.root / f.png)
        frames.append(f)
    write_jsonl(run.frames, frames)
    write_jsonl(run.boxes, [FrameBoxes(frame=n, png=frames[n].png, engine={"engine": "fake"}, boxes=bs) for n, bs in enumerate(boxes)])
    return run


TOOLTIP = (100, 120, 300, 380)


def tooltip_box():
    return mk("b1", 305, 101, 375, 119, "Cloud Shell")


def test_tooltip_reverts_with_hold_time(tmp_path):
    run = make_run(tmp_path / "r", [black(), lit(TOOLTIP), black()], [[], [tooltip_box()], []], t_change=[0.0, 1.0, 3.8])
    run_track(run, Config())
    t1, t2 = run.load_changes()
    assert (t1.id, t2.id) == ("T1", "T2")
    assert [(r.kind, r.after.box) for r in t1.records] == [("appeared", "1:b1")] and t1.reverts == []
    [r] = t2.records
    assert r.kind == "removed" and r.before.box == "1:b1" and r.continues == "T1/0"
    assert t2.reverts == [Revert(of="T1", rect=(300, 100, 380, 120), hold_s=2.8)]


def test_revert_while_something_else_changes(tmp_path):
    run = make_run(tmp_path / "r", [black(), lit(TOOLTIP), lit((20, 40, 20, 100))],
                   [[], [tooltip_box()], [mk("b1", 30, 21, 90, 39, "Saved")]], t_change=[0.0, 1.0, 3.8])
    run_track(run, Config())
    _, t2 = run.load_changes()
    assert t2.pixels.components == 2
    assert [(r.kind, (r.after or r.before).box) for r in t2.records] == [("appeared", "2:b1"), ("removed", "1:b1")]
    assert t2.reverts == [Revert(of="T1", rect=(300, 100, 380, 120), hold_s=2.8)]


def test_partial_return_is_not_a_revert(tmp_path):
    run = make_run(tmp_path / "r", [black(), lit(TOOLTIP), lit((100, 120, 300, 340))], [[], [tooltip_box()], []], t_change=[0.0, 1.0, 3.8])
    run_track(run, Config())
    assert run.load_changes()[1].reverts == []


def test_continues_links_consecutive_growth(tmp_path):
    images = [black(), lit((52, 66, 140, 168), v=255), lit((52, 66, 140, 168), (52, 66, 176, 228), v=255)]
    boxes = [[mk("b1", 10, 50, 130, 68, "PS>")], [mk("b1", 10, 50, 170, 68, "PS> git")], [mk("b1", 10, 50, 230, 68, "PS> git status")]]
    run = make_run(tmp_path / "r", images, boxes)
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
        assert t.pixels is None and t.records == [] and t.same_place == 2 and t.reverts == []


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
