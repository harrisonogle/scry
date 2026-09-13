# Design review (fork) — docs/visual-transcript-pipeline-design.md rev 2 @ 922452d

Evidence gathered on this machine during review (probe venv, sample video): full decode = 25,585 frames, PTS never None, monotonic; Apple Vision on real 1080p frames at t=60/300/600 s: 0.22 / 0.15 / 0.16 s, 6 / 52 / 99 lines, every line confidence 1.00; Vision merged "Node pools Access Networking" into one observation and split "Basics" / "Integrations"; icons transcribed as letters ("P Search resources, services, and docs", "A AKS1-… - Microsoft x", "Learn more B'"). FTS5 `unicode61 tokenchars` and `trigram` both work on sqlite 3.53.4; sqlite-vec `vec0` works; `anthropic.messages.parse(output_format=…)` exists.

## Blocker

**B1. §7.2 + §7.4 — churn mask feeds back on itself and oscillates.** §7.2 computes `changed[p]` "for unmasked pixels" and §7.4 fills the ring buffer with those maps, so once a region is masked its pixels stop registering change, its count decays below ρ_off within W, it leaves the mask, re-registers, re-enters — period ≈ W. Also "hysteresis per component" is undefined because components are recomputed each frame. Fix: compute `changed_all` over all pixels; churn uses `changed_all`; the trigger uses `changed_all & ~mask`. Hysteresis is per pixel with a persistent mask: `mask = (mask & (count > ρ_off·n)) | (count > ρ_on·n)` where `n` = maps currently in the window (so start-up works); bboxes = components of `dilate(open(mask))`.

**B2. §7.2 / §7.5 / §17 — block and underscore cursors never settle.** Only a 1–2 px bar caret (~36 px) is below θcomp = 64. A blinking block cursor (≈9×18 = 160 px at 1080p; 36 px at half-res vs θcomp/4 = 16) triggers on every blink, so the screen never settles and every state is a 3-s max-hold tagged `settled=false`. cmd, conhost PowerShell and many terminal configs use block/underscore cursors. §17 lists "caret exclusion" but §7.2 has no mechanism. Fix: a *blink mask*, handled exactly like churn (excluded from the trigger only): a change component ≤ 12×32 px whose bbox (IoU ≥ 0.5) recurs ≥ 3 times within 3 s with 0.15–0.7 s between recurrences is added to the mask until it has not recurred for 2 s. The same tracker is the caret position for §7.5/§9.4. Add "blink component size / recurrence / expiry" rows to §16.

## Major

**M1. §12 — Stage 5 is made sequential by its own context.** "The last three transitions' `action` fields" as input means call k needs the outputs of calls k−1..k−3, contradicting §19.3 "parallelizable" and §20.7 batch mode. Fix: v1 context = outline preamble (if present) + the previous three transitions' *computed* events/diff one-liners (available before any Stage 5 call). Drop `action` carry-forward; revisit in v2.

**M2. §7.3 — max-hold fires during the settle wait and mislabels settled states.** Trace: motion 0→2.8 s, still from 2.83 s. At t=3.0: still, but `changed` is true and t−tChange ≥ M → emit `settled=false`, `tChange=3.0`. At t=3.23: t−tStill ≥ S, `trigger(f,last)` is false (identical to the 3.0 frame) → nothing emitted, `changed=false`. The state settled but is recorded unsettled with the wrong `t_settled`. Fix: guard max-hold with `tStill == ∅` (only while actually moving), and on settle confirmation, if `last.settled == false` and `!trigger(f,last)`, upgrade `last` in place: `settled=true, t_settled=tStill`.

**M3. §9.3 — `layout_conf` penalizes every foreground window; the §10.1 example contradicts the rule.** The containment test uses the other region's hull; in the example r1 (terminal, [12,40,640,300]) lies entirely inside r2's hull ([0,0,1920,1080]) → −0.6 → ≤ 0.35, yet the example shows 0.9. Fix: skip pairs related by `occludes` (either direction); penalize only *mutual* interleaving (this region has a line centre inside the other's hull AND vice versa); at most −0.3 per other region. The scatter test (Σ line areas / hull area < 0.3) fires on ordinary terminals with short and blank lines; replace with vertical coverage (Σ line heights / hull height < 0.3) or drop until calibrated.

**M4. §11.1 — cross-frame region matching by VLM-emitted names is the weakest link.** Names vary call to call ("Windows Terminal — pwsh" vs "Terminal"); on a miss every region becomes appeared/disappeared and the transition has no line ops, so Stage 5 loses the computed diff. Fix: primary signal = text overlap: Jaccard of normalized joined-line text sets ≥ 0.3 (or ≥ 0.5 of the smaller set) plus bbox IoU; names as tie-breaker only; greedy one-to-one assignment by score = 0.6·textJaccard + 0.3·IoU + 0.1·nameMatch; regions with `bbox: null` match by text only.

**M5. §8.2 — label placement occludes text in dense regions.** At an 18-px line pitch, "outside the top-left" lands on the previous line, so the fallback "inside the top-left" covers the first characters the VLM must transcribe (R1). Fix: place the label right of the box (x1+3, vertically centred, usually blank in terminals and lists), else left of x0, else inside the right end; draw on a 50 %-alpha backing; tell the VLM in §15.1 that the number sits at the end of the line and is not part of the text.

**M6. §9.2 — icon glyphs make portal lines `agree=false` wholesale.** Vision returns a letter for icons ("P Search resources…", "A AKS1-…", "Learn more B'"); the VLM will not, so every icon-prefixed nav/toolbar/link line disagrees and the coverage metric collapses on portal content. Fix: in alignment, if `norm(vlm)` equals `norm(ocr)` with one leading or trailing single-character token removed, record `agree=true`, `ocr_glyph_stripped: "P"`, and use the stripped text as the fused line. Do not strip for §11.2 diffs (the glyph is stable across frames).

**M7. §8.1 / §9.2 — Vision's confidence is uninformative.** All 157 lines across three real frames came back at 1.00. `ocr_conf` cannot drive fusion, `layout_conf`, or "low confidence" labelling. State that `agree` is the only per-line uncertainty signal with Vision and that `ocr_conf` is engine-specific and advisory.

**M8. §19.6 / §20.7 — thinking tokens are missing from the cost model.** `claude-opus-5` runs adaptive thinking when `thinking` is omitted; thinking is billed as output at $25/M, so a few thousand tokens per call can double or triple the $18 + $15 estimate. Fix: make `output_config.effort` a per-stage config parameter (Stage 2c and 5: `low`; Stage 6: `high`), say so in §19.6, and sum `usage.output_tokens` (which includes thinking) into the manifest.

**M9. §9.4 / §10.1 / §7.5 / §20.9 — three fields are written by stages that do not own `frames.jsonl`.** Retrospective `focused_region` (Stage 4b), `outline_chapter` (after optional Stage 0), and `caret` (needs the state's whole stable interval, but the record is emitted at settle) violate "each stage writes its own JSONL" and the input-hash skip rule. Fix: Stage 1 finalizes a frame's record at its `t_end` (caret from the stable interval); Stage 3 writes `merged.jsonl` without focus fields; Stage 4b writes `frames.jsonl` = merged + focus (last writer); `outline_chapter` is not stored — computed on read from `outline.json` by `t_settled` by whoever needs it.

**M10. §16 — "scale pixel counts by 4 for 1440p" is wrong.** UI elements have the same pixel size at 1440p (a 16×16 checkbox is 256 px regardless, unless DPI-scaled), which is the whole point of §7.2's absolute counts. Replace with: thresholds are absolute pixel counts at native resolution and do not change with resolution; divide areas by 4 and linear sizes by 2 when detecting at half resolution.

**M11. §10.1 "lines appear only on leaf regions" vs real groupings.** A window with a title-bar line and child panes is normal; the VLM will put `member_line_ids` on non-leaf regions. Fix: allow lines on any region; "leaf region" in §9/§11 means "region that has lines"; §9.1 bbox recursion unchanged.

**M12. §11.3 vs §10.2 — the rules do not produce the example.** Rule 1 says `typed.text = b_final` (the whole line "PS C:\src> git status") but the example shows "git status"; frame 12 already shows "gi", so the span 12→16 typed "t status"; and no rule yields one transition carrying both `typed` and `output_appended`. Fix: `typed.text` = suffix of `b_final` beyond `a_first` (normalized), store `line_after = b_final`; add Rule 4: a typed run followed immediately by one transition whose ops are inserts below the typed line (optionally plus a no-new-text modify of that line) merges into one transition with both events; state that a coalesced transition's `computed_diff` is recomputed directly between `from_frame` and `to_frame`; fix the example (`from_frame: 11` or `text: "t status"`).

## Minor

**m1. §10.2 vs §10.6 — refs format.** Example uses `"r1:l3"`; §10.6 says `"<frame>:<line>"`. A transition spans two frames, so refs must name the frame (`"16:l3"`). Add: invalid refs are dropped, `refs_invalid` count stored, no re-prompt in v1.

**m2. §10.2 — `computed_diff` keyed by `r1`** but region IDs are per frame. Key by the to-frame region ID with `from_region`; add `regions: {matched: [[from,to]], appeared: [], disappeared: []}`; specify `index` (insert → index into `cur`, delete → index into `prev`), `y` (= y0 of the new line), and `char_diff` as a list of `[op, text]`.

**m3. §13.1 — fallback depends on optional Stage 0.** If `outline.json` is absent, sections fall back to fixed windows of 5 steps. Also require boundary output IDs to exist and be in order.

**m4. §10.3 / §13.3 — `t` semantics.** "[t_settled, t_change]" of which frames is unstated. Define transition `t = [t_end(from_frame), t_settled(to_frame)]` (the action window) and step/section `t = [t[0] of first child, t[1] of last child]`.

**m5. §9.2 — short lines never align.** "OK" vs "0K" has similarity 0.5 → both retained as OCR-only and VLM-only. Add `or (len ≤ 4 and Levenshtein ≤ 1)` to the predicate.

**m6. §9.0 vs §15.1 — joined rows vs per-cell VLM entries.** After joining, a table row is one OCR line but the VLM may emit one entry per cell, so alignment fails. Add to §15.1: "text on one row (table cells, tabs, side-by-side labels) is one entry, left to right"; in alignment, try the concatenation of 2–3 consecutive VLM lines when a single one fails.

**m7. §11.3 / §11.4 — ordering unspecified.** Detect transients on single transitions first, then coalesce over the result; an unsettled intermediate frame does not break a typed run.

**m8. §9.1 / §9.3 / §11.1 — regions whose lines are all VLM-only have no boxes.** Define `bbox: null`, `layout_conf = min(conf, 0.5)`, text-only matching, skipped in geometry (avoids division by zero in §9.3).

**m9. §8.3 — validation outcomes unspecified.** Missing IDs → appended to `unassigned_line_ids`; duplicates → keep the deepest region, log; `focused_region` not an emitted ID → `null`; parse failure → one retry, then `vlm: null, error: "…"`.

**m10. §14.2 / §20.10 — FTS5 specifics (verified).** `tokenize = "unicode61 tokenchars '-_./:'"` and `trigram` both work, but with tokenchars `rg` no longer matches `rg-demo` (only `rg*` or the trigram index does), and hyphens in queries must be quoted (`"--resource-group"`; an unquoted `-` is FTS5's NOT and raises a syntax error). The agent's `search` tool should quote terms by default. Remove the [verify] tag.

**m11. §7.2 — taskbar clocks emit a frame per minute.** A changing digit (~80 px) exceeds θcomp, so a spurious settled frame and a Stage 5 call happen each minute (~14 on the sample). At Stage 4, tag ops whose only difference lies inside a `\d{1,2}:\d{2}(:\d{2})?` token as `clock`; a transition with only `clock` ops is `kind: trivial` and skips Stage 5.

**m12. §20.2 — PTS guard and the decode figure.** Guard `frame.pts is None` (use `frame.time`, else previous + 1/average_rate, and log); the sample never hits it (25,585 frames) but the guard is cheap. Decode alone runs ≈7,700 fps; the 535 fps figure is dominated by the gray conversion, so convert at half resolution in swscale (`frame.reformat(width//2, height//2, "gray")`) rather than slicing a full-res array.

**m13. §20.4 / §22 #10 — Vision is fast enough; a pool needs `spawn`.** 0.15–0.22 s per real 1080p frame with 6–99 lines, so a process pool is unlikely to be needed; if used, it must use `multiprocessing.get_context("spawn")` (forking after Objective-C initialization crashes on macOS). Record the figure as [measured] and downgrade #10.

**m14. §18 — nothing is measurable until ground truth exists.** Add a "ground-truth-free diagnostics" list the harness reports from day one: emitted-frame count and settled fraction, lines per frame, `agree=true` fraction, OCR-only and VLM-only fractions, schema/ID validation failure rate, refs validity rate, fragment stability, per-stage tokens/cost/wall time, refusal count.

**m15. §20.7 — caching and fallbacks caveats.** The minimum cacheable prefix is model-dependent (512–4096 tokens); the Stage 2 system prompt plus schema may fall below it and never cache — check `cache_read_input_tokens` and pad with the §15 worked example if needed. The `fallbacks` parameter is rejected on the Batches API; say so next to batch mode.

**m16. §18.3 (2) vs D15.** A cross-vendor VLM bake-off requires a second provider, which D15 defers; v1's bake-off is Opus 5 / Sonnet 5 / Haiku 4.5 within the Anthropic provider.

**m17. Cross-reference errors (revision 1 leftovers).** §5.2 "the harness (§12) picks it" → §18; §11.3 "must be validated (§12)" → §18; §16 "tuned on the ground-truth set (§17)" → §18.1; §0's section list omits §24.

**m18. §9.4 — missing combination cases.** Computed signal present, VLM `null` → computed, 0.7; caret and retrospective disagree → retrospective wins (exact); the caret region is a pane but `focused_region` is a window → compare at root-window level.

**m19. §6 — a pair straddling two chapters.** Use the chapter containing `t_settled` of frame b.

**m20. §7.4 — W is in seconds but the buffer is in frames.** 150 maps assumes 30 fps; state the conversion and that the 39 MB figure is for 30 fps (double at 60).

## Nit

**n1. §10.1** line records lack `merged_from` (§9.0) and `words` (§8.1 says stored); add them or state that words live only in the Stage 2a file.
**n2.** Stage output file names are never fixed (Stage 1 metadata, 2a, 2b, 2c raw). Propose `stage1.jsonl`, `ocr.jsonl`, `perception.jsonl`, `merged.jsonl`, `frames.jsonl`, `transitions.jsonl`, `steps.jsonl`, `sections.jsonl`, `video.json`, `outline.json`, `manifest.json`.
**n3. §10.1 `unassigned_lines` vs §8.3 `unassigned_line_ids`:** state that `unassigned_lines` holds full line records (they have text and boxes).
**n4. §7.1** "decodes in under a minute" is conservative (decode-only ≈ 3.3 s for the sample; gray conversion dominates).

## Checked and found correct (no need to re-verify)

- §5.2/§5.3 Claude image facts and token arithmetic (69×39 = 2,691; 92×52 = 4,784 = the cap; 4K → 2576×1449) match the vision docs.
- §19.6 arithmetic is right for its inputs (only the thinking-token omission, M8).
- PyAV: `frame.pts` present and strictly increasing for all 25,585 sample frames; `pts × time_base` is valid; `thread_type = "AUTO"` works.
- §20.4 PyObjC calls run as written; `boundingBoxForRange_error_` returns word boxes; the §8.1 coordinate conversion is correct (checked against visible layout, e.g. "Microsoft Azure" → [64,16,181,33]).
- §14.2/§20.10 FTS5 `tokenchars` + `trigram` syntax and sqlite-vec `vec0` create/query work on sqlite 3.53.4 (with m10's quoting caveat).
- `anthropic` 1.5.0 `messages.parse` accepts `output_format` and `output_config`.
- §9.0's premise is real (Vision merged three tab labels into one observation and split neighbours); §7.3's `t_settled` correction is right as far as it goes; §7.7 loss analysis; §11.2 raw-op retention; §11.4 hold computation `t_change_{i+1} − t_settled_i`; §13.3 propagation; RRF choice; §19.6/§19.7/§24 numbering is consistent.
