from __future__ import annotations

import hashlib
import importlib.metadata
import io
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scry.config import Config, config_hash
from scry.jsonl import sha256_file, write_jsonl
from scry.run import Run
from scry.schemas import Frame
from scry.settle import Emission, SettleMachine
from scry.video import iter_frames, video_info

log = logging.getLogger(__name__)


def _encode_png(img, path: Path) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=1)
    data = buf.getvalue()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _versions() -> dict[str, str]:
    out = {}
    for name in ("av", "numpy", "scipy", "anthropic", "pillow", "rapidfuzz", "pydantic"):
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return out


def run_decode(run: Run, cfg: Config, video: Path) -> None:
    inputs = [video]
    ch = config_hash(cfg, "decode")
    if run.stage_up_to_date("decode", inputs, ch):
        log.info("decode up to date")
        return
    info = video_info(video)
    ds = cfg.decode.detect.downsample
    vid = run.root.name
    run.manifest_update(video=str(video), video_sha256=sha256_file(video), video_id=vid, versions=_versions(),
                        width=info.width, height=info.height, fps=info.fps, duration=info.duration)
    pool = ThreadPoolExecutor(max_workers=2)
    counter = {"n": 0}

    def on_emit(em: Emission) -> None:
        n = counter["n"]
        counter["n"] += 1
        img = em.frame.to_image()
        path = run.frames_dir / f"{n:05d}.png"
        em.png_future = pool.submit(_encode_png, img, path)
        em.frame = (n, path)

    machine = SettleMachine(cfg.decode, info.fps, (info.height, info.width), ds, on_emit=on_emit)
    records: list[Frame] = []

    def take(ems: list[Emission]) -> None:
        for em in ems:
            n, path = em.frame
            sha = em.png_future.result()
            records.append(Frame(video_id=vid, frame=n, t_change=em.t_change, t_settled=em.t_settled,
                                 t_end=em.t_end, settled=em.settled, churn_regions=em.churn_regions,
                                 caret=em.caret, width=info.width, height=info.height, sha256=sha,
                                 png=str(path.relative_to(run.root))))

    for df in iter_frames(video):
        take(machine.step(df.index, df.t, df.gray, frame=df.frame))
        if df.index % 3000 == 0 and df.index:
            log.info("decoded %d frames (t=%.1fs), emitted %d", df.index, df.t, counter["n"])
    take(machine.finish(info.duration))
    pool.shutdown(wait=True)
    write_jsonl(run.frames, records)
    run.stage_done("decode", inputs, ch, emitted=len(records), settled=sum(r.settled for r in records))
