from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import av
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    duration: float
    codec: str


@dataclass
class DecodedFrame:
    index: int
    t: float
    gray: np.ndarray
    frame: av.VideoFrame


def video_info(path: Path) -> VideoInfo:
    with av.open(str(path)) as c:
        s = c.streams.video[0]
        fps = float(s.average_rate or s.guessed_rate or 30)
        if c.duration:
            duration = float(c.duration / av.time_base)  # av.time_base is the int 1_000_000 (AV_TIME_BASE) in PyAV 18
        elif s.duration:
            duration = float(s.duration * s.time_base)
        else:
            duration = 0.0
        return VideoInfo(s.width, s.height, fps, duration, s.codec_context.name)


def iter_frames(path: Path, start: float | None = None) -> Iterator[DecodedFrame]:
    """Full-resolution grayscale frames with exact presentation times; `start` seeks to a time in seconds."""
    with av.open(str(path)) as c:
        s = c.streams.video[0]
        s.thread_type = "AUTO"
        tb = s.time_base
        fps = float(s.average_rate or 30)
        if start:
            c.seek(int(start / tb), stream=s, backward=True, any_frame=False)
        prev_t: float | None = None
        for i, fr in enumerate(c.decode(s)):
            if fr.pts is not None:
                t = float(fr.pts * tb)
            elif fr.time is not None:
                t = float(fr.time)
            else:
                t = (prev_t + 1.0 / fps) if prev_t is not None else 0.0
                log.warning("frame %d has no pts; using %.4f", i, t)
            prev_t = t
            if start and t < start:
                continue
            yield DecodedFrame(i, t, fr.to_ndarray(format="gray"), fr)
