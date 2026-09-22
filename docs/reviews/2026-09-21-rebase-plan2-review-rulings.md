# Review: re-base plan 2 (`annotate`), held to the owner's rulings and to simplicity

Reviewed: `docs/superpowers/plans/2026-09-21-rebase-boxes-2-annotate.md` (16 tasks, 1,585 lines) against
`docs/proposals/2026-09-21-boxes-mode-rebase.md` (revision 3, §12 included), ledger L28–L46, plan 1 as reconciled
(header, decisions, "Returns with" table, Tasks 4 and 11), the interface sections of plans 3 and 4, and the tag
`pre-rebase-boxes` (`perceive.py`, `prompts/stage2c.py`, `merge.agreement`, `diagnostics.mark_match`,
`overlay.run_overlay`, the old schema descriptions).

Method: reading and reasoning only. Commands were limited to reading files and git history (`sed`, `grep`, `git show`,
`git log`). No prototype, script or experiment was written or run, no test was run, no model was called, nothing was
committed, and nothing was edited but this file. Figures marked **[estimated]** are arithmetic on ledger numbers, not
measurements. The lens is the owner's rulings: every finding asks for something to be removed, deferred or stated,
none asks for new machinery.

**Verdict: accept with changes.** Tasks 1–11 (what P1 needs) are sound, honour the flat-container, no-focus,
description-kept and co-equal-bases rulings, and can start once B1 is fixed; S4 and S5 are one-line changes inside
them. Tasks 12, 13 and 15 stand. Task 14 should be deferred. Task 16 should be reduced before it is built (B2): as
written it decides, by construction, an evaluation the owner asked to be left open.

## Blocking

**B1. Task 5, schema field descriptions: the evaluated video's content is in the prompt.** `OutContainer.name` gives
the example `'tooltip: Cloud Shell'` and `app` gives `'PowerShell'`. The Cloud Shell tooltip is frame 149's popup, one
of the two frames behind the spec's guard "popups found on frames 149 and 151" (§9; L40, L42), and PowerShell is span
2's window. Field descriptions travel in the JSON schema, so this is prompt text (the plan says so itself). It breaks
ruling 2 and contaminates a P1–P2 guard and the by-eye container judgement. The tag's descriptions had neither
(`'Windows Terminal', 'Browser', 'VS Code', 'Notepad'`; `'Save dialog'`). Fix by removal: drop those two examples, keep
`'Browser'`, `'VS Code'`, `'Save dialog'`. It must happen before P1, because every paid answer is cached under this
schema hash. Blocks Task 5.

**B2. D6 and Task 16: the answer-dependent context costs incremental annotation the batch discount, and the context
buys something the spec says has no value.** Blocks Task 16 and P3, not P1.
- *Consequence.* Known containers, neighbours' containers and link state are built from earlier answers, so calls are
  chained, so batch is refused. P3 then sets incremental-sync against every-frame-batch. From L29, L33 and L35 a
  transcribing call is about $0.12, of which output is about $0.07 and the two images about $0.04–0.05; incremental
  annotation shrinks only the output share (D5 says so: it saves boxes per call, not calls). With a quarter of the
  boxes as targets, incremental-sync is about $0.07 against every-frame-batch at $0.06 **[estimated; P0 gives the real
  target share]**. The option loses or ties on price by construction while carrying every risk §6 lists. Plan 4
  also shows a batch price for every run (`dollars_batch` in its Task 1, "the same at the batch price" in its report),
  which for an incremental run is a price nobody can pay. Ruling 6 says this option is evaluated, not decided; D6 quietly decides it.
- *What the context buys.* Stable container ids and names across frames. §9: "Label consistency across frames decides
  nothing." §11: "No window identity across frames." Plan 3 never compares containers across records.
- *The simpler rule,* which the plan names and declines: build the request from measured records only. Tasks 3, 6, 7
  and 10 already implement it: targets are named in the user turn, the overlay numbers every box (D7), repair already
  drops non-target assigns and target-less links, and the join already carries labels along lifetimes. Each call lists
  the containers on screen exactly as an every-frame call does and assigns only its targets. D15's already-linked
  check needs earlier answers but is post-processing: it runs after the answers are in, in frame order, under sync or
  batch alike. **Removed by this:** `chains` and `CallPlan.head` (Task 3), `context.py` whole, `known_as` (D3), D27 and
  `neighbour_reach`, D28 and `update_known_rects`, the four keyword arguments of `repair` and
  `test_repair_with_known_context`, the batch-refusal validator, Review Focus 3. Arms B and C become incremental for
  free (code assigns the targets' centres). A renamed window is re-listed at the next call instead of keeping a frozen
  name, which removes one of §6's listed risks at screen level. Task 16 shrinks from 109 lines to about 40.
- *Honest costs of the simpler rule:* each call re-lists the containers (tens of output tokens; arms B and C do that
  under D28 anyway); two boxes of one window labelled by different calls carry separately proposed container labels
  (§11 already accepts that names vary by call; plan 4's by-eye sheet would group by source record and id); the model
  is not told which known boxes are linked, so `link_already_linked` fires more often, counted; a link between a target
  and a known box is not checked for crossing containers (see S4).
- It departs from one sentence of spec §6 ("the call also carries the known containers and the target boxes'
  neighbours"), so it needs a ledger row. **If the coordinator keeps that sentence instead:** D6's refusal stands, the
  manifest and plan 4 must not show a batch price for incremental runs (`None`, not a number), the P3 report must say
  the comparison mixes two price regimes, and S2 and S3 below apply.

## Should-fix

**S1. Defer Task 14 (D18, `TextReading.named` in D19, the last clause of D22).** No phase P1–P5 and no matrix in plan 4
sets `text_assignment` (no occurrence of the key in plans 3 or 4). Its evidence, the model putting 5 of 53 settled
readings on a neighbouring row (L43), was measured under the old parallel `rows` / `vlm_lines` arrays; §6 replaced those
with `{box, text}` objects for exactly that fault. That is a repair for a mechanism already removed. `mark_match` on
P1's transcribing runs is the evidence that would justify it, and because it is post-processing on cached answers
(D22) it can be added later at no model cost and compared on P1's own outputs. Deferring removes `readings.py`, two
config keys (one an unevidenced 2.0 box heights), `named`, `text_unplaced` and eight tests.

**S2. D3: remove `known_as` and the stored notion behind `container_ref`.** Direct answer to the brief: it gates and
alters nothing measured, so it does not breach "labels never gate, never alter measured records". It is, though, a
cross-frame container identity kept up by the model: §3 lists "region correspondence" as removed and §11 says there is
no window identity across frames. No consumer needs it: plan 3 never reads it; plan 4 uses `container_ref` only to
group one frame's boxes and count its popups, where D3's own numbering already makes the plain id in force unique.
Group by `container.id`. (Under B2's simpler rule `container_ref` is at most the derived string `<source frame>:<id>`,
never stored.)

**S3. Defer incremental × arms B and C (D28, the last clause of D17, the B/C `+inc` paragraph, rectangles in the
known-container lines), exactly as D12 defers pane × B and C.** P3 is 12 runs on one arm (§9). D28 is also where a
model-maintained id matters most: code moves a known container's rectangle on the model's say-so that "c1" is still the
same window, and L41 recorded ids shuffled on a dense strip. Refuse the combination in config until P2 picks B or C.
Moot under B2's simpler rule.

**S4. D14 (Task 7 rule 15) is stricter than the spec; remove the extra clause.** The spec drops "a link across two
containers". The plan also drops any link with a member that has no container, under the counter
`link_cross_container`. One slip in `assign` then costs the link too (Task 9's own `test_repairs_are_counted_not_fatal`
shows the cascade), and under arms B and C every `ambiguous` or `outside` box takes its links with it, so P2's
link-quality comparison across arms would partly measure container assignment. Drop a link only when two members have
different containers.

**S5. `mark_match` comes back as a function nothing calls (Task 10 rule 8, IA12).** It is not in Task 9's manifest and
does not occur in plans 3 or 4. It is the check that caught the first live failure (L28–L30) and the evidence S1 waits
for. Put `(hits, total)` into the `annotate` manifest entry when transcribing; no new module or report.

**S6. Tests (ruling 8; L45 cut plan 1's CLI smoke tests): about 100 new named tests for one stage (107 names in all).** Cut those that pin absence,
wording or structure rather than behaviour: `test_mask_code_is_gone`, `test_overlay_config_is_font_only`,
`test_old_vocabulary_is_absent`, `test_tag_width_grows_with_the_number`, `test_fixture_t_is_consistent`,
`test_models_are_memoised_and_named`, `test_cli_annotate`, `test_stage_list`, `test_scaled_coordinates_sentence`; and fold
`test_arm_paragraph_differences`, `test_pane_changes_one_paragraph` and `test_incremental_inserts_one_paragraph` into one
test (the paragraphs are written out in full and copied; one check that variants differ only where intended is enough).
With Task 14's eight that is about twenty fewer. Keep `test_writes_only_its_own_files`: it is the test of ruling 4. Keep
all of Task 7's and Task 10's: repair and the join are where a wrong rule costs money.

## Nits

- **N1 (D11).** Sound as the smallest rule, but it reads `cfg.track.margin`, which P0 sweeps (0, 0.25, 0.5, 1.0). If P0
  settles on 0 (L38 measured the margin's benefit as nil), an arm C point must fall inside a box, and arm C is handicapped
  in P2 for a reason that has nothing to do with arm C. L38 measured OCR boxes against pixel components, not a model's
  pointing error; the justification is an analogy. No new key: the coordinator should know the coupling.
- **N2 (D27).** Relative and not fitted: the sample figure (7–25 line heights; it is in `docs/open-items.md`, not L29) is
  used to justify having *no* horizontal limit. Rest that on L37 instead (the owner retired the horizontal gap cap as a
  finicky heuristic). The 1.0 has no evidence. Gone under B2.
- **N3 (D26).** The 2 is not fitted: it first appears in the scaffolding commit `15b8efc`, before the first live run, and
  L30's `[8] Node pools` (three characters, not caught) shows it was never tuned to the sample. A module constant does
  depart from L45's "parameters live in config", applied there to `gap_ratio`. The constant is the smaller choice;
  record the departure rather than thread a config through `Run.load_labels()`.
- **N4 (D20).** Sound: removal with a stated reason, recoverable from the tag; the scale belongs to `[annotate]` because
  arms C and D have no overlay. L40 says the mask modes "remain for experiments"; a ledger line should supersede it.
- **N5 (D24).** Sound: two conditional lines carrying measured facts, nothing new. The tag's system-prompt sentence
  telling the model what to do with animating marks is gone without a stated reason. State one (the description
  paragraph already asks for "anything animating"); do not restore the paragraph.
- **N6 (Task 12).** Arm D's schema differs from arm A's only in its title, and `prompt_version` already puts `+D` in the
  cache key. `output_model("D", …)` can return arm A's classes: four fewer classes, six with the pane.
- **N7 (D17).** Under arm C `non_text` cannot arise, so icon boxes stay in index text and in `text_missing`; `repairs`
  and the agreement denominators are therefore not comparable across arms. Say so where P2 reads them.
- **N8 (Task 16, the A/D `+inc` paragraph).** It says the description covers the whole screen and is silent on
  `missed`, which D16 also treats as screen-level: a missed text reported once would vanish from later frames' labels
  while still on screen (ruling 3, in incremental mode only). One sentence.
- **N9.** The one coordinate-list configuration ever measured (L42: overlay *plus* list, at 0.67) is none of the four
  arms; arm D has no overlay. That is the spec's and the owner's definition. State it so it is not a silent drop; do
  not add an arm.
- **N10.** `agreement` no longer returns which token the glyph strip removed (`ocr_glyph_stripped` at the tag). No
  consumer; state it.
- **N11 (D21).** `transcribe = true` as the default is harmless while plan 4's matrices set each base explicitly.

## A. Decisions and interface assumptions

| | Verdict |
|---|---|
| D1, D2, D7, D8, D9, D12, D13, D16, D19 (less `known_as`, `named`), D22 (less its last clause), D23, D25 | Sound. D1 and D7 are what make B2's simpler rule nearly free. D2 rests on reading the installed SDK, which is reading. D16 is the most intricate rule in the plan and I could not make it smaller: one rule serves both modes, and "unknown rather than stale" after a failed call is persistence-is-not-evidence applied to labels. |
| D3 | First sentence sound. `known_as`: remove (S2, B2). |
| D4, D5 | Sound. A failed head call leaves every box on screen unlabelled for its lifetime; `failed_targets` shows it; no retry rule should be added. |
| D6 | B2. |
| D10 | Sound, and the smallest honest rule: code resolves overlaps only from the model's own `covers` and otherwise counts. Direct `covers` suffices for a stack (A covers B, B covers C leaves A). |
| D11 | Sound; N1. |
| D14 | S4. |
| D15 | Sound as drop-not-rescue; its stated cost (a run cannot grow by a third line) is counted. The check can run after the fact (B2). |
| D17 | Sound for every-frame; incremental clause deferred (S3); N7. |
| D18 | Defer (S1). |
| D20, D24, D26, D27, D21 | N4, N5, N3, N2, N11. |
| D28 | Defer or remove (S3, B2). |
| IA1–IA5, IA10 | Match plan 1 as reconciled (its Task 4, Task 11, D7, D15, D16). |
| IA6 | Fine. |
| IA7 | `STAGES` order conflicts with plan 3 (its A9 f). Coordinator. |
| IA8 | Task 8 (80 lines) is written in two plans. One owner: plan 2, since §10 builds `annotate` first; plan 3 drops its copy; one import style for `tests/fakes.py`. |
| IA9 | Right, and a removal: one rule, one implementation. Plan 1 is being implemented now, so the coordinator decides when `incremental_projection` starts calling `plan_calls` and which count P0 reports. |
| IA11 | Already reconciled in plan 4 (`p3.toml` sets `annotate.mode`). |
| IA12 | Everything returns; `mark_match` is unwired (S5). |

## B. The split

Right. Tasks 1–11 are exactly §10 step 3 plus the accounting P1 needs. Of the switches: Tasks 12 and 13 must exist
before P2 (ruling 6) and gain nothing from merging; N6 is their only cut. Task 14 serves no phase: defer (S1). Task 15
is 40 lines for a phase the owner asked for: keep. Task 16: reduce (B2), or at least narrow to arms A and D (S3).
`chains` and `head` in Task 3 serve only Task 16 and go with B2. None of this blocks arms × scales, transcribing
against group-only, incremental or the pane label.

## C. The arm A prompt

Honours rulings 3 to 5: the description paragraph is in both variants; containers are flat with `owner` and `covers`
only; no focus, caret, cursor or suggestion wording; group-only swaps one whole paragraph, so neither base is the
other's afterthought. Nothing of rows, regions, marks or focus is left; `occludes` became `covers`. Readable: seven
paragraphs, each starting with the field it explains. Two things: the leak in the field descriptions (B1), and the
dropped animating sentence (N5). "A two-column grid of labels and values is pairs" and "three or more columns" come
from the spec's draft and are general UI statements, not sample constants.

## D. What plan 1 handed over

| From the tag | Returns in | Note |
|---|---|---|
| The labelling call, concurrency bound, error records | Task 9 | Better than the tag: the user turn's text is now hashed (D22); the tag hashed only the two images. |
| The prompt and its group-only variant | Task 5 | Focus paragraph gone by ruling; animating sentence gone unstated (N5). |
| The overlay and its place in the pipeline, `label_clashes` | Tasks 4, 9 | Drawn inside the stage; mask modes removed with a reason (N4). |
| `stage2c_transcribe`, `stage2c_panes`, `stage2c_mark_coords`, `[overlay] scale`, `effort_stage2c` | `transcribe`, `pane`, arm D, `[annotate] scale`, `effort_annotate` | Overlay-plus-list is not an arm (N9). |
| The batch path | Tasks 8, 9 | Every-frame only (B2). |
| `agreement` with the glyph strip | Task 10 | Config key becomes a constant (N3); stripped token no longer returned (N10). |
| `mark_match` | Task 10 | Defined, never called (S5). |
| Cost accounting with cache-creation tokens, usage over retries | Tasks 8, 9 | Correct; duplicated in plan 3 (IA8). |

Nothing findable today is lost by this plan in every-frame mode. The one findability loss I found is incremental-only (N8).

## E. Size

| Cut | Lines, about | Also removes |
|---|---|---|
| Task 14 deferred (S1) | 65 | D18, two config keys, `named`, one repair key, 8 tests |
| Task 16 reduced (B2) | 70, plus 30 in Tasks 3 and 7 | D6's refusal, D27, D28, half of D3, `context.py`, Review Focus 3 |
| Tests that pin wording or absence (S6) | 30 | about 11 tests |
| Arm D reuses arm A's classes (N6) | 5 | 4–6 classes |
| Task 8 in one plan only (IA8) | 80, in plan 3 | — |

About 1,585 → 1,380 lines and 16 → 15 tasks, with the largest mechanism of the plan gone.

## For the coordinator to decide

1. **B2:** build incremental requests from measured records only (a ledger row: departs from one sentence of §6), or
   keep the spec's context and accept that P3 compares incremental-sync with every-frame-batch, with no batch price
   shown for incremental runs.
2. **S1:** defer Task 14 until P1's `mark_match` and by-eye reading show misassignment under the `{box, text}` schema.
3. **S3:** if the context stays, refuse incremental with arms B and C until P2 picks one.
4. **N3:** `GLYPH_MAX_LEN` as a constant against L45's "parameters live in config".
5. **N4:** a ledger line superseding L40's "the modes remain for experiments".
6. **IA7, IA8, IA9:** `STAGES` order; who owns Task 8 and the `fakes` import style; when plan 1's projection starts
   calling `plan_calls`.
7. **N1:** arm C's snapping follows `track.margin`; if P0 moves the margin, arm C moves with it.
