from eval_fixtures import QUESTIONS

from scry.evaluation.judge import JUDGE_PROMPT_VERSION, ItemVerdict, JudgeOutput, judge_answers, label_from, load_judgments, write_judgments
from scry.evaluation.questions import Answer, RubricItem, parse_questions
from scry.providers import VlmResult
from scry.run import Run


class FakeJudge:
    """A provider that records every call and returns the same canned verdicts."""
    model = "claude-opus-5"

    def __init__(self, verdicts: dict[str, bool]):
        self.verdicts = verdicts
        self.calls: list[dict] = []

    async def complete(self, **kw) -> VlmResult:
        self.calls.append(kw)
        items = [ItemVerdict(id=i, holds=holds, quote="git status ran" if holds else "") for i, holds in self.verdicts.items()]
        return VlmResult(JudgeOutput(items=items), None, {"input_tokens": 2_000, "output_tokens": 200})


def _answer(q, text: str) -> Answer:
    return Answer(qid=q.id, key=q.key, polarity=q.polarity, question=q.question, answer=text, dollars=0.1, model="claude-opus-5")


def test_label_from():
    rubric = [RubricItem("M1", "must", "a"), RubricItem("M2", "must", "b"), RubricItem("X1", "must_not", "c")]
    assert label_from({"M1": True, "M2": True, "X1": False}, rubric) == "correct"
    assert label_from({"M1": True, "M2": False, "X1": False}, rubric) == "partial"
    assert label_from({"M1": True, "M2": True, "X1": True}, rubric) == "wrong"
    assert label_from({"M1": False, "M2": False, "X1": False}, rubric) == "wrong"
    negative = [RubricItem("M1", "must", "says no"), RubricItem("X1", "must_not", "says yes")]
    assert label_from({"M1": True, "X1": False}, negative) == "correct"  # a bare, correct "No" is correct


def test_judge_scores_costs_and_is_blind(tmp_path):
    questions = parse_questions(QUESTIONS)
    q1 = questions[0]
    judge = FakeJudge({"M1": True, "M2": True, "X1": False})
    [j] = judge_answers("span2-transcribing-r1", questions, [_answer(q1, "git status ran at frame 2.")], judge)
    assert (j.run, j.qid, j.key, j.polarity) == ("span2-transcribing-r1", "Q1", q1.key, "positive")
    assert (j.label, j.score, j.source, j.dollars, j.error) == ("correct", 1.0, "judge", 0.015, None)  # 2,000 × 5 + 200 × 25 millionths
    assert j.items == {"M1": True, "M2": True, "X1": False} and set(j.quotes) == {"M1", "M2", "X1"}
    [kw] = judge.calls
    assert (kw["stage"], kw["effort"], kw["prompt_version"], kw["output_model"]) == ("judge", "low", JUDGE_PROMPT_VERSION, JudgeOutput)
    sent = kw["system"] + "".join(b["text"] for b in kw["blocks"])
    assert all(b["type"] == "text" for b in kw["blocks"])  # never a frame
    assert "span2-transcribing-r1" not in sent and "transcribing" not in sent  # blind to the run
    for part in (q1.question, q1.reference, "M2: gives frame 2 or 3.", "git status ran at frame 2."):
        assert part in sent

    judge_answers("span2-none-r2", questions, [_answer(q1, "git status ran at frame 2.")], judge)  # another run, the same answer
    judge_answers("span2-none-r3", questions, [_answer(q1, "It ran at frame 3.")], judge)
    h1, h2, h3 = (c["input_hashes"] for c in judge.calls)
    assert h1 == h2 and h1 != h3  # identical answers get one verdict from the judge's cache

    judge = FakeJudge({"M1": True, "M2": True, "X1": False})
    stale = Answer(qid="Q9", key="Q9@000000", polarity="positive", question="gone", answer="x")
    js = judge_answers("r", questions, [_answer(q1, "  "), _answer(questions[1], "").model_copy(update={"error": "RuntimeError: x"}), stale],
                       judge)
    assert [(j.label, j.score, j.source, j.dollars) for j in js] == [("wrong", 0.0, "rule", 0.0)] * 2  # the stale answer is not judged
    assert js[0].items == {"M1": False, "M2": False, "X1": False} and judge.calls == []
    run = Run(tmp_path)
    write_judgments(run, js)
    assert load_judgments(run) == js


def test_missing_item_is_an_error_not_a_default():
    questions = parse_questions(QUESTIONS)
    [j] = judge_answers("r", questions, [_answer(questions[0], "git status ran.")], FakeJudge({"M1": True, "M2": True, "Z9": True}))
    assert (j.label, j.score) == (None, None) and "X1" in j.error
    assert j.items == {"M1": True, "M2": True} and j.dollars == 0.015  # a verdict for an id the rubric lacks is dropped

    class Refusing(FakeJudge):
        async def complete(self, **kw) -> VlmResult:
            return VlmResult(None, "refusal", {"input_tokens": 2_000, "output_tokens": 0})

    [j] = judge_answers("r", questions, [_answer(questions[0], "git status ran.")], Refusing({}))
    assert (j.label, j.score, j.error, j.items) == (None, None, "refusal", {})
