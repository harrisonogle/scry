import json
import sys
import types
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scry import outline
from scry.cli import app
from scry.config import Config, OutlineConfig
from scry.outline import OutlineError, build_request, list_price_cost, parse_outline_text, run_outline, usage_by_kind
from scry.run import Run

REPLY = '[{"start_s": 312, "end_s": 600, "title": "Create the cluster", "gist": "g2"}, {"start_s": 0, "end_s": 312, "title": "Resource group", "gist": "g1"}]'
ON = Config(outline=OutlineConfig(enabled=True))


def test_parse_outline_text_handles_fences_and_bad_entries():
    text = '```json\n[{"start_s": 312, "end_s": 600, "title": "Create the cluster", "gist": "…"}, {"start_s": 0, "end_s": 312, "title": "Resource group", "gist": "g"}, {"bad": 1}]\n```'
    ch = parse_outline_text(text)
    assert [c.id for c in ch] == ["c1", "c2"] and ch[0].title == "Resource group" and ch[1].start_s == 312.0


def test_parse_outline_text_is_lenient():
    wrapped = '{"chapters": [{"start_s": "5", "end_s": 9.5, "title": "A"}, "text", {"start_s": 9, "end_s": 9, "title": "ends where it starts"}, {"start_s": "0:05", "end_s": 7, "title": "a time that is no number"}]}'
    ch = parse_outline_text(wrapped)
    assert [(c.id, c.start_s, c.end_s, c.title, c.gist) for c in ch] == [("c1", 5.0, 9.5, "A", "")]
    assert parse_outline_text("no list here") == [] and parse_outline_text("[not json]") == []


def test_build_request_is_an_agentic_video_block_a_prompt_and_a_json_schema():
    req = build_request("https://files/abc", "video/mp4", "gemini-3.8-flash")
    assert req["model"] == "gemini-3.8-flash"
    assert req["input"] == [{"type": "video", "uri": "https://files/abc", "mime_type": "video/mp4", "processing": "agentic"},
                            {"type": "text", "text": outline.PROMPT}]
    fmt = req["response_format"]
    assert fmt["type"] == "text" and fmt["mime_type"] == "application/json" and fmt["schema"]["items"]["required"] == ["start_s", "end_s", "title", "gist"]
    assert "generation_config" not in req  # no output-token limit: thinking counts against one


def test_usage_by_kind_and_list_price_cost():
    usage = {"input_tokens_by_modality": [{"modality": "text", "tokens": 641}], "total_input_tokens": 641, "total_output_tokens": 1419,
             "tool_use_tokens_by_modality": [{"modality": "text", "tokens": 4361}, {"modality": "image", "tokens": 38148}, {"modality": "video", "tokens": 38148}],
             "total_thought_tokens": 2728, "total_tokens": 85445, "total_tool_use_tokens": 80657}  # the first live run, 2026-09-21
    tokens = usage_by_kind(usage)
    assert tokens == {"prompt": 641, "prompt_text": 641, "tool_use": 80657, "tool_use_text": 4361, "tool_use_image": 38148, "tool_use_video": 38148,
                      "thinking": 2728, "output": 1419, "total": 85445}
    assert list_price_cost(tokens, "gemini-3.8-flash") == 0.0765  # (641 + 80657) × $0.75 + (2728 + 1419) × $3.75, per million
    assert list_price_cost(tokens, "some-other-model") is None
    assert usage_by_kind({}) == {"prompt": 0, "tool_use": 0, "thinking": 0, "output": 0, "total": 0}


def test_disabled_does_nothing_and_import_works_while_disabled(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(outline, "_gemini_outline", lambda *a: pytest.fail("no call when disabled or importing"))
    run = Run(tmp_path / "run")
    run_outline(run, Config(), Path("v.mp4"))
    assert not run.outline.exists() and "outline" not in run.manifest_read()
    src = tmp_path / "chapters.json"
    src.write_text(REPLY)
    run_outline(run, Config(), Path("v.mp4"), import_path=src)
    assert [c.title for c in run.load_outline()] == ["Resource group", "Create the cluster"] and run.chapter_of(400.0).id == "c2"
    assert run.manifest_read()["outline"] == {"chapters": 2, "source": str(src)}
    src.write_text("[]")
    with pytest.raises(OutlineError, match="no chapter"):
        run_outline(run, Config(), Path("v.mp4"), import_path=src)


def test_enabled_writes_the_outline_and_the_call_record_once(tmp_path: Path, monkeypatch):
    calls = []
    monkeypatch.setattr(outline, "_gemini_outline", lambda video, model: (calls.append((video, model)), (REPLY, {"model": model, "call_path": "fake", "tokens": {"total": 7}}))[1])
    run = Run(tmp_path / "run")
    run_outline(run, ON, Path("v.mp4"))
    run_outline(run, ON, Path("v.mp4"))  # outline.json exists: no second call
    assert calls == [(Path("v.mp4"), "gemini-3.8-flash")] and len(run.load_outline()) == 2
    assert run.manifest_read()["outline"] == {"chapters": 2, "source": "gemini-3.8-flash", "model": "gemini-3.8-flash", "call_path": "fake", "tokens": {"total": 7}}


def test_a_reply_without_chapters_fails_and_writes_nothing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(outline, "_gemini_outline", lambda video, model: ("I cannot watch videos.", {}))
    run = Run(tmp_path / "run")
    with pytest.raises(OutlineError, match="I cannot watch"):
        run_outline(run, ON, Path("v.mp4"))
    assert not run.outline.exists()


def test_client_needs_the_extra_and_the_gemini_key_and_passes_that_key(monkeypatch):
    monkeypatch.setitem(sys.modules, "google", None)  # as if the extra were not installed
    with pytest.raises(OutlineError, match="uv sync --extra outline"):
        outline._client()
    fake = types.ModuleType("google")
    fake.genai = types.SimpleNamespace(Client=lambda api_key: ("client", api_key))
    monkeypatch.setitem(sys.modules, "google", fake)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "another-key")  # the SDK would take this one by itself; the stage never does
    with pytest.raises(OutlineError, match="GEMINI_API_KEY"):
        outline._client()
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    assert outline._client() == ("client", "gemini-key")


def test_cli_disabled_without_import_and_a_stage_error_exit_1_with_a_message(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # no scry.toml here: defaults, so the stage is disabled
    runner = CliRunner()
    res = runner.invoke(app, ["outline", "v.mp4", "--out", str(tmp_path / "run")])
    assert res.exit_code == 1 and "outline disabled" in res.output
    (tmp_path / "chapters.json").write_text(REPLY)
    assert runner.invoke(app, ["outline", "v.mp4", "--out", str(tmp_path / "run"), "--import", str(tmp_path / "chapters.json")]).exit_code == 0
    assert len(json.loads((tmp_path / "run" / "outline.json").read_text())) == 2
    (tmp_path / "on.toml").write_text("[outline]\nenabled = true\n")
    monkeypatch.setattr(outline, "_client", lambda: (_ for _ in ()).throw(OutlineError("the outline stage needs GEMINI_API_KEY")))
    res = runner.invoke(app, ["outline", "v.mp4", "--out", str(tmp_path / "run2"), "--config", str(tmp_path / "on.toml")])
    assert res.exit_code == 1 and "outline: the outline stage needs GEMINI_API_KEY" in res.output
