from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from scry.config import Config
from scry.run import Run
from scry.schemas import OutlineChapter

log = logging.getLogger(__name__)

PROMPT = """Produce a chapter outline of this screen-recording tutorial as JSON: a list of 5-20 objects with keys start_s, end_s (seconds), title, gist. Put boundaries where the sub-goal changes. Do not attempt to transcribe exact text. Return only the JSON array."""


def parse_outline_text(text: str) -> list[OutlineChapter]:
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
            items.append((float(it["start_s"]), float(it["end_s"]), str(it["title"]), str(it.get("gist", ""))))
        except (KeyError, TypeError, ValueError):
            continue
    items.sort()
    return [OutlineChapter(id=f"c{i}", start_s=s, end_s=e, title=t, gist=g) for i, (s, e, t, g) in enumerate(items, start=1)]


def _gemini_outline(video: Path, model: str) -> str:
    from google import genai  # optional extra: uv sync --extra outline

    client = genai.Client()
    f = client.files.upload(file=str(video))
    while not f.state or f.state.name != "ACTIVE":
        time.sleep(5)
        f = client.files.get(name=f.name)
    # [verify] input item shape per the Gemini docs fetched 2026-09-13; google-genai 2.23 exposes client.interactions
    interaction = client.interactions.create(model=model, input=[
        {"type": "video", "uri": f.uri, "mime_type": f.mime_type, "processing": "agentic"},
        {"type": "text", "text": PROMPT}])
    return interaction.output_text


def run_outline(run: Run, cfg: Config, video: Path, import_path: Path | None = None) -> None:
    if import_path is not None:
        chapters = parse_outline_text(import_path.read_text())
    elif cfg.outline.enabled:
        if run.outline.exists():
            log.info("outline exists; skipping")
            return
        chapters = parse_outline_text(_gemini_outline(video, cfg.outline.model))
    else:
        return
    run.outline.write_text(json.dumps([c.model_dump() for c in chapters], indent=1))
    run.manifest_update(outline={"chapters": len(chapters), "source": str(import_path) if import_path else cfg.outline.model})
