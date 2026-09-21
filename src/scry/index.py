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
    containers: list[str] = []  # names
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
            t_start REAL, t_end REAL, apps TEXT, containers TEXT, step_id TEXT, section_id TEXT, chapter_id TEXT, text TEXT,
            payload TEXT);
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
        db.execute("INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (n.node_id, n.video_id, n.level, n.item_id, n.frames[0], n.frames[1], n.t[0], n.t[1], json.dumps(n.apps),
                    json.dumps(n.containers), n.step_id, n.section_id, n.chapter_id, n.text, json.dumps(n.payload)))
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
        row = db.execute("SELECT node_id, video_id, level, item_id, frame_start, frame_end, t_start, t_end, apps, containers, text, payload FROM nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row:
            out.append({"node_id": row[0], "video_id": row[1], "level": row[2], "item_id": row[3], "frames": [row[4], row[5]],
                        "t": [row[6], row[7]], "apps": json.loads(row[8]), "containers": json.loads(row[9]), "text": row[10],
                        "payload": json.loads(row[11]), "score": round(score, 5)})
    return out


# ---------- the stage ----------
def build_index(run: Run, cfg: Config) -> None:
    """index.sqlite, rebuilt from scratch from whatever records the run has."""
    inputs = [run.frames, run.boxes, run.changes, run.lifetimes, run.annotations, run.interpretations, run.steps, run.sections,
              run.video, run.outline]
    ch = config_hash(cfg, "index")
    if run.stage_up_to_date("index", inputs, ch):
        log.info("index up to date")
        return
    from scry.nodes import extract_nodes  # nodes imports Node from here

    nodes, stats = extract_nodes(run)
    run.index_db.unlink(missing_ok=True)
    db = open_db(run.index_db)
    index_nodes(db, nodes, get_embedder(cfg.index))
    db.close()
    run.stage_done("index", inputs, ch, **stats, embedder=cfg.index.embedder)
