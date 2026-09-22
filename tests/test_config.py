from pathlib import Path

import pydantic
import pytest

from scry.config import Config, config_hash, load_config

REPO = Path(__file__).resolve().parents[1]


def _toml(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "c.toml"
    p.write_text(body)
    return p


def test_sections_and_unknown_keys(tmp_path: Path):
    assert load_config(_toml(tmp_path, "[decode.settle]\nstill_s = 0.5\n")).decode.settle.still_s == 0.5
    with pytest.raises(pydantic.ValidationError):
        load_config(_toml(tmp_path, "[stage1.settle]\nstill_s = 0.5\n"))
    with pytest.raises(pydantic.ValidationError):
        load_config(_toml(tmp_path, '[read]\nlanguages = ["en"]\n'))


def test_repo_toml_loads():
    cfg = load_config(REPO / "scry.toml")
    assert cfg.read.engine == "rapid"
    assert (cfg.annotate.mode, cfg.annotate.transcribe) == ("incremental", False)  # the owner's default: incremental group-only (ledger L73)
    assert cfg.annotate.reference == "ids"  # the tagged overlay and box ids: today's call, byte for byte
    assert cfg.model.effort_annotate == "low"
    assert cfg.interpret.images == "scaled"
    assert cfg.ask.max_turns == 12 and cfg.ask.frames is True and cfg.ask.model == ""
    assert cfg.model.temperature is None and cfg.model.schema_in_prompt is False  # the API's defaults: no temperature sent, the API shows the descriptions


def test_local_qwen_config_is_the_landed_local_configuration():
    """configs/local-qwen.toml reproduces the runs behind the cost headline (ledger L76, L78) from config alone: the
    local 27B through openai_compat at temperature 0 with the schema in the prompt, one call at a time, the owner's
    default annotate settings, and the answering agent left on the API."""
    cfg = load_config(REPO / "configs" / "local-qwen.toml")
    assert cfg.model.provider == "openai_compat" and cfg.model.base_url == "http://127.0.0.1:8080/v1"
    assert cfg.model.model == "mlx-community/Qwen3.8-27B-4bit"
    assert cfg.model.temperature == 0.0 and cfg.model.schema_in_prompt is True and cfg.model.concurrency == 1
    assert cfg.model.mode == "sync"
    assert (cfg.annotate.mode, cfg.annotate.transcribe, cfg.annotate.reference, cfg.annotate.scale) == ("incremental", False, "ids", 1.0)
    assert cfg.ask.model == "claude-opus-5"  # ask calls the Claude API whatever the provider; empty would send the Qwen name there


def test_stage_sections_defaults():
    cfg = Config()
    assert (cfg.interpret.images, cfg.interpret.scale, cfg.interpret.context_transitions) == ("scaled", 0.5, 3)
    assert cfg.summarize.window == 2000
    assert cfg.index.collapse is True
    assert cfg.ask.max_turns == 12
    assert cfg.ask.frames is True  # the agent may open frames unless a run withholds them
    assert cfg.ask.model == ""  # empty: the answering agent runs on the pipeline's model, [model] model
    assert (cfg.model.effort_interpret, cfg.model.effort_summarize, cfg.model.effort_ask) == ("low", "medium", "high")
    for mode in ("text", "crops"):
        with pytest.raises(pydantic.ValidationError):
            Config.model_validate({"interpret": {"images": mode}})


def test_annotate_reference_key():
    """How the call refers to boxes: "ids" (the numbered overlay, answers by box id) or "coords" (no overlay, the boxes
    listed as rectangles, answers by a point inside the box); nothing else."""
    assert Config().annotate.reference == "ids"
    assert Config.model_validate({"annotate": {"reference": "coords"}}).annotate.reference == "coords"
    for bad in ("boxes", "C", "", "IDS"):
        with pytest.raises(pydantic.ValidationError):
            Config.model_validate({"annotate": {"reference": bad}})


def test_annotate_box_text_key():
    """`box_text` lists each box's OCR reading in the user turn; group-only only: with `transcribe = true` the second
    reading must stay independent of OCR, so the pair is refused."""
    assert Config().annotate.box_text is False
    cfg = Config.model_validate({"annotate": {"transcribe": False, "box_text": True}})
    assert (cfg.annotate.transcribe, cfg.annotate.box_text) == (False, True)
    with pytest.raises(pydantic.ValidationError, match="box_text"):
        Config.model_validate({"annotate": {"transcribe": True, "box_text": True}})
    assert Config.model_validate({"annotate": {"transcribe": True, "box_text": False}}).annotate.box_text is False


def test_ask_frames_is_in_no_pipeline_stage_hash():
    """Withholding the frames from the answering agent leaves every pipeline stage up to date: no stage hashes [ask]."""
    with_frames, without = Config(), Config.model_validate({"ask": {"frames": False}})
    pipeline = [s for s in Config.model_fields if s != "ask"]
    assert config_hash(with_frames, *pipeline) == config_hash(without, *pipeline)
    assert config_hash(with_frames, "ask") != config_hash(without, "ask")


def test_ask_model_is_in_no_pipeline_stage_hash():
    """Answering on another model leaves every pipeline stage up to date, and [model], which the stages hash, as it was."""
    pipelines, sonnet = Config(), Config.model_validate({"ask": {"model": "claude-sonnet-5"}})
    pipeline = [s for s in Config.model_fields if s != "ask"]
    assert config_hash(pipelines, *pipeline) == config_hash(sonnet, *pipeline)
    assert config_hash(pipelines, "ask") != config_hash(sonnet, "ask")
    assert sonnet.model.model == pipelines.model.model == "claude-opus-5"


def test_annotate_defaults():
    cfg = Config()
    assert cfg.annotate.mode == "incremental"  # the owner's default: incremental group-only (ledger L73)
    assert cfg.annotate.transcribe is False
    assert cfg.annotate.scale == 1.0
    assert cfg.model.effort_annotate == "low"


def test_annotate_section_loads_and_rejects_bad_values(tmp_path: Path):
    cfg = load_config(_toml(tmp_path, '[annotate]\nmode = "off"\ntranscribe = false\nscale = 0.5\n'))
    assert cfg.annotate.mode == "off"
    assert cfg.annotate.transcribe is False
    assert cfg.annotate.scale == 0.5
    for bad in ("scale = 0", "scale = 1.5", 'mode = "sometimes"', 'stage2c_rows = "boxes"'):
        with pytest.raises(pydantic.ValidationError):
            load_config(_toml(tmp_path, f"[annotate]\n{bad}\n"))


def test_incremental_mode(tmp_path: Path):
    assert load_config(_toml(tmp_path, '[annotate]\nmode = "incremental"\n')).annotate.mode == "incremental"
    cfg = load_config(_toml(tmp_path, '[annotate]\nmode = "incremental"\n\n[model]\nmode = "batch"\n'))
    assert (cfg.annotate.mode, cfg.model.mode) == ("incremental", "batch")  # calls are independent, so batch mode works


def test_config_hash_is_stable_per_section(tmp_path: Path):
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.decode.detect.theta_comp == 24
    assert config_hash(cfg, "decode") == config_hash(Config(), "decode")
    assert config_hash(cfg, "decode") != config_hash(cfg, "read")


@pytest.mark.parametrize("name, margin", [("000", 0.0), ("025", 0.25), ("100", 1.0)])
def test_p0_margin_configs_differ_only_in_margin(name: str, margin: float):
    cfg = load_config(REPO / "configs" / f"p0-margin-{name}.toml")
    assert cfg.track.margin == margin
    dumped = cfg.model_dump()
    dumped["track"]["margin"] = 0.5
    assert dumped == load_config(REPO / "scry.toml").model_dump()
