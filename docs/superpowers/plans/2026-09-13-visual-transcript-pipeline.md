# Visual Transcript Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `vt`, a Python command-line pipeline that turns a silent screen-recording tutorial video into an exact, timestamped, queryable visual transcript (frames → OCR + VLM perception → merged states → line diffs and coalesced transitions → VLM interpretations → step/section hierarchy → SQLite index → question-answering agent), as specified in the design document.

**Architecture:** Nine idempotent stages, each a module under `src/vt/` that reads other stages' JSONL files from a run directory and writes exactly one file of its own (`docs/visual-transcript-pipeline-design.md` §10.7). Stage 1 (decode, change detection, settle, churn, blink tracking) is a pure state machine over grayscale frames so it can be simulated on synthetic sequences. Perception uses Apple Vision through PyObjC and the Anthropic SDK with structured outputs behind a provider interface and an on-disk call cache. Everything downstream of perception is deterministic Python over pydantic records.

**Tech Stack:** Python ≥ 3.12 (3.14.6 here), `uv`; `av` (PyAV) for decode; `numpy` + `scipy.ndimage` for pixels; `pyobjc-framework-Vision`/`Quartz` for OCR; `pillow` for PNG and overlays; `rapidfuzz` for similarity; `anthropic` ≥ 1.5 with `pydantic` 2 for model calls; `sqlite3` FTS5 + `sqlite-vec` for the index; `typer` CLI; `pytest`.

**Spec:** `docs/visual-transcript-pipeline-design.md` (revision 3, commit `eb194ec`). Section numbers below (§) refer to it. Executors read both.

## Global Constraints

- Platform: macOS on Apple Silicon (verified on macOS 26.3); the OCR adapter is the only platform-specific module (§20.8). Python `>=3.12`. Managed with `uv` (`uv sync`, `uv run`).
- **No OpenCV, no system `ffmpeg`, no `difflib` for the op list, no JPEG anywhere** (D14, §11.2, §7.1).
- Every timestamp comes from `frame.pts × time_base`, never from a frame counter or a model (R2; the one exception is the optional Stage 0 outline, snapped on read).
- **No stage writes a file another stage owns** (§10.7). Later signals go in sidecars; loaders merge on read.
- All coordinates are `[x0, y0, x1, y1]` integers in original-frame pixels, origin top-left (§10.5).
- Model default `claude-opus-5`; `output_config.effort` per stage: Stage 2c `low`, Stage 5 `low`, Stage 6 `medium`, agent `high` (§16). `max_tokens` 16000, retried once at 32000 on truncation (§8.3).
- Every model call is cached on disk by SHA-256 of `(stage, model, effort, max_tokens, prompt_version, schema_hash, input_hashes)` (§20.7). Re-running with unchanged inputs makes no API calls.
- Tests are unit tests over synthetic frames, hand-written line lists, and recorded model responses — **no video, no network** (§18.4). The owner has asked for tests to be light: test the pure functions and state machines; do not test CLI glue or provider I/O beyond a fake client. **No integration tests** until the owner hand-creates ground truth.
- Commit after every task, directly to `main` (decision ledger L8). Commit messages end with the attribution block used throughout this session.
- The sample video `assets/create-aks-cluster-tutorial.mp4` (1920×1080, 30 fps, h264, 852.8 s) may be used for manual smoke checks of Stage 1 and OCR; never in tests.

---

## File Structure

```
pyproject.toml                  project metadata, dependencies, [project.scripts] vt = "vt.cli:app", pytest config
uv.lock                         lockfile
.gitignore                      runs/, .venv/, __pycache__/, *.pyc, .pytest_cache/, cache/
README.md                       what this is, how to run, where the design/plan/ledger live
vt.toml                         default configuration (every §16 parameter)
src/vt/__init__.py              version string
src/vt/cli.py                   typer app: run, decode, ocr, overlay, perceive, merge, diff, interpret, hierarchy, index, ask, setup, outline
src/vt/config.py                pydantic Config (+ sub-models), load_config(path), config_hash(config, section)
src/vt/schemas.py               every record type (§10) and every VLM output model (§8.3, §12, §13)
src/vt/jsonl.py                 read_jsonl / write_jsonl / sha256_file / sha256_obj
src/vt/run.py                   Run: directory layout, manifest, stage skip, load_frames, load_transitions, chapter_of, diagnostics
src/vt/decode.py                iter_frames (PyAV), video_info
src/vt/detect.py                change_map, components, trigger, ChurnTracker, BlinkTracker       (§7.2, §7.4, §7.5)
src/vt/settle.py                SettleMachine                                                    (§7.3)
src/vt/stage1.py                run_stage1: decode → machine → PNGs + stage1.jsonl
src/vt/ocr/base.py              OcrEngine protocol, RawLine/RawWord
src/vt/ocr/vision.py            Apple Vision adapter (PyObjC)                                    (§8.1, §20.4)
src/vt/ocr/rapid.py             RapidOCR adapter (optional extra)
src/vt/ocr/__init__.py          get_engine(config)
src/vt/stage2a.py               run_ocr: ocr.jsonl with IDs, in_churn, confusable
src/vt/overlay.py               draw_overlay with label placement; run_overlay                   (§8.2)
src/vt/textdiff.py              norm, similarity, myers, pair_modifies, char_diff, is_clock_change (§9.2, §11.2)
src/vt/providers/base.py        Block builders, VlmProvider protocol, VlmResult
src/vt/providers/cache.py       CallCache (disk)
src/vt/providers/anthropic_.py  AnthropicProvider: parse + retry ladder + refusal + usage        (§20.7)
src/vt/providers/batch.py       Message Batches submission/resume                                (§20.7)
src/vt/prompts/stage2c.py       SYSTEM, VERSION
src/vt/prompts/stage5.py        SYSTEM, VERSION
src/vt/prompts/stage6.py        BOUNDARY_SYSTEM, ELABORATE_SYSTEM, VERSION
src/vt/prompts/agent.py         SYSTEM, VERSION
src/vt/perceive.py              Stage 2c: blocks, call, validate/repair → perception.jsonl       (§8.3)
src/vt/merge.py                 Stage 3: rows, alignment, agreement, layout_conf, focus → frames.jsonl (§9)
src/vt/correspond.py            region correspondence                                            (§11.1)
src/vt/diff.py                  Stage 4: per-pair diffs                                          (§11.2)
src/vt/coalesce.py              Stage 4b: transients, coalescing, trivial, retrospective focus  (§11.3–§11.5, §9.4)
src/vt/interpret.py             Stage 5                                                          (§12)
src/vt/hierarchy.py             Stage 6                                                          (§13)
src/vt/index.py                 Stage 7: SQLite schema, indexing, query builder, RRF search     (§14)
src/vt/agent.py                 answering agent (tool loop)                                      (§14.3)
src/vt/outline.py               Stage 0 (Gemini agentic outline, optional)                      (§6)
tests/conftest.py               synthetic frame renderer, tiny helpers
tests/test_textdiff.py, test_detect.py, test_settle.py, test_overlay.py, test_merge.py, test_correspond.py, test_coalesce.py, test_index.py, test_schemas.py, test_vision.py (darwin only)
```

Interfaces between tasks are stated in each task's **Interfaces** block; the record types in `schemas.py` (Task 1) are the contract every stage shares.

---

### Task 1: Project scaffolding, configuration, schemas, JSONL utilities

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `README.md`, `vt.toml`, `src/vt/__init__.py`, `src/vt/config.py`, `src/vt/schemas.py`, `src/vt/jsonl.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Produces: `vt.config.Config` (pydantic; sub-models `Stage1Config{detect,settle,churn,blink}`, `OcrConfig`, `OverlayConfig`, `ModelConfig`, `MergeConfig`, `DiffConfig`, `HierarchyConfig`, `IndexConfig`, `OutlineConfig`), `load_config(path: Path | None) -> Config`, `config_hash(cfg, *sections) -> str`.
- Produces: every record model in `vt.schemas` (listed in the code below) and `BBox = tuple[int, int, int, int]`.
- Produces: `vt.jsonl.read_jsonl(path, model) -> list[model]`, `write_jsonl(path, records)`, `sha256_file(path) -> str`, `sha256_obj(obj) -> str`.

- [ ] **Step 1: Create the project files**

`pyproject.toml`:

```toml
[project]
name = "vt"
version = "0.1.0"
description = "Visual transcript pipeline for silent screen-recording tutorials"
requires-python = ">=3.12"
dependencies = [
  "numpy>=2.0",
  "scipy>=1.14",
  "av>=14",
  "pillow>=11",
  "rapidfuzz>=3.9",
  "anthropic>=1.5",
  "pydantic>=2.8",
  "sqlite-vec>=0.1.6",
  "typer>=0.12",
  "pyobjc-framework-Vision>=10; sys_platform == 'darwin'",
  "pyobjc-framework-Quartz>=10; sys_platform == 'darwin'",
]

[project.optional-dependencies]
rapid = ["rapidocr-onnxruntime>=1.3"]
embed = ["fastembed>=0.3"]
outline = ["google-genai>=1.0"]

[project.scripts]
vt = "vt.cli:app"

[dependency-groups]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/vt"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

`.gitignore`:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
runs/
cache/
*.egg-info/
.DS_Store
```

`vt.toml` (defaults; every §16 parameter, grouped as the config models below):

```toml
[stage1.detect]
theta_pix = 12
theta_min = 8
theta_comp = 24
theta_count = 100
bar_max_width = 3
bar_min_height = 8
bar_max_height = 30
downsample = 1

[stage1.settle]
still_s = 0.4
max_hold_s = 3.0

[stage1.churn]
window_s = 5.0
rho_on = 0.5
rho_off = 0.2
min_area = 400

[stage1.blink]
max_w = 12
max_h = 32
min_period_s = 0.15
max_period_s = 0.7
confirm_recurrences = 2
confirm_window_s = 3.0
expiry_s = 2.0
iou = 0.5

[ocr]
engine = "vision"
languages = ["en-US"]
language_correction = false
minimum_text_height = 0.0

[overlay]
font_size = 11
font_path = "/System/Library/Fonts/Menlo.ttc"

[model]
provider = "anthropic"
model = "claude-opus-5"
effort_stage2c = "low"
effort_stage5 = "low"
effort_stage6 = "medium"
effort_agent = "high"
max_tokens = 16000
retry_max_tokens = 32000
concurrency = 4
mode = "sync"

[merge]
row_y_tol = 0.5
row_gap_lines = 3.0
align_sim = 0.8
align_short_len = 8
align_short_lev = 1
glyph_max_len = 2

[diff]
modify_sim = 0.6
typed_tolerance = 3
transient_max_s = 2.0
corr_w_text = 0.5
corr_w_iou = 0.3
corr_w_app = 0.1
corr_w_name = 0.1
corr_accept = 0.3

[hierarchy]
window = 2000
overlap = 200
fallback_step_transitions = 20
fallback_section_steps = 8

[index]
embedder = "none"
k = 20
k_filtered = 50
rrf = 60

[outline]
enabled = false
model = "gemini-3.8-flash"
```

`src/vt/__init__.py`:

```python
__version__ = "0.1.0"
```

`src/vt/config.py`:

```python
from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class DetectParams(BaseModel):
    theta_pix: int = 12
    theta_min: int = 8
    theta_comp: int = 24
    theta_count: int = 100
    bar_max_width: int = 3
    bar_min_height: int = 8
    bar_max_height: int = 30
    downsample: Literal[1, 2] = 1


class SettleParams(BaseModel):
    still_s: float = 0.4
    max_hold_s: float = 3.0


class ChurnParams(BaseModel):
    window_s: float = 5.0
    rho_on: float = 0.5
    rho_off: float = 0.2
    min_area: int = 400


class BlinkParams(BaseModel):
    max_w: int = 12
    max_h: int = 32
    min_period_s: float = 0.15
    max_period_s: float = 0.7
    confirm_recurrences: int = 2
    confirm_window_s: float = 3.0
    expiry_s: float = 2.0
    iou: float = 0.5


class Stage1Config(BaseModel):
    detect: DetectParams = DetectParams()
    settle: SettleParams = SettleParams()
    churn: ChurnParams = ChurnParams()
    blink: BlinkParams = BlinkParams()


class OcrConfig(BaseModel):
    engine: Literal["vision", "rapid"] = "vision"
    languages: list[str] = ["en-US"]
    language_correction: bool = False
    minimum_text_height: float = 0.0


class OverlayConfig(BaseModel):
    font_size: int = 11
    font_path: str = "/System/Library/Fonts/Menlo.ttc"


Effort = Literal["low", "medium", "high", "xhigh", "max"]


class ModelConfig(BaseModel):
    provider: Literal["anthropic"] = "anthropic"
    model: str = "claude-opus-5"
    effort_stage2c: Effort = "low"
    effort_stage5: Effort = "low"
    effort_stage6: Effort = "medium"
    effort_agent: Effort = "high"
    max_tokens: int = 16000
    retry_max_tokens: int = 32000
    concurrency: int = 4
    mode: Literal["sync", "batch"] = "sync"


class MergeConfig(BaseModel):
    row_y_tol: float = 0.5
    row_gap_lines: float = 3.0
    align_sim: float = 0.8
    align_short_len: int = 8
    align_short_lev: int = 1
    glyph_max_len: int = 2


class DiffConfig(BaseModel):
    modify_sim: float = 0.6
    typed_tolerance: int = 3
    transient_max_s: float = 2.0
    corr_w_text: float = 0.5
    corr_w_iou: float = 0.3
    corr_w_app: float = 0.1
    corr_w_name: float = 0.1
    corr_accept: float = 0.3


class HierarchyConfig(BaseModel):
    window: int = 2000
    overlap: int = 200
    fallback_step_transitions: int = 20
    fallback_section_steps: int = 8


class IndexConfig(BaseModel):
    embedder: Literal["none", "fastembed"] = "none"
    k: int = 20
    k_filtered: int = 50
    rrf: int = 60


class OutlineConfig(BaseModel):
    enabled: bool = False
    model: str = "gemini-3.8-flash"


class Config(BaseModel):
    stage1: Stage1Config = Stage1Config()
    ocr: OcrConfig = OcrConfig()
    overlay: OverlayConfig = OverlayConfig()
    model: ModelConfig = ModelConfig()
    merge: MergeConfig = MergeConfig()
    diff: DiffConfig = DiffConfig()
    hierarchy: HierarchyConfig = HierarchyConfig()
    index: IndexConfig = IndexConfig()
    outline: OutlineConfig = OutlineConfig()


def load_config(path: Path | None = None) -> Config:
    """Load vt.toml (or the given path); missing file means defaults."""
    if path is None:
        path = Path("vt.toml")
    if not path.exists():
        return Config()
    with path.open("rb") as f:
        return Config.model_validate(tomllib.load(f))


def config_hash(cfg: Config, *sections: str) -> str:
    """SHA-256 of the named top-level sections (all sections if none given)."""
    data = cfg.model_dump()
    if sections:
        data = {s: data[s] for s in sections}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
```

`src/vt/jsonl.py`:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def read_jsonl(path: Path, model: type[T]) -> list[T]:
    if not path.exists():
        return []
    out: list[T] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(model.model_validate_json(line))
    return out


def write_jsonl(path: Path, records: Iterable[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        for r in records:
            f.write(r.model_dump_json(exclude_none=False))
            f.write("\n")
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_obj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()
```

`src/vt/schemas.py` (the shared contract; §10):

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BBox = tuple[int, int, int, int]  # x0, y0, x1, y1 in original-frame pixels; x1/y1 exclusive


# ---------- Stage 1 (§7.6) ----------
class Stage1Record(BaseModel):
    video_id: str
    frame: int
    t_change: float
    t_settled: float
    t_end: float
    settled: bool
    churn_regions: list[BBox] = []
    caret: BBox | None = None
    width: int
    height: int
    sha256: str
    png: str


# ---------- Stage 2a (§8.1) ----------
class RawWord(BaseModel):
    text: str
    bbox: BBox


class OcrLine(BaseModel):
    id: str
    bbox: BBox
    text: str
    conf: float
    words: list[RawWord] | None = None
    in_churn: bool = False
    confusable: bool = False


class OcrFrame(BaseModel):
    frame: int
    engine: str
    settings: dict = {}
    seconds: float = 0.0
    lines: list[OcrLine] = []


# ---------- Stage 2c VLM output (§8.3) ----------
class VlmRegion(BaseModel):
    id: str = Field(description="Region id you assign: r1, r2, … unique in this frame.")
    kind: Literal["window", "pane", "popup"] = Field(description="window = top-level application window; pane = an area inside a window; popup = menu, dialog, tooltip, toast.")
    name: str = Field(description="Short human name for the region, e.g. 'Windows Terminal — pwsh', 'left navigation', 'Save dialog'.")
    app: str = Field(description="Application the region belongs to, e.g. 'Windows Terminal', 'Browser', 'VS Code', 'Notepad'.")
    parent: str | None = Field(description="Id of the enclosing region, or null for a top-level window.")
    conf: float = Field(description="Your 0-1 confidence that this region exists as described and its marks are grouped correctly.")
    occludes: list[str] = Field(default_factory=list, description="Ids of regions this region visually covers, in whole or in part.")
    rows: list[list[str]] = Field(default_factory=list, description="The region's visual lines in reading order. Each row lists the mark numbers (as 'l7') that sit on that one visual line, left to right; [] for a line the boxes missed. Every mark appears in exactly one row of exactly one region, or in unassigned_line_ids.")
    vlm_lines: list[str] = Field(default_factory=list, description="Verbatim text of each row, one entry per row, same order and length as rows. Transcribe from the clean image. Preserve case, punctuation, whitespace and symbols; never correct, complete or normalize code, commands, paths or identifiers; use ? for a character you cannot resolve; do not transcribe icons.")


class VlmPerception(BaseModel):
    regions: list[VlmRegion]
    focused_region: str | None = Field(description="Id of the window that has keyboard focus, or null if unclear.")
    focused_conf: float = Field(description="0-1 confidence in focused_region.")
    focused_cues: list[str] = Field(default_factory=list, description="Visual cues used: title bar highlight, caret visible, dialog modality, …")
    description: str = Field(description="Anything the rows cannot express: selections, highlights, toggles, icons, diagram relationships, dialogs, animating regions.")
    unassigned_line_ids: list[str] = Field(default_factory=list, description="Marks that belong to no region.")


class PerceptionRecord(BaseModel):
    frame: int
    model: str
    prompt_version: str
    output: VlmPerception | None
    error: str | None = None
    usage: dict = {}
    repairs: int = 0
    label_clashes: int = 0


# ---------- Stage 3 merged state (§10.1) ----------
class Line(BaseModel):
    id: str
    marks: list[str] = []
    bbox: BBox | None
    ocr: str | None
    ocr_conf: float | None
    vlm: str | None
    agree: bool | None
    in_churn: bool | None
    ocr_glyph_stripped: str | None = None
    confusable: bool = False
    row_rejected: bool = False

    @property
    def fused(self) -> str:
        if self.agree and self.vlm is not None and self.ocr_glyph_stripped is not None:
            return self.vlm
        if self.agree and self.ocr is not None:
            return self.ocr
        if self.ocr is None:
            return self.vlm or ""
        return self.ocr

    @property
    def uncertain(self) -> bool:
        return not self.agree and self.ocr is not None and self.vlm is not None


class Region(BaseModel):
    id: str
    kind: str
    name: str
    app: str
    parent: str | None
    bbox: BBox | None
    conf: float
    layout_conf: float
    occludes: list[str] = []
    lines: list[Line] = []


class FrameRecord(BaseModel):
    video_id: str
    frame: int
    t_change: float
    t_settled: float
    t_end: float
    settled: bool
    png: str
    overlay: str | None
    sha256: str
    width: int
    height: int
    churn_regions: list[BBox] = []
    caret: BBox | None = None
    focused_region: str | None = None
    focused_conf: float | None = None
    focused_signals: list[str] = []
    description: str = ""
    regions: list[Region] = []
    unassigned_lines: list[Line] = []
    grouping_repairs: int = 0
    rows_rejected: int = 0
    label_clashes: int = 0
    vlm_model: str | None = None
    prompt_version: str | None = None
    error: str | None = None

    def region(self, rid: str) -> Region | None:
        return next((r for r in self.regions if r.id == rid), None)

    def line_ids(self) -> set[str]:
        ids = {ln.id for r in self.regions for ln in r.lines}
        ids |= {ln.id for ln in self.unassigned_lines}
        return ids


# ---------- Stage 4 (§10.2) ----------
class DiffOp(BaseModel):
    op: Literal["insert", "delete", "modify"]
    old: str | None = None
    new: str | None = None
    old_index: int | None = None
    new_index: int | None = None
    char_diff: list[list[str]] | None = None
    y: int | None = None
    uncertain: bool = False
    clock: bool = False
    in_churn: bool = False


class RegionDiff(BaseModel):
    from_region: str | None
    ops: list[DiffOp] = []


class Event(BaseModel):
    type: Literal["typed", "output_appended", "appeared", "disappeared"]
    region: str
    text: str | None = None
    line: str | None = None
    lines: int | None = None
    frames: tuple[int, int]


class Correspondence(BaseModel):
    matched: list[tuple[str, str, float]] = []
    appeared: list[str] = []
    disappeared: list[str] = []


class TransientInfo(BaseModel):
    frame: int
    region: str
    name: str
    hold_s: float


class Transition(BaseModel):
    id: str
    from_frame: int
    to_frame: int
    intermediate_frames: list[int] = []
    t: tuple[float, float]
    kind: Literal["single", "coalesced", "transient_merged", "unsettled", "trivial"]
    regions: Correspondence = Correspondence()
    computed_diff: dict[str, RegionDiff] = {}
    events: list[Event] = []
    transient: TransientInfo | None = None


class FocusRecord(BaseModel):
    frame: int
    focused_region: str | None
    focused_conf: float | None
    focused_signals: list[str]


# ---------- Stage 5 (§12) ----------
class VlmRefs(BaseModel):
    lines: list[str] = Field(default_factory=list, description="Line references your statements rest on, as '<frame>:<line_id>' using the frame numbers given, e.g. '16:l3'.")


class VlmInterpretation(BaseModel):
    action: str = Field(description="The single user action that best explains the change (typed, clicked, selected, navigated, pressed a key). If none is evident, say so.")
    result: str = Field(description="What visibly changed as a consequence, including non-textual changes visible in the images.")
    description: str = Field(description="Anything else visible and relevant.")
    confidence: float = Field(description="0-1 confidence in action and result.")
    refs: VlmRefs = Field(default_factory=VlmRefs)


class Interpretation(BaseModel):
    id: str
    action: str | None = None
    result: str | None = None
    description: str | None = None
    confidence: float | None = None
    refs: VlmRefs = VlmRefs()
    invalid_refs: int = 0
    model: str | None = None
    prompt_version: str | None = None
    error: str | None = None


# ---------- Stage 6 (§10.3, §13) ----------
class SegmentStart(BaseModel):
    start_id: str = Field(description="Id of the first item of a new segment, exactly as listed.")
    label: str = Field(description="Short label for the segment that starts here.")


class VlmBoundaries(BaseModel):
    segments: list[SegmentStart]


class VlmElaboration(BaseModel):
    label: str = Field(description="Short label for this segment.")
    description: str = Field(description="Description for a reader who will follow it. Every sentence carries the child ids it rests on in brackets, e.g. [T13]. Quote commands exactly.")
    refs: list[str] = Field(default_factory=list, description="Every child id cited in description.")


class HierNode(BaseModel):
    id: str
    level: Literal["step", "section", "video"]
    children: tuple[str, str]
    frames: tuple[int, int]
    t: tuple[float, float]
    label: str
    description: str
    refs: list[str] = []
    segmentation_conf: Literal["high", "low"] = "high"


# ---------- Stage 0 (§10.4) ----------
class OutlineChapter(BaseModel):
    id: str
    start_s: float
    end_s: float
    title: str
    gist: str
```

`README.md`:

```markdown
# agentic-escort — visual transcript pipeline

`vt` turns a silent screen-recording tutorial (terminal, editor, browser portal) into an exact,
timestamped, queryable "visual transcript": every distinct screen state with its text and layout,
every change between states with what the user did, a step/section hierarchy, and a searchable index.

- Design: `docs/visual-transcript-pipeline-design.md` (revision 3)
- Implementation plan: `docs/superpowers/plans/2026-09-13-visual-transcript-pipeline.md`
- Decisions made without the owner present: `docs/decision-ledger.md`
- Design reviews: `docs/reviews/`

## Setup (macOS, Apple Silicon)

    uv sync
    uv run vt setup            # checks Vision OCR, FTS5, credentials

Model calls use the Anthropic SDK; credentials come from `ANTHROPIC_API_KEY` or `ant auth login`.

## Run

    uv run vt run assets/create-aks-cluster-tutorial.mp4 --out runs/aks
    uv run vt ask runs/aks "what command created the cluster?"

Each stage can be run alone (`vt decode|ocr|overlay|perceive|merge|diff|interpret|hierarchy|index <run-dir>`);
every stage is idempotent and skips itself when its inputs and configuration are unchanged.

## Tests

    uv run pytest
```

- [ ] **Step 2: Write the schema round-trip test**

`tests/test_schemas.py`:

```python
from pathlib import Path

from vt.config import Config, config_hash, load_config
from vt.jsonl import read_jsonl, write_jsonl
from vt.schemas import FrameRecord, Line, Region, Transition


def test_config_defaults_and_hash_are_stable(tmp_path: Path):
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.stage1.detect.theta_comp == 24
    assert config_hash(cfg, "stage1") == config_hash(Config(), "stage1")
    assert config_hash(cfg, "stage1") != config_hash(cfg, "merge")


def test_frame_record_roundtrip(tmp_path: Path):
    line = Line(id="l3", marks=["l3"], bbox=(12, 40, 300, 58), ocr="git status", ocr_conf=1.0,
                vlm="git status", agree=True, in_churn=False)
    region = Region(id="r1", kind="window", name="Terminal", app="Windows Terminal", parent=None,
                    bbox=(12, 40, 640, 300), conf=0.95, layout_conf=0.9, lines=[line])
    rec = FrameRecord(video_id="v", frame=12, t_change=47.3, t_settled=47.72, t_end=52.1, settled=True,
                      png="frames/00012.png", overlay=None, sha256="x", width=1920, height=1080, regions=[region])
    write_jsonl(tmp_path / "frames.jsonl", [rec])
    back = read_jsonl(tmp_path / "frames.jsonl", FrameRecord)
    assert back == [rec]
    assert back[0].regions[0].lines[0].fused == "git status"
    assert back[0].line_ids() == {"l3"}


def test_line_fused_prefers_stripped_reading():
    line = Line(id="l1", marks=["l1"], bbox=(0, 0, 1, 1), ocr="P Search", ocr_conf=1.0, vlm="Search",
                agree=True, in_churn=False, ocr_glyph_stripped="P")
    assert line.fused == "Search"
    unc = Line(id="l2", marks=["l2"], bbox=(0, 0, 1, 1), ocr="maln", ocr_conf=1.0, vlm="main", agree=False, in_churn=False)
    assert unc.fused == "maln" and unc.uncertain
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv sync && uv run pytest tests/test_schemas.py -v`
Expected: FAIL (module `vt.config` not found) until the files from Step 1 exist; after creating them, PASS.

- [ ] **Step 4: Create the files from Step 1, run the tests, verify they pass**

Run: `uv run pytest tests/test_schemas.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock .gitignore README.md vt.toml src/vt tests/test_schemas.py
git commit -m "feat: project scaffolding, configuration, record schemas"
```

---

### Task 2: Text utilities — normalization, similarity, Myers diff, modify pairing, char diff, clock detection

**Files:**
- Create: `src/vt/textdiff.py`
- Test: `tests/test_textdiff.py`

**Interfaces:**
- Produces: `norm(s: str) -> str`; `similarity(a, b) -> float` (rapidfuzz normalized Levenshtein on `norm`); `levenshtein(a, b) -> int`; `myers(a: Sequence, b: Sequence) -> list[tuple[str, int, int]]` returning runs `("equal"|"insert"|"delete", i, j)` per element; `line_ops(prev: list[str], cur: list[str]) -> list[dict]` raw insert/delete ops with indices; `pair_modifies(ops, prev_y, cur_y, heights, sim_threshold) -> list[DiffOp]`; `char_diff(a, b) -> list[list[str]]` runs `[op, text]`; `is_clock_change(a, b) -> bool`; `lcp_len(a, b) -> int`.

- [ ] **Step 1: Write the failing tests**

`tests/test_textdiff.py`:

```python
from vt.schemas import DiffOp
from vt.textdiff import char_diff, is_clock_change, lcp_len, line_ops, myers, norm, pair_modifies, similarity


def test_norm_collapses_whitespace_and_quotes_but_keeps_case():
    assert norm("  git   status ") == "git status"
    assert norm("say “hi” and ‘bye’") == 'say "hi" and \'bye\''
    assert norm("MyCluster") == "MyCluster"


def test_similarity_short_lines():
    assert similarity("ls", "1s") == 0.5
    assert similarity("git status", "git status") == 1.0


def test_myers_minimal_script():
    a = ["a", "b", "c", "d"]
    b = ["a", "c", "d", "e"]
    runs = myers(a, b)
    ops = [r[0] for r in runs]
    assert ops == ["equal", "delete", "equal", "equal", "insert"]
    assert runs[1] == ("delete", 1, 1)
    assert runs[-1] == ("insert", 4, 3)


def test_line_ops_scroll_is_equal_plus_inserts():
    prev = ["l1", "l2", "l3"]
    cur = ["l2", "l3", "l4", "l5"]
    ops = line_ops(prev, cur)
    assert [(o["op"], o.get("old_index"), o.get("new_index")) for o in ops] == [
        ("delete", 0, None), ("insert", None, 2), ("insert", None, 3)]


def test_pair_modifies_by_y_overlap():
    ops = line_ops(["PS> gi"], ["PS> git status"])
    paired = pair_modifies(ops, prev_y=[41], cur_y=[41], line_h=18, sim_threshold=0.6)
    assert len(paired) == 1 and paired[0].op == "modify"
    assert paired[0].old == "PS> gi" and paired[0].new == "PS> git status"
    assert paired[0].char_diff == [["=", "PS> gi"], ["+", "t status"]]
    assert paired[0].y == 41


def test_pair_modifies_keeps_unrelated_lines_apart():
    ops = line_ops(["alpha"], ["zzzzz"])
    paired = pair_modifies(ops, prev_y=[10], cur_y=[400], line_h=18, sim_threshold=0.6)
    assert [o.op for o in paired] == ["delete", "insert"]


def test_char_diff_runs():
    assert char_diff("git stauts", "git status") == [["=", "git sta"], ["-", "u"], ["=", "t"], ["+", "u"], ["=", "s"]]


def test_clock_change():
    assert is_clock_change("Tue 14:02", "Tue 14:03")
    assert is_clock_change("14:02:59 PM", "14:03:00 PM")
    assert not is_clock_change("14:02 build ok", "14:03 build failed")
    assert not is_clock_change("a", "b")


def test_lcp():
    assert lcp_len("PS> git st", "PS> git status") == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_textdiff.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.textdiff`.

- [ ] **Step 3: Write the implementation**

`src/vt/textdiff.py`:

```python
from __future__ import annotations

import re
from typing import Sequence

from rapidfuzz.distance import Levenshtein

from vt.schemas import DiffOp

_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})
_CLOCK = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?(?: ?[AP]M)?")


def norm(s: str) -> str:
    return " ".join(s.translate(_QUOTES).split())


def similarity(a: str, b: str) -> float:
    return float(Levenshtein.normalized_similarity(norm(a), norm(b)))


def levenshtein(a: str, b: str) -> int:
    return int(Levenshtein.distance(norm(a), norm(b)))


def lcp_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def myers(a: Sequence, b: Sequence) -> list[tuple[str, int, int]]:
    """Myers O(ND) diff. Returns per-element runs ('equal'|'insert'|'delete', i, j):
    for equal/delete, i indexes a; for insert, j indexes b (i is the insertion point in a)."""
    n, m = len(a), len(b)
    max_d = n + m
    v = {1: 0}
    trace: list[dict[int, int]] = []
    for d in range(max_d + 1):
        trace.append(dict(v))
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
                x = v.get(k + 1, 0)
            else:
                x = v.get(k - 1, 0) + 1
            y = x - k
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            v[k] = x
            if x >= n and y >= m:
                return _backtrack(trace, a, b)
    return _backtrack(trace, a, b)


def _backtrack(trace, a, b) -> list[tuple[str, int, int]]:
    x, y = len(a), len(b)
    ops: list[tuple[str, int, int]] = []
    for d in range(len(trace) - 1, -1, -1):
        v = trace[d]
        k = x - y
        if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
            prev_k = k + 1
        else:
            prev_k = k - 1
        prev_x = v.get(prev_k, 0)
        prev_y = prev_x - prev_k
        while x > prev_x and y > prev_y:
            x -= 1
            y -= 1
            ops.append(("equal", x, y))
        if d > 0:
            if x == prev_x:
                y -= 1
                ops.append(("insert", x, y))
            else:
                x -= 1
                ops.append(("delete", x, y))
    ops.reverse()
    return ops


def line_ops(prev: list[str], cur: list[str]) -> list[dict]:
    out: list[dict] = []
    for op, i, j in myers(prev, cur):
        if op == "delete":
            out.append({"op": "delete", "old": prev[i], "old_index": i})
        elif op == "insert":
            out.append({"op": "insert", "new": cur[j], "new_index": j})
    return out


def char_diff(a: str, b: str) -> list[list[str]]:
    runs: list[list[str]] = []
    for op, i, j in myers(list(a), list(b)):
        sym = {"equal": "=", "insert": "+", "delete": "-"}[op]
        ch = b[j] if op == "insert" else a[i]
        if runs and runs[-1][0] == sym:
            runs[-1][1] += ch
        else:
            runs.append([sym, ch])
    return runs


def pair_modifies(ops: list[dict], prev_y: list[int], cur_y: list[int], line_h: float, sim_threshold: float) -> list[DiffOp]:
    """Pair adjacent (delete a, insert b) into modify(a→b) when they overlap vertically or are similar."""
    out: list[DiffOp] = []
    i = 0
    while i < len(ops):
        o = ops[i]
        nxt = ops[i + 1] if i + 1 < len(ops) else None
        if o["op"] == "delete" and nxt is not None and nxt["op"] == "insert":
            ya, yb = prev_y[o["old_index"]], cur_y[nxt["new_index"]]
            if abs(ya - yb) < 0.5 * line_h or similarity(o["old"], nxt["new"]) >= sim_threshold:
                out.append(DiffOp(op="modify", old=o["old"], new=nxt["new"], old_index=o["old_index"],
                                  new_index=nxt["new_index"], char_diff=char_diff(o["old"], nxt["new"]), y=yb,
                                  clock=is_clock_change(o["old"], nxt["new"])))
                i += 2
                continue
        if o["op"] == "delete":
            out.append(DiffOp(op="delete", old=o["old"], old_index=o["old_index"], y=prev_y[o["old_index"]]))
        else:
            out.append(DiffOp(op="insert", new=o["new"], new_index=o["new_index"], y=cur_y[o["new_index"]]))
        i += 1
    return out


def is_clock_change(a: str, b: str) -> bool:
    """True when a and b differ only inside a clock-like token at the same position."""
    if a == b:
        return False
    ma, mb = list(_CLOCK.finditer(a)), list(_CLOCK.finditer(b))
    if not ma or len(ma) != len(mb):
        return False
    stripped_a = _CLOCK.sub("\x00", a)
    stripped_b = _CLOCK.sub("\x00", b)
    return stripped_a == stripped_b
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_textdiff.py -v`
Expected: 9 passed. If `test_myers_minimal_script` fails on the exact run order, print `myers(a, b)` and fix the backtrack (the expected script is the unique minimal one for that input: delete `b`, insert `e`).

- [ ] **Step 5: Commit**

```bash
git add src/vt/textdiff.py tests/test_textdiff.py
git commit -m "feat: text normalization, Myers diff, modify pairing, clock detection"
```

---

### Task 3: Decode (PyAV)

**Files:**
- Create: `src/vt/decode.py`
- Test: `tests/test_decode.py`, `tests/conftest.py`

**Interfaces:**
- Produces: `VideoInfo(width, height, fps, duration, codec)`; `video_info(path) -> VideoInfo`; `DecodedFrame(index, t, gray, frame)`; `iter_frames(path, downsample=1) -> Iterator[DecodedFrame]` where `gray` is `uint8` at detection resolution and `frame` is the full-resolution `av.VideoFrame`.
- `tests/conftest.py` produces `make_video(path, frames: list[np.ndarray], fps)` used by this and later tests.

- [ ] **Step 1: Write the conftest helper and the failing test**

`tests/conftest.py`:

```python
from pathlib import Path

import av
import numpy as np
import pytest


def make_video(path: Path, frames: list[np.ndarray], fps: int = 30) -> Path:
    """Encode grayscale uint8 frames (H, W) into an mp4 with the mpeg4 codec (always available in PyAV)."""
    h, w = frames[0].shape
    with av.open(str(path), mode="w") as c:
        s = c.add_stream("mpeg4", rate=fps)
        s.width, s.height, s.pix_fmt = w, h, "yuv420p"
        for g in frames:
            rgb = np.stack([g, g, g], axis=-1)
            fr = av.VideoFrame.from_ndarray(rgb, format="rgb24")
            for pkt in s.encode(fr):
                c.mux(pkt)
        for pkt in s.encode():
            c.mux(pkt)
    return path


@pytest.fixture
def video_factory(tmp_path: Path):
    def _make(frames, fps=30, name="v.mp4"):
        return make_video(tmp_path / name, frames, fps)
    return _make
```

`tests/test_decode.py`:

```python
import numpy as np

from vt.decode import iter_frames, video_info


def test_iter_frames_times_and_shapes(video_factory):
    frames = [np.full((64, 96), 20 + i, dtype=np.uint8) for i in range(12)]
    path = video_factory(frames, fps=30)
    info = video_info(path)
    assert (info.width, info.height) == (96, 64)
    assert abs(info.fps - 30) < 0.01
    assert 0.35 <= info.duration <= 0.45
    decoded = list(iter_frames(path))
    assert len(decoded) == 12
    assert decoded[0].t == 0.0
    assert all(abs((decoded[i + 1].t - decoded[i].t) - 1 / 30) < 1e-3 for i in range(11))
    assert decoded[0].gray.shape == (64, 96) and decoded[0].gray.dtype == np.uint8
    half = list(iter_frames(path, downsample=2))
    assert half[0].gray.shape == (32, 48)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_decode.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.decode`.

- [ ] **Step 3: Write the implementation**

`src/vt/decode.py`:

```python
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import av
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: float
    codec: str


@dataclass
class DecodedFrame:
    index: int
    t: float
    gray: np.ndarray
    frame: av.VideoFrame


def video_info(path: Path) -> VideoInfo:
    with av.open(str(path)) as c:
        s = c.streams.video[0]
        fps = float(s.average_rate or s.guessed_rate or 30)
        if c.duration:
            duration = float(c.duration * av.time_base)
        elif s.duration:
            duration = float(s.duration * s.time_base)
        else:
            duration = 0.0
        return VideoInfo(s.width, s.height, fps, duration, s.codec_context.name)


def iter_frames(path: Path, downsample: int = 1) -> Iterator[DecodedFrame]:
    with av.open(str(path)) as c:
        s = c.streams.video[0]
        s.thread_type = "AUTO"
        tb = s.time_base
        fps = float(s.average_rate or 30)
        prev_t: float | None = None
        for i, fr in enumerate(c.decode(s)):
            if fr.pts is not None:
                t = float(fr.pts * tb)
            elif fr.time is not None:
                t = float(fr.time)
            else:
                t = (prev_t + 1.0 / fps) if prev_t is not None else 0.0
                log.warning("frame %d has no pts; using %.4f", i, t)
            if downsample == 1:
                gray = fr.to_ndarray(format="gray")
            else:
                gray = fr.reformat(width=fr.width // downsample, height=fr.height // downsample, format="gray").to_ndarray()
            yield DecodedFrame(i, t, gray, fr)
            prev_t = t
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_decode.py -v`
Expected: 1 passed. (If the mpeg4 encoder reorders or drops the last frame, relax the count to `>= 11`; the timing assertion is the one that matters.)

- [ ] **Step 5: Commit**

```bash
git add src/vt/decode.py tests/conftest.py tests/test_decode.py
git commit -m "feat: PyAV decode with exact presentation timestamps"
```

---

### Task 4: Change detection, churn tracker, blink tracker (§7.2, §7.4, §7.5)

**Files:**
- Create: `src/vt/detect.py`
- Test: `tests/test_detect.py`

**Interfaces:**
- Produces: `Component(area, bbox)`; `scale_params(detect, churn, blink, downsample) -> (DetectParams, ChurnParams, BlinkParams)`; `change_map(prev, cur, theta_pix) -> bool ndarray`; `components(changed, theta_min) -> list[Component]` (tight bboxes of changed pixels, exclusive x1/y1); `is_bar(c, p) -> bool`; `trigger(comps, p) -> bool`; `iou(a, b) -> float`; `ChurnTracker(shape, fps, p)` with `.update(changed, frame_index, t) -> ChurnUpdate(regions, deactivated, t_last_change)` and `.excludes(c) -> bool` and `.active -> bool`; `BlinkTracker(p)` with `.update(comps, t) -> BlinkUpdate(excluded: set[int], newly_confirmed: list[Candidate])`, `.is_blinker_bbox(bbox) -> bool`, `.caret_for_interval(t0, t1) -> BBox | None`.

- [ ] **Step 1: Write the failing tests**

`tests/test_detect.py`:

```python
import numpy as np

from vt.config import BlinkParams, ChurnParams, DetectParams
from vt.detect import BlinkTracker, ChurnTracker, Component, change_map, components, is_bar, trigger


def glyph(img, x, y, w=6, h=10, v=255):
    img[y:y + h, x:x + w] = v


def test_thin_strokes_survive_and_noise_does_not():
    p = DetectParams()
    prev = np.zeros((60, 160), np.uint8)
    cur = prev.copy()
    # a 1-px-wide 'l' glyph: 1x10 = 10 changed px, would vanish under a 3x3 opening
    cur[20:30, 40:41] = 255
    comps = components(change_map(prev, cur, p.theta_pix), p.theta_min)
    assert len(comps) == 1 and comps[0].area == 10 and comps[0].bbox == (40, 20, 41, 30)
    # scattered codec noise: 6 isolated pixels
    noisy = prev.copy()
    for x in (5, 30, 55, 80, 105, 130):
        noisy[10, x] = 40
    assert components(change_map(prev, noisy, p.theta_pix), p.theta_min) == []


def test_dilation_merges_glyph_strokes_into_one_component():
    p = DetectParams()
    prev = np.zeros((60, 160), np.uint8)
    cur = prev.copy()
    cur[20:30, 40:41] = 255  # left stem
    cur[20:21, 41:46] = 255  # top bar (touching)
    cur[20:30, 47:48] = 255  # a second stem 1 px away from the bar: dilation bridges the gap
    comps = components(change_map(prev, cur, p.theta_pix), p.theta_min)
    assert len(comps) == 1


def test_bar_caret_is_excluded_by_shape_but_glyph_triggers():
    p = DetectParams()
    prev = np.zeros((60, 160), np.uint8)
    caret = prev.copy()
    caret[20:38, 50:52] = 255  # 2x18 bar caret
    comps = components(change_map(prev, caret, p.theta_pix), p.theta_min)
    assert len(comps) == 1 and is_bar(comps[0], p)
    assert not trigger([c for c in comps if not is_bar(c, p)], p)
    g = prev.copy()
    glyph(g, 50, 20)  # 6x10 = 60 px lowercase-sized glyph
    comps = components(change_map(prev, g, p.theta_pix), p.theta_min)
    assert trigger(comps, p)


def test_churn_activates_on_sustained_change_and_deactivates_after_it_stops():
    fps = 30
    cp = ChurnParams(window_s=1.0, rho_on=0.5, rho_off=0.2, min_area=100)
    tr = ChurnTracker((60, 160), fps, cp)
    rng = np.random.default_rng(0)
    deactivated_at = None
    for i in range(150):
        changed = np.zeros((60, 160), bool)
        if i < 90:  # a 20x20 region flickers every frame for 3 s
            changed[10:30, 100:120] = rng.random((20, 20)) > 0.3
        upd = tr.update(changed, i, i / fps)
        if i == 60:
            assert upd.regions and tr.active
            x0, y0, x1, y1 = upd.regions[0]
            assert x0 <= 100 and y0 <= 10 and x1 >= 120 and y1 >= 30
            assert tr.excludes(Component(50, (105, 15, 110, 20)))
            assert not tr.excludes(Component(50, (5, 5, 10, 10)))
        if upd.deactivated and deactivated_at is None:
            deactivated_at = i
            assert upd.t_last_change is not None and abs(upd.t_last_change - 89 / fps) < 0.05
    assert deactivated_at is not None and 90 < deactivated_at < 130
    assert not tr.active


def test_churn_does_not_activate_on_a_single_large_change_at_startup():
    tr = ChurnTracker((60, 160), 30, ChurnParams(window_s=1.0, min_area=100))
    changed = np.zeros((60, 160), bool)
    changed[:, :] = True
    upd = tr.update(changed, 0, 0.0)
    assert upd.regions == []


def test_blink_tracker_confirms_periodic_component_and_expires():
    bp = BlinkParams()
    bt = BlinkTracker(bp)
    box = (50, 20, 58, 32)  # 8x12 block cursor
    confirmed_at = None
    for i in range(120):
        t = i / 30
        comps = [Component(96, box)] if i % 15 == 0 else []  # toggles every 0.5 s
        upd = bt.update(comps, t)
        if comps and upd.excluded and confirmed_at is None:
            confirmed_at = t
    assert confirmed_at == 1.0  # third toggle: 2 recurrences after the first
    assert bt.is_blinker_bbox((51, 21, 58, 32))
    assert bt.caret_for_interval(0.9, 1.6) == box
    for i in range(120, 220):  # no more toggles: expires after 2 s
        bt.update([], i / 30)
    assert not bt.is_blinker_bbox(box)


def test_blink_tracker_ignores_large_components():
    bt = BlinkTracker(BlinkParams())
    for i in range(0, 90, 15):
        upd = bt.update([Component(500, (0, 0, 40, 40))], i / 30)
        assert upd.excluded == set()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_detect.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.detect`.

- [ ] **Step 3: Write the implementation**

`src/vt/detect.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from vt.config import BlinkParams, ChurnParams, DetectParams
from vt.schemas import BBox

_S8 = np.ones((3, 3), dtype=bool)


@dataclass(frozen=True)
class Component:
    area: int          # changed pixels before dilation
    bbox: BBox         # tight bbox of the changed pixels; x1/y1 exclusive


def scale_params(d: DetectParams, c: ChurnParams, b: BlinkParams, downsample: int) -> tuple[DetectParams, ChurnParams, BlinkParams]:
    """§16 half-resolution column: areas ×0.4, linear sizes ×0.5."""
    if downsample == 1:
        return d, c, b
    a = 0.4
    d2 = d.model_copy(update=dict(theta_min=max(2, round(d.theta_min * a)), theta_comp=round(d.theta_comp * a),
                                  theta_count=round(d.theta_count * a), bar_max_width=max(1, d.bar_max_width // 2 + 1),
                                  bar_min_height=d.bar_min_height // 2, bar_max_height=d.bar_max_height // 2))
    c2 = c.model_copy(update=dict(min_area=round(c.min_area * a)))
    b2 = b.model_copy(update=dict(max_w=b.max_w // 2, max_h=b.max_h // 2))
    return d2, c2, b2


def change_map(prev: np.ndarray, cur: np.ndarray, theta_pix: int) -> np.ndarray:
    return np.abs(cur.astype(np.int16) - prev.astype(np.int16)) > theta_pix


def components(changed: np.ndarray, theta_min: int) -> list[Component]:
    if int(changed.sum()) < theta_min:
        return []
    blobs = ndimage.binary_dilation(changed, structure=_S8)
    labels, n = ndimage.label(blobs, structure=_S8)
    if n == 0:
        return []
    areas = np.bincount(labels[changed], minlength=n + 1)
    tight = np.where(changed, labels, 0)
    objs = ndimage.find_objects(tight, max_label=n)
    out: list[Component] = []
    for lab in range(1, n + 1):
        a = int(areas[lab])
        sl = objs[lab - 1]
        if a < theta_min or sl is None:
            continue
        ys, xs = sl
        out.append(Component(a, (int(xs.start), int(ys.start), int(xs.stop), int(ys.stop))))
    return out


def is_bar(c: Component, p: DetectParams) -> bool:
    w = c.bbox[2] - c.bbox[0]
    h = c.bbox[3] - c.bbox[1]
    return w <= p.bar_max_width and p.bar_min_height <= h <= p.bar_max_height


def trigger(comps: list[Component], p: DetectParams) -> bool:
    if not comps:
        return False
    return any(c.area >= p.theta_comp for c in comps) or sum(c.area for c in comps) >= p.theta_count


def iou(a: BBox, b: BBox) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    if inter == 0:
        return 0.0
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua


@dataclass
class ChurnUpdate:
    regions: list[BBox]
    deactivated: bool
    t_last_change: float | None


class ChurnTracker:
    """§7.4: ring buffer of unmasked change maps, running per-pixel count, per-pixel hysteresis mask."""

    def __init__(self, shape: tuple[int, int], fps: float, p: ChurnParams):
        self.h, self.w = shape
        self.p = p
        self.n = max(2, int(round(p.window_s * fps)))
        self.warmup = min(self.n, max(2, int(round(fps))))  # need ~1 s of history before masking anything
        size = self.h * self.w
        self.ring = np.zeros((self.n, (size + 7) // 8), dtype=np.uint8)
        self.filled = 0
        self.pos = 0
        self.count = np.zeros(size, dtype=np.uint16)
        self.mask = np.zeros(size, dtype=bool)
        self.last_change = np.full(size, -1, dtype=np.int32)
        self.times: dict[int, float] = {}
        self.regions: list[BBox] = []

    @property
    def active(self) -> bool:
        return bool(self.regions)

    def update(self, changed: np.ndarray, frame_index: int, t: float) -> ChurnUpdate:
        flat = changed.ravel()
        size = flat.size
        if self.filled == self.n:
            old = np.unpackbits(self.ring[self.pos])[:size].astype(bool)
            self.count[old] -= 1
        else:
            self.filled += 1
        self.ring[self.pos] = np.packbits(flat)
        self.pos = (self.pos + 1) % self.n
        self.count[flat] += 1
        self.last_change[flat] = frame_index
        self.times[frame_index] = t
        if len(self.times) > self.n + 2:
            for k in [k for k in self.times if k < frame_index - self.n - 1]:
                del self.times[k]
        n = self.filled
        if n < self.warmup:
            return ChurnUpdate([], False, None)
        on = self.count > self.p.rho_on * n
        stay = self.mask & (self.count > self.p.rho_off * n)
        new_mask = on | stay
        leaving = self.mask & ~new_mask
        deactivated = bool(leaving.any())
        t_last = None
        if deactivated:
            idx = int(self.last_change[leaving].max())
            t_last = self.times.get(idx, t)
        self.mask = new_mask
        self.regions = self._regions(new_mask)
        return ChurnUpdate(self.regions, deactivated, t_last)

    def _regions(self, mask: np.ndarray) -> list[BBox]:
        if not mask.any():
            return []
        m2 = mask.reshape(self.h, self.w)
        m2 = ndimage.binary_opening(m2, structure=_S8)
        m2 = ndimage.binary_dilation(m2, structure=np.ones((9, 9), dtype=bool))
        labels, k = ndimage.label(m2, structure=_S8)
        if k == 0:
            return []
        areas = np.bincount(labels.ravel(), minlength=k + 1)
        out: list[BBox] = []
        for lab, sl in enumerate(ndimage.find_objects(labels), start=1):
            if sl is None or areas[lab] < self.p.min_area:
                continue
            ys, xs = sl
            out.append((int(xs.start), int(ys.start), int(xs.stop), int(ys.stop)))
        return out

    def excludes(self, c: Component) -> bool:
        cx = (c.bbox[0] + c.bbox[2]) / 2
        cy = (c.bbox[1] + c.bbox[3]) / 2
        return any(x0 <= cx < x1 and y0 <= cy < y1 for x0, y0, x1, y1 in self.regions)


@dataclass
class Candidate:
    bbox: BBox
    times: list[float]
    last_seen: float
    confirmed: bool = False
    confirmed_at: float | None = None


@dataclass
class BlinkUpdate:
    excluded: set[int]
    newly_confirmed: list[Candidate] = field(default_factory=list)


class BlinkTracker:
    """§7.5: small components recurring periodically at one position are blinkers (cursors)."""

    def __init__(self, p: BlinkParams):
        self.p = p
        self.cands: list[Candidate] = []

    def _match(self, bbox: BBox) -> Candidate | None:
        best, best_iou = None, 0.0
        for c in self.cands:
            v = iou(c.bbox, bbox)
            if v >= self.p.iou and v > best_iou:
                best, best_iou = c, v
        return best

    def update(self, comps: list[Component], t: float) -> BlinkUpdate:
        excluded: set[int] = set()
        newly: list[Candidate] = []
        for idx, c in enumerate(comps):
            w, h = c.bbox[2] - c.bbox[0], c.bbox[3] - c.bbox[1]
            if w > self.p.max_w or h > self.p.max_h:
                continue
            cand = self._match(c.bbox)
            if cand is None:
                self.cands.append(Candidate(c.bbox, [t], t))
                continue
            dt = t - cand.times[-1]
            cand.last_seen = t
            if dt < self.p.min_period_s:
                if cand.confirmed:
                    excluded.add(idx)
                continue
            if dt <= self.p.max_period_s:
                cand.times.append(t)
            else:
                cand.times = [t]
                cand.confirmed = False
            cand.bbox = c.bbox
            recent = [x for x in cand.times if t - x <= self.p.confirm_window_s]
            if not cand.confirmed and len(recent) - 1 >= self.p.confirm_recurrences:
                cand.confirmed = True
                cand.confirmed_at = t
                newly.append(cand)
            if cand.confirmed:
                excluded.add(idx)
        self.cands = [c for c in self.cands if t - c.last_seen <= self.p.expiry_s]
        return BlinkUpdate(excluded, newly)

    def is_blinker_bbox(self, bbox: BBox) -> bool:
        c = self._match(bbox)
        return c is not None and c.confirmed

    def caret_for_interval(self, t0: float, t1: float) -> BBox | None:
        best: Candidate | None = None
        for c in self.cands:
            if c.confirmed and any(t0 <= x <= t1 for x in c.times):
                if best is None or c.times[-1] > best.times[-1]:
                    best = c
        return best.bbox if best else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_detect.py -v`
Expected: 7 passed. If `test_churn_activates…` deactivates outside the expected window, print `tr.count.max()` per frame: with `window_s=1.0` (30 maps) and `rho_off=0.2`, the count drops below 6 about 24 frames after the flicker stops (frame ~114).

- [ ] **Step 5: Commit**

```bash
git add src/vt/detect.py tests/test_detect.py
git commit -m "feat: change detection with dilation+min-area, churn tracker, blink tracker"
```

---

### Task 5: Settle state machine (§7.3)

**Files:**
- Create: `src/vt/settle.py`
- Test: `tests/test_settle.py`

**Interfaces:**
- Consumes: `vt.detect` (Task 4), `Stage1Config` (Task 1).
- Produces: `Emission(frame_index, t_change, t_settled, settled, churn_regions, frame, t_end, caret)`; `SettleMachine(cfg: Stage1Config, fps, shape, downsample=1, on_emit=None)` with `.step(index, t, gray, frame=None) -> list[Emission]` (records finalized by this step) and `.finish(duration) -> list[Emission]`. `on_emit(em)` is called at emission time with the frame object attached (for PNG encoding); finalized records carry `t_end` and `caret`. Bboxes in emissions are scaled back to full-resolution pixels.

- [ ] **Step 1: Write the failing simulation tests**

`tests/test_settle.py`:

```python
import numpy as np

from vt.config import Stage1Config
from vt.settle import SettleMachine

FPS = 30
H, W = 60, 200


def run(frames, cfg=None, duration=None):
    cfg = cfg or Stage1Config()
    m = SettleMachine(cfg, FPS, (H, W))
    out = []
    for i, g in enumerate(frames):
        out += m.step(i, i / FPS, g)
    out += m.finish(duration if duration is not None else len(frames) / FPS)
    return out


def blank():
    return np.zeros((H, W), np.uint8)


def with_glyphs(n, base=None, x0=10, y=20):
    g = blank() if base is None else base.copy()
    for k in range(n):
        g[y:y + 10, x0 + 8 * k:x0 + 8 * k + 6] = 255
    return g


def test_static_video_emits_only_first_frame():
    frames = [blank() for _ in range(90)]
    ems = run(frames)
    assert len(ems) == 1
    assert ems[0].settled and ems[0].t_change == 0.0 and ems[0].t_end == 3.0


def test_single_change_settles_with_first_still_frame_time():
    frames = [blank() for _ in range(30)] + [with_glyphs(1) for _ in range(60)]
    ems = run(frames)
    assert len(ems) == 2
    e = ems[1]
    assert e.frame_index >= 30 + 12
    assert e.t_change == 30 / FPS
    assert e.t_settled == 30 / FPS  # frame 31 is still relative to 30, so the state was on screen at t(30)
    assert e.settled
    assert ems[0].t_end == e.t_change


def test_flash_that_reverts_within_S_emits_nothing():
    frames = [blank() for _ in range(30)] + [with_glyphs(2) for _ in range(6)] + [blank() for _ in range(60)]
    assert len(run(frames)) == 1


def test_bar_caret_blink_does_not_emit_and_is_recorded_as_caret():
    frames = []
    for i in range(150):
        g = blank()
        if (i // 15) % 2 == 1:
            g[20:38, 100:102] = 255
        frames.append(g)
    ems = run(frames)
    assert len(ems) == 1
    assert ems[0].caret is not None and abs(ems[0].caret[0] - 100) <= 1


def test_block_cursor_blink_is_learned_and_does_not_prevent_settling():
    frames = [blank() for _ in range(15)]
    for i in range(15, 240):
        g = with_glyphs(1)
        if (i // 15) % 2 == 1:
            g[20:32, 20:28] = 255  # 8x12 block cursor right of the glyph
        frames.append(g)
    ems = run(frames)
    assert len(ems) == 2
    e = ems[1]
    assert e.settled
    assert abs(e.t_settled - 15 / FPS) < 0.05  # corrected back to the real motion, not the blinks
    assert not any(not x.settled for x in ems)


def test_typing_without_pauses_is_one_state_and_with_a_pause_is_two():
    fast = [blank() for _ in range(30)]
    for k in range(1, 6):
        fast += [with_glyphs(k) for _ in range(8)]  # 0.27 s per keystroke < S
    fast += [with_glyphs(5) for _ in range(60)]
    ems = run(fast)
    assert len(ems) == 2 and ems[1].t_change == 30 / FPS and ems[1].t_settled == (30 + 8 * 4) / FPS

    slow = [blank() for _ in range(30)] + [with_glyphs(1) for _ in range(30)] + [with_glyphs(2) for _ in range(60)]
    ems = run(slow)
    assert len(ems) == 3


def test_max_hold_during_continuous_motion_then_settle():
    frames = [blank() for _ in range(30)]
    for i in range(150):  # a 20x20 block sweeping right for 5 s
        g = blank()
        x = 10 + i
        g[30:50, x:x + 20] = 255
        frames.append(g)
    frames += [frames[-1] for _ in range(60)]
    ems = run(frames)
    unsettled = [e for e in ems if not e.settled]
    settled = [e for e in ems if e.settled]
    assert len(unsettled) == 1 and abs(unsettled[0].t_change - 30 / FPS) < 1e-6 and abs(unsettled[0].t_settled - (30 + 90) / FPS) < 1e-6
    assert settled[-1].t_settled == (30 + 149) / FPS


def test_max_hold_frame_that_is_the_end_state_is_upgraded():
    frames = [blank() for _ in range(30)]
    for i in range(90):  # motion for exactly M = 3 s
        g = blank()
        g[30:50, 10 + i:30 + i] = 255
        frames.append(g)
    frames += [frames[-1] for _ in range(60)]  # identical to the max-hold frame
    ems = run(frames)
    assert len(ems) == 2
    assert ems[1].settled and ems[1].t_settled == (30 + 89) / FPS


def test_end_of_stream_flushes_pending_change():
    frames = [blank() for _ in range(30)] + [with_glyphs(3) for _ in range(5)]
    ems = run(frames)
    assert len(ems) == 2 and ems[1].settled and ems[1].t_end == 35 / FPS


def test_scrolling_region_yields_ticks_and_a_final_settled_state():
    cfg = Stage1Config()
    cfg.churn.window_s = 1.0
    cfg.churn.min_area = 100
    rng = np.random.default_rng(1)
    frames = [blank() for _ in range(30)]
    for i in range(300):  # 10 s of a 30x40 region changing every frame
        g = blank()
        g[10:40, 120:160] = (rng.random((30, 40)) * 255).astype(np.uint8)
        frames.append(g)
    frames += [frames[-1] for _ in range(180)]
    ems = run(frames, cfg)
    ticks = [e for e in ems if not e.settled]
    assert len(ticks) >= 2
    final = ems[-1]
    assert final.settled and abs(final.t_settled - (30 + 299) / FPS) < 0.1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_settle.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.settle`.

- [ ] **Step 3: Write the implementation**

`src/vt/settle.py`:

```python
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from vt.config import Stage1Config
from vt.detect import BlinkTracker, ChurnTracker, Component, change_map, components, iou, is_bar, scale_params, trigger
from vt.schemas import BBox


@dataclass
class Emission:
    frame_index: int
    t_change: float
    t_settled: float
    settled: bool
    churn_regions: list[BBox]
    frame: object = None
    t_end: float | None = None
    caret: BBox | None = None
    png_future: object = None


class SettleMachine:
    """§7.3 settle state machine over grayscale frames at detection resolution."""

    def __init__(self, cfg: Stage1Config, fps: float, shape: tuple[int, int], downsample: int = 1,
                 on_emit: Callable[[Emission], None] | None = None):
        self.d, cp, bp = scale_params(cfg.detect, cfg.churn, cfg.blink, downsample)
        self.S = cfg.settle.still_s
        self.M = cfg.settle.max_hold_s
        self.ds = downsample
        self.churn = ChurnTracker(shape, fps, cp)
        self.blink = BlinkTracker(bp)
        self.on_emit = on_emit
        self.prev: np.ndarray | None = None
        self.prev_t = 0.0
        self.prev_index = 0
        self.prev_frame: object = None
        self.last_gray: np.ndarray | None = None
        self.last: Emission | None = None
        self.changed = False
        self.t_change: float | None = None
        self.t_still: float | None = None
        self.t_last_emit = 0.0
        self.history: deque[tuple[float, bool, list[BBox]]] = deque()
        self.finalized: list[Emission] = []

    # ---- helpers ----
    def _scale(self, b: BBox) -> BBox:
        s = self.ds
        return (b[0] * s, b[1] * s, b[2] * s, b[3] * s)

    def _active(self, comps: list[Component], excluded: set[int]) -> list[Component]:
        return [c for i, c in enumerate(comps) if i not in excluded and not is_bar(c, self.d) and not self.churn.excludes(c)]

    def _novel(self, gray: np.ndarray) -> bool:
        comps = components(change_map(self.last_gray, gray, self.d.theta_pix), self.d.theta_min)
        active = [c for c in comps if not is_bar(c, self.d) and not self.churn.excludes(c) and not self.blink.is_blinker_bbox(c.bbox)]
        return trigger(active, self.d)

    def _emit(self, index: int, t: float, gray: np.ndarray, frame: object, t_change: float, t_settled: float, settled: bool) -> None:
        em = Emission(index, t_change, t_settled, settled, [self._scale(b) for b in self.churn.regions], frame=frame)
        self._finalize(t_change)
        self.last = em
        self.last_gray = gray
        self.t_last_emit = t
        if self.on_emit:
            self.on_emit(em)

    def _finalize(self, t_end: float) -> None:
        if self.last is None:
            return
        self.last.t_end = t_end
        caret = self.blink.caret_for_interval(self.last.t_settled, t_end)
        self.last.caret = self._scale(caret) if caret else None
        self.finalized.append(self.last)
        self.last = None

    def _drain(self) -> list[Emission]:
        out, self.finalized = self.finalized, []
        return out

    # ---- main loop ----
    def step(self, index: int, t: float, gray: np.ndarray, frame: object = None) -> list[Emission]:
        if self.prev is None:
            self._emit(index, t, gray, frame, t_change=t, t_settled=t, settled=True)
            self.prev, self.prev_t, self.prev_index, self.prev_frame = gray, t, index, frame
            return self._drain()
        cm = change_map(self.prev, gray, self.d.theta_pix)
        churn_upd = self.churn.update(cm, index, t)
        comps = components(cm, self.d.theta_min)
        blink_upd = self.blink.update(comps, t)
        active = self._active(comps, blink_upd.excluded)
        moving = trigger(active, self.d)
        self.history.append((t, moving, [c.bbox for c in active]))
        while self.history and t - self.history[0][0] > 3.0:
            self.history.popleft()

        if moving:
            if not self.changed:
                self.changed, self.t_change = True, t
            self.t_still = None
        elif self.changed:
            if self.t_still is None:
                self.t_still = self.prev_t
            if t - self.t_still >= self.S:
                if self._novel(gray):
                    self._emit(index, t, gray, frame, self.t_change, self.t_still, True)
                elif self.last is not None and not self.last.settled:
                    self.last.settled = True
                    self.last.t_settled = self.t_still
                self.changed = False

        if self.changed and self.t_still is None and t - self.t_change >= self.M:
            self._emit(index, t, gray, frame, self.t_change, t, False)
            self.t_change = t
        if self.churn.active and t - self.t_last_emit >= self.M:
            self._emit(index, t, gray, frame, self.t_last_emit, t, False)
        if churn_upd.deactivated:
            if not self.changed:
                self.changed, self.t_change = True, self.t_last_emit
            self.t_still = churn_upd.t_last_change if churn_upd.t_last_change is not None else self.prev_t
        for cand in blink_upd.newly_confirmed:
            t_real = self._last_real_motion(cand.bbox)
            if self.changed and t_real is not None and (self.t_still is None or t_real < self.t_still):
                self.t_still = t_real

        self.prev, self.prev_t, self.prev_index, self.prev_frame = gray, t, index, frame
        return self._drain()

    def _last_real_motion(self, blinker: BBox) -> float | None:
        for t, moving, boxes in reversed(self.history):
            if moving and any(iou(b, blinker) < self.blink.p.iou for b in boxes):
                return t
        return None

    def finish(self, duration: float) -> list[Emission]:
        if self.prev is not None and self.changed and self.last_gray is not None and self._novel(self.prev):
            t_settled = self.t_still if self.t_still is not None else self.prev_t
            self._emit(self.prev_index, self.prev_t, self.prev, self.prev_frame, self.t_change, t_settled, self.t_still is not None)
        self._finalize(duration)
        return self._drain()
```

- [ ] **Step 4: Run tests to verify they pass; tune only via the config values in `vt.toml` defaults**

Run: `uv run pytest tests/test_settle.py -v`
Expected: 10 passed. Likely first failures and their fixes:
- *Block-cursor test finds `t_settled` at a blink time:* the correction rule needs `history` entries with the blinker's toggles marked `moving=True`; confirm `_last_real_motion` compares against the candidate's bbox at confirmation time (`cand.bbox`).
- *Scrolling test gets no ticks:* the churn region needs ≥ 1 s of history (`warmup`); with `window_s=1.0` ticks start after `M` = 3 s; assert `len(ticks) >= 2` over 10 s.
- *Max-hold test off by one frame:* `t_settled` for the unsettled emission is `t` of the emitting frame (frame 30 + 90); adjust the test's tolerance, not the machine.

- [ ] **Step 5: Commit**

```bash
git add src/vt/settle.py tests/test_settle.py
git commit -m "feat: settle state machine with max-hold, churn ticks, blink correction, end-of-stream flush"
```

---

### Task 6: Run directory, Stage 1 driver, CLI skeleton

**Files:**
- Create: `src/vt/run.py`, `src/vt/stage1.py`, `src/vt/cli.py`
- Test: none beyond a `--help` smoke run (glue; the machine is tested in Task 5). Manual check on the sample video.

**Interfaces:**
- Produces: `Run(root: Path)` with attributes `root, frames_dir, overlays_dir, cache_dir`, file paths `stage1, ocr, perception, frames, transitions, focus, interpretations, steps, sections, video, outline, index_db, manifest, batches`; methods `manifest_read() -> dict`, `manifest_update(**kv)`, `stage_up_to_date(name, inputs: list[Path], cfg_hash) -> bool`, `stage_done(name, inputs, cfg_hash, **stats)`, `video_id`, `load_stage1()`, `load_ocr()`, `load_perception()`, `load_frames() -> list[FrameRecord]` (with `focus.jsonl` applied), `load_transitions() -> list[Transition]`, `load_interpretations() -> dict[str, Interpretation]`, `load_outline() -> list[OutlineChapter]`, `chapter_of(t) -> OutlineChapter | None`.
- Produces: `run_stage1(run, cfg, video: Path) -> None` writing `frames/NNNNN.png` and `stage1.jsonl`.
- Produces: `vt.cli.app` (typer) with `decode VIDEO --out RUN [--config vt.toml]`.

- [ ] **Step 1: Write `run.py`**

```python
from __future__ import annotations

import json
import time
from pathlib import Path

from vt.jsonl import read_jsonl, sha256_file
from vt.schemas import (FocusRecord, FrameRecord, Interpretation, OcrFrame, OutlineChapter, PerceptionRecord,
                        Stage1Record, Transition)


class Run:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.frames_dir = self.root / "frames"
        self.overlays_dir = self.root / "overlays"
        self.cache_dir = self.root / "cache"
        self.stage1 = self.root / "stage1.jsonl"
        self.ocr = self.root / "ocr.jsonl"
        self.perception = self.root / "perception.jsonl"
        self.frames = self.root / "frames.jsonl"
        self.transitions = self.root / "transitions.jsonl"
        self.focus = self.root / "focus.jsonl"
        self.interpretations = self.root / "interpretations.jsonl"
        self.steps = self.root / "steps.jsonl"
        self.sections = self.root / "sections.jsonl"
        self.video = self.root / "video.json"
        self.outline = self.root / "outline.json"
        self.index_db = self.root / "index.sqlite"
        self.manifest = self.root / "manifest.json"
        self.batches = self.root / "batches.json"
        for d in (self.root, self.frames_dir, self.overlays_dir, self.cache_dir):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def video_id(self) -> str:
        return self.manifest_read().get("video_id", self.root.name)

    # ---- manifest ----
    def manifest_read(self) -> dict:
        return json.loads(self.manifest.read_text()) if self.manifest.exists() else {}

    def manifest_update(self, **kv) -> None:
        m = self.manifest_read()
        m.update(kv)
        self.manifest.write_text(json.dumps(m, indent=2, sort_keys=True, default=str))

    def inputs_hash(self, inputs: list[Path]) -> str:
        parts = [f"{p.name}:{sha256_file(p) if p.exists() else 'missing'}" for p in inputs]
        return "|".join(parts)

    def stage_up_to_date(self, name: str, inputs: list[Path], cfg_hash: str) -> bool:
        st = self.manifest_read().get("stages", {}).get(name)
        return bool(st) and st.get("inputs") == self.inputs_hash(inputs) and st.get("config") == cfg_hash

    def stage_done(self, name: str, inputs: list[Path], cfg_hash: str, **stats) -> None:
        m = self.manifest_read()
        m.setdefault("stages", {})[name] = {"inputs": self.inputs_hash(inputs), "config": cfg_hash,
                                            "finished": time.strftime("%Y-%m-%dT%H:%M:%S"), **stats}
        self.manifest.write_text(json.dumps(m, indent=2, sort_keys=True, default=str))

    # ---- loaders (§10.7) ----
    def load_stage1(self) -> list[Stage1Record]:
        return read_jsonl(self.stage1, Stage1Record)

    def load_ocr(self) -> list[OcrFrame]:
        return read_jsonl(self.ocr, OcrFrame)

    def load_perception(self) -> list[PerceptionRecord]:
        return read_jsonl(self.perception, PerceptionRecord)

    def load_frames(self) -> list[FrameRecord]:
        frames = read_jsonl(self.frames, FrameRecord)
        focus = {f.frame: f for f in read_jsonl(self.focus, FocusRecord)}
        for fr in frames:
            f = focus.get(fr.frame)
            if f is not None:
                fr.focused_region, fr.focused_conf, fr.focused_signals = f.focused_region, f.focused_conf, f.focused_signals
        return frames

    def load_transitions(self) -> list[Transition]:
        return read_jsonl(self.transitions, Transition)

    def load_interpretations(self) -> dict[str, Interpretation]:
        return {i.id: i for i in read_jsonl(self.interpretations, Interpretation)}

    def load_outline(self) -> list[OutlineChapter]:
        if not self.outline.exists():
            return []
        return [OutlineChapter.model_validate(c) for c in json.loads(self.outline.read_text())]

    def chapter_of(self, t: float) -> OutlineChapter | None:
        for c in self.load_outline():
            if c.start_s <= t < c.end_s:
                return c
        return None
```

- [ ] **Step 2: Write `stage1.py`**

```python
from __future__ import annotations

import hashlib
import io
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from vt.config import Config, config_hash
from vt.decode import iter_frames, video_info
from vt.jsonl import sha256_file, write_jsonl
from vt.run import Run
from vt.schemas import Stage1Record
from vt.settle import Emission, SettleMachine

log = logging.getLogger(__name__)


def _encode_png(img, path: Path) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=1)
    data = buf.getvalue()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def run_stage1(run: Run, cfg: Config, video: Path) -> None:
    inputs = [video]
    ch = config_hash(cfg, "stage1")
    if run.stage_up_to_date("stage1", inputs, ch):
        log.info("stage1 up to date")
        return
    info = video_info(video)
    ds = cfg.stage1.detect.downsample
    run.manifest_update(video=str(video), video_sha256=sha256_file(video), video_id=run.root.name,
                        width=info.width, height=info.height, fps=info.fps, duration=info.duration)
    pool = ThreadPoolExecutor(max_workers=2)
    counter = {"n": 0}

    def on_emit(em: Emission) -> None:
        n = counter["n"]
        counter["n"] += 1
        img = em.frame.to_image()
        path = run.frames_dir / f"{n:05d}.png"
        em.png_future = pool.submit(_encode_png, img, path)
        em.frame = (n, path)

    machine = SettleMachine(cfg.stage1, info.fps, (info.height // ds, info.width // ds), ds, on_emit=on_emit)
    records: list[Stage1Record] = []

    def take(ems: list[Emission]) -> None:
        for em in ems:
            n, path = em.frame
            sha = em.png_future.result()
            records.append(Stage1Record(video_id=run.video_id, frame=n, t_change=em.t_change, t_settled=em.t_settled,
                                        t_end=em.t_end, settled=em.settled, churn_regions=em.churn_regions,
                                        caret=em.caret, width=info.width, height=info.height, sha256=sha,
                                        png=str(path.relative_to(run.root))))

    for df in iter_frames(video, ds):
        take(machine.step(df.index, df.t, df.gray, frame=df.frame))
        if df.index % 3000 == 0 and df.index:
            log.info("decoded %d frames (t=%.1fs), emitted %d", df.index, df.t, counter["n"])
    take(machine.finish(info.duration))
    pool.shutdown(wait=True)
    write_jsonl(run.stage1, records)
    run.stage_done("stage1", inputs, ch, emitted=len(records), settled=sum(r.settled for r in records))
```

Note: `stage1.on_emit` replaces `em.frame` (the decoded frame) with `(n, path)` and sets `em.png_future`; `SettleMachine._finalize` leaves `frame` untouched, so `take()` reads them back at finalization.

- [ ] **Step 3: Write `cli.py` (decode only; later tasks add commands)**

```python
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
```

- [ ] **Step 4: Smoke-run on the sample video (manual, not a test)**

Run: `uv run vt decode assets/create-aks-cluster-tutorial.mp4 --out runs/aks --verbose`
Expected: completes in a few minutes; `runs/aks/stage1.jsonl` has on the order of 100–400 records; open three PNGs from `runs/aks/frames/` and confirm they are settled screens. Record the emitted count and wall time in the decision ledger / README.

- [ ] **Step 5: Commit**

```bash
git add src/vt/run.py src/vt/stage1.py src/vt/cli.py
git commit -m "feat: run directory, Stage 1 driver, vt decode"
```

---

### Task 7: OCR engine interface, Apple Vision adapter, Stage 2a (§8.1, §20.4)

**Files:**
- Create: `src/vt/ocr/__init__.py`, `src/vt/ocr/base.py`, `src/vt/ocr/vision.py`, `src/vt/ocr/rapid.py`, `src/vt/stage2a.py`
- Modify: `src/vt/cli.py` (add `ocr`)
- Test: `tests/test_ocr.py` (platform-independent parts), `tests/test_vision.py` (macOS only)

**Interfaces:**
- Produces: `RawLine(text, conf, bbox, words: list[RawWord] | None)`; `OcrEngine` protocol with `name: str`, `settings() -> dict`, `recognize(png: Path) -> list[RawLine]`; `get_engine(cfg: OcrConfig) -> OcrEngine`; `is_confusable(text) -> bool`; `assign_ids(raw: list[RawLine], churn: list[BBox]) -> list[OcrLine]`; `run_ocr(run, cfg)` writing `ocr.jsonl`.

- [ ] **Step 1: Write the failing tests**

`tests/test_ocr.py`:

```python
from vt.ocr.base import RawLine
from vt.schemas import RawWord
from vt.stage2a import assign_ids, is_confusable


def test_confusable_flags_mixed_script_tokens():
    assert is_confusable("3ебb0e8a-2743")      # Cyrillic е and б inside an ASCII token
    assert not is_confusable("git status")
    assert not is_confusable("naïve café")      # whole-word non-ASCII letters are fine
    assert not is_confusable("• Zone 1")


def test_assign_ids_reading_order_and_churn():
    raw = [RawLine("second", 1.0, (10, 40, 100, 58), None), RawLine("first", 1.0, (10, 10, 100, 28), None),
           RawLine("spinner text", 1.0, (500, 10, 600, 28), [RawWord(text="spinner", bbox=(500, 10, 560, 28))])]
    lines = assign_ids(raw, churn=[(490, 0, 700, 100)])
    assert [ln.id for ln in lines] == ["l1", "l2", "l3"]
    assert [ln.text for ln in lines] == ["first", "spinner text", "second"]
    assert [ln.in_churn for ln in lines] == [False, True, False]
    assert lines[1].words[0].text == "spinner"
```

`tests/test_vision.py`:

```python
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="Apple Vision is macOS only")


def test_vision_reads_terminal_text_exactly(tmp_path: Path):
    from vt.config import OcrConfig
    from vt.ocr.vision import VisionEngine

    img = Image.new("RGB", (900, 120), (12, 12, 12))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
    d.text((20, 20), "PS C:\\src> git status", fill=(230, 230, 230), font=font)
    d.text((20, 60), "az aks create --resource-group rg-demo --name aks-demo-01", fill=(230, 230, 230), font=font)
    png = tmp_path / "t.png"
    img.save(png)
    eng = VisionEngine(OcrConfig())
    lines = sorted(eng.recognize(png), key=lambda l: l.bbox[1])
    assert [l.text for l in lines] == ["PS C:\\src> git status", "az aks create --resource-group rg-demo --name aks-demo-01"]
    x0, y0, x1, y1 = lines[0].bbox
    assert 10 <= x0 <= 30 and 10 <= y0 <= 30 and 200 <= x1 <= 280 and 36 <= y1 <= 50
    assert lines[0].words and lines[0].words[0].text == "PS"
    assert eng.settings()["language_correction"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ocr.py tests/test_vision.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.ocr`.

- [ ] **Step 3: Write the implementation**

`src/vt/ocr/base.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from vt.schemas import BBox, RawWord


@dataclass
class RawLine:
    text: str
    conf: float
    bbox: BBox
    words: list[RawWord] | None


class OcrEngine(Protocol):
    name: str

    def settings(self) -> dict: ...

    def recognize(self, png: Path) -> list[RawLine]: ...
```

`src/vt/ocr/vision.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

from vt.config import OcrConfig
from vt.ocr.base import RawLine
from vt.schemas import BBox, RawWord


def _to_pixels(rect, W: int, H: int) -> BBox:
    x0 = rect.origin.x * W
    y0 = (1.0 - rect.origin.y - rect.size.height) * H
    x1 = (rect.origin.x + rect.size.width) * W
    y1 = (1.0 - rect.origin.y) * H
    clamp = lambda v, hi: int(min(max(round(v), 0), hi))
    return (clamp(x0, W), clamp(y0, H), clamp(x1, W), clamp(y1, H))


class VisionEngine:
    name = "apple-vision"

    def __init__(self, cfg: OcrConfig):
        import Foundation  # noqa: F401  (PyObjC)
        import Quartz
        import Vision

        self._F, self._Q, self._V = Foundation, Quartz, Vision
        self.cfg = cfg
        self._revision = int(self._make_request().revision())

    def _make_request(self):
        V = self._V
        req = V.VNRecognizeTextRequest.alloc().init()
        req.setRecognitionLevel_(V.VNRequestTextRecognitionLevelAccurate)
        req.setUsesLanguageCorrection_(bool(self.cfg.language_correction))
        req.setRecognitionLanguages_(list(self.cfg.languages))
        req.setAutomaticallyDetectsLanguage_(False)
        req.setMinimumTextHeight_(float(self.cfg.minimum_text_height))
        return req

    def settings(self) -> dict:
        return {"engine": self.name, "revision": self._revision, "level": "accurate",
                "language_correction": bool(self.cfg.language_correction), "languages": list(self.cfg.languages),
                "minimum_text_height": float(self.cfg.minimum_text_height)}

    def recognize(self, png: Path) -> list[RawLine]:
        F, Q = self._F, self._Q
        src = Q.CGImageSourceCreateWithURL(F.NSURL.fileURLWithPath_(str(png)), None)
        cg = Q.CGImageSourceCreateImageAtIndex(src, 0, None)
        if cg is None:
            raise RuntimeError(f"cannot load {png}")
        W, H = Q.CGImageGetWidth(cg), Q.CGImageGetHeight(cg)
        req = self._make_request()
        handler = self._V.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, None)
        ok, err = handler.performRequests_error_([req], None)
        if not ok:
            raise RuntimeError(f"Vision failed on {png}: {err}")
        out: list[RawLine] = []
        for obs in req.results() or []:
            cands = obs.topCandidates_(1)
            if not cands:
                continue
            cand = cands[0]
            text = str(cand.string())
            bbox = _to_pixels(obs.boundingBox(), W, H)
            words: list[RawWord] = []
            for m in re.finditer(r"\S+", text):
                rect_obs, _ = cand.boundingBoxForRange_error_(F.NSMakeRange(m.start(), m.end() - m.start()), None)
                if rect_obs is not None:
                    words.append(RawWord(text=m.group(), bbox=_to_pixels(rect_obs.boundingBox(), W, H)))
            out.append(RawLine(text, float(cand.confidence()), bbox, words or None))
        return out
```

`src/vt/ocr/rapid.py`:

```python
from __future__ import annotations

from pathlib import Path

from vt.config import OcrConfig
from vt.ocr.base import RawLine


class RapidEngine:
    name = "rapidocr"

    def __init__(self, cfg: OcrConfig):
        from rapidocr_onnxruntime import RapidOCR  # optional extra: uv sync --extra rapid

        self._ocr = RapidOCR()
        self.cfg = cfg

    def settings(self) -> dict:
        return {"engine": self.name}

    def recognize(self, png: Path) -> list[RawLine]:
        result, _ = self._ocr(str(png))
        out: list[RawLine] = []
        for quad, text, conf in result or []:
            xs = [int(round(p[0])) for p in quad]
            ys = [int(round(p[1])) for p in quad]
            out.append(RawLine(str(text), float(conf), (min(xs), min(ys), max(xs), max(ys)), None))
        return out
```

`src/vt/ocr/__init__.py`:

```python
from __future__ import annotations

from vt.config import OcrConfig
from vt.ocr.base import OcrEngine, RawLine  # noqa: F401


def get_engine(cfg: OcrConfig) -> OcrEngine:
    if cfg.engine == "vision":
        from vt.ocr.vision import VisionEngine

        return VisionEngine(cfg)
    if cfg.engine == "rapid":
        from vt.ocr.rapid import RapidEngine

        return RapidEngine(cfg)
    raise ValueError(f"unknown OCR engine {cfg.engine}")
```

`src/vt/stage2a.py`:

```python
from __future__ import annotations

import logging
import re
import time
import unicodedata

from vt.config import Config, config_hash
from vt.jsonl import write_jsonl
from vt.ocr import get_engine
from vt.ocr.base import RawLine
from vt.run import Run
from vt.schemas import BBox, OcrFrame, OcrLine

log = logging.getLogger(__name__)
_TOKEN = re.compile(r"\S+")


def is_confusable(text: str) -> bool:
    """A token mixing ASCII letters/digits with non-ASCII letters (Cyrillic е in a GUID)."""
    for tok in _TOKEN.findall(text):
        has_ascii = any(ch.isascii() and ch.isalnum() for ch in tok)
        has_foreign = any((not ch.isascii()) and unicodedata.category(ch).startswith("L") for ch in tok)
        if has_ascii and has_foreign:
            return True
    return False


def _intersects(a: BBox, b: BBox) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def assign_ids(raw: list[RawLine], churn: list[BBox]) -> list[OcrLine]:
    ordered = sorted(raw, key=lambda l: (l.bbox[1], l.bbox[0]))
    out: list[OcrLine] = []
    for i, l in enumerate(ordered, start=1):
        out.append(OcrLine(id=f"l{i}", bbox=l.bbox, text=l.text, conf=l.conf, words=l.words,
                           in_churn=any(_intersects(l.bbox, c) for c in churn), confusable=is_confusable(l.text)))
    return out


def run_ocr(run: Run, cfg: Config) -> None:
    inputs = [run.stage1]
    ch = config_hash(cfg, "ocr")
    if run.stage_up_to_date("ocr", inputs, ch):
        log.info("ocr up to date")
        return
    engine = get_engine(cfg.ocr)
    frames = []
    for rec in run.load_stage1():
        t0 = time.time()
        raw = engine.recognize(run.root / rec.png)
        frames.append(OcrFrame(frame=rec.frame, engine=engine.name, settings=engine.settings(),
                               seconds=round(time.time() - t0, 3), lines=assign_ids(raw, rec.churn_regions)))
    write_jsonl(run.ocr, frames)
    run.stage_done("ocr", inputs, ch, frames=len(frames), lines=sum(len(f.lines) for f in frames),
                   seconds=round(sum(f.seconds for f in frames), 1), engine=engine.settings())
```

Add to `cli.py`:

```python
@app.command()
def ocr(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 2a: OCR every emitted frame → ocr.jsonl."""
    _setup_logging(verbose)
    from vt.stage2a import run_ocr
    run_ocr(Run(run_dir), load_config(config))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ocr.py tests/test_vision.py -v`
Expected: 3 passed (the Vision test is skipped off macOS). Then `uv run vt ocr runs/aks` on the smoke run: expect 0.1–0.3 s per frame.

- [ ] **Step 5: Commit**

```bash
git add src/vt/ocr src/vt/stage2a.py src/vt/cli.py tests/test_ocr.py tests/test_vision.py
git commit -m "feat: OCR engine interface, Apple Vision adapter, Stage 2a"
```

---

### Task 8: Set-of-mark overlay with clash-free label placement (§8.2)

**Files:**
- Create: `src/vt/overlay.py`
- Modify: `src/vt/cli.py` (add `overlay`)
- Test: `tests/test_overlay.py`

**Interfaces:**
- Produces: `place_label(box, lw, lh, boxes, W, H) -> tuple[int, int, bool]` (x, y, clash); `draw_overlay(png_in, lines: list[OcrLine], png_out, cfg: OverlayConfig) -> int` (clash count); `run_overlay(run, cfg)` writing `overlays/NNNNN.png` and recording `label_clashes` per frame in the manifest (`overlay.clashes: {frame: n}`).

- [ ] **Step 1: Write the failing tests**

`tests/test_overlay.py`:

```python
from pathlib import Path

from PIL import Image

from vt.config import OverlayConfig
from vt.overlay import draw_overlay, place_label
from vt.schemas import OcrLine


def test_place_label_prefers_right_then_left_then_above_then_below():
    W, H = 400, 200
    box = (100, 50, 200, 66)
    lw, lh = 14, 10
    # nothing around: right of the box
    x, y, clash = place_label(box, lw, lh, [box], W, H)
    assert (x, y, clash) == (202, 53, False)
    # a box immediately right → left gutter
    right = (202, 50, 300, 66)
    x, y, clash = place_label(box, lw, lh, [box, right], W, H)
    assert (x, y, clash) == (84, 53, False)
    # boxes right and left → above
    left = (60, 50, 98, 66)
    x, y, clash = place_label(box, lw, lh, [box, right, left], W, H)
    assert (x, y, clash) == (100, 39, False)
    # right, left, above and below occupied → least-overlap fallback, clash counted
    above = (100, 34, 200, 49)
    below = (100, 67, 200, 83)
    x, y, clash = place_label(box, lw, lh, [box, right, left, above, below], W, H)
    assert clash is True


def test_place_label_never_leaves_the_image():
    x, y, clash = place_label((0, 0, 50, 16), 14, 10, [(0, 0, 50, 16)], 400, 200)
    assert x >= 0 and y >= 0


def test_draw_overlay_keeps_dimensions(tmp_path: Path):
    src = tmp_path / "f.png"
    Image.new("RGB", (320, 120), (10, 10, 10)).save(src)
    lines = [OcrLine(id="l1", bbox=(10, 10, 120, 28), text="a", conf=1.0),
             OcrLine(id="l2", bbox=(10, 40, 200, 58), text="b", conf=1.0)]
    out = tmp_path / "o.png"
    clashes = draw_overlay(src, lines, out, OverlayConfig())
    im = Image.open(out)
    assert im.size == (320, 120) and clashes == 0
    assert im.getpixel((10, 10)) != (10, 10, 10)  # a rectangle was drawn
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_overlay.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.overlay`.

- [ ] **Step 3: Write the implementation**

`src/vt/overlay.py`:

```python
from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from vt.config import Config, OverlayConfig, config_hash
from vt.run import Run
from vt.schemas import BBox, OcrLine

log = logging.getLogger(__name__)
COLOR = (255, 0, 255, 255)


def _overlap(a: BBox, b: BBox) -> int:
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def place_label(box: BBox, lw: int, lh: int, boxes: list[BBox], W: int, H: int) -> tuple[int, int, bool]:
    x0, y0, x1, y1 = box
    cy = (y0 + y1) // 2 - lh // 2
    slots = [(x1 + 2, cy), (x0 - lw - 2, cy), (x0, y0 - lh - 1), (x0, y1 + 1)]
    others = [b for b in boxes if b != box]
    best, best_ov = None, None
    for sx, sy in slots:
        sx = min(max(sx, 0), W - lw)
        sy = min(max(sy, 0), H - lh)
        rect = (sx, sy, sx + lw, sy + lh)
        ov = _overlap(rect, box) + sum(_overlap(rect, b) for b in others)
        if ov == 0:
            return sx, sy, False
        if best_ov is None or ov < best_ov:
            best, best_ov = (sx, sy), ov
    return best[0], best[1], True


def _font(cfg: OverlayConfig):
    try:
        return ImageFont.truetype(cfg.font_path, cfg.font_size)
    except OSError:
        return ImageFont.load_default()


def draw_overlay(png_in: Path, lines: list[OcrLine], png_out: Path, cfg: OverlayConfig) -> int:
    img = Image.open(png_in).convert("RGBA")
    W, H = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = _font(cfg)
    boxes = [ln.bbox for ln in lines]
    clashes = 0
    for ln in lines:
        x0, y0, x1, y1 = ln.bbox
        draw.rectangle((x0, y0, max(x1 - 1, x0), max(y1 - 1, y0)), outline=COLOR, width=1)
        label = ln.id[1:]  # "l17" → "17"
        l, t, r, b = font.getbbox(label)
        lw, lh = (r - l) + 2, (b - t) + 2
        x, y, clash = place_label(ln.bbox, lw, lh, boxes, W, H)
        clashes += int(clash)
        draw.rectangle((x, y, x + lw, y + lh), fill=(0, 0, 0, 128))
        draw.text((x + 1 - l, y + 1 - t), label, fill=COLOR, font=font)
    Image.alpha_composite(img, layer).convert("RGB").save(png_out, format="PNG", compress_level=1)
    return clashes


def run_overlay(run: Run, cfg: Config) -> None:
    inputs = [run.ocr]
    ch = config_hash(cfg, "overlay")
    if run.stage_up_to_date("overlay", inputs, ch):
        log.info("overlay up to date")
        return
    s1 = {r.frame: r for r in run.load_stage1()}
    clashes: dict[int, int] = {}
    for of in run.load_ocr():
        rec = s1[of.frame]
        out = run.overlays_dir / f"{of.frame:05d}.png"
        clashes[of.frame] = draw_overlay(run.root / rec.png, of.lines, out, cfg.overlay)
    run.manifest_update(overlay_clashes=clashes)
    run.stage_done("overlay", inputs, ch, frames=len(clashes), label_clashes=sum(clashes.values()))
```

Add to `cli.py`:

```python
@app.command()
def overlay(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 2b: draw numbered boxes → overlays/."""
    _setup_logging(verbose)
    from vt.overlay import run_overlay
    run_overlay(Run(run_dir), load_config(config))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_overlay.py -v`
Expected: 3 passed. Then `uv run vt overlay runs/aks` and open one overlay PNG: labels sit beside boxes, never over text.

- [ ] **Step 5: Commit**

```bash
git add src/vt/overlay.py src/vt/cli.py tests/test_overlay.py
git commit -m "feat: set-of-mark overlay with clash-free label placement"
```

---

### Task 9: Model provider — Anthropic structured outputs, on-disk cache, retry ladder (§20.7)

**Files:**
- Create: `src/vt/providers/__init__.py`, `src/vt/providers/base.py`, `src/vt/providers/cache.py`, `src/vt/providers/anthropic_.py`
- Test: `tests/test_provider.py`

**Interfaces:**
- Produces: `text_block(s) -> dict`, `image_block(png: Path) -> dict`, `VlmResult(parsed, error, usage, raw_text, cached, stop_reason)`, `VlmProvider` protocol with `async complete(*, stage, system, blocks, output_model, effort, prompt_version, input_hashes) -> VlmResult`; `CallCache(dir)` with `key(...)`, `get(key)`, `put(key, request, response)`; `AnthropicProvider(cfg: ModelConfig, cache: CallCache, client=None)`; `get_provider(cfg: Config, run: Run) -> VlmProvider`.

- [ ] **Step 1: Write the failing tests**

`tests/test_provider.py`:

```python
import asyncio
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel

from vt.config import ModelConfig
from vt.providers.anthropic_ import AnthropicProvider
from vt.providers.base import text_block
from vt.providers.cache import CallCache


class Out(BaseModel):
    answer: str


class FakeMessages:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def parse(self, **kw):
        self.calls.append(kw)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(parsed_output=item.get("parsed"), stop_reason=item.get("stop", "end_turn"),
                               usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0, cache_creation_input_tokens=0),
                               content=[SimpleNamespace(type="text", text=item.get("text", ""))])


def fake_client(script):
    return SimpleNamespace(messages=FakeMessages(script))


def run(coro):
    return asyncio.run(coro)


def test_cache_hit_avoids_second_call(tmp_path: Path):
    client = fake_client([{"parsed": Out(answer="a")}])
    p = AnthropicProvider(ModelConfig(), CallCache(tmp_path), client=client)
    kw = dict(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"])
    r1 = run(p.complete(**kw))
    r2 = run(p.complete(**kw))
    assert r1.parsed == Out(answer="a") and not r1.cached
    assert r2.parsed == Out(answer="a") and r2.cached
    assert len(client.messages.calls) == 1
    assert client.messages.calls[0]["output_config"] == {"effort": "low"}
    assert client.messages.calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_max_tokens_retries_once_with_larger_budget(tmp_path: Path):
    client = fake_client([{"parsed": None, "stop": "max_tokens"}, {"parsed": Out(answer="b")}])
    p = AnthropicProvider(ModelConfig(max_tokens=100, retry_max_tokens=200), CallCache(tmp_path), client=client)
    r = run(p.complete(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"]))
    assert r.parsed == Out(answer="b")
    assert [c["max_tokens"] for c in client.messages.calls] == [100, 200]


def test_refusal_is_recorded_not_raised(tmp_path: Path):
    client = fake_client([{"parsed": None, "stop": "refusal"}])
    p = AnthropicProvider(ModelConfig(), CallCache(tmp_path), client=client)
    r = run(p.complete(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"]))
    assert r.parsed is None and r.error == "refusal"


def test_schema_failure_retries_once_with_error_text(tmp_path: Path):
    client = fake_client([ValueError("1 validation error"), {"parsed": Out(answer="c")}])
    p = AnthropicProvider(ModelConfig(), CallCache(tmp_path), client=client)
    r = run(p.complete(stage="s", system="sys", blocks=[text_block("q")], output_model=Out, effort="low", prompt_version="v1", input_hashes=["h"]))
    assert r.parsed == Out(answer="c")
    second = client.messages.calls[1]["messages"][0]["content"]
    assert "validation error" in second[-1]["text"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_provider.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.providers`.

- [ ] **Step 3: Write the implementation**

`src/vt/providers/base.py`:

```python
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def text_block(s: str) -> dict:
    return {"type": "text", "text": s}


def image_block(png: Path) -> dict:
    data = base64.standard_b64encode(png.read_bytes()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}


@dataclass
class VlmResult:
    parsed: BaseModel | None
    error: str | None
    usage: dict = field(default_factory=dict)
    raw_text: str | None = None
    cached: bool = False
    stop_reason: str | None = None


class VlmProvider(Protocol):
    model: str

    async def complete(self, *, stage: str, system: str, blocks: list[dict], output_model: type[T], effort: str,
                       prompt_version: str, input_hashes: list[str]) -> VlmResult: ...
```

`src/vt/providers/cache.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from vt.jsonl import sha256_obj


class CallCache:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(stage: str, model: str, effort: str, max_tokens: int, prompt_version: str, schema_hash: str, input_hashes: list[str]) -> str:
        return sha256_obj([stage, model, effort, max_tokens, prompt_version, schema_hash, list(input_hashes)])

    def path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def get(self, key: str) -> dict | None:
        p = self.path(key)
        return json.loads(p.read_text()) if p.exists() else None

    def put(self, key: str, request: dict, response: dict) -> None:
        self.path(key).write_text(json.dumps({"request": request, "response": response}, indent=1, default=str))
```

`src/vt/providers/anthropic_.py`:

```python
from __future__ import annotations

import asyncio
import logging

from pydantic import BaseModel, ValidationError

from vt.config import ModelConfig
from vt.jsonl import sha256_obj
from vt.providers.base import VlmResult, text_block
from vt.providers.cache import CallCache

log = logging.getLogger(__name__)


class AnthropicProvider:
    def __init__(self, cfg: ModelConfig, cache: CallCache, client=None):
        if client is None:
            import anthropic

            client = anthropic.AsyncAnthropic()
        self.client = client
        self.cfg = cfg
        self.model = cfg.model
        self.cache = cache
        self.sem = asyncio.Semaphore(cfg.concurrency)

    async def complete(self, *, stage: str, system: str, blocks: list[dict], output_model: type[BaseModel], effort: str,
                       prompt_version: str, input_hashes: list[str]) -> VlmResult:
        schema_hash = sha256_obj(output_model.model_json_schema())
        key = CallCache.key(stage, self.model, effort, self.cfg.max_tokens, prompt_version, schema_hash, input_hashes)
        hit = self.cache.get(key)
        if hit is not None:
            resp = hit["response"]
            parsed = output_model.model_validate(resp["parsed"]) if resp.get("parsed") is not None else None
            return VlmResult(parsed, resp.get("error"), resp.get("usage", {}), resp.get("text"), True, resp.get("stop_reason"))
        async with self.sem:
            r = await self._call(system, blocks, output_model, effort, self.cfg.max_tokens)
            if r.stop_reason == "max_tokens":
                r = await self._call(system, blocks, output_model, effort, self.cfg.retry_max_tokens)
            if r.error and r.error.startswith("schema"):
                retry_blocks = blocks + [text_block(f"Your previous output was invalid: {r.error}. Return JSON that matches the schema exactly.")]
                r = await self._call(system, retry_blocks, output_model, effort, self.cfg.retry_max_tokens)
        self.cache.put(key, {"stage": stage, "model": self.model, "effort": effort, "prompt_version": prompt_version,
                             "schema_hash": schema_hash, "input_hashes": input_hashes},
                       {"parsed": r.parsed.model_dump() if r.parsed is not None else None, "error": r.error,
                        "usage": r.usage, "text": r.raw_text, "stop_reason": r.stop_reason})
        return r

    async def _call(self, system: str, blocks: list[dict], output_model: type[BaseModel], effort: str, max_tokens: int) -> VlmResult:
        try:
            resp = await self.client.messages.parse(
                model=self.model, max_tokens=max_tokens,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": blocks}],
                output_format=output_model, output_config={"effort": effort},
            )
        except (ValidationError, ValueError) as e:
            return VlmResult(None, f"schema: {str(e)[:500]}")
        except Exception as e:  # anthropic.APIError family: retried by the SDK; record and continue
            log.warning("model call failed: %s", e)
            return VlmResult(None, f"api: {type(e).__name__}: {str(e)[:300]}")
        u = resp.usage
        usage = {"input_tokens": getattr(u, "input_tokens", 0), "output_tokens": getattr(u, "output_tokens", 0),
                 "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
                 "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0}
        text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), None)
        if resp.stop_reason == "refusal":
            return VlmResult(None, "refusal", usage, text, False, "refusal")
        if resp.stop_reason == "max_tokens":
            return VlmResult(None, "max_tokens", usage, text, False, "max_tokens")
        parsed = getattr(resp, "parsed_output", None)
        if parsed is None:
            return VlmResult(None, "schema: no parsed output", usage, text, False, resp.stop_reason)
        return VlmResult(parsed, None, usage, text, False, resp.stop_reason)
```

`src/vt/providers/__init__.py`:

```python
from __future__ import annotations

from vt.config import Config
from vt.providers.base import VlmProvider, VlmResult, image_block, text_block  # noqa: F401
from vt.providers.cache import CallCache
from vt.run import Run


def get_provider(cfg: Config, run: Run) -> VlmProvider:
    from vt.providers.anthropic_ import AnthropicProvider

    return AnthropicProvider(cfg.model, CallCache(run.cache_dir))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_provider.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vt/providers tests/test_provider.py
git commit -m "feat: Anthropic provider with structured outputs, disk cache, retry ladder"
```

---

### Task 10: Stage 2c — perception call, validation by repair (§8.3, §15.1)

**Files:**
- Create: `src/vt/prompts/__init__.py`, `src/vt/prompts/stage2c.py`, `src/vt/perceive.py`
- Modify: `src/vt/cli.py` (add `perceive`)
- Test: `tests/test_perceive.py`

**Interfaces:**
- Produces: `prompts.stage2c.SYSTEM: str`, `VERSION = "s2c-v1"`; `build_blocks(rec: Stage1Record, ocr: OcrFrame, frame_png: Path, overlay_png: Path) -> list[dict]`; `repair(out: VlmPerception, mark_ids: list[str]) -> tuple[VlmPerception, int]`; `run_perceive(run, cfg, provider=None)` writing `perception.jsonl`.

- [ ] **Step 1: Write the failing tests**

`tests/test_perceive.py`:

```python
from vt.perceive import repair
from vt.schemas import VlmPerception, VlmRegion


def region(rid, rows, lines, parent=None):
    return VlmRegion(id=rid, kind="window", name=rid, app="x", parent=parent, conf=0.9, rows=rows, vlm_lines=lines)


def test_repair_missing_duplicate_unknown_and_lengths():
    out = VlmPerception(
        regions=[region("r1", [["l1"], ["l2", "l9"]], ["a", "b"]), region("r2", [["l2"], ["l3"]], ["c"], parent="zz")],
        focused_region="r7", focused_conf=0.5, description="", unassigned_line_ids=[])
    fixed, n = repair(out, ["l1", "l2", "l3", "l4"])
    r1, r2 = fixed.regions
    assert r1.rows == [["l1"], ["l2"]]            # unknown l9 dropped
    assert r2.rows == [["l3"]] and r2.vlm_lines == ["c"]  # duplicate l2 dropped from the later region; lengths aligned
    assert fixed.unassigned_line_ids == ["l4"]     # missing mark appended
    assert fixed.focused_region is None and r2.parent is None
    assert n == 5
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_perceive.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.perceive`.

- [ ] **Step 3: Write the implementation**

`src/vt/prompts/__init__.py`: empty.

`src/vt/prompts/stage2c.py`:

```python
VERSION = "s2c-v1"

SYSTEM = """You transcribe and structure screenshots of computer tutorials (terminals, code editors, browsers, dialogs).

You are shown the same screenshot twice. Image 1 is the clean frame. Image 2 is the same frame with numbered boxes drawn around detected text lines; each number sits beside its box and is NOT part of the screen's text. Transcribe from Image 1; use Image 2 only to know which number refers to which line. A number is written as a mark id: l1, l2, ...

Produce a JSON object with these fields.

regions: the screen as a tree of regions: windows (top-level application windows), panes (areas inside a window: editor, terminal pane, navigation, content blade, toolbar, title bar), and popups (menus, dialogs, tooltips, toasts). Name each region and its application. Every mark id must appear in exactly one row of exactly one region, or in unassigned_line_ids.

rows: within a region, its visual lines in reading order. A row is one visual line: text that sits on one line (a prompt and its command, a table's cells, tabs side by side, a label and its value) is one row, listed left to right. A line the boxes missed is an empty row []. Do not put marks from different lines in one row.

vlm_lines: the verbatim text of each row, one entry per row, same order and length as rows. Preserve case, punctuation, whitespace and symbols exactly as displayed. Never correct, complete, or normalize commands, code, paths, or identifiers. Use ? for any character you cannot resolve. Do not omit rows. Icons are not text: do not transcribe them.

focused_region, focused_conf, focused_cues: the window with keyboard focus, your 0-1 confidence, and the visual cues you used (title bar highlight, caret visible, dialog modality).

occludes: for each region, the ids of regions it visually covers, in whole or in part.

description: anything the rows cannot express: selections, highlights, toggles, icons, diagram relationships, dialogs, animating regions.

Marks listed as animating are inside regions that were changing continuously when the frame was captured; their text is low confidence — say so rather than guessing."""
```

`src/vt/perceive.py`:

```python
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from vt.config import Config, config_hash
from vt.jsonl import sha256_file, write_jsonl
from vt.prompts import stage2c
from vt.providers import get_provider, image_block, text_block
from vt.providers.base import VlmProvider
from vt.run import Run
from vt.schemas import OcrFrame, PerceptionRecord, Stage1Record, VlmPerception

log = logging.getLogger(__name__)


def build_blocks(rec: Stage1Record, ocr: OcrFrame, frame_png: Path, overlay_png: Path) -> list[dict]:
    ids = [ln.id for ln in ocr.lines]
    animating = [ln.id for ln in ocr.lines if ln.in_churn]
    blocks = [
        text_block(f"Image 1 (clean frame {rec.frame}, t={rec.t_settled:.2f}s):"), image_block(frame_png),
        text_block("Image 2 (same frame with numbered boxes):"), image_block(overlay_png),
        text_block(f"Marks present: {', '.join(ids) if ids else 'none'}."),
    ]
    if animating:
        blocks.append(text_block(f"Marks inside animating regions (low confidence): {', '.join(animating)}."))
    if not rec.settled:
        blocks.append(text_block("This frame was captured while the screen was still changing (not settled)."))
    blocks.append(text_block("Return the JSON object."))
    return blocks


def repair(out: VlmPerception, mark_ids: list[str]) -> tuple[VlmPerception, int]:
    """§8.3: validation by repair, never by abort. Returns the repaired output and the number of repairs."""
    known = set(mark_ids)
    region_ids = {r.id for r in out.regions}
    repairs = 0
    seen: set[str] = set()
    for r in out.regions:
        new_rows: list[list[str]] = []
        for row in r.rows:
            kept: list[str] = []
            for m in row:
                if m not in known or m in seen:
                    repairs += 1
                    continue
                seen.add(m)
                kept.append(m)
            new_rows.append(kept)
        r.rows = new_rows
        if len(r.vlm_lines) != len(r.rows):
            repairs += 1
            n = min(len(r.vlm_lines), len(r.rows))
            r.rows, r.vlm_lines = r.rows[:n], r.vlm_lines[:n]
        if r.parent is not None and r.parent not in region_ids:
            r.parent = None
            repairs += 1
    unassigned = [m for m in out.unassigned_line_ids if m in known and m not in seen]
    seen.update(unassigned)
    for m in mark_ids:
        if m not in seen:
            unassigned.append(m)
            repairs += 1
    out.unassigned_line_ids = unassigned
    if out.focused_region is not None and out.focused_region not in region_ids:
        out.focused_region = None
        repairs += 1
    return out, repairs


async def _perceive_all(run: Run, cfg: Config, provider: VlmProvider) -> list[PerceptionRecord]:
    s1 = {r.frame: r for r in run.load_stage1()}
    clashes = run.manifest_read().get("overlay_clashes", {})

    async def one(of: OcrFrame) -> PerceptionRecord:
        rec = s1[of.frame]
        frame_png = run.root / rec.png
        overlay_png = run.overlays_dir / f"{of.frame:05d}.png"
        blocks = build_blocks(rec, of, frame_png, overlay_png)
        res = await provider.complete(stage="stage2c", system=stage2c.SYSTEM, blocks=blocks, output_model=VlmPerception,
                                      effort=cfg.model.effort_stage2c, prompt_version=stage2c.VERSION,
                                      input_hashes=[rec.sha256, sha256_file(overlay_png)])
        out, repairs = (repair(res.parsed, [ln.id for ln in of.lines]) if res.parsed is not None else (None, 0))
        return PerceptionRecord(frame=of.frame, model=provider.model, prompt_version=stage2c.VERSION, output=out,
                                error=res.error, usage=res.usage, repairs=repairs, label_clashes=int(clashes.get(str(of.frame), 0)))

    return list(await asyncio.gather(*(one(of) for of in run.load_ocr())))


def run_perceive(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None:
    inputs = [run.ocr]
    ch = config_hash(cfg, "model") + stage2c.VERSION
    if run.stage_up_to_date("perceive", inputs, ch):
        log.info("perceive up to date")
        return
    provider = provider or get_provider(cfg, run)
    records = asyncio.run(_perceive_all(run, cfg, provider))
    records.sort(key=lambda r: r.frame)
    write_jsonl(run.perception, records)
    usage = {k: sum(r.usage.get(k, 0) for r in records) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens")}
    run.stage_done("perceive", inputs, ch, frames=len(records), errors=sum(r.error is not None for r in records),
                   repairs=sum(r.repairs for r in records), usage=usage, model=provider.model)
```

Add to `cli.py`:

```python
@app.command()
def perceive(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 2c: VLM grouping and transcription → perception.jsonl."""
    _setup_logging(verbose)
    from vt.perceive import run_perceive
    run_perceive(Run(run_dir), load_config(config))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_perceive.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vt/prompts src/vt/perceive.py src/vt/cli.py tests/test_perceive.py
git commit -m "feat: Stage 2c perception with two-image prompt and repair validation"
```

---

### Task 11: Stage 3 — rows, alignment, agreement, layout_conf, focus (§9)

**Files:**
- Create: `src/vt/merge.py`
- Modify: `src/vt/cli.py` (add `merge`)
- Test: `tests/test_merge.py`

**Interfaces:**
- Consumes: `Stage1Record`, `OcrFrame`, `PerceptionRecord` (Tasks 1, 7, 10); `norm`, `similarity`, `levenshtein` (Task 2).
- Produces: `build_region_lines(vr: VlmRegion, ocr_by_id, cfg) -> tuple[list[Line], int, list[tuple[int, str]]]` (lines, rows_rejected, pending VLM texts for repair); `align_repair(lines, pending, cfg) -> None`; `agreement(ocr, vlm, cfg) -> tuple[bool, str | None]`; `region_bbox(region_id, regions) -> BBox | None`; `layout_conf(region, regions) -> float`; `caret_region(caret, regions) -> str | None`; `combine_focus(caret_region, retro_region, vlm_region, vlm_conf) -> tuple[str | None, float | None, list[str]]`; `merge_frame(s1, ocr, perc, cfg) -> FrameRecord`; `run_merge(run, cfg)` writing `frames.jsonl`.

- [ ] **Step 1: Write the failing tests**

`tests/test_merge.py`:

```python
from vt.config import MergeConfig
from vt.merge import agreement, build_region_lines, caret_region, combine_focus, layout_conf, merge_frame
from vt.schemas import (Line, OcrFrame, OcrLine, PerceptionRecord, Region, Stage1Record, VlmPerception, VlmRegion)

CFG = MergeConfig()


def ocr(id, x0, y0, x1, y1, text):
    return OcrLine(id=id, bbox=(x0, y0, x1, y1), text=text, conf=1.0)


def test_rows_join_fragments_and_reject_implausible_rows():
    by_id = {l.id: l for l in [ocr("l1", 10, 40, 60, 58, "PS C:\\src>"), ocr("l2", 70, 40, 200, 58, "git status"),
                                ocr("l3", 10, 60, 120, 78, "On branch main"), ocr("l4", 10, 400, 80, 418, "far away")]}
    vr = VlmRegion(id="r1", kind="window", name="Terminal", app="Windows Terminal", parent=None, conf=0.9,
                   rows=[["l1", "l2"], ["l3"], ["l4", "l1"], []],
                   vlm_lines=["PS C:\\src> git status", "On branch main", "nonsense", "nothing to commit"])
    lines, rejected, pending = build_region_lines(vr, by_id, CFG)
    assert lines[0].marks == ["l1", "l2"] and lines[0].ocr == "PS C:\\src> git status" and lines[0].bbox == (10, 40, 200, 58)
    assert lines[0].agree is True
    assert lines[1].agree is True
    assert rejected == 1
    assert [l.row_rejected for l in lines].count(True) == 2  # l4 and (duplicate) l1 split back into single-mark lines
    assert pending == [(2, "nonsense")]
    vlm_only = [l for l in lines if l.marks == []]
    assert len(vlm_only) == 1 and vlm_only[0].vlm == "nothing to commit" and vlm_only[0].bbox is None and vlm_only[0].agree is None


def test_agreement_glyph_strip_and_short_lines():
    assert agreement("P Search resources", "Search resources", CFG) == (True, "P")
    assert agreement("Learn more B'", "Learn more", CFG) == (True, "B'")
    assert agreement("• Zone 1", "Zone 1", CFG) == (True, "•")
    assert agreement("git status", "git status", CFG) == (True, None)
    assert agreement("On branch maln", "On branch main", CFG) == (False, None)


def test_layout_conf_does_not_penalize_foreground_over_background():
    term = Region(id="r1", kind="window", name="Terminal", app="T", parent=None, bbox=(12, 40, 640, 300), conf=0.95, layout_conf=0,
                  occludes=["r2"], lines=[Line(id="l3", marks=["l3"], bbox=(12, 40, 300, 58), ocr="a", ocr_conf=1, vlm="a", agree=True, in_churn=False),
                                          Line(id="l4", marks=["l4"], bbox=(12, 60, 540, 78), ocr="b", ocr_conf=1, vlm="b", agree=True, in_churn=False)])
    browser = Region(id="r2", kind="window", name="Portal", app="B", parent=None, bbox=(0, 0, 1920, 1080), conf=0.9, layout_conf=0,
                     lines=[Line(id="l1", marks=["l1"], bbox=(64, 17, 181, 33), ocr="Azure", ocr_conf=1, vlm="Azure", agree=True, in_churn=False),
                            Line(id="l9", marks=["l9"], bbox=(20, 1000, 200, 1018), ocr="z", ocr_conf=1, vlm="z", agree=True, in_churn=False)])
    assert layout_conf(term, [term, browser]) >= 0.9
    # interleaved text from an unrelated region on the same rows is penalized
    other = Region(id="r3", kind="pane", name="x", app="B", parent="r2", bbox=(300, 40, 500, 78), conf=0.9, layout_conf=0,
                   lines=[Line(id="l7", marks=["l7"], bbox=(300, 42, 500, 58), ocr="q", ocr_conf=1, vlm="q", agree=True, in_churn=False)])
    assert layout_conf(term, [term, browser, other]) <= 0.7
    single = Region(id="r4", kind="pane", name="s", app="B", parent=None, bbox=(0, 0, 10, 10), conf=0.95, layout_conf=0,
                    lines=[Line(id="l8", marks=["l8"], bbox=(0, 0, 10, 10), ocr="s", ocr_conf=1, vlm="s", agree=True, in_churn=False)])
    assert layout_conf(single, [single]) <= 0.6


def test_caret_region_and_focus_combination():
    term = Region(id="r1", kind="window", name="T", app="T", parent=None, bbox=(12, 40, 640, 300), conf=0.9, layout_conf=0.9,
                  lines=[Line(id="l3", marks=["l3"], bbox=(12, 40, 300, 58), ocr="a", ocr_conf=1, vlm="a", agree=True, in_churn=False)])
    pane = Region(id="r3", kind="pane", name="p", app="T", parent="r1", bbox=(12, 60, 300, 78), conf=0.9, layout_conf=0.9,
                  lines=[Line(id="l4", marks=["l4"], bbox=(12, 60, 300, 78), ocr="b", ocr_conf=1, vlm="b", agree=True, in_churn=False)])
    assert caret_region((318, 41, 2, 18), [term, pane]) == "r1"    # inside, compared at root-window level
    assert caret_region((20, 90, 2, 18), [term, pane]) == "r1"     # just below the pane: within two line heights
    assert caret_region((900, 900, 2, 18), [term, pane]) is None
    assert combine_focus("r1", None, "r1", 0.8) == ("r1", 0.9, ["caret", "vlm"])
    assert combine_focus("r1", None, None, 0.0) == ("r1", 0.7, ["caret"])
    assert combine_focus("r1", None, "r2", 0.8) == ("r1", 0.6, ["caret", "vlm:r2@0.3"])
    assert combine_focus("r1", "r2", "r2", 0.8) == ("r2", 0.6, ["retro", "vlm"])
    assert combine_focus(None, None, "r2", 0.8) == ("r2", 0.5, ["vlm"])
    assert combine_focus(None, None, None, 0.0) == (None, None, [])


def test_merge_frame_end_to_end_with_perception_error_falls_back_to_ocr_only():
    s1 = Stage1Record(video_id="v", frame=3, t_change=1, t_settled=1.2, t_end=5, settled=True, width=100, height=100, sha256="x", png="frames/00003.png")
    of = OcrFrame(frame=3, engine="e", lines=[ocr("l1", 0, 0, 50, 10, "hello"), ocr("l2", 0, 20, 50, 30, "world")])
    perc = PerceptionRecord(frame=3, model="m", prompt_version="v", output=None, error="refusal")
    fr = merge_frame(s1, of, perc, CFG)
    assert fr.error == "refusal" and len(fr.regions) == 1 and [l.ocr for l in fr.regions[0].lines] == ["hello", "world"]
    assert fr.regions[0].kind == "unknown"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_merge.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.merge`.

- [ ] **Step 3: Write the implementation**

`src/vt/merge.py`:

```python
from __future__ import annotations

import logging
import statistics

from vt.config import Config, MergeConfig, config_hash
from vt.jsonl import write_jsonl
from vt.run import Run
from vt.schemas import (BBox, FrameRecord, Line, OcrFrame, OcrLine, PerceptionRecord, Region, Stage1Record, VlmPerception,
                        VlmRegion)
from vt.textdiff import levenshtein, norm, similarity

log = logging.getLogger(__name__)


# ---------- geometry ----------
def union(boxes: list[BBox]) -> BBox | None:
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def _h(b: BBox) -> int:
    return b[3] - b[1]


def _median_h(boxes: list[BBox], default: float = 16.0) -> float:
    hs = [_h(b) for b in boxes if b is not None and _h(b) > 0]
    return float(statistics.median(hs)) if hs else default


# ---------- agreement (§9.2) ----------
def agreement(ocr: str, vlm: str, cfg: MergeConfig) -> tuple[bool, str | None]:
    if norm(ocr) == norm(vlm):
        return True, None
    toks = ocr.split()
    if len(toks) >= 2:
        if len(toks[0]) <= cfg.glyph_max_len and norm(" ".join(toks[1:])) == norm(vlm):
            return True, toks[0]
        if len(toks[-1]) <= cfg.glyph_max_len and norm(" ".join(toks[:-1])) == norm(vlm):
            return True, toks[-1]
    return False, None


def _matches(ocr: str, vlm: str, cfg: MergeConfig) -> bool:
    if similarity(ocr, vlm) >= cfg.align_sim:
        return True
    return min(len(norm(ocr)), len(norm(vlm))) <= cfg.align_short_len and levenshtein(ocr, vlm) <= cfg.align_short_lev


def _make_line(marks: list[OcrLine], vlm: str | None, cfg: MergeConfig, row_rejected: bool = False) -> Line:
    text = " ".join(m.text for m in marks)
    agree, stripped = (None, None)
    if vlm is not None:
        agree, stripped = agreement(text, vlm, cfg)
    return Line(id=marks[0].id, marks=[m.id for m in marks], bbox=union([m.bbox for m in marks]), ocr=text,
                ocr_conf=min(m.conf for m in marks), vlm=vlm, agree=agree, in_churn=any(m.in_churn for m in marks),
                ocr_glyph_stripped=stripped, confusable=any(m.confusable for m in marks), row_rejected=row_rejected)


# ---------- rows (§9.0) ----------
def build_region_lines(vr: VlmRegion, ocr_by_id: dict[str, OcrLine], cfg: MergeConfig) -> tuple[list[Line], int, list[tuple[int, str]]]:
    marks_all = [ocr_by_id[m] for row in vr.rows for m in row if m in ocr_by_id]
    med_h = _median_h([m.bbox for m in marks_all])
    lines: list[Line] = []
    rejected = 0
    pending: list[tuple[int, str]] = []
    seen: set[str] = set()
    vcount = 0
    for k, row in enumerate(vr.rows):
        vtext = vr.vlm_lines[k] if k < len(vr.vlm_lines) else None
        ms = [ocr_by_id[m] for m in row if m in ocr_by_id and m not in seen]
        if not row or not ms:
            if vtext is not None:
                vcount += 1
                lines.append(Line(id=f"v{vcount}", marks=[], bbox=None, ocr=None, ocr_conf=None, vlm=vtext, agree=None, in_churn=None))
            continue
        ms.sort(key=lambda m: m.bbox[0])
        plausible = _row_plausible(ms, med_h, cfg) and len(ms) == len(row)  # a duplicated or unknown mark makes the row implausible
        if plausible:
            lines.append(_make_line(ms, vtext, cfg))
            seen.update(m.id for m in ms)
        else:
            rejected += 1
            for m in ms:
                lines.append(_make_line([m], None, cfg, row_rejected=True))
                seen.add(m.id)
            if vtext is not None:
                pending.append((len(lines) - len(ms), vtext))
    return lines, rejected, pending


def _row_plausible(ms: list[OcrLine], med_h: float, cfg: MergeConfig) -> bool:
    ycs = [(m.bbox[1] + m.bbox[3]) / 2 for m in ms]
    if max(ycs) - min(ycs) > cfg.row_y_tol * med_h:
        return False
    for a, b in zip(ms, ms[1:]):
        if b.bbox[0] - a.bbox[2] > cfg.row_gap_lines * med_h:
            return False
    return True


def align_repair(lines: list[Line], pending: list[tuple[int, str]], cfg: MergeConfig) -> None:
    """LCS-style repair: match pending VLM texts to lines that have no VLM text (rejected rows), in order."""
    if not pending:
        return
    free = [l for l in lines if l.vlm is None and l.ocr is not None]
    texts = [t for _, t in pending]
    i = j = 0
    while i < len(free) and j < len(texts):
        matched = False
        for take in (1, 2, 3):
            cand = " ".join(texts[j:j + take])
            if j + take <= len(texts) and _matches(free[i].ocr, cand, cfg):
                free[i].vlm = cand
                free[i].agree, free[i].ocr_glyph_stripped = agreement(free[i].ocr, cand, cfg)
                j += take
                matched = True
                break
        if not matched:
            if similarity(free[i].ocr, texts[j]) < 0.3 and i + 1 < len(free) and _matches(free[i + 1].ocr, texts[j], cfg):
                i += 1
                continue
            j += 1
            continue
        i += 1


# ---------- regions (§9.1, §9.3) ----------
def _children(rid: str, regions: list[Region]) -> list[Region]:
    return [r for r in regions if r.parent == rid]


def region_bbox(rid: str, regions: list[Region]) -> BBox | None:
    r = next(x for x in regions if x.id == rid)
    boxes = [l.bbox for l in r.lines if l.bbox]
    for c in _children(rid, regions):
        cb = region_bbox(c.id, regions)
        if cb:
            boxes.append(cb)
    return union(boxes)


def _related(a: Region, b: Region, regions: list[Region]) -> bool:
    by_id = {r.id: r for r in regions}

    def ancestors(r: Region) -> set[str]:
        out, p = set(), r.parent
        while p and p in by_id:
            out.add(p)
            p = by_id[p].parent
        return out

    return a.id in ancestors(b) or b.id in ancestors(a) or a.id in b.occludes or b.id in a.occludes


def layout_conf(region: Region, regions: list[Region]) -> float:
    score = region.conf
    lines = [l for l in region.lines if l.bbox]
    if not lines or region.bbox is None:
        return round(min(score, 0.5), 3)
    penalty = 0.0
    for other in regions:
        if other.id == region.id or _related(region, other, regions):
            continue
        olines = [l for l in other.lines if l.bbox]
        hit = False
        for l in lines:
            for m in olines:
                v = min(l.bbox[3], m.bbox[3]) - max(l.bbox[1], m.bbox[1])
                hz = min(l.bbox[2], m.bbox[2]) - max(l.bbox[0], m.bbox[0])
                if v >= 0.5 * _h(l.bbox) and hz > 0:
                    hit = True
                    break
            if hit:
                break
        if hit:
            penalty += 0.3
    score -= min(penalty, 0.6)
    med = _median_h([l.bbox for l in lines])
    coverage = (len(lines) * med) / max(_h(region.bbox), 1)
    if coverage < 0.3:
        score -= 0.2
    if len(lines) == 1:
        score = min(score, 0.6)
    return round(max(0.0, min(1.0, score)), 3)


# ---------- focus (§9.4) ----------
def _root(rid: str, regions: list[Region]) -> str:
    by_id = {r.id: r for r in regions}
    while by_id[rid].parent and by_id[rid].parent in by_id:
        rid = by_id[rid].parent
    return rid


def caret_region(caret: BBox | None, regions: list[Region]) -> str | None:
    if caret is None:
        return None
    cx, cy = caret[0] + caret[2] / 2, caret[1] + caret[3] / 2
    best, best_d = None, None
    for r in regions:
        if r.bbox is None:
            continue
        lh = _median_h([l.bbox for l in r.lines if l.bbox])
        x0, y0, x1, y1 = r.bbox[0] - lh, r.bbox[1] - lh, r.bbox[2] + lh, r.bbox[3] + lh
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            d = 0.0
        else:
            dx = max(r.bbox[0] - cx, 0, cx - r.bbox[2])
            dy = max(r.bbox[1] - cy, 0, cy - r.bbox[3])
            d = (dx * dx + dy * dy) ** 0.5
            if d > 2 * lh:
                continue
        if best_d is None or d < best_d:
            best, best_d = r.id, d
    return _root(best, regions) if best else None


def combine_focus(caret_r: str | None, retro_r: str | None, vlm_r: str | None, vlm_conf: float) -> tuple[str | None, float | None, list[str]]:
    computed = retro_r or caret_r
    if caret_r and retro_r and caret_r != retro_r:
        computed = retro_r
    if computed:
        signals = [s for s, v in (("caret", caret_r), ("retro", retro_r)) if v == computed]
        if vlm_r is None:
            return computed, 0.7, signals
        if vlm_r == computed:
            return computed, 0.9, signals + ["vlm"]
        if caret_r and retro_r and caret_r != retro_r:
            return computed, 0.6, signals + ["vlm"] if vlm_r == computed else signals + [f"vlm:{vlm_r}@0.3"]
        return computed, 0.6, signals + [f"vlm:{vlm_r}@0.3"]
    if vlm_r:
        return vlm_r, 0.5, ["vlm"]
    return None, None, []


# ---------- frame merge ----------
def merge_frame(s1: Stage1Record, of: OcrFrame, perc: PerceptionRecord, cfg: MergeConfig) -> FrameRecord:
    ocr_by_id = {l.id: l for l in of.lines}
    regions: list[Region] = []
    rows_rejected = 0
    unassigned: list[Line] = []
    description = ""
    vlm_focus, vlm_conf = None, 0.0
    out: VlmPerception | None = perc.output
    if out is None:
        lines = [_make_line([l], None, cfg) for l in sorted(of.lines, key=lambda l: (l.bbox[1], l.bbox[0]))]
        regions = [Region(id="r1", kind="unknown", name="screen", app="unknown", parent=None, bbox=union([l.bbox for l in lines]),
                          conf=0.0, layout_conf=0.0, lines=lines)]
    else:
        for vr in out.regions:
            lines, rej, pending = build_region_lines(vr, ocr_by_id, cfg)
            align_repair(lines, pending, cfg)
            rows_rejected += rej
            regions.append(Region(id=vr.id, kind=vr.kind, name=vr.name, app=vr.app, parent=vr.parent, bbox=None, conf=vr.conf,
                                  layout_conf=0.0, occludes=list(vr.occludes), lines=lines))
        for r in regions:
            r.bbox = region_bbox(r.id, regions)
        for r in regions:
            r.layout_conf = layout_conf(r, regions)
        unassigned = [_make_line([ocr_by_id[m]], None, cfg) for m in out.unassigned_line_ids if m in ocr_by_id]
        description = out.description
        vlm_focus, vlm_conf = out.focused_region, out.focused_conf
    focused, fconf, signals = combine_focus(caret_region(s1.caret, regions), None, vlm_focus, vlm_conf)
    return FrameRecord(video_id=s1.video_id, frame=s1.frame, t_change=s1.t_change, t_settled=s1.t_settled, t_end=s1.t_end,
                       settled=s1.settled, png=s1.png, overlay=f"overlays/{s1.frame:05d}.png", sha256=s1.sha256, width=s1.width,
                       height=s1.height, churn_regions=s1.churn_regions, caret=s1.caret, focused_region=focused, focused_conf=fconf,
                       focused_signals=signals, description=description, regions=regions, unassigned_lines=unassigned,
                       grouping_repairs=perc.repairs, rows_rejected=rows_rejected, label_clashes=perc.label_clashes,
                       vlm_model=perc.model, prompt_version=perc.prompt_version, error=perc.error)


def run_merge(run: Run, cfg: Config) -> None:
    inputs = [run.stage1, run.ocr, run.perception]
    ch = config_hash(cfg, "merge")
    if run.stage_up_to_date("merge", inputs, ch):
        log.info("merge up to date")
        return
    s1 = {r.frame: r for r in run.load_stage1()}
    ocr = {f.frame: f for f in run.load_ocr()}
    percs = {p.frame: p for p in run.load_perception()}
    records = [merge_frame(s1[f], ocr[f], percs.get(f, PerceptionRecord(frame=f, model="", prompt_version="", output=None, error="missing")), cfg.merge)
               for f in sorted(s1) if f in ocr]
    write_jsonl(run.frames, records)
    lines = [l for r in records for reg in r.regions for l in reg.lines]
    run.stage_done("merge", inputs, ch, frames=len(records), lines=len(lines),
                   agree=sum(1 for l in lines if l.agree), ocr_only=sum(1 for l in lines if l.vlm is None and l.ocr),
                   vlm_only=sum(1 for l in lines if l.ocr is None), rows_rejected=sum(r.rows_rejected for r in records))
```

Add to `cli.py`:

```python
@app.command()
def merge(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 3: merge OCR and VLM output → frames.jsonl."""
    _setup_logging(verbose)
    from vt.merge import run_merge
    run_merge(Run(run_dir), load_config(config))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_merge.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vt/merge.py src/vt/cli.py tests/test_merge.py
git commit -m "feat: Stage 3 merge with VLM rows, agreement, layout_conf and focus"
```

---

### Task 12: Region correspondence and Stage 4 line diff (§11.1, §11.2)

**Files:**
- Create: `src/vt/correspond.py`, `src/vt/diff.py`
- Test: `tests/test_correspond.py`, `tests/test_diff.py`

**Interfaces:**
- Produces: `correspond(prev: FrameRecord, cur: FrameRecord, cfg: DiffConfig) -> Correspondence`; `diff_region(prev_lines, cur_lines, cfg) -> list[DiffOp]`; `diff_pair(prev, cur, cfg) -> Transition` (id assigned later by the caller; `kind` `single` or `unsettled`; `t = (prev.t_end, cur.t_settled)`; `computed_diff` keyed by cur region id, `r0` for unassigned lines).

- [ ] **Step 1: Write the failing tests**

`tests/test_correspond.py`:

```python
from vt.config import DiffConfig
from vt.correspond import correspond, score
from vt.schemas import FrameRecord, Line, Region


def ln(i, text, y):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(10, y, 300, y + 18), ocr=text, ocr_conf=1, vlm=text, agree=True, in_churn=False)


def reg(rid, name, app, lines, bbox):
    return Region(id=rid, kind="window", name=name, app=app, parent=None, bbox=bbox, conf=0.9, layout_conf=0.9, lines=lines)


def frame(n, regions):
    return FrameRecord(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=True, png="", overlay=None,
                       sha256="", width=1920, height=1080, regions=regions)


def test_correspondence_by_text_survives_renaming_and_growth():
    a = frame(1, [reg("r1", "Windows Terminal — pwsh", "Windows Terminal", [ln(1, "PS> ls", 40)], (10, 40, 300, 58)),
                  reg("r2", "Azure Portal", "Browser", [ln(5, "Home", 10)], (10, 10, 300, 28))])
    b = frame(2, [reg("r9", "Azure Portal", "Browser", [ln(5, "Home", 10)], (10, 10, 300, 28)),
                  reg("r4", "Terminal", "Windows Terminal", [ln(1, "PS> ls", 40)] + [ln(10 + k, f"line {k}", 60 + 18 * k) for k in range(30)], (10, 40, 300, 600))])
    c = correspond(a, b, DiffConfig())
    assert sorted((m[0], m[1]) for m in c.matched) == [("r1", "r4"), ("r2", "r9")]
    assert c.appeared == [] and c.disappeared == []


def test_empty_regions_match_only_on_app_and_name():
    a = frame(1, [reg("r1", "Toolbar", "App", [], None)])
    b = frame(2, [reg("r2", "Toolbar", "App", [], None), reg("r3", "Other", "App", [], None)])
    c = correspond(a, b, DiffConfig())
    assert [(m[0], m[1]) for m in c.matched] == [("r1", "r2")]
    assert c.appeared == ["r3"]
```

`tests/test_diff.py`:

```python
from vt.config import DiffConfig
from vt.diff import diff_pair, diff_region
from vt.schemas import FrameRecord, Line, Region


def ln(i, text, y, agree=True, vlm=None):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(10, y, 300, y + 18), ocr=text, ocr_conf=1, vlm=vlm or text, agree=agree, in_churn=False)


def reg(rid, lines):
    return Region(id=rid, kind="window", name="T", app="T", parent=None, bbox=(10, 40, 300, 400), conf=0.9, layout_conf=0.9, lines=lines)


def frame(n, regions, unassigned=(), settled=True):
    return FrameRecord(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=settled, png="", overlay=None,
                       sha256="", width=1920, height=1080, regions=regions, unassigned_lines=list(unassigned))


def test_diff_region_modify_insert_and_uncertain():
    prev = [ln(1, "PS> gi", 40), ln(2, "old", 60, agree=False, vlm="o1d")]
    cur = [ln(1, "PS> git status", 40), ln(2, "old", 60, agree=False, vlm="o1d"), ln(3, "On branch main", 80)]
    ops = diff_region(prev, cur, DiffConfig())
    assert [o.op for o in ops] == ["modify", "insert"]
    assert ops[0].new == "PS> git status" and ops[0].char_diff == [["=", "PS> gi"], ["+", "t status"]]
    assert ops[1].new == "On branch main" and ops[1].new_index == 2 and ops[1].y == 80


def test_diff_pair_builds_transition_with_r0_and_unsettled_kind():
    a = frame(1, [reg("r1", [ln(1, "a", 40)])], unassigned=[ln(9, "stray", 900)])
    b = frame(2, [reg("r1", [ln(1, "a", 40), ln(2, "b", 60)])], unassigned=[ln(9, "stray2", 900)], settled=False)
    t = diff_pair(a, b, DiffConfig())
    assert t.kind == "unsettled" and t.t == (2.0, 2.1) and (t.from_frame, t.to_frame) == (1, 2)
    assert "r1" in t.computed_diff and t.computed_diff["r1"].from_region == "r1"
    assert [o.op for o in t.computed_diff["r1"].ops] == ["insert"]
    assert [o.op for o in t.computed_diff["r0"].ops] == ["modify"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_correspond.py tests/test_diff.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

`src/vt/correspond.py`:

```python
from __future__ import annotations

from vt.config import DiffConfig
from vt.detect import iou
from vt.schemas import Correspondence, FrameRecord, Region
from vt.textdiff import norm


def _texts(r: Region) -> set[str]:
    return {norm(l.fused) for l in r.lines if l.fused}


def score(a: Region, b: Region, cfg: DiffConfig) -> float:
    ta, tb = _texts(a), _texts(b)
    j = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    i = iou(a.bbox, b.bbox) if a.bbox and b.bbox else 0.0
    app = float(norm(a.app).lower() == norm(b.app).lower())
    name = float(norm(a.name).lower() == norm(b.name).lower())
    return cfg.corr_w_text * j + cfg.corr_w_iou * i + cfg.corr_w_app * app + cfg.corr_w_name * name


def correspond(prev: FrameRecord, cur: FrameRecord, cfg: DiffConfig) -> Correspondence:
    pa = [r for r in prev.regions if r.lines]
    pb = [r for r in cur.regions if r.lines]
    pairs = sorted(((score(a, b, cfg), a.id, b.id) for a in pa for b in pb), reverse=True)
    used_a: set[str] = set()
    used_b: set[str] = set()
    matched: list[tuple[str, str, float]] = []
    for s, ia, ib in pairs:
        if s < cfg.corr_accept or ia in used_a or ib in used_b:
            continue
        matched.append((ia, ib, round(s, 3)))
        used_a.add(ia)
        used_b.add(ib)
    ea = [r for r in prev.regions if not r.lines]
    eb = [r for r in cur.regions if not r.lines]
    for a in ea:
        for b in eb:
            if b.id in used_b:
                continue
            if norm(a.app).lower() == norm(b.app).lower() and norm(a.name).lower() == norm(b.name).lower():
                matched.append((a.id, b.id, 1.0))
                used_a.add(a.id)
                used_b.add(b.id)
                break
    matched.sort(key=lambda m: m[1])
    disappeared = [r.id for r in prev.regions if r.id not in used_a]
    appeared = [r.id for r in cur.regions if r.id not in used_b]
    return Correspondence(matched=matched, appeared=appeared, disappeared=disappeared)
```

`src/vt/diff.py`:

```python
from __future__ import annotations

import statistics

from vt.config import DiffConfig
from vt.correspond import correspond
from vt.schemas import DiffOp, FrameRecord, Line, RegionDiff, Transition
from vt.textdiff import line_ops, pair_modifies


def _ys(lines: list[Line]) -> list[int]:
    ys: list[int] = []
    last = 0
    for l in lines:
        if l.bbox is not None:
            last = l.bbox[1]
        ys.append(last)
    return ys


def _line_h(lines: list[Line]) -> float:
    hs = [l.bbox[3] - l.bbox[1] for l in lines if l.bbox]
    return float(statistics.median(hs)) if hs else 16.0


def diff_region(prev: list[Line], cur: list[Line], cfg: DiffConfig) -> list[DiffOp]:
    p = [l.fused for l in prev]
    c = [l.fused for l in cur]
    ops = pair_modifies(line_ops(p, c), _ys(prev), _ys(cur), _line_h(prev + cur), cfg.modify_sim)
    for o in ops:
        src = []
        if o.old_index is not None:
            src.append(prev[o.old_index])
        if o.new_index is not None:
            src.append(cur[o.new_index])
        o.uncertain = any(l.uncertain for l in src)
        o.in_churn = any(bool(l.in_churn) for l in src)
    return ops


def diff_pair(prev: FrameRecord, cur: FrameRecord, cfg: DiffConfig) -> Transition:
    corr = correspond(prev, cur, cfg)
    computed: dict[str, RegionDiff] = {}
    for a, b, _ in corr.matched:
        ops = diff_region(prev.region(a).lines, cur.region(b).lines, cfg)
        if ops:
            computed[b] = RegionDiff(from_region=a, ops=ops)
    r0 = diff_region(prev.unassigned_lines, cur.unassigned_lines, cfg)
    if r0:
        computed["r0"] = RegionDiff(from_region="r0", ops=r0)
    kind = "unsettled" if not (prev.settled and cur.settled) else "single"
    return Transition(id="", from_frame=prev.frame, to_frame=cur.frame, t=(prev.t_end, cur.t_settled), kind=kind,
                      regions=corr, computed_diff=computed)
```

`DiffOp.in_churn` (declared in Task 1) is set here and read by the coalescing rules in Task 13.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_correspond.py tests/test_diff.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vt/correspond.py src/vt/diff.py tests/test_correspond.py tests/test_diff.py
git commit -m "feat: region correspondence and Stage 4 line diff"
```

---

### Task 13: Stage 4b — transients, coalescing, trivial transitions, retrospective focus (§11.3–§11.5, §9.4)

**Files:**
- Create: `src/vt/coalesce.py`
- Modify: `src/vt/cli.py` (add `diff`)
- Test: `tests/test_coalesce.py`

**Interfaces:**
- Consumes: `diff_pair`, `correspond` (Task 12), `combine_focus`, `caret_region` (Task 11).
- Produces: `merge_transients(frames, singles, cfg) -> list[Transition]`; `coalesce(frames, transitions, cfg) -> list[Transition]`; `tag_trivial(t) -> Transition`; `retrospective_focus(frames, transitions) -> list[FocusRecord]`; `assign_ids(transitions)`; `run_diff(run, cfg)` writing `transitions.jsonl` and `focus.jsonl`.

- [ ] **Step 1: Write the failing tests**

`tests/test_coalesce.py`:

```python
from vt.coalesce import coalesce, merge_transients, retrospective_focus, tag_trivial
from vt.config import DiffConfig
from vt.diff import diff_pair
from vt.schemas import FrameRecord, Line, Region

CFG = DiffConfig()


def ln(i, text, y):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(10, y, 300, y + 18), ocr=text, ocr_conf=1, vlm=text, agree=True, in_churn=False)


def term(lines, rid="r1"):
    return Region(id=rid, kind="window", name="Terminal", app="T", parent=None, bbox=(10, 40, 300, 400), conf=0.9, layout_conf=0.9, lines=lines)


def frame(n, regions, t0=None):
    t0 = n * 2.0 if t0 is None else t0
    return FrameRecord(video_id="v", frame=n, t_change=t0, t_settled=t0 + 0.2, t_end=t0 + 2.0, settled=True, png="", overlay=None,
                       sha256="", width=1920, height=1080, regions=regions)


def singles(frames):
    ts = [diff_pair(a, b, CFG) for a, b in zip(frames, frames[1:])]
    for i, t in enumerate(ts):
        t.id = f"T{i}"
    return ts


def test_typing_then_output_becomes_one_command_transition():
    frames = [frame(0, [term([ln(1, "PS> ", 40)])]),
              frame(1, [term([ln(1, "PS> git", 40)])]),
              frame(2, [term([ln(1, "PS> git stat", 40)])]),
              frame(3, [term([ln(1, "PS> git status", 40)])]),
              frame(4, [term([ln(1, "PS> git status", 40), ln(2, "On branch main", 60)])]),
              frame(5, [term([ln(1, "PS> git status", 40), ln(2, "On branch main", 60), ln(3, "clean", 80)])])]
    out = coalesce(frames, singles(frames), CFG)
    assert len(out) == 1
    t = out[0]
    assert (t.from_frame, t.to_frame) == (0, 5) and t.kind == "coalesced" and t.intermediate_frames == [1, 2, 3, 4]
    assert [e.type for e in t.events] == ["typed", "output_appended"]
    assert t.events[0].text == "git status" and t.events[0].line == "PS> git status" and t.events[0].frames == (0, 3)
    assert t.events[1].lines == 2 and t.events[1].text == "On branch main\nclean" and t.events[1].frames == (3, 5)
    assert t.t == (frames[0].t_end, frames[5].t_settled)
    assert [o.op for o in t.computed_diff["r1"].ops] == ["modify", "insert", "insert"]


def test_backspace_and_scrolloff_are_tolerated():
    frames = [frame(0, [term([ln(1, "PS> git stauts", 40)])]),
              frame(1, [term([ln(1, "PS> git status", 40)])]),
              frame(2, [term([ln(1, "PS> git status", 40), ln(2, "x1", 60), ln(3, "x2", 80)])]),
              frame(3, [term([ln(2, "x1", 40), ln(3, "x2", 60), ln(4, "x3", 80)])])]
    out = coalesce(frames, singles(frames), CFG)
    assert len(out) == 1 and [e.type for e in out[0].events] == ["typed", "output_appended"]
    assert out[0].events[1].lines == 3


def test_transient_toast_is_merged_across_three_frames():
    toast = Region(id="r5", kind="popup", name="toast", app="Editor", parent=None, bbox=(800, 900, 1000, 930), conf=0.9, layout_conf=0.9,
                   lines=[ln(20, "Saved", 900)])
    frames = [frame(0, [term([ln(1, "code", 40)])]), frame(1, [term([ln(1, "code", 40)]), toast], t0=2.0),
              frame(2, [term([ln(1, "code", 40)])], t0=3.0)]
    out = merge_transients(frames, singles(frames), CFG)
    assert len(out) == 1 and out[0].kind == "transient_merged" and out[0].intermediate_frames == [1]
    assert out[0].transient.name == "toast" and abs(out[0].transient.hold_s - 1.0) < 1e-6


def test_clock_only_transition_is_trivial():
    frames = [frame(0, [term([ln(1, "Tue 14:02", 40)])]), frame(1, [term([ln(1, "Tue 14:03", 40)])])]
    t = tag_trivial(singles(frames)[0])
    assert t.kind == "trivial"


def test_retrospective_focus_attributes_typing_to_from_frame():
    frames = [frame(0, [term([ln(1, "PS> ", 40)])]), frame(1, [term([ln(1, "PS> ls", 40)])])]
    frames[0].focused_region, frames[0].focused_conf, frames[0].focused_signals = None, None, []
    out = coalesce(frames, singles(frames), CFG)
    focus = retrospective_focus(frames, out)
    assert focus[0].frame == 0 and focus[0].focused_region == "r1" and focus[0].focused_conf == 0.7 and focus[0].focused_signals == ["retro"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_coalesce.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.coalesce`.

- [ ] **Step 3: Write the implementation**

`src/vt/coalesce.py`:

```python
from __future__ import annotations

import logging

from vt.config import Config, DiffConfig, config_hash
from vt.diff import diff_pair
from vt.jsonl import write_jsonl
from vt.merge import caret_region, combine_focus
from vt.run import Run
from vt.schemas import DiffOp, Event, FocusRecord, FrameRecord, Transition, TransientInfo
from vt.textdiff import lcp_len, norm

log = logging.getLogger(__name__)


# ---------- helpers ----------
def _other_ops_ok(t: Transition, region: str) -> bool:
    for rid, rd in t.computed_diff.items():
        if rid == region:
            continue
        if any(not (o.in_churn or o.clock) for o in rd.ops):
            return False
    return True


def _typed_op(t: Transition, region: str, cfg: DiffConfig) -> DiffOp | None:
    rd = t.computed_diff.get(region)
    if rd is None or len(rd.ops) != 1 or rd.ops[0].op != "modify":
        return None
    o = rd.ops[0]
    a, b = norm(o.old or ""), norm(o.new or "")
    if lcp_len(a, b) >= len(a) - cfg.typed_tolerance and len(b) >= len(a) - cfg.typed_tolerance and _other_ops_ok(t, region):
        return o
    return None


def _output_ops(t: Transition, region: str, prev_count: int, cur_count: int) -> list[DiffOp] | None:
    rd = t.computed_diff.get(region)
    if rd is None or not rd.ops:
        return None
    dels = [o for o in rd.ops if o.op == "delete"]
    ins = [o for o in rd.ops if o.op == "insert"]
    if len(dels) + len(ins) != len(rd.ops) or not ins:
        return None
    if any(o.old_index != k for k, o in enumerate(dels)):
        return None
    if any(o.new_index < cur_count - len(ins) for o in ins):
        return None
    if not _other_ops_ok(t, region):
        return None
    return ins


def _follow(t_next: Transition, region_in_prev_to: str) -> str | None:
    for a, b, _ in t_next.regions.matched:
        if a == region_in_prev_to:
            return b
    return None


def _kind(members: list[Transition]) -> str:
    if any(m.kind == "unsettled" for m in members):
        return "unsettled"
    return "coalesced"


def _build(frames_by_id: dict[int, FrameRecord], members: list[Transition], events: list[Event], cfg: DiffConfig) -> Transition:
    first, last = members[0], members[-1]
    t = diff_pair(frames_by_id[first.from_frame], frames_by_id[last.to_frame], cfg)
    t.intermediate_frames = [m.from_frame for m in members[1:]] if len(members) > 1 else []
    t.intermediate_frames = sorted(set(t.intermediate_frames) | {f for m in members for f in m.intermediate_frames})
    t.kind = _kind(members)
    if len(members) == 1 and members[0].kind == "transient_merged":
        t.kind = "transient_merged"
        t.transient = members[0].transient
    t.events = events
    return t


# ---------- §11.4 transients ----------
def merge_transients(frames: list[FrameRecord], singles: list[Transition], cfg: DiffConfig) -> list[Transition]:
    by_id = {f.frame: f for f in frames}
    out: list[Transition] = []
    i = 0
    while i < len(singles):
        t1 = singles[i]
        t2 = singles[i + 1] if i + 1 < len(singles) else None
        merged = None
        if t2 is not None and t1.to_frame == t2.from_frame:
            mid = by_id[t1.to_frame]
            nxt = by_id[t2.to_frame]
            nxt_texts = {norm(l.fused) for r in nxt.regions for l in r.lines}
            for rid in t1.regions.appeared:
                if rid in t2.regions.disappeared:
                    region = mid.region(rid)
                    texts = {norm(l.fused) for l in region.lines if l.fused}
                    if texts and texts & nxt_texts:
                        continue
                    hold = nxt.t_change - mid.t_change
                    if hold < cfg.transient_max_s:
                        merged = diff_pair(by_id[t1.from_frame], nxt, cfg)
                        merged.kind = "transient_merged"
                        merged.intermediate_frames = [mid.frame]
                        merged.transient = TransientInfo(frame=mid.frame, region=rid, name=region.name, hold_s=round(hold, 3))
                        break
        if merged is not None:
            out.append(merged)
            i += 2
        else:
            out.append(t1)
            i += 1
    return out


# ---------- §11.3 coalescing ----------
def coalesce(frames: list[FrameRecord], transitions: list[Transition], cfg: DiffConfig) -> list[Transition]:
    by_id = {f.frame: f for f in frames}
    out: list[Transition] = []
    i = 0
    while i < len(transitions):
        t = transitions[i]
        typed_run: list[Transition] = []
        region: str | None = None
        first_old: str | None = None
        last_new: str | None = None
        for rid in t.computed_diff:
            o = _typed_op(t, rid, cfg)
            if o is not None:
                region, first_old, last_new = rid, o.old or "", o.new or ""
                typed_run = [t]
                break
        j = i + 1
        cur_region = region
        while typed_run and j < len(transitions):
            nxt = transitions[j]
            if nxt.from_frame != typed_run[-1].to_frame:
                break
            nr = _follow(nxt, cur_region)
            o = _typed_op(nxt, nr, cfg) if nr else None
            if o is None or norm(o.old or "") != norm(last_new or ""):
                break
            typed_run.append(nxt)
            cur_region, last_new = nr, o.new or ""
            j += 1
        output_run: list[Transition] = []
        out_region = cur_region
        k = j if typed_run else i
        while k < len(transitions):
            nxt = transitions[k]
            if output_run and nxt.from_frame != output_run[-1].to_frame:
                break
            if not output_run and not typed_run:
                cand_regions = list(nxt.computed_diff)
            else:
                nr = _follow(nxt, out_region) if (output_run or typed_run) else None
                cand_regions = [nr] if nr else []
            found = None
            for rid in cand_regions:
                if rid == "r0":
                    continue
                prev_f, cur_f = by_id[nxt.from_frame], by_id[nxt.to_frame]
                from_rid = nxt.computed_diff[rid].from_region
                ins = _output_ops(nxt, rid, len(prev_f.region(from_rid).lines) if from_rid and prev_f.region(from_rid) else 0,
                                  len(cur_f.region(rid).lines))
                if ins is not None:
                    found = (rid, ins)
                    break
            if found is None:
                break
            out_region = found[0]
            output_run.append(nxt)
            k += 1
        if typed_run or output_run:
            members = typed_run + output_run
            events: list[Event] = []
            if typed_run:
                text = last_new[lcp_len(first_old or "", last_new):] if last_new else ""
                events.append(Event(type="typed", region=cur_region, text=text, line=last_new,
                                    frames=(typed_run[0].from_frame, typed_run[-1].to_frame)))
            if output_run:
                lines: list[str] = []
                for m in output_run:
                    rid = next((r for r in m.computed_diff if m.computed_diff[r].ops and all(o.op in ("insert", "delete") for o in m.computed_diff[r].ops) and r != "r0"), None)
                    if rid:
                        lines += [o.new for o in m.computed_diff[rid].ops if o.op == "insert" and o.new is not None]
                events.append(Event(type="output_appended", region=out_region, lines=len(lines), text="\n".join(lines),
                                    frames=(output_run[0].from_frame, output_run[-1].to_frame)))
            if len(members) == 1 and not (typed_run and output_run):
                t1 = members[0]
                t1.events = events
                out.append(t1)
            else:
                out.append(_build(by_id, members, events, cfg))
            i = k
            continue
        out.append(t)
        i += 1
    return out


# ---------- trivial (§11.2) ----------
def tag_trivial(t: Transition) -> Transition:
    ops = [o for rd in t.computed_diff.values() for o in rd.ops]
    if ops and all(o.clock for o in ops) and not t.regions.appeared and not t.regions.disappeared and t.kind == "single":
        t.kind = "trivial"
    return t


# ---------- retrospective focus (§9.4) ----------
def retrospective_focus(frames: list[FrameRecord], transitions: list[Transition]) -> list[FocusRecord]:
    by_id = {f.frame: f for f in frames}
    out: list[FocusRecord] = []
    for t in transitions:
        typed = next((e for e in t.events if e.type == "typed"), None)
        if typed is None or t.regions.appeared:
            continue
        from_region = t.computed_diff.get(typed.region).from_region if typed.region in t.computed_diff else None
        if from_region is None:
            continue
        f = by_id[t.from_frame]
        vlm_r = next((s for s in f.focused_signals if s == "vlm"), None)
        vlm_region = f.focused_region if ("vlm" in f.focused_signals and f.focused_region) else None
        root = from_region
        by_rid = {r.id: r for r in f.regions}
        while by_rid.get(root) and by_rid[root].parent in by_rid:
            root = by_rid[root].parent
        region, conf, signals = combine_focus(caret_region(f.caret, f.regions), root, vlm_region, f.focused_conf or 0.0)
        out.append(FocusRecord(frame=f.frame, focused_region=region, focused_conf=conf, focused_signals=signals))
    return out


def assign_ids(transitions: list[Transition]) -> None:
    for i, t in enumerate(transitions, start=1):
        t.id = f"T{i}"


def run_diff(run: Run, cfg: Config) -> None:
    inputs = [run.frames]
    ch = config_hash(cfg, "diff")
    if run.stage_up_to_date("diff", inputs, ch):
        log.info("diff up to date")
        return
    frames = run.load_frames()
    singles = [diff_pair(a, b, cfg.diff) for a, b in zip(frames, frames[1:])]
    ts = merge_transients(frames, singles, cfg.diff)
    ts = coalesce(frames, ts, cfg.diff)
    ts = [tag_trivial(t) for t in ts]
    assign_ids(ts)
    write_jsonl(run.transitions, ts)
    write_jsonl(run.focus, retrospective_focus(frames, ts))
    run.stage_done("diff", inputs, ch, transitions=len(ts), trivial=sum(t.kind == "trivial" for t in ts),
                   coalesced=sum(t.kind == "coalesced" for t in ts), transient=sum(t.kind == "transient_merged" for t in ts))
```

Add to `cli.py`:

```python
@app.command()
def diff(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 4/4b: diffs, transients, coalescing → transitions.jsonl, focus.jsonl."""
    _setup_logging(verbose)
    from vt.coalesce import run_diff
    run_diff(Run(run_dir), load_config(config))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_coalesce.py -v`
Expected: 5 passed. The coalescing loop is the most intricate code in the plan; when a test fails, print `[(t.from_frame, t.to_frame, {r: [(o.op, o.old, o.new) for o in d.ops] for r, d in t.computed_diff.items()}) for t in singles]` and check the run boundaries against Rules 1, 2, 1b in §11.3 before changing the rules themselves.

- [ ] **Step 5: Commit**

```bash
git add src/vt/coalesce.py src/vt/cli.py tests/test_coalesce.py
git commit -m "feat: Stage 4b transients, coalescing, trivial transitions, retrospective focus"
```

---

### Task 14: Stage 5 — transition interpretation (§12, §15.2)

**Files:**
- Create: `src/vt/prompts/stage5.py`, `src/vt/interpret.py`
- Modify: `src/vt/cli.py` (add `interpret`)
- Test: `tests/test_interpret.py`

**Interfaces:**
- Produces: `render_transition_line(t, frames_by_id) -> str`; `render_diff(t, frames_by_id) -> str`; `build_blocks(t, frames_by_id, run, chapter, previous: list[Transition]) -> list[dict]`; `validate_refs(refs: list[str], frames: list[FrameRecord]) -> tuple[list[str], int]`; `run_interpret(run, cfg, provider=None)` writing `interpretations.jsonl`.

- [ ] **Step 1: Write the failing tests**

`tests/test_interpret.py`:

```python
from vt.interpret import render_diff, render_transition_line, validate_refs
from vt.schemas import DiffOp, Event, FrameRecord, Line, Region, RegionDiff, Transition


def ln(i, text, y, agree=True, vlm=None):
    return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(10, y, 300, y + 18), ocr=text, ocr_conf=1, vlm=vlm or text, agree=agree, in_churn=False)


def frame(n, lines):
    reg = Region(id="r1", kind="window", name="Terminal", app="Windows Terminal", parent=None, bbox=(10, 40, 300, 400), conf=0.9, layout_conf=0.4, lines=lines)
    return FrameRecord(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=True, png="", overlay=None, sha256="", width=1, height=1, regions=[reg])


def test_render_diff_shows_both_readings_and_uncertain_grouping():
    a = frame(1, [ln(1, "PS> gi", 40)])
    b = frame(2, [ln(1, "PS> git status", 40), ln(2, "On branch maln", 60, agree=False, vlm="On branch main")])
    t = Transition(id="T1", from_frame=1, to_frame=2, t=(2.0, 2.1), kind="single",
                   computed_diff={"r1": RegionDiff(from_region="r1", ops=[DiffOp(op="modify", old="PS> gi", new="PS> git status", old_index=0, new_index=0, y=40),
                                                                       DiffOp(op="insert", new="On branch maln", new_index=1, y=60, uncertain=True)])},
                   events=[Event(type="typed", region="r1", text="t status", line="PS> git status", frames=(1, 2))])
    text = render_diff(t, {1: a, 2: b})
    assert "Terminal" in text and "modify" in text and "PS> git status" in text
    assert "OCR: On branch maln" in text and "VLM: On branch main" in text
    assert "grouping uncertain" in text
    assert 'typed "t status"' in render_transition_line(t, {1: a, 2: b})


def test_validate_refs_drops_unknown_frames_and_lines():
    a = frame(1, [ln(1, "x", 40)])
    b = frame(2, [ln(1, "x", 40), ln(2, "y", 60)])
    valid, bad = validate_refs(["2:l2", "1:l1", "3:l1", "2:l9", "junk"], [a, b])
    assert valid == ["2:l2", "1:l1"] and bad == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_interpret.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.interpret`.

- [ ] **Step 3: Write the implementation**

`src/vt/prompts/stage5.py`:

```python
VERSION = "s5-v1"

SYSTEM = """You interpret changes between two consecutive screen states of a computer tutorial.

You are shown two screenshots (Frame a, then Frame b), optionally a transient frame that appeared between them, and an exact computed list of text changes between them. The computed list is authoritative for text: do not restate its strings with alterations. Where two readings of a line disagree (OCR vs VLM), quote both and assert neither.

Return a JSON object:
action: the single user action that best explains the change (typed, clicked, selected, navigated, pressed a key). If none is evident, say so.
result: what visibly changed as a consequence, including non-textual changes visible in the images (a checkbox toggled, a row highlighted, a dialog opened).
description: anything else visible and relevant.
confidence: 0-1.
refs.lines: the line references your statements rest on, as "<frame>:<line_id>" using the frame numbers given, e.g. "16:l3"."""
```

`src/vt/interpret.py`:

```python
from __future__ import annotations

import asyncio
import logging

from vt.config import Config, config_hash
from vt.jsonl import sha256_obj, write_jsonl
from vt.prompts import stage5
from vt.providers import get_provider, image_block, text_block
from vt.providers.base import VlmProvider
from vt.run import Run
from vt.schemas import FrameRecord, Interpretation, OutlineChapter, Transition, VlmInterpretation, VlmRefs

log = logging.getLogger(__name__)


def _region_name(f: FrameRecord, rid: str) -> str:
    if rid == "r0":
        return "unassigned lines"
    r = f.region(rid)
    return f"{r.app}: {r.name}" if r else rid


def render_transition_line(t: Transition, frames: dict[int, FrameRecord]) -> str:
    b = frames[t.to_frame]
    parts = []
    for e in t.events:
        name = _region_name(b, e.region)
        if e.type == "typed":
            parts.append(f'{name}: typed "{e.text}"')
        elif e.type == "output_appended":
            parts.append(f"{name}: {e.lines} lines appended")
    if not parts:
        n = sum(len(rd.ops) for rd in t.computed_diff.values())
        parts.append(f"{n} text changes" + (f"; appeared: {', '.join(_region_name(b, r) for r in t.regions.appeared)}" if t.regions.appeared else ""))
    return f"{t.id} [f{t.from_frame}→f{t.to_frame}, {t.t[0]:.1f}–{t.t[1]:.1f}s] " + "; ".join(parts)


def render_diff(t: Transition, frames: dict[int, FrameRecord]) -> str:
    a, b = frames[t.from_frame], frames[t.to_frame]
    out = []
    if t.regions.appeared:
        out.append("Regions that appeared in frame b: " + ", ".join(_region_name(b, r) for r in t.regions.appeared))
    if t.regions.disappeared:
        out.append("Regions that disappeared after frame a: " + ", ".join(_region_name(a, r) for r in t.regions.disappeared))
    for rid, rd in t.computed_diff.items():
        reg = b.region(rid)
        head = _region_name(b, rid)
        if reg is not None and reg.layout_conf < 0.5:
            head += " (grouping uncertain; text may belong to an adjacent window)"
        out.append(f"Region {head}:")
        for o in rd.ops:
            flag = " [uncertain reading]" if o.uncertain else ""
            churn = " [region was animating]" if o.in_churn else ""
            if o.op == "modify":
                out.append(f'  modify: "{o.old}" -> "{o.new}"{flag}{churn}')
            elif o.op == "insert":
                out.append(f'  insert: "{o.new}"{flag}{churn}')
            else:
                out.append(f'  delete: "{o.old}"{flag}{churn}')
            src = None
            if o.new_index is not None and reg is not None and o.new_index < len(reg.lines):
                src = reg.lines[o.new_index]
            if src is not None and src.agree is False and src.ocr and src.vlm:
                out.append(f"    readings disagree — OCR: {src.ocr} | VLM: {src.vlm}")
    for e in t.events:
        if e.type == "typed":
            out.append(f'Coalesced event: typed "{e.text}" (line now: "{e.line}") over frames {e.frames[0]}→{e.frames[1]}')
        elif e.type == "output_appended":
            out.append(f"Coalesced event: {e.lines} output lines appended over frames {e.frames[0]}→{e.frames[1]}")
    if t.kind == "unsettled":
        out.append("One of these frames was captured while the screen was still changing.")
    return "\n".join(out) if out else "No text changes were computed; look for non-textual change."


def build_blocks(t: Transition, frames: dict[int, FrameRecord], run: Run, chapter: OutlineChapter | None, previous: list[Transition]) -> list[dict]:
    a, b = frames[t.from_frame], frames[t.to_frame]
    ctx = []
    if chapter is not None:
        ctx.append(f"Global outline chapter for this pair: {chapter.title} — {chapter.gist}")
    if previous:
        ctx.append("Preceding transitions:\n" + "\n".join(render_transition_line(p, frames) for p in previous))
    blocks = [text_block("\n".join(ctx) if ctx else "No preceding context.")]
    blocks += [text_block(f"Frame {a.frame} (t={a.t_settled:.2f}s):"), image_block(run.root / a.png)]
    if t.transient is not None:
        mid = frames[t.transient.frame]
        blocks += [text_block(f"Transient frame {mid.frame}: region '{t.transient.name}' appeared for {t.transient.hold_s:.1f}s between the two frames:"),
                   image_block(run.root / mid.png)]
    blocks += [text_block(f"Frame {b.frame} (t={b.t_settled:.2f}s):"), image_block(run.root / b.png)]
    blocks.append(text_block("Computed changes:\n" + render_diff(t, frames)))
    blocks.append(text_block("Return the JSON object."))
    return blocks


def validate_refs(refs: list[str], frames: list[FrameRecord]) -> tuple[list[str], int]:
    ids = {f.frame: f.line_ids() for f in frames}
    valid, bad = [], 0
    for r in refs:
        try:
            fr, lid = r.split(":", 1)
            if int(fr) in ids and lid in ids[int(fr)]:
                valid.append(r)
                continue
        except ValueError:
            pass
        bad += 1
    return valid, bad


async def _interpret_all(run: Run, cfg: Config, provider: VlmProvider) -> list[Interpretation]:
    frames_list = run.load_frames()
    frames = {f.frame: f for f in frames_list}
    ts = run.load_transitions()

    async def one(i: int, t: Transition) -> Interpretation:
        if t.kind == "trivial":
            return Interpretation(id=t.id, error="trivial")
        chapter = run.chapter_of(frames[t.to_frame].t_settled)
        blocks = build_blocks(t, frames, run, chapter, ts[max(0, i - 3):i])
        res = await provider.complete(stage="stage5", system=stage5.SYSTEM, blocks=blocks, output_model=VlmInterpretation,
                                      effort=cfg.model.effort_stage5, prompt_version=stage5.VERSION,
                                      input_hashes=[frames[t.from_frame].sha256, frames[t.to_frame].sha256, sha256_obj(t.model_dump())])
        if res.parsed is None:
            return Interpretation(id=t.id, error=res.error, model=provider.model, prompt_version=stage5.VERSION)
        p: VlmInterpretation = res.parsed
        scope = [frames[t.from_frame], frames[t.to_frame]] + ([frames[t.transient.frame]] if t.transient else [])
        valid, bad = validate_refs(p.refs.lines, scope)
        return Interpretation(id=t.id, action=p.action, result=p.result, description=p.description, confidence=p.confidence,
                              refs=VlmRefs(lines=valid), invalid_refs=bad, model=provider.model, prompt_version=stage5.VERSION)

    return list(await asyncio.gather(*(one(i, t) for i, t in enumerate(ts))))


def run_interpret(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None:
    inputs = [run.transitions, run.frames]
    ch = config_hash(cfg, "model") + stage5.VERSION
    if run.stage_up_to_date("interpret", inputs, ch):
        log.info("interpret up to date")
        return
    provider = provider or get_provider(cfg, run)
    records = asyncio.run(_interpret_all(run, cfg, provider))
    write_jsonl(run.interpretations, records)
    run.stage_done("interpret", inputs, ch, transitions=len(records), errors=sum(r.error not in (None, "trivial") for r in records),
                   invalid_refs=sum(r.invalid_refs for r in records), model=provider.model)
```

Add to `cli.py`:

```python
@app.command()
def interpret(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 5: VLM interpretation of each transition → interpretations.jsonl."""
    _setup_logging(verbose)
    from vt.interpret import run_interpret
    run_interpret(Run(run_dir), load_config(config))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_interpret.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vt/prompts/stage5.py src/vt/interpret.py src/vt/cli.py tests/test_interpret.py
git commit -m "feat: Stage 5 transition interpretation with validated refs"
```

---

### Task 15: Stage 6 — hierarchy (§13, §15.3)

**Files:**
- Create: `src/vt/prompts/stage6.py`, `src/vt/hierarchy.py`
- Modify: `src/vt/cli.py` (add `hierarchy`)
- Test: `tests/test_hierarchy.py`

**Interfaces:**
- Produces: `repair_boundaries(segments: list[SegmentStart], ids: list[str]) -> list[tuple[int, str]]` (sorted `(start_index, label)`, first forced to 0); `fallback_segments(n_items, size) -> list[tuple[int, str]]`; `window_ranges(n, window, overlap) -> list[tuple[int, int]]`; `merge_window_boundaries(per_window: list[tuple[int, int, list[tuple[int, str]]]], n, overlap) -> list[tuple[int, str]]`; `propagate(children: list[HierNode | Transition]) -> tuple[tuple[int,int], tuple[float,float]]`; `run_hierarchy(run, cfg, provider=None)` writing `steps.jsonl`, `sections.jsonl`, `video.json`.

- [ ] **Step 1: Write the failing tests**

`tests/test_hierarchy.py`:

```python
from vt.hierarchy import fallback_segments, merge_window_boundaries, propagate, repair_boundaries, window_ranges
from vt.schemas import HierNode, SegmentStart, Transition


def test_repair_boundaries_sorts_dedups_drops_unknown_and_forces_first():
    ids = [f"T{i}" for i in range(1, 11)]
    segs = [SegmentStart(start_id="T5", label="b"), SegmentStart(start_id="T9", label="c"), SegmentStart(start_id="T5", label="dup"),
            SegmentStart(start_id="T99", label="x")]
    assert repair_boundaries(segs, ids) == [(0, "segment 1"), (4, "b"), (8, "c")]
    assert repair_boundaries([], ids) == [(0, "segment 1")]


def test_fallback_and_windows():
    assert fallback_segments(45, 20) == [(0, "segment 1"), (20, "segment 2"), (40, "segment 3")]
    assert window_ranges(10, 2000, 200) == [(0, 10)]
    assert window_ranges(5000, 2000, 200) == [(0, 2000), (1800, 3800), (3600, 5000)]


def test_merge_window_boundaries_keeps_non_overlap_and_agreed_overlap():
    per = [(0, 2000, [(0, "a"), (1000, "b"), (1900, "c")]), (1800, 3800, [(1800, "c?"), (1900, "c"), (2500, "d")])]
    out = merge_window_boundaries(per, 3800, 200)
    assert [s for s, _ in out] == [0, 1000, 1900, 2500]


def test_propagate_from_transitions_and_nodes():
    ts = [Transition(id="T1", from_frame=3, to_frame=5, t=(1.0, 2.0), kind="single"), Transition(id="T2", from_frame=5, to_frame=9, t=(2.5, 4.0), kind="single")]
    assert propagate(ts) == ((3, 9), (1.0, 4.0))
    steps = [HierNode(id="S1", level="step", children=("T1", "T2"), frames=(3, 9), t=(1.0, 4.0), label="l", description="d")]
    assert propagate(steps) == ((3, 9), (1.0, 4.0))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_hierarchy.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.hierarchy`.

- [ ] **Step 3: Write the implementation**

`src/vt/prompts/stage6.py`:

```python
VERSION = "s6-v1"

BOUNDARY_SYSTEM = """You segment an ordered list of items from a computer tutorial into coherent units.

Each line is one item: its id, its frame range and time range, and a one-line summary. Output only the ids at which a new segment begins, with a short label for the segment that starts there. A segment is a coherent unit of work a tutorial reader would follow as one step (for steps) or one topic (for sections). The first item always begins the first segment. Use ids exactly as listed; do not invent ids."""

ELABORATE_SYSTEM = """You describe one segment of a computer tutorial for a reader who will follow it.

You are given the segment's items in full and the screen state at its start and end. Return a short label and a description. Every sentence of the description must carry, in square brackets, the ids of the items it rests on, e.g. [T13]. Quote commands, paths and identifiers exactly as given; do not paraphrase or correct them. List every cited id in refs."""
```

`src/vt/hierarchy.py`:

```python
from __future__ import annotations

import asyncio
import json
import logging
from typing import Sequence

from vt.config import Config, HierarchyConfig, config_hash
from vt.interpret import render_transition_line
from vt.jsonl import sha256_obj, write_jsonl
from vt.prompts import stage6
from vt.providers import get_provider, text_block
from vt.providers.base import VlmProvider
from vt.run import Run
from vt.schemas import FrameRecord, HierNode, Interpretation, SegmentStart, Transition, VlmBoundaries, VlmElaboration

log = logging.getLogger(__name__)


# ---------- pure helpers ----------
def repair_boundaries(segments: list[SegmentStart], ids: list[str]) -> list[tuple[int, str]]:
    pos = {i: k for k, i in enumerate(ids)}
    starts: dict[int, str] = {}
    for s in segments:
        k = pos.get(s.start_id)
        if k is not None and k not in starts:
            starts[k] = s.label
    if 0 not in starts:
        starts[0] = "segment 1"
    return sorted(starts.items())


def fallback_segments(n: int, size: int) -> list[tuple[int, str]]:
    return [(k, f"segment {k // size + 1}") for k in range(0, n, size)]


def window_ranges(n: int, window: int, overlap: int) -> list[tuple[int, int]]:
    if n <= window:
        return [(0, n)]
    out, start = [], 0
    while True:
        end = min(start + window, n)
        out.append((start, end))
        if end == n:
            return out
        start = end - overlap


def merge_window_boundaries(per_window: list[tuple[int, int, list[tuple[int, str]]]], n: int, overlap: int) -> list[tuple[int, str]]:
    found: dict[int, tuple[str, int]] = {}
    for wi, (ws, we, bounds) in enumerate(per_window):
        prev_overlap_end = ws + overlap if wi > 0 else ws
        next_overlap_start = we - overlap if wi < len(per_window) - 1 else we
        for s, label in bounds:
            in_overlap = s < prev_overlap_end or s >= next_overlap_start
            if not in_overlap:
                found[s] = (label, 2)
            else:
                strong = (s - ws >= 25) and (we - s >= 25)
                cur = found.get(s)
                votes = (cur[1] if cur else 0) + (1 if not strong else 2)
                found[s] = (label if not cur else cur[0], votes)
    out = [(s, lab) for s, (lab, v) in found.items() if v >= 2]
    if not out or out[0][0] != 0:
        out.append((0, "segment 1"))
    return sorted(set(out))


def propagate(children: Sequence[HierNode | Transition]) -> tuple[tuple[int, int], tuple[float, float]]:
    first, last = children[0], children[-1]
    f0 = first.from_frame if isinstance(first, Transition) else first.frames[0]
    f1 = last.to_frame if isinstance(last, Transition) else last.frames[1]
    return (f0, f1), (first.t[0], last.t[1])


# ---------- rendering ----------
def _item_line(item: HierNode | Transition, frames: dict[int, FrameRecord], interps: dict[str, Interpretation]) -> str:
    if isinstance(item, Transition):
        line = render_transition_line(item, frames)
        ip = interps.get(item.id)
        if ip and ip.action:
            line += f" — {ip.action}"
        return line
    return f"{item.id} [f{item.frames[0]}→f{item.frames[1]}, {item.t[0]:.1f}–{item.t[1]:.1f}s] {item.label}"


def _item_full(item: HierNode | Transition, frames: dict[int, FrameRecord], interps: dict[str, Interpretation]) -> str:
    if isinstance(item, Transition):
        ip = interps.get(item.id)
        parts = [render_transition_line(item, frames)]
        if ip and ip.action:
            parts.append(f"  action: {ip.action}\n  result: {ip.result}")
        return "\n".join(parts)
    return f"{item.id} {item.label}\n  {item.description}"


def _state_line(f: FrameRecord) -> str:
    names = ", ".join(f"{r.app}: {r.name}" for r in f.regions if r.parent is None)
    foc = f.region(f.focused_region).name if f.focused_region and f.region(f.focused_region) else "unknown"
    return f"frame {f.frame} (t={f.t_settled:.1f}s): windows [{names}]; focused: {foc}"


# ---------- level builder ----------
async def _boundaries(provider: VlmProvider, cfg: Config, level: str, lines: list[str], suggestion: str | None) -> tuple[list[SegmentStart] | None, str | None]:
    text = "\n".join(lines)
    if suggestion:
        text += "\n\nSuggested boundaries from a coarse outline (reconcile against the items; the items win):\n" + suggestion
    res = await provider.complete(stage=f"stage6-boundary-{level}", system=stage6.BOUNDARY_SYSTEM, blocks=[text_block(text)],
                                  output_model=VlmBoundaries, effort=cfg.model.effort_stage6, prompt_version=stage6.VERSION,
                                  input_hashes=[sha256_obj(text)])
    return (res.parsed.segments if res.parsed else None), res.error


async def _elaborate(provider: VlmProvider, cfg: Config, level: str, seg_id: str, items_text: str, start_state: str, end_state: str) -> VlmElaboration:
    text = f"Segment {seg_id}\nStart state: {start_state}\nEnd state: {end_state}\n\nItems:\n{items_text}"
    res = await provider.complete(stage=f"stage6-elaborate-{level}", system=stage6.ELABORATE_SYSTEM, blocks=[text_block(text)],
                                  output_model=VlmElaboration, effort=cfg.model.effort_stage6, prompt_version=stage6.VERSION,
                                  input_hashes=[sha256_obj(text)])
    if res.parsed is None:
        return VlmElaboration(label=seg_id, description=f"(elaboration failed: {res.error})", refs=[])
    return res.parsed


async def build_level(provider: VlmProvider, cfg: Config, level: str, prefix: str, items: list, frames: dict[int, FrameRecord],
                      interps: dict[str, Interpretation], suggestion: str | None, fallback_size: int) -> list[HierNode]:
    hc: HierarchyConfig = cfg.hierarchy
    ids = [it.id for it in items]
    lines = [_item_line(it, frames, interps) for it in items]
    per_window = []
    seg_conf = "high"
    for ws, we in window_ranges(len(items), hc.window, hc.overlap):
        segs, err = await _boundaries(provider, cfg, level, lines[ws:we], suggestion)
        if segs is None or len(segs) == 0:
            segs, err = await _boundaries(provider, cfg, level, lines[ws:we], suggestion)  # one re-prompt
        if segs is None:
            log.warning("boundary call failed for %s window %d-%d: %s; using fallback", level, ws, we, err)
            bounds = [(ws + k, lab) for k, lab in fallback_segments(we - ws, fallback_size)]
            seg_conf = "low"
        else:
            bounds = [(ws + k, lab) for k, lab in repair_boundaries(segs, ids[ws:we])]
        per_window.append((ws, we, bounds))
    bounds = merge_window_boundaries(per_window, len(items), hc.overlap) if len(per_window) > 1 else per_window[0][2]
    starts = [s for s, _ in bounds] + [len(items)]
    nodes: list[HierNode] = []
    tasks = []
    for k, (s, label) in enumerate(bounds):
        e = starts[k + 1]
        chunk = items[s:e]
        frames_rng, t_rng = propagate(chunk)
        items_text = "\n".join(_item_full(it, frames, interps) for it in chunk)
        if len(chunk) > 80:  # map-reduce within the segment (§13.2)
            parts = [chunk[i:i + 60] for i in range(0, len(chunk), 60)]
            summaries = await asyncio.gather(*(_elaborate(provider, cfg, level, f"{prefix}{k + 1} part {p + 1}",
                                                          "\n".join(_item_full(it, frames, interps) for it in part),
                                                          _state_line(frames[part[0].from_frame if isinstance(part[0], Transition) else part[0].frames[0]]),
                                                          _state_line(frames[part[-1].to_frame if isinstance(part[-1], Transition) else part[-1].frames[1]]))
                                               for p, part in enumerate(parts)))
            items_text = "\n".join(f"part {p + 1}: {s_.description}" for p, s_ in enumerate(summaries))
        tasks.append(_elaborate(provider, cfg, level, f"{prefix}{k + 1}", items_text, _state_line(frames[frames_rng[0]]), _state_line(frames[frames_rng[1]])))
        nodes.append(HierNode(id=f"{prefix}{k + 1}", level=level, children=(chunk[0].id, chunk[-1].id), frames=frames_rng, t=t_rng,
                              label=label, description="", segmentation_conf=seg_conf))
    elabs = await asyncio.gather(*tasks)
    for node, el, (s, _) in zip(nodes, elabs, bounds):
        child_ids = {it.id for it in items[s:starts[bounds.index((s, _)) + 1]]}
        node.label = el.label or node.label
        node.description = el.description
        node.refs = [r for r in el.refs if r in child_ids]
    return nodes


async def _hierarchy(run: Run, cfg: Config, provider: VlmProvider) -> tuple[list[HierNode], list[HierNode], HierNode]:
    frames = {f.frame: f for f in run.load_frames()}
    interps = run.load_interpretations()
    ts = [t for t in run.load_transitions() if t.kind != "trivial"]
    steps = await build_level(provider, cfg, "step", "S", ts, frames, interps, None, cfg.hierarchy.fallback_step_transitions)
    outline = run.load_outline()
    suggestion = "\n".join(f"{c.start_s:.0f}s–{c.end_s:.0f}s: {c.title}" for c in outline) if outline else None
    sections = await build_level(provider, cfg, "section", "C", steps, frames, interps, suggestion, cfg.hierarchy.fallback_section_steps)
    frames_rng, t_rng = propagate(sections)
    el = await _elaborate(provider, cfg, "video", "video", "\n".join(_item_full(s, frames, interps) for s in sections),
                          _state_line(frames[frames_rng[0]]), _state_line(frames[frames_rng[1]]))
    video = HierNode(id="V", level="video", children=(sections[0].id, sections[-1].id), frames=frames_rng, t=t_rng,
                     label=el.label, description=el.description, refs=[r for r in el.refs if r in {s.id for s in sections}])
    return steps, sections, video


def run_hierarchy(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None:
    inputs = [run.transitions, run.interpretations, run.frames]
    ch = config_hash(cfg, "model", "hierarchy") + stage6.VERSION
    if run.stage_up_to_date("hierarchy", inputs, ch):
        log.info("hierarchy up to date")
        return
    if not run.load_transitions():
        log.warning("no transitions; skipping hierarchy")
        return
    provider = provider or get_provider(cfg, run)
    steps, sections, video = asyncio.run(_hierarchy(run, cfg, provider))
    write_jsonl(run.steps, steps)
    write_jsonl(run.sections, sections)
    run.video.write_text(video.model_dump_json(indent=2))
    run.stage_done("hierarchy", inputs, ch, steps=len(steps), sections=len(sections),
                   low_conf=sum(n.segmentation_conf == "low" for n in steps + sections))
```

Add to `cli.py`:

```python
@app.command()
def hierarchy(run_dir: Path, config: Path | None = None, verbose: bool = False):
    """Stage 6: steps, sections, video summary."""
    _setup_logging(verbose)
    from vt.hierarchy import run_hierarchy
    run_hierarchy(Run(run_dir), load_config(config))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_hierarchy.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vt/prompts/stage6.py src/vt/hierarchy.py src/vt/cli.py tests/test_hierarchy.py
git commit -m "feat: Stage 6 hierarchy with boundary repair and map-reduce elaboration"
```

---

### Task 16: Stage 7 — index and retrieval (§14, §20.10)

**Files:**
- Create: `src/vt/index.py`
- Modify: `src/vt/cli.py` (add `index`, `search`)
- Test: `tests/test_index.py`

**Interfaces:**
- Produces: `Node` (pydantic: `node_id, video_id, level, item_id, frames, t, apps, region_names, layout_conf, step_id, section_id, chapter_id, text, payload`); `extract_nodes(run) -> list[Node]`; `open_db(path) -> sqlite3.Connection` (schema created, sqlite-vec loaded); `index_nodes(db, nodes, embedder)`; `fts_query(query: str) -> str`; `trigram_query(query) -> str | None`; `rrf(rankings: list[list[str]], k: int) -> list[tuple[str, float]]`; `search(db, query, cfg, embedder=None, video_id=None, level=None, t_from=None, t_to=None, app=None) -> list[dict]`; `get_embedder(cfg) -> Embedder | None`; `build_index(run, cfg)`.

- [ ] **Step 1: Write the failing tests**

`tests/test_index.py`:

```python
from vt.config import IndexConfig
from vt.index import Node, fts_query, index_nodes, open_db, rrf, search, trigram_query


def node(i, text, level="transition", t=(0.0, 1.0), apps=("Windows Terminal",)):
    return Node(node_id=f"n{i}", video_id="v1", level=level, item_id=f"T{i}", frames=(i, i + 1), t=t, apps=list(apps),
                region_names=[], layout_conf=0.9, text=text, payload={"id": f"T{i}"})


def test_fts_query_quotes_every_term_and_trigram_needs_three_chars():
    assert fts_query('az aks create --resource-group "rg demo"') == '"az" OR "aks" OR "create" OR "--resource-group" OR "rg demo"'
    assert trigram_query("az") is None
    assert trigram_query("KodeKloud aks") == '"KodeKloud" OR "aks"'


def test_rrf_fuses_rankings():
    fused = rrf([["a", "b", "c"], ["b", "a"]], 60)
    assert [x for x, _ in fused][:2] == ["a", "b"] or [x for x, _ in fused][:2] == ["b", "a"]
    assert fused[0][1] > fused[-1][1]


def test_index_and_search_exact_identifiers_and_substrings(tmp_path):
    db = open_db(tmp_path / "i.sqlite")
    nodes = [node(1, "az aks create --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp", t=(10, 20)),
             node(2, "kubectl get nodes", t=(30, 40)),
             node(3, "Configure the storage account", level="step", t=(50, 60), apps=("Browser",))]
    index_nodes(db, nodes, None)
    cfg = IndexConfig()
    hits = search(db, "--resource-group", cfg)
    assert hits and hits[0]["node_id"] == "n1"
    hits = search(db, "KodeKloud", cfg)          # substring via trigram
    assert hits and hits[0]["node_id"] == "n1"
    hits = search(db, "storage", cfg, level="step")
    assert [h["node_id"] for h in hits] == ["n3"]
    hits = search(db, "kubectl", cfg, t_from=0, t_to=25)
    assert hits == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_index.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.index`.

- [ ] **Step 3: Write the implementation**

`src/vt/index.py`:

```python
from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from vt.config import Config, IndexConfig, config_hash
from vt.run import Run

log = logging.getLogger(__name__)


class Node(BaseModel):
    node_id: str
    video_id: str
    level: str
    item_id: str
    frames: tuple[int, int]
    t: tuple[float, float]
    apps: list[str] = []
    region_names: list[str] = []
    layout_conf: float = 1.0
    step_id: str | None = None
    section_id: str | None = None
    chapter_id: str | None = None
    text: str
    payload: dict = {}


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastembedEmbedder:
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding

        self._m = TextEmbedding(model)
        self.dim = len(next(iter(self._m.embed(["x"]))))

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._m.embed(texts)]


def get_embedder(cfg: IndexConfig) -> Embedder | None:
    if cfg.embedder == "fastembed":
        return FastembedEmbedder()
    return None


# ---------- schema ----------
def open_db(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(path))
    try:
        import sqlite_vec

        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
    except Exception as e:  # vector search unavailable; lexical still works
        log.warning("sqlite-vec unavailable: %s", e)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            node_id TEXT PRIMARY KEY, video_id TEXT, level TEXT, item_id TEXT, frame_start INTEGER, frame_end INTEGER,
            t_start REAL, t_end REAL, apps TEXT, region_names TEXT, layout_conf REAL, step_id TEXT, section_id TEXT,
            chapter_id TEXT, text TEXT, payload TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(text, node_id UNINDEXED, tokenize="unicode61 tokenchars '-_./:\\'");
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_tri USING fts5(text, node_id UNINDEXED, tokenize='trigram');
        """
    )
    return db


def _ensure_vec(db: sqlite3.Connection, dim: int) -> None:
    db.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS nodes_vec USING vec0(node_id TEXT PRIMARY KEY, embedding float[{dim}], level TEXT, video_id TEXT)")


def index_nodes(db: sqlite3.Connection, nodes: list[Node], embedder: Embedder | None) -> None:
    db.execute("DELETE FROM nodes")
    db.execute("DELETE FROM nodes_fts")
    db.execute("DELETE FROM nodes_tri")
    for n in nodes:
        db.execute("INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (n.node_id, n.video_id, n.level, n.item_id, n.frames[0], n.frames[1], n.t[0], n.t[1], json.dumps(n.apps),
                    json.dumps(n.region_names), n.layout_conf, n.step_id, n.section_id, n.chapter_id, n.text, json.dumps(n.payload)))
        db.execute("INSERT INTO nodes_fts(text, node_id) VALUES (?, ?)", (n.text, n.node_id))
        db.execute("INSERT INTO nodes_tri(text, node_id) VALUES (?, ?)", (n.text, n.node_id))
    if embedder is not None and nodes:
        import sqlite_vec

        _ensure_vec(db, embedder.dim)
        db.execute("DELETE FROM nodes_vec")
        for n, vec in zip(nodes, embedder.embed([n.text for n in nodes])):
            db.execute("INSERT INTO nodes_vec(node_id, embedding, level, video_id) VALUES (?,?,?,?)",
                       (n.node_id, sqlite_vec.serialize_float32(vec), n.level, n.video_id))
    db.commit()


# ---------- queries (§14.2) ----------
_TERM = re.compile(r'"([^"]+)"|(\S+)')


def _terms(query: str) -> list[str]:
    return [(a or b) for a, b in _TERM.findall(query)]


def fts_query(query: str) -> str:
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in _terms(query))


def trigram_query(query: str) -> str | None:
    terms = [t for t in _terms(query) if len(t) >= 3]
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in terms) if terms else None


def rrf(rankings: list[list[str]], k: int) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, node_id in enumerate(ranking, start=1):
            scores[node_id] = scores.get(node_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: -kv[1])


def _filter_sql(video_id, level, t_from, t_to, app) -> tuple[str, list]:
    clauses, params = [], []
    if video_id:
        clauses.append("n.video_id = ?")
        params.append(video_id)
    if level:
        clauses.append("n.level = ?")
        params.append(level)
    if t_from is not None:
        clauses.append("n.t_end >= ?")
        params.append(t_from)
    if t_to is not None:
        clauses.append("n.t_start <= ?")
        params.append(t_to)
    if app:
        clauses.append("n.apps LIKE ?")
        params.append(f"%{app}%")
    return (" AND " + " AND ".join(clauses)) if clauses else "", params


def search(db: sqlite3.Connection, query: str, cfg: IndexConfig, embedder: Embedder | None = None, video_id: str | None = None,
           level: str | None = None, t_from: float | None = None, t_to: float | None = None, app: str | None = None) -> list[dict]:
    filtered = any(v is not None for v in (video_id, level, t_from, t_to, app))
    k = cfg.k_filtered if filtered else cfg.k
    where, params = _filter_sql(video_id, level, t_from, t_to, app)
    rankings: list[list[str]] = []
    q = fts_query(query)
    if q:
        rows = db.execute(f"SELECT f.node_id FROM nodes_fts f JOIN nodes n ON n.node_id = f.node_id WHERE nodes_fts MATCH ?{where} ORDER BY bm25(nodes_fts) LIMIT ?",
                          [q, *params, k]).fetchall()
        rankings.append([r[0] for r in rows])
    tq = trigram_query(query)
    if tq:
        rows = db.execute(f"SELECT f.node_id FROM nodes_tri f JOIN nodes n ON n.node_id = f.node_id WHERE nodes_tri MATCH ?{where} ORDER BY bm25(nodes_tri) LIMIT ?",
                          [tq, *params, k]).fetchall()
        rankings.append([r[0] for r in rows])
    if embedder is not None:
        import sqlite_vec

        vec = sqlite_vec.serialize_float32(embedder.embed([query])[0])
        vwhere = " AND ".join(c for c in ["level = ?" if level else "", "video_id = ?" if video_id else ""] if c)
        vparams = [p for p, c in ((level, level), (video_id, video_id)) if c]
        rows = db.execute(f"SELECT node_id FROM nodes_vec WHERE embedding MATCH ? AND k = ?{(' AND ' + vwhere) if vwhere else ''} ORDER BY distance",
                          [vec, k, *vparams]).fetchall()
        ids = [r[0] for r in rows]
        if t_from is not None or t_to is not None or app:
            keep = {r[0] for r in db.execute(f"SELECT n.node_id FROM nodes n WHERE 1=1{where}", params).fetchall()}
            ids = [i for i in ids if i in keep]
        rankings.append(ids)
    fused = rrf(rankings, cfg.rrf)[:k]
    out = []
    for node_id, score in fused:
        row = db.execute("SELECT node_id, video_id, level, item_id, frame_start, frame_end, t_start, t_end, apps, layout_conf, text, payload FROM nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row:
            out.append({"node_id": row[0], "video_id": row[1], "level": row[2], "item_id": row[3], "frames": [row[4], row[5]],
                        "t": [row[6], row[7]], "apps": json.loads(row[8]), "layout_conf": row[9], "text": row[10],
                        "payload": json.loads(row[11]), "score": round(score, 5)})
    return out


# ---------- node extraction (§14.1) ----------
def extract_nodes(run: Run) -> list[Node]:
    vid = run.video_id
    frames = run.load_frames()
    ts = run.load_transitions()
    interps = run.load_interpretations()
    from vt.jsonl import read_jsonl
    from vt.schemas import HierNode

    steps = read_jsonl(run.steps, HierNode)
    sections = read_jsonl(run.sections, HierNode)

    def _rng_lookup(nodes: list[HierNode], child_ids: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for n in nodes:
            a, b = n.children
            inside = False
            for cid in child_ids:
                if cid == a:
                    inside = True
                if inside:
                    out[cid] = n.id
                if cid == b:
                    inside = False
        return out

    t_ids = [t.id for t in ts]
    step_of = _rng_lookup(steps, t_ids)
    section_of_step = _rng_lookup(sections, [s.id for s in steps])
    nodes: list[Node] = []
    for f in frames:
        chapter = run.chapter_of(f.t_settled)
        for r in f.regions:
            text = "\n".join(l.fused for l in r.lines if l.fused)
            if not text:
                continue
            nodes.append(Node(node_id=f"{vid}:f{f.frame}:{r.id}", video_id=vid, level="region", item_id=f"{f.frame}:{r.id}",
                              frames=(f.frame, f.frame), t=(f.t_settled, f.t_end), apps=[r.app], region_names=[r.name],
                              layout_conf=r.layout_conf, chapter_id=chapter.id if chapter else None, text=f"{r.app} {r.name}\n{text}",
                              payload={"frame": f.frame, "region": r.id, "lines": [l.model_dump() for l in r.lines]}))
        if f.description:
            nodes.append(Node(node_id=f"{vid}:f{f.frame}:desc", video_id=vid, level="frame", item_id=str(f.frame), frames=(f.frame, f.frame),
                              t=(f.t_settled, f.t_end), apps=sorted({r.app for r in f.regions}), text=f.description,
                              chapter_id=chapter.id if chapter else None, payload={"frame": f.frame}))
    for t in ts:
        ip = interps.get(t.id)
        b = next((f for f in frames if f.frame == t.to_frame), None)
        ev = "; ".join(f'{e.type} {e.text or ""}'.strip() for e in t.events)
        text = " \n".join(x for x in [ev, ip.action if ip else "", ip.result if ip else ""] if x)
        if not text:
            text = " ".join((o.new or o.old or "") for rd in t.computed_diff.values() for o in rd.ops)
        chapter = run.chapter_of(b.t_settled) if b else None
        nodes.append(Node(node_id=f"{vid}:{t.id}", video_id=vid, level="transition", item_id=t.id, frames=(t.from_frame, t.to_frame), t=t.t,
                          apps=sorted({r.app for r in (b.regions if b else [])}), step_id=step_of.get(t.id),
                          section_id=section_of_step.get(step_of.get(t.id, ""), None), chapter_id=chapter.id if chapter else None,
                          text=text, payload={"transition": t.model_dump(), "interpretation": ip.model_dump() if ip else None}))
    for s in steps:
        nodes.append(Node(node_id=f"{vid}:{s.id}", video_id=vid, level="step", item_id=s.id, frames=s.frames, t=s.t, step_id=s.id,
                          section_id=section_of_step.get(s.id), text=f"{s.label}\n{s.description}", payload=s.model_dump()))
    for c in sections:
        nodes.append(Node(node_id=f"{vid}:{c.id}", video_id=vid, level="section", item_id=c.id, frames=c.frames, t=c.t, section_id=c.id,
                          text=f"{c.label}\n{c.description}", payload=c.model_dump()))
    if run.video.exists():
        v = HierNode.model_validate_json(run.video.read_text())
        nodes.append(Node(node_id=f"{vid}:V", video_id=vid, level="video", item_id="V", frames=v.frames, t=v.t, text=f"{v.label}\n{v.description}", payload=v.model_dump()))
    for c in run.load_outline():
        nodes.append(Node(node_id=f"{vid}:{c.id}", video_id=vid, level="chapter", item_id=c.id, frames=(0, 0), t=(c.start_s, c.end_s),
                          chapter_id=c.id, text=f"{c.title}\n{c.gist}", payload=c.model_dump()))
    return nodes


def build_index(run: Run, cfg: Config) -> None:
    inputs = [run.frames, run.transitions, run.interpretations, run.steps, run.sections]
    ch = config_hash(cfg, "index")
    if run.stage_up_to_date("index", inputs, ch):
        log.info("index up to date")
        return
    nodes = extract_nodes(run)
    if run.index_db.exists():
        run.index_db.unlink()
    db = open_db(run.index_db)
    index_nodes(db, nodes, get_embedder(cfg.index))
    db.close()
    run.stage_done("index", inputs, ch, nodes=len(nodes), embedder=cfg.index.embedder)
```

Add to `cli.py`:

```python
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
        typer.echo(f"{h['score']:.4f} {h['level']:<10} {h['item_id']:<8} t={h['t'][0]:.1f}-{h['t'][1]:.1f}  {h['text'][:100]!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_index.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vt/index.py src/vt/cli.py tests/test_index.py
git commit -m "feat: Stage 7 SQLite index with FTS5, trigram, sqlite-vec and RRF search"
```

---

### Task 17: Answering agent (§14.3, §15.4)

**Files:**
- Create: `src/vt/prompts/agent.py`, `src/vt/agent.py`
- Modify: `src/vt/cli.py` (add `ask`)
- Test: `tests/test_agent.py` (tool functions only; the loop needs the network)

**Interfaces:**
- Produces: `Tools(run, cfg)` with methods `search(query, level=None, t_from=None, t_to=None, app=None) -> dict`, `get_node(node_id) -> dict`, `get_transitions(t_a, t_b) -> dict`, `get_frame(frame) -> list[dict]` (content blocks: a text label and an image), `redecode(t_a, t_b, fps) -> list[dict]` (up to 6 image blocks); `TOOL_DEFS: list[dict]` (Anthropic tool schemas); `ask(run, cfg, question, client=None, max_turns=12) -> str`.

- [ ] **Step 1: Write the failing test**

`tests/test_agent.py`:

```python
from pathlib import Path

from vt.agent import TOOL_DEFS, Tools
from vt.config import Config
from vt.index import Node, index_nodes, open_db
from vt.run import Run


def test_tools_search_and_get_node(tmp_path: Path):
    run = Run(tmp_path / "r")
    db = open_db(run.index_db)
    index_nodes(db, [Node(node_id="v:T1", video_id="v", level="transition", item_id="T1", frames=(1, 2), t=(3.0, 4.0),
                          text='typed "kubectl get nodes"', payload={"id": "T1"})], None)
    db.close()
    tools = Tools(run, Config())
    res = tools.search("kubectl")
    assert res["hits"][0]["item_id"] == "T1" and res["hits"][0]["t"] == [3.0, 4.0]
    assert tools.get_node("v:T1")["payload"] == {"id": "T1"}
    assert {t["name"] for t in TOOL_DEFS} == {"search", "get_node", "get_transitions", "get_frame", "redecode"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.agent`.

- [ ] **Step 3: Write the implementation**

`src/vt/prompts/agent.py`:

```python
VERSION = "agent-v1"

SYSTEM = """You answer questions about screen-recording tutorials using an index built from them.

Answer only from retrieved material. Use the tools: search the index (exact strings such as commands and identifiers work best quoted), read nodes, list the transitions in a time range, and look at frames when the text is ambiguous. Cite frame numbers and times for every factual claim. Quote exact text only from lines marked agree=true; otherwise present both readings, or mark a single reading as unverified. If the material does not answer the question, say so and suggest which time range to inspect."""
```

`src/vt/agent.py`:

```python
from __future__ import annotations

import json
import logging
from pathlib import Path

from vt.config import Config
from vt.index import get_embedder, open_db, search as _search
from vt.prompts import agent as agent_prompt
from vt.providers.base import image_block, text_block
from vt.run import Run

log = logging.getLogger(__name__)

TOOL_DEFS = [
    {"name": "search", "description": "Search the visual-transcript index (lexical + substring; vector if configured). Returns ranked nodes with frames, times and text.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "level": {"type": "string", "description": "region|frame|transition|step|section|video|chapter"},
                                                        "t_from": {"type": "number"}, "t_to": {"type": "number"}, "app": {"type": "string"}}, "required": ["query"]}},
    {"name": "get_node", "description": "Fetch one node in full by node_id (payload includes lines with agree flags for regions, or the transition and its interpretation).",
     "input_schema": {"type": "object", "properties": {"node_id": {"type": "string"}}, "required": ["node_id"]}},
    {"name": "get_transitions", "description": "List transitions whose time window overlaps [t_a, t_b] seconds, with their events and interpretations.",
     "input_schema": {"type": "object", "properties": {"t_a": {"type": "number"}, "t_b": {"type": "number"}}, "required": ["t_a", "t_b"]}},
    {"name": "get_frame", "description": "Return the PNG of an emitted frame as an image, with its time.",
     "input_schema": {"type": "object", "properties": {"frame": {"type": "integer"}}, "required": ["frame"]}},
    {"name": "redecode", "description": "Re-decode the source video between t_a and t_b seconds at the given fps and return up to 6 frames as images (recovery tool).",
     "input_schema": {"type": "object", "properties": {"t_a": {"type": "number"}, "t_b": {"type": "number"}, "fps": {"type": "number", "default": 2}}, "required": ["t_a", "t_b"]}},
]


class Tools:
    def __init__(self, run: Run, cfg: Config):
        self.run, self.cfg = run, cfg
        self.db = open_db(run.index_db)
        self.embedder = get_embedder(cfg.index)

    def search(self, query: str, level: str | None = None, t_from: float | None = None, t_to: float | None = None, app: str | None = None) -> dict:
        hits = _search(self.db, query, self.cfg.index, self.embedder, level=level, t_from=t_from, t_to=t_to, app=app)
        return {"hits": [{k: v for k, v in h.items() if k != "payload"} for h in hits]}

    def get_node(self, node_id: str) -> dict:
        row = self.db.execute("SELECT level, item_id, frame_start, frame_end, t_start, t_end, text, payload FROM nodes WHERE node_id = ?", (node_id,)).fetchone()
        if not row:
            return {"error": "no such node"}
        return {"node_id": node_id, "level": row[0], "item_id": row[1], "frames": [row[2], row[3]], "t": [row[4], row[5]], "text": row[6], "payload": json.loads(row[7])}

    def get_transitions(self, t_a: float, t_b: float) -> dict:
        interps = self.run.load_interpretations()
        out = []
        for t in self.run.load_transitions():
            if t.t[1] >= t_a and t.t[0] <= t_b:
                ip = interps.get(t.id)
                out.append({"id": t.id, "frames": [t.from_frame, t.to_frame], "t": list(t.t), "kind": t.kind,
                            "events": [e.model_dump() for e in t.events], "action": ip.action if ip else None, "result": ip.result if ip else None})
        return {"transitions": out}

    def get_frame(self, frame: int) -> list[dict]:
        rec = next((f for f in self.run.load_stage1() if f.frame == frame), None)
        if rec is None:
            return [text_block("no such frame")]
        return [text_block(f"Frame {frame} (t={rec.t_settled:.2f}s):"), image_block(self.run.root / rec.png)]

    def redecode(self, t_a: float, t_b: float, fps: float = 2.0) -> list[dict]:
        from vt.decode import iter_frames

        video = Path(self.run.manifest_read()["video"])
        blocks: list[dict] = []
        next_t = t_a
        tmp = self.run.root / "redecode"
        tmp.mkdir(exist_ok=True)
        for df in iter_frames(video):
            if df.t < t_a:
                continue
            if df.t > t_b or len(blocks) >= 12:
                break
            if df.t >= next_t:
                p = tmp / f"{df.t:09.3f}.png"
                df.frame.to_image().save(p, format="PNG", compress_level=1)
                blocks += [text_block(f"t={df.t:.2f}s:"), image_block(p)]
                next_t += 1.0 / fps
        return blocks or [text_block("no frames in range")]


def _dispatch(tools: Tools, name: str, args: dict):
    fn = getattr(tools, name)
    return fn(**args)


def ask(run: Run, cfg: Config, question: str, client=None, max_turns: int = 12) -> str:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    tools = Tools(run, cfg)
    messages = [{"role": "user", "content": question}]
    for _ in range(max_turns):
        resp = client.messages.create(model=cfg.model.model, max_tokens=16000, system=agent_prompt.SYSTEM, tools=TOOL_DEFS,
                                      output_config={"effort": cfg.model.effort_agent}, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        results = []
        for b in resp.content:
            if getattr(b, "type", "") != "tool_use":
                continue
            try:
                out = _dispatch(tools, b.name, dict(b.input))
                content = out if isinstance(out, list) else json.dumps(out, default=str)[:60000]
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": content})
            except Exception as e:  # tool errors go back to the model, never abort the loop
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": f"error: {e}", "is_error": True})
        messages.append({"role": "user", "content": results})
    return "Stopped after too many tool calls without a final answer."
```

Add to `cli.py`:

```python
@app.command()
def ask(run_dir: Path, question: str, config: Path | None = None, verbose: bool = False):
    """Answer a question over a run's index with citations."""
    _setup_logging(verbose)
    from vt.agent import ask as _ask
    typer.echo(_ask(Run(run_dir), load_config(config), question))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_agent.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vt/prompts/agent.py src/vt/agent.py src/vt/cli.py tests/test_agent.py
git commit -m "feat: answering agent with search/get_node/get_transitions/get_frame/redecode tools"
```

---

### Task 18: End-to-end runner, `vt setup`, run diagnostics (§18.4, §20.9, §20.11)

**Files:**
- Create: `src/vt/diagnostics.py`
- Modify: `src/vt/cli.py` (add `run`, `setup`)
- Test: `tests/test_diagnostics.py`

**Interfaces:**
- Produces: `diagnostics(run) -> dict` (the §18.4 list: emitted frames, settled fraction, lines per frame, agree/OCR-only/VLM-only fractions, rows_rejected, grouping_repairs, label_clashes, perception errors, invalid_refs rate, transitions by kind, per-stage usage and cost estimate, cache hit rate, refusals); `estimate_cost(usage, model) -> float`; `vt run VIDEO --out RUN [--stages a,b,c] [--config]`; `vt setup`.

- [ ] **Step 1: Write the failing test**

`tests/test_diagnostics.py`:

```python
from vt.diagnostics import estimate_cost, summarize


def test_summarize_counts_and_cost():
    frames = [{"settled": True, "lines": [{"agree": True}, {"agree": None, "ocr": None}, {"agree": False}]},
              {"settled": False, "lines": [{"agree": True}]}]
    s = summarize(frames)
    assert s["frames"] == 2 and s["settled_fraction"] == 0.5 and s["lines_per_frame"] == 2.0
    assert s["agree_fraction"] == 0.5 and s["vlm_only_fraction"] == 0.25
    assert estimate_cost({"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 0}, "claude-opus-5") == 7.5
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_diagnostics.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.diagnostics`.

- [ ] **Step 3: Write the implementation**

`src/vt/diagnostics.py`:

```python
from __future__ import annotations

import json

from vt.run import Run

PRICES = {  # $ per million tokens, input / output / cache read (2026-09-13 list prices)
    "claude-opus-5": (5.0, 25.0, 0.5),
    "claude-sonnet-5": (2.0, 10.0, 0.2),
    "claude-haiku-4-5": (1.0, 5.0, 0.1),
}


def estimate_cost(usage: dict, model: str) -> float:
    pin, pout, pcache = PRICES.get(model, (5.0, 25.0, 0.5))
    return round((usage.get("input_tokens", 0) * pin + usage.get("output_tokens", 0) * pout + usage.get("cache_read_input_tokens", 0) * pcache) / 1e6, 4)


def summarize(frames: list[dict]) -> dict:
    n = len(frames)
    lines = [l for f in frames for l in f.get("lines", [])]
    nl = len(lines) or 1
    return {"frames": n, "settled_fraction": round(sum(1 for f in frames if f.get("settled")) / max(n, 1), 3),
            "lines_per_frame": round(len(lines) / max(n, 1), 2),
            "agree_fraction": round(sum(1 for l in lines if l.get("agree") is True) / nl, 3),
            "ocr_only_fraction": round(sum(1 for l in lines if l.get("agree") is None and l.get("ocr") is not None) / nl, 3),
            "vlm_only_fraction": round(sum(1 for l in lines if l.get("ocr") is None) / nl, 3)}


def diagnostics(run: Run) -> dict:
    frames = run.load_frames()
    flat = [{"settled": f.settled, "lines": [{"agree": l.agree, "ocr": l.ocr} for r in f.regions for l in r.lines]} for f in frames]
    d = summarize(flat)
    d.update({"rows_rejected": sum(f.rows_rejected for f in frames), "grouping_repairs": sum(f.grouping_repairs for f in frames),
              "label_clashes": sum(f.label_clashes for f in frames), "perception_errors": sum(1 for f in frames if f.error),
              "refusals": sum(1 for f in frames if f.error == "refusal")})
    ts = run.load_transitions()
    d["transitions"] = {k: sum(1 for t in ts if t.kind == k) for k in ("single", "coalesced", "transient_merged", "unsettled", "trivial")}
    interps = run.load_interpretations()
    d["invalid_refs"] = sum(i.invalid_refs for i in interps.values())
    m = run.manifest_read()
    usage_total: dict[str, int] = {}
    cost = 0.0
    for name, st in m.get("stages", {}).items():
        u = st.get("usage")
        if u:
            for k, v in u.items():
                usage_total[k] = usage_total.get(k, 0) + v
            cost += estimate_cost(u, st.get("model", ""))
    d["usage"] = usage_total
    d["estimated_cost_usd"] = round(cost, 2)
    cache_files = list(run.cache_dir.glob("*.json"))
    d["cache_entries"] = len(cache_files)
    return d
```

Add to `cli.py`:

```python
STAGES = ["outline", "decode", "ocr", "overlay", "perceive", "merge", "diff", "interpret", "hierarchy", "index"]


@app.command()
def run(video: Path, out: Path = typer.Option(..., "--out"), config: Path | None = None, stages: str | None = None, verbose: bool = False):
    """Run every stage in order (idempotent; each stage skips itself when inputs and config are unchanged)."""
    _setup_logging(verbose)
    cfg = load_config(config)
    r = Run(out)
    wanted = stages.split(",") if stages else STAGES
    from vt import coalesce, hierarchy as hier, index as idx, interpret as interp, merge as mrg, overlay as ov, perceive as perc, stage1, stage2a
    from vt.diagnostics import diagnostics
    from vt.outline import run_outline

    steps = {"outline": lambda: run_outline(r, cfg, video), "decode": lambda: stage1.run_stage1(r, cfg, video),
             "ocr": lambda: stage2a.run_ocr(r, cfg), "overlay": lambda: ov.run_overlay(r, cfg), "perceive": lambda: perc.run_perceive(r, cfg),
             "merge": lambda: mrg.run_merge(r, cfg), "diff": lambda: coalesce.run_diff(r, cfg), "interpret": lambda: interp.run_interpret(r, cfg),
             "hierarchy": lambda: hier.run_hierarchy(r, cfg), "index": lambda: idx.build_index(r, cfg)}
    for name in STAGES:
        if name in wanted:
            typer.echo(f"== {name}")
            steps[name]()
    r.manifest_update(diagnostics=diagnostics(r))
    typer.echo(json.dumps(r.manifest_read().get("diagnostics", {}), indent=2))


@app.command()
def setup(config: Path | None = None):
    """Check the environment: Vision OCR, FTS5, sqlite-vec, credentials, optional embedder."""
    import sqlite3
    cfg = load_config(config)
    ok = True
    try:
        from vt.ocr import get_engine
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
    typer.echo("anthropic credentials: " + ("ANTHROPIC_API_KEY set" if os.environ.get("ANTHROPIC_API_KEY") else "no env var (an `ant auth login` profile may still work)"))
    if cfg.index.embedder != "none":
        try:
            from vt.index import get_embedder
            get_embedder(cfg.index)
            typer.echo(f"embedder {cfg.index.embedder}: ok")
        except Exception as e:
            typer.echo(f"embedder {cfg.index.embedder}: FAILED ({e})")
    raise typer.Exit(code=0 if ok else 1)
```

(`import json` at the top of `cli.py`.)

- [ ] **Step 4: Run the test and the setup command**

Run: `uv run pytest tests/test_diagnostics.py -v && uv run vt setup`
Expected: 1 passed; setup prints `ok` for the OCR engine and FTS5.

- [ ] **Step 5: Commit**

```bash
git add src/vt/diagnostics.py src/vt/cli.py tests/test_diagnostics.py
git commit -m "feat: vt run pipeline driver, vt setup, run diagnostics"
```

---

### Task 19: Batch mode for Stages 2c and 5 (§20.7)

**Files:**
- Create: `src/vt/providers/batch.py`
- Modify: `src/vt/providers/anthropic_.py` (collect mode), `src/vt/perceive.py`, `src/vt/interpret.py` (two-phase run when `model.mode == "batch"`)
- Test: `tests/test_batch.py`

**Interfaces:**
- Produces: `strict_schema(model: type[BaseModel]) -> dict` (the SDK's `transform_schema` when importable, else a local transformation that sets `additionalProperties: false` and requires every property, recursively); `chunk_requests(reqs: list[dict], max_bytes) -> list[list[dict]]`; `BatchRunner(client, cache, run)` with `async run(pending: list[PendingRequest]) -> None` (submit chunks, persist `batches.json`, poll, write results into the cache, re-queue errored/expired once).
- `AnthropicProvider.collecting: bool` — when true, `complete()` records a `PendingRequest(key, request_params, output_model)` on a cache miss and returns `VlmResult(None, "pending")`; `provider.pending` is the list.

- [ ] **Step 1: Write the failing tests**

`tests/test_batch.py`:

```python
from pydantic import BaseModel

from vt.providers.batch import chunk_requests, strict_schema


class Inner(BaseModel):
    a: int
    b: str | None = None


class Outer(BaseModel):
    items: list[Inner]
    name: str


def test_strict_schema_requires_all_and_forbids_extras():
    s = strict_schema(Outer)
    assert s["additionalProperties"] is False and set(s["required"]) == {"items", "name"}
    inner = s["$defs"]["Inner"] if "$defs" in s else s["properties"]["items"]["items"]
    assert inner["additionalProperties"] is False and set(inner["required"]) == {"a", "b"}


def test_chunk_requests_by_size():
    reqs = [{"custom_id": str(i), "params": {"x": "y" * 100}} for i in range(10)]
    chunks = chunk_requests(reqs, max_bytes=450)
    assert sum(len(c) for c in chunks) == 10 and all(len(c) <= 3 for c in chunks)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_batch.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.providers.batch`.

- [ ] **Step 3: Write the implementation**

`src/vt/providers/batch.py`:

```python
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

from pydantic import BaseModel

from vt.providers.cache import CallCache
from vt.run import Run

log = logging.getLogger(__name__)


def _local_strict(schema: dict) -> dict:
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"].keys())
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(schema)
    return schema


def strict_schema(model: type[BaseModel]) -> dict:
    schema = model.model_json_schema()
    try:
        from anthropic.lib._parse._transform import transform_schema

        return transform_schema(schema)
    except Exception:
        return _local_strict(schema)


@dataclass
class PendingRequest:
    key: str
    params: dict
    output_model: type[BaseModel]


def chunk_requests(reqs: list[dict], max_bytes: int = 200 * 1024 * 1024) -> list[list[dict]]:
    chunks: list[list[dict]] = [[]]
    size = 0
    for r in reqs:
        n = len(json.dumps(r))
        if chunks[-1] and size + n > max_bytes:
            chunks.append([])
            size = 0
        chunks[-1].append(r)
        size += n
    return [c for c in chunks if c]


class BatchRunner:
    def __init__(self, client, cache: CallCache, run: Run, poll_s: float = 60.0):
        self.client, self.cache, self.run, self.poll_s = client, cache, run, poll_s

    def _state(self) -> dict:
        return json.loads(self.run.batches.read_text()) if self.run.batches.exists() else {"batches": []}

    def _save(self, st: dict) -> None:
        self.run.batches.write_text(json.dumps(st, indent=1))

    async def run_pending(self, pending: list[PendingRequest]) -> None:
        by_key = {p.key: p for p in pending}
        st = self._state()
        done_keys = {k for b in st["batches"] for k in b.get("done", [])}
        todo = [p for p in pending if p.key not in done_keys]
        open_batches = [b for b in st["batches"] if b["status"] != "ended"]
        queued = {k for b in open_batches for k in b["custom_ids"]}
        new = [p for p in todo if p.key not in queued]
        for chunk in chunk_requests([{"custom_id": p.key, "params": p.params} for p in new]):
            batch = await self.client.messages.batches.create(requests=chunk)
            st["batches"].append({"batch_id": batch.id, "custom_ids": [c["custom_id"] for c in chunk], "status": "submitted", "done": []})
            self._save(st)
        requeue: list[PendingRequest] = []
        for b in st["batches"]:
            if b["status"] == "ended":
                continue
            while True:
                info = await self.client.messages.batches.retrieve(b["batch_id"])
                if info.processing_status == "ended":
                    break
                log.info("batch %s: %s", b["batch_id"], info.processing_status)
                await asyncio.sleep(self.poll_s)
            async for res in await self.client.messages.batches.results(b["batch_id"]):
                p = by_key.get(res.custom_id)
                if p is None:
                    continue
                if res.result.type == "succeeded":
                    msg = res.result.message
                    text = next((c.text for c in msg.content if getattr(c, "type", "") == "text"), "")
                    usage = {"input_tokens": msg.usage.input_tokens, "output_tokens": msg.usage.output_tokens,
                             "cache_read_input_tokens": getattr(msg.usage, "cache_read_input_tokens", 0) or 0}
                    try:
                        parsed = p.output_model.model_validate_json(text).model_dump() if msg.stop_reason != "refusal" else None
                        error = "refusal" if msg.stop_reason == "refusal" else None
                    except Exception as e:
                        parsed, error = None, f"schema: {str(e)[:300]}"
                    self.cache.put(p.key, {"batch": b["batch_id"]}, {"parsed": parsed, "error": error, "usage": usage, "text": text, "stop_reason": msg.stop_reason})
                elif res.result.type == "errored" and res.result.error.type == "invalid_request":
                    self.cache.put(p.key, {"batch": b["batch_id"]}, {"parsed": None, "error": f"invalid_request: {res.result.error}", "usage": {}, "text": None, "stop_reason": None})
                else:
                    requeue.append(p)
                b["done"].append(res.custom_id)
            b["status"] = "ended"
            self._save(st)
        if requeue and not getattr(self, "_retried", False):
            self._retried = True
            await self.run_pending(requeue)
```

Changes to `src/vt/providers/anthropic_.py` — add collect mode: in `__init__` add `self.collecting = False` and `self.pending: list = []`; in `complete()`, after the cache-miss check and before `async with self.sem`, insert:

```python
        if self.collecting:
            from vt.providers.batch import PendingRequest, strict_schema

            params = {"model": self.model, "max_tokens": self.cfg.max_tokens,
                      "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                      "messages": [{"role": "user", "content": blocks}],
                      "output_config": {"effort": effort, "format": {"type": "json_schema", "schema": strict_schema(output_model)}}}
            self.pending.append(PendingRequest(key, params, output_model))
            return VlmResult(None, "pending")
```

and add:

```python
    async def run_batches(self, run) -> None:
        from vt.providers.batch import BatchRunner

        await BatchRunner(self.client, self.cache, run).run_pending(self.pending)
        self.pending = []
```

Changes to `run_perceive` and `run_interpret`: replace `records = asyncio.run(_xxx_all(run, cfg, provider))` with:

```python
    if cfg.model.mode == "batch" and hasattr(provider, "collecting"):
        provider.collecting = True
        asyncio.run(_perceive_all(run, cfg, provider))      # collect cache misses
        provider.collecting = False
        asyncio.run(provider.run_batches(run))              # submit, poll, fill the cache
    records = asyncio.run(_perceive_all(run, cfg, provider))
```

(same shape with `_interpret_all` in `interpret.py`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_batch.py tests/test_provider.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vt/providers/batch.py src/vt/providers/anthropic_.py src/vt/perceive.py src/vt/interpret.py tests/test_batch.py
git commit -m "feat: Message Batches mode for Stages 2c and 5 with size chunking and resume"
```

---

### Task 20: Stage 0 — optional Gemini agentic outline (§6, §10.4)

**Files:**
- Create: `src/vt/outline.py`
- Modify: `src/vt/cli.py` (add `outline`)
- Test: `tests/test_outline.py`

**Interfaces:**
- Produces: `parse_outline_text(text) -> list[OutlineChapter]` (accepts fenced or bare JSON, assigns `c1..cN`, drops malformed entries, sorts by `start_s`); `run_outline(run, cfg, video, import_path=None)` writing `outline.json` when `cfg.outline.enabled` or `import_path` is given; otherwise a no-op.

- [ ] **Step 1: Write the failing test**

`tests/test_outline.py`:

```python
from vt.outline import parse_outline_text


def test_parse_outline_text_handles_fences_and_bad_entries():
    text = '```json\n[{"start_s": 312, "end_s": 600, "title": "Create the cluster", "gist": "…"}, {"start_s": 0, "end_s": 312, "title": "Resource group", "gist": "g"}, {"bad": 1}]\n```'
    ch = parse_outline_text(text)
    assert [c.id for c in ch] == ["c1", "c2"] and ch[0].title == "Resource group" and ch[1].start_s == 312.0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_outline.py -v`
Expected: FAIL with `ModuleNotFoundError: vt.outline`.

- [ ] **Step 3: Write the implementation**

`src/vt/outline.py`:

```python
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from vt.config import Config
from vt.run import Run
from vt.schemas import OutlineChapter

log = logging.getLogger(__name__)

PROMPT = """Produce a chapter outline of this screen-recording tutorial as JSON: a list of 5-20 objects with keys start_s, end_s (seconds), title, gist. Put boundaries where the sub-goal changes. Do not attempt to transcribe exact text. Return only the JSON array."""


def parse_outline_text(text: str) -> list[OutlineChapter]:
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        raw = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    items = []
    for it in raw:
        try:
            items.append((float(it["start_s"]), float(it["end_s"]), str(it["title"]), str(it.get("gist", ""))))
        except (KeyError, TypeError, ValueError):
            continue
    items.sort()
    return [OutlineChapter(id=f"c{i}", start_s=s, end_s=e, title=t, gist=g) for i, (s, e, t, g) in enumerate(items, start=1)]


def _gemini_outline(video: Path, model: str) -> str:
    from google import genai  # optional extra: uv sync --extra outline

    client = genai.Client()
    f = client.files.upload(file=str(video))
    while not f.state or f.state.name != "ACTIVE":
        time.sleep(5)
        f = client.files.get(name=f.name)
    interaction = client.interactions.create(model=model, input=[
        {"type": "video", "uri": f.uri, "mime_type": f.mime_type, "processing": "agentic"},
        {"type": "text", "text": PROMPT}])
    return interaction.output_text


def run_outline(run: Run, cfg: Config, video: Path, import_path: Path | None = None) -> None:
    if import_path is not None:
        chapters = parse_outline_text(import_path.read_text())
    elif cfg.outline.enabled:
        if run.outline.exists():
            log.info("outline exists; skipping")
            return
        chapters = parse_outline_text(_gemini_outline(video, cfg.outline.model))
    else:
        return
    run.outline.write_text(json.dumps([c.model_dump() for c in chapters], indent=1))
    run.manifest_update(outline={"chapters": len(chapters), "source": str(import_path) if import_path else cfg.outline.model})
```

Add to `cli.py`:

```python
@app.command()
def outline(video: Path, out: Path = typer.Option(..., "--out"), import_path: Path | None = typer.Option(None, "--import"), config: Path | None = None):
    """Stage 0 (optional): Gemini agentic chapter outline, or import one from a JSON file."""
    from vt.outline import run_outline
    cfg = load_config(config)
    if import_path is None and not cfg.outline.enabled:
        typer.echo("outline disabled in config (set [outline] enabled = true) and no --import given")
        raise typer.Exit(code=1)
    run_outline(Run(out), cfg, video, import_path)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/test_outline.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/vt/outline.py src/vt/cli.py tests/test_outline.py
git commit -m "feat: optional Stage 0 outline (Gemini agentic or imported)"
```

---

### Task 21: Wrap-up — full test run, smoke run on the sample without model calls, docs

**Files:**
- Modify: `README.md`, `docs/decision-ledger.md`

- [ ] **Step 1: Run the whole test suite**

Run: `uv run pytest -v`
Expected: all tests pass (≈ 45). Fix anything red before continuing.

- [ ] **Step 2: Smoke-run the local stages on the sample video**

Run: `uv run vt run assets/create-aks-cluster-tutorial.mp4 --out runs/aks --stages decode,ocr,overlay --verbose`
Expected: Stage 1 completes; note emitted frame count, settled fraction, wall time; OCR lines per frame; overlay clashes. Open two overlays and two frames. Record the numbers in `docs/decision-ledger.md` under a "First run on the sample" entry.

- [ ] **Step 3: Dry-run the model stages without credentials**

Run: `uv run vt run assets/create-aks-cluster-tutorial.mp4 --out runs/aks --stages perceive` (only if `ANTHROPIC_API_KEY` or an `ant auth login` profile exists — otherwise skip and note it).
Expected: with credentials, `perception.jsonl` fills and `manifest.json` records usage and cost; without, the provider records `api:` errors per frame and the run continues (that behavior is itself worth confirming on one frame with `--stages perceive` and a run directory holding a single frame).

- [ ] **Step 4: Update docs**

`README.md`: fill the "Status" section with what runs today and the measured numbers. `docs/decision-ledger.md`: add entries for any executive decision taken during implementation.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/decision-ledger.md
git commit -m "docs: implementation status and first-run numbers"
```

---

## Self-review (writing-plans checklist)

**Spec coverage** — design section → task: §6 Stage 0 → Task 20; §7.1 decode → Task 3; §7.2/§7.4/§7.5 → Task 4; §7.3/§7.6 → Tasks 5–6; §8.1 → Task 7; §8.2 → Task 8; §8.3/§15.1 → Tasks 9–10; §9 → Task 11; §10 data model → Task 1 (schemas) with owners in Tasks 6, 7, 10, 11, 13, 14, 15, 16, 20; §10.7 loaders → Task 6; §11.1–§11.2 → Task 12; §11.3–§11.5 → Task 13; §12/§15.2 → Task 14; §13/§15.3 → Task 15; §14/§15.4 → Tasks 16–17; §16 parameters → Task 1 (`vt.toml`, config models); §18.4 fixtures and diagnostics → Tasks 4, 5, 18; §19/§20.7 batch and cost → Tasks 18–19; §20.9 idempotency → Task 6 (`Run.stage_up_to_date`) used by every stage; §20.11 CLI → Tasks 6–18. Not implemented in v1, by design: a second VLM provider (D15), the RapidOCR bake-off harness (§18.3 needs ground truth), redaction (§22 #12), Windows/Linux adapters beyond the engine switch (§20.8).

**Placeholder scan** — no TBD/TODO; every code step has the code.

**Type consistency** — `Line.fused`/`uncertain` (Task 1) are used by Tasks 12–14, 16; `Correspondence.matched` is `list[tuple[str, str, float]]` in Tasks 1, 12, 13; `Transition.t` is `tuple[float, float]` = `(prev.t_end, cur.t_settled)` in Tasks 12–16; `DiffOp.in_churn` is declared in Task 1, set in Task 12 and read in Tasks 13–14; `VlmProvider.complete` keyword signature is identical in Tasks 9, 10, 14, 15; `Run.load_frames()` applies `focus.jsonl` (Task 6) and is what Tasks 13–17 read; `SettleMachine.on_emit` receives the `Emission` with `frame` set (Task 5) and Task 6 replaces `frame` with `(n, path)` and sets `png_future`.

**Owner's constraints honoured** — tests are unit tests over synthetic frames, hand-written records and fake clients only; no integration tests; no test uses the sample video or the network. Manual smoke checks are labelled as such.
