"""Why does the 27B return `texts: []`? One call with the pipeline's own annotate prompt for smoke frame 145 (68 targets),
(a) as the run sent it but at temperature 0, (b) with `texts` constrained to at least one item (minItems) — the
request as the provider builds it, posted directly. Prints texts returned, agreement with OCR, tokens, seconds.
Usage: texts_check.py <run-dir> <model> <port> [a|b|both]"""
import asyncio, json, sys, time, copy
from pathlib import Path
from rapidfuzz import fuzz
from scry.config import Config, ModelConfig
from scry.run import Run
from scry.annotate.stage import ARM, PANE
from scry.prompts.annotate import prompt_version, system_prompt
from scry.annotate.output import output_model
from scry.annotate.blocks import build_blocks
from scry.annotate.targets import CallPlan, plan_calls
from scry.providers.openai_compat import OpenAICompatProvider, UrllibClient, parse_answer
from scry.providers.cache import CallCache
from scry.textdiff import norm

root, model_name, port = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
which = sys.argv[4] if len(sys.argv) > 4 else "both"
run = Run(root)
cfg = Config.model_validate(json.load(open(root / "config.json")))
frames = {f.frame: f for f in run.load_frames()}
boxes = {fb.frame: fb for fb in run.load_boxes()}
plans = plan_calls(list(boxes.values()), list(run.load_changes()), list(run.load_lifetimes()), "incremental")
plan = next(p for p in plans if p.frame == 145)
a = cfg.annotate
system, model = system_prompt(ARM, a.transcribe, PANE, a.reference), output_model(ARM, a.transcribe, PANE, a.reference)
frame_png = root / frames[145].png
overlay_png = run.overlays_dir / "00145.png"
blocks = build_blocks(frames[145], boxes[145], plan, ARM, a.scale, frame_png, overlay_png, a.reference)
mc = ModelConfig(provider="openai_compat", model=model_name, base_url=f"http://127.0.0.1:{port}/v1", concurrency=1, max_tokens=cfg.model.max_tokens)
p = OpenAICompatProvider(mc, CallCache(Path("/tmp/none-cache-unused")), client=UrllibClient())
ocr = {b.id: b.text for b in boxes[145].boxes}


def variant(name, temperature=None, min_items=None):
    body = p.request(system, blocks, model, cfg.model.max_tokens)
    if temperature is not None:
        body["temperature"] = temperature
    if min_items is not None:
        schema = body["response_format"]["json_schema"]["schema"]
        schema["properties"]["texts"]["minItems"] = min_items
    t0 = time.monotonic()
    status, resp = asyncio.run(p.client.post_json(p.url, body, {"Authorization": "Bearer none"}))
    wall = time.monotonic() - t0
    text = resp["choices"][0]["message"]["content"]; u = resp["usage"]
    try:
        out = parse_answer(text, model); err = None
    except Exception as e:
        out = None; err = str(e)[:200]
    d = json.loads(text) if err is None else {}
    texts = d.get("texts", [])
    good = sum(1 for t in texts if t["box"] in ocr and fuzz.ratio(norm(t["text"]).lower(), norm(ocr[t["box"]]).lower()) >= 80)
    print(f"[{name}] {wall:.1f}s prompt={u.get('prompt_tokens')} completion={u.get('completion_tokens')} finish={resp['choices'][0].get('finish_reason')} "
          f"valid={err is None} {err or ''} | texts {len(texts)} of {len(plan.targets)} targets, agreeing with OCR {good}, missed {len(d.get('missed', []))}, "
          f"assign {len(d.get('assign', []))}, pairs {len(d.get('pairs', []))}, records {len(d.get('records', []))}")
    for t in texts[:6]:
        print(f"      {t['box']:>5} model={t['text'][:45]!r:50} ocr={ocr.get(t['box'], '<none>')[:45]!r}")
    Path(f"/private/tmp/claude-501/-Users-harrisonogle-src-harrisonogle-agentic-escort/00000000-0000-0000-0000-000000000000/scratchpad/localvlm/results/texts-check-{name}.json").write_text(text)


if which in ("a", "both"):
    variant("temp0", temperature=0.0)
if which in ("b", "both"):
    variant("minitems1", min_items=1)
