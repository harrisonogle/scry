"""outline (optional, "Stage 0"): a coarse chapter outline of the whole video from Gemini's agentic video mode, or one
imported from a JSON file. Later stages use it only as context, and every one of them runs without it."""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

from scry.config import Config
from scry.run import Run
from scry.schemas import OutlineChapter

log = logging.getLogger(__name__)

PROMPT = """Produce a chapter outline of this screen-recording tutorial as JSON: a list of 5-20 objects with keys start_s, end_s (seconds), title, gist. Put boundaries where the sub-goal changes. Do not attempt to transcribe exact text. Return only the JSON array."""

SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "start_s": {"type": "number"}, "end_s": {"type": "number"}, "title": {"type": "string"}, "gist": {"type": "string"}},
    "required": ["start_s", "end_s", "title", "gist"]}}

CALL_PATH = "files.upload, then interactions.create (video processing=agentic, JSON response schema)"  # verified live 2026-09-21, google-genai 2.23.0
# $ per million tokens, input / output including thinking: the Gemini API's paid-tier list prices fetched 2026-09-21
# (ai.google.dev/gemini-api/docs/pricing; one input rate for every modality; the page says both double on 2027-01-01)
LIST_PRICES = {"gemini-3.8-flash": (0.75, 3.75)}
UPLOAD_TIMEOUT_S = 600  # seconds for the uploaded file to become ACTIVE


class OutlineError(RuntimeError):
    """The outline stage cannot run, or got nothing usable; the message says what to do."""


def parse_outline_text(text: str) -> list[OutlineChapter]:
    """Lenient: the first [...] in the text (so code fences and a wrapping object are fine); an entry without the keys,
    with a time that is not a number, or that ends before it starts is dropped; chapters are ordered by start."""
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        raw = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    items = []
    for it in raw:
        try:
            item = (float(it["start_s"]), float(it["end_s"]), str(it["title"]), str(it.get("gist", "")))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if item[1] > item[0]:
            items.append(item)
    items.sort()
    return [OutlineChapter(id=f"c{i}", start_s=s, end_s=e, title=t, gist=g) for i, (s, e, t, g) in enumerate(items, start=1)]


def build_request(uri: str, mime_type: str, model: str) -> dict:
    """The keyword arguments of `client.interactions.create` (google-genai 2.23: a `video` content block with
    `processing: "agentic"`, a `text` response format with a JSON schema). No output-token limit on purpose: the model
    thinks before it replies and thinking counts against the limit."""
    return {"model": model,
            "input": [{"type": "video", "uri": uri, "mime_type": mime_type, "processing": "agentic"}, {"type": "text", "text": PROMPT}],
            "response_format": {"type": "text", "mime_type": "application/json", "schema": SCHEMA}}


def usage_by_kind(usage: dict) -> dict:
    """Token counts by kind from the interaction's `usage` (dumped to a dict): the prompt, the agentic mode's own tool
    use (where the video is counted: the mode fetches frames through its own calls, so the prompt holds only the text),
    thinking, output and the API's total; prompt and tool use are also split by modality (text, image, video, audio)."""
    def split(prefix: str, key: str) -> dict:
        return {f"{prefix}_{m['modality']}": m.get("tokens") or 0 for m in usage.get(key) or [] if m.get("modality")}
    return {"prompt": usage.get("total_input_tokens") or 0, **split("prompt", "input_tokens_by_modality"),
            "tool_use": usage.get("total_tool_use_tokens") or 0, **split("tool_use", "tool_use_tokens_by_modality"),
            "thinking": usage.get("total_thought_tokens") or 0, "output": usage.get("total_output_tokens") or 0,
            "total": usage.get("total_tokens") or 0}


def list_price_cost(tokens: dict, model: str) -> float | None:
    """Dollars at LIST_PRICES (prompt and tool-use tokens at the input rate, thinking and output at the output rate);
    None for a model with no price here."""
    if model not in LIST_PRICES:
        return None
    pin, pout = LIST_PRICES[model]
    return round(((tokens["prompt"] + tokens["tool_use"]) * pin + (tokens["thinking"] + tokens["output"]) * pout) / 1e6, 4)


def _client():
    try:
        from google import genai  # optional extra
    except ImportError as e:
        raise OutlineError("the outline stage needs the Google SDK: run `uv sync --extra outline`") from e
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise OutlineError("the outline stage needs GEMINI_API_KEY in the environment or ./.env (or import an outline with --import)")
    # passed explicitly: a bare Client() takes GOOGLE_API_KEY first when both are set, and that key may not be one for the Gemini API
    return genai.Client(api_key=key)


def _gemini_outline(video: Path, model: str) -> tuple[str, dict]:
    """Upload the video, wait until it is ACTIVE, ask for the outline; returns the reply text and what the call took."""
    from importlib.metadata import version

    client = _client()
    t0 = time.perf_counter()
    f = client.files.upload(file=str(video))
    try:
        while f.state is None or f.state.name != "ACTIVE":
            if f.state is not None and f.state.name == "FAILED":
                raise OutlineError(f"Gemini could not process the uploaded video: {f.error}")
            if time.perf_counter() - t0 > UPLOAD_TIMEOUT_S:
                raise OutlineError(f"the uploaded video was not ACTIVE after {UPLOAD_TIMEOUT_S} s")
            time.sleep(3)
            f = client.files.get(name=f.name)
        t1 = time.perf_counter()
        interaction = client.interactions.create(**build_request(f.uri, f.mime_type, model))
        t2 = time.perf_counter()
    finally:
        try:
            client.files.delete(name=f.name)  # it would expire by itself in 48 hours
        except Exception as e:
            log.warning("could not delete the uploaded file %s: %s", f.name, e)
    if interaction.status != "completed":
        raise OutlineError(f"the interaction ended with status {interaction.status!r}: {interaction.errors}")
    tokens = usage_by_kind(interaction.usage.model_dump(exclude_none=True) if interaction.usage else {})
    stats = {"model": model, "call_path": CALL_PATH, "sdk": f"google-genai {version('google-genai')}", "interaction_id": interaction.id,
             "steps": [s.type for s in interaction.steps or []], "tokens": tokens,
             "seconds": {"upload_and_processing": round(t1 - t0, 1), "call": round(t2 - t1, 1), "total": round(t2 - t0, 1)},
             "cost_usd": list_price_cost(tokens, model),
             "cost_basis": "Gemini API paid-tier list prices fetched 2026-09-21" if model in LIST_PRICES else "no list price recorded for this model"}
    return interaction.output_text or "", stats


def run_outline(run: Run, cfg: Config, video: Path, import_path: Path | None = None) -> None:
    if import_path is not None:
        chapters, stats = parse_outline_text(import_path.read_text()), {"source": str(import_path)}
        if not chapters:
            raise OutlineError(f"no chapter could be read from {import_path}: it must hold a JSON list of objects with start_s, end_s, title, gist")
    elif cfg.outline.enabled:
        if run.outline.exists():
            log.info("outline exists; skipping")
            return
        text, stats = _gemini_outline(video, cfg.outline.model)
        chapters, stats = parse_outline_text(text), {"source": cfg.outline.model, **stats}
        if not chapters:
            raise OutlineError(f"no chapter could be read from the model's reply, which began: {text[:200]!r}")
    else:
        return
    run.outline.write_text(json.dumps([c.model_dump() for c in chapters], indent=1))
    run.manifest_update(outline={"chapters": len(chapters), **stats})
    log.info("outline: %d chapters from %s", len(chapters), stats["source"])
