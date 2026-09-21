import json
from pathlib import Path

from eval_fixtures import GROUND_TRUTH
from minirun import mini_interpretations, mini_run

from scry.config import Config
from scry.evaluation.judge import Judgment, write_judgments
from scry.evaluation.questions import Answer
from scry.evaluation.scorecard import METRICS, build_scorecard, score_phase
from scry.index import build_index
from scry.jsonl import sha256_file, write_jsonl
from scry.run import Run

INTERPRET = {"usage": {"input_tokens": 20_000}, "model": "claude-opus-5", "cache": {"hits": 0, "misses": 3}, "errors": 0,
             "invalid_citations": 2}


def _evalrun(run: Run, gt: Path | None, interpret: dict = INTERPRET, **state) -> None:
    """What the runner leaves in a run directory, written by hand: evalrun.json, config.json and the manifest's usage."""
    span = {"name": "s", "frames": [10, 13], "ground_truth": str(gt) if gt else None, "questions": None}
    (run.root / "evalrun.json").write_text(json.dumps(
        {"phase": "p9", "name": "s-r1", "config_id": "s", "span": span, "values": {}, "repeat": 1, "overrides": {}, "stages": ["interpret"],
         "matrix": "p9.toml", "spec_hash": "h", "code": {"git_commit": "abc", "git_dirty": False}, "cold": True, "started": "t0",
         "finished": "t1", "status": "done", "resumed": False, "seconds": {"interpret": 4.0}, "error": None} | state))
    (run.root / "config.json").write_text(json.dumps({"model": {"model": "claude-opus-5"}}))
    stages = run.manifest_read().get("stages", {})
    run.manifest_update(stages=stages | {"decode": {"emitted": 4}, "interpret": interpret})


def test_scorecard_full_and_with_pieces_missing(tmp_path: Path):
    gt = tmp_path / "gt.md"
    gt.write_text(GROUND_TRUTH)
    run = mini_run(tmp_path / "eval" / "p9" / "s-r1", labels=True)
    mini_interpretations(run)
    build_index(run, Config())
    _evalrun(run, gt)
    card = build_scorecard(run.root)
    assert card["run"] == {"phase": "p9", "name": "s-r1", "config_id": "s", "span": "s", "frames": [10, 13], "values": {}, "repeat": 1,
                           "status": "done", "resumed": False, "cold": True, "git_commit": "abc", "git_dirty": False}
    assert card["counts"] == {"frames": 4, "transitions": 3, "lifetimes": 7}
    rates = card["commands"]["rates"]
    assert (rates["found"], rates["exact"]["ocr"], rates["exact"]["vlm"], rates["submitted"], rates["false_run"]) == ([1, 1], [1, 1], [1, 1], [1, 1], [0, 1])
    assert card["units"]["found"] == {"1": 1.0} and card["units"]["false_run"] == {"N1": 0.0}
    assert card["counters"] == {"annotate": {}, "interpret": {"errors": 0, "invalid_citations": 2}}
    cost = card["cost"]
    assert (cost["dollars"], cost["per_frame"], cost["per_video"]) == (0.1, 0.025, 0.1)  # 20,000 × 5 millionths; projection 4
    assert card["units"]["cost.per_frame"] == {"run": 0.025} and card["units"]["seconds.per_frame"] == {"run": 1.0}
    assert card["questions"] is None and card["warnings"] == [] and card["notes"] == []
    assert set(card["units"]) <= set(METRICS)
    assert card["inputs"] == {"ground_truth_sha256": sha256_file(gt), "questions_sha256": None}
    assert score_phase(tmp_path / "eval", "p9") == [card]  # every directory with an evalrun.json, scored and written
    assert json.loads((run.root / "scorecard.json").read_text()) == card

    bare = mini_run(tmp_path / "bare")  # no labels, no interpretations, no index
    _evalrun(bare, gt)
    card = build_scorecard(bare.root)
    rates = card["commands"]["rates"]
    assert rates["found"] is None and rates["false_run"] is None and rates["exact"]["ocr"] == [1, 1]
    assert not {"found", "false_run", "exact.vlm"} & card["units"].keys()
    for word in ("index", "interpretations", "annotations", "second reader"):
        assert any(word in note for note in card["notes"]), word
    assert card["warnings"] == []

    _evalrun(bare, gt, interpret=INTERPRET | {"cache": {"hits": 2, "misses": 1}}, status="failed", error="ValueError: boom")
    warnings = build_scorecard(bare.root)["warnings"]
    assert any("failed" in w for w in warnings) and any("2 cache hits" in w for w in warnings)


def test_questions_section(tmp_path: Path):
    run = mini_run(tmp_path)
    _evalrun(run, None)
    answers = [Answer(qid="Q1", key="Q1@aaaaaa", polarity="positive", question="q1", answer="a1", dollars=0.1, seconds=20.0),
               Answer(qid="Q2", key="Q2@bbbbbb", polarity="negative", question="q2", answer="a2", dollars=0.2, seconds=30.0)]
    write_jsonl(run.root / "answers.jsonl", answers)
    card = build_scorecard(run.root)
    assert card["questions"] is None and any("scry eval judge" in note for note in card["notes"])  # answers not judged

    def judgment(a: Answer, label: str, score: float) -> Judgment:
        return Judgment(run="s-r1", qid=a.qid, key=a.key, polarity=a.polarity, items={"M1": label == "correct", "X1": label == "wrong"},
                        quotes={"M1": "a", "X1": ""}, label=label, score=score, source="judge", dollars=0.015)

    write_judgments(run, [judgment(answers[0], "correct", 1.0), judgment(answers[1], "wrong", 0.0)])
    card = build_scorecard(run.root)
    q = card["questions"]
    assert q["positive"] == {"n": 1, "correct": 1, "partial": 0, "wrong": 0, "unscored": 0, "mean": 1.0}
    assert q["negative"] == {"n": 1, "correct": 0, "partial": 0, "wrong": 1, "unscored": 0, "mean": 0.0}
    assert (q["dollars_per_question"], q["ask_dollars"], q["judge_dollars"], q["seconds_per_question"], q["stale"]) == (0.15, 0.3, 0.03, 25.0, 0)
    assert card["units"]["questions.positive"] == {"Q1@aaaaaa": 1.0} and card["units"]["questions.negative"] == {"Q2@bbbbbb": 0.0}
    assert card["units"]["cost.per_question"] == {"Q1@aaaaaa": 0.1, "Q2@bbbbbb": 0.2}
    assert [(r["qid"], r["label"], r["items"], r["quotes"]) for r in q["answers"]] == [
        ("Q1", "correct", {"M1": True, "X1": False}, {"M1": "a", "X1": ""}), ("Q2", "wrong", {"M1": False, "X1": True}, {"M1": "a", "X1": ""})]
    assert card["commands"] is None and set(card["units"]) <= set(METRICS)
