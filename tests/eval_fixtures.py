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
