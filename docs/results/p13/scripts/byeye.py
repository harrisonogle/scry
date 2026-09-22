"""By eye, transcribing runs, P3 overlay (s) and P13 coords (ct) side by side at every scale:
(1) the live prompt lines: frame 155 (both spans; truth a bare `a`), span2 frames 161, 165, 166, 172, 175, 178, 179, 185
    (P3 spec.py's rule: the lowest target whose OCR starts with 'PS');
(2) descriptions of frames 150, 151, 155 at 0.3 and 0.2 (and 1.0 for reference), with counts of mentions of
    rectangle / coordinate / 'the target' / illegible / overlay across all descriptions of every scale.
Usage: byeye.py"""
import json, re
from collections import Counter
from pathlib import Path
E = Path('<repo>/runs/eval')
SC = ['100', '067', '050', '040', '030', '025', '020']
def load(phase, n):
    d = E / phase / n
    if not (d / 'annotations.jsonl').exists(): return None
    ann = {}; boxes = {}
    for l in open(d / 'annotations.jsonl'):
        a = json.loads(l); ann[a['frame']] = a
    for l in open(d / 'boxes.jsonl'):
        fb = json.loads(l); boxes[fb['frame']] = {b['id']: b for b in fb['boxes']}
    return ann, boxes
runs = {}
for span in ('smoke', 'span2'):
    for sc in SC:
        for phase, pre in (('p3', 's'), ('p13', 'ct')):
            for r in (1, 2):
                n = f'{span}-{pre}{sc}-r{r}'; x = load(phase, n)
                if x: runs[n] = x
LINES = {'smoke': [155], 'span2': [155, 161, 165, 166, 172, 175, 178, 179, 185]}
print('== LIVE PROMPT LINES (the lowest PS target on the frame; OCR = what the tracker read; then each run\'s second reading, "" = empty, None = no reading)')
for span, frames in LINES.items():
    for f in frames:
        ann, boxes = next(v for k, v in runs.items() if k.startswith(span))
        cands = [b for b in ann[f]['targets'] if boxes[f][b]['text'].startswith('PS')]
        if not cands: print(f'{span} F{f}: no PS target'); continue
        b = max(cands, key=lambda x: boxes[f][x]['bbox'][1])
        print(f'\n{span} F{f} {b} OCR: {boxes[f][b]["text"]!r}')
        for sc in SC:
            row = []
            for pre in ('s', 'ct'):
                for r in (1, 2):
                    n = f'{span}-{pre}{sc}-r{r}'
                    if n not in runs: row.append(f'{pre}{sc}-r{r}: MISSING'); continue
                    a = runs[n][0][f]
                    t = next((x['text'] for x in (a['texts'] or []) if x['box'] == b), None)
                    row.append(f'{pre}-r{r}: {t!r}')
            print(f'  {sc}: overlay ' + ' | '.join(row[:2]) + '   coords ' + ' | '.join(row[2:]))
print('\n\n== MENTIONS in descriptions, per run (all frames): rectangle | coordinate | "the target"/"targets" | illegible/unreadable/too small/low resolution/blurry | overlay/tag/label(s) | box ids like b12 | no description')
pats = {'rect': re.compile(r'\brectangle', re.I), 'coord': re.compile(r'\bcoordinat|\bpixel', re.I), 'target': re.compile(r'\bthe targets?\b|\btargets?\b', re.I),
        'illegible': re.compile(r'illegible|unreadable|not readable|cannot be read|can\'t be read|too small|low[- ]resolution|blurr|hard to read|difficult to read|not legible|indistinct', re.I),
        'overlay': re.compile(r'\boverlay|\bmagenta|\byellow (?:tag|label)|\bnumbered\b|\btags?\b', re.I), 'boxid': re.compile(r'\bb\d{1,3}\b')}
for n, (ann, boxes) in runs.items():
    c = Counter(); nod = []
    for f, a in ann.items():
        d = a.get('description') or ''
        if not d: nod.append(f); continue
        for k, p in pats.items():
            if p.search(d): c[k] += 1
    print(f"{n} | {c['rect']} | {c['coord']} | {c['target']} | {c['illegible']} | {c['overlay']} | {c['boxid']} | no-desc {nod}")
print('\n\n== DESCRIPTIONS at 1.0, 0.3, 0.2 for frames 150, 151, 155 (smoke), coords then overlay')
for sc in ('100', '030', '020'):
    for f in (150, 151, 155):
        for pre in ('ct', 's'):
            for r in (1, 2):
                n = f'smoke-{pre}{sc}-r{r}'
                if n not in runs: continue
                a = runs[n][0][f]
                print(f"--- {n} F{f} ({len(a['targets'])} targets)\n{a.get('description')}\n")
print('\n\n== DESCRIPTIONS span2 at 0.3 and 0.2 for the command frames 161, 166, 172, 175 (coords only)')
for sc in ('030', '020'):
    for f in (161, 166, 172, 175):
        for r in (1, 2):
            n = f'span2-ct{sc}-r{r}'
            if n not in runs: continue
            a = runs[n][0][f]
            print(f"--- {n} F{f}\n{a.get('description')}\n")
