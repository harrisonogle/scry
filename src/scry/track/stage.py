"""The track stage: changes.jsonl and lifetimes.jsonl from frames.jsonl, boxes.jsonl and the frame PNGs. No model."""
from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Literal

import numpy as np

from scry.config import Config, config_hash
from scry.jsonl import write_jsonl
from scry.run import Run
from scry.schemas import Change, Frame, Revert
from scry.track.changes import track_pair
from scry.track.lifetimes import LifetimeBuilder
from scry.track.pixels import PixelDiff, PixelSource

log = logging.getLogger(__name__)


def transition_kind(a: Frame, b: Frame) -> Literal["single", "unsettled"]:
    return "single" if a.settled and b.settled else "unsettled"


def link_continues(prev: Change | None, cur: Change) -> None:
    """A record whose before box is the after box of a record of the previous change names it: "<change id>/<index>".
    An exact identity through a shared box; geometry is not consulted and nothing is asserted."""
    if prev is None:
        return
    by_after = {r.after.box: j for j, r in enumerate(prev.records) if r.after is not None}
    for r in cur.records:
        if r.before is not None and r.before.box in by_after:
            r.continues = f"{prev.id}/{by_after[r.before.box]}"


def find_reverts(prev: Change | None, prev_diff: PixelDiff | None, zb: PixelDiff | None, a: Frame, b: Frame) -> list[Revert]:
    """H8: `prev` is the change z→a with its PixelDiff, `zb` the direct difference of z and b. A component of z→a is
    undone by a→b when z and b do not differ on any of that component's own pixels. No time constant; nothing is folded."""
    if prev is None or prev_diff is None or zb is None:
        return []
    still_changed = set(np.unique(prev_diff.labels[zb.labels > 0]).tolist())
    hold = round(b.t_change - a.t_change, 3)
    return [Revert(of=prev.id, rect=c.bbox, hold_s=hold) for k, c in enumerate(prev_diff.components, start=1) if k not in still_changed]


def run_track(run: Run, cfg: Config) -> None:
    inputs = [run.frames, run.boxes]
    ch = config_hash(cfg, "track", "decode")  # θpix and θmin live in [decode.detect]
    if run.stage_up_to_date("track", inputs, ch):
        log.info("track up to date")
        return
    t0 = time.perf_counter()
    frames = run.load_frames()
    boxes = {fb.frame: fb.boxes for fb in run.load_boxes()}
    for f in frames:
        if f.frame not in boxes:
            raise ValueError(f"frame {f.frame} has no record in {run.boxes.name}: run `scry read` first")
    source = PixelSource(run.root, cfg.decode.detect)
    lifetimes = LifetimeBuilder()
    if frames:
        lifetimes.first_frame(frames[0], boxes[frames[0].frame])
    changes: list[Change] = []
    z: Frame | None = None
    prev_diff: PixelDiff | None = None
    for a, b in zip(frames, frames[1:]):
        diff = source.diff(a, b)
        result = track_pair(a, b, boxes[a.frame], boxes[b.frame], diff, cfg.track.margin)
        change = result.change
        change.id = f"T{len(changes) + 1}"
        change.kind = transition_kind(a, b)
        prev = changes[-1] if changes else None
        link_continues(prev, change)
        if prev_diff is not None and prev_diff.components:
            change.reverts = find_reverts(prev, prev_diff, source.diff(z, b), a, b)
        lifetimes.step(b, boxes[b.frame], result)
        changes.append(change)
        z, prev_diff = a, diff
        log.debug("%s %d→%d: %d records", change.id, a.frame, b.frame, len(change.records))
    lives = lifetimes.finish()
    write_jsonl(run.changes, changes)
    write_jsonl(run.lifetimes, lives)
    run.stage_done("track", inputs, ch, transitions=len(changes), kinds=dict(Counter(c.kind for c in changes)),
                   records=dict(Counter(r.kind for c in changes for r in c.records)), moved=sum(len(c.moved) for c in changes),
                   same_place=sum(c.same_place for c in changes), unchanged=sum(c.unchanged for c in changes),
                   variants=sum(c.variants for c in changes), flicker_new=sum(len(c.flicker_new) for c in changes),
                   flicker_lost=sum(len(c.flicker_lost) for c in changes), reverts=sum(len(c.reverts) for c in changes),
                   lifetimes=len(lives), unstable=sum(l.unstable for l in lives), margin=cfg.track.margin,
                   seconds=round(time.perf_counter() - t0, 1))
