# Re-base step 4: the evaluation harness for phases P0–P6 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **One deliberate adaptation of the writing-plans format: this plan contains NO implementation bodies and no test
> code.** The owner forbids code that exists anywhere except as the real implementation on the branch with its tests;
> no drafter or reviewer writes a prototype, a scratch implementation or a trial script, not even to check an idea. So
> every task gives: the files; the public interface (signatures, record fields, file formats, config keys); the
> behaviour as numbered rules; the tests to write FIRST, each named, with its concrete fixture and exact expected
> values (all arithmetic below was done by hand); the commands; the commit. The implementer writes the test code and
> the implementation on the branch from these. Reviewers of this plan read and reason; they do not execute anything.

**Goal:** Make phases P0–P6 of the re-base proposal runnable and comparable: a committed run matrix expands into cold
run directories, a runner executes them, committed code scores them against the owner's ground truth, measures the
noise between identical runs, marks every difference as inside or outside that noise, and writes Markdown reports
with dollars per frame and per video beside every quality number.

**Architecture:** A subpackage `scry.evaluation` beside the pipeline, reached through `scry eval …`. It never edits a
stage's file: it derives run directories with the existing `subset` tool, calls the stage entry points in-process,
and reads their records through one module of thin adapters (`adapters.py`), the only place that touches the sibling
plans' loaders. Every measurement is a pure function over records, producing per-unit values (per ground-truth entry,
per frame, per transition, per question) so that any two configurations can be paired over the same units. Matrix
files (`evals/*.toml`) hold everything that is specific to a video or a phase; the code holds none of it.

**Tech stack:** Python ≥ 3.12 with `uv`; pydantic 2, typer, rapidfuzz, the Anthropic SDK through the existing
`scry.providers` (judge calls only), `tomllib`, SQLite FTS5 through the existing `scry.index`; pytest. No new
dependencies.

**Spec:** `docs/proposals/2026-09-21-boxes-mode-rebase.md`, revision 3.1: §9 (Evaluation) is what this plan implements;
§4 (principles 8 and 9, H1–H8), §5 (Records) and §2 (stages and files) are the contract with the sibling plans.
Ground truth: `docs/ground-truth/span2-commands.md` (accepted) and `docs/ground-truth/span2-questions.md` (draft,
written with this plan). Measured background: `docs/decision-ledger.md` L28–L43, above all L42 (identical cold runs
differ), and L44–L46 (the owner's standing rules while away; plan 1's reconciliation). Sibling plans:
`…-1-read-track.md` (reconciled, commit `684618a`, being implemented), `…-2-annotate.md` and
`…-3-interpret-summarize-index-ask.md` (committed as drafted, before review; read while this plan was being finished;
see "Interface assumptions"). Executors read the spec with this plan.

**Order of execution:** after plans 1–3 have landed (spec §10 step 7). Tasks 2, 3, 8, 11, 12 and 13 touch nothing
beyond plan 1 and can be built while plans 2 and 3 are in progress; the others consume plan 2's joined labels or plan
3's cost functions, scorers, index and `ask`.

## Global Constraints

The owner's rulings, binding on every task:

- **Cost is an outcome.** Every quality number in every report has dollars per frame and dollars per video beside it.
  Cost includes cache-creation tokens, which today's accounting drops (`docs/open-items.md`, "Usage accounting");
  plan 3's Task 3 prices them in `scry.costs`, and this plan builds on that function and adds no second price list.
- **Primary scores** per executed command: *found* and *exact*. **Secondary**, reported beside them and breaking ties
  only: time error of first appearance and of submission, and *false run*. Negative questions weigh less than
  positive ones. The harness encodes "weighs less" as order, never as a numeric weight.
- **No success threshold is pre-committed, anywhere.** No report says pass or fail. Fixed in advance is only what
  counts as evidence: metrics are computed by committed code written before a phase runs; the noise floor is measured
  first; comparisons are paired over the same frames; a difference inside the noise is no difference. The only verdict
  words are `outside`, `inside` and `unknown` (of the noise), and `not comparable`.
- **Runs that judge a model call are cold with repeats:** a private, initially empty call cache per run directory,
  never a symlink. Cached or copied model outputs are used only to hold the upstream of a comparison fixed.
- **Label quality is judged by eye on samples.** There is no hand-made label ground truth; the harness builds the
  samples and tallies the owner's ticks. Label consistency across frames decides nothing.
- **Persistence is never evidence that a command ran.** No metric reads a lifetime's duration or sighting count as
  evidence of execution; *false run* and the submission metrics read only `interpret`'s `submitted`.
- **No per-video constants in code.** Frame ranges, popup frames, ground-truth paths and the projection length live in
  `evals/*.toml`. A test scans the package for them (Task 14).
- Phases report as they finish; nothing in the harness waits for an approval or enforces a budget.
- **Simplify before repairing; no machinery pre-emptively; what matters is that it works** (ledger L44, spec §12).
  The harness measures and reports; where a rule below goes beyond what a phase needs, the Decisions section names
  it as a candidate to strike, and a reviewer's first answer to a finding here should be to remove, not to add.

Engineering constraints:

- Work only on branch `rebase-boxes`. `uv run pytest` reports 0 failures after every commit.
- Unit tests only: synthetic records written in the test, fake stage functions, fake providers, fake clocks. No test
  reads the sample video or a directory under `runs/`, calls the network or a model, or needs an API key. Three tests
  read committed documents (the two files under `docs/ground-truth/`, and `evals/*.toml`) on purpose, to catch a
  silent edit.
- Real code in the package with tests; no throwaway scripts. The harness writes only inside run directories it created
  (`evalrun.json`, `config.json`, `answers.jsonl`, `judgments.jsonl`, `scorecard.json`) and inside the results
  directory; it never writes a stage's file and never writes under the matrix's `source`.
- Rounding: dollars 4 places, dollars per video 2, seconds 1, rates and shares 4, time errors 2.
- Commit messages end with the attribution lines the session supplies.

## Review Focus

Conditions the spec implies and that are most likely to bite a person using the harness; each has a test in the task
that owns the code.

1. **A run is interrupted and resumed.** A stage's manifest usage may then cover only the second attempt, and the
   earlier calls come back as cache hits. Expect the cost never to be under-reported and the run to be flagged: the run total
   is the larger of manifest usage and the private cache's summed usage (Task 1
   `test_resumed_run_costs_come_from_the_call_cache`, Task 3 `test_resume_skips_done_and_restarts_failed`).
2. **The same string is an executed command and, later, a never-run suggestion** (`kubectl config current-context`,
   executed row 6 and never-run row 4). Expect a late sighting not to pass silently for the executed one, and a correct
   `submitted: yes` that lands on the suggestion's frame to be visible as such beside the false-run score (Task 4
   `test_exact_by_reader_and_window`, `test_shared_claim_is_flagged`).
3. **Runs with pieces missing:** the no-annotation base has no `annotations.jsonl` and no second reader; an `interpret`
   call failed; the index was not built. Expect a scorecard with `null` sections and a warning, never a crash, and
   comparisons that drop the missing units and say how many (Task 10 `test_scorecard_without_annotations_or_index`,
   Task 12 `test_missing_units_are_dropped_and_counted`).
4. **Things that must not be compared are compared:** different frame ranges, a ground-truth or question file edited
   between runs, a run whose metric code changed after it started. Expect a refusal or a "not comparable" row, and a
   warning at the top of the report (Task 12 `test_different_frames_are_refused`,
   `test_edited_ground_truth_is_not_comparable`, Task 10 `test_metric_code_changed_since_run_is_flagged`).
5. **A typo in a matrix file:** a config key that does not exist, two axis values that are the same configuration, a
   hyphen in a name. Expect failure at expansion, before a cent is spent (Task 2
   `test_config_for_applies_overrides_and_rejects_unknown_keys`, `test_duplicate_axis_values_rejected`,
   `test_bad_names_and_bad_excludes`).

Also covered where it arises: a one-letter command matched loosely (Task 4 `test_one_letter_answers_need_equality`);
a judge that omits a rubric line (Task 7 `test_missing_item_is_an_error_not_a_default`); an unreviewed by-eye item
(Task 8 `test_unreviewed_items_are_ignored`); an answer that cites nothing or cites what does not exist (Task 6
`test_citation_check`). Command text full of FTS5 syntax is plan 3's Review Focus 3.

## File structure at the end of this plan

```
src/scry/
  cli.py                     gains the sub-command group `eval`                                                  (modified)
  evaluation/
    __init__.py
    accounting.py            per-stage, per-frame, per-video dollars and seconds; manifest against call cache
    matrix.py                evals/*.toml → Matrix → RunSpec list; config overlays
    runner.py                cold run directories via subset; stages in-process; evalrun.json; resume; code identity
    adapters.py              the only module that touches the sibling plans' loaders, search and ask
    commands.py              one row per entry from plan 1's and plan 3's scorers; exact per reader; per-unit values
    guards.py                box stability, touched share, one-container share, repairs, unassigned, citations, popups
    questions.py             question-file parser; the question runner through `ask`; citation check
    judge.py                 rubric scoring by a separate model call; label derivation
    byeye.py                 blind answer sheet, tick parser, judge-against-eye agreement, by-eye override
    labelsheet.py            by-eye sheets for containers and links over shared sample frames; tallies
    scorecard.py             one run → scorecard.json (scores, guards, cost, per-unit values, warnings)
    noise.py                 paired differences between identical runs; the noise floor
    compare.py               paired comparison of two configurations; inside / outside / unknown
    reporting.py             Markdown phase report, scores.json, ledger-row template
    cli.py                   `scry eval expand|run|status|judge|sheet|labelsheet|score|report`
evals/                       p0-read.toml p0.toml p1.toml p2-grouponly.toml p2-transcribing.toml p3.toml p4.toml
                             p5.toml README.md
docs/results/<phase>/        report.md scores.json noise.json ledger-row.md answer-sheet.md label-sheet.md (committed)
runs/eval/<phase>/<run>/     run directories (git-ignored, like all of runs/)
tests/                       test_eval_accounting.py test_eval_matrix.py test_eval_runner.py
                             test_eval_commands.py test_eval_guards.py test_eval_questions.py test_eval_judge.py
                             test_eval_byeye.py test_eval_labelsheet.py test_eval_scorecard.py test_eval_noise.py
                             test_eval_compare.py test_eval_reporting.py test_eval_cli.py
```

## Interface assumptions

Plan 1 is reconciled with its reviews (commit `684618a`; ledger L45, L46) and is being implemented. Plans 2 and 3
are committed as drafted, before review, and were written against plan 1's earlier record shapes (change *groups*,
`readings` as counts); they will be reconciled to plan 1's `records` list and to `readings` as reading → frames.
This plan is insulated from both changes: of a `Change` it reads `id`, `from_frame`, `to_frame` and `t[1]` and
otherwise goes through plan 1's metric functions; of a `Lifetime` it reads `id`, `text`, the keys of `readings`,
`first` and `last`. Every use of plans 2 and 3 goes through `scry/evaluation/adapters.py`, so a renamed loader costs
one adapter function, not a metric. The values this plan's tests assert on plan 3's Fixture M (four frames with 3, 3,
5, 5 boxes; `unchanged` 2, 3, 4 and one variant; seven lifetimes, one unstable; interpretation T2 `git status`,
`yes`) are to be re-read from the reconciled plan 3 when Tasks 4, 5, 9 and 10 start.

**Overlaps, resolved so that nothing is defined twice.** The ground-truth parser, *exact* for the OCR reader and the
first-appearance error are plan 1's (its Task 14). *Found*, the submission error and *false run* are plan 3's (its
Task 16). Pricing of cache-creation tokens, the batch price, usage summed over retries and `run_costs` are plan 3's
(its Task 3; plan 2 creates them if it lands first). The track guards are plan 1's (its Task 13). `scry report` (one
run, read by eye) belongs to plans 1 and 3. This plan consumes all of these and adds what compares runs: exactness per
reader, per-unit values, the matrix, the cold runner, dollars and seconds per frame and per video, the question set,
the judge, the by-eye sheets, the noise floor, the paired comparison and the phase report.

**Pinned by the sibling plans and consumed as written:**
- P1 (plan 1). `scry.groundtruth`: `Entry(n, text, first_frame, first_t, submitted_frame, submitted_t, frames)`,
  `parse_commands(md) -> (executed, never_run)`, `scorable(e)` (at least 4 non-space characters), `score_exact(entries,
  lifetimes) -> list[dict]` with keys `n, text, scorable, exact, matches, lifetime, first_frame, frame_error, t_error`
  (a case-sensitive substring test after `scry.textdiff.norm`), `exact_rate`. `scry.metrics`: `box_stability`,
  `touched_share_low_half`, `fragmentation`. Records and loaders: `Frame`, `Box`, `FrameBoxes`, `Change` (`id`,
  `from_frame`, `to_frame`, `t`), `Lifetime` (`id`, `text`, `readings`, `first`, `last`; `first.t` the first frame's
  `t_settled`, `last.t` the last frame's `t_end`), `parse_box_ref`, `Run.load_frames/load_boxes/load_changes/
  load_lifetimes`. `scry.subset.make_subset(src_root: Path, out, frames, share_cache=True) -> Run`, never writing under
  `src_root`. Every config model rejects unknown keys. `scry.read.run_read`, `scry.track.stage.run_track`. `runs/p0`
  holds the 221 decoded frames (its Task 16).
- P2 (plan 2). `scry.annotate.run_annotate(run, cfg, provider=None)`; `[annotate]` keys `mode` (`"every_frame"`,
  `"off"`, `"incremental"`), `transcribe`, `scale`, `arm` (`"A"`–`"D"`), `pane`; with `mode = "off"` the stage writes
  no file and a manifest entry with zero usage. `Run.load_annotations() -> list[Annotation]` (`frame`, `targets`,
  `unassigned`, `repairs`, `usage` of that one call, `error`). `Run.load_labels() -> Labels | None`; `Labels.box(ref) ->
  BoxLabel | None` (`container`, `container_ref`); `Labels.frame(frame) -> FrameLabel` (`containers`, `links` with ids
  as box refs of that frame); `Labels.lifetime(id) -> LifetimeLabel | None` (`vlm`, the model's majority reading).
  Manifest `stages.annotate`: `usage` (four keys), `model`, `cache`, `calls`.
- P3 (plan 3). `scry.interpret.run_interpret`, `scry.summarize.run_summarize`, `scry.index.build_index`, each callable
  as `(run, cfg)`. `Interpretation` with `id`, `entered_text`, `submitted`, `citations`, `invalid_citations`, per-record
  `usage`, `model`, `error`; `Run.load_interpretations() -> dict[str, Interpretation]`. **`entered_text` is the text the
  user has entered "as it stands in Frame b"**, so on the transition where Enter was pressed it is the whole command
  (its Task 5 prompt and example); the submission metric and *false run* depend on exactly this reading. `scry.costs`:
  `USAGE_KEYS`, `CACHE_WRITE_MULTIPLIER = 1.25`, `BATCH_MULTIPLIER = 0.5`, `add_usage(total, usage)`,
  `estimate_cost(usage, model, batch=False)`, `run_costs(manifest)` (`stages.<name>.cost_usd` and `cost_usd_batch`,
  `total_usd`, `frames`, `per_frame_usd`). `scry.groundtruth`: `score_found(entries, db, cfg.index)` (rows `n, text,
  scorable, found, rank, level, node_id`; the entry's time is `[first_t, submitted_t]`; a hit covers it when the two
  closed intervals intersect), `found_rate`, `score_submitted(entries, changes, interps)` (rows `n, text, matched,
  submit_frame_error, submit_t_error`), `score_false_run(never_run, changes, interps)` (rows `text, false_run,
  transitions`). `scry.index.open_db`, `search`. `scry.ask.ask(run, cfg, question, client=None) -> AskResult` with
  `answer`, `turns`, `tool_calls: list[str]`, `usage` (four keys, summed over turns), `cost_usd`, `stop`; no call
  cache, a fresh conversation per call. `[interpret] images` (`"scaled"`, `"crops"`, `"full"`). Test helpers
  `tests/minirun.py` (`mini_run(tmp_path, labels=False)`, `mini_interpretations(run)`; its Fixture M) and
  `tests/fakes.py`.

**Needed by this plan and pinned by no sibling plan** (for the synthesis pass):
- N1. **`AskResult` carries no structured citations.** Plan 3's prompt asks for "a frame number and a time for every
  factual claim" in prose. The harness therefore reads frames, box refs, transition ids and times out of the answer
  text (Task 6 rules 11–12); that is a heuristic, and it feeds guards only. A `citations: list[str]` field on
  `AskResult` would make it exact.
- N2. **No config key selects an `ask` prompt variant.** P5's "agent prompt wording on the negative questions" cannot
  be a matrix axis until one exists (say `[ask] prompt`). No `p5-ask.toml` is committed; `evals/README.md` gives the
  recipe (upstream fixed to P1's runs, stages `["ask"]`, one axis over the new key).
- N3. **`estimate_cost` prices an unknown model as `claude-opus-5` without saying so.** The harness adds a warning to
  the scorecard (Task 1 rule 3). The reviewers may prefer an error in `scry.costs`.
- N4. **Two findings about plan 3's Task 16, handled here without a second definition.** `score_submitted` matches by
  containment, so for the one-letter answers `Y` and `y` any claim containing the letter would do; the harness accepts
  such a match only on equality (Task 4 rule 9). `score_false_run` has only a frame condition, so a true submission of
  executed row 6 that `interpret` marks one transition late (on 177→178) is also counted as a false run of never-run
  row 4, which lists frame 178; the harness keeps plan 3's score and flags the shared claim beside it (Task 4 rule 10).
- N5. `Change.t[0]`: plan 1 writes `a.t_end`, plan 3's A2 assumes the from-frame's `t_settled`. This plan reads only
  `t[1]`, the to-frame's `t_settled`, which both agree on and which is the ground truth's time base.
- N6. Stage wall time: plan 3's `scry run` writes `seconds` into the manifest; the harness calls the stage functions
  directly and times them itself (`evalrun.json`).
- N7. Whether a stage's manifest `usage` counts cache hits (plan 2's D23 says it does: "what a cold run would pay") or
  only paid calls. In a cold run the two are equal; after a resume they are not, and Task 1 rule 4 takes the larger of
  the manifest's figure and the private call cache's, whichever convention a stage follows.
- N8. The hold-out video's command list, if the owner writes one, uses the format of `span2-commands.md`, so plan 1's
  parser reads it unchanged.

---

### Task 1: Dollars and seconds per stage, per frame, per video

**Files:**
- Create: `src/scry/evaluation/__init__.py`, `src/scry/evaluation/accounting.py`, `tests/test_eval_accounting.py`

**Interfaces:**
- Consumes: `scry.costs.PRICES`, `estimate_cost`, `add_usage`, `run_costs` (P3: cache-creation tokens are priced
  there, at 1.25 × the input price, and the provider sums usage over its retries); the call-cache file format of
  `scry.providers.cache.CallCache` (`{"request": {"stage", "model", …}, "response": {"usage", …}}`).
- Produces:
  - `cache_usage(cache_dir: Path) -> dict[str, dict]`: per `request.stage` (`"unknown"` when absent)
    `{"usage": the four keys summed with add_usage, "model": str | None, "entries": int}`
  - `projection_frames(manifest: dict) -> int | None`
  - `run_cost(manifest: dict, stage_seconds: dict[str, float], cache: dict[str, dict], frames: int, projection: int |
    None, default_model: str) -> dict`

**Rules:**
1. `projection_frames`: the manifest's `subset.source` names the run the directory was derived from; return that
   run's `stages.decode.emitted` (falling back to `stages.stage1.emitted` for a pre-re-base source). No `subset` key →
   the manifest's own `stages.decode.emitted`. Nothing found → `None`.
2. `run_cost` starts from `run_costs(manifest)`. Result: `{"frames", "projection_frames", "dollars", "dollars_batch",
   "per_frame", "per_video", "seconds", "seconds_per_frame", "by_stage": {stage: {"dollars", "dollars_batch",
   "per_frame", "seconds", "calls", "model", "usage"}}, "sources": {"manifest", "call_cache"}, "cold": bool,
   "warnings": [str]}`. Every stage in the manifest or in `stage_seconds` has a `by_stage` row (`dollars` 0.0 without
   usage); `dollars` is that stage's `cost_usd`, `dollars_batch` its `cost_usd_batch`; `calls` is the entry's `calls`,
   else its `cache.misses`, else `None`. `frames` is the argument (the run directory's frame count), not the
   manifest's.
3. A stage whose `model` is not a key of `PRICES` gets the warning `no list price for <model>: priced as
   claude-opus-5` (`estimate_cost` falls back silently, N3).
4. **The run total is the larger of two sources.** `sources.manifest` is `run_costs`' `total_usd`;
   `sources.call_cache` is the sum over `cache` of `estimate_cost(usage, model or default_model)`. `dollars =
   max(both)`. When they differ by more than $0.0001 a warning says which is larger and by how much; `by_stage` stays
   the manifest's. (In a cold run every paid terminal call is exactly one entry of the run's private cache, so the
   cache sum survives a resume that a manifest may forget.)
5. `cold` is false, with a warning `"<n> cache hits in <stage>"`, when any stage entry has `cache.hits > 0`.
6. `per_frame = dollars / frames`; `per_video = per_frame × projection` (`None` without a projection); the projection
   is linear and every report says so. `seconds` sums `stage_seconds`. `frames == 0` gives `None` rates, no exception.
7. The cost of the question set and of the judge is not part of `run_cost`: Tasks 6 and 7 record it per question.

**Tests to write first:**
- `test_run_cost_per_stage_frame_and_video`: manifest stages `read` (no usage), `annotate` (`usage` input 100_000,
  output 20_000, cache creation 8_000, cache read 0; `model "claude-opus-5"`; `calls 10`; `cache {"hits": 0, "misses":
  10}`), `interpret` (input 30_000, output 4_000; same model; `cache {"hits": 0, "misses": 9}`); `stage_seconds {"read":
  50.0, "annotate": 120.0, "interpret": 30.0}`; a cache holding one entry per model stage with the same usage; `frames
  10`, `projection 200` → `by_stage.annotate.dollars 1.05` (0.5 + 0.5 + 0.05), `by_stage.annotate.dollars_batch 0.525`,
  `by_stage.annotate.per_frame 0.105`, `by_stage.annotate.calls 10`, `by_stage.interpret.dollars 0.25`,
  `by_stage.interpret.calls 9`, `by_stage.read.dollars 0.0`, `dollars 1.3`, `dollars_batch 0.65`, `per_frame 0.13`,
  `per_video 26.0`, `seconds 200.0`, `seconds_per_frame 20.0`, `sources {"manifest": 1.3, "call_cache": 1.3}`, `cold
  True`, `warnings []`.
- `test_resumed_run_costs_come_from_the_call_cache`: the same, plus a third cache entry (stage `annotate`, input
  10_000) → `sources.call_cache 1.35`, `dollars 1.35`, `per_frame 0.135`, `per_video 27.0`, one warning containing
  `call cache` and `0.05`; `by_stage.annotate.dollars` still `1.05`.
- `test_cache_hits_break_cold`: `interpret`'s `cache` is `{"hits": 3, "misses": 6}` → `cold False`, a warning
  containing `3 cache hits in interpret`.
- `test_unknown_model_is_flagged`: `annotate`'s `model` is `"claude-nope"` → a warning containing `claude-nope` and
  `priced as claude-opus-5`.
- `test_cache_usage_groups_by_stage`: three files written with `CallCache.put` (stages `annotate`, `annotate`, and a
  request without `stage`) → keys `annotate` (`entries 2`, usage summed) and `unknown` (`entries 1`).
- `test_projection_frames`: a source manifest with `stages.decode.emitted = 4` and a derived manifest with `subset =
  {"source": <that directory>, "frames": [1, 2]}` → `4`; a source with only `stages.stage1.emitted = 7` → `7`; neither
  → `None`.
- `test_zero_frames_does_not_divide`: `frames 0` → `per_frame None`, `per_video None`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_accounting.py -q`. Expected: FAIL (`No module
  named 'scry.evaluation'`).
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): dollars and seconds per stage, frame and video; manifest checked against the call cache`

### Task 2: The run matrix

**Files:**
- Create: `src/scry/evaluation/matrix.py`, `tests/test_eval_matrix.py`

**Interfaces:**
- Consumes: `scry.config.Config`, `load_config`; `scry.subset.parse_frames`.
- Produces:
  - `MODEL_STAGES = ("annotate", "interpret", "summarize", "ask")`
  - `@dataclass(frozen=True) Span`: `name: str`, `frames: tuple[int, int]`, `ground_truth: Path | None`, `questions: Path
    | None`, `popup_frames: tuple[int, ...]`
  - `@dataclass(frozen=True) RunSpec`: `phase: str`, `name: str`, `config_id: str`, `span: Span`, `values: dict[str,
    str]` (axis → value name, axis order), `repeat: int`, `overrides: dict[str, object]`, `stages: tuple[str, ...]`
    (effective, after skips), `judged: bool`, `fixed_from: Path | None`
  - `@dataclass Matrix`: `phase`, `path: Path`, `source: Path`, `base_config: Path`, `stages: tuple[str, ...]`,
    `repeats: int`, `spans: dict[str, Span]`, `axes: dict[str, dict[str, dict]]`, `exclude: list[dict]`, `fixed_from: str
    | None`, `compare: list[dict]`, `floor: Path | None`, `floor_match: tuple[str, ...]`, `judge: dict`, `reference:
    dict | None`
  - `load_matrix(path: Path) -> Matrix`; `expand(m: Matrix) -> list[RunSpec]`; `apply_overrides(base: dict, overrides:
    dict[str, object]) -> dict`; `config_for(m: Matrix, spec: RunSpec) -> Config`

**The file format** (`evals/<phase>.toml`; everything specific to a video or a phase lives here):

```toml
# An illustration of every key; no real phase uses all of them at once.
phase = "px"                       # letters, digits, _ and . ; run directories go under runs/eval/<phase>/
source = "runs/p0"                 # a run directory with decode's frames; never written
base_config = "scry.toml"          # optional, this is the default
stages = ["read", "track", "annotate", "interpret", "summarize", "index", "ask"]
repeats = 3
fixed_from = "runs/eval/p1/{span}-grouponly-r{repeat}"   # optional: hold the upstream fixed (Task 3 rule 6)
floor = "docs/results/p1/noise.json"                     # optional: an earlier phase's noise floor (Task 12)
floor_match = ["base"]                                   # optional, this is the default

[spans.span2]
frames = "155-187"
ground_truth = "docs/ground-truth/span2-commands.md"     # optional: command metrics are scored on this span
questions = "docs/ground-truth/span2-questions.md"       # optional: "ask" runs on this span
popup_frames = []                                        # optional: frames on which the popup guard looks

[axis.base.transcribing]           # [axis.<axis>.<value>]: dotted config keys, quoted, and the reserved key skip_stages
"annotate.transcribe" = true
[axis.base.none]
skip_stages = ["annotate"]

[[exclude]]                        # optional: drop combinations; a value or a list of values per axis, or `span`
base = "none"
[[compare]]                        # optional: comparisons the report makes, per span (Task 12)
a = { base = "transcribing" }
b = { base = "none" }
[judge]                            # optional (Task 7)
effort = "low"
[reference]                        # optional: one fixed row shown beside the cost table (Task 13)
label = "runs/span2-before (pre-re-base pipeline, cold)"
frames = 33
model = "claude-opus-5"
[reference.usage]
input_tokens = 272050
```

**Rules:**
1. Unknown top-level keys, unknown span keys and a missing `phase`, `source`, `stages`, `repeats` or `spans` raise
   `ValueError` naming the key. `repeats ≥ 1`. Paths are kept as written (relative to the working directory).
2. `phase`, span names, axis names and value names match `^[A-Za-z0-9_.]+$` (no hyphen: the hyphen separates the parts
   of a run name); otherwise `ValueError` naming the offender.
3. Expansion order: spans in file order × the cartesian product of the axes in file order, values in file order ×
   repeats `1..repeats`. `config_id = "-".join([span, *values])`; `name = config_id + f"-r{repeat}"`. With no axes the
   config id is the span name.
4. `overrides` is the union of the chosen values' tables without `skip_stages`; a key set by two axes raises
   `ValueError` naming the key and both axes. Effective `stages` = the matrix's stages minus every chosen value's
   `skip_stages`, minus `"ask"` on a span without `questions`. A stage name outside `read, track, annotate, interpret,
   summarize, index, ask` raises.
5. `judged` = any effective stage is in `MODEL_STAGES`. A matrix with no judged run is deterministic and may use
   `repeats = 1`.
6. `[[exclude]]`: a combination is dropped when, for some exclude table, every key matches (`span` matches the span
   name; an axis key matches a value name or any member of a list). A key that is neither `span` nor an axis raises.
7. Two values of one axis with equal tables (overrides and `skip_stages`) raise `ValueError("… are the same
   configuration")`: a copy-paste slip would otherwise be measured as a difference that is pure noise.
8. `apply_overrides` deep-copies `base` and sets each dotted path; a path that runs through a non-table raises
   `ValueError`. `config_for` loads `base_config` with `tomllib`, applies the overrides and returns
   `Config.model_validate(...)`; an unknown key therefore raises pydantic's `ValidationError` at expansion time.
   The harness never names a pipeline config key in code.
9. `fixed_from` may contain `{span}` and `{repeat}`; it is formatted per spec. `compare`, `floor`, `floor_match`
   (default `("base",)`), `judge` and `reference` are carried as written for Tasks 7, 12 and 13.

**Tests to write first** (the matrix text is written to `tmp_path`; the config keys used exist after plan 1):

```toml
phase = "p9"
source = "SRC"
stages = ["read", "track", "annotate", "ask"]
repeats = 2
[spans.smoke]
frames = "1-2"
popup_frames = [2]
[spans.span2]
frames = "2-3"
ground_truth = "gt.md"
questions = "q.md"
[axis.base.transcribing]
"model.max_tokens" = 16000
[axis.base.grouponly]
"model.max_tokens" = 8000
[axis.base.none]
skip_stages = ["annotate"]
[axis.scale.s100]
"overlay.scale" = 1.0
[axis.scale.s050]
"overlay.scale" = 0.5
[[exclude]]
base = "none"
scale = "s050"
```

- `test_expand_order_names_and_flags`: 20 specs. `names[:3] == ["smoke-transcribing-s100-r1",
  "smoke-transcribing-s100-r2", "smoke-transcribing-s050-r1"]`; `names[-1] == "span2-none-s100-r2"`; no name contains
  `none-s050`. `smoke-transcribing-s100-r1`: `config_id "smoke-transcribing-s100"`, `stages ("read", "track",
  "annotate")` (no questions on `smoke`), `judged True`, `overrides {"model.max_tokens": 16000, "overlay.scale": 1.0}`,
  `span.frames (1, 2)`, `span.popup_frames (2,)`. `smoke-none-s100-r1`: `stages ("read", "track")`, `judged False`.
  `span2-none-s100-r1`: `stages ("read", "track", "ask")`, `judged True`.
- `test_config_for_applies_overrides_and_rejects_unknown_keys`: overrides `{"track.margin": 0.25, "overlay.scale":
  0.5}` → `cfg.track.margin == 0.25`, `cfg.overlay.scale == 0.5`, every other value the base's. `{"track.margn": 1}` →
  `pydantic.ValidationError`. `{"track.margin.x": 1}` → `ValueError`.
- `test_bad_names_and_bad_excludes`: a value named `group-only` → `ValueError` containing `group-only`; an exclude
  table with the key `colour` → `ValueError` containing `colour`; `stages = ["read", "perceive"]` → `ValueError`
  containing `perceive`; a top-level key `repeat = 3` → `ValueError` containing `repeat`.
- `test_duplicate_axis_values_rejected`: `[axis.scale.s100]` and `[axis.scale.full]` both `"overlay.scale" = 1.0` →
  `ValueError` containing `s100`, `full` and `same configuration`.
- `test_two_axes_setting_one_key_is_an_error`: `base.transcribing` also sets `"overlay.scale" = 1.0` → `ValueError`
  containing `overlay.scale`.
- `test_fixed_from_template`: `fixed_from = "runs/eval/p1/{span}-grouponly-r{repeat}"` → the spec
  `span2-…-r2` has `fixed_from == Path("runs/eval/p1/span2-grouponly-r2")`.
- `test_deterministic_matrix`: `stages = ["read", "track"]`, `repeats = 1` → no spec is `judged`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_matrix.py -q`. Expected: FAIL (`No module named
  'scry.evaluation.matrix'`).
- [ ] **Step 2:** Implement rules 1–9.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): run matrix: spans × axes × repeats, config overlays validated at expansion`

### Task 3: The runner: cold run directories, stages in-process, timing, resume

**Files:**
- Create: `src/scry/evaluation/runner.py`, `tests/test_eval_runner.py`

**Interfaces:**
- Consumes: `Matrix`, `RunSpec`, `config_for` (Task 2); `make_subset`, `Run` (P1); the stage entry points of P1, P2
  and P3; `run_questions` (Task 6) for the pseudo-stage `ask`, imported lazily.
- Produces:
  - `STAGE_FUNCS: dict[str, str]` = `{"read": "scry.read:run_read", "track": "scry.track.stage:run_track", "annotate":
    "scry.annotate:run_annotate", "interpret": "scry.interpret:run_interpret", "summarize":
    "scry.summarize:run_summarize", "index": "scry.index:build_index"}`; `resolve(stage: str) -> Callable[[Run, Config],
    None]` imports the named function when first asked (tests replace `resolve` or pass `stage_funcs`)
  - `STAGE_OUTPUTS: dict[str, tuple[str, ...]]` = `read: boxes.jsonl`; `track: changes.jsonl, lifetimes.jsonl`;
    `annotate: annotations.jsonl`; `interpret: interpretations.jsonl`; `summarize: steps.jsonl, sections.jsonl,
    video.json`; `index: index.sqlite` (spec §2's table)
  - `metric_code_hash(package_dir: Path) -> str`; `code_identity(repo: Path) -> dict` with `git_commit: str | None`,
    `git_dirty: list[str]`, `metric_code_hash: str`
  - `@dataclass RunOutcome`: `name`, `status: Literal["done", "failed", "skipped"]`, `seconds: dict[str, float]`,
    `error: str | None`
  - `materialise(m: Matrix, spec: RunSpec, root: Path, identity: dict) -> Run`
  - `execute(m: Matrix, spec: RunSpec, root: Path, identity: dict, stage_funcs: dict[str, Callable] | None = None,
    clock: Callable[[], float] = time.perf_counter) -> RunOutcome`
  - `run_matrix(m: Matrix, root: Path, only: str | None = None, allow_dirty: bool = False, stage_funcs=None,
    clock=…, identity: dict | None = None) -> list[RunOutcome]`
  - the file `evalrun.json` in each run directory: `{"phase", "name", "config_id", "span": {"name", "frames",
    "ground_truth", "questions", "popup_frames"}, "values", "repeat", "overrides", "stages", "judged", "fixed_from",
    "matrix": str, "spec_hash", "code": {…identity…}, "started", "finished", "status": "new" | "running" | "done" |
    "failed", "resumed": bool, "stage_status": {stage: {"status": "done" | "failed", "seconds"}}, "error"}`; and
    `config.json` = `config_for(...).model_dump()`

**Rules:**
1. The run directory is `root / spec.phase / spec.name`. A fresh one is made by `make_subset(m.source, dir,
   spec.span.frames, share_cache=False)`; then `evalrun.json` (`status "new"`) and `config.json` are written.
   `spec_hash = sha256_obj` of the spec's name, span, overrides, stages and `fixed_from`. An existing directory whose
   `evalrun.json` has the same `spec_hash` is reused; a different hash raises `ValueError` (the matrix changed under a
   finished run: choose a new phase name or delete the directory).
2. **Cold.** Before any stage runs, `run.cache_dir` must be a real directory (`is_symlink()` false) and, when no stage
   has started, empty; otherwise `RuntimeError("a run that judges a model call must not share a call cache")`. Nothing
   in the harness ever passes `share_cache=True` or writes into another run's cache.
3. **Committed code first.** `run_matrix` computes `code_identity` once. When the matrix has a judged run and
   `git_dirty` lists anything under `src/scry`, `evals` or `docs/ground-truth`, it raises `RuntimeError` naming the
   paths, unless `allow_dirty`. `metric_code_hash` is the SHA-256 over the sorted relative paths and bytes of every
   `*.py` under `src/scry/evaluation/` and of `src/scry/groundtruth.py`, `metrics.py` and `costs.py`. Both are stored
   in `evalrun.json` when the run starts; Task 10 compares them with the code that scores. `git` missing → `git_commit
   None`, `git_dirty []`.
4. `execute` runs the effective stages in order with the run's `Config`, timing each with `clock` (rounded to 0.1 s)
   and rewriting `evalrun.json` atomically after each stage. The pseudo-stage `ask` calls `run_questions(run, cfg,
   spec.span.questions)`. An exception stops this run: `status "failed"`, `error = "<Type>: <message>"[:500]`, later
   stages not run. `run_matrix` goes on to the next run and returns every outcome; it runs sequentially, never in
   parallel (wall times stay comparable and rate limits stay out of the measurements).
5. **Resume.** `status "done"` → outcome `skipped`. `"failed"` or `"running"` → restart at the first stage whose
   `stage_status` is not `done`, set `resumed true` (Task 1 rule 4 then keeps the cost honest).
6. **A fixed upstream** (`spec.fixed_from`): the named run must be `done` and hold exactly the same frames
   (`frames.jsonl` frame numbers equal), else `ValueError`. After `make_subset`, copy from it the `STAGE_OUTPUTS` of
   every stage that is *not* in the spec's effective stages and exists there, together with those stages' manifest
   entries. Stages that do run, run cold in the new directory's own empty cache. `evalrun.json` records `fixed_from`, and
   every report says that differences upstream of the first stage run were not sampled. `{repeat}` in the template
   gives each repeat a different upstream sample.
7. `only` restricts `run_matrix` to the spec with that name.

**Tests to write first** (a helper builds a source run under `tmp_path / "src"` as `tests/test_subset.py` does after
plan 1: `frames.jsonl` with `Frame`s 0–3, four 8×8 PNGs, a manifest with `video_id` and `stages.decode`, and one file
`cache/k.json`; fake stage functions append their name to a list and write their `STAGE_OUTPUTS` files; a fake clock
advances 1.5 s per stage call; `identity = {"git_commit": "abc", "git_dirty": [], "metric_code_hash": "h"}`):
- `test_materialise_is_cold`: matrix `p9`, span `smoke` `1-2`, no axes → directory `root/p9/smoke-r1`; its `cache` is a
  directory, not a symlink, and empty; `frames/00001.png` and `00002.png` exist and `00000.png` does not;
  `evalrun.json` has `name "smoke-r1"`, `status "new"`, `code.git_commit "abc"`; `config.json` exists; the listing of
  `src` is unchanged.
- `test_execute_runs_stages_in_order_and_times_them`: stages `read, track` → calls `["read", "track"]`; outcome
  `status "done"`, `seconds {"read": 1.5, "track": 1.5}`; `evalrun.json` `status "done"`, `stage_status.track.seconds
  1.5`, `finished` set.
- `test_failed_stage_stops_the_run_not_the_matrix`: two repeats; the fake `track` raises `ValueError("boom")` on its
  first call only → outcomes `[("smoke-r1", "failed"), ("smoke-r2", "done")]`; the first has `error "ValueError: boom"`
  and `seconds {"read": 1.5}`.
- `test_resume_skips_done_and_restarts_failed`: run the matrix again with a `track` that succeeds → the call list of
  the second pass is `["track"]` (no second `read`); outcomes `[("smoke-r1", "done"), ("smoke-r2", "skipped")]`;
  `smoke-r1/evalrun.json` has `resumed true`.
- `test_shared_cache_is_refused`: replace a materialised run's `cache` directory with a symlink to the source's →
  `execute` raises `RuntimeError` containing `share a call cache`.
- `test_changed_spec_is_refused`: materialise, then expand the same matrix with an added override → `ValueError`.
- `test_dirty_tree_is_refused_for_judged_runs`: `identity["git_dirty"] = ["src/scry/evaluation/commands.py"]` and a
  matrix with `annotate` → `RuntimeError` containing that path; with `allow_dirty=True` it runs; a matrix with only
  `read, track` runs either way; `git_dirty = ["README.md"]` runs.
- `test_metric_code_hash`: a directory with `a.py` and `b.py` → a 64-character hex string; the same after re-creating
  the files in the other order; different after changing one byte of `b.py`; different after renaming `b.py`.
- `test_fixed_from_copies_the_upstream_and_runs_the_rest_cold`: a finished run `root/p1/smoke-r1` holding
  `boxes.jsonl`, `changes.jsonl`, `lifetimes.jsonl`, `annotations.jsonl` and manifest entries for `read`, `track`,
  `annotate`; a matrix with `fixed_from = "<root>/p1/{span}-r{repeat}"` and `stages = ["interpret", "index"]` → the new
  directory holds byte-equal copies of the four files and the three manifest entries, the fake `interpret` and `index`
  ran, no fake `read`, and the new `cache` is empty and not a symlink. A fixed run with other frames (`2-3`) →
  `ValueError` containing `same frames`. A fixed run whose status is `failed` → `ValueError`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_runner.py -q`. Expected: FAIL (`No module named
  'scry.evaluation.runner'`).
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): runner: cold run directories from subset, in-process stages, timing, resume, fixed upstream`

### Task 4: Command metrics: one row per entry from the siblings' scorers, exactness per reader, per-unit values

**Files:**
- Create: `src/scry/evaluation/commands.py`, `src/scry/evaluation/adapters.py`, `tests/test_eval_commands.py`

**Interfaces:**
- Consumes: `Entry`, `parse_commands`, `scorable`, `score_exact` (P1); `score_found`, `found_rate`, `score_submitted`,
  `score_false_run`, `Interpretation`, `Run.load_interpretations`, `open_db` (P3); `Run.load_labels`,
  `Labels.lifetime` (P2); `scry.textdiff.norm`; `rapidfuzz.fuzz.partial_ratio`.
- Produces, in `adapters.py` (each a few lines over the sibling plans' loaders; the rest of the package reaches the
  siblings' loaders only through this module):
  - `lifetimes(run) -> list[Lifetime]`; `changes(run) -> list[Change]`; `interpretations(run) -> dict[str,
    Interpretation]` (`{}` when the file is absent)
  - `vlm_majority(run) -> dict[str, str]`: lifetime id → `Labels.lifetime(id).vlm` where it is not `None`; `{}`
    without labels or without transcription
  - `index_db(run) -> sqlite3.Connection | None` (`None` when `index.sqlite` is absent)
- Produces, in `commands.py`:
  - `contains(text: str, reading: str) -> bool` = `norm(text) in norm(reading)` (plan 1 Task 14 rule 6, restated once)
  - `window(e: Entry) -> tuple[float, float] | None` (plan 3's interval: `(first_t, submitted_t)`, one standing in
    for a missing other)
  - `reader_views(lifetimes: list[Lifetime], vlm: dict[str, str]) -> dict[str, list[Lifetime]]`
  - `score_exact_by_reader(entries, views) -> list[dict]`
  - `guard_submissions(entries, submit_rows, interps) -> list[dict]`; `flag_shared_claims(false_rows, submit_rows) ->
    list[dict]`; `submission_notes(entries, changes, interps, submit_rows, false_rows) -> dict`
  - `command_scores(executed, never_run, lifetimes, vlm, found_rows, submit_rows, false_rows, changes, interps) ->
    dict` (pure assembly; any of the three row lists may be `None`)
  - `score_commands(run, cfg, ground_truth: Path, adapters) -> dict | None` (parses the file, calls the siblings'
    scorers through the adapters, then `command_scores`)

**Rules — found (primary).** 1. `found_rows = score_found(executed, db, cfg.index)` when the index exists, else `None`.
The query, the entry's time and "covering" are plan 3's (its Task 16 rule 1: the quoted command through the lexical
search the agent's tool uses, no embedder; a hit covers the entry when `[hit.t[0], hit.t[1]]` intersects `[first_t,
submitted_t]`). This plan adds nothing to the definition; the rank and level in each row show a coarse find.

**Rules — exact, per reader (primary; spec §9: "some lifetime's majority reading contains it exactly, per reader"):**
2. `reader_views`: `"ocr"` is the lifetimes as loaded. `"vlm"`, present only when `vlm` is non-empty, holds for every
   lifetime id in `vlm` a copy with `text` replaced by the model's majority reading (`model_copy(update=…)`).
3. For each view call plan 1's `score_exact(executed, view)`; merge by `n` into `{"n", "text", "scorable", "exact":
   {"ocr": bool, "vlm": bool, "any": bool}, "lifetime": {reader: id | None}, "first_t_error": {reader: float | None},
   "first_frame_error": {reader: int | None}, "in_window": {reader: bool}, "variant_only": bool, "nearest": dict |
   None}`. `any` is true when any reader is; the `vlm` keys are absent without a second reader. `exact_rate[reader]`
   counts scorable executed entries, as plan 1's `exact_rate` does. `exact.any` is the score that compares bases with
   different readers.
4. `in_window[reader]`: the entry is exact for that reader and the lifetime plan 1 reports (its earliest match)
   intersects the entry's window: `lifetime.first.t ≤ window[1]` and `lifetime.last.t ≥ window[0]`; `in_window["any"]`
   is true when any reader's is. It is a companion, not the score: the score follows the spec's words, and the report
   flags every entry where `exact` holds and `in_window` does not (a later sighting of the same string stood in for
   the executed one).
5. `variant_only` (OCR reader): not `exact.ocr`, but `contains(text, r)` for some key `r` of some lifetime's
   `readings`: the right string was read and outvoted. `nearest`, for an entry exact under no reader: the OCR lifetime
   maximising `partial_ratio(norm(text), norm(lifetime.text))`, ties to the smaller `first.frame` then the smaller id
   number, as `{"lifetime", "text", "score": round(ratio / 100, 3)}`: what was recorded instead.

**Rules — time error of first appearance (secondary):**
6. Per reader, plan 1's `t_error` and `frame_error` (signed, positive = the record starts late).
   `first_t_error["any"]` is the value with the smallest absolute among the readers that are exact.
7. Aggregate per reader and for `any`: `first_t_error_abs_mean = round(mean(|t_error|), 2)` over scorable entries that
   have a value, with their count.

**Rules — submission and false run (secondary; plan 3's scorers, which read `submitted` and nothing else):**
8. `submit_rows = score_submitted(executed, changes, interps)` and `false_rows = score_false_run(never_run, changes,
   interps)`; both `None` when there are no interpretations.
9. **One-letter answers need equality** (`guard_submissions`, N4): for an entry that is not `scorable`, a `matched`
   change is kept only when `norm(interps[matched].entered_text) == entry.text`; otherwise the row becomes unmatched
   (`matched None`, errors `None`) and `rejected_loose_match` holds the change id. Scorable entries pass through.
10. **Shared claims are flagged, not rescored** (`flag_shared_claims`, N4): each false-run row gains `shared_claim`, the
    list of its transitions that are also the `matched` change of an executed entry (after rule 9), as
    `{"transition", "executed": n}`. `false_run` stays plan 3's value; the report prints the flag beside it.
11. `submission_notes` → `{"unmatched_submits": [{"transition", "entered_text"}], "unclear": int}`: the changes whose
    interpretation says `submitted == "yes"` with a non-blank `entered_text` and that are neither an executed row's
    `matched` nor among a false-run row's `transitions`; and the number of changes whose `to_frame` is some entry's
    `submitted_frame` and whose interpretation says `unclear`. Information only.
12. `submit_marked_rate = (rows with a match, executed entries with a submitted_t)` (the one-letter answers count
    here); `submit_t_error_abs_mean` over matched rows; `false_run = (rows with false_run, never-run entries)`.

**Rules — assembly:**
13. `command_scores` returns `{"entries": [merged rows: plan 3's found keys, rule 3's keys, plan 3's submission keys
    with `submit_marked`], "never_run": [...], "rates": {"found", "exact": {reader: (k, n)}, "in_window": {reader: (k,
    n)}, "submit_marked", "false_run"}, "first_t_error_abs_mean", "submit_t_error_abs_mean", "unmatched_submits",
    "unclear", "units": {...}}`. `units` maps metric name → unit → value: `found`, `exact.ocr`, `exact.vlm`,
    `exact.any`, `exact_in_window.any` (unit = the entry's `n` as a string; scorable entries; 1.0 or 0.0; `found` only
    where it is not `None`), `first_t_error_abs.any`, `submit_t_error_abs` (entries that have a value),
    `submit_marked` (every executed entry with a `submitted_t`), `false_run` (unit `"N<i>"`, the never-run row's
    1-based position). A `None` row list leaves its rates `None` and its metrics out of `units`.
14. Nothing here reads `sightings`, `last − first` or any other duration as evidence that a command ran.

**Tests to write first.** Shared fixture, built as objects (not parsed): executed `E1` `n 1` `"az account show"` first
`(157, 628.77)` submitted `(158, 629.57)`; `E2` `n 2` `"az configure --defaults group=RG1"` first `(161, 649.17)`
submitted `(164, 653.57)`; `E3` `n 3` `"y"` first `(170, 660.83)` submitted `(171, 664.13)`; `E4` `n 4` `"kubectl config
current-context"` first `(175, 674.23)` submitted `(177, 677.13)`. Never run: `N1` `"az login"` frames `[155]`; `N2`
`"kubectl config current-context"` frames `[178]`.
- `test_exact_by_reader_and_window`: lifetimes `L1` `"PS C:\Users\msadmin> az account show"` first `(157, 628.77)`
  last `(186, 716.9)`; `L2` text `"PS C:\Users\msadmin>azconfigure --defaultsgroup=RG1"`, readings `{that text: [161,
  163], "PS C:\Users\msadmin> az configure --defaults group=RG1": [162]}`, first `(161, 649.17)` last `(163, 653.57)`; `L3`
  `"PS C:\Users\msadmin> kubectl config current-context"` first `(178, 698.07)` last `(178, 699.7)`; `L4`
  `"PS C:\Users\msadmin> kubect1 config current-context"` first `(175, 674.23)` last `(177, 698.07)`. `vlm = {"L2":
  "PS C:\Users\msadmin> az configure --defaults group=RG1", "L4": "PS C:\Users\msadmin> kubectl config
  current-context"}`. Expected. E1: `exact {"ocr": True, "vlm": False, "any": True}`, `first_t_error.ocr 0.0`,
  `in_window.ocr True`. E2: `exact {"ocr": False, "vlm": True, "any": True}`, `variant_only True`,
  `first_t_error.vlm 0.0`, `first_t_error.any 0.0`. E4: `exact.ocr True` through `L3` with `first_t_error.ocr 23.84`,
  `first_frame_error.ocr 3`, `in_window.ocr False`; `exact.vlm True` through `L4` with `first_t_error.vlm 0.0`,
  `in_window.vlm True`; `first_t_error.any 0.0`; `in_window.any True`. Rates: `exact {"ocr": (2, 3), "vlm": (2, 3),
  "any": (3, 3)}`, `in_window {"ocr": (1, 3), "vlm": (2, 3), "any": (3, 3)}`. With `vlm = {}` no row has a `vlm` key and
  `any` equals `ocr`.
- `test_nearest_names_what_was_recorded_instead`: only `L2` and `L1`, no `vlm` → E2 `exact.any False`,
  `nearest.lifetime "L2"`, `nearest.text` the misread line, `0 < nearest.score ≤ 1`.
- `test_one_letter_answers_need_equality`: a submit row for E3 `{"n": 3, "text": "y", "matched": "T40",
  "submit_frame_error": 15, "submit_t_error": 52.77}` with `T40`'s `entered_text "kubectl get deployment"` → after the
  guard `matched None`, both errors `None`, `rejected_loose_match "T40"`; the same row matched to `T16` whose
  `entered_text` is `"y"` is kept unchanged; a scorable entry's row is never touched.
- `test_shared_claim_is_flagged`: submit rows with E4 matched to `T23`; false rows `N1 {"false_run": True,
  "transitions": ["T1"]}` and `N2 {"false_run": True, "transitions": ["T23", "T24"]}` → `N1.shared_claim == []`,
  `N2.shared_claim == [{"transition": "T23", "executed": 4}]`; both still `false_run True`.
- `test_submission_notes`: changes `T1 155→156`, `T3 157→158`, `T9 163→164`, `T16 170→171`, `T23 177→178`, `T24
  178→179`, `T30 180→181`; interpretations `T1 ("az login", "yes")`, `T3 ("az account show", "yes")`, `T9 ("az
  configure --defaults group=RG1", "unclear")`, `T16 ("y", "yes")`, `T23` and `T24 ("kubectl config current-context",
  "yes")`, `T30 ("clear", "yes")`; submit rows matched `T3`, `None`, `T16`, `T23`; false rows as in the test above →
  `unmatched_submits == [{"transition": "T30", "entered_text": "clear"}]`, `unclear 1`.
- `test_command_scores_assembles_rates_and_units`: found rows (plan 3's shape) E1 `found True, rank 1, level "video"`,
  E2 `found False`, E3 `found None`, E4 `found True, rank 2, level "lifetime"`; the exact fixture above; submit rows
  with errors `0.0`, `None`, `0.0`, `20.94`; the false rows above → `rates.found (2, 3)`, `rates.submit_marked (3, 4)`,
  `submit_t_error_abs_mean 6.98`, `rates.false_run (2, 2)`; `units["found"] == {"1": 1.0, "2": 0.0, "4": 1.0}`,
  `units["exact.any"] == {"1": 1.0, "2": 1.0, "4": 1.0}`, `units["submit_marked"] == {"1": 1.0, "2": 0.0, "3": 1.0,
  "4": 1.0}`, `units["submit_t_error_abs"] == {"1": 0.0, "3": 0.0, "4": 20.94}`, `units["false_run"] == {"N1": 1.0,
  "N2": 1.0}`. With `found_rows=None` and `submit_rows=false_rows=None` → `rates["found"] is None`,
  `rates["false_run"] is None`, and no `found`, `submit_marked` or `false_run` key in `units`.
- `test_score_commands_on_the_mini_run` (plan 3's Fixture M: `mini_run(tmp_path, labels=True)`,
  `mini_interpretations(run)`, `build_index(run, cfg)`; a ground-truth file in plan 1's format with the executed row
  `` `git status` ``, first `11, 24.40`, submitted `12, 26.40`, and the never-run row `` `git stash` `` frames `11
  (24.40)`) → the entry has `found True`, `rank 1`, `level "lifetime"`, `exact {"ocr": True, "vlm": True, "any":
  True}` (the model's readings of `L4` are `git st` once and `git status` twice), `first_t_error.any 0.0`,
  `in_window.any True`, `matched "T2"`, `submit_t_error 0.0`; `rates.false_run (0, 1)`. With `labels=False` the row has
  no `vlm` key. With no `index.sqlite` and no `interpretations.jsonl` the found and submission keys are `None`.
- `test_repo_ground_truth_parses_as_the_harness_expects` (reads `docs/ground-truth/span2-commands.md` through plan 1's
  parser): 9 executed, 5 never run; `[scorable(e) for e in executed] == [True, True, True, False, False, True, True,
  True, True]`; entry 2 text `az configure --defaults group=RG1-KodeKloud-AKS`, first `(161, 649.17)`, submitted `(164,
  653.57)`; entry 7 first `(180, 702.03)`, submitted `(180, 702.03)`; entry 9 submitted `(187, 721.0)`; never-run
  frames `[[155], [165], [172, 173, 174], [178], [179]]`; every executed entry has a window.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_commands.py -q`. Expected: FAIL (`No module named
  'scry.evaluation.commands'`).
- [ ] **Step 2:** Implement rules 1–14 and the adapters.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): command metrics per entry: exact per reader, guards on the submission scorers, per-unit values`

### Task 5: Guards: reported beside everything, never used to rank

**Files:**
- Create: `src/scry/evaluation/guards.py`, `tests/test_eval_guards.py`
- Modify: `src/scry/evaluation/adapters.py`

**Interfaces:**
- Consumes: `box_stability`, `touched_share_low_half`, `fragmentation` (P1); `Run.load_labels`, `Labels.box`,
  `Labels.frame`, `Run.load_annotations` (P2); `Interpretation` (P3).
- Produces, in `adapters.py`:
  - `@dataclass FrameLabels`: `frame: int`, `boxes: int`, `container_of: dict[str, str | None]` (box id → the
    `container_ref` in force after plan 2's join, `None` for a box with no container), `popups: int`, `called: bool`,
    `repairs: int`, `unassigned: int`, `error: str | None`
  - `frame_labels(run) -> list[FrameLabels] | None` (`None` when `Run.load_labels()` is `None`)
  - `annotation_usage(run) -> dict[int, dict]` (frame → the usage of the call made for it; frames without a call absent)
- Produces, in `guards.py`: `track_guards(changes, lifetimes) -> dict`; `label_guards(labels: list[FrameLabels],
  popup_frames: Sequence[int]) -> dict`; `citation_guards(interps: dict[str, Interpretation]) -> dict`;
  `guards(changes, lifetimes, labels, interps, popup_frames) -> dict`

**Rules:**
1. `track_guards`: `{"box_stability": box_stability(changes), "touched_share_low_half":
   touched_share_low_half(changes), "unstable_rate": round(f["unstable"] / f["lifetimes"], 4) or None when there are no
   lifetimes, "lifetimes_per_text": f["per_text"]}` with `f = fragmentation(lifetimes)`. "Touched share on near-static
   pairs" is plan 1's rank rule (the lower half of transitions by changed fraction): no cut-off is added here.
2. `label_guards`: `one_container_share = round(boxes with a container / boxes, 4)` over all frames (`None` with no
   boxes) and the same per frame for frames that have boxes; `zero` = boxes without one (plan 2's stored shape gives a
   box at most one container, so "exactly one" is "has one"); `repairs` and `unassigned` summed and per frame (frames
   with `called`); `calls`, `errors`; `popups_found = {str(frame): popups ≥ 1}` for each named popup frame present in
   the run and `popup_frames_missing` for the others.
3. `FrameLabels.popups` = the number of distinct `container_ref`s of kind `popup` among the frame's boxes, plus the
   popup containers of `Labels.frame(frame).containers` that no box of the frame is assigned to (a textless popup).
   Whether it is the *right* popup is judged by eye (Task 9); the guard counts presence.
4. `citation_guards`: `invalid_citations` summed and per change id; `interpret_errors`; `interpretations`.
5. `guards` returns `{"track": …, "labels": … | None, "citations": … | None, "units": {…}}` with `units` for
   `one_container_share`, `repairs`, `unassigned`, `popup_found` (unit = frame as a string), `invalid_citations` (unit =
   change id), and the run-level `box_stability`, `touched_share_low_half`, `unstable_rate` under the single unit
   `"run"`. `labels` is `None` for the no-annotation base, `citations` is `None` without interpretations.
6. Guards carry the role `guard` in the metric registry (Task 10); Task 12 compares them like anything else and its
   reading never consults them. Label consistency across frames is not computed at all.

**Tests to write first:**
- `test_label_guards`: `FrameLabels` for frame 149 (`boxes 10`; eight boxes with a container, `b9` and `b10` `None`;
  `popups 1`, `called True`, `repairs 2`, `unassigned 1`), frame 150 (`boxes 5`, all with a container, `popups 0`,
  `called True`, `repairs 0`, `unassigned 0`), frame 151 (`boxes 0`, `called False`); `popup_frames [149, 151, 160]` →
  `one_container_share 0.8667` (13 / 15), per frame `{"149": 0.8, "150": 1.0}`, `zero 2`, `repairs 2`, `unassigned 1`,
  `calls 2`, `popups_found {"149": True, "151": False}`, `popup_frames_missing [160]`.
- `test_track_guards_delegate_to_plan_1`: two changes with `unchanged` 98 and 50, `variants` 2 and 0, `flicker_lost`
  `["0:b9"]` and `[]`, `pixels` `(changed_fraction, touched_share)` `(0.001, 0.02)` and `(0.2, 0.5)`; three lifetimes,
  one `unstable`, texts `"a"`, `"a"`, `"b"` → `box_stability 0.9799`, `touched_share_low_half 0.02`, `unstable_rate
  0.3333`, `lifetimes_per_text 1.5`.
- `test_citation_guards`: interpretations `T1` (`invalid_citations 2`), `T2` (0), `T3` (`error "api: x"`) →
  `invalid_citations 2`, per change `{"T1": 2, "T2": 0}`, `interpret_errors 1`, `interpretations 3`.
- `test_guards_without_annotations_or_interpretations`: `labels=None`, `interps={}` → `labels None`, `citations None`,
  `units` holds only the three run-level track guards.
- `test_frame_labels_on_the_mini_run` (`mini_run(tmp_path, labels=True)`): four `FrameLabels` with `boxes` 3, 3, 5, 5,
  no `None` in any `container_of`, `popups 0`, `called True`, `repairs 0`, `unassigned 0`; `annotation_usage` has the
  keys 10, 11, 12, 13. With `labels=False` → `frame_labels(run) is None` and `annotation_usage(run) == {}`.
- `test_frame_labels_carry_along_a_lifetime` (records written as JSON lines in plan 2's shape, through
  `Run.load_labels()`): `boxes.jsonl` frame 1 `b1`, `b2`, frame 2 `b1`, `b2`, `b3`; `lifetimes.jsonl` `L1` boxes
  `["1:b1", "2:b1"]`, `L2` `["1:b2"]`, `L3` `["2:b2"]`, `L4` `["2:b3"]`; `annotations.jsonl` frame 1 `{"frame": 1,
  "targets": ["b1", "b2"], "containers": [{"id": "c1", "kind": "window", "app": "x", "name": "w"}, {"id": "c2", "kind":
  "popup", "app": "x", "name": "tip"}], "assign": [{"box": "b1", "container": "c1"}, {"box": "b2", "container":
  "c2"}], "unassigned": [], "repairs": 1, "model": "m", "prompt_version": "annotate-v1", "usage": {"input_tokens":
  100}}` and frame 2 `{"frame": 2, "targets": ["b2", "b3"], "containers": [{"id": "c1", "kind": "window", "app": "x",
  "name": "w"}], "assign": [{"box": "b3", "container": "c1"}], "unassigned": ["b2"], "repairs": 0, "model": "m",
  "prompt_version": "annotate-v1", "usage": {"input_tokens": 40}}` → frame 1: `boxes 2`, `container_of {"b1": "1:c1",
  "b2": "1:c2"}`, `popups 1`, `repairs 1`; frame 2: `container_of {"b1": "1:c1", "b2": None, "b3": "2:c1"}` (`b1`
  carried along `L1`), `popups 0`, `unassigned 1`; `annotation_usage == {1: {"input_tokens": 100}, 2: {"input_tokens":
  40}}`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_guards.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6; `frame_labels` is a thin layer over plan 2's `Labels`.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): guards: box stability, touched share, one-container share, repairs, unassigned, citations, popups`

### Task 6: The question set: parser, and the runner through `ask`

**Files:**
- Create: `src/scry/evaluation/questions.py`, `tests/test_eval_questions.py`
- Modify: `src/scry/evaluation/adapters.py`

**Interfaces:**
- Consumes: plan 3's `ask` and `AskResult` (P3) through the adapter; `Change` (P1).
- Produces, in `adapters.py`: `@dataclass AskOutcome`: `text: str`, `usage: dict`, `dollars: float`, `model: str`,
  `turns: int`, `tools: list[str]`, `stop: str`; `answer_fn(run, cfg, question: str) -> AskOutcome` (one call to plan
  3's `ask`; `text = answer`, `dollars = cost_usd`, `tools = tool_calls`, `model = cfg.model.model`).
- Produces, in `questions.py`:
  - `@dataclass RubricItem`: `id: str` (`M1`, `X1`, …), `kind: Literal["must", "must_not"]`, `text: str`
  - `@dataclass Question`: `id`, `key` (`"<id>@<6 hex>"`), `polarity: Literal["positive", "negative"]`, `style`,
    `question`, `reference`, `rubric: list[RubricItem]`, `evidence_frames: tuple[int, int] | None`, `evidence_t:
    tuple[float, float] | None`, `evidence_note: str`
  - `parse_questions(md: str) -> list[Question]`
  - `class Answer(BaseModel)`: `qid`, `key`, `polarity`, `question`, `answer`, `usage: dict`, `model: str | None`,
    `dollars: float`, `seconds: float`, `turns: int`, `tools: list[str]`, `stop: str | None`, `error: str | None`
  - `@dataclass Cited`: `frames: list[int]`, `refs: list[str]`, `transitions: list[str]`, `times: list[float]`;
    `read_citations(text: str) -> Cited`
  - `run_questions(run, cfg, questions_path: Path, answer=adapters.answer_fn, clock=time.perf_counter) ->
    list[Answer]`, writing `answers.jsonl` in the run directory; `load_answers(run) -> list[Answer]`
  - `citation_check(a: Answer, q: Question, boxes_by_frame: dict[int, set[str]], changes: list[Change]) -> dict`

**Rules — the file format** (that of `docs/ground-truth/span2-questions.md`):
1. A question starts at a line matching `^### (Q\d+) \((positive|negative), ([^)]+)\)\s*$` and ends at the next `#`
   heading. Everything outside question blocks is ignored.
2. Inside a block the bullets `- **Question:**`, `- **Reference answer:**`, `- **Rubric:**` and `- **Evidence:**` are
   read. A value continues over the following lines that are indented and do not start with `- ` after their
   indentation; continuation lines are stripped and joined with one space.
3. Rubric items are the indented lines `- M<n>: …` (`must`) and `- X<n>: …` (`must_not`) under **Rubric**, with the
   same continuation rule.
4. **Evidence** is split on `;`. A part matching `^frames (\d+)-(\d+)$` gives `evidence_frames`; `^t (\d+(?:\.\d+)?)-
   (\d+(?:\.\d+)?)$` gives `evidence_t`; the other parts, joined with `"; "`, are `evidence_note`.
5. `key = id + "@" + sha256(norm(question))[:6]`: an edited question is a different unit, so answers to different
   wordings are never paired (Task 12).
6. `ValueError` naming the question for: a repeated id; a missing **Question**, **Reference answer** or **Rubric**; no
   `M` item; a negative question without an `X` item; a repeated rubric id.

**Rules — the runner:**
7. Every question is asked once per run directory, in file order, each through one call of `answer` (a fresh
   conversation; nothing is shared between questions and no call cache is involved: these calls are what is judged).
8. `dollars` is the outcome's (plan 3 prices the summed usage of the turns); `seconds` is the wall time of the call,
   rounded to 0.1.
9. An exception from `answer` becomes an `Answer` with `error = "<Type>: <message>"[:500]` and empty `answer`; the
   runner continues with the next question.
10. Resume: an existing `answers.jsonl` entry with the same `key` and no `error` is kept; every other question is
    asked. The file is rewritten atomically after each answer.
11. `read_citations` reads what plan 3's prompt asks the agent to give in prose (N1): box refs
    `\b(\d+):(b\d+)\b`; frames `\bframes?\s+(\d+)(?:\s*(?:-|–|to)\s*(\d+))?` (both ends of a range; the word matched case-insensitively); transition ids
    `\bT\d+\b`; times `\b(\d{1,2}):(\d{2})(?:\.(\d+))?\b` as minutes and seconds, and `(\d+(?:\.\d+)?)\s*s\b` as
    seconds. Each list is sorted and without repeats. It is a heuristic over free text and feeds guards only.
12. `citation_check` → `{"cited": bool, "cited_in_evidence": bool | None, "invalid": int}`. `cited`: anything was
    read. `cited_in_evidence` (`None` when the question has neither evidence range): some cited frame, some box ref's
    frame or some cited transition's `to_frame` lies in `evidence_frames`, or some cited time lies in
    `[floor(evidence_t[0]), ceil(evidence_t[1])]` (an answer that says 10:28 for 628.77 s is inside). `invalid`: cited
    frames and box-ref frames that are not in the run, box refs whose `b<n>` is not among that frame's boxes, and
    transition ids that are not in `changes`. These guard the agent's citations; they are not part of an answer's
    label.

**Tests to write first.** The fixture text:

```
Intro that is ignored.
## Positive questions
### Q1 (positive, exact-string lookup)
- **Question:** Where does `git status` get run?
- **Reference answer:** At frame 2 (0:02.5),
  submitted by frame 3.
- **Rubric:**
  - M1: says `git status` was executed.
  - M2: gives frame 2 or 3.
  - X1: says it was not run.
- **Evidence:** executed row 1; frames 2-3; t 2.5-9.0
## Negative questions (secondary)
### Q2 (negative, did they)
- **Question:** Did they push?
- **Reference answer:** No.
- **Rubric:**
  - M1: says nothing was pushed.
  - X1: says `git push` was executed.
- **Evidence:** never-run row 1; frames 4-4; t 12.0-12.0
```

- `test_parse_questions`: two questions. Q1: `polarity "positive"`, `style "exact-string lookup"`, `reference "At
  frame 2 (0:02.5), submitted by frame 3."`, rubric ids `["M1", "M2", "X1"]` with kinds `["must", "must",
  "must_not"]`, `evidence_frames (2, 3)`, `evidence_t (2.5, 9.0)`, `evidence_note "executed row 1"`, `key` matching
  `^Q1@[0-9a-f]{6}$`. Q2: `polarity "negative"`, `evidence_frames (4, 4)`. Changing Q1's question text changes its
  `key` and not Q2's.
- `test_parse_errors`: removing Q2's `X1` line → `ValueError` containing `Q2`; a second `### Q1 (…)` block →
  `ValueError` containing `Q1`; removing Q1's **Reference answer** → `ValueError` containing `Reference`.
- `test_repo_question_file_parses` (reads `docs/ground-truth/span2-questions.md`; asserts structure only, because the
  owner will correct the content): between 10 and 25 questions; ids unique; at least 3 negative; every question has
  `evidence_frames` within `(155, 187)`.
- `test_run_questions_records_cost_and_time`: a fake `answer` returning `AskOutcome("It ran at frame 2.",
  {"input_tokens": 10_000, "output_tokens": 2_000}, 0.1, "claude-opus-5", 3, ["search", "get_frame"], "end_turn")` and
  a fake clock advancing 2.0 s per call → two answers; each `dollars 0.1`, `seconds 2.0`, `turns 3`, `tools ["search",
  "get_frame"]`; `answers.jsonl` has two lines.
- `test_answer_fn_maps_plan_3s_result`: with `scry.ask.ask` monkeypatched to return `AskResult(answer="x", turns=2,
  tool_calls=["search"], usage={"input_tokens": 1}, cost_usd=0.0225, stop="end_turn")` → `AskOutcome` with `text "x"`,
  `dollars 0.0225`, `tools ["search"]`, `model` the config's.
- `test_resume_keeps_answers_and_asks_changed_questions`: run again with Q2's question text changed → the fake is
  called once (for Q2 only); Q1's answer is byte-equal to before.
- `test_answer_error_is_recorded_not_raised`: the fake raises `RuntimeError("rate limit")` for Q1 → Q1 `error
  "RuntimeError: rate limit"`, `answer ""`, `dollars 0.0`; Q2 answered.
- `test_read_citations`: `"They ran `git status` at 24.4–26.4 s (T2, frame 12); see 12:b4 and 99:b1, also 0:25 and
  frames 12 to 13."` → `frames [12, 13]`, `refs ["12:b4", "99:b1"]`, `transitions ["T2"]`, `times [25.0, 26.4]`; `"No
  idea."` → four empty lists.
- `test_citation_check`: that answer, boxes `{11: {"b3"}, 12: {"b3", "b4", "b5"}, 13: {"b1"}}`, changes `T2 11→12`,
  `evidence_frames (11, 12)`, `evidence_t (24.4, 26.4)` → `cited True`, `cited_in_evidence True`, `invalid 1` (frame
  99). An answer citing only `10:28` against `evidence_t (628.77, 629.57)` → `cited_in_evidence True`; citing only
  `T9` with no such change → `invalid 1`, `cited_in_evidence False`. `"No idea."` → `cited False`, `cited_in_evidence
  False`, `invalid 0`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_questions.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–12 and the `answer_fn` adapter (P3).
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): question-set parser and the question runner through ask, with cost per question`

### Task 7: Scoring answers against the rubric with a separate model call

**Files:**
- Create: `src/scry/evaluation/judge.py`, `tests/test_eval_judge.py`

**Interfaces:**
- Consumes: `Question`, `RubricItem`, `Answer` (Task 6); `scry.providers` (`VlmProvider.complete`, `CallCache`,
  `text_block`); `sha256_obj`; `estimate_cost`.
- Produces:
  - `JUDGE_PROMPT_VERSION = "judge-v1"`; `JUDGE_SYSTEM: str` (the text below)
  - `class ItemVerdict(BaseModel)`: `id: str`, `holds: bool`, `quote: str`; `class JudgeOutput(BaseModel)`: `items:
    list[ItemVerdict]`
  - `SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}`
  - `label_from(items: dict[str, bool], rubric: list[RubricItem]) -> Literal["correct", "partial", "wrong"]`
  - `class Judgment(BaseModel)`: `run: str`, `qid`, `key`, `polarity`, `items: dict[str, bool]`, `quotes: dict[str,
    str]`, `label: str | None`, `score: float | None`, `source: Literal["judge", "rule", "eye"]`, `model: str | None`,
    `usage: dict`, `dollars: float`, `error: str | None`
  - `judge_answers(run_name: str, questions: list[Question], answers: list[Answer], provider, effort: str = "low") ->
    list[Judgment]`; `judge_provider(m: Matrix, base_cfg: Config, results_dir: Path) -> VlmProvider`;
    `write_judgments(run, js)`, `load_judgments(run) -> list[Judgment]` (`judgments.jsonl` in the run directory)

**The judge's system prompt (`JUDGE_SYSTEM`):**

```
You grade one answer to a question about a screen-recording tutorial. You are given the question, a reference answer
written from ground truth, a list of rubric statements, and the answer to grade. For each rubric statement decide
whether it is true OF THE ANSWER, not whether it is true of the video. Judge only what the answer says. Do not reward
or punish style, length, hedging or citations. A statement about an exact string holds only if the answer contains that
string character for character, including case. A statement that the answer gives a time in a range also holds when
the answer names a frame in the stated range. A "says ..." or "claims ..." statement holds when the answer asserts it
as its conclusion, not when it mentions it as a possibility it rejects. Return every rubric id exactly once, with holds
true or false and a short verbatim quote from the answer that decided it (empty when nothing in the answer bears on it).
```

**Rules:**
1. One call per answer, carrying one text block: the question, the reference answer, the rubric lines as `id: text`,
   and the answer. Never the run name, the configuration, the phase, other answers or any frame: the judge is blind.
2. The call goes through `provider.complete(stage="judge", system=JUDGE_SYSTEM, blocks=[…], output_model=JudgeOutput,
   effort=effort, prompt_version=JUDGE_PROMPT_VERSION, input_hashes=[sha256_obj({"question", "reference", "rubric",
   "answer"})])`. `judge_provider` builds an `AnthropicProvider` whose `CallCache` is `results_dir / "judge-cache"`,
   never a run's cache, with `model = m.judge.get("model", base_cfg.model.model)`. The judge is an instrument, not the
   thing measured: caching it makes re-scoring free and repeatable, and two identical answers get one verdict.
3. `label_from`: `wrong` when any `must_not` item holds or no `must` item holds; `correct` when every `must` item
   holds and no `must_not` item does; otherwise `partial`. `score = SCORE[label]`.
4. An answer that is empty after `strip()`, or has an `error`, is `wrong` with `source "rule"`, every item `False`, and
   no call.
5. Verdicts for ids that are not in the rubric are dropped. A rubric id the judge did not return, a provider error, or
   a refusal gives `label None`, `score None` and `error` naming the ids or the provider's error; nothing is
   defaulted. Such judgments are counted in every report and excluded from means.
6. `dollars = estimate_cost(usage, model)` of the call (P3's function; `0.0` for a cache hit, whose
   `VlmResult.cached` is true).
7. The judge's verdicts are never reported without the agreement check of Task 8 beside them.

**Tests to write first** (a fake provider: an object with `model = "claude-opus-5"` and an async `complete(**kw)` that
records `kw` and returns a `VlmResult` with a canned `JudgeOutput` and `usage {"input_tokens": 2_000, "output_tokens":
200}`):
- `test_label_from`: rubric `M1, M2, X1` → `{M1: T, M2: T, X1: F}` `correct`; `{T, F, F}` `partial`; `{T, T, T}`
  `wrong`; `{F, F, F}` `wrong`. Rubric `M1` only → `{M1: T}` `correct`, `{M1: F}` `wrong`.
- `test_judge_scores_and_costs_an_answer`: Task 6's Q1 and the answer `"git status ran at frame 2."`, canned verdicts
  `M1 T`, `M2 T`, `X1 F` → `label "correct"`, `score 1.0`, `source "judge"`, `dollars 0.015`, `quotes` has three keys.
- `test_judge_is_blind`: `run_name "span2-transcribing-r1"` → the recorded `system` and block texts contain neither
  `span2-transcribing-r1` nor `transcribing`; the recorded `input_hashes` are equal for two runs whose answers have the
  same text, and differ when the answer text differs.
- `test_missing_item_is_an_error_not_a_default`: canned verdicts for `M1` and `M2` only → `label None`, `score None`,
  `error` containing `X1`.
- `test_unknown_ids_are_dropped`: canned verdicts `M1, M2, X1, Z9` → `items` has exactly the three rubric keys.
- `test_empty_answer_is_wrong_without_a_call`: an `Answer` with `answer ""` and one with `error "RuntimeError: x"` →
  both `label "wrong"`, `source "rule"`, `dollars 0.0`; the fake recorded no call.
- `test_provider_error_is_recorded`: the fake returns `VlmResult(None, "refusal")` → `label None`, `error "refusal"`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_judge.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): rubric scoring of answers by a blind, cached judge call; labels derived by code`

### Task 8: The by-eye answer sheet and the judge's agreement with it

**Files:**
- Create: `src/scry/evaluation/byeye.py`, `tests/test_eval_byeye.py`

**Interfaces:**
- Consumes: `Question`, `Answer` (Task 6); `Judgment`, `label_from`, `SCORE` (Task 7).
- Produces:
  - `item_code(run_name: str, key: str) -> str` = the first 8 hex digits of `sha256(f"{run_name}|{key}")`
  - `sample_answers(answers_by_run: dict[str, list[Answer]], questions: list[Question], per_question: int = 2, seed: int
    = 0) -> list[tuple[str, str]]` (run name, question key)
  - `render_answer_sheet(title: str, sample, questions, answers_by_run) -> tuple[str, dict]` (the Markdown, and the key
    `{code: {"run", "key"}}` that is saved beside it as `answer-sheet.key.json`)
  - `parse_sheet(md: str) -> dict[str, dict[str, bool]]` (code → rubric id → ticked; reviewed items only)
  - `agreement(eye: dict, key: dict, judgments: list[Judgment], questions: list[Question]) -> dict`
  - `apply_eye(judgments: list[Judgment], eye: dict, key: dict, questions) -> list[Judgment]`

**The procedure this task implements** (how a model-scored question set is made reportable without a threshold):
the judge scores every answer; the harness draws a blind sample; the owner ticks the same rubric lines by eye without
seeing the judge's verdicts or which configuration wrote the answer; the harness reports, beside every question score,
how often the judge and the eye agree, line by line and label by label, and lists every disagreement with the judge's
quote; for the sampled answers the eye's verdict replaces the judge's. Nothing decides whether the agreement is "good
enough": the numbers and the disagreements are in the report and the owner reads them. If the owner ticks every
answer, the judge drops out entirely.

**Rules:**
1. `sample_answers`: for question number `qi` (file order), the candidates are the runs, sorted by name, that hold an
   answer with that `key`, no `error` and a non-empty text; with `m` candidates, `step = max(1, m // per_question)` and
   `s = (seed + qi) % m`, take candidates `(s + j × step) % m` for `j = 0 … per_question − 1`, duplicates removed. No
   random number generator: the same inputs give the same sheet, and successive questions rotate through the runs so
   every configuration is sampled.
2. The sheet: a title line, the instruction paragraph "Tick a statement when it is true OF THE ANSWER. Tick `reviewed`
   when you have read the item; items without it are ignored.", then per sampled answer:
   `## item <code> (<qid>)`, `**Question:**`, `**Reference answer:**`, `**Answer:**` with the answer as a block quote,
   then `- [ ] reviewed` and one `- [ ] <id>: <text>` line per rubric item. It contains no run name, configuration,
   cost, judge verdict or citation check.
3. `parse_sheet`: items are found by `^## item ([0-9a-f]{8}) \(`; a checkbox is ticked for `[x]` or `[X]`; an item
   without a ticked `reviewed` line is left out; a rubric id missing from a reviewed item raises `ValueError` naming
   the item.
4. `agreement` over the reviewed items that have a judgment with `label` not `None`: `items_compared`,
   `item_agreement = round(equal / compared, 4)`, `confusion = {"both_true", "judge_only", "eye_only", "both_false"}`,
   `answers_compared`, `label_agreement` (labels derived with `label_from` on both sides), `judge_mean` and `eye_mean`
   (mean `SCORE` over the compared answers), and `disagreements = [{"code", "qid", "item", "judge", "eye", "quote"}]`.
   With nothing reviewed every rate is `None`.
5. `apply_eye`: for each reviewed item, the matching judgment (same run and key; created if the judge had failed) gets
   the eye's `items`, the label and score derived from them, and `source "eye"`. Reports count judgments by source.

**Tests to write first:**
- `test_sample_rotates_through_runs`: runs `a1, a2, a3, b1, b2, b3`, each answering `Q1@…` and `Q2@…` → with
  `per_question 2, seed 0`: `[("a1", Q1), ("b1", Q1), ("a2", Q2), ("b2", Q2)]`; with `seed 1` the first two are `a2,
  b2`; a run whose Q1 answer has an `error` is never sampled for Q1; with a single candidate run the question
  contributes one item.
- `test_sheet_is_blind_and_round_trips`: rendering a sample from runs named `span2-transcribing-r1` and
  `span2-none-r1` → the Markdown contains neither run name nor `transcribing`; `parse_sheet` of the untouched sheet
  is `{}`; after ticking `reviewed` and `M1` of the first item → `{code: {"M1": True, "M2": False, "X1": False}}`.
- `test_unreviewed_items_are_ignored`: ticks on an item whose `reviewed` box is empty do not appear.
- `test_agreement_numbers`: three reviewed answers. A (rubric `M1, X1`): eye `{M1: T, X1: F}`, judge the same. B
  (`M1, M2`): eye `{T, F}`, judge `{T, T}`. C (`M1, X1`): eye `{F, T}`, judge `{F, F}`. A fourth, unreviewed. →
  `items_compared 6`, `item_agreement 0.6667`, `confusion {"both_true": 2, "judge_only": 1, "eye_only": 1,
  "both_false": 2}`, `answers_compared 3`, `label_agreement 0.6667` (A correct/correct, B partial/correct, C
  wrong/wrong), `judge_mean 0.6667`, `eye_mean 0.5`, two `disagreements` (`B/M2`, `C/X1`).
- `test_apply_eye_overrides_the_judge`: after `apply_eye`, B's judgment has `label "partial"`, `score 0.5`, `source
  "eye"`; the unreviewed fourth keeps `source "judge"`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_byeye.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–5.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): blind by-eye answer sheet, tick parser, judge-against-eye agreement, by-eye override`

### Task 9: By-eye label sheets for containers and links

**Files:**
- Create: `src/scry/evaluation/labelsheet.py`, `tests/test_eval_labelsheet.py`
- Modify: `src/scry/evaluation/adapters.py`

**Interfaces:**
- Consumes: `Run.load_labels`, `Labels.box`, `Labels.frame` (P2); `Run.load_boxes` (P1).
- Produces, in `adapters.py`: `@dataclass LabelItem`: `frame: int`, `kind: Literal["container", "run", "pair",
  "record"]`, `ident: str`, `summary: str`; `label_items(run, frames: Sequence[int]) -> list[LabelItem]`.
- Produces, in `labelsheet.py`:
  - `sample_frames(frames: Sequence[int], n: int, always: Sequence[int] = ()) -> list[int]`
  - `run_code(run_name: str) -> str` = `"R" +` the first 4 hex digits of `sha256(run_name)`
  - `thin(items: list[LabelItem], per_kind: int) -> list[LabelItem]`
  - `render_label_sheet(title, frames, items_by_run: dict[str, list[LabelItem]], frame_png: Callable[[int], str]) ->
    tuple[str, dict]`; `parse_label_sheet(md: str) -> dict`; `label_tallies(parsed: dict, key: dict) -> dict`

**Rules** (owner's ruling: label quality is judged by eye on samples; there is no label ground truth to score against):
1. `sample_frames`: with `m` sorted frames and `n < m`, the frames at 0-based positions `floor((i + 0.5) × m / n)` for `i = 0 …
   n − 1`; with `n ≥ m`, all of them; then the members of `always` that are in `frames` are added (the span's popup
   frames); sorted, unique. Every run on a sheet is shown on the same frames, so tallies pair by frame.
2. `label_items` lists, for a frame, the labels in force there after plan 2's join. Containers: the frame's boxes
   grouped by `Labels.box(ref).container_ref`, one item per group (`ident` the ref; `summary` = `kind | app | name | <n>
   boxes: "<first three box texts in reading order, joined by ' · '>"`), plus one item with `0 boxes` for each popup
   of `Labels.frame(frame).containers` that no box is assigned to. Links: one item per link of
   `Labels.frame(frame).links` (`run`: the member texts in order with the joiner shown; `pair`: `"<key texts>" →
   "<value texts>"`; `record`: header texts, then each member's texts, joined by ` | `), `ident` = the link's kind and
   first box ref.
3. `thin`: at most `per_kind` items of each kind per run and frame, taken at even spacing by rule 1's formula over the
   items in file order.
4. The sheet: per frame `## frame <n>` and the image path `frame_png(n)` (the matrix source's frame, identical for all
   runs, so it reveals no configuration); per run a block `### frame <n> run <run_code>` with `- [ ] reviewed`, one
   `- [ ] (<code>) <kind>: <summary>` per item (`code` = the first 6 hex of `sha256(run|frame|kind|ident)`), and the
   two lines `missed containers: 0` and `missed links: 0` for the owner to overwrite. A tick means "this label is
   right". The key maps run codes and item codes back.
5. `label_tallies`, over reviewed blocks only: per run and kind `judged`, `correct`, `precision_by_eye = round(correct
   / judged, 4)` (`None` when nothing was judged); `missed_containers`, `missed_links` summed per run; and `units` for
   `labels.precision.<kind>` keyed by frame. Recall is not computed: only the owner's missed counts are reported.
6. These tallies are guards (spec §9 lists link and container quality among them): reported beside the scores,
   never part of a reading.

**Tests to write first:**
- `test_sample_frames`: frames `145 … 155`, `n 3`, `always [149, 151, 160]` → `[146, 149, 150, 151, 154]`; `n 20` → all
  eleven; `n 3` without `always` → `[146, 150, 154]`.
- `test_thin`: ten `pair` items and two `container` items, `per_kind 3` → the pairs at 0-based positions 1, 5 and 8 (`floor(0.5
  × 10 / 3)`, `floor(1.5 × 10 / 3)`, `floor(2.5 × 10 / 3)`) and both containers.
- `test_sheet_is_blind_and_round_trips`: two runs named `smoke-transcribing-r1` and `smoke-grouponly-r1`, one frame,
  three items each → the Markdown contains neither run name; untouched it parses to no reviewed block; after ticking
  `reviewed` and two of three items in the first block and writing `missed links: 2` → that block parses to two
  ticked codes, one unticked, `missed_links 2`, `missed_containers 0`.
- `test_label_tallies`: run `R1` reviewed on frames 149 and 150: containers judged 4 correct 3 (frame 149: 2 of 2;
  frame 150: 1 of 2), pairs judged 5 correct 5, `missed links` 2 and 0; run `R2` not reviewed → `R1.container
  {"judged": 4, "correct": 3, "precision_by_eye": 0.75}`, `R1.pair.precision_by_eye 1.0`, `R1.missed_links 2`,
  `units["labels.precision.container"] == {"149": 1.0, "150": 0.5}` for `R1`; `R2` absent.
- `test_label_items_on_the_mini_run` (`mini_run(tmp_path, labels=True)`, frame 12) → three items: a `container` whose
  summary contains `window | Azure Portal | Resource overview | 2 boxes` and `"Status" · "Creating"`; a `container`
  whose summary contains `window | Windows Terminal | PowerShell | 3 boxes`; a `pair` with summary `"Status" →
  "Creating"`. With `labels=False` → `[]`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_labelsheet.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6 and the `label_items` adapter.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): blind by-eye label sheets over shared sample frames; precision-by-eye tallies per kind`

### Task 10: The scorecard: one run, every number, per-unit values

**Files:**
- Create: `src/scry/evaluation/scorecard.py`, `tests/test_eval_scorecard.py`
- Modify: `src/scry/evaluation/adapters.py`

**Interfaces:**
- Consumes: Tasks 1, 3–9; `parse_commands` (P1); `estimate_cost` (P3).
- Produces, in `adapters.py`: `boxes_by_frame(run) -> dict[int, set[str]]`; `@dataclass Adapters` bundling the adapter
  functions as fields (`lifetimes`, `changes`, `vlm_majority`, `interpretations`, `index_db`, `frame_labels`,
  `annotation_usage`, `boxes_by_frame`), and `REAL = Adapters(...)` holding the real ones. Tests may pass fakes.
- Produces, in `scorecard.py`:
  - `@dataclass(frozen=True) MetricDef`: `name`, `role: Literal["primary", "secondary", "question", "guard", "cost"]`,
    `unit: Literal["entry", "never_run", "question", "frame", "transition", "run"]`, `better: Literal["higher",
    "lower"]`
  - `METRICS: dict[str, MetricDef]`, exactly this table:

    | name | role | unit | better |
    |---|---|---|---|
    | `found`, `exact.ocr`, `exact.vlm`, `exact.any` | primary | entry | higher |
    | `exact_in_window.any`, `submit_marked` | secondary | entry | higher |
    | `first_t_error_abs.any`, `submit_t_error_abs` | secondary | entry | lower |
    | `false_run` | secondary | never_run | lower |
    | `questions.positive`, `questions.negative` | question | question | higher |
    | `ask.cited_in_evidence` | guard | question | higher |
    | `ask.invalid_citations` | guard | question | lower |
    | `box_stability` | guard | run | higher |
    | `touched_share_low_half`, `unstable_rate` | guard | run | lower |
    | `one_container_share`, `popup_found`, `labels.precision.container`, `.run`, `.pair`, `.record` | guard | frame | higher |
    | `repairs`, `unassigned` | guard | frame | lower |
    | `invalid_citations` | guard | transition | lower |
    | `cost.per_frame`, `seconds.per_frame` | cost | run | lower |
    | `cost.annotate` | cost | frame | lower |
    | `cost.interpret` | cost | transition | lower |
    | `cost.per_question` | cost | question | lower |

  - `build_scorecard(run_dir: Path, adapters: Adapters = REAL, identity: dict | None = None, eye: dict | None = None,
    label_tallies: dict | None = None) -> dict`; `write_scorecard(run_dir, card)` (`scorecard.json`);
    `load_scorecards(root: Path, phase: str) -> list[dict]`

**Rules:**
1. Inputs come from the run directory: `evalrun.json` (the spec, the span's ground-truth and question paths, the code
   identity at run start, stage seconds), `config.json` (the default model), `manifest.json`, the call cache, and the
   records through `adapters`.
2. The card: `{"run": {phase, name, config_id, span, frames, values, repeat, judged, fixed_from, status, resumed},
   "inputs": {"ground_truth_sha256", "questions_sha256"}, "code": {"git_commit", "metric_code_hash", "at_run_start",
   "changed_since_run": bool}, "counts": {"frames", "transitions", "lifetimes"}, "commands": Task 4's result | None,
   "guards": Task 5's result (with "by_eye_labels": this run's tallies | None), "questions": … | None, "cost": Task 1's
   run_cost, "units": {metric: {unit: value}}, "warnings": [str], "notes": [str]}`.
3. `commands` is scored when the span names a ground truth: Task 4's `score_commands`. Without `index.sqlite` the
   found keys are `None` (note `no index: found not scored`); without interpretations the submission keys are `None`
   (note); without lifetimes `commands` is `None` with a warning.
4. `questions`, when `judgments.jsonl` exists: judgments after `apply_eye` (when `eye` is given), split by polarity:
   `{"n", "correct", "partial", "wrong", "unscored", "mean"}` each, `by_source`, `dollars_per_question` (mean of the
   answers' `dollars`), `ask_dollars`, `judge_dollars`, `seconds_per_question`, and the citation guards (`cited`,
   `cited_in_evidence`, `invalid` as counts over answers). Units are keyed by the question `key`: `questions.positive`,
   `questions.negative` (the score; unscored judgments have no unit), `ask.cited_in_evidence`, `ask.invalid_citations`,
   `cost.per_question`.
5. Cost units: `cost.per_frame` and `seconds.per_frame` under the unit `"run"`; `cost.annotate[frame] =
   estimate_cost(usage, model)` from `annotation_usage`, and `0.0` for a frame of the run without a call (when
   annotations exist at all); `cost.interpret[change id]` from each interpretation's `usage` and `model`, and `0.0` for
   a change without an interpretation (when interpretations exist at all).
6. `units` is the union of the command, guard, question and cost units. Every key is a name in `METRICS`.
7. Warnings (things that weaken the evidence): every warning of `run_cost` (not cold, manifest against cache); `metric
   code changed since the run started` when `identity["metric_code_hash"]` differs from the one in `evalrun.json`;
   `run status is <status>` unless `done`; failed `interpret` or `annotate` calls with their count; answers with
   `error`; judgments with `label None`. Notes (expected absences): no annotations, no index, no interpretations, no
   second reader, a fixed upstream (`upstream fixed to <run>: differences before <first stage> were not sampled`).
8. A scorecard is rebuilt freely: scoring calls no model and costs nothing.

**Tests to write first** (rates are two-element lists, as they are after a JSON round trip. The run directory is plan
3's Fixture M with everything real: `mini_run(tmp_path, labels=True)`, `mini_interpretations(run)`, `build_index(run,
cfg)`; added by hand: `evalrun.json` with span `s` frames `[10, 13]`, `ground_truth` = Task 4's `git status` / `git
stash` file, `status "done"`, `code.metric_code_hash "h"`, `stage_status.interpret.seconds 4.0`; `config.json` with
`model.model = "claude-opus-5"`; in the manifest `stages.decode.emitted = 4` and `stages.interpret = {"usage":
{"input_tokens": 20_000}, "model": "claude-opus-5", "cache": {"hits": 0, "misses": 3}}`; one call-cache file for stage
`interpret` with the same usage; identity hash `"h"`):
- `test_scorecard_numbers`: `counts == {"frames": 4, "transitions": 3, "lifetimes": 7}`; `commands.rates.found == [1,
  1]`, `rates.exact.ocr == [1, 1]`, `rates.exact.vlm == [1, 1]`, `rates.submit_marked == [1, 1]`, `rates.false_run ==
  [0, 1]`; `units["found"] == {"1": 1.0}`; `units["false_run"] == {"N1": 0.0}`; `guards.track.box_stability 0.8889`
  ((2 + 3 + 4 − 1) / 9), `guards.track.unstable_rate 0.1429` (1 / 7); `guards.labels.one_container_share 1.0`;
  `units["one_container_share"] == {"10": 1.0, "11": 1.0, "12": 1.0, "13": 1.0}`; `cost.dollars 0.1`, `cost.per_frame
  0.025`, `cost.per_video 0.1` (projection 4), `units["cost.per_frame"] == {"run": 0.025}`,
  `units["seconds.per_frame"] == {"run": 1.0}`; `questions is None`; `warnings == []`; every key of `units` is in
  `METRICS`; `inputs.ground_truth_sha256` is the file's SHA-256.
- `test_scorecard_without_annotations_or_index`: `mini_run(tmp_path)` without labels, interpretations or index →
  `rates.found is None`, `rates.false_run is None`, `guards.labels is None`, no `found`, `false_run`,
  `one_container_share` or `cost.interpret` key in `units`, notes for the index, the interpretations, the annotations
  and the second reader, no exception.
- `test_interpret_cost_units`: interpretations rewritten with `usage {"input_tokens": 2_000}` and `model
  "claude-opus-5"` on `T1` and `T2` and no record for `T3` → `units["cost.interpret"] == {"T1": 0.01, "T2": 0.01, "T3":
  0.0}`.
- `test_metric_code_changed_since_run_is_flagged`: identity hash `"other"` → `code.changed_since_run True` and a warning
  containing `metric code changed`.
- `test_unfinished_and_uncold_runs_are_flagged`: `status "failed"` → a warning containing `failed`; manifest `cache.hits
  2` → a warning containing `2 cache hits`.
- `test_questions_section`: `answers.jsonl` with two answers (`Q1@aaaaaa` positive `dollars 0.1`, `Q2@bbbbbb` negative
  `dollars 0.2`) and `judgments.jsonl` with labels `correct` and `wrong` → `questions.positive == {"n": 1, "correct":
  1, "partial": 0, "wrong": 0, "unscored": 0, "mean": 1.0}`, `questions.negative.mean 0.0`, `dollars_per_question
  0.15`, `units["questions.negative"] == {"Q2@bbbbbb": 0.0}`; with `eye` overriding Q2 to correct → `negative.mean
  1.0`, `by_source == {"judge": 1, "eye": 1}`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_scorecard.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–8.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): scorecard per run: scores, guards, cost, per-unit values, warnings`

### Task 11: The noise floor, from repeats of identical cold runs

**Files:**
- Create: `src/scry/evaluation/noise.py`, `tests/test_eval_noise.py`

**Interfaces:**
- Consumes: scorecards (Task 10).
- Produces: `paired_difference(a: dict[str, float], b: dict[str, float]) -> tuple[float | None, int, int]`;
  `run_value(units: dict[str, float]) -> float | None`; `same_config_diffs(cards: list[dict], metric: str, units:
  set[str] | None = None) -> list[float]`; `floor_single(diffs: list[float]) -> float | None`; `scaled_floor(f1: float,
  n_a: int, n_b: int) -> float`; `noise_table(cards: list[dict]) -> dict`; `floor_lookup(noise: dict, span: str, values:
  dict, floor_match: Sequence[str]) -> dict[str, float]`

**Rules** (spec §9: "P1 sets the noise floor; a difference inside it is no difference"; ledger L42: identical cold
runs differ):
1. `paired_difference(a, b)`: over the units present in both, the mean of `b[u] − a[u]`, rounded to 6; with it the
   number of common units and the number dropped (`|a ∪ b| −` common). No common unit → `(None, 0, dropped)`.
2. `same_config_diffs`: for every pair `i < j` of cards that both hold the metric, `|paired_difference(units_i,
   units_j)|`, restricted to `units` when given. Cards are "the same configuration" when their `config_id` and phase
   are equal; they differ only in `repeat`.
3. **The floor for one run against one run** is `floor_single` = the largest of those absolute differences: the
   biggest difference ever seen between two runs that should have been identical. `None` without a pair.
4. **Means of repeats are steadier than single runs.** For a mean of `n_a` runs against a mean of `n_b`,
   `scaled_floor = f1 × sqrt((1/n_a + 1/n_b) / 2)`, rounded to 6: `f1` itself for one against one, `f1 × 0.7071` for two
   against two, `f1 × 0.5774` for three against three. This is what lets added repeats clear the noise (spec §9).
5. `noise_table`: per configuration with at least two repeats, per metric: `{"values": [run_value per repeat, in repeat
   order, rounded to 4], "pairs", "max", "median"}` of the absolute paired differences; configurations of unjudged
   runs are listed with `"deterministic": true` and no metrics. Written as `noise.json` with the phase and the commit.
6. `floor_lookup`: among the configurations of a noise file with the same span and the same value on every
   `floor_match` axis that `values` has, the largest `max` per metric; `{}` when none matches.

**Tests to write first:**
- `test_paired_difference`: `a {"1": 1, "2": 1, "3": 0}`, `b {"1": 1, "2": 0, "3": 0}` → `(-0.333333, 3, 0)`; `a {"1": 1,
  "2": 0}`, `b {"1": 1, "2": 1, "3": 1}` → `(0.5, 2, 1)`; disjoint → `(None, 0, 2)`.
- `test_floor_from_three_repeats`: `found` units of three repeats `{1: 1, 2: 1, 3: 0}`, `{1: 1, 2: 0, 3: 0}`, `{1: 1,
  2: 1, 3: 0}` → diffs `[0.333333, 0.0, 0.333333]`, `floor_single 0.333333`; `noise_table` gives `values [0.6667,
  0.3333, 0.6667]`, `pairs 3`, `max 0.333333`, `median 0.333333`.
- `test_scaled_floor`: `(0.3, 1, 1)` → `0.3`; `(0.3, 2, 2)` → `0.212132`; `(0.3, 3, 3)` → `0.173205`; `(0.3, 3, 1)` →
  `0.244949`.
- `test_single_run_has_no_floor`: one card → `same_config_diffs == []`, `floor_single([]) is None`, and the
  configuration is absent from `noise_table`.
- `test_unjudged_runs_are_deterministic`: two cards with `run.judged False` → `{"deterministic": True}`.
- `test_floor_lookup`: a noise file with `span2-transcribing` (`found` max 0.1429), `span2-grouponly` (0.2857) and
  `smoke-grouponly` (0.5); lookup for span `span2`, values `{"base": "grouponly", "arm": "B"}`, match `("base",)` →
  `{"found": 0.2857}`; values `{"prompt": "v2"}` → `{}`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_noise.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): noise floor from paired differences between identical cold runs`

### Task 12: Paired comparison: inside or outside the noise

**Files:**
- Create: `src/scry/evaluation/compare.py`, `tests/test_eval_compare.py`

**Interfaces:**
- Consumes: scorecards and `METRICS` (Task 10); `noise.py` (Task 11); `Matrix.compare`, `floor`, `floor_match` (Task 2).
- Produces:
  - `select(cards: list[dict], selector: dict, phase: str) -> dict[str, list[dict]]` (config id → its repeats)
  - `@dataclass Row`: `metric`, `role`, `unit`, `better`, `n_a`, `n_b`, `units: int`, `dropped: int`, `mean_a`, `mean_b`,
    `diff`, `floor_single`, `floor`, `verdict: Literal["outside", "inside", "unknown", "not comparable"]`, `reason: str
    | None`, `favours: Literal["a", "b"] | None`, `flips: list[str]`, `cost_a: dict`, `cost_b: dict`
  - `compare_configs(a: list[dict], b: list[dict], floor_extra: dict[str, float] | None = None) -> list[Row]`
  - `COMMAND_ORDER = ("found", "exact.any", "first_t_error_abs.any", "submit_t_error_abs", "false_run")`,
    `QUESTION_ORDER = ("questions.positive", "questions.negative")`, of which `found`, `exact.any` and
    `questions.positive` are the scores and the rest break ties
  - `reading(rows: list[Row]) -> dict[str, str]` with the keys `commands` and `questions`
  - `planned_comparisons(m: Matrix, cards: list[dict], earlier: list[dict], noise_file: dict | None) ->
    list[tuple[str, str, str, list[Row]]]` (span, A's config id, B's config id, rows)

**Rules:**
1. **Same frames or nothing.** All cards of both sides must have the same `run.frames`; otherwise `ValueError`
   containing `paired over the same frames`.
2. One row per metric of `METRICS` that any card holds. A metric that every card of one side lacks gives `verdict "not
   comparable"` with `reason "absent in A"` or `"absent in B"` (the second reader does not exist without
   transcription). Command metrics are `not comparable` with `reason "ground truth differs"` when
   `inputs.ground_truth_sha256` is not one value across all cards. Question units carry the question's text hash in
   their key, so answers to a reworded question simply do not pair and are counted in `dropped`.
3. **Pairing.** The common units are those present in every card of both sides that holds the metric. `a_u` is the
   mean over A's cards of the value at `u`, `b_u` likewise; `diff = mean over u of (b_u − a_u)`, `mean_a` and `mean_b`
   the means of `a_u` and `b_u`; all rounded to 6. `dropped` = units seen in some card and not common. No common unit →
   `not comparable`, `reason "no common units"`.
4. **The floor.** `floor_single` = the largest of: the same-configuration differences inside A and inside B, computed
   over the common units (Task 11 rule 2), and `floor_extra[metric]` when given. When every card of both sides is
   unjudged the floor is `0.0`. Otherwise, with no pair and no extra, `floor_single` is `None` and the verdict
   `unknown`: single runs without a measured floor are never evidence of a difference (L42).
5. `floor = scaled_floor(floor_single, n_a, n_b)`; `verdict = "outside"` when `|diff| > floor`, else `"inside"`.
6. `favours`, for `outside` rows only: B when the difference goes the way `better` says, else A.
7. `flips`, for metrics whose values are all 0 or 1: `"<unit>: A only"` when every A card has 1 and every B card 0,
   `"<unit>: B only"` for the reverse. They name the commands or questions behind a difference.
8. Every row carries `cost_a` and `cost_b`: the mean `per_frame` and `per_video` over that side's cards.
9. `reading`: walk `COMMAND_ORDER`; the first row with verdict `outside` decides: `"<A|B> ahead on <metric> (outside the
   noise)"`, prefixed by `"tie on the scores; "` when the deciding metric is a tie-breaker. No `outside` row → `"no
   difference outside the noise"`; when `found` or `exact.any` is `unknown` the sentence ends with `"; noise unknown
   for <metric>: add repeats"`. `QUESTION_ORDER` is walked the same way, the negative questions being the tie-breaker.
   Guards and costs never enter a reading. The reading is a mechanical summary; the decision stays the owner's.
10. `select`: a card matches a selector when its phase equals the selector's `phase` (default: the matrix's phase) and
    `run.values[axis]` equals the selector's value for every other key. `planned_comparisons`: for each `[[compare]]`
    table and each span both sides have, A's configurations against B's (`b = "each"` means every configuration of the
    matrix's phase); `earlier` holds the scorecards of other phases for selectors that name one; `floor_extra` comes
    from `floor_lookup` on the matrix's `floor` file for A's and for B's values, the larger per metric.

**Tests to write first:**
- `test_outside_the_noise`: `found` units. A: `{1: 1, 2: 1, 3: 1}`, the same, `{1: 1, 2: 1, 3: 0}`. B: three times `{1:
  1, 2: 0, 3: 0}`. → `units 3`, `mean_a 0.888889`, `mean_b 0.333333`, `diff -0.555556`, `floor_single 0.333333`, `floor
  0.19245`, `verdict "outside"`, `favours "a"`, `flips ["2: A only"]`.
- `test_inside_the_noise`: `repairs` (lower is better). A: `{f1: 2, f2: 0}`, `{f1: 4, f2: 0}`. B: `{f1: 3, f2: 1}`,
  `{f1: 3, f2: 0}` → `diff 0.25`, `floor_single 1.0`, `floor 0.707107`, `verdict "inside"`, `favours None`.
- `test_single_runs_are_unknown_until_a_floor_is_supplied`: one card a side, `found` A `{1: 1, 2: 1}`, B `{1: 1, 2: 0}`
  → `verdict "unknown"`; with `floor_extra {"found": 0.2}` → `floor 0.2`, `verdict "outside"`; with `floor_extra
  {"found": 0.5}` → `"inside"` (`|−0.5| > 0.5` is false).
- `test_unjudged_runs_compare_exactly`: the same two cards with `run.judged False` → `floor 0.0`, `verdict "outside"`;
  equal units → `diff 0.0`, `"inside"`.
- `test_missing_units_are_dropped_and_counted`: A's second card lacks unit `3` → `units 2`, `dropped 1`.
- `test_different_frames_are_refused`: A on `[155, 187]`, B on `[145, 155]` → `ValueError` containing `same frames`.
- `test_edited_ground_truth_is_not_comparable`: different `ground_truth_sha256` → the `found` row is `not comparable`
  with `reason "ground truth differs"`; the `repairs` row is still compared.
- `test_absent_reader`: `exact.vlm` in A's cards only → `not comparable`, `reason "absent in B"`.
- `test_rows_carry_cost`: A's cards `per_frame` 0.12 and 0.14, `per_video` 26.52 and 30.94 → every row's `cost_a ==
  {"per_frame": 0.13, "per_video": 28.73}`.
- `test_reading`: rows `found` outside favouring A → `commands == "A ahead on found (outside the noise)"`; `found` and
  `exact.any` inside and `false_run` outside favouring B → `"tie on the scores; B ahead on false_run (outside the
  noise)"`; everything inside → `"no difference outside the noise"`; `found` unknown → the sentence ends with `"noise
  unknown for found: add repeats"`; a `repairs` row outside never changes either sentence.
- `test_select_and_planned_comparisons`: cards of phase `p1` with `values.base` in `transcribing`, `grouponly` on spans
  `smoke` and `span2`, three repeats each; `[[compare]] a = {base = "transcribing"}, b = {base = "grouponly"}` → two
  comparisons, `("smoke", "smoke-transcribing", "smoke-grouponly")` and the `span2` one; a selector `{phase = "p0",
  base = "x"}` with no matching card yields no comparison and no exception.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_compare.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–10.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): paired comparison over common units; every difference marked inside or outside the noise`

### Task 13: Markdown reports, the results directory, the ledger-row template

**Files:**
- Create: `src/scry/evaluation/reporting.py`, `tests/test_eval_reporting.py`

**Interfaces:**
- Consumes: scorecards, `noise_table`, `planned_comparisons`, `reading`, `agreement`, `label_tallies`, `estimate_cost`.
- Produces:
  - `config_rows(cards: list[dict]) -> list[dict]` (one row per configuration: means over its repeats)
  - `table(headers: list[str], rows: list[list], cost: bool = True) -> str`
  - `phase_report(m: Matrix, cards, noise: dict, comparisons, agreement: dict | None, tallies: dict | None, identity:
    dict, today: str) -> str`
  - `next_ledger_number(ledger_md: str) -> int`; `ledger_row(m: Matrix, cards, comparisons, agreement, number: int,
    today: str) -> str`
  - `write_results(results_dir: Path, m: Matrix, …) -> list[Path]`: `report.md`, `scores.json` (every scorecard of the
    phase, so the report can be rebuilt from committed data), `noise.json`, `ledger-row.md`

**Rules:**
1. **Cost beside every number.** `table(..., cost=True)` requires the last two headers to be `$ / frame` and `$ / video`
   and raises `ValueError` otherwise; every table of the report that shows a score, a guard or a question result is
   built with it. Per configuration the two columns are the means over its repeats; the header line of the report
   says: `$ / video = $ / frame × <N> frames, a linear projection from this span to the whole source video`.
2. Sections, in this order: `# <phase> evaluation report` (date, commit, metric-code hash, matrix path, runs by
   status); `## Warnings` (every scorecard warning, prefixed by the run name; `none` when empty); `## Runs` (run,
   status, frames, cold, resumed, dollars, $ / frame, $ / video, wall seconds); `## Cost` (per configuration and stage:
   $ / frame, $ / video, the same at the batch price, seconds / frame; questions: $ / question, judge dollars; the
   matrix's `[reference]` row when present, its dollars computed by `estimate_cost` from its `usage` and `model`);
   `## Commands: scores` (found, exact per reader
   and any, as `k/n` per repeat and mean); `## Commands: tie-breakers` (first-appearance error, submit marked,
   submission error, false run, exact-in-window, and the list of entries where `exact` holds and `in_window` does not);
   `## Commands by entry` (per configuration and entry: found in `r/n` runs, exact.any in `r/n` runs, `nearest`
   reading where not exact, `variant_only`); `## Questions` (positive, then negative marked secondary: correct /
   partial / wrong / unscored, mean; by source; the agreement block of Task 8 with every disagreement; citation guards);
   `## Guards (reported, never ranked)`; `## By-eye labels`; `## Noise floor` (per configuration and metric: the
   repeats' values, pairs, max, median); `## Comparisons` (per planned comparison: a table of rows — metric, role, A,
   B, difference, floor, verdict, favours, units, dropped, `$ / frame` and `$ / video` of A and of B — then the flips,
   then the two sentences of `reading`, introduced by `Mechanical reading (the decision is the owner's):`); `## Ledger
   row`.
3. Vocabulary: the verdict column holds only `outside`, `inside`, `unknown`, `not comparable`. The report never
   contains the words `threshold`, `significant` or `pass`, and says `failed` only of a run's status.
4. A comparison whose either side has a fixed upstream repeats that scorecard's note under its table.
5. `next_ledger_number`: one more than the largest `n` in lines matching `^\| L(\d+) \|`.
6. `ledger_row` is one Markdown table line with the ledger's five cells: `| L<n> | <today> | **<phase>: <matrix file>,
   <runs> runs (<judged> cold), commit <commit>, metric code <hash[:8]>, spend $<total> (pipeline $…, questions $…,
   judge $…).** Per configuration on <span>: <config>: found k/n, exact ocr k/n vlm k/n any k/n, questions +<mean> /
   −<mean>, $<per_frame>/frame, $<per_video>/video; … Outside the noise: <metric (A against B, favours)>, … or
   nothing. Inside or unknown: <count>. Judge against eye: <item_agreement> over <items> rubric lines, <n>
   disagreements. Warnings: <n>. | WHY: <to be written by the author> | IF YOU DISAGREE: <to be written by the author> |`.
   Counts `k/n` are means over repeats shown with one decimal when not whole. A `|` inside a cell is written `\|`.
   The measured part is filled by code; the two capitalised cells are the only text a person writes.

**Tests to write first** (scorecards built as dicts: phase `p9`, span `span2`, configurations `span2-a` and `span2-b`,
two repeats each, `found` and `repairs` units, `cost.per_frame 0.13` / `per_video 26.0` for `a` and `0.08` / `16.0` for
`b`, one warning on `span2-b-r2`; one planned comparison):
- `test_report_sections_in_order`: every heading of rule 2 appears, in that order.
- `test_every_results_table_has_the_cost_columns`: every Markdown table under `## Commands: scores`, `## Commands:
  tie-breakers`, `## Questions`, `## Guards (reported, never ranked)` and `## Comparisons` has a header line containing
  both `$ / frame` and `$ / video`; `table(["a", "b"], [], cost=True)` raises `ValueError`.
- `test_vocabulary`: the report contains none of `threshold`, `significant`, `pass` (case-insensitive, whole words);
  the verdict cells are within the four allowed words.
- `test_warnings_are_at_the_top`: the warning text appears under `## Warnings`, before `## Runs`, with `span2-b-r2`.
- `test_reference_row`: a matrix `[reference]` with `model "claude-opus-5"`, `frames 33` and the usage recorded by
  `runs/span2-before` (typed into the test: input 272050, output 127046, cache read 106335, cache creation 9105) → the
  cost section holds a row with the label, `4.6465` (1.36025 + 3.17615 + 0.0531675 + 0.05690625; the ledger's $4.59
  left the last term out) and `0.1408` per frame.
- `test_next_ledger_number`: a ledger text whose last rows are `| L42 |` and `| L43 |` → `44`; an empty text → `1`.
- `test_ledger_row`: one line; starts with `| L44 | 2026-09-22 | **p9:`; contains `found`, `$0.1300/frame`,
  `$26.00/video`, `WHY:` and `IF YOU DISAGREE:`; splitting on unescaped `|` gives exactly five cells.
- `test_write_results`: the four files exist; `scores.json` round-trips to the scorecards.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_reporting.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): Markdown phase report with cost beside every number, results directory, ledger-row template`

### Task 14: `scry eval`, the committed matrices for P0–P5, and the no-constants check

**Files:**
- Create: `src/scry/evaluation/cli.py`, `tests/test_eval_cli.py`, `evals/p0-read.toml`, `evals/p0.toml`,
  `evals/p1.toml`, `evals/p2-grouponly.toml`, `evals/p2-transcribing.toml`, `evals/p3.toml`, `evals/p4.toml`,
  `evals/p5.toml`, `evals/README.md`
- Modify: `src/scry/cli.py` (`app.add_typer(eval_app, name="eval")`), `README.md` (one paragraph pointing at
  `evals/README.md`)

**Interfaces:**
- Produces the commands (each takes the matrix path first; `--root` defaults to `runs/eval`, `--results` to
  `docs/results`):
  - `scry eval expand MATRIX`: prints one line per run (name, stages, judged, fixed upstream) and validates every
    run's config; exit code 1 with the error on any `ValueError` or `ValidationError`. Spends nothing.
  - `scry eval run MATRIX [--only NAME] [--allow-dirty]`: Task 3; prints each outcome; exit code 1 when any run failed.
  - `scry eval status MATRIX`: name, status, stage seconds, dollars so far.
  - `scry eval judge MATRIX`: Task 7 over every run that has `answers.jsonl`; judge cache under the results directory.
  - `scry eval sheet MATRIX [--per-question 2] [--seed 0]`: writes `answer-sheet.md` and `answer-sheet.key.json`;
    refuses to overwrite a sheet that has any ticked box.
  - `scry eval labelsheet MATRIX [--frames-per-span 3] [--per-kind 12]`: first repeat of every annotating
    configuration; writes `label-sheet.md` and `label-sheet.key.json`; the same overwrite rule.
  - `scry eval score MATRIX`: writes every run's `scorecard.json`; reads the ticked sheets when they exist.
  - `scry eval report MATRIX`: scores, builds the noise table and the planned comparisons, writes the results files.

**The committed matrices** (the keys under `[axis.*]` are plan 2's and plan 3's config keys, P2 and P3; the test below
fails loudly if one does not exist, and only these files change then):

| File | Phase | Source; fixed upstream | Stages | Spans | Axes | Repeats | Runs |
|---|---|---|---|---|---|---|---|
| `p0-read.toml` | `p0read` | `runs/p0` | read | `full` 0-220 (ground truth), `smoke` 145-155 (popup frames 149, 151), `span2` 155-187 (ground truth) | — | 1 | 3 |
| `p0.toml` | `p0` | `runs/p0`; fixed `runs/eval/p0read/{span}-r1` | track | the same three | `margin`: `m000` 0.0, `m025` 0.25, `m050` 0.5, `m100` 1.0 (`"track.margin"`) | 1 | 12 |
| `p1.toml` | `p1` | `runs/p0` | read, track, annotate, interpret, summarize, index, ask | `smoke`, `span2` (ground truth, questions) | `base`: `transcribing` (`"annotate.transcribe" = true`), `grouponly` (`false`), `none` (`"annotate.mode" = "off"`) | 3 | 18 |
| `p2-grouponly.toml` | `p2g` | `runs/p0` | read, track, annotate | `smoke` | `base`: `grouponly`; `arm`: `A`–`D` (`"annotate.arm"`); `scale`: `s100`, `s050`, `s025` (`"annotate.scale"`); exclude `arm A` × `s100` (P1 holds it, three repeats) | 2 | 22 |
| `p2-transcribing.toml` | `p2t` | `runs/p0` | read, track, annotate | `smoke` | `base`: `transcribing`; `arm`: `A`–`D`; `scale`: `s100`, `s067`; the same exclusion | 2 | 14 |
| `p3.toml` | `p3` | `runs/p0` | as P1 | `smoke`, `span2` | `base`: `transcribing`, `grouponly`; `inc`: `on` (`"annotate.mode" = "incremental"`) | 3 | 12 |
| `p4.toml` | `p4` | `runs/p0` | read, track, annotate, interpret, summarize, index | `smoke` | `base`: one value (the mode chosen after P3; committed as `grouponly`); `pane`: `on`, `off` (`"annotate.pane"`; plan 2 allows it under arms A and D only) | 2 | 4 |
| `p5.toml` | `p5` | `runs/p0`; fixed `runs/eval/p1/{span}-grouponly-r{repeat}` | interpret, summarize, index, ask | `span2` | `base`: as P4; `images`: `crops` (`"interpret.images" = "crops"`) | 3 | 3 |

`p1.toml` compares `transcribing` with `grouponly`, `grouponly` with `none` and `transcribing` with `none`, and
carries the `[reference]` row of `runs/span2-before` (its recorded usage, 33 frames). The P2 screens stop at
`annotate`: they choose a referencing arm and a scale on guards, by-eye labels and cost, and "each mode's chosen point
on span 2" (spec §9 P2) is then run through the whole pipeline from a copy of `p1.toml`. The P2 files compare `{phase
= "p1", base = …}` with `b = "each"` and set `floor = "docs/results/p1/noise.json"`; `p3.toml` compares each base with
the same base of P1; `p5.toml` compares with `{phase = "p1", base = …}`. The run counts are the spec's (18; 22 + 14 =
36; 12; 4; 3). `evals/README.md` says how the files that depend on results are made: the P2 refinement and
chosen-point matrices (copy a file, replace the `scale` values or the spans and stages, new phase name), the base of
P4 and P5 (edit the single `base` value and the `fixed_from` template), P5's comparison of `ask` prompt wordings (N2:
it needs a prompt-variant key in `[ask]`; then a matrix with the upstream fixed to P1's runs, stages `["ask"]` and one
axis over that key), and P6 for the hold-out video (a copy of `p1.toml` with the hold-out's decode run as `source`, one
span covering it, its own ground-truth file in the same format if the owner lists its commands, no `[reference]`; θpix
and θmin are read from the `touched_share_low_half` guard).

**Rules:**
1. The CLI functions only parse arguments, call Tasks 2–13 and print; they hold no logic of their own.
2. `score` and `report` never call a model. `judge` is the only harness command besides `run` that can spend money.
3. **No per-video constants in code:** no file under `src/scry/evaluation/` contains a frame number of the sample,
   its length, or a string from it.

**Tests to write first** (`typer.testing.CliRunner`; stage functions replaced by fakes by monkeypatching
`scry.evaluation.runner.resolve`; a source run built as in Task 3):
- `test_expand_lists_runs_and_spends_nothing`: a two-repeat matrix → exit code 0, two run names in the output, no
  directory created under the root. A matrix with `"track.margn" = 1` → exit code 1 and `margn` in the output.
- `test_run_score_report_end_to_end_with_fake_stages`: `run` → exit code 0 and two `evalrun.json` with `status "done"`;
  `score` → two `scorecard.json`; `report` → `report.md`, `scores.json`, `noise.json`, `ledger-row.md` under
  `<results>/p9/`; `status` prints both names with `done`.
- `test_run_exit_code_on_failure`: a fake stage that raises → exit code 1, and the second run still ran.
- `test_sheet_refuses_to_overwrite_ticks`: write a sheet, tick one box, run `sheet` again → exit code 1, file unchanged.
- `test_committed_matrices_expand_to_the_planned_runs` (reads `evals/*.toml`; needs plans 2 and 3 landed): run counts
  `p0-read 3`, `p0 12`, `p1 18`, `p2-grouponly 22`, `p2-transcribing 14`, `p3 12`, `p4 4`, `p5 3`; `config_for`
  succeeds for every run; every run of `p1`, `p2*`, `p3`, `p4`, `p5` is `judged`, no run of `p0*` is; no
  matrix names a `source` or `fixed_from` outside `runs/`.
- `test_no_video_constants_in_code`: no file under `src/scry/evaluation/` matches `\b(145|149|151|155|187|220|221)\b`
  or contains `KodeKloud`, `msadmin`, `create-aks` or `span2` (case-insensitive).

- [ ] **Step 1:** Write the tests and the eight matrix files. Run `uv run pytest tests/test_eval_cli.py -q`. Expected:
  FAIL (`No such command 'eval'`).
- [ ] **Step 2:** Implement the commands; write `evals/README.md` and the README paragraph.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry eval expand evals/p1.toml` prints 18 runs and exits 0.
  `uv run scry eval --help` lists `expand`, `run`, `status`, `judge`, `sheet`, `labelsheet`, `score`, `report`.
- [ ] **Step 4:** Commit: `feat(eval): scry eval commands and the committed run matrices for P0–P5`

---

## Running a phase with the harness (the procedure, with P1 as the example)

Not a task: what the executor of a phase does once this plan has landed. Nothing here waits for an approval.

1. The matrix, the ground truth and the question file are committed **before** the phase runs; `git status` is clean.
   `uv run scry eval expand evals/p1.toml` → 18 runs, no error.
2. `uv run scry eval run evals/p1.toml` (about $55 by the spec's estimate; sequential; safe to re-issue after an
   interruption: finished runs are skipped, an interrupted one resumes and is flagged).
3. `uv run scry eval judge evals/p1.toml`, then `uv run scry eval sheet evals/p1.toml` and `uv run scry eval
   labelsheet evals/p1.toml`. The owner (or the executor, by eye, against the frames) ticks
   `docs/results/p1/answer-sheet.md` and `label-sheet.md`.
4. `uv run scry eval report evals/p1.toml` → `docs/results/p1/report.md`, `scores.json`, `noise.json`,
   `ledger-row.md`. Read the warnings first. Write the two capitalised cells of the ledger row, append it to
   `docs/decision-ledger.md`, commit the results directory and the ledger together, and report to the owner. The next
   phase starts without waiting.
5. Later phases set `floor = "docs/results/p1/noise.json"` so that their two-repeat screens are read against P1's
   measured noise as well as their own; finalists get more repeats by raising `repeats` in a copy of the matrix under
   a new phase name (a finished run's directory is never re-used for a changed spec).

## Decisions this plan makes (for the reviewers)

The spec is silent or looser on each of these; none is settled until reviewed. Under the owner's rule "simplify before
repairing", these are the parts a phase can run without, and so the first candidates to strike if a reviewer finds
them to be machinery ahead of evidence: the companions of *exact* (`exact_in_window`, `variant_only`, `nearest`; D3),
the two guards on plan 3's scorers (D4), the citation reading (D6), the `[reference]` row, `skip_stages`, and P0
expressed as matrices (D19). What a paid phase cannot run without: the matrix and the cold runner (Tasks 2, 3),
accounting (Task 1), the assembly of command scores (Task 4 rules 1–3, 6–8, 12–13), the question runner and its
scoring (Tasks 6–8), scorecards, noise and comparison (Tasks 10–12) and the report (Task 13).

- **D1. Where things live.** Code in `src/scry/evaluation/`, commands under `scry eval`, matrices in `evals/`
  (committed), run directories in `runs/eval/<phase>/<run>/` (git-ignored), results in `docs/results/<phase>/`
  (committed, with every scorecard in `scores.json`, so a report can be checked without the run directories).
- **D2. One definition of each command metric, and it is a sibling's.** The parser, *exact* for OCR and the
  first-appearance error are plan 1's; *found*, the submission error and *false run* are plan 3's ("covering its time"
  = the hit's `[t_start, t_end]` intersects `[first visible t, submitted t]`; the quoted command through the lexical
  search the agent's tool uses). This plan calls them and defines none of them again. Entries under four non-space
  characters (the answers `Y` and `y`) stay out of the *found* and *exact* rates as plan 1 ruled; they are covered by
  the submission metric and by question Q4.
- **D3. What this plan adds to *exact*.** Plan 1's function once per reader: `ocr`, `vlm` (the model's majority
  reading per lifetime, from plan 2's joined view) and `any`, which is the score that compares bases with different
  readers. The score follows the spec's words (no time condition); a companion `exact_in_window` and a flag list expose
  the case where only a later sighting of the same string matched. `variant_only` and `nearest` explain failures. A
  command that the screen wrapped over two boxes is not exact under this rule (none of the nine is); `nearest` shows it.
- **D4. Two guards on plan 3's submission scorers, without rescoring.** A one-letter answer's match is kept only on
  equality of `entered_text`; a false run whose claim is also an executed entry's matched submission is flagged
  `shared_claim` beside the unchanged score. Unmatched `submitted: yes` claims and `unclear` verdicts on submitting
  transitions are listed as information.
- **D5. Aggregates.** Time errors are reported as mean absolute values over the entries that have one, with the
  count; rates as `k/n`; per-unit 0/1 values feed the pairing.
- **D6. Citations of the agent are read from its prose** (frames, box refs, transition ids, times), because
  `AskResult` has no citation list (N1). They feed two guards and never an answer's label.
- **D7. "Weighs less" is order, not arithmetic.** No numeric weights. Two mechanical readings per comparison:
  commands (found, then exact.any; tie-breakers first-appearance error, submission error, false run) and questions
  (positive; tie-breaker negative). The spec does not say how the two relate, so they are not merged; guards and
  costs never enter either; the decision stays the owner's.
- **D8. The noise floor** is the largest absolute paired difference seen between two cold runs of the same
  configuration, pooled over both sides of a comparison and an earlier phase's floor file when the matrix names one;
  for means of repeats it is scaled by `sqrt((1/n_a + 1/n_b) / 2)`; a difference is `outside` only when it is strictly
  larger; without any repeat it is `unknown`; unjudged (model-free) runs have floor 0. It is a range, as ledger L42
  reports noise, not a significance test: with three repeats a maximum over three pairs is a crude estimate, and the
  report shows the repeats' values so the owner can see that.
- **D9. Pairing units.** Ground-truth entry for command metrics, never-run row for *false run*, question (keyed by
  id and text hash) for the question set, frame for label guards and `annotate` cost, change id for citations and
  `interpret` cost, the run for run-level numbers. Only units present in every run of both sides are paired; the rest
  are counted as dropped.
- **D10. Cost.** Prices, the 1.25 × cache-creation multiplier and the batch half-price are plan 3's `scry.costs`; an
  unknown model earns a warning here (N3). Added here: the run total as the larger of manifest usage and the private
  call cache's usage; `$ / video` as `$ / frame` times the source run's frame count, a linear projection that the
  report names as such; seconds per stage and per frame, timed by the runner; the question set's cost per question,
  outside `$ / video`; the judge's cost reported apart; the batch price shown beside the synchronous one.
- **D11. Cold, mechanically.** `subset` with a private cache; a symlinked or pre-filled cache is refused; any cache
  hit flags the run; runs are sequential. A `fixed_from` upstream is the only reuse of model outputs: copied files,
  never a shared cache; the stages that run still run cold, `{repeat}` gives each repeat its own upstream sample, and
  the report says what was not sampled.
- **D12. "Committed code, written before a phase runs", mechanically.** A judged matrix does not start on a dirty tree
  (code, matrices, ground truth); each run records the commit and a hash of the metric code; a scorecard built by
  different metric code says so at the top of the report.
- **D13. Question scoring.** Rubric lines are statements about the answer; a judge call decides each line, code
  derives `correct`, `partial`, `wrong` (1, 0.5, 0 for means; the counts are always shown). The judge is blind to the
  configuration, runs at low effort on the pipeline's model unless the matrix says otherwise, and is cached apart.
  The by-eye sample is two answers per question, rotating through the runs; by-eye verdicts replace the judge's;
  agreement is reported per rubric line and per label with a confusion table and every disagreement, with no
  threshold and no kappa. Citation validity and whether a citation falls in the evidence range are guards.
- **D14. By-eye label sheets.** The same evenly spaced frames plus the span's popup frames for every run; first repeat
  of each configuration; at most twelve items per kind, frame and run; blind run codes; precision by eye per kind and
  the owner's missed counts; no recall.
- **D15. Guards.** `box_stability`, `touched_share_low_half` and the unstable rate are plan 1's; "near-static" stays
  its rank rule; popup frames are named in the matrix; one-container share counts boxes after the join.
- **D16. The matrix format**: opaque dotted overrides validated against `Config` at expansion, so the harness names no
  pipeline key; names without hyphens; two equal axis values are an error; P2 reuses P1's full-scale arm-A runs, and
  the P2 screens stop at `annotate` (they choose an arm and a scale; the chosen points then run the whole pipeline).
- **D17. The question-file format** of `docs/ground-truth/span2-questions.md` and its parser's strictness.
- **D18. In-process stages and no TOML writer:** the runner passes `Config` objects and records the effective config
  as `config.json`.
- **D19. P0 through the harness** is expressed (`p0-read.toml`, `p0.toml`) so margins are compared by the same paired
  machinery; it does not replace plan 1's Task 16, whose by-eye reading of H1–H8 no harness can do.

## Self-review

- **Spec coverage (§9).** G1 → plan 1's parser, checked against the committed file in Task 4. G2 by eye → Task 9. Q →
  `span2-questions.md`, Tasks 6–8. Primary metrics → plan 3's *found* and plan 1's *exact*, assembled per reader in
  Task 4 rules 1–5. Secondary → Task 4 rules 6–12. Question set with lighter negatives → Tasks 6–8, Task 12 rule 9.
  Guards → Task 5, Task 9, Task 6 rule 12. Cost beside every number → Task 1, Task 10 rule 5, Task 12 rule 8, Task 13
  rule 1. Evidence rules: committed code → Task 3 rule 3, Task 10 rule 7; paired over the same frames → Task 12 rules
  1–3; noise floor first → Task 11, Task 12 rule 4, the `floor` key; two-repeat screening and added repeats → Task 11
  rule 4; no threshold → Task 13 rule 3; phases report as they finish → the procedure. Cold runs → Task 3 rule 2,
  Task 1 rule 5. Phases P0–P5 → Task 14's matrices; P6 and P5's prompt wording → `evals/README.md` (N2). Not covered by
  design: the by-eye reading of H1–H8 (plan 1 Task 16); `scry report` for one run (plans 1 and 3); the full-sample
  sync and batch runs after the phases (`run_cost` already shows the batch price).
- **Placeholders.** None in the tasks: every test names its fixture and expected values. The ledger row's two
  capitalised cells are part of the deliverable's format, written by a person after a phase.
- **Type consistency.** `RunSpec`, `Matrix`, `Span` (Task 2) are used in Tasks 3, 12–14; `evalrun.json`'s fields
  (Task 3) in Tasks 1, 10; `FrameLabels`, `LabelItem`, `AskOutcome`, `Adapters` (Tasks 5, 6, 9, 10) live in
  `adapters.py`, the only importer of the siblings' loaders, search index and `ask`; the siblings' scorers
  (`score_exact`, `score_found`, `score_submitted`, `score_false_run`, `estimate_cost`, `run_costs`) are called from
  Tasks 1, 4, 7, 10 and 13 under the names P1 and P3 give; `Question.key` (Task 6) is the unit key in Tasks 8, 10, 12;
  `Judgment` (Task 7) in Tasks 8, 10; `METRICS` names (Task 10) equal the `units` keys of Tasks 4, 5, 6, 9 and the
  orders of Task 12; `scaled_floor`, `same_config_diffs`, `floor_lookup` (Task 11) in Task 12.
- **Review focus.** Each of the five lines names its tests and tasks.
