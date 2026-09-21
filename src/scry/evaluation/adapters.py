"""Plain functions, and the only module of the harness that touches the pipeline's loaders, its search index and `ask`:
a renamed loader costs one function here, never a metric. Pipeline modules are imported inside the functions."""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass, field
from typing import Callable

from scry.config import Config
from scry.run import Run
from scry.schemas import Change, Interpretation, Lifetime


def frame_count(run: Run) -> int:
    return len(run.load_frames())


def lifetimes(run: Run) -> list[Lifetime]:
    return run.load_lifetimes()


def changes(run: Run) -> list[Change]:
    return run.load_changes()


def interpretations(run: Run) -> dict[str, Interpretation]:
    """By change id; `{}` when interpretations.jsonl is absent."""
    return run.load_interpretations()


def vlm_majority(run: Run) -> dict[str, str]:
    """Lifetime id → the model's majority reading, where there is one; `{}` without labels or without transcription."""
    labels = run.load_labels()
    if labels is None:
        return {}
    labelled = ((l.id, labels.lifetime(l.id)) for l in run.load_lifetimes())
    return {i: label.vlm for i, label in labelled if label is not None and label.vlm is not None}


def search_fn(run: Run, cfg: Config) -> Callable[[str], list[dict]] | None:
    """The agent's lexical search with no filter and no embedder; None when the run has no index.sqlite (never created
    here). Each hit carries `node_id`, `level` and `frames` (first and last frame)."""
    if not run.index_db.exists():
        return None
    from scry.index import open_db, search

    def hits_for(query: str) -> list[dict]:
        with closing(open_db(run.index_db)) as db:
            return search(db, query, cfg.index, embedder=None)

    return hits_for


@dataclass
class AskOutcome:
    """One answered question, as the harness records it."""
    text: str
    usage: dict
    dollars: float
    model: str
    turns: int
    tools: list[str]
    stop: str
    calls: list[dict] = field(default_factory=list)  # per tool call: name, input, results (a count), error
    prompt: str | None = None  # the ask prompt that answered: "ask-v1", or "ask-v1+noframes" under [ask] frames = false


def answer_fn(run: Run, cfg: Config, question: str) -> AskOutcome:
    """One call of `ask`: a fresh conversation, no call cache. A failed API call comes back with `stop "api_error"`."""
    from scry.ask import ask

    r = ask(run, cfg, question)
    return AskOutcome(text=r.text, usage=dict(r.usage), dollars=r.cost_usd, model=cfg.model.model, turns=r.turns,
                      tools=list(r.tool_calls), stop=r.stop, calls=[c.model_dump(exclude_none=True) for c in r.tool_log], prompt=r.prompt)
