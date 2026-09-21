import asyncio
from pathlib import Path

from fakes import fake_client
from pydantic import BaseModel

from scry.config import ModelConfig
from scry.providers import is_transient
from scry.providers.anthropic_ import AnthropicProvider
from scry.providers.base import text_block
from scry.providers.cache import CallCache


class Out(BaseModel):
    answer: str


def run(coro):
    return asyncio.run(coro)


def test_cache_hit_avoids_second_call(tmp_path: Path):
    client = fake_client([{"parsed": Out(answer="a")}])
    p = AnthropicProvider(ModelConfig(), CallCache(tmp_path), client=client)
    kw = dict(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"])
    r1 = run(p.complete(**kw))
    r2 = run(p.complete(**kw))
    assert r1.parsed == Out(answer="a") and not r1.cached
    assert r2.parsed == Out(answer="a") and r2.cached
    assert len(client.messages.calls) == 1
    assert client.messages.calls[0]["output_config"] == {"effort": "low"}
    assert client.messages.calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_max_tokens_retries_once_with_larger_budget(tmp_path: Path):
    client = fake_client([{"parsed": None, "stop": "max_tokens"}, {"parsed": Out(answer="b")}])
    p = AnthropicProvider(ModelConfig(max_tokens=100, retry_max_tokens=200), CallCache(tmp_path), client=client)
    r = run(p.complete(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"]))
    assert r.parsed == Out(answer="b")
    assert [c["max_tokens"] for c in client.messages.calls] == [100, 200]


def test_refusal_is_recorded_not_raised(tmp_path: Path):
    client = fake_client([{"parsed": None, "stop": "refusal"}])
    p = AnthropicProvider(ModelConfig(), CallCache(tmp_path), client=client)
    r = run(p.complete(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"]))
    assert r.parsed is None and r.error == "refusal"


def test_schema_failure_retries_once_with_error_text(tmp_path: Path):
    client = fake_client([ValueError("1 validation error"), {"parsed": Out(answer="c")}])
    p = AnthropicProvider(ModelConfig(), CallCache(tmp_path), client=client)
    r = run(p.complete(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"]))
    assert r.parsed == Out(answer="c")
    second = client.messages.calls[1]["messages"][0]["content"]
    assert "validation error" in second[-1]["text"]


def test_transient_api_error_is_not_cached(tmp_path: Path):
    client = fake_client([RuntimeError("connection reset"), {"parsed": Out(answer="d")}])
    p = AnthropicProvider(ModelConfig(), CallCache(tmp_path), client=client)
    kw = dict(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"])
    r1 = run(p.complete(**kw))
    assert r1.parsed is None and r1.error.startswith("api:")
    r2 = run(p.complete(**kw))
    assert r2.parsed == Out(answer="d") and not r2.cached
    assert p.stats["hits"] == 0 and p.stats["misses"] == 2
    assert is_transient(r1.error) and is_transient("max_tokens")
    assert not is_transient(None) and not is_transient("refusal") and not is_transient("schema: x")


def test_usage_sums_over_retries(tmp_path: Path):
    second = {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 7}
    kw = dict(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"])
    client = fake_client([{"parsed": None, "stop": "max_tokens"}, {"parsed": Out(answer="b"), "usage": second}])
    p = AnthropicProvider(ModelConfig(), CallCache(tmp_path / "a"), client=client)
    r = run(p.complete(**kw))
    summed = {"input_tokens": 20, "output_tokens": 10, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 7}
    assert r.usage == summed and p.usage_by_stage["s"] == summed and p.stats["usage_lost"] == 0
    again = run(p.complete(**kw))
    assert again.cached and again.usage == summed
    # the gap, made visible: a reply the SDK's parse helper rejects was billed, and its usage never arrives
    client = fake_client([ValueError("1 validation error"), {"parsed": Out(answer="c"), "usage": second}])
    p = AnthropicProvider(ModelConfig(), CallCache(tmp_path / "b"), client=client)
    r = run(p.complete(**kw))
    assert r.parsed.answer == "c" and r.usage == second and p.stats["usage_lost"] == 1
