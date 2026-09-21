from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from pathlib import Path

import av
import numpy as np
from PIL import Image

from scry.config import DetectParams
from scry.detect import Component, change_map, label_components
from scry.schemas import BBox, Box, Frame


@dataclass(frozen=True)
class PixelDiff:
    labels: np.ndarray  # int32, frame-shaped: k on the changed pixels of the k-th component, 0 elsewhere
    components: list[Component]
    changed_fraction: float  # all changed pixels / screen


class PixelSource:
    """Changed pixels between two emitted frames: decode's change map and components (`[decode.detect]` θpix, θmin) over
    the two PNGs at full resolution (the `downsample` setting is ignored: track runs once per emitted pair). Gray comes
    through the swscale path the decoder uses, which is within one level of the decode-time gray (ledger L32)."""

    def __init__(self, root: Path, detect: DetectParams, keep: int = 8):
        self.root = Path(root)
        self.detect = detect
        self.keep = keep
        self._gray: dict[int, np.ndarray] = {}

    def gray(self, frame: Frame) -> np.ndarray | None:
        g = self._gray.get(frame.frame)
        if g is None:
            path = self.root / frame.png
            if not frame.png or not path.is_file():
                return None
            rgb = np.asarray(Image.open(path).convert("RGB"))
            g = av.VideoFrame.from_ndarray(rgb, format="rgb24").to_ndarray(format="gray")
            self._gray[frame.frame] = g
            while len(self._gray) > self.keep:
                del self._gray[next(iter(self._gray))]
        return g

    def diff(self, a: Frame, b: Frame) -> PixelDiff | None:
        ga, gb = self.gray(a), self.gray(b)
        if ga is None or gb is None or ga.shape != gb.shape:
            return None
        changed = change_map(ga, gb, self.detect.theta_pix)
        labels, comps = label_components(changed, self.detect.theta_min)
        return PixelDiff(labels, comps, round(float(changed.mean()), 6))


def margin_px(a_boxes: list[Box], b_boxes: list[Box], margin: float) -> int:
    """The touch margin in pixels: margin × the median box height over the boxes of both frames, rounded half up."""
    heights = [b.bbox[3] - b.bbox[1] for b in (*a_boxes, *b_boxes)]
    if not heights or margin == 0:
        return 0
    return math.floor(margin * statistics.median(heights) + 0.5)


def grow(bbox: BBox, m: int, shape: tuple[int, int]) -> BBox:
    """The box expanded by m on every side and clipped to the frame; shape is (height, width)."""
    h, w = shape
    return (max(bbox[0] - m, 0), max(bbox[1] - m, 0), min(bbox[2] + m, w), min(bbox[3] + m, h))


def touched_by(bbox: BBox, diff: PixelDiff, m: int) -> set[int]:
    """The numbers of the components with a changed pixel inside the grown box (H6: pixels, not rectangles)."""
    x0, y0, x1, y1 = grow(bbox, m, diff.labels.shape)
    return {int(k) for k in np.unique(diff.labels[y0:y1, x0:x1]) if k}


def touched(bbox: BBox, diff: PixelDiff, m: int) -> bool:
    x0, y0, x1, y1 = grow(bbox, m, diff.labels.shape)
    return bool(diff.labels[y0:y1, x0:x1].any())


def touched_by_rect(bbox: BBox, diff: PixelDiff, m: int) -> bool:
    """Whether the grown box intersects any component's bounding rectangle. Only for the rect_only diagnostic."""
    x0, y0, x1, y1 = grow(bbox, m, diff.labels.shape)
    return any(x0 < c.bbox[2] and c.bbox[0] < x1 and y0 < c.bbox[3] and c.bbox[1] < y1 for c in diff.components)
