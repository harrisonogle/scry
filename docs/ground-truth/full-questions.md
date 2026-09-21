# Question set: the whole sample video, frames 0-220 (findability)

Status: **DRAFT written by an agent from the frames, for the owner to correct. Nothing here is accepted yet.** Correct a
question, a reference answer or a rubric line in place, delete what you do not want asked, add what is missing; the
evaluation harness reads whatever this file holds when a phase runs (the file's hash is recorded in every scorecard,
and a reworded question never pairs with answers to its old wording).

Why this set exists (ledger L57 and L59): the two earlier sets cover 33 frames (`span2-questions.md`) and 11 frames
(`smoke-questions.md`). On spans that short every search lands in the right place and the answering agent can afford to
open the frames and look, so neither set can tell whether the index FINDS the right moment, which is the owner's first
priority ("cannot find it" is the worst failure). These questions are about the whole 221-frame, 14-minute sample: each
is answerable only by getting to one moment, or a small set of moments, among 221 frames, and the agent cannot look at
everything. Several ask about a value that is on screen in more than one state or place (the Region field, the node
count range, a command run twice, three similar IP addresses), where a search hit on the wrong moment gives a wrong
answer; several are worded without the words that are on screen.

Source: written by an agent that looked at the frames of `runs/p0/frames/` (1920x1080), whole and then in enlarged
crops of the regions asked about. There is no owner-accepted ground-truth file behind this set: **the reference answers
below are the proposed ground truth**, and every one was checked against the image itself. `runs/p0/boxes.jsonl` and
`runs/p0/lifetimes.jsonl` were used to find where a text first and last appears and for the spelling of long strings;
where OCR and the image differ, the image wins. `runs/outline-live/outline.json` was used only to get oriented. Times
are `t_settled` of `runs/p0/frames.jsonl`, written as minutes and seconds (553.70 s = 9:13.7); where a frame's
`t_change` or `t_end` is used, the text says so. Many frames of the portal part are forced emissions (`settled: false`,
one every three seconds while something on the page keeps moving), so a time taken from them is good to about three
seconds. For the two commands that fall inside frames 155-187 the times are those of the owner-accepted
`span2-commands.md`. No model was called and no pipeline stage was run to write this file. The video has no audio
stream; nothing here depends on what was said or on guessing what the presenter meant to do.

What the video shows, as read from the images:

| Frames | Time | On screen |
|---|---|---|
| 0-5 | 0:00-0:14 | Animated intro with numbered bubbles ("01 Kubernetes Overview", "02 Deploying an AKS Cluster", a third one cut off), then the title card "Kubernetes Overview". |
| 6-10 | 0:14-0:48 | Slide "Kubernetes Components": a box "Control Plane" (kube-controller-manager, etcd, kube-apiserver, kube-scheduler) and a box "Node" (kubelet, Kube-proxy, Container Runtime). |
| 11-19 | 0:48-1:32 | The Control Plane slide built up: kube-apiserver, kubectl, then etcd, kube-controller-manager and kube-scheduler with a caption each; kube-scheduler and its caption only on frame 19. |
| 20-24 | 1:32-2:04 | The Node slide built up: Kubelet, Kube-proxy, Container Runtime with captions. |
| 25-39 | 2:04-3:46 | A diagram of a request's way from kubectl through the control plane to the node, built up arrow by arrow. |
| 40 | 3:46.6-3:49.0 | Title card "Deploying an Azure Kubernetes Service (AKS Cluster)". |
| 41-45 | 3:49-4:21 | Azure portal: home page, "Create a resource", category Containers, "Create" under Azure Kubernetes Service (AKS). |
| 46-81, 84-85 | 4:21-6:28 | "Create Kubernetes cluster", tab Basics: resource group, cluster name, region, zones, version, node size, scale method. |
| 82-83, 86-102 | 6:20-7:21 | Tab Node pools, and the panel "Update node pool" (frames 91-100). |
| 103-105 | 7:21-7:30 | Tab Access. |
| 106-110 | 7:32-7:44 | Tab Networking. |
| 111-129 | 7:45-8:31 | Tab Integrations, with the side panel "Create container registry" on frames 113-124. |
| 130-133 | 8:31-8:46 | Tabs Advanced (130-131) and Tags (132-133, nothing entered). |
| 134-141 | 8:48-9:11 | Tab Review + create: final validation, Create, the notifications "Initializing deployment..." and "Submitting deployment...". |
| 142-145 | 9:13-9:23 | Deployment page `microsoft.aks-20230404212734 \| Overview`: "Deployment is in progress". |
| 146 | 9:22.8-9:25.5 | Title card "Deploying our sample application to AKS Cluster". |
| 147-181 | 9:25-11:47 | Browser on the cluster's overview page with a PowerShell window in front: `az` and `kubectl` commands (the two earlier question sets). |
| 182-184 | 11:49-11:54 | Portal pages of the virtual machine scale set `aks-agentpool-18097611-vmss`: overview, then Instances. |
| 185-203 | 11:56-12:58 | PowerShell in front of the Instances page; on frame 188 a Docker Hub window lies over both. |
| 204-215 | 12:57-13:59 | PowerShell in front of the portal page of the node, "Current workloads" (a list of pods). |
| 216-218 | 13:59-14:07 | A new browser tab, a context menu in its address bar, then the sample application's page. |
| 219-220 | 14:09-14:13 | KodeKloud logo. |

Scope: the whole video, 0:00 to 14:12.8. A question that names no time is about the whole video. Four questions need
a moment inside frames 145-187, which the two earlier sets cover, and each of them also needs a moment outside that
range (Q6, Q17, Q18, Q22). Q9, Q12 and Q14 can be answered from outside that range; their reference answers only
mention frames inside it (183, 182-187 and 145).

Types: (a) exact-string lookups, including values typed into form fields: Q4, Q10, Q11, Q12, Q14, Q15, Q16, Q19;
(b) when: Q3, Q13, and a time line in Q1, Q4, Q8, Q15 and Q16; (c) worded without the on-screen words: Q1, Q7, Q9, Q12;
(d) a value in several states or places, where the right moment matters: Q5, Q6, Q7, Q8, Q10, Q14, Q17, Q18, Q19, Q20;
(e) order across distant parts: Q21, Q22; (f) negative questions: Q23-Q27.

Weighting (as in the other sets): the **positive** questions Q1-Q22 are the question-set score. The **negative**
questions Q23-Q27, whose correct answer is no, are **secondary**: they are reported beside the positive score and break
ties only.

How an answer is scored: each rubric line is a statement about the answer. `M` lines must be true of the answer; `X`
lines must not be. A separate model call, which does not know which run produced the answer, decides each line, and
code derives the label: an answer is *correct* when every `M` line holds and no `X` line does, *wrong* when any `X`
line holds or no `M` line holds, and *partial* otherwise.

Which lines require an exact string: **only a line that says "contains the exact string"** (here Q2 M1 and M2, Q4 M1,
Q6 M1 and M2, Q10 M2, Q11 M1, Q12 M1, Q14 M1, Q15 M1, Q16 M1, Q19 M1 and M2, Q20 M1). There the string must appear in
the answer character for character, including case. Every other line is judged on meaning: "names the component",
"gives the text" or "says …" holds when the answer unmistakably refers to the same thing, whatever its spelling,
spacing or case. "Gives a time between A and B" is also satisfied by naming a frame in the stated range. A stated time
range already contains the tolerance: about five seconds either side of the moment, more where the moment is a
stretch of typing.

Negative questions: each has exactly one `M` line (the answer says no) and one `X` line (the precise wrong claim), so
a plain, correct "No" is *correct*. The explanation in the reference answer is for people and is not scored.

Format (read by `scry.evaluation.questions.parse_questions`; keep it): a heading `### Q<n> (<positive|negative>,
<style>)`, then the bullets **Question**, **Reference answer**, **Rubric** (indented `M<n>:` and `X<n>:` lines) and
**Evidence**, which is for people: the harness does not read it.

## Positive questions

### Q1 (positive, worded without the slide's words)
- **Question:** According to the presentation at the start, which piece of Kubernetes picks the machine that new work
  gets placed on, and when is that on screen?
- **Reference answer:** kube-scheduler. On the "Control Plane" slide its caption reads "Determines the node to run the
  workload". On this slide kube-scheduler and its caption are on screen only on frame 19, from 1:24.2 to 1:31.8; the
  slide is built up piece by piece and the scheduler comes last. The other captions on the same slide are "Maintains
  the state of the Kubernetes Cluster" (etcd, from frame 17) and "Oversees smaller controllers"
  (kube-controller-manager, from frame 18). The name kube-scheduler alone, without the caption, is also on the overview
  slide of frames 8-10 (0:21.7 to 0:48.7) and in the request diagram of frames 25-39.
- **Rubric:**
  - M1: names kube-scheduler (the scheduler).
  - M2: gives a time between 1:19 and 1:37, or frame 19.
  - X1: names a different component (etcd, kube-controller-manager, kube-apiserver, kubelet) as the one that picks the
    node.
- **Evidence:** frame 19; t 84.23-91.77. OCR reads the caption in two boxes, `Determines the node` and `to run the workload`.

### Q2 (positive, labels in a diagram)
- **Question:** In the diagram that traces a request through the cluster, which two small boxes sit between the
  container runtime and the pods, and what does the arrow beside them lead to?
- **Reference answer:** HCL and HNS, two small boxes side by side inside one frame, under Container Runtime and above
  Pods, in the "Node" half of the diagram. An arrow leads from that frame to the right, to a box "Endpoint". The frame is
  drawn empty from frame 26 (2:05.5); HCL is added at frame 36 (3:21.1), HNS and Endpoint at frame 37 (3:26.5), and the
  finished diagram stays until 3:46.6 (frame 39).
- **Rubric:**
  - M1: contains the exact string `HCL`.
  - M2: contains the exact string `HNS`.
  - M3: says the arrow beside them leads to Endpoint.
  - X1: names kubelet, Kube-proxy or kube-scheduler as one of the two boxes between the container runtime and the pods.
- **Evidence:** frames 36-39; t 201.07-226.57. OCR reads `HCL`, `HNS` and `Endpoint` correctly.

### Q3 (positive, when did they)
- **Question:** When do the slides stop and the Azure portal first come on screen, and what does the title card just
  before it say?
- **Reference answer:** The portal's home page ("Azure services", "Resources", "Navigate", "Tools") is first on screen
  at frame 41, 3:49.4 (change detected at 3:49.0). Just before it, from 3:46.6 to 3:49.0 (frame 40), a title card reads
  "Deploying an Azure Kubernetes Service (AKS Cluster)". Before the card the request-flow diagram was on screen
  (frame 39, until 3:46.6).
- **Rubric:**
  - M1: gives a time between 3:44 and 3:54 for the portal's first appearance, or frame 40 or 41.
  - M2: gives the card's text, Deploying an Azure Kubernetes Service (AKS Cluster).
  - X1: gives a time after 4:10 for the portal's first appearance, or gives the text of the other title card
    ("Deploying our sample application to AKS Cluster", 9:24) as the one before the portal.
- **Evidence:** frames 39-41; t 219.03-229.37

### Q4 (positive, a value typed into a form field)
- **Question:** What did the presenter call the resource group for the cluster, was it an existing one, and at about
  what time was the name entered?
- **Reference answer:** `RG1-KodeKloud-AKS`, a new one. The presenter clicks "Create new" under the Resource group
  field (frame 47, 4:23.1), a small popup with a "Name" field opens (frame 48, 4:27.8), the name is typed from 4:30.5
  (frame 49, `RG1-`) to 4:37.8 (frame 53, `RG1-KodeKloud-AKS`, pointer on OK), and from frame 54 (4:38.9) the Resource
  group field reads "(New) RG1-KodeKloud-AKS". Until then it read "(New) Resource group".
- **Rubric:**
  - M1: contains the exact string `RG1-KodeKloud-AKS`.
  - M2: says it was a new resource group, created in the form.
  - M3: gives a time between 4:25 and 4:43, or a frame from 48 to 54.
  - X1: says an existing resource group was picked, or gives `MC_RG1-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia` as
    the resource group the presenter entered.
- **Evidence:** frames 47-54; t 263.10-278.93. OCR reads the partial names as `RG1-`, `RG1-Kode`, `RG1-KodeKloud`,
  `RG1-KodeKloud-`, `RG1-KodeKloud-AKS`.

### Q5 (positive, a value before and after it was changed)
- **Question:** Which Azure region was the cluster created in? The Region field held other values before that: which?
- **Reference answer:** Southeast Asia. When the form loads the field reads "(US) West US" (frames 47-60, from 4:23.1).
  The presenter opens the list, types "south" into its filter (frame 61, 4:52.6) and picks "(Asia Pacific) Southeast
  Asia" (frame 62, 4:55.6). Later the list is opened again (frame 66, 5:22.8), "australia" is typed (frame 67, 5:25.4)
  and at frame 68 (5:29.3) the field reads "(Asia Pacific) Australia Southeast", with the note "No availability zones
  are available for the location you have selected." under a greyed-out Availability zones field; the list is open once
  more at frame 69 (5:29.7), and by frame 70 (5:33.3) the field is back to "(Asia Pacific) Southeast Asia", where it
  stays. The Review + create tab says "Region Southeast Asia" (frames 134-141) and the deployed cluster's page says
  "Location : Southeast Asia" (from 9:25.8).
- **Rubric:**
  - M1: says the cluster was created in Southeast Asia.
  - M2: says the field first read West US.
  - M3: says the field read Australia Southeast for a moment before going back to Southeast Asia.
  - X1: gives West US or Australia Southeast (or any region other than Southeast Asia) as the region the cluster was
    created in.
- **Evidence:** frames 47, 60-62, 66-71, 134-141; t 263.10-333.73 and 528.93-550.70. "Australia Southeast" is also an
  entry of the open region list on frames 60, 61, 67 and 69, and "Southeast Asia" an entry on frames 61 and 66: only
  the field below the list tells what is selected. Frames 68 and 70 are forced emissions (`settled: false`).

### Q6 (positive, the form against the running cluster)
- **Question:** Which Kubernetes version was selected in the creation form, and does the running cluster report the
  same version later in the video?
- **Reference answer:** The form has "1.24.9 (default)". The presenter opens the version list at 5:37.8 (frames 73-74,
  until 5:57.6; it offers 1.26.0 (preview), 1.25.5, 1.25.4, 1.24.9 (default), 1.24.6, 1.23.15 and more) and leaves the
  default; the Review + create tab says "Kubernetes version 1.24.9" (frames 134-141). The running cluster reports a
  different version: its overview page says 1.24.10 (Essentials and the Properties tab, from frame 147, 9:25.8), and
  `kubectl get nodes` prints VERSION v1.24.10 (frame 180, 11:42.0, and in the scrollback until frame 215).
- **Rubric:**
  - M1: contains the exact string `1.24.9`, given as the version in the form.
  - M2: contains the exact string `1.24.10`, given as the version the running cluster reports.
  - X1: says the form and the running cluster show the same version.
- **Evidence:** frames 73-74 and 134-141 for the form; 147-181 and 180-215 for the cluster; t 337.77-357.63,
  528.93-550.70, 565.80-706.70. OCR reads both strings correctly.

### Q7 (positive, worded without the on-screen words and first against final state)
- **Question:** How many machines can the cluster's pool grow to under the settings the presenter ended up with, and
  what was that limit at first?
- **Reference answer:** One: the node count range ends as 1 to 1, with scale method Autoscale. At first the maximum was
  5 (the form's default, "Node count range" 1 and 5 on the Basics tab, frame 78, 6:04.3). In between, as the frames
  show it: the Basics tab shows 1 and 1 from frame 79 (6:16.7) with the pointer on the slider; the Node pools tab lists
  agentpool with "Node count 1-1" on frames 82-83 (6:20.3) but "1-5" on frames 86-90 (6:30.9 to 6:56.7); the presenter
  opens the panel "Update node pool" (frame 91, 6:59.8), where the range reads 1 and 5, selects the 5 (frame 99,
  7:11.5) and replaces it by 1 (frame 100, 7:16.0); back on the Node pools tab the table reads "1-1" (frames 101-102,
  7:16.6 to 7:21.1), which is the last time the range is shown. Later the cluster has one node (`kubectl get nodes`,
  11:42.0) and the scale set one instance (11:49.8).
- **Rubric:**
  - M1: says the final maximum is 1 (a range of 1 to 1, a single node).
  - M2: says the maximum was 5 at first (a range of 1 to 5).
  - X1: gives 5, or 1 to 5, as the setting the presenter ended up with.
- **Evidence:** frames 78-79, 82-83, 86-90, 91-102; t 364.30-441.13. OCR reads the table cells as `1-1` and `1-5` and
  the two fields of the range as separate boxes `1` and `5`. Frames 79 and 100 are forced emissions.

### Q8 (positive, a value before and after with an error in between)
- **Question:** The presenter lowers the limit on how many pods one machine may run. From what to what, and did the
  portal complain while the new number was being typed?
- **Reference answer:** From 110 to 30, in the field "Max pods per node" of the panel "Update node pool". The Node
  pools tab shows "Max pods / node 110" (frames 87-89, the 110 selected on frame 89, 6:42.3); in the panel the 110 is
  selected (frames 91-93, until 7:03.2) and overwritten. With only "3" typed (frames 94-95) the portal shows two errors
  in red under the field, on frame 95 only (7:03.8 to 7:04.3): "The minimum required number of pods for a system node
  pool is 30. With 1 node as the minimum scale value, the minimum pods per node is 30." and "The value must be between
  30 and 250." They are gone when the field reads 30 (frame 96, 7:05.9, until the panel closes after 7:16.0).
- **Rubric:**
  - M1: says the limit was changed to 30.
  - M2: says it was 110 before.
  - M3: says an error appeared while typing (the minimum is 30, or the value must be between 30 and 250), or gives a
    time between 6:59 and 7:09 or frame 95 for it.
  - X1: gives 110 or 250 as the final value, or says no error or warning appeared.
- **Evidence:** frames 89-96; t 402.30-426.33. OCR has no box for the lone `3` on frames 94-95; it reads both error
  lines on frame 95.

### Q9 (positive, worded without the on-screen words with the value in two places)
- **Question:** How many CPUs and how much memory does each of the cluster's machines have, and where in the video can
  that be seen?
- **Reference answer:** 2 vCPUs and 7 GiB of memory: the node size is Standard DS2 v2. It can be seen in two places far
  apart: in the panel "Update node pool" of the creation form, under Node size, "Standard DS2 v2" with "2 vcpus, 7 GiB
  memory" below it (frames 91-100, 6:59.8 to 7:16.0); and on the portal page of the virtual machine scale set
  `aks-agentpool-18097611-vmss`, Properties tab, section Size: "Size Standard_DS2_v2", "vCPUs 2", "RAM 7 GiB" (frame
  183, 11:49.8). The Basics tab (frames 75-85) and the Node pools table name the size without the figures.
- **Rubric:**
  - M1: says 2 vCPUs and 7 GiB of memory.
  - M2: names the size Standard DS2 v2 (Standard_DS2_v2).
  - X1: gives a different number of CPUs or a different amount of memory.
- **Evidence:** frames 91-100 and 183; t 419.77-436.00 and 709.77. Both readings are clearly legible.

### Q10 (positive, a changed choice and an exact string)
- **Question:** Which network plugin did the presenter pick for the cluster, what was selected before, and what address
  range does the new cluster subnet get?
- **Reference answer:** Azure CNI. The Networking tab opens with "Kubenet" selected (frames 106-107, 7:32.4); from frame
  108 (7:37.2) "Azure CNI" is selected, a note about IP addresses per pod appears, and new fields show: Virtual network
  "(New) RG1-KodeKloud-AKS-vnet" and Cluster subnet "(new) default (10.224.0.0/16)". The subnet's range is
  10.224.0.0/16. The fields below it hold other ranges: Kubernetes service address range 10.0.0.0/16, Kubernetes DNS
  service IP address 10.0.0.10, Docker Bridge address 172.17.0.1/16. The Review + create tab confirms "Network
  configuration Azure CNI" but shows the subnet only as "(new) default".
- **Rubric:**
  - M1: says Azure CNI was picked, and that Kubenet was selected before.
  - M2: contains the exact string `10.224.0.0/16`, given as the cluster subnet's range.
  - X1: says Kubenet was the final choice, or gives `10.0.0.0/16` or `172.17.0.1/16` as the cluster subnet's range.
- **Evidence:** frames 106-110; t 452.43-463.97. OCR reads the subnet field as `(new) default (10.224.0.0/16)`.

### Q11 (positive, values typed and chosen in a side panel)
- **Question:** What name did the presenter give the container registry that is created with the cluster, and which
  pricing tier (SKU) did it end up with?
- **Reference answer:** `crkodekloud` (shown with the suffix .azurecr.io), SKU Basic. On the Integrations tab the
  presenter opens the side panel "Create container registry" (frame 113, 7:51.7, change detected at 7:48.7), types the
  name from 8:03.4 (frame 115, `cr`) to 8:08.1 (frame 118, `crkodekloud`); on frames 116-117, with `cr` and then
  `crkode` in the field, an error under it says that resource names may contain alphanumeric characters only and must
  be between 5 and 50 characters. The SKU reads
  "Standard" until the list is opened (frame 123, 8:17.2: Basic, Standard, Premium) and "Basic" from frame 124
  (8:17.3). Admin user stays on "Disable", resource group "(New) RG1-KodeKloud-AKS", region Southeast Asia. After the
  panel closes the tab's Container registry field reads "(New) crkodekloud" (frames 125-129, from 8:19.5); before, it
  read "None".
- **Rubric:**
  - M1: contains the exact string `crkodekloud`.
  - M2: says the SKU ended as Basic.
  - X1: gives Standard or Premium as the SKU the registry ended up with.
- **Evidence:** frames 113-125; t 471.70-499.50. OCR reads `crkodekloud` correctly from frame 118; on frame 123 it
  reads the list as `Basic`, `Stand`, `Premium` (the pointer covers part of "Standard").

### Q12 (positive, an exact string that appears in several places)
- **Question:** AKS keeps the cluster's virtual machines in a second resource group that it names itself. What is that
  group called in this video, and where is the name shown?
- **Reference answer:** `MC_RG1-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia`. It is first shown in the creation form,
  tab Advanced, field "Infrastructure resource group" (frames 130-131, 8:31.8 to 8:40.8). It shows again on the pages of
  the virtual machine scale set: as the resource group in Essentials (frame 183, 11:49.8), in the breadcrumb "Home >
  Resource groups > MC_RG1-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia" and in the browser's address (frames 182-203,
  11:49.7 to 12:57.9). The resource group the presenter created, RG1-KodeKloud-AKS, is a different one.
- **Rubric:**
  - M1: contains the exact string `MC_RG1-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia`.
  - M2: names at least one place where it is shown: the Advanced tab's Infrastructure resource group field, or the
    scale set's page (its resource group, breadcrumb or address).
  - X1: gives `RG1-KodeKloud-AKS` alone as the group that holds the virtual machines.
- **Evidence:** frames 130-131 and 182-203; t 511.80-520.80 and 709.70-777.93. OCR reads the string correctly on frame
  130.

### Q13 (positive, when did they)
- **Question:** At what time did the form's final validation pass, and when did the page saying the deployment is in
  progress come up?
- **Reference answer:** The Review + create tab shows "Running final validation..." from frame 134 (8:48.9) and
  "Validation passed" from frame 137 (8:56.6, change detected at 8:55.4), with the Create button active. By frame 138
  (9:01.7) Create is greyed out with the hand pointer on it; a notification "Initializing deployment..." shows at frame
  139 (9:04.7) and "Submitting deployment..." at frame 141 (9:10.7). The page `microsoft.aks-20230404212734 | Overview`
  with "Deployment is in progress" is on screen from frame 142 (9:13.7, change detected at 9:10.7) to frame 145
  (9:22.8).
- **Rubric:**
  - M1: gives a time between 8:50 and 9:02 for the validation passing, or frame 137.
  - M2: gives a time between 9:05 and 9:19 for the deployment page coming up, or frame 142.
  - X1: says the validation failed, or places the "Deployment is in progress" page before 9:00.
- **Evidence:** frames 134-142; t 528.93-553.70. Frames 138-145 are forced emissions, three seconds apart.

### Q14 (positive, exact-string lookup with a near miss elsewhere)
- **Question:** What is the name of the deployment on the portal page that says the deployment is in progress, and what
  start time does that page give?
- **Reference answer:** Deployment name `microsoft.aks-20230404212734`, start time 4/4/2023, 9:32:34 PM (subscription
  sub-global, resource group RG1-KodeKloud-AKS), on frames 142-145 (9:13.7 to 9:22.8). A similar but different name,
  `microsoft.aks-20230410195123`, is in the breadcrumb of the cluster's page later (frames 147-181, from 9:25.8); that
  is not the page asked about.
- **Rubric:**
  - M1: contains the exact string `microsoft.aks-20230404212734`.
  - M2: gives the start time 4/4/2023, 9:32:34 PM (any clear spelling of that date and time).
  - X1: gives `microsoft.aks-20230410195123` as the name on the in-progress page.
- **Evidence:** frames 142-145; t 553.70-562.77. OCR reads the name correctly in the page title and in the "Deployment
  name:" row.

### Q15 (positive, a page that is on screen for three seconds)
- **Question:** Before deploying, the presenter shows where the application's container image lives. Which site is it,
  what is the repository called, how many tags does it have, and when is this shown?
- **Reference answer:** Docker Hub. A browser window on `hub.docker.com/repository/docker/hpranav/kodekloudappcs/general`
  lies over the portal and the PowerShell window on frame 188 only, from 12:11.7 to 12:14.7 (change detected at
  12:10.8). The repository is hpranav/kodekloudappcs (highlighted in yellow), with "This repository does not have a
  description", "Last pushed: 7 hours ago" and "This repository contains 2 tag(s)"; the first row of the tag table is
  v2, the second row is cut off by the bottom of the picture.
- **Rubric:**
  - M1: contains the exact string `hpranav/kodekloudappcs`.
  - M2: says the site is Docker Hub.
  - M3: says the repository has 2 tags.
  - M4: gives a time between 12:06 and 12:20, or frame 188.
  - X1: says the image was shown in, or comes from, the Azure container registry (crkodekloud, azurecr.io).
- **Evidence:** frame 188; t 731.70-734.70. OCR reads the address and `hpranav / kodekloudappcs` correctly.

### Q16 (positive, exact command and when)
- **Question:** What exact command created the Kubernetes deployment for the sample application, when was it run, and
  what did it print?
- **Reference answer:** `kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1 --replicas=1`. At
  frame 190 (12:20.0) the presenter has typed `kubectl create deployment` and the shell suggests the rest in grey; from
  frame 191 (12:25.7) the line reads up to `:v1`; `--replicas=1` is typed on frames 195-197 (12:37.1 to 12:38.9); it is
  submitted by frame 198 (12:39.5), which shows the output `deployment.apps/kodekloudapp created` and a new prompt.
- **Rubric:**
  - M1: contains the exact string `kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1 --replicas=1`.
  - M2: gives a time between 12:34 and 12:45 for the run, or frame 197 or 198.
  - M3: says it printed that the deployment (deployment.apps/kodekloudapp) was created.
  - X1: gives a different image or tag (for example `:v2`), or says the deployment was created from a YAML file.
- **Evidence:** frames 190-198; t 740.00-759.47. OCR reads `kubectl` as `kubect1` on frames 190 and 197; the image shows
  `kubectl`.

### Q17 (positive, the same command at two moments)
- **Question:** `kubectl get deployment` was run more than once in the video. What did it print each time, and roughly
  when was each run?
- **Reference answer:** Twice. The first time, submitted by frame 186 (11:56.9), it printed "No resources found in
  default namespace." The second time, after the deployment had been created: `kubectl get deplo` with the grey
  suggestion `yment` at frame 200 (12:46.9), output at frame 201 (12:48.0): kodekloudapp, READY 1/1, UP-TO-DATE 1,
  AVAILABLE 1, AGE 20s.
- **Rubric:**
  - M1: says the first run found no resources in the default namespace (around 11:57).
  - M2: says the second run listed kodekloudapp as ready, 1/1 (around 12:48).
  - X1: says it was run only once, or that the first run already listed the deployment.
- **Evidence:** frames 185-186 and 200-201; t 716.53-716.90 and 766.93-768.00. The first run is executed row 8 of
  `span2-commands.md`. At frame 199 (12:44.5) the shell also suggested the whole `kubectl create deployment …` line
  again after `kubect`; it was not run a second time.

### Q18 (positive, how many times)
- **Question:** How many times was `kubectl get pods` actually run in the whole video, and what did each run show?
- **Reference answer:** Twice. First between frame 186 (11:56.9) and frame 187 (12:01.0): "No resources found in
  default namespace." Second between frame 202 (12:49.8) and frame 203 (12:53.5), after the deployment existed: one
  pod, kodekloudapp-67ffc758c5-mm42w, READY 1/1, STATUS Running, RESTARTS 0, AGE 34s. Both are first seen already in
  the scrollback with their output. The same words appear at other moments only as the shell's grey suggestion and were
  not run: at frame 189 (12:15.7) after `kubectl ` had been typed (the line becomes `kubectl create deployment` at frame
  190), and on frames 205-207 (12:59.1 to 13:06.8) after `ku`, `kubect` and `kubectl ` (the line becomes `kubectl
  expose` at frame 208). The scrollback of frame 213 shows no third run.
- **Rubric:**
  - M1: says it was run twice.
  - M2: says the first run found nothing and the second listed one running pod (kodekloudapp-67ffc758c5-mm42w).
  - X1: says it was run three or more times, or only once.
- **Evidence:** frames 186-187, 189-190, 202-203, 205-208, 213; t 716.90-721.00, 735.70-740.00, 769.80-773.53,
  779.10-787.77. The first run is executed row 9 of `span2-commands.md`. OCR cannot tell the grey suggestion from typed
  text (`kuhectl get pods`, `kubect get pods`, `kubectlget pods` on frames 205-207).

### Q19 (positive, exact-string lookup among similar values)
- **Question:** After the application was exposed, which external IP address did the service get, what is its cluster
  IP, and which command showed them?
- **Reference answer:** `kubectl get service` (typed as `kubectl get s` with the grey suggestion `vc` at frame 212,
  13:54.1; the executed line at frame 213 reads `kubectl get service`). Output at frame 213 (13:55.6): kodekloudapp,
  TYPE LoadBalancer, CLUSTER-IP 10.0.199.121, EXTERNAL-IP 20.247.251.108, PORT(S) 80:30895/TCP, AGE 15s; and a second
  row kubernetes, ClusterIP, 10.0.0.1, `<none>`, 443/TCP, 51m. At frame 214 (13:56.6) the external IP is selected in
  the terminal. Before that, `kubectl expose deployment kodekloudapp --type=LoadBalancer --port=80 --target-port=80`
  had printed "service/kodekloudapp exposed" (frame 210, 13:49.4).
- **Rubric:**
  - M1: contains the exact string `20.247.251.108`, given as the external IP.
  - M2: contains the exact string `10.0.199.121`, given as the cluster IP.
  - M3: names `kubectl get service` (or its short form `kubectl get svc`) as the command.
  - X1: gives `10.0.0.1`, `10.224.0.31` or `<none>` as the application's external IP.
- **Evidence:** frames 212-215; t 834.07-838.83. OCR reads all the values correctly.

### Q20 (positive, similar values in different places)
- **Question:** When the application is opened in the browser at the end, which IP address does the page itself
  report, and is that the address in the browser's address bar?
- **Reference answer:** No, they differ. The page (tab title "Home page - KodeKloudApp", heading "Welcome", on frame
  218, 14:02.2 to 14:06.8) reports "IP address: ::ffff:10.224.0.31", together with "Message: Hello World from
  AppSettings.json" and "System name: kodekloudapp-67ffc758c5-mm42w". 10.224.0.31 is the pod's IP: the same value is in
  the Pod IP column of the row kodekloudapp-67ffc758c5-mm42w on the portal's "Current workloads" page (frames 204-215).
  The address bar reads 20.247.251.108, marked "Not secure", which is the service's external IP. Just before, a new tab
  is open (frame 216, 13:59.8) and a context menu in its address bar offers "Paste and go to 20.247.251.108" (frame 217,
  14:00.4).
- **Rubric:**
  - M1: contains the exact string `10.224.0.31`, given as the address the page reports.
  - M2: says the address bar held 20.247.251.108, a different address.
  - X1: says the page reports 20.247.251.108 as its own IP address, or that the two addresses are the same.
- **Evidence:** frames 216-218 and 204-215; t 839.77-846.77 and 777.93-838.83. OCR reads the page's line as
  `IP address:ff:10.224.0.31` (the image shows `::ffff:`), and the address bar as `Not secure20.247.251.108`.

### Q21 (positive, order across the video)
- **Question:** Put these five moments in the order in which they happen in the video: (a) a Docker Hub page is shown;
  (b) the network plugin is switched to Azure CNI; (c) a slide explains kubelet, kube-proxy and the container runtime;
  (d) the deployment is exposed through a load balancer; (e) the container registry is given its name.
- **Reference answer:** c, b, e, a, d. The slide about the node's components is on screen from 1:32 to 2:04 (frames
  20-24); Azure CNI is selected at 7:37.2 (frame 108); the registry name is typed from 8:03.4 to 8:08.1 (frames
  115-118); the Docker Hub page shows at 12:11.7 (frame 188); `kubectl expose deployment …` is typed by 13:09.1 (frame
  209) and its output "service/kodekloudapp exposed" shows at 13:49.4 (frame 210).
- **Rubric:**
  - M1: gives the order c, b, e, a, d (the slide, Azure CNI, the registry name, Docker Hub, the expose).
  - X1: places the Docker Hub page before the container registry is named, or the expose before the Docker Hub page.
- **Evidence:** frames 20-24, 108, 115-118, 188, 208-210; t 92.00-124.00, 457.20, 483.37-488.10, 731.70, 787.77-829.37

### Q22 (positive, order across the video)
- **Question:** Between submitting the cluster's deployment in the portal and running `kubectl create deployment`,
  three things happen: the Docker Hub repository is shown, the cluster's credentials are fetched with the Azure CLI, and
  the portal pages of the virtual machine scale set are opened. In which order, and roughly when?
- **Reference answer:** First the credentials: `az aks get-Credentials --name AKS1-KodeKloudApp`, typed from 10:56.2
  and submitted by 10:59.3, the context merged at 11:04.1 (frames 166-171). Then the scale set
  `aks-agentpool-18097611-vmss` in the portal: its overview at 11:49.7 (frames 182-183) and its Instances page at
  11:53.5 (frame 184). Then the Docker Hub repository at 12:11.7 (frame 188). The cluster's deployment was submitted at
  about 9:10 (frames 141-142) and `kubectl create deployment …` ran at 12:39.5 (frame 198).
- **Rubric:**
  - M1: gives the order credentials, then the scale set's pages, then Docker Hub.
  - M2: gives a time for at least two of the three that is within about ten seconds of 10:57-11:04 (credentials),
    11:50-11:54 (scale set) or 12:12 (Docker Hub).
  - X1: places the Docker Hub page before the credentials are fetched, or the scale set's pages after `kubectl create
    deployment`.
- **Evidence:** frames 166-171, 182-184, 188; t 656.20-664.13, 709.70-713.53, 731.70. The credentials are executed rows
  3 to 5 of `span2-commands.md`.

## Negative questions (secondary)

### Q23 (negative, did they)
- **Question:** Did the presenter set the cluster up to sign users in with Azure AD?
- **Reference answer:** No. On the Access tab the list under "Authentication and Authorization" is opened once (frame
  105, 7:25.5 to 7:30.3) and shows three options, "Local accounts with Kubernetes RBAC", "Azure AD authentication with
  Kubernetes RBAC" and "Azure AD authentication with Azure RBAC", with the first one highlighted; the field keeps
  reading "Local accounts with Kubernetes RBAC" (frames 103-105). The Review + create tab says "Authentication and
  Authorization Local accounts with Kubernetes RBAC" (frames 134-141), and so does the deployed cluster's Properties tab
  (from 9:25.8).
- **Rubric:**
  - M1: says no: local accounts with Kubernetes RBAC was kept.
  - X1: says Azure AD authentication was chosen for the cluster.
- **Evidence:** frames 103-105, 134-141, 147-181; t 441.87-450.30, 528.93-550.70. The words "Azure AD authentication"
  are on screen on frame 105 only.

### Q24 (negative, did they)
- **Question:** Did they deploy the application from a YAML manifest, for example with `kubectl apply -f`?
- **Reference answer:** No. The deployment was made with `kubectl create deployment kodekloudapp
  --image=hpranav/kodekloudappcs:v1 --replicas=1` (12:39.5) and exposed with `kubectl expose deployment kodekloudapp
  --type=LoadBalancer --port=80 --target-port=80` (output at 13:49.4). No manifest, no editor and no `kubectl apply` is
  on any frame. The word "YAML" is on screen only as an entry of the left menu of the node's portal page (frames
  204-215), which is never opened; "Current workloads" stays the highlighted entry.
- **Rubric:**
  - M1: says no manifest and no `kubectl apply` was used (the deployment was created and exposed with direct commands).
  - X1: says a YAML manifest was applied, or that `kubectl apply` was run.
- **Evidence:** frames 190-198, 208-210, 204-215; t 740.00-759.47, 787.77-829.37

### Q25 (negative, was a page shown)
- **Question:** Does the video ever show the portal page saying that the cluster's deployment is complete?
- **Reference answer:** No. The deployment page is on screen on frames 142-145 (9:13.7 to 9:22.8) and says "Deployment
  is in progress" on all four; on the last one the details table lists AKS1-KodeKloudApp with status "Created" and five
  other deployments with "OK". Then comes a title card (frame 146), and the next portal page is already the cluster's
  own overview page with "Status : Succeeded (Running)" (frame 147, 9:25.8). No page or notification saying the
  deployment is complete or succeeded is on any frame.
- **Rubric:**
  - M1: says no such page is shown (the deployment page is last seen in progress).
  - X1: says the video shows a page or message saying the deployment is complete.
- **Evidence:** frames 142-147; t 553.70-565.80. No text containing "complete" is in `lifetimes.jsonl`.

### Q26 (negative, did they)
- **Question:** At the end, does the presenter delete the cluster or the resource group to clean up?
- **Reference answer:** No. The last things shown are the external IP being selected in the terminal (frame 214,
  13:56.6), a new browser tab (frames 216-217) and the application's page at 20.247.251.108 (frame 218, 14:02.2 to
  14:06.8); the video then ends on the KodeKloud logo (frames 219-220, until 14:12.8). No delete command is in the
  terminal on any frame, and no deletion page or confirmation is on any frame of the portal; "Delete" appears only as
  a toolbar button on portal pages.
- **Rubric:**
  - M1: says no clean-up or deletion is shown.
  - X1: says the cluster, the resource group, the deployment or the service was deleted.
- **Evidence:** frames 213-220; t 835.60-852.83

### Q27 (negative, where did a value come from)
- **Question:** Was the application's image pulled from the Azure container registry that was created along with the
  cluster?
- **Reference answer:** No. The registry `crkodekloud` is only defined in the creation form (frames 113-129, 7:51.7 to
  8:30.9) and is not seen again. The deployment uses `--image=hpranav/kodekloudappcs:v1` (frames 190-198), which is the
  Docker Hub repository shown at 12:11.7 (frame 188). No image reference with `azurecr.io` and no `az acr` command is on
  any frame.
- **Rubric:**
  - M1: says no: the image came from the Docker Hub repository hpranav/kodekloudappcs.
  - X1: says the image was pulled from, or pushed to, the crkodekloud registry (azurecr.io).
- **Evidence:** frames 113-129, 188, 190-198; t 471.70-510.90, 731.70, 740.00-759.47. `azurecr` and `crkode` have no
  lifetime after frame 129.

## Frame content the agent was unsure about

- **The count.** 27 questions rather than about 25 (22 positive, 5 negative), so that the owner can delete rather than
  add. Candidates that were verified and left out: how the presenter got from the portal's home page to the form
  ("Create a resource" at 4:01.4, category Containers at 4:04.4, "Create" under Azure Kubernetes Service (AKS) at
  4:19.5); the recommended alert rules on the Integrations tab ("CPU Usage Percentage is greater than 80%", "Memory
  Working Set Percentage is greater than 80%", frames 111-112 and 125-129); Azure Policy left "Disabled" (frames
  126-129); the scale set's single instance `aks-agentpool-18097611-vmss_0`, Running (frame 184); the pod's name in
  three places (the terminal at 12:53.5, the portal's pod list from 12:57.9, the application's page at 14:02.2); the
  context menu entry "Paste and go to 20.247.251.108" on the single frame 217.
- **Questions that knowledge alone can answer.** Q1 (the scheduler picks the node) and part of Q9 can be answered
  without finding anything. Q1 therefore has a time line (M2); Q9 has none, because its two places are minutes apart and
  either is a fair answer. The owner may want a place or time line on Q9 too.
- **The node count range (Q7).** The Node pools tab shows "1-1" on frames 82-83 and "1-5" again on frames 86-90, after
  the Basics tab had shown 1 and 1. Why the value went back cannot be seen. The reference answer reports the frames in
  order and the rubric asks only for the first and the final state. Whether "1-1" survived to the deployment is not
  shown either: the Review + create tab gives only "Node pools 1" (the number of pools); that the cluster later has one
  node fits both ranges.
- **Availability zones.** The list is opened with nothing ticked at frame 63 (4:59.3), reads "None" from frame 64, is
  greyed out while the region is Australia Southeast (frame 68), and on the forced frame 70 (5:33.3) the field reads
  "Zone 3" with Zone 3 ticked and the hand pointer on it; from frame 71 (5:33.7) it reads "None" again and stays so
  (Node pools table, frames 87-89; Update node pool panel, frame 91). Whether Zone 3 was ticked and unticked by the
  presenter or set by the portal cannot be seen, so no question asks about it. It would make a fifth "value at the
  right moment" negative ("did the cluster end up in an availability zone?": no) if the owner reads the frames the same
  way.
- **The intro's third bubble** ("03 Deploying an Application to AKS Cluster", presumably) is never whole and sharp on
  any frame (cut off on frames 2-3, blurred on frame 1), so the agenda is not asked about. Frames 1-4 are forced
  emissions of an animation.
- **Two recordings.** The form says Kubernetes 1.24.9 and the deployment is `microsoft.aks-20230404212734` (4/4/2023);
  the cluster page after the title card says 1.24.10, its breadcrumb names `microsoft.aks-20230410195123`, and the node
  is 44 minutes old. Q6 and Q14 ask only what is on screen and say nothing about why.
- **Times in the portal part.** Frames 138-145 (and 53, 68, 70, 79, 100, 113, 123, 182, 184) are forced emissions every
  three seconds, so "Create was pressed" is known only as between 8:58.7 and 9:01.7, and the deployment page's first
  appearance as between 9:10.7 and 9:13.7. The ranges of Q13 allow for that.
- **When `kubectl expose` was submitted.** The full line is on screen unchanged from 13:09.1 to 13:49.2 (frame 209) and
  the output shows at 13:49.4. Whether Enter was pressed at 13:49 or earlier, with the command taking its time, cannot
  be seen; no question asks for that time, and Q21 needs only the order.
- **How the registry panel was opened.** On frame 112 the pointer is on "Next : Advanced >" and the next frame already
  shows the panel "Create container registry"; the click on "Create new" is not on any frame. Not asked.
- **Typing not observed.** The second `kubectl get pods` (Q18) and `kubectl get service` (Q19) are first seen already
  executed, apart from `kubectl get s` on frame 212; whether `--image=…:v1` of Q16 was typed or accepted from the grey
  suggestion cannot be told (frame 190 shows it grey, frame 191 in normal brightness).
- **Frame 217's context menu.** That "Paste and go to 20.247.251.108" was the entry clicked is inferred from the next
  frame; it is in Q20's reference answer and in no rubric line.
- **Docker Hub's second tag** is cut off by the bottom edge of frame 188. It is presumably v1, the tag the command
  uses, but that is not on screen, so Q15 asks only for the count the page states.
- **Q19 M3** accepts `kubectl get svc`, the form the shell suggested, because a line judged on meaning cannot tell the
  two apart; the executed line on frame 213 reads `kubectl get service`.
- **Exact strings of three letters.** Q2's `HCL` and `HNS` must match in case; an answer that spells them in lower case
  fails those lines. The owner may prefer lines judged on meaning there.
- **Slides not looked at one by one.** Frames 11-17 and 31-35 were checked through OCR text only, frames 18 and 25-30
  on reduced contact sheets. No question depends on them beyond "kube-scheduler and its caption are only on frame 19"
  (Q1: frame 18 seen without them; `lifetimes.jsonl` has one sighting of "Determines the node") and "the frame under
  Container Runtime is drawn empty from frame 26" (Q2, seen on the contact sheet; in no rubric line).
- **The presenter's e-mail address and subscription ID** are clearly legible (alert rules, `az account show`, the
  portal's top bar) and deliberately not asked about.
