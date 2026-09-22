import json, sys
BASE='/Users/harrisonogle/src/harrisonogle/agentic-escort/runs/eval'
frames=[int(x) for x in sys.argv[1].split(',')]
for s in sys.argv[2:]:
    for r in (1,2):
        for span in ('smoke','span2'):
            try: lines=open(f"{BASE}/{'p7' if s.startswith('sonnet') else 'p3'}/{span}-{s}-r{r}/annotations.jsonl")
            except FileNotFoundError: continue
            for l in lines:
                a=json.loads(l)
                if a['frame'] in frames:
                    print(f"--- {span}-{s}-r{r} F{a['frame']} ({len(a['targets'])} targets)\n{a['description']}\n")
