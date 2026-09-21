from __future__ import annotations

from scry.config import Config
from scry.run import Run
from scry.schemas import OcrFrame, PerceptionRecord, Transition
from scry.textdiff import norm, similarity

PRICES = {  # $ per million tokens, input / output / cache read (2026-09-13 list prices)
    "claude-opus-5": (5.0, 25.0, 0.5),
    "claude-sonnet-5": (2.0, 10.0, 0.2),
    "claude-haiku-4-5": (1.0, 5.0, 0.1),
}


def estimate_cost(usage: dict, model: str) -> float:
    pin, pout, pcache = PRICES.get(model, (5.0, 25.0, 0.5))
    return round((usage.get("input_tokens", 0) * pin + usage.get("output_tokens", 0) * pout + usage.get("cache_read_input_tokens", 0) * pcache) / 1e6, 4)


def summarize(frames: list[dict]) -> dict:
    """frames: [{"settled": bool, "lines": [{"agree": bool|None, "ocr": str|None}, ...]}, ...]"""
    n = len(frames)
    lines = [l for f in frames for l in f.get("lines", [])]
    nl = len(lines) or 1
    return {"frames": n, "settled_fraction": round(sum(1 for f in frames if f.get("settled")) / max(n, 1), 3),
            "lines_per_frame": round(len(lines) / max(n, 1), 2),
            "agree_fraction": round(sum(1 for l in lines if l.get("agree") is True) / nl, 3),
            "ocr_only_fraction": round(sum(1 for l in lines if l.get("agree") is None and l.get("ocr") is not None) / nl, 3),
            "vlm_only_fraction": round(sum(1 for l in lines if l.get("ocr") is None) / nl, 3)}


def fragment_stability(frames: list, transitions: list) -> float | None:
    """§18.4: fraction of unchanged lines (same fused text in matched units of consecutive frames) whose OCR mark count
    differs — 0.0 means the engine split lines identically frame to frame."""
    by_id = {f.frame: f for f in frames}
    same, differ = 0, 0
    for t in transitions:
        a, b = by_id.get(t.from_frame), by_id.get(t.to_frame)
        if a is None or b is None:
            continue
        for ra, rb, _ in t.regions.matched:
            la = {norm(l.fused): len(l.marks) for l in a.unit_lines(ra) if l.marks}
            for l in b.unit_lines(rb):
                k = norm(l.fused)
                if l.marks and k in la:
                    if la[k] == len(l.marks):
                        same += 1
                    else:
                        differ += 1
    total = same + differ
    return round(differ / total, 3) if total else None


def mark_match(ocr_frames: list[OcrFrame], perception: list[PerceptionRecord], threshold: float = 0.8) -> tuple[int, int]:
    """Rows of VLM output whose transcription resembles the OCR text of the marks the row names (similarity ≥ threshold),
    over all rows with marks and text. Low values mean the model is not reading the overlay ids (ledger L28)."""
    ocr = {f.frame: {l.id: l.text for l in f.lines} for f in ocr_frames}
    hit = total = 0
    for p in perception:
        if p.output is None or p.frame not in ocr:
            continue
        for r in p.output.regions:
            for row, text in zip(r.rows, r.vlm_lines):
                named = " ".join(ocr[p.frame][m] for m in row if m in ocr[p.frame])
                if not row or not text.strip() or not named:
                    continue
                total += 1
                hit += similarity(named, text) >= threshold
    return hit, total


def pixel_gate_counts(ts: list[Transition], max_fraction: float) -> tuple[int, int]:
    """(ops vetoed by the §11.2 pixel gate, transitions whose changed_fraction is at or below the gate's threshold)."""
    with_pixels = [t for t in ts if t.pixels is not None]
    return sum(t.pixels.vetoed for t in with_pixels), sum(1 for t in with_pixels if t.pixels.changed_fraction <= max_fraction)


def diagnostics(run: Run, cfg: Config) -> dict:
    frames = run.load_frames()
    flat = [{"settled": f.settled, "lines": [{"agree": l.agree, "ocr": l.ocr} for r in f.regions for l in r.lines]} for f in frames]
    d = summarize(flat)
    d.update({"rows_rejected": sum(f.rows_rejected for f in frames), "grouping_repairs": sum(f.grouping_repairs for f in frames),
              "label_clashes": sum(f.label_clashes for f in frames), "perception_errors": sum(1 for f in frames if f.error),
              "refusals": sum(1 for f in frames if f.error == "refusal")})
    hit, total = mark_match(run.load_ocr(), run.load_perception())
    d["mark_match_fraction"] = round(hit / total, 3) if total else None
    ts = run.load_transitions()
    d["transitions"] = {k: sum(1 for t in ts if t.kind == k) for k in ("single", "coalesced", "transient_merged", "unsettled", "trivial")}
    d["fragment_stability"] = fragment_stability(frames, ts)
    d["ops_vetoed"], d["pixel_gated_transitions"] = pixel_gate_counts(ts, cfg.diff.pixel_gate_max_fraction)
    interps = run.load_interpretations()
    d["invalid_refs"] = sum(i.invalid_refs for i in interps.values())
    m = run.manifest_read()
    usage_total: dict[str, int] = {}
    cost = 0.0
    hits = misses = 0
    seconds: dict[str, float] = {}
    for name, st in m.get("stages", {}).items():
        u = st.get("usage")
        if u:
            for k, v in u.items():
                usage_total[k] = usage_total.get(k, 0) + v
            cost += estimate_cost(u, st.get("model", ""))
        c = st.get("cache") or {}
        hits += c.get("hits", 0)
        misses += c.get("misses", 0)
        if "seconds" in st:
            seconds[name] = st["seconds"]
    d["usage"] = usage_total
    d["estimated_cost_usd"] = round(cost, 2)
    d["cache"] = {"hits": hits, "misses": misses, "hit_rate": round(hits / (hits + misses), 3) if hits + misses else None}
    d["seconds"] = seconds
    d["versions"] = m.get("versions", {})
    return d
