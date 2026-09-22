from track_fixtures import diff_of, fixture_k, mk, new_labels

from scry.track.changes import match_one_to_one, match_unchanged, touched_flags


def test_keystroke_touched_and_unchanged():
    a, b, d = fixture_k()
    assert d.changed_fraction == 0.0154 and d.components[0].area == 1232
    ta, tb = touched_flags(a, d, 9), touched_flags(b, d, 9)
    assert ta == [False, False, False]  # a.b2 grown is (1,41,139,77); the component starts at x = 140
    assert tb == [False, True]
    assert match_unchanged(a, b, ta, tb) == [(0, 0)]


def test_one_to_one_when_two_later_boxes_claim_one_earlier_box():
    d = diff_of(new_labels(), [])
    a = [mk("b1", 10, 100, 390, 118, "Authentication and Authorization Local accounts")]
    b = [mk("b1", 10, 100, 200, 118, "Authentication and Authorization"), mk("b2", 220, 100, 390, 118, "Local accounts")]
    ta, tb = touched_flags(a, d, 9), touched_flags(b, d, 9)
    assert match_unchanged(a, b, ta, tb) == [(0, 0)]  # areas 3,420 and 3,060; index 1 of b is in no pair


def test_no_pixels_means_everything_is_touched():
    a, b = [mk("b1", 0, 0, 10, 10, "x")], [mk("b1", 0, 0, 10, 10, "x")]
    ta, tb = touched_flags(a, None, 9), touched_flags(b, None, 9)
    assert ta == [True] and tb == [True]
    assert match_unchanged(a, b, ta, tb) == []


def test_match_one_to_one_tie_breaks():
    assert match_one_to_one([(50, 0, 1), (50, 0, 0), (40, 1, 0)]) == [(0, 0)]
