"""The pipeline's annotate stage, unchanged, on a copy of a finished local run, with one difference in the request: the
grammar is told `texts` holds at least one item (minItems 1 on the output schema). Own empty cache; the run directory
sits beside the original as <name>-min1. Usage: annotate_minitems.py <src-run-dir> <model> <port>"""
import json, logging, shutil, sys
from pathlib import Path
from scry.config import Config
from scry.run import Run
from scry.annotate.stage import run_annotate
from scry.providers.openai_compat import OpenAICompatProvider
from scry.providers.cache import CallCache

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
src, model_name, port = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
dst = src.parent / (src.name.replace("-r1", "-min1-r1"))
if dst.exists():
    shutil.rmtree(dst)
dst.mkdir()
for name in ("boxes.jsonl", "changes.jsonl", "config.json", "frames.jsonl", "lifetimes.jsonl", "evalrun.json"):
    shutil.copy(src / name, dst / name)
shutil.copytree(src / "frames", dst / "frames")
m = json.load(open(src / "manifest.json"))
m["stages"].pop("annotate", None)
json.dump(m, open(dst / "manifest.json", "w"), indent=1)
cfg = Config.model_validate(json.load(open(dst / "config.json")))
cfg = cfg.model_copy(update={"model": cfg.model.model_copy(update={"model": model_name, "base_url": f"http://127.0.0.1:{port}/v1"})})


class MinItemsProvider(OpenAICompatProvider):
    def request(self, system, blocks, output_model, max_tokens):
        body = super().request(system, blocks, output_model, max_tokens)
        body["response_format"]["json_schema"]["schema"]["properties"]["texts"]["minItems"] = 1
        return body


run = Run(dst)
run_annotate(run, cfg, MinItemsProvider(cfg.model, CallCache(run.cache_dir)))
a = json.load(open(dst / "manifest.json"))["stages"]["annotate"]
print("DONE", dst, {k: a.get(k) for k in ("calls", "errors", "mark_match", "repairs", "repair_counts", "usage")})
