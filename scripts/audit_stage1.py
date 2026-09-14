"""Ground-truth-free check of Stage 1 against the video: settled screens the machine did not emit.

For every decoded frame inside an emitted state's stable interval, test whether the frame is still relative to its
predecessor yet differs from the emitted PNG (above the trigger threshold, bar-shaped components excluded). A run of
such frames lasting at least the settle window S is a screen the machine should have emitted. Cursor blinks show up as
departures of a few dozen pixels lasting one blink half-period; anything text-sized (hundreds of pixels or more) is a
real miss. On the sample video (2026-09-13) this found 10 departures of 32-179 px and nothing text-sized (ledger L27).

Usage: uv run python scripts/audit_stage1.py runs/aks [--video PATH] [--start S] [--end S]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from vt.config import load_config
from vt.decode import iter_frames
from vt.detect import change_map, components, is_bar, trigger
from vt.run import Run


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--video", type=Path, default=None, help="defaults to the video recorded in manifest.json")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--config", type=Path, default=None)
    args = ap.parse_args()
    run = Run(args.run_dir)
    cfg = load_config(args.config)
    p, S = cfg.stage1.detect, cfg.stage1.settle.still_s
    video = args.video or Path(run.manifest_read()["video"])
    recs = run.load_stage1()
    if not recs:
        raise SystemExit("no stage1.jsonl in the run directory; run `vt decode` first")

    def active(a, b):
        return [c for c in components(change_map(a, b, p.theta_pix), p.theta_min) if not is_bar(c, p)]

    i = 0
    state = np.array(Image.open(run.root / recs[0].png).convert("L"))
    prev = None
    cur: dict | None = None
    departures: list[dict] = []

    def close():
        nonlocal cur
        if cur is not None and cur["end"] - cur["start"] >= S:
            departures.append(cur)
        cur = None

    for df in iter_frames(video, start=args.start or None):
        if args.end is not None and df.t > args.end:
            break
        while i + 1 < len(recs) and df.t >= recs[i + 1].t_settled:
            close()
            i += 1
            state = np.array(Image.open(run.root / recs[i].png).convert("L"))
        if df.t < recs[i].t_settled:  # inside the transition into state i
            prev = df.gray
            continue
        moving = prev is not None and trigger(active(prev, df.gray), p)
        diff = active(state, df.gray)
        if trigger(diff, p) and not moving:
            px = sum(c.area for c in diff)
            big = max(diff, key=lambda c: c.area).bbox
            if cur is None:
                cur = {"state": recs[i].frame, "start": df.t, "end": df.t, "max_px": px, "largest_bbox": big}
            else:
                cur["end"] = df.t
                if px > cur["max_px"]:
                    cur["max_px"], cur["largest_bbox"] = px, big
        else:
            close()
        prev = df.gray
    close()

    text_sized = [d for d in departures if d["max_px"] >= 500]
    print(f"states: {len(recs)}; settled-but-unemitted departures: {len(departures)} ({len(text_sized)} text-sized, >= 500 px)")
    for d in departures:
        x0, y0, x1, y1 = d["largest_bbox"]
        print(f"  state {d['state']:4d}  {d['start']:8.2f}-{d['end']:8.2f} s  {d['end'] - d['start']:5.2f} s  {d['max_px']:7d} px  largest {x1 - x0}x{y1 - y0} at ({x0},{y0})")
    (run.root / "audit.json").write_text(json.dumps({"departures": departures, "text_sized": len(text_sized)}, indent=1))


if __name__ == "__main__":
    main()
