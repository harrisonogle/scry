"""Per frame: billed output tokens against the size of the stored answer text (call cache 'text'), both models.
Cache files are matched to frames by the description string."""
import json, glob
BASE='<repo>/runs/eval/'
for span in ('smoke','span2'):
    names=[f'p3/{span}-s100-r1',f'p3/{span}-s100-r2',f'p7/{span}-sonnet5-r1',f'p7/{span}-sonnet5-r2']
    data={}
    for n in names:
        ann={json.loads(l)['frame']:json.loads(l) for l in open(BASE+n+'/annotations.jsonl')}
        bydesc={a['description']:f for f,a in ann.items()}
        for p in glob.glob(BASE+n+'/cache/*.json'):
            d=json.load(open(p))
            if d['request'].get('stage')!='annotate': continue
            desc=(d['response'].get('parsed') or {}).get('description')
            f=bydesc.get(desc)
            data[(n,f)]=(len(d['response']['text'] or ''), d['response']['usage']['output_tokens'], len(ann[f]['targets']) if f in ann else None)
    print(f'== {span}: frame targets | opus chars/tokens (chars per token) r1 r2 | sonnet chars/tokens (cpt) r1 r2')
    frames=sorted({f for n,f in data if f is not None})
    for f in frames:
        cells=[]
        for n in names:
            c,t,_=data.get((n,f),(0,0,0)); cells.append(f'{c}/{t} ({c/max(1,t):.2f})')
        print(f, data[(names[0],f)][2], '|', ' '.join(cells[:2]), '|', ' '.join(cells[2:]))
    for n in names:
        small=[(c,t) for (m,f),(c,t,k) in data.items() if m==n and k is not None and k<=5]; big=[(c,t) for (m,f),(c,t,k) in data.items() if m==n and k is not None and k>20]
        print(n, 'records<=5 targets: chars/token', round(sum(c for c,t in small)/sum(t for c,t in small),2), '| records>20 targets:', round(sum(c for c,t in big)/sum(t for c,t in big),2), 'unmatched', sum(1 for (m,f) in data if m==n and f is None))
