"""When an answer quotes a text that its own tool results marked as read differently by the two readers (agree: false), as unstable, or as
seen once, does the answer say so? Mechanical; lifetime search hits and get_frame records only. usage: readings.py [-v]"""
import re, sys, json
from p9lib import *
from replay import tools_for
from triage import squash
V = "-v" in sys.argv
SAYS_DIFF = re.compile(r"readers? (dis)?agree|readers? differ|two readers|both readers|ocr (read|reads|reading|rendered|renders|sometimes|occasionally|misread|captured|gave|shows|text)|read by ocr as|vision (reader|model)|vlm|model reads|unstable|other ocr reading|ocr[- ]derived", re.I)
SAYS_ONCE = re.compile(r"seen once|single (captured )?frame|one sighting|1 sighting|only (in )?(one|a single) frame|on (one|a single) frame|only on frame|one frame only", re.I)
FRAME_LINE = re.compile(r'^(b\d+) (L\d+) "(.*?)" \| seen [\d.]+–[\d.]+s in (\d+) frames(.*)$')
def items(tools, a):
    out = []  # (kind, lifetime id, [readings])
    for c in a["calls"]:
        if c["name"] == "search":
            try: res = tools.search(**c["input"])
            except Exception: continue
            for h in res["hits"]:
                if h["level"] != "lifetime": continue
                rd = [x for x in (h["readers"]["ocr"], h["readers"]["vlm"]) if x]
                if h.get("agree") is False or h.get("unstable"): out.append(("differ", h["item_id"], rd))
                if h.get("seen_once"): out.append(("once", h["item_id"], rd))
        elif c["name"] == "get_frame":
            try: res = tools.get_frame(**c["input"])
            except Exception: continue
            for line in res[0]["text"].split("\n"):
                m = FRAME_LINE.match(line)
                if not m: continue
                rd = [m[3]] + re.findall(r'model reads "(.*?)"', m[5]) + re.findall(r'"(.*?)"', m[5].split("| model reads")[0]) 
                if "model reads" in m[5] or "other OCR readings" in m[5]: out.append(("differ", m[2], rd))
                if m[4] == "1": out.append(("once", m[2], rd))
    return out
for s in ("P4", "P9", "P8"):
    tot = {"differ": [0, 0], "once": [0, 0]}
    per_run = {r: {"differ": [0, 0], "once": [0, 0]} for r in RUNS}
    for r in RUNS:
        tools = tools_for(s, r)
        for q, a in answers(s, r).items():
            sa = squash(a["answer"])
            used = {"differ": set(), "once": set()}
            for kind, lid, rd in items(tools, a):
                if any(len(squash(x)) >= 8 and squash(x) in sa for x in rd): used[kind].add(lid)
            for kind, pat in (("differ", SAYS_DIFF), ("once", SAYS_ONCE)):
                if used[kind]:
                    said = bool(pat.search(a["answer"]))
                    tot[kind][0] += 1; tot[kind][1] += said; per_run[r][kind][0] += 1; per_run[r][kind][1] += said
                    if V and not said: print(f"   {s} {r} {q} quotes a text marked {kind} and does not say so: {sorted(used[kind])[:6]}")
    print(f"{s}: answers that quote a text whose readings differ or vary: {tot['differ'][0]}, of which say so: {tot['differ'][1]} | quote a text seen once: {tot['once'][0]}, of which say so: {tot['once'][1]} | per run {json.dumps(per_run)}")
