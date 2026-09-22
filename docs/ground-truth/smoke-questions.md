# Question set: frames 145-155 of the sample video (graphical content)

Status: **DRAFT written by an agent from the frames, for the owner to correct. Nothing here is accepted yet.** Correct a
question, a reference answer or a rubric line in place, delete what you do not want asked, add what is missing; the
evaluation harness reads whatever this file holds when a phase runs (the file's hash is recorded in every scorecard,
and a reworded question never pairs with answers to its old wording).

Why this set exists (ledger L57): the 15 questions of `span2-questions.md` were written from a list of terminal
commands, and every pipeline variant scored 100 % on them, including the one with no screen annotation, because OCR
reads terminal text exactly. These questions ask about what annotation is for: which label goes with which value on a
portal page, which window or area a text belongs to, and state that is not text (a selected tab, a highlighted menu
entry, a greyed-out button, a tooltip and what it hangs on), plus the order of events across the span.

Source: written by an agent that looked at `runs/p0/frames/00145.png` to `00155.png` (1920x1080), each one whole and
then in enlarged crops of the regions asked about. There is no owner-accepted ground-truth file behind this set, as
there was for span 2: **the reference answers below are the proposed ground truth**, and every one was checked against
the image itself. Times are `t_settled` of `runs/p0/frames.jsonl`, written as minutes and seconds (587.87 s = 9:47.9);
where a frame's `t_change` or `t_end` is used, the text says so. `runs/p0/boxes.jsonl` was consulted only for the
spelling of strings; where OCR and the image differ, the image wins and the Evidence line says so. No model was called
and no pipeline stage was run to write this file. Nothing here depends on guessing what the presenter meant to do.

What the frames show, as read from the images:

| Frame | Time | On screen |
|---|---|---|
| 145 | 9:22.8 (from 9:19.8) | Azure portal, deployment page `microsoft.aks-20230404212734 \| Overview`: "Deployment is in progress". No browser chrome in the picture. |
| 146 | 9:24.3 (9:22.8-9:25.5) | Title slide: "Deploying our sample application to AKS Cluster". |
| 147 | 9:25.8 (until 9:46.1) | Browser on the portal's overview page of the Kubernetes service `AKS1-KodeKloudApp`; a PowerShell window in front of it with an empty prompt. |
| 148 | 9:47.9 | PowerShell window no longer on screen; whole portal page visible; hand pointer on the first icon right of the portal's search box; the browser's status bubble `https://portal.azure.com/#` at the bottom left. |
| 149 | 9:48.7 (until 9:51.5) | The same, with a tooltip under that icon: "Cloud Shell" (the hand hides its first two letters). |
| 150 | 9:52.1 | Pointer, tooltip and status bubble gone; page unchanged. |
| 151 | 9:53.7 (until 9:54.3) | A bordered tooltip "Administrator: PowerShell 7-preview (x64)" at the lower middle of the screen, over the portal page; no pointer and no PowerShell window visible. |
| 152 | 9:54.5 | Tooltip gone; a vertical double-headed arrow pointer over the value of "Workspace resource ID" at the lower right. |
| 153 | 9:56.5 | An arrow pointer at the very bottom edge of the picture, mostly cut off. |
| 154 | 9:58.7 (from 9:57.8) | PowerShell window back, same place and size, prompt still empty; arrow pointer inside it. |
| 155 | 10:20.7 (until 10:23.7) | One character `a` typed at the prompt, followed by the shell's greyed suggestion `z login`. |

Scope: every question is about what was on screen between 9:19.8 (start of frame 145) and 10:23.7 (end of frame 155).
Portal pages and the terminal appear elsewhere in the video too, so the question texts carry a time ("around 9:50",
"between 9:25 and 10:24"). Frame 155 is also the first frame of span 2.

Types: (a) label and value lookups Q1-Q4; (b) which window or area Q5-Q6; (c) state that is not text Q7-Q11; (d) what
happened, in order Q12-Q14; (e) negative questions Q15-Q18.

Weighting (as in span 2): the **positive** questions Q1-Q14 are the question-set score. The **negative** questions
Q15-Q18, whose correct answer is no, are **secondary**: they are reported beside the positive score and break ties only.

How an answer is scored: each rubric line is a statement about the answer. `M` lines must be true of the answer; `X`
lines must not be. A separate model call, which does not know which run produced the answer, decides each line, and
code derives the label: an answer is *correct* when every `M` line holds and no `X` line does, *wrong* when any `X`
line holds or no `M` line holds, and *partial* otherwise.

Which lines require an exact string: **only a line that says "contains the exact string"** (here Q1 M1, Q3 M1 and
Q3 M2). There the string must appear in the answer character for character. Every other line is judged on meaning:
"names the tab", "gives the text" or "says …" holds when the answer unmistakably refers to the same thing, whatever its
spelling, spacing or case. "Gives a time between A and B" is also satisfied by naming a frame in the stated range.

Negative questions: each has exactly one `M` line (the answer says no) and one `X` line (the precise wrong claim), so
a plain, correct "No" is *correct*. The explanation in the reference answer is for people and is not scored.

Format (read by `scry.evaluation.questions.parse_questions`; keep it): a heading `### Q<n> (<positive|negative>,
<style>)`, then the bullets **Question**, **Reference answer**, **Rubric** (indented `M<n>:` and `X<n>:` lines) and
**Evidence**, which is for people: the harness does not read it.

## Positive questions

### Q1 (positive, a value shown in several places)
- **Question:** According to the portal page shown around 9:50, which Kubernetes version is the AKS1-KodeKloudApp
  cluster on, and where on the page is that stated?
- **Reference answer:** 1.24.10, and the overview page states it three times: in the Essentials block at the top right
  ("Kubernetes version : 1.24.10", a link); on the Properties tab under the heading "Node pools" ("Kubernetes versions
  1.24.10"); and on the Properties tab under the heading "Configuration" ("Kubernetes version 1.24.10"). The three agree.
- **Rubric:**
  - M1: contains the exact string `1.24.10`.
  - M2: says the version is shown in more than one place on the page and names at least two of these: the Essentials
    block, the Node pools section, the Configuration section.
  - X1: gives any other version number as the cluster's Kubernetes version.
- **Evidence:** frames 148-153 (all three also stay visible around the PowerShell window on 147, 154 and 155);
  t 587.87-596.47. OCR reads all three correctly (the Essentials one as `:1.24.10`).

### Q2 (positive, label and value where two columns interleave)
- **Question:** On the cluster's Properties tab around 9:50, what is the Auto Upgrade Type, and are local accounts enabled?
- **Reference answer:** Auto Upgrade Type is "Patch" and Local accounts is "Enabled". Both are in the "Configuration"
  section of the left column, together with Kubernetes version 1.24.10 and Authentication and Authorization "Local
  accounts with Kubernetes RBAC". At the same heights the right column reads Private cluster, Authorized IP ranges and
  Application Gateway ingress controller, each "Not enabled"; those values belong to the right column's labels.
- **Rubric:**
  - M1: gives Patch as the Auto Upgrade Type.
  - M2: says local accounts are enabled.
  - X1: says local accounts are not enabled, or gives "Not enabled" as the Auto Upgrade Type.
- **Evidence:** frames 147-155 (this part of the left column is never covered); t 565.80-620.67. OCR puts the label
  "Authentication and Authorization" and its value in one box on most frames; "Local accounts" (y 893) sits 9 pixels
  below the right column's "Not enabled" (y 884).

### Q3 (positive, similar labels)
- **Question:** What Service CIDR and what DNS service IP does the portal show for the cluster at about 9:50?
- **Reference answer:** Service CIDR 10.0.0.0/16 and DNS service IP 10.0.0.10, in the "Networking" section in the right
  column of the Properties tab. The same section also lists Pod CIDR, whose value is a dash, and Docker bridge CIDR
  172.17.0.1/16; those are different settings.
- **Rubric:**
  - M1: contains the exact string `10.0.0.0/16`, given as the Service CIDR.
  - M2: contains the exact string `10.0.0.10`, given as the DNS service IP.
  - X1: gives `172.17.0.1/16` as the Service CIDR, or gives the two asked-for values the wrong way round.
- **Evidence:** frames 148-153 only (on 147, 154 and 155 the PowerShell window covers these rows); t 587.87-596.47.
  OCR reads the four values correctly.

### Q4 (positive, a list that spans both columns)
- **Question:** Which features does the cluster's Properties tab list as "Not enabled" at about 9:50?
- **Reference answer:** Five. In the left column, under "Kubernetes services": Virtual node pools. In the right column,
  under "Networking": HTTP application routing, Private cluster, Authorized IP ranges and Application Gateway ingress
  controller. Two settings read "Enabled": Local accounts (left column, Configuration) and Container insights (right
  column, Integrations). Network Policy reads "None" and Pod CIDR a dash, which is not the same wording.
- **Rubric:**
  - M1: names all four Networking items: HTTP application routing, Private cluster, Authorized IP ranges, Application
    Gateway ingress controller.
  - M2: names Virtual node pools.
  - X1: lists Local accounts or Container insights as not enabled.
- **Evidence:** frames 148-153; t 587.87-596.47. OCR has five `Not enabled` boxes and two `Enabled` boxes; the left
  column's `Enabled` (y 882-903) overlaps in height the right column's last `Not enabled` (y 874-893).

### Q5 (positive, left navigation versus main pane)
- **Question:** On the AKS1-KodeKloudApp page around 9:50 the word "Networking" shows up in two places. Where is each one?
- **Reference answer:** Once as an entry of the left navigation menu, in the group "Settings", between "Cluster
  configuration" and "Extensions + applications (preview)". Once in the main pane, as the blue heading of the section at
  the top of the right column of the Properties tab, above API server address, Network type (plugin), the CIDR rows and
  the rest of the network settings.
- **Rubric:**
  - M1: says one of them is an entry of the left navigation menu (under Settings).
  - M2: says the other is a section heading in the main pane, on the Properties tab, above the network settings.
  - X1: puts both in the same area, or says Networking is the highlighted entry of the menu.
- **Evidence:** frames 148-153 (menu entry at about x 83, y 790; heading at about x 1243, y 547); t 587.87-596.47.
  On 147, 154 and 155 the heading is behind the PowerShell window and only the menu entry is visible.

### Q6 (positive, which window)
- **Question:** At about 9:26 there is a prompt `PS C:\Users\msadmin>` on screen. Which window is it in, and what else
  is on screen with it?
- **Reference answer:** It is in a PowerShell window titled "Administrator: PowerShell 7-preview (x64)", a smaller
  window standing in front of the browser. The prompt is empty: a cursor and nothing typed. The browser behind it (tab
  "AKS1-KodeKloudApp - Microsoft…", address `portal.azure.com/…/managedClusters/AKS1-KodeKloudApp/overview`) shows the
  Azure portal's overview page of the Kubernetes service AKS1-KodeKloudApp; the PowerShell window covers the middle and
  right of that page, and the left menu, the left part of Essentials and of the Properties tab, and the rows below the
  window stay visible.
- **Rubric:**
  - M1: says the prompt is in a PowerShell (terminal) window.
  - M2: says that window is in front of, or partly covering, a browser showing the Azure portal page of AKS1-KodeKloudApp.
  - X1: says the prompt is in Azure Cloud Shell, or that it is part of the browser or of the portal page.
- **Evidence:** frame 147 (on screen 9:25.8-9:46.1), the same again on frame 154; t 565.80-586.13 and 598.73. The
  window occupies about x 660-1680, y 320-853.

### Q7 (positive, which tab is selected)
- **Question:** Which tab of the cluster's overview page was open while the AKS1-KodeKloudApp page was on screen between
  9:25 and 10:24?
- **Reference answer:** "Properties". It is the one drawn with darker text and a blue underline. The others in the row,
  Get started, Monitoring, Capabilities (3), Recommendations and Tutorials, are not selected, and the selection does not
  change on any frame.
- **Rubric:**
  - M1: names Properties as the selected tab.
  - X1: names any other tab as the selected one.
- **Evidence:** frames 147-155; t 565.80-620.67. With the PowerShell window in front (147, 154, 155) the row is cut
  after "Capabili" but the underlined "Properties" is still visible. Nothing in the OCR text marks the selection.

### Q8 (positive, which navigation entry is highlighted)
- **Question:** In the left-hand menu of the cluster page, which entry was highlighted between 9:25 and 10:24?
- **Reference answer:** "Overview", the first entry, which has a grey background. No other entry of the menu (Activity
  log … Policies, including Node pools, Networking and Configuration) is highlighted on any frame.
- **Rubric:**
  - M1: names Overview as the highlighted entry.
  - X1: names any other entry as the highlighted one.
- **Evidence:** frames 147-155; t 565.80-620.67. (Frame 145, before the slide, shows a different menu, Overview, Inputs,
  Outputs, Template, and its "Overview" is highlighted as well.)

### Q9 (positive, which buttons are disabled)
- **Question:** Were any of the buttons in the toolbar above the cluster's Essentials greyed out between 9:25 and 10:24?
  Which?
- **Reference answer:** Yes, exactly one: "Start", whose icon and label are light grey. The other buttons of that
  toolbar, Create, Connect, Stop, Delete, Refresh, Open in mobile and Give feedback, are drawn as active. The Essentials
  block on the same page gives the status as "Succeeded (Running)". This is not the toolbar of the deployment page seen
  before the slide (frame 145), where Delete and Redeploy are grey and Cancel, Download and Refresh are active.
- **Rubric:**
  - M1: says Start is greyed out (disabled).
  - X1: says that on the cluster page any of Create, Connect, Stop, Delete, Refresh, Open in mobile or Give feedback is
    disabled, or says that no button is disabled.
- **Evidence:** frames 147-155 (toolbar at y 233); t 565.80-620.67. OCR reads the button as `D Start` on most frames
  (the grey triangle read as a letter); nothing in the OCR text marks it as disabled.

### Q10 (positive, a tooltip and what it belongs to)
- **Question:** Around 9:48 the mouse rests on something in the blue bar at the top of the portal and a tooltip pops up.
  What did the tooltip say, and which icon was it for?
- **Reference answer:** "Cloud Shell". The hand pointer rests on the first icon to the right of the search box, the one
  drawn as a terminal prompt, which is the portal's Cloud Shell button. At frame 148 (9:47.9) the pointer is already
  there with no tooltip, and the browser's status bubble `https://portal.azure.com/#` shows at the bottom left; at frame
  149 (9:48.7) the tooltip is under the icon. The hand hides its first two letters, so the visible text is "oud Shell".
  At frame 150 (9:52.1) the tooltip, the pointer and the status bubble are gone and nothing has opened.
- **Rubric:**
  - M1: says the tooltip read Cloud Shell (giving the visible part "oud Shell" and identifying it as Cloud Shell counts).
  - M2: says it belongs to the Cloud Shell icon in the portal's top bar (the first icon right of the search box).
  - X1: attaches the tooltip to a different icon (directory filter, notifications, settings, help, feedback), or gives
    a different tooltip text.
- **Evidence:** frames 148-150; t 587.87-592.13. OCR reads the tooltip as `oud Shell`: correct for the visible pixels;
  the hidden "Cl" is inferred from the icon.

### Q11 (positive, a tooltip and where it was)
- **Question:** A few seconds later, at about 9:54, another tooltip appeared. What was written in it, where on the
  screen was it, and was the window it names visible at that moment?
- **Reference answer:** It read "Administrator: PowerShell 7-preview (x64)", which is the title of the PowerShell
  window. It was a small bordered box at the lower middle of the screen, lying over the portal page, where it covers the
  beginning of the label "Application Gateway ingress controller" in the Networking section. It is there at frame 151
  (9:53.7) and gone at frame 152 (9:54.5). The PowerShell window itself was not on screen at that moment: it is absent
  from frame 148 to frame 153. What the tooltip hangs on cannot be seen: there is no pointer in the frame and the bottom
  of the picture shows no taskbar.
- **Rubric:**
  - M1: gives the tooltip's text as Administrator: PowerShell 7-preview (x64).
  - M2: says it appeared over the browser's portal page, in the lower part of the screen.
  - M3: says the PowerShell window itself was not visible at that moment.
  - X1: says the PowerShell window was open on screen at that moment, or takes the text for a window's title bar.
- **Evidence:** frame 151, and 152 for its absence; t 593.73-594.47. The box is at about x 1065-1327, y 875-907. OCR
  reads the string correctly, and it is the same string OCR reads in the title bar on frames 147, 154 and 155.

### Q12 (positive, the cut to the slide and back)
- **Question:** There is a title card a little after 9:20. What does it say, and what was on screen just before it and
  just after it?
- **Reference answer:** The card says "Deploying our sample application to AKS Cluster" (black text, slanted, between
  two white rules on a pale background): frame 146, on screen from 9:22.8 to 9:25.5. Just before it (frame 145) the
  Azure portal showed the deployment page "microsoft.aks-20230404212734 | Overview" with "Deployment is in progress".
  Just after it (frame 147, 9:25.8) a browser showed the portal's overview page of the Kubernetes service
  AKS1-KodeKloudApp, with a PowerShell window in front.
- **Rubric:**
  - M1: gives the card's text, Deploying our sample application to AKS Cluster.
  - M2: says that before it the portal showed a deployment in progress.
  - M3: says that after it the screen showed the portal page of the AKS1-KodeKloudApp cluster (the PowerShell window may
    be mentioned or not).
  - X1: puts the cluster page before the card, or the deployment-in-progress page after it.
- **Evidence:** frames 145-147; t 562.77-565.80. OCR reads the card as `Deploying our sample` and `applicatíon to AKS
  Cluster` (an accented i that is not in the image) in two large slanted boxes.

### Q13 (positive, order: a window leaves and returns)
- **Question:** Between 9:25 and 10:00 the PowerShell window goes away and comes back. When does each happen, and what
  happens on the portal page in between?
- **Reference answer:** The window is in front of the browser from frame 147 (9:25.8) until 9:46.1; at frame 148
  (9:47.9) it is no longer on screen and the whole portal page is visible. In between, in this order: the pointer rests
  on the Cloud Shell icon in the top bar and its tooltip appears (frames 148-149, tooltip at 9:48.7); a tooltip with the
  PowerShell window's title appears at the lower middle of the screen (frame 151, 9:53.7); the pointer, as a vertical
  double-headed arrow, is over the Workspace resource ID value at the lower right (frame 152, 9:54.5); the pointer is at
  the bottom edge of the picture (frame 153, 9:56.5). The page itself does not change: same tab, same values, nothing
  opens. The window is back at frame 154 (9:58.7, change detected at 9:57.8), in the same place and size, its prompt
  still empty.
- **Rubric:**
  - M1: says the window left the screen between 9:46 and 9:49, or names frame 148.
  - M2: says it came back between 9:57 and 9:59, or names frame 154.
  - M3: mentions the pointer on the Cloud Shell icon, or its tooltip, in between.
  - X1: says something was typed or run in the PowerShell window before 10:20.
- **Evidence:** frames 147-154; t 565.80-598.73.

### Q14 (positive, the single keystroke)
- **Question:** What did the presenter type into PowerShell at about 10:20, and what did the shell show next to it?
- **Reference answer:** One character, `a`. Right after it the shell shows `z login` in dim grey, its inline suggestion,
  so the row looks like `PS C:\Users\msadmin> az login` with only the `a` in normal brightness and the cursor sitting on
  the `z`. Nothing was submitted: there is no output and no second prompt (frame 155, 10:20.7 to 10:23.7).
- **Rubric:**
  - M1: says only the letter `a` had been typed.
  - M2: says the rest, `z login` (making `az login`), was the shell's greyed suggestion and was not typed.
  - X1: says `az login` was typed in full, or that it was run.
- **Evidence:** frame 155, against frame 154 for the empty prompt; t 598.73-620.67. OCR reads the row as the single
  string `PS C:\Users\msadmin> az login` with nothing to tell typed text from suggestion; the image is the truth. The
  only pixels that differ between frames 154 and 155 are x 835-901, y 355-369.

## Negative questions (secondary)

### Q15 (negative, did they)
- **Question:** Did the presenter open Cloud Shell in the portal between 9:20 and 10:24?
- **Reference answer:** No. The pointer rested on the Cloud Shell icon in the portal's top bar (frames 148-149) and its
  tooltip appeared at 9:48.7, but no Cloud Shell pane opened: at frame 150 (9:52.1) the page is unchanged, and it stays
  so to frame 155. The shell on screen in this stretch is the local PowerShell window.
- **Rubric:**
  - M1: says Cloud Shell was not opened (at most hovered over).
  - X1: says Cloud Shell was opened, or that commands were typed into Cloud Shell.
- **Evidence:** frames 148-155; t 587.87-620.67

### Q16 (negative, did a dialog appear)
- **Question:** Did any dialog box, confirmation or error message pop up on the portal between 9:20 and 10:24?
- **Reference answer:** No. The only things that popped up were two small tooltips ("Cloud Shell" at 9:48.7 and
  "Administrator: PowerShell 7-preview (x64)" at 9:53.7) and the browser's status bubble at the bottom left (frames
  148-149). No dialog, no confirmation, no error and no opened notification panel is on any frame; the notification
  bell carries a badge "1" on frames 147-155 but is never opened.
- **Rubric:**
  - M1: says no dialog, confirmation or error message appeared (tooltips may be mentioned).
  - X1: says a dialog box, a confirmation prompt or an error message appeared.
- **Evidence:** frames 145-155; t 562.77-620.67

### Q17 (negative, a value the setting did not have)
- **Question:** Is AKS1-KodeKloudApp shown as a private cluster on the portal page at about 9:50?
- **Reference answer:** No. The Networking section in the right column of the Properties tab reads "Private cluster
  Not enabled". The left column at almost the same height reads "Auto Upgrade Type Patch", and the two "Enabled" values
  on the page belong to Local accounts and to Container insights.
- **Rubric:**
  - M1: says private cluster is not enabled (the cluster is not shown as private).
  - X1: says the cluster is private, or that private cluster is enabled.
- **Evidence:** frames 148-153 (row at y 827; behind the PowerShell window on 147, 154 and 155); t 587.87-596.47

### Q18 (negative, was a command run)
- **Question:** Was anything executed in the PowerShell window between 9:25 and 10:24?
- **Reference answer:** No. The prompt is empty at frame 147 (9:25.8) and again at frame 154 (9:58.7); at frame 155
  (10:20.7) a single `a` has been typed, followed by the greyed suggestion `z login`. On all three frames the window
  holds that one prompt row and nothing else: no output and no second prompt.
- **Rubric:**
  - M1: says no command was executed in that time.
  - X1: says a command (for example `az login`) was executed in that time.
- **Evidence:** frames 147, 154, 155; t 565.80-620.67. Overlaps span 2's Q14, which asks about `az login` by name from
  10:20 on.

## Frame content the agent was unsure about

- **Frame 149, the tooltip's full text.** Only "oud Shell" is visible; the hand pointer hides the first two letters.
  "Cloud Shell" is inferred from the icon it sits under. Q10 M1 accepts the visible part.
- **Frame 151, what the tooltip hangs on.** The brief for this draft calls it a taskbar tooltip. The frame shows neither
  a pointer nor a taskbar (the picture ends at the bottom of the browser page), so Q11 asks only for its text, its place
  and whether the PowerShell window was visible. If the owner knows it is the taskbar button's tooltip, a rubric line
  could say so.
- **How the PowerShell window left and came back** (minimised, or the browser brought in front, and then restored from
  the taskbar) cannot be seen. The reference answers say only "no longer on screen" and "back".
- **Frame 152, the pointer's shape.** Enlarged, it is a vertical double-headed arrow (a resize pointer), not a text
  cursor. Why a resize pointer shows over the page cannot be told from the frame. It is in Q13's reference answer but in
  no rubric line.
- **Whether the Cloud Shell icon was clicked.** Verified only that nothing opened on frames 150-155 (Q15). Frames after
  155 were not examined for this draft.
- **The API server address** reads `aks1-kodekloudapp-dns-wq0okvps.hcp.southeastasia.azmk8s.io` by eye and by OCR, but
  a zero and a letter o cannot be told apart with confidence after `wq`, so no question asks for it.
- **Frame 145.** `frames.jsonl` marks it `settled: false`, the picture has no browser chrome (the later frames do), and
  the same page was probably on screen before 9:19.8; frames before 145 were not examined. Its deployment name,
  `microsoft.aks-20230404212734` (start time 4/4/2023, 9:32:34 PM), is not the deployment named in the cluster page's
  breadcrumb on frames 147-155, `microsoft.aks-20230410195123 | Overview`. Both strings are clearly legible. No
  question asks about the difference because explaining it means guessing about the recording; the owner may want one
  ("is the deployment in the breadcrumb the one that was in progress before the slide?": no).
- **Frame 145's details table** (AKS1-KodeKloudApp "Created", five other rows "OK") is legible and would make a table
  lookup question; it was left out to keep the set near 16 questions.
- **Browser window controls.** On frame 147 the browser's minimise button is drawn with a hover highlight though no
  pointer is visible; on frames 154 and 155 the browser's controls look faded, as for a window without focus. Too faint
  to ask about.
- **Which browser it is** (it looks like Chrome) is not asserted anywhere.
