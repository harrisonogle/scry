"""Group-only coords quality: P13 cg (0.4, 0.3, 0.25, 0.2) with P12 coords067/050 (corrected listing, smoke only) and
P10 coords100 above; yardstick both P10 ids100 repeats; P10's columns (P10 qual.py / P12 qual.py). Span2 has no P12 runs,
so P10 coords067/050 (old listing) stand in there, marked. Usage: qual_cg.py <span>"""
import json, sys, re
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from scry.run import Run
from scry.schemas import parse_box_ref
E = Path('/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval')
span = sys.argv[1]
SETS = [('p10', 'ids100'), ('p10', 'coords100'), ('p10', 'ids067'), ('p12' if span == 'smoke' else 'p10', 'coords067'), ('p10', 'ids050'), ('p12' if span == 'smoke' else 'p10', 'coords050'),
        ('p13', 'cg040'), ('p13', 'cg030'), ('p13', 'cg025'), ('p13', 'cg020')]
class R:
    def __init__(self, phase, name):
        self.name = name; self.phase = phase; self.run = Run(E / phase / name)
        self.ann = {a.frame: a for a in self.run.load_annotations()}
        self.boxes = {fb.frame: fb for fb in self.run.load_boxes()}
        self.labels = self.run.load_labels()
runs = {}
for phase, s in SETS:
    for r in (1, 2):
        n = f'{span}-{s}-r{r}'
        if (E / phase / n / 'annotations.jsonl').exists(): runs[f'{phase}:{n}'] = R(phase, n)
print('runs', len(runs), 'targets identical:', len({json.dumps({f: a.targets for f, a in r.ann.items()}, sort_keys=True) for r in runs.values()}) == 1,
      'boxes identical:', len({json.dumps({f: [(b.id, b.bbox, b.text) for b in fb.boxes] for f, fb in r.boxes.items()}, sort_keys=True) for r in runs.values()}) == 1)
def assign_map(a): return {x.box: x.container for x in a.assign}
def appclass(c):
    if c is None: return 'none'
    s = (c.app + ' ' + c.name).lower(); k = 'P:' if c.kind == 'popup' else 'W:'
    if 'powershell' in s or 'terminal' in s or 'pwsh' in s: return k + 'term'
    if 'edge' in s or 'browser' in s or 'chrome' in s or 'azure' in s: return k + 'browser'
    if 'taskbar' in s or 'windows' in s or 'explorer' in s or 'shell' in s or 'desktop' in s: return k + 'os'
    return k + 'other'
def container_diff(x, ref):
    diff = set(); tot = 0
    for f, ra in ref.ann.items():
        xa = x.ann.get(f); rm = assign_map(ra); tot += len(ra.targets)
        if xa is None or xa.error: diff |= {(f, b) for b in ra.targets}; continue
        xm = assign_map(xa)
        xc = sorted({v for b, v in xm.items() if b in ra.targets}); rc = sorted({v for b, v in rm.items() if b in ra.targets})
        if not xc or not rc:
            diff |= {(f, b) for b in ra.targets if xm.get(b) != rm.get(b) or xm.get(b) is None}; continue
        M = np.zeros((len(xc), len(rc)))
        for b in ra.targets:
            if b in xm and b in rm: M[xc.index(xm[b]), rc.index(rm[b])] += 1
        ri, ci = linear_sum_assignment(-M); match = {xc[i]: rc[j] for i, j in zip(ri, ci) if M[i, j] > 0}
        xcon = {c.id: c for c in xa.containers}; rcon = {c.id: c for c in ra.containers}
        for b in ra.targets:
            xb, rb = xm.get(b), rm.get(b)
            if xb is None and rb is None: continue
            if xb is None or rb is None or match.get(xb) != rb: diff.add((f, b)); continue
            if appclass(xcon.get(xb)) != appclass(rcon.get(rb)): diff.add((f, b))
    return diff, tot
def linkset(x, kind):
    out = set()
    for f, a in x.ann.items():
        for l in a.links:
            if l.kind != kind: continue
            if kind == 'pair': out.add((f, frozenset(l.key), frozenset(l.value)))
            elif kind == 'run': out.add((f, tuple(l.boxes)))
            else: out.add((f, tuple(tuple(c) for c in l.members)))
    return out
def gap(a, b): return max(0, max(a[0], b[0]) - min(a[2], b[2])), max(0, max(a[1], b[1]) - min(a[3], b[3]))
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
refs = [runs[f'p10:{span}-ids100-r1'], runs[f'p10:{span}-ids100-r2']]
refpairs = linkset(refs[0], 'pair') | linkset(refs[1], 'pair')
r1, r2 = refs[0].ann, refs[1].ann
term = {(f, b) for f, a in r1.items() for b in a.targets if cls(cont_of(a, b)) == 'term' and f in r2 and cls(cont_of(r2[f], b)) == 'term'}
T = [('b33','b34'),('b38','b37'),('b40','b39'),('b43','b44'),('b47','b48'),('b49','b50'),('b54','b55'),
     ('b69','b70'),('b72','b73'),('b83','b84'),('b89','b88'),('b94','b93'),('b105','b104'),('b110','b109'),('b119','b118'),
     ('b67','b68'),('b74','b75'),('b81','b82'),('b87','b86'),('b90','b91'),('b95','b96'),('b99','b98'),('b103','b102'),('b107','b108'),
     ('b112','b113'),('b117+b120','b116'),('b128','b127'),('b130','b131')]
truth = {(frozenset(k.split('+')), frozenset(v.split('+'))) for k, v in T}
pat = re.compile(r"\bb\d{1,3}\b|\bbox(?:es)?\s+\d|\bnumbered\b|\boverlay\b|\bmagenta\b|\byellow (?:tag|label)|\btargets? (?:box|were|was|is|are|list)|no targets|\bannotat|image [12]\b|\bcoordinat|\brectangle|\bx0\b|\bthe list\b|\blisted\b|\bbox ids?\b|\bthe targets?\b|\bOCR\b|\bbounding\b|\d{2,4},\d{2,4},\d{2,4}", re.I)

def measure(x):
    m = {}
    m['cont'] = np.mean([len(a.containers) for a in x.ann.values()])
    m['popups'] = sum(1 for a in x.ann.values() for c in a.containers if c.kind == 'popup')
    m['unassigned'] = sum(len(a.unassigned) for a in x.ann.values())
    rk = Counter()
    for a in x.ann.values(): rk.update(a.repair_counts)
    m['repairs'] = dict(rk); m['nrep'] = sum(rk.values())
    cds = []; prs = []; rrs = []
    for ref in refs:
        if ref is x: continue
        d, tot = container_diff(x, ref); cds.append(100 * len(d) / tot)
        rp = linkset(ref, 'pair'); prs.append(100 * len(rp & linkset(x, 'pair')) / max(1, len(rp)))
        rr = linkset(ref, 'run'); rrs.append(100 * len(rr & linkset(x, 'run')) / max(1, len(rr)))
    m['contdiff'] = np.mean(cds); m['pairs'] = np.mean(prs); m['runs'] = np.mean(rrs); m['cds'] = cds; m['prs'] = prs; m['rrs'] = rrs
    lk = Counter(l.kind for a in x.ann.values() for l in a.links); m['links'] = (lk['run'], lk['pair'], lk['record'])
    off = []; rj = []; newp = []; maxg = 0
    for f, a in x.ann.items():
        bb = {b.id: b for b in x.boxes[f].boxes}
        for l in a.links:
            if l.kind == 'pair':
                g = min((gap(bb[k].bbox, bb[v].bbox) for k in l.key for v in l.value if k in bb and v in bb), key=lambda t: t[1] * 10 + t[0], default=(0, 0))
                maxg = max(maxg, sum(g))
                if g[1] > 12: off.append((f, g, ' + '.join(bb[k].text[:25] for k in l.key), '=>', ' + '.join(bb[v].text[:25] for v in l.value)))
                if (f, frozenset(l.key), frozenset(l.value)) not in refpairs: newp.append((f, g, ' + '.join(bb[k].text[:25] for k in l.key), '=>', ' + '.join(bb[v].text[:25] for v in l.value)))
            elif l.kind == 'run':
                gs = [gap(bb[p].bbox, bb[q].bbox) for p, q in zip(l.boxes, l.boxes[1:]) if p in bb and q in bb]
                if any(g[1] > 12 or g[0] > 300 for g in gs): rj.append((f, gs, ' | '.join(bb[p].text[:25] for p in l.boxes)))
    m['off'] = off; m['rj'] = rj; m['newp'] = newp; m['far'] = [p for p in newp if sum(p[1]) > 150]; m['maxg'] = maxg
    m['relinked'] = x.labels.relinked
    ann = x.ann
    m['term_ok'] = sum(1 for f, b in term if f in ann and cls(cont_of(ann[f], b)) == 'term')
    m['term_missed'] = [(f, b, cls(cont_of(ann[f], b)), next(bb.text[:30] for bb in x.boxes[f].boxes if bb.id == b)) for f, b in sorted(term) if cls(cont_of(ann[f], b)) != 'term']
    m['term_false'] = [(f, b, next(bb.text[:30] for bb in x.boxes[f].boxes if bb.id == b)) for f, a in ann.items() for b in a.targets if cls(cont_of(a, b)) == 'term' and (f, b) not in term and cls(cont_of(r1[f], b)) != 'term' and cls(cont_of(r2[f], b)) != 'term']
    tf = sorted({f for f, b in term}); m['term_listed'] = (sum(1 for f in tf if any(cls(c) == 'term' for c in ann[f].containers)), len(tf))
    m['zero_cont'] = sum(1 for a in ann.values() if not a.containers)
    tt = []; own = 0
    for f, b in ((149, 'b13'), (151, 'b116')):
        if f in ann and b in ann[f].targets:
            c = cont_of(ann[f], b); pops = [c2.name for c2 in ann[f].containers if c2.kind == 'popup']
            o = bool(c and c.kind == 'popup'); own += o
            tt.append(f"{'OWN-POPUP' if o else 'in:' + cls(c)} {pops}")
        else: tt.append('-')
    m['tooltips'] = tt; m['tooltip_own'] = own
    m['vocab'] = Counter((c.kind, c.app) for a in ann.values() for c in a.containers).most_common(4)
    if 150 in ann:
        fl = x.labels.frame(150); loc = lambda ref: parse_box_ref(ref)[1]; ocr = {b.id: b.text for b in x.boxes[150].boxes}
        pairs = [(frozenset(map(loc, l.key)), frozenset(map(loc, l.value))) for l in fl.links if l.kind == 'pair']
        correct = [p for p in pairs if p in truth]
        partial = [p for p in pairs if p not in truth and any(p[1] == t[1] and p[0] <= t[0] for t in truth)]
        wrong_ = [p for p in pairs if p not in truth and p not in partial]
        missing = [t for t in truth if t not in pairs and not any(p[1] == t[1] and p[0] <= t[0] for p in partial)]
        m['f150'] = (len(correct), len(partial), len(wrong_), len(missing))
        m['f150_detail'] = dict(wrong=[(' + '.join(ocr[b][:30] for b in sorted(k)), ' + '.join(ocr[b][:30] for b in sorted(v))) for k, v in wrong_],
                                partial=[(' + '.join(ocr[b][:30] for b in sorted(k)), ' + '.join(ocr[b][:30] for b in sorted(v))) for k, v in partial],
                                missing=[(' + '.join(ocr[b][:30] for b in sorted(k)), ' + '.join(ocr[b][:30] for b in sorted(v))) for k, v in missing])
    else: m['f150'] = None
    m['desc_hits'] = [(f, a.description[max(0, mm.start() - 40):mm.end() + 40]) for f, a in ann.items() if a.description for mm in [pat.search(a.description)] if mm]
    m['no_desc'] = [f for f, a in ann.items() if not a.description]
    return m
M = {n: measure(x) for n, x in runs.items()}
print(f'\nterminal targets (both ids100 refs agree): {len(term)}')
print('\n== PER RUN')
print('run | cont/rec | popups | unassigned | repairs (kinds) | contdiff% vs r1,r2 | links run/pair/record | relinked | pairs-repro% vs r1,r2 | runs-repro% vs r1,r2 | off-row pairs (dy>12) | run jumps | pairs in neither ids100 ref | of which gap>150px | max pair gap | term ok | term frames listed | false term | 0-window records | tooltip149 | tooltip151 | f150 c/p/w/m | desc mechanism hits | vocab')
fmt = lambda vs: ','.join(f'{v:.1f}' for v in vs) if vs else '-'
for n, m in M.items():
    print(f"{n} | {m['cont']:.2f} | {m['popups']} | {m['unassigned']} | {m['nrep']} {m['repairs']} | {fmt(m['cds'])} | {'/'.join(map(str, m['links']))} | {m['relinked']} | {fmt(m['prs'])} | {fmt(m['rrs'])} | {len(m['off'])} {dict(Counter(o[0] for o in m['off']))} | {len(m['rj'])} | {len(m['newp'])} | {len(m['far'])} | {m['maxg']} | {m['term_ok']}/{len(term)} | {m['term_listed'][0]}/{m['term_listed'][1]} | {len(m['term_false'])} | {m['zero_cont']} | {m['tooltips'][0]} | {m['tooltips'][1]} | {m['f150']} | {len(m['desc_hits'])} | {m['vocab']}")
    for o in m['off']: print('      OFFROW', o)
    for o in m['rj']: print('      RUNJUMP', o)
    for o in m['far']: print('      FARNEWPAIR', o)
    if m['term_missed']: print('      missed term:', m['term_missed'][:12])
    if m['term_false']: print('      false term:', m['term_false'][:12])
    if m['f150'] and (m['f150'][1] or m['f150'][2] or m['f150'][3]): print('      f150:', {k: v for k, v in m['f150_detail'].items() if v})
    if m['desc_hits']: print('      desc:', m['desc_hits'][:4])
    if m['no_desc']: print('      no description:', m['no_desc'])
print("\n== PER SET (mean of repeats; P10's analysis columns). First row = ids100 vs the other ids100 (noise).")
print(f"set | pairs repro % | runs repro % | cont differs % | term boxes (of {len(term)}) | false term | tooltips own popup (of 4, 2 runs) | f150 correct/wrong/missing (sum of 2 runs; partial) | links run/pair/rec | repairs (kinds, sum) | cont/rec | off-row pairs r1,r2 | run jumps | pairs in neither ref r1,r2 | of which gap>150 | desc mechanism hits r1,r2")
for phase, s in SETS:
    ms = [M[f'{phase}:{span}-{s}-r{r}'] for r in (1, 2) if f'{phase}:{span}-{s}-r{r}' in M]
    if not ms: print(f'{phase}:{s} MISSING'); continue
    mean = lambda k: np.mean([m[k] for m in ms])
    rk = Counter()
    for m in ms: rk.update(m['repairs'])
    f150 = None if ms[0]['f150'] is None else tuple(sum(m['f150'][i] for m in ms) for i in range(4))
    links = tuple(np.mean([m['links'][i] for m in ms]) for i in range(3))
    print(f"{phase}:{s} (n={len(ms)}) | {mean('pairs'):.1f} | {mean('runs'):.1f} | {mean('contdiff'):.1f} | {mean('term_ok'):.1f} | {np.mean([len(m['term_false']) for m in ms]):.1f} | {sum(m['tooltip_own'] for m in ms)} | {'-' if f150 is None else f'{f150[0]}/{f150[2]}/{f150[3]} (partial {f150[1]})'} | {'/'.join(f'{v:.1f}' for v in links)} | {sum(rk.values())} {dict(rk)} | {mean('cont'):.2f} | {','.join(str(len(m['off'])) for m in ms)} | {','.join(str(len(m['rj'])) for m in ms)} | {','.join(str(len(m['newp'])) for m in ms)} | {','.join(str(len(m['far'])) for m in ms)} | {','.join(str(len(m['desc_hits'])) for m in ms)}")
