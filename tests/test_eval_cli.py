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


def test_p6_matrix_asks_again_over_the_five_p4_pipelines(monkeypatch):
    """Reads the committed matrix on purpose: P6 builds nothing, and each run's config is the one its P4 pipeline had."""
    monkeypatch.chdir(REPO)
    m = load_matrix(Path("evals/p6.toml"))
    specs = expand(m)
    assert {s.name: str(s.copy_from) for s in specs} == {
        "full-inc-transcribing-indexonly-r1": "runs/eval/p4/full-inc-transcribing-r1",
        "full-inc-transcribing-indexonly-r2": "runs/eval/p4/full-inc-transcribing-r2",
        "full-none-indexonly-r1": "runs/eval/p4/full-none-r1", "full-none-indexonly-r2": "runs/eval/p4/full-none-r2",
        "full-inc-transcribing-batch-indexonly-r1": "runs/eval/p4b/full-inc-transcribing-batch-r1"}
    assert all(s.stages == ("ask",) and s.span.frames == (0, 220) for s in specs)
    by_origin = {(p4.phase, p4.name): config_for(p4m, p4) for p4m in (load_matrix(Path("evals/p4.toml")), load_matrix(Path("evals/p4b.toml")))
                 for p4 in expand(p4m)}
    for s in specs:
        cfg, origin = config_for(m, s), by_origin[s.copy_from.parts[-2], s.copy_from.parts[-1]]
        assert cfg.ask.frames is False and origin.ask.frames is True
        assert cfg.model_dump(exclude={"ask"}) == origin.model_dump(exclude={"ask"})  # the pipeline's config, to the key


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


def test_asking_again_over_copied_pipelines_end_to_end(tmp_path: Path, monkeypatch):
    """The shape of P6: the pipelines of a finished phase are copied, the questions are asked again without frames, and
    judge and report work on the result. The copied manifest carries the pipeline's dollars; the questions' are new."""
    src = source_run(tmp_path)
    built, root, results = _matrix(tmp_path, src), tmp_path / "eval", tmp_path / "results"
    stages = {"read": _stage("read"), "annotate": _stage("annotate")}
    asked: list[bool] = []

    def fake_ask(run, cfg, question, client=None):
        asked.append(cfg.ask.frames)
        return SimpleNamespace(text="It ran at frame 2.", turns=2, tool_calls=["search"], tool_log=[], usage={"input_tokens": 1_000},
                               cost_usd=0.05 if cfg.ask.frames else 0.02, stop="end_turn", prompt="ask-v1" if cfg.ask.frames else "ask-v1+noframes")

    monkeypatch.setattr("scry.evaluation.runner.resolve", lambda stage: stages[stage])
    monkeypatch.setattr("scry.ask.ask", fake_ask)
    monkeypatch.setattr("scry.evaluation.judge.judge_provider", lambda cfg, cache_dir: _Judge())
    cli = CliRunner()
    assert cli.invoke(app, ["eval", "run", str(built), "--root", str(root)]).exit_code == 0
    manifests = {name: (root / "p9" / name / "manifest.json").read_bytes() for name in ("smoke-r1", "smoke-r2")}

    again = tmp_path / "p10.toml"
    again.write_text(f'phase = "p10"\nsource = "{src.root}"\nbase_config = "{tmp_path / "base.toml"}"\nstages = ["ask"]\nrepeats = 2\n'
                     f'[spans.smoke]\nframes = "1-2"\nquestions = "{tmp_path / "q.md"}"\n[axis.ask.indexonly]\n"ask.frames" = false\n'
                     f'[copy]\nsmoke-indexonly-r1 = "{root / "p9" / "smoke-r1"}"\nsmoke-indexonly-r2 = "{root / "p9" / "smoke-r2"}"\n')
    dry = cli.invoke(app, ["eval", "run", str(again), "--dry-run", "--root", str(root)])
    assert dry.exit_code == 0 and f"smoke-indexonly-r1: ask (pipeline copied from {root / 'p9' / 'smoke-r1'})" in dry.output
    assert "2 runs" in dry.output and not (root / "p10").exists()
    (tmp_path / "p11.toml").write_text(again.read_text().replace('phase = "p10"', 'phase = "p11"').replace("smoke-r2", "smoke-r3"))
    missing = cli.invoke(app, ["eval", "run", str(tmp_path / "p11.toml"), "--dry-run", "--root", str(root)])  # refused before a cent is spent
    assert missing.exit_code == 1 and "smoke-r3 is not a run of the harness" in missing.output

    asked.clear()
    done = cli.invoke(app, ["eval", "run", str(again), "--root", str(root)])
    assert done.exit_code == 0, done.output
    assert asked == [False] * 4  # two questions a run, every one without frames
    for name, origin in (("smoke-indexonly-r1", "smoke-r1"), ("smoke-indexonly-r2", "smoke-r2")):
        assert (root / "p10" / name / "manifest.json").read_bytes() == manifests[origin] == (root / "p9" / origin / "manifest.json").read_bytes()
    assert cli.invoke(app, ["eval", "judge", str(again), "--root", str(root)]).exit_code == 0
    reported = cli.invoke(app, ["eval", "report", str(again), "--root", str(root), "--results", str(results)])
    assert reported.exit_code == 0, reported.output
    card = json.loads((root / "p10" / "smoke-indexonly-r1" / "scorecard.json").read_text())
    assert card["run"]["cold"] is False and "run is not cold" in card["warnings"]  # how the report shows that nothing was built here
    assert card["cost"]["dollars"] == 0.15 and card["cost"]["seconds"] == 0  # the pipeline's dollars are the copied manifest's
    assert card["questions"]["ask_dollars"] == 0.04 and card["questions"]["positive"]["correct"] == 1  # the questions' are this phase's
    report = (results / "p10" / "report.md").read_text()
    assert "# p10 evaluation report" in report and "smoke-indexonly" in report and "run is not cold" in report
    copied = f"pipeline copied from {root / 'p9' / 'smoke-r1'}, not built by this run"  # said outright, in the card and in the report
    assert copied in card["notes"] and f"- smoke-indexonly-r1: {copied}" in report


def test_run_and_report_end_to_end_with_fake_stages(tmp_path: Path, monkeypatch):
    src = source_run(tmp_path)
    matrix, root, results = _matrix(tmp_path, src), tmp_path / "eval", tmp_path / "results"
    stages = {"read": _stage("read"), "annotate": _stage("annotate")}
    monkeypatch.setattr("scry.evaluation.runner.resolve", lambda stage: stages[stage])
    monkeypatch.setattr("scry.ask.ask", lambda run, cfg, question, client=None: SimpleNamespace(
        text="It ran at frame 2.", turns=2, tool_calls=["search"], tool_log=[], usage={"input_tokens": 1_000}, cost_usd=0.05, stop="end_turn",
        prompt="ask-v1"))
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
