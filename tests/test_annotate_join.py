from pathlib import Path

import pytest
from annotate_fixtures import fixture_t, record_a10, record_a11, write_run

from scry.annotate.join import BoxLink, FrameLabel, agreement, build_labels
from scry.jsonl import write_jsonl
from scry.schemas import Annotation, Assign, Container, PairLink, RunLink, TextReading


def _labels(records):
    _, frames, _, lifetimes = fixture_t()
    return build_labels(records, frames, lifetimes)


def test_own_record_and_carried_labels():
    labels = _labels([record_a10(), record_a11()])
    own = labels.box("10:b4")
    assert (own.source, own.container.id, own.container.app) == ("10:b4", "c2", "PowerShell")
    assert (own.vlm, own.agree, own.non_text) == ("PS C:\\> a", False, False)
    carried = labels.box("11:b2")
    assert (carried.source, carried.container.app, carried.vlm, carried.agree) == ("10:b1", "Browser", "Resource group", True)
    typed = labels.box("12:b5")
    assert (typed.source, typed.container.id, typed.container.app) == ("11:b5", "c1", "PowerShell")  # the id is A11's own
    assert (typed.vlm, typed.agree) == ("PS C:\\> az login", True)
    title = labels.box("12:b4")  # the same window as 12:b5, labelled by another record under another id
    assert (title.source, title.container.id, title.container.app) == ("10:b3", "c2", "PowerShell")
    banner = labels.box("12:b1")
    assert (banner.source, banner.container.app) == ("11:b1", "Browser")


def test_links_in_force():
    labels = _labels([record_a10(), record_a11()])
    assert labels.frame(10).links == [PairLink(key=["10:b1"], value=["10:b2"])]
    # A11's pair names 11:b2, which A10's pair still holds: refused
    assert labels.frame(11).links == [PairLink(key=["11:b2"], value=["11:b3"]), RunLink(boxes=["11:b4", "11:b5"], joiner=" ")]
    assert labels.relinked == 1
    assert labels.frame(12).links == [PairLink(key=["12:b2"], value=["12:b3"]), RunLink(boxes=["12:b4", "12:b5"], joiner=" ")]
    assert labels.box("12:b3").link == BoxLink(kind="pair", role="value", key=["12:b2"], value=["12:b3"])
    assert labels.box("12:b4").link.role == "run"
    assert labels.box("12:b1").link is None


def test_a_link_ends_with_its_lifetimes():
    a10 = record_a10()
    a10.links.append(RunLink(boxes=["b3", "b4"], joiner=""))
    labels = _labels([a10, record_a11()])
    assert len(labels.frame(10).links) == 2
    # L4 has no box on frame 11, so the run has ended, and A11's run over 11:b4 is accepted all the same
    assert labels.frame(11).links == [PairLink(key=["11:b2"], value=["11:b3"]), RunLink(boxes=["11:b4", "11:b5"], joiner=" ")]
    assert labels.relinked == 1


def test_screen_level_labels():
    labels = _labels([record_a10(), record_a11()])
    f10, f12 = labels.frame(10), labels.frame(12)
    assert (f10.description, f10.description_frame, [m.text for m in f10.missed]) == ("d10", 10, ["Networking"])
    assert [c.app for c in f10.containers] == ["Browser", "PowerShell"]
    assert (f12.description, f12.description_frame, f12.missed) == ("d11", 11, [])
    assert [c.app for c in f12.containers] == ["PowerShell", "Browser"]  # A11's own list
    assert labels.frame(9) == FrameLabel()


def test_failed_record_is_not_a_source():
    failed = Annotation(frame=11, targets=["b1", "b5"], model="fake-model", prompt_version="annotate-v1", error="refusal")
    labels = _labels([record_a10(), failed])
    assert labels.box("11:b5") is None and labels.box("12:b5") is None
    assert labels.box("11:b2").source == "10:b1"
    for n in (11, 12):
        assert (labels.frame(n).description, labels.frame(n).description_frame) == ("d10", 10)
    assert labels.frame(11).links == [PairLink(key=["11:b2"], value=["11:b3"])]


def test_every_frame_records_do_not_pile_up():
    a11f = Annotation(frame=11, targets=["b1", "b2", "b3", "b4", "b5"],
                      containers=[Container(id="c1", kind="window", app="Browser", name="Azure portal"),
                                  Container(id="c2", kind="window", app="PowerShell", name="PowerShell 7")],
                      assign=[Assign(box=b, container=c) for b, c in (("b1", "c1"), ("b2", "c1"), ("b3", "c1"), ("b4", "c2"), ("b5", "c2"))],
                      texts=[], description="d11", model="fake-model", prompt_version="annotate-v1")
    labels = _labels([record_a10(), a11f])
    assert labels.box("11:b2").source == "11:b2"
    assert labels.frame(11).links == [] and labels.relinked == 0


def test_agreement():
    assert agreement("区 Overview", "Overview") and agreement("Overview >", "Overview") and agreement("ab Overview", "Overview")
    assert not agreement("abc Overview", "Overview")
    assert not agreement("az configure", "azconfigure")
    assert agreement("PS  C:\\> az", "PS C:\\> az") and agreement("“x”", '"x"')


def test_non_text_and_group_only():
    icon = record_a10()
    icon.texts[0] = TextReading(box="b1", text="")
    label = _labels([icon]).box("10:b1")
    assert (label.vlm, label.non_text, label.agree) == ("", True, None)
    group = record_a10()
    group.texts = None
    label = _labels([group]).box("10:b1")
    assert (label.vlm, label.agree, label.non_text) == (None, None, False)


def test_without_lifetimes_nothing_is_carried():
    _, frames, _, _ = fixture_t()
    labels = build_labels([record_a10()], frames, [])
    assert labels.box("11:b2") is None and labels.box("10:b1").source == "10:b1"


def test_load_labels(tmp_path: Path):
    frames, boxes, changes, lifetimes = fixture_t()
    run = write_run(tmp_path, frames, boxes, changes, lifetimes)
    assert run.load_labels() is None
    write_jsonl(run.annotations, [record_a10(), record_a11()])
    labels = run.load_labels()
    assert labels.box("12:b5").source == "11:b5"
    with pytest.raises(KeyError):
        labels.box("99:b1")
