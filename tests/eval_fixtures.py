"""Fixtures shared by the evaluation harness tests (plan 4)."""

# Task 5's question file: one positive question with a continued reference answer and an Evidence bullet, one negative
QUESTIONS = """Intro that is ignored.
## Positive questions
### Q1 (positive, exact-string lookup)
- **Question:** Where does `git status` get run?
- **Reference answer:** At frame 2 (0:02.5),
  submitted by frame 3.
- **Rubric:**
  - M1: says `git status` was executed.
  - M2: gives frame 2 or 3.
  - X1: says it was not run.
- **Evidence:** executed row 1; frames 2-3
## Negative questions (secondary)
### Q2 (negative, did they)
- **Question:** Did they push?
- **Reference answer:** No.
- **Rubric:**
  - M1: says nothing was pushed.
  - X1: says `git push` was executed.
"""

# Task 4's command list over plan 3's Fixture M, in the format of docs/ground-truth/span2-commands.md
GROUND_TRUTH = """## Executed, in order

| # | Text as displayed | First fully visible (frame, t) | Submitted (frame, t) | Confidence note |
|---|---|---|---|---|
| 1 | `git status` | 11, 24.40 | 12, 26.40 | High |

## Appeared on screen but was never run

| Text as displayed | Frames (t) | What the presenter had actually entered | What happened next |
|---|---|---|---|
| `git stash` | 11 (24.40) | `git st` | replaced |
"""
