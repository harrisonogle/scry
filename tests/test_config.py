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


def test_config_hash_is_stable_per_section(tmp_path: Path):
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.decode.detect.theta_comp == 24
    assert config_hash(cfg, "decode") == config_hash(Config(), "decode")
    assert config_hash(cfg, "decode") != config_hash(cfg, "read")
