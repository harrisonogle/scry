"""Token split per question by base and set; repeat gaps."""
from p9lib import *
print("| base | set | uncached in / q | cache write / q | cache read / q | out / q | $ / q | s / q | $ r1, r2 | total $ (2 runs) |"); print("|" + "---|" * 10)
for b in ("ann", "none"):
    for s in ("P4", "P9", "P8"):
        an = [a for r in (f"{b}-r1", f"{b}-r2") for a in answers(s, r).values()]; n = len(an)
        u = lambda k: sum(a["usage"].get(k, 0) or 0 for a in an) / n
        per = [sum(a["dollars"] for a in answers(s, f"{b}-r{i}").values()) / 27 for i in (1, 2)]
        print(f"| {b} | {s} | {u('input_tokens'):.0f} | {u('cache_creation_input_tokens'):.0f} | {u('cache_read_input_tokens'):.0f} | {u('output_tokens'):.0f} | {sum(a['dollars'] for a in an)/n:.4f} | {sum(a['seconds'] for a in an)/n:.1f} | {per[0]:.4f}, {per[1]:.4f} | {sum(a['dollars'] for a in an):.2f} |")
print("\nwords per answer (mean):")
for s in ("P4", "P9", "P8"):
    print(" ", s, {r: round(sum(len(a["answer"].split()) for a in answers(s, r).values()) / 27) for r in RUNS})
print("\nanswers that opened at least one frame, of 27:")
for s in ("P4", "P9", "P8"):
    print(" ", s, {r: sum(1 for a in answers(s, r).values() if any(c["name"] == "get_frame" and c.get("results") for c in a["calls"])) for r in RUNS})
print("\nquestions where the agent opened a frame in k of 4 runs (P4 / P9 / P8):")
for q in QIDS:
    print(f"  {q}: " + " / ".join(str(sum(1 for r in RUNS if any(c["name"] == "get_frame" and c.get("results") for c in answers(s, r)[q]["calls"]))) for s in ("P4", "P9", "P8")))
