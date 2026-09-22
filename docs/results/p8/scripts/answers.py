"""Answers: labels per run and type, tool use, failures. Free: reads files only."""
import json, os, sys, collections
ROOT='<repo>'
RUNS={
 'O none r1':'runs/eval/p4/full-none-r1','O none r2':'runs/eval/p4/full-none-r2',
 'S none r1':'runs/eval/p8/full-none-sonnet5-r1','S none r2':'runs/eval/p8/full-none-sonnet5-r2',
 'O inc r1':'runs/eval/p4/full-inc-transcribing-r1','O inc r2':'runs/eval/p4/full-inc-transcribing-r2',
 'S inc r1':'runs/eval/p8/full-inc-transcribing-sonnet5-r1','S inc r2':'runs/eval/p8/full-inc-transcribing-sonnet5-r2'}
TYPES={'a exact string':[4,10,11,12,14,15,16,19],'b when':[3,13],'c paraphrase':[1,7,9,12],'d value in several states':[5,6,7,8,10,14,17,18,19,20],'e order':[21,22],'f negative':[23,24,25,26,27],'untyped (Q2)':[2]}
SCORE={'correct':1.0,'partial':0.5,'wrong':0.0}
def jl(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
D={}
for k,rd in RUNS.items():
    a=jl(os.path.join(ROOT,rd,'answers.jsonl')); j=jl(os.path.join(ROOT,rd,'judgments.jsonl'))
    if a: D[k]={'a':{x['qid']:x for x in a},'j':{x['qid']:x for x in j}}
names=list(D)
print('## labels'); print('| Q | '+' | '.join(names)+' |'); print('|---|'+'---|'*len(names))
for q in range(1,28):
    qid=f'Q{q}'; print(f'| {qid} | '+' | '.join((D[k]['j'].get(qid,{}).get('label') or '—') for k in names)+' |')
print(); print('## score per run: positive, negative, all')
for k in names:
    js=D[k]['j']
    pos=[SCORE[js[f'Q{q}']['label']] for q in range(1,23) if f'Q{q}' in js and js[f'Q{q}'].get('label') in SCORE]; neg=[SCORE[js[f'Q{q}']['label']] for q in range(23,28) if f'Q{q}' in js and js[f'Q{q}'].get('label') in SCORE]
    print(f'  {k}: positive {sum(pos)}/{len(pos)}  negative {sum(neg)}/{len(neg)}  all {sum(pos)+sum(neg)}/{len(pos)+len(neg)}  labels {dict(collections.Counter(x.get("label") for x in js.values()))} judge errors {sum(1 for x in js.values() if x.get("error"))}')
print(); print('## score and $ per question by type (a question can be in two types)')
print('| type | n | '+' | '.join(names)+' |'); print('|---|---|'+'---|'*len(names))
for t,qs in TYPES.items():
    row=[]
    for k in names:
        js=D[k]['j']; an=D[k]['a']
        sc=[SCORE.get(js.get(f'Q{q}',{}).get('label'),None) for q in qs]; sc=[s for s in sc if s is not None]
        dl=[an[f'Q{q}']['dollars'] for q in qs if f'Q{q}' in an]
        row.append('%s/%d $%.3f'%(('%g'%sum(sc)),len(sc),sum(dl)/len(dl) if dl else float('nan')))
    print(f'| {t} | {len(qs)} | '+' | '.join(row)+' |')
print(); print('## tool use per run')
print('| run | answers | opened frames (answers) | frames opened / answer | get_frame | redecode | search | get_node | get_transitions | calls / answer | turns / answer | zero-result searches | zero-result other | stops | errors | in tok / q | out tok / q | $ / q | s / q |')
print('|'+'---|'*19)
for k in names:
    an=list(D[k]['a'].values()); n=len(an)
    cnt=collections.Counter(c['name'] for a in an for c in a['calls'])
    opened=sum(1 for a in an if any(c['name'] in ('get_frame','redecode') and c.get('results') for c in a['calls']))
    nfr=sum(len({c['input'].get('frame') for c in a['calls'] if c['name']=='get_frame' and c.get('results')}) for a in an)
    zs=sum(1 for a in an for c in a['calls'] if c['name']=='search' and not c.get('results')); zo=sum(1 for a in an for c in a['calls'] if c['name']!='search' and not c.get('results'))
    ns=cnt['search']
    intok=sum(sum(a['usage'].get(x,0) for x in ('input_tokens','cache_read_input_tokens','cache_creation_input_tokens')) for a in an)/n; outtok=sum(a['usage'].get('output_tokens',0) for a in an)/n
    print(f"| {k} | {n} | {opened} | {nfr/n:.2f} | {cnt['get_frame']} | {cnt['redecode']} | {ns} | {cnt['get_node']} | {cnt['get_transitions']} | {sum(len(a['calls']) for a in an)/n:.2f} | {sum(a['turns'] for a in an)/n:.2f} | {zs}/{ns} | {zo} | {dict(collections.Counter(a.get('stop') for a in an))} | {sum(1 for a in an if a.get('error'))} | {intok:.0f} | {outtok:.0f} | {sum(a['dollars'] for a in an)/n:.4f} | {sum(a['seconds'] for a in an)/n:.1f} |")
print(); print('## every answer not fully correct')
for k in names:
    for q in range(1,28):
        qid=f'Q{q}'; j=D[k]['j'].get(qid); a=D[k]['a'].get(qid)
        if not a: print(f'### {k} {qid}: NO ANSWER'); continue
        if not j or j.get('label')!='correct':
            print(f'### {k} {qid}: label {j.get("label") if j else None} items {j.get("items") if j else None} stop={a.get("stop")} turns={a.get("turns")} error={a.get("error")} judge_error={j.get("error") if j else None}')
            print('QUESTION:',a['question']); print('ANSWER:',a['answer']); 
            if j: print('QUOTES:',json.dumps(j.get('quotes'),ensure_ascii=False))
            print('CALLS:'); 
            for c in a['calls']: print('   ',c['name'],json.dumps(c['input'],ensure_ascii=False),'->',c.get('results'))
            print()
