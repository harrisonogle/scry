"""Arm G1: Gemini answers each of the 27 questions directly from the video, one interactions.create per question, the
uploaded file handle reused, at most 4 calls at a time. Writes runs/compare-gemini/g1/answers.jsonl (scry Answer records,
file order) and raw/<qid>.json per call. Resumable: a question already answered without error is not asked again."""
from __future__ import annotations

import json
import sys
import threading

from compare.gemini.common import (ANSWER_INSTRUCTION, GEMINI_CONCURRENCY, GEMINI_MODEL, OUT, Ledger, answer_record,
                                   gemini_call_with_retry, gemini_client, gemini_request, questions, read_jsonl, run_threads,
                                   setup, uploaded_video, video_path)
from scry.evaluation.questions import Answer

ARM = OUT / "g1"
PROMPT_VERSION = "g1-v1"


def prompt_for(question: str) -> str:
    return f"{ANSWER_INSTRUCTION}\n\nQuestion: {question}"


def main() -> None:
    setup()
    client = gemini_client()
    uri, mime, _ = uploaded_video(client, video_path())
    qs = [q for q in questions() if not sys.argv[1:] or q.id in sys.argv[1:]]  # optional: only these ids
    done = {a["key"]: Answer(**a) for a in read_jsonl(ARM / "answers.jsonl") if not a.get("error")}
    ledger = Ledger()
    lock = threading.Lock()
    (ARM / "raw").mkdir(parents=True, exist_ok=True)

    def write() -> None:
        from compare.gemini.common import write_jsonl
        write_jsonl(ARM / "answers.jsonl", [done[q.key] for q in qs if q.key in done])

    def one(q):
        if q.key in done:
            return
        res, failures = gemini_call_with_retry(client, gemini_request(uri, mime, prompt_for(q.question)), f"G1 {q.id}")
        ledger.add("gemini", "g1", q.id, res["dollars"] if res else None, res["seconds"] if res else 0.0, res is not None,
                   "; ".join(failures))
        (ARM / "raw" / f"{q.id}.json").write_text(json.dumps({"qid": q.id, "prompt": prompt_for(q.question), "result": res,
                                                              "failures": failures}, indent=1, default=str))
        a = answer_record(q, res, failures, GEMINI_MODEL, {"prompt": PROMPT_VERSION})
        with lock:
            done[q.key] = a
            write()
        print(f"{q.id}: {'ok' if res else 'FAILED'} {a.seconds}s ${a.dollars:.4f} {len(a.answer)} chars")

    run_threads(qs, one, GEMINI_CONCURRENCY)
    write()
    failed = [q.id for q in qs if q.key in done and done[q.key].error]
    print(f"G1 done: {len(qs) - len(failed)} answered, {len(failed)} failed {failed}; spend {ledger.total()}")


if __name__ == "__main__":
    main()
