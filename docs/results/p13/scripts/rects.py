"""Rectangle echo exactness per P13 run (P10's rects.py with the scale): every rectangle the model returned (assign,
unassigned, runs, pairs, records, texts), recomputed from the call cache against the listed boxes in the scaled space:
exact / overlap (IoU >= .5, < .5) / nearest / dropped; whether drift (off by 1-2 px) appears at small scales.
Usage: rects.py [-v]"""
import json, sys, glob
from collections import Counter
from pathlib import Path
from scry.run import Run
from scry.annotate.proposal import snap_rect, _overlap
from scry.overlay import scale_box
from scry.track.pixels import margin_px
verbose = '-v' in sys.argv
ROOT = Path('<repo>/runs/eval/p13')
def rects_of(p):
    out = []
    for a in p['assign']: out.append(('assign', a['rect']))
    for r in p['unassigned']: out.append(('unassigned', r))
    for r in p['runs']:
        for b in r['boxes']: out.append(('run', b))
    for pr in p['pairs']:
        for b in pr['key'] + pr['value']: out.append(('pair', b))
    for rec in p['records']:
        for cell in rec['members'] + [rec['header']]:
            for b in cell: out.append(('record', b))
    for t in p.get('texts', []) or []: out.append(('text', t['rect']))
    return out
print('run | scale | calls | rectangles | exact | exact % | overlap IoU>=.5 / <.5 | nearest | dropped | inexact by field | frames with an inexact rect | not 4 ints | max |dx| among inexact')
tot = Counter(); per_scale = {}
for d in sorted(ROOT.iterdir(), key=lambda p: (p.name.split('-')[1], p.name)):
    if not (d / 'annotations.jsonl').exists(): continue
    cfg = json.load(open(d / 'config.json'))
    if cfg['annotate'].get('reference') != 'coords': continue
    scale = cfg['annotate']['scale']
    run = Run(d); frames = {f.sha256: f for f in run.load_frames()}; boxes = {fb.frame: fb for fb in run.load_boxes()}
    margin = cfg['track']['margin']
    kinds = Counter(); byfield = Counter(); fr = set(); bad = 0; n = 0; nrect = 0; ex = []; maxd = 0
    for c in glob.glob(str(d / 'cache' / '*.json')):
        e = json.load(open(c))
        if e['request'].get('stage') != 'annotate' or e['response'].get('parsed') is None: continue
        f = frames.get(e['request']['input_hashes'][0])
        if f is None: continue
        n += 1; fb = boxes[f.frame].boxes; m = margin_px(fb, [], margin)
        byrect = {tuple(scale_box(b.bbox, scale)): b for b in fb}
        for field, r in rects_of(e['response']['parsed']):
            nrect += 1
            if not (isinstance(r, list) and len(r) == 4 and all(isinstance(v, int) for v in r)): bad += 1; kinds['dropped'] += 1; byfield[field] += 1; fr.add(f.frame); continue
            if tuple(r) in byrect: kinds['exact'] += 1; continue
            byfield[field] += 1; fr.add(f.frame)
            bid = snap_rect(r, fb, m, scale)
            if bid is None: kinds['dropped'] += 1; ex.append((f.frame, field, r, None, 'dropped')); continue
            b = next(x for x in fb if x.id == bid); sb = scale_box(b.bbox, scale)
            maxd = max(maxd, max(abs(r[i] - sb[i]) for i in range(4)))
            ov = _overlap(r, sb)
            if ov > 0:
                area = lambda q: (q[2] - q[0]) * (q[3] - q[1])
                iou = ov / (area(r) + area(sb) - ov)
                kinds['overlap>=0.5' if iou >= 0.5 else 'overlap<0.5'] += 1; ex.append((f.frame, field, r, sb, round(iou, 2), b.text[:30]))
            else: kinds['nearest'] += 1; ex.append((f.frame, field, r, sb, 'nearest', b.text[:30]))
    tot.update(kinds); tot['rects'] += nrect
    k = (d.name.split('-')[1][:2], scale); ps = per_scale.setdefault(k, Counter()); ps.update(kinds); ps['rects'] += nrect
    print(f"{d.name} | {scale} | {n} | {nrect} | {kinds['exact']} | {100 * kinds['exact'] / max(1, nrect):.2f} | {kinds['overlap>=0.5']} / {kinds['overlap<0.5']} | {kinds['nearest']} | {kinds['dropped']} | {dict(byfield)} | {sorted(fr)} | {bad} | {maxd}")
    if verbose or ex:
        for x in ex[:12]: print('     ', x)
print('\n== per mode x scale (both spans, both repeats)')
for k in sorted(per_scale, key=lambda k: (k[0], -k[1])):
    ps = per_scale[k]
    print(f"{k[0]} {k[1]} | rects {ps['rects']} | exact {ps['exact']} ({100 * ps['exact'] / max(1, ps['rects']):.2f}%) | overlap {ps['overlap>=0.5']}/{ps['overlap<0.5']} | nearest {ps['nearest']} | dropped {ps['dropped']}")
print('TOTAL', dict(tot), f"exact {100 * tot['exact'] / max(1, tot['rects']):.3f}%")
