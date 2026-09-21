"""P9 analysis library. Free: reads run directories only; no model calls."""
import json, re
from pathlib import Path
REPO = Path("/Users/harrisonogle/src/harrisonogle/agentic-escort")
S = Path(__file__).parent
# set -> short run name -> run dir (relative to the repo). O/O: Opus agent, Opus index (P4). S/O: Sonnet agent, Opus index (P9).
# S/S: Sonnet agent, Sonnet index (P8).
SETS = {
 "P4": {"ann-r1": "runs/eval/p4/full-inc-transcribing-r1", "ann-r2": "runs/eval/p4/full-inc-transcribing-r2",
        "none-r1": "runs/eval/p4/full-none-r1", "none-r2": "runs/eval/p4/full-none-r2"},
 "P9": {"ann-r1": "runs/eval/p9/full-inc-transcribing-asksonnet-r1", "ann-r2": "runs/eval/p9/full-inc-transcribing-asksonnet-r2",
        "none-r1": "runs/eval/p9/full-none-asksonnet-r1", "none-r2": "runs/eval/p9/full-none-asksonnet-r2"},
 "P8": {"ann-r1": "runs/eval/p8/full-inc-transcribing-sonnet5-r1", "ann-r2": "runs/eval/p8/full-inc-transcribing-sonnet5-r2",
        "none-r1": "runs/eval/p8/full-none-sonnet5-r1", "none-r2": "runs/eval/p8/full-none-sonnet5-r2"},
}
LABEL = {"P4": "Opus agent, Opus index (P4)", "P9": "Sonnet agent, Opus index (P9)", "P8": "Sonnet agent, Sonnet index (P8)"}
RUNS = ["ann-r1", "ann-r2", "none-r1", "none-r2"]
# replay roots: record-only copies (no images) of the index the answers were given over. P4 and P9 share bytes.
REPLAY = {"P9": {r: S / "replay" / Path(SETS["P9"][r]).name for r in RUNS}}
REPLAY["P4"] = REPLAY["P9"]
REPLAY["P8"] = {r: S / "replay-p8" / Path(SETS["P8"][r]).name for r in RUNS}
LISTS = {"exact": [4,10,11,12,14,15,16,19], "when": [3,13], "paraphrase": [1,7,9,12], "changed": [5,6,7,8,10,14,17,18,19,20],
         "order": [21,22], "negative": [23,24,25,26,27], "diagram (Q2)": [2]}
LISTS = {t: [f"Q{n}" for n in v] for t, v in LISTS.items()}
SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
QIDS = [f"Q{n}" for n in range(1, 28)]
def jl(p):
    p = Path(p)
    return [json.loads(l) for l in p.open()] if p.exists() else []
def answers(s, r): return {a["qid"]: a for a in jl(REPO / SETS[s][r] / "answers.jsonl")}
def judgments(s, r): return {j["qid"]: j for j in jl(REPO / SETS[s][r] / "judgments.jsonl")}
def intok(a): return sum(a["usage"].get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
def outtok(a): return a["usage"].get("output_tokens", 0) or 0
