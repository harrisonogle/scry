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
