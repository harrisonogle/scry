"""P13 cost table in P3's form: per mode (ct = coords transcribing, cg = coords group-only) and scale, mean of repeats,
smoke | span2. Beside it P3's overlay transcribing at the same scale (runs/eval/p3) and P10's overlay group-only (ids)
where it exists (1.0, 0.67, 0.5), plus P10 coords100 and P12 coords067/050 (group-only, corrected listing, smoke only).
Savings against (a) the overlay at the same scale, (b) P3 s100, (c) P10 ids100. Cold and warm-equivalent
(cache creation repriced as cache read: (1.25 - 0.1) * $5/M = $5.75/M)."""
import json, sys
from collections import defaultdict
from pathlib import Path
E = Path('/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval')
SPANS = ['smoke', 'span2']
CT = ['ct100', 'ct067', 'ct050', 'ct040', 'ct030', 'ct025', 'ct020']
CG = ['cg040', 'cg030', 'cg025', 'cg020']
P3S = {'ct100': 's100', 'ct067': 's067', 'ct050': 's050', 'ct040': 's040', 'ct030': 's030', 'ct025': 's025', 'ct020': 's020'}
IDS = {'cg100': 'ids100', 'cg067': 'ids067', 'cg050': 'ids050'}
WARM_PER_M = 5.75

def load(phase, span, s, r):
    d = E / phase / f'{span}-{s}-r{r}'
    if not (d / 'manifest.json').exists(): return None
    m = json.load(open(d / 'manifest.json'))['stages'].get('annotate')
    e = json.load(open(d / 'evalrun.json'))
    if m is None: return None
    return m, e

def row(phase, span, s):
    rows = [x for r in (1, 2) if (x := load(phase, span, s, r))]
    if not rows: return None
    n = len(rows); avg = lambda f: sum(f(m, e) for m, e in rows) / n
    u = lambda m: m['usage']
    kinds = defaultdict(float)
    for m, e in rows:
        for k, v in m.get('repair_counts', {}).items(): kinds[k] += v / n
    out = dict(
        n=n, calls=avg(lambda m, e: m['calls']), targets=avg(lambda m, e: m['targets']),
        errors=[m['errors'] for m, e in rows], terrors=[m['transient_errors'] for m, e in rows],
        repairs=[m['repairs'] for m, e in rows], kinds=dict(kinds), clash=[m['label_clashes'] for m, e in rows],
        mark=[(m['mark_match']['hits'], m['mark_match']['total']) if m['mark_match'] else None for m, e in rows],
        inc=avg(lambda m, e: (u(m)['input_tokens'] + u(m)['cache_read_input_tokens'] + u(m)['cache_creation_input_tokens']) / m['calls']),
        inc_parts=[(u(m)['cache_creation_input_tokens'] // m['calls'], u(m)['cache_read_input_tokens'] // m['calls'], u(m)['input_tokens'] // m['calls']) for m, e in rows],
        creation_calls=[round(u(m)['cache_creation_input_tokens'] / max(1, u(m)['cache_creation_input_tokens'] + u(m)['cache_read_input_tokens']) * m['calls'], 1) for m, e in rows],
        outc=avg(lambda m, e: u(m)['output_tokens'] / m['calls']), outc_each=[u(m)['output_tokens'] / m['calls'] for m, e in rows],
        cost=[m['cost_usd'] for m, e in rows], pf=avg(lambda m, e: m['cost_per_frame_usd']), pf_each=[m['cost_per_frame_usd'] for m, e in rows],
        warm=avg(lambda m, e: (m['cost_usd'] - u(m)['cache_creation_input_tokens'] * WARM_PER_M / 1e6) / m['frames']),
        wall=[e['seconds'].get('annotate', 0) for m, e in rows], status=[e.get('status') for m, e in rows],
        hits=[m['cache']['hits'] for m, e in rows], lost=[m['usage_lost'] for m, e in rows],
        commit=[e['code']['git_commit'][:7] + ('*' if e['code']['git_dirty'] else '') for m, e in rows],
        cold=[e.get('cold') for m, e in rows])
    return out

R = {}
for span in SPANS:
    for s in CT + CG: R[(span, 'p13', s)] = row('p13', span, s)
    for s in P3S.values(): R[(span, 'p3', s)] = row('p3', span, s)
    for s in ['ids100', 'ids067', 'ids050', 'coords100', 'coords067', 'coords050']: R[(span, 'p10', s)] = row('p10', span, s)
    for s in ['coords067', 'coords050']: R[(span, 'p12', s)] = row('p12', span, s)

fmt = lambda v, d=4: '-' if v is None else f'{v:.{d}f}'
print('== P13 raw, per span (mean of repeats; lists are r1/r2)')
for span in SPANS:
    print(f'-- {span}')
    print('run | n | calls targ | err terr | repairs (kinds) | mark_match | in/call (create,read,uncached per call) | calls that wrote the cache | out/call (r1/r2) | cost r1/r2 | $/frame cold | $/frame warm-eq | $/video cold | wall s | status | hits lost | commit')
    for s in CT + CG:
        x = R[(span, 'p13', s)]
        if x is None: print(s, 'MISSING'); continue
        mm = '/'.join('-' if m is None else f'{m[0]}of{m[1]}' for m in x['mark'])
        print(f"{s} | {x['n']} | {x['calls']:.0f} {x['targets']:.0f} | {x['errors']} {x['terrors']} | {x['repairs']} {x['kinds']} | {mm} | {x['inc']:.0f} {x['inc_parts']} | {x['creation_calls']} | {x['outc']:.0f} ({'/'.join(f'{o:.0f}' for o in x['outc_each'])}) | {'/'.join(f'{c:.3f}' for c in x['cost'])} | {x['pf']:.4f} | {x['warm']:.4f} | {x['pf']*221:.2f} | {x['wall']} | {x['status']} | {x['hits']} {x['lost']} | {x['commit']}")
spend = sum(sum(x['cost']) for k, x in R.items() if k[1] == 'p13' and x)
print('P13 annotate spend so far', round(spend, 2), 'runs', sum(x['n'] for k, x in R.items() if k[1] == 'p13' and x))

def pair(key):
    return [R.get((span,) + key) for span in SPANS]

print('\n== COST TABLE (cold, as billed), smoke | span2. $/video = $/frame x 221. Savings: vs overlay same scale (P3 s for ct, P10 ids for cg), vs P3 s100 (.0782 | .0614), vs P10 ids100 (.0570 | .0514).')
print('mode scale | in tok/call | out tok/call | $/frame | $/video || overlay same scale $/frame | saving $ (%) || vs P3 s100: saving $ (%) || vs P10 ids100: saving $ (%)')
base_s100 = pair(('p3', 's100')); base_ids100 = pair(('p10', 'ids100'))
def sav(pf, base): return '-' if pf is None or base is None else f'{base - pf:+.4f} ({100 * (base - pf) / base:+.0f}%)'
def line(label, xs, ov):
    inc = ' | '.join(fmt(x['inc'] if x else None, 0) for x in xs)
    outc = ' | '.join(fmt(x['outc'] if x else None, 0) for x in xs)
    pf = ' | '.join(fmt(x['pf'] if x else None) for x in xs)
    pv = ' | '.join(fmt(x['pf'] * 221 if x else None, 2) for x in xs)
    opf = ' | '.join(fmt(o['pf'] if o else None) for o in ov)
    s_ov = ' | '.join(sav(x['pf'] if x else None, o['pf'] if o else None) for x, o in zip(xs, ov))
    s_100 = ' | '.join(sav(x['pf'] if x else None, b['pf'] if b else None) for x, b in zip(xs, base_s100))
    s_ids = ' | '.join(sav(x['pf'] if x else None, b['pf'] if b else None) for x, b in zip(xs, base_ids100))
    print(f'{label} | {inc} | {outc} | {pf} | {pv} || {opf} | {s_ov} || {s_100} || {s_ids}')
for s in CT: line(f'coords transcribing {s[2:]}', pair(('p13', s)), pair(('p3', P3S[s])))
print('-- overlay transcribing (P3), for reference')
for s in CT: line(f'overlay transcribing {s[2:]}', pair(('p3', P3S[s])), [None, None])
print('-- group-only coords: P10 coords100 (old listing), P12 coords067/050 (corrected, smoke only; span2 = P10 old listing), P13 cg')
line('coords group-only 100 (P10)', pair(('p10', 'coords100')), pair(('p10', 'ids100')))
line('coords group-only 067 (P12 smoke | P10 span2)', [R[('smoke', 'p12', 'coords067')], R[('span2', 'p10', 'coords067')]], pair(('p10', 'ids067')))
line('coords group-only 050 (P12 smoke | P10 span2)', [R[('smoke', 'p12', 'coords050')], R[('span2', 'p10', 'coords050')]], pair(('p10', 'ids050')))
for s in CG: line(f'coords group-only {s[2:]}', pair(('p13', s)), [None, None])
print('-- overlay group-only (P10 ids), for reference')
for s in ['ids100', 'ids067', 'ids050']: line(f'overlay group-only {s[3:]}', pair(('p10', s)), [None, None])

print('\n== WARM-EQUIVALENT $/frame (cache creation repriced as read), same layout; P3 s100 warm and P10 ids100 warm as the bases')
print('mode scale | $/frame warm | $/video warm || overlay same scale warm | saving || vs P3 s100 warm | vs P10 ids100 warm')
b100 = [b['warm'] if b else None for b in base_s100]; bids = [b['warm'] if b else None for b in base_ids100]
def wline(label, xs, ov):
    pf = ' | '.join(fmt(x['warm'] if x else None) for x in xs)
    pv = ' | '.join(fmt(x['warm'] * 221 if x else None, 2) for x in xs)
    opf = ' | '.join(fmt(o['warm'] if o else None) for o in ov)
    s_ov = ' | '.join(sav(x['warm'] if x else None, o['warm'] if o else None) for x, o in zip(xs, ov))
    s_100 = ' | '.join(sav(x['warm'] if x else None, b) for x, b in zip(xs, b100))
    s_ids = ' | '.join(sav(x['warm'] if x else None, b) for x, b in zip(xs, bids))
    print(f'{label} | {pf} | {pv} || {opf} | {s_ov} || {s_100} || {s_ids}')
for s in CT: wline(f'coords transcribing {s[2:]}', pair(('p13', s)), pair(('p3', P3S[s])))
for s in CT: wline(f'overlay transcribing {s[2:]}', pair(('p3', P3S[s])), [None, None])
wline('coords group-only 100 (P10)', pair(('p10', 'coords100')), pair(('p10', 'ids100')))
wline('coords group-only 067 (P12 | P10)', [R[('smoke', 'p12', 'coords067')], R[('span2', 'p10', 'coords067')]], pair(('p10', 'ids067')))
wline('coords group-only 050 (P12 | P10)', [R[('smoke', 'p12', 'coords050')], R[('span2', 'p10', 'coords050')]], pair(('p10', 'ids050')))
for s in CG: wline(f'coords group-only {s[2:]}', pair(('p13', s)), [None, None])
for s in ['ids100', 'ids067', 'ids050']: wline(f'overlay group-only {s[3:]}', pair(('p10', s)), [None, None])
print('P3 s100 warm', [fmt(b) for b in b100], 'P3 s100 cold', [fmt(b['pf'] if b else None) for b in base_s100], '; P10 ids100 warm', [fmt(b) for b in bids], 'cold', [fmt(b['pf'] if b else None) for b in base_ids100])

print('\n== repeat noise |r1-r2| $/frame (cold), smoke | span2')
for s in CT + CG:
    xs = pair(('p13', s))
    print(s, ' | '.join('-' if not x or x['n'] < 2 else f"{abs(x['pf_each'][0] - x['pf_each'][1]):.4f}" for x in xs))
