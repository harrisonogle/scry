import sys, json, re
import numpy as np
sys.argv = ['qual.py', sys.argv[1]]
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    exec(open('<scratch>/qual.py').read())
from scry.schemas import parse_box_ref
print('scale | contdiff% targets (mean over repeats x refs) | contdiff% all boxes | pairs repro% | runs repro% | strict agree% r1/r2 | wrongbox r1/r2 | off r1/r2 | empty_real r1/r2 | pairs n | runs n | records n | popups | cont/rec')
for s in SCALES:
    xs = [runs[f'{span}-{s}-r{r}'] for r in (1, 2)]
    cd = []; cda = []; pr = []; rr = []
    for x in xs:
        for ref in refs:
            if ref is x: continue
            d, tot = container_diff(x, ref); cd.append(100 * len(d) / tot)
            n = k = 0
            for (f, b) in x.ocr:
                lab = x.labels.box(f'{f}/{b}') if False else None
            # all boxes through lifetimes
            for ref_ in x.labels._boxes:
                src = x.labels._source.get(ref_)
                if src is None: continue
                n += 1; k += (parse_box_ref(src) in d)
            cda.append(100 * k / n)
            rp = linkset(ref, 'pair'); pr.append(100 * len(rp & linkset(x, 'pair')) / len(rp))
            r_ = linkset(ref, 'run'); rr.append(100 * len(r_ & linkset(x, 'run')) / len(r_))
    rd = [readings(x) for x in xs]
    lk = [links_by_kind(x) for x in xs]
    print(f"{s} | {np.mean(cd):.1f} | {np.mean(cda):.1f} | {np.mean(pr):.0f} | {np.mean(rr):.0f} | {100*rd[0][0]/rd[0][1]:.1f}/{100*rd[1][0]/rd[1][1]:.1f} | {rd[0][3]}/{rd[1][3]} | {len(rd[0][6])}/{len(rd[1][6])} | {rd[0][2]}/{rd[1][2]} | {lk[0]['pair']}/{lk[1]['pair']} | {lk[0]['run']}/{lk[1]['run']} | {lk[0]['record']}/{lk[1]['record']} | {'/'.join(str(sum(1 for a in x.ann.values() for c in a.containers if c.kind=='popup')) for x in xs)} | {'/'.join(f'{np.mean([len(a.containers) for a in x.ann.values()]):.2f}' for x in xs)}")
