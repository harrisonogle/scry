"""Per-frame token counts for the same frames under Opus 5 (P3 s100) and Sonnet 5 (P7); cache engagement; output chars per token;
stop reasons and errors from the call cache; price check."""
import json, glob, sys
from collections import Counter
BASE='/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval/'
sys.path.insert(0,'/Users/harrisonogle/src/harrisonogle/agentic-escort/src')
from scry.costs import estimate_cost, PRICES
def recs(p):
    return {json.loads(l)['frame']:json.loads(l) for l in open(BASE+p+'/annotations.jsonl')}
def tin(u): return u['input_tokens']+u['cache_read_input_tokens']+u['cache_creation_input_tokens']
for span in ('smoke','span2'):
    R={n:recs(n) for n in [f'p3/{span}-s100-r1',f'p3/{span}-s100-r2',f'p7/{span}-sonnet5-r1',f'p7/{span}-sonnet5-r2']}
    names=list(R)
    print(f'\n== {span}: per-frame total input tokens (uncached+cache read+cache write) | output tokens | answer chars (description+texts as stored)')
    print('frame targets | opus r1 in, r2 in | sonnet r1 in, r2 in | ratio S/O in | opus out r1,r2 | sonnet out r1,r2 | ratio S/O out')
    tot={n:[0,0] for n in names}
    for f in sorted(R[names[0]]):
        ins=[tin(R[n][f]['usage']) for n in names]; outs=[R[n][f]['usage']['output_tokens'] for n in names]
        for n,i,o in zip(names,ins,outs): tot[n][0]+=i; tot[n][1]+=o
        print(f"{f} {len(R[names[0]][f]['targets'])} | {ins[0]},{ins[1]} | {ins[2]},{ins[3]} | {(ins[2]+ins[3])/(ins[0]+ins[1]):.3f} | {outs[0]},{outs[1]} | {outs[2]},{outs[3]} | {(outs[2]+outs[3])/max(1,(outs[0]+outs[1])):.2f}")
    print('TOTAL', {n:tot[n] for n in names})
    print('ratio S/O input total', (tot[names[2]][0]+tot[names[3]][0])/(tot[names[0]][0]+tot[names[1]][0]), 'output total', (tot[names[2]][1]+tot[names[3]][1])/(tot[names[0]][1]+tot[names[1]][1]))
    print('\n-- cache engagement per record (cache_read>0 / cache_creation>0 / neither) and the sizes seen')
    for n in names:
        rd=[r['usage']['cache_read_input_tokens'] for r in R[n].values()]; cr=[r['usage']['cache_creation_input_tokens'] for r in R[n].values()]
        print(n, 'read>0:',sum(x>0 for x in rd),'create>0:',sum(x>0 for x in cr),'neither:',sum(1 for a,b in zip(rd,cr) if a==0 and b==0),'read sizes',Counter(rd).most_common(4),'create sizes',Counter(cr).most_common(4))
    print('\n-- call cache: stop reasons, errors, output chars per output token')
    for n in names:
        sr=Counter(); er=Counter(); ch=0; ot=0; models=Counter(); eff=Counter()
        for p in glob.glob(BASE+n+'/cache/*.json'):
            d=json.load(open(p)); 
            if d['request'].get('stage')!='annotate': continue
            sr[d['response'].get('stop_reason')]+=1; er[d['response'].get('error')]+=1; models[d['request'].get('model')]+=1; eff[d['request'].get('effort')]+=1
            ch+=len(d['response'].get('text') or ''); ot+=(d['response'].get('usage') or {}).get('output_tokens',0)
        print(n,'cache files',sum(sr.values()),'stop',dict(sr),'error',dict(er),'model',dict(models),'effort',dict(eff),f'answer chars {ch} out tokens {ot} chars/token {ch/max(1,ot):.2f} chars/call {ch/max(1,sum(sr.values())):.0f}')
    print('\n-- manifest: model, price check')
    for n in names:
        m=json.load(open(BASE+n+'/manifest.json'))['stages']['annotate']; e=json.load(open(BASE+n+'/evalrun.json'))
        u=m['usage']
        as_s=estimate_cost(u,'claude-sonnet-5'); as_o=estimate_cost(u,'claude-opus-5')
        print(n,'model',m['model'],'prompt',m['prompt_version'],'mode',m['mode'],'arm',m.get('arm'),'transcribe',m.get('transcribe'),'cost_usd',m['cost_usd'],'| priced as sonnet',as_s,'as opus',as_o,'| errors',m['errors'],'transient',m['transient_errors'],'failed_targets',m['failed_targets'],'skipped',m['skipped_frames'],'usage_lost',m['usage_lost'],'cache',m['cache'],'| status',e['status'],'dirty',e['code']['git_dirty'],e['code']['git_commit'][:7],'cold',e['cold'],'secs',e['seconds'],'overrides',e['overrides'])
        print('    usage',u, 'inputs', m['inputs'][-40:], 'config', m['config'][:12])
