# Cold review: docs/visual-transcript-pipeline-design.md (revision 2)

Reviewer stance: skeptical senior systems engineer, no prior context. Every "[measured]" below was run on this machine in the probe environment on 2026-09-13 against the sample video (`assets/create-aks-cluster-tutorial.mp4`, 1920x1080, 30 fps, 852.8 s) or synthetic frames; no model API calls were made.

## Findings, ranked

### Blocker

**B1. §7.2 / §16 — the 3x3 morphological opening erases typed text, so typing never triggers a change.**
Problem: text strokes at terminal sizes are 1–2 px wide; a 3x3 opening (erode then dilate) removes every pixel without a full 3x3 changed neighbourhood. [measured] Synthetic 15-px Menlo on a dark background: `gi -> git` = 29 changed px at full res, **0 after opening**; `statu -> status` = 37 -> 0; a whole `git status` typed at once = 323 -> **0**; a capital `W` = 66 -> 42 (< θcomp=64, < θcount=150: still no trigger). Half-resolution numbers are the same story (10/13/120 -> 0). On the real video (600–690 s, half-res, thresholds/4) 14 of 79 triggering frames are lost to the opening, and every lost one is a keystroke-sized change on the PowerShell prompt row (bboxes 8–56 px wide, 10–14 px tall at x≈844–926).
Why it matters: §7.3's typing-pause behaviour, §11.3 Rule 1, §9.4's retrospective focus, and §18.2's `t_change` timing all assume keystrokes (or at least commands) produce emitted frames. As specified they do not; a command only surfaces when its output appears, with `t_change` = the output's time, and commands with no output (`cd`, assignments, `az login`) may never produce a frame at all (a new 15-px prompt line is also erased).
Proposed change (replace the §7.2 block):
```
delta    = |luma_f − luma_prev|                      // unmasked pixels
changed  = delta > θpix                              // θpix = 12
blobs    = dilate(changed, 3×3)                      // merge the strokes of one glyph/word; NO opening
comps    = label(blobs, 8-conn); area(c) = count of *changed* (pre-dilation) pixels in c
comps    = [c for c in comps if area(c) ≥ θmin]      // θmin = 8 px: removes every I-frame residual blob measured (≤ 8 px, see "checked")
comps    = [c for c in comps if not caret_shaped(c)] // bbox ≤ 3 px wide and 8–30 px tall at the tracked caret position ±2 px (§7.5)
trigger  = any(area ≥ θcomp) or Σ area ≥ θcount      // θcomp = 24 (lowercase glyph at 15 px ≈ 25–40 px), θcount = 100
```
Detect at full resolution, or compute `delta` at full resolution and reduce with a 2x2 **max** (not mean) before labeling; calibrate the half-res thresholds on a synthetic typing fixture in `tests/` (single glyph must trigger, 2x18 caret must not). Add that fixture to §18.2 as a unit test, not a ground-truth metric. Accept that a lone `l`/`i`/`|` keystroke is caret-shaped and gets bundled with the next one.

**B2. §7.3 + §7.4 — the churn mask suppresses the novelty test and the max-hold, so continuously scrolling output is never captured.**
Problem: once a scrolling pane is masked, `trigger(f, prev)` is false, so `changed` never becomes true, so the max-hold clause (`if changed and t − tChange ≥ M`) never fires. §7.4's "Max-hold M still emits frames periodically, so nothing stalls" is false under the pseudo-code as written. Worse, `trigger(f, last)` is also masked, so when the scroll ends the final state is not novel either; the finished output only appears bundled into the next unrelated change (e.g. the next command's first keystroke), with the wrong `t_change`. The mask releases only 4 s after the scroll stops (ρ_off = 0.2 of a 5 s window), by which time nothing re-runs the novelty test.
Why it matters: `az aks create`, `kubectl get ... -w`, package installs — the sample corpus is full of long scrolling output, and its end state (success/failure text) is the most-asked-about content.
Proposed change (add to §7.3, referenced from §7.4):
```
mask is applied to the stillness test trigger(f, prev) ONLY; novel(f, last) is always evaluated unmasked
each frame, after updating the mask:
  if any churn region active and !changed: changed = true; tChange = t      // keeps the max-hold clock running → an unsettled frame every M
  if churn region R deactivated this frame:
      changed = true; tChange = tLastChange(R); tStill = tLastChange(R)     // tLastChange(R): last frame with any changed pixel inside R (known from the ring buffer)
      // the normal settle path then emits the final state with the right times, or upgrades `last` (see M1)
```

**B3. §8.2 — the label-placement rule draws the number inside the text box on roughly a quarter of lines, occluding the first characters the VLM must transcribe verbatim.**
Problem: labels go "just outside the box's top-left corner", else inside it. With 16–17 px line pitch the "outside" slot is the previous line's box. [measured] Applying the rule as written to Vision output: frame_300 (portal form) 13/52 labels forced inside (25%); frame_600 (portal + terminal) 26/99 (26%). An 11-px digit block inside a 16-px box covers the top of the first 1–3 characters (`PS `, `az `). The overlay is the only image Stage 2c sees.
Why it matters: R1 fusion depends on the VLM reading exactly what OCR read; systematic occlusion turns `agree=false` into a placement artifact, and the VLM "completing" an occluded prefix is precisely the correction the design forbids.
Proposed change: (1) Stage 2c sends two images: `Image 1` = clean frame, `Image 2` = overlay; contract: "transcribe from Image 1; use the numbers in Image 2 only to group". Cost +2.7k input tokens/frame (≈ +$0.013 on Opus 5); per-image caps are unaffected. (2) Placement order: left gutter (`x0 − label_w − 2`) if that rectangle intersects no OCR box, else right of the box (`x1 + 2`), else above, else below; never inside. Code asserts no label pixel lies inside any OCR box and records `label_clashes` per frame in the manifest. Keep the "no padding/border" rule.

### Major

**M1. §7.3 — settle state machine: no end-of-stream flush; max-hold can fire during an in-progress still run; a max-hold frame that turns out to be the end state is never marked settled; `tStill` is one frame late.**
Traces: (a) video ends 200 ms after the last output appears → `changed` is true, loop exits, final state never emitted. (b) motion 0–2.8 s, still from 2.8 s; at 3.0 s `t − tChange ≥ M` fires with `tStill = 2.8` → emitted `settled=false`, `tChange = 3.0`; at 3.2 s the still run completes but `trigger(f, last)` is false (same pixels) → nothing emitted, `changed=false`: the state that did settle at 2.8 s is recorded as unsettled forever. (c) same outcome whenever motion stops right after any max-hold. (d) the first still frame `f` equals `prev`, so the state was on screen at `t_prev`, not `t`.
Proposed replacement:
```
emit(f0, tChange=t0, tSettled=t0, settled=true); prev=last=f0; changed=false; tStill=∅
for each frame f at t (tPrev = time of prev):
  if trigger(f, prev):                                  // masked stillness test
     if !changed: changed=true; tChange=tPrev
     tStill=∅
  elif changed:
     if tStill==∅: tStill=tPrev
     if t − tStill ≥ S:
        if novel(f, last): emit(f, tChange, tSettled=tStill, settled=true); last=f
        elif !last.settled: last.settled=true; last.t_settled=tStill   // max-hold frame was the end state
        changed=false
  if changed and tStill==∅ and t − tChange ≥ M:         // max-hold only while actually moving
     emit(f, tChange, tSettled=t, settled=false); last=f; tChange=t
  prev=f
end of stream: if changed and novel(prev, last): emit(prev, tChange, tSettled=(tStill or tPrev), settled=(tStill≠∅))
last emitted frame: t_end = container.duration (stream.frames is 0 on the sample; do not rely on a frame count)
```
`novel()` is the unmasked test from B2. Since frame records are appended to JSONL, the `last.settled` upgrade requires Stage 1 to buffer the last record until it is superseded.

**M2. §9.0 / §9.2 / §11.2 — the fragment join is applied to OCR lines but not to `vlm_lines`, breaks the §9.2 alignment predicate, and (without a horizontal limit) merges text across windows that share a baseline; §9.2's "fusion does not depend on the region tree" is false once the join precedes it.**
Problem: the VLM sees one mark per OCR fragment and is told "one entry per line"; after the join an OCR row `Status : Succeeded (Running)` is one line while the VLM plausibly emits two entries → normalized similarity of a fragment against the joined row is far below 0.8 → OCR-only + VLM-only instead of matched. [measured] frame_600 has the terminal's title bar (`Administrator: PowerShell 7-preview (x64)`, x=667) on the same row as the portal's `Status` / `: Succeeded (Running)` (x=301/402): one mis-assigned mark and the join produces a garbled line, so a grouping error now corrupts text, contradicting D4's separation.
Proposed change: make the VLM the arbiter of rows (grouping is its job, geometry is OCR's): add to the §8.3 schema, per leaf region, `rows: [["l7","l8"],["l9"],[]]` with `vlm_lines[k]` the verbatim transcription of `rows[k]` (`[]` = a row OCR missed). Code joins OCR fragments exactly as `rows` says (single space, `merged_from`, union bbox), rejects a row whose marks differ in y-centre by > 0.5 × median line height or whose neighbouring marks are > 3 × line height apart horizontally (split it, flag `row_rejected`), then aligns `vlm_lines[k]` to row k directly; LCS is needed only to place `[]` rows. Delete the "0.5 × median line height" join rule and the `merged_from` sentence in §9.0 accordingly, and move "fusion is independent of grouping" to "independent of *window* grouping".

**M3. §9.3 — `layout_conf` penalises the corpus's normal layout (a foreground window over a background window) and the scatter rule fires on ordinary panes; the JSON example contradicts the rule.**
Problem: region bboxes are text extents; a browser behind a terminal has bbox ≈ the whole screen, so every terminal line's centre lies inside it → penalty 0.6 → `layout_conf` 0.35 for the terminal. §10.1's example shows r1 at 0.9 with r2 = [0,0,1920,1080], impossible under the rule. Σ(line areas)/area(bbox) < 0.3 is normal for a terminal with one long line and short prompts, or a left nav.
Proposed change:
```
score = region.conf
for each member line L: for each region R' (not ancestor/descendant, not in region.occludes) that has a LINE whose bbox
    overlaps L vertically by ≥ 50% of L's height and overlaps L horizontally: score −= 0.3   (cap 0.6)
row coverage = (# distinct text rows × median line height) / bbox height; if < 0.3: score −= 0.2
singleton: min(score, 0.6); clamp
```
Fix the example values, and define `occludes` in §8.3: "regions this region visually covers, in whole or part".

**M4. §11.3 — coalescing rules fail on scrolling output, on backspaces/shell predictions, and on any concurrent op; the typed+output merge in the §10.2 example is not a stated rule; typed `text` and `frames` in the example contradict Rule 1.**
Problem: Rule 2 requires every op to be an `insert` at the bottom, but once the pane is full Myers also emits `delete`s at the top (scrolled-off lines) → the run breaks exactly for long outputs. Rule 1's "a prefix of b" fails on a backspace (`git stauts` → `git status`) and on PSReadLine inline prediction (grey suggestion text appears/disappears; the sample is PowerShell 7). "Exactly one op" breaks the run when a clock or status region changes concurrently. Rule 1 says `typed(text = b_final)` (the whole line) but the example shows `"git status"` while `a_first` was `PS C:\src> gi`, i.e. the suffix would be `t status`. The example's `output_appended` has `frames: [16, 16]`. Nothing says a typed run followed by an output run becomes one transition, yet T017 is exactly that.
Proposed change:
```
Rule 1 (typed): consecutive transitions whose ops restricted to region R are exactly one modify(a→b) on the same row
   with lcp(norm a, norm b) ≥ len(norm a) − 3; ops in other regions are permitted only on lines with in_churn=true.
   event typed(text = b_final[len(lcp(a_first, b_final)):], line = b_final, region, frames = [first.from_frame, last.to_frame])
Rule 2 (output_appended): ops in R are inserts at the end of R's list, optionally with deletes at the start (scroll);
   event output_appended(lines = Σ inserted, text = concatenation, region, frames = [first.from_frame, last.to_frame])
Rule 1b (command executed): a Rule-1 run immediately followed in the same region by a Rule-2 run is ONE transition with events [typed, output_appended].
kind of a coalesced transition = "unsettled" if any member transition is unsettled, else "coalesced". Transients (§11.4) are resolved before coalescing.
```
Fix the example (`frames: [15, 16]` or the true pair; `text` per the rule).

**M5. §11.1 — cross-frame region correspondence on text-extent IoU is brittle: extents change whenever text is added, empty regions have no bbox, names are free text, and there is no one-to-one assignment; `unassigned_lines` are never diffed.**
Problem: a terminal with 1 line then 30 lines has IoU ≈ 0.03; the "same name with any overlap" rescue depends on the VLM emitting byte-identical names across frames, which §10.6 admits it does not. Two panes in frame i+1 can both match one region in frame i. `bbox = [min x0 ...]` over zero lines is undefined (the §10.1 example has `r2.lines: []`). Text changes in `unassigned_lines` are invisible to Stages 4–5.
Proposed change: score every leaf pair `s = 0.5·J + 0.3·IoU + 0.2·[norm(app) equal]` (+0.2 if `norm(name)` equal), `J` = Jaccard over normalized line texts (0 if either side is empty); greedy one-to-one by descending `s`, accept `s ≥ 0.3`; regions with no lines get `bbox: null` and match on app+name only; diff `unassigned_lines` as pseudo-region `r0`; record the assignment and scores on the transition.

**M6. §10.2 / §10.3 / §13.3 — transitions carry no timestamps (R2), and the step `t` mapping is wrong at both ends.**
Problem: `transitions.jsonl` has only frame numbers. §10.3 says `t = [t_settled(first from_frame), t_change(last to_frame)]`: the start is when the *pre-state* appeared (possibly minutes before the first action) and the end is when the last change *began*.
Proposed change: transition record gains `"t": [t_end(from_frame), t_settled(to_frame)]` (coalesced: first from_frame's `t_end` to last to_frame's `t_settled`); steps/sections/video: `t = [children[0].t[0], children[-1].t[1]]`; `frames` as stated. Say so in §13.3 and fix the §10.3 example.

**M7. §9.2 / §10.1 / §10.2 / §10.6 — VLM-only lines have no ID, no sort position, no `in_churn`; `agree` is unspecified for unmatched lines; Stage 5 `refs` use `r1:l3`, which cannot identify a frame; Stage 5 refs are never validated.**
Problem: §11.2 sorts by `(y0, x0)` and §9.3 uses line centres — both undefined for `bbox: null`. Stage 5 spans two frames whose `r`/`l` IDs are independent, so `r1:l3` is ambiguous; §10.6 mandates `<frame>:<line>`. §18.2 wants "citation validity (refs exist)", but nothing keeps invalid refs.
Proposed change: VLM-only lines get IDs `v<n>` per frame, `bbox: null`, `in_churn: null`, `agree: null`, and a sort key interpolated from the aligned neighbours; OCR-only lines `agree: null`; Stage 5 `refs.lines` entries are `"<frame>:<line_id>"` validated against from/to/transient frames — invalid refs are dropped from `refs` and counted in `invalid_refs` (that count is the §18.2 metric); the §10.2 example becomes `["16:l3", "16:l4"]`.

**M8. §20.7 / §19.6 — Opus 5 runs adaptive thinking by default; thinking tokens bill as output and are absent from the cost model and the cache key; the validation-failure path for Stage 2c is unspecified.**
Problem: §19.6 assumes 1.5k output tokens/frame; with thinking on, a dense transcription call can spend several thousand more. The call-cache key omits `effort`, `thinking`, and `max_tokens`, all of which change outputs. §8.3 says the membership rule is "validated by code" but not what happens when it fails, nor what happens on `stop_reason == "max_tokens"` (truncated JSON) or a pydantic failure from `parse`.
Proposed change: per-stage `output_config={"effort": <config, default "low" for Stage 2c/5, "medium" for Stage 6>, "format": ...}`; cache key = SHA-256 of `(stage, model, effort, max_tokens, prompt_version, schema_hash, input_hashes)`; ladder: `max_tokens` hit → retry once at 2× (≤ 32k); schema failure → retry once with the error text; membership violation → repair in code (missing IDs → `unassigned_line_ids`, duplicates → first occurrence, unknown IDs dropped) and record `grouping_repairs` on the frame; never abort the run. Add a "thinking/output" line to §19.6 and confirm with `usage` on the 20-frame set.

**M9. §20.7 batch mode — one batch cannot hold a video's Stage 5 requests, and unattended resumption is unspecified.**
Problem: batches are capped at 256 MB. [measured] Sample frames encode to 119–453 KB PNG (160–600 KB base64); Stage 5 sends 2–3 per request, so ~300 transitions ≈ 350–550 MB. Nothing records batch IDs, so a crash while polling re-submits; `errored`/`expired` results are not handled.
Proposed change: chunk by serialized size (≤ 200 MB); persist `runs/<id>/batches.json` `{batch_id, custom_ids, status}` and resume from it; `errored`/`expired`/`canceled` results are re-queued into the next batch (invalid_request errors go to the manifest and the record gets `error`). Consider uploading each PNG once via the Files API and referencing `file_id` in Stage 2 and both Stage 5 calls (payload becomes text-sized) **[verify file references are accepted inside batch requests]**. `custom_id` = 64-hex cache key fits the 64-char limit exactly **[verify limit and charset]**.

**M10. §14.2 — the tokenizer plan works for indexing but breaks querying unless every term is phrase-quoted.**
[measured] SQLite 3.53.4: `unicode61 tokenchars '-_./:'` indexes `--resource-group`, `aks-demo-01`, `C:/src/app.py` as single tokens, but `MATCH '--resource-group'` → `syntax error near "-"`, `MATCH 'aks-demo-01'` → `no such column: demo`, `MATCH 'app.py'` → syntax error; the quoted forms `"aks-demo-01"`, `"C:/src/app.py"` match. `trigram` requires ≥ 3 characters (`az` → 0 hits) and is case-insensitive unless `case_sensitive 1`. `unicode61` folds case (`mycluster` hits `MyCluster`).
Proposed change: state the query builder: every term is emitted as an FTS5 phrase (`"..."`, inner quotes doubled); trigram queries only for terms ≥ 3 chars; exact-case verification is done against the stored payload, not the index; scoring via `bm25()`. Remove the **[verify]**.

**M11. §18.1 vs §18.2 — the ground-truth inventory does not contain what four of the metrics need.**
Stage 1 P/R and `t_change` error need a hand-marked state-change list (not listed); settle needs end-state/mid-animation labels; focus accuracy needs per-frame focused-window labels; coalescing P/R needs an action list (clicks, scrolls, key presses — "commands with time entered" covers typed only).
Proposed change: add to §18.1: (a) a hand-marked change list with times for ≥ 5 min of each video; (b) end-state labels for every emitted frame in those spans; (c) focused-window labels for the 20-frame set; (d) an action list for the same spans.

**M12. §20.9 / §9.4 / §10.1 — two stages mutate `frames.jsonl` after Stage 3 wrote it, breaking the hash-based skip rule and creating a race with optional Stage 0.**
Problem: retrospective focus (§9.4) is "written back into the frame record" by Stage 4b; `outline_chapter` is "filled after Stage 0 completes", and Stage 0 is optional and parallel. Which hash does "inputs unchanged" refer to, and who writes `outline_chapter` if Stage 0 finishes after Stage 3?
Proposed change: no stage writes an upstream file. Stage 4b emits `focus.jsonl`; `outline_chapter` is computed at read time from `outline.json` (join on `t_settled`); a `load_frames(run)` helper assembles the merged view for Stages 5–7.

**M13. §7.4 — component-level hysteresis is undefined (components have no identity across frames) and the `uint8` count overflows at 60 fps.**
W = 5 s is 300 frames at 60 fps (§1.1 lists 60 fps as typical) > 255.
Proposed change: per-pixel hysteresis `mask[p] = count[p] > ρ_on·W or (mask_prev[p] and count[p] > ρ_off·W)`; churn regions = components of `dilate(open(mask, 3×3), 9×9)` with area ≥ 400; `count` is `uint16`.

**M14. §8.1 / §9.0 / §9.2 — Vision's confidence carries no information, icon glyphs prefix UI lines, and confusable characters appear inside identifiers; several rules lean on `ocr_conf`.**
[measured] 151/151 Vision lines on frame_300/frame_600 report `confidence = 1.0`, including misreads (`Leamn more`, `Learn more B'`, `C:\Users \msadmin`). Icons become leading characters (`P Search resources…`, `Ô Delete`, `ORefresh`, `9 Access control (IAM)`). A GUID came back as `3ебb0e8a-…` (Cyrillic е, б) with `en-US` only and correction off.
Why it matters: min-conf on join and "low confidence" tagging are no-ops; every icon-prefixed line will be `agree=false`, depressing the §18.2 coverage metric and the Stage 7 quoting rule for reasons unrelated to text accuracy.
Proposed change: document `ocr_conf` as uninformative for Vision (keep the field; no rule may depend on it); in §9.2 set `agree=true` with `ocr_icon_prefix=true` when `norm(vlm)` equals `norm(ocr)` after removing one leading token of ≤ 2 non-alphanumeric or uppercase characters that `vlm` lacks (the stored `ocr` string is untouched); flag lines containing non-ASCII letters inside an otherwise ASCII token as `confusable=true` (flag only — no rewriting), and include a GUID/URL in the calibration set.

### Minor

**m1. §7.5 — caret tracking as described cannot work with §7.2 (the opening erases a 2-px caret) and its output is needed before it can be confirmed.**
Track on the raw thresholded map: components ≤ 3 px wide, 8–30 px tall; confirm after ≥ 2 toggles at the same bbox (±1 px) with 0.15–0.6 s between toggles (one blink period exceeds S, so confirmation lands after emission → write to the frame whose stable interval contains the toggles, via the buffered record of M1). §9.4 rule: the region whose bbox *expanded by one line height* contains the caret, else the nearest region within two line heights (a caret on an empty prompt line lies outside a text-extent bbox).

**m2. §11.4 — the transient precondition "every matched region's fused text is equal between i−1 and i+1" rejects the common cases (a Saved toast next to a title-bar dirty-marker change; a toast during output).**
Replace with: frame i has ≥ 1 region unmatched in both neighbours, that region's lines are absent from i+1, and `hold_s = t_change_{i+1} − t_change_i < T_transient`; compute the i−1→i+1 diff normally and attach it. State that transients are resolved before coalescing.

**m3. §13.1 — validate by repair, not by re-prompt; the sections fallback assumes Stage 0 exists; the windowed merge rule as written drops boundaries seen once.**
Ask for `[{start_id, label}]` only and derive ends in code (any output becomes contiguous and covering after sorting/deduping and forcing the first start); unknown IDs are dropped. Fallback when Stage 0 is absent: fixed windows of 8 steps. Windowing: keep every boundary found in a window's non-overlap zone; in an overlap zone keep boundaries found by both windows, else by the window in which it is ≥ 25 items from an edge. At a 1M context a 2-h video (~1,600 transitions × ~40 tokens) fits one call; set the window to 2,000 or drop windowing from v1.

**m4. §16 — "scale pixel counts by 4 for 1440p" is wrong.** 1440p has 1.78× the pixels of 1080p, and UI elements keep their pixel size at 100% display scaling; the thresholds are UI-element sizes and should not scale with resolution. Scale only for detection downsampling (with the 2x2-max rule of B1 the factor is ≈ 2.5, to be calibrated on the synthetic fixture).

**m5. §19.6 — the 1440p multiplier is ≈ 1.25×, not 1.8× (output tokens dominate and are resolution-independent); add the thinking line from M8; the sample video (14.2 min, likely 100–250 frames) is ≈ $8–18 on Opus 5.**

**m6. §9.4 — "Exact" overclaims for the retrospective signal and the combination is missing cases.** A click that focuses a window can share a transition with the first keystroke, so attribute to the run's from_frame only when that transition has no region `appeared` and no `focused_region` change; else 0.6. Add rows: computed present but VLM `null` → computed, 0.7; caret and retrospective disagree → retrospective, 0.6; nothing → `null`.

**m7. §14.2 — metadata filters must be applied before top-k in each index, or a filtered query fuses an empty list.** [measured] sqlite-vec 0.1.9 accepts metadata columns in the KNN `WHERE`; FTS5 filters via a join on `nodes`. State the RRF constant (60) and over-fetch (k=50) when filters are set.

**m8. §10.6 — `T<nnn>` overflows at 1,000 transitions (a 2-h video); any Stage 1 parameter change renumbers every frame and invalidates all downstream IDs, and content addressing does not help with that.** Use unpadded or 5-digit IDs and say explicitly that Stage 1 is the only stage whose re-run invalidates the whole run.

**m9. §7.1 / §20.2 — resolve the [verify] on hardware decode and the frame-count assumption.** [measured] `av.open(path, hwaccel=HWAccel(device_type="videotoolbox"))` works (PyAV 18.1.0; frames arrive as `nv12`; `to_ndarray(format="gray")` works) but runs at ≈ 241 fps versus ≈ 535 fps for software decode with `thread_type="AUTO"`, so keep software as the default. `stream.frames` is 0 on the sample; use `container.duration` (852.83 s) for `t_end` and progress.

**m10. §14.2 / R6 — `fastembed` downloads its model on first use, so a cold run on an offline machine fails.** Add a `vt setup` step that pre-fetches the embedder (and records its hash in the manifest), or vendor the model.

**m11. §9.2 — the 0.8 alignment predicate is too coarse for short lines.** [measured] `normalized_similarity("ls", "1s") = 0.5`, so a two-character command becomes OCR-only + VLM-only. Use `sim ≥ 0.8 or (len ≤ 8 and Levenshtein ≤ 1)`.

**m12. §1.3 R2 vs §6 / §10.1 — Stage 0's `start_s/end_s` are model-produced timestamps that are indexed and joined to frames.** Either state the exception in R2's row or snap each chapter boundary to the emitted frame whose stable interval contains it and store that frame's `t_change`.

### Nit

**n1. §7.2 / §16** — the 16-px minimum in `Σ(comp.area for comp.area ≥ 16)` is a parameter not listed in §16 (it becomes `θmin` under B1).
**n2. §10.2** — specify `index` (position in the *new* list), `y` (of the new line), and the `char_diff` encoding (e.g. unified `+`/`−` runs from the character-level Myers of §20.6).
**n3. §8.3** — say that `vlm_lines` (and `rows`) are empty on non-leaf regions and that `unassigned_line_ids` lines are transcribed nowhere.

## Checked and found correct

- PyAV timestamps: `time_base = 1/15360`, `start_time = 0`, pts step 512 → exact 1/30 s from t = 0 on the sample; `thread_type = "AUTO"`, `to_ndarray(format="gray")` (yuv420p → 1080x1920 uint8) work as in §20.2.
- Apple Vision through PyObjC exactly as in §20.4: revision 3, `supportedRevisions` = 1–3, `minimumTextHeight` default 0.0, `topCandidates_`, `boundingBox()`; the §8.1 bottom-left → top-left conversion yields correct pixel boxes. Throughput: 0.15–0.23 s per real 1080p frame (52–99 lines) at the accurate level, an order of magnitude inside §19.2's 2 s bound. Vision does split and merge rows inconsistently (e.g. `Node pools Access Networking` as one line; `Subscription` / `:sub-global` as two), as §5.4 warns.
- Codec-noise premise for θpix = 12: over 2,700 frames (600–690 s) 93% have max |Δluma| ≤ 12; every I-frame (every 6 s) without real change shows 23–51 pixels above θpix in components of ≤ 8 px, so a minimum-area filter alone removes it.
- §5.3 token arithmetic (69×39 = 2,691; 92×52 = 4,784 at the cap; 4K → 2576×1449) and §19.6 dollar arithmetic for Opus 5 and Sonnet 5 at the listed prices.
- Anthropic SDK 1.5.0: `client.messages.parse(..., output_format=PydanticModel, output_config={"effort", "format"})` and `response.parsed_output` exist as documented in the SDK reference; Batches: 100k requests / 256 MB per batch, results keyed by `custom_id`, retained 29 days; prompt-cache minimum on Opus 5 is 512 tokens, so a byte-stable system block of that size caches; `client.files` exists.
- Bundled SQLite 3.53.4 with FTS5 (`unicode61 tokenchars`, `trigram`, `bm25()`), `enable_load_extension`, and sqlite-vec 0.1.9 KNN all work in the uv-managed Python 3.14.6; `rapidfuzz.distance.Levenshtein.normalized_similarity` exists; `/System/Library/Fonts/Menlo.ttc` exists; library versions in §20.1 match the lockfile.
- Frame PNG sizes (119–453 KB) are far below the 10 MB per-image and 32 MB per-request limits.
- §7.3 flash-and-revert (menu open/close within S) and "still frames do not reset the timer" trace correctly; Myers over line lists treats scrolled-but-identical lines as `equal` (§11.2) — standard.
