import itertools
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from eval_fixtures import QUESTIONS

from scry.config import Config
from scry.evaluation import adapters
from scry.evaluation.adapters import AskOutcome
from scry.evaluation.questions import load_answers, parse_questions, run_questions
from scry.run import Run


def test_parse_questions():
    q1, q2 = parse_questions(QUESTIONS)
    assert (q1.id, q1.polarity, q1.style) == ("Q1", "positive", "exact-string lookup")
    assert q1.question == "Where does `git status` get run?"
    assert q1.reference == "At frame 2 (0:02.5), submitted by frame 3."
    assert [(i.id, i.kind) for i in q1.rubric] == [("M1", "must"), ("M2", "must"), ("X1", "must_not")]
    assert q1.rubric[1].text == "gives frame 2 or 3." and q1.rubric[2].text == "says it was not run."  # Evidence is not read
    assert re.fullmatch(r"Q1@[0-9a-f]{6}", q1.key)
    assert (q2.id, q2.polarity, q2.question) == ("Q2", "negative", "Did they push?")
    r1, r2 = parse_questions(QUESTIONS.replace("get run?", "run?"))  # an edited question is a different unit
    assert r1.key != q1.key and r2.key == q2.key
    with pytest.raises(ValueError, match="Q2"):
        parse_questions(QUESTIONS.replace("  - X1: says `git push` was executed.\n", ""))  # a negative question without an X line
    with pytest.raises(ValueError, match="Q1"):
        parse_questions(QUESTIONS + "### Q1 (positive, again)\n- **Question:** Again?\n- **Reference answer:** Yes.\n- **Rubric:**\n  - M1: says yes.\n")


def test_repo_question_file_parses():
    """Reads the committed draft on purpose. Nothing more is asserted: the owner may prune or rewrite it."""
    assert parse_questions((Path(__file__).parents[1] / "docs/ground-truth/span2-questions.md").read_text())


def _clock():
    ticks = itertools.count()
    return lambda: next(ticks) * 2.0  # every call measures 2.0 s


def _outcome(stop: str = "end_turn", dollars: float = 0.1) -> AskOutcome:
    return AskOutcome("It ran at frame 2.", {"input_tokens": 10_000, "output_tokens": 2_000}, dollars, "claude-opus-5", 3,
                      ["search", "get_frame"], stop)


def test_run_questions_records_cost_resumes_and_keeps_errors(tmp_path: Path):
    path = tmp_path / "q.md"
    path.write_text(QUESTIONS)
    cfg = Config()
    asked: list[str] = []

    def answer(run, cfg, question):
        asked.append(question)
        return _outcome()

    run = Run(tmp_path / "run")
    a1, a2 = run_questions(run, cfg, path, answer=answer, clock=_clock())
    assert (a1.qid, a1.polarity, a1.answer, a1.dollars, a1.seconds, a1.turns) == ("Q1", "positive", "It ran at frame 2.", 0.1, 2.0, 3)
    assert (a2.qid, a2.dollars, a2.seconds, a2.tools, a2.model, a2.error) == ("Q2", 0.1, 2.0, ["search", "get_frame"], "claude-opus-5", None)
    assert len((run.root / "answers.jsonl").read_text().splitlines()) == 2
    assert asked == ["Where does `git status` get run?", "Did they push?"]

    path.write_text(QUESTIONS.replace("Did they push?", "Did they push anything?"))  # a reworded question is asked again
    asked.clear()
    b1, b2 = run_questions(run, cfg, path, answer=answer, clock=_clock())
    assert asked == ["Did they push anything?"]
    assert b1 == a1 and b2.key != a2.key and load_answers(run) == [b1, b2]

    def failing(run, cfg, question):
        if "git status" in question:
            raise RuntimeError("rate limit")
        return _outcome()

    run = Run(tmp_path / "run2")
    path.write_text(QUESTIONS)
    with pytest.raises(RuntimeError, match="1 questions failed"):
        run_questions(run, cfg, path, answer=failing, clock=_clock())
    f1, f2 = load_answers(run)  # both lines were written before it raised
    assert (f1.error, f1.answer, f1.dollars) == ("RuntimeError: rate limit", "", 0.0)
    assert (f2.error, f2.answer) == (None, "It ran at frame 2.")

    run = Run(tmp_path / "run3")
    with pytest.raises(RuntimeError, match="1 questions failed"):  # `ask` returns a failed API call instead of raising
        run_questions(run, cfg, path, answer=lambda run, cfg, q: _outcome("api_error" if "git status" in q else "end_turn", 0.02),
                      clock=_clock())
    g1, g2 = load_answers(run)
    assert (g1.error, g1.answer, g1.dollars, g1.stop) == ("It ran at frame 2.", "", 0.02, "api_error")
    assert g2.error is None
    asked.clear()
    h1, h2 = run_questions(run, cfg, path, answer=answer, clock=_clock())  # only the failed question is asked again
    assert asked == ["Where does `git status` get run?"]
    assert h1.error is None and h2 == g2


def test_answer_fn_maps_ask_result(tmp_path: Path, monkeypatch):
    seen = []

    def fake_ask(run, cfg, question, client=None):
        seen.append(question)
        return SimpleNamespace(text="x", turns=2, tool_calls=["search"], usage={"input_tokens": 1}, cost_usd=0.0225, stop="end_turn")

    monkeypatch.setattr("scry.ask.ask", fake_ask)
    cfg = Config()
    out = adapters.answer_fn(Run(tmp_path), cfg, "Did they push?")
    assert seen == ["Did they push?"]
    assert out == AskOutcome(text="x", usage={"input_tokens": 1}, dollars=0.0225, model=cfg.model.model, turns=2, tools=["search"],
                             stop="end_turn")
