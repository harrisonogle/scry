# P6: index-only answering, analysis beside the generated report

Matrix `evals/p6.toml`. The five whole-video pipelines of P4 and P4b were copied byte for byte and only `ask` was run again with `[ask] frames = false`: the agent has `search`, `get_node`, `get_transitions` and a `get_frame` that returns a frame's text record with no image; `redecode` is withheld. Same 27 questions. 5 of 5 runs clean, 135 answers, 0 errors. Spend $32.70 (questions $31.42, judge $1.29). The copies were verified with `diff -rq`; nothing was written under `runs/eval/p4` or `p4b`. This file holds what the analyst found from the run directories and the recorded tool calls (600 calls, replayed with 0 mismatches). Nothing here comes from a prototype.

## Result

| index | runs | positive questions correct / partial / wrong | negatives |
|---|---|---|---|
| annotated (two sync-built, one batch-built) | 3 | 22 / 0 / 0 in each | 5 / 5 in each |
| no annotation | 2 | 21 / 1 / 0 in each | 5 / 5 in each |

With frames (P4) every run scored 27 of 27. Without pixels, 413 of 415 judged rubric lines pass. The two that fail are the same line of the same question in the two unannotated runs. Repeats agree on every one of the 83 lines, within each base and between the batch-built and sync-built annotated indexes: the separation between bases is one rubric line, the separation between repeats is none.

## The one difference

Q2 asks about an architecture diagram on a slide; its third rubric line is that the arrow beside two named boxes leads to "Endpoint". Both unannotated answers described other arrows that are really in the picture and not the one asked about. The fact is not in those indexes at all: their transition entries say an "Endpoint" box appeared to the right and say nothing of an arrow. The annotated indexes hold it twice, in the frame description ("…and from that box to Endpoint"; "an arrow from that panel points to an Endpoint tile at the far right") and in the transition text, because `interpret` is given the description in force. 3 of 3 against 0 of 2.

What carried it was the per-frame **description**. No answer in any run turned on a container, a link or a second reading. The second reading did change wording: on Q20 the annotated answers quote the model's reading `::ffff:10.224.0.31`, where the unannotated ones say the record cannot confirm the leading colons (both judged correct).

The unannotated index is not free of pixels: `interpret` saw both frames of every transition, and its text carries the visual facts the other questions needed (which radio button was selected before the change, the red validation errors and the disabled button, a grey suggestion against typed text, the highlighted list entry). By the analyst's reading only two rubric lines in the set need a fact that no on-screen text carries: this arrow, and a radio button's state. One separated the bases and one did not.

## Honesty without pixels

85 answers were read in full and all 135 were checked mechanically (every visual word and every quoted string against what the answer's tool calls returned). No visual fact is asserted without a source in the tool results, and no on-screen text is invented. Annotated answers attribute visual claims to descriptions; unannotated ones take them from transition text and say "only one reader (OCR)" in 23 and 24 of 27 answers. Unscored slips in both bases: words of intent ("deliberately", "purely to demonstrate"; "shown and discussed", although the video has no audio), and one wrong time in one answer.

## Cost and behaviour (with frames in P4, then without in P6)

| base | $ per question | input tokens per question | turns | `get_frame` calls per answer |
|---|---|---|---|---|
| annotated, sync-built | 0.263, then 0.240 | 68.8k, then 62.4k | 3.19, then 3.17 | 0.67, then 0.46 |
| annotated, batch-built | 0.269, then 0.255 | 66.6k, then 58.6k | 3.15, then 3.04 | 0.74, then 0.37 |
| no annotation | 0.216, then 0.214 | 57.6k, then 64.6k | 3.43, then 3.70 | 1.00, then 1.00 |

Withholding pixels saved 8 %, 5 % and 1 % per question. Without annotation the agent read a frame's text record as often as it used to open the frame, and took more turns. Unannotated stays cheaper per question by about $0.025. Zero-result searches: 15 of 415, all exact-phrase probes, 13 of them on negatives.

## Bugs and surprises

- The junk description on frame 92 of the batch-built index (unrelated Dutch prose, P4 analysis) came back in 6 search results over 5 questions. Two answers named it as spurious; every batch answer was correct.
- A copy carries frames, overlays and the call cache: 959 MB for the phase that an index-only `ask` never reads.
- The report's "Spend: pipeline" line restates what P4 paid for the copied pipelines; the batch copy carries P4b's false cache-hit warnings (see `../p4/analysis.md`).
- `scry eval judge` prints three "Event loop is closed" tracebacks at shutdown and exits 0 with every verdict written.
- The judge was checked: 105 exact-string and time lines mechanically, 0 disagreements; every semantic line of 85 answers read, all agree. No judge error and no wrong draft answer.
