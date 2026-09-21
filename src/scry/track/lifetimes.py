"""Box lifetimes: a box followed across consecutive frames while it stays the same text (unchanged, same place, moved,
or re-read with only whitespace differing). The fields are measurements; how long a text lasted is evidence of nothing."""
from __future__ import annotations

from collections import Counter

from scry.schemas import Box, Frame, FrameTime, Lifetime, box_ref
from scry.track.changes import PairResult


class LifetimeBuilder:
    def __init__(self) -> None:
        self._lifetimes: list[Lifetime] = []  # in creation order; ids L1, L2, …
        self._open: dict[str, Lifetime] = {}  # box id in the latest frame → the lifetime that holds it

    def _sight(self, life: Lifetime, frame: Frame, box: Box) -> None:
        life.boxes.append(box_ref(frame.frame, box.id))
        life.readings.setdefault(box.text, []).append(frame.frame)
        life.last = FrameTime(frame=frame.frame, t=frame.t_end)

    def _start(self, frame: Frame, box: Box) -> Lifetime:
        at = FrameTime(frame=frame.frame, t=frame.t_settled)
        life = Lifetime(id=f"L{len(self._lifetimes) + 1}", text="", readings={}, unstable=False, sightings=0, first=at, last=at, boxes=[])
        self._lifetimes.append(life)
        self._sight(life, frame, box)
        return life

    def first_frame(self, frame: Frame, boxes: list[Box]) -> None:
        self._open = {box.id: self._start(frame, box) for box in boxes}

    def step(self, b: Frame, b_boxes: list[Box], result: PairResult) -> None:
        counts = Counter([p.b for p in result.pairings] + list(result.starts))
        for box in b_boxes:
            if counts[box.id] != 1:
                raise ValueError(f"frame {b.frame}: box {box.id} is in {counts[box.id]} of the pairings and starts, expected exactly one")
        by_id = {box.id: box for box in b_boxes}
        nxt: dict[str, Lifetime] = {}
        for p in result.pairings:
            life = self._open[p.a]
            self._sight(life, b, by_id[p.b])
            if p.how == "moved":
                life.moved = True
            nxt[p.b] = life
        for box_id in result.starts:  # reading order, so ids follow it within the frame
            nxt[box_id] = self._start(b, by_id[box_id])
        self._open = nxt  # a lifetime that was not continued simply stops

    def finish(self) -> list[Lifetime]:
        for life in self._lifetimes:
            life.text = max(life.readings, key=lambda r: len(life.readings[r]))  # a tie goes to the reading sighted first
            life.unstable = len(life.readings) > 1
            life.sightings = len(life.boxes)
        return self._lifetimes
