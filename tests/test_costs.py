from fakes import USAGE

from scry.costs import add_usage, estimate_cost, run_costs


def test_estimate_cost():
    assert estimate_cost({"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 0}, "claude-opus-5") == 7.5


def test_estimate_cost_prices_cache_writes():
    usage = {"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 2_000_000, "cache_creation_input_tokens": 1_000_000}
    assert estimate_cost(usage, "claude-opus-5") == 14.75  # 5 + 2.5 + 1 + 6.25
    assert estimate_cost(usage, "claude-opus-5", batch=True) == 7.375
    assert estimate_cost(dict(USAGE), "fake-model") == 0.004  # an unknown model is priced as claude-opus-5


def test_add_usage():
    assert add_usage({"input_tokens": 1}, {"input_tokens": 2, "cache_creation_input_tokens": None, "output_tokens": 3}) == {
        "input_tokens": 3, "output_tokens": 3, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}


def test_run_costs():
    usage = {"input_tokens": 300, "output_tokens": 60, "cache_read_input_tokens": 3000, "cache_creation_input_tokens": 1200}
    manifest = {"stages": {"decode": {"emitted": 4}, "track": {"transitions": 3}, "interpret": {"usage": usage, "model": "claude-opus-5"}}}
    # 300 × 5 + 60 × 25 + 3000 × 0.5 + 1200 × 6.25 = 12,000 millionths of a dollar
    assert run_costs(manifest) == {"stages": {"interpret": {"usage": usage, "cost_usd": 0.012}}, "total_usd": 0.012, "frames": 4,
                                   "per_frame_usd": 0.003}
    assert run_costs({}) == {"stages": {}, "total_usd": 0.0, "frames": None, "per_frame_usd": None}
    off = {"stages": {"annotate": {"skipped": True, "usage": add_usage({}, {}), "model": "claude-opus-5"}}}  # [annotate] mode = "off"
    assert run_costs(off)["stages"] == {"annotate": {"usage": add_usage({}, {}), "cost_usd": 0.0}}
