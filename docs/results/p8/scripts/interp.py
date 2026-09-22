"""interpret on the terminal part (T155..T207): entered_text and submitted against a by-eye truth table (crops in scratchpad/crops).
Free: reads files only."""
import json, os, re, sys, collections
ROOT='/Users/harrisonogle/src/harrisonogle/agentic-escort'
RUNS={
 'O none r1':'runs/eval/p4/full-none-r1','O none r2':'runs/eval/p4/full-none-r2',
 'O inc r1':'runs/eval/p4/full-inc-transcribing-r1','O inc r2':'runs/eval/p4/full-inc-transcribing-r2',
 'S none r1':'runs/eval/p8/full-none-sonnet5-r1','S none r2':'runs/eval/p8/full-none-sonnet5-r2',
 'S inc r1':'runs/eval/p8/full-inc-transcribing-sonnet5-r1','S inc r2':'runs/eval/p8/full-inc-transcribing-sonnet5-r2'}
CD='kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1'
EX='kubectl expose deployment kodekloudapp --type=LoadBalancer --port=80 --target-port=80'
TYPED={155:'a',157:'az account show',161:'az c',162:'az configure --defaults group=RG1-KodeKloud-AKS',163:'az configure --defaults group=RG1-KodeKloud-AKS',
 165:'az ak',166:'az aks get',167:'az aks get-Credentials --name AKS1-KodeKloudApp',168:'az aks get-Credentials --name AKS1-KodeKloudApp',
 172:'kubect',173:'kubectl',174:'kubectl ',175:'kubectl config',176:'kubectl config current-context',178:'kubect',179:'kubectl get ',
 185:'kubectl get deplo',189:'kubectl ',190:'kubectl create deployment',191:CD,192:CD,193:CD,194:CD,195:CD+' --',196:CD+' --replicas',197:CD+' --replicas=1',
 199:'kubect',200:'kubectl get deplo',205:'ku',206:'kubect',207:'kubectl ',208:'kubectl expose ',209:EX,211:'kubectl ',212:'kubectl get s'}
SUGG={155:'az login',161:'az configure --defaults group=RG1-KodeKloud-AKS',165:'az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2',
 166:'az aks get-Credentials --name AKS1-KodeKloudApp',172:'kubectl rollout undo deployment/kodekloudapp',173:'kubectl rollout undo deployment/kodekloudapp',
 174:'kubectl rollout undo deployment/kodekloudapp',175:'kubectl config current-context',178:'kubectl config current-context',179:'kubectl get svc',
 185:'kubectl get deployment',189:'kubectl get pods',190:CD,199:CD+' --replicas=1',200:'kubectl get deployment',205:'kubectl get pods',206:'kubectl get pods',207:'kubectl get pods',208:EX,211:EX,212:'kubectl get svc'}
SUBMIT={158:'az account show',164:'az configure --defaults group=RG1-KodeKloud-AKS',169:'az aks get-Credentials --name AKS1-KodeKloudApp',170:'Y',171:'y',
 177:'kubectl config current-context',180:'kubectl get nodes',186:'kubectl get deployment',187:'kubectl get pods',198:CD+' --replicas=1',201:'kubectl get deployment',203:'kubectl get pods',210:EX,213:'kubectl get service'}
NEVER=['az login','az aks scale','kubectl rollout undo','kubectl get svc']
def norm(s): return re.sub(r'\s+',' ',(s or '')).strip()
def classify(n, ent):
    typed=norm(TYPED[n]); sug=norm(SUGG[n]); e=norm(ent)
    if ent is None: return 'none'
    if e.lower()==typed.lower(): return 'typed'
    if e.lower()==sug[:len(typed)+1].lower() or e.lower()==sug[:len(TYPED[n])+1].strip().lower(): return 'cursor-char'
    if e.lower().startswith(typed.lower()) and sug.lower().startswith(e.lower()): return 'SUGGESTION' if len(e)-len(typed)>=2 else 'cursor-char'
    if e.lower()==sug.lower(): return 'SUGGESTION'
    return 'other'
def load(rd):
    p=os.path.join(ROOT,rd,'interpretations.jsonl')
    return {json.loads(l)['id']:json.loads(l) for l in open(p)} if os.path.exists(p) else None
data={k:load(v) for k,v in RUNS.items()}; data={k:v for k,v in data.items() if v}
names=list(data)
print('## entered_text on the 21 transitions (T155..T212) whose live line shows a grey suggestion')
tally={k:collections.Counter() for k in names}
print('| T | typed (by eye) | '+' | '.join(names)+' |'); print('|---|---|'+'---|'*len(names))
for n in sorted(SUGG):
    row=[]
    for k in names:
        d=data[k][f'T{n}']; c=classify(n,d['entered_text']); tally[k][c]+=1
        row.append(('`%s`'%d['entered_text'] if d['entered_text'] is not None else 'null')+(' **%s**'%c if c not in ('typed',) else '')+(' SUB=%s'%d['submitted'] if d['submitted']!='no' else ''))
    print(f'| T{n} | `{TYPED[n]}` + grey `{SUGG[n][len(TYPED[n].rstrip()):][:30]}` | '+' | '.join(row)+' |')
print(); print('tally:'); 
for k in names: print('  ',k,dict(tally[k]))
print(); print('## submitted over T147..T215 (truth: yes at '+', '.join(f'T{n}' for n in SUBMIT)+')')
for k in names:
    fy=[]; miss=[]; unclear=[]; wrongtext=[]
    for n in range(147,216):
        d=data[k][f'T{n}']
        if d['submitted']=='yes' and n not in SUBMIT: fy.append((n,d['entered_text']))
        if n in SUBMIT and d['submitted']!='yes': miss.append((n,d['submitted'],d['entered_text']))
        if d['submitted']=='unclear': unclear.append((n,d['entered_text']))
        if n in SUBMIT and d['submitted']=='yes' and norm(d['entered_text'])!=norm(SUBMIT[n]): wrongtext.append((n,d['entered_text']))
    print(f'  {k}: false yes {fy}; missed {miss}; unclear {unclear}; yes with other text {wrongtext}')
print(); print('## never-run strings anywhere in entered_text (all transitions), with submitted')
for k in names:
    hits=[(t,d['entered_text'],d['submitted']) for t,d in data[k].items() for s in NEVER if d.get('entered_text') and s in d['entered_text']]
    print('  ',k,hits)
print(); print('## does the record call the grey text a suggestion? (action+result+description mention suggest/predict/grey/gray/ghost/autocomplet/history) on the 21')
for k in names:
    yes=0; typedcalled=[]
    for n in sorted(SUGG):
        d=data[k][f'T{n}']; txt=' '.join([d.get('action') or '',d.get('result') or '',d.get('description') or '']).lower()
        if re.search(r'suggest|predict|gr[ae]y|ghost|autocomplet|history|dim',txt): yes+=1
        else: typedcalled.append(n)
    print(f'   {k}: {yes}/21 mention it; not mentioned at {typedcalled}')
if '--full' in sys.argv:
    print(); print('## all T147..T215')
    for n in range(147,216):
        print(f'T{n}', '(typed by eye: %r)'%TYPED.get(n) if n in TYPED else '', '(SUBMIT %r)'%SUBMIT[n] if n in SUBMIT else '')
        for k in names:
            d=data[k][f'T{n}']; print(f"     {k:10s} sub={d['submitted']:7s} conf={d.get('confidence')} ent={d['entered_text']!r} cit={d['citations']}")
