"""Replay the recorded tool calls of answers against record-only scratch copies of the indexes (no model calls; no images).
usage: replay.py <set> [<qid>,<qid>...]   writes replays/<set>/<run>/<qid>.txt. Also importable: seen_text(set, run, answer)."""
import json, sys, logging
logging.disable(logging.WARNING)
from p9lib import *
from scry.ask import Tools, _result_count
from scry.config import Config
from scry.run import Run
_tools = {}
def tools_for(s, r):
    if (s, r) not in _tools:
        root = REPLAY[s][r]
        cfg = Config.model_validate(json.loads((root / "config.json").read_text()))
        _tools[(s, r)] = Tools(Run(root), cfg)
    return _tools[(s, r)]
def run_call(tools, c):
    """(lines of text the agent was given, result count or None). redecode returns only images: not replayed."""
    if c["name"] == "redecode":
        return ["<redecode: images only, not replayed>"], None
    try:
        out = getattr(tools, c["name"])(**c["input"])
    except Exception as e:
        return [f"REPLAY ERROR {type(e).__name__}: {e}"], None
    n = _result_count(c["name"], out)
    if isinstance(out, list):
        return [b.get("text", "<image>") for b in out], n
    return [json.dumps(out, ensure_ascii=False, default=str)[:60000]], n
def pretty(c, tools):
    if c["name"] == "redecode": return ["<redecode: images only, not replayed>"]
    try: out = getattr(tools, c["name"])(**c["input"])
    except Exception as e: return [f"REPLAY ERROR {type(e).__name__}: {e}"]
    if isinstance(out, list): return [b.get("text", "<image>") for b in out]
    if c["name"] == "search":
        lines = []
        for h in out["hits"]:
            extra = {k: v for k, v in h.items() if k not in ("node_id", "level", "item_id", "frames", "t", "score", "text")}
            lines.append(f"- [{h['level']}] {h['node_id']} frames={h['frames']} t={h['t']} score={h['score']:.4f} {json.dumps(extra, ensure_ascii=False) if extra else ''}")
            lines.append("    " + str(h["text"]).replace("\n", "\n    ")[:2500])
        if "note" in out: lines.append("note: " + out["note"])
        return lines
    return [json.dumps(out, indent=1, ensure_ascii=False, default=str)[:60000]]
def main(s, qids):
    mism = n = 0
    for r in RUNS:
        tools = tools_for(s, r)
        out_dir = S / "replays" / s / r; out_dir.mkdir(parents=True, exist_ok=True)
        for qid, a in answers(s, r).items():
            for c in a["calls"]:
                if c["name"] == "redecode": continue
                _, cnt = run_call(tools, c); n += 1
                if cnt != c["results"]: mism += 1; print("MISMATCH", s, r, qid, c, cnt)
            if qids and qid not in qids: continue
            lines = [f"# {s} {r} {qid}: {a['question']}", f"model={a.get('model')} turns={a['turns']} stop={a['stop']} dollars={a['dollars']} seconds={a['seconds']}", ""]
            for i, c in enumerate(a["calls"]):
                lines.append(f"## call {i+1}: {c['name']} {json.dumps(c['input'], ensure_ascii=False)}  (recorded results={c['results']}, error={c.get('error')})")
                lines += pretty(c, tools); lines.append("")
            lines += ["## ANSWER", a["answer"], ""]
            (out_dir / f"{qid}.txt").write_text("\n".join(lines))
    print(s, "calls replayed:", n, "result-count mismatches:", mism)
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2].split(",") if len(sys.argv) > 2 else [])
