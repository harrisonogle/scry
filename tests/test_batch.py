import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from scry.config import Config
from scry.providers.anthropic_ import AnthropicProvider
from scry.providers.base import text_block
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


class Killed(Exception):
    pass


class FakeBatches:
    """Every batch has ended when it is retrieved. `outcomes[i]` gives the result type of a custom id in the i-th batch
    created (a request it does not name succeeded); `created` lists each batch's custom ids; the first `retrieve` of
    the batch `killed` raises, as if the process were killed between that submission and its results."""

    def __init__(self, outcomes=(), killed: str | None = None):
        self.outcomes, self.killed, self.created = list(outcomes), killed, []

    async def create(self, requests):
        self.created.append([r["custom_id"] for r in requests])
        return SimpleNamespace(id=f"B{len(self.created)}")

    async def retrieve(self, batch_id):
        if batch_id == self.killed:
            self.killed = None
            raise Killed
        return SimpleNamespace(processing_status="ended")

    async def results(self, batch_id):
        n = int(batch_id[1:]) - 1
        outcomes = self.outcomes[n] if n < len(self.outcomes) else {}
        message = SimpleNamespace(content=[SimpleNamespace(type="text", text='{"answer": "a"}')], stop_reason="end_turn",
                                  usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=3, cache_creation_input_tokens=7))

        async def each():
            for k in self.created[n]:
                kind = outcomes.get(k, "succeeded")
                if kind == "succeeded":
                    yield SimpleNamespace(custom_id=k, result=SimpleNamespace(type="succeeded", message=message))
                elif kind == "errored":
                    error = SimpleNamespace(type="error", error=SimpleNamespace(type="api_error", message="overloaded"))
                    yield SimpleNamespace(custom_id=k, result=SimpleNamespace(type="errored", error=error))
                else:
                    yield SimpleNamespace(custom_id=k, result=SimpleNamespace(type=kind))
        return each()


def batch_client(*outcomes: dict, killed: str | None = None):
    return SimpleNamespace(messages=SimpleNamespace(batches=FakeBatches(outcomes, killed)))


def test_batch_results_keep_cache_creation_tokens(tmp_path: Path):
    client = batch_client()
    cache = CallCache(tmp_path / "c")
    asyncio.run(BatchRunner(client, cache, Run(tmp_path / "r"), poll_s=0).run_pending([PendingRequest("k", {}, Out, "s")]))
    response = cache.get("k")["response"]
    assert response["usage"] == {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 3, "cache_creation_input_tokens": 7}
    assert response["parsed"] == {"answer": "a"}


def test_errored_and_expired_results_are_resubmitted_once(tmp_path: Path):
    client, cache, run = batch_client({"e": "errored", "x": "expired"}), CallCache(tmp_path / "c"), Run(tmp_path / "r")
    pending = [PendingRequest(k, {}, Out, "s") for k in ("ok", "e", "x")]
    asyncio.run(BatchRunner(client, cache, run, poll_s=0).run_pending(pending))
    assert client.messages.batches.created == [["ok", "e", "x"], ["e", "x"]]  # the second batch: only what failed
    assert all(cache.get(k)["response"]["parsed"] == {"answer": "a"} for k in ("ok", "e", "x"))
    state = json.loads(run.batches.read_text())["batches"]
    assert [(b["status"], b["done"]) for b in state] == [("ended", ["ok"]), ("ended", ["e", "x"])]


def test_a_request_that_fails_twice_gets_a_terminal_record(tmp_path: Path):
    client, cache, run = batch_client({"e": "errored"}, {"e": "canceled"}), CallCache(tmp_path / "c"), Run(tmp_path / "r")
    asyncio.run(BatchRunner(client, cache, run, poll_s=0).run_pending([PendingRequest(k, {}, Out, "s") for k in ("ok", "e")]))
    assert client.messages.batches.created == [["ok", "e"], ["e"]]  # one resubmission, never a third batch
    response = cache.get("e")["response"]  # what the stage's second pass reads, instead of calling at the sync price
    assert response["parsed"] is None and response["error"] == "batch: failed twice, last result canceled"
    assert cache.get("ok")["response"]["error"] is None


def test_a_killed_process_resumes_its_batches(tmp_path: Path):
    def killed_then_resumed(name: str, client) -> CallCache:
        cache, run = CallCache(tmp_path / name / "c"), Run(tmp_path / name / "r")
        pending = [PendingRequest(k, {}, Out, "s") for k in ("ok", "e")]
        with pytest.raises(Killed):
            asyncio.run(BatchRunner(client, cache, run, poll_s=0).run_pending(pending))
        asyncio.run(BatchRunner(client, cache, run, poll_s=0).run_pending([p for p in pending if cache.get(p.key) is None]))
        return cache

    client = batch_client(killed="B1")  # after the first submission: nothing is submitted again
    cache = killed_then_resumed("first", client)
    assert client.messages.batches.created == [["ok", "e"]] and cache.get("e")["response"]["parsed"] == {"answer": "a"}
    client = batch_client({"e": "errored"}, {"e": "errored"}, killed="B2")  # after the resubmission
    cache = killed_then_resumed("second", client)
    assert client.messages.batches.created == [["ok", "e"], ["e"]]  # batches.json says `e` has had its second try
    assert cache.get("e")["response"]["error"] == "batch: failed twice, last result errored"


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


def test_answers_of_the_runs_own_batches_are_not_cache_hits(tmp_path: Path):
    cfg = Config()
    cfg.model.mode = "batch"

    async def stage_fn(run, cfg, provider):
        return [await provider.complete(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low",
                                        prompt_version="v1", input_hashes=[h]) for h in ("a", "b")]

    def stats_of(name: str) -> dict:
        provider = AnthropicProvider(cfg.model, CallCache(tmp_path / "c"), client=batch_client())
        results = asyncio.run(run_with_batches(Run(tmp_path / name), cfg, provider, stage_fn))
        assert [r.parsed for r in results] == [Out(answer="a")] * 2
        return provider.stats

    # the second pass reads every batch result out of the call cache by design: those calls were paid for in this run
    assert stats_of("cold") == {"hits": 0, "misses": 2, "usage_lost": 0}
    # the same calls again, now answered by what the cold run left: a run that is not cold is flagged, each hit once
    assert stats_of("warm") == {"hits": 2, "misses": 0, "usage_lost": 0}
