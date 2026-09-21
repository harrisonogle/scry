# p8 evaluation report

Date: 2026-09-21. Matrix: `evals/p8.toml`. Source run: `runs/p0`. Runs: 4.

Runs by status: done 4.
Commits the runs started on: `0275ac901d4e` (4 runs).
Runs that started on a dirty tree: none.

$ / video = $ / frame × 221 frames, a linear projection from this span to the whole source video. Dollars are the price each stage's manifest records as paid (`cost_usd`): the synchronous list price, or the Batches price for a stage that ran in batch mode; an answer served from a call cache is priced as if paid. The question set's dollars are per question and outside $ / video; the judge's dollars are apart from both.

An `outside` row means only that the difference is larger than the largest difference seen between identical cold runs of the two configurations, scaled for means of repeats. With three repeats a side that floor is a range of three values: by a normal approximation about one row in eight reads `outside` when nothing differs [estimated], and this report has dozens of rows. One `outside` row is weak evidence. Nothing here is a verdict, and no row decides anything by itself.

## Warnings

none

Notes (expected absences):

- full-none-sonnet5-r1: no annotations
- full-none-sonnet5-r1: no second reader: exact.vlm not scored
- full-none-sonnet5-r2: no annotations
- full-none-sonnet5-r2: no second reader: exact.vlm not scored

## Runs

| run | status | frames | cold | resumed | cache hits | $ | $ / frame | $ / video | pipeline s | questions s |
|---|---|---|---|---|---|---|---|---|---|---|
| full-none-sonnet5-r1 | done | 221 | yes | no | 0 | $1.8674 | $0.0084 | $1.87 | 940.2 | 266.2 |
| full-none-sonnet5-r2 | done | 221 | yes | no | 0 | $1.9995 | $0.0090 | $2.00 | 982.5 | 288.3 |
| full-inc-transcribing-sonnet5-r1 | done | 221 | yes | no | 0 | $7.3866 | $0.0334 | $7.39 | 1655.6 | 274.2 |
| full-inc-transcribing-sonnet5-r2 | done | 221 | yes | no | 0 | $7.3797 | $0.0334 | $7.38 | 1621.2 | 288.3 |

The stages' own counters, reported, never compared:

| run | annotate | interpret |
|---|---|---|
| full-none-sonnet5-r1 | — | {"errors": 0, "invalid_citations": 34, "submitted": {"no": 124, "unclear": 41, "yes": 55}} |
| full-none-sonnet5-r2 | — | {"errors": 0, "invalid_citations": 26, "submitted": {"no": 122, "unclear": 43, "yes": 55}} |
| full-inc-transcribing-sonnet5-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"bad_owner": 1, "link_already_linked": 9, "link_malformed": 11, "link_unknown_box": 2}, "repairs": 23} | {"errors": 0, "invalid_citations": 25, "submitted": {"no": 124, "unclear": 42, "yes": 54}} |
| full-inc-transcribing-sonnet5-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"bad_owner": 1, "link_already_linked": 8, "link_malformed": 8, "link_unknown_box": 1}, "repairs": 18} | {"errors": 0, "invalid_citations": 23, "submitted": {"no": 128, "unclear": 33, "yes": 59}} |

## Cost

Means over a configuration's repeats, per stage. One figure per stage: the price its manifest records as paid. s / frame is the wall time of the stages the dollars cover (the pipeline through `index`); answering the questions is timed per question, below.

| configuration | stage | $ | $ / frame | $ / video | s / frame |
|---|---|---|---|---|---|
| full-none-sonnet5 | index | $0.0000 | $0.0000 | $0.00 | 0.0 |
| full-none-sonnet5 | interpret | $1.4797 | $0.0067 | $1.48 | 0.8 |
| full-none-sonnet5 | read | $0.0000 | $0.0000 | $0.00 | 2.9 |
| full-none-sonnet5 | summarize | $0.4537 | $0.0020 | $0.46 | 0.5 |
| full-none-sonnet5 | track | $0.0000 | $0.0000 | $0.00 | 0.1 |
| full-none-sonnet5 | all stages | $1.9335 | $0.0087 | $1.94 | 4.3 |
| full-inc-transcribing-sonnet5 | annotate | $5.2127 | $0.0236 | $5.21 | 3.2 |
| full-inc-transcribing-sonnet5 | index | $0.0000 | $0.0000 | $0.00 | 0.0 |
| full-inc-transcribing-sonnet5 | interpret | $1.7980 | $0.0082 | $1.80 | 0.8 |
| full-inc-transcribing-sonnet5 | read | $0.0000 | $0.0000 | $0.00 | 2.9 |
| full-inc-transcribing-sonnet5 | summarize | $0.3724 | $0.0017 | $0.37 | 0.3 |
| full-inc-transcribing-sonnet5 | track | $0.0000 | $0.0000 | $0.00 | 0.1 |
| full-inc-transcribing-sonnet5 | all stages | $7.3831 | $0.0334 | $7.38 | 7.4 |

The question set, outside $ / video, and the judge, apart (means per run):

| configuration | $ / question | s / question | question set $ | judge $ |
|---|---|---|---|---|
| full-none-sonnet5 | $0.0530 | 10.3 | $1.4299 | $0.1972 |
| full-inc-transcribing-sonnet5 | $0.0662 | 10.4 | $1.7873 | $0.2189 |

Spend over all 4 runs: pipeline $18.6332; question set $6.4344; judge $0.8323 (what the last pass of `scry eval judge` paid: a verdict served from the judge's cache costs nothing).

## Commands

**Primary, side by side, with no order between them:** found and exact, as k/n of the rated entries per repeat, then the mean. Every comparison with the command list is by frame number. `exact.any` is what compares bases that have different readers; it can only tie or rise with a second reader, so it is shown as what the second reading adds, at its price, beside `exact.ocr`, not as a contest.

| configuration | found | exact.ocr | exact.vlm | exact.any | $ / frame | $ / video |
|---|---|---|---|---|---|---|
| full-none-sonnet5 | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | —, — | 7/7, 7/7; mean 1 | $0.0087 | $1.94 |
| full-inc-transcribing-sonnet5 | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | $0.0334 | $7.38 |

**Secondary:** the first-appearance error and the submission error (mean absolute frames over the entries that have one, per repeat), submitted and false run (k/n per repeat).

| configuration | first appearance, ocr | first appearance, vlm | first appearance, any | submitted | submission error | false run | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|
| full-none-sonnet5 | 0.14 over 7, 0.14 over 7; mean 0.14 | —, — | 0.14 over 7, 0.14 over 7; mean 0.14 | 5/7, 5/7; mean 0.7143 | 0 over 5, 0 over 5; mean 0 | 0/5, 0/5; mean 0 | $0.0087 | $1.94 |
| full-inc-transcribing-sonnet5 | 0.14 over 7, 0.14 over 7; mean 0.14 | 1.57 over 7, 0.14 over 7; mean 0.85 | 0.14 over 7, 0.14 over 7; mean 0.14 | 5/7, 6/7; mean 0.7857 | 0 over 5, 0 over 6; mean 0 | 1/5, 0/5; mean 0.1 | $0.0334 | $7.38 |

Per entry, in how many runs (of those that scored it). `summary only`: no localising entry covered the command and a summary entry of that level quoted it. `Y` and `y` are reported and not rated.

| configuration | # | text | found | exact.any | submitted | summary only | note | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-none-sonnet5 | 1 | `az account show` | 2/2 | 2/2 | 2/2 | — | — | $0.0087 | $1.94 |
| full-none-sonnet5 | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 2/2 | 2/2 | 0/2 | — | — | $0.0087 | $1.94 |
| full-none-sonnet5 | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 2/2 | 2/2 | 0/2 | — | — | $0.0087 | $1.94 |
| full-none-sonnet5 | 4 | `Y` | — | 2/2 | 2/2 | — | not rated | $0.0087 | $1.94 |
| full-none-sonnet5 | 5 | `y` | — | 2/2 | 2/2 | — | not rated | $0.0087 | $1.94 |
| full-none-sonnet5 | 6 | `kubectl config current-context` | 2/2 | 2/2 | 2/2 | — | — | $0.0087 | $1.94 |
| full-none-sonnet5 | 7 | `kubectl get nodes` | 2/2 | 2/2 | 2/2 | — | — | $0.0087 | $1.94 |
| full-none-sonnet5 | 8 | `kubectl get deployment` | 2/2 | 2/2 | 2/2 | — | — | $0.0087 | $1.94 |
| full-none-sonnet5 | 9 | `kubectl get pods` | 2/2 | 2/2 | 2/2 | — | — | $0.0087 | $1.94 |
| full-inc-transcribing-sonnet5 | 1 | `az account show` | 2/2 | 2/2 | 2/2 | — | — | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 2/2 | 2/2 | 1/2 | — | — | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 2/2 | 2/2 | 0/2 | — | — | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | 4 | `Y` | — | 2/2 | 2/2 | — | not rated | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | 5 | `y` | — | 2/2 | 2/2 | — | not rated | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | 6 | `kubectl config current-context` | 2/2 | 2/2 | 2/2 | — | — | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | 7 | `kubectl get nodes` | 2/2 | 2/2 | 2/2 | — | — | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | 8 | `kubectl get deployment` | 2/2 | 2/2 | 2/2 | — | — | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | 9 | `kubectl get pods` | 2/2 | 2/2 | 2/2 | — | — | $0.0334 | $7.38 |

Texts that appeared on screen and were never run: in how many runs a `submitted: yes` claimed them (false run).

| configuration | row | text | false run | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-none-sonnet5 | N1 | `az login` | 0/2 | $0.0087 | $1.94 |
| full-none-sonnet5 | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/2 | $0.0087 | $1.94 |
| full-none-sonnet5 | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/2 | $0.0087 | $1.94 |
| full-none-sonnet5 | N4 | `kubectl config current-context` | 0/2 | $0.0087 | $1.94 |
| full-none-sonnet5 | N5 | `kubectl get svc` | 0/2 | $0.0087 | $1.94 |
| full-inc-transcribing-sonnet5 | N1 | `az login` | 0/2 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/2 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/2 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | N4 | `kubectl config current-context` | 0/2 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | N5 | `kubectl get svc` | 1/2 | $0.0334 | $7.38 |

## Questions

**The positive questions (primary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-none-sonnet5 | 44 | 44 | 0 | 0 | 0 | 1, 1; mean 1 | $0.0530 | $0.0087 | $1.94 |
| full-inc-transcribing-sonnet5 | 44 | 43 | 1 | 0 | 0 | 0.9773, 1; mean 0.9887 | $0.0662 | $0.0334 | $7.38 |

**The negative questions (secondary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-none-sonnet5 | 10 | 10 | 0 | 0 | 0 | 1, 1; mean 1 | $0.0530 | $0.0087 | $1.94 |
| full-inc-transcribing-sonnet5 | 10 | 10 | 0 | 0 | 0 | 1, 1; mean 1 | $0.0662 | $0.0334 | $7.38 |

Per question, the label of each repeat (every answer, with the judge's verdict and quote for each rubric line, is in `scores.json`).

| configuration | question | polarity | labels per repeat | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-none-sonnet5 | Q1 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q2 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q3 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q4 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q5 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q6 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q7 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q8 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q9 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q10 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q11 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q12 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q13 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q14 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q15 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q16 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q17 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q18 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q19 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q20 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q21 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q22 | positive | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q23 | negative | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q24 | negative | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q25 | negative | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q26 | negative | correct, correct | $0.0087 | $1.94 |
| full-none-sonnet5 | Q27 | negative | correct, correct | $0.0087 | $1.94 |
| full-inc-transcribing-sonnet5 | Q1 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q2 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q3 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q4 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q5 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q6 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q7 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q8 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q9 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q10 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q11 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q12 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q13 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q14 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q15 | positive | partial, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q16 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q17 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q18 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q19 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q20 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q21 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q22 | positive | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q23 | negative | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q24 | negative | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q25 | negative | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q26 | negative | correct, correct | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | Q27 | negative | correct, correct | $0.0334 | $7.38 |

Stale answers (to a wording the question file no longer has), not judged: full-none-sonnet5 0, full-inc-transcribing-sonnet5 0. Unscored answers: full-none-sonnet5 0, full-inc-transcribing-sonnet5 0.

## Noise

Per configuration and metric: the value of each repeat (the mean of its units) and the largest paired difference between two repeats, which is the floor for one run against one run.

| configuration | metric | repeats | largest paired difference | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-none-sonnet5 | found | 1, 1 | 0 | $0.0087 | $1.94 |
| full-none-sonnet5 | exact.ocr | 1, 1 | 0 | $0.0087 | $1.94 |
| full-none-sonnet5 | exact.any | 1, 1 | 0 | $0.0087 | $1.94 |
| full-none-sonnet5 | submitted | 0.7143, 0.7143 | 0 | $0.0087 | $1.94 |
| full-none-sonnet5 | first_frame_error_abs.any | 0.1429, 0.1429 | 0 | $0.0087 | $1.94 |
| full-none-sonnet5 | submit_frame_error_abs | 0, 0 | 0 | $0.0087 | $1.94 |
| full-none-sonnet5 | false_run | 0, 0 | 0 | $0.0087 | $1.94 |
| full-none-sonnet5 | questions.positive | 1, 1 | 0 | $0.0087 | $1.94 |
| full-none-sonnet5 | questions.negative | 1, 1 | 0 | $0.0087 | $1.94 |
| full-none-sonnet5 | cost.per_question | 0.0538, 0.0522 | 0.001589 | $0.0087 | $1.94 |
| full-none-sonnet5 | cost.per_frame | 0.0084, 0.009 | 0.0006 | $0.0087 | $1.94 |
| full-none-sonnet5 | seconds.per_frame | 4.3, 4.4 | 0.1 | $0.0087 | $1.94 |
| full-inc-transcribing-sonnet5 | found | 1, 1 | 0 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | exact.ocr | 1, 1 | 0 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | exact.vlm | 1, 1 | 0 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | exact.any | 1, 1 | 0 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | submitted | 0.7143, 0.8571 | 0.142857 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | first_frame_error_abs.any | 0.1429, 0.1429 | 0 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | submit_frame_error_abs | 0, 0 | 0 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | false_run | 0.2, 0 | 0.2 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | questions.positive | 0.9773, 1 | 0.022727 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | questions.negative | 1, 1 | 0 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | cost.per_question | 0.0657, 0.0667 | 0.001048 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | cost.per_frame | 0.0334, 0.0334 | 0 | $0.0334 | $7.38 |
| full-inc-transcribing-sonnet5 | seconds.per_frame | 7.5, 7.3 | 0.2 | $0.0334 | $7.38 |

## Comparisons

### full: A = full-none-sonnet5, B = full-inc-transcribing-sonnet5

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| found | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| exact.ocr | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| exact.vlm | higher | — | — | — | — | not comparable | absent in A | — | 0 | 7 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| exact.any | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| submitted | higher | 0.714286 | 0.785714 | 0.071429 | 0.101015 | inside | — | — | 7 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| first_frame_error_abs.any | lower | 0.142857 | 0.142857 | 0 | 0 | inside | — | — | 7 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| submit_frame_error_abs | lower | 0 | 0 | 0 | 0 | inside | — | — | 5 | 1 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| false_run | lower | 0 | 0.1 | 0.1 | 0.141421 | inside | — | — | 5 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| questions.positive | higher | 1 | 0.988636 | -0.011364 | 0.01607 | inside | — | — | 22 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 5 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| cost.per_question | lower | 0.052957 | 0.066198 | 0.013241 | 0.001124 | outside | — | A | 27 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| cost.per_frame | lower | 0.0087 | 0.0334 | 0.0247 | 0.000424 | outside | — | A | 1 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
| seconds.per_frame | lower | 4.35 | 7.4 | 3.05 | 0.141421 | outside | — | A | 1 | 0 | $0.0087 | $1.94 | $0.0334 | $7.38 |
