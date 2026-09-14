from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from scry.config import BlinkParams, ChurnParams, DetectParams
from scry.schemas import BBox

_S8 = np.ones((3, 3), dtype=bool)


@dataclass(frozen=True)
class Component:
    area: int          # changed pixels before dilation
    bbox: BBox         # tight bbox of the changed pixels; x1/y1 exclusive


def scale_params(d: DetectParams, c: ChurnParams, b: BlinkParams, downsample: int) -> tuple[DetectParams, ChurnParams, BlinkParams]:
    """§16 half-resolution column: areas ×0.4, linear sizes ×0.5."""
    if downsample == 1:
        return d, c, b
    a = 0.4
    d2 = d.model_copy(update=dict(theta_min=max(2, round(d.theta_min * a)), theta_comp=round(d.theta_comp * a),
                                  theta_count=round(d.theta_count * a), bar_max_width=max(1, d.bar_max_width // 2 + 1),
                                  bar_min_height=d.bar_min_height // 2, bar_max_height=d.bar_max_height // 2))
    c2 = c.model_copy(update=dict(min_area=round(c.min_area / 4)))  # a region's area scales by 4 (§16: 400 → 100)
    b2 = b.model_copy(update=dict(max_w=b.max_w // 2, max_h=b.max_h // 2))
    return d2, c2, b2


def change_map(prev: np.ndarray, cur: np.ndarray, theta_pix: int) -> np.ndarray:
    return np.abs(cur.astype(np.int16) - prev.astype(np.int16)) > theta_pix


def reduce_2x2(changed: np.ndarray) -> np.ndarray:
    """§7.2 half-resolution mode: 2×2 max (any) of the full-resolution change map, so 1-px strokes survive; odd edges cropped."""
    h, w = changed.shape[0] // 2 * 2, changed.shape[1] // 2 * 2
    return changed[:h, :w].reshape(h // 2, 2, w // 2, 2).any(axis=(1, 3))


def components(changed: np.ndarray, theta_min: int) -> list[Component]:
    if int(changed.sum()) < theta_min:
        return []
    blobs = ndimage.binary_dilation(changed, structure=_S8)
    labels, n = ndimage.label(blobs, structure=_S8)
    if n == 0:
        return []
    areas = np.bincount(labels[changed], minlength=n + 1)
    tight = np.where(changed, labels, 0)
    objs = ndimage.find_objects(tight, max_label=n)
    out: list[Component] = []
    for lab in range(1, n + 1):
        a = int(areas[lab])
        sl = objs[lab - 1]
        if a < theta_min or sl is None:
            continue
        ys, xs = sl
        out.append(Component(a, (int(xs.start), int(ys.start), int(xs.stop), int(ys.stop))))
    return out


def is_bar(c: Component, p: DetectParams) -> bool:
    w = c.bbox[2] - c.bbox[0]
    h = c.bbox[3] - c.bbox[1]
    return w <= p.bar_max_width and p.bar_min_height <= h <= p.bar_max_height


def trigger(comps: list[Component], p: DetectParams) -> bool:
    if not comps:
        return False
    return any(c.area >= p.theta_comp for c in comps) or sum(c.area for c in comps) >= p.theta_count


def iou(a: BBox, b: BBox) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    if inter == 0:
        return 0.0
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua


@dataclass
class ChurnUpdate:
    regions: list[BBox]
    deactivated: bool
    t_last_change: float | None


class ChurnTracker:
    """§7.4: ring buffer of unmasked change maps, running per-pixel count, per-pixel hysteresis mask."""

    def __init__(self, shape: tuple[int, int], fps: float, p: ChurnParams):
        self.h, self.w = shape
        self.p = p
        self.n = max(2, int(round(p.window_s * fps)))
        self.warmup = min(self.n, max(2, int(round(fps))))  # need ~1 s of history before masking anything
        size = self.h * self.w
        self.ring = np.zeros((self.n, (size + 7) // 8), dtype=np.uint8)
        self.filled = 0
        self.pos = 0
        self.count = np.zeros(size, dtype=np.uint16)
        self.mask = np.zeros(size, dtype=bool)
        self.last_change = np.full(size, -1, dtype=np.int32)
        self.times: dict[int, float] = {}
        self.regions: list[BBox] = []
        self._leave_max = -1  # latest last_change index among pixels that left the mask since the last deactivation event

    @property
    def active(self) -> bool:
        return bool(self.regions)

    def update(self, changed: np.ndarray, frame_index: int, t: float) -> ChurnUpdate:
        flat = changed.ravel()
        size = flat.size
        if self.filled == self.n:
            old = np.unpackbits(self.ring[self.pos])[:size].astype(bool)
            self.count[old] -= 1
        else:
            self.filled += 1
        self.ring[self.pos] = np.packbits(flat)
        self.pos = (self.pos + 1) % self.n
        self.count[flat] += 1
        self.last_change[flat] = frame_index
        self.times[frame_index] = t
        if len(self.times) > self.n + 2:
            for k in [k for k in self.times if k < frame_index - self.n - 1]:
                del self.times[k]
        n = self.filled
        if n < self.warmup:
            return ChurnUpdate([], False, None)
        on = self.count > self.p.rho_on * n
        stay = self.mask & (self.count > self.p.rho_off * n)
        new_mask = on | stay
        leaving = self.mask & ~new_mask
        if leaving.any():
            self._leave_max = max(self._leave_max, int(self.last_change[leaving].max()))
        self.mask = new_mask
        before = len(self.regions)
        self.regions = self._regions(new_mask)
        # per-pixel hysteresis empties a region gradually; the event is "a region disappeared", dated by the last change
        # inside the pixels that left it (§7.4)
        deactivated = before > 0 and len(self.regions) < before
        t_last = None
        if deactivated:
            t_last = self.times.get(self._leave_max, t) if self._leave_max >= 0 else t
            self._leave_max = -1
        return ChurnUpdate(self.regions, deactivated, t_last)

    def _regions(self, mask: np.ndarray) -> list[BBox]:
        if not mask.any():
            return []
        m2 = mask.reshape(self.h, self.w)
        m2 = ndimage.binary_opening(m2, structure=_S8)
        m2 = ndimage.binary_dilation(m2, structure=np.ones((9, 9), dtype=bool))
        labels, k = ndimage.label(m2, structure=_S8)
        if k == 0:
            return []
        areas = np.bincount(labels.ravel(), minlength=k + 1)
        out: list[BBox] = []
        for lab, sl in enumerate(ndimage.find_objects(labels), start=1):
            if sl is None or areas[lab] < self.p.min_area:
                continue
            ys, xs = sl
            out.append((int(xs.start), int(ys.start), int(xs.stop), int(ys.stop)))
        return out

    def excludes(self, c: Component) -> bool:
        cx = (c.bbox[0] + c.bbox[2]) / 2
        cy = (c.bbox[1] + c.bbox[3]) / 2
        return any(x0 <= cx < x1 and y0 <= cy < y1 for x0, y0, x1, y1 in self.regions)


@dataclass
class Candidate:
    bbox: BBox
    times: list[float]
    last_seen: float
    confirmed: bool = False
    confirmed_at: float | None = None


@dataclass
class BlinkUpdate:
    excluded: set[int]
    newly_confirmed: list[Candidate] = field(default_factory=list)


class BlinkTracker:
    """§7.5: small components recurring periodically at one position are blinkers (cursors)."""

    def __init__(self, p: BlinkParams):
        self.p = p
        self.cands: list[Candidate] = []
        self.history: list[tuple[BBox, float, float]] = []  # (bbox, first toggle, last toggle) of expired confirmed blinkers

    def _match(self, bbox: BBox) -> Candidate | None:
        best, best_iou = None, 0.0
        for c in self.cands:
            v = iou(c.bbox, bbox)
            if v >= self.p.iou and v > best_iou:
                best, best_iou = c, v
        return best

    def update(self, comps: list[Component], t: float) -> BlinkUpdate:
        excluded: set[int] = set()
        newly: list[Candidate] = []
        for idx, c in enumerate(comps):
            w, h = c.bbox[2] - c.bbox[0], c.bbox[3] - c.bbox[1]
            if w > self.p.max_w or h > self.p.max_h:
                continue
            cand = self._match(c.bbox)
            if cand is None:
                self.cands.append(Candidate(c.bbox, [t], t))
                continue
            dt = t - cand.times[-1]
            cand.last_seen = t
            if dt < self.p.min_period_s:
                if cand.confirmed:
                    excluded.add(idx)
                continue
            if dt <= self.p.max_period_s:
                cand.times.append(t)
            else:
                cand.times = [t]
                cand.confirmed = False
            cand.bbox = c.bbox
            recent = [x for x in cand.times if t - x <= self.p.confirm_window_s]
            if not cand.confirmed and len(recent) - 1 >= self.p.confirm_recurrences:
                cand.confirmed = True
                cand.confirmed_at = t
                newly.append(cand)
            if cand.confirmed:
                excluded.add(idx)
        keep = []
        for c in self.cands:
            if t - c.last_seen <= self.p.expiry_s:
                if len(c.times) > 64:  # a cursor that blinks for minutes: keep only what confirmation and lookup need
                    c.times = c.times[-64:]
                keep.append(c)
            elif c.confirmed:
                self.history.append((c.bbox, c.times[0], c.last_seen))
        self.cands = keep
        if len(self.history) > 4096:
            self.history = self.history[-2048:]
        return BlinkUpdate(excluded, newly)

    def is_blinker_bbox(self, bbox: BBox) -> bool:
        c = self._match(bbox)
        return c is not None and c.confirmed

    def candidate_last_seen(self, bbox: BBox) -> float | None:
        """Last toggle time of an unconfirmed candidate at this position (None if untracked or confirmed)."""
        c = self._match(bbox)
        return c.times[-1] if c is not None and not c.confirmed else None

    def caret_for_interval(self, t0: float, t1: float) -> BBox | None:
        """The confirmed blinker active during [t0, t1] (live or expired), preferring the latest one."""
        best: tuple[float, BBox] | None = None
        for c in self.cands:
            if c.confirmed and c.times[0] <= t1 and c.last_seen >= t0:
                last = min(c.last_seen, t1)
                if best is None or last > best[0]:
                    best = (last, c.bbox)
        for bbox, first, last_seen in self.history:
            if first <= t1 and last_seen >= t0:
                last = min(last_seen, t1)
                if best is None or last > best[0]:
                    best = (last, bbox)
        return best[1] if best else None
