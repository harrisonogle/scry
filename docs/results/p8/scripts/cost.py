"""Cost, wall time, tokens, errors per stage. Usage: cost.py (reads P4 and P8 run dirs). Free: reads files only."""
import json, glob, os, sys, collections
ROOT='<repo>'
PRICES={"claude-opus-5":(5.0,25.0,0.5),"claude-sonnet-5":(2.0,10.0,0.2)}
def price(u,model):
    pin,pout,pc=PRICES[model]
    return (u.get('input_tokens',0)*pin+u.get('output_tokens',0)*pout+u.get('cache_read_input_tokens',0)*pc+u.get('cache_creation_input_tokens',0)*pin*1.25)/1e6
GROUPS={
 'opus none':['runs/eval/p4/full-none-r1','runs/eval/p4/full-none-r2'],
 'sonnet none':['runs/eval/p8/full-none-sonnet5-r1','runs/eval/p8/full-none-sonnet5-r2'],
 'opus inc':['runs/eval/p4/full-inc-transcribing-r1','runs/eval/p4/full-inc-transcribing-r2'],
 'sonnet inc':['runs/eval/p8/full-inc-transcribing-sonnet5-r1','runs/eval/p8/full-inc-transcribing-sonnet5-r2'],
}
def jl(p):
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def run_stats(rd):
    rd=os.path.join(ROOT,rd)
    m=json.load(open(f'{rd}/manifest.json')); ev=json.load(open(f'{rd}/evalrun.json'))
    out={'run':os.path.basename(rd),'status':ev['status'],'cold':ev['cold'],'resumed':ev['resumed'],'dirty':ev['code']['git_dirty'],'commit':ev['code']['git_commit'][:7],'started':ev['started'],'finished':ev['finished'],'error':ev.get('error')}
    cfg=json.load(open(f'{rd}/config.json')); out['cfg_model']=cfg['model']['model']
    for st in ('annotate','interpret','summarize'):
        s=m['stages'].get(st,{})
        u=s.get('usage',{}) or {}
        calls=s.get('calls') or s.get('interpreted') or 0
        o={'model':s.get('model'),'cost':s.get('cost_usd',0.0),'secs':ev['seconds'].get(st),'calls':calls,'usage':u,
           'errors':s.get('errors'),'cache':s.get('cache'),'usage_lost':(s.get('cache') or {}).get('usage_lost', s.get('usage_lost')),
           'skipped':s.get('skipped',False),'reprice':round(price(u,s.get('model')) ,4) if s.get('model') in PRICES else None,
           'invalid':s.get('invalid_citations', s.get('invalid_refs')), 'transient':s.get('transient_errors')}
        if st=='annotate': o.update({k:s.get(k) for k in ('repairs','repair_counts','failed_targets','mark_match','targets','label_clashes','skipped_frames')})
        if st=='interpret': o.update({'submitted':s.get('submitted'),'entered':s.get('entered')})
        if st=='summarize': o.update({'steps':s.get('steps'),'sections':s.get('sections'),'low_conf':s.get('low_conf')})
        out[st]=o
    out['secs_all']=ev['seconds']
    # stop reasons from the call cache
    stops=collections.Counter(); errs=collections.Counter(); models=collections.Counter()
    for f in glob.glob(f'{rd}/cache/*.json'):
        d=json.load(open(f)); rq=d['request']; rs=d['response']
        stops[(rq.get('stage'),rs.get('stop_reason'))]+=1
        models[(rq.get('stage'),rq.get('model'),rq.get('effort'))]+=1
        if rs.get('error'): errs[(rq.get('stage'),rs['error'][:80])]+=1
    out['stops']=dict((f'{a}:{b}',c) for (a,b),c in stops.items()); out['cache_errs']=dict((f'{a}:{b}',c) for (a,b),c in errs.items())
    out['cache_models']=dict((f'{a}:{b}:{c}',n) for (a,b,c),n in models.items())
    # per-record errors / models
    for fn,st in (('annotations.jsonl','annotate'),('interpretations.jsonl','interpret')):
        recs=jl(f'{rd}/{fn}')
        out[st]['rec_errors']=sum(1 for r in recs if r.get('error'))
        out[st]['rec_models']=dict(collections.Counter(r.get('model') for r in recs))
        if recs:
            out[st]['out_per_call']=sum((r.get('usage') or {}).get('output_tokens',0) for r in recs)/len(recs)
            out[st]['in_per_call']=sum(sum((r.get('usage') or {}).get(k,0) for k in ('input_tokens','cache_read_input_tokens','cache_creation_input_tokens')) for r in recs)/len(recs)
    # answers
    ans=jl(f'{rd}/answers.jsonl')
    if ans:
        n=len(ans)
        out['ask']={'n':n,'models':dict(collections.Counter(a.get('model') for a in ans)),'dollars':sum(a['dollars'] for a in ans),'secs':sum(a['seconds'] for a in ans),
          'in_per_q':sum(sum(a['usage'].get(k,0) for k in ('input_tokens','cache_read_input_tokens','cache_creation_input_tokens')) for a in ans)/n,
          'out_per_q':sum(a['usage'].get('output_tokens',0) for a in ans)/n,
          'reprice':sum(price(a['usage'],a['model']) for a in ans),
          'errors':sum(1 for a in ans if a.get('error')),'stops':dict(collections.Counter(a.get('stop') for a in ans)),
          'turns':sum(a.get('turns',0) for a in ans)/n,'calls':sum(len(a.get('calls',[])) for a in ans)/n,'secs_wall':ev['seconds'].get('ask')}
    sc_p=f'{rd}/scorecard.json'
    if os.path.exists(sc_p):
        sc=json.load(open(sc_p)); out['scorecost']=sc.get('cost'); out['q']={k:sc['questions'].get(k) for k in ('dollars_per_question','ask_dollars','judge_dollars','seconds_per_question')}
    jd=jl(f'{rd}/judgments.jsonl')
    out['judge']={'n':len(jd),'dollars':sum(j.get('dollars',0) for j in jd),'models':dict(collections.Counter(j.get('model') for j in jd)),'errors':sum(1 for j in jd if j.get('error'))}
    return out
if __name__=='__main__':
    res={}
    for g,rds in GROUPS.items():
        res[g]=[run_stats(r) for r in rds if os.path.exists(os.path.join(ROOT,r,'manifest.json')) and os.path.exists(os.path.join(ROOT,r,'evalrun.json'))]
    json.dump(res,open(os.path.join(os.path.dirname(__file__),'cost.json'),'w'),indent=1)
    def mean(xs): xs=[x for x in xs if x is not None]; return sum(xs)/len(xs) if xs else float('nan')
    print('group | stage | model | $ mean | s mean | calls | in/call | out/call | errors | usage_lost | reprice-ok')
    for g,rs in res.items():
        for st in ('annotate','interpret','summarize'):
            if not rs: continue
            print(g,'|',st,'|',set(r[st]['model'] for r in rs),'| %.4f | %.1f | %s | %.0f | %.0f | %s | %s | %s'%(
              mean([r[st]['cost'] for r in rs]),mean([r[st]['secs'] for r in rs]),[r[st]['calls'] for r in rs],
              mean([ (sum(r[st]['usage'].get(k,0) for k in ('input_tokens','cache_read_input_tokens','cache_creation_input_tokens'))/r[st]['calls']) if r[st]['calls'] else None for r in rs]),
              mean([ (r[st]['usage'].get('output_tokens',0)/r[st]['calls']) if r[st]['calls'] else None for r in rs]),
              [r[st]['errors'] for r in rs],[r[st]['usage_lost'] for r in rs],[abs((r[st]['reprice'] or 0)-r[st]['cost'])<0.001 for r in rs]))
        for r in rs:
            a=r.get('ask')
            print('   ',r['run'],r['status'],'cold' if r['cold'] else 'WARM','resumed' if r['resumed'] else '','DIRTY' if r['dirty'] else 'clean',r['commit'],'cfg',r['cfg_model'])
            print('      secs',r['secs_all'])
            if a: print('      ask: models %s $%.4f ($%.4f/q) reprice $%.4f  %.1f s/q  in/q %.0f out/q %.0f turns %.2f calls %.2f errors %d stops %s'%(a['models'],a['dollars'],a['dollars']/a['n'],a['reprice'],a['secs']/a['n'],a['in_per_q'],a['out_per_q'],a['turns'],a['calls'],a['errors'],a['stops']))
            print('      stops',r['stops'],'cache_errs',r['cache_errs'])
            print('      cache models',r['cache_models'])
            print('      judge',r['judge'],'scorecost',r.get('scorecost'))
            for st in ('annotate','interpret','summarize'):
                extra={k:v for k,v in r[st].items() if k in ('repairs','repair_counts','failed_targets','mark_match','targets','label_clashes','submitted','entered','steps','sections','low_conf','invalid','rec_errors','rec_models','transient','cache')}
                print('      ',st,extra)
