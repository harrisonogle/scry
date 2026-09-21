"""P3's cost.py, adapted: arm A (P3 s100/s067/s050) beside arm D (P5 d100/d067/d050)."""
import json, sys, os
from collections import defaultdict
BASE='/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval'
SETS=[('p3',['s100','s067','s050']),('p5',['d100','d067','d050'])]
res={}
for phase,scales in SETS:
    ROOT=f'{BASE}/{phase}'
    tot=0
    for span in ['smoke','span2']:
        print(f'== {phase} {span}')
        print('scale  calls targ err terr repairs(kinds) clash mark_match in/call out/call cost $/frame $/video wall_s')
        for s in scales:
            rows=[]
            for r in (1,2):
                d=f'{ROOT}/{span}-{s}-r{r}'
                try:
                    m=json.load(open(d+'/manifest.json'))['stages']['annotate']
                    e=json.load(open(d+'/evalrun.json'))
                except Exception as ex:
                    print(s,r,'MISSING',ex); continue
                rows.append((m,e))
            if not rows: continue
            def avg(f): return sum(f(m,e) for m,e in rows)/len(rows)
            kinds=defaultdict(float)
            for m,e in rows:
                for k,v in m.get('repair_counts',{}).items(): kinds[k]+=v/len(rows)
            u=lambda m:m['usage']
            calls=avg(lambda m,e:m['calls'])
            incall=avg(lambda m,e:(u(m)['input_tokens']+u(m)['cache_read_input_tokens']+u(m)['cache_creation_input_tokens'])/m['calls'])
            outcall=avg(lambda m,e:u(m)['output_tokens']/m['calls'])
            cpf=avg(lambda m,e:m['cost_per_frame_usd'])
            wall=avg(lambda m,e:e['seconds'].get('annotate',0))
            mm=avg(lambda m,e:100*m['mark_match']['hits']/max(1,m['mark_match']['total']))
            res[(phase,span,s[1:])]=dict(incall=incall,outcall=outcall,cpf=cpf,wall=wall,mm=mm,
                 cpfs=[m['cost_per_frame_usd'] for m,e in rows], mms=[100*m['mark_match']['hits']/max(1,m['mark_match']['total']) for m,e in rows],
                 usage=[u(m) for m,e in rows], cost=[m['cost_usd'] for m,e in rows])
            line=[s,f"{calls:.0f}",f"{avg(lambda m,e:m['targets']):.0f}",
                  '/'.join(str(m['errors']) for m,e in rows),'/'.join(str(m['transient_errors']) for m,e in rows),
                  '/'.join(str(m['repairs']) for m,e in rows)+' '+','.join(f'{k}:{v:g}' for k,v in sorted(kinds.items())),
                  '/'.join(str(m['label_clashes']) for m,e in rows),
                  '/'.join(f"{m['mark_match']['hits']}of{m['mark_match']['total']}" for m,e in rows),
                  f"{incall:.0f}", f"{outcall:.0f}",
                  '/'.join(f"{m['cost_usd']:.3f}" for m,e in rows),
                  f"{cpf:.4f}", f"{cpf*221:.2f}",
                  '/'.join(f"{e['seconds'].get('annotate',0):.0f}" for m,e in rows),
                  'status='+'/'.join(str(e.get('status')) for m,e in rows),
                  'cachehits='+'/'.join(str(m['cache']['hits']) for m,e in rows), 'lost='+'/'.join(str(m['usage_lost']) for m,e in rows)]
            tot+=sum(m['cost_usd'] for m,e in rows)
            print(' | '.join(line))
    print(f'TOTAL annotate spend {phase} (these scales)', round(tot,2))
print('\n== SIDE BY SIDE (mean of repeats; smoke | span2): D, A, D-A')
for sc in ['100','067','050']:
    for key,fmt in [('incall','{:.0f}'),('outcall','{:.0f}'),('cpf','{:.4f}'),('wall','{:.0f}'),('mm','{:.1f}')]:
        cells=[]
        for span in ['smoke','span2']:
            d=res.get(('p5',span,sc)); a=res.get(('p3',span,sc))
            if d and a: cells.append(f"D {fmt.format(d[key])} A {fmt.format(a[key])} diff {fmt.format(d[key]-a[key])} ({100*(d[key]-a[key])/a[key]:+.0f}%)")
            else: cells.append('missing')
        print(sc,key,' | '.join(cells))
    for span in ['smoke','span2']:
        d=res.get(('p5',span,sc)); a=res.get(('p3',span,sc))
        if d and a: print(sc,span,'$/video D',f"{d['cpf']*221:.2f}",'A',f"{a['cpf']*221:.2f}",'diff',f"{(d['cpf']-a['cpf'])*221:+.2f}")
print('\n== repeat noise ($/frame |r1-r2|, mark_match gap)')
for k,v in res.items():
    if len(v['cpfs'])==2: print(k, f"cost gap {abs(v['cpfs'][0]-v['cpfs'][1]):.4f}", f"mm {v['mms'][0]:.1f}/{v['mms'][1]:.1f} gap {abs(v['mms'][0]-v['mms'][1]):.1f}")
print('\n== usage detail')
for k,v in res.items():
    for i,uu in enumerate(v['usage']): print(k,'r%d'%(i+1),{a:b for a,b in uu.items() if isinstance(b,(int,float))}, 'cost',v['cost'][i])
