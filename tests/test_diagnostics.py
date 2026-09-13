from vt.diagnostics import estimate_cost, summarize


def test_summarize_counts_and_cost():
    frames = [{"settled": True, "lines": [{"agree": True, "ocr": "a"}, {"agree": None, "ocr": None}, {"agree": False, "ocr": "b"}]},
              {"settled": False, "lines": [{"agree": True, "ocr": "c"}]}]
    s = summarize(frames)
    assert s["frames"] == 2 and s["settled_fraction"] == 0.5 and s["lines_per_frame"] == 2.0
    assert s["agree_fraction"] == 0.5 and s["vlm_only_fraction"] == 0.25 and s["ocr_only_fraction"] == 0.0
    assert estimate_cost({"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 0}, "claude-opus-5") == 7.5
