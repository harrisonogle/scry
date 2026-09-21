# Review: re-base plan 4 (evaluation harness) and the span-2 question set, lean lens

Reviewed: `docs/superpowers/plans/2026-09-21-rebase-boxes-4-evaluation.md` (14 tasks) and
`docs/ground-truth/span2-questions.md`, against the spec (revision 3.1, §9 and §12), ledger L42 to L46,
`docs/ground-truth/span2-commands.md`, plan 1 (Tasks 13, 14, 16), plan 2 (interface assumptions, decisions, Tasks 1, 4,
9), plan 3 (A1 to A9, Tasks 1 to 3, 7, 11 to 13, 15, 16, its decisions), the three reviews of plans 2 and 3 where they
touch plan 4, and the branch's `costs.py`, `subset.py`, `config.py`, `schemas.py`, `providers/anthropic_.py`,
`providers/cache.py`. Frame times were read from `runs/aks/stage1.jsonl`.

Method: reading and reasoning only. No prototype, script, experiment, test run or model call; nothing edited but this
file. All arithmetic is by hand. **[estimated]** marks a reasoned figure.

**Verdict: accept with changes.** What the plan specifies is careful and its fixtures recompute (every value I checked
agrees). Two faults must be fixed before P1 (B1, B2). The larger change is by deletion: P1 needs roughly half of the
plan. The rest is machinery ahead of any phase that uses it, some of it for a human who is not there, and the owner's
rule (L44, spec §12) says not to build it yet.

## Blocking

**B1. *Found*, the submission error and *false run* are defined by no plan.** Plan 4 consumes `score_found`,
`found_rate`, `score_submitted` and `score_false_run` "from plan 3's Task 16". Plan 3's Task 16 is `scry run`; its D20
and A9 (d) say "no metric is defined here … plan 4's Task 4 defines them", and both plan-3 reviews agree (rulings: "(d)
is right, the metrics are plan 4's"; executability S9: "have no owner"). One of the two primary scores has no
definition; N4 discusses the behaviour of functions that do not exist. Fix, on plan 4's side, in Task 4, one rule each:
- *found* (scorable entries): `search(db, '"' + text + '"', cfg.index, embedder=None)` (plan 3 Task 13; its D20
  guarantees a quoted query stays a phrase). Found when some hit's `frames` range intersects `[first_frame,
  submitted_frame]` (see B2). Keep rank and level of the first such hit.
- A *claim* is a transition whose interpretation has `submitted == "yes"` and a non-blank `entered_text`. It matches an
  entry when `norm(entered_text) == norm(entry.text)`, case-sensitively like *exact* (plan 3 D2: `entered_text` is the
  whole input without the prompt). Executed entries, in list order, each take the unclaimed matching claim whose
  `to_frame` is nearest their `submitted_frame` (tie: the earlier). Submission error = `to_frame − submitted_frame`, and
  in seconds from the run's own `frames.jsonl` (`t_settled` of the two frames).
- *false run*: a never-run row whose text equals a claim that is left over after the executed entries took theirs.
  No frame condition.
This one rule replaces both D4 guards: equality already keeps `Y` and `y` apart from everything else and from each
other, and a claim consumed by executed row 6 cannot also be a false run of never-run row 4, so `guard_submissions`,
`flag_shared_claims` and `submission_notes` go.

**B2. "Covering its time" compared in seconds fails on the ground truth's own rounding.** The command list prints
`t_settled` to two places; the records carry the full value. Entry 7 (`kubectl get nodes`, never seen being typed):
the parser gives first = submitted = (180, 702.03), so the window is the point [702.03, 702.03]. Frame 180's
`t_settled` is 702.0333…, so the scrollback line's lifetime starts at 702.0333 > 702.03, the frame entry `f180` starts
there too, and the transition entry T(179→180) has `t = (a.t_end, b.t_settled)` = (702.0333, 702.0333). No localising
entry intersects the window: entry 7 is "not found" in every configuration, for 3 ms of rounding, unless a step, section
or video summary happens to quote it. `exact_in_window` fails the same way (rule 4: `lifetime.first.t ≤ window[1]` is
false). Entry 9 (721.0 against 721.00), and entry 8 if its line is first read exactly at frame 186 (716.9 against
716.90), pass only by float equality at the boundary. Fix: compare frame numbers. The ground truth has
them, every hit carries `frames` (plan 3 Tasks 10 to 13), subsets keep frame numbers, and no tolerance constant is
needed.

## Should-fix

**S1. Nothing in P1 may wait on a tick-sheet, and nothing in P1 uses one.** The procedure's step 3 has the owner tick
`answer-sheet.md` and `label-sheet.md` between the run and the report, and Task 7 rule 7 says the judge's verdicts are
"never reported without the agreement check of Task 8 beside them". With nobody to tick, Task 8 reports `None` and Task
9 reports nothing. Strike rule 7; defer Tasks 8 and 9 (verdicts below). What replaces Task 8 for now costs nothing:
`scores.json` keeps each answer with the judge's per-line verdict and quote, so the owner can audit the judge from
committed data whenever he likes.

**S2. Drop `reading` (Task 12 rule 9, D7).** It prints "A ahead on found (outside the noise)". (a) `COMMAND_ORDER` puts
*found* strictly before *exact*; the owner named both primary and gave no order between them. (b) Both primaries are
monotone in spend: more index text can only add lexical hits, and `exact.any` with a second reader can only tie or
rise, so the sentence will name the dearer base or nobody. (c) The floor is about 1.5 standard deviations of the
difference (S3), too weak to carry a sentence. The table of rows is the evidence; the coordinator reads it.

**S3. The noise floor: keep the definition, say what it is, drop what P1 does not use.**
- The scaling rule is right: the variance of a difference of means of `n_a` and `n_b` runs over that of a difference of
  two single runs is `(1/n_a + 1/n_b) / 2`. Checked: 1, 0.7071, 0.5774; (0.3, 3, 1) → 0.3 × 0.8165 = 0.244949.
- With equal unit sets the mean of unit differences equals the difference of run means, so `floor_single` is the range
  of the repeats' run values. "Largest paired difference" is already the simplest sane floor, and it is how L42 reports
  noise. Keep it; drop `median` and `pairs`.
- With 3 repeats it is a range of three: about 1.7σ for one configuration and about 2.2σ pooled over two **[estimated,
  normal approximation]**; × 0.577 gives about 1.3σ against a standard deviation of 0.82σ for the difference of means,
  so about 1.5 standard deviations: roughly one `outside` in eight where nothing differs, per metric and comparison. P1
  on span 2 has 3 comparisons × about 10 metrics, so a few chance `outside` rows are expected. Put one sentence saying
  so in the report header; never let a single `outside` row decide anything (S2).
- In P1 `exact.ocr`, and *found* wherever OCR's reading suffices, are functions of `read` and `track` only, which are
  model-free and identical across the three bases and all repeats: floor 0 and difference 0 by construction. P1's
  discriminating evidence is the question set, `exact.vlm`, the secondary metrics and cost. That is why the lean cut
  must not touch Tasks 6 and 7 and can cut deep around Task 4.
- `floor`, `floor_match`, `floor_lookup` and `noise.json` serve P2's two-repeat screens (one pair can be 0 by chance, so
  pooling P1's floor there is right). Defer to P2. `floor_match`'s default `("base",)` is an axis name of one phase
  sitting in code.

**S4. Cost: drop the second source.** Plan 2 D23 (Task 9 rule 9) and plan 3 D18 (Task 7) both define a stage's manifest
`usage` as the sum over its records, cache hits included, "what a cold run would pay". A resumed run therefore cannot
under-report, and Task 1 rule 4, `cache_usage`, `sources` and `test_resumed_run_costs_come_from_the_call_cache` are
redundant; N7 dissolves, and so does plan 3's A9 (a) (the `summarize-boundary-*` stage strings that `cache_usage` would
have mis-grouped). `cold` should mean the structural fact (private cache, empty at start, recorded at materialise); a
non-zero `cache.hits` is a count to print, since identical inputs inside one run or a resume also produce hits.

**S5. D12: record, do not refuse, and no metric-code hash.** Implementation agents work in this tree in parallel (L44:
parallelise), so `src/scry` is often dirty and the refusal becomes a habitual `--allow-dirty`. Scoring is free and
`report` rescores every run it reads, so all scorecards in a report are scored by the same code by construction; a hash
"changed since the run started" detects nothing that matters, because runs do not depend on metric code. Keep: the
commit and the dirty paths in `evalrun.json`, the distinct commits in the report header.

**S6. Commit only `evals/p1.toml`.** The owner: sequencing is decided one step after another from results. `p4.toml`
and `p5.toml` hard-code a base "committed as `grouponly`" before P1 has run. And
`test_committed_matrices_expand_to_the_planned_runs` makes plan 4's suite need `annotate.arm`, `annotate.pane` and
`mode = "incremental"` (plan 2 Tasks 12, 15, 16), none of which P1 uses: P1 would wait for code it does not run. The
lean harness needs plan 1, plan 2 Tasks 1 to 11 and plan 3.

**S7. Stale interface block for plan 3** (details in §3): `AskResult` has `text`, not `answer`, and already has
`citations`, `model` and `prompt`; `[ask] prompt` exists; `Change.t[0]` is not disputed.
`test_answer_fn_maps_plan_3s_result` fails as written.

**S8. `overlay.scale` is removed by plan 2 Task 4** (`test_overlay_config_is_font_only`), and plan 4 runs after plan 2.
Task 2's fixture, `test_config_for_applies_overrides…`, `test_duplicate_axis_values_rejected` and
`test_two_axes_setting_one_key…` use it. Use `annotate.scale`.

**S9. Summary-level hits make the time test vacuous.** A step, section or video node spans many frames, so "covering
its time" holds for any summary that quotes the command, and *found* then measures the summariser's prose. Since B1
has to write the definition anyway: count hits of level `lifetime`, `frame` or `transition`; show the best level
otherwise. The coordinator's call; one filter, no constant.

**S10. Judge prompt and rubric disagree on when a string must be exact.** The prompt says "a statement about an exact
string holds only if the answer contains that string character for character"; rubric lines say variously "contains
the exact string" (Q2, Q3), "names the command" (Q6 to Q8), "names the file" (Q5), "gives the output" (Q6). Whether
`kubect1 get nodes` "names the command" is left to the judge, and that is judge noise inside the floor. Make the prompt
say: only a line that says "contains the exact string" is exact.

## Nits

- N-a. Task 1's worked example has cache read 0, so the 0.5 $/MTok read price is untested in the accounting task once
  the `[reference]` row goes. Give `annotate` a non-zero `cache_read_input_tokens` in the fixture.
- N-b. `test_repo_question_file_parses` (10 to 25 questions, at least 3 negative) fails if the owner prunes his own
  draft. Assert that it parses, nothing more.
- N-c. `exact.any` can only tie or rise with a second reader. The report should present it as "what the second reading
  adds, at its price", beside `exact.ocr`, not as a contest.
- N-d. Spec §9 says "majority reading contains it"; the coordinator's brief says "some recorded reading contains it".
  Plan 1's `score_exact` reads the majority. If "any recorded reading" is meant, `variant_only` becomes part of *exact*
  instead of a companion. Decide once; I assume the spec.
- N-e. `table(cost=True)` raising on a missing header, `test_vocabulary`, `test_no_video_constants_in_code` (a digit
  regex over source), the hyphen rule (nothing parses run names; `evalrun.json` has the values), the duplicate-axis
  check, the injectable `Adapters`/`REAL` bundle: enforcement machinery for rules a reader of one report can check. Drop.
- N-f. `ledger_row` and `next_ledger_number`: ledger rows are prose the coordinator writes from `report.md`. Drop.
- N-g. `run_matrix` is sequential by rule; `--only` already lets the coordinator start several processes. Say so.
- N-h. Rename one of `run_cost` (here) and `run_costs` (plan 3), as plan 3's review N8 asks.

## 1. The minimum harness for P1

| Task | P1 | Keep | Defer or drop |
|---|---|---|---|
| 1 accounting | yes | rules 1 to 3, 5 to 7 | rule 4, `cache_usage`, `sources` (drop, S4) |
| 2 matrix | lean | `phase`, `source`, `base_config`, `stages`, `repeats`, `[spans.*]` `frames`/`ground_truth`/`questions`, `[axis.*.*]` dotted overrides, product expansion, `config_for` validated at expansion, no `ask` without `questions` | `skip_stages` and `[reference]` (drop); `[[exclude]]`, `floor`, `floor_match`, cross-phase `[[compare]]`, `popup_frames` (P2); `fixed_from` (P5); `[judge]`; rules 2, 7 |
| 3 runner | yes | rules 1, 2, 4, 7; rule 5 as "`done` → skip, else call the stage list again" (each stage skips itself when up to date, the private cache returns paid calls; set `resumed`); commit and dirty paths in `evalrun.json` | refusal and `metric_code_hash` (drop, S5); rule 6 (P5); the per-stage restart bookkeeping (the stage seconds stay) |
| 4 commands | yes | rules 1 to 3, 6 to 8, 12, 13, with the scorers of B1 compared by frame (B2); adapters as plain functions | rules 4, 5, 9 to 11 (drop) |
| 5 guards | no | the scorecard copies the counters plans 2 and 3 already write (`stages.annotate`: `repairs`, `repair_counts`, `errors`, `failed_targets`; `stages.interpret`: `errors`, `invalid_citations`, `submitted`) | whole task → P2; track guards never (deterministic, printed by `scry report`) |
| 6 questions | yes | rules 1 to 10 | rules 11, 12, `Cited`, `read_citations`, `citation_check` (drop) |
| 7 judge | yes | rules 1 to 6 | rule 7, `source "eye"`, `[judge]` table |
| 8 answer sheets | no | none | when the owner wants to audit the judge; never gates |
| 9 label sheets | no | none | P2 at the earliest, as a plain listing |
| 10 scorecard | lean | run block, input hashes, `commands`, `questions` (with answers and judgments), `cost`, `units`, warnings; `METRICS` as name → `better` for the metrics P1 computes | `changed_since_run`, `eye`, `label_tallies`, guard and by-eye rows, per-frame and per-transition cost units (P3), `Adapters` |
| 11 noise | yes | rules 1 to 5: values per repeat, max | `median`, `pairs`, rule 6 (P2) |
| 12 compare | yes | rules 1 to 8 without `floor_extra`; by default every pair of configurations of a span | rule 9 (drop, S2); rule 10's phase selectors, `b = "each"`, `earlier` (P2) |
| 13 report | lean | `report.md` (warnings, runs, cost per configuration and stage at sync and batch price, commands per configuration and per entry with per-repeat `k/n`, questions, noise, comparisons), `scores.json` | `ledger_row`, `[reference]` row, cost-column enforcement, vocabulary test, agreement and by-eye sections |
| 14 CLI, matrices | lean | `scry eval run [--dry-run] [--only]`, `judge`, `report`; `evals/p1.toml` | `status`, `score`, `sheet`, `labelsheet`; `p0*.toml` (drop); `p2` to `p5.toml` (each when its phase is decided) |

Tasks 11 and 12 can be one task, 13 and 14 another: nine tasks, **[estimated]** under half the plan's code and tests.

**Verdicts on the plan's own strike list and on the items asked about.**

| Item | Verdict |
|---|---|
| Companions of *exact* (D3) | Strike. `exact_in_window` repeats what the first-appearance error already shows (the plan's own fixture: 23.84 s, 3 frames) and is broken by B2; `variant_only` and `nearest` are diagnostics the coordinator gets by reading `lifetimes.jsonl`. Add one only when a P1 report shows an entry that needs it. |
| D4 guards | Strike as mechanisms; B1's one rule does their work. |
| Citation reading (D6) | Strike. N1 is stale (plan 3 Task 15 has `citations`); guards only; P5 at the earliest, from `AskResult.citations`. |
| `[reference]` row | Strike. The number is a constant already computed here (4.6465 $, 0.1408 $/frame); it is one sentence in P1's ledger row. |
| `skip_stages` | Drop outright: no committed matrix uses it (`p1.toml` sets `annotate.mode = "off"`). |
| P0 as matrices (D19) | Drop outright. Plan 1 Task 16 runs P0 with three committed configs and `scry report`; P0 is deterministic, so noise and pairing add nothing; it is the main customer of `fixed_from`. |
| Rubric judge (Task 7) | Keep. With nobody to read 135 answers, a committed, blind prompt and code-derived labels are the only way the question set yields a number under the evidence rules. About $2 for P1 **[estimated]**. |
| Answer sheets, agreement (Task 8) | Defer; S1. |
| Label sheets (Task 9) | Defer to P2, where an arm is chosen partly on labels. Then build `sample_frames`, `label_items` and a plain listing to read. Tick parsing, blind codes, `thin`, tallies and `labels.precision.*` units turn an eye judgment into a paired metric with verdicts, which is the label ground truth the owner said does not exist; build them only when a person commits to ticking. |
| Metric registry (Task 10) | Shrink to name → `better`. `role` and `unit` order nothing once `reading` goes. |
| Dirty-tree refusal, metric-code hash (D12) | Drop; record the commit. S5. |
| Matrix format (Task 2) | Keep, lean: a committed file naming what ran is evidence. |
| `scry eval` commands (Task 14) | Three, not eight. |

## 2. Soundness of what remains

**Walks through `span2-commands.md`** (plan 1 Task 14's parser; B1's scorers).
- Entry 2, `az configure --defaults group=RG1-KodeKloud-AKS`: column 3's first pair is (161, 649.17), column 4's last
  pair (164, 653.57); scorable. *Exact* (OCR): true when the earliest lifetime whose majority reading contains the
  string exists; the line sits in scrollback until 187, so the 174 misread of the spec's example is outvoted. First
  appearance error = that lifetime's first frame − 161, likely +1 to +3 frames, because OCR reads a line carrying the
  grey suggestion badly (L43: 3 of 11). *Found*: the lifetime's `frames` intersect [161, 164]. Submission: a claim on
  T(163→164) with equal `entered_text`, error 0 frames.
- Entry 7, `kubectl get nodes`: B2. By frames: lifetime (180, …) intersects [180, 180], found; *exact* true with
  `frame_error 0`, `t_error` round(702.0333 − 702.03, 2) = 0.0; submission: a claim on T(179→180) (plan 3 D2:
  `entered_text` is the whole command "even when typing was never seen"), error 0.
- `Y` and `y`: texts `Y`, `y`; not scorable (one non-space character), so outside *found* and *exact*, as L46 (4)
  rules. The parser's "first" pair is the question's frame (169; 170), which is harmless while they are unrated. They
  count in `submit_marked`: claims on T(169→170) with `"Y"` and T(170→171) with `"y"`, by case-sensitive equality. An
  interpretation that writes `y` for both leaves row 4 unmatched, which is a fair miss.
- Never-run row 4 (`kubectl config current-context`, frame 178): same text as executed row 6. If `interpret` marks the
  true submission late, on T(177→178), row 6 takes that claim (+1 frame) and row 4 is not a false run; a second claim
  with that text is one. Under the frame-only condition N4 describes, that late claim needed the `shared_claim` flag;
  and row 1 (`az login`, frame 155) could never score in a span-2 run, because T(154→155) is outside the span and
  T(155→156) ends on 156. Text equality has neither hole.

**Cold runs.** `make_subset(..., share_cache=False)` (verified in `subset.py`: no symlink, `Run()` makes an empty
`cache/`) plus Task 3 rule 2 is sufficient and simple. `ask` has no cache (plan 3 Task 15 rule 5). The judge's cache is
shared on purpose and lives outside every run. No hole found besides the wording of `cold` (S4).

**Cost arithmetic**, at the branch's list prices for `claude-opus-5` (5 / 25 / 0.5 $/MTok; cache creation 1.25 × input =
6.25; batch × 0.5 on all four kinds), which match the current price list:
- Task 1: annotate 100,000 × 5 + 20,000 × 25 + 8,000 × 6.25 = 0.50 + 0.50 + 0.05 = 1.05; batch 0.525; interpret 0.15 +
  0.10 = 0.25; total 1.30, batch 0.65; ÷ 10 = 0.13; × 200 = 26.0; 200 s ÷ 10 = 20.0. Agrees. (The resumed case, +10,000
  input = +0.05 → 1.35, 0.135, 27.0, also agrees, and is dropped by S4.)
- Task 13 reference row: 272,050 × 5 = 1.36025; 127,046 × 25 = 3.17615; 106,335 × 0.5 = 0.0531675; 9,105 × 6.25 =
  0.05690625; sum 4.64647 → 4.6465; ÷ 33 = 0.1408. Agrees; without the last term 4.5896, the ledger's $4.59.
- Task 7: 2,000 × 5 + 200 × 25 = 0.015. Task 10: 20,000 × 5 = 0.10, ÷ 4 = 0.025. Agree.
- `$ / video` is linear in frames; `summarize` is not. The report says "linear projection"; enough.

**Noise and pairing.** S3. The fixtures recompute: `test_outside_the_noise` (0.888889, 0.333333, −0.555556, floor
0.333333 × 0.57735 = 0.19245, flip "2: A only"), `test_inside_the_noise` (0.25; 1.0 → 0.707107),
`test_floor_from_three_repeats`, `test_paired_difference`, `test_scaled_floor`. Dropping a unit that any card lacks
(Task 12 rule 3) means one failed judgment removes that question from a comparison; `dropped` shows it; acceptable.

## 3. Interfaces

Read from **plan 1**: `Entry`, `parse_commands`, `scorable`, `score_exact` (row keys as pinned), `exact_rate`;
`box_stability`, `touched_share_low_half`, `fragmentation` (deferred with Task 5); `Change.id/from_frame/to_frame/t`,
`Lifetime.id/text/readings/first/last`; `Run.load_frames/boxes/changes/lifetimes`; `make_subset(src_root, out, frames,
share_cache)`; `parse_frames`; `run_read`, `track.stage.run_track`; `track.margin`; manifest `stages.decode.emitted`
and `subset.source`. All match the plan and, where landed, the code.
From **plan 2**: `run_annotate(run, cfg, provider=None)`; `annotate.mode`, `annotate.transcribe` (P1); `scale`, `arm`,
`pane`, `mode = "incremental"` (later phases); `Run.load_labels`, `Labels.lifetime(id).vlm` (P1); `Labels.box`,
`Labels.frame`, `container_ref`, `Run.load_annotations` (deferred Tasks 5, 9); manifest `stages.annotate`. Match.
From **plan 3**: `run_interpret`, `run_summarize`, `build_index` as `(run, cfg)`; `Interpretation` fields;
`load_interpretations`; `scry.costs` (`USAGE_KEYS`, multipliers, `add_usage`, `estimate_cost(…, batch)`, `run_costs`
keys); `open_db`, `search` (hits with `level`, `frames`, `t`); `ask`/`AskResult`; `interpret.images`; `tests/minirun.py`,
`tests/fakes.py`. Match except as below.

| | Status | Simplest fix, side |
|---|---|---|
| N1 | Stale. `AskResult.citations` exists (plan 3 Task 15, read from prose by its own `extract_citations`). | Plan 4: drop `read_citations`. |
| N2 | Stale. `AskConfig.prompt = "ask-v1"` and `PROMPTS` exist (plan 3 Tasks 2, 15). | Plan 4: delete. |
| N3 | Confirmed in `costs.py` (`PRICES.get(model, (5.0, 25.0, 0.5))`); plan 3's fakes rely on it. | Plan 4: keep the one warning. |
| N4 | Moot: the functions do not exist. | B1, plan 4. |
| N5 | Stale. Plan 3's A2 says `Change.t == (a.t_end, b.t_settled)`, as plan 1 Task 10 rule 6 does. | Delete; B2 stops reading seconds anyway. |
| N6 | Fine. | None. |
| N7 | Dissolved by plan 2 D23 and plan 3 D18. | S4, plan 4. |
| N8 | Fine. | None. |
| missed | *Found*, submission, *false run* unowned. | B1, plan 4. |
| missed | `AskResult.text` (not `answer`); `model` and `prompt` are fields. | Plan 4: `AskOutcome` from `text`, `model`; fix the test. |
| missed | `overlay.scale` removed by plan 2. | S8, plan 4. |
| missed | The ground truth's seconds are rounded; records are not. | B2, plan 4. |
| missed | Committed P2 to P5 matrices tie plan 4's suite to plan 2 Tasks 12 to 16. | S6, plan 4. |
| missed | Plan 3's D21 still speaks of "trivial" transitions (dropped in L45). | Plan 3's side; nothing here reads it. |

## 4. The question set

All fifteen are answerable from the command list alone, and every reference answer agrees with it: I recomputed each
mm:ss from the seconds (620.67 → 10:20.7; 668.13 to 669.47 → 11:08.1 to 11:09.5; 698.07 → 11:38.1; the rest likewise)
and checked each frame, suggestion and output string against its row. Phrasing is varied: nine styles; four questions
quote the command and eleven paraphrase it. Corrections:

1. **Scope Q9, Q13 and Q15 in time, like Q10, Q12 and Q14.** "In this part of the video" (Q9) has no referent for the
   agent, and "in this session" (Q13) and the bare Q15 are safe only while the index holds frames 155 to 187. The two
   suggestions come from shell history, so an earlier `az aks scale` or an earlier `kubectl config current-context` in
   the full video is likely, and the reference answers would then be wrong. Add "between 10:20 and 12:01".
2. **Q12 to Q14, M2** ("appeared only as a suggestion, or was never submitted"): a plain, correct "No" scores
   `partial`. The owner's words are that these "must be answered no"; Q15 has no such line. Make the four consistent.
   By the owner's wording, strike M2 from Q12 to Q14: X1 already catches the failure that matters. If it stays (it
   does separate an informed no from an empty index), the header must say a bare "No" is partial by design.
3. **Q5, M2** "names the file `C:\Users\msadmin\.kube\config`": under the judge's exact-string rule this becomes a test
   of reading backslashes, in a question about what the CLI reported. Reword: "says the context was merged into the
   kube config file (`.kube\config`)".
4. **Exactness wording** (S10): only Q2 M1 and Q3 M1 say "contains the exact string"; say in the header that only such
   lines are exact.
5. Q3's X1 is redundant (a lower-case answer already fails the only M line); harmless. Q4's M1 is implied by M2, which
   is how `partial` is meant to work there; fine.
6. Q14's evidence `t 620.67-620.67` beside `frames 155-156`, and Q5's single frame, only fed the citation check that is
   dropped.

The negatives are fair: each names something that was on screen and never run, and each X line is the precise wrong
claim. Status "DRAFT … nothing here is accepted yet" is fine for P1: the file's hash goes into every scorecard and
reworded questions never pair with old answers.

## 5. Smuggled constants, thresholds, persistence, design pressure

- **Per-video constants:** none in code besides `floor_match`'s default (S3). `popup_frames`, the spans and the
  reference usage sit in `evals/`, where the plan says they belong. The four-character `scorable` cut is declared (L46).
- **Pre-committed thresholds:** no pass/fail anywhere. What comes close: `reading` with its metric order (S2); the
  question-count bounds in a test (N-b); P4 and P5 matrices that fix a base before P1 has run (S6). `SCORE`'s 1 / 0.5 /
  0 is a convention, and the counts are always shown.
- **Persistence as evidence:** none. *False run* and submission read only `submitted`. `exact_in_window` and *found*
  use a lifetime's span as coverage, not as evidence of execution.
- **Design pressure:** *found* and `exact.any` reward more indexed text and more readers, never fewer (S2, N-c); *found*
  through summary nodes rewards summaries that recite commands (S9). With cost beside every number and no mechanical
  winner, the owner's metrics stay honest. The first-appearance error rewards reading a line while the grey suggestion
  is on it; that is consistent with the honest text contract and only breaks ties.

## Lean task list for P1

1. Task 1, rules 1 to 3 and 5 to 7.
2. Task 2, lean (spans, one level of axes, overrides validated at expansion).
3. Task 3, rules 1, 2, 4, 7 and the reduced resume; commit recorded, never refused.
4. Task 4, rules 1 to 3, 6 to 8, 12, 13, with B1's three definitions by frame.
5. Task 6, rules 1 to 10.
6. Task 7, rules 1 to 6, with S10's sentence.
7. Task 10, lean, carrying the manifest counters of `annotate` and `interpret`, and answers with judgments.
8. Tasks 11 and 12: values per repeat, max, scaled floor, rows with cost, flips; no `reading`, no floor file.
9. Tasks 13 and 14: `report.md`, `scores.json`; `scry eval run`, `judge`, `report`; `evals/p1.toml`.

Needs plan 1, plan 2 Tasks 1 to 11 and plan 3. Items 1, 2, 3, the parser of 5, and 8 can be built now.

## Deferred, with the phase that needs each

| Item | Needed at |
|---|---|
| `[[exclude]]`; `floor`, `floor_match`, `floor_lookup`, `noise.json`; cross-phase comparisons (`phase` selector, `b = "each"`, `earlier`) | P2 |
| Task 5 label guards, `popup_frames`, `popups_found`, `one_container_share` | P2 |
| Task 9 as a plain listing over shared sample frames | P2, P3; tick parsing and tallies only when a person will tick |
| Per-frame `cost.annotate` and per-transition `cost.interpret` units; no batch price for incremental runs (plan 2's review) | P3 |
| `fixed_from` | P5 |
| Citation guards, from `AskResult.citations` | P5, if prompt wordings are compared |
| Task 8 | when the owner asks to audit the judge; never a gate |
| Companions of *exact* | only if a P1 report shows an entry that needs one |
| P2 to P5 matrices | each when its phase is decided; P6 is a copy of `p1.toml` with another `source` |

Dropped outright: `skip_stages`; P0 as matrices; `[reference]`; the dirty-tree refusal and the metric-code hash; the
manifest-against-cache maximum and `cache_usage`; the D4 guards as separate mechanisms; `read_citations` and
`citation_check`; `reading`; the ledger-row generator; the cost-column and vocabulary enforcement; the `Adapters`
bundle; the hyphen and duplicate-axis rules; `status` and `score`.
