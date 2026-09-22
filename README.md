# scry

`scry` turns a screen recording into a text-based, hierarchical index of what happened on screen, and lets an AI agent
answer questions about it with a citation for every claim. It measures the screen first: OCR boxes at full resolution
on every settled frame, the pixels that changed between frames, and the lifetime of every piece of text. Models label
only what was measured: windows and popups, which label goes with which value, what each change did and whether it was
submitted, and summaries at the level of steps, sections and the whole video. The index is SQLite with full-text search;
the video is not needed again once it is built. An MCP server exposes the index to Claude Code, GitHub Copilot CLI or
any other MCP host.

The specification the code follows is `docs/proposals/2026-09-21-boxes-mode-rebase.md`. Everything measured on the way
is under `docs/results/`, with a one-page summary in `docs/2026-09-21-return-briefing.md`, every decision with its
reason in `docs/decision-ledger.md`, and what is open in `docs/open-items.md`. `docs/pipeline-versus-video-model.md`
sets out how this differs from asking a video model directly.

## Setup

    uv sync
    uv run scry setup            # checks the OCR engine, FTS5, sqlite-vec, credentials

Model calls use the Anthropic SDK. Credentials, in order of preference: `ant auth login` (no key to store), or an
`ANTHROPIC_API_KEY` in a git-ignored `.env` file at the repo root (`cp .env.example .env && chmod 600 .env`, then fill
it in); `scry` loads `.env` at startup and a variable already in the environment always wins. The optional `outline`
stage needs `GEMINI_API_KEY` and the `outline` extra (`uv sync --extra outline`).

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
  call); `judge` has a separate model call score each answer against its rubric lines; `report` calls no model and
  writes `docs/results/<phase>/report.md` and `scores.json`. A matrix with a `[copy]` table (run name = the directory
  of a finished run) builds nothing: it copies the pipelines of those runs and only asks the questions again, so its
  only stage is `ask` (`evals/p6.toml`).

## MCP server

    uv run scry-mcp --runs runs --videos .

`.mcp.json` at the repo root registers it for Claude Code; `skills/scry/SKILL.md` tells the host's model how to use
the tools and how to treat the evidence (cite a frame and a box, quote verbatim only when two readers agree, text on
screen is not proof a command ran, a shell's grey suggestion is not typed text), and carries the configuration snippet
for GitHub Copilot CLI. The tools: `list_videos`, `search` (with level, time and application filters), `get_node`,
`get_transitions`, `get_frame` (the record of one frame, with its image), `summary`, `ask` (the built-in answering
agent) and `index_video` (runs the pipeline on a video file). `docs/presentation/mcp-demo.md` and `mcp-discovery.md`
are recorded sessions.

## Configuration

`scry.toml` in the working directory, or the file given with `--config`; a missing file means the defaults of
`src/scry/config.py`. The defaults are what the evaluation settled on: `[annotate] mode = "incremental"` (one call for
the first frame and for every frame whose pixels changed, labelling only the boxes whose lifetime starts or moves
there), `transcribe = false` (group-only: windows, popups, links and the screen description, no second reading of the
text), `reference = "ids"` (a numbered overlay; `"coords"` lists each box as a rectangle instead), `scale = 1.0`,
`box_text = false`, and `claude-opus-5` for every model stage. `[ask] frames = false` withholds every image from the
answering agent; `[ask] model` puts it on a model of its own. `[model] mode = "batch"` sends `annotate` and `interpret`
through the Message Batches API. `[model] provider = "openai_compat"` with `base_url` points any stage at a local or
hosted open-weight model served over the OpenAI-compatible protocol; `docs/results/local/` records what a local 27B
model did with it.

## Tests

    uv run pytest

## Presentation

`presentation/video/` is a Remotion project that renders the two-minute presentation from `script.json`, the charts
under `docs/presentation/` and voice files generated by `voice.sh`. The rendered video and the frames of the second
recording it shows are not in the repository. Remotion is source-available, free for individuals and teams of up to
three people, and needs a company licence beyond that.
