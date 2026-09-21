"""Which frames get a labelling call and which boxes are its targets: a pure function of track's records (spec §2).
No model, no I/O."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from scry.schemas import Change, FrameBoxes, Lifetime, box_ref


@dataclass(frozen=True)
class CallPlan:
    frame: int
    targets: tuple[str, ...]  # box ids, reading order


def plan_calls(frames: list[FrameBoxes], changes: list[Change], lifetimes: list[Lifetime],
               mode: Literal["every_frame", "incremental"]) -> list[CallPlan]:
    if mode == "every_frame":
        return [CallPlan(fb.frame, tuple(b.id for b in fb.boxes)) for fb in frames]
    into = {c.to_frame: c for c in changes}
    starts = {l.boxes[0] for l in lifetimes}
    plans: list[CallPlan] = []
    for i, fb in enumerate(frames):
        if i == 0:  # the first frame: every box is new
            plans.append(CallPlan(fb.frame, tuple(b.id for b in fb.boxes)))
            continue
        change = into.get(fb.frame)
        if change is None:
            raise ValueError(f"changes.jsonl has no transition into frame {fb.frame}")
        if change.pixels is None or change.pixels.components > 0:
            plans.append(CallPlan(fb.frame, tuple(b.id for b in fb.boxes if box_ref(fb.frame, b.id) in starts)))
    return plans
