from pathlib import Path

from PIL import Image
from track_fixtures import make_run, typing_run

from scry.config import Config
from scry.report import build_report, write_sheets
from scry.run import Run
from scry.track.stage import run_track

HEADINGS = ["# track report", "## Run", "## Transitions", "## Totals", "## Guards", "## Lifetimes", "## Incremental annotation projection",
            "## Text changes", "## Moves", "## Unstable lifetimes", "## Reverts"]


def tracked(tmp_path: Path) -> Run:
    run = typing_run(tmp_path / "r")
    run_track(run, Config())
    return run


def rows(text: str, start: str) -> list[str]:
    return [ln for ln in text.split("\n") if ln.startswith(start)]


def test_report_has_sections_and_numbers(tmp_path):
    text = build_report(tracked(tmp_path), Config())
    positions = [text.index("\n" + h + "\n") if i else text.index(h + "\n") for i, h in enumerate(HEADINGS)]
    assert positions == sorted(positions)
    assert rows(text, "| T1 |") and rows(text, "| T2 |")
    assert "appended" in text
    assert "`PS> git` → `PS> git status`" in text
    assert "model calls: none, $0.00" in text.split("\n")


def test_report_frames_filter(tmp_path):
    text = build_report(tracked(tmp_path), Config(), frames=(1, 2))
    assert rows(text, "| T2 |") and not rows(text, "| T1 |")
    assert "T1/0" in text  # T2's continues


def test_report_with_ground_truth(tmp_path):
    gt = tmp_path / "gt.md"
    gt.write_text("## Executed\n\n| # | Text as displayed | First fully visible (frame, t) | Submitted (frame, t) | Note |\n|---|---|---|---|---|\n"
                  "| 1 | `git status` | 2, 2.00 | 2, 2.00 | High |\n")
    text = build_report(tracked(tmp_path), Config(), ground_truth=gt)
    commands = text[text.index("## Commands"):]
    assert "| 1 | `git status` | yes | yes | 1 | L3 | 2 | 0 | 0.0 |" in commands  # scorable, exact, matches, lifetime, first frame, frame error, t error
    assert "exact: 1 / 1" in commands


def test_report_renders_on_empty_run(tmp_path):
    run = make_run(tmp_path / "zero", [], [])
    run_track(run, Config())
    text = build_report(run, Config())
    for h in HEADINGS:
        assert h in text
    assert not rows(text, "| T")


def test_sheets_written(tmp_path):
    run = tracked(tmp_path)
    paths = write_sheets(run, Config(), run.root / "report-sheets", None, per_kind=5, seed=0)
    assert paths and all(p.exists() for p in paths)
    for p in paths:
        Image.open(p).load()
    assert {"T1-r0-appended.png", "T2-r0-appended.png"} <= {p.name for p in paths}
