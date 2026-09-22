
## scores

| arm | positive (of 22) | negative (of 5) | correct / partial / wrong | rubric lines passed |
|---|---|---|---|---|
| G1 | 17/22 | 5/5 | 19 / 6 / 2 | 70/83 |
| G2 | 16.5/22 | 5/5 | 17 / 9 / 1 | 70/83 |
| P4 full-inc-transcribing-r1 | 22/22 | 5/5 | 27 / 0 / 0 | 83/83 |
| P4 full-inc-transcribing-r2 | 22/22 | 5/5 | 27 / 0 / 0 | 83/83 |
| P4 full-none-r1 | 22/22 | 5/5 | 27 / 0 / 0 | 83/83 |
| P4 full-none-r2 | 22/22 | 5/5 | 27 / 0 / 0 | 83/83 |
| P6 full-inc-transcribing-indexonly-r1 | 22/22 | 5/5 | 27 / 0 / 0 | 83/83 |
| P6 full-inc-transcribing-indexonly-r2 | 22/22 | 5/5 | 27 / 0 / 0 | 83/83 |
| P6 full-inc-transcribing-batch-indexonly-r1 | 22/22 | 5/5 | 27 / 0 / 0 | 83/83 |
| P6 full-none-indexonly-r1 | 21.5/22 | 5/5 | 26 / 1 / 0 | 82/83 |
| P6 full-none-indexonly-r2 | 21.5/22 | 5/5 | 26 / 1 / 0 | 82/83 |
| P9 full-inc-transcribing-asksonnet-r1 | 22/22 | 5/5 | 27 / 0 / 0 | 83/83 |
| P9 full-inc-transcribing-asksonnet-r2 | 21.5/22 | 5/5 | 26 / 1 / 0 | 82/83 |
| P9 full-none-asksonnet-r1 | 22/22 | 5/5 | 27 / 0 / 0 | 83/83 |
| P9 full-none-asksonnet-r2 | 22/22 | 5/5 | 27 / 0 / 0 | 83/83 |

## types

| question type | n | G1 | G2 | P4 (mean of 4 runs) | P6 (mean of 5 runs) | P9 (mean of 4 runs) |
|---|---|---|---|---|---|---|
| exact string | 8 | 4/8 | 4.5/8 | 8/8 | 8/8 | 7.9/8 |
| when | 2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| worded without the on-screen words | 4 | 3.5/4 | 3.5/4 | 4/4 | 4/4 | 4/4 |
| value in several states or places | 10 | 8/10 | 7/10 | 10/10 | 10/10 | 10/10 |
| order across the video | 2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| diagram (Q2) | 1 | 1/1 | 1/1 | 1/1 | 0.8/1 | 1/1 |
| negative | 5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 |

## verdicts

| Q | type | G1 label | G2 label | G1 lines | G2 lines | P4 (4 runs) | P6 (5 runs) | P9 (4 runs) |
|---|---|---|---|---|---|---|---|---|
| Q1 | worded without the slide's words | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q2 | labels in a diagram | c | c | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ | cccc | cccpp | cccc |
| Q3 | when did they | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q4 | a value typed into a form field | p | p | M1- M2+ M3+ X1+ | M1- M2+ M3+ X1+ | cccc | ccccc | cccc |
| Q5 | a value before and after it was changed | c | p | M1+ M2+ M3+ X1+ | M1+ M2+ M3- X1+ | cccc | ccccc | cccc |
| Q6 | the form against the running cluster | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q7 | worded without the on-screen words and first against final state | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q8 | a value before and after with an error in between | c | w | M1+ M2+ M3+ X1+ | M1+ M2+ M3- X1- | cccc | ccccc | cccc |
| Q9 | worded without the on-screen words with the value in two places | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q10 | a changed choice and an exact string | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q11 | values typed and chosen in a side panel | p | p | M1- M2+ X1+ | M1- M2+ X1+ | cccc | ccccc | cccc |
| Q12 | an exact string that appears in several places | p | p | M1- M2+ X1+ | M1- M2+ X1+ | cccc | ccccc | cccc |
| Q13 | when did they | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q14 | exact-string lookup with a near miss elsewhere | p | p | M1+ M2- X1+ | M1+ M2- X1+ | cccc | ccccc | cccc |
| Q15 | a page that is on screen for three seconds | p | p | M1- M2+ M3+ M4+ X1+ | M1- M2+ M3- M4+ X1+ | cccc | ccccc | cpcc |
| Q16 | exact command and when | w | p | M1- M2- M3+ X1- | M1- M2- M3+ X1+ | cccc | ccccc | cccc |
| Q17 | the same command at two moments | c | p | M1+ M2+ X1+ | M1+ M2- X1+ | cccc | ccccc | cccc |
| Q18 | how many times | w | c | M1- M2- X1- | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q19 | exact-string lookup among similar values | p | p | M1- M2- M3+ X1+ | M1+ M2- M3+ X1+ | cccc | ccccc | cccc |
| Q20 | similar values in different places | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q21 | order across the video | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |
| Q22 | order across the video | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ | cccc | ccccc | cccc |
| Q23 | did they | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |
| Q24 | did they | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |
| Q25 | was a page shown | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |
| Q26 | did they | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |
| Q27 | where did a value come from | c | c | M1+ X1+ | M1+ X1+ | cccc | ccccc | cccc |

## failed

| arm | Q | line | statement | judge's quote from the answer |
|---|---|---|---|---|
| G1 | Q4 | M1 | contains the exact string `RG1-KodeKloud-AKS`. | `RG1-kodecloud-AKS` |
| G1 | Q11 | M1 | contains the exact string `crkodekloud`. | cklcloudaks1 |
| G1 | Q12 | M1 | contains the exact string `MC_RG1-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia`. | MC_RG1-KodeKloud-AKS_AKS1-KodekloudApp_southeastasia |
| G1 | Q14 | M2 | gives the start time 4/4/2023, 9:32:34 PM (any clear spelling of that date and time). | 4/4/2023, 9:22:34 PM |
| G1 | Q15 | M1 | contains the exact string `hpranav/kodekloudappcs`. | hpranav/kodekloudapps |
| G1 | Q16 | M1 | contains the exact string `kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1 --replicas=1`. | `kubectl create deployment kodekloudapp --image=hpranav/kodekloudapp:v1 --replicas=1` |
| G1 | Q16 | M2 | gives a time between 12:34 and 12:45 for the run, or frame 197 or 198. | The command was executed at **12:47**–**12:48**. |
| G1 | Q16 | X1 | gives a different image or tag (for example `:v2`), or says the deployment was created from a YAML file. | --image=hpranav/kodekloudapp:v1 |
| G1 | Q18 | M1 | says it was run twice. | run **2 times on-screen** (and appears in total **3 times** |
| G1 | Q18 | M2 | says the first run found nothing and the second listed one running pod (kodekloudapp-67ffc758c5-mm42w). | kodekloudapp-679b75cb5-mm42w   0/1     ContainerCreating |
| G1 | Q18 | X1 | says it was run three or more times, or only once. | in total **3 times** in the terminal session |
| G1 | Q19 | M1 | contains the exact string `20.247.251.108`, given as the external IP. | 20.247.253.108 |
| G1 | Q19 | M2 | contains the exact string `10.0.199.121`, given as the cluster IP. | 10.0.198.121 |
| G2 | Q4 | M1 | contains the exact string `RG1-KodeKloud-AKS`. | `R01-KodeKloud-AKS` |
| G2 | Q5 | M3 | says the field read Australia Southeast for a moment before going back to Southeast Asia. | the only prior value the transcript shows |
| G2 | Q8 | M3 | says an error appeared while typing (the minimum is 30, or the value must be between 30 and 250), or gives a time between 6:59 and 7:09 or frame 95 for it. | no validation error is recorded for the max‑pods field |
| G2 | Q8 | X1 | gives 110 or 250 as the final value, or says no error or warning appeared. | no error/complaint is shown for that field |
| G2 | Q11 | M1 | contains the exact string `crkodekloud`. | ckadkodekloud |
| G2 | Q12 | M1 | contains the exact string `MC_RG1-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia`. | MC_R01-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia |
| G2 | Q14 | M2 | gives the start time 4/4/2023, 9:32:34 PM (any clear spelling of that date and time). | `4/4/2023, 9:22:34 PM` |
| G2 | Q15 | M1 | contains the exact string `hpranav/kodekloudappcs`. | hpranav/kodekloudapps |
| G2 | Q15 | M3 | says the repository has 2 tags. | only one tag is shown listed |
| G2 | Q16 | M1 | contains the exact string `kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1 --replicas=1`. | --image=hpranav/kodekloudapps:v1 --replicas=1 |
| G2 | Q16 | M2 | gives a time between 12:34 and 12:45 for the run, or frame 197 or 198. | executed/Enter pressed at 12:47 |
| G2 | Q17 | M2 | says the second run listed kodekloudapp as ready, 1/1 (around 12:48). | kodekloudapp   0/1     1            0           4s |
| G2 | Q19 | M2 | contains the exact string `10.0.199.121`, given as the cluster IP. | 10.0.198.121 |

## exact

14 exact-string lines per arm; judge and mechanical check disagree on 0 lines.

| arm | Q | line | expected | in answer | judge | closest text in the answer |
|---|---|---|---|---|---|---|
| G1 | Q4 | M1 | `RG1-KodeKloud-AKS` | no | False | `RG1-kodecloud-AKS` |
| G1 | Q11 | M1 | `crkodekloud` | no | False | ` cklclouda` |
| G1 | Q12 | M1 | `MC_RG1-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia` | no | False | `MC_RG1-KodeKloud-AKS_AKS1-KodekloudApp_southeastasia` |
| G1 | Q15 | M1 | `hpranav/kodekloudappcs` | no | False | `/hpranav/kodekloudapps` |
| G1 | Q16 | M1 | `kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1 --replicas=1` | no | False | ` kubectl create deployment kodekloudapp --image=hpranav/kodekloudapp:v1 --replicas=1` |
| G1 | Q19 | M1 | `20.247.251.108` | no | False | `20.247.253.108` |
| G1 | Q19 | M2 | `10.0.199.121` | no | False | `10.0.198.121` |
| G2 | Q4 | M1 | `RG1-KodeKloud-AKS` | no | False | `R01-KodeKloud-AKS` |
| G2 | Q11 | M1 | `crkodekloud` | no | False | `adkodekloud` |
| G2 | Q12 | M1 | `MC_RG1-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia` | no | False | `MC_R01-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia` |
| G2 | Q15 | M1 | `hpranav/kodekloudappcs` | no | False | `hpranav/kodekloudapps/` |
| G2 | Q16 | M1 | `kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1 --replicas=1` | no | False | `kubectl create deployment kodekloudapp --image=hpranav/kodekloudapps:v1 --replicas=1
` |
| G2 | Q19 | M2 | `10.0.199.121` | no | False | `10.0.198.121` |

## pipeline_readings

- Q2 M1: the blue chips **"HCL"**
- Q2 M2: **"HNS"** appeared beside it
- Q4 M1: `RG1-KodeKloud-AKS`
- Q6 M1: 1.24.9 (default)
- Q6 M2: running cluster later reports **1.24.10**
- Q10 M2: (new) default (10.224.0.0/16)
- Q11 M1: Name: `crkodekloud`
- Q12 M1: `MC_RG1-KodeKloud-AKS_AKS1-KodeKloudApp_southeastasia`
- Q14 M1: `microsoft.aks-20230404212734`
- Q15 M1: hub.docker.com/repository/docker/hpranav/kodekloudappcs/general
- Q16 M1: kubectl create deployment kodekloudapp --image=hpranav/kodekloudappcs:v1 --replicas=1
- Q19 M1: **20.247.251.108** (213:b115)
- Q19 M2: **10.0.199.121** (213:b114)
- Q20 M1: `IP address: ::ffff:10.224.0.31`

## cost

| arm | one-time per video | per question | seconds per question | notes |
|---|---|---|---|---|
| G1 Gemini direct | upload 25.1 s, $0 | $0.0785 (min 0.0177, max 0.3337); sum over 27 $2.121 | 32.2 (min 12, max 116) | mean tokens per call: prompt 1028, tool use 92940 (video 43888, text 5165), thinking 1676, output 478, cached 27837 |
| G1c Gemini command list | | $0.9654 for the one call | 384 | tool use 1238330 tokens |
| G2 Gemini transcript | $0.4100, 237 s (20971 chars, 7707 output tokens) | $0.0152 amortised over 27 | 8.8 amortised | tool use 461781 tokens (video 218658) |
| G2 Opus answers | | $0.0230 (sum $0.622); with the transcript amortised $0.0382 | 17.4 (min 5, max 32) | mean input 9761 tokens (26 of 27 read the cache), output 625 |
| pipeline (P4, annotated) | $17.85 | $0.263 | 22.0 | docs/results/p4, p6 |
| pipeline (unannotated) | $4.62 | $0.216 | | docs/results/p6 |
| pipeline, Sonnet agent (P9, annotated) | $17.85 | $0.062 | 9.5 | docs/results/p9 |
| pipeline, Sonnet agent (P9, unannotated) | $4.62 | $0.053 | 9.5 | docs/results/p9 |

Break-even (the number of questions per video after which the pipeline's build plus per-question cost is below the arm's):

- annotated, Opus agent pipeline against G1: never; G1 is cheaper per question ($0.0785 against $0.263) and has no build
- annotated, Opus agent pipeline against G2: never; G2 is cheaper per question ($0.0382 against $0.263) and has no build
- unannotated, Opus agent pipeline against G1: never; G1 is cheaper per question ($0.0785 against $0.216) and has no build
- unannotated, Opus agent pipeline against G2: never; G2 is cheaper per question ($0.0382 against $0.216) and has no build
- annotated, Sonnet agent pipeline against G1: the pipeline's total is lower after 1079 questions on this video (build $17.85 / ($0.0785 - $0.062 per question))
- annotated, Sonnet agent pipeline against G2: never; G2 is cheaper per question ($0.0382 against $0.062) and has no build
- unannotated, Sonnet agent pipeline against G1: the pipeline's total is lower after 181 questions on this video (build $4.62 / ($0.0785 - $0.053 per question))
- unannotated, Sonnet agent pipeline against G2: never; G2 is cheaper per question ($0.0382 against $0.053) and has no build

## perq

| Q | G1 $ | G1 s | G1 video tokens | G1 cached | G1 label | G2 Opus $ | G2 s | G2 output tokens | G2 label |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | 0.0237 | 17 | 12870 | 0 | c | 0.0699 | 5 | 362 | c |
| Q2 | 0.0938 | 49 | 49368 | 0 | c | 0.0225 | 9 | 682 | c |
| Q3 | 0.0339 | 33 | 17952 | 0 | c | 0.0131 | 6 | 312 | c |
| Q4 | 0.0255 | 25 | 13002 | 0 | p | 0.0166 | 6 | 451 | p |
| Q5 | 0.0333 | 26 | 16500 | 0 | c | 0.0178 | 6 | 502 | p |
| Q6 | 0.0777 | 24 | 44220 | 0 | c | 0.0230 | 10 | 705 | c |
| Q7 | 0.1725 | 44 | 93984 | 74998 | c | 0.0255 | 11 | 805 | c |
| Q8 | 0.0827 | 38 | 45606 | 0 | c | 0.0306 | 15 | 1010 | w |
| Q9 | 0.0351 | 20 | 18282 | 0 | c | 0.0228 | 10 | 699 | c |
| Q10 | 0.0387 | 28 | 19932 | 0 | c | 0.0201 | 14 | 591 | c |
| Q11 | 0.3337 | 56 | 180312 | 243585 | p | 0.0165 | 13 | 446 | p |
| Q12 | 0.0645 | 28 | 36894 | 0 | p | 0.0220 | 14 | 663 | p |
| Q13 | 0.0497 | 17 | 29172 | 0 | c | 0.0132 | 14 | 314 | c |
| Q14 | 0.0221 | 32 | 12210 | 0 | p | 0.0119 | 14 | 262 | p |
| Q15 | 0.0241 | 24 | 12540 | 0 | p | 0.0198 | 18 | 574 | p |
| Q16 | 0.0907 | 38 | 52008 | 0 | w | 0.0175 | 16 | 486 | p |
| Q17 | 0.2242 | 46 | 136224 | 167878 | c | 0.0150 | 18 | 385 | p |
| Q18 | 0.2952 | 116 | 177012 | 265132 | w | 0.0250 | 26 | 787 | c |
| Q19 | 0.0257 | 45 | 13530 | 0 | p | 0.0172 | 21 | 475 | p |
| Q20 | 0.0242 | 13 | 11022 | 0 | c | 0.0219 | 24 | 660 | c |
| Q21 | 0.1013 | 24 | 58080 | 0 | c | 0.0299 | 26 | 967 | c |
| Q22 | 0.0347 | 14 | 17820 | 0 | c | 0.0386 | 32 | 1316 | c |
| Q23 | 0.0908 | 53 | 51084 | 0 | c | 0.0270 | 29 | 870 | c |
| Q24 | 0.0274 | 12 | 15180 | 0 | c | 0.0228 | 26 | 701 | c |
| Q25 | 0.0397 | 14 | 22242 | 0 | c | 0.0192 | 28 | 556 | c |
| Q26 | 0.0177 | 17 | 6732 | 0 | c | 0.0177 | 27 | 497 | c |
| Q27 | 0.0382 | 18 | 21186 | 0 | c | 0.0249 | 32 | 786 | c |

## citations

| arm | answers | with at least one mm:ss time | times per answer (mean, min) | answers naming a frame number | answers saying the video does not show something |
|---|---|---|---|---|---|
| G1 | 27 | 27 | 7.1, 3 | 0 | 3 |
| G2 | 27 | 27 | 12.0, 4 | 0 | 4 |
