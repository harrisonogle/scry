"""Metrics over changes.jsonl and lifetimes.jsonl. Pure functions, no I/O, no thresholds: they are read, not judged."""
from __future__ import annotations

import math
import statistics
from collections import Counter

from scry.annotate.targets import plan_calls
from scry.schemas import Change, FrameBoxes, Lifetime, parse_box_ref


def select(boxes: list[FrameBoxes], changes: list[Change], lifetimes: list[Lifetime],
           frames: tuple[int, int] | None) -> tuple[list[FrameBoxes], list[Change], list[Lifetime]]:
    """The records of an inclusive frame range: changes wholly inside it, lifetimes with at least one sighting in it
    (their first and last are not clipped). None selects everything."""
    if frames is None:
        return boxes, changes, lifetimes
    lo, hi = frames
    return ([b for b in boxes if lo <= b.frame <= hi], [c for c in changes if lo <= c.from_frame and c.to_frame <= hi],
            [l for l in lifetimes if any(lo <= parse_box_ref(ref)[0] <= hi for ref in l.boxes)])


def box_stability(changes: list[Change]) -> float | None:
    """Of the boxes on unchanged pixels, the share that recurred with the same text: (unchanged − variants) over
    (unchanged + flicker_lost). No overlap threshold is involved."""
    unchanged = sum(c.unchanged for c in changes)
    den = unchanged + sum(len(c.flicker_lost) for c in changes)
    return round((unchanged - sum(c.variants for c in changes)) / den, 4) if den else None


def touched_share_low_half(changes: list[Change]) -> float | None:
    """The median touched share over the lower half of the transitions by changed fraction (a rank, not a cut-off):
    the per-video alarm for θpix and θmin."""
    with_pixels = sorted((c for c in changes if c.pixels is not None), key=lambda c: (c.pixels.changed_fraction, int(c.id[1:])))
    if not with_pixels:
        return None
    low = with_pixels[:math.ceil(len(with_pixels) / 2)]
    return round(statistics.median(c.pixels.touched_share for c in low), 4)


def totals(changes: list[Change]) -> dict:
    with_pixels = [c.pixels for c in changes if c.pixels is not None]
    return {"transitions": dict(Counter(c.kind for c in changes)), "records": dict(Counter(r.kind for c in changes for r in c.records)),
            "moved": sum(len(c.moved) for c in changes), "same_place": sum(c.same_place for c in changes),
            "unchanged": sum(c.unchanged for c in changes), "variants": sum(c.variants for c in changes),
            "flicker_new": sum(len(c.flicker_new) for c in changes), "flicker_lost": sum(len(c.flicker_lost) for c in changes),
            "reverts": sum(c.reverts is not None for c in changes), "textless": sum(p.textless for p in with_pixels),
            "rect_only": sum(p.rect_only for p in with_pixels)}


def fragmentation(lifetimes: list[Lifetime], top: int = 20) -> dict:
    """H7: how many lifetimes each distinct text has; `top` holds the texts with the most."""
    per_text = Counter(l.text for l in lifetimes)
    return {"lifetimes": len(lifetimes), "distinct_texts": len(per_text),
            "per_text": round(len(lifetimes) / len(per_text), 3) if per_text else None,
            "unstable": sum(l.unstable for l in lifetimes), "single_sighting": sum(l.sightings == 1 for l in lifetimes),
            "top": sorted(per_text.items(), key=lambda kv: (-kv[1], kv[0]))[:top]}


def incremental_projection(boxes: list[FrameBoxes], changes: list[Change], lifetimes: list[Lifetime]) -> dict:
    """The calls and target boxes incremental annotation would make, taken from the stage's own planner so the price
    and the stage cannot drift apart: one call for the first frame, with every box a target, and one for every
    transition in which pixels changed (or that has no pixel data), even if no lifetime starts there, because the
    screen description must be refreshed. What it saves is boxes per call, not calls."""
    plans = plan_calls(boxes, changes, lifetimes, "incremental")
    n_frames, n_boxes = len(boxes), sum(len(b.boxes) for b in boxes)
    calls, target_boxes = len(plans), sum(len(p.targets) for p in plans)
    return {"frames": n_frames, "boxes": n_boxes, "calls": calls, "calls_without_targets": sum(1 for p in plans if not p.targets),
            "target_boxes": target_boxes, "share_of_boxes": round(target_boxes / n_boxes, 4) if n_boxes else None,
            "targets_per_call": round(target_boxes / calls, 2) if calls else None,
            "boxes_per_frame": round(n_boxes / n_frames, 2) if n_frames else None}
