# p4b evaluation report

Date: 2026-09-21. Matrix: `evals/p4b.toml`. Source run: `runs/p0`. Runs: 1.

Runs by status: done 1.
Commits the runs started on: `6ac8d6300add` (1 runs).
Runs that started on a dirty tree: none.

$ / video = $ / frame × 221 frames, a linear projection from this span to the whole source video. Dollars are what a cold run pays at the synchronous list price, from the stages' manifest usage (an answer served from a call cache is priced as if paid); the batch price is half. The question set's dollars are per question and outside $ / video; the judge's dollars are apart from both.

An `outside` row means only that the difference is larger than the largest difference seen between identical cold runs of the two configurations, scaled for means of repeats. With three repeats a side that floor is a range of three values: by a normal approximation about one row in eight reads `outside` when nothing differs [estimated], and this report has dozens of rows. One `outside` row is weak evidence. Nothing here is a verdict, and no row decides anything by itself.

## Warnings

- full-inc-transcribing-batch-r1: 221 cache hits in annotate
- full-inc-transcribing-batch-r1: 220 cache hits in interpret

## Runs

| run | status | frames | cold | resumed | cache hits | $ | $ / frame | $ / video | pipeline s | questions s |
|---|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-batch-r1 | done | 221 | yes | no | 441 | $23.2843 | $0.1054 | $23.28 | 1423.3 | 592.8 |

The stages' own counters, reported, never compared:

| run | annotate | interpret |
|---|---|---|
| full-inc-transcribing-batch-r1 | {"errors": 0, "failed_targets": 0, "repair_counts": {"bad_owner": 1, "link_already_linked": 1, "link_malformed": 7, "link_unknown_box": 1, "text_not_target": 511}, "repairs": 521} | {"errors": 0, "invalid_citations": 0, "submitted": {"no": 191, "unclear": 4, "yes": 25}} |

## Cost

Means over a configuration's repeats, per stage. One figure per stage, at the synchronous list price; the batch columns are half of it. s / frame is the wall time of the stages the dollars cover (the pipeline through `index`); answering the questions is timed per question, below.

| configuration | stage | $ | $ / frame | $ / video | batch $ | batch $ / frame | batch $ / video | s / frame |
|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-batch | annotate | $15.7133 | $0.0711 | $15.71 | $7.8567 | $0.0355 | $7.86 | 1.6 |
| full-inc-transcribing-batch | index | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.0 |
| full-inc-transcribing-batch | interpret | $6.6364 | $0.0300 | $6.64 | $3.3182 | $0.0150 | $3.32 | 0.9 |
| full-inc-transcribing-batch | read | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 3.5 |
| full-inc-transcribing-batch | summarize | $0.9346 | $0.0042 | $0.93 | $0.4673 | $0.0021 | $0.47 | 0.4 |
| full-inc-transcribing-batch | track | $0.0000 | $0.0000 | $0.00 | $0.0000 | $0.0000 | $0.00 | 0.1 |
| full-inc-transcribing-batch | all stages | $23.2843 | $0.1054 | $23.28 | $11.6422 | $0.0527 | $11.64 | 6.4 |

The question set, outside $ / video, and the judge, apart (means per run):

| configuration | $ / question | s / question | question set $ | judge $ |
|---|---|---|---|---|
| full-inc-transcribing-batch | $0.2686 | 22.0 | $7.2516 | $0.2713 |

Spend over all 1 runs: pipeline $23.2843; question set $7.2516; judge $0.2713 (what the last pass of `scry eval judge` paid: a verdict served from the judge's cache costs nothing).

## Commands

**Primary, side by side, with no order between them:** found and exact, as k/n of the rated entries per repeat, then the mean. Every comparison with the command list is by frame number. `exact.any` is what compares bases that have different readers; it can only tie or rise with a second reader, so it is shown as what the second reading adds, at its price, beside `exact.ocr`, not as a contest.

| configuration | found | exact.ocr | exact.vlm | exact.any | $ / frame | $ / video |
|---|---|---|---|---|---|---|
| full-inc-transcribing-batch | 7/7; mean 1 | 7/7; mean 1 | 7/7; mean 1 | 7/7; mean 1 | $0.1054 | $23.28 |

**Secondary:** the first-appearance error and the submission error (mean absolute frames over the entries that have one, per repeat), submitted and false run (k/n per repeat).

| configuration | first appearance, ocr | first appearance, vlm | first appearance, any | submitted | submission error | false run | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-batch | 0.14 over 7; mean 0.14 | 0.14 over 7; mean 0.14 | 0.14 over 7; mean 0.14 | 7/7; mean 1 | 0 over 7; mean 0 | 0/5; mean 0 | $0.1054 | $23.28 |

Per entry, in how many runs (of those that scored it). `summary only`: no localising entry covered the command and a summary entry of that level quoted it. `Y` and `y` are reported and not rated.

| configuration | # | text | found | exact.any | submitted | summary only | note | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-batch | 1 | `az account show` | 1/1 | 1/1 | 1/1 | — | — | $0.1054 | $23.28 |
| full-inc-transcribing-batch | 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 1/1 | 1/1 | 1/1 | — | — | $0.1054 | $23.28 |
| full-inc-transcribing-batch | 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 1/1 | 1/1 | 1/1 | — | — | $0.1054 | $23.28 |
| full-inc-transcribing-batch | 4 | `Y` | — | 1/1 | 1/1 | — | not rated | $0.1054 | $23.28 |
| full-inc-transcribing-batch | 5 | `y` | — | 1/1 | 1/1 | — | not rated | $0.1054 | $23.28 |
| full-inc-transcribing-batch | 6 | `kubectl config current-context` | 1/1 | 1/1 | 1/1 | — | — | $0.1054 | $23.28 |
| full-inc-transcribing-batch | 7 | `kubectl get nodes` | 1/1 | 1/1 | 1/1 | — | — | $0.1054 | $23.28 |
| full-inc-transcribing-batch | 8 | `kubectl get deployment` | 1/1 | 1/1 | 1/1 | — | — | $0.1054 | $23.28 |
| full-inc-transcribing-batch | 9 | `kubectl get pods` | 1/1 | 1/1 | 1/1 | — | — | $0.1054 | $23.28 |

Texts that appeared on screen and were never run: in how many runs a `submitted: yes` claimed them (false run).

| configuration | row | text | false run | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing-batch | N1 | `az login` | 0/1 | $0.1054 | $23.28 |
| full-inc-transcribing-batch | N2 | `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 0/1 | $0.1054 | $23.28 |
| full-inc-transcribing-batch | N3 | `kubectl rollout undo deployment/kodekloudapp` | 0/1 | $0.1054 | $23.28 |
| full-inc-transcribing-batch | N4 | `kubectl config current-context` | 0/1 | $0.1054 | $23.28 |
| full-inc-transcribing-batch | N5 | `kubectl get svc` | 0/1 | $0.1054 | $23.28 |

## Questions

**The positive questions (primary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-batch | 22 | 22 | 0 | 0 | 0 | 1; mean 1 | $0.2686 | $0.1054 | $23.28 |

**The negative questions (secondary).** Counts over the configuration's repeats; the mean scores correct 1, partial 0.5, wrong 0, per repeat and over them; unscored answers are counted and left out of means.

| configuration | answers | correct | partial | wrong | unscored | mean | $ / question | $ / frame | $ / video |
|---|---|---|---|---|---|---|---|---|---|
| full-inc-transcribing-batch | 5 | 5 | 0 | 0 | 0 | 1; mean 1 | $0.2686 | $0.1054 | $23.28 |

Per question, the label of each repeat (every answer, with the judge's verdict and quote for each rubric line, is in `scores.json`).

| configuration | question | polarity | labels per repeat | $ / frame | $ / video |
|---|---|---|---|---|---|
| full-inc-transcribing-batch | Q1 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q2 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q3 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q4 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q5 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q6 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q7 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q8 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q9 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q10 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q11 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q12 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q13 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q14 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q15 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q16 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q17 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q18 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q19 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q20 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q21 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q22 | positive | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q23 | negative | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q24 | negative | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q25 | negative | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q26 | negative | correct | $0.1054 | $23.28 |
| full-inc-transcribing-batch | Q27 | negative | correct | $0.1054 | $23.28 |

Stale answers (to a wording the question file no longer has), not judged: full-inc-transcribing-batch 0. Unscored answers: full-inc-transcribing-batch 0.

## Noise

Per configuration and metric: the value of each repeat (the mean of its units) and the largest paired difference between two repeats, which is the floor for one run against one run.

No configuration has two repeats: no floor was measured.

## Comparisons

No span has two configurations.
