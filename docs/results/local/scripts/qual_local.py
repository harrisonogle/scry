"""Label quality of local-model runs beside the API model's. Usage: qual_local.py <span> <run-dir>... (references: P3 s100 r1, r2)."""
import json, sys, re, hashlib
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from rapidfuzz import fuzz
from scry.run import Run
from scry.annotate.join import agreement
from scry.textdiff import norm
from scry.schemas import link_members

WT = Path('/Users/harrisonogle/src/harrisonogle/agentic-escort/.claude/worktrees/localvlm')
ROOT = WT / 'runs/eval/p3'
span = sys.argv[1]
EXTRA = [Path(p) for p in sys.argv[2:]]

class R:
    def __init__(self, name, path=None):
        self.name = name
        path = path or ROOT / name
        self.run = Run(path)
        self.ann = {a.frame: a for a in self.run.load_annotations()}
        self.boxes = {fb.frame: fb for fb in self.run.load_boxes()}
        self.ocr = {(f, b.id): b.text for f, fb in self.boxes.items() for b in fb.boxes}
        self.labels = self.run.load_labels()
        self.boxhash = hashlib.sha256((path / 'boxes.jsonl').read_bytes()).hexdigest()[:10]
        self.lifehash = hashlib.sha256((path / 'lifetimes.jsonl').read_bytes()).hexdigest()[:10]

runs = {}
for r in (1, 2):
    n = f'{span}-s100-r{r}'
    if (ROOT / n / 'annotations.jsonl').exists():
        runs[n] = R(n)
for p in EXTRA:
    if (p / 'annotations.jsonl').exists():
        runs[p.parent.name + '/' + p.name] = R(p.name, p)
print('runs loaded', len(runs), 'box hashes', Counter(r.boxhash for r in runs.values()), 'life hashes', Counter(r.lifehash for r in runs.values()))
print('targets identical across runs:', len({json.dumps({f: a.targets for f, a in r.ann.items()}, sort_keys=True) for r in runs.values()}) == 1)

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
    """per record: match x's containers to ref's by the targets they hold (Hungarian on overlap); a target differs when
    its container is not the matched one, or the matched pair disagree in kind/app class. Returns set of differing (frame, box)."""
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

def all_box_diff(x, ref, diff):
    """share of all boxes on all frames whose (source) label differs"""
    n = d = 0
    for (f, b) in x.ocr:
        lab = ref.labels.box(f'{f}/{b}') if False else None
    return None

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

refs = [runs[f'{span}-s100-r1'], runs[f'{span}-s100-r2']] if f'{span}-s100-r2' in runs else [runs[f'{span}-s100-r1']]
print('\nrun | cont/rec mean | popups | unassigned | contdiff% vs r1,r2 | appclass-mismatch | links run/pair/record | relinked | pairs-repro% vs r1,r2 | runs-repro% | agree/tot % | empty_real | wrongbox | missed')
store = {}
for n, x in runs.items():
    nrec = len(x.ann)
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
    print(f"{n} | {cont:.2f} | {pops} | {unas} | {fmt(cds[0])},{fmt(cds[-1])} | | {lk['run']}/{lk['pair']}/{lk['record']} | {x.labels.relinked} | {fmt(prs[0])},{fmt(prs[-1])} | {fmt(rrs[0])},{fmt(rrs[-1])} | {ag}/{tot} {100*ag/max(1,tot):.1f} | {er} | {wr}+{len(offs)}off | {missed}")
json.dump({n: {k: v for k, v in s.items()} for n, s in store.items()}, open(f'/private/tmp/claude-501/-Users-harrisonogle-src-harrisonogle-agentic-escort/00000000-0000-0000-0000-000000000000/scratchpad/localvlm/qual-{span}-detail.json', 'w'), indent=0, default=str)
