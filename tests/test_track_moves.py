from track_fixtures import mk

from scry.track.changes import cancel_moves, same_place


def ids(boxes):
    return [b.id for b in boxes]


def pair_ids(pairs):
    return [(a.id, b.id) for a, b in pairs]


def all_ids(boxes):
    return {b.id for b in boxes}


def test_highlight_over_unchanged_text_is_same_place():
    before = [mk("b1", 10, 130, 100, 148, "Overview")]
    after = [mk("b1", 10, 130, 100, 148, "Overview")]
    pairs, rest_a, rest_b = same_place(before, after, all_ids(before), all_ids(after))
    assert pair_ids(pairs) == [("b1", "b1")] and rest_a == [] and rest_b == []


def _scroll():
    before = [mk("b1", 10, 20, 100, 38, "alpha"), mk("b2", 10, 40, 100, 58, "beta"), mk("b3", 10, 60, 100, 78, "gamma")]
    after = [mk("b1", 10, 20, 100, 38, "beta"), mk("b2", 10, 40, 100, 58, "gamma"), mk("b3", 10, 60, 100, 78, "delta")]
    return before, after


def test_scroll_cancels_as_moves():
    before, after = _scroll()
    ta, tb = all_ids(before), all_ids(after)
    pairs, rest_a, rest_b = same_place(before, after, ta, tb)
    assert pairs == [] and ids(rest_a) == ["b1", "b2", "b3"] and ids(rest_b) == ["b1", "b2", "b3"]
    pairs, rest_a, rest_b = cancel_moves(rest_a, rest_b, ta, tb)
    assert pair_ids(pairs) == [("b2", "b1"), ("b3", "b2")]
    assert ids(rest_a) == ["b1"] and ids(rest_b) == ["b3"]


def test_duplicates_pair_same_place_first_then_reading_order():
    before = [mk("b1", 10, 10, 60, 28, "1.24.10"), mk("b2", 10, 100, 60, 118, "1.24.10")]
    after = [mk("b1", 10, 100, 60, 118, "1.24.10"), mk("b2", 200, 120, 250, 138, "1.24.10")]
    ta, tb = all_ids(before), all_ids(after)
    pairs, rest_a, rest_b = same_place(before, after, ta, tb)
    assert pair_ids(pairs) == [("b2", "b1")]
    pairs, rest_a, rest_b = cancel_moves(rest_a, rest_b, ta, tb)
    assert pair_ids(pairs) == [("b1", "b2")]  # k-th with k-th alone would have crossed them
    assert rest_a == [] and rest_b == []


def test_whitespace_difference_is_not_equal_here():
    before = [mk("b1", 10, 10, 300, 28, "Open in mobile Give feedback")]
    after = [mk("b1", 10, 10, 300, 28, "Open in mobileGive feedback")]
    ta, tb = all_ids(before), all_ids(after)
    pairs, rest_a, rest_b = same_place(before, after, ta, tb)
    assert pairs == []
    pairs, rest_a, rest_b = cancel_moves(rest_a, rest_b, ta, tb)
    assert pairs == [] and ids(rest_a) == ["b1"] and ids(rest_b) == ["b1"]


def test_only_touched_boxes_move():
    before = [mk("b1", 10, 10, 30, 28, "x"), mk("b2", 10, 40, 30, 58, "x")]
    after = [mk("b1", 200, 100, 220, 118, "x")]
    pairs, rest_a, rest_b = cancel_moves(before, after, {"b2"}, {"b1"})
    assert pair_ids(pairs) == [("b2", "b1")]
    assert ids(rest_a) == ["b1"] and rest_b == []
