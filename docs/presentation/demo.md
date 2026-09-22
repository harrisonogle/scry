# Live demo: one question through the answering agent

Recorded 2026-09-21 against a byte-for-byte copy of `runs/eval/p4/full-inc-transcribing-r1` (the annotated whole-video index, incremental transcribing, Opus 5, sync). One paid call: **$0.2142**, 54 s wall, 3 turns, 4 tool calls, model `claude-opus-5`, stop `end_turn`. Tokens: 6 input, 28,068 cache write, 20,114 cache read, 1,146 output. Nothing under `runs/eval/p4/` was touched.

## The command to run on camera

```
uv run scry ask runs/eval/p4/full-inc-transcribing-r1 "What exact command created the deployment, when was it run, and what did the terminal show afterwards?"
```

Add `--json` to print the answer, citations, tool log, usage and cost as JSON; without it the answer is printed and one line `turns=... tools=... cost=$...` goes to stderr. Expect 30 to 60 s.

**Does `ask` write into the run directory?** Only if the agent calls the `redecode` tool, which saves frames under `<run>/redecode/`; `search`, `get_node`, `get_transitions` and `get_frame` read only, and no answer or cache is written (`src/scry/ask.py`, module docstring). This run did not call `redecode`. The P4 directories are evidence: to be safe, ask against a copy (`cp -R runs/eval/p4/full-inc-transcribing-r1 /tmp/demo-run` and pass that path), as was done for this transcript. The answer below is what the copy returned; it will vary a little from call to call (every question is a fresh conversation).

## The tool calls, in order

Turn 1 issued two searches at once; turn 2 opened the frame and the transitions; turn 3 wrote the answer.

1. `search(query="kubectl create deployment")` -> 20 hits. Top of the list: section C5 ("Deploy kodekloudapp and check where it runs", frames 189 to 207), lifetime L1589 (the command line on frame 190, OCR `kubect1 ...` against the model's `kubectl ...`, `agree: false`), transition T190 (the first keystrokes, 737.8 to 740.0 s, `submitted: no`), transition T196 (` --replicas` appended, `submitted: no`), frames 199 and 197, step S23, frame 200, the video node, then lifetimes L1609, L1592, transition T197, transition T198, lifetime L1610, step S24, lifetimes L1613, L1608, transition T191, section C3, lifetime L1634.
2. `search(query="deployment created")` -> 20 hits. Top: transition T145 and frame 144 (the Azure portal's ARM deployment page, an earlier "Created" status, a near miss the agent set aside), section C5, **lifetime L1611** (`deployment.apps/kodekloudapp created`, frames 198 to 215, 18 sightings, both readers agree), frame 200, step S15, lifetime L1007, transition T144, transition T198, step S23, and ten more.
3. `get_frame(frame=198)` -> the frame's record and its image. The record starts with the description in force ("... The last command creates a deployment named kodekloudapp from image hpranav/kodekloudappcs:v1 with one replica, which reports created, and a blinking cursor waits at a fresh prompt ...") and lists every text box alive on the frame with its lifetime, when it was seen, other OCR readings and its window. The lines that matter:
   - `b88 L1610 "PS C:\Users\msadmin> kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1 --replicas=1" | seen 759.5-769.8s in 4 frames | PowerShell window`
   - `b89 L1611 "deployment.apps/kodekloudapp created" | seen 759.5-838.8s in 18 frames | PowerShell window`
   - `b91 L1612 "PS C:\Users\msadmin>" | seen 759.5-763.3s in 1 frames | PowerShell window`
4. `get_transitions(t_a=759.4, t_b=775)` -> 6 transitions, T198 to T203. T198 (frame 197 to 198, 759.43 to 759.47 s): action "The user pressed Enter to run the typed kubectl command.", result "The command executed: \"deployment.apps/kodekloudapp created\" was printed and a fresh prompt appeared below.", `entered_text` the full command, `submitted: yes`, confidence 0.94. T199: `kubectl` typed with a greyed PSReadLine suggestion, `submitted: no`. T200 and T201: `kubectl get deployment` typed, then run. T202: the console window enlarged, no text entered. T203: `kubectl get pods` run.

## The answer, verbatim

## The command

```
kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1 --replicas=1
```

It was typed up in stages: the shell history suggested `kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1` when the user started typing at ~737.8–740 s (T190, frame 190), then ` --replicas` was appended at 758.3 s (T196) and `=1` at 758.9 s (T197).

A note on the text: OCR reads the binary as "kubect1" in several single-frame lifetimes (e.g. L1589, L1609), while the vision reader reads "kubectl"; on the stable lifetimes both readers agree on `kubectl` (L1592, 5 frames, and L1634, 14 frames), and the screenshot of frame 198 clearly shows `kubectl`. The rest of the flags are agreed on by both readers.

## When it ran

Enter was pressed between frame 197 and frame 198, i.e. at **t ≈ 759.43–759.47 s (about 12:39 into the video)**. Transition T198 records `submitted: yes` (confidence 0.94).

## What the terminal showed afterwards

- Immediately below the command, frame 198 (t = 759.47 s) shows the output line **`deployment.apps/kodekloudapp created`** (box 198:b89, lifetime L1611 — both readers agree; visible in 18 frames through 838.8 s), followed by a fresh prompt `PS C:\Users\msadmin>` (198:b91).
- At 763.3–764.5 s the user typed `kubectl` again and PSReadLine offered the greyed suggestion ` create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1 --replicas=1` (T199, frame 199) — a suggestion, not a typed command.
- Instead the line was completed as `kubectl get deployment` (T200) and run at 767.7–768.0 s (T201, submitted yes): the table header `NAME READY UP-TO-DATE AVAILABLE AGE` with the row `kodekloudapp 1/1 1 1 20s`.
- After enlarging the console window (T202, 769.8 s), `kubectl get pods` was run at ~770.5–773.5 s (T203, submitted yes), printing `NAME READY STATUS RESTARTS AGE` and one row: `kodekloudapp-67ffc758c5-mm42w 1/1 Running 0 34s`.

## Citations extracted by `scry` from the answer

`T190, 190, T196, T197, L1589, L1609, L1592, L1634, 198, 197, T198, 198:b89, L1611, 198:b91, T199, 199, T200, T201, T202, T203`

Every citation is an id the index knows (a transition `T…`, a frame number, a lifetime `L…`, or a frame-and-box `198:b89`). The one to show on screen is **frame 198, box b89**.

## The frame to show

- Frame image: `runs/eval/p4/full-inc-transcribing-r1/frames/00198.png` (1920 x 1080, settled at t = 759.47 s, held to 763.30 s).
- Cited box `198:b89`: rectangle x 657 to 964, y 768 to 789 (from `boxes.jsonl`, frame 198), text `deployment.apps/kodekloudapp created`, OCR confidence 0.9998.
- The command line above it, `198:b88`: x 659 to 1547, y 752 to 772.
- `docs/presentation/demo-frame-198.png` is that frame with both boxes drawn (blue: the command, b88; orange: the cited output, b89), and `demo-frame-198-crop.png` is the terminal lines at 2x for a cut-in.

## Alternate questions, the three most visual of the 27 draft questions

From `docs/ground-truth/full-questions.md`; each has a moment that reads well on screen.

1. **Q8** "The presenter lowers the limit on how many pods one machine may run. From what to what, and did the portal complain while the new number was being typed?" (110 to 30; two red validation errors on frame 95 only, 7:03.8 to 7:04.3, while the field read `3`.)
2. **Q2** "In the diagram that traces a request through the cluster, which two small boxes sit between the container runtime and the pods, and what does the arrow beside them lead to?" (HCL and HNS, arrow to Endpoint; the one rubric line that only the per-frame description carried in P6.)
3. **Q15** "Before deploying, the presenter shows where the application's container image lives. Which site is it, what is the repository called, how many tags does it have, and when is this shown?" (Docker Hub, `hpranav/kodekloudappcs`, 2 tags, on frame 188 only, 12:11.7 to 12:14.7: the page that is on screen for three seconds, and the one the Sonnet agent got partially wrong by not opening the frame.)
