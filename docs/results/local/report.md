# Local VLM probe, final report

Two mlx-community 4-bit models served on this Mac through a new `openai_compat` provider: `Qwen3-VL-8B-Instruct-4bit` (8B) and `Qwen3.8-27B-4bit` (27B). All runs are cold, one repeat, through the pipeline's own stages on the P3 subsets of `runs/p0`. Code on branch `local-vlm` (commits 1069ae7, 5001be7), suite 360 green. No API cost.

## Efficacy

### annotate, group-only (the owner's chosen default): 27B beside the P10 ids100 yardstick, smoke span 145–155

Scored with P10's `qual.py` (copied to scratch as `qual_p10_local.py`); the 27B's answers were made in transcribing mode and their `texts` are ignored here. The min1 re-run (below) gave byte-identical containers and links, so this row stands for both 27B runs.

| measure | API ids100 r1 / r2 (P10) | 27B | 8B |
|---|---|---|---|
| reference pairs reproduced, % vs ids100 r1 / r2 | 97.4 / 95.0 | 27.5 / 28.2 | 0 / 0 |
| container differs, % of targets | 0.0 | 45.1 (113 targets of frame 147 left unplaced) | 4.3 |
| links run / pair / record kept | 8/40/6, 9/39/6 | 2/16/3 | 0/0/0 |
| frame 150 pairs correct / wrong / missing of 28 | 28/1/0 | 8/3/20 | 0/0/28 |
| terminal boxes in the terminal window (of 9) | 9 | 5 (PowerShell listed as a window on 3/3 frames; frame 147's boxes unplaced) | 0 (PowerShell labelled a popup) |
| tooltip 149 / 151 as its own popup | yes / yes | yes / no (description says "a tooltip … 'Administrator: PowerShell 7-preview (x64)'", but no popup container) | no / no |
| containers per record; popups | 1.45; 2 | 1.36; 1 | 1.27; 3 |
| repairs (kinds) | 0 | 176: unplaced 113, unknown_box 43, link_malformed 11, bad_owner 6, already_linked 3 | 2 link_malformed (+109 text_missing) |
| ids named that do not exist | 0 | 43, all on frame 147: `{"box": "", "container": ""}` × 43, a degenerate answer for the 113-target frame | 0 |

27B pairs that are right by id on frame 148 (where frame 150's boxes start): `API server address => aks1-kodekloudapp-dns-…`, `Network type (plugin) => Azure CNI`, `Service CIDR => 10.0.0.0/16`, `DNS service IP => 10.0.0.10`, `Docker bridge CIDR => 172.17.0.1/16`, `Network Policy => None`. Wrong: `Networking => aks1-…` (section heading as key), `Network type (plugin) : Azure CNI => Node pools + : 1 node pool`. Seven records of frame 145's deployment table carry the right ids (one is the header row). The 27B reads the numbered tags; it labels a third of what the API labels and collapses on the densest frame.

The 8B does not read the tags: its readings are real screen text attached to the wrong ids with scattered offsets (+2, +11, −4, +6, +40 …); agreement 17/52 in the first ten positions of its list, 5/94 after. Its labels are at P3's 0.2-scale level.

### annotate, second readings (transcribing mode), P3 s100 references

| measure | API s100 r1 / r2 | 27B as prompted | 27B with `texts` forced (minItems 1, re-run) | 8B |
|---|---|---|---|---|
| readings returned / targets | 212 / 255 | 2 / 255 | 225 / 225 | 146 / 255 |
| agreeing with OCR | 86.8% / 87.0% | 1 of 2 | 43.1% (97/225); frame 145: 59/68 = 87%, frame 148: 31/39; frame 147 (degenerate): 11/113; without 147: 77% | 8.2% |
| readings on the wrong box | 0 (+1 off) | 0 | 71 (+13 off), 43 of them on frame 147 | 98 (+12 off) |
| real words read as "" | 3 / 7 | 0 | 12 | 0 |
| missed strings | 7 / 14 | 118 (114 on frame 151: the page's text, URL included, dumped into `missed`) | 1 | 0 |
| frame 155 edited line (truth: bare `a` before a grey suggestion) | `PS C:\Users\msadmin> a_ login` / `… a` | no reading | `a_ login` (prompt prefix dropped; absorbs the suggestion like the API's r1) | `PS C:\Users\msadmin> a_login` (absorbs it) |

### interpret, span2 155–187, no annotation, half scale: the harness's command scores

`found` needs the index: `summarize` (10 calls on the 27B, 18k prompt / 1.2k completion tokens) and `index` were run on the run directory with its own config. Opus and Sonnet rows are the P4/P8 full-video runs' scorecards.

| run | found | exact (OCR / model reading) | submitted | false run of the 5 never-run strings | submit frame error |
|---|---|---|---|---|---|
| 27B, span2 | 7/7 | 7/7 / — | 5/7 | 0/5 | 0.0 |
| Opus, incremental, r1 and r2 (P4) | 7/7 | 7/7 / 7/7 | 7/7 | 0/5 | 0.0 |
| Sonnet, incremental, r1 / r2 (P8) | 7/7 | 7/7 / 7/7 | 5/7 / 6/7 | 1/5 / 0/5 | 0.0 |
| Sonnet, no annotation, r1 (P8) | 7/7 | 7/7 / — | 5/7 | 0/5 | 0.0 |
| 8B, span2 (31 of 32 records; T27 ran away to 16000 then 32000 tokens, deterministic) | 7/7 | 7/7 / — | 3/7 | **2/5** (`az login` claimed submitted at frame 156, `kubectl config current-context` at 176) | 0.0 |

27B misses: `az aks get-Credentials` (frame 169: `submitted: yes` with `entered_text: null`, so no claim attaches) and `kubectl get deployment` (frame 186: `submitted: yes` with `entered_text: "kubectl get deploy"`, the text as typed before the suggestion). No false yes on the page navigations 182–184; one missed `Y` (frame 170, `no`). 32 records, 0 errors, mean confidence 0.83 (Opus 0.80–0.82, Sonnet 0.66–0.68; the 8B 0.94 with 3/7 submitted and two false runs).

Secondary, the honest text-change contract on the 10 of the 21 typing transitions that fall in the span (frames 161–185):

| run | suggestion recorded as entered | typed only | null | other (suggestion with a typo: `kubectl_rollout undo …`, `kubectlrollout undo …`, `kubectl get vc`) | record calls it a suggestion |
|---|---|---|---|---|---|
| Opus r1 / r2 | 1 / 1 | 9 / 9 | 0 | 0 | 10/10, 10/10 |
| Sonnet r1 / r2 | 10 / 8 | 0 | 0 | 0 / 2 | 5/10, 2/10 |
| 27B | 5 | 0 | 2 | 3 | 1/10 |
| 8B | 3 | 0 | 1 | 6 | 4/10 |

The 27B is at Sonnet's level on the contract: it writes the grey suggestion into `entered_text` (8 of 10 counting the typo variants) and almost never names it a suggestion; it is at Opus's level on false runs (0) and confidence.

### Why the 27B returns `texts: []` and dumps transcriptions into `missed`

Free checks. The request carries `output_model.model_json_schema()` with its 21 field descriptions intact, all nine fields `required`, no `minItems`, so an empty `texts` list is valid. mlx-vlm turns the schema into an llguidance grammar; the model never sees the schema or its descriptions (with the Anthropic API the descriptions are prompt text, output.py's docstring relies on that). The system prompt's texts paragraph is the sixth of seven paragraphs. In every 27B answer the keys come in schema order and `"texts": []` sits between `records` and `missed`; the 8B, on the same request, wrote 64 readings on frame 145. So the request is the same for both; what differs is the model's willingness to fill an optional-looking list.

Four single calls on frame 150 (4 targets: three icons the OCR read as CJK glyphs, and `Policies`), the pipeline's own prompt and images:

| variant | texts returned | readings (model / OCR) |
|---|---|---|
| (1) temperature 0 | 0 of 4 | — |
| (2) `minItems` = 4 in the grammar | 4 of 4, on the target ids | b9 `''` / `区` (icon), b30 `+` / `十` (a plus icon), b132 `Automated deployments` / `品` (the icon's label, not the icon), b135 `(preview)` / `Policies` (next word, wrong) |
| (3) texts paragraph first in the system prompt, user turn ends "Return texts for every target" | 4 of 4, no grammar change | b9 `?` / `区`, b30 `''` / `十`, b132 `Automated deployments (preview)` / `品`, b135 `Policies` / `Policies` (right) |
| (4) texts-only schema (texts and missed), texts paragraph | 0 of 4; 11 completion tokens: `{"texts": [], "missed": []}` | — |

On frame 145 (68 targets) the same two checks: temperature 0 → 0 of 68 (pairs 9, no records); `minItems` 1 → 68 of 68, 59 agreeing with OCR (`user@example...`, `Microsoft Azure`, `Search resources, services, and docs (G+ /)`, `Home` for `Home>`), and the whole-smoke re-run with `minItems` 1 filled every target (table above). Best explanation: the model does not see the schema's descriptions and treats `texts` as optional; it writes the minimal valid object unless the grammar forces items or the prompt puts the transcription first. When forced it binds readings to ids about as well as the API on ordinary frames (87% on 145, 79% on 148) and poorly on icons and on the frame where its answer had already degenerated. The `missed` dump on 151 is the same behaviour: the id-free field takes what the model did not put under ids. Variant (4) shows it is not only id-binding: asked for texts alone it still wrote nothing.

## Cost

Tokens per call, one call per frame (11 calls on 11 smoke frames; 32 interpret calls on 33 span2 frames). Priced (a) at OpenRouter's listed rate for the same model, `qwen/qwen3.8-27b` $0.42 per M prompt, $3.00 per M completion, and `qwen/qwen3-vl-8b-instruct` $0.117 / $0.455, read from https://openrouter.ai/api/v1/models on 2026-09-21 (a search summary the same day quoted $0.10/$1.80 for the 27B; the list price moves week to week); (b) as GPU time on a rented RTX 3090 at $0.46/h (RunPod, https://flexprice.io/blog/runprod-pricing-guide-with-gpu-costs) at the published decode throughput of Qwen3.8-27B at 4-bit on one RTX 3090 with vLLM: 127 tok/s single-stream, about 1,035 tok/s aggregate at 64 concurrent (https://github.com/syv-ai/qwen38-27b-rtx3090). No published prefill rate: (b) is decode only, and the prompt is 5.5k tokens (two 1080p images) per annotate call, so it understates. No 8B GPU figure was looked up.

| stage, model | prompt / completion tokens per call | (a) hosted, $ per frame | (b) GPU, single-stream / batched, $ per frame | Opus, $ per frame |
|---|---|---|---|---|
| annotate 27B, group-only as it answered (texts empty) | 5463 / 835 | 0.0048 | 0.00084 / 0.00010 | 0.0782 (transcribing, P3 1.0) |
| annotate 27B, texts forced (min1 re-run) | 5463 / 1084 | 0.0055 | 0.0011 / 0.00013 | 0.0782 |
| annotate 8B | 5450 / 817 | 0.0010 | — | 0.0782 |
| interpret 27B | 3190 / 182 | 0.0019 | 0.00018 / 0.00002 | 0.021 |
| interpret 8B (31 ok calls) | 3055 / 215 | 0.0005 | — | 0.021 |
| summarize 27B (10 calls for 33 frames) | 1800 / 121 | 0.0011 per call, 0.0003 per frame | 0.00012 / 0.00001 per call | — |

At the hosted rate the 27B is 14–16× cheaper than Opus on annotate and 11× on interpret, for a third of the labels and Sonnet's contract; API input here includes the images as prompt tokens as the hosted provider would count them.

## Run and code facts

- Installed in `~/.venvs/localvlm` (Python 3.12.13): mlx-vlm 0.7.2, mlx 0.32.2, llguidance 1.8.0, transformers 5.17, huggingface_hub 1.32.0. Downloads: 8B 5.78 GB in 3.0 min, 27B 16.05 GB in 4.5 min (the two xet downloads throttle each other to 3 MB/s when parallel; alone 140 MB/s). Both repo ids exist as given; the 27B is model_type `qwen3_5`, `Qwen3_5ForConditionalGeneration`, with a vision config.
- Server: `python -m mlx_vlm.server --model <repo> --port <p> --max-num-seqs 1`; `/v1/chat/completions` with `response_format` json_schema through llguidance. Prefix caching never engaged (`cached_tokens=0`). Sampling is each model's generation_config (8B 0.7 / top_p 0.8; 27B 1.0 / top_p 0.95); the provider sets none. The server is deterministic for a given prompt: the min1 re-run's frame-145 answer is byte-identical to the single check call, and its containers and links are identical to the first run's, so a local repeat measures nothing unless the seed is varied.
- JSON validity: 8B 11/11 annotate, 31/32 interpret (T27: 16000 tokens of valid, looping JSON, and 32000 on the retry, the same both times the run was made), 9/9 summarize; 27B 11/11 + 11/11 annotate, 32/32 interpret, 10/10 summarize, 4/4 checks. Every id the 8B named exists; the 27B named 43 non-ids on frame 147.
- Code: `src/scry/providers/openai_compat.py` (block conversion to image_url data URLs, json_schema strict with the model's schema, schema retry with the error appended, length retry, usage from prompt/completion tokens, effort ignored, no batch mode, stdlib HTTP on a thread), `config.py` (`provider` literal, `base_url`, `OPENAI_COMPAT_API_KEY` default "none"), `costs.py` (`mlx-community/` priced 0), `providers/__init__.py`; `tests/test_openai_compat.py` (7 tests). `uv run pytest`: 360 passed, exit status 0. Matrices `evals/local-scry.toml`, `evals/local-probe.toml`, `evals/local-span2.toml`.
- Raw outputs: `runs/eval/local-probe/smoke-q8b-r1`, `smoke-q27b-r1`, `smoke-q27b-min1-r1` (the forced-texts re-run, made by `scratchpad/localvlm/annotate_minitems.py` through `run_annotate` with a one-line schema change and its own cache); `runs/eval/local-span2/span2-q27b-r1` (interpret, summarize, index, `commands-score.json`), `span2-q8b-r1`. Scratch `scratchpad/localvlm/`: server and run logs, `results/` (smoke-labels.txt, p10-grouponly-smoke.txt, commands-27b.txt, interp-contract-27b.txt, texts-check-*.json, texts4-f150-*.json), `scripts/` (qual_local.py, qual_p10_local.py, f150_local.py, spec_local.py, interp_local.py, commands_local.py, calls_table.py), `texts_check.py`, `texts_check4.py`.

## Uncertain

- One repeat per run and a deterministic server: no repeat noise is measured; the API rows carry theirs (pairs 95–97%, containers 0.0–0.4%).
- The P10 yardstick is group-only; the 27B's containers and links come from transcribing-mode answers (a group-only run was not made). The 27B's frame-147 degeneration (43 empty ids) may or may not recur under a different seed.
- The 27B's temperature is its config's 1.0; temperature 0 changed nothing about `texts` on two frames but was not tried for labels.
- Hosted prices are one provider's list on one day; the GPU figure is decode-only on a consumer card from one repository's README.

Footnote, wall time (not the point; the Mac was shared with API eval runs, a video renderer and heavy swap): 8B annotate 25 s per call (41 tok/s decode, 1400 tok/s prefill), interpret 4–17 s; 27B annotate 75 s per call as prompted, 65 s with texts forced (12–17 tok/s decode, 400–600 tok/s prefill), interpret 16 s, summarize 9 s. Memory: 8B 6 GB wired, 27B 20–23 GB wired; the two cannot be co-resident on 36 GB.
