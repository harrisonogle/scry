from __future__ import annotations

import json
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
    """Stage 1: decode, detect changes, settle, write frames/ and stage1.jsonl."""
    _setup_logging(verbose)
    from scry.stage1 import run_stage1
    run_stage1(Run(out), load_config(config), video)


if __name__ == "__main__":
    app()


@app.command()
def ocr(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 2a: OCR every emitted frame → ocr.jsonl."""
    _setup_logging(verbose)
    from scry.stage2a import run_ocr
    run_ocr(Run(run_dir), load_config(config))


@app.command()
def overlay(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 2b: draw numbered boxes → overlays/."""
    _setup_logging(verbose)
    from scry.overlay import run_overlay
    run_overlay(Run(run_dir), load_config(config))


@app.command()
def perceive(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 2c: VLM grouping and transcription → perception.jsonl."""
    _setup_logging(verbose)
    from scry.perceive import run_perceive
    run_perceive(Run(run_dir), load_config(config))


@app.command()
def merge(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 3: merge OCR and VLM output → frames.jsonl."""
    _setup_logging(verbose)
    from scry.merge import run_merge
    run_merge(Run(run_dir), load_config(config))


@app.command()
def diff(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 4/4b: diffs, transients, coalescing → transitions.jsonl, focus.jsonl."""
    _setup_logging(verbose)
    from scry.coalesce import run_diff
    run_diff(Run(run_dir), load_config(config))


@app.command()
def interpret(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 5: VLM interpretation of each transition → interpretations.jsonl."""
    _setup_logging(verbose)
    from scry.interpret import run_interpret
    run_interpret(Run(run_dir), load_config(config))


@app.command()
def hierarchy(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 6: steps, sections, video summary."""
    _setup_logging(verbose)
    from scry.hierarchy import run_hierarchy
    run_hierarchy(Run(run_dir), load_config(config))


@app.command()
def index(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 7: build index.sqlite."""
    _setup_logging(verbose)
    from scry.index import build_index
    build_index(Run(run_dir), load_config(config))


@app.command()
def search(run_dir: Path, query: str, level: str | None = None, config: Path | None = None):
    """Search the index (lexical + trigram, vector if configured)."""
    from scry.index import get_embedder, open_db, search as _search
    cfg = load_config(config)
    db = open_db(Run(run_dir).index_db)
    for h in _search(db, query, cfg.index, get_embedder(cfg.index), level=level):
        typer.echo(f"{h['score']:.4f} {h['level']:<10} {h['item_id']:<8} t={h['t'][0]:.1f}-{h['t'][1]:.1f}  {h['text'][:100]}")


@app.command()
def ask(run_dir: Path, question: str, config: Path | None = None, verbose: bool = False):
    """Answer a question over a run's index with citations."""
    _setup_logging(verbose)
    from scry.agent import ask as _ask
    typer.echo(_ask(Run(run_dir), load_config(config), question))


@app.command()
def subset(src: Path, out: Path = typer.Option(..., "--out"),
           frames: str = typer.Option(..., "--frames", help="inclusive Stage 1 frame range, e.g. 145-155"),
           share_cache: bool = typer.Option(True, "--share-cache/--no-share-cache", help="symlink the source run's call cache"),
           verbose: bool = False):
    """Derive a small run directory from an existing run's Stage 1 frames, for cheap live checks of the model stages."""
    _setup_logging(verbose)
    from scry.subset import make_subset, parse_frames
    dst = make_subset(Run(src), out, parse_frames(frames), share_cache)
    typer.echo(f"{out}: {len(dst.load_stage1())} frames; Stage 1 is marked done, so `scry run <video> --out {out}` runs the rest")


STAGES = ["outline", "decode", "ocr", "overlay", "perceive", "merge", "diff", "interpret", "hierarchy", "index"]


@app.command()
def run(video: Path, out: Path = typer.Option(..., "--out"), config: Path | None = None, stages: str | None = None, verbose: bool = False):
    """Run every stage in order (idempotent; each stage skips itself when inputs and config are unchanged)."""
    _setup_logging(verbose)
    cfg = load_config(config)
    r = Run(out)
    wanted = stages.split(",") if stages else STAGES
    import time
    from scry import coalesce, hierarchy as hier, index as idx, interpret as interp, merge as mrg, overlay as ov, perceive as perc, stage1, stage2a
    from scry.diagnostics import diagnostics

    def _outline():
        from scry.outline import run_outline  # created in Task 20; imported lazily so `scry run` works before that task lands
        run_outline(r, cfg, video)

    steps = {"outline": _outline, "decode": lambda: stage1.run_stage1(r, cfg, video),
             "ocr": lambda: stage2a.run_ocr(r, cfg), "overlay": lambda: ov.run_overlay(r, cfg), "perceive": lambda: perc.run_perceive(r, cfg),
             "merge": lambda: mrg.run_merge(r, cfg), "diff": lambda: coalesce.run_diff(r, cfg), "interpret": lambda: interp.run_interpret(r, cfg),
             "hierarchy": lambda: hier.run_hierarchy(r, cfg), "index": lambda: idx.build_index(r, cfg)}
    keys = {"decode": "stage1", "ocr": "ocr", "overlay": "overlay", "perceive": "perceive", "merge": "merge", "diff": "diff",
            "interpret": "interpret", "hierarchy": "hierarchy", "index": "index"}
    for name in STAGES:
        if name in wanted:
            typer.echo(f"== {name}")
            t0 = time.perf_counter()
            steps[name]()
            st = r.manifest_read().get("stages", {})
            if keys.get(name) in st:  # per-stage wall time (§18.4)
                st[keys[name]]["seconds"] = round(time.perf_counter() - t0, 1)
                r.manifest_update(stages=st)
    r.manifest_update(diagnostics=diagnostics(r))
    typer.echo(json.dumps(r.manifest_read().get("diagnostics", {}), indent=2))


@app.command()
def setup(config: Path | None = None):
    """Check the environment: Vision OCR, FTS5, sqlite-vec, credentials, optional embedder."""
    import sqlite3
    cfg = load_config(config)
    ok = True
    try:
        from scry.ocr import get_engine
        get_engine(cfg.ocr)
        typer.echo(f"ocr engine {cfg.ocr.engine}: ok")
    except Exception as e:
        ok = False
        typer.echo(f"ocr engine {cfg.ocr.engine}: FAILED ({e})")
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
