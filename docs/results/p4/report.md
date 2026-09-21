# p4 evaluation report

Date: 2026-09-21. Matrix: `evals/p4.toml`. Source run: `runs/p0`. Runs: 4.

Runs by status: done 4.
Commits the runs started on: `6ac8d6300add` (4 runs).
Runs that started on a dirty tree: none.

$ / video = $ / frame × 221 frames, a linear projection from this span to the whole source video. Dollars are what a cold run pays at the synchronous list price, from the stages' manifest usage (an answer served from a call cache is priced as if paid); the batch price is half. The question set's dollars are per question and outside $ / video; the judge's dollars are apart from both.

An `outside` row means only that the difference is larger than the largest difference seen between identical cold runs of the two configurations, scaled for means of repeats. With three repeats a side that floor is a range of three values: by a normal approximation about one row in eight reads `outside` when nothing differs [estimated], and this report has dozens of rows. One `outside` row is weak evidence. Nothing here is a verdict, and no row decides anything by itself.

## Warnings

none

Notes (expected absences):

- full-none-r1: no annotations
- full-none-r1: no second reader: exact.vlm not scored
- full-none-r2: no annotations
- full-none-r2: no second reader: exact.vlm not scored

## Runs

| run | status | frames | cold | resumed | cache hits | $ | $ / frame | $ / video | pipeline s | questions s |
|---|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-r1 | done | 221 | yes | no | 0 | $17.7736 | $0.0804 | $17.77 | 1857.0 | 609.5 |
| full-inc-transcribing-r2 | done | 221 | yes | no | 0 | $17.9202 | $0.0811 | $17.92 | 1846.0 | 613.4 |
| full-none-r1 | done | 221 | yes | no | 0 | $4.6469 | $0.0210 | $4.65 | 1093.5 | 596.6 |
| full-none-r2 | done | 221 | yes | no | 0 | $4.5927 | $0.0208 | $4.59 | 456.7 | 614.2 |

The stages' own counters, reported, never compared:

| run | annotate | interpret |
|---|---|---|
| full-inc-transcribing-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"bad_owner": 1, "link_already_linked": 1, "link_malformed": 4, "second_text": 1, "text_not_target": 481}, "repairs": 488} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 191, "unclear": 3, "yes": 26}} |
| full-inc-transcribing-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"bad_owner": 1, "link_already_linked": 1, "link_malformed": 4, "link_unknown_box": 1, "text_not_target": 677}, "repairs": 684} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 191, "unclear": 5, "yes": 24}} |
| full-none-r1 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 193, "unclear": 2, "yes": 25}} |
| full-none-r2 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 196, "unclear": 1, "yes": 23}} |

## Cost

Means over a configuration's repeats, per stage. One figure per stage, at the synchronous list price; the batch columns are half of it. s / frame is the wall time of the stages the dollars cover (the pipeline through `index`); answering the questions is timed per question, below.

| configuration | stage | $ | $ / frame | $ / video | batch $ | batch $ / frame | batch $ / video | s / frame |
|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing | annotate | $12.2180 | $0.0553 | $12.22 | $6.1090 | $0.0277 | $6.11 | 3.3 |
| full-inc-transcribing | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| full-inc-transcribing | interpret | $4.6860 | $0.0212 | $4.69 | $2.3430 | $0.0106 | $2.35 | 1.1 |
| full-inc-transcribing | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 3.5 |
| full-inc-transcribing | summarize | $0.9429 | $0.0043 | $0.94 | $0.4714 | $0.0022 | $0.47 | 0.4 |
| full-inc-transcribing | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| full-inc-transcribing | all stages | $17.8469 | $0.0808 | $17.84 | $8.9235 | $0.0404 | $8.92 | 8.4 |
| full-none | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| full-none | interpret | $3.8042 | $0.0173 | $3.80 | $1.9021 | $0.0086 | $1.90 | 1.1 |
| full-none | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 2.0 |
| full-none | summarize | $0.8156 | $0.0037 | $0.81 | $0.4078 | $0.0019 | $0.41 | 0.3 |
| full-none | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| full-none | all stages | $4.6198 | $0.0209 | $4.62 | $2.3099 | $0.0104 | $2.31 | 3.5 |

The question set, outside $ / video, and the judge, apart (means per run):

| configuration | $ / question | s / question | question set $ | judge $ |
|---|---|---|---|---|
| full-inc-transcribing | $0.2626 | 22.6 | $7.0904 | $0.1686 |
| full-none | $0.2162 | 22.5 | $5.8358 | $0.1232 |

Spend over all 4 runs: pipeline $44.9334; question set $25.8524; judge $0.5836 (what the last pass of `scry eval judge` paid: a verdict served from the judge's cache costs nothing).

## Commands

**Primary, side by side, with no order between them:** found and exact, as k/n of the rated entries per repeat, then the mean. Every comparison with the command list is by frame number. `exact.any` is what compares bases that have different readers; it can only tie or rise with a second reader, so it is shown as what the second reading adds, at its price, beside `exact.ocr`, not as a contest.

| configuration | found | exact.ocr | exact.vlm | exact.any | $ / frame | $ / video |
|---|---|---|---|---|---|---|
| full-inc-transcribing | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | $0.0808 | $17.84 |
| full-none | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | —, — | 7/7, 7/7; mean 1 | $0.0209 | $4.62 |

**Secondary:** the first-appearance error and the submission error (mean absolute frames over the entries that have one, per repeat), submitted and false run (k/n per repeat).

| configuration | first appearance, ocr | first appearance, vlm | first appearance, any | submitted | submission error | false run | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing | 0.14 over 7, 0.14 over 7; mean 0.14 | 0.71 over 7, 1.57 over 7; mean 1.14 | 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7; mean 1 | 0 over 7, 0 over 7; mean 0 | 0/5, 0/5; mean 0 | $0.0808 | $17.84 |
| full-none | 0.14 over 7, 0.14 over 7; mean 0.14 | —, — | 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7; mean 1 | 0 over 7, 0 over 7; mean 0 | 0/5, 0/5; mean 0 | $0.0209 | $4.62 |

Per entry, in how many runs (of those that scored it). `summary only`: no localising entry covered the command and a summary entry of that level quoted it. `Y` and `y` are reported and not rated.

| configuration | # | text | found | exact.any | submitted | summary only | note | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing | 1 | `az account show` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing | 4 | `Y` | — | 2/2 | 2/2 | — | not rated | $0.0808 | $17.84 |
| full-inc-transcribing | 5 | `y` | — | 2/2 | 2/2 | — | not rated | $0.0808 | $17.84 |
| full-inc-transcribing | 6 | `kubectl config current-context` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing | 7 | `kubectl get nodes` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing | 8 | `kubectl get deployment` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing | 9 | `kubectl get pods` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-none | 1 | `az account show` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none | 4 | `Y` | — | 2/2 | 2/2 | — | not rated | $0.0209 | $4.62 |
| full-none | 5 | `y` | — | 2/2 | 2/2 | — | not rated | $0.0209 | $4.62 |
| full-none | 6 | `kubectl config current-context` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none | 7 | `kubectl get nodes` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none | 8 | `kubectl get deployment` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none | 9 | `kubectl get pods` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |

Texts that appeared on screen and were never run: in how many runs a `submitted: yes` claimed them (false run).

| configuration | row | text | false run | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing | N1 | `az login` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing | N4 | `kubectl config current-context` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing | N5 | `kubectl get svc` | 0/2 | $0.0808 | $17.84 |
| full-none | N1 | `az login` | 0/2 | $0.0209 | $4.62 |
| full-none | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/2 | $0.0209 | $4.62 |
| full-none | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/2 | $0.0209 | $4.62 |
| full-none | N4 | `kubectl config current-context` | 0/2 | $0.0209 | $4.62 |
| full-none | N5 | `kubectl get svc` | 0/2 | $0.0209 | $4.62 |

## Questions

**The positive questions (primary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing | 44 | 44 | 0 | 0 | 0 | 1, 1; mean 1 | $0.2626 | $0.0808 | $17.84 |
| full-none | 44 | 44 | 0 | 0 | 0 | 1, 1; mean 1 | $0.2162 | $0.0209 | $4.62 |

**The negative questions (secondary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing | 10 | 10 | 0 | 0 | 0 | 1, 1; mean 1 | $0.2626 | $0.0808 | $17.84 |
| full-none | 10 | 10 | 0 | 0 | 0 | 1, 1; mean 1 | $0.2162 | $0.0209 | $4.62 |

Per question, the label of each repeat (every answer, with the judge's verdict and quote for each rubric line, is in `scores.json`).

| configuration | question | polarity | labels per repeat | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing | Q1 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q2 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q3 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q4 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q5 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q6 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q7 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q8 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q9 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q10 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q11 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q12 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q13 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q14 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q15 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q16 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q17 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q18 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q19 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q20 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q21 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q22 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q23 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q24 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q25 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q26 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing | Q27 | negative | correct, correct | $0.0808 | $17.84 |
| full-none | Q1 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q2 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q3 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q4 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q5 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q6 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q7 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q8 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q9 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q10 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q11 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q12 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q13 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q14 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q15 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q16 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q17 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q18 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q19 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q20 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q21 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q22 | positive | correct, correct | $0.0209 | $4.62 |
| full-none | Q23 | negative | correct, correct | $0.0209 | $4.62 |
| full-none | Q24 | negative | correct, correct | $0.0209 | $4.62 |
| full-none | Q25 | negative | correct, correct | $0.0209 | $4.62 |
| full-none | Q26 | negative | correct, correct | $0.0209 | $4.62 |
| full-none | Q27 | negative | correct, correct | $0.0209 | $4.62 |

Stale answers (to a wording the question file no longer has), not judged: full-inc-transcribing 0, full-none 0. Unscored answers: full-inc-transcribing 0, full-none 0.

## Noise

Per configuration and metric: the value of each repeat (the mean of its units) and the largest paired difference between two repeats, which is the floor for one run against one run.

| configuration | metric | repeats | largest paired difference | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing | found | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing | exact.ocr | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing | exact.vlm | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing | exact.any | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing | submitted | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing | first_frame_error_abs.any | 0.1429, 0.1429 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing | submit_frame_error_abs | 0, 0 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing | false_run | 0, 0 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing | questions.positive | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing | questions.negative | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing | cost.per_question | 0.2534, 0.2718 | 0.018326 | $0.0808 | $17.84 |
| full-inc-transcribing | cost.per_frame | 0.0804, 0.0811 | 0.0007 | $0.0808 | $17.84 |
| full-inc-transcribing | seconds.per_frame | 8.4, 8.4 | 0 | $0.0808 | $17.84 |
| full-none | found | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none | exact.ocr | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none | exact.any | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none | submitted | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none | first_frame_error_abs.any | 0.1429, 0.1429 | 0 | $0.0209 | $4.62 |
| full-none | submit_frame_error_abs | 0, 0 | 0 | $0.0209 | $4.62 |
| full-none | false_run | 0, 0 | 0 | $0.0209 | $4.62 |
| full-none | questions.positive | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none | questions.negative | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none | cost.per_question | 0.2221, 0.2102 | 0.011844 | $0.0209 | $4.62 |
| full-none | cost.per_frame | 0.021, 0.0208 | 0.0002 | $0.0209 | $4.62 |
| full-none | seconds.per_frame | 4.9, 2.1 | 2.8 | $0.0209 | $4.62 |

## Comparisons

### full: A = full-inc-transcribing, B = full-none

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| found | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| exact.ocr | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| exact.vlm | higher | — | — | — | — | not comparable | absent in B | — | 0 | 7 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| exact.any | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| submitted | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| first_frame_error_abs.any | lower | 0.142857 | 0.142857 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| submit_frame_error_abs | lower | 0 | 0 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| false_run | lower | 0 | 0 | 0 | 0 | inside | — | — | 5 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| questions.positive | higher | 1 | 1 | 0 | 0 | inside | — | — | 22 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 5 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| cost.per_question | lower | 0.262607 | 0.216141 | -0.046467 | 0.012958 | outside | — | B | 27 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| cost.per_frame | lower | 0.08075 | 0.0209 | -0.05985 | 0.000495 | outside | — | B | 1 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| seconds.per_frame | lower | 8.4 | 3.5 | -4.9 | 1.9799 | outside | — | B | 1 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
