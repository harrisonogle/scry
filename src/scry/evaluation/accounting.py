from __future__ import annotations

import json
from pathlib import Path

from scry.costs import PRICES, estimate_cost

BATCH_PRICE_SHARE = 0.5  # the Batch API's list discount; no sibling records a batch price, so a report halves


def _emitted(manifest: dict) -> int | None:
    stages = manifest.get("stages", {})
    for name in ("decode", "stage1"):  # stage1: a pre-re-base source
        n = stages.get(name, {}).get("emitted")
        if n is not None:
            return n
    return None


def projection_frames(manifest: dict) -> int | None:
    """The frame count of the whole source video: of the run this directory was derived from, else its own."""
    subset = manifest.get("subset")
    if not subset:
        return manifest.get("stages", {}).get("decode", {}).get("emitted")
    source = Path(subset["source"]) / "manifest.json"
    return _emitted(json.loads(source.read_text())) if source.exists() else None


def _rates(dollars: float, frames: int, projection: int | None) -> tuple[float | None, float | None]:
    """Dollars per frame and per video; the projection to the whole video is linear."""
    if not frames:
        return None, None
    per_video = None if projection is None else round(dollars / frames * projection, 2)
    return round(dollars / frames, 4), per_video


def cost_summary(manifest: dict, stage_seconds: dict[str, float], frames: int, projection: int | None,
                 default_model: str) -> dict:
    """Dollars and seconds per stage, per frame and per video, read from the manifest's usage and nothing else: a
    stage's usage counts cache hits, so a resumed run cannot under-report. The question set and the judge are apart."""
    stages = manifest.get("stages", {})
    by_stage: dict[str, dict] = {}
    warnings: list[str] = []
    cache_hits = 0
    for name in [*stages, *(s for s in stage_seconds if s not in stages)]:
        entry = stages.get(name, {})
        usage = entry.get("usage")
        model = entry.get("model")
        dollars = 0.0
        if isinstance(usage, dict):
            model = model or default_model
            dollars = estimate_cost(usage, model)
            if model not in PRICES:
                warnings.append(f"no list price for {model}: priced as claude-opus-5")
        hits = (entry.get("cache") or {}).get("hits", 0)
        if hits:
            cache_hits += hits
            warnings.append(f"{hits} cache hits in {name}")
        calls = entry.get("calls")
        if calls is None:
            calls = (entry.get("cache") or {}).get("misses")
        per_frame, per_video = _rates(dollars, frames, projection)
        by_stage[name] = {"dollars": dollars, "dollars_batch": round(dollars * BATCH_PRICE_SHARE, 4),
                          "per_frame": per_frame, "per_video": per_video,
                          "seconds": round(stage_seconds.get(name, 0.0), 1), "calls": calls, "model": model,
                          "usage": usage}
    dollars = round(sum(row["dollars"] for row in by_stage.values()), 4)
    seconds = round(sum(stage_seconds.values()), 1)
    per_frame, per_video = _rates(dollars, frames, projection)
    return {"frames": frames, "projection_frames": projection, "dollars": dollars,
            "dollars_batch": round(dollars * BATCH_PRICE_SHARE, 4), "per_frame": per_frame, "per_video": per_video,
            "seconds": seconds, "seconds_per_frame": round(seconds / frames, 1) if frames else None,
            "cache_hits": cache_hits, "by_stage": by_stage, "warnings": warnings}
