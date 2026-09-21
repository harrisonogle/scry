"""Fixtures shared by the evaluation harness tests (plan 4)."""
from pathlib import Path

from PIL import Image

from scry.jsonl import write_jsonl
from scry.run import Run
from scry.schemas import Frame


def source_run(tmp_path: Path) -> Run:
    """A source run as tests/test_subset.py builds it: frames 0-3, a finished decode, one paid call in its cache."""
    src = Run(tmp_path / "src")
    recs = []
    for n in range(4):
        Image.new("L", (8, 8), 40 * n).save(src.frames_dir / f"{n:05d}.png")
        recs.append(Frame(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=n != 2,
                          width=8, height=8, sha256=f"{n:064x}", png=f"frames/{n:05d}.png"))
    write_jsonl(src.frames, recs)
    src.manifest_update(video="v.mp4", video_sha256="abc", video_id="v", fps=30.0, duration=4.0, width=8, height=8)
    src.stage_done("decode", [tmp_path / "v.mp4"], "cfg", emitted=4, settled=3)
    (src.cache_dir / "k.json").write_text("{}")
    return src


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
