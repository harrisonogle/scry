"""Every target where a Sonnet reading differs from both Opus s100 readings (whitespace-normalised, case kept). Usage: readdiff.py <span>"""
import json, sys, re
BASE='<repo>/runs/eval/'
span=sys.argv[1]
names=[f'p3/{span}-s100-r1',f'p3/{span}-s100-r2',f'p7/{span}-sonnet5-r1',f'p7/{span}-sonnet5-r2']
R={n:{json.loads(l)['frame']:json.loads(l) for l in open(BASE+n+'/annotations.jsonl')} for n in names}
boxes={json.loads(l)['frame']:{b['id']:b for b in json.loads(l)['boxes']} for l in open(BASE+names[0]+'/boxes.jsonl')}
nz=lambda s: re.sub(r'\s+',' ',(s or '')).strip()
n_all=n_diff=0
for f in sorted(R[names[0]]):
    tx=[{t['box']:t['text'] for t in (R[n][f]['texts'] or [])} for n in names]
    for b in R[names[0]][f]['targets']:
        o=[nz(tx[0].get(b)),nz(tx[1].get(b))]; s=[nz(tx[2].get(b)),nz(tx[3].get(b))]
        n_all+=1
        bad=[x for x in s if x not in o]
        if bad:
            n_diff+=1
            print(f"F{f} {b} OCR={boxes[f][b]['text'][:70]!r}\n      opus  {o[0][:90]!r} | {o[1][:90]!r}\n      sonnet {s[0][:90]!r} | {s[1][:90]!r}")
print('targets',n_all,'with a sonnet reading unlike both opus readings',n_diff)
