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
from scry.schemas import Frame, FrameBoxes


def frame_block(frame_png: Path, scale: float) -> dict:
    """The clean frame as an image block: the file as it is at scale 1, otherwise downscaled in memory, never written."""
    if scale == 1.0:
        return image_block(frame_png)
    buf = io.BytesIO()
    scale_image(Image.open(frame_png).convert("RGB"), scale).save(buf, format="PNG", compress_level=1)
    data = base64.standard_b64encode(buf.getvalue()).decode()
    return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}}


def build_blocks(frame: Frame, fb: FrameBoxes, plan: CallPlan, arm: str, scale: float, frame_png: Path,
                 overlay_png: Path | None) -> list[dict]:
    """Arm A: the clean frame, the overlay with every box numbered, the box ids. Arm D: the clean frame alone, and every
    box as its id and rectangle, always in pixels of the unscaled frame. From the targets on, the two turns are the same."""
    if arm not in ("A", "D"):
        raise ValueError(f"no user turn for arm {arm!r}")
    ids = [b.id for b in fb.boxes]
    if not plan.targets:
        targets = "Targets: none."
    elif list(plan.targets) == ids:
        targets = "Targets: all boxes."
    else:
        targets = f"Targets: {', '.join(plan.targets)}."
    if arm == "A":
        blocks = [
            text_block(f"Image 1 (clean frame {frame.frame}, t={frame.t_settled:.2f}s):"), frame_block(frame_png, scale),
            text_block("Image 2 (same frame with numbered boxes):"), image_block(overlay_png),
            text_block(f"Boxes: {', '.join(ids)}." if ids else "Boxes: none."),
        ]
    else:
        size = f"{frame.width}x{frame.height}"
        coords = f"Coordinates are pixels of the {size} frame: top-left origin, x1 and y1 exclusive."
        if scale != 1.0:
            coords += f" The image is scaled by {scale:g}; every coordinate is in the unscaled {size} frame."
        listed = "; ".join(f"{b.id}: {','.join(map(str, b.bbox))}" for b in fb.boxes)
        blocks = [
            text_block(f"Screenshot (frame {frame.frame}, t={frame.t_settled:.2f}s):"), frame_block(frame_png, scale),
            text_block(coords),
            text_block(f"Boxes, as id: x0,y0,x1,y1 in reading order: {listed}." if ids else "Boxes: none."),
        ]
    blocks.append(text_block(targets))
    animating = [b.id for b in fb.boxes if b.in_churn]
    if animating:
        blocks.append(text_block(f"Boxes inside animating areas (low confidence): {', '.join(animating)}."))
    if not frame.settled:
        blocks.append(text_block("This frame was captured while the screen was still changing (not settled)."))
    blocks.append(text_block("Return the JSON object."))
    return blocks


def input_hashes(frame: Frame, overlay_png: Path | None, blocks: list[dict]) -> list[str]:
    """Every byte of the user turn is covered: the frame's hash, the overlay's hash ("-" under arm D, which sends
    none), the text, which under arm D holds the rectangles (the scale is in the prompt version)."""
    return [frame.sha256, sha256_file(overlay_png) if overlay_png else "-",
            sha256_obj([b["text"] for b in blocks if b["type"] == "text"])]
