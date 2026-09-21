"""P3's qual.py + summ.py, adapted: arm A (P3) and arm D (P5) rows against the same reference (P3's two s100 repeats).
Usage: qual.py <span>.  Functions container_diff, linkset, links_by_kind, readings, appclass are P3's, unchanged."""
import json, sys, re, hashlib
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from rapidfuzz import fuzz
from scry.run import Run
from scry.annotate.join import agreement
from scry.textdiff import norm
from scry.schemas import link_members, parse_box_ref

BASE = Path('/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval')
SETS = [('p3', ['s100']), ('p7', ['sonnet5'])]
OUT = Path('/private/tmp/claude-501/-Users-harrisonogle-src-harrisonogle-agentic-escort/00000000-0000-0000-0000-000000000000/scratchpad/p7')
span = sys.argv[1]

class R:
    def __init__(self, root, name):
        self.name = name
        self.run = Run(root / name)
        self.ann = {a.frame: a for a in self.run.load_annotations()}
        self.boxes = {fb.frame: fb for fb in self.run.load_boxes()}
        self.ocr = {(f, b.id): b.text for f, fb in self.boxes.items() for b in fb.boxes}
        self.labels = self.run.load_labels()
        self.boxhash = hashlib.sha256((root / name / 'boxes.jsonl').read_bytes()).hexdigest()[:10]
        self.lifehash = hashlib.sha256((root / name / 'lifetimes.jsonl').read_bytes()).hexdigest()[:10]

runs = {}
for phase, scales in SETS:
    for s in scales:
        for r in (1, 2):
            n = f'{span}-{s}-r{r}'
            if (BASE / phase / n / 'annotations.jsonl').exists() and 'annotate' in json.load(open(BASE / phase / n / 'manifest.json'))['stages']:
                runs[n] = R(BASE / phase, n)
print('runs loaded', len(runs), 'box hashes', Counter(r.boxhash for r in runs.values()), 'life hashes', Counter(r.lifehash for r in runs.values()))
print('targets identical across runs:', len({json.dumps({f: a.targets for f, a in r.ann.items()}, sort_keys=True) for r in runs.values()}) == 1)
print('records with error:', {n: [f for f, a in r.ann.items() if a.error] for n, r in runs.items() if any(a.error for a in r.ann.values())})

def assign_map(a):
    return {x.box: x.container for x in a.assign}

def appclass(c):
    if c is None: return 'none'
    s = (c.app + ' ' + c.name).lower()
    k = 'P:' if c.kind == 'popup' else 'W:'
    if 'powershell' in s or 'terminal' in s or 'pwsh' in s: return k + 'term'
    if 'edge' in s or 'browser' in s or 'chrome' in s or 'azure' in s: return k + 'browser'
    if 'taskbar' in s or 'windows' in s or 'explorer' in s or 'shell' in s or 'desktop' in s: return k + 'os'
    return k + 'other'

def container_diff(x, ref):
    diff = set(); tot = 0
    for f, ra in ref.ann.items():
        xa = x.ann.get(f)
        rm = assign_map(ra); tot += len(ra.targets)
        if xa is None or xa.error:
            diff |= {(f, b) for b in ra.targets}; continue
        xm = assign_map(xa)
        xc = sorted({v for b, v in xm.items() if b in ra.targets}); rc = sorted({v for b, v in rm.items() if b in ra.targets})
        if not xc or not rc:
            diff |= {(f, b) for b in ra.targets if xm.get(b) != rm.get(b) or xm.get(b) is None}; continue
        M = np.zeros((len(xc), len(rc)))
        for b in ra.targets:
            if b in xm and b in rm: M[xc.index(xm[b]), rc.index(rm[b])] += 1
        ri, ci = linear_sum_assignment(-M)
        match = {xc[i]: rc[j] for i, j in zip(ri, ci) if M[i, j] > 0}
        xcon = {c.id: c for c in xa.containers}; rcon = {c.id: c for c in ra.containers}
        for b in ra.targets:
            xb, rb = xm.get(b), rm.get(b)
            if xb is None and rb is None: continue
            if xb is None or rb is None or match.get(xb) != rb: diff.add((f, b)); continue
            if appclass(xcon.get(xb)) != appclass(rcon.get(rb)): diff.add((f, b))
    return diff, tot

def links_by_kind(x):
    c = Counter()
    for a in x.ann.values():
        for l in a.links: c[l.kind] += 1
    return c

def linkset(x, kind):
    out = set()
    for f, a in x.ann.items():
        for l in a.links:
            if l.kind != kind: continue
            if kind == 'pair': out.add((f, frozenset(l.key), frozenset(l.value)))
            elif kind == 'run': out.add((f, tuple(l.boxes)))
            else: out.add((f, tuple(tuple(c) for c in l.members)))
    return out

def readings(x):
    agree = tot = empty_real = wrong = 0; empties = []; wrongs = []; offs = []
    for f, a in x.ann.items():
        if a.texts is None: continue
        frame_ocr = {b.id: b.text for b in x.boxes[f].boxes}
        for t in a.texts:
            o = frame_ocr.get(t.box)
            if o is None: continue
            if not t.text.strip():
                if len(re.findall(r'[A-Za-z]{3,}', o)) >= 1:
                    empty_real += 1; empties.append((f, t.box, o))
                continue
            tot += 1
            if agreement(o, t.text): agree += 1; continue
            a_, b_ = norm(o).lower(), norm(t.text).lower()
            if fuzz.ratio(a_, b_) < 60 and fuzz.partial_ratio(a_, b_) < 80 and len(b_) >= 3:
                other = [b for b, ot in frame_ocr.items() if b != t.box and fuzz.ratio(norm(ot).lower(), b_) >= 90]
                if other: wrong += 1; wrongs.append((f, t.box, o, t.text, other[:2]))
                else: offs.append((f, t.box, o, t.text))
    return agree, tot, empty_real, wrong, empties, wrongs, offs

refs = [runs[f'{span}-s100-r1'], runs[f'{span}-s100-r2']]
print('\nPER RUN: run | cont/rec mean | popups | unassigned | contdiff% vs r1,r2 | links run/pair/record | relinked | pairs-repro% vs r1,r2 | runs-repro% | agree/tot % | empty_real | wrongbox | missed')
store = {}
for n, x in runs.items():
    cont = np.mean([len(a.containers) for a in x.ann.values()])
    pops = sum(1 for a in x.ann.values() for c in a.containers if c.kind == 'popup')
    unas = sum(len(a.unassigned) for a in x.ann.values())
    cds = []; prs = []; rrs = []
    for ref in refs:
        if ref is x: cds.append(None); prs.append(None); rrs.append(None); continue
        d, tot = container_diff(x, ref); cds.append(100 * len(d) / tot)
        rp = linkset(ref, 'pair'); prs.append(100 * len(rp & linkset(x, 'pair')) / max(1, len(rp)))
        rr = linkset(ref, 'run'); rrs.append(100 * len(rr & linkset(x, 'run')) / max(1, len(rr)))
    lk = links_by_kind(x)
    ag, tot, er, wr, empties, wrongs, offs = readings(x)
    missed = sum(len(a.missed) for a in x.ann.values())
    store[n] = dict(empties=empties, wrongs=wrongs, offs=offs)
    fmt = lambda v: '-' if v is None else f'{v:.1f}'
    print(f"{n} | {cont:.2f} | {pops} | {unas} | {fmt(cds[0])},{fmt(cds[-1])} | {lk['run']}/{lk['pair']}/{lk['record']} | {x.labels.relinked} | {fmt(prs[0])},{fmt(prs[-1])} | {fmt(rrs[0])},{fmt(rrs[-1])} | {ag}/{tot} {100*ag/max(1,tot):.1f} | {er} | {wr}+{len(offs)}off | {missed}")
json.dump(store, open(OUT / f'qual-{span}-detail.json', 'w'), indent=0, default=str)

print('\nSUMMARY: scale | contdiff% targets (mean over repeats x refs) | contdiff% all boxes | pairs repro% | runs repro% | strict agree% r1/r2 | wrongbox r1/r2 | off r1/r2 | empty_real r1/r2 | pairs n | runs n | records n | popups | cont/rec')
for phase, scales in SETS:
    for s in scales:
        xs = [runs[f'{span}-{s}-r{r}'] for r in (1, 2) if f'{span}-{s}-r{r}' in runs]
        if len(xs) < 2: print(s, 'incomplete'); continue
        cd = []; cda = []; pr = []; rr = []
        for x in xs:
            for ref in refs:
                if ref is x: continue
                d, tot = container_diff(x, ref); cd.append(100 * len(d) / tot)
                n = k = 0
                for ref_ in x.labels._boxes:
                    src = x.labels._source.get(ref_)
                    if src is None: continue
                    n += 1; k += (parse_box_ref(src) in d)
                cda.append(100 * k / n)
                rp = linkset(ref, 'pair'); pr.append(100 * len(rp & linkset(x, 'pair')) / len(rp))
                r_ = linkset(ref, 'run'); rr.append(100 * len(r_ & linkset(x, 'run')) / len(r_))
        rd = [readings(x) for x in xs]
        lk = [links_by_kind(x) for x in xs]
        print(f"{s} | {np.mean(cd):.1f} ({'/'.join(f'{v:.1f}' for v in cd)}) | {np.mean(cda):.1f} | {np.mean(pr):.0f} ({'/'.join(f'{v:.0f}' for v in pr)}) | {np.mean(rr):.0f} | {100*rd[0][0]/rd[0][1]:.1f}/{100*rd[1][0]/rd[1][1]:.1f} | {rd[0][3]}/{rd[1][3]} | {len(rd[0][6])}/{len(rd[1][6])} | {rd[0][2]}/{rd[1][2]} | {lk[0]['pair']}/{lk[1]['pair']} | {lk[0]['run']}/{lk[1]['run']} | {lk[0]['record']}/{lk[1]['record']} | {'/'.join(str(sum(1 for a in x.ann.values() for c in a.containers if c.kind=='popup')) for x in xs)} | {'/'.join(f'{np.mean([len(a.containers) for a in x.ann.values()]):.2f}' for x in xs)}")
