# Contributing

`scry` turns a screen recording into a text-based, hierarchical index of what happened on screen, which an AI agent
can query with a citation for every claim. The specification is `docs/proposals/2026-09-21-boxes-mode-rebase.md`; the
code implements it. This file is the sequence a contributor follows, from clone to pull request. It was developed on a
Mac with Apple Silicon; the OCR engine is RapidOCR (ONNX, bundled models, downloaded at first use), and nothing in the
pipeline is macOS-only.

## Get running

1. **Install `uv`** (`brew install uv`). It downloads a suitable Python (3.12 or newer) on its own if none is present.
2. **Clone and sync.** From the repo root:

       uv sync

   This creates `.venv`, installs the pinned dependencies from `uv.lock` (including pytest), and installs the `scry`
   command. Every command below runs as `uv run scry …` from the repo root.
3. **Check the environment:**

       uv run scry setup

   It reports the OCR engine, SQLite FTS5, sqlite-vec, and whether credentials are visible.
4. **Credentials, only if you will run the model stages.** The local stages (decode, read, track, index)
   need none. Otherwise either log in with the Anthropic CLI (`brew install anthropics/tap/ant`, then `ant auth login`),
   or create a git-ignored `.env` at the repo root:

       cp .env.example .env
       chmod 600 .env        # then fill in ANTHROPIC_API_KEY

   `scry` loads `./.env` at startup; a variable already in the environment always wins. Never put a key in `scry.toml`
   or in your shell profile.
5. **Run the tests:**

       uv run pytest

   They take a couple of seconds, use no network and no video.
6. **Try the pipeline on the sample without spending anything:**

       uv run scry run <a screen recording>.mp4 --out runs/aks --stages decode,read,track

   Outputs land in `runs/aks/` (git-ignored). Dropping `--stages` runs the model stages too, which costs money: a
   four-minute portal session cost $9.32 and a fourteen-minute tutorial $16.30 at the default configuration on
   `claude-opus-5` (`docs/results/`); `[model] mode = "batch"` paid about 0.68 of that.
7. **Read, in this order:** `README.md` (commands and configuration), `docs/proposals/2026-09-21-boxes-mode-rebase.md`
   (the specification), `docs/decision-ledger.md` (why things are the way they are), `docs/results/` (what was
   measured), and `docs/reviews/` (what independent reviewers found and how it was resolved).

## Make a change

1. **Branch from `main` and open a pull request.** The direct-to-`main` history of the first day was a one-off
   (ledger L8).
2. **Tests stay unit tests.** Synthetic frames rendered in the test, hand-written records, or the fake model client in
   `tests/test_provider.py`. No test may read the sample video or touch the network. Integration tests wait for the
   hand-made ground truth described in design §18.1; do not add them before it exists.
3. **The design is the contract.** If you change a rule the design states (a threshold, a state-machine transition, a
   repair rule, a file's owner), update the design section and add a line to §24. Parameters live in `scry.toml` and
   `src/scry/config.py`, never as literals in stage code.
4. **One file per stage, written by that stage only** (design §10.7). Later signals go in sidecar files that the loaders
   in `src/scry/run.py` merge on read. Do not make a stage rewrite another stage's output.
5. **Re-running a stage after a code change.** The skip logic keys on input hashes and the configuration section, not on
   code. Delete the stage's entry from `runs/<id>/manifest.json` (or the run directory) to force it.
6. **Model-stage changes cost money to exercise for real.** Test against the fake client first, then on a run directory
   trimmed to a few frames: `uv run scry subset runs/aks --out runs/smoke --frames 145-155` followed by
   `uv run scry run <video> --out runs/smoke`. Every model call is cached under `runs/<id>/cache/` (a subset shares its
   source's cache); a re-run with unchanged inputs makes no API calls.
7. **Before you commit:** `uv run pytest` is green; nothing under `runs/`, no `.env`, and no cache files are staged
   (`.gitignore` already covers them); commit messages say what changed and why.

## Where things are

| Path | What |
|---|---|
| `src/scry/` | the package: one module per stage, `providers/` for model calls, `prompts/` for prompt contracts |
| `tests/` | unit tests; `conftest.py` renders synthetic videos |
| `scry.toml` | every tunable parameter (design §16) |
| `docs/visual-transcript-pipeline-design.md` | the design, revision history in §24 |
| `docs/superpowers/plans/` | the implementation plan that produced v1 (historical; the code is the source of truth) |
| `docs/decision-ledger.md` | decisions made without the owner present, with rationale and how to undo each |
| `docs/reviews/` | archived design and plan reviews |
| `runs/` | per-video outputs (git-ignored) |
