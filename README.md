# agentic-escort — `scry`, a visual transcript pipeline

`scry` turns a silent screen-recording tutorial (terminal, editor, browser portal) into an exact,
timestamped, queryable "visual transcript": every distinct screen state with its text and layout,
every change between states with what the user did, a step/section hierarchy, and a searchable index.

- Design: `docs/proposals/2026-09-21-boxes-mode-rebase.md` is the specification the code follows (the re-base on OCR
  boxes); `docs/visual-transcript-pipeline-design.md` (revision 6.2) describes the pipeline before the re-base
- Implementation plans: `docs/superpowers/plans/` (the v1 plan of 2026-09-13; the re-base plans `2026-09-21-rebase-boxes-1` to `-4`)
- Evaluation results: `docs/results/`
- Decisions made without the owner present: `docs/decision-ledger.md`; what is open: `docs/open-items.md`
- Design reviews: `docs/reviews/`
- Contributing: `CONTRIBUTING.md`

## Setup (macOS, Apple Silicon)

    uv sync
    uv run scry setup            # checks the OCR engine, FTS5, sqlite-vec, credentials

Model calls use the Anthropic SDK. Credentials, in order of preference: `ant auth login` (no key to store), or an
`ANTHROPIC_API_KEY` in a git-ignored `.env` file at the repo root (`cp .env.example .env && chmod 600 .env`, then fill
it in); `scry` loads `.env` at startup and a variable already in the environment always wins.

## Run

    uv run scry run assets/create-aks-cluster-tutorial.mp4 --out runs/aks
    uv run scry ask runs/aks "what command created the cluster?"

The stages, in order: `decode, outline, read, track, annotate, interpret, summarize, index`; then `ask` answers a
question over the index. `decode` and `outline` take the video and `--out`; every other stage takes the run directory
(`scry read runs/aks`), is idempotent and skips itself when its inputs and configuration are unchanged; `scry run … --stages
read,track` runs a selection. Beside the stages:

- `scry subset runs/aks --out runs/smoke --frames 145-155` derives a small run from decoded frames, for cheap live checks;
- `scry report <run-dir> [--frames 155-187] [--ground-truth <list>]` writes what `track` measured, with evidence sheets;
- `scry eval run|judge|report <matrix.toml>` (the matrices are in `evals/`): `run` executes the matrix's runs, each
  cold in its own directory under `runs/eval/<phase>/` (costs money; `--dry-run` lists the runs, validates every config
  and spends nothing; `--only <run name>` executes that one run, so several can go side by side; a run whose `[read]`
  is the source's gets the source's `boxes.jsonl` for its frames and skips `read`, OCR being deterministic and no model
  call: `ocr_imported_from` in its `evalrun.json`); `judge` has a
  separate model call score each answer against its rubric lines; `report` calls no model and writes
  `docs/results/<phase>/report.md` and `scores.json`. A matrix with a `[copy]` table (run name = the directory of a
  finished run) builds nothing: it copies the pipelines of those runs and only asks the questions again, so its only
  stage is `ask` (`evals/p6.toml`).

Configuration is `scry.toml` in the working directory, or the file given with `--config`; a missing file means the
defaults of `src/scry/config.py`. `[annotate] mode` is `"incremental"` by default and `transcribe` is `false` (group-only: the model labels windows, popups, links and the screen description, and gives no second reading of the text; ledger L73): a call for the first frame and for every frame
whose pixels changed, labelling only the boxes whose lifetime starts at that frame or continues there by a move. `"every_frame"` labels every box of
every frame, and `"off"` runs the pipeline with no annotation. `[ask] frames = false` withholds every image from the
answering agent, so that it answers from the index alone; `[ask] model` puts the answering agent on a model of its
own (empty: the pipeline's). `[model] mode = "batch"` sends `annotate` and `interpret`
through the Message Batches API; on the whole sample that paid 0.68 of the synchronous price, not half (ledger L62).

## Tests

    uv run pytest

## Status (2026-09-21)

The pipeline was re-based on OCR boxes (branch `rebase-boxes`): `read` detects and reads text boxes, `track` follows them
across frames into lifetimes and transitions, `annotate` has a model group and label them, `interpret` says what the user
did at each transition, `summarize` builds steps and sections, `index` makes it all searchable for `ask`. Every stage is
unit-tested over synthetic frames, hand-written records and fake model clients; no test touches the sample video or the
network. Nothing is merged to `main`, which is at the tag `pre-rebase-boxes`. The paid evaluation phases are reported
under `docs/results/` (P1 to P7 so far); what each showed is in the ledger (rows L57, L59, L60 and L62 to L65), and
open items are in `docs/open-items.md`.

Model calls use `claude-opus-5` (`[model] model`). Retrieval is lexical-only until an embedder is configured
(`[index] embedder`). A stage re-runs only when its inputs or its configuration section change; after a code change to
a stage, delete its entry from `runs/<id>/manifest.json` (or the run directory).
