# Candidate list: commands executed in frames 155-187 (runs/span2-before) - for the owner to correct

Source: RapidOCR first pass, Google Cloud Vision and the language model's readings of each frame, cross-checked by eye on
gamma-brightened crops (peek_commands.png). Times are `t_settled` of the frame in `stage1.jsonl` (seconds; mm:ss in brackets).
"First fully visible" = first frame in which the whole command text is on screen (typed, or typed prefix plus grey
PSReadLine prediction, as noted). "Submitted" = first frame in which output or a new prompt appears below it, so the Enter
key fell between the previous frame and that one. Capitalisation is as displayed. The terminal is not visible in frames 182-184
(portal pages); nothing was run there (the prompt row of 181 is unchanged in 185).

## Executed, in order

| # | Text as displayed | First fully visible (frame, t) | Submitted (frame, t) | Confidence note |
|---|---|---|---|---|
| 1 | `az account show` | 157, 628.77 (10:28.8), fully typed, no prediction | 158, 629.57 (10:29.6), JSON output and new prompt | High. All readers agree on the command (RapidOCR's detector cut the leading `PS` of this row in scrollback; command text unaffected). |
| 2 | `az configure --defaults group=RG1-KodeKloud-AKS` | 161, 649.17 (10:49.2) as typed `az c` + grey prediction; fully typed from 162, 652.00 (10:52.0) | 164, 653.57 (10:53.6), new prompt below, no output | High. RapidOCR (settled rows) and the model agree; Vision reads `=` as `-` and `KodeKloud` as `Kodekloud` on most sightings, by eye it is `=` and `KodeKloud`. |
| 3 | `az aks get-Credentials --name AKS1-KodeKloudApp` | 166, 656.20 (10:56.2) as typed `az aks get` + prediction; fully typed from 167, 657.07 (10:57.1) | 169, 659.27 (10:59.3), "A different object named AKS1-KodeKloudApp already exists..." | High. Capital `C` in `get-Credentials` is on screen (RapidOCR and Vision on all 16 scrollback sightings; the model lower-cased it in 2 of 16 scrollback sightings). |
| 4 | `Y` (answer to the first `Overwrite? (y/n):`, object AKS1-KodeKloudApp) | question visible 169, 659.27; answer visible 170, 660.83 (11:00.8) | 170, 660.83 (11:00.8), second message and second question already below it | High for "answered yes"; capital `Y` as displayed (RapidOCR, Vision, by eye). Typed and submitted between 169 and 170. |
| 5 | `y` (answer to the second `Overwrite? (y/n):`, object clusterUser_RG1-KodeKloud-AKS_AKS1-KodeKloudApp) | question visible 170, 660.83; answer visible 171, 664.13 (11:04.1) | 171, 664.13 (11:04.1), `Merged "AKS1-KodeKloudApp" as current context in C:\Users\msadmin\.kube\config` and new prompt | High; lower-case `y` as displayed. Typed and submitted between 170 and 171. |
| 6 | `kubectl config current-context` | 175, 674.23 (11:14.2) as typed `kubectl config` + prediction; fully typed 176, 676.30 (11:16.3) | 177, 677.13 (11:17.1), output `AKS1-KodeKloudApp` and new prompt | High. |
| 7 | `kubectl get nodes` | 180, 702.03 (11:42.0), already in scrollback with its output (never seen while being typed; 179 shows `kubectl get` + prediction ` svc`) | between 179, 699.70 (11:39.7) and 180, 702.03 (11:42.0) | High for the text (all readers, every sighting); typing not observed. |
| 8 | `kubectl get deployment` | 185, 716.53 (11:56.5) as typed `kubectl get deplo` + prediction `yment`; seen fully typed only after submission | 186, 716.90 (11:56.9), "No resources found in default namespace." and new prompt | High. |
| 9 | `kubectl get pods` | 187, 721.00 (12:01.0), already in scrollback with its output (never seen while being typed) | between 186, 716.90 (11:56.9) and 187, 721.00 (12:01.0) | High for the text; typing not observed. |

## Shown as grey prediction (ghost text) but never executed

| Text as displayed | Frames (t) | Typed prefix (bright) | What happened next |
|---|---|---|---|
| `az login` | 155 (620.67) | `a` (the `z` under the cursor bar is already grey) | 156 shows a bare prompt on the same row: the line was cleared, not run. Vision and the model both read this line as `a login`. |
| `az aks scale --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp --node-count 2` | 165 (655.00) | `az ak` | 166 shows `az aks get` + a different prediction on the same row. |
| `kubectl rollout undo deployment/kodekloudapp` | 172 (668.13), 173 (668.87), 174 (669.47) | `kubect` (172), `kubectl` (173-174) | 175 shows `kubectl config` + prediction ` current-context` on the same row. |
| `kubectl config current-context` (second showing, from history) | 178 (698.07) | `kubect` | 179 shows `kubectl get` + prediction ` svc`; not run a second time. |
| `kubectl get svc` | 179 (699.70) | `kubectl get` | 180 shows `kubectl get nodes` executed instead. |

The parallel check's four predictions (`az login`, `az aks scale ...`, `kubectl rollout undo ...`, `kubectl get svc`) are confirmed on
the images; the fifth row above (the repeated `kubectl config current-context` in 178) is an addition. The predictions in 161, 166, 175
and 185 were accepted or typed through and became executed commands 2, 3, 6 and 8.
