"""The numbered-box overlay: every OCR box outlined, with its number on an opaque tag beside it."""
from __future__ import annotations

import logging
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scry.config import OverlayConfig
from scry.schemas import BBox, Box

log = logging.getLogger(__name__)
COLOR = (255, 0, 255, 255)   # box outline
LABEL_BG = (255, 255, 0, 255)  # opaque yellow tag with black digits: the first live run showed the model could not read
LABEL_FG = (0, 0, 0, 255)      # magenta digits on a translucent dark backing and guessed the ids (ledger L29)
PAD = 2


def _overlap(a: BBox, b: BBox) -> int:
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def place_label(box: BBox, lw: int, lh: int, boxes: list[BBox], W: int, H: int) -> tuple[int, int, bool]:
    """Where a box's tag goes: right of the box, else the left gutter, above, below, each clamped into the image; the
    first slot that intersects no box, else the least-overlapping one (the earliest among equals) and a clash."""
    x0, y0, x1, y1 = box
    cy = (y0 + y1) // 2 - lh // 2
    slots = [(x1 + 2, cy), (x0 - lw - 2, cy), (x0, y0 - lh - 1), (x0, y1 + 1)]
    others = [b for b in boxes if b != box]
    best, best_ov = None, None
    for sx, sy in slots:
        sx = min(max(sx, 0), W - lw)
        sy = min(max(sy, 0), H - lh)
        rect = (sx, sy, sx + lw, sy + lh)
        ov = _overlap(rect, box) + sum(_overlap(rect, b) for b in others)
        if ov == 0:
            return sx, sy, False
        if best_ov is None or ov < best_ov:
            best, best_ov = (sx, sy), ov
    return best[0], best[1], True


def _font(cfg: OverlayConfig):
    try:
        return ImageFont.truetype(cfg.font_path, cfg.font_size)
    except OSError:
        return ImageFont.load_default(cfg.font_size)


def scale_image(img: Image.Image, scale: float) -> Image.Image:
    """The frame downscaled by `scale` (LANCZOS); unchanged at 1.0. The clean frame is scaled the same way, so the two
    images the model sees stay the same size."""
    if scale == 1.0:
        return img
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)


def _scale_box(box: BBox, scale: float) -> BBox:
    x0, y0, x1, y1 = box  # rounded outward so the rectangle still encloses its text
    return (math.floor(x0 * scale), math.floor(y0 * scale), math.ceil(x1 * scale), math.ceil(y1 * scale))


def draw_overlay(png_in: Path, boxes: list[Box], png_out: Path, cfg: OverlayConfig, scale: float = 1.0) -> int:
    """Write the frame with every box outlined and numbered; returns the number of label clashes. With scale < 1 the
    frame and the rectangles shrink; the tag font does not, so the tags stay legible."""
    img = scale_image(Image.open(png_in).convert("RGBA"), scale)
    W, H = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = _font(cfg)
    rects = [_scale_box(b.bbox, scale) for b in boxes]
    clashes = 0
    for box, rect in zip(boxes, rects):
        x0, y0, x1, y1 = rect
        draw.rectangle((x0, y0, max(x1 - 1, x0), max(y1 - 1, y0)), outline=COLOR, width=1)
        label = box.id[1:]  # "b17" → "17"
        l, t, r, b = font.getbbox(label)
        lw, lh = (r - l) + 2 * PAD, (b - t) + 2 * PAD
        x, y, clash = place_label(rect, lw, lh, rects, W, H)
        clashes += int(clash)
        draw.rectangle((x, y, x + lw - 1, y + lh - 1), fill=LABEL_BG)
        draw.text((x + PAD - l, y + PAD - t), label, fill=LABEL_FG, font=font)
    Image.alpha_composite(img, layer).convert("RGB").save(png_out, format="PNG", compress_level=1)
    return clashes
