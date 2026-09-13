from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

from pydantic import BaseModel

from vt.providers.cache import CallCache
from vt.run import Run

log = logging.getLogger(__name__)


def _local_strict(schema: dict) -> dict:
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = [k for k, v in node["properties"].items() if "default" not in v]  # mirror the SDK: defaulted fields stay optional
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(schema)
    return schema


def strict_schema(model: type[BaseModel]) -> dict:
    schema = model.model_json_schema()
    try:
        from anthropic.lib._parse._transform import transform_schema

        return transform_schema(schema)
    except Exception:
        return _local_strict(schema)


@dataclass
class PendingRequest:
    key: str
    params: dict
    output_model: type[BaseModel]
    stage: str = ""


def chunk_requests(reqs: list[dict], max_bytes: int = 200 * 1024 * 1024) -> list[list[dict]]:
    chunks: list[list[dict]] = [[]]
    size = 0
    for r in reqs:
        n = len(json.dumps(r))
        if chunks[-1] and size + n > max_bytes:
            chunks.append([])
            size = 0
        chunks[-1].append(r)
        size += n
    return [c for c in chunks if c]


class BatchRunner:
    def __init__(self, client, cache: CallCache, run: Run, poll_s: float = 60.0):
        self.client, self.cache, self.run, self.poll_s = client, cache, run, poll_s

    def _state(self) -> dict:
        return json.loads(self.run.batches.read_text()) if self.run.batches.exists() else {"batches": []}

    def _save(self, st: dict) -> None:
        self.run.batches.write_text(json.dumps(st, indent=1))

    async def run_pending(self, pending: list[PendingRequest]) -> None:
        by_key = {p.key: p for p in pending}
        st = self._state()
        done_keys = {k for b in st["batches"] for k in b.get("done", [])}
        todo = [p for p in pending if p.key not in done_keys]
        open_batches = [b for b in st["batches"] if b["status"] != "ended"]
        queued = {k for b in open_batches for k in b["custom_ids"]}
        new = [p for p in todo if p.key not in queued]
        for chunk in chunk_requests([{"custom_id": p.key, "params": p.params} for p in new]):
            batch = await self.client.messages.batches.create(requests=chunk)
            st["batches"].append({"batch_id": batch.id, "custom_ids": [c["custom_id"] for c in chunk], "status": "submitted", "done": []})
            self._save(st)
        requeue: list[PendingRequest] = []
        for b in st["batches"]:
            if b["status"] == "ended":
                continue
            while True:
                info = await self.client.messages.batches.retrieve(b["batch_id"])
                if info.processing_status == "ended":
                    break
                log.info("batch %s: %s", b["batch_id"], info.processing_status)
                await asyncio.sleep(self.poll_s)
            async for res in await self.client.messages.batches.results(b["batch_id"]):
                p = by_key.get(res.custom_id)
                if p is None:
                    continue
                if res.result.type == "succeeded":
                    msg = res.result.message
                    text = next((c.text for c in msg.content if getattr(c, "type", "") == "text"), "")
                    usage = {"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens,
                             "cache_read_input_tokens": getattr(msg.usage, "cache_read_input_tokens", 0) or 0}
                    try:
                        parsed = p.output_model.model_validate_json(text).model_dump() if msg.stop_reason != "refusal" else None
                        error = "refusal" if msg.stop_reason == "refusal" else None
                    except Exception as e:
                        parsed, error = None, f"schema: {str(e)[:300]}"
                    self.cache.put(p.key, {"batch": b["batch_id"]}, {"parsed": parsed, "error": error, "usage": usage, "text": text, "stop_reason": msg.stop_reason})
                elif res.result.type == "errored" and getattr(getattr(res.result.error, "error", None), "type", "") == "invalid_request_error":
                    self.cache.put(p.key, {"batch": b["batch_id"]}, {"parsed": None, "error": f"invalid_request: {res.result.error}", "usage": {}, "text": None, "stop_reason": None})
                else:
                    requeue.append(p)
                b["done"].append(res.custom_id)
            b["status"] = "ended"
            self._save(st)
        if requeue and not getattr(self, "_retried", False):
            self._retried = True
            await self.run_pending(requeue)
        elif requeue:
            for p in requeue:  # failed twice: record it so the synchronous pass does not silently re-issue the call
                self.cache.put(p.key, {"batch": "failed-twice"}, {"parsed": None, "error": "batch: errored twice", "usage": {}, "text": None, "stop_reason": None})
