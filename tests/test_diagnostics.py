from scry.diagnostics import estimate_cost, summarize


def test_summarize_counts_and_cost():
    frames = [{"settled": True, "lines": [{"agree": True, "ocr": "a"}, {"agree": None, "ocr": None}, {"agree": False, "ocr": "b"}]},
              {"settled": False, "lines": [{"agree": True, "ocr": "c"}]}]
    s = summarize(frames)
    assert s["frames"] == 2 and s["settled_fraction"] == 0.5 and s["lines_per_frame"] == 2.0
    assert s["agree_fraction"] == 0.5 and s["vlm_only_fraction"] == 0.25 and s["ocr_only_fraction"] == 0.0
    assert estimate_cost({"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 0}, "claude-opus-5") == 7.5


def test_fragment_stability_compares_unit_lines_of_matched_units():
    from scry.diagnostics import fragment_stability
    from scry.schemas import Correspondence, FrameRecord, Line, Region, Transition

    def fr(n, marks):
        win = Region(id="r1", kind="window", name="w", app="a", parent=None, bbox=(0, 0, 9, 9), conf=1, layout_conf=1, lines=[])
        pane = Region(id="r2", kind="pane", name="p", app="a", parent="r1", bbox=(0, 0, 9, 9), conf=1, layout_conf=1,
                      lines=[Line(id="l1", marks=marks, bbox=(0, 0, 9, 9), ocr="x", ocr_conf=1, vlm="x", agree=True, in_churn=False)])
        return FrameRecord(video_id="v", frame=n, t_change=n, t_settled=n, t_end=n + 1, settled=True, png="", overlay=None, sha256="", width=1, height=1, regions=[win, pane])

    t = Transition(id="T1", from_frame=1, to_frame=2, t=(1, 2), kind="single", regions=Correspondence(matched=[("r1", "r1", 1.0)]))
    assert fragment_stability([fr(1, ["l1"]), fr(2, ["l1", "l2"])], [t]) == 1.0
    assert fragment_stability([fr(1, ["l1"]), fr(2, ["l1"])], [t]) == 0.0


def test_mark_match_counts_rows_whose_text_matches_the_named_marks():
    from scry.diagnostics import mark_match
    from scry.schemas import OcrFrame, OcrLine, PerceptionRecord, VlmPerception, VlmRegion
    ocr = [OcrFrame(frame=0, engine="e", settings={}, seconds=0, lines=[OcrLine(id="l1", bbox=(0, 0, 9, 9), text="az login", conf=1),
                                                                       OcrLine(id="l2", bbox=(0, 10, 9, 19), text="Overview", conf=1)])]
    reg = VlmRegion(id="r1", kind="window", name="n", app="a", parent=None, conf=1.0,
                    rows=[["l1"], ["l2"], [], ["l1"]], vlm_lines=["az login", "Storage", "missed line", ""])
    per = [PerceptionRecord(frame=0, model="m", prompt_version="v", output=VlmPerception(regions=[reg], focused_region=None, focused_conf=0, description="", unassigned_line_ids=[]))]
    assert mark_match(ocr, per) == (1, 2)  # row 1 matches, row 2 does not; the empty row and the empty text are skipped
