"""Pairs a run named on frame N, with the OCR text of each box, beside the ids100 r1 reference. Usage: pairs148.py <frame> <run-dir>..."""
import sys
from pathlib import Path
from scry.run import Run
F = int(sys.argv[1])
REF = Path('/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval/p10/smoke-ids100-r1')
for p in [REF] + [Path(x) for x in sys.argv[2:]]:
    run = Run(p); a = {x.frame: x for x in run.load_annotations()}[F]; fb = {x.frame: x for x in run.load_boxes()}[F]
    t = {b.id: b for b in fb.boxes}
    print(f'\n== {p.name} frame {F}: containers {[(c.id, c.kind, c.app, c.name[:40]) for c in a.containers]}; targets {len(a.targets)}; repairs {a.repair_counts}')
    for l in a.links:
        if l.kind == 'pair':
            print(f"  PAIR {'+'.join(l.key)} => {'+'.join(l.value)} : {' + '.join(t[k].text[:30] for k in l.key if k in t)}  =>  {' + '.join(t[v].text[:35] for v in l.value if v in t)}")
    for l in a.links:
        if l.kind == 'run': print(f"  RUN {' | '.join(t[b].text[:25] for b in l.boxes if b in t)}")
    for l in a.links:
        if l.kind == 'record': print(f"  RECORD {[' + '.join(t[b].text[:20] for b in cell if b in t) for cell in l.members]}")
    asg = {x.box: x.container for x in a.assign}
    print('  container of each target:', {c.id: sum(1 for b in a.targets if asg.get(b) == c.id) for c in a.containers}, 'unassigned', len(a.unassigned))
