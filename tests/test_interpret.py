import base64
import io
from pathlib import Path

import pydantic
import pytest
from minirun import mini_run
from PIL import Image

from scry.config import InterpretConfig
from scry.interpret import build_blocks, prompt_version, validate_citations
from scry.schemas import ModelInterpretation, OutlineChapter


def _images(blocks: list[dict]) -> list[tuple[int, int]]:
    return [Image.open(io.BytesIO(base64.standard_b64decode(b["source"]["data"]))).size for b in blocks if b["type"] == "image"]


def _texts(blocks: list[dict]) -> str:
    return "\n".join(b["text"] for b in blocks if b["type"] == "text")


def _blocks(run, change_id: str, ic: InterpretConfig, chapter: OutlineChapter | None = None):
    changes = run.load_changes()
    i = next(k for k, c in enumerate(changes) if c.id == change_id)
    return build_blocks(changes[i], changes[:i], {f.frame: f for f in run.load_frames()}, {fb.frame: fb for fb in run.load_boxes()},
                        run.load_labels(), run, chapter, ic)


def test_validate_citations():
    cited = ["11:b3", "11:b9", "b3", "T1", "11:b3", "11:b3 ", "10:b3"]
    assert validate_citations(cited, ["11:b3", "10:b3"]) == (["11:b3", "10:b3"], 4)
    assert validate_citations([], ["11:b3"]) == ([], 0)
    assert validate_citations(["11:b3"], []) == ([], 1)


def test_model_interpretation_schema():
    required = ModelInterpretation.model_json_schema()["required"]
    assert set(required) == {"action", "result", "description", "confidence", "entered_text", "submitted"}
    fields = dict(action="a", result="r", description="d", confidence=0.5, entered_text=None, submitted="no")
    assert ModelInterpretation(**fields).entered_text is None
    with pytest.raises(pydantic.ValidationError):
        ModelInterpretation(**(fields | {"submitted": "maybe"}))


def test_scaled_mode_is_the_default(tmp_path: Path):
    blocks, ids, _ = _blocks(mini_run(tmp_path), "T1", InterpretConfig())
    assert _images(blocks) == [(200, 100), (200, 100)]
    texts = _texts(blocks)
    assert "Frame a = frame 10 (t=20.40s), downscaled by 0.5:" in texts
    assert "Frame b = frame 11 (t=24.40s), downscaled by 0.5:" in texts
    assert texts.startswith("No preceding context.")
    assert "Changes:\nTransition T1:" in texts
    assert texts.endswith("Return the JSON object.")
    assert ids == ["11:b3", "10:b3"]
    assert prompt_version(InterpretConfig()) == "interpret-v1+scaled0.5"


def test_full_mode_sends_native_size(tmp_path: Path):
    blocks, _, _ = _blocks(mini_run(tmp_path), "T1", InterpretConfig(images="full"))
    assert _images(blocks) == [(400, 200), (400, 200)]
    assert "downscaled" not in _texts(blocks)
    assert prompt_version(InterpretConfig(images="full")) == "interpret-v1+full"


def test_context_and_labels_reach_the_blocks(tmp_path: Path):
    run = mini_run(tmp_path / "plain")
    blocks, _, _ = _blocks(run, "T3", InterpretConfig())
    assert blocks[0]["text"] == ('Preceding transitions:\nT1 [f10→f11, 24.0–24.4s] appended "C:\\src> git status"\n'
                                 'T2 [f11→f12, 26.0–26.4s] appeared 2')
    chapter = OutlineChapter(id="c1", start_s=0, end_s=60, title="Setup", gist="Check the repo")
    assert _blocks(run, "T3", InterpretConfig(), chapter)[0][0]["text"].startswith("Chapter: Setup — Check the repo")
    labelled, _, _ = _blocks(mini_run(tmp_path / "labelled", labels=True), "T3", InterpretConfig())
    assert 'value of "Status"' in _texts(labelled)
