# p1 evaluation report

Date: 2026-09-21. Matrix: `evals/p1.toml`. Source run: `runs/p0`. Runs: 18.

Runs by status: done 18.
Commits the runs started on: `71ef8c642998` (4 runs), `b644274c499c` (7 runs), `f0e76916a72f` (7 runs).
Runs that started on a dirty tree: smoke-transcribing-r1, smoke-transcribing-r2, smoke-transcribing-r3, smoke-grouponly-r1, smoke-grouponly-r2, smoke-grouponly-r3, smoke-none-r1, smoke-none-r2, smoke-none-r3, span2-transcribing-r1, span2-transcribing-r2, span2-transcribing-r3, span2-grouponly-r1, span2-grouponly-r2, span2-grouponly-r3, span2-none-r1, span2-none-r2, span2-none-r3.

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
- span2-grouponly-r1: no second reader: exact.vlm not scored
- span2-grouponly-r2: no second reader: exact.vlm not scored
- span2-grouponly-r3: no second reader: exact.vlm not scored
- span2-none-r1: no annotations
- span2-none-r1: no second reader: exact.vlm not scored
- span2-none-r2: no annotations
- span2-none-r2: no second reader: exact.vlm not scored
- span2-none-r3: no annotations
- span2-none-r3: no second reader: exact.vlm not scored

## Runs

| run | status | frames | cold | resumed | cache hits | $ | $ / frame | $ / video | wall s |
|---|---|---|---|---|---|---|---|---|---|
| smoke-transcribing-r1 | done | 11 | yes | no | 0 | $2.4639 | $0.2240 | $49.50 | 265.1 |
| smoke-transcribing-r2 | done | 11 | yes | no | 0 | $2.4293 | $0.2208 | $48.81 | 234.1 |
| smoke-transcribing-r3 | done | 11 | yes | no | 0 | $2.5158 | $0.2287 | $50.54 | 264.6 |
| smoke-grouponly-r1 | done | 11 | yes | no | 0 | $1.6179 | $0.1471 | $32.51 | 150.2 |
| smoke-grouponly-r2 | done | 11 | yes | no | 0 | $1.5096 | $0.1372 | $30.33 | 146.7 |
| smoke-grouponly-r3 | done | 11 | yes | no | 0 | $1.5429 | $0.1403 | $31.00 | 154.0 |
| smoke-none-r1 | done | 11 | yes | no | 0 | $0.3025 | $0.0275 | $6.08 | 51.8 |
| smoke-none-r2 | done | 11 | yes | no | 0 | $0.3062 | $0.0278 | $6.15 | 54.7 |
| smoke-none-r3 | done | 11 | yes | no | 0 | $0.3036 | $0.0276 | $6.10 | 55.1 |
| span2-transcribing-r1 | done | 33 | yes | no | 0 | $7.9915 | $0.2422 | $53.52 | 1061.4 |
| span2-transcribing-r2 | done | 33 | yes | no | 0 | $8.1294 | $0.2463 | $54.44 | 957.6 |
| span2-transcribing-r3 | done | 33 | yes | no | 0 | $8.3814 | $0.2540 | $56.13 | 972.3 |
| span2-grouponly-r1 | done | 33 | yes | no | 0 | $4.7036 | $0.1425 | $31.50 | 786.3 |
| span2-grouponly-r2 | done | 33 | yes | no | 0 | $4.6580 | $0.1412 | $31.19 | 709.7 |
| span2-grouponly-r3 | done | 33 | yes | no | 0 | $4.6995 | $0.1424 | $31.47 | 751.7 |
| span2-none-r1 | done | 33 | yes | no | 0 | $0.8144 | $0.0247 | $5.45 | 499.7 |
| span2-none-r2 | done | 33 | yes | no | 0 | $0.8185 | $0.0248 | $5.48 | 418.1 |
| span2-none-r3 | done | 33 | yes | no | 0 | $0.8145 | $0.0247 | $5.45 | 413.4 |

The stages' own counters, reported, never compared:

| run | annotate | interpret |
|---|---|---|
| smoke-transcribing-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 2, "link_malformed": 11, "second_text": 6}, "repairs": 19} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-transcribing-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_malformed": 11}, "repairs": 11} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-transcribing-r3 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_malformed": 3, "second_text": 2}, "repairs": 5} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-grouponly-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {}, "repairs": 0} | {"errors": 0, "invalid_citations": 1, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-grouponly-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 3, "link_malformed": 2}, "repairs": 5} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-grouponly-r3 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 1, "link_malformed": 4}, "repairs": 5} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-none-r1 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-none-r2 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| smoke-none-r3 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 10, "unclear": 0, "yes": 0}} |
| span2-transcribing-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 4, "link_malformed": 19, "second_text": 3}, "repairs": 26} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-transcribing-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 2, "link_malformed": 7, "second_text": 2}, "repairs": 11} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 22, "unclear": 1, "yes": 9}} |
| span2-transcribing-r3 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 5, "link_malformed": 28, "second_text": 1, "text_unknown_box": 1}, "repairs": 35} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-grouponly-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 3, "link_malformed": 11}, "repairs": 14} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-grouponly-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 3, "link_malformed": 17}, "repairs": 20} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-grouponly-r3 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 1, "link_malformed": 13}, "repairs": 14} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-none-r1 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-none-r2 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-none-r3 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |

## Cost

Means over a configuration's repeats, per stage. One figure per stage, at the synchronous list price; the batch columns are half of it.

| configuration | stage | $ | $ / frame | $ / video | batch $ | batch $ / frame | batch $ / video | s / frame |
|---|---|---|---|---|---|---|---|---|
| smoke-transcribing | annotate | $2.1023 | $0.1911 | $42.24 | $1.0512 | $0.0955 | $21.12 | 16.8 |
| smoke-transcribing | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| smoke-transcribing | interpret | $0.2439 | $0.0222 | $4.90 | $0.1220 | $0.0111 | $2.45 | 1.5 |
| smoke-transcribing | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 1.8 |
| smoke-transcribing | summarize | $0.1235 | $0.0112 | $2.48 | $0.0617 | $0.0056 | $1.24 | 2.9 |
| smoke-transcribing | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| smoke-transcribing | all stages | $2.4697 | $0.2245 | $49.62 | $1.2349 | $0.1123 | $24.81 | 23.2 |
| smoke-grouponly | annotate | $1.1863 | $0.1079 | $23.84 | $0.5931 | $0.0539 | $11.92 | 8.5 |
| smoke-grouponly | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| smoke-grouponly | interpret | $0.2439 | $0.0222 | $4.90 | $0.1220 | $0.0111 | $2.45 | 1.3 |
| smoke-grouponly | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.8 |
| smoke-grouponly | summarize | $0.1266 | $0.0115 | $2.55 | $0.0633 | $0.0057 | $1.27 | 3.0 |
| smoke-grouponly | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| smoke-grouponly | all stages | $1.5568 | $0.1415 | $31.28 | $0.7784 | $0.0707 | $15.64 | 13.7 |
| smoke-none | interpret | $0.1888 | $0.0172 | $3.79 | $0.0944 | $0.0086 | $1.90 | 1.4 |
| smoke-none | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.7 |
| smoke-none | summarize | $0.1153 | $0.0105 | $2.32 | $0.0576 | $0.0053 | $1.16 | 2.7 |
| smoke-none | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| smoke-none | all stages | $0.3041 | $0.0276 | $6.11 | $0.1520 | $0.0138 | $3.06 | 4.9 |
| span2-transcribing | annotate | $7.1373 | $0.2163 | $47.80 | $3.5686 | $0.1081 | $23.90 | 17.3 |
| span2-transcribing | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| span2-transcribing | interpret | $0.7382 | $0.0224 | $4.94 | $0.3691 | $0.0112 | $2.47 | 1.2 |
| span2-transcribing | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 1.8 |
| span2-transcribing | summarize | $0.2920 | $0.0088 | $1.95 | $0.1460 | $0.0044 | $0.97 | 1.3 |
| span2-transcribing | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| span2-transcribing | ask | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 8.5 |
| span2-transcribing | all stages | $8.1674 | $0.2475 | $54.70 | $4.0837 | $0.1237 | $27.35 | 30.2 |
| span2-grouponly | annotate | $3.7302 | $0.1131 | $24.98 | $1.8651 | $0.0566 | $12.49 | 8.4 |
| span2-grouponly | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| span2-grouponly | interpret | $0.6966 | $0.0211 | $4.66 | $0.3483 | $0.0106 | $2.33 | 1.3 |
| span2-grouponly | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 1.7 |
| span2-grouponly | summarize | $0.2603 | $0.0079 | $1.74 | $0.1301 | $0.0040 | $0.87 | 1.4 |
| span2-grouponly | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| span2-grouponly | ask | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 9.8 |
| span2-grouponly | all stages | $4.6870 | $0.1420 | $31.39 | $2.3435 | $0.0710 | $15.70 | 22.7 |
| span2-none | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| span2-none | interpret | $0.5598 | $0.0170 | $3.75 | $0.2799 | $0.0085 | $1.88 | 1.2 |
| span2-none | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 1.8 |
| span2-none | summarize | $0.2560 | $0.0078 | $1.71 | $0.1280 | $0.0039 | $0.85 | 1.4 |
| span2-none | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| span2-none | ask | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 9.0 |
| span2-none | all stages | $0.8158 | $0.0247 | $5.46 | $0.4079 | $0.0123 | $2.73 | 13.4 |

The question set, outside $ / video, and the judge, apart (means per run):

| configuration | $ / question | question set $ | judge $ |
|---|---|---|---|
| span2-transcribing | $0.2005 | $3.0071 | $0.1131 |
| span2-grouponly | $0.1979 | $2.9692 | $0.1202 |
| span2-none | $0.1786 | $2.6786 | $0.1132 |

Spend over all 18 runs: pipeline $54.0025; question set $25.9646; judge $1.0394 (what the last pass of `scry eval judge` paid: a verdict served from the judge's cache costs nothing).

## Commands

**Primary, side by side, with no order between them:** found and exact, as k/n of the rated entries per repeat, then the mean. Every comparison with the command list is by frame number. `exact.any` is what compares bases that have different readers; it can only tie or rise with a second reader, so it is shown as what the second reading adds, at its price, beside `exact.ocr`, not as a contest.

| configuration | found | exact.ocr | exact.vlm | exact.any | $ / frame | $ / video |
|---|---|---|---|---|---|---|
| span2-transcribing | 7/7, 7/7, 7/7; mean 1 | 7/7, 7/7, 7/7; mean 1 | 7/7, 7/7, 7/7; mean 1 | 7/7, 7/7, 7/7; mean 1 | $0.2475 | $54.70 |
| span2-grouponly | 7/7, 7/7, 7/7; mean 1 | 7/7, 7/7, 7/7; mean 1 | —, —, — | 7/7, 7/7, 7/7; mean 1 | $0.1420 | $31.39 |
| span2-none | 7/7, 7/7, 7/7; mean 1 | 7/7, 7/7, 7/7; mean 1 | —, —, — | 7/7, 7/7, 7/7; mean 1 | $0.0247 | $5.46 |

**Secondary:** the first-appearance error and the submission error (mean absolute frames over the entries that have one, per repeat), submitted and false run (k/n per repeat).

| configuration | first appearance, ocr | first appearance, vlm | first appearance, any | submitted | submission error | false run | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|
| span2-transcribing | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7, 7/7; mean 1 | 0 over 7, 0 over 7, 0 over 7; mean 0 | 0/5, 0/5, 0/5; mean 0 | $0.2475 | $54.70 |
| span2-grouponly | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | —, —, — | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7, 7/7; mean 1 | 0 over 7, 0 over 7, 0 over 7; mean 0 | 0/5, 0/5, 0/5; mean 0 | $0.1420 | $31.39 |
| span2-none | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | —, —, — | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7, 7/7; mean 1 | 0 over 7, 0 over 7, 0 over 7; mean 0 | 0/5, 0/5, 0/5; mean 0 | $0.0247 | $5.46 |

Per entry, in how many runs (of those that scored it). `summary only`: no localising entry covered the command and a summary entry of that level quoted it. `Y` and `y` are reported and not rated.

| configuration | # | text | found | exact.any | submitted | summary only | note | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| span2-transcribing | 1 | `az account show` | 3/3 | 3/3 | 3/3 | — | — | $0.2475 | $54.70 |
| span2-transcribing | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 3/3 | 3/3 | 3/3 | — | — | $0.2475 | $54.70 |
| span2-transcribing | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 3/3 | 3/3 | 3/3 | — | — | $0.2475 | $54.70 |
| span2-transcribing | 4 | `Y` | — | 3/3 | 3/3 | — | not rated | $0.2475 | $54.70 |
| span2-transcribing | 5 | `y` | — | 3/3 | 3/3 | — | not rated | $0.2475 | $54.70 |
| span2-transcribing | 6 | `kubectl config current-context` | 3/3 | 3/3 | 3/3 | — | — | $0.2475 | $54.70 |
| span2-transcribing | 7 | `kubectl get nodes` | 3/3 | 3/3 | 3/3 | — | — | $0.2475 | $54.70 |
| span2-transcribing | 8 | `kubectl get deployment` | 3/3 | 3/3 | 3/3 | — | — | $0.2475 | $54.70 |
| span2-transcribing | 9 | `kubectl get pods` | 3/3 | 3/3 | 3/3 | — | — | $0.2475 | $54.70 |
| span2-grouponly | 1 | `az account show` | 3/3 | 3/3 | 3/3 | — | — | $0.1420 | $31.39 |
| span2-grouponly | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 3/3 | 3/3 | 3/3 | — | — | $0.1420 | $31.39 |
| span2-grouponly | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 3/3 | 3/3 | 3/3 | — | — | $0.1420 | $31.39 |
| span2-grouponly | 4 | `Y` | — | 3/3 | 3/3 | — | not rated | $0.1420 | $31.39 |
| span2-grouponly | 5 | `y` | — | 3/3 | 3/3 | — | not rated | $0.1420 | $31.39 |
| span2-grouponly | 6 | `kubectl config current-context` | 3/3 | 3/3 | 3/3 | — | — | $0.1420 | $31.39 |
| span2-grouponly | 7 | `kubectl get nodes` | 3/3 | 3/3 | 3/3 | — | — | $0.1420 | $31.39 |
| span2-grouponly | 8 | `kubectl get deployment` | 3/3 | 3/3 | 3/3 | — | — | $0.1420 | $31.39 |
| span2-grouponly | 9 | `kubectl get pods` | 3/3 | 3/3 | 3/3 | — | — | $0.1420 | $31.39 |
| span2-none | 1 | `az account show` | 3/3 | 3/3 | 3/3 | — | — | $0.0247 | $5.46 |
| span2-none | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 3/3 | 3/3 | 3/3 | — | — | $0.0247 | $5.46 |
| span2-none | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 3/3 | 3/3 | 3/3 | — | — | $0.0247 | $5.46 |
| span2-none | 4 | `Y` | — | 3/3 | 0/3 | — | not rated | $0.0247 | $5.46 |
| span2-none | 5 | `y` | — | 3/3 | 3/3 | — | not rated | $0.0247 | $5.46 |
| span2-none | 6 | `kubectl config current-context` | 3/3 | 3/3 | 3/3 | — | — | $0.0247 | $5.46 |
| span2-none | 7 | `kubectl get nodes` | 3/3 | 3/3 | 3/3 | — | — | $0.0247 | $5.46 |
| span2-none | 8 | `kubectl get deployment` | 3/3 | 3/3 | 3/3 | — | — | $0.0247 | $5.46 |
| span2-none | 9 | `kubectl get pods` | 3/3 | 3/3 | 3/3 | — | — | $0.0247 | $5.46 |

Texts that appeared on screen and were never run: in how many runs a `submitted: yes` claimed them (false run).

| configuration | row | text | false run | $ / frame | $ / video |
|---|---|---|---|---|---|
| span2-transcribing | N1 | `az login` | 0/3 | $0.2475 | $54.70 |
| span2-transcribing | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/3 | $0.2475 | $54.70 |
| span2-transcribing | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/3 | $0.2475 | $54.70 |
| span2-transcribing | N4 | `kubectl config current-context` | 0/3 | $0.2475 | $54.70 |
| span2-transcribing | N5 | `kubectl get svc` | 0/3 | $0.2475 | $54.70 |
| span2-grouponly | N1 | `az login` | 0/3 | $0.1420 | $31.39 |
| span2-grouponly | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/3 | $0.1420 | $31.39 |
| span2-grouponly | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/3 | $0.1420 | $31.39 |
| span2-grouponly | N4 | `kubectl config current-context` | 0/3 | $0.1420 | $31.39 |
| span2-grouponly | N5 | `kubectl get svc` | 0/3 | $0.1420 | $31.39 |
| span2-none | N1 | `az login` | 0/3 | $0.0247 | $5.46 |
| span2-none | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/3 | $0.0247 | $5.46 |
| span2-none | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/3 | $0.0247 | $5.46 |
| span2-none | N4 | `kubectl config current-context` | 0/3 | $0.0247 | $5.46 |
| span2-none | N5 | `kubectl get svc` | 0/3 | $0.0247 | $5.46 |

## Questions

**The positive questions (primary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| span2-transcribing | 33 | 33 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.2005 | $0.2475 | $54.70 |
| span2-grouponly | 33 | 33 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1979 | $0.1420 | $31.39 |
| span2-none | 33 | 33 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1786 | $0.0247 | $5.46 |

**The negative questions (secondary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| span2-transcribing | 12 | 12 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.2005 | $0.2475 | $54.70 |
| span2-grouponly | 12 | 12 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1979 | $0.1420 | $31.39 |
| span2-none | 12 | 12 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1786 | $0.0247 | $5.46 |

Per question, the label of each repeat (every answer, with the judge's verdict and quote for each rubric line, is in `scores.json`).

| configuration | question | polarity | labels per repeat | $ / frame | $ / video |
|---|---|---|---|---|---|
| span2-transcribing | Q1 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q2 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q3 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q4 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q5 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q6 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q7 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q8 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q9 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q10 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q11 | positive | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q12 | negative | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q13 | negative | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q14 | negative | correct, correct, correct | $0.2475 | $54.70 |
| span2-transcribing | Q15 | negative | correct, correct, correct | $0.2475 | $54.70 |
| span2-grouponly | Q1 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q2 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q3 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q4 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q5 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q6 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q7 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q8 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q9 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q10 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q11 | positive | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q12 | negative | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q13 | negative | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q14 | negative | correct, correct, correct | $0.1420 | $31.39 |
| span2-grouponly | Q15 | negative | correct, correct, correct | $0.1420 | $31.39 |
| span2-none | Q1 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q2 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q3 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q4 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q5 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q6 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q7 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q8 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q9 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q10 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q11 | positive | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q12 | negative | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q13 | negative | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q14 | negative | correct, correct, correct | $0.0247 | $5.46 |
| span2-none | Q15 | negative | correct, correct, correct | $0.0247 | $5.46 |

Stale answers (to a wording the question file no longer has), not judged: span2-transcribing 0, span2-grouponly 0, span2-none 0. Unscored answers: span2-transcribing 0, span2-grouponly 0, span2-none 0.

## Noise

Per configuration and metric: the value of each repeat (the mean of its units) and the largest paired difference between two repeats, which is the floor for one run against one run.

| configuration | metric | repeats | largest paired difference | $ / frame | $ / video |
|---|---|---|---|---|---|
| smoke-transcribing | cost.per_frame | 0.224, 0.2208, 0.2287 | 0.0079 | $0.2245 | $49.62 |
| smoke-transcribing | seconds.per_frame | 24.1, 21.3, 24.1 | 2.8 | $0.2245 | $49.62 |
| smoke-grouponly | cost.per_frame | 0.1471, 0.1372, 0.1403 | 0.0099 | $0.1415 | $31.28 |
| smoke-grouponly | seconds.per_frame | 13.7, 13.3, 14 | 0.7 | $0.1415 | $31.28 |
| smoke-none | cost.per_frame | 0.0275, 0.0278, 0.0276 | 0.0003 | $0.0276 | $6.11 |
| smoke-none | seconds.per_frame | 4.7, 5, 5 | 0.3 | $0.0276 | $6.11 |
| span2-transcribing | found | 1, 1, 1 | 0 | $0.2475 | $54.70 |
| span2-transcribing | exact.ocr | 1, 1, 1 | 0 | $0.2475 | $54.70 |
| span2-transcribing | exact.vlm | 1, 1, 1 | 0 | $0.2475 | $54.70 |
| span2-transcribing | exact.any | 1, 1, 1 | 0 | $0.2475 | $54.70 |
| span2-transcribing | submitted | 1, 1, 1 | 0 | $0.2475 | $54.70 |
| span2-transcribing | first_frame_error_abs.any | 0.1429, 0.1429, 0.1429 | 0 | $0.2475 | $54.70 |
| span2-transcribing | submit_frame_error_abs | 0, 0, 0 | 0 | $0.2475 | $54.70 |
| span2-transcribing | false_run | 0, 0, 0 | 0 | $0.2475 | $54.70 |
| span2-transcribing | questions.positive | 1, 1, 1 | 0 | $0.2475 | $54.70 |
| span2-transcribing | questions.negative | 1, 1, 1 | 0 | $0.2475 | $54.70 |
| span2-transcribing | cost.per_question | 0.2082, 0.1939, 0.1994 | 0.01432 | $0.2475 | $54.70 |
| span2-transcribing | cost.per_frame | 0.2422, 0.2463, 0.254 | 0.0118 | $0.2475 | $54.70 |
| span2-transcribing | seconds.per_frame | 32.2, 29, 29.5 | 3.2 | $0.2475 | $54.70 |
| span2-grouponly | found | 1, 1, 1 | 0 | $0.1420 | $31.39 |
| span2-grouponly | exact.ocr | 1, 1, 1 | 0 | $0.1420 | $31.39 |
| span2-grouponly | exact.any | 1, 1, 1 | 0 | $0.1420 | $31.39 |
| span2-grouponly | submitted | 1, 1, 1 | 0 | $0.1420 | $31.39 |
| span2-grouponly | first_frame_error_abs.any | 0.1429, 0.1429, 0.1429 | 0 | $0.1420 | $31.39 |
| span2-grouponly | submit_frame_error_abs | 0, 0, 0 | 0 | $0.1420 | $31.39 |
| span2-grouponly | false_run | 0, 0, 0 | 0 | $0.1420 | $31.39 |
| span2-grouponly | questions.positive | 1, 1, 1 | 0 | $0.1420 | $31.39 |
| span2-grouponly | questions.negative | 1, 1, 1 | 0 | $0.1420 | $31.39 |
| span2-grouponly | cost.per_question | 0.1998, 0.1997, 0.1943 | 0.005533 | $0.1420 | $31.39 |
| span2-grouponly | cost.per_frame | 0.1425, 0.1412, 0.1424 | 0.0013 | $0.1420 | $31.39 |
| span2-grouponly | seconds.per_frame | 23.8, 21.5, 22.8 | 2.3 | $0.1420 | $31.39 |
| span2-none | found | 1, 1, 1 | 0 | $0.0247 | $5.46 |
| span2-none | exact.ocr | 1, 1, 1 | 0 | $0.0247 | $5.46 |
| span2-none | exact.any | 1, 1, 1 | 0 | $0.0247 | $5.46 |
| span2-none | submitted | 1, 1, 1 | 0 | $0.0247 | $5.46 |
| span2-none | first_frame_error_abs.any | 0.1429, 0.1429, 0.1429 | 0 | $0.0247 | $5.46 |
| span2-none | submit_frame_error_abs | 0, 0, 0 | 0 | $0.0247 | $5.46 |
| span2-none | false_run | 0, 0, 0 | 0 | $0.0247 | $5.46 |
| span2-none | questions.positive | 1, 1, 1 | 0 | $0.0247 | $5.46 |
| span2-none | questions.negative | 1, 1, 1 | 0 | $0.0247 | $5.46 |
| span2-none | cost.per_question | 0.1892, 0.1744, 0.1722 | 0.01698 | $0.0247 | $5.46 |
| span2-none | cost.per_frame | 0.0247, 0.0248, 0.0247 | 0.0001 | $0.0247 | $5.46 |
| span2-none | seconds.per_frame | 15.1, 12.7, 12.5 | 2.6 | $0.0247 | $5.46 |

## Comparisons

### smoke: A = smoke-transcribing, B = smoke-grouponly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cost.per_frame | lower | 0.2245 | 0.141533 | -0.082967 | 0.005716 | outside | — | B | 1 | 0 | $0.2245 | $49.62 | $0.1415 | $31.28 |
| seconds.per_frame | lower | 23.1667 | 13.6667 | -9.5 | 1.61658 | outside | — | B | 1 | 0 | $0.2245 | $49.62 | $0.1415 | $31.28 |

### smoke: A = smoke-transcribing, B = smoke-none

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cost.per_frame | lower | 0.2245 | 0.027633 | -0.196867 | 0.004561 | outside | — | B | 1 | 0 | $0.2245 | $49.62 | $0.0276 | $6.11 |
| seconds.per_frame | lower | 23.1667 | 4.9 | -18.2667 | 1.61658 | outside | — | B | 1 | 0 | $0.2245 | $49.62 | $0.0276 | $6.11 |

### smoke: A = smoke-grouponly, B = smoke-none

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cost.per_frame | lower | 0.141533 | 0.027633 | -0.1139 | 0.005716 | outside | — | B | 1 | 0 | $0.1415 | $31.28 | $0.0276 | $6.11 |
| seconds.per_frame | lower | 13.6667 | 4.9 | -8.76667 | 0.404145 | outside | — | B | 1 | 0 | $0.1415 | $31.28 | $0.0276 | $6.11 |

### span2: A = span2-transcribing, B = span2-grouponly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| found | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| exact.ocr | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| exact.vlm | higher | — | — | — | — | not comparable | absent in B | — | 0 | 7 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| exact.any | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| submitted | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| first_frame_error_abs.any | lower | 0.142857 | 0.142857 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| submit_frame_error_abs | lower | 0 | 0 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| false_run | lower | 0 | 0 | 0 | 0 | inside | — | — | 5 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| questions.positive | higher | 1 | 1 | 0 | 0 | inside | — | — | 11 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| cost.per_question | lower | 0.200476 | 0.197944 | -0.002531 | 0.008268 | inside | — | — | 15 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| cost.per_frame | lower | 0.2475 | 0.142033 | -0.105467 | 0.006813 | outside | — | B | 1 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |
| seconds.per_frame | lower | 30.2333 | 22.7 | -7.53333 | 1.84752 | outside | — | B | 1 | 0 | $0.2475 | $54.70 | $0.1420 | $31.39 |

### span2: A = span2-transcribing, B = span2-none

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| found | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| exact.ocr | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| exact.vlm | higher | — | — | — | — | not comparable | absent in B | — | 0 | 7 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| exact.any | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| submitted | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| first_frame_error_abs.any | lower | 0.142857 | 0.142857 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| submit_frame_error_abs | lower | 0 | 0 | 0 | 0 | inside | — | — | 7 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| false_run | lower | 0 | 0 | 0 | 0 | inside | — | — | 5 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| questions.positive | higher | 1 | 1 | 0 | 0 | inside | — | — | 11 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| cost.per_question | lower | 0.200476 | 0.178571 | -0.021904 | 0.009803 | outside | — | B | 15 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| cost.per_frame | lower | 0.2475 | 0.024733 | -0.222767 | 0.006813 | outside | — | B | 1 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |
| seconds.per_frame | lower | 30.2333 | 13.4333 | -16.8 | 1.84752 | outside | — | B | 1 | 0 | $0.2475 | $54.70 | $0.0247 | $5.46 |

### span2: A = span2-grouponly, B = span2-none

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| found | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| exact.ocr | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| exact.any | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| submitted | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| first_frame_error_abs.any | lower | 0.142857 | 0.142857 | 0 | 0 | inside | — | — | 7 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| submit_frame_error_abs | lower | 0 | 0 | 0 | 0 | inside | — | — | 7 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| false_run | lower | 0 | 0 | 0 | 0 | inside | — | — | 5 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| questions.positive | higher | 1 | 1 | 0 | 0 | inside | — | — | 11 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| cost.per_question | lower | 0.197944 | 0.178571 | -0.019373 | 0.009803 | outside | — | B | 15 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| cost.per_frame | lower | 0.142033 | 0.024733 | -0.1173 | 0.000751 | outside | — | B | 1 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
| seconds.per_frame | lower | 22.7 | 13.4333 | -9.26667 | 1.50111 | outside | — | B | 1 | 0 | $0.1420 | $31.39 | $0.0247 | $5.46 |
