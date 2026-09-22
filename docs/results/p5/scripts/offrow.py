"""Pair links whose key and value share no row: vertical gap between the nearest key box and value box > 12 px.
Measured on stored records; both arms. Usage: offrow.py [-v]"""
import json, sys
from collections import Counter
BASE='<repo>/runs/eval/'
verbose='-v' in sys.argv
def load(p):
    ann={}; boxes={}
    for l in open(BASE+p+'/annotations.jsonl'):
        a=json.loads(l); ann[a['frame']]=a
    for l in open(BASE+p+'/boxes.jsonl'):
        fb=json.loads(l); boxes[fb['frame']]={b['id']:b for b in fb['boxes']}
    return ann,boxes
def gap(a,b):
    return max(0,max(a[0],b[0])-min(a[2],b[2])), max(0,max(a[1],b[1])-min(a[3],b[3]))
print('run | pair links | off-row pairs (dy>12) | frames | runs with a jump (dy>12 or dx>300 between consecutive boxes)')
for span in ('smoke','span2'):
    for s in ['s100','s067','s050','d100','d067','d050']:
        for r in (1,2):
            n=f"{'p5' if s[0]=='d' else 'p3'}/{span}-{s}-r{r}"
            ann,boxes=load(n)
            tot=0; off=[]; rj=[]
            for f,a in ann.items():
                bb=boxes[f]
                for l in a['links']:
                    if l['kind']=='pair':
                        tot+=1
                        g=min((gap(bb[k]['bbox'],bb[v]['bbox']) for k in l['key'] for v in l['value']),key=lambda t:t[1]*10+t[0])
                        if g[1]>12: off.append((f,g,' + '.join(bb[k]['text'][:25] for k in l['key']),'=>',' + '.join(bb[v]['text'][:25] for v in l['value'])))
                    elif l['kind']=='run':
                        gs=[gap(bb[x]['bbox'],bb[y]['bbox']) for x,y in zip(l['boxes'],l['boxes'][1:])]
                        if any(g[1]>12 or g[0]>300 for g in gs): rj.append((f,gs,' | '.join(bb[x]['text'][:25] for x in l['boxes'])))
            print(f"{n} | {tot} | {len(off)} | {dict(Counter(o[0] for o in off))} | {len(rj)}")
            if verbose:
                for o in off: print('      OFFROW',o)
                for o in rj: print('      RUNJUMP',o)
