"""A second provider: any server that speaks OpenAI's `/v1/chat/completions` with `response_format` json_schema, meant
for a model served on this machine (mlx_vlm.server, llama.cpp, vLLM). Same call cache and cache-key rule as the
Anthropic provider: the key holds the model name, so a local answer never collides with an API one. `effort` is
ignored (the local runtime has no such knob) and stays in the key. Every call is synchronous; there is no batch mode."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from typing import Protocol

from pydantic import BaseModel, ValidationError

from scry.config import ModelConfig
from scry.costs import add_usage
from scry.jsonl import sha256_obj
from scry.providers.base import VlmResult, text_block
from scry.providers.cache import CallCache

log = logging.getLogger(__name__)

API_KEY_VAR = "OPENAI_COMPAT_API_KEY"  # a local server wants none; the header carries "none" then
TIMEOUT_S = 3600.0  # a local model answers a large frame in minutes, not seconds


class HttpClient(Protocol):
    async def post_json(self, url: str, body: dict, headers: dict) -> tuple[int, object]:
        """POST `body` as JSON; return the status code and the decoded JSON body (or the raw text when not JSON)."""
        ...


class UrllibClient:
    """The default client: the standard library on a thread, so the event loop stays free (no new dependency)."""

    async def post_json(self, url: str, body: dict, headers: dict) -> tuple[int, object]:
        return await asyncio.to_thread(self._post, url, body, headers)

    @staticmethod
    def _post(url: str, body: dict, headers: dict) -> tuple[int, object]:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                status, text = resp.status, resp.read().decode()
        except urllib.error.HTTPError as e:
            status, text = e.code, e.read().decode(errors="replace")
        try:
            return status, json.loads(text)
        except ValueError:
            return status, text

    async def close(self) -> None:
        return None


def convert_blocks(blocks: list[dict]) -> list[dict]:
    """Anthropic-style content blocks as OpenAI content parts: text stays text, a base64 image becomes an image_url data URL."""
    out = []
    for b in blocks:
        if b.get("type") == "text":
            out.append({"type": "text", "text": b["text"]})
        elif b.get("type") == "image":
            src = b["source"]
            if src.get("type") == "base64":
                url = f"data:{src['media_type']};base64,{src['data']}"
            elif src.get("type") == "url":
                url = src["url"]
            else:
                raise ValueError(f"image source {src.get('type')!r} has no OpenAI form")
            out.append({"type": "image_url", "image_url": {"url": url}})
        else:
            raise ValueError(f"block type {b.get('type')!r} has no OpenAI form")
    return out


_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def parse_answer(text: str, output_model: type[BaseModel]) -> BaseModel:
    """The message text as the output model: a code fence around the JSON is tolerated; anything else is a schema error."""
    m = _FENCE.match(text)
    body = m.group(1) if m else text
    try:
        data = json.loads(body)
    except ValueError as e:
        raise ValueError(f"not JSON: {e}") from None
    return output_model.model_validate(data)


class OpenAICompatProvider:
    def __init__(self, cfg: ModelConfig, cache: CallCache, client: HttpClient | None = None):
        if not cfg.base_url:
            raise ValueError('[model] provider = "openai_compat" needs base_url, e.g. "http://127.0.0.1:8080/v1"')
        self.client = client if client is not None else UrllibClient()
        self.cfg = cfg
        self.model = cfg.model
        self.url = cfg.base_url.rstrip("/") + "/chat/completions"
        self.api_key = os.environ.get(API_KEY_VAR) or "none"
        self.cache = cache
        self.sem = asyncio.Semaphore(cfg.concurrency)
        self.stats = {"hits": 0, "misses": 0, "usage_lost": 0}
        self.usage_by_stage: dict[str, dict] = {}
        self.calls: list[dict] = []  # one record per HTTP call: stage, wall seconds, tokens, whether the JSON validated

    def _account(self, stage: str, usage: dict) -> None:
        acc = self.usage_by_stage.setdefault(stage, {})
        for k, v in usage.items():
            acc[k] = acc.get(k, 0) + (v or 0)

    async def complete(self, *, stage: str, system: str, blocks: list[dict], output_model: type[BaseModel], effort: str,
                       prompt_version: str, input_hashes: list[str]) -> VlmResult:
        schema_hash = sha256_obj(output_model.model_json_schema())
        key = CallCache.key(stage, self.model, effort, self.cfg.max_tokens, prompt_version, schema_hash, input_hashes)
        hit = self.cache.get(key)
        if hit is not None:
            self.stats["hits"] += 1
            resp = hit["response"]
            parsed = output_model.model_validate(resp["parsed"]) if resp.get("parsed") is not None else None
            return VlmResult(parsed, resp.get("error"), resp.get("usage", {}), resp.get("text"), True, resp.get("stop_reason"))
        async with self.sem:
            r = await self._call(stage, system, blocks, output_model, self.cfg.max_tokens)
            usage = add_usage({}, r.usage)
            if r.stop_reason == "max_tokens":
                r = await self._call(stage, system, blocks, output_model, self.cfg.retry_max_tokens)
                add_usage(usage, r.usage)
            if r.error and r.error.startswith("schema"):
                retry_blocks = blocks + [text_block(f"Your previous output was invalid: {r.error}. Return JSON that matches the schema exactly.")]
                r = await self._call(stage, system, retry_blocks, output_model, self.cfg.retry_max_tokens)
                add_usage(usage, r.usage)
            r.usage = usage
        self.stats["misses"] += 1
        self._account(stage, r.usage)
        if r.error is None or r.error == "refusal" or r.error.startswith("schema"):  # terminal outcomes only; API blips retry next run
            self.cache.put(key, {"stage": stage, "model": self.model, "effort": effort, "prompt_version": prompt_version,
                                 "schema_hash": schema_hash, "input_hashes": input_hashes},
                           {"parsed": r.parsed.model_dump() if r.parsed is not None else None, "error": r.error,
                            "usage": r.usage, "text": r.raw_text, "stop_reason": r.stop_reason})
        return r

    def request(self, system: str, blocks: list[dict], output_model: type[BaseModel], max_tokens: int) -> dict:
        return {"model": self.model, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": convert_blocks(blocks)}],
                "response_format": {"type": "json_schema",
                                    "json_schema": {"name": output_model.__name__, "schema": output_model.model_json_schema(), "strict": True}}}

    async def _call(self, stage: str, system: str, blocks: list[dict], output_model: type[BaseModel], max_tokens: int) -> VlmResult:
        t0 = time.monotonic()
        try:
            status, body = await self.client.post_json(self.url, self.request(system, blocks, output_model, max_tokens),
                                                       {"Authorization": f"Bearer {self.api_key}"})
        except Exception as e:  # connection refused, timeout: transient, retried next run
            log.warning("model call failed: %s", e)
            return VlmResult(None, f"api: {type(e).__name__}: {str(e)[:300]}")
        wall = time.monotonic() - t0
        if status != 200 or not isinstance(body, dict):
            log.warning("model call failed: HTTP %s: %s", status, str(body)[:300])
            return VlmResult(None, f"api: HTTP {status}: {str(body)[:300]}")
        u = body.get("usage") or {}
        details = u.get("prompt_tokens_details") or {}
        usage = {"input_tokens": u.get("prompt_tokens", 0) or 0, "output_tokens": u.get("completion_tokens", 0) or 0,
                 "cache_read_input_tokens": details.get("cached_tokens", 0) or 0, "cache_creation_input_tokens": 0}
        choice = (body.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content")
        if isinstance(text, list):  # some servers return content parts
            text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
        finish = choice.get("finish_reason")
        record = {"stage": stage, "wall_s": round(wall, 2), "prompt_tokens": usage["input_tokens"],
                  "completion_tokens": usage["output_tokens"], "finish_reason": finish, "valid": False}
        self.calls.append(record)
        if finish == "length":
            log.info("openai_compat %s: %.1fs prompt=%d completion=%d max_tokens", stage, wall, usage["input_tokens"], usage["output_tokens"])
            return VlmResult(None, "max_tokens", usage, text, False, "max_tokens")
        if finish == "content_filter":
            return VlmResult(None, "refusal", usage, text, False, "refusal")
        try:
            parsed = parse_answer(text or "", output_model)
        except (ValidationError, ValueError) as e:
            log.info("openai_compat %s: %.1fs prompt=%d completion=%d schema error", stage, wall, usage["input_tokens"], usage["output_tokens"])
            return VlmResult(None, f"schema: {str(e)[:500]}", usage, text, False, finish)
        record["valid"] = True
        log.info("openai_compat %s: %.1fs prompt=%d completion=%d ok", stage, wall, usage["input_tokens"], usage["output_tokens"])
        return VlmResult(parsed, None, usage, text, False, finish)
