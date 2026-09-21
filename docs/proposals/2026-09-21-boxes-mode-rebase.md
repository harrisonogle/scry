# Proposal: re-base the pipeline on boxes mode

Status: **draft for the owner's review, 2026-09-21. No code has been written against it.** If accepted it becomes
design revision 7 and replaces §4 (parts), §8.3, §9, §10.1–10.2, §10.6, §11, §15.1–15.2 and the affected rows of
§14, §16, §17 and §18 of `docs/visual-transcript-pipeline-design.md`. Stage 0, Stage 1, Stage 2a, Stage 6, the
provider, the call cache and the `subset` tool are untouched.

## 1. Purpose and evidence

The pipeline rebuilds every frame from scratch and then diffs two independent reconstructions, so instability in
the reconstruction reads as change. Every fix since the first live run has been a patch on that seam. The evidence:

| Finding | Ledger |
|---|---|
| The model split one page into 8 panes in one frame and 3 in the next; panes "appeared" on a static page. Fixed by demoting panes to labels. | L31 |
| On near-static transitions 90 of 96 structural ops sat on lines with no changed pixel. Fixed by a pixel veto. | L32, L38 |
| One knob, the row gap cap, moved agreement from 0.365 to 0.752 on the same data; it rejected 116 real rows. Turned off. | L37, L41 |
| A window whose only line is rewritten and grows scores just under the 0.3 correspondence threshold and is reported as gone. Documented, not fixed. | L31 |
| The typed event was blocked twice: by OCR whitespace jitter, then by a phantom box-less line in another window through the nothing-else-changed clause. | L29, L35, L41 |
| Each OCR box as its own unit with model-proposed associations works end to end: 31 groups on frame 150, the pairs checked were correct, zero rejected rows, +20 % Stage 2c cost. | L41 |
| RapidOCR boxes are stable: on unchanged pixels 96.5 % of boxes recur with the same rectangle and text (Vision 88.5 %). | `scratchpad/box-stability/result.txt` |
| Identical cold runs differ: repairs 5–13, one tooltip comes and goes. Single-run differences of a few percent are noise. | L42 |

The common cause is that **model-proposed structure carries identity**: rows are the unit of the diff, windows
scope it and are matched across frames by a score. The re-base moves identity onto what is measured.

## 2. Vocabulary

One name for the mode: **boxes mode**. It replaces "rows-as-boxes", "boxes plus associations" and the config value
`stage2c_rows = "boxes"`.

| Term | Meaning | Source |
|---|---|---|
| **Box** | One OCR detection: text and a rectangle. The unit of identity, diffing, citation and agreement. | measured |
| **Container** | A window or popup, optionally a pane inside a window. Every box belongs to one innermost container. A label. | model |
| **Link** | A typed relation among boxes of one container: `run`, `pair`, `record`. A label. | model |
| **Changed area** | A rectangle where pixels differ between two emitted frames (Stage 1's rule), joined with the boxes touching it. The "location" of a change. | measured |
| **Text change** | Before text and after text of one changed area, with a character diff. | measured |

| Old | New |
|---|---|
| mark, OCR line, `l<n>` | box, `b<n>` |
| row, row line, line, `Line` | box (a split text is a `run` link) |
| region, unit, `Region`, `r<n>` | container, `Container`, `c<n>` |
| association | link |
| `rows`, `vlm_lines` | `containers[].boxes`, `texts` |
| VLM-only line `v<n>` | missed text `m<n>` (never has a rectangle) |
| `computed_diff`, `DiffOp`, `RegionDiff` | `changes`, `Change` |
| `typed`, `output_appended` events | `text_appended` (chained); everything else is a plain text change |
| region correspondence, `matched` | removed |
| `rows_rejected`, `fragment_stability`, `layout_conf` | removed; `box_stability`, `link_consistency` |
| citation `"<frame>:<line_id>"` | `"<frame>:<box_id>"` |

"Line" survives only as a plain-English word for what a person sees in a terminal. "Cell", "visual line" and "row"
leave the design.

## 3. Principles

1. **Measured things carry identity; model-proposed things are labels.** Boxes and pixels decide what exists and
   what changed. Containers and links never gate, are never diffed, and never alter recorded text. A wrong label
   costs an enrichment, never a fake change.
2. **A box with no changed pixel under it is unchanged**, at any changed fraction. The 5 % limit on the veto
   (`pixel_gate_max_fraction`) was needless and goes.
3. **Honest text-change contract.** The mechanical layer reports that text appeared, changed or was removed at a
   location, with before, after and a character diff. It does not claim "typed". It makes no attempt to separate
   ghost text, program output or paste. Stage 5, which sees the frames, may say "typed".
4. **Two levels of screen structure, no more:** container and box, plus links. A UI element tree in the
   accessibility sense stays a non-goal (§1.4). The temporal hierarchy (video, sections, steps, transitions,
   frames) is unchanged.
5. **No constants from the sample video.** Geometric parameters are relative to box height or screen size and the
   evaluation sets their values. No logic for edge cases until evidence shows the case (§9 watch list).
6. **Cold runs for anything that judges a model call**, with repeats; cached model outputs only when comparing
   code downstream of a fixed output.

## 4. Data model

`frames.jsonl`, one record per emitted frame (Stage 1 fields unchanged and elided):

```json
{"frame": 155, "png": "frames/00155.png", "width": 1920, "height": 1080,
 "boxes": [
   {"id": "b33", "bbox": [659, 352, 904, 371], "text": "PS C:\\Users\\msadmin> az login", "conf": 0.98,
    "container": "c2", "vlm": "PS C:\\Users\\msadmin> a login", "agree": false, "in_churn": false}],
 "containers": [
   {"id": "c1", "kind": "window", "app": "Browser", "name": "Edge — Azure portal", "parent": null,
    "rect": [0, 0, 1920, 1040], "rect_source": "hull", "conf": 0.9, "occludes": []},
   {"id": "c2", "kind": "window", "app": "PowerShell", "name": "Administrator: PowerShell 7-preview (x64)",
    "parent": null, "rect": [658, 320, 1680, 853], "rect_source": "model", "conf": 0.95, "occludes": ["c1"]}],
 "links": [
   {"kind": "pair", "key": ["b28"], "value": ["b29"]},
   {"kind": "run", "boxes": ["b61", "b62"], "joiner": ""},
   {"kind": "record", "members": [["b70"], ["b71"], ["b72"]]}],
 "missed": [{"id": "m1", "text": "Networking", "container": "c1"}],
 "unassigned": ["b9"], "focused_container": "c2", "focused_conf": 0.8, "description": "…",
 "repairs": 0, "model": "claude-opus-5", "prompt_version": "s2c-v2", "error": null}
```

- `text` is the OCR reading. `vlm` and `agree` exist only when Stage 2c transcribes. Which reading is recorded on
  disagreement stays design open question §22 #15.
- `rect_source` is `hull` (union of the container's boxes, today's rule) or `model` (drawn by the model, arms B
  and C of §7).
- `missed` entries have no rectangle, so they can never enter a change record. They are index text only. This is
  what removes the phantom-line failure of L41.
- A side of a `pair` and a member of a `record` are lists of box ids, which is an implicit run. A box appears in
  at most one link.

`transitions.jsonl`:

```json
{"id": "T9", "from_frame": 154, "to_frame": 155, "t": [598.7, 620.7], "kind": "single",
 "pixels": {"changed_fraction": 0.0002, "areas": 1},
 "changes": [
   {"rect": [659, 350, 904, 373], "kind": "appended",
    "before": ["PS C:\\Users\\msadmin>"], "after": ["PS C:\\Users\\msadmin> az login"],
    "char_diff": [["=", "PS C:\\Users\\msadmin>"], ["+", " az login"]],
    "before_boxes": ["154:b31"], "after_boxes": ["155:b33"], "uncertain": true,
    "labels": {"container": "PowerShell: Administrator: PowerShell 7-preview (x64)", "link": null}}],
 "container_events": [],
 "events": [{"type": "text_appended", "rect": [659, 350, 904, 373], "text": " az login",
             "result": "PS C:\\Users\\msadmin> az login", "frames": [154, 155]}],
 "transient": null}
```

- `kind` of a change: `appeared` (nothing before), `removed` (nothing after), `appended` (joined before is a prefix
  of joined after), `truncated` (the reverse), `changed` (otherwise), `visual_only` (the before and after texts
  are the same multiset: a highlight, a cursor, a hover). The labels are conveniences; before, after and the diff
  are the record.
- When an area touches many boxes (a window switch, a scroll) `before` and `after` are the two box-text lists in
  reading order and the record also carries `ops`, the existing Myers alignment over those lists, so moved
  identical texts align as equal. A delete and insert whose boxes overlap vertically by half the smaller height
  pair as a modify; the 0.6 similarity pairing is dropped.
- `labels.link` names the key when a changed box is the value of a pair ("value of Status").
- `container_events` are annotation-level: a container of the later frame most of whose boxes are after-only is
  `appeared`, with `pixel_support`, the share of its rectangle under changed pixels. The reverse is `disappeared`.

## 5. Stage by stage

**Stage 2a, 2b.** Unchanged. The overlay exists only for referencing arms A and B (§7).

**Stage 2c.** One call per frame. Draft system prompt, arm A, with the transcription paragraph optional:

```
You structure screenshots of computer tutorials (terminals, code editors, browsers, dialogs).

You are shown the same screenshot twice. Image 1 is the clean frame. Image 2 is the same frame with a numbered
box around every piece of text an OCR engine detected; each number sits beside its box and is NOT part of the
screen. A number is written as a box id: b1, b2, ...

Produce a JSON object with these fields.

containers: the windows (top-level application windows) and popups (menus, dialogs, tooltips, toasts) on screen
and, inside a window, its panes (editor, terminal pane, navigation, content area, toolbar, title bar). Anything
drawn over a window is its own popup, never part of what it covers. Name each container and its application,
give its parent (null for a window or a free-floating popup), the containers it covers, and the ids of the boxes
it directly contains. Every box id appears in exactly one container, or in unassigned.

links: relations between boxes of one container. Three kinds.
  run: boxes that are one continuous piece of text which the OCR engine split or the screen wrapped onto the
    next line, in reading order. joiner is "" when the text was cut by a hard wrap, as in a terminal, and " "
    otherwise.
  pair: a label and its value (a property and its value, a form field and its content). Give key and value,
    each a list of box ids in reading order.
  record: the members of one table row, left to right, each a list of box ids.
Boxes that merely sit side by side stand alone: tabs, toolbar buttons, menu items, breadcrumbs. A box appears
in at most one link.

[transcribing only] texts: for every box id, the verbatim text inside that box. Preserve case, punctuation,
whitespace and symbols. Never correct, complete or normalize commands, code, paths or identifiers. Use ? for a
character you cannot resolve. An icon is not text: give "". missed: text no box covers, with its container.

focused_container, focused_conf, focused_cues; description: as today.
```

Validation stays repair, never abort: an unknown id is dropped, a box in two containers keeps the first, a link
naming an unknown or already-linked box is dropped, a box in no container goes to `unassigned`; all counted.
Group-only mode is legal (the current validator forbidding it is an artifact of how L41 was wired).

**Stage 3 (merge).** Shrinks to: attach each box's container, attach links, and when transcribing attach `vlm`
and `agree` per box (exact equality after `norm`, with the icon-glyph strip rule kept). Nothing geometric remains.

**Stage 4 (changes).** For each consecutive frame pair:
1. Changed components by Stage 1's rule over the two PNGs (`PixelSource`, as today), each grown by
   `pixel_gate_margin_lines` × the median box height.
2. A changed area is a component joined with the boxes of either frame that touch it; areas sharing a box merge.
3. Every box touching no area is unchanged. No op can exist on it.
4. Per area: `before` and `after` are the touching boxes' texts in reading order (boxes whose vertical extents
   overlap by at least half the smaller height are on one line, left to right; lines top to bottom). If the two
   multisets are equal the change is `visual_only`, which makes an ordering flip harmless. Otherwise compare the
   joined strings, which is invariant to OCR re-splitting, then align the lists with Myers when either has more
   than one entry.
5. **Transients by pixels.** Frame *i* is a transient when an area changed at *i* shows no change between frames
   *i−1* and *i+1* under the same rule, and the hold is under `transient_max_s`. The model no longer has to
   recognise the tooltip for the rule to fire, which removes the scale sensitivity seen in L33 and L42.
6. **Chaining.** Consecutive transitions chain into one `text_appended` event when each has an `appended` change,
   the rectangles intersect, and one's joined after text equals the next one's joined before text. The event
   carries the full appended string. Stage 5 is called once on the first and last frames, as today.
7. `trivial` keeps the clock rule on `char_diff`.

**Focus.** Caret attribution and retrospective focus are dropped. `focused_container` is the model's self-report,
a label. Stage 1's blink tracker stays: its job is keeping a blinking cursor from emitting frames.

**Stage 5.** Half-scale frames (L39). The change text is rendered per area with its labels, for example
`PowerShell window: appended " az login" to "PS C:\Users\msadmin>"` or `Browser, value of Status: "Creating" →
"Succeeded"`. Citations are `"<frame>:<box_id>"`. The §15.2 contract is reworded to boxes and areas.

**Stage 7.** Correction to the record: today's frame-level node holds only the model's description, so a
multi-term query depends on the model's container assignment. New nodes: one **frame node holding every box's
text**, independent of containers; one node per container (its box texts, run texts joined with their joiner,
both readings of a disagreeing box); pairs stored as `key` and `value` fields in the payload and indexed as
`key value` tokens, independent of the on-screen delimiter and whitespace; transitions indexed by their change
text and interpretation. A `get_pairs(key_like, t_from, t_to)` tool for the agent is a follow-on, not part of the
re-base.

## 6. What is deleted and what stays

| Module | Deleted | Stays |
|---|---|---|
| `merge.py` | `_row_plausible`, `build_region_lines`, `align_repair`, `_matches`, `region_associations`, `layout_conf` with `_related`, `_ancestors`, `_children`, `_descendant_lines`, `caret_region`, `combine_focus`, `_root` | `agreement` (per box, only when transcribing), `union`, a small `merge_frame` |
| `correspond.py` | the whole module: `score`, `correspond`, the 0.5/0.3/0.1/0.1 weights and the 0.3 threshold, and with it the single-line-window gap | — |
| `diff.py` | `diff_region`, `_ys`, `_line_h`, `is_gated`, `pixel_gate` as a veto over structural ops | `PixelSource`, `_overlaps`, `_dilate`, `_margin`; Myers in `textdiff.py` |
| `coalesce.py` | `_other_ops_ok`, `_typed_op`, `_output_ops`, `_follow`, `retrospective_focus`, `_vlm_focus`; Rules 1, 1b, 2 | `tag_trivial`, `assign_ids`, `_kind`, `run_diff`; `merge_transients` and `coalesce` rewritten |
| `schemas.py` | `Line`, `Region`, `FrameRecord.unit_of/units/unit_line_sources/unit_lines`, `Correspondence`, `RegionDiff`, `DiffOp`, `FocusRecord`, the eight `VlmRegion*`/`VlmPerception*` variants | Stage 1 and OCR records, `PixelChange`, `Transition` reshaped, hierarchy records |
| `index.py` | `region_text` | everything else; `extract_nodes` gains the frame node and pair fields |
| `diagnostics.py` | `fragment_stability`, `rows_rejected`, `grouping_repairs` | `mark_match` (when transcribing), costs; new metrics of §7 |
| config | `row_y_tol`, `row_gap_lines`, `align_*`, `modify_sim`, `typed_tolerance`, `corr_*`, `pixel_gate_max_fraction`, `stage2c_panes`, `stage2c_rows` | `pixel_gate_margin_lines`, `transient_max_s`, `glyph_max_len` |

Files `focus.jsonl` and the row-banding rule of L31 go with them. Existing run directories stop loading; the
commit before the re-base gets a tag so the evidence behind L28–L42 stays reproducible.

**OCR coordinates in code after the re-base:** id assignment in reading order (2a); overlay drawing (2b); the
optional input list (arm D; L30, L42); box-to-container assignment by centre-inside (arms B, C); snapping the
model's points to boxes (arm C); the container hull (arm A); changed-area construction and the veto (Stage 4);
modify pairing by vertical overlap; reading order within an area; the spacing guard's word gaps (Rapid adapter);
the box-stability metric; Stage 5 crops mode; a future citation highlight.

## 7. Evaluation plan

**Spans.** The smoke span, frames 145–155 (11 frames: title slide, portal, tooltips, a window switch, one
keystroke). A second span, frames 155–187 (33 frames: `az login`, `az account show` with output, `az configure`,
`az aks get-credentials` with output, `kubectl` commands with output, a cut around 182–184). The current
pipeline's cold before-run of span 2 is `runs/span2-before` (in progress at the time of writing).

**Reference-free metrics.**

| Metric | Definition |
|---|---|
| `box_stability` | On frame pairs, the share of boxes on unchanged pixels that recur with the same rectangle (IoU ≥ 0.8) and text |
| `link_consistency` | On frame pairs with no changed pixel under a link's boxes, the share of links proposed identically in both frames, per kind |
| container coverage | Boxes in exactly one container; in none; in several (arms B, C) |
| popups found | Frames 149 and 151 of the smoke span, and any in span 2, per run |
| container-name consistency | Share of static frame pairs where a container keeps its app and name |
| snap failures | Arm C: model points that land on no box within half a box height |
| text-change events | Changes per transition by kind; `text_appended` chains found; Stage 5 calls |
| agreement, `mark_match_fraction` | Only when transcribing |
| repairs, unassigned, cost, wall time | As today |

**Needs the owner's ground truth:** whether recorded text is right (CER on commands), link precision and recall,
container assignment accuracy, and event precision and recall. The cheapest useful piece is a hand list of the
commands in span 2 with their times, about a dozen lines.

**Referencing arms.**

| Arm | Images | The model returns | Code does |
|---|---|---|---|
| A | clean + overlay | box ids per container and per link | hull rectangle per container |
| B | clean + overlay | a rectangle per container; links by id | assigns boxes by centre-inside, front-most container wins |
| C | clean only | a rectangle per container; links as points | assigns by centre-inside; snaps each point to the nearest box |
| D | clean only, plus OCR's box coordinates as a text list | box ids | as A |

If transcriptions are kept under B, C or D they are assigned to boxes by position and similarity jointly, so an
id shuffle of the kind seen in L41 cannot occur. Arm A's labels will clash at small scales; `label_clashes` shows
where it stops being viable.

**Phases.** Screen one factor at a time; the only factorial is scale × arm, in group-only mode. All runs cold.
Costs use the measured per-frame figures: Stage 2c transcribing in boxes mode $0.117, group-only $0.063 at full
scale (measured in row mode) falling to about $0.031 at scale 0.2, Stage 5 at half scale $0.019 per transition.

| Phase | What | Runs | Estimate |
|---|---|---|---|
| E0 | One boxes-mode run of each span to develop Stages 3–7 against fixed model outputs | 2 | $5 |
| E1 | Noise floor: arm A, transcribing, full scale, 3 repeats, both spans, Stage 5 included | 6 | $18 |
| E2 | Arms A–D, group-only, full scale, 3 repeats on the smoke span; the best two confirmed on span 2 | 12 + 6 | $17 |
| E3 | Transcription on or off with the winning arm at full scale, 3 repeats, both spans (reuses E1 if A wins) | 0–6 | $0–15 |
| E4 | Pane labels on or off (L41's finding was specific to rows), 3 repeats, smoke span | 6 | $4 |
| E5 | Scale 0.67, 0.5, 0.4, 0.3, 0.25, 0.2 × the best two arms, group-only, 3 repeats, smoke span (1.0 from E2); the chosen point confirmed on span 2 | 36 + 3 | $17 |
| E6 | Stage 5 on the new change text, 3 repeats, both spans | 3 | $3 |

About 75 runs and $65–80 of the $491. Then the full sample, sync and batch.

## 8. Build order

Each step lands with synthetic-fixture tests and its own commit; steps 3–6 develop against E0's cached outputs.

1. Schemas and loaders: `Box`, `Container`, `Link`, `Change`; tag the pre-re-base commit.
2. Stage 2c arm A: prompt, schema, typed links, repair rules, group-only legal.
3. Stage 3 shrink.
4. Stage 4: areas, veto at any fraction, change records, transients by pixels, chaining, clock rule.
5. Stage 5 rendering and the §15.2 contract; citations by box.
6. Stage 7: frame node with all box texts, container nodes, run and pair text, pair fields.
7. Diagnostics: `box_stability`, `link_consistency`, coverage, name consistency.
8. Arms B, C, D as evaluation-only switches; run §7; delete the losing arms.
9. Delete the row machinery and its config keys; fold this document into the design as revision 7; ledger rows.

## 9. Risks and watch list

- **Containers lose their scoping role.** The per-window diff protected against interleaved text of overlapping
  windows. The veto at any fraction and area-local lists should make that moot; a scroll inside a partly covered
  window is the case to watch.
- **No window identity across frames.** Names vary from call to call, so "the same window" is only a label.
  Nothing mechanical depends on it after the re-base; the name-consistency metric says how much the UX suffers.
- **One geometric rule remains:** reading order within an area. It is scale-free, and the multiset check makes a
  flip harmless on near-static transitions.
- **Areas can merge** a keystroke with a simultaneous large change; the ops list still carries both, labelled.
- **Output bursts no longer coalesce** (Rule 2 goes). Span 2 will show how many Stage 5 calls that costs.
- **Links are unproven beyond one frame of one run:** consistency per kind, joiner correctness on a wrapped
  command, and the id shuffle on dense strips are all open. A kind that fails `link_consistency` is dropped.
- **Arm C's localisation error** relative to box height is unknown; snap failures measure it.
- **The spacing guard or the engine flips** `SubscriptionID` and `Subscription ID` on unchanged pixels. The veto
  hides it from the diff; the index still sees both. Check which component flips.
- **Watch list, no logic until evidence:** a growing line (needs none: box identity is only used on unchanged
  pixels, where overlap matching measured 96.5 %), cursor glyphs read as text, the pointer clipping a box,
  low-contrast flicker, scrolls and window moves, occlusion clipping, duplicate strings, re-wrap on resize.

## 10. Questions for the owner

1. **Is a second reading wanted at all?** E3 measures its cost and what it catches; the threshold for "worth it"
   is yours. It also decides whether "index both readings" and joint position-and-similarity assignment exist.
2. **Delete row mode outright** once the re-base is validated, behind a tag, or keep it as a switch? Recommended:
   delete.
3. **Are pane labels wanted** in search hits and descriptions if E4 shows they cost tokens and change nothing
   mechanical?
4. **Is "which window had focus" a deliverable?** If not, the model's self-report can go too.
5. **Will you write the span 2 command list** (about a dozen commands with times)? It turns the text-change
   contract from reference-free to measured.
6. **Budget:** about $65–80 for §7, before the full sample run.
