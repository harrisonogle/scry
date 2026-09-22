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

> **Reconciled on 2026-09-21** with its two read-only reviews (`docs/reviews/2026-09-21-rebase-plan2-review-rulings.md`
> and `…-plan2-review-executability.md`, both "accept with changes") under the mandate of ledger L44; ledger L49 lists
> what each finding became. The rule of the reconciliation is the spec's §12, *simplify before repairing*. The largest
> change: **every call is independent of every other call.** An incremental call is the every-frame call with a shorter
> target list; nothing from an earlier answer enters a request. So there are no call chains, no context module, no
> known containers, no neighbour band, and batch mode works in every mode. Also: container membership no longer gates
> a link; assigning readings by position and similarity is deferred; arms B and C assign boxes after container repair;
> a transient failure is retried by the next run. Tasks 1–13 keep their numbers (plan 3 refers to Task 8); the pane
> label is now Task 14 and incremental annotation Task 15. The first draft is commit `fbe7982`.

**Goal:** On branch `rebase-boxes`, build the `annotate` stage: one model call per frame that proposes labels for OCR
boxes — containers, typed links, optionally a second reading, and a screen description — written to
`annotations.jsonl`, plus the loader that joins those labels onto boxes, frames and lifetimes on read.

**Architecture:** The model proposes, code disposes. Whatever the referencing arm, the model's answer is converted by
pure functions into one arm-independent proposal, repaired (never aborted) against the measured boxes, and stored in one
record shape; measured files are never touched and nothing downstream is gated on a label. A pure planner decides
which frames get a call and which boxes are targets from `track`'s records alone, and every request is built from
measured records only, so calls are independent of each other: the same stage code runs "every frame" and
"incremental", synchronously or through the Batches API, and a failed call costs only its own labels. The existing
Anthropic provider, call cache and batch path carry the calls; a joined view (`Labels`) gives later stages labels per
box, per frame and per lifetime, resolving a box's labels through its lifetime to the record that labelled it.

**Tech stack:** Python ≥ 3.12 with `uv`; pydantic 2 (records and the structured-output schemas); the `anthropic` SDK
≥ 1.5 through the existing `AnthropicProvider` (`messages.parse`, prompt caching, Batches); Pillow (overlay, scaling);
rapidfuzz (through `scry.textdiff.similarity`); typer; pytest. No new dependencies.

**Spec:** `docs/proposals/2026-09-21-boxes-mode-rebase.md`, revision 3.1: §2 (the order, incremental annotation, the
"no annotation" base), §3, §4 (principles 1, 5, 7, 9), §5 (`annotations.jsonl`), §6 `annotate`, §7, §8, §9 (P1–P4),
§10 steps 3 and 8, §11, and §12 "Simplify before repairing". Where this plan and the spec differ, this plan is later
and wins (the spec's status line); the one deliberate departure is D6. Evidence: `docs/decision-ledger.md` L28–L51.
Executors read the spec with this plan. Sibling plans: `…-rebase-boxes-1-read-track.md` (plan 1, implemented on the
branch: `frames.jsonl`, `boxes.jsonl`, `changes.jsonl`, `lifetimes.jsonl`, `read`, `track`, `report`),
`…-rebase-boxes-3-interpret-summarize-index-ask.md` (plan 3, which consumes this plan's joined view) and
`…-rebase-boxes-4-evaluation.md` (plan 4).

## Interface assumptions

Things this plan needs that spec §5 does not pin down, or names shared with a sibling plan. For plan 1 the code
committed on the branch is the authority, not the plan text.

- **IA1. Plan 1's records and loaders, as committed in `src/scry/schemas.py` and `src/scry/run.py`:** `BBox`, `Frame`
  (`video_id, frame, t_change, t_settled, t_end, settled, churn_regions, caret, width, height, sha256, png`),
  `RawWord`, `Box` (`id, bbox, text, conf, words, in_churn`), `FrameBoxes` (`frame, png, engine, seconds, boxes`),
  `PixelStats` (`changed_fraction, components, textless, textless_area, touched_share, rect_only`), `BoxText`,
  `BoxChange`, `Revert`, `Change`, `FrameTime`, `Lifetime` (`id, text, readings, unstable, sightings, first, last,
  moved, boxes`), `box_ref(frame, box_id)`, `parse_box_ref(ref)`; `Run.frames`, `Run.boxes`, `Run.changes`,
  `Run.lifetimes`, `Run.overlays_dir`, `Run.cache_dir` and `load_frames()`, `load_boxes()`, `load_changes()`,
  `load_lifetimes()`, each `[]` for an absent file. Of a `Change` this plan reads only `to_frame` and `pixels`; of a
  `Lifetime` only `id`, `text`, `boxes` and `first.frame`. So the reshaping of `reverts` (ledger L51) does not touch it.
- **IA2. Reading order is `read`'s id order** (plan 1 D7): `FrameBoxes.boxes` is sorted by top edge then left edge and
  numbered `b1`, `b2`, …; "reading order" in this plan always means that list order.
- **IA3. Lifetimes partition the boxes.** Every box of every frame is in exactly one `Lifetime.boxes` list; a lifetime
  holds at most one box per frame, over consecutive emitted frames; `boxes` is in frame order and `first.frame` is the
  frame of `boxes[0]`; a lifetime that stopped never resumes. A box continues a lifetime when `track` found it
  untouched, in the same place, moved, or a `reread`; the `after` box of an `appended`, `truncated`, `changed` or
  `appeared` record and every `flicker_new` box start one, and so does every box of the first frame (plan 1 Task 11;
  `scry.metrics.targets`).
- **IA4. One `Change` per consecutive pair of emitted frames**, found by `to_frame`; `pixels is None` when pixel
  evidence is missing; `pixels.components` counts the changed components that survive θmin over the whole frame, so
  `components == 0` means "no changed pixel that counts" (spec §6 `track` step 1).
- **IA5. `cfg.track.margin: float = 0.5`** (× the median box height) and
  `scry.track.pixels.margin_px(a_boxes: list[Box], b_boxes: list[Box], margin: float) -> int` =
  `floor(margin × median + 0.5)`, 0 with no boxes (plan 1 Task 7, D16). This plan calls `margin_px(boxes, [], …)` for
  one frame.
- **IA6. Config as committed:** every config model has `extra="forbid"`; `ModelConfig` has `provider, model,
  max_tokens, retry_max_tokens, concurrency, mode` and no per-stage effort key (plan 3 adds `effort_interpret`,
  `effort_summarize`, `effort_ask`; this plan adds `effort_annotate` in the same style); `OverlayConfig` has
  `font_size, font_path, scale, mask`; `scry.toml`'s `[overlay]` holds only `font_size` and `font_path`.
- **IA7. Code as committed:** `scry.overlay` has `place_label`, `scale_image`, `mask_image` and `draw_overlay(png_in,
  lines: list[Box], png_out, cfg: OverlayConfig) -> int`, which reads `cfg.scale` and `cfg.mask`; there is no
  `run_overlay`. `scry.costs.PRICES` and `estimate_cost(usage, model)`. `scry.textdiff.norm` and `similarity`
  (Levenshtein normalised similarity after `norm`). `scry.providers`: `get_provider`, `VlmProvider`, `VlmResult`,
  `image_block`, `text_block`, `CallCache`, `AnthropicProvider`, `BatchRunner`, `PendingRequest`, `strict_schema`. CLI
  `STAGES == ["outline", "decode", "read", "track"]`.
- **IA8. This plan owns the pieces plans 2 and 3 share,** because its Tasks 1–11 land before plan 3: the provider and
  cost fix, `scry.providers.batch.run_with_batches` (client closed inside the loop), `scry.providers.is_transient`,
  `tests/fakes.py` and `src/scry/prompts/__init__.py` (Tasks 5 and 8). Plan 3 drops its copies and keeps only what it
  adds (`ScriptedProvider`, `stage_cost`, `run_costs`, `FakeSyncMessages`). The joined view uses the names plan 3's A4
  assumes: `Run.load_labels() -> Labels | None`, `Labels.box/frame/lifetime`, `BoxLabel`, `BoxLink`, `FrameLabel`,
  `LifetimeLabel`, `LifetimeLink`.
- **IA9. Conventions shared with plans 3 and 4** (ledger L49): (a) test helpers are top-level modules in `tests/`,
  imported as `from fakes import …` and `from annotate_fixtures import …`, the way the committed tests import
  `track_fixtures` (`tests/` has no `__init__.py` and `pyproject.toml` sets no `pythonpath`); (b) the stage order is
  `decode, outline, read, track, annotate, interpret, summarize, index`; this plan's Task 9 reorders `STAGES` to
  `["decode", "outline", "read", "track", "annotate"]`; (c) every task that creates a module which
  `tests/test_package.py` lists as absent removes the name from `GONE_MODULES` in the same commit (here: `prompts`,
  Task 5); (d) a config defaults test asserts the keys it cares about, never the exact `model_dump()` dict, so a later
  task can add a key. Plan 3 (its A10) adds `pythonpath = ["tests"]` to `pyproject.toml` if it is absent; this plan does
  not need it (pytest already puts `tests/` on `sys.path`, which is how `track_fixtures` is imported today) and does
  not add it. This plan has no test of the stage list (cut, L49), so plan 3's Task 10 finds none to delete.
- **IA10. One rule, one implementation, for what incremental annotation asks.** Plan 1's committed
  `scry.metrics.incremental_projection` prices incremental annotation with its own statement of the rule this plan
  implements in Task 3 (`plan_calls`). The two give the same counts (Task 3's rule 3 is plan 1's `targets(change)` read
  from the lifetimes instead of from the change records), so P0's reported numbers (L47: 221 calls, 1,794 target
  boxes of 14,774) stand. When Task 15 lands, one named step makes the projection call `plan_calls` and deletes its
  own rule, so the price and the stage cannot drift apart.
- **IA11. Majority ties:** plan 1 gives a tie to the reading sighted first (its D15); the model's majority reading
  per lifetime uses the same rule.
- **IA12. What plan 4 reads, as reconciled (ledger L50), and all of it holds here:** `run_annotate(run, cfg,
  provider=None)`; the keys `mode` (`every_frame`, `incremental`, `off`), `transcribe` and `scale`; with `mode = "off"`
  no file and a manifest entry with zero usage; `Run.load_labels()` and `Labels.lifetime(id).vlm`; of the manifest
  entry `usage` (four keys, cache hits included), `model`, `cache` (`hits`, `misses`), `calls`, `repairs`,
  `repair_counts`, `errors`, `failed_targets`; `estimate_cost(usage, model)` with an unknown model at the
  `claude-opus-5` prices (every stage test here prices `"fake-model"` that way, `0.004` a call). Two things it does
  not know yet: this plan's manifest also records a batch price (`cost_usd_batch`, Task 9; plan 4 halves in its own
  Task 1, and the two agree at 0.5 ×), which is a price one can pay for every run, incremental runs included (D6);
  and, should its deferred label guards return, one frame's boxes are grouped by the pair (frame of `BoxLabel.source`,
  `container.id`), because container ids are local to a record (D3) and `container_ref` does not exist.
- **IA13. For plan 3 to know:** the three members of the `Link` union do not share fields (`RunLink` has no `key`), so
  a reader branches on `kind` before touching a field; `BoxLink` and `LifetimeLink` do carry every role list. A
  `Missed.id` is local to its record and `FrameLabel.missed` may come from an earlier frame's record, so a missed text
  is cited as `"<FrameLabel.description_frame>:<id>"`. A box's container is read from its `BoxLabel`, never looked up
  by id in `FrameLabel.containers` (Task 10 rule 6). `scry.providers.is_transient` (Task 8) is there for plan 3's
  stages to apply D30's rule to their own records if they choose to.
- **IA14. Plan 1's "Returns with" table** hands this plan the labelling call, its prompt, the overlay's place in the
  pipeline, the batch path, per-box agreement with the icon-glyph strip, and `mark_match`. They return in Tasks 9, 5,
  4 and 9, 8, 10, and 9 (where `mark_match` is also called, D29).

## Decisions this plan makes

The spec is silent or looser on each of these. The list was reviewed by two read-only reviewers and reconciled by the
coordinator under the owner's mandate (ledger L44); what each review finding became is in ledger L49. The numbers of
the first draft are kept so that the reviews can still be read against them; a withdrawn decision keeps its number
and says what replaced it.

- **D1. One stored shape under every arm.** Arm-specific answers (rectangles, points) are converted to ids by code;
  `annotations.jsonl` and the loader never know the arm (§5: one record per call; principle 1). Under arms B and C the
  containers are repaired first and boxes are assigned afterwards, over the repaired list (Task 13 rule 5), so a
  duplicated container id gives two implementers one outcome.
- **D2. The model-facing schema has three link lists (`runs`, `pairs`, `records`), rectangles and points as objects
  with named integer fields, and every field required.** Reason, from reading the installed SDK
  (`anthropic/lib/_parse/_transform.py`, 1.5.0; the executability review confirmed each point): a tagged union becomes
  `anyOf` with its `discriminator` pasted into the description, a tuple's `prefixItems` is pasted there too instead of
  staying schema, defaulted fields become optional, and a description on a model-typed field is dropped with the
  other siblings of its `$ref`. §6 already demands "lists of objects, never arrays parallel to an id list". The stored
  record keeps §5's single `links` list with `kind`.
- **D3. Container ids are local to a record.** Every call lists the containers it sees afresh and numbers them itself;
  nothing carries a container from one record to the next. Two boxes are in the same container when their labels come
  from the same record and name the same id; nothing more is claimed (§11: no window identity across frames; §9:
  label consistency across frames decides nothing). The first draft's `known_as` and `container_ref` are gone.
- **D4. Targets are a pure function of `track`'s records:** every box of the frame, or, when incremental, the boxes
  whose lifetime starts at that frame. This keeps model behaviour out of what is asked and lets P0 price P3 with no
  model (§9 P0; principle 1). A call that failed for good (a refusal, a schema failure twice) is not asked again: its
  targets stay unlabelled for their lifetimes and are counted (`failed_targets`). A transient failure is retried by
  the next run (D30).
- **D5. Call rule:** the first frame, and every frame whose incoming change has `pixels is None` or
  `pixels.components > 0`; no transition kind is consulted (§2 says "whenever pixels changed" and names no exception).
  `decode` emits a frame only on change, so nearly every frame gets a call: P0 counted 221 calls for 221 frames, with
  12.1 % of the boxes as targets (L47). What incremental annotation saves is boxes per call, not calls.
- **D6. Every request is built from measured records only, so calls are independent in every mode.** An incremental
  call is the every-frame call — the same system prompt, schema and images — whose user turn names fewer targets.
  No context is built from earlier answers: no call chains, no known containers, no neighbours' link state. Batch mode
  (half price) therefore works for incremental annotation too, P3 compares like with like, a failed or retried call
  changes no other call's cache key, and the call for a first frame or a cut is byte for byte the every-frame call, so
  P3 reuses P1's paid answer for it. **This departs from one sentence of spec §6** ("the call also carries the known
  containers and the target boxes' neighbours"; ledger L49). What that context would have bought is container ids and
  names that stay stable across frames, which §9 and §11 say nothing depends on. The costs, accepted: each call
  re-lists the containers on screen (tens of output tokens); two boxes of one window labelled by different calls carry
  separately proposed container labels; the model is not told which carried boxes are already linked, so the join
  refuses such links more often (D15), counted.
- **D7. The overlay numbers every box in both modes; targets are named in the text.** The image of a frame is then the
  same in P1 and P3, "text no box covers" keeps its meaning for `missed`, and no second, untested overlay style is
  introduced (L28–L29: legibility was the first live failure). With D6 this is what makes an incremental call the
  every-frame call plus a target list.
- **D8. No OCR text is ever sent to the model,** in any arm or mode (arm D's list carries ids and rectangles only).
  Exact agreement of two independent readers is the only "quote verbatim" signal (§7); showing OCR's reading would
  end the independence.
- **D9. Every coordinate in a request or an answer is in original-frame pixels, at every image scale;** the user turn
  states the frame size (the form L42 measured for the coordinate list at scale 0.67).
- **D10. Front-most rule for arms B and C:** among the containers whose rectangle holds the box centre, drop those
  that another candidate lists in `covers`; if exactly one remains it wins; otherwise the box is unassigned and counted
  `ambiguous`. No "a popup beats a window" tie-break, no area heuristic, no transitive closure: the count is what P2
  reads, and logic is added only on that evidence (§12).
- **D11. A point snaps to the nearest box only within `track`'s margin** (half a median box height, IA5): the model's
  point and OCR's rectangle come from different tools. No new constant. The coupling is known: `cfg.track.margin` gains
  a second consumer, and at margin 0 a point must fall inside a box, which would handicap arm C for a reason that has
  nothing to do with arm C. P0 kept the margin at 0.5 (L51), so nothing is added for it.
- **D12. The pane label exists only under arms A and D** (it rides on `assign` entries, which B and C do not have).
  If P2 picks B or C, P4's pane needs a design; the config refuses the combination until then.
- **D13. "A box is in at most one link" exempts `header` references.** §5's own example gives every record of a table
  the same header boxes. In every other respect a header id is checked like a member: a bad one drops the record
  (§12: no rescue rule without evidence).
- **D14. Withdrawn: container membership does not gate a link.** The first draft dropped a link unless every member
  was assigned to one container, which is stricter than the spec and cascades: one slip in `assign` cost the link too,
  and under arms B and C every `ambiguous` or `outside` box took its links with it, so P2's link comparison would
  partly have measured container assignment. A link is dropped only when it names an unknown box id, is not a link at
  all (rule 11 of Task 7), or names a box already in another link. The spec's "a link across two containers is dropped
  and counted" goes with it (§4 principle 1: labels never gate); a reader that wants it can compare the members'
  containers on read.
- **D15. A link never re-labels a box that already has one.** Inside one answer the earlier link stands (repair,
  `link_already_linked`). Across records the join decides, in record order: a link that names a box which is already
  in a link in force at that frame is refused for good, and counted in `Labels.relinked`, which P3 reads (so a run
  cannot grow by a third line; §6 risks: "nothing is re-annotated"). The check needs earlier answers but runs on read,
  after every answer is in, so it costs no call its independence. A link may otherwise name any box of the frame.
- **D16. What is in force at a frame.** Box labels: the box's own record if it was a target of a successful record,
  else the latest earlier record in which a box of its lifetime was (§5). A link: it was accepted (D15), every
  lifetime it names still has a box at the frame, and its target members still draw their labels from the record that
  proposed it. The description, the missed texts and the container list are screen-level: those of the latest
  *successful* record at or before the frame, with that record's frame beside them (`description_frame`), so a reader
  can see how old they are; a failed call changes nothing.
- **D17. Arm C details:** `missed` is derived by code (a reading whose point snaps to no box); icons are left out
  rather than returned as `""`, so `non_text` cannot arise, icon boxes stay in index text and count in `text_missing`.
  `repairs` and the agreement denominators are therefore not comparable between arm C and the other arms; where P2
  reads them it says so.
- **D18. Deferred: assigning readings by position and similarity** (the first draft's Task 14, with
  `TextReading.named`, `text_assignment`, `assign_reach` and `text_unplaced`). See "Deferred" after Task 15.
- **D19. Additions to §5's record:** `repair_counts` (the breakdown of `repairs`) and `label_clashes`; `texts` is
  `null` for a group-only call and a list for a transcribing one.
- **D20. The mask modes leave `overlay.py`, and the image scale moves from `[overlay] scale` to `[annotate] scale`.**
  L40 measured masking and did not adopt it; the spec's evaluation has no mask arm; arms C and D scale an image with no
  overlay. Ledger L49 supersedes L40's "the modes remain for experiments"; the code is recoverable from tag
  `pre-rebase-boxes`.
- **D21. Defaults:** `mode = "every_frame"`, `arm = "A"`, `transcribe = true`, `pane = false`, `scale = 1.0` — the
  configuration of §5's example record and of §10 step 3. A default is not a verdict: transcribing and group-only are
  co-equal (§0) and P1 sets each base explicitly in its own config file.
- **D22. The prompt version names the system prompt and schema variant (arm, group-only, pane, scale); the user turn
  is covered by `input_hashes`.** Incremental annotation has no variant of its own (D6). The call-cache key does not
  hash the system prompt's text, so any edit to a prompt paragraph bumps `VERSION` (P5 and P6 plan to tune prompts);
  field descriptions are covered by the schema hash.
- **D23. Costs are cold-equivalent:** the manifest sums the usage stored with every record, cache hits included, and
  prices it both ways (synchronous and batch). Cache-creation tokens are priced at 1.25 × input, batch at 0.5 ×; usage
  is summed over a call's retries (open item "Usage accounting"; principle 9). One under-count is known and made
  visible instead of repaired: when the SDK's parse helper raises on a truncated or non-JSON reply, the attempt was
  billed and its usage never reaches the provider; the provider counts such attempts (`usage_lost`) and the manifest
  shows the number. The provider is not restructured for it. An unknown model is priced as `claude-opus-5`, with a
  logged warning.
- **D24. Two lines of today's user turn are kept:** the boxes inside animating areas and the "not settled" note. They
  are measured facts (`in_churn`, `settled`) that §5 still records. The tag's system-prompt sentence on what to do
  with animating marks is not restored: the description paragraph already asks for "anything animating".
- **D25. `mode = "off"` removes an existing `annotations.jsonl`** (the call cache keeps every paid answer, so turning
  annotation back on costs nothing) and `Run.load_labels()` is `None`; the "no annotation" base then cannot read stale
  labels.
- **D26. `agree`** is today's rule unchanged: equality after `textdiff.norm`, or equality after dropping one leading
  or trailing OCR token of at most 2 characters (§5: "icon-glyph strip kept"). The 2 was `[merge] glyph_max_len`; it
  becomes the named constant `GLYPH_MAX_LEN` beside the rule. That departs from "parameters live in config" (L45,
  recorded in L49): the loader is called without a config (`Run.load_labels()`), the value dates from before the first
  live run and was never tuned to the sample (L30's three-character `[8]` is not caught), nothing in the evaluation
  varies it, and `agree` only flags: it never alters recorded text. `agreement` returns a bool; which token was
  stripped (the tag's second return value) has no consumer.
- **D27. Withdrawn with D6:** no neighbour band, no `neighbour_reach`.
- **D28. Incremental annotation is built for the id-based arms A and D only** (it replaces the first draft's rule for
  known containers under arms B and C, withdrawn with D6). P2 compares the arms on every frame; P3 compares
  incremental against every frame for the arm chosen by then. The config refuses `mode = "incremental"` with arm B or
  C, as D12 does for the pane, until the evaluation picks one of them.
- **D29. `mark_match` is called, not only defined.** When transcribing, the stage's manifest entry reports it: it is
  the diagnostic that caught unreadable overlay tags (L28, L30), and it is the evidence D18 waits for. The name keeps
  the old word "mark" because spec §7 and the ledger use it; it is the one exemption from the vocabulary constraint.
- **D30. A transient failure leaves the stage not up to date.** A record whose `error` starts with `api:` or is
  `max_tokens` was never stored in the call cache, so the next `scry annotate` runs again, gets every answered call
  from the cache and pays only for the failed ones. With independent calls (D6) nothing cascades.
- **D31. The one coordinate-list configuration ever measured (L42: overlay plus list, at scale 0.67) is none of the
  four arms;** arm D has no overlay. That is the spec's definition of the arms; no fifth arm is added.

## Global Constraints

- Work only on branch `rebase-boxes`; plan 1 has landed. The package imports and `uv run pytest` reports 0 failures
  after every commit.
- **Model proposals never gate or alter measured records.** Nothing in this plan writes `frames.jsonl`, `boxes.jsonl`,
  `changes.jsonl` or `lifetimes.jsonl`, and no measured stage reads `annotations.jsonl` (principle 1; spec §2: "every
  stage writes only its own file").
- **No content of the evaluated video in any prompt or schema description.** System prompts, user-turn templates and
  the field descriptions of the model-facing schema (which travel in the JSON schema and are prompt text) contain no
  window title, application name, command, tooltip or resource name of the 14-minute sample; every example in them is
  invented. Every paid answer is cached under the prompt version and the schema hash, and the evaluation checks those
  very containers (the popups of frames 149 and 151). Test fixtures are not prompts and may hold any text.
- **Every request is built from measured records only** (D6): nothing from an earlier model answer enters a request.
- Unit tests only: the fake clients of `tests/fakes.py`, synthetic frames made in the test, hand-written records. No
  network, no model API call, no sample video, no run directory under `runs/`. No prototypes, scratch scripts or trial
  runs by anyone. **The build is not test-heavy (owner):** a test is here because it pins a rule, a record shape,
  repair counts, assignment or cache-key behaviour; tests of wording, absence or structure were cut (ledger L49), and
  an implementer adds none of that kind.
- Test helpers are imported as top-level modules (`from fakes import …`, `from annotate_fixtures import …`), as the
  committed tests import `track_fixtures` (IA9).
- No constants from the sample video: every geometric parameter is relative to box height or frame size, lives in
  `src/scry/config.py` with its unit in a comment, and appears in `scry.toml` (the one named exception is D26).
- No logic for watch-list cases without evidence; no cursor or suggestion locating; no brightness thresholds; nothing
  reasons from how long a text stayed on screen.
- Validation is repair, never abort: a bad answer costs labels, is counted, and the run continues (§6).
- **Simplify before repairing (spec §12).** When a review or the first runs find a fault in a mechanism of this plan,
  the first question is whether the mechanism can go; logic is added only on evidence from real runs. Every rule here
  that drops a label instead of rescuing it (`ambiguous`, `link_already_linked`, `second_text`, `Labels.relinked`) is
  that choice, and its counter is the evidence a later rule would need.
- Coordinates: `BBox = (x0, y0, x1, y1)` in original-frame pixels, `x1`/`y1` exclusive. A point `(x, y)` is inside a
  rectangle when `x0 ≤ x < x1` and `y0 ≤ y < y1`.
- The old vocabulary does not return: no mark, line id, row, region, unit, association or focus in code, prompts,
  records or tests (§3). The one exemption is the function name `mark_match` (D29).
- Every stage writes only its own file, atomically (`scry.jsonl.write_jsonl`), and skips itself when its inputs hash
  and config hash are unchanged (`Run.stage_up_to_date`) and its last run left no transient failure (D30).
- Commit messages end with the attribution lines the session supplies.

## Review Focus

Inputs the spec implies and that are most likely to bite; each has a test in the task that owns the code.

1. **An answer that names things that do not exist:** unknown box ids, a box assigned twice, a box in two links, a
   container that names itself as owner. Expect repairs counted, a valid record, no exception (Task 7
   `test_repair_assign`, `test_repair_links`, `test_repair_containers`).
2. **A frame with no boxes** (a blank or image-only slide). Expect a call all the same (the description), an overlay
   identical in size to the frame, `targets == []`, empty lists, no division by zero in any median (Task 4
   `test_overlay_of_a_frame_without_boxes_is_the_frame`, Task 6 `test_arm_a_blocks`, Task 9
   `test_frame_without_boxes_still_gets_a_call`, Task 13 `median_box_height([]) == 0.0`).
3. **A failed call.** A refusal or a schema failure twice: the record carries `error`, every other call is untouched,
   the failed call's boxes stay unlabelled and the screen-level labels stay those of the latest successful record
   (Task 9 `test_error_record_and_the_run_continues`, Task 10 `test_failed_record_is_not_a_source`). An API error or a
   truncation: the same, and the next run retries just that call (Task 9
   `test_transient_error_is_retried_on_the_next_run`).
4. **Rectangles and points outside the frame, inverted or empty, and a container id used twice** (arms B, C). Expect
   clamping, `bad_rect`, the duplicate dropped before any box is assigned, a box outside every rectangle unassigned, a
   far point snapped to nothing (Task 13 `test_rect_sanitising`, `test_arm_b_assigns_by_centre`,
   `test_snap_within_margin_only`).
5. **Quotes, backslashes, newlines and non-ASCII in names and texts** (`PS C:\Users\msadmin>`, `区`, a window title
   with a double quote). Expect a lossless JSONL round trip (Task 2 `test_annotation_round_trip_unicode`).

Known and not tested here: in batch mode a truncated or schema-invalid result is terminal (the batch path has no
`max_tokens` or schema retry, as today; batch mode is still unexercised live, open items). A reply that the SDK's
parse helper rejects (truncated at `max_tokens` with text in it, or a refusal whose text is not JSON) raises inside
`messages.parse`, so that attempt's usage is lost; it is counted (`usage_lost`, D23), not recovered. The overlay font
path is a macOS path; elsewhere Pillow's default font is used, as today. The arm A system prompt is about 500 tokens,
around Opus 5's 512-token minimum cacheable prefix, so `cache_creation_input_tokens` may be 0; nothing depends on it.
No schema at the tag had an empty-string enum value, and `joiner` has `["", " "]`; if the API rejected it, the first
frame of P1 would show `api:` errors, which is cheap to find.

## File structure at the end of this plan

```
src/scry/
  config.py            + AnnotateConfig [annotate]; ModelConfig.effort_annotate; OverlayConfig loses scale and mask
  schemas.py           + Container, Assign, RunLink, PairLink, RecordLink, Link, TextReading, Missed, Annotation,
                         link_members, link_refs
  run.py               + Run.annotations, load_annotations(), load_labels()
  overlay.py           place_label, scale_image, draw_overlay(…, scale)      (mask code removed)
  costs.py             + USAGE_KEYS, CACHE_WRITE_MULTIPLIER, BATCH_MULTIPLIER, add_usage; estimate_cost(…, batch)
  metrics.py           incremental_projection calls plan_calls; targets() removed               (Task 15)
  providers/
    base.py            + is_transient
    anthropic_.py      usage summed over a request's retries; stats["usage_lost"]
    batch.py           all four usage keys; run_with_batches() (also closes the client inside the loop)
  prompts/
    __init__.py        (empty)
    annotate.py        VERSION, the paragraphs, system_prompt(), prompt_version()
  annotate/
    __init__.py        exports run_annotate
    targets.py         CallPlan, plan_calls                                 (pure; no model, no I/O)
    output.py          the model-facing schema variants: output_model(arm, transcribe, pane)
    blocks.py          frame_block, build_blocks, input_hashes              (the user turn)
    proposal.py        Proposal, to_proposal                                (arm answer → ids)
    geometry.py        centre, inside, point_rect_distance, median_box_height, container_at, snap
    repair.py          REPAIR_KEYS, Repaired, repair_containers, repair
    join.py            GLYPH_MAX_LEN, agreement, BoxLink, BoxLabel, FrameLabel, LifetimeLink, LifetimeLabel, Labels,
                       build_labels
    stage.py           run_annotate, mark_match
  cli.py               + annotate; STAGES == ["decode", "outline", "read", "track", "annotate"]
tests/
  fakes.py annotate_fixtures.py
  test_package.py test_config.py test_schemas.py test_overlay.py test_costs.py test_provider.py test_batch.py
  test_metrics.py                                                                                   (extended)
  test_annotate_targets.py test_annotate_output.py test_annotate_prompt.py test_annotate_blocks.py
  test_annotate_proposal.py test_annotate_geometry.py test_annotate_repair.py test_annotate_join.py
  test_annotate_stage.py
```

## Order of work

**Tasks 1–11 are implemented first: they are what the first paid phase (P1) needs** (spec §10 step 3: arm A on every
frame with the transcribing switch, records, repair, loaders, and the accounting). **Tasks 12–15 are the evaluation
switches** of §10 step 8 (arms B, C, D; centre-inside and snapping; the pane label; incremental annotation); they land
after P1 and change no default. What each task needs:

| Task | Needs |
|---|---|
| 1 Config | plan 1 (landed) |
| 2 Records | plan 1's records |
| 3 Calls and targets | plan 1's records |
| 4 Overlay | — |
| 5 Schema, prompt, version (arm A) | — (edits `tests/test_package.py`) |
| 6 User turn (arm A) | 3, 4 |
| 7 Proposal and repair | 2, 5 |
| 8 Provider, costs, fakes | nothing of this plan (plan 3 may need it early: its A6) |
| 9 Stage and CLI | 1–8 |
| 10 Joined view: boxes and frames | 2 |
| 11 Joined view: lifetimes | 10 |
| 12 Arms B, C, D: config, schemas, prompts, user turn | 1, 5, 6, 7, 9 |
| 13 Arms B and C in code | 12, 7, 9 |
| 14 Pane label | 12 (the `arm` key, for the validator), 5, 7, 9, 10 |
| 15 Incremental annotation | 3, 9, 10, 12 (the `arm` key, for the validator); edits plan 1's `metrics.py` and `report.py` |

Tasks 13, 14 and 15 do not depend on one another.

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
  fields 0.0 or 0; `kind "single"`, `t` any pair of floats, every list empty).
- Lifetimes: `L1 "Resource group" [10:b1, 11:b2, 12:b2]`; `L2 "RG1" [10:b2, 11:b3, 12:b3]`; `L3 "PowerShell 7"
  [10:b3, 11:b4, 12:b4]`; `L4 "PS C:\> az" [10:b4]`; `L5 "Banner" [11:b1, 12:b1]`; `L6 "PS C:\> az login" [11:b5,
  12:b5]` (`readings`, `sightings`, `first` and `last` filled in as plan 1's `Lifetime` defines them; nothing here
  reads them except `first.frame` and `text`). Every box ref of every frame is in exactly one lifetime.
- Record `A10` (frame 10, every box a target): containers `c1` window Browser "Azure portal", `c2` window PowerShell
  "PowerShell 7" (owner null, covers [], rect null); assign b1→c1, b2→c1, b3→c2, b4→c2; links `[pair key [b1] value
  [b2]]`; texts b1 "Resource group", b2 "RG1", b3 "PowerShell 7", b4 "PS C:\> a"; missed `[m1 "Networking" c1]`;
  description "d10"; repairs 0; model "fake-model"; prompt_version "annotate-v1".
- Record `A11` (frame 11, targets `[b1, b5]`), what an incremental call stores. Its containers are listed afresh and
  in another order, so the ids are visibly local to the record (D3): `c1` window PowerShell "PowerShell 7", `c2` window
  Browser "Azure portal"; assign b1→c2, b5→c1; links `[run boxes [b4, b5] joiner " ", pair key [b1] value [b2]]` (the
  pair names the carried box `b2`, which `A10` already put in a pair: repair cannot know that and keeps it, the join
  refuses it, D15); texts b1 "Banner", b5 "PS C:\> az login"; missed `[]`; description "d11"; repairs 0;
  prompt_version "annotate-v1". There is no record for frame 12.

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
| `mode` | `Literal["every_frame", "off"] = "every_frame"` (Task 15 adds `"incremental"`) | which frames get a call and which boxes are targets; `off` is the "no annotation" base (§2) | 1, 15 |
| `transcribe` | `bool = True` | `true`: the call also returns a second reading (`texts`, `missed`); `false`: group-only (§0, §7) | 1 |
| `scale` | `float = Field(1.0, gt=0, le=1)` | factor applied to every image sent; tags keep their pixel size (L33, §9 P2). Replaces `[overlay] scale` (D20) | 1 |
| `arm` | `Literal["A", "B", "C", "D"] = "A"` | referencing arm (§6) | 12 |
| `pane` | `bool = False` | ask for a pane label string per target (arms A, D; §9 P4) | 14 |
| `[model] effort_annotate` | `Effort = "low"` | was `effort_stage2c` (L13) | 1 |

**Rules:**
1. `AnnotateConfig` has `model_config = ConfigDict(extra="forbid")` like every config model (IA6).
2. `scry.toml` gains `[annotate]` with this task's three keys written out at their defaults, and `effort_annotate =
   "low"` under `[model]`. `max_tokens = 16000`, `retry_max_tokens = 32000` (tokens), `concurrency = 4` (calls) and
   `mode = "sync"` under `[model]` are reused unchanged. The three `configs/p0-margin-*.toml` files need no edit: the
   new keys sit at their defaults.
3. Nothing else reads these keys yet.

**Tests to write first (`tests/test_config.py`):**
- `test_annotate_defaults`: `Config().annotate.mode == "every_frame"`, `.transcribe is True`, `.scale == 1.0` and
  `Config().model.effort_annotate == "low"`, each asserted on its own: never the exact `model_dump()`, so Tasks 12, 14
  and 15 can add keys (IA9).
- `test_annotate_section_loads_and_rejects_bad_values`: a TOML holding `[annotate]\nmode = "off"\ntranscribe =
  false\nscale = 0.5` loads with those three values; each of `scale = 0`, `scale = 1.5`, `mode = "sometimes"` and the
  stale key `stage2c_rows = "boxes"` under `[annotate]` raises `pydantic.ValidationError`.
- `test_repo_toml_loads` (exists) additionally asserts `cfg.annotate.mode == "every_frame"` and
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

**Interfaces (pydantic `BaseModel`, unknown fields ignored like plan 1's records):**

```
Container    id: str ("c<n>") · kind: Literal["window", "popup"] · app: str · name: str · owner: str | None = None ·
             covers: list[str] = [] · rect: BBox | None = None
Assign       box: str · container: str · pane: str | None = None
RunLink      kind: Literal["run"] = "run" · boxes: list[str] · joiner: Literal["", " "]
PairLink     kind: Literal["pair"] = "pair" · key: list[str] · value: list[str]
RecordLink   kind: Literal["record"] = "record" · members: list[list[str]] · header: list[str] = []
Link         = Annotated[RunLink | PairLink | RecordLink, Field(discriminator="kind")]
TextReading  box: str · text: str
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
1. Field names and shapes are spec §5's. Inside a record every box id is frame-local (`"b33"`) and every container id
   is local to the record (D3). `repair_counts` and `label_clashes` are additions (D19).
2. `texts is None` means the call did not transcribe (group-only, or it failed); a list, possibly empty, means it did
   (§5: "`texts` exists only when transcribing").
3. `rect` is set only under arms B and C (§5).
4. The link models enforce no minimum lengths: shape is judged by repair (Task 7), so a bad answer can be represented
   and counted rather than raise.
5. One record per call; a failed call is a record with `error` set, `description None`, `texts None` and empty lists,
   and keeps its `targets`.

**Tests to write first (`tests/test_schemas.py`):**
- `test_spec_example_parses`: spec §5's `annotations.jsonl` example, copied verbatim and joined into one JSON line →
  `Annotation.model_validate_json` succeeds; `rec.targets == ["b33"]`; `rec.containers[0].covers == ["c1"]` and `.rect
  is None`; `[l.kind for l in rec.links] == ["pair", "run", "record"]`; `rec.links[1].joiner == ""`;
  `rec.links[2].header == ["b64", "b65", "b66"]`; `rec.missed[0].id == "m1"`; `rec.repair_counts == {}`.
- `test_annotation_round_trip_unicode`: an `Annotation` with a container named `He said "hi" — 区`, a text
  `PS C:\Users\msadmin> az login`, a missed text containing a newline, `texts=None` in a second record; written with
  `write_jsonl` and read with `read_jsonl` → equal to the originals; the written `RunLink` line contains
  `"kind":"run"` and no `key` field.
- `test_link_members_and_refs`: `RecordLink(members=[["b70"], ["b71", "b73"], ["b72"]], header=["b64"])` →
  `link_members == ["b70", "b71", "b73", "b72"]`, `link_refs == ["b70", "b71", "b73", "b72", "b64"]`;
  `PairLink(key=["b1"], value=["b2", "b3"])` → members `["b1", "b2", "b3"]`.
- `test_loaders_return_empty_lists_on_a_fresh_run` (exists) additionally asserts `load_annotations() == []`.

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
- Consumes: `FrameBoxes`, `Change`, `Lifetime`, `box_ref` (IA1, IA3, IA4).
- Produces:
  - `@dataclass(frozen=True) CallPlan`: `frame: int`, `targets: tuple[str, ...]` (box ids, reading order)
  - `plan_calls(frames: list[FrameBoxes], changes: list[Change], lifetimes: list[Lifetime], mode: Literal["every_frame",
    "incremental"]) -> list[CallPlan]`

**Rules (pure functions: no model, no I/O; spec §2, §5 "targets", §9 P0; D4, D5):**
1. `every_frame`: one `CallPlan` per `FrameBoxes`, in frame order, `targets` = every box id. `changes` and `lifetimes`
   are not read.
2. `incremental`, which frames: the first frame of `frames` always. A later frame *b* gets a call when the change with
   `to_frame == b` has `pixels is None` or `pixels.components > 0`; otherwise it gets none (§2: "a transition with no
   changed pixel makes no call"). No change record into a frame that is not the first → `ValueError("changes.jsonl has
   no transition into frame <b>")`. Transition kinds are not consulted (D5).
3. `incremental`, which boxes: the targets of the first call are every box of that frame; the targets of a later call
   at frame *f* are the boxes of *f* that are the first box of a lifetime (`Lifetime.boxes[0] == box_ref(f, id)`), in
   reading order. In a run these are one rule, "the boxes whose lifetime starts at that frame", because every box of
   the first frame starts a lifetime (IA3): "the first frame and a cut are the same rule with every box new" (§2), and
   no threshold appears anywhere. The first frame is written out so that a report filtered to a span (plan 1's
   `select` does not clip lifetimes) prices the span as a video of its own, as P0's reports did (IA10).
4. A box whose lifetime starts on a frame that gets no call is never a target: it stays unlabelled. That needs a box
   appearing on unchanged pixels (`flicker_new`) in a transition without one changed component; P0 saw no frame
   without a call in 221 (L47), and with this reading the targets equal plan 1's committed projection exactly.
5. No frames → `[]`.

**Tests to write first** (Fixture P, defined here: frames 0–3; boxes 0: `b1 "A"`, `b2 "B"`; 1: `b1 "A"`, `b2 "B"`,
`b3 "F"`; 2: `b1 "A"`, `b2 "B2"`, `b3 "C"`, `b4 "F"`; 3: `b1 "Z"`; any rectangles in id order. Changes `T1` 0→1
components 0, `T2` 1→2 components 2, `T3` 2→3 components 1. Lifetimes `L1 "A" [0:b1, 1:b1, 2:b1]`, `L2 "B" [0:b2,
1:b2]`, `L3 "F" [1:b3, 2:b4]`, `L4 "B2" [2:b2]`, `L5 "C" [2:b3]`, `L6 "Z" [3:b1]`):
- `test_incremental_plan`: → `[CallPlan(0, ("b1", "b2")), CallPlan(2, ("b2", "b3")), CallPlan(3, ("b1",))]`. Frame 1
  has no call, and `"F"` is never a target: its lifetime began on frame 1 (rule 4). Five targets in all, which is what
  plan 1's projection counts for the same records (2 + 2 + 1).
- `test_missing_pixels_means_a_call`: `T1.pixels = None` → calls at 0, 1, 2, 3 with targets `("b1", "b2")`, `("b3",)`,
  `("b2", "b3")`, `("b1",)`.
- `test_every_frame_plan`: four plans, each with all of its frame's ids, with `changes=[]` and `lifetimes=[]`; a
  single frame with no boxes → `[CallPlan(0, ())]`; `plan_calls([], [], [], "incremental") == []`.
- `test_fixture_t_plan`: Fixture T, incremental → `[CallPlan(10, ("b1", "b2", "b3", "b4")), CallPlan(11, ("b1",
  "b5"))]`; frame 12 (`components 0`) has no call.
- `test_missing_transition_raises`: Fixture P without `T2` → `ValueError` matching `frame 2`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_targets.py -q`. Expected: FAIL (`No module
  named scry.annotate`).
- [ ] **Step 2:** Implement rules 1–5.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): call frames and targets as a pure function of track's records (spec §2)`

### Task 4: The overlay in the new vocabulary

**Files:**
- Modify: `src/scry/overlay.py`, `src/scry/config.py` (`OverlayConfig`), `tests/test_overlay.py`

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
   deleted, with `OverlayConfig.mask` and `OverlayConfig.scale` (D20: the mask modes were experiment-only and not
   adopted, L40; the image scale is `[annotate] scale`). `scry.toml` has neither key, so it needs no edit.
5. Docstrings and comments say box, never line or mark (§3).

**Tests to write first (`tests/test_overlay.py`; the four placement and tag tests that exist keep their expected
values):**
- Keep: `test_place_label_prefers_right_then_left_then_above_then_below` (`(202, 53, False)`, `(84, 53, False)`,
  `(100, 39, False)`, then a clash), `test_place_label_never_leaves_the_image`, `test_draw_overlay_keeps_dimensions`,
  `test_labels_are_opaque_high_contrast_tags`.
- Adapt: `test_draw_overlay_scale_halves_the_image_and_boxes_but_not_the_tags` passes `scale=0.5` as the argument:
  box `b7 (10,11,121,29)` on 320×120 → output 160×60, outline pixels at `(5, 5)` and `(60, 14)` are `(255, 0, 255)`,
  `(30, 10)` is the background, and the tag is as many pixel rows tall as at full size.
- Delete: `test_overlay_scale_is_bounded` (Task 1 bounds `[annotate] scale`), the four `test_mask_*` tests,
  `test_overlay_mask_is_validated`.
- New `test_overlay_of_a_frame_without_boxes_is_the_frame`: a 64×32 frame of `(9, 9, 9)` and `boxes=[]` → returns 0;
  the output is 64×32 and every pixel is `(9, 9, 9)`.

- [ ] **Step 1:** Write and adapt the tests. Run `uv run pytest tests/test_overlay.py -q`. Expected: FAIL
  (`draw_overlay() got an unexpected keyword argument 'scale'`).
- [ ] **Step 2:** Apply rules 1–5.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `grep -n "mask\|OcrLine\|mark" src/scry/overlay.py` prints nothing.
- [ ] **Step 4:** Commit: `refactor(overlay): boxes and tags only; scale is an argument; mask modes removed (L29, L40)`

### Task 5: The contract with the model, arm A: schema, prompt, version

**Files:**
- Create: `src/scry/annotate/output.py`, `src/scry/prompts/__init__.py` (empty; IA8), `src/scry/prompts/annotate.py`,
  `tests/test_annotate_output.py`, `tests/test_annotate_prompt.py`
- Modify: `tests/test_package.py` (remove `"prompts"` from `GONE_MODULES`: plan 1 listed the package as gone and this
  task brings it back; without the edit `test_old_machinery_is_gone` fails at this commit and every one after it; IA9)

**Interfaces:**
- Consumes: `scry.providers.batch.strict_schema` (tests only).
- Produces:
  - `output_model(arm: str = "A", transcribe: bool = True, pane: bool = False) -> type[BaseModel]`, memoised so that
    equal arguments return the same class. Until Task 12 any arm but `"A"` raises `ValueError`; until Task 14
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
    pane: bool = False) -> str`; `prompt_version(arm: str = "A", transcribe: bool = True, pane: bool = False,
    scale: float = 1.0) -> str`. Neither has an incremental variant (D6).

**Field descriptions** (they travel in the JSON schema, so they are prompt text, and their examples are invented: no
content of the evaluated video, Global Constraints): `OutContainer.id` "Container id: c1, c2, … unique in this
answer."; `kind` "window = top-level application window; popup = menu, dialog, tooltip, toast: anything drawn over a
window."; `app` "Application the container belongs to, e.g. 'Spreadsheet', 'Mail', 'Code editor'."; `name` "The
container's title as shown, or a short human name, e.g. 'Export dialog', 'tooltip: Zoom in'."; `owner` "For a popup,
the id of the window it belongs to, or null. Always null for a window."; `covers` "Ids of the containers this one is
drawn over, in whole or in part."; `OutAssign.box` "A target box id, e.g. 'b7'."; `container` "Id of the container the
box belongs to."; `unassigned` "Target box ids that belong to no container."; `OutRun.boxes` "Box ids in reading
order."; `joiner` "'' when a word was cut in two, ' ' otherwise."; `OutPair.key` "Box ids of the label."; `value` "Box
ids of its value."; `OutRecord.members` "The row's cells, left to right, each a list of box ids."; `header` "Box ids of
the column headings when they are visible, otherwise []."; `OutText.text` "Verbatim text inside the box; '' for an
icon."; `OutMissed.text` "Verbatim text that no box covers."; `OutMissed.container` "Id of its container, or null.";
`description` "What the boxes cannot express about this screen, in plain prose."

**The system prompt for arm A, transcribing (`annotate-v1`), in full.** Seven paragraphs separated by one blank line.
It is spec §6's draft with four changes: links are three lists (D2); the header exception is stated (D13); the images
paragraph keeps today's live-tested sentence about which image to read and introduces the word "target"; the links
paragraph says a link needs a target. The last is empty when every box is a target, and it is what lets the same
prompt serve incremental annotation (D6). The first line's list of screen kinds is the spec's and names a domain, not
the sample.

```
You label screenshots of computer tutorials (terminals, code editors, browsers, dialogs).

You are shown the same screenshot twice. Image 1 is the clean frame. Image 2 is the same frame with a numbered box around every piece of text an OCR engine detected; each number sits beside its box and is NOT part of the screen. A number is written as a box id: b1, b2, ... Read the screen from Image 1; use Image 2 only to know which number refers to which text. The user message lists the box ids and names the targets: the boxes you are asked to label.

containers: the windows (top-level application windows) and popups (menus, dialogs, tooltips, toasts) on screen. Containers do not nest. Anything drawn over a window is its own popup, never part of what it covers; a popup may name the window it belongs to as owner. Give each container an id (c1, c2, ...), its application and name, and the containers it covers.

assign: for every target box id, the container it belongs to. Every target appears exactly once, or in unassigned.

links: relations between boxes of one container, given as three lists. A link must include at least one target; it may also include boxes that are not targets. A box belongs to at most one run, pair or record; column headings are the exception and may be named by every record of their table.
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
   `G` (+ `P` with a pane, Task 14), so each variant has its own JSON-schema title and with it its own schema hash in
   the call-cache key.
2. The schema must survive the SDK's strict transform unchanged in meaning (D2): no `prefixItems`, no `oneOf`, no
   `discriminator`, no `default` anywhere; every object lists all its properties in `required`.
3. `system_prompt` joins named paragraphs with `"\n\n"`; variants swap whole paragraphs and never edit inside a shared
   one, so a test can pin what differs.
4. `prompt_version = VERSION + ("" if arm == "A" else "+" + arm) + ("" if transcribe else "+grouponly") + ("+pane" if
   pane else "") + ("" if scale == 1.0 else f"+s{scale:g}")` (D22; the scale is here because the clean frame is scaled
   in memory and its file hash does not change, as today).
5. The call-cache key holds the version, not the prompt's text: **any edit to a paragraph bumps `VERSION`** (D22).
6. `containers`, `missed` and `description` are about the whole screen in every call; `assign` and `texts` are about
   the targets; a link needs one target. So a record's screen-level labels are complete whatever its target list,
   which is what Task 10 rule 6 relies on.

**Tests to write first:**
- `test_annotate_output.py::test_fields_of_arm_a`: `list(output_model("A", True).model_fields) == ["containers",
  "assign", "unassigned", "runs", "pairs", "records", "texts", "missed", "description"]`; the group-only model has the
  same list without `texts` and `missed`; `output_model("A", True) is output_model("A", True)` (one class, one schema
  hash).
- `::test_schema_is_strict_friendly`: for both models, walking `model_json_schema()`: no key named `prefixItems`,
  `oneOf`, `discriminator` or `default` occurs; every node with `"type": "object"` has `set(required) ==
  set(properties)`; `strict_schema(model)` returns and every object node in it has `additionalProperties is False`;
  the `joiner` property's `enum == ["", " "]`; `owner` is `anyOf` string and null.
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
- `::test_no_sample_video_content`: neither prompt, and neither model's `json.dumps(model_json_schema())`, contains
  any of `PowerShell`, `Cloud Shell`, `Azure`, `kubectl`, `msadmin` (the one absence test kept: every paid answer is
  cached under this text, and the evaluation checks those containers).

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_output.py tests/test_annotate_prompt.py -q`.
  Expected: FAIL (`No module named scry.annotate.output`).
- [ ] **Step 2:** Write the two modules: the models with the descriptions above, the paragraphs copied character for
  character from this task; edit `GONE_MODULES`.
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
    overlay_png: Path | None) -> list[dict]` (Task 12 adds the other arms)
  - `input_hashes(frame: Frame, overlay_png: Path | None, blocks: list[dict]) -> list[str]`

**Rules (spec §6; D6, D7, D8, D22, D24):**
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
3. The targets line is the only thing an incremental call changes (D6): everything in the turn comes from `decode`'s,
   `read`'s and `track`'s records, nothing from an earlier answer, and no OCR text appears in any block (D8).
4. `input_hashes = [frame.sha256, sha256_file(overlay_png) if overlay_png else "-", sha256_obj([b["text"] for b in
   blocks if b["type"] == "text"])]`: every byte of the user turn is covered by the frame's hash, the overlay's hash,
   the text, or the scale in the prompt version (D22).
5. Any arm but `"A"` raises `ValueError` until Task 12.

**Tests to write first** (Fixture E, frame 0; PNGs made in the test, the "overlay" file any 128×64 PNG):
- `test_arm_a_blocks`: block types are `[text, image, text, image, text, text, text]`; the texts are `"Image 1 (clean
  frame 0, t=0.00s):"`, `"Image 2 (same frame with numbered boxes):"`, `"Boxes: b1, b2."`, `"Targets: all boxes."`,
  `"Return the JSON object."`. The same frame with no boxes and `CallPlan(0, ())` → `"Boxes: none."` and `"Targets:
  none."`.
- `test_partial_targets_churn_and_unsettled`: `plan.targets == ("b2",)`, `b1.in_churn = True`, `frame.settled = False`
  → the texts after the images are `"Boxes: b1, b2."`, `"Targets: b2."`, `"Boxes inside animating areas (low
  confidence): b1."`, `"This frame was captured while the screen was still changing (not settled)."`, `"Return the JSON
  object."`.
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
  - `to_proposal(arm: str, out: BaseModel, boxes: list[Box], frame_size: tuple[int, int], margin_px: int) ->
    tuple[Proposal, dict[str, int]]`. This task implements arm `"A"`; Task 12 routes `"D"` to the same path; Task 13
    adds `"B"` and `"C"`. The dict holds counts raised during conversion (none for arm A).
  - `REPAIR_KEYS: tuple[str, ...]` = `("dup_container", "bad_owner", "bad_covers", "bad_rect", "unknown_box",
    "not_target", "unknown_container", "second_assignment", "unplaced", "outside", "ambiguous", "link_unsnapped",
    "link_unknown_box", "link_malformed", "link_already_linked", "text_unknown_box", "text_not_target", "second_text",
    "text_missing", "missed_empty", "missed_unknown_container")`.
  - `repair_containers(containers: list[Container]) -> tuple[list[Container], dict[str, int]]` (rules 1–4; public
    because Task 13 repairs the containers before it assigns boxes, D1).
  - `@dataclass Repaired`: `containers`, `assign`, `unassigned`, `links`, `texts`, `missed: list[Missed]`,
    `counts: dict[str, int]` (non-zero keys only).
  - `repair(p: Proposal, targets: Sequence[str], frame_boxes: Sequence[str]) -> Repaired`. One function for every mode:
    nothing about earlier records is passed in (D6).

**Rules.** Validation is repair, never abort (spec §6). Every dropped item adds 1 to exactly one key, the first check
it fails in the order written; one container can add to `bad_owner` once and to `bad_covers` once for each id removed.
Uncounted by design: a record's empty cells removed, a pane stripped to `None`, a rectangle clamped into the frame,
ids that vanish from `unassigned` under rule 9. `repairs` on the record is the sum of all counts.

*`to_proposal`, arm A:* a field-for-field copy: `OutContainer` → `Container` (`rect None`), `OutAssign` → `Assign` (its
`pane` when the class has one), `unassigned`, `runs` → `RunLink`, `pairs` → `PairLink`, `records` → `RecordLink`, `texts`
→ `TextReading` (or `None` when the answer class has no `texts` field), `missed` → `(text, container)` (or `[]`),
`description`.

*Containers* (`repair_containers`; running it again on its own result changes and counts nothing):
1. A container whose id equals an earlier one in the answer → dropped (`dup_container`).
2. The result list is the remaining containers in returned order.
3. `owner` must name a different container of the result list whose kind is `window`, and only a popup may have one;
   otherwise `owner = None` (`bad_owner`).
4. Every id in `covers` that names no container of the result list, names the container itself, or repeats an earlier
   entry is removed (`bad_covers` each).

*Assign and unassigned,* entries in returned order:
5. Box not in `frame_boxes` → dropped (`unknown_box`). 6. Box not in `targets` → dropped (`not_target`; an
   incremental answer that labels a carried box is refused here). 7. Container not in the result list → dropped
   (`unknown_container`). 8. Box already assigned by a kept entry → dropped (`second_assignment`). A `pane` that is
   empty after stripping becomes `None` (not counted).
9. `unassigned` keeps, in order and once each, the ids that are targets and not assigned; others vanish uncounted.
   Then every target that is neither assigned nor listed is appended in reading order (`unplaced` each). Afterwards
   every target is in exactly one of `assign` and `unassigned` (spec §6).

*Links,* in stored order. "Members" are `link_members`, "refs" are `link_refs` (members plus a record's header; Task
2). A link is dropped for exactly three reasons, and container membership is not one of them (D14): an unassigned
box, a box in another container and a box that is not a target may all be linked.
10. A ref not in `frame_boxes` → link dropped (`link_unknown_box`).
11. Not a link → `link_malformed`: a run needs at least two members; a pair needs a non-empty key and a non-empty
    value; a record's empty cells are removed first and it then needs at least two cells; no ref may occur twice in
    one link (so a key and value that OCR put in one box can never be a pair, spec §5, and a header box cannot be a
    cell).
12. A member that is a member of a link already kept from this answer → dropped (`link_already_linked`; D15). Whether
    a carried box was linked by an earlier record is not known here; the join decides that (Task 10 rule 4).
13. Header ids are exempt from rule 12 and do not become "already linked" (D13).

*Texts,* only when `p.texts` is not `None`, in returned order: 14. box not in `frame_boxes` → dropped
(`text_unknown_box`); 15. not a target → dropped (`text_not_target`); 16. a second text for a box → dropped
(`second_text`); 17. each target left without a text adds 1 to `text_missing` (nothing is invented for it).

*Missed:* 18. text empty after stripping → dropped (`missed_empty`); 19. a container not in the result list → `None`
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
  2}` (owners fail for `c2`: `c9` is unknown; `c3`: a window has no owner; `c4`: its owner `c2` is a popup). Passing the
  repaired containers through `repair_containers` again returns them unchanged with counts `{}`.
- `::test_repair_assign`: targets `b1`–`b6`, frame boxes `b1`–`b7`, windows `c1`, `c2`; assign in order `b1→c1`,
  `b2→c1`, `b2→c2`, `b9→c1`, `b7→c1`, `b3→c7`, `b4→c2`; unassigned `["b5", "b1", "b8"]` → assign `[b1→c1, b2→c1,
  b4→c2]`, unassigned `["b5", "b3", "b6"]`, counts `{"unknown_box": 1, "not_target": 1, "unknown_container": 1,
  "second_assignment": 1, "unplaced": 2}`.
- `::test_repair_links`: targets = frame boxes = `b1`–`b8`; assign `b1, b2, b3, b7 → c1`, `b4, b5, b6 → c2`,
  unassigned `["b8"]`; runs `[b4, b5] " "`, `[b5, b6] ""`, `[b1]`, `[b1, b99]`, `[b6, b6]`; pairs `key [b1] value
  [b2]`, `key [b3] value [b6]`, `key [b7] value [b8]`, `key [b3] value [b3]` → links `[RunLink(boxes=["b4", "b5"],
  joiner=" "), PairLink(key=["b1"], value=["b2"]), PairLink(key=["b3"], value=["b6"]), PairLink(key=["b7"],
  value=["b8"])]`, counts `{"link_already_linked": 1, "link_malformed": 3, "link_unknown_box": 1}` (`[b5, b6]`: `b5`
  is taken; `[b1]`, `[b6, b6]` and `[b3]/[b3]` are not links; `b99` does not exist). The pair across `c1` and `c2`
  and the pair with the unassigned `b8` are kept: containers do not gate a link (D14).
- `::test_repair_records_and_headers`: targets = frame boxes = `b1`–`b18`; records in order: `[[b4], [b5], [b6]]` header
  `[b1, b2, b3]`; `[[b7], [b8]]` header `[b1, b2, b3]`; `[[b4], [b7]]`; `[[b10], [b11]]` header `[b1, b99]`; `[[b12], [],
  [b13]]`; `[[b14]]`; `[[b17], [b18]]` header `[b17]` → three records kept, in order: the first two with header `["b1",
  "b2", "b3"]` (the shared header is not "already linked"), then members `[["b12"], ["b13"]]` with header `[]`; counts
  `{"link_already_linked": 1, "link_unknown_box": 1, "link_malformed": 2}` (the third record; the `b99` header; the
  one-cell record and the header that is also a cell).
- `::test_repair_texts_and_missed`: targets `b1`–`b3`, frame boxes `b1`–`b4`, container `c1`, all assigned; texts
  `b1 "x"`, `b1 "y"`, `b9 "z"`, `b4 "w"`, `b2 ""`; missed `("Networking", "c1")`, `("  ", None)`, `("Help", "c9")` →
  texts `[b1 "x", b2 ""]`; missed `[Missed(id="m1", text="Networking", container="c1"), Missed(id="m2", text="Help",
  container=None)]`; counts `{"second_text": 1, "text_unknown_box": 1, "text_not_target": 1, "text_missing": 1,
  "missed_empty": 1, "missed_unknown_container": 1}`. With `p.texts = None` → `texts is None` and no `text_missing`.
- `::test_every_target_ends_up_exactly_once`: for each case above, `sorted(a.box for a in assign) + sorted(unassigned)`
  is a permutation of `targets`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_proposal.py tests/test_annotate_repair.py -q`.
  Expected: FAIL (`No module named scry.annotate.repair`).
- [ ] **Step 2:** Implement `to_proposal` for arm A and rules 1–19.
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

**What changes** is accounting, one re-homed helper and one predicate. **This plan owns these changes and
`tests/fakes.py`** (IA8): plan 3 uses them and re-defines none of them; it depends on nothing else of this plan, so it
may be executed ahead of Tasks 1–7 if plan 3 needs it.

**Files:**
- Create: `tests/fakes.py`
- Modify: `src/scry/providers/anthropic_.py`, `src/scry/providers/batch.py`, `src/scry/providers/base.py`,
  `src/scry/providers/__init__.py` (re-export), `src/scry/costs.py`, `tests/test_provider.py`, `tests/test_batch.py`,
  `tests/test_costs.py`

**Interfaces:**
- Produces, in `scry.costs`: `USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens",
  "cache_creation_input_tokens")`; `CACHE_WRITE_MULTIPLIER = 1.25`; `BATCH_MULTIPLIER = 0.5`; `add_usage(total: dict,
  usage: dict) -> dict`; `estimate_cost(usage: dict, model: str, batch: bool = False) -> float`.
- Produces, in `scry.providers.base` and re-exported by `scry.providers`: `is_transient(error: str | None) -> bool`.
- Produces, in `scry.providers.batch`: `async run_with_batches(run: Run, cfg: Config, provider, stage_fn) -> list`.
- `AnthropicProvider.stats` gains the key `"usage_lost"` (starts at 0).
- Produces, in `tests/fakes.py` (imported as `from fakes import …`, IA9): `FakeMessages(script)` and
  `fake_client(script)`, moved from `tests/test_provider.py` unchanged except that a script item may carry `"usage":
  {…}` (absent: `input_tokens 10, output_tokens 5`, both cache counts 0); `USAGE = {"input_tokens": 100,
  "output_tokens": 20, "cache_read_input_tokens": 1000, "cache_creation_input_tokens": 400}`; `class
  AnswerProvider(answer: Callable[[dict], BaseModel | str])` with `model = "fake-model"`, `calls: list[dict]`, `stats =
  {"hits": 0, "misses": 0}`, whose `async def complete(**kw)` records `kw`, calls `answer(kw)` and returns
  `VlmResult(parsed, None, dict(USAGE))` for a model or `VlmResult(None, error, dict(USAGE))` for a string;
  `call_frame(kw: dict) -> int`, the number after the word `frame` in the call's first text block.

**Rules:**
1. `estimate_cost = (input × p_in + output × p_out + cache_read × p_cache + cache_creation × p_in × 1.25) / 1e6`, times
   0.5 when `batch`, rounded to 4 places. The provider asks for the default five-minute cache, whose writes cost
   1.25 × the input price; today's function drops them (open item "Usage accounting"; principle 9). An unknown model
   uses the `claude-opus-5` prices, as today, and logs one warning per model name per process, so a mispriced run is
   visible (plans 3 and 4 rely on the fallback, IA12).
2. `add_usage` adds the four keys (absent or `None` counts 0) into `total` and returns it.
3. `AnthropicProvider.complete` returns, accounts (`usage_by_stage`) and caches the **sum** of the usage of every
   `_call` it made for the request. Today a `max_tokens` retry and a schema retry replace the first attempt's result,
   so a billed attempt disappears from the record.
4. **The sum is complete only for attempts that return a response.** `messages.parse` validates the reply's text
   inside the SDK, so a reply truncated at `max_tokens` with text in it, or a refusal whose text is not JSON, raises
   there; `_call` reports `schema: …` with empty usage and the billed tokens of that attempt are lost. The provider is
   not restructured to recover them (D23). Each time `_call` catches `ValidationError` or `ValueError` from
   `messages.parse` it adds 1 to `stats["usage_lost"]`: an upper bound on the attempts whose usage is missing.
5. `BatchRunner.run_pending` records all four usage keys of a succeeded result (today it omits
   `cache_creation_input_tokens`).
6. `is_transient(error)` is true when `error` starts with `"api:"` or equals `"max_tokens"`: exactly the outcomes
   `complete` does not store in the call cache (it stores successes, `refusal` and `schema…`; the batch path also
   stores its own terminal errors). A stage uses it to decide whether its last run is worth repeating (D30).
7. `run_with_batches` is the tag's `perceive._run_with_batches`: one event loop for the stage; with `cfg.model.mode ==
   "batch"` and a provider that has `collecting`, run `stage_fn(run, cfg, provider)` once collecting, `await
   provider.run_batches(run)`, then run `stage_fn` again (all cache hits) and return that result; otherwise run it once.
   Afterwards, also when `stage_fn` raised, when `provider` has a `client` with an awaitable `close`, await it inside
   the loop (open item: "Event loop is closed" tracebacks). A provider is therefore used for one stage run, which
   holds because each stage builds its own.

**Tests to write first:**
- `tests/test_costs.py::test_estimate_cost_prices_cache_writes`: `{"input_tokens": 1_000_000, "output_tokens": 100_000,
  "cache_read_input_tokens": 2_000_000, "cache_creation_input_tokens": 1_000_000}` with `"claude-opus-5"` → `14.75`
  (5 + 2.5 + 1 + 6.25); with `batch=True` → `7.375`; `dict(USAGE)` with `"fake-model"` → `0.004` ((500 + 500 + 500 +
  2500) / 1e6). The existing `test_estimate_cost` (`7.5`) still passes.
- `::test_add_usage`: `add_usage({"input_tokens": 1}, {"input_tokens": 2, "cache_creation_input_tokens": None,
  "output_tokens": 3})` → `{"input_tokens": 3, "output_tokens": 3, "cache_read_input_tokens": 0,
  "cache_creation_input_tokens": 0}`.
- `tests/test_provider.py::test_usage_sums_over_retries`: script `[{"parsed": None, "stop": "max_tokens"}, {"parsed":
  Out(answer="b"), "usage": {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 0,
  "cache_creation_input_tokens": 7}}]` → `r.usage == {"input_tokens": 20, "output_tokens": 10,
  "cache_read_input_tokens": 0, "cache_creation_input_tokens": 7}`; `p.usage_by_stage["s"]` equals it;
  `p.stats["usage_lost"] == 0`; a second identical `complete` is a cache hit with the same usage. **And the gap, made
  visible** (the executability review's values): a fresh provider with the script `[ValueError("1 validation error"),
  {"parsed": Out(answer="c"), "usage": {10, 5, 0, 7 as above}}]` → `r.parsed.answer == "c"`, `r.usage ==
  {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 7}` (the first
  attempt contributes nothing) and `p.stats["usage_lost"] == 1`.
- `tests/test_provider.py` imports the fakes with `from fakes import FakeMessages, fake_client`; its five existing
  tests keep their expectations, except that `test_transient_api_error_is_not_cached` compares `p.stats["hits"]` and
  `p.stats["misses"]` instead of the whole dict and additionally asserts `is_transient(r1.error)`, `is_transient(
  "max_tokens")`, and that `is_transient` is false for `None`, `"refusal"` and `"schema: x"`.
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
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `fix(providers): price cache-creation tokens, sum usage over retries and batch results, count lost usage; run_with_batches; is_transient`

### Task 9: The `annotate` stage, every frame, and `scry annotate`

**Files:**
- Create: `src/scry/annotate/stage.py`, `tests/test_annotate_stage.py`
- Modify: `src/scry/annotate/__init__.py` (exports `run_annotate`), `src/scry/cli.py`

**Interfaces:**
- Consumes: Tasks 1–8; `get_provider`, `VlmProvider`, `is_transient`; `config_hash`; `margin_px` (IA5);
  `textdiff.similarity`.
- Produces: `run_annotate(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None`, writing
  `annotations.jsonl` and `overlays/NNNNN.png`; `mark_match(annotations: list[Annotation], frames: list[FrameBoxes],
  threshold: float = 0.8) -> tuple[int, int]`; CLI `scry annotate RUN_DIR [--config PATH] [--verbose]`; `STAGES ==
  ["decode", "outline", "read", "track", "annotate"]` (the shared stage order, IA9: `outline` moves behind `decode`) and
  `scry run` runs `annotate` after `track` (manifest key `annotate`).

**Rules:**
1. `mode == "off"` (the "no annotation" base, §2, §9 P1): delete `annotations.jsonl` if it exists (D25), write the
   manifest entry with `skipped = True`, `frames` = the number of emitted frames, `calls = 0`, `usage` = four zeros,
   `cost_usd = 0.0`, `model = cfg.model.model`, and return. No provider is created and nothing is drawn.
2. Inputs `[run.frames, run.boxes]`; config hash `config_hash(cfg, "annotate", "model", "overlay", "track")` +
   `prompt_version(…)`. The stage returns without work when `run.stage_up_to_date("annotate", …)` holds,
   `annotations.jsonl` is present **and the manifest entry's `transient_errors` is 0** (D30). Otherwise it runs in full:
   every call that was answered before, refusals and schema failures included, is a cache hit, so a rerun after an API
   error or a truncation pays only for the calls that failed; nothing else changes, because no call depends on
   another (D6).
3. Frames in `frames.jsonl` order; a frame without a `boxes.jsonl` record → `ValueError("… run `scry read` first")`.
   Plans from `plan_calls(frame_boxes, [], [], "every_frame")` (Task 15 adds the incremental branch).
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
   whole stage runs under `run_with_batches`, so `[model] mode = "batch"` works unchanged, in every annotate mode (D6).
8. Records sorted by frame, written with `write_jsonl`. The stage reads no other stage's output but `frames.jsonl` and
   `boxes.jsonl`, and writes no file but its own and its overlays.
9. `mark_match` (the check that caught unreadable tags, L28–L30; D29) returns `(hits, total)` over the texts of
   successful transcribing records: a text counts when it is not empty after stripping and its `box` is a box of the
   record's frame; it is a hit when `textdiff.similarity(that box's OCR text, text) ≥ threshold`. The 0.8 is the
   design's diagnostic constant (§18.4, L30); no pipeline decision rests on it. Under arm C the box was chosen by code
   (the snap), so there it measures the snap.
10. Manifest `stages.annotate`: `mode`, `arm` (`"A"` until Task 12), `transcribe`, `prompt_version`, `model`, `frames`
    (emitted frames), `calls` (records), `boxes` (boxes over the call frames), `targets`, `errors`, `transient_errors`
    (records whose `error` `is_transient`), `failed_targets` (targets of records with an error), `repairs`,
    `repair_counts` (summed by key), `label_clashes`, `mark_match` (`{"hits": h, "total": t}` when transcribing, else
    `None`), `usage` (the four keys, `add_usage` over the records, so cache hits count: the cost is what a cold run
    would pay, D23), `usage_lost` (`getattr(provider, "stats", {}).get("usage_lost", 0)`: attempts of this run whose
    billed usage never reached the record; 0 in batch mode and for a run served from the cache), `cache` (the
    provider's `stats`), `cost_usd =
    estimate_cost(usage, model)`, `cost_usd_batch = estimate_cost(usage, model, batch=True)`, `cost_per_frame_usd` and
    `cost_per_frame_usd_batch` (÷ `frames`, 5 places, `None` with no frames), `cost_per_call_usd` (÷ `calls`, 5 places,
    `None` with no calls). Spec §9: "cost beside every number: dollars per frame". No projection to the sample's 221
    frames is computed in code. Repeats for the evidence rules are separate run directories made with `scry subset
    --no-share-cache`, as in L42; there is no repeat key.

**Tests to write first** (Fixture E through `write_run`; `AnswerProvider`; the standard answer for a frame *n* is one
window `c1` (app "x", name "w", owner null, covers []), `b1→c1`, `b2→c1`, `unassigned []`, no runs, one pair `key [b1]
value [b2]`, no records, texts `b1 "a"`, `b2 "B"`, no missed, description `"d<n>"`, built with `kw["output_model"]`):
- `test_every_frame_arm_a_end_to_end`: two records; record 0 has `targets ["b1", "b2"]`, one container, two assigns,
  `links == [PairLink(key=["b1"], value=["b2"])]`, `texts == [TextReading(box="b1", text="a"), TextReading(box="b2",
  text="B")]`, `description "d0"`, `repairs 0`, `repair_counts {}`, `label_clashes 0`, `model "fake-model"`,
  `prompt_version "annotate-v1"`, `error None`; each call had `stage "annotate"`, `effort "low"`, `system ==
  system_prompt()`, `output_model is output_model("A", True)`, two image blocks; `overlays/00000.png` and
  `overlays/00001.png` exist and are 128×64; manifest `frames 2`, `calls 2`, `boxes 4`, `targets 4`, `errors 0`,
  `transient_errors 0`, `usage_lost 0`, `mark_match {"hits": 2, "total": 4}` (`"a"` against `"a"` is 1.0; `"B"` against
  `"b"` is 0.0: one substitution in one character), `usage == {"input_tokens": 200, "output_tokens": 40,
  "cache_read_input_tokens": 2000, "cache_creation_input_tokens": 800}`, `cost_usd 0.008`, `cost_usd_batch 0.004`,
  `cost_per_frame_usd 0.004`, `cost_per_call_usd 0.004`.
- `test_group_only`: `transcribe = false` → `system == system_prompt(transcribe=False)`, `output_model is
  output_model("A", False)`, `prompt_version "annotate-v1+grouponly"`, `record.texts is None`, `record.missed == []`,
  manifest `mark_match is None`.
- `test_repairs_are_counted_not_fatal`: the answer assigns `b9→c1` instead of `b2→c1` → each record has `unassigned
  ["b2"]`, `repairs 2`, `repair_counts {"unknown_box": 1, "unplaced": 1}`, and still `links == [PairLink(key=["b1"],
  value=["b2"])]`: the slip in `assign` does not cost the link (D14); manifest `repairs 4`.
- `test_error_record_and_the_run_continues`: the answer for frame 1 is the string `"refusal"` → record 1 has `error
  "refusal"`, `targets ["b1", "b2"]`, `description None`, `texts None`, `links []`; record 0 is whole; manifest `errors
  1`, `transient_errors 0`, `failed_targets 2`; a second `run_annotate` makes no call (a refusal is final).
- `test_transient_error_is_retried_on_the_next_run`: the answer for frame 1 is the string `"api: APIConnectionError:
  down"` → record 1 has that `error`; manifest `errors 1`, `transient_errors 1`. A second `run_annotate`, unchanged
  config, with a provider that answers both frames → it runs (the `AnswerProvider` has no cache, so it sees 2 calls;
  with the real provider the answered frame is a cache hit), record 1 is whole, manifest `errors 0`,
  `transient_errors 0`; a third run makes no call.
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
- `test_mark_match` (Fixture T's records and frames, no stage run): `[A10, A11]` → `(6, 6)` (`"PS C:\> a"` against
  `"PS C:\> az"` is 1 − 1/10 = 0.9); with `A11`'s text for `b1` replaced by `"PowerShell 7"` → `(5, 6)`; an empty text
  and a group-only record count nothing.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_stage.py -q`. Expected: FAIL (`ImportError:
  run_annotate`).
- [ ] **Step 2:** Implement rules 1–10 and the command.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry --help` lists `annotate`.
- [ ] **Step 4:** Commit: `feat: annotate stage: one call per frame proposing containers, links, a second reading and a description; cost per frame and mark_match in the manifest`

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
              pane: str | None · link: BoxLink | None · vlm: str | None · agree: bool | None · non_text: bool
FrameLabel    containers: list[Container] = [] · links: list[Link] = [] (box refs of that frame) ·
              description: str | None = None · description_frame: int | None = None · missed: list[Missed] = []
Labels        box(ref: str) -> BoxLabel | None · frame(frame: int) -> FrameLabel · lifetime(id) (Task 11) ·
              relinked: int
build_labels(annotations: list[Annotation], frames: list[FrameBoxes], lifetimes: list[Lifetime]) -> Labels
Run.load_labels() -> Labels | None                  # None when annotations.jsonl is absent or holds no record
```

**Rules (spec §2 "loaders join labels onto measured records on read"; §5; D3, D15, D16).** A record is *successful*
when its `error` is `None`. One set of rules serves every-frame and incremental records; the join never asks which
mode wrote them.
1. **Source: a box's labels are resolved through its lifetime to the record that labelled it.** The source of box
   *(f, b)* is *(f, b)* itself when frame *f* has a successful record with *b* among its targets; otherwise the latest
   earlier box *(g, y)* of the same lifetime, `g < f`, for which that holds; otherwise none, and `Labels.box` returns
   `None`. With `lifetimes == []` nothing is carried. A ref that is not in `frames` → `KeyError`.
2. **Box labels** come from the source record *g* and its box *y*: `container` is the record's container named by
   *y*'s assign entry (`None` when *y* is unassigned), `pane` from the same entry; `vlm` is *y*'s text in `texts`
   (`None` when the record did not transcribe or has no entry); `non_text = vlm is not None and vlm.strip() == ""`;
   `agree` is `None` when `vlm` is `None` or `non_text`, else `agreement(OCR text of (g, y), vlm)` — both readers read
   frame *g*'s pixels. Container ids are local to a record (D3): two boxes are in the same container when their
   sources lie in the same frame's record and their containers have the same id. Readers group by that pair and never
   compare ids across records.
3. **`agreement`** (today's rule, D26): true when `norm(ocr) == norm(vlm)`; else, when `ocr.split()` has at least two
   tokens, true when the first token has at most `glyph_max_len` characters and `norm` of the rest equals `norm(vlm)`,
   or the same with the last token; else false. `norm` collapses whitespace and straightens quotes and nothing else, so
   `azconfigure` against `az configure` disagrees, as it must (L43). It only flags; no recorded text is altered.
4. **Links: accepted once, then in force.** Successful records are taken in frame order, each record's links in stored
   order. A link of record *g* is *accepted* unless one of its members (not its header, D13) is, at frame *g*, a member
   of a link of an earlier record that is in force at *g*: then the earlier link stands, the later one is refused for
   good, and `Labels.relinked` grows by 1 (D15: a box that has a link is never re-labelled). An accepted link of
   record *g* is *in force* at frame *f ≥ g* when every id in `link_refs` maps to a box of *f* through its lifetime
   (the box itself when `f == g`) and, for every member that was a target of *g*, the source of its mapped box is
   still that member in *g*. So every-frame records never pile up (at *f* every box draws from *f*'s record, so no
   earlier link is in force and none is refused), and an incremental link lasts exactly as long as the boxes it names.
5. `FrameLabel.links` are the links in force with every id written as a box ref of *f*, in record order then stored
   order. `BoxLabel.link` is the link in force of which the box is a member, with its role (`run`, `key`, `value`,
   `member`); failing that the first link in force that names it in `header` (role `header`); failing that `None`.
6. **Screen-level labels are those of the latest successful record at or before the frame.** Let *r* be the latest
   successful record with `frame ≤ f`. If there is none: `FrameLabel()`. Otherwise `containers`, `description` and
   `missed` are *r*'s, with `description_frame = r.frame`: a frame without a call shows the previous description (spec
   §2), a failed call changes nothing, and the frame number says how old the labels are. Every record lists the whole
   screen's containers, missed texts and description (Task 5 rule 6), so *r* alone suffices. A carried box's
   `BoxLabel.container` may come from an earlier record than *r* and is then no element of `FrameLabel.containers`;
   readers take a box's container from its `BoxLabel`, never by looking an id up in the frame's list.
7. `Run.load_labels()` imports this module lazily and builds from `load_annotations()`, `load_boxes()`,
   `load_lifetimes()`. Nothing here writes a file or alters a measured record.

**Tests to write first** (Fixture T with records `[A10, A11]` unless stated):
- `test_own_record_and_carried_labels`: `box("10:b4")` → `source "10:b4"`, `container.id "c2"`, `container.app
  "PowerShell"`, `vlm "PS C:\> a"`, `agree False`, `non_text False`; `box("11:b2")` → `source "10:b1"`,
  `container.app "Browser"`, `vlm "Resource group"`, `agree True`; `box("12:b5")` → `source "11:b5"`, `container.id
  "c1"`, `container.app "PowerShell"` (the id is `A11`'s own), `vlm "PS C:\> az login"`, `agree True`; `box("12:b4")`
  → `source "10:b3"`, `container.id "c2"`, `container.app "PowerShell"`: the same window as `12:b5`, labelled by
  another record under another id, which is all D3 promises; `box("12:b1")` → `source "11:b1"`, `container.app
  "Browser"`.
- `test_links_in_force`: `frame(10).links == [PairLink(key=["10:b1"], value=["10:b2"])]`; `frame(11).links ==
  [PairLink(key=["11:b2"], value=["11:b3"]), RunLink(boxes=["11:b4", "11:b5"], joiner=" ")]`: `A11`'s pair names
  `11:b2`, which `A10`'s pair still holds, so it is refused; `labels.relinked == 1`. `frame(12).links` is the same with
  `12:` refs; `box("12:b3").link == BoxLink(kind="pair", role="value", key=["12:b2"], value=["12:b3"])`;
  `box("12:b4").link.role == "run"`; `box("12:b1").link is None`.
- `test_a_link_ends_with_its_lifetimes`: `A10` with the extra link `run [b3, b4] ""` → `frame(10).links` has two
  links; `frame(11).links` does not contain that run (`L4` has no box on frame 11), and `A11`'s run over `11:b4` is
  accepted all the same (the ended run is not in force at 11): `labels.relinked == 1`, as before.
- `test_screen_level_labels`: `frame(10)` → description `"d10"`, `description_frame 10`, missed texts
  `["Networking"]`, container apps `["Browser", "PowerShell"]`; `frame(12)` → `"d11"`, `11`, `[]`, `["PowerShell",
  "Browser"]` (`A11`'s own list); `frame(9)` → `FrameLabel()`.
- `test_failed_record_is_not_a_source`: `A11` replaced by a record of frame 11 with `targets ["b1", "b5"]` and `error
  "refusal"` → `box("11:b5") is None`, `box("12:b5") is None`, `box("11:b2").source == "10:b1"`;
  `frame(11).description == "d10"` with `description_frame 10`, and the same at frame 12 (the latest successful
  record); `frame(11).links == [PairLink(key=["11:b2"], value=["11:b3"])]`.
- `test_every_frame_records_do_not_pile_up`: records `A10` and a full `A11f` (every box of frame 11 a target;
  containers `c1`, `c2`; `b1, b2, b3 → c1`, `b4, b5 → c2`; no links) → `box("11:b2").source == "11:b2"`,
  `frame(11).links == []`, `labels.relinked == 0`.
- `test_agreement`: `("区 Overview", "Overview")` true; `("Overview >", "Overview")` true; `("ab Overview",
  "Overview")` true; `("abc Overview", "Overview")` false; `("az configure", "azconfigure")` false; `("PS  C:\> az",
  "PS C:\> az")` true; `("“x”", '"x"')` true.
- `test_non_text_and_group_only`: a text `""` → `vlm ""`, `non_text True`, `agree None`; a record with `texts None` →
  `vlm None`, `agree None`, `non_text False`.
- `test_without_lifetimes_nothing_is_carried`: `build_labels([A10], frames, [])` → `box("11:b2") is None`,
  `box("10:b1").source == "10:b1"`.
- `test_load_labels`: a run without `annotations.jsonl` → `None`; with `[A10, A11]` written → a `Labels`;
  `box("99:b1")` raises `KeyError`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_join.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): the joined view: labels per box and per frame, resolved through lifetimes (spec §5)`

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
               container: Container | None · links: list[LifetimeLink] = []
Labels.lifetime(lifetime_id: str) -> LifetimeLabel | None
```

**Rules (spec §5: "per lifetime the model's majority reading"; §6 `index`; principle 5: record, do not pick):**
1. `vlm_readings` counts, exactly as returned, the text of every box of the lifetime that was a target of a successful
   transcribing record and has a text there. Under every-frame annotation that is one reading per sighting; under
   incremental annotation one in all.
2. `non_text` is true when there is at least one reading and every reading is empty after stripping. `vlm` is the
   non-empty reading with the highest count, a tie going to the reading seen first in frame order (IA11), `None` when
   there is none. `agree` is `None` when `vlm` is `None`, else `agreement(lifetime.text, vlm)`: the two majority
   readings compared.
3. `container` is that of the lifetime's latest labelled box (an object of that box's source record, D3).
4. Every accepted link (Task 10 rule 4) of every successful record is mapped to lifetime ids. Relations equal in kind,
   joiner and structure of lifetime ids are one `LifetimeLink`, with `records` = how many records proposed it and
   `first_frame` the first. Nothing is picked: a lifetime that was paired in 20 records and put in a run in 1 has both,
   with their counts. A lifetime's `links` are all those naming it, header included, ordered by `first_frame` then
   stored order.
5. `Labels.lifetime` returns `None` for a lifetime with no labelled box and no link; an unknown id → `KeyError`.
   How long a lifetime lasted is not read anywhere here.

**Tests to write first** (Fixture T):
- `test_lifetime_labels_incremental` (`[A10, A11]`): `lifetime("L2")` → `vlm "RG1"`, `vlm_readings {"RG1": 1}`, `agree
  True`, `non_text False`, `container.app "Browser"`, `links == [LifetimeLink(kind="pair", key=["L1"], value=["L2"],
  records=1, first_frame=10)]`; `lifetime("L4")` → `vlm "PS C:\> a"`, `agree False`; `lifetime("L6").links ==
  [LifetimeLink(kind="run", boxes=["L3", "L6"], joiner=" ", records=1, first_frame=11)]` and `lifetime("L3").links` is
  equal to it; `lifetime("L5").links == []` (its pair was refused) while `lifetime("L5").vlm == "Banner"`.
- `test_majority_over_every_frame_records`: full records `A10`, `A11m`, `A12m` (frames 11 and 12: every box a target,
  one window `c1` holding every box, the pair `key [b2] value [b3]`, a text per box equal to its OCR text except that
  `b3` reads `"RG1"` in `A11m` and `"RGl"` in `A12m`) → `lifetime("L2").vlm_readings == {"RG1": 2, "RGl": 1}`, `vlm
  "RG1"`, `agree True`, `links[0].records == 3`, `links[0].first_frame == 10`.
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

Tasks 12–15 are the evaluation switches (spec §10 step 8). They land after P1 and change no default. "Order of work"
above lists what each needs.

### Task 12: Arms B, C and D: config, schemas, prompts, user turn

**Needs:** Tasks 1, 5, 6, 7, 9.

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
OutContainerRect  OutContainer's fields + rect: OutRect
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
| D | arm A's classes: `output_model("D", …) is output_model("A", …)` | | | | |

Six classes (`AnnotateOut` + `A`, `B`, `C` + `T`/`G`), six schema hashes. Arm D asks for exactly what arm A asks for, so
it has no class of its own; its calls are kept apart in the cache by `+D` in the prompt version and by the user turn.
The `rect` field carries no description of its own: the SDK's transform drops a description beside a `$ref` (D2), so
the containers paragraph and `OutRect`'s integer fields say what it is.

**Prompt paragraphs that differ from arm A** (spec §6's table; each is a whole paragraph; anything not listed is arm
A's paragraph, character for character; no example in them comes from the evaluated video).

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
*Arm C, paragraph 5 (`links`), in full (arm A's with points for box ids; arm C has no targets):*
```
links: relations between pieces of text of one container, given as three lists of points. A piece of text belongs to at most one run, pair or record; column headings are the exception and may be named by every record of their table.
  runs: pieces of text that are one continuous piece of text which the screen wrapped onto the next line, in reading order, one point each. joiner is "" when a word was cut in two by the wrap, " " otherwise.
  pairs: a label and its value (a property and its value, a form field and its content). key and value are lists of points. A two-column grid of labels and values is pairs, not records.
  records: one row of a table with three or more columns: members, left to right, each a list of points; header, the points of the column headings when they are visible, otherwise [].
Pieces of text that merely sit side by side stand alone: tabs, toolbar buttons, menu items, breadcrumbs.
```

*Arm C, paragraph 6 (`texts`):*
```
texts: for every piece of text on screen, one entry per run of text on one visual line (a label, a button, a menu item, a table cell, a command line together with its prompt): a point inside it and its verbatim text. Preserve case, punctuation, whitespace and symbols. Never correct, complete or normalize commands, code, paths or identifiers. Use ? for a character you cannot resolve. An icon is not text: leave it out.
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
3. Arm C: `Screenshot (…):`, the clean frame, `COORDS`; when some box has `in_churn`: `Animating areas (low
   confidence), as x0,y0,x1,y1: …` (those boxes' rectangles in reading order, joined by `; `); the unsettled line; the
   final line. No box ids and no target line: under arm C every box is a target (D28).
4. Arms C and D send no overlay: `overlay_png` is `None`, the stage draws none, and `input_hashes[1] == "-"`.
5. The stage's manifest entry records the arm.

**Tests to write first:**
- `test_config.py::test_arm_key`: default `"A"`; `arm = "E"` raises `pydantic.ValidationError`.
- `test_annotate_output.py::test_fields_per_arm`: B transcribing → `["containers", "runs", "pairs", "records", "texts",
  "missed", "description"]`; C transcribing → `["containers", "runs", "pairs", "records", "texts", "description"]`;
  `output_model("D", True) is output_model("A", True)`; the group-only lists lack `texts` and `missed`.
  `test_schema_is_strict_friendly` now covers all six classes, and their six `sha256_obj(model_json_schema())` differ.
- `test_annotate_prompt.py::test_variants_differ_only_where_intended` (the one test of paragraph structure; Task 14
  extends it): every prompt has 7 paragraphs; B differs from A exactly at indices `{2, 3}`; C from A at `{1, 2, 3, 4,
  5}`; C from B at `{1, 4, 5}`; D from A at `{1, 5}`; group-only D from group-only A at `{1}`; the C prompt contains
  neither `box id` nor `Image 2`. `::test_versions` gains `prompt_version("B") == "annotate-v1+B"` and
  `prompt_version("C", False, scale=0.5) == "annotate-v1+C+grouponly+s0.5"`. `::test_no_sample_video_content` covers
  every arm.
- `test_annotate_blocks.py::test_arm_b_c_d_blocks` (Fixture E, frame 0): B → the texts after the images are `COORDS`
  for 128x64, `"Boxes: b1, b2."`, `"Targets: all boxes."`, `"Return the JSON object."`; C → block types `[text, image,
  text, text]`, and with `b1.in_churn` a fourth text `"Animating areas (low confidence), as x0,y0,x1,y1: 4,4,40,20."`
  before the final line; D → the texts are `"Screenshot (frame 0, t=0.00s):"`, `COORDS`, `"Boxes, as id: x0,y0,x1,y1 in
  reading order: b1: 4,4,40,20; b2: 70,4,110,20."`, `"Targets: all boxes."`, `"Return the JSON object."`.
- `test_annotate_stage.py::test_arm_d_end_to_end`: `arm = "D"` with the standard answer → records as in arm A,
  `prompt_version "annotate-v1+D"`, one image block per call, no file in `overlays/`, manifest `arm "D"`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_output.py tests/test_annotate_prompt.py
  tests/test_annotate_blocks.py tests/test_annotate_stage.py tests/test_config.py -q`. Expected: FAIL.
- [ ] **Step 2:** Add the key, the models, the paragraphs (copied from this task) and rules 1–5.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): referencing arms B, C, D: schemas, prompts and user turns (spec §6)`

### Task 13: Arms B and C in code: centre-inside, front-most, snapping

**Needs:** Tasks 12, 7, 9.

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
5. **Boxes are assigned after container repair** (D1). `to_proposal` for arms B and C sanitises the rectangles (rule
   2), passes the containers through `repair_containers` (Task 7 rules 1–4: a repeated id is dropped, owners and
   `covers` are cleaned; counted there) and only then assigns: for each box of the frame in reading order,
   `container_at(centre(box))` over the repaired list → an `Assign`, or `unassigned` with `outside` or `ambiguous`
   counted. `repair` later finds the containers already clean and counts nothing twice. Under arm B links, texts and
   missed come by id as in arm A.
6. Arm C: assign as arm B. Every point of a link is snapped over all boxes of the frame; a link with a point that
   snaps to nothing is dropped (`link_unsnapped`); repair then judges the ids as usual, so two points falling in one
   OCR box make the link malformed (spec §5: a key and value in one box can never be a pair). Each `OutTextAt` is
   snapped the same way: a hit is `TextReading(box, text)`; a miss becomes a missed text `(text, container_at(point)
   when "ok" else None)` (D17).

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
  no `c3` → `b6` in `unassigned`, counts `{"outside": 1}`. **A container id used twice** (rule 5): `c1` rect
  `(0,0,250,90)`, `c2` rect `(250,0,400,200)`, and a second container with id `c2`, a popup with rect
  `(140,90,300,130)` → the duplicate is dropped before any box is assigned, so `b6`, whose centre `(190, 108)` lies
  only in the duplicate's rectangle, is `unassigned`; containers `["c1", "c2"]`; counts `{"dup_container": 1,
  "outside": 1}` (assigning first would have put `b6` into the first `c2`, whose rectangle does not hold it).
- `::test_arm_c_points`: an `AnnotateOutCT` answer with `c1` and `c2`, the pair `key [(50, 48)] value [(180, 48)]`, the
  run `boxes [(325, 18), (600, 18)] " "`, texts `at (325, 48) "PS C:\> az login"` and `at (30, 150) "Networking"` →
  links `[PairLink(key=["b3"], value=["b4"])]`; texts `[TextReading(box="b5", text="PS C:\> az login")]`; missed
  `[("Networking", "c1")]`; assign `[b1→c1, b2→c2, b3→c1, b4→c1, b5→c2, b6→c1]`; counts `{"link_unsnapped": 1}`
  (`(600, 18)` is 210 px from `b2`).
- `test_annotate_stage.py::test_arm_b_end_to_end` (Fixture S written as a one-frame run; the first answer of
  `test_arm_b_assigns_by_centre` plus the pair `key [b3] value [b4]` and a text per box equal to its OCR text): the
  record has the six assigns, `containers[0].rect == (0, 0, 250, 200)`, `links == [PairLink(key=["b3"],
  value=["b4"])]`, `repairs 0`, `prompt_version "annotate-v1+B"`, and `overlays/00007.png` exists.
  `::test_arm_c_end_to_end` (the answer of `test_arm_c_points`): `missed == [Missed(id="m1", text="Networking",
  container="c1")]`, `repair_counts == {"link_unsnapped": 1, "text_missing": 5}`, one image per call, no overlay file.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_geometry.py tests/test_annotate_proposal.py
  tests/test_annotate_stage.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): arms B and C: containers repaired, then boxes assigned by centre with the front-most container winning; points snapped within the margin`

### Task 14: The pane label (P4)

**Needs:** Task 12 (the validator reads the `arm` key), Tasks 5, 7, 9, 10.

**Files:**
- Modify: `src/scry/config.py`, `scry.toml`, `src/scry/annotate/output.py`, `src/scry/prompts/annotate.py`,
  `src/scry/annotate/stage.py`, and the tests `test_config.py`, `test_annotate_output.py`, `test_annotate_prompt.py`,
  `test_annotate_stage.py`, `test_annotate_join.py`

**Interfaces:**
- Produces: `AnnotateConfig.pane: bool = False`; a validator: `pane = true` with arm B or C raises `ValueError("pane
  needs arm A or D")` (D12). `OutAssignPane` = `OutAssign` + `pane: str | None` ("Short name of the area of its window
  the box sits in, or null."); `output_model(arm, transcribe, pane=True)` for arms A and D, the two classes
  `AnnotateOutATP` and `AnnotateOutAGP`; `system_prompt(…, pane=True)`; version suffix `+pane`.

**Rules (spec §3: "pane is at most a label string"; §9 P4):**
1. With a pane the `assign` paragraph is this whole paragraph instead (arm A's sentence, then the pane's):
```
assign: for every target box id, the container it belongs to. Every target appears exactly once, or in unassigned. pane: a short name for the area of its window the box sits in (title bar, tab strip, toolbar, sidebar, editor, terminal, status bar), or null when the window has no distinct areas or the container is a popup. A pane is only a name: never list a pane as a container.
```
2. The string is stored on the `Assign` entry (empty after stripping → `None`), joined as `BoxLabel.pane`, and read by
   nothing mechanical: it is never a container, never diffed, never an id (L31: panes split 8 ways on one frame and 3
   on the next).

**Tests to write first:**
- `test_config.py::test_pane_key`: default `False`; `pane = true` with `arm = "B"` or `"C"` raises; with `"D"` loads.
- `test_annotate_output.py::test_pane_variant`: `output_model("A", True, True).__name__ == "AnnotateOutATP"`; its
  `assign` items have the properties `box`, `container`, `pane`, all required; `output_model("D", True, True)` is the
  same class; `output_model("B", True, True)` raises `ValueError`; the strict-friendly test covers the two pane
  classes.
- `test_annotate_prompt.py::test_variants_differ_only_where_intended` gains: with and without a pane the prompts
  differ only at index 3, and the pane paragraph starts with the plain one. `::test_versions` gains
  `prompt_version(pane=True) == "annotate-v1+pane"` and `prompt_version("D", False, True, 0.5) ==
  "annotate-v1+D+grouponly+pane+s0.5"`.
- `test_annotate_stage.py::test_pane_is_stored`: `pane = true`; the answer gives `b1` the pane `"title bar"` and `b2`
  `"  "` → `assign[0].pane == "title bar"`, `assign[1].pane is None`, `prompt_version "annotate-v1+pane"`.
- `test_annotate_join.py::test_pane_is_joined`: Fixture T with `A10`'s assign for `b1` given the pane `"terminal"` →
  `box("10:b1").pane == "terminal"`, and the carried box `"11:b2"` has it too.

- [ ] **Step 1:** Write the tests. Run the five test files with `-q`. Expected: FAIL.
- [ ] **Step 2:** Implement the key, the class, the paragraph and the suffix.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): optional pane label string on assign entries, arms A and D (P4)`

### Task 15: Incremental annotation

**Needs:** Tasks 3, 9, 10, and 12 (the validator reads the `arm` key). It also edits plan 1's `src/scry/metrics.py`,
`src/scry/report.py` and `tests/test_metrics.py` (rule 6).

An incremental call is the every-frame call with a shorter target list (D6). Tasks 3, 5, 6, 7 and 10 already hold
every rule it needs: the planner names the targets, the prompt and the user turn speak of targets, repair refuses
labels for boxes that are not targets, and the join resolves a box's labels through its lifetime. What is left is the
switch, its two inputs and the manifest.

**Files:**
- Modify: `src/scry/config.py`, `src/scry/annotate/stage.py`, `src/scry/metrics.py`, `src/scry/report.py`, and the
  tests `test_config.py`, `test_annotate_stage.py`, `test_metrics.py`

**Interfaces:**
- Produces: `AnnotateConfig.mode` gains `"incremental"`; a validator: `mode = "incremental"` with arm B or C raises
  `ValueError("incremental annotation needs arm A or D")` (D28). `[model] mode = "batch"` is accepted with every
  annotate mode (D6). `scry.metrics.incremental_projection(boxes, changes, lifetimes) -> dict` (one more parameter);
  `scry.metrics.targets` is deleted.

**Rules (spec §2, §5 "targets"; D4–D7, D15, D16, D28):**
1. **The same call.** Every call of an incremental run uses the same system prompt, schema, images (the overlay
   numbers every box, D7) and prompt version as an every-frame call; only the `Targets:` line of the user turn
   differs. Nothing from any earlier answer enters a request, so the calls are independent: they run concurrently
   under Task 9's bound, in batch mode if configured, and a transient failure is retried alone (D30). The call for
   the first frame, and for a cut where every box is new, reads `Targets: all boxes.` and is byte for byte the
   every-frame call: it has the same cache key, so P3 reuses P1's paid answer for it.
2. Plans come from `plan_calls(frame_boxes, changes, lifetimes, "incremental")`; the stage's inputs gain `run.changes`
   and `run.lifetimes`; either file absent → `ValueError("… run `scry track` first")`.
3. **What the model returns:** the containers it sees, afresh, with ids local to the record (D3); `assign`, and
   `texts` when transcribing, for the targets only; links with at least one target, which may name any other box of
   the frame; `missed` and the description for the whole screen. Repair is Task 7's, unchanged: an assign or a text for
   a carried box is dropped (`not_target`, `text_not_target`), and a link is judged by its ids alone.
4. **What the join makes of it** (Task 10, unchanged): a carried box keeps the labels of the record that labelled it; a
   link that names a carried box which already has a link is refused (`Labels.relinked`, which P3 reads beside the
   risks §6 lists); the containers, missed texts and description in force at a frame are those of the latest
   successful record at or before it.
5. Manifest addition: `skipped_frames` (emitted frames without a call). `cost_per_frame_usd` still divides by all
   emitted frames, which is how incremental annotation's saving shows (§9: cost per frame beside every number).
6. **One rule, one implementation (the named step of IA10).** `incremental_projection(boxes, changes, lifetimes)` takes
   its calls and targets from `plan_calls(boxes, changes, lifetimes, "incremental")`: `calls` = the number of plans,
   `target_boxes` = the sum of their targets, `calls_without_targets` = the plans with no target; the other keys are
   computed from these as today. `scry.metrics.targets` and `test_targets` are deleted, and `report.py` passes the
   lifetimes it already selects. The counts are those of the committed rule (Task 3 rule 4), so P0's reported numbers
   stand; the one difference is that a first frame without boxes now counts as a call without targets.

**Tests to write first:**
- `test_config.py::test_incremental_mode`: `mode = "incremental"` loads, also with `[model] mode = "batch"`; with `arm
  = "B"` or `"C"` it raises `pydantic.ValidationError` matching `incremental`; with `arm = "D"` it loads.
- `test_annotate_stage.py::test_incremental_run` (Fixture T; `AnswerProvider` keyed by `call_frame`, answering frame 10
  with `A10`'s content and frame 11 with `A11`'s, each built with `kw["output_model"]`): calls are made for frames 10
  and 11 and none for 12; both used `system_prompt()`, `output_model("A", True)` and `prompt_version "annotate-v1"`;
  the call for frame 10 has the text `Targets: all boxes.` and the call for frame 11 `Targets: b1, b5.`; the records
  equal Fixture T's `A10` and `A11` in `targets`, `containers`, `assign`, `links`, `texts`, `missed`, `description` and
  `repairs` (0 in both: repair cannot know that `b2` is linked); manifest `mode "incremental"`, `calls 2`, `frames 3`,
  `skipped_frames 1`, `targets 6`; afterwards `labels = run.load_labels()` has `labels.frame(12).links ==
  [PairLink(key=["12:b2"], value=["12:b3"]), RunLink(boxes=["12:b4", "12:b5"], joiner=" ")]` and `labels.relinked ==
  1`. **Cache-key behaviour:** an every-frame run of the same fixture makes a call for frame 10 whose `blocks`' texts,
  `prompt_version` and `input_hashes` equal those of the incremental run's call for frame 10.
- `::test_incremental_needs_track`: without `lifetimes.jsonl` → `ValueError` matching `scry track`.
- `test_metrics.py::test_incremental_projection` (exists; its fixture gains one single-box lifetime for each target
  box of the later frames, one on frame 1 and twelve on frame 3, whose `boxes[0]` is the `after` box of the change
  record; the first frame's hundred boxes are targets by rule; the call passes the lifetimes): the expected values do
  not change
  — 4 calls, 1 without targets, 113 target boxes of 415, `0.2723`, `28.25`, `103.75`; with the second change's
  `components` set to 0: 3 calls, 0 without targets, 113 target boxes, `37.67`. `test_targets` is deleted.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_annotate_stage.py tests/test_config.py
  tests/test_metrics.py -q`. Expected: FAIL.
- [ ] **Step 2:** Implement rules 1–6 and the key.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(annotate): incremental annotation: the same call with only the boxes whose lifetime starts as targets; labels ride their lifetimes; the projection prices it with plan_calls (spec §2)`

### Deferred: readings assigned by position and similarity (the first draft's Task 14)

Not built. It would move a returned reading from the box the model named to a nearby box whose OCR text resembles it
more (spec §7), and with it come `readings.py`, the keys `text_assignment` and `assign_reach`, `TextReading.named` and
the counter `text_unplaced`. Its evidence, readings put on a neighbouring line (L43), was measured under the old
parallel arrays of rows and texts, which §6 already replaced by `{box, text}` objects for exactly that fault, and no
phase or matrix of plans 3 and 4 sets the switch. **What would trigger it:** P1's transcribing runs showing, in the
manifest's `mark_match` and in the by-eye reading of their records, readings that land on a neighbouring box under
the `{box, text}` schema. It is post-processing of cached answers (it changes no request and no cache key), so it can
then be added at no model cost and compared on P1's own outputs. The first draft's rules and hand-checked tests are
in commit `fbe7982`.

---

## Self-review

- **Spec coverage.** §2 stage table row `annotate`, "every stage writes only its own file" → Tasks 9, 10; incremental
  annotation (targets, the call on any pixel change, first frame and cut as one rule) → Tasks 3, 15; "no annotation" →
  Tasks 1, 9 (`mode = "off"`, D25). §3 vocabulary (container, link, `c<n>`, `m<n>`, pane as a string) → Tasks 2, 5, 14.
  §5 `annotations.jsonl` and the loader derivations (`vlm`, `agree`, `non_text`, majority per lifetime, labels from the
  own frame's record else the lifetime's latest, `rect` only under B and C, at most one link, key and value in one box
  never a pair) → Tasks 2, 7, 10, 11, 13. §6 `annotate`: the draft prompt, the transcribing paragraph, the description
  kept → Task 5; lists of objects, repair never abort → Tasks 5, 7; the four arms → Tasks 12, 13; OCR coordinates
  serving numbering, overlay, arm D's list, assignment and snapping → Tasks 4, 12, 13. §7 (record both, `agree`,
  `non_text`, `mark_match`) → Tasks 9, 10, 11; assignment by position and similarity → deferred (D18). §8 new config
  "the annotate switches" → Tasks 1, 12, 14, 15. §9 cost beside every number → Tasks 8, 9; P1's three bases are three
  config files (`transcribe = true`, `false`, `mode = "off"`); P2's arms and scales → Tasks 12, 13 and `scale`; P3 →
  Task 15; P4 → Task 14. **Departures from the spec, each in ledger L49:** the incremental call carries no known
  containers and no neighbours (§6; D6); a link across two containers is not dropped (§5, §6; D14). Changed from the
  first draft, not from the spec: after a failed call the screen-level labels are the latest successful record's, not
  unknown (D16). Not covered by design: the guards and
  per-video cost report (§10 step 7), `interpret`'s rendering of labels, the index's use of links (plan 3), running any
  paid phase.
- **Placeholders.** None: every test names its fixture and expected values; every prompt paragraph is written out.
  The `ValueError`s for arms and pane "until Task N" are removed by the task they name.
- **Type consistency.** `CallPlan(frame, targets)` (Task 3) is what Tasks 6, 9, 15 consume; `Proposal` and
  `to_proposal(arm, out, boxes, frame_size, margin_px)` (Task 7) are extended, not re-signed, in Tasks 12, 13;
  `repair(p, targets, frame_boxes)` and `repair_containers(containers)` (Task 7) keep one signature in every mode;
  `output_model(arm, transcribe, pane)`, `system_prompt(arm, transcribe, pane)`, `prompt_version(arm, transcribe, pane,
  scale)` keep one signature from Task 5 on; `Labels.box / frame / lifetime`, `BoxLabel`, `BoxLink`, `FrameLabel`,
  `LifetimeLabel` are the names plan 3 assumes; `estimate_cost(usage, model, batch)`, `add_usage`, `USAGE`,
  `run_with_batches(run, cfg, provider, stage_fn)` are what plan 3 consumes from Task 8.
- **Review focus.** Each of the five lines names its test and task.
- **Fixtures rechecked by hand after the reconciliation,** because their rules changed: Fixture P under the new target
  rule (5 targets, equal to plan 1's projection); `test_repair_links` and `test_repair_records_and_headers` without the
  container gate; Task 9's repair counts (2 a record, 4 in all) and `mark_match` (2 of 4; 6 of 6; 5 of 6); Fixture T's
  new `A11` through Tasks 10, 11 and 15 (sources, the refused pair, `relinked 1`, links in force at 11 and 12, the
  screen-level labels after a failed record); the duplicate-id case of `test_arm_b_assigns_by_centre`; the unchanged
  values of `test_incremental_projection`.
- **Not verified, by the owner's rule.** No expected value in this plan was produced by running anything. The ones
  that rest on library behaviour rather than on this plan's own rules are: pydantic emitting no `default`, `oneOf` or
  `prefixItems` for the models of Tasks 5 and 12 (they use only required fields, `Literal`, `str | None` and lists);
  the tag fitting right of each box in Fixture E (`label_clashes 0`); `rapidfuzz`'s normalised Levenshtein similarity
  in `mark_match` (`0.9` and `0.0` above); the API accepting an enum with an empty string (`joiner`). If the first test
  run contradicts one of them, the finding goes back to the plan's author as a finding, not as a silent fix.

## Execution handoff

Plan reconciled and saved to `docs/superpowers/plans/2026-09-21-rebase-boxes-2-annotate.md`; ledger L49 records the
decisions and every declined finding. I recommend **subagent-driven** execution: fifteen tasks that meet only at the
interfaces named above, each with its own tests; a wrong label rule is cheap to catch in a per-task review and
expensive to find after P1 has been paid for. **Tasks 1–11 land first and are all P1 needs; Tasks 12–15 are the
evaluation switches** and land before P2–P4 (12 and 13 before P2, 15 before P3, 14 before P4).
