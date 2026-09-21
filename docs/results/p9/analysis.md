# P9: the answering agent alone on Sonnet 5, analysis beside the generated report

Matrix `evals/p9.toml`. P4's four Opus-built whole-video pipelines were copied byte for byte and only `ask` was run again with `[ask] model = "claude-sonnet-5"`, frames available as usual. 4 of 4 runs clean, 108 answers, 0 errors; every answer record says `claude-sonnet-5` and is priced at Sonnet's prices. Spend $7.05 (questions $6.23, judge $0.82). The generated `report.md` and `scores.json` do not name the model that answered (the only trace is the axis label `asksonnet`), and their pipeline dollars restate what P4 paid. The analyst read all 108 answers in full, replayed all 291 tool calls (0 mismatches), and re-ran the same checks over P4 and P8; scripts in `scripts/`, the 27-row table in `tables.md`. Nothing here comes from a prototype.

Three sets are compared: **P4**, Opus agent on the Opus index; **P9**, Sonnet agent on the Opus index; **P8**, Sonnet agent on a Sonnet index.

## Scores and cost

| | P4 | P9 | P8 |
|---|---|---|---|
| questions correct of 27 (annotated r1, r2; no annotation r1, r2) | 27, 27, 27, 27 | 27, 26.5, 27, 27 | 26.5, 27, 27, 27 |
| $ per question, annotated / no annotation | 0.263 / 0.216 | 0.062 / 0.053 | 0.066 / 0.053 |
| seconds per question | 22.5 | 9.5 | 10.4 |
| answers that opened a frame, per run of 27 | 15, 14, 19, 23 | 3, 3, 6, 6 | 7, 5, 12, 11 |
| answers from searches alone, of 108 | 20 | 78 | 67 |
| turns / tool calls per answer (annotated) | 3.19 / 4.13 | 2.37 / 2.57 | 2.59 / 3.06 |

The one miss in P9 is P8's miss again, now on the Opus index: Q15, "Number of tags: 1". The agent counted the one row a description mentions and did not open the frame; the Opus agent read the same description, opened the frame and found "This repository contains 2 tag(s)". Two of the four annotated Sonnet-agent runs across P8 and P9 made this miss; none of the four Opus ones.

P9 costs a quarter of Opus per question: 0.40 from the price and 0.60 from doing less.

## The honest text-change contract

**Q18 separates the agent from the index.** Reading Opus's index, none of the four Sonnet answers says `kubectl get pods` was retyped: all four say `ku`, `kubect`, `kubectl` were typed and the rest was the shell's grey suggestion. P8's "retyped" was the Sonnet index's error, not the agent's. The Sonnet agent still loosens the wording ("a third attempt was typed but abandoned") where Opus does not.

| contract item | P4 | P9 | P8 |
|---|---|---|---|
| Q18 says "retyped `kubectl get pods`" | 0 of 4 | 0 of 4 | 4 of 4 |
| names the suggestion on Q16 / Q17 / Q18 (of 4 each) | 3 / 3 / 4 | 1 / 2 / 4 | 0 / 0 / 0 |
| answers that mention readers, sightings or stability, of 108 | 90 | 12 | 9 |
| quotes a text its results marked as read differently, and says so | 40 of 46 | 3 of 18 | 2 of 26 |
| quotes a once-seen text, and says so | 20 of 65 | 1 of 36 | 0 of 34 |
| cites scrollback as corroboration that commands ran | 0 | 2, and 1 borderline | 0 |

Breaks in P9, all judged correct by the rubric:

- Q17, two answers: "Both runs' outputs are corroborated by later scrollback visible in frames 205, 212–215"; "reflected in later scrollback frames … confirming the sequence". An Opus answer to the same question says the opposite, correctly: the outputs remained in the scrollback, "which is why it keeps appearing later in the record without being re-run".
- Q20, one answer: shown both readings (OCR `IP address:ff:10.224.0.31`, the model's `::ffff:`), it did not open the frame and wrote "confirmed independently by the OCR-derived text". That is a false agreement. One of four Sonnet answers names both readings; the Opus answers do.
- Q19: in both annotated runs the search returned header cells marked `agree: false`; neither Sonnet answer mentions it and none of the four opened the frame. Opus opened it 4 of 4.
- Q21, one answer: gives the time the expose command "ran" from two transitions that say `submitted: no`; it never retrieved the transition where it ran. The order asked for is still right.
- Q22, one answer: the deployment "was submitted and completed"; the video never shows it finishing, and the same run's answer to the negative Q25 says so.

No text is invented in any answer: every quoted string and visual word is in the tool results. The Sonnet agent repeats the index whoever built it; it does not check it.

## What a Sonnet agent holds and loses against an Opus agent on the same index

- **Holds:** the scores; every exact string and time; all negatives; no invented text; typed against suggested, once the index says it.
- **Loses:** checking (78 of 108 answers from searches alone; a sixth to a third as many frames opened); almost all of "say when readings differ or a text was seen once"; and in a few answers it leans on scrollback, reports a run from `submitted: no` transitions, or calls a deployment completed.
- **Costs:** $0.053 to $0.062 a question against $0.216 to $0.263; 9.5 s against 22.5 s.

## Noise

Repeats agree on every verdict except Q15. Inside repeat noise: the one partial taken alone, the two scrollback sentences, P9 against P8 on dollars. Far outside it, Sonnet against Opus on the same index: dollars, tokens, seconds, turns, calls, frames opened (3 to 6 of 27 against 14 to 23), remarks about readers (12 of 108 against 90), answer length. Outside it, P9 against P8: "retyped" 0 of 4 against 4 of 4; frames opened 18 of 108 against 35.

## Surprises in the Opus indexes

In one no-annotation index the Create click is recorded three times (three consecutive transitions, each `submitted: yes`). One annotated step summary says "type the command `kubectl create deployment …`" although the transition it cites calls most of that line a suggestion: a likely source of the "typed" wording on Q16, in both agents.
