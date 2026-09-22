"""The honest text-change contract of docs/results/p8/analysis.md on a span2 (155-187) run beside the Opus and Sonnet full
runs, restricted to the transitions the span holds. Truth tables copied from docs/results/p8/scripts/interp.py.
Usage: interp_local.py <run-dir>...   (a run's changes.jsonl maps its transition ids to source frames). Free: reads files only."""
import json, os, re, sys, collections
from pathlib import Path
ROOT = '<repo>/.claude/worktrees/localvlm'
RUNS = {'O inc r1': 'runs/eval/p4/full-inc-transcribing-r1', 'O inc r2': 'runs/eval/p4/full-inc-transcribing-r2',
        'S inc r1': 'runs/eval/p8/full-inc-transcribing-sonnet5-r1', 'S inc r2': 'runs/eval/p8/full-inc-transcribing-sonnet5-r2'}
for p in sys.argv[1:]:
    RUNS[Path(p).parent.name + '/' + Path(p).name] = p
CD = 'kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1'
EX = 'kubectl expose deployment kodekloudapp --type=LoadBalancer --port=80 --target-port=80'
TYPED = {155: 'a', 157: 'az account show', 161: 'az c', 162: 'az configure --defaults group=RG1-KodeKloud-AKS', 163: 'az configure --defaults group=RG1-KodeKloud-AKS',
         165: 'az ak', 166: 'az aks get', 167: 'az aks get-Credentials --name AKS1-KodeKloudApp', 168: 'az aks get-Credentials --name AKS1-KodeKloudApp',
         172: 'kubect', 173: 'kubectl', 174: 'kubectl ', 175: 'kubectl config', 176: 'kubectl config current-context', 178: 'kubect', 179: 'kubectl get ',
         185: 'kubectl get deplo', 189: 'kubectl ', 190: 'kubectl create deployment', 191: CD, 192: CD, 193: CD, 194: CD, 195: CD + ' --', 196: CD + ' --replicas', 197: CD + ' --replicas=1',
         199: 'kubect', 200: 'kubectl get deplo', 205: 'ku', 206: 'kubect', 207: 'kubectl ', 208: 'kubectl expose ', 209: EX, 211: 'kubectl ', 212: 'kubectl get s'}
SUGG = {155: 'az login', 161: 'az configure --defaults group=RG1-KodeKloud-AKS', 165: 'az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2',
        166: 'az aks get-Credentials --name AKS1-KodeKloudApp', 172: 'kubectl rollout undo deployment/kodekloudapp', 173: 'kubectl rollout undo deployment/kodekloudapp',
        174: 'kubectl rollout undo deployment/kodekloudapp', 175: 'kubectl config current-context', 178: 'kubectl config current-context', 179: 'kubectl get svc',
        185: 'kubectl get deployment', 189: 'kubectl get pods', 190: CD, 199: CD + ' --replicas=1', 200: 'kubectl get deployment', 205: 'kubectl get pods', 206: 'kubectl get pods', 207: 'kubectl get pods', 208: EX, 211: EX, 212: 'kubectl get svc'}
SUBMIT = {158: 'az account show', 164: 'az configure --defaults group=RG1-KodeKloud-AKS', 169: 'az aks get-Credentials --name AKS1-KodeKloudApp', 170: 'Y', 171: 'y',
          177: 'kubectl config current-context', 180: 'kubectl get nodes', 186: 'kubectl get deployment', 187: 'kubectl get pods', 198: CD + ' --replicas=1', 201: 'kubectl get deployment', 203: 'kubectl get pods', 210: EX, 213: 'kubectl get service'}
NEVER = ['az login', 'az aks scale', 'kubectl rollout undo', 'kubectl get svc', 'kubectl config current-context']  # the five never-run strings of span2-commands.md
LO, HI = 156, 187  # frame b of the span's transitions


def norm(s): return re.sub(r'\s+', ' ', (s or '')).strip()


def classify(n, ent):
    typed = norm(TYPED[n]); sug = norm(SUGG[n]); e = norm(ent)
    if ent is None: return 'none'
    if e.lower() == typed.lower(): return 'typed'
    if e.lower() == sug[:len(typed) + 1].lower() or e.lower() == sug[:len(TYPED[n]) + 1].strip().lower(): return 'cursor-char'
    if e.lower().startswith(typed.lower()) and sug.lower().startswith(e.lower()): return 'SUGGESTION' if len(e) - len(typed) >= 2 else 'cursor-char'
    if e.lower() == sug.lower(): return 'SUGGESTION'
    return 'other'


def load(rd):
    """interpretations by frame b (source frame numbers), via the run's changes.jsonl"""
    p = os.path.join(ROOT, rd, 'interpretations.jsonl')
    if not os.path.exists(p): return None
    to_frame = {json.loads(l)['id']: json.loads(l)['to_frame'] for l in open(os.path.join(ROOT, rd, 'changes.jsonl'))}
    out = {}
    for l in open(p):
        d = json.loads(l); out[to_frame[d['id']]] = d
    return out


data = {k: load(v) for k, v in RUNS.items()}; data = {k: v for k, v in data.items() if v}
names = list(data)
sugg = [n for n in sorted(SUGG) if LO <= n <= HI]
print(f'## entered_text on the {len(sugg)} transitions of frames {LO}-{HI} (of the 21 T155..T212) whose live line shows a grey suggestion')
tally = {k: collections.Counter() for k in names}
print('| frame b | typed (by eye) | ' + ' | '.join(names) + ' |'); print('|---|---|' + '---|' * len(names))
for n in sugg:
    row = []
    for k in names:
        d = data[k].get(n)
        if d is None or d.get('error'): row.append('(no record)'); tally[k]['missing'] += 1; continue
        c = classify(n, d['entered_text']); tally[k][c] += 1
        row.append(('`%s`' % d['entered_text'] if d['entered_text'] is not None else 'null') + (' **%s**' % c if c not in ('typed',) else '') + (' SUB=%s' % d['submitted'] if d['submitted'] != 'no' else ''))
    print(f'| {n} | `{TYPED[n]}` + grey `{SUGG[n][len(TYPED[n].rstrip()):][:30]}` | ' + ' | '.join(row) + ' |')
print(); print('tally (SUGGESTION = never-typed suggested text recorded as entered):')
for k in names: print('  ', k, dict(tally[k]))
subs = [n for n in SUBMIT if LO <= n <= HI]
print(); print(f'## submitted over frames {LO}..{HI} (truth: yes at ' + ', '.join(str(n) for n in subs) + ')')
for k in names:
    fy = []; miss = []; unclear = []; wrongtext = []; yes = 0
    for n in range(LO, HI + 1):
        d = data[k].get(n)
        if d is None or d.get('error'): continue
        if d['submitted'] == 'yes': yes += 1
        if d['submitted'] == 'yes' and n not in SUBMIT: fy.append((n, d['entered_text']))
        if n in SUBMIT and d['submitted'] != 'yes': miss.append((n, d['submitted'], d['entered_text']))
        if d['submitted'] == 'unclear': unclear.append((n, d['entered_text']))
        if n in SUBMIT and d['submitted'] == 'yes' and norm(d['entered_text']) != norm(SUBMIT[n]): wrongtext.append((n, d['entered_text']))
    print(f'  {k}: yes {yes}; false yes {fy}; missed {miss}; unclear {len(unclear)} {unclear[:6]}; yes with other text {wrongtext}')
print(); print(f'## never-run strings in entered_text (frames {LO}..{HI}), with submitted; "submitted: yes" on one is a false run')
for k in names:
    hits = [(n, d['entered_text'], d['submitted']) for n, d in sorted(data[k].items()) if LO <= n <= HI for s in NEVER if d.get('entered_text') and s in d['entered_text']]
    false_runs = [h for h in hits if h[2] == 'yes' and not any(norm(h[1]) == norm(v) for v in SUBMIT.values())]
    print(f'   {k}: {len(hits)} mentions, false runs {len(false_runs)}: {hits}')
print(); print(f'## does the record call the grey text a suggestion? (action+result+description mention suggest/predict/grey/gray/ghost/autocomplet/history/dim) on the {len(sugg)}')
for k in names:
    yes = 0; typedcalled = []
    for n in sugg:
        d = data[k].get(n)
        if d is None or d.get('error'): typedcalled.append(n); continue
        txt = ' '.join([d.get('action') or '', d.get('result') or '', d.get('description') or '']).lower()
        if re.search(r'suggest|predict|gr[ae]y|ghost|autocomplet|history|dim', txt): yes += 1
        else: typedcalled.append(n)
    print(f'   {k}: {yes}/{len(sugg)} mention it; not mentioned at {typedcalled}')
print(); print('## records, errors, confidence, invalid citations')
for k in names:
    recs = [d for n, d in data[k].items() if LO <= n <= HI]
    errs = [d['id'] for d in recs if d.get('error')]
    conf = [d['confidence'] for d in recs if d.get('confidence') is not None]
    print(f'   {k}: {len(recs)} records, {len(errs)} errors {errs[:5]}, mean confidence {sum(conf)/max(1,len(conf)):.2f}')
