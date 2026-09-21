import asyncio
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel

from scry.config import Config
from scry.providers.batch import BatchRunner, PendingRequest, chunk_requests, run_with_batches, strict_schema
from scry.providers.cache import CallCache
from scry.run import Run


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


class Out(BaseModel):
    answer: str


class FakeBatches:
    """One batch, already ended, with one succeeded result."""

    async def create(self, requests):
        return SimpleNamespace(id="B1")

    async def retrieve(self, batch_id):
        return SimpleNamespace(processing_status="ended")

    async def results(self, batch_id):
        message = SimpleNamespace(content=[SimpleNamespace(type="text", text='{"answer": "a"}')], stop_reason="end_turn",
                                  usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=3, cache_creation_input_tokens=7))

        async def one():
            yield SimpleNamespace(custom_id="k", result=SimpleNamespace(type="succeeded", message=message))
        return one()


def test_batch_results_keep_cache_creation_tokens(tmp_path: Path):
    client = SimpleNamespace(messages=SimpleNamespace(batches=FakeBatches()))
    cache = CallCache(tmp_path / "c")
    asyncio.run(BatchRunner(client, cache, Run(tmp_path / "r"), poll_s=0).run_pending([PendingRequest("k", {}, Out, "s")]))
    response = cache.get("k")["response"]
    assert response["usage"] == {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 3, "cache_creation_input_tokens": 7}
    assert response["parsed"] == {"answer": "a"}


def test_run_with_batches_runs_twice_in_batch_mode(tmp_path: Path):
    def events_of(mode: str) -> list:
        events: list = []

        class Provider:
            collecting = False

            async def run_batches(self, run):
                events.append("batches")

        async def stage_fn(run, cfg, provider):
            events.append(provider.collecting)
            return []

        cfg = Config()
        cfg.model.mode = mode
        asyncio.run(run_with_batches(Run(tmp_path / mode), cfg, Provider(), stage_fn))
        return events

    assert events_of("batch") == [True, "batches", False]
    assert events_of("sync") == [False]
