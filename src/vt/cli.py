from __future__ import annotations

import logging
from pathlib import Path

import typer

from vt.config import load_config
from vt.run import Run

app = typer.Typer(no_args_is_help=True, help="Visual transcript pipeline")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(asctime)s %(name)s %(message)s")


@app.command()
def decode(video: Path, out: Path = typer.Option(..., "--out"), config: Path | None = None, verbose: bool = False):
    """Stage 1: decode, detect changes, settle, write frames/ and stage1.jsonl."""
    _setup_logging(verbose)
    from vt.stage1 import run_stage1
    run_stage1(Run(out), load_config(config), video)


if __name__ == "__main__":
    app()


@app.command()
def ocr(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 2a: OCR every emitted frame → ocr.jsonl."""
    _setup_logging(verbose)
    from vt.stage2a import run_ocr
    run_ocr(Run(run_dir), load_config(config))


@app.command()
def overlay(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 2b: draw numbered boxes → overlays/."""
    _setup_logging(verbose)
    from vt.overlay import run_overlay
    run_overlay(Run(run_dir), load_config(config))


@app.command()
def perceive(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 2c: VLM grouping and transcription → perception.jsonl."""
    _setup_logging(verbose)
    from vt.perceive import run_perceive
    run_perceive(Run(run_dir), load_config(config))


@app.command()
def merge(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 3: merge OCR and VLM output → frames.jsonl."""
    _setup_logging(verbose)
    from vt.merge import run_merge
    run_merge(Run(run_dir), load_config(config))


@app.command()
def diff(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 4/4b: diffs, transients, coalescing → transitions.jsonl, focus.jsonl."""
    _setup_logging(verbose)
    from vt.coalesce import run_diff
    run_diff(Run(run_dir), load_config(config))


@app.command()
def interpret(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 5: VLM interpretation of each transition → interpretations.jsonl."""
    _setup_logging(verbose)
    from vt.interpret import run_interpret
    run_interpret(Run(run_dir), load_config(config))


@app.command()
def hierarchy(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 6: steps, sections, video summary."""
    _setup_logging(verbose)
    from vt.hierarchy import run_hierarchy
    run_hierarchy(Run(run_dir), load_config(config))


@app.command()
def index(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 7: build index.sqlite."""
    _setup_logging(verbose)
    from vt.index import build_index
    build_index(Run(run_dir), load_config(config))


@app.command()
def search(run_dir: Path, query: str, level: str | None = None, config: Path | None = None):
    """Search the index (lexical + trigram, vector if configured)."""
    from vt.index import get_embedder, open_db, search as _search
    cfg = load_config(config)
    db = open_db(Run(run_dir).index_db)
    for h in _search(db, query, cfg.index, get_embedder(cfg.index), level=level):
        typer.echo(f"{h['score']:.4f} {h['level']:<10} {h['item_id']:<8} t={h['t'][0]:.1f}-{h['t'][1]:.1f}  {h['text'][:100]}")


@app.command()
def ask(run_dir: Path, question: str, config: Path | None = None, verbose: bool = False):
    """Answer a question over a run's index with citations."""
    _setup_logging(verbose)
    from vt.agent import ask as _ask
    typer.echo(_ask(Run(run_dir), load_config(config), question))
