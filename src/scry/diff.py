from __future__ import annotations

import statistics

from scry.config import DiffConfig
from scry.correspond import correspond
from scry.schemas import DiffOp, FrameRecord, Line, RegionDiff, Transition
from scry.textdiff import line_ops, pair_modifies


def _ys(lines: list[Line]) -> list[int]:
    ys: list[int] = []
    last = 0
    for l in lines:
        if l.bbox is not None:
            last = l.bbox[1]
        ys.append(last)
    return ys


def _line_h(lines: list[Line]) -> float:
    hs = [l.bbox[3] - l.bbox[1] for l in lines if l.bbox]
    return float(statistics.median(hs)) if hs else 16.0


def diff_region(prev: list[Line], cur: list[Line], cfg: DiffConfig) -> list[DiffOp]:
    p = [l.fused for l in prev]
    c = [l.fused for l in cur]
    ops = pair_modifies(line_ops(p, c), _ys(prev), _ys(cur), _line_h(prev + cur), cfg.modify_sim)
    for o in ops:
        src = []
        if o.old_index is not None:
            src.append(prev[o.old_index])
        if o.new_index is not None:
            src.append(cur[o.new_index])
        o.uncertain = any(l.uncertain for l in src)
        o.in_churn = any(bool(l.in_churn) for l in src)
    return ops


def diff_pair(prev: FrameRecord, cur: FrameRecord, cfg: DiffConfig) -> Transition:
    corr = correspond(prev, cur, cfg)
    computed: dict[str, RegionDiff] = {}
    for a, b, _ in corr.matched:
        ops = diff_region(prev.region(a).lines, cur.region(b).lines, cfg)
        if ops:
            computed[b] = RegionDiff(from_region=a, ops=ops)
    r0 = diff_region(prev.unassigned_lines, cur.unassigned_lines, cfg)
    if r0:
        computed["r0"] = RegionDiff(from_region="r0", ops=r0)
    kind = "unsettled" if not (prev.settled and cur.settled) else "single"
    return Transition(id="", from_frame=prev.frame, to_frame=cur.frame, t=(prev.t_end, cur.t_settled), kind=kind,
                      regions=corr, computed_diff=computed)
