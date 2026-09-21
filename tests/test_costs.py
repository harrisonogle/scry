from fakes import USAGE

from scry.costs import add_usage, estimate_cost


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
