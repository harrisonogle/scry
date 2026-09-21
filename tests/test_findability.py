"""The findability guarantee of plan 3 (F1 to F6; F7 and F8 are in test_ask.py): nothing findable before the re-base
may become unfindable. This file is the contract and is never weakened to make a change pass."""
import json
from pathlib import Path

from minirun import mini_interpretations, mini_run

from scry.config import Config, IndexConfig
from scry.index import Node, build_index, fts_query, index_nodes, open_db, search, trigram_query
from scry.jsonl import write_jsonl
from scry.nodes import frame_nodes, lifetime_nodes
from scry.run import Run
from scry.schemas import Box, Frame, FrameBoxes, FrameTime, Lifetime


def _nodes(run: Run):
    labels, lifetimes = run.load_labels(), run.load_lifetimes()
    frames = frame_nodes(run, run.load_frames(), {fb.frame: fb for fb in run.load_boxes()}, lifetimes, labels)
    return {n.node_id: n for n in frames}, {n.node_id: n for n in lifetime_nodes(run, lifetimes, labels)}


def _hand_run(root: Path, boxes: dict[int, list[tuple[str, str, tuple[int, int, int, int]]]], lifetimes: list[Lifetime],
              annotations: list[dict]) -> Run:
    """Frames n = 0, 1, … with (t_change, t_settled, t_end) = (2n, 2n + 0.4, 2n + 2); no PNG is needed for nodes."""
    run = Run(root)
    run.manifest_update(video="v.mp4", video_id="v")
    write_jsonl(run.frames, [Frame(video_id="v", frame=n, t_change=2.0 * n, t_settled=2.0 * n + 0.4, t_end=2.0 * n + 2.0, settled=True,
                                   width=400, height=200, sha256=f"sha{n}", png=f"frames/{n:05d}.png") for n in boxes])
    write_jsonl(run.boxes, [FrameBoxes(frame=n, png=f"frames/{n:05d}.png", engine={},
                                       boxes=[Box(id=i, bbox=bbox, text=text, conf=1.0) for i, text, bbox in bs]) for n, bs in boxes.items()])
    write_jsonl(run.lifetimes, lifetimes)
    run.annotations.write_text("".join(json.dumps(a) + "\n" for a in annotations))
    return run


def _life(id: str, readings: dict[str, list[int]], box: str, last_t: float, unstable: bool = False) -> Lifetime:
    frames = sorted(n for ns in readings.values() for n in ns)
    return Lifetime(id=id, text=next(iter(readings)), readings=readings, unstable=unstable, sightings=len(frames),
                    first=FrameTime(frame=frames[0], t=0.4), last=FrameTime(frame=frames[-1], t=last_t),
                    boxes=[f"{n}:{box}" for n in frames])


def test_frame_document_is_a_superset(tmp_path: Path):
    run = mini_run(tmp_path, labels=True)
    frames, _ = _nodes(run)
    assert frames["v:f13"].text == ("Azure Portal Resource overview\nWindows Terminal PowerShell\nEssentials\nStatus\nSucceeded\n"
                                    "C:\\src> git status\nOn branch maln\nC:\\src>\nOn branch main\nRefresh\nStatus Succeeded\n"
                                    "The Status value now reads Succeeded.")
    assert frames["v:f11"].text == ("Azure Portal Resource overview\nWindows Terminal PowerShell\nEssentials\nStatus\nCreating\n"
                                    "C:\\src> git status\nC:\\src> git st\nStatus Creating\n"
                                    "The Overview item is highlighted in the left navigation.")
    for fb in run.load_boxes():
        lines = frames[f"v:f{fb.frame}"].text.split("\n")
        for b in fb.boxes:
            assert b.text in lines, (fb.frame, b.id)


def test_tokenizers_and_query_builders_unchanged(tmp_path: Path):
    db = open_db(tmp_path / "i.sqlite")
    sql = dict(db.execute("SELECT name, sql FROM sqlite_master WHERE name IN ('nodes_fts', 'nodes_tri')").fetchall())
    assert "tokenize=\"unicode61 tokenchars '-_./:\\'\"" in sql["nodes_fts"]
    assert "tokenize='trigram'" in sql["nodes_tri"]
    assert fts_query('az aks create --resource-group "rg demo"') == '"az" OR "aks" OR "create" OR "--resource-group" OR "rg demo"'
    assert trigram_query("az") is None


def test_non_text_never_removes_a_frame_line(tmp_path: Path):
    boxes = [("b1", "区", (24, 164, 48, 179)), ("b2", "Overview", (60, 164, 140, 179))]
    record = {"targets": ["b1", "b2"], "model": "fake-model", "prompt_version": "annotate-v1", "containers": [], "assign": [],
              "links": [], "missed": [], "repairs": 0, "usage": {}}
    annotations = [record | {"frame": 0, "unassigned": ["b1", "b2"], "description": "", "error": None,
                             "texts": [{"box": "b1", "text": ""}, {"box": "b2", "text": "Overview"}]},
                   record | {"frame": 1, "unassigned": [], "description": None, "error": "refusal", "texts": None}]  # a failed record
    run = _hand_run(tmp_path, {0: boxes, 1: boxes}, [_life("L1", {"区": [0, 1]}, "b1", 4.0), _life("L2", {"Overview": [0, 1]}, "b2", 4.0)],
                    annotations)
    frames, lifetimes = _nodes(run)
    assert [n.text for n in frames.values()] == ["区\nOverview", "区\nOverview"]
    assert [(n.node_id, n.text, n.payload["non_text"]) for n in lifetimes.values()] == [("v:L1", "区", True), ("v:L2", "Overview", False)]


def test_every_reading_and_both_joins_are_searchable(tmp_path: Path):
    good, bad = "git commit --amend --no-ed", "git comit --amend --no-ed"
    boxes = {n: [("b1", bad if n == 1 else good, (10, 10, 300, 28)), ("b2", "it", (10, 30, 40, 48))] for n in (0, 1, 2)}
    annotations = [{"frame": n, "targets": ["b1", "b2"], "model": "fake-model", "prompt_version": "annotate-v1",
                    "containers": [{"id": "c1", "kind": "window", "app": "Terminal", "name": "shell", "owner": None, "covers": []}],
                    "assign": [{"box": "b1", "container": "c1"}, {"box": "b2", "container": "c1"}],
                    "links": [{"kind": "run", "boxes": ["b1", "b2"], "joiner": ""}], "texts": None, "missed": [], "unassigned": [],
                    "description": "", "repairs": 0, "usage": {}, "error": None} for n in (0, 1, 2)]  # group-only records
    run = _hand_run(tmp_path, boxes, [_life("L1", {good: [0, 2], bad: [1]}, "b1", 6.0, unstable=True),
                                      _life("L2", {"it": [0, 1, 2]}, "b2", 6.0)], annotations)
    _, lifetimes = _nodes(run)
    assert lifetimes["v:L1"].text == f"{good}\n{bad}\ngit commit --amend --no-edit\ngit commit --amend --no-ed it"
    db = open_db(tmp_path / "i.sqlite")
    index_nodes(db, list(lifetimes.values()), None)
    for query in ("--no-edit", '"--no-ed it"', "comit"):
        assert search(db, query, IndexConfig())[0]["node_id"] == "v:L1", query


def test_index_without_annotations_holds_every_ocr_text(tmp_path: Path):
    run = mini_run(tmp_path)  # no labels, no interpretations
    build_index(run, Config())
    db = open_db(run.index_db)
    for fb in run.load_boxes():
        for b in fb.boxes:
            hits = search(db, '"' + b.text + '"', IndexConfig(k=50))
            assert any(h["frames"][0] <= fb.frame <= h["frames"][1] for h in hits), (fb.frame, b.id)


def test_many_lifetime_hits_do_not_displace_the_frame_hit(tmp_path: Path):
    nodes = [Node(node_id=f"L{i:02d}", video_id="v", level="lifetime", item_id=f"L{i:02d}", frames=(0, 0), t=(i, i + 1), text="alpha")
             for i in range(1, 31)]
    nodes.append(Node(node_id="f0", video_id="v", level="frame", item_id="0", frames=(0, 0), t=(0.0, 1.0), text="alpha\nbeta",
                      payload={"ordinal": 0}))
    db = open_db(tmp_path / "i.sqlite")
    index_nodes(db, nodes, None)
    hits = search(db, "alpha", IndexConfig())
    assert len(hits) == 20
    assert hits[1]["node_id"] == "f0"  # tied with the first lifetime at 2/61; the family order breaks the tie


def test_collapse_is_a_partition_of_the_frame_hits(tmp_path: Path):
    run = mini_run(tmp_path, labels=True)
    mini_interpretations(run)
    build_index(run, Config())
    db, cfg = open_db(run.index_db), IndexConfig()
    times = {f.frame: (f.t_settled, f.t_end) for f in run.load_frames()}
    for query in ("Status", "git", "branch", "Creating"):
        before = [h["node_id"] for h in search(db, query, cfg, collapse=False, level="frame")]
        hits = search(db, query, cfg, level="frame")
        members = [m for h in hits for m in h["members"]]
        assert len(before) == len(set(before)) and len(members) == len(set(members))
        assert set(before) == {f"v:f{m}" for m in members}, query
        for h in hits:
            assert h["collapsed"] == len(h["members"])
            assert h["frames"] == [h["members"][0], h["members"][-1]]
            assert h["t"] == [times[h["members"][0]][0], times[h["members"][-1]][1]]
