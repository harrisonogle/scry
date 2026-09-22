"""Terminal targets (both Opus refs put them in a terminal window): in a PowerShell container of kind window / of kind popup / elsewhere.
Plus frame 171 b87 in all runs."""
import json
BASE='/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval/'
def isterm(c): 
    s=(c['app']+' '+c['name']).lower() if c else ''
    return 'powershell' in s or 'terminal' in s or 'pwsh' in s
def cont_of(a,b):
    cid=next((x['container'] for x in a['assign'] if x['box']==b),None)
    return next((c for c in a['containers'] if c['id']==cid),None)
for span in ('smoke','span2'):
    names=[f'p3/{span}-s100-r1',f'p3/{span}-s100-r2',f'p7/{span}-sonnet5-r1',f'p7/{span}-sonnet5-r2']
    R={n:{json.loads(l)['frame']:json.loads(l) for l in open(BASE+n+'/annotations.jsonl')} for n in names}
    term={(f,b) for f,a in R[names[0]].items() for b in a['targets'] if (c:=cont_of(a,b)) and c['kind']=='window' and isterm(c) and (c2:=cont_of(R[names[1]][f],b)) and c2['kind']=='window' and isterm(c2)}
    tframes=sorted({f for f,b in term})
    for n in names:
        w=p=e=0; recw=recp=0
        for f,b in term:
            c=cont_of(R[n][f],b)
            if c and isterm(c): 
                if c['kind']=='window': w+=1
                else: p+=1
            else: e+=1
        for f in tframes:
            ks={c['kind'] for c in R[n][f]['containers'] if isterm(c)}
            recw+='window' in ks; recp+=('popup' in ks and 'window' not in ks)
        print(f'{n}: terminal targets {len(term)} | in PowerShell window {w} | in PowerShell popup {p} | elsewhere {e} || records with terminal targets {len(tframes)}: PowerShell listed as window {recw}, as popup {recp}')
    if span=='span2':
        print('popup-kind frames sonnet r1:',[f for f in sorted(R[names[2]]) if any(isterm(c) and c['kind']=='popup' for c in R[names[2]][f]['containers'])])
        print('popup-kind frames sonnet r2:',[f for f in sorted(R[names[3]]) if any(isterm(c) and c['kind']=='popup' for c in R[names[3]][f]['containers'])])
        print('window-kind frames sonnet r1:',[f for f in sorted(R[names[2]]) if any(isterm(c) and c['kind']=='window' for c in R[names[2]][f]['containers'])])
        print('window-kind frames sonnet r2:',[f for f in sorted(R[names[3]]) if any(isterm(c) and c['kind']=='window' for c in R[names[3]][f]['containers'])])
        for n in names:
            a=R[n][171]; c=cont_of(a,'b87'); t=next((x['text'] for x in a['texts'] if x['box']=='b87'),None)
            links=[l for l in a['links'] if 'b87' in json.dumps(l)]
            print('F171 b87',n,'container',c['kind'],c['app'],'| read',repr(t),'| links',links)
