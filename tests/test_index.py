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
