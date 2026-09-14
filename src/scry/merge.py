from __future__ import annotations

import logging
import statistics

from scry.config import Config, MergeConfig, config_hash
from scry.jsonl import write_jsonl
from scry.run import Run
from scry.schemas import (BBox, FrameRecord, Line, OcrFrame, OcrLine, PerceptionRecord, Region, Stage1Record, VlmPerception,
                        VlmRegion)
from scry.textdiff import levenshtein, norm, similarity

log = logging.getLogger(__name__)


# ---------- geometry ----------
def union(boxes: list[BBox]) -> BBox | None:
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def _h(b: BBox) -> int:
    return b[3] - b[1]


def _median_h(boxes: list[BBox], default: float = 16.0) -> float:
    hs = [_h(b) for b in boxes if b is not None and _h(b) > 0]
    return float(statistics.median(hs)) if hs else default


# ---------- agreement (§9.2) ----------
def agreement(ocr: str, vlm: str, cfg: MergeConfig) -> tuple[bool, str | None]:
    if norm(ocr) == norm(vlm):
        return True, None
    toks = ocr.split()
    if len(toks) >= 2:
        if len(toks[0]) <= cfg.glyph_max_len and norm(" ".join(toks[1:])) == norm(vlm):
            return True, toks[0]
        if len(toks[-1]) <= cfg.glyph_max_len and norm(" ".join(toks[:-1])) == norm(vlm):
            return True, toks[-1]
    return False, None


def _matches(ocr: str, vlm: str, cfg: MergeConfig) -> bool:
    if similarity(ocr, vlm) >= cfg.align_sim:
        return True
    return min(len(norm(ocr)), len(norm(vlm))) <= cfg.align_short_len and levenshtein(ocr, vlm) <= cfg.align_short_lev


def _make_line(marks: list[OcrLine], vlm: str | None, cfg: MergeConfig, row_rejected: bool = False) -> Line:
    text = " ".join(m.text for m in marks)
    agree, stripped = (None, None)
    if vlm is not None:
        agree, stripped = agreement(text, vlm, cfg)
    return Line(id=marks[0].id, marks=[m.id for m in marks], bbox=union([m.bbox for m in marks]), ocr=text,
                ocr_conf=min(m.conf for m in marks), vlm=vlm, agree=agree, in_churn=any(m.in_churn for m in marks),
                ocr_glyph_stripped=stripped, confusable=any(m.confusable for m in marks), row_rejected=row_rejected)


# ---------- rows (§9.0) ----------
def _row_plausible(ms: list[OcrLine], med_h: float, cfg: MergeConfig) -> bool:
    ycs = [(m.bbox[1] + m.bbox[3]) / 2 for m in ms]
    if max(ycs) - min(ycs) > cfg.row_y_tol * med_h:
        return False
    for a, b in zip(ms, ms[1:]):
        if b.bbox[0] - a.bbox[2] > cfg.row_gap_lines * med_h:
            return False
    return True


def build_region_lines(vr: VlmRegion, ocr_by_id: dict[str, OcrLine], cfg: MergeConfig) -> tuple[list[Line], int, list[tuple[int, str]]]:
    marks_all = [ocr_by_id[m] for row in vr.rows for m in row if m in ocr_by_id]
    med_h = _median_h([m.bbox for m in marks_all])
    lines: list[Line] = []
    rejected = 0
    pending: list[tuple[int, str]] = []
    seen: set[str] = set()
    vcount = 0
    for k, row in enumerate(vr.rows):
        vtext = vr.vlm_lines[k] if k < len(vr.vlm_lines) else None
        ms = [ocr_by_id[m] for m in row if m in ocr_by_id and m not in seen]
        if not row or not ms:
            if vtext is not None:
                vcount += 1
                lines.append(Line(id=f"v{vcount}", marks=[], bbox=None, ocr=None, ocr_conf=None, vlm=vtext, agree=None, in_churn=None))
            continue
        ms.sort(key=lambda m: m.bbox[0])
        plausible = _row_plausible(ms, med_h, cfg) and len(ms) == len(row)  # a duplicated or unknown mark makes the row implausible
        if plausible:
            lines.append(_make_line(ms, vtext, cfg))
            seen.update(m.id for m in ms)
        else:
            rejected += 1
            for m in ms:
                lines.append(_make_line([m], None, cfg, row_rejected=True))
                seen.add(m.id)
            if vtext is not None:
                pending.append((len(lines) - len(ms), vtext))
    return lines, rejected, pending


def align_repair(lines: list[Line], pending: list[tuple[int, str]], cfg: MergeConfig) -> None:
    """LCS-style repair: match pending VLM texts to lines that have no VLM text (rejected rows), in order."""
    if not pending:
        return
    free = [l for l in lines if l.vlm is None and l.ocr is not None]
    texts = [t for _, t in pending]
    i = j = 0
    while i < len(free) and j < len(texts):
        matched = False
        for take in (1, 2, 3):
            if j + take > len(texts):
                break
            cand = " ".join(texts[j:j + take])
            if _matches(free[i].ocr, cand, cfg):
                free[i].vlm = cand
                free[i].agree, free[i].ocr_glyph_stripped = agreement(free[i].ocr, cand, cfg)
                j += take
                matched = True
                break
        if not matched:
            if similarity(free[i].ocr, texts[j]) < 0.3 and i + 1 < len(free) and _matches(free[i + 1].ocr, texts[j], cfg):
                i += 1
                continue
            j += 1
            continue
        i += 1


# ---------- regions (§9.1, §9.3) ----------
def _children(rid: str, regions: list[Region]) -> list[Region]:
    return [r for r in regions if r.parent == rid]


def _descendant_lines(rid: str, regions: list[Region]) -> list[Line]:
    out: list[Line] = []
    for c in _children(rid, regions):
        out += [l for l in c.lines if l.bbox] + _descendant_lines(c.id, regions)
    return out


def region_bbox(rid: str, regions: list[Region]) -> BBox | None:
    r = next(x for x in regions if x.id == rid)
    boxes = [l.bbox for l in r.lines if l.bbox]
    for c in _children(rid, regions):
        cb = region_bbox(c.id, regions)
        if cb:
            boxes.append(cb)
    return union(boxes)


def _ancestors(r: Region, by_id: dict[str, Region]) -> set[str]:
    out: set[str] = set()
    p = r.parent
    while p and p in by_id and p not in out:
        out.add(p)
        p = by_id[p].parent
    return out


def _related(a: Region, b: Region, regions: list[Region]) -> bool:
    """Ancestor/descendant, or occlusion between the regions or any of their ancestors (a terminal that occludes a
    browser window also occludes the browser's panes)."""
    by_id = {r.id: r for r in regions}
    anc_a, anc_b = _ancestors(a, by_id) | {a.id}, _ancestors(b, by_id) | {b.id}
    return a.id in anc_b or b.id in anc_a or bool(anc_a & set(b.occludes)) or bool(anc_b & set(a.occludes))


def layout_conf(region: Region, regions: list[Region]) -> float:
    score = region.conf
    lines = [l for l in region.lines if l.bbox]
    if not lines or region.bbox is None:
        return round(min(score, 0.5), 3)
    penalty = 0.0
    for other in regions:
        if other.id == region.id or _related(region, other, regions):
            continue
        olines = [l for l in other.lines if l.bbox]
        hit = False
        for l in lines:
            for m in olines:
                v = min(l.bbox[3], m.bbox[3]) - max(l.bbox[1], m.bbox[1])
                hz = min(l.bbox[2], m.bbox[2]) - max(l.bbox[0], m.bbox[0])
                if v >= 0.5 * _h(l.bbox) and hz > 0:
                    hit = True
                    break
            if hit:
                break
        if hit:
            penalty += 0.3
    score -= min(penalty, 0.6)
    rows = lines + _descendant_lines(region.id, regions)  # a window's text may live in its panes
    med = _median_h([l.bbox for l in rows])
    coverage = (len(rows) * med) / max(_h(region.bbox), 1)
    if coverage < 0.3:
        score -= 0.2
    if len(rows) == 1:  # a window with one title row and thirty pane rows is not a singleton
        score = min(score, 0.6)
    return round(max(0.0, min(1.0, score)), 3)


# ---------- focus (§9.4) ----------
def _root(rid: str, regions: list[Region]) -> str:
    by_id = {r.id: r for r in regions}
    seen = {rid}
    while by_id[rid].parent and by_id[rid].parent in by_id and by_id[rid].parent not in seen:
        rid = by_id[rid].parent
        seen.add(rid)
    return rid


def caret_region(caret: BBox | None, regions: list[Region]) -> str | None:
    """caret is a [x0, y0, x1, y1] box (§10.5)."""
    if caret is None:
        return None
    cx, cy = (caret[0] + caret[2]) / 2, (caret[1] + caret[3]) / 2
    best, best_d = None, None
    for r in regions:
        if r.bbox is None:
            continue
        lh = _median_h([l.bbox for l in r.lines if l.bbox])
        x0, y0, x1, y1 = r.bbox[0] - lh, r.bbox[1] - lh, r.bbox[2] + lh, r.bbox[3] + lh
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            d = 0.0
        else:
            dx = max(r.bbox[0] - cx, 0, cx - r.bbox[2])
            dy = max(r.bbox[1] - cy, 0, cy - r.bbox[3])
            d = (dx * dx + dy * dy) ** 0.5
            if d > 2 * lh:
                continue
        if best_d is None or d < best_d:
            best, best_d = r.id, d
    return _root(best, regions) if best else None


def combine_focus(caret_r: str | None, retro_r: str | None, vlm_r: str | None, vlm_conf: float) -> tuple[str | None, float | None, list[str]]:
    """§9.4 combination table; a caret/retrospective conflict caps confidence at 0.6 whatever the VLM says."""
    computed = retro_r or caret_r
    if computed:
        disagree = bool(caret_r and retro_r and caret_r != retro_r)
        signals = [s for s, v in (("caret", caret_r), ("retro", retro_r)) if v == computed]
        if vlm_r is None:
            return computed, (0.6 if disagree else 0.7), signals
        if vlm_r == computed:
            return computed, (0.6 if disagree else 0.9), signals + ["vlm"]
        return computed, 0.6, signals + [f"vlm:{vlm_r}@0.3"]
    if vlm_r:
        return vlm_r, 0.5, ["vlm"]
    return None, None, []


# ---------- frame merge ----------
def merge_frame(s1: Stage1Record, of: OcrFrame, perc: PerceptionRecord, cfg: MergeConfig) -> FrameRecord:
    ocr_by_id = {l.id: l for l in of.lines}
    regions: list[Region] = []
    rows_rejected = 0
    unassigned: list[Line] = []
    description = ""
    vlm_focus, vlm_conf = None, 0.0
    out: VlmPerception | None = perc.output
    if out is None:
        lines = [_make_line([l], None, cfg) for l in sorted(of.lines, key=lambda l: (l.bbox[1], l.bbox[0]))]
        regions = [Region(id="r1", kind="unknown", name="screen", app="unknown", parent=None, bbox=union([l.bbox for l in lines]),
                          conf=0.0, layout_conf=0.0, lines=lines)]
    else:
        for vr in out.regions:
            lines, rej, pending = build_region_lines(vr, ocr_by_id, cfg)
            align_repair(lines, pending, cfg)
            rows_rejected += rej
            regions.append(Region(id=vr.id, kind=vr.kind, name=vr.name, app=vr.app, parent=vr.parent, bbox=None, conf=vr.conf,
                                  layout_conf=0.0, occludes=list(vr.occludes), lines=lines))
        for r in regions:
            r.bbox = region_bbox(r.id, regions)
        for r in regions:
            r.layout_conf = layout_conf(r, regions)
        unassigned = [_make_line([ocr_by_id[m]], None, cfg) for m in out.unassigned_line_ids if m in ocr_by_id]
        description = out.description
        vlm_focus, vlm_conf = out.focused_region, out.focused_conf
    focused, fconf, signals = combine_focus(caret_region(s1.caret, regions), None, vlm_focus, vlm_conf)
    return FrameRecord(video_id=s1.video_id, frame=s1.frame, t_change=s1.t_change, t_settled=s1.t_settled, t_end=s1.t_end,
                       settled=s1.settled, png=s1.png, overlay=f"overlays/{s1.frame:05d}.png", sha256=s1.sha256, width=s1.width,
                       height=s1.height, churn_regions=s1.churn_regions, caret=s1.caret, focused_region=focused, focused_conf=fconf,
                       focused_signals=signals, description=description, regions=regions, unassigned_lines=unassigned,
                       grouping_repairs=perc.repairs, rows_rejected=rows_rejected, label_clashes=perc.label_clashes,
                       vlm_model=perc.model, prompt_version=perc.prompt_version, error=perc.error)


def run_merge(run: Run, cfg: Config) -> None:
    inputs = [run.stage1, run.ocr, run.perception]
    ch = config_hash(cfg, "merge")
    if run.stage_up_to_date("merge", inputs, ch):
        log.info("merge up to date")
        return
    s1 = {r.frame: r for r in run.load_stage1()}
    ocr = {f.frame: f for f in run.load_ocr()}
    percs = {p.frame: p for p in run.load_perception()}
    records = [merge_frame(s1[f], ocr[f], percs.get(f, PerceptionRecord(frame=f, model="", prompt_version="", output=None, error="missing")), cfg.merge)
               for f in sorted(s1) if f in ocr]
    write_jsonl(run.frames, records)
    lines = [l for r in records for reg in r.regions for l in reg.lines]
    run.stage_done("merge", inputs, ch, frames=len(records), lines=len(lines),
                   agree=sum(1 for l in lines if l.agree), ocr_only=sum(1 for l in lines if l.vlm is None and l.ocr),
                   vlm_only=sum(1 for l in lines if l.ocr is None), rows_rejected=sum(r.rows_rejected for r in records))
