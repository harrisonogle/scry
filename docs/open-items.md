# Open items

Things that are known to be undone, unverified, or worth revisiting. Decisions and their rationale live in
`docs/decision-ledger.md`; questions the evaluation harness must answer live in the design's §22; the v2 roadmap is the
design's §21. This list is the short "what next" view across all three.

## Before the first real run

- [x] **Credentials.** Done 2026-09-13: `.env` holds `ANTHROPIC_API_KEY` and `uv run scry setup` reports it. On a new
      machine: `cp .env.example .env && chmod 600 .env`, fill in the key (or `ant auth login`), confirm with `uv run scry setup`.
- [x] **Live smoke of the model stages** on 11 frames (ledger L28–L29): contract verified, overlay labels fixed,
      measured cost ≈ $0.076 per frame for Stage 2c and ≈ $0.042 per transition for Stage 5.
- [ ] **First full run on the sample** (`uv run scry run assets/create-aks-cluster-tutorial.mp4 --out runs/aks`;
      projected ≈ $27 sync or ≈ $14 with `[model] mode = "batch"`, ~25 min wall; the 11 smoke frames are cache hits).
      The two tuning items below are decided (ledger L36–L37); merge is free to re-run if either is revisited.
      Read `manifest.json` → `diagnostics` afterwards: `agree_fraction`, `rows_rejected`, `invalid_refs`, refusals, cost.
- [ ] **Revisit the embedder default.** Retrieval is lexical-only (`[index] embedder = "none"`) because the local ONNX
      model could not be downloaded during a transient network fault (ledger L9). With the network working, try
      `embedder = "fastembed"` (`uv sync --extra embed`) and see whether semantic questions improve.

## Findings from the smoke run (ledger L28–L29)

- [x] **`[merge] row_gap_lines = 3` rejects the rows the prompt asks for.** 135 of the 165 rejected rows on the
      smoke are label/value pairs and table rows whose column gap is 7–25 line heights; the y-spread test already
      catches marks from different lines. Re-merging the cached data in memory: 10 → 75 rejected, `agree_fraction`
      0.495; 30 → 58, 0.518; off → 30, 0.553. Off since 2026-09-21 (`row_gap_lines = 0`, ledger L37): the owner calls
      the cap a finicky heuristic, the diff runs per unit since L31, and rows-as-boxes (below) may retire rows entirely.
- [ ] **The typed-command rule missed the `az login` keystroke (T9 on the smoke).** OCR read `Users \msadmin` with a
      space on frame 154 and `Users\msadmin` on 155; the fused text is the OCR reading whenever the readers disagree,
      so the longest-common-prefix test failed (§22 #15, second occurrence; L24 said to prefer the VLM reading if it
      recurred). Options: a whitespace-insensitive prefix test in `_typed_op`, or prefer the VLM reading in `Line.fused`
      when the two are near-identical, or both. Separate question for §22: both readers transcribe the shell's grey
      inline autocomplete (`login`) as if typed.
- [ ] **Harmless `RuntimeError: Event loop is closed` tracebacks** at the end of every async stage: the
      `AsyncAnthropic` client is never closed inside the loop. Close it at the end of `_run_with_batches`.
- [ ] **Usage accounting.** `run_perceive` sums only three usage keys, dropping `cache_creation_input_tokens` from the
      manifest; `estimate_cost` ignores cache-creation tokens (billed at 1.25× input). ≈ $0.05 on the smoke.
- [ ] **Batch mode** (`[model] mode = "batch"`) is still unexercised live.
- [x] **Overlay A/B** (ledger L30): a per-mark coordinate list and 16-px labels are within noise of the 12-px opaque
      tags; both stay off. Residual id errors (6 % of rows) are identical lines on one screen, e.g. two 'Node pools';
      per-pane crops (design §21) are the literature's answer if that ever matters.
- [x] **Pane segmentation is unstable between near-identical frames** (the same portal page is 8 panes in frame 150
      and 3 in frame 155), so panes "appeared" and "disappeared" and their lines showed up as deleted and inserted
      noise while the windows were stable in all 11 frames. Correspondence and the diff now run over window-level
      units (parent-null regions plus popups); panes are labels only (ledger L31, design §11.1 revision 5.5).
- [x] **Most structural ops on near-static transitions were OCR jitter.** On the five smoke transitions with
      < 0.3 % of the screen changed, 90 of 96 ops sat on lines with no changed pixel. Stage 4 now gates those ops with
      Stage 1's pixel rule (`[diff] pixel_gate_max_fraction = 0.05`): 81 ops vetoed on `runs/smoke-pixelgate`, T9
      reduced to the one PowerShell prompt op. On a gated transition the typed and output rules need an op under
      changed pixels; no-box VLM-only rows ride along but are not evidence (ledger L32, design §11.2–§11.3 revision 5.7).
      Since L38 each component is grown by half a line height (`pixel_gate_margin_lines = 0.5`) before the test; on
      `runs/smoke-rapid-margin` that changed no op and no veto.

## Proposed after the smoke runs (owner's call)

- [ ] **Index both readings.** Findability is the top UX priority and today only the fused text is searchable, which is
      OCR's reading on any disagreement (`inttooliction o azure kunerneras sorwice` for a line the model read cleanly).
      Adding the model's reading to the region node text in Stage 7 is small and needs no model calls.
- [ ] **Typed rule: compare either reading** (§22 #15, third option). Preferred over a whitespace-blind prefix test,
      which would loosen what counts as typing; making the model's reading the fused text (L24's suggestion) is held
      for ground truth because near-identical readings are where a model "completion" hides.
- [x] **Default OCR engine: `rapid`** (owner, 2026-09-21; ledger L36). Measured (L35): mark match 0.726 → 0.920, disagreeing
      lines 19.5 % → 4.7 %, the typed event fires, at +1.1 s OCR per frame and +29 % Stage 2c output tokens. The row gap
      test went off rather than wider (L37). Vision stays selectable on macOS.
- [ ] **Rows as OCR boxes plus model-proposed associations.** If rows exist to pair labels with values, ask the model
      for the associations between box ids and drop the row geometry checks and the repair pass; the diff no longer
      needs rows as its unit once the pixel gate (L32) and box-level matching carry it. Decide after the engine change.
- [ ] **Windows and popups only in the Stage 2c schema.** Panes are labels since L31; asking for them still costs
      output tokens and is where the model's grouping churns.
- [x] **Stage 5 image scale.** Measured (L39): half scale keeps the descriptions at 47 % of the cost; now the default.
- [x] **Masking the text for Stage 2c** (owner's three variants plus re-rendered text at half scale): not adopted (L40).
- [x] **Vision misses the grey label column** on portal pages; addressed by the engine change (L34).

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
