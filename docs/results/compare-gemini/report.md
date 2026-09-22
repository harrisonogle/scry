# "Why not just send the video to Gemini?" Measured on the sample, for analysis only

Date 2026-09-21. Branch `compare-gemini`, code under `compare/gemini/`, raw outputs under `runs/compare-gemini/`
(git-ignored), the generated tables in `tables.md` beside this file. Nothing under `src/scry/`, `runs/eval/` or
`runs/p0` was modified; no `scry` command that builds or changes a run was used. The scry modules were used read-only:
the question parser, the blind judge, the Anthropic provider and price table, `load_dotenv`, and `outline.py`'s Gemini
call shape and price list.

## What was run

The video: `assets/create-aks-cluster-tutorial.mp4` (the source recorded in `runs/p0/manifest.json`; 14:12.8,
1920x1080, no audio). The questions: the 27 of `docs/ground-truth/full-questions.md` (22 positive, 5 negative), parsed
with `scry.evaluation.questions.parse_questions`, so the keys match the phases'. The judge: `scry.evaluation.judge`,
prompt `judge-v1`, `claude-opus-5` at effort low, as `scry eval judge` runs it, with its own call cache under
`runs/compare-gemini/judge-cache`; it saw the question, the reference, the rubric lines and the answer, never the arm.

| arm | what | calls | failures | wall time | spend (list price) |
|---|---|---|---|---|---|
| G1 | `gemini-3.8-flash`, the video and one question per call (`files.upload` once, then `interactions.create` with a `video` block, `processing: "agentic"`, the same call shape as the outline stage, the uploaded handle reused), 4 at a time | 27 | 0 (no retries) | 12 to 116 s per call, mean 32 s | $2.12 |
| G1c | one Gemini call for the list of commands executed in the terminal, scored by hand against `span2-commands.md` | 1 | 0 | 384 s | $0.97 |
| G2 | one Gemini call for a complete timestamped transcript (21k characters); then one `claude-opus-5` call per question, effort high, plain text, the transcript as system context with `cache_control` and the question as the user turn, 8 at a time | 1 + 27 | 0 | 237 s, then 5 to 32 s per call | $0.41 + $0.62 |
| judge | 54 blind verdicts (27 per arm) | 54 | 0 | | $0.50 |
| cache try | one `caches.create` with the video and one `generate_content` on it (see below) | 2 | 0 | 10 s + 10 s | $0.05 |

Total spend $4.67: Gemini $3.54 (31 calls), Anthropic $1.12 (81 calls). Cap $15. The instruction in every answering
call: answer from the video; give a time (mm:ss) for every factual claim; quote on-screen text exactly as displayed,
character for character; if the video does not show something, say so. The video was deleted from Gemini's file store
at the end.

Gemini prices are `outline.py`'s `LIST_PRICES` (paid tier, $0.75 per million input and $3.75 per million output
tokens including thinking, fetched 2026-09-21, the basis of the outline stage's manifest). The agentic mode fetches the
video through its own processing calls, so the video is counted as tool-use tokens, not prompt tokens; they are priced
at the input rate here as in the outline stage. Two caveats: the API lists every fetched frame under both the "image"
and the "video" modality and `total_tool_use_tokens` is their sum, and 4 of 27 G1 calls plus the transcript call
reported `total_cached_tokens` (751,593 of G1's 2,509,385 tool-use tokens; 296,677 of the transcript's 461,781), which
the list-price figure does not discount. The Gemini dollars are therefore an upper bound at these prices.

**Context caching.** The interactions call of the outline stage has no cached-content field (google-genai 2.23's
`CreateModelInteraction` takes `input`, `model`, `generation_config`, `previous_interaction_id`, `response_format`,
`system_instruction`, `tools`), and in the agentic mode the video is not in the prompt at all, so there is nothing for a
prompt cache to hold; `previous_interaction_id` chains a conversation (the next question would see the previous answer)
and was not used. Explicit caching exists on the other path, `caches.create` with the uploaded file and
`models.generate_content` with `cached_content`, and it was tried once, for Q1: the cache was created in 9.7 s and holds
60,564 tokens (the whole video at that path's fixed sampling, about 71 tokens per second of video), $0.045 at the input
rate to create (storage per hour not counted); the call took 9.8 s, 93 output and 358 thinking tokens, and answered Q1
correctly (kube-scheduler, 01:24 to 01:31). The usage it reported (`prompt_token_count` 56,376, below the 60,564
cached) does not let the uncached remainder be computed. This is a different call shape and a different, coarser look
at the video (G1's agentic calls fetched 6,700 to 180,000 video tokens per question, 43,900 on average); its reading
quality was not measured beyond that one question, and G1 sent the video (by handle) each time.

## Scores

Positive questions are the score; negatives are secondary. Each of the 83 rubric lines is a statement about the answer.

| arm | positive (of 22) | negative (of 5) | correct / partial / wrong | rubric lines passed |
|---|---|---|---|---|
| G1 Gemini answers directly | 17/22 | 5/5 | 19 / 6 / 2 | 70/83 |
| G2 Gemini transcript, Opus answers | 16.5/22 | 5/5 | 17 / 9 / 1 | 70/83 |
| P4 Opus pipeline with frames (4 runs) | 22/22 in each | 5/5 | 27 / 0 / 0 in each | 83/83 |
| P6 index only, no pixels (5 runs) | 22, 22, 22, 21.5, 21.5 | 5/5 | 27/0/0 in 3, 26/1/0 in 2 | 83, 83, 83, 82, 82 |
| P9 Sonnet agent on the Opus index (4 runs) | 22, 21.5, 22, 22 | 5/5 | 27/0/0 in 3, 26/1/0 in 1 | 83, 82, 83, 83 |

By question type (the types of the question file; a question can be in several):

| question type | n | G1 | G2 | P4 (mean of 4) | P6 (mean of 5) | P9 (mean of 4) |
|---|---|---|---|---|---|---|
| exact string | 8 | 4/8 | 4.5/8 | 8/8 | 8/8 | 7.9/8 |
| when | 2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| worded without the on-screen words | 4 | 3.5/4 | 3.5/4 | 4/4 | 4/4 | 4/4 |
| value in several states or places | 10 | 8/10 | 7/10 | 10/10 | 10/10 | 10/10 |
| order across the video | 2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| diagram (Q2) | 1 | 1/1 | 1/1 | 1/1 | 0.8/1 | 1/1 |
| negative | 5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |

Both Gemini arms get every "when", "order" and negative question and the diagram. What they lose is the exact strings
and the values read off the terminal. The 27-row table (c correct, p partial, w wrong; `M1+` a passed line, `M1-` a
failed one; the phase columns give one letter per run):

| Q | type | G1 | G2 | G1 lines | G2 lines | P4 (4) | P6 (5) | P9 (4) |
|---|---|---|---|---|---|---|---|---|
| Q1 | worded without the slide's words | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q2 | labels in a diagram | c | c | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ | cccc | cccpp | cccc |
| Q3 | when did they | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q4 | a value typed into a form field | p | p | M1- M2+ M3+ X1+ | M1- M2+ M3+ X1+ | cccc | ccccc | cccc |
| Q5 | a value before and after it was changed | c | p | M1+ M2+ M3+ X1+ | M1+ M2+ M3- X1+ | cccc | ccccc | cccc |
| Q6 | the form against the running cluster | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q7 | first against final state | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q8 | before and after with an error in between | c | w | M1+ M2+ M3+ X1+ | M1+ M2+ M3- X1- | cccc | ccccc | cccc |
| Q9 | the value in two places | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q10 | a changed choice and an exact string | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q11 | values typed and chosen in a side panel | p | p | M1- M2+ X1+ | M1- M2+ X1+ | cccc | ccccc | cccc |
| Q12 | an exact string in several places | p | p | M1- M2+ X1+ | M1- M2+ X1+ | cccc | ccccc | cccc |
| Q13 | when did they | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q14 | exact string with a near miss elsewhere | p | p | M1+ M2- X1+ | M1+ M2- X1+ | cccc | ccccc | cccc |
| Q15 | a page on screen for three seconds | p | p | M1- M2+ M3+ M4+ X1+ | M1- M2+ M3- M4+ X1+ | cccc | ccccc | cpcc |
| Q16 | exact command and when | w | p | M1- M2- M3+ X1- | M1- M2- M3+ X1+ | cccc | ccccc | cccc |
| Q17 | the same command at two moments | c | p | M1+ M2+ X1+ | M1+ M2- X1+ | cccc | ccccc | cccc |
| Q18 | how many times | w | c | M1- M2- X1- | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q19 | exact strings among similar values | p | p | M1- M2- M3+ X1+ | M1+ M2- M3+ X1+ | cccc | ccccc | cccc |
| Q20 | similar values in different places | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q21 | order across the video | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |
| Q22 | order across the video | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q23 | negative | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |
| Q24 | negative | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |
| Q25 | negative | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |
| Q26 | negative | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |
| Q27 | negative | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |

## Every failed rubric line, classified

Classes: **misread** (the text is on the frame and the model read it wrongly; the differing characters are named),
**time misread**, **invented** (the claim is on no frame), **not in the transcript, said so** (G2 only: the perceiver
omitted it and the answerer said honestly that it is not shown), **judge error** (none found: the judge and the
mechanical check agree on all 28 exact-string lines, and every failed line's quote was read and agrees with the
verdict). Frames 142, 188, 201 and 213 of `runs/p0/frames/` were looked at by eye where the ground truth is a draft.

G1, 13 lines on 8 questions:

| Q, line | class | what happened |
|---|---|---|
| Q4 M1 | misread | `RG1-kodecloud-AKS` for `RG1-KodeKloud-AKS`: two characters, K to k and K to c |
| Q11 M1 | misread | `cklcloudaks1` for `crkodekloud`: only `c` and `cloud` survive; the same typed field reads `ckckkcloud` in G1's answer to Q21 and `ckaklkdecloud` in its answer to Q27, three readings of one string |
| Q12 M1 | misread | `KodekloudApp` for `KodeKloudApp`: one character, K to k |
| Q14 M2 | misread | start time `9:22:34 PM` for `9:32:34 PM`: one digit (frame 142 checked) |
| Q15 M1 | misread | `hpranav/kodekloudapps` for `hpranav/kodekloudappcs`: the `c` dropped. The word is the largest text on frame 188, highlighted in yellow, and Gemini reads it `kodekloudapps` in every one of its seven sightings across G1, G1c and the transcript |
| Q16 M1 | misread | `--image=hpranav/kodekloudapp:v1` for `kodekloudappcs:v1`: `cs` dropped |
| Q16 M2 | time misread | "executed at 12:47–12:48"; the output is on screen from 12:39.5 (frame 198). Other G1 answers date the same run 12:38 (Q22), 12:44 (Q27), 12:46 (Q24): a spread of 10 s across calls for one event |
| Q16 X1 | the M1 misread again | a different image name is what X1 forbids |
| Q18 M1, X1 | invented | a third run "at 12:57" with output `kodekloudapp-679b75cb5-mm42w 1/1 Running 0 19s`, and a second "at 12:53" with `0/1 ContainerCreating 0 2s`; frame 213's scrollback holds two runs, the second printing `1/1 Running 0 34s`; no `ContainerCreating` is on any frame |
| Q18 M2 | invented and misread | the pod name `679b75cb5` for `67ffc758c5`, and the `ContainerCreating` output |
| Q19 M1 | misread | `20.247.253.108` for `20.247.251.108`: one digit, 1 to 3 |
| Q19 M2 | misread | `10.0.198.121` for `10.0.199.121`: one digit, 9 to 8; the transcript reads the same wrong digit |

G2, 13 lines on 10 questions. Opus answered only from the transcript, so every misread and invention below is the
perceiver's; Opus repeated it, and where the transcript was silent it said so:

| Q, line | class | what happened |
|---|---|---|
| Q4 M1 | misread | `R01-KodeKloud-AKS`: G to 0; the transcript uses `R01` nine times |
| Q5 M3 | not in the transcript, said so | the Australia Southeast detour (5:25 to 5:33) is absent from the transcript; the answer: "this is the only prior value the transcript shows" and "If any other values flashed in the field during the dropdown search, they are not captured here" |
| Q8 M3, X1 | not in the transcript, said so; the honest sentence is what X1 forbids | the transcript has `Max pods per node *: 30 (minimum required value shown)`, no edit from 110 and no error; the answer: "no error/complaint is shown for that field", "that is not shown in the transcript". X1 ("says no error or warning appeared") holds by the letter |
| Q11 M1 | misread | `ckadkodekloud` for `crkodekloud`, and `ckad` for the partial `cr` |
| Q12 M1 | misread | `MC_R01-...`: G to 0 |
| Q14 M2 | misread | `9:22:34 PM` (the same digit as G1) |
| Q15 M1 | misread | `kodekloudapps` |
| Q15 M3 | not in the transcript, said so (and the transcript's tag row is invented) | the transcript says "Tag listed: v1 (OS: linux/amd64, Size: 110 MB, pushed 7 hours ago)" and omits "This repository contains 2 tag(s)"; frame 188 shows the first tag row as v2, the second cut off, and no size. The answer: "only one tag is shown listed", "I can't confirm a total count beyond the one displayed" |
| Q16 M1 | misread | `kodekloudapps:v1` |
| Q16 M2 | time misread | the transcript's "User hits Enter at 12:47" |
| Q17 M2 | invented | the transcript's second-run output `kodekloudapp 0/1 1 0 4s` at 12:48; frame 201 (12:48.0) shows `1/1 1 1 20s`, and no `0/1` deployment output is on any frame. G1's answer to Q17 invents the same output and adds a third run |
| Q19 M2 | misread | `10.0.198.121` |

Not visible at the sampling: no failed line could be attributed to that with confidence, because the agentic mode does
not say which segments it fetched. Every failed exact string is on a settled frame for seconds (the resource group
name for two minutes, the IPs for 40 s, the Docker Hub page for 3 s), so these are readings, not misses. The
transcript's omissions (Q5's detour of 8 s, Q8's typing and error of about 2 s, Q15's tag count) are the closest thing
to a sampling loss, and there the answerer said so.

## Exactness, checked mechanically

Every "contains the exact string" line (14 per arm) was checked as P6's analyst did: the string is or is not in the
answer character for character. Judge and check agree on all 28. G1 has 7 of 14 exact, G2 8 of 14; the pipeline
(P4, four runs) 14 of 14 in each. The inexact strings, beside the pipeline's rendering (the judge's quote from P4
annotated r1, which cites a frame and a box id where it read pixels):

| Q, line | expected | G1 wrote | G2 wrote | P4 wrote |
|---|---|---|---|---|
| Q4 M1 | `RG1-KodeKloud-AKS` | `RG1-kodecloud-AKS` | `R01-KodeKloud-AKS` | `RG1-KodeKloud-AKS` |
| Q11 M1 | `crkodekloud` | `cklcloudaks1` | `ckadkodekloud` | `crkodekloud` |
| Q12 M1 | `MC_RG1-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia` | `..._AKS1-KodekloudApp_...` | `MC_R01-KodeKloud-AKS_...` | exact |
| Q15 M1 | `hpranav/kodekloudappcs` | `hpranav/kodekloudapps` | `hpranav/kodekloudapps` | `hub.docker.com/repository/docker/hpranav/kodekloudappcs/general` |
| Q16 M1 | `... --image=hpranav/kodekloudappcs:v1 --replicas=1` | `...kodekloudapp:v1...` | `...kodekloudapps:v1...` | exact |
| Q19 M1 | `20.247.251.108` | `20.247.253.108` | exact | `20.247.251.108 (213:b115)` |
| Q19 M2 | `10.0.199.121` | `10.0.198.121` | `10.0.198.121` | `10.0.199.121 (213:b114)` |

The exact strings both arms got right: `HCL`, `HNS`, `1.24.9`, `1.24.10`, `10.224.0.0/16`, `microsoft.aks-20230404212734`,
`10.224.0.31`. The misreads are single characters in IPs and identifiers, and capitalisation in names; the one string
Gemini cannot read at all is the registry name typed into a side panel (five readings, none right, none alike). The
pipeline's OCR read every one of these strings correctly (the question file's Evidence lines), and its answers cite the
frame and box.

Other misreads in the transcript, outside the rubric (checked on frames 201 and 213): the prompt `PS C:\Users\acadeix>`
for `msadmin`, the port `80:30863/TCP` for `80:30895/TCP`, the pod `67ffc75dc5` for `67ffc758c5`, `0/1 Running 20s` for
`1/1 Running 34s`, the correlation ID, the Review + create tab's version `1.24.10` for `1.24.9`, and the version list.

## G1c, the command list, scored by hand

One call, 384 s, $0.97 (1.24 million tool-use tokens: it read the whole terminal section). Against the accepted
executed list of `span2-commands.md` (frames 155 to 187; "time" is Gemini's against the ground truth's submitted time):

| # | ground truth | Gemini listed | found | exact | within 10 s |
|---|---|---|---|---|---|
| 1 | `az account show`, 10:29.6 | `az account show`, 10:29 | yes | yes | yes |
| 2 | `az configure --defaults group=RG1-KodeKloud-AKS`, 10:53.6 | the same, 10:54 | yes | yes | yes |
| 3 | `az aks get-Credentials --name AKS1-KodeKloudApp`, 10:59.3 | `az aks get-credentials --name AKS1-KodeKloudApp`, 10:58 | yes | no (C to c) | yes |
| 4 | `Y`, 11:00.8 | one note: "typing `y` at 11:03 to confirm the overwrite prompt" | no (one answer listed where two were given) | no | |
| 5 | `y`, 11:04.1 | `y`, 11:03 | yes | yes | yes |
| 6 | `kubectl config current-context`, 11:17.1 | 11:14 | yes | yes | yes (3 s; 11:14.2 is when it became visible) |
| 7 | `kubectl get nodes`, between 11:39.7 and 11:42.0 | 11:42 | yes | yes | yes |
| 8 | `kubectl get deployment`, 11:56.9 | 11:56 | yes | yes | yes |
| 9 | `kubectl get pods`, between 11:56.9 and 12:01.0 | 11:58 | yes | yes | yes |

Found 8 of 9, exact 7 of 9, every found command within 10 s. Of the five strings that appeared but never ran
(`az login`, `az aks scale ...`, `kubectl rollout undo deployment/kodekloudapp`, the second `kubectl config
current-context`, `kubectl get svc`), Gemini lists none as run: 0 false runs of 5. After the span (checked on frame
213) it lists five more: `kubectl create deployment ... --image=hpranav/kodekloudapps:v1 --replicas=1` at 12:44
(inexact, `cs` to `s`; run at 12:39.5), `kubectl get deployment` 12:48, `kubectl get pods` 12:53, `kubectl expose ...`
13:48 and `kubectl get service` 13:55, all four exact and on time; it names `kubectl get service`, the executed line,
where G1 and the transcript name the suggestion `svc`. Of 13 commands over the whole video, 11 exact. So the one long
call read the terminal better than the per-question calls and the transcript, at a third of a question set's price.

## The contract: typed against suggested, ran against shown

Every G1 and G2 answer to Q16, Q17, Q18, Q19, Q21, Q22 and Q23 to Q27 was read in full, and the transcript.

**The transcript itself.** In one place it distinguishes a suggestion from typed text: at 10:55, "(Shell auto-suggests
in gray `--node-count 2`, which the user does not use)", a garbled sighting of the `az aks scale ... --node-count 2`
suggestion of frame 165. Everywhere else it does not, and it records as executed a command that was only a suggestion:
"**10:21** User types command: `az login`. User hits Enter at **10:27**. **10:29** Command output displayed:" followed by
the JSON that `az account show` printed. `az login` is the first row of the never-run section (a grey suggestion after
`a` on frame 155, cleared on frame 156); `az account show`, the command that did run, is absent from the transcript.
It also records two runs that are on no frame, with output: "**12:51** User types command: `kubectl get nodes`" (a
second run, "48m v1.24.10") and "**13:02** `kubectl get pods -A`" with three lines of system pods; and the
`kubectl get deployment` output `0/1 1 0 4s`.

**G1 (Gemini answering).**

- Q16: "(Typed between **12:20** and **12:40**, and displayed fully at the prompt at **12:40**–**12:47**)" and "The
  command was executed at **12:47**–**12:48**." It says nothing of the grey suggestion that supplied most of the line
  at 12:20 (frame 190); it does not claim the line was typed by hand either. The time is 8 s late.
- Q17: "the command `kubectl get deployment` is run **three** times", with "**2. Second Run (~12:47 – 12:48)** ...
  `kodekloudapp 0/1 1 0 4s`" and "**3. Third Run (~12:50)** ... `kodekloudapp 1/1 1 1 20s`". The second run and its
  output are invented; the rubric (twice, first empty, second 1/1) is blind to a third run and scored it correct.
- Q18: "is run **2 times on-screen** (and appears in total **3 times** in the terminal session, including one execution
  that occurred off-screen)", then "**2. Second Run** Executed at **12:53** ... `0/1 ContainerCreating 0 2s`" and
  "**3. Third Run** Executed at **12:57** ... `1/1 Running 0 19s`". The run "at 12:57" falls where the shell showed
  `kubectl get pods` in grey after `ku`, `kubect`, `kubectl ` (frames 205 to 207, 12:59 to 13:07): the suggestion
  taken as a run, with an output written for it. This is the failure the owner's contract names.
- Q19: "**Command:** `kubectl get svc` (executed at 13:54–13:56)". The typed text was `kubectl get s` with `vc` in
  grey (frame 212); the executed line reads `kubectl get service` (frame 213). The suggestion is named as the command.
- Q21: order right; "the field `Registry name *` is populated with `ckckkcloud`" (a misread quoted as exact).
- Q22: order and times right; "the command `az aks get-credentials --name AKS1-KodeKloud-AKS` is run (**10:56**)", a
  wrong argument (`AKS1-KodeKloudApp` was typed) and a lower-cased `C`; "`C:\Users\meadmin\.kube\config`" for `msadmin`;
  "showing the tag `v1`" on the Docker Hub page, whose visible tag row is v2.
- Q23 to Q27: every "no" is right and each is argued from what is on screen. Q23 quotes the three Access options and
  the Review + create line correctly. Q24: "At **12:46** ... `kubectl create deployment kodekloudapp
  --image=hpranav/kodekloudapps:v1 --replicas=1`" (time and string off). Q26: "runs `kubectl get svc` in the terminal
  to retrieve the external IP address (`20.247.251.158`)" and "navigates to `20.247.251.158`" (108 read as 158, twice;
  `svc` again). Q27: "a new Azure Container Registry named `ckaklkdecloud` was created".

**G2 (Opus answering over the transcript).**

- Q16: "Command (typed at 12:20, executed/Enter pressed at 12:47)"; then "Immediate follow-up confirmation shown in
  the video" repeating the transcript's invented `0/1 1 0 4s` and `0/1 Running 0 20s` outputs.
- Q17: "`kubectl get deployment` appears **twice**" (right), "2nd run ... around 12:48 ... `kodekloudapp 0/1 1 0 4s`"
  (the transcript's invention), and "Note: the transcript shows no other runs of `kubectl get deployment`."
- Q18: "was run **twice** (11:58 and 12:53). A third, related run used the `-A` flag (`kubectl get pods -A`) at 13:02
  ... whether you count that depends on whether you treat the flagged variant as the same command." The `-A` run never
  happened; Opus reports it as fact because the transcript does, and scopes its count honestly: "I'm working only
  from the transcript of the video".
- Q19: "**Command used:** `kubectl get svc` ... typed at **13:51**" (the transcript's word).
- Q21: order right; "types `ckad` ... then types `ckadkodekloud`".
- Q22: order right; "It is preceded by `az login` at **10:21** (Enter at 10:27)": the never-run command reported as
  run, inherited. Q23 repeats it: "at **10:21 – 10:29** the presenter ran `az login` in PowerShell, which
  authenticates the Azure CLI to the subscription".
- Q24 to Q27: every "no" right; Q24 and Q27 repeat the invented outputs ("later `1/1 Running` (13:02)"); Q26 ends
  "if the presenter mentioned cleanup verbally, that would not be captured here" (the video has no audio).

Summary of the contract reading: G1 takes a grey suggestion as a run once (Q18) and names the suggestion form of a
command as the command twice (Q19, Q26); it invents runs with output in Q17 and Q18. The transcript records one
never-run suggestion as executed (`az login`) and two runs that are on no frame, and every G2 answer that touches those
moments repeats them; Opus adds nothing of its own and says when the transcript is silent (Q5, Q8, Q15, Q17, Q18).
In P4 and P9 no answer took a suggestion for a run and no on-screen text was invented (`docs/results/p9/analysis.md`).

## Cost and time per question

| arm | one-time per video | per question | seconds per question | notes |
|---|---|---|---|---|
| G1 Gemini direct | upload 25 s, no charge | $0.0785 mean (median $0.039, min $0.018, max $0.334); $2.12 for 27 | 32 mean (median 26, min 12, max 116) | mean per call: prompt 1,028 tokens, tool use 92,940 (video 43,888, text 5,165), thinking 1,676, output 478 |
| G1c command list | | $0.97 for the one call | 384 | 1.24 million tool-use tokens |
| G2 transcript | $0.41, 237 s (7,707 output tokens) | $0.0152 amortised over 27 | 8.8 amortised | 461,781 tool-use tokens, 296,677 of them reported cached |
| G2 Opus answers | | $0.0230 mean ($0.62 for 27); $0.0382 with the transcript amortised | 8 (the first eight calls, 5 to 11 s; the recorded mean of 17 s includes queueing behind the 8-call limit) | 9,655 tokens of transcript read from the cache in 26 of 27 calls; 625 output tokens mean |
| pipeline, Opus agent (P4) | $17.85 annotated, $4.62 unannotated | $0.263 annotated, $0.216 unannotated | 22 | plus about 31 min of stage time before `ask` (P4 annotated r1: read 763 s, annotate 742 s, interpret 251 s, summarize 85 s) |
| pipeline, Sonnet agent (P9) | the same build | $0.062 annotated, $0.053 unannotated | 9.5 | |

Break-even, the number of questions on this video after which the pipeline's build plus per-question cost is below
the arm's:

- Opus agent, either base, against G1 or G2: never. G1 ($0.0785) and G2 ($0.038) are cheaper per question than
  $0.216 and have no build.
- Sonnet agent, annotated ($17.85 build, $0.062) against G1: 1,079 questions. Unannotated ($4.62, $0.053) against G1:
  181 questions. Against G2 ($0.038): never.

So on cost alone Gemini wins at any number of questions against the Opus agent, and the Sonnet agent on an unannotated
index pays for itself after about 180 questions on the video. On time, G1 at 32 s is slower than the pipeline's 22 s
(Opus) or 9.5 s (Sonnet) per question once the index exists; G2's Opus call at 8 s is the fastest of all after its
one 4-minute transcript. The per-question G1 table is in `tables.md`; the costly calls are the ones that scanned the
terminal section (Q11 $0.33, Q18 $0.30, Q17 $0.22, Q7 $0.17).

## Citations

Every one of the 54 answers gives mm:ss times, 7 per answer in G1 (at least 3), 12 in G2 (at least 4); none names a
frame, a box or anything else that resolves to a stored artifact. The times are the model's own clock: for the one
event of the `kubectl create deployment` run, G1's calls say 12:38, 12:44, 12:46, 12:47 and 12:48, and the G2 transcript
12:47, for an output that is on screen from 12:39.5. So a reader can verify a Gemini claim only by opening the video and
scrubbing to about the stated second, and when the claim is a misread digit or an invented run, the video at that
second shows something else. Three G1 answers and four G2 answers say the video (or the transcript) does not show
something; G2's were the honest ones on Q5, Q8 and Q15, and G1's are on the negatives, where they are right. The
pipeline's answers cite frame and box ids ("20.247.251.108 (213:b115)"), which resolve to a frame image and an OCR
record under the run directory, and they were checked that way in P4, P6 and P9.

## What this does and does not show

One video, 27 draft questions that the owner has not accepted, one run of each Gemini arm (no repeat, so the repeat
noise is unknown; the pipeline's repeats agreed on 83 of 83 lines), and a rubric that is blind to the contract: Q17 was
scored correct with an invented run in it, and Q8 was scored wrong for saying honestly that the transcript shows no
error. On this sample Gemini in agentic video mode answers the questions that ask when, in what order and whether
something happened as well as the pipeline does, for a fifth to a tenth of the price per question and with no build,
and it loses on exact text: 7 of 14 and 8 of 14 exact strings against 14 of 14, single characters in IPs and
identifiers, one name it could not read in five tries, and a start time both arms misread the same way. It also
invents terminal runs with plausible output (three in G1's answers, three in the transcript) and once takes the shell's
grey suggestion for a run, which is what the pipeline was built not to do. Whether these misreads are a matter of the
model's video sampling, of the specific frames the agentic mode chose to fetch, or of the model, this run cannot say:
the API does not report which segments were fetched, and the one long call (G1c) read 11 of 13 commands exactly where
the per-question calls did not. The prices are list prices for tokens the API reported, some of them marked cached and
not discounted here; the pipeline's dollars are the phases' recorded figures. Nothing here measures a second video, a
different question style, or Gemini's static (non-agentic) mode beyond one call.

## Files

- `compare/gemini/common.py` (client, upload, call shape, prices, ledger), `g1.py`, `g1c.py`, `g2.py`, `judge.py`,
  `cache_try.py`, `analyze.py` (all tables above, no model calls).
- `runs/compare-gemini/` (git-ignored): `g1/answers.jsonl`, `g1/judgments.jsonl`, `g1/raw/Q*.json` (full usage and
  steps per call), `g1c/answer.json`, `g2/transcript.{json,md}`, `g2/answers.jsonl`, `g2/judgments.jsonl`,
  `g2/raw/Q*.json`, `judge-cache/`, `cache-try.json`, `spend.jsonl` (one line per call), `upload.json`.
- `docs/results/compare-gemini/tables.md`: the output of `python -m compare.gemini.analyze`.
