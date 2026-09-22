"""How each returned rectangle matched a box (recomputed with snap_rect from the call cache): exact / overlap / nearest / dropped,
per coords run; inexact rectangles and what they look like. Usage: rects.py [p10|p10full] [-v]"""
import json, sys, glob
from collections import Counter
from pathlib import Path
from scry.run import Run
from scry.annotate.proposal import snap_rect, _overlap
from scry.track.pixels import margin_px
phase = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'p10'
verbose = '-v' in sys.argv
ROOT = Path('<repo>/runs/eval') / phase
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
print('run | calls matched to frames | rectangles | exact | overlap (IoU>=0.5 / <0.5) | nearest | dropped | inexact by field | frames with an inexact rect | rect not 4 ints')
for d in sorted(ROOT.iterdir()):
    if not (d / 'annotations.jsonl').exists(): continue
    cfg = json.load(open(d / 'config.json'))
    if cfg['annotate'].get('reference') != 'coords': continue
    run = Run(d); frames = {f.sha256: f for f in run.load_frames()}; boxes = {fb.frame: fb for fb in run.load_boxes()}
    margin = cfg['track']['margin']
    kinds = Counter(); byfield = Counter(); fr = set(); bad = 0; n = 0; nrect = 0; ex = []
    for c in glob.glob(str(d / 'cache' / '*.json')):
        e = json.load(open(c))
        if e['request'].get('stage') != 'annotate' or e['response'].get('parsed') is None: continue
        f = frames.get(e['request']['input_hashes'][0])
        if f is None: continue
        n += 1; fb = boxes[f.frame].boxes; m = margin_px(fb, [], margin); byrect = {tuple(b.bbox): b for b in fb}
        for field, r in rects_of(e['response']['parsed']):
            nrect += 1
            if not (isinstance(r, list) and len(r) == 4 and all(isinstance(v, int) for v in r)): bad += 1; kinds['dropped'] += 1; byfield[field] += 1; fr.add(f.frame); continue
            if tuple(r) in byrect: kinds['exact'] += 1; continue
            byfield[field] += 1; fr.add(f.frame)
            bid = snap_rect(r, fb, m)
            if bid is None: kinds['dropped'] += 1; ex.append((f.frame, field, r, None, None)); continue
            b = next(x for x in fb if x.id == bid)
            ov = _overlap(r, b.bbox)
            if ov > 0:
                area = lambda q: (q[2] - q[0]) * (q[3] - q[1])
                iou = ov / (area(r) + area(b.bbox) - ov)
                kinds['overlap>=0.5' if iou >= 0.5 else 'overlap<0.5'] += 1; ex.append((f.frame, field, r, b.bbox, round(iou, 2), b.text[:30]))
            else: kinds['nearest'] += 1; ex.append((f.frame, field, r, b.bbox, 'nearest', b.text[:30]))
    print(f"{d.name} | {n} | {nrect} | {kinds['exact']} | {kinds['overlap>=0.5']} / {kinds['overlap<0.5']} | {kinds['nearest']} | {kinds['dropped']} | {dict(byfield)} | {sorted(fr)} | {bad}")
    if verbose:
        for x in ex: print('     ', x)
