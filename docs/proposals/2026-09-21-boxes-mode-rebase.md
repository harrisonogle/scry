# Proposal: re-base the pipeline on boxes mode

Status: **revision 3, 2026-09-21, for the owner's review. No code has been written against it.** Revision 1 is commit
`0a3135e`, revision 2 `b9b0c0c`; the two reviews of revision 1 are in `docs/reviews/`. If accepted this becomes design
revision 7, a restructuring of `docs/visual-transcript-pipeline-design.md` around new stages and records rather than a
patch to its sections. The decoder and settle machine, the optional Gemini outline, the RapidOCR adapter, the provider,
the call cache and `subset` carry over unchanged. Everything between OCR and the index is written fresh.

## 0. Revision 3: what changed and why

| Change | Source |
|---|---|
| **Reviewer prototypes are thrown out.** Every number and claim sourced from one is removed and their code is deleted; the implementation is not based on them, compared with them or justified by them. Choices that cited them survive only where they follow from the principles, as hypotheses (§4) that the real implementation's first run tests on its own terms. Future reviews read, reason and run the repository's real code. | Owner ruling |
| **Written as the redesign it is.** Stages are named for what they do and ordered as the design implies; no lines, rows, regions, units, marks or old stage numbers survive. | Owner ruling |
| **`track` (changes and lifetimes) sits before the model stage**: it needs only OCR boxes and pixels. Two options follow, evaluated and not decided: annotate only new or changed boxes (§6), and no annotation at all as the cost floor (§9). | The order; span-2 baseline: 27 of 30 transitions changed under 5 % of the screen |
| **Built on a branch** (`rebase-boxes`), fresh against the new records; nothing imports the old row machinery; `main` and a tag stay runnable. The "new files beside the old" plan is gone. The Apple Vision adapter and its macOS dependencies go too. | Owner ruling |
| **Transients are never folded.** Both transitions stay; a change that undoes the previous one is annotated `reverts` with the hold time. No time constant. | Owner ruling |
| **Focus is not a deliverable.** The model's self-report goes with caret and retrospective focus. | Owner ruling |
| **Persistence is never a correctness mechanism** and never evidence that a command ran. The majority reading survives only as de-noising of repeated readings of the same unchanged pixels. | Owner ruling |
| **Whether the model gives a second reading is not decided.** Transcribing and group-only are co-equal from the first paid phase; everything that exists only with two readings is conditional (§7). | Owner ruling |
| **Cost is an outcome of every phase**, per frame and per video, beside every quality number. The remaining budget (about $470) is pre-approved; phases report as they finish and nothing waits for permission. | Owner ruling |

Revision 2's changes, and where they stand now:

| Status | Revision 2 change |
|---|---|
| Kept | Per-box change records, moves cancelled, whitespace-blind labels over exact strings (now H2–H4); one record shape (H5); `continues`; flat containers, no container events; lifetimes as the index unit, both joins, pairs as fields; `entered_text`, `submitted`, citable box ids; a guiding agent prompt; ground-truth evaluation with evidence rules; arms alive through the scale sweep; L43's RapidOCR settings |
| Reversed | "Transcription stays on in the base" (now undecided, co-equal arms); the transient folded without a time gate (now never folded); new files beside the old (now a branch) |
| Subsumed | Transcribing only changed boxes (by incremental annotation) |

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
- **Incremental annotation.** `annotate` labels only boxes that are new or changed; an unchanged box carries its
  labels along its lifetime; a transition with no such box makes no call. The first frame and a cut are the same
  rule with every box new, so no threshold separates "full" from "incremental".
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
| **Change group** | Before and after boxes that overlap each other under changed pixels, with a kind and a character diff. | measured |
| **Container** | A window or a popup. Flat: containers do not nest. A popup may name its owner window. A label. | model |
| **Link** | A typed relation among boxes of one container: `run`, `pair`, `record`. A label. | model |

| Old | New |
|---|---|
| Stage 1; Stage 0 | `decode`; `outline` |
| Stage 2a, `ocr.jsonl`, mark, OCR line, `l<n>` | `read`, `boxes.jsonl`, box, `b<n>` |
| Stage 4, 4b, `transitions.jsonl`, `computed_diff`, `DiffOp`, unit line lists, row banding | `track`, `changes.jsonl`: `groups`, `appeared`, `removed`, `moved`; `lifetimes.jsonl` |
| Stage 2b, 2c, 3, `perception.jsonl`, `frames.jsonl` (merged), `focus.jsonl` | `annotate`, `annotations.jsonl`; `frames.jsonl` now names `decode`'s records |
| row, row line, line, `Line`, `rows`, `vlm_lines` | box; a split text is a `run` link; `texts` |
| region, unit, pane, `Region`, `r<n>` | container `c<n>` (window or popup); pane is at most a label string |
| association | link |
| VLM-only line `v<n>` | missed text `m<n>` (no rectangle; citable, never in a change) |
| `typed`, `output_appended`, `coalesced`, `transient_merged` | kinds on groups; `continues`; `reverts`; `entered_text`, `submitted` from `interpret` |
| region correspondence, `matched`, focus signals | removed |
| Stage 5, 6, 7, the agent | `interpret`, `summarize`, `index`, `ask` |
| per-frame region and frame index nodes | lifetime nodes |
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

**Hypotheses.** These choices follow from the principles and nothing admissible has tested them. P0 tests each on
its own terms: by reading the records against the frames of both spans, and by the command metrics of §9.

| | Hypothesis | Follows from |
|---|---|---|
| H1 | The veto is sound at any changed fraction: a differing OCR text on unchanged pixels is a re-read. | Principle 2; the differences the box-stability result lists are glyph and spacing noise |
| H2 | The box is the unit of a change record; a changed box finds its earlier self by rectangle intersection, so a growing text matches its shorter self. | Principle 1: joining every box near a change mixes unrelated boxes |
| H3 | Equal texts on both sides of a transition are moves, cancelled across the whole transition; scrolls and window moves become small. | A scroll changes every pixel and no text |
| H4 | Kind labels computed with whitespace removed are useful conveniences; the exact strings are the record. | L35, L43: OCR spacing jitters on the same text |
| H5 | One record shape serves a keystroke and a page load; no large-change mode is needed. | Principle 7 |
| H6 | Touch is tested on a component's pixels, not its bounding rectangle. | A window outline's rectangle covers its whole interior |
| H7 | Lifetimes do not fragment so much that duplicate search hits return. | Box stability 96.5 % on unchanged pixels |
| H8 | A change that undoes the previous one is found by comparing the frames on either side of it directly. | No time constant needed |

## 5. Records

`frames.jsonl` is `decode`'s record per emitted frame, unchanged in content. `boxes.jsonl`, from `read`:

```json
{"frame": 155, "png": "frames/00155.png", "engine": {"name": "rapidocr", "version": "3.9.2"},
 "boxes": [{"id": "b33", "bbox": [659, 352, 904, 371], "text": "PS C:\\Users\\msadmin> az login", "conf": 0.98,
            "words": [{"text": "PS", "bbox": [659, 352, 679, 371]}], "in_churn": false}]}
```

`changes.jsonl`, from `track`, one record per transition:

```json
{"id": "T9", "from_frame": 154, "to_frame": 155, "t": [598.7, 620.7], "kind": "single",
 "pixels": {"changed_fraction": 0.0002, "components": 2, "textless": 1, "touched_share": 0.01},
 "groups": [{"kind": "appended", "rect": [659, 350, 904, 373],
             "before": [{"box": "154:b31", "text": "PS C:\\Users\\msadmin>"}],
             "after": [{"box": "155:b33", "text": "PS C:\\Users\\msadmin> az login"}],
             "char_diff": [["=", "PS C:\\Users\\msadmin>"], ["+", " az login"]], "continues": null}],
 "appeared": [], "removed": [], "moved": 0, "same_place": 1, "reverts": []}
```

- One shape for every size (H5). A keystroke is one group. A page load is a few groups plus long `appeared` and
  `removed` lists of box ids. A scroll is mostly `moved`.
- `reverts` lists the areas of this transition that undo the previous transition's change there, as
  `{"of": "T4", "rect": […], "hold_s": 3.4}`. Both transitions stay and both are interpreted.
- Transition kinds: `single`, `unsettled`, `trivial`.

`lifetimes.jsonl`, from `track`, measured fields only (counts illustrative):

```json
{"id": "L412", "text": "PS C:\\Users\\msadmin> az configure --defaults group=RG1-KodeKloud-AKS",
 "readings": {"PS C:\\Users\\msadmin> az configure --defaults group=RG1-KodeKloud-AKS": 25,
              "PS C:\\Users\\msadmin>azconfigure --defaultsgroup=RG1-KodeKloud-AKS": 1},
 "unstable": true, "sightings": 26, "first": {"frame": 161, "t": 649.2}, "last": {"frame": 187, "t": 721.0},
 "moved": true, "boxes": ["161:b40", "…"]}
```

`text` is the majority OCR reading; `unstable` means OCR gave more than one reading of the same pixels, a measured
fact the agent can hedge on with no second reader.

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
 "repairs": 0, "model": "claude-opus-5", "prompt_version": "annotate-v1", "usage": {}, "error": null}
```

- `targets` is every box of the frame, or only the new and changed boxes when incremental. A box's labels come from
  its own frame's record, else from the latest record of its lifetime.
- `texts` exists only when transcribing. The loader then derives per box `vlm`, `agree` (exact equality after
  normalisation, icon-glyph strip kept) and `non_text` (the model returned `""`, so the box leaves agreement
  denominators and index text), and per lifetime the model's majority reading.
- `rect` is set only under arms where the model draws containers (§6). A box is in at most one link; a link across
  two containers is dropped and counted. A key and value that OCR put in one box can never be a pair: pairs enrich,
  they are not a table of properties.

`interpretations.jsonl` keeps action, result, description, confidence and citations, and gains `entered_text` (what the
user entered in this transition as far as the frames show, excluding anything the application suggested; null when
nothing) and `submitted` (`yes`, `no`, `unclear`: whether what was entered took effect).

## 6. Stage by stage

**`read`.** RapidOCR 3.9 with `use_cls` off and `rec_batch_num` 1 (L43). No second pass, upscale, normalisation,
English model or OCR ensemble. Google Cloud Vision works with the owner's key and stays an optional extra reader
outside the base.

**`track`.** For each consecutive pair of emitted frames *a*, *b*:

1. **Changed components** by `decode`'s rule over the two PNGs: pixels differing by more than θpix, in connected
   components of at least θmin pixels. Changed pixels outside any component are ignored.
2. **Touched boxes.** A box is touched when a pixel of a component (H6) lies inside the box grown by the margin,
   half the median box height over both frames. With a PNG missing every box is touched and `pixels` is null.
3. **Untouched boxes are unchanged** (H1). Each continues the lifetime of the untouched box of *a* it overlaps most; a
   differing OCR text there is a variant reading.
4. **Same place, same text.** A touched before box and after box that intersect and read the same drop out, counted
   in `same_place`: something visual changed over unchanged text.
5. **Moved** (H3). Texts equal on both sides anywhere in the transition cancel as a multiset, counted in `moved`, and
   continue their lifetimes. Reading order is used only to pair duplicates of the same string.
6. **Groups** (H2). The remaining before and after boxes are grouped by rectangle intersection. Each group's kind is
   computed with whitespace removed (H4): `reread` (equal), `appended` (before is a prefix of after), `truncated` (the
   reverse), `changed` (otherwise). Recorded strings and `char_diff` are exact. A `reread` continues the lifetime with
   a variant; the other kinds end one lifetime and start another.
7. **Appeared, removed.** After boxes in no group; before boxes in no group.
8. **Textless components**, touching no box in either frame, are counted with their area and yield no record.
9. **Reverts** (H8). For each area the previous transition *z*→*a* changed, if comparing *z* and *b* directly shows no
   component inside it, *a*→*b* records `reverts` with the hold time. Nothing is folded.
10. **Continues.** A group whose before box is the previous transition's after box records `continues`: an exact
    identity through a shared box that asserts nothing. New output arrives as new boxes, so geometry cannot join it to
    a growing input text.
11. `trivial` keeps the clock rule on `char_diff`; boxes flagged `in_churn` by `decode` keep the flag on their groups.

**`annotate`.** One call per frame, or per transition with targets when incremental. Draft system prompt for
referencing arm A, with the transcription paragraph present only when transcribing:

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
```

When incremental, the call also carries the known containers and the target boxes' neighbours, and a link may join a
target to a known box. Output lists are lists of objects, never arrays parallel to an id list. Validation is repair,
never abort: unknown ids, second assignments and links naming unknown, already-linked or cross-container boxes are
dropped, an unplaced target goes to `unassigned`; all counted.

Referencing arms, all kept alive through the scale sweep (L42 showed an arm that is neutral at full scale helping at a
reduced one):

| Arm | Images | The model returns | Code does |
|---|---|---|---|
| A | clean + numbered overlay | box ids | — |
| B | clean + numbered overlay | a rectangle per container; links and texts by id | assigns boxes by centre-inside, front-most container wins |
| C | clean only | a rectangle per container; links and texts as points | assigns by centre-inside; snaps each point to the nearest box |
| D | clean only, plus OCR's box coordinates as a text list | box ids | — |

OCR's coordinates serve code in: box numbering, the overlay, arm D's list, assignment and snapping (arms B, C),
`track`'s touch and intersection tests, the spacing guard, `box_stability`, and crops for `interpret`.

**Risks of incremental annotation, stated before it is tried.** A wrong label is carried for a whole lifetime, not
re-drawn each frame. A container can change with no box changing (a window renamed, a textless popup), and no call
is made. The first frame and every cut are full calls, so a video of cuts saves nothing. A link between a new box and
an old one depends on the context the call carries. Nothing is re-annotated, so label noise is invisible within a run.

**`interpret`.** Half-scale frames (L39), one call per non-trivial transition; nothing is folded, so a tooltip costs
two calls. The change text is rendered per group with the box ids the model may cite and with labels when annotations
exist, for example `[155:b33] PowerShell window: "PS C:\Users\msadmin>" → appended " az login"`; the model's reading
sits beside OCR's where two readings differ; appeared and removed texts carry their ids; moved and textless counts are
one line each; a `reverts` entry reads "undoes T4's change after 3.4 s". Citations are validated against those ids.
The prompt asks for `entered_text` and `submitted` and says an input field may show a suggestion the user did not enter.

**`summarize`.** Renders each transition from its interpretation (action, `entered_text`, `submitted`) and group
texts, and a frame's state from its containers when annotations exist. Intent unchanged.

**`index` and `ask`.** Nodes: one per **lifetime** (the majority reading of each reader, every variant, run texts
joined both with `""` and with `" "` so a wrong joiner cannot hide a command, pair text as `key value` tokens with
`key` and `value` as fields, first and last time, container label when there is one); one per transition (action,
result, `entered_text`, `submitted`, group texts); steps, sections and the video as today. There are no per-frame
copies: a text on screen for many frames is one hit with its first and last time (today's smoke index holds 67
region nodes for 11 frames of three screens). A multi-term query with no single-node match falls back to per-term
hits whose lifetimes overlap in time; a deduplicated whole-screen node is added only if the question set shows the
need. `ask`'s tools return lifetimes, changes and interpretations. Its prompt guides and does not prohibit: quote
verbatim where independent readers agree; where they differ, or a text is `unstable` or seen once, say so or look at
the frame; an input field may show a suggestion; `submitted` is the primary evidence that a command ran, and without
it say what was seen and how sure; time on screen is not evidence either way. A `get_pairs` tool is a follow-on.

## 7. If two readings survive: which is recorded (design §22 #15)

Conditional on the evaluation keeping the model's second reading. For it (L43): the model reads a line being edited
better (12 of 16 against 8 of 16), disagreement flags 9 of 9 OCR misreads with 10 false alarms in 71, and no OCR-side
remedy (second pass, upscaling, normalisation, other models, an ensemble with Cloud Vision) was right where no single
reader was. Against it: about half the per-frame cost, and readings assigned to a neighbouring box (48 of 53), which
arms B–D and assignment by position and similarity together are meant to fix.

| Option | For | Against |
|---|---|---|
| OCR always (today) | No model normalisation can enter the record | A line being edited is recorded wrong half the time |
| Model always | Best on those lines | Wrong-neighbour assignment and quiet case normalisation enter the record |
| Pick by rule (near-identical → model) | Cleaner text | The rule hides exactly where a model "completion" would sit |
| **Record both, pick neither** | Honest; both searchable; exact agreement stays the only "quote verbatim" signal | Two strings to carry; the agent must handle disagreement |

**Recommendation if two readings survive: record both.** Also conditional on that outcome: `agree` and `non_text`,
indexing both readings, assignment by position and similarity, and `mark_match`. With one reader, `unstable` is the
only hedge and `entered_text` the only second opinion on a command.

## 8. Removed, kept, new

The branch's first commit removes the old row machinery, so nothing can import it; `main` and the tag `pre-rebase` hold
the runnable old pipeline for before-and-after comparison. The removal reaches `main` when the branch merges.

| | Modules and keys |
|---|---|
| **Removed** | `merge.py`, `correspond.py`, `coalesce.py`, `perceive.py`, `interpret.py`, `hierarchy.py`, `diff.py` except `PixelSource` and the margin helpers (moved into `track`), node extraction in `index.py`, the tools of `agent.py`, the four prompt modules, `diagnostics.py` except cost accounting; every schema from `Line` and `Region` to `Transition` and the `Vlm*` variants; `perception.jsonl`, the merged `frames.jsonl`, `transitions.jsonl`, `focus.jsonl`; the `[merge]` and `[diff]` config keys, `transient_max_s`, `stage2c_*`; their tests |
| **Removed, not row machinery** | the Apple Vision adapter `ocr/vision.py`, its test and the PyObjC dependencies (the deployment target is not Apple hardware; not the default since L36) |
| **Kept** | `decode.py`, `detect.py`, `settle.py`, `stage1.py` (renamed for `decode`), `ocr/rapid.py`, `overlay.py`, `outline.py`, `providers/`, `run.py` (new loaders), `subset.py`, `config.py`, `env.py`, `jsonl.py`, `textdiff.py` (normalisation, Myers for `char_diff`), `agreement` per box, cost accounting, the search and fusion code of `index.py` |
| **New** | `read`, `track` (changes, lifetimes), `annotate`, `interpret`, `summarize`, `index` node extraction, `ask` tools and prompt; schemas `Box`, `Change`, `Lifetime`, `Annotation`, `Container`, `Link`, `Interpretation`; config `margin` (box heights), the annotate switches of §9 |

Existing run directories do not load on the branch; `decode`'s output is reused by renaming one file or re-running it
(free, under five minutes for the sample).

## 9. Evaluation

**Ground truth.** G1, the precondition of every paid phase: the command list of span 2,
`docs/ground-truth/span2-commands.md` (9 executed entries with frames and times, accepted by the owner on
2026-09-21, and 5 suggestions that appeared on screen and were never run, kept as a scoring key only). G2, small: the links of frame 150 and the windows and popups of the 11
smoke frames, drafted from existing runs for the owner to correct. Q: about fifteen questions written from G1, with
negatives ("did they roll back the deployment?", "did they run `az login`?" must be answered no). The owner is
preparing a second, different video as a hold-out.

**Primary metrics, scored without a model call.** Per executed entry: *found* (a lexical search for its exact text
returns a node covering its time) and *exact* (some lifetime's majority reading contains it exactly, per reader);
these two rank alternatives. **Secondary** (owner's ruling: run against not-run matters less than finding and
quoting): *time error* of first appearance and of submission, and *false run* (never-run suggestions covered by a
`submitted: yes`); they are reported beside the primary scores and break ties, no more. Then the question set
through `ask`, where the negative questions likewise weigh less than the positive ones. **Guards, not rankers:** `box_stability`, the `unstable`
rate, `touched_share` on near-static pairs (the per-video alarm for θpix and θmin), boxes in exactly one container,
popups found on frames 149 and 151, repairs, link and container precision and recall against G2. Label consistency
across frames decides nothing: a label wrong in every frame is perfectly consistent. **Cost beside every number:**
dollars per frame, and per video projected to the 221-frame sample; today's reference is about $0.135 per frame all
in, about $30 per video.

**Evidence rules.** Metrics are computed by committed scripts before a phase runs. Comparisons are paired by frame
over the same frames. P1 sets the noise floor; a difference inside it is no difference. Screening uses two repeats;
repeats are added to finalists until a difference clears the noise or is declared none. No success threshold is
pre-committed. Each phase reports to the owner when it finishes and may reshape what follows; the next phase starts
without waiting.

| Phase | What | Runs | Estimate |
|---|---|---|---|
| P0 | **Free.** `read` and `track` over all 221 frames and both spans. H1–H8 by reading records against frames; the OCR reader's primary metrics against G1; margin 0, 0.25, 0.5, 1.0; lifetime fragmentation; and the calls and target boxes incremental annotation would make, which prices P3 in advance | — | $0 |
| P1 | Three co-equal bases at full scale, arm A, every frame annotated: **transcribing**, **group-only**, **no annotation**; both spans through `index`, the question set on span 2; 3 repeats each. Noise floor per base; side by side with `runs/span2-before`; link quality per kind against G2 | 18 | about $55 |
| P2 | Referencing arms × coarse scales, smoke span, 2 repeats, every arm alive throughout. Group-only: A–D × 1.0, 0.5, 0.25. Transcribing: A–D × 1.0, 0.67 (it must still read). Then refinement among 0.67, 0.4, 0.3, 0.2 where it looks good; then each mode's chosen point on span 2, 3 repeats | about 36 + 12 + 6 | about $60 |
| P3 | Incremental annotation against annotating every frame (from P1), for both modes, both spans, 3 repeats: cost, container and link quality against G2, the command metrics, and what the listed risks cost in practice | 12 | $10–30 |
| P4 | Pane as a label string, on or off, smoke span, 2 repeats: does it change link quality or the usefulness of a search hit | 4 | about $5 |
| P5 | `entered_text` and `submitted` against G1, never-run suggestions included, with half-scale frames (from P1) and with crops (L39: crops kept the suggestion detail); agent prompt wording on the negative questions | 3 + agent calls | about $6 |
| P6 | The owner's hold-out video through the configuration chosen so far: θpix and θmin by `touched_share`, the prompt, the command metrics if the owner lists its commands | 1–3 | by length |

About $140–190 of the $470 if every phase runs as listed; then the full sample, sync and batch. Figures behind the
estimates: the per-frame call transcribing $0.117 on the smoke span (L41) and about $0.139 on span 2 (row mode
measured $0.115); group-only about $0.08 (row mode $0.063, plus ids and links), falling with scale (L33, L42);
`interpret` $0.019 per transition (L39); `summarize` $0.1–0.3 per span; a question about $0.10.

## 10. Build order on the branch

Each step lands with synthetic-fixture tests and its own commit. The order is the pipeline's.

0. Tag `pre-rebase` on `main`; create `rebase-boxes`; the first commit removes what §8 lists and renames `decode`'s
   and `read`'s outputs.
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
  index is unaffected. `touched_share` on near-static pairs is the per-video alarm, and P6 is its first outside test.
- **Remaining constants:** the margin (half a box height; P0 varies it), "overlaps most" and "rectangles intersect"
  (no threshold), whitespace-blind labels, reading order only to pair duplicate moved texts, the spacing guard's gap
  ratio (it did not fire on the `azconfigure` line of the span-2 baseline; `rec_batch_num` 1 may have made it moot).
- **The hypotheses of §4 are untested.** If P0 refutes one, the design changes before anything is paid for.
- **No window identity across frames** (names vary by call; nothing mechanical depends on them), and **moves pair
  duplicates arbitrarily** (a lifetime may hop between two identical strings).
- **Without annotation, `interpret` carries everything interpretive.** P1 shows what that costs on the question set.
- **Links are unproven beyond one frame of one run** (L41), the joiner is a model judgement (hence both joins in the
  index), and ids were shuffled on a dense tab strip in that run.
- **Everything measured so far comes from one 14-minute video.**
- **Watch list, no logic until the real implementation shows the case:** the pointer clipping a box (frame 149,
  L40), a cursor glyph read as text (L43), an occluding window edge, low-contrast flicker, re-wrap on resize, text
  changing at sub-threshold contrast, duplicate strings under a scroll.

## 12. Questions for the owner

1. **G2:** will you correct about 55 drafted entries (links of frame 150, windows and popups of the smoke frames), or
   should label quality be judged by eye on samples instead?
2. **If two readings survive, record both and pick neither** (§7): agreed?
3. **The draft omits the per-frame prose `description`:** it has no home once per-frame index nodes go, and
   non-textual state is `interpret`'s job. Keep it out (recommended), or index it once per run of unchanged frames?
4. **Stage and command names** (`decode`, `read`, `track`, `annotate`, `interpret`, `summarize`, `index`, `ask`):
   acceptable?
5. **The hold-out video:** will you also list its commands, so P6 can score the command metrics and not only the guards?
