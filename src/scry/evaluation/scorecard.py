"""One run → its scorecard: every number the report shows for the run, the per-unit values that pair it with another
run, and what weakens its evidence. Scoring calls no model and costs nothing, so a scorecard is rebuilt freely."""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Literal

from scry.config import Config
from scry.evaluation import adapters
from scry.evaluation.accounting import cost_summary, projection_frames
from scry.evaluation.commands import score_commands
from scry.evaluation.judge import load_judgments
from scry.evaluation.questions import load_answers
from scry.jsonl import sha256_file
from scry.run import Run

# Every metric that has per-unit values, and which way is better. The keys of a scorecard's `units` are names of this
# table, and a comparison has one row per name. The direction names what `favours` means on one row; nothing orders,
# weights or combines metrics.
METRICS: dict[str, Literal["higher", "lower"]] = {
    "found": "higher",  # unit: the executed entry's n
    "exact.ocr": "higher",
    "exact.vlm": "higher",
    "exact.any": "higher",
    "submitted": "higher",
    "first_frame_error_abs.any": "lower",
    "submit_frame_error_abs": "lower",
    "false_run": "lower",  # unit: N<i>, the never-run row
    "questions.positive": "higher",  # unit: the question key
    "questions.negative": "higher",
    "cost.per_question": "lower",
    "cost.per_frame": "lower",  # unit: "run"
    "seconds.per_frame": "lower",
}

COUNTERS = {"annotate": ("repairs", "repair_counts", "errors", "failed_targets"),  # what the stages already count,
            "interpret": ("errors", "invalid_citations", "submitted")}  # copied as written: printed per run, never compared


def _sha256(path: str | None) -> str | None:
    return sha256_file(Path(path)) if path and Path(path).exists() else None


def _questions(run: Run, warnings: list[str], notes: list[str]) -> tuple[dict | None, dict]:
    """The questions section and its units. Units are keyed by the question key, which carries the text's hash."""
    answers = load_answers(run)
    failed = sum(a.error is not None for a in answers)
    if failed:
        warnings.append(f"{failed} questions failed and have no answer")
    if not (run.root / "judgments.jsonl").exists():
        if answers:
            notes.append("answers not judged: run scry eval judge")
        return None, {}
    judged = {j.key: j for j in load_judgments(run)}
    section: dict = {}
    units: dict[str, dict[str, float]] = {"cost.per_question": {a.key: a.dollars for a in answers}}
    for polarity in ("positive", "negative"):
        js = [judged[a.key] for a in answers if a.key in judged and a.polarity == polarity]
        scored = [j for j in js if j.label is not None]
        section[polarity] = {"n": len(js), **{label: sum(j.label == label for j in js) for label in ("correct", "partial", "wrong")},
                             "unscored": len(js) - len(scored), "mean": round(mean(j.score for j in scored), 4) if scored else None}
        units[f"questions.{polarity}"] = {j.key: j.score for j in scored}
    section["answers"] = [{"qid": a.qid, "key": a.key, "polarity": a.polarity, "answer": a.answer,
                           "label": judged[a.key].label if a.key in judged else None,
                           "items": judged[a.key].items if a.key in judged else {},
                           "quotes": judged[a.key].quotes if a.key in judged else {},  # the judge's verdict and quote per rubric line
                           "dollars": a.dollars, "seconds": a.seconds, "error": a.error} for a in answers]
    stale = sum(a.key not in judged for a in answers)  # answers to a wording the question file no longer has
    unscored = section["positive"]["unscored"] + section["negative"]["unscored"]
    section |= {"dollars_per_question": round(mean(a.dollars for a in answers), 4) if answers else None,
                "ask_dollars": round(sum(a.dollars for a in answers), 4),  # outside dollars per video
                "judge_dollars": round(sum(j.dollars for j in judged.values()), 4),  # apart
                "seconds_per_question": round(mean(a.seconds for a in answers), 1) if answers else None, "stale": stale}
    if unscored:
        warnings.append(f"{unscored} answers have no verdict from the judge")
    if stale:
        warnings.append(f"{stale} stale answers: the question file changed after the run")
    return section, {name: by_unit for name, by_unit in units.items() if by_unit}


def build_scorecard(run_dir: Path) -> dict:
    """Read a run directory the runner made (evalrun.json, config.json, the manifest, the records through the adapters,
    answers.jsonl and judgments.jsonl when present) and score it. A missing piece gives a `None` section and a note,
    never an exception. Warnings are what weakens the evidence; notes are expected absences."""
    run = Run(run_dir)
    state = json.loads((run.root / "evalrun.json").read_text())
    cfg = Config.model_validate(json.loads((run.root / "config.json").read_text()))
    manifest = run.manifest_read()
    stages = manifest.get("stages", {})
    span = state["span"]
    warnings: list[str] = []
    notes: list[str] = []
    counts = {"frames": adapters.frame_count(run), "transitions": len(adapters.changes(run)), "lifetimes": len(adapters.lifetimes(run))}
    cost = cost_summary(manifest, state["seconds"], counts["frames"], projection_frames(manifest), cfg.model.model)
    warnings += cost["warnings"]
    if not state["cold"]:
        warnings.append("run is not cold")
    if state["resumed"]:
        warnings.append("run was resumed")
    if state["status"] != "done":
        warnings.append(f"run status is {state['status']}")
    for stage in COUNTERS:
        if stages.get(stage, {}).get("errors"):
            warnings.append(f"{stages[stage]['errors']} failed {stage} calls")

    units: dict[str, dict[str, float]] = {}
    commands = None
    if span["ground_truth"]:
        if not Path(span["ground_truth"]).exists():
            warnings.append(f"ground truth not found: {span['ground_truth']}")
        else:
            commands = score_commands(run, cfg, Path(span["ground_truth"]))
            if commands is None:
                warnings.append("no lifetimes: commands not scored")
    if not run.annotations.exists():
        notes.append("no annotations")
    if not adapters.vlm_majority(run):
        notes.append("no second reader: exact.vlm not scored")
    if not run.index_db.exists():
        notes.append("no index: found not scored")
    if not adapters.interpretations(run):
        notes.append("no interpretations: submitted and false run not scored")
    if commands is not None:
        units |= commands["units"]
    questions, question_units = _questions(run, warnings, notes)
    units |= question_units
    for name, value in (("cost.per_frame", cost["per_frame"]), ("seconds.per_frame", cost["seconds_per_frame"])):
        if value is not None:
            units[name] = {"run": value}
    card = {"run": {"phase": state["phase"], "name": state["name"], "config_id": state["config_id"], "span": span["name"],
                    "frames": span["frames"], "values": state["values"], "repeat": state["repeat"], "status": state["status"],
                    "resumed": state["resumed"], "cold": state["cold"], "git_commit": state["code"]["git_commit"],
                    "git_dirty": state["code"]["git_dirty"]},
            "inputs": {"ground_truth_sha256": _sha256(span["ground_truth"]), "questions_sha256": _sha256(span["questions"])},
            "counts": counts, "commands": commands, "questions": questions,
            "counters": {stage: {k: stages[stage][k] for k in keys if k in stages.get(stage, {})} for stage, keys in COUNTERS.items()},
            "cost": cost, "units": units, "warnings": warnings, "notes": notes}
    return json.loads(json.dumps(card))  # as it reads back from scorecard.json or scores.json: rates are two-element lists


def write_scorecard(run_dir: Path, card: dict) -> None:
    path = Path(run_dir) / "scorecard.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(card, indent=2))
    tmp.replace(path)


def score_phase(root: Path, phase: str) -> list[dict]:
    """Build and write the card of every directory under `root/<phase>` that holds an evalrun.json, in name order."""
    cards = []
    for run_dir in sorted(p.parent for p in (Path(root) / phase).glob("*/evalrun.json")):
        card = build_scorecard(run_dir)
        write_scorecard(run_dir, card)
        cards.append(card)
    return cards
