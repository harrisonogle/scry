# p2a evaluation report

Date: 2026-09-21. Matrix: `evals/p2a.toml`. Source run: `runs/p0`. Runs: 15.

Runs by status: done 15.
Commits the runs started on: `eac77d32fda1` (5 runs), `26216fea11e5` (10 runs).
Runs that started on a dirty tree: smoke-grouponly-r2, smoke-grouponly-r3, smoke-inc-transcribing-r3, smoke-inc-grouponly-r1, smoke-inc-grouponly-r2, smoke-inc-grouponly-r3.

$ / video = $ / frame × 221 frames, a linear projection from this span to the whole source video. Dollars are what a cold run pays at the synchronous list price, from the stages' manifest usage (an answer served from a call cache is priced as if paid); the batch price is half. The question set's dollars are per question and outside $ / video; the judge's dollars are apart from both.

An `outside` row means only that the difference is larger than the largest difference seen between identical cold runs of the two configurations, scaled for means of repeats. With three repeats a side that floor is a range of three values: by a normal approximation about one row in eight reads `outside` when nothing differs [estimated], and this report has dozens of rows. One `outside` row is weak evidence. Nothing here is a verdict, and no row decides anything by itself.

## Warnings

none

Notes (expected absences):

- smoke-grouponly-r1: no second reader: exact.vlm not scored
- smoke-grouponly-r2: no second reader: exact.vlm not scored
- smoke-grouponly-r3: no second reader: exact.vlm not scored
- smoke-none-r1: no annotations
- smoke-none-r1: no second reader: exact.vlm not scored
- smoke-none-r2: no annotations
- smoke-none-r2: no second reader: exact.vlm not scored
- smoke-none-r3: no annotations
- smoke-none-r3: no second reader: exact.vlm not scored
- smoke-inc-grouponly-r1: no second reader: exact.vlm not scored
- smoke-inc-grouponly-r2: no second reader: exact.vlm not scored
- smoke-inc-grouponly-r3: no second reader: exact.vlm not scored

## Runs

| run | status | frames | cold | resumed | cache hits | $ | $ / frame | $ / video | pipeline s | questions s |
|---|---|---|---|---|---|---|---|---|---|---|
| smoke-transcribing-r1 | done | 11 | yes | no | 0 | $2.4643 | $0.2240 | $49.51 | 277.9 | 363.3 |
| smoke-transcribing-r2 | done | 11 | yes | no | 0 | $2.4857 | $0.2260 | $49.94 | 239.6 | 345.1 |
| smoke-transcribing-r3 | done | 11 | yes | no | 0 | $2.4359 | $0.2214 | $48.94 | 244.2 | 335.2 |
| smoke-grouponly-r1 | done | 11 | yes | no | 0 | $1.6596 | $0.1509 | $33.34 | 136.6 | 383.2 |
| smoke-grouponly-r2 | done | 11 | yes | no | 0 | $1.6659 | $0.1514 | $33.47 | 140.4 | 355.2 |
| smoke-grouponly-r3 | done | 11 | yes | no | 0 | $1.5625 | $0.1420 | $31.39 | 148.1 | 367.3 |
| smoke-none-r1 | done | 11 | yes | no | 0 | $0.3773 | $0.0343 | $7.58 | 89.4 | 430.8 |
| smoke-none-r2 | done | 11 | yes | no | 0 | $0.3011 | $0.0274 | $6.05 | 54.5 | 388.9 |
| smoke-none-r3 | done | 11 | yes | no | 0 | $0.2765 | $0.0251 | $5.56 | 45.8 | 424.9 |
| smoke-inc-transcribing-r1 | done | 11 | yes | no | 0 | $1.1489 | $0.1044 | $23.08 | 107.9 | 352.6 |
| smoke-inc-transcribing-r2 | done | 11 | yes | no | 0 | $1.2400 | $0.1127 | $24.91 | 107.5 | 373.4 |
| smoke-inc-transcribing-r3 | done | 11 | yes | no | 0 | $1.1819 | $0.1074 | $23.75 | 101.7 | 350.9 |
| smoke-inc-grouponly-r1 | done | 11 | yes | no | 0 | $1.0609 | $0.0964 | $21.31 | 97.0 | 384.1 |
| smoke-inc-grouponly-r2 | done | 11 | yes | no | 0 | $1.1207 | $0.1019 | $22.52 | 95.5 | 377.6 |
| smoke-inc-grouponly-r3 | done | 11 | yes | no | 0 | $1.1230 | $0.1021 | $22.56 | 94.5 | 384.3 |

The stages' own counters, reported, never compared:

| run | annotate | interpret |
|---|---|---|
| smoke-transcribing-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 2, "link_malformed": 1, "link_unknown_box": 1, "second_text": 1, "text_unknown_box": 1}, "repairs": 6} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-transcribing-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 1, "link_malformed": 2, "second_text": 2}, "repairs": 5} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-transcribing-r3 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 3, "second_text": 2, "text_unknown_box": 1}, "repairs": 6} | {"errors": 0, "invalid_citations": 1, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-grouponly-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 2}, "repairs": 2} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-grouponly-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 2, "link_malformed": 2}, "repairs": 4} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-grouponly-r3 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 1, "link_malformed": 4}, "repairs": 5} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-none-r1 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-none-r2 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-none-r3 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-inc-transcribing-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_malformed": 3}, "repairs": 3} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-inc-transcribing-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 1, "link_malformed": 1}, "repairs": 2} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-inc-transcribing-r3 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 2, "link_malformed": 5}, "repairs": 7} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-inc-grouponly-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 4}, "repairs": 4} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-inc-grouponly-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 1, "link_malformed": 4}, "repairs": 5} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-inc-grouponly-r3 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_malformed": 1}, "repairs": 1} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |

## Cost

Means over a configuration's repeats, per stage. One figure per stage, at the synchronous list price; the batch columns are half of it. s / frame is the wall time of the stages the dollars cover (the pipeline through `index`); answering the questions is timed per question, below.

| configuration | stage | $ | $ / frame | $ / video | batch $ | batch $ / frame | batch $ / video | s / frame |
|---|---|---|---|---|---|---|---|---|
| smoke-transcribing | annotate | $2.1226 | $0.1930 | $42.65 | $1.0613 | $0.0965 | $21.32 | 17.5 |
| smoke-transcribing | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| smoke-transcribing | interpret | $0.2434 | $0.0221 | $4.89 | $0.1217 | $0.0111 | $2.44 | 1.4 |
| smoke-transcribing | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 1.7 |
| smoke-transcribing | summarize | $0.0959 | $0.0087 | $1.93 | $0.0479 | $0.0043 | $0.96 | 2.4 |
| smoke-transcribing | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| smoke-transcribing | all stages | $2.4620 | $0.2238 | $49.46 | $1.2310 | $0.1119 | $24.73 | 23.1 |
| smoke-grouponly | annotate | $1.2315 | $0.1120 | $24.74 | $0.6158 | $0.0560 | $12.37 | 8.5 |
| smoke-grouponly | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| smoke-grouponly | interpret | $0.2858 | $0.0260 | $5.74 | $0.1429 | $0.0130 | $2.87 | 1.4 |
| smoke-grouponly | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.7 |
| smoke-grouponly | summarize | $0.1120 | $0.0102 | $2.25 | $0.0560 | $0.0051 | $1.12 | 2.2 |
| smoke-grouponly | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| smoke-grouponly | all stages | $1.6293 | $0.1481 | $32.73 | $0.8146 | $0.0741 | $16.36 | 12.9 |
| smoke-none | interpret | $0.2117 | $0.0192 | $4.25 | $0.1058 | $0.0096 | $2.12 | 1.5 |
| smoke-none | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 1.7 |
| smoke-none | summarize | $0.1066 | $0.0097 | $2.14 | $0.0533 | $0.0049 | $1.07 | 2.4 |
| smoke-none | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| smoke-none | all stages | $0.3183 | $0.0289 | $6.40 | $0.1592 | $0.0144 | $3.20 | 5.8 |
| smoke-inc-transcribing | annotate | $0.8544 | $0.0777 | $17.17 | $0.4272 | $0.0389 | $8.59 | 5.3 |
| smoke-inc-transcribing | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| smoke-inc-transcribing | interpret | $0.2429 | $0.0221 | $4.88 | $0.1215 | $0.0111 | $2.44 | 1.3 |
| smoke-inc-transcribing | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.7 |
| smoke-inc-transcribing | summarize | $0.0930 | $0.0085 | $1.87 | $0.0465 | $0.0043 | $0.94 | 2.2 |
| smoke-inc-transcribing | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| smoke-inc-transcribing | all stages | $1.1903 | $0.1082 | $23.91 | $0.5951 | $0.0541 | $11.96 | 9.6 |
| smoke-inc-grouponly | annotate | $0.6662 | $0.0605 | $13.38 | $0.3331 | $0.0302 | $6.69 | 3.8 |
| smoke-inc-grouponly | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| smoke-inc-grouponly | interpret | $0.3091 | $0.0281 | $6.21 | $0.1545 | $0.0140 | $3.10 | 1.5 |
| smoke-inc-grouponly | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.7 |
| smoke-inc-grouponly | summarize | $0.1263 | $0.0115 | $2.54 | $0.0631 | $0.0057 | $1.27 | 2.5 |
| smoke-inc-grouponly | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| smoke-inc-grouponly | all stages | $1.1015 | $0.1001 | $22.13 | $0.5507 | $0.0500 | $11.06 | 8.7 |

The question set, outside $ / video, and the judge, apart (means per run):

| configuration | $ / question | s / question | question set $ | judge $ |
|---|---|---|---|---|
| smoke-transcribing | $0.1593 | 19.3 | $2.8679 | $0.1448 |
| smoke-grouponly | $0.1702 | 20.5 | $3.0637 | $0.1610 |
| smoke-none | $0.1665 | 23.0 | $2.9968 | $0.1598 |
| smoke-inc-transcribing | $0.1514 | 19.9 | $2.7260 | $0.1461 |
| smoke-inc-grouponly | $0.1888 | 21.2 | $3.3980 | $0.1552 |

Spend over all 15 runs: pipeline $20.1042; question set $45.1573; judge $2.3010 (what the last pass of `scry eval judge` paid: a verdict served from the judge's cache costs nothing).

## Commands

No span of this phase names a command list.

## Questions

**The positive questions (primary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| smoke-transcribing | 42 | 41 | 0 | 1 | 0 | 0.9286, 1, 1; mean 0.9762 | $0.1593 | $0.2238 | $49.46 |
| smoke-grouponly | 42 | 38 | 0 | 4 | 0 | 0.9286, 0.9286, 0.8571; mean 0.9048 | $0.1702 | $0.1481 | $32.73 |
| smoke-none | 42 | 36 | 0 | 6 | 0 | 0.8571, 0.8571, 0.8571; mean 0.8571 | $0.1665 | $0.0289 | $6.40 |
| smoke-inc-transcribing | 42 | 42 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1514 | $0.1082 | $23.91 |
| smoke-inc-grouponly | 42 | 39 | 0 | 3 | 0 | 1, 0.8571, 0.9286; mean 0.9286 | $0.1888 | $0.1001 | $22.13 |

**The negative questions (secondary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| smoke-transcribing | 12 | 12 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1593 | $0.2238 | $49.46 |
| smoke-grouponly | 12 | 12 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1702 | $0.1481 | $32.73 |
| smoke-none | 12 | 12 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1665 | $0.0289 | $6.40 |
| smoke-inc-transcribing | 12 | 12 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1514 | $0.1082 | $23.91 |
| smoke-inc-grouponly | 12 | 12 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1888 | $0.1001 | $22.13 |

Per question, the label of each repeat (every answer, with the judge's verdict and quote for each rubric line, is in `scores.json`).

| configuration | question | polarity | labels per repeat | $ / frame | $ / video |
|---|---|---|---|---|---|
| smoke-transcribing | Q1 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q2 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q3 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q4 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q5 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q6 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q7 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q8 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q9 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q10 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q11 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q12 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q13 | positive | wrong, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q14 | positive | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q15 | negative | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q16 | negative | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q17 | negative | correct, correct, correct | $0.2238 | $49.46 |
| smoke-transcribing | Q18 | negative | correct, correct, correct | $0.2238 | $49.46 |
| smoke-grouponly | Q1 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q2 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q3 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q4 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q5 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q6 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q7 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q8 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q9 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q10 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q11 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q12 | positive | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q13 | positive | correct, correct, wrong | $0.1481 | $32.73 |
| smoke-grouponly | Q14 | positive | wrong, wrong, wrong | $0.1481 | $32.73 |
| smoke-grouponly | Q15 | negative | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q16 | negative | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q17 | negative | correct, correct, correct | $0.1481 | $32.73 |
| smoke-grouponly | Q18 | negative | correct, correct, correct | $0.1481 | $32.73 |
| smoke-none | Q1 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q2 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q3 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q4 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q5 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q6 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q7 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q8 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q9 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q10 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q11 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q12 | positive | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q13 | positive | wrong, wrong, wrong | $0.0289 | $6.40 |
| smoke-none | Q14 | positive | wrong, wrong, wrong | $0.0289 | $6.40 |
| smoke-none | Q15 | negative | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q16 | negative | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q17 | negative | correct, correct, correct | $0.0289 | $6.40 |
| smoke-none | Q18 | negative | correct, correct, correct | $0.0289 | $6.40 |
| smoke-inc-transcribing | Q1 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q2 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q3 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q4 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q5 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q6 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q7 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q8 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q9 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q10 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q11 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q12 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q13 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q14 | positive | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q15 | negative | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q16 | negative | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q17 | negative | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-transcribing | Q18 | negative | correct, correct, correct | $0.1082 | $23.91 |
| smoke-inc-grouponly | Q1 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q2 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q3 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q4 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q5 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q6 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q7 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q8 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q9 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q10 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q11 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q12 | positive | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q13 | positive | correct, wrong, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q14 | positive | correct, wrong, wrong | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q15 | negative | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q16 | negative | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q17 | negative | correct, correct, correct | $0.1001 | $22.13 |
| smoke-inc-grouponly | Q18 | negative | correct, correct, correct | $0.1001 | $22.13 |

Stale answers (to a wording the question file no longer has), not judged: smoke-transcribing 0, smoke-grouponly 0, smoke-none 0, smoke-inc-transcribing 0, smoke-inc-grouponly 0. Unscored answers: smoke-transcribing 0, smoke-grouponly 0, smoke-none 0, smoke-inc-transcribing 0, smoke-inc-grouponly 0.

## Noise

Per configuration and metric: the value of each repeat (the mean of its units) and the largest paired difference between two repeats, which is the floor for one run against one run.

| configuration | metric | repeats | largest paired difference | $ / frame | $ / video |
|---|---|---|---|---|---|
| smoke-transcribing | questions.positive | 0.9286, 1, 1 | 0.071429 | $0.2238 | $49.46 |
| smoke-transcribing | questions.negative | 1, 1, 1 | 0 | $0.2238 | $49.46 |
| smoke-transcribing | cost.per_question | 0.158, 0.15, 0.17 | 0.019939 | $0.2238 | $49.46 |
| smoke-transcribing | cost.per_frame | 0.224, 0.226, 0.2214 | 0.0046 | $0.2238 | $49.46 |
| smoke-transcribing | seconds.per_frame | 25.3, 21.8, 22.2 | 3.5 | $0.2238 | $49.46 |
| smoke-grouponly | questions.positive | 0.9286, 0.9286, 0.8571 | 0.071429 | $0.1481 | $32.73 |
| smoke-grouponly | questions.negative | 1, 1, 1 | 0 | $0.1481 | $32.73 |
| smoke-grouponly | cost.per_question | 0.1724, 0.173, 0.1652 | 0.007828 | $0.1481 | $32.73 |
| smoke-grouponly | cost.per_frame | 0.1509, 0.1514, 0.142 | 0.0094 | $0.1481 | $32.73 |
| smoke-grouponly | seconds.per_frame | 12.4, 12.8, 13.5 | 1.1 | $0.1481 | $32.73 |
| smoke-none | questions.positive | 0.8571, 0.8571, 0.8571 | 0 | $0.0289 | $6.40 |
| smoke-none | questions.negative | 1, 1, 1 | 0 | $0.0289 | $6.40 |
| smoke-none | cost.per_question | 0.182, 0.1576, 0.1599 | 0.024456 | $0.0289 | $6.40 |
| smoke-none | cost.per_frame | 0.0343, 0.0274, 0.0251 | 0.0092 | $0.0289 | $6.40 |
| smoke-none | seconds.per_frame | 8.1, 5, 4.2 | 3.9 | $0.0289 | $6.40 |
| smoke-inc-transcribing | questions.positive | 1, 1, 1 | 0 | $0.1082 | $23.91 |
| smoke-inc-transcribing | questions.negative | 1, 1, 1 | 0 | $0.1082 | $23.91 |
| smoke-inc-transcribing | cost.per_question | 0.1452, 0.1531, 0.156 | 0.010767 | $0.1082 | $23.91 |
| smoke-inc-transcribing | cost.per_frame | 0.1044, 0.1127, 0.1074 | 0.0083 | $0.1082 | $23.91 |
| smoke-inc-transcribing | seconds.per_frame | 9.8, 9.8, 9.2 | 0.6 | $0.1082 | $23.91 |
| smoke-inc-grouponly | questions.positive | 1, 0.8571, 0.9286 | 0.142857 | $0.1001 | $22.13 |
| smoke-inc-grouponly | questions.negative | 1, 1, 1 | 0 | $0.1001 | $22.13 |
| smoke-inc-grouponly | cost.per_question | 0.1846, 0.1892, 0.1925 | 0.007911 | $0.1001 | $22.13 |
| smoke-inc-grouponly | cost.per_frame | 0.0964, 0.1019, 0.1021 | 0.0057 | $0.1001 | $22.13 |
| smoke-inc-grouponly | seconds.per_frame | 8.8, 8.7, 8.6 | 0.2 | $0.1001 | $22.13 |

## Comparisons

### smoke: A = smoke-transcribing, B = smoke-grouponly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| questions.positive | higher | 0.97619 | 0.904762 | -0.071429 | 0.04124 | outside | — | A | 14 | 0 | $0.2238 | $49.46 | $0.1481 | $32.73 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.2238 | $49.46 | $0.1481 | $32.73 |
| cost.per_question | lower | 0.15933 | 0.170206 | 0.010876 | 0.011512 | inside | — | — | 18 | 0 | $0.2238 | $49.46 | $0.1481 | $32.73 |
| cost.per_frame | lower | 0.2238 | 0.1481 | -0.0757 | 0.005427 | outside | — | B | 1 | 0 | $0.2238 | $49.46 | $0.1481 | $32.73 |
| seconds.per_frame | lower | 23.1 | 12.9 | -10.2 | 2.02073 | outside | — | B | 1 | 0 | $0.2238 | $49.46 | $0.1481 | $32.73 |

Units that every run of one side has and no run of the other:

- questions.positive: Q14@89ab64: A only

### smoke: A = smoke-transcribing, B = smoke-none

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| questions.positive | higher | 0.97619 | 0.857143 | -0.119048 | 0.04124 | outside | — | A | 14 | 0 | $0.2238 | $49.46 | $0.0289 | $6.40 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.2238 | $49.46 | $0.0289 | $6.40 |
| cost.per_question | lower | 0.15933 | 0.166489 | 0.007159 | 0.01412 | inside | — | — | 18 | 0 | $0.2238 | $49.46 | $0.0289 | $6.40 |
| cost.per_frame | lower | 0.2238 | 0.028933 | -0.194867 | 0.005312 | outside | — | B | 1 | 0 | $0.2238 | $49.46 | $0.0289 | $6.40 |
| seconds.per_frame | lower | 23.1 | 5.76667 | -17.3333 | 2.25167 | outside | — | B | 1 | 0 | $0.2238 | $49.46 | $0.0289 | $6.40 |

Units that every run of one side has and no run of the other:

- questions.positive: Q14@89ab64: A only

### smoke: A = smoke-transcribing, B = smoke-inc-transcribing

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| questions.positive | higher | 0.97619 | 1 | 0.02381 | 0.04124 | inside | — | — | 14 | 0 | $0.2238 | $49.46 | $0.1082 | $23.91 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.2238 | $49.46 | $0.1082 | $23.91 |
| cost.per_question | lower | 0.15933 | 0.151444 | -0.007885 | 0.011512 | inside | — | — | 18 | 0 | $0.2238 | $49.46 | $0.1082 | $23.91 |
| cost.per_frame | lower | 0.2238 | 0.108167 | -0.115633 | 0.004792 | outside | — | B | 1 | 0 | $0.2238 | $49.46 | $0.1082 | $23.91 |
| seconds.per_frame | lower | 23.1 | 9.6 | -13.5 | 2.02073 | outside | — | B | 1 | 0 | $0.2238 | $49.46 | $0.1082 | $23.91 |

### smoke: A = smoke-transcribing, B = smoke-inc-grouponly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| questions.positive | higher | 0.97619 | 0.928571 | -0.047619 | 0.082479 | inside | — | — | 14 | 0 | $0.2238 | $49.46 | $0.1001 | $22.13 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.2238 | $49.46 | $0.1001 | $22.13 |
| cost.per_question | lower | 0.15933 | 0.188778 | 0.029448 | 0.011512 | outside | — | A | 18 | 0 | $0.2238 | $49.46 | $0.1001 | $22.13 |
| cost.per_frame | lower | 0.2238 | 0.100133 | -0.123667 | 0.003291 | outside | — | B | 1 | 0 | $0.2238 | $49.46 | $0.1001 | $22.13 |
| seconds.per_frame | lower | 23.1 | 8.7 | -14.4 | 2.02073 | outside | — | B | 1 | 0 | $0.2238 | $49.46 | $0.1001 | $22.13 |

### smoke: A = smoke-grouponly, B = smoke-none

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| questions.positive | higher | 0.904762 | 0.857143 | -0.047619 | 0.04124 | outside | — | A | 14 | 0 | $0.1481 | $32.73 | $0.0289 | $6.40 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.1481 | $32.73 | $0.0289 | $6.40 |
| cost.per_question | lower | 0.170206 | 0.166489 | -0.003717 | 0.01412 | inside | — | — | 18 | 0 | $0.1481 | $32.73 | $0.0289 | $6.40 |
| cost.per_frame | lower | 0.1481 | 0.028933 | -0.119167 | 0.005427 | outside | — | B | 1 | 0 | $0.1481 | $32.73 | $0.0289 | $6.40 |
| seconds.per_frame | lower | 12.9 | 5.76667 | -7.13333 | 2.25167 | outside | — | B | 1 | 0 | $0.1481 | $32.73 | $0.0289 | $6.40 |

### smoke: A = smoke-grouponly, B = smoke-inc-transcribing

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| questions.positive | higher | 0.904762 | 1 | 0.095238 | 0.04124 | outside | — | B | 14 | 0 | $0.1481 | $32.73 | $0.1082 | $23.91 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.1481 | $32.73 | $0.1082 | $23.91 |
| cost.per_question | lower | 0.170206 | 0.151444 | -0.018761 | 0.006216 | outside | — | B | 18 | 0 | $0.1481 | $32.73 | $0.1082 | $23.91 |
| cost.per_frame | lower | 0.1481 | 0.108167 | -0.039933 | 0.005427 | outside | — | B | 1 | 0 | $0.1481 | $32.73 | $0.1082 | $23.91 |
| seconds.per_frame | lower | 12.9 | 9.6 | -3.3 | 0.635085 | outside | — | B | 1 | 0 | $0.1481 | $32.73 | $0.1082 | $23.91 |

Units that every run of one side has and no run of the other:

- questions.positive: Q14@89ab64: B only

### smoke: A = smoke-grouponly, B = smoke-inc-grouponly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| questions.positive | higher | 0.904762 | 0.928571 | 0.02381 | 0.082479 | inside | — | — | 14 | 0 | $0.1481 | $32.73 | $0.1001 | $22.13 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.1481 | $32.73 | $0.1001 | $22.13 |
| cost.per_question | lower | 0.170206 | 0.188778 | 0.018572 | 0.004567 | outside | — | A | 18 | 0 | $0.1481 | $32.73 | $0.1001 | $22.13 |
| cost.per_frame | lower | 0.1481 | 0.100133 | -0.047967 | 0.005427 | outside | — | B | 1 | 0 | $0.1481 | $32.73 | $0.1001 | $22.13 |
| seconds.per_frame | lower | 12.9 | 8.7 | -4.2 | 0.635085 | outside | — | B | 1 | 0 | $0.1481 | $32.73 | $0.1001 | $22.13 |

### smoke: A = smoke-none, B = smoke-inc-transcribing

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| questions.positive | higher | 0.857143 | 1 | 0.142857 | 0 | outside | — | B | 14 | 0 | $0.0289 | $6.40 | $0.1082 | $23.91 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.0289 | $6.40 | $0.1082 | $23.91 |
| cost.per_question | lower | 0.166489 | 0.151444 | -0.015044 | 0.01412 | outside | — | B | 18 | 0 | $0.0289 | $6.40 | $0.1082 | $23.91 |
| cost.per_frame | lower | 0.028933 | 0.108167 | 0.079233 | 0.005312 | outside | — | A | 1 | 0 | $0.0289 | $6.40 | $0.1082 | $23.91 |
| seconds.per_frame | lower | 5.76667 | 9.6 | 3.83333 | 2.25167 | outside | — | A | 1 | 0 | $0.0289 | $6.40 | $0.1082 | $23.91 |

Units that every run of one side has and no run of the other:

- questions.positive: Q13@4f6ffc: B only
- questions.positive: Q14@89ab64: B only

### smoke: A = smoke-none, B = smoke-inc-grouponly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| questions.positive | higher | 0.857143 | 0.928571 | 0.071429 | 0.082479 | inside | — | — | 14 | 0 | $0.0289 | $6.40 | $0.1001 | $22.13 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.0289 | $6.40 | $0.1001 | $22.13 |
| cost.per_question | lower | 0.166489 | 0.188778 | 0.022289 | 0.01412 | outside | — | A | 18 | 0 | $0.0289 | $6.40 | $0.1001 | $22.13 |
| cost.per_frame | lower | 0.028933 | 0.100133 | 0.0712 | 0.005312 | outside | — | A | 1 | 0 | $0.0289 | $6.40 | $0.1001 | $22.13 |
| seconds.per_frame | lower | 5.76667 | 8.7 | 2.93333 | 2.25167 | outside | — | A | 1 | 0 | $0.0289 | $6.40 | $0.1001 | $22.13 |

### smoke: A = smoke-inc-transcribing, B = smoke-inc-grouponly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| questions.positive | higher | 1 | 0.928571 | -0.071429 | 0.082479 | inside | — | — | 14 | 0 | $0.1082 | $23.91 | $0.1001 | $22.13 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.1082 | $23.91 | $0.1001 | $22.13 |
| cost.per_question | lower | 0.151444 | 0.188778 | 0.037333 | 0.006216 | outside | — | A | 18 | 0 | $0.1082 | $23.91 | $0.1001 | $22.13 |
| cost.per_frame | lower | 0.108167 | 0.100133 | -0.008033 | 0.004792 | outside | — | B | 1 | 0 | $0.1082 | $23.91 | $0.1001 | $22.13 |
| seconds.per_frame | lower | 9.6 | 8.7 | -0.9 | 0.34641 | outside | — | B | 1 | 0 | $0.1082 | $23.91 | $0.1001 | $22.13 |
