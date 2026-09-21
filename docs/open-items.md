# Open items

Things that are known to be undone, unverified, or worth revisiting. Decisions and their rationale live in
`docs/decision-ledger.md`. This list was brought up to date on 2026-09-21 (evening), after the re-base on boxes mode
(ledger L44 to L65). The first two parts are what is open now. The parts after them are the list as it stood before the
re-base: each item there is ticked (done, with its ledger row), struck (the re-base made it meaningless, with the
reason; a struck item has no box) or moved up, so every empty box in this file is an open item. The design document
(`docs/visual-transcript-pipeline-design.md`, with its §21 roadmap and §22 questions) describes the pipeline before the
re-base; the re-base specification is `docs/proposals/2026-09-21-boxes-mode-rebase.md`, and its section "Where the code
stands" says what is built.

## Open now: needs the owner

- [ ] **Correct the three draft question sets, and look at the second section of the command list**
      (`docs/ground-truth/`). `span2-questions.md` (15 questions written from the command list of frames 155 to 187;
      L50, L57), `smoke-questions.md` (18 graphical questions on frames 145 to 155; L57, L59) and `full-questions.md`
      (27 questions on the whole video; L59, L62) each say "DRAFT, nothing here is accepted yet". Every judged answer so
      far was scored against them as they stand. The two later sets end with a section "Frame content the agent was
      unsure about". All three are saturated: every base scores at or near the ceiling (L57, L59, L62), and none asks
      for what the owner wants annotation for as an experience: search by key, the application filter, a second opinion
      on a doubtful text (L65). In `span2-commands.md` the executed list was accepted by the owner on 2026-09-21; the
      second section ("Appeared on screen but was never run", the key of the *false run* metric) is kept at the owner's
      request and the file records no acceptance of it.
- [ ] **The question sets are blind to the honest text-change contract** (L66, L67). Every answer below was judged
  correct: "retyped `kubectl get pods`" where only `kubectl ` was typed and the rest was the shell's grey suggestion
  (all four Sonnet answers in P8); "corroborated by later scrollback" as evidence that commands ran (two Sonnet
  answers in P9); two differing readings called "confirmed independently by the OCR-derived text" (P9). Until the
  rubrics have lines for typed against suggested (Q16, Q18), for what counts as evidence that a command ran (Q17,
  Q21) and for saying so when readers differ (Q19, Q20), a comparison of models or agents on these sets measures
  recall of strings and times and little else. The sets are the owner's to correct, so nothing was added.
- [ ] **Which model answers questions** (L66, L67). On Opus-built indexes a Sonnet 5 agent ties on score at a quarter
  of the price ($0.053 to $0.062 a question against $0.216 to $0.263) and in under half the time. It opens a frame in
  3 to 6 of 27 answers where Opus opens 14 to 23, and says that readers differ for 3 of 18 such texts where Opus says
  so for 40 of 46. The default stays Opus 5; `[ask] model = "claude-sonnet-5"` is there for whoever wants the other
  trade. `annotate`, `interpret` and `summarize` stay on Opus 5: on Sonnet the index itself records suggestions as
  entered text (P7, P8).
- [ ] **`summarize` can paraphrase the contract away** (L67). One Opus step summary says "type the command `kubectl
  create deployment …`" where the transition it cites calls most of that line a suggestion. One step in one run; it
  is the first sign of the contract leaking on Opus, and both agents then said "typed" on that question. Nothing was
  changed: the fix is prompt wording for `summarize`, and the owner should see the case first
  (`docs/results/p9/analysis.md`, last section).
- [ ] **The owner's hold-out second video.** Not yet supplied. About $70 of the Anthropic budget is kept for it and
      no further paid phase is started without a result that calls for one (L64, L65). It is the first outside test of
      θpix and θmin, with `touched_share` on near-static pairs as the alarm (proposal §11), the place to find out
      whether descriptions keep earning their place (L65), and, if it has narration, the first test of the outline
      stage on audio (L58).
- [ ] **Confirm or change the working default for `annotate`** (L57, L59, L62, L65). It is `mode = "incremental"`,
      `transcribe = true`, `scale = 1.0`, referencing arm A, on Opus 5 (L59, L60, L63, L64), chosen without the owner.
      What the phases say about this sample: no annotation ties on the command metrics and on the answers of P1 and P4
      at about a quarter of the cost ($4.62 against $17.85 a video, L62); in P2 the one separation was the second
      reading of a line being edited (L59); in P6, with the agent's pixels withheld, annotated indexes scored 27 of 27
      and unannotated ones 26 and a partial, and what carried the difference was the description (L65). No answer in
      any phase turned on a container, a link or a second reading; `annotate` is about three quarters of the pipeline's
      cost ($13 of $17.85, L65). A description-only mode (the clean frame alone, only the description asked for,
      roughly a third of the cost of full annotation) is unbuilt; L65 puts it to the owner as the first question on
      return. Transcribing, group-only and none stay co-equal until the owner decides.
- [ ] **Referencing arms B and C (position-based assignment) were never built, although the owner said "I do want it
      evaluated"** (L61). Deferred because nothing measured since the tag fix (L53) points at id assignment as a live
      problem (`mark_match` 93 to 94 % at scale 1.0). Under B and C every box is a target, so they cannot use
      incremental annotation: evaluating them means every-frame annotation at about three times the cost, plus new
      code for centre-inside, front-most and snapping (L61). Flagged with it: arm D, which the owner called promising,
      was built, lost in P5 (equal cost at 1.0, dearer below it, a silent whole-frame scramble in 5 of 264 calls) and
      was removed behind the tag `arm-d-evaluated` (L63).
- [ ] **Whether to skip `annotate` calls that have no target.** 47 of the 221 incremental calls on the sample have
      none; they cost about $2.30 a video, 19 % of `annotate`. They are kept because they refresh the per-frame
      description, which the owner wants kept; skipping them would leave those frames with the previous description
      (L62).
- [ ] **Look at the branch; then merge and push.** Nothing has been pushed. `main` is untouched at the tag
      `pre-rebase-boxes`; everything is on `rebase-boxes` (L44). Merged branches and both tags are kept, with no
      squashing and no forced updates (L46): `rebase-boxes-eval`, `-incremental`, `-incfix`, `-outline`, `-armd`,
      `-batchfix`, `-askindex`, and `-docs` (this revision of the documents); tags `pre-rebase-boxes` and
      `arm-d-evaluated`. Step 9 of the proposal's build order (rewrite the design document as revision 7, merge to
      `main`) has not been done.

## Open now: recorded and left alone

Each of these was seen in a real run and deliberately given no machinery; none has cost an answer so far.

- [ ] **Search is lexical only, and it floods.** `[index] embedder = "none"` is the default; the optional `fastembed`
      embedder (`uv sync --extra embed`) has not been run in any phase (L9). One paraphrase (Q1 of the whole-video
      set) never reaches its frame within 20 hits on any index; the agents recovered by other words. Where one line
      changes over many frames (a command being entered), 17 of 20 hits are that line: collapsing is broken by OCR
      jitter. Description text can pollute: a search for "Region" returns slides whose description says "region".
      No change was made: an embedder, or collapsing that survives OCR jitter, would be machinery without a failed
      answer behind it (L62). "Cannot find it" is the failure the owner ranks worst, so this is the first place to
      look if the hold-out video fails an answer.
- [ ] **No guard against junk in a description.** One `annotate` answer in about 1,500 calls carries 4.7k characters
      of unrelated text inside `description`; it passed the schema, is indexed, and came back in search results in
      P6. A length or language check would be a constant or a heuristic (L62, `docs/results/p6/analysis.md`).
- [ ] **A phrase split across two OCR boxes is not findable as a phrase.** A quoted phrase that spans two boxes
      matches only when the boxes are adjacent in reading order in the frame entry or are joined by a link; the loss
      is widest with no annotation (L48, "Known losses"). In P0 three never-run suggestion lines matched no lifetime
      for this reason or because of a misread at the cursor (L47).
- [ ] **Application names are inconsistent, so the `--app` filter splits one window.** The same browser is named
      three to seven ways in one run (L53, L54, L56, L59). Labels carry no identity across frames, by design; the
      filter of `scry search --app` and of the agent's search tool matches on the name.
- [ ] **The sample video has no audio stream, so the outline stage's audio path is untested** (L58). The stage works
      live on the picture alone, at about a dime per video. Also left alone there: `chapter_of` does not snap chapter
      times to emitted frames, and the manifest's outline entry sits outside `stages`, so the cost roll-up skips it.
- [ ] **Haiku 4.5 cannot be tried without a provider change**: it refuses the `effort` parameter that every call
      sends (L64). Sonnet 5 was tried on `annotate` (P7: about half the price, clearly worse labels; `annotate` stays
      on Opus 5, L64). P8, every stage on Sonnet 5, was in flight when this list was written (L64).
- [ ] **A request that fails twice in a batch leaves a permanent error entry in the call cache.** Since the batch
      fix (L62; merge `bed0d80`, commit `b55d33e`) a failed batch result is resubmitted once, and a second failure is
      written to the cache as `batch: failed twice, …` so that the synchronous pass does not silently re-issue the
      call at the sync price. That error is not one the stages treat as transient (only `api:` and `max_tokens` are),
      so later runs read it from the cache and never retry; the entry's file under the run's `cache/` has to be
      deleted by hand. Not exercised live.
- [ ] **A `[copy]` run carries 959 MB it never reads**: frames, overlays and the call cache of the run it copies,
      for a phase that only asks questions (L65). Recorded with it: `scry eval judge` prints harmless "Event loop is
      closed" tracebacks at shutdown and exits 0 (L57, L65).

## Before the first real run

- [x] **Credentials.** Done 2026-09-13: `.env` holds `ANTHROPIC_API_KEY` and `uv run scry setup` reports it. On a new
      machine: `cp .env.example .env && chmod 600 .env`, fill in the key (or `ant auth login`), confirm with `uv run scry setup`.
- [x] **Live smoke of the model stages** on 11 frames (ledger L28–L29): contract verified, overlay labels fixed,
      measured cost ≈ $0.076 per frame for Stage 2c and ≈ $0.042 per transition for Stage 5.
- [x] **First full run on the sample** (`uv run scry run assets/create-aks-cluster-tutorial.mp4 --out runs/aks`;
      projected ≈ $27 sync or ≈ $14 with `[model] mode = "batch"`, ~25 min wall; the 11 smoke frames are cache hits).
      The two tuning items below are decided (ledger L36–L37); merge is free to re-run if either is revisited.
      Read `manifest.json` → `diagnostics` afterwards: `agree_fraction`, `rows_rejected`, `invalid_refs`, refusals, cost.
      Done after the re-base, through the evaluation harness: P4 and P4b ran the whole 221-frame sample five times
      cold (L62). The projection and the `diagnostics` keys above belong to the pipeline before the re-base.
- Moved up, to "Search is lexical only": **Revisit the embedder default.**

## Findings from the smoke run (ledger L28–L29)

- [x] **`[merge] row_gap_lines = 3` rejects the rows the prompt asks for.** 135 of the 165 rejected rows on the
      smoke are label/value pairs and table rows whose column gap is 7–25 line heights; the y-spread test already
      catches marks from different lines. Re-merging the cached data in memory: 10 → 75 rejected, `agree_fraction`
      0.495; 30 → 58, 0.518; off → 30, 0.553. Off since 2026-09-21 (`row_gap_lines = 0`, ledger L37): the owner calls
      the cap a finicky heuristic, the diff runs per unit since L31, and rows-as-boxes (below) may retire rows entirely.
      The re-base retired rows and `[merge]` entirely (proposal §8).
- ~~**The typed-command rule missed the `az login` keystroke (T9 on the smoke).** OCR read `Users \msadmin` with a
      space on frame 154 and `Users\msadmin` on 155; the fused text is the OCR reading whenever the readers disagree,
      so the longest-common-prefix test failed (§22 #15, second occurrence; L24 said to prefer the VLM reading if it
      recurred). Options: a whitespace-insensitive prefix test in `_typed_op`, or prefer the VLM reading in `Line.fused`
      when the two are near-identical, or both. Separate question for §22: both readers transcribe the shell's grey
      inline autocomplete (`login`) as if typed.~~
      Struck: the re-base removed the typed rule, `_typed_op` and the fused text. The mechanical layer records that
      text changed and never says it was typed; `interpret` offers `entered_text` and `submitted` as a model's reading
      (proposal §4, principles 3 and 4). With annotation, `entered_text` on this very transition is `a`, since
      `interpret` is given the screen descriptions (L54, L55); without annotation it is often `az` or `az login`
      (L59).
- [x] **Harmless `RuntimeError: Event loop is closed` tracebacks** at the end of every async stage: the
      `AsyncAnthropic` client is never closed inside the loop. Close it at the end of `_run_with_batches`.
      Done for the stages: `run_with_batches` closes the client inside the loop, also when the stage raised (L49).
      `scry eval judge` still prints them (see "Open now").
- [x] **Usage accounting.** `run_perceive` sums only three usage keys, dropping `cache_creation_input_tokens` from the
      manifest; `estimate_cost` ignores cache-creation tokens (billed at 1.25× input). ≈ $0.05 on the smoke.
      Done: all four usage keys are summed, over retries too, and cache-creation tokens are priced at 1.25 × input
      (`src/scry/costs.py`, L49). `run_perceive` went with the row machinery.
- [x] **Batch mode** (`[model] mode = "batch"`) is still unexercised live.
      Done: P4b ran the whole sample in batch mode (L62). It works, gives equivalent output in about half the wall
      time, and paid 0.68 of the sync price, not half. Three defects found with it were fixed (L62).
- [x] **Coordinates at reduced scale** (L42): the list restores grouping at 0.67 scale but costs as much as the pixels it replaces; Stage 2c stays at full resolution. Three repeats per condition put run-to-run noise at a few percent of rows and one small popup.
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

The last three findings are what the re-base was built on: identity moved from model-proposed structure onto OCR boxes
and pixels (proposal §1), and the stages and config keys they name no longer exist.

## Proposed after the smoke runs (owner's call)

- [x] **Index both readings.** Findability is the top UX priority and today only the fused text is searchable, which is
      OCR's reading on any disagreement (`inttooliction o azure kunerneras sorwice` for a line the model read cleanly).
      Adding the model's reading to the region node text in Stage 7 is small and needs no model calls.
      Done in the re-base: a lifetime entry holds every reading of each reader, and a frame entry adds the model's
      reading wherever the two differ (proposal §6 and §7, `src/scry/nodes.py`).
- ~~**Typed rule: compare either reading** (§22 #15, third option). Preferred over a whitespace-blind prefix test,
      which would loosen what counts as typing; making the model's reading the fused text (L24's suggestion) is held
      for ground truth because near-identical readings are where a model "completion" hides.~~
      Struck: there is no typed rule after the re-base (see above). Both readings are recorded and neither is picked
      (proposal §7).
- [x] **Default OCR engine: `rapid`** (owner, 2026-09-21; ledger L36). Measured (L35): mark match 0.726 → 0.920, disagreeing
      lines 19.5 % → 4.7 %, the typed event fires, at +1.1 s OCR per frame and +29 % Stage 2c output tokens. The row gap
      test went off rather than wider (L37). Vision stays selectable on macOS.
      Since the re-base `rapid` is the only engine: the Apple Vision adapter was removed on the branch (proposal §8).
- [x] **Windows and popups only in the Stage 2c schema.** Measured (L41): harmful, rows built across columns; rejected.
- [x] **Rows as OCR boxes plus model associations.** Measured (L41): agreement 0.752 → 0.768 at +20 % cost, associations
      correct and searchable; kept as a switch, not the default.
      The re-base made it the only mode: boxes carry identity and the model's associations are links (proposal §3).
- ~~**`_other_ops_ok` vetoes a typed event when any other unit has a surviving op** (blocked T9 in the rows-as-boxes run
      on one flicker op in the browser). With the pixel gate on, consider limiting the check to the typing unit.~~
      Struck: the function went with the row machinery (proposal §8).
- [x] **Empty transcriptions.** In rows-as-boxes mode the model transcribes icon-only marks as "" (the prompt's icon rule),
      which merge treats as no reading (OCR-only). Whether "" should count as agreement that a mark is not text is a policy call.
      Settled in the re-base: `""` sets `non_text`; the box leaves the agreement count and stays indexed from OCR, the
      flag being payload only (L48). Real words that the model read as `""` were seen and left alone (L53).
- [x] **Stage 5 image scale.** Measured (L39): half scale keeps the descriptions at 47 % of the cost; now the default.
- [x] **Masking the text for Stage 2c** (owner's three variants plus re-rendered text at half scale): not adopted (L40).
      The mask modes were removed on the branch (L49).
- [x] **Vision misses the grey label column** on portal pages; addressed by the engine change (L34).

## Needs the owner (hand-made ground truth, design §18.1)

- ~~Two fully annotated videos, the 20-frame calibration set, the question set. Everything in §18.2 is unmeasurable
      until then; integration tests are deliberately absent.~~
      Struck: the owner ruled that label quality is judged by eye on samples and accepted a command list of frames
      155 to 187 as the ground truth of the paid phases (proposal §9 and §12). What is still wanted from the owner is
      in "Open now": the draft question sets and the hold-out video.
- ~~With ground truth: the OCR bake-off (Apple Vision vs RapidOCR), the model/effort bake-off, and tuning the §16
      parameters (`still_s` in particular decides how finely typing is split into states).~~
      Struck: the Apple Vision adapter is removed (proposal §8); the model tier was measured on `annotate` in P7 and
      is being measured on the other stages in P8 (L64); θpix and θmin wait for the hold-out video (see "Open now").
      `still_s` has not been varied in any phase.

## Known limitations observed on the sample (details in the design)

- ~~The terminal cursor in the sample does not blink, so terminal frames carry no caret signal; focus there rests on the
  retrospective and VLM signals (§7.5, §9.4).~~ Struck: focus is not a deliverable after the re-base (proposal §0).
- ~~Apple Vision misreads seen on fixtures: a dropped hyphen in `--resource-group`, `C:\` read as `Ci\` (§5.4, §22
  #14–15). When OCR and VLM disagree the fused text is the OCR reading, which broke the typed-command rule once (§22 #15).~~
  Struck: the Vision adapter, the fused text and the typed rule are gone (proposal §8).
- Some overlay tags cannot avoid every text box on dense portal screens (`label_clashes` in the manifest). Since L53 a
  tag also avoids the tags already placed, and one that still overlaps another counts as a clash. At a reduced image
  scale the fallback can put a tag outside its window; left unrepaired because the scale stays 1.0 (L60, L63).
- A stage re-runs only when its inputs or configuration change, not when its code changes; delete the stage's entry
  from `runs/<id>/manifest.json` after editing a stage. A change to a model stage's prompt bumps its prompt version,
  which is part of that check and of the call-cache key.

## Unverified claims marked in the design

- Search the design for `[verify]`: Batches `custom_id` limits and Files API references inside batch requests (§20.7;
  batch mode has since run live with this code's `custom_id`s and inline images, L62), the Windows OCR port (§20.8;
  RapidOCR, the only engine now, is cross-platform, L34), the Gemini `interactions` input shape (§6, Task 20; verified
  live on 2026-09-21 with google-genai 2.23.0, see `src/scry/outline.py` and L58), the macOS floor for Vision
  revision 3 (moot: the Vision adapter is removed).
