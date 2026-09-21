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


# The families of entries: each is ranked on its own and the rankings are fused, because BM25's length normalisation
# ranks a one-line lifetime entry above a whole-screen entry of a hundred lines for the same term. The order breaks ties.
FAMILIES = (("lifetime", ("lifetime",)), ("transition", ("transition",)), ("frame", ("frame",)),
            ("summary", ("step", "section", "video", "chapter")))
_FAMILY_OF = {level: k for k, (_, levels) in enumerate(FAMILIES) for level in levels}


def matched_lines(text: str, terms: list[str]) -> tuple[str, ...]:
    """The lines of `text` that hold a query term as a case-folded substring; the whole text when none does. It is not
    faithful to either tokenizer and can see fewer lines than they matched."""
    folded = [t.casefold() for t in terms]
    lines = tuple(line for line in text.split("\n") if any(t in line.casefold() for t in folded))
    return lines or (text,)


def collapse_runs(hits: list[tuple[str, int, tuple[str, ...]]]) -> list[list[str]]:
    """(node id, ordinal, matched lines) in; runs of node ids out, each in frame order: a run is a maximal sequence of
    consecutive emitted frames whose matched lines are identical."""
    runs: list[list[str]] = []
    prev: tuple[int, tuple[str, ...]] | None = None
    for node_id, ordinal, matched in sorted(hits, key=lambda h: h[1]):
        if prev is not None and ordinal == prev[0] + 1 and matched == prev[1]:
            runs[-1].append(node_id)
        else:
            runs.append([node_id])
        prev = (ordinal, matched)
    return runs


_FRAME_COLUMNS = "n.node_id, n.text, json_extract(n.payload, '$.ordinal'), n.frame_start, n.t_start, n.t_end"


def search(db: sqlite3.Connection, query: str, cfg: IndexConfig, embedder: Embedder | None = None, video_id: str | None = None,
           level: str | None = None, t_from: float | None = None, t_to: float | None = None, app: str | None = None,
           collapse: bool | None = None) -> list[dict]:
    """Ranked hits. Identical consecutive frame hits are collapsed into one hit with a frame range and a time range, in
    this result list only: every entry stays in the index. It never raises for a query."""
    if level is not None and level not in _FAMILY_OF:  # no family holds it (the old `region`, say)
        return []
    filtered = any(v is not None for v in (video_id, level, t_from, t_to, app))
    k = cfg.k_filtered if filtered else cfg.k
    collapse = cfg.collapse if collapse is None else collapse
    where, params = _filter_sql(video_id, level, t_from, t_to, app)
    terms = _terms(query)
    rankings: list[list[str]] = []
    frame_rankings: list[list[str]] = []
    frame_info: dict[str, tuple] = {}  # node id -> (text, ordinal, frame, t_start, t_end)
    for family, levels in FAMILIES:
        if level is not None and level not in levels:
            continue
        unlimited = family == "frame" and collapse  # a run is recognised only with all its members present
        for table, q in (("nodes_fts", fts_query(query)), ("nodes_tri", trigram_query(query))):
            if not q:
                continue
            sql = (f"SELECT {_FRAME_COLUMNS} FROM {table} f JOIN nodes n ON n.node_id = f.node_id WHERE {table} MATCH ?{where} "
                   f"AND n.level IN ({','.join('?' * len(levels))}) ORDER BY bm25({table}), n.t_start, n.node_id"
                   + ("" if unlimited else " LIMIT ?"))
            try:
                rows = db.execute(sql, [q, *params, *levels, *([] if unlimited else [k])]).fetchall()
            except sqlite3.OperationalError:  # a query string SQLite rejects is an empty ranking
                rows = []
            rankings.append([r[0] for r in rows])
            if family == "frame":
                frame_rankings.append(rankings[-1])
                frame_info.update({r[0]: r[1:] for r in rows})
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
        for node_id in ids:  # a frame entry the lexical rankings did not return
            if node_id not in frame_info:
                row = db.execute(f"SELECT {_FRAME_COLUMNS} FROM nodes n WHERE n.node_id = ? AND n.level = 'frame'", (node_id,)).fetchone()
                if row:
                    frame_info[node_id] = row[1:]
    members = {node_id: [node_id] for node_id in frame_info}
    if collapse:
        runs = collapse_runs([(node_id, info[1], matched_lines(info[0], terms)) for node_id, info in frame_info.items()])
        first = {node_id: run[0] for run in runs for node_id in run}  # the representative is the earliest member
        members = {run[0]: run for run in runs}
        for ranking in rankings:  # the run takes its best member's rank
            ranking[:] = list(dict.fromkeys(first.get(node_id, node_id) for node_id in ranking))
        for ranking in frame_rankings:
            del ranking[k:]
    rows = {}
    for node_id, score in rrf(rankings, cfg.rrf):
        row = db.execute("SELECT node_id, video_id, level, item_id, frame_start, frame_end, t_start, t_end, apps, containers, text, payload "
                         "FROM nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row:
            rows[node_id] = (round(score, 5), row)
    # the rounded score is the value the hit carries, so a difference in the last bit of a sum cannot reorder a tie
    order = sorted(rows, key=lambda i: (-rows[i][0], _FAMILY_OF.get(rows[i][1][2], len(FAMILIES)), rows[i][1][6], i))[:k]
    out = []
    for node_id in order:
        score, row = rows[node_id]
        hit = {"node_id": row[0], "video_id": row[1], "level": row[2], "item_id": row[3], "frames": [row[4], row[5]],
               "t": [row[6], row[7]], "apps": json.loads(row[8]), "containers": json.loads(row[9]), "text": row[10],
               "payload": json.loads(row[11]), "score": score}
        if row[2] == "frame":
            run = [frame_info[m] for m in members[node_id]]
            hit |= {"collapsed": len(run), "members": [info[2] for info in run], "matched": list(matched_lines(row[10], terms)),
                    "frames": [run[0][2], run[-1][2]], "t": [run[0][3], run[-1][4]]}
        out.append(hit)
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
