import numpy as np

from vt.decode import iter_frames, video_info


def test_iter_frames_times_and_shapes(video_factory):
    frames = [np.full((64, 96), 20 + i, dtype=np.uint8) for i in range(12)]
    path = video_factory(frames, fps=30)
    info = video_info(path)
    assert (info.width, info.height) == (96, 64)
    assert abs(info.fps - 30) < 0.01
    assert 0.35 <= info.duration <= 0.45
    decoded = list(iter_frames(path))
    assert len(decoded) == 12
    assert decoded[0].t == 0.0
    assert all(abs((decoded[i + 1].t - decoded[i].t) - 1 / 30) < 1e-3 for i in range(11))
    assert decoded[0].gray.shape == (64, 96) and decoded[0].gray.dtype == np.uint8
    tail = list(iter_frames(path, start=0.2))
    assert tail and tail[0].t >= 0.15 and len(tail) < 12
