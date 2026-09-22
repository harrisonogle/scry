"""Looser than P3's wrong-box rule (which drops a reading that still resembles its own OCR, e.g. two prompt lines):
a reading that disagrees with its own box, scores < 90 against it, and scores >= 90 against another box on the frame.
Reports where that other box is. Both arms. Usage: loose.py [-v]"""
import json, sys, re
from collections import Counter
from pathlib import Path
from rapidfuzz import fuzz
from scry.run import Run
from scry.annotate.join import agreement
from scry.textdiff import norm
BASE = Path('<repo>/runs/eval')
verbose = '-v' in sys.argv
def gap(a, b): return max(0, max(a[0], b[0]) - min(a[2], b[2])), max(0, max(a[1], b[1]) - min(a[3], b[3]))
print('run | readings | another box\'s text (loose) | own is icon glyph | other box: line above/below (dy<=12,dx==0) | beside (dy==0) | elsewhere | frames')
for span in ('smoke', 'span2'):
    for s in ['s100', 's067', 's050', 'd100', 'd067', 'd050']:
        for r in (1, 2):
            n = f'{span}-{s}-r{r}'; run = Run(BASE / ('p5' if s[0] == 'd' else 'p3') / n)
            boxes = {fb.frame: fb for fb in run.load_boxes()}
            nread = 0; hits = []
            for a in run.load_annotations():
                if a.texts is None: continue
                fb = boxes[a.frame].boxes; bb = {b.id: b for b in fb}
                for t in a.texts:
                    if t.box not in bb or not t.text.strip(): continue
                    nread += 1; o = bb[t.box].text
                    if agreement(o, t.text): continue
                    b_ = norm(t.text).lower()
                    if len(b_) < 3 or fuzz.ratio(norm(o).lower(), b_) >= 90: continue
                    c = [(fuzz.ratio(norm(x.text).lower(), b_), x.id) for x in fb if x.id != t.box]
                    c = [x for x in c if x[0] >= 90]
                    if not c: continue
                    oid = min(c, key=lambda x: sum(gap(bb[t.box].bbox, bb[x[1]].bbox)))[1]
                    dx, dy = gap(bb[t.box].bbox, bb[oid].bbox)
                    where = 'line' if (dx == 0 and dy <= 12) else 'beside' if dy == 0 else 'elsewhere'
                    hits.append((a.frame, t.box, o[:50], t.text[:50], oid, dx, dy, where, not re.search(r'[A-Za-z]{3,}', o)))
            w = Counter(h[7] for h in hits if not h[8])
            print(f"{n} | {nread} | {len(hits)} | {sum(h[8] for h in hits)} | {w['line']} | {w['beside']} | {w['elsewhere']} | {dict(Counter(h[0] for h in hits))}")
            if verbose:
                for h in hits: print('      ', h)
