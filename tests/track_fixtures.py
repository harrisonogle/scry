"""Shared fixtures for the track tests (plan 1, Tasks 8-10). Frame shape (200, 400); every box is 18 px tall unless a
test says otherwise, so margin 0.5 gives m = 9."""
import numpy as np

from scry.detect import Component
from scry.schemas import Box, Frame
from scry.track.pixels import PixelDiff

SHAPE = (200, 400)


def mk(id: str, x0: int, y0: int, x1: int, y1: int, text: str) -> Box:
    return Box(id=id, bbox=(x0, y0, x1, y1), text=text, conf=1.0)


def new_labels() -> np.ndarray:
    return np.zeros(SHAPE, np.int32)


def block(labels: np.ndarray, k: int, y0: int, y1: int, x0: int, x1: int) -> Component:
    labels[y0:y1, x0:x1] = k
    return Component((y1 - y0) * (x1 - x0), (x0, y0, x1, y1))


def diff_of(labels: np.ndarray, comps: list[Component]) -> PixelDiff:
    return PixelDiff(labels, comps, round(int((labels > 0).sum()) / (SHAPE[0] * SHAPE[1]), 6))


def frame(n: int, t_change: float | None = None, t_settled: float | None = None, t_end: float | None = None, settled: bool = True) -> Frame:
    return Frame(video_id="v", frame=n, t_change=float(n) if t_change is None else t_change,
                 t_settled=float(n) if t_settled is None else t_settled, t_end=n + 1.0 if t_end is None else t_end,
                 settled=settled, width=SHAPE[1], height=SHAPE[0], sha256="", png=f"frames/{n:05d}.png")


def fixture_k() -> tuple[list[Box], list[Box], PixelDiff]:
    """A keystroke: the prompt grows by ' git status'; one changed component over the new characters."""
    a = [mk("b1", 10, 10, 110, 28, "Title"), mk("b2", 10, 50, 130, 68, "PS>"), mk("b3", 300, 150, 330, 168, "区")]
    b = [mk("b1", 10, 10, 110, 28, "Title"), mk("b2", 10, 50, 230, 68, "PS> git status")]
    labels = new_labels()
    comps = [block(labels, 1, 52, 66, 140, 228)]
    return a, b, diff_of(labels, comps)
