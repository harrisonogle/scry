# P10 / P10full analysis (shepherd notes, 2026-09-21 ~18:50)

Sources: runs/eval/p10 (24 runs, all done, commit daa16a3, clean), runs/eval/p10full (2 sync done at c0a0f16, 2 batch in flight).
Scripts here: cost.py (cost.out), qual.py (qual-smoke.out, qual-span2.out), rects.py (rects-p10.out). Generated reports:
.claude/worktrees/p10full/docs/results/p10/report.md and .../p10full/report.md (written from the worktree; untracked there).

## Short spans, cost (mean of 2 repeats; smoke | span2; calls 11 | 33, targets 255 | 425, 0 errors, 0 cache hits)
| ref | scale | in tok/call | out tok/call | $/frame | $/video | vs ids100 same phase | vs P3 s100 (.0782 | .0614) |
| coords | 1.0  | 7.2k | 7.3k | 1603 | 976 | .0748 | .0462 | 16.54 | 10.20 | +31% | -10% | -4% | -25% |
| coords | 0.67 | 5.7k | 5.8k | 1831 | 1182 | .0732 | .0440 | 16.19 | 9.73 | +28% | -14% | -6% | -28% |
| coords | 0.5  | 5.2k | 5.3k | 1632 | 1102 | .0658 | .0395 | 14.54 | 8.74 | +15% | -23% | -16% | -36% |
| ids | 1.0  | 8.8k | 8.9k | 1061 | 742 | .0570 | .0514 | 12.61 | 11.35 | 0 | 0 | -27% | -16% |
| ids | 0.67 | 5.8k | 5.9k | 1018 | 768 | .0410 | .0350 | 9.07 | 7.73 | -28% | -32% | -48% | -43% |
| ids | 0.5  | 4.9k | 4.9k | 1254 | 829 | .0483 | .0315 | 10.68 | 6.97 | -15% | -39% | -38% | -49% |
Cache caveat: every smoke coords run (and ids050-r2, ids100 span2-r1) paid cache CREATION on all 11 calls (concurrency 8, cold prompt):
2355 tok/call at 1.25x input price instead of 0.1x. Warm-equivalent $/frame (creation repriced as read): coords .0613/.0597/.0523 smoke,
.0462/.0440/.0395 span2; ids .0570/.0410/.0420 smoke, .0493/.0350/.0315 span2. Warm: coords vs ids at same scale = +7%/+46%/+25% smoke,
-6%/+26%/+25% span2. Coords at 0.5 vs ids at 1.0 warm: -8% | -20%. Coords output tokens are 1.3-1.8x ids (4 numbers per box reference).
Repeat noise $/frame: coords .0025/.0058/.0083 | .0004/.0001/.0033; ids .0001/.0019/.0128 | .0043/.0005/.0018.

## Short spans, quality (yardstick: both ids100 runs of P10; first row = ids100 vs the other ids100)
| ref/scale | pairs repro % | cont differs % | term boxes (of 9 | of 126) | tooltips own popup (of 4, 2 runs) | f150 correct/wrong/missing | links run/pair/rec | repairs (kinds) | cont/rec |
| ids100 (noise) | 96 | 89 | 0.0 | 0.2 | 9 | 126 | 4 | 28/1/0 | 8.5/39.5/6 | 6.5/46/4 | 0 | 0.5 (link_unknown_box) | 1.45 | 1.76 |
| coords100 | 93.7 | 88.6 | 0.2 | 0.2 | 9 | 126 | 4 | 27/1/1 | 8.5/40/6 | 4.5/43/4 | 2 (link_malformed 1.5, rect_unplaced .5) | 1 (link_malformed .5, second_assignment .5) | 1.45 | 1.94 |
| ids067 | 92.4 | 90.7 | 0.0 | 1.5 | 9 | 122.5 | 4 | 27.5/1/0.5 | 9.5/39/6 | 6/51/4 | 0 | 0.5 (already_linked) | 1.45 | 1.76 |
| coords067 | 89.9 | 79.4 | 5.5 (r2 10.6) | 0.9 | 7 (r2 5/9, 23 false) | 124.5 | 4 | 26/2/2 | 11/41.5/6 | 6.5/45/4.5 | 0 | 1 (link_malformed) | 1.45 | 1.94 |
| ids050 | 91.2 | 79.3 | 0.8 | 0.7 | 9 | 124 | 3 (r2 f151 in terminal) | 27/1.5/0.5 (+1 partial) | 7/42.5/6 | 12/46.5/4.5 | 0 | 0 | 1.45 | 1.76 |
| coords050 | 93.7 | 73.9 | 3.4 (r2 5.5) | 1.4 | 7 (r2 5/9, 6 false) | 122.5 | 2 (f149 in browser both runs) | 28/2.5/0 | 9.5/43/6 | 6.5/42.5/4.5 | 1.5 (rect_unplaced .5, malformed .5, already_linked .5) | 0 | 1.40 | 1.94 |
- Runs reproduced % (ids100 refs): coords lower on span2 at every scale (coords100 60/37.5, 80/50 vs ids noise 62.5/100); small counts (5-8 runs).
- Whole-frame scrambles (P5 form; no readings, so links and containers): coords: smoke-coords067-r2 f147 (22 browser boxes given to the
  PowerShell window, 4 terminal boxes to the browser, 4 wrong pairs up to 624 px apart) and smoke-coords050-r2 f147 (5 browser boxes to
  PowerShell, 4 terminal boxes to the browser). Rectangles were echoed exactly; the model mislocated the small PowerShell strip (657-1668 x
  324-370) without an overlay. ids: no container scramble in any run. Off-row pairs (dy>12) per run: coords 0,0 | 0,0 ; 0,1 | 1,1 ; 2,2 | 1,2;
  ids 0,0 | 0,2 ; 0,0 | 0,0 ; 1,0 | 3,1. Pairs in neither ids100 ref with gap>150px: coords 0,0|1,0; 0,4|2,4; 1,1|1,2; ids 0,0|0,0; 0,0|2,3; 3,2|3,1.
- Rectangle echo: 5,862 rectangles in the 12 coords runs; 5,856 exact (99.9%), 3 by overlap (IoU .99, .94, .99 = 1-2 px off on x0; one IoU .20
  on span2-coords100-r1 f175 pair, snapped to '"type": "user"'), 0 nearest, 2 dropped (rect_unplaced): both an invented 7x17 rect at
  [1418,621,1425,638] on f148 (smoke-coords100-r2, smoke-coords050-r2), a thing with no box. 0 malformed rects. label_clashes 0 (no overlay).
- 0-container records: ids100/ids067 span2 have 3 (frames 162,168,176: zero targets, containers omitted); coords lists containers anyway -> 1.94 vs 1.76.
- Descriptions naming the mechanism ("the target is the small icon..."): coords 1,0|4,3; 0,1|3,3; 0,0|3,0; ids 0,0|1,0; 0,0|1,1; 1,0|2,2 (pattern loose).

## Whole video (sync runs; batch in flight)
| run | $ annotate | $ interpret | $ summarize | $ video | $/frame | $/question | questions | commands found/exact.ocr/submitted/false run |
| full-coords050-sync-r1 | 7.43 | 4.93 | 1.05 | 13.41 | .0607 | .2696 | 27/27 | 7/7, 7/7, 6/7, 0/5 |
| full-coords067-sync-r1 | 8.19 | 4.70 | 0.95 | 13.83 | .0626 | .2579 | 27/27 | 7/7, 7/7, 6/7, 0/5 |
| P4 inc-transcribing ids 1.0 (mean of 2) | 12.22 | 4.69 | 0.94 | 17.85 | .0808 | .2626 | 27/27 | 7/7, 7/7, 7/7, 0/5 |
| P4 none | - | 3.80 | 0.81 | 4.62 | .0209 | .2162 | 27/27 | 7/7, 7/7, 7/7, 0/5 |
- Judge: $0.52 for the two sync runs; 0 failed rubric lines, so nothing to classify. Tools per run: search 78/80, get_frame 21/22, get_transitions 8/9, get_node 9/6; 3.3 turns mean.
- Submitted 6/7: entry 3 `az aks get-Credentials`; both interpreters lower-cased it at submission (T169: "the actual command is lowercase"), P4 r1 kept the capital. Interpreter case noise, not a label.
- Wall: pipeline 479 s / 500 s (P4 1857 s) but OCR was imported and questions ran concurrently (63 s for 27 vs 610 s): not comparable.
- Label dependence of answers: not established in the time; the answer records hold tool names and result counts only.
- Span2 pair losses vs ids100-r1 (47 ref pairs, noise 6): coords100-r1 5, ids067-r1 3, coords067 10/9, ids050-r1 10, coords050-r2 13; concentrated on
  the property pages f182/f183 (where P5 found pair scrambles) and f155.
