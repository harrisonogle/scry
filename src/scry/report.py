"""`scry report`: what track measured, as Markdown, and evidence sheets to read the records against the frames.
Not a stage: no manifest entry, always regenerated. It states no pass or fail and compares with no threshold."""
from __future__ import annotations

import json
import random
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

from scry.config import Config
from scry.groundtruth import exact_rate, matching_lifetimes, parse_commands, score_exact
from scry.metrics import box_stability, fragmentation, incremental_projection, select, totals, touched_share_low_half
from scry.overlay import _font
from scry.run import Run
from scry.schemas import BBox, FrameBoxes, parse_box_ref
from scry.track.pixels import grow

RECORD_KINDS = ("reread", "appended", "truncated", "changed", "appeared", "removed")
TEXT_CHANGE_KINDS = ("appended", "truncated", "changed")
MAX_TEXT_CHANGES = 20  # lines per change in "Text changes"
MAX_MOVES = 10  # pairs per change in "Moves"
MAX_UNSTABLE = 50  # lifetimes in "Unstable lifetimes"


def _code(text: str) -> str:
    """The exact string as a Markdown code span (safe inside a table cell)."""
    fence = "``" if "`" in text else "`"
    pad = " " if "`" in text else ""
    return f"{fence}{pad}{text}{pad}{fence}".replace("|", "\\|")


def _ranges(frames: list[int]) -> str:
    """[0, 1, 2, 5] → "0–2, 5"."""
    out, i = [], 0
    while i < len(frames):
        j = i
        while j + 1 < len(frames) and frames[j + 1] == frames[j] + 1:
            j += 1
        out.append(str(frames[i]) if i == j else f"{frames[i]}–{frames[j]}")
        i = j + 1
    return ", ".join(out)


def _kinds(counter: dict) -> str:
    return ", ".join(f"{k} {counter[k]}" for k in RECORD_KINDS if counter.get(k)) or "–"


def _dict_lines(d: dict) -> list[str]:
    return [f"- {k}: {json.dumps(v, ensure_ascii=False)}" for k, v in d.items()]


def _per(total, n) -> str:
    return f"{total / n:.3f} s" if total is not None and n else "n/a"


def _box_index(boxes: list[FrameBoxes]) -> dict[str, BBox]:
    return {f"{fb.frame}:{b.id}": b.bbox for fb in boxes for b in fb.boxes}


def build_report(run: Run, cfg: Config, frames: tuple[int, int] | None = None, ground_truth: Path | None = None) -> str:
    all_boxes = run.load_boxes()
    boxes, changes, lifetimes = select(all_boxes, run.load_changes(), run.load_lifetimes(), frames)
    stages = run.manifest_read().get("stages", {})
    read, track = stages.get("read", {}), stages.get("track", {})
    L: list[str] = ["# track report", ""]

    L += ["## Run", "",
          f"- run directory: {run.root}",
          f"- frame range: {'all' if frames is None else f'{frames[0]}–{frames[1]}'}",
          f"- frames: {len(boxes)}; boxes: {sum(len(b.boxes) for b in boxes)}; transitions: {len(changes)}; lifetimes: {len(lifetimes)}",
          f"- read engine (manifest): {json.dumps(read.get('engine'), ensure_ascii=False)}",
          f"- read dropped empty boxes (whole run): {read.get('dropped_empty', 'n/a')}",
          f"- track.margin (manifest): {track.get('margin', 'n/a')} × the median box height",
          f"- wall time (manifest, whole run): read {_per(read.get('seconds'), read.get('frames'))} per frame; "
          f"track {_per(track.get('seconds'), track.get('transitions'))} per pair",
          f"- θpix {cfg.decode.detect.theta_pix}, θmin {cfg.decode.detect.theta_min}",
          "", "model calls: none, $0.00", ""]

    L += ["## Transitions", "",
          "| id | frames | kind | changed % | components | textless | touched share | rect-only | records | moved | same place | unchanged | variants | flicker new / lost | revert share |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in changes:
        p = c.pixels
        px = [f"{p.changed_fraction * 100:.4f}", p.components, p.textless, p.touched_share, p.rect_only] if p else ["–"] * 5
        cells = [c.id, f"{c.from_frame}→{c.to_frame}", c.kind, *px, _kinds(Counter(r.kind for r in c.records)), len(c.moved), c.same_place,
                 c.unchanged, c.variants, f"{len(c.flicker_new)} / {len(c.flicker_lost)}", c.reverts.share if c.reverts else "–"]
        L.append("| " + " | ".join(str(x) for x in cells) + " |")
    L.append("")

    L += ["## Totals", "", *_dict_lines(totals(changes)), ""]
    L += ["## Guards", "", f"- box_stability: {box_stability(changes)}", f"- touched_share_low_half: {touched_share_low_half(changes)}",
          f"- rect_only (total): {totals(changes)['rect_only']}", ""]

    frag = fragmentation(lifetimes)
    L += ["## Lifetimes", "", *_dict_lines({k: v for k, v in frag.items() if k != "top"}), "", "| text | lifetimes |", "|---|---|"]
    L += [f"| {_code(text)} | {n} |" for text, n in frag["top"]]
    L.append("")

    L += ["## Incremental annotation projection", "",
          "A labelling call for the first frame and for every transition in which pixels changed; the targets are the boxes whose lifetime starts or continues by a move.",
          "", *_dict_lines(incremental_projection(boxes, changes, lifetimes)), ""]

    L += ["## Text changes", ""]
    for c in changes:
        found = [(j, r) for j, r in enumerate(c.records) if r.kind in TEXT_CHANGE_KINDS]
        for j, r in found[:MAX_TEXT_CHANGES]:
            cont = f" (continues {r.continues})" if r.continues else ""
            L.append(f"- {c.id}/{j} {c.from_frame}→{c.to_frame} {r.kind}: {_code(r.before.text)} → {_code(r.after.text)}{cont}")
        if len(found) > MAX_TEXT_CHANGES:
            L.append(f"- {c.id}: … and {len(found) - MAX_TEXT_CHANGES} more")
    L.append("")

    rects, texts = _box_index(all_boxes), {f"{fb.frame}:{b.id}": b.text for fb in all_boxes for b in fb.boxes}
    L += ["## Moves", ""]
    for c in changes:
        if c.moved:
            L.append(f"- {c.id} {c.from_frame}→{c.to_frame}: {len(c.moved)} moved")
            L += [f"  - {_code(texts.get(q, '?'))} {p} {rects.get(p)} → {q} {rects.get(q)}" for p, q in c.moved[:MAX_MOVES]]
    L.append("")

    unstable = sorted((l for l in lifetimes if l.unstable), key=lambda l: (-l.sightings, int(l.id[1:])))
    L += ["## Unstable lifetimes", "", f"{len(unstable)} unstable of {len(lifetimes)}; up to {MAX_UNSTABLE} listed, by sightings.", ""]
    for l in unstable[:MAX_UNSTABLE]:
        L.append(f"- {l.id}: {l.sightings} sightings, frames {l.first.frame}–{l.last.frame}, majority {_code(l.text)}")
        L += [f"  - ×{len(fr)} {_code(reading)} at frames {_ranges(fr)}" for reading, fr in l.readings.items()]
    L.append("")

    L += ["## Reverts", "",
          "Share: of the pixels the previous transition changed, the part that is back to what it was before it. Largest share first.", ""]
    L += [f"- {c.id} {c.from_frame}→{c.to_frame} reverts {c.reverts.of}: share {c.reverts.share}, held {c.reverts.hold_s} s"
          for c in sorted((c for c in changes if c.reverts), key=lambda c: (-c.reverts.share, int(c.id[1:])))]
    L.append("")

    if ground_truth is not None:
        executed, never = parse_commands(Path(ground_truth).read_text())
        scored = score_exact(executed, lifetimes)
        hit, rated = exact_rate(scored)
        yn = lambda v: "yes" if v else "no"
        L += ["## Commands", "", f"Ground truth: {ground_truth}. Reader: OCR (lifetime majority readings).", "",
              "| # | text | scorable | exact | matches | lifetime | first frame | frame error | t error |", "|---|---|---|---|---|---|---|---|---|"]
        L += [f"| {r['n']} | {_code(r['text'])} | {yn(r['scorable'])} | {yn(r['exact'])} | {r['matches']} | {r['lifetime']} | {r['first_frame']} | "
              f"{r['frame_error']} | {r['t_error']} |" for r in scored]
        L += ["", f"exact: {hit} / {rated} scorable executed entries", "", "Appeared on screen but never run (information only; enters no rate):", "",
              "| text | ground-truth frames | matching lifetimes (id, first–last frame, sightings) |", "|---|---|---|"]
        for e in never:
            found = ", ".join(f"{l.id} {l.first.frame}–{l.last.frame} ×{l.sightings}" for l in matching_lifetimes(e, lifetimes)) or "none"
            L.append(f"| {_code(e.text)} | {_ranges(e.frames)} | {found} |")
        L += ["", "The OCR reader's exact rate is a lower bound: a command that OCR splits over two boxes cannot be exact until `run` links exist.", ""]
    return "\n".join(L)


# ---------- evidence sheets ----------
_OUTLINE = (255, 0, 255)


def _crop(img: Image.Image, rect: BBox) -> Image.Image:
    """The rectangle grown on every side by its own height and clipped (scale-free, independent of the margin under
    test), with the rectangle itself outlined one pixel outside its edge."""
    x0, y0, x1, y1 = grow(rect, rect[3] - rect[1], (img.height, img.width))
    out = img.crop((x0, y0, x1, y1)).convert("RGB")
    ImageDraw.Draw(out).rectangle((rect[0] - x0 - 1, rect[1] - y0 - 1, rect[2] - x0, rect[3] - y0), outline=_OUTLINE, width=1)
    return out


def _sheet(rows: list[tuple[str, Image.Image]], font) -> Image.Image:
    """Captioned crops stacked top to bottom."""
    asc, desc = font.getmetrics()
    line = asc + desc + 4
    width = max(max(im.width for _, im in rows), max(int(font.getlength(cap)) + 8 for cap, _ in rows))
    sheet = Image.new("RGB", (width, sum(line + im.height + 4 for _, im in rows)), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for cap, im in rows:
        draw.text((4, y + 2), cap, fill=(0, 0, 0), font=font)
        sheet.paste(im, (0, y + line))
        y += line + im.height + 4
    return sheet


def write_sheets(run: Run, cfg: Config, out_dir: Path, frames: tuple[int, int] | None, per_kind: int, seed: int) -> list[Path]:
    """One PNG per sampled record, unstable lifetime and flicker box: up to `per_kind` of each record kind and of each of
    the other two, drawn with random.Random(seed). A sheet that needs a missing PNG is skipped. A revert has no sheet:
    it is one number over a whole transition and has no rectangle to crop."""
    all_boxes = run.load_boxes()
    _, changes, lifetimes = select(all_boxes, run.load_changes(), run.load_lifetimes(), frames)
    png = {f.frame: run.root / f.png for f in run.load_frames()}
    rects, texts = _box_index(all_boxes), {f"{fb.frame}:{b.id}": b.text for fb in all_boxes for b in fb.boxes}
    font = _font(cfg.overlay)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    images: dict[int, Image.Image] = {}

    def image(frame: int) -> Image.Image | None:
        if frame not in images:
            path = png.get(frame)
            if path is None or not path.is_file():
                return None
            if len(images) >= 8:
                del images[next(iter(images))]
            images[frame] = Image.open(path).convert("RGB")
        return images[frame]

    def save(name: str, parts: list[tuple[int, BBox, str]]) -> Path | None:
        rows = []
        for frame, rect, caption in parts:
            img = image(frame)
            if img is None:
                return None
            rows.append((f"frame {frame}: {caption}", _crop(img, rect)))
        path = out_dir / name
        _sheet(rows, font).save(path)
        return path

    rng = random.Random(seed)
    pick = lambda population: rng.sample(population, min(per_kind, len(population)))
    jobs: list[tuple[str, list[tuple[int, BBox, str]]]] = []
    for kind in RECORD_KINDS:
        for c, j, r in pick([(c, j, r) for c in changes for j, r in enumerate(c.records) if r.kind == kind]):
            jobs.append((f"{c.id}-r{j}-{kind}.png", [(c.from_frame, r.rect, f"{kind}, before: {r.before.text if r.before else '(no box)'}"),
                                                      (c.to_frame, r.rect, f"after: {r.after.text if r.after else '(no box)'}")]))
    for l in pick([l for l in lifetimes if l.unstable]):
        ref_at = {parse_box_ref(ref)[0]: ref for ref in l.boxes}
        readings = [l.text] + [r for r in l.readings if r != l.text]  # majority first
        jobs.append((f"{l.id}.png", [(l.readings[r][0], rects[ref_at[l.readings[r][0]]], f"×{len(l.readings[r])} {r}") for r in readings]))
    for c, which, ref in pick([(c, w, ref) for c in changes for w, refs in (("new", c.flicker_new), ("lost", c.flicker_lost)) for ref in refs]):
        jobs.append((f"{c.id}-flicker-{which}-{parse_box_ref(ref)[1]}.png",
                     [(c.from_frame, rects[ref], f"flicker {which} {ref}: {texts[ref]}" if which == "lost" else "earlier frame"),
                      (c.to_frame, rects[ref], f"flicker {which} {ref}: {texts[ref]}" if which == "new" else "later frame")]))
    paths = [save(name, parts) for name, parts in sorted(jobs, key=lambda j: min(f for f, _, _ in j[1]))]  # by frame: few image loads
    return [p for p in paths if p is not None]


def write_report(run: Run, cfg: Config, out: str, frames: tuple[int, int] | None, ground_truth: Path | None, sheets: bool, per_kind: int,
                 seed: int) -> tuple[Path, list[Path]]:
    """The report file inside the run directory and, with `sheets`, its evidence sheets in `<out stem>-sheets/`, emptied first."""
    path = run.root / Path(out).name
    path.write_text(build_report(run, cfg, frames, ground_truth))
    written: list[Path] = []
    if sheets:
        sheet_dir = run.root / f"{path.stem}-sheets"
        if sheet_dir.exists():
            shutil.rmtree(sheet_dir)
        written = write_sheets(run, cfg, sheet_dir, frames, per_kind, seed)
    return path, written
