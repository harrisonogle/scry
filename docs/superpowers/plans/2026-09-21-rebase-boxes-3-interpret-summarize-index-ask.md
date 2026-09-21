# Re-base step 3: `interpret`, `summarize`, `index`, `ask` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **One deliberate adaptation of the writing-plans format: this plan contains NO implementation bodies and no test
> code.** The owner forbids code that exists anywhere except as the real implementation on the branch with its tests; no
> drafter or reviewer writes a prototype, a scratch implementation or a trial script, not even to check an idea. This
> plan was written by reading the specification, the ledger and the repository's real code, and by reasoning. So every
> task gives: the files; the public interface (signatures with types, pydantic record fields, config keys with
> defaults); the behaviour as numbered rules precise enough that two implementers produce the same outputs, each traced
> to the specification; the tests to write FIRST, each named, with its concrete fixture and exact expected values; the
> commands; the commit message. Prompt text is specification, not code, and is given in full. The implementer writes
> the test code and the implementation on the branch from these. Reviewers of this plan read and reason; they execute
> nothing.

**Goal:** On branch `rebase-boxes`, build the stages after the labels — `interpret` (what the user did in each
transition, with `entered_text`, `submitted` and validated citations), `summarize` (steps, sections, the video),
`index` (whole-screen entries kept, lifetime entries added, duplicates collapsed in the result list) and `ask` (the
answering agent) — plus their config keys, cost accounting, CLI commands and the `run` wiring for the whole pipeline.

**Architecture:** Every stage reads the measured records of plan 1 (`frames.jsonl`, `boxes.jsonl`, `changes.jsonl`,
`lifetimes.jsonl`) and, when they exist, the labels of plan 2 (`annotations.jsonl`) through plan 2's joined view; with
no annotations every stage still runs end to end (the "no annotation" base, spec §2). One pure module renders a change
record as text with the box ids the model may cite; `interpret`, `summarize` and `ask` all use it, so the model and
the agent read the same honest account (spec §4 principle 3). The index keeps one document per emitted frame that is a
superset of everything known about that frame, adds one document per lifetime and per transition, ranks each family
of documents separately and fuses them, and collapses identical consecutive frame hits in the result list only.

**Tech stack:** Python ≥ 3.12 with `uv`; pydantic 2, typer, Pillow, SQLite FTS5 (unicode61 and trigram tokenizers),
`sqlite-vec` (optional), the Anthropic SDK behind `scry.providers` (kept), pytest. No new dependencies.

**Spec:** `docs/proposals/2026-09-21-boxes-mode-rebase.md`, revision 3 (§2, §3, §4, §5 `interpretations.jsonl`, §6
`interpret`, `summarize`, `index` and `ask`, §7, §8, §9 metrics and cost, §10 steps 4–7). It supersedes
`docs/visual-transcript-pipeline-design.md` wherever they differ; the old design's §12–§15 still state the intent of
these stages. Ledger rows L28–L43 (`docs/decision-ledger.md`), in particular L39 (image modes) and L43 (readers), and
`docs/ground-truth/span2-commands.md`. Sibling plans: `2026-09-21-rebase-boxes-1-read-track.md` (plan 1),
`…-2-annotate.md` (plan 2) and `…-4-evaluation.md` (plan 4); plan 1 was read in full while this plan was drafted, plans
2 and 4 appeared as it was finished and were read for their interfaces only. Executors read the spec with this plan.
Where this plan is more specific than the spec, the choice is listed under "Decisions this plan makes".

**Code to adapt:** plan 1's first commit deletes `interpret.py`, `hierarchy.py`, `agent.py`, `diagnostics.py` and
`prompts/` on the branch. They are read from the pre-re-base tag (`git show pre-rebase-boxes:src/scry/interpret.py`,
likewise `hierarchy.py`, `agent.py`, `index.py`, `prompts/stage5.py`, `prompts/stage6.py`, `prompts/agent.py`, and
their tests) and re-created under the names below. Nothing on the branch imports the tag's modules.

## Interface assumptions (for the synthesis pass)

Spec §5 is the contract. Everything below is something this plan needs that §5 does not pin down, or a name chosen
by a sibling plan. Each line says what is assumed; a different name in a sibling plan is a rename here, a different
meaning is a conflict to reconcile.

- **A1. Plan 1's records and loaders, exactly as its Task 4:** `BBox`, `Frame` (`video_id, frame, t_change, t_settled,
  t_end, settled, churn_regions, caret, width, height, sha256, png`), `Box`, `FrameBoxes`, `PixelStats`, `BoxText`,
  `Group`, `Revert`, `Change`, `FrameTime`, `Lifetime`, `OutlineChapter`, `box_ref`, `parse_box_ref`; `Run.frames`,
  `Run.boxes`, `Run.changes`, `Run.lifetimes`, `Run.outline`; `Run.load_frames()`, `load_boxes()`, `load_changes()`,
  `load_lifetimes()`, `load_outline()`, `chapter_of(t)`; every loader returns `[]` for an absent file.
- **A2. Meanings taken from plan 1's rules and decisions:** reading order is box id order within a frame (its D7);
  `Change.t == (a.t_end, b.t_settled)`, the interval in which the change happened (its Task 10 rule 6);
  `Group.continues` is written `"T8/0"` (change id, slash, group position; its D14); `Lifetime.first.t` is the first
  frame's `t_settled` and `Lifetime.last.t` the last frame's `t_end` (its D15); **every box of every frame is in
  exactly one lifetime's `boxes` list**; every ref in `appeared`, `removed` and the groups resolves in `boxes.jsonl`;
  `same_place`, `moved` and `pixels.textless` are counts.
- **A3. What plan 1 leaves in place:** `scry.costs.PRICES` and `estimate_cost`; `scry.video.iter_frames`;
  `scry.overlay.scale_image`; `scry.track.pixels.margin_px(a_boxes, b_boxes, margin) -> int`; in `scry.index`: `Node`,
  `Embedder`, `FastembedEmbedder`, `get_embedder`, `open_db`, `_ensure_vec`, `index_nodes`, `_terms`, `fts_query`,
  `trigram_query`, `rrf`, `_filter_sql`, `search`; `IndexConfig(embedder, k, k_filtered, rrf)`; every config model with
  `extra="forbid"`; `ModelConfig` without any per-stage effort key; the manifest entry `stages.decode.emitted`; the tag
  name `pre-rebase-boxes` (the spec says `pre-rebase`).
- **A4. Plan 2's joined view of the labels, as its Tasks 10 and 11 define it** (spec §5: "a box's labels come from its
  own frame's record, else from the latest record of its lifetime"). This plan consumes it and re-implements no join:
  - `Run.annotations: Path`; `Run.load_labels() -> Labels | None`, `None` when `annotations.jsonl` is absent or holds
    no record (the "no annotation" base).
  - `Labels.box(ref) -> BoxLabel | None` (`KeyError` for a ref that is in no frame). `BoxLabel`: `container: Container |
    None` (`id, kind, app, name, owner`) · `pane: str | None` · `link: BoxLink | None` · `vlm: str | None` · `agree: bool
    | None` · `non_text: bool`. `BoxLink`: `kind` · `role: "run" | "key" | "value" | "member" | "header"` · `boxes`,
    `joiner`, `key`, `value`, `members`, `header`, every id a box ref of the box's own frame.
  - `Labels.frame(frame) -> FrameLabel`: `containers: list[Container]` · `links: list[Link]` (the links in force, every
    id a box ref of that frame, each with `kind` and the same role lists) · `description: str | None` (the description
    in force) · `missed: list[Missed]` (`id, text, container`). A frame with nothing known gives `FrameLabel()`.
  - `Labels.lifetime(lifetime_id) -> LifetimeLabel | None` (`None` for a lifetime with no labelled box and no link).
    `LifetimeLabel`: `vlm: str | None` (the model's majority reading) · `vlm_readings: dict[str, int]` · `agree: bool |
    None` (the two majority readings compared) · `non_text: bool` (at least one reading, all empty) · `container:
    Container | None` (of the latest labelled box) · `links: list[LifetimeLink]`, each with `kind`, `joiner`, the role
    lists **as lifetime ids**, `records: int` (how many records proposed it) and `first_frame: int`, ordered by
    `first_frame` then stored order. A lifetime's `links` are all that name it, in any role.
- **A5. Plan 2's stage:** `scry.annotate.run_annotate(run, cfg, provider=None)`; with `[annotate] mode = "off"` it
  deletes `annotations.jsonl`, writes a manifest entry with `skipped`, zero usage and the model, and returns. Its
  manifest entry `stages.annotate` carries `usage` (four keys) and `model` like the entries written here.
- **A6. Created by plan 2's Task 8 with the definitions this plan first drafted** (plan 2's IA8): in `scry.costs`
  `USAGE_KEYS`, `CACHE_WRITE_MULTIPLIER = 1.25`, `BATCH_MULTIPLIER = 0.5`, `add_usage(total, usage) -> dict`,
  `estimate_cost(usage, model, batch=False)` pricing cache-creation tokens; `AnthropicProvider.complete` returning the
  usage summed over its retries; `BatchRunner` keeping `cache_creation_input_tokens`;
  `scry.providers.batch.run_with_batches(run, cfg, provider, stage_fn)`; `tests/fakes.py` with `FakeMessages`,
  `fake_client`, `USAGE` (`input 100, output 20, cache read 1000, cache creation 400`: $0.004 a call at the fallback
  prices) and `AnswerProvider`; `src/scry/prompts/__init__.py`. If this plan is executed before plan 2, execute plan
  2's Task 8 first: it depends on nothing else of plan 2.
- **A7. §5's `Annotation` JSON shape** is what this plan's fixture writes by hand, line by line, into
  `annotations.jsonl`; plan 2's record model must load it with its own extra fields defaulted.
- **A8. A wish, not a dependency:** `Change.same_place` is a count. If plan 1 listed the box refs instead, the
  renderer of Task 4 would cite them (a highlight moving over unchanged text is exactly what `interpret` must explain).
- **A9. What plan 4 assumes of this plan, and where it stands** (its A9–A14, written without seeing this plan):
  stage entry points `(run, cfg)` with manifest keys `interpret`, `summarize`, `index`: **yes**; `usage` per
  interpretation record: **yes** (Task 1); `entered_text` holds the whole submitted text on the submitting transition:
  **yes** (Decision D2); `search` stays the agent's search function, collapse included, hits with `node_id, level, t,
  frames, text`: **yes** (Task 13); `ask` returns `text`, `citations`, `usage`, `model`, `turns`, `tool_calls`: **yes**
  (Task 15 adopts these names); `[ask] prompt` names a prompt variant: **yes** (Tasks 2 and 15).
  **Differences to reconcile:** (a) `summarize` passes the provider stage strings `summarize-boundary-<level>` and
  `summarize-elaborate-<level>`, so plan 4's call-cache attribution must treat a stage string starting with
  `summarize` as `summarize`; (b) plan 4's Task 1 redefines the cost functions with other names and one other
  behaviour (`BATCH_DISCOUNT` for `BATCH_MULTIPLIER`, a `cost_breakdown`, `KeyError` on an unknown model where A6 keeps
  today's fallback to the `claude-opus-5` prices, which this plan's fakes rely on with `"fake-model"`); (c) plan 4's
  `run_cost` and this plan's `run_costs` (Task 3) both total a manifest: this one feeds `scry run`'s summary, plan 4's
  the scorecards; (d) **the command metrics *found*, submission error and *false run* are plan 4's (its Task 4); this
  plan defines none**, although plan 1's D21 deferred *found* "to the index"; (e) plan 2 writes `from tests.fakes
  import …`, this plan `from fakes import …` (`tests/` has no `__init__.py` today): one style must be chosen;
  (f) plan 2 keeps `outline` first in `STAGES`; this plan's brief puts it after `decode` (Decision D19).

## Global Constraints

- Work only on branch `rebase-boxes`, after plans 1 and 2 have landed. `main` and the tag stay runnable and untouched.
- The package imports and `uv run pytest` reports 0 failures after every commit.
- **Unit tests only:** the fake clients of `tests/fakes.py` and hand-written records. No test reads the sample video, a
  directory under `runs/`, or the network. **No model API call is made anywhere in this plan**, by implementer or
  reviewer. No prototypes: code exists only as the real implementation with its tests.
- No constants taken from the sample video; geometric parameters are relative to box height or frame size and live in
  `src/scry/config.py` with their unit in a comment, and in `scry.toml`. Test fixtures and prompt examples use invented
  content (`git status`, a `Status` field), never the sample's commands.
- No logic for a case until the real implementation shows the case (spec §4 principle 7, §11 watch list). No cursor or
  suggestion locating, no brightness thresholds (principle 3).
- **The mechanical layer never says "typed"** and never separates suggestions, program output or paste. Whether
  something was entered or submitted is `interpret`'s judgement from the frames (principle 4).
- **Persistence is never evidence.** No rule, prompt or metric here reads how long a text stayed on screen as evidence
  that something was or was not run. `sightings`, `first` and `last` are measurements and de-noising only (principle 5).
- **Transients are never folded.** Every non-trivial transition is interpreted, including both halves of a change that
  `reverts` (spec §0, §5).
- Focus is not a deliverable: no stage, record, prompt or tool here reports which window had focus.
- Measured facts and model proposals never share a file: each stage writes only its own file, atomically
  (`scry.jsonl.write_jsonl`), and records a manifest entry `{inputs, config, finished, …stats}`; a stage skips itself
  when its inputs hash and config hash are unchanged (`Run.stage_up_to_date`, as today).
- Citations are `"<frame>:<box_id>"` (spec §3) and are validated against the ids the call was handed.
- Cost is an outcome (principle 9): every model stage records token usage including cache-creation tokens, and dollars.
- Commit messages end with the attribution lines the session supplies.

## The findability guarantee

The owner's top priority: **nothing findable today may become unfindable** (spec §6). The plan does not promise a
ranking it cannot run; it guarantees the following invariants, each pinned by a named test in
`tests/test_findability.py` (or the file the row names); that file is the contract and is never weakened to make a
change pass.

| | Invariant | How | Test |
|---|---|---|---|
| F1 | **The frame document is a superset.** Every string that today's index stores for a frame (each region's text, the model's reading of a disagreeing line, association text, the frame description, the app and window names) has a counterpart line in the one whole-screen document of that frame. | Task 10 rules 2–7: every box's OCR text (no box is left out for any label), the model's reading where it differs, missed texts, link lines, container names, the description in force | `test_frame_document_is_a_superset` |
| F2 | **Same matcher.** A query that matched a today-document of frame *f* matches the new document of *f*: the FTS5 tokenizer string, the trigram table and the query builders are unchanged, and the new document contains the old one's lines. One document per frame also keeps "terms in different boxes or windows match one document" (spec §6). | Task 10 rule 1 keeps `open_db`'s two virtual tables and `fts_query`, `trigram_query` byte for byte | `test_tokenizers_and_query_builders_unchanged` |
| F3 | **Additive documents cannot displace frame documents.** Lifetime and transition entries are ranked in their own lists and fused; a frame hit's fused score does not depend on how many lifetime entries match. | Task 13 rules 2–3, 7 (per-family rankings, reciprocal-rank fusion) | `test_many_lifetime_hits_do_not_displace_the_frame_hit` |
| F4 | **Collapsing never drops.** Every frame hit before collapsing is a member of exactly one hit after it; the collapsed hit's frame and time range cover every member; collapsing happens before the top-k cut, so it can only make room. The matcher used to decide "identical matching text" errs towards more lines, so it collapses less, never more. | Task 13 rules 4–6, 8 | `test_collapse_is_a_partition_of_the_frame_hits` |
| F5 | **Every reading is indexed.** A lifetime entry holds the majority reading of each reader and every variant; a run is indexed with both joins; a pair as `key value`. A wrong joiner, a wrong majority or a wrong reader cannot hide a string. | Task 11 rules 3–5 | `test_every_reading_and_both_joins_are_searchable` |
| F6 | **Labels cannot remove text.** Without `annotations.jsonl`, or with a record whose `error` is set, every OCR text is still indexed. `non_text` can remove a lifetime entry only when every annotated sighting said so, and never a line of a frame document. | Task 10 rule 3, Task 11 rule 2, Task 12 rule 6 | `test_index_without_annotations_holds_every_ocr_text`, `test_non_text_never_removes_a_frame_line` |
| F7 | **Nothing about a frame is unreachable.** `ask`'s frame tool returns the image, the texts alive at that frame and the description in force. | Task 14 rule 5 | `test_get_frame_returns_image_texts_and_description` (`tests/test_ask.py`) |

**What is not guaranteed, stated plainly.** Today a model-proposed row joined several OCR marks into one line, so a
quoted phrase spanning two marks of one visual row matched. Rows are gone (spec §3). In the frame document a quoted
phrase still matches across two boxes when they are adjacent in reading order (FTS5 treats the line break as a
separator) or joined by a link line; it does not when reading order separates them. No row-banding rule is
re-introduced to close this. P1 reads it on the question set; the ledger row for P1 must report any question lost to it.

## Review Focus

Inputs the spec implies and that are most likely to bite; each has a test in the task that owns the code.

1. **A run with no `annotations.jsonl`, or with annotation records whose `error` is set.** Expect every stage to run,
   change text without labels, frame documents with every OCR text, no description, no crash (Task 4
   `test_render_without_labels`, Task 12 `test_index_without_annotations_holds_every_ocr_text`, Task 16
   `test_pipeline_end_to_end_without_annotations`).
2. **The model cites what it was not handed:** an id of an unchanged box, a bare `b33`, a transition id, a duplicate,
   trailing spaces. Expect those dropped and counted, the valid ones kept in order, no re-prompt (Task 5
   `test_validate_citations`).
3. **Queries full of FTS5 syntax:** `--name`, `C:\Users\me>`, an unbalanced `"`, `*`, a one-character term. Expect no
   SQLite error and hits where the text exists (Task 13 `test_search_survives_fts_syntax`).
4. **`ask` when things go wrong inside the loop:** an unknown tool name, a tool that raises, an unknown frame, a
   `refusal` or `max_tokens` stop, the turn limit. Expect a clear answer string, usage still reported, no exception
   (Task 15 `test_ask_tool_errors_and_stops`).
5. **Interpretations missing or failed for some transitions** (refusal, schema failure, a missing PNG). Expect
   `summarize` and `index` to use the measured text for those items and carry on (Task 9
   `test_summarize_with_a_failed_interpretation`, Task 12 `test_transition_node_without_interpretation`).

## File structure at the end of this plan

```
src/scry/
  schemas.py        + Interpretation, ModelInterpretation, SegmentStart, ModelBoundaries, ModelElaboration, HierNode
  run.py            + paths interpretations, steps, sections, video, index_db; their loaders
  config.py         + ModelConfig.effort_interpret/effort_summarize/effort_ask; InterpretConfig [interpret];
                      SummarizeConfig [summarize]; IndexConfig.collapse; AskConfig [ask]
  costs.py          + stage_cost, run_costs (the honest token accounting itself lands with plan 2's Task 8, A6)
  changetext.py     a change record as text: box_label, render_change, render_change_line, change_rects
  interpret.py      image modes, build_blocks, validate_citations, run_interpret
  summarize.py      boundary and elaboration passes over the new records, run_summarize
  nodes.py          node extraction: frame_nodes, lifetime_nodes, transition_nodes, summary_nodes, extract_nodes
  index.py          Node and schema (layout_conf gone), build_index, search with families and collapsing
  ask.py            Tools, TOOL_DEFS, AskResult, extract_citations, ask
  prompts/          __init__.py, interpret.py, summarize.py, ask.py      (annotate.py is plan 2's)
  cli.py            + interpret, summarize, index, search, ask; run over the eight stages; cost summary
tests/
  fakes.py minirun.py
  test_costs.py test_changetext.py test_interpret.py test_summarize.py test_nodes.py test_index.py
  test_findability.py test_ask.py test_cli.py test_pipeline.py
```

> **Fixture M (the mini run), built by `tests/minirun.py` (Task 1) and used by Tasks 4–16.** Invented content; four
> emitted frames of a 400×200 screen: a portal pane whose `Status` value changes, and a terminal where `git status` is
> entered with a shell suggestion showing, then submitted.
>
> *Frames* (`video_id "v"`, `settled` true, `width 400`, `height 200`, `sha256 "sha<frame>"`, `png
> "frames/000<frame>.png"`, no churn, no caret), as `(frame: t_change, t_settled, t_end)`: `10: 20.0, 20.4, 24.0` ·
> `11: 24.0, 24.4, 26.0` · `12: 26.0, 26.4, 30.0` · `13: 30.0, 30.4, 35.0`. Each PNG is a white 400×200 RGB image with a
> black rectangle pasted at `(100 + 5·(frame − 10), 150, 120 + 5·(frame − 10), 170)`, so the four images differ.
> Manifest: `video "v.mp4"`, `video_id "v"`.
>
> *Boxes* (`conf 1.0`, all 18 px tall):
> frame 10: `b1 "Status" (10,10,70,28)`, `b2 "Creating" (200,10,280,28)`, `b3 "C:\src> git" (10,100,120,118)`;
> frame 11: `b1`, `b2` as in 10, `b3 "C:\src> git status" (10,100,190,118)`;
> frame 12: `b1`, `b2`, `b3` as in 11, `b4 "On branch main" (10,120,150,138)`, `b5 "C:\src>" (10,140,80,158)`;
> frame 13: `b1` as before, `b2 "Succeeded" (200,10,290,28)`, `b3` as in 11, `b4 "On branch maln" (10,120,150,138)`
> (an OCR variant on unchanged pixels), `b5` as in 12.
>
> *Changes* (`kind "single"`; `t = (a.t_end, b.t_settled)` as plan 1 writes it; `PixelStats(changed_fraction,
> components, textless, textless_area, touched_share, rect_only)`):
> `T1` 10→11, `t (24.0, 24.4)`, pixels `(0.002, 1, 0, 0, 0.3333, 0)`, one group `appended`, rect `(10,100,190,118)`,
> before `[("10:b3", "C:\src> git")]`, after `[("11:b3", "C:\src> git status")]`, `char_diff [["=", "C:\src> git"],
> ["+", " status"]]`, `continues None`; `unchanged 2`.
> `T2` 11→12, `t (26.0, 26.4)`, pixels `(0.005, 2, 0, 0, 0.0, 0)`, no groups, `appeared ["12:b4", "12:b5"]`;
> `unchanged 3`.
> `T3` 12→13, `t (30.0, 30.4)`, pixels `(0.001, 1, 0, 0, 0.2, 0)`, one group `changed`, rect `(200,10,290,28)`, before
> `[("12:b2", "Creating")]`, after `[("13:b2", "Succeeded")]`, `char_diff [["-", "Creating"], ["+", "Succeeded"]]`;
> `unchanged 4`, `variants 1`.
>
> *Lifetimes* (`first (frame, t)`, `last (frame, t)`):
> `L1 "Status"` readings `{"Status": 4}`, sightings 4, first `(10, 20.4)`, last `(13, 35.0)`, boxes `10:b1 … 13:b1`;
> `L2 "Creating"` `{"Creating": 3}`, 3, `(10, 20.4)`, `(12, 30.0)`, boxes `10:b2, 11:b2, 12:b2`;
> `L3 "C:\src> git"` 1, `(10, 20.4)`, `(10, 24.0)`, `10:b3`;
> `L4 "C:\src> git status"` `{"C:\src> git status": 3}`, 3, `(11, 24.4)`, `(13, 35.0)`, `11:b3, 12:b3, 13:b3`;
> `L5 "On branch main"` `{"On branch main": 1, "On branch maln": 1}`, `unstable` true, 2, `(12, 26.4)`, `(13, 35.0)`,
> `12:b4, 13:b4`; `L6 "C:\src>"` 2, `(12, 26.4)`, `(13, 35.0)`, `12:b5, 13:b5`;
> `L7 "Succeeded"` 1, `(13, 30.4)`, `(13, 35.0)`, `13:b2`. All others `unstable` false, `moved` false.
>
> *Annotations, only with `labels=True`* (one §5 record per frame, every box a target, transcribing, `repairs 0`,
> `model "fake-model"`, `prompt_version "annotate-v1"`, `usage {}`, `error null`, `unassigned []`). Containers in every
> record: `c1` window, app `"Azure Portal"`, name `"Resource overview"`, owner null, covers `[]`; `c2` window, app
> `"Windows Terminal"`, name `"PowerShell"`, owner null, covers `["c1"]`; `rect` null. Assign: `b1`, `b2` → `c1` with
> pane `"Essentials"`; `b3`, `b4`, `b5` → `c2`, pane null. Links in every record: `{"kind": "pair", "key": ["b1"],
> "value": ["b2"]}`. Texts equal the OCR text of each box, except `11:b3` → `"C:\src> git st"` (the model leaves the
> grey suggestion out) and `13:b4` → `"On branch main"`. Missed: only frame 13, `{"id": "m1", "text": "Refresh",
> "container": "c1"}`. Descriptions: frames 10 and 11 `"The Overview item is highlighted in the left navigation."`;
> frame 12 `"The terminal shows new output."`; frame 13 `"The Status value now reads Succeeded."`.
> So, through plan 2's view: `11:b3` and `13:b4` have `agree` false, every other box `agree` true; `L4`'s model
> readings are `{"C:\src> git status": 2, "C:\src> git st": 1}`, majority `"C:\src> git status"`, `agree` true; `L5`'s
> model majority is `"On branch main"`, `agree` true.
>
> *Interpretations, written by `mini_interpretations(run)`* (for the tasks downstream of `interpret`; `confidence` as
> given, `images "scaled"`, `model "fake-model"`, `prompt_version "interpret-v1+scaled0.5"`, `usage {}`):
> `T1`: action `The user typed " st" in the terminal; the shell offers "atus" as a completion.`, result `The command
> line now reads git st with a greyed suggestion.`, description `""`, confidence 0.8, `entered_text "git st"`,
> `submitted "no"`, citations `["11:b3"]`.
> `T2`: action `The user pressed Enter.`, result `Git printed "On branch main" and a new prompt appeared.`, description
> `""`, 0.9, `entered_text "git status"`, `submitted "yes"`, citations `["12:b4", "12:b5"]`.
> `T3`: action `No user action is evident; the portal refreshed.`, result `The Status value changed from Creating to
> Succeeded.`, description `""`, 0.7, `entered_text null`, `submitted "no"`, citations `["13:b2"]`.

---

### Task 1: Records, run paths, test fakes and the mini run

**Files:**
- Modify: `src/scry/schemas.py`, `src/scry/run.py`, `tests/test_schemas.py`, `tests/fakes.py` (from plan 2's Task 8, A6)
- Create: `tests/minirun.py`, `tests/test_minirun.py`

**Interfaces:**
- Consumes: A1, A4, A6 (`VlmResult`, `USAGE`), A7.
- Produces (pydantic `BaseModel`s in `scry.schemas`):

```
Submitted        = Literal["yes", "no", "unclear"]
Interpretation   id: str · action: str | None = None · result: str | None = None · description: str | None = None ·
                 confidence: float | None = None · entered_text: str | None = None · submitted: Submitted | None = None ·
                 citations: list[str] = [] · invalid_citations: int = 0 · images: str | None = None (the image mode
                 actually sent) · usage: dict = {} · model: str | None = None · prompt_version: str | None = None ·
                 error: str | None = None
SegmentStart     start_id: str · label: str                       (field descriptions as at the tag)
ModelBoundaries  segments: list[SegmentStart]                     (was VlmBoundaries)
ModelElaboration label: str · description: str · refs: list[str] = []   (was VlmElaboration; descriptions as at the tag)
HierNode         id: str · level: Literal["step", "section", "video"] · children: tuple[str, str] · frames: tuple[int, int] ·
                 t: tuple[float, float] · label: str · description: str · refs: list[str] = [] ·
                 segmentation_conf: Literal["high", "low"] = "high"          (unchanged from the tag)
```

- `Run` gains paths `interpretations` (`interpretations.jsonl`), `steps` (`steps.jsonl`), `sections` (`sections.jsonl`),
  `video` (`video.json`), `index_db` (`index.sqlite`) and loaders `load_interpretations() -> dict[str, Interpretation]`
  (keyed by id), `load_steps() -> list[HierNode]`, `load_sections() -> list[HierNode]`, `load_video() -> HierNode | None`.
- `tests/fakes.py` gains (it already holds `FakeMessages`, `fake_client`, `USAGE` and `AnswerProvider`, A6):
  - `class ScriptedProvider(script: dict[str, list])` with `model = "fake-model"`, `calls: list[dict]`, `stats`,
    `usage_by_stage`. `complete(**kw)` records `kw`, takes the script key that is the longest prefix of `kw["stage"]`,
    pops its first item and returns `VlmResult(parsed=item, error=None, usage=dict(USAGE))` when the item is a pydantic
    model, or `VlmResult(None, item, usage=dict(USAGE))` when it is a string (an error such as `"refusal"`). A script
    value may instead be a callable taking `kw` and returning such an item, for tests that must not depend on the order
    in which concurrent calls arrive. An empty list or no matching key raises `AssertionError` naming the stage.
  - `class FakeSyncMessages(script)` with `calls` and `create(**kw)` popping the next scripted response, and
    `fake_sync_client(script)`. Helpers `tool_use(id, name, input)`, `text(s)` and `response(content, stop_reason,
    usage=None)` build `SimpleNamespace` blocks and responses; the default usage is `input_tokens 1000, output_tokens
    100`, both cache counts 0.
- `tests/minirun.py`: `mini_run(tmp_path: Path, labels: bool = False) -> Run` writes Fixture M (the PNGs, the manifest,
  `frames.jsonl`, `boxes.jsonl`, `changes.jsonl`, `lifetimes.jsonl`, and with `labels=True` the four hand-written
  `annotations.jsonl` lines as JSON objects in §5's shape); `mini_interpretations(run: Run) -> None` writes the three
  interpretations of Fixture M.

**Rules:**
1. Field names follow spec §5: `interpretations.jsonl` "keeps action, result, description, confidence and citations,
   and gains `entered_text` … and `submitted` (`yes`, `no`, `unclear`)". `citations` is a flat list of
   `"<frame>:<box_id>"` strings (spec §3), replacing the tag's `refs.lines`.
2. All models keep pydantic's default `extra="ignore"` so a later stage may add fields (plan 1 Task 4 rule 3).
3. `load_video` returns `None` when `video.json` is absent. `load_interpretations` returns `{}` for an absent file.
4. The fakes make no network call and import nothing from `anthropic`.
5. `tests/` has no `__init__.py`, and pytest's default import mode puts it on `sys.path`: the helpers are imported as
   top-level modules (`from fakes import ScriptedProvider`, `from minirun import mini_run`), as `conftest.py` is today.

**Tests to write first:**
- `tests/test_schemas.py::test_interpretation_round_trip`: `Interpretation(id="T2", action="a", result="r",
  description="", confidence=0.9, entered_text="git status", submitted="yes", citations=["12:b4"], invalid_citations=2,
  images="scaled", usage={"input_tokens": 1})` written with `write_jsonl` and read with `read_jsonl` is equal;
  `Interpretation(id="T9", submitted="maybe")` raises `pydantic.ValidationError`.
- `::test_stage_loaders_on_a_fresh_run`: `Run(tmp_path / "r")` gives `load_interpretations() == {}`, `load_steps() ==
  []`, `load_sections() == []`, `load_video() is None`.
- `tests/test_minirun.py::test_mini_run_loads`: `mini_run(tmp_path)` → 4 frames, 4 box records with 3, 3, 5, 5 boxes,
  changes `["T1", "T2", "T3"]`, 7 lifetimes, `run.load_labels() is None`; every box ref of every frame occurs in exactly
  one lifetime's `boxes` (A2).
- `::test_mini_run_labels`: `mini_run(tmp_path, labels=True)` → `labels = run.load_labels()` is not `None`;
  `labels.box("11:b3").agree is False` and `.vlm == "C:\\src> git st"`; `labels.box("13:b2").link.role == "value"` and
  `.link.key == ["13:b1"]`; `labels.frame(13).description == "The Status value now reads Succeeded."`;
  `[m.text for m in labels.frame(13).missed] == ["Refresh"]`; `labels.lifetime("L5").vlm == "On branch main"`. (This
  test is the tripwire for A4: if it fails, reconcile with plan 2 before going on.)
- `::test_scripted_provider`: `ScriptedProvider({"interpret": [m1, "refusal"]})`: two `complete(stage="interpret", …)`
  calls return `m1` then `error == "refusal"`, both with `usage == USAGE`; a third raises `AssertionError`.

- [ ] **Step 1:** Write the tests and the two helper modules' tests. Run `uv run pytest tests/test_minirun.py
  tests/test_schemas.py -q`. Expected: FAIL (`ImportError: Interpretation`, `No module named 'minirun'`).
- [ ] **Step 2:** Add the models, paths and loaders; write `tests/fakes.py` and `tests/minirun.py`.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat: records and run paths for interpret, summarize and index; test fakes and the mini run`

### Task 2: Config keys

**Files:**
- Modify: `src/scry/config.py`, `scry.toml`, `tests/test_config.py`

**Interfaces (every model `extra="forbid"`, A3):**

```
ModelConfig       + effort_interpret: Effort = "low"       # was effort_stage5
                  + effort_summarize: Effort = "medium"    # was effort_stage6
                  + effort_ask: Effort = "high"            # was effort_agent
InterpretConfig   images: Literal["scaled", "crops", "full"] = "scaled"   # ledger L39
  [interpret]     scale: float = Field(0.5, gt=0, le=1)    # scaled and crops: both frames downscaled by this factor
                  crop_pad: float = 2.0                     # crops: each changed text rectangle grows by this × the median box height of the two frames
                  crop_max: int = 4                         # crops: at most this many rectangles; the pair whose union adds least area merges until it holds
                  crop_max_fraction: float = 0.25           # crops: with more of the screen changed than this, or no pixel data, the call is sent scaled
                  context_transitions: int = 3              # preceding transitions rendered one line each
SummarizeConfig   window: int = 2000 · overlap: int = 200 · fallback_step_transitions: int = 20 ·
  [summarize]     fallback_section_steps: int = 8           # unchanged from the tag's HierarchyConfig
IndexConfig       embedder, k = 20, k_filtered = 50, rrf = 60 (kept) + collapse: bool = True   # collapse identical consecutive frame hits in the result list
AskConfig         prompt: str = "ask-v1"                    # the named variant of the agent's system prompt (scry.prompts.ask.PROMPTS)
  [ask]           max_turns: int = 12                       # model turns before the loop gives up
                  max_tool_result_chars: int = 60000        # a JSON tool result longer than this is cut
                  redecode_max_frames: int = 6              # frames one redecode call may return
Config            + interpret: InterpretConfig · summarize: SummarizeConfig · ask: AskConfig
```

**Rules:**
1. Defaults are the tag's values (design §16), except `crop_pad`, which was 40 px measured on the sample (L39) and is
   now relative to box height (Decision D4), and the `text` image mode, which is gone (D4).
2. `scry.toml` gains the four sections with the defaults written out, and the three effort keys under `[model]`.

**Tests to write first (`tests/test_config.py`):**
- `test_stage_sections_defaults`: `Config()` has `interpret.images == "scaled"`, `interpret.scale == 0.5`,
  `interpret.crop_pad == 2.0`, `summarize.window == 2000`, `index.collapse is True`, `ask.max_turns == 12`, `ask.prompt == "ask-v1"`,
  `model.effort_interpret == "low"`, `model.effort_summarize == "medium"`, `model.effort_ask == "high"`.
- `test_old_stage_keys_are_rejected`: a TOML holding `[stage5]\nimages = "scaled"` raises `pydantic.ValidationError`; so
  do `[hierarchy]\nwindow = 5`, `[interpret]\nimages = "text"` and `[model]\neffort_stage5 = "low"`.
- `test_repo_toml_loads` (exists from plan 1) additionally asserts `cfg.interpret.images == "scaled"` and
  `cfg.ask.max_turns == 12`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_config.py -q`. Expected: FAIL (`Config` has no
  `interpret`).
- [ ] **Step 2:** Add the models, fields and TOML sections.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(config): [interpret], [summarize], [ask], index.collapse and the three effort keys`

### Task 3: Cost per stage and per run

Plan 2's Task 8 has already made the accounting honest (A6): cache-creation tokens are priced at 1.25 × input, usage
is summed over a request's retries, and batch results keep all four keys. This task adds the two functions the stages
and `scry run` report with. (If plan 2's Task 8 has not landed, execute it first; it is self-contained.)

**Files:**
- Modify: `src/scry/costs.py`, `tests/test_costs.py`

**Interfaces:**
- Consumes: `estimate_cost(usage: dict, model: str, batch: bool = False) -> float`, `add_usage`, `USAGE_KEYS` (A6).
- Produces, in `scry.costs`: `stage_cost(usage: dict, model: str) -> dict`; `run_costs(manifest: dict) -> dict`.

**Rules** (spec §4 principle 9 and §9: "dollars per frame, and per video", beside every number):
1. `stage_cost` = `{"cost_usd": estimate_cost(usage, model), "cost_usd_batch": estimate_cost(usage, model,
   batch=True)}`. Both prices are reported because one stage execution can mix cache hits from an earlier synchronous
   run with batch results; the manifest does not guess which price was paid (Decision D18).
2. `run_costs`: for every `stages.<name>` entry that has a `usage` dict: `{"usage": that dict, **stage_cost(usage,
   entry.get("model", ""))}`. Result: `{"stages": {name: …}, "total_usd": Σ cost_usd, "total_usd_batch": Σ
   cost_usd_batch, "frames": stages.decode.emitted or None, "per_frame_usd": round(total_usd / frames, 4) or None when
   frames is missing or 0}`; totals rounded to 4 places. No projection to the sample's 221 frames is computed here.

**Tests to write first (`tests/test_costs.py`):**
- `test_stage_cost`: `stage_cost(dict(USAGE), "fake-model") == {"cost_usd": 0.004, "cost_usd_batch": 0.002}` (100 × 5 +
  20 × 25 + 1000 × 0.5 + 400 × 6.25 = 4000 millionths of a dollar).
- `test_run_costs`: manifest `{"stages": {"decode": {"emitted": 4}, "track": {"transitions": 3}, "interpret":
  {"usage": {"input_tokens": 300, "output_tokens": 60, "cache_read_input_tokens": 3000, "cache_creation_input_tokens":
  1200}, "model": "claude-opus-5"}}}` → `stages == {"interpret": {"usage": …, "cost_usd": 0.012, "cost_usd_batch":
  0.006}}`, `total_usd 0.012`, `total_usd_batch 0.006`, `frames 4`, `per_frame_usd 0.003`. `run_costs({})` →
  `{"stages": {}, "total_usd": 0.0, "total_usd_batch": 0.0, "frames": None, "per_frame_usd": None}`. A stage entry
  with zero usage (plan 2's `annotate` with `mode = "off"`) contributes `0.0` and is listed.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_costs.py -q`. Expected: FAIL (`ImportError:
  stage_cost`).
- [ ] **Step 2:** Implement rules 1–2.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(costs): stage_cost and run_costs: dollars per stage, per run and per frame, sync and batch`

### Task 4: A change record as text, with the ids that may be cited

**Files:**
- Create: `src/scry/changetext.py`, `tests/test_changetext.py`

**Interfaces:**
- Consumes: `Change`, `Group`, `Revert`, `FrameBoxes`, `parse_box_ref` (A1, A2); `Labels`, `BoxLabel`, `BoxLink` (A4).
- Produces (pure functions, no I/O; `boxes` is `{frame: FrameBoxes}`):
  - `text_of(ref: str, boxes: dict[int, FrameBoxes]) -> str`
  - `box_label(ref: str, labels: Labels | None, boxes: dict[int, FrameBoxes]) -> str`
  - `render_change(c: Change, boxes: dict[int, FrameBoxes], labels: Labels | None) -> tuple[str, list[str]]` — the text
    and the citable ids in order of first appearance
  - `render_change_line(c: Change) -> str`
  - `change_rects(c: Change, boxes: dict[int, FrameBoxes]) -> list[BBox]`

**Rules** (spec §6 `interpret`; §4 principle 3: the text reports that text appeared, changed, moved or was removed at a
place, with before and after; it never says "typed"):
1. `text_of`: the OCR text of the box named by the ref; an unknown frame or box id raises `ValueError` naming the ref
   (the records come from one `track` run over one `boxes.jsonl`; a miss means the run directory is inconsistent).
2. `box_label` joins with `", "` the parts that exist, and is `""` when `labels` is `None`, the box has no label or no
   part exists:
   a. container: `"{app} {kind}"`; with an empty `app`, `"{name} {kind}"`; with both empty, `"{kind}"`;
   b. `pane`, when set;
   c. the link role: `value` → `value of "{K}"`, K = the OCR texts of the link's `key` refs joined with one space;
      `key` → `label of "{V}"`, V likewise from `value`; `run` → `part of a wrapped text`; `member` → `table cell`;
      `header` → `table heading`.
3. `render_change`, line by line; a line in a bracket list below is emitted only when its condition holds:
   - `Transition {id}: frame {from_frame} → frame {to_frame}, t={t[0]:.2f}–{t[1]:.2f}s.` (`t` is the interval in
     which the change happened, A2; the frames' own times are in the image captions)
   - `Pixels changed: {100·changed_fraction:.2f}% of the screen; changed areas: {components}.` — or, with `pixels`
     null, `Pixels: no comparison is available for this pair.`
   - when there are groups: `Text changes:` then one line per group, in record order:
     `[{ids}] {label}: {body}{suffix}`, where `{ids}` is the group's `after` refs then its `before` refs joined with
     `", "`; `{label}: ` is `box_label` of the first `after` ref and is omitted with its colon when empty; a side's
     texts are each wrapped in straight double quotes, unescaped, and joined with `" + "` (call them `B` and `A`);
     `{body}` by kind: `appended` → `{B} → appended "{plus}"; now {A}` · `truncated` → `{B} → truncated, removed
     "{minus}"; now {A}` · `changed` → `{B} → {A}` · `reread` → `{B} re-read as {A} (same text)`; `plus` is the
     concatenation of the `+` runs of `char_diff`, `minus` of the `-` runs; `{suffix}` is `; continues {X}` when
     `continues` is set, X being the part of it before `/`, then ` [area was animating]` when `in_churn`.
   - when `appeared` is non-empty: `Appeared:` then `[{ref}] {label}: "{text}"` per ref; when `removed` is non-empty:
     `Removed:` likewise. The label and colon are omitted when empty.
   - under any line above, for each of its refs in bracket order whose label has `agree is False` and a non-empty
     `vlm`: `    model reads {ref}: "{vlm}"` (four spaces; spec: "the model's reading sits beside OCR's where two
     readings differ").
   - `Texts that only moved: {moved}.` when `moved > 0`; `Boxes with a visual change over unchanged text:
     {same_place}.` when `same_place > 0`; `Changed areas without text: {textless}.` when `pixels` is not null and
     `textless > 0` (spec: "moved and textless counts are one line each").
   - per `reverts` entry: `Undoes {of}'s change after {hold_s:.1f} s, in the area {x0},{y0},{x1},{y1}.`
   - `One of these frames was captured while the screen was still changing.` when `kind == "unsettled"`.
   - `No text change was recorded; look for a change that is not text.` when there are no groups, nothing appeared and
     nothing was removed.
   Nothing is capped or abbreviated: a page load lists every appeared and removed box, because every listed id is
   citable (spec H5: one record shape for a keystroke and a page load).
4. The citable ids are exactly the refs printed inside square brackets, in order of first appearance, without repeats.
5. `render_change_line`: `{id} [f{from_frame}→f{to_frame}, {t[0]:.1f}–{t[1]:.1f}s] ` followed by these parts joined
   with `"; "`: for each of the first three groups `{kind} "{cut(after)}"` (`after` = the group's after texts joined
   with one space; `cut(s)` is `s` when `len(s) ≤ 80`, else `s[:79] + "…"`); `+{n} more text changes` when there are
   `n > 0` further groups; `appeared {n}`, `removed {n}`, `moved {n}` for each `n > 0`; `undoes {of}` per revert; and
   `no text change` when no part exists. It is mechanical, so it exists before any model call and keeps `interpret`
   parallel and batchable (design §12).
6. `change_rects`: the `rect` of each group in order, then the `bbox` of each appeared box, then of each removed box
   (OCR's coordinates, spec §6: they "serve code in … crops for `interpret`").

**Tests to write first** (Fixture M unless a fixture is given):
- `test_render_keystroke_with_labels`: `render_change(T1, boxes, labels)` returns the text
  ```
  Transition T1: frame 10 → frame 11, t=24.00–24.40s.
  Pixels changed: 0.20% of the screen; changed areas: 1.
  Text changes:
  [11:b3, 10:b3] Windows Terminal window: "C:\src> git" → appended " status"; now "C:\src> git status"
      model reads 11:b3: "C:\src> git st"
  ```
  and the ids `["11:b3", "10:b3"]`.
- `test_render_value_change_names_its_pair`: T3 with labels → third and fourth lines are `Text changes:` and
  `[13:b2, 12:b2] Azure Portal window, Essentials, value of "Status": "Creating" → "Succeeded"`.
- `test_render_without_labels`: T1 with `labels=None` → the group line is `[11:b3, 10:b3] "C:\src> git" → appended
  " status"; now "C:\src> git status"` and no `model reads` line; T2 → the text
  ```
  Transition T2: frame 11 → frame 12, t=26.00–26.40s.
  Pixels changed: 0.50% of the screen; changed areas: 2.
  Appeared:
  [12:b4] "On branch main"
  [12:b5] "C:\src>"
  ```
  and ids `["12:b4", "12:b5"]`.
- `test_render_every_annotation`: boxes frame 20 `b2 "PS> git status" (10,50,230,68)`, `b7 "Cloud Shell"
  (305,101,375,119)`; frame 21 `b2 "PS> git" (10,50,170,68)`; `Change(id="T5", from_frame=20, to_frame=21, t=(50.0,
  52.5), kind="unsettled", pixels=PixelStats(0.00023, 2, 1, 40, 0.01, 0), groups=[Group(kind="truncated",
  rect=(10,50,230,68), before=[("20:b2", "PS> git status")], after=[("21:b2", "PS> git")], char_diff=[["=", "PS> git"],
  ["-", " status"]], continues="T4/0", in_churn=True)], removed=["20:b7"], moved=12, same_place=1,
  reverts=[Revert(of="T4", rect=(300,100,380,120), hold_s=3.4)])`, no labels → exactly
  ```
  Transition T5: frame 20 → frame 21, t=50.00–52.50s.
  Pixels changed: 0.02% of the screen; changed areas: 2.
  Text changes:
  [21:b2, 20:b2] "PS> git status" → truncated, removed " status"; now "PS> git"; continues T4 [area was animating]
  Removed:
  [20:b7] "Cloud Shell"
  Texts that only moved: 12.
  Boxes with a visual change over unchanged text: 1.
  Changed areas without text: 1.
  Undoes T4's change after 3.4 s, in the area 300,100,380,120.
  One of these frames was captured while the screen was still changing.
  ```
  and ids `["21:b2", "20:b2", "20:b7"]`. The word `typed` occurs nowhere in the output.
- `test_render_nothing_recorded`: a change with no groups, `appeared`, `removed` and `pixels=None` → lines 2 and 3 are
  `Pixels: no comparison is available for this pair.` and `No text change was recorded; look for a change that is not
  text.`; ids `[]`.
- `test_render_multi_box_sides_and_reread`: a `changed` group with before `[("1:b1", "a"), ("1:b2", "b")]` and after
  `[("2:b1", "a b c")]` → `[2:b1, 1:b1, 1:b2] "a" + "b" → "a b c"`; a `reread` group `"A b"` → `"Ab"` renders `"A b"
  re-read as "Ab" (same text)`.
- `test_box_label_parts`: with labels, `box_label("13:b1", …) == 'Azure Portal window, Essentials, label of
  "Succeeded"'`; `box_label("11:b3", …) == "Windows Terminal window"`; with `labels=None` → `""`.
- `test_render_change_line`: T1 → `T1 [f10→f11, 24.0–24.4s] appended "C:\src> git status"`; T2 → `T2 [f11→f12,
  26.0–26.4s] appeared 2`; T3 → `T3 [f12→f13, 30.0–30.4s] changed "Succeeded"`; the T5 of the test above →
  `T5 [f20→f21, 50.0–52.5s] truncated "PS> git"; removed 1; moved 12; undoes T4`; five groups → three quoted parts and
  `+2 more text changes`; an after text of 100 `x` → 79 `x` and `…`; an empty change → `… no text change`.
- `test_change_rects`: T1 → `[(10,100,190,118)]`; T2 → `[(10,120,150,138), (10,140,80,158)]`.
- `test_unknown_ref_raises`: `text_of("99:b1", boxes)` raises `ValueError` containing `99:b1`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_changetext.py -q`. Expected: FAIL (`No module named
  scry.changetext`).
- [ ] **Step 2:** Implement rules 1–6.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat: render a change record as text with citable box ids and labels (spec §6 interpret)`

### Task 5: The `interpret` prompt, its output schema, and citation validation

**Files:**
- Create: `src/scry/prompts/interpret.py`, `src/scry/interpret.py` (first part), `tests/test_interpret.py`
- Create if absent: `src/scry/prompts/__init__.py` (A6)
- Modify: `src/scry/schemas.py`

**Interfaces:**
- Produces:
  - `scry.prompts.interpret.VERSION = "interpret-v1"` and `SYSTEM: str` (the text below, verbatim).
  - `scry.schemas.ModelInterpretation` (what the model returns; the field descriptions are part of the contract):
    `action: str` — "The single user action that best explains the change, or that no user action is evident." ·
    `result: str` — "What visibly changed as a consequence, including changes that are not text." ·
    `description: str` — "Anything else visible and relevant: a suggestion an input field showed, a disagreement between
    your reading and the listed strings." ·
    `confidence: float` — "0 to 1: confidence in action, entered_text and submitted together." ·
    `entered_text: str | None` — "The text the user has entered in the input being edited, as it stands in Frame b,
    without anything the application suggested; the whole submitted text when this transition shows a submission; null
    when the user entered nothing." ·
    `submitted: Submitted` — "yes, no or unclear: whether what was entered took effect, judged only from these frames." ·
    `citations: list[str] = []` — "Ids copied exactly from the square brackets in Changes, e.g. '41:b17'."
  - `scry.interpret.validate_citations(cited: list[str], allowed: list[str]) -> tuple[list[str], int]`

**Rules:**
1. The span-2 baseline produced 53 invalid citations in 30 transitions because its prompt never named the ids it could
   cite (spec §1). The prompt therefore explains the bracketed ids, and the call is handed them by Task 4's renderer.
2. `validate_citations`: comparison is exact string equality (no stripping, no case folding). The valid list holds the
   cited entries that are in `allowed`, first occurrence only, in cited order. The count is the number of cited entries
   (repeats included) that are not in `allowed`. No re-prompt (design §12).
3. The prompt states the honest contract (spec §4 principles 3–4): the list does not know who changed a text; the
   strings are OCR readings; an input field may show a suggestion; persistence says nothing. Its examples are invented,
   never the sample video's commands (they would leak the evaluation's answers).

**The system prompt** (as the model receives it; escape as the language requires):

```
You interpret what happened between two consecutive captured states of a screen recording of a computer tutorial.

You receive, in order: context (the chapter, when known, and one line for each of the transitions just before this
one); the two screenshots, "Frame a" then "Frame b", downscaled or at full size as each caption says, sometimes
followed by full-resolution crops of the areas where text changed; and "Changes", a list computed from the pixels and
from an OCR engine's text boxes.

What the Changes list is, and what it is not. It records that text appeared, changed, moved or was removed at a place,
with the text before and after. It does not know who or what changed it: a keystroke, a pasted string, a program
printing output and an application offering a suggestion all look the same in it. Deciding which it was is your job,
from the screenshots. The quoted strings are OCR readings: dependable for settled text, and sometimes wrong by a
character or a space on a line that is being edited. Quote them exactly when you rely on them. When a screenshot
clearly shows something else, say what you read and that it differs.

How to read a line. Every line you may cite begins with its ids in square brackets, such as [41:b17]: frame number,
colon, box id. A label after the ids (Windows Terminal window; value of "Status") is an earlier model's guess about
where the box sits: a hint, not a fact. "model reads" under a line is a second reading of the same box. "continues
T11" means the same piece of text also changed in the previous transition. "Undoes T4's change" means the area has
returned to how it looked before T4; describe this transition on its own terms all the same. Texts that only moved,
and changed areas that contain no text, are only counted: look at the screenshots for them.

Return a JSON object:
action: the single user action that best explains the change (entered text, pressed Enter, clicked, selected,
  scrolled, switched window, hovered), or that no user action is evident (output arriving, a page finishing loading,
  something animating).
result: what visibly changed as a consequence, including changes that are not text: a checkbox toggled, a row
  highlighted, a dialog opened, a window brought to the front.
description: anything else visible and relevant, including any suggestion an input field showed and any disagreement
  between your reading and the listed strings.
entered_text: the text the user has entered in the input being edited, as it stands in Frame b: what they typed or
  pasted, exactly as displayed, and nothing the application offered. An input field may show a suggestion the user did
  not enter: a shell's predicted command in grey after the cursor, an autocomplete entry, placeholder text. Leave it
  out. When this transition shows a command or a form being submitted, give the whole text that was submitted, even if
  you never saw it being typed. Do not include the prompt or the field's label. null when the user entered nothing.
submitted: "yes" when the frames show that what was entered took effect: output that answers the command, a new
  prompt below it, a form closing, a page navigating as a result. "no" when text was entered and is still being
  edited, or was cleared or replaced without taking effect, or when nothing was entered or submitted. "unclear" when
  these frames do not settle it. Judge only from what these two frames show. How long something stayed on screen says
  nothing about whether it ran.
confidence: 0 to 1, your confidence in action, entered_text and submitted together.
citations: the ids your statements rest on, copied exactly from the square brackets in Changes. An id that is not in
  Changes is discarded, so do not make one up for a box that did not change.

Worked example 1. Frame a shows a terminal whose last line is "C:\src> git". In Frame b the line shows "git st" in
white followed by "atus" in grey. Changes:
Transition T12: frame 40 → frame 41, t=82.60–83.05s.
Pixels changed: 0.03% of the screen; changed areas: 1.
Text changes:
[41:b17, 40:b17] Windows Terminal window: "C:\src> git" → appended " status"; now "C:\src> git status"; continues T11
A good answer:
{"action": "The user typed \" st\" after \"git\" in the terminal.", "result": "The line now shows \"git st\" followed by a greyed \"atus\": the shell is suggesting \"git status\".", "description": "The listed string includes the grey suggestion; only \"git st\" was entered.", "confidence": 0.85, "entered_text": "git st", "submitted": "no", "citations": ["41:b17"]}

Worked example 2, the next transition. Frame b shows "C:\src> git status" all in white, two lines of output under it
and a new empty prompt. Changes:
Transition T13: frame 41 → frame 42, t=84.10–84.60s.
Pixels changed: 0.41% of the screen; changed areas: 3.
Appeared:
[42:b18] Windows Terminal window: "On branch main"
[42:b19] Windows Terminal window: "nothing to commit, working tree clean"
[42:b20] Windows Terminal window: "C:\src>"
A good answer:
{"action": "The user finished the command and pressed Enter.", "result": "Git printed that the branch is main with a clean working tree, and a new prompt appeared below.", "description": "Frame b shows the command line as \"C:\\src> git status\" with no grey text.", "confidence": 0.9, "entered_text": "git status", "submitted": "yes", "citations": ["42:b18", "42:b19", "42:b20"]}

A poor answer reports "git status" as entered in example 1 (the suggestion was not entered), says a command ran
because its text was on the line, alters a quoted string ("git-status"), or cites an id that is not in Changes.
```

**Tests to write first (`tests/test_interpret.py`):**
- `test_validate_citations`: `validate_citations(["11:b3", "11:b9", "b3", "T1", "11:b3", "11:b3 ", "10:b3"], ["11:b3",
  "10:b3"]) == (["11:b3", "10:b3"], 4)`; `validate_citations([], ["11:b3"]) == ([], 0)`;
  `validate_citations(["11:b3"], []) == ([], 1)`.
- `test_prompt_contract` (every substring check on a prompt is made after collapsing whitespace runs to one space,
  `" ".join(SYSTEM.split())`, because the prompt text is hard-wrapped): `SYSTEM` contains each of `entered_text`, `submitted`, `"unclear"`, `square brackets`, `An
  input field may show a suggestion`, `How long something stayed on screen says nothing`; it contains none of `focus`,
  `az `, `kubectl`; `VERSION == "interpret-v1"`.
- `test_model_interpretation_schema`: `ModelInterpretation.model_json_schema()["required"]` holds `action`, `result`,
  `description`, `confidence`, `entered_text`, `submitted` and not `citations`; `submitted="maybe"` raises
  `ValidationError`; `entered_text=None` validates.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_interpret.py -q`. Expected: FAIL (`No module named
  scry.interpret`).
- [ ] **Step 2:** Write the prompt module, the schema and `validate_citations`.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(interpret): prompt interpret-v1 with entered_text, submitted and citable ids; citation validation`

### Task 6: `interpret`'s images and content blocks

**Files:**
- Modify: `src/scry/interpret.py`, `tests/test_interpret.py`

**Interfaces:**
- Consumes: `render_change`, `render_change_line`, `change_rects` (Task 4); `InterpretConfig` (Task 2);
  `scry.overlay.scale_image`, `scry.track.pixels.margin_px` (A3); `scry.providers.image_block`, `text_block`.
- Produces:
  - `prompt_version(ic: InterpretConfig) -> str`
  - `crop_boxes(rects: list[BBox], width: int, height: int, pad: int, cap: int) -> list[BBox]`
  - `image_mode(c: Change, ic: InterpretConfig, rects: list[BBox]) -> str`
  - `context_text(chapter: OutlineChapter | None, previous: list[Change]) -> str`
  - `build_blocks(c: Change, previous: list[Change], frames: dict[int, Frame], boxes: dict[int, FrameBoxes], labels:
    Labels | None, run: Run, chapter: OutlineChapter | None, ic: InterpretConfig) -> tuple[list[dict], list[str], str,
    str]` — the content blocks, the citable ids, the image mode actually used, and the hash input (rule 7)

**Rules** (spec §6: "Half-scale frames (L39), one call per non-trivial transition"; crops and full are options):
1. `prompt_version`: `VERSION + "+full"`, `VERSION + f"+scaled{scale:g}"`, or `VERSION +
   f"+crops{scale:g}p{crop_pad:g}m{crop_max}f{crop_max_fraction:g}"`, so one mode never hits another's cache entries.
2. `crop_boxes` is the tag's function unchanged: each rectangle grown by `pad` and clamped to the frame; empty ones
   dropped; overlapping rectangles merged until none overlap (positive-area overlap); while more than `cap` remain, the
   pair whose union adds the least area is merged and overlaps are merged again; the result sorted by `(y0, x0)`.
3. `image_mode`: `"crops"` becomes `"scaled"` when `c.pixels` is null, when `c.pixels.changed_fraction >
   ic.crop_max_fraction`, or when `rects` is empty; every other case is `ic.images`.
4. `context_text`: `Chapter: {title} — {gist}` when a chapter is given; then, when `previous` is non-empty,
   `Preceding transitions:` and one `render_change_line` per change; when neither exists, `No preceding context.`
5. Blocks, in order: (a) `text_block(context_text)`; (b) the images; (c) `text_block("Changes:\n" + change text)`;
   (d) `text_block("Return the JSON object.")`. There is no transient frame: nothing is folded (spec §0).
6. The images, with `a`, `b` the two `Frame`s:
   - `full`: `Frame a = frame {a.frame} (t={a.t_settled:.2f}s):` + the PNG as is; the same for `Frame b`.
   - `scaled`: the same captions ending `, downscaled by {scale:g}:` and both images through `scale_image`, sent as
     in-memory PNGs (never written to disk).
   - `crops` (Decision D4): everything `scaled` sends, then `Areas where text changed, at full resolution, as
     x0,y0,x1,y1 of the {width}x{height} frame; each is shown from frame {a.frame} (before), then from frame {b.frame}
     (after):`, then per rectangle *k* (from 1) of `crop_boxes(change_rects(c, boxes), b.width, b.height, pad,
     ic.crop_max)`: `Area {k} ({x0},{y0},{x1},{y1}) before:` + the crop of `a`, `Area {k} after:` + the crop of `b`.
     `pad = margin_px(boxes of a, boxes of b, ic.crop_pad)`: the pad is relative to box height, not a pixel constant.
7. The hash input is `context_text + "\n" + change text`; Task 7 hashes it with the two frames' `sha256`.

**Tests to write first** (Fixture M; `_images(blocks)` decodes the image blocks with Pillow, `_texts(blocks)` joins the
text blocks with newlines):
- `test_scaled_mode_is_the_default`: `build_blocks(T1, [], …, InterpretConfig())` → image sizes `[(200, 100), (200,
  100)]`; the texts contain `Frame a = frame 10 (t=20.40s), downscaled by 0.5:` and `Frame b = frame 11 (t=24.40s),
  downscaled by 0.5:`, start with `No preceding context.`, contain `Changes:\nTransition T1:` and end with `Return the
  JSON object.`; ids `["11:b3", "10:b3"]`; mode `"scaled"`.
- `test_full_mode_sends_native_size`: `images="full"` → sizes `[(400, 200), (400, 200)]`, no `downscaled` in the texts.
- `test_crops_mode_adds_full_resolution_text_areas`: `images="crops"` on T1 (median box height 18, so `pad = 36`) →
  sizes `[(200, 100), (200, 100), (226, 90), (226, 90)]` and the text `Area 1 (0,64,226,154) before:`; on T2 the two
  appeared boxes pad to `(0,84,186,174)` and `(0,104,116,194)`, which overlap and merge → sizes `[(200, 100), (200,
  100), (186, 110), (186, 110)]` and `Area 1 (0,84,186,194) before:`.
- `test_crops_falls_back_to_scaled`: `image_mode` is `"scaled"` for T1 with `pixels=None`, with
  `changed_fraction=0.3`, and with `rects=[]`; it is `"crops"` at `changed_fraction=0.25` exactly; `images="full"` is
  never changed.
- `test_context_lists_preceding_transitions`: `build_blocks(T3, [T1, T2], …)` → the first text block is
  `Preceding transitions:\nT1 [f10→f11, 24.0–24.4s] appended "C:\src> git status"\nT2 [f11→f12, 26.0–26.4s] appeared
  2`; with `chapter=OutlineChapter(id="c1", start_s=0, end_s=60, title="Setup", gist="Check the repo")` it starts with
  `Chapter: Setup — Check the repo`.
- `test_crop_boxes_pad_clamp_merge_and_cap` (the tag's test, kept): `crop_boxes([(100,50,120,70), (300,150,320,170)],
  400, 200, 40, 4) == [(60,10,160,110), (260,110,360,200)]`; `crop_boxes([(10,10,20,20), (30,30,40,40),
  (500,500,510,510)], 600, 600, 40, 4) == [(0,0,80,80), (460,460,550,550)]`; six scattered components with cap 4 → 4
  rectangles, sorted, every component inside one; `crop_boxes([], 400, 200, 40, 4) == []`.
- `test_prompt_version_names_the_mode`: defaults → `"interpret-v1+scaled0.5"`; `images="full"` →
  `"interpret-v1+full"`; `images="crops"` → `"interpret-v1+crops0.5p2m4f0.25"`.
- `test_labels_reach_the_change_text`: with `labels=True`, `_texts(build_blocks(T3, …))` contains `value of "Status"`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_interpret.py -q`. Expected: FAIL (`ImportError:
  build_blocks`).
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(interpret): image modes scaled, crops and full; content blocks with context and change text (L39)`

### Task 7: The `interpret` stage

**Files:**
- Modify: `src/scry/interpret.py`, `src/scry/cli.py`, `tests/test_interpret.py`
- Create: `tests/test_cli.py` (or extend it if plan 1 or 2 created it)

**Interfaces:**
- Consumes: Tasks 1–6; `get_provider`, `VlmProvider`, `VlmResult`; `Run.annotations`, `Run.load_labels` (A4);
  `scry.providers.batch.run_with_batches(run, cfg, provider, stage_fn) -> list` (A6).
- Produces:
  - `run_interpret(run: Run, cfg: Config, provider: VlmProvider | None = None) -> None`, writing
    `interpretations.jsonl`
  - CLI `scry interpret RUN_DIR [--config PATH] [--verbose]`

**Rules:**
1. The whole stage runs under `run_with_batches`, so `[model] mode = "batch"` works as it does for `annotate`: a
   collecting pass, the batches, then a pass that is all cache hits and whose records are the ones written.
2. One record per change, in `changes.jsonl` order (spec §6: one call per non-trivial transition; nothing is folded, so
   a change that `reverts` the previous one is interpreted like any other):
   a. `kind == "trivial"` → `Interpretation(id, error="trivial")`, no call;
   b. a frame PNG that does not exist → `Interpretation(id, error="missing_png")`, no call (Decision D22);
   c. otherwise `previous` = the `cfg.interpret.context_transitions` records before it (any kind), `chapter =
      run.chapter_of(t_settled of the to-frame)`, and one `provider.complete(stage="interpret", system=SYSTEM,
      blocks=…, output_model=ModelInterpretation, effort=cfg.model.effort_interpret, prompt_version=prompt_version(…),
      input_hashes=[a.sha256, b.sha256, sha256_obj(hash input)])`, at most `cfg.model.concurrency × 2` in flight.
3. A result without `parsed` → `Interpretation(id, error=res.error, images=mode, usage=res.usage, model,
   prompt_version)`. Otherwise the model's fields are copied; `citations, invalid_citations =
   validate_citations(parsed.citations, citable ids)`; an `entered_text` that is empty after `strip()` is stored as
   `None`; `images` is the mode actually sent; `usage = res.usage` (the usage of the call that produced the record,
   whether or not it came from the cache: Decision D18).
4. Inputs `[run.changes, run.frames, run.boxes, run.annotations]` (an absent file hashes as `missing`, so adding
   annotations later re-runs the stage); config hash `config_hash(cfg, "model", "interpret") + prompt_version(…)`;
   manifest key `interpret` with stats `transitions`, `interpreted` (records with `error` null), `trivial`, `errors`
   (any other error), `invalid_citations`, `entered` (records with `entered_text`), `submitted` (`{"yes": n, "no": n,
   "unclear": n}`), `images` (configured), `image_fallbacks` (calls sent in another mode), `labels` (bool),
   `usage` (the four keys summed over the records with `add_usage`), `cost_usd`, `cost_usd_batch` (`stage_cost`),
   `model`, `cache` (`provider.stats`).

**Tests to write first:**
- `test_run_interpret_writes_records_and_stats`: Fixture M without labels; `m = ModelInterpretation(action="a",
  result="r", description="d", confidence=0.7, entered_text="git st", submitted="no", citations=["11:b3", "11:b9",
  "11:b3"])`; `ScriptedProvider({"interpret": [m] * 6})`. After `run_interpret`: three records; `T1.citations ==
  ["11:b3"]`, `T1.invalid_citations == 1`; `T2.citations == []`, `T2.invalid_citations == 3`; `T3.invalid_citations ==
  3`; every record has `entered_text "git st"`, `submitted "no"`, `images "scaled"`, `usage == USAGE`,
  `prompt_version "interpret-v1+scaled0.5"`. Manifest `stages.interpret`: `transitions 3`, `interpreted 3`, `trivial
  0`, `errors 0`, `invalid_citations 7`, `entered 3`, `submitted {"yes": 0, "no": 3, "unclear": 0}`, `images "scaled"`,
  `image_fallbacks 0`, `labels False`, `usage {"input_tokens": 300, "output_tokens": 60, "cache_read_input_tokens":
  3000, "cache_creation_input_tokens": 1200}`, `cost_usd 0.012`, `cost_usd_batch 0.006`, `model "fake-model"`. Every
  call had `stage "interpret"`, `effort "low"` and `system == SYSTEM`. The call for T3 has a first text block listing
  T1 and T2; the call for T1 starts `No preceding context.` A second `run_interpret` makes no call;
  `Config(interpret=InterpretConfig(images="full"))` makes three more, with `prompt_version "interpret-v1+full"`.
- `test_trivial_and_missing_png_make_no_call`: rewrite `changes.jsonl` with `T2.kind = "trivial"` and delete
  `frames/00013.png` → one provider call; `T2.error == "trivial"`, `T3.error == "missing_png"`; stats `interpreted 1`,
  `trivial 1`, `errors 1`.
- `test_refusal_is_recorded`: script `{"interpret": ["refusal", m, m]}` → the refused record has `error "refusal"`,
  `action None`, `usage == USAGE`; stats `errors 1`, `interpreted 2`; no exception.
- `test_blank_entered_text_is_null`: the model returns `entered_text="  "` → the record has `entered_text None`.
- `test_labels_flag_and_rerun`: run once without labels (`labels False`), then write Fixture M's annotations into the
  same directory → `run_interpret` runs again (the inputs hash changed) and the stat `labels` is `True`.
- `tests/test_cli.py::test_cli_interpret`: monkeypatch `scry.interpret.get_provider` to return a `ScriptedProvider`;
  `scry interpret <dir>` exits 0 and `interpretations.jsonl` has three lines.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_interpret.py tests/test_cli.py -q`.
  Expected: FAIL (`ImportError: run_interpret`).
- [ ] **Step 2:** Implement rules 1–4 and the command.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry --help` lists `interpret`.
- [ ] **Step 4:** Commit: `feat: interpret stage: one call per transition, entered_text and submitted, citations validated against handed ids`

### Task 8: `summarize`: what stays, what is rendered differently, and the prompts

**What stays from the tag's `hierarchy.py` (design §13), unchanged in behaviour:** the two-pass pattern per level
(a boundary call over one-line items, then one elaboration call per segment); ends derived in code; one re-prompt with
a changed request when no valid start survives; the fallbacks (outline chapters for sections, else fixed windows) with
`segmentation_conf "low"`; windowing (2,000 items, overlap 200) and the overlap vote; map-reduce inside a segment of
more than 80 children (parts of 60); frame and time ranges propagated by code, never by the model; text-only calls;
`HierNode`; ids `S<n>`, `C<n>`, `V`. **What changes:** the inputs. Items are rendered from `changes.jsonl` and
`interpretations.jsonl` (spec §6: "Renders each transition from its interpretation (action, `entered_text`,
`submitted`) and group texts, and a frame's state from its containers when annotations exist"); the state line loses
`focused`; the prompts lose the `typed` and `lines appended` events and gain the `submitted` rule; invalid elaboration
refs are counted; usage is summed.

**Files:**
- Create: `src/scry/summarize.py` (pure part), `src/scry/prompts/summarize.py`, `tests/test_summarize.py`

**Interfaces:**
- Consumes: `render_change_line` (Task 4); `Change`, `Interpretation`, `HierNode`, `SegmentStart`; `Labels` (A4).
- Produces, in `scry.summarize`:
  - `repair_boundaries(segments: list[SegmentStart], ids: list[str]) -> list[tuple[int, str]]`
  - `fallback_segments(n: int, size: int) -> list[tuple[int, str]]`
  - `window_ranges(n: int, window: int, overlap: int) -> list[tuple[int, int]]`
  - `merge_window_boundaries(per_window: list[tuple[int, int, list[tuple[int, str]]]], n: int, overlap: int) ->
    list[tuple[int, str]]`
  - `propagate(children: Sequence[HierNode | Change]) -> tuple[tuple[int, int], tuple[float, float]]`
  - `item_line(item: HierNode | Change, interps: dict[str, Interpretation]) -> str`
  - `item_full(item: HierNode | Change, interps: dict[str, Interpretation]) -> str`
  - `state_line(frame: Frame, labels: Labels | None) -> str`
  - constants `SEGMENT_MAX_ITEMS = 80`, `SEGMENT_PART_ITEMS = 60`, `OVERLAP_EDGE = 25` (the tag's literals, named)
- Produces, in `scry.prompts.summarize`: `VERSION = "summarize-v1"`, `BOUNDARY_SYSTEM`, `ELABORATE_SYSTEM` (below).

**Rules:**
1. `repair_boundaries`: map each `start_id` to its position in `ids`; drop unknown ids; keep the first label for a
   repeated position; add `(0, "segment 1")` when position 0 is absent; return sorted by position.
2. `fallback_segments(n, size)`: `[(k, f"segment {k // size + 1}") for k in range(0, n, size)]`.
3. `window_ranges`: `[(0, n)]` when `n ≤ window`; else windows of `window` items, each starting `overlap` before the
   previous one's end, the last ending at `n`.
4. `merge_window_boundaries`: a boundary outside every overlap zone is kept; inside an overlap zone each window that
   found it gives 2 votes when the boundary lies at least `OVERLAP_EDGE` items from both edges of that window, else 1,
   and it is kept with 2 or more votes; the first label seen wins; `(0, "segment 1")` is added when 0 is missing;
   sorted, without duplicates.
5. `propagate`: frames `(first.from_frame or first.frames[0], last.to_frame or last.frames[1])`, time `(first.t[0],
   last.t[1])`.
6. `item_line` for a `Change`: `render_change_line(c)`; when an interpretation with an `action` exists, ` — {action}`;
   then ` [entered "{entered_text}", submitted: {submitted}]` when `entered_text` is not null, or ` [submitted: yes]`
   when it is null and `submitted == "yes"`. For a `HierNode`: `{id} [f{frames[0]}→f{frames[1]},
   {t[0]:.1f}–{t[1]:.1f}s] {label}`.
7. `item_full` for a `Change`: the `render_change_line`; then, when an interpretation with an `action` exists,
   `  action: {action}` and `  result: {result}`, and `  entered: "{entered_text}"; submitted: {submitted}` when
   `entered_text` is not null or `submitted == "yes"` (`entered: null` in the second case); then one line per group
   `  text: {B} → {A}` with the sides quoted and joined as in Task 4 rule 3. For a `HierNode`: `{id} {label}` and
   `  {description}`.
8. `state_line`: `frame {n} (t={t_settled:.1f}s): windows [{app}: {name}, …]` over `labels.frame(n).containers` in
   record order; `frame {n} (t={t_settled:.1f}s)` when `labels` is null or the list is empty. Focus is not reported.
9. No rule reads a duration as evidence; "submitted" comes only from the interpretation.

**`BOUNDARY_SYSTEM`:**

```
You segment an ordered list of items from a screen-recording tutorial into coherent units.

Each line is one item: its id, its frame range and time range, and a one-line summary. For a transition the summary
has two parts. Before the dash is what was measured: texts that changed (their kind and their text after the change,
in quotes) and counts of texts that appeared, were removed or moved. After the dash is a model's interpretation of
what the user did, followed in square brackets, when it applies, by what the user had entered and whether it was
submitted. Output only the ids at which a new segment begins, with a short label for the segment that starts there. A
segment is a coherent unit of work a tutorial reader would follow as one step (for steps) or one topic (for sections).
The first item always begins the first segment. Use ids exactly as listed; do not invent ids.

Worked example. Given items
T1 [f0→f2, 0.0–3.1s] appeared 14; removed 9 — The user opened the "Create a resource group" page in the portal.
T2 [f2→f5, 3.1–9.8s] appended "rg-demo" — The user typed the resource group name. [entered "rg-demo", submitted: no]
T3 [f5→f9, 9.8–20.2s] appeared 12; removed 30 — The user clicked "Review + create". [submitted: yes]
T4 [f9→f12, 20.2–31.0s] appended "C:\src> git status" — The user typed a command in the terminal. [entered "git status", submitted: no]
T5 [f12→f14, 31.0–40.5s] appeared 3 — The user pressed Enter and Git printed the branch state. [entered "git status", submitted: yes]
a good answer is {"segments": [{"start_id": "T1", "label": "Create the resource group in the portal"},
{"start_id": "T4", "label": "Check the repository from the terminal"}]}: the first item starts the first segment, and
a new segment begins where the sub-goal changes (portal work, then terminal work), not at every item.
```

**`ELABORATE_SYSTEM`:**

```
You describe one segment of a screen-recording tutorial for a reader who will follow it.

You are given the segment's items in full and the screen state at its start and end (the windows, when they are
known). For a transition an item holds what was measured (the text before and after each change) and a model's
interpretation: action, result, entered (what the user had entered, as far as the frames showed) and submitted (yes,
no or unclear: whether what was entered took effect). Return a short label and a description. Every sentence of the
description carries, in square brackets, the ids of the items it rests on, e.g. [T13]. Quote commands, paths and
identifiers exactly as the items give them; do not paraphrase or correct them. Say that a command was run, or a form
was sent, where an item says submitted: yes. Where it says no or unclear, say what was entered or shown instead: text
on an input line may have been a suggestion, or may have been cleared. List every cited id in refs.

Worked example. For a segment whose items are
T4 [f9→f12, 20.2–31.0s] appended "C:\src> git status"
  action: The user typed a command in the terminal.
  result: The command line reads git status.
  entered: "git status"; submitted: no
  text: "C:\src>" → "C:\src> git status"
T5 [f12→f14, 31.0–40.5s] appeared 3
  action: The user pressed Enter.
  result: Git printed "On branch main" and "nothing to commit, working tree clean".
  entered: "git status"; submitted: yes
a good answer is {"label": "Check the repository state", "description": "Type `git status` in the terminal [T4] and
run it [T5]. Git reports \"On branch main\" and \"nothing to commit, working tree clean\" [T5].", "refs": ["T4",
"T5"]}. A poor answer paraphrases the command, says it was run on the strength of T4 alone, or leaves a sentence
without a bracketed id.
```

**Tests to write first (`tests/test_summarize.py`):**
- The tag's four tests, re-pointed at `scry.summarize` and `Change`:
  `test_repair_boundaries_sorts_dedups_drops_unknown_and_forces_first` (ids `T1…T10`; starts `T5 "b"`, `T9 "c"`, `T5
  "dup"`, `T99 "x"` → `[(0, "segment 1"), (4, "b"), (8, "c")]`; no starts → `[(0, "segment 1")]`);
  `test_fallback_and_windows` (`fallback_segments(45, 20) == [(0, "segment 1"), (20, "segment 2"), (40, "segment 3")]`;
  `window_ranges(10, 2000, 200) == [(0, 10)]`; `window_ranges(5000, 2000, 200) == [(0, 2000), (1800, 3800), (3600,
  5000)]`); `test_merge_window_boundaries_keeps_non_overlap_and_agreed_overlap` (windows `(0, 2000, [(0, "a"), (1000,
  "b"), (1900, "c")])` and `(1800, 3800, [(1800, "c?"), (1900, "c"), (2500, "d")])`, overlap 200 → positions `[0, 1000,
  1900, 2500]`); `test_propagate_from_changes_and_nodes` (changes `T1` 3→5 `t (1.0, 2.0)` and `T2` 5→9 `t (2.5, 4.0)` →
  `((3, 9), (1.0, 4.0))`; one step node over them → the same).
- `test_item_line` (Fixture M and its interpretations): T1 → `T1 [f10→f11, 24.0–24.4s] appended "C:\src> git status" —
  The user typed " st" in the terminal; the shell offers "atus" as a completion. [entered "git st", submitted: no]`;
  T2 → `T2 [f11→f12, 26.0–26.4s] appeared 2 — The user pressed Enter. [entered "git status", submitted: yes]`; T3 →
  `T3 [f12→f13, 30.0–30.4s] changed "Succeeded" — No user action is evident; the portal refreshed.`; T1 with no
  interpretation → `T1 [f10→f11, 24.0–24.4s] appended "C:\src> git status"`; an interpretation with `entered_text
  None`, `submitted "yes"` → the line ends ` [submitted: yes]`; a `HierNode(id="S1", frames=(10, 12), t=(24.0, 26.4),
  label="Run git status", …)` → `S1 [f10→f12, 24.0–26.4s] Run git status`.
- `test_item_full`: T1 →
  ```
  T1 [f10→f11, 24.0–24.4s] appended "C:\src> git status"
    action: The user typed " st" in the terminal; the shell offers "atus" as a completion.
    result: The command line now reads git st with a greyed suggestion.
    entered: "git st"; submitted: no
    text: "C:\src> git" → "C:\src> git status"
  ```
  T3 → the line, `  action: …`, `  result: …`, `  text: "Creating" → "Succeeded"` and no `entered` line; T1 with an
  interpretation whose `error` is `"refusal"` → the first and the `text:` lines only.
- `test_state_line`: with labels → `frame 10 (t=20.4s): windows [Azure Portal: Resource overview, Windows Terminal:
  PowerShell]`; without → `frame 10 (t=20.4s)`; neither contains `focus`.
- `test_prompts` (substring checks after collapsing whitespace runs to one space): both prompts contain `submitted`; neither contains `typed "`, `lines appended`, `focus`, `kubectl` or
  `az `; `VERSION == "summarize-v1"`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_summarize.py -q`. Expected: FAIL (`No module named
  scry.summarize`).
- [ ] **Step 2:** Implement rules 1–9 and the prompt module.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(summarize): items rendered from changes and interpretations; prompts summarize-v1`

### Task 9: The `summarize` stage

**Files:**
- Modify: `src/scry/summarize.py`, `src/scry/cli.py`, `tests/test_summarize.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: Task 8; `add_usage`, `stage_cost` (Task 3); `SummarizeConfig`; `ModelBoundaries`, `ModelElaboration`.
- Produces: `build_level(provider, cfg: Config, level: str, prefix: str, items: list, frames: dict[int, Frame], interps:
  dict[str, Interpretation], labels: Labels | None, suggestion: str | None, fallback_size: int, chapter_starts:
  list[tuple[int, str]] | None, meter: dict) -> list[HierNode]`; `run_summarize(run: Run, cfg: Config, provider=None) ->
  None` writing `steps.jsonl`, `sections.jsonl`, `video.json`; CLI `scry summarize RUN_DIR [--config PATH] [--verbose]`.

**Rules** (design §13, unchanged unless said):
1. Steps are built over the changes whose `kind != "trivial"`, in order; sections over the steps; the video over the
   sections. With no non-trivial change the stage logs a warning and writes nothing, as today.
2. Boundary call per window: the items' `item_line`s joined by newlines; for sections, when `outline.json` exists,
   followed by `\n\nSuggested boundaries from a coarse outline (reconcile against the items; the items win):\n` and one
   `{start_s:.0f}s–{end_s:.0f}s: {title}` per chapter. `stage=f"summarize-boundary-{level}"`,
   `system=BOUNDARY_SYSTEM`, `output_model=ModelBoundaries`, `effort=cfg.model.effort_summarize`,
   `prompt_version=VERSION`, `input_hashes=[sha256_obj(text), "first"]`. When no segment comes back, one retry whose
   text ends `\n\n(Retry: the previous answer contained no valid start ids. Use the ids exactly as listed above.)` and
   whose second hash is `"retry"` (a changed request, or the call cache would return the failed answer).
3. After a failed retry: for sections with an outline, the chapter starts mapped to the first step starting at or after
   each chapter's `start_s`; otherwise `fallback_segments`; position 0 forced; every node of the level gets
   `segmentation_conf "low"`.
4. Elaboration call per segment: `Segment {id}\nStart state: {state_line(first frame)}\nEnd state: {state_line(last
   frame)}\n\nItems:\n{item_full of each child}`; a segment of more than `SEGMENT_MAX_ITEMS` children is first
   summarised in parts of `SEGMENT_PART_ITEMS` (ids `{id} part {p}`) and the parent call receives `part {p}:
   {description}` lines. `stage=f"summarize-elaborate-{level}"`, `output_model=ModelElaboration`,
   `input_hashes=[sha256_obj(text)]`. A failed call yields label = the segment id and description `(elaboration
   failed: {error})`.
5. A node's `label` is the elaboration's label when non-empty, else the boundary label; `refs` keeps the returned refs
   that are ids of the node's children, in order; the others are dropped **and counted** in `meter["invalid_refs"]`.
   `children = (first child id, last child id)`; `frames`, `t` from `propagate`.
6. The video node `V` is one elaboration over the sections with `level "video"`.
7. Every `complete` result's `usage` is added into `meter["usage"]` with `add_usage` and `meter["calls"]` counts the
   calls (cached or not: Decision D18).
8. Inputs `[run.changes, run.interpretations, run.frames, run.annotations, run.outline]`; config hash
   `config_hash(cfg, "model", "summarize") + VERSION`; manifest key `summarize` with stats `steps`, `sections`,
   `low_conf`, `invalid_refs`, `calls`, `usage`, `cost_usd`, `cost_usd_batch`, `model`, `cache`. Calls depend on one
   another level by level, so this stage never uses the batch path.

**Tests to write first:**
- `test_run_summarize_builds_three_levels`: Fixture M with its interpretations, no labels;
  `ScriptedProvider({"summarize-boundary-step": [ModelBoundaries(segments=[SegmentStart(start_id="T1", label="Run git
  status"), SegmentStart(start_id="T3", label="Watch the deployment")])], "summarize-elaborate-step":
  [ModelElaboration(label="Run git status", description="Type `git status` [T1] and run it [T2].", refs=["T1", "T2",
  "T9"]), ModelElaboration(label="", description="The status becomes Succeeded [T3].", refs=["T3"])],
  "summarize-boundary-section": [ModelBoundaries(segments=[SegmentStart(start_id="S1", label="Everything")])],
  "summarize-elaborate-section": [ModelElaboration(label="Everything", description="All of it [S1] [S2].", refs=["S1",
  "S2"])], "summarize-elaborate-video": [ModelElaboration(label="A short demo", description="One section [C1].",
  refs=["C1"])]})`. Expected: steps `S1` children `("T1", "T2")`, frames `(10, 12)`, `t (24.0, 26.4)`, refs `["T1",
  "T2"]`, label `"Run git status"`; `S2` children `("T3", "T3")`, frames `(12, 13)`, `t (30.0, 30.4)`, label `"Watch the
  deployment"` (the empty elaboration label falls back to the boundary label); section `C1` children `("S1", "S2")`,
  frames `(10, 13)`, `t (24.0, 30.4)`; `video.json` id `V`, children `("C1", "C1")`. The step boundary call's text is
  exactly the three `item_line`s of Task 8 joined by newlines. The first step elaboration's text starts `Segment
  S1\nStart state: frame 10 (t=20.4s)\nEnd state: frame 12 (t=26.4s)\n\nItems:\nT1 [f10→f11`. Manifest: `steps 2`,
  `sections 1`, `low_conf 0`, `invalid_refs 1`, `calls 6`, `usage.input_tokens 600`, `usage.cache_creation_input_tokens
  2400`, `cost_usd 0.024`, `cost_usd_batch 0.012`. A second `run_summarize` makes no call.
- `test_boundary_retry_then_fallback`: both step boundary answers are `ModelBoundaries(segments=[])` → two boundary
  calls, the second text ending with the retry sentence; with `fallback_step_transitions = 2` the steps are `S1`
  (`T1`–`T2`) and `S2` (`T3`), both `segmentation_conf "low"`; stat `low_conf` counts them.
- `test_summarize_with_a_failed_interpretation` (Review Focus 5): rewrite `interpretations.jsonl` so `T2` has `error
  "refusal"` and no action → the boundary text's second line is `T2 [f11→f12, 26.0–26.4s] appeared 2`; the stage
  completes.
- `test_trivial_transitions_are_not_items`: `T2.kind = "trivial"` → the step boundary text has two lines (T1, T3).
- `test_state_lines_use_containers_when_labelled`: with `labels=True` the first elaboration text contains `windows
  [Azure Portal: Resource overview, Windows Terminal: PowerShell]`.
- `test_no_transitions_writes_nothing`: every change trivial → no provider call, no `steps.jsonl`, no manifest entry.
- `tests/test_cli.py::test_cli_summarize`: with `scry.summarize.get_provider` monkeypatched, `scry summarize <dir>`
  exits 0 and the three files exist.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_summarize.py tests/test_cli.py -q`. Expected: FAIL
  (`ImportError: run_summarize`).
- [ ] **Step 2:** Implement rules 1–8 and the command.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry --help` lists `summarize`.
- [ ] **Step 4:** Commit: `feat: summarize stage over changes and interpretations; invalid refs and usage counted`

### Task 10: Index schema, and the whole-screen entry per emitted frame (kept)

**Files:**
- Modify: `src/scry/index.py`, `tests/test_index.py`
- Create: `src/scry/nodes.py`, `tests/test_nodes.py`, `tests/test_findability.py`

**Interfaces:**
- Consumes: `Node`, `open_db`, `index_nodes`, `search`, `fts_query`, `trigram_query` (A3); `Frame`, `FrameBoxes`,
  `Lifetime`, `box_ref`; `Labels` (A4); `text_of` (Task 4).
- Produces:
  - `scry.index.Node`: `node_id, video_id, level, item_id, frames, t, apps: list[str] = [], containers: list[str] = [],
    step_id, section_id, chapter_id, text, payload`. `layout_conf` is removed (spec §3) and `region_names` becomes
    `containers`; the `nodes` table has the matching 15 columns; `search`'s hit dicts drop `layout_conf` and gain
    `containers`. Levels: `"frame"`, `"lifetime"`, `"transition"`, `"step"`, `"section"`, `"video"`, `"chapter"`.
  - `scry.nodes.link_anchor(link) -> str` and `scry.nodes.link_lines(link, text: Callable[[str], str]) -> list[str]`,
    where `link` is any of plan 2's link shapes (`Link`, `BoxLink`, `LifetimeLink`: they share `kind`, `boxes`,
    `joiner`, `key`, `value`, `members`, `header`) and `text` maps one of its ids to a string
  - `scry.nodes.frame_nodes(run: Run, frames: list[Frame], boxes: dict[int, FrameBoxes], lifetimes: list[Lifetime],
    labels: Labels | None) -> list[Node]`

**Rules** (spec §6: "Whole-screen entries stay, one per emitted frame: every box's text in reading order plus the screen
`description` in force at that frame"):
1. `open_db` keeps its two virtual tables exactly: `nodes_fts` with `tokenize="unicode61 tokenchars '-_./:\'"` and
   `nodes_tri` with `tokenize='trigram'`; `fts_query`, `trigram_query`, `_terms` and `rrf` are not touched (F2).
   `index.sqlite` is rebuilt from scratch by `build_index`, so the column change needs no migration.
2. One node per emitted frame: `node_id f"{vid}:f{frame}"`, `level "frame"`, `item_id str(frame)`, `frames (frame,
   frame)`, `t (t_settled, t_end)`, `chapter_id` of `run.chapter_of(t_settled)`.
3. **Every box's OCR text, in reading order, one per line. No label removes a line**: a box the model called
   `non_text`, a box in no container and a box of a frame whose annotation failed are all included (F1, F6).
4. After the box lines, for each box in reading order whose label has `agree is False` and a non-empty `vlm`: the
   model's reading on its own line (today's index does the same for disagreeing lines; spec §7 "record both").
5. Then the text of each missed text in force (`m<n>`, no rectangle), in record order.
6. Then the link lines: for each link of `labels.frame(frame).links` (the links in force, in plan 2's order),
   `link_lines(link, text)` with `text` = the OCR text of a ref in this frame. `link_anchor`: a `run`'s first box; a `pair`'s first `value` box; a
   `record`'s first box of its first member (Decision D12). `link_lines`: `run` → the texts joined with `""` and joined
   with `" "`, as two lines, one when they are equal ("so a wrong joiner cannot hide a command"); `pair` → one line,
   the key texts joined with `" "`, a space, the value texts joined with `" "` (`key value` tokens); `record` → one
   line, each member's texts joined with `" "`, the members joined with `" "`. `header` adds no line. A link naming a
   ref that is not in the frame raises `ValueError`.
7. Before all of these, one line per container in force, `"{app} {name}"` stripped, skipped when empty; after all of
   them, the description in force, when there is one. (Decision D10: today's region entries begin with the app and
   window name, so a query for an application name the screen never spells out finds them; that must not be lost.)
8. `apps` = the sorted distinct non-empty container apps; `containers` = the container names in record order. The
   payload is `{"frame", "ordinal" (0-based position in `frames.jsonl`), "png", "boxes": [{"id", "text", "lifetime"}],
   "description", "containers": [{"id", "kind", "app", "name"}], "missed": [{"id", "text"}]}`; `lifetime` is the id of
   the lifetime whose `boxes` holds the ref (A2). A frame whose text comes out empty yields no node.
9. Without labels, rules 4–7 contribute nothing and the node is rule 3's lines.

**Tests to write first:**
- `tests/test_findability.py::test_frame_document_is_a_superset` (F1; Fixture M with labels): the text of `v:f13` is
  exactly
  ```
  Azure Portal Resource overview
  Windows Terminal PowerShell
  Status
  Succeeded
  C:\src> git status
  On branch maln
  C:\src>
  On branch main
  Refresh
  Status Succeeded
  The Status value now reads Succeeded.
  ```
  and the text of `v:f11` is exactly
  ```
  Azure Portal Resource overview
  Windows Terminal PowerShell
  Status
  Creating
  C:\src> git status
  C:\src> git st
  Status Creating
  The Overview item is highlighted in the left navigation.
  ```
  For every frame and every box, the box's text is a line of that frame's node.
- `::test_tokenizers_and_query_builders_unchanged` (F2): after `open_db(tmp_path / "i.sqlite")`, the `sql` of
  `nodes_fts` in `sqlite_master` contains `tokenize="unicode61 tokenchars '-_./:\'"` and that of `nodes_tri` contains
  `tokenize='trigram'`; `fts_query('az aks create --resource-group "rg demo"') == '"az" OR "aks" OR "create" OR
  "--resource-group" OR "rg demo"'`; `trigram_query("az") is None`.
- `::test_non_text_never_removes_a_frame_line` (F6): one frame 0, boxes `b1 "区" (24,164,48,179)`, `b2 "Overview"
  (60,164,140,179)`, lifetimes `L1 "区"` and `L2 "Overview"`; one annotation record with no containers, `assign []`,
  `unassigned ["b1", "b2"]`, `texts [{"box": "b1", "text": ""}, {"box": "b2", "text": "Overview"}]`, `description ""` →
  the frame node's text is exactly `区\nOverview`.
- `tests/test_nodes.py::test_frame_nodes_without_labels`: Fixture M → four nodes; `v:f11` text `Status\nCreating\nC:\src>
  git status`; `t (24.4, 26.0)`; `apps []`; payload `ordinal 1`, `description None`, `boxes[2] == {"id": "b3", "text":
  "C:\\src> git status", "lifetime": "L4"}`.
- `::test_frame_node_metadata_with_labels`: `v:f12` → `apps ["Azure Portal", "Windows Terminal"]`, `containers
  ["Resource overview", "PowerShell"]`, payload `description "The terminal shows new output."`.
- `::test_link_lines`: a `run` over texts `"git commit --amend --no-ed"`, `"it"` → `["git commit --amend --no-edit",
  "git commit --amend --no-ed it"]`; a `pair` key `["Resource", "group"]` value `["rg-demo"]` → `["Resource group
  rg-demo"]`; a `record` with members `[["node-1"], ["Ready"], ["1.2", "GiB"]]` → `["node-1 Ready 1.2 GiB"]`; anchors
  are the first run box, the first value box and the first box of the first member.
- `::test_blank_frame_has_no_node`: a frame with no boxes and no labels → no node.
- `tests/test_index.py`: the helper `node()` drops `layout_conf` and `region_names`; the three kept tests pass
  unchanged otherwise; `test_index_and_search…` additionally asserts `"layout_conf" not in hits[0]`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_nodes.py tests/test_findability.py tests/test_index.py
  -q`. Expected: FAIL (`No module named scry.nodes`).
- [ ] **Step 2:** Implement rules 1–9.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(index): whole-screen entry per frame as a superset document; layout_conf gone (spec §6)`

### Task 11: Lifetime entries (added)

**Files:**
- Modify: `src/scry/nodes.py`, `tests/test_nodes.py`, `tests/test_findability.py`

**Interfaces:**
- Consumes: `Lifetime`; `Labels.lifetime`, `LifetimeLabel`, `LifetimeLink` (A4); `link_anchor`, `link_lines` (Task 10).
- Produces: `lifetime_nodes(run: Run, lifetimes: list[Lifetime], labels: Labels | None) -> tuple[list[Node], int]` (the
  nodes, and how many lifetimes were skipped as non-text).

**Rules** (spec §6: "one per lifetime (the majority reading of each reader, every variant, run texts joined both with
`""` and with `" "` …, pair text as `key value` tokens with `key` and `value` as fields, first and last time,
container label when there is one)"):
1. One node per lifetime: `node_id f"{vid}:{L.id}"`, `level "lifetime"`, `item_id L.id`, `frames (first.frame,
   last.frame)`, `t (first.t, last.t)` (A2: `last.t` is the last frame's `t_end`, so the node covers the whole time the
   text was on screen), `chapter_id` of `first.t`.
2. **Skipped only when the label says so everywhere:** when `labels.lifetime(L.id).non_text` is true, no node is made
   and the count rises (spec §5: a `non_text` box "leaves … index text"). Its OCR text stays in every frame document
   (Task 10 rule 3), so a wrong `non_text` label costs an enrichment and never findability (spec §4 principle 1).
3. Text lines, skipping any string already listed and any empty string: `L.text` (the OCR majority); the other keys of
   `L.readings` by count descending, then by string; the model's majority reading; the other keys of `vlm_readings` in
   the same order. "Record, do not pick" (principle 5): every reading of every reader is searchable.
4. A lifetime's entry carries the links of `labels.lifetime(L.id).links` **whose anchor it is** (`link_anchor(link)
   == L.id`), in plan 2's order. Plan 2 lists a link under every lifetime it names; the anchor rule puts its text in
   one entry only, so one pair is one hit. A pair therefore lives on its **value**'s entry: the pairing lasts as long as
   the value does (Decision D12). Plan 2 keeps every differing proposal with its count; so does the entry (principle 5).
5. Each carried link adds lines after rule 3's: `link_lines` with `text` = the OCR majority reading of a lifetime id;
   then the same with the model's majority readings when every lifetime of the link has a non-empty one, skipping
   lines already listed.
6. `apps` and `containers` come from `LifetimeLabel.container` (the latest labelled box's): `[app]` and `[name]` when
   non-empty, else `[]`. They are metadata for the `app` filter and the payload, not index text: a window name in every
   entry's text would make every entry of that window match the name (Decision D13).
7. Payload: `{"lifetime": L.model_dump(), "readers": {"ocr": {"text", "readings"}, "vlm": {"text", "readings"} or
   None}, "agree": LifetimeLabel.agree or None, "seen_once": L.sightings == 1, "container": {"app", "name", "kind"} or
   None, "links": [{"kind", "lines", "key", "value", "seen"}]}`; `seen` is the link's `records`; `key` and `value` are
   the joined OCR texts for a pair and `None` otherwise ("with `key` and `value` as fields").

**Tests to write first:**
- `tests/test_nodes.py::test_lifetime_nodes_with_labels` (Fixture M): seven nodes, none skipped. `v:L4`: text `C:\src>
  git status\nC:\src> git st`, `frames (11, 13)`, `t (24.4, 35.0)`, `apps ["Windows Terminal"]`, payload `agree True`,
  `seen_once False`, `readers.vlm.readings == {"C:\\src> git status": 2, "C:\\src> git st": 1}`. `v:L5`: text `On branch
  main\nOn branch maln`, payload `lifetime.unstable True`. `v:L2`: text `Creating\nStatus Creating`, `t (20.4, 30.0)`,
  payload `links == [{"kind": "pair", "lines": ["Status Creating"], "key": "Status", "value": "Creating", "seen": 3}]`.
  `v:L7`: text `Succeeded\nStatus Succeeded`, `seen_once True`, link `seen 1`. `v:L1`: text `Status`, `links []`.
- `::test_lifetime_nodes_without_labels`: `v:L2` text `Creating`; `v:L5` text `On branch main\nOn branch maln`; payload
  `readers.vlm None`, `agree None`, `container None`, `apps []`.
- `::test_non_text_lifetime_is_skipped_and_counted`: the one-frame fixture of `test_non_text_never_removes_a_frame_line`
  → nodes for `Overview` only, skipped count 1.
- `tests/test_findability.py::test_every_reading_and_both_joins_are_searchable` (F5): three frames 0, 1, 2, each with boxes
  `b1 (10,10,300,28)` and `b2 "it" (10,30,40,48)`; `b1` reads `git commit --amend --no-ed` in frames 0 and 2 and `git
  comit --amend --no-ed` in frame 1; lifetimes `L1` (boxes `0:b1, 1:b1, 2:b1`, readings `{"git commit --amend --no-ed":
  2, "git comit --amend --no-ed": 1}`) and `L2 "it"` (boxes `0:b2, 1:b2, 2:b2`); one annotation record per frame, each
  with the link `{"kind": "run", "boxes": ["b1", "b2"], "joiner": ""}` and no `texts`. `v:L1`'s text is `git commit --amend --no-ed\ngit comit --amend --no-ed\ngit
  commit --amend --no-edit\ngit commit --amend --no-ed it`. After indexing the lifetime nodes, `search(db, "--no-edit",
  IndexConfig())`, `search(db, '"--no-ed it"', …)` and `search(db, "comit", …)` each return `v:L1` first.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_nodes.py tests/test_findability.py -q`. Expected: FAIL
  (`ImportError: lifetime_nodes`).
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(index): lifetime entries with every reading, both joins of a run and pairs as key value`

### Task 12: Transition and summary entries, `build_index`, `scry index`

**Files:**
- Modify: `src/scry/nodes.py`, `src/scry/index.py`, `src/scry/cli.py`, `tests/test_nodes.py`, `tests/test_index.py`,
  `tests/test_findability.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `transition_nodes(run, changes: list[Change], interps: dict[str, Interpretation], boxes, labels, steps:
  list[HierNode], sections: list[HierNode]) -> list[Node]`; `summary_nodes(run, steps, sections, video: HierNode | None)
  -> list[Node]`; `extract_nodes(run: Run) -> tuple[list[Node], dict]` (nodes and stats); `scry.index.build_index(run:
  Run, cfg: Config) -> None`; CLI `scry index RUN_DIR [--config PATH] [--verbose]`.

**Rules:**
1. One node per change, trivial ones included (as today): `node_id f"{vid}:{c.id}"`, `level "transition"`, `item_id
   c.id`, `frames (from_frame, to_frame)`, `t c.t`, `apps` = the sorted distinct container apps in force at the
   to-frame, `step_id` and `section_id` from the `children` ranges of the steps and sections (as today), `chapter_id` of
   `c.t[1]`.
2. Text lines, skipping `None` and empty strings (spec §6: "action, result, `entered_text`, `submitted`, group texts"):
   `entered_text`; `action`; `result`; then per group every before text and every after text, one per line. When that
   leaves nothing (no interpretation and no group), the texts of the appeared boxes, then of the removed boxes. A node
   whose text is still empty is not made. `submitted` is not index text: `yes` and `no` match everything and mean
   nothing to a lexical search; it is in the payload and in `ask`'s hit summaries (Decision D13).
3. Payload `{"change": c.model_dump(), "interpretation": the record's `model_dump()` or None}`.
4. `summary_nodes`: steps, sections, the video and the outline chapters exactly as today: text `{label}\n{description}`
   (`{title}\n{gist}` for a chapter), levels `step`, `section`, `video`, `chapter`, payload = the record.
5. `extract_nodes`: frame nodes, lifetime nodes, transition nodes, summary nodes, in that order; stats `{"nodes": n,
   "by_level": {level: n}, "skipped_non_text": n, "labels": bool}`.
6. `build_index`: inputs `[run.frames, run.boxes, run.changes, run.lifetimes, run.annotations, run.interpretations,
   run.steps, run.sections, run.video, run.outline]`; config hash `config_hash(cfg, "index")`; an existing
   `index.sqlite` is deleted and rebuilt; manifest key `index` with the stats and `embedder`. It runs with any of the
   model stages' files absent.

**Tests to write first:**
- `tests/test_nodes.py::test_transition_nodes` (Fixture M with its interpretations, no labels): `v:T1` text
  ```
  git st
  The user typed " st" in the terminal; the shell offers "atus" as a completion.
  The command line now reads git st with a greyed suggestion.
  C:\src> git
  C:\src> git status
  ```
  `v:T2` text `git status\nThe user pressed Enter.\nGit printed "On branch main" and a new prompt appeared.`; `v:T3` text
  ends `\nCreating\nSucceeded`; `v:T2` payload `interpretation.submitted == "yes"`; `frames (11, 12)`, `t (26.0, 26.4)`.
- `::test_transition_node_without_interpretation` (Review Focus 5): no `interpretations.jsonl` → `v:T1` text `C:\src>
  git\nC:\src> git status`; `v:T2` text `On branch main\nC:\src>` (the appeared boxes); payload `interpretation None`.
- `::test_step_and_section_ids_on_transitions`: steps `S1 ("T1", "T2")`, `S2 ("T3", "T3")`, section `C1 ("S1", "S2")` →
  `v:T2.step_id == "S1"`, `v:T3.step_id == "S2"`, both `section_id "C1"`; step nodes carry `section_id "C1"`.
- `tests/test_index.py::test_build_index_stats_and_rerun`: Fixture M with labels and interpretations →
  `stages.index.by_level == {"frame": 4, "lifetime": 7, "transition": 3}`, `nodes 14`, `skipped_non_text 0`, `labels
  True`, `embedder "none"`; a second `build_index` does nothing; deleting `interpretations.jsonl` makes it run again.
- `tests/test_findability.py::test_index_without_annotations_holds_every_ocr_text` (F6, Review Focus 1): Fixture M
  without labels and without interpretations, `build_index`; for every box of every frame, `search(db, '"' + text +
  '"', IndexConfig(k=50))` returns a hit whose frames cover the box's frame.
- `tests/test_cli.py::test_cli_index`: `scry index <dir>` exits 0 and `index.sqlite` exists.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_nodes.py tests/test_index.py tests/test_findability.py
  tests/test_cli.py -q`. Expected: FAIL (`ImportError: transition_nodes`).
- [ ] **Step 2:** Implement rules 1–6 and the command.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry --help` lists `index`.
- [ ] **Step 4:** Commit: `feat: index stage: transition entries with entered_text; steps, sections, video as before; build_index over the new records`

### Task 13: Search: families fused, identical consecutive frame hits collapsed

**Files:**
- Modify: `src/scry/index.py`, `src/scry/cli.py`, `tests/test_index.py`, `tests/test_findability.py`, `tests/test_cli.py`

**Interfaces:**
- Produces:
  - `FAMILIES = (("lifetime", ("lifetime",)), ("transition", ("transition",)), ("frame", ("frame",)), ("summary",
    ("step", "section", "video", "chapter")))`
  - `matched_lines(text: str, terms: list[str]) -> tuple[str, ...]`
  - `collapse_runs(hits: list[tuple[str, int, tuple[str, ...]]]) -> list[list[str]]` — `(node_id, ordinal, matched)`
    in, runs of node ids out, each run in frame order
  - `search(db, query, cfg: IndexConfig, embedder=None, video_id=None, level=None, t_from=None, t_to=None, app=None,
    collapse: bool | None = None) -> list[dict]`
  - CLI `scry search RUN_DIR QUERY [--level L] [--t-from S] [--t-to S] [--app A] [--no-collapse] [--config PATH]`

**Rules** (spec §6: "hits from consecutive frames whose matching text is identical are collapsed into one hit with a
frame and time range … The duplicate problem is solved where it arises, in the result list, not by deleting entries"):
1. Terms, the FTS5 query and the trigram query are built as today. `k = cfg.k_filtered` when any filter is set, else
   `cfg.k`.
2. **One ranking per family and tokenizer.** For each family of `FAMILIES`, in that order (only the family holding
   `level`, restricted to that level, when `level` is given), and for FTS5 then trigram: the node ids matching the
   query with the metadata filters applied in SQL as today, restricted to the family's levels, `ORDER BY bm25(…),
   n.t_start, n.node_id` (the two added keys make equal scores deterministic), `LIMIT k` — except that the `frame`
   family has no `LIMIT` while collapsing is on, because a run can only be recognised when all its members are
   present (a two-hour video has some 2,000 frame entries; the query returns ids and texts only).
3. The vector ranking, when an embedder is configured, is one list over all levels, as today.
4. `matched_lines`: the lines of `text` (split on `"\n"`) that contain at least one term as a case-folded substring, in
   order; when no line does, the 1-tuple `(text,)`. Substring matching is looser than either tokenizer, so it can only
   find more matching lines, which makes two frames harder to call identical: it errs towards fewer collapses.
5. `collapse_runs`: sort by ordinal; a run is a maximal sequence in which each hit's ordinal is the previous one's plus
   one and its `matched` tuple equals the previous one's. Consecutive means consecutive emitted frames (`ordinal`, not
   frame number). Only `frame`-level hits are collapsed: a lifetime exists once and two transitions never have
   identical matching text by construction (Decision D14).
6. When collapsing (`collapse` if given, else `cfg.collapse`): the hits are the `frame`-level ids of every ranking; each
   run's representative is its **earliest** member; in every ranking each member is replaced by its representative and
   later repeats are removed, so the run takes its best member's rank; the two `frame` rankings are then cut to `k`.
7. Fuse all rankings with `rrf(rankings, cfg.rrf)`; order by score descending, then by the family position of the
   node's level, then `t_start`, then `node_id`; keep `k`. Because each family has its own rankings, the score of a
   frame hit does not depend on how many lifetime or transition entries match (F3).
8. A hit is today's dict without `layout_conf`, with `containers`, and for `frame`-level hits `collapsed` (member
   count, 1 when alone), `members` (frame numbers in order), `matched` (the lines), `frames = [first member's frame,
   last member's frame]` and `t = [first member's t_start, last member's t_end]`; `text` and `payload` are the
   representative's. Every pre-collapse frame hit is a member of exactly one hit (F4).
9. `scry search` prints one line per hit: `{score:.4f} {level:<10} {item_id:<8} f{frames[0]}-{frames[1]}
   t={t[0]:.1f}-{t[1]:.1f}` then ` x{collapsed}` when above 1, two spaces, and the first matched line (frame hits) or
   the first line of the text, cut to 100 characters.

**Tests to write first** (the index of Fixture M with labels and interpretations, built by `build_index`, unless given):
- `tests/test_index.py::test_search_collapses_identical_consecutive_frame_hits`: `search(db, "Creating",
  IndexConfig())` → node ids `["v:L2", "v:T3", "v:f10"]`, every score `0.03279` (rank 1 in its FTS5 and its trigram
  ranking: 2/61); the third hit has `frames [10, 12]`, `t [20.4, 30.0]`, `collapsed 3`, `members [10, 11, 12]`,
  `matched ["Creating", "Status Creating"]`. With `collapse=False` the node ids are the set `{"v:L2", "v:T3", "v:f10",
  "v:f11", "v:f12"}` and no hit has `collapsed > 1`.
- `::test_differing_matching_text_is_not_collapsed`: `search(db, "git", …)`: the `members` of the frame-level hits,
  sorted, are `[[10], [11], [12, 13]]` (frame 11 also matches the model's reading `C:\src> git st`); on the index of
  Fixture M **without** labels they are `[[10], [11, 12, 13]]`.
- `::test_ocr_variant_prevents_a_collapse`: `search(db, "branch", …)` → frame hits with members `[[12], [13]]` (frame
  13 reads `On branch maln`): the safe direction.
- `::test_collapse_runs_need_consecutive_ordinals`: `collapse_runs([("a", 0, ("x",)), ("b", 1, ("x",)), ("c", 3,
  ("x",)), ("d", 4, ("y",))]) == [["a", "b"], ["c"], ["d"]]`.
- `::test_matched_lines`: `matched_lines("Status\nCreating\nStatus Creating", ["creating"]) == ("Creating", "Status
  Creating")`; with terms `["zzz"]` → `("Status\nCreating\nStatus Creating",)`.
- `::test_level_and_time_filters`: `search(db, "Creating", cfg, level="frame")` → one hit, `v:f10`; `search(db,
  "Creating", cfg, t_from=25.0)` → the frame hit has `members [11, 12]` (frame 10 ends at 24.0) and `frames [11, 12]`;
  `search(db, "Status", cfg, app="Terminal")` returns no hit whose `apps` lacks `Windows Terminal`.
- `tests/test_findability.py::test_many_lifetime_hits_do_not_displace_the_frame_hit` (F3): hand-made nodes: thirty
  `lifetime` nodes `L01…L30` with text `alpha` and `t (i, i + 1)`, and one `frame` node `f0` with text `alpha\nbeta`,
  payload `{"ordinal": 0}` → `search(db, "alpha", IndexConfig())` returns 20 hits and `hits[1]["node_id"]` is the frame
  node's (tied with the first lifetime at 2/61; the family order breaks the tie).
- `::test_collapse_is_a_partition_of_the_frame_hits` (F4): for each query of `"Status"`, `"git"`, `"branch"`,
  `"Creating"`: the frame node ids of `search(…, collapse=False, level="frame")` equal, as a set and without
  repeats, the union of `members` of `search(…, level="frame")`; each collapsed hit's `frames` and `t` span its members.
- `tests/test_index.py::test_search_survives_fts_syntax` (Review Focus 3): none of `search(db, q, cfg)` raises for `q`
  in `--name`, `C:\src>`, `"git status`, `*`, `a`, `git AND NOT status`, `(`; `search(db, "C:\\src>", cfg)` returns at
  least one hit.
- `tests/test_cli.py::test_cli_search_prints_collapsed_hits`: `scry search <dir> Creating` exits 0 and its output has a
  line containing `frame` and `f10-12` and `x3`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_index.py tests/test_findability.py tests/test_cli.py
  -q`. Expected: FAIL (`ImportError: matched_lines`).
- [ ] **Step 2:** Implement rules 1–9.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(search): rank each family on its own and fuse; collapse identical consecutive frame hits in the result list`

### Task 14: `ask`: the tools over the new records

**Files:**
- Create: `src/scry/ask.py` (tools part), `tests/test_ask.py`

**Interfaces:**
- Consumes: `search`, `open_db`, `get_embedder` (Task 13); `render_change_line`, `box_label` (Task 4); `Run` loaders;
  `Labels` (A4); `scry.video.iter_frames` (A3); `AskConfig` (Task 2); `image_block`, `text_block`.
- Produces: `TOOL_DEFS: list[dict]`; `hit_summary(hit: dict) -> dict`; `class Tools(run: Run, cfg: Config)` with
  `search(query, level=None, t_from=None, t_to=None, app=None) -> dict`, `get_node(node_id) -> dict`,
  `get_transitions(t_a, t_b) -> dict`, `get_frame(frame: int) -> list[dict]`, `redecode(t_a, t_b, fps=2.0) ->
  list[dict]`.

**Rules** (spec §6: "`ask`'s tools return lifetimes, changes and interpretations"; "`ask`'s frame tool returns the image,
the texts alive at that frame and the description in force"; a `get_pairs` tool is a follow-on and is not built):
1. `TOOL_DEFS` has exactly these five tools; the descriptions are prompt text:
   - `search` — "Search the record of what was on screen and what changed. Lexical: exact strings work best, and text
     inside double quotes is matched as a phrase (commands, flags, identifiers, paths). Returns ranked hits of several
     kinds: lifetime (one on-screen text, once, with its first and last time and its readings), transition (a change
     between two captured frames with its interpretation, entered_text and submitted), frame (a whole screen; identical
     consecutive frames come back as one hit with a frame range, showing only the matching lines), step, section, video,
     chapter. Narrow with level, t_from and t_to (seconds) or app." Input: `query` (string, required); `level` (string:
     "lifetime|frame|transition|step|section|video|chapter"); `t_from`, `t_to` (number); `app` (string).
   - `get_node` — "Fetch one entry in full by node_id. A lifetime's payload holds every reading of each reader with
     counts, whether the readers agree, whether it was seen once, its links (a pair's key and value, a wrapped run) and
     its window. A transition's payload holds the full change record and the interpretation. A frame's payload lists
     every text box of that screen with its lifetime id." Input: `node_id` (string, required).
   - `get_transitions` — "List the transitions that overlap [t_a, t_b] seconds, in order: what changed (one line), the
     interpreted action and result, entered_text and submitted. Use it to establish order: what was entered, whether and
     when it was submitted, what followed. A long range is cut; continue from next_t_a." Input: `t_a`, `t_b` (number,
     required).
   - `get_frame` — "Look at one captured frame: the screenshot, every text alive at that frame (box id, lifetime id,
     text, when it was first and last seen, other readings) and the screen description in force. Use it when a reading
     is doubtful or the question is about something visual." Input: `frame` (integer, required).
   - `redecode` — "Re-decode the source video between t_a and t_b seconds at the given fps and return the first few
     frames as images: a recovery tool for what happened between two captured frames." Input: `t_a`, `t_b` (number,
     required), `fps` (number, default 2).
2. `search` returns `{"hits": [hit_summary(h) for h in index.search(…)]}` with collapsing as configured.
   `hit_summary`: `node_id, level, item_id, frames, t, score` and `text`; for a `frame` hit `text` is its `matched`
   lines joined by newlines and `collapsed` is added; a `lifetime` hit adds `sightings`, `unstable`, `seen_once`,
   `agree` and `readers` (`{"ocr": text, "vlm": text or None}`) from its payload; a `transition` hit adds
   `entered_text`, `submitted` and `confidence` from its payload's interpretation (`None` without one). The payload
   itself is never in a hit.
3. `get_node`: as today (`level, item_id, frames, t, text, payload`); an unknown id → `{"error": "no such node"}`.
4. `get_transitions`: the changes with `t[1] ≥ t_a` and `t[0] ≤ t_b`, in order, as `{"transitions": [item, …]}` with
   item = `{"id", "node_id", "frames", "t", "kind", "summary": render_change_line(c), "action", "result",
   "entered_text", "submitted", "confidence", "undoes": [of, …]}` (interpretation fields `None` without one). The first
   item is always included; further items are added while `len(json.dumps({"transitions": items}))` stays within
   `cfg.ask.max_tool_result_chars`; when the next one does not fit, the result gains `"truncated": true` and
   `"next_t_a"` = that change's `t[0]`, so the result is always valid JSON (today's cut is mid-string).
5. `get_frame`: an unknown frame → `[text_block("no such frame")]`. Otherwise one text block then the image at full
   resolution (the agent looks at a frame in order to read it). The text: `Frame {n}, t={t_settled:.2f}–{t_end:.2f}s.` ·
   `Description in force: {description}` or `Description in force: none.` · `Texts alive at this frame (box, lifetime,
   text; when seen; notes):` · then per box in reading order `{box_id} {lifetime_id} "{text}" | seen
   {first.t:.1f}–{last.t:.1f}s in {sightings} frames`, followed, each only when it applies, by ` | other OCR readings:
   "x", "y"` (the lifetime's other readings, by count descending then string), ` | model reads "{vlm}"` (the box's label
   has `agree` false and a non-empty `vlm`) and ` | {box_label}` · then per missed text in force `{id} (no box)
   "{text}"`. A text is alive at a frame when its lifetime's `boxes` holds a ref of that frame. With the PNG missing,
   the image block is replaced by `text_block("(the image file is missing)")`.
6. `redecode`: as today, through `scry.video.iter_frames(video, start=t_a)` with the video path from the manifest: a
   frame is taken at the first decoded time ≥ each of `t_a, t_a + 1/fps, …` up to `t_b`, at most
   `cfg.ask.redecode_max_frames`; each is saved under `<run>/redecode/` and returned as `t={t:.2f}s:` plus the image;
   none → `[text_block("no frames in range")]`.
7. No tool reports focus, and none derives "was run" from a duration: `sightings`, `first` and `last` are passed on as
   the measurements they are.

**Tests to write first** (Fixture M with labels and interpretations, indexed, unless given):
- `test_tool_defs`: the names are exactly `{"search", "get_node", "get_transitions", "get_frame", "redecode"}`; every
  `input_schema` is an object schema with `required` as in rule 1; no description contains `focus`.
- `test_search_tool_returns_summaries`: `Tools(run, Config()).search("Creating")["hits"]` → node ids `["v:L2", "v:T3",
  "v:f10"]`; no hit has `payload`; the first has `sightings 3`, `unstable False`, `seen_once False`, `agree True`,
  `readers {"ocr": "Creating", "vlm": "Creating"}`; the second has `entered_text None`, `submitted "no"`, `confidence
  0.7`; the third has `text "Creating\nStatus Creating"`, `collapsed 3`, `frames [10, 12]`.
- `test_get_node`: `get_node("v:T2")["payload"]["interpretation"]["submitted"] == "yes"`; `get_node("v:nope") ==
  {"error": "no such node"}`.
- `test_get_transitions_window_and_truncation`: `get_transitions(24.0, 26.0)` → ids `["T1", "T2"]` (T3 starts at 30.0); the
  second item has `summary "T2 [f11→f12, 26.0–26.4s] appeared 2"`, `entered_text "git status"`, `submitted "yes"`,
  `node_id "v:T2"`, `undoes []`; `get_transitions(0, 100)` → three ids and no `truncated` key. With
  `AskConfig(max_tool_result_chars=600)`, `get_transitions(0, 100)` → ids `["T1"]` (T1 and T2 together exceed 600
  characters), `truncated True`, `next_t_a 26.0`; with `max_tool_result_chars=10` → still `["T1"]`.
- `test_get_frame_returns_image_texts_and_description` (F7): `get_frame(12)` → two blocks, the second an image block of
  the 400×200 PNG; the text starts `Frame 12, t=26.40–30.00s.\nDescription in force: The terminal shows new output.`
  and contains the lines `b2 L2 "Creating" | seen 20.4–30.0s in 3 frames | Azure Portal window, Essentials, value of
  "Status"`, `b3 L4 "C:\src> git status" | seen 24.4–35.0s in 3 frames | Windows Terminal window` and `b4 L5 "On branch
  main" | seen 26.4–35.0s in 2 frames | other OCR readings: "On branch maln" | Windows Terminal window`.
  `get_frame(13)` contains `b4 L5 "On branch maln" | seen 26.4–35.0s in 2 frames | other OCR readings: "On branch main"
  | model reads "On branch main" | Windows Terminal window` and `m1 (no box) "Refresh"`. Without labels, `get_frame(11)`
  has `Description in force: none.` and the line `b3 L4 "C:\src> git status" | seen 24.4–35.0s in 3 frames`.
  `get_frame(99)` → one text block, `no such frame`.
- `test_redecode_returns_capped_frames`: with `video_factory` (the synthetic encoder of `tests/conftest.py`), 60 gray
  64×64 frames at 30 fps, the manifest's `video` pointing at the file, and `AskConfig(redecode_max_frames=2)` →
  `redecode(0.0, 2.0, fps=2)` returns four blocks (text, image, text, image), the first text starting `t=0.`;
  `redecode(50.0, 60.0)` → `no frames in range`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_ask.py -q`. Expected: FAIL (`No module named scry.ask`).
- [ ] **Step 2:** Implement rules 1–7.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed.
- [ ] **Step 4:** Commit: `feat(ask): tools over lifetimes, changes and interpretations; the frame tool returns image, live texts and description`

### Task 15: `ask`: the prompt that guides, the loop, usage and cost, `scry ask`

**Files:**
- Create: `src/scry/prompts/ask.py`
- Modify: `src/scry/ask.py`, `src/scry/cli.py`, `tests/test_ask.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `Tools`, `TOOL_DEFS` (Task 14); `add_usage`, `estimate_cost` (Task 3); `fakes.fake_sync_client` (Task 1).
- Produces: `scry.prompts.ask.VERSION = "ask-v1"`, `SYSTEM` (below), `PROMPTS: dict[str, str] = {"ask-v1": SYSTEM}`
  (P5 adds wording variants here, spec §9); `class AskResult(BaseModel)`: `text: str` · `citations: list[str]` · `turns:
  int` · `tool_calls: list[str]` · `usage: dict` · `cost_usd: float` · `model: str` · `prompt: str` · `stop: str` (the
  names plan 4 assumes, A9); `extract_citations(text: str) -> list[str]`; `ask(run: Run, cfg: Config, question: str,
  client=None) -> AskResult`; CLI `scry ask RUN_DIR QUESTION [--json] [--config PATH] [--verbose]`.

**Rules:**
1. The prompt **guides and does not prohibit** (spec §6): quote verbatim where independent readers agree; where they
   differ, or a text is `unstable` or seen once, say so or look at the frame; an input field may show a suggestion;
   `submitted` is the primary evidence that a command ran, and without it say what was seen and how sure; time on
   screen is not evidence either way. It names no window as focused.
2. The system prompt is `PROMPTS[cfg.ask.prompt]`; an unknown name raises `ValueError` listing the names, before any
   call. The loop is today's manual loop: up to `cfg.ask.max_turns` calls of `client.messages.create(model=cfg.model.model,
   max_tokens=cfg.model.max_tokens, system=<that prompt>, tools=TOOL_DEFS, output_config={"effort": cfg.model.effort_ask},
   cache_control={"type": "ephemeral"}, messages=messages)`. The top-level `cache_control` caches the growing
   conversation, whose frame images are otherwise re-billed at full price every turn (Decision D17). The assistant's
   `content` is appended unchanged every turn.
3. Every `tool_use` block of a turn is executed and **all** results go back in one user message. A name outside
   `TOOL_DEFS` → a `tool_result` with `is_error` and `error: unknown tool {name}`; an exception inside a tool → `is_error`
   and `error: {exception}`; a list result (blocks) is passed as is, a dict as JSON cut to
   `cfg.ask.max_tool_result_chars`. Tool errors never end the loop.
4. The loop ends when `stop_reason` is not `tool_use`: `text` is the concatenated text blocks; an empty text with
   `refusal` or `max_tokens` → `No answer: the model stopped with {reason}.`; after `max_turns` tool turns → `Stopped
   after {max_turns} turns without a final answer.` with `stop "max_turns"`.
5. `usage` sums the four keys over every response (`add_usage`; absent attributes count 0); `cost_usd =
   estimate_cost(usage, cfg.model.model)`; `tool_calls` lists the tool names in call order; `model` and `prompt` are
   the configured names. `citations = extract_citations(text)`: every match of the pattern
   `\b(\d+:[bm]\d+)\b|\b[Ff]rames?\s+(\d+)`, in order of appearance and without repeats, a box or missed-text ref as it
   stands and a frame as its number. Each call is a fresh conversation; `ask` uses no call cache and writes no file
   (spec §2: `ask` writes nothing).
6. `scry ask` prints the text to stdout and `turns={turns} tools={names joined by ","} cost=${cost_usd:.4f}` to
   stderr; with `--json` it prints `AskResult.model_dump_json(indent=2)` to stdout instead (the evaluation's question
   set reads cost per question from it, spec §9).

**The system prompt:**

```
You answer questions about a screen-recording tutorial from a searchable record of what was on its screen and what
changed.

What the record holds
- lifetime entries: one piece of on-screen text, recorded once, with the first and last time it was visible, the
  number of captured frames it was seen in (sightings), and every reading of it. "ocr" is an OCR engine's reading.
  "vlm", when present, is a vision model's independent reading of the same pixels. A lifetime may carry links: a pair
  (a label and its value, such as Status and Succeeded) or a run (one text that the screen wrapped over two lines,
  indexed joined both with and without a space).
- frame entries: everything on screen at one captured frame: the windows, every text box in reading order, and a
  prose description of what text cannot express (selections, toggles, dialogs, icons). Consecutive frames whose
  matching lines are identical come back as one hit with a frame range and a time range.
- transition entries: what changed between two consecutive captured frames, and a model's interpretation of it:
  action, result, entered_text (what the user had entered, as far as the frames showed, without anything the
  application suggested) and submitted (yes, no or unclear: whether what was entered took effect).
- steps, sections and the video summary are written from the transitions. They are good for finding where in the
  video something happens; confirm the details in the entries below them.

How to work
Search first; put exact strings such as commands, flags and identifiers in double quotes. Read the entries you find.
List the transitions around a time when order matters: what was entered, whether it was submitted, what followed. Look
at a frame whenever a text is doubtful or the question is about something visual. Give a frame number and a time for
every factual claim, so the reader can check it; write a frame as "frame 12" and a text box as "12:b4".

How sure you can be of a text
- Quote a text verbatim when two independent readers agree on it ("agree": true), or when one reader gave the same
  reading over several sightings of the same pixels ("unstable": false, more than one sighting).
- When the readers differ, when a text is marked unstable, or when it was seen in a single frame, say so: give the
  readings you have, or look at the frame and read it yourself. The usual difference is one character (l and 1, a
  missing space), and in a command that matters.
- When only one reader exists, entered_text on a transition is a second opinion on a command's text: a model read it
  from the frames.
- An input field may show a suggestion the application offered and the user did not enter: a shell's predicted command
  in grey, an autocomplete entry, placeholder text. A text on an input line is therefore not proof that anyone typed
  it, and still less that it ran.

Whether something was done
- submitted: yes on a transition is the primary evidence that a command ran or a form was sent; it rests on what the
  frames showed next, such as output that answers the command or a new prompt under it. Cite that transition.
- Without it, report what was seen and how sure you are, for example: "the line read X at 10:55; no transition shows
  it being submitted". When the question is whether something was done and nothing shows it, the honest answer is that
  the record does not show it being done, together with the closest thing that was seen.
- How long a text stayed on screen is not evidence either way. A command can run and scroll away at once, or sit
  unexecuted for a minute, and a one-line terminal shows no history.

When the record does not answer the question, say so and name the time range worth inspecting; redecode can recover
frames between the captured ones.
```

**Tests to write first:**
- `test_prompt_guides_and_does_not_prohibit` (substring checks after collapsing whitespace runs to one space): `SYSTEM`
  contains `submitted: yes on a transition is the primary
  evidence`, `An input field may show a suggestion`, `is not evidence either way`, `"agree": true`, `seen in a single
  frame`; it contains none of `focus`, `Answer only`, `agree=true`, ` never `, ` must `, `Do not`, `kubectl`, `az `;
  `VERSION == "ask-v1"`.
- `test_ask_loop_runs_tools_and_reports_cost`: `fake_sync_client([response([tool_use("u1", "search", {"query": "\"git
  status\""})], "tool_use"), response([tool_use("u2", "get_frame", {"frame": 12}), tool_use("u3", "get_transitions",
  {"t_a": 24.0, "t_b": 27.0})], "tool_use"), response([text("They ran `git status` at 26.0–26.4 s (T2, frame 12; the
  output is 12:b4).")], "end_turn")])` → `AskResult.text` is that sentence, `citations ["12", "12:b4"]`, `model
  "claude-opus-5"`, `prompt "ask-v1"`, `turns 3`, `tool_calls ["search", "get_frame",
  "get_transitions"]`, `usage {"input_tokens": 3000, "output_tokens": 300, "cache_read_input_tokens": 0,
  "cache_creation_input_tokens": 0}`, `cost_usd 0.0225`, `stop "end_turn"`. Every `create` call had `system == SYSTEM`,
  `tools == TOOL_DEFS`, `output_config == {"effort": "high"}`, `cache_control == {"type": "ephemeral"}`. The third
  call's last message is one user message holding two `tool_result` blocks, ids `u2` and `u3`; the first one's content
  is a list whose second element is an image block.
- `test_ask_tool_errors_and_stops` (Review Focus 4): a turn with `tool_use("u1", "nope", {})` and `tool_use("u2",
  "get_transitions", {"t_a": 1})` (a missing argument raises inside the tool) → both results have `is_error` true (`error: unknown tool nope`; the second starts
  `error:`), and the loop goes on to the scripted final text. A response with `stop_reason "refusal"` and no text →
  text `No answer: the model stopped with refusal.`, `citations []`, `stop "refusal"`. `AskConfig(max_turns=2)` with a
  client that always asks for a tool → `Stopped after 2 turns without a final answer.`, `stop "max_turns"`, `turns 2`, usage summed
  over both.
- `test_extract_citations`: `extract_citations("See frame 12 and 12:b4, then Frame 13; frames 12 again (13:m1).") ==
  ["12", "12:b4", "13", "13:m1"]`; `extract_citations("nothing here") == []`.
- `test_unknown_prompt_variant`: `AskConfig(prompt="nope")` → `ask` raises `ValueError` naming `ask-v1`, and the fake
  client received no call.
- `tests/test_cli.py::test_cli_ask_json`: with `scry.ask.ask` monkeypatched to return a fixed `AskResult`, `scry ask
  <dir> "q" --json` exits 0 and stdout parses as JSON with `cost_usd`; without `--json` stdout is the text and stderr
  has `cost=$`.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_ask.py tests/test_cli.py -q`. Expected: FAIL
  (`ImportError: ask`).
- [ ] **Step 2:** Write the prompt module; implement rules 2–6 and the command.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry --help` lists `ask` and `search`.
- [ ] **Step 4:** Commit: `feat(ask): guiding prompt ask-v1; tool loop with usage and cost per question; scry ask --json`

### Task 16: `scry run` over the whole pipeline, the cost summary, and the end-to-end test

**Files:**
- Modify: `src/scry/cli.py`, `tests/test_cli.py`
- Create: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `run_decode`, `run_read`, `run_track` (plan 1), `run_outline`, `run_annotate` (A5), `run_interpret`,
  `run_summarize`, `build_index`, `run_costs`.
- Produces: `STAGES = ["decode", "outline", "read", "track", "annotate", "interpret", "summarize", "index"]`; `scry run
  VIDEO --out DIR [--config PATH] [--stages a,b,…] [--verbose]`.

**Rules:**
1. `run` executes the wanted stages in `STAGES` order (spec §2's order), each through its stage function, echoing `==
   {name}` and recording the stage's wall seconds in its manifest entry as today. `outline` does nothing unless
   enabled; `annotate` is plan 2's function, which itself decides whether annotation is off (A5); every later stage
   runs with or without `annotations.jsonl`.
2. After the last stage: `run.manifest_update(costs=run_costs(run.manifest_read()))` and the costs are echoed as JSON
   (they replace today's diagnostics print; guards belong to plan 1's `scry report`).
3. An unknown name in `--stages` exits with code 2 and names the valid stages.
4. The CLI's command list after this plan: `decode, outline, read, track, annotate, interpret, summarize, index,
   search, ask, report, subset, setup, run` (plan 4 adds `eval`).

**Tests to write first:**
- `tests/test_cli.py::test_run_executes_stages_in_pipeline_order`: every stage function monkeypatched to append its
  name to a list → `scry run v.mp4 --out <dir>` records `["decode", "outline", "read", "track", "annotate",
  "interpret", "summarize", "index"]`; with `--stages index,read` → `["read", "index"]`; `--stages perceive` → exit
  code 2. The manifest has a `costs` entry with `total_usd 0.0`.
- `tests/test_pipeline.py::test_pipeline_end_to_end_with_annotations`: Fixture M with labels; `run_interpret` with a
  `ScriptedProvider` whose `interpret` entry is a callable that reads the `Transition T<n>:` line of the call's
  `Changes:` block and returns the `ModelInterpretation` matching Fixture M's interpretation of that transition;
  `run_summarize` with the script of Task 9's first test; `build_index`; then: `search(db, '"git status"',
  cfg.index)[0]["node_id"] == "v:L4"`; a search for `Run git status` returns the step `v:S1`;
  `Tools.get_transitions(24.0, 26.0)` lists T1 and T2 with `submitted` `no` and `yes`; `ask` with a fake client that
  searches and then answers returns that text with `cost_usd > 0`; `run_costs(manifest)` has the stages `interpret` and
  `summarize` and `per_frame_usd is None` (no `decode` entry in a hand-written run).
- `::test_pipeline_end_to_end_without_annotations` (Review Focus 1): the same without labels → every stage completes;
  `stages.interpret.labels is False`; `by_level` is `{"frame": 4, "lifetime": 7, "transition": 3, "step": 2, "section":
  1, "video": 1}`; `search(db, "Overview", cfg.index) == []` (there is no description to find: part of what the
  no-annotation base prices, spec §12); `search(db, '"On branch maln"', cfg.index)` returns hits.

- [ ] **Step 1:** Write the tests. Run `uv run pytest tests/test_cli.py tests/test_pipeline.py -q`. Expected: FAIL
  (`STAGES` is plan 2's shorter list; the costs entry is missing).
- [ ] **Step 2:** Implement rules 1–4.
- [ ] **Step 3:** `uv run pytest -q` → 0 failed. `uv run scry --help` lists the commands of rule 4.
- [ ] **Step 4:** Commit: `feat: scry run over decode → outline → read → track → annotate → interpret → summarize → index, with a cost summary`

---

## Decisions this plan makes (for the reviewers)

The spec is silent or looser on each of these; none is settled until reviewed. Each names the principle it rests on.

- **D1. Module layout.** `changetext.py` (one renderer for `interpret`, `summarize` and `ask`), `interpret.py`,
  `summarize.py` (was `hierarchy.py`), `nodes.py` (extraction) beside `index.py` (storage, search), `ask.py` (was
  `agent.py`), `prompts/interpret.py`, `prompts/summarize.py`, `prompts/ask.py`. Code is adapted by reading the tag, not
  by importing it (spec §8: the branch cannot import the old machinery).
- **D2. `entered_text` is the state of the user's input as frame b shows it, not the keystrokes of one transition;** on
  a submission it is the whole submitted text, even when typing was never seen. §5 says "what the user entered in this
  transition as far as the frames show". The ground truth has commands that were never seen being typed (`kubectl get
  nodes`, `kubectl get pods`) and records "what the presenter had actually entered" as the whole input (`az ak`,
  `kubect`). Only this reading lets the transition with `submitted: yes` carry the command, which the *false run* and
  submission-time metrics of §9 and the agent's "primary evidence" need. The prompt or the field label is excluded.
- **D3. `submitted` when nothing was entered** is `no`, unless the frames show a form or button submission, which is
  `yes` with `entered_text` null (§5 says "a command or form").
- **D4. Image modes are `scaled` (default, L39), `crops` and `full`; `text` is gone.** L39 measured the text-only mode
  fabricating a click and misplacing the cursor, and the honest contract leaves interpretation to the frames
  (principle 4), so a mode without frames contradicts the design. `crops` is `scaled` plus full-resolution before and
  after crops of the rectangles where **text** changed (group rectangles, appeared and removed boxes), from OCR's
  coordinates as §6 says; it is a pure superset of the default, which makes P5's comparison clean. The pad is 2 × the
  median box height instead of L39's 40 px (no pixel constants from the sample; at the sample's box height it is about
  the same). Changed areas without text are not cropped; both half-scale frames show them. If P5 shows that they need
  full resolution, plan 1's `PixelSource.diff(a, b).components` has their rectangles.
- **D5. The change text** (Task 4): the header gives the interval in which the change happened (`Change.t`, plan 1:
  from the earlier frame's end to the later frame's settling), not two frame times; one line per group with after ids
  before before ids; `appended` and `truncated`
  show the added or removed characters and the whole text after; `reread` groups are shown (they sit under changed
  pixels, so something visual happened there); nothing is capped, since every listed id is citable; `same_place` gets
  its own count line beside the two the spec names; a group's `clock` flag (plan 1's addition) is not rendered.
- **D6. Citable ids are exactly the ids printed in the change text.** Missed texts (`m<n>`) are "citable, never in a
  change" (§3), and `interpret` hands over only changes, so they are not citable there. Repeats are dropped silently;
  anything else is counted as invalid; there is no re-prompt (design §12).
- **D7. The context lines and the summary items are mechanical one-liners** with two presentation limits, three groups
  and 80 characters per text; neither is tuned on anything, and the full change text never uses them.
- **D8. Prompt examples and fixtures use invented content,** never the sample's commands: an example taken from the
  evaluated video would leak the answer key into the prompt under test (§9 evidence rules).
- **D9. `summarize`:** the tag's literals 80, 60 and 25 become named constants, not config keys; `focused` leaves the
  state line (§0: focus is not a deliverable); elaboration refs outside the segment are counted as well as dropped
  (design §13.2 says counted; the tag only dropped them); `outline.json` and `annotations.jsonl` join the stage's
  inputs; stage names become `summarize-boundary-*` and `summarize-elaborate-*`, so no old cache entry is reused.
- **D10. The frame document holds more than "every box's text plus the description".** It also holds the container
  names, the model's reading where it differs, the missed texts and the link lines. Each is something today's region
  and frame entries hold for that frame; leaving any out would make something findable today unfindable (the owner's
  ruling in §6). It is one document per frame, as the spec requires.
- **D11. `non_text`** removes a lifetime entry only when every annotated sighting of the lifetime said so, and never a
  line of a frame document. §5 says a `non_text` box "leaves … index text"; §6, written later at the owner's
  instruction, says "every box's text". This reading satisfies both: a wrong label costs an enrichment, never
  findability (principle 1).
- **D12. Where a link's text lives.** On the entry of the link's anchor: a run's first box, a pair's first **value**
  box (the pairing lasts as long as the value; the label usually outlives many values), a record's first cell. The spec
  names run and pair text only; a record is indexed as its cells joined by spaces because L41 showed joined row text is
  what makes a table row a search hit. Equal observations across frames are one link with a `seen` count; differing
  ones are all kept (principle 5).
- **D13. `submitted` and container names are not index text on transition and lifetime entries.** `yes` and `no` match
  everything lexically; a window name in every lifetime of that window would flood its family's ranking. Both are in
  the payload and in `ask`'s hit summaries, the container apps serve the `app` filter, and the names are index text in
  the frame document (D10).
- **D14. The collapsing rule** (Task 13 rules 4–6): frame-level hits only; "matching text" is the tuple of lines
  containing a query term as a case-folded substring (the whole text when none does); consecutive means consecutive
  positions in `frames.jsonl`; the representative is the earliest member and takes the best member's rank; the frame
  rankings are not cut before collapsing, because a run is only visible with all its members. Every choice errs
  towards collapsing less.
- **D15. One ranking per family** (lifetime, transition, frame, summary), fused by reciprocal rank, ties broken in that
  order. Today all levels share one pool, and §6 records that duplicates crowd other results out of the top k. If H7
  fails and lifetimes fragment, a shared pool would let them crowd out frame entries; separate rankings make "additive"
  true in the ranking as well as in the table. The `rrf` function itself is unchanged.
- **D16. Times.** A lifetime entry spans `first.t` to `last.t` (plan 1: the last frame's `t_end`). A text is alive at a
  frame when its lifetime's `boxes` holds a ref of that frame.
- **D17. `ask`.** It returns an `AskResult` with usage and dollars and writes no file (§2); `scry ask --json` exists for
  the question-set scripts. Its field names are the ones plan 4 assumes (`text`, `citations`, `usage`, `model`,
  `turns`, `tool_calls`). `citations` are read out of the answer's prose by one pattern (box refs and "frame N"), and
  the prompt asks for that spelling: the agent's answer stays free text, and a structured answer format is not
  introduced for the evaluation's sake. `[ask] prompt` selects a named wording from `PROMPTS`, which holds one entry
  until P5 adds the variants it compares. `get_transitions` returns compact items and truncates on an item boundary; the first item
  always fits. `search` shows a frame hit's matching lines, not its whole text. The loop passes a top-level
  `cache_control` so re-sent frame images are billed as cache reads; this follows the SDK's documentation and has not
  been exercised live (no model call is made in this plan), so the first paid question confirms it from
  `usage.cache_read_input_tokens`.
- **D18. Cost.** A stage's `usage` is the sum over its records of the usage of the call that produced each record,
  cached or not: what these outputs cost to produce, which is the number §9 compares (plan 2's D23 says the same of
  `annotate`). Both the synchronous and the batch price are recorded, because one execution can mix them. The pricing
  of cache-creation tokens, the sum over retries and the batch usage key were first drafted here and now land with
  plan 2's Task 8 (A6); plan 4's Task 1 restates them under other names (A9b), which the synthesis must settle.
- **D19. `run` order** is `decode, outline, read, track, annotate, interpret, summarize, index` (the brief's order; the
  tag ran `outline` first, and nothing depends on its position before `summarize`). Whether annotation runs is plan 2's
  switch inside `run_annotate`.
- **D20. No metric is defined here.** *Found*, submission error and *false run* need this plan's records and were
  deferred by plan 1 (its D21); plan 4's Task 4 defines them over `search` and `interpretations.jsonl`, and this plan
  only guarantees what they read (A9): `entered_text` holds the whole submitted text on the submitting transition,
  hits carry `t` and `frames` that cover every collapsed member, and a quoted query stays a phrase.
- **D21. Trivial transitions** are not interpreted and not summarised, and are indexed from their group texts, as today.
- **D22. A missing frame PNG** yields `error "missing_png"` without a call: `track` already degrades on a missing PNG
  (plan 1), and a call without its images would be the text-only mode D4 removes.

## Not in this plan

The paid phases P1–P6 and their ledger rows; arms B–D, the scale sweep, incremental annotation and the pane switch
(§10 step 8); a `get_pairs` tool (§6: a follow-on); the design document's revision 7, README and CONTRIBUTING (§10
step 9); the evaluation harness and every metric (plan 4). After Task 16 the branch is ready for P1: `scry run` over a span with each of the three bases, `scry report`
for the guards and command metrics, `scry ask --json` for the question set, and `manifest.costs` beside every number.

## Self-review

- **Spec coverage.** §5 `interpretations.jsonl` → Tasks 1, 5, 7. §6 `interpret` (half scale, one call per non-trivial
  transition, nothing folded, change text with ids and labels, both readings, appeared and removed ids, moved and
  textless lines, `reverts`, citation validation, the suggestion sentence) → Tasks 4–7. §6 `summarize` → Tasks 8–9. §6
  `index` (lifetime entries, both joins, pair fields, transition entries, steps, sections, video; whole-screen entries
  kept; collapsing in the result list) → Tasks 10–13. §6 `ask` (tools, frame tool, guiding prompt) → Tasks 14–15. §7
  (both readings recorded and indexed, `agree` the only verbatim signal, `unstable` the hedge with one reader) → Tasks
  10, 11, 15. §8 new config and kept cost accounting → Tasks 2, 3. §9 cost beside every number → Tasks 3, 7, 9, 15,
  16; §9's metrics are plan 4's (D20). §10 steps 4–7 → the whole plan. §4 principles 3, 4, 5, 7, 9 → Global
  Constraints and the rules that cite them.
- **Placeholders.** None: every test names its fixture and expected values; the three prompts and the five tool
  descriptions are given in full; no step says "handle edge cases".
- **Type consistency.** `Interpretation`, `ModelInterpretation`, `HierNode`, `ModelBoundaries`, `ModelElaboration`
  (Tasks 1, 5) are the names used in Tasks 7–16; `render_change`, `render_change_line`, `box_label`, `change_rects`,
  `text_of` (Task 4) in 6, 8, 10, 14; `build_blocks` returns four values (Task 6) and Task 7 uses all four;
  `link_anchor`, `link_lines` (Task 10) in 11; `frame_nodes`, `lifetime_nodes`, `transition_nodes`, `summary_nodes`,
  `extract_nodes` (Tasks 10–12); `search(…, collapse=…)`, `matched_lines`, `collapse_runs`, `FAMILIES` (Task 13) in
  14, 16; `Tools`, `TOOL_DEFS`, `AskResult`, `ask` (Tasks 14–15) in 16; `add_usage`, `estimate_cost` (A6), `stage_cost`,
  `run_costs` (Task 3) in 7, 9, 15, 16; `ScriptedProvider`, `fake_sync_client`, `mini_run`, `mini_interpretations`
  (Task 1) throughout.
- **Review focus.** Each of the five lines names its tests and the tasks that own them.
- **Standing rules.** No constant comes from the sample video (the one pixel constant inherited from L39 became
  relative, D4). No rule locates a cursor or a suggestion; the prompts ask a model to look. No rule, prompt or metric
  uses time on screen as evidence that something ran; the two prompts that mention it say it is not evidence. Focus
  appears nowhere.
