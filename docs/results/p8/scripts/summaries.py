"""Summaries: counts and texts side by side. Free: reads files only."""
import json, os, sys
ROOT='<repo>'
RUNS={
 'O none r1':'runs/eval/p4/full-none-r1','O none r2':'runs/eval/p4/full-none-r2',
 'S none r1':'runs/eval/p8/full-none-sonnet5-r1','S none r2':'runs/eval/p8/full-none-sonnet5-r2',
 'O inc r1':'runs/eval/p4/full-inc-transcribing-r1','O inc r2':'runs/eval/p4/full-inc-transcribing-r2',
 'S inc r1':'runs/eval/p8/full-inc-transcribing-sonnet5-r1','S inc r2':'runs/eval/p8/full-inc-transcribing-sonnet5-r2'}
def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
full='--full' in sys.argv
print('| run | steps | sections | summarize calls | invalid_refs | low_conf | seg conf not high | mean step description chars | video description chars |'); print('|'+'---|'*9)
for k,rd in RUNS.items():
    rd=os.path.join(ROOT,rd)
    if not os.path.exists(f'{rd}/video.json'): continue
    st=jl(f'{rd}/steps.jsonl'); se=jl(f'{rd}/sections.jsonl'); v=json.load(open(f'{rd}/video.json')); m=json.load(open(f'{rd}/manifest.json'))['stages']['summarize']
    nothigh=sum(1 for x in st+se+[v] if x.get('segmentation_conf')!='high')
    print(f"| {k} | {len(st)} | {len(se)} | {m.get('calls')} | {m.get('invalid_refs')} | {m.get('low_conf')} | {nothigh} | {sum(len(x['description']) for x in st)/len(st):.0f} | {len(v['description'])} |")
for k,rd in RUNS.items():
    rd=os.path.join(ROOT,rd)
    if not os.path.exists(f'{rd}/video.json'): continue
    st=jl(f'{rd}/steps.jsonl'); se=jl(f'{rd}/sections.jsonl'); v=json.load(open(f'{rd}/video.json'))
    print(); print('=====',k); print('VIDEO:',v['label']); print(v['description'])
    print('SECTIONS:')
    for x in se: print(f"  {x['id']} f{x['frames'][0]}-{x['frames'][1]}: {x['label']}"+(('\n      '+x['description']) if full else ''))
    print('STEPS:')
    for x in st: print(f"  {x['id']} f{x['frames'][0]}-{x['frames'][1]}: {x['label']}"+(('\n      '+x['description']) if full else ''))
