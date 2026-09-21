# P4 and P4b: analysis beside the generated reports

The generated reports are `report.md` here and in `../p4b/`. This file holds what the analyst found by reading the run directories, the recorded tool calls and the batch state (`runs/eval/p4/`, `runs/eval/p4b/`, not committed). Nothing here comes from a prototype.

Five cold runs on the whole 221-frame sample, 27 draft questions (`docs/ground-truth/full-questions.md`): incremental transcribing twice in sync mode, no annotation twice, incremental transcribing once in batch mode. 0 errors, 0 retries. Spend $91.42 (P4 $71.79, P4b $19.63).

## Result

Every base ties at the ceiling: 135 of 135 answers judged correct, and the 7 commands are found, exact and submitted in all five runs with 0 of 5 false runs. The draft question set does not separate the bases. The judge was checked: 105 exact-string and time rubric lines checked mechanically with 0 disagreements, about 40 semantic verdicts and 9 full answers read, all agreed. Ten draft answers were checked against the frames and OCR and are right. The draft's problem is discrimination, not correctness.

## Cost and wall time

| base | annotate | interpret | summarize | $ per frame | $ per video | $ per question | s per question |
|---|---|---|---|---|---|---|---|
| incremental transcribing, sync (mean of 2) | $12.22, 739 s | $4.69, 252 s | $0.94, 82 s | 0.0808 | 17.85 | 0.263 | 22.6 |
| no annotation (mean of 2) | none | $3.80, 253 s | $0.82, 62 s | 0.0209 | 4.62 | 0.216 | 22.4 |
| incremental transcribing, batch (price paid) | $7.86, 355 s | $3.32, 209 s | $0.93, 81 s | 0.0548 | 12.11 | 0.269 | 22.0 |

- `read` took 128 s alone and 763 s with four or five processes contending. `track` 15 s. `index` under a second.
- Annotation makes answering dearer (69k against 58k input tokens per question) but the agent opens frames less often: 29 of 54 answers against 42 of 54.
- Cost per question by type, annotated then not: exact strings $0.211 / $0.180; when $0.150 / $0.146; paraphrases $0.361 / $0.233; values that changed $0.303 / $0.234; order $0.342 / $0.288; negatives $0.243 / $0.232.
- Repeats: the cost-per-question gap between the bases ($0.046) exceeds the largest gap between identical repeats ($0.013). Two repeats is weak evidence. Seconds per frame are confounded by contention.

## Sync against batch

- The batch run paid 0.68 of the sync price for the pipeline (annotate 0.64, interpret 0.71), not 0.5. Batched requests mostly wrote the prompt cache instead of reading it: about 161 of 221 annotate calls and 120 of 220 interpret calls were cache writes. `summarize` is never batched.
- Wall time: annotate took half the time (two batches of 172 and 49 requests, about 5 minutes; interpret's one batch of 220 took 3 minutes).
- Outputs are equivalent: 0 errors, the same command metrics, 27 of 27 questions, output tokens 3 % higher.
- **Known error in `../p4b/report.md` as generated:** it prices the batch run at $23.28 (cache writes at sync rates) and shows $11.64 in the batch column (halving `summarize`, which is not batched). The manifest's `cost_usd`, $12.11, is the price paid. `report.md` here projects $8.92 per video for batch from the sync runs, 36 % below what was measured. Both are fixed in code after this phase; the reports are regenerated then.
- The P4b report's warnings of 221 and 220 cache hits are false: they come from the batch path's second pass, which reads results from the call cache by design.

## Commands against the whole-video index

Found 7 of 7, exact 7 of 7 for the OCR reading and for the model's reading, submitted 7 of 7, false run 0 of 5, in all five runs, as on the 33-frame index. Nothing stopped being found. Ranks shift: on the 33-frame index the counting hit was always rank 1 or 2; here, with no annotation, 1, 1, 2, 2, 1, 1, 1; annotated, up to rank 4 for `kubectl get deployment` and `kubectl get pods`, whose second run at frames 200 to 203 and the grey shell suggestions at frames 189 and 205 to 207 interleave with the first run.

## Findability, from the recorded tool calls

- No answer was wrong or partial, so there is no failure to classify.
- Each answer that opened frames opened 1 to 3, always relevant. No agent browsed.
- Searches with no result: 7 of 157, 7 of 157 and 3 of 80. All but three were exact-phrase probes on negative questions.
- The first search hit the target moment for 19 of 20 single-moment questions in every run but one (18).
- The exception is Q1: "scheduler picks node for pods" never returns frame 19 within 20 hits in any index. Search is lexical with OR semantics and there is no embedder. The agents recovered through `kube-scheduler`, the step summaries and transition T19.
- A fixed probe of 42 first queries against all five indexes misses the target within 20 hits on 4 of 42 in every index but one (5). Annotation helps visual paraphrases (Q15 ranks the Docker Hub frame 2 against 12 to 13; Q20 ranks 1 to 2 against 3 to 12) and hurts Q3. The bases are not separable on this probe.
- Flooding: searching the create-deployment command returns 17 of 20 hits for the same line (six lifetimes, some of them OCR variants such as `kubect1`; six typing transitions; five frame groups). With `level: frame`, 13 to 23 of 50 hits duplicate each other; collapsing is broken by OCR jitter and by trigram matching `image` inside `Reimage`.
- Descriptions pollute: a search for "Region" returns five slide frames whose descriptions contain the word.

## Bugs and surprises

1. **Batch requeue bug, not exercised.** In `src/scry/providers/batch.py`, `run_pending` marks errored and expired requests done before re-queuing them, so the retry never resubmits them and the second pass calls them silently at the sync price.
2. **Calls with no targets.** 47 of 221 incremental calls are sent with "Targets: none." and cost $2.3 to $2.4 per sync run, 19 % of `annotate`. In 16 to 20 of them the model transcribes every box anyway: 481, 677 and 511 `text_not_target` repairs, a kind that was 0 in earlier phases.
3. **Junk description.** Frame 92 of the batch run has 4.7k characters of unrelated Dutch text after `</description>}`. It passed the schema and is in the index.
4. Box ids in descriptions: 2 of 221 in the batch run (frames 28 and 153), 0 in the sync runs.
5. Batch memory: resident size peaked at 2.3 GB against 1.2 GB for sync, because every pending request is held with its images.
6. `summarize` needed one boundary call and no map-reduce (largest step 40 transitions); 0 invalid references or citations; 23 to 30 steps with annotation against 14 to 19 without.
7. Index size 11 MB with annotation, 7.3 MB without. Without annotation the blank frame 0 has no index entry.
