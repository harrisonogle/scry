from scry.textdiff import char_diff, lcp_len, myers, norm, similarity


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


def test_char_diff_runs():
    assert char_diff("git stauts", "git status") == [["=", "git sta"], ["-", "u"], ["=", "t"], ["+", "u"], ["=", "s"]]


def test_lcp():
    assert lcp_len("PS> git st", "PS> git status") == 10
