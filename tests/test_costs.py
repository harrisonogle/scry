from scry.costs import estimate_cost


def test_estimate_cost():
    assert estimate_cost({"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 0}, "claude-opus-5") == 7.5
