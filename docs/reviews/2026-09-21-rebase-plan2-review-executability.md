# Review of build plan 2 (`annotate`): executability

Reviewed: `docs/superpowers/plans/2026-09-21-rebase-boxes-2-annotate.md` as committed in `fbe7982`, against the spec
(`docs/proposals/2026-09-21-boxes-mode-rebase.md`, revision 3), plan 1 as reconciled, plan 3's interface assumptions,
the code at tag `pre-rebase-boxes`, the branch's working tree, and the installed SDK (`anthropic` 1.5.0, read under
`.venv/lib/python3.14/site-packages/anthropic/`). Read-only: nothing was run, no script was written, no test was
executed, no model was called. Every number below was worked by hand from the plan's rules.

**Verdict: accept with changes.** The plan is buildable test-first. I recomputed every expected value I could reach
(list in §2) and found no arithmetic error. One finding breaks the plan's own "0 failures after every commit" rule and
is a one-line fix; the rest are small wording or scoping changes. None needs new machinery; two remove some.

## Findings, ranked

### Blocking

**B1. Task 5 turns the suite red: `scry.prompts` is on plan 1's "gone" list.** `tests/test_package.py` (plan 1 Task 1,
in the tree now) has `GONE_MODULES = [..., "stage2a", "prompts"]` and asserts `find_spec("scry." + name) is None`.
Task 5 creates `src/scry/prompts/__init__.py` and does not list `tests/test_package.py` among its files, so
`test_old_machinery_is_gone` fails at Task 5's commit and at every commit after it. Fix: Task 5 also modifies
`tests/test_package.py` to drop `"prompts"` from the list (plan 3 has the same problem: it creates `src/scry/interpret.py` and `interpret` is on the list too).
The plan's IA8 and IA12 discuss `prompts/` returning and miss the test that forbids it.

### Should-fix

**S1. Task 8 rule 3 (usage summed over retries) does not capture the attempt it cites.** The description of today's
provider is accurate (`r = await self._call(…)` overwrites the first result). But in the installed SDK
`messages.parse` validates the text unconditionally in its post-parser (`lib/_parse/_response.py::parse_text` →
`TypeAdapter.validate_json`), so a reply truncated at `max_tokens` with any text in it, or a refusal whose text is not
JSON, raises `ValidationError` inside `parse()`. `AnthropicProvider._call` then takes its `except (ValidationError,
ValueError)` branch and returns `VlmResult(None, "schema: …")` with `usage == {}` and no `stop_reason`: there is no
response object to read usage from. So the provider's `stop_reason == "max_tokens"` branch fires only when the reply
has no text block at all (thinking used the whole budget), and "a billed attempt of up to 16,000 output tokens" still
disappears in the common case. `FakeMessages` hides this: it returns `parsed_output=None, stop="max_tokens"` where the
SDK would raise. The change is complete for the paths that return a response, incomplete for the path that raises.
Smallest fix: say so under "Known and not tested", and add the second half of the test that makes the gap visible
(script `[ValueError("1 validation error"), {"parsed": Out(answer="c"), usage 10/5/0/7}]` → the sum is `10, 5, 0, 7`:
the first attempt contributes nothing). Closing it needs the raw response and belongs in an open item, not here.

**S2. Task 8: `from tests.fakes import …` cannot import in this repository.** `tests/` has no `__init__.py`,
`pyproject.toml` sets no `pythonpath`, and pytest's default import mode puts `tests/` itself on `sys.path`; the
existing helpers are imported as `from track_fixtures import …`. Plan 3 Task 1 rule 5 states the convention and its
A9(e) flags the conflict. Change line 894 to "imports the fakes from `fakes`", and the same for `annotate_fixtures`.

**S3. Task 1's `test_annotate_defaults` cannot stay green through Tasks 12, 14, 15, 16.** It asserts
`Config().annotate.model_dump() == {"mode", "transcribe", "scale"}` exactly; each later task adds a key (`arm`,
`text_assignment`, `assign_reach`, `pane`, `neighbour_reach`) and none lists this test for update. Either assert the
three values individually in Task 1, or have each later task's key test say it extends this one.

**S4. Task 13, arms B and C: assignment runs on unrepaired containers, and duplicate ids are silent.** D1 and Task 13
rule 5 convert before repair, so `container_at` sees the answer's containers as returned. With two containers `c2`
(rects R1, R2) and a box centre only in R2, one implementer returns `Assign(box, "c2")`, repair then drops the second
`c2` (`dup_container`) and the box ends up in the first `c2`, whose rectangle does not hold it; another implementer
dedupes first and gets `outside`. One sentence in rule 2 settles it: "a container whose id repeats an earlier one is
ignored for assignment (repair drops and counts it)". Add the case to `test_arm_b_assigns_by_centre`.

**S5. Task 9 rule 2 and Task 16: what a rerun does after an uncached failure is unstated.** The provider caches
success, `refusal` and `schema…`; it does not cache `api: …` or `max_tokens`. But the stage is "up to date" once
`annotations.jsonl` exists and inputs and config are unchanged, so those records are never retried by `scry annotate`
(today's `run_perceive` behaves the same). State the operator path (delete `annotations.jsonl`; every answered call is
a cache hit) in rule 2 and in the manifest's `errors` note. In an incremental chain add the cost consequence: when a
retried call now succeeds, the context text of every later call in the chain changes, so their keys change and they
are paid again. D23 and D25 say "the call cache keeps every paid answer"; for a chain that is true only while every
earlier answer is unchanged.

**S6. Task 16 rule 5, "placed after the targets line", is undefined for arm C heads.** Under Task 12 rule 3 arm C
writes a target line only "when the targets are not every box", so a head has none. Say where the two context blocks
go then (after `COORDS`); the position changes the hashed text and the test expectations.

**S7. `test_failed_call_does_not_stop_the_chain` pins nothing about record 11 ("stored whole").** With the frame-11
answer of the preceding test (no containers, `b1→c1`, `b5→c2`, run `[b4, b5]`, pair `[b1]/[b2]`, two texts) and
`known == []`, the rules give: both assigns dropped (`unknown_container` 2), both targets appended (`unplaced` 2), the
run dropped because `b4` has no container and the pair because `b1` has none (`link_cross_container` 2); so `error
None`, `assign []`, `unassigned ["b1", "b5"]`, `links []`, two texts, `description "d11"`, `repairs 6`,
`repair_counts {"unknown_container": 2, "unplaced": 2, "link_cross_container": 2}`. Name the answer and pin these, or
script an answer that creates `c1`, `c2` and pin that.

**S8. Dependencies among Tasks 12–16 are real and unstated.** Task 14 rule 1 and rule 3 use `median_box_height`,
`centre`, `point_rect_distance`; Task 16 rule 4 uses `median_box_height`; all three are created by Task 13
(`geometry.py`). Task 15's validator reads `arm` (Task 12). Order: 12 → 13 → {14, 16}; 12 → 15. Task 14 has no
"Consumes" line at all. If reading assignment is wanted for arm A before P2 (§7 offers it as a remedy for the
wrong-neighbour readings of transcribing), move the three helpers into Task 14.

**S9. Two cross-plan conflicts are missing from the interface list.** (a) Plan 4's Task 1 redefines the cost functions
with `KeyError` on an unknown model (plan 3 A9(b)); every stage test here prices `"fake-model"` at the fallback Opus
prices (`0.004`, `0.008`). (b) `test_stage_list` pins `["outline", "decode", "read", "track", "annotate"]`; plan 3's
D19 moves `outline` after `decode`. Add both to IA11 for the synthesis pass.

### Nits

- **N1. Task 7 preamble** ("every dropped or altered item adds 1 to exactly one key") contradicts its own rules and
  tests: one container can add to `bad_owner` and to `bad_covers` several times (rules 4–5, `test_repair_containers`),
  and several alterations are uncounted by design (a record's empty cells, the pane strip, a clamped rectangle, a
  known id echoed, ids that vanish from `unassigned`). The tests are right; reword the sentence.
- **N2.** Task 10 Step 2 says "rules 1–7"; `mark_match` is rule 8.
- **N3.** `A11f` names two different fixtures: no links in Task 10 (`test_every_frame_records_do_not_pile_up`), the
  pair `[b2]/[b3]` in Task 11 (`test_majority_over_every_frame_records`, which needs it for `records == 3`).
- **N4.** Task 3 rule 5: "no lifetime crosses a head" is false as worded (a lifetime begun on a no-call frame before
  the head crosses it). It is unlabelled before the head, so the
  conclusion holds; say "no labelled lifetime".
- **N5.** `mark_match` breaks the plan's own constraint at line 212 ("no mark … in code"). Exempt it by name (spec §7
  uses it) or rename it.
- **N6.** `AnswerProvider.complete` must be `async def`; the text does not say so.
- **N7.** Under arms A and D an answer container that reuses a known id is ignored uncounted even when its kind or
  name differ (the model ignoring "New containers start at c3"); targets assigned to it silently join the known
  container. By the plan's own rule ("its counter is the evidence a later rule would need") this wants a count.
- **N8.** The call-cache key does not hash the system prompt; `VERSION` is its only guard (as at the tag). Say in Task
  5 that any edit to a paragraph bumps `VERSION`; P5 and P6 plan to tune prompts.
- **N9.** Rules with no test: Task 3 rule 5's `ValueError`; Task 8 rule 5's client close (and what happens when
  `stage_fn` raises); Task 8 rule 3 on the schema-retry path (S1); Task 9 rule 7 in batch mode through the stage;
  `ambiguous` reaching `unassigned` through `to_proposal` (only `outside` is pinned); `BoxLink.role == "header"` and a
  header at lifetime level (plan 3 reads both); every-frame labels carried over a failed record; a text point that
  misses with `container_at` not "ok"; `update_known_rects` through the stage; two chains in one run.
- **N10.** Tests that pin nothing a rule requires: `test_tag_width_grows_with_the_number` (font behaviour, no rule);
  `test_mask_code_is_gone` duplicates Step 3's grep.
- **N11.** The self-review's "not verified" list should add: `label_clashes 0` in Fixture T (the Task 16 stage test
  compares whole records), and the API accepting `joiner`'s enum `["", " "]` (no schema at the tag has an empty-string
  enum value). A rejection would show as `api:` errors on the first P1 frame, so it is cheap to find.
- **N12.** `cfg.track.margin` gains a second consumer (arm C's snap distance, D11). P0 varies that key (0, 0.25, 0.5,
  1.0) for `track`'s reasons; at 0 a point must fall inside a box. Note the coupling in D11.
- **N13.** D6's consequence list should add wall-clock: a video is mostly one chain (heads are the first frame and
  cuts), so incremental annotation runs its calls one after another.

## 1. Can each task be built from the plan, with the same outputs?

Yes for Tasks 1–12, 14, 15 and most of 13 and 16, given B1 and S2–S4, S6. The cases asked about:

| Case | Where decided | Verdict |
|---|---|---|
| Frame with no boxes | Task 3 r4 (head), Task 4, Task 6 r2.5–2.6, Task 9 test, `margin_px` 0, `median_box_height` 0.0 | defined and tested |
| Unknown or duplicate ids | Task 7 r1, r6, r11, r17 | defined and tested; duplicates under B/C before assignment are not (S4) |
| Box in two containers, or none | Task 7 r9, r10; Task 13 r3 | defined and tested |
| Link naming a box outside its container | Task 7 r15 | defined and tested, headers included |
| Rectangle partly outside the frame | Task 13 r2 | clamped, uncounted; tested |
| Two rectangles over a box, no `covers` | Task 13 r3 (D10) | `ambiguous`; `container_at` tested, the path into `unassigned` is not (N9) |
| Point equidistant from two boxes | Task 13 r4 | reading order; tested at 10 px each side |
| Refusal, `max_tokens`, schema failure | Task 8 (provider), Task 9 r6 | error record; rerun semantics unstated (S5); usage gap (S1); batch mode terminal, as the plan says |
| Failed call inside a chain | Task 16 r7, D4 | defined; the test pins too little (S7) |
| First frame; a cut | Task 3 r3–r4, Task 16 r1 | one rule; tested |
| Arm C head, context block position | Task 16 r5 | undefined (S6) |

No rule is circular. Task 10 rule 1 (source) feeds rule 4 (links in force) and Task 16 rule 3 reads both; each is
defined before its use.

## 2. Tests recomputed by hand

All of these agree with the plan:

- **Task 3.** Fixture P incremental: frame 0 `(b1, b2)` head; frame 1 none (`components 0`); frame 2, `p = 0`: `b1`
  `L1` first 0 no, `b2` `L4` first 2, `b3` `L5` first 2, `b4` `L3` first 1 > 0 → `(b2, b3, b4)`, not a head; frame 3
  `(b1)` head. With `T1.pixels = None`: frame 1 `(b3)`, frame 2 with `p = 1` → `(b2, b3)`. Chains `[[0, 2], [3]]`.
  Fixture T: `(b1..b4)` head, `(b1, b5)`, none for 12.
- **Task 7.** `test_repair_containers`: owners fail for `c2` (`c9` unknown), `c3` (a window), `c4` (owner is a popup)
  = 3; covers drops `c1` (self) and `zz` = 2. `test_repair_assign`: 1 + 1 + 1 + 1, then `b3`, `b6` unplaced = 2.
  `test_repair_links`: `[b5, b6]` already linked 1; `[b1]`, `[b6, b6]`, `[b3]/[b3]` malformed 3; `b99` 1; `b3/b6` and
  `b7/b8` cross-container 2. Records: 1, 1, 2, 1 as stated; three kept. Texts and missed: six keys at 1. Known
  context: `link_no_target` 1, `link_already_linked` 1; the pair survives.
- **Task 8.** `(1e6·5 + 1e5·25 + 2e6·0.5 + 1e6·5·1.25) / 1e6 = 5 + 2.5 + 1 + 6.25 = 14.75`; batch `7.375`; today's
  function gives `8.5`. `USAGE`: `(500 + 500 + 500 + 2500) / 1e6 = 0.004`. Retry sum `20, 10, 0, 7`.
- **Task 9.** Usage `200, 40, 2000, 800`; `0.008`, batch `0.004`, per frame `0.004`, per call `0.004`. Repairs test:
  `unknown_box`, `unplaced`, `link_cross_container` = 3 a record, 6 in all.
- **Task 10.** Sources, `container_ref` through `known_as`, links in force at 10, 11, 12, the failed-record case, the
  pile-up case; `agreement`'s seven pairs against `textdiff.norm` and the tag's `merge.agreement`;
  `similarity("PS C:\> a", "PS C:\> az") = 1 − 1/10 = 0.9` (it is Levenshtein normalised, as the test assumes);
  `mark_match` `(6, 6)`, `(5, 6)`, `(5, 6)`.
- **Task 11.** `{"RG1": 2, "RGl": 1}`, `records 3`, `first_frame 10`; the incremental links for `L1/L2` and `L3/L6`.
- **Task 12.** Paragraph difference sets `{2, 3}`, `{1, 2, 3, 4, 5}`, `{1, 4, 5}`, `{1, 5}`, `{1}`; block texts and
  types; version strings. No prompt paragraph in the plan contains `mark`, `region`, `vlm_lines` or `focus`.
- **Task 13.** `margin_px = floor(0.5·16 + 0.5) = 8`; distances `5.0`, `hypot(10, 24) = 26.0`, `0.0`; `(250, 48)` is
  10 from `b4` and `b5`; `(250, 80)` is 26, 26 and `hypot(20, 20) ≈ 28.3`; the six centre assignments; arm C: pair
  `b3/b4`, the run lost to `(600, 18)` (210 px from `b2`), `Networking` at `(30, 150)` missed into `c1`;
  `text_missing 5`.
- **Task 14.** Both winning claims have similarity 1.0 and distance 12, ordered by box; `1ogin_` stays
  (`1 − 2/17 ≈ 0.88` on `b1` against a far lower value on `b2`); reach `92 > 32`; an empty reading scores 0 everywhere.
- **Task 15, 16.** Version strings; neighbour band at reach 0, 4 (`96 > 96` false), 5, 16; `next_id 3`; `linked {b2,
  b3}`; the context texts; the stage test's `A11` (`link_already_linked 1`); `targets 6`; `frame(12).links`.

One value the plan leaves open is computed in S7.

## 3. Structured output

D2's claim is correct against `anthropic/lib/_parse/_transform.py` 1.5.0:

- `oneOf` is rewritten to `anyOf`; `discriminator` is not a handled key, so it falls into the leftover dict and is
  pasted into `description`. Worse than the plan says: each variant's `kind` is a `const` (with a `default`), also
  unhandled, so the tag becomes an unconstrained string described as `{const: run, default: run}`. The API itself
  accepts `const` and `anyOf`; the loss is the SDK's.
- A tuple gives `prefixItems`, `minItems: 4`, `maxItems: 4`; only `minItems` 0 or 1 is kept, the rest goes to
  `description`, and the array is left with no `items`: any array validates on the wire.
- `required` is passed through as pydantic wrote it, so defaulted fields are optional, and `default` is pasted into
  `description`. The batch path's `_local_strict` mirrors that.

Every schema the plan specifies uses only objects, arrays (nested included, as `rows: list[list[str]]` was at the
tag), strings, integers, `enum`, `anyOf` with null, and `$ref`/`$defs`: all expressible, all fields required. Two
small notes: `transform_schema` returns early on `$ref` and drops sibling keys, so a field description on a
model-typed field (`OutContainerRect.rect`) never reaches the model (the B/C containers paragraph already says it;
`test_schema_is_strict_friendly` walks the pydantic schema and cannot see this); and N11 on the empty-string enum.
The schema `title` survives the transform and is in `model_json_schema()`, so the eight (twelve with pane) class
names do give distinct schema hashes.

## 4. Provider changes

| Change | Described current behaviour | Complete? |
|---|---|---|
| Usage summed over retries | accurate | no: attempts that raise carry no usage (S1) |
| Cache-creation tokens on the batch path | accurate (`run_pending` builds a three-key dict) | yes |
| `estimate_cost` with writes at 1.25× and batch at 0.5× | accurate (today's function ignores the key; `8.5`) | yes; 1.25× is the five-minute rate the provider asks for; the 512-token minimum for Opus 5 is right |
| `run_with_batches` re-homed, client closed in the loop | accurate (`perceive._run_with_batches`, no close) | behaviour yes; the close is untested (N9) and makes a provider single-use, which holds because each stage builds its own |

## 5. Interfaces

Read from plan 1 and present as assumed: `Frame` (`frame, t_settled, settled, width, height, sha256, png`), `Box`
(`id, bbox, text, in_churn`), `FrameBoxes`, `Change.to_frame`, `Change.pixels`, `PixelStats.components`, `Lifetime`
(`id, text, boxes, first.frame`), `box_ref`, `parse_box_ref`, the four loaders, `Run.overlays_dir`, `Run.cache_dir`,
`margin_px`, `cfg.track.margin`, `place_label`, `scale_image`, `draw_overlay`, `PRICES`, `estimate_cost`, `norm`,
`similarity`, `STAGES`, `Effort`. `scry.toml`'s `[overlay]` has no `scale` or `mask` key, so Task 4 breaks neither it
nor the `configs/p0-margin-*.toml` copies, and the new `[annotate]` keys sit at their defaults, so
`test_p0_margin_configs_differ_only_in_margin` stays green.

Mismatches:

1. **Flagged by the plan (IA9):** a box first seen on a frame with no call. On Fixture P plan 1's projection counts
   `2 + 2 + 1 = 5` targets and `plan_calls` asks about `2 + 3 + 1 = 6` (`2:b4`). With `components == 0` no box is
   touched, so `flicker_new` is the only way this arises; IA9 is complete. Making the projection call `plan_calls`
   needs `lifetimes` added to its signature.
2. **Not flagged:** `tests/test_package.py` forbids `scry.prompts` (B1).
3. **Not flagged:** the import style of test helpers (S2); plan 4's cost functions and plan 3's stage order (S9).
4. Plan 3's Task 10 says `Link`, `BoxLink` and `LifetimeLink` "share `kind, boxes, joiner, key, value, members,
   header`". `BoxLink` and `LifetimeLink` do; the members of `Link` do not (`RunLink` has no `key`). Plan 3's
   `link_anchor` and `link_lines` must branch on `kind` before touching a field.
5. `Missed.id` is record-local and `FrameLabel.missed` may come from an earlier frame; a citation must be built from
   `description_frame`, which plan 3's A4 does not list.
6. Plan 4's `annotate.incremental` (IA11, flagged).

## 6. Commit order

After B1, S2 and S3 the suite passes at every commit: Task 1 needs plan 1 Task 3; Task 2 needs plan 1 Task 4; Task 3
only plan 1's records; Task 4 has no other consumer of `OverlayConfig.scale` or `mask_image` in the tree; Task 8
depends on nothing else here (as plan 3's A6 says); Task 9 needs plan 1 Task 12 for `cfg.track.margin`. Tasks 12–16:
12 needs 1, 5, 6, 7, 9; 13 needs 12, 7, 9; 14 needs 1, 7, 9 and 13's helpers; 15 needs 12 (the `arm` key), 5, 7, 9,
10; 16 needs 3, 5, 6, 7, 9, 10, 12 and 13's `median_box_height` (S8).

## 7. Cache keys

The key is `(stage, model, effort, max_tokens, prompt_version, schema_hash, input_hashes)`. Distinct for every change
to what is asked: transcribing or not (`+grouponly`, class `T`/`G`), arm (suffix, class, and the text), pane (`+pane`,
class `P`), incremental (`+inc`, context in the hashed text), scale (`+s…` and the overlay's bytes), overlay font (the
overlay's bytes), `neighbour_reach` (the hashed text), effort and model. Unchanged for post-processing:
`text_assignment`, `assign_reach`, `track.margin` (snap distance), D10, repair; the stage's config hash still makes
it rerun, on cache hits. Batch and sync share keys. Gaps: the system prompt text itself is not hashed (N8), and in a
chain a key depends on every earlier answer (S5). A head under incremental mode uses the `+inc` prompt, so it never
reuses P1's answer for the same frame; that is a handful of calls a video and keeps one rule, so I would leave it.

## What to cut

- **Arms B and C under incremental annotation** (D28, `update_known_rects`, the second incremental paragraph, the
  `rect` field and rectangle form in the context blocks, D17's incremental clause). P2 compares arms on every frame;
  P3 compares incremental against every frame for the arm chosen by then. Refuse `mode = "incremental"` with arm B or
  C in config, as D12 already does for the pane, and build it only if P2 picks B or C. S6 disappears with it.
- **Task 14** is conditional on P1 keeping the second reading (§7); say "do not build before P1 reports".
- `test_tag_width_grows_with_the_number` and one of the two mask-is-gone checks.

## Verdict

Accept with changes: fix B1; apply S1–S9 as wording, test or scoping edits; take the cuts if the owner agrees.
