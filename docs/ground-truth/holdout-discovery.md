# Question set: discovering the hold-out video from the index alone (draft)

Status: **DRAFT written by an agent from the frames of `runs/v2/grouponly-100/`, for the owner to correct. Nothing here
is accepted yet.** Correct a question, a reference answer or a rubric line in place, delete what you do not want asked,
add what is missing. Format follows `docs/ground-truth/full-questions.md` (readable by
`scry.evaluation.questions.parse_questions`).

Why this set exists: the questions of `holdout-questions.md` are written by someone who has seen the video. These
sixteen are the natural sequence of inquiries of a person who has NEVER seen it and may not have the file: they have the
index and the MCP tools, and want to find out what happened, what actions were taken and how the person behaved. They
are asked in order, in one conversation; a follow-up carries terms from earlier answers ("you said an endpoint was
added", "the hostname that was pasted", "near the end the person ran a query"), as a real conversation would. The
"Follows" line of each question says what it follows up. The transcript of one such conversation, run through the
MCP server from Claude Code with the judge's verdicts, is `docs/presentation/mcp-discovery.md`.

Source: the 80 decoded frames (2048x1080) of `runs/v2/grouponly-100/frames/`, whole (contact sheets of all 80) and in
enlarged crops of the "Add endpoint" panels (frames 17, 19, 21, 43, 50), the endpoint tables and toasts (frames 17, 22,
45, 52, 55), the KQL editor (frames 58, 62, 64, 70, 71, 73, 79), the chart footers (frames 70, 79), the Kusto.Explorer
window (frame 72) and the sign-in dialog (frame 33). Where OCR and the image differ, the image wins. Times are
`t_settled` of `frames.jsonl` as minutes and seconds; 62 of the 80 frames are forced 3-second snapshots (`settled:
false`), so a time taken from one is good to about three seconds. The video's audio was not used (the pipeline never
reads it). No model was called to write this file.

Two corrections to the frame table of `holdout-questions.md`, found while verifying: frame 17 (0:50) is the
`tm-profile-AU | Endpoints` page (au.endpoint weight 100, AFDEndpoint weight 50), a short look at a profile
that already has the endpoint, in the middle of filling the ap01 form; and frame 55 (2:38) is that same AU01 page again,
not NA01.

What the video shows, as read from the images:

| Frames | Time | On screen |
|---|---|---|
| 0-3 | 0:00-0:09 | Edge on Windows 11, Azure portal, `FRONTDOOR-A \| Front Door manager`: two endpoints, the second hostname `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` highlighted by find-on-page (`f9.b02.azurefd.net 1/1`). |
| 4 | 0:12 | Azure portal loading splash. |
| 5-9 | 0:15-0:26 | Traffic Manager profile `AU01-tm-profile`, Endpoints (au.endpoint and AFDEndpoint already listed). |
| 10-11 | 0:29-0:32 | Back on the FRONTDOOR-A Front Door manager page. |
| 12-16 | 0:35-0:48 | Profile `tm-profile-ap`: Overview (12), Endpoints with one row `ap.endpoint` (13-14), the "Add endpoint" panel opening (15, "Loading"), then with Type "Azure endpoint" and Name `AFDEndpoint` typed (16). |
| 17 | 0:50 | `tm-profile-AU \| Endpoints`: au.endpoint 100, AFDEndpoint 50 (a look at a profile that already has it). |
| 18-21 | 0:54-1:00 | ap01 "Add endpoint" panel: the Type dropdown open (18), Type "External endpoint" with the FQDN empty (19), FQDN pasted and Weight 1 (20), the pointer on Add (21). Enable Endpoint is unchecked. |
| 22-23 | 1:04-1:06 | Toast "Saved Traffic Manager profile changes ... 'tm-profile-ap'"; second row `AFDEndpoint  Disabled  Disabled  External endpoint  1`. Frame 23: the portal search box open (search history ap01-pem, au01, ...). |
| 24-25 | 1:10-1:14 | ap01 Endpoints, then Overview. |
| 26-32 | 1:17-1:34 | Azure Home, then `Network foundation \| Traffic managers` (12 profiles listed). |
| 33 | 1:37 | `login.microsoftonline.com`, Microsoft "Pick an account": the account holder `user@example.com` (highlighted), the account holder `user@example.com`, "Use another account". |
| 34-36 | 1:40-1:46 | Splash, then `tm-profile-NA` Overview and Endpoints (one row, na.endpoint). |
| 37 | 1:49 | FRONTDOOR-A Front Door manager again (find-on-page still on the hostname). |
| 38-43 | 1:52-2:06 | `tm-profile-EU`: Endpoints (one row, eu.endpoint), the "Add endpoint" panel filled: External endpoint, AFDEndpoint, Enable Endpoint unchecked, the FQDN, Weight 1. The Add click is not captured. |
| 44-45 | 2:09-2:12 | EU01 Overview, then Endpoints with the toast for 'tm-profile-EU' and the row `AFDEndpoint  Disabled  Disabled  External endpoint  1`. |
| 46-52 | 2:15-2:32 | `tm-profile-NA`: Endpoints, the panel empty with Enable Endpoint still checked (48), then filled with it unchecked (49-50), Add (50), toast "Saving Traffic Manager profile" (51, 2:28), then "Saved ... 'tm-profile-NA'" with the second row (52). |
| 53-55 | 2:34-2:39 | Traffic managers list (53-54), then `tm-profile-AU \| Endpoints` (55). |
| 56 | 2:42 | FRONTDOOR-A Front Door manager (find-on-page again). |
| 57-64 | 2:45-3:01 | `FRONTDOOR-A \| Logs`: a 10-line KQL editor with the query history below (58-60): lines 1-7 the old query (summarize by `originName_s`, `bin 5m`), a blank line 8, lines 9-10 a pasted `summarize ... requestUri_s ... 1m` and `render timechart`. By frame 62 (2:55) the old lines 6-7 are deleted: 7 lines. Run at frame 64 (3:01, editor greyed). |
| 65-70 | 3:04-3:18 | The time chart (y-axis to 30,000; legend of `*.manage.microsoft.com` URIs; footer `3s 28ms`, `1000 records`). |
| 71 | 3:21 | Line 5 (the i.manage / r.manage / a.manage filter) commented out with `//`; lines 5-7 selected. |
| 72 | 3:24 | `Kusto.Explorer [v1.0.3.1566]`, tab `XSU-RUALSV2.kql`, line 6 `\| where requestUri_s contains "ServiceA/Certificate"` selected. |
| 73-79 | 3:27-3:44 | Back in the Logs blade: the 8-line query with the new line 5, "Running your query..." (74-75), then the new chart (y-axis to 1,250; legend of `ServiceA/.../Certificate/ServiceAddresses` URIs; footer `3s 153ms`, `277 records`). |

Scope: the whole video, 0:00 to 3:44 (224 s, 80 frames). The questions are asked in order, in one conversation.

Types: Q1, Q2, Q3, Q14 open-ended (the claims a good answer must contain, and must not make); Q4, Q5, Q7, Q9, Q10, Q15
exact values; Q6, Q8, Q11 what happened; Q12, Q13 negatives (the honest answer is "no"); Q16 the honesty check (what
the record cannot say). Q12, Q13 and Q16 are the **negative or honesty checks** and are secondary, as in the other
sets: the positive questions are the score, the negatives are reported beside it.

How an answer is scored: each rubric line is a statement about the answer. `M` lines must be true of the answer; `X`
lines must not be. A separate model call, which does not know which run produced the answer, decides each line, and
code derives the label: *correct* when every `M` line holds and no `X` line does, *wrong* when any `X` line holds or
no `M` line holds, *partial* otherwise. Only a line that says "contains the exact string" is about exact text; every
other line is judged on meaning, and "gives a time between A and B" is also satisfied by a frame in that range.

## Positive questions

### Q1 (positive, open-ended overview)
- **Follows:** nothing; the opening question.
- **Question:** What is this video about, overall? Give me the one-paragraph version.
- **Reference answer:** A 3 minute 44 second screen recording of an Azure portal session in Microsoft Edge on Windows
  11. The person adds the Front Door endpoint `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` (the hostname highlighted
  on the `FRONTDOOR-A | Front Door manager` page at 0:00) as an external endpoint named `AFDEndpoint`, weight 1, disabled,
  to three Traffic Manager profiles in turn: `tm-profile-ap` (saved at about 1:04), `tm-profile-EU`
  (about 2:12) and `tm-profile-NA` (about 2:32), each confirmed by a "Saved Traffic Manager profile changes"
  toast; a Microsoft "Pick an account" prompt appears once at 1:37. From 2:45 the person opens the `FRONTDOOR-A | Logs`
  blade, edits and runs a KQL query over `AzureDiagnostics` / `FrontDoorAccessLog` (a time chart, 1000 records at
  3:18), comments out one filter, copies a `ServiceA/Certificate` filter from a Kusto.Explorer
  window (3:24) and re-runs (277 records at 3:44).
- **Rubric:**
  - M1: says the session is in the Azure portal and endpoints were added to Traffic Manager profiles (or an endpoint
    named AFDEndpoint / a Front Door hostname was added).
  - M2: says a log query (KQL, Logs blade, Log Analytics or Kusto) was run near the end.
  - M3: mentions three profiles, or names at least two of tm-profile-ap, tm-profile-EU and
    tm-profile-NA.
  - X1: says an endpoint or profile was deleted, or that a new profile was created.
  - X2: says the video is about something other than Azure (for example a Kubernetes or AKS tutorial).
- **Evidence:** frames 0, 22, 45, 52, 64, 79; the table above.

### Q2 (positive, open-ended sequence)
- **Follows:** Q1.
- **Question:** Walk me through what the person did, step by step, with the time each step started.
- **Reference answer:** 0:00 on `FRONTDOOR-A | Front Door manager` with the hostname `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`
  found on the page (0:00-0:09). 0:12-0:26 the portal reloads and shows `AU01-tm-profile | Endpoints`, which
  already lists AFDEndpoint. 0:29 back to the Front Door manager page. 0:35 opens `tm-profile-ap` (Overview, then
  Endpoints at 0:38), 0:44 opens "Add endpoint", types the name AFDEndpoint (0:48), glances at the AU01 profile at 0:50,
  sets Type to External endpoint, pastes the FQDN and Weight 1 (0:54-1:00), clicks Add (1:00); 1:04 the toast "Saved
  Traffic Manager profile changes" for ap01. 1:17 Azure Home, 1:19-1:34 the `Network foundation | Traffic managers`
  list; 1:37 a "Pick an account" sign-in prompt; 1:40-1:46 `tm-profile-NA` Overview and Endpoints; 1:49 the
  Front Door manager page again. 1:52 `tm-profile-EU` Endpoints, 1:58-2:06 its Add endpoint form filled the
  same way; 2:09 Overview; 2:12 the toast for EU01. 2:15 `tm-profile-NA` Endpoints, 2:18-2:27 the form,
  2:27 Add, 2:28 "Saving", 2:32 "Saved" for NA01. 2:34 the Traffic managers list, 2:38 the AU01 Endpoints page, 2:42
  the Front Door manager page. 2:45 the `FRONTDOOR-A | Logs` blade: a KQL query is edited (two old lines deleted by 2:55),
  run at 3:01; 3:04-3:18 the time chart (1000 records). 3:21 the i.manage / r.manage / a.manage line is commented out;
  3:24 Kusto.Explorer, a line `| where requestUri_s contains "ServiceA/Certificate"` selected;
  3:27 the line is in the portal query; 3:30 "Running your query..."; 3:36-3:44 the new chart (277 records).
- **Rubric:**
  - M1: puts the ap01 addition before the EU01 addition and the EU01 addition before the NA01 addition (or gives them
    times in increasing order about 1:04, 2:12, 2:32).
  - M2: places the log query after all three additions (a time after 2:40, or last).
  - M3: gives a time for the first addition's save between 0:58 and 1:10 (or frame 21-23).
  - M4: mentions the sign-in / "Pick an account" prompt between the first and second additions (a time between 1:30 and
    1:45).
  - X1: puts the query before any endpoint addition.
  - X2: says the endpoint was added to a profile other than tm-profile-ap, tm-profile-EU and
    tm-profile-NA (AU01 is looked at, never edited).
- **Evidence:** the frame table; frames 21-22, 33, 45, 50-52, 64, 71-73, 79.

### Q3 (positive, first thing on screen)
- **Follows:** Q2.
- **Question:** What was the very first thing on screen, and what was the person doing there?
- **Reference answer:** Frame 0 (0:00): Microsoft Edge on a Windows 11 desktop, the Azure portal page `FRONTDOOR-A | Front
  Door manager` (a Front Door profile), with two endpoint cards: `FRONTDOOR-A-drgzexethuh8cpen.b02.azurefd.net` and
  `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`. The second hostname is highlighted orange by the browser's
  find-on-page bar, which reads `f9.b02.azurefd.net 1/1`: the person had searched the page for the hostname (so as to
  select and copy it). This stays until 0:09; the page reloads at 0:12.
- **Rubric:**
  - M1: names the FRONTDOOR-A Front Door manager page (or a Front Door profile page) in the Azure portal.
  - M2: says a hostname ending in `azurefd.net` was highlighted, selected or found on the page (or that the find bar
    was open).
  - X1: names a Traffic Manager profile, the Logs blade or the sign-in dialog as the first thing on screen.
- **Evidence:** frame 0, the highlighted card at [399, 811, 666, 832] (box `0:b116`) and the find bar at the top
  right.

### Q4 (positive, exact values)
- **Follows:** Q1/Q2, which say an endpoint was added.
- **Question:** You said an endpoint was added. What exactly was entered in that form: every field and its value?
- **Reference answer:** The "Add endpoint" panel of a Traffic Manager profile, filled the same way three times (frames
  19-21 for ap01, 41-43 for EU01, 49-50 for NA01): Type `External endpoint` (changed from the default `Azure
  endpoint`); Name `AFDEndpoint`; Enable Endpoint unchecked (the checkbox is ticked by default, frame 48, and is
  cleared before Add, so the endpoint is created disabled); Fully-qualified domain name (FQDN) or IP address
  `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` (the field shows it truncated, `FRONTDOOR-A-cqhefshkhrgmgqf9....`; the
  full string is the one on the Front Door page); Weight `1`; Custom Header settings left empty. Then Add.
- **Rubric:**
  - M1: gives the name AFDEndpoint.
  - M2: gives the type External endpoint.
  - M3: gives the weight 1.
  - M4: gives the hostname `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` (a truncated form with `FRONTDOOR-A-cqhefshkhrgmgqf9` also holds).
  - M5: says the Enable Endpoint checkbox was unchecked (or that the endpoint was added disabled).
  - X1: gives a weight other than 1, or the type Azure endpoint as what was submitted.
- **Evidence:** frames 21, 43 and 50 panel crops (Type, Name, Enable Endpoint unchecked, FQDN, Weight 1); frame 48 for
  the ticked default; frame 22 row `AFDEndpoint  Disabled`.

### Q5 (positive, order and times)
- **Follows:** Q4.
- **Question:** Which profiles got the new endpoint, in what order, and at what times?
- **Reference answer:** Three profiles, in this order: `tm-profile-ap` (form filled 0:54-1:00, Add at about
  1:00, saved toast at about 1:04, frame 22); `tm-profile-EU` (form filled 1:58-2:06, the Add click not
  captured, saved toast at about 2:12, frame 45); `tm-profile-NA` (form filled 2:18-2:27, Add at about 2:27,
  "Saving" at 2:28, saved toast at about 2:32, frame 52). `tm-profile-AU` already had the endpoint (weight
  50, enabled) and was only looked at (0:15-0:26, 0:50, 2:38).
- **Rubric:**
  - M1: names tm-profile-ap as the first, with a time between 0:55 and 1:10.
  - M2: names tm-profile-EU as the second, with a time between 1:55 and 2:15.
  - M3: names tm-profile-NA as the third, with a time between 2:15 and 2:35.
  - X1: says AU01 (any AU01 profile) got the new endpoint during the session.
- **Evidence:** frames 22, 45, 52 (toasts naming the profile); frames 17 and 55 (AU01 already has it).

### Q6 (positive, evidence of success)
- **Follows:** Q5.
- **Question:** Did each of those additions succeed? How do you know?
- **Reference answer:** Yes, all three. For each, a green-tick toast "Saved Traffic Manager profile changes /
  Successfully saved configuration changes to Traffic Manager profile '<name>'" appears (ap01 at frame 22, 1:04; EU01 at
  frame 45, 2:12; NA01 at frame 52, 2:32, after a "Saving Traffic Manager profile" toast at frame 51), and the
  Endpoints table grows from one row to two, the new row reading `AFDEndpoint | Disabled | Disabled | External
  endpoint | 1` (frames 22, 45, 52). No error toast or validation message appears. The endpoint is saved disabled by
  design (Enable Endpoint unchecked), which is not a failure.
- **Rubric:**
  - M1: says all three succeeded.
  - M2: cites the "Saved Traffic Manager profile changes" toast (or the success notification) as the evidence.
  - M3: cites the new AFDEndpoint row in the endpoints table (or the table going from one row to two).
  - X1: says one of the additions failed or is unconfirmed.
- **Evidence:** frames 22, 45, 51, 52 toasts and tables.

### Q7 (positive, provenance of a value)
- **Follows:** Q4.
- **Question:** Where did the hostname that was pasted into the form come from? Show me where it first appears.
- **Reference answer:** From the `FRONTDOOR-A | Front Door manager` page: it is the hostname of the second endpoint card,
  `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`, drawn with an orange find-on-page highlight from the very first frame
  (frame 0, 0:00; the find bar reads `f9.b02.azurefd.net 1/1`). The person returns to this page before each addition
  (0:29, 1:49, 2:42), consistent with copying it each time; the copy itself is not visible.
- **Rubric:**
  - M1: says the hostname comes from the FRONTDOOR-A Front Door manager page (or a Front Door endpoint card).
  - M2: says it first appears at the start of the video (a time between 0:00 and 0:10, or frame 0).
  - M3: contains the exact string `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`.
  - X1: says it first appears in the Add endpoint form, the Logs blade or Kusto.Explorer.
- **Evidence:** frame 0 box `0:b116`; frames 11, 37, 56.

### Q8 (positive, event and choice)
- **Follows:** Q2.
- **Question:** Was there any sign-in or account prompt during the session? What was chosen?
- **Reference answer:** Yes, once: at frame 33 (about 1:37, between 1:34 and 1:37), on `login.microsoftonline.com`, a
  Microsoft "Pick an account / to continue to Microsoft Azure" dialog with two accounts, both the account holder:
  `user@example.com` (first, highlighted with a focus border) and `user@example.com` (second),
  plus "Use another account". It comes right after the Traffic managers list (frame 32) and is gone by frame 34 (1:40,
  a portal loading splash), followed by the NA01 profile at 1:43. The click itself is not captured: the record shows
  the first account highlighted and the session continuing in the same portal account (`user@example.com` in the
  header), so the first account is the likely choice, but no frame shows it being chosen.
- **Rubric:**
  - M1: says yes, a "Pick an account" (Microsoft sign-in) prompt appeared, with a time between 1:30 and 1:42 or frame 33.
  - M2: names the account user@example.com (or "the first account") as the highlighted or likely choice.
  - M3: says the click or the choice itself is not captured (or hedges that it is inferred).
  - X1: says user@example.com or "Use another account" was chosen.
  - X2: says no sign-in prompt appeared.
- **Evidence:** frame 33 crop; frames 32, 34, 35.

### Q9 (positive, exact query text)
- **Follows:** Q1/Q2, which mention the query.
- **Question:** Near the end the person ran a query. What was the exact query text, line by line, and what did it return?
- **Reference answer:** Two runs. The first run (Run at frame 64, 3:01; chart from 3:04) of the 7-line query:
  `AzureDiagnostics` / `| where TimeGenerated > ago(2h)` / `| where Category == "FrontDoorAccessLog"` / `| where
  requestUri_s !contains "enrollment"` / `| where requestUri_s contains "i.manage"  or requestUri_s contains
  "r.manage"  or requestUri_s contains "a.manage"` / `| summarize count() by strcat(httpStatusCode_d, requestUri_s),
  bin(TimeGenerated, 1m)` / `| render timechart`. It returned a time chart (Chart tab) with series such as
  `200.0https://a.manage.microsoft.com:443/devicegatewayproxy/AOSPHandler.ashx`, y-axis to 30,000, footer `3s 28ms`
  and `1000 records` (frame 70, 3:18). The second run (3:30-3:44) of the 8-line query, with a new line 5 `| where
  requestUri_s contains "ServiceA/Certificate"` and line 6 commented out (`//| where requestUri_s
  contains "i.manage" ...`), returned a chart with series like
  `200.0https://agents.manage.microsoft.com:443/ServiceA/ServiceA/Certificate/ServiceAddresses`
  (also 307, 400, 499, 500), y-axis to 1,250, footer `3s 153ms` and `277 records` (frame 79, 3:44).
- **Rubric:**
  - M1: contains the exact string `FrontDoorAccessLog`.
  - M2: gives the enrollment exclusion line (`requestUri_s !contains "enrollment"`).
  - M3: gives the summarize line with `strcat(httpStatusCode_d, requestUri_s)` and `bin(TimeGenerated, 1m)`.
  - M4: says it returned a time chart (render timechart) and gives a record count of 1000 or 277.
  - M5: gives the source table AzureDiagnostics and the `ago(2h)` window.
  - X1: gives `originName_s` or `bin(TimeGenerated, 5m)` as part of the query that was run.
  - X2: says the query returned no results or an error.
- **Evidence:** frames 62, 64, 70 (7 lines, footer), 73, 79 (8 lines, footer). Line crops at 2x checked by eye.

### Q10 (positive, what changed)
- **Follows:** Q9.
- **Question:** Did the query change while they worked on it? What changed?
- **Reference answer:** Yes, in three steps. (1) Before the first run (frames 58-62, 2:47-2:55): the editor held ten
  lines, the old query whose lines 6-7 were `| summarize count() by strcat(httpStatusCode_d, originName_s),
  bin(TimeGenerated, 5m)` and `| render timechart`, a blank line, and two pasted lines with `requestUri_s` and `1m`;
  the old lines 6-7 were deleted, leaving the 7-line query that was run at 3:01. (2) At frame 71 (3:21) line 5, the
  `i.manage` / `r.manage` / `a.manage` filter, was commented out with `//`. (3) At frame 73 (3:27), after a visit to
  Kusto.Explorer (3:24), a new line 5 `| where requestUri_s contains "ServiceA/Certificate"` was
  inserted after the enrollment line, making 8 lines; the re-run returned 277 records instead of 1000.
- **Rubric:**
  - M1: says the i.manage / r.manage / a.manage line was commented out (or removed).
  - M2: says a `ServiceA/Certificate` filter line was added.
  - M3: says the record count went from 1000 to 277 (or that the result changed after the edit).
  - X1: says the query did not change.
  - X2: says the summarize line or the render line was changed between the first and second run.
- **Evidence:** frames 58, 62 (deletion), 70, 71 (comment), 72, 73 (new line), 79 (footer).

### Q11 (positive, other applications)
- **Follows:** Q10, which mentions Kusto.Explorer.
- **Question:** Did the person use any application other than the browser? When, and for what?
- **Reference answer:** Yes: Kusto.Explorer (title bar `Kusto.Explorer [v1.0.3.1566]`), on screen at frame 72 only
  (about 3:24, between 3:21 and 3:24), with many query tabs and the tab `XSU-RUALSV2.kql` active, connected to
  `cluster('ade.loganalytics.io').database('intuneprod')`. Line 6 of that tab, `| where requestUri_s contains
  "ServiceA/Certificate"`, is selected; the same line appears in the portal query at 3:27, so the
  visit was to copy that filter. Everything else is Microsoft Edge (the Azure portal and one login.microsoftonline.com
  page) on the Windows desktop.
- **Rubric:**
  - M1: names Kusto.Explorer (or a Kusto / KQL desktop client) as the other application.
  - M2: gives a time between 3:18 and 3:28, or frame 72.
  - M3: says it was used to copy or look up the `ServiceA/Certificate` filter line (or a query line)
    that then went into the portal query.
  - X1: says no application other than the browser was used.
  - X2: names a terminal, PowerShell, VS Code or another application as used.
- **Evidence:** frame 72 crop (title bar, tab, selected line); frame 73.

### Q14 (positive, duration and time spent)
- **Follows:** Q2.
- **Question:** How long did the whole task take, and where did the person spend the most time?
- **Reference answer:** The recording is 3 minutes 44 seconds (223.97 s, 80 frames, last frame at 3:43.9). About 2:45
  of it (0:00-2:44) is in Traffic Manager: the three endpoint additions with their navigation and the sign-in prompt,
  about 55 s each for ap01 (0:35-1:14 including the form), EU01 (1:52-2:12) and NA01 (2:15-2:32); the last minute
  (2:45-3:44) is the Logs blade query, two runs and the Kusto.Explorer visit. The longest single stretch on one page is
  the Logs blade (about 60 s, frames 57-79 minus frame 72); the longest form is the first one, ap01 (0:44-1:04, about
  20 s, including the glance at AU01).
- **Rubric:**
  - M1: gives a total length between 3:35 and 3:50 (or 220-228 seconds).
  - M2: says most of the time was spent adding endpoints to the Traffic Manager profiles (or on the portal's Traffic
    Manager pages), or that the Logs / query part took about the last minute.
  - X1: gives a total length under 3:00 or over 4:30.
- **Evidence:** `frames.jsonl` (t_settled of frame 79 = 223.9 s; `video.json` duration 223.97 s); the frame table.

### Q15 (positive, reproduction values)
- **Follows:** everything before it.
- **Question:** If I wanted to reproduce what the person did, list every exact value I would need: names, hostnames,
  weights, types, query text.
- **Reference answer:** Profiles: `tm-profile-ap`, `tm-profile-EU`, `tm-profile-NA` (Front
  Door profile `FRONTDOOR-A`, resource group `PE-XSUCP-AFD.ResourceGroup`). Endpoint: Type `External endpoint`, Name
  `AFDEndpoint`, Enable Endpoint off, FQDN `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`, Weight `1`, no custom
  headers. Query (final, 8 lines): `AzureDiagnostics` / `| where TimeGenerated > ago(2h)` / `| where Category ==
  "FrontDoorAccessLog"` / `| where requestUri_s !contains "enrollment"` / `| where requestUri_s contains
  "ServiceA/Certificate"` / `//| where requestUri_s contains "i.manage"  or requestUri_s contains
  "r.manage"  or requestUri_s contains "a.manage"` / `| summarize count() by strcat(httpStatusCode_d, requestUri_s),
  bin(TimeGenerated, 1m)` / `| render timechart`; run in the `FRONTDOOR-A | Logs` blade, time range "Set in query", show
  1000 results.
- **Rubric:**
  - M1: contains the exact string `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`.
  - M2: names all three profiles tm-profile-ap, tm-profile-EU and tm-profile-NA.
  - M3: gives the name AFDEndpoint, the type External endpoint and the weight 1.
  - M4: gives the query text including `FrontDoorAccessLog`, `!contains "enrollment"`,
    `ServiceA/Certificate` and the summarize line.
  - X1: gives a weight other than 1, or lists AU01 as a profile to add the endpoint to.
- **Evidence:** as Q4, Q5 and Q9.

## Negative and honesty questions

### Q12 (negative, nothing failed)
- **Follows:** Q6.
- **Question:** Did anything go wrong, fail, or get deleted during the session?
- **Reference answer:** No failure and no deletion of a resource. Every save shows a green success toast; the
  command-bar Delete is greyed out on every Endpoints page and no confirmation dialog appears. The only things
  "deleted" are text: two lines of KQL removed from the editor between 2:53 and 2:55 (frames 61-62), and one line
  commented out at 3:21. The sign-in prompt at 1:37 is not an error, and the new endpoints show "Disabled" because
  they were added with Enable Endpoint unchecked, not because anything failed.
- **Rubric:**
  - M1: says nothing failed and no resource (endpoint, profile) was deleted.
  - X1: says an endpoint, profile or other resource was deleted.
  - X2: says one of the endpoint additions failed or errored.
- **Evidence:** frames 22, 45, 52 (success toasts, tables grow); frame 36 (Delete greyed); frames 61-62.

### Q13 (negative, no profile created)
- **Follows:** Q5.
- **Question:** Did the person create any new profile, or only change existing ones?
- **Reference answer:** Only existing ones. No "Create Traffic Manager profile" or "Create" form appears; the three
  profiles edited (tm-profile-ap, tm-profile-EU, tm-profile-NA) are all in the Traffic
  managers list at 1:19-1:34 (12 profiles) before they are opened, and each already had one endpoint (ap.endpoint,
  eu.endpoint, na.endpoint) before the addition. The only thing created is one endpoint per profile.
- **Rubric:**
  - M1: says no new profile was created; only existing profiles were changed.
  - X1: says a new profile (or a new Front Door) was created.
- **Evidence:** frames 29-32 (the list); frames 13, 38, 46 (one row before), 22, 45, 52 (two after).

### Q16 (negative, honesty check)
- **Follows:** everything before it.
- **Question:** Is there anything about this session that the record cannot tell me?
- **Reference answer:** Yes. (1) There is no audio: nothing said or narrated is in the index. (2) The record is 80
  captures over 224 s, 62 of them forced 3-second snapshots, so nothing between captures is known: the Add click for
  EU01, the account click on the sign-in dialog, the copy of the hostname and of the Kusto.Explorer line, and the
  keystrokes of the edits are inferred from before-and-after states, not seen; times are good to about 3 s. (3) Intent
  and reasons are unknowable: why the endpoint is added disabled with weight 1, why AU01 was looked at, what the
  person concluded from the charts. (4) What is off-screen or truncated (the FQDN field shows the hostname cut off;
  the full string comes from the Front Door page), and anything after 3:44.
- **Rubric:**
  - M1: says the record has no audio / no narration (or nothing about what was said).
  - M2: says there are gaps between captures (some clicks or keystrokes are not seen, only inferred from before-and-after
    states) or that times are approximate to a few seconds.
  - M3: says the person's intent or reasons cannot be known from the record.
  - X1: claims the record is complete or that everything the person did can be recovered from it.
- **Evidence:** `frames.jsonl` (62 of 80 `settled: false`); the pipeline reads no audio; frames 43-45 (EU01 Add not
  captured), 33-34 (sign-in click not captured).
