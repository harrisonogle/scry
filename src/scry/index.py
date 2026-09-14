from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from scry.config import Config, IndexConfig, config_hash
from scry.run import Run

log = logging.getLogger(__name__)


class Node(BaseModel):
    node_id: str
    video_id: str
    level: str
    item_id: str
    frames: tuple[int, int]
    t: tuple[float, float]
    apps: list[str] = []
    region_names: list[str] = []
    layout_conf: float = 1.0
    step_id: str | None = None
    section_id: str | None = None
    chapter_id: str | None = None
    text: str
    payload: dict = {}


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastembedEmbedder:
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding

        self._m = TextEmbedding(model)
        self.dim = len(next(iter(self._m.embed(["x"]))))

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._m.embed(texts)]


def get_embedder(cfg: IndexConfig) -> Embedder | None:
    if cfg.embedder == "fastembed":
        return FastembedEmbedder()
    return None


# ---------- schema ----------
def open_db(path: Path) -> sqlite3.Connection:
    db = sqlite3.connect(str(path))
    try:
        import sqlite_vec

        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
    except Exception as e:  # vector search unavailable; lexical still works
        log.warning("sqlite-vec unavailable: %s", e)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS nodes (
            node_id TEXT PRIMARY KEY, video_id TEXT, level TEXT, item_id TEXT, frame_start INTEGER, frame_end INTEGER,
            t_start REAL, t_end REAL, apps TEXT, region_names TEXT, layout_conf REAL, step_id TEXT, section_id TEXT,
            chapter_id TEXT, text TEXT, payload TEXT);
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(text, node_id UNINDEXED, tokenize="unicode61 tokenchars '-_./:\\'");
        CREATE VIRTUAL TABLE IF NOT EXISTS nodes_tri USING fts5(text, node_id UNINDEXED, tokenize='trigram');
        """
    )
    return db


def _ensure_vec(db: sqlite3.Connection, dim: int) -> None:
    db.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS nodes_vec USING vec0(node_id TEXT PRIMARY KEY, embedding float[{dim}], level TEXT, video_id TEXT)")


def index_nodes(db: sqlite3.Connection, nodes: list[Node], embedder: Embedder | None) -> None:
    db.execute("DELETE FROM nodes")
    db.execute("DELETE FROM nodes_fts")
    db.execute("DELETE FROM nodes_tri")
    for n in nodes:
        db.execute("INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (n.node_id, n.video_id, n.level, n.item_id, n.frames[0], n.frames[1], n.t[0], n.t[1], json.dumps(n.apps),
                    json.dumps(n.region_names), n.layout_conf, n.step_id, n.section_id, n.chapter_id, n.text, json.dumps(n.payload)))
        db.execute("INSERT INTO nodes_fts(text, node_id) VALUES (?, ?)", (n.text, n.node_id))
        db.execute("INSERT INTO nodes_tri(text, node_id) VALUES (?, ?)", (n.text, n.node_id))
    if embedder is not None and nodes:
        import sqlite_vec

        _ensure_vec(db, embedder.dim)
        db.execute("DELETE FROM nodes_vec")
        for n, vec in zip(nodes, embedder.embed([n.text for n in nodes])):
            db.execute("INSERT INTO nodes_vec(node_id, embedding, level, video_id) VALUES (?,?,?,?)",
                       (n.node_id, sqlite_vec.serialize_float32(vec), n.level, n.video_id))
    db.commit()


# ---------- queries (§14.2) ----------
_TERM = re.compile(r'"([^"]+)"|(\S+)')


def _terms(query: str) -> list[str]:
    return [(a or b) for a, b in _TERM.findall(query)]


def fts_query(query: str) -> str:
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in _terms(query))


def trigram_query(query: str) -> str | None:
    terms = [t for t in _terms(query) if len(t) >= 3]
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in terms) if terms else None


def rrf(rankings: list[list[str]], k: int) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, node_id in enumerate(ranking, start=1):
            scores[node_id] = scores.get(node_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: -kv[1])


def _filter_sql(video_id, level, t_from, t_to, app) -> tuple[str, list]:
    clauses, params = [], []
    if video_id:
        clauses.append("n.video_id = ?")
        params.append(video_id)
    if level:
        clauses.append("n.level = ?")
        params.append(level)
    if t_from is not None:
        clauses.append("n.t_end >= ?")
        params.append(t_from)
    if t_to is not None:
        clauses.append("n.t_start <= ?")
        params.append(t_to)
    if app:
        clauses.append("n.apps LIKE ?")
        params.append(f"%{app}%")
    return (" AND " + " AND ".join(clauses)) if clauses else "", params


def search(db: sqlite3.Connection, query: str, cfg: IndexConfig, embedder: Embedder | None = None, video_id: str | None = None,
           level: str | None = None, t_from: float | None = None, t_to: float | None = None, app: str | None = None) -> list[dict]:
    filtered = any(v is not None for v in (video_id, level, t_from, t_to, app))
    k = cfg.k_filtered if filtered else cfg.k
    where, params = _filter_sql(video_id, level, t_from, t_to, app)
    rankings: list[list[str]] = []
    q = fts_query(query)
    if q:
        rows = db.execute(f"SELECT f.node_id FROM nodes_fts f JOIN nodes n ON n.node_id = f.node_id WHERE nodes_fts MATCH ?{where} ORDER BY bm25(nodes_fts) LIMIT ?",
                          [q, *params, k]).fetchall()
        rankings.append([r[0] for r in rows])
    tq = trigram_query(query)
    if tq:
        rows = db.execute(f"SELECT f.node_id FROM nodes_tri f JOIN nodes n ON n.node_id = f.node_id WHERE nodes_tri MATCH ?{where} ORDER BY bm25(nodes_tri) LIMIT ?",
                          [tq, *params, k]).fetchall()
        rankings.append([r[0] for r in rows])
    if embedder is not None:
        import sqlite_vec

        vec = sqlite_vec.serialize_float32(embedder.embed([query])[0])
        vwhere = " AND ".join(c for c in ["level = ?" if level else "", "video_id = ?" if video_id else ""] if c)
        vparams = [p for p, c in ((level, level), (video_id, video_id)) if c]
        rows = db.execute(f"SELECT node_id FROM nodes_vec WHERE embedding MATCH ? AND k = ?{(' AND ' + vwhere) if vwhere else ''} ORDER BY distance",
                          [vec, k, *vparams]).fetchall()
        ids = [r[0] for r in rows]
        if t_from is not None or t_to is not None or app:
            keep = {r[0] for r in db.execute(f"SELECT n.node_id FROM nodes n WHERE 1=1{where}", params).fetchall()}
            ids = [i for i in ids if i in keep]
        rankings.append(ids)
    fused = rrf(rankings, cfg.rrf)[:k]
    out = []
    for node_id, score in fused:
        row = db.execute("SELECT node_id, video_id, level, item_id, frame_start, frame_end, t_start, t_end, apps, layout_conf, text, payload FROM nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row:
            out.append({"node_id": row[0], "video_id": row[1], "level": row[2], "item_id": row[3], "frames": [row[4], row[5]],
                        "t": [row[6], row[7]], "apps": json.loads(row[8]), "layout_conf": row[9], "text": row[10],
                        "payload": json.loads(row[11]), "score": round(score, 5)})
    return out


# ---------- node extraction (§14.1) ----------
def extract_nodes(run: Run) -> list[Node]:
    vid = run.video_id
    frames = run.load_frames()
    ts = run.load_transitions()
    interps = run.load_interpretations()
    from scry.jsonl import read_jsonl
    from scry.schemas import HierNode

    steps = read_jsonl(run.steps, HierNode)
    sections = read_jsonl(run.sections, HierNode)

    def _rng_lookup(nodes: list[HierNode], child_ids: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for n in nodes:
            a, b = n.children
            inside = False
            for cid in child_ids:
                if cid == a:
                    inside = True
                if inside:
                    out[cid] = n.id
                if cid == b:
                    inside = False
        return out

    t_ids = [t.id for t in ts]
    step_of = _rng_lookup(steps, t_ids)
    section_of_step = _rng_lookup(sections, [s.id for s in steps])
    nodes: list[Node] = []
    for f in frames:
        chapter = run.chapter_of(f.t_settled)
        for r in f.regions:
            text = "\n".join(l.fused for l in r.lines if l.fused)
            text += "".join(f"\n{l.vlm}" for l in r.lines if l.agree is False and l.vlm)  # index both readings (§14.1)
            if not text.strip():
                continue
            nodes.append(Node(node_id=f"{vid}:f{f.frame}:{r.id}", video_id=vid, level="region", item_id=f"{f.frame}:{r.id}",
                              frames=(f.frame, f.frame), t=(f.t_settled, f.t_end), apps=[r.app], region_names=[r.name],
                              layout_conf=r.layout_conf, chapter_id=chapter.id if chapter else None, text=f"{r.app} {r.name}\n{text}",
                              payload={"frame": f.frame, "region": r.id, "lines": [l.model_dump() for l in r.lines]}))
        if f.description:
            nodes.append(Node(node_id=f"{vid}:f{f.frame}:desc", video_id=vid, level="frame", item_id=str(f.frame), frames=(f.frame, f.frame),
                              t=(f.t_settled, f.t_end), apps=sorted({r.app for r in f.regions}), text=f.description,
                              chapter_id=chapter.id if chapter else None, payload={"frame": f.frame}))
    for t in ts:
        ip = interps.get(t.id)
        b = next((f for f in frames if f.frame == t.to_frame), None)
        ev = "; ".join(f'{e.type} {e.text or ""}'.strip() for e in t.events)
        text = " \n".join(x for x in [ev, ip.action if ip else "", ip.result if ip else ""] if x)
        if not text:
            text = " ".join((o.new or o.old or "") for rd in t.computed_diff.values() for o in rd.ops)
        chapter = run.chapter_of(b.t_settled) if b else None
        nodes.append(Node(node_id=f"{vid}:{t.id}", video_id=vid, level="transition", item_id=t.id, frames=(t.from_frame, t.to_frame), t=t.t,
                          apps=sorted({r.app for r in (b.regions if b else [])}), step_id=step_of.get(t.id),
                          section_id=section_of_step.get(step_of.get(t.id, ""), None), chapter_id=chapter.id if chapter else None,
                          text=text, payload={"transition": t.model_dump(), "interpretation": ip.model_dump() if ip else None}))
    for s in steps:
        nodes.append(Node(node_id=f"{vid}:{s.id}", video_id=vid, level="step", item_id=s.id, frames=s.frames, t=s.t, step_id=s.id,
                          section_id=section_of_step.get(s.id), text=f"{s.label}\n{s.description}", payload=s.model_dump()))
    for c in sections:
        nodes.append(Node(node_id=f"{vid}:{c.id}", video_id=vid, level="section", item_id=c.id, frames=c.frames, t=c.t, section_id=c.id,
                          text=f"{c.label}\n{c.description}", payload=c.model_dump()))
    if run.video.exists():
        v = HierNode.model_validate_json(run.video.read_text())
        nodes.append(Node(node_id=f"{vid}:V", video_id=vid, level="video", item_id="V", frames=v.frames, t=v.t, text=f"{v.label}\n{v.description}", payload=v.model_dump()))
    for c in run.load_outline():
        nodes.append(Node(node_id=f"{vid}:{c.id}", video_id=vid, level="chapter", item_id=c.id, frames=(0, 0), t=(c.start_s, c.end_s),
                          chapter_id=c.id, text=f"{c.title}\n{c.gist}", payload=c.model_dump()))
    return nodes


def build_index(run: Run, cfg: Config) -> None:
    inputs = [run.frames, run.transitions, run.interpretations, run.steps, run.sections]
    ch = config_hash(cfg, "index")
    if run.stage_up_to_date("index", inputs, ch):
        log.info("index up to date")
        return
    nodes = extract_nodes(run)
    if run.index_db.exists():
        run.index_db.unlink()
    db = open_db(run.index_db)
    index_nodes(db, nodes, get_embedder(cfg.index))
    db.close()
    run.stage_done("index", inputs, ch, nodes=len(nodes), embedder=cfg.index.embedder)
