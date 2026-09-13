import asyncio
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel

from vt.config import ModelConfig
from vt.providers.anthropic_ import AnthropicProvider
from vt.providers.base import text_block
from vt.providers.cache import CallCache


class Out(BaseModel):
    answer: str


class FakeMessages:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def parse(self, **kw):
        self.calls.append(kw)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(parsed_output=item.get("parsed"), stop_reason=item.get("stop", "end_turn"),
                               usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0),
                               content=[SimpleNamespace(type="text", text=item.get("text", ""))])


def fake_client(script):
    return SimpleNamespace(messages=FakeMessages(script))


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
    assert p.stats == {"hits": 0, "misses": 2}
