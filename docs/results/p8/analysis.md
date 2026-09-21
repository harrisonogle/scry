# P8: every stage on Sonnet 5, analysis beside the generated report

Matrix `evals/p8.toml`. The whole 221-frame sample with `claude-sonnet-5` for `annotate`, `interpret`, `summarize` and the answering agent; the judge stays on Opus 5. Two bases (no annotation; incremental transcribing), two cold repeats each: 4 of 4 runs clean on a clean tree at `0275ac9`, 0 errors, schema failures, truncations or refusals in any stage. Spend $25.90 (pipeline $18.63, questions $6.43, judge $0.83). The comparison set is P4, the same two bases on Opus 5 (`../p4/`). The generated `report.md` here compares only the two Sonnet bases; the comparison with Opus is below. Numbers were computed from the run directories (`runs/eval/p8/`, `runs/eval/p4/`, not committed) by the scripts in `scripts/`; the truth table for the typing transitions was read by eye from crops of the live line. Nothing here comes from a prototype.

## Cost (mean of two repeats; S/O is Sonnet over Opus)

| | no annotation, Opus | no annotation, Sonnet | S/O | annotated, Opus | annotated, Sonnet | S/O |
|---|---|---|---|---|---|---|
| `annotate` $ | none | none | | 12.22 | 5.21 | 0.43 |
| `interpret` $ | 3.80 | 1.48 | 0.39 | 4.69 | 1.80 | 0.38 |
| `summarize` $ (calls) | 0.82 (25) | 0.45 (90) | 0.56 | 0.94 (36) | 0.37 (50) | 0.39 |
| **$ per video** | 4.62 | **1.93** | 0.42 | 17.85 | **7.38** | 0.41 |
| **$ per question** | 0.216 | **0.053** | 0.25 | 0.263 | **0.066** | 0.25 |
| seconds per question | 22.4 | 10.3 | 0.46 | 22.6 | 10.4 | 0.46 |

Answering costs a quarter of Opus and not 40 %, because the Sonnet agent does less: 2.6 to 2.8 turns and 3.0 to 3.6 tool calls per answer against 3.2 to 3.4 and 4.1 to 4.7, and it opens frames in 12, 11, 7 and 5 of 27 answers against 19, 23, 15 and 14.

## Answers

Sonnet without annotation 27 of 27 twice; annotated 26 and a partial, then 27. Opus: 27 of 27 in all four. The one partial (annotated r1, Q15, "the repository has 2 tags") is the agent stopping early: the index holds "This repository contains 2 tag(s)." and the agent counted the one table row a description mentions without opening the frame. It is not a wrong label. **No answer is wrong because of a Sonnet label**, although the labels are worse, as in P7 (`mark_match` 0.885 against 0.945; 204 to 221 pairs against 353 to 355; the PowerShell window labelled a popup on 38 to 41 of about 55 frames against 1 of 60).

**What the rubric does not see.** Q18 is judged correct in all four Sonnet answers, and all four say the presenter "retyped `kubectl get pods`" and abandoned it. Only `ku`, `kubect` and `kubectl ` were typed; the rest was the shell's grey suggestion. All four Opus answers call it a suggestion. The Sonnet agents repeat what the Sonnet index says.

## Commands, and the honest text-change contract

| run | found | exact (OCR / model reading) | submitted | false run |
|---|---|---|---|---|
| Opus, all four | 7/7 | 7/7 / 7/7 | 7/7 | 0/5 |
| Sonnet, no annotation, r1 and r2 | 7/7 | 7/7 / none | 5/7, 5/7 | 0/5 |
| Sonnet, annotated, r1 | 7/7 | 7/7 / 7/7 | 5/7 | **1/5** |
| Sonnet, annotated, r2 | 7/7 | 7/7 / 7/7 | 6/7 | 0/5 |

Finding and exact reading hold, because they rest on OCR and lifetimes. What breaks is what `interpret` writes.

- **Suggested text recorded as entered.** On the 21 typing transitions of the terminal part (T155 to T212), Sonnet puts never-typed suggested text into `entered_text` on 17, 15, 18 and 16; Opus on 2, 2, 3 and 1. Sonnet's record mentions a suggestion at all on 1, 4, 6 and 4 of the 21; Opus on 21, 19, 21 and 21. Example, the same in all four Sonnet runs (T165): `entered_text: "az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2"`, "The user typed a new az aks scale command". The presenter typed `az ak`. Opus: `az aks`, "followed by a greyed predictive suggestion".
- **The false run** (annotated r1, T213): `entered_text: "kubectl get svc"`, `submitted: yes`. What ran was `kubectl get service`; `svc` was the grey suggestion on the frame before.
- **Missed submissions.** `az configure` in 3 of 4 runs: `submitted: yes` with `entered_text: null`, so no claim attaches to the command. `az aks get-Credentials` in 4 of 4: Sonnet lower-cases the displayed capital C.
- **`submitted` loses its meaning.** Sonnet says yes 54 to 59 times per run (38 to 40 with no entered text, 8 to 13 on slide advances, page navigations counted as submissions) and unclear 33 to 43 times; Opus yes 23 to 26 and unclear 1 to 5.
- Sonnet copies OCR misreads that Opus corrects from the image (`AKS1-KdeKloudApp` in 4 of 4 runs), writes 23 to 34 invalid citations per run against 0 (it invents a box id where there is nothing to cite), and its mean confidence is 0.63 to 0.66 against 0.81 to 0.83.

## Summaries

In 4 of 4 Sonnet runs the section boundary call makes every step its own section (25 and 62, 25 and 22 sections against Opus's 5 to 8), and the step count is unstable (25 against 62 on the same base). The summaries inherit `interpret`'s errors: a step titled "Verify Azure login, scale AKS, and get credentials" (nothing was scaled); "types `kubectl rollout undo deployment/kodekloudapp` at the prompt but does not run it"; a video summary that says the deployment "completes successfully", which the video never shows.

## One thing Sonnet does better

It obeys "Targets: none": 0 `text_not_target` repairs against 481 and 677, and about 450 billed output tokens on those calls against about 800. (These runs have the plainer no-target line; P4's Opus runs did not.)

## Noise

Repeats agree on found, exact and the answers. Inside repeat noise: the one partial answer, the one false run. Far outside it: suggestions recorded as entered (15 to 18 against 1 to 3, repeat gap 2 or less), the `submitted` counts, invalid citations, sections equal to steps, frames opened per answer, the same two missed submissions.

## Judge and bugs

56 exact-string verdicts checked mechanically, 0 disagreements; 16 semantic verdicts read, all agree. A `submitted: yes` with no `entered_text` silently drops a command's submission claim. `judge_dollars` in P4's scorecards reads 0 for cached verdicts, so judge cost is not comparable across phases. One transient HTTP 520 was retried by the SDK.
