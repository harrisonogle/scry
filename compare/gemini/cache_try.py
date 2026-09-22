"""One try of the Gemini API's explicit context caching for the video, to report whether it works for this use and what
it costs. The interactions call shape of outline.py (processing="agentic") has no cached_content field in google-genai
2.23 (CreateModelInteraction: input, model, generation_config, previous_interaction_id, response_format, ...), and in
that mode the video is fetched through the mode's own processing calls, not held in the prompt, so a prompt cache has
nothing to hold. Explicit caching exists on the other path: caches.create with the uploaded file, then
models.generate_content with cached_content. This script does that once for Q1 and records the usage and the cache's
token count. Writes runs/compare-gemini/cache-try.json. The cache is deleted at the end."""
from __future__ import annotations

import json
import time

from google.genai import types

from compare.gemini.common import GEMINI_MODEL, LIST_PRICES, OUT, Ledger, gemini_client, questions, setup, uploaded_video, video_path
from compare.gemini.g1 import prompt_for


def main() -> None:
    setup()
    client = gemini_client()
    uri, mime, _ = uploaded_video(client, video_path())
    q1 = questions()[0]
    out: dict = {"model": GEMINI_MODEL, "path": "caches.create(contents=[video file]) then models.generate_content(cached_content=...)"}
    pin, pout = LIST_PRICES[GEMINI_MODEL]
    ledger = Ledger()
    cache = None
    try:
        t0 = time.perf_counter()
        cache = client.caches.create(model=GEMINI_MODEL, config=types.CreateCachedContentConfig(
            display_name="compare-gemini video", ttl="900s",
            contents=[types.Content(role="user", parts=[types.Part.from_uri(file_uri=uri, mime_type=mime)])]))
        out["create_seconds"] = round(time.perf_counter() - t0, 1)
        out["cache"] = cache.model_dump(exclude_none=True, mode="json")
        cached_tokens = (cache.usage_metadata.total_token_count if cache.usage_metadata else 0) or 0
        # list price basis: cache creation billed at the input rate for the cached tokens (the price page's rule for
        # explicit caching), storage per token-hour not known for this model and not counted
        out["create_dollars_at_input_rate"] = round(cached_tokens * pin / 1e6, 4)
        ledger.add("gemini", "cache-try", "caches.create", out["create_dollars_at_input_rate"], out["create_seconds"], True,
                   f"{cached_tokens} cached tokens")
        t1 = time.perf_counter()
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt_for(q1.question),
                                              config=types.GenerateContentConfig(cached_content=cache.name))
        out["call_seconds"] = round(time.perf_counter() - t1, 1)
        um = resp.usage_metadata.model_dump(exclude_none=True, mode="json") if resp.usage_metadata else {}
        out["usage"] = um
        out["text"] = resp.text
        # the un-cached prompt tokens at the input rate, cached at an assumed 10 % of it (the price page's usual
        # cached-token rate; not verified for this model, so shown as an assumption), output and thinking at the output rate
        uncached = (um.get("prompt_token_count") or 0) - (um.get("cached_content_token_count") or 0)
        gen = (um.get("candidates_token_count") or 0) + (um.get("thoughts_token_count") or 0)
        out["call_dollars"] = {"uncached_prompt": round(uncached * pin / 1e6, 4), "cached_prompt_at_10pct": round((um.get("cached_content_token_count") or 0) * pin * 0.1 / 1e6, 4),
                               "output_and_thinking": round(gen * pout / 1e6, 4)}
        out["call_dollars"]["total"] = round(sum(out["call_dollars"].values()), 4)
        out["worked"] = True
        ledger.add("gemini", "cache-try", "generate_content(cached)", out["call_dollars"]["total"], out["call_seconds"], True)
    except Exception as e:
        out["worked"] = False
        out["error"] = f"{type(e).__name__}: {str(e)[:800]}"
        ledger.add("gemini", "cache-try", "failed", None, 0.0, False, out["error"][:200])
    finally:
        if cache is not None:
            try:
                client.caches.delete(name=cache.name)
                out["deleted"] = True
            except Exception as e:
                out["deleted"] = f"{type(e).__name__}: {e}"
    (OUT / "cache-try.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({k: v for k, v in out.items() if k not in ("text", "cache")}, indent=1, default=str))
    print(out.get("text", "")[:1500])


if __name__ == "__main__":
    main()
