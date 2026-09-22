"""Command metrics per run from scorecard.json. Free: reads files only."""
import json, os
ROOT='<repo>'
RUNS={
 'O none r1':'runs/eval/p4/full-none-r1','O none r2':'runs/eval/p4/full-none-r2',
 'S none r1':'runs/eval/p8/full-none-sonnet5-r1','S none r2':'runs/eval/p8/full-none-sonnet5-r2',
 'O inc r1':'runs/eval/p4/full-inc-transcribing-r1','O inc r2':'runs/eval/p4/full-inc-transcribing-r2',
 'S inc r1':'runs/eval/p8/full-inc-transcribing-sonnet5-r1','S inc r2':'runs/eval/p8/full-inc-transcribing-sonnet5-r2'}
S={}
for k,rd in RUNS.items():
    p=os.path.join(ROOT,rd,'scorecard.json')
    if os.path.exists(p): S[k]=json.load(open(p))
print('| run | found | exact.ocr | exact.vlm | exact.any | submitted | false run | first-appearance err (ocr / vlm / any) | submit err | ranks of the counting hit (#1,2,3,6,7,8,9) |'); print('|'+'---|'*10)
for k,sc in S.items():
    c=sc['commands']; r=c['rates']; ex=r['exact']
    f=lambda x: f'{x[0]}/{x[1]}' if x else '—'
    ranks=[e.get('rank') for e in c['entries'] if e.get('scorable')]
    fe=c['first_frame_error_abs_mean']
    print(f"| {k} | {f(r['found'])} | {f(ex.get('ocr'))} | {f(ex.get('vlm'))} | {f(ex.get('any'))} | {f(r['submitted'])} | {f(r['false_run'])} | {fe.get('ocr')} / {fe.get('vlm','—')} / {fe.get('any')} | {c['submit_frame_error_abs_mean']} | {ranks} |")
print()
for k,sc in S.items():
    c=sc['commands']
    for e in c['entries']:
        bad=[]
        if e.get('scorable'):
            if not e.get('found'): bad.append('NOT FOUND')
            if not e.get('submitted'): bad.append('NOT SUBMITTED')
            if e.get('submit_frame_error') not in (0,None): bad.append(f"submit_frame_error {e['submit_frame_error']}")
            ex=e.get('exact') or {}
            for rd_,v in ex.items():
                if v is False or (isinstance(v,dict) and v.get('exact') is False): bad.append(f'not exact.{rd_}')
        if bad: print(k,'#',e['n'],repr(e['text']),bad,json.dumps({x:e.get(x) for x in ('exact','first_frame_error','rank','level','node_id','claim','submit_frame_error')}))
    for nr in c['never_run']:
        if nr.get('false_run'): print(k,'FALSE RUN',nr)
print(); print('counters'); 
for k,sc in S.items(): print(' ',k,json.dumps(sc.get('counters')))
