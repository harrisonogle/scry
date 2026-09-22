"""Shared pieces of the Gemini comparison (analysis only; the pipeline is not touched). Read-only use of scry modules:
the question parser, the blind judge, the Anthropic provider and its price table, load_dotenv, and outline.py's Gemini
call shape and price list. Raw outputs go under runs/compare-gemini/ (git-ignored)."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

from scry.env import load_dotenv
from scry.evaluation.questions import Answer, Question, parse_questions
from scry.outline import LIST_PRICES, UPLOAD_TIMEOUT_S, list_price_cost, usage_by_kind

log = logging.getLogger("compare.gemini")

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent  # the worktree root (runs/ and .env are symlinks to the main checkout's)
MAIN = Path("/Users/harrisonogle/src/harrisonogle/agentic-escort")
OUT = REPO / "runs" / "compare-gemini"
QUESTIONS = REPO / "docs" / "ground-truth" / "full-questions.md"
GEMINI_MODEL = "gemini-3.8-flash"
OPUS_MODEL = "claude-opus-5"
GEMINI_CONCURRENCY = 4
ANTHROPIC_CONCURRENCY = 8
CALL_TIMEOUT_S = 1800

ANSWER_INSTRUCTION = """Answer the question from the video. Give a time (mm:ss) for every factual claim. Quote on-screen text exactly as displayed, character for character. If the video does not show something, say so."""


def setup() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_dotenv(REPO / ".env")
    OUT.mkdir(parents=True, exist_ok=True)


def video_path() -> Path:
    manifest = json.loads((REPO / "runs" / "p0" / "manifest.json").read_text())
    p = Path(manifest["video"])
    return p if p.is_absolute() else MAIN / p


def questions(path: Path = QUESTIONS) -> list[Question]:
    return parse_questions(Path(path).read_text())


def write_jsonl(path: Path, rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(json.dumps(r.model_dump() if hasattr(r, "model_dump") else r) + "\n" for r in rows))
    tmp.replace(path)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


# ---- Gemini -----------------------------------------------------------------------------------------------------

def gemini_client():
    from google import genai

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set (it is read from .env)")
    return genai.Client(api_key=key)  # explicit, as outline.py does: a bare Client() may take GOOGLE_API_KEY


def uploaded_video(client, video: Path, rec_path: Path | None = None) -> tuple[str, str, dict]:
    """The uploaded file's (uri, mime_type, stats). The handle is kept in <out>/upload.json (default
    runs/compare-gemini/) and reused by every call of every arm while it is still ACTIVE on the server; otherwise the
    video is uploaded again."""
    rec_path = OUT / "upload.json" if rec_path is None else rec_path
    rec_path.parent.mkdir(parents=True, exist_ok=True)
    if rec_path.exists():
        rec = json.loads(rec_path.read_text())
        try:
            f = client.files.get(name=rec["name"])
            if f.state is not None and f.state.name == "ACTIVE":
                return f.uri, f.mime_type, rec
        except Exception as e:  # expired or deleted: upload again
            log.info("stored upload not usable (%s); uploading again", e)
    t0 = time.perf_counter()
    f = client.files.upload(file=str(video))
    while f.state is None or f.state.name != "ACTIVE":
        if f.state is not None and f.state.name == "FAILED":
            raise RuntimeError(f"Gemini could not process the uploaded video: {f.error}")
        if time.perf_counter() - t0 > UPLOAD_TIMEOUT_S:
            raise RuntimeError(f"the uploaded video was not ACTIVE after {UPLOAD_TIMEOUT_S} s")
        time.sleep(3)
        f = client.files.get(name=f.name)
    rec = {"name": f.name, "uri": f.uri, "mime_type": f.mime_type, "video": str(video),
           "upload_and_processing_s": round(time.perf_counter() - t0, 1), "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    rec_path.write_text(json.dumps(rec, indent=1))
    log.info("uploaded %s in %.1f s", video.name, rec["upload_and_processing_s"])
    return f.uri, f.mime_type, rec


def gemini_request(uri: str, mime_type: str, prompt: str, model: str = GEMINI_MODEL) -> dict:
    """The same call shape as outline.build_request (a video block with processing="agentic", then the text), without
    the JSON schema: the answers are prose."""
    return {"model": model,
            "input": [{"type": "video", "uri": uri, "mime_type": mime_type, "processing": "agentic"}, {"type": "text", "text": prompt}]}


def gemini_call(client, request: dict) -> dict:
    """One interactions.create; returns text, usage by kind, dollars at list price, seconds, steps and status. Raises on
    an exception or a status other than completed (the caller retries once)."""
    t0 = time.perf_counter()
    interaction = client.interactions.create(**request, timeout=CALL_TIMEOUT_S)
    seconds = round(time.perf_counter() - t0, 1)
    if interaction.status != "completed":
        raise RuntimeError(f"interaction status {interaction.status!r}: {interaction.errors}")
    raw_usage = interaction.usage.model_dump(exclude_none=True) if interaction.usage else {}
    tokens = usage_by_kind(raw_usage)
    tokens["cached"] = raw_usage.get("total_cached_tokens") or 0
    return {"text": interaction.output_text or "", "tokens": tokens, "raw_usage": raw_usage,
            "dollars": list_price_cost(tokens, request["model"]), "seconds": seconds,
            "steps": [s.type for s in interaction.steps or []], "interaction_id": interaction.id, "status": interaction.status}


def gemini_call_with_retry(client, request: dict, label: str) -> tuple[dict | None, list[str]]:
    """Call; on failure retry once; returns (result or None, the failure messages)."""
    failures: list[str] = []
    for attempt in (1, 2):
        try:
            return gemini_call(client, request), failures
        except Exception as e:
            msg = f"{label} attempt {attempt}: {type(e).__name__}: {str(e)[:400]}"
            log.warning(msg)
            failures.append(msg)
    return None, failures


def run_threads(items: list, fn, concurrency: int) -> list:
    """fn(item) on at most `concurrency` threads; results in item order."""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        return list(pool.map(fn, items))


class Ledger:
    """Appends every call's dollars and outcome to runs/compare-gemini/spend.jsonl (one line per call), so the cap of
    $15 on the whole comparison can be checked at any time with `python -m compare.gemini.spend`."""

    def __init__(self, path: Path | None = None):
        self.path = OUT / "spend.jsonl" if path is None else path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def add(self, vendor: str, arm: str, label: str, dollars: float | None, seconds: float, ok: bool, note: str = "") -> None:
        row = {"vendor": vendor, "arm": arm, "label": label, "dollars": dollars, "seconds": seconds, "ok": ok, "note": note,
               "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        with self.lock, self.path.open("a") as f:
            f.write(json.dumps(row) + "\n")

    def total(self) -> dict:
        by = {}
        for r in read_jsonl(self.path):
            v = by.setdefault(r["vendor"], {"dollars": 0.0, "calls": 0, "failed": 0})
            v["dollars"] += r["dollars"] or 0.0
            v["calls"] += 1
            v["failed"] += 0 if r["ok"] else 1
        return by


def answer_record(q: Question, res: dict | None, failures: list[str], model: str, extra: dict | None = None) -> Answer:
    """A scry Answer (what the judge grades) for a question."""
    if res is None:
        return Answer(qid=q.id, key=q.key, polarity=q.polarity, question=q.question, answer="", error="; ".join(failures)[:500],
                      model=model, usage=extra or {})
    return Answer(qid=q.id, key=q.key, polarity=q.polarity, question=q.question, answer=res["text"], model=model,
                  usage=res.get("tokens") or res.get("usage") or {}, dollars=res["dollars"] or 0.0, seconds=res["seconds"],
                  prompt=extra.get("prompt") if extra else None, stop=res.get("status"),
                  calls=[{"interaction_id": res.get("interaction_id"), "steps": res.get("steps"), "retries": failures}] if res.get("interaction_id") else [])


__all__ = ["LIST_PRICES", "GEMINI_MODEL", "OPUS_MODEL", "OUT", "REPO", "MAIN", "ANSWER_INSTRUCTION"]
