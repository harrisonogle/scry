# agentic-escort — `scry`, a visual transcript pipeline

`scry` turns a silent screen-recording tutorial (terminal, editor, browser portal) into an exact,
timestamped, queryable "visual transcript": every distinct screen state with its text and layout,
every change between states with what the user did, a step/section hierarchy, and a searchable index.

- Design: `docs/visual-transcript-pipeline-design.md` (revision 3)
- Implementation plans: `docs/superpowers/plans/` (the v1 plan of 2026-09-13; the re-base plans `2026-09-21-rebase-boxes-1` to `-4`)
- Evaluation results: `docs/results/`
- Decisions made without the owner present: `docs/decision-ledger.md`
- Design reviews: `docs/reviews/`
- Contributing: `CONTRIBUTING.md`

## Setup (macOS, Apple Silicon)

    uv sync
    uv run scry setup            # checks Vision OCR, FTS5, credentials

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
- `scry eval run|judge|report <matrix.toml>` runs an evaluation matrix cold (costs money; `--dry-run` spends nothing), has a
  judge model score the answers, and writes `docs/results/<phase>/report.md`.

## Tests

    uv run pytest

## Status (2026-09-21)

The pipeline was re-based on OCR boxes (branch `rebase-boxes`): `read` detects and reads text boxes, `track` follows them
across frames into lifetimes and transitions, `annotate` has a model group and label them, `interpret` says what the user
did at each transition, `summarize` builds steps and sections, `index` makes it all searchable for `ask`. Every stage is
unit-tested over synthetic frames, hand-written records and fake model clients; no test touches the sample video or the
network. The first paid evaluation (P1, frames 155 to 187 of the sample video, 18 cold runs) is in `docs/results/p1/`;
what it showed and what follows is ledger row L57; open items are in `docs/open-items.md`.

Model calls use `claude-opus-5`; `[model] mode = "batch"` in `scry.toml` halves the price of `annotate` and `interpret`.
Retrieval is lexical-only until an embedder is configured (`[index] embedder`). A stage re-runs only when its inputs or
its configuration section change; after a code change to a stage, delete its entry from `runs/<id>/manifest.json` (or
the run directory).
