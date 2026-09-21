# Re-base step 1: `read`, `track` and the free phase P0 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **One deliberate adaptation of the writing-plans format: this plan contains NO implementation bodies and no test
> code.** The previous plan's unrun code blocks failed 13 to 15 of 69 tests when first executed (ledger L20), and the
> owner now forbids code that exists anywhere except as the real implementation on the branch with its tests; no
> drafter or reviewer writes a prototype. So every task gives: the files; the public interface (signatures, record
> fields, config keys with units); the behaviour as numbered rules, each traced to the specification; the tests to
> write FIRST, each named, with its concrete fixture and exact expected values; the commands; the commit. The
> implementer writes the test code and the implementation on the branch from these. Reviewers of this plan read and
> reason; they do not execute anything.

> **Reconciled on 2026-09-21** with the two read-only reviews (`docs/reviews/2026-09-21-rebase-plan1-review-fork.md`,
> `…-fresh.md`) and the owner's rulings since the first draft; ledger L45 lists what each finding became. The rule of
> the reconciliation is the spec's §12, *simplify before repairing*: a fault in a mechanism is met first by removing the
> mechanism. So `track` has no groups, no connected components and no pools: a change record is one pair of boxes, or
> one appeared or removed box. The clock rule, the `trivial` kind and the `confusable` flag are dropped. Where the
> spec's §5 sketch and §6 steps still say "groups", §12 governs.

**Goal:** On branch `rebase-boxes`, replace the row machinery with the first measured stages of boxes mode — `read`
(OCR boxes per frame) and `track` (per-box change records and box lifetimes, from boxes and pixels only) — plus a
`report` command, and run the free phase P0 over all 221 decoded frames of the sample.

**Architecture:** `decode` (kept) emits frames; `read` writes `boxes.jsonl`; `track` compares consecutive frames'
pixels with `decode`'s own rule, decides per box what is unchanged, moved or changed, and writes `changes.jsonl` and
`lifetimes.jsonl`. Nothing in these stages calls a model or reads a model's output. Pure functions over boxes and a
labelled change image carry all the logic; thin stage wrappers do I/O, ids and the manifest.

**Tech stack:** Python ≥ 3.12 with `uv`; numpy, scipy.ndimage, PyAV (gray conversion), Pillow, pydantic 2, typer,
rapidfuzz; RapidOCR 3.9 on ONNX Runtime; pytest. No new dependencies.

**Spec:** `docs/proposals/2026-09-21-boxes-mode-rebase.md`, revision 3 (§2, §4 H1–H8, §5, §6 `read` and `track`, §8,
§9 P0, §10 steps 0–2, §11, and §12 "Simplify before repairing", which governs where §5–§6 still describe groups).
Executors read it with this plan. Where this plan is more specific than the spec, the
choice is listed under "Decisions this plan makes" for the reviewers.

## Global Constraints

- Work only on branch `rebase-boxes`. `main` and tag `pre-rebase-boxes` stay runnable and untouched. Nothing on the
  branch imports the old row machinery; after Task 1 it no longer exists on the branch.
- The package imports and `uv run pytest` reports 0 failures after every commit.
- Unit tests only: synthetic frames rendered in the test (as `tests/conftest.py` and `tests/test_detect.py` do),
  hand-made boxes, fake engines. No test reads the sample video, a run directory under `runs/`, or the network.
- No model API calls anywhere in this plan. No reviewer or implementer prototypes: code exists only as the real
  implementation with its tests.
- No constants taken from the sample video. Every geometric parameter is relative to box height or frame size, lives in
  `src/scry/config.py` with its unit in a comment, and appears in `scry.toml`.
- No logic for watch-list cases (pointer clipping a box, cursor glyphs, occlusion, low-contrast flicker, re-wrap)
  without evidence; no cursor or suggestion locating; no brightness thresholds; how long a text stays on screen is
  never evidence that something was run.
- The mechanical layer never says "typed". Recorded strings are exact; whitespace-blind comparison decides kind labels
  only (H4).
- Coordinates: `BBox = (x0, y0, x1, y1)` in original-frame pixels, `x1`/`y1` exclusive. Two rectangles *intersect*
  when their intersection has positive area.
- *Reading order* means one thing everywhere: the order of `read`'s box ids within a frame (Task 6, rule 2).
- Every stage writes only its own file, atomically (`scry.jsonl.write_jsonl`), and records a manifest entry
  `{inputs, config, finished, …stats}`; a stage skips itself when its inputs hash and config hash are unchanged
  (`Run.stage_up_to_date`, as today).
- Commit messages end with the attribution lines the session supplies.

## Review Focus

Inputs the spec implies and that are most likely to bite; each has a test in the task that owns the code.

1. **A frame pair of different sizes, or a missing PNG.** Expect no crash: `pixels` is null, every box is treated as
   touched, the text rules still run (Task 12, `test_size_mismatch_and_missing_png_degrade`).
2. **OCR boxes that overlap inside one frame** (a box nested in another; adjacent terminal lines, whose boxes overlap
   by a few pixels in the stored RapidOCR output). Expect a deterministic one-to-one result, no box in two records, no
   lifetime claimed twice (Task 8 `test_one_to_one_when_two_later_boxes_claim_one_earlier_box`, Task 10
   `test_adjacent_overlapping_lines_pair_with_their_own_earlier_selves`).
3. **The same string many times on one screen** (`1.24.10` twice, two `Node pools`). Expect same-place pairs first,
   then moves paired in reading order, never a cross-pairing that invents a change (Task 9
   `test_duplicates_pair_same_place_first_then_reading_order`).
4. **A run with zero or one frame, or a frame with no boxes.** Expect empty `changes.jsonl`, lifetimes for what
   exists, a report that renders (Task 12 `test_zero_and_one_frame_runs`, Task 15 `test_report_renders_on_empty_run`).
5. **Non-ASCII and empty OCR text** (icon glyphs read as CJK characters, whitespace-only text). Expect a lossless JSONL
   round trip and empty-text boxes dropped by `read`, never matched as "equal texts" (Task 4
   `test_records_round_trip_unicode`, Task 6 `test_read_drops_empty_text`).

Known and not tested here: RapidOCR loads OpenCV and `track` loads PyAV; both bundle FFmpeg (ledger L3). They have
run in one process since L32 without incident on the build machine. P0 runs `read` and `track` as separate commands.

## File structure at the end of this plan

```
src/scry/
  cli.py            commands: decode, outline, read, track, report, subset, setup, run (decode → read → track)
  config.py         DecodeConfig [decode.*], ReadConfig [read], TrackConfig [track], OverlayConfig, ModelConfig,
                    IndexConfig, OutlineConfig; unknown keys rejected
  schemas.py        BBox, Frame, RawWord, Box, FrameBoxes, PixelStats, BoxText, BoxChange, Revert, Change, FrameTime,
                    Lifetime, OutlineChapter
  run.py            Run: paths, manifest, loaders for the four files
  video.py          PyAV helpers (was decode.py)
  decode.py         the decode stage (was stage1.py)
  detect.py settle.py   unchanged apart from one added function in detect.py (Task 7)
  read.py           the read stage (was stage2a.py)
  ocr/              __init__.py, base.py, rapid.py          (vision.py deleted)
  track/            __init__.py, pixels.py, changes.py, lifetimes.py, stage.py
  metrics.py groundtruth.py report.py
  subset.py         also imports a pre-re-base run directory
  costs.py          PRICES, estimate_cost (was part of diagnostics.py)
  textdiff.py       norm, similarity, levenshtein, lcp_len, myers, char_diff
  index.py          Node, open_db, index_nodes, search and fusion only (node extraction returns with `index`)
  overlay.py        drawing functions only (the stage wrapper returns with `annotate`)
  outline.py providers/ env.py jsonl.py     unchanged
tests/              one file per module above; files for deleted modules are deleted
configs/            p0-margin-000.toml, p0-margin-025.toml, p0-margin-100.toml (Task 12; used by P0 only)
```

Deleted on the branch: `merge.py`, `correspond.py`, `coalesce.py`, `diff.py`, `perceive.py`, `interpret.py`,
`hierarchy.py`, `agent.py`, `diagnostics.py`, `stage2a.py`, `prompts/`, `ocr/vision.py`, and their tests.

---

### Task 1: Remove the row machinery

**Files:**
- Delete: `src/scry/merge.py`, `correspond.py`, `coalesce.py`, `diff.py`, `perceive.py`, `interpret.py`, `hierarchy.py`,
  `agent.py`, `diagnostics.py`, `stage2a.py`, `src/scry/prompts/` (whole package); `tests/test_merge.py`,
  `test_correspond.py`, `test_coalesce.py`, `test_diff.py`, `test_perceive.py`, `test_interpret.py`, `test_hierarchy.py`,
  `test_agent.py`, `test_diagnostics.py`, `test_ocr.py`, `test_schemas.py`
- Create: `src/scry/costs.py`, `tests/test_costs.py`, `tests/test_package.py`
- Modify: `src/scry/schemas.py`, `run.py`, `cli.py`, `config.py`, `index.py`, `overlay.py`, `textdiff.py`, `scry.toml`,
  `tests/test_index.py`, `tests/test_textdiff.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `scry.costs.PRICES: dict[str, tuple[float, float, float]]` and
  `scry.costs.estimate_cost(usage: dict, model: str) -> float`, moved verbatim from `diagnostics.py`.
  `scry.schemas` keeps exactly `BBox`, `Stage1Record`, `RawWord`, `OcrLine`, `OutlineChapter` (the first and fourth are
  renamed or replaced in Tasks 3 and 4). `scry.textdiff` keeps `norm`, `similarity`, `levenshtein`, `lcp_len`, `myers`,
  `char_diff`.

**Rules:**
1. Delete the files listed (spec §8 "Removed"). `diff.py` goes whole: its `PixelSource` is rewritten in Task 7 from the
   rules there, not moved. After `git rm -r src/scry/prompts`, remove the directory itself (`rm -rf`, its `__pycache__`
   included): a leftover directory is a namespace package and `find_spec("scry.prompts")` would still find it.
2. `schemas.py`: remove every class and function except the five named above.
3. `run.py`: `Run` keeps `root`, `frames_dir`, `overlays_dir`, `cache_dir`, `stage1`, `outline`, `manifest`, `batches`,
   the manifest methods, `load_stage1`, `load_outline`, `chapter_of`, `video_id`. Remove every other path and loader.
4. `cli.py`: keep `decode`, `subset`, `setup`, `outline`, and `run` with `STAGES = ["outline", "decode"]` and without the
   diagnostics print. Remove every other command.
5. `config.py`: remove `MergeConfig`, `DiffConfig`, `Stage5Config`, `HierarchyConfig` and their `Config` fields; in
   `ModelConfig` remove `effort_stage2c`, `effort_stage5`, `effort_stage6`, `effort_agent`, every `stage2c_*` field and
   the validator (they return under new names with their stages). Remove the same keys and sections from `scry.toml`.
6. `index.py`: remove `region_text`, `extract_nodes`, `build_index`, the `Region` import and the inner imports; keep
   `Node`, the embedder classes, `get_embedder`, `open_db`, `_ensure_vec`, `index_nodes`, `_terms`, `fts_query`,
   `trigram_query`, `rrf`, `_filter_sql`, `search`.
7. `overlay.py`: remove `run_overlay` and the `Run`, `Config`, `config_hash` imports it alone needed; keep
   `place_label`, `draw_overlay`, `mask_image`, `scale_image`, the colour constants.
8. `textdiff.py`: remove `line_ops`, `pair_modifies`, the `DiffOp` import, and the clock rule (`_CLOCK`,
   `is_clock_change`; Decision D23).

**Returns with** (everything this plan deletes or reduces that a later plan must bring back; the deleted files are
recovered from tag `pre-rebase-boxes`, since they no longer exist on the branch; plans 2–4 are reconciled against this
table):

| Deleted or reduced here | What it was | Returns with |
|---|---|---|
| `perceive.py`, `prompts/stage2c.py`, `overlay.run_overlay` and the overlay's place in the pipeline, the `stage2c_*` and `effort_stage2c` config keys, `perceive._run_with_batches` (the batch path) | the labelling call, its prompt, the numbered-tag overlay it is shown, batch mode | plan 2, `annotate` |
| `merge.agreement` with `[merge] glyph_max_len`; `diagnostics.mark_match` | per-box agreement of two readings with the icon-glyph strip; the check that caught unreadable labels (L28–L30) | plan 2, loader side, only when transcribing |
| `interpret.py`, `prompts/stage5.py`, `Stage5Config` with `images = "scaled"`, `scale = 0.5` (the owner's default, L39) and its `crops`, `full` and `text` modes, `effort_stage5` | the interpretation of each transition | plan 3, `interpret` |
| `hierarchy.py`, `prompts/stage6.py`, `HierarchyConfig`, `effort_stage6` | steps, sections, the video | plan 3, `summarize` |
| `index.extract_nodes`, `build_index`, `region_text`; CLI `index` and `search` (storage, search and fusion stay in `index.py`) | the index build and the search command | plan 3, `index` |
| `agent.py`, `prompts/agent.py`, `effort_agent`, CLI `ask` | the answering agent and its prompt | plan 3, `ask` |
| `Run` paths and loaders of later stages; the full `run` wiring | `annotations`, `interpretations`, `steps`, `sections`, `video`, `index_db`; `run` beyond `track` | each stage's plan; plan 3 completes `run` |
| `diagnostics.diagnostics` (the manifest's diagnostics block and cost roll-up); `costs.py` stays | cost per stage and per run, which must now include cache-creation tokens | plan 4, evaluation |
| `outline` | not deleted: `outline.py` and its command stay unchanged here; exercised live after the re-base (L44) | — |

Gone for good, each by an owner's ruling: the row machinery (`merge`, `correspond`, `coalesce`, the row diff ops,
`Line`, `Region`, `FrameRecord`, the `VlmRegion` family), the Apple Vision adapter and PyObjC, caret and focus
attribution, transient folding, the clock rule and the `trivial` kind, the `confusable` flag.

**Tests to write first:**
- `tests/test_package.py::test_old_machinery_is_gone`: for each name in `merge, correspond, coalesce, diff, perceive,
  interpret, hierarchy, agent, diagnostics, stage2a, prompts`, `importlib.util.find_spec("scry." + name)` is `None`;
  `scry.schemas` has none of the attributes `Line, Region, FrameRecord, Transition, DiffOp, VlmRegion, VlmPerception,
  PerceptionRecord` (`Interpretation` and `HierNode` are not listed: plan 3 brings those names back).
- `tests/test_package.py::test_every_module_imports`: walking `pkgutil.walk_packages(scry.__path__, "scry.")` and
  importing each module raises nothing.
- `tests/test_costs.py::test_estimate_cost`: `estimate_cost({"input_tokens": 1_000_000, "output_tokens": 100_000,
  "cache_read_input_tokens": 0}, "claude-opus-5") == 7.5` (moved from `test_diagnostics.py`).
- In `tests/test_textdiff.py` delete `test_line_ops_scroll_is_equal_plus_inserts`, `test_pair_modifies_by_y_overlap`,
  `test_pair_modifies_keeps_unrelated_lines_apart`, `test_clock_change` and the `DiffOp`, `line_ops`, `pair_modifies`,
  `is_clock_change` imports. `tests/test_schemas.py` goes with the row schemas; its one test that is not about them,
  the config-hash check, returns in Task 3's `tests/test_config.py`. In
  `tests/test_index.py` delete `test_region_nodes_carry_association_text_as_one_searchable_line`.

- [ ] **Step 1:** Write `tests/test_package.py` and `tests/test_costs.py`. Run `uv run pytest tests/test_package.py -q`.
  Expected: FAIL (`find_spec("scry.merge")` is not None).
- [ ] **Step 2:** Apply rules 1–8 and the test edits.
- [ ] **Step 3:** Run `uv run pytest -q`. Expected: 0 failed. Run `uv run scry --help`. Expected: the commands `decode`,
  `outline`, `run`, `setup`, `subset` and no others.
- [ ] **Step 4:** Commit: `refactor!: remove the row machinery on rebase-boxes (spec §8); costs.py keeps cost accounting`

### Task 2: One OCR engine; drop the Apple Vision adapter

**Files:**
- Delete: `src/scry/ocr/vision.py`, `tests/test_vision.py`
- Modify: `src/scry/ocr/__init__.py`, `src/scry/config.py` (`OcrConfig`), `scry.toml`, `pyproject.toml`, `uv.lock`,
  `src/scry/cli.py` (`setup`)

**Interfaces:**
- Produces: `scry.ocr.get_engine(cfg) -> OcrEngine` returns a `RapidEngine` for `engine == "rapid"` and raises
  `ValueError` otherwise. `OcrConfig` has exactly `engine: Literal["rapid"] = "rapid"` and
  `gap_ratio: float = 0.25  # spacing guard: a gap of at least this × the box height between two words is a space`.

**Rules:**
1. Remove the Vision branch of `get_engine`, the Vision-only `OcrConfig` fields (`languages`, `language_correction`,
   `minimum_text_height`) and their `scry.toml` keys. Add `gap_ratio = 0.25` to the `[ocr]` section of `scry.toml`
   (the section becomes `[read]` in Task 3).
2. `pyproject.toml`: remove both `pyobjc-framework-*` dependencies; move `rapidocr>=3.9` and `onnxruntime>=1.20` from the
   `rapid` extra into `dependencies`; delete the `rapid` extra. Run `uv lock` then `uv sync`.
3. `RapidEngine.__init__` already reads `cfg.gap_ratio` when present; it now always is.

**Tests to write first:**
- `tests/test_rapid.py::test_get_engine_knows_only_rapid`: `get_engine(OcrConfig())` is a `RapidEngine` when
  `models_available()` (skip otherwise); `OcrConfig(engine="vision")` raises `pydantic.ValidationError`.
- `tests/test_rapid.py::test_gap_ratio_comes_from_config`: `RapidEngine(OcrConfig(gap_ratio=0.4)).gap_ratio == 0.4`
  (skip when models are unavailable).

- [ ] **Step 1:** Write the two tests. Run `uv run pytest tests/test_rapid.py -q`. Expected: FAIL on the `vision` literal.
- [ ] **Step 2:** Apply rules 1–3.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry setup` → prints `ocr engine rapid: ok`.
- [ ] **Step 4:** Commit: `refactor!: RapidOCR is the only reader; remove the Apple Vision adapter and PyObjC (spec §8)`

### Task 3: Names that follow the pipeline

**Files:**
- Rename: `src/scry/decode.py` → `src/scry/video.py`; `src/scry/stage1.py` → `src/scry/decode.py`;
  `tests/test_decode.py` → `tests/test_video.py`
- Modify: `src/scry/schemas.py`, `config.py`, `run.py`, `cli.py`, `settle.py`, `subset.py`, `scry.toml`, the body of the
  renamed `src/scry/decode.py` (`from scry.video import …`, `cfg.decode`, `Frame`, `run.frames`), `src/scry/ocr/__init__.py`,
  `src/scry/ocr/rapid.py` and `tests/test_rapid.py` (all three import `OcrConfig`, now `ReadConfig`; Task 2's two tests
  included), `tests/test_video.py` (its import), `tests/test_settle.py`, `tests/test_subset.py`, `tests/test_package.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `scry.video.video_info`, `scry.video.iter_frames` (unchanged signatures).
  - `scry.decode.run_decode(run: Run, cfg: Config, video: Path) -> None` (was `run_stage1`), writing `frames/` and
    **`frames.jsonl`**, manifest stage key **`decode`**, config hash `config_hash(cfg, "decode")`.
  - `scry.schemas.Frame` (was `Stage1Record`), fields unchanged: `video_id, frame, t_change, t_settled, t_end, settled,
    churn_regions, caret, width, height, sha256, png`.
  - `scry.config.DecodeConfig` (was `Stage1Config`) as `Config.decode`; `ReadConfig` (was `OcrConfig`) as `Config.read`;
    TOML sections `[decode.detect]`, `[decode.settle]`, `[decode.churn]`, `[decode.blink]`, `[read]`.
  - `Run.frames: Path` = `root / "frames.jsonl"`; `Run.load_frames() -> list[Frame]`. `Run.stage1` and `load_stage1` are
    removed.

**Rules:**
1. Pure renames; no behaviour changes in decoding, detection or settling. The content of a `frames.jsonl` line is
   byte-for-byte what a `stage1.jsonl` line was (spec §5).
2. Every config model (`Config` and each section) sets `model_config = ConfigDict(extra="forbid")`, so a stale
   `[merge]` or `[stage1]` section fails loudly instead of being ignored.
3. `cli.py`: `run`'s stage table uses `"decode"` for both the step name and the manifest key.
4. `subset.py` reads and writes `frames.jsonl` and the manifest key `decode` (legacy import is Task 5).

**Tests to write first:**
- `tests/test_config.py::test_sections_and_unknown_keys`: `load_config` of a TOML holding `[decode.settle]\nstill_s = 0.5`
  gives `cfg.decode.settle.still_s == 0.5`; a TOML holding `[stage1.settle]\nstill_s = 0.5` raises
  `pydantic.ValidationError`; so does `[read]\nlanguages = ["en"]`.
- `tests/test_config.py::test_repo_toml_loads`: `load_config(Path(__file__).resolve().parents[1] / "scry.toml")`
  succeeds and `cfg.read.engine == "rapid"` (anchored on the test file, not on the working directory).
- `tests/test_config.py::test_config_hash_is_stable_per_section` (re-homed from the deleted `tests/test_schemas.py`):
  `load_config(tmp_path / "missing.toml")` gives the defaults (`cfg.decode.detect.theta_comp == 24`);
  `config_hash(cfg, "decode") == config_hash(Config(), "decode")` and `!= config_hash(cfg, "read")`.
- `tests/test_package.py::test_old_machinery_is_gone` additionally asserts `find_spec("scry.stage1") is None` and that
  `scry.schemas` has no `Stage1Record`.
- `tests/test_subset.py` and `tests/test_settle.py`: update imports (`Frame`, `DecodeConfig`) and file names
  (`frames.jsonl`, manifest key `decode`); expectations otherwise unchanged.

- [ ] **Step 1:** Write `tests/test_config.py`, update the other tests. Run `uv run pytest tests/test_config.py -q`.
  Expected: FAIL (`Config` has no `decode`).
- [ ] **Step 2:** `git mv` the three files in this order — `src/scry/decode.py` → `video.py` first, then `stage1.py` →
  `decode.py`, then the test — and apply the renames and rules 1–4.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `refactor!: stages and config named for what they do: decode, video, [decode.*], [read], frames.jsonl`

### Task 4: Records and loaders

**Files:**
- Modify: `src/scry/schemas.py`, `src/scry/run.py`, `src/scry/overlay.py`, `tests/test_overlay.py`
- Create: `tests/test_schemas.py`

**Interfaces (all pydantic `BaseModel`, produced for every later task):**

```
Box          id: str ("b<n>", n from 1) · bbox: BBox · text: str · conf: float · words: list[RawWord] | None = None ·
             in_churn: bool = False
FrameBoxes   frame: int · png: str · engine: dict · seconds: float = 0.0 · boxes: list[Box] = []
PixelStats   changed_fraction: float · components: int · textless: int · textless_area: int ·
             touched_share: float · rect_only: int
BoxText      box: str ("<frame>:<box id>", e.g. "154:b31") · text: str
BoxChange    kind: Literal["reread", "appended", "truncated", "changed", "appeared", "removed"] · rect: BBox ·
             before: BoxText | None · after: BoxText | None · char_diff: list[list[str]] = [] ·
             continues: str | None = None ("T8/0": change id and record index) · in_churn: bool = False
Revert       of: str (a change id) · rect: BBox · hold_s: float
Change       id: str ("T<n>", n from 1) · from_frame: int · to_frame: int · t: tuple[float, float] ·
             kind: Literal["single", "unsettled"] · pixels: PixelStats | None ·
             records: list[BoxChange] = [] · moved: list[tuple[str, str]] = [] (box refs: earlier, later) ·
             same_place: int = 0 · unchanged: int = 0 · variants: int = 0 ·
             flicker_new: list[str] = [] · flicker_lost: list[str] = [] · reverts: list[Revert] = []
FrameTime    frame: int · t: float
Lifetime     id: str ("L<n>", n from 1) · text: str · readings: dict[str, list[int]] (reading → the frames at which
             it was sighted, ascending) · unstable: bool · sightings: int ·
             first: FrameTime · last: FrameTime · moved: bool = False · boxes: list[str] (box refs, frame order)
```

`Run` gains paths `boxes` (`boxes.jsonl`), `changes` (`changes.jsonl`), `lifetimes` (`lifetimes.jsonl`) and loaders
`load_boxes() -> list[FrameBoxes]`, `load_changes() -> list[Change]`, `load_lifetimes() -> list[Lifetime]`; each returns
`[]` when the file is absent. Helper `scry.schemas.box_ref(frame: int, box_id: str) -> str` and
`parse_box_ref(ref: str) -> tuple[int, str]`.

**Rules:**
1. Field names and shapes are those of spec §5 except where Decision D13 says otherwise: `records` is one list of
   `BoxChange` (no groups, spec §12; an `appeared` record has `before` null, a `removed` record has `after` null);
   `moved` is a list of box-ref pairs and `Lifetime.readings` carries frames, so that P0 can read H3 and H1; the fields
   `textless_area`, `rect_only`, `unchanged`, `variants`, `flicker_new`, `flicker_lost`, `BoxChange.in_churn` and
   `FrameBoxes.seconds` are additions; `FrameBoxes.engine` holds the adapter's whole `settings()` dict.
2. `OcrLine` is deleted; `overlay.py`'s functions take `list[Box]` and draw the label `box.id[1:]` exactly as they drew
   `line.id[1:]`. `tests/test_overlay.py` builds `Box` objects; its expectations do not change.
3. All models `extra="ignore"` (pydantic's default) so a later stage may add fields without breaking old files.

**Tests to write first (`tests/test_schemas.py`):**
- `test_records_round_trip_unicode`: a `FrameBoxes` with boxes `b1 "区" (24,164,48,179)` and
  `b2 "PS C:\\Users\\msadmin> az login" (659,352,904,371)` with one word; a `Change` with one `BoxChange` of kind `appended`,
  one `appeared` record (`before` null), one moved pair `("0:b4", "1:b3")`, one `Revert`, `pixels=None`; a `Lifetime`
  whose `readings` has two keys, `{"A b": [0, 2], "Ab": [1]}`. Write each with `write_jsonl`, read back with
  `read_jsonl`: equal to the originals.
- `test_box_ref_round_trip`: `box_ref(154, "b31") == "154:b31"`; `parse_box_ref("154:b31") == (154, "b31")`;
  `parse_box_ref("b31")` raises `ValueError`.
- `test_loaders_return_empty_lists_on_a_fresh_run`: a `Run(tmp_path / "r")` loads `[]` from all four loaders.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_schemas.py -q`. Expected: FAIL (`ImportError: Box`).
- [ ] **Step 2:** Add the models, paths, loaders and helpers; adapt `overlay.py` and its test.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat: records for boxes mode (Box, Change, Lifetime) and their loaders (spec §5)`

### Task 5: `subset` imports a pre-re-base run directory

**Files:**
- Modify: `src/scry/subset.py`, `tests/test_subset.py`

**Interfaces:**
- Consumes: `Frame`, `Run.frames`, manifest key `decode`.
- Produces: `make_subset(src_root: Path, out: Path, frames: tuple[int, int], share_cache: bool = True) -> Run`. The
  first parameter becomes a path (was a `Run`): constructing a `Run` creates directories, and the source must not be
  written to.

**Rules:**
1. Source records: if `src_root / "stage1.jsonl"` exists read it, else read `src_root / "frames.jsonl"`; validate every
   line as `Frame`. (A pre-re-base directory's `frames.jsonl` is the old merged file and is never read when
   `stage1.jsonl` is present.)
2. Source manifest stage entry: `stages["decode"]` if present, else `stages["stage1"]`; neither → `ValueError`. The
   entry is written under `stages["decode"]` of the new manifest with `emitted` and `settled` recomputed for the range;
   `subset = {"source": str(src_root), "frames": [lo, hi]}` as today.
3. Nothing is created, modified or deleted under `src_root`. Frame PNGs are copied; frame numbers are kept.
4. The CLI passes the path. `--share-cache` keeps its meaning and default, with one case now defined: when the source
   has no `cache/` directory no link is made (nothing is ever created under the source, and a dangling link would make
   `Run(out)` fail). For a legacy source the closing message says to run the stage commands, not `scry run` (D6).

**Tests to write first:**
- `test_subset_imports_a_legacy_directory`: build a source by hand under `tmp_path / "old"`: `stage1.jsonl` with 4
  `Frame` lines (frames 0–3), a `frames.jsonl` containing the single line `{"not": "a frame"}`, 8×8 PNGs, and a
  manifest `{"video": "v.mp4", "video_id": "v", "stages": {"stage1": {"inputs": "v.mp4:abc", "config": "cfg",
  "emitted": 4, "settled": 3}}}`. `make_subset(old, tmp_path / "new", (1, 2), share_cache=False)`: the new
  `frames.jsonl` holds frames 1 and 2; the new manifest has `stages.decode.emitted == 2` and no `stage1` key; the
  listing of `old` is unchanged (same file names and sizes).
- Existing tests adapted to the path parameter.

- [ ] **Step 1:** Write the test. Run `uv run pytest tests/test_subset.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–4.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat: subset imports a pre-re-base run directory without touching it`

### Task 6: `read`

**Files:**
- Create: `src/scry/read.py`, `tests/test_read.py`
- Modify: `src/scry/cli.py`

**Interfaces:**
- Consumes: `Run.load_frames`, `get_engine`, `OcrEngine`, `RawLine`, `Box`, `FrameBoxes`.
- Produces: `assign_ids(raw: list[RawLine], churn: list[BBox]) -> tuple[list[Box], int]` (boxes, dropped-empty count);
  `run_read(run: Run, cfg: Config, engine: OcrEngine | None = None) -> None` writing `boxes.jsonl`; CLI
  `scry read RUN_DIR [--config PATH] [--verbose]`; `run` gains the stage `read` after `decode`.

**Rules:**
1. A raw line whose text is empty after `str.strip()` is dropped and counted (Decision D5).
2. **Reading order and ids:** the remaining lines are sorted by `(bbox[1], bbox[0])` (top edge, then left edge) and
   numbered `b1`, `b2`, … . This order is the pipeline's only definition of reading order (Decision D7).
3. `in_churn` is true when the box intersects any of the frame's `churn_regions`.
4. One `FrameBoxes` per frame in frame order: `png` copied from the `Frame`, `engine = engine.settings()`, `seconds`
   the wall time of `recognize`, rounded to 3 places. Text, `conf`, `bbox` and `words` are the adapter's, unaltered.
5. Inputs `[run.frames]`, config hash `config_hash(cfg, "read")`, manifest key `read`, stats `frames`, `boxes`,
   `dropped_empty`, `seconds`, `engine`. The engine is RapidOCR with `use_cls` off and `rec_batch_num` 1 (already the
   adapter's settings, ledger L43); no second pass of any kind (spec §6).

**Tests to write first (`tests/test_read.py`, with a fake engine class returning fixed `RawLine`s):**
- `test_assign_ids_reading_order_and_churn`: raw lines `("second", 0.9, (10,40,90,58))`, `("first", 0.95, (10,10,90,28))`,
  `("right", 0.8, (200,10,260,28))`; churn `[(0,35,100,60)]` → ids and texts `[("b1","first"), ("b2","right"),
  ("b3","second")]`; `in_churn` is `[False, False, True]`; dropped count 0.
- `test_read_drops_empty_text`: raw lines `("  ", 0.5, (200,10,210,28))` and `("x", 0.9, (10,10,20,28))` → one box `b1`
  `"x"`; dropped count 1.
- `test_run_read_writes_boxes_and_skips_when_up_to_date`: a run with two `Frame`s and two 8×8 PNGs; a fake engine that
  counts calls → `boxes.jsonl` has two records with `engine == {"engine": "fake"}`; manifest `stages.read.frames == 2`;
  a second `run_read` makes no further engine calls; after rewriting `frames.jsonl` with a changed `sha256` it runs again.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_read.py -q`. Expected: FAIL (`No module named scry.read`).
- [ ] **Step 2:** Implement rules 1–5 and the CLI command.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat: read stage: OCR boxes per frame in reading order (spec §6)`

### Task 7: Changed pixels: labelled components, margin, touch

**Files:**
- Modify: `src/scry/detect.py`, `tests/test_detect.py`
- Create: `src/scry/track/__init__.py` (empty), `src/scry/track/pixels.py`, `tests/test_track_pixels.py`

**Interfaces:**
- Produces, in `detect.py`: `label_components(changed: np.ndarray, theta_min: int) -> tuple[np.ndarray, list[Component]]`.
  `components(changed, theta_min)` is left exactly as it is (it runs on `decode`'s per-video-frame path); the two may
  share a private helper, and the first test below pins that they agree.
- Produces, in `track/pixels.py`:
  - `@dataclass(frozen=True) PixelDiff`: `labels: np.ndarray` (int32, frame-shaped), `components: list[Component]`,
    `changed_fraction: float`.
  - `class PixelSource(root: Path, detect: DetectParams, keep: int = 8)` with `gray(frame: Frame) -> np.ndarray | None`
    and `diff(a: Frame, b: Frame) -> PixelDiff | None`.
  - `margin_px(a_boxes: list[Box], b_boxes: list[Box], margin: float) -> int`
  - `grow(bbox: BBox, m: int, shape: tuple[int, int]) -> BBox`
  - `touched(bbox: BBox, diff: PixelDiff, m: int) -> bool`; `touched_by(bbox, diff, m) -> set[int]` (component numbers);
    `touched_by_rect(bbox: BBox, diff: PixelDiff, m: int) -> bool`

**Rules:**
1. `label_components` (spec §6 `track` step 1): `decode`'s rule exactly — 3×3 dilation, 8-connected labelling, a
   component's area is its count of *changed* pixels, components under `theta_min` dropped. `labels[y, x] = k` for every
   changed pixel of the k-th **kept** component, k = 1-based position in the returned list (scipy's label order among
   the kept ones); 0 everywhere else, including the dilation halo and changed pixels of dropped components. Fewer than
   `theta_min` changed pixels in all → `(zeros, [])`.
2. `gray`: open `root / frame.png` with Pillow, convert to RGB, then
   `av.VideoFrame.from_ndarray(rgb, format="rgb24").to_ndarray(format="gray")` — swscale's path, which is within one
   level of `decode`'s gray (ledger L32); it is the same call the pre-re-base `PixelSource.gray` made, which can be read
   from tag `pre-rebase-boxes`. `None` when `frame.png` is empty or the file is missing. The last `keep`
   grays are cached by frame number.
3. `diff`: `None` when either gray is `None` or the shapes differ. Otherwise `change_map(a, b, detect.theta_pix)` at
   full resolution (the `downsample` setting is ignored: `track` runs once per emitted pair), `label_components(...,
   detect.theta_min)`, `changed_fraction = round(float(changed.mean()), 6)` over all changed pixels.
4. `margin_px = floor(margin × median + 0.5)`, `median` = `statistics.median` of `y1 − y0` over the boxes of **both**
   frames; 0 when there are no boxes or `margin` is 0 (spec step 2).
5. `grow` expands by `m` on every side and clips to `(0, 0, width, height)`.
6. `touched` (H6): true when `diff.labels` has a non-zero value inside the grown box. `touched_by` returns the set of
   those values. `touched_by_rect`: true when the grown box intersects any component's `bbox`; it exists only for the
   `rect_only` diagnostic that lets P0 judge H6.

**Tests to write first:**
- `tests/test_detect.py::test_label_components_agrees_with_components`: `prev = zeros((60,160), uint8)`; `cur`:
  `[20:30, 40:41] = 255`, `[20:30, 100:106] = 255`, and the pixels `(10,5)`, `(10,30)`, `(10,55)` = 40; θpix 12, θmin 8.
  Expected: the list equals `components(...)` and is `[Component(10, (40,20,41,30)), Component(60, (100,20,106,30))]`;
  `(labels == 1).sum() == 10`; `(labels == 2).sum() == 60`; `labels[10, 5] == 0`; `labels[19, 39] == 0`;
  `labels.max() == 2`; `labels.dtype == int32`. With only the three noise pixels: `(zeros, [])`.
- `test_track_pixels.py::test_touch_margin_edges`: the `PixelDiff` of that fixture; box `(50,18,90,32)`: `touched` is
  `False` for `m = 9` (grown `(41,9,99,41)`; the stem at x = 40 is outside) and `True` for `m = 10` (grown
  `(40,8,100,42)`; x = 40 is inside, and the glyph at x = 100 is not because x1 is exclusive);
  `touched_by(..., 10) == {1}`.
- `::test_touch_is_on_pixels_not_rectangles` (H6): `prev` zeros `(60,160)`; `cur` a hollow outline: `[10:50, 20:21]`,
  `[10:50, 139:140]`, `[10:11, 20:140]`, `[49:50, 20:140]` = 255 → one component, `bbox (20,10,140,50)`, `area 316`. Box
  `(60,25,100,35)`, `m = 5`: `touched` is `False`, `touched_by_rect` is `True`.
- `::test_grow_clips`: `grow((2,3,10,12), 5, (60,160)) == (0,0,15,17)`.
- `::test_margin_px`: heights `[10, 20]` and `[30]`, margin 0.5 → 10; a single height 21 → 11; no boxes → 0; margin 0 → 0.
- `::test_pixel_source_diff_and_degenerate`: write two 40×60 (h×w) `L`-mode PNGs, one black, one black with
  `[10:20, 10:30] = 255`; `diff` → one component, `bbox (10,10,30,20)`, `area 200`, `changed_fraction 0.083333`. A
  `Frame` whose PNG is missing → `diff` is `None`. A second frame of 20×30 → `None`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_pixels.py tests/test_detect.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed (the existing `test_detect.py` and `test_settle.py` tests still pass:
  `components` did not change).
- [ ] **Step 4:** Commit: `feat(track): labelled changed components, relative margin, touch tested on pixels (H6)`

> **Shared fixtures for Tasks 8–10.** Frame shape `(200, 400)`. `mk(id, x0, y0, x1, y1, text)` builds a `Box` with
> `conf = 1.0`. `block(labels, k, y0, y1, x0, x1)` sets `labels[y0:y1, x0:x1] = k` and returns the matching
> `Component(area, (x0, y0, x1, y1))`. A `PixelDiff` is built directly from such labels; `changed_fraction` is the
> labelled pixel count / 80,000. Every box is 18 px tall unless a test says otherwise, so `margin 0.5` gives `m = 9`.
> **Fixture K (a keystroke):** frame 0 boxes `b1 "Title" (10,10,110,28)`, `b2 "PS>" (10,50,130,68)`,
> `b3 "区" (300,150,330,168)`; frame 1 boxes `b1 "Title" (10,10,110,28)`, `b2 "PS> git status" (10,50,230,68)`;
> one component `block(labels, 1, 52, 66, 140, 228)` (area 1,232, `changed_fraction 0.0154`).

### Task 8: `track` steps 2–3: touched boxes, and untouched boxes are unchanged

**Files:**
- Create: `src/scry/track/changes.py`, `tests/test_track_unchanged.py`

**Interfaces:**
- Consumes: `Box`, `PixelDiff`, `touched`.
- Produces:
  - `intersection(a: BBox, b: BBox) -> int` (area, 0 when none)
  - `match_one_to_one(cands: list[tuple[int, int, int]]) -> list[tuple[int, int]]` — candidates are
    `(area, index_in_a, index_in_b)`; returns index pairs
  - `touched_flags(boxes: list[Box], diff: PixelDiff | None, m: int) -> list[bool]`
  - `match_unchanged(a_boxes: list[Box], b_boxes: list[Box], ta: list[bool], tb: list[bool]) -> list[tuple[int, int]]`
    (index pairs, ordered by index in *b*)

**Rules:**
1. **Touched** (spec step 2): with `diff is None` every box of both frames is touched; otherwise `touched(box.bbox, diff, m)`.
2. **One-to-one matching** (used here and in Tasks 9 and 10): sort candidates by area descending, then `index_in_a`,
   then `index_in_b` ascending; walk the list taking a pair when neither side is taken. Indices are positions in
   reading order.
3. **Untouched boxes are unchanged** (H1, spec step 3): candidates are every untouched box of *a* with every untouched
   box of *b* it intersects. The matched pairs are `unchanged`; their texts may differ (a variant reading, never a
   change).
4. Nothing else is decided here. Every box not in an unchanged pair goes on to Tasks 9 and 10 carrying its touched
   flag. There are no pools (spec §12, "Simplify before repairing"; Decision D8).

**Tests to write first:**
- `test_keystroke_touched_and_unchanged`: fixture K, `m = 9` → `touched_flags` of frame 0 is `[False, False, False]`
  (`a.b2` grown is `(1,41,139,77)`; the component starts at x = 140) and of frame 1 `[False, True]`;
  `match_unchanged == [(0, 0)]`.
- `test_one_to_one_when_two_later_boxes_claim_one_earlier_box`: no changed pixels (`labels` zeros, no components); *a*
  `b1 "Authentication and Authorization Local accounts" (10,100,390,118)`; *b* `b1 "Authentication and Authorization"
  (10,100,200,118)`, `b2 "Local accounts" (220,100,390,118)`. Areas 190 × 18 = 3,420 and 170 × 18 = 3,060 →
  `match_unchanged == [(0, 0)]`; index 1 of *b* is in no pair (Task 10 reports it as `flicker_new`).
- `test_no_pixels_means_everything_is_touched`: `diff=None`; *a* `b1 "x" (0,0,10,10)`, *b* `b1 "x" (0,0,10,10)` →
  both flag lists are `[True]`; `match_unchanged == []`.
- `test_match_one_to_one_tie_breaks`: candidates `[(50,0,1), (50,0,0), (40,1,0)]` → sorted `(50,0,0), (50,0,1),
  (40,1,0)`; `(0,0)` is taken, `(0,1)` is refused because a 0 is taken, `(1,0)` is refused because b 0 is taken →
  result `[(0,0)]`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_unchanged.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–4.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(track): touched boxes; untouched boxes are unchanged at any changed fraction (H1)`

### Task 9: `track` steps 4–5: same place, and moves

**Files:**
- Modify: `src/scry/track/changes.py`
- Create: `tests/test_track_moves.py`

**Interfaces:**
- Produces: `same_place(before: list[Box], after: list[Box], touched_a: set[str], touched_b: set[str]) ->
  tuple[list[tuple[Box, Box]], list[Box], list[Box]]` and `cancel_moves(before, after, touched_a, touched_b)` with the
  same return shape; each returns its pairs and the two remaining lists in reading order. `before` and `after` are the
  boxes Task 8 left outside the unchanged pairs; `touched_a` and `touched_b` are the ids of the touched ones.

**Rules:**
1. **Text equality here is exact string equality** (Decision D11). Whitespace-blind comparison is for kind labels only (H4).
2. **Same place, same text** (spec step 4): candidates are pairs that intersect, have equal text and have at least
   one touched box; matched one to one by Task 8's rule 2. (With real box geometry a scroll of less than one box
   height leaves equal texts intersecting, so such a row is counted here, not as a move; either way it is no change.)
3. **Moves** (H3, spec step 5): only touched boxes take part on either side, because an untouched box cannot have
   moved (H1; Decision D22). For every text present among the remaining touched boxes of both lists, the k-th
   occurrence in `before` is paired with the k-th occurrence in `after` (reading order), up to the smaller count,
   anywhere in the frame. Untouched boxes pass through to the remaining lists.

**Tests to write first** (every box is touched unless a test says otherwise):
- `test_highlight_over_unchanged_text_is_same_place`: `before [b1 "Overview" (10,130,100,148)]`, `after` the same →
  one pair, both remaining lists empty.
- `test_scroll_cancels_as_moves`: `before b1 "alpha" (10,20,100,38)`, `b2 "beta" (10,40,100,58)`, `b3 "gamma"
  (10,60,100,78)`; `after b1 "beta" (10,20,100,38)`, `b2 "gamma" (10,40,100,58)`, `b3 "delta" (10,60,100,78)` →
  `same_place` finds nothing (rows 20–38 and 40–58 do not intersect); `cancel_moves` pairs `(a.b2, b.b1)` and
  `(a.b3, b.b2)`; remaining `before` ids `["b1"]`, `after` ids `["b3"]`.
- `test_duplicates_pair_same_place_first_then_reading_order`: `before b1 "1.24.10" (10,10,60,28)`, `b2 "1.24.10"
  (10,100,60,118)`; `after b1 "1.24.10" (10,100,60,118)`, `b2 "1.24.10" (200,120,250,138)` (ids in reading order on
  both sides) → `same_place` pairs `(a.b2, b.b1)`; then `cancel_moves` pairs `(a.b1, b.b2)`; both lists empty.
  Pairing k-th with k-th alone would have crossed them.
- `test_whitespace_difference_is_not_equal_here`: `"Open in mobile Give feedback"` and `"Open in mobileGive feedback"`
  at the same rectangle → no pair from either function; both remain (Task 10 pairs them as a `reread`).
- `test_only_touched_boxes_move`: `before b1 "x" (10,10,30,28)` untouched, `b2 "x" (10,40,30,58)` touched; `after b1
  "x" (200,100,220,118)` touched → `cancel_moves` pairs `(a.b2, b.b1)`; `before` keeps `b1`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_moves.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–3.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(track): same-place pairs and whole-transition move cancellation (H3)`

### Task 10: `track` steps 6–8: one record per changed box, kinds, appeared, removed, flicker, pixel statistics

**Files:**
- Modify: `src/scry/track/changes.py`
- Create: `tests/test_track_pair.py`

**Interfaces:**
- Produces:
  - `kind_of(before: str, after: str) -> Literal["reread", "appended", "truncated", "changed"]`
  - `pair_rest(before: list[Box], after: list[Box], touched_a: set[str], touched_b: set[str]) ->
    tuple[list[tuple[Box, Box]], list[Box], list[Box]]` (pairs, remaining before, remaining after)
  - `@dataclass Pairing`: `a: str`, `b: str` (box ids), `how: Literal["unchanged", "same_place", "moved", "reread"]`
  - `@dataclass PairResult`: `change: Change`, `pairings: list[Pairing]`, `starts: list[str]` (box ids of *b* whose
    lifetime starts here)
  - `track_pair(a: Frame, b: Frame, a_boxes: list[Box], b_boxes: list[Box], diff: PixelDiff | None, margin: float) -> PairResult`

**Rules:**
1. **Pairing** (H2; spec §12): candidates are every remaining before box with every remaining after box it
   intersects, where at least one of the two is touched; matched one to one by Task 8's rule 2, so the greatest
   intersection wins and a sliver overlap with a neighbouring line cannot take a box from its own earlier self. The
   partner may be untouched: a growing text's shorter self usually lies outside the changed pixels, and so does a
   shrinking text's shorter self. One candidate rule serves both directions (Decision D8). No groups, no connected
   components, no pools (Decision D12).
2. **Records.** Each pair is one `BoxChange`: `kind` by rule 3, `before` and `after` as `BoxText(box_ref(frame, id),
   text)`, `rect` the union of the two boxes, `char_diff = textdiff.char_diff(before_text, after_text)` on the exact
   two strings, `in_churn` when either box is. A touched after box left without a partner is an `appeared` record
   (`before` null, `rect` its box, `char_diff` empty); a touched before box left without a partner is a `removed`
   record (spec step 7). An **untouched** box left without a partner is flicker (Decision D9): no record,
   `flicker_new` (from *b*) or `flicker_lost` (from *a*). Order of `records`: pair and `appeared` records by the later
   box's reading order, then `removed` records by the earlier box's reading order. One record shape for any size of
   change (H5): a keystroke is one record, a page load is many `appeared` and `removed` records.
3. **Kind** (H4): `kind_of` removes all whitespace from both texts (`"".join(s.split())`) and returns `reread` when
   equal, `appended` when the after string starts with the before string, `truncated` when the before string starts
   with the after string, else `changed`. Exactly equal texts never reach here (Task 9 rule 2 has taken every such
   pair), so a `reread` always carries two strings that differ in whitespace only.
4. **Lifetimes:** each `unchanged`, `same_place` and move pair is a `Pairing`; a `reread` record is a
   `Pairing(how="reread")`; for every other pair record the after id goes to `starts` (its before box's lifetime simply
   stops). `appeared` and `flicker_new` ids go to `starts`. `pairings` are ordered by *b*'s reading order; `starts` is in
   reading order.
5. **Statistics:** `unchanged`, `variants` (unchanged pairs whose texts differ), `same_place` (counts); `moved` as the
   list of `(box_ref(a), box_ref(b))` pairs in *b*'s reading order, so P0 can read H3; `flicker_new`, `flicker_lost` as
   box refs. `pixels` is `None` when `diff` is; otherwise `components = len(diff.components)`; a component is
   **textless** when no box of either frame has it in its `touched_by` set (spec step 8): `textless` counts them and
   `textless_area` sums their areas; `touched_share = round((|touched_a| + |touched_b|) / (boxes of a + boxes of b), 4)`,
   `0.0` with no boxes; `rect_only` = boxes of either frame with `touched_by_rect` true and `touched` false.
6. The returned `Change` has `id = ""`, `kind = "single"`, `t = (a.t_end, b.t_settled)`, `reverts = []` and every
   record's `continues = None`; the stage fills them in Task 12.

**Tests to write first:**
- `test_kind_of`: `("PS>", "PS> git status")` → `appended`; `("PS> git status", "PS>")` → `truncated`;
  `("Status : Creating", "Status : Succeeded")` → `changed`; `("Open in mobile Give feedback", "Open in mobileGive
  feedback")` → `reread`.
- `test_keystroke_is_one_appended_record` (H2): fixture K, frames 0 and 1, margin 0.5. `a.b2` is untouched (Task 8) and
  `b.b2` is touched; they intersect over 120 × 18 = 2,160 → exactly one record: `kind "appended"`, `rect (10,50,230,68)`,
  `before ("0:b2", "PS>")`, `after ("1:b2", "PS> git status")`, `char_diff [["=", "PS>"], ["+", " git status"]]`.
  `unchanged == 1`, `variants == 0`, `moved == []`, `same_place == 0`, `flicker_lost == ["0:b3"]`, `flicker_new == []`.
  `pixels`: `changed_fraction 0.0154`, `components 1`, `textless 0`, `textless_area 0`, `touched_share 0.2` (one touched
  box of five), `rect_only 0`. `pairings == [Pairing("b1", "b1", "unchanged")]`, `starts == ["b2"]`.
- `test_truncation_pairs_with_the_untouched_later_box`: *a* `b1 "PS> git status" (10,50,230,68)`; *b* `b1 "PS>"
  (10,50,130,68)`; the component of fixture K. `a.b1` is touched, `b.b1` is not (grown `(1,41,139,77)`) → one record,
  `kind "truncated"`, `char_diff [["=", "PS>"], ["-", " git status"]]`; no flicker; `starts == ["b1"]`.
- `test_adjacent_overlapping_lines_pair_with_their_own_earlier_selves` (boxes 20 px tall at a 17-px pitch, the
  geometry RapidOCR gives terminal lines; margin 0.5 → `m = 10`): *a* `b1 "cmd1 output" (10,40,300,60)`, `b2 "PS>"
  (10,57,70,77)`; *b* `b1 "cmdl output" (10,40,300,60)`, `b2 "PS> git status" (10,57,200,77)`; `block(labels, 1, 60, 75,
  80, 198)`. Touched: `a.b1`, `b.b1`, `b.b2` (`a.b2` grown is `(0,47,80,87)`; the block starts at x = 80). Candidate
  areas: `(a.b1, b.b1)` 290 × 20 = 5,800; `(a.b2, b.b2)` 60 × 20 = 1,200; `(a.b1, b.b2)` 190 × 3 = 570; `(a.b2, b.b1)`
  60 × 3 = 180 → two records in this order: `changed` `"cmd1 output"` → `"cmdl output"`, and `appended` `"PS>"` →
  `"PS> git status"` with `char_diff [["=", "PS>"], ["+", " git status"]]`. `touched_share == 0.75`; `starts == ["b1",
  "b2"]`; `pairings == []`.
- `test_char_diff_reassembles_both_sides`: `"Status : Creating"` → `"Status : Succeeded"` at one rectangle under a
  changed block: the record is `changed`; joining the `=` and `-` runs gives the before text and the `=` and `+` runs
  the after text. (No exact run list is asserted: Myers may choose among equal-cost scripts.)
- `test_reread_record_continues_the_lifetime`: `"Open in mobile Give feedback"` in *a* and `"Open in mobileGive
  feedback"` in *b*, both at `(10,10,300,28)` under `block(labels, 1, 10, 28, 10, 300)` → one record, `kind "reread"`;
  `pairings == [Pairing("b1", "b1", "reread")]`; `starts == []`.
- `test_resplit_is_one_record_and_one_appeared_box` (the known cost of having no groups): *a* `b1 "File Edit View"
  (10,10,200,28)`; *b* `b1 "File" (10,10,50,28)`, `b2 "Edit View" (60,10,200,28)`; `block(labels, 1, 10, 28, 10, 200)`.
  Areas 40 × 18 = 720 and 140 × 18 = 2,520 → `a.b1` pairs with `b.b2`. `records`: an `appeared` record for `"1:b1"`
  `"File"`, then a `changed` record `"File Edit View"` → `"Edit View"` (`FileEditView` and `EditView` are neither equal
  nor prefixes of one another). `starts == ["b1", "b2"]`; `pairings == []`.
- `test_popup_appears_and_a_textless_component`: *a* `b1 "Title" (10,10,110,28)`; *b* the same plus `b2 "Cloud Shell"
  (300,100,380,118)`; `block(labels, 1, 96, 122, 296, 384)` and `block(labels, 2, 180, 190, 350, 360)` → `records` is one
  `appeared` record (`before` null, `after ("1:b2", "Cloud Shell")`, `rect (300,100,380,118)`); `unchanged == 1`;
  `pixels.components == 2`, `textless == 1`, `textless_area == 100`, `touched_share == 0.3333`.
- `test_scroll_is_mostly_moved` (H3, H5): Task 9's scroll fixture under `block(labels, 1, 20, 78, 10, 100)` → `moved ==
  [("0:b2", "1:b1"), ("0:b3", "1:b2")]`; `records`: `appeared` `"1:b3"` `"delta"`, then `removed` `"0:b1"` `"alpha"`
  (they do not intersect, so they are not paired).
- `test_untouched_leftover_is_flicker_not_a_change` (H1): Task 8's fixture of one earlier box and two later boxes with
  no changed pixels → `records == []`, `unchanged == 1`, `variants == 1`, `flicker_new == ["1:b2"]`, `starts == ["b2"]`.
- `test_variant_on_untouched_pixels_is_not_a_change` (H1): *a* `b1 "Subscription ID :3e6b" (10,100,200,118)`; *b* `b1
  "SubscriptionID :3e6b" (10,100,201,119)`; no changed pixels → `unchanged == 1`, `variants == 1`, no records.
- `test_no_boxes_at_all`: both box lists empty, one component → `records == []`, `pixels.textless == 1`,
  `touched_share == 0.0`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_pair.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6; `track_pair` composes Tasks 7–9 and rule 1 in the spec's order: touched,
  unchanged, same place, moves, pairing, leftovers.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(track): one change record per changed box: whitespace-blind kinds, appeared, removed, flicker (H2, H4, H5)`

### Task 11: Lifetimes

**Files:**
- Create: `src/scry/track/lifetimes.py`, `tests/test_track_lifetimes.py`

**Interfaces:**
- Consumes: `PairResult`, `Pairing`, `Frame`, `Box`, `Lifetime`, `FrameTime`, `box_ref`.
- Produces: `class LifetimeBuilder` with `first_frame(frame: Frame, boxes: list[Box]) -> None`,
  `step(b: Frame, b_boxes: list[Box], result: PairResult) -> None`, `finish() -> list[Lifetime]`.

**Rules:**
1. `first_frame`: every box starts a lifetime. Ids `L1`, `L2`, … in creation order; within a frame, the reading order
   of the starting boxes.
2. `step`: each `Pairing` appends *b*'s box to the lifetime that holds *a*'s box and records *b*'s frame number under
   *b*'s text in `readings`; `how == "moved"` sets `moved`. Each id in `starts` begins a lifetime. A lifetime that is
   not continued simply stops. Every box of *b* must be in exactly one of the pairings or `starts`, else `ValueError`
   naming the box.
3. `finish`: `readings` maps each reading to the ascending list of frames at which it was sighted, so P0 can open the
   frame where a variant occurred. `text` is the reading sighted at the most frames; a tie goes to the reading sighted
   first (spec principle 5: de-noising of repeated readings; a text seen once has its one reading). `unstable =
   len(readings) > 1`. `sightings = len(boxes)`. `first = FrameTime(frame, t_settled)` of the first box's frame;
   `last = FrameTime(frame, t_end)` of the last box's frame (Decision D15). Sorted by id number.
4. Nothing here reads how long a text lasted as evidence of anything; the fields are measurements.

**Tests to write first:**
- `test_lifetimes_over_three_frames`: frames 0, 1, 2 with `(t_settled, t_end)` = `(0.0, 1.0)`, `(1.5, 2.0)`, `(2.5,
  9.0)`. Frame 0 boxes `b1 "Title"`, `b2 "PS>"`. Step to frame 1 (boxes `b1 "Title"`, `b2 "PS> git status"`):
  pairings `[("b1","b1","unchanged")]`, `starts ["b2"]`. Step to frame 2 (boxes `b1 "Title"`, `b2 "PS> git
  status"`, `b3 "On branch main"`): pairings `[("b1","b1","unchanged"), ("b2","b2","unchanged")]`, `starts ["b3"]`.
  Expected: `L1 "Title"` boxes `["0:b1","1:b1","2:b1"]`, sightings 3, `readings {"Title": [0, 1, 2]}`, first `(0, 0.0)`,
  last `(2, 9.0)`, stable; `L2 "PS>"` boxes `["0:b2"]`, first `(0, 0.0)`, last `(0, 1.0)`; `L3 "PS> git status"` boxes
  `["1:b2","2:b2"]`, first `(1, 1.5)`, last `(2, 9.0)`; `L4 "On branch main"` boxes `["2:b3"]`.
- `test_majority_reading_and_tie`: one box followed over frames 0, 1, 2 reading `"Subscription ID"`,
  `"SubscriptionID"`, `"Subscription ID"` → `text "Subscription ID"`, `readings {"Subscription ID": [0, 2],
  "SubscriptionID": [1]}`, `unstable`; over frames 0, 1 reading `"A b"`, `"Ab"` → `text "A b"`.
- `test_moved_sets_the_flag`: frame 0 box `b1 "beta"`, step to frame 1 with pairings `[("b1","b1","moved")]` → `L1.moved`
  is true and `sightings == 2`.
- `test_unaccounted_box_raises`: frame 1 has boxes `b1`, `b2`; a `PairResult` with pairings `[("b1","b1","unchanged")]`
  and `starts []` → `ValueError` whose message contains `b2`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_lifetimes.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–4.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(track): box lifetimes with majority readings and the frames of each variant (H7)`

### Task 12: The `track` stage: ids, kinds, `continues`, `reverts`, files, CLI

**Files:**
- Create: `src/scry/track/stage.py`, `tests/test_track_stage.py`, `configs/p0-margin-000.toml`,
  `configs/p0-margin-025.toml`, `configs/p0-margin-100.toml`
- Modify: `src/scry/config.py` (`TrackConfig`), `scry.toml`, `src/scry/cli.py`, `tests/test_config.py`

**Interfaces:**
- Produces: `TrackConfig` as `Config.track` with `margin: float = 0.5  # × the median box height of the two frames; 0 =
  exact touch`; TOML `[track] margin = 0.5`. `transition_kind(a: Frame, b: Frame) -> Literal["single", "unsettled"]`;
  `link_continues(prev: Change | None, cur: Change) -> None`; `find_reverts(prev: Change, prev_diff: PixelDiff | None,
  zb: PixelDiff | None, a: Frame, b: Frame) -> list[Revert]`; `run_track(run: Run, cfg: Config) -> None`; CLI
  `scry track RUN_DIR [--config PATH] [--verbose]`; `run` gains `track` after `read`.
- The three `configs/p0-margin-*.toml` files are complete copies of `scry.toml` whose only difference is `[track]
  margin` = `0.0`, `0.25`, `1.0`. They are committed so that P0's margin runs never depend on editing a config by
  pattern (Task 16).

**Rules:**
1. Pairs are consecutive records of `frames.jsonl`. Boxes come from `boxes.jsonl` by frame number; a frame without a
   boxes record raises `ValueError("… run `scry read` first")`. Change ids `T1`, `T2`, … in order.
2. `transition_kind`: `unsettled` when either frame is not `settled`, else `single`. There is no `trivial` kind and no
   clock rule (owner's ruling, spec §12): it never fired in a recorded run and would have let a transition go
   uninterpreted.
3. `link_continues` (spec step 10, as simplified): for each record of `cur` that has a `before`, if record *j* of
   `prev.records` has `after.box` equal to that `before.box`, set `continues = f"{prev.id}/{j}"`; otherwise it stays
   null. At most one such *j* exists, because a later box is in at most one record. The previous record may be of any
   kind that has an `after`, `appeared` included, so a text that appeared and then grew, or appeared and was removed,
   is linked. An exact identity through a shared box; geometry is not consulted and nothing is asserted.
4. `find_reverts` (H8, spec step 9; Decision D14): `prev` is the change *z*→*a*, `prev_diff` its `PixelDiff`, `zb` the
   direct `PixelSource.diff(z, b)`. With any of the three `None`, return `[]`. For each component *k* of `prev_diff` in
   list order: it is undone when `zb.labels` is 0 at every pixel where `prev_diff.labels == k`. Each undone component
   yields `Revert(of=prev.id, rect=component.bbox, hold_s=round(b.t_change − a.t_change, 3))`. The test is per
   component, so a revert is still found when something else changes in the same transition. No time constant; both
   transitions stay and nothing is folded.
5. Lifetimes through `LifetimeBuilder`. Zero frames: both files are written empty. One frame: no changes, one lifetime
   per box.
6. Inputs `[run.frames, run.boxes]`; config hash `config_hash(cfg, "track", "decode")` (θpix and θmin live in
   `[decode.detect]`); manifest key `track` with stats `transitions`, `kinds`, `records` by kind, `moved`,
   `same_place`, `unchanged`, `variants`, `flicker_new`, `flicker_lost`, `reverts`, `lifetimes`, `unstable`, `margin`,
   `seconds` (wall time of the stage, rounded to 1 place).

**Tests to write first** (a helper writes `L`-mode PNGs from arrays plus `frames.jsonl` and `boxes.jsonl` by hand; frame
size 200×400; every box 18 px tall unless stated):
- `test_tooltip_reverts_with_hold_time` (H8): frames 0, 1, 2 with `t_change` 0.0, 1.0, 3.8. Images: black; black with
  `[100:120, 300:380] = 200`; black. Boxes: none; `b1 "Cloud Shell" (305,101,375,119)`; none → two changes. `T1.records`
  is one `appeared` record for `"1:b1"`, `T1.reverts == []`. `T2.records` is one `removed` record for `"1:b1"` with
  `continues == "T1/0"`; `T2.reverts == [Revert(of="T1", rect=(300,100,380,120), hold_s=2.8)]`.
- `test_revert_while_something_else_changes` (H8): the same, except frame 2 is black with `[20:40, 20:100] = 200` and has
  the box `b1 "Saved" (30,21,90,39)`. The 1→2 difference has two components, `(20,20,100,40)` and `(300,100,380,120)`,
  each of area 1,600. `T2.records`: an `appeared` record for `"2:b1"`, then a `removed` record for `"1:b1"`. Comparing
  frames 0 and 2 directly changes nothing at the tooltip's pixels → `T2.reverts == [Revert(of="T1",
  rect=(300,100,380,120), hold_s=2.8)]`.
- `test_partial_return_is_not_a_revert`: frame 2 keeps `[100:120, 300:340] = 200` → `T2.reverts == []`.
- `test_continues_links_consecutive_growth`: three frames with boxes `b1 "PS>" (10,50,130,68)`, `b1 "PS> git"
  (10,50,170,68)`, `b1 "PS> git status" (10,50,230,68)`; images black, then `[52:66, 140:168] = 255`, then additionally
  `[52:66, 176:228] = 255` → `T1.records[0].kind == "appended"` and `continues is None`; `T2.records[0].kind ==
  "appended"` and `continues == "T1/0"` (frame 1's box grown by 9 reaches x = 178, inside the second block);
  lifetimes: three, each with one sighting.
- `test_unsettled_kind`: a pair whose later frame has `settled = False` → `kind "unsettled"`; both settled → `"single"`.
- `test_size_mismatch_and_missing_png_degrade`: frame 1's PNG is 100×200, frame 2's PNG is deleted, the boxes are
  identical in all three frames → `T1.pixels is None`, `T2.pixels is None`, no records, `same_place` equals the box
  count, `reverts == []`, no exception.
- `test_zero_and_one_frame_runs`: empty `frames.jsonl` and `boxes.jsonl` → both output files exist and are empty,
  manifest `transitions == 0` and `lifetimes == 0`; one frame with boxes `b1 "a"`, `b2 "b"` → `changes.jsonl` empty,
  two lifetimes with one sighting each.
- `test_missing_boxes_record_is_an_error`: frames 0 and 1 in `frames.jsonl`, a boxes record for frame 0 only →
  `ValueError` whose message contains `scry read`.
- `test_skips_when_up_to_date_and_reruns_on_margin_change` (rewrite `cfg.track.margin` to 0.0 → the stage runs again).
- `tests/test_config.py::test_p0_margin_configs_differ_only_in_margin`: for `(000, 0.0)`, `(025, 0.25)`, `(100, 1.0)`,
  with paths anchored on `__file__`: `load_config(configs/p0-margin-<n>.toml).track.margin` equals the value, and its
  `model_dump()` with `["track"]["margin"]` set back to `0.5` equals `load_config(scry.toml).model_dump()`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_stage.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6, the config key, the three config files and the CLI command.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry --help` lists `decode`, `outline`, `read`, `track`, `run`,
  `setup`, `subset`.
- [ ] **Step 4:** Commit: `feat: track stage: changes.jsonl and lifetimes.jsonl; continues; reverts without a time constant (H8)`

### Task 13: Metrics over the records

**Files:**
- Create: `src/scry/metrics.py`, `tests/test_metrics.py`

**Interfaces:**
- Consumes: `Change`, `Lifetime`, `FrameBoxes`, `parse_box_ref`.
- Produces (pure functions, no I/O):
  - `select(boxes, changes, lifetimes, frames: tuple[int, int] | None) -> tuple[list[FrameBoxes], list[Change], list[Lifetime]]`
  - `box_stability(changes) -> float | None`
  - `touched_share_low_half(changes) -> float | None`
  - `totals(changes) -> dict`
  - `fragmentation(lifetimes, top: int = 20) -> dict`
  - `targets(change: Change) -> list[str]`
  - `incremental_projection(boxes, changes) -> dict`

**Rules (Decision D17 covers the definitions):**
1. `select` with `(lo, hi)`: boxes records with `lo ≤ frame ≤ hi`; changes with `lo ≤ from_frame` and `to_frame ≤ hi`;
   lifetimes with at least one sighting in the range (their `first` and `last` are not clipped). `None` selects all.
2. `box_stability = (Σ unchanged − Σ variants) / (Σ unchanged + Σ len(flicker_lost))`, rounded to 4; `None` when the
   denominator is 0. No overlap threshold is involved.
3. `touched_share_low_half`: the changes with `pixels` not null, sorted by `changed_fraction` ascending then id number;
   take the first `ceil(n / 2)`; the `statistics.median` of their `touched_share`, rounded to 4; `None` when there are
   none. A rank rule, so no threshold decides what "near-static" means.
4. `totals`: `{"transitions": {kind: n}, "records": {kind: n}, "moved", "same_place", "unchanged", "variants",
   "flicker_new", "flicker_lost", "reverts", "textless", "rect_only"}` summed over changes (`moved` counts pairs).
5. `fragmentation`: `{"lifetimes": N, "distinct_texts": D, "per_text": round(N / D, 3), "unstable": U,
   "single_sighting": S, "top": [(text, count), …]}`; `top` holds the texts with the most lifetimes, by count descending
   then text; `per_text` is `None` when `D == 0` (H7).
6. `targets(change)`: the boxes whose lifetime starts in the later frame, which are the boxes an incremental labelling
   call would have to label: the `after` box of every record of kind `appended`, `truncated`, `changed` or `appeared`,
   plus `flicker_new`. A `reread` continues its lifetime and is not a target (spec §5: labels come from the latest
   record of the box's lifetime).
7. `incremental_projection` (spec §2 as the owner amended it: a labelling call is made for the first frame and for
   every transition in which pixels changed, even if no box did, because the screen description must be refreshed):
   a change **makes a call** when `pixels` is null or `pixels.components ≥ 1`. Result: `{"frames": F, "boxes": total
   boxes, "calls": (1 if F ≥ 1 else 0) + changes that make a call, "calls_without_targets": changes that make a call and
   have no target, "target_boxes": boxes of the first selected frame + Σ len(targets) over the changes that make a
   call, "share_of_boxes": round(target_boxes / boxes, 4), "targets_per_call": round(target_boxes / calls, 2),
   "boxes_per_frame": round(boxes / F, 2)}`; the ratios are `None` when their denominator is 0. `decode` emits a
   frame only on change, so calls stay close to frames: what incremental labelling saves is boxes per call, not calls.

**Tests to write first:**
- `test_box_stability`: two changes with `unchanged` 98 and 50, `variants` 2 and 0, `flicker_lost` `["0:b9"]` and `[]` →
  `0.9799` (146 / 149). No changes → `None`.
- `test_touched_share_low_half`: four changes with `(changed_fraction, touched_share)` `(0.001, 0.02)`, `(0.2, 0.5)`,
  `(0.0005, 0.01)`, `(0.3, 0.9)` → `0.015`. A change with `pixels=None` is ignored.
- `test_fragmentation`: lifetimes with texts `"a"`, `"a"`, `"b"`, sightings 1, 3, 1, the second unstable → `lifetimes 3`,
  `distinct_texts 2`, `per_text 1.5`, `unstable 1`, `single_sighting 2`, `top [("a", 2), ("b", 1)]`.
- `test_targets`: a change with records `appended` (after `"1:b2"`), `reread` (after `"1:b4"`), `appeared` (after
  `"1:b7"`), `removed`, and `flicker_new == ["1:b9"]` → `["1:b2", "1:b7", "1:b9"]`.
- `test_incremental_projection`: boxes per frame 100, 101, 101, 113 (frames 0–3); three changes, each with
  `pixels.components == 1`, with 1 target (one `appended` record), 0 targets, and 12 targets (twelve `appeared`
  records). By hand: calls = 1 + 3 = 4; calls without targets = 1; target boxes = 100 + 1 + 0 + 12 = 113; boxes = 100 +
  101 + 101 + 113 = 415; 113 / 415 = 0.27229 → `0.2723`; 113 / 4 = `28.25`; 415 / 4 = `103.75`. With the second change's
  `components` set to 0: calls = 3, calls without targets = 0, target boxes 113, targets per call 113 / 3 = `37.67`.
- `test_select_by_frames`: changes `T1 (0→1)`, `T2 (1→2)`, `T3 (2→3)` and range `(1, 2)` → only `T2`; a lifetime with
  boxes `["0:b1", "1:b1"]` is kept, one with `["3:b2"]` is not.
- `test_totals_sums_kinds`: two changes, one `single` with records `appended`, `changed`, one `unsettled` with a
  `changed` record and two moved pairs → `transitions {"single": 1, "unsettled": 1}`, `records {"appended": 1,
  "changed": 2}`, `moved 2`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_metrics.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat: metrics over changes and lifetimes (box stability, fragmentation, incremental projection)`

### Task 14: Ground truth: the command list and the OCR reader's exactness

**Files:**
- Create: `src/scry/groundtruth.py`, `tests/test_groundtruth.py`

**Interfaces:**
- Produces: `@dataclass Entry`: `n: int | None`, `text: str`, `first_frame: int | None`, `first_t: float | None`,
  `submitted_frame: int | None`, `submitted_t: float | None`, `frames: list[int]`; `parse_commands(md: str) ->
  tuple[list[Entry], list[Entry]]` (executed, never run); `scorable(e: Entry) -> bool`; `score_exact(entries:
  list[Entry], lifetimes: list[Lifetime]) -> list[dict]`; `exact_rate(rows: list[dict]) -> tuple[int, int]`.

**Rules (the format is that of `docs/ground-truth/span2-commands.md`):**
1. Sections start at `## ` headings. The executed table is under the first heading whose lower-cased text starts with
   `executed`; the never-run table under the heading whose lower-cased text contains `never run`. Table rows are the
   lines starting with `|` after the header row and the `|---` row; cells are split on `|`. A row whose cell count
   differs from its header's raises `ValueError` with the line number. A missing section gives an empty list.
2. `text` is the first back-quoted span of the "Text as displayed" cell; a row without one raises `ValueError`.
3. A *pair* is the regex `(\d+),\s*(\d+\.\d+)`. `first_frame, first_t` = the first pair of the third executed column;
   `submitted_frame, submitted_t` = the last pair of the fourth. `n` is the first column as an integer. (For the two
   one-letter answers of the real list the first pair of column three is the *question's* frame; they are unrated
   by rule 5, so nothing depends on it.)
4. Never-run rows: `frames` = every match of `(\d+)\s*\(\d+\.\d+\)` in the second column.
5. `scorable`: the text has at least 4 non-space characters (a one-letter answer such as `y` is a substring of almost
   any lifetime, so it is reported and left out of rates).
6. **Exact** (spec §9 primary metric, OCR reader): a lifetime matches an entry when `norm(entry.text)` is a substring
   of `norm(lifetime.text)`, case-sensitively (`scry.textdiff.norm` collapses whitespace runs and nothing else that
   matters here). Per entry: `{"n", "text", "scorable", "exact", "matches", "lifetime", "first_frame", "frame_error",
   "t_error"}` where `lifetime` is the matching lifetime with the smallest `first.frame` (then smallest id number),
   `frame_error = lifetime.first.frame − entry.first_frame`, `t_error = round(lifetime.first.t − entry.first_t, 2)`;
   `None`s when nothing matches or the entry has no first frame. `exact_rate` counts scorable executed rows only.
7. Never-run entries go through the same matching and are reported as information — matching lifetime ids, first and
   last frame, sightings — and enter no rate (owner: run against not-run is secondary; spec §9).

**Tests to write first** (the Markdown fixture is a string inside the test, never the repository file):

```
## Executed, in order

| # | Text as displayed | First fully visible (frame, t) | Submitted (frame, t) | Confidence note |
|---|---|---|---|---|
| 1 | `az configure --defaults group=RG1` | 161, 649.17 (10:49.2) as typed `az c`; fully typed from 162, 652.00 | 164, 653.57 (10:53.6), new prompt | High |
| 2 | `y` (answer to `Overwrite? (y/n):`) | question visible 170, 660.83; answer visible 171, 664.13 | 171, 664.13 (11:04.1) | High |
| 3 | `kubectl get pods` | 187, 721.00 (12:01.0) | between 186, 716.90 (11:56.9) and 187, 721.00 (12:01.0) | High |

## Appeared on screen but was never run

| Text as displayed | Frames (t) | What the presenter had actually entered | What happened next |
|---|---|---|---|
| `kubectl rollout undo deployment/kodekloudapp` | 172 (668.13), 173 (668.87) | `kubect` | replaced |
```

- `test_parse_commands`: executed texts as above; entry 1 `first (161, 649.17)`, `submitted (164, 653.57)`; entry 2
  `first (170, 660.83)`, `submitted (171, 664.13)`, not scorable; entry 3 `first (187, 721.0)`, `submitted (187,
  721.0)`; never-run entry `frames [172, 173]`.
- `test_score_exact`: lifetimes `L3 "PS C:\Users\msadmin>azconfigure --defaultsgroup=RG1"` first `(161, 649.17)`;
  `L4 "PS C:\Users\msadmin> az configure --defaults group=RG1"` first `(162, 652.0)`; `L7 "PS C:\Users\msadmin>
  kubectl get pods"` first `(187, 721.0)`; `L9 "PSC:\Users\msadmin> kubect1rollout undo deployment/kodekloudapp"` first
  `(172, 668.13)` → entry 1: `exact True`, `lifetime "L4"`, `frame_error 1`, `t_error 2.83`, `matches 1`; entry 3:
  `exact True`, `"L7"`, `frame_error 0`, `t_error 0.0`; entry 2: `scorable False`; `exact_rate == (2, 2)`. The never-run
  entry: `matches 0`.
- `test_exact_is_case_sensitive`: entry `az aks get-Credentials` against a lifetime reading `… az aks get-credentials …`
  → `exact False`.
- `test_malformed_row_raises`: the fixture with the last cell of executed row 1 removed (that row is line 5 of the
  fixture string) → `ValueError` whose message contains `line 5`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_groundtruth.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat: command ground truth parser and the exact-reading metric (spec §9)`

### Task 15: `scry report`

**Files:**
- Create: `src/scry/report.py`, `tests/test_report.py`
- Modify: `src/scry/cli.py`

**Interfaces:**
- Produces: `build_report(run: Run, cfg: Config, frames: tuple[int, int] | None = None, ground_truth: Path | None =
  None) -> str`; `write_sheets(run: Run, cfg: Config, out_dir: Path, frames: tuple[int, int] | None, per_kind: int, seed:
  int) -> list[Path]`; CLI `scry report RUN_DIR [--frames A-B] [--ground-truth PATH] [--out report.md]
  [--sheets/--no-sheets] [--per-kind 30] [--seed 0] [--config PATH]`. It is not a stage: no manifest entry, always
  regenerated, written inside the run directory. Sheets go to a directory named after the report, `<out stem>-sheets/`
  (`report-span2.md` → `report-span2-sheets/`), emptied first, so three reports never mix their samples.

**Rules:**
1. Markdown with these headings, in this order: `# track report`; `## Run` (frames, boxes, transitions; the `read`
   engine settings, `track.margin`, and the wall time of `read` per frame and of `track` per pair, all taken from the
   run's manifest and not from `--config`; θpix, θmin; the frame range; the line `model calls: none, $0.00`);
   `## Transitions` (one table row per change: id, frames, kind, changed %, components, textless, touched share,
   rect-only, records by kind, moved, same place, unchanged, variants, flicker new and lost, reverts); `## Totals`;
   `## Guards` (`box_stability`, `touched_share_low_half`, total `rect_only`); `## Lifetimes` (`fragmentation`);
   `## Incremental annotation projection`; `## Text changes` (every record of kind `appended`, `truncated` or `changed`:
   change id, record index, kind, before → after in back-quotes, `continues`; at most 20 lines per change, then "… and
   N more"); `## Moves` (for every change with moved pairs: the count and up to 10 pairs as text, earlier rectangle →
   later rectangle, joined from `boxes.jsonl`); `## Unstable lifetimes` (up to 50, by sightings descending: id, majority
   text, each reading with its count and its frames, first and last frame); `## Reverts` (every one: change id, `of`,
   rectangle, hold time); and, with a ground truth, `## Commands` (the rows of `score_exact` and `exact_rate`, then the
   never-run table marked "information only", then the sentence that the OCR reader's rate is a lower bound: a
   command that OCR splits over two boxes cannot be exact until `run` links exist).
2. `write_sheets` makes the evidence the executor reads against the frames (spec §4: hypotheses are judged by reading
   records against frames). With `random.Random(seed)`, sample up to `per_kind` of each: records per kind, reverts,
   unstable lifetimes, and `flicker` boxes. One PNG each: the crop of the earlier frame above the crop of the later
   frame (for a revert: frames *z*, *a*, *b*), the crop being the record's rectangle grown on every side by its own height and clipped
   (scale-free, and independent of the margin under test). An unstable lifetime's sheet has one
   row per distinct reading, majority first: the crop of the box at the first frame where that reading was sighted,
   captioned with the frame number and the reading, so the reader sees the frame where the variant occurred. Names
   `T12-r0-appended.png`, `T12-r3-appeared.png`, `T12-r5-removed.png`, `T12-revert0.png`, `T12-flicker-new-b9.png`,
   `L388.png`. A missing PNG skips that sheet.
3. The report states no pass or fail and compares with no threshold.

**Tests to write first** (the run directory is Task 12's three-frame typing fixture, produced by `run_track`):
- `test_report_has_sections_and_numbers`: the text contains each heading of rule 1 up to `## Reverts`, table rows
  starting `| T1 |` and `| T2 |`, the word `appended`, the string `` `PS> git` → `PS> git status` `` and the line `model
  calls: none, $0.00`.
- `test_report_frames_filter`: `frames=(1, 2)` → the transitions table has a row starting `| T2 |` and none starting
  `| T1 |` (the string `T1` still occurs, in T2's `continues`).
- `test_report_with_ground_truth`: a ground-truth file with one executed row `` `git status` `` first visible at frame
  2 → the `## Commands` section shows `exact` true, `frame_error 0`, and `1 / 1`.
- `test_report_renders_on_empty_run`: a run with zero frames → the headings render and the tables are empty.
- `test_sheets_written`: `write_sheets(..., per_kind=5, seed=0)` returns paths that exist, open with Pillow and include
  `T1-r0-appended.png` and `T2-r0-appended.png`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_report.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–3 and the command.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat: scry report: track metrics, command exactness and evidence sheets`

### Task 16: P0 — the first real run (free)

No code. `runs/` is git-ignored; `runs/aks` is read and never written. No model is called: the cost of P0 is $0.

- [ ] **Step 1: Bring the 221 decoded frames over.**
  `uv run scry subset runs/aks --out runs/p0 --frames 0-220 --no-share-cache`
  Expected: `runs/p0: 221 frames; …`; `runs/p0/frames.jsonl` has 221 lines. Safety check, repeated after every later
  step: `find runs/aks -newer runs/p0/manifest.json` prints nothing (`runs/` is git-ignored, so `git status` says
  nothing about it).
- [ ] **Step 2: Read.** `uv run scry read runs/p0` (about five minutes). Expected: `boxes.jsonl` with 221 records;
  note `boxes`, `dropped_empty` and `seconds` from `manifest.json`.
- [ ] **Step 3: Track.** `uv run scry track runs/p0`. Expected: `changes.jsonl` with 220 records and `lifetimes.jsonl`;
  note `seconds`.
- [ ] **Step 4: Reports.**
  `uv run scry report runs/p0 --ground-truth docs/ground-truth/span2-commands.md --out report.md`
  `uv run scry report runs/p0 --frames 145-155 --out report-smoke.md`
  `uv run scry report runs/p0 --frames 155-187 --ground-truth docs/ground-truth/span2-commands.md --out report-span2.md`
- [ ] **Step 5: Margin sensitivity** (spec §9 P0: margin 0, 0.25, 0.5, 1.0; 0.5 is `runs/p0`). The three configs are
  committed files (Task 12), not edited copies. For each `N` in `000`, `025`, `100`:
  `mkdir runs/p0-m$N && ln -s ../p0/frames runs/p0-m$N/frames && cp runs/p0/manifest.json runs/p0/frames.jsonl runs/p0/boxes.jsonl runs/p0-m$N/`
  `uv run scry track runs/p0-m$N --config configs/p0-margin-$N.toml`
  `wc -l runs/p0-m$N/changes.jsonl` — expected 220; if the file is missing, `track` skipped itself: stop and find out why.
  `uv run scry report runs/p0-m$N --config configs/p0-margin-$N.toml --frames 155-187 --ground-truth docs/ground-truth/span2-commands.md --no-sheets`
  Check that each report's `## Run` shows the intended margin (it is read from the manifest).
- [ ] **Step 6: Read the records against the frames.** No pass threshold is set for any of this (owner's ruling); the
  job is to say what was seen. Use the sheets under `runs/p0/report*-sheets/`, the reports and the frames themselves.
  - **H1** — every sheet of an unstable lifetime (up to 30; each shows the frame where the variant reading occurred)
    and every flicker sheet (up to 30): is any a real change of text on screen that the veto hid? Also the five
    transitions with the largest `changed_fraction`: did any box that visibly changed stay in `unchanged`?
  - **H2** — every `appended` and `truncated` record of span 2 (the report lists them), and 20 sampled `changed` records:
    is the before box the after box's earlier self, or did a sliver overlap marry two unrelated boxes? Any growing text
    reported as `appeared` + `removed` instead?
  - **Re-splits, the known cost of having no groups** (spec §12) — how often does OCR split or merge a text under
    changed pixels, so that one text shows as a `changed` or `truncated` record beside an `appeared` or `removed` box
    on the same visual line? Count them over both spans and give ids. This count is the evidence that would justify
    grouping later, or show it is not needed.
  - **Entered and submitted between two frames** — a command that was entered and submitted between two emitted frames
    shows as `appeared` text beside a moved prompt, never as `appended` (the earlier bare prompt cancels as a move with
    the new bare prompt). Expected and honest. Note how often it happens in span 2 (the ground truth marks two
    commands never seen while being entered) and give ids.
  - **H3** — from `## Moves`: every transition with ten or more moved pairs, up to ten of them, five pairs each: did the
    text really move (the rectangles differ and the frames show it)? Any duplicate string cross-paired?
  - **H4** — every `reread` record, up to 30: whitespace noise only?
  - **H5** — the five largest and five smallest non-empty changes: is the one record shape readable at both ends?
  - **H6** — `rect_only` totals per transition, and ten boxes behind the largest counts: would a rectangle test have
    called them changed wrongly?
  - **H7** — `fragmentation`: the twenty texts with the most lifetimes; for ten, why did the lifetime split?
  - **H8** — every `reverts` entry; and whether the two tooltips of the smoke span (frames 149 and 151) were found.
  - **Commands** — the `## Commands` table of span 2 at each margin.
- [ ] **Step 7: Ledger row and hand-back.** Append one row to `docs/decision-ledger.md` (next free number): what ran
  (commit hash, frames, boxes, transitions, lifetimes); cost ($0, no model calls) and wall time per frame for `read`
  and per pair for `track`; totals by kind; `box_stability`, `touched_share_low_half`, `rect_only`; fragmentation; the
  incremental-annotation projection (calls, calls without targets, target boxes and targets per call against 221
  frames and all boxes) for the whole video and both spans; `exact_rate` and the frame and time errors on span 2 at the
  four margins; the re-split count; one line per hypothesis saying what was seen, with the transition or lifetime ids
  that show it; every case from the spec's watch list that actually occurred, with ids. Commit:
  `docs: ledger row for P0 (read and track over the full sample)`. Hand back the row, the three reports, and a list of
  any rule in this plan that the real data showed to be wrong or undefined — as findings, not fixes.

---

## Decisions this plan makes

The spec is silent or looser on each of these. The list was reviewed by two read-only reviewers and reconciled by the
coordinator under the owner's mandate (ledger L44); what each review finding became is in ledger L45.

- **D1. One reader, a core dependency.** The Apple Vision adapter and PyObjC go in the branch's first commits (spec §8
  and §10 step 0; owner's ruling), and `rapidocr` + `onnxruntime` move from an extra into `dependencies`, because `read`
  has one engine.
- **D2. `agent.py` and `prompts/` are deleted whole.** The spec removes "the tools of `agent.py`" and "the four prompt
  modules"; the loop cannot import without its prompt. They return from the tag with `ask` (Task 1's "Returns with"
  table).
- **D3. Kept modules whose stage is not rebuilt here are reduced to what imports cleanly:** `index.py` keeps storage,
  search and fusion; `overlay.py` keeps its drawing functions (now over `Box`) and loses `run_overlay`; no CLI command
  for either. `outline` stays as it is. `run` is reduced to `outline → decode → read → track`. A `report` command is
  added. So the CLI is `decode, outline, read, track, report, subset, setup, run`. Everything reduced here is listed
  with its return point in Task 1's table.
- **D4. Names.** `stage1.py` → `decode.py`, the PyAV helpers → `video.py`, `stage2a.py` → `read.py`; `Stage1Record` →
  `Frame`; TOML `[stage1.*]` → `[decode.*]`, `[ocr]` → `[read]`, new `[track]`; manifest keys `decode`, `read`,
  `track`. The `effort_stage*` keys, `Stage5Config` and `HierarchyConfig` are removed until their stages return under
  new names. Config models reject unknown keys, so a stale section fails instead of being ignored.
- **D5. `read` drops two things the spec's `Box` does not carry:** boxes whose text is empty after stripping (counted),
  and the `confusable` flag (the owner confirmed the drop on 2026-09-21).
- **D6. Legacy import goes through `subset`**, which prefers a source's `stage1.jsonl` and maps the manifest key.
  The copied `decode` entry keeps the source's config hash, so `scry run` on an imported directory may decide to decode
  again; P0 therefore uses the stage commands. A source without a `cache/` directory gets no cache link.
- **D7. "Reading order" is `read`'s id order** — boxes sorted by top edge then left edge — everywhere. There is no
  row-banding rule and no half-height overlap rule. With one record per box, reading order no longer decides any
  recorded text; it only breaks ties and pairs duplicate moved strings.
- **D8. A changed box's other self may be an untouched box, in either direction.** The pairing candidates are
  intersecting boxes of which at least one is touched. Without this, a growing text whose old extent lies outside the
  changed pixels would be reported as `appeared` beside an unrelated silent ending, contradicting H2; a shrinking text
  is the mirror case. This replaces the pools of the first draft (spec §12: simplify before repairing).
- **D9. Flicker.** An untouched box left without a partner yields no change record (H1: nothing changed there); its
  lifetime starts or ends silently and it is counted in `flicker_new` / `flicker_lost`, which P0 reads for H1 and H7.
- **D10. One-to-one matching is greedy by intersection area, ties by reading order,** for unchanged pairs, same-place
  pairs and changed pairs alike. "Overlaps most" in the spec does not say what happens when two boxes claim one.
  There is no floor on the overlap; P0's H2 reading looks for sliver marriages.
- **D11. Text equality in steps 4 and 5 is exact string equality.** Whitespace-blind comparison is confined to kind
  labels (H4). The owner's brief for this plan lists a `visual_only` kind; revision 3 expresses that case as the
  `same_place` count (something visual changed over unchanged text) and this plan follows revision 3.
- **D12. No groups.** A change record is one pair of boxes, or one appeared or one removed box (spec §12; where the
  spec's §5 sketch and §6 steps 6–7 and 10 still say "groups", §12 governs). Only a `reread` continues a lifetime;
  every other kind ends one and starts another. The known cost: when OCR re-splits a text under changed pixels, it
  shows as one record plus an `appeared` or `removed` box. P0 counts how often that happens.
- **D13. Record shape beyond the spec's sketches.** `Change.records` (one list of `BoxChange`, kinds `reread`,
  `appended`, `truncated`, `changed`, `appeared`, `removed`) replaces the sketch's `groups`, `appeared` and `removed`
  lists, so that `continues` can name any record; `moved` is a list of box-ref pairs, not a count (P0 reads H3 from
  it); `Lifetime.readings` maps each reading to the frames at which it was sighted, not to a count (P0 opens the frame
  where a variant occurred); added measured fields `pixels.textless_area`, `pixels.rect_only`, `unchanged`, `variants`,
  `flicker_new`, `flicker_lost`, `BoxChange.in_churn`, `FrameBoxes.seconds`; `FrameBoxes.engine` is the adapter's whole
  `settings()` dict (engine, version, runtime, model file names, `rec_lang`, `word_boxes`, `use_cls`, `rec_batch_num`,
  `gap_ratio`, and the running `space_guard_fired` count), not the sketch's two keys. Plans 2–4 are reconciled against
  these shapes.
- **D14. Reverts are tested per component of the previous transition, on that component's own pixels** (not its
  rectangle, for the reason behind H6), so a revert is found even when something else changes in the same transition;
  `hold_s = t_change(b) − t_change(a)`. `continues` is written `"T8/0"`: the previous change's id and the index of the
  record in its `records` whose `after` box is this record's `before` box, whatever that record's kind.
- **D15. Lifetime details:** `first.t` is the first frame's `t_settled`, `last.t` the last frame's `t_end`; a tie for
  the majority goes to the reading sighted first; ids in creation order.
- **D16. Margin arithmetic:** `floor(margin × median + 0.5)` pixels, the median over both frames' boxes, grown
  rectangles clipped to the frame; zero boxes → 0.
- **D17. Metric definitions:** `box_stability` without any overlap threshold; `touched_share` summarised over the
  lower half of transitions by `changed_fraction` (a rank, not a cut-off); the incremental projection counts a call for
  the first frame and for every transition with a changed component or without pixel data, and reports target boxes
  per call as the saving; exactness as a case-sensitive substring after whitespace collapsing; entries under 4
  non-space characters (the answers `Y` and `y`) reported and kept out of rates, because a one-letter text is a
  substring of almost any lifetime (an evaluation-side cut fitted to this list, stated as such); never-run entries
  reported and never rated.
- **D18. One whole-video run; spans are report filters** (`--frames`); margin sensitivity uses light run directories
  that share the frames by symlink and three committed config files, never a config edited by pattern. Evidence sheets
  are part of `scry report`, as real code with tests, in a directory named after the report.
- **D19. `decode`'s record keeps its `caret` field** ("unchanged in content", spec §5) though nothing reads it.
- **D20. `track` always works at full resolution** and ignores `[decode.detect] downsample`.
- **D21. No `found` metric yet.** The spec's *found* needs the index; this plan reports *exact*, first-sighting frame
  and time error for the OCR reader only.
- **D22. Only touched boxes can be moves.** The spec's step 5 says "anywhere in the transition"; an untouched box
  cannot have moved (H1), so it never takes part in move cancellation.
- **D23. Transition kinds are `single` and `unsettled` only.** The clock rule and `trivial` are dropped (owner's
  ruling, spec §12).

## Self-review

- **Spec coverage.** §5 records → Task 4. §6 `read` → Task 6. §6 `track` steps 1–2 → Task 7; 3 → Task 8; 4–5 →
  Task 9; 6–8 as simplified by §12 → Task 10; 9–10 → Task 12; lifetimes → Task 11. §8 removals → Tasks 1–3. §9 P0
  (H1–H8, margins, fragmentation, incremental projection, the OCR reader's command metrics) → Tasks 13–16. §10 steps
  0–2 → the whole plan. Not covered by design: `annotate`, `interpret`, `summarize`, `index`, `ask` (later plans; Task
  1's table lists what they must bring back), the *found* metric (D21), README and CONTRIBUTING updates (they follow the
  design's revision 7 at the end of the re-base).
- **Placeholders.** None: every test names its fixture and its expected values; no step says "handle edge cases".
- **Type consistency.** `Box`, `FrameBoxes`, `Change`, `BoxChange`, `Revert`, `Lifetime`, `FrameTime`, `PixelStats`,
  `BoxText` (Task 4) are the names used in Tasks 6–15; `PixelDiff`, `touched`, `touched_by`, `touched_by_rect`,
  `margin_px`, `grow` (Task 7) in 8, 10, 12, 15; `intersection`, `match_one_to_one`, `touched_flags`,
  `match_unchanged` (Task 8) in 9–10; `Pairing`, `PairResult`, `track_pair` (Task 10) in 11–12;
  `LifetimeBuilder.step(b, b_boxes, result)` (Task 11) in 12; `targets` (Task 13) in 15.
- **Review focus.** Each of the five lines names its test and task.
- **Hand checks after reconciliation.** Every fixture whose rules changed was recomputed by hand: fixture K under the
  new pairing (touched flags, the 2,160 intersection, `touched_share` 1 / 5); the truncation mirror; the overlapping
  lines (areas 5,800, 1,200, 570, 180; `m = 10`; `touched_share` 3 / 4); the re-split (720 against 2,520); the scroll
  (two moved pairs, one appeared, one removed); the revert beside another change (two components of 1,600 pixels, hold
  2.8 s, `continues "T1/0"`); the projection (4 calls, 113 targets, 0.2723, 28.25, 103.75; and 3 calls, 37.67).
