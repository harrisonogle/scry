from annotate_fixtures import mk

from scry.annotate.output import output_model
from scry.annotate.proposal import snap_rect, to_proposal
from scry.schemas import PairLink, RecordLink, RunLink, TextReading
from scry.track.pixels import margin_px

BOXES = [mk(f"b{i}", 10, 20 * i, 110, 20 * i + 16, "x") for i in range(1, 8)]


def _answer(transcribe: bool) -> dict:
    answer = {"containers": [{"id": "c1", "kind": "window", "app": "Mail", "name": "Inbox", "owner": None, "covers": []}],
              "assign": [{"box": "b1", "container": "c1"}, {"box": "b2", "container": "c1"}], "unassigned": ["b3"],
              "runs": [{"boxes": ["b1", "b2"], "joiner": " "}], "pairs": [{"key": ["b3"], "value": ["b4"]}],
              "records": [{"members": [["b5"], ["b6"], ["b7"]], "header": []}], "description": "d"}
    if transcribe:
        answer |= {"texts": [{"box": "b1", "text": "a"}, {"box": "b2", "text": ""}],
                   "missed": [{"text": "Networking", "container": "c1"}]}
    return answer


def test_arm_a_copy():
    out = output_model("A", True).model_validate(_answer(True))
    p, counts = to_proposal("A", out, BOXES, (400, 200), 8)
    assert [l.kind for l in p.links] == ["run", "pair", "record"]
    assert p.texts == [TextReading(box="b1", text="a"), TextReading(box="b2", text="")]
    assert p.missed == [("Networking", "c1")]
    assert counts == {}
    assert p.containers[0].id == "c1" and p.containers[0].rect is None
    assert [(a.box, a.container) for a in p.assign] == [("b1", "c1"), ("b2", "c1")] and p.unassigned == ["b3"]
    assert p.description == "d"
    group, _ = to_proposal("A", output_model("A", False).model_validate(_answer(False)), BOXES, (400, 200), 8)
    assert group.texts is None and group.missed == []


# ---------- reference = "coords": every rectangle matched to a box id before repair sees the proposal ----------
def _r(i: int) -> list[int]:
    """The rectangle of b<i>, as the user message lists it."""
    return [10, 20 * i, 110, 20 * i + 16]


def _coords_answer(transcribe: bool) -> dict:
    """The answer of `_answer` with each box named by its rectangle."""
    answer = {"containers": [{"id": "c1", "kind": "window", "app": "Mail", "name": "Inbox", "owner": None, "covers": []}],
              "assign": [{"rect": _r(1), "container": "c1"}, {"rect": _r(2), "container": "c1"}], "unassigned": [_r(3)],
              "runs": [{"boxes": [_r(1), _r(2)], "joiner": " "}], "pairs": [{"key": [_r(3)], "value": [_r(4)]}],
              "records": [{"members": [[_r(5)], [_r(6)], [_r(7)]], "header": []}], "description": "d"}
    if transcribe:
        answer |= {"texts": [{"rect": _r(1), "text": "a"}, {"rect": _r(2), "text": ""}],
                   "missed": [{"text": "Networking", "container": "c1"}]}
    return answer


def test_coords_rectangles_become_the_arm_a_proposal():
    """`margin_px(BOXES, [], 0.5) == 8`; every rectangle of `_coords_answer` is a listed one, so the proposal is `_answer`'s."""
    assert margin_px(BOXES, [], 0.5) == 8
    out = output_model("A", True, reference="coords").model_validate(_coords_answer(True))
    p, counts = to_proposal("A", out, BOXES, (400, 200), 8, reference="coords")
    want, _ = to_proposal("A", output_model("A", True).model_validate(_answer(True)), BOXES, (400, 200), 8)
    assert p == want and counts == {}
    group, counts = to_proposal("A", output_model("A", False, reference="coords").model_validate(_coords_answer(False)), BOXES, (400, 200), 8, reference="coords")
    assert group.texts is None and group.missed == [] and counts == {}
    assert [l.kind for l in group.links] == ["run", "pair", "record"]


def test_snap_rect():
    # (1) equal to a listed rectangle → that box; (2) else the box it overlaps most; (3) else the nearest box by centre
    # distance within the margin; (4) else nothing. Ties go to reading order; a list that is not four numbers is nothing.
    assert snap_rect(_r(1), BOXES, 8) == "b1" and snap_rect(_r(7), BOXES, 8) == "b7"
    assert snap_rect([12, 22, 100, 34], BOXES, 8) == "b1"  # inside b1
    assert snap_rect([0, 0, 400, 200], BOXES, 8) == "b1"  # covers every box equally: reading order
    assert snap_rect([10, 30, 110, 50], BOXES, 8) == "b2"  # 600 px² with b1, 1000 with b2
    assert snap_rect([60, 28, 60, 28], BOXES, 8) == "b1"  # no area: b1's centre
    assert snap_rect([60, 36, 60, 36], BOXES, 8) == "b1"  # 8 below b1's centre, 12 above b2's: at the margin
    assert snap_rect([60, 37, 60, 37], BOXES, 8) is None  # 9 and 11: beyond it
    assert snap_rect([10, 37, 110, 39], BOXES, 8) is None  # between b1 and b2, overlapping neither, both centres 10 away
    assert snap_rect([300, 20, 400, 36], BOXES, 8) is None
    assert snap_rect(_r(1), [], 8) is None
    assert snap_rect([60, 30, 60, 30], BOXES, 0) is None and snap_rect([12, 22, 100, 34], BOXES, 0) == "b1"  # margin 0: (3) needs equal centres
    assert snap_rect([10, 20, 110], BOXES, 8) is None and snap_rect([10, 20, 110, 36, 0], BOXES, 8) is None
    big, small = mk("b1", 0, 0, 200, 100, "outer"), mk("b2", 50, 40, 90, 56, "inner")
    assert snap_rect([50, 40, 90, 56], [big, small], 8) == "b2"  # equality before overlap: the outer box overlaps it whole too
    assert snap_rect([0, 0, 100, 100], [big, small], 8) == "b1"  # 10000 px² with the outer box, 640 with the inner
    assert snap_rect([52, 42, 88, 54], [big, small], 8) == "b1"  # inside both: the overlap ties, and reading order decides


def test_coords_unplaced_rectangles_are_dropped_and_counted():
    far = [300, 20, 400, 36]  # overlaps no box; its centre is 290 px from b1's
    answer = _coords_answer(True)
    answer["assign"].append({"rect": far, "container": "c1"})
    answer["unassigned"].append(far)
    answer["runs"][0]["boxes"].append(far)
    answer["pairs"][0]["key"].insert(0, far)
    answer["records"][0]["members"][1].append(far)
    answer["records"][0]["header"] = [far]
    answer["texts"].append({"rect": far, "text": "ghost"})
    answer["texts"].append({"rect": [50], "text": "not a rectangle"})
    out = output_model("A", True, reference="coords").model_validate(answer)
    p, counts = to_proposal("A", out, BOXES, (400, 200), 8, reference="coords")
    want, _ = to_proposal("A", output_model("A", True).model_validate(_answer(True)), BOXES, (400, 200), 8)
    assert p == want  # every reference that matched is kept, in its place
    assert counts == {"rect_unplaced": 8}


def test_coords_two_rectangles_on_one_box_collapse_inside_a_link():
    answer = _coords_answer(False)
    answer["runs"][0]["boxes"] = [_r(1), [12, 22, 100, 34], _r(2), [10, 40, 110, 50]]  # b1, b1, b2, b2
    answer["pairs"][0]["value"] = [_r(3), _r(4), [12, 62, 100, 74]]  # b3 (the key's box), b4, b3 again
    answer["records"][0]["members"] = [[_r(5), _r(5)], [_r(6)], [_r(7)]]
    answer["records"][0]["header"] = [_r(5)]  # a header on a member's box: the first occurrence in the link is kept
    out = output_model("A", False, reference="coords").model_validate(answer)
    p, counts = to_proposal("A", out, BOXES, (400, 200), 8, reference="coords")
    assert p.links == [RunLink(boxes=["b1", "b2"], joiner=" "), PairLink(key=["b3"], value=["b4"]),
                       RecordLink(members=[["b5"], ["b6"], ["b7"]], header=[])]
    assert counts == {}  # a collapse is not a dropped reference
    # a key and a value in one box: after the collapse the value is empty and repair drops the pair (link_malformed)
    answer["pairs"][0]["value"] = [[12, 62, 100, 74]]
    p, _ = to_proposal("A", output_model("A", False, reference="coords").model_validate(answer), BOXES, (400, 200), 8, reference="coords")
    assert p.links[1] == PairLink(key=["b3"], value=[])
    # two assigns on one box are two assigns: repair counts the second (second_assignment), not the conversion
    answer["assign"] = [{"rect": _r(1), "container": "c1"}, {"rect": [12, 22, 100, 34], "container": "c1"}]
    p, counts = to_proposal("A", output_model("A", False, reference="coords").model_validate(answer), BOXES, (400, 200), 8, reference="coords")
    assert [a.box for a in p.assign] == ["b1", "b1"] and counts == {}
