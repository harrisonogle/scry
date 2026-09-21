import pydantic
import pytest

from scry.annotate.output import output_model
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
    for model in (output_model("A", True), output_model("A", False)):
        schema = model.model_json_schema()
        for node in _walk(schema):
            assert not {"prefixItems", "oneOf", "discriminator", "default"} & set(node)
            if node.get("type") == "object":
                assert set(node["required"]) == set(node["properties"])
        strict = strict_schema(model)
        assert all(node["additionalProperties"] is False for node in _walk(strict) if node.get("type") == "object")
        assert schema["$defs"]["OutRun"]["properties"]["joiner"]["enum"] == ["", " "]
        assert [t["type"] for t in schema["$defs"]["OutContainer"]["properties"]["owner"]["anyOf"]] == ["string", "null"]


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
