# Review (with context): build plan 1, `read`, `track`, P0

Reviewed: `docs/superpowers/plans/2026-09-21-rebase-boxes-1-read-track.md` at d148751, against
`docs/proposals/2026-09-21-boxes-mode-rebase.md` at the branch head (41b54fe: description and whole-screen index
entries kept) and the owner's rulings in the session. Read-only: nothing was run except reading files; every fixture
below was checked by hand. No prototype, script or experiment was written.

**Verdict: accept with changes.** The plan is faithful to the redesign: no rows, no containers, no focus, no folding,
no "typed", no persistence reasoning, no cursor logic, margin relative to box height, no thresholds in P0. Every
expected value I recomputed agrees with the plan (list at the end). The changes below are about one grouping rule that
real box geometry will break, one rule that contradicts the proposal as the owner last amended it, two drops the owner
has not sanctioned, and bookkeeping between the four plans.

## Should-fix (none is blocking on its own; S1–S3 should be settled before code)

**S1. Groups as connected components over *any* positive intersection will chain vertically adjacent lines (Task 10
rule 1, D12; also D8's pull-in).** RapidOCR's boxes for adjacent terminal lines overlap by 3–6 px and widely in x.
Evidence, read from the stored boxes of frame 178 (`runs/span2-before/ocr.jsonl`): `l76` y 602–621 and `l79`
y 618–638; `l80` 635–655 and `l84` 649–674; `l94` 716–741, `l97` 736–755, `l99` 752–771. With the margin at half a
box height (≈ 10 px) and a line pitch of ≈ 17 px, the line above a typed line is *touched* whenever it extends over the
typed position. Usually it reads the same and leaves as a `same_place` pair. When its OCR text jitters (box stability is
96.5 %, so a few percent of pairs), it stays in the pools, and the sliver overlap joins it to the typed line's group:
before `"… cmd1 PS>"`, after `"… cmdl PS> git status"`, kind `changed` instead of `appended`, two lines in one record.
A terminal redraw becomes one group holding every line. The plan's fixtures never show this because their lines are
spaced (Task 9's scroll fixture says "equal texts never intersect"; with real boxes a one-line scroll makes them
intersect, so they pair as `same_place`, not `moved`, which also mislabels what P0 reads for H3).
Remedy that needs no constant and reuses the plan's own rule: form groups from the one-to-one greatest-intersection
matching (Task 8 rule 2) first, then attach each leftover box to the group of the box it overlaps most; a box that
overlaps nothing stays appeared or removed. Add a fixture with 20-px boxes at 17-px pitch: a keystroke under a line
whose reading differs must still give one `appended` group for the typed line and a separate `changed` or `reread`
group for the neighbour.

**S2. An untouched box pulled into a pool (D8) can come out as `appeared` or `removed`.** If the touched box it
intersected leaves through `same_place` or a move, the untouched box has no partner and rule 1 of Task 10 reports it as
appeared or removed although no pixel changed under it, against principle 2. With sliver overlaps and icon-glyph
flicker (1.6 % of boxes per pair in `scratchpad/box-stability/result.txt`) this will happen next to every changed line.
Rule to add: an untouched pool box left in no group falls back to `flicker_new` / `flicker_lost`.

**S3. `incremental_projection` contradicts the proposal as amended (Task 13 rule 6).** Since 0b132d8 the proposal
says an incremental call is made *whenever pixels changed, even if no box did* (the screen description must be
refreshed; owner's ruling). The plan counts a call only for transitions with a target box, so P0 would overstate the
saving and misprice P3. Count `1 +` every change with `pixels.components ≥ 1` (report separately how many of those
have no target box), keep `target_boxes` as is; the test's `calls` becomes 4 if all three changes have pixels. Since
`decode` only emits on change, calls ≈ frames: the saving is in tokens per call, which is the honest message. Add a
dollar line with stated assumptions (owner: cost beside every number); today the row has counts only, and the ledger row
should also state `$0` and seconds per frame for `read` and per pair for `track`.

**S4. Two drops without the owner's sanction.**
- *`confusable` (D5).* Today `read` flags a token mixing ASCII with a non-Latin letter; the flag rides on every line
  into `frames.jsonl` and the index payload the agent reads (`merge.py:59`, `index.py` payload). Nothing else consumed
  it, so no behaviour is lost, but it is free, measured, additive, and the design lists it as the mitigation for
  look-alike glyphs in identifiers (design §8.1, §17); the first live run had exactly that case (Cyrillic letters in the
  subscription id, L28). "Nothing in the spec consumes it" is the reasoning the owner rejected for the screen
  description. Keep it as a field of `Box` (one function moves from `stage2a.py`), or put it to the owner.
- *The clock rule (`Group.clock`, kind `trivial`; Task 10 rule 3, Task 12 rule 2).* It is in the proposal, but it is a
  regex that decides a transition is trivial, which later means uninterpreted, and it has never fired: `trivial: 0` in
  every recorded run (L28, L29, `runs/span2-before`). By principle 7 (no logic until the real implementation shows the
  case) it should wait for evidence. Proposal-level; for the owner.
Dropping empty-text boxes (counted) and keeping the unread `caret` field (D19) are fine.

**S5. Task 1 deletes working capabilities that other plans must bring back, and nobody has the list.** Plans 2–4 are
being written against a tree where these files still exist. Add a "returns with" table to plan 1 and hand it to the
synthesis pass: `overlay` stage wrapper and the `stage2c_*`/effort keys → plan 2; `[stage5] images = "scaled"`,
`scale = 0.5` (owner's decision, L39), `interpret`, `hierarchy`, node extraction, `scry index`, `scry search`,
`agent.py` loop, tools and the four prompts → plan 3 (restored from tag `pre-rebase-boxes`, since the files are gone);
the label-reading diagnostic `mark_match` (the check that caught unreadable labels, L28–L30) and cost accounting with
cache-creation tokens → plan 2 or 4. Gone for good, each by an owner ruling: row machinery, Apple Vision (D1 moves it
from the last step to the first commits, which is harmless), caret and focus attribution, transient folding. D2
(deleting `agent.py` whole, where the proposal removes only its tools) is a deferral, not a drop, but belongs in the
table.

**S6. Task 3's file list is incomplete.** `OcrConfig` → `ReadConfig` also touches `src/scry/ocr/__init__.py`,
`src/scry/ocr/rapid.py` and `tests/test_rapid.py` (all import `OcrConfig`), and Task 2's two new tests. State the
`git mv` order (`decode.py` → `video.py` first). Green-after-every-commit is otherwise achievable: I traced the
imports of every kept module and test (`run.py`, `textdiff.py`, `overlay.py`, `index.py`, `providers/`, `subset.py`,
`settle.py`) against Tasks 1–4 and found no other dangling import.

**S7. `continues` is undefined when the earlier box *appeared* in the previous transition** (a new prompt line that
then grows): its ref is in `prev.appeared`, not in a group, so rule 3 of Task 12 gives `None`. Define it (for example
`"T8/appeared"`) or say it is deliberately null.

## Nits

- N1. Reading order by `(y0, x0)` flips on 1-px jitter between boxes of one visual line (real-run evidence: L31).
  The blast radius is now small (joined text of a multi-box group side, pairing of duplicate moved strings), but a
  re-split line can read `changed` instead of `reread`. Watch in P0; no rule until seen.
- N2. Unchanged matching accepts any positive overlap ("overlaps most" has no floor, as in the proposal). Record the
  overlap ratio of each unchanged pair whose texts differ so P0 can see sliver marriages without adding a threshold.
- N3. `scorable` uses a length of 4 (D17). A rule without a number: match short entries as a whole whitespace token in
  a lifetime alive between the entry's first-visible and submitted frames. Also, rows 4–5 of the real list put the
  *question's* frame first in column 3, so "first pair" gives the wrong first frame for `Y` and `y` (harmless while they
  are unrated).
- N4. `touched_share_low_half` is a rank rule, fine as a guard; print the quartiles too.
- N5. `exact` needs the whole command inside one box's lifetime; a command OCR splits in two can never be exact at
  this step (no `run` links yet). Say so in the report: the OCR reader's rate is a lower bound.
- N6. The proposal says `PixelSource` and the margin helpers are *moved* into `track`; Task 1 deletes `diff.py` whole
  and Task 7 rewrites them. Moving the tested code keeps L32's swscale detail from being re-derived.
- N7. `subset --share-cache` must not create the source's `cache/` when absent (today `Run(src)` would have).

## Decisions: whose they are

Implementer's, all consistent with the proposal: D1, D3, D4, D6, D7, D9, D10, D11, D13–D16, D18–D21. D8 and D12 stand
with S1 and S2 applied. For the owner: D5 (`confusable`) only. D2 is fine once S5's table exists.

## Degenerate cases walked (by reasoning)

No boxes; no changed pixels; different sizes or a missing PNG; a box touching two components; two later boxes claiming
one earlier box (untouched and touched variants); empty text; duplicate strings under a scroll; a text growing beside
an untouched neighbour; a revert while something else changes (per-component test on the component's own pixels,
sub-θmin residue ignored as in `decode`): each is defined and has a test. Undefined: S7; S2's leftover pool box.

## Fixtures recomputed by hand, all agree

Task 7: areas 10 and 60, label numbering among kept components, halo 0, outline area 316 (320 − 4 corners), grow
`(0,0,15,17)`, margins 10 and 11, fraction 200 / 2,400. Task 8: fixture K pools and flicker (`a.b2` grown to x 139, the
component starts at 140); intersections 3,420 and 3,060; the tie-break walk. Tasks 9–10: scroll, duplicates, keystroke
(`touched_share` 1 / 5, `ends` `b2`, `b3`), popup (`textless_area` 100, share 1 / 3). Task 11: the three-frame
lifetimes and the tie. Task 12: revert rectangle `(300,100,380,120)`, hold 2.8 s; `continues "T1/0"` (the second
component reaches x 176–178 inside the grown earlier box). Task 13: 146 / 149 = 0.9799; median 0.015; 113 / 415 =
0.2723. Task 14: frame error 1, time error 2.83, rate 2 of 2.

## P0 task

It produces what proposal §9 asks: H1–H8 read against frames with sample sizes and no pass thresholds, four margins
on light directories that share frames, fragmentation, the incremental projection (after S3), and the OCR reader's
exactness against the accepted command list; *found* rightly waits for the index (D21). The legacy import is
non-destructive (path parameter, no `Run(src)`, `--no-share-cache`, stage commands instead of `run` to avoid a
re-decode). Add cost ($0) and per-frame wall time to the ledger row (S3).

## For the owner's eyes

1. Keep the `confusable` flag on boxes? It was dropped only because nothing reads it yet.
2. The clock regex that marks a transition `trivial` has never fired on any run; by your rule it should wait for
   evidence. Drop it from the proposal for now?
3. Incremental annotation will save tokens per call, not calls: with your description ruling nearly every transition
   still makes a call. P0 will report it that way once S3 is applied.
