from __future__ import annotations

import logging

log = logging.getLogger(__name__)

PRICES = {  # $ per million tokens, input / output / cache read (2026-09-13 list prices)
    "claude-opus-5": (5.0, 25.0, 0.5),
    "claude-sonnet-5": (2.0, 10.0, 0.2),
    "claude-haiku-4-5": (1.0, 5.0, 0.1),
}
# a model served on this machine through the openai_compat provider (an mlx-community conversion) bills nothing: price 0,
# and no warning. The electricity and the wall time are the cost, and the run's log carries the seconds per call.
LOCAL_MODEL_PREFIXES = ("mlx-community/",)
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
CACHE_WRITE_MULTIPLIER = 1.25  # × the input price: a write to the default five-minute prompt cache
BATCH_MULTIPLIER = 0.5  # × everything: the Batches API discount
_warned: set[str] = set()


def add_usage(total: dict, usage: dict) -> dict:
    """Add the four usage keys of `usage` into `total` (absent or None counts 0) and return it."""
    for k in USAGE_KEYS:
        total[k] = (total.get(k) or 0) + (usage.get(k) or 0)
    return total


def estimate_cost(usage: dict, model: str, batch: bool = False) -> float:
    """Dollars for a usage dict. A local model (LOCAL_MODEL_PREFIXES) costs 0; any other unknown model is priced as
    claude-opus-5, with one warning per model name."""
    if model.startswith(LOCAL_MODEL_PREFIXES):
        return 0.0
    if model not in PRICES and model not in _warned:
        _warned.add(model)
        log.warning("no price for model %r: priced as claude-opus-5", model)
    pin, pout, pcache = PRICES.get(model, PRICES["claude-opus-5"])
    u = add_usage({}, usage)
    dollars = (u["input_tokens"] * pin + u["output_tokens"] * pout + u["cache_read_input_tokens"] * pcache
               + u["cache_creation_input_tokens"] * pin * CACHE_WRITE_MULTIPLIER) / 1e6
    return round(dollars * (BATCH_MULTIPLIER if batch else 1.0), 4)


def run_costs(manifest: dict) -> dict:
    """One dollar figure per stage that recorded usage, their total, and dollars per emitted frame. A stage's usage
    counts answers served from the call cache, so this is what a cold run would pay at the synchronous price. Halving
    it is no batch price: batched requests mostly write the prompt cache where synchronous ones read it (P4b), and a
    stage that ran in batch mode records what it paid as its own `cost_usd`."""
    entries = manifest.get("stages", {})
    stages = {name: {"usage": e["usage"], "cost_usd": estimate_cost(e["usage"], e.get("model", ""))}
              for name, e in entries.items() if isinstance(e.get("usage"), dict)}
    total = round(sum(s["cost_usd"] for s in stages.values()), 4)
    frames = entries.get("decode", {}).get("emitted") or None
    return {"stages": stages, "total_usd": total, "frames": frames, "per_frame_usd": round(total / frames, 4) if frames else None}
