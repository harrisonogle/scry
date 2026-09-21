from dataclasses import replace
from pathlib import Path

import pydantic
import pytest

from scry.config import Config
from scry.evaluation.matrix import config_for, expand, load_matrix

MATRIX = """
phase = "p9"
source = "SRC"
stages = ["track", "read", "annotate", "ask"]
repeats = 2
[spans.smoke]
frames = "1-2"
[spans.span2]
frames = "2-3"
ground_truth = "gt.md"
questions = "q.md"
[axis.base.big]
"model.max_tokens" = 16000
[axis.base.small]
"model.max_tokens" = 8000
[axis.margin.m050]
"track.margin" = 0.5
[axis.margin.m025]
"track.margin" = 0.25
"""


def _matrix(tmp_path: Path, text: str = MATRIX):
    path = tmp_path / "p9.toml"
    path.write_text(text)
    return load_matrix(path)


def test_expand_order_names_and_stages(tmp_path):
    specs = expand(_matrix(tmp_path))
    names = [s.name for s in specs]
    assert len(specs) == 16  # 2 spans × 2 × 2 × 2 repeats
    assert names[:3] == ["smoke-big-m050-r1", "smoke-big-m050-r2", "smoke-big-m025-r1"]
    assert names[-1] == "span2-small-m025-r2"
    by_name = {s.name: s for s in specs}
    s = by_name["smoke-big-m050-r1"]
    assert s.phase == "p9" and s.config_id == "smoke-big-m050" and s.repeat == 1
    assert s.stages == ("read", "track", "annotate")  # pipeline order; no questions on `smoke`
    assert s.overrides == {"model.max_tokens": 16000, "track.margin": 0.5}
    assert s.span.frames == (1, 2) and s.span.ground_truth is None
    assert s.values == {"base": "big", "margin": "m050"}
    s2 = by_name["span2-big-m050-r1"]
    assert s2.stages == ("read", "track", "annotate", "ask")
    assert s2.span.ground_truth == Path("gt.md") and s2.span.questions == Path("q.md")


def test_config_for_applies_overrides_and_rejects_unknown_keys(tmp_path):
    base = tmp_path / "base.toml"
    base.write_text("[track]\nmargin = 0.5\n[index]\nk = 7\n")
    m = _matrix(tmp_path, f'base_config = "{base}"\n' + MATRIX)
    spec = expand(m)[0]
    cfg = config_for(m, replace(spec, overrides={"track.margin": 0.25, "model.max_tokens": 8000}))
    assert cfg.track.margin == 0.25 and cfg.model.max_tokens == 8000
    expected = Config().model_dump()
    expected["track"]["margin"] = 0.25
    expected["model"]["max_tokens"] = 8000
    expected["index"]["k"] = 7
    assert cfg.model_dump() == expected  # every other value is the base's
    with pytest.raises(pydantic.ValidationError):
        config_for(m, replace(spec, overrides={"track.margn": 1}))
    with pytest.raises(ValueError, match="not a table"):
        config_for(m, replace(spec, overrides={"track.margin.x": 1}))


def test_bad_keys_are_refused_at_load(tmp_path):
    with pytest.raises(ValueError, match="perceive"):
        _matrix(tmp_path, MATRIX.replace('stages = ["track", "read", "annotate", "ask"]', 'stages = ["read", "perceive"]'))
    with pytest.raises(ValueError, match="repeat"):
        _matrix(tmp_path, "repeat = 3\n" + MATRIX)
    with pytest.raises(ValueError, match="track.margin"):
        _matrix(tmp_path, MATRIX.replace('"model.max_tokens" = 16000', '"model.max_tokens" = 16000\n"track.margin" = 0.5'))
