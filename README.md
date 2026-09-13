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

## Status (2026-09-13)

Every stage of the design is implemented and unit-tested (76 tests over synthetic frames, hand-written records and a
fake model client; no test touches the sample video or the network). What has and has not been exercised for real:

| Stage | Verified on the sample video | Notes |
|---|---|---|
| 1 decode / detect / settle | yes — 221 frames emitted (192 settled) from 14.2 min of 1080p/30 fps in ~4 min 40 s | median 2.7 s between states; carets found on 29 frames (the sample's terminal cursor does not blink, so terminal frames have none) |
| 2a OCR (Apple Vision) | yes — 13.3k lines, ~53 per frame, 33 s total | Vision reports confidence 1.0 almost everywhere; `agree` (Stage 3) is the real signal |
| 2b overlays | yes — 6 s, ~1 % of labels could not avoid every box | |
| 2c perception, 5 interpretation, 6 hierarchy, 7 agent | **no live calls** — no Anthropic key on the build machine | exercised on a synthetic run without credentials: errors are recorded per record, nothing is cached, later stages fall back and complete |
| 3 merge, 4/4b diff + coalescing, 7 index + search | on the synthetic run | with OCR-only regions (the perception fallback) |
| 0 outline (Gemini) | no | optional; `--import` a JSON outline instead |

To run the model stages: set `ANTHROPIC_API_KEY` (or log in with the `ant` CLI) and re-run `uv run vt run … --out runs/aks`;
finished stages are skipped and the ≈ 221 frames go through perception and interpretation (design §19.6 estimates
$18–45 on `claude-opus-5`; halve it with `[model] mode = "batch"` in `vt.toml`). Retrieval is lexical-only until an
embedder is configured (`[index] embedder`). A stage re-runs only when its inputs or its configuration section change;
after a code change to a stage, delete its entry from `runs/<id>/manifest.json` (or the run directory).

Known limitations worth knowing before the first real run are listed in the design's §22 (open questions) and in the
decision ledger (L23–L26).
