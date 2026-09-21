from scry.config import IndexConfig
from scry.index import Node, fts_query, index_nodes, open_db, rrf, search, trigram_query


def node(i, text, level="transition", t=(0.0, 1.0), apps=("Windows Terminal",)):
    return Node(node_id=f"n{i}", video_id="v1", level=level, item_id=f"T{i}", frames=(i, i + 1), t=t, apps=list(apps),
                region_names=[], layout_conf=0.9, text=text, payload={"id": f"T{i}"})


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
    hits = search(db, "KodeKloud", cfg)          # substring via trigram
    assert hits and hits[0]["node_id"] == "n1"
    hits = search(db, "storage", cfg, level="step")
    assert [h["node_id"] for h in hits] == ["n3"]
    hits = search(db, "kubectl", cfg, t_from=0, t_to=25)
    assert hits == []


def test_region_nodes_carry_association_text_as_one_searchable_line(tmp_path):
    from scry.index import extract_nodes, region_text
    from scry.jsonl import write_jsonl
    from scry.run import Run
    from scry.schemas import FrameRecord, Line, Region

    def line(i, text, vlm=None, agree=True):
        return Line(id=f"l{i}", marks=[f"l{i}"], bbox=(0, 20 * i, 100, 20 * i + 18), ocr=text, ocr_conf=1.0, vlm=vlm or text, agree=agree, in_churn=False)

    reg = Region(id="r7", kind="pane", name="Essentials", app="Azure Portal", parent="r1", bbox=(0, 0, 100, 100), conf=0.9, layout_conf=0.9,
                 lines=[line(1, "Resource group"), line(2, ":"), line(3, "RG1-KodeKloud-AKS"), line(4, "Status"), line(5, "Succeded", "Succeeded", False)],
                 associations=[["l1", "l2", "l3"], ["l4", "l5"]])
    text, assoc = region_text(reg)
    assert text == "Resource group\n:\nRG1-KodeKloud-AKS\nStatus\nSucceded\nSucceeded\nResource group : RG1-KodeKloud-AKS\nStatus Succeded"
    assert assoc == [{"marks": ["l1", "l2", "l3"], "text": "Resource group : RG1-KodeKloud-AKS"}, {"marks": ["l4", "l5"], "text": "Status Succeded"}]
    assert region_text(Region(**reg.model_dump(exclude={"associations"}))) == (text.rsplit("\nResource group :", 1)[0], [])

    run = Run(tmp_path)
    write_jsonl(run.frames, [FrameRecord(video_id="v", frame=150, t_change=1, t_settled=1.2, t_end=5, settled=True, png="frames/00150.png", overlay=None,
                                         sha256="x", width=100, height=100, regions=[reg])])
    [node] = [n for n in extract_nodes(run) if n.level == "region"]
    assert node.text == f"Azure Portal Essentials\n{text}" and node.payload["associations"] == assoc and node.payload["region"] == "r7"
    db = open_db(tmp_path / "i.sqlite")
    index_nodes(db, [node], None)
    hits = search(db, '"Resource group : RG1-KodeKloud-AKS"', IndexConfig())
    assert hits and hits[0]["node_id"] == node.node_id and "Resource group : RG1-KodeKloud-AKS" in hits[0]["text"]
