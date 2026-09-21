# p9 evaluation report

Date: 2026-09-21. Matrix: `evals/p9.toml`. Source run: `runs/p0`. Runs: 4.

Runs by status: done 4.
Commits the runs started on: `537fcdb3f971` (4 runs).
Runs that started on a dirty tree: none.

$ / video = $ / frame × 221 frames, a linear projection from this span to the whole source video. Dollars are the price each stage's manifest records as paid (`cost_usd`): the synchronous list price, or the Batches price for a stage that ran in batch mode; an answer served from a call cache is priced as if paid. The question set's dollars are per question and outside $ / video; the judge's dollars are apart from both.

An `outside` row means only that the difference is larger than the largest difference seen between identical cold runs of the two configurations, scaled for means of repeats. With three repeats a side that floor is a range of three values: by a normal approximation about one row in eight reads `outside` when nothing differs [estimated], and this report has dozens of rows. One `outside` row is weak evidence. Nothing here is a verdict, and no row decides anything by itself.

## Warnings

- full-inc-transcribing-asksonnet-r1: run is not cold
- full-inc-transcribing-asksonnet-r2: run is not cold
- full-none-asksonnet-r1: run is not cold
- full-none-asksonnet-r2: run is not cold

Notes (expected absences):

- full-inc-transcribing-asksonnet-r1: pipeline copied from runs/eval/p4/full-inc-transcribing-r1, not built by this run
- full-inc-transcribing-asksonnet-r2: pipeline copied from runs/eval/p4/full-inc-transcribing-r2, not built by this run
- full-none-asksonnet-r1: pipeline copied from runs/eval/p4/full-none-r1, not built by this run
- full-none-asksonnet-r1: no annotations
- full-none-asksonnet-r1: no second reader: exact.vlm not scored
- full-none-asksonnet-r2: pipeline copied from runs/eval/p4/full-none-r2, not built by this run
- full-none-asksonnet-r2: no annotations
- full-none-asksonnet-r2: no second reader: exact.vlm not scored

## Runs

| run | status | frames | cold | resumed | cache hits | $ | $ / frame | $ / video | pipeline s | questions s |
|---|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-asksonnet-r1 | done | 221 | no | no | 0 | $17.7736 | $0.0804 | $17.77 | 0 | 265.3 |
| full-inc-transcribing-asksonnet-r2 | done | 221 | no | no | 0 | $17.9202 | $0.0811 | $17.92 | 0 | 251.7 |
| full-none-asksonnet-r1 | done | 221 | no | no | 0 | $4.6469 | $0.0210 | $4.65 | 0 | 252.1 |
| full-none-asksonnet-r2 | done | 221 | no | no | 0 | $4.5927 | $0.0208 | $4.59 | 0 | 253.0 |

The stages' own counters, reported, never compared:

| run | annotate | interpret |
|---|---|---|
| full-inc-transcribing-asksonnet-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"bad_owner": 1, "link_already_linked": 1, "link_malformed": 4, "second_text": 1, "text_not_target": 481}, "repairs": 488} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 191, "unclear": 3, "yes": 26}} |
| full-inc-transcribing-asksonnet-r2 | {"errors": 0, "failed_targets": 0, "repair_counts": {"bad_owner": 1, "link_already_linked": 1, "link_malformed": 4, "link_unknown_box": 1, "text_not_target": 677}, "repairs": 684} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 191, "unclear": 5, "yes": 24}} |
| full-none-asksonnet-r1 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 193, "unclear": 2, "yes": 25}} |
| full-none-asksonnet-r2 | — | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 196, "unclear": 1, "yes": 23}} |

## Cost

Means over a configuration's repeats, per stage. One figure per stage: the price its manifest records as paid. s / frame is the wall time of the stages the dollars cover (the pipeline through `index`); answering the questions is timed per question, below.

| configuration | stage | $ | $ / frame | $ / video | s / frame |
|---|---|---|---|---|---|
| full-inc-transcribing-asksonnet | annotate | $12.2180 | $0.0553 | $12.22 | 0.0 |
| full-inc-transcribing-asksonnet | interpret | $4.6860 | $0.0212 | $4.69 | 0.0 |
| full-inc-transcribing-asksonnet | summarize | $0.9429 | $0.0043 | $0.94 | 0.0 |
| full-inc-transcribing-asksonnet | all stages | $17.8469 | $0.0808 | $17.84 | 0.0 |
| full-none-asksonnet | interpret | $3.8042 | $0.0173 | $3.80 | 0.0 |
| full-none-asksonnet | summarize | $0.8156 | $0.0037 | $0.81 | 0.0 |
| full-none-asksonnet | all stages | $4.6198 | $0.0209 | $4.62 | 0.0 |

The question set, outside $ / video, and the judge, apart (means per run):

| configuration | $ / question | s / question | question set $ | judge $ |
|---|---|---|---|---|
| full-inc-transcribing-asksonnet | $0.0620 | 9.6 | $1.6754 | $0.2137 |
| full-none-asksonnet | $0.0534 | 9.4 | $1.4415 | $0.1966 |

Spend over all 4 runs: pipeline $44.9334; question set $6.2339; judge $0.8205 (what the last pass of `scry eval judge` paid: a verdict served from the judge's cache costs nothing).

## Commands

**Primary, side by side, with no order between them:** found and exact, as k/n of the rated entries per repeat, then the mean. Every comparison with the command list is by frame number. `exact.any` is what compares bases that have different readers; it can only tie or rise with a second reader, so it is shown as what the second reading adds, at its price, beside `exact.ocr`, not as a contest.

| configuration | found | exact.ocr | exact.vlm | exact.any | $ / frame | $ / video |
|---|---|---|---|---|---|---|
| full-inc-transcribing-asksonnet | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | $0.0808 | $17.84 |
| full-none-asksonnet | 7/7, 7/7; mean 1 | 7/7, 7/7; mean 1 | —, — | 7/7, 7/7; mean 1 | $0.0209 | $4.62 |

**Secondary:** the first-appearance error and the submission error (mean absolute frames over the entries that have one, per repeat), submitted and false run (k/n per repeat).

| configuration | first appearance, ocr | first appearance, vlm | first appearance, any | submitted | submission error | false run | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-asksonnet | 0.14 over 7, 0.14 over 7; mean 0.14 | 0.71 over 7, 1.57 over 7; mean 1.14 | 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7; mean 1 | 0 over 7, 0 over 7; mean 0 | 0/5, 0/5; mean 0 | $0.0808 | $17.84 |
| full-none-asksonnet | 0.14 over 7, 0.14 over 7; mean 0.14 | —, — | 0.14 over 7, 0.14 over 7; mean 0.14 | 7/7, 7/7; mean 1 | 0 over 7, 0 over 7; mean 0 | 0/5, 0/5; mean 0 | $0.0209 | $4.62 |

Per entry, in how many runs (of those that scored it). `summary only`: no localising entry covered the command and a summary entry of that level quoted it. `Y` and `y` are reported and not rated.

| configuration | # | text | found | exact.any | submitted | summary only | note | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-asksonnet | 1 | `az account show` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | 4 | `Y` | — | 2/2 | 2/2 | — | not rated | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | 5 | `y` | — | 2/2 | 2/2 | — | not rated | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | 6 | `kubectl config current-context` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | 7 | `kubectl get nodes` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | 8 | `kubectl get deployment` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | 9 | `kubectl get pods` | 2/2 | 2/2 | 2/2 | — | — | $0.0808 | $17.84 |
| full-none-asksonnet | 1 | `az account show` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-asksonnet | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-asksonnet | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-asksonnet | 4 | `Y` | — | 2/2 | 2/2 | — | not rated | $0.0209 | $4.62 |
| full-none-asksonnet | 5 | `y` | — | 2/2 | 2/2 | — | not rated | $0.0209 | $4.62 |
| full-none-asksonnet | 6 | `kubectl config current-context` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-asksonnet | 7 | `kubectl get nodes` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-asksonnet | 8 | `kubectl get deployment` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |
| full-none-asksonnet | 9 | `kubectl get pods` | 2/2 | 2/2 | 2/2 | — | — | $0.0209 | $4.62 |

Texts that appeared on screen and were never run: in how many runs a `submitted: yes` claimed them (false run).

| configuration | row | text | false run | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing-asksonnet | N1 | `az login` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | N4 | `kubectl config current-context` | 0/2 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | N5 | `kubectl get svc` | 0/2 | $0.0808 | $17.84 |
| full-none-asksonnet | N1 | `az login` | 0/2 | $0.0209 | $4.62 |
| full-none-asksonnet | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/2 | $0.0209 | $4.62 |
| full-none-asksonnet | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/2 | $0.0209 | $4.62 |
| full-none-asksonnet | N4 | `kubectl config current-context` | 0/2 | $0.0209 | $4.62 |
| full-none-asksonnet | N5 | `kubectl get svc` | 0/2 | $0.0209 | $4.62 |

## Questions

**The positive questions (primary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-asksonnet | 44 | 43 | 1 | 0 | 0 | 1, 0.9773; mean 0.9887 | $0.0620 | $0.0808 | $17.84 |
| full-none-asksonnet | 44 | 44 | 0 | 0 | 0 | 1, 1; mean 1 | $0.0534 | $0.0209 | $4.62 |

**The negative questions (secondary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-asksonnet | 10 | 10 | 0 | 0 | 0 | 1, 1; mean 1 | $0.0620 | $0.0808 | $17.84 |
| full-none-asksonnet | 10 | 10 | 0 | 0 | 0 | 1, 1; mean 1 | $0.0534 | $0.0209 | $4.62 |

Per question, the label of each repeat (every answer, with the judge's verdict and quote for each rubric line, is in `scores.json`).

| configuration | question | polarity | labels per repeat | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing-asksonnet | Q1 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q2 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q3 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q4 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q5 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q6 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q7 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q8 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q9 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q10 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q11 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q12 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q13 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q14 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q15 | positive | correct, partial | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q16 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q17 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q18 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q19 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q20 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q21 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q22 | positive | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q23 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q24 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q25 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q26 | negative | correct, correct | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | Q27 | negative | correct, correct | $0.0808 | $17.84 |
| full-none-asksonnet | Q1 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q2 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q3 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q4 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q5 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q6 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q7 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q8 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q9 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q10 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q11 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q12 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q13 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q14 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q15 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q16 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q17 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q18 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q19 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q20 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q21 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q22 | positive | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q23 | negative | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q24 | negative | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q25 | negative | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q26 | negative | correct, correct | $0.0209 | $4.62 |
| full-none-asksonnet | Q27 | negative | correct, correct | $0.0209 | $4.62 |

Stale answers (to a wording the question file no longer has), not judged: full-inc-transcribing-asksonnet 0, full-none-asksonnet 0. Unscored answers: full-inc-transcribing-asksonnet 0, full-none-asksonnet 0.

## Noise

Per configuration and metric: the value of each repeat (the mean of its units) and the largest paired difference between two repeats, which is the floor for one run against one run.

| configuration | metric | repeats | largest paired difference | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing-asksonnet | found | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | exact.ocr | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | exact.vlm | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | exact.any | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | submitted | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | first_frame_error_abs.any | 0.1429, 0.1429 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | submit_frame_error_abs | 0, 0 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | false_run | 0, 0 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | questions.positive | 1, 0.9773 | 0.022727 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | questions.negative | 1, 1 | 0 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | cost.per_question | 0.0594, 0.0647 | 0.005237 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | cost.per_frame | 0.0804, 0.0811 | 0.0007 | $0.0808 | $17.84 |
| full-inc-transcribing-asksonnet | seconds.per_frame | 0, 0 | 0 | $0.0808 | $17.84 |
| full-none-asksonnet | found | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-asksonnet | exact.ocr | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-asksonnet | exact.any | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-asksonnet | submitted | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-asksonnet | first_frame_error_abs.any | 0.1429, 0.1429 | 0 | $0.0209 | $4.62 |
| full-none-asksonnet | submit_frame_error_abs | 0, 0 | 0 | $0.0209 | $4.62 |
| full-none-asksonnet | false_run | 0, 0 | 0 | $0.0209 | $4.62 |
| full-none-asksonnet | questions.positive | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-asksonnet | questions.negative | 1, 1 | 0 | $0.0209 | $4.62 |
| full-none-asksonnet | cost.per_question | 0.0497, 0.0571 | 0.007396 | $0.0209 | $4.62 |
| full-none-asksonnet | cost.per_frame | 0.021, 0.0208 | 0.0002 | $0.0209 | $4.62 |
| full-none-asksonnet | seconds.per_frame | 0, 0 | 0 | $0.0209 | $4.62 |

## Comparisons

### full: A = full-inc-transcribing-asksonnet, B = full-none-asksonnet

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
| questions.positive | higher | 0.988636 | 1 | 0.011364 | 0.01607 | inside | — | — | 22 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| questions.negative | higher | 1 | 1 | 0 | 0 | inside | — | — | 5 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| cost.per_question | lower | 0.062052 | 0.053391 | -0.008661 | 0.00523 | outside | — | B | 27 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| cost.per_frame | lower | 0.08075 | 0.0209 | -0.05985 | 0.000495 | outside | — | B | 1 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
| seconds.per_frame | lower | 0 | 0 | 0 | 0 | inside | — | — | 1 | 0 | $0.0808 | $17.84 | $0.0209 | $4.62 |
