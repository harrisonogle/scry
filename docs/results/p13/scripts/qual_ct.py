"""P13 transcribing quality (coords, ct) beside P3's overlay (s) at the same scale. Yardstick: both P3 s100 repeats
(each candidate is measured against each ref; the mean over repeats x refs is reported, as P3's summ.py did).
P3's qual.py / summ.py / spec.py / f150.py measures, one script. Usage: qual_ct.py <span>"""
import json, sys, re
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from rapidfuzz import fuzz
from scry.run import Run
from scry.annotate.join import agreement
from scry.textdiff import norm
from scry.schemas import parse_box_ref
E = Path('/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval')
SC = ['100', '067', '050', '040', '030', '025', '020']
span = sys.argv[1]

class R:
    def __init__(self, phase, name):
        self.name = name; self.run = Run(E / phase / name)
        self.ann = {a.frame: a for a in self.run.load_annotations()}
        self.boxes = {fb.frame: fb for fb in self.run.load_boxes()}
        self.labels = self.run.load_labels()
        self.manifest = json.load(open(E / phase / name / 'manifest.json'))['stages']['annotate']
runs = {}
for sc in SC:
    for r in (1, 2):
        for phase, pre in (('p3', 's'), ('p13', 'ct')):
            n = f'{span}-{pre}{sc}-r{r}'
            if (E / phase / n / 'annotations.jsonl').exists(): runs[n] = R(phase, n)
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
def readings(x):
    """P3's rule: agree/total, real words read as '', readings that are another box's text (wrong box), off (nothing like any box)"""
    agree = tot = empty_real = wrong = 0; empties = []; wrongs = []; offs = []
    for f, a in x.ann.items():
        if a.texts is None: continue
        frame_ocr = {b.id: b.text for b in x.boxes[f].boxes}
        for t in a.texts:
            o = frame_ocr.get(t.box)
            if o is None: continue
            if not t.text.strip():
                if len(re.findall(r'[A-Za-z]{3,}', o)) >= 1: empty_real += 1; empties.append((f, t.box, o))
                continue
            tot += 1
            if agreement(o, t.text): agree += 1; continue
            a_, b_ = norm(o).lower(), norm(t.text).lower()
            if fuzz.ratio(a_, b_) < 60 and fuzz.partial_ratio(a_, b_) < 80 and len(b_) >= 3:
                other = [b for b, ot in frame_ocr.items() if b != t.box and fuzz.ratio(norm(ot).lower(), b_) >= 90]
                if other: wrong += 1; wrongs.append((f, t.box, o, t.text, other[:2]))
                else: offs.append((f, t.box, o, t.text))
    return agree, tot, empty_real, wrong, empties, wrongs, offs
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

refs = [runs[f'{span}-s100-r1'], runs[f'{span}-s100-r2']]
r1, r2 = refs[0].ann, refs[1].ann
term = {(f, b) for f, a in r1.items() for b in a.targets if cls(cont_of(a, b)) == 'term' and f in r2 and cls(cont_of(r2[f], b)) == 'term'}
T = [('b33','b34'),('b38','b37'),('b40','b39'),('b43','b44'),('b47','b48'),('b49','b50'),('b54','b55'),
     ('b69','b70'),('b72','b73'),('b83','b84'),('b89','b88'),('b94','b93'),('b105','b104'),('b110','b109'),('b119','b118'),
     ('b67','b68'),('b74','b75'),('b81','b82'),('b87','b86'),('b90','b91'),('b95','b96'),('b99','b98'),('b103','b102'),('b107','b108'),
     ('b112','b113'),('b117+b120','b116'),('b128','b127'),('b130','b131')]
truth = {(frozenset(k.split('+')), frozenset(v.split('+'))) for k, v in T}

def measure(x):
    m = {}
    mm = x.manifest['mark_match']; m['mark'] = 100 * mm['hits'] / max(1, mm['total']); m['mark_raw'] = (mm['hits'], mm['total'])
    cds = []; prs = []; rrs = []
    for ref in refs:
        if ref is x: continue
        d, tot = container_diff(x, ref); cds.append(100 * len(d) / tot)
        rp = linkset(ref, 'pair'); prs.append(100 * len(rp & linkset(x, 'pair')) / max(1, len(rp)))
        rr = linkset(ref, 'run'); rrs.append(100 * len(rr & linkset(x, 'run')) / max(1, len(rr)))
    m['contdiff'] = np.mean(cds); m['pairs'] = np.mean(prs); m['runs'] = np.mean(rrs)
    ag, tot, er, wr, empties, wrongs, offs = readings(x)
    m['agree'] = 100 * ag / max(1, tot); m['nread'] = tot; m['empty_real'] = er; m['wrong'] = wr; m['off'] = len(offs)
    m['wrongs'] = wrongs; m['empties'] = empties; m['offs'] = offs
    lk = Counter(l.kind for a in x.ann.values() for l in a.links); m['links'] = (lk['run'], lk['pair'], lk['record'])
    rk = Counter()
    for a in x.ann.values(): rk.update(a.repair_counts)
    m['repairs'] = dict(rk); m['nrep'] = sum(rk.values())
    m['cont'] = np.mean([len(a.containers) for a in x.ann.values()])
    m['popups'] = sum(1 for a in x.ann.values() for c in a.containers if c.kind == 'popup')
    m['unassigned'] = sum(len(a.unassigned) for a in x.ann.values())
    m['missed'] = sum(len(a.missed) for a in x.ann.values())
    m['zero_cont'] = sum(1 for a in x.ann.values() if not a.containers)
    m['errors'] = sum(1 for a in x.ann.values() if a.error)
    ann = x.ann
    m['term_ok'] = sum(1 for f, b in term if f in ann and cls(cont_of(ann[f], b)) == 'term')
    m['term_missed'] = [(f, b, cls(cont_of(ann[f], b)), next(bb.text[:30] for bb in x.boxes[f].boxes if bb.id == b)) for f, b in sorted(term) if cls(cont_of(ann[f], b)) != 'term']
    m['term_false'] = [(f, b, next(bb.text[:30] for bb in x.boxes[f].boxes if bb.id == b)) for f, a in ann.items() for b in a.targets if cls(cont_of(a, b)) == 'term' and (f, b) not in term and cls(cont_of(r1[f], b)) != 'term' and cls(cont_of(r2[f], b)) != 'term']
    tt = []; tooltip_own = 0
    for f, b in ((149, 'b13'), (151, 'b116')):
        if f in ann and b in ann[f].targets:
            c = cont_of(ann[f], b); pops = [c2.name for c2 in ann[f].containers if c2.kind == 'popup']
            own = bool(c and c.kind == 'popup'); tooltip_own += own
            tt.append(f"{'OWN-POPUP' if own else 'in:' + cls(c)} {pops}")
        else: tt.append('-')
    m['tooltips'] = tt; m['tooltip_own'] = tooltip_own
    if 150 in ann:
        fl = x.labels.frame(150); loc = lambda ref: parse_box_ref(ref)[1]
        pairs = [(frozenset(map(loc, l.key)), frozenset(map(loc, l.value))) for l in fl.links if l.kind == 'pair']
        correct = [p for p in pairs if p in truth]
        partial = [p for p in pairs if p not in truth and any(p[1] == t[1] and p[0] <= t[0] for t in truth)]
        wrong_ = [p for p in pairs if p not in truth and p not in partial]
        missing = [t for t in truth if t not in pairs and not any(p[1] == t[1] and p[0] <= t[0] for p in partial)]
        ocr = {b.id: b.text for b in x.boxes[150].boxes}
        m['f150'] = (len(correct), len(partial), len(wrong_), len(missing))
        m['f150_detail'] = dict(wrong=[(' + '.join(ocr[b][:30] for b in sorted(k)), ' + '.join(ocr[b][:30] for b in sorted(v))) for k, v in wrong_],
                                partial=[(' + '.join(ocr[b][:30] for b in sorted(k)), ' + '.join(ocr[b][:30] for b in sorted(v))) for k, v in partial],
                                missing=[(' + '.join(ocr[b][:30] for b in sorted(k)), ' + '.join(ocr[b][:30] for b in sorted(v))) for k, v in missing])
    else: m['f150'] = None
    return m

M = {n: measure(x) for n, x in runs.items()}
print(f'\nterminal targets (both s100 refs agree): {len(term)}')
print('\n== PER RUN')
print('run | mark_match | agree% (n read) | wrongbox | off | empty_real | contdiff% | pairs repro% | runs repro% | links run/pair/rec | repairs | cont/rec | popups | unassigned | missed | 0-cont | errors | term ok | false term | tooltips 149,151 | f150 correct/partial/wrong/missing')
for n, m in M.items():
    print(f"{n} | {m['mark_raw'][0]}of{m['mark_raw'][1]} {m['mark']:.1f} | {m['agree']:.1f} ({m['nread']}) | {m['wrong']} | {m['off']} | {m['empty_real']} | {m['contdiff']:.1f} | {m['pairs']:.1f} | {m['runs']:.1f} | {'/'.join(map(str, m['links']))} | {m['nrep']} {m['repairs']} | {m['cont']:.2f} | {m['popups']} | {m['unassigned']} | {m['missed']} | {m['zero_cont']} | {m['errors']} | {m['term_ok']}/{len(term)} | {len(m['term_false'])} | {m['tooltips']} | {m['f150']}")
    if m['term_missed']: print('      missed term:', m['term_missed'][:10])
    if m['term_false']: print('      false term:', m['term_false'][:10])
    if m['f150'] and (m['f150'][2] or m['f150'][3] or m['f150'][1]): print('      f150:', {k: v for k, v in m['f150_detail'].items() if v})

print('\n== PER SCALE (mean of repeats; contdiff/pairs/runs mean over repeats x refs; the 1.0 overlay row is s100 r1 vs r2 = repeat noise)')
print(f'scale | mode | mark_match % | wrong box | off | empty_real | pairs repro % | runs repro % | contdiff % | term boxes ok (of {len(term)}) | false term | tooltips own (of 4) | f150 correct/wrong/missing (sum of 2 runs) | links run/pair/rec | repairs (kinds, sum) | cont/rec')
summary = {}
for sc in SC:
    for mode, pre in (('overlay', 's'), ('coords', 'ct')):
        ms = [M[f'{span}-{pre}{sc}-r{r}'] for r in (1, 2) if f'{span}-{pre}{sc}-r{r}' in M]
        if not ms: print(f'{sc} | {mode} | MISSING'); continue
        n = len(ms); mean = lambda k: np.mean([m[k] for m in ms])
        rk = Counter()
        for m in ms: rk.update(m['repairs'])
        f150 = None if ms[0]['f150'] is None else tuple(sum(m['f150'][i] for m in ms) for i in range(4))
        links = tuple(np.mean([m['links'][i] for m in ms]) for i in range(3))
        summary[(sc, mode)] = dict(n=n, mark=mean('mark'), wrong=mean('wrong'), off=mean('off'), empty=mean('empty_real'), pairs=mean('pairs'), runs=mean('runs'),
                                  contdiff=mean('contdiff'), term=mean('term_ok'), false=np.mean([len(m['term_false']) for m in ms]),
                                  tooltip=sum(m['tooltip_own'] for m in ms), f150=f150, links=links, repairs=dict(rk), cont=mean('cont'))
        s = summary[(sc, mode)]
        print(f"{sc} | {mode} (n={n}) | {s['mark']:.1f} | {s['wrong']:.1f} | {s['off']:.1f} | {s['empty']:.1f} | {s['pairs']:.1f} | {s['runs']:.1f} | {s['contdiff']:.1f} | {s['term']:.1f} | {s['false']:.1f} | {s['tooltip']} | {'-' if f150 is None else f'{f150[0]}/{f150[2]}/{f150[3]} (partial {f150[1]})'} | {'/'.join(f'{v:.1f}' for v in links)} | {sum(rk.values())} {dict(rk)} | {s['cont']:.2f}")
json.dump({n: {k: v for k, v in m.items() if k in ('wrongs', 'empties', 'offs', 'term_missed', 'term_false', 'tooltips', 'f150_detail')} for n, m in M.items()},
          open(f'/private/tmp/claude-501/-Users-harrisonogle-src-harrisonogle-agentic-escort/00000000-0000-0000-0000-000000000000/scratchpad/p13-analysis/qual-ct-{span}-detail.json', 'w'), indent=0, default=str)
