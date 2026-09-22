from pathlib import Path

from minirun import mini_interpretations, mini_run

from scry.nodes import frame_nodes, lifetime_nodes, link_anchor, link_lines, summary_nodes, transition_nodes
from scry.schemas import HierNode, PairLink, RecordLink, RunLink


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


def _transition_nodes(run, steps=(), sections=()):
    nodes = transition_nodes(run, run.load_changes(), run.load_interpretations(), run.load_labels(), list(steps), list(sections))
    return {n.node_id: n for n in nodes}


def test_transition_nodes(tmp_path: Path):
    run = mini_run(tmp_path)
    mini_interpretations(run)
    nodes = _transition_nodes(run)
    assert nodes["v:T1"].text == ('git st\nThe user typed " st" in the terminal; the shell offers "atus" as a completion.\n'
                                  'The command line now reads git st with a greyed suggestion.\nC:\\src> git\nC:\\src> git status')
    t2 = nodes["v:T2"]  # its records are `appeared` and the interpretation left something, so the fallback does not apply
    assert t2.text == 'git status\nThe user pressed Enter.\nGit printed "On branch main" and a new prompt appeared.'
    assert (t2.level, t2.item_id, t2.frames, t2.t) == ("transition", "T2", (11, 12), (26.0, 26.4))
    assert t2.payload["interpretation"]["submitted"] == "yes"
    assert t2.payload["change"]["id"] == "T2"
    assert nodes["v:T3"].text.endswith("\nCreating\nSucceeded")


def test_transition_node_without_interpretation(tmp_path: Path):
    nodes = _transition_nodes(mini_run(tmp_path))
    assert nodes["v:T1"].text == "C:\\src> git\nC:\\src> git status"
    assert nodes["v:T2"].text == "On branch main\nC:\\src>"  # the appeared records
    assert nodes["v:T2"].payload["interpretation"] is None


def test_step_and_section_ids_on_transitions(tmp_path: Path):
    run = mini_run(tmp_path)
    steps = [HierNode(id="S1", level="step", children=("T1", "T2"), frames=(10, 12), t=(24.0, 26.4), label="a", description="b"),
             HierNode(id="S2", level="step", children=("T3", "T3"), frames=(12, 13), t=(30.0, 30.4), label="c", description="d")]
    sections = [HierNode(id="C1", level="section", children=("S1", "S2"), frames=(10, 13), t=(24.0, 30.4), label="e", description="f")]
    nodes = _transition_nodes(run, steps, sections)
    assert (nodes["v:T2"].step_id, nodes["v:T3"].step_id) == ("S1", "S2")
    assert (nodes["v:T2"].section_id, nodes["v:T3"].section_id) == ("C1", "C1")
    summaries = {n.node_id: n for n in summary_nodes(run, steps, sections, None)}
    assert (summaries["v:S1"].section_id, summaries["v:S2"].section_id, summaries["v:S1"].text) == ("C1", "C1", "a\nb")
