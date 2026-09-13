from vt.hierarchy import fallback_segments, merge_window_boundaries, propagate, repair_boundaries, window_ranges
from vt.schemas import HierNode, SegmentStart, Transition


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
    out = merge_window_boundaries(per, 3800, 200)
    assert [s for s, _ in out] == [0, 1000, 1900, 2500]


def test_propagate_from_transitions_and_nodes():
    ts = [Transition(id="T1", from_frame=3, to_frame=5, t=(1.0, 2.0), kind="single"), Transition(id="T2", from_frame=5, to_frame=9, t=(2.5, 4.0), kind="single")]
    assert propagate(ts) == ((3, 9), (1.0, 4.0))
    steps = [HierNode(id="S1", level="step", children=("T1", "T2"), frames=(3, 9), t=(1.0, 4.0), label="l", description="d")]
    assert propagate(steps) == ((3, 9), (1.0, 4.0))
