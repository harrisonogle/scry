from __future__ import annotations

import logging
import math
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
MASK_FILL = (204, 204, 204, 255)  # [overlay] mask = opaque / opaque_label: the light grey covering each OCR box
RENDER_BG = (255, 255, 255, 255)  # [overlay] mask = rendered: white box with the OCR text re-set in the tag font
RENDER_FG = (0, 0, 0, 255)
RENDER_MIN_PT = 6                 # rendered: the text shrinks to fit the box width down to this size, then is clipped


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


def _font(cfg: OverlayConfig, size: int | None = None):
    size = cfg.font_size if size is None else size
    try:
        return ImageFont.truetype(cfg.font_path, size)
    except OSError:
        return ImageFont.load_default(size)


def _fit_text(text: str, w: int, h: int, cfg: OverlayConfig, fonts: dict) -> tuple[ImageFont.FreeTypeFont, int]:
    """The tag font at the largest size whose ascent + descent fit the box height and whose rendering of `text` fits
    the box width, never below RENDER_MIN_PT (past that the caller clips); with the y offset that centres its line box."""
    size = max(RENDER_MIN_PT, h)
    while True:
        font = fonts.get(size) or fonts.setdefault(size, _font(cfg, size))
        asc, desc = font.getmetrics()
        if size <= RENDER_MIN_PT or (asc + desc <= h and font.getlength(text) <= w):
            return font, (h - asc - desc) // 2
        size -= 1


def mask_image(img: Image.Image, lines: list[OcrLine], cfg: OverlayConfig) -> Image.Image:
    """[overlay] mask: `img` (the frame, already scaled by cfg.scale) with every OCR box covered, in place. opaque and
    opaque_label fill the box MASK_FILL grey; rendered fills it white and re-sets the OCR text inside it (left-aligned,
    vertically centred, see _fit_text). No tags: draw_overlay adds them afterwards, and perceive.frame_block applies the
    same masking to the clean frame in memory so both Stage 2c images cover the same rectangles. none returns img as is."""
    if cfg.mask == "none":
        return img
    draw = ImageDraw.Draw(img)
    fonts: dict[int, ImageFont.FreeTypeFont] = {}
    for ln in lines:
        x0, y0, x1, y1 = _scale_box(ln.bbox, cfg.scale)
        if x1 <= x0 or y1 <= y0:
            continue
        if cfg.mask != "rendered":
            draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=MASK_FILL)
            continue
        w, h = x1 - x0, y1 - y0
        font, top = _fit_text(ln.text, w, h, cfg, fonts)
        tile = Image.new("RGBA", (w, h), RENDER_BG)  # text past the box edge is clipped by the tile
        ImageDraw.Draw(tile).text((0, top), ln.text, fill=RENDER_FG, font=font, anchor="la")
        img.paste(tile, (x0, y0))
    return img


def scale_image(img: Image.Image, scale: float) -> Image.Image:
    """The frame downscaled by `scale` (LANCZOS); unchanged at 1.0. Stage 2c scales the clean frame the same way, so
    the two images the model sees stay the same size."""
    if scale == 1.0:
        return img
    return img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)


def _scale_box(box: BBox, scale: float) -> BBox:
    x0, y0, x1, y1 = box  # rounded outward so the box still encloses its text
    return (math.floor(x0 * scale), math.floor(y0 * scale), math.ceil(x1 * scale), math.ceil(y1 * scale))


def draw_overlay(png_in: Path, lines: list[OcrLine], png_out: Path, cfg: OverlayConfig) -> int:
    img = mask_image(scale_image(Image.open(png_in).convert("RGBA"), cfg.scale), lines, cfg)
    W, H = img.size
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = _font(cfg)  # font_size is not scaled: the tags stay legible when the frame shrinks
    boxes = [_scale_box(ln.bbox, cfg.scale) for ln in lines]
    clashes = 0
    for ln, box in zip(lines, boxes):
        x0, y0, x1, y1 = box
        draw.rectangle((x0, y0, max(x1 - 1, x0), max(y1 - 1, y0)), outline=COLOR, width=1)
        label = ln.id[1:]  # "l17" → "17"
        l, t, r, b = font.getbbox(label)
        lw, lh = (r - l) + 2 * PAD, (b - t) + 2 * PAD
        if cfg.mask == "opaque_label":  # the tag sits inside the covered box: left-aligned, vertically centred, black on the grey
            y = y0 + (y1 - y0 - lh) // 2
            draw.text((x0 + PAD - l, y + PAD - t), label, fill=LABEL_FG, font=font)
            continue
        x, y, clash = place_label(box, lw, lh, boxes, W, H)
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
