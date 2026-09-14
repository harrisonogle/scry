from pathlib import Path

from scry.agent import TOOL_DEFS, Tools
from scry.config import Config
from scry.index import Node, index_nodes, open_db
from scry.run import Run


def test_tools_search_and_get_node(tmp_path: Path):
    run = Run(tmp_path / "r")
    db = open_db(run.index_db)
    index_nodes(db, [Node(node_id="v:T1", video_id="v", level="transition", item_id="T1", frames=(1, 2), t=(3.0, 4.0),
                          text='typed "kubectl get nodes"', payload={"id": "T1"})], None)
    db.close()
    tools = Tools(run, Config())
    res = tools.search("kubectl")
    assert res["hits"][0]["item_id"] == "T1" and res["hits"][0]["t"] == [3.0, 4.0]
    assert tools.get_node("v:T1")["payload"] == {"id": "T1"}
    assert {t["name"] for t in TOOL_DEFS} == {"search", "get_node", "get_transitions", "get_frame", "redecode"}
