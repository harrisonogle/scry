# Review: re-base plan 3 (`interpret`, `summarize`, `index`, `ask`), lens: the owner's rulings and simplicity

Reviewed: `docs/superpowers/plans/2026-09-21-rebase-boxes-3-interpret-summarize-index-ask.md` (commit `4da46ac`) against
the proposal `docs/proposals/2026-09-21-boxes-mode-rebase.md` (revision 3, with §12 "Simplify before repairing"), ledger
L39 to L46, plan 1 as reconciled (its header, decisions D1 to D23, the "Returns with" table, Task 4), the interface
sections of plans 2 and 4, and the old code at tag `pre-rebase-boxes` (`index.py`, `agent.py`, `interpret.py`,
`hierarchy.py`, `diagnostics.py`, `config.py`, the three prompt modules).

Method: reading and reasoning only. Nothing was written or run but this file; no prototype, no script, no model call.
The few sums checked (dollars, reciprocal-rank scores, crop sizes) were done by hand and agree with the plan. The one
outside fact checked, by reading the Anthropic SDK reference, is D17's top-level `cache_control`: it is a documented
parameter of `messages.create`.

**Verdict: accept with changes.** The design is sound and holds to the rulings: one honest renderer shared by three
stages, the whole-screen entry kept as a superset, additive lifetime entries, collapsing in the result list only,
`entered_text` and `submitted` as interpretation, no focus, no folding, cost on every stage and every question. But
the plan was written against plan 1's first draft, and as written its fixture cannot be built on plan 1's records.
That reconciliation is mechanical and makes the plan smaller. The plan has no section titled "Conflicts for the
synthesis pass"; its A9 "Differences to reconcile" (a) to (f) is what I reviewed under that name.

## Blocking

**B1. The plan consumes records plan 1 no longer has (ruling 8).** Plan 1 Task 4 and D13: `Change.records` is one list
of `BoxChange` (kinds `reread`, `appended`, `truncated`, `changed`, `appeared`, `removed`; `before` and `after` are one
`BoxText` or null; every record has a `rect`); `moved` is a list of box-ref pairs; `Lifetime.readings` maps a reading to
the frames where it was sighted; kinds are `single` and `unsettled`; there is no `Group`, no `clock`. Fixture M as written
fails on it: `kind = "trivial"`, `moved = 12` and `readings = {"Status": 4}` do not validate, and `groups`, `appeared`,
`removed` are unknown fields (ignored, leaving `records` empty), so every expected value downstream is wrong. Each place,
with the simplest fix:

| Where | Assumes | Simplest fix |
|---|---|---|
| A1, A2, Task 4 "Consumes" | `Group`; `Group.continues` by group position; refs in `appeared`, `removed`, groups; `moved` a count | `BoxChange`; index into `records`; `len(c.moved)` |
| A8 | a wish for `same_place` refs | delete the wish; plan 1 keeps the count and nothing here shows a need |
| Fixture M | groups with list sides; `appeared [...]`; count readings; no `engine` on box records (a required field) | T1, T3: one paired record each; T2: two `appeared` records with `rect` and `after`; readings as frame lists (`{"Status": [10, 11, 12, 13]}`, L5 `{"On branch main": [12], "On branch maln": [13]}`); give `engine {}` |
| Task 4 rule 3, D5 | `Text changes:` per group, sides joined with `" + "`, then `Appeared:` and `Removed:` from two lists; the `clock` sentence | one pass over `records` in record order, body by the six kinds; the `" + "` join, its test half and the `clock` sentence go. Whether the three headings stay (filter by kind) or become one list is the coordinator's; one list is simpler and lets `continues` read naturally for any kind. Task 5's two worked examples follow whichever is chosen |
| Task 4 rules 5, 6; D4, D7 | "first three groups", group `after` texts joined, counts from lists; `change_rects` from groups plus box lookups | count by record kind; `change_rects` is the `rect` of each record in order (every `BoxChange` has one), so it needs no `boxes` argument |
| Task 4 tests | `Group(...)`, `removed=["20:b7"]`, `moved=12` | records; two moved pairs are enough |
| Task 8 rule 7 | "one line per group" | one line per paired record |
| Task 11 rule 3 and payload; Task 14 rule 5; F5's fixture | readings ordered "by count" from a count dict | count is `len(frames)`; give the payload `{reading: count}` for both readers so the two sit in one shape (the raw lifetime dump keeps the frames) |
| Task 12 rule 2 | "per group every before and after text; appeared and removed only when nothing else" | the same intent over kinds: paired records always, `appeared` and `removed` only as the fallback. Do not widen it: a page load would turn a transition entry into a second whole-screen document |

**B2. `trivial` is still a live path, and it is the path the owner removed because it "would have let a transition go
uninterpreted" (proposal §12, plan 1 D23).** Global Constraints ("every non-trivial transition"), Task 7 rule 2a, the
`trivial` stat and `test_trivial_and_missing_png_make_no_call`; Task 9 rule 1, `test_trivial_transitions_are_not_items`,
`test_no_transitions_writes_nothing` ("every change trivial"); Task 12 rule 1; D21. Fix: delete every one; every change
is interpreted, summarised and indexed; the empty case is an empty `changes.jsonl`. D21 goes whole.

## Should-fix

**S1. The guarantee section overclaims in two sentences; reword them, repair nothing (Findability section, D14).**
(a) F2 says a query that matched a today-document of a frame matches the new one. Two paragraphs later the plan admits
that is false for a quoted phrase across boxes. F2 is true for unquoted terms (the query is an OR of terms) and for
phrases inside one box; say so. (b) F4 and Task 13 rule 4 say the substring matcher "can only find more matching lines".
It can find fewer: a phrase the unicode61 table matched across a line break; a term with a separator inside it
(`--resource-group=rg1` matches a line reading `--resource-group rg1` in FTS5, not as a substring); diacritics, which
unicode61 folds. When some other term still yields lines, two frames whose missed lines differ collapse. That is
harmless under ruling 3: both frames are members of the hit, its range covers both, the hit never showed the missed
line in either case, and each differing string is a lifetime entry of its own. So D14 is safe; the sentence is not true.
A matcher faithful to the tokenizers would be machinery; do not add one.

**S2. D15 (four families): keep it, correct its reason, add nothing to it.** The stated reason is hypothetical ("if H7
fails"). The real one holds on any video: one FTS table will hold one-line lifetime documents beside whole-screen
documents of a hundred lines, and BM25's length normalisation ranks the short ones first for the same term, so in one
pool under `LIMIT k` a frame document loses its place whenever k short documents share any query term (any natural
multi-word query does that). Then the description, which lives only in frame documents, and "terms in different boxes
match one document" (spec §6) stop being reachable in the top k. Separate rankings are the smallest thing that makes
"additive" true, and the code is one loop over a tuple whether it holds four families or two. State the consequence:
eight fused rankings make the result list a round-robin across families, so a weak summary hit ties with the best
lifetime hit and family order breaks the tie. Acceptable for an agent that reads twenty hits. No weights, no per-family k.
The unbounded frame query is needed for the same reason collapsing exists (cut first and twenty identical frames
collapse to one hit and nothing fills the room); fine.

**S3. D11 and Task 11 rule 2: remove the `non_text` skip.** Never skip a lifetime; carry `non_text` in the payload.
What goes: a stat, a test, a decision, and an interaction the plan does not mention (a skipped anchor lifetime takes
its link lines out of the lifetime family, D12). What is gained: F6 becomes unconditional, and the three bases index
the same lifetimes, so comparisons between them are over one set (ruling 5). The cost is a few icon-glyph entries
nobody queries. This departs from the letter of spec §5 ("leaves … index text") in the direction of the owner's later
ruling.

**S4. D18 and Task 3: `cost_usd_batch` is always exactly half of `cost_usd`** (plan 2 Task 8 multiplies the whole sum
by 0.5; every expected value in this plan confirms it). A stored field that is another field times a constant is not
information. Remove it and `stage_cost` from the manifests of plans 2 to 4; a report states the batch price as half.
Task 3 is then `run_costs` alone and folds into Task 16, its only user.

**S5. Pre-emptive machinery for P5 and for an unseen fault (ruling 1): defer three things.**
(a) Task 2 and 15: `[ask] prompt`, the `PROMPTS` registry with one entry, its `ValueError` and
`test_unknown_prompt_variant`. Add them in the commit that adds a second wording; `AskResult.prompt` is `VERSION` until
then (plan 4's A14 waits with it).
(b) Task 14 rule 4: `truncated` and `next_t_a`. Task 15 rule 3 already cuts every dict result at
`max_tool_result_chars`, so this is a second truncation mechanism repairing a cut no recorded run has hit. Keep the one
cut; add paging when a real question shows it.
(c) Task 6 `crops` (three config keys, `crop_boxes`, `image_mode`, `change_rects`, four tests). Only P5 needs it. It is
also no longer the mode L39 measured: the rectangles are text changes instead of changed-pixel components (L39's crops
kept the cursor shape; this one cannot), and it sends both half-scale frames where the tag sent one, so L39's $0.174
does not carry over. Make it its own task, run any time before P5, and say in D4 that P5 measures it afresh.

**S6. D4 drops the `text` image mode, which plan 1's "Returns with" table says comes back here.** I agree with the drop
(L39 measured it fabricating a click; principle 4 gives interpretation the frames; D22 leans on its absence). Ruling 3
asks for a stated reason where the promise was made: one ledger line, and the table's cell amended.

**S7. The no-annotation base has two traps in `ask` (ruling 5).** Every `apps` list is empty there, so any search with
`app` returns nothing and the agent may conclude "not found". And the prompt describes frame entries as holding "the
windows … and a prose description" unconditionally. One clause each ("when the record has window labels"; "a filtered
search that returns nothing is worth repeating without app"). Prompt text, not logic. Group-only is safe by
construction (`agree is None` is never `is False`); F5's fixture is the only test on it, and no test should be added.

**S8. One thing findable today does not come back: pane names.** At the tag a pane is a region, and its name is index
text (`"{app} {name}"` heads every region document). Task 10 rule 7 lists containers only, so with plan 2's pane switch
on, the label exists and is not searchable, and P4's "usefulness of a search hit" cannot see it. One more part on the
container line when a pane label is in force. The coordinator decides whether now or with P4; say which.

**S9. Tests beyond what the rules need (ruling 7); about 95 are named.** Plan 1's reconciliation cut its `test_cli_*`
smoke tests at the owner's word; the same applies here. Cut: five of the six CLI tests (keep
`test_run_executes_stages_in_pipeline_order`); `test_scripted_provider`, `test_mini_run_loads` and
`test_stage_loaders_on_a_fresh_run` (tests of test helpers and of a default; keep `test_mini_run_labels`, the tripwire
for plan 2's interface); `test_old_stage_keys_are_rejected` (`extra="forbid"` is plan 1's, tested there);
`test_matched_lines` and `test_collapse_runs_need_consecutive_ordinals` (covered through `search` by three other
tests); the tests that leave with B2, S3, S5. Collapse the three prompt tests into one that checks only the rulings
(no `focus`, no sample strings, `submitted` present): the positive substrings and the ban on ` must `, ` never `,
`Do not` make every P5 wording variant write around a test, which is the design-bending the owner warned of. Keep all
eight findability tests, the two end-to-end tests, `test_validate_citations`, `test_render_without_labels`.

## Nits

- **N1 (D8, Tasks 8 and 15).** No command of the sample is in any prompt; good. Three echoes of the evaluated video
  remain and cost nothing to swap: the boundary example is the tag's Azure scenario with the strings changed (the
  "Create a resource group" page, `rg-demo`, "Review + create", and the label "Create the resource group in the portal"
  verbatim from the tag); the ask prompt's "the line read X at 10:55" falls inside span 2 (10:20 to 12:01); "l and 1, a
  missing space" is L43's finding on the sample. Use a neutral form, another time, and "one character or a space".
- **N2 (Task 15 prompt, first bullet).** "Quote verbatim … when one reader gave the same reading over several sightings
  of the same pixels." A deterministic OCR on unchanged pixels returns the same reading every time, so several
  sightings there are one observation and the count is time on screen. The spec lists only when to hedge (differ,
  `unstable`, seen once). This is the one sentence where persistence works as positive evidence (of a reading, not of a
  run). Cutting the clause is the simple fix; P5 is where wording is judged.
- **N3 (D22).** `missing_png` is a branch for a broken run directory. Task 4 rule 1 raises for the same condition; let
  this raise too. With B2 the whole test goes.
- **N4 (D9).** 80, 60, 25 as module constants against L45's "parameters live in config by the owner's rule": pick one.
  The windowing and overlap vote have never run on real data (the sample has about 220 transitions against a window of
  2,000); port them verbatim with the tag's four tests and spend nothing more on them.
- **N5 (D12).** The anchor rule is acceptable: it gives a pair the value's time range. Listing a link's lines on every
  lifetime it names would need no rule and cost a duplicate hit. Record why the anchor was kept.
- **N6 (D18).** Usage is cold-equivalent (cache hits included). Right for comparison; the `scry run` echo should say
  so, since a re-run pays nothing.
- **N7 (D19, A9f).** Plan 1 kept `outline` first in `STAGES`; appending the new stages is the smaller change.
- **N8 (A9c, A9e).** `run_costs` (here) beside `run_cost` (plan 4) invites mistakes; rename one. Helper imports follow
  `conftest.py` (top-level modules).
- **N9.** `level = "region"` no longer exists; state what `search` does with an unknown level.
- D1, D3, D6, D7, D10, D13, D14, D16, D17 (apart from S5), D20: sound, nothing to remove.

## The review questions, briefly

**A.** B1 and B2 list every stale assumption. Nothing else found: `Revert`, `PixelStats`, `same_place` as a count,
`in_churn`, `unsettled`, `Frame`, and plan 2's joined view (A4) match what the siblings now say. `flicker_new` and
`flicker_lost` are rightly not rendered (H1: nothing changed there).

**B.** Needs the owner: nothing blocks on the owner. To be told: the phrase-across-boxes loss (D below). Coordinator,
with a ledger line: D2 (`entered_text` is the input as frame b shows it, the whole text on submission; sound, agrees
with the ground truth's own column "what the presenter had actually entered" and with plan 4's A11, but it rewords
spec §5, so bring that sentence into line), D4 (S6), D11 (S3), D15 (S2), D18 (S4). Remove or defer: S3, S4, S5, N3.
A9 (a) the stage strings are the tag's pattern, so plan 4 attributes by prefix; (b) already taken up by plan 4's
current text; (c), (e), (f) are N7 and N8; (d) is right, the metrics are plan 4's.

**C.** Everything plan 1's table assigns to plan 3 comes back: interpretation with `scaled` at 0.5 as the default
(L39), `full`, and `crops` in a changed form (S5c); summarisation in full; `build_index`, `search` and `scry search`;
all five agent tools with `get_frame` extended as spec §6 asks; the prompt; the `run` wiring. The tag's search keeps its
tokenizers, query builders, filters, `k`, `k_filtered` and fusion constant. Stated drops: the `text` mode (S6),
`layout_conf`, the `region` level, raw events in `get_transitions`, the diagnostics print at the end of `run`.
Unstated: pane names (S8). Cost is spread over three plans (pricing with cache-creation tokens in plan 2's Task 8,
`run_costs` here, per video and wall time in plan 4) where plan 1's table names plan 4 alone; nothing is lost, the
table should say so.

**D.** Queries that find something today and would not: (1) the admitted one, a quoted phrase across two boxes of one
visual row. It is wider than the plan's wording in two ways. Reading order is top edge then left edge, so three or
more boxes on one row whose tops differ by a pixel interleave, and adjacency fails for table rows in particular. And
in the no-annotation base there are no link lines at all, so nothing restores it. A row-banding rule would be the
machinery the owner removed; the plan is right to add none and to have P1 report each question lost. (2) The same
phrase as a trigram substring containing a space never matches across boxes; the unicode61 ranking still finds it
when the boxes are adjacent. (3) A pane name, even with the pane switch on (S8). (4) Anything with `app` set in the
no-annotation base (S7). I found no other. Unquoted queries are safe because the frame document is a token superset
and the query is an OR. D14 is safe (S1); D15 is needed (S2).

**E.** All three prompts honour ruling 4: the list "does not know who or what changed it", `submitted` is judged from
the frames, time on screen "says nothing" or "is not evidence either way", no focus, the model is asked to look and no
code locates a cursor or a suggestion. Ruling 5: labels and the second reading are described as present only when
shown; the gaps are S7 and N2. Citable ids are handed over in brackets, after and before box alike, and validated
against exactly that list; `summarize` validates refs against the segment's children; `ask` is told the spelling
`12:b4`. Leaks: none of the answer key; the echoes are N1.

**F.** Sixteen tasks can be about ten with no loss: 1 with 2 (scaffolding); 3 into 16 (S4); 5 with 6 less `crops`,
then 7; 8 with 9 (a port); 10 with 11; 12; 13; 14 with 15; 16; `crops` alone before P5. Tests: S9 takes roughly
ninety-five to about seventy.

## For the coordinator to decide

1. B1's renderer shape: one list in record order, or the three headings filtered by kind.
2. S3: drop the `non_text` skip, against the letter of spec §5.
3. S4: remove `cost_usd_batch` across plans 2 to 4.
4. S5: defer the prompt registry, the `get_transitions` paging, and `crops` to a task before P5.
5. S6 and D2: one ledger line each; amend plan 1's table cell and the proposal's §5 sentence on `entered_text`.
6. S2: four families with the corrected reason, or two pools (today's levels as today, lifetimes apart). I would keep
   four: with two, the long frame documents sink under the short transition documents in the shared pool.
7. S8: pane names in the frame document now, or with P4.
8. N2: whether the ask prompt may treat several sightings as licence to quote verbatim.
9. To tell the owner on return: the phrase-across-boxes loss, widest in the no-annotation base, with the
   questions P1 shows lost to it.
