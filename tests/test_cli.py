from pathlib import Path

from typer.testing import CliRunner

from scry.cli import STAGES, app
from scry.run import Run

TARGETS = {"decode": "scry.decode.run_decode", "outline": "scry.outline.run_outline", "read": "scry.read.run_read",
           "track": "scry.track.stage.run_track", "annotate": "scry.annotate.run_annotate", "interpret": "scry.interpret.run_interpret",
           "summarize": "scry.summarize.run_summarize", "index": "scry.index.build_index"}


def test_run_executes_stages_in_pipeline_order(tmp_path: Path, monkeypatch):
    ran: list[str] = []
    for name, target in TARGETS.items():
        monkeypatch.setattr(target, lambda *args, _name=name, **kw: ran.append(_name))
    runner, out = CliRunner(), tmp_path / "run"
    assert runner.invoke(app, ["run", "v.mp4", "--out", str(out)]).exit_code == 0
    assert ran == ["decode", "outline", "read", "track", "annotate", "interpret", "summarize", "index"] == STAGES
    assert Run(out).manifest_read()["costs"]["total_usd"] == 0.0
    ran.clear()
    assert runner.invoke(app, ["run", "v.mp4", "--out", str(out), "--stages", "index,read"]).exit_code == 0
    assert ran == ["read", "index"]
    assert runner.invoke(app, ["run", "v.mp4", "--out", str(out), "--stages", "perceive"]).exit_code == 2
