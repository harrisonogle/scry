import pytest
from track_fixtures import frame, mk

from scry.schemas import Change, FrameTime
from scry.track.changes import PairResult, Pairing
from scry.track.lifetimes import LifetimeBuilder


def boxes(*texts):
    return [mk(f"b{i}", 10, 20 * i, 100, 20 * i + 18, t) for i, t in enumerate(texts, start=1)]


def result(a: int, b: int, pairings, starts) -> PairResult:
    change = Change(id="", from_frame=a, to_frame=b, t=(0.0, 0.0), kind="single", pixels=None)
    return PairResult(change, [Pairing(*p) for p in pairings], list(starts))


def test_lifetimes_over_three_frames():
    f0, f1, f2 = frame(0, t_settled=0.0, t_end=1.0), frame(1, t_settled=1.5, t_end=2.0), frame(2, t_settled=2.5, t_end=9.0)
    lb = LifetimeBuilder()
    lb.first_frame(f0, boxes("Title", "PS>"))
    lb.step(f1, boxes("Title", "PS> git status"), result(0, 1, [("b1", "b1", "unchanged")], ["b2"]))
    lb.step(f2, boxes("Title", "PS> git status", "On branch main"),
            result(1, 2, [("b1", "b1", "unchanged"), ("b2", "b2", "unchanged")], ["b3"]))
    l1, l2, l3, l4 = lb.finish()
    assert (l1.id, l1.text, l1.boxes, l1.sightings) == ("L1", "Title", ["0:b1", "1:b1", "2:b1"], 3)
    assert l1.readings == {"Title": [0, 1, 2]} and not l1.unstable and not l1.moved
    assert l1.first == FrameTime(frame=0, t=0.0) and l1.last == FrameTime(frame=2, t=9.0)
    assert (l2.id, l2.text, l2.boxes) == ("L2", "PS>", ["0:b2"])
    assert l2.first == FrameTime(frame=0, t=0.0) and l2.last == FrameTime(frame=0, t=1.0)
    assert (l3.id, l3.text, l3.boxes) == ("L3", "PS> git status", ["1:b2", "2:b2"])
    assert l3.first == FrameTime(frame=1, t=1.5) and l3.last == FrameTime(frame=2, t=9.0)
    assert (l4.id, l4.text, l4.boxes) == ("L4", "On branch main", ["2:b3"])


def test_majority_reading_and_tie():
    lb = LifetimeBuilder()
    lb.first_frame(frame(0), boxes("Subscription ID"))
    lb.step(frame(1), boxes("SubscriptionID"), result(0, 1, [("b1", "b1", "unchanged")], []))
    lb.step(frame(2), boxes("Subscription ID"), result(1, 2, [("b1", "b1", "unchanged")], []))
    [life] = lb.finish()
    assert life.text == "Subscription ID" and life.unstable
    assert life.readings == {"Subscription ID": [0, 2], "SubscriptionID": [1]}

    lb = LifetimeBuilder()
    lb.first_frame(frame(0), boxes("A b"))
    lb.step(frame(1), boxes("Ab"), result(0, 1, [("b1", "b1", "reread")], []))
    [life] = lb.finish()
    assert life.text == "A b"  # a tie goes to the reading sighted first


def test_moved_sets_the_flag():
    lb = LifetimeBuilder()
    lb.first_frame(frame(0), boxes("beta"))
    lb.step(frame(1), boxes("beta"), result(0, 1, [("b1", "b1", "moved")], []))
    [life] = lb.finish()
    assert life.moved and life.sightings == 2


def test_unaccounted_box_raises():
    lb = LifetimeBuilder()
    lb.first_frame(frame(0), boxes("a"))
    with pytest.raises(ValueError, match="b2"):
        lb.step(frame(1), boxes("a", "b"), result(0, 1, [("b1", "b1", "unchanged")], []))
