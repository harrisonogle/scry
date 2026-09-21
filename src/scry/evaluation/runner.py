from __future__ import annotations

import importlib
import json
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from scry.config import Config
from scry.evaluation.matrix import Matrix, RunSpec, config_for, expand
from scry.jsonl import sha256_obj
from scry.run import Run
from scry.subset import make_subset

log = logging.getLogger(__name__)

STAGE_FUNCS: dict[str, str] = {
    "read": "scry.read:run_read",
    "track": "scry.track.stage:run_track",
    "annotate": "scry.annotate:run_annotate",
    "interpret": "scry.interpret:run_interpret",
    "summarize": "scry.summarize:run_summarize",
    "index": "scry.index:build_index",
}


def resolve(stage: str) -> Callable[[Run, Config], None]:
    """The stage's entry point, imported when first asked for, so the harness imports before every stage exists."""
    module, _, name = STAGE_FUNCS[stage].partition(":")
    return getattr(importlib.import_module(module), name)


def code_identity(repo: Path) -> dict:
    """The commit the code is at and whether the tree is dirty. Recorded, never refused."""
    def git(*args: str) -> str | None:
        try:
            done = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
        except OSError:  # no git
            return None
        return done.stdout.strip() if done.returncode == 0 else None

    return {"git_commit": git("rev-parse", "HEAD") or None, "git_dirty": bool(git("status", "--porcelain"))}


@dataclass
class RunOutcome:
    name: str
    status: Literal["done", "failed", "skipped"]
    seconds: dict[str, float]
    error: str | None


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _span(spec: RunSpec) -> dict:
    s = spec.span
    return {"name": s.name, "frames": list(s.frames), "ground_truth": str(s.ground_truth) if s.ground_truth else None,
            "questions": str(s.questions) if s.questions else None}


def _spec_hash(spec: RunSpec) -> str:
    """What a run directory was made from. The copy source is in it only when there is one, so the hash of every run
    that built its own pipeline is what it always was."""
    copied = {"copy": str(spec.copy_from)} if spec.copy_from is not None else {}
    return sha256_obj({"name": spec.name, "span": _span(spec), "overrides": spec.overrides, "stages": list(spec.stages)} | copied)


def _write_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, default=str))
    tmp.replace(path)


# What a copy leaves behind, at the top of the run it copies: the harness's state and the run's config (this run has its
# own), the answers with their verdicts and scores (asking again is the point), and the frames `redecode` saved for them.
NOT_PIPELINE = ("evalrun.json", "config.json", "answers.jsonl", "judgments.jsonl", "scorecard.json", "redecode")


def check_copy(m: Matrix, spec: RunSpec) -> dict:
    """The state of the finished run whose pipeline `spec` copies. A copy must not mislabel what it holds, so it is
    refused unless that run is finished, covers the span's frames and was built with the spec's config in every
    section but `[ask]`, the one section no pipeline stage reads. Only reads."""
    src = Path(spec.copy_from)
    if not (src / "evalrun.json").exists():
        raise ValueError(f"{src} is not a run of the harness: it has no evalrun.json")
    state = json.loads((src / "evalrun.json").read_text())
    if state["status"] != "done":
        raise ValueError(f"{src} is not finished: its status is {state['status']}")
    if state["span"]["frames"] != list(spec.span.frames):
        raise ValueError(f"{src} covers frames {state['span']['frames']}, not {list(spec.span.frames)}")
    built = Config.model_validate(json.loads((src / "config.json").read_text())).model_dump()
    mine = config_for(m, spec).model_dump()
    differ = [section for section in mine if section != "ask" and mine[section] != built[section]]
    if differ:
        raise ValueError(f"{src} was built with a different " + ", ".join(f"[{section}]" for section in differ))
    return state


def materialise(m: Matrix, spec: RunSpec, root: Path, identity: dict) -> Run:
    """The run directory `root/<phase>/<name>`: derived from the matrix's source with a private, empty call cache, or
    reused when it was made from the same spec. Nothing is written under the source. A spec that copies a pipeline
    gets every file of that finished run but NOT_PIPELINE, byte for byte, and is never cold; nothing is written there."""
    out = Path(root) / spec.phase / spec.name
    state = out / "evalrun.json"
    spec_hash = _spec_hash(spec)
    if state.exists():
        if json.loads(state.read_text())["spec_hash"] != spec_hash:
            raise ValueError(f"{out} was made from a different spec: the matrix changed under a run; "
                             "choose a new phase name or delete the directory")
        return Run(out)
    cfg = config_for(m, spec)  # a bad override fails before anything is created
    if spec.copy_from is not None:
        check_copy(m, spec)
        src = Path(spec.copy_from)
        shutil.copytree(src, out, ignore=lambda d, names: [n for n in names if n in NOT_PIPELINE] if Path(d) == src else [])
        run = Run(out)
    else:
        run = make_subset(m.source, out, spec.span.frames, share_cache=False)
    cache = run.cache_dir
    _write_json(out / "config.json", cfg.model_dump())
    _write_json(state, {
        "phase": spec.phase, "name": spec.name, "config_id": spec.config_id, "span": _span(spec),
        "values": spec.values, "repeat": spec.repeat, "overrides": spec.overrides, "stages": list(spec.stages),
        "matrix": str(m.path), "spec_hash": spec_hash, "code": dict(identity),
        **({"copied_from": str(spec.copy_from)} if spec.copy_from is not None else {}),  # the pipeline was not built here
        "cold": spec.copy_from is None and cache.is_dir() and not cache.is_symlink() and not any(cache.iterdir()),
        "started": None, "finished": None, "status": "new", "resumed": False, "seconds": {}, "error": None})
    return run


def execute(m: Matrix, spec: RunSpec, root: Path, identity: dict, stage_funcs: dict[str, Callable] | None = None,
            clock: Callable[[], float] = time.perf_counter) -> RunOutcome:
    """Run the spec's stages in order, in-process, timing each. A finished run is skipped; an unfinished one gets the
    whole stage list again, flagged `resumed` (real stages skip themselves when their inputs and config are unchanged,
    and an interrupted one finds its paid calls in the run's private cache). A run whose pipeline was copied has `ask`
    as its only stage (the matrix loader sees to it), so what it times and pays for is the questions."""
    run = materialise(m, spec, root, identity)
    path = run.root / "evalrun.json"
    state = json.loads(path.read_text())
    if state["status"] == "done":
        return RunOutcome(spec.name, "skipped", state["seconds"], None)
    if run.cache_dir.is_symlink():
        raise RuntimeError("a run that judges a model call must not share a call cache")
    cfg = Config.model_validate(json.loads((run.root / "config.json").read_text()))
    state.update(status="running", resumed=state["resumed"] or state["status"] != "new",
                 started=state["started"] or _now(), finished=None, error=None)
    _write_json(path, state)
    for stage in spec.stages:
        log.info("%s: %s", spec.name, stage)
        try:
            t0 = clock()
            if stage == "ask":
                from scry.evaluation.questions import run_questions  # Task 5; imported when a span has questions
                run_questions(run, cfg, spec.span.questions)
            else:
                (stage_funcs[stage] if stage_funcs is not None else resolve(stage))(run, cfg)
            elapsed = clock() - t0
        except Exception as e:  # this run stops; the matrix goes on
            state.update(status="failed", error=f"{type(e).__name__}: {e}"[:500])
            _write_json(path, state)
            return RunOutcome(spec.name, "failed", state["seconds"], state["error"])
        state["seconds"][stage] = round(state["seconds"].get(stage, 0.0) + elapsed, 1)
        _write_json(path, state)
    state.update(status="done", finished=_now())
    _write_json(path, state)
    return RunOutcome(spec.name, "done", state["seconds"], None)


def run_matrix(m: Matrix, root: Path, only: str | None = None, stage_funcs: dict[str, Callable] | None = None,
               clock: Callable[[], float] = time.perf_counter, identity: dict | None = None) -> list[RunOutcome]:
    """Every run of the matrix, one after the other (`only`: the run with that name). A failed run does not stop the
    next. Several processes started with `only` may run side by side; their wall times are then not comparable."""
    if identity is None:
        identity = code_identity(Path(__file__).parent)
    return [execute(m, spec, root, identity, stage_funcs, clock) for spec in expand(m) if only is None or spec.name == only]
