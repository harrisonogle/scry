from pathlib import Path

import av
import numpy as np
import pytest


def make_video(path: Path, frames: list[np.ndarray], fps: int = 30) -> Path:
    """Encode grayscale uint8 frames (H, W) into an mp4 with the mpeg4 codec (always available in PyAV)."""
    h, w = frames[0].shape
    with av.open(str(path), mode="w") as c:
        s = c.add_stream("mpeg4", rate=fps)
        s.width, s.height, s.pix_fmt = w, h, "yuv420p"
        for g in frames:
            rgb = np.stack([g, g, g], axis=-1)
            fr = av.VideoFrame.from_ndarray(rgb, format="rgb24")
            for pkt in s.encode(fr):
                c.mux(pkt)
        for pkt in s.encode():
            c.mux(pkt)
    return path


@pytest.fixture
def video_factory(tmp_path: Path):
    def _make(frames, fps=30, name="v.mp4"):
        return make_video(tmp_path / name, frames, fps)
    return _make
