"""Arm G2: Gemini perceives, Opus answers. `transcript`: one Gemini call for a complete timestamped transcript of the
video (runs/compare-gemini/g2/transcript.json). `answer`: for each of the 27 questions one claude-opus-5 call, effort
high, plain text, with the transcript as system context marked for prompt caching and the question as the user turn
(runs/compare-gemini/g2/answers.jsonl, scry Answer records, file order; raw/<qid>.json per call). At most 8 Anthropic
calls at a time. Resumable like G1."""
from __future__ import annotations

import asyncio
import json
import sys
import time

from compare.gemini.common import (ANSWER_INSTRUCTION, ANTHROPIC_CONCURRENCY, GEMINI_MODEL, OPUS_MODEL, OUT, Ledger,
                                   gemini_call_with_retry, gemini_client, gemini_request, questions, read_jsonl, setup,
                                   uploaded_video, video_path, write_jsonl)
from scry.costs import estimate_cost
from scry.evaluation.questions import Answer

ARM = OUT / "g2"
PROMPT_VERSION = "g2-v1"
TRANSCRIPT_PROMPT = """Produce a complete timestamped transcript of everything shown on screen in this screen-recording tutorial, from beginning to end. The video has no audio. Give a time (mm:ss) for every entry. Include: every command typed in a terminal, with its exact text character for character as displayed, and what happens after it is run (its output, a new prompt, an error); every form field with its label and value, and every value that changes, with the value before and after; window, page, tab and dialog titles; every slide's text; every button clicked; every error or notification. Distinguish text the user typed from text the shell or the page merely suggested or auto-completed, when that can be seen. Quote on-screen text exactly as displayed. Be as long as needed; do not summarise or skip."""
SYSTEM_PREFIX = """You answer questions about a screen-recording tutorial. You have not seen the video. Everything you know about it is the transcript below, which was written by a vision model from the video; it is timestamped (mm:ss). Answer only from the transcript. If the transcript does not show something, say so instead of guessing.

TRANSCRIPT:
"""


def transcript() -> None:
    client = gemini_client()
    uri, mime, _ = uploaded_video(client, video_path())
    res, failures = gemini_call_with_retry(client, gemini_request(uri, mime, TRANSCRIPT_PROMPT), "G2 transcript")
    Ledger().add("gemini", "g2", "transcript", res["dollars"] if res else None, res["seconds"] if res else 0.0, res is not None,
                 "; ".join(failures))
    ARM.mkdir(parents=True, exist_ok=True)
    (ARM / "transcript.json").write_text(json.dumps({"model": GEMINI_MODEL, "prompt": TRANSCRIPT_PROMPT, "result": res,
                                                     "failures": failures}, indent=1, default=str))
    if res:
        (ARM / "transcript.md").write_text(res["text"])
    print("G2 transcript:", "ok" if res else "FAILED", res and res["seconds"], res and res["dollars"], res and len(res["text"]), "chars")


async def _opus_call(client, sem, system: list, question: str) -> dict:
    async with sem:
        t0 = time.perf_counter()  # the call alone; the run of 2026-09-21 timed from before the semaphore, so its seconds include queueing
        resp = await client.messages.create(model=OPUS_MODEL, max_tokens=16000, system=system,
                                            messages=[{"role": "user", "content": [{"type": "text", "text": f"{ANSWER_INSTRUCTION}\n\nQuestion: {question}"}]}],
                                            output_config={"effort": "high"})
    u = resp.usage
    usage = {"input_tokens": getattr(u, "input_tokens", 0), "output_tokens": getattr(u, "output_tokens", 0),
             "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
             "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0}
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    return {"text": text, "usage": usage, "dollars": estimate_cost(usage, OPUS_MODEL), "seconds": round(time.perf_counter() - t0, 1),
            "stop": resp.stop_reason, "id": resp.id}


async def answer() -> None:
    import anthropic

    tr = json.loads((ARM / "transcript.json").read_text())
    if not tr.get("result"):
        raise SystemExit("no transcript: run `transcript` first")
    system = [{"type": "text", "text": SYSTEM_PREFIX + tr["result"]["text"], "cache_control": {"type": "ephemeral"}}]
    qs = [q for q in questions() if not sys.argv[2:] or q.id in sys.argv[2:]]
    done = {a["key"]: Answer(**a) for a in read_jsonl(ARM / "answers.jsonl") if not a.get("error")}
    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(ANTHROPIC_CONCURRENCY)
    ledger = Ledger()
    (ARM / "raw").mkdir(parents=True, exist_ok=True)

    async def one(q):
        if q.key in done:
            return
        res, failures = None, []
        for attempt in (1, 2):
            try:
                res = await _opus_call(client, sem, system, q.question)
                break
            except Exception as e:
                failures.append(f"G2 {q.id} attempt {attempt}: {type(e).__name__}: {str(e)[:400]}")
        ledger.add("anthropic", "g2", q.id, res["dollars"] if res else None, res["seconds"] if res else 0.0, res is not None,
                   "; ".join(failures))
        (ARM / "raw" / f"{q.id}.json").write_text(json.dumps({"qid": q.id, "result": res, "failures": failures}, indent=1, default=str))
        base = dict(qid=q.id, key=q.key, polarity=q.polarity, question=q.question, model=OPUS_MODEL, prompt=PROMPT_VERSION)
        if res is None:
            done[q.key] = Answer(**base, answer="", error="; ".join(failures)[:500])
        else:
            done[q.key] = Answer(**base, answer=res["text"], usage=res["usage"], dollars=res["dollars"], seconds=res["seconds"],
                                 stop=res["stop"], turns=1, calls=[{"id": res["id"], "retries": failures}])
        write_jsonl(ARM / "answers.jsonl", [done[x.key] for x in qs if x.key in done])
        a = done[q.key]
        print(f"{q.id}: {'ok' if res else 'FAILED'} {a.seconds}s ${a.dollars:.4f} {len(a.answer)} chars "
              f"cache_read={a.usage.get('cache_read_input_tokens')} cache_write={a.usage.get('cache_creation_input_tokens')}")

    # the first call alone, so its cache write is read by the other 26 (a cache write is 1.25x the input price)
    if qs and qs[0].key not in done:
        await one(qs[0])
    await asyncio.gather(*(one(q) for q in qs[1:]))
    write_jsonl(ARM / "answers.jsonl", [done[x.key] for x in qs if x.key in done])
    failed = [q.id for q in qs if q.key in done and done[q.key].error]
    print(f"G2 answers done: {len(qs) - len(failed)} answered, {len(failed)} failed {failed}; spend {ledger.total()}")


def main() -> None:
    setup()
    cmd = sys.argv[1] if sys.argv[1:] else ""
    if cmd == "transcript":
        transcript()
    elif cmd == "answer":
        asyncio.run(answer())
    else:
        raise SystemExit("usage: python -m compare.gemini.g2 transcript | answer [Qn ...]")


if __name__ == "__main__":
    main()
