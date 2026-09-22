"""Presentation assets from one session's run directory (default runs/v2/grouponly-100), drawn from its own records:

  session/NN.png         every settled frame downscaled to 1280 px wide (PNG, or JPEG quality 90 if the PNG set is over 15 MB)
  stages/read/NN.png     every OCR box of the frame (boxes.jsonl) as a thin blue outline
  stages/track/NN.png    the change records of the transition INTO the frame (changes.jsonl): appeared boxes filled green at
                         25 % alpha, changed/reread/appended/truncated boxes filled orange at 25 % alpha, removed boxes as a
                         thin red outline at the rectangle the record holds (where the text was on the previous frame)
  stages/annotate/NN.png the labels in force at the frame (scry.annotate.join.Labels, the view the index uses): each
                         container's bounding rectangle over the boxes assigned to it, windows blue and popups orange, with
                         the container name as a small tag; every pair link as a thin aqua line from the key box's right
                         edge to the value box's left edge; every run as a violet bracket under its boxes
  stages/interpret/NN.png the frame with a card in the top-left corner holding the transition's action, entered_text and
                         submitted (interpretations.jsonl), trimmed to three lines

    uv run python docs/presentation/stages.py [run_dir] [out_dir] [first_frame] [last_frame]

Overlays are drawn at full resolution (2 px strokes) and downscaled with LANCZOS to 1280 px wide. Chart palette.
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from scry.run import Run  # noqa: E402

RUN = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("runs/v2/grouponly-100")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent
FIRST = int(sys.argv[3]) if len(sys.argv) > 3 else 12
LAST = int(sys.argv[4]) if len(sys.argv) > 4 else 31
WIDTH = 1280
BLUE, ORANGE, AQUA, RED, VIOLET, INK = "#2a78d6", "#eb6834", "#1baf7a", "#e34948", "#4a3aa7", "#0b0b0b"
FONT = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
CARD_FONT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)


def rgba(hex_colour: str, alpha: int) -> tuple[int, int, int, int]:
    h = hex_colour.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha


def downscale(im: Image.Image) -> Image.Image:
    h = round(im.height * WIDTH / im.width)
    return im.convert("RGB").resize((WIDTH, h), Image.LANCZOS)


def save(im: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    downscale(im).save(path, optimize=True)


def tag(dr: ImageDraw.ImageDraw, x: int, y: int, text: str, colour: str, font=FONT) -> None:
    w, h = dr.textbbox((0, 0), text, font=font)[2:]
    dr.rectangle([x, y, x + w + 8, y + h + 6], fill=colour)
    dr.text((x + 4, y + 2), text, fill="white", font=font)


def main() -> None:
    run = Run(RUN)
    frames = run.load_frames()
    boxes = {fb.frame: {b.id: b for b in fb.boxes} for fb in run.load_boxes()}
    changes = {c.to_frame: c for c in run.load_changes()}
    interps = run.load_interpretations()
    labels = run.load_labels()

    # 1. the session: every frame at 1280 px wide
    session = OUT / "session"
    session.mkdir(parents=True, exist_ok=True)
    for f in frames:
        im = Image.open(RUN / f.png)
        downscale(im).save(session / f"{f.frame:02d}.png", optimize=True)
    total = sum(p.stat().st_size for p in session.glob("*.png"))
    fmt = "png"
    if total > 15 * 1024 * 1024:
        for p in session.glob("*.png"):
            Image.open(p).save(p.with_suffix(".jpg"), quality=90, optimize=True)
            p.unlink()
        total = sum(p.stat().st_size for p in session.glob("*.jpg"))
        fmt = "jpg"
    print(f"session: {len(frames)} frames as {fmt}, {total / 1e6:.1f} MB")

    # 2. the stage overlays for frames FIRST..LAST
    for f in frames:
        n = f.frame
        if not FIRST <= n <= LAST:
            continue
        base = Image.open(RUN / f.png).convert("RGBA")
        fb = boxes.get(n, {})

        # read: every OCR box, thin blue outline
        im = base.copy()
        dr = ImageDraw.Draw(im)
        for b in fb.values():
            dr.rectangle(list(b.bbox), outline=BLUE, width=2)
        save(im, OUT / "stages" / "read" / f"{n:02d}.png")

        # track: the transition into this frame
        im = base.copy()
        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        c = changes.get(n)
        counts = {"appeared": 0, "changed": 0, "removed": 0}
        if c is not None:
            for r in c.records:
                rect = list(r.rect)
                if r.kind == "appeared":
                    ld.rectangle(rect, fill=rgba(AQUA, 64))
                    counts["appeared"] += 1
                elif r.kind == "removed":
                    ld.rectangle(rect, outline=rgba(RED, 255), width=2)
                    counts["removed"] += 1
                else:  # changed, reread, appended, truncated
                    ld.rectangle(rect, fill=rgba(ORANGE, 64))
                    counts["changed"] += 1
        im = Image.alpha_composite(im, layer)
        save(im, OUT / "stages" / "track" / f"{n:02d}.png")

        # annotate: containers in force (bounding rectangle of their boxes), pair links, run brackets
        im = base.copy()
        dr = ImageDraw.Draw(im)
        n_pairs = n_runs = 0
        if labels is not None:
            groups: dict[tuple[str, str], list[list[int]]] = {}
            for bid, b in fb.items():
                lab = labels.box(f"{n}:{bid}")
                if lab is None or lab.container is None:
                    continue
                groups.setdefault((lab.container.kind, lab.container.name), []).append(list(b.bbox))
            for (kind, name), rects in groups.items():
                x0 = min(r[0] for r in rects) - 4
                y0 = min(r[1] for r in rects) - 4
                x1 = max(r[2] for r in rects) + 4
                y1 = max(r[3] for r in rects) + 4
                colour = ORANGE if kind == "popup" else BLUE
                dr.rectangle([x0, y0, x1, y1], outline=colour, width=2)
                tag(dr, x0, max(0, y0 - 28), f"{kind}: {name[:60]}", colour)
            for link in labels.frame(n).links:
                if link.kind == "pair":
                    keys = [fb[r.split(":")[1]] for r in link.key if r.split(":")[1] in fb]
                    vals = [fb[r.split(":")[1]] for r in link.value if r.split(":")[1] in fb]
                    if keys and vals:
                        k, v = keys[-1], vals[0]
                        dr.line([(k.bbox[2], (k.bbox[1] + k.bbox[3]) // 2), (v.bbox[0], (v.bbox[1] + v.bbox[3]) // 2)], fill=AQUA, width=2)
                        n_pairs += 1
                elif link.kind == "run":
                    members = [fb[r.split(":")[1]] for r in link.boxes if r.split(":")[1] in fb]
                    if len(members) >= 2:
                        x0 = min(m.bbox[0] for m in members)
                        x1 = max(m.bbox[2] for m in members)
                        y = max(m.bbox[3] for m in members) + 3
                        dr.line([(x0, y - 5), (x0, y), (x1, y), (x1, y - 5)], fill=VIOLET, width=2)
                        n_runs += 1
        save(im, OUT / "stages" / "annotate" / f"{n:02d}.png")

        # interpret: a card with the transition's action, entered text and submitted, three lines
        im = base.copy()
        dr = ImageDraw.Draw(im)
        ip = interps.get(c.id) if c is not None else None
        if ip is not None:
            lines = textwrap.wrap(f"{c.id}: {ip.action}", 78)[:2]
            lines.append(f"entered_text: {ip.entered_text!r}   submitted: {ip.submitted}"[:90])
        else:
            lines = [f"frame {n}: no transition record"]
        w = max(dr.textbbox((0, 0), l, font=CARD_FONT)[2] for l in lines) + 40
        h = 44 * len(lines) + 24
        dr.rectangle([24, 24, 24 + w, 24 + h], fill=(252, 252, 251, 235), outline=BLUE, width=2)
        for i, l in enumerate(lines):
            dr.text((44, 36 + 44 * i), l, fill=INK, font=CARD_FONT)
        save(im, OUT / "stages" / "interpret" / f"{n:02d}.png")
        print(f"frame {n:02d}: boxes {len(fb)}, track {counts}, pairs {n_pairs}, runs {n_runs}")


if __name__ == "__main__":
    main()
