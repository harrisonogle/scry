"""The hold-out comparison: G1 (Gemini direct, the silent copy of the hold-out video, one call per question) against
the pipeline's own `ask` over runs/v2/grouponly-100 (scry.ask.ask through the harness's adapter, Opus 5, the owner's
config), both judged by the same blind judge. Outputs under runs/compare-gemini-v2/. Subcommands:
  questions <draft.md>   copy the question draft in and record its hash
  g1                     Gemini answers (4 at a time)
  import                 the pipeline's answers already asked on runs/v2/grouponly-100 (runs/v2/ask/q*.json) as arm pipe-grouponly-100
  pipe <run> [Qn ...]    the pipeline's answers over a run (8 at a time; `ask` writes redecoded frames under the run's
                         redecode/): grouponly-100 (runs/v2/, the owner's config) or a runs/eval/v2/<run> (its config.json)
  judge [arm ...]        judge the arms (default: every arm directory under the output)
  analyze                the report's tables (no model calls)
Every call is appended to spend.jsonl; g1 and pipe stop asking when the ledger passes the cap."""
from __future__ import annotations

import hashlib
import json
import shutil
import statistics
import sys
import threading
from pathlib import Path

from compare.gemini import analyze
from compare.gemini.common import (ANSWER_INSTRUCTION, ANTHROPIC_CONCURRENCY, GEMINI_CONCURRENCY, GEMINI_MODEL, MAIN, REPO,
                                   Ledger, answer_record, gemini_call_with_retry, gemini_client, gemini_request, questions,
                                   read_jsonl, run_threads, setup, uploaded_video, write_jsonl)
from compare.gemini.judge import judge_arm
from scry.evaluation.questions import Answer

import os

OUT = REPO / "runs" / "compare-gemini-v2"
# COMPARE_SET=disc: the 16 questions of docs/ground-truth/holdout-discovery.md (questions-disc.md, arms *-disc, ledger
# spend-disc.jsonl, cap $12); unset: the 5 draft questions (questions.md, cap $10)
SET = os.environ.get("COMPARE_SET", "")
SUFFIX = f"-{SET}" if SET else ""
QUESTIONS = OUT / (f"questions-{SET}.md" if SET else "questions.md")
VIDEO = MAIN / "runs" / "videos" / "recording-2026-09-17-silent.mp4"
RUN_DIR = MAIN / "runs" / "v2" / "grouponly-100"
VIEW_DIR = OUT / "view-grouponly-100"  # a symlink view of the run: `ask` writes its redecoded frames here, never into the run
RUN_CONFIG = MAIN / "runs" / "v2" / "scry-v2.toml"
CAP_USD = 12.0 if SET else 10.0


def ledger() -> Ledger:
    return Ledger(OUT / f"spend{SUFFIX}.jsonl")


def view_of_run(root: Path) -> Path:
    """A directory of symlinks to every entry of the run directory except redecode/, so a Run opened on it reads the
    run's files and writes only here."""
    VIEW_DIR.mkdir(parents=True, exist_ok=True)
    for entry in root.iterdir():
        if entry.name == "redecode":
            continue
        link = VIEW_DIR / entry.name
        if not link.is_symlink():
            link.symlink_to(entry)
    return VIEW_DIR


def spent() -> float:
    return sum(v["dollars"] for v in ledger().total().values())


def copy_questions(draft: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(draft, QUESTIONS)
    qs = questions(QUESTIONS)
    rec = {"source": str(draft), "sha256": hashlib.sha256(QUESTIONS.read_bytes()).hexdigest(), "questions": len(qs),
           "positive": sum(q.polarity == "positive" for q in qs), "ids": [q.id for q in qs]}
    (OUT / "questions.json").write_text(json.dumps(rec, indent=1))
    print(rec)


def _resumable(arm: Path, qs: list) -> tuple[dict, threading.Lock]:
    done = {a["key"]: Answer(**a) for a in read_jsonl(arm / "answers.jsonl") if not a.get("error")}
    (arm / "raw").mkdir(parents=True, exist_ok=True)
    return done, threading.Lock()


def g1() -> None:
    client = gemini_client()
    uri, mime, _ = uploaded_video(client, VIDEO, OUT / "upload.json")
    qs = [q for q in questions(QUESTIONS) if not sys.argv[2:] or q.id in sys.argv[2:]]
    arm = OUT / f"g1{SUFFIX}"
    done, lock = _resumable(arm, qs)
    led = ledger()

    def one(q):
        if q.key in done:
            return
        if spent() >= CAP_USD:
            print(f"{q.id}: not asked, the ledger is at ${spent():.2f}")
            return
        prompt = f"{ANSWER_INSTRUCTION}\n\nQuestion: {q.question}"
        res, failures = gemini_call_with_retry(client, gemini_request(uri, mime, prompt), f"G1 {q.id}")
        led.add("gemini", "g1", q.id, res["dollars"] if res else None, res["seconds"] if res else 0.0, res is not None, "; ".join(failures))
        (arm / "raw" / f"{q.id}.json").write_text(json.dumps({"qid": q.id, "prompt": prompt, "result": res, "failures": failures}, indent=1, default=str))
        a = answer_record(q, res, failures, GEMINI_MODEL, {"prompt": "g1-v1"})
        with lock:
            done[q.key] = a
            write_jsonl(arm / "answers.jsonl", [done[x.key] for x in qs if x.key in done])
        print(f"{q.id}: {'ok' if res else 'FAILED'} {a.seconds}s ${a.dollars:.4f} {len(a.answer)} chars")

    run_threads(qs, one, GEMINI_CONCURRENCY)
    print(f"G1 done; spend {led.total()}")


RUNS = {"grouponly-100": (RUN_DIR, RUN_CONFIG)}  # the other runs: runs/eval/v2/<name> with their own config.json


def _run_and_config(name: str):
    from scry.config import Config, load_config
    from scry.run import Run

    if name in RUNS:
        root, cfg_path = RUNS[name]
        root = view_of_run(root)
        cfg = load_config(cfg_path)
    else:
        root = MAIN / "runs" / "eval" / "v2" / name
        if not (root / "config.json").exists():
            raise SystemExit(f"no such run: {root}")
        cfg = Config.model_validate(json.loads((root / "config.json").read_text()))
    cfg.model.concurrency = min(cfg.model.concurrency, ANTHROPIC_CONCURRENCY)
    return Run(root), cfg


def import_existing() -> None:
    """runs/v2/ask/q1..q5.json (AskResult dumps of `scry ask` on grouponly-100, asked 2026-09-21 by the drafting agent,
    seconds in timing.txt) as the arm pipe-grouponly-100, so they are judged blind like the others. The question text
    of each file is checked against the parsed question."""
    src = MAIN / "runs" / "v2" / "ask"
    qs = questions(QUESTIONS)
    texts = dict(l.rstrip("\n").split("|", 1) for l in (src / "questions.txt").read_text().splitlines() if "|" in l)
    secs = {l.split()[0]: float(l.split("seconds=")[1]) for l in (src / "timing.txt").read_text().splitlines() if "seconds=" in l}
    out = []
    for q in qs:
        k = q.id.lower()
        assert texts[k].strip() == q.question, (k, texts[k], q.question)
        r = json.loads((src / f"{k}.json").read_text())
        assert r["stop"] != "api_error", r["text"][:100]
        out.append(Answer(qid=q.id, key=q.key, polarity=q.polarity, question=q.question, answer=r["text"], usage=r["usage"], model=r["model"],
                          dollars=r["cost_usd"], seconds=round(secs[k], 1), turns=r["turns"], tools=r["tool_calls"], calls=r["tool_log"],
                          prompt=r["prompt"], stop=r["stop"]))
    arm = OUT / "pipe-grouponly-100"
    write_jsonl(arm / "answers.jsonl", out)
    (arm / "source.json").write_text(json.dumps({"imported_from": str(src), "files": [f"q{i}.json" for i in range(1, len(qs) + 1)]}, indent=1))
    print(f"imported {len(out)} answers, ${sum(a.dollars for a in out):.4f}, {[a.seconds for a in out]} s")


def pipe() -> None:
    """The pipeline's answers over one run: scry.evaluation.adapters.answer_fn (one `ask` per question, a fresh
    conversation, no call cache), the run's config with [model] concurrency capped at 8, from the worktree root so a
    manifest's relative video path resolves through the runs symlink."""
    from scry.evaluation.adapters import answer_fn

    name = sys.argv[2]
    run, cfg = _run_and_config(name)
    qs = [q for q in questions(QUESTIONS) if not sys.argv[3:] or q.id in sys.argv[3:]]
    arm = OUT / f"pipe-{name}{SUFFIX}"
    done, lock = _resumable(arm, qs)
    led = ledger()

    def one(q):
        import time
        if q.key in done:
            return
        if spent() >= CAP_USD:
            print(f"{q.id}: not asked, the ledger is at ${spent():.2f}")
            return
        t0 = time.perf_counter()
        failures: list[str] = []
        out = None
        for attempt in (1, 2):
            try:
                out = answer_fn(run, cfg, q.question)
                if out.stop == "api_error":
                    failures.append(f"pipe {q.id} attempt {attempt}: {out.text[:300]}")
                    out = None
                    continue
                break
            except Exception as e:
                failures.append(f"pipe {q.id} attempt {attempt}: {type(e).__name__}: {str(e)[:300]}")
        seconds = round(time.perf_counter() - t0, 1)
        led.add("anthropic", f"pipe-{name}{SUFFIX}", q.id, out.dollars if out else None, seconds, out is not None, "; ".join(failures))
        base = dict(qid=q.id, key=q.key, polarity=q.polarity, question=q.question)
        if out is None:
            a = Answer(**base, answer="", error="; ".join(failures)[:500], seconds=seconds)
        else:
            a = Answer(**base, answer=out.text, usage=out.usage, model=out.model, dollars=out.dollars, seconds=seconds, turns=out.turns,
                       tools=out.tools, calls=out.calls, prompt=out.prompt, stop=out.stop)
        (arm / "raw" / f"{q.id}.json").write_text(a.model_dump_json(indent=1))
        with lock:
            done[q.key] = a
            write_jsonl(arm / "answers.jsonl", [done[x.key] for x in qs if x.key in done])
        print(f"{q.id}: {'ok' if out else 'FAILED'} {seconds}s ${a.dollars:.4f} turns {a.turns} tools {a.tools} {len(a.answer)} chars")

    run_threads(qs, one, cfg.model.concurrency)
    print(f"pipe-{name} done; spend {led.total()}")


def arms_present() -> list[str]:
    names = sorted(p.parent.name for p in OUT.glob("*/answers.jsonl"))
    return [n for n in names if (n.endswith(SUFFIX) if SET else not n.endswith("-disc"))]


def judge() -> None:
    qs = questions(QUESTIONS)
    led = ledger()
    for arm in sys.argv[2:] or arms_present():
        judge_arm(OUT, arm, qs, led)


PIPE_LABEL = {"pipe-grouponly-100": "pipeline, group-only 1.0 (owner's default, runs/v2/grouponly-100)",
              "pipe-full-grouponly-067-r1": "pipeline, group-only 0.67 (runs/eval/v2/full-grouponly-067-r1)",
              "pipe-full-transcribing-100-r1": "pipeline, transcribing 1.0 (runs/eval/v2/full-transcribing-100-r1)",
              "pipe-full-none-r1": "pipeline, no annotation (runs/eval/v2/full-none-r1)"}


def _build_cost(arm: str) -> float | None:
    root = RUN_DIR if arm == "pipe-grouponly-100" else MAIN / "runs" / "eval" / "v2" / arm[len("pipe-"):]
    from scry.costs import run_costs

    m = json.loads((root / "manifest.json").read_text())
    return (m.get("costs") or {}).get("total_usd") or run_costs(m)["total_usd"]  # an eval run's manifest has no costs block


def cost_table(arms: dict) -> str:
    up = json.loads((OUT / "upload.json").read_text())
    rows = ["| arm | build per video | $ per question (mean; each) | seconds per question (mean; each) | notes |", "|---|---|---|---|---|"]
    A1, _ = arms["G1"]
    d = [a["dollars"] for a in A1.values()]
    sec = [a["seconds"] for a in A1.values()]
    tok = {k: statistics.mean(a["usage"].get(k, 0) for a in A1.values()) for k in ("prompt", "tool_use", "tool_use_video", "thinking", "output", "cached")}
    rows.append(f"| G1 Gemini direct, silent copy | upload {up['upload_and_processing_s']} s, no charge | ${statistics.mean(d):.3f}; {', '.join(f'{x:.3f}' for x in d)} | {statistics.mean(sec):.0f}; {', '.join(f'{x:.0f}' for x in sec)} | mean per call: prompt {tok['prompt']:.0f} tokens, tool use {tok['tool_use']:.0f} (video {tok['tool_use_video']:.0f}), thinking {tok['thinking']:.0f}, output {tok['output']:.0f}, cached {tok['cached']:.0f} |")
    g1_per = statistics.mean(d)
    be = []
    for arm, (A, J) in arms.items():
        if arm == "G1":
            continue
        d = [a["dollars"] for a in A.values()]
        sec = [a["seconds"] for a in A.values()]
        p_in = statistics.mean(a["usage"]["input_tokens"] + a["usage"]["cache_read_input_tokens"] + a["usage"]["cache_creation_input_tokens"] for a in A.values())
        p_out = statistics.mean(a["usage"]["output_tokens"] for a in A.values())
        turns = statistics.mean(a["turns"] for a in A.values())
        tools = statistics.mean(len(a["tools"]) for a in A.values())
        frames = sum(1 for a in A.values() if any(t in ("get_frame", "redecode") for t in a["tools"]))
        build = _build_cost(arm)
        rows.append(f"| {PIPE_LABEL.get(arm, arm)} | ${build} (annotate, interpret, summarize; the manifest's total) | ${statistics.mean(d):.3f}; {', '.join(f'{x:.3f}' for x in d)} | {statistics.mean(sec):.0f}; {', '.join(f'{x:.0f}' for x in sec)} | mean input {p_in:.0f} tokens, output {p_out:.0f}; {turns:.1f} turns, {tools:.1f} tool calls; {frames} of {len(A)} answers opened a frame or redecoded |")
        per = statistics.mean(d)
        if per < g1_per:
            be.append(f"{PIPE_LABEL.get(arm, arm)}: the pipeline's total is below G1's after {build / (g1_per - per):.0f} questions")
        else:
            be.append(f"{PIPE_LABEL.get(arm, arm)}: never, G1 is cheaper per question (${g1_per:.3f} against ${per:.3f}) and has no build")
    return "\n".join(rows) + "\n\nBreak-even against G1 (questions per video after which build plus per-question cost is below G1's):\n\n" + "\n".join(f"- {b}" for b in be)


def per_question(arms: dict) -> str:
    names = list(arms)
    out = ["| Q | style | " + " | ".join(f"{n} label" for n in names) + " | " + " | ".join(f"{n} $" for n in names) + " | " + " | ".join(f"{n} s" for n in names) + " |",
           "|---|---|" + "---|" * (3 * len(names))]
    for qid in analyze.QIDS:
        row = [qid, analyze.QS[qid].style]
        row += [analyze.SHORT[J.get(qid, {}).get("label")] for A, J in arms.values()]
        row += [f"{A[qid]['dollars']:.3f}" if qid in A else "" for A, J in arms.values()]
        row += [f"{A[qid]['seconds']:.0f}" if qid in A else "" for A, J in arms.values()]
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def pipeline_readings(arms: dict) -> str:
    """What each pipeline answer wrote for each exact string (the judge's quote for the line)."""
    out = []
    for qid in analyze.QIDS:
        for it in analyze.QS[qid].rubric:
            m = analyze.EXACT.search(it.text)
            if m:
                for arm, (A, J) in arms.items():
                    out.append(f"- {arm} {qid} {it.id} `{m[1]}`: {(J.get(qid, {}).get('quotes') or {}).get(it.id, '')}")
    return "\n".join(out)


def do_analyze() -> None:
    analyze.configure(QUESTIONS, {})
    arms = {}
    for arm in [f"g1{SUFFIX}"] + [a for a in arms_present() if a.startswith("pipe-")]:
        arms["G1" if arm == f"g1{SUFFIX}" else arm] = ({a["qid"]: a for a in read_jsonl(OUT / arm / "answers.jsonl")},
                                             {j["qid"]: j for j in read_jsonl(OUT / arm / "judgments.jsonl")})
    sections = {"scores": analyze.scores_table, "verdicts": analyze.verdict_table, "failed": analyze.failed_lines, "exact": analyze.exact_check,
                "pipeline_readings": pipeline_readings, "cost": cost_table, "perq": per_question, "citations": analyze.citations}
    for name in sys.argv[2:] or sections:
        print(f"\n## {name}\n\n{sections[name](arms)}")


def main() -> None:
    setup()
    cmd = sys.argv[1] if sys.argv[1:] else ""
    if cmd == "questions":
        copy_questions(Path(sys.argv[2]))
    elif cmd in ("g1", "pipe", "judge", "import"):
        {"g1": g1, "pipe": pipe, "judge": judge, "import": import_existing}[cmd]()
    elif cmd == "analyze":
        do_analyze()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
