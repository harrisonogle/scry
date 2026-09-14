# Open items

Things that are known to be undone, unverified, or worth revisiting. Decisions and their rationale live in
`docs/decision-ledger.md`; questions the evaluation harness must answer live in the design's §22; the v2 roadmap is the
design's §21. This list is the short "what next" view across all three.

## Before the first real run

- [x] **Credentials.** Done 2026-09-13: `.env` holds `ANTHROPIC_API_KEY` and `uv run scry setup` reports it. On a new
      machine: `cp .env.example .env && chmod 600 .env`, fill in the key (or `ant auth login`), confirm with `uv run scry setup`.
- [ ] **First paid run on the sample** (`uv run scry run assets/create-aks-cluster-tutorial.mp4 --out runs/aks`;
      ≈ $18–45 on `claude-opus-5`, half in batch mode). Stages 2c, 5, 6 and the agent have only been exercised on their
      no-credentials error path. Read `manifest.json` → `diagnostics` afterwards: `agree_fraction`, `rows_rejected`,
      `grouping_repairs`, `invalid_refs`, refusals, cost.
- [ ] **Revisit the embedder default.** Retrieval is lexical-only (`[index] embedder = "none"`) because the local ONNX
      model could not be downloaded during a transient network fault (ledger L9). With the network working, try
      `embedder = "fastembed"` (`uv sync --extra embed`) and see whether semantic questions improve.

## Needs the owner (hand-made ground truth, design §18.1)

- [ ] Two fully annotated videos, the 20-frame calibration set, the question set. Everything in §18.2 is unmeasurable
      until then; integration tests are deliberately absent.
- [ ] With ground truth: the OCR bake-off (Apple Vision vs RapidOCR), the model/effort bake-off, and tuning the §16
      parameters (`still_s` in particular decides how finely typing is split into states).

## Known limitations observed on the sample (details in the design)

- The terminal cursor in the sample does not blink, so terminal frames carry no caret signal; focus there rests on the
  retrospective and VLM signals (§7.5, §9.4).
- Apple Vision misreads seen on fixtures: a dropped hyphen in `--resource-group`, `C:\` read as `Ci\` (§5.4, §22
  #14–15). When OCR and VLM disagree the fused text is the OCR reading, which broke the typed-command rule once (§22 #15).
- About 1 % of overlay labels cannot avoid every text box in dense portal screens (`label_clashes` in the manifest).
- A stage re-runs only when its inputs or configuration change, not when its code changes; delete the stage's entry
  from `runs/<id>/manifest.json` after editing a stage.

## Unverified claims marked in the design

- Search the design for `[verify]`: Batches `custom_id` limits and Files API references inside batch requests (§20.7),
  the Windows OCR port (§20.8), the Gemini `interactions` input shape (§6, Task 20), the macOS floor for Vision
  revision 3.
