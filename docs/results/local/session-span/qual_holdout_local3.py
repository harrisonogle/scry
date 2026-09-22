"""Hold-out label quality (group-only measures): the local 27B run beside the API's own annotations of the same frames.
Usage: qual_holdout_local3.py <local-run-dir> [first-last]   (default 12-33). Yardstick: runs/v2/grouponly-100
(one run, Opus 5, so no repeat-noise figure exists for it). Adapted from docs/results/local/second-attempt/qual_p10_local2.py."""
import json, sys, re
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from scry.run import Run
from scry.schemas import parse_box_ref
from scry.costs import PRICES, CACHE_WRITE_MULTIPLIER

REFDIR = Path('<repo>/runs/v2/grouponly-100')
LOCAL = Path(sys.argv[1])
lo, hi = (int(v) for v in (sys.argv[2] if len(sys.argv) > 2 else '12-33').split('-'))
FR = list(range(lo, hi + 1))
QWEN_PRICE = (0.42, 3.00)  # $/M prompt, completion: OpenRouter, Qwen3.8-27B, the price the first probe cited

class R:
    def __init__(self, name, path):
        self.name = name; self.run = Run(path)
        self.ann = {a.frame: a for a in self.run.load_annotations() if a.frame in FR}
        self.boxes = {fb.frame: fb for fb in self.run.load_boxes() if fb.frame in FR}
        self.labels = self.run.load_labels()
ref = R('api', REFDIR); loc = R('27b', LOCAL)
done = sorted(f for f, a in loc.ann.items() if a.error is None)
failed = sorted(f for f, a in loc.ann.items() if a.error is not None)
print(f'frames {lo}-{hi}: {len(FR)} asked; local completed {len(done)} {done}; failed {len(failed)} {failed}')
same_boxes = all(f in loc.boxes and [b.id for b in loc.boxes[f].boxes] == [b.id for b in ref.boxes[f].boxes] for f in done)
print('box ids identical on completed frames:', same_boxes)
tdiff = {f: (len(set(ref.ann[f].targets)), len(set(loc.ann[f].targets)), len(set(ref.ann[f].targets) & set(loc.ann[f].targets))) for f in done}
print('targets (api, local, common) per frame:', tdiff)

def assign_map(a): return {x.box: x.container for x in a.assign}
def appclass(c):
    if c is None: return 'none'
    s = (c.app + ' ' + c.name).lower(); k = 'P:' if c.kind == 'popup' else 'W:'
    if 'powershell' in s or 'terminal' in s or 'pwsh' in s: return k + 'term'
    if 'edge' in s or 'browser' in s or 'chrome' in s or 'azure' in s or 'portal' in s or 'sign in' in s or 'microsoft' in s: return k + 'browser'
    if 'taskbar' in s or 'windows' in s or 'explorer' in s or 'shell' in s or 'desktop' in s: return k + 'os'
    return k + 'other'
def container_diff(x, refr, frames):
    """API targets that are also local targets; a target differs when its container does not match under the best
    one-to-one container matching of the frame, or matches a container of another kind/app class."""
    diff = set(); tot = 0; detail = {}
    for f in frames:
        ra = refr.ann[f]; xa = x.ann.get(f); rm = assign_map(ra)
        tg = [b for b in ra.targets if b in set(xa.targets)] if xa is not None and xa.error is None else []
        tot += len(tg)
        if not tg: continue
        xm = assign_map(xa)
        xc = sorted({v for b, v in xm.items() if b in tg}); rc = sorted({v for b, v in rm.items() if b in tg})
        if not xc or not rc:
            d = {(f, b) for b in tg if xm.get(b) != rm.get(b) or xm.get(b) is None}; diff |= d; detail[f] = len(d); continue
        M = np.zeros((len(xc), len(rc)))
        for b in tg:
            if b in xm and b in rm: M[xc.index(xm[b]), rc.index(rm[b])] += 1
        ri, ci = linear_sum_assignment(-M); match = {xc[i]: rc[j] for i, j in zip(ri, ci) if M[i, j] > 0}
        xcon = {c.id: c for c in xa.containers}; rcon = {c.id: c for c in ra.containers}
        n0 = len(diff)
        for b in tg:
            xb, rb = xm.get(b), rm.get(b)
            if xb is None and rb is None: continue
            if xb is None or rb is None or match.get(xb) != rb: diff.add((f, b)); continue
            if appclass(xcon.get(xb)) != appclass(rcon.get(rb)): diff.add((f, b))
        detail[f] = len(diff) - n0
    return diff, tot, detail
def linkset(x, kind, frames):
    out = set()
    for f in frames:
        a = x.ann.get(f)
        if a is None or a.error: continue
        for l in a.links:
            if l.kind != kind: continue
            if kind == 'pair': out.add((f, frozenset(l.key), frozenset(l.value)))
            elif kind == 'run': out.add((f, tuple(l.boxes)))
            else: out.add((f, tuple(tuple(c) for c in l.members)))
    return out
def forceset(x, kind, frames):
    out = set()
    for f in frames:
        fl = x.labels.frame(f)
        for l in fl.links:
            if l.kind != kind: continue
            loc_ = lambda r: parse_box_ref(r)[1]
            if kind == 'pair': out.add((f, frozenset(map(loc_, l.key)), frozenset(map(loc_, l.value))))
            elif kind == 'run': out.add((f, tuple(map(loc_, l.boxes))))
    return out
def txt(x, f, ids): return ' + '.join(next((b.text[:30] for b in x.boxes[f].boxes if b.id == i), i) for i in sorted(ids))

print('\n== container placement (API targets that are also local targets; both runs, completed frames only)')
d, tot, detail = container_diff(loc, ref, done)
print(f'container differs: {len(d)} of {tot} targets = {100*len(d)/max(1,tot):.1f}%  per frame {detail}')
print('containers per record: api', round(np.mean([len(ref.ann[f].containers) for f in done]), 2), 'local', round(np.mean([len(loc.ann[f].containers) for f in done]), 2))
print('popups: api', sum(1 for f in done for c in ref.ann[f].containers if c.kind == 'popup'), 'local', sum(1 for f in done for c in loc.ann[f].containers if c.kind == 'popup'))
print('unassigned: api', sum(len(ref.ann[f].unassigned) for f in done), 'local', sum(len(loc.ann[f].unassigned) for f in done))
for f in done:
    print(f'  f{f}: api {[(c.kind, c.app[:18], c.name[:45]) for c in ref.ann[f].containers]}')
    print(f'       27b {[(c.kind, c.app[:18], c.name[:45]) for c in loc.ann[f].containers]}')

print('\n== links (records of the completed frames)')
for kind in ('pair', 'run', 'record'):
    rs = linkset(ref, kind, done); ls = linkset(loc, kind, done)
    print(f'{kind}: api {len(rs)} local {len(ls)} reproduced {len(rs & ls)} = {100*len(rs&ls)/max(1,len(rs)):.1f}% of the API\'s; local extra (not in API record) {len(ls - rs)}')
rp = linkset(ref, 'pair', done); lp = linkset(loc, 'pair', done)
print('pairs in force per frame (labels resolved through lifetimes, both runs):')
rf = forceset(ref, 'pair', done); lf = forceset(loc, 'pair', done)
print(f'  api {len(rf)} local {len(lf)} common {len(rf & lf)} = {100*len(rf&lf)/max(1,len(rf)):.1f}% of the API\'s in-force pairs')
print('API pairs (record-level) the local did not make:')
for f, k, v in sorted(rp - lp, key=lambda t: t[0]): print(f'   f{f}  {txt(ref, f, k)}  =>  {txt(ref, f, v)}')
print('local pairs (record-level) not in the API record:')
for f, k, v in sorted(lp - rp, key=lambda t: t[0]): print(f'   f{f}  {txt(loc, f, k)}  =>  {txt(loc, f, v)}')

print('\n== repairs, validity, tokens')
for n, x in (('api', ref), ('27b', loc)):
    rk = Counter()
    for f in done: rk.update(x.ann[f].repair_counts)
    clashes = sum(x.ann[f].label_clashes for f in done)
    print(f'{n}: repairs {sum(rk.values())} {dict(rk)}; label clashes {clashes}; relinked (whole run) {x.labels.relinked}')
cdir = LOCAL / 'cache'
calls = [json.loads(p.read_text()) for p in sorted(cdir.glob('*.json'))] if cdir.exists() else []
calls = [c for c in calls if c['request'].get('stage') == 'annotate']
print(f'local cache: {len(calls)} annotate calls, {sum(1 for c in calls if not c["response"].get("error"))} parsed (valid JSON against the schema), errors: {[c["response"].get("error")[:80] for c in calls if c["response"].get("error")]}')

print('\n== cost for the completed frames (annotate stage only, both runs)')
pin, pout, pcache = PRICES['claude-opus-5']
au = Counter()
for f in done:
    for k, v in ref.ann[f].usage.items(): au[k] += v or 0
api_usd = (au['input_tokens'] * pin + au['output_tokens'] * pout + au['cache_read_input_tokens'] * pcache + au['cache_creation_input_tokens'] * pin * CACHE_WRITE_MULTIPLIER) / 1e6
lu = Counter()
for f in done:
    for k, v in loc.ann[f].usage.items(): lu[k] += v or 0
loc_usd = (lu['input_tokens'] * QWEN_PRICE[0] + lu['output_tokens'] * QWEN_PRICE[1]) / 1e6
print(f'api  usage {dict(au)}  ${api_usd:.4f} = ${api_usd/len(done):.4f}/frame (Opus 5 list: ${pin}/M in, ${pout}/M out, ${pcache}/M cache read, cache write x{CACHE_WRITE_MULTIPLIER})')
print(f'27b  usage {dict(lu)}  ${loc_usd:.4f} = ${loc_usd/len(done):.4f}/frame at OpenRouter Qwen3.8-27B ${QWEN_PRICE[0]}/M prompt, ${QWEN_PRICE[1]}/M completion')
print(f'ratio api/27b = {api_usd/max(1e-9,loc_usd):.1f}x')
pt = [loc.ann[f].usage.get('input_tokens', 0) for f in done]; ct = [loc.ann[f].usage.get('output_tokens', 0) for f in done]
print(f'27b per call: prompt mean {np.mean(pt):.0f} ({min(pt)}-{max(pt)}), completion mean {np.mean(ct):.0f} ({min(ct)}-{max(ct)})')
pt = [ref.ann[f].usage.get('input_tokens', 0) + ref.ann[f].usage.get('cache_read_input_tokens', 0) + ref.ann[f].usage.get('cache_creation_input_tokens', 0) for f in done]; ct = [ref.ann[f].usage.get('output_tokens', 0) for f in done]
print(f'api per call: prompt (incl. cached) mean {np.mean(pt):.0f} ({min(pt)}-{max(pt)}), completion mean {np.mean(ct):.0f} ({min(ct)}-{max(ct)})')

print('\n== popups: the toast (f22, f23), the Add endpoint panel (f15-21), the search dropdown (f23, f24), the tooltip (f29)')
def cont_of(a, box):
    cid = next((x.container for x in a.assign if x.box == box), None)
    return next((c for c in a.containers if c.id == cid), None)
for f in [x for x in (15, 16, 18, 19, 20, 21, 22, 23, 24, 29) if x in done]:
    ra, la = ref.ann[f], loc.ann[f]
    pop_boxes = [b for b in ra.targets if (c := cont_of(ra, b)) and c.kind == 'popup']
    inpop = [b for b in pop_boxes if (c := cont_of(la, b)) and c.kind == 'popup']
    print(f'  f{f}: API popup boxes {len(pop_boxes)} of {len(ra.targets)} targets -> local put {len(inpop)} in a popup; local popups {[c.name[:45] for c in la.containers if c.kind == "popup"]}; API popups {[c.name[:45] for c in ra.containers if c.kind == "popup"]}')
    if pop_boxes: print('     API popup boxes:', txt(ref, f, pop_boxes[:8]))
    lpop = [b for b in la.targets if (c := cont_of(la, b)) and c.kind == 'popup']
    if lpop: print('     local popup boxes:', txt(loc, f, lpop[:8]))

print('\n== sign-in dialog, frame 33')
if 33 in done:
    for n, x in (('api', ref), ('27b', loc)):
        a = x.ann[33]; am = assign_map(a)
        print(f'  {n}: containers {[(c.kind, c.app, c.name, c.owner) for c in a.containers]}; targets {len(a.targets)}; assigned per container {Counter(am[b] for b in a.targets if b in am)}; unassigned {a.unassigned}')
        print(f'     description: {(a.description or "")[:400]}')
else: print('  frame 33 not completed')

print('\n== pairs in force on the dense frames (for the by-eye check): a table frame and a form frame')
for f in [x for x in (22, 23, 27, 20, 21, 19, 16) if x in done]:
    for n, x in (('api', ref), ('27b', loc)):
        fl = x.labels.frame(f); ocr = {b.id: b.text for b in x.boxes[f].boxes}
        pairs = sorted({(frozenset(parse_box_ref(r)[1] for r in l.key), frozenset(parse_box_ref(r)[1] for r in l.value)) for l in fl.links if l.kind == 'pair'}, key=lambda t: sorted(t[0]))
        print(f'  f{f} {n}: {len(pairs)} distinct pairs in force')
        for k, v in pairs: print(f'      {"+".join(sorted(k))} {" + ".join(ocr.get(b, b)[:40] for b in sorted(k))}  =>  {"+".join(sorted(v))} {" + ".join(ocr.get(b, b)[:40] for b in sorted(v))}')

print('\n== descriptions mentioning the mechanism')
pat = re.compile(r"\bb\d{1,3}\b|\bbox(?:es)?\s+\d|\bnumbered\b|\boverlay\b|\bmagenta\b|\byellow (?:tag|label)|\btargets? (?:box|were|was|is|are|list)|no targets|\bannotat|image [12]\b|\bcoordinat|\brectangle|\bx0\b|\bthe list\b|\blisted\b|\bbox ids?\b|\bthe targets?\b|\bOCR\b|\bbounding\b", re.I)
for n, x in (('api', ref), ('27b', loc)):
    hits = [(f, x.ann[f].description[max(0, m.start() - 40):m.end() + 40]) for f in done if x.ann[f].description for m in [pat.search(x.ann[f].description)] if m]
    print(n, len(hits), hits[:4], 'no-description', [f for f in done if not x.ann[f].description])

print('\n== record (row) and run links on the table frames 13, 14, 22, 23, 27 (record-level), both runs')
for f in [x for x in (13, 14, 22, 23, 27) if x in done]:
    for n, x in (('api', ref), ('27b', loc)):
        a = x.ann[f]; ocr = {b.id: b.text for b in x.boxes[f].boxes}
        recs = [l for l in a.links if l.kind == 'record']; runs_ = [l for l in a.links if l.kind == 'run']
        print(f'  f{f} {n}: {len(recs)} records, {len(runs_)} runs, {sum(1 for l in a.links if l.kind == "pair")} pairs in the record')
        for l in recs: print('      ROW ' + ' | '.join('+'.join(ocr.get(b, b)[:22] for b in cell) for cell in l.members) + (f'   header {[ocr.get(b, b)[:15] for b in l.header]}' if l.header else ''))
        for l in runs_: print('      RUN ' + ' | '.join(ocr.get(b, b)[:25] for b in l.boxes))
