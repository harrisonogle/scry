"""P10 cost table in P3's form. Mean of repeats per reference x scale, smoke | span2."""
import json
from collections import defaultdict
ROOT='/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval/p10'
REFS=['coords100','coords067','coords050','ids100','ids067','ids050']
P3={'smoke':0.0782,'span2':0.0614}
tot=0; res={}
for span in ['smoke','span2']:
    print(f'== {span}')
    print('ref | calls targ | err/terr | repairs(kinds) | clash | in/call (cache_create,cache_read,uncached) | out/call | cost r1/r2 | $/frame | $/video | wall_s | status')
    for s in REFS:
        rows=[]
        for r in (1,2):
            d=f'{ROOT}/{span}-{s}-r{r}'
            m=json.load(open(d+'/manifest.json'))['stages']['annotate']; e=json.load(open(d+'/evalrun.json')); rows.append((m,e))
        avg=lambda f: sum(f(m,e) for m,e in rows)/len(rows)
        kinds=defaultdict(float)
        for m,e in rows:
            for k,v in m.get('repair_counts',{}).items(): kinds[k]+=v/len(rows)
        u=lambda m:m['usage']
        inc=avg(lambda m,e:(u(m)['input_tokens']+u(m)['cache_read_input_tokens']+u(m)['cache_creation_input_tokens'])/m['calls'])
        outc=avg(lambda m,e:u(m)['output_tokens']/m['calls'])
        pf=avg(lambda m,e:m['cost_per_frame_usd'])
        res[(span,s)]=dict(inc=inc,outc=outc,pf=pf,pf_each=[m['cost_per_frame_usd'] for m,e in rows],cost=[m['cost_usd'] for m,e in rows])
        line=[s,f"{avg(lambda m,e:m['calls']):.0f} {avg(lambda m,e:m['targets']):.0f}",
              '/'.join(str(m['errors']) for m,e in rows)+' '+'/'.join(str(m['transient_errors']) for m,e in rows),
              '/'.join(str(m['repairs']) for m,e in rows)+' '+','.join(f'{k}:{v:g}' for k,v in sorted(kinds.items())),
              '/'.join(str(m['label_clashes']) for m,e in rows),
              f"{inc:.0f} ("+'/'.join(f"{u(m)['cache_creation_input_tokens']//m['calls']},{u(m)['cache_read_input_tokens']//m['calls']},{u(m)['input_tokens']//m['calls']}" for m,e in rows)+")",
              f"{outc:.0f} ("+'/'.join(f"{u(m)['output_tokens']//m['calls']}" for m,e in rows)+")",
              '/'.join(f"{m['cost_usd']:.3f}" for m,e in rows), f"{pf:.4f}", f"{pf*221:.2f}",
              '/'.join(f"{e['seconds'].get('annotate',0):.0f}" for m,e in rows),
              '/'.join(str(e.get('status')) for m,e in rows)+' cachehits='+'/'.join(str(m['cache']['hits']) for m,e in rows)+' lost='+'/'.join(str(m['usage_lost']) for m,e in rows)+' commit='+'/'.join(e['code']['git_commit'][:7]+('*' if e['code']['git_dirty'] else '') for m,e in rows)]
        tot+=sum(m['cost_usd'] for m,e in rows)
        print(' | '.join(line))
print('P10 annotate spend', round(tot,2))
print('\n== savings per frame (mean of repeats), smoke | span2: against ids100 of this phase and against P3 s100 (.0782 | .0614)')
for s in REFS:
    out=[s]
    for span in ['smoke','span2']:
        pf=res[(span,s)]['pf']; base=res[(span,'ids100')]['pf']; p3=P3[span]
        out.append(f"{span}: ${pf:.4f} vs ids100 ${base:.4f}: {pf-base:+.4f} ({100*(pf-base)/base:+.0f}%) x221 {221*(pf-base):+.2f}; vs P3 ${p3:.4f}: {pf-p3:+.4f} ({100*(pf-p3)/p3:+.0f}%) x221 {221*(pf-p3):+.2f}")
    print(' | '.join(out))
print('\n== repeat noise ($/frame, |r1-r2|)')
for s in REFS:
    print(s, ' | '.join(f"{span} {abs(res[(span,s)]['pf_each'][0]-res[(span,s)]['pf_each'][1]):.4f}" for span in ['smoke','span2']))

print('\n== warm-cache equivalent: cache_creation repriced as cache_read (5*1.25 - 0.5 = $5.75 per M saved), $/frame mean of repeats, and the same savings')
warm={}
for span in ['smoke','span2']:
    for s in REFS:
        pfs=[]
        for r in (1,2):
            m=json.load(open(f'{ROOT}/{span}-{s}-r{r}/manifest.json'))['stages']['annotate']
            pfs.append((m['cost_usd']-m['usage']['cache_creation_input_tokens']*5.75/1e6)/m['frames'])
        warm[(span,s)]=sum(pfs)/2
for s in REFS:
    out=[s]
    for span in ['smoke','span2']:
        pf=warm[(span,s)]; base=warm[(span,'ids100')]; p3=P3[span]
        out.append(f"{span}: ${pf:.4f} (x221 {pf*221:.2f}) vs ids100 ${base:.4f}: {pf-base:+.4f} ({100*(pf-base)/base:+.0f}%); vs P3 ${p3:.4f}: {100*(pf-p3)/p3:+.0f}%")
    print(' | '.join(out))
