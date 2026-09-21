# P3: image-scale sweep on `annotate`

Matrix `evals/p3.toml`. Incremental transcribing, prompt `annotate-v4`, stages `read`, `track`, `annotate` only. Seven image scales (1.0, 0.67, 0.5, 0.4, 0.3, 0.25, 0.2), two spans (smoke, frames 145–155, 11 frames; span2, frames 155–187, 33 frames), two cold repeats each: 28 runs, 616 model calls, 0 errors, 0 transient errors, 0 call-cache hits, 0 lost usage. Spend $29.04. Run directories are under `runs/eval/p3/` (not committed). The numbers below were computed from those run directories by the scripts in `scripts/`; nothing here comes from a prototype.

The scale applies to both images sent to the model (the frame and the tagged overlay). Tags stay 12 px at every scale, so at reduced scale they grow relative to the text they sit on.

Pairs of values are smoke | span2.

## Cost against scale

Mean of two repeats. Calls (11 | 33) and targets (255 | 425) are the same at every scale.

| scale | input tokens per call, cached prompt included | output tokens per call | $ per frame | $ per 221-frame video | annotate wall (s) |
|---|---|---|---|---|---|
| 1.0 | 9.4k | 1747 / 1216 | .0782 / .0614 | 17.29 / 13.57 | 64 / 138 |
| 0.67 | 6.4k | 1895 / 1292 | .0632 / .0483 | 13.97 / 10.68 | 72 / 144 |
| 0.5 | 5.4k | 2190 / 1448 | .0657 / .0473 | 14.51 / 10.45 | 94 / 170 |
| 0.4 | 4.9k | 2116 / 1565 | .0613 / .0477 | 13.54 / 10.54 | 84 / 177 |
| 0.3 | 4.5k | 2197 / 1348 | .0613 / .0403 | 13.56 / 8.90 | 86 / 159 |
| 0.25 | 4.4k | 1440 / 1018 | .0417 / .0313 | 9.21 / 6.93 | 53 / 124 |
| 0.2 | 4.2k | 1215 / 913 | .0354 / .0280 | 7.82 / 6.19 | 46 / 111 |

- Cost noise between the two 1.0 repeats is $0.0076 per frame on smoke and $0.0004 on span2.
- Span2 wall times from 0.3 down are not comparable: the P4 runs started alongside at 13:47.
- The shared prompt (about 3.6k tokens) is read from the prompt cache on every call after the first.
- At 1.0 on span2 the output is half the cost of `annotate` ($1.00 of $2.02); at 0.67 it is two thirds.

Savings by step: 1.0 to 0.67 saves $0.013–0.015 per frame, about $3 per video. 0.67 to 0.5 saves nothing, because output tokens rise by as much as the images shrink. 0.5 to 0.4 is within the repeat noise. Below 0.3 the saving comes from the model giving up on links and readings.

## Quality against scale

The reference for each scale is a 1.0 repeat. The 1.0 row compares one 1.0 repeat with the other, which is the run-to-run noise.

| scale | label clashes | mark_match % | readings on wrong box | reference pairs reproduced % | container differs, % of targets | terminal boxes in the terminal window (of 9 / of 125) | tooltips as own popup (of 4) | frame 150 pairs correct / wrong / missing of 28 |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 12 / 51 | 94 / 93 (repeat gap 1.5 / 1.1) | 0 / 5 | 95 / 94 | 0.4 / 0.2 | 9 / 125 | 3 | 28/0/0 |
| 0.67 | 60 / 315 | 90 / 89 | 2 / 12 | 96 / 94 | 0.2 / 1.3 | 9 / 122 | 4 | 28/1/0 |
| 0.5 | 123 / 521 | 88 / 82 | 6 / 26 | 93 / 82 | 0.8 / 1.1 | 9 / 122 | 4 | 27/1/0 |
| 0.4 | 252 / 983 | 75 / 66 | 27 / 76 | 56 / 66 | 2.7 / 2.7 | 6 / 119 | 4 | 18/8/10 |
| 0.3 | 565 / 2062 | 45 / 25 | 74 / 159 | 24 / 11 | 3.3 / 3.9 | 6 / 115 | 4 | 8/17/20 |
| 0.25 | 729 / 2583 | 13 / 9 | 79 / 135 | 13 / 9 | 2.0 / 4.4 | 5 / 112 | 2 | 5/10/23 |
| 0.2 | 934 / 3183 | 6 / 2 | 37 / 41 | 0 / 8 | 6.3 / 31 | 0.5 / 20 | 0 | 0/10/28 |

- Repairs stay at 0–3 per run at every scale, including the scales where the labels are mostly wrong. Only `mark_match` tracks the collapse in the manifest.
- Containers per record hold at 1.45 | 1.94 down to 0.3 and fall to about 1.3 | 1.76 at 0.2.
- Links by kind (run/pair/record) are about 8/39/5 | 5/45/4 at 1.0 and hold until 0.4, where the run-link count becomes erratic. At 0.2 they are 1/12/2 | 0/16/2.
- Real words read as "" number 5 | 15 at 1.0, show no trend down to 0.4, and jump to 27 | 35 at 0.2.

## By eye

**The edited line on frame 155** (four readings per scale; the measured text absorbs the shell's suggestion, the truth is a bare `a`). At 1.0 all four are good (`a_ login`, `a`, `a login`, `a login`). At 0.67 three are good and one is `az login`. At 0.5 all four read the bare prompt, so the `a` is lost, and all four descriptions say the console is empty except for the prompt. At 0.4 and below the reading is another box's text, empty, or invented.

**Span2 command lines** (frames 161, 166, 172, 175; eight readings per scale). At 1.0 and 0.67 all eight are faithful to what is displayed. At 0.5 frame 175 is empty in both repeats, and so is frame 165. At 0.4 one of eight is right. At 0.3 none is right and the model invents commands that were never on screen (`az aks nodepool list --resource-group …`, span2-s030-r2 frame 165).

**Descriptions** (frames 150, 151, 155). Accurate at 0.5 apart from the lost `a`. At 0.3 the tooltip is still read but items are invented. At 0.2 they are wrong, and 55 of 88 say the text is illegible. No box ids appear in any of the 616 descriptions. Four descriptions mention "the target" and three at 0.3 and 0.2 mention the overlay.

**Overlays on frame 150.** At 0.3, 44 of 135 tags are partly painted over by a later tag, tags cover the left navigation text, and the UI text is 7 px high. At 0.2, 82 of 135 tags are overlapped and 48 boxes are more than half covered by a tag.

## Where it falls

Second readings fall first: a small drop at 0.67 (equal to the spread between the two 0.67 repeats), a clear one at 0.5, where the live prompt lines are the casualty. Links and membership of the terminal window fall sharply at 0.4. Everything has collapsed by 0.3. Container assignment and the tooltips are the most robust. Every fall from 0.4 down is far outside the repeat noise.

## Bugs and surprises

1. At reduced scale the fallback in `place_label` (`src/scry/overlay.py`) can put a box's tag outside its window. At 0.4 on frames 147, 154 and 155 the prompt line's tag lands in the browser's left gutter; the line is labelled as browser and a neighbouring browser box as terminal, in every 0.4 run. At 0.67 the same happens to two boxes on frame 170 in both repeats. `label_clashes` counts these and nothing acts on the count.
2. In smoke-s100-r1 frame 151 the tooltip popup is listed with no boxes; its one box is assigned to the browser window and read as empty. This is an error in a reference run.
3. Two descriptions end in stray characters ("…top right.map", "…top.z"), both on frame 150 at 0.3 and 0.2.
4. At 0.2 the local PowerShell window is labelled as a popup named "Azure Cloud Shell terminal" in more than 20 records.
5. At 0.67 and 0.5 both repeats add one wrong pair on frame 150 linking a navigation item to "Subscription ID…". At 0.5 the wrapped key on frame 150 loses its second line.
6. Three runs are flagged `git_dirty` (smoke-s067-r2, smoke-s050-r1, span2-s067-r1) because an untracked scratch file sat in the repo root for about three minutes. No source was touched. HEAD moved from ed9c5e1 to 6ac8d63 during the sweep; that commit touched only `docs/` and `evals/`.
