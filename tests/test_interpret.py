import base64
import io
from pathlib import Path

import pydantic
import pytest
from fakes import USAGE, AnswerProvider
from minirun import call_text, mini_run, write_annotations
from PIL import Image

from scry.config import Config, InterpretConfig
from scry.interpret import build_blocks, prompt_version, run_interpret, validate_citations
from scry.prompts.interpret import SYSTEM
from scry.schemas import ModelInterpretation, OutlineChapter

M = ModelInterpretation(action="a", result="r", description="d", confidence=0.7, entered_text="git st", submitted="no",
                        citations=["11:b3", "11:b9", "11:b3"])


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
    assert prompt_version(InterpretConfig()) == "interpret-v2+scaled0.5"


def test_full_mode_sends_native_size(tmp_path: Path):
    blocks, _, _ = _blocks(mini_run(tmp_path), "T1", InterpretConfig(images="full"))
    assert _images(blocks) == [(400, 200), (400, 200)]
    assert "downscaled" not in _texts(blocks)
    assert prompt_version(InterpretConfig(images="full")) == "interpret-v2+full"


def test_context_and_labels_reach_the_blocks(tmp_path: Path):
    run = mini_run(tmp_path / "plain")
    blocks, _, _ = _blocks(run, "T3", InterpretConfig())
    assert blocks[0]["text"] == ('Preceding transitions:\nT1 [f10→f11, 24.0–24.4s] appended "C:\\src> git status"\n'
                                 'T2 [f11→f12, 26.0–26.4s] appeared 2')
    chapter = OutlineChapter(id="c1", start_s=0, end_s=60, title="Setup", gist="Check the repo")
    assert _blocks(run, "T3", InterpretConfig(), chapter)[0][0]["text"].startswith("Chapter: Setup — Check the repo")
    labelled, _, _ = _blocks(mini_run(tmp_path / "labelled", labels=True), "T3", InterpretConfig())
    assert 'value of "Status"' in _texts(labelled)


def test_screen_descriptions_reach_the_user_turn_and_the_cache_key(tmp_path: Path):
    plain = _blocks(mini_run(tmp_path / "plain"), "T2", InterpretConfig())
    assert "Screen descriptions" not in _texts(plain[0]) and "Screen descriptions" not in plain[2]
    run = mini_run(tmp_path / "labelled", labels=True)
    blocks, _, hashed = _blocks(run, "T2", InterpretConfig())
    described = ("Screen descriptions:\nFrame a: The Overview item is highlighted in the left navigation.\n"
                 "Frame b: The terminal shows new output.")
    texts = [b["text"] for b in blocks if b["type"] == "text"]
    assert texts[3] == described and texts[4].startswith("Changes:\nTransition T2:")  # after the two frames, before Changes
    assert described in hashed
    # incremental annotation: frame 12 has no record of its own, so frame 11's description is in force there, and says so
    lines = [line for line in run.annotations.read_text().splitlines() if '"frame": 12,' not in line]
    run.annotations.write_text("\n".join(lines) + "\n")
    _, _, stale = _blocks(run, "T2", InterpretConfig())
    assert "Frame b (written at frame 11, the latest before it): The Overview item is highlighted" in stale
    assert stale != hashed
    assert "full resolution" in " ".join(SYSTEM.split())


def test_a_changed_description_is_a_new_call_key(tmp_path: Path):
    run, provider = mini_run(tmp_path, labels=True), AnswerProvider(lambda kw: M)
    run_interpret(run, Config(), provider)
    before = {call_text(kw).split("Transition ")[1][:2]: kw["input_hashes"] for kw in provider.calls}
    run.annotations.write_text(run.annotations.read_text().replace("The terminal shows new output.",
                                                                   "The command line shows a greyed suggestion."))
    run_interpret(run, Config(), provider)  # annotations.jsonl is an input of the up-to-date check
    assert len(provider.calls) == 6
    after = {call_text(kw).split("Transition ")[1][:2]: kw["input_hashes"] for kw in provider.calls[3:]}
    assert before["T1"] == after["T1"]  # frames 10 and 11: neither description changed
    assert before["T2"] != after["T2"] and before["T3"] != after["T3"]  # frame 12 is T2's later frame and T3's earlier
    assert "The command line shows a greyed suggestion." in call_text(provider.calls[4])


def _stats(run) -> dict:
    return run.manifest_read()["stages"]["interpret"]


def test_run_interpret_writes_records_and_stats(tmp_path: Path):
    run, provider = mini_run(tmp_path), AnswerProvider(lambda kw: M)
    run_interpret(run, Config(), provider)
    records = run.load_interpretations()
    assert list(records) == ["T1", "T2", "T3"]
    assert (records["T1"].citations, records["T1"].invalid_citations) == (["11:b3"], 1)
    assert (records["T2"].citations, records["T2"].invalid_citations) == ([], 3)
    assert records["T3"].invalid_citations == 3
    for r in records.values():
        assert (r.entered_text, r.submitted, r.usage, r.prompt_version) == ("git st", "no", USAGE, "interpret-v2+scaled0.5")
        assert (r.action, r.result, r.description, r.confidence, r.model, r.error) == ("a", "r", "d", 0.7, "fake-model", None)
    stats = _stats(run)
    expected = {"transitions": 3, "interpreted": 3, "errors": 0, "invalid_citations": 7, "entered": 3,
                "submitted": {"yes": 0, "no": 3, "unclear": 0}, "images": "scaled", "labels": False,
                "usage": {"input_tokens": 300, "output_tokens": 60, "cache_read_input_tokens": 3000, "cache_creation_input_tokens": 1200},
                "cost_usd": 0.012, "model": "fake-model"}
    assert {k: stats[k] for k in expected} == expected
    assert "cost_usd_batch" not in stats
    assert len(provider.calls) == 3
    for kw in provider.calls:
        assert (kw["stage"], kw["effort"], kw["system"]) == ("interpret", "low", SYSTEM)
    t3 = next(kw for kw in provider.calls if "Transition T3:" in call_text(kw))
    assert t3["blocks"][0]["text"].split("\n")[1:] == ['T1 [f10→f11, 24.0–24.4s] appended "C:\\src> git status"',
                                                        "T2 [f11→f12, 26.0–26.4s] appeared 2"]
    t1 = next(kw for kw in provider.calls if "Transition T1:" in call_text(kw))
    assert call_text(t1).startswith("No preceding context.")
    run_interpret(run, Config(), provider)
    assert len(provider.calls) == 3
    run_interpret(run, Config(interpret=InterpretConfig(images="full")), provider)
    assert len(provider.calls) == 6
    assert {kw["prompt_version"] for kw in provider.calls[3:]} == {"interpret-v2+full"}


def test_missing_png_makes_no_call(tmp_path: Path):
    run, provider = mini_run(tmp_path), AnswerProvider(lambda kw: M)
    (run.frames_dir / "00013.png").unlink()
    run_interpret(run, Config(), provider)
    assert len(provider.calls) == 2
    assert run.load_interpretations()["T3"].error == "missing_png"
    assert (_stats(run)["interpreted"], _stats(run)["errors"]) == (2, 1)


def test_refusal_and_blank_entered_text(tmp_path: Path):
    def answer(kw: dict):
        text = call_text(kw)
        if "Transition T2:" in text:
            return "refusal"
        return M.model_copy(update={"entered_text": "  "}) if "Transition T3:" in text else M

    run = mini_run(tmp_path)
    run_interpret(run, Config(), AnswerProvider(answer))
    records = run.load_interpretations()
    assert (records["T2"].error, records["T2"].action, records["T2"].usage) == ("refusal", None, USAGE)
    assert records["T3"].entered_text is None
    stats = _stats(run)
    assert (stats["errors"], stats["interpreted"], stats["entered"]) == (1, 2, 1)


def test_labels_flag_and_rerun(tmp_path: Path):
    run, provider = mini_run(tmp_path), AnswerProvider(lambda kw: M)
    run_interpret(run, Config(), provider)
    assert _stats(run)["labels"] is False
    write_annotations(run)
    run_interpret(run, Config(), provider)  # the inputs hash changed
    assert len(provider.calls) == 6
    assert _stats(run)["labels"] is True
