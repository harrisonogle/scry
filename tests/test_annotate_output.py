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
    assert output_model("A", True, reference="coords").model_json_schema()["$defs"]["OutRunRect"]["properties"]["joiner"]["enum"] == ["", " "]


def test_coords_schema_names_boxes_by_rectangles():
    """The same shape as the ids schema; every place that named a box holds the box's rectangle [x0, y0, x1, y1],
    described once, in $defs."""
    full, group = output_model("A", True, reference="coords"), output_model("A", False, reference="coords")
    assert list(full.model_fields) == FIELDS and list(group.model_fields) == [f for f in FIELDS if f not in ("texts", "missed")]
    assert full is output_model("A", True, reference="coords") and full is not output_model("A", True)
    assert (full.__name__, group.__name__) == ("AnnotateOutACoordsT", "AnnotateOutACoordsG")
    hashes = {sha256_obj(m.model_json_schema()) for m in (full, group, output_model("A", True), output_model("A", False))}
    assert len(hashes) == 4
    schema = full.model_json_schema()
    rect = schema["$defs"]["OutRect"]
    assert rect["type"] == "array" and rect["items"] == {"type": "integer"} and "[x0, y0, x1, y1]" in rect["description"]
    assert "exactly as the user message lists it" in rect["description"] and "unscaled" in rect["description"]
    ref = {"$ref": "#/$defs/OutRect"}
    defs = schema["$defs"]
    assert defs["OutAssignRect"]["properties"]["rect"] == ref and list(defs["OutAssignRect"]["properties"]) == ["rect", "container"]
    assert schema["properties"]["unassigned"]["items"] == ref
    assert defs["OutRunRect"]["properties"]["boxes"]["items"] == ref
    assert defs["OutPairRect"]["properties"]["key"]["items"] == ref and defs["OutPairRect"]["properties"]["value"]["items"] == ref
    assert defs["OutRecordRect"]["properties"]["members"]["items"]["items"] == ref and defs["OutRecordRect"]["properties"]["header"]["items"] == ref
    assert list(defs["OutTextRect"]["properties"]) == ["rect", "text"]
    assert list(defs["OutMissed"]["properties"]) == ["text", "container"]  # no rectangle: a missed text is in no box
    text = json.dumps(schema)
    assert "box id" not in text.lower() and not re.search(r"\bb\d+\b", text)  # no id in any description
    assert not any("box" in node.get("properties", {}) for node in _walk(schema))  # no field named box
    assert text.count("A box's rectangle [x0, y0, x1, y1]") == 1  # described once
    answer = {"containers": [{"id": "c1", "kind": "window", "app": "Mail", "name": "Inbox", "owner": None, "covers": []}],
              "assign": [{"rect": [4, 4, 40, 20], "container": "c1"}, {"rect": [70, 4, 110, 20], "container": "c1"}], "unassigned": [[4, 40, 40, 56]],
              "runs": [], "pairs": [{"key": [[4, 4, 40, 20]], "value": [[70, 4, 110, 20]]}],
              "records": [{"members": [[[4, 4, 40, 20]], [[70, 4, 110, 20]]], "header": []}],
              "texts": [{"rect": [4, 4, 40, 20], "text": "From"}, {"rect": [70, 4, 110, 20], "text": ""}],
              "missed": [{"text": "Drafts", "container": None}], "description": "d"}
    out = full.model_validate(answer)
    assert out.assign[0].rect.root == [4, 4, 40, 20] and out.model_dump() == answer  # the cache stores and restores it as is
    with pytest.raises(pydantic.ValidationError):
        full.model_validate(answer | {"assign": [{"box": "b1", "container": "c1"}]})
