from pathlib import Path

from minirun import mini_run


def test_mini_run_labels(tmp_path: Path):
    """The tripwire for the labels interface (plan 3, A4 and A7) and the only test of the fixture itself."""
    labels = mini_run(tmp_path, labels=True).load_labels()
    assert labels is not None
    assert labels.box("11:b3").agree is False and labels.box("11:b3").vlm == "C:\\src> git st"
    assert labels.box("13:b2").link.role == "value" and labels.box("13:b2").link.key == ["13:b1"]
    assert labels.box("12:b1").pane == "Essentials"
    assert labels.frame(13).description == "The Status value now reads Succeeded."
    assert [m.text for m in labels.frame(13).missed] == ["Refresh"]
    assert labels.lifetime("L5").vlm == "On branch main"
    assert mini_run(tmp_path / "plain").load_labels() is None
