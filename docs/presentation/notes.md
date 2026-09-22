# Presentation notes: every number on every chart, with its source and a voice-over line

Written 2026-09-21 on branch `presentation` from `rebase-boxes` at `f071ab7`; the cost chart was redrawn and the Gemini chart added from `rebase-boxes` at `fcc1860`, which holds the P10full, P11 and compare-gemini results. Nothing was re-run; every number below is copied from a committed report, analysis or the ledger, and the source file is named beside it. The one paid call of this branch is the demo question in `demo.md` ($0.2142). Charts are 3840 x 2160 PNGs (1920 x 1080 at 2x), light background, drawn by a scratch matplotlib script that is not part of the repo.

## 1. `cost-per-video.png`: dollars per 221-frame video by configuration

| bar | $ | source |
|---|---|---|
| Every-frame transcribing, projected from P1's span2 (33 frames): $0.2475 per frame x 221 | 54.70 | `docs/results/savings.md` (P1 row; "per-video figures are linear projections" in How to read it) |
| Incremental transcribing, sync, Opus 5 (the working default), mean of two cold runs | 17.85 | `docs/results/p4/analysis.md` (Cost and wall time), `docs/results/savings.md` (baseline) |
| Group-only, tagged overlay, scale 1.0 (P11 `full-ids100-grouponly`, one run, 27 of 27) | 16.30 | `docs/results/p11/report.md` (cost table, questions.positive 22 of 22 and negative 5 of 5), `docs/decision-ledger.md` L69 |
| Group-only, coordinates, scale 0.67 (P10full `full-coords067-sync-r1`, one run, 27 of 27) | 13.83 | `docs/results/p10/analysis.md` (whole-video table), `docs/decision-ledger.md` L69 |
| Group-only, coordinates, scale 0.5 (P10full `full-coords050-sync-r1`, one run, 27 of 27) | 13.41 | `docs/results/p10/analysis.md` (whole-video table), `docs/decision-ledger.md` L69 |
| Group-only, tagged overlay, scale 0.67 (P11 `full-ids067-grouponly`, one run, 27 of 27) | 12.62 | `docs/results/p11/report.md`, `docs/decision-ledger.md` L69 |
| Incremental transcribing, batch mode (price paid) | 12.11 | `docs/results/p4/analysis.md`, `docs/decision-ledger.md` L62 |
| Every stage on Sonnet 5, incremental transcribing | 7.38 | `docs/results/savings.md` (P8 row), `docs/decision-ledger.md` L66 |
| No annotation, Opus 5 | 4.62 | `docs/results/p4/analysis.md`, `docs/decision-ledger.md` L62 |
| Every stage on Sonnet 5, no annotation | 1.93 | `docs/results/savings.md` (P8 row), `docs/decision-ledger.md` L66 |

The Sonnet bars carry the caption "breaks the typed-against-suggested rule": on Sonnet 5 `interpret` records suggested text as entered on 15 to 18 of 21 typing transitions against 1 to 3 on Opus (`docs/decision-ledger.md` L66; `docs/results/p8/analysis.md`). The subtitle's "three quarters" is annotate $12.22 of $17.85 (`docs/results/p4/analysis.md`). "27 of 27" beside a bar is the draft question score of that run (the Sonnet incremental-transcribing bar had one partial in one of two runs, so it carries the rule caption instead). Colour is the family: blue transcribing (second reading on), aqua group-only (no second reading), orange Sonnet 5 on every stage, light blue the projection. Ledger L69 on the group-only bars: all four are 27 of 27 and 7 of 7 found and exact; all four have `submitted` 6 of 7 because `interpret` lower-cases `get-Credentials` without the second reading; coordinates save nothing over the overlay at the same scale, so the tagged overlay stays the default. The saving of group-only against transcribing is $1.55 at 1.0 and $5.23 at 0.67 (L69).

Voice-over: "Indexing one fourteen-minute video costs about eighteen dollars with the full annotation, twelve to sixteen without the second reading, and under five with no annotation at all; labelling only what changed is what keeps it off the fifty-five-dollar bar."

## 2. `scale-cliff.png`: second-reading agreement and cost per frame against image scale

All from `docs/results/p3/report.md`, mean of two cold repeats, smoke span (11 frames) and span2 (33 frames).

| scale | mark_match % smoke / span2 | $ per frame smoke / span2 |
|---|---|---|
| 1.0 | 94 / 93 | 0.0782 / 0.0614 |
| 0.67 | 90 / 89 | 0.0632 / 0.0483 |
| 0.5 | 88 / 82 | 0.0657 / 0.0473 |
| 0.4 | 75 / 66 | 0.0613 / 0.0477 |
| 0.3 | 45 / 25 | 0.0613 / 0.0403 |
| 0.25 | 13 / 9 | 0.0417 / 0.0313 |
| 0.2 | 6 / 2 | 0.0354 / 0.0280 |

The band between 0.5 and 0.4 is the cliff named in the report's "Where it falls" and in ledger L60 ("a cliff, not a slope"). The cost line on the chart, "1.0 to 0.67 saves about $3 a video; 0.67 to 0.5 saves nothing", is the report's "Savings by step". The repeat gap at 1.0 (1.5 and 1.1 points) is the report's quality table. Two panels, one x axis, no twin axes.

Voice-over: "Shrink the images and the labels fall off a cliff between half and forty percent scale, while the cost barely moves, so the scale stays at one."

## 3. `per-question.png`: the Opus agent against the Sonnet agent on the same index

All from `docs/results/p9/analysis.md` (Scores and cost; The honest text-change contract), P4 (Opus 5 agent) against P9 (Sonnet 5 agent), both over P4's Opus-built annotated index, 27 questions, two runs each side.

| measure | Opus 5 agent (P4) | Sonnet 5 agent (P9) |
|---|---|---|
| $ per question, annotated index | 0.263 | 0.062 |
| seconds per question | 22.5 | 9.5 |
| answers that opened a frame, per run of 27 (range over the four P4 / P9 runs) | 15, 14, 19, 23 -> 14 to 23 | 3, 3, 6, 6 -> 3 to 6 |
| quotes a text its results marked as read differently, and says so | 40 of 46 | 3 of 18 |
| questions correct of 27 (annotated r1, r2) | 27, 27 | 27, 26.5 |

The frames-opened range covers both the annotated and the no-annotation runs (the analysis's per-run list), so "14 to 23" and "3 to 6" are the extremes of those four runs.

Voice-over: "A Sonnet agent answers the same questions for a quarter of the price and ties on score, but it opens a fraction of the frames and almost never says when the two readers disagree."

## 4. `what-annotation-bought.png`: questions correct of 27 by phase and base

| phase | annotated (incremental transcribing) | no annotation | source |
|---|---|---|---|
| P4, Opus agent, frames open | 27, 27 | 27, 27 | `docs/results/p4/analysis.md` (Result: 135 of 135), `docs/results/p9/analysis.md` (Scores table, P4 column) |
| P6, Opus agent, index only (no pixels) | 27, 27, 27 (two sync-built, one batch-built) | 26 and a partial, twice | `docs/results/p6/analysis.md` (Result; The one difference) |
| P8, Sonnet 5 on every stage, frames open | 26.5, 27 | 27, 27 | `docs/results/p9/analysis.md` (Scores table, P8 column), `docs/decision-ledger.md` L66 |
| P9, Sonnet 5 agent on the Opus index, frames open | 27, 26.5 | 27, 27 | `docs/results/p9/analysis.md` (Scores table, P9 column) |

The callout under P6 no-annotation: Q2's third rubric line, which box an arrow beside two named boxes leads to on a slide, is nowhere in an unannotated index and is in the per-frame description of the annotated ones (`docs/results/p6/analysis.md`, The one difference; ledger L65). The P8 and P9 partials are Q15, the agent stopping early or counting from a description without opening the frame (`docs/results/p9/analysis.md`). "26.5" is how the P9 analysis writes one partial.

Voice-over: "With the frames open every configuration gets all twenty-seven; take the pixels away and one rubric line separates the annotated index from the bare one, and what carried it was the screen description."

## 5. `pipeline.png`: the stages

Stage names and order from `docs/2026-09-21-return-briefing.md` ("Stages: `decode, outline, read, track, annotate, interpret, summarize, index, ask`"). What each stage measures or labels is from the same briefing and `docs/pipeline-versus-video-model.md` (structural points 1 and 2: OCR at full resolution per frame, a second reading stored beside the OCR reading, an answer that names a frame and a text box). The outline stage is optional, from Gemini, about $0.10 a video (ledger L58). No numbers on the chart.

Voice-over: "Three stages measure the screen without a model, three let a model label only what was measured, and the agent answers from the index with a frame and a box behind every claim."

## 6. `us-vs-gemini.png`: the pipeline against Gemini asked directly

All from `docs/results/compare-gemini/report.md` (Scores; Exactness, checked mechanically; Cost and time per question) and `docs/decision-ledger.md` L70. Same video, the same 27 draft questions (22 positive, 5 negative), the same blind judge (`judge-v1`, Opus 5).

| measure | pipeline (P4, Opus agent, four runs) | G1 Gemini direct (`gemini-3.8-flash`, the video and one question per call) | G2 Gemini transcript, then Opus answers |
|---|---|---|---|
| positive questions correct of 22 | 22 in each run | 17 | 16.5 |
| negatives of 5 | 5 | 5 | 5 |
| exact strings exact of 14 | 14 in each run | 7 | 8 |
| $ per question | 0.263 | 0.079 (the report's mean $0.0785; median $0.039) | 0.038 (Opus answers $0.023 plus the $0.41 transcript amortised over 27) |
| seconds per question | 22 | 32 | 8 (plus the 237 s transcript once) |

The caption, "Gemini invented terminal runs where the shell showed a grey suggestion: a third `kubectl get pods` "at 12:57", with plausible output", is L70's wording and the report's Q18 line (invented: a third run "at 12:57" with output `kodekloudapp-679b75cb5-mm42w 1/1 Running 0 19s`, where frame 213's scrollback holds two runs). Every Gemini miss on an exact string is a one-character misread (`20.247.253.108` for `20.247.251.108`, `R01` for `RG1`, the registry name returned five ways). Break-even (report): the Opus agent never; the Sonnet agent on an unannotated index against G1 after about 181 questions. Not on the chart: seconds per question, the 70 of 83 rubric lines for each Gemini arm, and G1c (one long Gemini call listing the commands, 11 of 13 exact, 0 false runs of 5), which shows the misreads are not only a resolution ceiling.

Voice-over: "Asked the same twenty-seven questions, Gemini gets every 'when' and every negative, misses half the exact strings by one character, and invents a terminal command exactly where the shell was showing a grey suggestion; the pipeline gets all of them, at three times the price per question." 

## Demo

`demo.md`: one real question, the tool calls and the answer with its citations, the cited frame `runs/eval/p4/full-inc-transcribing-r1/frames/00198.png` and box `198:b89`, and the same frame with the boxes drawn in `demo-frame-198.png` and `demo-frame-198-crop.png`. Cost $0.2142, 54 s.
