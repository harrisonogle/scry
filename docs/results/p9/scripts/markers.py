"""Contract markers in the answers, counted mechanically per set (each hit is then read by eye): who names the suggestion, who cites `submitted`,
who says how many readers or sightings a text has, who leans on the scrollback. usage: markers.py [-v]"""
import re, sys
from p9lib import *
V = "-v" in sys.argv
SUGG = re.compile(r"suggest|predict|autosuggest|greyed|grayed|\bgrey\b|\bgray\b|dimmed|\bdim\b|ghost", re.I)
SUBM = re.compile(r"submitted|pressed enter|enter (was |being )?pressed|press(ing|ed)? enter|enter pressed", re.I)
READ = re.compile(r"readers? (dis)?agree|both readers|one reader|single reader|only one reader|ocr (only|read|reads|reading|rendered|renders|sometimes|occasionally|misread)|vision (reader|model)|vlm|seen once|single (captured )?frame|one sighting|1 sighting|sightings|unstable|other ocr reading", re.I)
SCROLL = re.compile(r"[^.\n]*(scrollback|still (visible|on screen|show)|persist|remain(s|ed)? (visible|on screen|in the))[^.\n]*(confirm|corroborat|reflect|evidence|proves?|shows? (it|they) (ran|was run))[^.\n]*|[^.\n]*(confirm|corroborat|reflected)[^.\n]*(scrollback|still (visible|show)|persist)[^.\n]*", re.I)
RETYPE = re.compile(r"[^.\n]*(re-?typ|typed (it|`?kubectl get pods`?) again|third time it was typed|third attempt was typed)[^.\n]*", re.I)
CMDQ = ["Q16", "Q17", "Q18", "Q19"]
def count(pat, qs, s):
    out = {}
    for q in qs:
        out[q] = sum(1 for r in RUNS if pat.search(answers(s, r)[q]["answer"]))
    return out
for s in ("P4", "P9", "P8"):
    print(f"\n== {s}: {LABEL[s]}")
    print("  names a suggestion (answers of 4):", count(SUGG, CMDQ, s))
    print("  cites submission evidence (answers of 4):", count(SUBM, CMDQ + ["Q21", "Q22", "Q24", "Q27"], s))
    tot = sum(1 for r in RUNS for q in QIDS if READ.search(answers(s, r)[q]["answer"]))
    print("  answers (of 108) that say something about readers, sightings or stability:", tot, "| by run:", {r: sum(1 for q in QIDS if READ.search(answers(s, r)[q]["answer"])) for r in RUNS})
    for name, pat in (("SCROLLBACK AS EVIDENCE", SCROLL), ("RETYPED", RETYPE)):
        for r in RUNS:
            for q in QIDS:
                for m in pat.finditer(answers(s, r)[q]["answer"]):
                    if name == "RETYPED" and q not in ("Q16", "Q17", "Q18", "Q19"): continue
                    print(f"  {name}: {s} {r} {q}: {m.group(0).strip()[:420]}")
