"""Four single calls on one frame of a finished local run, the pipeline's own annotate prompt and blocks, to see what
fills `texts`: (1) temperature 0; (2) `texts` minItems = number of targets; (3) the texts paragraph first in the system
prompt and the user turn ending "Return texts for every target"; (4) a texts-only schema (texts and missed) with the
texts paragraph. Readings are quoted against the OCR text. Usage: texts_check4.py <run-dir> <model> <port> <frame>"""
import asyncio, json, sys, time
from pathlib import Path
from pydantic import BaseModel, Field, create_model
from rapidfuzz import fuzz
from scry.config import Config, ModelConfig
from scry.run import Run
from scry.annotate.stage import ARM, PANE
from scry.prompts import annotate as P
from scry.annotate.output import output_model, OutText, OutMissed
from scry.annotate.blocks import build_blocks
from scry.annotate.targets import plan_calls
from scry.providers.openai_compat import OpenAICompatProvider, UrllibClient, parse_answer
from scry.providers.base import text_block
from scry.providers.cache import CallCache
from scry.textdiff import norm

OUT = Path("<scratch>/localvlm/results")
root, model_name, port, frame_no = Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
run = Run(root)
cfg = Config.model_validate(json.load(open(root / "config.json")))
frames = {f.frame: f for f in run.load_frames()}
boxes = {fb.frame: fb for fb in run.load_boxes()}
plans = plan_calls(list(boxes.values()), list(run.load_changes()), list(run.load_lifetimes()), "incremental")
plan = next(p for p in plans if p.frame == frame_no)
a = cfg.annotate
system = P.system_prompt(ARM, a.transcribe, PANE, a.reference)
model = output_model(ARM, a.transcribe, PANE, a.reference)
blocks = build_blocks(frames[frame_no], boxes[frame_no], plan, ARM, a.scale, root / frames[frame_no].png, run.overlays_dir / f"{frame_no:05d}.png", a.reference)
mc = ModelConfig(provider="openai_compat", model=model_name, base_url=f"http://127.0.0.1:{port}/v1", concurrency=1, max_tokens=cfg.model.max_tokens)
p = OpenAICompatProvider(mc, CallCache(Path("/tmp/none-cache-unused")), client=UrllibClient())
ocr = {b.id: b.text for b in boxes[frame_no].boxes}
print(f"frame {frame_no}: {len(plan.targets)} targets {list(plan.targets)}; OCR: {[(t, ocr[t][:30]) for t in plan.targets][:12]}")

TextsOnly = create_model("AnnotateTextsOnly", texts=(list[OutText], ...), missed=(list[OutMissed], ...))


def call(name, system_, blocks_, out_model, temperature=None, min_items=None):
    body = p.request(system_, blocks_, out_model, cfg.model.max_tokens)
    if temperature is not None:
        body["temperature"] = temperature
    if min_items is not None:
        body["response_format"]["json_schema"]["schema"]["properties"]["texts"]["minItems"] = min_items
    t0 = time.monotonic()
    status, resp = asyncio.run(p.client.post_json(p.url, body, {"Authorization": "Bearer none"}))
    wall = time.monotonic() - t0
    if status != 200:
        print(f"[{name}] HTTP {status}: {str(resp)[:300]}"); return
    text = resp["choices"][0]["message"]["content"]; u = resp["usage"]
    try:
        parse_answer(text, out_model); err = None
    except Exception as e:
        err = str(e)[:200]
    d = json.loads(text) if err is None else {}
    texts = d.get("texts", [])
    good = sum(1 for t in texts if t["box"] in ocr and fuzz.ratio(norm(t["text"]).lower(), norm(ocr[t["box"]]).lower()) >= 80)
    print(f"[{name}] {wall:.1f}s prompt={u.get('prompt_tokens')} completion={u.get('completion_tokens')} finish={resp['choices'][0].get('finish_reason')} valid={err is None} {err or ''}"
          f" | texts {len(texts)} of {len(plan.targets)} targets ({sum(1 for t in texts if t['box'] in plan.targets)} on targets), agreeing with OCR {good}, missed {len(d.get('missed', []))}, "
          f"assign {len(d.get('assign', []))}, pairs {len(d.get('pairs', []))}, records {len(d.get('records', []))}")
    for t in texts[:10]:
        print(f"      {t['box']:>5} model={t['text'][:50]!r:55} ocr={ocr.get(t['box'], '<no such box>')[:50]!r}")
    for m in d.get("missed", [])[:4]:
        print(f"      MISSED {m}")
    (OUT / f"texts4-f{frame_no}-{name}.json").write_text(text)


which = sys.argv[5] if len(sys.argv) > 5 else "1234"
if "1" in which:
    call("1-temp0", system, blocks, model, temperature=0.0)
if "2" in which:
    call("2-minitems-n", system, blocks, model, min_items=len(plan.targets))
if "3" in which:
    parts = [P.ROLE, P.TEXTS, P.IMAGES, P.CONTAINERS, P.ASSIGN, P.LINKS, P.DESCRIPTION]
    sys3 = "\n\n".join(parts)
    blocks3 = blocks[:-1] + [text_block("Return texts for every target. Return the JSON object.")]
    call("3-texts-first", sys3, blocks3, model)
if "4" in which:
    sys4 = "\n\n".join([P.ROLE, P.IMAGES, P.TEXTS])
    blocks4 = blocks[:-1] + [text_block("Return only texts and missed. Return the JSON object.")]
    call("4-texts-only", sys4, blocks4, TextsOnly)
