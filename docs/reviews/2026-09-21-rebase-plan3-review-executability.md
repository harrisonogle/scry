# Review of re-base plan 3 (`interpret`, `summarize`, `index`, `ask`): executability

Reviewer: fresh, read-only, one lens: can the plan be executed test first, and would two implementers agree.
Read: the spec (now **revision 3.1**, commit `50461ff`; it changed under the plan, which still cites revision 3);
plan 3 in full; plan 1 Tasks 4, 7, 10–12, its "Returns with" table and decisions; plan 2's interface section and Tasks
2, 8–11; the tag's `interpret.py`, `hierarchy.py`, `index.py`, `agent.py`, `providers/*`, `cli.py`, `config.py` and
their tests; the branch's committed `schemas.py`, `run.py`, `costs.py`, `index.py`, `cli.py`, `tests/test_package.py`;
the installed SDK's `messages.create` signature. Nothing was run. All arithmetic below is by hand.

**Verdict: accept with changes.** The design is sound, the rules are unusually precise, and almost every expected
value follows from them. But the plan was drafted against plan 1's records before they were simplified, so Fixture M
and Tasks 4, 7, 8, 9, 11, 12 and 14 cannot be executed as written. One mechanical reconciliation pass (the kind plan 1
had) fixes that; it removes text and adds none.

## Blocking

**B1. The change and lifetime records are not plan 1's (Fixture M; Tasks 1, 4, 6, 8, 11, 12, 14; A1, A2, D5).**
Committed `schemas.py` has `BoxChange` and no `Group`; `Change.records` (kinds `reread … removed`, `before`/`after`
one `BoxText | None`), no `groups`/`appeared`/`removed`; `moved: list[tuple[str, str]]`; `kind: "single" |
"unsettled"`; `Lifetime.readings: dict[str, list[int]]`. Consequences: `import Group` fails (Task 4 Consumes);
Fixture M's `groups` and `appeared` keys are **silently dropped** by `extra="ignore"`, so T1–T3 load with `records ==
[]`; `readings {"Status": 4}` and `moved=12` raise `ValidationError`. Simplest fix, all on plan 3's side:

| Plan 3 says | Becomes |
|---|---|
| a group; its `before`/`after` lists | a record of kind reread/appended/truncated/changed; one `before`, one `after` |
| `appeared`, `removed` ref lists; `text_of(ref)` for them | records of those kinds; text is `after.text` / `before.text` |
| `moved` (count), `moved > 0` | `len(c.moved)` |
| readings "by count" (Task 11 r3, Task 14 r5), payload counts | by `len(frames)`; fixtures write frame lists (`{"Status": [10, 11, 12, 13]}`) |
| `change_rects(c, boxes)` | `[r.rect for r in c.records]`; the `boxes` argument goes (same expected values) |
| `continues` "group position" | record index; rendering unchanged |

Cut: the `" + "` side join and the first half of `test_render_multi_box_sides_and_reread` (sides are single boxes);
D5's `clock` flag; A8 stays a wish (`same_place` is still a count). The rendered layout (`Text changes:`, `Appeared:`,
`Removed:`) and every expected string in Tasks 4, 6, 8, 12 survive unchanged once Fixture M is rewritten as records;
the T5 fixture needs `moved` as pairs (use two pairs and `moved 2`).

**B2. `trivial` no longer exists** (plan 1 D23, spec §12; `Change.kind` rejects it). Remove: Task 7 rule 2a, the
`trivial` stat and `error="trivial"`; Task 9 rule 1's filter and `test_trivial_transitions_are_not_items`; Task 12 rule
1 "trivial ones included"; D21; "non-trivial" in Global Constraints and Task 6. `test_trivial_and_missing_png…` becomes
the missing-PNG half only (two calls, `interpreted 2`, `errors 1`); `test_no_transitions_writes_nothing` uses an empty
`changes.jsonl`.

**B3. The suite fails at two commits because of tests the plan does not list.**
(a) Task 5 creates `src/scry/interpret.py` (and `prompts/` if plan 2 has not): committed
`tests/test_package.py::GONE_MODULES` holds `"interpret"` and `"prompts"`, so `test_old_machinery_is_gone` fails. Add
the file to Task 5 (drop both names; `hierarchy`, `agent`, `diagnostics` stay gone under the new names).
(b) Task 16 changes `STAGES`; plan 2's `test_annotate_stage.py::test_stage_list` asserts the five-stage list. Add that
file to Task 16. Keeping plan 2's order (`outline` first, then the three new stages appended) is the smaller change;
D19 itself says nothing depends on the position.

## Should-fix

- **S1 (Task 10 r6, A4). `FrameLabel.links` are plan 2's `RunLink | PairLink | RecordLink`**, each with only its own
  fields; "they share `kind, boxes, joiner, key, value, members, header`" is false for them (`PairLink.boxes` raises).
  Fix: `link_anchor`/`link_lines` dispatch on `kind` and read that kind's fields only; say which class
  `test_link_lines` builds.
- **S2 (Tasks 10, 11). Two hand-written annotation fixtures cannot load or do not work.** Plan 2's `Annotation`
  requires `targets`, `model`, `prompt_version`; the one-frame `区` fixture and the F5 run fixture give none. With
  `targets` omitted: `ValidationError`. With `targets []`: plan 2 Task 11 rule 1 counts only target boxes, so `L1` is
  not `non_text` and `test_non_text_lifetime_is_skipped_and_counted` fails. State `targets` = every box in both.
- **S3 (Task 8 r5). `first.from_frame or first.frames[0]` breaks on frame 0**, the from-frame of T1 in every real run
  (0 is falsy, a `Change` has no `frames`). The test uses 3→5 and passes. Reword by type, as the tag did, and make the
  test's first change start at frame 0.
- **S4 (Task 7 r4). `interpret` reads `outline.json` (`chapter_of` feeds the context text) but `run.outline` is not an
  input**, while `summarize` and `index` list it. `scry outline --import` after `interpret` leaves stale context and
  no re-run. Add the path.
- **S5 (Global Constraints). "After plans 1 and 2 have landed" is circular**: plan 2's Tasks 12–16 land after P1,
  which needs this plan. Say: after plan 2's Tasks 1–11.
- **S6 (Task 15 r2, D17). The `cache_control` risk is not isolated.** The installed SDK 1.5.0 accepts the top-level
  field (`messages.create`, "applies a cache_control marker to the last cacheable block"), so the client side is safe;
  the server side is unexercised. It is a hard-wired kwarg pinned by a test, `ask` has no rule for an exception from
  `create`, and the first exercise is the paid question set, where a rejection fails every question. Smallest
  isolation: one `[ask]` boolean (default on) that omits the field; and one sentence on what `ask` returns when
  `create` raises (today it propagates; Review Focus 4 promises "no exception" only for the listed cases).
- **S7 (Task 13 r2, r5). Where `ordinal` comes from is unstated**: the frame query "returns ids and texts only", yet
  `collapse_runs` needs the ordinal, which lives only in the JSON payload. Name it (`json_extract`, or a column).
- **S8 (Task 14 r4 with Task 15 r3). `truncated` and `next_t_a` are added after the length check**, so `ask`'s own
  cut to `max_tool_result_chars` can slice exactly those keys off. Measure the whole result, or put the two keys first.
- **S9 (A9d, D20). *Found*, submission error and *false run* have no owner**: plan 1 D21 defers to the index, this
  plan to plan 4's Task 4, and plan 4 (on disk) consumes `score_found`, `score_submitted`, `score_false_run` "from plan
  3's Task 16". A9 describes another draft of plan 4 in both directions (plan 4's N1, N2 ask for `citations` and `[ask]
  prompt`, which exist here). Settle in synthesis before either is executed.
- **S10 (Review Focus 1, F6). The errored-annotation case is claimed and untested**: all three named tests run with
  no annotations at all. Give one frame of an existing labelled test a record with `error` set, or drop the claim.

## Nits

- Task 1: `ScriptedProvider.complete` must be `async` (the protocol is); its callable form duplicates plan 2's
  `AnswerProvider`: keep one. Task 9's first test scripts two different step elaborations as a list although they run
  under `gather`; use the callable form the plan already offers.
- Task 6: `image_block` takes a `Path`; in-memory PNGs need the tag's private `_png_block`. Plan 2 Task 6 builds the
  same helper; share it. `image_mode`'s `rects`: say raw `change_rects`, not the cropped result.
- Task 9 r4/r6: the video call's `Segment {id}`: `V` or the tag's `video`?
- Task 13: `matched_lines` returns a tuple, the tests compare a list; say the hit holds a list. Ties: sort on the
  rounded score the hit carries, or three-ranking sums can differ in the last bit. `fts_query("*")` and `"("` give an
  empty phrase; the rules do not say what `search` does if SQLite raises. `scry search` output for no hits is unstated.
- Task 14: `open_db` creates `index.sqlite` when absent, so `ask`/`search` on an unindexed run write a file and return
  nothing, against "ask writes no file". "Other OCR readings" means other than the box's own text; only the test says
  so. `Labels.box` may return `None` when labels exist (failed record): rules 4 (Task 10) and 5 (Task 14) should say skip.
- Task 15: `extract_citations` validates nothing (a cited frame 99 is kept); say so for plan 4.
- Fixture M: T2 `touched_share 0.0` contradicts plan 1 (two appeared boxes are touched: 2 / (3 + 5) = 0.25). Unread here.
- Header: spec revision 3 → 3.1; Task 2 "four sections" are three sections and one key; A9(e): the branch already
  imports helpers top-level (`from track_fixtures import …`), so this plan's style is the one to keep.

## Q1. Cases asked about

| Case | Status |
|---|---|
| no annotations file | specified and tested (Tasks 4, 10, 12, 16) |
| annotation records with `error` | handled by plan 2's view; untested here (S10) |
| transition with no change records | specified (`No text change…`, no ids, `crops` → `scaled`, no index node without an interpretation); tested in Task 4 only |
| frames without PNG | `missing_png`, no call (Task 7); `get_frame` text block (Task 14, rule only, no test) |
| refusal, `max_tokens`, schema failure | one rule covers all (`error = res.error`); only refusal tested. Inherited: uncached `api:`/`max_tokens` errors are never retried, because the stage is marked done |
| citations not offered | `interpret`: dropped and counted, tested; `summarize` refs: counted, tested; `ask`: unvalidated |
| empty index, no hits | returns `[]`; CLI output and the created empty DB unstated |
| identical text, different descriptions | collapse unless a term is in the description; hit shows the earliest member. Pinned: frames 10–12 collapse across two descriptions |
| ties | SQL order and rule 7 are deterministic; collapsing has no tie (one node per ordinal) |

## Q2. Values recomputed (on the plan's own shapes)

Agree: `USAGE` 100·5 + 20·25 + 1000·0.5 + 400·6.25 = 4000 µ$ → 0.004; `run_costs` 0.012 / 4 = 0.003; `summarize` 6
calls → 600 / 2400 tokens, 0.024; `ask` 3000·5 + 300·25 = 22,500 µ$ → 0.0225; crops T1: pad `floor(2·18 + 0.5)` = 36,
(10,100,190,118) → (0,64,226,154) = 226×90; T2: (0,84,186,174) ∪ (0,104,116,194) = (0,84,186,194) = 186×110;
`Pixels changed` 0.20 / 0.50 / 0.02 %; `validate_citations` 4, and 1 + 3 + 3 = 7; `merge_window_boundaries` (1800 gets
one vote: 0 items from its window's edge); "Creating": one hit per family at rank 1 twice, 2/61 = 0.032787 → 0.03279,
family order breaks the tie, run [10, 11, 12], `t` [20.4, 30.0]; "git" [[10], [11], [12, 13]] and [[10], [11, 12, 13]];
"branch" [[12], [13]]; `t_from=25` → [11, 12]; F3: 21 candidates, L01 and f0 tie at 2/61, 20 kept; F5's four lines;
`"git status"` → `v:L4` first (`v:L4`, `v:f11`, `v:S1` tie at 2/61; lifetime leads the family order); both
`extract_citations` lists; the `get_frame` lines.
Truncation: T1 item 417 characters, T2 339, wrapper 19, separator 2 → 777 (757 with `ensure_ascii=False`) > 600, T1
alone 436: `["T1"]` either way.
Differ: none of the numbers; only S2, S3, the tuple/list nit and Fixture M's `touched_share`.

Rules without a test: Task 4 r2a (empty `app`), r2c roles `run`/`member`/`header`, `model reads` under
Appeared/Removed; Task 6 `Area k after:` caption; Task 7 r1 (batch: nothing pins that `pending` records are never
written), `image_fallbacks` > 0, the concurrency bound; Task 9 outline suggestion, chapter-start fallback, windows,
parts over 80 children; Task 13 r3 (vector list), r9 format beyond one line; Task 14 missing-PNG block; Task 16 r1
wall seconds. Tests that pin nothing a rule requires: none found.

## Q3. Interfaces read from plans 1 and 2

Match (checked against plan 1 Task 4, 7, 10–12 and the committed code; plan 2 Tasks 2, 8–11): `Frame` fields; `Box`,
`FrameBoxes`; `PixelStats`' six fields; `Revert`; `BoxChange.rect`, `in_churn`, `char_diff`, `continues "T8/0"`;
`Change.t = (a.t_end, b.t_settled)`, `same_place` (count), `reverts`; `Lifetime.text`, `unstable`, `sightings`,
`first`, `last` (`t_settled` / `t_end`), `boxes`; `box_ref`, `parse_box_ref`; the four loaders, `load_outline`,
`chapter_of`, `video_id`, `stage_up_to_date`; `margin_px(a, b, margin)`; `scale_image`; `scry.video.iter_frames`; the
kept names of `scry.index`; `IndexConfig`; `extra="forbid"`; `stages.decode.emitted`; `Run.annotations`,
`load_labels`, `Labels.box/frame/lifetime`, `BoxLabel`, `BoxLink`, `FrameLabel` (`containers`, `description`,
`missed`), `LifetimeLabel`, `LifetimeLink` (`records`, `first_frame`); `run_annotate` and `mode = "off"`; A6's cost
names and `USAGE`. "Returns with": every row addressed to plan 3 is covered; the `text` image mode is dropped with a
stated reason (D4).
Mismatch: `Group`, `groups`, `appeared`, `removed`, multi-box sides, `moved` as a count, `readings` as counts, the
`clock` flag (B1); `trivial` (B2); `FrameLabel.links` element shape (S1); `Annotation`'s required fields (S2);
`STAGES` order and `test_stage_list`, `GONE_MODULES` (B3); `tests.fakes` import style (plan 2's side); plan 4 (S9).
Unread new plan 1 fields (`unchanged`, `variants`, `flicker_*`): nothing to do.

## Q5. Commit order

With B1–B3 fixed, the package imports and the suite can pass after every commit: each task's new module is imported
only by later tasks, Task 10 updates the kept `test_index.py` helper in the same commit as `Node`, and plan 1's
`test_p0_margin_configs…` still holds because Task 2 writes defaults into `scry.toml` (the dumps stay equal). Without
them it fails at Task 1 (Fixture M does not validate), Task 5 (`test_package`) and Task 16 (`test_stage_list`). Needed
from the siblings and not guaranteed: plan 2 Tasks 2, 8, 9, 10, 11 before Task 1 (S5); `Annotation` loading
hand-written §5 lines (S2); the scorers' owner (S9).

## Q4. Provider and SDK

The three accounting claims hold against the tag: `estimate_cost` ignores cache creation; `complete` overwrites the
first attempt's usage on both retries; `BatchRunner` drops `cache_creation_input_tokens`. 1.25× is right for the
default five-minute cache the provider and `ask` request. The loop matches the tag and L18: same `TOOL_DEFS` shape,
no `tool_choice`, `output_config={"effort": …}`, `resp.content` appended unchanged (thinking blocks intact), list
content in `tool_result` for images, string `system`. Nothing specified would be rejected as the tag's notes describe
the API; the one new field is S6. Batch-path note (inherited): a batch `max_tokens` result is cached as `schema: …`
with no retry.

## Q6. Stage inputs

| Stage | Reads but not an input | Effect |
|---|---|---|
| `interpret` | `outline.json` | stale context, no re-run (S4) |
| `interpret`, `summarize`, `index` | `lifetimes.jsonl` through `load_labels` (`index` lists it) | none in practice: `track` writes it with `changes.jsonl` |
| all model stages | — but hash all of `[model]` | another stage's effort re-runs them as cache hits: free |
| `index` | — but hashes query-time `k`, `rrf`, `collapse` | a free rebuild |

Otherwise complete: annotations absent hashes as `missing`, so labelling later, or `mode = "off"`, re-runs all three.
