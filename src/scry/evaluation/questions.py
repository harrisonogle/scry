"""The question set: the parser of a question file (the format of docs/ground-truth/span2-questions.md) and the runner
that asks every question once per run directory through `ask`. These calls are what is judged: no call cache is
involved, and a question that failed is recorded as an error, never as an answer."""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel

from scry.config import Config
from scry.evaluation import adapters
from scry.jsonl import read_jsonl, write_jsonl
from scry.run import Run
from scry.textdiff import norm

_HEADING = re.compile(r"^### (Q\d+) \((positive|negative), ([^)]+)\)\s*$")
_BULLET = re.compile(r"^- \*\*([^*]+):\*\*\s*(.*)$")
_ITEM = re.compile(r"^- ([MX])(\d+):\s*(.*)$")
_FIELDS = {"Question": "question", "Reference answer": "reference", "Rubric": "rubric"}


@dataclass
class RubricItem:
    id: str  # M1, X1, …
    kind: Literal["must", "must_not"]
    text: str


@dataclass
class Question:
    id: str
    key: str  # "<id>@<6 hex of the question text>": an edited question is a different unit
    polarity: Literal["positive", "negative"]
    style: str
    question: str
    reference: str
    rubric: list[RubricItem]


def _joined(parts: list[str]) -> str:
    """A value and its continuation lines, stripped and joined with one space."""
    return " ".join(p.strip() for p in parts if p.strip())


def _question(qid: str, polarity: str, style: str, lines: list[str]) -> Question:
    values: dict[str, list[str]] = {}  # field → the parts of its value
    items: list[tuple[str, list[str]]] = []  # rubric id → the parts of its text
    field: str | None = None
    parts: list[str] | None = None  # where a continuation line goes
    for line in lines:
        indented, s = line[:1] in (" ", "\t"), line.strip()
        bullet = _BULLET.match(line)
        if bullet:  # a top-level bullet; one that is not read (Evidence) ends the value before it
            field = _FIELDS.get(bullet.group(1).strip())
            parts = [bullet.group(2)] if field else None
            if field:
                values[field] = parts
        elif indented and s.startswith("- "):
            item = _ITEM.match(s) if field == "rubric" else None
            parts = None
            if item:
                parts = [item.group(3)]
                items.append((item.group(1) + item.group(2), parts))
        elif indented and s and parts is not None:
            parts.append(s)
        else:
            parts = None
    for name, field in _FIELDS.items():
        if field not in values:
            raise ValueError(f"{qid}: no **{name}**")
    ids = [i for i, _ in items]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{qid}: a rubric id is repeated")
    if not any(i.startswith("M") for i in ids):
        raise ValueError(f"{qid}: the rubric has no M line")
    if polarity == "negative" and not any(i.startswith("X") for i in ids):
        raise ValueError(f"{qid}: a negative question needs an X line")
    text = _joined(values["question"])
    return Question(id=qid, key=f"{qid}@{hashlib.sha256(norm(text).encode()).hexdigest()[:6]}", polarity=polarity,
                    style=style.strip(), question=text, reference=_joined(values["reference"]),
                    rubric=[RubricItem(i, "must" if i.startswith("M") else "must_not", _joined(p)) for i, p in items])


def parse_questions(md: str) -> list[Question]:
    """The question blocks of the file, in file order; everything outside them is ignored."""
    blocks: list[tuple[re.Match, list[str]]] = []
    inside = False
    for line in md.split("\n"):
        heading = _HEADING.match(line)
        if heading:
            blocks.append((heading, []))
            inside = True
        elif line.startswith("#"):
            inside = False
        elif inside:
            blocks[-1][1].append(line)
    questions = []
    for heading, lines in blocks:
        if any(q.id == heading.group(1) for q in questions):
            raise ValueError(f"{heading.group(1)}: the id is repeated")
        questions.append(_question(*heading.groups(), lines))
    return questions


class Answer(BaseModel):
    qid: str
    key: str
    polarity: str
    question: str
    answer: str  # empty when the question failed
    usage: dict = {}
    model: str | None = None
    dollars: float = 0.0
    seconds: float = 0.0
    turns: int = 0
    tools: list[str] = []
    stop: str | None = None
    error: str | None = None


def _answers_path(run: Run) -> Path:
    return run.root / "answers.jsonl"


def load_answers(run: Run) -> list[Answer]:
    return read_jsonl(_answers_path(run), Answer)


def run_questions(run: Run, cfg: Config, questions_path: Path, answer: Callable[..., adapters.AskOutcome] = adapters.answer_fn,
                  clock: Callable[[], float] = time.perf_counter) -> list[Answer]:
    """Ask every question of the file once, in file order, each in a fresh conversation, and write answers.jsonl after
    each. An answer the file already holds for the same key, without an error, is kept. A failed question is recorded
    with its error and an empty answer; after the last question any failure raises, so the run is marked failed and the
    next `scry eval run` asks only those questions again."""
    questions = parse_questions(Path(questions_path).read_text())
    answers = {a.key: a for a in load_answers(run) if a.error is None}
    for q in questions:
        if q.key in answers:
            continue
        base = dict(qid=q.id, key=q.key, polarity=q.polarity, question=q.question)
        t0 = clock()
        try:
            out = answer(run, cfg, q.question)
        except Exception as e:
            answers[q.key] = Answer(**base, answer="", error=f"{type(e).__name__}: {e}"[:500], seconds=round(clock() - t0, 1))
        else:
            failed = out.stop == "api_error"  # the text is then the error message, never an answer
            answers[q.key] = Answer(**base, answer="" if failed else out.text, error=out.text[:500] if failed else None,
                                    usage=out.usage, model=out.model, dollars=out.dollars, seconds=round(clock() - t0, 1),
                                    turns=out.turns, tools=out.tools, stop=out.stop)
        write_jsonl(_answers_path(run), [answers[x.key] for x in questions if x.key in answers])
    result = [answers[q.key] for q in questions]
    write_jsonl(_answers_path(run), result)
    failed = sum(a.error is not None for a in result)
    if failed:
        raise RuntimeError(f"{failed} questions failed")
    return result
