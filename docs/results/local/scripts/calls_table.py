"""Per-call table of a local run: the provider's log lines (in call order) beside the run's annotations (frame order;
concurrency 1 keeps them aligned). Usage: calls_table.py <log> <run-dir> [stage]"""
import json, re, sys, statistics
log, run = sys.argv[1], sys.argv[2]; stage = sys.argv[3] if len(sys.argv) > 3 else "annotate"
calls = []
for l in open(log):
    m = re.search(rf"openai_compat {stage}: ([\d.]+)s prompt=(\d+) completion=(\d+) (.+)$", l)
    if m: calls.append((float(m[1]), int(m[2]), int(m[3]), m[4].strip()))
if stage == "annotate":
    recs = [json.loads(l) for l in open(f"{run}/annotations.jsonl")]
    print("| frame | targets | wall s | prompt | completion | outcome | texts returned | links kept | repairs |"); print("|---|---|---|---|---|---|---|---|---|")
    for a, c in zip(recs, calls):
        print(f"| {a['frame']} | {len(a['targets'])} | {c[0]:.1f} | {c[1]} | {c[2]} | {c[3]} | {len(a['texts'] or [])} | {len(a['links'])} | {a.get('repairs')} |")
else:
    recs = [json.loads(l) for l in open(f"{run}/interpretations.jsonl")]
    print("| T | wall s | prompt | completion | outcome | entered_text | submitted |"); print("|---|---|---|---|---|---|---|")
    for a, c in zip(recs, calls):
        print(f"| {a['id']} | {c[0]:.1f} | {c[1]} | {c[2]} | {c[3]} | {a.get('entered_text')!r} | {a.get('submitted')} |")
w = [c[0] for c in calls]
if w:
    print(f"\n{len(calls)} calls, wall total {sum(w):.0f}s, mean {statistics.mean(w):.1f}s, median {statistics.median(w):.1f}s, max {max(w):.1f}s; "
          f"prompt mean {statistics.mean(c[1] for c in calls):.0f}, completion mean {statistics.mean(c[2] for c in calls):.0f}; "
          f"valid first time {sum(1 for c in calls if c[3]=='ok')}/{len(calls)}; ok-after-retry lines {sum(1 for c in calls if c[3]!='ok')}")
