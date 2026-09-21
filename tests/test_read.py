from pathlib import Path

from PIL import Image

from scry.config import Config
from scry.jsonl import write_jsonl
from scry.ocr.base import RawLine
from scry.read import assign_ids, run_read
from scry.run import Run
from scry.schemas import Frame


class FakeEngine:
    name = "fake"

    def __init__(self, lines: list[RawLine]):
        self.lines = lines
        self.calls = 0

    def settings(self) -> dict:
        return {"engine": "fake"}

    def recognize(self, png: Path) -> list[RawLine]:
        self.calls += 1
        return list(self.lines)


def test_assign_ids_reading_order_and_churn():
    raw = [RawLine("second", 0.9, (10, 40, 90, 58), None), RawLine("first", 0.95, (10, 10, 90, 28), None),
           RawLine("right", 0.8, (200, 10, 260, 28), None)]
    boxes, dropped = assign_ids(raw, [(0, 35, 100, 60)])
    assert [(b.id, b.text) for b in boxes] == [("b1", "first"), ("b2", "right"), ("b3", "second")]
    assert [b.in_churn for b in boxes] == [False, False, True]
    assert dropped == 0


def test_read_drops_empty_text():
    boxes, dropped = assign_ids([RawLine("  ", 0.5, (200, 10, 210, 28), None), RawLine("x", 0.9, (10, 10, 20, 28), None)], [])
    assert [(b.id, b.text) for b in boxes] == [("b1", "x")]
    assert dropped == 1


def _frames(run: Run, shas: list[str]) -> None:
    recs = []
    for n, sha in enumerate(shas):
        Image.new("L", (8, 8), 0).save(run.frames_dir / f"{n:05d}.png")
        recs.append(Frame(video_id="v", frame=n, t_change=n, t_settled=n + 0.1, t_end=n + 1, settled=True, width=8, height=8,
                          sha256=sha, png=f"frames/{n:05d}.png"))
    write_jsonl(run.frames, recs)


def test_run_read_writes_boxes_and_skips_when_up_to_date(tmp_path: Path):
    run = Run(tmp_path / "r")
    _frames(run, ["a", "b"])
    engine = FakeEngine([RawLine("x", 0.9, (1, 1, 5, 5), None)])
    run_read(run, Config(), engine)
    recs = run.load_boxes()
    assert [r.frame for r in recs] == [0, 1] and all(r.engine == {"engine": "fake"} for r in recs)
    assert recs[0].png == "frames/00000.png" and [b.id for b in recs[0].boxes] == ["b1"]
    assert run.manifest_read()["stages"]["read"]["frames"] == 2
    assert engine.calls == 2
    run_read(run, Config(), engine)
    assert engine.calls == 2  # up to date: no further engine calls
    _frames(run, ["a", "c"])
    run_read(run, Config(), engine)
    assert engine.calls == 4
