# Re-base step 3: implementation notes

One entry per place where the implementation of `2026-09-21-rebase-boxes-3-interpret-summarize-index-ask.md` had to
choose, because a rule was ambiguous, an interface was incomplete, an expected value did not follow from the rules, or
the plan differed from the code committed on the branch. Each entry: the task, what the plan said, what was done, why.
The reading that needs the least machinery was taken every time.

| # | Task | The plan said | What was done | Why |
|---|---|---|---|---|
| N1 | 1 | `tests/minirun.py` has `mini_run`, `mini_interpretations` and `call_text`. Task 4's `test_labels_flag_and_rerun` "writes Fixture M's annotations into the same directory" of a run made without labels. | `minirun.py` also exposes `write_annotations(run)`, the function `mini_run(labels=True)` itself calls. The annotation lines are written as JSON objects by hand (not through the `Annotation` model), as the plan asks. | The test needs the same four lines a second time; one function instead of a copy. |
