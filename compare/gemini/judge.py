"""Score the G1 and G2 answers with the harness's blind judge (scry.evaluation.judge: judge-v1 prompt, the base
config's [model] = claude-opus-5, effort low, as `scry eval judge` runs it), with a call cache of this comparison's own
under runs/compare-gemini/judge-cache. Writes judgments.jsonl beside each arm's answers.jsonl. No run directory is
touched; the judge never sees which arm produced an answer."""
from __future__ import annotations

import sys
from pathlib import Path

from compare.gemini.common import OUT, REPO, Ledger, questions, read_jsonl, setup, write_jsonl
from scry.config import load_config
from scry.evaluation.judge import judge_answers, judge_provider
from scry.evaluation.questions import Answer


def main() -> None:
    setup()
    cfg = load_config(REPO / "scry.toml")  # [model] claude-opus-5, the same base config the phases judged with
    cfg.model.concurrency = 8
    qs = questions()
    ledger = Ledger()
    for arm in sys.argv[1:] or ["g1", "g2"]:
        answers = [Answer(**a) for a in read_jsonl(OUT / arm / "answers.jsonl")]
        provider = judge_provider(cfg, OUT / "judge-cache")
        js = judge_answers(arm, qs, answers, provider, effort="low")
        write_jsonl(OUT / arm / "judgments.jsonl", js)
        dollars = sum(j.dollars for j in js)
        ledger.add("anthropic", "judge", arm, dollars, 0.0, all(j.error is None for j in js),
                   f"{len(js)} judged, hits {provider.stats['hits']}, misses {provider.stats['misses']}")
        labels = {}
        for j in js:
            labels[j.label] = labels.get(j.label, 0) + 1
        print(f"{arm}: {len(js)} judged, ${dollars:.4f}, {labels}, errors {[j.qid for j in js if j.error]}")


if __name__ == "__main__":
    main()
