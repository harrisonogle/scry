from __future__ import annotations

import asyncio
import logging

from pydantic import BaseModel, ValidationError

from scry.config import ModelConfig
from scry.costs import add_usage
from scry.jsonl import sha256_obj
from scry.providers.base import VlmResult, text_block
from scry.providers.cache import CallCache

log = logging.getLogger(__name__)


class AnthropicProvider:
    def __init__(self, cfg: ModelConfig, cache: CallCache, client=None):
        if client is None:
            import anthropic

            client = anthropic.AsyncAnthropic()
        self.client = client
        self.cfg = cfg
        self.model = cfg.model
        self.cache = cache
        self.sem = asyncio.Semaphore(cfg.concurrency)
        self.stats = {"hits": 0, "misses": 0, "usage_lost": 0}  # usage_lost: attempts billed whose usage never arrived
        self.usage_by_stage: dict[str, dict] = {}
        self.collecting = False   # batch mode: record cache misses instead of calling (Task 19)
        self.pending: list = []

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
        if self.collecting:
            from scry.providers.batch import PendingRequest, strict_schema

            params = {"model": self.model, "max_tokens": self.cfg.max_tokens,
                      "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                      "messages": [{"role": "user", "content": blocks}],
                      "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": strict_schema(output_model)}}}
            self.pending.append(PendingRequest(key, params, output_model, stage))
            return VlmResult(None, "pending")
        async with self.sem:
            r = await self._call(system, blocks, output_model, effort, self.cfg.max_tokens)
            usage = add_usage({}, r.usage)  # every attempt was billed: the record carries their sum
            if r.stop_reason == "max_tokens":
                r = await self._call(system, blocks, output_model, effort, self.cfg.retry_max_tokens)
                add_usage(usage, r.usage)
            if r.error and r.error.startswith("schema"):
                retry_blocks = blocks + [text_block(f"Your previous output was invalid: {r.error}. Return JSON that matches the schema exactly.")]
                r = await self._call(system, retry_blocks, output_model, effort, self.cfg.retry_max_tokens)
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

    async def run_batches(self, run) -> None:
        from scry.providers.batch import BatchRunner

        await BatchRunner(self.client, self.cache, run).run_pending(self.pending)
        self.pending = []

    async def _call(self, system: str, blocks: list[dict], output_model: type[BaseModel], effort: str, max_tokens: int) -> VlmResult:
        try:
            resp = await self.client.messages.parse(
                model=self.model, max_tokens=max_tokens,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": blocks}],
                output_format=output_model, output_config={"effort": effort},
            )
        except (ValidationError, ValueError) as e:  # raised inside the SDK's parse helper: the attempt was billed, its usage is lost
            self.stats["usage_lost"] += 1
            return VlmResult(None, f"schema: {str(e)[:500]}")
        except Exception as e:  # anthropic.APIError family: retried by the SDK; record and continue
            log.warning("model call failed: %s", e)
            return VlmResult(None, f"api: {type(e).__name__}: {str(e)[:300]}")
        u = resp.usage
        usage = {"input_tokens": getattr(u, "input_tokens", 0), "output_tokens": getattr(u, "output_tokens", 0),
                 "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
                 "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0}
        text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), None)
        if resp.stop_reason == "refusal":
            return VlmResult(None, "refusal", usage, text, False, "refusal")
        if resp.stop_reason == "max_tokens":
            return VlmResult(None, "max_tokens", usage, text, False, "max_tokens")
        parsed = getattr(resp, "parsed_output", None)
        if parsed is None:
            return VlmResult(None, "schema: no parsed output", usage, text, False, resp.stop_reason)
        return VlmResult(parsed, None, usage, text, False, resp.stop_reason)
