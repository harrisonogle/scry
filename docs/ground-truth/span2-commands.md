# Ground truth: commands in frames 155-187 of the sample video (span 2)

Status: the executed list was reviewed and accepted by the owner on 2026-09-21. The second section is kept at the
owner's request as an answer key for scoring only: no pipeline code treats that text differently from any other text.

Source: RapidOCR first pass, Google Cloud Vision and the language model's readings of each frame, cross-checked by eye on the frames. Times are `t_settled` of the frame in `stage1.jsonl` (seconds; mm:ss in brackets).
"First fully visible" = first frame in which the whole command text is on screen (entered by the presenter, or partly entered with the
shell's suggestion showing the rest, as noted). "Submitted" = first frame in which output or a new prompt appears below it, so the Enter
key fell between the previous frame and that one. Capitalisation is as displayed. The terminal is not visible in frames 182-184
(portal pages); nothing was run there (the prompt row of 181 is unchanged in 185).

## Executed, in order

| # | Text as displayed | First fully visible (frame, t) | Submitted (frame, t) | Confidence note |
|---|---|---|---|---|
| 1 | `az account show` | 157, 628.77 (10:28.8), fully typed, no suggestion | 158, 629.57 (10:29.6), JSON output and new prompt | High. All readers agree on the command (RapidOCR's detector cut the leading `PS` of this row in scrollback; command text unaffected). |
| 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 161, 649.17 (10:49.2) as typed `az c` + the shell's suggestion; fully typed from 162, 652.00 (10:52.0) | 164, 653.57 (10:53.6), new prompt below, no output | High. RapidOCR (settled rows) and the model agree; Vision reads `=` as `-` and `KodeKloud` as `Kodekloud` on most sightings, by eye it is `=` and `KodeKloud`. |
| 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 166, 656.20 (10:56.2) as typed `az aks get` + suggestion; fully typed from 167, 657.07 (10:57.1) | 169, 659.27 (10:59.3), "A different object named AKS1-KodeKloudApp already exists..." | High. Capital `C` in `get-Credentials` is on screen (RapidOCR and Vision on all 16 scrollback sightings; the model lower-cased it in 2 of 16 scrollback sightings). |
| 4 | `Y` (answer to the first `Overwrite? (y/n):`, object AKS1-KodeKloudApp) | question visible 169, 659.27; answer visible 170, 660.83 (11:00.8) | 170, 660.83 (11:00.8), second message and second question already below it | High for "answered yes"; capital `Y` as displayed (RapidOCR, Vision, by eye). Typed and submitted between 169 and 170. |
| 5 | `y` (answer to the second `Overwrite? (y/n):`, object clusterUser_RG1-KodeKloud-AKS_AKS1-KodeKloudApp) | question visible 170, 660.83; answer visible 171, 664.13 (11:04.1) | 171, 664.13 (11:04.1), `Merged "AKS1-KodeKloudApp" as current context in C:\Users\msadmin\.kube\config` and new prompt | High; lower-case `y` as displayed. Typed and submitted between 170 and 171. |
| 6 | `kubectl config current-context` | 175, 674.23 (11:14.2) as typed `kubectl config` + suggestion; fully typed 176, 676.30 (11:16.3) | 177, 677.13 (11:17.1), output `AKS1-KodeKloudApp` and new prompt | High. |
| 7 | `kubectl get nodes` | 180, 702.03 (11:42.0), already in scrollback with its output (never seen while being typed; 179 shows `kubectl get` + suggestion ` svc`) | between 179, 699.70 (11:39.7) and 180, 702.03 (11:42.0) | High for the text (all readers, every sighting); typing not observed. |
| 8 | `kubectl get deployment` | 185, 716.53 (11:56.5) as typed `kubectl get deplo` + suggestion `yment`; seen fully typed only after submission | 186, 716.90 (11:56.9), "No resources found in default namespace." and new prompt | High. |
| 9 | `kubectl get pods` | 187, 721.00 (12:01.0), already in scrollback with its output (never seen while being typed) | between 186, 716.90 (11:56.9) and 187, 721.00 (12:01.0) | High for the text; typing not observed. |

## Appeared on screen but was never run

| Text as displayed | Frames (t) | What the presenter had actually entered | What happened next |
|---|---|---|---|
| `az login` | 155 (620.67) | `a` | 156 shows a bare prompt on the same row: the line was cleared, not run. |
| `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 165 (655.00) | `az ak` | 166 shows `az aks get` + a different suggestion on the same row. |
| `kubectl rollout undo deployment/kodekloudapp` | 172 (668.13), 173 (668.87), 174 (669.47) | `kubect` (172), `kubectl` (173-174) | 175 shows `kubectl config` + suggestion ` current-context` on the same row. |
| `kubectl config current-context` (second showing, from history) | 178 (698.07) | `kubect` | 179 shows `kubectl get` + suggestion ` svc`; not run a second time. |
| `kubectl get svc` | 179 (699.70) | `kubectl get` | 180 shows `kubectl get nodes` executed instead. |

The suggestions in frames 161, 166, 175 and 185 were accepted or typed through and became executed commands 2, 3, 6 and 8.
