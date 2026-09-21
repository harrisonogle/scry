"""Container sets per frame: kind, app, name, owner, covers, and how many targets each holds. Opus s100 beside Sonnet. Usage: conts.py <span> [frames]"""
import json, sys
from collections import Counter
BASE='/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval/'
span=sys.argv[1]; only=[int(x) for x in sys.argv[2].split(',')] if len(sys.argv)>2 else None
names=[f'p3/{span}-s100-r1',f'p3/{span}-s100-r2',f'p7/{span}-sonnet5-r1',f'p7/{span}-sonnet5-r2']
R={n:{json.loads(l)['frame']:json.loads(l) for l in open(BASE+n+'/annotations.jsonl')} for n in names}
sig=Counter()
for f in sorted(R[names[0]]):
    if only and f not in only: continue
    print(f'--- F{f} targets {len(R[names[0]][f]["targets"])}')
    for n in names:
        a=R[n][f]; cnt=Counter(x['container'] for x in a['assign'])
        print('  ',n.split('/')[1],'|',' ; '.join(f"{c['id']} {c['kind']} app={c['app']!r} name={c['name'][:45]!r} owner={c['owner']} covers={c['covers']} n={cnt.get(c['id'],0)}" + (f" rect={c.get('rect')}" if c.get('rect') else '') for c in a['containers']), '| unassigned', len(a['unassigned']))
print('\nSUMMARY per run: kinds, apps, owner set, covers set, popups with owner=None, containers with 0 boxes')
for n in names:
    k=Counter(); apps=Counter(); own=0; cov=0; pop_noown=0; empty=0; nrec=0; popnames=Counter()
    for f,a in R[n].items():
        cnt=Counter(x['container'] for x in a['assign']); nrec+=1
        for c in a['containers']:
            k[c['kind']]+=1; apps[(c['kind'],c['app'])]+=1
            own+= c['owner'] is not None; cov+= bool(c['covers'])
            if c['kind']=='popup': popnames[c['name'][:40]]+=1
            if c['kind']=='popup' and c['owner'] is None: pop_noown+=1
            if cnt.get(c['id'],0)==0: empty+=1
    print(n, dict(k), 'owner set',own,'covers set',cov,'popup without owner',pop_noown,'empty containers',empty)
    print('     apps', apps.most_common(12))
    print('     popup names', popnames.most_common(12))
