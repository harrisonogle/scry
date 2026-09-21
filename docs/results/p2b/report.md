# p2b evaluation report

Date: 2026-09-21. Matrix: `evals/p2b.toml`. Source run: `runs/p0`. Runs: 6.

Runs by status: done 6.
Commits the runs started on: `eac77d32fda1` (4 runs), `26216fea11e5` (2 runs).
Runs that started on a dirty tree: none.

$ / video = $ / frame × 221 frames, a linear projection from this span to the whole source video. Dollars are what a cold run pays at the synchronous list price, from the stages' manifest usage (an answer served from a call cache is priced as if paid); the batch price is half. The question set's dollars are per question and outside $ / video; the judge's dollars are apart from both.

An `outside` row means only that the difference is larger than the largest difference seen between identical cold runs of the two configurations, scaled for means of repeats. With three repeats a side that floor is a range of three values: by a normal approximation about one row in eight reads `outside` when nothing differs [estimated], and this report has dozens of rows. One `outside` row is weak evidence. Nothing here is a verdict, and no row decides anything by itself.

## Warnings

none

Notes (expected absences):

- span2-inc-grouponly-r1: no second reader: exact.vlm not scored
- span2-inc-grouponly-r2: no second reader: exact.vlm not scored
- span2-inc-grouponly-r3: no second reader: exact.vlm not scored

## Runs

| run | status | frames | cold | resumed | cache hits | $ | $ / frame | $ / video | pipeline s | questions s |
|---|---|---|---|---|---|---|---|---|---|---|
| span2-inc-transcribing-r1 | done | 33 | yes | no | 0 | $3.0060 | $0.0911 | $20.13 | 312.6 | 289.6 |
| span2-inc-transcribing-r2 | done | 33 | yes | no | 0 | $3.0255 | $0.0917 | $20.26 | 246.4 | 313.8 |
| span2-inc-transcribing-r3 | done | 33 | yes | no | 0 | $3.0255 | $0.0917 | $20.26 | 238.1 | 314.2 |
| span2-inc-grouponly-r1 | done | 33 | yes | no | 0 | $2.6229 | $0.0795 | $17.57 | 263.5 | 326.6 |
| span2-inc-grouponly-r2 | done | 33 | yes | no | 0 | $2.6243 | $0.0795 | $17.57 | 209.5 | 300.1 |
| span2-inc-grouponly-r3 | done | 33 | yes | no | 0 | $2.6158 | $0.0793 | $17.52 | 201.0 | 314.3 |

The stages' own counters, reported, never compared:

| run | annotate | interpret |
|---|---|---|
| span2-inc-transcribing-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"second_text": 1}, "repairs": 1} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 22, "unclear": 1, "yes": 9}} |
| span2-inc-transcribing-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 1}, "repairs": 1} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-inc-transcribing-r3 | {"errors": 0, "failed_targets": 0, "repair_counts": {"link_already_linked": 1, "link_malformed": 1}, "repairs": 2} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-inc-grouponly-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {}, "repairs": 0} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-inc-grouponly-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {}, "repairs": 0} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |
| span2-inc-grouponly-r3 | {"errors": 0, "failed_targets": 0, "repair_counts": {}, "repairs": 0} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 23, "unclear": 0, "yes": 9}} |

## Cost

Means over a configuration's repeats, per stage. One figure per stage, at the synchronous list price; the batch columns are half of it. s / frame is the wall time of the stages the dollars cover (the pipeline through `index`); answering the questions is timed per question, below.

| configuration | stage | $ | $ / frame | $ / video | batch $ | batch $ / frame | batch $ / video | s / frame |
|---|---|---|---|---|---|---|---|---|
| span2-inc-transcribing | annotate | $2.1343 | $0.0647 | $14.29 | $1.0672 | $0.0323 | $7.14 | 4.5 |
| span2-inc-transcribing | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| span2-inc-transcribing | interpret | $0.7027 | $0.0213 | $4.70 | $0.3513 | $0.0106 | $2.35 | 1.3 |
| span2-inc-transcribing | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 1.3 |
| span2-inc-transcribing | summarize | $0.1820 | $0.0055 | $1.22 | $0.0910 | $0.0027 | $0.61 | 0.9 |
| span2-inc-transcribing | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| span2-inc-transcribing | all stages | $3.0190 | $0.0915 | $20.22 | $1.5095 | $0.0457 | $10.11 | 8.1 |
| span2-inc-grouponly | annotate | $1.7479 | $0.0529 | $11.71 | $0.8740 | $0.0265 | $5.86 | 3.2 |
| span2-inc-grouponly | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| span2-inc-grouponly | interpret | $0.6872 | $0.0208 | $4.60 | $0.3436 | $0.0104 | $2.30 | 1.3 |
| span2-inc-grouponly | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 1.3 |
| span2-inc-grouponly | summarize | $0.1859 | $0.0057 | $1.24 | $0.0930 | $0.0029 | $0.62 | 0.9 |
| span2-inc-grouponly | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| span2-inc-grouponly | all stages | $2.6210 | $0.0794 | $17.55 | $1.3105 | $0.0397 | $8.78 | 6.8 |

The question set, outside $ / video, and the judge, apart (means per run):

| configuration | $ / question | s / question | question set $ | judge $ |
|---|---|---|---|---|
| span2-inc-transcribing | $0.1680 | 20.4 | $2.5199 | $0.1133 |
| span2-inc-grouponly | $0.1781 | 20.9 | $2.6715 | $0.1178 |

Spend over all 6 runs: pipeline $16.9200; question set $15.5744; judge $0.6932 (what the last pass of `scry eval judge` paid: a verdict served from the judge's cache costs nothing).

## Commands

**Primary, side by side, with no order between them:** found and exact, as k/n of the rated entries per repeat, then the mean. Every comparison with the command list is by frame number. `exact.any` is what compares bases that have different readers; it can only tie or rise with a second reader, so it is shown as what the second reading adds, at its price, beside `exact.ocr`, not as a contest.

| configuration | found | exact.ocr | exact.vlm | exact.any | $ / frame | $ / video |
|---|---|---|---|---|---|---|
| span2-inc-transcribing | 7/7, 7/7, 7/7; mean 1 | 7/7, 7/7, 7/7; mean 1 | 7/7, 6/7, 6/7; mean 0.9048 | 7/7, 7/7, 7/7; mean 1 | $0.0915 | $20.22 |
| span2-inc-grouponly | 7/7, 7/7, 7/7; mean 1 | 7/7, 7/7, 7/7; mean 1 | —, —, — | 7/7, 7/7, 7/7; mean 1 | $0.0794 | $17.55 |

**Secondary:** the first-appearance error and the submission error (mean absolute frames over the entries that have one, per repeat), submitted and false run (k/n per repeat).

| configuration | first appearance, ocr | first appearance, vlm | first appearance, any | submitted | submission error | false run | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|
| span2-inc-transcribing | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | 0.14 over 7, 0.17 over 6, 0.17 over 6; mean 0.16 | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7, 7/7; mean 1 | 0 over 7, 0 over 7, 0 over 7; mean 0 | 0/5, 0/5, 0/5; mean 0 | $0.0915 | $20.22 |
| span2-inc-grouponly | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | —, —, — | 0.14 over 7, 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7, 7/7; mean 1 | 0 over 7, 0 over 7, 0 over 7; mean 0 | 0/5, 0/5, 0/5; mean 0 | $0.0794 | $17.55 |

Per entry, in how many runs (of those that scored it). `summary only`: no localising entry covered the command and a summary entry of that level quoted it. `Y` and `y` are reported and not rated.

| configuration | # | text | found | exact.any | submitted | summary only | note | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| span2-inc-transcribing | 1 | `az account show` | 3/3 | 3/3 | 3/3 | — | — | $0.0915 | $20.22 |
| span2-inc-transcribing | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 3/3 | 3/3 | 3/3 | — | — | $0.0915 | $20.22 |
| span2-inc-transcribing | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 3/3 | 3/3 | 3/3 | — | — | $0.0915 | $20.22 |
| span2-inc-transcribing | 4 | `Y` | — | 3/3 | 3/3 | — | not rated | $0.0915 | $20.22 |
| span2-inc-transcribing | 5 | `y` | — | 3/3 | 3/3 | — | not rated | $0.0915 | $20.22 |
| span2-inc-transcribing | 6 | `kubectl config current-context` | 3/3 | 3/3 | 3/3 | — | — | $0.0915 | $20.22 |
| span2-inc-transcribing | 7 | `kubectl get nodes` | 3/3 | 3/3 | 3/3 | — | — | $0.0915 | $20.22 |
| span2-inc-transcribing | 8 | `kubectl get deployment` | 3/3 | 3/3 | 3/3 | — | — | $0.0915 | $20.22 |
| span2-inc-transcribing | 9 | `kubectl get pods` | 3/3 | 3/3 | 3/3 | — | — | $0.0915 | $20.22 |
| span2-inc-grouponly | 1 | `az account show` | 3/3 | 3/3 | 3/3 | — | — | $0.0794 | $17.55 |
| span2-inc-grouponly | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 3/3 | 3/3 | 3/3 | — | — | $0.0794 | $17.55 |
| span2-inc-grouponly | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 3/3 | 3/3 | 3/3 | — | — | $0.0794 | $17.55 |
| span2-inc-grouponly | 4 | `Y` | — | 3/3 | 3/3 | — | not rated | $0.0794 | $17.55 |
| span2-inc-grouponly | 5 | `y` | — | 3/3 | 3/3 | — | not rated | $0.0794 | $17.55 |
| span2-inc-grouponly | 6 | `kubectl config current-context` | 3/3 | 3/3 | 3/3 | — | — | $0.0794 | $17.55 |
| span2-inc-grouponly | 7 | `kubectl get nodes` | 3/3 | 3/3 | 3/3 | — | — | $0.0794 | $17.55 |
| span2-inc-grouponly | 8 | `kubectl get deployment` | 3/3 | 3/3 | 3/3 | — | — | $0.0794 | $17.55 |
| span2-inc-grouponly | 9 | `kubectl get pods` | 3/3 | 3/3 | 3/3 | — | — | $0.0794 | $17.55 |

Texts that appeared on screen and were never run: in how many runs a `submitted: yes` claimed them (false run).

| configuration | row | text | false run | $ / frame | $ / video |
|---|---|---|---|---|---|
| span2-inc-transcribing | N1 | `az login` | 0/3 | $0.0915 | $20.22 |
| span2-inc-transcribing | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/3 | $0.0915 | $20.22 |
| span2-inc-transcribing | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/3 | $0.0915 | $20.22 |
| span2-inc-transcribing | N4 | `kubectl config current-context` | 0/3 | $0.0915 | $20.22 |
| span2-inc-transcribing | N5 | `kubectl get svc` | 0/3 | $0.0915 | $20.22 |
| span2-inc-grouponly | N1 | `az login` | 0/3 | $0.0794 | $17.55 |
| span2-inc-grouponly | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/3 | $0.0794 | $17.55 |
| span2-inc-grouponly | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/3 | $0.0794 | $17.55 |
| span2-inc-grouponly | N4 | `kubectl config current-context` | 0/3 | $0.0794 | $17.55 |
| span2-inc-grouponly | N5 | `kubectl get svc` | 0/3 | $0.0794 | $17.55 |

## Questions

**The positive questions (primary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| span2-inc-transcribing | 33 | 33 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1680 | $0.0915 | $20.22 |
| span2-inc-grouponly | 33 | 33 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1781 | $0.0794 | $17.55 |

**The negative questions (secondary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| span2-inc-transcribing | 12 | 12 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1680 | $0.0915 | $20.22 |
| span2-inc-grouponly | 12 | 12 | 0 | 0 | 0 | 1, 1, 1; mean 1 | $0.1781 | $0.0794 | $17.55 |

Per question, the label of each repeat (every answer, with the judge's verdict and quote for each rubric line, is in `scores.json`).

| configuration | question | polarity | labels per repeat | $ / frame | $ / video |
|---|---|---|---|---|---|
| span2-inc-transcribing | Q1 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q2 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q3 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q4 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q5 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q6 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q7 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q8 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q9 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q10 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q11 | positive | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q12 | negative | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q13 | negative | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q14 | negative | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-transcribing | Q15 | negative | correct, correct, correct | $0.0915 | $20.22 |
| span2-inc-grouponly | Q1 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q2 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q3 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q4 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q5 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q6 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q7 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q8 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q9 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q10 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q11 | positive | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q12 | negative | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q13 | negative | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q14 | negative | correct, correct, correct | $0.0794 | $17.55 |
| span2-inc-grouponly | Q15 | negative | correct, correct, correct | $0.0794 | $17.55 |

Stale answers (to a wording the question file no longer has), not judged: span2-inc-transcribing 0, span2-inc-grouponly 0. Unscored answers: span2-inc-transcribing 0, span2-inc-grouponly 0.

## Noise

Per configuration and metric: the value of each repeat (the mean of its units) and the largest paired difference between two repeats, which is the floor for one run against one run.

| configuration | metric | repeats | largest paired difference | $ / frame | $ / video |
|---|---|---|---|---|---|
| span2-inc-transcribing | found | 1, 1, 1 | 0 | $0.0915 | $20.22 |
| span2-inc-transcribing | exact.ocr | 1, 1, 1 | 0 | $0.0915 | $20.22 |
| span2-inc-transcribing | exact.vlm | 1, 0.8571, 0.8571 | 0.142857 | $0.0915 | $20.22 |
| span2-inc-transcribing | exact.any | 1, 1, 1 | 0 | $0.0915 | $20.22 |
| span2-inc-transcribing | submitted | 1, 1, 1 | 0 | $0.0915 | $20.22 |
| span2-inc-transcribing | first_frame_error_abs.any | 0.1429, 0.1429, 0.1429 | 0 | $0.0915 | $20.22 |
| span2-inc-transcribing | submit_frame_error_abs | 0, 0, 0 | 0 | $0.0915 | $20.22 |
| span2-inc-transcribing | false_run | 0, 0, 0 | 0 | $0.0915 | $20.22 |
| span2-inc-transcribing | questions.positive | 1, 1, 1 | 0 | $0.0915 | $20.22 |
| span2-inc-transcribing | questions.negative | 1, 1, 1 | 0 | $0.0915 | $20.22 |
| span2-inc-transcribing | cost.per_question | 0.1601, 0.1737, 0.1702 | 0.013567 | $0.0915 | $20.22 |
| span2-inc-transcribing | cost.per_frame | 0.0911, 0.0917, 0.0917 | 0.0006 | $0.0915 | $20.22 |
| span2-inc-transcribing | seconds.per_frame | 9.5, 7.5, 7.2 | 2.3 | $0.0915 | $20.22 |
| span2-inc-grouponly | found | 1, 1, 1 | 0 | $0.0794 | $17.55 |
| span2-inc-grouponly | exact.ocr | 1, 1, 1 | 0 | $0.0794 | $17.55 |
| span2-inc-grouponly | exact.any | 1, 1, 1 | 0 | $0.0794 | $17.55 |
| span2-inc-grouponly | submitted | 1, 1, 1 | 0 | $0.0794 | $17.55 |
| span2-inc-grouponly | first_frame_error_abs.any | 0.1429, 0.1429, 0.1429 | 0 | $0.0794 | $17.55 |
| span2-inc-grouponly | submit_frame_error_abs | 0, 0, 0 | 0 | $0.0794 | $17.55 |
| span2-inc-grouponly | false_run | 0, 0, 0 | 0 | $0.0794 | $17.55 |
| span2-inc-grouponly | questions.positive | 1, 1, 1 | 0 | $0.0794 | $17.55 |
| span2-inc-grouponly | questions.negative | 1, 1, 1 | 0 | $0.0794 | $17.55 |
| span2-inc-grouponly | cost.per_question | 0.1765, 0.173, 0.1849 | 0.011893 | $0.0794 | $17.55 |
| span2-inc-grouponly | cost.per_frame | 0.0795, 0.0795, 0.0793 | 0.0002 | $0.0794 | $17.55 |
| span2-inc-grouponly | seconds.per_frame | 8, 6.3, 6.1 | 1.9 | $0.0794 | $17.55 |

## Comparisons

### span2: A = span2-inc-transcribing, B = span2-inc-grouponly

Differences are B − A, paired over the units every run of both sides has.

| metric | better | A | B | difference | floor | verdict | reason | favours | units | dropped | A $ / frame | A $ / video | B $ / frame | B $ / video |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| found | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| exact.ocr | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| exact.vlm | higher | — | — | — | — | not comparable | absent in B | — | 0 | 7 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| exact.any | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| submitted | higher | 1 | 1 | 0 | 0 | inside | — | — | 7 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| first_frame_error_abs.any | lower | 0.142857 | 0.142857 | 0 | 0 | inside | — | — | 7 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| submit_frame_error_abs | lower | 0 | 0 | 0 | 0 | inside | — | — | 7 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| false_run | lower | 0 | 0 | 0 | 0 | inside | — | — | 5 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| questions.positive | higher | 1 | 1 | 0 | 0 | inside | — | — | 11 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 4 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| cost.per_question | lower | 0.167996 | 0.178102 | 0.010107 | 0.007833 | outside | — | A | 15 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| cost.per_frame | lower | 0.0915 | 0.079433 | -0.012067 | 0.000346 | outside | — | B | 1 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
| seconds.per_frame | lower | 8.06667 | 6.8 | -1.26667 | 1.32791 | inside | — | — | 1 | 0 | $0.0915 | $20.22 | $0.0794 | $17.55 |
