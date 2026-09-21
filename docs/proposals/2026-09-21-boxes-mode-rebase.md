# Proposal: re-base the pipeline on boxes mode

Status: **revision 2, 2026-09-21, for the owner's review. No code has been written against it.** Revision 1 is commit
`0a3135e`; its two reviews are `docs/reviews/2026-09-21-boxes-mode-rebase-review-{fork,fresh}.md` (both: accept with
changes; both prototyped Stage 4 on existing OCR and frames). If accepted this becomes design revision 7 and replaces
§4 (parts), §8.3, §9, §10.1–10.2, §10.6, §11, §12 (inputs and outputs), §13.2–13.3 (rendering), §14, §15.1–15.4 and the
affected rows of §16–§18 of `docs/visual-transcript-pipeline-design.md`. Stage 0, Stage 1, Stage 2a, the provider, the
call cache and `subset` are untouched. Stage 6 and the answering agent are **not** untouched (revision 1 said they were).

## 0. Revision 2: what changed and why

| Change | Source |
|---|---|
| The unit of a change record is the **box**, not an area's joined string. Same-place same-text pairs drop out, equal texts cancel across the whole transition as moves, the rest group by rectangle intersection. Labels compare with whitespace removed; recorded strings stay exact. | Both reviews, blocking (fork F1–F4, fresh B1): 4 of 9 `appended` records were artifacts, 3 of 6 real entries were missed, and on scrolls 72 of 213 moved texts (55 of 64 on page scrolls) land in different areas. Owner approved the whitespace-blind label. |
| One record shape for every size of change: a few counterpart groups plus lists of appeared and removed box ids. No large-change threshold. | Fork F6 (35, 67, 47 areas on 181→184). |
| Chaining no longer merges Stage 5 calls. Each group records `continues`, an exact link through a shared box. | Both prototypes: chaining saved 1 call in 32. |
| `container_events` cut. Containers are **flat**: windows and popups, no nesting; a popup may name its owner window; "pane" is at most a label string, tested once. Phase E4 reduced to that. | Fresh S3 (3 of 5 firings false); owner decision. |
| Transients are per area and the time gate goes; `hold_s` is recorded. | Fork F7, fresh S4.7; the 2.8 s tooltip the gate missed. |
| The index unit is a **box lifetime** with a majority reading; no per-frame copies; both joins of a run indexed; pairs as fields. | Owner discussion; fresh S7 (`"az account show"`: 20 near-duplicate hits, no transition) and S5; L43 (majority 7/7 against first sighting 4/7). |
| Transcription stays **on** in the base; group-only becomes a cost ablation. A new option is added: transcribe only changed boxes. | L43: the model is the best reader of live command lines (12/16 against 8/16) and its disagreement flags 9 of 9 OCR misreads; OCR confidence flags none. |
| §22 #15 (which reading is recorded) gets options, evidence and a recommendation (§6). | Fork Q-B; L43. |
| Stage 5 gains `entered_text` and `submitted`, is handed the box ids it may cite, and the agent prompt gives guidance, not a prohibition. Persistence is evidence, never a gate. | Owner decisions; span-2 baseline: 5 predicted commands never ran; 53 invalid citations in 30 transitions. |
| Build order: Stage 4 and lifetimes first, free, on all 221 frames; new files live beside the old until the last step; Stage 6, the agent and both prompts get entries. | Both reviews (fork should-fix 1–2, fresh S1–S2). |
| Evaluation rebuilt on ground truth (the span-2 command list, negatives included); evidence rules instead of thresholds; arms are not eliminated before the scale sweep; paired by frame; repeats go to finalists. | Fresh B2, fork should-fix 3–4, owner decisions, L42. |
| Every undefined case the reviews listed is now defined (§5 Stage 4), and the constants that remain are named (§10). | Fresh S4, S6. |
| Engine settings `use_cls` off and `rec_batch_num` 1 are part of the base. | L43. |

## 1. Purpose and evidence

The pipeline rebuilds every frame from scratch and diffs two independent reconstructions, so instability in the
reconstruction reads as change. Every fix since the first live run has patched that seam.

| Finding | Source |
|---|---|
| Panes split 8 against 3 on one page and "appeared" on a static screen. | L31 |
| On near-static transitions 90 of 96 structural ops sat on lines with no changed pixel. | L32, L38 |
| One knob, the row gap cap, moved agreement from 0.365 to 0.752 on the same Rapid-box data. | L37, L41 |
| A one-line window that is rewritten and grows falls under the 0.3 correspondence threshold. | L31 |
| The typed event was blocked by whitespace jitter, then by a phantom box-less line in another window. | L29, L35, L41 |
| Boxes as units with model-proposed associations work end to end. | L41 |
| **The veto is sound:** on 35 near-static pairs 4,199 boxes touch no changed component; 176 read differently in the next frame and every one is an OCR re-read, none a real change. Box stability 96.7 % (smoke), 95.6 % (span 2). | fresh review, measured |
| **Today's pipeline on span 2** (frames 155–187, cold, $4.59): the typed rule captured 1 of about 8 commands and recorded it wrong from its first sighting (`azconfigure --defaultsgroup=…`); Stage 5 narrated most commands correctly from the frames; 53 invalid citations over 30 transitions. | `runs/span2-before` |
| **OCR is reliable on settled text and unreliable on a live input line:** scrollback rows 52/53 exact, live rows 8/16, 3/11 when the shell's predicted text is on the line; five live "commands" were predictions that never ran; the majority reading over a text's sightings is right for 7 of 7 executed commands. | L43 |
| Identical cold runs differ: repairs 5–13, a tooltip comes and goes, container-name consistency 0.39, 0.79, 1.00. | L42, fresh review |

The common cause is that **model-proposed structure carries identity**. The re-base moves identity onto what is measured.

## 2. Vocabulary

One name: **boxes mode**.

| Term | Meaning | Source |
|---|---|---|
| **Box** | One OCR detection: text and a rectangle. Unit of identity, change, citation and agreement. | measured |
| **Reading** | A text for a box from one reader: `ocr`, or `vlm` when Stage 2c transcribes. | measured / model |
| **Lifetime** | A box followed across consecutive frames while it stays the same text: on unchanged pixels, moved, or re-read with only whitespace differing. It has a majority reading per reader, the variants, and first and last frame and time. The index unit. | measured |
| **Container** | A window or a popup. Flat: containers do not nest. A popup may name an owner window. A label. | model |
| **Link** | A typed relation among boxes of one container: `run`, `pair`, `record`. A label. | model |
| **Changed component / area** | A connected set of changed pixels of at least θmin (Stage 1's rule), and its rectangle. The location of a change. | measured |
| **Change group** | A small set of before and after boxes that overlap each other under changed pixels, with a kind and a character diff. | measured |

| Old | New |
|---|---|
| mark, OCR line, `l<n>` | box, `b<n>` |
| row, row line, line, `Line` | box (a split text is a `run` link) |
| region, unit, pane, `Region`, `r<n>` | container `c<n>` (window or popup); pane is at most `box.pane`, a string |
| association | link |
| `rows`, `vlm_lines` | `containers[].boxes`, `texts` |
| VLM-only line `v<n>` | missed text `m<n>` (no rectangle; citable, never in a change) |
| `computed_diff`, `DiffOp`, `RegionDiff`, unit line lists, row banding | `groups`, `appeared`, `removed`, `moved` |
| `typed`, `output_appended`, `coalesced` | kinds `appended` … on groups; `continues`; Stage 5's `entered_text`, `submitted` |
| region correspondence, `matched`, `container_events` | removed |
| per-frame region and frame index nodes | lifetime nodes |
| `rows_rejected`, `fragment_stability`, `layout_conf` | removed; `box_stability`, `unstable`, `touched_share` |
| citation `"<frame>:<line_id>"` | `"<frame>:<box_id>"` |

"Line" survives only as a plain word for what a person sees in a terminal. "Row", "cell" and "visual line" leave the design.

## 3. Principles

1. **Measured things carry identity; model-proposed things are labels.** Boxes and pixels decide what exists and what
   changed. Containers and links never gate, are never diffed, never alter recorded text. A wrong label costs an
   enrichment, never a fake change.
2. **A box with no changed component under it is unchanged**, at any changed fraction.
3. **Honest text-change contract.** The mechanical layer reports that text appeared, changed, moved or was removed at a
   location, with before, after and a character diff. It does not say "typed" and does not separate suggestions,
   program output or paste. No cursor or suggestion locating, no brightness thresholds, no caret attribution.
4. **Whether something was done is interpretation.** Stage 5 sees the frames and says what the user entered and whether
   it was submitted. How long a text stayed on screen is evidence shown to the agent, never a rule: a command can be
   entered and the window minimised, and a one-line terminal has no scrollback.
5. **Record, do not pick.** Every reading is kept with its counts. Exact agreement between independent readers is the
   only "quote this verbatim" signal.
6. **Two levels of screen structure:** container and box, plus links. No UI element tree (§1.4). The temporal
   hierarchy is unchanged.
7. **No constants from the sample video**, and no logic for a case until evidence shows it. The constants that remain
   are listed in §10 with how each is checked.
8. **Evidence rules, not success thresholds.** How each metric is computed is fixed before spending; the noise floor is
   measured first; a difference inside the noise is no difference; every phase is reviewed before the next is planned.
   Cold runs with repeats for anything that judges a model call; cached outputs only downstream of a fixed output.

## 4. Data model

New files live beside the old ones until the last build step (§9).

`boxes.jsonl`, one record per emitted frame:

```json
{"frame": 155, "png": "frames/00155.png",
 "boxes": [{"id": "b33", "bbox": [659, 352, 904, 371], "ocr": "PS C:\\Users\\msadmin> az login", "conf": 0.98,
            "vlm": "PS C:\\Users\\msadmin> a login", "agree": false, "non_text": false,
            "container": "c2", "pane": null, "in_churn": false, "lifetime": "L388"}],
 "containers": [{"id": "c1", "kind": "window", "app": "Browser", "name": "Edge — Azure portal", "owner": null,
                 "rect": [0, 0, 1920, 1040], "rect_source": "hull", "covers": []},
                {"id": "c2", "kind": "window", "app": "PowerShell", "name": "Administrator: PowerShell 7-preview (x64)",
                 "owner": null, "rect": [658, 320, 1680, 853], "rect_source": "model", "covers": ["c1"]}],
 "links": [{"kind": "pair", "key": ["b28"], "value": ["b29"]},
           {"kind": "run", "boxes": ["b61", "b62"], "joiner": ""},
           {"kind": "record", "members": [["b70"], ["b71"], ["b72"]], "header": ["b64", "b65", "b66"]}],
 "missed": [{"id": "m1", "text": "Networking", "container": "c1"}],
 "unassigned": ["b9"], "focused_container": "c2", "description": "…", "repairs": 0,
 "model": "claude-opus-5", "prompt_version": "s2c-v2", "error": null}
```

- `non_text` is set when the model returns `""` for a box (an icon glyph such as `口`): the box leaves agreement
  denominators and index text. This closes the open item on empty transcriptions.
- A key and value that OCR put in one box (`Subscription ID :3e6b…`) can never be a pair; pairs are an enrichment, not
  a complete table of properties.
- A link whose boxes sit in two containers is dropped and counted. A box is in at most one link.

`changes.jsonl`, one record per transition:

```json
{"id": "T9", "from_frame": 154, "to_frame": 155, "t": [598.7, 620.7], "kind": "single",
 "pixels": {"changed_fraction": 0.0002, "components": 2, "textless": 1, "touched_share": 0.01},
 "groups": [{"kind": "appended", "rect": [659, 350, 904, 373],
             "before": [{"box": "154:b31", "text": "PS C:\\Users\\msadmin>"}],
             "after": [{"box": "155:b33", "text": "PS C:\\Users\\msadmin> az login"}],
             "char_diff": [["=", "PS C:\\Users\\msadmin>"], ["+", " az login"]],
             "uncertain": true, "continues": null, "transient": false,
             "labels": {"container": "PowerShell: Administrator: PowerShell 7-preview (x64)", "link": null}}],
 "appeared": [], "removed": [], "moved": 0, "same_place": 1, "transient": null}
```

- One shape for every size. A keystroke is one group. A page load is a few groups plus long `appeared` and `removed`
  lists of box ids (texts live in `boxes.jsonl`). A scroll is mostly `moved`. There is no "large change" mode.
- `text` in a group is the OCR reading of that frame; `uncertain` means the readers disagree on one of its boxes.
- `labels.link` names the key when a changed box is the value of a pair ("value of Status").
- Transition kinds: `single`, `transient_merged`, `unsettled`, `trivial`. `coalesced` goes.

`lifetimes.jsonl`:

```json
{"id": "L412", "ocr": "PS C:\\Users\\msadmin> az configure --defaults group=RG1-KodeKloud-AKS",
 "readings": {"ocr": {"PS C:\\Users\\msadmin> az configure --defaults group=RG1-KodeKloud-AKS": 25,
                      "PS C:\\Users\\msadmin>azconfigure --defaultsgroup=RG1-KodeKloud-AKS": 1},
              "vlm": {"PS C:\\Users\\msadmin> az configure --defaults group=RG1-KodeKloud-AKS": 26}},
 "agree": true, "unstable": true, "sightings": 26,
 "first": {"frame": 161, "t": 649.2}, "last": {"frame": 187, "t": 721.0},
 "moved": true, "container": "PowerShell: Administrator: PowerShell 7-preview (x64)", "boxes": ["161:b40", "…"]}
```

`ocr` and `vlm` at the top level are each reader's majority reading; `agree` compares the two majorities; `unstable`
means a reader gave more than one reading of the same pixels (3.3 % of boxes on the smoke span, 4.4 % on span 2), a
measured fact the agent can hedge on even without a second reader.

Stage 5 output gains two fields: `entered_text` (what the user entered in this transition as far as the frames show,
excluding anything the application suggested; null when nothing was entered) and `submitted` (`yes`, `no`, `unclear`:
whether what was entered took effect, for example Enter pressed and output or a new prompt appearing).

## 5. Stage by stage

**Stage 2a.** RapidOCR 3.9 with `use_cls` off and `rec_batch_num` 1 (L43). No second pass, upscale, normalisation,
English model or OCR ensemble. **Stage 2b.** Unchanged; the overlay exists only for referencing arms A and B.

**Stage 2c.** One call per frame, transcribing. Draft system prompt, arm A:

```
You structure and transcribe screenshots of computer tutorials (terminals, code editors, browsers, dialogs).

You are shown the same screenshot twice. Image 1 is the clean frame. Image 2 is the same frame with a numbered box
around every piece of text an OCR engine detected; each number sits beside its box and is NOT part of the screen.
A number is written as a box id: b1, b2, ... Read text from Image 1; use Image 2 only to know which id is which box.

containers: the windows (top-level application windows) and popups (menus, dialogs, tooltips, toasts) on screen.
Containers do not nest. Anything drawn over a window is its own popup, never part of what it covers; a popup may name
the window it belongs to as owner. Give each container's application and name, the containers it covers, and the ids
of the boxes it contains. Every box id appears in exactly one container, or in unassigned.

links: relations between boxes of one container.
  run: boxes that are one continuous piece of text which the OCR engine split or the screen wrapped onto the next
    line, in reading order. joiner is "" when a word was cut in two by the wrap, " " otherwise.
  pair: a label and its value (a property and its value, a form field and its content). key and value are lists of
    box ids. A two-column grid of labels and values is pairs, not records.
  record: one row of a table with three or more columns: members, left to right, each a list of box ids; header,
    the box ids of the column headings when they are visible.
Boxes that merely sit side by side stand alone: tabs, toolbar buttons, menu items, breadcrumbs.

texts: for every box id, {id, text}: the verbatim text inside that box. Preserve case, punctuation, whitespace and
symbols. Never correct, complete or normalize commands, code, paths or identifiers. Use ? for a character you cannot
resolve. An icon is not text: give "". missed: text no box covers, with its container.

focused_container, focused_conf, focused_cues; description: as today.
```

The output schema is fixed in the build step, not here, but two choices are made: `texts` is a list of `{id, text}`,
not an array parallel to the id list (about 330 more output tokens per frame, in exchange for no positional
misalignment), and structured outputs allow no free-key maps. Validation is repair, never abort: an unknown id is
dropped, a box in two containers keeps the first, a link naming an unknown, already-linked or cross-container box is
dropped, a box in no container goes to `unassigned`; all counted. Group-only mode and changed-boxes-only transcription
(§8, P3) are legal variants of the same prompt.

**Stage 3.** Attach each box's container and links, and `vlm`, `agree` and `non_text` per box (exact equality after
`norm`, with the icon-glyph strip rule kept). Under arms B–D readings are assigned to boxes by position and similarity
jointly. Nothing geometric remains.

**Stage 4.** Needs only `ocr.jsonl` and the PNGs. For each consecutive pair of emitted frames *a*, *b*:

1. **Changed components** by Stage 1's rule over the two PNGs: pixels above θpix, connected components of at least θmin
   pixels. Pixels above θpix outside any such component are noise and are ignored everywhere (there are a median of 2
   to 11 per pair, and the known-good tooltip leaves 13).
2. **Touched boxes.** A box is touched when a pixel of some component lies inside the box grown by the margin
   (`pixel_gate_margin_lines` × the median box height over both frames). The test is on component pixels, not on the
   component's bounding rectangle, so a window border does not touch everything inside it. If a PNG is missing there is
   no pixel evidence: every box is treated as touched and the record says `pixels: null`.
3. **Untouched boxes are unchanged.** Each untouched box of *b* continues the lifetime of the untouched box of *a* it
   overlaps most; a differing OCR text there is a variant reading, not a change.
4. **Same place, same text.** Among touched boxes, a before box and an after box whose rectangles intersect and whose
   texts are equal drop out (counted in `same_place`): something visual changed over unchanged text. They continue
   the lifetime.
5. **Moved.** Texts equal on both sides anywhere in the transition cancel as a multiset, paired in reading order, and
   are counted in `moved`; they continue the lifetime. This is what handles scrolls and window moves, whose lines land
   in different areas.
6. **Groups.** What is left is grouped by rectangle intersection between before and after boxes (connected components
   of the intersection graph; a growing line intersects its shorter self). Each group is classified with whitespace
   removed from both sides: `reread` (equal), `appended` (before is a prefix of after), `truncated` (the reverse),
   `changed` (otherwise). The recorded strings and `char_diff` are exact. A `reread` continues the lifetime and the
   differing text is a variant; the other kinds end one lifetime and start another.
7. **Appeared, removed.** After boxes in no group are `appeared`; before boxes in no group are `removed`.
8. **Textless components** (touching no box in either frame) are counted in `pixels.textless` with their area; they
   yield no record. A transition with only these is what `visual_only` meant in revision 1.
9. **Transients, per area.** A group or appeared box of *a*→*b* is `transient` when, comparing frames *a* and *c* (the
   frame after *b*) directly, no component lies inside its rectangle. When every text-bearing change of *a*→*b* is
   transient, frame *b* is folded: one `transient_merged` transition *a*→*c* whose changes are recomputed between its end
   frames, carrying `transient: {frame, hold_s, texts}`. There is no time gate; `hold_s` is data for Stage 5.
10. **Continues.** A group whose before box is the after box of a group of the previous transition records
    `continues`. It is an exact identity through a shared box, asserts nothing, and merges no Stage 5 calls. Program
    output arrives as new boxes (`appeared`), so it cannot chain with a growing input line by geometry.
11. `trivial` keeps the clock rule on `char_diff`. Boxes flagged `in_churn` by Stage 1 keep the flag on their groups.

Both prototypes of this shape exist (`scratchpad/rebase-prototype/variant.py`, `rebase-review-fresh/boxlevel.py`): five
of six commands entered on an empty prompt come out `appended` (156→157, where OCR drops `PS `, stays an honest
`changed`), the Cloud Shell tooltip becomes `appeared` then `removed`, output is `appeared`, and the 186→187 terminal
scroll cancels 26 moved texts leaving 11 records. Reading order within an area and modify pairing by vertical overlap,
the two geometric rules revision 1 kept, are gone.

**Focus.** Caret attribution and retrospective focus are dropped. `focused_container` is the model's self-report.
Stage 1's blink tracker stays: its job is keeping a blinking cursor from emitting frames.

**Stage 5.** Half-scale frames (L39), one call per non-trivial transition as today (30 for 32 on span 2). The change
text is rendered per group with labels and **the box ids the model may cite**, for example
`[155:b33] PowerShell window: "PS C:\Users\msadmin>" → appended " az login" (readers disagree: OCR "…az login", model
"…a login")`; appeared and removed texts are listed with their ids; moved and textless counts are one line each.
Citations are validated against those ids. The prompt asks for `entered_text` and `submitted` and says that an input
line may show a suggestion the user did not enter. §15.2 is reworded.

**Stage 6.** `hierarchy.py` renders each transition from its Stage 5 action, `entered_text` and `submitted` and its
group texts (today: `typed` and `output_appended` events, `computed_diff`, `regions.appeared`), and each frame's state
line from flat containers and `focused_container` (today: `units()`). §15.3 is unchanged in intent.

**Stage 7 and the agent.** Nodes: one per **lifetime** (both readers' majority texts, every variant, run texts joined
both with `""` and with `" "`, pair text as `key value` tokens with `key` and `value` as fields, first and last time,
container label); one per transition (Stage 5 action and result, `entered_text`, `submitted`, group texts); steps,
sections, video as today. No per-frame copies, so a command on screen for 27 frames is one hit with its first
appearance, and "when did they run X" has an answer. A multi-term query with no single-node match falls back to
per-term hits whose lifetimes overlap in time ("on screen together from … to …"); a deduplicated screen node is added
only if the question set shows that is not enough. `layout_conf` leaves the index columns; the level `region` becomes
`text`. `agent.py` tools return lifetimes, changes and Stage 5 judgments. The agent prompt (§15.4) is reworded from
"quote exact text only from lines marked agree=true" to guidance: quote verbatim where readers agree; where they
differ, or a text is `unstable` or seen once, say so or look at the frame; text on an input line may include a
suggestion; Stage 5's `submitted` is the primary evidence that a command ran, and without it say what was seen and how
sure; time on screen is one piece of evidence. A `get_pairs(key_like, t_from, t_to)` tool is a follow-on.

## 6. Which reading is recorded when the readers disagree (§22 #15)

Span-2 evidence (L43): OCR is right on 52/53 settled rows and 8/16 live rows; the model on 48/53 settled rows (its
errors are off-by-one assignments to boxes, plus `get-credentials` for the displayed `get-Credentials` on 2 of 16
sightings) and 12/16 live rows; disagreement flags 9 of 9 OCR misreads with 10 false alarms in 71; no ensemble was ever
right when no member was; the majority reading over a text's sightings is right for 7 of 7 executed commands for both
readers.

| Option | For | Against |
|---|---|---|
| OCR always (today) | No model normalisation can enter the record | The live command line is recorded wrong half the time, on the core deliverable |
| Model always | Best on live lines | Off-by-one assignment and quiet case normalisation enter the record; undoes R1's guard |
| Pick by rule (near-identical → model) | Cleaner text | A rule that hides exactly where a model "completion" would sit |
| **Record both, pick neither** | Honest; both searchable; agreement stays meaningful; majority per reader fixes first-sighting errors | Two strings to carry; the agent must handle disagreement |

**Recommendation: record both.** A lifetime carries each reader's majority and variants; both are indexed; `agree`
compares majorities; change records show OCR's text of that frame and the model's beside it when they differ. For
commands there is a third, interpretive reading: Stage 5's `entered_text`. The assignment weakness is what arms B–D and
position-and-similarity assignment are for. Google Cloud Vision works with the owner's key and stays an optional third
reader outside the base: it cuts the flag's false alarms from 10 to 4 in 71 but misreads `group=` on all 21 sightings
and must be clipped to a window.

## 7. What is deleted and what stays

| Module | Deleted at the last step | Stays or is new |
|---|---|---|
| `merge.py` | `_row_plausible`, `build_region_lines`, `_make_line`, `align_repair`, `_matches`, `region_associations`, `region_bbox`, `_h`, `_median_h`, `layout_conf` and helpers, `caret_region`, `combine_focus`, `_root` | `agreement` per box, `union`, a small merge writing `boxes.jsonl` |
| `correspond.py` | the whole module, its weights and the 0.3 threshold | — |
| `diff.py` | `diff_region`, `diff_pair`, `_ys`, `_line_h`, `is_gated`, `pixel_gate` | `PixelSource`, `_margin`; new `changes.py` (Stage 4 above) and `lifetimes.py`; Myers stays in `textdiff.py` for `char_diff` |
| `coalesce.py` | `_other_ops_ok`, `_typed_op`, `_output_ops`, `_follow`, `_build`, `retrospective_focus`, `_vlm_focus`, Rules 1, 1b, 2, `merge_transients` as written | `tag_trivial`, `assign_ids`, `_kind` |
| `schemas.py` | `Line`, `Region`, `FrameRecord` unit helpers, `Correspondence`, `RegionDiff`, `DiffOp`, `Event`, `FocusRecord`, the `VlmRegion*`/`VlmPerception*` variants | Stage 1 and OCR records, `PixelChange`; new `Box`, `Container`, `Link`, `Change`, `Lifetime`; `VlmInterpretation` gains two fields |
| `interpret.py` | `render_diff`, `render_transition_line`, `validate_refs` over `line_ids()` | rewritten over groups and box ids |
| `hierarchy.py` | `_state_line` over `units()`, item lines over events | rewritten (§5) |
| `index.py`, `agent.py`, `prompts/agent.py` | region and frame nodes, `region_text`, the `layout_conf` column, the `agree=true` quoting rule | lifetime and transition nodes, the co-occurrence fallback, reworded prompt |
| `prompts/stage2c.py`, `prompts/stage5.py` | the row-mode prompt and its four variants | the prompt of §5; Stage 5 with ids, `entered_text`, `submitted` |
| `diagnostics.py` | `fragment_stability`; the `rows_rejected` and `grouping_repairs` keys | `mark_match` (now per box), costs; `box_stability`, `unstable`, `touched_share` |
| config | `row_y_tol`, `row_gap_lines`, `align_*`, `modify_sim`, `typed_tolerance`, `transient_max_s`, `corr_*`, `pixel_gate_max_fraction`, `stage2c_panes`, `stage2c_rows` | `pixel_gate_margin_lines`, `glyph_max_len` |

`focus.jsonl`, `frames.jsonl` and `transitions.jsonl` go at the last step; existing run directories stop loading; the
commit before the re-base is tagged so L28–L43 stay reproducible.

## 8. Evaluation

**Ground truth, a precondition of any paid phase.** G1: the owner-corrected command list of span 2; the candidate is
`scratchpad/ocr-ensemble/span2-commands-candidate.md` (9 executed commands with frames and times, including `Y` and `y`
at two prompts; 5 predictions that were shown and never run). It moves into `docs/ground-truth/` once corrected. G2,
small and optional: the links of frame 150 (about 31) and the windows and popups of the 11 smoke frames (about 25
entries), drafted from existing runs for the owner to correct. Q: about fifteen questions written from G1, with
negatives ("did they roll back the deployment?", "did they scale the cluster?", "did they run `az login`?" must be
answered no).

**Primary metrics, scored without a model call.** Per executed command: *found* (a lexical search for its exact text
returns a node covering its time); *exact* (some lifetime's majority reading contains it exactly, per reader);
*time error* of first appearance and of submission; and *false run* (never-run predictions that any `submitted: yes`
covers). Then the question set through the agent. **Guards, not rankers:** `box_stability`, `unstable` rate,
`touched_share` on near-static pairs (the per-video alarm for θpix and θmin), boxes in exactly one container, popups
found on frames 149 and 151, repairs, link and container precision and recall against G2, cost. `link_consistency` and
container-name consistency are reported but decide nothing: the first is at its ceiling (194 of 194) and scores 1.0 for
a link that is wrong in every frame, the second ranges 0.39 to 1.00 across identical runs.

**Evidence rules.** Metrics are computed by committed scripts before a phase runs. Comparisons are paired by frame
over the same frames. P1 sets the noise floor; a difference inside it is no difference. Screening uses two repeats;
repeats are added only to finalists, until a difference clears the noise or is declared none. No threshold is
pre-committed: after each phase the results come to the owner and the next phase is planned then.

| Phase | What | Runs | Estimate |
|---|---|---|---|
| P0 | **Free.** Stage 4 and lifetimes on OCR alone over all 221 frames and both spans; primary metrics for the OCR reader against G1; margin 0, 0.25, 0.5, 1.0 for sensitivity; how many lifetimes the pointer or an occluding window splits; the 96.5 % result into a ledger row | — | $0 |
| P1 | Base: arm A, transcribing, full scale, both spans, Stages 5–7 and the question set; 3 repeats. Noise floor; side by side with `runs/span2-before`; per-kind link quality against G2 (the cut of link kinds is made here) | 6 | $25 |
| P2a | Referencing arms B, C, D, transcribing, full scale, smoke span, 2 repeats (A from P1): assignment of readings to boxes, containers and links against G2, cost | 6 | $7 |
| P2b | Arms A–D × scale 1.0, 0.5, 0.25, group-only, smoke span, 2 repeats; then refinement around what looks good (0.67, 0.4, 0.3, 0.2 as warranted) with every arm still alive; the chosen point on span 2, 3 repeats | 24 + about 12 + 3 | $26 |
| P3 | Where the second reading is spent: every box (base, from P1), **only boxes under changed pixels or newly appeared** (read from full-resolution crops; unchanged boxes keep their lifetime's readings), or none; both spans, 3 repeats each | 12 | $20–27 |
| P4 | Pane as a label, on or off, smoke span, 2 repeats: does it change link quality or search-hit usefulness | 4 | $5 |
| P5 | Stage 5 `entered_text` and `submitted` against G1 with half-scale frames (from P1) and with crops (L39: crops kept the suggestion detail); agent prompt wording on the negatives | 3 + agent calls | $5 |

About $90–110 of the $491 if every phase runs as listed; each is reviewed before the next, so later phases may shrink
or vanish. P2b is a cost ablation now that transcription stays on: it prices a Stage 2c that only groups, which P3's
changed-boxes option would make usable, since grouping could then run at a low scale and reading at full resolution on
a handful of crops. Costs: Stage 2c transcribing in boxes mode $0.117 per smoke frame (L41) and about $0.139 on span 2
(more text); group-only about $0.08 at full scale (row mode measured $0.063, plus ids and links), falling with scale;
Stage 5 $0.019 per transition; a question about $0.10. Then a hold-out check (question 4 below), then the full sample,
sync and batch.

## 9. Build order

Each step lands with synthetic-fixture tests and its own commit. The old pipeline keeps running until step 10.

0. Tag the pre-re-base commit. Commit the evaluation scripts for the primary metrics.
1. **Stage 4** (`changes.py`) writing `changes.jsonl` from `ocr.jsonl` and the PNGs. Validate free (P0).
2. **Lifetimes** (`lifetimes.py`), majority readings. Validate free (P0).
3. Schemas `Box`, `Container`, `Link`, `Lifetime`, `Change` beside the old ones; Stage 2c arm A prompt, schema, repair.
4. Stage 3 writing `boxes.jsonl`; labels joined onto changes and lifetimes.
5. Stage 5: rendering with box ids, `entered_text`, `submitted`, citation validation; §15.2.
6. Stage 6 rendering over the new records.
7. Stage 7: lifetime and transition nodes, both joins, pair fields, co-occurrence fallback; agent tools and prompt; §15.4.
8. Diagnostics. P1.
9. Arms B, C, D, group-only, changed-boxes-only transcription and the pane label as evaluation switches. P2–P5.
10. With the owner's go-ahead after P1 is laid beside `runs/span2-before`: switch the CLI to the new path, delete the row
    machinery, its config keys and the losing switches, fold this document into the design as revision 7, ledger rows.

## 10. Risks, remaining constants, watch list

- **θpix and θmin now carry identity for the whole pipeline and were calibrated on this one video** (§7.2, §22 #3).
  The failure is graceful: a noisier encode means fewer vetoes and more OCR jitter reported as change; the index is
  unaffected. `touched_share` on near-static pairs is the per-video alarm.
- **Remaining constants:** the margin (0.5 box heights; P0 varies it), "overlaps most" and "rectangles intersect"
  (no threshold), whitespace-blind labels, reading order only to pair duplicate moved texts. `transient_max_s`, IoU
  cut-offs and the vertical-overlap pairing are gone.
- **No window identity across frames.** Names vary by call; nothing mechanical depends on them.
- **A lifetime ends when its text changes under changed pixels,** so a pointer passing over a box (`891c` ⇒ ` c`), a
  cursor glyph read as text (`(y/n):■`), or an occluding window edge (`Identit` ⇒ `Identity`) splits it and produces
  honest `changed` records. The reviews saw each once. P0 counts them; logic only if the count matters.
- **Moves pair duplicates arbitrarily.** Harmless for text; a lifetime may hop between two identical strings.
- **Links are unproven beyond one frame of one run**, the joiner is a model judgement (hence both joins in the index),
  and pair against record will flip without the tie-break sentence.
- **The changed-boxes-only reading is new in this revision** and unmeasured.
- **Everything measured so far comes from one 14-minute video.**
- **Watch list, no logic until evidence:** low-contrast flicker, re-wrap on resize, text that changes inside an
  unchanged rectangle at sub-threshold contrast, duplicate strings under a scroll, the spacing guard's 0.25 ratio
  (it fired on none of span 2's dropped spaces; `rec_batch_num` 1 may have made it moot).

## 11. Questions for the owner

1. **Correct the command list** (`span2-commands-candidate.md`): it gates every paid phase.
2. **Record both readings and pick neither** (§6): agreed?
3. **The time gate on transients is dropped** in favour of "the pixels came back" plus a recorded `hold_s`. A window
   opened and closed with nothing else happening folds into one transition however long it stayed. Acceptable?
4. **A hold-out recording:** ten frames of a different video (an editor, a dark terminal) for the final check of the
   prompt and of θpix and θmin. Can you supply one?
5. **Is "which window had focus" a deliverable?** If not, the model's self-report goes too.
6. **Delete row mode outright** at step 10, behind the tag? Recommended.
7. **Budget:** about $90–110 for §8, phase by phase, before the full sample run.
