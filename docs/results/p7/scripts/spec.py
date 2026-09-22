"""Specific checks. Usage: spec.py <span>"""
import json, sys, re
from collections import Counter, defaultdict
from pathlib import Path
BASE = Path('<repo>/runs/eval')
SCALES = ['s100', 'sonnet5']
def rootof(n): return BASE / ('p7' if 'sonnet5' in n else 'p3')
span = sys.argv[1]
def load(n):
    ann = {}
    for l in open(rootof(n) / n / 'annotations.jsonl'):
        a = json.loads(l); ann[a['frame']] = a
    boxes = {}
    for l in open(rootof(n) / n / 'boxes.jsonl'):
        fb = json.loads(l); boxes[fb['frame']] = {b['id']: b for b in fb['boxes']}
    return ann, boxes
def cls(c):
    if c is None: return 'none'
    if c['kind'] == 'popup': return 'P'
    s = (c['app'] + ' ' + c['name']).lower()
    if 'powershell' in s or 'terminal' in s or 'pwsh' in s or 'command' in s: return 'term'
    if 'edge' in s or 'browser' in s or 'chrome' in s or 'azure' in s: return 'browser'
    if 'taskbar' in s or 'windows' in s or 'explorer' in s or 'desktop' in s: return 'os'
    return 'other'
def cont_of(a, box):
    cid = next((x['container'] for x in a['assign'] if x['box'] == box), None)
    return next((c for c in a['containers'] if c['id'] == cid), None)
runs = {}
for s in SCALES:
    for r in (1, 2):
        n = f'{span}-{s}-r{r}'
        if (rootof(n) / n / 'annotations.jsonl').exists(): runs[n] = load(n)
names = list(runs)
# app vocabulary
voc = Counter()
for n, (ann, _) in runs.items():
    for a in ann.values():
        for c in a['containers']: voc[(c['kind'], c['app'], cls(c))] += 1
print('APP VOCAB', voc.most_common(60))
# terminal boxes per refs
r1, r2 = runs[f'{span}-s100-r1'][0], runs[f'{span}-s100-r2'][0]
term = set()
for f, a in r1.items():
    for b in a['targets']:
        if cls(cont_of(a, b)) == 'term' and f in r2 and cls(cont_of(r2[f], b)) == 'term': term.add((f, b))
disagree_refs = sum(1 for f, a in r1.items() for b in a['targets'] if (cls(cont_of(a, b)) == 'term') != (cls(cont_of(r2[f], b)) == 'term'))
print('terminal targets (both refs agree):', len(term), 'refs disagree on', disagree_refs)
print('\nrun | term boxes in a terminal window | term frames with a terminal window listed | false-terminal | records with 0 windows | tooltip149 | tooltip151')
for n, (ann, boxes) in runs.items():
    ok = sum(1 for f, b in term if f in ann and cls(cont_of(ann[f], b)) == 'term')
    miss = [(f, b, cls(cont_of(ann[f], b))) for f, b in sorted(term) if f in ann and cls(cont_of(ann[f], b)) != 'term']
    false = [(f, b) for f, a in ann.items() for b in a['targets'] if cls(cont_of(a, b)) == 'term' and (f, b) not in term and cls(cont_of(r1[f], b)) != 'term' and cls(cont_of(r2[f], b)) != 'term']
    tf = sorted({f for f, b in term}); listed = sum(1 for f in tf if any(cls(c) == 'term' for c in ann[f]['containers']))
    tt = []
    for f, b in ((149, 'b13'), (151, 'b116')):
        if f in ann and b in ann[f]['targets']:
            c = cont_of(ann[f], b); pops = [x['name'] for x in ann[f]['containers'] if x['kind'] == 'popup']
            tt.append(f"{'OWN-POPUP' if c and c['kind']=='popup' else 'in:'+cls(c)} (popups listed: {pops})")
        else: tt.append('-')
    print(f"{n} | {ok}/{len(term)} | {listed}/{len(tf)} | {len(false)} | {sum(1 for a in ann.values() if not a['containers'])} | {tt[0]} | {tt[1]}")
    if miss: print('      missed term boxes:', [(f, b, k, boxes[f][b]['text'][:30]) for f, b, k in miss][:12])
    if false: print('      false term boxes:', [(f, b, boxes[f][b]['text'][:30]) for f, b in false][:12])
# live lines
print('\nLIVE LINES')
LINES = {'smoke': [(155, None)], 'span2': [(155, None), (161, None), (165, None), (166, None), (172, None), (175, None), (178, None), (179, None), (185, 'last')]}[span]
for f, _ in LINES:
    ann, boxes = runs[names[0]]
    cands = [b for b in ann[f]['targets'] if boxes[f][b]['text'].startswith('PS')]
    if not cands: print(f, 'no PS target'); continue
    b = max(cands, key=lambda x: boxes[f][x]['bbox'][1])
    print(f'F{f} {b} OCR: {boxes[f][b]["text"]!r}')
    for n, (ann, boxes) in runs.items():
        t = next((x['text'] for x in (ann[f]['texts'] or []) if x['box'] == b), None)
        print(f'    {n}: {t!r}')
# descriptions
print('\nDESCRIPTIONS mentioning boxes/targets')
pat = re.compile(r"\bb\d{1,3}\b|\bbox(?:es)?\s+\d|\bnumbered\b|\boverlay\b|\bmagenta\b|\byellow (?:tag|label)|\btargets? (?:box|were|was|is|are|list)|no targets|\bannotat|image [12]\b|\bcoordinat|\brectangle|\bx0\b|\bthe list\b|\blisted\b|\bbox ids?\b|\bthe targets?\b|\bOCR\b|\bbounding\b|\d{2,4},\d{2,4},\d{2,4}", re.I)
for n, (ann, boxes) in runs.items():
    hits = [(f, a['description'][max(0,m.start()-40):m.end()+40]) for f, a in ann.items() if a['description'] for m in [pat.search(a['description'])] if m]
    nodesc = [f for f, a in ann.items() if not a['description']]
    print(n, 'hits', len(hits), hits[:8], 'no-description', nodesc)
