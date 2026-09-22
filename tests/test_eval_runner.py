import itertools
import json
import shutil
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from eval_fixtures import QUESTIONS
from eval_fixtures import source_run as _source

from scry.config import Config
from scry.evaluation.matrix import expand, load_matrix
from scry.evaluation.runner import check_copy, execute, materialise, run_matrix
from scry.read import read_config_hash, run_read
from scry.run import Run

IDENTITY = {"git_commit": "abc", "git_dirty": True}


def _matrix(tmp_path: Path, src: Run, stages: str, repeats: int, axis: str = ""):
    (tmp_path / "base.toml").write_text("")
    path = tmp_path / "p9.toml"
    path.write_text(f'phase = "p9"\nsource = "{src.root}"\nbase_config = "{tmp_path / "base.toml"}"\n'
                    f'stages = {stages}\nrepeats = {repeats}\n[spans.smoke]\nframes = "1-2"\n{axis}')
    return load_matrix(path)


def _with_ocr(src: Run) -> Run:
    """The source after a finished `read` with the base config: what every source of a matrix holds."""
    src.boxes.write_bytes(b"".join(b'{"frame": %d, "png": "frames/%05d.png", "engine": {}, "boxes": []}\n' % (n, n) for n in range(4)))
    src.stage_done("read", [src.frames], read_config_hash(Config()), frames=4, boxes=0, dropped_empty=0, seconds=8.0,
                   seconds_per_frame=2.0, engine={})
    return src


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


def test_materialise_imports_the_source_ocr_and_read_skips_itself(tmp_path, monkeypatch):
    src = _with_ocr(_source(tmp_path))
    m = _matrix(tmp_path, src, '["read", "track"]', 1)
    [spec] = expand(m)
    before = _listing(src.root)
    root = tmp_path / "eval"
    run = materialise(m, spec, root, IDENTITY)
    lines = src.boxes.read_bytes().splitlines(keepends=True)
    assert run.boxes.read_bytes() == lines[1] + lines[2]
    assert run.stage_up_to_date("read", [run.frames], read_config_hash(Config()))
    state = json.loads((run.root / "evalrun.json").read_text())
    assert state["ocr_imported_from"] == str(src.root) and state["cold"] is True and state["status"] == "new"
    assert run.cache_dir.is_dir() and not run.cache_dir.is_symlink() and not any(run.cache_dir.iterdir())
    assert _listing(src.root) == before

    def no_engine(cfg):
        raise AssertionError("read ran: an OCR engine was built")

    monkeypatch.setattr("scry.read.get_engine", no_engine)  # the real stage, which must find itself up to date
    tracked = []
    outcome = execute(m, spec, root, IDENTITY, stage_funcs={"read": run_read, "track": lambda run, cfg: tracked.append(run.root.name)},
                      clock=_clock())
    assert (outcome.status, outcome.seconds) == ("done", {"read": 1.5, "track": 1.5})
    assert tracked == ["smoke-r1"]
    assert run.boxes.read_bytes() == lines[1] + lines[2]  # untouched
    state = json.loads((run.root / "evalrun.json").read_text())
    assert state["ocr_imported_from"] == str(src.root) and state["status"] == "done"


def test_read_runs_as_before_when_its_config_differs_or_the_source_was_never_read(tmp_path):
    root = tmp_path / "eval"
    src = _with_ocr(_source(tmp_path))
    m = _matrix(tmp_path, src, '["read"]', 1, '[axis.read.gap]\n"read.gap_ratio" = 0.3\n')
    [spec] = expand(m)
    assert spec.name == "smoke-gap-r1" and spec.overrides == {"read.gap_ratio": 0.3}
    run = materialise(m, spec, root, IDENTITY)
    assert not run.boxes.exists() and "read" not in run.manifest_read()["stages"]
    state = json.loads((run.root / "evalrun.json").read_text())
    assert "ocr_imported_from" not in state and state["cold"] is True
    read_calls = []
    outcome = execute(m, spec, root, IDENTITY, stage_funcs={"read": lambda run, cfg: read_calls.append(cfg.read.gap_ratio)}, clock=_clock())
    assert outcome.status == "done" and read_calls == [0.3]

    never_read = _source(tmp_path / "unread")
    m = _matrix(tmp_path, never_read, '["read"]', 1)
    [spec] = expand(m)
    run = materialise(m, spec, root, IDENTITY)
    assert not run.boxes.exists() and "read" not in run.manifest_read()["stages"]
    assert "ocr_imported_from" not in json.loads((run.root / "evalrun.json").read_text())


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


def _files(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _copying(tmp_path: Path, src: Run, origin: Path):
    """Phase p10: the questions again, without frames, over the pipeline of the finished run `origin`."""
    (tmp_path / "q.md").write_text(QUESTIONS)
    path = tmp_path / "p10.toml"
    path.write_text(f'phase = "p10"\nsource = "{src.root}"\nbase_config = "{tmp_path / "base.toml"}"\nstages = ["ask"]\nrepeats = 1\n'
                    f'[spans.smoke]\nframes = "1-2"\nquestions = "{tmp_path / "q.md"}"\n[axis.ask.indexonly]\n"ask.frames" = false\n'
                    f'[copy]\nsmoke-indexonly-r1 = "{origin}"\n')
    return load_matrix(path)


def test_a_copied_pipeline_is_byte_identical_and_only_the_questions_are_asked(tmp_path, monkeypatch):
    src = _source(tmp_path)
    root = tmp_path / "eval"

    def read(run, cfg):  # the pipeline of the run that is copied: a record, a paid call in its cache, a manifest entry
        (run.root / "boxes.jsonl").write_text("boxes\n")
        (run.cache_dir / "paid.json").write_text("{}")
        run.stage_done("read", [run.frames], "cfg", usage={"input_tokens": 1000})

    [built] = run_matrix(_matrix(tmp_path, src, '["read"]', 1), root, stage_funcs={"read": read}, clock=_clock(), identity=IDENTITY)
    origin = root / "p9" / "smoke-r1"
    assert built.status == "done"
    for name in ("answers.jsonl", "judgments.jsonl", "scorecard.json", "redecode/000001.000.png"):  # what came after its pipeline
        (origin / name).parent.mkdir(exist_ok=True)
        (origin / name).write_text("theirs\n")
    before = _files(origin)

    m = _copying(tmp_path, src, origin)
    [spec] = expand(m)
    run = materialise(m, spec, root, IDENTITY)
    assert run.root == root / "p10" / "smoke-indexonly-r1"
    mine = ("evalrun.json", "config.json")  # the harness's state and the run's config are this run's own
    left_behind = (*mine, "answers.jsonl", "judgments.jsonl", "scorecard.json", "redecode/000001.000.png")
    pipeline = {name: data for name, data in before.items() if name not in left_behind}
    assert {"boxes.jsonl", "manifest.json", "frames.jsonl", "frames/00001.png", "cache/paid.json"} <= set(pipeline)
    assert {name: data for name, data in _files(run.root).items() if name not in mine} == pipeline  # every byte, and nothing else
    assert _files(origin) == before  # nothing is written under the run it copies
    state = json.loads((run.root / "evalrun.json").read_text())
    assert (state["copied_from"], state["cold"], state["status"], state["seconds"]) == (str(origin), False, "new", {})
    assert (state["phase"], state["name"], state["overrides"]) == ("p10", "smoke-indexonly-r1", {"ask.frames": False})
    assert json.loads((run.root / "config.json").read_text())["ask"]["frames"] is False

    seen = []

    def fake_ask(run, cfg, question, client=None):
        seen.append(cfg.ask.frames)
        return SimpleNamespace(text="It ran.", turns=1, tool_calls=[], tool_log=[], usage={"input_tokens": 1}, cost_usd=0.01,
                               model="claude-opus-5", stop="end_turn", prompt="ask-v1+noframes")

    monkeypatch.setattr("scry.ask.ask", fake_ask)
    outcome = execute(m, spec, root, IDENTITY, clock=_clock())
    assert (outcome.status, outcome.seconds) == ("done", {"ask": 1.5})  # no pipeline stage ran; the time is the questions'
    assert seen == [False, False]
    answers = (run.root / "answers.jsonl").read_text()
    assert "theirs" not in answers and answers.count("ask-v1+noframes") == 2  # asked anew, never carried over
    assert {name: data for name, data in _files(run.root).items() if name not in (*mine, "answers.jsonl")} == pipeline
    assert _files(origin) == before
    assert "copied_from" not in json.loads((origin / "evalrun.json").read_text())  # a built run has no such key

    def altered(name: str, file: str, change) -> Path:
        other = tmp_path / name
        shutil.copytree(origin, other)
        data = json.loads((other / file).read_text())
        change(data)
        (other / file).write_text(json.dumps(data))
        return other

    refusals = {"not finished": altered("failed", "evalrun.json", lambda d: d.update(status="failed")),
                "frames": altered("longer", "evalrun.json", lambda d: d["span"].update(frames=[0, 3])),
                r"\[track\]": altered("margin", "config.json", lambda d: d["track"].update(margin=0.25)),
                "evalrun.json": tmp_path / "nowhere"}
    for message, other in refusals.items():  # a copy must not mislabel what it holds; refused before anything is created
        with pytest.raises(ValueError, match=message):
            check_copy(m, replace(spec, copy_from=other))
        with pytest.raises(ValueError, match=message):
            materialise(m, replace(spec, name="smoke-indexonly-r2", copy_from=other), root, IDENTITY)
    assert not (root / "p10" / "smoke-indexonly-r2").exists()
    # [ask] is what such a phase changes, and a config written before a key existed holds that key's default
    older = altered("older", "config.json", lambda d: (d["ask"].update(max_turns=3), d["ask"].pop("frames"), d["ask"].pop("model")))
    assert check_copy(m, replace(spec, copy_from=older))["status"] == "done"
    with pytest.raises(ValueError, match="different spec"):  # the table changed under a run that exists
        materialise(m, replace(spec, copy_from=older), root, IDENTITY)
