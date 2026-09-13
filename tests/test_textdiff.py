from vt.schemas import DiffOp
from vt.textdiff import char_diff, is_clock_change, lcp_len, line_ops, myers, norm, pair_modifies, similarity


def test_norm_collapses_whitespace_and_quotes_but_keeps_case():
    assert norm("  git   status ") == "git status"
    assert norm("say “hi” and ‘bye’") == 'say "hi" and \'bye\''
    assert norm("MyCluster") == "MyCluster"


def test_similarity_short_lines():
    assert similarity("ls", "1s") == 0.5
    assert similarity("git status", "git status") == 1.0


def test_myers_minimal_script():
    a = ["a", "b", "c", "d"]
    b = ["a", "c", "d", "e"]
    runs = myers(a, b)
    ops = [r[0] for r in runs]
    assert ops == ["equal", "delete", "equal", "equal", "insert"]
    assert runs[1] == ("delete", 1, 1)
    assert runs[-1] == ("insert", 4, 3)


def test_line_ops_scroll_is_equal_plus_inserts():
    prev = ["l1", "l2", "l3"]
    cur = ["l2", "l3", "l4", "l5"]
    ops = line_ops(prev, cur)
    assert [(o["op"], o.get("old_index"), o.get("new_index")) for o in ops] == [
        ("delete", 0, None), ("insert", None, 2), ("insert", None, 3)]


def test_pair_modifies_by_y_overlap():
    ops = line_ops(["PS> gi"], ["PS> git status"])
    paired = pair_modifies(ops, prev_y=[41], cur_y=[41], line_h=18, sim_threshold=0.6)
    assert len(paired) == 1 and paired[0].op == "modify"
    assert paired[0].old == "PS> gi" and paired[0].new == "PS> git status"
    assert paired[0].char_diff == [["=", "PS> gi"], ["+", "t status"]]
    assert paired[0].y == 41


def test_pair_modifies_keeps_unrelated_lines_apart():
    ops = line_ops(["alpha"], ["zzzzz"])
    paired = pair_modifies(ops, prev_y=[10], cur_y=[400], line_h=18, sim_threshold=0.6)
    assert [o.op for o in paired] == ["delete", "insert"]


def test_char_diff_runs():
    assert char_diff("git stauts", "git status") == [["=", "git sta"], ["-", "u"], ["=", "t"], ["+", "u"], ["=", "s"]]


def test_clock_change():
    assert is_clock_change("Tue 14:02", "Tue 14:03")
    assert is_clock_change("14:02:59 PM", "14:03:00 PM")
    assert not is_clock_change("14:02 build ok", "14:03 build failed")
    assert not is_clock_change("a", "b")


def test_lcp():
    assert lcp_len("PS> git st", "PS> git status") == 10
