import json
import re

import pydantic
import pytest

from scry.annotate.output import output_model
from scry.jsonl import sha256_obj
from scry.providers.batch import strict_schema

FIELDS = ["containers", "assign", "unassigned", "runs", "pairs", "records", "texts", "missed", "description"]


def test_fields_of_arm_a():
    assert list(output_model("A", True).model_fields) == FIELDS
    assert list(output_model("A", False).model_fields) == [f for f in FIELDS if f not in ("texts", "missed")]
    assert output_model("A", True) is output_model("A", True)  # one class, one schema hash


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def test_schema_is_strict_friendly():
    for model in (output_model("A", True), output_model("A", False),
                  output_model("A", True, reference="coords"), output_model("A", False, reference="coords")):
        schema = model.model_json_schema()
        for node in _walk(schema):
            assert not {"prefixItems", "oneOf", "discriminator", "default"} & set(node)
            if node.get("type") == "object":
                assert set(node["required"]) == set(node["properties"])
        strict = strict_schema(model)
        assert all(node["additionalProperties"] is False for node in _walk(strict) if node.get("type") == "object")
        assert [t["type"] for t in schema["$defs"]["OutContainer"]["properties"]["owner"]["anyOf"]] == ["string", "null"]
    assert output_model("A", True).model_json_schema()["$defs"]["OutRun"]["properties"]["joiner"]["enum"] == ["", " "]
    assert output_model("A", True, reference="coords").model_json_schema()["$defs"]["OutRunAt"]["properties"]["joiner"]["enum"] == ["", " "]


def test_coords_schema_names_boxes_by_points():
    """The same shape as the ids schema; every place that named a box holds a point [x, y], described once, in $defs."""
    full, group = output_model("A", True, reference="coords"), output_model("A", False, reference="coords")
    assert list(full.model_fields) == FIELDS and list(group.model_fields) == [f for f in FIELDS if f not in ("texts", "missed")]
    assert full is output_model("A", True, reference="coords") and full is not output_model("A", True)
    assert (full.__name__, group.__name__) == ("AnnotateOutACoordsT", "AnnotateOutACoordsG")
    hashes = {sha256_obj(m.model_json_schema()) for m in (full, group, output_model("A", True), output_model("A", False))}
    assert len(hashes) == 4
    schema = full.model_json_schema()
    point = schema["$defs"]["OutPoint"]
    assert point["type"] == "array" and point["items"] == {"type": "integer"} and "[x, y]" in point["description"]
    assert "inside" in point["description"] and "unscaled" in point["description"]
    ref = {"$ref": "#/$defs/OutPoint"}
    defs = schema["$defs"]
    assert defs["OutAssignAt"]["properties"]["point"] == ref and list(defs["OutAssignAt"]["properties"]) == ["point", "container"]
    assert schema["properties"]["unassigned"]["items"] == ref
    assert defs["OutRunAt"]["properties"]["boxes"]["items"] == ref
    assert defs["OutPairAt"]["properties"]["key"]["items"] == ref and defs["OutPairAt"]["properties"]["value"]["items"] == ref
    assert defs["OutRecordAt"]["properties"]["members"]["items"]["items"] == ref and defs["OutRecordAt"]["properties"]["header"]["items"] == ref
    assert list(defs["OutTextAt"]["properties"]) == ["point", "text"]
    assert list(defs["OutMissed"]["properties"]) == ["text", "container"]  # no point: a missed text is in no box
    text = json.dumps(schema)
    assert "box id" not in text.lower() and not re.search(r"\bb\d+\b", text)  # no id in any description
    assert not any("box" in node.get("properties", {}) for node in _walk(schema))  # no field named box
    assert text.count("A point [x, y]") == 1  # described once
    answer = {"containers": [{"id": "c1", "kind": "window", "app": "Mail", "name": "Inbox", "owner": None, "covers": []}],
              "assign": [{"point": [30, 12], "container": "c1"}, {"point": [90, 12], "container": "c1"}], "unassigned": [[5, 40]],
              "runs": [], "pairs": [{"key": [[30, 12]], "value": [[90, 12]]}], "records": [{"members": [[[30, 12]], [[90, 12]]], "header": []}],
              "texts": [{"point": [30, 12], "text": "From"}, {"point": [90, 12], "text": ""}],
              "missed": [{"text": "Drafts", "container": None}], "description": "d"}
    out = full.model_validate(answer)
    assert out.assign[0].point.root == [30, 12] and out.model_dump() == answer  # the cache stores and restores it as is
    with pytest.raises(pydantic.ValidationError):
        full.model_validate(answer | {"assign": [{"box": "b1", "container": "c1"}]})


def test_answer_round_trip():
    answer = {"containers": [{"id": "c1", "kind": "window", "app": "Mail", "name": "Inbox", "owner": None, "covers": []}],
              "assign": [{"box": "b1", "container": "c1"}, {"box": "b2", "container": "c1"}], "unassigned": [],
              "runs": [], "pairs": [{"key": ["b1"], "value": ["b2"]}], "records": [],
              "texts": [{"box": "b1", "text": "From"}, {"box": "b2", "text": ""}],
              "missed": [{"text": "Drafts", "container": None}], "description": "d"}
    out = output_model("A", True).model_validate(answer)
    assert out.texts[1].text == "" and out.missed[0].container is None
    del answer["unassigned"]
    with pytest.raises(pydantic.ValidationError):
        output_model("A", True).model_validate(answer)
