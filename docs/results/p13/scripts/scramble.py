"""Whole-frame scrambles by P5's measures, per run, P13 (ct and cg) beside P3 (s) at the same scale:
neigh.py: second readings that are another box's text (ratio>=90 to another box, <60 to own), where that box is
  (reading-order offset, beside/above/below), icon glyphs, swapped pairs, longest shift chain;
loose.py: the looser rule (<90 to own, >=90 to another), line above/below | beside | elsewhere;
offrow.py: pair links whose key and value share no row (dy>12), run links with a jump (dy>12 or dx>300);
plus containers: frames where >=4 boxes of one window (per the s100/ids100 refs) are given to a window of another class.
Usage: scramble.py <span>"""
import json, sys, re
from collections import Counter
from pathlib import Path
from rapidfuzz import fuzz
from scry.run import Run
from scry.annotate.join import agreement
from scry.textdiff import norm
E = Path('/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval')
span = sys.argv[1]; verbose = '-v' in sys.argv
SC = ['100', '067', '050', '040', '030', '025', '020']
names = []
for sc in SC:
    for phase, pre in (('p3', 's'), ('p13', 'ct'), ('p13', 'cg')):
        for r in (1, 2):
            n = f'{span}-{pre}{sc}-r{r}'
            if (E / phase / n / 'annotations.jsonl').exists(): names.append((phase, n))
runs = {}
for phase, n in names:
    run = Run(E / phase / n); runs[n] = ({a.frame: a for a in run.load_annotations()}, {fb.frame: fb for fb in run.load_boxes()})
def gap(a, b): return max(0, max(a[0], b[0]) - min(a[2], b[2])), max(0, max(a[1], b[1]) - min(a[3], b[3]))
def relation(a, b):
    dx, dy = gap(a, b)
    if dy == 0 and dx >= 0: return 'beside', dx, dy
    if dx == 0: return ('above' if b[1] < a[1] else 'below'), dx, dy
    return 'diagonal', dx, dy
print("== NEIGH (P5 neigh.py): run | targets read (non-empty) | disagree with own OCR | is ANOTHER box's text | of which own box is an icon glyph | adjacent in reading order (|d|<=1) | |d|<=3 | far (|d|>3) | swapped pairs | longest shift chain | frames")
for n, (ann, boxes) in runs.items():
    if all(a.texts is None for a in ann.values()): continue
    nread = ndis = 0; hits = []
    for f, a in ann.items():
        if a.texts is None: continue
        fb = boxes[f].boxes; order = {b.id: i for i, b in enumerate(fb)}; bb = {b.id: b for b in fb}
        for t in a.texts:
            if t.box not in bb or not t.text.strip(): continue
            nread += 1; o = bb[t.box].text
            if agreement(o, t.text): continue
            ndis += 1; b_ = norm(t.text).lower()
            if len(b_) < 3: continue
            if fuzz.ratio(norm(o).lower(), b_) >= 60 or fuzz.partial_ratio(norm(o).lower(), b_) >= 80: continue
            cands = [(fuzz.ratio(norm(x.text).lower(), b_), x.id) for x in fb if x.id != t.box]
            cands = [c for c in cands if c[0] >= 90]
            if not cands: continue
            oid = min(cands, key=lambda c: abs(order[c[1]] - order[t.box]))[1]
            kind, dx, dy = relation(bb[t.box].bbox, bb[oid].bbox)
            icon = not re.search(r'[A-Za-z]{3,}', o)
            hits.append(dict(frame=f, box=t.box, own=o, read=t.text, other=oid, d=order[oid] - order[t.box], rel=kind, dx=dx, dy=dy, icon=icon))
    hs = {(h['frame'], h['box']): h for h in hits}
    swaps = sum(1 for h in hits if (h['frame'], h['other']) in hs and hs[(h['frame'], h['other'])]['other'] == h['box']) // 2
    longest = 0
    for h in hits:
        seen = {h['box']}; cur = h; L = 1
        while (cur['frame'], cur['other']) in hs and cur['other'] not in seen:
            cur = hs[(cur['frame'], cur['other'])]; seen.add(cur['box']); L += 1
        longest = max(longest, L)
    txt = [h for h in hits if not h['icon']]
    print(f"{n} | {nread} | {ndis} | {len(hits)} | {sum(h['icon'] for h in hits)} | {sum(abs(h['d'])<=1 for h in txt)} | {sum(abs(h['d'])<=3 for h in txt)} | {sum(abs(h['d'])>3 for h in txt)} | {swaps} | {longest} | {dict(Counter(h['frame'] for h in hits))}")
    if verbose:
        for h in hits[:20]: print('     ', {k: (v[:40] if isinstance(v, str) else v) for k, v in h.items()})
print("\n== LOOSE (P5 loose.py): run | readings | another box's text (loose) | own is icon glyph | other box: line above/below | beside | elsewhere | frames")
for n, (ann, boxes) in runs.items():
    if all(a.texts is None for a in ann.values()): continue
    nread = 0; hits = []
    for f, a in ann.items():
        if a.texts is None: continue
        fb = boxes[f].boxes; bb = {b.id: b for b in fb}
        for t in a.texts:
            if t.box not in bb or not t.text.strip(): continue
            nread += 1; o = bb[t.box].text
            if agreement(o, t.text): continue
            b_ = norm(t.text).lower()
            if len(b_) < 3 or fuzz.ratio(norm(o).lower(), b_) >= 90: continue
            c = [(fuzz.ratio(norm(x.text).lower(), b_), x.id) for x in fb if x.id != t.box]
            c = [x for x in c if x[0] >= 90]
            if not c: continue
            oid = min(c, key=lambda x: sum(gap(bb[t.box].bbox, bb[x[1]].bbox)))[1]
            dx, dy = gap(bb[t.box].bbox, bb[oid].bbox)
            where = 'line' if (dx == 0 and dy <= 12) else 'beside' if dy == 0 else 'elsewhere'
            hits.append((f, t.box, o[:50], t.text[:50], oid, dx, dy, where, not re.search(r'[A-Za-z]{3,}', o)))
    w = Counter(h[7] for h in hits if not h[8])
    print(f"{n} | {nread} | {len(hits)} | {sum(h[8] for h in hits)} | {w['line']} | {w['beside']} | {w['elsewhere']} | {dict(Counter(h[0] for h in hits))}")
print('\n== OFFROW (P5 offrow.py): run | pair links | off-row pairs (dy>12) | frames | runs with a jump (dy>12 or dx>300) | max pair gap px')
for n, (ann, boxes) in runs.items():
    tot = 0; off = []; rj = []; maxg = 0
    for f, a in ann.items():
        bb = {b.id: b for b in boxes[f].boxes}
        for l in a.links:
            if l.kind == 'pair':
                tot += 1
                g = min((gap(bb[k].bbox, bb[v].bbox) for k in l.key for v in l.value if k in bb and v in bb), key=lambda t: t[1] * 10 + t[0], default=(0, 0))
                maxg = max(maxg, sum(g))
                if g[1] > 12: off.append((f, g, ' + '.join(bb[k].text[:25] for k in l.key), '=>', ' + '.join(bb[v].text[:25] for v in l.value)))
            elif l.kind == 'run':
                gs = [gap(bb[x].bbox, bb[y].bbox) for x, y in zip(l.boxes, l.boxes[1:]) if x in bb and y in bb]
                if any(g[1] > 12 or g[0] > 300 for g in gs): rj.append((f, gs, ' | '.join(bb[x].text[:25] for x in l.boxes)))
    print(f"{n} | {tot} | {len(off)} | {dict(Counter(o[0] for o in off))} | {len(rj)} | {maxg}")
    if verbose:
        for o in off[:10]: print('      OFFROW', o)
        for o in rj[:10]: print('      RUNJUMP', o)
# container scrambles: against the s100 refs (P3) for the window class of each target
def cls(c):
    if c is None: return 'none'
    if c.kind == 'popup': return 'P'
    s = (c.app + ' ' + c.name).lower()
    if 'powershell' in s or 'terminal' in s or 'pwsh' in s or 'command' in s: return 'term'
    if 'edge' in s or 'browser' in s or 'chrome' in s or 'azure' in s: return 'browser'
    if 'taskbar' in s or 'windows' in s or 'explorer' in s or 'desktop' in s: return 'os'
    return 'other'
def cont_of(a, box):
    cid = next((x.container for x in a.assign if x.box == box), None)
    return next((c for c in a.containers if c.id == cid), None)
ref1, ref2 = runs[f'{span}-s100-r1'][0], runs[f'{span}-s100-r2'][0]
print('\n== CONTAINER SCRAMBLES (window class per target where both s100 refs agree; frames with >=4 targets moved to another class): run | targets moved | frames (count, moved to)')
for n, (ann, boxes) in runs.items():
    moved = []
    for f, a in ann.items():
        for b in a.targets:
            k1, k2 = cls(cont_of(ref1[f], b)), cls(cont_of(ref2[f], b))
            if k1 != k2 or k1 in ('P', 'none'): continue
            k = cls(cont_of(a, b))
            if k != k1 and k != 'P': moved.append((f, b, k1, k))
    byf = Counter(m[0] for m in moved)
    big = {f: (c, dict(Counter((m[2], m[3]) for m in moved if m[0] == f))) for f, c in byf.items() if c >= 4}
    print(f"{n} | {len(moved)} | {big}")
