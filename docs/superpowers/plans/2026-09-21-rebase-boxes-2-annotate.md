# Re-base step 2: `annotate`, the one call that proposes labels — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **One deliberate adaptation of the writing-plans format: this plan contains NO implementation bodies and no test
> code.** The owner forbids code that exists anywhere except as the real implementation on the branch with its tests;
> no drafter or reviewer writes a prototype, a scratch script or a trial of any kind (spec §12). So every task gives:
> the files; the public interface (signatures with types, pydantic record fields, config keys with defaults and
> units); the behaviour as numbered rules precise enough that two implementers produce the same outputs, each traced
> to the spec section it implements; the tests to write FIRST, each named, with its concrete fixture and exact expected
> values; the commands; the commit. Prompt text is specification, not code, and is written out in full. Nothing in this
> plan was executed: every expected value was derived by hand from the rules. Reviewers read and reason; they run
> nothing.

**Goal:** On branch `rebase-boxes`, build the `annotate` stage: one model call per frame (or per changed frame) that
proposes labels for OCR boxes — containers, typed links, optionally a second reading, and a screen description — written
to `annotations.jsonl`, plus the loader that joins those labels onto boxes, changes and lifetimes on read.

**Architecture:** The model proposes, code disposes. Whatever the referencing arm, the model's answer is converted by
pure functions into one arm-independent proposal, repaired (never aborted) against the measured boxes, and stored in one
record shape; measured files are never touched and nothing downstream is gated on a label. A pure planner decides
which frames get a call and which boxes are targets from `track`'s records alone, so the same stage code runs "every
frame" and "incremental". The existing Anthropic provider, call cache and batch path carry the calls; a joined view
(`Labels`) gives later stages labels per box, per frame and per lifetime.

**Tech stack:** Python ≥ 3.12 with `uv`; pydantic 2 (records and the structured-output schemas); the `anthropic` SDK
≥ 1.5 through the existing `AnthropicProvider` (`messages.parse`, prompt caching, Batches); Pillow (overlay, scaling);
rapidfuzz (through `scry.textdiff.similarity`); typer; pytest. No new dependencies.

**Spec:** `docs/proposals/2026-09-21-boxes-mode-rebase.md`, revision 3: §2 (the order, incremental annotation, the
"no annotation" base), §3, §4 (principles 1, 5, 7, 9), §5 (`annotations.jsonl`), §6 `annotate`, §7, §8, §9 (P1–P4),
§10 steps 3 and 8, §11, and §12 "Simplify before repairing". Evidence: `docs/decision-ledger.md` L28–L43. Executors read the spec with this plan. Sibling
plans: `…-rebase-boxes-1-read-track.md` (plan 1: branch hygiene, `frames.jsonl`, `boxes.jsonl`, `changes.jsonl`,
`lifetimes.jsonl`, `read`, `track`) and `…-rebase-boxes-3-interpret-summarize-index-ask.md` (plan 3, which consumes
this plan's joined view). Spec §5 is the contract between the plans.

## Interface assumptions (for the synthesis pass)

Things this plan needs that spec §5 does not pin down, or names chosen by a sibling plan. A different name elsewhere
is a rename here; a different meaning is a conflict to reconcile.

- **IA1. Plan 1's records and loaders as its Task 4:** `BBox`, `Frame` (`video_id, frame, t_change, t_settled, t_end,
  settled, churn_regions, caret, width, height, sha256, png`), `RawWord`, `Box` (`id, bbox, text, conf, words,
  in_churn`), `FrameBoxes` (`frame, png, engine, seconds, boxes`), `PixelStats` (`changed_fraction, components,
  textless, textless_area, touched_share, rect_only`), `Change`, `FrameTime`, `Lifetime`, `box_ref(frame, box_id)`,
  `parse_box_ref(ref)`; `Run.frames`, `Run.boxes`, `Run.changes`, `Run.lifetimes`, `Run.overlays_dir`, `Run.cache_dir`
  and `load_frames()`, `load_boxes()`, `load_changes()`, `load_lifetimes()`, each `[]` for an absent file.
- **IA2. Reading order is `read`'s id order** (plan 1 D7): `FrameBoxes.boxes` is sorted by top edge then left edge and
  numbered `b1`, `b2`, …; "reading order" in this plan always means that list order.
- **IA3. Lifetimes partition the boxes.** Every box of every frame is in exactly one `Lifetime.boxes` list; a lifetime
  holds at most one box per frame, over consecutive emitted frames; `boxes` is in frame order and `first.frame` is the
  frame of `boxes[0]`; a lifetime that stopped never resumes. A box continues a lifetime when `track` found it
  untouched, in the same place, moved, or a `reread`; the `after` box of an `appended`, `truncated`, `changed` or
  `appeared` record and every `flicker_new` box start one (plan 1 as reconciled: Tasks 10–11, its `targets(change)`).
- **IA4. One `Change` per consecutive pair of emitted frames**, found by `to_frame`; `pixels is None` when pixel
  evidence is missing; `pixels.components` counts the changed components that survive θmin over the whole frame, so
  `components == 0` means "no changed pixel that counts" (spec §6 `track` step 1).
- **IA5. `cfg.track.margin: float = 0.5`** (× the median box height) and
  `scry.track.pixels.margin_px(a_boxes: list[Box], b_boxes: list[Box], margin: float) -> int` =
  `floor(margin × median + 0.5)`, 0 with no boxes (plan 1 Task 7, D16). This plan calls `margin_px(boxes, [], …)` for
  one frame.
- **IA6. Config conventions:** every config model has `extra="forbid"`; `ModelConfig` keeps `provider, model,
  max_tokens, retry_max_tokens, concurrency, mode` and has no per-stage effort key when this plan starts (plan 3 adds
  `effort_interpret`, `effort_summarize`, `effort_ask`; this plan adds `effort_annotate` in the same style);
  `OverlayConfig` still has `font_size, font_path, scale, mask` when this plan starts.
- **IA7. `scry.overlay` after plan 1:** `place_label`, `scale_image`, `mask_image`, `draw_overlay(png_in, boxes:
  list[Box], png_out, cfg: OverlayConfig) -> int`, no `run_overlay`. `scry.costs.PRICES` and `estimate_cost(usage,
  model)`. `scry.textdiff.norm` and `similarity`. CLI `STAGES == ["outline", "decode", "read", "track"]`.
- **IA8. Shared with plan 3, created by whichever lands first (its A6):** `src/scry/prompts/__init__.py` (empty),
  `scry.providers.batch.run_with_batches`, `tests/fakes.py`, and the cost-accounting fix. Spec §10 builds `annotate`
  before `interpret`, so this plan creates them (Tasks 8 and 9) **with the definitions and test values of plan 3's
  Tasks 1 and 3** (`USAGE`, `USAGE_KEYS`, `CACHE_WRITE_MULTIPLIER`, `BATCH_MULTIPLIER`, `add_usage`, `estimate_cost(…,
  batch)`, usage summed over retries, the batch usage key). Plan 3 keeps only what it adds (`ScriptedProvider`,
  `stage_cost`, `run_costs`, `FakeSyncMessages`). This plan's joined view uses the names plan 3's A4 assumes: `Run.
  load_labels() -> Labels | None`, `Labels.box/frame/lifetime`, `BoxLabel`, `BoxLink`, `FrameLabel`, `LifetimeLabel`.
- **IA9. One rule, two statements.** Plan 1 as reconciled (its Task 13 rules 6–7) prices incremental annotation with
  the rule this plan implements in Task 3: a call for the first frame and for every change with `pixels` null or
  `components ≥ 1`; targets are the boxes whose lifetime starts. One difference remains: a box whose lifetime starts on
  a frame that gets no call (a `flicker_new` box on unchanged pixels) is a target of the next call here, and is not
  counted by the projection. Task 3's `plan_calls` is pure and needs only plan 1's records; the synthesis pass should
  make `incremental_projection` call it, so the price and the stage cannot drift apart.
- **IA10. Majority ties:** plan 1 gives a tie to the reading sighted first (its D15); the model's majority reading
  per lifetime uses the same rule.
- **IA11. Plan 4 (`…-4-evaluation.md`) assumes other config names** (its A8): `annotate.incremental` (bool), and the
  "no annotation" base made by skipping the stage. Here they are `[annotate] mode = "incremental"` and `mode = "off"`
  (plan 3's A5 already uses `mode`); in plan 4 that is a rename inside its `evals/*.toml` files, and skipping the stage
  keeps working as long as the run directory has no `annotations.jsonl`. Its A5–A7 hold as written: `run_annotate(run,
  cfg)`, a manifest entry with four-key `usage`, `model` and `cache`, per-record `usage`, and the joined view of Tasks
  10–11 (containers and links per frame, the majority reading per lifetime).
- **IA12. Plan 1's "Returns with" table** hands this plan the labelling call, its prompt, the overlay's place in the
  pipeline, the batch path, per-box agreement with the icon-glyph strip, and `mark_match`. They return in Tasks 5, 9, 4
  and 9, 8, 10 and 10.

## Decisions this plan makes (for the reviewers)

The spec is silent or looser on each of these. None is settled until reviewed. Each names the principle it rests on.

- **D1. One stored shape under every arm.** Arm-specific answers (rectangles, points) are converted to ids by code
  before repair; `annotations.jsonl` and the loader never know the arm (§5: one record per call; principle 1).
- **D2. The model-facing schema has three link lists (`runs`, `pairs`, `records`), rectangles and points as objects
  with named integer fields, and every field required.** Reason, from reading the installed SDK
  (`anthropic/lib/_parse/_transform.py`, 1.5.0): a tagged union becomes `anyOf` with its `discriminator` pasted into
  the description, a tuple's `prefixItems` is pasted there too instead of staying schema, and defaulted fields
  become optional. §6 already
  demands "lists of objects, never arrays parallel to an id list". The stored record keeps §5's single `links` list
  with `kind`.
- **D3. Container ids are local to a record; a container that an incremental call was told about keeps its id and
  carries `known_as = "<frame>:<id>"`, the record that first proposed it.** Two boxes are in the same container when
  those references are equal. New containers are numbered after the highest known id, so the ids in force on one
  frame are unique. Nothing mechanical depends on it (§11: no window identity across frames).
- **D4. Targets are a pure function of `track`'s records:** a box is a target of the first call made at or after its
  lifetime's first frame. A failed call's targets are not asked again; they stay unlabelled and are counted. This keeps
  model behaviour out of what is asked and lets P0 price P3 with no model (§9 P0; principle 1).
- **D5. Call rule:** the first frame, and every frame whose incoming change has `pixels is None` or
  `pixels.components > 0`; no transition kind is consulted (§2 says "whenever pixels changed" and names no exception).
  `decode` emits a frame only on change, so nearly every frame gets a call: what incremental annotation saves is boxes
  per call, which P0's projection prices.
- **D6. Incremental calls run in frame order inside a chain, because the context of a call (known containers, the
  neighbours' containers and link state) is built from earlier answers.** A chain starts at a frame where every box is
  a target (the first frame, a cut); chains run concurrently. **Batch mode is therefore refused with incremental
  annotation** (a config error). Consequence the owner should see before P3: the Batches discount (half price) is
  available to every-frame annotation only, so P3 must set incremental-sync beside every-frame-sync and
  every-frame-batch. A context built only from measured records would make the calls independent again; the spec asks
  for known containers in the context, so that variant is not built.
- **D7. The overlay numbers every box in both modes; targets are named in the text.** The image of a frame is then the
  same in P1 and P3, "text no box covers" keeps its meaning for `missed`, and no second, untested overlay style is
  introduced (L28–L29: legibility was the first live failure).
- **D8. No OCR text is ever sent to the model,** in any arm or mode (arm D's list and the neighbour list carry ids,
  rectangles and container ids only). Exact agreement of two independent readers is the only "quote verbatim" signal
  (§7); showing OCR's reading would end the independence.
- **D9. Every coordinate in a request or an answer is in original-frame pixels, at every image scale;** the user turn
  states the frame size (the form L42 measured for the coordinate list at scale 0.67).
- **D10. Front-most rule for arms B and C:** among the containers whose rectangle holds the box centre, drop those
  that another candidate lists in `covers`; if exactly one remains it wins; otherwise the box is unassigned and counted
  `ambiguous`. No "a popup beats a window" tie-break, no area heuristic, no transitive closure: the count is what P2
  reads, and logic is added only on that evidence (§12, simplify before repairing).
- **D11. A point snaps to the nearest box only within `track`'s margin** (half a median box height, IA5): the model's
  point and OCR's rectangle come from different tools, which is what that margin is for (L38). No new constant.
- **D12. The pane label exists only under arms A and D** (it rides on `assign` entries, which B and C do not have).
  If P2 picks B or C, P4's pane needs a design; the config refuses the combination until then.
- **D13. "A box is in at most one link" exempts `header` references.** §5's own example gives every record of a table
  the same header boxes. In every other respect a header id is checked like a member: a bad one drops the record
  (§12: no rescue rule without evidence).
- **D14. A link must lie wholly inside one container:** every member assigned, all to the same container; otherwise
  dropped and counted (§3: "a typed relation among boxes of one container").
- **D15. Incremental links never re-label known boxes:** a link naming a known box that is already in a link in force
  is dropped (so a run cannot grow by a third line; counted `link_already_linked`, which P3 reads), and a link naming
  no target is dropped (§6 risks: "nothing is re-annotated").
- **D16. What is in force at a frame.** Box labels: the box's own record if it was a target of a successful record,
  else the latest earlier record in which a box of its lifetime was (§5). A link: every lifetime it names still has a
  box at the frame, and its target members still draw their labels from the record that proposed it. The description,
  the missed texts and the container list are screen-level: those of the latest record at or before the frame, and
  unknown (`None`, `[]`, `[]`) when that record failed.
- **D17. Arm C details:** `missed` is derived by code (a reading whose point snaps to no box); icons are left out
  rather than returned as `""`, so `non_text` cannot arise; with incremental annotation the targets are given as
  rectangles and `missed` covers the target areas only (an enrichment, never in a change record).
- **D18. Assignment of readings by position and similarity has no threshold:** a reading leaves the box the model
  named only for a box within `assign_reach` box heights whose OCR text is strictly more similar to it; claims are
  honoured in order of similarity, then distance; a reading left without a box is dropped and counted. The model's own
  reference is kept in `named` (principle 5; §7).
- **D19. Additions to §5's record:** `Container.known_as`, `TextReading.named`, `repair_counts` (the breakdown of
  `repairs`), `label_clashes`; `texts` is `null` for a group-only call and a list for a transcribing one.
- **D20. The mask modes leave `overlay.py`, and the image scale moves to `[annotate] scale`.** L40 measured masking
  and did not adopt it; the spec's evaluation has no mask arm; arms C and D scale an image with no overlay.
- **D21. Defaults:** `mode = "every_frame"`, `arm = "A"`, `transcribe = true`, `pane = false`, `scale = 1.0` — the
  configuration of §5's example record and of §10 step 3. A default is not a verdict: transcribing and group-only are
  co-equal (§0) and P1 sets each base explicitly in its own config file.
- **D22. The prompt version names the system prompt and schema variant (arm, group-only, pane, incremental, scale);
  the user turn is covered by `input_hashes`; post-processing switches (`text_assignment`, `assign_reach`) change no cache
  key,** so they can be compared downstream of one fixed answer (§9 evidence rules).
- **D23. Costs are cold-equivalent:** the manifest sums the usage stored with every record, cache hits included, and
  prices it both ways (synchronous and batch). Cache-creation tokens are priced at 1.25 × input; usage is summed over
  a call's retries (open item "Usage accounting"; principle 9).
- **D24. Two lines of today's user turn are kept:** the boxes inside animating areas and the "not settled" note. They
  are measured facts (`in_churn`, `settled`) that §5 still records.
- **D25. `mode = "off"` removes an existing `annotations.jsonl`** (the call cache keeps every paid answer, so turning
  annotation back on costs nothing) and `Run.load_labels()` is `None`; the "no annotation" base then cannot read stale
  labels.
- **D26. `agree`** is today's rule unchanged: equality after `textdiff.norm`, or equality after dropping one leading
  or trailing OCR token of at most 2 characters (§5: "icon-glyph strip kept"). The 2 was `[merge] glyph_max_len`; it
  becomes the constant `GLYPH_MAX_LEN` beside the rule, because the loader is called without a config
  (`Run.load_labels()`), it is counted in characters and nothing in the evaluation varies it.
- **D27. Neighbours are the carried boxes in a band of `neighbour_reach` box heights above and below a target, across
  the whole frame width,** because label-and-value gaps measured 7–25 line heights (L29) and a wrapped run continues on
  the next line.
- **D28. Under arms B and C an incremental call returns every container now on screen with its current rectangle;**
  a repeated known id supplies only `rect` and `covers`, never a new name. Under A and D it returns only new
  containers and a repeated known id is ignored.

## Global Constraints

- Work only on branch `rebase-boxes`, after plan 1's Task 12 (`track`) has landed. The package imports and
  `uv run pytest` reports 0 failures after every commit.
- **Model proposals never gate or alter measured records.** Nothing in this plan writes `frames.jsonl`, `boxes.jsonl`,
  `changes.jsonl` or `lifetimes.jsonl`, and no measured stage reads `annotations.jsonl` (principle 1; spec §2: "every
  stage writes only its own file").
- Unit tests only: the fake clients of `tests/fakes.py`, synthetic frames made in the test, hand-written records. No
  network, no model API call, no sample video, no run directory under `runs/`. No prototypes, scratch scripts or trial
  runs by anyone.
- No constants from the sample video: every geometric parameter is relative to box height or frame size, lives in
  `src/scry/config.py` with its unit in a comment, and appears in `scry.toml`.
- No logic for watch-list cases without evidence; no cursor or suggestion locating; no brightness thresholds; nothing
  reasons from how long a text stayed on screen.
- Validation is repair, never abort: a bad answer costs labels, is counted, and the run continues (§6).
- **Simplify before repairing (spec §12).** When a review or the first runs find a fault in a mechanism of this plan,
  the first question is whether the mechanism can go; logic is added only on evidence from real runs. Every rule here
  that drops a label instead of rescuing it (`ambiguous`, `link_already_linked`, `second_text`, `text_unplaced`) is that
  choice, and its counter is the evidence a later rule would need.
- Coordinates: `BBox = (x0, y0, x1, y1)` in original-frame pixels, `x1`/`y1` exclusive. A point `(x, y)` is inside a
  rectangle when `x0 ≤ x < x1` and `y0 ≤ y < y1`.
- The old vocabulary does not return: no mark, line id, row, region, unit, association or focus in code, prompts,
  records or tests (§3).
- Every stage writes only its own file, atomically (`scry.jsonl.write_jsonl`), and skips itself when its inputs hash
  and config hash are unchanged (`Run.stage_up_to_date`).
- Commit messages end with the attribution lines the session supplies.

## Review Focus

Inputs the spec implies and that are most likely to bite; each has a test in the task that owns the code.

1. **An answer that names things that do not exist:** unknown box ids, a box assigned twice, a link across two
   windows, a container that names itself as owner. Expect repairs counted, a valid record, no exception (Task 7
   `test_repair_assign`, `test_repair_links`, `test_repair_containers`).
2. **A frame with no boxes** (a blank or image-only slide). Expect a call all the same (the description), an overlay
   identical in size to the frame, `targets == []`, empty lists, no division by zero in any median (Task 4
   `test_overlay_of_a_frame_without_boxes_is_the_frame`, Task 6 `test_blocks_for_a_frame_without_boxes`, Task 9
   `test_frame_without_boxes_still_gets_a_call`, Task 13 `median_box_height([]) == 0.0`).
3. **A failed call in the middle of an incremental chain** (refusal, schema failure twice). Expect the record with
   `error`, later calls still made in order, the failed call's boxes unlabelled and described to the next call as
   `no container`, the description unknown until the next successful call (Task 16
   `test_failed_call_does_not_stop_the_chain`, Task 10 `test_failed_record_is_not_a_source`).
4. **Rectangles and points outside the frame, inverted or empty** (arms B, C). Expect clamping, `bad_rect`, a box
   outside every rectangle unassigned, a far point snapped to nothing (Task 13 `test_rect_sanitising`,
   `test_snap_within_margin_only`).
5. **Quotes, backslashes, newlines and non-ASCII in names and texts** (`PS C:\Users\msadmin>`, `区`, a window title
   with a double quote). Expect a lossless JSONL round trip and known containers rendered as valid JSON lines (Task 2
   `test_annotation_round_trip_unicode`, Task 16 `test_known_containers_are_json_lines`).

Known and not tested here: in batch mode a truncated or schema-invalid result is terminal (the batch path has no
`max_tokens` or schema retry, as today; batch mode is still unexercised live, open items). The overlay font path is a
macOS path; elsewhere Pillow's default font is used, as today. The arm A system prompt is about 500 tokens, around
Opus 5's 512-token minimum cacheable prefix, so `cache_creation_input_tokens` may be 0; nothing depends on it.

## File structure at the end of this plan

```
src/scry/
  config.py            + AnnotateConfig [annotate]; ModelConfig.effort_annotate; OverlayConfig loses scale and mask
  schemas.py           + Container, Assign, RunLink, PairLink, RecordLink, Link, TextReading, Missed, Annotation,
                         link_members, link_refs
  run.py               + Run.annotations, load_annotations(), load_labels()
  overlay.py           place_label, scale_image, draw_overlay(…, scale)      (mask code removed)
  costs.py             + USAGE_KEYS, CACHE_WRITE_MULTIPLIER, BATCH_MULTIPLIER, add_usage; estimate_cost(…, batch)
  providers/
    anthropic_.py      usage summed over a request's retries
    batch.py           all four usage keys; run_with_batches() (also closes the client inside the loop)
  prompts/
    __init__.py        (empty)
    annotate.py        VERSION, the paragraphs, system_prompt(), prompt_version()
  annotate/
    __init__.py        exports run_annotate
    targets.py         CallPlan, plan_calls, chains                         (pure; no model, no I/O)
    output.py          the model-facing schema variants: output_model(arm, transcribe, pane)
    blocks.py          frame_block, build_blocks, input_hashes              (the user turn)
    proposal.py        Proposal, to_proposal                                (arm answer → ids)
    geometry.py        centre, inside, point_rect_distance, median_box_height, container_at, snap
    readings.py        assign_readings                                      (position and similarity)
    repair.py          REPAIR_KEYS, Repaired, repair
    context.py         CallContext, build_context, context_blocks           (incremental)
    join.py            agreement, BoxLink, BoxLabel, FrameLabel, LifetimeLink, LifetimeLabel, Labels, build_labels
    stage.py           run_annotate
  cli.py               + annotate; STAGES gains "annotate" after "track"
tests/
  fakes.py annotate_fixtures.py
  test_config.py test_schemas.py test_overlay.py test_costs.py test_provider.py test_batch.py      (extended)
  test_annotate_targets.py test_annotate_output.py test_annotate_prompt.py test_annotate_blocks.py
  test_annotate_proposal.py test_annotate_geometry.py test_annotate_readings.py test_annotate_repair.py
  test_annotate_context.py test_annotate_join.py test_annotate_stage.py
```

Tasks 1–11 are what P1 needs (spec §10 step 3: arm A on every frame with the transcribing switch, records, repair,
loaders). Tasks 12–16 are the evaluation switches of §10 step 8 (arms B, C, D; reading assignment; the pane label;
incremental annotation). Task 3 depends only on plan 1's records and may be pulled ahead of plan 1's Task 13 (IA9).

## Shared fixtures (`tests/annotate_fixtures.py`, created in Task 2, extended where a task says so)

`mk(id, x0, y0, x1, y1, text, in_churn=False) -> Box` builds a `Box` with `conf = 1.0`. `frame(n, w, h, settled=True)
-> Frame` builds a `Frame` with `video_id "v"`, `t_change = t_settled = float(n)`, `t_end = n + 1.0`, `sha256 =
"sha-<n>"`, `png = "frames/<n:05d>.png"`. `write_run(tmp_path, frames, frame_boxes, changes=(), lifetimes=()) -> Run`
writes a solid grey `(128, 128, 128)` RGB PNG of each frame's size plus the four JSONL files by hand.

**Fixture E (every frame).** Frames 0 and 1, 128×64. Both frames: `b1 "a" (4,4,40,20)`, `b2 "b" (70,4,110,20)` (far
enough apart that each tag fits to the right of its box whatever the font).

**Fixture S (a screen).** One frame, number 7, 400×200. Boxes, all 16 px tall: `b1 "Browser tab" (10,10,110,26)`,
`b2 "PowerShell" (260,10,390,26)`, `b3 "Resource group" (10,40,90,56)`, `b4 "RG1-Kode" (120,40,240,56)`,
`b5 "PS C:\> az login" (260,40,390,56)`, `b6 "Cloud Shell" (150,100,230,116)`. Centres: b1 (60, 18), b2 (325, 18),
b3 (50, 48), b4 (180, 48), b5 (325, 48), b6 (190, 108). Containers used with it: `c1` window Browser "Azure portal"
rect (0,0,250,200); `c2` window PowerShell "PowerShell 7" rect (250,0,400,200); `c3` popup Browser "tooltip" owner
`c1` rect (140,90,300,130).

**Fixture T (typing, three frames).** Frames 10, 11, 12, 400×200, all boxes 16 px tall.
- Frame 10: `b1 "Resource group" (10,40,110,56)`, `b2 "RG1" (130,40,200,56)`, `b3 "PowerShell 7" (10,80,110,96)`,
  `b4 "PS C:\> az" (10,100,200,116)`.
- Frames 11 and 12: `b1 "Banner" (10,10,110,26)`, `b2 "Resource group" (10,40,110,56)`, `b3 "RG1" (130,40,200,56)`,
  `b4 "PowerShell 7" (10,80,110,96)`, `b5 "PS C:\> az login" (10,100,200,116)`.
- Changes: `T1` 10→11 with `pixels.components = 2`; `T2` 11→12 with `pixels.components = 0` (other `PixelStats`
  fields 0.0 or 0).
- Lifetimes: `L1 "Resource group" [10:b1, 11:b2, 12:b2]`; `L2 "RG1" [10:b2, 11:b3, 12:b3]`; `L3 "PowerShell 7"
  [10:b3, 11:b4, 12:b4]`; `L4 "PS C:\> az" [10:b4]`; `L5 "Banner" [11:b1, 12:b1]`; `L6 "PS C:\> az login" [11:b5,
  12:b5]` (`readings`, `sightings`, `first` and `last` filled in as plan 1's `Lifetime` defines them; nothing here
  reads them except `first.frame` and `text`).
- Record `A10` (frame 10, every box a target): containers `c1` window Browser "Azure portal", `c2` window PowerShell
  "PowerShell 7" (owner null, covers [], rect null, known_as null); assign b1→c1, b2→c1, b3→c2, b4→c2; links
  `[pair key [b1] value [b2]]`; texts b1 "Resource group", b2 "RG1", b3 "PowerShell 7", b4 "PS C:\> a"; missed
  `[m1 "Networking" c1]`; description "d10"; repairs 0; model "fake-model"; prompt_version "annotate-v1+inc".
- Record `A11` (frame 11, targets `[b1, b5]`): containers `c1` and `c2` as above but with `known_as "10:c1"` and
  `"10:c2"`; assign b1→c1, b5→c2; links `[run boxes [b4, b5] joiner " "]`; texts b1 "Banner", b5 "PS C:\> az login";
  missed `[]`; description "d11"; repairs 1; repair_counts `{"link_already_linked": 1}`; prompt_version
  "annotate-v1+inc". There is no record for frame 12.

---

### Task 1: Config: `[annotate]` and the stage's effort

**Files:**
- Modify: `src/scry/config.py`, `scry.toml`, `tests/test_config.py`

**Interfaces:**
- Consumes: `Effort`, `ModelConfig`, `Config` (IA6).
- Produces: `AnnotateConfig` as `Config.annotate` (TOML `[annotate]`) and `ModelConfig.effort_annotate`. The whole
  table is given here once; this task adds the rows marked 1, later tasks add theirs.

| Key | Type and default | Unit, meaning | Task |
|---|---|---|---|
| `mode` | `Literal["every_frame", "off"] = "every_frame"` (Task 16 adds `"incremental"`) | which frames get a call; `off` is the "no annotation" base (§2) | 1, 16 |
| `transcribe` | `bool = True` | `true`: the call also returns a second reading (`texts`, `missed`); `false`: group-only (§0, §7) | 1 |
| `scale` | `float = Field(1.0, gt=0, le=1)` | factor applied to every image sent; tags keep their pixel size (L33, §9 P2) | 1 |
| `arm` | `Literal["A", "B", "C", "D"] = "A"` | referencing arm (§6) | 12 |
| `text_assignment` | `Literal["as_returned", "position_similarity"] = "as_returned"` | how a returned reading finds its box (§7, D18) | 14 |
| `assign_reach` | `float = Field(2.0, ge=0)` | × the frame's median box height: how far from the named box a reading may move | 14 |
| `pane` | `bool = False` | ask for a pane label string per target (arms A, D; §9 P4) | 15 |
| `neighbour_reach` | `float = Field(1.0, ge=0)` | × the frame's median box height: the band above and below a target in which known boxes are listed (D27) | 16 |
| `[model] effort_annotate` | `Effort = "low"` | was `effort_stage2c` (L13) | 1 |

**Rules:**
1. `AnnotateConfig` has `model_config = ConfigDict(extra="forbid")` like every config model (IA6).
2. `scry.toml` gains `[annotate]` with this task's three keys written out at their defaults, and `effort_annotate =
   "low"` under `[model]`. `max_tokens = 16000`, `retry_max_tokens = 32000` (tokens), `concurrency = 4` (calls) and
   `mode = "sync"` under `[model]` are reused unchanged.
3. Nothing else reads these keys yet.

**Tests to write first (`tests/test_config.py`):**
- `test_annotate_defaults`: `Config().annotate.model_dump() == {"mode": "every_frame", "transcribe": True, "scale":
  1.0}` and `Config().model.effort_annotate == "low"`.
- `test_annotate_section_loads`: a TOML holding `[annotate]\nmode = "off"\ntranscribe = false\nscale = 0.5` loads with
  those three values.
- `test_annotate_rejects_bad_values`: each of `scale = 0`, `scale = 1.5`, `mode = "sometimes"` and the stale key `stage2c_rows = "boxes"` under `[annotate]` raises `pydantic.ValidationError`.
- `test_repo_toml_loads` (exists from plan 1) additionally asserts `cfg.annotate.mode == "every_frame"` and
  `cfg.model.effort_annotate == "low"`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_config.py -q`. Expected: FAIL (`Config` has no
  `annotate`).
- [ ] **Step 2:** Add the model, the field and the TOML keys.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(config): [annotate] mode, transcribe, scale; model.effort_annotate`

### Task 2: Records: `annotations.jsonl`

**Files:**
- Modify: `src/scry/schemas.py`, `src/scry/run.py`, `tests/test_schemas.py`
- Create: `tests/annotate_fixtures.py` (the helpers and Fixtures E, S, T of "Shared fixtures" above)

**Interfaces (pydantic `BaseModel`, `extra="ignore"` like plan 1's records):**

```
Container    id: str ("c<n>") · kind: Literal["window", "popup"] · app: str · name: str · owner: str | None = None ·
             covers: list[str] = [] · rect: BBox | None = None · known_as: str | None = None
Assign       box: str · container: str · pane: str | None = None
RunLink      kind: Literal["run"] = "run" · boxes: list[str] · joiner: Literal["", " "]
PairLink     kind: Literal["pair"] = "pair" · key: list[str] · value: list[str]
RecordLink   kind: Literal["record"] = "record" · members: list[list[str]] · header: list[str] = []
Link         = Annotated[RunLink | PairLink | RecordLink, Field(discriminator="kind")]
TextReading  box: str · text: str · named: str | None = None
Missed       id: str ("m<n>", n from 1 in the record) · text: str · container: str | None = None
Annotation   frame: int · targets: list[str] · containers: list[Container] = [] · assign: list[Assign] = [] ·
             links: list[Link] = [] · texts: list[TextReading] | None = None · missed: list[Missed] = [] ·
             unassigned: list[str] = [] · description: str | None = None · repairs: int = 0 ·
             repair_counts: dict[str, int] = {} · label_clashes: int = 0 · model: str · prompt_version: str ·
             usage: dict = {} · error: str | None = None
link_members(link) -> list[str]   run: boxes · pair: key + value · record: the members flattened, left to right
link_refs(link) -> list[str]      link_members(link) + (header for a record)
```

`Run.annotations: Path` = `root / "annotations.jsonl"`; `Run.load_annotations() -> list[Annotation]` (`[]` when absent).

**Rules:**
1. Field names and shapes are spec §5's. Inside a record every box id is frame-local (`"b33"`), every container id is
   record-local. `known_as`, `named`, `repair_counts` and `label_clashes` are additions (D19).
2. `texts is None` means the call did not transcribe (group-only, or it failed); a list, possibly empty, means it did
   (§5: "`texts` exists only when transcribing").
3. `rect` is set only under arms B and C (§5). `known_as` is set only by incremental calls (D3).
4. The link models enforce no minimum lengths: shape is judged by repair (Task 7), so a bad answer can be represented
   and counted rather than raise.
5. One record per call; a failed call is a record with `error` set, `description None`, `texts None` and empty lists,
   and keeps its `targets`.

**Tests to write first (`tests/test_schemas.py`):**
- `test_spec_example_parses`: spec §5's `annotations.jsonl` example, copied verbatim and joined into one JSON line →
  `Annotation.model_validate_json` succeeds; `rec.targets == ["b33"]`;
  `rec.containers[0].covers == ["c1"]` and `.rect is None` and `.known_as is None`; `[l.kind for l in rec.links] ==
  ["pair", "run", "record"]`; `rec.links[1].joiner == ""`; `rec.links[2].header == ["b64", "b65", "b66"]`;
  `rec.texts[0].named is None`; `rec.missed[0].id == "m1"`; `rec.repair_counts == {}`.
- `test_annotation_round_trip_unicode`: an `Annotation` with a container named `He said "hi" — 区`, a text
  `PS C:\Users\msadmin> az login`, a missed text containing a newline, `texts=None` in a second record; written with
  `write_jsonl` and read with `read_jsonl` → equal to the originals; the written `RunLink` line contains
  `"kind":"run"` and no `key` field.
- `test_link_members_and_refs`: `RecordLink(members=[["b70"], ["b71", "b73"], ["b72"]], header=["b64"])` →
  `link_members == ["b70", "b71", "b73", "b72"]`, `link_refs == ["b70", "b71", "b73", "b72", "b64"]`;
  `PairLink(key=["b1"], value=["b2", "b3"])` → members `["b1", "b2", "b3"]`.
- `test_load_annotations_on_a_fresh_run`: `Run(tmp_path / "r").load_annotations() == []`.
- `test_fixture_t_is_consistent`: in Fixture T every box ref of every frame occurs in exactly one lifetime, and `A10`,
  `A11` validate as `Annotation`.

- [ ] **Step 1:** Write the tests and `tests/annotate_fixtures.py`. Run `uv run pytest tests/test_schemas.py -q`.
  Expected: FAIL (`ImportError: Annotation`).
- [ ] **Step 2:** Add the models, the two helpers, the path and the loader.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat: Annotation records (containers, assign, typed links, texts, missed, description) and their loader (spec §5)`

### Task 3: Which frames get a call, and which boxes are targets

**Files:**
- Create: `src/scry/annotate/__init__.py` (empty for now), `src/scry/annotate/targets.py`,
  `tests/test_annotate_targets.py`

**Interfaces:**
- Consumes: `FrameBoxes`, `Change`, `Lifetime`, `parse_box_ref` (IA1, IA3, IA4).
- Produces:
  - `@dataclass(frozen=True) CallPlan`: `frame: int`, `targets: tuple[str, ...]` (box ids, reading order), `head: bool`
  - `plan_calls(frames: list[FrameBoxes], changes: list[Change], lifetimes: list[Lifetime], mode: Literal["every_frame",
    "incremental"]) -> list[CallPlan]`
  - `chains(plans: list[CallPlan]) -> list[list[CallPlan]]`

**Rules (pure functions: no model, no I/O; spec §2, §5 "targets", §9 P0):**
1. `every_frame`: one `CallPlan` per `FrameBoxes`, in frame order, `targets` = every box id, `head = True`. `changes`
   and `lifetimes` are not read.
2. `incremental`, which frames: the first frame always. A later frame *b* gets a call when the change with `to_frame ==
   b` has `pixels is None` or `pixels.components > 0`; otherwise it gets none (§2: "a transition with no changed pixel
   makes no call"). No change record into a frame that is not the first → `ValueError("changes.jsonl has no transition
   into frame <b>")`. Transition kinds are not consulted (D5).
3. `incremental`, which boxes: let *p* be the previous frame that got a call, −1 for the first call. The targets of a
   call at frame *f* are the boxes of *f* whose lifetime's `first.frame > p`, in reading order (D4). So a box first
   seen on a frame without a call is a target of the next call, a box that continues a lifetime already asked about
   never is, and a failed call changes nothing here. A box of *f* in no lifetime → `ValueError` naming its ref.
4. `head` is true when every box of the frame is a target (true for a frame with no boxes). "The first frame and a cut
   are the same rule with every box new" (§2): no threshold appears anywhere.
5. `chains` splits the plans, kept in frame order, before every head. A plan list that does not start with a head →
   `ValueError`. Under rule 3 no lifetime crosses a head, so nothing in one chain depends on another (D6).
6. No frames → `[]`.

**Tests to write first** (Fixture P, defined here: frames 0–3; boxes 0: `b1 "A"`, `b2 "B"`; 1: `b1 "A"`, `b2 "B"`,
`b3 "F"`; 2: `b1 "A"`, `b2 "B2"`, `b3 "C"`, `b4 "F"`; 3: `b1 "Z"`; any rectangles in id order. Changes `T1` 0→1
components 0, `T2` 1→2 components 2, `T3` 2→3 components 1. Lifetimes `L1 "A" [0:b1, 1:b1, 2:b1]`, `L2 "B" [0:b2,
1:b2]`, `L3 "F" [1:b3, 2:b4]`, `L4 "B2" [2:b2]`, `L5 "C" [2:b3]`, `L6 "Z" [3:b1]`):
- `test_incremental_plan`: → `[CallPlan(0, ("b1", "b2"), True), CallPlan(2, ("b2", "b3", "b4"), False),
  CallPlan(3, ("b1",), True)]`. Frame 1 has no call; `b4 "F"` of frame 2 is a target because its lifetime began on
  frame 1, after the call at frame 0.
- `test_missing_pixels_means_a_call`: `T1.pixels = None` → calls at 0, 1, 2, 3 with targets `("b1", "b2")`, `("b3",)`,
  `("b2", "b3")`, `("b1",)`.
- `test_every_frame_plan`: four plans, each with all of its frame's ids and `head True`, with `changes=[]` and
  `lifetimes=[]`.
- `test_chains`: for `test_incremental_plan`'s result the frames per chain are `[[0, 2], [3]]`; for the every-frame
  plans `[[0], [1], [2], [3]]`.
- `test_fixture_t_plan`: Fixture T, incremental → `[CallPlan(10, ("b1", "b2", "b3", "b4"), True), CallPlan(11, ("b1",
  "b5"), False)]`; frame 12 (`components 0`) has no call.
- `test_contract_violations_raise`: dropping `T2` → `ValueError` matching `frame 2`; dropping `L5` → `ValueError`
  matching `2:b3`.
- `test_empty_and_boxless`: `plan_calls([], [], [], "incremental") == []`; a single frame with no boxes →
  `[CallPlan(0, (), True)]`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_targets.py -q`. Expected: FAIL (`No module
  named scry.annotate`).
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): call frames, targets and chains as a pure function of track's records (spec §2)`

### Task 4: The overlay in the new vocabulary

**Files:**
- Modify: `src/scry/overlay.py`, `src/scry/config.py` (`OverlayConfig`), `tests/test_overlay.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `Box`, `OverlayConfig`, `place_label`, `scale_image` (IA7).
- Produces:
  - `OverlayConfig`: exactly `font_size: int = 12  # px, not scaled with the image` and `font_path: str`.
  - `draw_overlay(png_in: Path, boxes: list[Box], png_out: Path, cfg: OverlayConfig, scale: float = 1.0) -> int`
    (returns the number of label clashes). `place_label` and `scale_image` keep their signatures.

**Rules (design §8.2 as amended by L29; spec §6 arms A and B):**
1. Every box gets a 1-px outline in `(255, 0, 255)` and a tag: the digits of its id (`"b17"` → `"17"`) in black at
   `cfg.font_size` on an opaque `(255, 255, 0)` rectangle with 2-px padding. `cfg.font_path` that cannot be opened
   falls back to `ImageFont.load_default(size)`, as today.
2. Placement is today's rule unchanged: try right of the box (`x1 + 2`, vertically centred), the left gutter
   (`x0 − label_w − 2`), above (`x0`, `y0 − label_h − 1`), below (`x0`, `y1 + 1`), each clamped into the image; take the
   first slot whose rectangle intersects no box, its own included; if none is free take the least-overlapping slot,
   the earliest among equals, and count a clash.
3. `scale < 1`: the frame is resized by `scale_image` (LANCZOS) and each rectangle is scaled outward (floor the
   near edges, ceil the far ones); the tag font is not scaled (L33: tags stay legible when the UI text does not). The
   output has exactly the scaled frame's dimensions: no border, no padding.
4. `mask_image`, `_fit_text`, `MASK_FILL`, `RENDER_BG`, `RENDER_FG`, `RENDER_MIN_PT` and the `opaque_label` branch are
   deleted, with `OverlayConfig.mask` and `OverlayConfig.scale` (D20).
5. Docstrings and comments say box, never line or mark (§3).

**Tests to write first (`tests/test_overlay.py`; the four placement and tag tests that exist keep their expected
values):**
- Keep: `test_place_label_prefers_right_then_left_then_above_then_below` (`(202, 53, False)`, `(84, 53, False)`,
  `(100, 39, False)`, then a clash), `test_place_label_never_leaves_the_image`, `test_draw_overlay_keeps_dimensions`,
  `test_labels_are_opaque_high_contrast_tags`.
- Adapt: `test_draw_overlay_scale_halves_the_image_and_boxes_but_not_the_tags` passes `scale=0.5` as the argument:
  box `b7 (10,11,121,29)` on 320×120 → output 160×60, outline pixels at `(5, 5)` and `(60, 14)` are `(255, 0, 255)`,
  `(30, 10)` is the background, and the tag is as many pixel rows tall as at full size.
- Delete: `test_overlay_scale_is_bounded`, the four `test_mask_*` tests, `test_overlay_mask_is_validated`.
- New `test_overlay_of_a_frame_without_boxes_is_the_frame`: a 64×32 frame of `(9, 9, 9)` and `boxes=[]` → returns 0;
  the output is 64×32 and every pixel is `(9, 9, 9)`.
- New `test_tag_width_grows_with_the_number`: `b7` and `b117`, each alone at `(10,10,120,28)` on a 320×120 grey frame:
  the count of pixel columns in `x ∈ [122, 170)` holding a `(255, 255, 0)` pixel is larger for `b117`.
- New `test_mask_code_is_gone`: `scry.overlay` has no attribute `mask_image`.
- `tests/test_config.py::test_overlay_config_is_font_only`: `set(OverlayConfig().model_dump()) == {"font_size",
  "font_path"}`; `OverlayConfig(scale=0.5)` and `OverlayConfig(mask="opaque")` raise `pydantic.ValidationError`.

- [ ] **Step 1:** Write and adapt the tests. Run `uv run pytest tests/test_overlay.py tests/test_config.py -q`.
  Expected: FAIL (`draw_overlay() got an unexpected keyword argument 'scale'`).
- [ ] **Step 2:** Apply rules 1–5.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `grep -n "mask\|OcrLine\|mark" src/scry/overlay.py` prints nothing.
- [ ] **Step 4:** Commit: `refactor(overlay): boxes and tags only; scale is an argument; mask modes removed (L29, L40)`

### Task 5: The contract with the model, arm A: schema, prompt, version

**Files:**
- Create: `src/scry/annotate/output.py`, `src/scry/prompts/__init__.py` (empty; IA8), `src/scry/prompts/annotate.py`,
  `tests/test_annotate_output.py`, `tests/test_annotate_prompt.py`

**Interfaces:**
- Consumes: `scry.providers.batch.strict_schema` (tests only).
- Produces:
  - `output_model(arm: str = "A", transcribe: bool = True, pane: bool = False) -> type[BaseModel]`, memoised so that
    equal arguments return the same class. Until Task 12 any arm but `"A"` raises `ValueError`; until Task 15
    `pane=True` raises `ValueError`.
  - Component models, every field required, none with a default (D2):

```
OutContainer  id: str · kind: Literal["window", "popup"] · app: str · name: str · owner: str | None · covers: list[str]
OutAssign     box: str · container: str
OutRun        boxes: list[str] · joiner: Literal["", " "]
OutPair       key: list[str] · value: list[str]
OutRecord     members: list[list[str]] · header: list[str]
OutText       box: str · text: str
OutMissed     text: str · container: str | None
AnnotateOutAT (arm A, transcribing)  containers: list[OutContainer] · assign: list[OutAssign] · unassigned: list[str] ·
              runs: list[OutRun] · pairs: list[OutPair] · records: list[OutRecord] · texts: list[OutText] ·
              missed: list[OutMissed] · description: str            (fields in this order)
AnnotateOutAG (arm A, group-only)    the same without texts and missed
```

  - In `scry.prompts.annotate`: `VERSION = "annotate-v1"`; `system_prompt(arm: str = "A", transcribe: bool = True,
    pane: bool = False, incremental: bool = False) -> str`; `prompt_version(arm: str = "A", transcribe: bool = True,
    pane: bool = False, incremental: bool = False, scale: float = 1.0) -> str`.

**Field descriptions** (they travel in the JSON schema, so they are prompt text): `OutContainer.id` "Container id: c1,
c2, … unique in this answer."; `kind` "window = top-level application window; popup = menu, dialog, tooltip, toast:
anything drawn over a window."; `app` "Application the container belongs to, e.g. 'PowerShell', 'Browser', 'VS
Code'."; `name` "The container's title as shown, or a short human name, e.g. 'Save dialog', 'tooltip: Cloud Shell'.";
`owner` "For a popup, the id of the window it belongs to, or null. Always null for a window."; `covers` "Ids of the
containers this one is drawn over, in whole or in part."; `OutAssign.box` "A target box id, e.g. 'b7'."; `container`
"Id of the container the box belongs to."; `unassigned` "Target box ids that belong to no container."; `OutRun.boxes`
"Box ids in reading order."; `joiner` "'' when a word was cut in two, ' ' otherwise."; `OutPair.key` "Box ids of the
label."; `value` "Box ids of its value."; `OutRecord.members` "The row's cells, left to right, each a list of box
ids."; `header` "Box ids of the column headings when they are visible, otherwise []."; `OutText.text` "Verbatim text
inside the box; '' for an icon."; `OutMissed.text` "Verbatim text that no box covers."; `OutMissed.container` "Id of
its container, or null."; `description` "What the boxes cannot express about this screen, in plain prose."

**The system prompt for arm A, transcribing, every frame (`annotate-v1`), in full.** Seven paragraphs separated by
one blank line. It is spec §6's draft with three changes that the schema forces: links are three lists (D2), the
header exception is stated (D13), and the images paragraph keeps today's live-tested sentence about which image to
read and introduces the word "target".

```
You label screenshots of computer tutorials (terminals, code editors, browsers, dialogs).

You are shown the same screenshot twice. Image 1 is the clean frame. Image 2 is the same frame with a numbered box around every piece of text an OCR engine detected; each number sits beside its box and is NOT part of the screen. A number is written as a box id: b1, b2, ... Read the screen from Image 1; use Image 2 only to know which number refers to which text. The user message lists the box ids and names the targets: the boxes you are asked to label.

containers: the windows (top-level application windows) and popups (menus, dialogs, tooltips, toasts) on screen. Containers do not nest. Anything drawn over a window is its own popup, never part of what it covers; a popup may name the window it belongs to as owner. Give each container an id (c1, c2, ...), its application and name, and the containers it covers.

assign: for every target box id, the container it belongs to. Every target appears exactly once, or in unassigned.

links: relations between boxes of one container, given as three lists. A box belongs to at most one run, pair or record; column headings are the exception and may be named by every record of their table.
  runs: boxes that are one continuous piece of text which the OCR engine split or the screen wrapped onto the next line, in reading order. joiner is "" when a word was cut in two by the wrap, " " otherwise.
  pairs: a label and its value (a property and its value, a form field and its content). key and value are lists of box ids. A two-column grid of labels and values is pairs, not records.
  records: one row of a table with three or more columns: members, left to right, each a list of box ids; header, the box ids of the column headings when they are visible, otherwise [].
Boxes that merely sit side by side stand alone: tabs, toolbar buttons, menu items, breadcrumbs.

texts: for every target box id, the verbatim text inside that box, read from Image 1. Preserve case, punctuation, whitespace and symbols. Never correct, complete or normalize commands, code, paths or identifiers. Use ? for a character you cannot resolve. An icon is not text: give "". missed: text no box covers, with its container.

description: what the boxes cannot express about this screen: selections, highlights, toggles, checked boxes, icons, diagrams and their relationships, dialogs, progress indicators, anything animating. Plain prose.
```

**Group-only variant (`annotate-v1+grouponly`):** paragraph 6 is replaced by the single sentence
`Do not transcribe any text: the OCR reading of each box is used.` Every other paragraph is identical. The description
paragraph stays in both: the owner keeps the description (spec §6, 2026-09-21).

**Rules:**
1. `output_model` builds each class once (for example with `pydantic.create_model`), named `AnnotateOut` + arm + `T` or
   `G` (+ `P` with a pane, Task 15), so each variant has its own JSON-schema title and with it its own schema hash in
   the call-cache key.
2. The schema must survive the SDK's strict transform unchanged in meaning (D2): no `prefixItems`, no `oneOf`, no
   `discriminator`, no `default` anywhere; every object lists all its properties in `required`.
3. `system_prompt` joins named paragraphs with `"\n\n"`; variants swap or insert whole paragraphs and never edit
   inside a shared one, so a test can pin what differs. Until Task 16 `incremental=True` raises `ValueError`.
4. `prompt_version = VERSION + ("" if arm == "A" else "+" + arm) + ("" if transcribe else "+grouponly") + ("+pane" if
   pane else "") + ("+inc" if incremental else "") + ("" if scale == 1.0 else f"+s{scale:g}")` (D22; the scale is here
   because the clean frame is scaled in memory and its file hash does not change, as today).
5. No prompt contains the substrings `mark`, `region`, `vlm_lines` or `focus` (§3; focus is not a deliverable, §0).

**Tests to write first:**
- `test_annotate_output.py::test_fields_of_arm_a`: `list(output_model("A", True).model_fields) == ["containers",
  "assign", "unassigned", "runs", "pairs", "records", "texts", "missed", "description"]`; the group-only model has the
  same list without `texts` and `missed`.
- `::test_schema_is_strict_friendly`: for both models, walking `model_json_schema()`: no key named `prefixItems`,
  `oneOf`, `discriminator` or `default` occurs; every node with `"type": "object"` has `set(required) ==
  set(properties)`; `strict_schema(model)` returns and every object node in it has `additionalProperties is False`;
  the `joiner` property's `enum == ["", " "]`; `owner` is `anyOf` string and null.
- `::test_models_are_memoised_and_named`: `output_model("A", True) is output_model("A", True)`; the two class names
  are `AnnotateOutAT` and `AnnotateOutAG`; `output_model("B")` and `output_model("A", True, True)` raise `ValueError`.
- `::test_answer_round_trip`: `AnnotateOutAT.model_validate` of a dict with one container, two assigns, one pair,
  two texts (one `""`), one missed with `container None` and a description succeeds; omitting `unassigned` raises
  `pydantic.ValidationError` (every field is required).
- `test_annotate_prompt.py::test_arm_a_paragraphs`: `system_prompt().split("\n\n")` has 7 items starting `"You label
  "`, `"You are shown the same screenshot twice."`, `"containers:"`, `"assign:"`, `"links:"`, `"texts:"`,
  `"description:"`; paragraph 5 contains `"  runs:"`, `"  pairs:"`, `"  records:"` and ends with `"breadcrumbs."`.
- `::test_group_only_differs_in_one_paragraph`: the two prompts have 7 paragraphs each and differ only at index 5,
  where group-only reads exactly `Do not transcribe any text: the OCR reading of each box is used.`; `"description:"`
  is in both.
- `::test_versions`: `prompt_version() == "annotate-v1"`; `prompt_version(transcribe=False) ==
  "annotate-v1+grouponly"`; `prompt_version(scale=0.5) == "annotate-v1+s0.5"`; `prompt_version(transcribe=False,
  scale=0.67) == "annotate-v1+grouponly+s0.67"`.
- `::test_old_vocabulary_is_absent`: neither prompt contains `mark`, `region`, `vlm_lines` or `focus`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_output.py tests/test_annotate_prompt.py -q`.
  Expected: FAIL (`No module named scry.annotate.output`).
- [ ] **Step 2:** Write the two modules: the models with the descriptions above, the paragraphs copied character for
  character from this task.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): arm A output schema and system prompt, transcribing and group-only (spec §6)`

### Task 6: The user turn, arm A

**Files:**
- Create: `src/scry/annotate/blocks.py`, `tests/test_annotate_blocks.py`

**Interfaces:**
- Consumes: `Frame`, `FrameBoxes`, `CallPlan` (Task 3), `scale_image` (Task 4), `image_block`, `text_block`
  (`scry.providers`), `sha256_file`, `sha256_obj` (`scry.jsonl`).
- Produces:
  - `frame_block(frame_png: Path, scale: float) -> dict`
  - `build_blocks(frame: Frame, fb: FrameBoxes, plan: CallPlan, arm: str, scale: float, frame_png: Path,
    overlay_png: Path | None) -> list[dict]` (Task 12 adds the other arms, Task 16 a `context` argument)
  - `input_hashes(frame: Frame, overlay_png: Path | None, blocks: list[dict]) -> list[str]`

**Rules (spec §6; D7, D8, D22, D24):**
1. `frame_block`: at `scale == 1.0` the PNG file as it is (`image_block`); otherwise the frame opened, converted to
   RGB, resized by `scale_image` and encoded as PNG (`compress_level=1`) in memory; nothing is written to disk.
2. Arm A blocks, in this order, each text exactly as written:
   1. `Image 1 (clean frame {frame.frame}, t={frame.t_settled:.2f}s):`
   2. the clean frame (`frame_block`)
   3. `Image 2 (same frame with numbered boxes):`
   4. the overlay file (`image_block(overlay_png)`)
   5. `Boxes: b1, b2, b3.` — every id of the frame in reading order; `Boxes: none.` for a frame without boxes
   6. `Targets: all boxes.` when the plan's targets are every box of a frame that has boxes; `Targets: none.` when
      there are no targets; otherwise `Targets: b2, b5.`
   7. only if some box has `in_churn`: `Boxes inside animating areas (low confidence): b7, b9.`
   8. only if `not frame.settled`: `This frame was captured while the screen was still changing (not settled).`
   9. `Return the JSON object.`
3. No OCR text appears in any block (D8).
4. `input_hashes = [frame.sha256, sha256_file(overlay_png) if overlay_png else "-", sha256_obj([b["text"] for b in
   blocks if b["type"] == "text"])]`: every byte of the user turn is covered by the frame's hash, the overlay's hash,
   the text, or the scale in the prompt version (D22).
5. Any arm but `"A"` raises `ValueError` until Task 12.

**Tests to write first** (Fixture E, frame 0; PNGs made in the test, the "overlay" file any 128×64 PNG):
- `test_arm_a_blocks`: block types are `[text, image, text, image, text, text, text]`; the texts are `"Image 1 (clean
  frame 0, t=0.00s):"`, `"Image 2 (same frame with numbered boxes):"`, `"Boxes: b1, b2."`, `"Targets: all boxes."`,
  `"Return the JSON object."`.
- `test_partial_targets_churn_and_unsettled`: `plan.targets == ("b2",)`, `b1.in_churn = True`, `frame.settled = False`
  → the texts after the images are `"Boxes: b1, b2."`, `"Targets: b2."`, `"Boxes inside animating areas (low
  confidence): b1."`, `"This frame was captured while the screen was still changing (not settled)."`, `"Return the JSON
  object."`.
- `test_blocks_for_a_frame_without_boxes`: `"Boxes: none."` and `"Targets: none."`.
- `test_scale_halves_the_clean_frame_in_memory`: `scale=0.5` → the first image block decodes to 64×32; the directory
  listing is unchanged (nothing written); at `scale=1.0` the block's data equals the file's bytes, base64-encoded.
- `test_no_ocr_text_is_sent`: with box texts `"SECRET-A"` and `"SECRET-B"`, no text block contains `SECRET`.
- `test_input_hashes`: three strings; the first is `"sha-0"`; changing `plan.targets` changes only the third;
  replacing the overlay file's bytes changes only the second; `overlay_png=None` gives `"-"` second.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_blocks.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–5.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): the user turn for arm A: two images, box ids, targets; every byte hashed`

### Task 7: From the answer to a proposal, and repair

**Files:**
- Create: `src/scry/annotate/proposal.py`, `src/scry/annotate/repair.py`, `tests/test_annotate_proposal.py`,
  `tests/test_annotate_repair.py`

**Interfaces:**
- Consumes: the records of Task 2; `output_model` (Task 5); `Box`.
- Produces:
  - `@dataclass Proposal`: `containers: list[Container]`, `assign: list[Assign]`, `unassigned: list[str]`,
    `links: list[Link]` (runs, then pairs, then records, each in returned order), `texts: list[TextReading] | None`,
    `missed: list[tuple[str, str | None]]` (text, container id), `description: str`.
  - `to_proposal(arm: str, out: BaseModel, boxes: list[Box], targets: Sequence[str], frame_size: tuple[int, int],
    margin_px: int) -> tuple[Proposal, dict[str, int]]`. This task implements arm `"A"`; Task 12 routes `"D"` to the
    same path; Task 13 adds `"B"` and `"C"`. The dict holds counts raised during conversion (none for arm A).
  - `REPAIR_KEYS: tuple[str, ...]` = `("dup_container", "bad_owner", "bad_covers", "bad_rect", "unknown_box",
    "not_target", "unknown_container", "second_assignment", "unplaced", "outside", "ambiguous", "link_unsnapped",
    "link_unknown_box", "link_malformed", "link_already_linked", "link_no_target", "link_cross_container",
    "text_unknown_box", "text_not_target", "second_text", "text_missing", "text_unplaced",
    "missed_empty", "missed_unknown_container")`.
  - `@dataclass Repaired`: `containers`, `assign`, `unassigned`, `links`, `texts`, `missed: list[Missed]`,
    `counts: dict[str, int]` (non-zero keys only).
  - `repair(p: Proposal, targets: Sequence[str], frame_boxes: Sequence[str], *, known: Sequence[Container] = (),
    box_container: Mapping[str, str | None] | None = None, linked: frozenset[str] = frozenset(),
    update_known_rects: bool = False) -> Repaired`. The keyword arguments describe what an incremental call was told
    (Task 16); with their defaults the function is the every-frame repair.

**Rules.** Validation is repair, never abort (spec §6). Every dropped or altered item adds 1 to exactly one key: the
first check it fails, in the order written. `repairs` on the record is the sum of all counts.

*`to_proposal`, arm A:* a field-for-field copy: `OutContainer` → `Container` (`rect None`), `OutAssign` → `Assign` (its
`pane` when the class has one), `unassigned`, `runs` → `RunLink`, `pairs` → `PairLink`, `records` → `RecordLink`, `texts`
→ `TextReading` (or `None` when the answer class has no `texts` field), `missed` → `(text, container)` (or `[]`),
`description`.

*Containers:*
1. A container whose id equals an earlier one in the answer → dropped (`dup_container`).
2. A container whose id equals a `known` id is not a new container. With `update_known_rects` the known container
   takes the answer's `rect` and `covers`; its kind, app, name, owner and `known_as` never change (D28). Not counted.
3. The result list is `known` in the given order, then the new containers in returned order.
4. `owner` must name a different container of the result list whose kind is `window`, and only a popup may have one;
   otherwise `owner = None` (`bad_owner`).
5. Every id in `covers` that names no container of the result list, names the container itself, or repeats an earlier
   entry is removed (`bad_covers` each).

*Assign and unassigned,* entries in returned order:
6. Box not in `frame_boxes` → dropped (`unknown_box`). 7. Box not in `targets` → dropped (`not_target`). 8. Container
   not in the result list → dropped (`unknown_container`). 9. Box already assigned by a kept entry → dropped
   (`second_assignment`). A `pane` that is empty after stripping becomes `None` (not counted).
10. `unassigned` keeps, in order and once each, the ids that are targets and not assigned; others vanish uncounted.
    Then every target that is neither assigned nor listed is appended in reading order (`unplaced` each). Afterwards
    every target is in exactly one of `assign` and `unassigned` (spec §6).

*Links,* in stored order. "Members" are `link_members`, "refs" are `link_refs` (members plus a record's header; Task
2). The container of a box is its kept `assign` entry's container if it is a target, else `box_container.get(box)`:
11. A ref not in `frame_boxes` → link dropped (`link_unknown_box`).
12. Shape → `link_malformed`: a run needs at least two members; a pair needs a non-empty key and a non-empty value; a
    record's empty cells are removed first and it then needs at least two cells; no ref may occur twice in one link
    (so a key and value that OCR put in one box can never be a pair, spec §5, and a header box cannot be a cell).
13. A member that is in `linked`, or is a member of a link already kept from this answer → dropped
    (`link_already_linked`; D15).
14. No member in `targets` → dropped (`link_no_target`; D15).
15. Some ref has no container, or two refs have different containers → dropped (`link_cross_container`; D14).
16. Header ids are exempt from rule 13, do not count for rule 14 and do not become "already linked" (D13).

*Texts,* only when `p.texts` is not `None`, in returned order: 17. box not in `frame_boxes` → dropped
(`text_unknown_box`); 18. not a target → dropped (`text_not_target`); 19. a second text for a box → dropped
(`second_text`); 20. each target left without a text adds 1 to `text_missing` (nothing is invented for it).

*Missed:* 21. text empty after stripping → dropped (`missed_empty`); 22. a container not in the result list → `None`
(`missed_unknown_container`). Kept entries are numbered `m1`, `m2`, … in order. They have no rectangle, are citable as
`"<frame>:m1"` and never enter a change record (§3).

**Tests to write first:**
- `test_annotate_proposal.py::test_arm_a_copy`: an `AnnotateOutAT` answer with one container, two assigns, one run, one
  pair, one record, two texts, one missed → a `Proposal` whose `links` kinds are `["run", "pair", "record"]`, `texts ==
  [TextReading(box="b1", text="a"), TextReading(box="b2", text="")]`, `missed == [("Networking", "c1")]`, counts `{}`;
  an `AnnotateOutAG` answer → `texts is None`, `missed == []`.
- `test_annotate_repair.py::test_repair_containers`: targets and frame boxes `["b1"]`; containers in order: `c1` window
  covers `["c2", "c1", "zz"]`; `c2` popup owner `"c9"`; `c2` window (a duplicate id); `c3` window owner `"c1"`; `c4`
  popup owner `"c2"`; `c5` popup owner `"c1"`; assign `b1→c5` → container ids `["c1", "c2", "c3", "c4", "c5"]`, owners
  `[None, None, None, None, "c1"]`, `c1.covers == ["c2"]`, counts `{"dup_container": 1, "bad_owner": 3, "bad_covers":
  2}`.
- `::test_repair_assign`: targets `b1`–`b6`, frame boxes `b1`–`b7`, windows `c1`, `c2`; assign in order `b1→c1`,
  `b2→c1`, `b2→c2`, `b9→c1`, `b7→c1`, `b3→c7`, `b4→c2`; unassigned `["b5", "b1", "b8"]` → assign `[b1→c1, b2→c1,
  b4→c2]`, unassigned `["b5", "b3", "b6"]`, counts `{"unknown_box": 1, "not_target": 1, "unknown_container": 1,
  "second_assignment": 1, "unplaced": 2}`.
- `::test_repair_links`: targets = frame boxes = `b1`–`b8`; assign `b1, b2, b3, b7 → c1`, `b4, b5, b6 → c2`,
  unassigned `["b8"]`; runs `[b4, b5] " "`, `[b5, b6] ""`, `[b1]`, `[b1, b99]`, `[b6, b6]`; pairs `key [b1] value
  [b2]`, `key [b3] value [b6]`, `key [b7] value [b8]`, `key [b3] value [b3]` → links `[RunLink(boxes=["b4", "b5"],
  joiner=" "), PairLink(key=["b1"], value=["b2"])]`, counts `{"link_already_linked": 1, "link_malformed": 3,
  "link_unknown_box": 1, "link_cross_container": 2}`.
- `::test_repair_records_and_headers`: targets = frame boxes = `b1`–`b18`, all in `c1` except `b9` in `c2`; records
  in order: `[[b4], [b5], [b6]]` header `[b1, b2, b3]`; `[[b7], [b8]]` header `[b1, b2, b3]`; `[[b4], [b7]]`;
  `[[b10], [b11]]` header `[b1, b99]`; `[[b12], [], [b13]]`; `[[b14]]`; `[[b15], [b16]]` header `[b9]`; `[[b17],
  [b18]]` header `[b17]` → three records kept, in order: the first two with header `["b1", "b2", "b3"]` (the shared
  header is not "already linked"), then members `[["b12"], ["b13"]]` with header `[]`; counts `{"link_already_linked":
  1, "link_unknown_box": 1, "link_malformed": 2, "link_cross_container": 1}` (the third record; the `b99` header; the
  one-cell record and the header that is also a cell; the header in `c2`).
- `::test_repair_texts_and_missed`: targets `b1`–`b3`, frame boxes `b1`–`b4`, container `c1`, all assigned; texts
  `b1 "x"`, `b1 "y"`, `b9 "z"`, `b4 "w"`, `b2 ""`; missed `("Networking", "c1")`, `("  ", None)`, `("Help", "c9")` →
  texts `[b1 "x", b2 ""]`; missed `[Missed(id="m1", text="Networking", container="c1"), Missed(id="m2", text="Help",
  container=None)]`; counts `{"second_text": 1, "text_unknown_box": 1, "text_not_target": 1, "text_missing": 1,
  "missed_empty": 1, "missed_unknown_container": 1}`. With `p.texts = None` → `texts is None` and no `text_missing`.
- `::test_repair_with_known_context`: frame boxes `b1`–`b6`, targets `["b1"]`, `known = [Container(id="c1",
  kind="window", app="A", name="W", known_as="5:c1")]`, `box_container = {"b2": "c1", "b3": "c1", "b4": "c1", "b5":
  None, "b6": "c1"}`, `linked = frozenset({"b3"})`; answer containers `c1` popup "echo" rect `(0,0,10,10)` covers
  `["c2"]`, and `c2` popup "new" owner `"c1"`; assign `b1→c1`; runs `[b4, b6] " "`, `[b1, b3] ""`; pairs `key [b1]
  value [b2]` → containers `[c1 (window, "W", known_as "5:c1", rect None, covers []), c2 (popup, owner "c1")]`; assign
  `[b1→c1]`; links `[PairLink(key=["b1"], value=["b2"])]`; counts `{"link_no_target": 1, "link_already_linked": 1}`.
  The same with `update_known_rects=True` → `c1.rect == (0, 0, 10, 10)`, `c1.covers == ["c2"]`, `c1.name == "W"`.
- `::test_every_target_ends_up_exactly_once`: for each case above, `sorted(a.box for a in assign) + sorted(unassigned)`
  is a permutation of `targets`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_proposal.py tests/test_annotate_repair.py -q`.
  Expected: FAIL (`No module named scry.annotate.repair`).
- [ ] **Step 2:** Implement `to_proposal` for arm A and rules 1–22.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): proposals and repair: every bad label is dropped and counted, never fatal (spec §6)`

### Task 8: The provider, exactly what changes

Read against `src/scry/providers/` as it stands. **Unchanged and reused as they are:** `VlmProvider.complete(stage,
system, blocks, output_model, effort, prompt_version, input_hashes)`; structured output through the SDK's parse helper
(`client.messages.parse(…, output_format=<pydantic class>, output_config={"effort": …})`); the system prompt sent as one
text block with `cache_control: {"type": "ephemeral"}`; one retry at `retry_max_tokens` when `stop_reason ==
"max_tokens"`; one retry with the validation error quoted when the answer fails the schema; refusals recorded, not
raised; API errors recorded and not cached; `CallCache.key(stage, model, effort, max_tokens, prompt_version,
schema_hash, input_hashes)`; the batch path (`collecting`, `PendingRequest`, `strict_schema`, `BatchRunner`). No
`thinking` parameter is sent: on `claude-opus-5` that means adaptive thinking, bounded by `effort` (L13). `annotate`
calls `complete` with `stage="annotate"` and `effort=cfg.model.effort_annotate`.

**What changes** is accounting and one re-homed helper. They are the same changes plan 3's Tasks 1, 3 and 7 describe
(IA8); whichever plan lands first makes them, with these values.

**Files:**
- Create: `tests/fakes.py`
- Modify: `src/scry/providers/anthropic_.py`, `src/scry/providers/batch.py`, `src/scry/costs.py`,
  `tests/test_provider.py`, `tests/test_batch.py`, `tests/test_costs.py`

**Interfaces:**
- Produces, in `scry.costs`: `USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens",
  "cache_creation_input_tokens")`; `CACHE_WRITE_MULTIPLIER = 1.25`; `BATCH_MULTIPLIER = 0.5`; `add_usage(total: dict,
  usage: dict) -> dict`; `estimate_cost(usage: dict, model: str, batch: bool = False) -> float`.
- Produces, in `scry.providers.batch`: `async run_with_batches(run: Run, cfg: Config, provider, stage_fn) -> list`.
- Produces, in `tests/fakes.py`: `FakeMessages(script)` and `fake_client(script)`, moved from `tests/test_provider.py`
  unchanged except that a script item may carry `"usage": {…}` (absent: `input_tokens 10, output_tokens 5`, both cache
  counts 0); `USAGE = {"input_tokens": 100, "output_tokens": 20, "cache_read_input_tokens": 1000,
  "cache_creation_input_tokens": 400}`; `class AnswerProvider(answer: Callable[[dict], BaseModel | str])` with `model =
  "fake-model"`, `calls: list[dict]`, `stats = {"hits": 0, "misses": 0}`, whose `complete(**kw)` records `kw`, calls
  `answer(kw)` and returns `VlmResult(parsed, None, dict(USAGE))` for a model or `VlmResult(None, error, dict(USAGE))`
  for a string; `call_frame(kw: dict) -> int`, the number after the word `frame` in the call's first text block.

**Rules:**
1. `estimate_cost = (input × p_in + output × p_out + cache_read × p_cache + cache_creation × p_in × 1.25) / 1e6`, times
   0.5 when `batch`, rounded to 4 places; an unknown model uses the `claude-opus-5` prices, as today. The provider asks
   for the default five-minute cache, whose writes cost 1.25 × the input price; today's function drops them (open item
   "Usage accounting"; principle 9).
2. `add_usage` adds the four keys (absent or `None` counts 0) into `total` and returns it.
3. `AnthropicProvider.complete` returns, accounts (`usage_by_stage`) and caches the **sum** of the usage of every
   `_call` it made for the request. Today a `max_tokens` retry and a schema retry replace the first attempt's result,
   so a billed attempt of up to 16,000 output tokens disappears from the record.
4. `BatchRunner.run_pending` records all four usage keys of a succeeded result (today it omits
   `cache_creation_input_tokens`).
5. `run_with_batches` is the tag's `perceive._run_with_batches`: one event loop for the stage; with `cfg.model.mode ==
   "batch"` and a provider that has `collecting`, run `stage_fn(run, cfg, provider)` once collecting, `await
   provider.run_batches(run)`, then run `stage_fn` again (all cache hits) and return that result; otherwise run it once.
   Afterwards, when `provider` has a `client` with an awaitable `close`, await it inside the loop (open item: "Event
   loop is closed" tracebacks).

**Tests to write first:**
- `tests/test_costs.py::test_estimate_cost_prices_cache_writes`: `{"input_tokens": 1_000_000, "output_tokens": 100_000,
  "cache_read_input_tokens": 2_000_000, "cache_creation_input_tokens": 1_000_000}` with `"claude-opus-5"` → `14.75`
  (5 + 2.5 + 1 + 6.25); with `batch=True` → `7.375`; `dict(USAGE)` with `"fake-model"` → `0.004`. The existing
  `test_estimate_cost` (`7.5`) still passes.
- `::test_add_usage`: `add_usage({"input_tokens": 1}, {"input_tokens": 2, "cache_creation_input_tokens": None,
  "output_tokens": 3})` → `{"input_tokens": 3, "output_tokens": 3, "cache_read_input_tokens": 0,
  "cache_creation_input_tokens": 0}`.
- `tests/test_provider.py::test_usage_sums_over_retries`: script `[{"parsed": None, "stop": "max_tokens"}, {"parsed":
  Out(answer="b"), "usage": {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 0,
  "cache_creation_input_tokens": 7}}]` → `r.usage == {"input_tokens": 20, "output_tokens": 10,
  "cache_read_input_tokens": 0, "cache_creation_input_tokens": 7}`; `p.usage_by_stage["s"]` equals it; a second
  identical `complete` is a cache hit with the same usage. `tests/test_provider.py` imports the fakes from
  `tests.fakes`; its five existing tests keep their expectations.
- `tests/test_batch.py::test_batch_results_keep_cache_creation_tokens`: a fake batches client (`create` returns an
  object with `id "B1"`; `retrieve` returns `processing_status "ended"`; `results` returns an async iterator of one
  succeeded result whose message has the text `{"answer": "a"}`, `stop_reason "end_turn"` and usage 10, 5, 3, 7).
  After `BatchRunner(client, CallCache(tmp_path / "c"), Run(tmp_path / "r"), poll_s=0).run_pending([PendingRequest("k",
  {}, Out, "s")])` the cache entry `k` has `response.usage == {"input_tokens": 10, "output_tokens": 5,
  "cache_read_input_tokens": 3, "cache_creation_input_tokens": 7}` and `response.parsed == {"answer": "a"}`.
- `::test_run_with_batches_runs_twice_in_batch_mode`: a fake provider with `collecting = False`, `run_batches`
  recording a call, and a `stage_fn` recording `provider.collecting` at each run → with `mode="batch"` the recorded
  values are `[True, False]` and `run_batches` ran once between them; with `mode="sync"` → `[False]`.

- [ ] **Step 1:** Write `tests/fakes.py` and the tests. Run `uv run pytest tests/test_costs.py tests/test_provider.py
  tests/test_batch.py -q`. Expected: FAIL (`14.75 != 8.5`, `ImportError: add_usage`).
- [ ] **Step 2:** Implement rules 1–5.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `fix(providers): price cache-creation tokens, sum usage over retries and batch results; run_with_batches`

### Task 9: The `annotate` stage, every frame, and `scry annotate`

**Files:**
- Create: `src/scry/annotate/stage.py`, `tests/test_annotate_stage.py`
- Modify: `src/scry/annotate/__init__.py` (exports `run_annotate`), `src/scry/cli.py`

**Interfaces:**
- Consumes: Tasks 1–8; `get_provider`, `VlmProvider`; `config_hash`; `margin_px` (IA5).
- Produces: `run_annotate(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None`, writing
  `annotations.jsonl` and `overlays/NNNNN.png`; CLI `scry annotate RUN_DIR [--config PATH] [--verbose]`; `STAGES ==
  ["outline", "decode", "read", "track", "annotate"]` and `scry run` runs `annotate` after `track` (manifest key
  `annotate`).

**Rules:**
1. `mode == "off"` (the "no annotation" base, §2, §9 P1): delete `annotations.jsonl` if it exists (D25), write the
   manifest entry with `skipped = True`, `frames` = the number of emitted frames, `calls = 0`, `usage` = four zeros,
   `model = cfg.model.model`, and return. No provider is created and nothing is drawn.
2. Inputs `[run.frames, run.boxes]`; config hash `config_hash(cfg, "annotate", "model", "overlay", "track")` +
   `prompt_version(…)`. Up to date and `annotations.jsonl` present → return.
3. Frames in `frames.jsonl` order; a frame without a `boxes.jsonl` record → `ValueError("… run `scry read` first")`.
   Plans from `plan_calls(frame_boxes, [], [], "every_frame")` (Task 16 adds the incremental branch).
4. Per plan: a frame whose PNG does not exist yields `Annotation(error="missing_png")` with no call. Otherwise draw
   `overlays/<frame:05d>.png` with `draw_overlay(…, scale=cfg.annotate.scale)` (every box numbered, D7), build the
   blocks (Task 6) and call `provider.complete(stage="annotate", system=system_prompt(…), blocks=…,
   output_model=output_model(…), effort=cfg.model.effort_annotate, prompt_version=…, input_hashes=…)`.
5. A parsed answer goes `to_proposal` → `repair` → `Annotation(frame, targets, **repaired, description=…,
   repairs=sum(counts), repair_counts=counts, label_clashes=…, model=provider.model, prompt_version=…, usage=…)`, where
   the counts of `to_proposal` and `repair` are added together. `margin_px = margin_px(boxes, [], cfg.track.margin)`.
6. `res.parsed is None` → `Annotation(frame, targets, error=res.error, usage=res.usage, …)` with empty lists,
   `texts None`, `description None`; the run continues.
7. At most `cfg.model.concurrency × 2` frames in flight (image payloads are built inside the bound, as today); the
   whole stage runs under `run_with_batches`, so `[model] mode = "batch"` works unchanged for every-frame annotation.
8. Records sorted by frame, written with `write_jsonl`. The stage reads no other stage's output but `frames.jsonl` and
   `boxes.jsonl`, and writes no file but its own and its overlays.
9. Manifest `stages.annotate`: `mode`, `arm` (`"A"` until Task 12), `transcribe`, `prompt_version`, `model`, `frames`
   (emitted frames), `calls` (records), `boxes` (boxes over the call frames), `targets`, `errors`, `failed_targets`
   (targets of records with an error), `repairs`, `repair_counts` (summed by key), `label_clashes`, `usage` (the four
   keys, `add_usage` over the records, so cache hits count: the cost is what a cold run would pay, D23), `cache`
   (`provider.stats`), `cost_usd = estimate_cost(usage, model)`, `cost_usd_batch = estimate_cost(usage, model,
   batch=True)`, `cost_per_frame_usd` and `cost_per_frame_usd_batch` (÷ `frames`, 5 places, `None` with no frames),
   `cost_per_call_usd` (÷ `calls`, 5 places, `None` with no calls). Spec §9: "cost beside every number: dollars per
   frame". No projection to the sample's 221 frames is computed in code. Repeats for the evidence rules are separate
   run directories made with `scry subset --no-share-cache`, as in L42; there is no repeat key.

**Tests to write first** (Fixture E through `write_run`; `AnswerProvider`; the standard answer for a frame *n* is one
window `c1` (app "x", name "w", owner null, covers []), `b1→c1`, `b2→c1`, `unassigned []`, no runs, one pair `key [b1]
value [b2]`, no records, texts `b1 "a"`, `b2 "B"`, no missed, description `"d<n>"`, built with `kw["output_model"]`):
- `test_every_frame_arm_a_end_to_end`: two records; record 0 has `targets ["b1", "b2"]`, one container, two assigns,
  `links == [PairLink(key=["b1"], value=["b2"])]`, `texts == [TextReading(box="b1", text="a"), TextReading(box="b2",
  text="B")]`, `description "d0"`, `repairs 0`, `repair_counts {}`, `label_clashes 0`, `model "fake-model"`,
  `prompt_version "annotate-v1"`, `error None`; each call had `stage "annotate"`, `effort "low"`, `system ==
  system_prompt()`, `output_model is output_model("A", True)`, two image blocks; `overlays/00000.png` and
  `overlays/00001.png` exist and are 128×64; manifest `frames 2`, `calls 2`, `boxes 4`, `targets 4`, `errors 0`, `usage
  == {"input_tokens": 200, "output_tokens": 40, "cache_read_input_tokens": 2000, "cache_creation_input_tokens": 800}`,
  `cost_usd 0.008`, `cost_usd_batch 0.004`, `cost_per_frame_usd 0.004`, `cost_per_call_usd 0.004`.
- `test_group_only`: `transcribe = false` → `system == system_prompt(transcribe=False)`, `output_model is
  output_model("A", False)`, `prompt_version "annotate-v1+grouponly"`, `record.texts is None`, `record.missed == []`.
- `test_repairs_are_counted_not_fatal`: the answer assigns `b9→c1` instead of `b2→c1` → each record has `unassigned
  ["b2"]`, `repairs 3`, `repair_counts {"unknown_box": 1, "unplaced": 1, "link_cross_container": 1}` (the pair names
  the now unassigned `b2`); manifest `repairs 6`.
- `test_error_record_and_the_run_continues`: the answer for frame 1 is the string `"refusal"` → record 1 has `error
  "refusal"`, `targets ["b1", "b2"]`, `description None`, `texts None`, `links []`; record 0 is whole; manifest `errors
  1`, `failed_targets 2`.
- `test_frame_without_boxes_still_gets_a_call`: frame 1 has no boxes → its call's texts include `"Boxes: none."`; its
  record has `targets []` and the description.
- `test_missing_png_is_an_error_record_without_a_call`: delete `frames/00001.png` → one call; record 1 `error
  "missing_png"`.
- `test_scale_reaches_the_version_and_both_images`: `scale = 0.5` → `prompt_version "annotate-v1+s0.5"`; both image
  blocks decode to 64×32.
- `test_skips_when_up_to_date_and_reruns_on_config_change`: a second `run_annotate` makes no call; with `transcribe =
  false` it calls again.
- `test_mode_off_removes_the_file_and_calls_nothing`: after a normal run, `mode = "off"` → `annotations.jsonl` is gone,
  no call, manifest `stages.annotate.skipped is True` and `usage.input_tokens == 0`.
- `test_writes_only_its_own_files`: the bytes of `frames.jsonl` and `boxes.jsonl` are unchanged after the stage.
- `test_cli_annotate`: monkeypatch `scry.annotate.stage.get_provider` to return an `AnswerProvider`; `scry annotate
  <dir>` exits 0 and `annotations.jsonl` has two lines. `test_stage_list`: `scry.cli.STAGES == ["outline", "decode",
  "read", "track", "annotate"]`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_stage.py -q`. Expected: FAIL (`ImportError:
  run_annotate`).
- [ ] **Step 2:** Implement rules 1–9 and the command.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry --help` lists `annotate`.
- [ ] **Step 4:** Commit: `feat: annotate stage: one call per frame proposing containers, links, a second reading and a description; cost per frame in the manifest`

### Task 10: The joined view: labels per box and per frame

**Files:**
- Create: `src/scry/annotate/join.py`, `tests/test_annotate_join.py`
- Modify: `src/scry/run.py`

**Interfaces:**
- Consumes: `Annotation` and its parts; `FrameBoxes`, `Lifetime` (IA3); `textdiff.norm`.
- Produces (names as plan 3's A4 assumes them, IA8):

```
GLYPH_MAX_LEN = 2                                   # characters; the icon-glyph strip of `agree` (D26)
agreement(ocr: str, vlm: str, glyph_max_len: int = GLYPH_MAX_LEN) -> bool
BoxLink       kind: "run" | "pair" | "record" · role: "run" | "key" | "value" | "member" | "header" ·
              boxes: list[str] = [] · joiner: str | None = None · key: list[str] = [] · value: list[str] = [] ·
              members: list[list[str]] = [] · header: list[str] = []        (every id a box ref of the box's own frame)
BoxLabel      source: str (ref of the target box the labels were read from) · container: Container | None ·
              container_ref: str | None · pane: str | None · link: BoxLink | None · vlm: str | None ·
              agree: bool | None · non_text: bool
FrameLabel    containers: list[Container] = [] · links: list[Link] = [] (box refs of that frame) ·
              description: str | None = None · description_frame: int | None = None · missed: list[Missed] = []
Labels        box(ref: str) -> BoxLabel | None · frame(frame: int) -> FrameLabel · lifetime(id) (Task 11)
build_labels(annotations: list[Annotation], frames: list[FrameBoxes], lifetimes: list[Lifetime]) -> Labels
Run.load_labels() -> Labels | None                  # None when annotations.jsonl is absent or holds no record
mark_match(annotations: list[Annotation], frames: list[FrameBoxes], threshold: float = 0.8) -> tuple[int, int]
```

**Rules (spec §2 "loaders join labels onto measured records on read"; §5; D16).** A record is *successful* when its
`error` is `None`.
1. **Source.** The source of box *(f, b)* is *(f, b)* itself when frame *f* has a successful record with *b* among its
   targets; otherwise the latest earlier box *(g, y)* of the same lifetime, `g < f`, for which that holds; otherwise
   none, and `Labels.box` returns `None`. With `lifetimes == []` nothing is carried. A ref that is not in `frames` →
   `KeyError`.
2. **Box labels** come from the source record *g* and its box *y*: `container` is the record's container named by
   *y*'s assign entry (`None` when *y* is unassigned), `container_ref = container.known_as or f"{g}:{container.id}"`,
   `pane` from the same entry; `vlm` is *y*'s text in `texts` (`None` when the record did not transcribe or has no
   entry); `non_text = vlm is not None and vlm.strip() == ""`; `agree` is `None` when `vlm` is `None` or `non_text`,
   else `agreement(OCR text of (g, y), vlm)` — both readers read frame *g*'s pixels.
3. **`agreement`** (today's rule, D26): true when `norm(ocr) == norm(vlm)`; else, when `ocr.split()` has at least two
   tokens, true when the first token has at most `glyph_max_len` characters and `norm` of the rest equals `norm(vlm)`,
   or the same with the last token; else false. `norm` collapses whitespace and straightens quotes and nothing else, so
   `azconfigure` against `az configure` disagrees, as it must (L43).
4. **Links in force at frame *f*.** For every successful record *g ≤ f* in frame order and each of its links in stored
   order: map every id in `link_refs` to frame *f* through its lifetime (the box itself when `g == f`). The link is in
   force when every id maps and, for every member that was a target of *g*, the source of its mapped box is still that
   member in *g*. So every-frame records never pile up (at *f* every box draws from *f*'s record), and an incremental
   link lasts exactly as long as the boxes it labelled.
5. `FrameLabel.links` are the links in force with every id written as a box ref of *f*. `BoxLabel.link` is the link in
   force of which the box is a member, with its role (`run`, `key`, `value`, `member`); failing that the first link in
   force that names it in `header` (role `header`); failing that `None`.
6. **Screen-level labels.** Let *r* be the latest record with `frame ≤ f`. If there is none, or *r* failed:
   `containers []`, `description None`, `description_frame None`, `missed []`. Otherwise they are *r*'s, with
   `description_frame = r.frame`: a frame without a call shows the previous description (spec §2), and a failed call
   makes it unknown rather than stale.
7. `Run.load_labels()` imports this module lazily and builds from `load_annotations()`, `load_boxes()`,
   `load_lifetimes()`. Nothing here writes a file or alters a measured record.
8. `mark_match` (the check that caught unreadable tags, L28–L30; conditional on a second reading, §7) returns `(hits,
   total)` over the texts of successful transcribing records: a text counts when it is not empty after stripping and
   the box the model named (`named` if set, else `box`) is a box of the record's frame; it is a hit when
   `textdiff.similarity(that box's OCR text, text) ≥ threshold`. It judges the model's own reference, before any
   reassignment. The 0.8 is the design's diagnostic constant (§18.4, L30); no pipeline decision rests on it, and the
   evaluation plan reports it as a guard.

**Tests to write first** (Fixture T with records `[A10, A11]` unless stated):
- `test_own_record_and_carried_labels`: `box("10:b4")` → `source "10:b4"`, `container.id "c2"`, `container_ref
  "10:c2"`, `vlm "PS C:\> a"`, `agree False`, `non_text False`; `box("11:b2")` → `source "10:b1"`, `container.app
  "Browser"`, `container_ref "10:c1"`, `vlm "Resource group"`, `agree True`; `box("12:b5")` → `source "11:b5"`,
  `container_ref "10:c2"` (through `known_as`), `vlm "PS C:\> az login"`, `agree True`; `box("12:b1")` → `source
  "11:b1"`, `container_ref "10:c1"`.
- `test_links_in_force`: `frame(10).links == [PairLink(key=["10:b1"], value=["10:b2"])]`; `frame(11).links ==
  [PairLink(key=["11:b2"], value=["11:b3"]), RunLink(boxes=["11:b4", "11:b5"], joiner=" ")]`; `frame(12).links` is the
  same with `12:` refs; `box("12:b3").link == BoxLink(kind="pair", role="value", key=["12:b2"], value=["12:b3"])`;
  `box("12:b4").link.role == "run"`; `box("12:b1").link is None`.
- `test_a_link_ends_with_its_lifetimes`: `A10` with the extra link `run [b3, b4] ""` → `frame(10).links` has two
  links; `frame(11).links` does not contain that run (`L4` has no box on frame 11).
- `test_screen_level_labels`: `frame(10)` → description `"d10"`, `description_frame 10`, missed texts
  `["Networking"]`, container ids `["c1", "c2"]`; `frame(12)` → `"d11"`, `11`, `[]`, `["c1", "c2"]`; `frame(9)` →
  `FrameLabel()`.
- `test_failed_record_is_not_a_source`: `A11` replaced by a record of frame 11 with `targets ["b1", "b5"]` and `error
  "refusal"` → `box("11:b5") is None`, `box("12:b5") is None`, `box("11:b2").source == "10:b1"`, `frame(11).description
  is None`, `frame(12).description is None`, `frame(11).links == [PairLink(key=["11:b2"], value=["11:b3"])]`.
- `test_every_frame_records_do_not_pile_up`: records `A10` and a full `A11f` (every box of frame 11 a target;
  containers `c1`, `c2` with `known_as None`; `b1, b2, b3 → c1`, `b4, b5 → c2`; no links) → `box("11:b2").source ==
  "11:b2"`, `container_ref "11:c1"`, `frame(11).links == []`.
- `test_agreement`: `("区 Overview", "Overview")` true; `("Overview >", "Overview")` true; `("ab Overview",
  "Overview")` true; `("abc Overview", "Overview")` false; `("az configure", "azconfigure")` false; `("PS  C:\> az",
  "PS C:\> az")` true; `("“x”", '"x"')` true.
- `test_non_text_and_group_only`: a text `""` → `vlm ""`, `non_text True`, `agree None`; a record with `texts None` →
  `vlm None`, `agree None`, `non_text False`.
- `test_without_lifetimes_nothing_is_carried`: `build_labels([A10], frames, [])` → `box("11:b2") is None`,
  `box("10:b1").source == "10:b1"`.
- `test_load_labels`: a run without `annotations.jsonl` → `None`; with `[A10, A11]` written → a `Labels`;
  `box("99:b1")` raises `KeyError`.
- `test_mark_match`: `[A10, A11]` → `(6, 6)` (`"PS C:\> a"` against `"PS C:\> az"` is 0.9); with `A11`'s text for `b1`
  replaced by `"PowerShell 7"` → `(5, 6)`; with that reading stored as `TextReading(box="b4", text="PowerShell 7",
  named="b1")` → still `(5, 6)` (the named box is judged); an empty text and a group-only record count nothing.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_join.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): the joined view: labels per box and per frame, carried along lifetimes (spec §5)`

### Task 11: The joined view: labels per lifetime

**Files:**
- Modify: `src/scry/annotate/join.py`, `tests/test_annotate_join.py`

**Interfaces:**
- Produces:

```
LifetimeLink   kind: "run" | "pair" | "record" · boxes: list[str] = [] · joiner: str | None = None ·
               key: list[str] = [] · value: list[str] = [] · members: list[list[str]] = [] · header: list[str] = [] ·
               records: int · first_frame: int                          (every id a lifetime id)
LifetimeLabel  vlm: str | None · vlm_readings: dict[str, int] · agree: bool | None · non_text: bool ·
               container: Container | None · container_ref: str | None · links: list[LifetimeLink] = []
Labels.lifetime(lifetime_id: str) -> LifetimeLabel | None
```

**Rules (spec §5: "per lifetime the model's majority reading"; §6 `index`; principle 5: record, do not pick):**
1. `vlm_readings` counts, exactly as returned, the text of every box of the lifetime that was a target of a successful
   transcribing record and has a text there. Under every-frame annotation that is one reading per sighting; under
   incremental annotation usually one in all.
2. `non_text` is true when there is at least one reading and every reading is empty after stripping. `vlm` is the
   non-empty reading with the highest count, a tie going to the reading seen first in frame order (IA10), `None` when
   there is none. `agree` is `None` when `vlm` is `None`, else `agreement(lifetime.text, vlm)`: the two majority
   readings compared.
3. `container` and `container_ref` are those of the lifetime's latest labelled box.
4. Every link of every successful record is mapped to lifetime ids. Relations equal in kind, joiner and structure of
   lifetime ids are one `LifetimeLink`, with `records` = how many records proposed it and `first_frame` the first.
   Nothing is picked: a lifetime that was paired in 20 records and put in a run in 1 has both, with their counts. A
   lifetime's `links` are all those naming it, header included, ordered by `first_frame` then stored order.
5. `Labels.lifetime` returns `None` for a lifetime with no labelled box and no link; an unknown id → `KeyError`.
   How long a lifetime lasted is not read anywhere here.

**Tests to write first** (Fixture T):
- `test_lifetime_labels_incremental` (`[A10, A11]`): `lifetime("L2")` → `vlm "RG1"`, `vlm_readings {"RG1": 1}`, `agree
  True`, `non_text False`, `container.id "c1"`, `container_ref "10:c1"`, `links == [LifetimeLink(kind="pair",
  key=["L1"], value=["L2"], records=1, first_frame=10)]`; `lifetime("L4")` → `vlm "PS C:\> a"`, `agree False`;
  `lifetime("L6").links == [LifetimeLink(kind="run", boxes=["L3", "L6"], joiner=" ", records=1, first_frame=11)]` and
  `lifetime("L3").links` is equal to it; `lifetime("L5").links == []`.
- `test_majority_over_every_frame_records`: full records `A10`, `A11f`, `A12f` (`A11f` and `A12f`: every box a target,
  pair `key [b2] value [b3]`, text of `b3` `"RG1"` in `A11f` and `"RGl"` in `A12f`) → `lifetime("L2").vlm_readings ==
  {"RG1": 2, "RGl": 1}`, `vlm "RG1"`, `agree True`, `links[0].records == 3`, `links[0].first_frame == 10`.
- `test_tie_goes_to_the_reading_seen_first`: readings `"x"` on frame 10 and `"y"` on frame 11 → `vlm "x"`.
- `test_non_text_needs_every_reading_empty`: readings `""`, `""` → `non_text True`, `vlm None`, `agree None`; readings
  `""`, `"X"` → `non_text False`, `vlm "X"`.
- `test_unlabelled_lifetime_is_none`: only a failed record for frame 10 → `lifetime("L1") is None`;
  `lifetime("L99")` raises `KeyError`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_join.py -q`. Expected: FAIL (`Labels` has no
  `lifetime`).
- [ ] **Step 2:** Implement rules 1–5.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): labels per lifetime: the model's majority reading, agreement, links with counts`

---

Tasks 12–16 are the evaluation switches (spec §10 step 8). They land after P1 and change no default.

### Task 12: Arms B, C and D: config, schemas, prompts, user turn

**Files:**
- Modify: `src/scry/config.py`, `scry.toml`, `src/scry/annotate/output.py`, `src/scry/prompts/annotate.py`,
  `src/scry/annotate/blocks.py`, `src/scry/annotate/proposal.py`, `src/scry/annotate/stage.py`, and the tests
  `test_config.py`, `test_annotate_output.py`, `test_annotate_prompt.py`, `test_annotate_blocks.py`,
  `test_annotate_stage.py`

**Interfaces:**
- Produces: `AnnotateConfig.arm: Literal["A", "B", "C", "D"] = "A"` (TOML `arm = "A"`); `output_model`,
  `system_prompt`, `prompt_version` and `build_blocks` accept every arm; `to_proposal` accepts `"D"` (the arm A path;
  `"B"` and `"C"` raise `ValueError` until Task 13). New component models, every field required:

```
OutRect           x0: int · y0: int · x1: int · y1: int     ("left", "top", "right (exclusive)", "bottom (exclusive)")
OutPoint          x: int · y: int                           ("a pixel inside the text you mean, near its middle")
OutContainerRect  OutContainer's fields + rect: OutRect     ("The container's visible outline, title bar included.")
OutRunAt          boxes: list[OutPoint] · joiner: Literal["", " "]
OutPairAt         key: list[OutPoint] · value: list[OutPoint]
OutRecordAt       members: list[list[OutPoint]] · header: list[OutPoint]
OutTextAt         at: OutPoint · text: str
```

| Arm | `containers` | `assign`, `unassigned` | `runs`, `pairs`, `records` | `texts` (transcribing) | `missed` (transcribing) |
|---|---|---|---|---|---|
| A | `OutContainer` | yes | by id | `OutText` | yes |
| B | `OutContainerRect` | no (code assigns) | by id | `OutText` | yes |
| C | `OutContainerRect` | no (code assigns) | `Out…At` (points) | `OutTextAt` | no (code derives it, D17) |
| D | `OutContainer` | yes | by id | `OutText` | yes |

Class names `AnnotateOut` + arm + `T`/`G`: eight classes, eight schema hashes (arm D's schema differs from arm A's only
in its title, which is enough for the cache key).

**Prompt paragraphs that differ from arm A** (spec §6's table; each is a whole paragraph; anything not listed is arm
A's paragraph, character for character).

*Arms B and C, paragraph 3 (`containers`):*
```
containers: the windows (top-level application windows) and popups (menus, dialogs, tooltips, toasts) on screen. Containers do not nest. Anything drawn over a window is its own popup, never part of what it covers; a popup may name the window it belongs to as owner. Give each container an id (c1, c2, ...), its application and name, and the containers it covers. rect: the rectangle of the container's visible outline, title bar included, as x0, y0, x1, y1 in the coordinates the user message states.
```
*Arms B and C, paragraph 4 (replaces `assign`):*
```
Text is assigned to containers by code, not by you: a piece of text belongs to the container whose rectangle holds its centre and, where rectangles overlap, to the one in front, which the code knows from covers. Draw each rectangle around the whole container and fill in covers for every overlap.
```
*Arm C, paragraph 2 (images):*
```
You are shown one screenshot. An OCR engine has detected the pieces of text on it, but you are not shown its boxes. Wherever an answer points at a piece of text, give a point: the x and y of a pixel inside that text, near its middle, in the coordinates the user message states. Code matches each point to the OCR box nearest to it.
```
*Arm C, paragraph 5 (`links`), in full (arm A's with points for box ids):*
```
links: relations between pieces of text of one container, given as three lists of points. A piece of text belongs to at most one run, pair or record; column headings are the exception and may be named by every record of their table.
  runs: pieces of text that are one continuous piece of text which the screen wrapped onto the next line, in reading order, one point each. joiner is "" when a word was cut in two by the wrap, " " otherwise.
  pairs: a label and its value (a property and its value, a form field and its content). key and value are lists of points. A two-column grid of labels and values is pairs, not records.
  records: one row of a table with three or more columns: members, left to right, each a list of points; header, the points of the column headings when they are visible, otherwise [].
Pieces of text that merely sit side by side stand alone: tabs, toolbar buttons, menu items, breadcrumbs.
```

*Arm C, paragraph 6 (`texts`):*
```
texts: for every piece of text on screen (inside the target areas, when the user message lists target areas), one entry per run of text on one visual line (a label, a button, a menu item, a table cell, a command line together with its prompt): a point inside it and its verbatim text. Preserve case, punctuation, whitespace and symbols. Never correct, complete or normalize commands, code, paths or identifiers. Use ? for a character you cannot resolve. An icon is not text: leave it out.
```
*Arm D, paragraph 2 (images):*
```
You are shown one screenshot. The user message lists every piece of text an OCR engine detected on it as a box id with its rectangle, b1: x0,y0,x1,y1, in reading order, in the coordinates it states. Use the rectangles to know which id refers to which text on screen. The user message also names the targets: the boxes you are asked to label.
```
*Arm D, paragraph 6 (`texts`):* arm A's with `read from Image 1` → `read from the screenshot`.

Group-only replaces paragraph 6 by the same sentence under every arm.

**Rules for the user turn** (`COORDS` = `Coordinates are pixels of the {W}x{H} frame: top-left origin, x1 and y1
exclusive.`, followed when `scale != 1.0` by ` The image is scaled by {scale:g}; give and read every coordinate in the
unscaled {W}x{H} frame.`; *W*, *H* are `frame.width`, `frame.height`; D9):
1. Arm B: arm A's blocks with `COORDS` inserted after the overlay image.
2. Arm D: `Screenshot (frame {n}, t={t:.2f}s):`, the clean frame, `COORDS`, `Boxes, as id: x0,y0,x1,y1 in reading
   order: b1: 4,4,40,20; b2: 70,4,110,20.` (or `Boxes: none.`), then arm A's targets, animating, unsettled and final
   lines. Coordinates only: no OCR text (D8).
3. Arm C: `Screenshot (…):`, the clean frame, `COORDS`; when the targets are not every box: `Target areas, as
   x0,y0,x1,y1: 70,4,110,20.` (the target boxes' rectangles in reading order, joined by `; `) or `Target areas: none.`;
   when some box has `in_churn`: `Animating areas (low confidence), as x0,y0,x1,y1: …` (those boxes' rectangles); the
   unsettled line; the final line. No box ids anywhere.
4. Arms C and D send no overlay: `overlay_png` is `None`, the stage draws none, and `input_hashes[1] == "-"`.
5. The stage's manifest entry records the arm.

**Tests to write first:**
- `test_config.py::test_arm_key`: default `"A"`; `arm = "E"` raises `pydantic.ValidationError`.
- `test_annotate_output.py::test_fields_per_arm`: B transcribing → `["containers", "runs", "pairs", "records", "texts",
  "missed", "description"]`; C transcribing → `["containers", "runs", "pairs", "records", "texts", "description"]`; D
  equals A; the group-only lists lack `texts` and `missed`. `test_schema_is_strict_friendly` and
  `test_models_are_memoised_and_named` now cover all eight classes (eight distinct names, eight distinct
  `sha256_obj(model_json_schema())`).
- `test_annotate_prompt.py::test_arm_paragraph_differences`: every prompt has 7 paragraphs; B differs from A exactly at
  indices `{2, 3}`; C from A at `{1, 2, 3, 4, 5}`; C from B at `{1, 4, 5}`; D from A at `{1, 5}`; group-only D from
  group-only A at `{1}`; the C prompt contains neither `box id` nor `Image 2`; `test_old_vocabulary_is_absent` covers
  all arms. `::test_versions`: `prompt_version("B") == "annotate-v1+B"`; `prompt_version("C", False, scale=0.5) ==
  "annotate-v1+C+grouponly+s0.5"`.
- `test_annotate_blocks.py::test_arm_b_c_d_blocks` (Fixture E, frame 0): B → the texts after the images are `COORDS`
  for 128x64, `"Boxes: b1, b2."`, `"Targets: all boxes."`, `"Return the JSON object."`; C → block types `[text, image,
  text, text]`; D → the texts are `"Screenshot (frame 0, t=0.00s):"`, `COORDS`, `"Boxes, as id: x0,y0,x1,y1 in
  reading order: b1: 4,4,40,20; b2: 70,4,110,20."`, `"Targets: all boxes."`, `"Return the JSON object."`.
  `::test_arm_c_targets_and_churn_are_rectangles`: targets `("b2",)` and `b1.in_churn` → `"Target areas, as
  x0,y0,x1,y1: 70,4,110,20."` and `"Animating areas (low confidence), as x0,y0,x1,y1: 4,4,40,20."`.
  `::test_scaled_coordinates_sentence`: `scale=0.5` → the coordinates text ends with `unscaled 128x64 frame.` and
  the box rectangles in arm D's list are unchanged.
- `test_annotate_stage.py::test_arm_d_end_to_end`: `arm = "D"` with the standard answer → records as in arm A,
  `prompt_version "annotate-v1+D"`, one image block per call, no file in `overlays/`, manifest `arm "D"`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_output.py tests/test_annotate_prompt.py
  tests/test_annotate_blocks.py tests/test_annotate_stage.py tests/test_config.py -q`. Expected: FAIL.
- [ ] **Step 2:** Add the key, the models, the paragraphs (copied from this task) and rules 1–5.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): referencing arms B, C, D: schemas, prompts and user turns (spec §6)`

### Task 13: Arms B and C in code: centre-inside, front-most, snapping

**Files:**
- Create: `src/scry/annotate/geometry.py`, `tests/test_annotate_geometry.py`
- Modify: `src/scry/annotate/proposal.py`, `tests/test_annotate_proposal.py`, `tests/test_annotate_stage.py`

**Interfaces:**
- Produces, in `geometry.py`: `centre(b: BBox) -> tuple[float, float]` = `((x0 + x1) / 2, (y0 + y1) / 2)`;
  `inside(p, rect: BBox) -> bool`; `point_rect_distance(p, rect: BBox) -> float`; `median_box_height(boxes:
  list[Box]) -> float` (`statistics.median` of `y1 − y0`; `0.0` with no boxes); `container_at(p, containers:
  list[Container]) -> tuple[Container | None, Literal["ok", "outside", "ambiguous"]]`; `snap(p, boxes: list[Box],
  margin_px: float) -> Box | None`.
- `to_proposal` handles `"B"` and `"C"`.

**Rules (spec §6 table: "assigns boxes by centre-inside, front-most container wins"; "snaps each point to the nearest
box"):**
1. `inside`: `x0 ≤ x < x1 and y0 ≤ y < y1`. `point_rect_distance`: `dx = max(x0 − x, 0, x − x1)`, `dy` likewise,
   `hypot(dx, dy)`; 0 inside.
2. **Rectangles are sanitised first:** each `x` is clamped into `[0, W]`, each `y` into `[0, H]`; a rectangle with `x1 ≤
   x0` or `y1 ≤ y0` afterwards becomes `rect None` (`bad_rect`); the container stays, and no box can fall in it.
3. `container_at` (D10): candidates = containers whose `rect` holds the point. None → `(None, "outside")`. One → it.
   Several: drop every candidate whose id is in the `covers` of another candidate; if exactly one is left it wins;
   otherwise `(None, "ambiguous")`. Direct `covers` only: no transitive closure, no popup-over-window rule, no area
   rule (§12).
4. `snap` (D11): the box with the smallest `point_rect_distance`, the earliest in reading order among equals; `None`
   when that distance exceeds `margin_px` or there are no boxes. `margin_px` is `track`'s (IA5).
5. Arm B: for each target in reading order, `container_at(centre(box))` → an `Assign`, or `unassigned` with `outside`
   or `ambiguous` counted. Links, texts and missed come by id as in arm A.
6. Arm C: assign as arm B. Every point of a link is snapped over **all** boxes of the frame (a link may name a known
   box); a link with a point that snaps to nothing is dropped (`link_unsnapped`); repair then judges the ids as usual,
   so two points falling in one OCR box make the link malformed (spec §5: a key and value in one box can never be a
   pair). Each `OutTextAt` is snapped the same way: a hit is `TextReading(box, text)`; a miss becomes a missed text
   `(text, container_at(point) when "ok" else None)` (D17).

**Tests to write first** (Fixture S; `margin_px(boxes, [], 0.5) == 8`):
- `test_annotate_geometry.py::test_distance_and_inside`: `point_rect_distance((245, 48), (120,40,240,56)) == 5.0`;
  `((250, 80), same) == 26.0`; `((180, 48), same) == 0.0`; `inside((240, 48), (120,40,240,56))` is false, `inside((120,
  40), …)` true; `median_box_height([]) == 0.0` and `16.0` for Fixture S.
- `::test_snap_within_margin_only`: `(180, 48)` → `b4`; `(245, 48)` → `b4` (5 ≤ 8); `(250, 48)` → `None` (10 px from
  `b4` and from `b5`); the same point with `margin_px=16` → `b4` (reading order breaks the tie); `(250, 80)` → `None`;
  `snap(p, [], 8) is None`.
- `::test_front_most`: with `c1`, `c2`, `c3` (covers `["c1"]`) the point `(190, 108)` → `(c3, "ok")`; with
  `c3.covers = []` → `(None, "ambiguous")` (the model did not say which is in front, and code does not guess); with
  `c1.covers = ["c3"]` and `c3.covers = ["c1"]` → `(None, "ambiguous")` (nothing is left); with `c1.rect =
  (0,0,250,90)` and no `c3` the point `(190, 108)` → `(None, "outside")`; the point `(60, 18)` → `(c1, "ok")`.
- `test_annotate_proposal.py::test_rect_sanitising`: frame 400×200; `(-20,-5,450,100)` → `(0,0,400,100)`;
  `(300,50,300,80)` → `None`; `(120,80,100,90)` → `None`; counts `{"bad_rect": 2}`.
- `::test_arm_b_assigns_by_centre`: the `AnnotateOutBT` answer with Fixture S's three containers (`c3` covers `["c1"]`)
  → assign `[b1→c1, b2→c2, b3→c1, b4→c1, b5→c2, b6→c3]`, `unassigned []`, counts `{}`; with `c1.rect = (0,0,250,90)` and
  no `c3` → `b6` in `unassigned`, counts `{"outside": 1}`.
- `::test_arm_c_points`: an `AnnotateOutCT` answer with `c1` and `c2`, the pair `key [(50, 48)] value [(180, 48)]`, the
  run `boxes [(325, 18), (600, 18)] " "`, texts `at (325, 48) "PS C:\> az login"` and `at (30, 150) "Networking"` →
  links `[PairLink(key=["b3"], value=["b4"])]`; texts `[TextReading(box="b5", text="PS C:\> az login")]`; missed
  `[("Networking", "c1")]`; assign `[b1→c1, b2→c2, b3→c1, b4→c1, b5→c2, b6→c1]`; counts `{"link_unsnapped": 1}`.
- `test_annotate_stage.py::test_arm_b_end_to_end` (Fixture S written as a one-frame run; the answer of
  `test_arm_b_assigns_by_centre` plus the pair `key [b3] value [b4]` and a text per box equal to its OCR text): the
  record has the six assigns, `containers[0].rect == (0, 0, 250, 200)`, `links == [PairLink(key=["b3"],
  value=["b4"])]`, `repairs 0`, `prompt_version "annotate-v1+B"`, and `overlays/00007.png` exists.
  `::test_arm_c_end_to_end` (the answer of `test_arm_c_points`): `missed == [Missed(id="m1", text="Networking",
  container="c1")]`, `repair_counts == {"link_unsnapped": 1, "text_missing": 5}`, one image per call, no overlay file.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_geometry.py tests/test_annotate_proposal.py
  tests/test_annotate_stage.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): arms B and C: boxes assigned by centre with the front-most container winning; points snapped within the margin`

### Task 14: Readings assigned by position and similarity together

Conditional on the evaluation keeping the second reading (spec §7). The switch is off by default.

**Files:**
- Create: `src/scry/annotate/readings.py`, `tests/test_annotate_readings.py`
- Modify: `src/scry/config.py`, `scry.toml`, `src/scry/annotate/stage.py`, `tests/test_config.py`,
  `tests/test_annotate_stage.py`

**Interfaces:**
- Produces: `AnnotateConfig.text_assignment: Literal["as_returned", "position_similarity"] = "as_returned"` and
  `assign_reach: float = Field(2.0, ge=0)  # × the frame's median box height`; a validator: `position_similarity`
  with `transcribe = false` raises `ValueError("text_assignment = 'position_similarity' needs transcribe = true")`.
  `assign_readings(texts: list[TextReading], boxes: list[Box], targets: Sequence[str], reach_px: float) ->
  tuple[list[TextReading], dict[str, int]]`.

**Rules (spec §7: the model misassigned readings to a neighbouring box on 5 of 53 settled lines, L43; D18):**
1. The stage applies it between `to_proposal` and `repair`, to `Proposal.texts`, only when the switch is on and
   `texts` is not `None`; `reach_px = cfg.annotate.assign_reach × median_box_height(boxes)`. The request is unchanged, so
   the prompt version and the cache key are unchanged (D22).
2. A reading whose `box` is not a box of the frame passes through untouched (repair counts it).
3. For reading *i* with named box *a*: `p = centre(a)`; its candidates are the target boxes *b* with
   `point_rect_distance(p, b.bbox) ≤ reach_px`. `s(i, b) = textdiff.similarity(text_i, b.text)`.
4. Claims: `(i, a)` when *a* is a target; and `(i, b)` for every other candidate with `s(i, b) > s(i, a)` — strictly:
   the model's own reference stands unless another nearby box resembles the reading more. There is no similarity
   threshold.
5. Claims are sorted by similarity descending, then distance ascending, then the box's place in reading order, then
   the reading's index; each is accepted when its reading has no box yet and its box has no reading yet.
6. An accepted reading becomes `TextReading(box=b, text=text, named=a if b != a else None)`; the output is ordered by
   the boxes' reading order, the pass-through readings after them. A reading with no accepted claim is dropped
   (`text_unplaced`). The text itself is never altered: both readings are recorded, neither is picked (§7).

**Tests to write first** (boxes 200 px wide and 16 px tall at a 20-px pitch: `b1 (0,0,200,16)`, `b2 (0,20,200,36)`,
`b3 (0,40,200,56)`; all targets; `reach_px = 32.0`):
- `test_off_by_one_rows_are_put_back`: OCR texts `"PS C:\> az login"`, `"PS C:\> kubectl get nodes"`, `"PS C:\> az aks
  list"`; readings `(box "b2", "PS C:\> az login")`, `(box "b3", "PS C:\> kubectl get nodes")` →
  `[TextReading(box="b1", text="PS C:\> az login", named="b2"), TextReading(box="b2", text="PS C:\> kubectl get nodes",
  named="b3")]`, counts `{}`. (Both winning claims have similarity 1.0 and distance 12.)
- `test_a_better_reading_of_an_edited_text_stays`: OCR `b1 "PS C:\> az 1ogin_"`, `b2 "PS C:\> kubectl get nodes"`;
  readings `(b1, "PS C:\> az login")`, `(b2, "PS C:\> kubectl get nodes")` → unchanged, `named None` on both.
- `test_identical_texts_do_not_swap`: OCR `b1 "1.24.10"`, `b2 "1.24.10"`; readings `(b1, "1.24.10")`, `(b2,
  "1.24.10")` → unchanged (equal similarity is not strictly greater).
- `test_reach_bounds_the_move`: `b1 (0,0,200,16) "alpha"`, `b2 (0,100,200,116) "beta"`; the reading `(b2, "alpha")` →
  stays on `b2` (the distance to `b1` is 92 > 32).
- `test_a_reading_without_a_box_is_dropped`: OCR `b1 "alpha"`; readings `(b1, "alpha")`, `(b1, "zzz")` → `[b1
  "alpha"]`, counts `{"text_unplaced": 1}`.
- `test_unknown_and_empty_readings`: `(b9, "x")` passes through as it is; `(b1, "")` keeps `b1` (an empty reading
  claims only the box the model named).
- `test_config.py::test_text_assignment_keys`: defaults `"as_returned"` and `2.0`; `position_similarity` with
  `transcribe = false` raises.
- `test_annotate_stage.py::test_text_assignment_does_not_change_the_cache_key`: a one-frame run with the three boxes of
  the first test and a real `AnthropicProvider(ModelConfig(), CallCache(run.cache_dir), client=fake_client([{"parsed":
  answer}]))`, where `answer` is an `AnnotateOutAT` with one window `c1`, `b1, b2, b3 → c1`, no links, the two shifted
  texts of the first test, no missed and a description; run with `as_returned`, then with `position_similarity` → `len(client.messages.calls) ==
  1`; the second `annotations.jsonl` has `texts[0] == TextReading(box="b1", text="PS C:\> az login", named="b2")` and
  `repair_counts == {"text_missing": 1}`; both records have `prompt_version "annotate-v1"`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_readings.py tests/test_annotate_stage.py
  tests/test_config.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6 and the keys.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): optional assignment of readings by position and similarity; the model's own reference kept in named (spec §7)`

### Task 15: The pane label (P4)

**Files:**
- Modify: `src/scry/config.py`, `scry.toml`, `src/scry/annotate/output.py`, `src/scry/prompts/annotate.py`,
  `src/scry/annotate/stage.py`, and the tests `test_config.py`, `test_annotate_output.py`, `test_annotate_prompt.py`,
  `test_annotate_stage.py`, `test_annotate_join.py`

**Interfaces:**
- Produces: `AnnotateConfig.pane: bool = False`; a validator: `pane = true` with arm B or C raises `ValueError("pane
  needs arm A or D")` (D12). `OutAssignPane` = `OutAssign` + `pane: str | None` ("Short name of the area of its window
  the box sits in, or null."); `output_model(arm, transcribe, pane=True)` for arms A and D, class names ending in `P`
  (`AnnotateOutATP`, …); `system_prompt(…, pane=True)`; version suffix `+pane`.

**Rules (spec §3: "pane is at most a label string"; §9 P4):**
1. With a pane the `assign` paragraph is this whole paragraph instead (arm A's sentence, then the pane's):
```
assign: for every target box id, the container it belongs to. Every target appears exactly once, or in unassigned. pane: a short name for the area of its window the box sits in (title bar, tab strip, toolbar, left navigation, editor, terminal, status bar), or null when the window has no distinct areas or the container is a popup. A pane is only a name: never list a pane as a container.
```
2. The string is stored on the `Assign` entry (empty after stripping → `None`), joined as `BoxLabel.pane`, and read by
   nothing mechanical: it is never a container, never diffed, never an id (L31: panes split 8 ways on one frame and 3
   on the next).

**Tests to write first:**
- `test_config.py::test_pane_key`: default `False`; `pane = true` with `arm = "B"` or `"C"` raises; with `"D"` loads.
- `test_annotate_output.py::test_pane_variant`: `output_model("A", True, True).__name__ == "AnnotateOutATP"`; its
  `assign` items have the properties `box`, `container`, `pane`, all required; `output_model("B", True, True)` raises
  `ValueError`; the strict-friendly test covers the four pane classes.
- `test_annotate_prompt.py::test_pane_changes_one_paragraph`: with and without a pane the prompts differ only at index
  3; the pane paragraph starts with the plain one and contains `pane:`; `prompt_version(pane=True) ==
  "annotate-v1+pane"`; `prompt_version("D", False, True, scale=0.5) == "annotate-v1+D+grouponly+pane+s0.5"`.
- `test_annotate_stage.py::test_pane_is_stored`: `pane = true`; the answer gives `b1` the pane `"title bar"` and `b2`
  `"  "` → `assign[0].pane == "title bar"`, `assign[1].pane is None`, `prompt_version "annotate-v1+pane"`.
- `test_annotate_join.py::test_pane_is_joined`: a record whose assign for `b1` has the pane `"terminal"` →
  `box("10:b1").pane == "terminal"`, and the carried box `"11:b2"` has it too.

- [ ] **Step 1:** Write the tests. Run the five test files with `-q`. Expected: FAIL.
- [ ] **Step 2:** Implement the key, the class, the paragraph and the suffix.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): optional pane label string on assign entries, arms A and D (P4)`

### Task 16: Incremental annotation

**Files:**
- Create: `src/scry/annotate/context.py`, `tests/test_annotate_context.py`
- Modify: `src/scry/config.py`, `scry.toml`, `src/scry/prompts/annotate.py`, `src/scry/annotate/blocks.py`,
  `src/scry/annotate/stage.py`, and the tests `test_config.py`, `test_annotate_prompt.py`, `test_annotate_blocks.py`,
  `test_annotate_stage.py`

**Interfaces:**
- Produces: `AnnotateConfig.mode` gains `"incremental"`; `neighbour_reach: float = Field(1.0, ge=0)  # × the frame's
  median box height`; a `Config`-level validator: `annotate.mode == "incremental"` with `model.mode == "batch"` raises
  `ValueError("incremental annotation cannot run in batch mode: each call needs the answers before it")` (D6).
  - `@dataclass CallContext`: `known: list[Container]`, `box_container: dict[str, str | None]`, `linked:
    frozenset[str]`, `neighbours: list[str]`, `next_id: int`.
  - `build_context(plan: CallPlan, fb: FrameBoxes, labels: Labels | None, reach_px: float) -> CallContext`
  - `context_blocks(ctx: CallContext, arm: str, fb: FrameBoxes) -> list[dict]`
  - `build_blocks(…, context: CallContext | None = None)`; `system_prompt(…, incremental=True)`; suffix `+inc`.

**The incremental paragraph,** inserted as paragraph 3 (after the images paragraph); every other paragraph is
unchanged. Arms A and D:
```
Most of this screen has been labelled already. The user message names the targets (text that is new or has changed), the known containers (windows and popups labelled earlier, with their ids) and the known boxes near the targets with the container each belongs to. Label only the targets. Assign a target to a known container by that container's id, or to a new container; list in containers only containers that are not known, numbered from the id the user message gives. A link must include at least one target and may include known boxes that are not already linked. The description still covers the whole screen as it is now.
```
Arms B and C:
```
Most of this screen has been labelled already. The user message names the targets (text that is new or has changed), the known containers (windows and popups labelled earlier, with their ids and last rectangles) and the known text near the targets with the container each belongs to. Label only the targets. List in containers every container on screen now with its current rectangle: repeat a known container's id for a known container (only its rectangle and covers are read) and number new containers from the id the user message gives. A link must include at least one target and may include known text that is not already linked. The description still covers the whole screen as it is now.
```

**Rules (spec §2, §6 "when incremental"; D3, D6, D7, D15, D27, D28):**
1. **One rule for every call.** In incremental mode every call uses the `+inc` prompt and carries the two context
   blocks, a head included (its lists are empty): "the first frame and a cut are the same rule with every box new".
   Plans come from `plan_calls(…, "incremental")`; the stage's inputs gain `run.changes` and `run.lifetimes`; either
   file absent → `ValueError("… run `scry track` first")`. The overlay numbers every box, as always (D7).
2. **Order.** `chains(plans)`; the calls of a chain run one after another, each after the previous record has been
   repaired; chains run concurrently under the same bound as Task 9. Before a call that is not a head, `labels =
   build_labels(<the chain's records so far>, frame_boxes, lifetimes)`.
3. `build_context`: the *carried* boxes are the frame's boxes that are not targets, in reading order.
   `box_container[b]` is the id of `labels.box(ref).container`, `None` for an unlabelled or unassigned box. `known` =
   the distinct containers of the carried boxes, by `container_ref`, in the order of their first carried box; each is
   the entry with that reference in `labels.frame(plan.frame).containers` when there is one (it has the latest
   rectangle; an entry's reference is its `known_as`, or `"<description_frame>:<id>"` without one), else the box
   label's container; `known_as` is set to the `container_ref`; an `owner` or a `covers` id
   that is not a known id is removed. A known container keeps its id (D3). `linked` = the carried boxes that are
   `link_members` of a link in `labels.frame(plan.frame).links`. `next_id` = 1 + the largest *n* among known ids of
   the form `c<n>`, 1 when there is none. A head, or `labels is None`, gives the empty context with `next_id = 1`.
4. `neighbours` (D27): the carried boxes *k* for which some target *t* has `k.y0 < t.y1 + reach_px and k.y1 > t.y0 −
   reach_px`, in reading order; `reach_px = cfg.annotate.neighbour_reach × median_box_height(fb.boxes)`. The band runs
   the whole width of the frame.
5. `context_blocks` returns two text blocks, placed after the targets line:
   - `Known containers: none. New containers start at c1.` — or `Known containers, one JSON object per line:`, then one
     line per known container, `json.dumps({"id": …, "kind": …, "app": …, "name": …, "owner": …}, ensure_ascii=False,
     separators=(",", ":"))` (arms B and C add `"rect": [x0, y0, x1, y1]` or `null`), then `New containers start at
     c<next_id>.`, all joined by `"\n"`.
   - `Known boxes near the targets: b2 (c1, linked), b3 (c1, linked), b4 (c2).` — `(no container)` for a box without
     one; `Known boxes near the targets: none.` when there are none. Arm C writes each as its rectangle: `10,40,110,56
     (c1, linked)`. Ids, rectangles and container ids only: no OCR text (D8).
6. After the call: `repair(…, known=ctx.known, box_container=ctx.box_container, linked=ctx.linked,
   update_known_rects=arm in ("B", "C"))`. The record's `containers` are the known ones followed by the new ones, so
   each record can be read on its own and the join finds a box's container in its own source record.
7. A failed call leaves its record with `error` and the chain goes on: the next context simply has fewer labels
   (spec §6 risks; Review Focus 3). Targets are never re-planned from results (D4).
8. Manifest additions: `skipped_frames` (emitted frames without a call), `chains`. `cost_per_frame_usd` still divides
   by all emitted frames, which is how incremental annotation's saving shows (§9: cost per frame beside every number).

**Tests to write first:**
- `test_config.py::test_incremental_keys`: `mode = "incremental"` loads; `neighbour_reach` defaults to `1.0`; with
  `[model] mode = "batch"` it raises `pydantic.ValidationError` matching `batch`; every-frame with batch loads.
- `test_annotate_prompt.py::test_incremental_inserts_one_paragraph`: for every arm, the incremental prompt has 8
  paragraphs and removing index 2 gives the every-frame prompt; arm A's contains `only containers that are not known`,
  arm B's `every container on screen now`; `prompt_version(incremental=True) == "annotate-v1+inc"`;
  `prompt_version("B", False, False, True, 0.5) == "annotate-v1+B+grouponly+inc+s0.5"`.
- `test_annotate_context.py::test_build_context_fixture_t`: `labels = build_labels([A10], …)`, the plan `CallPlan(11,
  ("b1", "b5"), False)`, `reach_px = 16.0` → `[c.id for c in known] == ["c1", "c2"]`, `[c.known_as for c in known] ==
  ["10:c1", "10:c2"]`, `box_container == {"b2": "c1", "b3": "c1", "b4": "c2"}`, `linked == frozenset({"b2", "b3"})`,
  `neighbours == ["b2", "b3", "b4"]`, `next_id == 3`.
- `::test_neighbour_band`: the same with `reach_px = 0.0` → `[]`; `4.0` → `[]` (`b4` ends at 96, the band of `b5`
  starts at 96: not inside); `5.0` → `["b4"]`; `16.0` → `["b2", "b3", "b4"]`.
- `::test_context_blocks_text`: arm A, the context above → exactly two blocks, the texts `Known containers, one JSON
  object per line:\n{"id":"c1","kind":"window","app":"Browser","name":"Azure portal","owner":null}\n{"id":"c2",
  "kind":"window","app":"PowerShell","name":"PowerShell 7","owner":null}\nNew containers start at c3.` (each JSON
  object on one line, no spaces) and `Known boxes near the targets: b2 (c1, linked), b3 (c1, linked), b4 (c2).`; arm C
  → the second text is `Known boxes near the targets: 10,40,110,56 (c1, linked), 130,40,200,56 (c1, linked),
  10,80,110,96 (c2).`; arm B → each JSON line ends with `,"rect":null}`.
- `::test_known_containers_are_json_lines`: a known container named `He said "hi" \ 区` → every line between the
  first and the last parses with `json.loads` and gives the name back.
- `::test_head_context_is_empty`: a head plan → `known == []`, `neighbours == []`, `next_id == 1`, and the texts
  `Known containers: none. New containers start at c1.` and `Known boxes near the targets: none.`
- `test_annotate_stage.py::test_incremental_run_is_sequential_and_carries_context` (Fixture T; `AnswerProvider` keyed
  by `call_frame`; the answer for frame 10 is `A10`'s content, for frame 11: no containers, `b1→c1`, `b5→c2`, the run
  `[b4, b5] " "`, the pair `key [b1] value [b2]`, the two texts, description `"d11"`): the calls are for frames `[10,
  11]` in that order, none for 12; both used `system_prompt(incremental=True)`; the second call's text blocks include
  `Targets: b1, b5.`, the known-containers text above and the neighbours text above; `annotations.jsonl` equals
  Fixture T's `A10` and `A11` apart from `usage` (so `A11.repair_counts == {"link_already_linked": 1}` and
  `A11.containers` carry `known_as`); manifest `calls 2`, `frames 3`, `skipped_frames 1`, `chains 1`, `targets 6`;
  afterwards `run.load_labels().frame(12).links == [PairLink(key=["12:b2"], value=["12:b3"]), RunLink(boxes=["12:b4",
  "12:b5"], joiner=" ")]`.
- `::test_failed_call_does_not_stop_the_chain`: the answer for frame 10 is `"refusal"` → the call for frame 11 is still
  made; its texts include `Known containers: none. New containers start at c1.` and `Known boxes near the targets:
  b2 (no container), b3 (no container), b4 (no container).`; record 11 is stored whole.
- `::test_incremental_needs_track`: without `lifetimes.jsonl` → `ValueError` matching `scry track`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_context.py tests/test_annotate_stage.py
  tests/test_annotate_prompt.py tests/test_config.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–8, the paragraphs (copied from this task) and the keys.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): incremental annotation: only new or changed boxes are targets, labels ride their lifetimes, calls run in order within a chain (spec §2)`

---

## Self-review

- **Spec coverage.** §2 stage table row `annotate`, "every stage writes only its own file" → Tasks 9, 10; incremental
  annotation (targets, the call on any pixel change, first frame and cut as one rule) → Tasks 3, 16; "no annotation" →
  Tasks 1, 9 (`mode = "off"`, D25). §3 vocabulary (container, link, `c<n>`, `m<n>`, pane as a string) → Tasks 2, 5, 15.
  §5 `annotations.jsonl` and the loader derivations (`vlm`, `agree`, `non_text`, majority per lifetime, labels from the
  own frame's record else the lifetime's latest, `rect` only under B and C, at most one link, cross-container links
  dropped, key and value in one box never a pair) → Tasks 2, 7, 10, 11, 13. §6 `annotate`: the draft prompt, the
  transcribing paragraph, the description kept → Task 5; lists of objects, repair never abort → Tasks 5, 7; the four
  arms → Tasks 12, 13; incremental context and risks → Task 16 and D6, D15; OCR coordinates serving numbering, overlay,
  arm D's list, assignment and snapping → Tasks 4, 12, 13. §7 (record both, `agree`, `non_text`, assignment by
  position and similarity, `mark_match`) → Tasks 10, 11, 14. §8 new config "the annotate switches" → Tasks 1, 12, 14,
  15, 16. §9 cost beside every number → Tasks 8, 9; P1's three bases are three config files (`transcribe = true`,
  `false`, `mode = "off"`); P2's arms and scales → Tasks 12, 13 and `scale`; P3 → Task 16; P4 → Task 15. Not covered by
  design: the guards and per-video cost report (§10 step 7), `interpret`'s rendering of labels, the index's use of
  links (plan 3), running any paid phase.
- **Placeholders.** None: every test names its fixture and expected values; every prompt paragraph is written out.
  The `ValueError`s for arms, pane and incremental "until Task N" are removed by the task they name.
- **Type consistency.** `CallPlan(frame, targets, head)` (Task 3) is what Tasks 6, 9, 16 consume; `Proposal` and
  `to_proposal(arm, out, boxes, targets, frame_size, margin_px)` (Task 7) are extended, not re-signed, in Tasks 12, 13;
  `repair(p, targets, frame_boxes, *, known, box_container, linked, update_known_rects)` (Task 7) is called with its
  context only in Task 16; `output_model(arm, transcribe, pane)`, `system_prompt(arm, transcribe, pane, incremental)`,
  `prompt_version(arm, transcribe, pane, incremental, scale)` keep one signature from Task 5 on; `Labels.box / frame /
  lifetime`, `BoxLabel`, `BoxLink`, `FrameLabel`, `LifetimeLabel` are the names plan 3 assumes; `estimate_cost(usage,
  model, batch)`, `add_usage`, `USAGE`, `run_with_batches(run, cfg, provider, stage_fn)` match plan 3's Tasks 1, 3, 7.
- **Review focus.** Each of the five lines names its test and task.
- **Not verified, by the owner's rule.** No expected value in this plan was produced by running anything. The ones
  that rest on library behaviour rather than on this plan's own rules are: pydantic emitting no `default`, `oneOf` or
  `prefixItems` for the models of Tasks 5 and 12 (they use only required fields, `Literal`, `str | None` and lists);
  the tag fitting right of each box in Fixture E (`label_clashes 0`); `rapidfuzz`'s normalised similarity ordering in
  Task 14's tests, which need only "identical text is 1.0 and anything else is less". If the first test run contradicts
  one of them, the finding goes back to the plan's author as a finding, not as a silent fix.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-21-rebase-boxes-2-annotate.md`. Please review it together
with plans 1 and 3; the "Interface assumptions" list is what the synthesis pass has to reconcile (IA9 before P0 is
priced). I recommend **subagent-driven** execution: sixteen tasks that meet only at the interfaces named above, each
with its own tests, and a wrong label rule is cheap to catch in a per-task review and expensive to find after P1 has
been paid for. Tasks 1–11 must land before P1; Tasks 12–16 before P2–P4.
