"""`ask`: the answering agent. A manual tool loop over a run's index and records: lifetimes, changes, interpretations,
frames. The tools pass measurements on as measurements: none reports which window had focus, and none derives "was
run" from how long a text stayed on screen. Each call is a fresh conversation; no answer is cached and no file is
written except the frames `redecode` saves. Every request of the loop asks for the API's automatic prompt caching, so
the conversation so far is read from the cache on the next turn instead of being paid for again (L54). With `[ask]
frames = false` only the pixels are withheld, which is how an evaluation sees what the index itself holds: `redecode`,
which returns nothing but images, is not offered, and `get_frame` returns the same record of a frame without its image."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from pydantic import BaseModel

from scry.changetext import box_label, render_change_line
from scry.config import Config
from scry.costs import USAGE_KEYS, add_usage, estimate_cost
from scry.index import get_embedder, open_db, search as index_search
from scry.prompts.ask import GET_FRAME_WITHOUT_IMAGE, TOOL_DESCRIPTIONS, prompt_version, system_prompt
from scry.providers import image_block, text_block
from scry.run import Run
from scry.schemas import box_ref

log = logging.getLogger(__name__)

_NUMBER = {"type": "number"}
_SCHEMAS = {
    "search": {"type": "object", "required": ["query"],
               "properties": {"query": {"type": "string"},
                              "level": {"type": "string", "description": "lifetime|frame|transition|step|section|video|chapter"},
                              "t_from": _NUMBER, "t_to": _NUMBER, "app": {"type": "string"}}},
    "get_node": {"type": "object", "required": ["node_id"], "properties": {"node_id": {"type": "string"}}},
    "get_transitions": {"type": "object", "required": ["t_a", "t_b"], "properties": {"t_a": _NUMBER, "t_b": _NUMBER}},
    "get_frame": {"type": "object", "required": ["frame"], "properties": {"frame": {"type": "integer"}}},
    "redecode": {"type": "object", "required": ["t_a", "t_b"],
                 "properties": {"t_a": _NUMBER, "t_b": _NUMBER, "fps": {"type": "number", "default": 2}}},
}
TOOL_DEFS: list[dict] = [{"name": name, "description": TOOL_DESCRIPTIONS[name], "input_schema": schema} for name, schema in _SCHEMAS.items()]
IMAGES_ONLY = ("redecode",)  # a tool whose result is nothing but images; get_frame's holds a record and one image
CACHE_CONTROL = {"type": "ephemeral"}  # top-level: the API puts the breakpoint on the last cacheable block and moves it each turn


def tool_defs(frames: bool = True) -> list[dict]:
    """The tools the model is offered: all five as they stand; or, without frames, all but `redecode`, with `get_frame`
    described as what it then returns (a frame's record and no image)."""
    if frames:
        return TOOL_DEFS
    return [d | {"description": GET_FRAME_WITHOUT_IMAGE} if d["name"] == "get_frame" else d for d in TOOL_DEFS if d["name"] not in IMAGES_ONLY]


def hit_summary(hit: dict) -> dict:
    """A search hit as the agent sees it: never the payload; a frame hit shows its matching lines only."""
    out = {k: hit[k] for k in ("node_id", "level", "item_id", "frames", "t", "score", "text")}
    payload = hit["payload"]
    if hit["level"] == "frame":
        out |= {"text": "\n".join(hit["matched"]), "collapsed": hit["collapsed"]}
    elif hit["level"] == "lifetime":
        readers = payload["readers"]
        out |= {"sightings": payload["lifetime"]["sightings"], "unstable": payload["lifetime"]["unstable"],
                "seen_once": payload["seen_once"], "agree": payload["agree"],
                "readers": {"ocr": readers["ocr"]["text"], "vlm": readers["vlm"]["text"] if readers["vlm"] else None}}
    elif hit["level"] == "transition":
        ip = payload["interpretation"] or {}
        out |= {k: ip.get(k) for k in ("entered_text", "submitted", "confidence")}
    return out


class Tools:
    def __init__(self, run: Run, cfg: Config):
        if not run.index_db.exists():  # never create a file here
            raise FileNotFoundError(f"{run.index_db} does not exist: run `scry index {run.root}` first")
        self.run, self.cfg = run, cfg
        self.db = open_db(run.index_db)
        self.embedder = get_embedder(cfg.index)
        self.labels = run.load_labels()

    def search(self, query: str, level: str | None = None, t_from: float | None = None, t_to: float | None = None,
               app: str | None = None) -> dict:
        ignored = app is not None and self.labels is None  # every `apps` list is empty: a filter would hide everything
        hits = index_search(self.db, query, self.cfg.index, self.embedder, level=level, t_from=t_from, t_to=t_to,
                            app=None if ignored else app)
        out: dict = {"hits": [hit_summary(h) for h in hits]}
        if ignored:
            out["note"] = "app filter ignored: this run has no window labels"
        return out

    def get_node(self, node_id: str) -> dict:
        row = self.db.execute("SELECT level, item_id, frame_start, frame_end, t_start, t_end, text, payload FROM nodes WHERE node_id = ?",
                              (node_id,)).fetchone()
        if not row:
            return {"error": "no such node"}
        return {"node_id": node_id, "level": row[0], "item_id": row[1], "frames": [row[2], row[3]], "t": [row[4], row[5]],
                "text": row[6], "payload": json.loads(row[7])}

    def get_transitions(self, t_a: float, t_b: float) -> dict:
        interps = self.run.load_interpretations()
        vid = self.run.video_id
        out = []
        for c in self.run.load_changes():
            if c.t[1] >= t_a and c.t[0] <= t_b:
                ip = interps.get(c.id)
                out.append({"id": c.id, "node_id": f"{vid}:{c.id}", "frames": [c.from_frame, c.to_frame], "t": list(c.t), "kind": c.kind,
                            "summary": render_change_line(c), "action": ip.action if ip else None, "result": ip.result if ip else None,
                            "entered_text": ip.entered_text if ip else None, "submitted": ip.submitted if ip else None,
                            "confidence": ip.confidence if ip else None, "undoes": c.reverts.of if c.reverts is not None else None})
        return {"transitions": out}

    def get_frame(self, frame: int) -> list[dict]:
        rec = next((f for f in self.run.load_frames() if f.frame == frame), None)
        if rec is None:
            return [text_block("no such frame")]
        boxes = {fb.frame: fb for fb in self.run.load_boxes()}
        lifetime_of = {ref: l for l in self.run.load_lifetimes() for ref in l.boxes}  # alive here: the lifetime holds a ref of this frame
        screen = self.labels.frame(frame) if self.labels is not None else None
        lines = [f"Frame {frame}, t={rec.t_settled:.2f}–{rec.t_end:.2f}s.",
                 f"Description in force: {screen.description}" if screen is not None and screen.description else "Description in force: none.",
                 "Texts alive at this frame (box, lifetime, text; when seen; notes):"]
        for b in (boxes[frame].boxes if frame in boxes else []):
            ref = box_ref(frame, b.id)
            life = lifetime_of[ref]
            line = f'{b.id} {life.id} "{b.text}" | seen {life.first.t:.1f}–{life.last.t:.1f}s in {life.sightings} frames'
            others = sorted((r for r in life.readings if r != b.text), key=lambda r: (-len(life.readings[r]), r))
            if others:
                line += " | other OCR readings: " + ", ".join(f'"{r}"' for r in others)
            label = self.labels.box(ref) if self.labels is not None else None
            if label is not None and label.agree is False and label.vlm:
                line += f' | model reads "{label.vlm}"'
            where = box_label(ref, self.labels, boxes)
            lines.append(line + (f" | {where}" if where else ""))
        lines += [f'{m.id} (no box) "{m.text}"' for m in (screen.missed if screen is not None else [])]
        record = text_block("\n".join(lines))
        if not self.cfg.ask.frames:  # only the pixels are withheld: the record is what it is with them
            return [record]
        png = self.run.root / rec.png  # at full resolution: the agent looks at a frame in order to read it
        return [record, image_block(png) if png.exists() else text_block("(the image file is missing)")]

    def redecode(self, t_a: float, t_b: float, fps: float = 2.0) -> list[dict]:
        from scry.video import iter_frames

        video = Path(self.run.manifest_read()["video"])
        out_dir = self.run.root / "redecode"
        out_dir.mkdir(exist_ok=True)
        blocks: list[dict] = []
        next_t = t_a
        for df in iter_frames(video, start=t_a):  # seeks to the keyframe before t_a instead of decoding from 0
            if df.t > t_b or len(blocks) >= 2 * self.cfg.ask.redecode_max_frames:
                break
            if df.t >= next_t:
                p = out_dir / f"{df.t:09.3f}.png"
                df.frame.to_image().save(p, format="PNG", compress_level=1)
                blocks += [text_block(f"t={df.t:.2f}s:"), image_block(p)]
                next_t += 1.0 / fps
        return blocks or [text_block("no frames in range")]


class ToolCall(BaseModel):
    """One tool call as the answer keeps it: what was asked and how much came back, never the results themselves, so
    a search that found nothing can be audited afterwards (ledger L57)."""
    name: str
    input: dict  # as the model gave it; for `search` the query and its filters
    results: int | None = None  # hits, transitions, decoded frames; a node or a frame: 1 or 0; None: the call failed
    error: str | None = None


class AskResult(BaseModel):
    text: str
    citations: list[str]  # read out of the answer's prose; a lifetime or transition id is kept only when the run has it
    turns: int  # the API calls that returned
    tool_calls: list[str]  # tool names in call order
    tool_log: list[ToolCall] = []  # the same calls with their inputs and result counts
    usage: dict
    cost_usd: float
    model: str
    prompt: str
    stop: str  # the last stop reason, or "max_turns" or "api_error"


_CITATION = re.compile(r"\b(\d+:[bm]\d+)\b|\b[Ff]rames?\s+(\d+)|\b([LT]\d+)\b")


def extract_citations(text: str, known: set[str] | None = None) -> list[str]:
    """Box and missed-text refs as they stand, frames as their numbers, and lifetime and transition ids (`L12`, `T7`) as
    they stand, in order of appearance, without repeats. A lifetime or transition id is kept only when it is in `known`
    (the ids of the run), because so short a pattern also matches other prose; None keeps them all. A range such as
    T3–T7 is its two ends."""
    found = (ref or frame or (item if known is None or item in known else "") for ref, frame, item in _CITATION.findall(text))
    return list(dict.fromkeys(c for c in found if c))


def _result_count(name: str, out) -> int:
    """How many things a tool returned: hits, transitions, a node (1 or 0), a frame (1 or 0), decoded frames."""
    if name == "search":
        return len(out["hits"])
    if name == "get_transitions":
        return len(out["transitions"])
    if name == "get_node":
        return 0 if "error" in out else 1
    if name == "get_frame":
        return 0 if out[0]["text"] == "no such frame" else 1  # a found frame starts with its record, with or without its image
    return sum(b["type"] == "image" for b in out)  # redecode


def _tool_result(tools: Tools, cfg: Config, block) -> tuple[dict, ToolCall]:
    """One tool call's result block and its record. A tool error goes back to the model and never ends the loop."""
    base = {"type": "tool_result", "tool_use_id": block.id}
    call = ToolCall(name=block.name, input=dict(block.input))
    if block.name not in _SCHEMAS or (block.name in IMAGES_ONLY and not cfg.ask.frames):  # a tool that was not offered
        call.error = "unknown tool"
        return base | {"content": f"error: unknown tool {block.name}", "is_error": True}, call
    try:
        out = getattr(tools, block.name)(**call.input)
    except Exception as e:
        call.error = f"{type(e).__name__}: {e}"[:200]
        return base | {"content": f"error: {e}", "is_error": True}, call
    call.results = _result_count(block.name, out)
    return base | {"content": out if isinstance(out, list) else json.dumps(out, default=str)[:cfg.ask.max_tool_result_chars]}, call


def ask(run: Run, cfg: Config, question: str, client=None) -> AskResult:
    """Answer one question over a run. A failed API call is returned in the result, never raised: one failed question
    must not crash a question set."""
    tools = Tools(run, cfg)
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    messages: list[dict] = [{"role": "user", "content": question}]
    system, offered = system_prompt(cfg.ask.frames), tool_defs(cfg.ask.frames)
    usage = add_usage({}, {})
    tool_calls: list[str] = []
    tool_log: list[ToolCall] = []
    turns = 0
    text, stop = f"Stopped after {cfg.ask.max_turns} turns without a final answer.", "max_turns"
    for _ in range(cfg.ask.max_turns):
        try:
            resp = client.messages.create(model=cfg.model.model, max_tokens=cfg.model.max_tokens, system=system, tools=offered,
                                          output_config={"effort": cfg.model.effort_ask}, cache_control=CACHE_CONTROL,
                                          messages=list(messages))
        except Exception as e:
            log.warning("ask: the API call failed: %s", e)
            text, stop = f"No answer: the API call failed ({type(e).__name__}: {e}).", "api_error"
            break
        turns += 1
        add_usage(usage, {k: getattr(resp.usage, k, 0) for k in USAGE_KEYS})
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            text, stop = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text"), str(resp.stop_reason)
            if not text.strip() and stop in ("refusal", "max_tokens"):
                text = f"No answer: the model stopped with {stop}."
            break
        calls = [b for b in resp.content if getattr(b, "type", "") == "tool_use"]
        tool_calls += [b.name for b in calls]
        results = [_tool_result(tools, cfg, b) for b in calls]
        tool_log += [call for _, call in results]
        messages.append({"role": "user", "content": [block for block, _ in results]})  # all results in one message
    known = {l.id for l in run.load_lifetimes()} | {c.id for c in run.load_changes()}
    return AskResult(text=text, citations=extract_citations(text, known), turns=turns, tool_calls=tool_calls, tool_log=tool_log, usage=usage,
                     cost_usd=estimate_cost(usage, cfg.model.model), model=cfg.model.model, prompt=prompt_version(cfg.ask.frames), stop=stop)
