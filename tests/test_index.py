from pathlib import Path

from minirun import mini_interpretations, mini_run

from scry.config import Config, IndexConfig
from scry.index import Node, build_index, fts_query, index_nodes, open_db, rrf, search, trigram_query


def node(i, text, level="transition", t=(0.0, 1.0), apps=("Windows Terminal",)):
    return Node(node_id=f"n{i}", video_id="v1", level=level, item_id=f"T{i}", frames=(i, i + 1), t=t, apps=list(apps),
                text=text, payload={"id": f"T{i}"})


def test_fts_query_quotes_every_term_and_trigram_needs_three_chars():
    assert fts_query('az aks create --resource-group "rg demo"') == '"az" OR "aks" OR "create" OR "--resource-group" OR "rg demo"'
    assert trigram_query("az") is None
    assert trigram_query("KodeKloud aks") == '"KodeKloud" OR "aks"'


def test_rrf_fuses_rankings():
    fused = rrf([["a", "b", "c"], ["b", "a"]], 60)
    assert [x for x, _ in fused][:2] == ["a", "b"] or [x for x, _ in fused][:2] == ["b", "a"]
    assert fused[0][1] > fused[-1][1]


def test_index_and_search_exact_identifiers_and_substrings(tmp_path):
    db = open_db(tmp_path / "i.sqlite")
    nodes = [node(1, "az aks create --resource-group RG1-KodeKloud-AKS --name AKS1-KodeKloudApp", t=(10, 20)),
             node(2, "kubectl get nodes", t=(30, 40)),
             node(3, "Configure the storage account", level="step", t=(50, 60), apps=("Browser",))]
    index_nodes(db, nodes, None)
    cfg = IndexConfig()
    hits = search(db, "--resource-group", cfg)
    assert hits and hits[0]["node_id"] == "n1"
    assert "layout_conf" not in hits[0]
    hits = search(db, "KodeKloud", cfg)          # substring via trigram
    assert hits and hits[0]["node_id"] == "n1"
    hits = search(db, "storage", cfg, level="step")
    assert [h["node_id"] for h in hits] == ["n3"]
    hits = search(db, "kubectl", cfg, t_from=0, t_to=25)
    assert hits == []


def test_build_index_stats_and_rerun(tmp_path: Path):
    run = mini_run(tmp_path, labels=True)
    mini_interpretations(run)
    build_index(run, Config())
    stats = run.manifest_read()["stages"]["index"]
    assert stats["by_level"] == {"frame": 4, "lifetime": 7, "transition": 3}
    assert (stats["nodes"], stats["labels"], stats["embedder"]) == (14, True, "none")
    built = run.index_db.stat()
    build_index(run, Config())  # up to date: nothing is rebuilt
    assert run.index_db.stat().st_mtime_ns == built.st_mtime_ns
    run.interpretations.unlink()
    build_index(run, Config())  # an input changed
    assert run.index_db.stat().st_mtime_ns != built.st_mtime_ns


def _mini_db(tmp_path: Path, labels: bool = True):
    run = mini_run(tmp_path, labels=labels)
    mini_interpretations(run)
    build_index(run, Config())
    return open_db(run.index_db)


def _frame_members(hits: list[dict]) -> list[list[int]]:
    return sorted(h["members"] for h in hits if h["level"] == "frame")


def test_search_collapses_identical_consecutive_frame_hits(tmp_path: Path):
    db = _mini_db(tmp_path)
    hits = search(db, "Creating", IndexConfig())
    assert [h["node_id"] for h in hits] == ["v:L2", "v:T3", "v:f10"]
    assert [h["score"] for h in hits] == [0.03279] * 3  # rank 1 in its FTS5 and its trigram ranking: 2/61
    frame = hits[2]
    assert (frame["frames"], frame["t"], frame["collapsed"], frame["members"]) == ([10, 12], [20.4, 30.0], 3, [10, 11, 12])
    assert frame["matched"] == ["Creating", "Status Creating"]
    plain = search(db, "Creating", IndexConfig(), collapse=False)
    assert {h["node_id"] for h in plain} == {"v:L2", "v:T3", "v:f10", "v:f11", "v:f12"}
    assert all(h.get("collapsed", 1) == 1 for h in plain)


def test_differing_matching_text_is_not_collapsed(tmp_path: Path):
    # frame 11 also matches the model's reading `C:\src> git st`
    assert _frame_members(search(_mini_db(tmp_path / "labelled"), "git", IndexConfig())) == [[10], [11], [12, 13]]
    assert _frame_members(search(_mini_db(tmp_path / "plain", labels=False), "git", IndexConfig())) == [[10], [11, 12, 13]]


def test_ocr_variant_prevents_a_collapse(tmp_path: Path):
    assert _frame_members(search(_mini_db(tmp_path), "branch", IndexConfig())) == [[12], [13]]  # frame 13 reads `On branch maln`


def test_level_and_time_filters(tmp_path: Path):
    db, cfg = _mini_db(tmp_path), IndexConfig()
    assert [h["node_id"] for h in search(db, "Creating", cfg, level="frame")] == ["v:f10"]
    assert search(db, "Creating", cfg, level="region") == []
    later = [h for h in search(db, "Creating", cfg, t_from=25.0) if h["level"] == "frame"]
    assert [(h["members"], h["frames"]) for h in later] == [([11, 12], [11, 12])]  # frame 10 ends at 24.0
    terminal = search(db, "Status", cfg, app="Terminal")
    assert terminal and all("Windows Terminal" in h["apps"] for h in terminal)


def test_search_survives_fts_syntax(tmp_path: Path):
    db, cfg = _mini_db(tmp_path), IndexConfig()
    for q in ("--name", "C:\\src>", '"git status', "*", "a", "git AND NOT status", "("):
        search(db, q, cfg)
    assert search(db, "C:\\src>", cfg)
