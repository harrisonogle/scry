import base64
import io
from pathlib import Path

import numpy as np
from fakes import fake_sync_client, response, text, tool_use
from minirun import mini_interpretations, mini_run
from PIL import Image

from scry.ask import TOOL_DEFS, Tools, ask, extract_citations
from scry.config import AskConfig, Config
from scry.index import build_index
from scry.prompts.ask import SYSTEM


def _indexed(tmp_path: Path, labels: bool = True):
    run = mini_run(tmp_path, labels=labels)
    mini_interpretations(run)
    build_index(run, Config())
    return run


def test_tool_defs():
    required = {"search": ["query"], "get_node": ["node_id"], "get_transitions": ["t_a", "t_b"], "get_frame": ["frame"],
                "redecode": ["t_a", "t_b"]}
    assert {d["name"] for d in TOOL_DEFS} == set(required) and len(TOOL_DEFS) == 5
    for d in TOOL_DEFS:
        assert d["input_schema"]["type"] == "object" and d["input_schema"]["required"] == required[d["name"]]
        assert set(required[d["name"]]) <= set(d["input_schema"]["properties"])


def test_search_and_get_node_tools(tmp_path: Path):
    tools = Tools(_indexed(tmp_path), Config())
    result = tools.search("Creating")
    hits = result["hits"]
    assert [h["node_id"] for h in hits] == ["v:L2", "v:T3", "v:f10"]
    assert all("payload" not in h for h in hits) and "note" not in result
    lifetime, transition, frame = hits
    assert (lifetime["sightings"], lifetime["unstable"], lifetime["seen_once"], lifetime["agree"]) == (3, False, False, True)
    assert lifetime["readers"] == {"ocr": "Creating", "vlm": "Creating"}
    assert (transition["entered_text"], transition["submitted"], transition["confidence"]) == (None, "no", 0.7)
    assert (frame["text"], frame["collapsed"], frame["frames"]) == ("Creating\nStatus Creating", 3, [10, 12])
    assert tools.get_node("v:T2")["payload"]["interpretation"]["submitted"] == "yes"
    assert tools.get_node("v:nope") == {"error": "no such node"}


def test_search_tool_ignores_app_without_labels(tmp_path: Path):
    plain = Tools(_indexed(tmp_path / "plain", labels=False), Config()).search("Creating", app="Portal")
    assert [h["node_id"] for h in plain["hits"]] == ["v:L2", "v:T3", "v:f10"]  # what the same search returns without `app`
    assert plain["note"] == "app filter ignored: this run has no window labels"
    labelled = Tools(_indexed(tmp_path / "labelled"), Config()).search("Creating", app="Portal")
    assert [h["node_id"] for h in labelled["hits"]] == ["v:L2", "v:T3", "v:f10"] and "note" not in labelled


def test_get_transitions_window(tmp_path: Path):
    tools = Tools(_indexed(tmp_path), Config())
    items = tools.get_transitions(24.0, 26.0)["transitions"]
    assert [i["id"] for i in items] == ["T1", "T2"]  # T3 starts at 30.0
    t2 = items[1]
    assert (t2["summary"], t2["entered_text"], t2["submitted"]) == ("T2 [f11→f12, 26.0–26.4s] appeared 2", "git status", "yes")
    assert (t2["node_id"], t2["undoes"]) == ("v:T2", None)
    assert len(tools.get_transitions(0, 100)["transitions"]) == 3


def test_get_frame_returns_image_texts_and_description(tmp_path: Path):
    tools = Tools(_indexed(tmp_path / "labelled"), Config())
    blocks = tools.get_frame(12)
    assert [b["type"] for b in blocks] == ["text", "image"]
    assert Image.open(io.BytesIO(base64.standard_b64decode(blocks[1]["source"]["data"]))).size == (400, 200)
    lines = blocks[0]["text"].split("\n")
    assert lines[:2] == ["Frame 12, t=26.40–30.00s.", "Description in force: The terminal shows new output."]
    assert 'b2 L2 "Creating" | seen 20.4–30.0s in 3 frames | Azure Portal window, Essentials, value of "Status"' in lines
    assert 'b3 L4 "C:\\src> git status" | seen 24.4–35.0s in 3 frames | Windows Terminal window' in lines
    assert 'b4 L5 "On branch main" | seen 26.4–35.0s in 2 frames | other OCR readings: "On branch maln" | Windows Terminal window' in lines
    lines = tools.get_frame(13)[0]["text"].split("\n")
    assert ('b4 L5 "On branch maln" | seen 26.4–35.0s in 2 frames | other OCR readings: "On branch main" | '
            'model reads "On branch main" | Windows Terminal window') in lines
    assert 'm1 (no box) "Refresh"' in lines
    assert tools.get_frame(99) == [{"type": "text", "text": "no such frame"}]
    lines = Tools(_indexed(tmp_path / "plain", labels=False), Config()).get_frame(11)[0]["text"].split("\n")
    assert lines[1] == "Description in force: none."
    assert 'b3 L4 "C:\\src> git status" | seen 24.4–35.0s in 3 frames' in lines


def test_redecode_returns_capped_frames(tmp_path: Path, video_factory):
    run = _indexed(tmp_path / "run")
    video = video_factory([np.full((64, 64), 40 + n, np.uint8) for n in range(60)], fps=30)
    run.manifest_update(video=str(video))
    tools = Tools(run, Config(ask=AskConfig(redecode_max_frames=2)))
    blocks = tools.redecode(0.0, 2.0, fps=2)
    assert [b["type"] for b in blocks] == ["text", "image", "text", "image"]
    assert blocks[0]["text"].startswith("t=0.")
    assert tools.redecode(50.0, 60.0) == [{"type": "text", "text": "no frames in range"}]


ANSWER = "They ran `git status` at 26.0–26.4 s (T2, frame 12; the output is 12:b4)."


def test_ask_loop_runs_tools_and_reports_cost(tmp_path: Path):
    client = fake_sync_client([
        response([tool_use("u1", "search", {"query": '"git status"'})], "tool_use"),
        response([tool_use("u2", "get_frame", {"frame": 12}), tool_use("u3", "get_transitions", {"t_a": 24.0, "t_b": 27.0})], "tool_use"),
        response([text(ANSWER)], "end_turn")])
    result = ask(_indexed(tmp_path), Config(), "Did they run git status?", client)
    assert (result.text, result.citations, result.model, result.prompt) == (ANSWER, ["12", "12:b4"], "claude-opus-5", "ask-v1")
    assert (result.turns, result.tool_calls, result.stop) == (3, ["search", "get_frame", "get_transitions"], "end_turn")
    assert result.usage == {"input_tokens": 3000, "output_tokens": 300, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    assert result.cost_usd == 0.0225
    calls = client.messages.calls
    for kw in calls:
        assert set(kw) == {"model", "max_tokens", "system", "tools", "output_config", "messages"}
        assert (kw["system"], kw["tools"], kw["output_config"]) == (SYSTEM, TOOL_DEFS, {"effort": "high"})
    last = calls[2]["messages"][-1]
    assert last["role"] == "user"
    assert [(b["type"], b["tool_use_id"]) for b in last["content"]] == [("tool_result", "u2"), ("tool_result", "u3")]
    assert last["content"][0]["content"][1]["type"] == "image"


def test_ask_tool_errors_and_stops(tmp_path: Path):
    run = _indexed(tmp_path)
    client = fake_sync_client([response([tool_use("u1", "nope", {}), tool_use("u2", "get_transitions", {"t_a": 1})], "tool_use"),
                               response([text("done")], "end_turn")])
    result = ask(run, Config(), "q", client)
    errors = client.messages.calls[1]["messages"][-1]["content"]
    assert [e["is_error"] for e in errors] == [True, True]
    assert errors[0]["content"] == "error: unknown tool nope" and errors[1]["content"].startswith("error:")
    assert (result.text, result.stop) == ("done", "end_turn")

    refused = ask(run, Config(), "q", fake_sync_client([response([], "refusal")]))
    assert (refused.text, refused.citations, refused.stop) == ("No answer: the model stopped with refusal.", [], "refusal")

    always = [response([tool_use(f"u{k}", "get_transitions", {"t_a": 0, "t_b": 1})], "tool_use") for k in range(5)]
    stopped = ask(run, Config(ask=AskConfig(max_turns=2)), "q", fake_sync_client(always))
    assert (stopped.text, stopped.stop, stopped.turns) == ("Stopped after 2 turns without a final answer.", "max_turns", 2)
    assert stopped.usage["input_tokens"] == 2000

    failed = ask(run, Config(), "q", fake_sync_client([response([tool_use("u1", "search", {"query": "git"})], "tool_use"),
                                                       RuntimeError("boom")]))
    assert (failed.text, failed.stop, failed.turns) == ("No answer: the API call failed (RuntimeError: boom).", "api_error", 1)
    assert failed.usage["input_tokens"] == 1000 and failed.tool_calls == ["search"]


def test_extract_citations():
    assert extract_citations("See frame 12 and 12:b4, then Frame 13; frames 12 again (13:m1).") == ["12", "12:b4", "13", "13:m1"]
    assert extract_citations("nothing here") == []
    assert extract_citations("frame 99") == ["99"]  # nothing is validated
