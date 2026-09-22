# Presentation notes: every number on every chart, with its source and a voice-over line

Written 2026-09-21 on branch `presentation` from `rebase-boxes` at `f071ab7`; the cost chart was redrawn and the Gemini chart added from `rebase-boxes` at `fcc1860` (P10full, P11, compare-gemini); the hold-out charts and the local-model chart were added from `5c62ee6` (the hold-out comparison, ledger L76); the per-question panel was redrawn from `746b5f0` (ledger L80). Nothing was re-run; every number below is copied from a committed report, analysis or the ledger, and the source file is named beside it. The one paid call of this branch is the demo question in `demo.md` ($0.2142). Charts are 3840 x 2160 PNGs (1920 x 1080 at 2x), light background, drawn by a scratch matplotlib script that is not part of the repo.

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

## 10. `index-hierarchy.png`: one index, six levels

The six-level index of one session, drawn from `runs/v2/grouponly-100` (the video the charts above call a four-minute session; the word hold-out is not on the figure). Every entry is real and comes from the run directory:

| level (bottom to top) | count | what is drawn | example on the figure | source file |
|---|---|---|---|---|
| text lifetimes | 2,565 | one tile per lifetime from `first.t` to `last.t` (under 0.4 s drawn 0.4 s wide), packed into lanes: lifetimes under 2 s in the lower lanes, longer ones above; lanes carry no meaning | `L760` "AFDEndpoint", seen 50.0 to 73.5 s in 9 frames (the row the click added). The brief's "61.0 to 224 s" is not what `lifetimes.jsonl` holds: AFDEndpoint has eight lifetimes there (L365, L478, L760, L1451, L1490, L1580, L1649, L1827); L760 is the longest | `lifetimes.jsonl` |
| frames | 80 | one tick per settled frame at `t_settled` | | `frames.jsonl` |
| changes | 79 | one mark per transition at the end of its `t`; taller where the interpretation says `submitted: yes` | T22, 61.0 to 64.0 s, `submitted: yes`, action "The user clicked the blue "Add" button at the bottom of the Add endpoint panel.", result "The panel closed and the endpoint was created: a success toast "Saved Traffic Manager profile changes" appeared, and the endpoints table now lists two rows including the new disabled AFDEndpoint with weight 1 ..." (quoted with an ellipsis on the figure) | `changes.jsonl`, `interpretations.jsonl` |
| steps | 12 | one band per step over its `t` | S4 "Add an external endpoint to tm-profile-ap" (41.4 to 64.0 s), S6 "Add an external endpoint to the EU Traffic Manager profile" (94.2 to 125.6 s), S10 "Run the query and inspect the timechart" (178.1 to 200.8 s) | `steps.jsonl` |
| sections | 7 | one band per section, C1 to C7 | C2 "Add an external endpoint to the tm-profile-ap Traffic Manager profile" (24.6 to 64.0 s), C6 "Query Front Door access logs in Log Analytics" (161.6 to 200.8 s), C7 "Compare Kusto.Explorer and read the chart results" (200.8 to 223.9 s) | `sections.jsonl` |
| session | 1 | one band with the video label | V "Add AFDEndpoint to Traffic Manager profiles and check Front Door logs" | `video.json` |

Shared time axis 0 to 224 s (`frames.jsonl`, last `t_end` 224.0). Caption on the figure: "One index, six levels: every text box, every frame, every change and what it meant, steps, sections, the session. Search at any level; every entry cites its frames."

Voice-over: "The index has six levels over one time axis: every piece of text and how long it lived, every frame, every change with what it meant, steps, sections, the session; you can search at any level, and every entry cites the frames it came from."

## Session frame 22

`holdout-frame-22.png`: `runs/v2/grouponly-100/frames/00022.png` (2048x1080) at full size with seven boxes from `runs/v2/grouponly-100/boxes.jsonl` (frame 22) drawn and tagged with their ids, in the style of `demo-frame-198.png`: the toast `b55` (1629,215,1846,237) "Saved Traffic Manager profile changes", `b58` (1617,239,1882,257), `b60` (1614,255,1820,275) in blue; the saved row `b91` (433,477,510,497) "AFDEndpoint", `b89` (721,476,774,497) "Disabled", `b93` (1644,481,1653,491) "1" in aqua; and the row count `b112` (380,1018,518,1035) "Showing 1 - 2 of 2 results." (OCR reads `Showina`) in orange, the key citation. `holdout-frame-22-crop.png` is the frame's region x 340 to 820, y 440 to 1060 at 2x (960x1240), holding the saved row and the row count.

## Demo

`demo.md`: one real question, the tool calls and the answer with its citations, the cited frame `runs/eval/p4/full-inc-transcribing-r1/frames/00198.png` and box `198:b89`, and the same frame with the boxes drawn in `demo-frame-198.png` and `demo-frame-198-crop.png`. Cost $0.2142, 54 s.

## 7. `holdout-cost-per-config.png`: what a four-minute session costs to index

On the chart the video is called "a four-minute session" (title "What a four-minute session costs to index"); the file name and this note keep the hold-out name.

The hold-out video: `runs/videos/recording-2026-09-17.mp4`, 223.97 s, 2048x1080, 80 decoded frames (`docs/results/compare-gemini/hold-out.md`, What was run; the manifests' `duration`, `width`, `height`; `frames.jsonl` has 80 rows). One run per configuration. Each bar is the sum of the `annotate`, `interpret` and `summarize` `cost_usd` in the run's `manifest.json` (decode and OCR are free; the outline call in `runs/v2/grouponly-100`, $0.02, is not in its bar, as in the hold-out report's cost table).

| bar | $ | manifest | annotate / interpret / summarize |
|---|---|---|---|
| Transcribing, overlay, scale 1.0 | 11.42 | `runs/eval/v2/full-transcribing-100-r1/manifest.json` | 8.22 / 2.59 / 0.62 |
| Group-only, overlay, scale 1.0 (the default, ledger L73) | 9.32 | `runs/v2/grouponly-100/manifest.json` | 5.84 / 2.75 / 0.73 |
| Group-only, overlay, scale 0.67 | 7.68 | `runs/eval/v2/full-grouponly-067-r1/manifest.json` | 4.58 / 2.49 / 0.61 |
| No annotation | 2.94 | `runs/eval/v2/full-none-r1/manifest.json` | none / 2.23 / 0.71 |

The same four figures are the "build per video" column of `docs/results/compare-gemini/hold-out.md` (Cost and time). "5 of 5" is that report's Scores table: every pipeline index answers all five draft questions and passes all 16 rubric lines. The four numbers were read from the manifests here and agree with the report to the cent.

Voice-over: "On the hold-out video the owner's default index costs about nine dollars to build, the full second reading eleven and a half, and no annotation three; all four answer every question."

## 8. `us-vs-gemini-holdout.png`: Scry against Gemini on the same session, same questions

On the chart the video is called "a four-minute session" (title "Scry against Gemini on the same session, same questions"); the file name and this note keep the hold-out name.

All from `docs/results/compare-gemini/hold-out.md` (Scores; The failed lines, classified; Cost and time).

| measure | pipeline (four configurations, Opus 5 agent) | Gemini direct (`gemini-3.8-flash`, silent copy) |
|---|---|---|
| questions correct of 5 | 5 in each of the four | 3 |
| rubric lines passed of 16 | 16 in each | 13 |
| $ per question, Opus agent on the four full indexes | 0.349 (none), 0.372 (group-only 1.0), 0.381 (group-only 0.67), 0.392 (transcribing): shown as $0.35 to $0.39 | 0.060 |
| $ per question, Sonnet agent on the full default index (`runs/v2/grouponly-100`), the same five draft questions | mean $0.146 (ask total $0.7322 over 5: 0.0607, 0.3924, 0.1304, 0.0398, 0.1089), 5 of 5, 27 s; `docs/results/local/session-span/ask-judge-sonnet-draft.txt`, ledger L80; run files `runs/v2/ask/answers-sonnet5-draft.jsonl`, `judgments-sonnet5-draft.jsonl` | |
| seconds per question (not on the chart) | 34 to 43 | 28 |

The third panel, "dollars per question, same five questions", has three bars, all on the same five draft questions and the full index: Gemini direct $0.06 (3 of 5); Scry with a Sonnet agent $0.15 (5 of 5; mean $0.146, L80); Scry with an Opus agent $0.35 to $0.39 (5 of 5; the four full indexes, drawn as the solid bar to $0.35 and a light segment to $0.39). The span-index figures of L79 ($0.058 Sonnet, $0.238 Opus, on a different five questions) are no longer on this chart: L80 says the video's per-question line is fifteen cents, not six, because only the same-questions comparison belongs beside Gemini's figure.

The caption is the report's two failed Q1 and Q2 lines: Gemini wrote `FRONTDOOR-A-cnhedcc5b0d0h4e0.z01.azurefd.net` for `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`, the 44-character hostname in the find-on-page highlight on frame 0, on screen for 9 s (every pipeline index quotes it exactly, box `0:b116`); and it gave the added KQL line as `where requestUri_s contains "testHostDeviceAllocationServiceClientCertificate"` where frame 73 reads `"ServiceA/Certificate"`. One run per arm, so repeat noise is unknown; the four pipeline indexes, built and asked separately, agree on all 80 verdicts.

Voice-over: "On a video it had never seen, every pipeline index answered all five questions and quoted every string exactly; Gemini got three, rewrote a hostname that sat highlighted on screen for nine seconds, and invented the query filter that was added."

## 9. `local-vs-api.png`: a local open-weight model on annotate, against the API

Drawn by `local-vs-api.py` from `local-vs-api.json`, so the numbers can be replaced (for the hold-out video) and the chart re-run with `uv run --with matplotlib python docs/presentation/local-vs-api.py`; the JSON's `dataset` string is printed as the subtitle so the chart always says which video it describes. Current numbers, from `docs/decision-ledger.md` L76 (smoke span of the sample video, 11 frames, group-only, one run each):

| measure | API, Opus 5 | local, Qwen 3.8 27B (4-bit) at a hosted open-weight rate | source |
|---|---|---|---|
| annotate, $ per frame | 0.078 | 0.005 | L76 ("$0.005 a frame against $0.078"); `docs/results/local/report.md` (hosted rate: OpenRouter's list for `qwen/qwen3.8-27b` on 2026-09-21; the API figure is P3's $0.0782 at scale 1.0) |
| reference pairs reproduced, % | 95 to 97 (the API's own repeat floor: `smoke-ids100` r1 against r2, 97.4 and 95.0) | 75 to 77 (`local2/smoke-L1-r1` against r1 and r2: 75.0 and 76.9) | L76; `docs/results/local/second-attempt/quality-table.txt` |

The "15.6x cheaper" label is computed from the two cost figures in the JSON (L75 says 14 to 16 times). The caption is L76's finding: temperature 0 and the schema's field descriptions in the prompt took the 27B from 28 % of the API's pairs (L75) to 75 to 77 %; L76 (a) keeps it a candidate, not a replacement.

Voice-over: "A local twenty-seven-billion-parameter model reproduces three quarters of the API's labels at a fifteenth of the price once it is run at temperature zero with the schema's descriptions in the prompt: a candidate, not yet a replacement."

## 11. `session/` and `stages/`: the frames and the stage overlays, made by `stages.py`

`uv run --with pillow python docs/presentation/stages.py runs/v2/grouponly-100 docs/presentation 12 31` produced both from the run's own records (nothing re-run, no model called).

- `session/00.jpg` to `79.jpg`: the 80 settled frames of `frames.jsonl` downscaled from 2048x1080 to 1280x675 with LANCZOS, JPEG quality 90 (the PNG set was over 15 MB; the JPEG set is 10.2 MB).
- `stages/read/12.png` to `31.png` (20 frames, the add-endpoint flow): every OCR box of `boxes.jsonl` for the frame as a thin blue (#2a78d6) outline. 98 to 184 boxes a frame.
- `stages/track/NN.png`: the change records of the transition INTO frame NN (`changes.jsonl`, `to_frame == NN`): `appeared` boxes filled aqua-green (#1baf7a) at 25 % alpha; `changed`, `reread`, `appended` and `truncated` boxes filled orange (#eb6834) at 25 % alpha; `removed` boxes as a thin red (#e34948) outline at the rectangle the record holds, which is where the text sat on the previous frame; unchanged and moved boxes untouched. Frame 21 (the mouse moving onto Add) has no records and is drawn bare.
- `stages/annotate/NN.png`: the labels in force at the frame as `scry.annotate.join.Labels` joins them (the view the index uses, so a box labelled on an earlier frame of its lifetime keeps that label): each container's bounding rectangle over the boxes of the frame assigned to it, windows blue and popups orange, tagged "window: name" or "popup: name" with the name the model gave when it labelled those boxes (so a tab that was later renamed can carry its earlier title); every pair link in force as a thin aqua line from the key box's right edge to the value box's left edge; every run in force as a thin violet (#4a3aa7) bracket under its boxes. Record links (tables) are not drawn. Boxes with no label in force are untouched.
- `stages/interpret/NN.png`: the frame with a card in the top-left corner holding the transition's id and `action` (two lines), then `entered_text` and `submitted`, from `interpretations.jsonl`; three lines at most.

Strokes are 2 px at full resolution before the downscale, so about 1.25 px at 1280 wide.

## `index-hierarchy.png`, second version

The C2/C7 callout now sits in clear space above the sections band with a leader line to C2; the T22 callout is one line in the gap above the changes band, to the right of the T22 mark: T22, 61.0 to 64.0 s, submitted: yes: "The user clicked the blue Add button" ... "a success toast ... appeared"; the L760 label and the frames note sit in the gap between the frames and lifetimes bands. No text crosses a band.
