"""Arm G1c: one Gemini call for the list of commands executed in the terminal, scored by hand against
docs/ground-truth/span2-commands.md. Writes runs/compare-gemini/g1c/answer.json."""
from __future__ import annotations

import json

from compare.gemini.common import (GEMINI_MODEL, OUT, Ledger, gemini_call_with_retry, gemini_client, gemini_request, setup,
                                   uploaded_video, video_path)

ARM = OUT / "g1c"
PROMPT = """List every command executed in the terminal in this video, in order, exactly as typed, with the time (mm:ss) each was run. Quote each command character for character as displayed. Say nothing about commands that were merely typed or suggested but not run."""


def main() -> None:
    setup()
    client = gemini_client()
    uri, mime, _ = uploaded_video(client, video_path())
    res, failures = gemini_call_with_retry(client, gemini_request(uri, mime, PROMPT), "G1c")
    Ledger().add("gemini", "g1c", "commands", res["dollars"] if res else None, res["seconds"] if res else 0.0, res is not None,
                 "; ".join(failures))
    ARM.mkdir(parents=True, exist_ok=True)
    (ARM / "answer.json").write_text(json.dumps({"model": GEMINI_MODEL, "prompt": PROMPT, "result": res, "failures": failures},
                                                indent=1, default=str))
    print("G1c:", "ok" if res else "FAILED", res and res["seconds"], res and res["dollars"])
    print(res["text"] if res else failures)


if __name__ == "__main__":
    main()
