
## scores

| arm | positive (of 13) | negative (of 3) | correct / partial / wrong | rubric lines passed |
|---|---|---|---|---|
| G1 | 9/13 | 2.5/3 | 9 / 5 / 2 | 58/71 |
| pipe-grouponly-100-disc | 11/13 | 3/3 | 13 / 2 / 1 | 65/71 |

## verdicts

| Q | type | G1 label | pipe-grouponly-100-disc label | G1 lines | pipe-grouponly-100-disc lines |
|---|---|---|---|---|---|
| Q1 | open-ended overview | c | c | M1+ M2+ M3+ X1+ X2+ | M1+ M2+ M3+ X1+ X2+ |
| Q2 | open-ended sequence | c | w | M1+ M2+ M3+ M4+ X1+ X2+ | M1- M2- M3- M4- X1+ X2+ |
| Q3 | first thing on screen | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ |
| Q4 | exact values | p | c | M1+ M2+ M3+ M4- M5+ X1+ | M1+ M2+ M3+ M4+ M5+ X1+ |
| Q5 | order and times | c | c | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ |
| Q6 | evidence of success | c | c | M1+ M2+ M3+ X1+ | M1+ M2+ M3+ X1+ |
| Q7 | provenance of a value | p | c | M1+ M2+ M3- X1+ | M1+ M2+ M3+ X1+ |
| Q8 | event and choice | p | p | M1+ M2+ M3- X1+ X2+ | M1+ M2+ M3- X1+ X2+ |
| Q9 | exact query text | w | c | M1+ M2- M3- M4+ M5+ X1- X2+ | M1+ M2+ M3+ M4+ M5+ X1+ X2+ |
| Q10 | what changed | w | c | M1- M2- M3- X1+ X2+ | M1+ M2+ M3+ X1+ X2+ |
| Q11 | other applications | c | p | M1+ M2+ M3+ X1+ X2+ | M1+ M2+ M3- X1+ X2+ |
| Q14 | duration and time spent | c | c | M1+ M2+ X1+ | M1+ M2+ X1+ |
| Q15 | reproduction values | p | c | M1- M2+ M3+ M4- X1+ | M1+ M2+ M3+ M4+ X1+ |
| Q12 | nothing failed | c | c | M1+ X1+ X2+ | M1+ X1+ X2+ |
| Q13 | no profile created | c | c | M1+ X1+ | M1+ X1+ |
| Q16 | honesty check | p | c | M1+ M2- M3- X1+ | M1+ M2+ M3+ X1+ |

## failed

| arm | Q | line | statement | judge's quote from the answer |
|---|---|---|---|---|
| G1 | Q4 | M4 | gives the hostname `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` (a truncated form with `FRONTDOOR-A-cqhefshkhrgmgqf9` also holds). | `FRONTDOOR-A-hostname.z01.azurefd.net` |
| G1 | Q7 | M3 | contains the exact string `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`. | FRONTDOOR-A-d7c3eeafgnh2hrcs.z01.azurefd.net |
| G1 | Q8 | M3 | says the click or the choice itself is not captured (or hedges that it is inferred). | The account chosen was the first option |
| G1 | Q9 | M2 | gives the enrollment exclusion line (`requestUri_s !contains "enrollment"`). | \| where requestUri_s contains "enrollment" |
| G1 | Q9 | M3 | gives the summarize line with `strcat(httpStatusCode_d, requestUri_s)` and `bin(TimeGenerated, 1m)`. | summarize count() by strcat(httpStatusCode_d, originalURL_s), bin(TimeGenerated, 5m) |
| G1 | Q9 | X1 | gives `originName_s` or `bin(TimeGenerated, 5m)` as part of the query that was run. | bin(TimeGenerated, 5m) |
| G1 | Q10 | M1 | says the i.manage / r.manage / a.manage line was commented out (or removed). | //\| where requestUri_s contains "/manage/"... |
| G1 | Q10 | M2 | says a `ServiceA/Certificate` filter line was added. | \| where requestUri_s contains 'HostAuthenticationService/Certificate' |
| G1 | Q10 | M3 | says the record count went from 1000 to 277 (or that the result changed after the edit). |  |
| G1 | Q15 | M1 | contains the exact string `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`. | FRONTDOOR-A-d7hqa4g5edbwh4ea.z01.azurefd.net |
| G1 | Q15 | M4 | gives the query text including `FrontDoorAccessLog`, `!contains "enrollment"`, `ServiceA/Certificate` and the summarize line. | \| where requestUri_s contains "enrollment" |
| G1 | Q16 | M2 | says there are gaps between captures (some clicks or keystrokes are not seen, only inferred from before-and-after states) or that times are approximate to a few seconds. |  |
| G1 | Q16 | M3 | says the person's intent or reasons cannot be known from the record. |  |
| pipe-grouponly-100-disc | Q2 | M1 | puts the ap01 addition before the EU01 addition and the EU01 addition before the NA01 addition (or gives them times in increasing order about 1:04, 2:12, 2:32). |  |
| pipe-grouponly-100-disc | Q2 | M2 | places the log query after all three additions (a time after 2:40, or last). |  |
| pipe-grouponly-100-disc | Q2 | M3 | gives a time for the first addition's save between 0:58 and 1:10 (or frame 21-23). |  |
| pipe-grouponly-100-disc | Q2 | M4 | mentions the sign-in / "Pick an account" prompt between the first and second additions (a time between 1:30 and 1:45). |  |
| pipe-grouponly-100-disc | Q8 | M3 | says the click or the choice itself is not captured (or hedges that it is inferred). | Transition T34 (frames 33→34, 97.2→100.3s) records a click on the first account tile |
| pipe-grouponly-100-disc | Q11 | M3 | says it was used to copy or look up the `ServiceA/Certificate` filter line (or a query line) that then went into the portal query. | to compare the portal's Log Analytics query/chart with an equivalent saved query in Kusto.Explorer |

## exact

3 exact-string lines per arm; judge and mechanical check disagree on 0 lines.

| arm | Q | line | expected | in answer | judge | closest text in the answer |
|---|---|---|---|---|---|---|
| G1 | Q7 | M3 | `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` | no | False | `*FRONTDOOR-A-d7c3eeafgnh2hrcs.z01.azurefd.net*` |
| G1 | Q15 | M1 | `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` | no | False | `(nothing close)` |

## pipeline_readings

- G1 Q7 M3 `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`: FRONTDOOR-A-d7c3eeafgnh2hrcs.z01.azurefd.net
- pipe-grouponly-100-disc Q7 M3 `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`: FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net
- G1 Q9 M1 `FrontDoorAccessLog`: Category == 'FrontDoorAccessLog'
- pipe-grouponly-100-disc Q9 M1 `FrontDoorAccessLog`: | where Category == "FrontDoorAccessLog"
- G1 Q15 M1 `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`: FRONTDOOR-A-d7hqa4g5edbwh4ea.z01.azurefd.net
- pipe-grouponly-100-disc Q15 M1 `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`: `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`
