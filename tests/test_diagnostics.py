from scry.diagnostics import estimate_cost, summarize


def test_summarize_counts_and_cost():
    frames = [{"settled": True, "lines": [{"agree": True, "ocr": "a"}, {"agree": None, "ocr": None}, {"agree": False, "ocr": "b"}]},
              {"settled": False, "lines": [{"agree": True, "ocr": "c"}]}]
    s = summarize(frames)
    assert s["frames"] == 2 and s["settled_fraction"] == 0.5 and s["lines_per_frame"] == 2.0
    assert s["agree_fraction"] == 0.5 and s["vlm_only_fraction"] == 0.25 and s["ocr_only_fraction"] == 0.0
    assert estimate_cost({"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 0}, "claude-opus-5") == 7.5


def test_mark_match_counts_rows_whose_text_matches_the_named_marks():
    from scry.diagnostics import mark_match
    from scry.schemas import OcrFrame, OcrLine, PerceptionRecord, VlmPerception, VlmRegion
    ocr = [OcrFrame(frame=0, engine="e", settings={}, seconds=0, lines=[OcrLine(id="l1", bbox=(0, 0, 9, 9), text="az login", conf=1),
                                                                       OcrLine(id="l2", bbox=(0, 10, 9, 19), text="Overview", conf=1)])]
    reg = VlmRegion(id="r1", kind="window", name="n", app="a", parent=None, conf=1.0,
                    rows=[["l1"], ["l2"], [], ["l1"]], vlm_lines=["az login", "Storage", "missed line", ""])
    per = [PerceptionRecord(frame=0, model="m", prompt_version="v", output=VlmPerception(regions=[reg], focused_region=None, focused_conf=0, description="", unassigned_line_ids=[]))]
    assert mark_match(ocr, per) == (1, 2)  # row 1 matches, row 2 does not; the empty row and the empty text are skipped
