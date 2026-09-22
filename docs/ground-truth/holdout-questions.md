# Question set: the hold-out video `recording-2026-09-17.mp4`, frames 0-79 (draft)

Status: **DRAFT written by an agent from the frames of `runs/v2/grouponly-100/`, for the owner to correct. Nothing here
is accepted yet.** Correct a question, a reference answer or a rubric line in place, delete what you do not want asked,
add what is missing. Format follows `docs/ground-truth/full-questions.md` (readable by
`scry.evaluation.questions.parse_questions`).

Source: the 80 decoded frames (2048x1080) of `runs/v2/grouponly-100/frames/`, whole and in enlarged crops of the regions
asked about; `boxes.jsonl` for box ids and the spelling of long strings; where OCR and the image differ, the image wins.
Times are `t_settled` of `frames.jsonl` (minutes and seconds); 62 of the 80 frames are forced 3-second snapshots
(`settled: false`), so a time taken from one is good to about three seconds. The video's audio stream was not used
(the pipeline never reads it). Each question below was also asked once through `scry ask` on 2026-09-21; the verdicts
are in the "Asked" line and are for people, not the harness.

What the video shows, as read from the images:

| Frames | Time | On screen |
|---|---|---|
| 0-3 | 0:00-0:09 | Edge on Windows 11, Azure portal, `FRONTDOOR-A | Front Door manager`: two endpoints, the second hostname highlighted by find-on-page (`f9.b02.azurefd.net 1/1`). |
| 4 | 0:12 | Azure portal loading splash. |
| 5-9 | 0:15-0:26 | Traffic Manager profile `AU01-tm-profile`, Endpoints (au.endpoint and AFDEndpoint already listed). |
| 10-11 | 0:29-0:32 | Back on the FRONTDOOR-A Front Door manager page. |
| 12-25 | 0:35-1:14 | Profile `tm-profile-ap`: Overview, Endpoints, the "Add endpoint" panel (frames 16-21: Type External endpoint, Name AFDEndpoint, FQDN pasted, Weight 1), Add clicked; frame 22 the toast "Saved Traffic Manager profile changes" and a second table row. |
| 26-32 | 1:17-1:34 | Azure Home, then the "Network foundation \| Traffic managers" list. |
| 33 | 1:37 | `login.microsoftonline.com`, the Microsoft "Pick an account" dialog. |
| 34-36 | 1:40-1:46 | Splash, then `tm-profile-NA` Overview and Endpoints. |
| 37 | 1:49 | FRONTDOOR-A Front Door manager again. |
| 38-43 | 1:52-2:06 | Profile `tm-profile-EU`: Endpoints, the "Add endpoint" panel filled. |
| 44-45 | 2:09-2:12 | EU01 Overview, then Endpoints with the saved-changes toast. |
| 46-52 | 2:15-2:32 | Profile `tm-profile-NA`: "Add endpoint" panel, Add, "Saving" then "Saved" toasts. |
| 53-55 | 2:34-2:39 | Traffic managers list, NA01 Endpoints. |
| 56 | 2:42 | FRONTDOOR-A Front Door manager (find-on-page again). |
| 57-64 | 2:45-3:01 | `FRONTDOOR-A | Logs`: a KQL query on AzureDiagnostics with query history below; two lines deleted at frame 62; run at frame 64. |
| 65-71 | 3:04-3:21 | The query's time chart (y-axis to 30,000, "3s 28ms", "1000 records"); at frame 71 the i.manage line is commented out. |
| 72 | 3:24 | Kusto.Explorer (v1.0.3.1566), tab XSU-RUALSV2.kql, line `where requestUri_s contains "ServiceA/Certificate"` selected. |
| 73-79 | 3:27-3:44 | Back in the portal Logs blade: the 8-line query with the new line 5, "Running your query...", then the new chart (y-axis to 1,250, "3s 153ms", "277 records"). |

## Positive questions

### Q1 (positive, exact string)
- **Question:** What is the full hostname of the highlighted (selected) Front Door endpoint on the FRONTDOOR-A Front Door
  manager page at the very start of the video? Give it exactly as written.
- **Reference answer:** `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`, the second endpoint card on the page, drawn with
  an orange find-on-page highlight (the find bar reads `f9.b02.azurefd.net 1/1`). The first, unhighlighted endpoint is
  `FRONTDOOR-A-drgzexethuh8cpen.b02.azurefd.net`. On screen at frames 0-3 (0:00-0:09), again at 0:29, 1:49 and 2:42.
- **Rubric:**
  - M1: contains the exact string `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`.
  - X1: gives `FRONTDOOR-A-drgzexethuh8cpen.b02.azurefd.net` as the highlighted endpoint.
- **Evidence:** frame 0, box `0:b116` [399, 811, 666, 832]; checked in a 4x crop of the PNG. OCR reads it correctly on
  frames 0, 2, 11, 37, 56; one transition record shows a variant with `g` for `q`.
- **Asked 2026-09-21:** right. Answer gave the string exactly, cited 0:b116 and L116, noted the `g`/`q` OCR variant and
  resolved it from the image. 4 tool calls, $0.37, 30 s.

### Q2 (positive, what changed)
- **Question:** How does the KQL query in the FRONTDOOR-A Logs blade at the end of the video differ from the version that
  was run when the time chart first appeared at about 3:18?
- **Reference answer:** Two edits. (1) The line `| where requestUri_s contains "i.manage" or requestUri_s contains
  "r.manage" or requestUri_s contains "a.manage"` is commented out with `//` (visible from frame 71, 3:21). (2) A new
  line `| where requestUri_s contains "ServiceA/Certificate"` is inserted after the
  `!contains "enrollment"` line (visible from frame 73, 3:27), copied from the Kusto.Explorer query shown at 3:24.
  The query grows from 7 to 8 lines; the source table, `ago(2h)`, `Category == "FrontDoorAccessLog"`, the enrollment
  filter, the `summarize count() by strcat(httpStatusCode_d, requestUri_s), bin(TimeGenerated, 1m)` line and
  `render timechart` are unchanged. The re-run returns 277 records in "3s 153ms" instead of 1000 records.
- **Rubric:**
  - M1: says a line filtering on `ServiceA/Certificate` was added.
  - M2: says the i.manage / r.manage / a.manage line was commented out (or removed).
  - X1: says the summarize, render or enrollment lines changed.
  - X2: says the query was unchanged.
- **Evidence:** frame 70 boxes `70:b9x` (7 lines, all active); frame 71 box `71:b103` (`//| where ...`); frame 73 box
  `73:b99` (the new line 5) and `73:b109` (line number 8); frame 79 boxes `79:b170` (`3s 153ms`) and `79:b173`
  (`277 records`). Crops of frames 70, 72 and 75 checked by eye.
- **Asked 2026-09-21:** right. Both versions quoted line by line with box citations, the commenting-out placed at frame
  71 before the Kusto.Explorer switch, the new line at frame 73, and the new footer figures. 7 tool calls, $0.66, 67 s.

### Q3 (positive, when)
- **Question:** When does the "Saved Traffic Manager profile changes" notification appear for the first time, and for
  which Traffic Manager profile? List every later time it appears too, with the profile each time.
- **Reference answer:** First at about 1:04 (frame 22, between 1:01 and 1:04; still shown at frame 23, 1:06) for
  `tm-profile-ap`, right after Add was clicked in the Add endpoint panel. Then at about 2:12 (frame 45, between
  2:09 and 2:12) for `tm-profile-EU`, and at about 2:32 (frame 52, between 2:29 and 2:32) for
  `tm-profile-NA`, where the "Saving Traffic Manager profile" toast of frame 51 turns into it. Three times in
  all.
- **Rubric:**
  - M1: gives a first time between 0:58 and 1:10, or frame 22.
  - M2: names tm-profile-ap as the profile of the first appearance.
  - M3: gives the two later appearances, for EU01 (about 2:12) and NA01 (about 2:32).
  - X1: names EU01 or NA01 as the first profile.
- **Evidence:** frame 22 box `22:b55` [1629, 215, 1846, 237] and `22:b60` (the profile name); frame 45 `45:b61`; frame
  52 `52:b62`. Verified by eye on frame 22.
- **Asked 2026-09-21:** right. All three appearances with times, profiles and box citations; noted that the EU01 Add
  click itself was not captured. 4 tool calls, $0.23, 27 s.

### Q4 (positive, visual)
- **Question:** When the Microsoft "Pick an account" sign-in dialog is shown, how many accounts are listed in it,
  which one is highlighted, and at what time is it on screen?
- **Reference answer:** Two accounts, both "the account holder": `user@example.com` (first) and
  `user@example.com` (second), each marked "Connected to Windows", plus a third option "Use another account".
  The first tile is highlighted (grey background, dotted focus border). On screen at frame 33 only, about 1:37
  (between 1:34 and 1:37); gone by 1:40.
- **Rubric:**
  - M1: says two accounts are listed.
  - M2: says the first account (user@example.com) is the highlighted one.
  - M3: gives a time between 1:30 and 1:42, or frame 33.
  - X1: says the second account (user@example.com) is highlighted.
- **Evidence:** frame 33 boxes `33:b57` ("Pick an account"), `33:b59`/`33:b60` (first tile), `33:b65`/`33:b66`
  (second), `33:b71` ("Use another account"). Verified by eye on the half-size frame.
- **Asked 2026-09-21:** right, including the pointer position (1110, 264) away from the tile, so the highlight is focus,
  not hover. 3 tool calls, $0.23, 28 s.

## Negative questions

### Q5 (negative)
- **Question:** Does the presenter delete an endpoint from any Traffic Manager profile during the video?
- **Reference answer:** No. Every endpoint operation is an addition (Add endpoint on ap01, EU01 and NA01). The
  command-bar "Delete" is greyed out whenever it is visible and no confirmation dialog appears. The only deletion is of
  two lines of KQL text in the Logs editor (frames 61 to 62, about 2:55).
- **Rubric:**
  - M1: says no.
  - X1: says an endpoint was deleted.
- **Evidence:** frames 22, 45, 52 (tables grow, never shrink); frame 36 (Delete greyed).
- **Asked 2026-09-21:** right. "No", with the greyed Delete and the KQL line deletion as the only delete. 4 tool calls,
  $0.38, 28 s.

## Demo candidates (verified by eye)

| Ask | Verified answer | Cited evidence |
|---|---|---|
| The exact hostname highlighted on the Front Door manager page at the start | `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` | `runs/v2/grouponly-100/frames/00000.png`, box `0:b116` [399, 811, 666, 832], t 0:00 |
| What changed in the KQL query after the Kusto.Explorer visit | new line 5 `where requestUri_s contains "ServiceA/Certificate"`, the i.manage line commented out; 277 records instead of 1000 | `frames/00073.png` box `73:b99` [474, 432, 960, 453], t 3:27; `frames/00071.png` box `71:b103`; `frames/00079.png` boxes `79:b170`, `79:b173` |
| Which account is highlighted in the "Pick an account" dialog and when | the first, `user@example.com`, of two, at 1:37 | `frames/00033.png` boxes `33:b59`/`33:b60`, t 1:37 |
