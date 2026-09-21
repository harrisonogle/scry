# Re-base step 4: implementation notes

One entry per place where the implementation of `2026-09-21-rebase-boxes-4-evaluation.md` had to choose, because a
rule was ambiguous, an interface was incomplete, or an expected value did not follow from the rules. Each entry: the
task, what the plan said, what was done, why. The reading that needs the least machinery was taken every time.

Tasks 1, 2, 3 and 8 were built first, on the branch `rebase-boxes-eval`, while plans 2 and 3 were being built on
`rebase-boxes`; Tasks 4 to 7 and 9 wait for their stages.

| # | Task | The plan said | What was done | Why |
|---|---|---|---|---|
| N1 | 1 | `estimate_cost` prices cache-creation tokens at 1.25 × input "after plan 2's provider task"; the test expects `annotate` at $1.07, of which $0.05 is cache creation. That task had not landed when Task 1 was built, and "this plan adds no second price list". | One term was added to the return line of `scry.costs.estimate_cost` (`cache_creation_input_tokens × input price × 1.25`), nothing else of plan 2's provider task (no `batch` argument, no `add_usage`, no new test in `tests/test_costs.py`). | Without it the expected value cannot be met except by pricing in `accounting.py`, which the plan forbids. Plan 2's task rewrites the same line with the same arithmetic: when the branches merge, take `rebase-boxes`' `costs.py`; Task 1's tests pass on either. |
| N2 | 1 | `per_video = per_frame × projection`; dollars round to 4 places and dollars per video to 2. | `per_frame = round(dollars / frames, 4)`; `per_video = round(dollars / frames × projection, 2)`, from the unrounded quotient. | Multiplying a rate already rounded to 4 places by 221 frames can move the cent. |
| N3 | 1 | Every stage in the manifest or in `stage_seconds` has a `by_stage` row; the fields of a row without usage are given only for `dollars`. | Such a row has `dollars 0.0`, `dollars_batch 0.0`, `usage None`, `model` as the manifest has it (usually `None`), and `seconds 0.0` when the runner did not time the stage (`decode`, which every derived manifest carries). Rows follow the manifest's order, then the timed stages the manifest lacks. | Nothing to choose between; written down so Task 7 and Task 9 know the shape. |
| N4 | 2 | Rule 3 puts "a key set by two axes raises" under expansion; the test that pins it is `test_bad_keys_are_refused_at_load`. | `load_matrix` makes the check, over every pair of axes; `expand` only unions. `Matrix.stages` is likewise put into `STAGE_ORDER` at load. | The product combines every value of one axis with every value of each other axis, so the same files fail either way; at load both readings of the test hold, and `--dry-run` loads before it expands. |
| N5 | 2 | `config_for` "loads `base_config` with `tomllib`"; `base_config` is optional and defaults to `scry.toml`. | A base config file that does not exist raises `FileNotFoundError`; it is not read as "all defaults", unlike `scry.config.load_config`. | A mistyped `base_config` would otherwise run a whole phase on defaults; review focus 5 wants a typo to fail before a cent is spent. |
