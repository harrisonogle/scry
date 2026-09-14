# Visual Transcript Pipeline — Design Specification (v1)

| | |
|---|---|
| **Status** | Draft design, pre-implementation — **revision 2** (macOS/Python port; supersedes the Windows/.NET-oriented revision 1; see §24) |
| **Date** | 2026-09-13 |
| **Platform** | Processing runs on macOS (Apple Silicon; macOS 13 or later for Vision text-recognition revision 3 **[verify floor]**; verified on macOS 26.3). Recordings may come from any OS — the sample corpus was recorded on Windows. Linux and Windows ports: §20.8. |
| **Scope** | Silent screen-recording tutorial videos → exact, timestamped, queryable "visual transcript" |
| **Audience** | A cold reader with systems-programming background and no prior context on this project |

---

## 0. How to read this document

Section 1 states the problem and requirements. Section 2 is a one-page summary of the design. Section 3 records every load-bearing decision and why it was made. Section 4 is a glossary; terms are defined there once and used freely afterward. Section 5 summarizes the tool landscape that was surveyed, so the choices in Section 3 are legible. Sections 6–14 are the stage-by-stage specification (with the data model in §10); §15 gives the prompt contracts, §16 the parameters, §17 failure modes, §18 the evaluation plan, §19 the cost model, §20 implementation notes, §21 the v2 roadmap, §22 open questions, §23 references, and §24 the revision history.

Anything marked **[verify]** is a fact recalled rather than confirmed from documentation during design and should be checked before it is relied on. Anything marked **[reasoned]** is a rule derived from first principles rather than taken from literature or prior art, and should be validated against ground truth. Anything marked **[measured]** was observed on the development machine (Apple Silicon, macOS 26.3) on 2026-09-13 with the sample video or a synthetic frame; treat it as an order of magnitude, not a benchmark. §24 lists what changed between revisions.

---

## 1. Problem statement

### 1.1 Inputs

- Screen recordings of computer tutorials: terminals, code editors, browsers (e.g., a cloud portal), text editors, dialogs.
- **No audio track.** All information is visual.
- Typical resolution 1080p or 1440p at 30 or 60 fps. **4K is out of scope for v1** (see §21).
- Videos already exist; there is no control over how they were recorded (no OS-level capture of window trees or input events). See §21 for what changes if that control is gained.
- The recording OS is irrelevant to processing. The sample corpus was recorded on Windows (Windows Terminal, PowerShell, the Azure portal in a browser); the pipeline runs on macOS and reads nothing OS-specific from the video. Examples throughout this document therefore show Windows *content* processed by macOS *tooling*.

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
| R2 | **Timestamps** on every state and transition, derived from the video clock, never from a model. | Frames carry timestamps from the decoder; models reference frame IDs only. The one exception is the optional Stage 0 outline, whose chapter times are model-produced and are snapped to emitted-frame intervals on read (§10.4). |
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

The pipeline decodes the video at native frame rate, detects every screen change with a pixel-difference test, waits for the screen to settle, and emits one frame per distinct settled state. Each emitted frame is perceived twice from the same PNG: by an OCR engine (exact characters with bounding boxes) and by a vision-language model (VLM) that groups the OCR'd lines into windows and panes, names them, and produces its own verbatim transcription. The two transcriptions are aligned row by row and an agreement flag is recorded. Consecutive states are diffed at line level to produce exact text deltas, which are coalesced into action-sized events (typed commands, appended output). A second VLM call per transition sees both frames as images plus the computed diff and produces an interpretation (action, result). Transitions are then grouped by semantic segmentation into steps, steps into sections, sections into a whole-video summary. Every node from every level is indexed for lexical and vector retrieval, and an agent answers questions over that index, fetching the underlying frame images as evidence when needed. Optionally and in parallel, Gemini's agentic video mode produces a coarse chapter outline of the whole video that is used as global context and as a retrieval document, but never overrides frame-level evidence; every consumer of the outline also runs without it (§6).

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
   │                                                          line diff (Myers) → transients → coalesce
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
| D12 | **Apple Vision (`VNRecognizeTextRequest`, accurate level, language correction off) as the baseline OCR engine; RapidOCR (PaddleOCR models on ONNX Runtime) evaluated against it.** | Ships with macOS; offline; no model download; returns text lines with a confidence and per-substring boxes. In a smoke test on a synthetic terminal frame it returned `PS C:\src> git status` and a 70-character `az aks create …` line character-for-character in ~0.3 s **[measured]**. Language correction must be off: it rewrites tokens toward dictionary words, which is exactly the "correction" R1 forbids. RapidOCR is pip-installable and cross-platform (so it doubles as the Linux engine), but on the same frame it dropped inter-word spaces and one whole line, so it is the challenger, not the baseline. The harness decides (§18.3). | Windows.Media.Ocr (revision 1's baseline; Windows-only; remains the engine for a Windows port, §20.8); Tesseract (weakest on anti-aliased UI text). |
| D13 | **Python (3.12 floor; 3.14 verified) as the implementation language, with `uv` for environments and the lockfile.** | The perception stack is Python-first: Apple Vision through PyObjC, PaddleOCR-family engines through ONNX Runtime, PyAV for decode, numpy/scipy for pixels, the Anthropic SDK with structured outputs, SQLite FTS5 and `sqlite-vec` for the index. Every dependency resolved, installed, and ran on the dev machine (§20.1). A .NET port on macOS would need the macOS workload for Vision bindings and has no maintained PaddleOCR path; Swift has the best Vision access but the weakest model-SDK and OCR-challenger story. | .NET (revision 1's choice; Windows-centric OCR); Swift; Rust/Go (no Vision bindings worth the effort). |
| D14 | **Decode in-process with PyAV (bundled FFmpeg); pixel processing with numpy/`scipy.ndimage`, not OpenCV.** | PyAV yields the decoder's exact per-frame presentation timestamp (`pts × time_base`) and needs no system `ffmpeg`. OpenCV's wheel bundles a second FFmpeg; loading it beside PyAV's on macOS logs duplicate Objective-C class warnings ("may cause spurious casting failures and mysterious crashes") **[measured]**. Everything Stage 1 needs (absolute difference, threshold, morphological opening, connected components with areas) is a few lines of numpy/scipy and runs in ~5 ms per half-resolution 1080p frame **[measured]**. | `ffmpeg` subprocess (extra install; time reconstructed from frame index); OpenCV (library conflict; no capability the pipeline lacks without it). |
| D15 | **One VLM provider in v1 — Anthropic, default model `claude-opus-5` — behind a provider interface; further providers are added when the harness can compare them.** | The interface is narrow: labeled images and text blocks in, JSON conforming to a schema out, plus token usage. Implementing three providers before a single ground-truth frame exists adds surface area without evidence. Claude's high-resolution image tier accepts 1080p and 1440p frames without downscaling (§5.3), which is the one property the design requires. `claude-sonnet-5` and `claude-haiku-4-5` are configuration alternatives for the cost bake-off. | Multi-provider from day one; Gemini-image as default (video-native context is Stage 0's job, not Stage 2's). |
| D16 | **Stage 2c sees two images per frame: the clean frame and the set-of-mark overlay.** | Labels cannot be guaranteed to avoid text in dense UIs — under revision 2's placement rule 25 % of lines on real portal frames had their label forced inside the box, over the first characters the VLM had to transcribe **[measured]**. With the clean frame in the same call, the transcription path never sees a label; the overlay serves grouping only. Cost ≈ +2.7k input tokens (≈ $0.013) per 1080p frame on Opus 5. | One image with never-inside placement only (still clashes on dense tables); a legend of crops (loses the spatial association the marks exist for). |
| D17 | **The VLM proposes rows (which marks share one visual line); code checks their geometry.** | OCR engines split and merge lines inconsistently between frames, and a geometric join within a region merged text from different windows sharing a baseline on the sample **[measured]**. The VLM already sees marks and windows; asking for rows costs nothing extra and yields `vlm_lines` that align to rows by construction. A geometric sanity check bounds the damage of a bad proposal to a split row. | Geometric join within a region (revision 2's §9.0); no join (spurious diffs and failed alignment). |

---

## 4. Glossary

- **Accessibility tree (AX):** the OS-maintained hierarchy of UI elements (windows, panes, controls) with text and rectangles — UI Automation on Windows, the Accessibility API (`AXUIElement`) on macOS. Available live on the recording machine only; not recoverable from a video.
- **Agentic video mode (Gemini):** a processing mode in which the model navigates the video with tools (read transcript, fetch frames for a time window at a chosen frame rate, re-fetch at higher rate) in a reason–call–observe loop rather than receiving all frames up front.
- **BM25 / lexical index:** full-text search scoring exact token matches. Needed for exact strings (commands, identifiers) that embeddings blur.
- **Blinker:** a small change component that recurs periodically at one position — a blinking bar, block, or underscore cursor — excluded from change detection and used to locate the caret (§7.5).
- **Caret:** the text-insertion cursor: a 1–2 px vertical bar, or a glyph-sized block or underscore in many terminals.
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
- **PTS (presentation timestamp):** the decoder's per-frame display time in stream time-base units; multiplied by the stream's time base it gives seconds. The source of every timestamp in this system (R2).
- **Refine summarization:** sequentially update one running summary with each new chunk. Cheap but early errors persist.
- **Region:** a node in the region tree: a window, a pane within a window, or a popup. Leaf regions hold lines.
- **Region tree:** window → panes → rows, built per frame by the set-of-mark grouping call.
- **Row / row line:** one visual line of text inside a region, as the VLM groups OCR marks (§9.0); the unit of alignment, agreement, and diffing.
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
- **Claude (Anthropic).** No native video input. Image path (confirmed against the vision documentation on 2026-09-13): 28×28-px patches, cost ⌈w/28⌉×⌈h/28⌉ visual tokens. Models from Claude 4.7 onward are the "high-resolution tier": up to 2576 px on the long edge **and** up to 4,784 visual tokens per image before downscaling (older models: 1568 px / 1,568 tokens). Up to 600 images per request (100 on 200k-context models), 10 MB per image, 32 MB per request; a request with more than 20 images imposes a stricter ~2000-px per-image limit (irrelevant here — every call carries one to three images). PNG/JPEG/GIF/WebP; images are best placed *before* the text that refers to them and introduced with a short label ("Image 1:"). Structured outputs (`output_config.format` with a JSON schema, or the SDK's `messages.parse`) return schema-conforming JSON. Image metadata is never read. v1 default model: `claude-opus-5` (D15).
- **Gemini image input** at `media_resolution: high` is a third option (images get larger token budgets than video frames).
- **Qwen3.5 (open weights, Apache-2.0, 2B–397B MoE).** Local inference; no per-token cost, no rate limits, data stays local, fine-tunable. Requires GPU hardware (~24–48 GB VRAM for a ~30B-class model at 8/4-bit) and vLLM-style serving. Quality relative to frontier APIs on these frames is an empirical question for the harness.

Model ranking on small-text OCR, verbatim compliance, and GUI grounding changes every few months; **the design does not assume a winner** — the harness (§18) picks it. Public benchmarks worth consulting: OCRBench (text), ScreenSpot-Pro (GUI grounding).

### 5.3 Native-resolution check (why no tiling in v1)

| Recording | Claude visual tokens (28 px) | OpenAI patches ×1.2 (32 px) | Downscaled? |
|---|---|---|---|
| 1920×1080 | 69×39 = 2,691 | 60×34 = 2,040 → 2,448 tokens | No (both) |
| 2560×1440 | 92×52 = 4,784 (exactly the high-resolution tier's visual-token cap) | 80×45 = 3,600 → 4,320 tokens | No (both; 2560 < 2576 and 4,784 ≤ 4,784 on Claude 4.7+) |
| 3840×2160 | downscaled to 2576×1449 → 4,784 | — | Yes on Claude (long edge > 2576; small text lost); OpenAI within patch limit at `original` but treat as v2 |

Claude figures are confirmed from the vision documentation (§23). OpenAI figures are as recalled in revision 1 and remain **[verify]**; they matter only if an OpenAI provider is added (D15). A 1440p frame sits exactly at Claude's token cap, so any overlay border or padding that enlarges the image must be drawn *inside* the frame's dimensions (§8.2).

### 5.4 OCR engines

- **Apple Vision (`VNRecognizeTextRequest`)** — ships with macOS (Vision.framework; text-recognition revision 3, the only non-deprecated revision as of macOS 26 **[measured: `supportedRevisions` = 1–3]**). An offline library call on any `CGImage`; unrelated to how the video was captured. Settings that matter here: `recognitionLevel = accurate`; **`usesLanguageCorrection = false`** (mandatory — correction rewrites tokens toward dictionary words, which is exactly what R1 forbids); `recognitionLanguages = ["en-US"]` with `automaticallyDetectsLanguage = false`; `minimumTextHeight` left at 0 so small text is attempted; `customWords` available for domain tokens (§22). Returns one `VNRecognizedTextObservation` per detected text line with `topCandidates(n)` (string + confidence) and a `boundingBox` in **normalized coordinates with a bottom-left origin** (converted at §8.1); per-substring boxes via `boundingBox(for: range)`, which yields word boxes on request. No documented maximum image dimension; 1080p frames are processed directly **[verify at 1440p]**. ~0.3 s for a 1000×300 synthetic frame **[measured]**; per-1080p-frame time to be measured (§22). Known behaviors to handle: an observation may merge text across a wide horizontal gap or split one visual line into fragments, and fragmentation can differ between visually near-identical frames (§9.0). On an 18-px Menlo fixture it also split a 57-character command into two observations and read `--resource-group` as `-resource-group`, dropping a hyphen while reporting confidence 1.0 **[measured by two reviewers]** — a command-syntax error nothing but the VLM cross-check (§9.2) and indexing both readings (§14.1) can catch. Callable from Python through PyObjC (`pyobjc-framework-Vision`, `pyobjc-framework-Quartz`); a Swift command-line helper is the fallback if PyObjC ever breaks.
- **RapidOCR** (`rapidocr-onnxruntime`: PaddleOCR PP-OCR detection and recognition models on ONNX Runtime, CPU). pip-installable on macOS arm64 and Linux; detects text lines as quadrilaterals (take the axis-aligned box); no word boxes. On the synthetic terminal frame the default models dropped inter-word spaces (`PSC:\src>gitstatus`), substituted a full-width comma, and missed the longest line entirely, in ~2.6 s including model load **[measured]**; it needs the English recognizer and a space-preserving configuration before it is competitive **[verify current packaging and model options]**. Role: comparison engine in the bake-off (§18.3) and the OCR engine for a Linux port (§20.8).
- **Windows.Media.Ocr** — revision 1's baseline. Windows-only WinRT API returning lines of words with `BoundingRect`; line box = union of word boxes; has a maximum image dimension (`OcrEngine.MaxImageDimension`, ~2600 px **[verify]**). Same engine interface as the others (§8.1); the engine for a Windows port (§20.8). Not used on macOS.
- **Tesseract.** Weakest on anti-aliased UI text; needs upscaling and inversion of dark themes. Not planned.

### 5.5 Screen parsing and layout (v2 candidates)

- **OmniParser (Microsoft).** Detects interactable elements and icons from screenshots with a trained detector plus OCR and captioning; built to feed computer-use agents. Likely more accurate than VLM grouping for buttons/icons; tuned for interactable elements rather than text-pane hierarchy. Complement, not replacement.
- **ScreenAI (Google).** Defines a screen-annotation schema (element types, boxes, text). Reference for schema design.
- **OS accessibility tree** (UI Automation on Windows; the Accessibility API / `AXUIElement` on macOS). Exact window/pane/control hierarchy with text and rects — but only available live on the *recording* machine, whatever OS that is. Not applicable to existing videos; see §21.

### 5.6 Long-video research (context for Stage 7)

Long-video work is categorized into single-pass multimodal LLMs, memory-based approaches (compressed visual tokens or textual memory banks accumulated as frames stream), and agentic approaches (a model with tools retrieves segments iteratively — VideoAgent, DrVideo's document-style retrieval, VideoTree's query-conditioned frame hierarchy). The known tension — coarse memories are searchable but lose detail, fine memories preserve detail but are hard to navigate at hour scale — is resolved here by a multi-level tree over precomputed text (Stage 6) with pooled retrieval (Stage 7). This problem is strictly easier than the streaming setting because all passes are offline over complete files. **RAPTOR** (recursive abstractive tree + collapsed retrieval) is the closest named match for Stages 6–7 combined.

---

## 6. Stage 0 — Global outline (Gemini agentic)

**Optional. Runs in parallel with Stage 1. Read-only downstream.**

Stage 0 needs a Gemini API key and a provider used nowhere else in the pipeline, so it is an optional stage: every consumer listed below must run correctly with `outline.json` absent (Stage 5 omits the outline preamble; Stage 6's section-boundary call receives no suggestion; Stage 7 indexes nothing from it; `chapter_of()` returns `null`). v1 implements the absent-outline path first and the Gemini call behind the same optional-stage switch.

- **Input:** the whole video file (or YouTube URL). Agentic mode; `media_resolution` default (resolution is irrelevant here; only structure is wanted).
- **Prompt:** produce a chapter outline as JSON: `[{start_s, end_s, title, gist}]`, with 5–20 chapters, boundaries at changes of sub-goal, no attempt at exact text.
- **Output:** `outline.json`.
- **Consumers:**
  1. Stage 5 prompt preamble: "Global outline: …; this pair falls inside chapter *k*: *title*." Disambiguates local actions.
  2. Stage 6 section-boundary call receives the chapter boundaries as a *suggestion* to reconcile against transition evidence. Rule: frame evidence wins on conflict.
  3. Stage 7: each outline entry is indexed as a top-level document.
- **Never** writes into `frames.jsonl` or `transitions.jsonl`. Chapter times are model-produced (the R2 exception) and are snapped to emitted-frame intervals on read (§10.4); nothing copies them into other files.

---

## 7. Stage 1 — Decode, change detection, settle, masks

Stage 1 is the only stage whose re-run renumbers frames and therefore invalidates every downstream file (§10.6). Its behavior is fully specified here so that it can be simulated on synthetic frame sequences in unit tests before any ground truth exists (§18.4).

### 7.1 Decode

Decode in-process with PyAV, which bundles FFmpeg (no system `ffmpeg` install). Every frame's presentation time is `frame.pts × stream.time_base` — the decoder's clock, never a frame counter (R2). For each decoded frame:

1. Convert to 8-bit grayscale (`frame.to_ndarray(format="gray")`) for detection. Detection runs at full resolution by default; a half-resolution mode exists for speed (§7.2, §20.2).
2. Keep the decoded frame object until the settle logic (§7.3) decides whether to emit it; on emit, convert *the same frame* to RGB and write a lossless PNG (never JPEG — compression artifacts damage small text). No second decode pass and no parallel color stream are needed.

Set the stream's `thread_type` to `AUTO` so decoding uses several cores. The 1080p/30 fps sample (h264, 14.2 min, no audio) decodes to grayscale at ~535 fps with `AUTO` threading **[measured]** (decode alone is ~7,700 fps; the gray conversion dominates), so a 15-minute video decodes in well under a minute; PNG encoding of an emitted frame costs ~0.3 s at Pillow's default compression **[measured]** and is done off the decode thread. VideoToolbox hardware decode works (`av.open(path, hwaccel=HWAccel(device_type="videotoolbox"))`, frames arrive as `nv12`) but ran at ~240 fps, slower than software decode **[measured]**, so software decode is the default. `stream.frames` is 0 on the sample; the video's duration is `container.duration` (852.83 s on the sample **[measured]**), used for the last frame's `t_end` and for progress. Guard `frame.pts is None` (fall back to `frame.time`, then to the previous time plus one frame period, and log it); the sample never hits it (25,585 frames, PTS strictly increasing **[measured]**).

Alternative (portable, not default): spawn `ffmpeg -i in.mp4 -f rawvideo -pix_fmt gray -` and read fixed-size frames from stdout, reconstructing time from the frame index and stream rate, or `-vf showinfo` to recover `pts_time`.

### 7.2 Change detection (per frame)

The revision-1 rule applied a 3×3 morphological opening to the changed-pixel map to kill codec noise. Text strokes at terminal sizes are 1–2 px wide, so the opening also erased typed characters: on a synthetic 15-px Menlo frame, `gi → git` produced 29 changed pixels and **0 after opening**; on the sample video 14 of 79 triggering frames in a 90-second span were lost, every one a keystroke-sized change on the prompt row **[measured]**. Revision 3 replaces the opening with a dilation (which merges the strokes of one glyph into one component) and a minimum-area filter (which removes the residual codec blobs, all ≤ 8 px on the sample **[measured]**):

```
delta      = |luma_f − luma_prev|                        // ALL pixels; nothing is masked here
changed    = delta > θpix                                // θpix = 12; feeds the churn ring buffer (§7.4) and last_change (§7.4)
blobs      = dilate(changed, 3×3)                        // merge the strokes of one glyph/word; NO opening
comps      = label(blobs, 8-conn)                        // scipy.ndimage.label; area(c) = count of *changed* (pre-dilation) pixels in c;
                                                         // bbox(c) = tight box of those pixels, not of the dilated blob (else a 2-px caret is 4 px wide)
comps      = [c for c in comps if area(c) ≥ θmin]        // θmin = 8 px: removes I-frame residual blobs
bars       = [c for c in comps if width(c) ≤ 3 and 8 ≤ height(c) ≤ 30]   // bar carets (and 1-px glyphs such as l, i, |): never trigger
comps      = comps − bars − blinkers(§7.5) − inside_churn(§7.4)
trigger    = any(area(c) ≥ θcomp) or Σ area(c) ≥ θcount  // θcomp = 24 (a lowercase glyph at 15 px is 25–40 px), θcount = 100
```

- `trigger(f, prev)` is the **stillness test**: it drives the settle state machine. `novel(f, last)` is the same computation between the candidate frame and the last emitted frame, with the same exclusions — the **novelty test** (§7.3).
- Rationale unchanged from revision 1: an **absolute** pixel count, never a fraction. A 1080p frame is 2,073,600 px; a 16×16 checkbox is 256 px = 0.012 %, which any fraction threshold would miss. The **connected-component** test distinguishes contiguous UI change from scattered compression noise; `θmin` does the noise removal that the opening used to do without destroying thin strokes.
- A lone keystroke that is itself bar-shaped (`l`, `i`, `|`, `1` in some fonts) is excluded like a caret and gets bundled into the next change. Accepted loss (§7.7).
- Thresholds are UI-element sizes in pixels and **do not scale with recording resolution** (a 16×16 checkbox is 256 px at 1080p and at 1440p alike, unless the recording used display scaling). They scale only with the detection resolution: in half-resolution mode `changed` is reduced with a 2×2 **max** (not mean) before dilation and labeling, and the calibrated half-resolution thresholds are separate parameters (§16) validated on the synthetic typing fixture (§18.4).
- The codec-noise premise for θpix = 12 holds on the sample: over 2,700 frames, 93 % have max |Δluma| ≤ 12, and every I-frame without real change shows 23–51 pixels above θpix in components of ≤ 8 px **[measured]**. Whether θpix or θmin need per-video calibration is an open question (§22).

### 7.3 Settle

Definitions: `prev` = previous decoded frame; `last` = the last emitted frame record, which is **buffered, not yet written**, until it is superseded (it may still be upgraded or have its caret filled in); `changed` = the screen has moved since the last decision; `tChange` = time the previous emitted state ended; `tStill` = time the current state was first fully on screen (`∅` while moving); `tLastEmit` = time of the last emission.

```
emit(f0, tChange=t0, tSettled=t0, settled=true); prev=last=f0; tLastEmit=t0
changed=false; tChange=∅; tStill=∅
for each frame f at time t (tPrev = time of prev):
  update the churn and blink masks from the unmasked change map (§7.4, §7.5)
  if trigger(f, prev):                                  // stillness test, masked
     if !changed: changed=true; tChange=t                // f is the first frame that no longer shows the previous state
     tStill=∅
  elif changed:                                          // a still frame after motion
     if tStill==∅: tStill=tPrev                          // f equals prev, so the state was already on screen at tPrev
     if t − tStill ≥ S:                                  // still for S
        if deferred(f, last): wait                       // §7.5: every novelty component sits at an unconfirmed blink-candidate position seen within one blink period
        elif novel(f, last): emit(f, tChange, tSettled=tStill, settled=true); last=f; tLastEmit=t; changed=false
        elif !last.settled and !churn_active: last.settled=true; last.t_settled=max(tStill, last.t_change); changed=false   // a snapshot was the end state
        else: changed=false                              // something flashed and reverted — nothing to emit
  if ((changed and tStill==∅ and t − tChange ≥ M) or (churn_active and t − tLastEmit ≥ M)) and t − tLastEmit ≥ M:
     // one unsettled snapshot per M, whether the clock is the max-hold (screen moving) or the churn tick (a region churning)
     emit(f, tChange=max(tChange if changed else tLastEmit, tLastEmit), tSettled=t, settled=false); last=f; tLastEmit=t
     if changed: tChange=t
  if churn_region_disappeared_this_frame:                // §7.4
     if !changed: changed=true; tChange=tLastEmit
     tStill=t_last_change(pixels that left the region)   // the final state has been on screen since the last change inside the region
  if a blinker was confirmed this frame (§7.5):
     tReal = time of the last motion frame whose components were not all that blinker's toggles
     if changed and (tStill = ∅ or tReal < tStill): tStill = tReal                       // corrects the pending state
     if last.t_settled is one of the blinker's toggle times and tReal < last.t_settled:
        last.t_settled = tReal                                                          // corrects the buffered emission
  prev=f
end of stream:
  if changed and novel(prev, last): emit(prev, tChange, tSettled=(tStill or tPrev), settled=(tStill≠∅))
  the last emitted frame's t_end = container.duration
```

- Comparison against `prev` measures stillness; comparison against `last` (last emitted) measures novelty. A menu that opens and closes within S emits nothing.
- Each emitted frame records `t_change` (when the previous state ended) and `t_settled` (when this state was fully on screen — the first still frame, not the frame S later at which stillness was confirmed). The PNG is taken from the confirming frame, which is identical to the first still frame up to excluded changes such as a caret blink. The state's stable interval is `[t_settled_i, t_change_i+1)`; the gap `[t_change_i+1, t_settled_i+1)` is "in transition."
- The max-hold fires only while the screen is actually moving (`tStill == ∅`). Revision 2 let it fire during the settle wait, which mislabeled a state that had in fact settled at 2.8 s as unsettled at 3.0 s and then never emitted the settled state because it was not novel **[reviewed by trace]**. The `!last.settled` upgrade handles the remaining case: a max-hold or churn-tick frame that turns out to be the end state is marked settled in place with the correct `t_settled`.
- The churn tick keeps periodic unsettled snapshots flowing while a region churns (revision 2's masking suppressed both the max-hold and the novelty test, so a continuously scrolling command output was never captured until the next unrelated change **[reviewed by trace]**); the deactivation rule captures the final state with the correct times once the region stops.
- Sub-threshold changes (caret blink, clock digits below θcomp) do not reset the settle timer; that is what makes settling possible.
- A typing pause longer than S splits one command into two emitted frames. This is not a failure; coalescing (Stage 4b) rejoins them.
- Records are finalized and written at `t_end` (when the next emission occurs, or at end of stream), because the caret (§7.5) is derived from the state's stable interval and the settled flag may be upgraded.

### 7.4 Churn mask

Purpose: a region that never stops changing (spinner, progress bar, embedded playing video, continuously scrolling log) would otherwise prevent the screen from ever settling.

```
N = W · fps                                            // W = 5 s → 150 maps at 30 fps, 300 at 60 fps
ring buffer of the last N unmasked change maps (§7.2 `changed`, bit-packed with np.packbits)
count[p]  = number of maps in the window with changed[p] set   // uint16 (uint8 overflows at 60 fps); running: += entering map, −= leaving map
n         = maps currently in the window (so start-up works)
mask[p]   = count[p] > ρ_on·n  or  (mask_prev[p] and count[p] > ρ_off·n)   // per-pixel hysteresis; ρ_on = 0.5, ρ_off = 0.2
churn     = connected components of dilate(open(mask, 3×3), 9×9) with area ≥ 400 px → list of bboxes, recomputed every frame
last_change[p] = index of the last frame with changed[p] set  // int32; used by the deactivation rule (§7.3)
churn_region_disappeared_this_frame = the number of churn regions decreased; t_last_change = max of last_change over the pixels
                                       that left the mask since the previous such event (per-pixel hysteresis empties a region gradually,
                                       so "a pixel left" is not the event — the sample video showed a mid-scroll snapshot being upgraded
                                       to a settled state when it was)
```

- The ring buffer is fed by the **unmasked** change map. Revision 2 fed it with the masked map, so a masked region stopped registering change, decayed out of the mask, re-registered, and re-entered with a period of about W **[reviewed by trace]**. Hysteresis is per pixel with a persistent mask; components are recomputed every frame and have no identity, which is why the deactivation event is a drop in the region count, dated by the pixels that left.
- Masked pixels (more precisely, change components lying inside an active churn bbox) are excluded **only** from the stillness and novelty tests (§7.2, §7.3). Nothing else in the pipeline is masked. The novelty test is masked only by *currently active* churn, so when a region deactivates its final content counts as novel.
- Every emitted frame records `churn_regions` (active churn bboxes at emission). Downstream: OCR lines inside churn are tagged `in_churn=true`; the Stage 2 VLM prompt lists them as "animating"; Stage 5 is told the region was changing continuously.
- Memory: 1080p × 150 maps × 1 bit ≈ 39 MB (78 MB at 60 fps; a quarter of that in half-resolution mode).
- Churn cannot distinguish a spinner from a continuously scrolling log; both are churn. The churn tick (§7.3) emits an unsettled frame every M while it lasts, so nothing stalls, and Stage 5 sees "output was scrolling continuously"; the deactivation rule captures the end state.

### 7.5 Blink tracker (caret and block cursors)

Bar carets (1–3 px wide) are excluded from the trigger by shape alone (§7.2). Block and underscore cursors (≈ 9×18 px at 1080p; the default in cmd, conhost PowerShell and many terminal profiles) are glyph-sized, so a blinking one would trigger on every blink and the screen would never settle; every state would be a max-hold tagged `settled=false`. The blink tracker handles them, and doubles as the caret locator for §9.4:

- Candidates: components (after the θmin filter, before exclusions) with bbox ≤ 12×32 px. Track candidates by bbox: a new component with IoU ≥ 0.5 against a tracked candidate is a recurrence of it.
- A candidate becomes a **blinker** after ≥ 2 recurrences with 0.15–0.7 s between consecutive recurrences, all within 3 s. Blinkers are excluded from the stillness and novelty tests until they have not recurred for 2 s.
- Because confirmation takes one or two blink periods, a block cursor triggers a few times after each state change before it is masked — and a cursor's half-period (~0.5 s) exceeds S, so between toggles the screen looks settled and each toggle would be emitted as a state. Two rules in §7.3 handle this: a novelty decision whose components all sit at unconfirmed candidate positions seen within one maximum blink period is **deferred** (a genuine one-off change of that size is emitted at most 0.7 s late, with correct times), and on confirmation `t_settled` of both the pending state and the buffered emission is restored to the last non-blinker motion. Verified on the synthetic block-cursor fixture of §18.4 **[measured]**.
- The caret position for a frame is the bbox of the blinker (or bar-shaped component recurring at one position) active during the frame's stable interval, written when the record is finalized at `t_end`: `caret: [x0,y0,x1,y1] | null` — a box like every other stored geometry (§10.5). Finalization happens at the *next* emission, which can be many seconds later, so the tracker keeps a history of expired confirmed blinkers (bbox, first and last toggle) for the lookup. A cursor that does not blink — the sample's PowerShell underscore cursor produces no toggles at all **[measured]** — yields no caret; focus then rests on the retrospective and VLM signals (§9.4).
- A typed glyph adjacent to the caret moves the caret one cell; the merged change component is wider than 12 px and is not a candidate, so typing still triggers. A lone bar-shaped keystroke is the accepted exception (§7.2).

### 7.6 Outputs (`stage1.jsonl`, `frames/`)

- `frames/NNNNN.png` — full-resolution emitted frames (content-addressed by SHA-256 as well, for idempotency).
- One record per emitted frame: `frame`, `t_change`, `t_settled`, `t_end`, `settled`, `churn_regions`, `caret`, `width`, `height`, `sha256`, `png`. `t_end` is the next frame's `t_change`; for the last frame it is the container duration.

### 7.7 What Stage 1 can and cannot lose

- **False positives** (spurious emitted frames) cost tokens only. Known source: a taskbar or terminal clock changing a digit (~80 px) every minute exceeds θcomp; Stage 4 tags such ops `clock` and the transition `kind: trivial`, which skips Stage 5 (§11.2).
- **False negatives** (a change below threshold) do not vanish: the change is still present at the next emitted frame and appears in that transition, with coarser timing and possibly bundled with another change. The bar-shaped-keystroke exclusion is the known case.
- **True loss** is only a sub-threshold change that reverts before the next emission — rare and low value.
- A solid object moving ≤ 3 px per frame (a slow window drag) has bar-shaped leading and trailing edges and is invisible to the trigger while it moves; its end position is captured by the novelty test once it stops. A ≤ 12×32 px change that toggles once at blink cadence and never confirms is emitted up to 0.7 s late (deferral, §7.5). Both accepted.
- **Recovery tool:** the video is kept; every record carries a time range; any downstream stage may request a re-decode of `[t_a, t_b]` at full rate to look again. This is exposed as a callable tool (`redecode(video_id, t_a, t_b, fps)`), not a manual step.

---

## 8. Stage 2 — Per-frame perception

One OCR run and one VLM call per emitted frame. Both consume the same PNG.

### 8.1 Stage 2a — OCR (`ocr.jsonl`)

- Input: `frames/NNNNN.png` at full resolution. Engines with a dimension cap below the frame size run at the cap and have their boxes scaled back (§10.5); Apple Vision has no documented cap and processes 1080p directly, in 0.07–0.28 s per real frame with 14–99 lines **[measured]**.
- Output per frame: `lines[] = {id, bbox:[x0,y0,x1,y1], text, conf, words[] | null, in_churn}` in **original-frame pixel coordinates**, plus the engine name and settings used.
- **Engine interface** (every engine conforms; selected by configuration): `recognize(png) → [{text, conf, bbox, words: [{text, bbox}] | null}]`, one entry per text line as the engine sees lines, boxes already in original-frame pixels. Adapters:
  - *Apple Vision:* one observation per line; `topCandidates(1)[0]` gives `string` and `confidence`; word boxes from `boundingBox(for:)` over each whitespace-delimited token's character range (cheap; stored). Vision's boxes are normalized with a bottom-left origin: `x0 = bx·W`, `y0 = (1 − by − bh)·H`, `x1 = (bx + bw)·W`, `y1 = (1 − by)·H`, rounded to integers. Settings: accurate level, `usesLanguageCorrection = false`, `["en-US"]`, automatic language detection off, `minimumTextHeight` 0.
  - *RapidOCR:* line quadrilaterals → axis-aligned bbox; `words = null`.
  - *Windows.Media.Ocr (Windows port only):* lines of words; line bbox = union of word boxes.
- **`conf` is engine-specific and advisory.** Vision reported `1.00` on 151 of 151 lines across two real frames, including misreads (`Leamn more`, a GUID with Cyrillic `е` and `б` substituted for `e` and `6`) **[measured]**; no rule in this design depends on `ocr_conf`. The per-line uncertainty signal is `agree` (§9.2).
- Word grouping fallback, for an engine that returns only words:

```
sort words by y-center
a word joins the current line if |yc(word) − yc(line)| < 0.5 · median(word height)
within each line sort by x; line.text = join(words, " "); line.bbox = union(word boxes)
```

- Line IDs are stable within a frame (`l1…lN`, assigned in reading order: sorted by y0 then x0). Fragments of one visual line are **not** joined here — rows are decided by the VLM (§8.3) and materialized in Stage 3 (§9.0).
- Lines whose bbox intersects a churn region are tagged `in_churn=true`.
- Lines containing a non-ASCII letter inside an otherwise ASCII token are flagged `confusable=true` (flag only; nothing is rewritten). A GUID and a URL belong in the calibration set (§18.1).

### 8.2 Stage 2b — Set-of-mark overlay (`overlays/`)

Draw each OCR line's bbox on a copy of the frame (Pillow) as a 1-px rectangle in a color that contrasts with the frame, with its numeric ID in a 10–12 px font (Menlo or SF Mono on macOS) on a 50 %-alpha backing. **Label placement never covers text:** try, in order, right of the box (`x1 + 2`, vertically centered), the left gutter (`x0 − label_w − 2`), above, below; a slot is taken only if the label rectangle intersects no OCR box; if every slot clashes, use the least-overlapping slot and count it in `label_clashes` for the frame (manifest). Revision 2's rule ("outside the top-left corner, else inside") put the label on the previous line's box at a 16–18 px line pitch and then fell back to inside the box on 25 % of lines on real portal frames, covering the first characters the VLM had to transcribe **[measured]**. The overlay keeps the frame's exact dimensions — no border or padding — because a 1440p frame already sits at Claude's visual-token cap (§5.3). Save as `overlays/NNNNN.png`.

### 8.3 Stage 2c — VLM grouping and transcription call (`perception.jsonl`)

- Input: **two images**, each preceded by a short text label — `Image 1 (clean frame 12, t=47.72s):` the frame PNG, and `Image 2 (same frame with numbered boxes):` the overlay PNG — sent at native resolution as base64 PNG blocks (Claude's high-resolution tier needs no opt-in; `detail: "original"` on OpenAI; `media_resolution: high` on Gemini). The contract says: transcribe from Image 1; use Image 2 only to group. The second image costs ~2.7k input tokens per 1080p frame (≈ $0.013 on Opus 5) and removes the overlay entirely from the transcription path (R1).
- Contract (full prompt text in §15.1): group the numbered lines into a region tree (windows → panes → popups), name each region and its application, identify the focused window with a confidence and the cues used, and for each region that holds text give its **rows** — each row is the ordered list of marks that sit on one visual line (table cells, tabs, a prompt and its command), or `[]` for a row OCR missed — and transcribe each row verbatim in `vlm_lines`, one entry per row, reading order. Free-text `description` for anything a line list cannot express (diagram relationships, highlighted rows, selected items, icons).
- Output schema (structured output — with the Anthropic SDK, `messages.parse` with a pydantic model, or `output_config.format` with the equivalent JSON schema; the models in code are the source of truth and this rendering is illustrative):

```json
{
  "regions": [
    {"id":"r1","kind":"window|pane|popup","name":"Windows Terminal — pwsh","app":"Windows Terminal",
     "parent":null,"conf":0.95,"occludes":["r2"],
     "rows":[["l3"],["l4"],[]],
     "vlm_lines":["git status","On branch main","nothing to commit, working tree clean"]}
  ],
  "focused_region":"r1","focused_conf":0.8,"focused_cues":["title bar highlight","caret visible"],
  "description":"…",
  "unassigned_line_ids":[]
}
```

- Rules enforced by prompt and validated by code: every OCR line ID appears in exactly one row of exactly one region or in `unassigned_line_ids`; `rows` and `vlm_lines` have equal length; `vlm_lines` are verbatim with `?` for unresolvable characters; no normalization of code; whitespace preserved. Any region may hold rows (a window's title bar plus child panes is normal); "leaf region" below means a region that holds rows. `occludes` = regions this region visually covers, in whole or in part. Lines in `unassigned_line_ids` are transcribed nowhere.
- **Validation is by repair, never by abort:** an unknown ID is dropped; a duplicate keeps its first occurrence; a row whose marks were all dropped is removed together with its text; a `rows`/`vlm_lines` length mismatch truncates to the shorter and the cut rows' marks fall through to `unassigned_line_ids`; a mark missing from every row is appended to `unassigned_line_ids`; a `parent` naming no region or closing a cycle becomes `null`; `focused_region` naming no emitted region becomes `null`. Every mark ends up exactly once. Repairs are counted on the frame record (`grouping_repairs`). Truncated output (`stop_reason == "max_tokens"`) is retried once at twice the token budget (≤ 32k); a schema failure is retried once with the validation error quoted; after that the frame gets `vlm: null, error: "…"` and the run continues.

### 8.4 Model choice

Any of the §5.2 models. Choose by the harness: transcribe the 20-frame calibration set, hand-check, compute CER on commands, compare cost per frame. The design assumes only that the model accepts images at native resolution and supports structured output. v1 ships the Anthropic provider (`claude-opus-5` default; `claude-sonnet-5`, `claude-haiku-4-5` as alternatives, D15).

---

## 9. Stage 3 — Merge (`frames.jsonl`)

Produces the canonical per-frame state record (§10.1). Nothing downstream touches raw OCR or raw VLM output again. Stage 3 owns `frames.jsonl`; the retrospective focus signal computed later lives in a sidecar (§9.4, §10.7).

### 9.0 Rows **[reasoned]**

OCR engines split or merge visual lines on their own criteria, and the split differs between frames whose text is identical (Vision returned `Node pools Access Networking` as one observation and its neighbours `Basics`, `Integrations` as separate ones; `Subscription` / `:sub-global` as two **[measured]**). Left alone, that produces spurious `delete`/`insert` pairs in Stage 4 and failed OCR↔VLM alignments here. Revision 2 joined fragments by a geometric baseline rule; that rule joined text across windows sharing a baseline (a terminal's title bar and the portal's `Status` row on the sample **[measured]**) and produced rows the VLM did not transcribe as one entry. Revision 3 makes the VLM the arbiter of rows (grouping is its job; geometry stays OCR's):

- For each region, each entry of `rows` (§8.3) is materialized as one **row line**: OCR fragments in the listed order, joined with a single space; `id` = the first mark's ID; `marks` = the list of mark IDs; `bbox` = union of the marks' boxes; `in_churn` = any mark's; `ocr` = the joined text.
- A row is **rejected** (split back into one row per mark, flagged `row_rejected`) if its marks' vertical centres differ by more than 0.5 × the region's median line height, or if two horizontally adjacent marks are more than 3 × the line height apart. Rejection is counted on the frame. A geometric sanity check, not a join rule: the VLM proposes, code disposes.
- An empty row `[]` is a VLM-only line (§9.2).
- Everything below — alignment, agreement, diff — operates on row lines. Individual fragment boxes remain in `ocr.jsonl`.

### 9.1 Region geometry

For each region: `bbox = [min x0, min y0, max x1, max y1]` over its row lines (recursively including child regions). This is the **text extent**, not the window frame: chrome and empty areas are excluded. A region with no row lines that have boxes (empty, or VLM-only rows) has `bbox: null` and is skipped by every geometric rule. Adequate for containment and metadata; if a true window rect is ever needed (v2 cropping) it is obtained separately.

### 9.2 Line alignment and agreement

Per leaf region, `vlm_lines[k]` is aligned to row `k` directly — the VLM defined both. The LCS alignment of revision 1 is used only as a repair: when rows were rejected (§9.0) or the lengths disagree, align the region's `vlm_lines` (reading order) with its row lines (sorted by y0 then x0) by LCS with the match predicate `similarity(a, b) ≥ 0.8 or (len(shorter) ≤ 8 and Levenshtein(a, b) ≤ 1)` (normalized Levenshtein ratio after whitespace normalization; the short-line clause is needed because `ls` vs `1s` scores 0.5 **[measured]**), also trying the concatenation of 2–3 consecutive VLM entries against one row when a single entry fails.

| Case | Record |
|---|---|
| matched | `ocr`, `vlm`, `ocr_conf`, `agree = (norm(ocr) == norm(vlm))` |
| matched except an icon glyph | Vision renders icons as characters (`P Search resources…`, `Ô Delete`, `• Zone 1` **[measured]**) and the VLM does not. If `norm(vlm)` equals `norm(ocr)` after removing one leading or trailing token of ≤ 2 characters that `vlm` lacks: `agree = true`, `ocr_glyph_stripped = "P"`, fused text = the stripped reading; `ocr` is stored untouched. |
| OCR-only (no VLM entry aligns) | `vlm = null`, `agree = null` |
| VLM-only (an empty row; OCR missed it) | `id = v<n>` (per frame), `ocr = null`, `ocr_conf = null`, `bbox = null`, `in_churn = null`, `agree = null`; sort position interpolated between the aligned neighbours |

`norm()` trims, collapses internal whitespace, and unifies quote glyphs (`“”` → `"`, `‘’` → `'`). Case is preserved. The **fused text** of a line — the text every later stage uses — is `ocr` (or the stripped reading) where `agree = true`, otherwise `vlm` if `ocr` is null, otherwise `ocr` with the line marked `uncertain` wherever it is quoted.

**Fusion does not depend on *window* grouping.** Agreement is computed per row line keyed by mark IDs; which window the row belongs to is metadata attached afterward. A row assigned to the wrong window still has the correct text, box, and `agree` flag. (Fusion does depend on the VLM's row proposal; §9.0's sanity check bounds the damage of a bad one to a split row.)

### 9.3 `layout_conf`

A per-region heuristic quality score in [0,1], not a probability.

```
score = region.conf                                             // VLM self-report
for each row line L of the region:
    for each region R' that is neither an ancestor nor a descendant of the region,
        and is not related to it by `occludes` in either direction,
        and has a row line whose bbox overlaps L vertically by ≥ 50 % of L's height and overlaps L horizontally:
            score −= 0.3                                         // interleaved text from two regions (total penalty capped at 0.6)
row_coverage = (number of distinct text rows, including descendants' rows × median line height) / bbox height
if row_coverage < 0.3: score −= 0.2                             // scattered membership
if the region, counting the rows of its descendants, has exactly one row line: score = min(score, 0.6)
regions with bbox = null: score = min(score, 0.5); geometric tests skipped
clamp to [0,1]
```

Revision 1 tested whether a line's centre lay inside another region's *hull*; since a background window's text extent encloses every foreground window, that penalized the corpus's normal layout (the §10.1 example was impossible under the rule) **[reviewed by trace]**; the area-based scatter test fired on any terminal with one long line. Consumers: (1) Stage 5 prompt lists regions with `layout_conf < 0.5` as "grouping uncertain; text may belong to an adjacent window"; (2) Stage 7 uses region/app names from such frames only as soft boosts, never as hard filters; (3) development: sample low-score frames for inspection; (4) optional reprocessing: re-run §8.3 with a second model or prompt for frames below threshold and keep the higher-scoring result. v1 implements (1) and (3).

### 9.4 Focus confidence

Three signals, two computable:

1. **Caret** (§7.5): the region whose bbox, expanded by one line height, contains the caret bbox is focused; else the nearest region within two line heights (a caret on an empty prompt line lies outside a text-extent bbox). Compared at root-window level when the caret falls in a pane.
2. **Retrospective**: if the next transition's coalesced `typed` event lands in region R, R was focused at this frame — attributed only when that transition has no `appeared` region and no `focused_region` change (a click that focuses a window can share a transition with the first keystroke). Computed after Stage 4b and written to `focus.jsonl` (§10.7), never back into `frames.jsonl`.
3. **VLM self-report** (§8.3) with its own 0–1 estimate and cues.

Combination (`focused_conf`; `focused_signals` lists the contributors):

| Signals | Result |
|---|---|
| caret or retrospective agrees with VLM | that region, 0.9 |
| a computed signal present, VLM `null` | computed, 0.7 |
| a computed signal disagrees with VLM | computed, 0.6; the VLM's answer recorded at 0.3 |
| caret and retrospective disagree | retrospective, 0.6 — whatever the VLM says (it is listed as a contributor when it agrees) |
| only VLM | VLM, 0.5 |
| nothing | `null` |

Stage 3 writes the caret + VLM combination into `frames.jsonl`; Stage 4b's sidecar supersedes it where the retrospective signal exists. Downstream logic must not depend hard on focus.

---
## 10. Data model

All files are JSON Lines (one object per line) except `outline.json`, `video.json`, `manifest.json`, and `batches.json`. All coordinates follow §10.5. All IDs follow §10.6. File ownership follows §10.7: **no stage writes a file another stage owns**; later signals live in sidecars that a loader merges on read.

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
  "caret": [318, 41, 320, 59],
  "focused_region": "r1",
  "focused_conf": 0.9,
  "focused_signals": ["caret", "vlm"],
  "description": "Terminal in the foreground; browser behind it shows a portal blade with a selected row.",
  "regions": [
    {
      "id": "r1", "kind": "window", "name": "Windows Terminal — pwsh", "app": "Windows Terminal",
      "parent": null, "bbox": [12, 40, 640, 300], "conf": 0.95, "layout_conf": 0.95, "occludes": ["r2"],
      "lines": [
        {"id": "l3", "marks": ["l3"], "bbox": [12, 40, 300, 58], "ocr": "git status", "ocr_conf": 1.0,
         "vlm": "git status", "agree": true, "in_churn": false},
        {"id": "l4", "marks": ["l4", "l5"], "bbox": [12, 60, 540, 78], "ocr": "On branch maln", "ocr_conf": 1.0,
         "vlm": "On branch main", "agree": false, "in_churn": false},
        {"id": "v1", "marks": [], "bbox": null, "ocr": null, "ocr_conf": null,
         "vlm": "nothing to commit, working tree clean", "agree": null, "in_churn": null}
      ]
    },
    {
      "id": "r2", "kind": "window", "name": "Azure Portal — Storage accounts", "app": "Browser",
      "parent": null, "bbox": [0, 0, 1920, 1080], "conf": 0.9, "layout_conf": 0.9, "occludes": [],
      "lines": [ {"id": "l1", "marks": ["l1"], "bbox": [64, 17, 181, 33], "ocr": "Microsoft Azure", "ocr_conf": 1.0, "vlm": "Microsoft Azure", "agree": true, "in_churn": false} ]
    },
    {
      "id": "r3", "kind": "pane", "name": "left navigation", "app": "Browser",
      "parent": "r2", "bbox": [0, 120, 260, 1000], "conf": 0.85, "layout_conf": 0.8, "occludes": [],
      "lines": [ {"id": "l15", "marks": ["l15"], "bbox": [22, 262, 106, 279], "ocr": "* Overview", "ocr_conf": 1.0, "vlm": "Overview", "agree": true, "ocr_glyph_stripped": "*", "in_churn": false} ]
    }
  ],
  "unassigned_lines": [],
  "grouping_repairs": 0, "rows_rejected": 0, "label_clashes": 0,
  "vlm_model": "claude-opus-5", "prompt_version": "s2c-v1", "error": null
}
```

Field notes:
- `t_end` is the next frame's `t_change`; for the last frame it is the container duration.
- `regions` is a flat list with `parent` links; `bbox` of a parent encloses its children by construction (§9.1); `bbox: null` for regions with no boxed lines.
- `lines` are row lines (§9.0) and may appear on any region. `marks` lists the OCR line IDs the row was built from (`[]` for VLM-only lines). Optional per-line flags: `ocr_glyph_stripped`, `confusable`, `row_rejected`, `uncertain`.
- `focused_*` here is Stage 3's caret + VLM combination; `focus.jsonl` (§10.7) supersedes it where a retrospective signal exists.
- There is no `outline_chapter` field. The chapter containing a frame is computed on read from `outline.json` by `t_settled` (§10.4).
- `vlm_model`, `prompt_version`, `error` record provenance and the §8.3 failure path (`error` non-null ⇒ `regions` came from OCR only: one region per frame, `kind: "unknown"`, rows = one per OCR line).

### 10.2 `transitions.jsonl` — edges

```json
{
  "id": "T17",
  "from_frame": 11,
  "to_frame": 16,
  "intermediate_frames": [12, 13, 14, 15],
  "t": [40.10, 47.72],
  "kind": "coalesced",
  "regions": {"matched": [["r1", "r1", 0.91], ["r2", "r2", 0.88]], "appeared": [], "disappeared": []},
  "computed_diff": {
    "r1": {
      "from_region": "r1",
      "ops": [
        {"op": "modify", "old": "PS C:\\src> ", "new": "PS C:\\src> git status", "old_index": 3, "new_index": 3,
         "char_diff": [["=", "PS C:\\src> "], ["+", "git status"]], "y": 41, "uncertain": false},
        {"op": "insert", "new_index": 4, "text": "On branch main", "y": 61},
        {"op": "insert", "new_index": 5, "text": "nothing to commit, working tree clean", "y": 81}
      ]
    }
  },
  "events": [
    {"type": "typed", "region": "r1", "text": "git status", "line": "PS C:\\src> git status", "frames": [11, 15]},
    {"type": "output_appended", "region": "r1", "lines": 2, "text": "On branch main\nnothing to commit, working tree clean", "frames": [15, 16]}
  ],
  "transient": null
}
```

- `t = [t_end(from_frame), t_settled(to_frame)]` — the window in which the action happened (R2). For a coalesced transition: the first member's `t[0]` to the last member's `t[1]`.
- `kind ∈ {single, coalesced, transient_merged, unsettled, trivial}`. `unsettled` if any member frame has `settled=false`; `trivial` if every op is a `clock` op (§11.2), in which case Stage 5 is skipped. For `transient_merged`, `transient = {"frame": 14, "region": "r5", "name": "toast", "hold_s": 1.2}`.
- `regions` records the §11.1 assignment with scores. `computed_diff` is keyed by the **to-frame** region ID with `from_region` naming the from-frame ID (region IDs are per frame); the pseudo-region `r0` holds the diff of `unassigned_lines`. `old_index`/`new_index` are positions in the from/to region's line list; `y` is the new line's `y0` (the old line's for a delete); `char_diff` is a list of `[op, text]` runs (`=`, `+`, `−`) from the character-level Myers of §11.2; `uncertain` marks ops whose text came from a non-agreeing line.
- A coalesced transition's `computed_diff` is **recomputed directly** between `from_frame` and `to_frame`; the members' diffs are not concatenated.
- Stage 5's interpretation is a sidecar, `interpretations.jsonl` (§10.7), keyed by transition ID: `{"id": "T17", "action", "result", "description", "confidence", "refs": {"lines": ["16:l3", "16:l4"]}, "invalid_refs": 0, "model", "prompt_version", "error"}`.

### 10.3 `steps.jsonl`, `sections.jsonl`, `video.json`

```json
{"id": "S4", "level": "step", "children": ["T12", "T31"], "frames": [10, 44], "t": [38.1, 191.4],
 "label": "Configure the storage account", "description": "…", "refs": ["T13", "T15", "T20"], "segmentation_conf": "high"}
```

- `children` is an inclusive ID range over the level below (transitions for steps, steps for sections).
- `frames` = `[first child's from_frame, last child's to_frame]`; `t = [first child's t[0], last child's t[1]]`, so a step spans from the end of the state before its first action to the settling of its last result.
- `refs` lists the child IDs each sentence in `description` rests on; the prompt requires inline references (`[T13]`) and code validates that every referenced ID is within `children` (invalid ones are dropped and counted).
- `segmentation_conf` is `high`, or `low` when the level came from a fallback (§13.1).
- `video.json` has the same shape with `level: "video"` and `children` spanning all sections.

### 10.4 `outline.json`

```json
[{"id": "c1", "start_s": 0.0, "end_s": 312.0, "title": "Create the resource group", "gist": "…"}]
```

Chapter times are **model-produced** (Gemini's video clock at 1 FPS) — the one exception to R2's "never from a model", confined to this file. On read, `chapter_of(t)` snaps each boundary to the emitted frame whose stable interval contains it, so every consumer reasons in Stage 1 time; nothing copies these times into other files.

### 10.5 Coordinate convention

All stored boxes are `[x0, y0, x1, y1]` in **original-frame pixels** (the recording's native grid), integers, origin top-left. Any tool that saw a transformed image (an OCR engine with a dimension cap, a provider that resizes) has its boxes scaled back before storage. Apple Vision's normalized, bottom-left-origin boxes are converted at Stage 2a (§8.1) before anything is stored. Normalized (0–1) coordinates are not stored.

### 10.6 ID conventions

- Frames: integer, monotonically increasing per video, zero-padded to 5 digits in filenames only.
- OCR lines (marks): `l<n>` unique within a frame, assigned in reading order. Row lines keep their first mark's ID; VLM-only lines are `v<n>`, unique within a frame.
- Regions: `r<n>` unique within a frame; `r0` is the pseudo-region for unassigned lines. Regions are **not** tracked across frames in v1 (a window's `r` ID may differ between frames); cross-frame identity is the §11.1 assignment recorded on each transition.
- Transitions `T<n>`, steps `S<n>`, sections `C<n>`, outline chapters `c<n>`; all unpadded, unique per video (a two-hour video exceeds 1,000 transitions).
- Cross-file line references are `"<frame>:<line_id>"` (`"16:l3"`, `"16:v1"`); other references are plain IDs.
- Stage 1 is the only stage whose re-run invalidates the whole run: any change to its parameters renumbers frames, and every downstream ID is per frame. Content addressing of PNGs makes unchanged frames cheap to re-OCR, not their IDs stable.

### 10.7 Files and ownership

| File | Written by | Read by | Notes |
|---|---|---|---|
| `stage1.jsonl`, `frames/*.png` | Stage 1 | 2a, 2b, 2c, 3, 7 | one record per emitted frame (§7.6) |
| `ocr.jsonl` | Stage 2a | 2b, 3 | raw engine lines with word boxes |
| `overlays/*.png` | Stage 2b | 2c | |
| `perception.jsonl` | Stage 2c | 3 | raw VLM output + usage + repairs |
| `frames.jsonl` | Stage 3 | 4, 5, 6, 7 | canonical states (§10.1) |
| `transitions.jsonl` | Stage 4/4b | 5, 6, 7 | edges (§10.2) |
| `focus.jsonl` | Stage 4b | 5, 6, 7 | retrospective focus per frame: `{frame, focused_region, focused_conf, focused_signals}` |
| `interpretations.jsonl` | Stage 5 | 6, 7 | per transition |
| `steps.jsonl`, `sections.jsonl`, `video.json` | Stage 6 | 7 | |
| `outline.json` | Stage 0 (optional) | 5, 6, 7 | |
| `index.sqlite` | Stage 7 | agent | FTS5 + vector tables |
| `manifest.json` | runner | everyone | config hash, versions, per-stage usage/time, diagnostics (§18.4) |
| `cache/<key>.json`, `batches.json` | model client | model client | call cache; batch submission state (§20.7) |

`load_frames(run)` returns `frames.jsonl` records with `focus.jsonl` applied and `chapter_of()` available; `load_transitions(run)` returns transitions, and `load_interpretations(run)` the interpretations keyed by transition ID. Stages 5–7 use the loaders, never the raw files. A stage is skipped when the SHA-256 of its inputs and of its slice of the configuration are unchanged (§20.9).

---

## 11. Stage 4 — Line diff; Stage 4b — Transients, coalescing, trivial transitions, retrospective focus

Order of operations, per video: (1) region correspondence and line diff for every consecutive pair (§11.1–§11.2); (2) transient detection over triples (§11.4); (3) coalescing over the resulting sequence (§11.3); (4) trivial tagging (§11.2); (5) retrospective focus (§9.4) into `focus.jsonl`. Steps 2–4 produce `transitions.jsonl`.

### 11.1 Region correspondence across frames

Before diffing, match regions between frame *i* and frame *i+1*. Revision 1 matched by VLM-emitted names plus bbox IoU; names vary from call to call and text extents change whenever text is added (a terminal with one line and then thirty has IoU ≈ 0.03), so a miss turned every region into `appeared`/`disappeared` and Stage 5 lost the computed diff. Revision 3 scores every pair of regions that hold lines:

```
J     = |A ∩ B| / min(|A|, |B|) over the sets of normalized fused line texts   // containment, not Jaccard: a terminal growing
                                                                            // from 1 line to 31 keeps J = 1; 0 if either side is empty
IoU   = bbox intersection over union                                    // 0 if either bbox is null
s     = 0.5·J + 0.3·IoU + 0.1·[norm(app) equal] + 0.1·[norm(name) equal]
assignment: greedy one-to-one by descending s; accept s ≥ 0.3
regions with no lines: matched only to a region with no lines whose app and name both match
unmatched regions → appeared / disappeared events; unassigned_lines diffed as pseudo-region r0
```

The assignment and scores are recorded on the transition (§10.2).

### 11.2 Line-level diff (per matched region)

```
prev = [fused(line) for line in region_i.lines   in stored order]
cur  = [fused(line) for line in region_i+1.lines in stored order]
ops  = myers_diff(prev, cur)                       // insert / delete / equal runs (a small Myers implementation in the repo;
                                                   // Python's difflib uses a different algorithm with junk heuristics and is not used)
post-process adjacent (delete a, insert b):
    pair as modify(a → b) if boxes overlap vertically (|yc(a) − yc(b)| < 0.5·h)   // preferred signal
                          or similarity(a, b) ≥ 0.6
    for each modify, also compute a character-level diff within the line (char_diff, same Myers over characters)
clock ops: a modify whose old and new differ only inside a token matching \d{1,2}:\d{2}(:\d{2})?( ?[AP]M)? is tagged clock
```

- `fused(line)` is the fused text of §9.2; an op built from a line marked `uncertain` carries `uncertain: true`.
- Raw `delete/insert` ops are always stored; `modify` is a derived annotation. A mis-pairing therefore loses nothing — both readings remain — it only affects readability. Y-overlap is the stronger pairing signal on screens because a modified line stays put.
- **Why line-level:** the diff turns "the screen changed" into a short, exact op list a model would get wrong by eyeballing two dense screenshots, and a line is the natural unit of everything of interest (command, log line, list item, menu entry) and of OCR output. Character-level diff over a whole region yields "inserted `tus` at offset 87" — exact but meaningless to humans and models; it is used only *inside* a modified line.
- **Scrolling** is handled for free: shifted-but-identical lines align as `equal`; only genuinely new bottom lines are `insert` (and scrolled-off top lines `delete`).
- Lines are the **row lines** of §9.0, so an OCR engine's changing its mind about where a line breaks between two frames does not surface as a change.
- A transition whose ops are all `clock` ops (a taskbar or terminal clock ticking; ~14 per sample video, one per minute) is `kind: trivial` and skips Stage 5; it remains in `transitions.jsonl` so timing is complete.

### 11.3 Coalescing **[reasoned]**

Input: the sequence of consecutive transitions with their computed diffs, after transient resolution (§11.4). Output: a sequence of coalesced transitions, each covering `[first, last]`, with `events`; each coalesced transition's `computed_diff` is recomputed directly between its `from_frame` and `to_frame`.

- **Rule 1 — typed:** a maximal run of consecutive transitions whose ops restricted to region R are exactly one `modify(a → b)` on the same row with `lcp(norm a, norm b) ≥ len(norm a) − 3` (the tolerance absorbs a backspace and PowerShell's inline prediction text changing under the caret); ops in other regions are permitted only on lines with `in_churn = true` or tagged `clock`. Event `typed(text = b_final[len(lcp(a_first, b_final)):], line = b_final, region, frames = [first.from_frame, last.to_frame])`.
- **Rule 2 — output_appended:** a maximal run whose ops in R are `insert`s at the end of R's list, optionally with `delete`s at the start (scroll-off), other regions restricted as in Rule 1. Event `output_appended(lines = Σ inserted, text = concatenation, region, frames)`.
- **Rule 1b — command executed:** a Rule-1 run immediately followed in the same region by a Rule-2 run is **one** transition with events `[typed, output_appended]` (the §10.2 example).
- **Rule 3 (expected, not yet specified):** editor edits where the change is in the middle of a line, not a suffix. To be added after ground-truth review.
- `kind` of a coalesced transition is `unsettled` if any member transition is unsettled, else `coalesced`. An unsettled intermediate frame does not break a typed run.
- **Provenance:** the idea (aggregating keystrokes into a single "type" action; merging adjacent diff hunks) is prior art in GUI-agent datasets, RPA tooling, and diff tools; these specific rules were derived from how line diffs behave on terminals and must be validated (§18).
- **Effect on Stage 5:** coalescing decides which frame pairs Stage 5 examines. A typed command becomes one Stage 5 call on `(frame before typing, settled frame after)` with the typed string attached, instead of one call per keystroke pause. Settle already collapses most typing; coalescing catches pauses longer than S and incremental output.

### 11.4 Transients **[reasoned]**

For frames `i−1, i, i+1`: frame `i` is a transient if it has at least one region unmatched (§11.1) in both neighbours, that region's lines are absent from frame `i+1`, and `hold_s = t_change_{i+1} − t_change_i < T_transient`. Revision 1 additionally required every matched region's text to be equal between `i−1` and `i+1`, which rejected the common cases (a "Saved" toast next to a title-bar dirty-marker change; a toast during output).

- Frame `i` stays in `frames.jsonl`.
- Instead of two Stage 5 calls (`i−1 → i` "toast appeared", `i → i+1` "toast disappeared"), one transition `i−1 → i+1` (`kind: transient_merged`) is built with the normal computed diff between `i−1` and `i+1`, and Stage 5 receives frame `i` as a third image with the note "this region appeared for *h* seconds between them." Result: one edge such as "user pressed Ctrl+S; a 'Saved' toast confirmed it."
- Transients are resolved **before** coalescing; a transient-merged transition can be a member of a typed or output run.
- Transients with no text (spinner overlays) are handled by churn (§7.4), not here.

### 11.5 Unsettled frames

Transitions into or out of a frame with `settled=false` are `kind: "unsettled"`; Stage 5 is told the region was changing continuously and OCR inside churn is low confidence.

---

## 12. Stage 5 — Transition interpretation (VLM) (`interpretations.jsonl`)

One call per transition that is not `trivial`. Calls are independent of one another, so the stage is embarrassingly parallel and batchable (§20.7); revision 1 fed each call the previous calls' `action` fields, which made the stage sequential.

- **Inputs, in order, as content blocks:**
  1. Text: the outline preamble if `outline.json` exists ("Global outline: …; this pair falls inside chapter *k*: *title*", the chapter being the one containing `t_settled` of frame *b*), and the running context: the previous three transitions' computed events rendered as one line each (`T16 [f10→f11] Windows Terminal: typed "cd src"`), which exist before any Stage 5 call.
  2. Text: `Frame <a> (t=<t_settled_a>s):`; Image: `frames/<a>.png`.
  3. (If transient) Text: note; Image: transient frame.
  4. Text: `Frame <b> (t=<t_settled_b>s):`; Image: `frames/<b>.png`.
  5. Text: the computed diff and coalesced events rendered compactly (region name, ops, `uncertain` flags, `agree=false` lines shown with both readings, churn notes, `layout_conf < 0.5` regions listed as uncertain grouping, region correspondence).
  6. Text: the task instruction (§15.2 prompt contract).
- **Output schema:** `{action, result, description, confidence, refs:{lines:[…]}}`. `action` is inference (what the user did); `result` is observation (what changed as a consequence); `description` is free prose for anything else visible. Rules: cite line IDs as `"<frame>:<line_id>"`; do not restate diff text with alterations; when readings disagree, quote both and do not assert either.
- **Validation:** every ref must name frame *a*, *b*, or the transient frame and a line ID that exists there; invalid refs are dropped and counted in `invalid_refs` (a §18.2 metric). No re-prompt for refs in v1. Truncation and schema failures follow the §8.3 ladder; a refusal or final failure records `error` and the run continues.
- Images are sent at native resolution. Both frames are sent even when the computed diff is small, because non-textual changes (checkbox, highlight, selection, dialog) are only visible in pixels.

---

## 13. Stage 6 — Hierarchy (semantic segmentation)

Levels: transitions → steps → sections → video. Each level is produced by the **two-pass pattern** over the level below, text-only, carrying frame ranges forward.

### 13.1 Boundary call (pass 1)

- Input: the ordered list of level-*n* items, each rendered as one line, e.g. `T17 [f11→f16, 40.1–47.7s] Windows Terminal: typed "git status"; 2 lines appended` (steps rendered as `S4 [f10→f44] Configure the storage account`). For sections, the Stage 0 chapter boundaries, if present, are appended as a suggestion.
- Instruction: output the IDs at which a new sub-goal (steps) or topic (sections) begins, with a short label per segment: `[{start_id, label}]`. Ends are derived in code, so any output becomes contiguous, non-overlapping, and covering after sorting, de-duplicating, dropping unknown IDs, and forcing the first item to be a start. Re-prompt once — with a changed request, or the call cache would return the same answer — only if no valid start survives; on a second failure fall back to the Stage 0 chapter boundaries mapped to the first step starting at or after each chapter (sections, if the outline exists) or fixed windows (20 transitions per step; 8 steps per section) and flag the level `segmentation_conf: low`.
- Lists too long for one call: at a 1M-token context a two-hour video (~1,600 transitions at ~40 tokens each) fits one call, so the window is 2,000 items and windowing is effectively off for v1. When it does apply (overlap 200): keep every boundary found in a window's non-overlap zone; in an overlap zone keep boundaries found by both windows, else by the window in which the boundary lies ≥ 25 items from an edge.

### 13.2 Elaboration call (pass 2)

- Per segment: input is the child items in full (their `action`/`result`/`events` for transitions; `label`/`description` for steps), plus the merged states at the segment's first and last frames (region names and focused window only, not full line lists).
- Output: `{label, description, refs}` with inline child references. Validate every referenced ID ∈ `children`; invalid refs are dropped and counted.
- If a single segment's children exceed the call budget, apply **map-reduce within the segment**: chunk children by token count; summarize each chunk (map, parallel); summarize the chunk summaries (reduce); recurse if the concatenation still doesn't fit. Boundary effects (an event straddling a chunk) are accepted at this level because segments are already semantically coherent. The **refine** pattern is not used (early errors persist; drift).

### 13.3 Frame-range and time propagation (R3)

`frames` and `t` are computed by code from children, never by the model: `frames = [children[0].from_frame, children[-1].to_frame]`, `t = [children[0].t[0], children[-1].t[1]]` (§10.3). Because every sentence carries child references and every child carries its own range, any sentence at any level can be walked down to specific frames and PNGs.

---
## 14. Stage 7 — Index and retrieval

### 14.1 Nodes

Every node from every level is a retrieval document: frame states (one document per region that holds lines — its fused text plus the VLM reading of every `agree = false` line, so a query hits whichever reading is right — plus one per frame `description`), transitions (computed events plus interpretation), steps, sections, the video summary, and Stage 0 outline entries. Each document carries metadata: `video_id`, `level`, `id`, `frames`, `t`, `apps`, `region_names`, `layout_conf` (min over involved regions), `step_id`, `section_id`, `chapter_id`. The index contains whatever was on screen — including identifiers such as subscription IDs and tenant domains visible in the sample — with no redaction in v1 (§22).

### 14.2 Indexes

- **Lexical** (SQLite FTS5, present in Python's bundled SQLite **[measured]**): exact strings — commands, identifiers, resource names. This is the reason R1 matters at query time. The FTS5 table uses `tokenize = "unicode61 tokenchars '-_./:\'"` so that `--resource-group`, `aks-demo-01`, and `C:\src\app.py` are single tokens, plus a `trigram` companion table for substring matches (`KodeKloud` inside `RG1-KodeKloud-AKS`) **[measured: both work on SQLite 3.53]**. Consequences the query builder must honour **[measured]**: every term is emitted as an FTS5 phrase (`"..."`, inner quotes doubled) — an unquoted `-` is FTS5's NOT and `aks-demo-01` unquoted is parsed as a column reference; trigram queries only for terms of ≥ 3 characters; both tokenizers fold case, so exact-case verification is done against the stored payload, not the index; ranking via `bm25()`.
- **Vector** (embeddings, stored in `sqlite-vec` in the same database file **[measured: loads on macOS arm64]**): semantic questions ("where did they set up authentication"). The embedder is pluggable; the v1 default is `none` (lexical retrieval only), because the local ONNX embedder (`fastembed`) downloads its model from Hugging Face on first use and that CDN was unreachable from the development machine when v1 was built (a transient network fault) **[measured]**, and no hosted-embedder key is configured. `scry setup` pre-fetches the embedder model when one is configured and records its hash in the manifest; the vector table and fusion path are built regardless so switching the embedder on is a configuration change.
- **Collapsed-tree retrieval:** both indexes hold all levels in one pool; a query retrieves top-k across levels with reciprocal-rank fusion (constant 60) of lexical and vector results. Metadata filters (video, app, time range) are applied **inside each index before top-k** (a `WHERE` on the nodes join for FTS5; metadata columns in the KNN `WHERE` for sqlite-vec), with k raised from 20 to 50 when filters are set, so a filtered query never fuses an empty list. Region/app names from `layout_conf < 0.5` frames are soft boosts only.

### 14.3 Answering agent

Tools: `search(query, filters)`, `get_node(id)`, `get_transitions(video_id, t_a, t_b)`, `get_frame(video_id, frame)` (returns the PNG as an image), `redecode(video_id, t_a, t_b, fps)` (Stage 1 recovery tool, §7.7). The agent iterates search → read → (optionally) look at frames → answer, and must cite frame IDs and times for every factual claim. Exact-text answers are quoted from `agree=true` lines; where `agree` is `false` or `null`, both readings (or the single reading, marked as unverified) are shown.

This is the same navigate-with-tools pattern as Gemini's agentic mode, applied at the layer where the data is high-resolution and pre-indexed, so per-question cost is text retrieval plus at most a few frame images rather than re-watching video.

---

## 15. Prompt contracts

Prompts are contracts: a system prompt defining each output field, a JSON schema with per-field descriptions, and one worked example. Model behavior depends on these definitions, not on field names. Each prompt carries a `prompt_version` recorded on every output record.

### 15.1 Stage 2c — grouping and transcription

Core instructions (paraphrased contract; exact wording lives in the repo):

1. You are shown the same screenshot twice: Image 1 is the clean frame; Image 2 has numbered boxes drawn around detected text lines, with each number placed beside its box (the numbers are not part of the screen's text). Transcribe from Image 1; use Image 2 only to know which number refers to which line.
2. Group every numbered line into a tree of regions: windows, panes within windows, and popups. Name each region and identify its application. Every number must appear in exactly one row of exactly one region or in `unassigned_line_ids`.
3. Within a region, list its **rows** in reading order. A row is one visual line: text that sits on one line (a prompt and its command, a table's cells, tabs side by side) is one row, listed left to right; a line the boxes missed is an empty row `[]`. For each row give its text **verbatim** in `vlm_lines` — one entry per row. Preserve case, punctuation, whitespace, and symbols. Never correct, complete, or normalize commands, code, paths, or identifiers. Use `?` for any character you cannot resolve. Do not omit rows. Icons are not text: do not transcribe them.
4. Identify the focused window; give a 0–1 confidence and list the visual cues used. List the regions each region visually covers in `occludes`.
5. In `description`, state anything the row list cannot express: selections, highlights, toggles, icons, diagram relationships, dialogs.
6. Regions listed as animating (churn) are low confidence; say so rather than guessing.

### 15.2 Stage 5 — transition interpretation

1. You are shown two consecutive screen states (and optionally a transient state between them) and an exact computed list of text changes. The computed list is authoritative for text; do not restate its strings with alterations.
2. `action`: the single user action that best explains the change (typed, clicked, selected, navigated, pressed a key). If none is evident, say so.
3. `result`: what visibly changed as a consequence, including non-textual changes visible in the images.
4. Where two readings of a line disagree, quote both; assert neither.
5. Reference the line IDs your statements rest on, as `"<frame>:<line_id>"` using the frame numbers given.

### 15.3 Stage 6 — boundary and elaboration

Boundary: "Output only the IDs at which a new sub-goal begins, with a label for the segment that starts there. A sub-goal is a coherent unit of work a tutorial reader would follow as one step." Elaboration: "Describe this segment for a reader who will follow it. Every sentence must carry the IDs it rests on in brackets. Quote commands exactly as given; do not paraphrase them."

### 15.4 Stage 7 — answering

"Answer only from retrieved material. Cite frame IDs and times for every claim. Quote exact text only from lines marked agree=true; otherwise present both readings, or mark a single reading as unverified. If the material does not answer the question, say so and suggest which time range to inspect."

---

## 16. Parameters

All are initial values to be tuned on the ground-truth set (§18.1); until then, the Stage 1 values are validated on the synthetic fixtures of §18.4. Pixel thresholds are UI-element sizes at the recording's native resolution and **do not change with recording resolution**; the half-resolution column applies only when detection runs on the 2×2-max-reduced map (§7.2).

| Parameter | Value | Half-res | Where | Meaning |
|---|---|---|---|---|
| `θpix` | 12 | 12 | §7.2 | Luma delta for a pixel to count as changed (ignores codec noise) |
| `θmin` | 8 px | 3 px | §7.2 | Minimum changed-pixel count for a component to survive noise filtering |
| dilation | 3×3 | 3×3 | §7.2 | Merges the strokes of one glyph into one component (no opening) |
| bar caret | width ≤ 3 px, height 8–30 px | ≤ 2, 4–15 | §7.2 | Bar-shaped components never trigger |
| `θcomp` | 24 px | 10 px | §7.2 | One connected component of at least this area triggers a change |
| `θcount` | 100 px | 40 px | §7.2 | Total component area that triggers a change |
| `S` | 400 ms | — | §7.3 | Stillness required before emitting |
| `M` | 3 s | — | §7.3 | Max hold and churn tick: emit even if never still |
| `W` | 5 s (= W·fps maps) | — | §7.4 | Churn window |
| `ρ_on / ρ_off` | 0.5 / 0.2 | — | §7.4 | Per-pixel churn hysteresis (fraction of window frames changed) |
| churn min area | 400 px | 100 px | §7.4 | Minimum component area to become a churn region |
| blink candidate | bbox ≤ 12×32 px | ≤ 6×16 | §7.5 | Component size eligible for blink tracking |
| blink confirmation | ≥ 2 recurrences, 0.15–0.7 s apart, within 3 s; IoU ≥ 0.5 | — | §7.5 | |
| blink expiry | 2 s without recurrence | — | §7.5 | |
| detection resolution | full (downsample 1) | — | §7.2, §20.2 | Half-resolution is a speed option |
| word grouping | 0.5 × median word height | — | §8.1 | Vertical tolerance for words joining a line (word-only engines) |
| OCR engine | Vision: accurate, language correction off, `en-US`, auto-detect off, `minimumTextHeight` 0 | — | §8.1 | Recorded in the run manifest |
| label font / placement | 10–12 px; right, left, above, below; never inside | — | §8.2 | |
| row sanity | y-centres within 0.5 × median line height; neighbour gap ≤ 3 × line height | — | §9.0 | Rejects an implausible VLM row |
| align similarity | ≥ 0.8, or (len ≤ 8 and Levenshtein ≤ 1) | — | §9.2 | OCR↔VLM alignment predicate (repair path) |
| glyph strip | one leading/trailing token of ≤ 2 chars | — | §9.2 | Icon-glyph agreement rule |
| `layout_conf` penalties | −0.3 per interleaved region (cap 0.6); −0.2 if row coverage < 0.3; cap 0.6 singleton; cap 0.5 no bbox | — | §9.3 | |
| focus combination | 0.9 / 0.7 / 0.6 / 0.6 / 0.5 / null | — | §9.4 | |
| region correspondence | s = 0.5·J + 0.3·IoU + 0.1·app + 0.1·name (J = text containment); accept ≥ 0.3 | — | §11.1 | Cross-frame region matching |
| modify pairing | y-overlap (0.5·h) or similarity ≥ 0.6 | — | §11.2 | Delete+insert pairing |
| typed tolerance | lcp ≥ len(a) − 3 | — | §11.3 | Backspace / inline-prediction tolerance |
| `T_transient` | 2 s | — | §11.4 | Max hold for a transient |
| boundary window | 2,000 items, 200 overlap | — | §13.1 | Long-list segmentation (effectively off) |
| fixed-window fallback | 20 transitions per step; 8 steps per section | — | §13.1 | Only after two failed boundary calls |
| retrieval k / RRF | 20 (50 with filters) per index; constant 60 | — | §14.2 | |
| effort | Stage 2c `low`, Stage 5 `low`, Stage 6 `medium`, Stage 7 agent `high` | — | §20.7 | `output_config.effort`; governs thinking-token spend |
| `max_tokens` | 16,000 (retry once at 32,000 on truncation) | — | §20.7 | |

---

## 17. Failure modes and mitigations

| Failure | Where | Consequence | Mitigation / recovery |
|---|---|---|---|
| Missed change below threshold | §7.2 | Change appears at next emitted frame, bundled and with coarser timing | Absolute pixel count + connected-component test; `redecode` tool; measure detection recall on ground truth |
| Thin text strokes erased by noise filtering | §7.2 | Keystrokes never trigger; commands surface only with their output | Dilation + minimum-area filter instead of morphological opening; synthetic typing fixture in unit tests (§18.4) |
| Spurious emitted frames (noise, clock digits) | §7.2 | Token cost only | `θmin`; `θpix` tuned on the recorded codec; `clock` ops → `trivial` transitions skip Stage 5 |
| Block or underscore cursor blinks above threshold | §7.5 | Screen never settles; every state a max-hold | Blink tracker; bar carets excluded by shape; `t_settled` corrected on confirmation |
| Screen never settles (spinner, playing video, scrolling log) | §7.3–§7.4 | Frames delayed; mid-animation frames | Churn mask (unmasked ring buffer, per-pixel hysteresis); churn tick every `M`; deactivation rule captures the end state; `settled=false` tagging |
| Video ends mid-change | §7.3 | Final state lost | End-of-stream flush |
| Max-hold frame was in fact the end state | §7.3 | State recorded as unsettled | In-place upgrade on settle confirmation |
| Typing pause splits a command | §7.3 | Two frames for one command | Coalescing Rule 1 |
| OCR garbles small monospace text or confusable glyphs | §8.1 | Wrong characters (`maln`, Cyrillic `е` in a GUID) | Engine bake-off; VLM cross-check; `agree` flag; `confusable` flag; vote across frames where the string persists |
| OCR confidence uninformative (Vision reports 1.0 everywhere) | §8.1 | No per-engine signal | No rule depends on `ocr_conf`; `agree` is the signal |
| OCR splits or merges visual lines inconsistently between frames | §9.0 | Spurious diff ops; failed alignment | VLM-proposed rows with geometric sanity check |
| Icon glyphs transcribed by OCR, not by the VLM | §9.2 | `agree=false` on every icon-prefixed UI line | Glyph-strip agreement rule |
| Overlay labels occlude text | §8.2 | VLM "completes" occluded characters | Two images (clean + overlay); never-inside placement; `label_clashes` counted |
| VLM paraphrases or "corrects" code | §8.3 | Plausible-but-wrong text | Verbatim contract; `?` convention; OCR cross-check; treat `agree=false` as uncertain |
| VLM omits lines | §8.3 | Missing text | OCR-only lines retained with `vlm=null` |
| OCR misses lines (no mark) | §8.1 | No box; grouping by VLM only | VLM-only lines (`v<n>`) retained with `ocr=null`, `bbox=null` |
| Wrong grouping (line assigned to wrong window) | §8.3 | Wrong region label | Fusion is independent of window grouping; `layout_conf`; `unassigned` fallback; sample low scores |
| VLM proposes an implausible row | §9.0 | Garbled joined line | Row sanity check splits it; `rows_rejected` counted |
| Overlapping/occluding windows | §8.3 | Membership ambiguity near edges; background window's union bbox encloses foreground | `occludes` relationships excluded from `layout_conf`; boxes used for filtering only, never for assignment; the sample has an overlapping-window segment |
| Text on canvases / diagrams | §8.3 | Line list loses spatial relations | `description` field; v2 screen parsing |
| Model-emitted coordinates | — | Approximate / wrong coordinate space | Not used (D4) |
| Provider downscales image | §5.3 | Small text lost | Native-resolution check per model; 4K excluded in v1; overlay never enlarges the frame |
| VLM output truncated or schema-invalid | §8.3, §12 | Lost frame/transition | Retry ladder; repair by code; `error` recorded; run continues |
| Region correspondence misses | §11.1 | Diff lost for a window | Text-Jaccard scoring; assignment recorded |
| Mis-paired modify | §11.2 | Readability only | Raw ops always stored |
| Coalescing rule over- or under-merges | §11.3 | Wrong event granularity | Rules are validated; Rule 3 pending; Stage 5 sees frames either way |
| Transient misclassified | §11.4 | Extra or merged edge | Frame retained; only Stage 5 call structure changes |
| Stage 5 cites lines that do not exist | §12 | Untraceable claim | Refs validated; invalid refs dropped and counted |
| Boundary call returns invalid segmentation | §13.1 | Bad steps/sections | Repair in code; re-prompt; fallback with `segmentation_conf: low` |
| Long-context quality degradation | §13.2 | Vague summaries | Map-reduce within segment; keep calls small |
| Stage 0 outline conflicts with frame evidence | §6 | Wrong global context | Frame evidence wins by rule; outline is read-only and optional |
| Focus inferred wrongly | §9.4 | Wrong "focused" label | Computed signals preferred; downstream must not depend hard on focus |
| Batch exceeds the 256 MB cap or fails mid-poll | §20.7 | Lost or duplicated calls | Size-chunked batches; `batches.json` resume; errored/expired results re-queued |
| Thinking tokens blow the cost estimate | §19.6 | Unexpected spend | Per-stage `effort`; usage summed into the manifest |
| Model regression after provider update | all VLM stages | Silent quality drop | Harness re-run on calibration set per model change; pin model versions |

---

## 18. Evaluation plan

### 18.1 Ground-truth set (hand-created by the owner; not part of v1 implementation)

- **Two full videos** (30–60 min each), chosen to include: terminal work, an editor, a browser portal with a left navigation and content blade, Notepad, at least one dialog, and **one segment with overlapping windows** (the sample video has one at ~10 min).
- **Hand-transcribed commands** and other exact strings (every command run, every value typed into a field), with the time they were entered; include at least one GUID and one URL.
- **A hand-marked state-change list** with times, for ≥ 5 minutes of each video (Stage 1 precision/recall and `t_change` timing error need it).
- **End-state labels** for every emitted frame in those spans (settle metric).
- **An action list** (clicks, scrolls, key presses, not only typed text) for the same spans (coalescing metric).
- **A hand-written step list** with boundaries (time) and labels.
- **A 20-frame calibration subset** with fully hand-transcribed screen text per region and a focused-window label per frame, used for model and OCR bake-offs and the focus metric.
- **A question set** (20–40 questions) with reference answers and the frame ranges that justify them.

### 18.2 Metrics, per component (R5)

| Component | Metric |
|---|---|
| Stage 1 detection | Recall and precision of emitted frames against the hand-marked change list; timing error (ms) of `t_change` |
| Stage 1 settle | Fraction of emitted frames that are end states (not mid-animation) |
| OCR alone | CER on commands; line recall; fragment stability (fraction of unchanged rows whose OCR line count differs between consecutive frames) |
| VLM transcription alone | CER on commands; line recall; paraphrase rate (normalized-equal but not exact) |
| Fused (`agree=true` lines) | CER; coverage (fraction of ground-truth strings with an `agree=true` line) |
| Rows and grouping | Fraction of rows matching hand rows; fraction of lines assigned to the correct window/pane; `layout_conf` correlation with errors |
| Focus | Accuracy vs hand labels, split by signal source |
| Coalescing | Event precision/recall against the hand action list |
| Stage 5 | Human-rated action/result correctness on a sample; citation validity (`invalid_refs` rate, and refs support the claim) |
| Stage 6 steps | Boundary agreement with the hand step list (WindowDiff or F1 with ±1 transition tolerance); label adequacy (human) |
| Stage 6 with vs without Stage 0 | Boundary agreement delta |
| Stage 7 | Answer accuracy on the question set; citation correctness; exact-string accuracy for command questions |

### 18.3 Bake-offs

1. OCR engines: Apple Vision vs RapidOCR on the 20-frame set (Windows.Media.Ocr too if a Windows machine is available).
2. VLMs: within the Anthropic provider in v1 — `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5` — on the 20-frame set (transcription CER, grouping accuracy, cost per frame, latency); other vendors when a second provider exists (D15).
3. Ensemble ablations: each switchable stage off, one at a time, against the full pipeline.
4. Effort: Stage 2c and Stage 5 at `low` vs `medium` on the 20-frame set.

### 18.4 Before ground truth exists: unit fixtures and run diagnostics

Ground truth is hand-made and arrives later; v1 still has to be checkable. Two mechanisms, both in the repository from day one:

- **Synthetic fixtures (unit tests, no video, no network):** rendered frame sequences that exercise Stage 1 — a typing sequence in a 15-px monospace font with a blinking 2-px bar caret (every keystroke must trigger; the caret must not; `t_settled` must equal the first still frame), the same with a 9×18 block cursor, a scrolling region under a static header (churn must activate; ticks every `M`; the end state must be emitted with the right `t_settled`), a flash that reverts within `S` (nothing emitted), a max-hold frame that turns out to be the end state (upgraded in place), a video ending mid-change (flushed), and a clock digit change (`trivial`). Hand-written line lists exercise rows, alignment, `layout_conf`, correspondence, Myers, modify pairing, coalescing Rules 1/2/1b, and transients. Prompt contracts are exercised with recorded model responses (no live calls).
- **Ground-truth-free diagnostics** written to `manifest.json` on every run: emitted-frame count and settled fraction; lines per frame; `agree=true`, OCR-only, and VLM-only fractions; `rows_rejected`, `grouping_repairs`, `label_clashes`; schema/ID validation failure and retry counts; `invalid_refs` rate; fragment stability; per-stage tokens, cost, and wall time; cache hit rate; refusal count. These are the numbers to look at after the first run on the sample video.

---

## 19. Cost and performance model

### 19.1 Unique-frame estimate

A 30-minute tutorial with typical activity yields on the order of 100–400 emitted frames after settle. This is the number that drives all per-frame costs; measure it on the sample first (the 14.2-minute sample is expected to yield 100–250).

### 19.2 Per-frame perception

- Visual tokens per frame (§5.3): ~2,700 (1080p) or ~4,800 (1440p) on Claude. Stage 2c sends **two** images (clean + overlay, §8.3), so ~5,400 / ~9,600 visual tokens, plus prompt and output text (~1–3k tokens) plus thinking (§19.6).
- OCR: local; Apple Vision at the accurate level takes 0.07–0.28 s per real 1080p frame **[measured]**.
- One VLM call per frame; parallelizable up to provider rate limits.

### 19.3 Transitions

Roughly one Stage 5 call per non-trivial coalesced transition, ≤ number of emitted frames; each sends two (occasionally three) frames, so ~2× per-frame image cost plus text.

### 19.4 Hierarchy and index

Text-only; a few dozen calls per video (one boundary call per level, one elaboration call per segment, map-reduce only for oversized segments). Negligible relative to Stages 2 and 5.

### 19.5 Alternatives considered for batching

- **Single-call whole video** (all emitted frames in one request): ~300 frames × ~2.5k ≈ 750k tokens; fits 1M-context models but is expensive per call and multimodal quality degrades at very long contexts. Rejected for v1; the pairwise design has no batching problem because no call is long.
- **Batches with overlap and carry-forward summary:** the general fallback if any stage ever needs multi-frame context beyond a pair — overlap by one or two frames so a boundary-straddling transition is visible to both batches, and include the previous batch's output as text so later batches know the context. Not needed in v1.

### 19.6 Dollar estimate at current Claude prices

List prices on 2026-09-13: `claude-opus-5` $5 / $25 per million input / output tokens; `claude-sonnet-5` $2 / $10; `claude-haiku-4-5` $1 / $5. **Thinking tokens bill as output**, and Opus 5 thinks by default; `output_config.effort` per stage (§16) bounds them, and the estimate below assumes ~1k thinking tokens per call at `low` — to be replaced by `usage` from the first run.

Per 1080p frame on Opus 5, Stage 2c: ~5.4k visual + ~2k text input (≈ $0.037) and ~1.5k output + ~1k thinking (≈ $0.063), so ≈ $0.10 per frame. Stage 5: ~5.4k visual + ~2k text (≈ $0.037) and ~0.5k output + ~1k thinking (≈ $0.038), so ≈ $0.075 per transition. A 300-frame video is therefore ≈ $30 + $22 + a few dollars for Stage 6 ≈ **$55 on Opus 5**, ≈ $22 on Sonnet 5; the sample video (100–250 frames) ≈ $18–45. 1440p costs ≈ 1.3× (visual tokens rise 1.8×; output tokens do not). The Message Batches API halves all of it for offline runs (§20.7); prompt caching of the fixed system prompt and schema removes most of the repeated text cost.

### 19.7 Local inference option

If per-frame API cost dominates at corpus scale, Qwen3.5 (or a successor) on a local GPU removes the per-token cost for Stage 2c/5; the harness decides whether quality is acceptable.

---

## 20. Implementation notes (Python on macOS)

### 20.1 Toolchain (verified on the dev machine, 2026-09-13)

| Component | Choice | Verified |
|---|---|---|
| OS / CPU | macOS 26.3, Apple Silicon (arm64) | — |
| Language | Python ≥ 3.12 (3.14.6 in use); `uv` for the virtual environment and lockfile | resolves and runs on 3.14 |
| Decode | `av` (PyAV 18, bundled FFmpeg) | decodes the sample at ~535 fps grayscale |
| Pixels | `numpy` 2.5, `scipy` 1.18 (`ndimage.binary_dilation`, `ndimage.label`, `ndimage.find_objects`) | ~5 ms per 960×540 frame for dilation + labeling |
| OCR | `pyobjc-framework-Vision`, `pyobjc-framework-Quartz` (Apple Vision); `rapidocr-onnxruntime` as an optional extra | Vision: 0.07–0.28 s per real 1080p frame; RapidOCR: runs, weaker |
| Images | `pillow` 12 (PNG I/O, overlay drawing) | — |
| Text similarity | `rapidfuzz` (normalized Levenshtein); Myers diff implemented in the repo | — |
| Models | `anthropic` 1.5 (`AsyncAnthropic`, `messages.parse`, Batches, Files); `pydantic` 2 for every schema | `parse` accepts `output_format` and `output_config` |
| Index | `sqlite3` with FTS5 (bundled); `sqlite-vec` 0.1.9; `fastembed` (local ONNX embeddings, optional, needs a model download) | FTS5 and `sqlite-vec` load; `fastembed` blocked by network here |
| CLI / tests | `typer`; `pytest` | — |

Not used, and why: OpenCV (D14); a system `ffmpeg` (D14); `difflib` for the op list (§11.2); JPEG anywhere (§7.1).

### 20.2 Decode (§7.1)

`av.open(path)`; `stream = container.streams.video[0]`; `stream.thread_type = "AUTO"`; iterate `container.decode(stream)`; `t = float(frame.pts * stream.time_base)` with the `pts is None` guard; `gray = frame.to_ndarray(format="gray")`; on emit, `frame.to_image().save(png, compress_level=1)` (≈ 350–570 KB per 1080p frame **[measured]**). Half-resolution mode keeps the full-resolution grayscale and thresholds at full resolution; only the boolean change map is reduced with a 2×2 max (`changed.reshape(h//2, 2, w//2, 2).any(axis=(1, 3))`) before dilation and labeling, so 1-px strokes survive (§7.2). Full-resolution detection runs at roughly 44 fps on frames with change and much faster on static stretches **[measured]**, so the sample takes 5–10 minutes. Duration from `container.duration` (microseconds).

### 20.3 Change detection, churn, blink tracker (§7.2–§7.5)

`changed = np.abs(cur.astype(np.int16) − prev) > θpix`; `blobs = scipy.ndimage.binary_dilation(changed, structure=np.ones((3,3)))`; `labels, n = scipy.ndimage.label(blobs, structure=np.ones((3,3)))`; per-component changed-pixel counts `np.bincount(labels[changed])`; bboxes from `scipy.ndimage.find_objects(labels)`. Churn: ring buffer of `np.packbits(changed)` rows, a running `uint16` count per pixel, a persistent boolean mask, an `int32` `last_change` frame index per pixel; churn bboxes from `find_objects` over the labeled `dilate(open(mask))`. Blink tracker: a small list of candidate bboxes with their recurrence times. All of Stage 1 is one process; decode and detection run in the main loop, PNG encoding in a small thread pool; records are buffered until `t_end`.

### 20.4 OCR (§8.1)

Apple Vision through PyObjC:

```python
import Vision, Quartz, Foundation
src = Quartz.CGImageSourceCreateWithURL(Foundation.NSURL.fileURLWithPath_(png), None)
cg = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
req = Vision.VNRecognizeTextRequest.alloc().init()
req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
req.setUsesLanguageCorrection_(False)
req.setRecognitionLanguages_(["en-US"])
req.setAutomaticallyDetectsLanguage_(False)
handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, None)
ok, err = handler.performRequests_error_([req], None)
for obs in req.results():
    cand = obs.topCandidates_(1)[0]           # cand.string(), cand.confidence()
    box = obs.boundingBox()                    # normalized, origin bottom-left → §8.1 conversion
    rect, err = cand.boundingBoxForRange_error_(Foundation.NSMakeRange(start, length), None)  # word boxes
```

The calls above ran on the dev machine **[measured]**; throughput makes a process pool unnecessary, and if one is ever used on macOS it must use `multiprocessing.get_context("spawn")` (forking after Objective-C initialization crashes). RapidOCR adapter: `RapidOCR()(png) → [(quad, text, conf), …]`. Engine and settings are recorded in the run manifest; a change to either invalidates Stage 2a's cache.

### 20.5 Overlay (§8.2)

Pillow `ImageDraw.rectangle` (width 1) and `ImageDraw.text` with `ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 11)` on an RGBA layer for the 50 %-alpha backing; fall back to Pillow's default bitmap font if the path is absent. Slot selection tests the label rectangle against every OCR box; the output PNG has the frame's exact dimensions.

### 20.6 Diff and similarity (§9.2, §11)

A Myers O(ND) implementation over lists of strings produces `equal`/`insert`/`delete` runs; the same function over lists of characters produces `char_diff` inside a `modify`. `rapidfuzz.distance.Levenshtein.normalized_similarity` and `.distance` implement the predicates. `norm()` is a pure function shared by §9.2 and §11.2.

### 20.7 Model calls (§8.3, §12, §13, §14.3)

- **Client:** `anthropic.AsyncAnthropic()` (credentials from the environment or an `ant auth login` profile); concurrency bounded by an `asyncio.Semaphore` sized from the account's rate limit; the SDK's own retries handle 429/5xx.
- **Structured output:** `client.messages.parse(model=…, system=…, messages=…, output_format=SomePydanticModel, output_config={"effort": …}, max_tokens=16000)`; `response.parsed_output` is the validated model. Field descriptions on the pydantic models *are* the prompt contract (§15).
- **Effort:** `output_config.effort` per stage (§16). Opus 5 thinks by default; `effort` bounds the spend. `usage.output_tokens` (which includes thinking) is summed per stage into the manifest.
- **Content layout:** for each image, a text block (`"Image 1 (clean frame 12, t=47.72s):"`, `"Frame 16 (t=52.10s):"`) followed by the base64 PNG image block, then the diff/context text, then the task instruction — images before the text that refers to them, each labeled (§5.2). Models never see filenames or metadata.
- **Caching:** the system prompt and schema are byte-identical across calls of a stage, so the system block carries `cache_control: {"type": "ephemeral"}`; volatile content (frame labels, diffs) comes after it. The minimum cacheable prefix is model-dependent (512 tokens on Opus 5); if a stage's system block is shorter, pad it with the §15 worked example. Verify with `usage.cache_read_input_tokens` in the run log.
- **Model pinning and provenance:** model ID, prompt version, and schema hash are recorded on every output record and in the manifest.
- **Call cache:** every request is keyed by SHA-256 of `(stage, model, effort, max_tokens, prompt_version, schema_hash, input_hashes)` and stored on disk (`cache/<key>.json`, request + response + usage); a re-run with unchanged inputs makes no API calls (R6). Only terminal outcomes are cached — a parsed result, a refusal, or a schema failure after its retry; transient API errors are not, so a re-run repairs them.
- **Batch mode:** Stages 2c and 5 are offline and embarrassingly parallel, so they can be submitted as Message Batches at 50 % of list price with up to 24 h latency. A batch is capped at 256 MB and 100,000 requests; a Stage 5 request carries two or three ~0.5 MB base64 PNGs, so a video's Stage 5 (~300 requests ≈ 350–550 MB) is chunked by serialized size (≤ 200 MB per batch). `runs/<id>/batches.json` records `{batch_id, custom_ids, status}` so an interrupted poll resumes instead of resubmitting; `custom_id` = the 64-hex cache key **[verify the 64-character limit and charset]**; `errored`/`expired`/`canceled` results are re-queued into the next batch (an `invalid_request` error goes to the manifest and the record gets `error`); results populate the same cache, so downstream stages are unchanged. Uploading each PNG once via the Files API and referencing `file_id` would shrink batch payloads to text size **[verify that file references are accepted inside batch requests]**. The server-side `fallbacks` parameter is rejected on the Batches API. Synchronous mode is the default for development.
- **Refusals:** `stop_reason == "refusal"` is recorded on the frame/transition (`error: "refusal"`) and the pipeline continues; server-side fallbacks are a configuration option for synchronous mode.

### 20.8 Portability

Everything except the OCR adapter is platform-neutral. Linux: select the RapidOCR engine (or another ONNX engine) in configuration; Vision is skipped. Windows: select a Windows.Media.Ocr adapter (via the `winocr` package or a small .NET helper process **[verify]**). The engine is a configuration key, never an import-time decision, so a run manifest states which engine produced each `ocr` field.

### 20.9 Idempotency, manifests, configuration (R5, R6)

- One TOML configuration file holds every parameter in §16, the OCR engine and settings, the model IDs, the effort levels, and the prompt versions; it is loaded into a pydantic model and its hash is recorded in the run manifest (`runs/<video_id>/manifest.json`, which also records library versions, the video's SHA-256, per-stage token usage and wall time, and the §18.4 diagnostics).
- Each stage reads other stages' files and writes only its own (§10.7); a stage is skipped when the SHA-256 of its inputs and of its slice of the configuration are unchanged. Frames are content-addressed by SHA-256 as well as numbered.
- Stage boundaries are the switch points R5 requires: any stage can be re-run with a different engine, model, or prompt and compared on the same inputs.

### 20.10 Index and retrieval (§14)

One SQLite file per corpus: a `nodes` table (metadata as columns, JSON payload), an FTS5 virtual table over the text with the tokenizer settings of §14.2, a `trigram` FTS5 table, and a `sqlite-vec` virtual table over embeddings (empty when the embedder is `none`). A query builder emits phrase-quoted terms and applies metadata filters inside each index; reciprocal-rank fusion is a few lines of Python over the ranked lists. The answering agent is a tool-use loop over the Anthropic SDK (`search`, `get_node`, `get_transitions`, `get_frame` returning the PNG as an image block, `redecode`).

### 20.11 Command line

One entry point, `scry`: `scry run <video> --out runs/<id>` executes every stage in order; `scry decode | ocr | overlay | perceive | merge | diff | interpret | hierarchy | index` run one stage on an existing run directory; `scry ask "<question>"` runs the agent over an index; `scry setup` pre-fetches optional models (embedder) and checks the environment (Vision available, FTS5 present); `scry subset <run> --out <dir> --frames A-B` derives a run directory holding only Stage 1 frames A..B (Stage 1 marked done, call cache shared with the source) so the model stages can be exercised live on a few frames before a whole video is paid for. Every command is idempotent (§20.9).

### 20.12 Repository layout

```
docs/                  this design; implementation plan; decision ledger
src/scry/                package: config, stage modules (decode, detect, ocr, overlay, perceive, merge, diff, coalesce, interpret, hierarchy, index, agent), providers/, schemas/
tests/                 unit tests over synthetic frames and hand-written line lists (no video, no network)
runs/                  per-video outputs (git-ignored)
assets/                sample video(s)
```

---
## 21. v2 roadmap

1. **Record-time capture (highest value where possible).** If future recordings can be influenced, capture the OS accessibility tree (UI Automation on Windows, `AXUIElement` on macOS — whichever OS the *recording* machine runs) and input events (keystrokes, clicks with coordinates) alongside the video. This replaces Stages 2–4 for those videos with exact data and reduces the vision pipeline to verification.
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

1. Which OCR engine and which VLM (and which effort level) win on the 20-frame set, and at what cost per frame?
2. Actual emitted-frame counts per hour of tutorial, by content type; the sample's count is the first data point.
3. Whether `θpix` and `θmin` need per-video calibration based on codec noise (the sample's I-frame residuals are ≤ 8 px; other encoders may differ).
4. How often coalescing Rules 1–2 mis-merge, and what Rule 3 should be.
5. Whether Stage 0 measurably improves step boundaries (§18.2 delta) or can be dropped.
6. Whether OCR cross-checking is needed for VLM-only lines (currently `agree` is `null` there) — e.g., re-OCR a crop of the region.
7. Whether region text extents are sufficient for retrieval filtering or true window rects are needed sooner than 4K.
8. How often the VLM's proposed rows fail the geometric sanity check, and whether the 0.5-line-height / 3-line-height limits are right.
9. Whether Vision's `customWords` (CLI tool names, resource-name patterns) improves command transcription without reintroducing dictionary-style corrections.
10. Whether the block-cursor confirmation latency (~1–1.5 s before a new cursor position is masked) is acceptable, or whether a shape prior for block cursors should exclude them immediately, as bar carets are.
11. Which embedder (local ONNX vs hosted) is adequate for the semantic questions in the question set, or whether lexical retrieval alone suffices for v1.
12. Redaction: recorded screens contain identifiers (subscription IDs, tenant domains, resource names) that end up verbatim in the index and in answers. Whether v1 needs a redaction or allow-list pass before indexing, and where it would sit (Stage 7 input) without breaking R1 for the owner's own queries.
13. Whether Files API references are accepted inside batch requests, and the Batches `custom_id` limits (§20.7 **[verify]**).
14. How often Apple Vision drops a hyphen from `--flag` tokens or splits commands on real frames (seen on an 18-px Menlo fixture, §5.4), and whether `customWords` or a larger `minimumTextHeight` changes it.
15. When OCR and VLM disagree, the fused text is the OCR reading (§9.2). On a synthetic dry run Vision read `PS C:\src>` as `PS Ci\src>` in one frame and correctly in the previous one, so the typed rule (§11.3) saw no prefix relation and the command produced no `typed` event. Whether fused text should prefer the VLM reading for lines flagged `confusable` or for low-similarity disagreements, and whether the typed rule should compare *either* reading, is for the harness to decide **[measured]**.

---
## 23. References

Documentation consulted during design (2026-09):

- Gemini API — Video understanding: https://ai.google.dev/gemini-api/docs/video-understanding
- Gemini API — Media resolution: https://ai.google.dev/gemini-api/docs/media-resolution
- Google blog — Agentic video understanding (2026-09-01): https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-agentic-video-in-gemini/
- OpenAI — Images and vision (image input limits, detail levels, patch tokenization): https://developers.openai.com/api/docs/guides/images-vision
- OpenAI — Cookbook, frame-extraction video narration (archived): https://developers.openai.com/cookbook/examples/gpt_with_vision_for_video_understanding
- Claude — Vision (patches, image limits, resolution tiers; confirmed 2026-09-13): https://platform.claude.com/docs/en/build-with-claude/vision
- Claude — Structured outputs and Message Batches (via the Anthropic SDK reference bundled with the development tooling, 2026-09-13)
- Apple — `VNRecognizeTextRequest` (properties: `recognitionLevel`, `usesLanguageCorrection`, `recognitionLanguages`, `customWords`, `minimumTextHeight`, `automaticallyDetectsLanguage`; revisions 1–3): https://developer.apple.com/documentation/vision/vnrecognizetextrequest
- Apple — Recognizing text in images: https://developer.apple.com/documentation/vision/recognizing-text-in-images
- PyObjC: https://pyobjc.readthedocs.io/
- PyAV: https://pyav.org/docs/stable/
- RapidOCR: https://github.com/RapidAI/RapidOCR
- sqlite-vec: https://github.com/asg017/sqlite-vec
- SQLite FTS5: https://www.sqlite.org/fts5.html
- fastembed: https://github.com/qdrant/fastembed
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

---

## 24. Revision history

- **Revision 1 (2026-09-13, earlier):** original draft, written with Windows.Media.Ocr and .NET as the implementation platform.
- **Revision 2 (2026-09-13):** macOS/Python port, without changing the pipeline's stages, data model, or prompt contracts. Changes: platform row in the header; §1.1 note that recording OS and processing OS are independent; D12 rewritten (Apple Vision baseline, RapidOCR challenger) and D13–D15 added (Python/uv; PyAV + numpy/scipy, no OpenCV; single VLM provider in v1); glossary entries for the accessibility tree and PTS; §5.2–§5.3 Claude image facts confirmed against documentation (4,784-token cap noted for 1440p); §5.4 rewritten; §5.5 and §21 generalized from Windows UI Automation to the OS accessibility tree; §6 made explicitly optional; §7.1 rewritten for in-process decode; §7.2/§7.4 implementation notes; §7.3 `t_settled` corrected to the first still frame; §8.1 rewritten around an engine interface with Vision's coordinate conversion; §8.2 overlay-dimension rule; §9.0 fragment join added and referenced from §11.2 (replaced by VLM-proposed rows in revision 3); §14.2 concrete index choices; §16, §18.2, §22, §23 extended; §19.6 dollar estimate added; §20 rewritten for Python on macOS with measured figures.
- **Revision 3 (2026-09-13):** synthesis of two independent design reviews (one with full project context, one cold), both of which ran experiments on the sample video. Stage 1 rewritten: the morphological opening that erased typed text is replaced by dilation plus a minimum-area filter (§7.2, verified on synthetic and real frames); the settle state machine gains an end-of-stream flush, a max-hold that fires only while moving, an in-place upgrade of max-hold frames that were end states, and `t_settled` at the first still frame (§7.3); the churn ring buffer is fed by the unmasked map with per-pixel hysteresis, and churn ticks plus a deactivation rule capture scrolling output (§7.4); a blink tracker handles block cursors and locates the caret (§7.5); thresholds no longer scale with recording resolution (§16). Stage 2: two images (clean + overlay) per VLM call and never-inside label placement (§8.2–§8.3, D16); the VLM proposes rows (§8.3, §9.0, D17); repair-not-abort validation. Stage 3: glyph-strip agreement, short-line alignment, `ocr_conf` declared advisory, `layout_conf` excludes occluding pairs and uses row coverage, focus combination table (§9). Data model: transitions carry `t`; `computed_diff` keyed by to-frame region with `from_region`; refs are `"<frame>:<line_id>"` and validated; sidecars `focus.jsonl` and `interpretations.jsonl` so no stage writes another's file; `outline_chapter` computed on read; file ownership table (§10.7); IDs unpadded. Stage 4: text-Jaccard region correspondence; clock ops and trivial transitions; coalescing tolerant of backspace, inline prediction and scroll-off, plus Rule 1b; transient rule relaxed; explicit ordering (§11). Stage 5 made parallel (context from computed events, not prior `action` fields) (§12). Stage 6: boundary output as start IDs with repair; fallbacks without Stage 0 (§13). Stage 7: query-builder rules, filters before top-k, embedder default `none` (§14). §16 rewritten; §17 extended; §18 ground-truth inventory completed and §18.4 fixtures/diagnostics added; §19.6 includes thinking tokens and the second image; §20.7 batch chunking/resume, cache key with effort. Open questions renumbered (§22). Not adopted from the reviews: `t_change = tPrev` (kept `t_change = t`, the first frame that no longer shows the previous state, matching the half-open stable-interval semantics).
- **Revision 4 (2026-09-13):** amendments from two independent reviews of the implementation plan, both of which executed the plan's code. §7.2: component boxes are tight boxes of changed pixels. §7.3/§7.5: novelty decisions resting only on unconfirmed blink candidates are deferred, and the confirmation correction also applies to the buffered emission (a block cursor's half-period exceeds S; without these, every keystroke pause emitted spurious states on the synthetic fixture); caret stored as a box. §7.7: slow solid motion and never-confirming toggles listed as accepted losses. §5.4/§22: Vision dropped a hyphen from `--resource-group` on a fixture. §8.3: repair rules completed (emptied rows, truncated rows, parent cycles). §9.4: caret/retrospective conflict caps at 0.6. §11.1/§16: region correspondence uses text containment instead of Jaccard (Jaccard collapsed on the growth case §11.1 itself cites). §13.1: the re-prompt must vary the request; chapter fallback mapping stated. §14.1: region documents index both readings of disagreeing lines. §10.7: loader wording. §20.2: half-resolution reduces the change map, not the frame. §20.7: only terminal outcomes are cached.
- **Revision 5 (2026-09-13):** amendments from the first run of Stage 1 on the sample video (223 emitted frames). §7.3: one unsettled snapshot per M whichever clock is due (a churn tick and a max-hold had fired one frame apart, leaving a record with `t_end` before `t_settled`); a snapshot is upgraded to settled only when no churn region is active, and its `t_settled` never precedes its `t_change`. §7.4: the deactivation event is a churn region *disappearing*, dated by the pixels that left it (any-pixel-left fired while the region still churned). §7.5: blinker history for caret lookup at finalization; non-blinking cursors give no caret. Record invariants (`t_change ≤ t_settled ≤ t_end`, snapshot spacing ≥ M) are now asserted by every settle fixture (§18.4).
- **Revision 5.1 (2026-09-14):** the package and command are renamed from `vt` to `scry` at the owner's request (`src/scry/`, `uv run scry …`, `scry.toml`). No behavior change. Historical documents (the plan, the reviews, ledger entries L1–L27) keep the old name.
- **Revision 5.2 (2026-09-13):** §20.11 adds `scry subset`, a derived run directory over a frame range of an existing Stage 1 output, used for the first live smoke run of the model stages (ledger L28).
