
## scores

| arm | positive (of 4) | negative (of 1) | correct / partial / wrong | rubric lines passed |
|---|---|---|---|---|
| G1 | 2/4 | 1/1 | 3 / 0 / 2 | 13/16 |
| pipe-full-grouponly-067-r1 | 4/4 | 1/1 | 5 / 0 / 0 | 16/16 |
| pipe-full-none-r1 | 4/4 | 1/1 | 5 / 0 / 0 | 16/16 |
| pipe-full-transcribing-100-r1 | 4/4 | 1/1 | 5 / 0 / 0 | 16/16 |
| pipe-grouponly-100 | 4/4 | 1/1 | 5 / 0 / 0 | 16/16 |

## verdicts

| Q | type | G1 label | pipe-full-grouponly-067-r1 label | pipe-full-none-r1 label | pipe-full-transcribing-100-r1 label | pipe-grouponly-100 label | G1 lines | pipe-full-grouponly-067-r1 lines | pipe-full-none-r1 lines | pipe-full-transcribing-100-r1 lines | pipe-grouponly-100 lines |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | exact string | w | c | c | c | c | M1- X1+ | M1+ X1+ | M1+ X1+ | M1+ X1+ | M1+ X1+ |
| Q2 | what changed | w | c | c | c | c | M1- M2- X1+ X2+ | M1+ M2+ X1+ X2+ | M1+ M2+ X1+ X2+ | M1+ M2+ X1+ X2+ | M1+ M2+ X1+ X2+ |
| Q3 | when | c | c | c | c | c | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ |
| Q4 | visual | c | c | c | c | c | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ |
| Q5 | did they | c | c | c | c | c | M1+ X1+ | M1+ X1+ | M1+ X1+ | M1+ X1+ | M1+ X1+ |

## failed

| arm | Q | line | statement | judge's quote from the answer |
|---|---|---|---|---|
| G1 | Q1 | M1 | contains the exact string `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`. | FRONTDOOR-A-cnhedcc5b0d0h4e0.z01.azurefd.net |
| G1 | Q2 | M1 | says a line filtering on `ServiceA/Certificate` was added. | contains "testHostDeviceAllocationServiceClientCertificate" |
| G1 | Q2 | M2 | says the i.manage / r.manage / a.manage line was commented out (or removed). | The added line was pasted in |

## exact

1 exact-string lines per arm; judge and mechanical check disagree on 0 lines.

| arm | Q | line | expected | in answer | judge | closest text in the answer |
|---|---|---|---|---|---|---|
| G1 | Q1 | M1 | `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` | no | False | `FRONTDOOR-A-cnhedcc5b0d0h4e0.z01.azurefd.net` |

## pipeline_readings

- G1 Q1 M1 `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`: FRONTDOOR-A-cnhedcc5b0d0h4e0.z01.azurefd.net
- pipe-full-grouponly-067-r1 Q1 M1 `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`: **FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net**
- pipe-full-none-r1 Q1 M1 `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`: **FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net**
- pipe-full-transcribing-100-r1 Q1 M1 `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`: **FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net**
- pipe-grouponly-100 Q1 M1 `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`: **`FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`**

## cost

| arm | build per video | $ per question (mean; each) | seconds per question (mean; each) | notes |
|---|---|---|---|---|
| G1 Gemini direct, silent copy | upload 27.9 s, no charge | $0.060; 0.026, 0.108, 0.089, 0.060, 0.017 | 28; 25, 46, 32, 30, 8 | mean per call: prompt 1438 tokens, tool use 62236 (video 28406), thinking 2771, output 517, cached 0 |
| pipeline, group-only 0.67 (runs/eval/v2/full-grouponly-067-r1) | $7.6778 (annotate, interpret, summarize; the manifest's total) | $0.381; 0.312, 0.648, 0.269, 0.220, 0.458 | 43; 32, 79, 35, 30, 36 | mean input 103025 tokens, output 1880; 3.4 turns, 4.4 tool calls; 4 of 5 answers opened a frame or redecoded |
| pipeline, no annotation (runs/eval/v2/full-none-r1) | $2.9399 (annotate, interpret, summarize; the manifest's total) | $0.349; 0.227, 0.685, 0.256, 0.181, 0.398 | 36; 25, 82, 26, 17, 30 | mean input 91956 tokens, output 2091; 3.6 turns, 4.8 tool calls; 4 of 5 answers opened a frame or redecoded |
| pipeline, transcribing 1.0 (runs/eval/v2/full-transcribing-100-r1) | $11.4237 (annotate, interpret, summarize; the manifest's total) | $0.392; 0.328, 0.870, 0.137, 0.165, 0.461 | 34; 22, 83, 18, 17, 32 | mean input 116515 tokens, output 1907; 3.4 turns, 4.2 tool calls; 3 of 5 answers opened a frame or redecoded |
| pipeline, group-only 1.0 (owner's default, runs/v2/grouponly-100) | $9.3163 (annotate, interpret, summarize; the manifest's total) | $0.372; 0.367, 0.659, 0.226, 0.225, 0.384 | 36; 30, 66, 27, 28, 28 | mean input 99253 tokens, output 1940; 3.4 turns, 4.4 tool calls; 4 of 5 answers opened a frame or redecoded |

Break-even against G1 (questions per video after which build plus per-question cost is below G1's):

- pipeline, group-only 0.67 (runs/eval/v2/full-grouponly-067-r1): never, G1 is cheaper per question ($0.060 against $0.381) and has no build
- pipeline, no annotation (runs/eval/v2/full-none-r1): never, G1 is cheaper per question ($0.060 against $0.349) and has no build
- pipeline, transcribing 1.0 (runs/eval/v2/full-transcribing-100-r1): never, G1 is cheaper per question ($0.060 against $0.392) and has no build
- pipeline, group-only 1.0 (owner's default, runs/v2/grouponly-100): never, G1 is cheaper per question ($0.060 against $0.372) and has no build

## perq

| Q | style | G1 label | pipe-full-grouponly-067-r1 label | pipe-full-none-r1 label | pipe-full-transcribing-100-r1 label | pipe-grouponly-100 label | G1 $ | pipe-full-grouponly-067-r1 $ | pipe-full-none-r1 $ | pipe-full-transcribing-100-r1 $ | pipe-grouponly-100 $ | G1 s | pipe-full-grouponly-067-r1 s | pipe-full-none-r1 s | pipe-full-transcribing-100-r1 s | pipe-grouponly-100 s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q1 | exact string | w | c | c | c | c | 0.026 | 0.312 | 0.227 | 0.328 | 0.367 | 25 | 32 | 25 | 22 | 30 |
| Q2 | what changed | w | c | c | c | c | 0.108 | 0.648 | 0.685 | 0.870 | 0.659 | 46 | 79 | 82 | 83 | 66 |
| Q3 | when | c | c | c | c | c | 0.089 | 0.269 | 0.256 | 0.137 | 0.226 | 32 | 35 | 26 | 18 | 27 |
| Q4 | visual | c | c | c | c | c | 0.060 | 0.220 | 0.181 | 0.165 | 0.225 | 30 | 30 | 17 | 17 | 28 |
| Q5 | did they | c | c | c | c | c | 0.017 | 0.458 | 0.398 | 0.461 | 0.384 | 8 | 36 | 30 | 32 | 28 |

## citations

| arm | answers | with at least one mm:ss time | times per answer (mean, min) | answers naming a frame number | answers saying the video does not show something |
|---|---|---|---|---|---|
| G1 | 5 | 5 | 8.2, 3 | 0 | 1 |
| pipe-full-grouponly-067-r1 | 5 | 2 | 1.4, 0 | 5 | 0 |
| pipe-full-none-r1 | 5 | 2 | 1.2, 0 | 5 | 0 |
| pipe-full-transcribing-100-r1 | 5 | 2 | 2.2, 0 | 5 | 0 |
| pipe-grouponly-100 | 5 | 4 | 3.4, 0 | 5 | 0 |
