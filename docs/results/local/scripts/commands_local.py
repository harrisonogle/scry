"""The harness's command scores (found, exact, submitted, false run) for a local span2 run, beside the Opus and Sonnet
full runs' scorecards. Optionally first runs summarize (a model call on the run's own [model]) and index (free) so
`found` can be scored. Usage: commands_local.py <run-dir> [--build]"""
import json, logging, sys
from pathlib import Path
from scry.config import Config
from scry.run import Run
from scry.evaluation.commands import score_commands

ROOT = Path('<repo>/.claude/worktrees/localvlm')
GT = ROOT / 'docs/ground-truth/span2-commands.md'
REF = {'O inc r1': 'runs/eval/p4/full-inc-transcribing-r1', 'O inc r2': 'runs/eval/p4/full-inc-transcribing-r2',
       'O none r1': 'runs/eval/p4/full-none-r1', 'S none r1': 'runs/eval/p8/full-none-sonnet5-r1',
       'S inc r1': 'runs/eval/p8/full-inc-transcribing-sonnet5-r1', 'S inc r2': 'runs/eval/p8/full-inc-transcribing-sonnet5-r2'}
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
run_dir = Path(sys.argv[1]); build = '--build' in sys.argv
run = Run(run_dir)
cfg = Config.model_validate(json.load(open(run_dir / 'config.json')))
if build:
    from scry.summarize import run_summarize
    from scry.index import build_index
    run_summarize(run, cfg)
    build_index(run, cfg)
    m = json.load(open(run_dir / 'manifest.json'))['stages'].get('summarize', {})
    print('summarize:', {k: m.get(k) for k in ('calls', 'usage', 'errors', 'model')})
sc = score_commands(run, cfg, GT)
json.dump(sc, open(run_dir / 'commands-score.json', 'w'), indent=1)
f = lambda x: f'{x[0]}/{x[1]}' if x else '—'


def row(name, c):
    r = c['rates']; ex = r['exact']
    return f"| {name} | {f(r['found'])} | {f(ex.get('ocr'))} | {f(ex.get('vlm'))} | {f(ex.get('any'))} | {f(r['submitted'])} | {f(r['false_run'])} | {c['submit_frame_error_abs_mean']} |"


print('| run | found | exact.ocr | exact.vlm | exact.any | submitted | false run | submit frame err |'); print('|' + '---|' * 8)
print(row(run_dir.parent.name + '/' + run_dir.name, sc))
for k, rd in REF.items():
    p = ROOT / rd / 'scorecard.json'
    if p.exists():
        print(row(k + ' (full video)', json.load(open(p))['commands']))
print()
for e in sc['entries']:
    if e.get('scorable'):
        print(f"  #{e['n']} {e['text']!r}: found={e.get('found')} submitted={e.get('submitted')} submit_frame_error={e.get('submit_frame_error')} exact={e.get('exact')} claim={str(e.get('claim'))[:120]}")
for nr in sc['never_run']:
    print(f"  NEVER-RUN {nr['text']!r}: false_run={nr.get('false_run')} claim={str(nr.get('claim'))[:160]}")
