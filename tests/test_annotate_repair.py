import pytest

from scry.annotate.proposal import Proposal
from scry.annotate.repair import repair, repair_containers
from scry.schemas import Assign, Container, Missed, PairLink, RecordLink, RunLink, TextReading


def _ids(a: int, b: int) -> list[str]:
    return [f"b{i}" for i in range(a, b + 1)]


def _window(id: str) -> Container:
    return Container(id=id, kind="window", app="x", name=id)


def _proposal(**kw) -> Proposal:
    return Proposal(**({"containers": [], "assign": [], "unassigned": [], "links": [], "texts": None, "missed": [],
                        "description": "d"} | kw))


def case_containers():
    containers = [Container(id="c1", kind="window", app="x", name="one", covers=["c2", "c1", "zz"]),
                  Container(id="c2", kind="popup", app="x", name="two", owner="c9"),
                  Container(id="c2", kind="window", app="x", name="two again"),
                  Container(id="c3", kind="window", app="x", name="three", owner="c1"),
                  Container(id="c4", kind="popup", app="x", name="four", owner="c2"),
                  Container(id="c5", kind="popup", app="x", name="five", owner="c1")]
    return _proposal(containers=containers, assign=[Assign(box="b1", container="c5")]), ["b1"], ["b1"]


def case_assign():
    assign = [Assign(box=b, container=c) for b, c in (("b1", "c1"), ("b2", "c1"), ("b2", "c2"), ("b9", "c1"), ("b7", "c1"),
                                                      ("b3", "c7"), ("b4", "c2"))]
    return _proposal(containers=[_window("c1"), _window("c2")], assign=assign, unassigned=["b5", "b1", "b8"]), _ids(1, 6), _ids(1, 7)


def case_links():
    assign = [Assign(box=b, container="c1") for b in ("b1", "b2", "b3", "b7")] + [Assign(box=b, container="c2") for b in ("b4", "b5", "b6")]
    links = [RunLink(boxes=["b4", "b5"], joiner=" "), RunLink(boxes=["b5", "b6"], joiner=""), RunLink(boxes=["b1"], joiner=" "),
             RunLink(boxes=["b1", "b99"], joiner=" "), RunLink(boxes=["b6", "b6"], joiner=" "),
             PairLink(key=["b1"], value=["b2"]), PairLink(key=["b3"], value=["b6"]), PairLink(key=["b7"], value=["b8"]),
             PairLink(key=["b3"], value=["b3"])]
    return _proposal(containers=[_window("c1"), _window("c2")], assign=assign, unassigned=["b8"], links=links), _ids(1, 8), _ids(1, 8)


def case_records():
    header = ["b1", "b2", "b3"]
    links = [RecordLink(members=[["b4"], ["b5"], ["b6"]], header=header), RecordLink(members=[["b7"], ["b8"]], header=header),
             RecordLink(members=[["b4"], ["b7"]]), RecordLink(members=[["b10"], ["b11"]], header=["b1", "b99"]),
             RecordLink(members=[["b12"], [], ["b13"]]), RecordLink(members=[["b14"]]),
             RecordLink(members=[["b17"], ["b18"]], header=["b17"])]
    return _proposal(unassigned=_ids(1, 18), links=links), _ids(1, 18), _ids(1, 18)


def case_texts():
    texts = [TextReading(box=b, text=t) for b, t in (("b1", "x"), ("b1", "y"), ("b9", "z"), ("b4", "w"), ("b2", ""))]
    return _proposal(containers=[_window("c1")], assign=[Assign(box=b, container="c1") for b in _ids(1, 3)], texts=texts,
                     missed=[("Networking", "c1"), ("  ", None), ("Help", "c9")]), _ids(1, 3), _ids(1, 4)


def test_repair_containers():
    p, targets, frame_boxes = case_containers()
    r = repair(p, targets, frame_boxes)
    assert [c.id for c in r.containers] == ["c1", "c2", "c3", "c4", "c5"]
    assert [c.owner for c in r.containers] == [None, None, None, None, "c1"]
    assert r.containers[0].covers == ["c2"]
    assert r.counts == {"dup_container": 1, "bad_owner": 3, "bad_covers": 2}
    assert repair_containers(r.containers) == (r.containers, {})


def test_repair_assign():
    r = repair(*case_assign())
    assert [(a.box, a.container) for a in r.assign] == [("b1", "c1"), ("b2", "c1"), ("b4", "c2")]
    assert r.unassigned == ["b5", "b3", "b6"]
    assert r.counts == {"unknown_box": 1, "not_target": 1, "unknown_container": 1, "second_assignment": 1, "unplaced": 2}


def test_repair_links():
    r = repair(*case_links())
    # the pair across c1 and c2 and the pair with the unassigned b8 are kept: containers do not gate a link
    assert r.links == [RunLink(boxes=["b4", "b5"], joiner=" "), PairLink(key=["b1"], value=["b2"]),
                       PairLink(key=["b3"], value=["b6"]), PairLink(key=["b7"], value=["b8"])]
    assert r.counts == {"link_already_linked": 1, "link_malformed": 3, "link_unknown_box": 1}


def test_repair_records_and_headers():
    r = repair(*case_records())
    assert r.links == [RecordLink(members=[["b4"], ["b5"], ["b6"]], header=["b1", "b2", "b3"]),
                       RecordLink(members=[["b7"], ["b8"]], header=["b1", "b2", "b3"]),
                       RecordLink(members=[["b12"], ["b13"]], header=[])]
    assert r.counts == {"link_already_linked": 1, "link_unknown_box": 1, "link_malformed": 2}


def test_repair_texts_and_missed():
    p, targets, frame_boxes = case_texts()
    r = repair(p, targets, frame_boxes)
    assert r.texts == [TextReading(box="b1", text="x"), TextReading(box="b2", text="")]
    assert r.missed == [Missed(id="m1", text="Networking", container="c1"), Missed(id="m2", text="Help", container=None)]
    assert r.counts == {"second_text": 1, "text_unknown_box": 1, "text_not_target": 1, "text_missing": 1,
                        "missed_empty": 1, "missed_unknown_container": 1}
    p.texts = None
    r = repair(p, targets, frame_boxes)
    assert r.texts is None and "text_missing" not in r.counts


@pytest.mark.parametrize("case", [case_containers, case_assign, case_links, case_records, case_texts])
def test_every_target_ends_up_exactly_once(case):
    p, targets, frame_boxes = case()
    r = repair(p, targets, frame_boxes)
    assert sorted([a.box for a in r.assign] + r.unassigned) == sorted(targets)
