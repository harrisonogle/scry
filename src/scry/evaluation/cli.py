"""`scry eval run | judge | report`. The functions parse arguments, call the harness and print; they hold no logic."""
from __future__ import annotations

import logging
from pathlib import Path

import typer

eval_app = typer.Typer(no_args_is_help=True, help="The evaluation harness: a matrix of cold runs, a blind judge for the answers, a report.")

_ROOT = typer.Option(Path("runs/eval"), "--root", help="run directories go under <root>/<phase>/")


@eval_app.command()
def run(matrix: Path, dry_run: bool = typer.Option(False, "--dry-run", help="list the runs and validate every config; create and spend nothing"),
        only: str | None = typer.Option(None, "--only", help="the one run with this name"), root: Path = _ROOT):
    """Execute the matrix's runs, each cold in its own directory. Costs money. Safe to re-issue: finished runs are
    skipped, an unfinished one is finished and flagged as resumed."""
    from scry.evaluation.matrix import check, load_matrix
    from scry.evaluation.runner import run_matrix
    try:
        m = load_matrix(matrix)
        specs = check(m)
    except (ValueError, OSError) as e:  # a typo in the matrix fails here, before a cent is spent
        typer.echo(f"{matrix}: {e}")
        raise typer.Exit(code=1)
    if dry_run:
        for spec in specs:
            typer.echo(f"{spec.name}: {', '.join(spec.stages)}")
        typer.echo(f"{len(specs)} runs")
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    outcomes = run_matrix(m, root, only=only)
    for o in outcomes:
        typer.echo(f"{o.name}: {o.status}" + (f" ({o.error})" if o.error else ""))
    if not outcomes:
        typer.echo(f"no run named {only}")
    if not outcomes or any(o.status == "failed" for o in outcomes):
        raise typer.Exit(code=1)


@eval_app.command()
def judge(matrix: Path, root: Path = _ROOT):
    """Judge every run's answers against their rubric lines with a separate, blind, low-effort model call. Costs money
    once: the judge's calls are cached under <root>/<phase>/judge-cache."""
    from scry.config import load_config
    from scry.evaluation.judge import judge_phase
    from scry.evaluation.matrix import load_matrix
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    m = load_matrix(matrix)
    for name, js in judge_phase(root, m.phase, load_config(m.base_config)):
        labels = ", ".join(f"{j.qid} {j.label or 'unscored'}" for j in js)
        typer.echo(f"{name}: {len(js)} judged, ${sum(j.dollars for j in js):.4f}: {labels}")


@eval_app.command()
def report(matrix: Path, root: Path = _ROOT, results: Path = typer.Option(Path("docs/results"), "--results", help="report.md and scores.json go under <results>/<phase>/")):
    """Score every run of the phase, measure the noise between repeats, compare every pair of configurations of a span,
    and write the report. Calls no model."""
    from datetime import date

    from scry.evaluation.compare import all_pairs, noise_table
    from scry.evaluation.matrix import load_matrix
    from scry.evaluation.reporting import matrix_order, write_results
    from scry.evaluation.scorecard import score_phase
    m = load_matrix(matrix)
    cards = matrix_order(m, score_phase(root, m.phase))
    if not cards:
        typer.echo(f"no runs under {root / m.phase}")
        raise typer.Exit(code=1)
    for path in write_results(results, m, cards, noise_table(cards), all_pairs(cards), date.today().isoformat()):
        typer.echo(str(path))
