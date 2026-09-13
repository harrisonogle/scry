from pydantic import BaseModel

from vt.providers.batch import chunk_requests, strict_schema


class Inner(BaseModel):
    a: int
    b: str | None = None


class Outer(BaseModel):
    items: list[Inner]
    name: str


def test_strict_schema_requires_all_and_forbids_extras():
    s = strict_schema(Outer)
    assert s["additionalProperties"] is False and set(s["required"]) == {"items", "name"}
    inner = s["$defs"]["Inner"] if "$defs" in s else s["properties"]["items"]["items"]
    assert inner["additionalProperties"] is False and "a" in inner["required"] and "b" not in inner["required"]  # defaulted fields stay optional, as the SDK's parse() sends them


def test_chunk_requests_by_size():
    reqs = [{"custom_id": str(i), "params": {"x": "y" * 100}} for i in range(10)]
    chunks = chunk_requests(reqs, max_bytes=450)
    assert sum(len(c) for c in chunks) == 10 and all(len(c) <= 3 for c in chunks)
