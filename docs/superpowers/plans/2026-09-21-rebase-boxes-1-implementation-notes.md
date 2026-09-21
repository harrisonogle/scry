# Re-base step 1: implementation notes

One entry per place where the implementation of `2026-09-21-rebase-boxes-1-read-track.md` had to choose, because a
rule was ambiguous, an interface was incomplete, or a file was needed that the plan does not list. Each entry: the
task, what the plan said, what was done, why. The reading that needs the least machinery was taken every time.

| # | Task | The plan said | What was done | Why |
|---|---|---|---|---|
| N1 | 5 | The CLI's closing message differs for a legacy source; no interface for telling one. | `subset.is_legacy(src_root)` (one line: `stage1.jsonl` exists), used by `make_subset` and by the CLI message. | The same test was needed in two places. |
| N2 | 7 | `components` "is left exactly as it is"; "the two may share a private helper". | `components` and `label_components` both call a private `_kept_components`; the body of the old `components` moved into it unchanged. | One copy of decode's rule; `test_label_components_agrees_with_components` and the existing detect and settle tests pin that nothing changed. |
| N3 | 8–10, 12 | "Shared fixtures for Tasks 8–10" (`mk`, `block`, fixture K), no file named. | `tests/track_fixtures.py`, a helper module (not a test file), imported by the track tests and by the stage and report tests. | The fixtures are shared by five test files. |
| N4 | 12 | `find_reverts(prev: Change, …)`: "with any of the three `None`, return `[]`". | The parameter is `prev: Change \| None`. `run_track` does not compute the direct z→b difference when the previous transition had no components (there is nothing to undo); the output is the same. | The signature and the sentence disagree; the skip saves one full-frame difference on still transitions. |
| N5 | 14 | The row of `score_exact` has a key `first_frame` that no rule defines. | It is the matching lifetime's `first.frame` (the frame where the OCR reader first has the text), `None` when nothing matches. `frame_error` and `t_error` are `None` when nothing matches or the entry has no first frame. | The entry's own first frame is already in the ground truth; the lifetime's is what a never-run row needs too (rule 7). |
| N6 | 14 | Never-run entries are reported with "matching lifetime ids, first and last frame, sightings"; `score_exact` returns one lifetime per entry. | `groundtruth.matching_lifetimes(entry, lifetimes)` is public; `score_exact` uses it and the report calls it for the never-run table. | The report needs every matching lifetime, not only the first. |
