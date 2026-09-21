# Briefing for the owner's return (2026-09-21)

What happened while you were away, in the order you will want it. The decision ledger (`docs/decision-ledger.md`, rows L44 to L67) has every decision with its reason and how to undo it. `docs/open-items.md` leads with what needs you. Each phase has a folder under `docs/results/`.

## Where things stand

- The re-base onto boxes mode is built end to end on the branch `rebase-boxes` (145 commits ahead of `main`, 335 tests pass). Stages: `decode, outline, read, track, annotate, interpret, summarize, index, ask`, plus the evaluation harness (`scry eval run|judge|report`). Row mode is gone; `main` is untouched at the tag `pre-rebase-boxes`. **Nothing has been pushed.** Every work branch was merged with a merge commit and kept.
- The optional Gemini outline stage works live (about $0.10 a video). The sample video has no audio stream, so its audio path is untested.
- Spend: about $421 of the $491 Anthropic credit, and about $0.30 on Google. **About $70 is left and is being kept for your hold-out video.** No paid phase is running or planned.

## What the phases found

| phase | what it was | spend | what it showed |
|---|---|---|---|
| P0 | `read` and `track` on all 221 frames, free | $0 | OCR exact on 7 of 7 commands; incremental targets are 12 % of boxes |
| P1 | transcribing, group-only, none, on your command span | $81.01 | all three tie at the ceiling |
| P2 | graphical questions on the short span; incremental against every-frame | $100.75 | incremental matches every-frame at under half the cost; the second reading of the edited line on frame 155 decided two questions; no annotation 36 of 42 |
| P3 | annotate image scale, 1.0 down to 0.2 | $29.04 | a cliff between 0.5 and 0.4; 0.67 saves only $3 a video; **scale stays 1.0** |
| P4, P4b | whole video, 27 draft questions, annotated against none, sync and batch | $91.42 | every base 27 of 27; $17.85 annotated, $12.11 in batch, $4.62 with no annotation; batch pays 0.68 of sync, not half |
| P5 | referencing without the overlay (boxes listed as id and rectangle) | $17.52 | no saving, and whole dense frames silently scrambled; **removed**, tag `arm-d-evaluated` |
| P6 | the same questions with pixels withheld from the agent | $32.70 | annotated 27 of 27, unannotated 26 and a partial; the per-frame description carried the difference |
| P7 | Sonnet 5 for `annotate` | $2.73 | half the price, clearly worse labels; **stays Opus 5** |
| P8 | Sonnet 5 for every stage | $25.90 | answers tie; `interpret` records grey suggestions as entered text on 15 to 18 of 21 typing transitions (Opus 1 to 3); **stays Opus 5** |
| P9 | Sonnet 5 as the answering agent only, on Opus-built indexes | $7.05 | ties on score at a quarter of the price; opens far fewer frames and rarely says when readers differ; **default stays Opus 5**, `[ask] model` is there |

## The three things the evidence says

1. **Nothing became unfindable.** On the whole video every command is found, read exactly and marked submitted, with no false run, with or without annotation. One paraphrase never reaches its frame by lexical search; the agents recovered by other words.
2. **`annotate` is three quarters of the pipeline's cost, and two parts of it have reached an answer:** the second reading of a line being edited (P2) and the per-frame description (P6). Containers and links have not decided any answer we have been able to ask. That is a statement about this video and these draft questions: search by key, the application filter and a second opinion on a doubtful text are experiences you asked for, and no question here exercises them. The working default stays incremental transcribing; the choice among transcribing, group-only, none (and an unbuilt description-only mode) is yours.
3. **The question sets cannot see your central rule.** Answers saying "retyped" for a grey suggestion, "corroborated by later scrollback", and a false agreement of two readers were all judged correct. Cheaper models pass the rubric while breaking the contract. The rubrics need lines for it before model or agent comparisons mean much.

## Decisions I made that you may want to reverse

- Incremental transcribing is the working default for `annotate` (L59).
- Arm D was built because you called it promising, lost in P5, and was removed behind a tag (L61, L63). Arms B and C (position-based assignment) are still unbuilt although you said you wanted it evaluated: under them every frame must be annotated, at about three times the cost, and nothing measured since the tag fix points at id assignment as a live problem (L61).
- Annotate calls with no target are kept, with a plainer instruction, because they refresh the description you wanted kept. Skipping them would save about $2.30 a video (L62).
- No machinery was added for: search flooding, junk in a description (one case in about 1,500 calls), the overlay's tag placement at reduced scale, scramble detection, batch cache warming. Each is written down with its evidence.
- Fixed along the way: a batch requeue bug that never resubmitted failed requests, batch cost reporting, false cache-hit warnings for batch runs.
- One ledger row of mine (L65) first overlooked P2's result and was corrected in place with a visible note.

## What needs you, in order

1. The hold-out video.
2. Correct the three draft question sets and add rubric lines for the contract (`docs/ground-truth/`).
3. The `annotate` default, in the light of the cost and of what reached an answer.
4. Whether to try position-based assignment after all; whether to skip no-target calls; which model answers questions.
5. One case to look at: an Opus step summary that says a command was "typed" where its own transition calls most of it a suggestion (`docs/results/p9/analysis.md`, last section). It is the first sign of the contract leaking on Opus.
6. Look at the branch, then merge and push when you are ready.
