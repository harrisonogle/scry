from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from scry.jsonl import write_jsonl
from scry.run import Run

log = logging.getLogger(__name__)

COPIED_KEYS = ("video", "video_sha256", "video_id", "versions", "width", "height", "fps", "duration")


def parse_frames(spec: str) -> tuple[int, int]:
    """'145-155' → (145, 155), inclusive; '150' → (150, 150)."""
    a, _, b = spec.partition("-")
    lo = int(a)
    hi = int(b) if b else lo
    if hi < lo:
        raise ValueError(f"empty frame range {spec!r}")
    return lo, hi


def make_subset(src: Run, out: Path, frames: tuple[int, int], share_cache: bool = True) -> Run:
    """Derive a run directory holding only Stage 1 frames lo..hi of `src`, with Stage 1 marked done in its manifest so
    `scry run <video> --out <out>` skips decoding and the later stages run on the subset as usual (§20.9 skip logic).
    Frame numbers are kept, so records, node ids and cache keys line up with the source run. With `share_cache` the
    subset's `cache/` is a symlink to the source's: model calls paid for here are cache hits when the full run reaches
    the same frames, because cache keys are content hashes (frame and overlay PNGs), not paths."""
    lo, hi = frames
    recs = [r for r in src.load_stage1() if lo <= r.frame <= hi]
    if not recs:
        raise ValueError(f"no Stage 1 frames in {lo}-{hi} under {src.root}")
    m = src.manifest_read()
    st = m.get("stages", {}).get("stage1")
    if st is None:
        raise ValueError(f"{src.root} has no finished Stage 1 in its manifest")
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"{out} exists and is not empty")
    out.mkdir(parents=True, exist_ok=True)
    if share_cache:
        (out / "cache").symlink_to(os.path.relpath(src.cache_dir, out), target_is_directory=True)
    dst = Run(out)  # creates frames/ and overlays/; an existing cache/ symlink to a directory is left alone
    for r in recs:
        shutil.copy2(src.root / r.png, dst.root / r.png)
    write_jsonl(dst.stage1, recs)
    dst.manifest_update(**{k: m[k] for k in COPIED_KEYS if k in m},
                        stages={"stage1": {**st, "emitted": len(recs), "settled": sum(r.settled for r in recs)}},
                        subset={"source": str(src.root), "frames": [lo, hi]})
    log.info("subset %s: %d frames (%d-%d) from %s", out, len(recs), lo, hi, src.root)
    return dst
