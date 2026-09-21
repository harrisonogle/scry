from pathlib import Path

import pytest
from minirun import mini_run

from scry.changetext import box_label, render_change, render_change_line, text_of
from scry.schemas import BoxChange, BoxText, Change, PixelStats, Revert


def _load(tmp_path: Path, labels: bool):
    run = mini_run(tmp_path, labels=labels)
    return {c.id: c for c in run.load_changes()}, {fb.frame: fb for fb in run.load_boxes()}, run.load_labels()


def _bt(ref: str, text: str) -> BoxText:
    return BoxText(box=ref, text=text)


def _t5() -> Change:
    return Change(id="T5", from_frame=20, to_frame=21, t=(50.0, 52.5), kind="unsettled",
                  pixels=PixelStats(changed_fraction=0.00023, components=2, textless=1, textless_area=40, touched_share=0.01, rect_only=0),
                  records=[BoxChange(kind="truncated", rect=(10, 50, 230, 68), before=_bt("20:b2", "PS> git status"),
                                     after=_bt("21:b2", "PS> git"), char_diff=[["=", "PS> git"], ["-", " status"]],
                                     continues="T4/0", in_churn=True),
                           BoxChange(kind="removed", rect=(305, 101, 375, 119), before=_bt("20:b7", "Cloud Shell"), after=None)],
                  moved=[("20:b3", "21:b3"), ("20:b4", "21:b4")], same_place=1, reverts=Revert(of="T4", share=0.9312, hold_s=3.4))


def _pair(kind: str, n: int, after: str) -> BoxChange:
    return BoxChange(kind=kind, rect=(0, 0, 1, 1), before=_bt(f"1:b{n}", "x"), after=_bt(f"2:b{n}", after))


def _change(records: list[BoxChange]) -> Change:
    return Change(id="T9", from_frame=1, to_frame=2, t=(1.0, 2.0), kind="single", pixels=None, records=records)


def test_render_keystroke_with_labels(tmp_path: Path):
    changes, boxes, labels = _load(tmp_path, True)
    text, ids = render_change(changes["T1"], boxes, labels)
    assert text == ('Transition T1: frame 10 → frame 11, t=24.00–24.40s.\n'
                    'Pixels changed: 0.20% of the screen; changed areas: 1.\n'
                    'Text changes:\n'
                    '[11:b3, 10:b3] Windows Terminal window: "C:\\src> git" → appended " status"; now "C:\\src> git status"\n'
                    '    model reads 11:b3: "C:\\src> git st"')
    assert ids == ["11:b3", "10:b3"]


def test_render_value_change_names_its_pair(tmp_path: Path):
    changes, boxes, labels = _load(tmp_path, True)
    lines = render_change(changes["T3"], boxes, labels)[0].split("\n")
    assert lines[2] == "Text changes:"
    assert lines[3] == ('[13:b2, 12:b2] Azure Portal window, Essentials, value of "Status": '
                        'at this place "Creating" was replaced by "Succeeded"')


def test_render_without_labels(tmp_path: Path):
    changes, boxes, _ = _load(tmp_path / "plain", False)
    text, _ = render_change(changes["T1"], boxes, None)
    assert text.split("\n")[3] == '[11:b3, 10:b3] "C:\\src> git" → appended " status"; now "C:\\src> git status"'
    assert "model reads" not in text
    text, ids = render_change(changes["T2"], boxes, None)
    assert text == ('Transition T2: frame 11 → frame 12, t=26.00–26.40s.\n'
                    'Pixels changed: 0.50% of the screen; changed areas: 2.\n'
                    'Text changes:\n'
                    '[12:b4] appeared "On branch main"\n'
                    '[12:b5] appeared "C:\\src>"')
    assert ids == ["12:b4", "12:b5"]
    changes, boxes, labels = _load(tmp_path / "labelled", True)
    assert render_change(changes["T2"], boxes, labels)[0].split("\n")[3] == '[12:b4] Windows Terminal window: appeared "On branch main"'


def test_render_every_annotation():
    text, ids = render_change(_t5(), {}, None)
    assert text == ('Transition T5: frame 20 → frame 21, t=50.00–52.50s.\n'
                    'Pixels changed: 0.02% of the screen; changed areas: 2.\n'
                    'Text changes:\n'
                    '[21:b2, 20:b2] "PS> git status" → truncated, removed " status"; now "PS> git"; continues T4 [area was animating]\n'
                    '[20:b7] removed "Cloud Shell"\n'
                    'Texts that only moved: 2.\n'
                    'Boxes with a visual change over unchanged text: 1.\n'
                    'Changed areas without text: 1.\n'
                    "Undoes 93% of T4's change after 3.4 s.\n"
                    'One of these frames was captured while the screen was still changing.')
    assert ids == ["21:b2", "20:b2", "20:b7"]
    assert "typed" not in text


def test_render_nothing_recorded():
    text, ids = render_change(_change([]), {}, None)
    assert text.split("\n")[1:] == ["Pixels: no comparison is available for this pair.",
                                    "No text change was recorded; look for a change that is not text."]
    assert ids == []


def test_render_reread():
    record = BoxChange(kind="reread", rect=(0, 0, 1, 1), before=_bt("1:b1", "A b"), after=_bt("2:b1", "Ab"))
    assert render_change(_change([record]), {}, None)[0].split("\n")[-1] == '[2:b1, 1:b1] "A b" re-read as "Ab" (same text)'


def test_box_label_parts(tmp_path: Path):
    _, boxes, labels = _load(tmp_path, True)
    assert box_label("13:b1", labels, boxes) == 'Azure Portal window, Essentials, label of "Succeeded"'
    assert box_label("11:b3", labels, boxes) == "Windows Terminal window"
    assert box_label("11:b3", None, boxes) == ""
    with pytest.raises(ValueError, match="99:b1"):
        text_of("99:b1", boxes)


def test_render_change_line(tmp_path: Path):
    changes, _, _ = _load(tmp_path, False)
    assert render_change_line(changes["T1"]) == 'T1 [f10→f11, 24.0–24.4s] appended "C:\\src> git status"'
    assert render_change_line(changes["T2"]) == "T2 [f11→f12, 26.0–26.4s] appeared 2"
    assert render_change_line(changes["T3"]) == 'T3 [f12→f13, 30.0–30.4s] changed "Succeeded"'
    assert render_change_line(_t5()) == 'T5 [f20→f21, 50.0–52.5s] truncated "PS> git"; removed 1; moved 2; undoes T4'
    five = render_change_line(_change([_pair("changed", n, f"text {n}") for n in range(1, 6)]))
    assert five == 'T9 [f1→f2, 1.0–2.0s] changed "text 1"; changed "text 2"; changed "text 3"; +2 more text changes'
    assert render_change_line(_change([_pair("appended", 1, "x" * 100)])) == 'T9 [f1→f2, 1.0–2.0s] appended "' + "x" * 79 + '…"'
    assert render_change_line(_change([])) == "T9 [f1→f2, 1.0–2.0s] no text change"
