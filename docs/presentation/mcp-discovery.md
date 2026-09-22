# The MCP server, driven by Claude Code: a discovery conversation about the hold-out video

Status: captured 2026-09-21 on branch `holdout-discovery`, against the rubric of the draft
`docs/ground-truth/holdout-discovery.md` (written from the frames, for the owner to correct). **What was captured is
not the sixteen-turn conversation that was planned**: it is one turn of Claude Code that received all sixteen
questions at once, because of a driver bug explained under "What did not work". The answer is still a fair sample of
what a person who has never seen the video gets from the index through the MCP server, so it is rendered and judged
here question by question; the multi-turn run is left for a fixed driver (the fix is one `< /dev/null`).

The premise: a person who has never seen the hold-out video (`runs/v2/grouponly-100`: the owner's default group-only
overlay index of the 224 s Azure-portal session, 80 frames) and does not have the file asks the sixteen questions of
that set in order, each follow-up seeing the earlier answers. The host is Claude Code 2.1.278 non-interactively,
model `claude-sonnet-5`, with the scry skill appended to the system prompt plus one paragraph of context (the user has
never seen the video, every question is about `v2/grouponly-100`, answer only the question asked in at most 4 tool
calls); session `00000000-0000-0000-0000-000000000000`:

```sh
claude -p "<question>" --session-id 00000000-0000-0000-0000-000000000000 \
  --mcp-config .mcp.json --strict-mcp-config --allowedTools "mcp__scry__*" --permission-mode dontAsk \
  --append-system-prompt "$(cat skills/scry/SKILL.md)<context paragraph>" --output-format stream-json --verbose \
  --max-budget-usd 0.9 --model sonnet
```

Nothing below is edited: the section is rendered from the host's JSON stream (tool results trimmed to 1,200
characters), the answer exactly as given. 8 turns, 6 scry tool calls, 171 s, $0.44 for the whole turn. The host
model did the reasoning; the server only served the index. It never opened a frame image (`get_frame` was called once
with `image: false`), so everything it says rests on the summary, one lifetime search, three transition windows and
one frame record.

## Scores

The blind judge (`scry.evaluation.judge`, judge-v1, claude-opus-5 at low effort, $0.40 for 16 calls) scored the one
answer against each question's rubric lines. Labels: {'correct': 9, 'partial': 7}. Positive questions (13): mean
0.77; negatives and honesty checks (Q12, Q13, Q16): mean 0.83.

| Q | judge | rubric lines | by eye, where it differs or needs a note |
|---|---|---|---|
| Q1 | correct | M1 yes, M2 yes, M3 yes, X1 no, X2 no | agree |
| Q2 | partial | M1 yes, M2 yes, M3 yes, M4 no, X1 no, X2 no | agree: partial. Order and times right; the sign-in prompt is placed in the EU01 section without its time. |
| Q3 | correct | M1 yes, M2 yes, X1 no | agree |
| Q4 | partial | M1 yes, M2 yes, M3 yes, M4 yes, M5 no, X1 no | agree: partial. It says the Enable Endpoint checkbox was not seen touched; frames 21, 43 and 50 show it unchecked and the new rows read Disabled. It never opened a form frame. |
| Q5 | correct | M1 yes, M2 yes, M3 yes, X1 no | agree |
| Q6 | correct | M1 yes, M2 yes, M3 yes, X1 no | agree |
| Q7 | correct | M1 yes, M2 yes, M3 yes, X1 no | agree |
| Q8 | partial | M1 yes, M2 yes, M3 no, X1 no, X2 no | disagree: wrong. It asserts "At T34 the person clicks the first the account holder tile"; no frame shows the click (frame 34 is the loading splash). The rubric's M3 (says the click is not captured) is false and the claim is unsupported. |
| Q9 | correct | M1 yes, M2 yes, M3 yes, M4 yes, M5 yes, X1 no, X2 no | agree |
| Q10 | partial | M1 yes, M2 no, M3 yes, X1 no, X2 no | agree: partial. It calls the ServiceA/Certificate line "a stray reading" from Kusto.Explorer; it is line 5 of the portal query on frames 73 to 79. |
| Q11 | partial | M1 yes, M2 yes, M3 no, X1 no, X2 no | agree: partial. Kusto.Explorer at the right time, but the reason (copying that filter line) is missed, consistent with the Q10 miss. |
| Q14 | correct | M1 yes, M2 yes, X1 no | agree |
| Q15 | partial | M1 yes, M2 yes, M3 yes, M4 no, X1 no | agree: partial. The reproduction list omits the ServiceA/Certificate line and says nothing about Enable Endpoint off. |
| Q12 | correct | M1 yes, X1 no, X2 no | agree |
| Q13 | correct | M1 yes, X1 no | agree |
| Q16 | partial | M1 no, M2 yes, M3 no, X1 no | agree: partial. Names the frame gaps well; says nothing about audio or intent. |

Three answers worth showing: Q9 (both runs of the KQL query line by line, with `3s 28ms` / `1000 records` and
`3s 153ms` / `277 records`, from the index alone); Q6 (all three saves confirmed from the toasts and the table growing
to two rows, and the honest note that the EU01 Add click "falls in a gap between captured frames"); Q7 (the hostname
"already present, highlighted by an in-progress find-on-page search, in the very first frame", with the lifetime ids).

Claims the record does not support: "At T34 the person clicks the first the account holder tile" (Q8; frame 34 is a loading
splash, the click is between captures); "switches to the FRONTDOOR-A Front Door manager to confirm the hostname exists
there" (Q1; intent, and the person is more likely copying it, which is also not visible); the
`ServiceA/Certificate` line dismissed as "a stray reading possibly carried over from the
Kusto.Explorer window" (Q9, Q10, Q16; it is line 5 of the portal query on frames 73 to 79, and the whole point of the
Kusto.Explorer visit). Unverified by eye: the window "resize/restore" at 0:00 and the "Network" tab closed at about
2:35 (both from transition interpretations; not checked against the frames in the time available).

## What did not work

1. **The driver fed all sixteen questions to the first `claude -p` call.** The loop read `questions.txt` on stdin and
   `claude -p` reads its stdin as extra input, so the first invocation received Q1 as its argument and Q2 to Q16 on
   stdin, answered all of them in one turn, and the loop found the file consumed (the two `--resume` calls that
   followed took 11 and 12 s and are not shown: they got an empty prompt). The fix is `< /dev/null` on the claude
   command; it is in the scratch driver but there was no budget left to re-run.
2. **Cost.** The first attempt on the default model (Fable) cost $1.29 for that same all-questions turn and hit an
   $0.80 per-call budget; a second attempt with `--max-budget-usd 0.4` on Sonnet was cut off before answering (16
   turns of evidence gathering, no answer). About $4.0 went on those two attempts and a stray driver that kept
   running after the first was thought killed; the captured turn cost $0.44 and the judge $0.43. Total about $4.9
   of the $8 cap, with the multi-turn run still to do (estimate $4 to $5 on Sonnet, more with the default model).
3. **The 4-tool-call instruction was not followed** (6 scry calls), and the model never looked at a frame image,
   which is where the Enable Endpoint checkbox and the new query line would have been settled.

## The conversation

## The single turn (all sixteen questions, in order)

**Prompt:** Q1 as the argument, Q2 to Q16 arriving on stdin (see above).

### Tool call 1: `summary`

```json
{"video": "v2/grouponly-100"}
```

Result (trimmed):

```
{
  "video": "v2/grouponly-100",
  "video_id": "grouponly-100",
  "duration_s": 223.966633,
  "summary": {
    "id": "V",
    "label": "Add AFDEndpoint to Traffic Manager profiles and check Front Door logs",
    "t": [
      0.03333333333333333,
      223.93333333333334
    ],
    "frames": [
      0,
      79
    ],
    "children": [
      "C1",
      "C7"
    ],
    "description": "Starting from the Front Door manager page, move through the Azure portal to a traffic manager resource and open \"AU01-tm-profile\" and its \"Endpoints\" blade, which lists au.endpoint and AFDEndpoint [C1]. On the tm-profile-ap profile's Endpoints blade, click \"+ Add\", set Type to \"External endpoint\", enter the FQDN and click \"Add\", producing the toast \"Saved Traffic Manager profile changes\" and a second endpoint row [C2]. Next reach the Traffic Manager profiles list via the \"Traffic Manager profiles\" tile on Home, sign in with the the account holder account to land on tm-profile-EU, open \"Endpoints\" and fill an \"Add endpoint\" panel with Type \"External endpoint\", the prefilled FQDN \"FRONTDOOR-A-cqhefshkhrgmgqf9....\" and the Name \"AFDEndpoint\", leaving the form open and
... (26225 more characters)
```

### Tool call 2: `search`

```json
{"video": "v2/grouponly-100", "query": "\"FRONTDOOR-A-cqhefshkhrgmgqf9\"", "level": "lifetime"}
```

Result (trimmed):

```
{
  "hits": [
    {
      "node_id": "grouponly-100:L1430",
      "level": "lifetime",
      "item_id": "L1430",
      "frames": [
        39,
        40
      ],
      "t": [
        115.36666666666666,
        118.36666666666666
      ],
      "score": 0.01639,
      "text": "FRONTDOOR-A-cqhefshkhrgmgqf9....\nFully-qualified domain name (FQDN) or IP address * FRONTDOOR-A-cqhefshkhrgmgqf9....",
      "sightings": 2,
      "unstable": false,
      "seen_once": false,
      "agree": null,
      "readers": {
        "ocr": "FRONTDOOR-A-cqhefshkhrgmgqf9....",
        "vlm": null
      }
    },
    {
      "node_id": "grouponly-100:L1477",
      "level": "lifetime",
      "item_id": "L1477",
      "frames": [
        42,
        43
      ],
      "t": [
        123.5,
        126.13333333333334
      ],
      "score": 0.01613,
      "text": "FRONTDOOR-A-cqhefshkhrgmgqf9....\nFully-qualified domain name (FQDN) or IP address * FRONTDOOR-A-cqhefshkhrgmgqf9....",
      "sightings": 2,
      "unstable": false,
      "seen_once": false,
      "agree": null,
      "readers": {
        "ocr": "FRONTDOOR-A-cqhefshkhrgmgqf9....",
        "vlm": null
      }
    },
    {
      "node_id": "groupon
... (3495 more characters)
```

### Tool call 3: `get_transitions`

```json
{"video": "v2/grouponly-100", "t_a": 94, "t_b": 127}
```

Result (trimmed):

```
{
  "transitions": [
    {
      "id": "T32",
      "node_id": "grouponly-100:T32",
      "frames": [
        31,
        32
      ],
      "t": [
        91.16666666666667,
        94.16666666666667
      ],
      "kind": "unsettled",
      "summary": "T32 [f31→f32, 91.2–94.2s] changed \"Sign in te X\"; changed \"Sign in t X\"; changed \"AFD mTL ×\"; +9 more text changes; appeared 3; removed 3; moved 3; undoes T31",
      "action": "The user moved the mouse from the NA01-tm-profile row up to the first row's link (ap-tm-profile), hovering it.",
      "result": "Row highlighting moved to the first row, its link underlined and the status-bar URL preview updated; tab titles shifted/narrowed slightly as tabs resized.",
      "entered_text": null,
      "submitted": "no",
      "confidence": 0.8,
      "undoes": "T31"
    },
    {
      "id": "T33",
      "node_id": "grouponly-100:T33",
      "frames": [
        32,
        33
      ],
      "t": [
        94.16666666666667,
        97.2
      ],
      "kind": "unsettled",
      "summary": "T33 [f32→f33, 94.2–97.2s] changed \"portal.az ×\"; changed \"Sign in t×\"; changed \"Network X\"; +12 more text changes; appeared 4; removed 110
... (10752 more characters)
```

### Tool call 4: `get_transitions`

```json
{"video": "v2/grouponly-100", "t_a": 200, "t_b": 223}
```

Result (trimmed):

```
{
  "transitions": [
    {
      "id": "T71",
      "node_id": "grouponly-100:T71",
      "frames": [
        70,
        71
      ],
      "t": [
        197.83333333333334,
        200.83333333333334
      ],
      "kind": "unsettled",
      "summary": "T71 [f70→f71, 197.8–200.8s] changed \"where requestUri_s !contains \"enrollment\"\"; changed \"//| where requestUri_s contains \"i.manage\"·or·requestUri_s·contains·\"r.manage\"·…\"; changed \"summarize·count()·by· strcat(httpStatusCode_d, requestUri_s),·bin(TimeGenerated…\"; +1 more text changes; appeared 6; removed 1; undoes T70",
      "action": "The user hovered the mouse over a data point on the chart (near 5:27 PM); the query lines 5–7 also appear selected/commented in the editor.",
      "result": "A chart tooltip appeared showing \"TimeGenerated [UTC]:9/17/2026, 5:27:00.000 PM\", \"count_: 1492\" and \"Column1: 200.0https://r.manage.microsoft.com:443/devicegatewayproxy/cimhandler.ashx\"; in the editor the line now reads \"//| where requestUri_s contains \"i.manage\" ...\" and lines 5-7 show blue selection highlight.",
      "entered_text": null,
      "submitted": "no",
      "confidence": 0.65,
      "undoes": "T70"
    }
... (7485 more characters)
```

### Tool call 5: `get_transitions`

```json
{"video": "v2/grouponly-100", "t_a": 178, "t_b": 201}
```

Result (trimmed):

```
{
  "transitions": [
    {
      "id": "T64",
      "node_id": "grouponly-100:T64",
      "frames": [
        63,
        64
      ],
      "t": [
        178.1,
        181.1
      ],
      "kind": "unsettled",
      "summary": "T64 [f63→f64, 178.1–181.1s] appended \"New Query 1* ...\"; reread \"Time range: Set in query\"; changed \"where requestUri_s contains \"i.manage\" or requestUri_s contains \"r.manage\" or r…\"; +2 more text changes; appeared 6; removed 23; undoes T63",
      "action": "The user clicked the Run button (or pressed Shift+Enter) to execute the KQL query.",
      "result": "The query history panel was replaced by the results pane showing Results/Chart tabs, a spinner with \"Running your query..\" and timer \"00:01\" plus a \"Stop query\" link; the Run button changed to \"Cancel\".",
      "entered_text": "AzureDiagnostics | where TimeGenerated > ago(2h) | where Category == \"FrontDoorAccessLog\" | where requestUri_s !contains \"enrollment\" | where requestUri_s contains \"i.manage\" or requestUri_s contains \"r.manage\" or requestUri_s contains \"a.manage\" | summarize count() by strcat(httpStatusCode_d, requestUri_s), bin(TimeGenerated, 1m) | render timechart"
... (7628 more characters)
```

### Tool call 6: `get_frame`

```json
{"video": "v2/grouponly-100", "frame": 73, "image": false}
```

Result (trimmed):

```
Frame 73, t=206.83–206.83s.
Description in force: A maximized Edge browser window with many pinned tabs sits over a Windows desktop covered in shortcut icons; the Azure portal is open on the FRONTDOOR-A Front Door resource's Logs blade. A small find-on-page bar is open near the top right, showing a searched hostname with a 1/1 match count. The left blade navigation lists resource sections (Security, Analytics, Monitoring, Automation, Help) with Logs highlighted as the current selection. The query editor holds an eight-line KQL query against AzureDiagnostics, one line commented out and shown in green; the toolbar shows a red Cancel button, time range set in query, a 1000-result limit and KQL mode. Below, the Chart tab is selected and the results pane shows an animated loading indicator with 'Running your query...' and a 00:00 timer plus a Stop query link, so the screen is mid-refresh. A Windows taskbar with search box, pinned apps and a clock reading 11:38 AM 9/17/2026 runs along the bottom.
Texts alive at this frame (box, lifetime, text; when seen; notes):
b1 L2324 "A" | seen 206.8–212.9s in 3 frames | Microsoft Edge window
b2 L2325 "C+AI_SAW_.." | seen 206.8–224.0s in 7 frames | Micro
... (12789 more characters)
```

### Answer

Based on the index for `v2/grouponly-100` (duration 223.97 s, 80 captured frames):

**1. Overall, one paragraph:** An engineer works through the Azure portal adding a Traffic Manager endpoint named "AFDEndpoint" (FQDN `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`) to several `*-tm-profile-ATM` Traffic Manager profiles (AU01 already had it; the video adds it to tm-profile-ap, tm-profile-EU and tm-profile-NA), then switches to the FRONTDOOR-A Front Door manager to confirm the hostname exists there, and finishes in Log Analytics (and briefly Kusto.Explorer) running a KQL query over `AzureDiagnostics` FrontDoorAccessLog data and reading a timechart of request counts.

**2. Step by step (section starts, from the pipeline's segmentation):**
- 0:00 (C1) — On Front Door manager, resize/restore the window, switch tabs, open AU01-tm-profile → Endpoints (already has au.endpoint + AFDEndpoint).
- 0:25 (C2) — Open tm-profile-ap → Endpoints, click "+ Add", set External endpoint, enter FQDN, click Add (T22 toast "Saved").
- 1:04 (C3) — Navigate to Traffic Manager profiles list, sign in as the account holder, open tm-profile-EU → Endpoints, fill the Add-endpoint form.
- 2:06 (C4) — Switch to tm-profile-NA, add the same endpoint, click Add (T51-52 toast "Saved").
- 2:32 (C5) — Close the "Network" tab, find `f9.b02.azurefd.net` on the Front Door manager page (1/1 match, T56).
- 2:42 (C6) — Open Logs, trim the saved KQL query, Run it (T64), inspect the timechart.
- 3:21 (C7) — Check Kusto.Explorer's `XSU-RUALSV2.kql`, return to Edge, wait for a second query run to finish, inspect its chart.

**3. First thing on screen:** Frame 0 (t=0.03 s) is the Front Door manager page in Edge, mid-action — the person is dragging/restoring the browser window (T1, 0.03–~3s), which had been shifted down-right, clipping the portal content. The hostname `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net` is already visible on an endpoint card at this very first frame (L116).

**4. Endpoint form, fields and values** (from T19/T20/T39/T48-50, e.g. node T39): Type "External endpoint", Name "AFDEndpoint" (typed each time, green check), FQDN "FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net" (prefilled/pasted, matches the truncated field text at L1430/L1477), Weight left at default 1. Custom Header settings and the Enable Endpoint checkbox appear on the form but the record doesn't show them being touched — I can't confirm their final values from the index.

**5. Profiles, in order:** AU01-tm-profile already had it at the start (not added on-camera) → tm-profile-ap (~0:41–1:04, T22) → tm-profile-EU (~1:43–2:09, confirmed by T45) → tm-profile-NA (~2:06–2:32, T51-52).

**6. Did they succeed:** Yes, all three. ap01: green toast "Saved Traffic Manager profile changes" and the table grows to 2 rows (T22). NA01: toast sequence "Saving..." → "Saved..." with the new row showing (T51→T52). EU01: the toast/2-row table is confirmed at T45, though the actual "Add" click itself falls in a gap between captured frames (T43 shows it still open/unsubmitted at 125.6s, T44 at 126.1s is already a tab switch) — the save is evidenced, but the exact click isn't a captured transition.

**7. Hostname origin:** The record never shows it being typed or copied — it's already present, highlighted by an in-progress find-on-page search, in the very first frame (L116/L231, t=0.0–6.1s) on the Front Door manager's endpoint list. It's used from there in the Traffic Manager forms; no clipboard/copy action is visible.

**8. Sign-in prompt:** Yes. At T33 (94.2–97.2s) a `login.microsoftonline.com` "Pick an account" card appears with two "the account holder" tiles and "Use another account." At T34 (97.2–100.3s) the person clicks the first the account holder tile (user), completing sign-in into tm-profile-EU.

**9/10. The query near the end, line by line, and result:** Two runs, both against `AzureDiagnostics`:
- First run (T64, submitted "yes" at 178.1–181.1s): `AzureDiagnostics | where TimeGenerated > ago(2h) | where Category == "FrontDoorAccessLog" | where requestUri_s !contains "enrollment" | where requestUri_s contains "i.manage" or requestUri_s contains "r.manage" or requestUri_s contains "a.manage" | summarize count() by strcat(httpStatusCode_d, requestUri_s), bin(TimeGenerated, 1m) | render timechart`. Result: "3s 28ms", "1000 records" (T65).
- Second run (T73–T75, ~203.8–212.9s): same query but with the `i.manage`/`r.manage`/`a.manage` line commented out (`//| where requestUri_s contains "i.manage"...`, visible in green at frame 73). Result: "3s 153ms", "277 records", 5-series legend (T75). Note: one text box in frame 73 (L2258, "ServiceA/Certificate") looks like a stray reading possibly carried over from the Kusto.Explorer window rather than the Edge query — I flag it as uncertain rather than assert it's part of the query.

**11. Did the query change:** Yes — between the two runs, the `i.manage`/`r.manage`/`a.manage` requestUri filter line was commented out (T70→T71, ~194.8–200.8s); everything else stayed the same, including the `bin(TimeGenerated, 1m)` from the earlier edit at T61-62.

**12. Other applications:** Yes, Kusto.Explorer, briefly: brought to front at T72 (200.8–203.8s), showing the `XSU-RUALSV2.kql` tab and a timechart with a spike near 18:05, then the person switched back to Edge at T73 (203.8–206.8s).

**13. Anything fail, error, or get deleted:** No errors or failed saves are recorded — every add produced a "Saved" toast. The only deletions were text edits: lines 6-7 of the saved KQL query were selected and deleted at T61-62 (161.6–177.6s window), and the "Network" browser tab was closed at T54 (~155s). No data or resource was deleted.

**14. New profile or only changes:** Only existing profiles were changed — an endpoint was added to already-existing Traffic Manager profiles (tm-profile-ap, tm-profile-EU, tm-profile-NA). No new Traffic Manager profile was created.

**15. Total time / where most time went:** 223.97 s total (~3 min 44 s). By section: C1 ~24s, C2 ~39s, C3 (EU01: navigation + sign-in + form) ~62s — the longest single stretch — C4 ~26s, C5 ~10s, C6 ~39s, C7 ~23s.

**16. To reproduce, exact values:**
- Endpoint Type: `External endpoint`; Name: `AFDEndpoint`; FQDN: `FRONTDOOR-A-cqhefshkhrgmgqf9.b02.azurefd.net`; Weight: `1`.
- Profiles touched: `tm-profile-ap`, `tm-profile-EU`, `tm-profile-NA` (plus pre-existing `AU01-tm-profile`).
- Sign-in account: the account holder (user@example.com).
- Front Door/CDN profile: `FRONTDOOR-A`, resource group `PE-XSUCP-AFD.ResourceGroup`, subscription `00000000-0000-0000-0000-000000000000`.
- KQL (first run, verbatim) and the second run with the `i.manage/r.manage/a.manage` line commented — both given in full under #9/10.

**What the record can't tell you:** the exact instant "Add" was clicked for EU01 (falls in a frame gap); whether Custom Header settings were touched on any form; how the FQDN got into the clipboard/form (no copy action is captured, it's simply present from frame 0); and why record counts differ (1000 vs 277) between the two query runs — the index shows the change made, not Kusto's internal reasoning. One OCR box in frame 73 (`ServiceA/Certificate`) is ambiguous and may be a stray reading from the Kusto.Explorer window rather than genuine second-query text.

*8 turns, 6 tool calls, 171 s, $0.44.*
