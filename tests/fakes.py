"""Fake model clients shared by the tests (plans 2 and 3): no network, no API call."""
import re
from types import SimpleNamespace
from typing import Callable

from pydantic import BaseModel

from scry.providers import VlmResult

USAGE = {"input_tokens": 100, "output_tokens": 20, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 400}


class FakeMessages:
    """Stands in for `client.messages`: each `parse` pops the next script item; an exception is raised, a dict becomes a
    response (`parsed`, `stop`, `text`, and optionally `usage`)."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def parse(self, **kw):
        self.calls.append(kw)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        usage = {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0} | item.get("usage", {})
        return SimpleNamespace(parsed_output=item.get("parsed"), stop_reason=item.get("stop", "end_turn"),
                               usage=SimpleNamespace(**usage), content=[SimpleNamespace(type="text", text=item.get("text", ""))])


def fake_client(script):
    return SimpleNamespace(messages=FakeMessages(script))


class AnswerProvider:
    """A provider whose answers come from a function of the call's keyword arguments: a model is a parsed answer, a
    string is an error. It has no call cache: every `complete` is a call."""
    model = "fake-model"

    def __init__(self, answer: Callable[[dict], BaseModel | str]):
        self.answer = answer
        self.calls: list[dict] = []
        self.stats = {"hits": 0, "misses": 0}

    async def complete(self, **kw) -> VlmResult:
        self.calls.append(kw)
        out = self.answer(kw)
        if isinstance(out, str):
            return VlmResult(None, out, dict(USAGE))
        return VlmResult(out, None, dict(USAGE))


def call_frame(kw: dict) -> int:
    """The frame a call is about: the number after the word `frame` in its first text block."""
    first = next(b["text"] for b in kw["blocks"] if b["type"] == "text")
    return int(re.search(r"frame (\d+)", first).group(1))
