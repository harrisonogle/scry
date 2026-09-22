import sys, io, contextlib
span = sys.argv[1]
sys.argv = ['qual.py', span]
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    exec(open('<scratch>/p7/qual.py').read())
def cname(x, f, b):
    a = x.ann[f]; cid = assign_map(a).get(b); c = next((c for c in a.containers if c.id == cid), None)
    return 'none' if c is None else f'{c.kind}:{c.app}/{c.name[:30]}'
ref = refs[0]
for n, x in runs.items():
    if x is ref: continue
    d, tot = container_diff(x, ref)
    print(n, len(d), 'of', tot)
    for f, b in sorted(d): print('     ', f, b, repr(x.ocr[(f, b)][:40]), '| run:', cname(x, f, b), '| ref r1:', cname(ref, f, b))
