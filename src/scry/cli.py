from __future__ import annotations

import logging
from pathlib import Path

import typer

from scry.config import load_config
from scry.run import Run

app = typer.Typer(no_args_is_help=True, help="Visual transcript pipeline")


@app.callback()
def _startup():
    """Load ./.env (git-ignored; see .env.example) before any command; real environment variables win."""
    from scry.env import load_dotenv

    load_dotenv()


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(asctime)s %(name)s %(message)s")


@app.command()
def decode(video: Path, out: Path = typer.Option(..., "--out"), config: Path | None = None, verbose: bool = False):
    """decode: detect changes, settle, write frames/ and frames.jsonl."""
    _setup_logging(verbose)
    from scry.decode import run_decode
    run_decode(Run(out), load_config(config), video)


@app.command()
def subset(src: Path, out: Path = typer.Option(..., "--out"),
           frames: str = typer.Option(..., "--frames", help="inclusive frame range, e.g. 145-155"),
           share_cache: bool = typer.Option(True, "--share-cache/--no-share-cache", help="symlink the source run's call cache"),
           verbose: bool = False):
    """Derive a small run directory from an existing run's decoded frames, for cheap live checks of the later stages."""
    _setup_logging(verbose)
    from scry.subset import make_subset, parse_frames
    dst = make_subset(Run(src), out, parse_frames(frames), share_cache)
    typer.echo(f"{out}: {len(dst.load_frames())} frames; decode is marked done, so `scry run <video> --out {out}` runs the rest")


STAGES = ["outline", "decode"]


@app.command()
def run(video: Path, out: Path = typer.Option(..., "--out"), config: Path | None = None, stages: str | None = None, verbose: bool = False):
    """Run every stage in order (idempotent; each stage skips itself when inputs and config are unchanged)."""
    _setup_logging(verbose)
    cfg = load_config(config)
    r = Run(out)
    wanted = stages.split(",") if stages else STAGES
    import time
    from scry.decode import run_decode

    def _outline():
        from scry.outline import run_outline
        run_outline(r, cfg, video)

    steps = {"outline": _outline, "decode": lambda: run_decode(r, cfg, video)}
    for name in STAGES:
        if name in wanted:
            typer.echo(f"== {name}")
            t0 = time.perf_counter()
            steps[name]()
            st = r.manifest_read().get("stages", {})
            if name in st:  # per-stage wall time; the step name is the manifest key
                st[name]["seconds"] = round(time.perf_counter() - t0, 1)
                r.manifest_update(stages=st)


@app.command()
def setup(config: Path | None = None):
    """Check the environment: the OCR engine, FTS5, sqlite-vec, credentials, optional embedder."""
    import sqlite3
    cfg = load_config(config)
    ok = True
    try:
        from scry.ocr import get_engine
        get_engine(cfg.read)
        typer.echo(f"ocr engine {cfg.read.engine}: ok")
    except Exception as e:
        ok = False
        typer.echo(f"ocr engine {cfg.read.engine}: FAILED ({e})")
    try:
        sqlite3.connect(":memory:").execute("create virtual table t using fts5(x)")
        typer.echo("sqlite fts5: ok")
    except Exception as e:
        ok = False
        typer.echo(f"sqlite fts5: FAILED ({e})")
    try:
        import sqlite_vec
        db = sqlite3.connect(":memory:"); db.enable_load_extension(True); sqlite_vec.load(db)
        typer.echo("sqlite-vec: ok")
    except Exception as e:
        typer.echo(f"sqlite-vec: unavailable ({e}); lexical retrieval only")
    import os
    from scry.env import LOADED
    if os.environ.get("ANTHROPIC_API_KEY"):
        typer.echo("anthropic credentials: ANTHROPIC_API_KEY set" + (" (from .env)" if "ANTHROPIC_API_KEY" in LOADED else " (from the environment)"))
    else:
        typer.echo("anthropic credentials: no ANTHROPIC_API_KEY in the environment or ./.env (an `ant auth login` profile may still work)")
    if cfg.index.embedder != "none":
        try:
            from scry.index import get_embedder
            get_embedder(cfg.index)
            typer.echo(f"embedder {cfg.index.embedder}: ok")
        except Exception as e:
            typer.echo(f"embedder {cfg.index.embedder}: FAILED ({e})")
    raise typer.Exit(code=0 if ok else 1)


@app.command()
def outline(video: Path, out: Path = typer.Option(..., "--out"), import_path: Path | None = typer.Option(None, "--import"), config: Path | None = None):
    """Stage 0 (optional): Gemini agentic chapter outline, or import one from a JSON file."""
    from scry.outline import run_outline
    cfg = load_config(config)
    if import_path is None and not cfg.outline.enabled:
        typer.echo("outline disabled in config (set [outline] enabled = true) and no --import given")
        raise typer.Exit(code=1)
    run_outline(Run(out), cfg, video, import_path)


if __name__ == "__main__":
    app()
