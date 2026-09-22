"""`scry-mcp`: an MCP server (stdio) over scry's indexes, so any MCP host (Claude Code, GitHub Copilot CLI, ...) can
analyse a screen-recording video and answer questions about it. The read tools are the answering agent's own
(`scry.ask.Tools`), one video argument added and the index chosen by it; `ask` runs the built-in agent; `index_video`
runs the pipeline (`scry run`) in a subprocess. Nothing here writes into a run except `index_video` and, through
`ask`, the frames `redecode` saves. A video id is a run directory's path relative to `--runs` (`demo/aks-tutorial`).

Run: `uv run scry-mcp --runs runs --videos .`. The `.env` of the working directory is read the way the CLI reads it
(`scry.env.load_dotenv`); nothing of it is ever printed. Logging goes to stderr: stdout is the MCP transport."""
from __future__ import annotations

import argparse
import asyncio
import io
import json
import logging
import sys
from pathlib import Path


from mcp.server.mcpserver import Context, Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ImageContent, TextContent

from scry.config import Config, load_config
from scry.run import Run

log = logging.getLogger(__name__)

MAX_IMAGE_WIDTH = 1280  # a frame image is downscaled to at most this wide before it is sent
SKIP_DIRS = {"frames", "overlays", "cache", "redecode", "batches"}  # never a run directory: not searched for one
MAX_DEPTH = 4  # `runs/eval/p4/full-inc-transcribing-r1` is depth 3
STAGES = ["decode", "outline", "read", "track", "annotate", "interpret", "summarize", "index"]  # scry.cli.STAGES, in order
ANNOTATE_MODES = ("incremental", "every_frame", "off")

INSTRUCTIONS = """\
scry answers questions about screen-recording videos from an index of what was on screen and what changed. Call
list_videos first to see the video ids, then search (exact strings in double quotes), get_node, get_transitions and
get_frame (with the image when a text is doubtful or the question is visual). Cite a frame ("frame 12"), a box
("12:b4") or a transition id ("T7") for every claim. A text on screen is not evidence that a command ran; a
transition with submitted: yes is. ask(video, question) runs scry's own answering agent (costs money, about 20 s).
index_video(path) runs the pipeline on a new video (minutes; dollars)."""


class Settings:
    """Where the server looks: the runs directory, the roots a video file may be under, the scry config."""

    def __init__(self, runs: Path = Path("runs"), videos: list[Path] | None = None, config: Path | None = None):
        self.runs = Path(runs)
        self.videos = [Path(v) for v in (videos or [Path(".")])]
        self.config = config

    def cfg(self) -> Config:
        return load_config(self.config)


settings = Settings()
server = MCPServer("scry", instructions=INSTRUCTIONS)


def configure(runs: Path, videos: list[Path] | None = None, config: Path | None = None) -> Settings:
    """Point the server at a runs directory (tests call this; `main` calls it from the command line)."""
    global settings
    settings = Settings(runs, videos, config)
    return settings


# ---- runs ----
def _find_runs(root: Path, depth: int = 0) -> list[Path]:
    """Directories under `root` (itself included) holding an index.sqlite, in path order, to MAX_DEPTH."""
    if not root.is_dir():
        return []
    found = [root] if (root / "index.sqlite").is_file() else []
    if depth < MAX_DEPTH:
        for child in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in SKIP_DIRS and not p.name.startswith(".")):
            found += _find_runs(child, depth + 1)
    return found


def video_ids() -> list[str]:
    return [p.relative_to(settings.runs).as_posix() or "." for p in _find_runs(settings.runs)]


def _run(video: str) -> Run:
    """The run of a video id, or a ToolError naming the ids there are. The id is a relative path: it must stay under
    the runs directory and hold an index."""
    runs_root = settings.runs.resolve()
    root = (settings.runs / video).resolve() if video and video != "." else runs_root
    if runs_root not in (root, *root.parents) or not (root / "index.sqlite").is_file():
        ids = video_ids()
        raise ToolError(f"unknown video {video!r}: the indexed videos under {settings.runs} are " + (", ".join(ids) if ids else "none"))
    return Run(root)


def _video_entry(root: Path) -> dict:
    run = Run(root)
    m = run.manifest_read()
    stages = m.get("stages", {})
    frames = stages.get("decode", {}).get("emitted")
    if frames is None and run.frames.exists():
        frames = sum(1 for line in run.frames.read_text().splitlines() if line.strip())
    return {"video": root.relative_to(settings.runs).as_posix() or ".", "video_id": m.get("video_id", root.name),
            "source": m.get("video"), "frames": frames, "duration_s": m.get("duration"),
            "annotated": run.annotations.exists() and run.annotations.stat().st_size > 0,
            "stages": [s for s in STAGES if s in stages], "cost_usd": m.get("costs", {}).get("total_usd") if isinstance(m.get("costs"), dict) else None}


def _tools(run: Run, frames: bool = False):
    from scry.ask import Tools

    cfg = settings.cfg()
    return Tools(run, cfg.model_copy(update={"ask": cfg.ask.model_copy(update={"frames": frames})}))


# ---- tools ----
@server.tool()
def list_videos() -> dict:
    """List the indexed videos this server can answer about: every run directory under the server's runs directory
    that holds an index. Each entry gives the video id to pass to the other tools (a relative path such as
    demo/aks-tutorial), the source file, the number of captured frames, the duration in seconds, whether the run
    is annotated (a vision model's second reading of every text, window labels and screen descriptions) and the
    pipeline stages done. Call this first."""
    return {"runs_dir": str(settings.runs), "videos": [_video_entry(p) for p in _find_runs(settings.runs)]}


@server.tool()
def search(video: str, query: str, level: str | None = None, t_from: float | None = None, t_to: float | None = None,
           app: str | None = None, limit: int = 20) -> dict:
    """Search the record of what was on a video's screen and what changed. Lexical: exact strings work best, and
    text inside double quotes is matched as a phrase (commands, flags, identifiers, paths). Returns ranked hits of
    several levels: lifetime (one on-screen text, once, with its first and last time, sightings and its readings:
    ocr, and vlm when the run is annotated; agree says whether they match), transition (a change between two
    captured frames with its interpretation: entered_text and submitted), frame (a whole screen; identical
    consecutive frames come back as one hit with a frame range, showing only the matching lines), step, section,
    video, chapter. Narrow with level, t_from and t_to (seconds) or app (the window's application; ignored, with a
    note, when the run has no window labels). A filtered search that finds nothing is worth repeating without the
    filter. Each hit carries a node_id for get_node."""
    tools = _tools(_run(video))
    try:
        out = tools.search(query, level=level, t_from=t_from, t_to=t_to, app=app)
    except Exception as e:
        raise ToolError(f"search failed: {type(e).__name__}: {e}")
    if limit is not None and limit >= 0:
        out["hits"] = out["hits"][:limit]
    return out


@server.tool()
def get_node(video: str, node_id: str) -> dict:
    """Fetch one index entry in full by node_id (from a search hit). A lifetime's payload holds every reading of each
    reader with counts, whether the readers agree, whether it was seen once, its links (a pair's key and value, a
    wrapped run) and its window. A transition's payload holds the full change record and the interpretation. A
    frame's payload lists every text box of that screen with its lifetime id. A step, section or video entry holds
    its label, description and time range."""
    out = _tools(_run(video)).get_node(node_id)
    if "error" in out:
        raise ToolError(f"{out['error']}: {node_id}")
    return out


@server.tool()
def get_transitions(video: str, t_a: float, t_b: float) -> dict:
    """List the transitions that overlap [t_a, t_b] seconds, in order: what changed (one line), the interpreted
    action and result, entered_text (what the user had entered, without anything the application suggested) and
    submitted (yes, no or unclear: whether what was entered took effect, judged from what the frames showed next).
    Use it to establish order: what was entered, whether and when it was submitted, what followed. Ask for a narrow
    range (a minute or two): a long result is large."""
    return _tools(_run(video)).get_transitions(t_a, t_b)


def _scaled_png(png: Path) -> tuple[bytes, str]:
    """The frame's PNG bytes at most MAX_IMAGE_WIDTH wide, and a note saying the scale."""
    from PIL import Image as PILImage

    with PILImage.open(png) as im:
        w, h = im.size
        if w <= MAX_IMAGE_WIDTH:
            return png.read_bytes(), f"Image: {w}x{h}, full resolution."
        scale = MAX_IMAGE_WIDTH / w
        small = im.convert("RGB").resize((MAX_IMAGE_WIDTH, round(h * scale)), PILImage.LANCZOS)
    buf = io.BytesIO()
    small.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), f"Image: {small.size[0]}x{small.size[1]}, scaled by {scale:.3f} from {w}x{h} (box rectangles are in full-resolution pixels)."


@server.tool(structured_output=False)
def get_frame(video: str, frame: int, image: bool = True) -> list[TextContent | ImageContent]:
    """Look at one captured frame: its record (the time range it was on screen, the screen description in force,
    every text alive at that frame with box id, lifetime id, text, when it was first and last seen, other readings
    and, when annotated, the window it belongs to) and, when image is true, the screenshot as an image (downscaled
    to at most 1280 px wide; the text says the scale). Use it when a reading is doubtful or the question is about
    something visual (a selection, a toggle, a dialog, a value in a form). Frame numbers come from search hits and
    transitions."""
    run = _run(video)
    tools = _tools(run, frames=False)
    record = tools.get_frame(frame)[0]["text"]
    if record == "no such frame":
        raise ToolError(f"no such frame {frame} in {video}")
    blocks: list[TextContent | ImageContent] = [TextContent(type="text", text=record)]
    if image:
        rec = next((f for f in run.load_frames() if f.frame == frame), None)
        png = run.root / rec.png if rec is not None else None
        if png is None or not png.is_file():
            blocks.append(TextContent(type="text", text="(the image file is missing)"))
        else:
            data, note = _scaled_png(png)
            blocks[0] = TextContent(type="text", text=record + "\n" + note)
            blocks.append(Image(data=data, format="png").to_image_content())
    return blocks


@server.tool()
def summary(video: str) -> dict:
    """The video's summary (label and description), and its sections and steps with their time ranges (seconds),
    frame ranges and descriptions, written by the pipeline from the transitions. Good for orientation and for
    finding where in the video something happens; confirm details with search, get_transitions and get_frame."""
    run = _run(video)
    node = run.load_video()

    def entry(n) -> dict:
        return {"id": n.id, "label": n.label, "t": list(n.t), "frames": list(n.frames), "children": list(n.children),
                "description": n.description, "segmentation_conf": n.segmentation_conf}

    if node is None and not run.sections.exists() and not run.steps.exists():
        raise ToolError(f"{video} has no summary: the summarize stage has not run")
    return {"video": video, "video_id": run.video_id, "duration_s": run.manifest_read().get("duration"),
            "summary": entry(node) if node is not None else None,
            "sections": [entry(s) for s in run.load_sections()], "steps": [entry(s) for s in run.load_steps()]}


@server.tool()
def ask(video: str, question: str) -> dict:
    """Answer a question about a video in one call with scry's own answering agent: a Claude model runs the search,
    get_node, get_transitions, get_frame and redecode tools over the index and writes an answer with citations
    (frames, boxes, lifetime and transition ids). Costs money (about $0.50-1 a question at high effort) and takes
    about 20-60 s. Returns the answer, its citations, the tool log (each call with its arguments and result count),
    usage and cost. Prefer the other tools when you want to read the evidence yourself."""
    from scry.ask import ask as _ask

    run = _run(video)
    try:
        result = _ask(run, settings.cfg(), question)
    except Exception as e:
        raise ToolError(f"ask failed: {type(e).__name__}: {e}")
    return {"answer": result.text, "citations": result.citations, "stop": result.stop, "turns": result.turns,
            "tool_log": [c.model_dump() for c in result.tool_log], "usage": result.usage, "cost_usd": result.cost_usd, "model": result.model}


def _toml(d: dict, prefix: str = "") -> str:
    """A TOML text of a nested dict of tables and scalars (what Config.model_dump() is). TOML has no null: a key whose
    value is None ([model] temperature unset) is left out, and loading the text gives the default, None, back."""
    lines, tables = [], []
    for k, v in d.items():
        if isinstance(v, dict):
            tables.append((f"{prefix}{k}", v))
        elif v is not None:
            lines.append(f"{k} = {json.dumps(v)}")
    out = (f"[{prefix.rstrip('.')}]\n" if prefix and lines else "") + "\n".join(lines) + ("\n" if lines else "")
    return out + "".join("\n" + _toml(v, f"{name}.") for name, v in tables)


def _video_path(path: str) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path.cwd() / p
    p = p.resolve()
    roots = [r.resolve() for r in settings.videos]
    if not any(r in (p, *p.parents) for r in roots):
        raise ToolError(f"{path} is outside the allowed video roots ({', '.join(str(r) for r in settings.videos)}); start the server with --videos to allow it")
    if not p.is_file():
        raise ToolError(f"{path} is not a file")
    return p


@server.tool()
async def index_video(path: str, out: str | None = None, annotate: str = "incremental", ctx: Context | None = None) -> dict:
    """Index a screen-recording video file with scry's pipeline (decode, read, track, annotate, interpret,
    summarize, index), so the other tools can answer about it. Costs money and time: on the 14-minute sample about
    $5 and 25 min without annotation (annotate="off"), about $18 and 35 min with (annotate="incremental", the
    default: a vision model reads every text again and labels windows; "every_frame" is dearer). Idempotent: a stage
    whose inputs and config are unchanged is skipped, so re-running a finished video is free. `path` must be under
    the server's --videos roots; `out` is the run directory (default: runs/<video file stem>). Progress
    notifications name each stage as it starts. Returns the video id to use with the other tools, the stages done
    and the costs."""
    src = _video_path(path)
    if annotate not in ANNOTATE_MODES:
        raise ToolError(f"annotate must be one of {', '.join(ANNOTATE_MODES)}")
    out_dir = (settings.runs / (out or src.stem)).resolve() if out is None or not Path(out).is_absolute() else Path(out)
    runs_root = settings.runs.resolve()
    if runs_root not in (out_dir, *out_dir.parents):
        raise ToolError(f"out must be under the runs directory {settings.runs}")
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = settings.cfg()
    cfg.annotate.mode = annotate  # type: ignore[assignment]
    cfg_path = out_dir / "mcp-config.toml"
    cfg_path.write_text(_toml(cfg.model_dump()))
    cmd = [sys.executable, "-m", "scry.cli", "run", str(src), "--out", str(out_dir), "--config", str(cfg_path)]
    log.info("index_video: %s", " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    tail: list[str] = []
    stage_no = 0
    assert proc.stdout is not None
    async for raw in proc.stdout:
        line = raw.decode(errors="replace").rstrip()
        tail = (tail + [line])[-40:]
        if line.startswith("== "):
            stage_no += 1
            if ctx is not None:
                try:
                    await ctx.report_progress(stage_no, len(STAGES) + 1, f"{line[3:]} ({stage_no}/{len(STAGES)})")
                except Exception:  # a host without progress support: the stage log is still returned
                    pass
    code = await proc.wait()
    run = Run(out_dir)
    m = run.manifest_read()
    video = out_dir.relative_to(runs_root).as_posix()
    if code != 0:
        raise ToolError(f"scry run exited with {code}; last lines:\n" + "\n".join(tail))
    return {"video": video, "stages": [s for s in STAGES if s in m.get("stages", {})], "costs": m.get("costs"),
            "log_tail": tail[-15:]}


# ---- entry point ----
def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="scry-mcp", description="MCP server over scry's video indexes (stdio).")
    parser.add_argument("--runs", type=Path, default=Path("runs"), help="directory whose run directories are the videos (default: runs)")
    parser.add_argument("--videos", type=Path, action="append", help="a root index_video may read video files from (repeatable; default: the current directory)")
    parser.add_argument("--config", type=Path, default=None, help="scry config file (default: ./scry.toml)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(name)s %(message)s")
    from scry.env import load_dotenv

    load_dotenv()  # the keys the pipeline and `ask` need; never printed
    configure(args.runs, args.videos, args.config)
    log.info("scry-mcp: runs=%s videos=%s", settings.runs, [str(v) for v in settings.videos])
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
