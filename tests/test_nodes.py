from pathlib import Path

from minirun import mini_run

from scry.nodes import frame_nodes, lifetime_nodes, link_anchor, link_lines
from scry.schemas import PairLink, RecordLink, RunLink


def _frame_nodes(run):
    nodes = frame_nodes(run, run.load_frames(), {fb.frame: fb for fb in run.load_boxes()}, run.load_lifetimes(), run.load_labels())
    return {n.node_id: n for n in nodes}


def _lifetime_nodes(run):
    return {n.node_id: n for n in lifetime_nodes(run, run.load_lifetimes(), run.load_labels())}


def test_frame_nodes_without_labels(tmp_path: Path):
    nodes = _frame_nodes(mini_run(tmp_path))
    assert list(nodes) == ["v:f10", "v:f11", "v:f12", "v:f13"]
    n = nodes["v:f11"]
    assert (n.level, n.item_id, n.frames, n.t, n.apps) == ("frame", "11", (11, 11), (24.4, 26.0), [])
    assert n.text == "Status\nCreating\nC:\\src> git status"
    assert (n.payload["ordinal"], n.payload["description"]) == (1, None)
    assert n.payload["boxes"][2] == {"id": "b3", "text": "C:\\src> git status", "lifetime": "L4"}


def test_frame_node_metadata_with_labels(tmp_path: Path):
    n = _frame_nodes(mini_run(tmp_path, labels=True))["v:f12"]
    assert n.apps == ["Azure Portal", "Windows Terminal"]
    assert n.containers == ["Resource overview", "PowerShell"]
    assert n.payload["description"] == "The terminal shows new output."


def test_link_lines():
    """Built with the per-kind classes, which carry only their own kind's fields: reading another kind's field raises."""
    run = RunLink(boxes=["b1", "b2"], joiner="")
    assert link_lines(run, {"b1": "git commit --amend --no-ed", "b2": "it"}.__getitem__) == ["git commit --amend --no-edit",
                                                                                              "git commit --amend --no-ed it"]
    assert link_anchor(run) == "b1"
    pair = PairLink(key=["b1", "b2"], value=["b3"])
    assert link_lines(pair, {"b1": "Resource", "b2": "group", "b3": "rg-demo"}.__getitem__) == ["Resource group rg-demo"]
    assert link_anchor(pair) == "b3"
    record = RecordLink(members=[["b1"], ["b2"], ["b3", "b4"]], header=["b9"])
    assert link_lines(record, {"b1": "node-1", "b2": "Ready", "b3": "1.2", "b4": "GiB"}.__getitem__) == ["node-1 Ready 1.2 GiB"]
    assert link_anchor(record) == "b1"


def test_lifetime_nodes_with_labels(tmp_path: Path):
    nodes = _lifetime_nodes(mini_run(tmp_path, labels=True))
    assert list(nodes) == [f"v:L{k}" for k in range(1, 8)]
    l4 = nodes["v:L4"]
    assert (l4.level, l4.item_id, l4.text) == ("lifetime", "L4", "C:\\src> git status\nC:\\src> git st")
    assert (l4.frames, l4.t, l4.apps) == ((11, 13), (24.4, 35.0), ["Windows Terminal"])
    assert (l4.payload["agree"], l4.payload["non_text"], l4.payload["seen_once"]) == (True, False, False)
    assert l4.payload["readers"]["ocr"]["readings"] == {"C:\\src> git status": 3}
    assert l4.payload["readers"]["vlm"]["readings"] == {"C:\\src> git status": 2, "C:\\src> git st": 1}
    l5 = nodes["v:L5"]
    assert l5.text == "On branch main\nOn branch maln"
    assert l5.payload["lifetime"]["unstable"] is True
    assert l5.payload["readers"]["ocr"]["readings"] == {"On branch main": 1, "On branch maln": 1}
    l2 = nodes["v:L2"]
    assert (l2.text, l2.t) == ("Creating\nStatus Creating", (20.4, 30.0))
    assert l2.payload["links"] == [{"kind": "pair", "lines": ["Status Creating"], "key": "Status", "value": "Creating", "seen": 3}]
    l7 = nodes["v:L7"]
    assert (l7.text, l7.payload["seen_once"], l7.payload["links"][0]["seen"]) == ("Succeeded\nStatus Succeeded", True, 1)
    assert (nodes["v:L1"].text, nodes["v:L1"].payload["links"]) == ("Status", [])  # the key of both pairs, the anchor of neither


def test_lifetime_nodes_without_labels(tmp_path: Path):
    nodes = _lifetime_nodes(mini_run(tmp_path))
    assert nodes["v:L2"].text == "Creating"
    assert nodes["v:L5"].text == "On branch main\nOn branch maln"
    payload = nodes["v:L5"].payload
    assert (payload["readers"]["vlm"], payload["agree"], payload["non_text"], payload["container"]) == (None, None, False, None)
    assert nodes["v:L5"].apps == []
