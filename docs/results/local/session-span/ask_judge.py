"""Ask the span's questions on a run's index with the built-in answering agent on the API (the owner's scry.toml:
Anthropic claude-opus-5), then judge them blind against the rubric with the harness's judge (same model, low effort).
Usage: ask_judge.py <run-dir> <questions.md> <judge-cache-dir> [ask-config.toml]"""
import json, sys
from pathlib import Path
from scry.env import load_dotenv
load_dotenv()
from scry.config import load_config
from scry.run import Run
from scry.evaluation.questions import run_questions, parse_questions, load_answers
from scry.evaluation.judge import judge_answers, judge_provider, write_judgments
run = Run(Path(sys.argv[1])); qpath = Path(sys.argv[2]); jcache = Path(sys.argv[3])
cfg = load_config(Path(sys.argv[4]) if len(sys.argv) > 4 else None)
print('ask model:', cfg.ask.model or cfg.model.model, 'provider', cfg.model.provider, 'concurrency', cfg.model.concurrency, flush=True)
try:
    answers = run_questions(run, cfg, qpath)
except RuntimeError as e:
    print('ask:', e); answers = [a for a in load_answers(run) if a.error is None]
for a in answers:
    print(f'--- {a.qid} ${a.dollars:.4f} turns={a.turns} tools={a.tools} stop={a.stop} model={a.model}\n{a.answer}\n', flush=True)
print('ask total $', round(sum(a.dollars for a in answers), 4))
qs = parse_questions(qpath.read_text())
js = judge_answers(run.root.name, qs, answers, judge_provider(cfg, jcache))
write_judgments(run, js)
for j in js:
    print(f'JUDGE {j.qid}: {j.label} score={j.score} ${j.dollars:.4f} items={j.items}')
    for k, v in (j.quotes or {}).items(): print(f'    {k}: {str(v)[:200]}')
print('judge total $', round(sum(j.dollars for j in js), 4))
