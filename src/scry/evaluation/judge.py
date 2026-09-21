"""Scoring answers against their rubric lines with a separate model call. The judge is blind: it is given the question,
the reference answer, the rubric lines and the answer, and never the run's name, its configuration, the phase, another
answer or a frame. It decides each line; code derives correct, partial or wrong. The judge is an instrument, not the
thing measured, so its calls are cached apart from every run: re-scoring is free and repeatable, and two identical
answers get one verdict."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from scry.config import Config
from scry.costs import estimate_cost
from scry.evaluation.questions import Answer, Question, RubricItem
from scry.jsonl import read_jsonl, sha256_obj, write_jsonl
from scry.providers import CallCache, VlmProvider, text_block
from scry.run import Run

JUDGE_PROMPT_VERSION = "judge-v1"
JUDGE_SYSTEM = """\
You grade one answer to a question about a screen-recording tutorial. You are given the question, a reference answer
written from ground truth, a list of rubric statements, and the answer to grade. For each rubric statement decide
whether it is true OF THE ANSWER, not whether it is true of the video. Judge only what the answer says. Do not reward
or punish style, length, hedging or citations. Only a statement that says the answer "contains the exact string" is
about exact text: it holds only if the answer contains that string character for character, including case. Every
other statement is judged on meaning: "names the command", "gives the output" or "says ..." holds when the answer
unmistakably refers to the same thing, whatever its spelling, spacing or case. A statement that the answer gives a
time in a range also holds when the answer names a frame in the stated range. A "says ..." or "claims ..." statement
holds when the answer asserts it as its conclusion, not when it mentions it as a possibility it rejects. Return every
rubric id exactly once, with holds true or false and a short verbatim quote from the answer that decided it (empty
when nothing in the answer bears on it)."""


class ItemVerdict(BaseModel):
    id: str = Field(description="The rubric statement's id, exactly as listed (M1, X1, …).")
    holds: bool = Field(description="Whether the statement is true of the answer.")
    quote: str = Field(description="A short verbatim quote from the answer that decided it; empty when nothing bears on it.")


class JudgeOutput(BaseModel):
    items: list[ItemVerdict]


SCORE = {"correct": 1.0, "partial": 0.5, "wrong": 0.0}  # for means only; the counts are always shown beside a mean


def label_from(items: dict[str, bool], rubric: list[RubricItem]) -> Literal["correct", "partial", "wrong"]:
    """Wrong when any must-not line holds or no must line holds; correct when every must line holds and no must-not
    line does; otherwise partial."""
    must = [items[i.id] for i in rubric if i.kind == "must"]
    if any(items[i.id] for i in rubric if i.kind == "must_not") or not any(must):
        return "wrong"
    return "correct" if all(must) else "partial"


class Judgment(BaseModel):
    run: str  # recorded here, never sent to the judge
    qid: str
    key: str
    polarity: str
    items: dict[str, bool]
    quotes: dict[str, str]
    label: str | None
    score: float | None
    source: Literal["judge", "rule"]
    model: str | None = None
    usage: dict = {}
    dollars: float = 0.0
    error: str | None = None


def _block(q: Question, answer: str) -> str:
    rubric = "\n".join(f"{i.id}: {i.text}" for i in q.rubric)
    return f"Question:\n{q.question}\n\nReference answer:\n{q.reference}\n\nRubric statements:\n{rubric}\n\nAnswer to grade:\n{answer}"


async def _judge(run_name: str, q: Question, a: Answer, provider: VlmProvider, effort: str) -> Judgment:
    base = dict(run=run_name, qid=q.id, key=q.key, polarity=q.polarity)
    if a.error is not None or not a.answer.strip():  # nothing to grade: decided by rule, without a call
        return Judgment(**base, items={i.id: False for i in q.rubric}, quotes={i.id: "" for i in q.rubric}, label="wrong",
                        score=SCORE["wrong"], source="rule")
    hashed = {"question": q.question, "reference": q.reference, "rubric": [[i.id, i.text] for i in q.rubric], "answer": a.answer}
    res = await provider.complete(stage="judge", system=JUDGE_SYSTEM, blocks=[text_block(_block(q, a.answer))],
                                  output_model=JudgeOutput, effort=effort, prompt_version=JUDGE_PROMPT_VERSION,
                                  input_hashes=[sha256_obj(hashed)])
    base |= dict(source="judge", model=provider.model, usage=res.usage,
                 dollars=0.0 if res.cached else estimate_cost(res.usage, provider.model))
    if res.parsed is None:  # a provider error or a refusal: nothing is defaulted
        return Judgment(**base, items={}, quotes={}, label=None, score=None, error=res.error or "no verdicts")
    ids = {i.id for i in q.rubric}
    verdicts = {v.id: v for v in res.parsed.items if v.id in ids}  # a verdict for an id the rubric lacks is dropped
    items = {i: v.holds for i, v in verdicts.items()}
    quotes = {i: v.quote for i, v in verdicts.items()}
    missing = [i.id for i in q.rubric if i.id not in verdicts]
    if missing:
        return Judgment(**base, items=items, quotes=quotes, label=None, score=None, error=f"no verdict for {', '.join(missing)}")
    label = label_from(items, q.rubric)
    return Judgment(**base, items=items, quotes=quotes, label=label, score=SCORE[label])


def judge_answers(run_name: str, questions: list[Question], answers: list[Answer], provider: VlmProvider,
                  effort: str = "low") -> list[Judgment]:
    """One judgment per answer whose key the question file still has, in answer order; an answer to a wording the file
    no longer has is stale and is not judged. One call per answer, none for an empty or failed one."""
    by_key = {q.key: q for q in questions}

    async def every() -> list[Judgment]:
        return list(await asyncio.gather(*(_judge(run_name, by_key[a.key], a, provider, effort) for a in answers if a.key in by_key)))

    return asyncio.run(every())


def judge_provider(base_cfg: Config, cache_dir: Path) -> VlmProvider:
    """The pipeline's model on the base config's [model], with a call cache of the judge's own, never a run's."""
    from scry.providers.anthropic_ import AnthropicProvider

    return AnthropicProvider(base_cfg.model, CallCache(cache_dir))


def _path(run: Run) -> Path:
    return run.root / "judgments.jsonl"


def write_judgments(run: Run, js: list[Judgment]) -> None:
    write_jsonl(_path(run), js)


def load_judgments(run: Run) -> list[Judgment]:
    return read_jsonl(_path(run), Judgment)
