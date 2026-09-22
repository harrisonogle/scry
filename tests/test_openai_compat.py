"""The openai_compat provider against a fake HTTP client: no server, no network."""
import asyncio
import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from scry.config import Config, ModelConfig
from scry.costs import estimate_cost
from scry.providers import get_provider
from scry.providers.base import text_block
from scry.providers.cache import CallCache
from scry.providers.openai_compat import OpenAICompatProvider, convert_blocks, parse_answer


class Out(BaseModel):
    answer: str
    n: int


class FakeHttp:
    """Each `post_json` pops the next script item: an exception is raised; a string is the assistant's message text; a
    tuple (status, body) is returned as is."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def post_json(self, url, body, headers):
        self.calls.append({"url": url, "body": body, "headers": headers})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, tuple):
            return item
        return 200, {"choices": [{"message": {"role": "assistant", "content": item}, "finish_reason": "stop"}],
                     "usage": {"prompt_tokens": 10, "completion_tokens": 5, "prompt_tokens_details": {"cached_tokens": 4}}}


def run(coro):
    return asyncio.run(coro)


def cfg(**kw) -> ModelConfig:
    return ModelConfig(provider="openai_compat", model="mlx-community/fake-4bit", base_url="http://127.0.0.1:8080/v1", concurrency=1, **kw)


KW = dict(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"])


def test_convert_blocks():
    png = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"}}
    assert convert_blocks([text_block("hi"), png]) == [
        {"type": "text", "text": "hi"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}]
    with pytest.raises(ValueError):
        convert_blocks([{"type": "document"}])


def test_request_shape_and_schema_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENAI_COMPAT_API_KEY", "k")
    http = FakeHttp([json.dumps({"answer": "a", "n": 1})])
    p = OpenAICompatProvider(cfg(max_tokens=123), CallCache(tmp_path), client=http)
    r = run(p.complete(**KW))
    assert r.parsed == Out(answer="a", n=1) and r.error is None and not r.cached
    assert r.usage == {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 4, "cache_creation_input_tokens": 0}
    call = http.calls[0]
    assert call["url"] == "http://127.0.0.1:8080/v1/chat/completions" and call["headers"]["Authorization"] == "Bearer k"
    body = call["body"]
    assert body["model"] == "mlx-community/fake-4bit" and body["max_tokens"] == 123
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert body["messages"][1] == {"role": "user", "content": [{"type": "text", "text": "q"}]}
    assert body["response_format"] == {"type": "json_schema", "json_schema": {"name": "Out", "schema": Out.model_json_schema(), "strict": True}}
    # the cache serves the second call, and the record is the Anthropic provider's shape
    again = run(p.complete(**KW))
    assert again.cached and again.parsed == Out(answer="a", n=1) and len(http.calls) == 1
    assert p.stats == {"hits": 1, "misses": 1, "usage_lost": 0} and p.usage_by_stage["s"]["input_tokens"] == 10
    assert p.calls == [{"stage": "s", "wall_s": p.calls[0]["wall_s"], "prompt_tokens": 10, "completion_tokens": 5, "finish_reason": "stop", "valid": True}]


def test_parse_answer_tolerates_a_fence():
    assert parse_answer('```json\n{"answer": "a", "n": 2}\n```', Out) == Out(answer="a", n=2)
    with pytest.raises(ValueError):
        parse_answer("not json", Out)


def test_schema_failure_retries_once_with_error_text(tmp_path: Path):
    http = FakeHttp(['{"answer": "a"}', json.dumps({"answer": "c", "n": 3})])  # the first answer misses `n`
    p = OpenAICompatProvider(cfg(max_tokens=100, retry_max_tokens=200), CallCache(tmp_path), client=http)
    r = run(p.complete(**KW))
    assert r.parsed == Out(answer="c", n=3) and r.error is None
    assert r.usage["input_tokens"] == 20  # both attempts billed
    second = http.calls[1]["body"]
    assert second["max_tokens"] == 200
    assert "Your previous output was invalid: schema:" in second["messages"][1]["content"][-1]["text"]
    assert [c["valid"] for c in p.calls] == [False, True]
    # a second schema failure is terminal and cached
    http = FakeHttp(["nope", "nope"])
    p = OpenAICompatProvider(cfg(), CallCache(tmp_path / "b"), client=http)
    r = run(p.complete(**KW))
    assert r.parsed is None and r.error.startswith("schema: not JSON")
    assert run(p.complete(**KW)).cached


def test_length_retries_with_larger_budget_and_api_errors_are_transient(tmp_path: Path):
    cut = (200, {"choices": [{"message": {"content": '{"answer": "'}, "finish_reason": "length"}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
    http = FakeHttp([cut, json.dumps({"answer": "b", "n": 1})])
    p = OpenAICompatProvider(cfg(max_tokens=100, retry_max_tokens=200), CallCache(tmp_path), client=http)
    r = run(p.complete(**KW))
    assert r.parsed == Out(answer="b", n=1) and [c["body"]["max_tokens"] for c in http.calls] == [100, 200]
    http = FakeHttp([ConnectionRefusedError("refused"), (503, "busy"), json.dumps({"answer": "d", "n": 1})])
    p = OpenAICompatProvider(cfg(), CallCache(tmp_path / "b"), client=http)
    r1 = run(p.complete(**KW))
    assert r1.parsed is None and r1.error.startswith("api: ConnectionRefusedError")
    r2 = run(p.complete(**KW))
    assert r2.parsed is None and r2.error == "api: HTTP 503: busy"
    r3 = run(p.complete(**KW))
    assert r3.parsed == Out(answer="d", n=1) and not r3.cached  # nothing transient was cached


def test_provider_selection(tmp_path: Path):
    from scry.providers.anthropic_ import AnthropicProvider

    class R:
        cache_dir = tmp_path / "c"

    local = Config.model_validate({"model": {"provider": "openai_compat", "model": "mlx-community/x", "base_url": "http://127.0.0.1:8080/v1"}})
    assert isinstance(get_provider(local, R()), OpenAICompatProvider)
    with pytest.raises(ValueError):
        get_provider(Config.model_validate({"model": {"provider": "openai_compat", "model": "mlx-community/x"}}), R())  # no base_url
    with pytest.raises(ValueError):
        get_provider(Config.model_validate({"model": {"provider": "openai_compat", "model": "mlx-community/x",
                                                       "base_url": "http://h/v1", "mode": "batch"}}), R())
    assert isinstance(get_provider(Config.model_validate({"model": {"provider": "anthropic"}}), R()), AnthropicProvider)
    with pytest.raises(ValueError):
        Config.model_validate({"model": {"provider": "ollama"}})


def test_local_model_costs_nothing():
    usage = {"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    assert estimate_cost(usage, "mlx-community/Qwen3-VL-8B-Instruct-4bit") == 0.0
    assert estimate_cost(usage, "claude-opus-5") == 7.5
