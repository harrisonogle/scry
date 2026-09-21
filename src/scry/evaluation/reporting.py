"""The phase report: Markdown for a person, and scores.json holding every scorecard so that the report can be rebuilt,
and the judge audited, from committed data. Every table that shows a score or a question result ends with dollars per
frame and per video. The report orders, weights and combines nothing: the verdict column holds only `outside`,
`inside`, `unknown` and `not comparable` (of the noise), and nothing here names a better configuration."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean

from scry.evaluation.accounting import BATCH_PRICE_SHARE
from scry.evaluation.compare import Row
from scry.evaluation.matrix import Matrix, expand

WEAK_EVIDENCE = (
    "An `outside` row means only that the difference is larger than the largest difference seen between identical cold "
    "runs of the two configurations, scaled for means of repeats. With three repeats a side that floor is a range of three "
    "values: by a normal approximation about one row in eight reads `outside` when nothing differs [estimated], and this "
    "report has dozens of rows. One `outside` row is weak evidence. Nothing here is a verdict, and no row decides anything "
    "by itself.")
EXACT_ANY = ("`exact.any` is what compares bases that have different readers; it can only tie or rise with a second reader, "
             "so it is shown as what the second reading adds, at its price, beside `exact.ocr`, not as a contest.")
RATES = ("found", "exact.ocr", "exact.vlm", "exact.any", "submitted", "false_run")
ERRORS = ("first_frame_error_abs.ocr", "first_frame_error_abs.vlm", "first_frame_error_abs.any", "submit_frame_error_abs")
COST_HEADERS = ["$ / frame", "$ / video"]


def _mean(values: list, places: int) -> float | None:
    values = [v for v in values if v is not None]
    return round(mean(values), places) if values else None


def _usd(x: float | None, places: int = 4) -> str:
    return "—" if x is None else f"${x:.{places}f}"


def _kn(pair: list | None) -> str:
    return "—" if pair is None else f"{pair[0]}/{pair[1]}"


def _rate(commands: dict | None, name: str) -> list | None:
    if commands is None:
        return None
    rates = commands["rates"]
    return rates["exact"].get(name[6:]) if name.startswith("exact.") else rates[name]


def _error(commands: dict | None, name: str) -> list | None:
    """[mean absolute frames, the number of entries it is over]."""
    if commands is None:
        return None
    if name == "submit_frame_error_abs":
        value, n = commands["submit_frame_error_abs_mean"], commands["submit_frame_error_abs_n"]
    else:
        reader = name.rpartition(".")[2]
        value, n = commands["first_frame_error_abs_mean"].get(reader), commands["first_frame_error_abs_n"].get(reader)
    return None if value is None else [value, n]


def matrix_order(m: Matrix, cards: list[dict]) -> list[dict]:
    """The cards in the matrix's expansion order, so configurations appear as the matrix lists them; others last."""
    position = {spec.name: i for i, spec in enumerate(expand(m))}
    return sorted(cards, key=lambda c: (position.get(c["run"]["name"], len(position)), c["run"]["name"]))


def config_rows(cards: list[dict]) -> list[dict]:
    """One row per configuration, in the order the cards first name them: means over its repeats, and the per-repeat
    values (rates as [k, n], errors as [mean, n], question means)."""
    groups: dict[str, list[dict]] = {}
    for c in cards:
        groups.setdefault(c["run"]["config_id"], []).append(c)
    rows = []
    for config_id, group in groups.items():
        group = sorted(group, key=lambda c: c["run"]["repeat"])
        commands = [c["commands"] for c in group]
        row = {"config_id": config_id, "span": group[0]["run"]["span"], "values": group[0]["run"]["values"], "repeats": len(group),
               "runs": [c["run"]["name"] for c in group], "cards": group,
               "dollars": _mean([c["cost"]["dollars"] for c in group], 4), "per_frame": _mean([c["cost"]["per_frame"] for c in group], 4),
               "per_video": _mean([c["cost"]["per_video"] for c in group], 2),
               "seconds_per_frame": _mean([c["cost"]["seconds_per_frame"] for c in group], 1), "rates": {}, "errors": {}, "questions": None}
        for name in RATES:
            per_repeat = [_rate(cmd, name) for cmd in commands]
            row["rates"][name] = {"per_repeat": per_repeat, "mean": _mean([p[0] / p[1] for p in per_repeat if p and p[1]], 4)}
        for name in ERRORS:
            per_repeat = [_error(cmd, name) for cmd in commands]
            row["errors"][name] = {"per_repeat": per_repeat, "mean": _mean([p[0] for p in per_repeat if p], 2)}
        judged = [c["questions"] for c in group if c["questions"] is not None]
        if judged:
            row["questions"] = {
                polarity: {**{k: sum(q[polarity][k] for q in judged) for k in ("n", "correct", "partial", "wrong", "unscored")},
                           "per_repeat": [q[polarity]["mean"] for q in judged], "mean": _mean([q[polarity]["mean"] for q in judged], 4)}
                for polarity in ("positive", "negative")}
            row |= {"dollars_per_question": _mean([q["dollars_per_question"] for q in judged], 4),
                    "seconds_per_question": _mean([q["seconds_per_question"] for q in judged], 1),
                    "ask_dollars": _mean([q["ask_dollars"] for q in judged], 4), "judge_dollars": _mean([q["judge_dollars"] for q in judged], 4),
                    "stale": sum(q["stale"] for q in judged)}
        rows.append(row)
    return rows


def table(headers: list[str], rows: list[list]) -> str:
    """A Markdown table; None prints as a dash."""
    def cell(x) -> str:
        return "—" if x is None else str(x).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    return "\n".join(lines + ["| " + " | ".join(cell(x) for x in row) + " |" for row in rows])


def _cost(row: dict) -> list[str]:
    return [_usd(row["per_frame"]), _usd(row["per_video"], 2)]


def _per_repeat(cells: list[str], average: float | None) -> str:
    return ", ".join(cells) + ("" if average is None else f"; mean {average:g}")


def _header(m: Matrix, cards: list[dict], today: str) -> list[str]:
    by_status = Counter(c["run"]["status"] for c in cards)
    commits = Counter(c["run"]["git_commit"] or "unknown" for c in cards)
    dirty = [c["run"]["name"] for c in cards if c["run"]["git_dirty"]]
    projections = sorted({c["cost"]["projection_frames"] for c in cards if c["cost"]["projection_frames"] is not None})
    frames = " or ".join(str(n) for n in projections) if projections else "an unknown number of"
    return [f"# {m.phase} evaluation report", "",
            f"Date: {today}. Matrix: `{m.path}`. Source run: `{m.source}`. Runs: {len(cards)}.", "",
            "Runs by status: " + (", ".join(f"{status} {n}" for status, n in by_status.items()) or "none") + ".",
            "Commits the runs started on: " + (", ".join(f"`{commit[:12]}` ({n} runs)" for commit, n in commits.items()) or "none") + ".",
            "Runs that started on a dirty tree: " + (", ".join(dirty) or "none") + ".", "",
            f"$ / video = $ / frame × {frames} frames, a linear projection from this span to the whole source video. Dollars are "
            "what a cold run pays at the synchronous list price, from the stages' manifest usage (an answer served from a call cache "
            "is priced as if paid); the batch price is half. The question set's dollars are per question and outside $ / video; "
            "the judge's dollars are apart from both.", "", WEAK_EVIDENCE, ""]


def _runs(cards: list[dict]) -> list[str]:
    rows = [[c["run"]["name"], c["run"]["status"], c["counts"]["frames"], "yes" if c["run"]["cold"] else "no",
             "yes" if c["run"]["resumed"] else "no", c["cost"]["cache_hits"], _usd(c["cost"]["dollars"]), _usd(c["cost"]["per_frame"]),
             _usd(c["cost"]["per_video"], 2), c["cost"]["seconds"], c["cost"].get("question_seconds")] for c in cards]
    counters = [[c["run"]["name"], *(json.dumps(c["counters"][stage], sort_keys=True) if c["counters"][stage] else None
                                     for stage in ("annotate", "interpret"))] for c in cards]
    return ["## Runs", "", table(["run", "status", "frames", "cold", "resumed", "cache hits", "$", *COST_HEADERS, "pipeline s", "questions s"], rows), "",
            "The stages' own counters, reported, never compared:", "", table(["run", "annotate", "interpret"], counters), ""]


def _cost_section(configs: list[dict], cards: list[dict]) -> list[str]:
    rows = []
    for cfg in configs:
        by_stage = [c["cost"]["by_stage"] for c in cfg["cards"]]
        frames = [c["cost"]["frames"] for c in cfg["cards"]]
        for stage in dict.fromkeys(s for stages in by_stage for s in stages):
            mine = [(stages[stage], n) for stages, n in zip(by_stage, frames) if stage in stages]
            if not any(s["dollars"] or s["seconds"] for s, _ in mine):
                continue  # decode: carried by subset, neither paid nor timed here
            dollars, per_frame = _mean([s["dollars"] for s, _ in mine], 4), _mean([s["per_frame"] for s, _ in mine], 4)
            per_video = _mean([s["per_video"] for s, _ in mine], 2)
            rows.append([cfg["config_id"], stage, _usd(dollars), _usd(per_frame), _usd(per_video, 2), *_batch(dollars, per_frame, per_video),
                         _mean([s["seconds"] / n for s, n in mine if n], 1)])
        rows.append([cfg["config_id"], "all stages", _usd(cfg["dollars"]), *_cost(cfg), *_batch(cfg["dollars"], cfg["per_frame"], cfg["per_video"]),
                     cfg["seconds_per_frame"]])
    out = ["## Cost", "", "Means over a configuration's repeats, per stage. One figure per stage, at the synchronous list price; the batch "
           "columns are half of it. s / frame is the wall time of the stages the dollars cover (the pipeline through `index`); "
           "answering the questions is timed per question, below.", "",
           table(["configuration", "stage", "$", *COST_HEADERS, "batch $", "batch $ / frame", "batch $ / video", "s / frame"], rows), ""]
    asked = [cfg for cfg in configs if cfg["questions"] is not None]
    if asked:
        out += ["The question set, outside $ / video, and the judge, apart (means per run):", "",
                table(["configuration", "$ / question", "s / question", "question set $", "judge $"],
                      [[cfg["config_id"], _usd(cfg["dollars_per_question"]), cfg["seconds_per_question"], _usd(cfg["ask_dollars"]),
                        _usd(cfg["judge_dollars"])] for cfg in asked]), ""]
    judged = [c["questions"] for c in cards if c["questions"] is not None]
    out += [f"Spend over all {len(cards)} runs: pipeline {_usd(sum(c['cost']['dollars'] for c in cards))}; question set "
            f"{_usd(sum(q['ask_dollars'] for q in judged))}; judge {_usd(sum(q['judge_dollars'] for q in judged))} "
            "(what the last pass of `scry eval judge` paid: a verdict served from the judge's cache costs nothing).", ""]
    return out


def _batch(dollars: float | None, per_frame: float | None, per_video: float | None) -> list[str]:
    half = [None if x is None else x * BATCH_PRICE_SHARE for x in (dollars, per_frame, per_video)]
    return [_usd(half[0]), _usd(half[1]), _usd(half[2], 2)]


def _commands(configs: list[dict]) -> list[str]:
    scored = [cfg for cfg in configs if any(c["commands"] is not None for c in cfg["cards"])]
    out = ["## Commands", ""]
    if not scored:
        return out + ["No span of this phase names a command list.", ""]

    def rate(cfg: dict, name: str) -> str:
        r = cfg["rates"][name]
        return _per_repeat([_kn(p) for p in r["per_repeat"]], r["mean"])

    def error(cfg: dict, name: str) -> str:
        e = cfg["errors"][name]
        return _per_repeat(["—" if p is None else f"{p[0]:g} over {p[1]}" for p in e["per_repeat"]], e["mean"])

    out += ["**Primary, side by side, with no order between them:** found and exact, as k/n of the rated entries per repeat, then "
            "the mean. Every comparison with the command list is by frame number. " + EXACT_ANY, "",
            table(["configuration", "found", "exact.ocr", "exact.vlm", "exact.any", *COST_HEADERS],
                  [[cfg["config_id"], *(rate(cfg, n) for n in ("found", "exact.ocr", "exact.vlm", "exact.any")), *_cost(cfg)] for cfg in scored]), "",
            "**Secondary:** the first-appearance error and the submission error (mean absolute frames over the entries that have "
            "one, per repeat), submitted and false run (k/n per repeat).", "",
            table(["configuration", "first appearance, ocr", "first appearance, vlm", "first appearance, any", "submitted",
                   "submission error", "false run", *COST_HEADERS],
                  [[cfg["config_id"], *(error(cfg, n) for n in ERRORS[:3]), rate(cfg, "submitted"), error(cfg, ERRORS[3]), rate(cfg, "false_run"),
                    *_cost(cfg)] for cfg in scored]), "",
            "Per entry, in how many runs (of those that scored it). `summary only`: no localising entry covered the command and a "
            "summary entry of that level quoted it. `Y` and `y` are reported and not rated.", ""]
    entries, never = [], []
    for cfg in scored:
        cmds = [c["commands"] for c in cfg["cards"] if c["commands"] is not None]
        for i, first in enumerate(cmds[0]["entries"]):
            mine = [cmd["entries"][i] for cmd in cmds]

            def runs(value) -> str:
                got = [value(e) for e in mine if value(e) is not None]
                return f"{sum(got)}/{len(got)}" if got else "—"

            levels = Counter(e["level"] for e in mine if e["found"] is False and e["level"])
            entries.append([cfg["config_id"], first["n"], f"`{first['text']}`", runs(lambda e: e["found"]), runs(lambda e: e["exact"]["any"]),
                            runs(lambda e: e["submitted"]), ", ".join(f"{level} ×{n}" for level, n in levels.items()) or None,
                            None if first["scorable"] else "not rated", *_cost(cfg)])
        for i, first in enumerate(cmds[0]["never_run"]):
            got = [cmd["never_run"][i]["false_run"] for cmd in cmds if cmd["never_run"][i]["false_run"] is not None]
            never.append([cfg["config_id"], f"N{i + 1}", f"`{first['text']}`", f"{sum(got)}/{len(got)}" if got else "—", *_cost(cfg)])
    out += [table(["configuration", "#", "text", "found", "exact.any", "submitted", "summary only", "note", *COST_HEADERS], entries), "",
            "Texts that appeared on screen and were never run: in how many runs a `submitted: yes` claimed them (false run).", "",
            table(["configuration", "row", "text", "false run", *COST_HEADERS], never), ""]
    return out


def _questions(configs: list[dict]) -> list[str]:
    asked = [cfg for cfg in configs if cfg["questions"] is not None]
    out = ["## Questions", ""]
    if not asked:
        return out + ["No run of this phase has judged answers (`scry eval judge`).", ""]
    for polarity, weight in (("positive", "primary"), ("negative", "secondary")):
        rows = []
        for cfg in asked:
            q = cfg["questions"][polarity]
            rows.append([cfg["config_id"], q["n"], q["correct"], q["partial"], q["wrong"], q["unscored"],
                         _per_repeat(["—" if v is None else f"{v:g}" for v in q["per_repeat"]], q["mean"]),
                         _usd(cfg["dollars_per_question"]), *_cost(cfg)])
        out += [f"**The {polarity} questions ({weight}).** Counts over the configuration's repeats; the mean scores correct 1, partial "
                "0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.", "",
                table(["configuration", "answers", "correct", "partial", "wrong", "unscored", "mean", "$ / question", *COST_HEADERS], rows), ""]
    rows = []
    for cfg in asked:
        per_run = [{a["key"]: a for a in c["questions"]["answers"]} for c in cfg["cards"] if c["questions"] is not None]
        for key in dict.fromkeys(k for answers in per_run for k in answers):
            first = next(answers[key] for answers in per_run if key in answers)
            labels = [answers[key]["label"] or ("error" if answers[key]["error"] else "unscored") if key in answers else "—" for answers in per_run]
            rows.append([cfg["config_id"], first["qid"], first["polarity"], ", ".join(labels), *_cost(cfg)])
    out += ["Per question, the label of each repeat (every answer, with the judge's verdict and quote for each rubric line, is in "
            "`scores.json`).", "", table(["configuration", "question", "polarity", "labels per repeat", *COST_HEADERS], rows), "",
            "Stale answers (to a wording the question file no longer has), not judged: "
            + ", ".join(f"{cfg['config_id']} {cfg['stale']}" for cfg in asked) + ". Unscored answers: "
            + ", ".join(f"{cfg['config_id']} {cfg['questions']['positive']['unscored'] + cfg['questions']['negative']['unscored']}" for cfg in asked) + ".", ""]
    return out


def _noise(configs: list[dict], noise: dict) -> list[str]:
    by_id = {cfg["config_id"]: cfg for cfg in configs}
    rows = [[config_id, metric, ", ".join(f"{v:g}" for v in entry["values"]), None if entry["max"] is None else f"{entry['max']:g}",
             *(_cost(by_id[config_id]) if config_id in by_id else [None, None])]
            for config_id, metrics in noise.items() for metric, entry in metrics.items()]
    return ["## Noise", "", "Per configuration and metric: the value of each repeat (the mean of its units) and the largest paired "
            "difference between two repeats, which is the floor for one run against one run.", "",
            table(["configuration", "metric", "repeats", "largest paired difference", *COST_HEADERS], rows) if rows else
            "No configuration has two repeats: no floor was measured.", ""]


def _comparisons(comparisons: list[tuple[str, str, str, list[Row]]]) -> list[str]:
    out = ["## Comparisons", ""]
    if not comparisons:
        out += ["No span has two configurations.", ""]
    for span, a, b, rows in comparisons:
        def num(x: float | None) -> str | None:
            return None if x is None else f"{x:g}"
        body = [[r.metric, r.better, num(r.mean_a), num(r.mean_b), num(r.diff), num(r.floor),
                 r.verdict, r.reason, r.favours.upper() if r.favours else None, r.units, r.dropped,
                 _usd(r.cost_a["per_frame"]), _usd(r.cost_a["per_video"], 2), _usd(r.cost_b["per_frame"]), _usd(r.cost_b["per_video"], 2)]
                for r in rows]
        flips = [f"- {r.metric}: {flip}" for r in rows for flip in r.flips]
        out += [f"### {span}: A = {a}, B = {b}", "", "Differences are B − A, paired over the units every run of both sides has.", "",
                table(["metric", "better", "A", "B", "difference", "floor", "verdict", "reason", "favours", "units", "dropped", "A $ / frame",
                       "A $ / video", "B $ / frame", "B $ / video"], body), "",
                *(["Units that every run of one side has and no run of the other:", "", *flips, ""] if flips else [])]
    return out


def phase_report(m: Matrix, cards: list[dict], noise: dict, comparisons: list[tuple[str, str, str, list[Row]]], today: str) -> str:
    configs = config_rows(cards)
    warnings = [f"- {c['run']['name']}: {w}" for c in cards for w in c["warnings"]]
    notes = [f"- {c['run']['name']}: {n}" for c in cards for n in c["notes"]]
    lines = [*_header(m, cards, today), "## Warnings", "", *(warnings or ["none"]), "",
             *(["Notes (expected absences):", "", *notes, ""] if notes else []),
             *_runs(cards), *_cost_section(configs, cards), *_commands(configs), *_questions(configs), *_noise(configs, noise),
             *_comparisons(comparisons)]
    return "\n".join(lines)


def write_results(results_dir: Path, m: Matrix, cards: list[dict], noise: dict, comparisons: list[tuple[str, str, str, list[Row]]],
                  today: str) -> list[Path]:
    """`<results>/<phase>/report.md` and `scores.json` (every scorecard of the phase)."""
    out = Path(results_dir) / m.phase
    out.mkdir(parents=True, exist_ok=True)
    report, scores = out / "report.md", out / "scores.json"
    report.write_text(phase_report(m, cards, noise, comparisons, today))
    scores.write_text(json.dumps({"phase": m.phase, "matrix": str(m.path), "date": today, "scorecards": cards}, indent=1))
    return [report, scores]
