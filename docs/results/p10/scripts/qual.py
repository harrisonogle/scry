"""P10 label quality, coords against ids, yardstick = both ids100 repeats of this phase. Usage: qual.py <span>"""
import json, sys, re, hashlib
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from scry.run import Run
from scry.schemas import parse_box_ref
ROOT = Path('<repo>/runs/eval/p10')
REFS = ['ids100', 'coords100', 'ids067', 'coords067', 'ids050', 'coords050']
span = sys.argv[1]

class R:
    def __init__(self, name):
        self.name = name; self.run = Run(ROOT / name)
        self.ann = {a.frame: a for a in self.run.load_annotations()}
        self.boxes = {fb.frame: fb for fb in self.run.load_boxes()}
        self.labels = self.run.load_labels()
        self.boxhash = hashlib.sha256((ROOT / name / 'boxes.jsonl').read_bytes()).hexdigest()[:10]
runs = {f'{span}-{s}-r{r}': R(f'{span}-{s}-r{r}') for s in REFS for r in (1, 2)}
print('runs', len(runs), 'box hashes', Counter(r.boxhash for r in runs.values()),
      'targets identical:', len({json.dumps({f: a.targets for f, a in r.ann.items()}, sort_keys=True) for r in runs.values()}) == 1)
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
refs = [runs[f'{span}-ids100-r1'], runs[f'{span}-ids100-r2']]
refpairs = linkset(refs[0], 'pair') | linkset(refs[1], 'pair')
print('\nrun | cont/rec | popups | unassigned | repairs (kinds) | contdiff% vs r1,r2 | links run/pair/record | relinked | pairs-repro% vs r1,r2 | runs-repro% vs r1,r2 | off-row pairs (dy>12) [frames] | run jumps | pairs in neither ids100 ref | of which gap>150px | max pair gap')
for n, x in runs.items():
    cont = np.mean([len(a.containers) for a in x.ann.values()])
    pops = sum(1 for a in x.ann.values() for c in a.containers if c.kind == 'popup')
    unas = sum(len(a.unassigned) for a in x.ann.values())
    rk = Counter()
    for a in x.ann.values(): rk.update(a.repair_counts)
    cds = []; prs = []; rrs = []
    for ref in refs:
        if ref is x: cds.append(None); prs.append(None); rrs.append(None); continue
        d, tot = container_diff(x, ref); cds.append(100 * len(d) / tot)
        rp = linkset(ref, 'pair'); prs.append(100 * len(rp & linkset(x, 'pair')) / max(1, len(rp)))
        rr = linkset(ref, 'run'); rrs.append(100 * len(rr & linkset(x, 'run')) / max(1, len(rr)))
    lk = Counter(l.kind for a in x.ann.values() for l in a.links)
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
    fmt = lambda v: '-' if v is None else f'{v:.1f}'
    print(f"{n} | {cont:.2f} | {pops} | {unas} | {sum(rk.values())} {dict(rk)} | {fmt(cds[0])},{fmt(cds[1])} | {lk['run']}/{lk['pair']}/{lk['record']} | {x.labels.relinked} | {fmt(prs[0])},{fmt(prs[1])} | {fmt(rrs[0])},{fmt(rrs[1])} | {len(off)} {dict(Counter(o[0] for o in off))} | {len(rj)} | {len(newp)} | {sum(1 for p in newp if sum(p[1]) > 150)} | {maxg}")
    for o in off: print('      OFFROW', o)
    for o in rj: print('      RUNJUMP', o)
    for o in newp:
        if sum(o[1]) > 150: print('      FARNEWPAIR', o)

# --- terminal boxes and tooltips (P3 spec.py) ---
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
r1, r2 = refs[0].ann, refs[1].ann
term = {(f, b) for f, a in r1.items() for b in a.targets if cls(cont_of(a, b)) == 'term' and f in r2 and cls(cont_of(r2[f], b)) == 'term'}
disagree = sum(1 for f, a in r1.items() for b in a.targets if (cls(cont_of(a, b)) == 'term') != (cls(cont_of(r2[f], b)) == 'term'))
print('\nterminal targets (both ids100 refs agree):', len(term), '; refs disagree on', disagree)
print('run | term boxes in a terminal window | term frames with a terminal listed | false-terminal | records with 0 windows | tooltip149 | tooltip151 | app vocab (kind,app) top')
for n, x in runs.items():
    ann = x.ann
    ok = sum(1 for f, b in term if f in ann and cls(cont_of(ann[f], b)) == 'term')
    miss = [(f, b, cls(cont_of(ann[f], b)), x.boxes[f].boxes[[bb.id for bb in x.boxes[f].boxes].index(b)].text[:30]) for f, b in sorted(term) if cls(cont_of(ann[f], b)) != 'term']
    false = [(f, b) for f, a in ann.items() for b in a.targets if cls(cont_of(a, b)) == 'term' and (f, b) not in term and cls(cont_of(r1[f], b)) != 'term' and cls(cont_of(r2[f], b)) != 'term']
    tf = sorted({f for f, b in term}); listed = sum(1 for f in tf if any(cls(c) == 'term' for c in ann[f].containers))
    tt = []
    for f, b in ((149, 'b13'), (151, 'b116')):
        if f in ann and b in ann[f].targets:
            c = cont_of(ann[f], b); pops = [c2.name for c2 in ann[f].containers if c2.kind == 'popup']
            tt.append(f"{'OWN-POPUP' if c and c.kind == 'popup' else 'in:' + cls(c)} {pops}")
        else: tt.append('-')
    voc = Counter((c.kind, c.app) for a in ann.values() for c in a.containers)
    print(f"{n} | {ok}/{len(term)} | {listed}/{len(tf)} | {len(false)} | {sum(1 for a in ann.values() if not a.containers)} | {tt[0]} | {tt[1]} | {voc.most_common(4)}")
    if miss: print('      missed term boxes:', miss[:12])
    if false: print('      false term boxes:', [(f, b, next(bb.text[:30] for bb in x.boxes[f].boxes if bb.id == b)) for f, b in false][:12])

# --- frame 150 pairs (P3 f150.py) ---
if span == 'smoke':
    T = [('b33','b34'),('b38','b37'),('b40','b39'),('b43','b44'),('b47','b48'),('b49','b50'),('b54','b55'),
         ('b69','b70'),('b72','b73'),('b83','b84'),('b89','b88'),('b94','b93'),('b105','b104'),('b110','b109'),('b119','b118'),
         ('b67','b68'),('b74','b75'),('b81','b82'),('b87','b86'),('b90','b91'),('b95','b96'),('b99','b98'),('b103','b102'),('b107','b108'),
         ('b112','b113'),('b117+b120','b116'),('b128','b127'),('b130','b131')]
    truth = {(frozenset(k.split('+')), frozenset(v.split('+'))) for k, v in T}
    print('\nFRAME 150 pairs of 28')
    for n, x in runs.items():
        L = x.labels; fl = L.frame(150); ocr = {b.id: b.text for b in x.boxes[150].boxes}
        loc = lambda ref: parse_box_ref(ref)[1]
        pairs = [(frozenset(map(loc, l.key)), frozenset(map(loc, l.value))) for l in fl.links if l.kind == 'pair']
        correct = [p for p in pairs if p in truth]
        partial = [p for p in pairs if p not in truth and any(p[1] == t[1] and p[0] <= t[0] for t in truth)]
        wrong = [p for p in pairs if p not in truth and p not in partial]
        missing = [t for t in truth if t not in pairs and not any(p[1] == t[1] and p[0] <= t[0] for p in partial)]
        print(f'{n}: pairs in force {len(pairs)} correct {len(correct)} partial {len(partial)} wrong {len(wrong)} missing {len(missing)}')
        for k, v in wrong: print('    WRONG ', ' + '.join(ocr[b][:40] for b in sorted(k)), ' => ', ' + '.join(ocr[b][:40] for b in sorted(v)))
        for k, v in partial: print('    PARTIAL ', ' + '.join(ocr[b][:40] for b in sorted(k)), ' => ', ' + '.join(ocr[b][:40] for b in sorted(v)))
        for k, v in missing: print('    MISSING ', ' + '.join(ocr[b][:40] for b in sorted(k)), ' => ', ' + '.join(ocr[b][:40] for b in sorted(v)))

# --- descriptions mentioning the mechanism ---
pat = re.compile(r"\bb\d{1,3}\b|\bbox(?:es)?\s+\d|\bnumbered\b|\boverlay\b|\bmagenta\b|\byellow (?:tag|label)|\btargets? (?:box|were|was|is|are|list)|no targets|\bannotat|image [12]\b|\bcoordinat|\brectangle|\bx0\b|\bthe list\b|\blisted\b|\bbox ids?\b|\bthe targets?\b|\bOCR\b|\bbounding\b|\d{2,4},\d{2,4},\d{2,4}", re.I)
print('\nDESCRIPTIONS mentioning the mechanism')
for n, x in runs.items():
    hits = [(f, a.description[max(0, m.start() - 40):m.end() + 40]) for f, a in x.ann.items() if a.description for m in [pat.search(a.description)] if m]
    print(n, len(hits), hits[:4], 'no-description', [f for f, a in x.ann.items() if not a.description])
