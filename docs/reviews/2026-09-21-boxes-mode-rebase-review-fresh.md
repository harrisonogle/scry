# Review: "Re-base the pipeline on boxes mode" (fresh reviewer, no prior context)

Reviewed: `docs/proposals/2026-09-21-boxes-mode-rebase.md` (draft of 2026-09-21), against the design (§7, §8–§12, §14–§16,
§18, §22), ledger L28–L42, `docs/open-items.md` and `src/scry/`. No model calls were made. Every number marked
**[measured]** comes from read-only scripts over existing run data (OCR boxes and PNGs of `runs/smoke-rapid`,
`runs/smoke-boxes`, `runs/span2-before`, `runs/aks`, `runs/smoke-c67-*`), which prototype the proposal's Stage 4 as
written: `[stage1.detect]` θpix 12, θmin 8, components grown by 0.5 × the median box height, areas merged through shared
boxes, kinds from the joined strings. Scripts and outputs are in the session scratchpad under `rebase-review-fresh/`
(`proto.py`, `boxlevel.py`, `scroll.py`, `veto.py`, `transient.py`, `cevents.py`); they are about 100 lines each and can
be re-run with `uv run python`.

**Verdict: accept with changes.** The principle is right and the data supports it. The Stage 4 text and the evaluation
plan are not yet fit to build and spend against; both are fixable inside the proposal's own frame. The required changes
are listed at the end.

## What holds up

- **The veto is sound on this data [measured].** Over the 35 near-static pairs of the two spans (≤ 5 % changed), 4,199
  boxes touch no changed component. 176 of them (4.2 %) read differently in the next frame. 154 of those have not one pixel
  above θpix under them; the other 22 have at most 36 such pixels, max |Δluma| 39. I read all 22: every one is OCR
  re-reading the same pixels (`'A different object named AKS1-KodeKloudApp already exists in your kubeconfig file.'` →
  `'At - .'` at max |Δluma| 14). No real text change was vetoed.
- **Box stability reproduces [measured]:** 741 of 766 (96.7 %) on the smoke pairs, 3,282 of 3,433 (95.6 %) on span 2,
  against the proposal's 96.5 %.
- **Transients by pixels work on the one known case [measured]:** the area of 150→151 has no component in 150→152
  (hold 0.6 s). No false transient on span 2 when the rule is read per area.
- Removing correspondence, row geometry and the nothing-else-changed clause removes the three mechanisms behind most of
  L28–L41. The cost figures check out ($1.29 / 11 = $0.117).

## Blocking

### B1. Stage 4 classifies on an area's joined string and aligns per area; both misfire on existing data

§4 and §5 step 4 define `kind`, `char_diff` and chaining on "the joined strings" of an area, and say Myers within an area
makes "moved identical texts align as equal". Measured on the 42 consecutive pairs of the two spans and the 221 frames
of `runs/aks`:

- **False `appended`.** 148→149, the Cloud Shell tooltip: `['G'] → ['G', 'oud Shell']`. 157→158:
  `['Encryption at-re'] → ['Encryption at-re', 'PS C:\Users\msadmin>']`, a clipped browser box and a PowerShell prompt
  from two windows in one area, because the 10-px margin reaches across the window edge. Program output after Enter is
  `appended` whenever the area also touches the prompt box (163→164, 168→169, 185→186), so §9's "output bursts no longer
  coalesce" contradicts §4: by the letter they chain with the typing into one `text_appended`.
- **Missed `appended`.** Six transitions put a command on an empty prompt (154→155, 156→157, 160→161, 164→165,
  171→172, 177→178). The exact prefix test labels four. 156→157 fails because a taskbar tooltip box shares the area and
  OCR drops `PS `; 171→172 because OCR reads `PS C:` before and `PSC:` after. A growing line is always under changed
  pixels, which is exactly where the 96 % stability does not apply; this is the L29/L31/L35 failure again, and the
  proposal deletes `typed_tolerance` (`coalesce.py:34`) without a replacement. For scale: the current pipeline fires one
  `typed` and one `output_appended` (its text is a tooltip title) in the 30 transitions of `runs/span2-before`, so this is "not the fix
  claimed", not a regression.
- **Scrolls split across areas.** On `runs/aks` 21 transitions move at least four uniquely identifiable texts, 213 texts
  in all. 72 (34 %) have their before-box and after-box in different areas, so no per-area alignment can pair them. On the
  four page scrolls of 170–280 px (75→76, 91→92, 107→108, 125→126) it is 55 of 64 (86 %); terminal scrolls of one to six
  lines all stay in one area. A page navigation is 35 areas (181→182) and a progressive load 67 (182→183), not the single
  large area §4 assumes. Today's unit-wide Myers does align these (design §11.2, "scrolling is handled for free"), so
  this is a regression against the current design, not a watch-list item.

**Change:** make the box the unit of the change record, as §2 already says it is. Among the boxes that touch changed
pixels: (1) drop pairs with equal text and intersecting rectangles; (2) cancel equal texts across the whole transition
as a multiset and record them as moved, which is the proposal's own `visual_only` idea lifted from area to transition;
(3) group what is left by rectangle intersection between before and after boxes and classify each small group, comparing
with whitespace removed; (4) the rest is `appeared` or `removed`. Areas stay as the location for rendering and for
Stage 5 crops. A 40-line prototype of this [measured] labels five of the six typed commands `appended` (156→157 stays
an honest `changed`), turns the Cloud Shell tooltip into `appeared` then `removed`, labels output `appeared`, and on the 186→187 scroll
cancels 26 moved texts leaving 11 records. It also deletes two geometric rules: reading order within an area, and
modify pairing by vertical overlap. Chaining then has an exact definition: an after-box of T*i* that is a before-box of
T*i+1* (same frame, same id).

### B2. The evaluation plan cannot choose between its alternatives

- **No decision rule and no acceptance test.** §7 lists nine metrics and no statement of which one picks the arm, or of
  what "the re-base is validated" (§10 Q2) means against `runs/span2-before`.
- **`link_consistency` is already at its ceiling [measured].** On `runs/smoke-boxes` (L41's single run) every association
  whose boxes all recur (same rectangle and text) is proposed identically in the next frame: 194 of 194 over 8 pairs; top-level container
  assignment agrees for 900 of 903 boxes. Arms A–D at full scale will all score about 1.0. The metric can show a collapse
  at reduced scale (E5); it cannot rank E2, and a link that is wrong in every frame scores 1.0.
- **Name consistency is dominated by run-to-run noise [measured].** Share of boxes keeping their top-level (kind, app) on
  the five static pairs 148–153, in the three identical cold runs `smoke-c67-off-{1,2,3}` (row mode, group-only, scale 0.67): 0.79, 0.39, 1.00. The model
  alternates "Browser" and "Microsoft Edge". A range of 0.6 on a 0–1 metric between identical runs.
- **Three repeats resolve only about 3 SD.** Recomputing L42 from the run directories: rows identical to full resolution
  0.70, 0.71, 0.62 without coordinates and 0.83, 0.68, 0.73 with (means 0.676 and 0.745, SD 0.046 and 0.075), t = 1.4 at
  4 degrees of freedom, p ≈ 0.25. The one effect the ledger has treated as real is not separable at n = 3. Differences
  "of a few percent" between arms will not be either.
- `box_stability` is a property of OCR and identical in every arm.
- **Nothing measures the first priority, and E3 cannot be decided without it [measured].**
  `kubectl rollout undo deployment/kodekloudapp` is on screen in frames 172–174 only. OCR reads `kubect1rollout`,
  `kubectl_rollout`, `kubectlrollout`, never correctly; the model reads it correctly in all three. In the other
  direction the model wrote `get-credentials` and `get_credentials` where OCR reads `get-Credentials` in 17 frames; which
  is right needs a human. "Is a second reading wanted" is a question about command error rate.

**Change:** make the span 2 command list a precondition of E1, not question 5. It is about a dozen lines and turns the
primary metric into one that needs no model call to score: for each hand-typed command, (a) a lexical `search` for the
exact string returns a node covering its time, (b) some reading of some box equals it exactly, (c) the time error of its
first appearance. Add two negatives, for example the `az aks scale … --node-count 2` line shown for 1.4 s at frame 165, apparently a
shell suggestion, and never run. Add the links of one frame by hand (frame 150, about 31) and the windows and popups of the 11 smoke
frames (about 25 entries) for precision and recall. State the rule before spending: the arm wins on the primary metric,
ties go to cost, and the consistency metrics are guards that must not fall below the E1 floor. Analyse paired by frame
(the same 11 or 33 frames in every arm) instead of per-run aggregates, and spend the extra repeats on the two finalists
only.

## Should fix

**S1. Build Stage 4 first, at no cost.** By principle 1 Stage 4 needs only `ocr.jsonl` and the PNGs. It can be built and
judged on the whole sample (`runs/aks` has 221 frames; Rapid OCR is CPU time) before any schema change or model spend;
the prototypes here cover 42 pairs in a minute or two of CPU. As ordered, step 1 replaces `FrameRecord` and `Transition`,
which `run.py`, `interpret.py`, `hierarchy.py`, `index.py` and `agent.py` load, so the pipeline is broken from step 1 to
step 6 and the old mode is in effect deleted at step 1, not step 9. Add the new records beside the old ones and switch
the loaders at step 9. Deleting the row machinery then is fine given the tag, provided B2's acceptance test exists;
without it, it is premature.

**S2. Stage 6 and the agent are not untouched.** `hierarchy.py:97–99` (`_state_line`) uses `f.units()` and
`focused_region`; `interpret.py:109–120` (`render_transition_line`, Stage 6's item line) reads `typed` and
`output_appended` events, `computed_diff` and `regions.appeared`. `prompts/agent.py:5` and design §15.4 say "quote exact
text only from lines marked agree=true"; in group-only mode `agree` never exists, so every quote becomes "unverified".
`agent.py:19` describes payloads by `agree` and levels by `region`; `index.py:28, 74, 185–188` carry `layout_conf` as a
column and a hit field. §6 and §8 should list these, with a Stage 6 step. One addition would give the agent something to
hedge on without a second reading: flag a box whose text differs from its pixel-identical predecessor as `unstable`; the
rate is 3.3 % on the smoke and 4.4 % on span 2 [measured], and it is a measured fact, not an inference.

**S3. `container_events` asserts identity from labels and is wrong more often than right [measured].** With the existing
run's window-level units as labels, "most boxes after-only" fires five times on span 2 and three are false: 155→156 and
157→158 (the PowerShell window was already there and filled with output, 12 of 16 boxes new) and 181→182 (the browser
navigated, 37 of 68). A terminal printing output is the commonest event in this corpus. Cut the events, or record the
two numbers (`pixel_support`, new-box share) and assert nothing. Note `pixel_support` over a hull rectangle is misleading
for a background window, whose hull encloses the foreground window (design §9.3).

**S4. Cases §5 Stage 4 does not define.**
1. "No changed pixel" must mean "no component of at least θmin within the margin". Residual pixels above θpix outside
   any component exist in nearly every pair (median 2 on the smoke and 11 on span 2, up to 134) and 147 untouched boxes
   have 1–36 of them underneath [measured]. The known-good tooltip leaves 13 residual pixels in its rectangle, so
   "shows no change" in the transient rule needs the same reading.
2. Which median box height sets the margin (frame a, frame b, both, per area), and what happens with no boxes (today a
   fixed 8 px, `diff.py:90`).
3. The joiner of "joined strings" and whether whitespace counts. 161→162 (`azconfigure --defaultsgroup=…` →
   `az configure --defaults group=…`) and 175→176 differ only in whitespace; with 172→173→174 that is 4 of the 29
   near-static span 2 pairs whose text change is only a re-read under a moving cursor or recoloured ghost text [measured].
4. An area that touches no box (158→159 and 159→160 consist only of such areas): which kind?
5. The reading-order rule is not transitive; give the clustering procedure (today: band against the row's first line,
   `schemas.py:249–254`).
6. Modify pairing by vertical overlap alone pairs a deleted key with an inserted value on the same visual row, now that
   the unit is a box and not a row. It needs rectangle intersection. B1's change removes items 5 and 6.
7. Transients: whether one reverting area is enough while others progress; the definition of `hold`; what `transient`
   carries now that there is no region name.
8. Whether a chained or transient-merged transition recomputes `changes` between its end frames (today `_build` does,
   `coalesce.py:71–74`).
9. No pixel evidence (`PixelSource.change` returns `None`, `diff.py:63, 74`): is the frame one area, or is there no record?
10. `uncertain` in the example is never defined; the transition kinds that replace `coalesced`; what `in_churn` does now.
11. The Stage 2c output schema is absent; only the prompt and the merged record are given. `texts` "for every box id"
    cannot be a map under structured outputs (no free keys), and a list of `{id, text}` costs more tokens than L41's
    parallel arrays. Also: is a link across two containers dropped, and where does a lone `:` box go?

**S5. Links.** `run`, `pair`, `record` is about the right size for the stated use, but:
- `run.joiner` puts a model judgement on the findability path, and the draft rule is wrong for the one wrapped command
  in the data. Frame 165 wraps `…--resource-group RG1-KodeKloud-AKS` / `--name AKS1-KodeKloudApp --node-count 2` at a
  space; "`""` for a hard wrap, as in a terminal" yields `RG1-KodeKloud-AKS--name`, a single FTS5 token under
  `tokenchars '-_./:\'` (`index.py:76`). Index both joins and keep `joiner` as a label, in the spirit of indexing both
  readings.
- A two-column property grid is both a `pair` and a `record` (L41's 21 Properties rows). The model will flip, and
  per-kind consistency will punish it for a distinction nothing uses. Add one tie-break sentence.
- `record` without its header answers no question a box does not ("STATUS of node X" needs the header cell). Add an
  optional `header` member list or drop `record` until a question needs it.
- A key and value inside one OCR box (`SubscriptionID :3e6b…`) can never be a `pair`; say so, so nobody builds
  `get_pairs` expecting completeness.
- The prompt lists "title bar" and "toolbar" as panes, which invites the 8-against-3 splitting of L31. Harmless
  mechanically now, but it fragments container nodes; the frame node is what saves multi-term queries.

**S6. θpix and θmin now carry identity for the whole pipeline and were calibrated on this one video** (design §7.2: "93 %
have max |Δluma| ≤ 12"; §22 #3 is still open). That sits badly with principle 5. The failure is graceful: a noisier
encode means fewer vetoes and OCR jitter reported as change, and the index is unaffected. The proposal should say this
and report one number per video, the share of boxes touched on near-static pairs, as the alarm. The other constants that
remain are 0.5 (margin), 0.5 (same line), 0.5 (modify pairing), "most" (container events), `transient_max_s`, IoU 0.8 and
the half-box-height snap. §3 says the evaluation sets their values, and no phase of §7 varies any of them.

**S7. The index returns one command twenty times [measured].** On `runs/span2-before/index.sqlite`, `"az account show"`
returns 20 hits, 11 region nodes and 9 frame nodes from frames 157–169, and no transition or step; the command is on
screen for 27 frames. The proposal adds one more per-frame node carrying the same text. Measured identity offers the
remedy: chain a box across frames while it sits on unchanged pixels with the same text (the 96 % case) and index the
text once with its first and last frame. "When did they run X" wants first appearance, and this is the cross-frame
identity the proposal otherwise never defines.

## Nits

- N1. The 96.5 % evidence lives in a session scratchpad under `/private/tmp`. Put it in a ledger row; it reproduces.
- N2. The veto tests component bounding boxes (`diff.py:116`), not pixels, so a hollow component (window border, focus
  ring) touches everything inside it. Small here: 5 boxes in 42 pairs were touched with no changed pixel beneath
  [measured]. State which test is meant.
- N3. `missed` exists only when transcribing, so group-only mode has no path for text OCR misses. Count it under E3.
- N4. E5 picks the scale in group-only mode; if E3 keeps transcription the result does not transfer. Say the scale stays
  1.0 in that case.
- N5. Every number behind the proposal, and this review, comes from one 14-minute video, mostly 11 frames of it. Hold
  out ten frames of a different recording (an editor, a dark terminal) for the final check of the prompt and θ.
- N6. Ghost text: the never-run `az aks scale …` line of frame 165 is indexed and `appended` like a real command. That is
  honest under principle 3; test the agent on it (B2's negatives).
- N7. Whether a `missed` id (`m<n>`) may be cited is not stated.

## The eight questions in brief

1. **Principle.** Sound, and the veto measurement supports it. It breaks where identity is needed under changed pixels:
   a growing line re-read by OCR (B1), a scroll whose lines land in different areas (B1), and containers asserted as
   events (S3). Window moves, overlaps and textless changes degrade to honest but noisy records. Compression noise is fine
   on this sample and unknown elsewhere (S6).
2. **Stage 4.** Not yet implementable without guessing: B1 and the eleven items of S4. "No changed pixel means unchanged"
   held for 4,199 of 4,199 boxes, read as "no component of at least θmin within the margin".
3. **Links and prompt.** Keep `run` and `pair`; index both joins; give `record` a header or drop it; add the pair/record
   tie-break (S5). The model will get the joiner wrong at a wrap that falls on a space, and will flip pair and record.
4. **Data model.** Lost or dangling: `agree` as the agent's quoting rule in group-only mode, `layout_conf`, Stage 6's
   item and state lines, the level name `region` (S2); first appearance was never there and should be (S7).
5. **Hidden constants.** θpix and θmin above all, then the list in S6.
6. **Evaluation.** Cannot separate the arms: metrics are at ceiling or swamped by noise, none measures correctness, and
   n = 3 resolves about 3 SD (B2). The cheapest ground truth is the command list with two negatives.
7. **Build order.** Stage 4 first and free; side by side until step 9; add Stage 6 and the agent (S1, S2). Deletion at
   step 9 is fine with the tag and an acceptance test.
8. **Unmentioned.** Index duplicates and first appearance (S7), OCR self-disagreement as a free uncertainty flag (S2), a
   second video (N5), ghost commands (N6).

## Verdict: accept with changes

1. Re-specify Stage 4's change records at box level with a transition-wide moved-text cancel and a whitespace-blind
   comparison, and define chaining on shared boxes (B1). Close the S4 list in the same edit.
2. Get the span 2 command list, with two negatives, before E1; write the decision rule and the acceptance test against
   `runs/span2-before`; analyse paired by frame (B2).
3. Reorder the build: Stage 4 first on the full sample at no cost, new records beside the old until step 9, and add
   Stage 6, the agent prompt, §15.4 and the index columns to §6 and §8 (S1, S2).
4. Cut `container_events`, or reduce them to two recorded numbers (S3).
5. Index both joins of a `run`; add the pair/record tie-break; decide `record` with or without a header (S5).
6. State the θ dependence and report the per-video alarm number (S6).
7. Recommended, not required: index a text once with its first and last frame, using unchanged-pixel box chains (S7).
