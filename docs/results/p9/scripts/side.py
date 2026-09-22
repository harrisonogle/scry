"""Side by side: the answers of the named sets to one question, with their recorded calls. usage: side.py Q18 [P9,P4,P8]"""
import sys, json
from p9lib import *
q = sys.argv[1]; sets = sys.argv[2].split(",") if len(sys.argv) > 2 else ["P9", "P4"]
for s in sets:
    for r in RUNS:
        a = answers(s, r).get(q); j = judgments(s, r).get(q, {})
        if not a: continue
        print(f"\n######## {s} {r} {q}  [{LABEL[s]}]  label={j.get('label')} items={j.get('items')} turns={a['turns']} ${a['dollars']} {a['seconds']}s")
        for c in a["calls"]: print("   call:", c["name"], json.dumps(c["input"], ensure_ascii=False), "->", c.get("results"))
        print(a["answer"])
