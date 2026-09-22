import json, sys, os
from collections import defaultdict
ROOT='<repo>/runs/eval/p3'
scales=['s100','s067','s050','s040','s030','s025','s020']
tot=0
for span in ['smoke','span2']:
    print(f'== {span}')
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
        line=[s,f"{calls:.0f}",f"{avg(lambda m,e:m['targets']):.0f}",
              '/'.join(str(m['errors']) for m,e in rows),'/'.join(str(m['transient_errors']) for m,e in rows),
              '/'.join(str(m['repairs']) for m,e in rows)+' '+','.join(f'{k}:{v:g}' for k,v in sorted(kinds.items())),
              '/'.join(str(m['label_clashes']) for m,e in rows),
              '/'.join(f"{m['mark_match']['hits']}of{m['mark_match']['total']}" for m,e in rows),
              f"{avg(lambda m,e:(u(m)['input_tokens']+u(m)['cache_read_input_tokens']+u(m)['cache_creation_input_tokens'])/m['calls']):.0f}",
              f"{avg(lambda m,e:u(m)['output_tokens']/m['calls']):.0f}",
              '/'.join(f"{m['cost_usd']:.3f}" for m,e in rows),
              f"{avg(lambda m,e:m['cost_per_frame_usd']):.4f}",
              f"{avg(lambda m,e:m['cost_per_frame_usd'])*221:.2f}",
              '/'.join(f"{e['seconds'].get('annotate',0):.0f}" for m,e in rows),
              'status='+'/'.join(str(e.get('status')) for m,e in rows),
              'cachehits='+'/'.join(str(m['cache']['hits']) for m,e in rows), 'lost='+'/'.join(str(m['usage_lost']) for m,e in rows)]
        tot+=sum(m['cost_usd'] for m,e in rows)
        print(' | '.join(line))
print('TOTAL spend so far', round(tot,2))
