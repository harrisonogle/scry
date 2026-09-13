from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable

import numpy as np

from vt.config import Stage1Config
from vt.detect import (BlinkTracker, ChurnTracker, Component, change_map, components, iou, is_bar, reduce_2x2,
                       scale_params, trigger)
from vt.schemas import BBox


@dataclass
class Emission:
    frame_index: int
    t_change: float
    t_settled: float
    settled: bool
    churn_regions: list[BBox]
    frame: object = None          # av.VideoFrame at emission time; Task 6 replaces it with (n, path)
    t_end: float | None = None
    caret: BBox | None = None
    png_future: object = None     # concurrent.futures.Future set by Task 6


class SettleMachine:
    """§7.3 settle state machine over full-resolution grayscale frames; detection at full or half resolution (§7.2)."""

    def __init__(self, cfg: Stage1Config, fps: float, shape: tuple[int, int], downsample: int = 1,
                 on_emit: Callable[[Emission], None] | None = None):
        self.d, cp, bp = scale_params(cfg.detect, cfg.churn, cfg.blink, downsample)
        self.S = cfg.settle.still_s
        self.M = cfg.settle.max_hold_s
        self.ds = downsample
        det_shape = (shape[0] // downsample, shape[1] // downsample)
        self.churn = ChurnTracker(det_shape, fps, cp)
        self.blink = BlinkTracker(bp)
        self.history_s = cfg.blink.confirm_window_s
        self.on_emit = on_emit
        self.prev: np.ndarray | None = None
        self.prev_t = 0.0
        self.prev_index = 0
        self.prev_frame: object = None
        self.last_gray: np.ndarray | None = None
        self.last: Emission | None = None
        self.changed = False
        self.t_change: float | None = None
        self.t_still: float | None = None
        self.t_last_emit = 0.0
        self.history: deque[tuple[float, bool, list[BBox]]] = deque()
        self.finalized: list[Emission] = []

    # ---- helpers ----
    def _scale(self, b: BBox) -> BBox:
        s = self.ds
        return (b[0] * s, b[1] * s, b[2] * s, b[3] * s)

    def _cm(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        cm = change_map(a, b, self.d.theta_pix)
        return reduce_2x2(cm) if self.ds == 2 else cm

    def _active(self, comps: list[Component], excluded: set[int]) -> list[Component]:
        return [c for i, c in enumerate(comps) if i not in excluded and not is_bar(c, self.d) and not self.churn.excludes(c)]

    def _novel(self, gray: np.ndarray, t: float) -> tuple[bool, bool]:
        """(novel, deferred). Deferred while every novelty component sits at an unconfirmed blink-candidate position
        that could still recur (seen within one maximum blink period): a block cursor's first toggles must not be
        emitted as states (§7.5). A candidate that stops recurring becomes novel after max_period_s."""
        comps = components(self._cm(self.last_gray, gray), self.d.theta_min)
        active = [c for c in comps if not is_bar(c, self.d) and not self.churn.excludes(c) and not self.blink.is_blinker_bbox(c.bbox)]
        if not trigger(active, self.d):
            return False, False

        def pending(c: Component) -> bool:
            seen = self.blink.candidate_last_seen(c.bbox)
            return seen is not None and t - seen <= self.blink.p.max_period_s

        return True, all(pending(c) for c in active)

    def _emit(self, index: int, t: float, gray: np.ndarray, frame: object, t_change: float, t_settled: float, settled: bool) -> None:
        t_settled = max(t_settled, t_change)  # churn deactivation can date the final state before the last snapshot
        em = Emission(index, t_change, t_settled, settled, [self._scale(b) for b in self.churn.regions], frame=frame)
        self._finalize(t_change)
        self.last = em
        self.last_gray = gray
        self.t_last_emit = t
        if self.on_emit:
            self.on_emit(em)

    def _finalize(self, t_end: float) -> None:
        if self.last is None:
            return
        self.last.t_end = max(t_end, self.last.t_settled)  # a snapshot's stable interval may be empty, never negative
        caret = self.blink.caret_for_interval(self.last.t_settled, self.last.t_end)
        self.last.caret = self._scale(caret) if caret else None
        self.finalized.append(self.last)
        self.last = None

    def _drain(self) -> list[Emission]:
        out, self.finalized = self.finalized, []
        return out

    def _last_real_motion(self, blinker: BBox) -> float | None:
        for t, moving, boxes in reversed(self.history):
            if moving and any(iou(b, blinker) < self.blink.p.iou for b in boxes):
                return t
        return None

    # ---- main loop ----
    def step(self, index: int, t: float, gray: np.ndarray, frame: object = None) -> list[Emission]:
        if self.prev is None:
            self._emit(index, t, gray, frame, t_change=t, t_settled=t, settled=True)
            self.prev, self.prev_t, self.prev_index, self.prev_frame = gray, t, index, frame
            return self._drain()
        cm = self._cm(self.prev, gray)
        churn_upd = self.churn.update(cm, index, t)
        comps = components(cm, self.d.theta_min)
        blink_upd = self.blink.update(comps, t)
        active = self._active(comps, blink_upd.excluded)
        moving = trigger(active, self.d)
        self.history.append((t, moving, [c.bbox for c in active]))
        while self.history and t - self.history[0][0] > self.history_s:
            self.history.popleft()

        if moving:
            if not self.changed:
                self.changed, self.t_change = True, t
            self.t_still = None
        elif self.changed:
            if self.t_still is None:
                self.t_still = self.prev_t
            if t - self.t_still >= self.S:
                novel, deferred = self._novel(gray, t)
                if not deferred:
                    if novel:
                        self._emit(index, t, gray, frame, self.t_change, self.t_still, True)
                    elif self.last is not None and not self.last.settled and not self.churn.active:
                        self.last.settled = True
                        self.last.t_settled = max(self.t_still, self.last.t_change)  # a snapshot taken after the region stopped
                    self.changed = False

        max_hold_due = self.changed and self.t_still is None and t - self.t_change >= self.M
        tick_due = self.churn.active and t - self.t_last_emit >= self.M
        if (max_hold_due or tick_due) and t - self.t_last_emit >= self.M - 1e-9:  # never two snapshots within M of each other
            t_change = max(self.t_change if self.changed else self.t_last_emit, self.t_last_emit)
            self._emit(index, t, gray, frame, t_change, t, False)
            if self.changed:
                self.t_change = t
        if churn_upd.deactivated:
            if not self.changed:
                self.changed, self.t_change = True, self.t_last_emit
            self.t_still = churn_upd.t_last_change if churn_upd.t_last_change is not None else self.prev_t
        for cand in blink_upd.newly_confirmed:
            t_real = self._last_real_motion(cand.bbox)
            if t_real is None:
                continue
            if self.changed and (self.t_still is None or t_real < self.t_still):
                self.t_still = t_real
            if self.last is not None and any(abs(self.last.t_settled - x) < 1e-9 for x in cand.times) and t_real < self.last.t_settled:
                self.last.t_settled = t_real  # the buffered emission "settled" on a cursor toggle, not on real motion

        self.prev, self.prev_t, self.prev_index, self.prev_frame = gray, t, index, frame
        return self._drain()

    def finish(self, duration: float) -> list[Emission]:
        if self.prev is not None and self.changed and self.last_gray is not None and self._novel(self.prev, self.prev_t + 10.0)[0]:
            t_settled = self.t_still if self.t_still is not None else self.prev_t
            self._emit(self.prev_index, self.prev_t, self.prev, self.prev_frame, self.t_change, t_settled, self.t_still is not None)
        self._finalize(duration)
        return self._drain()
