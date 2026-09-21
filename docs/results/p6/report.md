# p6 evaluation report

Date: 2026-09-21. Matrix: `evals/p6.toml`. Source run: `runs/p0`. Runs: 5.

Runs by status: done 5.
Commits the runs started on: `0275ac901d4e` (5 runs).
Runs that started on a dirty tree: none.

$ / video = $ / frame × 221 frames, a linear projection from this span to the whole source video. Dollars are the price each stage's manifest records as paid (`cost_usd`): the synchronous list price, or the Batches price for a stage that ran in batch mode; an answer served from a call cache is priced as if paid. The question set's dollars are per question and outside $ / video; the judge's dollars are apart from both.

An `outside` row means only that the difference is larger than the largest difference seen between identical cold runs of the two configurations, scaled for means of repeats. With three repeats a side that floor is a range of three values: by a normal approximation about one row in eight reads `outside` when nothing differs [estimated], and this report has dozens of rows. One `outside` row is weak evidence. Nothing here is a verdict, and no row decides anything by itself.

## Warnings

- full-inc-transcribing-indexonly-r1: run is not cold
- full-inc-transcribing-indexonly-r2: run is not cold
- full-none-indexonly-r1: run is not cold
- full-none-indexonly-r2: run is not cold
- full-inc-transcribing-batch-indexonly-r1: 221 cache hits in annotate
- full-inc-transcribing-batch-indexonly-r1: 220 cache hits in interpret
- full-inc-transcribing-batch-indexonly-r1: run is not cold

Notes (expected absences):

- full-inc-transcribing-indexonly-r1: pipeline copied from runs/eval/p4/full-inc-transcribing-r1, not built by this run
- full-inc-transcribing-indexonly-r2: pipeline copied from runs/eval/p4/full-inc-transcribing-r2, not built by this run
- full-none-indexonly-r1: pipeline copied from runs/eval/p4/full-none-r1, not built by this run
- full-none-indexonly-r1: no annotations
- full-none-indexonly-r1: no second reader: exact.vlm not scored
- full-none-indexonly-r2: pipeline copied from runs/eval/p4/full-none-r2, not built by this run
- full-none-indexonly-r2: no annotations
- full-none-indexonly-r2: no second reader: exact.vlm not scored
- full-inc-transcribing-batch-indexonly-r1: pipeline copied from runs/eval/p4b/full-inc-transcribing-batch-r1, not built by this run

## Runs

| run | status | frames | cold | resumed | cache hits | $ | $ / frame | $ / video | pipeline s | questions s |
|---|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-indexonly-r1 | done | 221 | no | no | 0 | $17.7736 | $0.0804 | $17.77 | 0 | 624.1 |
| full-inc-transcribing-indexonly-r2 | done | 221 | no | no | 0 | $17.9202 | $0.0811 | $17.92 | 0 | 631.2 |
| full-none-indexonly-r1 | done | 221 | no | no | 0 | $4.6469 | $0.0210 | $4.65 | 0 | 654.6 |
| full-none-indexonly-r2 | done | 221 | no | no | 0 | $4.5927 | $0.0208 | $4.59 | 0 | 661.3 |
| full-inc-transcribing-batch-indexonly-r1 | done | 221 | no | no | 441 | $12.1094 | $0.0548 | $12.11 | 0 | 604.0 |

The stages' own counters, reported, never compared:

| run | annotate | interpret |
|---|---|---|
| full-inc-transcribing-indexonly-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"bad_owner": 1, "link_already_linked": 1, "link_malformed": 4, "second_text": 1, "text_not_target": 481}, "repairs": 488} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 191, "unclear": 3, "yes": 26}} |
| full-inc-transcribing-indexonly-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"bad_owner": 1, "link_already_linked": 1, "link_malformed": 4, "link_unknown_box": 1, "text_not_target": 677}, "repairs": 684} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 191, "unclear": 5, "yes": 24}} |
| full-none-indexonly-r1 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 193, "unclear": 2, "yes": 25}} |
| full-none-indexonly-r2 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 196, "unclear": 1, "yes": 23}} |
| full-inc-transcribing-batch-indexonly-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"bad_owner": 1, "link_already_linked": 1, "link_malformed": 7, "link_unknown_box": 1, "text_not_target": 511}, "repairs": 521} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 191, "unclear": 4, "yes": 25}} |

## Cost

Means over a configuration's repeats, per stage. One figure per stage: the price its manifest records as paid. s / frame is the wall time of the stages the dollars cover (the pipeline through `index`); answering the questions is timed per question, below.

| configuration | stage | $ | $ / frame | $ / video | s / frame |
|---|---|---|---|---|---|
| full-inc-transcribing-indexonly | annotate | $12.2180 | $0.0553 | $12.22 | 0.0 |
| full-inc-transcribing-indexonly | interpret | $4.6860 | $0.0212 | $4.69 | 0.0 |
| full-inc-transcribing-indexonly | summarize | $0.9429 | $0.0043 | $0.94 | 0.0 |
| full-inc-transcribing-indexonly | all stages | $17.8469 | $0.0808 | $17.84 | 0.0 |
| full-none-indexonly | interpret | $3.8042 | $0.0173 | $3.80 | 0.0 |
| full-none-indexonly | summarize | $0.8156 | $0.0037 | $0.81 | 0.0 |
| full-none-indexonly | all stages | $4.6198 | $0.0209 | $4.62 | 0.0 |
| full-inc-transcribing-batch-indexonly | annotate | $7.8566 | $0.0356 | $7.86 | 0.0 |
| full-inc-transcribing-batch-indexonly | interpret | $3.3182 | $0.0150 | $3.32 | 0.0 |
| full-inc-transcribing-batch-indexonly | summarize | $0.9346 | $0.0042 | $0.93 | 0.0 |
| full-inc-transcribing-batch-indexonly | all stages | $12.1094 | $0.0548 | $12.11 | 0.0 |

The question set, outside $ / video, and the judge, apart (means per run):

| configuration | $ / question | s / question | question set $ | judge $ |
|---|---|---|---|---|
| full-inc-transcribing-indexonly | $0.2404 | 23.2 | $6.4902 | $0.2539 |
| full-none-indexonly | $0.2138 | 24.4 | $5.7730 | $0.2534 |
| full-inc-transcribing-batch-indexonly | $0.2551 | 22.4 | $6.8887 | $0.2713 |

Spend over all 5 runs: pipeline $57.0428; question set $31.4151; judge $1.2859 (what the last pass of `scry eval judge` paid: a verdict served from the judge's cache costs nothing).

## Commands

**Primary, side by side, with no order between them:** found and exact, as k/n of the rated entries per repeat, then the mean. Every comparison with the command list is by frame number. `exact.any` is what compares bases that have different readers; it can only tie or rise with a second reader, so it is shown as what the second reading adds, at its price, beside `exact.ocr`, not as a contest.

| configuration | found | exact.ocr | exact.vlm | exact.any | $ / frame | $ / video |
|---|---|---|---|---|---|---|
| full-inc-transcribing-indexonly | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | $0.0808 | $17.84 |
| full-none-indexonly | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | —, — | 7/7, 7/7; mean 1 | $0.0209 | $4.62 |
| full-inc-transcribing-batch-indexonly | 7/7; mean 1 | 7/7; mean 1 | 7/7; mean 1 | 7/7; mean 1 | $0.0548 | $12.11 |

**Secondary:** the first-appearance error and the submission error (mean absolute frames over the entries that have one, per repeat), submitted and false run (k/n per repeat).

| configuration | first appearance, ocr | first appearance, vlm | first appearance, any | submitted | submission error | false run | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-indexonly | 0.14 over 7, 0.14 over 7; mean 0.14 | 0.71 over 7, 1.57 over 7; mean 1.14 | 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7; mean 1 | 0 over 7, 0 over 7; mean 0 | 0/5, 0/5; mean 0 | $0.0808 | $17.84 |
| full-none-indexonly | 0.14 over 7, 0.14 over 7; mean 0.14 | —, — | 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7; mean 1 | 0 over 7, 0 over 7; mean 0 | 0/5, 0/5; mean 0 | $0.0209 | $4.62 |
| full-inc-transcribing-batch-indexonly | 0.14 over 7; mean 0.14 | 0.14 over 7; mean 0.14 | 0.14 over 7; mean 0.14 | 7/7; mean 1 | 0 over 7; mean 0 | 0/5; mean 0 | $0.0548 | $12.11 |

Per entry, in how many runs (of those that scored it). `summary only`: no localising entry covered the command and a summary entry of that level quoted it. `Y` and `y` are reported and not rated.

| configuration | # | text | found | exact.any | submitted | summary only | note | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-indexonly | 1 | `az account show` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | 4 | `Y` | — | 2/2 | 2/2 | — | not rated | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | 5 | `y` | — | 2/2 | 2/2 | — | not rated | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | 6 | `kubectl config current-context` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | 7 | `kubectl get nodes` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | 8 | `kubectl get deployment` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | 9 | `kubectl get pods` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-none-indexonly | 1 | `az account show` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-indexonly | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-indexonly | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-indexonly | 4 | `Y` | — | 2/2 | 2/2 | — | not rated | $0.0209 | $4.62 |
| full-none-indexonly | 5 | `y` | — | 2/2 | 2/2 | — | not rated | $0.0209 | $4.62 |
| full-none-indexonly | 6 | `kubectl config current-context` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-indexonly | 7 | `kubectl get nodes` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-indexonly | 8 | `kubectl get deployment` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-indexonly | 9 | `kubectl get pods` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-inc-transcribing-batch-indexonly | 1 | `az account show` | 1/1 | 1/1 | 1/1 | — | — | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 1/1 | 1/1 | 1/1 | — | — | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 1/1 | 1/1 | 1/1 | — | — | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | 4 | `Y` | — | 1/1 | 1/1 | — | not rated | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | 5 | `y` | — | 1/1 | 1/1 | — | not rated | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | 6 | `kubectl config current-context` | 1/1 | 1/1 | 1/1 | — | — | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | 7 | `kubectl get nodes` | 1/1 | 1/1 | 1/1 | — | — | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | 8 | `kubectl get deployment` | 1/1 | 1/1 | 1/1 | — | — | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | 9 | `kubectl get pods` | 1/1 | 1/1 | 1/1 | — | — | $0.0548 | $12.11 |

Texts that appeared on screen and were never run: in how many runs a `submitted: yes` claimed them (false run).

| configuration | row | text | false run | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing-indexonly | N1 | `az login` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | N4 | `kubectl config current-context` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | N5 | `kubectl get svc` | 0/2 | $0.0808 | $17.84 |
| full-none-indexonly | N1 | `az login` | 0/2 | $0.0209 | $4.62 |
| full-none-indexonly | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/2 | $0.0209 | $4.62 |
| full-none-indexonly | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/2 | $0.0209 | $4.62 |
| full-none-indexonly | N4 | `kubectl config current-context` | 0/2 | $0.0209 | $4.62 |
| full-none-indexonly | N5 | `kubectl get svc` | 0/2 | $0.0209 | $4.62 |
| full-inc-transcribing-batch-indexonly | N1 | `az login` | 0/1 | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/1 | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/1 | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | N4 | `kubectl config current-context` | 0/1 | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | N5 | `kubectl get svc` | 0/1 | $0.0548 | $12.11 |

## Questions

**The positive questions (primary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-indexonly | 44 | 44 | 0 | 0 | 0 | 1, 1; mean 1 | $0.2404 | $0.0808 | $17.84 |
| full-none-indexonly | 44 | 42 | 2 | 0 | 0 | 0.9773, 0.9773; mean 0.9773 | $0.2138 | $0.0209 | $4.62 |
| full-inc-transcribing-batch-indexonly | 22 | 22 | 0 | 0 | 0 | 1; mean 1 | $0.2551 | $0.0548 | $12.11 |

**The negative questions (secondary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-indexonly | 10 | 10 | 0 | 0 | 0 | 1, 1; mean 1 | $0.2404 | $0.0808 | $17.84 |
| full-none-indexonly | 10 | 10 | 0 | 0 | 0 | 1, 1; mean 1 | $0.2138 | $0.0209 | $4.62 |
| full-inc-transcribing-batch-indexonly | 5 | 5 | 0 | 0 | 0 | 1; mean 1 | $0.2551 | $0.0548 | $12.11 |

Per question, the label of each repeat (every answer, with the judge's verdict and quote for each rubric line, is in `scores.json`).

| configuration | question | polarity | labels per repeat | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing-indexonly | Q1 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q2 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q3 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q4 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q5 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q6 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q7 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q8 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q9 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q10 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q11 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q12 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q13 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q14 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q15 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q16 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q17 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q18 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q19 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q20 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q21 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q22 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q23 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q24 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q25 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q26 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | Q27 | negative | correct, correct | $0.0808 | $17.84 |
| full-none-indexonly | Q1 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q2 | positive | partial, partial | $0.0209 | $4.62 |
| full-none-indexonly | Q3 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q4 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q5 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q6 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q7 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q8 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q9 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q10 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q11 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q12 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q13 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q14 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q15 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q16 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q17 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q18 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q19 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q20 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q21 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q22 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q23 | negative | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q24 | negative | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q25 | negative | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q26 | negative | correct, correct | $0.0209 | $4.62 |
| full-none-indexonly | Q27 | negative | correct, correct | $0.0209 | $4.62 |
| full-inc-transcribing-batch-indexonly | Q1 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q2 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q3 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q4 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q5 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q6 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q7 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q8 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q9 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q10 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q11 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q12 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q13 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q14 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q15 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q16 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q17 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q18 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q19 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q20 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q21 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q22 | positive | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q23 | negative | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q24 | negative | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q25 | negative | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q26 | negative | correct | $0.0548 | $12.11 |
| full-inc-transcribing-batch-indexonly | Q27 | negative | correct | $0.0548 | $12.11 |

Stale answers (to a wording the question file no longer has), not judged: full-inc-transcribing-indexonly 0, full-none-indexonly 0, full-inc-transcribing-batch-indexonly 0. Unscored answers: full-inc-transcribing-indexonly 0, full-none-indexonly 0, full-inc-transcribing-batch-indexonly 0.

## Noise

Per configuration and metric: the value of each repeat (the mean of its units) and the largest paired difference between two repeats, which is the floor for one run against one run.

| configuration | metric | repeats | largest paired difference | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing-indexonly | found | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | exact.ocr | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | exact.vlm | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | exact.any | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | submitted | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | first_frame_error_abs.any | 0.1429, 0.1429 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | submit_frame_error_abs | 0, 0 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | false_run | 0, 0 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | questions.positive | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | questions.negative | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | cost.per_question | 0.2388, 0.2419 | 0.003119 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | cost.per_frame | 0.0804, 0.0811 | 0.0007 | $0.0808 | $17.84 |
| full-inc-transcribing-indexonly | seconds.per_frame | 0, 0 | 0 | $0.0808 | $17.84 |
| full-none-indexonly | found | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-indexonly | exact.ocr | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-indexonly | exact.any | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-indexonly | submitted | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-indexonly | first_frame_error_abs.any | 0.1429, 0.1429 | 0 | $0.0209 | $4.62 |
| full-none-indexonly | submit_frame_error_abs | 0, 0 | 0 | $0.0209 | $4.62 |
| full-none-indexonly | false_run | 0, 0 | 0 | $0.0209 | $4.62 |
| full-none-indexonly | questions.positive | 0.9773, 0.9773 | 0 | $0.0209 | $4.62 |
| full-none-indexonly | questions.negative | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-indexonly | cost.per_question | 0.215, 0.2127 | 0.002281 | $0.0209 | $4.62 |
| full-none-indexonly | cost.per_frame | 0.021, 0.0208 | 0.0002 | $0.0209 | $4.62 |
| full-none-indexonly | seconds.per_frame | 0, 0 | 0 | $0.0209 | $4.62 |

## Comparisons

### full: A = full-inc-transcribing-indexonly, B = full-none-indexonly

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
| questions.positive | higher | 1 | 0.977273 | -0.022727 | 0 | outside | — | A | 22 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 5 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| cost.per_question | lower | 0.240378 | 0.213815 | -0.026563 | 0.002205 | outside | — | B | 27 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| cost.per_frame | lower | 0.08075 | 0.0209 | -0.05985 | 0.000495 | outside | — | B | 1 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| seconds.per_frame | lower | 0 | 0 | 0 | 0 | inside | — | — | 1 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |

### full: A = full-inc-transcribing-indexonly, B = full-inc-transcribing-batch-indexonly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| found | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| exact.ocr | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| exact.vlm | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| exact.any | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| submitted | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| first_frame_error_abs.any | lower | 0.142857 | 0.142857 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| submit_frame_error_abs | lower | 0 | 0 | 0 | 0 | inside | — | — | 7 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| false_run | lower | 0 | 0 | 0 | 0 | inside | — | — | 5 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| questions.positive | higher | 1 | 1 | 0 | 0 | inside | — | — | 22 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 5 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| cost.per_question | lower | 0.240378 | 0.255137 | 0.014759 | 0.002701 | outside | — | A | 27 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| cost.per_frame | lower | 0.08075 | 0.0548 | -0.02595 | 0.000606 | outside | — | B | 1 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |
| seconds.per_frame | lower | 0 | 0 | 0 | 0 | inside | — | — | 1 | 0 | $0.0808 | $17.84 | $0.0548 | $12.11 |

### full: A = full-none-indexonly, B = full-inc-transcribing-batch-indexonly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| found | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| exact.ocr | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| exact.vlm | higher | — | — | — | — | not comparable | absent in A | — | 0 | 7 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| exact.any | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| submitted | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| first_frame_error_abs.any | lower | 0.142857 | 0.142857 | 0 | 0 | inside | — | — | 7 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| submit_frame_error_abs | lower | 0 | 0 | 0 | 0 | inside | — | — | 7 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| false_run | lower | 0 | 0 | 0 | 0 | inside | — | — | 5 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| questions.positive | higher | 0.977273 | 1 | 0.022727 | 0 | outside | — | B | 22 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 5 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| cost.per_question | lower | 0.213815 | 0.255137 | 0.041322 | 0.001975 | outside | — | A | 27 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| cost.per_frame | lower | 0.0209 | 0.0548 | 0.0339 | 0.000173 | outside | — | A | 1 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
| seconds.per_frame | lower | 0 | 0 | 0 | 0 | inside | — | — | 1 | 0 | $0.0209 | $4.62 | $0.0548 | $12.11 |
