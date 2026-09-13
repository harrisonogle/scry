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
