from scry.perceive import repair
from scry.schemas import VlmPerception, VlmRegion


def region(rid, rows, lines, parent=None):
    return VlmRegion(id=rid, kind="window", name=rid, app="x", parent=parent, conf=0.9, rows=rows, vlm_lines=lines)


def test_repair_missing_duplicate_unknown_and_lengths():
    out = VlmPerception(
        regions=[region("r1", [["l1"], ["l2", "l9"]], ["a", "b"]), region("r2", [["l2"], ["l3"]], ["c"], parent="zz")],
        focused_region="r7", focused_conf=0.5, description="", unassigned_line_ids=[])
    fixed, n = repair(out, ["l1", "l2", "l3", "l4"])
    r1, r2 = fixed.regions
    assert r1.rows == [["l1"], ["l2"]] and r1.vlm_lines == ["a", "b"]   # unknown l9 dropped
    assert r2.rows == [] and r2.vlm_lines == []                          # duplicate l2 emptied its row; l3's row lost its text
    assert fixed.unassigned_line_ids == ["l3", "l4"]                     # l3 released by the length repair; l4 was missing
    assert fixed.focused_region is None and r2.parent is None
    assert n == 7


def test_repair_breaks_parent_cycles():
    out = VlmPerception(regions=[region("r1", [["l1"]], ["a"], parent="r2"), region("r2", [["l2"]], ["b"], parent="r1"),
                                 region("r3", [["l3"]], ["c"], parent="r3")],
                        focused_region=None, focused_conf=0.0, description="", unassigned_line_ids=[])
    fixed, n = repair(out, ["l1", "l2", "l3"])
    parents = [r.parent for r in fixed.regions]
    assert parents.count(None) >= 2 and n >= 2


def test_build_blocks_lists_mark_boxes_only_when_asked(tmp_path):
    from PIL import Image

    from scry.perceive import build_blocks, prompt_version
    from scry.schemas import OcrFrame, OcrLine, Stage1Record
    png = tmp_path / "f.png"
    Image.new("RGB", (8, 8)).save(png)
    rec = Stage1Record(video_id="v", frame=3, t_change=0, t_settled=1.0, t_end=2, settled=True, width=8, height=8, sha256="x", png="f.png")
    ocr = OcrFrame(frame=3, engine="e", settings={}, seconds=0, lines=[OcrLine(id="l1", bbox=(1, 2, 3, 4), text="a", conf=1.0),
                                                                     OcrLine(id="l2", bbox=(5, 6, 7, 8), text="b", conf=1.0)])
    plain = [b["text"] for b in build_blocks(rec, ocr, png, png) if b["type"] == "text"]
    coords = [b["text"] for b in build_blocks(rec, ocr, png, png, coords=True) if b["type"] == "text"]
    assert any(t == "Marks present: l1, l2." for t in plain)
    assert any("l1: 1,2,3,4; l2: 5,6,7,8" in t for t in coords)
    assert prompt_version(False) != prompt_version(True)  # distinct cache keys for the two prompts


def test_repair_keeps_every_row_of_group_only_output():
    from scry.schemas import VlmPerceptionGroupOnly, VlmRegionGroupOnly, perception_from_group_only
    out = perception_from_group_only(VlmPerceptionGroupOnly(
        regions=[VlmRegionGroupOnly(id="r1", kind="window", name="r1", app="x", parent=None, conf=0.9, rows=[["l1", "l2"], ["l3"], ["l9"]])],
        focused_region=None, focused_conf=0.0, description=""))
    fixed, n = repair(out, ["l1", "l2", "l3", "l4"])
    assert fixed.regions[0].rows == [["l1", "l2"], ["l3"]] and fixed.regions[0].vlm_lines == ["", ""]  # no length repair, nothing truncated
    assert fixed.unassigned_line_ids == ["l4"] and n == 2                                            # l9 unknown, l4 missing


def test_group_only_mode_has_its_own_prompt_and_version():
    from scry.perceive import prompt_version, system_prompt
    from scry.prompts import stage2c
    assert system_prompt(True) is stage2c.SYSTEM and system_prompt(False) is stage2c.SYSTEM_GROUP_ONLY
    assert "vlm_lines" in stage2c.SYSTEM and "vlm_lines" not in stage2c.SYSTEM_GROUP_ONLY
    assert "Do not transcribe any text" in stage2c.SYSTEM_GROUP_ONLY and "description:" in stage2c.SYSTEM_GROUP_ONLY
    a, b = stage2c.SYSTEM.split("\n\n"), stage2c.SYSTEM_GROUP_ONLY.split("\n\n")
    changed = {0, 1, 4, 5}  # opening lines, rows, vlm_lines; every other paragraph is shared verbatim
    assert len(a) == len(b) and [p for i, p in enumerate(a) if i not in changed] == [p for i, p in enumerate(b) if i not in changed]
    assert prompt_version(False, transcribe=False) != prompt_version(False)
    assert prompt_version(True, transcribe=False) == prompt_version(True) + "+grouponly"


def test_perceive_group_only_mode_sends_the_grouping_prompt_and_schema(tmp_path):
    import asyncio

    from PIL import Image

    from scry.config import Config, ModelConfig
    from scry.jsonl import write_jsonl
    from scry.perceive import _perceive_all, prompt_version
    from scry.prompts import stage2c
    from scry.providers.base import VlmResult
    from scry.run import Run
    from scry.schemas import OcrFrame, OcrLine, Stage1Record, VlmPerceptionGroupOnly, VlmRegionGroupOnly

    run = Run(tmp_path)
    Image.new("RGB", (8, 8)).save(run.frames_dir / "00003.png")
    Image.new("RGB", (8, 8)).save(run.overlays_dir / "00003.png")
    write_jsonl(run.stage1, [Stage1Record(video_id="v", frame=3, t_change=0, t_settled=1.0, t_end=2, settled=True, width=8, height=8, sha256="x", png="frames/00003.png")])
    write_jsonl(run.ocr, [OcrFrame(frame=3, engine="e", lines=[OcrLine(id="l1", bbox=(1, 2, 3, 4), text="a", conf=1.0),
                                                            OcrLine(id="l2", bbox=(4, 2, 6, 4), text="b", conf=1.0)])])

    class Fake:
        model = "fake"
        calls: list[dict] = []

        async def complete(self, **kw):
            self.calls.append(kw)
            parsed = kw["output_model"](regions=[VlmRegionGroupOnly(id="r1", kind="window", name="w", app="x", parent=None, conf=0.9, rows=[["l1", "l2"]])],
                                        focused_region="r1", focused_conf=0.5, description="")
            return VlmResult(parsed, None, {"input_tokens": 1})

    cfg = Config(model=ModelConfig(stage2c_transcribe=False))
    [rec] = asyncio.run(_perceive_all(run, cfg, Fake()))
    [call] = Fake.calls
    assert call["system"] == stage2c.SYSTEM_GROUP_ONLY and call["output_model"] is VlmPerceptionGroupOnly
    assert call["prompt_version"] == rec.prompt_version == prompt_version(False, transcribe=False)
    assert rec.output.regions[0].rows == [["l1", "l2"]] and rec.output.regions[0].vlm_lines == [""] and rec.repairs == 0


def test_build_blocks_scale_downscales_the_clean_frame_in_memory(tmp_path):
    import base64
    import io

    from PIL import Image

    from scry.perceive import build_blocks, prompt_version
    from scry.schemas import OcrFrame, OcrLine, Stage1Record
    png, ov = tmp_path / "f.png", tmp_path / "o.png"
    Image.new("RGB", (16, 8), (7, 7, 7)).save(png)
    Image.new("RGB", (8, 4)).save(ov)  # the overlay stage already wrote it at the scaled size
    rec = Stage1Record(video_id="v", frame=3, t_change=0, t_settled=1.0, t_end=2, settled=True, width=16, height=8, sha256="x", png="f.png")
    ocr = OcrFrame(frame=3, engine="e", settings={}, seconds=0, lines=[OcrLine(id="l1", bbox=(1, 2, 3, 4), text="a", conf=1.0)])
    blocks = build_blocks(rec, ocr, png, ov, coords=True, scale=0.5)
    frame, overlay = [Image.open(io.BytesIO(base64.b64decode(b["source"]["data"]))) for b in blocks if b["type"] == "image"]
    assert frame.size == (8, 4) and overlay.size == (8, 4)
    assert frame.convert("RGB").getpixel((0, 0)) == (7, 7, 7)
    assert sorted(q.name for q in tmp_path.iterdir()) == ["f.png", "o.png"] and Image.open(png).size == (16, 8)  # nothing written
    [marks] = [b["text"] for b in blocks if b["type"] == "text" and b["text"].startswith("Marks present")]
    assert "l1: 1,2,3,4" in marks and "original 16x8 frame; the images are scaled by 0.5" in marks  # boxes stay in frame pixels
    [plain] = [b["text"] for b in build_blocks(rec, ocr, png, png, coords=True) if b["type"] == "text" and b["text"].startswith("Marks present")]
    assert "scaled" not in plain and "pixels in Image 1" in plain
    # the scale is part of the cache key only when it is not 1.0
    assert prompt_version(False, scale=1.0) == prompt_version(False)
    assert prompt_version(False, scale=0.5) == prompt_version(False) + "+s0.5"
    assert prompt_version(True, transcribe=False, scale=0.5) == prompt_version(True) + "+grouponly+s0.5"


def test_perceive_threads_the_overlay_scale_into_the_call(tmp_path):
    import asyncio
    import base64
    import io

    from PIL import Image

    from scry.config import Config, ModelConfig, OverlayConfig
    from scry.jsonl import write_jsonl
    from scry.perceive import _perceive_all, prompt_version
    from scry.providers.base import VlmResult
    from scry.run import Run
    from scry.schemas import OcrFrame, OcrLine, Stage1Record

    run = Run(tmp_path)
    Image.new("RGB", (16, 8)).save(run.frames_dir / "00003.png")
    Image.new("RGB", (8, 4)).save(run.overlays_dir / "00003.png")
    write_jsonl(run.stage1, [Stage1Record(video_id="v", frame=3, t_change=0, t_settled=1.0, t_end=2, settled=True, width=16, height=8, sha256="x", png="frames/00003.png")])
    write_jsonl(run.ocr, [OcrFrame(frame=3, engine="e", lines=[OcrLine(id="l1", bbox=(1, 2, 3, 4), text="a", conf=1.0)])])

    class Fake:
        model = "fake"
        calls: list[dict] = []

        async def complete(self, **kw):
            self.calls.append(kw)
            return VlmResult(None, "skipped", {})

    cfg = Config(overlay=OverlayConfig(scale=0.5), model=ModelConfig(stage2c_transcribe=False))
    [rec] = asyncio.run(_perceive_all(run, cfg, Fake()))
    [call] = Fake.calls
    assert call["prompt_version"] == rec.prompt_version == prompt_version(False, transcribe=False, scale=0.5)
    sizes = [Image.open(io.BytesIO(base64.b64decode(b["source"]["data"]))).size for b in call["blocks"] if b["type"] == "image"]
    assert sizes == [(8, 4), (8, 4)]
