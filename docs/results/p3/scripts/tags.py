"""Geometry of the overlay at each scale, no model: clashes, tags overlapping other tags, share of box area under tags."""
import math, sys
from pathlib import Path
from PIL import Image
from scry.config import load_config
from scry.run import Run
from scry.overlay import place_label, _scale_box, _font, PAD, _overlap
import inspect
try:
    cfg = load_config(None)
except Exception as e:
    from scry.config import Config; cfg = Config()
font = _font(cfg.overlay)
run = Run(Path('runs/eval/p3/smoke-s100-r1'))
fbs = {fb.frame: fb for fb in run.load_boxes()}
fbs2 = {fb.frame: fb for fb in Run(Path('runs/eval/p3/span2-s100-r1')).load_boxes()}
print('font', cfg.overlay.font_path, cfg.overlay.font_size)
for frame, src in ((150, fbs), (166, fbs2)):
    boxes = src[frame].boxes
    for scale in (1.0, 0.67, 0.5, 0.4, 0.3, 0.25, 0.2):
        W, H = round(1920 * scale), round(1080 * scale)
        rects = [_scale_box(b.bbox, scale) for b in boxes]
        tags = []; clashes = 0
        for box, rect in zip(boxes, rects):
            l, t, r, b = font.getbbox(box.id[1:]); lw, lh = (r - l) + 2 * PAD, (b - t) + 2 * PAD
            x, y, clash = place_label(rect, lw, lh, rects, W, H, tags)
            tags.append((x, y, x + lw, y + lh)); clashes += clash
        # tags painted over by a later tag (any overlap), and boxes whose area is >25% under tags
        over = sum(1 for i, a in enumerate(tags) if any(_overlap(a, c) > 0 for c in tags[i + 1:]))
        over50 = sum(1 for i, a in enumerate(tags) if sum(_overlap(a, c) for c in tags[i + 1:]) >= 0.5 * (a[2]-a[0])*(a[3]-a[1]))
        cov = []
        for rc in rects:
            area = max(1, (rc[2]-rc[0])*(rc[3]-rc[1])); cov.append(min(1.0, sum(_overlap(rc, t) for t in tags) / area))
        print(f'F{frame} scale {scale}: image {W}x{H} boxes {len(boxes)} clashes {clashes} tags overlapped by a later tag {over} (>=50% hidden: {over50}) boxes >25% under tags {sum(c>0.25 for c in cov)} >50%: {sum(c>0.5 for c in cov)} median box height px {sorted(r[3]-r[1] for r in rects)[len(rects)//2]}')
