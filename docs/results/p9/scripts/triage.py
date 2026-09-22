"""Mechanical triage of unsupported claims (method of P6's analyst): for every answer, rebuild the TEXT its tool calls returned and flag
(1) quoted strings that are in no tool result and not in the question, (2) sentences with a visual word that is in no tool result,
(3) words of intent or narration. An answer that opened a frame also saw its pixels: a flag there is a lead to check by eye, not a finding.
usage: triage.py <set> [<set> ...]"""
import json, re, sys, collections
from p9lib import *
from replay import tools_for, run_call
VISUAL = ["highlight", "selected", "greyed", "grayed", "grey", "gray", " red ", "red text", "in red", "blue", "yellow", "green", "white", "icon", "arrow",
          "pointer", "cursor", "hover", "bold", "dimmed", "disabled", "checked", "ticked", "radio", "toggle", "overlap", "in front", "behind",
          "on top", "popup", "dropdown", "banner", "tile", "chip", "spinner", "checkmark", "tick", "foreground", "background", "window"]
INTENT = ["demonstrat", "deliberately", "discussed", "explained", "explains", "purely", "on purpose", "intend", "intent", "mistake", "accident", "decides", "decided",
          "wants", "wanted", "in order to", "changed their mind", "changes their mind", "changed his mind", "reconsider", "realiz", "realis", "abandon", "to verify", "to confirm", "to check",
          "mentions", " says ", "talks", "narrat", "walks through", "presumably", "likely", "probably", "appears to", "seems"]
QUOTES = "\"'`*\\"
DASHES = "‐‑–—"
def norm(s): return re.sub(r"\s+", " ", s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")).lower()
def squash(s):
    """for quote matching: no quote marks, backslashes or emphasis; one kind of dash; single spaces"""
    s = norm(s).replace("\\n", " ").replace("\\u2013", "-")
    s = "".join("-" if ch in DASHES else ch for ch in s if ch not in QUOTES)
    return re.sub(r"\s+", " ", s).strip()
SPLIT = re.compile(r"\s*(?:…|\.\.\.| / | \| | — | – | - |\s{2,}|→|->|>)\s*")
def triage(s):
    rows = []; per = collections.Counter()
    for r in RUNS:
        tools = tools_for(s, r)
        for qid, a in answers(s, r).items():
            seen = []
            for c in a["calls"]:
                lines, _ = run_call(tools, c); seen.append("\n".join(lines))
            blob = norm("\n".join(seen)); sblob = squash("\n".join(seen))
            ans = a["answer"]; q = norm(a["question"]); sq = squash(a["question"])
            opened = sorted({c["input"].get("frame") for c in a["calls"] if c["name"] == "get_frame" and c.get("results")})
            clean = ans.replace("“", '"').replace("”", '"').replace("**", "")
            quoted = {x for x in re.findall(r'"([^"\n]*)"', clean) + re.findall(r"`([^`\n]*)`", clean) if 4 <= len(x) <= 300}
            for x in sorted(quoted):
                parts = [squash(p).rstrip(".,;:") for p in SPLIT.split(x)]
                parts = [p for p in parts if len(p) >= 4]
                if all(p in sblob or p in sq for p in parts): continue
                missing = [p for p in parts if not (p in sblob or p in sq)]
                rows.append((r, qid, "QUOTE", x, opened, missing)); per[(r, "QUOTE")] += 1
            for sent in re.split(r"(?<=[.!?])\s+|\n+", ans):
                ls = " " + norm(sent) + " "
                for w in VISUAL:
                    if w in ls and w.strip() not in blob and w.strip() not in q:
                        rows.append((r, qid, "VISUAL:" + w.strip(), sent.strip()[:500], opened, [])); per[(r, "VISUAL")] += 1
                for w in INTENT:
                    if w in ls:
                        rows.append((r, qid, "INTENT:" + w.strip(), sent.strip()[:500], opened, [])); per[(r, "INTENT")] += 1
    (S / f"triage-{s}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(s, "flags:", len(rows), dict(sorted(per.items())))
if __name__ == "__main__":
    for s in sys.argv[1:] or ["P9"]: triage(s)
