from track_fixtures import block, diff_of, fixture_k, frame, mk, new_labels

from scry.schemas import BoxText
from scry.track.changes import Pairing, kind_of, track_pair


def run(a_boxes, b_boxes, diff, margin=0.5):
    return track_pair(frame(0), frame(1), a_boxes, b_boxes, diff, margin)


def one_block(y0, y1, x0, x1):
    labels = new_labels()
    return diff_of(labels, [block(labels, 1, y0, y1, x0, x1)])


def test_kind_of():
    assert kind_of("PS>", "PS> git status") == "appended"
    assert kind_of("PS> git status", "PS>") == "truncated"
    assert kind_of("Status : Creating", "Status : Succeeded") == "changed"
    assert kind_of("Open in mobile Give feedback", "Open in mobileGive feedback") == "reread"


def test_keystroke_is_one_appended_record():
    a, b, d = fixture_k()
    res = run(a, b, d)
    c = res.change
    assert len(c.records) == 1
    r = c.records[0]
    assert r.kind == "appended" and r.rect == (10, 50, 230, 68)
    assert r.before == BoxText(box="0:b2", text="PS>") and r.after == BoxText(box="1:b2", text="PS> git status")
    assert r.char_diff == [["=", "PS>"], ["+", " git status"]]
    assert r.continues is None
    assert c.unchanged == 1 and c.variants == 0 and c.moved == [] and c.same_place == 0
    assert c.flicker_lost == ["0:b3"] and c.flicker_new == []
    p = c.pixels
    assert (p.changed_fraction, p.components, p.textless, p.textless_area, p.touched_share, p.rect_only) == (0.0154, 1, 0, 0, 0.2, 0)
    assert res.pairings == [Pairing("b1", "b1", "unchanged")] and res.starts == ["b2"]
    assert c.id == "" and c.kind == "single" and c.t == (1.0, 1.0) and c.reverts == []


def test_truncation_pairs_with_the_untouched_later_box():
    a = [mk("b1", 10, 50, 230, 68, "PS> git status")]
    b = [mk("b1", 10, 50, 130, 68, "PS>")]
    res = run(a, b, fixture_k()[2])
    [r] = res.change.records
    assert r.kind == "truncated" and r.char_diff == [["=", "PS>"], ["-", " git status"]]
    assert res.change.flicker_new == [] and res.change.flicker_lost == []
    assert res.starts == ["b1"]


def test_adjacent_overlapping_lines_pair_with_their_own_earlier_selves():
    a = [mk("b1", 10, 40, 300, 60, "cmd1 output"), mk("b2", 10, 57, 70, 77, "PS>")]
    b = [mk("b1", 10, 40, 300, 60, "cmdl output"), mk("b2", 10, 57, 200, 77, "PS> git status")]
    res = run(a, b, one_block(60, 75, 80, 198))
    r1, r2 = res.change.records
    assert (r1.kind, r1.before.text, r1.after.text) == ("changed", "cmd1 output", "cmdl output")
    assert (r2.kind, r2.before.text, r2.after.text) == ("appended", "PS>", "PS> git status")
    assert r2.char_diff == [["=", "PS>"], ["+", " git status"]]
    assert res.change.pixels.touched_share == 0.75
    assert res.starts == ["b1", "b2"] and res.pairings == []


def test_char_diff_reassembles_both_sides():
    a = [mk("b1", 10, 10, 200, 28, "Status : Creating")]
    b = [mk("b1", 10, 10, 200, 28, "Status : Succeeded")]
    [r] = run(a, b, one_block(10, 28, 10, 200)).change.records
    assert r.kind == "changed"
    assert "".join(t for s, t in r.char_diff if s in "=-") == "Status : Creating"
    assert "".join(t for s, t in r.char_diff if s in "=+") == "Status : Succeeded"


def test_reread_record_continues_the_lifetime():
    a = [mk("b1", 10, 10, 300, 28, "Open in mobile Give feedback")]
    b = [mk("b1", 10, 10, 300, 28, "Open in mobileGive feedback")]
    res = run(a, b, one_block(10, 28, 10, 300))
    [r] = res.change.records
    assert r.kind == "reread"
    assert res.pairings == [Pairing("b1", "b1", "reread")] and res.starts == []


def test_resplit_is_one_record_and_one_appeared_box():
    a = [mk("b1", 10, 10, 200, 28, "File Edit View")]
    b = [mk("b1", 10, 10, 50, 28, "File"), mk("b2", 60, 10, 200, 28, "Edit View")]
    res = run(a, b, one_block(10, 28, 10, 200))
    r1, r2 = res.change.records
    assert r1.kind == "appeared" and r1.before is None and r1.after == BoxText(box="1:b1", text="File")
    assert (r2.kind, r2.before.text, r2.after.text) == ("changed", "File Edit View", "Edit View")
    assert res.starts == ["b1", "b2"] and res.pairings == []


def test_popup_appears_and_a_textless_component():
    a = [mk("b1", 10, 10, 110, 28, "Title")]
    b = [mk("b1", 10, 10, 110, 28, "Title"), mk("b2", 300, 100, 380, 118, "Cloud Shell")]
    labels = new_labels()
    d = diff_of(labels, [block(labels, 1, 96, 122, 296, 384), block(labels, 2, 180, 190, 350, 360)])
    c = run(a, b, d).change
    [r] = c.records
    assert r.kind == "appeared" and r.before is None and r.after == BoxText(box="1:b2", text="Cloud Shell")
    assert r.rect == (300, 100, 380, 118) and r.char_diff == []
    assert c.unchanged == 1
    assert (c.pixels.components, c.pixels.textless, c.pixels.textless_area, c.pixels.touched_share) == (2, 1, 100, 0.3333)


def test_scroll_is_mostly_moved():
    a = [mk("b1", 10, 20, 100, 38, "alpha"), mk("b2", 10, 40, 100, 58, "beta"), mk("b3", 10, 60, 100, 78, "gamma")]
    b = [mk("b1", 10, 20, 100, 38, "beta"), mk("b2", 10, 40, 100, 58, "gamma"), mk("b3", 10, 60, 100, 78, "delta")]
    res = run(a, b, one_block(20, 78, 10, 100))
    c = res.change
    assert c.moved == [("0:b2", "1:b1"), ("0:b3", "1:b2")]
    r1, r2 = c.records
    assert r1.kind == "appeared" and r1.after == BoxText(box="1:b3", text="delta")
    assert r2.kind == "removed" and r2.before == BoxText(box="0:b1", text="alpha") and r2.after is None
    assert res.pairings == [Pairing("b2", "b1", "moved"), Pairing("b3", "b2", "moved")] and res.starts == ["b3"]


def test_untouched_leftover_is_flicker_not_a_change():
    a = [mk("b1", 10, 100, 390, 118, "Authentication and Authorization Local accounts")]
    b = [mk("b1", 10, 100, 200, 118, "Authentication and Authorization"), mk("b2", 220, 100, 390, 118, "Local accounts")]
    res = run(a, b, diff_of(new_labels(), []))
    c = res.change
    assert c.records == [] and c.unchanged == 1 and c.variants == 1 and c.flicker_new == ["1:b2"]
    assert res.starts == ["b2"]


def test_variant_on_untouched_pixels_is_not_a_change():
    a = [mk("b1", 10, 100, 200, 118, "Subscription ID :3e6b")]
    b = [mk("b1", 10, 100, 201, 119, "SubscriptionID :3e6b")]
    c = run(a, b, diff_of(new_labels(), [])).change
    assert c.unchanged == 1 and c.variants == 1 and c.records == []


def test_no_boxes_at_all():
    c = run([], [], one_block(50, 60, 50, 60)).change
    assert c.records == [] and c.pixels.textless == 1 and c.pixels.touched_share == 0.0
