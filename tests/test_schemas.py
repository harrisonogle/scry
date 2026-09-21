from pathlib import Path

import pytest

from scry.jsonl import read_jsonl, write_jsonl
from scry.run import Run
from scry.schemas import (Box, BoxChange, BoxText, Change, FrameBoxes, FrameTime, Lifetime, RawWord, Revert, box_ref,
                          parse_box_ref)


def test_records_round_trip_unicode(tmp_path: Path):
    fb = FrameBoxes(frame=155, png="frames/00155.png", engine={"engine": "rapidocr", "version": "3.9.2"}, seconds=1.25, boxes=[
        Box(id="b1", bbox=(24, 164, 48, 179), text="区", conf=0.41),
        Box(id="b2", bbox=(659, 352, 904, 371), text="PS C:\\Users\\msadmin> az login", conf=0.98,
            words=[RawWord(text="PS", bbox=(659, 352, 679, 371))])])
    change = Change(id="T9", from_frame=154, to_frame=155, t=(598.7, 620.7), kind="single", pixels=None,
                    records=[BoxChange(kind="appended", rect=(659, 350, 904, 373),
                                       before=BoxText(box="154:b31", text="PS C:\\Users\\msadmin>"),
                                       after=BoxText(box="155:b33", text="PS C:\\Users\\msadmin> az login"),
                                       char_diff=[["=", "PS C:\\Users\\msadmin>"], ["+", " az login"]], continues="T8/0"),
                             BoxChange(kind="appeared", rect=(24, 164, 48, 179), before=None, after=BoxText(box="155:b1", text="区"))],
                    moved=[("0:b4", "1:b3")], reverts=Revert(of="T8", share=0.8125, hold_s=2.8))
    life = Lifetime(id="L1", text="A b", readings={"A b": [0, 2], "Ab": [1]}, unstable=True, sightings=3,
                    first=FrameTime(frame=0, t=0.0), last=FrameTime(frame=2, t=9.0), boxes=["0:b1", "1:b1", "2:b1"])
    for name, rec, model in (("boxes.jsonl", fb, FrameBoxes), ("changes.jsonl", change, Change), ("lifetimes.jsonl", life, Lifetime)):
        write_jsonl(tmp_path / name, [rec])
        assert read_jsonl(tmp_path / name, model) == [rec]
    assert "区" in (tmp_path / "boxes.jsonl").read_text(encoding="utf-8")


def test_box_ref_round_trip():
    assert box_ref(154, "b31") == "154:b31"
    assert parse_box_ref("154:b31") == (154, "b31")
    with pytest.raises(ValueError):
        parse_box_ref("b31")


def test_loaders_return_empty_lists_on_a_fresh_run(tmp_path: Path):
    run = Run(tmp_path / "r")
    assert run.load_frames() == [] and run.load_boxes() == [] and run.load_changes() == [] and run.load_lifetimes() == []
