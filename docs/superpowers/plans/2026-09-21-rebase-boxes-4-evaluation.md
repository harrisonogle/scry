# Re-base step 4: the evaluation harness, cut to what the first paid phase (P1) needs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **One deliberate adaptation of the writing-plans format: this plan contains NO implementation bodies and no test
> code.** The owner forbids code that exists anywhere except as the real implementation on the branch with its tests;
> no drafter or reviewer writes a prototype, a scratch implementation or a trial script, not even to check an idea. So
> every task gives: the files; the public interface (signatures, record fields, file formats, config keys); the
> behaviour as numbered rules; the tests to write FIRST, each named, with its concrete fixture and exact expected
> values (all arithmetic below was done by hand); the commands; the commit. The implementer writes the test code and
> the implementation on the branch from these. Reviewers of this plan read and reason; they do not execute anything.

> **Reconciled on 2026-09-21 with its review** (`docs/reviews/2026-09-21-rebase-plan4-review.md`, "accept with
> changes") under ledger L50. The first draft is commit `c23108d` (14 tasks); this is the review's lean list (9 tasks).
> Everything cut is either under "Deferred, with the phase that would need it" or under "Dropped outright", near the
> end, and can be restored from that commit.

**Goal:** Make P1 of the re-base proposal runnable and comparable: a committed run matrix expands into cold run
directories, a runner executes them, committed code scores them against the owner's command list, the question set is
asked through `ask` and judged blind against rubric lines, the noise between identical runs is measured, every
difference is marked as inside or outside that noise, and a Markdown report shows dollars per stage, per frame and
per video beside every quality number. Later phases add what they need when they are planned, from the previous
phase's results.

**Architecture:** A subpackage `scry.evaluation` beside the pipeline, reached through `scry eval …`. It never edits a
stage's file: it derives run directories with the existing `subset` tool, calls the stage entry points in-process,
and reads their records through one module of plain adapter functions (`adapters.py`), the only place that touches
the sibling plans' loaders, search and `ask`. Every measurement is a pure function over records, producing per-unit
values (per ground-truth entry, per question, per run) so that any two configurations can be paired over the same
units. The matrix file holds everything that is specific to a video or a phase; the code holds none of it.

**Tech stack:** Python ≥ 3.12 with `uv`; pydantic 2, typer, the Anthropic SDK through the existing `scry.providers`
(judge calls only), `tomllib`, SQLite FTS5 through the existing `scry.index`; pytest. No new dependencies.

**Spec:** `docs/proposals/2026-09-21-boxes-mode-rebase.md`, revision 3.1: §9 (Evaluation) is what this plan implements
for P1; §4 (principles 8 and 9), §5 (Records) and §2 (stages and files) are the contract with the sibling plans.
Ground truth: `docs/ground-truth/span2-commands.md` (accepted) and `docs/ground-truth/span2-questions.md` (a draft
for the owner to correct). Measured background: `docs/decision-ledger.md` L42 (identical cold runs differ) and L44 to
L46, L48 and L50 (the owner's standing rules while away; the reconciliations). Sibling plans: `…-1-read-track.md`
(landed on the branch), `…-3-interpret-summarize-index-ask.md` (reconciled, L48) and `…-2-annotate.md` (being
reconciled while this was written; see "Interface assumptions"). Executors read the spec with this plan.

**Order of execution:** after plan 1, plan 2 as far as arm A on every frame with the transcribing switch, the cost
accounting and the loaders that join labels (its Tasks 1 to 11 as drafted; not arms B to D, incremental annotation
or the pane label), and plan 3. Tasks 2 and 3 and the parser of Task 5 touch nothing beyond plan 1 and can be built
now; so can Task 8, whose tests build scorecards as dicts, once the `METRICS` table of Task 7 is written down. Task 1
needs only plan 2's provider task (`estimate_cost` pricing cache-creation tokens).

## Global Constraints

The owner's rulings and the coordinator's decisions (L50), binding on every task:

- **Cost is an outcome.** Every quality number in every report has dollars per frame and dollars per video beside
  it, and every stage its dollars. Cost comes from manifest usage, which plans 2 and 3 define as cold-equivalent (the
  sum over a stage's records, cache hits included), priced by `scry.costs`: cache-creation tokens at 1.25 × the input
  price, the batch price shown as half. This plan adds no second price list. An unknown model is priced as
  `claude-opus-5` with a warning, never an exception. The question set's cost is reported per question and outside
  dollars per video; the judge's cost is reported apart.
- **Primary scores** per executed command: *found* and *exact*, reported side by side with no order between them.
  **Secondary:** *submitted* and its error, the first-appearance error, and *false run*. In the question set the
  positive questions are primary and the negative ones secondary. "Weighs less" is where a number is printed; no code
  orders, weights or combines scores, and no report names a winner.
- **This plan owns the command metrics** (Task 4). Plan 1 supplies the parser and *exact* for one reader; plan 3
  defines none. **Every comparison with the command list is by frame number, never by seconds:** the list rounds
  times to two places, so a time window can exclude the very frame it names (N9).
- **No success threshold is pre-committed, anywhere.** No report says pass or fail. Fixed in advance is only what
  counts as evidence: metrics are computed by committed code written before a phase runs; the noise floor is measured
  from repeats; comparisons are paired over the same frames; a difference inside the noise is no difference. The only
  verdict words are `outside`, `inside` and `unknown` (of the noise), and `not comparable`; and every report says in
  words that with three repeats `outside` is weak evidence.
- **Runs are cold with repeats:** each run directory is derived with `subset` with a private, initially empty call
  cache, never a symlink; any cache hit in a run is flagged in its scorecard.
- **No human tick-sheet gates anything.** Answers are judged by a separate, blind, low-effort model call against the
  question's rubric lines, and code derives `correct`, `partial` or `wrong` from the per-line verdicts. `scores.json`
  keeps every answer with the judge's verdict and quote for each line, so the owner can audit the judge from committed
  data whenever he likes.
- **Label quality is judged by eye on samples.** There is no hand-made label ground truth and P1 builds nothing for
  it (see Deferred).
- **Persistence is never evidence that a command ran.** No metric reads a lifetime's duration or sighting count as
  evidence of execution; *submitted* and *false run* read only `interpret`'s `submitted` and `entered_text`.
- **No per-video constants in code.** Frame ranges, ground-truth paths and the source run live in `evals/*.toml`.
- Phases report as they finish; nothing in the harness waits for an approval or enforces a budget.
- **Simplify before repairing; no machinery pre-emptively; what matters is that it works** (ledger L44, spec §12).
  This plan is the cut. A later phase adds a mechanism when it is planned and only if its matrix needs it.

Engineering constraints:

- Work only on branch `rebase-boxes`. `uv run pytest` reports 0 failures after every commit.
- **Tests are light** (L44, L50). They pin the metric definitions, the cost arithmetic, the floor and the comparison
  verdicts, the matrix expansion, and a handful of behaviours whose failure would cost money or silently break an
  evidence rule (cold materialisation, resume, the blind judge, the two parsers, one end-to-end pass with fakes).
  Unit tests only: synthetic records written in the test, fake stage functions, fake providers, fake clocks. No test
  reads the sample video or a directory under `runs/`, calls the network or a model, or needs an API key. Three tests
  read committed documents (the two files under `docs/ground-truth/`, and `evals/p1.toml`) on purpose, to catch a
  silent edit. Test helpers are imported as top-level modules: `from fakes import …`, `from minirun import …`.
- Real code in the package with tests; no throwaway scripts. The harness writes only inside run directories it created
  (`evalrun.json`, `config.json`, `answers.jsonl`, `judgments.jsonl`, `scorecard.json`), the phase's judge cache, and
  the results directory; it never writes a stage's file and never writes under the matrix's `source`.
- Rounding: dollars 4 places, dollars per video 2, seconds 1, rates 4, means of frame errors 2, differences and
  floors 6.
- Commit messages end with the attribution lines the session supplies.

## Review Focus

Conditions most likely to bite a person using the harness; each has a test or a worked example in the task that owns
the code.

1. **A time the command list rounds.** `kubectl get nodes` is first seen at frame 180, which the list prints as
   702.03 s and the records hold as 702.0333… s. Expect it to be found and exact: frames are compared, never seconds
   (Task 4 worked example B, `test_found_by_frame_and_level`).
2. **The same string is an executed command and, later, a never-run suggestion** (`kubectl config current-context`,
   executed row 6 and never-run row 4). Expect a submission that `interpret` marks one transition late to score as one
   frame late and not as a false run, and a second claim of the text to be the false run (Task 4 worked example C,
   `test_claims_one_per_row`).
3. **A run is interrupted and resumed.** Expect finished runs to be skipped, the unfinished one to be finished and
   flagged `resumed`, its cache hits flagged, and its cost not under-reported, because manifest usage counts cache hits
   (Task 3 `test_failed_run_is_resumed_and_finished_runs_are_skipped`, Task 1
   `test_cache_hits_and_unknown_model_are_flagged`).
4. **Runs with pieces missing:** the no-annotation base has no `annotations.jsonl` and no second reader; an
   `interpret` call failed; the index was not built. Expect a scorecard with `null` sections and notes, never a crash,
   and comparisons that drop the missing units and say how many (Task 7
   `test_scorecard_full_and_with_pieces_missing`, Task 8 `test_missing_units_and_absent_metrics`).
5. **A typo in the matrix file:** a config key that does not exist, a stage that does not exist, one key set by two
   axes. Expect failure at expansion (`scry eval run --dry-run`), before a cent is spent (Task 2).

## File structure at the end of this plan

```
src/scry/
  cli.py                     gains the sub-command group `eval`                                                  (modified)
  evaluation/
    __init__.py
    accounting.py            dollars and seconds per stage, per frame and per video, from manifest usage
    matrix.py                evals/*.toml → Matrix → RunSpec list; config overlays validated at expansion
    runner.py                cold run directories via subset; stages in-process; evalrun.json; resume; commit recorded
    adapters.py              plain functions; the only module that touches the sibling plans' loaders, search and ask
    commands.py              found, exact per reader, first-appearance error, submitted, false run; per-unit values
    questions.py             question-file parser; the question runner through `ask`
    judge.py                 rubric scoring by a separate, blind model call; label derivation
    scorecard.py             one run → scorecard.json (scores, questions with answers and verdicts, cost, units, warnings)
    compare.py               the noise floor from repeats; paired comparison; inside / outside / unknown
    reporting.py             Markdown phase report, scores.json
    cli.py                   `scry eval run [--dry-run] [--only] | judge | report`
evals/p1.toml                the only committed matrix
docs/results/<phase>/        report.md scores.json (committed)
runs/eval/<phase>/<run>/     run directories; runs/eval/<phase>/judge-cache/ (git-ignored, like all of runs/)
tests/                       test_eval_accounting.py test_eval_matrix.py test_eval_runner.py test_eval_commands.py
                             test_eval_questions.py test_eval_judge.py test_eval_scorecard.py test_eval_compare.py
                             test_eval_cli.py
```

## Interface assumptions

Plan 1 has landed on the branch (`src/scry/groundtruth.py`, `schemas.py`, `run.py`, `subset.py`, `track/`); what is
listed for it below was read from the code. Plan 3 is reconciled (ledger L48) and was re-read; plan 2 was being
reconciled while this was written, so what is listed for it is the coordinator's decisions (L50 item 7) over its
draft, and wins over that draft. This plan is insulated from the rest: of a `Change` it reads `id`, `from_frame` and
`to_frame`; of a `Lifetime` it reads `id`, `text` and `first.frame` through plan 1's scorer; every use of plans 2 and
3 goes through `scry/evaluation/adapters.py`, so a renamed loader costs one adapter function, not a metric. The
values two tests assert on plan 3's Fixture M (four frames 10 to 13; lifetime `L4` `C:\src> git status` over frames
11 to 13, the model's majority reading the same; interpretation `T2`, 11→12, `git status`, `yes`) were checked
against the reconciled plan 3.

**Who defines what.** The ground-truth parser, `scorable`, *exact* for one reader and the first-appearance error are
plan 1's (`scry.groundtruth`). *Found*, *submitted* with its error, and *false run* are **this plan's** (Task 4);
plan 3 defines no metric. Pricing (cache-creation tokens, usage summed over retries) is `scry.costs`, made honest by
plan 2's provider task; the batch price is a halving done in Task 1. `scry report` (one run, read by eye, with the
track guards) belongs to plan 1. This plan adds what compares runs.

**Pinned by the sibling plans and consumed as written:**
- P1 (plan 1, from the code). `scry.groundtruth`: `Entry(n, text, first_frame, first_t, submitted_frame,
  submitted_t, frames)`; `parse_commands(md) -> (executed, never_run)` (an executed row's first pair of column 3 is
  its first frame, the last pair of column 4 its submitted frame; a never-run row lists its frames); `scorable(e)` (at
  least 4 non-space characters); `score_exact(entries, lifetimes) -> list[dict]` with keys `n, text, scorable, exact,
  matches, lifetime, first_frame, frame_error, t_error` (a case-sensitive substring test of `norm(text)` in the
  lifetime's majority reading; the earliest matching lifetime is reported; `frame_error` = its first frame minus the
  entry's); `exact_rate`. Records and loaders: `Change` (`id` `"T<n>"` numbered from 1 by position in the run,
  `from_frame`, `to_frame`), `Lifetime` (`id`, `text` the majority reading, `first`, `last`), `Run.load_frames/
  load_boxes/load_changes/load_lifetimes`, `Run.cache_dir`, `Run.stage_up_to_date`. `scry.subset.make_subset(src_root,
  out, frames, share_cache=True) -> Run`, never writing under `src_root`, keeping frame numbers, and writing `subset =
  {"source", "frames"}` into the manifest; `parse_frames`. Every config model rejects unknown keys. Stage entry
  points `scry.read.run_read`, `scry.track.stage.run_track`, each skipping itself when its inputs and config are
  unchanged. `runs/p0` holds the 221 decoded frames.
- P2 (plan 2). `scry.annotate.run_annotate(run, cfg, provider=None)`. `[annotate]` keys: `mode` (`"every_frame"`,
  `"incremental"` or `"off"`), `transcribe` (true or false), `scale` (the image scale; the overlay's scale key is
  gone). With `mode = "off"` the stage writes no file and a manifest entry with zero usage. `Run.load_labels() ->
  Labels | None`; `Labels.lifetime(id) -> LifetimeLabel | None` with `vlm`, the model's majority reading. Manifest
  `stages.annotate`: `usage` (four keys, summed over the records, cache hits included), `model`, `cache` (`hits`,
  `misses`), `calls`, `repairs`, `repair_counts`, `errors`, `failed_targets`. `scry.costs` after its provider task:
  `PRICES`, `estimate_cost(usage, model)` with cache-creation tokens at 1.25 × input and an unknown model at the
  `claude-opus-5` prices; usage summed over a call's retries. No sibling records a batch price (plan 3 A6, A9): a
  report halves, and Task 1 does. `tests/fakes.py`.
- P3 (plan 3, as reconciled under L48; its A9 lists what this plan reads). `scry.interpret.run_interpret`,
  `scry.summarize.run_summarize`, `scry.index.build_index`, each callable as `(run, cfg)`. `Interpretation` with `id`,
  `entered_text`, `submitted`, `error`; `Run.load_interpretations() -> dict[str, Interpretation]`. **`entered_text` is
  the user's whole input as the later frame shows it, without the prompt and without anything the application
  suggested, also when the typing was never seen** (its D2); *submitted* and *false run* depend on exactly this
  reading. Manifest `stages.interpret`: `usage`, `model`, `cache`, `errors`, `invalid_citations`, `submitted`;
  `stages.summarize`: `usage`, `model`. `scry.index.open_db`, `search(db, query, cfg.index, embedder=None)` returning
  hits with `node_id`, `level` and `frames` (first and last frame: a lifetime entry spans its first to its last frame,
  a transition entry its two frames, a frame entry every collapsed member); a query in double quotes stays a phrase.
  `scry.ask.ask(run, cfg, question, client=None) -> AskResult` with `text`, `turns`, `tool_calls`, `usage` (four
  keys, summed over turns), `cost_usd`, `stop`; no call cache, a fresh conversation per call; a failed API call is
  returned, not raised, with `stop "api_error"`. `[interpret] images` is `"scaled"` or `"full"`. The agent's
  prompt-variant registry is deferred in plan 3, so nothing here reads `[ask] prompt`. `scry run`'s stage order is
  `decode, outline, read, track, annotate, interpret, summarize, index`; the harness starts at `read`, on a directory
  `subset` derived from decoded frames, and never runs `outline`. Test helpers `tests/minirun.py` (`mini_run(tmp_path,
  labels=False)`, `mini_interpretations(run)`; its Fixture M) and `tests/fakes.py`, imported as top-level modules
  (`from minirun import …`, `from fakes import …`; `pythonpath = ["tests"]` in `pyproject.toml`, added by whichever
  plan lands first).

**Notes that remain** (the draft's N1, N2 and N5 were stale and are removed; N4 and N7 are resolved as stated):
- N3. `estimate_cost` prices an unknown model as `claude-opus-5` without saying so, and plan 3's fakes rely on that
  with `"fake-model"`. The harness adds the warning (Task 1 rule 3) and never raises.
- N4. The command metrics are this plan's (Task 4): one rule each, compared by frame.
- N6. Stage wall time: the harness calls the stage functions directly and times them itself (`evalrun.json`).
- N7. A stage's manifest `usage` counts cache hits (plan 2 D23, plan 3 D18: "what a cold run would pay"), so a resumed
  run cannot under-report and the manifest is the only cost source.
- N8. The hold-out video's command list, if the owner writes one, uses the format of `span2-commands.md`, so plan 1's
  parser reads it unchanged.
- N9. The command list prints `t_settled` to two places; the records carry the full value (frame 180: 702.03 in the
  list, 702.0333… in `frames.jsonl`). No rule in this plan compares the list's seconds with a record's.

---

### Task 1: Dollars and seconds per stage, per frame, per video

**Files:**
- Create: `src/scry/evaluation/__init__.py`, `src/scry/evaluation/accounting.py`, `tests/test_eval_accounting.py`

**Interfaces:**
- Consumes: `scry.costs.PRICES`, `estimate_cost(usage, model)` (P2: cache-creation tokens priced at 1.25 × input).
- Produces:
  - `BATCH_PRICE_SHARE = 0.5`: the Batch API's list discount, the one price fact this plan holds. Plan 3 records no
    batch price ("a report shows the batch price by halving", its A9), so the halving is done here
  - `projection_frames(manifest: dict) -> int | None`
  - `cost_summary(manifest: dict, stage_seconds: dict[str, float], frames: int, projection: int | None,
    default_model: str) -> dict` (named apart from plan 3's `run_costs`, which feeds `scry run`'s summary)

**Rules:**
1. `projection_frames`: the manifest's `subset.source` names the run the directory was derived from; return that
   run's `stages.decode.emitted` (falling back to `stages.stage1.emitted` for a pre-re-base source). No `subset` key →
   the manifest's own `stages.decode.emitted`. Nothing found → `None`.
2. `cost_summary` reads the manifest and nothing else (N7). For every `stages.<name>` entry that has a `usage` dict,
   with `model = entry.get("model") or default_model`: `dollars = estimate_cost(usage, model)` and `dollars_batch =
   round(dollars × BATCH_PRICE_SHARE, 4)`. Result: `{"frames", "projection_frames", "dollars", "dollars_batch",
   "per_frame", "per_video", "seconds", "seconds_per_frame", "cache_hits", "by_stage": {stage: {"dollars",
   "dollars_batch", "per_frame", "per_video", "seconds", "calls", "model", "usage"}}, "warnings": [str]}`. Every stage
   in the manifest or in `stage_seconds` has a `by_stage` row (`dollars` 0.0 without usage); `calls` is the entry's
   `calls`, else its `cache.misses`, else `None`. `dollars` is the sum over the stages and `dollars_batch` half of
   it. `frames` is the argument (the run directory's frame count), not the manifest's.
3. A stage whose `model` is not a key of `PRICES` gets the warning `no list price for <model>: priced as
   claude-opus-5` (`estimate_cost` falls back silently, N3). Never an exception.
4. `cache_hits` is the sum of the stages' `cache.hits`; each stage with hits adds the warning `"<n> cache hits in
   <stage>"`. Whether a run *is* cold is a structural fact the runner records (Task 3 rule 2); hits are what a resume,
   or identical inputs inside one run, leave behind, and the scorecard flags them.
5. `per_frame = dollars / frames`; `per_video = per_frame × projection` (`None` without a projection), for the run and
   for each stage; the projection is linear and every report says so. `seconds` sums `stage_seconds`. `frames == 0`
   gives `None` rates, no exception.
6. The cost of the question set and of the judge is not part of `cost_summary`: Tasks 5 and 6 record it per question.

**Tests to write first:**
- `test_cost_per_stage_frame_and_video`: manifest stages `read` (no usage), `annotate` (`usage` input 100_000, output
  20_000, cache creation 8_000, cache read 40_000; `model "claude-opus-5"`; `calls 10`; `cache {"hits": 0, "misses":
  10}`), `interpret` (input 30_000, output 4_000; same model; `cache {"hits": 0, "misses": 9}`); `stage_seconds
  {"read": 50.0, "annotate": 120.0, "interpret": 30.0}`; `frames 10`, `projection 200` → `by_stage.annotate.dollars
  1.07` (0.50 + 0.50 + 0.05 + 0.02), `by_stage.annotate.dollars_batch 0.535`, `by_stage.annotate.per_frame 0.107`,
  `by_stage.annotate.per_video 21.4`, `by_stage.annotate.calls 10`, `by_stage.interpret.dollars 0.25` (0.15 + 0.10),
  `by_stage.interpret.dollars_batch 0.125`, `by_stage.interpret.calls 9`, `by_stage.read.dollars 0.0`, `dollars 1.32`,
  `dollars_batch 0.66`, `per_frame 0.132`, `per_video 26.4`, `seconds 200.0`, `seconds_per_frame 20.0`, `cache_hits
  0`, `warnings []`.
- `test_cache_hits_and_unknown_model_are_flagged`: the same with `interpret`'s `cache` `{"hits": 3, "misses": 6}` and
  `annotate`'s `model` `"claude-nope"` → `cache_hits 3`, a warning containing `3 cache hits in interpret`, a warning
  containing `claude-nope` and `priced as claude-opus-5`, `by_stage.annotate.dollars` still `1.07`, no exception.
- `test_projection_frames_and_zero_frames`: a source manifest with `stages.decode.emitted = 4` and a derived manifest
  with `subset = {"source": <that directory>, "frames": [1, 2]}` → `4`; a source with only `stages.stage1.emitted = 7`
  → `7`; neither → `None`. `cost_summary` with `frames 0` → `per_frame None`, `per_video None`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_accounting.py -q`. Expected: FAIL (`No module
  named 'scry.evaluation'`).
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): dollars and seconds per stage, per frame and per video, from manifest usage`

### Task 2: The run matrix

**Files:**
- Create: `src/scry/evaluation/matrix.py`, `tests/test_eval_matrix.py`

**Interfaces:**
- Consumes: `scry.config.Config`; `scry.subset.parse_frames`.
- Produces:
  - `STAGE_ORDER = ("read", "track", "annotate", "interpret", "summarize", "index", "ask")`
  - `@dataclass(frozen=True) Span`: `name: str`, `frames: tuple[int, int]`, `ground_truth: Path | None`, `questions:
    Path | None`
  - `@dataclass(frozen=True) RunSpec`: `phase: str`, `name: str`, `config_id: str`, `span: Span`, `values: dict[str,
    str]` (axis → value name, axis order), `repeat: int`, `overrides: dict[str, object]`, `stages: tuple[str, ...]`
  - `@dataclass Matrix`: `phase`, `path: Path`, `source: Path`, `base_config: Path`, `stages: tuple[str, ...]`,
    `repeats: int`, `spans: dict[str, Span]`, `axes: dict[str, dict[str, dict]]`
  - `load_matrix(path: Path) -> Matrix`; `expand(m: Matrix) -> list[RunSpec]`; `apply_overrides(base: dict, overrides:
    dict[str, object]) -> dict`; `config_for(m: Matrix, spec: RunSpec) -> Config`

**The file format** (`evals/<phase>.toml`; everything specific to a video or a phase lives here):

```toml
phase = "px"                       # run directories go under runs/eval/<phase>/
source = "runs/p0"                 # a run directory with decode's frames; never written
base_config = "scry.toml"          # optional, this is the default
stages = ["read", "track", "annotate", "interpret", "summarize", "index", "ask"]
repeats = 3

[spans.span2]
frames = "155-187"
ground_truth = "docs/ground-truth/span2-commands.md"     # optional: command metrics are scored on this span
questions = "docs/ground-truth/span2-questions.md"       # optional: "ask" runs on this span only

[axis.base.transcribing]           # [axis.<axis>.<value>]: dotted config keys, quoted
"annotate.transcribe" = true
```

**Rules:**
1. Unknown top-level keys, unknown span keys and a missing `phase`, `source`, `stages`, `repeats` or `spans` raise
   `ValueError` naming the key. `repeats ≥ 1`. Paths are kept as written (relative to the working directory).
2. Expansion order: spans in file order × the cartesian product of the axes in file order, values in file order ×
   repeats `1..repeats`. `config_id = "-".join([span, *values])`; `name = config_id + f"-r{repeat}"`. With no axes the
   config id is the span name. Nothing parses a run name: `evalrun.json` holds the values.
3. `overrides` is the union of the chosen values' tables; a key set by two axes raises `ValueError` naming the key and
   both axes. Effective `stages` = the matrix's stages, in `STAGE_ORDER` whatever order the file lists them in, minus
   `"ask"` on a span without `questions`. A stage name outside `STAGE_ORDER` raises.
4. `apply_overrides` deep-copies `base` and sets each dotted path; a path that runs through a non-table raises
   `ValueError`. `config_for` loads `base_config` with `tomllib`, applies the overrides and returns
   `Config.model_validate(...)`; an unknown key therefore raises pydantic's `ValidationError` at expansion time.
   The harness never names a pipeline config key in code.

**Tests to write first** (the matrix text is written to `tmp_path`; the config keys used exist after plan 1):

```toml
phase = "p9"
source = "SRC"
stages = ["track", "read", "annotate", "ask"]
repeats = 2
[spans.smoke]
frames = "1-2"
[spans.span2]
frames = "2-3"
ground_truth = "gt.md"
questions = "q.md"
[axis.base.big]
"model.max_tokens" = 16000
[axis.base.small]
"model.max_tokens" = 8000
[axis.margin.m050]
"track.margin" = 0.5
[axis.margin.m025]
"track.margin" = 0.25
```

- `test_expand_order_names_and_stages`: 16 specs (2 spans × 2 × 2 × 2 repeats). `names[:3] == ["smoke-big-m050-r1",
  "smoke-big-m050-r2", "smoke-big-m025-r1"]`; `names[-1] == "span2-small-m025-r2"`. `smoke-big-m050-r1`: `config_id
  "smoke-big-m050"`, `stages ("read", "track", "annotate")` (pipeline order; no questions on `smoke`), `overrides
  {"model.max_tokens": 16000, "track.margin": 0.5}`, `span.frames (1, 2)`, `values {"base": "big", "margin": "m050"}`.
  `span2-big-m050-r1`: `stages ("read", "track", "annotate", "ask")`.
- `test_config_for_applies_overrides_and_rejects_unknown_keys`: overrides `{"track.margin": 0.25, "model.max_tokens":
  8000}` → `cfg.track.margin == 0.25`, `cfg.model.max_tokens == 8000`, every other value the base's. `{"track.margn":
  1}` → `pydantic.ValidationError`. `{"track.margin.x": 1}` → `ValueError`.
- `test_bad_keys_are_refused_at_load`: `stages = ["read", "perceive"]` → `ValueError` containing `perceive`; a
  top-level key `repeat = 3` → `ValueError` containing `repeat`; `base.big` also setting `"track.margin" = 0.5` →
  `ValueError` containing `track.margin`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_matrix.py -q`. Expected: FAIL (`No module named
  'scry.evaluation.matrix'`).
- [ ] **Step 2:** Implement rules 1–4.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): run matrix: spans × axes × repeats, config overlays validated at expansion`

### Task 3: The runner: cold run directories, stages in-process, timing, resume

**Files:**
- Create: `src/scry/evaluation/runner.py`, `tests/test_eval_runner.py`

**Interfaces:**
- Consumes: `Matrix`, `RunSpec`, `config_for` (Task 2); `make_subset`, `Run` (P1); the stage entry points of P1, P2
  and P3; `run_questions` (Task 5) for the pseudo-stage `ask`, imported lazily.
- Produces:
  - `STAGE_FUNCS: dict[str, str]` = `{"read": "scry.read:run_read", "track": "scry.track.stage:run_track", "annotate":
    "scry.annotate:run_annotate", "interpret": "scry.interpret:run_interpret", "summarize":
    "scry.summarize:run_summarize", "index": "scry.index:build_index"}`; `resolve(stage: str) -> Callable[[Run, Config],
    None]` imports the named function when first asked (tests replace `resolve` or pass `stage_funcs`)
  - `code_identity(repo: Path) -> dict` with `git_commit: str | None` and `git_dirty: bool`
  - `@dataclass RunOutcome`: `name`, `status: Literal["done", "failed", "skipped"]`, `seconds: dict[str, float]`,
    `error: str | None`
  - `materialise(m: Matrix, spec: RunSpec, root: Path, identity: dict) -> Run`
  - `execute(m: Matrix, spec: RunSpec, root: Path, identity: dict, stage_funcs: dict[str, Callable] | None = None,
    clock: Callable[[], float] = time.perf_counter) -> RunOutcome`
  - `run_matrix(m: Matrix, root: Path, only: str | None = None, stage_funcs=None, clock=…, identity: dict | None =
    None) -> list[RunOutcome]`
  - the file `evalrun.json` in each run directory: `{"phase", "name", "config_id", "span": {"name", "frames",
    "ground_truth", "questions"}, "values", "repeat", "overrides", "stages", "matrix": str, "spec_hash", "code":
    {"git_commit", "git_dirty"}, "cold": bool, "started", "finished", "status": "new" | "running" | "done" | "failed",
    "resumed": bool, "seconds": {stage: float}, "error"}`; and `config.json` = `config_for(...).model_dump()`

**Rules:**
1. The run directory is `root / spec.phase / spec.name`. A fresh one is made by `make_subset(m.source, dir,
   spec.span.frames, share_cache=False)`; then `evalrun.json` (`status "new"`) and `config.json` are written.
   `spec_hash = sha256_obj` of the spec's name, span, overrides and stages. An existing directory whose `evalrun.json`
   has the same `spec_hash` is reused; a different hash raises `ValueError` (the matrix changed under a run: choose a
   new phase name or delete the directory).
2. **Cold.** `materialise` records `cold true` when `run.cache_dir` is a real directory (`is_symlink()` false) and
   empty. Before any stage runs, a symlinked cache raises `RuntimeError("a run that judges a model call must not share
   a call cache")`. Nothing in the harness ever passes `share_cache=True` or writes into another run's cache.
3. **The code is recorded, never refused.** `code_identity`: `git rev-parse HEAD`, and whether `git status
   --porcelain` prints anything; `git` missing → `None` and `False`. Stored in `evalrun.json` when the run starts.
   Implementation agents work in this tree in parallel, so a dirty tree is normal; scoring is free and `report`
   rescores every run it reads, so all scorecards of a report are scored by the same code by construction.
4. `execute` runs the effective stages in order with the run's `Config`, timing each with `clock` (rounded to 0.1 s;
   a stage's seconds accumulate over attempts; a stage that raised adds nothing) and rewriting `evalrun.json`
   atomically after each stage. The pseudo-stage `ask` calls `run_questions(run, cfg, spec.span.questions)`. An
   exception stops this run: `status "failed"`, `error = "<Type>: <message>"[:500]`, later stages not run.
   `run_matrix` goes on to the next run and returns every outcome. Inside one process runs are sequential; `--only`
   lets the coordinator start several processes side by side, and the phase's ledger row then says that wall times
   are not comparable.
5. **Resume.** `status "done"` → outcome `skipped`. Anything else → the whole stage list is called again with
   `resumed true`: each pipeline stage skips itself when its inputs and config are unchanged, an interrupted stage
   finds its paid calls in the run's private cache, its manifest usage stays cold-equivalent (N7), and the question
   runner keeps the answers it has (Task 5 rule 9).
6. `only` restricts `run_matrix` to the spec with that name.

**Tests to write first** (a helper builds a source run under `tmp_path / "src"` as `tests/test_subset.py` does:
`frames.jsonl` with `Frame`s 0–3, four 8×8 PNGs, a manifest with `video_id` and `stages.decode`, and one file
`cache/k.json`; fake stage functions append their name to a list; a fake clock makes every stage call measure 1.5 s;
`identity = {"git_commit": "abc", "git_dirty": True}`):
- `test_materialise_is_cold`: matrix `p9`, span `smoke` `1-2`, no axes → directory `root/p9/smoke-r1`; its `cache` is a
  directory, not a symlink, and empty; `frames/00001.png` and `00002.png` exist and `00000.png` does not;
  `evalrun.json` has `name "smoke-r1"`, `status "new"`, `cold True`, `code {"git_commit": "abc", "git_dirty": True}`;
  `config.json` exists; the listing of `src` is unchanged. Replacing the run's `cache` directory with a symlink to the
  source's → `execute` raises `RuntimeError` containing `share a call cache`. Expanding the same matrix with an added
  override and materialising again → `ValueError`.
- `test_failed_run_is_resumed_and_finished_runs_are_skipped`: stages `read, track`, two repeats; the fake `track`
  raises `ValueError("boom")` on its first call only → outcomes `[("smoke-r1", "failed"), ("smoke-r2", "done")]`; the
  first has `error "ValueError: boom"` and `seconds {"read": 1.5}`; the second `seconds {"read": 1.5, "track": 1.5}`.
  Running the matrix again → the second pass calls `["read", "track"]` (the fakes do not skip themselves as real
  stages do) for `smoke-r1` only; outcomes `[("smoke-r1", "done"), ("smoke-r2", "skipped")]`; `smoke-r1/evalrun.json`
  has `status "done"`, `resumed true`, `seconds {"read": 3.0, "track": 1.5}`, `finished` set.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_runner.py -q`. Expected: FAIL (`No module named
  'scry.evaluation.runner'`).
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): runner: cold run directories from subset, in-process stages, timing, resume, commit recorded`

### Task 4: The command metrics: found, exact per reader, first appearance, submitted, false run

**Files:**
- Create: `src/scry/evaluation/commands.py`, `src/scry/evaluation/adapters.py`, `tests/test_eval_commands.py`

**Interfaces:**
- Consumes: `Entry`, `parse_commands`, `scorable`, `score_exact` (P1); `Interpretation`, `Run.load_interpretations`,
  `open_db`, `search` (P3); `Run.load_labels`, `Labels.lifetime` (P2); `scry.textdiff.norm`.
- Produces, in `adapters.py` (plain functions of a few lines each; the rest of the package reaches the siblings only
  through this module, and it imports their modules inside the functions, so the package imports before plans 2 and
  3 have landed):
  - `lifetimes(run) -> list[Lifetime]`; `changes(run) -> list[Change]`; `interpretations(run) -> dict[str,
    Interpretation]` (`{}` when the file is absent)
  - `vlm_majority(run) -> dict[str, str]`: lifetime id → `Labels.lifetime(id).vlm` where it is not `None`; `{}`
    without labels or without transcription
  - `search_fn(run, cfg) -> Callable[[str], list[dict]] | None`: `None` when `index.sqlite` is absent; otherwise a
    function calling `search(db, query, cfg.index, embedder=None)`, the agent's lexical search with no filter
- Produces, in `commands.py`:
  - `COUNTING_LEVELS = ("lifetime", "frame", "transition")`
  - `window(e: Entry) -> tuple[int, int] | None`
  - `score_found(entries: list[Entry], hits_for: Callable[[str], list[dict]]) -> list[dict]`
  - `reader_views(lifetimes: list[Lifetime], vlm: dict[str, str]) -> dict[str, list[Lifetime]]`
  - `score_exact_by_reader(entries, views) -> list[dict]`
  - `claims(changes: list[Change], interps: dict[str, Interpretation]) -> list[dict]`
  - `score_claims(executed, never_run, claims) -> tuple[list[dict], list[dict]]` (submission rows, false-run rows)
  - `command_scores(executed, never_run, found_rows, exact_rows, submit_rows, false_rows) -> dict` (pure assembly;
    `found_rows`, and `submit_rows` with `false_rows`, may be `None`)
  - `score_commands(run, cfg, ground_truth: Path) -> dict | None` (parses the file, reads the records through the
    adapters, calls the scorers, then `command_scores`; `None` when the run has no lifetimes)

**Rules — found (primary).** "A lexical search for the command's exact text returns an entry whose frame range
includes the list's first-visible frame or any frame up to its submitted frame."
1. `window(e)` = `(min, max)` of the entry's `first_frame` and `submitted_frame` that are not `None`; `None` when both
   are. Frame numbers only (N9).
2. Found is scored for the scorable executed entries that have a window. The query is the entry's text between
   double quotes, given to `hits_for`. A hit *covers* the entry when `hit["frames"][0] ≤ window[1]` and
   `hit["frames"][1] ≥ window[0]` (a transition entry covers both of its frames). The entry is **found** when some
   covering hit has a level in `COUNTING_LEVELS`. A step, section, video or chapter entry spans many frames, so its
   range says nothing about where the command was; such a hit never counts, and is shown instead. Row: `{"n", "text",
   "scorable", "found": bool | None, "rank", "level", "node_id"}`: `rank` (1-based position in the hit list) and
   `node_id` of the first covering hit at a counting level; `level` is that hit's level, or, when not found, the level
   of the first covering hit of any level (`found False, level "step"` reads "only a summary quotes it"), else `None`.
   `found None` for an entry that is not scorable or has no window, and no search is made for it. A command that
   itself contains a double quote is outside this rule until a list holds one.

**Rules — exact, per reader (primary; spec §9: "some lifetime's majority reading contains it exactly, per reader"):**
3. `reader_views`: `"ocr"` is the lifetimes as loaded. `"vlm"`, present only when `vlm` is non-empty, holds for every
   lifetime id in `vlm` a copy with `text` replaced by the model's majority reading (`model_copy(update=…)`).
4. For each view call plan 1's `score_exact(executed, view)`; merge by `n` into `{"n", "text", "scorable", "exact":
   {"ocr": bool, "vlm": bool, "any": bool}, "lifetime": {reader: id | None}, "first_frame_error": {reader: int | None,
   "any": int | None}, "first_t_error": {reader: float | None}}`. `any` is true when any reader is; the `vlm` keys are
   absent without a second reader. `exact_rate[reader]` counts scorable executed entries, as plan 1's `exact_rate`
   does. `exact.any` is what compares bases that have different readers; it can only tie or rise with a second
   reader, so reports present it as what the second reading adds, at its price, beside `exact.ocr`, not as a contest.

**Rules — first-appearance error (secondary):**
5. Per reader, plan 1's `frame_error` (signed, positive = the record starts late); `first_frame_error["any"]` is the
   value with the smallest absolute among the readers that are exact, a tie going to `ocr`. Aggregate per reader and
   for `any`: `first_frame_error_abs_mean = round(mean(|error|), 2)` over scorable entries that have a value, with
   their count. Plan 1's `t_error` rides along in the row for a person reading one run; it is never a unit and never
   compared.

**Rules — submitted and false run (secondary; they read `submitted` and `entered_text` and nothing else):**
6. A **claim** is a change whose interpretation has `submitted == "yes"`, no `error`, and an `entered_text` that is
   not blank: `{"change": id, "to_frame": the change's later frame, "text": norm(entered_text)}`, in change order.
7. **Submitted.** Executed entries, in list order, scorable or not, each take one claim: among the claims not yet
   taken whose `text == norm(entry.text)` (case-sensitive, like *exact*), the one whose `to_frame` is nearest the
   entry's `submitted_frame`, a tie going to the earlier (with no `submitted_frame`, the earliest). Row: `{"n", "text",
   "scorable", "submitted": bool, "claim": change id | None, "submit_frame_error": to_frame − submitted_frame | None}`
   (signed, positive = marked late).
8. **False run.** Never-run rows, in file order, each take the earliest claim not yet taken whose text equals the
   row's text: `{"text", "false_run": bool, "claim": change id | None}`. One claim per ground-truth row, and no frame
   condition: equality already keeps `Y`, `y` and every command apart, and a claim taken by an executed row cannot
   also charge a never-run row that shows the same text.
9. Rates: `submitted = (scorable entries with a claim, scorable executed entries with a submitted_frame)`;
   `submit_frame_error_abs_mean` over the scorable entries with a claim, with their count; `false_run = (rows with a
   claim, never-run rows)`. **The one-letter answers `Y` and `y`** (not `scorable`, ledger L46) take part in rule 7 and
   are shown in the rows; they enter no rate and no unit of any metric: reported, not rated.

**Rules — assembly:**
10. `command_scores` returns `{"entries": [rows merged by n: the keys of rules 2, 4 and 7], "never_run": [...],
    "rates": {"found", "exact": {reader: (k, n)}, "submitted", "false_run"}, "first_frame_error_abs_mean": {reader:
    …}, "submit_frame_error_abs_mean", "units": {...}}`. `units` maps metric name → unit → value: `found`,
    `exact.ocr`, `exact.vlm`, `exact.any`, `submitted` (unit = the entry's `n` as a string; scorable entries; 1.0 or
    0.0), `first_frame_error_abs.any`, `submit_frame_error_abs` (scorable entries that have a value), `false_run`
    (unit `"N<i>"`, the never-run row's 1-based position). A `None` row list leaves its rates `None` and its metrics
    out of `units` (no index: no `found`; no interpretations: no `submitted`, `submit_frame_error_abs`, `false_run`).
11. Nothing here reads `sightings`, `last − first` or any other duration as evidence that a command ran.

**Worked examples, by hand, on `docs/ground-truth/span2-commands.md`.** Lifetimes are the free phase's real records
(`runs/p0`, the branch's `read` and `track`; the ids are that run's). No paid run exists yet, so the interpretations
are supposed, to exercise the rules. In a run over frames 155 to 187 the changes are `T1` (155→156) to `T32`
(186→187), so `T22` is 176→177, `T23` 177→178 and `T25` 179→180.

- **A. Executed entry 6, `kubectl config current-context`.** Column 3's first pair is `175, 674.23`, column 4's last
  pair `177, 677.13`: first frame 175, submitted frame 177; 28 non-space characters, scorable; window (175, 177).
  *Exact* (OCR): lifetime `L1264` has the majority reading `PS C:\Users\msadmin> kubectl config current-context`
  (sighted at 176 to 181; at 175, with the grey suggestion on the line, OCR read `PSC:\Users\msadmin> kubectl
  configcurrent-context`, a variant of the same lifetime), first frame 175, last frame 181; `L1454` (185 to 187, after
  the portal pages) reads the same. The text is a substring of both majorities: exact, 2 matches, the earliest is
  `L1264`, `first_frame_error` = 175 − 175 = 0. *Found*: the lifetime entry of `L1264` spans frames (175, 181); 175 ≤
  177 and 181 ≥ 175, so it covers, at a counting level: found. The entry of `L1454`, (185, 187), does not cover (185 >
  177); a hit on the video summary, (155, 187), would cover and not count. *Submitted*: suppose `T22` has
  `entered_text "kubectl config current-context"`, `submitted "yes"`. It is the only claim with that text; entry 6
  takes it; `submit_frame_error` = 177 − 177 = 0.
- **B. Executed entry 7, `kubectl get nodes`, never seen being typed.** Column 3's first pair is `180, 702.03` (`179
  shows …` is not a frame-and-seconds pair); column 4 holds `179, 699.70` and `180, 702.03`, and the last pair is the
  submitted one: first frame 180, submitted frame 180; window (180, 180). By seconds this entry could never be found:
  the list prints 702.03, frame 180's `t_settled` is 702.0333…, and a lifetime that starts at frame 180 starts 3 ms
  after the window [702.03, 702.03] has closed. By frames: *exact*, `L1275` reads `PS C:\Users\msadmin> kubectl get
  nodes` over frames 180 to 181 (`L1456` again at 185 to 187): exact, `first_frame_error` = 180 − 180 = 0. *Found*:
  `L1275`'s entry spans (180, 181); 180 ≤ 180 and 181 ≥ 180: found; the transition entry of `T25`, (179, 180), and the
  frame entry of 180 cover it too. *Submitted*: plan 3's D2 has `entered_text` hold the whole input as the later
  frame shows it even when the typing was never seen, so the expected claim is `T25` with `entered_text "kubectl get
  nodes"`: `submit_frame_error` = 180 − 180 = 0. If `interpret` writes `kubectl get` there (what frame 179 showed), no
  claim has the entry's text: `submitted False`, a fair miss.
- **C. Never-run row 4, `kubectl config current-context` (second showing, frame 178).** Its text equals executed
  entry 6's. (1) The only claim with that text is `T22`: entry 6 took it (A), nothing is left, `false_run False`.
  (2) `interpret` marks the true submission one transition late, on `T23` (177→178), and not on `T22`: entry 6 takes
  `T23`, `submit_frame_error` = 178 − 177 = +1, nothing is left, row 4 is still not a false run. A frame condition
  would have charged row 4 here, because 178 is its own frame. (3) Both `T22` and `T23` claim the text: entry 6 takes
  the nearer (|177 − 177| = 0 against |178 − 177| = 1), `T23` is left over, row 4 takes it: `false_run True`, `claim
  "T23"`. Never-run row 1 (`az login`, frame 155) shows why there is no frame condition at all: in a span-2 run the
  transition 154→155 is outside the span, and a claim of `az login` on `T1` (155→156) is a false run by text alone.
- **`Y` and `y`** (entries 4 and 5): one non-space character each, not scorable. They take claims by case-sensitive
  equality (a claim `y` on 169→170 does not match `Y`), their rows are shown, and they enter no rate.

**Tests to write first.** Shared fixture, built as objects (not parsed): executed `E1` `n 1` `"az account show"` first
frame 157, submitted 158; `E2` `n 2` `"az configure --defaults group=RG1"` first 161, submitted 164; `E3` `n 3` `"y"`
first 170, submitted 171; `E4` `n 4` `"kubectl config current-context"` first 175, submitted 177. Never run: `N1` `"az
login"` frames `[155]`; `N2` `"kubectl config current-context"` frames `[178]`.
- `test_found_by_frame_and_level`: `hits_for` looks the query up in a dict and records what it was asked. `"az account
  show"` (in double quotes, like every query here) → `[{"node_id": "v:V", "level": "video", "frames": [155, 187]},
  {"node_id": "v:L1", "level": "lifetime", "frames": [157, 186]}]` → E1 `found True`, `rank 2`, `level "lifetime"`,
  `node_id "v:L1"`. E2's query → `[{"node_id": "v:S3", "level": "step", "frames": [160, 165]}]` → `found False`, `rank
  None`, `node_id None`, `level "step"`; with `[]` instead → `level None`. E3 → `found None`, and `hits_for` was never
  asked for `"y"`. E4's query → `[{"node_id": "v:L3", "level": "lifetime", "frames": [178, 178]}, {"node_id": "v:T22",
  "level": "transition", "frames": [176, 177]}]` → `found True`, `rank 2`, `level "transition"` (178 > 177: the first
  hit does not cover). An added `E5` `n 5` `"kubectl get nodes"` with `first_t = submitted_t = 702.03`, first and
  submitted frame 180, and the hit `{"node_id": "v:L9", "level": "lifetime", "frames": [180, 181], "t": [702.0333,
  706.7]}` → `found True`, `rank 1` (a comparison in seconds would miss it).
- `test_exact_per_reader`: lifetimes `L1` `"PS C:\Users\msadmin> az account show"` first frame 157; `L2` text `"PS
  C:\Users\msadmin>azconfigure --defaultsgroup=RG1"`, first frame 161; `L3` `"PS C:\Users\msadmin> kubectl config
  current-context"` first frame 178; `L4` `"PS C:\Users\msadmin> kubect1 config current-context"` first frame 175.
  `vlm = {"L2": "PS C:\Users\msadmin> az configure --defaults group=RG1", "L4": "PS C:\Users\msadmin> kubectl config
  current-context"}`. Expected. E1: `exact {"ocr": True, "vlm": False, "any": True}`, `first_frame_error {"ocr": 0,
  "vlm": None, "any": 0}`. E2: `exact {"ocr": False, "vlm": True, "any": True}`, `first_frame_error.any 0`. E4:
  `exact.ocr True` through `L3` with `first_frame_error.ocr 3` (178 − 175); `exact.vlm True` through `L4` with
  `first_frame_error.vlm 0`; `first_frame_error.any 0`. Rates `exact {"ocr": (2, 3), "vlm": (2, 3), "any": (3, 3)}`;
  `first_frame_error_abs_mean {"ocr": 1.5, "vlm": 0.0, "any": 0.0}` (OCR: 0 and 3 over two entries). With `vlm = {}`
  no row has a `vlm` key, `any` equals `ocr`, and E4's `first_frame_error.any` is `3`.
- `test_claims_one_per_row`: changes `T1 155→156`, `T3 157→158`, `T9 163→164`, `T16 170→171`, `T22 176→177`, `T23
  177→178`, `T30 184→185`; interpretations `T1 ("az login", "yes")`, `T3 ("az account show", "yes")`, `T9 ("az
  configure --defaults group=RG1", "unclear")`, `T16 ("y", "yes")`, `T22 (" kubectl  config current-context ",
  "yes")` (spaces to collapse), `T23 ("kubectl config current-context", "yes")`, `T30 ("clear", "yes")` → six claims
  (`T9` is none). E1 `submitted True`, `claim "T3"`, `submit_frame_error 0`; E2 `submitted False`, `claim None`; E3
  `claim "T16"`, error `0`; E4 `claim "T22"`, error `0` (0 frames away against 1). N1 `false_run True`, `claim "T1"`;
  N2 `false_run True`, `claim "T23"` (left over). Rates `submitted (2, 3)`, `submit_frame_error_abs_mean 0.0` over 2,
  `false_run (2, 2)`. Without `T22`'s interpretation: E4 `claim "T23"`, `submit_frame_error 1`, N2 `false_run False`,
  `false_run (1, 2)`, `submit_frame_error_abs_mean 0.5`. With `T16`'s `entered_text` `"kubectl get deployment"` (it
  contains a `y`): E3 `submitted False`.
- `test_command_scores_rates_and_units`: the found rows of E1 to E4, the exact rows and the claim rows of the tests
  above → `rates.found (2, 3)`; `units["found"] == {"1": 1.0, "2": 0.0, "4": 1.0}`, `units["exact.ocr"] == {"1": 1.0,
  "2": 0.0, "4": 1.0}`, `units["exact.vlm"] == {"1": 0.0, "2": 1.0, "4": 1.0}`, `units["exact.any"] == {"1": 1.0, "2":
  1.0, "4": 1.0}`, `units["first_frame_error_abs.any"] == {"1": 0.0, "2": 0.0, "4": 0.0}`, `units["submitted"] ==
  {"1": 1.0, "2": 0.0, "4": 1.0}`, `units["submit_frame_error_abs"] == {"1": 0.0, "4": 0.0}`, `units["false_run"] ==
  {"N1": 1.0, "N2": 1.0}`; no metric has a unit `"3"`. With `found_rows=None` and `submit_rows=false_rows=None` →
  `rates["found"] is None`, `rates["false_run"] is None`, and no `found`, `submitted`, `submit_frame_error_abs` or
  `false_run` key in `units`.
- `test_score_commands_on_the_mini_run` (the tripwire for the adapters; plan 3's Fixture M: `mini_run(tmp_path,
  labels=True)`, `mini_interpretations(run)`, `build_index(run, cfg)`; a ground-truth file in plan 1's format with the
  executed row `` `git status` ``, first `11, 24.40`, submitted `12, 26.40`, and the never-run row `` `git stash` ``
  frames `11 (24.40)`) → the entry has `found True`, `level "lifetime"`, `exact {"ocr": True, "vlm": True, "any":
  True}`, `first_frame_error.any 0`, `submitted True`, `claim "T2"`, `submit_frame_error 0`; `rates.false_run (0, 1)`.
  With `labels=False` the row has no `vlm` key. With no `index.sqlite` and no `interpretations.jsonl` the found and
  submission rates are `None`.
- `test_repo_ground_truth_frames` (reads `docs/ground-truth/span2-commands.md` through plan 1's parser): 9 executed,
  5 never run; `[scorable(e) for e in executed] == [True, True, True, False, False, True, True, True, True]`; entry 2
  first frame 161, submitted frame 164; entry 7 first frame 180 and submitted frame 180; entry 9 submitted frame 187;
  never-run frames `[[155], [165], [172, 173, 174], [178], [179]]`; every executed entry has a window.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_commands.py -q`. Expected: FAIL (`No module named
  'scry.evaluation.commands'`).
- [ ] **Step 2:** Implement rules 1–11 and the adapters.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): command metrics by frame: found, exact per reader, first appearance, submitted, false run`

### Task 5: The question set: parser, and the runner through `ask`

**Files:**
- Create: `src/scry/evaluation/questions.py`, `tests/test_eval_questions.py`
- Modify: `src/scry/evaluation/adapters.py`

**Interfaces:**
- Consumes: plan 3's `ask` (P3) through the adapter.
- Produces, in `adapters.py`: `@dataclass AskOutcome`: `text: str`, `usage: dict`, `dollars: float`, `model: str`,
  `turns: int`, `tools: list[str]`, `stop: str`; `answer_fn(run, cfg, question: str) -> AskOutcome` (one call to plan
  3's `ask`; `text = result.text`, `dollars = result.cost_usd`, `tools = result.tool_calls`, `model =
  cfg.model.model`, the name `ask` was configured with).
- Produces, in `questions.py`:
  - `@dataclass RubricItem`: `id: str` (`M1`, `X1`, …), `kind: Literal["must", "must_not"]`, `text: str`
  - `@dataclass Question`: `id`, `key` (`"<id>@<6 hex>"`), `polarity: Literal["positive", "negative"]`, `style`,
    `question`, `reference`, `rubric: list[RubricItem]`
  - `parse_questions(md: str) -> list[Question]`
  - `class Answer(BaseModel)`: `qid`, `key`, `polarity`, `question`, `answer`, `usage: dict`, `model: str | None`,
    `dollars: float`, `seconds: float`, `turns: int`, `tools: list[str]`, `stop: str | None`, `error: str | None`
  - `run_questions(run, cfg, questions_path: Path, answer=adapters.answer_fn, clock=time.perf_counter) ->
    list[Answer]`, writing `answers.jsonl` in the run directory; `load_answers(run) -> list[Answer]`

**Rules — the file format** (that of `docs/ground-truth/span2-questions.md`):
1. A question starts at a line matching `^### (Q\d+) \((positive|negative), ([^)]+)\)\s*$` and ends at the next `#`
   heading. Everything outside question blocks is ignored.
2. Inside a block the bullets `- **Question:**`, `- **Reference answer:**` and `- **Rubric:**` are read. A value
   continues over the following lines that are indented and do not start with `- ` after their indentation;
   continuation lines are stripped and joined with one space. `- **Evidence:**` is for people and is not read.
3. Rubric items are the indented lines `- M<n>: …` (`must`) and `- X<n>: …` (`must_not`) under **Rubric**, with the
   same continuation rule.
4. `key = id + "@" + sha256(norm(question))[:6]`: an edited question is a different unit, so answers to different
   wordings are never paired (Task 8).
5. `ValueError` naming the question for: a repeated id; a missing **Question**, **Reference answer** or **Rubric**; no
   `M` item; a negative question without an `X` item; a repeated rubric id.

**Rules — the runner:**
6. Every question is asked once per run directory, in file order, each through one call of `answer` (a fresh
   conversation; nothing is shared between questions and no call cache is involved: these calls are what is judged).
7. `dollars` is the outcome's (plan 3 prices the summed usage of the turns); `seconds` is the wall time of the call,
   rounded to 0.1.
8. A question that failed is recorded, never judged as if its error message were an answer: an exception from
   `answer` becomes an `Answer` with `error = "<Type>: <message>"[:500]` and empty `answer`; an outcome whose `stop` is
   `"api_error"` (plan 3's `ask` returns a failed API call instead of raising) becomes an `Answer` with `error` = the
   outcome's text, empty `answer`, and the outcome's `dollars`. The runner continues with the next question, and
   after the last one raises `RuntimeError("<n> questions failed")` when any answer has an `error`, so the run is
   marked `failed` and the next `scry eval run` asks only those questions again (rule 9).
9. Resume: an existing `answers.jsonl` entry with the same `key` and no `error` is kept; every other question is
   asked. The file is rewritten atomically after each answer.

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
- **Evidence:** executed row 1; frames 2-3
## Negative questions (secondary)
### Q2 (negative, did they)
- **Question:** Did they push?
- **Reference answer:** No.
- **Rubric:**
  - M1: says nothing was pushed.
  - X1: says `git push` was executed.
```

- `test_parse_questions`: two questions. Q1: `polarity "positive"`, `style "exact-string lookup"`, `reference "At
  frame 2 (0:02.5), submitted by frame 3."`, rubric ids `["M1", "M2", "X1"]` with kinds `["must", "must",
  "must_not"]`, `key` matching `^Q1@[0-9a-f]{6}$`. Q2: `polarity "negative"`. Changing Q1's question text changes its
  `key` and not Q2's. Removing Q2's `X1` line → `ValueError` containing `Q2`; a second `### Q1 (…)` block →
  `ValueError` containing `Q1`.
- `test_repo_question_file_parses` (reads `docs/ground-truth/span2-questions.md`): it parses. Nothing more: the owner
  may prune or rewrite his own draft.
- `test_run_questions_records_cost_resumes_and_keeps_errors`: a fake `answer` returning `AskOutcome("It ran at frame
  2.", {"input_tokens": 10_000, "output_tokens": 2_000}, 0.1, "claude-opus-5", 3, ["search", "get_frame"],
  "end_turn")` and a fake clock advancing 2.0 s per call → two answers; each `dollars 0.1`, `seconds 2.0`, `turns 3`;
  `answers.jsonl` has two lines. Run again with Q2's question text changed → the fake is called once (for Q2 only)
  and Q1's answer is unchanged. With a fake that raises `RuntimeError("rate limit")` for Q1 → `run_questions` raises
  `RuntimeError` containing `1 questions failed` after writing both lines: Q1 `error "RuntimeError: rate limit"`,
  `answer ""`, `dollars 0.0`; Q2 answered. With a fake returning `stop "api_error"` and `dollars 0.02` for Q1 → Q1
  `error` set, `answer ""`, `dollars 0.02`. A further call with a working fake asks Q1 only.
- `test_answer_fn_maps_ask_result`: with `scry.ask.ask` monkeypatched to return `SimpleNamespace(text="x", turns=2,
  tool_calls=["search"], usage={"input_tokens": 1}, cost_usd=0.0225, stop="end_turn")` → `AskOutcome` with `text "x"`,
  `dollars 0.0225`, `tools ["search"]`, `model` the config's.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_questions.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–9 and the `answer_fn` adapter (P3).
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): question-set parser and the question runner through ask, with cost per question`

### Task 6: Scoring answers against the rubric with a separate, blind model call

**Files:**
- Create: `src/scry/evaluation/judge.py`, `tests/test_eval_judge.py`

**Interfaces:**
- Consumes: `Question`, `RubricItem`, `Answer` (Task 5); `scry.providers` (`VlmProvider.complete`, `CallCache`,
  `AnthropicProvider`, `text_block`); `sha256_obj`; `estimate_cost`.
- Produces:
  - `JUDGE_PROMPT_VERSION = "judge-v1"`; `JUDGE_SYSTEM: str` (the text below)
  - `class ItemVerdict(BaseModel)`: `id: str`, `holds: bool`, `quote: str`; `class JudgeOutput(BaseModel)`: `items:
    list[ItemVerdict]`
  - `SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}`
  - `label_from(items: dict[str, bool], rubric: list[RubricItem]) -> Literal["correct", "partial", "wrong"]`
  - `class Judgment(BaseModel)`: `run: str`, `qid`, `key`, `polarity`, `items: dict[str, bool]`, `quotes: dict[str,
    str]`, `label: str | None`, `score: float | None`, `source: Literal["judge", "rule"]`, `model: str | None`,
    `usage: dict`, `dollars: float`, `error: str | None`
  - `judge_answers(run_name: str, questions: list[Question], answers: list[Answer], provider, effort: str = "low") ->
    list[Judgment]`; `judge_provider(base_cfg: Config, cache_dir: Path) -> VlmProvider`; `write_judgments(run, js)`,
    `load_judgments(run) -> list[Judgment]` (`judgments.jsonl` in the run directory)

**The judge's system prompt (`JUDGE_SYSTEM`):**

```
You grade one answer to a question about a screen-recording tutorial. You are given the question, a reference answer
written from ground truth, a list of rubric statements, and the answer to grade. For each rubric statement decide
whether it is true OF THE ANSWER, not whether it is true of the video. Judge only what the answer says. Do not reward
or punish style, length, hedging or citations. Only a statement that says the answer "contains the exact string" is
about exact text: it holds only if the answer contains that string character for character, including case. Every
other statement is judged on meaning: "names the command", "gives the output" or "says ..." holds when the answer
unmistakably refers to the same thing, whatever its spelling, spacing or case. A statement that the answer gives a
time in a range also holds when the answer names a frame in the stated range. A "says ..." or "claims ..." statement
holds when the answer asserts it as its conclusion, not when it mentions it as a possibility it rejects. Return every
rubric id exactly once, with holds true or false and a short verbatim quote from the answer that decided it (empty
when nothing in the answer bears on it).
```

**Rules:**
1. One call per answer, carrying one text block: the question, the reference answer, the rubric lines as `id: text`,
   and the answer. Never the run name, the configuration, the phase, other answers or any frame: the judge is blind.
2. The call goes through `provider.complete(stage="judge", system=JUDGE_SYSTEM, blocks=[…], output_model=JudgeOutput,
   effort=effort, prompt_version=JUDGE_PROMPT_VERSION, input_hashes=[sha256_obj({"question", "reference", "rubric",
   "answer"})])`. `judge_provider` builds an `AnthropicProvider` on the base config's `[model]` with a `CallCache` at
   `cache_dir` (`runs/eval/<phase>/judge-cache`), never a run's cache. The judge is an instrument, not the thing
   measured: caching it makes re-scoring free and repeatable, and two identical answers get one verdict.
3. `label_from`: `wrong` when any `must_not` item holds or no `must` item holds; `correct` when every `must` item
   holds and no `must_not` item does; otherwise `partial`. `score = SCORE[label]`; the counts are always shown beside
   a mean.
4. An answer that is empty after `strip()`, or has an `error`, is `wrong` with `source "rule"`, every item `False`, and
   no call. An answer whose `key` is not in the question file (the file was edited after the run) is not judged and
   is counted as stale.
5. Verdicts for ids that are not in the rubric are dropped. A rubric id the judge did not return, a provider error, or
   a refusal gives `label None`, `score None` and `error` naming the ids or the provider's error; nothing is
   defaulted. Such judgments are counted in every report and excluded from means.
6. `dollars = estimate_cost(usage, model)` of the call (`0.0` for a cache hit, whose `VlmResult.cached` is true).

**Tests to write first** (a fake provider: an object with `model = "claude-opus-5"` and an async `complete(**kw)` that
records `kw` and returns a `VlmResult` with a canned `JudgeOutput` and `usage {"input_tokens": 2_000, "output_tokens":
200}`):
- `test_label_from`: rubric `M1, M2, X1` → `{M1: T, M2: T, X1: F}` `correct`; `{T, F, F}` `partial`; `{T, T, T}`
  `wrong`; `{F, F, F}` `wrong`. Rubric `M1, X1` (a negative question) → `{M1: T, X1: F}` `correct`: a bare "No" that
  satisfies `M1` is correct.
- `test_judge_scores_costs_and_is_blind`: Task 5's Q1 and the answer `"git status ran at frame 2."`, canned verdicts
  `M1 T`, `M2 T`, `X1 F`, `run_name "span2-transcribing-r1"` → `label "correct"`, `score 1.0`, `source "judge"`,
  `dollars 0.015` (2,000 × 5 + 200 × 25 millionths), `quotes` has three keys; the recorded `system` and block texts
  contain neither `span2-transcribing-r1` nor `transcribing`; the recorded `input_hashes` are equal for two runs whose
  answers have the same text, and differ when the answer text differs. An `Answer` with `answer ""` → `label "wrong"`,
  `source "rule"`, `dollars 0.0`, and no call recorded for it.
- `test_missing_item_is_an_error_not_a_default`: canned verdicts for `M1` and `M2` only → `label None`, `score None`,
  `error` containing `X1`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_judge.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): rubric scoring of answers by a blind, cached judge call; labels derived by code`

### Task 7: The scorecard: one run, every number, per-unit values

**Files:**
- Create: `src/scry/evaluation/scorecard.py`, `tests/test_eval_scorecard.py`

**Interfaces:**
- Consumes: Tasks 1, 3–6; `adapters`; `Run`.
- Produces:
  - `METRICS: dict[str, Literal["higher", "lower"]]`, exactly this table (name → which way is better):

    | name | better | unit |
    |---|---|---|
    | `found`, `exact.ocr`, `exact.vlm`, `exact.any`, `submitted` | higher | entry `n` |
    | `first_frame_error_abs.any`, `submit_frame_error_abs` | lower | entry `n` |
    | `false_run` | lower | `N<i>` |
    | `questions.positive`, `questions.negative` | higher | question key |
    | `cost.per_question` | lower | question key |
    | `cost.per_frame`, `seconds.per_frame` | lower | `run` |

  - `build_scorecard(run_dir: Path) -> dict`; `write_scorecard(run_dir, card)` (`scorecard.json`); `score_phase(root:
    Path, phase: str) -> list[dict]` (builds and writes the card of every directory under `root / phase` that holds an
    `evalrun.json`, in name order)

**Rules:**
1. Inputs come from the run directory: `evalrun.json` (the spec, the span's ground-truth and question paths, the
   commit and dirty flag, `cold`, stage seconds), `config.json` (the default model), `manifest.json`, `answers.jsonl`
   and `judgments.jsonl` when present, and the records through `adapters`.
2. The card: `{"run": {phase, name, config_id, span, frames, values, repeat, status, resumed, cold, git_commit,
   git_dirty}, "inputs": {"ground_truth_sha256", "questions_sha256"}, "counts": {"frames", "transitions",
   "lifetimes"}, "commands": Task 4's result | None, "questions": … | None, "counters": {"annotate": {…}, "interpret":
   {…}}, "cost": Task 1's cost_summary, "units": {metric: {unit: value}}, "warnings": [str], "notes": [str]}`.
3. `commands` is scored when the span names a ground truth: Task 4's `score_commands`. Without `index.sqlite` the
   found keys are `None` (note `no index: found not scored`); without interpretations the submission keys are `None`
   (note); without lifetimes `commands` is `None` with a warning.
4. `questions`, when `judgments.jsonl` exists: per polarity `{"n", "correct", "partial", "wrong", "unscored",
   "mean"}`; `answers`: one row per answer `{"qid", "key", "polarity", "answer", "label", "items", "quotes",
   "dollars", "seconds", "error"}` (the judge's verdict and quote for every rubric line, so the judge can be audited
   from `scores.json`); `dollars_per_question` (mean of the answers' `dollars`), `ask_dollars`, `judge_dollars` (apart),
   `seconds_per_question`, `stale`. Units are keyed by the question `key`: `questions.positive`, `questions.negative`
   (the score; unscored judgments have no unit), `cost.per_question`. Answers without judgments → `questions None` and
   the note `answers not judged: run scry eval judge`.
5. `counters` copies what plans 2 and 3 already count, as written, where present: `stages.annotate`: `repairs`,
   `repair_counts`, `errors`, `failed_targets`; `stages.interpret`: `errors`, `invalid_citations`, `submitted`. They
   are printed per run and never compared.
6. Cost units: `cost.per_frame` and `seconds.per_frame` under the single unit `"run"`. `units` is the union of the
   command, question and cost units. Every key is a name in `METRICS`.
7. Warnings (things that weaken the evidence): every warning of `cost_summary` (cache hits, an unknown model); `run
   is not cold` when `evalrun.json` says so; `run was resumed`; `run status is <status>` unless `done`; failed
   `interpret` or `annotate` calls with their count; answers with `error`; judgments with `label None`; stale answers.
   Notes (expected absences): no annotations, no index, no interpretations, no second reader, answers not judged.
8. A scorecard is rebuilt freely: scoring calls no model and costs nothing.

**Tests to write first** (rates are two-element lists, as they are after a JSON round trip. The run directory is plan
3's Fixture M with everything real: `mini_run(tmp_path, labels=True)`, `mini_interpretations(run)`, `build_index(run,
cfg)`; added by hand: `evalrun.json` with span `s` frames `[10, 13]`, `ground_truth` = Task 4's `git status` / `git
stash` file, `status "done"`, `cold true`, `seconds {"interpret": 4.0}`; `config.json` with `model.model =
"claude-opus-5"`; in the manifest `stages.decode.emitted = 4` and `stages.interpret = {"usage": {"input_tokens":
20_000}, "model": "claude-opus-5", "cache": {"hits": 0, "misses": 3}, "errors": 0, "invalid_citations": 2}`):
- `test_scorecard_full_and_with_pieces_missing`: `counts == {"frames": 4, "transitions": 3, "lifetimes": 7}`;
  `commands.rates.found == [1, 1]`, `rates.exact.ocr == [1, 1]`, `rates.exact.vlm == [1, 1]`, `rates.submitted == [1,
  1]`, `rates.false_run == [0, 1]`; `units["found"] == {"1": 1.0}`; `units["false_run"] == {"N1": 0.0}`;
  `counters.interpret == {"errors": 0, "invalid_citations": 2}`; `cost.dollars 0.1` (20,000 × 5 millionths),
  `cost.per_frame 0.025`, `cost.per_video 0.1` (projection 4), `units["cost.per_frame"] == {"run": 0.025}`,
  `units["seconds.per_frame"] == {"run": 1.0}`; `questions is None`; `warnings == []`; every key of `units` is in
  `METRICS`; `inputs.ground_truth_sha256` is the file's SHA-256. Then `mini_run(tmp_path)` without labels,
  interpretations or index → `rates.found is None`, `rates.false_run is None`, no `found`, `false_run` or `exact.vlm`
  key in `units`, notes for the index, the interpretations, the annotations and the second reader, no exception. With
  `status "failed"` and manifest `cache.hits 2` → warnings containing `failed` and `2 cache hits`.
- `test_questions_section`: `answers.jsonl` with two answers (`Q1@aaaaaa` positive `dollars 0.1`, `Q2@bbbbbb` negative
  `dollars 0.2`) and `judgments.jsonl` with labels `correct` and `wrong`, `dollars 0.015` each → `questions.positive
  == {"n": 1, "correct": 1, "partial": 0, "wrong": 0, "unscored": 0, "mean": 1.0}`, `questions.negative.mean 0.0`,
  `dollars_per_question 0.15`, `ask_dollars 0.3`, `judge_dollars 0.03`, `units["questions.negative"] == {"Q2@bbbbbb":
  0.0}`, `units["cost.per_question"] == {"Q1@aaaaaa": 0.1, "Q2@bbbbbb": 0.2}`; `questions.answers` has two rows, each
  with `label`, `items` and `quotes`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_scorecard.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–8.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): scorecard per run: commands, questions with verdicts, stage counters, cost, per-unit values, warnings`

### Task 8: The noise floor from repeats, and the paired comparison: inside or outside the noise

**Files:**
- Create: `src/scry/evaluation/compare.py`, `tests/test_eval_compare.py`

**Interfaces:**
- Consumes: scorecards and `METRICS` (Task 7).
- Produces:
  - `paired_difference(a: dict[str, float], b: dict[str, float]) -> tuple[float | None, int, int]`
  - `same_config_diffs(cards: list[dict], metric: str, units: set[str] | None = None) -> list[float]`
  - `floor_single(diffs: list[float]) -> float | None`; `scaled_floor(f1: float, n_a: int, n_b: int) -> float`
  - `noise_table(cards: list[dict]) -> dict`
  - `@dataclass Row`: `metric`, `better`, `n_a`, `n_b`, `units: int`, `dropped: int`, `mean_a`, `mean_b`, `diff`,
    `floor_single`, `floor`, `verdict: Literal["outside", "inside", "unknown", "not comparable"]`, `reason: str |
    None`, `favours: Literal["a", "b"] | None`, `flips: list[str]`, `cost_a: dict`, `cost_b: dict`
  - `compare_configs(a: list[dict], b: list[dict]) -> list[Row]`
  - `all_pairs(cards: list[dict]) -> list[tuple[str, str, str, list[Row]]]` (span, A's config id, B's config id, rows)

**Rules — the floor** (spec §9: "P1 sets the noise floor; a difference inside it is no difference"; ledger L42:
identical cold runs differ):
1. `paired_difference(a, b)`: over the units present in both, the mean of `b[u] − a[u]`, rounded to 6; with it the
   number of common units and the number dropped (`|a ∪ b| −` common). No common unit → `(None, 0, dropped)`.
2. `same_config_diffs`: for every pair `i < j` of cards that both hold the metric, `|paired_difference(units_i,
   units_j)|`, restricted to `units` when given. Cards are "the same configuration" when their `config_id` and phase
   are equal; they differ only in `repeat`.
3. **The floor for one run against one run** is `floor_single` = the largest of those absolute differences: the
   biggest difference ever seen between two runs that should have been identical. `None` without a pair.
4. **Means of repeats are steadier than single runs.** For a mean of `n_a` runs against a mean of `n_b`,
   `scaled_floor = f1 × sqrt((1/n_a + 1/n_b) / 2)`, rounded to 6: `f1` itself for one against one, `f1 × 0.7071` for two
   against two, `f1 × 0.5774` for three against three. This is what lets added repeats clear the noise (spec §9);
   without it more repeats could only raise the floor.
5. `noise_table`: per configuration with at least two repeats, per metric: `{"values": [the mean of the units per
   repeat, in repeat order, rounded to 4], "max": floor_single}`.

**Rules — the comparison:**
6. **Same frames or nothing.** All cards of both sides must have the same `run.frames`; otherwise `ValueError`
   containing `paired over the same frames`.
7. One row per metric of `METRICS` that any card holds. A metric that every card of one side lacks gives `verdict "not
   comparable"` with `reason "absent in A"` or `"absent in B"` (the second reader does not exist without
   transcription). Question units carry the question's text hash in their key, so answers to a reworded question
   simply do not pair and are counted in `dropped`.
8. **Pairing.** The common units are those present in every card of both sides that holds the metric. `a_u` is the
   mean over A's cards of the value at `u`, `b_u` likewise; `diff = mean over u of (b_u − a_u)`, `mean_a` and `mean_b`
   the means of `a_u` and `b_u`; all rounded to 6. `dropped` = units seen in some card and not common. No common unit →
   `not comparable`, `reason "no common units"`.
9. **The floor.** `floor_single` = the largest of the same-configuration differences inside A and inside B, computed
   over the common units (rule 2). With no pair on either side, `floor_single` is `None` and the verdict `unknown`:
   single runs without a measured floor are never evidence of a difference (L42).
10. `floor = scaled_floor(floor_single, n_a, n_b)`; `verdict = "outside"` only when `|diff| > floor`, strictly; else
    `"inside"`. No threshold besides the measured floor, and no success condition.
11. `favours`, for `outside` rows only: B when the difference goes the way `METRICS` says is better, else A. It names
    a direction on one metric; nothing combines rows.
12. `flips`, for metrics whose values are all 0 or 1: `"<unit>: A only"` when every A card has 1 and every B card 0,
    `"<unit>: B only"` for the reverse. They name the commands or questions behind a difference.
13. Every row carries `cost_a` and `cost_b`: the mean `per_frame` and `per_video` over that side's cards.
14. `all_pairs`: per span, every pair of configurations in the order in which the cards first name them.
15. **What the floor is worth, in words** (the report prints this, Task 9 rule 2). With three repeats a side the floor
    is a range of three values per configuration; by a normal approximation a difference of means clears it about
    once in eight when nothing differs **[estimated by the review]**, per metric and per comparison. A single `outside`
    row is weak evidence. And in P1 `exact.ocr`, and *found* wherever OCR's reading suffices, depend on `read` and
    `track` only, which are model-free and identical across the three bases and all repeats: floor 0 and difference 0
    by construction. P1's discriminating evidence is the question set, `exact.vlm`, the secondary metrics and cost.

**Tests to write first:**
- `test_paired_difference`: `a {"1": 1, "2": 1, "3": 0}`, `b {"1": 1, "2": 0, "3": 0}` → `(-0.333333, 3, 0)`; `a {"1": 1,
  "2": 0}`, `b {"1": 1, "2": 1, "3": 1}` → `(0.5, 2, 1)`; disjoint → `(None, 0, 2)`.
- `test_floor_from_three_repeats_and_scaling`: `found` units of three repeats `{1: 1, 2: 1, 3: 0}`, `{1: 1, 2: 0, 3:
  0}`, `{1: 1, 2: 1, 3: 0}` → diffs `[0.333333, 0.0, 0.333333]`, `floor_single 0.333333`; `noise_table` gives `values
  [0.6667, 0.3333, 0.6667]`, `max 0.333333`; a configuration with one card is absent from the table and
  `floor_single([]) is None`. `scaled_floor(0.3, 1, 1)` → `0.3`; `(0.3, 2, 2)` → `0.212132`; `(0.3, 3, 3)` →
  `0.173205`; `(0.3, 3, 1)` → `0.244949`.
- `test_outside_the_noise`: `found` units. A: `{1: 1, 2: 1, 3: 1}`, the same, `{1: 1, 2: 1, 3: 0}`. B: three times `{1:
  1, 2: 0, 3: 0}`. → `units 3`, `mean_a 0.888889`, `mean_b 0.333333`, `diff -0.555556`, `floor_single 0.333333`, `floor
  0.19245`, `verdict "outside"`, `favours "a"`, `flips ["2: A only"]`.
- `test_inside_identical_and_unknown`: `first_frame_error_abs.any` (lower is better). A: `{1: 2, 2: 0}`, `{1: 4, 2:
  0}`. B: `{1: 3, 2: 1}`, `{1: 3, 2: 0}` → `diff 0.25`, `floor_single 1.0`, `floor 0.707107`, `verdict "inside"`,
  `favours None`. Four cards with equal units → `diff 0.0`, `floor 0.0`, `verdict "inside"` (0 is not strictly larger
  than 0). One card a side, A `{1: 1, 2: 1}`, B `{1: 1, 2: 0}` → `floor_single None`, `verdict "unknown"`.
- `test_missing_units_and_absent_metrics`: the cards of `test_outside_the_noise`, with unit `3` removed from A's
  second card → `units 2`, `dropped 1`. `exact.vlm` in A's cards only → `not comparable`, `reason "absent in B"`. A on frames `[155, 187]`, B on `[145, 155]` →
  `ValueError` containing `same frames`. A's cards `per_frame` 0.12 and 0.14, `per_video` 26.52 and 30.94 → every
  row's `cost_a == {"per_frame": 0.13, "per_video": 28.73}`.
- `test_all_pairs_per_span`: cards of `smoke-transcribing`, `smoke-grouponly`, `smoke-none`, `span2-transcribing`,
  `span2-grouponly`, `span2-none`, three repeats each → six comparisons: per span `(transcribing, grouponly)`,
  `(transcribing, none)`, `(grouponly, none)`; none across spans.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_eval_compare.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–14 (rule 15 is prose for Task 9).
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(eval): noise floor from identical cold runs; paired comparison marked inside or outside the noise`

### Task 9: The report, `scry eval`, and the P1 matrix

**Files:**
- Create: `src/scry/evaluation/reporting.py`, `src/scry/evaluation/cli.py`, `tests/test_eval_cli.py`, `evals/p1.toml`
- Modify: `src/scry/cli.py` (`app.add_typer(eval_app, name="eval")`)

**Interfaces:**
- Produces, in `reporting.py`: `config_rows(cards: list[dict]) -> list[dict]` (one row per configuration: means over
  its repeats, and the per-repeat `k/n`); `table(headers: list[str], rows: list[list]) -> str`; `phase_report(m:
  Matrix, cards, noise: dict, comparisons, today: str) -> str`; `write_results(results_dir: Path, m: Matrix, cards,
  noise, comparisons, today) -> list[Path]`: `report.md` and `scores.json` (every scorecard of the phase, so the
  report can be rebuilt, and the judge audited, from committed data).
- Produces the commands (each takes the matrix path first; `--root` defaults to `runs/eval`, `--results` to
  `docs/results`):
  - `scry eval run MATRIX [--dry-run] [--only NAME]`: Task 3; prints each outcome; exit code 1 when any run failed.
    With `--dry-run` it prints one line per run (name, stages) and validates every run's config; exit code 1 with the
    error on any `ValueError` or `ValidationError`; it creates nothing and spends nothing.
  - `scry eval judge MATRIX`: Task 6 over every run that has `answers.jsonl`; the judge cache is `<root>/<phase>/
    judge-cache`. Besides `run`, the only command that can spend money.
  - `scry eval report MATRIX`: `score_phase`, the noise table, `all_pairs`, then the results files. Calls no model.

**Rules:**
1. **Cost beside every number.** Every table of the report that shows a score or a question result ends with the
   columns `$ / frame` and `$ / video`, the means over the configuration's repeats. No code enforces it; a reader of
   one report can see it.
2. The header holds: the date; the matrix path; runs by status; the distinct commits the runs started on and which
   runs started on a dirty tree; the sentence `$ / video = $ / frame × <N> frames, a linear projection from this span
   to the whole source video`; and this paragraph, word for word: ``An `outside` row means only that the difference is
   larger than the largest difference seen between identical cold runs of the two configurations, scaled for means of
   repeats. With three repeats a side that floor is a range of three values: by a normal approximation about one row
   in eight reads `outside` when nothing differs [estimated], and this report has dozens of rows. One `outside` row is
   weak evidence. Nothing here is a verdict, and no row decides anything by itself.``
3. Sections, in this order: `# <phase> evaluation report` (the header); `## Warnings` (every scorecard warning,
   prefixed by the run name; `none` when empty); `## Runs` (run, status, frames, cold, resumed, cache hits, dollars,
   `$ / frame`, `$ / video`, wall seconds; then the stage counters of Task 7 rule 5 per run, "reported, never
   compared"); `## Cost` (per configuration and stage: dollars, `$ / frame`, `$ / video`, the same at the batch price,
   seconds / frame; questions: `$ / question` and the question set's dollars, outside `$ / video`; the judge's dollars
   apart); `## Commands` (**primary, side by side:** found, and exact for `ocr`, `vlm` and `any`, as `k/n` per repeat
   and mean, with the sentence of Task 4 rule 4 about `exact.any`; **secondary:** first-appearance error, submitted,
   submission error, false run; then per configuration and entry: found, exact.any and submitted in `r/n` runs, the
   level where only a summary quoted the command, the rows of `Y` and `y` marked `not rated`, and per never-run row
   false run in `r/n` runs); `## Questions` (positive, **primary**; negative, **secondary**: correct / partial / wrong
   / unscored and mean per configuration; per question the labels per repeat; stale and unscored counts); `## Noise`
   (per configuration and metric: the repeats' values and their largest paired difference); `## Comparisons` (per
   span and pair: a table of rows — metric, A, B, difference, floor, verdict, favours, units, dropped, `$ / frame` and
   `$ / video` of A and of B — then the flips).
4. Vocabulary: the verdict column holds only `outside`, `inside`, `unknown`, `not comparable`. The report states no
   pass, fail or winner, and says `failed` only of a run's status.
5. The CLI functions only parse arguments, call Tasks 2–8 and print; they hold no logic of their own.

**The committed matrix, `evals/p1.toml`** (the only one; a later phase's matrix is written when that phase is planned,
from the previous phase's results):

```toml
# P1 (spec §9): three co-equal bases, arm A, full scale, every frame annotated; both spans through `index`;
# the question set on span 2; three cold repeats each: 18 runs, about $55 by the spec's estimate.
phase = "p1"
source = "runs/p0"
stages = ["read", "track", "annotate", "interpret", "summarize", "index", "ask"]
repeats = 3

[spans.smoke]
frames = "145-155"

[spans.span2]
frames = "155-187"
ground_truth = "docs/ground-truth/span2-commands.md"
questions = "docs/ground-truth/span2-questions.md"

[axis.base.transcribing]
"annotate.mode" = "every_frame"
"annotate.transcribe" = true
"annotate.scale" = 1.0

[axis.base.grouponly]
"annotate.mode" = "every_frame"
"annotate.transcribe" = false
"annotate.scale" = 1.0

[axis.base.none]
"annotate.mode" = "off"
```

Arm A is plan 2's only arm until its arm switch lands, so the matrix names no arm key. With `mode = "off"` the
`annotate` stage still runs, writes no file and records zero usage, so the three bases share one stage list.

**Tests to write first** (`typer.testing.CliRunner`; stage functions replaced by fakes by monkeypatching
`scry.evaluation.runner.resolve`; a source run built as in Task 3):
- `test_p1_matrix_expands_to_the_planned_runs` (reads `evals/p1.toml`; needs plans 2 and 3 landed): 18 runs;
  `config_for` succeeds for every run; every `smoke-*` run's stages end with `index` and every `span2-*` run's with
  `ask`; `span2-transcribing-r1`'s config has `annotate.mode "every_frame"`, `annotate.transcribe True`,
  `annotate.scale 1.0`; every `*-none-*` run's has `annotate.mode "off"`; `source` is under `runs/`.
- `test_run_and_report_end_to_end_with_fake_stages`: a two-repeat matrix whose fake stages only add a manifest entry
  with usage. `run --dry-run` → exit code 0, two run names in the output, no directory created under the root; a
  matrix with `"track.margn" = 1` → exit code 1 and `margn` in the output. `run` → exit code 0 and two `evalrun.json`
  with `status "done"`; with a fake stage that raises on its first call → exit code 1, and the second run still ran.
  `report` → `report.md` and `scores.json` under `<results>/p9/`; `scores.json` round-trips to the two scorecards;
  the report has the headings of rule 3 in order, contains `One `outside` row is weak evidence` and `linear
  projection`, and its `## Runs` table has the columns `$ / frame` and `$ / video`.

- [ ] **Step 1:** Write the tests and `evals/p1.toml`. Run `uv run pytest tests/test_eval_cli.py -q`. Expected: FAIL
  (`No such command 'eval'`).
- [ ] **Step 2:** Implement the report and the commands.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry eval run evals/p1.toml --dry-run` prints 18 runs and
  exits 0. `uv run scry eval --help` lists `run`, `judge`, `report`.
- [ ] **Step 4:** Commit: `feat(eval): phase report with cost beside every number; scry eval run, judge, report; the P1 matrix`

---

## Running a phase with the harness (the procedure, with P1 as the example)

Not a task: what the executor of a phase does once this plan has landed. Nothing here waits for an approval, and no
person has to tick anything.

1. The matrix, the ground truth and the question file are committed **before** the phase runs. `uv run scry eval run
   evals/p1.toml --dry-run` → 18 runs, no error, nothing spent.
2. `uv run scry eval run evals/p1.toml` (about $55 by the spec's estimate; safe to re-issue after an interruption:
   finished runs are skipped, an unfinished one is finished and flagged). To go faster, start several processes with
   `--only NAME`; wall times are then not comparable, and the ledger row says so.
3. `uv run scry eval judge evals/p1.toml` (about $2 **[estimated by the review]**; free to repeat).
4. `uv run scry eval report evals/p1.toml` → `docs/results/p1/report.md` and `scores.json`. Read the warnings first.
   The coordinator writes the ledger row in prose from the report: the commits, the spend (pipeline, questions, judge
   apart), per configuration the primary scores side by side, the secondary ones, the questions and the cost per
   frame and per video, what read `outside` and why that is weak evidence with three repeats, and one sentence of
   reference: `runs/span2-before`, the pre-re-base pipeline, cost $4.6465 for the same 33 frames, $0.1408 per frame
   (272,050 input, 127,046 output, 106,335 cache-read and 9,105 cache-creation tokens at the list prices; the ledger's
   $4.59 left the last term out). Commit the results directory and the ledger together and report to the owner.
5. The next phase's matrix is written then, from these results, together with whatever item of "Deferred" that phase
   needs. Finalists get more repeats by raising `repeats` in a copy of the matrix under a new phase name (a finished
   run's directory is never re-used for a changed spec).

## Deferred, with the phase that would need it

Nothing below is built now. Each returns, from commit `c23108d` where the draft specified it, when the named phase is
planned and only if that phase's matrix uses it.

| Item | Needed at |
|---|---|
| Guards as compared metrics: one-container share, popups found on named frames (`popup_frames` in a span), repairs and unassigned per frame (the draft's Task 5). Until then the scorecard copies the stages' own counters, and the track guards stay with plan 1's `scry report` (they are deterministic) | P2, where an arm and a scale are chosen partly on them |
| `[[exclude]]`; the floor file (`floor`, `floor_match`, `floor_lookup`, `noise.json`) for two-repeat screens read against P1's measured noise; comparisons across phases (`[[compare]]` with a `phase` selector, `b = "each"`) | P2 |
| A plain by-eye listing of containers and links over shared sample frames (the draft's Task 9 without tick parsing, blind codes, thinning or tallies; those only when a person commits to ticking) | P2 or P3 |
| Per-unit cost: `cost.annotate` per frame and `cost.interpret` per transition as paired units; no batch price shown for incremental runs | P3 |
| `fixed_from`: copying a finished run's upstream so that only later stages are sampled | P5 |
| Citation guards for `ask`, from plan 3's `AskResult.citations`, never from prose | P5, if prompt wordings are compared (plan 3 has deferred the prompt-variant registry) |
| The blind by-eye answer sheet and the judge-against-eye agreement (the draft's Task 8) | only if the owner asks to audit the judge; never gating a phase. `scores.json` already holds every answer with the judge's verdicts and quotes |
| Matrices for P2 to P5 | each when its phase is planned. P6 is a copy of `p1.toml` with the hold-out's decode run as `source` and its own command list, if the owner writes one (N8) |

## Dropped outright

`skip_stages` (the no-annotation base is `annotate.mode = "off"`); P0 expressed as matrices (plan 1 ran P0 with its
own configs and `scry report`; it is deterministic, so pairing and noise add nothing); the `[reference]` row (one
sentence in the ledger row, procedure step 4); reading citations out of the agent's prose (`read_citations`,
`citation_check`, the parser's **Evidence** fields); the companions of *exact* (`exact_in_window`, `variant_only`,
`nearest`: the first-appearance error already shows a late sighting, and the rest is read from `lifetimes.jsonl`); the
two guards on submission (`guard_submissions`, `flag_shared_claims`, `submission_notes`: text equality with one claim
per row does their work); the dirty-tree refusal and the metric-code hash (the commit and a dirty flag are recorded);
the manifest-against-call-cache maximum and `cache_usage` (manifest usage already counts cache hits); the mechanical
`reading` that ordered *found* over *exact*, with `COMMAND_ORDER` and the metric roles; the ledger-row generator; the
enforcement of cost columns, of vocabulary and of "no digits from the video" by tests; the `Adapters` bundle; the
hyphen and duplicate-axis rules; the `judged` flag and the zero floor for model-free runs (no matrix is model-free
once P0 is out); the "ground truth differs" verdict (`report` rescores every run against the file as it stands, so
the cards of one report cannot differ in it); the `[judge]` table; the commands `expand`, `status`, `score`, `sheet`
and `labelsheet`; `evals/README.md`.

## Decisions this plan makes (settled in the reconciliation, ledger L50)

- **D1. Where things live.** Code in `src/scry/evaluation/`, commands under `scry eval`, the matrix in `evals/`
  (committed), run directories and the judge cache in `runs/eval/<phase>/` (git-ignored), results in
  `docs/results/<phase>/` (committed, with every scorecard in `scores.json`).
- **D2. This plan owns the command metrics, and they are compared by frame.** *Found*: a quoted lexical search
  returns an entry at a localising level (lifetime, frame, transition) whose frame range meets the entry's frames from
  first visible to submitted. *Exact*: plan 1's scorer per reader, with `any`. *Submitted*: a `submitted: yes`
  interpretation whose `entered_text` equals the command after whitespace collapse, one claim per ground-truth row,
  the error in frames. *False run*: a never-run row's text equals a claim left over. *Found* and *exact* are primary,
  side by side with no order; the rest secondary; `Y` and `y` are reported and not rated.
- **D3. No mechanical reading.** The rows are the evidence and the coordinator reads them beside their cost; both
  primaries can only tie or rise with more indexed text and more readers, so a sentence naming who is "ahead" would
  name the dearer base or nobody.
- **D4. Aggregates.** Errors are reported as mean absolute frames over the entries that have one, with the count;
  rates as `k/n`; per-unit 0/1 values feed the pairing.
- **D5. The noise floor** is the largest absolute paired difference seen between two cold runs of the same
  configuration, over both sides of a comparison; for means of repeats it is scaled by `sqrt((1/n_a + 1/n_b) / 2)`; a
  difference is `outside` only when it is strictly larger, `inside` otherwise, `unknown` without any repeat. It is a
  range, as ledger L42 reports noise, not a significance test, and the report says in words that with three repeats
  `outside` is weak evidence.
- **D6. Pairing units.** Ground-truth entry for command metrics, never-run row for *false run*, question (keyed by id
  and text hash) for the question set, the run for cost. Only units present in every run of both sides are paired;
  the rest are counted as dropped.
- **D7. Cost.** From manifest usage alone, priced by `scry.costs`; an unknown model earns a warning, never an
  exception; `$ / video` is `$ / frame` times the source run's frame count, a linear projection that the report names
  as such; seconds per stage and per frame are timed by the runner; the question set's cost is per question and
  outside `$ / video`; the judge's cost is apart; the batch price is shown beside the synchronous one.
- **D8. Cold, mechanically.** `subset` with a private cache, recorded as `cold`; a symlinked cache is refused; any
  cache hit is flagged in the scorecard; a resumed run is flagged.
- **D9. The code is recorded, not policed:** the commit and a dirty flag in every `evalrun.json`, the distinct commits
  in the report header.
- **D10. Question scoring.** Rubric lines are statements about the answer; a blind, low-effort judge call on the
  pipeline's model decides each line, cached apart; code derives `correct`, `partial`, `wrong` (1, 0.5, 0 for means;
  the counts are always shown). Only a line that says "contains the exact string" is exact. No human tick-sheet.
- **D11. The matrix format:** opaque dotted overrides validated against `Config` at expansion, so the harness names no
  pipeline key; one committed matrix; every pair of configurations of a span is compared.
- **D12. In-process stages and no TOML writer:** the runner passes `Config` objects and records the effective config
  as `config.json`.

## Self-review

- **Spec coverage (§9), for P1.** G1 → plan 1's parser, checked against the committed file in Task 4. Q →
  `span2-questions.md`, Tasks 5–6. Primary metrics → Task 4 rules 1–4. Secondary → Task 4 rules 5–9. Question set with
  lighter negatives → Tasks 5–7, Task 9 rule 3. Cost beside every number → Task 1, Task 8 rule 13, Task 9 rule 1.
  Evidence rules: committed code → Task 3 rule 3; paired over the same frames → Task 8 rules 6–8; the noise floor →
  Task 8 rules 1–5 and 9; added repeats → Task 8 rule 4; no threshold → Task 8 rule 10, Task 9 rule 4; phases report
  as they finish → the procedure. Cold runs → Task 3 rule 2, Task 1 rule 4. P1 → `evals/p1.toml`. Not covered, by
  decision: guards as compared metrics and G2 by eye (Deferred, P2); P2 to P6 (each when planned); the by-eye reading
  of H1–H8 and `scry report` for one run (plan 1); the full-sample sync and batch runs after the phases
  (`cost_summary` already shows the batch price).
- **Placeholders.** None in the tasks: every test names its fixture and expected values. The worked examples of Task
  4 use real lifetimes of `runs/p0` and supposed interpretations, and say which is which.
- **Type consistency.** `RunSpec`, `Matrix`, `Span` (Task 2) are used in Tasks 3 and 9; `evalrun.json`'s fields (Task
  3) in Task 7; `AskOutcome` and the adapter functions (Tasks 4, 5) live in `adapters.py`, the only importer of the
  siblings' loaders, search index and `ask`; `Question.key` (Task 5) is the unit key in Tasks 6–8; `Judgment` (Task
  6) in Task 7; `METRICS` names (Task 7) equal the `units` keys of Tasks 4 and 7 and the rows of Task 8;
  `scaled_floor` and `same_config_diffs` are used by `compare_configs` in the same module.
- **Review focus.** Each of the five lines names its test or worked example.
