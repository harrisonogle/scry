"""Per-stage calls, tokens and cost: the local run (hosted rate) beside the API's run apportioned to the same frames.
Usage: stage_costs.py <local-run-dir> [first-last]"""
import json, sys
from collections import Counter
from pathlib import Path
from scry.costs import PRICES, CACHE_WRITE_MULTIPLIER
REF = Path('/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/v2/grouponly-100')
LOC = Path(sys.argv[1]); lo, hi = (int(v) for v in (sys.argv[2] if len(sys.argv) > 2 else '12-33').split('-'))
FR = set(range(lo, hi + 1)); nfr = len(FR)
QP, QC = 0.42, 3.00  # $/M prompt, completion: OpenRouter qwen/qwen3.8-27b (docs/results/local/report.md, read 2026-09-21)
pin, pout, pcache = PRICES['claude-opus-5']
def api_usd(u): return (u.get('input_tokens', 0) * pin + u.get('output_tokens', 0) * pout + u.get('cache_read_input_tokens', 0) * pcache + u.get('cache_creation_input_tokens', 0) * pin * CACHE_WRITE_MULTIPLIER) / 1e6
def loc_usd(u): return (u.get('input_tokens', 0) * QP + u.get('output_tokens', 0) * QC) / 1e6
def jl(p): return [json.loads(l) for l in open(p)] if p.exists() else []
def add(us):
    t = Counter()
    for u in us:
        for k, v in (u or {}).items(): t[k] += v or 0
    return t
rows = []
# annotate: one record per frame, usage on the record
ra = [r['usage'] for r in jl(REF / 'annotations.jsonl') if r['frame'] in FR]
la = [r['usage'] for r in jl(LOC / 'annotations.jsonl') if r.get('error') is None]
rows.append(('annotate', len(la), add(la), len(ra), add(ra), 'exact: the API records of frames %d-%d' % (lo, hi)))
# interpret: one record per transition; the API's T<n> is frame n-1 -> n, so the span's are T<lo+1>..T<hi>
ri = [r['usage'] for r in jl(REF / 'interpretations.jsonl') if lo + 1 <= int(r['id'][1:]) <= hi]
li = [r['usage'] for r in jl(LOC / 'interpretations.jsonl') if r.get('error') is None]
rows.append(('interpret', len(li), add(li), len(ri), add(ri), 'exact: the API records of transitions T%d-T%d' % (lo + 1, hi)))
# summarize: from the manifests; the API's apportioned by frames (22 of 80)
rm = json.load(open(REF / 'manifest.json'))['stages']; lm = json.load(open(LOC / 'manifest.json'))['stages']
rs = rm['summarize']; ls_ = lm.get('summarize', {})
frac = nfr / rm['decode']['emitted'] if rm.get('decode', {}).get('emitted') else nfr / 80
rsu = Counter({k: v * frac for k, v in rs['usage'].items()})
rows.append(('summarize', ls_.get('calls'), add([ls_.get('usage', {})]), round(rs['calls'] * frac, 1), rsu, 'API apportioned by frames: %d of 80 = x%.3f of %d calls, $%.4f' % (nfr, frac, rs['calls'], rs['cost_usd'])))
print('stage | local calls | local prompt tok | local completion tok | local $ (hosted rate) | API calls | API $ (Opus 5 list) | note')
tl = tr = 0
for name, lc, lu, rc, ru, note in rows:
    l_usd, r_usd = loc_usd(lu), api_usd(ru); tl += l_usd; tr += r_usd
    print(f'{name} | {lc} | {lu.get("input_tokens", 0)} | {lu.get("output_tokens", 0)} | ${l_usd:.4f} | {rc} | ${r_usd:.4f} | {note}')
print(f'TOTAL | | | | ${tl:.4f} = ${tl/nfr:.4f}/frame | | ${tr:.4f} = ${tr/nfr:.4f}/frame | ratio API/local {tr/max(tl,1e-9):.1f}x over {nfr} frames')
print('index:', {k: v for k, v in lm.get('index', {}).items() if k in ('by_level', 'nodes', 'seconds', 'embedder')})
for st in ('annotate', 'interpret', 'summarize'):
    e = lm.get(st, {}); print(st, 'manifest:', {k: e.get(k) for k in ('calls', 'transitions', 'interpreted', 'errors', 'seconds', 'cost_usd', 'usage', 'steps', 'sections', 'model')})
