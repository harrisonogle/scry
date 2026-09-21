# Question set: frames 155-187 of the sample video (span 2)

Status: **DRAFT for the owner to correct. Nothing here is accepted yet.** Correct a question, a reference answer or a
rubric line in place, delete what you do not want asked, add what is missing; the evaluation harness reads whatever
this file holds when a phase runs (the file's hash is recorded in every scorecard, and a reworded question never pairs
with answers to its old wording). Corrected on 2026-09-21 after the review of build plan 4 (ledger L50): a time scope
on Q9, Q13 and Q15; one `M` line and one `X` line on every negative question; Q5's second line loosened; and the rule
below saying which rubric lines require an exact string. It is still a draft.

Source: written only from `docs/ground-truth/span2-commands.md` (the owner-accepted list of 9 executed entries and the
5 strings that appeared on screen and were never run). No fact below comes from anywhere else. Wording of the on-screen
strings was checked by eye against `runs/span2-before/frames/00171.png`, `00178.png` and `00187.png`. Minutes and
seconds for the never-run rows are computed from that file's seconds (620.67 s = 10:20.7, and so on). Things that are
visible on the frames but are not in the ground-truth file (the fields of the `az account show` output, the node table
printed by `kubectl get nodes`, what `kubectl get pods` printed, the portal pages of frames 182-184) are deliberately
not asked about; add them to the ground-truth file first if they should be.

Scope: every question is about the terminal session between 10:20.7 (frame 155) and 12:01.0 (frame 187). Where an
unscoped question could have a different answer elsewhere in the video, the question text carries the time scope
("between 10:20 and 12:01": Q9, Q10 and Q12 to Q15). The shell's suggestions come from its history, so a suggested
command may well have been run earlier in the full video.

Weighting (owner's ruling): the **positive** questions Q1-Q11 are the question-set score. The **negative** questions
Q12-Q15, whose correct answer is no, are **secondary**: they are reported beside the positive score and break ties only.

How an answer is scored: each rubric line is a statement about the answer. `M` lines must be true of the answer; `X`
lines must not be. A separate model call, which does not know which run produced the answer, decides each line, and
code derives the label: an answer is *correct* when every `M` line holds and no `X` line does, *wrong* when any `X`
line holds or no `M` line holds, and *partial* otherwise.

Which lines require an exact string: **only a line that says "contains the exact string"** (today Q2 M1 and Q3 M1).
There the string must appear in the answer character for character, including case. Every other line is judged on
meaning: "names the command", "gives the output" or "says …" holds when the answer unmistakably refers to the same
thing, whatever its spelling, spacing or case. "Gives a time between A and B" is also satisfied by naming a frame in
the stated range.

Negative questions: each has exactly one `M` line (the answer says no) and one `X` line (the precise wrong claim), so
a plain, correct "No" is *correct*, as the owner's wording asks ("must be answered no"). The explanation in the
reference answer (it appeared only as a suggestion) is for people and is not scored.

Format (read by `scry.evaluation.questions.parse_questions`; keep it): a heading `### Q<n> (<positive|negative>,
<style>)`, then the bullets **Question**, **Reference answer**, **Rubric** (indented `M<n>:` and `X<n>:` lines) and
**Evidence**, which is for people: the harness does not read it.

## Positive questions

### Q1 (positive, exact-string lookup)
- **Question:** Where in the terminal session does `az account show` get run?
- **Reference answer:** `az account show` is fully typed at frame 157 (10:28.8) and submitted by frame 158 (10:29.6),
  where its JSON output and a new prompt appear. It is the first of the executed entries in frames 155-187.
- **Rubric:**
  - M1: says that `az account show` was executed, not merely shown.
  - M2: gives a time between 10:28 and 10:30, or frame 157 or 158.
  - X1: says the command was not run, or that it cannot be found.
- **Evidence:** executed row 1; frames 157-158; t 628.77-629.57

### Q2 (positive, what command did they use to)
- **Question:** What command did the presenter use to set the default resource group for the Azure CLI?
- **Reference answer:** `az configure --defaults group=RG1-KodeKloud-AKS`. It is first on screen at frame 161 (10:49.2),
  partly typed with the shell's suggestion showing the rest, fully typed from frame 162 (10:52.0), and submitted by
  frame 164 (10:53.6): a new prompt appears below it and there is no output.
- **Rubric:**
  - M1: contains the exact string `az configure --defaults group=RG1-KodeKloud-AKS`.
  - X1: gives a different command as the one that set the default.
- **Evidence:** executed row 2; frames 161-164; t 649.17-653.57

### Q3 (positive, exact string with capitalisation)
- **Question:** What exactly did they type to fetch the cluster credentials? I need it as shown on screen, capitalisation included.
- **Reference answer:** `az aks get-Credentials --name AKS1-KodeKloudApp`, with a capital `C` in `get-Credentials` as
  displayed. First on screen at frame 166 (10:56.2) partly typed with the shell's suggestion, fully typed from frame 167
  (10:57.1), submitted by frame 169 (10:59.3).
- **Rubric:**
  - M1: contains the exact string `az aks get-Credentials --name AKS1-KodeKloudApp`, capital `C` included.
  - X1: presents a lower-case `get-credentials` as the form shown on screen.
- **Evidence:** executed row 3; frames 166-169; t 656.20-659.27

### Q4 (positive, what did they answer when asked to overwrite)
- **Question:** When the CLI asked whether to overwrite, what did the presenter answer?
- **Reference answer:** It asked twice (`Overwrite? (y/n):`) and both times the answer was yes: `Y` to the first
  question, about the object AKS1-KodeKloudApp (question on screen at frame 169, answer visible at frame 170, 11:00.8),
  and `y` to the second, about the object clusterUser_RG1-KodeKloud-AKS_AKS1-KodeKloudApp (question at frame 170,
  answer visible at frame 171, 11:04.1).
- **Rubric:**
  - M1: says the presenter answered yes (`Y` or `y`).
  - M2: says there were two overwrite questions and that both were answered yes.
  - X1: says the presenter answered no, or declined to overwrite.
- **Evidence:** executed rows 4 and 5; frames 169-171; t 659.27-664.13

### Q5 (positive, what happened next)
- **Question:** After the overwrite questions were answered, what did the CLI report?
- **Reference answer:** At frame 171 (11:04.1), after the second `y`, it printed
  `Merged "AKS1-KodeKloudApp" as current context in C:\Users\msadmin\.kube\config` and a new prompt appeared.
- **Rubric:**
  - M1: says AKS1-KodeKloudApp was merged as the current context.
  - M2: says the context was merged into the kube config file (`.kube\config`).
  - X1: says the merge failed or was cancelled.
- **Evidence:** executed row 5; frames 171-171; t 664.13-664.13

### Q6 (positive, when did they)
- **Question:** When did they check which kubectl context was active, and what came back?
- **Reference answer:** With `kubectl config current-context`: first on screen at frame 175 (11:14.2) partly typed with
  the shell's suggestion, fully typed at frame 176 (11:16.3), submitted by frame 177 (11:17.1). The output was
  `AKS1-KodeKloudApp`.
- **Rubric:**
  - M1: names the command `kubectl config current-context`.
  - M2: gives the output `AKS1-KodeKloudApp`.
  - M3: gives a time between 11:14 and 11:18, or a frame from 175 to 177.
  - X1: places the execution at about 11:38 (frame 178), where the same text only re-appeared as a suggestion.
- **Evidence:** executed row 6; frames 175-177; t 674.23-677.13

### Q7 (positive, what command did they use to)
- **Question:** Which command did they use to list the cluster's nodes, and roughly when?
- **Reference answer:** `kubectl get nodes`, submitted between frame 179 (11:39.7) and frame 180 (11:42.0). It is first
  seen at frame 180 already in the scrollback with its output; the typing itself was not observed.
- **Rubric:**
  - M1: names the command `kubectl get nodes`.
  - M2: gives a time between 11:39 and 11:43, or frame 179 or 180.
  - X1: gives `kubectl get svc` as the command that was run.
- **Evidence:** executed row 7; frames 179-180; t 699.70-702.03

### Q8 (positive, did they and what was the result)
- **Question:** Did they look for deployments in the cluster, and what did kubectl say?
- **Reference answer:** Yes: `kubectl get deployment`, first on screen at frame 185 (11:56.5) as `kubectl get deplo`
  with the suggestion `yment`, submitted by frame 186 (11:56.9). kubectl answered "No resources found in default
  namespace."
- **Rubric:**
  - M1: names the command `kubectl get deployment`.
  - M2: says no resources were found in the default namespace.
  - X1: says a deployment was listed or exists.
- **Evidence:** executed row 8; frames 185-186; t 716.53-716.90

### Q9 (positive, exact-string lookup)
- **Question:** Is `kubectl get pods` run anywhere between 10:20 and 12:01? Where?
- **Reference answer:** Yes, once, at the very end: it was submitted between frame 186 (11:56.9) and frame 187
  (12:01.0), and is first visible at frame 187 already in the scrollback with its output. The typing itself was not
  observed.
- **Rubric:**
  - M1: says `kubectl get pods` was run.
  - M2: gives a time between 11:56 and 12:02, or frame 186 or 187.
  - X1: says it was not run.
- **Evidence:** executed row 9; frames 186-187; t 716.90-721.00

### Q10 (positive, order)
- **Question:** List, in order, every command that was actually executed in the terminal between 10:20 and 12:01.
- **Reference answer:** (1) `az account show`; (2) `az configure --defaults group=RG1-KodeKloud-AKS`;
  (3) `az aks get-Credentials --name AKS1-KodeKloudApp`, followed by the answers `Y` and `y` to its two overwrite
  questions; (4) `kubectl config current-context`; (5) `kubectl get nodes`; (6) `kubectl get deployment`;
  (7) `kubectl get pods`.
- **Rubric:**
  - M1: lists all seven commands (the two overwrite answers may be left out or mentioned).
  - M2: gives them in the order of the reference answer.
  - X1: lists as executed any of `az login`, `az aks scale`, `kubectl rollout undo`, `kubectl get svc`.
- **Evidence:** executed rows 1-9; frames 157-187; t 628.77-721.00

### Q11 (positive, order)
- **Question:** What did they run right after checking the current context?
- **Reference answer:** `kubectl get nodes` (submitted between 11:39.7 and 11:42.0). In between, `kubectl config
  current-context` re-appeared from history at frame 178 and `kubectl get svc` was suggested at frame 179; neither was run.
- **Rubric:**
  - M1: answers `kubectl get nodes`.
  - X1: answers `kubectl get svc`, or a second `kubectl config current-context`.
- **Evidence:** executed rows 6 and 7, never-run rows 4 and 5; frames 177-180; t 677.13-702.03

## Negative questions (secondary)

### Q12 (negative, did they)
- **Question:** Between 10:20 and 12:01, did the presenter roll back the deployment?
- **Reference answer:** No. `kubectl rollout undo deployment/kodekloudapp` was on screen at frames 172-174
  (11:08.1-11:09.5) only as the shell's suggestion, while the presenter had typed `kubect` and then `kubectl`. At frame
  175 the same row shows `kubectl config` with a different suggestion. It was never run.
- **Rubric:**
  - M1: says no rollback was performed (the command was not run).
  - X1: says the deployment was rolled back, or that `kubectl rollout undo` was executed.
- **Evidence:** never-run row 3; frames 172-175; t 668.13-674.23

### Q13 (negative, did they)
- **Question:** Between 10:20 and 12:01, did they scale the cluster, to two nodes or otherwise?
- **Reference answer:** No. `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2`
  appeared at frame 165 (10:55.0) as the shell's suggestion after the presenter had typed `az ak`. Frame 166 shows
  `az aks get` with a different suggestion on the same row. It was never run.
- **Rubric:**
  - M1: says the cluster was not scaled (the command was not run).
  - X1: says the cluster was scaled, or that `az aks scale` was executed.
- **Evidence:** never-run row 2; frames 165-166; t 655.00-656.20

### Q14 (negative, exact-string lookup)
- **Question:** Did the presenter run `az login` in the terminal between 10:20 and 12:01?
- **Reference answer:** No. `az login` was on screen at frame 155 (10:20.7) as the shell's suggestion after the
  presenter had typed `a`. Frame 156 shows a bare prompt on the same row: the line was cleared, not run.
- **Rubric:**
  - M1: says `az login` was not run in the time asked about.
  - X1: says `az login` was executed, or that the presenter logged in with it, in the time asked about.
- **Evidence:** never-run row 1; frames 155-156; t 620.67-620.67

### Q15 (negative, how many times)
- **Question:** Between 10:20 and 12:01, was `kubectl config current-context` run more than once?
- **Reference answer:** No. In that time it was run once (submitted by frame 177, 11:17.1). At frame 178 (11:38.1) the
  same text re-appeared from history as a suggestion after the presenter had typed `kubect`; frame 179 (11:39.7) shows
  `kubectl get` with the suggestion ` svc`. It was not run a second time.
- **Rubric:**
  - M1: says it was run once in that time, or not run a second time.
  - X1: says it was run twice or more in that time.
- **Evidence:** executed row 6, never-run row 4; frames 177-179; t 677.13-699.70
