from __future__ import annotations

from scry.config import DiffConfig
from scry.detect import iou
from scry.merge import union
from scry.schemas import Correspondence, FrameRecord, Line, Region
from scry.textdiff import norm


def _texts(lines: list[Line]) -> set[str]:
    return {norm(l.fused) for l in lines if l.fused}


def score(a: Region, b: Region, la: list[Line], lb: list[Line], cfg: DiffConfig) -> float:
    """a and b are units; la and lb their unit line lists (§11.1)."""
    ta, tb = _texts(la), _texts(lb)
    j = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0  # containment, not Jaccard: growth must not break a match (§11.1)
    ba, bb = union([l.bbox for l in la]), union([l.bbox for l in lb])
    i = iou(ba, bb) if ba and bb else 0.0
    app = float(norm(a.app).lower() == norm(b.app).lower())
    name = float(norm(a.name).lower() == norm(b.name).lower())
    return cfg.corr_w_text * j + cfg.corr_w_iou * i + cfg.corr_w_app * app + cfg.corr_w_name * name


def correspond(prev: FrameRecord, cur: FrameRecord, cfg: DiffConfig) -> Correspondence:
    la = {u.id: prev.unit_lines(u.id) for u in prev.units()}
    lb = {u.id: cur.unit_lines(u.id) for u in cur.units()}
    pa = [u for u in prev.units() if la[u.id]]
    pb = [u for u in cur.units() if lb[u.id]]
    pairs = sorted(((score(a, b, la[a.id], lb[b.id], cfg), a.id, b.id) for a in pa for b in pb), reverse=True)
    used_a: set[str] = set()
    used_b: set[str] = set()
    matched: list[tuple[str, str, float]] = []
    for s, ia, ib in pairs:
        if s < cfg.corr_accept or ia in used_a or ib in used_b:
            continue
        matched.append((ia, ib, round(s, 3)))
        used_a.add(ia)
        used_b.add(ib)
    ea = [u for u in prev.units() if not la[u.id]]
    eb = [u for u in cur.units() if not lb[u.id]]
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
    disappeared = [u.id for u in prev.units() if u.id not in used_a]
    appeared = [u.id for u in cur.units() if u.id not in used_b]
    return Correspondence(matched=matched, appeared=appeared, disappeared=disappeared)
