import itertools
import json
from pathlib import Path
from types import SimpleNamespace

from eval_fixtures import QUESTIONS, source_run
from typer.testing import CliRunner

from scry.cli import app
from scry.evaluation.judge import ItemVerdict, JudgeOutput
from scry.evaluation.matrix import config_for, expand, load_matrix
from scry.providers import VlmResult

REPO = Path(__file__).parents[1]
HEADINGS = ["# p9 evaluation report", "## Warnings", "## Runs", "## Cost", "## Commands", "## Questions", "## Noise", "## Comparisons"]


def test_p1_matrix_expands_to_the_planned_runs(monkeypatch):
    """Reads the committed matrix on purpose, to catch a silent edit."""
    monkeypatch.chdir(REPO)  # the matrix's paths are relative to the working directory
    m = load_matrix(Path("evals/p1.toml"))
    specs = expand(m)
    cfgs = {s.name: config_for(m, s) for s in specs}  # every run's config validates
    assert len(specs) == 18 and m.source.parts[0] == "runs"
    assert all(s.stages[-1] == ("ask" if s.span.name == "span2" else "index") for s in specs)
    assert {s.span.name: s.span.frames for s in specs} == {"smoke": (145, 155), "span2": (155, 187)}
    a = cfgs["span2-transcribing-r1"].annotate
    assert (a.mode, a.transcribe, a.scale) == ("every_frame", True, 1.0)
    assert cfgs["smoke-grouponly-r3"].annotate.transcribe is False
    assert all(cfg.annotate.mode == "off" for name, cfg in cfgs.items() if "-none-" in name)


def _stage(name: str, fail_first: bool = False):
    """A fake stage: it only adds a manifest entry with usage."""
    calls = itertools.count(1)

    def stage(run, cfg):
        if fail_first and next(calls) == 1:
            raise ValueError("boom")
        stages = run.manifest_read().get("stages", {})
        run.manifest_update(stages=stages | {name: {"usage": {"input_tokens": 10_000, "output_tokens": 1_000}, "model": "claude-opus-5",
                                                    "cache": {"hits": 0, "misses": 2}}})
    return stage


class _Judge:
    model = "claude-opus-5"

    async def complete(self, **kw) -> VlmResult:
        items = [ItemVerdict(id=i, holds=i.startswith("M"), quote="") for i in ("M1", "M2", "X1")]
        return VlmResult(JudgeOutput(items=items), None, {"input_tokens": 2_000, "output_tokens": 200})


def _matrix(tmp_path: Path, src, phase: str = "p9", extra: str = "") -> Path:
    (tmp_path / "base.toml").write_text("")
    (tmp_path / "q.md").write_text(QUESTIONS)
    path = tmp_path / f"{phase}.toml"
    path.write_text(f'phase = "{phase}"\nsource = "{src.root}"\nbase_config = "{tmp_path / "base.toml"}"\n'
                    f'stages = ["read", "annotate", "ask"]\nrepeats = 2\n[spans.smoke]\nframes = "1-2"\nquestions = "{tmp_path / "q.md"}"\n{extra}')
    return path


def test_run_and_report_end_to_end_with_fake_stages(tmp_path: Path, monkeypatch):
    src = source_run(tmp_path)
    matrix, root, results = _matrix(tmp_path, src), tmp_path / "eval", tmp_path / "results"
    stages = {"read": _stage("read"), "annotate": _stage("annotate")}
    monkeypatch.setattr("scry.evaluation.runner.resolve", lambda stage: stages[stage])
    monkeypatch.setattr("scry.ask.ask", lambda run, cfg, question, client=None: SimpleNamespace(
        text="It ran at frame 2.", turns=2, tool_calls=["search"], tool_log=[], usage={"input_tokens": 1_000}, cost_usd=0.05, stop="end_turn"))
    monkeypatch.setattr("scry.evaluation.judge.judge_provider", lambda cfg, cache_dir: _Judge())
    cli = CliRunner()

    dry = cli.invoke(app, ["eval", "run", str(matrix), "--dry-run", "--root", str(root)])
    assert dry.exit_code == 0 and "smoke-r1" in dry.output and "smoke-r2" in dry.output and "ask" in dry.output
    assert not root.exists()  # a dry run creates nothing and spends nothing
    typo = cli.invoke(app, ["eval", "run", str(_matrix(tmp_path, src, "p8", '[axis.base.x]\n"track.margn" = 1\n')), "--dry-run", "--root", str(root)])
    assert typo.exit_code == 1 and "margn" in typo.output and not root.exists()

    done = cli.invoke(app, ["eval", "run", str(matrix), "--root", str(root)])
    assert done.exit_code == 0, done.output
    states = [json.loads((root / "p9" / name / "evalrun.json").read_text()) for name in ("smoke-r1", "smoke-r2")]
    assert [s["status"] for s in states] == ["done", "done"] and all(s["cold"] for s in states)

    stages["read"] = _stage("read", fail_first=True)  # another phase: its first run stops, the second still runs
    broken = cli.invoke(app, ["eval", "run", str(_matrix(tmp_path, src, "p7")), "--root", str(root)])
    assert broken.exit_code == 1 and "ValueError: boom" in broken.output
    assert [json.loads((root / "p7" / name / "evalrun.json").read_text())["status"] for name in ("smoke-r1", "smoke-r2")] == ["failed", "done"]

    judged = cli.invoke(app, ["eval", "judge", str(matrix), "--root", str(root)])
    assert judged.exit_code == 0, judged.output
    assert len((root / "p9" / "smoke-r1" / "judgments.jsonl").read_text().splitlines()) == 2

    reported = cli.invoke(app, ["eval", "report", str(matrix), "--root", str(root), "--results", str(results)])
    assert reported.exit_code == 0, reported.output
    cards = [json.loads((root / "p9" / name / "scorecard.json").read_text()) for name in ("smoke-r1", "smoke-r2")]
    assert json.loads((results / "p9" / "scores.json").read_text())["scorecards"] == cards
    assert cards[0]["questions"]["positive"]["correct"] == 1 and cards[0]["cost"]["dollars"] == 0.15  # two stages at $0.075
    report = (results / "p9" / "report.md").read_text()
    at = [report.index("\n" + h + "\n") if i else report.index(h + "\n") for i, h in enumerate(HEADINGS)]
    assert at == sorted(at)  # the sections, in order
    assert "One `outside` row is weak evidence" in report and "linear projection" in report
    runs_table = report[report.index("## Runs"):report.index("## Cost")]
    assert "$ / frame" in runs_table and "$ / video" in runs_table
    assert "| configuration | $ / question | s / question | question set $ | judge $ |" in report
