from __future__ import annotations

import json
import logging
from pathlib import Path

from vt.config import Config
from vt.index import get_embedder, open_db, search as _search
from vt.prompts import agent as agent_prompt
from vt.providers.base import image_block, text_block
from vt.run import Run

log = logging.getLogger(__name__)

TOOL_DEFS = [
    {"name": "search", "description": "Search the visual-transcript index (lexical + substring; vector if configured). Returns ranked nodes with frames, times and text.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "level": {"type": "string", "description": "region|frame|transition|step|section|video|chapter"},
                                                        "t_from": {"type": "number"}, "t_to": {"type": "number"}, "app": {"type": "string"}}, "required": ["query"]}},
    {"name": "get_node", "description": "Fetch one node in full by node_id (payload includes lines with agree flags for regions, or the transition and its interpretation).",
     "input_schema": {"type": "object", "properties": {"node_id": {"type": "string"}}, "required": ["node_id"]}},
    {"name": "get_transitions", "description": "List transitions whose time window overlaps [t_a, t_b] seconds, with their events and interpretations.",
     "input_schema": {"type": "object", "properties": {"t_a": {"type": "number"}, "t_b": {"type": "number"}}, "required": ["t_a", "t_b"]}},
    {"name": "get_frame", "description": "Return the PNG of an emitted frame as an image, with its time.",
     "input_schema": {"type": "object", "properties": {"frame": {"type": "integer"}}, "required": ["frame"]}},
    {"name": "redecode", "description": "Re-decode the source video between t_a and t_b seconds at the given fps and return up to 6 frames as images (recovery tool).",
     "input_schema": {"type": "object", "properties": {"t_a": {"type": "number"}, "t_b": {"type": "number"}, "fps": {"type": "number", "default": 2}}, "required": ["t_a", "t_b"]}},
]


class Tools:
    def __init__(self, run: Run, cfg: Config):
        self.run, self.cfg = run, cfg
        self.db = open_db(run.index_db)
        self.embedder = get_embedder(cfg.index)

    def search(self, query: str, level: str | None = None, t_from: float | None = None, t_to: float | None = None, app: str | None = None) -> dict:
        hits = _search(self.db, query, self.cfg.index, self.embedder, level=level, t_from=t_from, t_to=t_to, app=app)
        return {"hits": [{k: v for k, v in h.items() if k != "payload"} for h in hits]}

    def get_node(self, node_id: str) -> dict:
        row = self.db.execute("SELECT level, item_id, frame_start, frame_end, t_start, t_end, text, payload FROM nodes WHERE node_id = ?", (node_id,)).fetchone()
        if not row:
            return {"error": "no such node"}
        return {"node_id": node_id, "level": row[0], "item_id": row[1], "frames": [row[2], row[3]], "t": [row[4], row[5]], "text": row[6], "payload": json.loads(row[7])}

    def get_transitions(self, t_a: float, t_b: float) -> dict:
        interps = self.run.load_interpretations()
        out = []
        for t in self.run.load_transitions():
            if t.t[1] >= t_a and t.t[0] <= t_b:
                ip = interps.get(t.id)
                out.append({"id": t.id, "frames": [t.from_frame, t.to_frame], "t": list(t.t), "kind": t.kind,
                            "events": [e.model_dump() for e in t.events], "action": ip.action if ip else None, "result": ip.result if ip else None})
        return {"transitions": out}

    def get_frame(self, frame: int) -> list[dict]:
        rec = next((f for f in self.run.load_stage1() if f.frame == frame), None)
        if rec is None:
            return [text_block("no such frame")]
        return [text_block(f"Frame {frame} (t={rec.t_settled:.2f}s):"), image_block(self.run.root / rec.png)]

    def redecode(self, t_a: float, t_b: float, fps: float = 2.0) -> list[dict]:
        from vt.decode import iter_frames

        video = Path(self.run.manifest_read()["video"])
        blocks: list[dict] = []
        next_t = t_a
        tmp = self.run.root / "redecode"
        tmp.mkdir(exist_ok=True)
        for df in iter_frames(video, start=t_a):  # seeks to the keyframe before t_a instead of decoding from 0
            if df.t > t_b or len(blocks) >= 12:
                break
            if df.t >= next_t:
                p = tmp / f"{df.t:09.3f}.png"
                df.frame.to_image().save(p, format="PNG", compress_level=1)
                blocks += [text_block(f"t={df.t:.2f}s:"), image_block(p)]
                next_t += 1.0 / fps
        return blocks or [text_block("no frames in range")]


def _dispatch(tools: Tools, name: str, args: dict):
    fn = getattr(tools, name)
    return fn(**args)


def ask(run: Run, cfg: Config, question: str, client=None, max_turns: int = 12) -> str:
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    tools = Tools(run, cfg)
    messages = [{"role": "user", "content": question}]
    for _ in range(max_turns):
        resp = client.messages.create(model=cfg.model.model, max_tokens=16000, system=agent_prompt.SYSTEM, tools=TOOL_DEFS,
                                      output_config={"effort": cfg.model.effort_agent}, messages=messages)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            if resp.stop_reason in ("refusal", "max_tokens") and not text.strip():
                return f"No answer: the model stopped with {resp.stop_reason}."
            return text
        results = []
        for b in resp.content:
            if getattr(b, "type", "") != "tool_use":
                continue
            try:
                out = _dispatch(tools, b.name, dict(b.input))
                content = out if isinstance(out, list) else json.dumps(out, default=str)[:60000]
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": content})
            except Exception as e:  # tool errors go back to the model, never abort the loop
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": f"error: {e}", "is_error": True})
        messages.append({"role": "user", "content": results})
    return "Stopped after too many tool calls without a final answer."
