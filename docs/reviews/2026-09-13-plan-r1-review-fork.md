# Plan review (fork) — docs/superpowers/plans/2026-09-13-visual-transcript-pipeline.md @ 9f204a6 vs design r3 @ eb194ec

Method: extracted every code block of the plan verbatim into a throwaway uv project (`scratchpad/planreview-fork/`, Python 3.14.6, all deps from the probe lockfile), ran the full test suite, root-caused every failure, applied minimal fixes in the throwaway copy until everything passed (69 tests), then read the rest against the design. No repo file was touched; no model API was called.

Initial run of the plan's code as written: **13 of 69 tests fail** (test_decode 1, test_settle 3, test_merge 3, test_correspond 1, test_perceive 1, test_ocr 1, test_diagnostics 1, test_batch 1, test_vision 1). All other tasks' tests (textdiff, detect, overlay, provider, diff, coalesce, interpret, hierarchy, index, agent, outline) pass as written. Every fix below was verified by re-running.

## Blocker

**B1. Task 5 `settle.py` / design §7.3–§7.5 — a blinking block cursor produces spurious emissions before the blink tracker confirms it, and the emission that follows the first toggle gets a wrong `t_settled`.** `test_block_cursor_blink_is_learned_and_does_not_prevent_settling` fails (3 emissions, then `t_settled` = 1.0 instead of 0.5). Cause: the design assumes toggles keep the screen "moving" until confirmation, but a cursor's half-period (0.5 s) exceeds S (0.4 s), so the machine settles between toggles and each toggle is "novel" against `last`. The corpus's terminal is PowerShell with a block cursor, so this hits the sample video. Fix (two parts, both verified):
(a) bounded deferral of novelty decisions that rest only on unconfirmed blink candidates — `detect.py` add to `BlinkTracker`:
```python
    def candidate_last_seen(self, bbox: BBox) -> float | None:
        c = self._match(bbox)
        return c.times[-1] if c is not None else None
```
`settle.py` replace `_novel` and its call sites:
```python
    def _novel(self, gray: np.ndarray, t: float) -> tuple[bool, bool]:
        """(novel, deferred): deferred while every novelty component sits at an unconfirmed blink-candidate
        position that could still recur (within one maximum blink period of its last occurrence)."""
        comps = components(change_map(self.last_gray, gray, self.d.theta_pix), self.d.theta_min)
        active = [c for c in comps if not is_bar(c, self.d) and not self.churn.excludes(c) and not self.blink.is_blinker_bbox(c.bbox)]
        if not trigger(active, self.d):
            return False, False
        def pending(c: Component) -> bool:
            seen = self.blink.candidate_last_seen(c.bbox)
            return seen is not None and t - seen <= self.blink.p.max_period_s
        return True, all(pending(c) for c in active)
```
```python
            if t - self.t_still >= self.S:
                novel, deferred = self._novel(gray, t)
                if not deferred:
                    if novel:
                        self._emit(index, t, gray, frame, self.t_change, self.t_still, True)
                    elif self.last is not None and not self.last.settled:
                        self.last.settled = True
                        self.last.t_settled = self.t_still
                    self.changed = False
```
and in `finish()`: `self._novel(self.prev, self.prev_t + 10.0)[0]` (never defer at end of stream). A first-occurrence single-glyph change is delayed by at most `max_period_s` (0.7 s) and emitted with the original `t_settled`; a slow-typing pause > S still splits states (`test_typing_without_pauses…` passes).
(b) apply the confirmation correction to the buffered emission too:
```python
        for cand in blink_upd.newly_confirmed:
            t_real = self._last_real_motion(cand.bbox)
            if t_real is None:
                continue
            if self.changed and (self.t_still is None or t_real < self.t_still):
                self.t_still = t_real
            if self.last is not None and any(abs(self.last.t_settled - x) < 1e-9 for x in cand.times) and t_real < self.last.t_settled:
                self.last.t_settled = t_real
```
Design: add both rules to §7.3/§7.5 (the "correction rule" sentence currently covers only the pending state).

**B2. Task 3 `decode.py` — `av.time_base` is the int `1000000` in PyAV 18, so `video_info().duration = c.duration * av.time_base` is 4×10¹¹ s.** `test_iter_frames_times_and_shapes` fails; downstream the last frame's `t_end` and every `chapter_of`/index time range for it would be garbage. Fix: `duration = float(c.duration / av.time_base)` (verified: 0.4 s on the fixture; the reviewer's design text §7.1 "852.83 s" was measured with the division form).

## Major

**M1. Task 12 `correspond.py` / design §11.1 — Jaccard collapses exactly in the case the design cites (a terminal with 1 line, then 31): J = 1/31, IoU = 0.03, score 0.13 < 0.3 → no match; `test_correspondence_by_text_survives_renaming_and_growth` fails.** Replace Jaccard with containment (`|A∩B| / min(|A|,|B|)`) in `score()`:
```python
    j = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0
```
and in the design §11.1 (`J = |A∩B| / min(|A|,|B|)`). Greedy descending assignment already limits the small-region-matches-anything risk; add IoU/app/name as the tie-break they already are.

**M2. Task 19 — the batch two-phase code calls `asyncio.run()` three times on one `AsyncAnthropic` client.** httpx2's async transport is created inside the first loop; reusing it from a second loop is the classic "Event loop is closed" failure. Wrap the two-phase in a single coroutine (in `run_perceive` / `run_interpret`):
```python
    async def _run() -> list[PerceptionRecord]:
        if cfg.model.mode == "batch" and hasattr(provider, "collecting"):
            provider.collecting = True
            await _perceive_all(run, cfg, provider)
            provider.collecting = False
            await provider.run_batches(run)
        return await _perceive_all(run, cfg, provider)
    records = asyncio.run(_run())
```

**M3. Task 19 `batch.py` — the errored-result check reads the wrong attribute.** `res.result.error` is an `ErrorResponse` whose `.type` is always `"error"`; the classification lives at `res.result.error.error.type` and is spelled `"invalid_request_error"`. As written, every invalid request is re-queued once and then silently dropped, and the final `_perceive_all` pass sends it to the live API synchronously. Fix:
```python
                elif res.result.type == "errored" and getattr(res.result.error.error, "type", "") == "invalid_request_error":
```

**M4. Task 10 `perceive.repair` — a row emptied by dropped marks becomes `[]` (which means "VLM-only line"), and marks in rows truncated by the length repair stay in `seen`, so they are neither assigned nor unassigned.** `test_repair_missing_duplicate_unknown_and_lengths` fails (`[[]]`). Replace the row loop:
```python
        new_rows: list[list[str]] = []
        new_lines: list[str] = []
        for k, row in enumerate(r.rows):
            kept = [m for m in row if m in known and m not in seen]
            repairs += len(row) - len(kept)
            seen.update(kept)
            if row and not kept:
                continue  # every mark was dropped: the row and its text go together
            new_rows.append(kept)
            if k < len(r.vlm_lines):
                new_lines.append(r.vlm_lines[k])
        if len(new_lines) != len(new_rows):
            repairs += 1
            n = min(len(new_lines), len(new_rows))
            for row in new_rows[n:]:
                seen.difference_update(row)
            new_rows, new_lines = new_rows[:n], new_lines[:n]
        r.rows, r.vlm_lines = new_rows, new_lines
```
and the test's expectations become `r2.rows == [] and r2.vlm_lines == []`, `unassigned_line_ids == ["l3", "l4"]`, `n == 7`. Put the rule in design §8.3 ("a row whose marks were all dropped is removed with its text; marks in rows cut by the length repair go to unassigned").

**M5. Task 7 `tests/test_vision.py` cannot pass as written, and it exposes a real OCR error worth recording.** On the 900×120 fixture Vision split the second line into two observations and read `--resource-group` as `-resource-group` (one hyphen dropped) — the parent's earlier 1000×300 smoke test happened to get one exact line. Make the test row-aware and tolerant of the hyphen: join fragments by row (`round(yc / 20)`), assert line 1 exactly, and for line 2 assert `text.replace("--", "-") == "az aks create -resource-group rg-demo -name aks-demo-01"`. Add the observation to design §5.4/§8.1 (Vision drops a hyphen of `--flag` on 18-px Menlo — R1 depends on the VLM cross-check) and to §22.

**M6. Task 11 `merge.layout_conf` — occlusion is not transitive to the occluded window's panes, and row coverage ignores descendant rows.** A terminal that `occludes` the browser window is still penalized by the browser's nav-pane lines that pass behind it (the pane's parent is the browser, not the pane), and a parent window whose text lives in child panes gets −0.2 for "scattered membership". Fix `_related` to compare ancestor sets against `occludes` (verified) and count rows recursively:
```python
    anc_a, anc_b = ancestors(a) | {a.id}, ancestors(b) | {b.id}
    return a.id in anc_b or b.id in anc_a or bool(anc_a & set(b.occludes)) or bool(anc_b & set(a.occludes))
```
Test fixture: `other` must be an unrelated region (`parent=None`) whose line overlaps the terminal's line horizontally (`bbox=(280, 42, 500, 58)` — the plan's boxes touch at x=300, so `hz > 0` is false and no penalty fires); `term.bbox` must be the union of its lines `(12, 40, 540, 78)` (the plan's `(12, 40, 640, 300)` gives coverage 0.14 → −0.2 → 0.75 and the `>= 0.9` assertion fails).

**M7. Task 3/4 — half-resolution mode diverges from design §7.2.** `iter_frames(downsample=2)` scales with swscale (an averaging filter), but §7.2 requires the *change map* to be reduced with a 2×2 max so 1-px strokes survive; averaged gray at half-res loses them before thresholding. Either implement §7.2 (decode full-res gray, `changed = change_map(...)`, then `changed.reshape(h//2, 2, w//2, 2).any(axis=(1, 3))`) or state in the plan that downsample=2 is unsupported in v1 and remove the option from `DetectParams`.

**M8. Task 5 `tests/test_settle.py` — two fixtures move a solid block 1 px per frame, whose leading/trailing edges are 1×20 columns: bar-shaped, excluded by §7.2, invisible.** `test_max_hold_during_continuous_motion_then_settle` (no unsettled emission) and `test_max_hold_frame_that_is_the_end_state_is_upgraded` fail for this reason, not because of the machine. Use `x = 10 + (i * 5) % 140`; and the upgrade scenario needs M **plus one frame** of motion (`range(91)`, expect `t_settled == (30 + 90) / FPS`): with exactly 90 moving frames the max-hold never fires (t − tChange reaches M on the first still frame, when `tStill` is already set). Add to design §7.7: a solid object moving ≤ 3 px per frame is invisible to detection (edges are bar-shaped) — accepted loss.

## Minor

**m1. Task 7 `is_confusable("naïve café")` is True (test fails).** The design means non-Latin look-alikes. Fix: `and not unicodedata.name(ch, "").startswith("LATIN")` on the non-ASCII letter test.

**m2. Task 11 `combine_focus`** returns 0.9 when caret and retrospective disagree but the VLM agrees with retrospective; the test expects 0.6. The design table has two matching rows with no precedence. Decide (test = conflict caps at 0.6) and state it in §9.4; code: compute `conflict` first and return `(0.6 if conflict else 0.9)`.

**m3. Task 11 `test_rows_join…`** expects 2 `row_rejected` lines, but the duplicate `l1` is consumed by row 0, so only `l4` is split out (1). Test bug; assert `== 1`.

**m4. Task 18 `tests/test_diagnostics.py`** fixture dicts have no `"ocr"` key, so every line counts as VLM-only (1.0). Give OCR lines `"ocr": "a"` etc.

**m5. Task 19 `test_strict_schema…`** expects optional fields to become required; the SDK's `transform_schema` keeps `b: str | None = None` optional (that is the SDK's contract for structured outputs). Assert `additionalProperties is False` and `"a" in required` only.

**m6. Task 15 `_hierarchy`** crashes with IndexError when every transition is `trivial` (`ts` empty → `propagate(sections)` on `[]`); guard `if not ts: return [], [], HierNode(...)` or skip the stage. Also §13.1's fallback to Stage 0 chapter boundaries for sections is not implemented (only fixed windows).

**m7. Task 10 `run_perceive` stage-skip key** hashes `ocr.jsonl` and the `model` config only; a changed overlay configuration re-draws overlays but `perceive` is skipped although its per-call inputs changed. Include `config_hash(cfg, "overlay")` in `ch` (or `run.overlays_dir` hashes).

**m8. Task 6 `Run.chapter_of`** does a plain `start_s <= t < end_s` range test and re-reads `outline.json` on every call (`extract_nodes` calls it per frame and per transition). Design §10.4 asks for snapping to emitted-frame intervals; at minimum cache the outline in the `Run` instance.

**m9. Task 6 `Run.load_transitions`** does not attach interpretations although design §10.7 says the loader does; consumers call `load_interpretations()` separately. Either change the design sentence or add an `attach=True` loader.

**m10. Task 18 `diagnostics()`** omits two §18.4 items (fragment stability, cache hit rate — `cache_entries` is not a rate) and the manifest never records library versions (§20.9). Add `"cache_hits"` by counting `cached` results per stage (return it from `stage_done` stats) and `importlib.metadata.version()` for `av`, `numpy`, `scipy`, `anthropic`, `pillow`, `rapidfuzz` in `run_stage1`'s `manifest_update`.

**m11. Task 13 `retrospective_focus`** implements only the "no `appeared` region" half of §9.4's attribution condition; "no `focused_region` change" is not checked. Add: skip when `frames[from].focused_region` and `frames[to].focused_region` are both set and the to-frame's focus does not correspond (via `t.regions.matched`) to the from-frame's.

**m12. Task 18 `estimate_cost`** ignores Stage 6 (its `stage_done` passes no `usage`/`model`); pass them from `run_hierarchy` as the other stages do.

**m13. Task 21 says "≈ 45" tests; the plan defines 69** (58 without the Vision test). Nit-level, but an executor counting will wonder.

**m14. Design §7.2 vs plan** — `components()` returns tight bboxes of changed pixels, so the 3×3 dilation used to merge strokes does not widen the bar test; good — but the plan text of §7.2 says "bars = … width ≤ 3" without saying tight; add "(tight bbox of the changed pixels, not the dilated blob)" to the design so a re-implementation does not use the blob bbox (which would make a 2-px caret 4 px wide and defeat the test).

## Nit

**n1.** `hierarchy.build_level`: `child_ids = {it.id for it in items[s:starts[bounds.index((s, _)) + 1]]}` relies on the loop variable `_`; use `enumerate` over `zip(nodes, elabs)` with `starts[k+1]`.
**n2.** `Emission.png_future: object` and `frame: object` — type them `Future | None` / `av.VideoFrame | tuple[int, Path] | None` so the on_emit replacement in Task 6 is visible in the signature.
**n3.** `cli.search` echoes `h['text'][:100]!r`; the `!r` inside an f-string with `:<8` formatting is fine but prints quotes; drop `!r`.
**n4.** `README.md` says "Nine idempotent stages" in the plan header; the CLI lists ten (`outline` … `index`). Say "ten (one optional)".

## Ran

- `uv sync --python 3.14` on the plan's `pyproject.toml` (hatchling, editable install of `vt`): ok.
- `uv run pytest tests -q` on the verbatim extraction: **56 passed, 13 failed** (listed above with causes).
- After the fixes above (B1, B2, M1, M4, M6 code + fixtures, M8 fixtures, m1–m5): **69 passed**, including `test_vision.py` (macOS) and all `test_settle.py` scenarios (static, single change, flash-revert, bar caret, block cursor, fast/slow typing, max-hold, max-hold upgrade, end-of-stream flush, scrolling churn ticks + final settled state).
- `uv run vt --help` lists all commands; `uv run vt setup` prints ok for Vision OCR, FTS5, sqlite-vec.
- SDK introspection: `AsyncAnthropic().messages.parse` accepts `output_format` + `output_config` + `system`; `messages.batches.results` is `async def` returning `AsyncJSONLDecoder` (so `async for … in await …` is correct); `MessageBatchErroredResult.error` is `ErrorResponse{error, request_id, type}` (M3); `MessageCreateParamsNonStreaming` has `output_config`, `cache_control`, `system`.
- `av.time_base == 1000000` (int) on PyAV 18.1 (B2).

## Checked and found correct

- Task 2 Myers/backtrack, `line_ops`, `pair_modifies`, `char_diff`, `is_clock_change`, `norm` (all 9 tests pass as written).
- Task 4 `components` (tight bboxes via `find_objects(np.where(changed, labels, 0), max_label=n)`), `is_bar`, `trigger`, `ChurnTracker` (warm-up, per-pixel hysteresis, deactivation time), `BlinkTracker` (confirmation at the third toggle, expiry) — all 7 tests pass.
- Task 5 machine logic for every scenario except the two rules in B1; churn ticks and the deactivation rule behave as §7.3 specifies on the scrolling fixture.
- Task 6 on_emit/finalize protocol (`frame` replaced by `(n, path)`, `png_future` awaited at finalization) is consistent after the plan's patch.
- Task 8 `place_label` slot order and clash counting; overlay keeps dimensions.
- Task 9 provider: cache key, cache hit path, `max_tokens` retry, schema retry with error text, refusal recording, `cache_control` on the system block, `output_config={"effort"}` — 4 tests pass; kwargs match the installed SDK.
- Task 12 `diff_region`/`diff_pair` (uncertain and in_churn propagation, `r0`, kind `unsettled`, `t = (prev.t_end, cur.t_settled)`).
- Task 13 coalescing Rules 1/2/1b (typed suffix, backspace tolerance, scroll-off deletes), transient merge with `hold_s`, trivial tagging, retrospective focus, `_follow` across per-frame region ids — 5 tests pass as written.
- Task 14 `render_diff` (both readings, grouping-uncertain flag), `validate_refs`, block layout (labels before images, transient image in the middle).
- Task 15 `repair_boundaries`, `fallback_segments`, `window_ranges`, `merge_window_boundaries`, `propagate`.
- Task 16 FTS5 tokenizer string, phrase quoting, trigram ≥ 3 chars, `bm25()` ordering, filters inside each index, RRF, node extraction ranges — 3 tests pass; sqlite-vec KNN query shape matches the earlier probe.
- Task 17 tool definitions and `Tools.search/get_node`; manual tool loop uses `tool_choice` auto (required for Fable 5.1) and returns all `tool_result`s in one user message.
- Task 20 `parse_outline_text`; Gemini call shape matches the fetched docs (`client.interactions.create` with `processing: "agentic"`).
- Typer `Path | None = None` options and `typer.Option(..., "--out")` work on typer 0.27; `from vt import coalesce, …` submodule imports in `cli.run` work.
- Spec coverage: every v1 section of the design maps to a task (§6→20, §7→3–6, §8→7–10, §9→11, §10→1/6, §11→12–13, §12→14, §13→15, §14→16–17, §16→1, §18.4→4/5/18, §20.7→9/19, §20.9→6, §20.11→6–18); the gaps are the minors m6–m11 above.
