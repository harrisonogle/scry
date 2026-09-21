from __future__ import annotations

PRICES = {  # $ per million tokens, input / output / cache read (2026-09-13 list prices)
    "claude-opus-5": (5.0, 25.0, 0.5),
    "claude-sonnet-5": (2.0, 10.0, 0.2),
    "claude-haiku-4-5": (1.0, 5.0, 0.1),
}


def estimate_cost(usage: dict, model: str) -> float:
    pin, pout, pcache = PRICES.get(model, (5.0, 25.0, 0.5))
    return round((usage.get("input_tokens", 0) * pin + usage.get("output_tokens", 0) * pout + usage.get("cache_read_input_tokens", 0) * pcache) / 1e6, 4)
