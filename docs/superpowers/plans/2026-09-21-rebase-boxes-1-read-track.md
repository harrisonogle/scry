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
§9 P0, §10 steps 0–2, §11). Executors read it with this plan. Where this plan is more specific than the spec, the
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
2. **OCR boxes that overlap inside one frame** (a box nested in another). Expect a deterministic one-to-one result, no
   box in two groups, no lifetime claimed twice (Task 8 `test_one_to_one_when_two_later_boxes_claim_one_earlier_box`,
   Task 10 `test_nested_boxes_form_one_group`).
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
  schemas.py        BBox, Frame, RawWord, Box, FrameBoxes, PixelStats, BoxText, Group, Revert, Change, FrameTime,
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
  textdiff.py       norm, similarity, levenshtein, lcp_len, myers, char_diff, is_clock_change
  index.py          Node, open_db, index_nodes, search and fusion only (node extraction returns with `index`)
  overlay.py        drawing functions only (the stage wrapper returns with `annotate`)
  outline.py providers/ env.py jsonl.py     unchanged
tests/              one file per module above; files for deleted modules are deleted
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
  `char_diff`, `is_clock_change`.

**Rules:**
1. Delete the files listed (spec §8 "Removed"). `diff.py` goes whole: its `PixelSource` is rewritten in Task 7 from the
   rules there, not moved.
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
8. `textdiff.py`: remove `line_ops`, `pair_modifies` and the `DiffOp` import.

**Tests to write first:**
- `tests/test_package.py::test_old_machinery_is_gone`: for each name in `merge, correspond, coalesce, diff, perceive,
  interpret, hierarchy, agent, diagnostics, stage2a, prompts`, `importlib.util.find_spec("scry." + name)` is `None`;
  `scry.schemas` has none of the attributes `Line, Region, FrameRecord, Transition, DiffOp, VlmRegion, VlmPerception,
  PerceptionRecord, Interpretation, HierNode`.
- `tests/test_package.py::test_every_module_imports`: walking `pkgutil.walk_packages(scry.__path__, "scry.")` and
  importing each module raises nothing.
- `tests/test_costs.py::test_estimate_cost`: `estimate_cost({"input_tokens": 1_000_000, "output_tokens": 100_000,
  "cache_read_input_tokens": 0}, "claude-opus-5") == 7.5` (moved from `test_diagnostics.py`).
- In `tests/test_textdiff.py` delete `test_line_ops_scroll_is_equal_plus_inserts`, `test_pair_modifies_by_y_overlap`,
  `test_pair_modifies_keeps_unrelated_lines_apart` and the `DiffOp`, `line_ops`, `pair_modifies` imports. In
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
   `minimum_text_height`) and their `scry.toml` keys.
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
- Modify: `src/scry/schemas.py`, `config.py`, `run.py`, `cli.py`, `settle.py`, `subset.py`, `scry.toml`,
  `tests/test_settle.py`, `tests/test_subset.py`, `tests/test_package.py`
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
- `tests/test_config.py::test_repo_toml_loads`: `load_config(Path("scry.toml"))` succeeds and
  `cfg.read.engine == "rapid"`.
- `tests/test_package.py::test_old_machinery_is_gone` additionally asserts `find_spec("scry.stage1") is None` and that
  `scry.schemas` has no `Stage1Record`.
- `tests/test_subset.py` and `tests/test_settle.py`: update imports (`Frame`, `DecodeConfig`) and file names
  (`frames.jsonl`, manifest key `decode`); expectations otherwise unchanged.

- [ ] **Step 1:** Write `tests/test_config.py`, update the other tests. Run `uv run pytest tests/test_config.py -q`.
  Expected: FAIL (`Config` has no `decode`).
- [ ] **Step 2:** `git mv` the three files, then apply the renames and rules 1–4.
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
Group        kind: Literal["reread", "appended", "truncated", "changed"] · rect: BBox · before: list[BoxText] ·
             after: list[BoxText] · char_diff: list[list[str]] · continues: str | None = None ·
             in_churn: bool = False · clock: bool = False
Revert       of: str (a change id) · rect: BBox · hold_s: float
Change       id: str ("T<n>", n from 1) · from_frame: int · to_frame: int · t: tuple[float, float] ·
             kind: Literal["single", "unsettled", "trivial"] · pixels: PixelStats | None ·
             groups: list[Group] = [] · appeared: list[str] = [] · removed: list[str] = [] (box refs) ·
             moved: int = 0 · same_place: int = 0 · unchanged: int = 0 · variants: int = 0 ·
             flicker_new: list[str] = [] · flicker_lost: list[str] = [] · reverts: list[Revert] = []
FrameTime    frame: int · t: float
Lifetime     id: str ("L<n>", n from 1) · text: str · readings: dict[str, int] · unstable: bool · sightings: int ·
             first: FrameTime · last: FrameTime · moved: bool = False · boxes: list[str] (box refs, frame order)
```

`Run` gains paths `boxes` (`boxes.jsonl`), `changes` (`changes.jsonl`), `lifetimes` (`lifetimes.jsonl`) and loaders
`load_boxes() -> list[FrameBoxes]`, `load_changes() -> list[Change]`, `load_lifetimes() -> list[Lifetime]`; each returns
`[]` when the file is absent. Helper `scry.schemas.box_ref(frame: int, box_id: str) -> str` and
`parse_box_ref(ref: str) -> tuple[int, str]`.

**Rules:**
1. Field names and shapes are those of spec §5. The fields `textless_area`, `rect_only`, `unchanged`, `variants`,
   `flicker_new`, `flicker_lost`, `Group.in_churn` and `Group.clock` are additions (Decision D13).
2. `OcrLine` is deleted; `overlay.py`'s functions take `list[Box]` and draw the label `box.id[1:]` exactly as they drew
   `line.id[1:]`. `tests/test_overlay.py` builds `Box` objects; its expectations do not change.
3. All models `extra="ignore"` (pydantic's default) so a later stage may add fields without breaking old files.

**Tests to write first (`tests/test_schemas.py`):**
- `test_records_round_trip_unicode`: a `FrameBoxes` with boxes `b1 "区" (24,164,48,179)` and
  `b2 "PS C:\\Users\\msadmin> az login" (659,352,904,371)` with one word; a `Change` with one `Group` of kind `appended`,
  one `Revert`, `pixels=None`; a `Lifetime` whose `readings` has two keys. Write each with `write_jsonl`, read back with
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
4. The CLI passes the path. `--share-cache` keeps its meaning and default.

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
- `test_cli_read`: `typer.testing.CliRunner` cannot inject an engine, so monkeypatch `scry.read.get_engine` to return the
  fake; `scry read <dir>` exits 0 and writes `boxes.jsonl`.

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
  `components(changed, theta_min)` becomes `label_components(changed, theta_min)[1]` with unchanged results.
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
   level of `decode`'s gray (ledger L32). `None` when `frame.png` is empty or the file is missing. The last `keep`
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
> labelled pixel count / 80,000. Every box is 18 px tall, so `margin 0.5` gives `m = 9`.
> **Fixture K (a keystroke):** frame 0 boxes `b1 "Title" (10,10,110,28)`, `b2 "PS>" (10,50,130,68)`,
> `b3 "区" (300,150,330,168)`; frame 1 boxes `b1 "Title" (10,10,110,28)`, `b2 "PS> git status" (10,50,230,68)`;
> one component `block(labels, 1, 52, 66, 140, 228)` (area 1,232, `changed_fraction 0.0154`).

### Task 8: `track` steps 2–3: untouched boxes, and the pools that carry on

**Files:**
- Create: `src/scry/track/changes.py`, `tests/test_track_pools.py`

**Interfaces:**
- Consumes: `Box`, `PixelDiff`, `touched`.
- Produces:
  - `intersection(a: BBox, b: BBox) -> int` (area, 0 when none)
  - `match_one_to_one(cands: list[tuple[int, int, int]]) -> list[tuple[int, int]]` — candidates are
    `(area, index_in_a, index_in_b)`; returns index pairs
  - `@dataclass Pools`: `unchanged: list[tuple[Box, Box]]`, `before: list[Box]`, `after: list[Box]`,
    `flicker_lost: list[Box]`, `flicker_new: list[Box]`, `touched_a: set[str]`, `touched_b: set[str]`
  - `build_pools(a_boxes: list[Box], b_boxes: list[Box], diff: PixelDiff | None, m: int) -> Pools`

**Rules:**
1. **Touched** (spec step 2): with `diff is None` every box of both frames is touched; otherwise `touched(box.bbox, diff, m)`.
2. **One-to-one matching** (used here and in Task 9): sort candidates by area descending, then `index_in_a`, then
   `index_in_b` ascending; walk the list taking a pair when neither side is taken. Indices are positions in reading order.
3. **Untouched boxes are unchanged** (H1, spec step 3): candidates are every untouched box of *a* with every untouched
   box of *b* it intersects. The matched pairs are `unchanged`; their texts may differ (a variant reading, never a
   change).
4. **Pools** (Decision D8): `after` = the touched boxes of *b* plus every untouched, unmatched box of *b* that
   intersects a touched box of *a*; `before` symmetrically. A growing text's shorter self usually lies wholly outside
   the changed pixels, and H2 requires it to be found.
5. **Flicker** (Decision D9): an untouched, unmatched box that intersects no touched box of the other frame is
   `flicker_lost` (from *a*) or `flicker_new` (from *b*): OCR found a box in one frame and not the other over pixels
   that did not change. It yields no change record.
6. All lists are in reading order.

**Tests to write first:**
- `test_keystroke_pools`: fixture K, `m = 9` → `unchanged == [(a.b1, b.b1)]`; `before` ids `["b2"]`; `after` ids
  `["b2"]`; `flicker_lost` ids `["b3"]`; `flicker_new == []`; `touched_a == set()`; `touched_b == {"b2"}`. (`a.b2`
  grown is `(1,41,139,77)`; the component starts at x = 140.)
- `test_truncation_pulls_in_the_untouched_later_box`: *a* `b1 "PS> git status" (10,50,230,68)`; *b* `b1 "PS>"
  (10,50,130,68)`; the component of fixture K → `before` ids `["b1"]`, `after` ids `["b1"]`, `unchanged == []`, no flicker.
- `test_one_to_one_when_two_later_boxes_claim_one_earlier_box`: no changed pixels (`labels` zeros, no components); *a*
  `b1 "Authentication and Authorization Local accounts" (10,100,390,118)`; *b* `b1 "Authentication and Authorization"
  (10,100,200,118)`, `b2 "Local accounts" (220,100,390,118)`. Areas 3,420 and 3,060 → `unchanged == [(a.b1, b.b1)]`,
  `flicker_new` ids `["b2"]`, pools empty.
- `test_no_pixels_means_everything_is_touched`: `diff=None`; *a* `b1 "x" (0,0,10,10)`, *b* `b1 "x" (0,0,10,10)` →
  `unchanged == []`, `before` ids `["b1"]`, `after` ids `["b1"]`.
- `test_match_one_to_one_tie_breaks`: candidates `[(50,0,1), (50,0,0), (40,1,0)]` → `[(0,0)]` first by index order, then
  `(1,0)` is refused because b 0 is taken → result `[(0,0)]`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_pools.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(track): untouched boxes are unchanged at any changed fraction (H1); pools; flicker`

### Task 9: `track` steps 4–5: same place, and moves

**Files:**
- Modify: `src/scry/track/changes.py`
- Create: `tests/test_track_moves.py`

**Interfaces:**
- Produces: `same_place(before: list[Box], after: list[Box]) -> tuple[list[tuple[Box, Box]], list[Box], list[Box]]` and
  `cancel_moves(before, after) -> tuple[list[tuple[Box, Box]], list[Box], list[Box]]`; each returns its pairs and the
  two remaining pools in reading order.

**Rules:**
1. **Text equality here is exact string equality** (Decision D11). Whitespace-blind comparison is for kind labels only (H4).
2. **Same place, same text** (spec step 4): candidates are pairs that intersect and have equal text; matched one to one
   by Task 8's rule 2.
3. **Moves** (H3, spec step 5): for every text present in both remaining pools, the k-th occurrence in `before` is
   paired with the k-th occurrence in `after` (reading order), up to the smaller count, anywhere in the frame.

**Tests to write first:**
- `test_highlight_over_unchanged_text_is_same_place`: `before [b1 "Overview" (10,130,100,148)]`, `after` the same →
  one pair, both pools empty.
- `test_scroll_cancels_as_moves`: `before b1 "alpha" (10,20,100,38)`, `b2 "beta" (10,40,100,58)`, `b3 "gamma"
  (10,60,100,78)`; `after b1 "beta" (10,20,100,38)`, `b2 "gamma" (10,40,100,58)`, `b3 "delta" (10,60,100,78)` →
  `same_place` finds nothing (equal texts never intersect); `cancel_moves` pairs `(a.b2, b.b1)` and `(a.b3, b.b2)`;
  remaining `before` ids `["b1"]`, `after` ids `["b3"]`.
- `test_duplicates_pair_same_place_first_then_reading_order`: `before b1 "1.24.10" (10,10,60,28)`, `b2 "1.24.10"
  (10,100,60,118)`; `after b1 "1.24.10" (10,100,60,118)`, `b2 "1.24.10" (200,10,250,28)` → `same_place` pairs
  `(a.b2, b.b1)`; then `cancel_moves` pairs `(a.b1, b.b2)`; both pools empty.
- `test_whitespace_difference_is_not_equal_here`: `"Open in mobile Give feedback"` and `"Open in mobileGive feedback"`
  at the same rectangle → no pair from either function; both remain.
- `test_unequal_counts_leave_the_surplus`: `before` two `"x"` boxes `b1`, `b2` far from `after`'s single `"x"` →
  pair `(a.b1, b.b1)`; `before` keeps `b2`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_moves.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–3.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(track): same-place pairs and whole-transition move cancellation (H3)`

### Task 10: `track` steps 6–8: groups, kinds, appeared, removed, pixel statistics

**Files:**
- Modify: `src/scry/track/changes.py`
- Create: `tests/test_track_pair.py`

**Interfaces:**
- Produces:
  - `kind_of(before: str, after: str) -> Literal["reread", "appended", "truncated", "changed"]`
  - `group_boxes(before: list[Box], after: list[Box]) -> tuple[list[tuple[list[Box], list[Box]]], list[Box], list[Box]]`
    (groups, removed, appeared)
  - `@dataclass Pairing`: `a: str`, `b: str` (box ids), `how: Literal["unchanged", "same_place", "moved", "reread"]`
  - `@dataclass PairResult`: `change: Change`, `pairings: list[Pairing]`, `starts: list[str]` (box ids of *b*),
    `ends: list[str]` (box ids of *a*)
  - `track_pair(a: Frame, b: Frame, a_boxes: list[Box], b_boxes: list[Box], diff: PixelDiff | None, margin: float) -> PairResult`

**Rules:**
1. **Groups** (H2, spec step 6): a graph whose nodes are the remaining `before` and `after` boxes and whose edges join
   a before box and an after box that intersect. Every connected component holding at least one box of each side is a
   group, its boxes listed per side in reading order. A remaining before box in no group is **removed**; a remaining
   after box in no group **appeared** (spec step 7). One record shape for any size of change (H5).
2. **Kind** (H4): a side's text is its boxes' texts joined with one space. `kind_of` removes all whitespace from both
   (`"".join(s.split())`) and returns `reread` when equal, `appended` when the after string starts with the before
   string, `truncated` when the before string starts with the after string, else `changed`.
3. `char_diff = textdiff.char_diff(before_text, after_text)` on the exact joined strings; `clock =
   textdiff.is_clock_change(before_text, after_text)`; `in_churn` = any box of the group is; `rect` = union of the
   group's boxes; groups ordered by `(rect[1], rect[0])`. `before` and `after` carry `BoxText(box_ref(frame, id), text)`.
4. **Lifetimes:** each `unchanged`, `same_place` and move pair is a `Pairing`; a `reread` group with exactly one box
   on each side is a `Pairing(how="reread")`; every other group puts all its before ids in `ends` and all its after
   ids in `starts` (Decision D12). Appeared and `flicker_new` ids go to `starts`; removed and `flicker_lost` to `ends`. `pairings`
   are ordered by *b*'s reading order; `starts` and `ends` are in reading order.
5. **Statistics:** `unchanged`, `variants` (unchanged pairs whose texts differ), `same_place`, `moved` (pairs),
   `flicker_new`, `flicker_lost`, `appeared`, `removed` as box refs. `pixels` is `None` when `diff` is; otherwise
   `components = len(diff.components)`; a component is **textless** when no box of either frame has it in its
   `touched_by` set (spec step 8): `textless` counts them and `textless_area` sums their areas;
   `touched_share = round((|touched_a| + |touched_b|) / (boxes of a + boxes of b), 4)`, `0.0` with no boxes;
   `rect_only` = boxes of either frame with `touched_by_rect` true and `touched` false.
6. The returned `Change` has `id = ""`, `kind = "single"`, `t = (a.t_end, b.t_settled)`, `reverts = []` and every
   group's `continues = None`; the stage fills them in Task 12.

**Tests to write first:**
- `test_kind_of`: `("PS>", "PS> git status")` → `appended`; `("PS> git status", "PS>")` → `truncated`;
  `("Status : Creating", "Status : Succeeded")` → `changed`; `("Open in mobile Give feedback", "Open in mobileGive
  feedback")` → `reread`; `("a", "a")` → `reread`.
- `test_keystroke_is_one_appended_group` (H2): fixture K, frames 0 and 1, margin 0.5 → exactly one group: `kind
  "appended"`, `rect (10,50,230,68)`, `before [("0:b2", "PS>")]`, `after [("1:b2", "PS> git status")]`, `char_diff
  [["=", "PS>"], ["+", " git status"]]`, `clock False`. `appeared == []`, `removed == []`, `unchanged == 1`, `variants ==
  0`, `moved == 0`, `same_place == 0`, `flicker_lost == ["0:b3"]`. `pixels`: `changed_fraction 0.0154`, `components 1`,
  `textless 0`, `textless_area 0`, `touched_share 0.2` (one touched box of five), `rect_only 0`. `pairings ==
  [Pairing("b1", "b1", "unchanged")]`, `starts == ["b2"]`, `ends == ["b2", "b3"]`.
- `test_char_diff_reassembles_both_sides`: for `"Status : Creating"` → `"Status : Succeeded"` at one rectangle under a
  changed block: the group is `changed`; joining the `=` and `-` runs gives the before text and the `=` and `+` runs the
  after text. (No exact run list is asserted: Myers may choose among equal-cost scripts.)
- `test_reread_group_continues_the_lifetime`: the two "Open in mobile…" boxes at `(10,10,300,28)` in both frames under
  `block(labels, 1, 10, 28, 10, 300)` → one group `reread`; `pairings == [Pairing("b1", "b1", "reread")]`; `starts ==
  ends == []`.
- `test_nested_boxes_form_one_group`: *a* `b1 "File Edit View" (10,10,200,28)`; *b* `b1 "File" (10,10,50,28)`, `b2
  "Edit View" (60,10,200,28)`; `block(labels, 1, 10, 28, 10, 200)` → one group with one before and two after boxes,
  `kind "reread"`; no pairing; `ends == ["b1"]`, `starts == ["b1", "b2"]`.
- `test_popup_appears_and_a_textless_component`: *a* `b1 "Title" (10,10,110,28)`; *b* the same plus `b2 "Cloud Shell"
  (300,100,380,118)`; `block(labels, 1, 96, 122, 296, 384)` and `block(labels, 2, 180, 190, 350, 360)` → `groups ==
  []`, `appeared == ["1:b2"]`, `unchanged == 1`, `pixels.components == 2`, `textless == 1`, `textless_area == 100`,
  `touched_share == 0.3333`.
- `test_scroll_is_mostly_moved` (H3, H5): Task 9's scroll fixture under `block(labels, 1, 20, 78, 10, 100)` → `moved ==
  2`, `removed == ["0:b1"]`, `appeared == ["1:b3"]`, `groups == []`.
- `test_variant_on_untouched_pixels_is_not_a_change` (H1): *a* `b1 "Subscription ID :3e6b" (10,100,200,118)`; *b* `b1
  "SubscriptionID :3e6b" (10,100,201,119)`; no changed pixels → `unchanged == 1`, `variants == 1`, no groups, nothing
  appeared or removed.
- `test_no_boxes_at_all`: both box lists empty, one component → `groups == []`, `pixels.textless == 1`,
  `touched_share == 0.0`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_pair.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6; `track_pair` composes Tasks 7–9 in the spec's order.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(track): per-box change records: groups, whitespace-blind kinds, appeared, removed (H2, H4, H5)`

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
2. `step`: each `Pairing` appends *b*'s box to the lifetime that holds *a*'s box and counts *b*'s text in `readings`;
   `how == "moved"` sets `moved`. Each id in `starts` begins a lifetime. A lifetime that is not continued simply stops.
   Every box of *b* must be in exactly one of the pairings or `starts`, else `ValueError` naming the box.
3. `finish`: `text` is the reading with the highest count; a tie goes to the reading sighted first (spec principle 5:
   de-noising of repeated readings; a text seen once has its one reading). `unstable = len(readings) > 1`. `sightings =
   len(boxes)`. `first = FrameTime(frame, t_settled)` of the first box's frame; `last = FrameTime(frame, t_end)` of
   the last box's frame (Decision D15). Sorted by id number.
4. Nothing here reads how long a text lasted as evidence of anything; the fields are measurements.

**Tests to write first:**
- `test_lifetimes_over_three_frames`: frames 0, 1, 2 with `(t_settled, t_end)` = `(0.0, 1.0)`, `(1.5, 2.0)`, `(2.5,
  9.0)`. Frame 0 boxes `b1 "Title"`, `b2 "PS>"`. Step to frame 1 (boxes `b1 "Title"`, `b2 "PS> git status"`):
  pairings `[("b1","b1","unchanged")]`, `starts ["b2"]`, `ends ["b2"]`. Step to frame 2 (boxes `b1 "Title"`, `b2 "PS> git
  status"`, `b3 "On branch main"`): pairings `[("b1","b1","unchanged"), ("b2","b2","unchanged")]`, `starts ["b3"]`.
  Expected: `L1 "Title"` boxes `["0:b1","1:b1","2:b1"]`, sightings 3, first `(0, 0.0)`, last `(2, 9.0)`, stable;
  `L2 "PS>"` boxes `["0:b2"]`, first `(0, 0.0)`, last `(0, 1.0)`; `L3 "PS> git status"` boxes `["1:b2","2:b2"]`, first
  `(1, 1.5)`, last `(2, 9.0)`; `L4 "On branch main"` boxes `["2:b3"]`.
- `test_majority_reading_and_tie`: one box followed over three frames reading `"Subscription ID"`, `"SubscriptionID"`,
  `"Subscription ID"` → `text "Subscription ID"`, `readings {"Subscription ID": 2, "SubscriptionID": 1}`, `unstable`;
  over two frames reading `"A b"`, `"Ab"` → `text "A b"`.
- `test_moved_sets_the_flag`; `test_unaccounted_box_raises` (a `PairResult` that omits `b2`).

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_lifetimes.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–4.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(track): box lifetimes with majority readings and variants (H7)`

### Task 12: The `track` stage: ids, kinds, `continues`, `reverts`, files, CLI

**Files:**
- Create: `src/scry/track/stage.py`, `tests/test_track_stage.py`
- Modify: `src/scry/config.py` (`TrackConfig`), `scry.toml`, `src/scry/cli.py`

**Interfaces:**
- Produces: `TrackConfig` as `Config.track` with `margin: float = 0.5  # × the median box height of the two frames; 0 =
  exact touch`; TOML `[track] margin = 0.5`. `transition_kind(a: Frame, b: Frame, change: Change) -> str`;
  `link_continues(prev: Change | None, cur: Change) -> None`; `find_reverts(prev: Change, prev_diff: PixelDiff | None,
  zb: PixelDiff | None, a: Frame, b: Frame) -> list[Revert]`; `run_track(run: Run, cfg: Config) -> None`; CLI
  `scry track RUN_DIR [--config PATH] [--verbose]`; `run` gains `track` after `read`.

**Rules:**
1. Pairs are consecutive records of `frames.jsonl`. Boxes come from `boxes.jsonl` by frame number; a frame without a
   boxes record raises `ValueError("… run `scry read` first")`. Change ids `T1`, `T2`, … in order.
2. `transition_kind` (spec step 11): `unsettled` when either frame is not `settled`; else `trivial` when the change has
   at least one group, every group has `clock` true, and nothing appeared or was removed; else `single`.
3. `link_continues` (spec step 10): for each group of `cur`, the first of its `before` refs (reading order) that is an
   `after` ref of group *j* of `prev` sets `continues = f"{prev.id}/{j}"`. An exact identity through a shared box;
   geometry is not consulted.
4. `find_reverts` (H8, spec step 9; Decision D14): `prev` is the change *z*→*a*, `prev_diff` its `PixelDiff`, `zb` the
   direct `PixelSource.diff(z, b)`. With any of the three `None`, return `[]`. For each component *k* of `prev_diff` in
   list order: it is undone when `zb.labels` is 0 at every pixel where `prev_diff.labels == k`. Each undone component
   yields `Revert(of=prev.id, rect=component.bbox, hold_s=round(b.t_change − a.t_change, 3))`. No time constant; both
   transitions stay and nothing is folded.
5. Lifetimes through `LifetimeBuilder`. Zero frames: both files are written empty. One frame: no changes, one lifetime
   per box.
6. Inputs `[run.frames, run.boxes]`; config hash `config_hash(cfg, "track", "decode")` (θpix and θmin live in
   `[decode.detect]`); manifest key `track` with stats `transitions`, `kinds`, `groups` by kind, `appeared`,
   `removed`, `moved`, `same_place`, `unchanged`, `variants`, `flicker_new`, `flicker_lost`, `reverts`, `lifetimes`,
   `unstable`, `margin`, `seconds`.

**Tests to write first** (a helper writes `L`-mode PNGs from arrays plus `frames.jsonl` and `boxes.jsonl` by hand; frame
size 200×400; every box 18 px tall unless stated):
- `test_tooltip_reverts_with_hold_time` (H8): frames 0, 1, 2 with `t_change` 0.0, 1.0, 3.8. Images: black; black with
  `[100:120, 300:380] = 200`; black. Boxes: none; `b1 "Cloud Shell" (305,101,375,119)`; none → two changes. `T1.appeared
  == ["1:b1"]`, `T1.reverts == []`. `T2.removed == ["1:b1"]`, `T2.reverts == [Revert(of="T1", rect=(300,100,380,120),
  hold_s=2.8)]`.
- `test_partial_return_is_not_a_revert`: frame 2 keeps `[100:120, 300:340] = 200` → `T2.reverts == []`.
- `test_continues_links_consecutive_growth`: three frames with boxes `b1 "PS>" (10,50,130,68)`, `b1 "PS> git"
  (10,50,170,68)`, `b1 "PS> git status" (10,50,230,68)`; images black, then `[52:66, 140:168] = 255`, then additionally
  `[52:66, 176:228] = 255` → `T1.groups[0].kind == "appended"` and `continues is None`; `T2.groups[0].kind ==
  "appended"` and `continues == "T1/0"`; lifetimes: three, each with one sighting.
- `test_unsettled_and_clock_kinds`: a pair whose later frame has `settled = False` → `kind "unsettled"`; a settled pair
  with `b1 "10:41 AM" (350,180,398,198)` → `b1 "10:42 AM"` at the same rectangle over a changed block → one group,
  `clock` true, `kind "trivial"`.
- `test_size_mismatch_and_missing_png_degrade`: frame 1's PNG is 100×200, frame 2's PNG is deleted, the boxes are
  identical in all three frames → `T1.pixels is None`, `T2.pixels is None`, no groups, `same_place` equals the box
  count, `reverts == []`, no exception.
- `test_zero_and_one_frame_runs`; `test_missing_boxes_record_is_an_error`;
  `test_skips_when_up_to_date_and_reruns_on_margin_change` (rewrite `cfg.track.margin` to 0.0 → the stage runs again);
  `test_cli_track` (exit code 0, both files written).

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_track_stage.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6, the config key and the CLI command.
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
  - `incremental_projection(boxes, changes) -> dict`

**Rules (Decision D17 covers the definitions):**
1. `select` with `(lo, hi)`: boxes records with `lo ≤ frame ≤ hi`; changes with `lo ≤ from_frame` and `to_frame ≤ hi`;
   lifetimes with at least one sighting in the range (their `first` and `last` are not clipped). `None` selects all.
2. `box_stability = (Σ unchanged − Σ variants) / (Σ unchanged + Σ len(flicker_lost))`, rounded to 4; `None` when the
   denominator is 0. No overlap threshold is involved.
3. `touched_share_low_half`: the changes with `pixels` not null, sorted by `changed_fraction` ascending then id number;
   take the first `ceil(n / 2)`; the `statistics.median` of their `touched_share`, rounded to 4; `None` when there are
   none. A rank rule, so no threshold decides what "near-static" means.
4. `totals`: `{"transitions": {kind: n}, "groups": {kind: n}, "appeared", "removed", "moved", "same_place",
   "unchanged", "variants", "flicker_new", "flicker_lost", "reverts", "textless", "rect_only"}` summed over changes.
5. `fragmentation`: `{"lifetimes": N, "distinct_texts": D, "per_text": round(N / D, 3), "unstable": U,
   "single_sighting": S, "top": [(text, count), …]}`; `top` holds the texts with the most lifetimes, by count descending
   then text; `per_text` is `None` when `D == 0` (H7).
6. `incremental_projection`: targets of a change = boxes in its groups' `after` lists + `appeared` + `flicker_new`.
   `{"frames": F, "boxes": total boxes, "calls": 1 + number of changes with at least one target (0 when F == 0),
   "target_boxes": boxes of the first selected frame + Σ targets, "share_of_boxes": round(target_boxes / boxes, 4)}`
   (spec §2 and §9 P0: it prices incremental annotation in advance; the first frame is a full call).

**Tests to write first:**
- `test_box_stability`: two changes with `unchanged` 98 and 50, `variants` 2 and 0, `flicker_lost` `["0:b9"]` and `[]` →
  `0.9799` (146 / 149). No changes → `None`.
- `test_touched_share_low_half`: four changes with `(changed_fraction, touched_share)` `(0.001, 0.02)`, `(0.2, 0.5)`,
  `(0.0005, 0.01)`, `(0.3, 0.9)` → `0.015`. A change with `pixels=None` is ignored.
- `test_fragmentation`: lifetimes with texts `"a"`, `"a"`, `"b"`, sightings 1, 3, 1, the second unstable → `lifetimes 3`,
  `distinct_texts 2`, `per_text 1.5`, `unstable 1`, `single_sighting 2`, `top [("a", 2), ("b", 1)]`.
- `test_incremental_projection`: boxes per frame 100, 101, 101, 113 (frames 0–3); three changes with targets 1 (one
  group with one after box), 0, 12 (twelve appeared) → `frames 4`, `boxes 415`, `calls 3`, `target_boxes 113`,
  `share_of_boxes 0.2723`.
- `test_select_by_frames`: changes `T1 (0→1)`, `T2 (1→2)`, `T3 (2→3)` and range `(1, 2)` → only `T2`; a lifetime with
  boxes `["0:b1", "1:b1"]` is kept, one with `["3:b2"]` is not.
- `test_totals_sums_kinds`: two changes, one `single` with groups `appended`, `changed`, one `trivial` with a `changed`
  group → `transitions {"single": 1, "trivial": 1}`, `groups {"appended": 1, "changed": 2}`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_metrics.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6.
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
   `submitted_frame, submitted_t` = the last pair of the fourth. `n` is the first column as an integer.
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
- `test_malformed_row_raises`: a row with a missing cell → `ValueError` naming line 5 of the fixture.

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
  regenerated, written inside the run directory.

**Rules:**
1. Markdown with these headings, in this order: `# track report`; `## Run` (frames, boxes, transitions, the `read`
   engine settings from the manifest, `track.margin`, θpix, θmin, the frame range); `## Transitions` (one table row per
   change: id, frames, kind, changed %, components, textless, touched share, rect-only, groups by kind, appeared,
   removed, moved, same place, unchanged, variants, flicker new and lost, reverts); `## Totals`; `## Guards`
   (`box_stability`, `touched_share_low_half`, total `rect_only`); `## Lifetimes` (`fragmentation`); `## Incremental
   annotation projection`; `## Text changes` (every group of kind `appended`, `truncated` or `changed`: change id, kind,
   before → after in back-quotes, `continues`; at most 20 lines per change, then "… and N more"); `## Unstable
   lifetimes` (up to 50, by sightings descending: id, majority text, readings with counts, first and last frame);
   `## Reverts` (every one: change id, `of`, rectangle, hold time); and, with a ground truth, `## Commands` (the rows of
   `score_exact` and `exact_rate`, then the never-run table marked "information only").
2. `write_sheets` makes the evidence the executor reads against the frames (spec §4: hypotheses are judged by reading
   records against frames). With `random.Random(seed)`, sample up to `per_kind` of each: groups per kind, appeared
   boxes, removed boxes, reverts, unstable lifetimes, and `flicker` boxes. One PNG each: the crop of the earlier frame
   above the crop of the later frame (for a revert: frames *z*, *a*, *b*; for a lifetime: first and last sighting), the
   crop being the record's rectangle grown by twice the margin in pixels and clipped. Names
   `sheets/T12-g0-appended.png`, `sheets/T12-appeared-b40.png`, `sheets/T12-removed-b3.png`, `sheets/T12-revert0.png`,
   `sheets/T12-flicker-new-b9.png`, `sheets/L388.png`. A missing PNG skips that sheet.
3. The report states no pass or fail and compares with no threshold.

**Tests to write first** (the run directory is Task 12's three-frame typing fixture, produced by `run_track`):
- `test_report_has_sections_and_numbers`: the text contains each heading of rule 1 up to `## Reverts`, the row ids `T1`
  and `T2`, the word `appended`, and the string `` `PS> git` → `PS> git status` ``.
- `test_report_frames_filter`: `frames=(1, 2)` → the transitions table has `T2` and not `T1`.
- `test_report_with_ground_truth`: a ground-truth file with one executed row `` `git status` `` first visible at frame
  2 → the `## Commands` section shows `exact` true, `frame_error 0`, and `1 / 1`.
- `test_report_renders_on_empty_run`: a run with zero frames → the headings render and the tables are empty.
- `test_sheets_written`: `write_sheets(..., per_kind=5, seed=0)` returns paths that exist, open with Pillow and include
  `T1-g0-appended.png` and `T2-g0-appended.png`.
- `test_cli_report_writes_file`: exit code 0 and `report.md` exists in the run directory.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_report.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–3 and the command.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat: scry report: track metrics, command exactness and evidence sheets`

### Task 16: P0 — the first real run (free)

No code. `runs/` is git-ignored; `runs/aks` is read and never written.

- [ ] **Step 1: Bring the 221 decoded frames over.**
  `uv run scry subset runs/aks --out runs/p0 --frames 0-220 --no-share-cache`
  Expected: `runs/p0: 221 frames; …`; `runs/p0/frames.jsonl` has 221 lines; `git status` clean; `ls runs/aks` unchanged.
- [ ] **Step 2: Read.** `uv run scry read runs/p0` (about five minutes). Expected: `boxes.jsonl` with 221 records;
  note `boxes` and `dropped_empty` from `manifest.json`.
- [ ] **Step 3: Track.** `uv run scry track runs/p0`. Expected: `changes.jsonl` with 220 records and `lifetimes.jsonl`.
- [ ] **Step 4: Reports.**
  `uv run scry report runs/p0 --ground-truth docs/ground-truth/span2-commands.md --out report.md`
  `uv run scry report runs/p0 --frames 145-155 --out report-smoke.md`
  `uv run scry report runs/p0 --frames 155-187 --ground-truth docs/ground-truth/span2-commands.md --out report-span2.md`
- [ ] **Step 5: Margin sensitivity** (spec §9 P0: margin 0, 0.25, 0.5, 1.0; 0.5 is `runs/p0`). For each `M` in `0`,
  `0.25`, `1.0`, with `N` = `000`, `025`, `100`:
  `mkdir runs/p0-m$N && ln -s ../p0/frames runs/p0-m$N/frames && cp runs/p0/manifest.json runs/p0/frames.jsonl runs/p0/boxes.jsonl runs/p0-m$N/`
  `sed "s/^margin = 0.5$/margin = $M/" scry.toml > runs/p0-m$N.toml`
  `uv run scry track runs/p0-m$N --config runs/p0-m$N.toml && uv run scry report runs/p0-m$N --config runs/p0-m$N.toml --frames 155-187 --ground-truth docs/ground-truth/span2-commands.md --no-sheets`
- [ ] **Step 6: Read the records against the frames.** No pass threshold is set for any of this (owner's ruling); the
  job is to say what was seen. Use the sheets under `runs/p0/sheets/` and the frames themselves.
  - **H1** — every sheet of an unstable lifetime (up to 30) and every flicker sheet (up to 30): is any a real change of
    text on screen that the veto hid? Also the five transitions with the largest `changed_fraction`: did any box that
    visibly changed stay in `unchanged`?
  - **H2** — every `appended` and `truncated` group of span 2 (the report lists them), and 20 sampled `changed` groups:
    is each before box the after box's earlier self? Any growing text reported as `appeared` + `removed` instead?
  - **H3** — every transition with `moved ≥ 10`, up to ten of them, five moved pairs each: same text, really moved?
    Any text that changed but was cancelled as a move?
  - **H4** — every `reread` group, up to 30: whitespace noise only?
  - **H5** — the five largest and five smallest non-empty changes: is the one record shape readable at both ends?
  - **H6** — `rect_only` totals per transition, and ten boxes behind the largest counts: would a rectangle test have
    called them changed wrongly?
  - **H7** — `fragmentation`: the twenty texts with the most lifetimes; for ten, why did the lifetime split?
  - **H8** — every `reverts` entry; and whether the two tooltips of the smoke span (frames 149 and 151) were found.
  - **Commands** — the `## Commands` table of span 2 at each margin.
- [ ] **Step 7: Ledger row and hand-back.** Append one row to `docs/decision-ledger.md` (next free number): what ran
  (commit hash, frames, boxes, transitions, lifetimes, wall times); totals by kind; `box_stability`,
  `touched_share_low_half`, `rect_only`; fragmentation; the incremental-annotation projection (calls and target boxes
  against 221 frames and all boxes) for the whole video and both spans; `exact_rate` and the frame and time errors on
  span 2 at the four margins; one line per hypothesis saying what was seen, with the transition or lifetime ids that
  show it; every case from the spec's watch list that actually occurred, with ids. Commit:
  `docs: ledger row for P0 (read and track over the full sample)`. Hand back the row, the three reports, and a list of
  any rule in this plan that the real data showed to be wrong or undefined — as findings, not fixes.

---

## Decisions this plan makes (for the reviewers)

The spec is silent or looser on each of these; none is settled until reviewed.

- **D1. One reader, a core dependency.** The Apple Vision adapter and PyObjC go in the branch's first commits (spec §8
  and §10 step 0), and `rapidocr` + `onnxruntime` move from an extra into `dependencies`, because `read` has one engine.
- **D2. `agent.py` and `prompts/` are deleted whole.** The spec removes "the tools of `agent.py`" and "the four prompt
  modules"; the loop cannot import without its prompt. It returns from the tag with the `ask` stage.
- **D3. Kept modules whose stage is not rebuilt here are reduced to what imports cleanly:** `index.py` keeps storage,
  search and fusion; `overlay.py` keeps its drawing functions (now over `Box`) and loses `run_overlay`; no CLI command
  for either. `outline` stays as it is. `run` is reduced to `outline → decode → read → track`. A `report` command is
  added. So the CLI is `decode, outline, read, track, report, subset, setup, run`.
- **D4. Names.** `stage1.py` → `decode.py`, the PyAV helpers → `video.py`, `stage2a.py` → `read.py`; `Stage1Record` →
  `Frame`; TOML `[stage1.*]` → `[decode.*]`, `[ocr]` → `[read]`, new `[track]`; manifest keys `decode`, `read`,
  `track`. The `effort_stage*` keys, `Stage5Config` and `HierarchyConfig` are removed until their stages return under
  new names. Config models reject unknown keys, so a stale section fails instead of being ignored.
- **D5. `read` drops two things the spec's `Box` does not carry:** boxes whose text is empty after stripping (counted),
  and the `confusable` flag (nothing in the spec consumes it).
- **D6. Legacy import goes through `subset`**, which prefers a source's `stage1.jsonl` and maps the manifest key.
  The copied `decode` entry keeps the source's config hash, so `scry run` on an imported directory may decide to decode
  again; P0 therefore uses the stage commands.
- **D7. "Reading order" is `read`'s id order** — boxes sorted by top edge then left edge — everywhere. There is no
  row-banding rule and no half-height overlap rule.
- **D8. A touched box's earlier (or later) self may be an untouched box.** The pools admit an untouched, unmatched box
  that intersects a touched box of the other frame. Without this, a growing text whose old extent lies outside the
  changed pixels would be reported as `appeared` next to an unrelated silent ending, contradicting H2. The spec's step
  6 says "the remaining before and after boxes" without saying whether an untouched box can remain.
- **D9. Flicker.** An untouched box with no counterpart and no touched neighbour yields no change record (H1: nothing
  changed there); its lifetime starts or ends silently and it is counted in `flicker_new` / `flicker_lost`, which P0
  reads for H1 and H7.
- **D10. One-to-one matching is greedy by intersection area, ties by reading order,** in step 3 and in step 4.
  "Overlaps most" in the spec does not say what happens when two boxes claim one.
- **D11. Text equality in steps 4 and 5 is exact string equality.** Whitespace-blind comparison is confined to kind
  labels (H4). The owner's brief for this plan lists a `visual_only` kind; revision 3 expresses that case as the
  `same_place` count (something visual changed over unchanged text) and this plan follows revision 3.
- **D12. A group is a connected component over before–after intersections only** (two boxes of one frame never link
  directly). A side's text is its boxes joined with single spaces in reading order. Only a one-to-one `reread` group
  continues a lifetime; a re-split `reread` (one box became two) ends and starts lifetimes.
- **D13. Measured fields beyond the spec's sketches:** `pixels.textless_area`, `pixels.rect_only`, `unchanged`,
  `variants`, `flicker_new`, `flicker_lost`, `Group.in_churn`, `Group.clock`. `appeared` and `removed` stay lists of box
  refs as in the sketch; their texts join from `boxes.jsonl`.
- **D14. Reverts are tested per component of the previous transition, on that component's own pixels** (not its
  rectangle, for the reason behind H6); `hold_s = t_change(b) − t_change(a)`; `continues` is written `"T8/0"`.
- **D15. Lifetime details:** `first.t` is the first frame's `t_settled`, `last.t` the last frame's `t_end`; a tie for
  the majority goes to the reading sighted first; ids in creation order.
- **D16. Margin arithmetic:** `floor(margin × median + 0.5)` pixels, the median over both frames' boxes, grown
  rectangles clipped to the frame; zero boxes → 0.
- **D17. Metric definitions:** `box_stability` without any overlap threshold; `touched_share` summarised over the
  lower half of transitions by `changed_fraction` (a rank, not a cut-off); exactness as a case-sensitive substring
  after whitespace collapsing; entries under 4 non-space characters reported and kept out of rates; never-run entries
  reported and never rated.
- **D18. One whole-video run; spans are report filters** (`--frames`), and margin sensitivity uses light run
  directories that share the frames by symlink. Evidence sheets are part of `scry report`, as real code with tests.
- **D19. `decode`'s record keeps its `caret` field** ("unchanged in content", spec §5) though nothing reads it.
- **D20. `track` always works at full resolution** and ignores `[decode.detect] downsample`.
- **D21. No `found` metric yet.** The spec's *found* needs the index; this plan reports *exact*, first-sighting frame
  and time error for the OCR reader only.

## Self-review

- **Spec coverage.** §5 records → Task 4. §6 `read` → Task 6. §6 `track` steps 1–2 → Task 7; 3 → Task 8; 4–5 →
  Task 9; 6–8 → Task 10; 9–11 → Task 12; lifetimes → Task 11. §8 removals → Tasks 1–3. §9 P0 (H1–H8, margins,
  fragmentation, incremental projection, the OCR reader's command metrics) → Tasks 13–16. §10 steps 0–2 → the whole
  plan. Not covered by design: `annotate`, `interpret`, `summarize`, `index`, `ask` (later plans), the *found* metric
  (D21), README and CONTRIBUTING updates (they follow the design's revision 7 at the end of the re-base).
- **Placeholders.** None: every test names its fixture and its expected values; no step says "handle edge cases".
- **Type consistency.** `Box`, `FrameBoxes`, `Change`, `Group`, `Revert`, `Lifetime`, `FrameTime`, `PixelStats`,
  `BoxText` (Task 4) are the names used in Tasks 6–15; `PixelDiff`, `touched`, `touched_by`, `touched_by_rect`,
  `margin_px`, `grow` (Task 7) in 8, 10, 12, 15; `Pools`, `match_one_to_one`, `intersection` (Task 8) in 9–10;
  `Pairing`, `PairResult`, `track_pair` (Task 10) in 11–12; `LifetimeBuilder.step(b, b_boxes, result)` (Task 11) in 12.
- **Review focus.** Each of the five lines names its test and task.
