# Proposal: re-base the pipeline on boxes mode

Status: **revision 3.2, 2026-09-21 (evening). Accepted by the owner as the basis of the re-base; built on branch
`rebase-boxes` from the plans under `docs/superpowers/plans/` (ledger L44 onward). Where a reconciled plan and this
document differ, the plan is later and wins; where a plan and the committed code differ, the code wins (L52).**
Revision 3.2 makes this document true of the committed code and of ledger rows L47 to L65; it changes no design.
Revision 1 is commit `0a3135e`, revision 2 `b9b0c0c`; the two reviews of revision 1 are in `docs/reviews/`. This is to
become design
revision 7, a restructuring of `docs/visual-transcript-pipeline-design.md` around new stages and records rather than a
patch to its sections; that rewrite has not been done (§10, step 9). The decoder and settle machine, the optional
Gemini outline, the RapidOCR adapter, the provider, the call cache and `subset` carry over (repaired or extended since:
the outline call, L58; the provider's usage and price accounting, L49; `subset` imports a pre-re-base run directory,
L47). Everything between OCR and the index is written fresh.

## Where the code stands (2026-09-21, evening)

Branch `rebase-boxes` at `63748f0`. Nothing is pushed and nothing is merged: `main` is untouched at the tag
`pre-rebase-boxes` (L44). What is open now is in `docs/open-items.md`.

**Built.** Every stage of §2, run live end to end (L54, L55): `decode`, the optional `outline` (L58), `read`, `track`,
`annotate`, `interpret`, `summarize`, `index`, `ask`, and the evaluation harness `scry eval run`, `judge`, `report`
(L50, L55). `track` has pairs only and one `reverts` record per transition (L45, L51). `annotate` is referencing arm A
with the switches `[annotate] mode` (`every_frame`, `incremental`, `off`), `transcribe` and `scale`; an incremental
call is the every-frame call with fewer targets and carries nothing from an earlier answer (L49), a box that moved is
a target again (L56), and a call with no target is still made, for the description (L62). `interpret` sends its two
frames `scaled` or `full` and is given the descriptions in force (L48, L54). `[model] mode = "batch"` works for
`annotate` and `interpret` (L62). `[ask] frames = false` withholds the pixels from the agent (L62, L65).

**Evaluated.** P0, free: the mechanical layer works and OCR quotes all 7 scorable commands of span 2 exactly (L47). P1:
the three co-equal bases tie on every quality metric and differ tenfold in cost (L57). P2: incremental annotation
matches labelling every frame at well under half the cost and became, transcribing, the working default for the owner to
confirm; the one thing annotation added to an answer was the second reading of a line being edited (L56, L59). P3: the
annotate image scale stays 1.0 (L60). P4 and P4b, the whole 221-frame sample: every base ties again; per video $17.85
for the working default, $12.11 for the same in batch mode (0.68 of the sync price) and $4.62 with no annotation (L62).
P5: arm D lost to arm A (L63). P6, answering from the index with the pixels withheld: annotated 27 of 27, unannotated 26
and a partial; the description carried the difference (L65). P7: Opus 5 stays the model for `annotate` (L64). P8, every
stage on Sonnet 5, was in flight at this writing (L64).

**Removed.** Referencing arm D, behind the tag `arm-d-evaluated` (L63). The overlay's mask modes and `[overlay] scale`
(L49). The `text` mode of `interpret` did not return from the old pipeline (L48). The projected batch price in
reports (L62).

**Unbuilt.** Referencing arms B and C and the assignment of readings by position (L49, L59, L61); the pane label
(L49); the `crops` mode of `interpret`, the `[ask] prompt` registry and paging of the transitions tool (L48); a
description-only mode of `annotate` (L65); the `get_pairs` tool (§6); design revision 7 and the merge to `main` (§10).
The owner's hold-out video has not arrived (§9).

## 0. Revision 3: what changed and why

| Change | Source |
|---|---|
| **Revision 3.2 (2026-09-21, evening):** made true of the committed code and of the ledger since P0: a section on where the code stands; false sentences corrected in place in §2, §4 to §9 and §11; passages on what was never built or was since removed are kept and marked in italics. No design change | L47 to L65 |
| **Revision 3.1 (2026-09-21):** brought into line with the reconciled build plan 1 (ledger L45, L46): pairs only, one record list, no groups, pools, clock rule, `trivial` kind or `confusable` flag; projection counts calls per pixel-changing transition | L45, L46 |
| **Reviewer prototypes are thrown out.** Every number and claim sourced from one is removed and their code is deleted; the implementation is not based on them, compared with them or justified by them. Choices that cited them survive only where they follow from the principles, as hypotheses (§4) that the real implementation's first run tests on its own terms. Future reviews read, reason and run the repository's real code. | Owner ruling |
| **Written as the redesign it is.** Stages are named for what they do and ordered as the design implies; no lines, rows, regions, units, marks or old stage numbers survive. | Owner ruling |
| **`track` (changes and lifetimes) sits before the model stage**: it needs only OCR boxes and pixels. Two options follow, evaluated and not decided: annotate only new or changed boxes (§6), and no annotation at all as the cost floor (§9). | The order; span-2 baseline: 27 of 30 transitions changed under 5 % of the screen |
| **Built on a branch** (`rebase-boxes`), fresh against the new records; nothing imports the old row machinery; `main` and a tag stay runnable. The "new files beside the old" plan is gone. The Apple Vision adapter and its macOS dependencies go too. | Owner ruling |
| **Transients are never folded.** Both transitions stay; a change that undoes the previous one is annotated `reverts` with the hold time. No time constant. | Owner ruling |
| **Focus is not a deliverable.** The model's self-report goes with caret and retrospective focus. | Owner ruling |
| **Persistence is never a correctness mechanism** and never evidence that a command ran. The majority reading survives only as de-noising of repeated readings of the same unchanged pixels. | Owner ruling |
| **Whether the model gives a second reading is not decided.** Transcribing and group-only are co-equal from the first paid phase; everything that exists only with two readings is conditional (§7). | Owner ruling |
| **Cost is an outcome of every phase**, per frame and per video, beside every quality number. The budget (about $470 when the re-base began; about $70 is left after P6 and P8 and is kept for the hold-out video, L64) is pre-approved; phases report as they finish and nothing waits for permission. | Owner ruling |

Revision 2's changes, and where they stand now:

| Status | Revision 2 change |
|---|---|
| Kept | Per-box change records, moves cancelled, whitespace-blind labels over exact strings (now H2–H4); one record shape (H5); `continues`; flat containers, no container events; lifetimes as the index unit, both joins, pairs as fields; `entered_text`, `submitted`, citable box ids; a guiding agent prompt; ground-truth evaluation with evidence rules; arms alive through the scale sweep; L43's RapidOCR settings |
| Reversed | "Transcription stays on in the base" (now undecided, co-equal arms); the transient folded without a time gate (now never folded); new files beside the old (now a branch) |
| Subsumed | Transcribing only changed boxes (by incremental annotation) |

*As of revision 3.2, "arms alive through the scale sweep" did not hold: the sweep (P3) ran on arm A alone, arm D was
swept in P5 and removed, and arms B and C were never built (L59, L60, L61, L63).*

## 1. Purpose and evidence

Today's pipeline rebuilds every frame from scratch with a model call and diffs two independent reconstructions, so
instability in the reconstruction reads as change. Every fix since the first live run has patched that seam. The
evidence below is only from real pipeline runs (the ledger), the box-stability measurement, the OCR investigations
against hand-built ground truth, and the cold span-2 baseline.

| Finding | Source |
|---|---|
| The model split one page into 8 panes in one frame and 3 in the next; panes "appeared" on a static screen. | L31 |
| On the five near-static smoke transitions the real pixel gate dropped 81 of 96 structural ops as sitting on unchanged pixels; on span 2 it dropped 557, and 27 of 30 transitions changed under 5 % of the screen. | L32, `runs/span2-before` |
| One knob, the row gap cap, moved agreement from 0.365 to 0.752 on the same data. | L37, L41 |
| A one-line window that is rewritten and grows falls under the 0.3 window-matching threshold and is reported as gone. | L31 |
| The typed event was blocked first by OCR whitespace jitter, then by a phantom box-less line in another window through the nothing-else-changed clause. | L29, L35, L41 |
| Each OCR box as its own unit with model-proposed associations runs end to end (31 groups on frame 150, +20 % on the per-frame call); the same run shuffled ids on a dense tab strip. | L41 |
| RapidOCR boxes are stable: on unchanged pixels 96.5 % of 766 boxes recur with the same rectangle and text; 1.6 % read differently in place (icon glyphs, spacing flips); 0.9 % split, merge or resize; 1.6 % vanish or appear. | `scratchpad/box-stability/result.txt` |
| Today's pipeline on span 2 (frames 155–187, cold, $4.59): one typed event for nine executed entries, recorded wrong (`azconfigure --defaultsgroup=…`); the interpretation call narrated most commands correctly from the frames; 53 invalid citations over 30 transitions, because its prompt never names the ids it may cite. | `runs/span2-before` |
| OCR reads text that is not being edited well (52 of 53 prompt lines exact) and a line being edited badly (8 of 16; 3 of 11 with the shell's suggestion on the line). The model reads those better (12 of 16) and misassigns readings to a neighbour more often (48 of 53). Their disagreement flags 9 of 9 OCR misreads with 10 false alarms in 71; OCR confidence flags none. Five texts on input lines were suggestions that were never run. | L43 |
| Identical cold runs differ: repairs 5–13, a tooltip comes and goes. | L42 |
| Cost today: about $30 for the 14-minute sample (221 frames), about $2 per minute of video, of which the per-frame model call is about $25. | L35, L39, `runs/span2-before` |

The common cause is that **model-proposed structure carries identity**. The re-base moves identity onto what is measured.

## 2. The pipeline, reordered

In the old design the diff came after the model call only because it diffed the model's rows and regions. It now needs
boxes and pixels, so it moves ahead of the model, and the model stage becomes labelling that can be partial or absent.

| Stage | Does | Reads | Writes | Model |
|---|---|---|---|---|
| `decode` | One frame per settled screen state | the video | `frames/`, `frames.jsonl` | no |
| `outline` (optional) | Coarse chapters from Gemini | the video | `outline.json` | Gemini |
| `read` | OCR: boxes per frame | frames | `boxes.jsonl` | no |
| `track` | What changed between consecutive frames, and each box's lifetime | boxes, frames | `changes.jsonl`, `lifetimes.jsonl` | no |
| `annotate` | Labels: containers, links, optionally a second reading | frames, boxes; lifetimes and changes when incremental | `annotations.jsonl` | yes |
| `interpret` | What the user did in each transition | frames, changes, annotations if any | `interpretations.jsonl` | yes |
| `summarize` | Steps, sections, the video | interpretations, changes | `steps.jsonl`, `sections.jsonl`, `video.json` | yes, text only |
| `index` | Searchable nodes | lifetimes, changes, interpretations, summaries, annotations | `index.sqlite` | no |
| `ask` | The answering agent | the index, frames | — | yes |

What the order makes possible, as options the evaluation prices:

- **`track` is free**, so it is built first and run over all 221 frames before any money is spent (§9, P0): the
  pipeline's order, not a build trick.
- **Incremental annotation.** `annotate` labels only the boxes whose lifetime starts at the frame (new or changed text)
  or continues there by a move (L56); an unchanged box carries its labels along its lifetime. A call is made whenever
  pixels changed, even if no box did, because the screen `description` (below) must be refreshed when a toggle, a
  selection or an icon changes; a transition with no changed pixel makes no call and the previous description carries
  over. The first frame and a cut are the same rule with every box new, so no threshold separates "full" from
  "incremental".
- **No annotation.** `interpret` sees the frames and the change records, so the pipeline runs end to end without
  `annotate`: no containers, links or second reading, and none of the $25. It is the cost floor and the measure of
  what annotation buys.

Every stage writes only its own file; loaders join labels onto measured records on read. Measured facts and model
proposals therefore never share a file.

## 3. Vocabulary

One name for the design: **boxes mode**.

| Term | Meaning | Source |
|---|---|---|
| **Box** | One OCR detection: text and a rectangle. The unit of identity, change, citation and agreement. | measured |
| **Reading** | A text for a box from one reader: `ocr` always, `vlm` when `annotate` transcribes. | measured / model |
| **Lifetime** | A box followed across consecutive frames while it stays the same text: on unchanged pixels, moved, or re-read with only whitespace differing. It has a majority reading per reader, the variants, and first and last frame and time. The index unit. | measured |
| **Change record** | One changed box: a pair of an earlier and a later box that intersect, at least one of them under changed pixels, with a kind, the exact before and after strings and a character diff; or a single box that appeared or was removed. | measured |
| **Container** | A window or a popup. Flat: containers do not nest. A popup may name its owner window. A label. | model |
| **Link** | A typed relation among boxes of one container: `run`, `pair`, `record`. A label. | model |

| Old | New |
|---|---|
| Stage 1; Stage 0 | `decode`; `outline` |
| Stage 2a, `ocr.jsonl`, mark, OCR line, `l<n>` | `read`, `boxes.jsonl`, box, `b<n>` |
| Stage 4, 4b, `transitions.jsonl`, `computed_diff`, `DiffOp`, unit line lists, row banding | `track`, `changes.jsonl`: `records`, `moved`; `lifetimes.jsonl` |
| Stage 2b, 2c, 3, `perception.jsonl`, `frames.jsonl` (merged), `focus.jsonl` | `annotate`, `annotations.jsonl`; `frames.jsonl` now names `decode`'s records |
| row, row line, line, `Line`, `rows`, `vlm_lines` | box; a split text is a `run` link; `texts` |
| region, unit, pane, `Region`, `r<n>` | container `c<n>` (window or popup); pane is at most a label string |
| association | link |
| VLM-only line `v<n>` | missed text `m<n>` (no rectangle; citable, never in a change) |
| `typed`, `output_appended`, `coalesced`, `transient_merged` | kinds on change records; `continues`; `reverts`; `entered_text`, `submitted` from `interpret` |
| region correspondence, `matched`, focus signals | removed |
| Stage 5, 6, 7, the agent | `interpret`, `summarize`, `index`, `ask` |
| per-frame region and frame index nodes | whole-screen entries per frame (kept) plus lifetime entries (added); duplicates collapsed at query time |
| `rows_rejected`, `fragment_stability`, `layout_conf` | removed; `box_stability`, `unstable`, `touched_share` |
| citation `"<frame>:<line_id>"` | `"<frame>:<box_id>"` |

"Line" survives only as a plain word for what a person sees in a terminal.

## 4. Principles and hypotheses

1. **Measured things carry identity; model-proposed things are labels.** Boxes and pixels decide what exists and what
   changed. Containers and links never gate, are never diffed, never alter recorded text. A wrong label costs an
   enrichment, never a fake change.
2. **A box with no changed component under it is unchanged**, at any changed fraction.
3. **Honest text-change contract.** The mechanical layer reports that text appeared, changed, moved or was removed at
   a location (a rectangle, a frame pair, a time), with before, after and a character diff. It never says "typed" and
   never separates suggestions, program output or paste. No cursor or suggestion locating, no brightness thresholds.
4. **Whether something was done is interpretation.** `interpret` sees the frames and says what the user entered and
   whether it was submitted. How long a text stayed on screen says nothing about whether it was run: a command can be
   entered and the window minimised, and a one-line terminal shows no history.
5. **Record, do not pick.** Every reading is kept with its counts. Repeated readings of the same unchanged pixels are
   de-noised by majority; a text seen once has its one reading.
6. **Two levels of screen structure:** container and box, plus links. No UI element tree (design §1.4). The temporal
   hierarchy (video, sections, steps, transitions, frames) is unchanged.
7. **No constants from the sample video**, and no logic for a case until the real implementation shows the case. The
   constants that remain are listed in §11.
8. **Evidence rules, not success thresholds** (§9). Cold runs with repeats for anything that judges a model call;
   cached outputs only downstream of a fixed output.
9. **Cost is an outcome.** Every result carries dollars per frame and per video.

**Hypotheses.** These choices follow from the principles and, when this was written, nothing admissible had tested
them. P0 tests each on its own terms: by reading the records against the frames of both spans, and by the command
metrics of §9.

*P0 has since run (L47). None was refuted outright. H8's test per component missed one of the two tooltips and wrote
1,249 entries in 82 transitions, so a revert became one record per transition (L51). What P0 showed against H2, H3 and
H4 (unrelated texts married by place when a page is replaced, equal strings that are different things paired as moves,
a kind label defeated by an icon glyph) was left alone as minor and honest (L51).*

| | Hypothesis | Follows from |
|---|---|---|
| H1 | The veto is sound at any changed fraction: a differing OCR text on unchanged pixels is a re-read. | Principle 2; the differences the box-stability result lists are glyph and spacing noise |
| H2 | The box is the unit of a change record; a changed box pairs one to one with the box of the other frame it intersects most, touched or not, so a growing text matches its shorter self and a shrinking text its longer self. | Principle 1: joining every box near a change mixes unrelated boxes |
| H3 | Equal texts on both sides of a transition are moves, cancelled across the whole transition; scrolls and window moves become small. | A scroll changes every pixel and no text |
| H4 | Kind labels computed with whitespace removed are useful conveniences; the exact strings are the record. | L35, L43: OCR spacing jitters on the same text |
| H5 | One record shape serves a keystroke and a page load; no large-change mode is needed. | Principle 7 |
| H6 | Touch is tested on a component's pixels, not its bounding rectangle. | A window outline's rectangle covers its whole interior |
| H7 | Lifetimes do not fragment so much that duplicate search hits return. | Box stability 96.5 % on unchanged pixels |
| H8 | A change that undoes the previous one is found by comparing the frames on either side of it directly. | No time constant needed |

## 5. Records

`frames.jsonl` is `decode`'s record per emitted frame, unchanged in content. `boxes.jsonl`, from `read`:

```json
{"frame": 155, "png": "frames/00155.png",
 "engine": {"engine": "rapidocr", "version": "3.9.2", "use_cls": false, "rec_batch_num": 1, "…": "…"},
 "boxes": [{"id": "b33", "bbox": [659, 352, 904, 371], "text": "PS C:\\Users\\msadmin> az login", "conf": 0.98,
            "words": [{"text": "PS", "bbox": [659, 352, 679, 371]}], "in_churn": false}]}
```

`engine` is the OCR adapter's whole settings record. The OCR wall time is in the manifest and not in this file, so
that the file's hash, which every later stage checks, does not change between identical runs (L56).

`changes.jsonl`, from `track`, one record per transition (values illustrative):

```json
{"id": "T9", "from_frame": 154, "to_frame": 155, "t": [598.7, 620.7], "kind": "single",
 "pixels": {"changed_fraction": 0.0002, "components": 2, "textless": 1, "textless_area": 64,
            "touched_share": 0.0113, "rect_only": 0},
 "records": [{"kind": "appended", "rect": [659, 352, 904, 371],
              "before": {"box": "154:b31", "text": "PS C:\\Users\\msadmin>"},
              "after": {"box": "155:b33", "text": "PS C:\\Users\\msadmin> az login"},
              "char_diff": [["=", "PS C:\\Users\\msadmin>"], ["+", " az login"]],
              "continues": null, "in_churn": false}],
 "moved": [], "same_place": 1, "unchanged": 131, "variants": 0,
 "flicker_new": [], "flicker_lost": [], "reverts": null}
```

- `records` is one list with one change record per changed box: a pair of an earlier and a later box (kinds `reread`,
  `appended`, `truncated`, `changed`), or a single box that `appeared` (`before` null) or was `removed` (`after`
  null). A pair carries the exact before and after strings and the character diff of that pair only. `rect` is the
  union of the two boxes, or the single box's own; `in_churn` is set when either box carries `decode`'s flag. Pair and
  `appeared` records come first, in the later box's reading order, then `removed` records in the earlier box's.
- One shape for every size (H5). A keystroke is one record. A page load is many `appeared` and `removed` records. A
  scroll is mostly `moved`.
- `moved` lists the cancelled moves as (earlier id, later id) pairs, for example `["154:b12", "155:b11"]`.
  `same_place` counts the pairs at the same place with exactly the same text (something visual changed over unchanged
  text): a count, not a kind. `unchanged` counts the untouched pairs and `variants` those of them whose OCR texts
  differ. `flicker_new` and `flicker_lost` list the untouched boxes left without a partner: no record, counted.
- `continues` names the record of the previous transition whose `after` box is this record's `before` box, written
  `"T8/0"` (the change id and the index in its `records`), whatever that record's kind; null otherwise.
- `pixels` is null when a PNG is missing or the two frames differ in size. `textless` and `textless_area` count the
  components that touch no box of either frame and sum their areas; `touched_share` is the touched boxes over all
  boxes of the two frames; `rect_only` counts the boxes that a component's bounding rectangle reaches and its pixels
  do not (what P0 reads for H6).
- `reverts` is one record per transition, or null (L51): `{"of": "T4", "share": 0.93, "hold_s": 3.4}`, where
  `share` is the share of the pixels the previous transition changed that are back to what they were before it, and
  `hold_s` is how long the previous change stood. It is recorded whenever the share is above zero; there is no
  threshold and no rectangle. Both transitions stay and both are interpreted.
- Transition kinds: `single`, `unsettled` (either frame is not settled).

`lifetimes.jsonl`, from `track`, measured fields only (frames illustrative):

```json
{"id": "L412", "text": "PS C:\\Users\\msadmin> az configure --defaults group=RG1-KodeKloud-AKS",
 "readings": {"PS C:\\Users\\msadmin> az configure --defaults group=RG1-KodeKloud-AKS": [161, 162, "…", 187],
              "PS C:\\Users\\msadmin>azconfigure --defaultsgroup=RG1-KodeKloud-AKS": [174]},
 "unstable": true, "sightings": 27, "first": {"frame": 161, "t": 649.2}, "last": {"frame": 187, "t": 721.0},
 "moved": true, "boxes": ["161:b40", "…"]}
```

`readings` maps each OCR reading to the frames at which it was sighted, ascending, so the frame where a variant
occurred can be opened. `text` is the majority OCR reading: the reading sighted at the most frames, a tie going to the
reading sighted first. `unstable` means OCR gave more than one reading of the same pixels, a measured fact the agent
can hedge on with no second reader. `sightings` is the number of boxes. `first` is the first box's frame with that
frame's `t_settled`; `last` is the last box's frame with that frame's `t_end`.

`annotations.jsonl`, from `annotate`, one record per call:

```json
{"frame": 155, "targets": ["b33"],
 "containers": [{"id": "c2", "kind": "window", "app": "PowerShell", "name": "Administrator: PowerShell 7-preview (x64)",
                 "owner": null, "covers": ["c1"], "rect": null}],
 "assign": [{"box": "b33", "container": "c2", "pane": null}],
 "links": [{"kind": "pair", "key": ["b28"], "value": ["b29"]},
           {"kind": "run", "boxes": ["b61", "b62"], "joiner": ""},
           {"kind": "record", "members": [["b70"], ["b71"], ["b72"]], "header": ["b64", "b65", "b66"]}],
 "texts": [{"box": "b33", "text": "PS C:\\Users\\msadmin> a login"}],
 "missed": [{"id": "m1", "text": "Networking", "container": "c1"}], "unassigned": [],
 "description": "The Overview item is highlighted in the left navigation; the Properties tab is selected; …",
 "repairs": 0, "repair_counts": {}, "label_clashes": 0, "model": "claude-opus-5", "prompt_version": "annotate-v4",
 "usage": {}, "error": null}
```

- `targets` is every box of the frame, or, when incremental, only the boxes whose lifetime starts at the frame or
  continues there by a move (L49, L56); it can be empty (L62). A box's labels come from
  its own frame's record, else from the latest record of its lifetime.
- `texts` exists only when transcribing. The loader then derives per box `vlm`, `agree` (exact equality after
  normalisation, icon-glyph strip kept) and `non_text` (the model returned `""`, so the box leaves agreement
  denominators; it stays in the index from OCR, and the flag is payload only, L48), and per lifetime the model's
  majority reading.
- `rect` was for the arms where the model draws containers (§6); they were never built, so it is always null (L61). A
  box is in at most one link. Container membership does not gate a link (L49, under principle 1): a link is dropped, and
  counted, only when it names an unknown box, is not a link at all, or names a box already in a link. A key and value
  that OCR put in one box can never be a pair: pairs enrich, they are not a table of properties.

`interpretations.jsonl` keeps action, result, description, confidence and citations, and gains `entered_text` (the text
the user has entered in the input being edited, as it stands in the later frame, without anything the application
suggested; the whole submitted text on a transition that shows a submission; null when nothing; L48) and `submitted`
(`yes`, `no`, `unclear`: whether what was entered took effect).

## 6. Stage by stage

**`read`.** RapidOCR 3.9 with `use_cls` off and `rec_batch_num` 1 (L43). No second pass, upscale, normalisation,
English model or OCR ensemble. Google Cloud Vision works with the owner's key and stays an optional extra reader
outside the base; no adapter for it is on the branch (`[read] engine` accepts only `rapid`).

**`track`.** For each consecutive pair of emitted frames *a*, *b*:

1. **Changed components** by `decode`'s rule over the two PNGs: pixels differing by more than θpix, in connected
   components of at least θmin pixels. Changed pixels outside any component are ignored.
2. **Touched boxes.** A box is touched when a pixel of a component (H6), not merely the component's bounding
   rectangle, lies inside the box grown by the margin. The margin is relative: half the median box height over the
   boxes of both frames. With a PNG missing, or two frames of different sizes, every box is touched and `pixels` is
   null.
3. **Untouched boxes are unchanged** (H1), at any changed fraction. Untouched boxes of *a* and *b* that intersect are
   matched one to one, greedily by intersection area with ties by reading order (the one matching rule, used again in
   steps 4 and 6). A matched pair is unchanged and continues the lifetime; a differing OCR text there is a variant
   reading, counted, never a change.
4. **Same place, same text.** Of the boxes left, a before box and an after box that intersect, read exactly the same
   string and of which at least one is touched drop out, matched one to one and counted in `same_place`: something
   visual changed over unchanged text. They continue their lifetimes.
5. **Moved** (H3). Then texts exactly equal on both sides, anywhere in the transition, cancel: the k-th occurrence of
   a string among the remaining touched before boxes pairs with its k-th occurrence among the remaining touched after
   boxes, up to the smaller count. Only touched boxes can move: an untouched box has not moved (H1). Each pair is
   listed in `moved` as (earlier id, later id) and continues its lifetime. Reading order is used only to pair
   duplicates of the same string.
6. **Pairs** (H2). The remaining boxes pair symmetrically and one to one: the candidates are every remaining before
   box with every remaining after box it intersects, provided at least one of the two is touched, taken greedily by
   intersection area with ties by reading order. The partner may be untouched, in either direction: a growing text's
   shorter self usually lies outside the changed pixels, and so does a shrinking text's. Each pair is one change
   record. Its kind is computed with whitespace removed (H4): `reread` (equal), `appended` (before is a prefix of
   after), `truncated` (the reverse), `changed` (otherwise). Recorded strings and `char_diff` are exact and cover that
   pair only. A `reread` continues the lifetime with a variant; the other kinds end one lifetime and start another.
7. **Appeared, removed, flicker.** A touched after box left without a partner is an `appeared` record; a touched
   before box left without a partner is a `removed` record. An untouched box left without a partner is flicker:
   nothing changed there, so it yields no record; its lifetime starts or ends silently and it is counted in
   `flicker_new` or `flicker_lost`.
8. **Textless components**, touching no box in either frame, are counted with their area and yield no record.
9. **Reverts** (H8), once per transition (L51). *z* and *b* are compared directly: of the pixels the previous
   transition *z*→*a* changed, the share at which *z* and *b* do not differ. When that share is above zero, *a*→*b*
   records `reverts` with the share and the hold time, the time from the one change to the other. It is a share of
   pixels, so a revert is found even when something else changes in the same transition. No threshold, no time
   constant; nothing is folded. (The first version tested each component and recorded its rectangle; P0 showed it
   missing a tooltip whose pointer left with it and writing 205 entries for one scroll, L47.)
10. **Continues.** A record whose before box is the after box of a record of the previous transition records
    `continues`, naming that record, whatever its kind (`appeared` included): an exact identity through a shared box
    that asserts nothing. New output arrives as new boxes, so geometry cannot join it to a growing input text.
11. **Lifetimes.** Every box of the first frame starts a lifetime. An unchanged, same-place, moved or `reread` pair
    continues the earlier box's lifetime and records the later frame under the later box's reading. Every other after
    box starts one: the later box of an `appended`, `truncated` or `changed` pair, an appeared box, a new flicker box.
    A lifetime that is not continued stops. The majority reading, `first` and `last` are as §5 defines them.

A transition is `unsettled` when either frame is not settled, else `single`. A record with a box that `decode` flagged
`in_churn` keeps the flag.

**`annotate`.** One call per frame; or, when incremental, one for the first frame and one for every frame whose
incoming transition changed pixels, with or without targets (L62). Draft system prompt for
referencing arm A, with the transcription paragraph present only when transcribing:

*The prompt as built is `src/scry/prompts/annotate.py`, version `annotate-v4`. It differs from this draft: links are
returned as three lists (runs, pairs, records); a link must include at least one target; a box id is in at most one
link and a wrapped side of a pair goes inside the pair (L53); separate lines, rows and menu items are not a run and a
pair needs two different boxes (L57); the description never mentions box ids or targets (L56, L59). The draft is kept
as history.*

```
You label screenshots of computer tutorials (terminals, code editors, browsers, dialogs).

You are shown the same screenshot twice. Image 1 is the clean frame. Image 2 is the same frame with a numbered box
around every piece of text an OCR engine detected; each number sits beside its box and is NOT part of the screen.
A number is written as a box id: b1, b2, ...

containers: the windows (top-level application windows) and popups (menus, dialogs, tooltips, toasts) on screen.
Containers do not nest. Anything drawn over a window is its own popup, never part of what it covers; a popup may name
the window it belongs to as owner. Give each container's application and name and the containers it covers.

assign: for every target box id, the container it belongs to. Every target appears exactly once, or in unassigned.

links: relations between boxes of one container.
  run: boxes that are one continuous piece of text which the OCR engine split or the screen wrapped onto the next
    line, in reading order. joiner is "" when a word was cut in two by the wrap, " " otherwise.
  pair: a label and its value (a property and its value, a form field and its content). key and value are lists of
    box ids. A two-column grid of labels and values is pairs, not records.
  record: one row of a table with three or more columns: members, left to right, each a list of box ids; header,
    the box ids of the column headings when they are visible.
Boxes that merely sit side by side stand alone: tabs, toolbar buttons, menu items, breadcrumbs.

[transcribing] texts: for every target box id, the verbatim text inside that box, read from Image 1. Preserve case,
punctuation, whitespace and symbols. Never correct, complete or normalize commands, code, paths or identifiers. Use ?
for a character you cannot resolve. An icon is not text: give "". missed: text no box covers, with its container.

description: what the boxes cannot express about this screen: selections, highlights, toggles, checked boxes,
icons, diagrams and their relationships, dialogs, progress indicators, anything animating. Plain prose.
```

The `description` is kept from today's prompt at the owner's instruction (2026-09-21): it is purely additive, costs
about half a cent per frame, and is the only place non-textual screen state becomes searchable at moments when
nothing changes. Revision 3's draft dropped it without cause.

When incremental, the call is the every-frame call with a shorter target list: the same system prompt, schema and
images, and nothing from an earlier answer, so no known containers and no neighbours (L49, which departs from this
section's first wording). A link must include at least one target and may name boxes that are not targets; on read, a
link that names a box already in a link in force is refused and counted (`relinked`). Output lists are lists of
objects, never arrays parallel to an id list. Validation is repair, never abort: unknown ids, second assignments and
links naming unknown or already-linked boxes are dropped, an unplaced target goes to `unassigned`; all counted. A link
across two containers is not dropped (L49).

*Of the four arms below only A is in the code. D was built, evaluated in P5, lost and was removed behind the tag
`arm-d-evaluated` (L61, L63). B and C were never built, although the owner said he wanted position-based assignment
evaluated (L59, L61); that is open in `docs/open-items.md`. The scale sweep ran on arm A (P3, L60) and arm D (P5).*

Referencing arms, all kept alive through the scale sweep (L42 showed an arm that is neutral at full scale helping at a
reduced one):

| Arm | Images | The model returns | Code does |
|---|---|---|---|
| A | clean + numbered overlay | box ids | — |
| B | clean + numbered overlay | a rectangle per container; links and texts by id | assigns boxes by centre-inside, front-most container wins |
| C | clean only | a rectangle per container; links and texts as points | assigns by centre-inside; snaps each point to the nearest box |
| D | clean only, plus OCR's box coordinates as a text list | box ids | — |

OCR's coordinates serve code in: box numbering, the overlay, `track`'s touch and intersection tests, the spacing
guard and `box_stability`. Arm D's list, assignment and snapping (arms B, C) and crops for `interpret` were further
planned uses; none of them is in the code (L48, L61, L63).

*Tried since: labels as good as labelling every frame at well under half the cost, and one wrong label seen carried
for an 11-frame lifetime (L56, L59). It is the working default, for the owner to confirm (L59, L65).*

**Risks of incremental annotation, stated before it is tried.** A wrong label is carried for a whole lifetime, not
re-drawn each frame. A container can change with no box changing (a window renamed, a textless popup); a call is still
made, because pixels changed, but it has no target box, so only the description can record it. The first frame and every
cut are full calls, so a video of cuts saves nothing. A link between a new box and an old one can only be proposed by a
call in which one of them is a target, since the call carries no context (L49). Nothing is re-annotated, so label noise
is invisible within a run.

**`interpret`.** Half-scale frames (L39; `[interpret] images = "scaled"`, the other mode being `"full"`; the `text` mode
is dropped and `crops` is not built, L48), one call per transition; nothing is folded, so a tooltip costs two calls. The
change text is rendered per change record with the box ids the model may cite and with labels when annotations exist,
for example `[155:b33, 154:b31] PowerShell window: "PS C:\Users\msadmin>" → appended " az login"; now "PS
C:\Users\msadmin> az login"`; a `changed` record reads "at this place X was replaced by Y", because the two texts may be
unrelated (L51); the model's reading sits beside OCR's where two readings differ; appeared and removed texts carry their
ids; moved and textless counts are one line each; a `reverts` record reads "Undoes 93% of T4's change after 3.4 s."
(L51). When annotations exist the call is also given the screen descriptions in force at its two frames (L54). Citations
are validated against those ids. The prompt asks for `entered_text` and `submitted` and says an input field may show a
suggestion the user did not enter.

**`summarize`.** Renders each transition from its interpretation (action, `entered_text`, `submitted`) and its
change records' texts, and a frame's state from its containers when annotations exist. Intent unchanged.

**`index` and `ask`.** Nodes: one per **lifetime** (the majority reading of each reader, every variant, run texts
joined both with `""` and with `" "` so a wrong joiner cannot hide a command, pair text as `key value` tokens with
`key` and `value` as fields, first and last time, container label when there is one); one per transition (action,
result, `entered_text`, the change records' texts; `submitted` is in the entry's payload and not in its text, since
"yes" and "no" match everything); steps, sections and the video as today.

**Whole-screen entries stay, one per emitted frame** (owner, 2026-09-21: nothing findable today may become unfindable):
every box's text in reading order plus the screen `description` in force at that frame, so a query whose terms sit in
different boxes or windows still matches one document and ranks as it does today, and non-textual state stays
searchable. Lifetime entries are additive: they give an exact string once, with its first and last time, its majority
reading and its variants. The duplicate problem is solved where it arises, in the result list, not by deleting entries:
hits from consecutive frames whose matching measured text (the OCR texts of the matched boxes) is identical are
collapsed into one hit with a frame and time range (L54; in the old pipeline the same static line was returned once per
frame and crowded other results out of the top k: the smoke index held 67 region nodes for 11 frames of three screens).
Nothing about a frame becomes unreachable: `ask`'s frame tool returns the image, the texts alive at that frame and the
description in force; with `[ask] frames = false` it returns the same record without the image, and the tool that
re-decodes the video is not offered (L62, L65). `ask`'s tools return lifetimes, changes and interpretations. Its prompt
guides and does not prohibit: quote verbatim where independent readers agree; where they differ, or a text is `unstable`
or seen once, say so or look at the frame; an input field may show a suggestion; `submitted` is the primary evidence
that a command ran, and without it say what was seen and how sure; time on screen is not evidence either way. A
`get_pairs` tool is a follow-on (not built).

## 7. If two readings survive: which is recorded (design §22 #15)

Conditional on the evaluation keeping the model's second reading. For it (L43): the model reads a line being edited
better (12 of 16 against 8 of 16), disagreement flags 9 of 9 OCR misreads with 10 false alarms in 71, and no OCR-side
remedy (second pass, upscaling, normalisation, other models, an ensemble with Cloud Vision) was right where no single
reader was. Against it: about half the per-frame cost, and readings assigned to a neighbouring box (48 of 53), which
arms B–D and assignment by position and similarity together were meant to fix. None of those is in the code (L49, L61,
L63); what was done instead is the tag-placement fix of L53, after which readings on the wrong box fell from 29 to 7
on frames 145 to 155 (L54).

| Option | For | Against |
|---|---|---|
| OCR always (today) | No model normalisation can enter the record | A line being edited is recorded wrong half the time |
| Model always | Best on those lines | Wrong-neighbour assignment and quiet case normalisation enter the record |
| Pick by rule (near-identical → model) | Cleaner text | The rule hides exactly where a model "completion" would sit |
| **Record both, pick neither** | Honest; both searchable; exact agreement stays the only "quote verbatim" signal | Two strings to carry; the agent must handle disagreement |

**Recommendation if two readings survive: record both.** Also conditional on that outcome: `agree` and `non_text`,
indexing both readings, assignment by position and similarity, and `mark_match`. With one reader, `unstable` is the
only hedge and `entered_text` the only second opinion on a command.

*As built: both readings are recorded and both are indexed; `agree`, `non_text` and `mark_match` exist; assignment by
position and similarity is deferred (L49). Whether the second reading survives is still the owner's decision:
incremental transcribing is a working default (L59, L65).*

## 8. Removed, kept, new

The branch's first commit removes the old row machinery, so nothing can import it; `main` and the tag
`pre-rebase-boxes` hold the runnable old pipeline for before-and-after comparison. The removal reaches `main` when the
branch merges.

| | Modules and keys |
|---|---|
| **Removed** | `merge.py`, `correspond.py`, `coalesce.py`, `perceive.py`, `interpret.py`, `hierarchy.py`, `diff.py` (its pixel comparison is rewritten inside `track`), node extraction in `index.py`, `agent.py` and the four prompt modules (the loop and the prompts return with `ask`, `interpret` and `summarize`; build plan 1's "Returns with" table lists everything removed on the branch and the plan that restores it), `diagnostics.py` except cost accounting; every schema from `Line` and `Region` to `Transition` and the `Vlm*` variants; `perception.jsonl`, the merged `frames.jsonl`, `transitions.jsonl`, `focus.jsonl`; the `[merge]` and `[diff]` config keys, `transient_max_s`, `stage2c_*`; their tests |
| **Removed, not row machinery** | the Apple Vision adapter `ocr/vision.py`, its test and the PyObjC dependencies (the deployment target is not Apple hardware; not the default since L36) |
| **Kept** | `decode.py`, `detect.py`, `settle.py`, `stage1.py` (renamed for `decode`), `ocr/rapid.py`, `overlay.py`, `outline.py`, `providers/`, `run.py` (new loaders), `subset.py`, `config.py`, `env.py`, `jsonl.py`, `textdiff.py` (normalisation, Myers for `char_diff`), `agreement` per box, cost accounting, the search and fusion code of `index.py` |
| **New** | `read`, `track` (changes, lifetimes), `annotate`, `interpret`, `summarize`, `index` node extraction, `ask` tools and prompt; schemas `Box`, `Change`, `Lifetime`, `Annotation`, `Container`, `Link`, `Interpretation`; config `margin` (box heights), the annotate switches `mode`, `transcribe` and `scale` (of the switches of §9 the arm and the pane label were not built), `[ask] frames` (L62); the evaluation harness `src/scry/evaluation/` (L50, L55) |

Existing run directories do not load on the branch; `decode`'s output is reused by importing it with `scry subset`,
which reads a pre-re-base directory (as P0 did, L47), or by re-running it (free, under five minutes for the sample).

## 9. Evaluation

**Ground truth.** G1, the precondition of every paid phase: the command list of span 2,
`docs/ground-truth/span2-commands.md` (9 executed entries with frames and times, accepted by the owner on 2026-09-21,
and 5 suggestions that appeared on screen and were never run, kept as a scoring key only). G2: label quality (links,
windows and popups) is judged by eye on samples, per the owner; if it comes to matter the owner will correct a drafted
list later and the numbers are re-run against it. Q: about fifteen questions written from G1, with negatives ("did they
roll back the deployment?", "did they run `az login`?" must be answered no). Two further sets were drafted from the
frames when the first could not tell the bases apart: 18 graphical questions on frames 145 to 155 (L57, L59) and 27
questions on the whole video (L59, L62). All three are drafts that await the owner's correction (`docs/ground-truth/`).
The owner is preparing a second, different video as a hold-out.

**Primary metrics, scored without a model call.** Per executed entry: *found* (a lexical search for its exact text, as a
phrase, returns within the first 20 hits a lifetime, frame or transition entry whose frame range meets the frames from
first visible to submitted; a summary hit is shown and not counted; L50, L55) and *exact* (some lifetime's majority
reading contains it exactly, per reader); these two rank alternatives. **Secondary** (owner's ruling: run against
not-run matters less than finding and quoting): *frame error* of first appearance and of submission (every comparison
with the list is by frame number, never by seconds, L50), *submitted* (a `submitted: yes` interpretation whose
`entered_text` equals the command), and *false run* (never-run suggestions covered by a `submitted: yes`); they are
reported beside the primary scores and break ties, no more. Then the question set through `ask`, where the negative
questions likewise weigh less than the positive ones. **Guards, not rankers:** `box_stability`, the `unstable` rate,
`touched_share` on near-static pairs (the per-video alarm for θpix and θmin), boxes in exactly one container, popups
found on frames 149 and 151, repairs, link and container precision and recall against G2. (As built, the scorecard
copies the counters `annotate` and `interpret` already write; guards as compared metrics are deferred, and no precision
or recall against G2 was computed, G2 being judged by eye: L50.) Label consistency across frames decides nothing: a
label wrong in every frame is perfectly consistent. **Cost beside every number:** dollars per frame, and per video
projected to the 221-frame sample; today's reference is about $0.135 per frame all in, about $30 per video.

**Evidence rules.** Metrics are computed by committed scripts before a phase runs. Comparisons are paired by frame
over the same frames. P1 sets the noise floor; a difference inside it is no difference. Screening uses two repeats;
repeats are added to finalists until a difference clears the noise or is declared none. No success threshold is
pre-committed. Each phase reports to the owner when it finishes and may reshape what follows; the next phase starts
without waiting.

*This table is the plan as first written. P0 ran as listed (L47). P1 ran as listed ($81.01, L57) except for the
comparison with `runs/span2-before` and link quality against G2, which the harness does not compute (L50). From P2 on,
each phase was chosen from the last result (L44), so the numbers below name other work than what ran under them: P2 was
graphical questions and incremental annotation (L59), P3 the image-scale sweep (L60), P4 and P4b the whole sample, sync
and batch (L62), P5 arm D against arm A (L63), P6 answering from the index alone (L65), P7 and P8 Sonnet 5 (L64). Never
run: the arms × scales matrix (arms B and C unbuilt), the pane label (unbuilt), `entered_text` with crops (unbuilt), and
the hold-out video (not yet supplied). Results are under `docs/results/`.*

| Phase | What | Runs | Estimate |
|---|---|---|---|
| P0 | **Free.** `read` and `track` over all 221 frames and both spans. H1–H8 by reading records against frames; the OCR reader's primary metrics against G1; margin 0, 0.25, 0.5, 1.0; lifetime fragmentation; and the incremental-annotation projection, in counts (P3 measures the dollars): a labelling call for the first frame and for every transition with changed pixels, and the target boxes per call against all boxes per frame, which is the saving (tokens per call, not calls) | — | $0 |
| P1 | Three co-equal bases at full scale, arm A, every frame annotated: **transcribing**, **group-only**, **no annotation**; both spans through `index`, the question set on span 2; 3 repeats each. Noise floor per base; side by side with `runs/span2-before`; link quality per kind against G2 | 18 | about $55 |
| P2 | Referencing arms × coarse scales, smoke span, 2 repeats, every arm alive throughout. Group-only: A–D × 1.0, 0.5, 0.25. Transcribing: A–D × 1.0, 0.67 (it must still read). Then refinement among 0.67, 0.4, 0.3, 0.2 where it looks good; then each mode's chosen point on span 2, 3 repeats | about 36 + 12 + 6 | about $60 |
| P3 | Incremental annotation against annotating every frame (from P1), for both modes, both spans, 3 repeats: cost, container and link quality against G2, the command metrics, and what the listed risks cost in practice | 12 | $10–30 |
| P4 | Pane as a label string, on or off, smoke span, 2 repeats: does it change link quality or the usefulness of a search hit | 4 | about $5 |
| P5 | `entered_text` and `submitted` against G1, never-run suggestions included, with half-scale frames (from P1) and with crops (L39: crops kept the suggestion detail); agent prompt wording on the negative questions | 3 + agent calls | about $6 |
| P6 | The owner's hold-out video through the configuration chosen so far: θpix and θmin by `touched_share`, the prompt, the command metrics if the owner lists its commands | 1–3 | by length |

About $140–190 of the $470 if every phase runs as listed; then the full sample, sync and batch. (As run, the
phases left about $70, L64. Batch mode paid 0.68 of the sync price on the whole sample, not half, because batched
requests mostly write the prompt cache instead of reading it, L62.) Figures behind the
estimates: the per-frame call transcribing $0.117 on the smoke span (L41) and about $0.139 on span 2 (row mode
measured $0.115); group-only about $0.08 (row mode $0.063, plus ids and links), falling with scale (L33, L42);
`interpret` $0.019 per transition (L39); `summarize` $0.1–0.3 per span; a question about $0.10.

## 10. Build order on the branch

Each step lands with synthetic-fixture tests and its own commit. The order is the pipeline's.

*As it went (L52, L53, L55): steps 0 to 7 were built in this order, with the harness built in parallel on its own
branch. Step 6 has no "co-occurrence fallback": the whole-screen entry per frame (§6) serves a query whose terms sit
in different boxes. Of step 8's switches the scale and incremental annotation were built; arm D was built and removed
(L63); arms B and C and the pane label were not built. Step 9 has not been done.*

0. Tag `pre-rebase-boxes` on `main`; create `rebase-boxes`; the first commit removes what §8 lists and renames
   `decode`'s and `read`'s outputs.
1. Records `Box`, `Change`, `Lifetime` and their loaders.
2. **`track`**: changes, then lifetimes. The scripts for the primary metrics. **P0.**
3. `annotate` arm A on every frame, with the transcribing switch; its records, repair, and the loaders that join
   labels onto boxes, changes and lifetimes.
4. `interpret`: rendering with box ids and labels, `entered_text`, `submitted`, citation validation, `reverts`.
5. `summarize` over the new records.
6. `index`: lifetime and transition nodes, both joins, pair fields, the co-occurrence fallback; `ask` tools and prompt.
7. Guards and cost reporting per frame and per video. **P1.**
8. Evaluation switches: arms B, C, D, the scale, incremental annotation, the pane label. **P2–P5**, then **P6**.
9. Remove the losing switches; rewrite the design document as revision 7; ledger rows; merge to `main`.

## 11. Risks, remaining constants, watch list

- **θpix and θmin now carry identity for the whole pipeline and were calibrated on this one video** (design §7.2,
  §22 #3). The failure is graceful: a noisier encode means fewer vetoes and more OCR jitter reported as change; the
  index is unaffected. `touched_share` on near-static pairs is the per-video alarm, and the owner's hold-out video
  (planned as P6, not yet run) is its first outside test.
- **Remaining constants:** the margin (half the median box height; P0 varied it and it stays, L51), "rectangles
  intersect" and "greatest intersection first" (no threshold, no floor on the overlap), whitespace-blind labels, reading
  order only to break ties and to pair duplicate moved texts, the spacing guard's gap ratio (it did not fire on the
  `azconfigure` line of the span-2 baseline; `rec_batch_num` 1 may have made it moot).
- **The hypotheses of §4 were tested by P0** before anything was paid for (L47); what it showed and what was done
  about it is L51.
- **No window identity across frames** (names vary by call; nothing mechanical depends on them), and **moves pair
  duplicates arbitrarily** (a lifetime may hop between two identical strings).
- **Without annotation, `interpret` carries everything interpretive.** P1, P2, P4 and P6 showed what that costs on
  the three draft question sets: nothing in P1 and P4 (L57, L62); two questions with one root cause in P2, the reading
  of a line being edited (L59); one rubric line of one question in P6, where the agent could not open frames (L65).
- **Links have been checked by eye on a few frames only** (L53, L56; `run` links chained separate terminal lines
  until prompt version 3, L57), and no answer in any phase turned on one (L65). The joiner is a model judgement (hence
  both joins in the index), and ids were shuffled on a dense tab strip in the one run of L41.
- **Everything measured so far comes from one 14-minute video.**
- **Watch list, no logic until the real implementation shows the case:** the pointer clipping a box (frame 149,
  L40), a cursor glyph read as text (L43), an occluding window edge, low-contrast flicker, re-wrap on resize, text
  changing at sub-threshold contrast, duplicate strings under a scroll. P0 saw each of these except re-wrap on
  resize and a text change under θpix (L47); none has been given logic (L51).

## 12. Questions for the owner

Answered on 2026-09-21: label quality is judged by eye (G2 above); if two readings survive, both are recorded and
neither is picked, which does not pre-decide transcribing against group-only; the stage and command names are accepted;
the hold-out video is dealt with when it arrives. No drafter or reviewer writes a prototype, at all: documents are
written by reading and reasoning, and code exists only as the real implementation on the branch with its tests.

**Simplify before repairing (owner, 2026-09-21).** Reviewers tend to answer a minor finding with more machinery. When a
review finds a fault in a mechanism, the first question is whether the mechanism can be removed; logic is added only
on evidence from real runs, and P0 is where that evidence comes from. Applied so far: change records pair each
changed box with the box of the other frame it intersects most (touched or not, in either direction, one to one) and
nothing more, so there are no groups, no
connected components and no pools until P0 shows that OCR re-splitting under changed pixels needs them (P0 counted 7
such re-splits over both spans, and they were left alone, L47, L51); the
`confusable` flag is dropped; the clock rule and the `trivial` transition kind are dropped (it never fired in any
recorded run and would have let a transition go uninterpreted).

Also answered on 2026-09-21: the screen `description` stays (§6); the "no annotation" base stays in P1. In that base
there is no description, which is part of what it prices.
