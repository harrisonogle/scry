import pytest
from annotate_fixtures import change, fb, fixture_t, life, mk

from scry.annotate.targets import CallPlan, plan_calls


def _boxes(*texts: str):
    return [mk(f"b{i}", 10, 20 * i, 110, 20 * i + 16, text) for i, text in enumerate(texts, 1)]


def fixture_p():
    frames = [fb(0, _boxes("A", "B")), fb(1, _boxes("A", "B", "F")), fb(2, _boxes("A", "B2", "C", "F")), fb(3, _boxes("Z"))]
    changes = [change("T1", 0, 1, 0), change("T2", 1, 2, 2), change("T3", 2, 3, 1)]
    lifetimes = [life("L1", "A", ["0:b1", "1:b1", "2:b1"]), life("L2", "B", ["0:b2", "1:b2"]), life("L3", "F", ["1:b3", "2:b4"]),
                 life("L4", "B2", ["2:b2"]), life("L5", "C", ["2:b3"]), life("L6", "Z", ["3:b1"])]
    return frames, changes, lifetimes


def test_incremental_plan():
    frames, changes, lifetimes = fixture_p()
    # frame 1 has no call, so "F", whose lifetime began there, is never a target
    assert plan_calls(frames, changes, lifetimes, "incremental") == [
        CallPlan(0, ("b1", "b2")), CallPlan(2, ("b2", "b3")), CallPlan(3, ("b1",))]


def test_missing_pixels_means_a_call():
    frames, changes, lifetimes = fixture_p()
    changes[0] = change("T1", 0, 1, None)
    assert plan_calls(frames, changes, lifetimes, "incremental") == [
        CallPlan(0, ("b1", "b2")), CallPlan(1, ("b3",)), CallPlan(2, ("b2", "b3")), CallPlan(3, ("b1",))]


def test_every_frame_plan():
    frames, _, _ = fixture_p()
    assert plan_calls(frames, [], [], "every_frame") == [
        CallPlan(0, ("b1", "b2")), CallPlan(1, ("b1", "b2", "b3")), CallPlan(2, ("b1", "b2", "b3", "b4")), CallPlan(3, ("b1",))]
    assert plan_calls([fb(0, [])], [], [], "every_frame") == [CallPlan(0, ())]
    assert plan_calls([], [], [], "incremental") == []


def test_fixture_t_plan():
    _, frames, changes, lifetimes = fixture_t()
    assert plan_calls(frames, changes, lifetimes, "incremental") == [
        CallPlan(10, ("b1", "b2", "b3", "b4")), CallPlan(11, ("b1", "b5"))]


def test_missing_transition_raises():
    frames, changes, lifetimes = fixture_p()
    with pytest.raises(ValueError, match="frame 2"):
        plan_calls(frames, [changes[0], changes[2]], lifetimes, "incremental")
