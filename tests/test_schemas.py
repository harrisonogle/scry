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


def test_transition_without_pixels_still_loads():
    old = ('{"id": "T1", "from_frame": 1, "to_frame": 2, "t": [1.0, 2.0], "kind": "single", '
           '"computed_diff": {"r1": {"from_region": "r1", "ops": [{"op": "insert", "new": "x", "new_index": 0}]}}}')
    t = Transition.model_validate_json(old)
    assert t.pixels is None and t.computed_diff["r1"].ops[0].under_change is None


def test_stage2c_structural_variants_validate_and_convert(tmp_path: Path):
    import pytest
    from pydantic import ValidationError

    from scry.schemas import (PerceptionRecord, VlmPerception, VlmPerceptionBoxes, VlmPerceptionGroupOnly, VlmPerceptionNoPanes,
                              VlmPerceptionNoPanesBoxes, VlmRegion, VlmRegionBoxes, VlmRegionNoPanes, VlmRegionNoPanesBoxes,
                              perception_from_variant, perception_model)
    base = dict(id="r1", name="w", app="x", parent=None, conf=0.9)
    with pytest.raises(ValidationError):
        VlmRegionNoPanes(**base, kind="pane")
    with pytest.raises(ValidationError):
        VlmRegionNoPanesBoxes(**base, kind="pane")
    popup = VlmRegionNoPanes(**base, kind="popup", rows=[["l1"]], vlm_lines=["a"])
    boxes = VlmRegionBoxes(**base, kind="pane", rows=[["l1"], ["l2"]], vlm_lines=["a", "b"], associations=[["l1", "l2"]])
    assert VlmRegionNoPanesBoxes(**base, kind="window", rows=[["l1"]], vlm_lines=["a"]).associations == []
    # only the variants carry the narrowed kind or associations; VlmRegion's schema (and so its cache keys) is unchanged
    props = lambda m: list(m.model_json_schema()["properties"])  # noqa: E731
    assert "associations" not in props(VlmRegion) and "associations" not in props(VlmRegionNoPanes)
    assert props(VlmRegionBoxes) == props(VlmRegionNoPanesBoxes) == props(VlmRegion) + ["associations"]
    assert VlmRegionNoPanes.model_json_schema()["properties"]["kind"]["enum"] == ["window", "popup"]
    assert VlmRegionNoPanesBoxes.model_json_schema()["properties"]["kind"]["enum"] == ["window", "popup"]
    assert "one row per mark" in VlmRegionBoxes.model_json_schema()["properties"]["rows"]["description"].lower()
    assert perception_model() is VlmPerception and perception_model(transcribe=False) is VlmPerceptionGroupOnly
    assert perception_model(panes=False) is VlmPerceptionNoPanes and perception_model(rows="boxes") is VlmPerceptionBoxes
    assert perception_model(panes=False, rows="boxes") is VlmPerceptionNoPanesBoxes
    # conversion to the stored shape, with the associations keyed by region
    out = VlmPerceptionBoxes(regions=[boxes], focused_region="r1", focused_conf=0.8, description="d")
    conv, assoc = perception_from_variant(out)
    assert type(conv) is VlmPerception and type(conv.regions[0]) is VlmRegion and assoc == {"r1": [["l1", "l2"]]}
    assert conv.regions[0].rows == [["l1"], ["l2"]] and conv.regions[0].vlm_lines == ["a", "b"] and conv.description == "d"
    conv, assoc = perception_from_variant(VlmPerceptionNoPanes(regions=[popup], focused_region=None, focused_conf=0.0, description=""))
    assert type(conv) is VlmPerception and conv.regions[0].kind == "popup" and assoc == {}
    conv, assoc = perception_from_variant(VlmPerceptionGroupOnly(regions=[], focused_region=None, focused_conf=0.0, description=""))
    assert type(conv) is VlmPerception and assoc == {}
    # the record round-trips the associations beside the usual output
    rec = PerceptionRecord(frame=1, model="m", prompt_version="s2c-v1+boxes", output=conv, associations={"r1": [["l1", "l2"]]})
    write_jsonl(tmp_path / "p.jsonl", [rec])
    assert read_jsonl(tmp_path / "p.jsonl", PerceptionRecord) == [rec] and PerceptionRecord(frame=1, model="m", prompt_version="v", output=None).associations == {}
    region = Region(id="r1", kind="window", name="w", app="x", parent=None, bbox=None, conf=0.9, layout_conf=0.9, associations=[["l1", "l2"]])
    assert Region.model_validate_json(region.model_dump_json()).associations == [["l1", "l2"]] and Region.model_validate_json('{"id":"r","kind":"window","name":"n","app":"a","parent":null,"bbox":null,"conf":1,"layout_conf":1}').associations == []


def test_structural_variants_need_a_transcribing_stage2c():
    import pytest

    from scry.config import ModelConfig
    assert ModelConfig().stage2c_panes is True and ModelConfig().stage2c_rows == "lines"
    ModelConfig(stage2c_panes=False, stage2c_rows="boxes")
    for flags in ({"stage2c_panes": False}, {"stage2c_rows": "boxes"}):
        with pytest.raises(ValueError):
            ModelConfig(stage2c_transcribe=False, **flags)
