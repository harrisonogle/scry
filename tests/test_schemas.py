from pathlib import Path

from scry.config import Config, config_hash, load_config
from scry.jsonl import read_jsonl, write_jsonl
from scry.schemas import FrameRecord, Line, Region, Transition


def test_config_defaults_and_hash_are_stable(tmp_path: Path):
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.stage1.detect.theta_comp == 24
    assert config_hash(cfg, "stage1") == config_hash(Config(), "stage1")
    assert config_hash(cfg, "stage1") != config_hash(cfg, "merge")
    assert cfg.model.stage2c_transcribe is True  # group-only Stage 2c is opt-in (§8.3)


def test_frame_record_roundtrip(tmp_path: Path):
    line = Line(id="l3", marks=["l3"], bbox=(12, 40, 300, 58), ocr="git status", ocr_conf=1.0,
                vlm="git status", agree=True, in_churn=False)
    region = Region(id="r1", kind="window", name="Terminal", app="Windows Terminal", parent=None,
                    bbox=(12, 40, 640, 300), conf=0.95, layout_conf=0.9, lines=[line])
    rec = FrameRecord(video_id="v", frame=12, t_change=47.3, t_settled=47.72, t_end=52.1, settled=True,
                      png="frames/00012.png", overlay=None, sha256="x", width=1920, height=1080, regions=[region])
    write_jsonl(tmp_path / "frames.jsonl", [rec])
    back = read_jsonl(tmp_path / "frames.jsonl", FrameRecord)
    assert back == [rec]
    assert back[0].regions[0].lines[0].fused == "git status"
    assert back[0].line_ids() == {"l3"}


def test_line_fused_prefers_stripped_reading():
    line = Line(id="l1", marks=["l1"], bbox=(0, 0, 1, 1), ocr="P Search", ocr_conf=1.0, vlm="Search",
                agree=True, in_churn=False, ocr_glyph_stripped="P")
    assert line.fused == "Search"
    unc = Line(id="l2", marks=["l2"], bbox=(0, 0, 1, 1), ocr="maln", ocr_conf=1.0, vlm="main", agree=False, in_churn=False)
    assert unc.fused == "maln" and unc.uncertain


def test_group_only_perception_converts_to_the_usual_shape():
    from scry.schemas import VlmPerception, VlmPerceptionGroupOnly, VlmRegion, VlmRegionGroupOnly, perception_from_group_only
    r = VlmRegionGroupOnly(id="r1", kind="window", name="Terminal", app="T", parent=None, conf=0.9, occludes=["r2"], rows=[["l1", "l2"], ["l3"], []])
    out = VlmPerceptionGroupOnly(regions=[r], focused_region="r1", focused_conf=0.8, focused_cues=["caret"], description="d", unassigned_line_ids=["l4"])
    conv = perception_from_group_only(out)
    assert isinstance(conv, VlmPerception) and conv.regions[0].vlm_lines == ["", "", ""]  # one empty entry per row, [] included
    assert conv.regions[0].model_dump(exclude={"vlm_lines"}) == r.model_dump()
    assert conv.model_dump(exclude={"regions"}) == out.model_dump(exclude={"regions"})
    assert "vlm_lines" not in VlmRegionGroupOnly.model_json_schema()["properties"]
    assert list(VlmRegion.model_json_schema()["properties"])[-1] == "vlm_lines"
