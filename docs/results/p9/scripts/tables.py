"""Scores, tool use and cost of P9 beside P4 and P8. Free: reads files only."""
import collections, statistics
from p9lib import *
D = {(s, r): {"a": answers(s, r), "j": judgments(s, r)} for s in SETS for r in RUNS}
cols = [(s, r) for r in RUNS for s in ("P4", "P9", "P8")]
def head(extra=()): 
    print("| " + " | ".join(list(extra) + [f"{s} {r}" for s, r in cols]) + " |"); print("|" + "---|" * (len(extra) + len(cols)))
print("## labels (c correct, p partial, w wrong, - none)"); head(["Q"])
for q in QIDS:
    print(f"| {q} | " + " | ".join((D[k]["j"].get(q, {}).get("label") or "-")[0] for k in cols) + " |")
print("\n## score per run")
print("| set | run | positive | negative | all | labels | judge errors | answer errors | stops | models |"); print("|" + "---|" * 10)
for s in ("P4", "P9", "P8"):
    for r in RUNS:
        js, an = D[(s, r)]["j"], D[(s, r)]["a"]
        pos = [SCORE[js[q]["label"]] for q in QIDS[:22] if q in js and js[q].get("label") in SCORE]
        neg = [SCORE[js[q]["label"]] for q in QIDS[22:] if q in js and js[q].get("label") in SCORE]
        print(f"| {s} | {r} | {sum(pos):g}/{len(pos)} | {sum(neg):g}/{len(neg)} | {sum(pos)+sum(neg):g}/{len(pos)+len(neg)} | {dict(collections.Counter(x.get('label') for x in js.values()))} | {sum(1 for x in js.values() if x.get('error'))} | {sum(1 for a in an.values() if a.get('error'))} | {dict(collections.Counter(a.get('stop') for a in an.values()))} | {dict(collections.Counter(a.get('model') for a in an.values()))} |")
print("\n## rubric lines passed (M true, X false) per run")
for s in ("P4", "P9", "P8"):
    for r in RUNS:
        ok = n = 0
        for q, j in D[(s, r)]["j"].items():
            for k, v in (j.get("items") or {}).items():
                n += 1; ok += (v is True) if k.startswith("M") else (v is False)
        print(f"  {s} {r}: {ok}/{n}")
print("\n## score and $ per question by type and base (mean of two repeats; a question can be in two types)")
print("| type | n | " + " | ".join(f"{s} {b}" for b in ("ann", "none") for s in ("P4", "P9", "P8")) + " |"); print("|" + "---|" * 8)
for t, qs in LISTS.items():
    row = []
    for b in ("ann", "none"):
        for s in ("P4", "P9", "P8"):
            sc, dl = [], []
            for r in (f"{b}-r1", f"{b}-r2"):
                js, an = D[(s, r)]["j"], D[(s, r)]["a"]
                sc += [SCORE[js[q]["label"]] for q in qs if q in js and js[q].get("label") in SCORE]
                dl += [an[q]["dollars"] for q in qs if q in an]
            row.append(f"{sum(sc):g}/{len(sc)} ${statistics.mean(dl):.3f}" if dl else "-")
    print(f"| {t} | {len(qs)} | " + " | ".join(row) + " |")
print("\n## tool use and cost per run")
print("| set | run | answers | answers that opened a frame | distinct frames / answer | get_frame | redecode | search | get_node | get_transitions | calls / answer | turns / answer | zero-result searches | in tok / q | out tok / q | $ / q | $ run | s / q |")
print("|" + "---|" * 18)
for s in ("P4", "P9", "P8"):
    for r in RUNS:
        an = list(D[(s, r)]["a"].values()); n = len(an)
        if not n: continue
        cnt = collections.Counter(c["name"] for a in an for c in a["calls"])
        opened = sum(1 for a in an if any(c["name"] in ("get_frame", "redecode") and c.get("results") for c in a["calls"]))
        nfr = sum(len({c["input"].get("frame") for c in a["calls"] if c["name"] == "get_frame" and c.get("results")}) for a in an)
        zs = sum(1 for a in an for c in a["calls"] if c["name"] == "search" and not c.get("results"))
        print(f"| {s} | {r} | {n} | {opened} | {nfr/n:.2f} | {cnt['get_frame']} | {cnt['redecode']} | {cnt['search']} | {cnt['get_node']} | {cnt['get_transitions']} | {sum(len(a['calls']) for a in an)/n:.2f} | {sum(a['turns'] for a in an)/n:.2f} | {zs}/{cnt['search']} | {sum(map(intok, an))/n:.0f} | {sum(map(outtok, an))/n:.0f} | {sum(a['dollars'] for a in an)/n:.4f} | {sum(a['dollars'] for a in an):.2f} | {sum(a['seconds'] for a in an)/n:.1f} |")
print("\n## by base (mean of the two repeats)")
print("| base | set | $ / q | in tok / q | out tok / q | s / q | turns | calls | frames opened / answer | answers with a frame (of 54) | zero-result searches |"); print("|" + "---|" * 11)
for b in ("ann", "none"):
    for s in ("P4", "P9", "P8"):
        an = [a for r in (f"{b}-r1", f"{b}-r2") for a in D[(s, r)]["a"].values()]; n = len(an)
        if not n: continue
        opened = sum(1 for a in an if any(c["name"] in ("get_frame", "redecode") and c.get("results") for c in a["calls"]))
        nfr = sum(len({c["input"].get("frame") for c in a["calls"] if c["name"] == "get_frame" and c.get("results")}) for a in an)
        ns = sum(1 for a in an for c in a["calls"] if c["name"] == "search"); zs = sum(1 for a in an for c in a["calls"] if c["name"] == "search" and not c.get("results"))
        print(f"| {b} | {s} | {sum(a['dollars'] for a in an)/n:.4f} | {sum(map(intok, an))/n:.0f} | {sum(map(outtok, an))/n:.0f} | {sum(a['seconds'] for a in an)/n:.1f} | {sum(a['turns'] for a in an)/n:.2f} | {sum(len(a['calls']) for a in an)/n:.2f} | {nfr/n:.2f} | {opened} | {zs}/{ns} |")
print("\n## frames opened per question: P4 | P9 | P8, each as ann-r1 ann-r2 none-r1 none-r2 (frame numbers)")
for q in QIDS:
    cells = []
    for s in ("P4", "P9", "P8"):
        cells.append(" ; ".join(",".join(str(c["input"].get("frame")) for c in D[(s, r)]["a"].get(q, {"calls": []})["calls"] if c["name"] == "get_frame") or "." for r in RUNS))
    print(f"  {q}: " + "  |  ".join(cells))
print("\n## per question: turns / calls / $ , P4 | P9 | P8 (mean of four runs)")
for q in QIDS:
    cells = []
    for s in ("P4", "P9", "P8"):
        an = [D[(s, r)]["a"][q] for r in RUNS if q in D[(s, r)]["a"]]
        cells.append(f"{statistics.mean(a['turns'] for a in an):.1f}/{statistics.mean(len(a['calls']) for a in an):.1f}/${statistics.mean(a['dollars'] for a in an):.3f}" if an else "-")
    print(f"  {q}: " + " | ".join(cells))
print("\n## repricing check: every P9 answer's dollars against Sonnet's and Opus's prices")
import sys; sys.path.insert(0, str(REPO / "src"))
from scry.costs import estimate_cost
for r in RUNS:
    an = D[("P9", r)]["a"].values()
    bad = [a["qid"] for a in an if abs(estimate_cost(a["usage"], "claude-sonnet-5") - a["dollars"]) > 1e-9]
    print(f"  P9 {r}: {len(list(an))} answers; models {dict(collections.Counter(a.get('model') for a in an))}; dollars differing from Sonnet's price: {bad}; "
          f"sum ${sum(a['dollars'] for a in an):.4f}; the same usage at Opus's price ${sum(estimate_cost(a['usage'], 'claude-opus-5') for a in an):.4f}")
