# P7: Sonnet 5 on `annotate` against Opus 5

Matrix `evals/p7.toml`. `claude-sonnet-5` in place of `claude-opus-5`; everything else is the working default (incremental, transcribing, tagged overlay, scale 1.0, prompt `annotate-v4`, effort low). Stages `read`, `track`, `annotate`; spans smoke (frames 145–155) and span2 (155–187); two cold repeats: 4 runs, 88 calls, 0 errors, schema failures, retries, refusals or truncations. Spend $2.73. The comparison set is P3's Opus runs at scale 1.0 (`../p3/report.md`), same spans, same targets, same prompt. Numbers were computed from the run directories (`runs/eval/p7/`, `runs/eval/p3/`, not committed) by the scripts in `scripts/`. Nothing here comes from a prototype. Haiku 4.5 is not in this phase: the Models API says it does not take the `effort` parameter the pipeline sends.

Pairs of values are smoke | span2.

## Cost (mean of two repeats)

| measure | Sonnet 5 | Opus 5 | Sonnet / Opus |
|---|---|---|---|
| input tokens per call, cached prompt included | 9391 / 9429 | 9391 / 9429 | 1.00 / 1.00 |
| output tokens per call | 2496 / 1554 | 1747 / 1216 | 1.43 / 1.28 |
| $ per frame | .0403 / .0279 | .0782 / .0614 | 0.52 / 0.45 |
| $ per 221-frame video | 8.90 / 6.17 | 17.29 / 13.57 | 0.52 / 0.45 |

- Input token counts are identical under both models on all 44 frames; the prompt cache engaged the same way.
- Billed output is 43 % | 28 % higher while the stored answer is slightly smaller, so the excess is outside the answer. It sits in the dense records (frame 147; frames 183, 185, 187), which are the ones Sonnet then gets wrong. This is why the price ratio is about a half and not the list ratio of 0.40.
- Cost noise between the two Sonnet repeats: $0.0031 | $0.0007 per frame.

## Quality (yardstick: both P3 Opus runs at 1.0, averaged)

| row | mark_match % | readings on wrong box | reference pairs reproduced % | container differs, % of targets | terminal boxes in a terminal WINDOW (of 9 / of 125) | tooltips as own popup (of 4) | frame 150 pairs correct / wrong / missing |
|---|---|---|---|---|---|---|---|
| Opus against Opus (noise) | 94 / 93 (gap 1.5 / 1.1) | 0 / 5 | 95 / 94 | 0.4 / 0.2 | 9 / 125 | 3 | 28/0/0 |
| Sonnet 5 | 87.7 / 80.5 (gap 2.4 / 2.7) | 4 / 34.5 | 84 / 72 | 2.2 / 16.8 | 4 / 56 | 4 | 24/1/4 in both repeats |

- Run links reproduced: 53 % | 20 %, against 94 | 100 between the two Opus repeats. Repairs per run 7.5 | 3.5 against 2.5 | 1.5. Real words read as "": 9 | 21 against 5 | 15. Missed text listed: fewer (lower recall, not better coverage).
- **Containers.** Sonnet finds the same set of containers with the same membership (difference 0.2 | 0.45 % of targets when the kind is ignored). The whole 16.8 % is one thing: Sonnet calls the PowerShell window a popup owned by the browser in 17 of 23 span2 records with terminal targets, on different frames in each repeat. Opus never does. The prompt sentence "Anything drawn over a window is its own popup" reads that way literally.
- **Scrambles.** No whole-frame scramble of arm D's kind (P5). The damage is regional and sits in the dense records: in 3 and 4 of the 6 dense span2 records three or more readings belong to another box, against 0 for Opus. The `kubectl get nodes` table on frames 180, 185 and 187 has headers and row values permuted in both repeats (12 of 35 readings wrong on frame 187 in one). Wrong pairs are mostly key-to-key joins across two columns, up to 765 px apart; 3 | 5–7 pairs per run appear in neither Opus run.
- Frame 171, box b87 ("Overwrite? (y/n): y"): Sonnet makes the same error as both Opus runs (puts it in the browser, reads it as the version number beside its tag). Arm D (P5) got it right in six of six. All four overlay runs at 1.0, across two models, get it wrong: this points at where the tag sits, not at the model.

## By eye

- **The edited line on frame 155** (truth: a bare `a`): all four Sonnet readings are `PS C:\Users\msadmin> a_ login`. Good: the `a` is kept and the grey `z` is not absorbed.
- **Span2 command lines** (frames 161, 166, 172, 175): all eight readings are faithful to what is displayed and no command is invented. Sonnet fills in the grey character under the cursor where Opus leaves it out (`kubectl` on frame 172).
- **Habits Opus does not have:** it completes characters hidden by the pointer (`891c` where Opus writes `8?1c` as the prompt directs), adds `...` to strings clipped by a window edge, drops the leading `:` of values, and reads "Overwrite? (y/n): Y" as `Y`.
- **Tooltips:** 4 of 4 as their own popups, read correctly.
- **Descriptions:** the same length as Opus's, vaguer, with three factual errors on frame 151 across the two repeats. On the 10 live-line frames of span2, Opus's description says the grey text is a suggestion on 9 and 9; Sonnet's on 0 and 1: it says the whole suggested command is "being typed". 4 of 88 descriptions mention a box id (Opus 1 of 88), all on records whose only target is an icon.

## Summary

Sonnet 5 costs about half of Opus 5 per frame and is worse, far outside the repeat noise, on second readings, wrong-box readings, pairs, runs, the kind of the terminal container, dense tables and descriptions. It equals Opus on the frame 155 line, the four command lines, tooltips, container membership and errors. On the measures, Sonnet at scale 1.0 sits near Opus at scale 0.5 (`mark_match` 87.7 | 80.5 against 88 | 82; wrong-box readings 4 | 34.5 against 6 | 26) at about two thirds of that price, except that Sonnet keeps the live lines Opus at 0.5 loses.
