from annotate_fixtures import mk

from scry.annotate.output import output_model
from scry.annotate.proposal import snap_point, to_proposal
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


# ---------- reference = "coords": every point snapped to a box id before repair sees the proposal ----------
def _coords_answer(transcribe: bool) -> dict:
    """The answer of `_answer` with points for ids: (50, 28) is inside b1, (50, 48) inside b2, and so on down the column."""
    def p(i: int) -> list[int]:
        return [50, 20 * i + 8]
    answer = {"containers": [{"id": "c1", "kind": "window", "app": "Mail", "name": "Inbox", "owner": None, "covers": []}],
              "assign": [{"point": p(1), "container": "c1"}, {"point": p(2), "container": "c1"}], "unassigned": [p(3)],
              "runs": [{"boxes": [p(1), p(2)], "joiner": " "}], "pairs": [{"key": [p(3)], "value": [p(4)]}],
              "records": [{"members": [[p(5)], [p(6)], [p(7)]], "header": []}], "description": "d"}
    if transcribe:
        answer |= {"texts": [{"point": p(1), "text": "a"}, {"point": p(2), "text": ""}],
                   "missed": [{"text": "Networking", "container": "c1"}]}
    return answer


def test_coords_points_become_the_arm_a_proposal():
    """`margin_px(BOXES, [], 0.5) == 8`; every point of `_coords_answer` is inside its box, so the proposal is `_answer`'s."""
    assert margin_px(BOXES, [], 0.5) == 8
    out = output_model("A", True, reference="coords").model_validate(_coords_answer(True))
    p, counts = to_proposal("A", out, BOXES, (400, 200), 8, reference="coords")
    want, _ = to_proposal("A", output_model("A", True).model_validate(_answer(True)), BOXES, (400, 200), 8)
    assert p == want and counts == {}
    group, counts = to_proposal("A", output_model("A", False, reference="coords").model_validate(_coords_answer(False)), BOXES, (400, 200), 8, reference="coords")
    assert group.texts is None and group.missed == [] and counts == {}
    assert [l.kind for l in group.links] == ["run", "pair", "record"]


def test_snap_point():
    # inside → that box; several → the smallest area; outside → the nearest within the margin (point-to-rectangle
    # distance, x1 and y1 exclusive as the plan's formula has them); beyond the margin → nothing
    big, small = mk("b1", 0, 0, 200, 100, "outer"), mk("b2", 50, 40, 90, 56, "inner")
    assert snap_point([60, 48], [big, small], 8) == "b2"
    assert snap_point([10, 10], [big, small], 8) == "b1"
    assert snap_point([50, 28], BOXES, 8) == "b1"
    assert snap_point([118, 28], BOXES, 8) == "b1"  # 8 px right of b1's x1: at the margin
    assert snap_point([119, 28], BOXES, 8) is None  # 9 px: beyond it
    assert snap_point([50, 18], BOXES, 8) == "b1"  # 2 px above b1 (y0 = 20)
    assert snap_point([5, 14], BOXES, 8) == "b1"  # diagonal: hypot(5, 6) is 7.8 from b1's corner
    assert snap_point([4, 13], BOXES, 8) is None  # hypot(6, 7) is 9.2
    assert snap_point([50, 38], BOXES, 8) == "b1"  # 2 px below b1's y1 (36) and 2 px above b2's y0 (40): a tie goes to reading order
    assert snap_point([300, 28], BOXES, 8) is None
    assert snap_point([50, 28], [], 8) is None
    assert snap_point([50, 28], BOXES, 0) == "b1" and snap_point([111, 28], BOXES, 0) is None  # margin 0: inside only
    assert snap_point([50], BOXES, 8) is None and snap_point([50, 28, 1], BOXES, 8) is None  # not a point


def test_coords_unplaced_points_are_dropped_and_counted():
    far = [300, 28]  # 190 px from b1: beyond every margin
    answer = _coords_answer(True)
    answer["assign"].append({"point": far, "container": "c1"})
    answer["unassigned"].append(far)
    answer["runs"][0]["boxes"].append(far)
    answer["pairs"][0]["key"].insert(0, far)
    answer["records"][0]["members"][1].append(far)
    answer["records"][0]["header"] = [far]
    answer["texts"].append({"point": far, "text": "ghost"})
    answer["texts"].append({"point": [50], "text": "not a point"})
    out = output_model("A", True, reference="coords").model_validate(answer)
    p, counts = to_proposal("A", out, BOXES, (400, 200), 8, reference="coords")
    want, _ = to_proposal("A", output_model("A", True).model_validate(_answer(True)), BOXES, (400, 200), 8)
    assert p == want  # every reference that snapped is kept, in its place
    assert counts == {"point_unplaced": 8}


def test_coords_two_points_on_one_box_collapse_inside_a_link():
    answer = _coords_answer(False)
    answer["runs"][0]["boxes"] = [[50, 28], [60, 28], [50, 48], [118, 48]]  # b1, b1, b2, b2 (the last by margin)
    answer["pairs"][0]["value"] = [[50, 68], [50, 88], [60, 68]]  # b3 (the key's box), b4, b3 again
    answer["records"][0]["members"] = [[[50, 108], [50, 108]], [[50, 128]], [[50, 148]]]
    answer["records"][0]["header"] = [[50, 108]]  # a header on a member's box: the first occurrence in the link is kept
    out = output_model("A", False, reference="coords").model_validate(answer)
    p, counts = to_proposal("A", out, BOXES, (400, 200), 8, reference="coords")
    assert p.links == [RunLink(boxes=["b1", "b2"], joiner=" "), PairLink(key=["b3"], value=["b4"]),
                       RecordLink(members=[["b5"], ["b6"], ["b7"]], header=[])]
    assert counts == {}  # a collapse is not a dropped reference
    # a key and a value in one box: after the collapse the value is empty and repair drops the pair (link_malformed)
    answer["pairs"][0]["value"] = [[60, 68]]
    p, _ = to_proposal("A", output_model("A", False, reference="coords").model_validate(answer), BOXES, (400, 200), 8, reference="coords")
    assert p.links[1] == PairLink(key=["b3"], value=[])
    # two assigns on one box are two assigns: repair counts the second (second_assignment), not the conversion
    answer["assign"] = [{"point": [50, 28], "container": "c1"}, {"point": [60, 28], "container": "c1"}]
    p, counts = to_proposal("A", output_model("A", False, reference="coords").model_validate(answer), BOXES, (400, 200), 8, reference="coords")
    assert [a.box for a in p.assign] == ["b1", "b1"] and counts == {}
