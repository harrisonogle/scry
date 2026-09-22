"""Container differences split in two: (a) P3's measure (membership and kind+app class), (b) membership and app class only,
ignoring whether the container is called window or popup. Also lists (b)'s differing targets. Usage: contdiff2.py <span>"""
import sys, io, contextlib
span = sys.argv[1]
sys.argv = ['qual.py', span]
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    exec(open('<scratch>/p7/qual.py').read())
_app = appclass
def appclass_nokind(c):
    return _app(c)[2:] if c is not None else 'none'
def cname(x, f, b):
    a = x.ann[f]; cid = assign_map(a).get(b); c = next((c for c in a.containers if c.id == cid), None)
    return 'none' if c is None else f'{c.kind}:{c.app}/{c.name[:30]}'
for n, x in runs.items():
    for ref in refs:
        if ref is x: continue
        appclass = _app
        d1, tot = container_diff(x, ref)
        appclass = appclass_nokind
        d2, _ = container_diff(x, ref)
        print(f'{n} vs {ref.name}: P3 measure {len(d1)}/{tot} = {100*len(d1)/tot:.1f}% | ignoring window/popup kind {len(d2)}/{tot} = {100*len(d2)/tot:.1f}%')
        if 'sonnet' in n and ref is refs[0]:
            for f, b in sorted(d2): print('       ', f, b, repr(x.ocr[(f, b)][:40]), '| run:', cname(x, f, b), '| ref:', cname(ref, f, b))
