from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scry.config import Config, OverlayConfig, config_hash
from scry.run import Run
from scry.schemas import BBox, OcrLine

log = logging.getLogger(__name__)
COLOR = (255, 0, 255, 255)   # box outline
LABEL_BG = (255, 255, 0, 255)  # opaque yellow tag with black digits: the first live run showed the model could not read
LABEL_FG = (0, 0, 0, 255)      # magenta digits on a translucent dark backing and guessed the ids (ledger L29)
PAD = 2


def _overlap(a: BBox, b: BBox) -> int:
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def place_label(box: BBox, lw: int, lh: int, boxes: list[BBox], W: int, H: int) -> tuple[int, int, bool]:
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
        return ImageFont.load_default()


def draw_overlay(png_in: Path, lines: list[OcrLine], png_out: Path, cfg: OverlayConfig) -> int:
    img = Image.open(png_in).convert("RGBA")
    W, H = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = _font(cfg)
    boxes = [ln.bbox for ln in lines]
    clashes = 0
    for ln in lines:
        x0, y0, x1, y1 = ln.bbox
        draw.rectangle((x0, y0, max(x1 - 1, x0), max(y1 - 1, y0)), outline=COLOR, width=1)
        label = ln.id[1:]  # "l17" → "17"
        l, t, r, b = font.getbbox(label)
        lw, lh = (r - l) + 2 * PAD, (b - t) + 2 * PAD
        x, y, clash = place_label(ln.bbox, lw, lh, boxes, W, H)
        clashes += int(clash)
        draw.rectangle((x, y, x + lw - 1, y + lh - 1), fill=LABEL_BG)
        draw.text((x + PAD - l, y + PAD - t), label, fill=LABEL_FG, font=font)
    Image.alpha_composite(img, layer).convert("RGB").save(png_out, format="PNG", compress_level=1)
    return clashes


def run_overlay(run: Run, cfg: Config) -> None:
    inputs = [run.ocr]
    ch = config_hash(cfg, "overlay")
    if run.stage_up_to_date("overlay", inputs, ch):
        log.info("overlay up to date")
        return
    s1 = {r.frame: r for r in run.load_stage1()}
    clashes: dict[int, int] = {}
    for of in run.load_ocr():
        rec = s1[of.frame]
        out = run.overlays_dir / f"{of.frame:05d}.png"
        clashes[of.frame] = draw_overlay(run.root / rec.png, of.lines, out, cfg.overlay)
    run.manifest_update(overlay_clashes=clashes)
    run.stage_done("overlay", inputs, ch, frames=len(clashes), label_clashes=sum(clashes.values()))
