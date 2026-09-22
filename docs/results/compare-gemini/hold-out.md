# The hold-out video: Gemini direct against the pipeline, for analysis only

Date 2026-09-21. Branch `compare-gemini`, code `compare/gemini/v2.py` (with `common.py`, `judge.py`, `analyze.py`),
raw outputs under `runs/compare-gemini-v2/` (git-ignored), the generated tables in `hold-out-tables.md` beside this
file. The first comparison, on the sample video, is `report.md`.

## What was run

- **The video.** `runs/videos/recording-2026-09-17.mp4` (the owner's second recording: 223.97 s, 2048x1080, 30 fps,
  6,719 frames, one h264 video stream and one AAC audio stream), given to Gemini as a **silent copy**,
  `runs/videos/recording-2026-09-17-silent.mp4`, remuxed with PyAV (the video stream's packets copied, no audio, no
  re-encode; verified: one video stream, zero audio streams, 6,719 packets and the same last pts in both, duration
  223.9667 s, the first and last frames decode and `scry.video` reads it). The pipeline never reads audio, so the two
  arms saw the same pictures. The remux script is in the analyst's scratchpad, not the repo (`*.mp4` is never committed).
- **The questions.** The five of the drafting agent's `questions-draft.md` (four positive: an exact string, a "what
  changed", a "when", a "visual"; one negative), 16 rubric lines, copied to `runs/compare-gemini-v2/questions.md`
  (sha256 `4472c39a...`). One edit to the copy: the heading `### Q5 (negative)` became `### Q5 (negative, did they)`,
  because `parse_questions` needs a style after the polarity and dropped Q5 as written; the question key is the hash
  of the question text and is unchanged. The draft is not owner-accepted.
- **G1, Gemini direct.** `gemini-3.8-flash`, the silent copy uploaded once, one `interactions.create` per question
  (`video` block, `processing: "agentic"`, the outline stage's call shape), the same instruction as in the first
  comparison (answer from the video; a time for every claim; quote on-screen text exactly; say when the video does not
  show something). 5 calls, 0 failures, 0 retries.
- **The pipeline, four indexes of the same 80 decoded frames.** The owner's-default run `runs/v2/grouponly-100`
  (group-only annotation at scale 1.0, outline off), whose five answers the drafting agent had already asked with
  `scry ask` (`runs/v2/ask/q1..q5.json`, 2026-09-21 20:32; imported, question texts checked, not re-asked); and three
  indexes the harness built cold from the same frames and OCR under `runs/eval/v2/` (`evals/v2.toml`): group-only at
  scale 0.67, transcribing at 1.0, and no annotation. On those three the five questions were asked with the built-in
  agent through `scry.evaluation.adapters.answer_fn` (`scry.ask.ask`, `claude-opus-5`, effort high, frames available,
  each run's own `config.json`, 8 calls at a time). 15 calls, 0 failures. `ask` wrote redecoded frames under each run's
  `redecode/` as it does in the harness; nothing else under a run directory changed.
- **The judge.** `scry.evaluation.judge`, `judge-v1`, `claude-opus-5` effort low, its cache under
  `runs/compare-gemini-v2/judge-cache`, blind to the arm: 25 verdicts, 0 errors (one "Event loop is closed"
  traceback at shutdown, the known harmless noise noted in `docs/results/p6/analysis.md`).

Spend: $6.19 (Gemini $0.30 over 5 calls; Anthropic $5.89 over 20 calls: $5.61 for the 15 pipeline answers, $0.28 for
the judge), under the $10 cap; the imported grouponly-100 answers had cost the drafting agent $1.86. Gemini's dollars
are `outline.py`'s list prices on the API's reported tokens (no cached tokens this time).

## Scores

| arm | positive (of 4) | negative (of 1) | correct / partial / wrong | rubric lines passed (of 16) | $ per question | seconds per question |
|---|---|---|---|---|---|---|
| G1 Gemini direct, silent copy | 2/4 | 1/1 | 3 / 0 / 2 | 13 | $0.060 | 28 |
| pipeline, group-only 1.0 (owner's default) | 4/4 | 1/1 | 5 / 0 / 0 | 16 | $0.372 | 36 |
| pipeline, group-only 0.67 | 4/4 | 1/1 | 5 / 0 / 0 | 16 | $0.381 | 43 |
| pipeline, transcribing 1.0 | 4/4 | 1/1 | 5 / 0 / 0 | 16 | $0.392 | 34 |
| pipeline, no annotation | 4/4 | 1/1 | 5 / 0 / 0 | 16 | $0.349 | 36 |

Per question (c correct, w wrong; dollars and seconds per answer):

| Q | style | G1 | grouponly 1.0 | grouponly 0.67 | transcribing | none | G1 $ / s | grouponly 1.0 $ / s | grouponly 0.67 $ / s | transcribing $ / s | none $ / s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | exact string | w | c | c | c | c | 0.026 / 25 | 0.367 / 30 | 0.312 / 32 | 0.328 / 22 | 0.227 / 25 |
| Q2 | what changed | w | c | c | c | c | 0.108 / 46 | 0.659 / 66 | 0.648 / 79 | 0.870 / 83 | 0.685 / 82 |
| Q3 | when | c | c | c | c | c | 0.089 / 32 | 0.226 / 27 | 0.269 / 35 | 0.137 / 18 | 0.256 / 26 |
| Q4 | visual | c | c | c | c | c | 0.060 / 30 | 0.225 / 28 | 0.220 / 30 | 0.165 / 17 | 0.181 / 17 |
| Q5 | negative | c | c | c | c | c | 0.017 / 8 | 0.384 / 28 | 0.458 / 36 | 0.461 / 32 | 0.398 / 30 |

Every pipeline index passes all 16 lines; the four indexes agree on every verdict. G1 fails 3 lines on 2 questions.

## The failed lines, classified

Frames 0, 33 and 73 of `runs/v2/grouponly-100/frames/` were checked by eye (crops enlarged).

| Q, line | class | what happened |
|---|---|---|
| Q1 M1 | misread, most of the string | Gemini: `FRONTDOOR-A-cnhedcc5b0d0h4e0.z01.azurefd.net` for `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`. The prefix `FRONTDOOR-A` and the suffix `.azurefd.net` survive; the 16-character random label, `MTLS`, and `b02` do not. The string is the orange find-on-page highlight on frame 0, on screen for 9 s at the start and again at 0:29, 1:49 and 2:42. Every pipeline index quotes it exactly (OCR box `0:b116`). |
| Q2 M1 | invented | Gemini: the added line is `where requestUri_s contains "testHostDeviceAllocationServiceClientCertificate"`; frame 73 line 5 reads `"ServiceA/Certificate"`. The same answer's "full query" also has `contains "enrollment"` for `!contains "enrollment"`, `!contains "w.manage" or ... "-manage"` for `contains "i.manage" or ... "r.manage"`, `httpStatus_s` for `httpStatusCode_d`, and `bin(TimeGenerated, 5m)` for `1m`: five misreads in eight lines, presented in a code block as the query. |
| Q2 M2 | not seen | Gemini says nothing of the `//` that comments out the i.manage line from frame 71 (3:21); its "end" version lists that line as active. The pipeline's four answers all place the `//` at frame 71 and the new line at frame 73. |

Unscored misreads in the answers judged correct: Q4's two accounts are `the account holder (user)` / `user@example.com` and `the account holder` / `user@example.com` (frame 33); Gemini wrote `USER (redacted)` / `user@example.com` and `the account holder` / `user@example.com`, and the rubric, judged on meaning ("the first account is highlighted"), passed it. Q5 names the added endpoint `afd-endpoint` three times; the panel reads `AFDEndpoint`. Q3's three profile names and the notification text are exact.

## Exactness

One "contains the exact string" line in this set (Q1 M1). Mechanically (P6's method): G1 0 of 1, every pipeline index
1 of 1; judge and check agree. Beside the pipeline's reading: G1 `FRONTDOOR-A-cnhedcc5b0d0h4e0.z01.azurefd.net`, the
pipeline `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` (cited as `0:b116`, lifetime `L116`, with the OCR variant `g`
for `q` on one transition named and resolved from the image). Counting every quoted string in the five G1 answers
against the frames: the hostname, the KQL line, four other KQL tokens, two account names and the endpoint name are
wrong; the profile names, the notification text, the page titles and the panel labels are right. Gemini's exactness on
this video is worse than on the sample (0 of 1 against 7 of 14), on a string that is longer and random where the
sample's were IPs and words.

## The contract

Every G1 answer and every pipeline answer to the five questions was read in full. No terminal in this video, so the
typed-against-suggested question does not arise; the contract here is "quote what is on screen and say what is not".

- G1 Q1: "This is also confirmed later when the endpoint is copied at 00:32 and pasted into the 'Fully qualified
  domain name (FQDN) or IP address *' field at 00:57–01:00." The pasting into the FQDN field is real (frames 16 to
  21); the confirmation is of a string that is not on screen.
- G1 Q2: "The added line was pasted in at 03:20–03:21 between `| where requestUri_s contains "enrollment"` and
  `| where requestUri_s !contains "w.manage" ...`, expanding the query from 7 lines to 8 lines before it was re-run at
  03:26." The 7-to-8 and the re-run are right; the pasted text and both neighbours are misquoted, and the answer
  presents two full code blocks as the queries.
- G1 Q4: "**`USER (redacted)`** ... **`user@example.com`**": invented account text quoted in code
  font as exact.
- G1 Q5: "the video does not show an endpoint being deleted" (right), then the panel name "**afd-endpoint**" three
  times (the field reads `AFDEndpoint`).
- G1 Q3: exact throughout (three profile names, the notification's two lines, times within 3 s of the frames).
- Pipeline, 20 answers: every quoted string checked against the judge's quotes and, for Q1, Q2 and Q4, against the
  frames, is on the frame it cites; each cites frame and box ids (`0:b116`, `79:b100`, `33:b59`), and 17 of 20 say
  which readings were single-sighting or single-reader, or where the OCR reading was checked against the frame ("seen in only this one frame ... only one reader (OCR)") or that
  the exact moment fell in an uncaptured gap ("the paste and the Run click fall in the uncaptured gap 204.3–206.8 s").
  The no-annotation and transcribing indexes redecoded the video for Q2 to place the Kusto.Explorer switch.

## Cost and time

| arm | build per video | $ per question | seconds per question | tokens per question |
|---|---|---|---|---|
| G1 Gemini direct | upload 28 s, no charge | $0.060 (0.017 to 0.108) | 28 (8 to 46) | 62k tool-use (28k video), 2.8k thinking, 0.5k output |
| pipeline, group-only 1.0 | $9.32 | $0.372 | 36 | 99k input, 1.9k output; 3.4 turns, 4.4 tool calls |
| pipeline, group-only 0.67 | $7.68 | $0.381 | 43 | 103k input; 3.4 turns, 4.4 calls |
| pipeline, transcribing 1.0 | $11.42 | $0.392 | 34 | 117k input; 3.4 turns, 4.2 calls |
| pipeline, no annotation | $2.94 | $0.349 | 36 | 92k input; 3.6 turns, 4.8 calls |

Build costs are the manifests' stage totals (annotate, interpret, summarize at list price; decode and OCR are free).
The pipeline's per-question cost on this video ($0.35 to $0.39) is above the sample's $0.263: the questions are
longer, three of five answers open a frame at 2048x1080, and Q2 takes 5 to 6 turns. Break-even against G1: never for
any index; G1 is cheaper per question by a factor of six and has no build. On time G1 (28 s) and the pipeline (34 to
43 s) are alike; the pipeline's build took 2 to 6 minutes per index on top.

## Citations

All five G1 answers give mm:ss times (8 per answer), none names a frame or anything that resolves to an artifact; the
times are within about 3 s of the frames' where the claim is right (Q3, Q4, Q5). All 20 pipeline answers cite frame
and box ids (only 10 of 20 also give mm:ss), which resolve to `frames/NNNNN.png` and `boxes.jsonl` under the run.

## What this shows

Five draft questions on a second video, one Gemini run per question and no repeat, so the repeat noise is unknown
(the four pipeline indexes, built and asked separately, agree on all 80 verdicts). On this video Gemini gets the
"when", the "visual" and the negative question and loses both questions that turn on reading text: it rewrites a
44-character hostname, invents the KQL filter that was added and misses the line that was commented out, and quotes
invented account names in code font. Every pipeline index, with or without annotation, answers all five, quotes every
string exactly, and cites the frame and box a reader can open; it costs six times more per question and $3 to $11 to
build. The Gemini arm had the silent copy and the pipeline had the original file; neither uses audio. The judge is
blind to invented text that a rubric line does not name (Q4, Q5), so the scores understate the difference; the
scores alone say 3 of 5 against 5 of 5.

## The outline stage on the silent copy (step 3)

From the pinned worktree `.claude/worktrees/v2` (`b55122e`):
`uv run scry run runs/videos/recording-2026-09-17-silent.mp4 --out runs/v2/grouponly-100 --stages outline,index --config <copy of runs/v2/scry-v2.toml with [outline] enabled = true>`
(`--stages` takes a comma-separated list of stage names; the two stages ran in order, 55 s wall). The outline stage
uploaded the silent copy (26.4 s), made one `gemini-3.8-flash` agentic call (26.9 s; 136 prompt tokens, 15,428
tool-use of which 7,392 video, 2,079 thinking, 561 output; **$0.0216** at list price) and wrote `outline.json` with 7
chapters. The index stage saw the new input (`outline.json` was `missing` in its recorded inputs) and rebuilt
`index.sqlite` from scratch: 2,751 nodes, 7 of them level `chapter`, against 2,744 before; every frame, lifetime and
transition node now carries a `chapter_id`. The manifest gained an `outline` block (the call's tokens, seconds and
cost) and the index stage's new record; `video` and `video_sha256` still name the original file, since decode did not
run. The run's costs block is unchanged at $9.32: `run_costs` prices the stages with a `usage` dict (Anthropic) and
the outline's `cost_usd` sits in its own block.

The chapters against the summarize stage's sections (the sections' times are `t` of `sections.jsonl`; a chapter's
are Gemini's whole seconds):

| chapter (Gemini, silent copy) | start, end | nearest section start | diff | section (summarize, from the frames) | start, end |
|---|---|---|---|---|---|
| c1 Review Front Door and Traffic Manager Setup | 0:00, 0:25 | | | C1 Switch from Front Door manager to the Traffic Manager Endpoints blade | 0:00, 0:24 |
| c2 Add Front Door Endpoint to AP01 Profile | 0:25, 1:05 | C2 24.6 s | 0.4 s | C2 Add an external endpoint to the tm-profile-ap Traffic Manager profile | 0:24.6, 1:04 |
| c3 Navigate to EU01 Traffic Manager Profile | 1:05, 1:42 | C3 64.0 s | 1.0 s | C3 Open the EU Traffic Manager profile and fill in a new external endpoint | 1:04, 2:05.6 |
| c4 Add Front Door Endpoint to EU01 Profile | 1:42, 2:13 | (none; C4 starts 126.1 s) | 24.1 s | | |
| c5 Add Front Door Endpoint to NA01 Profile | 2:13, 2:36 | C4 126.1 s | 6.9 s | C4 Add the AFDEndpoint to NA01 | 2:06.1, 2:31.7 |
| | | | | C5 Close the Network tab and locate the AFD hostname | 2:31.7, 2:41.6 |
| c6 Query Front Door Logs | 2:36, 3:21 | C6 161.6 s | 5.6 s | C6 Query Front Door access logs in Log Analytics | 2:41.6, 3:20.8 |
| c7 Refine Query and Analyze Traffic Chart | 3:21, 3:44 | C7 200.8 s | 0.2 s | C7 Compare Kusto.Explorer and read the chart results | 3:20.8, 3:43.9 |

Three of the six chapter boundaries agree with a section boundary within about a second (0.4, 1.0 and 0.2 s: the
start of the AP01 work, the move to EU01, and the Kusto.Explorer switch). Two are 4 to 7 s off (the NA01 start, 133
against 126.1 s; the Logs start, 156 against 161.6 s). One chapter boundary has no section counterpart: Gemini splits
the EU01 work into "navigate" (1:05 to 1:42, ending at the sign-in dialog) and "add endpoint" (1:42 to 2:13), where
summarize keeps EU01 as one section C3 (1:04 to 2:05.6); and one section boundary has no chapter counterpart: C5
(2:31.7 to 2:41.6, closing a tab and finding the hostname) is inside Gemini's c5. Both readings put the same seven
pieces of work in the same order with matching titles; the chapter gists are a sentence each and name no on-screen
string, as the stage's prompt asks ("Do not attempt to transcribe exact text").

## 21 questions

The 16 questions of `docs/ground-truth/holdout-discovery.md` (13 positive, 3 negative, 71 rubric lines; copied to
`runs/compare-gemini-v2/questions-disc.md`), each asked on its own with the same instruction: G1 on the silent copy
(16 Gemini calls, 4 at a time, 0 failures, $1.94) and the pipeline's built-in agent (`scry.ask.ask`, Opus 5, the
owner's config) on the default index `runs/v2/grouponly-100` through a symlink view `runs/compare-gemini-v2/view-grouponly-100/`
(every entry of the run linked; the agent's 24 redecoded frames landed in the view's `redecode/`, nothing in the run;
16 calls, 8 at a time, 0 failures, $8.70). Judged with the same blind judge (32 verdicts, $0.49). Spend for this set
$11.13 (Gemini $1.94, Anthropic $9.20), cap $12. Tables in `hold-out-tables-21.md`.

Combined over the 21 questions (the 5 draft questions above plus these 16):

| arm | correct / partial / wrong (of 21) | positive score | negative score | rubric lines passed (of 87) | $ per question | seconds per question |
|---|---|---|---|---|---|---|
| G1 Gemini direct, silent copy | 12 / 5 / 4 | 11/17 | 3.5/4 | 71 | $0.107 (5: 0.060; 16: 0.121) | 32 (5: 28; 16: 33) |
| pipeline, group-only 1.0, `runs/v2/grouponly-100` | 18 / 2 / 1 | 15/17 | 4/4 | 81 | $0.503 (5: 0.372; 16: 0.544) | 60 (5: 36; 16: 67) |

On the 16 alone: G1 9 / 5 / 2, 58 of 71 lines; pipeline 13 / 2 / 1, 65 of 71. The pipeline's one wrong answer is Q2
(the open-ended sequence): the agent stopped after 12 turns and 28 tool calls (8 searches, 12 `get_node`, 7
`get_transitions`, 1 `get_frame`) without a final answer, $1.62 spent; it is judged wrong by rule. Its two partials:
Q8 (it reports the click on the account tile as recorded by transition T34 rather than as inferred; the rubric wants
the hedge) and Q11 (it says Kusto.Explorer was used to compare queries, not that the filter line was copied from it).
G1's answers to Q2 and Q11 pass where the pipeline's do not.

The 13 G1 rubric lines failed on the 16, classified, one quote each (frames checked by eye in the earlier sections;
every failed exact-string line agrees with the mechanical check):

| class | Q, line | quote from the answer | what is on screen |
|---|---|---|---|
| misread string | Q4 M4 | `FRONTDOOR-A-hostname.z01.azurefd.net` | `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` (frame 0) |
| misread string | Q7 M3 | `FRONTDOOR-A-d7c3eeafgnh2hrcs.z01.azurefd.net` | the same hostname |
| misread string | Q15 M1 | `FRONTDOOR-A-d7hqa4g5edbwh4ea.z01.azurefd.net` | the same hostname: four calls, four different random labels, every one `z01` for `b02` |
| misread string | Q9 M2 | `\| where requestUri_s contains "enrollment"` | `!contains "enrollment"` (frame 73 line 4) |
| misread string | Q15 M4 | `\| where requestUri_s contains "enrollment"` | the same line |
| misread string | Q9 M3, X1 | `summarize count() by strcat(httpStatusCode_d, originalURL_s), bin(TimeGenerated, 5m)` | `strcat(httpStatusCode_d, requestUri_s), bin(TimeGenerated, 1m)` (frame 73 line 7); `5m` is what X1 forbids |
| invented | Q10 M2 | `\| where requestUri_s contains 'HostAuthenticationService/Certificate'` | `"ServiceA/Certificate"` (frame 73 line 5); the draft-set answer to the same edit had invented `testHostDeviceAllocationServiceClientCertificate` |
| invented | Q10 M1 | `//\| where requestUri_s contains "/manage/"...` | the commented line reads `contains "i.manage" or ... "r.manage" or ... "a.manage"`; the `//` is right, the content is not |
| missed | Q10 M3 | (nothing in the answer bears on it) | the footer "1000 records" then "277 records" (frames 70 and 79) |
| missed | Q8 M3 | "The account chosen was the first option" | the click itself falls between frames 33 and 34; the rubric wants that said |
| missed | Q16 M2, M3 | "The video does not show or mention anything about what a record cannot tell regarding this session." | the question asks what the record cannot tell (gaps between captures, intent); Gemini answered that the video has no such text |

Of the 13: 7 misread strings (the hostname three times, the KQL lines four times), 2 invented (both the KQL edit), 4
missed (a count, a hedge, and the two lines of the honesty question). The hostname, on screen for 9 s at the start and
three times later, has now been read wrongly in all five G1 calls that quote it across the two sets, with five
different labels; the pipeline quotes it exactly in every answer that names it (`0:b116`). Repeat noise is unknown:
one call per question per arm.

What the 21 add to the 5: the pipeline's advantage is on exact text (the three hostname lines and the four query lines
that G1 fails are all passed by the pipeline) and on the questions that ask what the record cannot show (Q16); G1
matches or beats it on the open-ended overview and sequence questions (Q1, Q2, Q5, Q11), where the pipeline's agent
either ran out of turns or answered from the index's summaries. Per question the pipeline costs 4.7 times more on this
set ($0.544 against $0.121) and takes twice as long (67 s against 33 s), the Q2 run-out alone being $1.62 and 4 minutes.
