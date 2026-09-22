# P5: referencing arm D (no overlay) against arm A

Matrix `evals/p5.toml` (ledger L61). Under arm D the model gets one clean frame and no tagged overlay; the user turn lists every OCR box as `id: x0,y0,x1,y1`; answers are by box id exactly as under arm A. Incremental transcribing, prompt `annotate-v4+D`, stages `read`, `track`, `annotate`; spans smoke (frames 145–155) and span2 (155–187); scales 1.0, 0.67, 0.5; two cold repeats: 12 runs, 264 calls, 0 errors, 0 call-cache hits. Spend $17.52. Code at `071cf28`. The comparison set is P3 (`../p3/report.md`): arm A, same spans, same targets (the boxes and lifetimes hashes are identical), same scales. The numbers were computed from the run directories (`runs/eval/p5/`, `runs/eval/p3/`, not committed) by the scripts in `scripts/`. Nothing here comes from a prototype.

Pairs of values are smoke | span2.

## Cost

Mean of two repeats. Calls (11 | 33) and targets (255 | 425) are the same as P3.

| scale | arm | input tokens per call | output tokens per call | $ per frame | $ per 221-frame video |
|---|---|---|---|---|---|
| 1.0 | D | 7.8k / 7.9k | 2081 / 1345 | .0823 / .0571 | 18.18 / 12.61 |
| 1.0 | A | 9.4k | 1747 / 1216 | .0782 / .0614 | 17.29 / 13.57 |
| 0.67 | D | 6.3k / 6.4k | 2766 / 1947 | .0847 / .0648 | 18.71 / 14.32 |
| 0.67 | A | 6.4k | 1895 / 1292 | .0632 / .0483 | 13.97 / 10.68 |
| 0.5 | D | 5.8k / 5.9k | 2921 / 1827 | .0861 / .0593 | 19.02 / 13.11 |
| 0.5 | A | 5.4k | 2190 / 1448 | .0657 / .0473 | 14.51 / 10.45 |

- At 1.0 the arms cost the same on smoke (warm against warm: D .0748, A .0744) and D is 7 % cheaper on span2.
- The list of rectangles costs about as many input tokens as the overlay image at 0.67 and more at 0.5.
- Billed output rises under arm D, most at reduced scale, while the stored answer is the same size in both arms (about 2960 | 2190 characters per call). The extra output is outside the answer. It rises on calls with more than 3 targets.
- Under arm D a smaller scale saves nothing: D at 0.67 and at 0.5 costs more per frame than D at 1.0 on both spans.
- Repeat noise between the two d100 runs: $0.0010 per frame on smoke, $0.0017 on span2.

## Quality

Yardstick: both P3 s100 repeats, averaged, as in P3. The first row is P3's s100-against-s100 noise.

| scale | arm | mark_match % | readings on wrong box | reference pairs reproduced % | container differs % | terminal boxes (of 9 / of 125) | tooltips as own popup (of 4) | frame 150 pairs correct/wrong/missing |
|---|---|---|---|---|---|---|---|---|
| 1.0 | A (noise) | 94 / 93 (gap 1.5 / 1.1) | 0 / 5 | 95 / 94 | 0.4 / 0.2 | 9 / 125 | 3 | 28/0/0 |
| 1.0 | D | 92.8 / 95.2 (gap 7.9 / 0.3) | 6 / 2.5 | 96 / 79 | 0.2 / 0.7 | 9 / 124 | 4 | 27.5/0/0.5 |
| 0.67 | A | 90 / 89 | 2 / 12 | 96 / 94 | 0.2 / 1.3 | 9 / 122 | 4 | 28/1/0 |
| 0.67 | D | 91.1 / 94.6 (gap 8.4 / 1.9) | 6 / 2 | 97 / 92 | 0.8 / 1.1 | 9 / 123 | 4 | 28/0/0 |
| 0.5 | A | 88 / 82 | 6 / 26 | 93 / 82 | 0.8 / 1.1 | 9 / 122 | 4 | 27/1/0 |
| 0.5 | D | 95.6 / 92.7 (gap 1.3 / 1.4) | 0.5 / 3.5 | 96 / 67 | 1.0 / 1.1 | 9 / 124 | 3 | 28/1/0 |

- Real words read as "": arm D 0 | 2.5, 0 | 2, 0.5 | 2 at the three scales; arm A 5 | 15, 3.5 | 16.5, 5 | 18. Arm A's losses are real words ("Refresh", "Stop", the URL, the page title); arm D's leftovers are fragments.
- Missed text per run on smoke falls from 9.5–11.5 under A to 2.5–5.5 under D; about equal on span2.
- Repairs: 0–3 per run in both arms. Containers per record 1.45 | 1.94 in both arms at every scale. Link counts by kind are alike.
- The yardstick is wrong on frame 171, box b87 ("Overwrite? (y/n): y"): both P3 s100 repeats assign it to the browser, read it as "1.24.10" and pair it with "Kubernetes versions". Arm D gets it right in all six span2 runs and is penalised for it.

## By eye

**The edited line on frame 155** (the truth is a bare `a`). At 1.0 and 0.67 all four arm D readings are good (arm A at 0.67 had three good and one `az login`). At 0.5 all four lose the `a`, as under arm A.

**Span2 command lines** (frames 161, 166, 172, 175; eight readings per scale). At 1.0 and 0.67 all eight are faithful under both arms. At 0.5 arm D has five faithful, two readings of another line, and one invention (`kubectl config use-context`; "use-context" is nowhere on screen); arm A at 0.5 has six faithful, two empty and no invention. Arm D more often gives only the typed part and leaves out the grey suggestion (`az ak_` on frame 165, `kubectl get` on frame 179).

**Tooltips.** Frame 151's is its own popup and read correctly in all six arm D runs. Frame 149's in five of six; in smoke-d050-r2 its box is put in the browser and read as `Home`, the text of the next id in the list, about 1200 px away.

**Descriptions** on frames 150, 151 and 155 are accurate at all three scales, with small slips. 11 of the 264 arm D descriptions mention the mechanism ("the box in question", "the target is…", once a box id, once "the reading list"), against 1 of 264 under arm A at the same scales. Nine of the 11 are on frames whose only target is an icon.

## Id confusion: whole-frame scrambles

This was the main risk of arm D. It is rare per reading, it comes as whole-frame scrambles, and it does not grow as the scale falls. Five of 264 call records, in 4 of the 12 runs, are scrambled. All five are dense records (48–68 targets): 5 of the 54 records with more than 20 targets.

- smoke-d100-r1 frame 145: at least 14 of 68 readings are shifted onto another id (a column shifted down by one through nine boxes; the left navigation shifted by one: Delete reads "Cancel", Search reads "Delete"). The OCR boxes are right. Links unaffected.
- smoke-d067-r1 frame 145: at least 21 of 68 readings belong to other boxes; three header and value swaps; seven wrong pairs up to 276 px apart.
- span2-d100-r2 frame 183: the readings are right, but 11 of 18 pairs join a key to another row's value ("OS disk ⇒ Disabled"). Many values on this page are "-" and get no box; the model seems to pair keys and values by list order.
- span2-d050-r1 frame 183: all 18 pairs are wrong, up to 1525 px apart.
- span2-d050-r1 frame 182: two pairs and three readings shifted by one row.

| measure | arm D, per run | arm A, per run |
|---|---|---|
| pairs with no shared row | 0 in nine runs, then 3, 10, 21 (one each at 0.67, 1.0, 0.5) | 0–2 |
| readings on the wrong box, smoke (r1, r2 at 1.0 / 0.67 / 0.5) | 12, 0 / 11, 1 / 0, 1 | 0, 0 / 4, 0 / 3, 9 |
| readings on the wrong box, span2 | 4, 1 / 2, 2 / 4, 3 | 5, 5 / 17, 7 / 26, 26 |

Outside the scrambled frames arm D has 0–2 wrong-box readings per run. Arm A's wrong-box readings grow steadily as the scale falls (icon boxes read as the label beside them; column shifts in the `kubectl` table). Arm A never scrambles a whole frame at 1.0. Nothing in the manifest flags a pair scramble: span2-d050-r1 has 0 repairs and `mark_match` 92.0.

Arm D also mis-assigns window-edge glyphs: PowerShell's □ and × on frame 185 go to the browser in four of six span2 runs (arm A at 1.0 gets them right), and the clipped browser text beside the terminal goes to PowerShell in seven of twelve runs (arm A only at 0.5).

## Summary by scale

- **1.0:** cost equal. Second readings, the frame 155 line, command lines, containers equal. Arm D is better on empty readings, missed text and tooltips. Arm D is worse on scrambles: one text scramble and one pair scramble in four runs, none under arm A.
- **0.67:** arm D costs 34 % more than arm A. It reads better (span2 `mark_match` +5.5, wrong-box readings 2 against 12) and has one scramble in four runs.
- **0.5:** arm D costs 25–31 % more. It reads better on the measures, equally loses the frame 155 line, invents one command, and has the worst pair scramble.
- Arm D at 0.67 holds what arm A holds at 1.0 except on cost (dearer than A at 1.0) and on freedom from scrambles. So arm D does not open the way to a cheaper scale.
