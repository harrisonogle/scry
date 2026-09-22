"""Id confusion, measured on the stored records (no model): second readings that are another box's text, where that box
is (reading-order offset, geometry), swapped pairs, shift chains; links not in either P3 s100 reference and how far apart
their boxes are. Usage: neigh.py <span> [-v]"""
import json, sys, re
from collections import Counter, defaultdict
from pathlib import Path
from rapidfuzz import fuzz
from scry.run import Run
from scry.annotate.join import agreement
from scry.textdiff import norm
BASE = Path('<repo>/runs/eval')
SCALES = ['s100', 's067', 's050', 'd100', 'd067', 'd050']
span = sys.argv[1]; verbose = '-v' in sys.argv
def rootof(n): return BASE / ('p5' if '-d' in n else 'p3')
def gap(a, b):
    dx = max(0, max(a[0], b[0]) - min(a[2], b[2])); dy = max(0, max(a[1], b[1]) - min(a[3], b[3]))
    return dx, dy
def relation(a, b, allb):
    """where b lies relative to a: same row / column neighbour, and whether any other box lies between"""
    dx, dy = gap(a, b)
    if dy == 0 and dx >= 0: kind = 'beside'
    elif dx == 0: kind = 'above' if b[1] < a[1] else 'below'
    else: kind = 'diagonal'
    return kind, dx, dy
runs = {}
for s in SCALES:
    for r in (1, 2):
        n = f'{span}-{s}-r{r}'
        p = rootof(n) / n
        if (p / 'annotations.jsonl').exists() and 'annotate' in json.load(open(p / 'manifest.json'))['stages']:
            run = Run(p); runs[n] = ({a.frame: a for a in run.load_annotations()}, {fb.frame: fb for fb in run.load_boxes()})
print('run | targets read (non-empty) | disagree with own OCR | is ANOTHER box\'s text (ratio>=90, any own-similarity) | of which: own box is an icon glyph | adjacent in reading order (|d|<=1) | |d|<=3 | far (|d|>3) | swapped pairs | longest shift chain')
detail = {}
for n, (ann, boxes) in runs.items():
    nread = ndis = 0; hits = []
    for f, a in ann.items():
        if a.texts is None: continue
        fb = boxes[f].boxes; order = {b.id: i for i, b in enumerate(fb)}; bb = {b.id: b for b in fb}
        for t in a.texts:
            if t.box not in bb or not t.text.strip(): continue
            nread += 1
            o = bb[t.box].text
            if agreement(o, t.text): continue
            ndis += 1
            b_ = norm(t.text).lower()
            if len(b_) < 3: continue
            if fuzz.ratio(norm(o).lower(), b_) >= 60 or fuzz.partial_ratio(norm(o).lower(), b_) >= 80: continue  # P3's rule: close to its own OCR is a misreading, not another box
            cands = [(fuzz.ratio(norm(x.text).lower(), b_), x.id) for x in fb if x.id != t.box]
            cands = [c for c in cands if c[0] >= 90]
            if not cands: continue
            # nearest candidate in reading order
            oid = min(cands, key=lambda c: abs(order[c[1]] - order[t.box]))[1]
            kind, dx, dy = relation(bb[t.box].bbox, bb[oid].bbox, fb)
            icon = not re.search(r'[A-Za-z]{3,}', o)
            hits.append(dict(frame=f, box=t.box, own=o, read=t.text, other=oid, d=order[oid] - order[t.box], rel=kind, dx=dx, dy=dy, icon=icon))
    hs = {(h['frame'], h['box']): h for h in hits}
    swaps = sum(1 for h in hits if (h['frame'], h['other']) in hs and hs[(h['frame'], h['other'])]['other'] == h['box']) // 2
    # shift chain: follow box -> other while other is itself a hit
    longest = 0
    for h in hits:
        seen = {h['box']}; cur = h; L = 1
        while (cur['frame'], cur['other']) in hs and cur['other'] not in seen:
            cur = hs[(cur['frame'], cur['other'])]; seen.add(cur['box']); L += 1
        longest = max(longest, L)
    txt = [h for h in hits if not h['icon']]
    print(f"{n} | {nread} | {ndis} | {len(hits)} | {sum(h['icon'] for h in hits)} | {sum(abs(h['d'])<=1 for h in txt)} | {sum(abs(h['d'])<=3 for h in txt)} | {sum(abs(h['d'])>3 for h in txt)} | {swaps} | {longest}  frames={dict(Counter(h['frame'] for h in hits))}")
    detail[n] = hits
    if verbose:
        for h in hits: print('     ', h)
json.dump(detail, open(f'<scratch>/p5/neigh-{span}.json', 'w'), indent=0)

# links: those in neither s100 reference; distance between the linked boxes
def linkitems(ann, boxes):
    out = []
    for f, a in ann.items():
        bb = {b.id: b for b in boxes[f].boxes}
        for l in a.links:
            if l.kind == 'pair':
                ids = list(l.key) + list(l.value); key = (f, 'pair', frozenset(l.key), frozenset(l.value))
                g = min((gap(bb[k].bbox, bb[v].bbox) for k in l.key for v in l.value if k in bb and v in bb), key=lambda t: t[0] + t[1], default=(0, 0))
            elif l.kind == 'run':
                key = (f, 'run', tuple(l.boxes)); ids = list(l.boxes)
                gs = [gap(bb[x].bbox, bb[y].bbox) for x, y in zip(l.boxes, l.boxes[1:]) if x in bb and y in bb]
                g = max(gs, key=lambda t: t[0] + t[1], default=(0, 0))
            else: continue
            out.append((key, g, ' + '.join(bb[i].text[:28] for i in ids if i in bb)))
    return out
ref = set()
for r in (1, 2):
    ann, boxes = runs[f'{span}-s100-r{r}']
    ref |= {k for k, g, t in linkitems(ann, boxes)}
print('\nLINKS: run | pair links | pairs in neither s100 ref | of those, gap > 150 px (dx+dy) | max pair gap px | run links | runs in neither ref | max gap between consecutive run boxes')
for n, (ann, boxes) in runs.items():
    it = linkitems(ann, boxes)
    P = [x for x in it if x[0][1] == 'pair']; Rn = [x for x in it if x[0][1] == 'run']
    newp = [x for x in P if x[0] not in ref]; newr = [x for x in Rn if x[0] not in ref]
    far = [x for x in newp if sum(x[1]) > 150]
    print(f"{n} | {len(P)} | {len(newp)} | {len(far)} | {max((sum(x[1]) for x in P), default=0)} | {len(Rn)} | {len(newr)} | {max((sum(x[1]) for x in Rn), default=0)}")
    if verbose:
        for k, g, t in newp: print('      NEWPAIR', k[0], g, t)
        for k, g, t in newr: print('      NEWRUN', k[0], g, t)
