import pytest
from annotate_fixtures import mk

from scry.annotate.output import output_model
from scry.annotate.proposal import to_proposal
from scry.schemas import TextReading

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


def test_arm_d_takes_the_arm_a_path():
    out = output_model("D", True).model_validate(_answer(True))
    assert to_proposal("D", out, BOXES, (400, 200), 8) == to_proposal("A", out, BOXES, (400, 200), 8)
    with pytest.raises(ValueError):
        to_proposal("B", out, BOXES, (400, 200), 8)
