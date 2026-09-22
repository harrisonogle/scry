# p11 evaluation report

Date: 2026-09-21. Matrix: `evals/p11.toml`. Source run: `runs/p0`. Runs: 2.

Runs by status: done 2.
Commits the runs started on: `ab3fd982cba9` (2 runs).
Runs that started on a dirty tree: none.

$ / video = $ / frame × 221 frames, a linear projection from this span to the whole source video. Dollars are the price each stage's manifest records as paid (`cost_usd`): the synchronous list price, or the Batches price for a stage that ran in batch mode; an answer served from a call cache is priced as if paid. The question set's dollars are per question and outside $ / video; the judge's dollars are apart from both.

An `outside` row means only that the difference is larger than the largest difference seen between identical cold runs of the two configurations, scaled for means of repeats. With three repeats a side that floor is a range of three values: by a normal approximation about one row in eight reads `outside` when nothing differs [estimated], and this report has dozens of rows. One `outside` row is weak evidence. Nothing here is a verdict, and no row decides anything by itself.

## Warnings

none

Notes (expected absences):

- full-ids100-grouponly-r1: no second reader: exact.vlm not scored
- full-ids067-grouponly-r1: no second reader: exact.vlm not scored

## Runs

| run | status | frames | cold | resumed | cache hits | $ | $ / frame | $ / video | pipeline s | questions s |
|---|---|---|---|---|---|---|---|---|---|---|
| full-ids100-grouponly-r1 | done | 221 | yes | no | 0 | $16.3043 | $0.0738 | $16.30 | 338.5 | 83.0 |
| full-ids067-grouponly-r1 | done | 221 | yes | no | 0 | $12.6158 | $0.0571 | $12.62 | 367.4 | 67.0 |

The stages' own counters, reported, never compared:

| run | annotate | interpret |
|---|---|---|
| full-ids100-grouponly-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 9, "link_malformed": 1}, "repairs": 10} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 193, "unclear": 2, "yes": 25}} |
| full-ids067-grouponly-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 5, "link_malformed": 2, "link_unknown_box": 3}, "repairs": 10} | {"errors": 0, "invalid_citations": 2, "submitted": {"no": 194, "unclear": 2, "yes": 24}} |

## Cost

Means over a configuration's repeats, per stage. One figure per stage: the price its manifest records as paid. s / frame is the wall time of the stages the dollars cover (the pipeline through `index`); answering the questions is timed per question, below.

| configuration | stage | $ | $ / frame | $ / video | s / frame |
|---|---|---|---|---|---|
| full-ids100-grouponly | annotate | $10.4610 | $0.0473 | $10.46 | 0.7 |
| full-ids100-grouponly | index | $0.0000 | $0.0000 | $0.00 | 0.0 |
| full-ids100-grouponly | interpret | $4.8903 | $0.0221 | $4.89 | 0.3 |
| full-ids100-grouponly | summarize | $0.9530 | $0.0043 | $0.95 | 0.2 |
| full-ids100-grouponly | track | $0.0000 | $0.0000 | $0.00 | 0.3 |
| full-ids100-grouponly | all stages | $16.3043 | $0.0738 | $16.30 | 1.5 |
| full-ids067-grouponly | annotate | $7.2050 | $0.0326 | $7.21 | 0.8 |
| full-ids067-grouponly | index | $0.0000 | $0.0000 | $0.00 | 0.0 |
| full-ids067-grouponly | interpret | $4.6016 | $0.0208 | $4.60 | 0.4 |
| full-ids067-grouponly | summarize | $0.8092 | $0.0037 | $0.81 | 0.2 |
| full-ids067-grouponly | track | $0.0000 | $0.0000 | $0.00 | 0.3 |
| full-ids067-grouponly | all stages | $12.6158 | $0.0571 | $12.62 | 1.7 |

The question set, outside $ / video, and the judge, apart (means per run):

| configuration | $ / question | s / question | question set $ | judge $ |
|---|---|---|---|---|
| full-ids100-grouponly | $0.2747 | 29.9 | $7.4166 | $0.2452 |
| full-ids067-grouponly | $0.2502 | 27.9 | $6.7549 | $0.2720 |

Spend over all 2 runs: pipeline $28.9201; question set $14.1715; judge $0.5172 (what the last pass of `scry eval judge` paid: a verdict served from the judge's cache costs nothing).

## Commands

**Primary, side by side, with no order between them:** found and exact, as k/n of the rated entries per repeat, then the mean. Every comparison with the command list is by frame number. `exact.any` is what compares bases that have different readers; it can only tie or rise with a second reader, so it is shown as what the second reading adds, at its price, beside `exact.ocr`, not as a contest.

| configuration | found | exact.ocr | exact.vlm | exact.any | $ / frame | $ / video |
|---|---|---|---|---|---|---|
| full-ids100-grouponly | 7/7; mean 1 | 7/7; mean 1 | — | 7/7; mean 1 | $0.0738 | $16.30 |
| full-ids067-grouponly | 7/7; mean 1 | 7/7; mean 1 | — | 7/7; mean 1 | $0.0571 | $12.62 |

**Secondary:** the first-appearance error and the submission error (mean absolute frames over the entries that have one, per repeat), submitted and false run (k/n per repeat).

| configuration | first appearance, ocr | first appearance, vlm | first appearance, any | submitted | submission error | false run | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|
| full-ids100-grouponly | 0.14 over 7; mean 0.14 | — | 0.14 over 7; mean 0.14 | 6/7; mean 0.8571 | 0 over 6; mean 0 | 0/5; mean 0 | $0.0738 | $16.30 |
| full-ids067-grouponly | 0.14 over 7; mean 0.14 | — | 0.14 over 7; mean 0.14 | 6/7; mean 0.8571 | 0 over 6; mean 0 | 0/5; mean 0 | $0.0571 | $12.62 |

Per entry, in how many runs (of those that scored it). `summary only`: no localising entry covered the command and a summary entry of that level quoted it. `Y` and `y` are reported and not rated.

| configuration | # | text | found | exact.any | submitted | summary only | note | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-ids100-grouponly | 1 | `az account show` | 1/1 | 1/1 | 1/1 | — | — | $0.0738 | $16.30 |
| full-ids100-grouponly | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 1/1 | 1/1 | 1/1 | — | — | $0.0738 | $16.30 |
| full-ids100-grouponly | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 1/1 | 1/1 | 0/1 | — | — | $0.0738 | $16.30 |
| full-ids100-grouponly | 4 | `Y` | — | 1/1 | 1/1 | — | not rated | $0.0738 | $16.30 |
| full-ids100-grouponly | 5 | `y` | — | 1/1 | 1/1 | — | not rated | $0.0738 | $16.30 |
| full-ids100-grouponly | 6 | `kubectl config current-context` | 1/1 | 1/1 | 1/1 | — | — | $0.0738 | $16.30 |
| full-ids100-grouponly | 7 | `kubectl get nodes` | 1/1 | 1/1 | 1/1 | — | — | $0.0738 | $16.30 |
| full-ids100-grouponly | 8 | `kubectl get deployment` | 1/1 | 1/1 | 1/1 | — | — | $0.0738 | $16.30 |
| full-ids100-grouponly | 9 | `kubectl get pods` | 1/1 | 1/1 | 1/1 | — | — | $0.0738 | $16.30 |
| full-ids067-grouponly | 1 | `az account show` | 1/1 | 1/1 | 1/1 | — | — | $0.0571 | $12.62 |
| full-ids067-grouponly | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 1/1 | 1/1 | 1/1 | — | — | $0.0571 | $12.62 |
| full-ids067-grouponly | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 1/1 | 1/1 | 0/1 | — | — | $0.0571 | $12.62 |
| full-ids067-grouponly | 4 | `Y` | — | 1/1 | 1/1 | — | not rated | $0.0571 | $12.62 |
| full-ids067-grouponly | 5 | `y` | — | 1/1 | 1/1 | — | not rated | $0.0571 | $12.62 |
| full-ids067-grouponly | 6 | `kubectl config current-context` | 1/1 | 1/1 | 1/1 | — | — | $0.0571 | $12.62 |
| full-ids067-grouponly | 7 | `kubectl get nodes` | 1/1 | 1/1 | 1/1 | — | — | $0.0571 | $12.62 |
| full-ids067-grouponly | 8 | `kubectl get deployment` | 1/1 | 1/1 | 1/1 | — | — | $0.0571 | $12.62 |
| full-ids067-grouponly | 9 | `kubectl get pods` | 1/1 | 1/1 | 1/1 | — | — | $0.0571 | $12.62 |

Texts that appeared on screen and were never run: in how many runs a `submitted: yes` claimed them (false run).

| configuration | row | text | false run | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-ids100-grouponly | N1 | `az login` | 0/1 | $0.0738 | $16.30 |
| full-ids100-grouponly | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/1 | $0.0738 | $16.30 |
| full-ids100-grouponly | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/1 | $0.0738 | $16.30 |
| full-ids100-grouponly | N4 | `kubectl config current-context` | 0/1 | $0.0738 | $16.30 |
| full-ids100-grouponly | N5 | `kubectl get svc` | 0/1 | $0.0738 | $16.30 |
| full-ids067-grouponly | N1 | `az login` | 0/1 | $0.0571 | $12.62 |
| full-ids067-grouponly | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/1 | $0.0571 | $12.62 |
| full-ids067-grouponly | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/1 | $0.0571 | $12.62 |
| full-ids067-grouponly | N4 | `kubectl config current-context` | 0/1 | $0.0571 | $12.62 |
| full-ids067-grouponly | N5 | `kubectl get svc` | 0/1 | $0.0571 | $12.62 |

## Questions

**The positive questions (primary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-ids100-grouponly | 22 | 22 | 0 | 0 | 0 | 1; mean 1 | $0.2747 | $0.0738 | $16.30 |
| full-ids067-grouponly | 22 | 22 | 0 | 0 | 0 | 1; mean 1 | $0.2502 | $0.0571 | $12.62 |

**The negative questions (secondary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-ids100-grouponly | 5 | 5 | 0 | 0 | 0 | 1; mean 1 | $0.2747 | $0.0738 | $16.30 |
| full-ids067-grouponly | 5 | 5 | 0 | 0 | 0 | 1; mean 1 | $0.2502 | $0.0571 | $12.62 |

Per question, the label of each repeat (every answer, with the judge's verdict and quote for each rubric line, is in `scores.json`).

| configuration | question | polarity | labels per repeat | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-ids100-grouponly | Q1 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q2 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q3 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q4 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q5 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q6 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q7 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q8 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q9 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q10 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q11 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q12 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q13 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q14 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q15 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q16 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q17 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q18 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q19 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q20 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q21 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q22 | positive | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q23 | negative | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q24 | negative | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q25 | negative | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q26 | negative | correct | $0.0738 | $16.30 |
| full-ids100-grouponly | Q27 | negative | correct | $0.0738 | $16.30 |
| full-ids067-grouponly | Q1 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q2 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q3 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q4 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q5 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q6 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q7 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q8 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q9 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q10 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q11 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q12 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q13 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q14 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q15 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q16 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q17 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q18 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q19 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q20 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q21 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q22 | positive | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q23 | negative | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q24 | negative | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q25 | negative | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q26 | negative | correct | $0.0571 | $12.62 |
| full-ids067-grouponly | Q27 | negative | correct | $0.0571 | $12.62 |

Stale answers (to a wording the question file no longer has), not judged: full-ids100-grouponly 0, full-ids067-grouponly 0. Unscored answers: full-ids100-grouponly 0, full-ids067-grouponly 0.

## Noise

Per configuration and metric: the value of each repeat (the mean of its units) and the largest paired difference between two repeats, which is the floor for one run against one run.

No configuration has two repeats: no floor was measured.

## Comparisons

### full: A = full-ids100-grouponly, B = full-ids067-grouponly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| found | higher | 1 | 1 | 0 | — | unknown | — | — | 7 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| exact.ocr | higher | 1 | 1 | 0 | — | unknown | — | — | 7 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| exact.any | higher | 1 | 1 | 0 | — | unknown | — | — | 7 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| submitted | higher | 0.857143 | 0.857143 | 0 | — | unknown | — | — | 7 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| first_frame_error_abs.any | lower | 0.142857 | 0.142857 | 0 | — | unknown | — | — | 7 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| submit_frame_error_abs | lower | 0 | 0 | 0 | — | unknown | — | — | 6 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| false_run | lower | 0 | 0 | 0 | — | unknown | — | — | 5 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| questions.positive | higher | 1 | 1 | 0 | — | unknown | — | — | 22 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| questions.negative | higher | 1 | 1 | 0 | — | unknown | — | — | 5 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| cost.per_question | lower | 0.274689 | 0.250181 | -0.024507 | — | unknown | — | — | 27 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| cost.per_frame | lower | 0.0738 | 0.0571 | -0.0167 | — | unknown | — | — | 1 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
| seconds.per_frame | lower | 1.5 | 1.7 | 0.2 | — | unknown | — | — | 1 | 0 | $0.0738 | $16.30 | $0.0571 | $12.62 |
