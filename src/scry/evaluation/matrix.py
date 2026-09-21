from __future__ import annotations

import copy
import itertools
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

from scry.config import Config
from scry.subset import parse_frames

STAGE_ORDER = ("read", "track", "annotate", "interpret", "summarize", "index", "ask")
REQUIRED_KEYS = ("phase", "source", "stages", "repeats", "spans")
TOP_KEYS = (*REQUIRED_KEYS, "base_config", "axis", "copy")
SPAN_KEYS = ("frames", "ground_truth", "questions")


@dataclass(frozen=True)
class Span:
    name: str
    frames: tuple[int, int]
    ground_truth: Path | None
    questions: Path | None


@dataclass(frozen=True)
class RunSpec:
    phase: str
    name: str
    config_id: str
    span: Span
    values: dict[str, str]  # axis → value name, in axis order
    repeat: int
    overrides: dict[str, object]
    stages: tuple[str, ...]
    copy_from: Path | None = None  # the finished run whose pipeline this run copies instead of building one


@dataclass
class Matrix:
    phase: str
    path: Path
    source: Path
    base_config: Path
    stages: tuple[str, ...]
    repeats: int
    spans: dict[str, Span]
    axes: dict[str, dict[str, dict]]
    copy_from: dict[str, Path] = field(default_factory=dict)  # the [copy] table: run name → the finished run its pipeline is copied from


def _span(name: str, table: dict) -> Span:
    for key in table:
        if key not in SPAN_KEYS:
            raise ValueError(f"unknown key in span {name}: {key}")
    if "frames" not in table:
        raise ValueError(f"span {name} has no frames")
    return Span(name, parse_frames(table["frames"]),
                Path(table["ground_truth"]) if "ground_truth" in table else None,
                Path(table["questions"]) if "questions" in table else None)


def load_matrix(path: Path) -> Matrix:
    """Read `evals/<phase>.toml`. Everything specific to a video or a phase lives in that file; paths are kept as
    written, relative to the working directory. A key the format does not have, a stage that does not exist and a
    config key set by two axes are refused here; a config key that does not exist is refused by `config_for`.

    A `[copy]` table (run name → the directory of a finished run) makes a phase that asks the questions again over
    pipelines that already exist, for a change that touches only `[ask]`: the matrix then has exactly the runs the
    table names, each run's pipeline is copied from its directory instead of being built, and the only stage is
    `ask`, so that a copied pipeline is never rebuilt."""
    path = Path(path)
    with path.open("rb") as f:
        data = tomllib.load(f)
    for key in data:
        if key not in TOP_KEYS:
            raise ValueError(f"unknown key in {path}: {key}")
    for key in REQUIRED_KEYS:
        if key not in data:
            raise ValueError(f"{path} has no {key}")
    for stage in data["stages"]:
        if stage not in STAGE_ORDER:
            raise ValueError(f"unknown stage in {path}: {stage}")
    if data["repeats"] < 1:
        raise ValueError(f"repeats must be at least 1 in {path}")
    axes = data.get("axis", {})
    setters: dict[str, str] = {}  # config key → the axis that sets it
    for axis, values in axes.items():
        for table in values.values():
            for key in table:
                if setters.setdefault(key, axis) != axis:
                    raise ValueError(f"{key} is set by two axes: {setters[key]} and {axis}")
    m = Matrix(phase=data["phase"], path=path, source=Path(data["source"]),
               base_config=Path(data.get("base_config", "scry.toml")),
               stages=tuple(s for s in STAGE_ORDER if s in data["stages"]), repeats=data["repeats"],
               spans={name: _span(name, table) for name, table in data["spans"].items()}, axes=axes,
               copy_from={name: Path(src) for name, src in data.get("copy", {}).items()})
    if m.copy_from:
        if m.stages != ("ask",):
            raise ValueError(f'{path} copies pipelines, which are never rebuilt: stages must be ["ask"]')
        unknown = sorted(set(m.copy_from) - {spec.name for spec in _expand_all(m)})
        if unknown:
            raise ValueError(f"[copy] in {path} names no run of the matrix: {', '.join(unknown)}")
    return m


def expand(m: Matrix) -> list[RunSpec]:
    """Spans in file order × the cartesian product of the axes (file order, the last axis fastest) × repeats. With a
    `[copy]` table: of those, the runs the table names, each with the directory its pipeline is copied from."""
    if not m.copy_from:
        return _expand_all(m)
    return [replace(spec, copy_from=m.copy_from[spec.name]) for spec in _expand_all(m) if spec.name in m.copy_from]


def _expand_all(m: Matrix) -> list[RunSpec]:
    specs = []
    for span in m.spans.values():
        stages = tuple(s for s in STAGE_ORDER if s in m.stages and (s != "ask" or span.questions is not None))
        for combo in itertools.product(*m.axes.values()):
            values = dict(zip(m.axes, combo))
            overrides = {k: v for axis, value in values.items() for k, v in m.axes[axis][value].items()}
            config_id = "-".join([span.name, *combo])
            for repeat in range(1, m.repeats + 1):
                specs.append(RunSpec(m.phase, f"{config_id}-r{repeat}", config_id, span, values, repeat, overrides, stages))
    return specs


def apply_overrides(base: dict, overrides: dict[str, object]) -> dict:
    """A deep copy of `base` with each dotted path set."""
    out = copy.deepcopy(base)
    for key, value in overrides.items():
        *tables, leaf = key.split(".")
        node = out
        for part in tables:
            node = node.setdefault(part, {})
            if not isinstance(node, dict):
                raise ValueError(f"{key}: {part} is not a table")
        node[leaf] = value
    return out


def config_for(m: Matrix, spec: RunSpec) -> Config:
    """The run's effective config: the base file with the spec's overrides, validated. Every config model rejects
    unknown keys, so a typo in the matrix fails here, at expansion, and the harness names no pipeline key."""
    with m.base_config.open("rb") as f:
        base = tomllib.load(f)
    return Config.model_validate(apply_overrides(base, spec.overrides))


def check(m: Matrix) -> list[RunSpec]:
    """Everything that can be refused before a cent is spent: every run's config validates, the source holds decoded
    frames, each span's command list and question file exist and parse, and a pipeline that is copied is a finished
    run built with the run's own config. Returns the expanded runs."""
    specs = expand(m)
    for spec in specs:
        config_for(m, spec)
    if m.copy_from:
        from scry.evaluation.runner import check_copy  # the runner knows what a run directory holds
        for spec in specs:
            check_copy(m, spec)
    if not (m.source / "frames.jsonl").exists() and not (m.source / "stage1.jsonl").exists():
        raise ValueError(f"source {m.source} holds no decoded frames")
    for span in m.spans.values():
        if span.ground_truth is not None:
            from scry.groundtruth import parse_commands
            parse_commands(span.ground_truth.read_text())
        if span.questions is not None:
            from scry.evaluation.questions import parse_questions
            parse_questions(span.questions.read_text())
    return specs
