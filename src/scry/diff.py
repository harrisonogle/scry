from __future__ import annotations

import statistics
from pathlib import Path

import av
import numpy as np
from PIL import Image

from scry.config import DetectParams, DiffConfig
from scry.correspond import correspond
from scry.detect import change_map, components
from scry.schemas import BBox, DiffOp, FrameRecord, Line, PixelChange, RegionDiff, Transition
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


# ---------- §11.2 pixel gate ----------
class PixelSource:
    """Changed pixels between two emitted frames: Stage 1's change map and components (`[stage1.detect]` θpix, θmin) over
    the two PNGs at full resolution, gray obtained through the same swscale path the decoder uses (within ±1 level of the
    decode-time gray). Recent grays are kept for the consecutive pairs and the occasional coalesced rebuild."""

    def __init__(self, root: Path, detect: DetectParams):
        self.root = Path(root)
        self.detect = detect
        self._gray: dict[int, np.ndarray] = {}

    def gray(self, f: FrameRecord) -> np.ndarray | None:
        g = self._gray.get(f.frame)
        if g is None:
            path = self.root / f.png
            if not f.png or not path.is_file():
                return None
            rgb = np.asarray(Image.open(path).convert("RGB"))
            g = av.VideoFrame.from_ndarray(rgb, format="rgb24").to_ndarray(format="gray")
            self._gray[f.frame] = g
            while len(self._gray) > 8:
                del self._gray[next(iter(self._gray))]
        return g

    def change(self, prev: FrameRecord, cur: FrameRecord) -> PixelChange | None:
        a, b = self.gray(prev), self.gray(cur)
        if a is None or b is None or a.shape != b.shape:
            return None
        cm = change_map(a, b, self.detect.theta_pix)
        comps = components(cm, self.detect.theta_min)
        return PixelChange(changed_fraction=round(float(cm.mean()), 6), components=[c.bbox for c in comps])


def _overlaps(a: BBox, b: BBox) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def is_gated(t: Transition, cfg: DiffConfig) -> bool:
    """The transition has pixel evidence and is near-static enough for the gate to apply (§11.2)."""
    return t.pixels is not None and 0 < cfg.pixel_gate_max_fraction and t.pixels.changed_fraction <= cfg.pixel_gate_max_fraction


def pixel_gate(t: Transition, prev: FrameRecord, cur: FrameRecord, cfg: DiffConfig) -> None:
    """Mark every op with whether its line's box (the new line for insert/modify, the old line for a delete) meets a
    changed-pixel component; on a near-static pair (changed_fraction ≤ pixel_gate_max_fraction) drop the ops that do not.
    Lines without a box are never vetoed. Runs inside diff_pair, so transients, coalescing and trivial tagging see the
    gated ops."""
    comps = t.pixels.components
    gate = is_gated(t, cfg)
    for unit, rd in list(t.computed_diff.items()):
        lb = cur.unassigned_lines if unit == "r0" else cur.unit_lines(unit)
        la = prev.unassigned_lines if unit == "r0" else prev.unit_lines(rd.from_region or unit)
        for o in rd.ops:
            line = lb[o.new_index] if o.new_index is not None else la[o.old_index]
            o.under_change = None if line.bbox is None else any(_overlaps(line.bbox, c) for c in comps)
        if gate:
            kept = [o for o in rd.ops if o.under_change is not False]
            t.pixels.vetoed += len(rd.ops) - len(kept)
            rd.ops = kept
            if not kept:
                del t.computed_diff[unit]


def diff_pair(prev: FrameRecord, cur: FrameRecord, cfg: DiffConfig, pixels: PixelSource | None = None) -> Transition:
    corr = correspond(prev, cur, cfg)
    computed: dict[str, RegionDiff] = {}
    for a, b, _ in corr.matched:  # units (§11.1); the pane a line came from rides along as metadata
        la, lb = prev.unit_line_sources(a), cur.unit_line_sources(b)
        ops = diff_region([l for l, _ in la], [l for l, _ in lb], cfg)
        for o in ops:
            src, unit = (lb[o.new_index][1], b) if o.new_index is not None else (la[o.old_index][1], a)
            o.pane = src if src != unit else None
        if ops:
            computed[b] = RegionDiff(from_region=a, ops=ops)
    r0 = diff_region(prev.unassigned_lines, cur.unassigned_lines, cfg)
    if r0:
        computed["r0"] = RegionDiff(from_region="r0", ops=r0)
    kind = "unsettled" if not (prev.settled and cur.settled) else "single"
    t = Transition(id="", from_frame=prev.frame, to_frame=cur.frame, t=(prev.t_end, cur.t_settled), kind=kind,
                   regions=corr, computed_diff=computed)
    if pixels is not None:
        t.pixels = pixels.change(prev, cur)
        if t.pixels is not None:
            pixel_gate(t, prev, cur, cfg)
    return t
