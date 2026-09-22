"""Analysis of the comparison, no model calls: reads runs/compare-gemini/{g1,g2}/{answers,judgments}.jsonl and the
pipeline phases' judgments (P4, P6, P9 under runs/eval/), and prints markdown tables for the report: scores by arm and
by question type, the 27-row verdict table, every failed rubric line with the judge's quote, the mechanical
exact-string check (P6's method: the string is or is not in the answer, character for character) with the closest
thing Gemini wrote, cost and time per question with the break-even against the pipeline, and what each answer cites."""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

from rapidfuzz import fuzz

from compare.gemini.common import LIST_PRICES, MAIN, OUT, questions, read_jsonl

PHASES = {  # the pipeline runs shown beside G1 and G2 (docs/results/p4, p6, p9)
    "P4": ["runs/eval/p4/full-inc-transcribing-r1", "runs/eval/p4/full-inc-transcribing-r2", "runs/eval/p4/full-none-r1", "runs/eval/p4/full-none-r2"],
    "P6": ["runs/eval/p6/full-inc-transcribing-indexonly-r1", "runs/eval/p6/full-inc-transcribing-indexonly-r2",
           "runs/eval/p6/full-inc-transcribing-batch-indexonly-r1", "runs/eval/p6/full-none-indexonly-r1", "runs/eval/p6/full-none-indexonly-r2"],
    "P9": ["runs/eval/p9/full-inc-transcribing-asksonnet-r1", "runs/eval/p9/full-inc-transcribing-asksonnet-r2",
           "runs/eval/p9/full-none-asksonnet-r1", "runs/eval/p9/full-none-asksonnet-r2"],
}
TYPES = {"exact string": [4, 10, 11, 12, 14, 15, 16, 19], "when": [3, 13], "worded without the on-screen words": [1, 7, 9, 12],
         "value in several states or places": [5, 6, 7, 8, 10, 14, 17, 18, 19, 20], "order across the video": [21, 22],
         "diagram (Q2)": [2], "negative": [23, 24, 25, 26, 27]}
TYPES = {t: [f"Q{n}" for n in v] for t, v in TYPES.items()}
EXACT = re.compile(r"contains the exact string `([^`]+)`")
SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}
SHORT = {"correct": "c", "partial": "p", "wrong": "w", None: "-"}
# the pipeline's per-question cost and build cost, from docs/results/p4 and p6 (annotated, sync-built base)
PIPE_PER_Q, PIPE_BUILD_ANN, PIPE_BUILD_UNANN, PIPE_SECONDS = 0.263, 17.85, 4.62, 22.0

QS = {q.id: q for q in questions()}
QIDS = list(QS)


def arm(name: str) -> tuple[dict, dict]:
    return ({a["qid"]: a for a in read_jsonl(OUT / name / "answers.jsonl")},
            {j["qid"]: j for j in read_jsonl(OUT / name / "judgments.jsonl")})


def phase_judgments(phase: str) -> list[dict]:
    return [{j["qid"]: j for j in read_jsonl(MAIN / r / "judgments.jsonl")} for r in PHASES[phase]]


def lines_passed(J: dict, qids=QIDS) -> tuple[int, int]:
    ok = n = 0
    for qid in qids:
        j = J.get(qid)
        if not j:
            continue
        for it in QS[qid].rubric:
            n += 1
            v = (j.get("items") or {}).get(it.id)
            ok += 1 if v is not None and (v if it.id.startswith("M") else not v) else 0
    return ok, n


def score(J: dict, qids) -> str:
    labels = [J[q]["label"] for q in qids if q in J]
    s = sum(SCORE.get(l, 0.0) for l in labels)
    return f"{s:g}/{len(qids)}"


def scores_table(arms: dict) -> str:
    pos = [q for q in QIDS if QS[q].polarity == "positive"]
    neg = [q for q in QIDS if QS[q].polarity == "negative"]
    out = ["| arm | positive (of 22) | negative (of 5) | correct / partial / wrong | rubric lines passed |", "|---|---|---|---|---|"]
    for name, (A, J) in arms.items():
        counts = {k: sum(1 for j in J.values() if j["label"] == k) for k in ("correct", "partial", "wrong")}
        ok, n = lines_passed(J)
        out.append(f"| {name} | {score(J, pos)} | {score(J, neg)} | {counts['correct']} / {counts['partial']} / {counts['wrong']} | {ok}/{n} |")
    for phase in PHASES:
        for r, J in zip(PHASES[phase], phase_judgments(phase)):
            counts = {k: sum(1 for j in J.values() if j["label"] == k) for k in ("correct", "partial", "wrong")}
            ok, n = lines_passed(J)
            out.append(f"| {phase} {Path(r).name} | {score(J, pos)} | {score(J, neg)} | {counts['correct']} / {counts['partial']} / {counts['wrong']} | {ok}/{n} |")
    return "\n".join(out)


def types_table(arms: dict) -> str:
    cols = list(arms) + [f"{p} (mean of {len(PHASES[p])} runs)" for p in PHASES]
    out = ["| question type | n | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    phases = {p: phase_judgments(p) for p in PHASES}
    for t, qids in TYPES.items():
        row = [t, str(len(qids))]
        for name, (A, J) in arms.items():
            row.append(score(J, qids))
        for p in PHASES:
            vals = [sum(SCORE.get(J[q]["label"], 0.0) for q in qids if q in J) for J in phases[p]]
            row.append(f"{statistics.mean(vals):.2g}/{len(qids)}")
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def verdict_table(arms: dict) -> str:
    phases = {p: phase_judgments(p) for p in PHASES}
    out = ["| Q | type | " + " | ".join(f"{a} label" for a in arms) + " | " + " | ".join(f"{a} lines" for a in arms)
           + " | " + " | ".join(f"{p} ({len(PHASES[p])} runs)" for p in PHASES) + " |",
           "|---|---|" + "---|" * (2 * len(arms) + len(PHASES))]
    for qid in QIDS:
        row = [qid, QS[qid].style]
        for name, (A, J) in arms.items():
            row.append(SHORT[J.get(qid, {}).get("label")])
        for name, (A, J) in arms.items():
            items = J.get(qid, {}).get("items") or {}
            row.append(" ".join(f"{it.id}{'+' if items.get(it.id) == it.id.startswith('M') else '-'}" for it in QS[qid].rubric))
        for p in PHASES:
            row.append("".join(SHORT[J.get(qid, {}).get("label")] for J in phases[p]))
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def failed_lines(arms: dict) -> str:
    out = ["| arm | Q | line | statement | judge's quote from the answer |", "|---|---|---|---|---|"]
    for name, (A, J) in arms.items():
        for qid in QIDS:
            j = J.get(qid)
            if not j:
                continue
            for it in QS[qid].rubric:
                v = (j.get("items") or {}).get(it.id)
                if v is None or v != it.id.startswith("M"):
                    quote = (j.get("quotes") or {}).get(it.id, "").replace("|", "\\|").replace("\n", " ")
                    out.append(f"| {name} | {qid} | {it.id} | {it.text.replace('|', chr(92) + '|')} | {quote[:160]} |")
    return "\n".join(out)


def closest(needle: str, hay: str) -> str:
    """The best-matching substring of the answer for an exact string it lacks (rapidfuzz alignment), so the report can
    say which characters differ."""
    al = fuzz.partial_ratio_alignment(needle, hay)
    if al is None or al.score < 50:
        return "(nothing close)"
    return hay[al.dest_start:al.dest_end]


def exact_check(arms: dict) -> str:
    """P6's method: every 'contains the exact string' line checked mechanically, against the judge's verdict."""
    out = ["| arm | Q | line | expected | in answer | judge | closest text in the answer |", "|---|---|---|---|---|---|---|"]
    dis = 0
    for name, (A, J) in arms.items():
        for qid in QIDS:
            for it in QS[qid].rubric:
                m = EXACT.search(it.text)
                if not m or qid not in A:
                    continue
                s = m[1]
                ans = A[qid]["answer"]
                mech = s in ans
                judge = (J.get(qid, {}).get("items") or {}).get(it.id)
                if judge is not None and judge != mech:
                    dis += 1
                if not mech or judge != mech:
                    out.append(f"| {name} | {qid} | {it.id} | `{s}` | {'yes' if mech else 'no'} | {judge} | `{closest(s, ans).replace('`', '')}` |")
    n = sum(1 for qid in QIDS for it in QS[qid].rubric if EXACT.search(it.text))
    return f"{n} exact-string lines per arm; judge and mechanical check disagree on {dis} lines.\n\n" + "\n".join(out)


def pipeline_exact_readings() -> dict[str, str]:
    """What the pipeline (P4 annotated r1) wrote for each exact string: the judge's quote for the line."""
    J = phase_judgments("P4")[0]
    out = {}
    for qid in QIDS:
        for it in QS[qid].rubric:
            m = EXACT.search(it.text)
            if m:
                out[f"{qid} {it.id}"] = (J.get(qid, {}).get("quotes") or {}).get(it.id, "")
    return out


def gemini_cost(tokens: dict) -> float:
    pin, pout = LIST_PRICES["gemini-3.8-flash"]
    return ((tokens.get("prompt", 0) + tokens.get("tool_use", 0)) * pin + (tokens.get("thinking", 0) + tokens.get("output", 0)) * pout) / 1e6


def cost_table(arms: dict) -> str:
    A1, _ = arms["G1"]
    A2, _ = arms["G2"]
    tr = json.loads((OUT / "g2" / "transcript.json").read_text())["result"]
    g1c = json.loads((OUT / "g1c" / "answer.json").read_text())["result"]
    up = json.loads((OUT / "upload.json").read_text())
    g1_d = [a["dollars"] for a in A1.values()]
    g1_s = [a["seconds"] for a in A1.values()]
    g1_tok = {k: statistics.mean(a["usage"].get(k, 0) for a in A1.values()) for k in ("prompt", "tool_use", "tool_use_video", "tool_use_text", "thinking", "output", "cached")}
    g2_d = [a["dollars"] for a in A2.values()]
    g2_s = [a["seconds"] for a in A2.values()]
    g2_in = statistics.mean(a["usage"]["input_tokens"] + a["usage"]["cache_read_input_tokens"] + a["usage"]["cache_creation_input_tokens"] for a in A2.values())
    g2_out = statistics.mean(a["usage"]["output_tokens"] for a in A2.values())
    g2_cache_reads = sum(1 for a in A2.values() if a["usage"]["cache_read_input_tokens"] > 0)
    tr_amort = tr["dollars"] / 27
    lines = [
        "| arm | one-time per video | per question | seconds per question | notes |", "|---|---|---|---|---|",
        f"| G1 Gemini direct | upload {up['upload_and_processing_s']} s, $0 | ${statistics.mean(g1_d):.4f} (min {min(g1_d):.4f}, max {max(g1_d):.4f}); sum over 27 ${sum(g1_d):.3f} | {statistics.mean(g1_s):.1f} (min {min(g1_s):.0f}, max {max(g1_s):.0f}) | mean tokens per call: prompt {g1_tok['prompt']:.0f}, tool use {g1_tok['tool_use']:.0f} (video {g1_tok['tool_use_video']:.0f}, text {g1_tok['tool_use_text']:.0f}), thinking {g1_tok['thinking']:.0f}, output {g1_tok['output']:.0f}, cached {g1_tok['cached']:.0f} |",
        f"| G1c Gemini command list | | ${g1c['dollars']:.4f} for the one call | {g1c['seconds']:.0f} | tool use {g1c['tokens']['tool_use']} tokens |",
        f"| G2 Gemini transcript | ${tr['dollars']:.4f}, {tr['seconds']:.0f} s ({len(tr['text'])} chars, {tr['tokens']['output']} output tokens) | ${tr_amort:.4f} amortised over 27 | {tr['seconds'] / 27:.1f} amortised | tool use {tr['tokens']['tool_use']} tokens (video {tr['tokens'].get('tool_use_video', 0)}) |",
        f"| G2 Opus answers | | ${statistics.mean(g2_d):.4f} (sum ${sum(g2_d):.3f}); with the transcript amortised ${statistics.mean(g2_d) + tr_amort:.4f} | {statistics.mean(g2_s):.1f} (min {min(g2_s):.0f}, max {max(g2_s):.0f}) | mean input {g2_in:.0f} tokens ({g2_cache_reads} of 27 read the cache), output {g2_out:.0f} |",
        f"| pipeline (P4, annotated) | ${PIPE_BUILD_ANN} | ${PIPE_PER_Q} | {PIPE_SECONDS} | docs/results/p4, p6 |",
        f"| pipeline (unannotated) | ${PIPE_BUILD_UNANN} | $0.216 | | docs/results/p6 |",
    ]
    lines += [f"| pipeline, Sonnet agent (P9, annotated) | ${PIPE_BUILD_ANN} | $0.062 | 9.5 | docs/results/p9 |",
              f"| pipeline, Sonnet agent (P9, unannotated) | ${PIPE_BUILD_UNANN} | $0.053 | 9.5 | docs/results/p9 |"]
    g1_per = statistics.mean(g1_d)
    g2_per = statistics.mean(g2_d) + tr_amort
    be = []
    for label, build, per in (("annotated, Opus agent", PIPE_BUILD_ANN, PIPE_PER_Q), ("unannotated, Opus agent", PIPE_BUILD_UNANN, 0.216),
                              ("annotated, Sonnet agent", PIPE_BUILD_ANN, 0.062), ("unannotated, Sonnet agent", PIPE_BUILD_UNANN, 0.053)):
        for arm_name, arm_per in (("G1", g1_per), ("G2", g2_per)):
            if per < arm_per:
                n = build / (arm_per - per)
                be.append(f"{label} pipeline against {arm_name}: the pipeline's total is lower after {n:.0f} questions on this video (build ${build} / (${arm_per:.4f} - ${per} per question))")
            else:
                be.append(f"{label} pipeline against {arm_name}: never; {arm_name} is cheaper per question (${arm_per:.4f} against ${per}) and has no build")
    return "\n".join(lines) + "\n\nBreak-even (the number of questions per video after which the pipeline's build plus per-question cost is below the arm's):\n\n" + "\n".join(f"- {b}" for b in be)


def per_question(arms: dict) -> str:
    A1, J1 = arms["G1"]
    A2, J2 = arms["G2"]
    out = ["| Q | G1 $ | G1 s | G1 video tokens | G1 cached | G1 label | G2 Opus $ | G2 s | G2 output tokens | G2 label |", "|---|---|---|---|---|---|---|---|---|---|"]
    for qid in QIDS:
        a, b = A1[qid], A2[qid]
        out.append(f"| {qid} | {a['dollars']:.4f} | {a['seconds']:.0f} | {a['usage'].get('tool_use_video', 0)} | {a['usage'].get('cached', 0)} | {SHORT[J1[qid]['label']]} "
                   f"| {b['dollars']:.4f} | {b['seconds']:.0f} | {b['usage']['output_tokens']} | {SHORT[J2[qid]['label']]} |")
    return "\n".join(out)


TIME = re.compile(r"(?<![\d:.])(\d{1,2}):(\d{2})(?:\.\d+)?(?![\d:])")


def citations(arms: dict) -> str:
    out = ["| arm | answers | with at least one mm:ss time | times per answer (mean, min) | answers naming a frame number | answers saying the video does not show something |", "|---|---|---|---|---|---|"]
    for name, (A, J) in arms.items():
        counts = [len(TIME.findall(a["answer"])) for a in A.values()]
        frames = sum(1 for a in A.values() if re.search(r"\bframe\s*\d+", a["answer"], re.I))
        notshown = sum(1 for a in A.values() if re.search(r"(does not|doesn't|not) (show|visible|display|appear)|not shown|cannot be seen|no evidence", a["answer"], re.I))
        out.append(f"| {name} | {len(A)} | {sum(1 for c in counts if c)} | {statistics.mean(counts):.1f}, {min(counts)} | {frames} | {notshown} |")
    return "\n".join(out)


def main() -> None:
    arms = {"G1": arm("g1"), "G2": arm("g2")}
    sections = {
        "scores": scores_table, "types": types_table, "verdicts": verdict_table, "failed": failed_lines, "exact": exact_check,
        "pipeline_readings": lambda arms: "\n".join(f"- {k}: {v}" for k, v in pipeline_exact_readings().items()),
        "cost": cost_table, "perq": per_question, "citations": citations,
    }
    for name in sys.argv[1:] or sections:
        print(f"\n## {name}\n\n{sections[name](arms)}")


if __name__ == "__main__":
    main()
