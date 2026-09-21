import itertools
import json
from dataclasses import replace
from pathlib import Path

import pytest
from eval_fixtures import source_run as _source

from scry.evaluation.matrix import expand, load_matrix
from scry.evaluation.runner import execute, materialise, run_matrix
from scry.run import Run

IDENTITY = {"git_commit": "abc", "git_dirty": True}


def _matrix(tmp_path: Path, src: Run, stages: str, repeats: int):
    (tmp_path / "base.toml").write_text("")
    path = tmp_path / "p9.toml"
    path.write_text(f'phase = "p9"\nsource = "{src.root}"\nbase_config = "{tmp_path / "base.toml"}"\n'
                    f'stages = {stages}\nrepeats = {repeats}\n[spans.smoke]\nframes = "1-2"\n')
    return load_matrix(path)


def _listing(root: Path):
    return sorted((str(p.relative_to(root)), p.stat().st_size if p.is_file() else -1) for p in root.rglob("*"))


def _clock():
    ticks = itertools.count()
    return lambda: next(ticks) * 1.5  # every stage call measures 1.5 s


def test_materialise_is_cold(tmp_path):
    src = _source(tmp_path)
    m = _matrix(tmp_path, src, '["read", "track"]', 1)
    [spec] = expand(m)
    before = _listing(src.root)
    root = tmp_path / "eval"
    run = materialise(m, spec, root, IDENTITY)
    assert run.root == root / "p9" / "smoke-r1"
    assert run.cache_dir.is_dir() and not run.cache_dir.is_symlink() and not any(run.cache_dir.iterdir())
    assert (run.root / "frames/00001.png").exists() and (run.root / "frames/00002.png").exists()
    assert not (run.root / "frames/00000.png").exists()
    state = json.loads((run.root / "evalrun.json").read_text())
    assert state["name"] == "smoke-r1" and state["status"] == "new" and state["cold"] is True
    assert state["code"] == {"git_commit": "abc", "git_dirty": True}
    assert (run.root / "config.json").exists()
    assert _listing(src.root) == before
    with pytest.raises(ValueError):  # the matrix changed under the run
        materialise(m, replace(spec, overrides={"track.margin": 0.25}), root, IDENTITY)
    run.cache_dir.rmdir()
    run.cache_dir.symlink_to(src.cache_dir, target_is_directory=True)
    with pytest.raises(RuntimeError, match="share a call cache"):
        execute(m, spec, root, IDENTITY, stage_funcs={"read": lambda run, cfg: None, "track": lambda run, cfg: None})


def test_failed_run_is_resumed_and_finished_runs_are_skipped(tmp_path):
    src = _source(tmp_path)
    m = _matrix(tmp_path, src, '["read", "track"]', 2)
    root = tmp_path / "eval"
    calls: list[tuple[str, str]] = []
    track_calls = itertools.count(1)

    def read(run, cfg):
        calls.append((run.root.name, "read"))

    def track(run, cfg):
        calls.append((run.root.name, "track"))
        if next(track_calls) == 1:  # its first call only
            raise ValueError("boom")

    funcs = {"read": read, "track": track}
    first = run_matrix(m, root, stage_funcs=funcs, clock=_clock(), identity=IDENTITY)
    assert [(o.name, o.status) for o in first] == [("smoke-r1", "failed"), ("smoke-r2", "done")]
    assert first[0].error == "ValueError: boom" and first[0].seconds == {"read": 1.5}
    assert first[1].error is None and first[1].seconds == {"read": 1.5, "track": 1.5}
    state = json.loads((root / "p9" / "smoke-r1" / "evalrun.json").read_text())
    assert state["status"] == "failed" and state["error"] == "ValueError: boom" and state["resumed"] is False

    calls.clear()
    second = run_matrix(m, root, stage_funcs=funcs, clock=_clock(), identity=IDENTITY)
    assert calls == [("smoke-r1", "read"), ("smoke-r1", "track")]  # the fakes do not skip themselves as real stages do
    assert [(o.name, o.status) for o in second] == [("smoke-r1", "done"), ("smoke-r2", "skipped")]
    state = json.loads((root / "p9" / "smoke-r1" / "evalrun.json").read_text())
    assert state["status"] == "done" and state["resumed"] is True and state["error"] is None
    assert state["seconds"] == {"read": 3.0, "track": 1.5}
    assert state["finished"]
    assert json.loads((root / "p9" / "smoke-r2" / "evalrun.json").read_text())["resumed"] is False
