from __future__ import annotations

from vt.config import DiffConfig
from vt.detect import iou
from vt.schemas import Correspondence, FrameRecord, Region
from vt.textdiff import norm


def _texts(r: Region) -> set[str]:
    return {norm(l.fused) for l in r.lines if l.fused}


def score(a: Region, b: Region, cfg: DiffConfig) -> float:
    ta, tb = _texts(a), _texts(b)
    j = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0  # containment, not Jaccard: growth must not break a match (§11.1)
    i = iou(a.bbox, b.bbox) if a.bbox and b.bbox else 0.0
    app = float(norm(a.app).lower() == norm(b.app).lower())
    name = float(norm(a.name).lower() == norm(b.name).lower())
    return cfg.corr_w_text * j + cfg.corr_w_iou * i + cfg.corr_w_app * app + cfg.corr_w_name * name


def correspond(prev: FrameRecord, cur: FrameRecord, cfg: DiffConfig) -> Correspondence:
    pa = [r for r in prev.regions if r.lines]
    pb = [r for r in cur.regions if r.lines]
    pairs = sorted(((score(a, b, cfg), a.id, b.id) for a in pa for b in pb), reverse=True)
    used_a: set[str] = set()
    used_b: set[str] = set()
    matched: list[tuple[str, str, float]] = []
    for s, ia, ib in pairs:
        if s < cfg.corr_accept or ia in used_a or ib in used_b:
            continue
        matched.append((ia, ib, round(s, 3)))
        used_a.add(ia)
        used_b.add(ib)
    ea = [r for r in prev.regions if not r.lines]
    eb = [r for r in cur.regions if not r.lines]
    for a in ea:
        for b in eb:
            if b.id in used_b:
                continue
            if norm(a.app).lower() == norm(b.app).lower() and norm(a.name).lower() == norm(b.name).lower():
                matched.append((a.id, b.id, 1.0))
                used_a.add(a.id)
                used_b.add(b.id)
                break
    matched.sort(key=lambda m: m[1])
    disappeared = [r.id for r in prev.regions if r.id not in used_a]
    appeared = [r.id for r in cur.regions if r.id not in used_b]
    return Correspondence(matched=matched, appeared=appeared, disappeared=disappeared)
