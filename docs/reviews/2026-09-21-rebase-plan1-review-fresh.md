# Review: re-base plan 1 (`read`, `track`, P0), fresh reviewer with no prior context

Reviewed: `docs/superpowers/plans/2026-09-21-rebase-boxes-1-read-track.md` against
`docs/proposals/2026-09-21-boxes-mode-rebase.md` (revision 3) and the code on `rebase-boxes` at `d148751`
(`detect.py`, `settle.py`, `stage1.py`, `decode.py`, `stage2a.py`, `ocr/`, `diff.py`, `schemas.py`, `run.py`, `jsonl.py`,
`cli.py`, `config.py`, `subset.py`, `index.py`, `overlay.py`, `textdiff.py`, `diagnostics.py`, `merge.py`, `coalesce.py`,
`pyproject.toml`, `scry.toml`, `tests/`, the listing of `runs/aks` and its manifest, `docs/ground-truth/span2-commands.md`).

Method: reading and reasoning only. No prototype, script or experiment was written or run, no model call was made, and
nothing was edited but this file. All arithmetic below is by hand. (One shell listing command carried a stray
`python3 -c "print(1)"`; it evaluated nothing and informed nothing.) Numbers marked **[estimated]** are reasoned, not
measured.

**Verdict: accept with changes.** The plan is executable, its order is the pipeline's, every fixture value I recomputed
agrees, and the legacy import and P0 commands cannot write into `runs/aks`. Two things must change before it is run,
because as written P0 hands back one wrong number and cannot test one of its eight hypotheses.

## Blocking

**B1. Task 13 rule 6 prices incremental annotation by a rule the spec does not have.** The plan counts
`calls = 1 + changes with at least one target`. Spec §2 (restored at the owner's instruction, commit `0b132d8`): "A call is
made whenever pixels changed, even if no box did, because the screen `description` must be refreshed … a transition with
no changed pixel makes no call." Every emitted pair has changed pixels by construction, so the honest figure is close to
one call per frame and what incremental annotation saves is target boxes, not calls. P0's ledger row ("prices P3 in
advance") would understate P3. Fix: `calls = 1 + changes with pixels null or components > 0`; keep the plan's figure beside
it as `calls_with_targets`. `test_incremental_projection` hard-codes `calls 3` under the wrong rule and gives its three
changes no pixel statistics; it needs them. Smaller, same rule: a one-to-one `reread` continues its lifetime (Task 10
rule 4), so by spec §5 ("labels come from … the latest record of its lifetime") its after box is not a target; targets are
exactly the transition's `starts`.

**B2. P0 Step 6 asks for evidence the plan never produces.**
- **H3** ("every transition with `moved ≥ 10` … five moved pairs each"): `Change.moved` is a bare count, `Lifetime.moved` a
  bool, `Pairing.how` is not persisted, and `write_sheets` (Task 15 rule 2) samples groups, appeared, removed, reverts,
  unstable lifetimes and flicker, not moves. Under the no-scratch-code rule the executor has no way to list moved pairs.
  Fix without changing a record: a `moved` sheet kind; `write_sheets` has `run` and `cfg`, so it can call `track_pair` for
  the sampled transitions and read `pairings`.
- **H1** ("is any unstable lifetime a real change that the veto hid?"): the lifetime sheet shows only the first and last
  sighting. A lifetime with readings {A: 25, B: 1} read B somewhere in the middle; the sheet never shows that frame. Fix:
  one strip per change of reading (sighting i−1 above sighting i wherever the text differs), derived from
  `Lifetime.boxes` and `boxes.jsonl`.

## Should-fix

**S1. Task 3's file list omits three files that import `OcrConfig`**: `src/scry/ocr/__init__.py:3`,
`src/scry/ocr/rapid.py:20`, `tests/test_rapid.py:47`, plus the two tests Task 2 has just written against `OcrConfig`. Also
unlisted: the bodies of the renamed `decode.py` (`from scry.decode import …` → `scry.video`, `cfg.stage1`, `Stage1Record`,
`run.stage1`) and `tests/test_video.py`'s import. `test_every_module_imports` catches it, so the commit self-corrects,
but "from the plan alone" fails here.

**S2. `trivial` was ported into a context that removed its guard (Task 12 rule 2).** Old `tag_trivial`
(`coalesce.py:206`) needed every op to be a clock op; a scroll or window drag produced non-clock ops, so it could never be
trivial. Now moves are cancelled and are not groups, textless components and `same_place` are counts, and the rule looks
only at groups, `appeared`, `removed`. A window drag, a ticked checkbox or a highlight change that coincides with a clock
tick is `trivial`, and spec §6 gives `interpret` "one call per non-trivial transition": the action becomes unfindable.
Fix: also require `moved == 0`, `same_place == 0` and `pixels.textless == 0` (or `pixels is None` → never trivial), with a
negative test.

**S3. Two predictable consequences belong on P0's reading list (no new logic).**
- *Reading order is an exact `(y0, x0)` sort (D7) and now decides kinds.* A side's text is its boxes joined in reading
  order (Task 10 rule 2). `"File Edit View"` re-split into `"File"` (y0 = 11) and `"Edit View"` (y0 = 10) joins as
  `EditViewFile` ≠ `FileEditView`: `changed`, not `reread`. Step 6's H4 reads only `reread` groups, so these hide among
  `changed`. Add: "multi-box `changed` groups whose boxes share a visual line".
- *Moves run before groups (spec steps 5–6), so a command typed and submitted between two frames (G1 entries 4, 5, 7, 9)
  will not be `appended`.* Frame *a* ends with a bare `PS C:\Users\msadmin>`; frame *b* has that row grown plus a new bare
  prompt lower down. The bare prompts are equal texts and cancel as a move; the grown row has no earlier self left and is
  `appeared`. The spec's ordering, not the plan's, but Step 6 H2 asks only about "`appeared` + `removed`"; add
  "`appeared` beside a moved prompt".

**S4. `char_diff` on a window switch is quadratic pure Python [estimated].** `textdiff.myers` stores `dict(v)` per `d`
(`textdiff.py:42`): Σ(2d+1) = (D+1)² dict entries and about D²/2 inner iterations. A terminal ↔ portal switch (181→182,
184→185) touches every box, cancels little, and rectangle intersection chains the rest into one or a few groups. With
about 100 boxes × 15–25 characters a side, D approaches N + M ≈ 3,500–5,000: 12–25 million entries (several hundred MB to
about 1 GB) and tens of seconds for one transition. No cap is wanted (that would be a fitted constant); state the risk in
Review Focus, log seconds per transition in `run_track`, and let P0 report it. `rapidfuzz` (already a dependency) gives
the same edit script in C if it bites.

**S5. Rules without a test, in order of importance.** (a) Task 12 rule 4 exists per component for "undoes the previous
change while something else also changes" (D14), and neither revert test has anything else changing: add frame 2 = black
plus a new block elsewhere → the revert is still recorded; and two components in *z*→*a* with one undone → one revert.
(b) `rect_only` through `track_pair` (the hollow-outline fixture → `rect_only == 1`). (c) `trivial` negative (clock group +
one appeared → `single`). (d) `Group.in_churn`. (e) two groups in one change, fixing the order and therefore the `j` of
`continues`. (f) `changed_fraction` counting sub-θmin pixels that `labels` excludes.

**S6. Drops and additions the plan does not declare** (owner's rule: nothing dropped without a stated reason).
`agreement` per box is "Kept" in spec §8 and goes with `merge.py` and `[merge] glyph_max_len` unmentioned; say it returns
from the tag with `annotate`. `tests/test_schemas.py::test_config_defaults_and_hash_are_stable` is deleted and not
re-homed in `tests/test_config.py`. The `search` and `index` CLI commands have no stated return point (D3 says only "no
CLI command for either"). `FrameBoxes.seconds` and the twelve-key `engine.settings()` dict (spec sketch: `name`,
`version`) are additions missing from D13; `settings()` carries `space_guard_fired`, a running counter, so the "engine"
of frame *k* differs from frame *k*+1. Put the counter in the manifest only.

**S7. Task 5 leaves one case undefined.** Today the CLI's `Run(src)` (`cli.py:129`) creates `src/cache`; Task 5 rightly
stops that. With the default `share_cache=True` and a source that has no `cache/`, `subset.py` makes a dangling symlink
and `Run(out)`'s `mkdir(exist_ok=True)` raises `FileExistsError`. State the rule (no link when the source has none). Not a
P0 risk: `runs/aks/cache` exists and Step 1 passes `--no-share-cache`.

**S8. Task 16 command robustness.** Step 5 copies `manifest.json` with `stages.track` inside; if the `sed` pattern does
not match (`margin = 0.5  # …` in `scry.toml`), the hashes are unchanged, `track` skips itself in a directory that has no
`changes.jsonl`, and the report is silently empty. Add `grep -c "^margin = $M$" runs/p0-m$N.toml` (expect 1). Step 4's
three reports write sheets into one `sheets/` directory with three different samples; say whether `write_sheets` clears
it or name it after `--out`. The report's `## Run` should take margin from the `track` manifest entry, not from whatever
`--config` the report was given.

## Nits

- `test_duplicates_pair_same_place_first_then_reading_order`: *after* `b1` has y0 = 100 and `b2` y0 = 10, which `read`
  can never emit (D7). The result does not depend on it; renumber.
- Tests with no concrete fixture despite the claim in Self-review: `test_unequal_counts_leave_the_surplus` (no
  coordinates), `test_moved_sets_the_flag`, `test_unaccounted_box_raises`, `test_zero_and_one_frame_runs`,
  `test_missing_boxes_record_is_an_error`, `test_malformed_row_raises` ("line 5" of which fixture).
- Task 1: `git rm -r src/scry/prompts` leaves `prompts/__pycache__`; the directory is then a namespace package and
  `find_spec("scry.prompts")` is not `None`. Delete the directory itself.
- `test_old_machinery_is_gone` forbids `scry.schemas.Interpretation`, a name spec §8 brings back.
- `test_repo_toml_loads` depends on the working directory; anchor on `__file__`.
- `test_report_frames_filter`: `T1` still occurs in T2's `continues == "T1/0"`; assert on the table rows.
- Task 2 never says to add `gap_ratio = 0.25` to `[read]`, which Global Constraints require.
- `components` becoming `label_components(...)[1]` puts a relabel on `decode`'s per-video-frame path for nothing; keep
  `components` and share a helper.
- `PairResult.ends` is unused by `LifetimeBuilder`. Group order `(rect[1], rect[0])` has no tie-break.
- Spec says tag `pre-rebase`; the repository and the plan say `pre-rebase-boxes`. The plan is right; fix the spec.
- The `subset` echo still promises "`scry run` … runs the rest", which D6 says is false for an imported directory.
- Step 1's check: `runs/` is git-ignored, so "`git status` clean" says nothing about `runs/aks`, and `ls` compares names
  only. `find runs/aks -newer runs/p0/manifest.json` printing nothing is a real check.

## The eight questions

**1. Executability.** Yes, apart from S1. Rules are sequential, none circular. Walked by hand: *no boxes* → `margin_px` 0,
every component textless, share 0.0 (tested). *No changed pixels* → `(zeros, [])`, nothing touched, all unchanged or
flicker, `single`. *Different sizes / missing PNG* → `diff None`, all touched, identical boxes fall to `same_place`
(tested). *A box on two components* → `touched_by` is a set; only textless counting reads it. *Two later boxes claim one
earlier* → greedy by area, loser is `flicker_new` (tested; note the survivor's lifetime gains a "variant" that is really
a different rectangle, so `unstable` overstates "same pixels"). *Empty text* → dropped by `read`. *Duplicates* →
same place first, then k-th with k-th (tested). *Growing text, untouched neighbour* → D8 pulls the shorter self in
(tested); a neighbour inside the margin becomes `same_place`. *Scroll* → moves; top and bottom rows do not intersect →
`removed` + `appeared` (tested); a scrolled row with a spacing flip is not a move under D11 and fragments its lifetime,
which H7 will show. *Revert plus another change* → per-component test handles it (untested, S5a). Two implementers agree
on all three record files except `FrameBoxes.seconds`; sheets and report layout will differ, which is harmless. Silent
cases: S2, S7, S8; "positive-area intersection" admits 1–2 px sliver overlaps between adjacent rows in Task 8 rule 3 and
Task 10 rule 1 (spec §11 accepts "no threshold"; P0's H1 and H2 readings will show it).

**2. Tests.** Every value recomputed agrees: stem 10 and glyph 60 px, noise labels 1–3 dropped so kept labels are 1 and 2;
grown `(41,9,99,41)` misses x = 40, `(40,8,100,42)` includes it and excludes x = 100; outline 40+40+120+120−4 = 316;
`grow` → `(0,0,15,17)`; margins median 20 → 10 and ⌊10.5+0.5⌋ = 11; 200/2,400 = 0.083333; 14×88 = 1,232 and /80,000 =
0.0154; `a.b2` grown `(1,41,139,77)` ends before x = 140; 190×18 = 3,420 and 170×18 = 3,060; tie-break order
(50,0,0),(50,0,1),(40,1,0) → `[(0,0)]`; shares 1/5 = 0.2 and 1/3 = 0.3333; hold 3.8 − 1.0 = 2.8; frame-1 box grown to
x1 = 179 > 176, so T2 is touched and `continues == "T1/0"`; 146/149 = 0.9799; median(0.01, 0.02) = 0.015; 113/415 =
0.2723; 652.0 − 649.17 = 2.83; `estimate_cost` = 5 + 2.5 = 7.5. The ground-truth regexes parse every row of the real
`span2-commands.md` as intended (checked rows 1–9 and the five never-run rows; no cell contains `|`). I dispute no
value, only `calls 3` (B1). Missing tests: S5.

**3. Commit order.** Holds after every commit except S1. Checked: after Task 1 no kept module imports a deleted one
(`textdiff` loses `DiffOp`, `index` loses `Region`, `overlay` loses `Run`/`Config`, `run.py`'s schema import shrinks;
`providers/`, `outline.py`, `detect.py`, `ocr/base.py` need only kept names; `ocr/vision.py` imports PyObjC lazily and
PyObjC is still a dependency until Task 2). `scry.toml` is cleaned in the same commits as the models, and
`extra="forbid"` arrives in Task 3 with `test_repo_toml_loads` guarding it; it is the repository's only config file
(`runs/*.toml` are git-ignored and will rightly fail). No CLI command survives its module. `uv lock` in Task 2 needs the
network once.

**4. Safety.** `runs/aks` holds `stage1.jsonl` (221 lines, frames 0–220), `manifest.json` with `stages.stage1`, 221 PNGs,
`cache/`, `overlays/`, `ocr.jsonl`, `audit.json`, and no `frames.jsonl`. After Task 5 the CLI builds no `Run` on the
source; `make_subset` reads two files and copies PNGs; `--no-share-cache` makes no link into `runs/aks/cache`. Steps 2–5
name only `runs/p0*`; the margin directories link to `../p0/frames`, and `Run.__init__` tolerates a symlinked directory.
Nothing writes into `runs/aks`. The standing hazard is the default `--share-cache`, which hands later model stages a
writable link into the source's cache; consider refusing it for a legacy source.

**5. Constants, thresholds, tie-breaks.**

| Item | Verdict |
|---|---|
| θpix 12, θmin 8, 3×3 dilation, 8-connectivity | inherited from `decode`; absolute pixels, calibrated on the sample; acknowledged in spec §11, alarmed by `touched_share` |
| margin 0.5 × median box height of both frames, ⌊x + 0.5⌋, clipped | scale-free; 0.5 is inherited (L38) and P0 varies it; a frame-wide median gives small text a relatively large margin |
| intersect = positive area; greedy by area, then index in *a*, then in *b* | threshold-free, deterministic; sliver overlaps admitted |
| reading order = exact `(y0, x0)` sort | no constant; 1-px jitter reorders a visual line (S3) |
| exact equality for same place and moves; whitespace-blind kinds; single-space join | principled |
| clock regex `\d{1,2}:\d{2}…` | inherited heuristic; also matches `80:31` in a port mapping, and with S2 that transition is skipped |
| revert = zero labelled *z*→*b* pixels on the component's own pixels; `hold_s` = Δ`t_change` | threshold-free; all-or-nothing, so one kept component (a pointer) cancels it; blink-phase carets will log reverts |
| majority tie → first sighted; smallest first frame, then id | deterministic |
| lower half by `changed_fraction` (⌈n/2⌉) | rank, not fitted; "half" is arbitrary and is not "near-static" on a busy video |
| scorable ≥ 4 non-space characters | fitted to this list (drops `Y`, `y`); evaluation only, reason stated |
| `gap_ratio` 0.25 | scale-free; value measured on the sample's 18-px terminal text; pre-existing, listed in spec §11 |
| rounding to 6/4/3/2 places; top 20, 20 lines, 50 lifetimes, 30 per kind, crop 2 × margin, gray cache 8 | presentation or performance; with margin 0 the crop has no context |

**6. Drops.** Stated with reason and return point: `agent.py` and `prompts/` (D2, `ask`), `run_overlay` and node extraction
(D3, file list), `Stage5Config`, `HierarchyConfig`, `effort_*`, `stage2c_*` (D4), Vision adapter, PyObjC, the `rapid`
extra (D1), `confusable` and empty-text boxes (D5; "nothing in the spec consumes it" is thin for a measured flag the agent
could hedge on, owner to confirm), `found` (D21), README and CONTRIBUTING (Self-review). Stated by the spec: the row
modules, their schemas and tests, `[merge]`, `[diff]`, the old diagnostics. Not stated: see S6; also `Run`'s paths for
later stages (`interpretations`, `steps`, `sections`, `video`, `index_db`), `perceive._run_with_batches`, the
`diagnostics` manifest entry, and `[stage5] images = "scaled"`, `scale = 0.5` (owner's decision L39, recoverable only from
the tag).

**7. Fidelity to §5 and §6.** Faithful in shape and order. Divergences: declared D8 (pools admit untouched boxes; step 4
says "touched"), D9 (flicker), D10 (one-to-one, not "overlaps most"), D11, D12 (only one-to-one `reread` continues), D13
(eight added fields), D14, D15, D20. Undeclared: B1; `FrameBoxes.seconds` and the `engine` shape; moves restricted to the
pools (step 5 says "anywhere in the transition"; correct under H1, say so); `PixelSource` rewritten, not moved (§8);
three removal commits for §10's one; tag name; `agreement` dropped. The Vocabulary's lifetime ("re-read with only
whitespace differing") is narrower than Task 8 rule 3, where any differing text on untouched pixels is a variant; that
is spec step 3, and P0's H1 reading is its test.

**8. Size.** About right; sixteen tasks, each one commit. Cuttable without touching P0's result: `PairResult.ends`, the
`gap_ratio` config key, the `test_cli_*` tests, the never-run `frames` parse; Task 2 is not needed for P0 but is spec
§10 step 0 and small. Missing for P0: B1, B2, seconds per transition (S4), the margin-run guard (S8), and the two
reading-list additions (S3).

## Required changes

1. Task 13 rule 6 and its test follow spec §2: calls are counted on changed pixels; targets are `starts` (B1).
2. `write_sheets` gains moved pairs and per-reading-change strips for unstable lifetimes (B2).
3. Task 3's file list is completed (S1); `trivial` regains its guard (S2).
4. S3–S8 as written, none larger than a paragraph of plan text or one test.
