# Review: `docs/superpowers/plans/2026-09-13-visual-transcript-pipeline.md` (fresh reviewer)

Method: every code block of Tasks 1–20 was extracted verbatim into a throwaway uv project (Python 3.14.6; probe2's lockfile: anthropic 1.5.0, av 18.1.0, numpy 2.5.3, scipy 1.18.1, pydantic 2.13.5, rapidfuzz 3.14.6, sqlite-vec 0.1.9, typer 0.27.2, Pillow 12.3.0, SQLite 3.53.4) and `uv run pytest` was run per task. **15 of the plan's 69 tests fail as written** (10 distinct causes). With the fixes below applied, all 69 pass. No model API was called.

## Blockers (a test cannot pass as written, or the product is wrong on a real run)

**B1 — Task 3 `src/vt/decode.py`: container duration is multiplied instead of divided.** In PyAV 18 `av.time_base` is the int `1000000` (AV_TIME_BASE), so `float(c.duration * av.time_base)` yields 4e11 for a 0.4 s clip; `test_decode` fails and every run's last `t_end` is garbage. Replace with `duration = float(c.duration / av.time_base)`.

**B2 — Task 5 `tests/test_settle.py`: the two max-hold fixtures produce bar-shaped diffs.** `g[30:50, x:x + 20]` swept 1 px/frame changes two 1×20 strips per frame; §7.2's bar rule (w ≤ 3, 8 ≤ h ≤ 30) excludes them, so the machine sees no motion: `test_max_hold_during_continuous_motion_then_settle` finds 0 unsettled emissions and `test_max_hold_frame_that_is_the_end_state_is_upgraded` gets `t_settled == 1.0`. The Step-4 hint ("adjust the test's tolerance, not the machine") points the executor at the wrong thing. Fix the fixtures: `g[5:55, x:x + 20] = 255` and `g[5:55, 10 + i:30 + i] = 255` (block taller than `bar_max_height`); both then pass unchanged code. Side note for §7.7: slow horizontal motion of anything ≤ 30 px tall is invisible to the trigger.

**B3 — Task 5 `src/vt/settle.py` + `src/vt/detect.py`: block-cursor test emits 3 states, not 2, and the design's own pseudo-code does the same.** With S = 0.4 s and a 0.5 s blink half-period, the cursor-OFF frame is still for S and passes the novelty test *before* the blinker is confirmed at its second recurrence (t = 1.5 s), so "glyph, cursor off" is emitted as a second settled state. §7.5's "only the emission is delayed" holds only when the half-period is shorter than S; real cursors blink at ~0.53 s, so on a terminal video every keystroke pause yields one or two spurious frames. The Step-4 hint about `_last_real_motion` does not touch this. Verified fix (all 10 settle tests pass): exclude *pending* candidates from the novelty test only:
```python
# detect.py, BlinkTracker
def is_pending_bbox(self, bbox: BBox) -> bool:
    """Tracked, toggled at least once at blink cadence, not yet confirmed."""
    c = self._match(bbox)
    return c is not None and not c.confirmed and len(c.times) >= 2
# settle.py, _novel
active = [c for c in comps if not is_bar(c, self.d) and not self.churn.excludes(c)
          and not self.blink.is_blinker_bbox(c.bbox) and not self.blink.is_pending_bbox(c.bbox)]
```
A pending candidate that never confirms is a ≤ 12×32 px toggle, which §7.7 already classes as an accepted false negative. Amend §7.5 and the ledger.

**B4 — Task 10 `src/vt/perceive.py` `repair`: test fails and OCR lines vanish from the frame.** A row emptied by the duplicate/unknown filter stays as `[]`, the length mismatch then truncates the *last* row, and its marks remain in `seen`, so `l3` ends in no region and not in `unassigned_line_ids` — `test_repair_missing_duplicate_unknown_and_lengths` gets `r2.rows == [[]]`, and on real output a line silently disappears from `frames.jsonl` (breaks §8.3's "every ID exactly once"). Verified fix:
```python
            if row and not kept:  # every mark was unknown or already placed: the row vanishes
                continue
            new_rows.append(kept)
        r.rows = new_rows
        if len(r.vlm_lines) != len(r.rows):
            repairs += 1
            n = min(len(r.vlm_lines), len(r.rows))
            for row in r.rows[n:]:
                seen.difference_update(row)  # truncated rows' marks fall through to unassigned_line_ids
            r.rows, r.vlm_lines = r.rows[:n], r.vlm_lines[:n]
```

**B5 — Task 11 `src/vt/merge.py` `caret_region` vs Task 5/6: caret coordinate convention mismatch.** Stage 1 writes `caret` as the blinker's `(x0, y0, x1, y1)` (`Candidate.bbox`, type `BBox`), but `caret_region` computes `caret[0] + caret[2] / 2` (`[x, y, w, h]`) and the test fixtures are `(318, 41, 2, 18)`. On a real run the caret centre lands half a screen away and the §9.4 caret signal attributes focus to the wrong window or none. (The design is inconsistent with itself: §7.5/§10.1 show `[x,y,w,h]`, §10.5 says all stored boxes are `[x0,y0,x1,y1]`.) Keep §10.5: `cx, cy = (caret[0] + caret[2]) / 2, (caret[1] + caret[3]) / 2`; fixtures → `(318, 41, 320, 59)`, `(20, 90, 22, 108)`, `(900, 900, 902, 918)`; fix §7.5/§10.1.

**B6 — Task 11 `tests/test_merge.py` / `merge.py`: three of five tests fail as written.**
(a) `count(True) == 2`: the duplicate `l1` is dropped by `m not in seen` before the row is built, so only `l4` is `row_rejected`; expect `== 1` (Stage 2c's repair removes duplicates anyway).
(b) `test_layout_conf…`: the terminal fixture has bbox `(12, 40, 640, 300)` with two 18-px rows, so §9.3's coverage rule fires (36/260 < 0.3 → 0.75; `>= 0.9` fails), and `l7` (x 300–500) only touches `l3` (x 12–300) — zero horizontal overlap, no interleave penalty (`<= 0.7` fails). Use the text extent and a real overlap: `term` bbox `(12, 40, 540, 78)`; `other` bbox `(250, 40, 500, 78)` with `l7` bbox `(250, 42, 500, 58)`.
(c) `combine_focus("r1", "r2", "r2", 0.8)` returns 0.9; the test and §9.4's "caret and retrospective disagree → retrospective, 0.6" want 0.6, and the branch that would return it is unreachable. Replace:
```python
def combine_focus(caret_r, retro_r, vlm_r, vlm_conf):
    computed = retro_r or caret_r
    if computed:
        disagree = bool(caret_r and retro_r and caret_r != retro_r)
        signals = [s for s, v in (("caret", caret_r), ("retro", retro_r)) if v == computed]
        if vlm_r is None:
            return computed, (0.6 if disagree else 0.7), signals
        if vlm_r == computed:
            return computed, (0.6 if disagree else 0.9), signals + ["vlm"]
        return computed, 0.6, signals + [f"vlm:{vlm_r}@0.3"]
    if vlm_r:
        return vlm_r, 0.5, ["vlm"]
    return None, None, []
```

**B7 — Task 12 `src/vt/correspond.py`: §11.1's Jaccard fails the plan's own growth test.** A terminal growing from 1 to 31 lines with a renamed region scores 0.5·(1/31) + 0.3·0.03 + 0.1 = 0.13 < 0.3, so it becomes `disappeared` + `appeared` and Stage 5 loses the computed diff — the exact failure §11.1 claims revision 3 fixed (Jaccard collapses on growth just like IoU). `test_correspondence_by_text_survives_renaming_and_growth` fails. Verified fix: overlap coefficient — `j = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0`; amend §11.1/§16 to `J = |A∩B| / min(|A|,|B|)`.

**B8 — Task 7 `src/vt/stage2a.py` `is_confusable`: `"naïve café"` is flagged.** `ï` is a non-ASCII letter inside an ASCII token, so the test's third assertion fails. Count only non-Latin letters:
```python
has_foreign = any((not ch.isascii()) and unicodedata.category(ch).startswith("L")
                  and not unicodedata.name(ch, "").startswith("LATIN") for ch in tok)
```

**B9 — Task 7 `tests/test_vision.py`: exact-list assertion cannot pass on this machine.** On macOS 26.3 Vision returns three observations for the two rendered lines — `PS C:\src> git status`, `az aks create -resource-group rg-demo --name`, `aks-demo-01` — i.e. it split the long line and read `--` as `-`. Assert line 0 exactly and the rest by content:
```python
assert lines[0].text == "PS C:\\src> git status"
joined = " ".join(l.text for l in lines[1:])
assert "rg-demo" in joined and "aks-demo-01" in joined
```
The `--`→`-` misread matters downstream (M6).

**B10 — Task 18 `tests/test_diagnostics.py`: fixture lacks `ocr` keys.** `summarize` treats `l.get("ocr") is None` as VLM-only, so the fixture gives `vlm_only_fraction == 1.0`, not 0.25. Use what `diagnostics()` actually emits: `{"agree": True, "ocr": "a"}, {"agree": None, "ocr": None}, {"agree": False, "ocr": "b"}` and `{"agree": True, "ocr": "c"}`.

**B11 — Task 19 `tests/test_batch.py`: the SDK's `transform_schema` does not make defaulted fields required.** anthropic 1.5.0 leaves `b: str | None = None` out of `required` (default noted in the description), so `set(inner["required"]) == {"a", "b"}` fails. Expect `{"a"}` — the batch schema must equal what `messages.parse` sends or the two modes diverge — and make `_local_strict` mirror the SDK (do not add defaulted properties to `required`) or delete it (anthropic is a hard dependency).

## Major

**M1 — Task 9 `src/vt/providers/anthropic_.py`: transient API failures are cached forever.** `complete()` writes every result to the cache, including `api: RateLimitError…` / connection errors (verified with a fake client raising once: the re-run returned the cached error and made zero calls). A blip becomes a permanent `error` on that frame/transition, and R6's "re-run makes no API calls" becomes "re-run never repairs". Cache only terminal outcomes:
```python
        if r.error is None or r.error == "refusal" or r.error.startswith("schema"):
            self.cache.put(key, {...}, {...})
        return r
```

**M2 — Task 10/11: a VLM parent cycle crashes Stage 3.** `repair` only nulls parents naming unknown regions; `r1.parent="r2", r2.parent="r1"` (or `parent == id`) makes `region_bbox` recurse without bound (verified: `RecursionError` in `merge_frame`) and `_root` loop forever. One bad frame aborts the stage. Add to `repair` after the parent check:
```python
    by_id = {r.id: r for r in out.regions}
    for r in out.regions:
        seen_ids, p = {r.id}, r.parent
        while p is not None and p in by_id and p not in seen_ids:
            seen_ids.add(p); p = by_id[p].parent
        if p is not None and p in seen_ids:   # closes a cycle
            r.parent = None; repairs += 1
```

**M3 — Task 15 `src/vt/hierarchy.py` `build_level`: the "re-prompt once" is a cache no-op.** The retry calls `_boundaries` with identical `input_hashes`, hits the entry the first call just wrote, and returns the same failure; the fallback then always fires. Vary the request: append `"\n\n(Retry: the previous answer contained no valid start ids.)"` to `text` on the retry, or pass `"retry1"` into `input_hashes`.

**M4 — Task 13 `src/vt/coalesce.py` `_build`: transient info is dropped inside runs.** A `transient_merged` member of a typed/output run comes out as `kind="coalesced", transient=None`, so Stage 5 never receives the transient frame for coalesced runs, contrary to §11.4 ("can be a member of a typed or output run"). In `_build`: `t.transient = next((m.transient for m in members if m.transient), None)`.

**M5 — Task 10/14 `perceive.py` / `interpret.py`: unbounded fan-out materialises every image payload at once.** `asyncio.gather(*(one(...) …))` starts all coroutines; each runs `build_blocks` (two base64 PNGs ≈ 1 MB) before blocking on the provider's semaphore, so ~300 frames ≈ 0.5 GB sit in memory (more for Stage 5's three images). Bound the fan-out: `sem = asyncio.Semaphore(cfg.model.concurrency * 2)` and `async with sem:` around the body of `one()`.

**M6 — Task 16 `src/vt/index.py` `extract_nodes`: disagreeing lines index only the OCR reading.** `fused` is the OCR text when `agree` is false, and Vision reads `--resource-group` as `-resource-group` (B9), so the §14.2 showcase query `"--resource-group"` misses the line whenever OCR and VLM disagreed — R1 defeated at query time on the most common command misread. Index both readings: `text = "\n".join(l.fused for l in r.lines if l.fused) + "".join(f"\n{l.vlm}" for l in r.lines if l.agree is False and l.vlm)` (payload already carries both for the agent's both-readings rule).

## Minor

**m1 — Task 9/§20.7: Stage 5/6 system prompts are below Opus 5's 512-token cacheable minimum** (~150–250 tokens), so `cache_control` on them is silently ignored; the design says to pad with the §15 worked example. Add the worked example to `prompts/stage5.py` and `stage6.py`, or drop the marker there.

**m2 — Task 18 `cli.py` `run` imports `vt.outline`, which Task 20 creates**, so `vt run` raises `ImportError` between Tasks 18 and 20. Import it under `if "outline" in wanted:` or move Task 20 ahead of Task 18.

**m3 — Task 13 `retrospective_focus`:** omits §9.4's "no `focused_region` change" guard; never recovers the VLM's answer when Stage 3 recorded it as `vlm:rX@0.3` (`vlm_r` is dead). Parse it: `vlm_region = next((s[4:].split("@")[0] for s in f.focused_signals if s.startswith("vlm:")), f.focused_region if "vlm" in f.focused_signals else None)` and `continue` when `by_id[t.to_frame].focused_region != f.focused_region`.

**m4 — Task 17 `agent.py` `redecode` decodes from t = 0 on every call** (25,585 frames on the sample). Give `iter_frames` a `start: float | None` that does `c.seek(int(start / s.time_base), stream=s)` before decoding and skips frames with `t < start`.

**m5 — Task 4 `scale_params` / Task 3 half-res: not the §7.2 procedure.** Half-res thresholds a swscale-*averaged* gray (a 1-px stroke's delta halves and can fall below θpix) instead of 2×2-max-reducing `changed`; churn `min_area` becomes 160 where §16 says 100. Either implement the max-reduce on the full-res map or state in §7.2/§20.2 that half-res means "decode at half resolution" and set `min_area=100` explicitly. (§20.2 itself contradicts §7.2 here.)

**m6 — Task 16 `search`: `app` is a hard `LIKE` filter and no soft boost exists for `layout_conf < 0.5` regions** (§14.2); region/frame nodes never get `step_id`/`section_id`. Acceptable for v1 — say so in the plan or trim the §14.2 claim.

**m7 — Task 18 `diagnostics`: §18.4 asks for per-stage wall time, cache hit rate and retry counts;** only a `finished` timestamp and `cache_entries` are recorded. Time each `steps[name]()` with `perf_counter()` into `stage_done(..., seconds=…)`; count `hits`/`misses` in `AnthropicProvider.complete` and report them.

**m8 — Task 19: a request that errors twice (non-`invalid_request`) never reaches the cache**, so the final `_perceive_all` pass silently issues synchronous calls for it. Either document that fallback or write `error: "batch: …"` after the second failure.

**m9 — Task 6/16: `Run.video_id` re-parses `manifest.json` per Stage-1 record and `chapter_of` re-parses `outline.json` per call** (Stage 7 calls it once per frame and per transition). Read `video_id` once in `run_stage1`; make `load_outline` a `functools.cached_property`.

**m10 — Task 15 `_hierarchy`: if every transition is `trivial`, `ts` is empty and `propagate([])` raises `IndexError`**; the `if not run.load_transitions()` guard does not cover it. Guard on `ts`.

## Nit

**n1 — Task 2 Interfaces block** says `pair_modifies(ops, prev_y, cur_y, heights, sim_threshold)`; code and tests use `line_h`.
**n2 — Task 5 `settle.py`** hard-codes the 3.0 s history window; use `self.blink.p.confirm_window_s`.
**n3 — Task 6 Step 4 "completes in a few minutes":** measured 44 fps at 1080p full-res on synthetic frames (detection, not decode, dominates) → ~10 min for the sample. Set the expectation, or default `downsample = 2` once m5 is settled.
**n4 — Task 21 "≈45 tests":** the plan's tests as written are 69.
**n5 — Task 17 `ask`:** `stop_reason == "refusal"`/`"max_tokens"` returns an empty string; return a message, and consider the `fallbacks` parameter for Opus 5 refusals.
**n6 — Task 20:** `client.interactions.create(model=…, input=[{"type": "video", "uri": …, "processing": "agentic"}, …])` is unverified — google-genai 2.23.0 does expose `client.interactions`, but the `input` item shape was not checked; mark it as such in the plan.

## Ran

Scratch project: `/private/tmp/claude-501/…/scratchpad/planreview-fresh` (copied probe2's `pyproject.toml` + `uv.lock`, `.python-version` = 3.14, `PYTHONPATH=src`). Code blocks extracted verbatim with `scratchpad/extract_blocks.py` (matches "`path`:" headings; Task 6's unlabeled `run.py`/`stage1.py`/`cli.py` fences by position; the eleven "Add to `cli.py`:" blocks appended in plan order).

| Command | Result (as written in the plan) |
|---|---|
| `uv run pytest tests` (Tasks 1–5: test_schemas, test_textdiff, test_decode, test_detect, test_settle) | 26 passed, 4 failed: `test_iter_frames_times_and_shapes` (B1), `test_block_cursor_blink…` (B3), `test_max_hold_during_continuous_motion…` (B2), `test_max_hold_frame_that_is_the_end_state…` (B2) |
| `uv run pytest tests/test_ocr.py tests/test_vision.py` (Task 7, Apple Vision on macOS 26.3) | 1 passed, 2 failed: `test_confusable_flags_mixed_script_tokens` (B8), `test_vision_reads_terminal_text_exactly` (B9) |
| `uv run pytest tests/test_overlay.py tests/test_provider.py` (Tasks 8, 9) | 7 passed |
| `uv run pytest tests/test_perceive.py tests/test_merge.py` (Tasks 10, 11) | 2 passed, 4 failed: `test_repair_missing_duplicate_unknown_and_lengths` (B4), `test_rows_join_fragments…` (B6a), `test_layout_conf…` (B6b), `test_caret_region_and_focus_combination` (B6c; B5 latent) |
| `uv run pytest tests/test_correspond.py tests/test_diff.py` (Task 12) | 3 passed, 1 failed: `test_correspondence_by_text_survives_renaming_and_growth` (B7) |
| `uv run pytest tests/test_coalesce.py` (Task 13) | 5 passed |
| `uv run pytest tests/test_interpret.py tests/test_hierarchy.py tests/test_index.py tests/test_agent.py tests/test_outline.py` (Tasks 14–17, 20) | 12 passed |
| `uv run pytest tests/test_diagnostics.py tests/test_batch.py` (Tasks 18, 19) | 1 passed, 2 failed: `test_summarize_counts_and_cost` (B10), `test_strict_schema_requires_all_and_forbids_extras` (B11) |
| Same suite after applying B1–B11 fixes plus B3's `is_pending_bbox` and B7's overlap coefficient | **69 passed** |
| Probe: `av.time_base` in PyAV 18.1.0 | `1000000` (int) |
| Probe: `AnthropicProvider.complete` with a fake client raising `RuntimeError` once, then re-run | second call returns the cached `api:` error, 1 API call total (M1) |
| Probe: `repair` + `merge_frame` on `r1.parent="r2", r2.parent="r1"` | `RecursionError` in `region_bbox` (M2) |
| Probe: `open_db`/`index_nodes`/`search` with a 4-dim fake embedder | vec0 table with metadata columns created; `embedding MATCH ? AND k = ? AND level = ? AND video_id = ?` returns rows; RRF fuses three rankings |
| Probe: `SettleMachine(cfg, 30, (30, 100), downsample=2)` on a synthetic sequence | runs; scaled params θmin 3, θcomp 10, θcount 40, bar (2, 4–15), churn min_area 160, blink 6×16 (m5) |
| Probe: `SettleMachine.step` on 60 synthetic 1920×1080 frames | 44 fps (n3) |
| `python -m vt.cli --help`, `decode --help`, `setup` (assembled `cli.py`, 13 commands) | help renders; setup: Vision ok, FTS5 ok, sqlite-vec ok |
| `load_config(Path("vt.toml"))` with the plan's `vt.toml` | validates |
| `uv run --with google-genai python -c "…hasattr(client, 'interactions')"` | True (2.23.0) |

## Checked and found correct

- anthropic 1.5.0: `AsyncMessages.parse(model=, max_tokens=, system=, messages=, output_format=<pydantic type>, output_config={"effort": …})` exists and merges `output_format` into `output_config.format`; `ParsedMessage.parsed_output` exists; schema mismatches raise pydantic `ValidationError` (a `ValueError`); `await client.messages.batches.results(id)` returns an `AsyncJSONLDecoder` with `__aiter__`, so `async for … in await …results(…)` is right; `MessageBatchIndividualResponse.custom_id/result.type/result.message` as used; 64-hex `custom_id` is within the 64-char limit; `output_config.effort` values `low|medium|high|xhigh|max` valid; Opus 5 needs no `thinking` parameter; 512-token cacheable minimum on Opus 5 as the design states.
- PyAV: `to_ndarray(format="gray")`, `frame.reformat(width=, height=, format="gray")`, `to_image()`, `stream.thread_type = "AUTO"`, `pts × time_base`, mpeg4 encoding in `conftest.make_video` (12 frames decode with exact 1/30 s spacing).
- scipy: `binary_dilation`/`label` with the 3×3 structure, `bincount(labels[changed])`, `find_objects(tight, max_label=n)`, `binary_opening` + 9×9 dilation for churn regions.
- Task 2 Myers/`_backtrack`, `char_diff` runs, `pair_modifies`, `is_clock_change`, `lcp_len`: all 9 tests pass and the op orders match the design's examples.
- Task 4 change detection (thin strokes survive, noise removed, dilation bridges strokes, bar rule, trigger), `ChurnTracker` (unmasked ring buffer, uint16 counts, per-pixel hysteresis, warm-up, deactivation with `t_last_change`), `BlinkTracker` (IoU tracking, 2 recurrences at 0.15–0.7 s within 3 s, expiry 2 s): 7 tests pass, rules match §7.2/§7.4/§7.5/§16.
- Task 5 settle machine against §7.3 pseudo-code line by line: first-frame emit, `tStill = tPrev`, novelty vs last emitted, in-place upgrade of an unsettled last frame, max-hold only while moving, churn tick every M with `tChange = tLastEmit`, churn deactivation rule, end-of-stream flush, `t_end`/caret written at finalization, bboxes scaled back to full resolution.
- Task 6 `Run` layout/manifest/skip logic, `stage1.on_emit` swapping `em.frame` for `(n, path)` + `png_future`, PNG encode off-thread; Task 7 Vision adapter's bottom-left-origin conversion and settings; `assign_ids` reading order/`in_churn`.
- Task 8 `place_label` slot order right/left/above/below, least-overlap fallback with clash count, exact output dimensions (3 tests pass).
- Task 9 retry ladder (max_tokens → retry_max_tokens; schema → one retry with the error quoted), refusal recorded not raised, cache key = (stage, model, effort, max_tokens, prompt_version, schema_hash, input_hashes), `cache_control` on the system block (4 tests pass).
- Task 11 rows (§9.0 sanity rules), agreement incl. glyph strip, `region_bbox` recursion (absent cycles), `layout_conf` occlusion/ancestry exemptions, OCR-only fallback region `kind="unknown"`.
- Task 12 `diff_region` (`fused` texts, y-overlap/similarity pairing, `uncertain`/`in_churn` propagation), `diff_pair` (`t = (prev.t_end, cur.t_settled)`, `unsettled`, `r0`); Task 13 Rules 1/2/1b, transient detection over triples, `tag_trivial`, retrospective focus attribution (5 tests pass as written).
- Task 14 block order and `render_diff` content (both readings, grouping-uncertain note), `validate_refs`; Task 15 boundary repair, windows, overlap merging (the ≥ 25-items rule), `propagate` (4 tests pass); Task 16 FTS5 tokenchars/trigram/phrase quoting, filters inside each index, k raised to 50 under filters, RRF; Task 17 tool defs/dispatch/tool_result shapes (image blocks allowed); Task 20 `parse_outline_text`.
- Interface consistency across tasks (field names, `Correspondence.matched` triples, `Transition.t`, `DiffOp.in_churn`, `VlmProvider.complete` kwargs, overlay path `overlays/NNNNN.png` in Tasks 8/10/11, `overlay_clashes` str keys) — the only breaks found are B5 (caret) and m2 (Task 18 → Task 20 import).
- Owner's constraints: no test reads the sample video or the network; `test_vision.py` uses Apple Vision on a rendered image (local, skipped off-macOS).
