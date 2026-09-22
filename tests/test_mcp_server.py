"""The MCP server (`scry-mcp`) over the mini run, driven through the MCP SDK's in-memory client: the tools the host
sees, what each returns, and that an unknown video is a tool error naming the videos there are."""
import base64
import io
import json
from pathlib import Path

import pytest
from minirun import mini_interpretations, mini_run
from PIL import Image

from scry.config import Config
from scry.index import build_index
from scry.mcp import server as S


@pytest.fixture
def runs(tmp_path: Path) -> Path:
    """A runs directory with one indexed video, `demo/mini`, and one directory without an index."""
    run = mini_run(tmp_path / "demo" / "mini", labels=True)
    mini_interpretations(run)
    build_index(run, Config())
    (tmp_path / "unindexed").mkdir()
    S.configure(tmp_path, [tmp_path])
    return tmp_path


async def _call(name: str, **args):
    from mcp import Client

    async with Client(S.server) as client:
        return await client.call_tool(name, args)


def _json(result) -> dict:
    assert not result.is_error, result.content[0].text
    return json.loads(result.content[0].text)


def test_tools_are_listed_with_schemas(runs: Path):
    import asyncio

    from mcp import Client

    async def go():
        async with Client(S.server) as client:
            return (await client.list_tools()).tools

    tools = {t.name: t for t in asyncio.run(go())}
    assert set(tools) == {"list_videos", "search", "get_node", "get_transitions", "get_frame", "summary", "ask", "index_video"}
    assert tools["search"].input_schema["required"] == ["video", "query"]
    assert "double quotes" in tools["search"].description
    assert "Costs money" in tools["ask"].description


def test_list_videos(runs: Path):
    import asyncio

    out = _json(asyncio.run(_call("list_videos")))
    assert [v["video"] for v in out["videos"]] == ["demo/mini"]
    v = out["videos"][0]
    assert v["video_id"] == "v" and v["frames"] == 4 and v["annotated"] is True and v["stages"] == ["index"]


def test_search_and_get_node(runs: Path):
    import asyncio

    out = _json(asyncio.run(_call("search", video="demo/mini", query='"git status"', limit=5)))
    assert out["hits"] and len(out["hits"]) <= 5
    hit = next(h for h in out["hits"] if h["level"] == "lifetime")
    assert "git status" in hit["text"] and "readers" in hit
    node = _json(asyncio.run(_call("get_node", video="demo/mini", node_id=hit["node_id"])))
    assert node["level"] == "lifetime" and node["payload"]["lifetime"]["id"] == hit["item_id"]
    bad = asyncio.run(_call("get_node", video="demo/mini", node_id="v:L999"))
    assert bad.is_error and "no such node" in bad.content[0].text


def test_get_transitions(runs: Path):
    import asyncio

    out = _json(asyncio.run(_call("get_transitions", video="demo/mini", t_a=25.0, t_b=27.0)))
    assert [t["id"] for t in out["transitions"]] == ["T2"]
    assert out["transitions"][0]["entered_text"] == "git status" and out["transitions"][0]["submitted"] == "yes"


def test_get_frame_with_and_without_image(runs: Path):
    import asyncio

    with_image = asyncio.run(_call("get_frame", video="demo/mini", frame=12))
    assert not with_image.is_error
    assert [b.type for b in with_image.content] == ["text", "image"]
    assert with_image.content[0].text.startswith("Frame 12, t=26.40–30.00s.")
    assert "Image: 400x200, full resolution." in with_image.content[0].text  # narrower than the cap: not scaled
    assert with_image.content[1].mime_type == "image/png"
    assert Image.open(io.BytesIO(base64.b64decode(with_image.content[1].data))).size == (400, 200)
    without = asyncio.run(_call("get_frame", video="demo/mini", frame=12, image=False))
    assert [b.type for b in without.content] == ["text"]
    assert 'b3 L4 "C:\\src> git status"' in without.content[0].text and "Image:" not in without.content[0].text
    missing = asyncio.run(_call("get_frame", video="demo/mini", frame=99))
    assert missing.is_error and "no such frame 99" in missing.content[0].text


def test_scaled_png_caps_the_width(tmp_path: Path):
    png = tmp_path / "wide.png"
    Image.new("RGB", (2560, 1440), "white").save(png)
    data, note = S._scaled_png(png)
    assert Image.open(io.BytesIO(data)).size == (1280, 720)
    assert note.startswith("Image: 1280x720, scaled by 0.500 from 2560x1440")


def test_summary(runs: Path):
    import asyncio

    from scry.jsonl import write_jsonl
    from scry.schemas import HierNode

    run_dir = runs / "demo" / "mini"
    write_jsonl(run_dir / "steps.jsonl", [HierNode(id="S1", level="step", children=("T1", "T3"), frames=(10, 13), t=(20.0, 35.0),
                                                   label="git status in the terminal", description="d")])
    write_jsonl(run_dir / "sections.jsonl", [HierNode(id="C1", level="section", children=("S1", "S1"), frames=(10, 13), t=(20.0, 35.0),
                                                      label="Terminal", description="d")])
    (run_dir / "video.json").write_text(HierNode(id="V", level="video", children=("C1", "C1"), frames=(10, 13), t=(20.0, 35.0),
                                                 label="A mini run", description="Four frames.").model_dump_json())
    out = _json(asyncio.run(_call("summary", video="demo/mini")))
    assert out["summary"]["label"] == "A mini run"
    assert [s["id"] for s in out["sections"]] == ["C1"] and out["steps"][0]["t"] == [20.0, 35.0]


def test_unknown_video_is_a_tool_error_naming_the_videos(runs: Path):
    import asyncio

    for name, args in [("search", {"query": "x"}), ("get_frame", {"frame": 1}), ("summary", {}), ("get_transitions", {"t_a": 0, "t_b": 1})]:
        result = asyncio.run(_call(name, video="unindexed", **args))
        assert result.is_error
        assert "unknown video 'unindexed'" in result.content[0].text and "demo/mini" in result.content[0].text
    outside = asyncio.run(_call("search", video="../../etc", query="x"))
    assert outside.is_error and "unknown video" in outside.content[0].text


def test_index_video_refuses_paths_outside_the_roots(runs: Path, tmp_path: Path):
    import asyncio

    S.configure(runs, [runs / "allowed"])
    (runs / "allowed").mkdir()
    out = asyncio.run(_call("index_video", path=str(runs / "demo" / "mini" / "manifest.json")))
    assert out.is_error and "outside the allowed video roots" in out.content[0].text
    bad_mode = asyncio.run(_call("index_video", path=str(runs / "allowed" / "missing.mp4"), annotate="always"))
    assert bad_mode.is_error and "is not a file" in bad_mode.content[0].text


def test_toml_round_trips_the_config(tmp_path: Path):
    import tomllib

    cfg = Config()
    cfg.annotate.mode = "off"
    text = S._toml(cfg.model_dump())
    assert Config.model_validate(tomllib.loads(text)) == cfg
