import sys
from pathlib import Path
from scry.run import Run
from scry.schemas import parse_box_ref
BASE = Path('/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval')
T = [('b33','b34'),('b38','b37'),('b40','b39'),('b43','b44'),('b47','b48'),('b49','b50'),('b54','b55'),
     ('b69','b70'),('b72','b73'),('b83','b84'),('b89','b88'),('b94','b93'),('b105','b104'),('b110','b109'),('b119','b118'),
     ('b67','b68'),('b74','b75'),('b81','b82'),('b87','b86'),('b90','b91'),('b95','b96'),('b99','b98'),('b103','b102'),('b107','b108'),
     ('b112','b113'),('b117+b120','b116'),('b128','b127'),('b130','b131')]
truth = {(frozenset(k.split('+')), frozenset(v.split('+'))) for k, v in T}
for s in sys.argv[1:]:
    for r in (1, 2):
        n = f'smoke-{s}-r{r}'
        run = Run(BASE / ('p7' if s.startswith('sonnet') else 'p3') / n); L = run.load_labels()
        ocr = {b.id: b.text for fb in run.load_boxes() if fb.frame == 150 for b in fb.boxes}
        fl = L.frame(150)
        loc = lambda ref: parse_box_ref(ref)[1]
        pairs = [(frozenset(map(loc, l.key)), frozenset(map(loc, l.value))) for l in fl.links if l.kind == 'pair']
        correct = [p for p in pairs if p in truth]
        partial = [p for p in pairs if p not in truth and any(p[1] == t[1] and p[0] <= t[0] for t in truth)]
        wrong = [p for p in pairs if p not in truth and p not in partial]
        missing = [t for t in truth if t not in pairs and not any(p[1] == t[1] and p[0] <= t[0] for p in partial)]
        runs_ = [[loc(b) for b in l.boxes] for l in fl.links if l.kind == 'run']
        recs = [l for l in fl.links if l.kind == 'record']
        print(f'{n}: pairs in force {len(pairs)} correct {len(correct)} partial {len(partial)} wrong {len(wrong)} missing {len(missing)} | runs {len(runs_)} records {len(recs)} relinked(total run) {L.relinked}')
        for k, v in wrong: print('    WRONG ', ' + '.join(ocr[b][:40] for b in sorted(k)), ' => ', ' + '.join(ocr[b][:40] for b in sorted(v)))
        for k, v in partial: print('    PARTIAL ', ' + '.join(ocr[b][:40] for b in sorted(k)), ' => ', ' + '.join(ocr[b][:40] for b in sorted(v)))
        for k, v in missing: print('    MISSING ', ' + '.join(ocr[b][:40] for b in sorted(k)), ' => ', ' + '.join(ocr[b][:40] for b in sorted(v)))
        for rb in runs_: print('    RUN ', ' | '.join(ocr[b][:30] for b in rb))
        for l in recs: print('    RECORD ', [[ocr[loc(b)][:20] for b in cell] for cell in l.members][:6], 'hdr', [ocr[loc(b)][:20] for b in l.header])
