from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path

from scry.jsonl import read_jsonl, write_jsonl
from scry.run import Run
from scry.schemas import Frame

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


def is_legacy(src_root: Path) -> bool:
    """A pre-re-base run directory: decode's records are in `stage1.jsonl` (its `frames.jsonl` is the old merged file)."""
    return (Path(src_root) / "stage1.jsonl").exists()


def import_ocr(src_root: Path, dst: Run, recs: list[Frame], read_config_hash: str) -> bool:
    """Copy the source's `boxes.jsonl` lines for `recs` into `dst` and mark `read` done there, so `read` finds itself
    up to date and does not run: OCR is deterministic and makes no model call (byte-identical boxes between cold runs,
    P5), so "cold" is about model answers and caches, never about it. Only when the source's read is finished for its
    current frames.jsonl (its entry's inputs hash) with a config that hashes as `read_config_hash`, and its file holds
    a record for every frame of the span; otherwise nothing is written and `read` runs as it always did. The lines are
    copied as bytes, in the source's order, never re-serialised. The entry carries this run's inputs hash of its own
    frames.jsonl, the given config hash, the source's stats with `frames` and `boxes` counted over what was copied,
    and `imported_from`."""
    src_root = Path(src_root)
    manifest, src_boxes = src_root / "manifest.json", src_root / "boxes.jsonl"
    st = json.loads(manifest.read_text()).get("stages", {}).get("read") if manifest.exists() else None
    if not st or not src_boxes.exists() or st.get("config") != read_config_hash \
            or st.get("inputs") != Run.inputs_hash([src_root / "frames.jsonl"]):
        return False
    wanted = {r.frame for r in recs}
    kept: list[bytes] = []
    frames: list[int] = []
    boxes = 0
    with src_boxes.open("rb") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["frame"] in wanted:
                kept.append(line if line.endswith(b"\n") else line + b"\n")
                frames.append(rec["frame"])
                boxes += len(rec.get("boxes", []))
    if frames != [r.frame for r in recs]:
        log.info("subset %s: the source's boxes.jsonl does not hold every frame of the span in order; read will run", dst.root)
        return False
    dst.boxes.write_bytes(b"".join(kept))
    stats = {k: v for k, v in st.items() if k not in ("inputs", "config", "finished")}
    dst.stage_done("read", [dst.frames], read_config_hash, **{**stats, "frames": len(kept), "boxes": boxes, "imported_from": str(src_root)})
    return True


def make_subset(src_root: Path, out: Path, frames: tuple[int, int], share_cache: bool = True,
                read_config_hash: str | None = None) -> Run:
    """Derive a run directory holding only the decoded frames lo..hi of the run directory `src_root`, with decode marked
    done in its manifest. Frame numbers are kept, so records, ids and cache keys line up with the source. The source is
    a path and is only read: nothing is created, modified or deleted under it. A pre-re-base directory is imported by
    reading its `stage1.jsonl` and its manifest's `stage1` entry. With `share_cache` the subset's `cache/` is a symlink
    to the source's when the source has one: model calls paid for here are cache hits when the full run reaches the same
    frames, because cache keys are content hashes, not paths. With `read_config_hash` (what `read` will hash the new
    run's config to: scry.read.read_config_hash) the source's OCR is imported too when it was made with the same hash
    (import_ocr); a legacy directory's never is."""
    src_root = Path(src_root)
    lo, hi = frames
    records = src_root / ("stage1.jsonl" if is_legacy(src_root) else "frames.jsonl")
    recs = [r for r in read_jsonl(records, Frame) if lo <= r.frame <= hi]
    if not recs:
        raise ValueError(f"no frames in {lo}-{hi} under {src_root}")
    manifest = src_root / "manifest.json"
    m = json.loads(manifest.read_text()) if manifest.exists() else {}
    stages = m.get("stages", {})
    st = stages.get("decode", stages.get("stage1"))
    if st is None:
        raise ValueError(f"{src_root} has no finished decode stage in its manifest")
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"{out} exists and is not empty")
    out.mkdir(parents=True, exist_ok=True)
    src_cache = src_root / "cache"
    if share_cache and src_cache.is_dir():
        (out / "cache").symlink_to(os.path.relpath(src_cache, out), target_is_directory=True)
    dst = Run(out)  # creates frames/ and overlays/; an existing cache/ symlink to a directory is left alone
    for r in recs:
        shutil.copy2(src_root / r.png, dst.root / r.png)
    write_jsonl(dst.frames, recs)
    dst.manifest_update(**{k: m[k] for k in COPIED_KEYS if k in m},
                        stages={"decode": {**st, "emitted": len(recs), "settled": sum(r.settled for r in recs)}},
                        subset={"source": str(src_root), "frames": [lo, hi]})
    imported = read_config_hash is not None and not is_legacy(src_root) and import_ocr(src_root, dst, recs, read_config_hash)
    log.info("subset %s: %d frames (%d-%d) from %s%s", out, len(recs), lo, hi, src_root, "; OCR imported" if imported else "")
    return dst
