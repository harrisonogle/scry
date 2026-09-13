# Visual Transcript Pipeline — Design Specification (v1)

| | |
|---|---|
| **Status** | Draft design, pre-implementation |
| **Date** | 2026-09-13 |
| **Scope** | Silent screen-recording tutorial videos → exact, timestamped, queryable "visual transcript" |
| **Audience** | A cold reader with systems-programming background and no prior context on this project |

---

## 0. How to read this document

Section 1 states the problem and requirements. Section 2 is a one-page summary of the design. Section 3 records every load-bearing decision and why it was made. Section 4 is a glossary; terms are defined there once and used freely afterward. Section 5 summarizes the tool landscape that was surveyed, so the choices in Section 3 are legible. Sections 6–14 are the stage-by-stage specification (with the data model in §10); §15 gives the prompt contracts, §16 the parameters, §17 failure modes, §18 the evaluation plan, §19 the cost model, §20 implementation notes, §21 the v2 roadmap, §22 open questions, and §23 references.

Anything marked **[verify]** is a fact recalled rather than confirmed from documentation during design and should be checked before it is relied on. Anything marked **[reasoned]** is a rule derived from first principles rather than taken from literature or prior art, and should be validated against ground truth.

---

## 1. Problem statement

### 1.1 Inputs

- Screen recordings of computer tutorials: terminals, code editors, browsers (e.g., a cloud portal), text editors, dialogs.
- **No audio track.** All information is visual.
- Typical resolution 1080p or 1440p at 30 or 60 fps. **4K is out of scope for v1** (see §21).
- Videos already exist; there is no control over how they were recorded (no OS-level capture of window trees or input events). See §21 for what changes if that control is gained.

### 1.2 Required outputs

A **visual transcript** per video, consisting of:

1. **States (levels):** for every distinct screen state, the exact visible text, organized by window and pane, with pixel bounding boxes and timestamps.
2. **Transitions (edges):** for every change between consecutive states, what changed (exact text diff), what user action explains it, and what the result was.
3. **Hierarchy:** transitions grouped into steps, steps into sections, sections into a whole-video summary, with every summary sentence traceable to specific frames.
4. **A queryable index** over all of the above. The primary use is **answering questions about the videos** (e.g., "what command did they run to publish?", "which resource group was selected?"), not producing a single summary.

### 1.3 Requirements

| ID | Requirement | Consequence for design |
|---|---|---|
| R1 | **Exactness of on-screen text.** Commands, code, paths, and identifiers must be reproduced character-for-character. | Dedicated OCR cross-checked against a vision model; verbatim-transcription prompting; no model is allowed to "correct" text. |
| R2 | **Timestamps** on every state and transition, derived from the video clock, never from a model. | Frames carry timestamps from the decoder; models reference frame IDs only. |
| R3 | **Traceability.** Every sentence at every level of the hierarchy must be traceable to frame IDs and therefore to PNGs. | Frame ranges propagate upward through the hierarchy and are validated. |
| R4 | **Structured intermediates.** All intermediate data is JSON; prose appears only in final human-facing fields. | Structured-output prompting with explicit schemas and field descriptions. |
| R5 | **Per-component measurability.** Every stage must be independently evaluable and switchable. | Ground-truth harness with per-component metrics from day one; ensemble members are separate stages. |
| R6 | **Cold-runnable.** A new video runs end to end with no manual steps. | Deterministic stage boundaries, idempotent stages, content-addressed frame storage. |

### 1.4 Non-goals (v1)

- Audio processing of any kind.
- 4K input (needs crop-by-region; deferred to v2).
- Real-world (camera) footage.
- Live/online processing; all processing is offline over complete files.
- Interactable-element detection (buttons, icons) beyond what text lines and regions provide (OmniParser-class parsing is v2).

---

## 2. Design summary

The pipeline decodes the video at native frame rate, detects every screen change with a pixel-difference test, waits for the screen to settle, and emits one frame per distinct settled state. Each emitted frame is perceived twice from the same PNG: by an OCR engine (exact characters with bounding boxes) and by a vision-language model (VLM) that groups the OCR'd lines into windows and panes, names them, and produces its own verbatim transcription. The two transcriptions are aligned line by line and an agreement flag is recorded. Consecutive states are diffed at line level to produce exact text deltas, which are coalesced into action-sized events (typed commands, appended output). A second VLM call per transition sees both frames as images plus the computed diff and produces an interpretation (action, result). Transitions are then grouped by semantic segmentation into steps, steps into sections, sections into a whole-video summary. Every node from every level is indexed for lexical and vector retrieval, and an agent answers questions over that index, fetching the underlying frame images as evidence when needed. In parallel, Gemini's agentic video mode produces a coarse chapter outline of the whole video that is used as global context and as a retrieval document, but never overrides frame-level evidence.

```
                 ┌──────────────────────────────────────────────────────────────┐
                 │ Stage 0 (parallel): Gemini agentic video → outline.json      │
                 └──────────────┬───────────────────────────────────────────────┘
                                │ global context (read-only)
 video.mp4                      ▼
   │   Stage 1            Stage 2 (per frame)         Stage 3         Stage 4/4b
   ├─► decode ─► change ─► settle ─► [frame_i PNG] ─► OCR (lines+boxes) ─┐
   │   (native fps)  detect   + churn mask              │                 │
   │                                                    ▼                 │
   │                                       set-of-mark overlay            │
   │                                                    │                 ▼
   │                                       VLM: regions, focus,      merge: bbox union,
   │                                       verbatim transcription ─► align, agree flags ─► frames.jsonl
   │                                                                      │
   │                                                                      ▼
   │                                                          line diff (Myers) → coalesce → transients
   │                                                                      │
   │   Stage 5                                                            ▼
   │   VLM transition pass: (frame_a, frame_b, computed diff, outline ctx) → transitions.jsonl
   │                                                                      │
   │   Stage 6                                                            ▼
   │   semantic segmentation: transitions → steps → sections → video summary
   │                                                                      │
   │   Stage 7                                                            ▼
   │   index every node (lexical + vector) → agent with search/get_frame tools → answers with citations
```

**Levels and edges.** States are *level-triggered* data (what is true while the screen is unchanged); transitions are *edge-triggered* data (what changed). States are the source of truth. Edges are derived: the exact text delta is computed from the merged states, and the interpretation is produced by a VLM that sees both raw images plus that delta. Edges are never derived from text descriptions alone, because descriptions are lossy for non-textual change (a toggled checkbox, a highlighted row, a dialog appearing).

**Two VLM passes.** Stage 2 runs one VLM call per emitted frame (grouping + transcription). Stage 5 runs one VLM call per *coalesced* transition (interpretation). Coalescing (Stage 4b) sits between them and decides which frame pairs Stage 5 examines.

---

## 3. Decision log

| # | Decision | Rationale | Rejected alternatives |
|---|---|---|---|
| D1 | **Frame pipeline, not a video-native model, as the primary path.** | Video-native paths tokenize frames at very low resolution (Gemini: 70 tokens/frame default, 280 at `high`), which loses small text — and small text is the entire content of these videos. An image model at native resolution spends ~2,000–4,800 tokens per 1080p/1440p frame (§19). | Gemini static/agentic as primary (kept as Stage 0 for global context); TwelveLabs Pegasus (built for real-world footage with audio; no evidence on screen recordings). |
| D2 | **Change detection at native frame rate with a settle rule, not 1 FPS sampling.** | 1 FPS was Gemini's default, not a recommendation. Native-rate detection never misses a change that lasted one frame; dedupe collapses static runs so cost is decode time only. Settle captures end states rather than mid-animation frames. | 1 FPS uniform sampling (misses transient UI); keyframe-only extraction (encoder-decided, not content-decided). |
| D3 | **OCR fusion for exactness; VLM for semantics.** | VLMs paraphrase and "correct" code (`npm ci` → `npm install`), drop characters in long strings, confuse `l/1/I`, `0/O`. OCR errors are different in kind (garbled characters), so disagreement is a usable uncertainty signal. | VLM-only transcription (insufficient for R1); OCR-only (no semantics, no grouping). |
| D4 | **Set-of-mark grouping; the VLM never emits coordinates.** | Model-emitted bounding boxes are approximate, provider-dependent, and sometimes in a resized coordinate space. Drawing numbered OCR boxes on the frame and asking the model to group the numbers makes OCR the sole source of geometry and the VLM the sole source of grouping/naming. Grouping visible marks is an easy task; regressing pixel coordinates is not. | VLM-emitted window boxes with calibration; text-only list of boxes handed to the VLM (works, but the visual overlay is more reliable). |
| D5 | **Edges from raw images + computed text diff, not from level text.** | Models miss single-character changes when eyeballing two dense screenshots; string diffs never do. Level text is lossy for non-textual change; images are not. | Text-only transition derivation; image-only transition derivation. |
| D6 | **Structured JSON at every intermediate layer; prose only in final fields.** | Separates observation (`on_screen_text`) from inference (`action`, `result`); enables validation (transcribed text must appear in OCR), diffing, and field-level merging. | Prose descriptions per frame. |
| D7 | **Semantic segmentation between hierarchy levels; map-reduce only within oversized segments; refine pattern not used.** | Steps and sections are semantic by definition; fixed windows cannot produce them. Refine propagates early errors and drifts. | Fixed-size windows; refine. |
| D8 | **Collapsed-tree retrieval (RAPTOR-style) over a temporally segmented tree.** | Tutorials are sequential, so contiguous spans are the right primary tree. RAPTOR's own results favor pooling all levels into one index over strict traversal. | RAPTOR's similarity-clustered tree construction (deferred to v2 for cross-video queries); strict tree traversal. |
| D9 | **Gemini agentic outline as Stage 0, read-only.** | Cheap global context that disambiguates local transitions; useful section-boundary prior; indexable. Must never override frame evidence because its per-frame resolution is low. | Second coarse frame pass with the image model (redundant once per-frame layer is precise). |
| D10 | **No tiling or cropping in v1.** | 1080p and 1440p pass through the chosen image models at native resolution (§5.3). Crop-by-region is an extra failure point needed only for 4K. | Grid tiling (bisects windows); crop-by-region (v2, 4K only). |
| D11 | **Ensemble members are switchable stages with per-component metrics; ensemble-first is acceptable under that condition.** | Cost is not the only ensemble downside: reconciliation logic must exist, and failures must be attributable. Both are solved by independent metrics. | Build-small-then-add (acceptable, not required); like-for-like ensembling of two VLMs per frame (no a priori reconciliation rule — not done). |
| D12 | **Windows.Media.Ocr as the baseline OCR engine; PaddleOCR evaluated against it.** | Zero-setup .NET baseline. Paddle is generally stronger on small monospace text. The evaluation harness decides. | Tesseract (weakest on UI text). |

---

## 4. Glossary

- **Agentic video mode (Gemini):** a processing mode in which the model navigates the video with tools (read transcript, fetch frames for a time window at a chosen frame rate, re-fetch at higher rate) in a reason–call–observe loop rather than receiving all frames up front.
- **BM25 / lexical index:** full-text search scoring exact token matches. Needed for exact strings (commands, identifiers) that embeddings blur.
- **Caret:** the blinking text-insertion cursor (1–2 px wide vertical bar).
- **CER (character error rate):** edit distance between predicted and reference text divided by reference length. Primary metric for R1.
- **Change map:** a per-pixel boolean image marking pixels whose luma differs from the previous frame by more than a threshold.
- **Churn / churn mask:** screen regions that change continuously (spinner, progress bar, playing video). Masked out of change detection so the rest of the screen can settle.
- **Coalescing:** merging a run of consecutive fine-grained transitions (e.g., keystrokes) into one action-sized event.
- **Collapsed-tree retrieval:** putting every node from every level of a summary hierarchy into a single retrieval pool and retrieving top-k across levels, rather than descending the tree.
- **Computer-use model:** a VLM trained to operate a GUI from screenshots by emitting actions (click at coordinates, type, scroll). Frontier VLMs' ability to read screenshots and emit coordinates comes from this training; the internal screen understanding is not exposed as a structured artifact.
- **Context window:** the maximum number of tokens (text + visual) a model accepts in one request.
- **Edge / transition:** the record describing the change between two consecutive emitted frames.
- **Embedding / vector index:** a numeric vector representing meaning; nearest-neighbor search over vectors finds semantically similar text.
- **Emitted frame:** a frame written out by Stage 1 as representing a distinct settled screen state. Also "unique frame."
- **Level / state:** the record describing one emitted frame's contents.
- **Long-edge cap:** a per-image limit: if an image's longer side exceeds N pixels, the provider downscales it before tokenizing. Independent of the context window and of per-request image-count/byte limits; all apply simultaneously.
- **Luma:** the brightness channel of a pixel (grayscale value).
- **Map-reduce summarization:** split items into chunks, summarize each independently (map), summarize the summaries (reduce), recurse if needed.
- **Myers diff / LCS:** the sequence-alignment algorithm behind `git diff`; produces insert/delete/equal runs between two sequences.
- **OCR:** optical character recognition; returns words and lines with bounding boxes and confidence.
- **Patch / visual token:** vision encoders cut an image into a full grid of small squares (28×28 px on Claude, 32×32 px on newer OpenAI models); each becomes one token the language model attends over. Not tiling: the model attends across all patches jointly, so text spanning patch boundaries is normal.
- **Refine summarization:** sequentially update one running summary with each new chunk. Cheap but early errors persist.
- **Region:** a node in the region tree: a window, a pane within a window, or a popup. Leaf regions hold lines.
- **Region tree:** window → panes → lines, built per frame by the set-of-mark grouping call.
- **Settle:** waiting until the screen has been still for a minimum duration before emitting a frame, so the emitted state is an end state rather than mid-animation.
- **Set-of-mark (SoM) prompting:** drawing numbered markers on an image so a model can refer to elements by number instead of by coordinates.
- **Structured output:** requesting model output that conforms to a JSON schema; each field carries a description that defines its meaning to the model.
- **Tiling:** splitting an image into separate images that are encoded independently. Can bisect a window. Not used in v1.
- **Transient:** a region present in one frame but absent from both neighbors and held for a short time (toast, tooltip, dropdown).
- **Two-pass pattern:** find boundaries with a small call, then elaborate each segment with its own call. Used at every level of Stage 6.
- **VLM:** vision-language model; an LLM that accepts images.

---

## 5. Landscape summary (what was surveyed and why it matters)

### 5.1 Video-native models

- **Gemini (Google).** Native video input. Static mode samples frames at 1 FPS and injects a timestamp every second; the prompt refers to moments as MM:SS. Per-frame token budget is set by `media_resolution`: 70 tokens/frame default (low and medium are treated identically for video), 280 tokens/frame at `high`, documented as needed only for dense text or small details. Supports clipping via start/end offsets and a custom `fps` in `videoMetadata`. **Agentic mode** (`processing: "agentic"`, Flash-tier models) navigates the video with tools and uses up to ~88% fewer tokens on long content, at some time-to-first-token cost on short clips. Output is free text driven by the prompt; timestamped event lists and JSON are available on request. **Role in this design:** Stage 0 outline only.
- **TwelveLabs Pegasus 1.5.** Video-to-text with temporal grounding, up to 2-hour inputs, long structured responses; claims on-screen text analysis. Design center is real-world footage with audio; no evidence found on screen recordings. **Not used in v1;** cheap to test later.

### 5.2 Image-input models (used for per-frame perception)

- **OpenAI.** No native video input as of 2026-09 (docs' "Images and video" section covers image understanding, image generation, and video generation only). Image path: up to 1,500 images per request; `detail: "original"` recommended for OCR and small-object tasks; 32-px patches; a 30,000-patch rejection limit per image; token multiplier 1.2× on newer models.
- **Claude (Anthropic).** No native video input. Image path: 28×28-px patches, cost ⌈w/28⌉×⌈h/28⌉ visual tokens; up to 600 images per request on newer models (32 MB request cap); newer models accept up to 2576 px on the long edge before downscaling.
- **Gemini image input** at `media_resolution: high` is a third option (images get larger token budgets than video frames).
- **Qwen3.5 (open weights, Apache-2.0, 2B–397B MoE).** Local inference; no per-token cost, no rate limits, data stays local, fine-tunable. Requires GPU hardware (~24–48 GB VRAM for a ~30B-class model at 8/4-bit) and vLLM-style serving. Quality relative to frontier APIs on these frames is an empirical question for the harness.

Model ranking on small-text OCR, verbatim compliance, and GUI grounding changes every few months; **the design does not assume a winner** — the harness (§12) picks it. Public benchmarks worth consulting: OCRBench (text), ScreenSpot-Pro (GUI grounding).

### 5.3 Native-resolution check (why no tiling in v1)

| Recording | Claude visual tokens (28 px) | OpenAI patches ×1.2 (32 px) | Downscaled? |
|---|---|---|---|
| 1920×1080 | 69×39 = 2,691 | 60×34 = 2,040 → 2,448 tokens | No (both) |
| 2560×1440 | 92×52 = 4,784 | 80×45 = 3,600 → 4,320 tokens | No (both; 2560 < 2576 on newer Claude) |
| 3840×2160 | — | — | Yes on Claude (long edge > 2576); OpenAI within patch limit at `original` but treat as v2 |

### 5.4 OCR engines

- **Windows.Media.Ocr** (ships with Windows; WinRT, callable from .NET with a Windows TFM such as `net8.0-windows10.0.19041.0`). Offline library call on any `SoftwareBitmap` — unrelated to capture; the recording's origin is irrelevant. Returns `Lines[]`, each with `Text` and `Words[]` with `BoundingRect`; the line box is computed as the union of its word boxes. Requires an installed language pack. Has a maximum image dimension (`OcrEngine.MaxImageDimension`, ~2600 px **[verify]**). Middling on small monospace text.
- **PaddleOCR** (open source). Detects text lines directly as quadrilaterals; generally stronger on small text. Python-first; ONNX-runtime ports with .NET wrappers exist (PaddleOCRSharp, RapidOCR) **[verify current packaging]**.
- **Tesseract.** .NET bindings exist; weakest on anti-aliased UI text; needs upscaling and inversion of dark themes. Not planned.

### 5.5 Screen parsing and layout (v2 candidates)

- **OmniParser (Microsoft).** Detects interactable elements and icons from screenshots with a trained detector plus OCR and captioning; built to feed computer-use agents. Likely more accurate than VLM grouping for buttons/icons; tuned for interactable elements rather than text-pane hierarchy. Complement, not replacement.
- **ScreenAI (Google).** Defines a screen-annotation schema (element types, boxes, text). Reference for schema design.
- **OS accessibility tree (Windows UI Automation).** Exact window/pane/control hierarchy with text and rects — but only available live on the recording machine. Not applicable to existing videos; see §21.

### 5.6 Long-video research (context for Stage 7)

Long-video work is categorized into single-pass multimodal LLMs, memory-based approaches (compressed visual tokens or textual memory banks accumulated as frames stream), and agentic approaches (a model with tools retrieves segments iteratively — VideoAgent, DrVideo's document-style retrieval, VideoTree's query-conditioned frame hierarchy). The known tension — coarse memories are searchable but lose detail, fine memories preserve detail but are hard to navigate at hour scale — is resolved here by a multi-level tree over precomputed text (Stage 6) with pooled retrieval (Stage 7). This problem is strictly easier than the streaming setting because all passes are offline over complete files. **RAPTOR** (recursive abstractive tree + collapsed retrieval) is the closest named match for Stages 6–7 combined.

---

## 6. Stage 0 — Global outline (Gemini agentic)

**Runs in parallel with Stage 1. Read-only downstream.**

- **Input:** the whole video file (or YouTube URL). Agentic mode; `media_resolution` default (resolution is irrelevant here; only structure is wanted).
- **Prompt:** produce a chapter outline as JSON: `[{start_s, end_s, title, gist}]`, with 5–20 chapters, boundaries at changes of sub-goal, no attempt at exact text.
- **Output:** `outline.json`.
- **Consumers:**
  1. Stage 5 prompt preamble: "Global outline: …; this pair falls inside chapter *k*: *title*." Disambiguates local actions.
  2. Stage 6 section-boundary call receives the chapter boundaries as a *suggestion* to reconcile against transition evidence. Rule: frame evidence wins on conflict.
  3. Stage 7: each outline entry is indexed as a top-level document.
- **Never** writes into `frames.jsonl` or `transitions.jsonl`.

---

## 7. Stage 1 — Decode, change detection, settle, churn mask

### 7.1 Decode

Spawn ffmpeg and read raw grayscale frames from stdout at native frame rate:

```
ffmpeg -i in.mp4 -f rawvideo -pix_fmt gray -
```

Track presentation time per frame from the frame index and the stream's frame rate (or use `showinfo`/`pts_time` if reading via a decoder library). Optionally downsample by 2 for detection (thresholds scale by 4); emit frames must be written from a full-resolution decode (a second pass or a parallel `-pix_fmt rgb24` stream at emit time).

### 7.2 Change detection (per frame)

```
changed[p] = |luma_f[p] − luma_prev[p]| > θpix      for unmasked pixels p
changed    = open(changed, 3×3)                      // erode then dilate: kills isolated codec noise
comps      = connectedComponents(changed, 8-conn)    // e.g. OpenCvSharp ConnectedComponentsWithStats
trigger    = any(comp.area ≥ θcomp)                  // one small solid change (a 16×16 checkbox)
          or Σ(comp.area for comp.area ≥ 16) ≥ θcount   // several medium changes
```

Rationale: an **absolute** pixel count is used, never a fraction. A 1080p frame is 2,073,600 px; a 16×16 checkbox is 256 px = 0.012%, which any fraction threshold would miss, while a blinking caret is ~36 px and must not trigger. The **connected-component** test distinguishes contiguous UI change from scattered compression noise.

### 7.3 Settle

```
emit(f0, tChange=t0, tSettled=t0, settled=true); prev=last=f0
changed=false; tChange=∅; tStill=t0
for each frame f at time t:
  if trigger(f, prev):                     // moving
     if !changed { changed=true; tChange=t }
     tStill = t
  else if changed and t − tStill ≥ S:      // was moving, now still for S
     if trigger(f, last): emit(f, tChange, tSettled=t, settled=true); last=f
     changed=false                         // else: something flashed and reverted — nothing to emit
  if changed and t − tChange ≥ M:          // never settled: max-hold
     emit(f, tChange, tSettled=t, settled=false); last=f; tChange=t
  prev=f
```

- Comparison against `prev` measures stillness; comparison against `last` (last emitted) measures novelty. A menu that opens and closes within S emits nothing.
- Each emitted frame records `t_change` (when the previous state ended) and `t_settled` (when this state was fully on screen). The state's stable interval is `[t_settled_i, t_change_i+1)`; the gap `[t_change_i+1, t_settled_i+1)` is "in transition." The last frame's `t_end` is the video end.
- Sub-threshold changes (caret blink, clock) do not reset the settle timer; that is what makes settling possible.
- A typing pause longer than S splits one command into two emitted frames. This is not a failure; coalescing (Stage 4b) rejoins them.

### 7.4 Churn mask

Purpose: a region that never stops changing (spinner, progress bar, embedded playing video, continuously scrolling log) would otherwise prevent the screen from ever settling.

```
ring buffer of the last W change maps (W ≈ 5 s of frames)
count[p]  = number of maps in the window with changed[p] set
raw       = count > ρ_on·W                      // pixels changing in >50% of recent frames
raw       = open(raw, 3×3); raw = dilate(raw, 9×9)
churn     = connected components of raw with area ≥ 400 px → list of bboxes
hysteresis: a component enters the mask at ρ_on = 0.5 and leaves at ρ_off = 0.2
```

- Masked pixels are excluded **only** from change detection (§7.2). Nothing else in the pipeline is masked.
- Every emitted frame records `churn_regions` (active churn bboxes). Downstream: OCR lines inside churn are tagged `in_churn=true` (low confidence); the Stage 2 VLM prompt lists them as "animating"; Stage 5 is told the region was changing continuously.
- Memory: 1080p × 150 maps × 1 bit ≈ 39 MB; halve by detecting at half resolution.
- Churn cannot distinguish a spinner from a continuously scrolling log; both are churn. Max-hold M still emits frames periodically, so nothing stalls, and Stage 5 sees "output was scrolling continuously."

### 7.5 Caret tracking (for focus confidence, §9.4)

From the same change maps: track components ≤ 3×30 px that toggle with a period of 0.3–1.2 s. Their bounding box is the caret position for the current state. Stored per emitted frame as `caret: [x,y,w,h] | null`.

### 7.6 Outputs

- `frames/NNNNN.png` — full-resolution emitted frames (content-addressed by SHA-256 as well, for idempotency).
- Per-frame metadata: `frame`, `t_change`, `t_settled`, `t_end`, `settled`, `churn_regions`, `caret`, `width`, `height`, `sha256`.

### 7.7 What Stage 1 can and cannot lose

- **False positives** (spurious emitted frames) cost tokens only.
- **False negatives** (a change below threshold) do not vanish: the change is still present at the next emitted frame and appears in that transition, with coarser timing and possibly bundled with another change.
- **True loss** is only a sub-threshold change that reverts before the next emission — rare and low value.
- **Recovery tool:** the video is kept; every record carries a time range; any downstream stage may request a re-decode of `[t_a, t_b]` at full rate to look again. This is exposed as a callable tool (`redecode(video_id, t_a, t_b, fps)`), not a manual step.

---

## 8. Stage 2 — Per-frame perception

One OCR run and one VLM call per emitted frame. Both consume the same PNG.

### 8.1 Stage 2a — OCR

- Input: `frames/NNNNN.png` (full resolution; if the engine has a dimension cap below the frame size, run at the cap and scale boxes back — see coordinate convention §10.5; for v1 1080p/1440p this does not arise with Windows.Media.Ocr **[verify cap]**).
- Output per frame: `lines[] = {id, bbox:[x0,y0,x1,y1], text, conf, words[]}` in **original-frame pixel coordinates**.
- Line construction: engines return a hierarchy. Windows.Media.Ocr returns lines with words; the line box is the union of the word boxes. PaddleOCR returns line quadrilaterals; take their axis-aligned bounding box. If only words are available, group them:

```
sort words by y-center
a word joins the current line if |yc(word) − yc(line)| < 0.5 · median(word height)
within each line sort by x; line.text = join(words, " "); line.bbox = union(word boxes)
```

- Line IDs are stable within a frame (`l1…lN`, assigned in reading order: sorted by y0 then x0).
- Lines whose bbox intersects a churn region are tagged `in_churn=true`.

### 8.2 Stage 2b — Set-of-mark overlay

Draw each OCR line's bbox on a copy of the frame as a thin colored rectangle with its numeric ID in a small legible font placed outside the box (top-left, offset), avoiding occlusion of the text. Save as `overlays/NNNNN.png`. This is what the VLM sees; the VLM never sees raw coordinates and never emits them.

### 8.3 Stage 2c — VLM grouping and transcription call

- Input: the overlay PNG, sent at native resolution (`detail: "original"` on OpenAI; default on Claude; `media_resolution: high` on Gemini).
- Contract (full prompt text in §15.1): group the numbered lines into a region tree (windows → panes → popups), name each region and its application, identify the focused window with a confidence and the cues used, and for each leaf region transcribe its visible text verbatim in reading order — including any text that has no number (OCR missed it). Free-text `description` field for anything a line list cannot express (diagram relationships, highlighted rows, selected items, icons).
- Output schema (structured output):

```json
{
  "regions": [
    {"id":"r1","kind":"window|pane|popup","name":"Windows Terminal — pwsh","app":"Windows Terminal",
     "parent":null,"member_line_ids":["l3","l4"],"conf":0.95,"occludes":[],
     "vlm_lines":["git status","On branch main"]}
  ],
  "focused_region":"r1","focused_conf":0.8,"focused_cues":["title bar highlight","caret visible"],
  "description":"…",
  "unassigned_line_ids":[]
}
```

- Rules enforced by prompt and validated by code: every OCR line ID appears in exactly one region's `member_line_ids` or in `unassigned_line_ids`; `vlm_lines` are verbatim with `?` for unresolvable characters; no normalization of code; whitespace preserved.

### 8.4 Model choice

Any of the §5.2 models. Choose by the harness: transcribe the 20-frame calibration set, hand-check, compute CER on commands, compare cost per frame. The design assumes only that the model accepts images at native resolution and supports structured output.

---

## 9. Stage 3 — Merge

Produces the canonical per-frame state record (`frames.jsonl`, §10.1). Nothing downstream touches raw OCR or raw VLM output again.

### 9.1 Region geometry

For each region: `bbox = [min x0, min y0, max x1, max y1]` over its member lines (recursively including child regions). This is the **text extent**, not the window frame: chrome and empty areas are excluded. Adequate for containment and metadata; if a true window rect is ever needed (v2 cropping) it is obtained separately.

### 9.2 Line alignment and agreement

Per leaf region, align `vlm_lines` (reading order) with member OCR lines (sorted by y0 then x0) using LCS with a match predicate `similarity(a, b) ≥ 0.8` (normalized Levenshtein ratio after whitespace normalization).

| Case | Record |
|---|---|
| matched | `ocr`, `vlm`, `ocr_conf`, `agree = (norm(ocr) == norm(vlm))` |
| OCR-only | `vlm = null` |
| VLM-only (no mark; OCR missed it) | `ocr = null`, `ocr_conf = null`, `bbox = null` (or the region bbox as a coarse fallback, flagged) |

`norm()` trims, collapses internal whitespace, and unifies quote glyphs (`“”` → `"`, `‘’` → `'`). Case is preserved.

**Fusion does not depend on the region tree.** Agreement is computed per line keyed by OCR line ID; the region is metadata attached afterward. A mis-grouped line still has the correct text, box, and `agree` flag.

### 9.3 `layout_conf`

A per-region heuristic quality score in [0,1], not a probability.

```
score = region.conf (VLM self-report)
for each member line whose center lies inside another region's bbox
    that is neither ancestor nor descendant: score −= 0.3   (total penalty capped at 0.6)
if (Σ member line areas) / area(bbox) < 0.3: score −= 0.2        // scattered membership
if member count == 1: score = min(score, 0.6)
clamp to [0,1]
```

Consumers: (1) Stage 5 prompt lists regions with `layout_conf < 0.5` as "grouping uncertain; text may belong to an adjacent window"; (2) Stage 7 uses region/app names from such frames only as soft boosts, never as hard filters; (3) development: sample low-score frames for inspection; (4) optional reprocessing: re-run §8.3 with a second model or prompt for frames below threshold and keep the higher-scoring result. v1 implements (1) and (3).

### 9.4 Focus confidence

Three signals, two computable:

1. **Caret** (§7.5): the region containing the caret bbox is focused. High confidence when present.
2. **Retrospective**: if the next transition's coalesced `typed` event lands in region R, R was focused at this frame. Exact, but computed after Stage 4b; written back into the frame record.
3. **VLM self-report** (§8.3) with its own 0–1 estimate and cues.

Combination: caret or retrospective agrees with VLM → 0.9; only VLM available → 0.5; VLM disagrees with a computed signal → use the computed signal and record 0.3 for the VLM's answer. Store `focused_signals` listing contributors. Downstream logic must not depend hard on focus.

---

## 10. Data model

All files are JSON Lines (one object per line) except `outline.json` and `video.json`. All coordinates follow §10.5. All IDs follow §10.6.

### 10.1 `frames.jsonl` — levels (states)

```json
{
  "video_id": "v-0001",
  "frame": 12,
  "t_change": 47.30,
  "t_settled": 47.72,
  "t_end": 52.10,
  "settled": true,
  "png": "frames/00012.png",
  "overlay": "overlays/00012.png",
  "sha256": "…",
  "width": 1920, "height": 1080,
  "churn_regions": [[1700, 40, 1760, 100]],
  "caret": [318, 41, 2, 18],
  "focused_region": "r1",
  "focused_conf": 0.9,
  "focused_signals": ["caret", "vlm"],
  "description": "Terminal in the foreground; browser behind it shows a portal blade with a selected row.",
  "regions": [
    {
      "id": "r1", "kind": "window", "name": "Windows Terminal — pwsh", "app": "Windows Terminal",
      "parent": null, "bbox": [12, 40, 640, 300], "conf": 0.95, "layout_conf": 0.9, "occludes": ["r2"],
      "lines": [
        {"id": "l3", "bbox": [12, 40, 300, 58], "ocr": "git status", "ocr_conf": 0.97,
         "vlm": "git status", "agree": true, "in_churn": false},
        {"id": "l4", "bbox": [12, 60, 540, 78], "ocr": "On branch maln", "ocr_conf": 0.81,
         "vlm": "On branch main", "agree": false, "in_churn": false}
      ]
    },
    {
      "id": "r2", "kind": "window", "name": "Azure Portal — Storage accounts", "app": "Browser",
      "parent": null, "bbox": [0, 0, 1920, 1080], "conf": 0.9, "layout_conf": 0.7, "occludes": [],
      "lines": []
    },
    {
      "id": "r3", "kind": "pane", "name": "left navigation", "app": "Browser",
      "parent": "r2", "bbox": [0, 120, 260, 1000], "conf": 0.85, "layout_conf": 0.8, "occludes": [],
      "lines": [ {"id": "l15", "…": "…"} ]
    }
  ],
  "unassigned_lines": [],
  "outline_chapter": "c3"
}
```

Field notes:
- `t_end` is the next frame's `t_change`; `null` for the last frame is replaced by the video duration.
- `regions` is a flat list with `parent` links; `bbox` of a parent encloses its children by construction (§9.1).
- `lines` appear only on leaf regions.
- `outline_chapter` is a join to `outline.json` by time, filled after Stage 0 completes.

### 10.2 `transitions.jsonl` — edges

```json
{
  "id": "T017",
  "from_frame": 12,
  "to_frame": 16,
  "intermediate_frames": [13, 14, 15],
  "kind": "coalesced",
  "computed_diff": {
    "r1": {
      "ops": [
        {"op": "modify", "old": "PS C:\\src> gi", "new": "PS C:\\src> git status",
         "char_diff": "+t status", "y": 41},
        {"op": "insert", "index": 4, "text": "On branch main"},
        {"op": "insert", "index": 5, "text": "nothing to commit, working tree clean"}
      ]
    }
  },
  "events": [
    {"type": "typed", "region": "r1", "text": "git status", "frames": [12, 16]},
    {"type": "output_appended", "region": "r1", "lines": 2, "frames": [16, 16]}
  ],
  "transient": null,
  "context": {"outline_chapter": "c3"},
  "vlm": {
    "action": "User typed `git status` in the terminal and pressed Enter.",
    "result": "Git reported branch main with a clean working tree.",
    "description": "…",
    "confidence": 0.9,
    "refs": {"lines": ["r1:l3", "r1:l4"]}
  }
}
```

`kind ∈ {single, coalesced, transient_merged, unsettled}`. For `transient_merged`, `transient = {"frame": 14, "region": "r5", "name": "toast", "hold_s": 1.2}`.

### 10.3 `steps.jsonl`, `sections.jsonl`, `video.json`

```json
{"id": "S04", "level": "step", "children": ["T012", "T031"], "frames": [10, 44], "t": [38.1, 191.4],
 "label": "Configure the storage account", "description": "…", "refs": ["T013", "T015", "T020"]}
```

- `children` is an inclusive ID range over the level below (transitions for steps, steps for sections).
- `frames` = `[first child's from_frame, last child's to_frame]`; `t` = corresponding `[t_settled, t_change]`.
- `refs` lists the child IDs each sentence in `description` rests on; the prompt requires inline references (`[T013]`) and code validates that every referenced ID is within `children`.
- `video.json` has the same shape with `level: "video"` and `children` spanning all sections.

### 10.4 `outline.json`

```json
[{"id": "c1", "start_s": 0.0, "end_s": 312.0, "title": "Create the resource group", "gist": "…"}]
```

### 10.5 Coordinate convention

All stored boxes are `[x0, y0, x1, y1]` in **original-frame pixels** (the recording's native grid), integers, origin top-left. Any tool that saw a transformed image (an OCR engine with a dimension cap, a provider that resizes) has its boxes scaled back before storage. Normalized (0–1) coordinates are not stored.

### 10.6 ID conventions

- Frames: integer, monotonically increasing per video, zero-padded to 5 digits in filenames.
- Lines: `l<n>` unique within a frame, assigned in reading order.
- Regions: `r<n>` unique within a frame. Regions are **not** tracked across frames in v1 (a window's `r` ID may differ between frames); cross-frame identity is by `name`+`app`+approximate `bbox` when Stage 4 needs it.
- Transitions `T<nnn>`, steps `S<nn>`, sections `C<nn>`, outline chapters `c<n>`; all unique per video.
- Cross-file references use `"<frame>:<line>"` or plain IDs as shown.

---

## 11. Stage 4 — Line diff; Stage 4b — Coalescing and transients

### 11.1 Region correspondence across frames

Before diffing, match leaf regions between frame *i* and frame *i+1*: same `app` and `name` (normalized), and bbox IoU ≥ 0.3, or the same `name` with any overlap. Unmatched regions are "appeared" / "disappeared" events. Correspondence is recorded on the transition.

### 11.2 Line-level diff (per matched region)

```
prev = [norm(line.text) for line in region_i.lines   sorted by (y0, x0)]
cur  = [norm(line.text) for line in region_i+1.lines sorted by (y0, x0)]
ops  = myers_diff(prev, cur)                       // insert / delete / equal runs (DiffPlex in .NET)
post-process adjacent (delete a, insert b):
    pair as modify(a → b) if boxes overlap vertically (|yc(a) − yc(b)| < 0.5·h)   // preferred signal
                          or similarity(a, b) ≥ 0.6
    for each modify, also compute a character-level diff within the line (char_diff)
```

- The text used for diffing is the **fused** line text: `ocr` where `agree=true`, otherwise `vlm` if `ocr` is null, otherwise `ocr` with the line flagged `uncertain` in the op.
- Raw `delete/insert` ops are always stored; `modify` is a derived annotation. A mis-pairing therefore loses nothing — both readings remain — it only affects readability. Y-overlap is the stronger pairing signal on screens because a modified line stays put.
- **Why line-level:** the diff turns "the screen changed" into a short, exact op list a model would get wrong by eyeballing two dense screenshots, and a line is the natural unit of everything of interest (command, log line, list item, menu entry) and of OCR output. Character-level diff over a whole region yields "inserted `tus` at offset 87" — exact but meaningless to humans and models; it is used only *inside* a modified line.
- **Scrolling** is handled for free: shifted-but-identical lines align as `equal`; only genuinely new bottom lines are `insert`.

### 11.3 Coalescing **[reasoned]**

Input: the sequence of consecutive single transitions `(i → i+1)` with their computed diffs. Output: a sequence of coalesced transitions, each covering `[first, last]`, with `events`.

- **Rule 1 — typed:** a maximal run of consecutive transitions where each has exactly one op, in the same region, of the form `modify(a → b)` with `a` a prefix of `b` after normalization (or an `insert` of a line that extends the previous transition's inserted line). Replace with one transition `[first, last]` and event `typed(text = b_final, region, frames)`.
- **Rule 2 — output_appended:** a maximal run of consecutive transitions where each op is an `insert` at the bottom of the same region. Replace with one transition and event `output_appended(lines = n, text = concatenation, region, frames)`.
- **Rule 3 (expected, not yet specified):** editor edits where the change is in the middle of a line, not a suffix. To be added after ground-truth review.
- **Provenance:** the idea (aggregating keystrokes into a single "type" action; merging adjacent diff hunks) is prior art in GUI-agent datasets, RPA tooling, and diff tools; these specific rules were derived from how line diffs behave on terminals and must be validated (§12).
- **Effect on Stage 5:** coalescing decides which frame pairs Stage 5 examines. A typed command becomes one Stage 5 call on `(frame before typing, settled frame after)` with the typed string attached, instead of one call per keystroke pause. Settle already collapses most typing; coalescing catches pauses longer than S and incremental output.

### 11.4 Transients **[reasoned]**

For frames `i−1, i, i+1`: if every matched region's fused text is equal between `i−1` and `i+1`, and frame `i` contains a region (by §11.1 matching) absent from both neighbors, and `t_change_i+1 − t_settled_i < T_transient`, then frame `i` is a transient.

- Frame `i` stays in `frames.jsonl`.
- Instead of two Stage 5 calls (`i−1 → i` "toast appeared", `i → i+1` "toast disappeared"), one call is made for `i−1 → i+1` with frame `i` attached as a third image and the note "this region appeared for *h* seconds between them." Result: one edge such as "user pressed Ctrl+S; a 'Saved' toast confirmed it."
- Transients with no text (spinner overlays) are handled by churn (§7.4), not here.

### 11.5 Unsettled frames

Transitions into or out of a frame with `settled=false` are `kind: "unsettled"`; Stage 5 is told the region was changing continuously and OCR inside churn is low confidence.

---

## 12. Stage 5 — Transition interpretation (VLM)

One call per (coalesced) transition.

- **Inputs, in order, as content blocks:**
  1. Text: outline preamble (§6) and the running context (label of the current step if Stage 6 has run in a previous iteration; otherwise the last three transitions' `action` fields).
  2. Text: `Frame <a>, t=<t_settled_a>`; Image: `frames/<a>.png`.
  3. (If transient) Text: note; Image: transient frame.
  4. Text: `Frame <b>, t=<t_settled_b>`; Image: `frames/<b>.png`.
  5. Text: the computed diff and coalesced events rendered compactly (region name, ops, `uncertain` flags, `agree=false` lines shown with both readings, churn notes, `layout_conf < 0.5` regions listed as uncertain grouping).
  6. Text: the task instruction (§15.2 prompt contract).
- **Output schema:** `{action, result, description, confidence, refs:{lines:[…]}}`. `action` is inference (what the user did); `result` is observation (what changed as a consequence); `description` is free prose for anything else visible. Rules: cite line IDs; do not restate diff text with alterations; when readings disagree, quote both and do not assert either.
- Images are sent at native resolution. Both frames are sent even when the computed diff is small, because non-textual changes (checkbox, highlight, selection, dialog) are only visible in pixels.

---

## 13. Stage 6 — Hierarchy (semantic segmentation)

Levels: transitions → steps → sections → video. Each level is produced by the **two-pass pattern** over the level below, text-only, carrying frame ranges forward.

### 13.1 Boundary call (pass 1)

- Input: the ordered list of level-*n* items, each rendered as one line, e.g. `T017 [f12→f16] Windows Terminal: typed "git status"; 2 lines appended` (steps rendered as `S04 [f10→f44] Configure the storage account`). For sections, the Stage 0 chapter boundaries are appended as a suggestion.
- Instruction: output boundary indices where a new sub-goal (steps) or topic (sections) begins, with a short label per segment. Output: `[{start_id, end_id, label}]`.
- Validation in code: contiguous, non-overlapping, covering the whole list. On failure, re-prompt once with the violation named; on second failure, fall back to Stage 0 chapter boundaries (sections) or fixed windows of 20 (steps) and flag the level `segmentation_conf: low`.
- Lists too long for one call: run the boundary call over overlapping windows (e.g., 400 items, 50 overlap) and merge boundaries, preferring boundaries found in both overlapping windows.

### 13.2 Elaboration call (pass 2)

- Per segment: input is the child items in full (their `action`/`result`/`events` for transitions; `label`/`description` for steps), plus the merged states at the segment's first and last frames (region names and focused window only, not full line lists).
- Output: `{label, description, refs}` with inline child references. Validate every referenced ID ∈ `children`.
- If a single segment's children exceed the call budget, apply **map-reduce within the segment**: chunk children by token count; summarize each chunk (map, parallel); summarize the chunk summaries (reduce); recurse if the concatenation still doesn't fit. Boundary effects (an event straddling a chunk) are accepted at this level because segments are already semantically coherent. The **refine** pattern is not used (early errors persist; drift).

### 13.3 Frame-range propagation (R3)

`frames` and `t` are computed by code from children, never by the model. Because every sentence carries child references and every child carries its own range, any sentence at any level can be walked down to specific frames and PNGs.

---

## 14. Stage 7 — Index and retrieval

### 14.1 Nodes

Every node from every level is a retrieval document: frame states (one document per leaf region, plus one per frame `description`), transitions, steps, sections, the video summary, and Stage 0 outline entries. Each document carries metadata: `video_id`, `level`, `id`, `frames`, `t`, `apps`, `region_names`, `layout_conf` (min over involved regions), `step_id`, `section_id`, `chapter_id`.

### 14.2 Indexes

- **Lexical** (BM25 or SQLite FTS5): exact strings — commands, identifiers, resource names. This is the reason R1 matters at query time.
- **Vector** (embeddings): semantic questions ("where did they set up authentication").
- **Collapsed-tree retrieval:** both indexes hold all levels in one pool; a query retrieves top-k across levels with reciprocal-rank fusion of lexical and vector results, filtered by metadata where the question specifies (video, app, time range). Region/app names from `layout_conf < 0.5` frames are soft boosts only.

### 14.3 Answering agent

Tools: `search(query, filters)`, `get_node(id)`, `get_transitions(video_id, t_a, t_b)`, `get_frame(video_id, frame)` (returns the PNG as an image), `redecode(video_id, t_a, t_b, fps)` (Stage 1 recovery tool, §7.7). The agent iterates search → read → (optionally) look at frames → answer, and must cite frame IDs and times for every factual claim. Exact-text answers are quoted from `agree=true` lines; where `agree=false`, both readings are shown.

This is the same navigate-with-tools pattern as Gemini's agentic mode, applied at the layer where the data is high-resolution and pre-indexed, so per-question cost is text retrieval plus at most a few frame images rather than re-watching video.

---

## 15. Prompt contracts

Prompts are contracts: a system prompt defining each output field, a JSON schema with per-field descriptions, and one worked example. Model behavior depends on these definitions, not on field names.

### 15.1 Stage 2c — grouping and transcription

Core instructions (paraphrased contract; exact wording lives in the repo):

1. The image is a screenshot with numbered boxes drawn around detected text lines. Group every numbered line into a tree of regions: windows, panes within windows, and popups. Name each region and identify its application. Every number must appear in exactly one region or in `unassigned_line_ids`.
2. Identify the focused window; give a 0–1 confidence and list the visual cues used.
3. For each leaf region, transcribe its visible text **verbatim**, in reading order, one entry per line, including text that has no number. Preserve case, punctuation, whitespace, and symbols. Never correct, complete, or normalize commands, code, paths, or identifiers. Use `?` for any character you cannot resolve. Do not omit lines.
4. In `description`, state anything the line list cannot express: selections, highlights, toggles, icons, diagram relationships, dialogs.
5. Regions listed as animating (churn) are low confidence; say so rather than guessing.

### 15.2 Stage 5 — transition interpretation

1. You are shown two consecutive screen states (and optionally a transient state between them) and an exact computed list of text changes. The computed list is authoritative for text; do not restate its strings with alterations.
2. `action`: the single user action that best explains the change (typed, clicked, selected, navigated, pressed a key). If none is evident, say so.
3. `result`: what visibly changed as a consequence, including non-textual changes visible in the images.
4. Where two readings of a line disagree, quote both; assert neither.
5. Reference the line IDs your statements rest on.

### 15.3 Stage 6 — boundary and elaboration

Boundary: "Output only boundaries where a new sub-goal begins. A sub-goal is a coherent unit of work a tutorial reader would follow as one step." Elaboration: "Describe this segment for a reader who will follow it. Every sentence must carry the IDs it rests on in brackets. Quote commands exactly as given; do not paraphrase them."

### 15.4 Stage 7 — answering

"Answer only from retrieved material. Cite frame IDs and times for every claim. Quote exact text only from lines marked agree=true; otherwise present both readings. If the material does not answer the question, say so and suggest which time range to inspect."

---

## 16. Parameters

All are initial values to be tuned on the ground-truth set (§17). Detection thresholds assume full-resolution 1080p; scale pixel counts by 4 for 1440p and divide by 4 when detecting at half resolution.

| Parameter | Value | Where | Meaning |
|---|---|---|---|
| `θpix` | 12 | §7.2 | Luma delta for a pixel to count as changed (ignores codec noise) |
| `θcomp` | 64 px | §7.2 | One connected component of at least this area triggers a change |
| `θcount` | 150 px | §7.2 | Total area of components ≥ 16 px that triggers a change |
| `S` | 400 ms | §7.3 | Stillness required before emitting |
| `M` | 3 s | §7.3 | Max hold: emit even if never still |
| `W` | 5 s | §7.4 | Churn window |
| `ρ_on / ρ_off` | 0.5 / 0.2 | §7.4 | Churn hysteresis (fraction of window frames a pixel changed) |
| churn min area | 400 px | §7.4 | Minimum component area to become a churn region |
| caret size / period | ≤ 3×30 px; 0.3–1.2 s | §7.5 | Caret detection |
| line grouping | 0.5 × median word height | §8.1 | Vertical tolerance for words joining a line |
| align similarity | ≥ 0.8 | §9.2 | OCR↔VLM line alignment predicate |
| modify similarity | ≥ 0.6 | §11.2 | Delete+insert pairing (or y-overlap) |
| region IoU | ≥ 0.3 | §11.1 | Cross-frame region matching |
| `T_transient` | 2 s | §11.4 | Max hold for a transient |
| `layout_conf` penalties | −0.3/line (cap 0.6), −0.2 scatter, cap 0.6 singleton | §9.3 | |
| focus combination | 0.9 / 0.5 / 0.3 | §9.4 | |
| boundary window | 400 items, 50 overlap | §13.1 | Long-list segmentation |
| fixed-window fallback | 20 transitions | §13.1 | Only after two failed boundary calls |
| retrieval k | 20 per index before fusion | §14.2 | |

---

## 17. Failure modes and mitigations

| Failure | Where | Consequence | Mitigation / recovery |
|---|---|---|---|
| Missed change below threshold | §7.2 | Change appears at next emitted frame, bundled and with coarser timing | Absolute pixel count + connected-component test; `redecode` tool; measure detection recall on ground truth |
| Spurious emitted frames (noise, caret above threshold) | §7.2 | Token cost only | Morphological opening; caret exclusion; tune `θpix` on recorded codec |
| Screen never settles (spinner, playing video, scrolling log) | §7.3 | Frames delayed; mid-animation frames | Churn mask; max-hold `M` with `settled=false` tagging; downstream told region was animating |
| Typing pause splits a command | §7.3 | Two frames for one command | Coalescing Rule 1 |
| OCR garbles small monospace text | §8.1 | Wrong characters | Engine bake-off; VLM cross-check; `agree` flag; vote across frames where the string persists |
| VLM paraphrases or "corrects" code | §8.3 | Plausible-but-wrong text | Verbatim contract; `?` convention; OCR cross-check; treat `agree=false` as uncertain |
| VLM omits lines | §8.3 | Missing text | OCR-only lines retained with `vlm=null` |
| OCR misses lines (no mark) | §8.1 | No box; grouping by VLM only | VLM-only lines retained with `ocr=null`; flagged coarse bbox |
| Wrong grouping (line assigned to wrong window) | §8.3 | Wrong region label | Fusion is independent of grouping; `layout_conf`; `unassigned` fallback; sample low scores |
| Overlapping/occluding windows | §8.3 | Membership ambiguity near edges; background window's union bbox encloses foreground | `occludes` relationships; boxes used for filtering only, never for assignment; include an overlapping-window video in ground truth |
| Text on canvases / diagrams | §8.3 | Line list loses spatial relations | `description` field; v2 screen parsing |
| Model-emitted coordinates | — | Approximate / wrong coordinate space | Not used (D4) |
| Provider downscales image | §5.3 | Small text lost | Native-resolution check per model; 4K excluded in v1 |
| Mis-paired modify | §11.2 | Readability only | Raw ops always stored |
| Coalescing rule over- or under-merges | §11.3 | Wrong event granularity | Rules are validated; Rule 3 pending; Stage 5 sees frames either way |
| Transient misclassified | §11.4 | Extra or merged edge | Frame retained; only Stage 5 call structure changes |
| Boundary call returns invalid segmentation | §13.1 | Bad steps/sections | Validation; re-prompt; fallback with `segmentation_conf: low` |
| Long-context quality degradation | §13.2 | Vague summaries | Map-reduce within segment; keep calls small |
| Stage 0 outline conflicts with frame evidence | §6 | Wrong global context | Frame evidence wins by rule; outline is read-only |
| Focus inferred wrongly | §9.4 | Wrong "focused" label | Computed signals preferred; downstream must not depend hard on focus |
| Model regression after provider update | all VLM stages | Silent quality drop | Harness re-run on calibration set per model change; pin model versions |

---

## 18. Evaluation plan

### 18.1 Ground-truth set

- **Two full videos** (30–60 min each), chosen to include: terminal work, an editor, a browser portal with a left navigation and content blade, Notepad, at least one dialog, and **one segment with overlapping windows**.
- **Hand-transcribed commands** and other exact strings (every command run, every value typed into a field), with the time they were entered.
- **Hand-written step list** with boundaries (time) and labels.
- **A 20-frame calibration subset** with fully hand-transcribed screen text per region, used for model and OCR bake-offs.
- **A question set** (20–40 questions) with reference answers and the frame ranges that justify them.

### 18.2 Metrics, per component (R5)

| Component | Metric |
|---|---|
| Stage 1 detection | Recall and precision of emitted frames against a hand-marked list of state changes; timing error (ms) of `t_change` |
| Stage 1 settle | Fraction of emitted frames that are end states (not mid-animation) |
| OCR alone | CER on commands; line recall |
| VLM transcription alone | CER on commands; line recall; paraphrase rate (normalized-equal but not exact) |
| Fused (`agree=true` lines) | CER; coverage (fraction of ground-truth strings with an `agree=true` line) |
| Grouping | Fraction of lines assigned to the correct window/pane; `layout_conf` correlation with errors |
| Focus | Accuracy vs hand labels, split by signal source |
| Coalescing | Event precision/recall against hand-marked actions |
| Stage 5 | Human-rated action/result correctness on a sample; citation validity (refs exist and support the claim) |
| Stage 6 steps | Boundary agreement with the hand step list (WindowDiff or F1 with ±1 transition tolerance); label adequacy (human) |
| Stage 6 with vs without Stage 0 | Boundary agreement delta |
| Stage 7 | Answer accuracy on the question set; citation correctness; exact-string accuracy for command questions |

### 18.3 Bake-offs

1. OCR engines: Windows.Media.Ocr vs PaddleOCR on the 20-frame set.
2. VLMs: at least two of Claude / OpenAI / Gemini-image / Qwen3.5-local on the 20-frame set (transcription CER, grouping accuracy, cost per frame, latency).
3. Ensemble ablations: each switchable stage off, one at a time, against the full pipeline.

---

## 19. Cost and performance model

### 19.1 Unique-frame estimate

A 30-minute tutorial with typical activity yields on the order of 100–400 emitted frames after settle. This is the number that drives all per-frame costs; measure it on the ground-truth videos first.

### 19.2 Per-frame perception

- Visual tokens per frame (§5.3): ~2,700 (1080p) or ~4,800 (1440p) on Claude; ~2,450 / ~4,320 on OpenAI at `original`. Plus prompt and output text (~1–3k tokens).
- OCR: local, milliseconds to low seconds per frame.
- One VLM call per frame; parallelizable up to provider rate limits.

### 19.3 Transitions

Roughly one Stage 5 call per coalesced transition, ≤ number of emitted frames; each sends two (occasionally three) frames, so ~2× per-frame image cost plus text.

### 19.4 Hierarchy and index

Text-only; a few dozen calls per video (one boundary call per level, one elaboration call per segment, map-reduce only for oversized segments). Negligible relative to Stages 2 and 5.

### 19.5 Alternatives considered for batching

- **Single-call whole video** (all emitted frames in one request): ~300 frames × ~2.5k ≈ 750k tokens; fits 1M-context models but is expensive per call and multimodal quality degrades at very long contexts. Rejected for v1; the pairwise design has no batching problem because no call is long.
- **Batches with overlap and carry-forward summary:** the general fallback if any stage ever needs multi-frame context beyond a pair — overlap by one or two frames so a boundary-straddling transition is visible to both batches, and include the previous batch's output as text so later batches know the context. Not needed in v1.

### 19.6 Local inference option

If per-frame API cost dominates at corpus scale, Qwen3.5 (or a successor) on a local GPU removes the per-token cost for Stage 2c/5; the harness decides whether quality is acceptable.

---

## 20. Implementation notes (.NET)

- **Decode:** spawn `ffmpeg -i in.mp4 -f rawvideo -pix_fmt gray -` and read fixed-size frames from stdout; keep a parallel or second-pass full-color decode for emitted frames. Alternatively FFmpeg.AutoGen for in-process decoding with exact PTS.
- **Change detection / churn / connected components:** OpenCvSharp (`Cv2.Absdiff`, `Cv2.Threshold`, `Cv2.MorphologyEx`, `Cv2.ConnectedComponentsWithStats`). Detect at half resolution if CPU-bound.
- **OCR:** `Windows.Media.Ocr` via a Windows TFM (`net8.0-windows10.0.19041.0` or later); `BitmapDecoder` → `SoftwareBitmap` → `OcrEngine.TryCreateFromUserProfileLanguages()` → `RecognizeAsync`. Check `OcrEngine.MaxImageDimension` and scale if needed. PaddleOCR via PaddleOCRSharp/RapidOCR (ONNX Runtime) as the comparison engine **[verify packaging]**.
- **Overlay drawing:** System.Drawing or SkiaSharp; thin 1–2 px rectangles, IDs in a 10–12 px font placed outside the box.
- **Diff:** DiffPlex for Myers line diff; a small Levenshtein implementation for similarity and char-level diff.
- **Model calls:** provider SDKs with structured-output/JSON-schema mode; images as base64 PNG content blocks preceded by a text block carrying frame ID and time (models never see filenames or metadata). Pin model versions. Cache every call by `(stage, model version, prompt hash, input hash)`.
- **Idempotency (R6):** frames content-addressed by SHA-256; each stage writes its own JSONL and is skippable when its inputs and configuration hash are unchanged.
- **Concurrency:** Stage 2 and Stage 5 are embarrassingly parallel per frame/pair; bound by provider rate limits. Stage 6 is sequential per level.
- **Index:** SQLite FTS5 for lexical; any local vector store (or SQLite with a vector extension) for embeddings; reciprocal-rank fusion in code.
- **Config:** every parameter in §16 in one config file, recorded into each run's manifest.

---

## 21. v2 roadmap

1. **Record-time capture (highest value where possible).** If future recordings can be influenced, capture the Windows UI Automation tree (exact window/pane/control hierarchy with text and rects) and input events (keystrokes, clicks with coordinates) alongside the video. This replaces Stages 2–4 for those videos with exact data and reduces the vision pipeline to verification.
2. **4K support:** crop-by-region using region text extents (padded) from Stage 3, or the true window rect if captured; never grid tiling.
3. **Screen parsing:** OmniParser for interactable elements and icons; ScreenAI's annotation schema as a reference for extending the region model.
4. **Cross-video retrieval:** RAPTOR-style similarity clustering over steps across the whole corpus ("every step that configures storage") as an additional index alongside the temporal tree.
5. **Second-opinion grouping:** re-run Stage 2c with a second model for `layout_conf < 0.5` frames.
6. **Region tracking across frames:** stable region IDs across a video to simplify Stage 4 correspondence and enable per-window timelines.
7. **Local inference** (Qwen-class) for Stages 2c/5 at corpus scale.
8. **Coalescing Rule 3** (mid-line editor edits) and any rules the ground truth reveals.
9. **Agentic re-look:** let the Stage 7 agent call `redecode` and re-run Stage 2 on a time range when retrieved material is insufficient.

---

## 22. Open questions (to resolve with the harness)

1. Which OCR engine and which VLM win on the 20-frame set, and at what cost per frame?
2. Actual emitted-frame counts per hour of tutorial, by content type.
3. Whether `θpix` needs per-video calibration based on codec noise.
4. How often coalescing Rules 1–2 mis-merge, and what Rule 3 should be.
5. Whether Stage 0 measurably improves step boundaries (§18.2 delta) or can be dropped.
6. Whether OCR cross-checking is needed for VLM-only lines (currently `agree` is undefined there) — e.g., re-OCR a crop of the region.
7. Whether region text extents are sufficient for retrieval filtering or true window rects are needed sooner than 4K.

---

## 23. References

Documentation consulted during design (2026-09):

- Gemini API — Video understanding: https://ai.google.dev/gemini-api/docs/video-understanding
- Gemini API — Media resolution: https://ai.google.dev/gemini-api/docs/media-resolution
- Google blog — Agentic video understanding (2026-09-01): https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-agentic-video-in-gemini/
- OpenAI — Images and vision (image input limits, detail levels, patch tokenization): https://developers.openai.com/api/docs/guides/images-vision
- OpenAI — Cookbook, frame-extraction video narration (archived): https://developers.openai.com/cookbook/examples/gpt_with_vision_for_video_understanding
- Claude — Vision (patches, image limits, resolution): https://platform.claude.com/docs/en/build-with-claude/vision
- TwelveLabs — Pegasus: https://docs.twelvelabs.io/docs/concepts/models/pegasus
- Overshoot — Open-source VLM catalog (2026): https://www.overshoot.ai/blogs/vlm-survey-2026
- Benchmarking open-source video LLMs on news captioning (arXiv 2603.27662): https://arxiv.org/pdf/2603.27662
- Homer: hierarchical memory and agentic reasoning for long video (arXiv 2607.02588; surveys VideoTree, VideoAgent, DrVideo): https://arxiv.org/pdf/2607.02588
- CASTLE 2026 challenge write-up (three paradigms of long-video understanding): https://arxiv.org/pdf/2606.01933

Prior art recalled from training, not fetched during design **[verify IDs]**:

- RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval (Sarthi et al., 2024) — arXiv 2401.18059
- Set-of-Mark Prompting (Yang et al., 2023) — arXiv 2310.11441
- OmniParser (Microsoft, 2024) — arXiv 2408.00203
- ScreenAI (Google, 2024) — arXiv 2402.04615
- Myers, "An O(ND) Difference Algorithm and Its Variations" (1986)
