# Re-base step 3: implementation notes

One entry per place where the implementation of `2026-09-21-rebase-boxes-3-interpret-summarize-index-ask.md` had to
choose, because a rule was ambiguous, an interface was incomplete, an expected value did not follow from the rules, or
the plan differed from the code committed on the branch. Each entry: the task, what the plan said, what was done, why.
The reading that needs the least machinery was taken every time.

| # | Task | The plan said | What was done | Why |
|---|---|---|---|---|
| N1 | 1 | `tests/minirun.py` has `mini_run`, `mini_interpretations` and `call_text`. Task 4's `test_labels_flag_and_rerun` "writes Fixture M's annotations into the same directory" of a run made without labels. | `minirun.py` also exposes `write_annotations(run)`, the function `mini_run(labels=True)` itself calls. The annotation lines are written as JSON objects by hand (not through the `Annotation` model), as the plan asks. | The test needs the same four lines a second time; one function instead of a copy. |
| N2 | 4 | Rule 4: `cost_usd` is `estimate_cost(usage, model)`; D18: "this plan never passes a batch flag to `estimate_cost`". Ledger L52 (1), later: "one cost figure per stage, at the price actually paid"; the committed `annotate` stage passes `batch=cfg.model.mode == "batch"` (plan 2's note N1). | `interpret`, the one stage of this plan that can run in batch mode, does as `annotate` does: `cost_usd = estimate_cost(usage, provider.model, batch=cfg.model.mode == "batch")`. `summarize` never uses the batch path and `ask` is synchronous, so both pass no flag. `run_costs` (Task 10) follows the plan and recomputes every stage from `usage` at the synchronous price. | The committed code and L52 win over the plan. In synchronous mode every figure agrees; for a batch-mode run the stage's `cost_usd` is half of what `run_costs` and plan 4's cost summary show for it, which is the limit plan 2's N1 already records. |
| N3 | 4 | The stat `labels` is a bool; the rule does not say of what. | `labels = bool(run.load_annotations())`: true exactly when `Run.load_labels()` is not `None`. Records of a missing PNG carry no `model` and no `prompt_version` (no call was made), as rule 2a writes them. | It is the condition `load_labels` itself applies, without building the view a second time. |
