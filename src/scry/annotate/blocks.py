"""The user turn of an `annotate` call. Everything in it comes from decode's, read's and track's records: nothing from
an earlier answer, and never an OCR text (the second reading must stay independent of the first)."""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

from scry.annotate.targets import CallPlan
from scry.jsonl import sha256_file, sha256_obj
from scry.overlay import scale_image
from scry.providers import image_block, text_block
from scry.schemas import Box, Frame, FrameBoxes


def frame_block(frame_png: Path, scale: float) -> dict:
    """The clean frame as an image block: the file as it is at scale 1, otherwise downscaled in memory, never written."""
    if scale == 1.0:
        return image_block(frame_png)
    buf = io.BytesIO()
    scale_image(Image.open(frame_png).convert("RGB"), scale).save(buf, format="PNG", compress_level=1)
    data = base64.standard_b64encode(buf.getvalue()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}


NO_TARGETS = "Targets: none. Label no box: return every list empty and give only the description."


def _rect(box: Box) -> str:
    return ",".join(str(v) for v in box.bbox)


def build_blocks(frame: Frame, fb: FrameBoxes, plan: CallPlan, arm: str, scale: float, frame_png: Path,
                 overlay_png: Path | None, reference: str = "ids") -> list[dict]:
    """The user turn. reference "ids": two images (the clean frame, the numbered overlay) and the boxes and targets by
    id. reference "coords": the clean frame alone, every box and every target as a rectangle x0,y0,x1,y1 in the
    unscaled frame, and no id anywhere (the answer names boxes by points). The targets line is the only thing an
    incremental call changes; a call with no target is still made, for the description: said outright, or the model
    labels every box anyway."""
    if arm != "A":
        raise ValueError(f"no user turn for arm {arm!r}")
    if reference not in ("ids", "coords"):
        raise ValueError(f"no user turn for reference {reference!r}")
    coords = reference == "coords"
    by_id = {b.id: b for b in fb.boxes}
    name = (lambda ids: "; ".join(_rect(by_id[i]) for i in ids)) if coords else (lambda ids: ", ".join(ids))
    ids = [b.id for b in fb.boxes]
    if not plan.targets:
        targets = NO_TARGETS
    elif list(plan.targets) == ids:
        targets = "Targets: all boxes."
    else:
        targets = f"Targets: {name(plan.targets)}."
    if coords:
        w, h = frame.width, frame.height
        where = f"Coordinates are pixels of the {w}x{h} frame: top-left origin, x1 and y1 exclusive."
        if scale != 1.0:
            where += f" The image is scaled by {scale:g}; every coordinate is in the unscaled {w}x{h} frame."
        blocks = [
            text_block(f"Screenshot (frame {frame.frame}, t={frame.t_settled:.2f}s):"), frame_block(frame_png, scale),
            text_block(where),
            text_block(f"Boxes, as x0,y0,x1,y1 in reading order: {name(ids)}." if ids else "Boxes: none."),
            text_block(targets),
        ]
    else:
        blocks = [
            text_block(f"Image 1 (clean frame {frame.frame}, t={frame.t_settled:.2f}s):"), frame_block(frame_png, scale),
            text_block("Image 2 (same frame with numbered boxes):"), image_block(overlay_png),
            text_block(f"Boxes: {name(ids)}." if ids else "Boxes: none."),
            text_block(targets),
        ]
    animating = [b.id for b in fb.boxes if b.in_churn]
    if animating:
        blocks.append(text_block(f"Boxes inside animating areas (low confidence): {name(animating)}."))
    if not frame.settled:
        blocks.append(text_block("This frame was captured while the screen was still changing (not settled)."))
    blocks.append(text_block("Return the JSON object."))
    return blocks


def input_hashes(frame: Frame, overlay_png: Path | None, blocks: list[dict]) -> list[str]:
    """Every byte of the user turn is covered: the frame's hash, the overlay's hash, the text (the scale is in the
    prompt version)."""
    return [frame.sha256, sha256_file(overlay_png) if overlay_png else "-",
            sha256_obj([b["text"] for b in blocks if b["type"] == "text"])]
