# The pipeline against a video model asked directly

Written 2026-09-21 for the question "why not send the video to Gemini's video-to-text API and ask it everything?". The pipeline already uses that API for one thing it is good at: the optional outline stage asks it for chapter boundaries, at about $0.10 a video (ledger L58). This page separates what is structural from what has to be measured. The measured part is in `docs/results/compare-gemini/report.md` (ledger L70): Gemini direct answered 17 of 22 positive questions against the pipeline's 22 of 22, read 7 of 14 exact strings against 14 of 14, and invented terminal runs where the shell showed a grey suggestion; it cost $0.079 a question against $0.263.

## Structural differences

These follow from what each approach is, not from any measurement, and they hold whatever the measured scores turn out to be.

1. **Every claim carries a citation a reader can open.** An answer from the pipeline names a frame and a text box (`frame 188`, `188:b12`) and the tool that returned it; the frame image is on disk and the box is drawn on it. A video model answers with a time at best, and checking a time means scrubbing the video to it. The pipeline's evaluation replays every tool call of every answer against the index and found no invented on-screen text in 500 answers (P4, P6, P9); the same check is not possible on a video model's answer, because there is nothing to replay.

2. **Measured text is the record; models only label it.** The pipeline's strings come from OCR at full resolution, per frame, and the model stages never overwrite them: a second reading is stored beside the OCR reading, never in its place, and a disagreement is shown to the reader. A video model samples the video at a fixed rate and resolution and returns one reading with no second opinion. Long exact strings (a command with flags, a subscription id, an IP address with its leading colons) are where this shows, and that is what the comparison measures.

3. **The pipeline distinguishes what was typed from what was suggested, and what ran from what was displayed.** The record marks a shell's grey suggestion as measured text that changed, the interpretation stage records `entered_text` and `submitted` as a model's reading with the transition it rests on, and the answering agent is told that text on screen is not evidence a command ran. Ledger L66 shows what happens when a weaker model builds that record: it writes suggested text as entered on 15 to 18 of 21 typing transitions. A video model asked a question has no such record to consult; whether it keeps that distinction is measured by the comparison, not assumed.

4. **Cost is paid once per video, then per question without the video.** The pipeline builds an index once ($4.62 a video without annotation, $17.85 with it, on Opus 5) and answers a question for $0.05 to $0.26 in 10 to 22 s, reading only what search returns. A video model call reads the whole video every time, so the cost and latency of each question scale with the video's length (context caching lowers the price of the cached part but every call still pays for it). The break-even number of questions per video is computed in the comparison.

5. **A corpus is searchable.** The index is one SQLite file per video with full-text search over measured text, descriptions and summaries, and a query can run across many videos ("which video shows `az aks get-credentials`?"). A video model answers one video per call; asking a corpus means asking each video in turn and paying for each.

6. **Length.** The index grows with the video and the answer step reads only what search returns, so a three-hour recording costs three times as much to build and the same per question. A video model call is bounded by what one request can hold, and its per-question cost grows with length. The exact ceiling for the model used here (`gemini-3.8-flash` with agentic video processing) has not been measured and is not claimed; the scaling of per-question cost is structural.

7. **What the pipeline does not have and a video model does.** Audio: the sample has no audio stream, and the pipeline reads the screen only; a video model with a narrated tutorial hears the narration. Motion: the pipeline sees settled frames and pixel changes between them, not what happens between captures. Simplicity: a video model is one call and no infrastructure.

## What is measured, not structural

- Whether the video model's answers are correct on the 27 draft questions, and whether its exact strings are exact.
- Whether it says a grey suggestion was typed, or that a command ran when it was only displayed.
- What one question costs and how long it takes, and the break-even against the pipeline's one-time build.
- Whether "Gemini perceives once, Opus answers from the transcript" recovers exactness or the contract.

## How to use this in a presentation

Lead with what was measured. Then the structural points, in this order: citations, measured text, typed against suggested, cost per question, corpus search. Say what the pipeline does not do (audio, motion, simplicity). The draft question set is known to be blind to the typed-against-suggested distinction (ledger L66, L67), so a tie on scores does not mean a tie on the contract; the reading of the answers is the evidence for that.
