from pathlib import Path

import pydantic
import pytest

from scry.jsonl import read_jsonl, write_jsonl
from scry.run import Run
from scry.schemas import (Annotation, Box, BoxChange, BoxText, Change, Container, FrameBoxes, FrameTime, Interpretation,
                          Lifetime, Missed, PairLink, RawWord, RecordLink, Revert, RunLink, TextReading, box_ref,
                          link_members, link_refs, parse_box_ref)


def test_records_round_trip_unicode(tmp_path: Path):
    fb = FrameBoxes(frame=155, png="frames/00155.png", engine={"engine": "rapidocr", "version": "3.9.2"}, boxes=[
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
    old = fb.model_dump_json().replace('"frame":155,', '"frame":155,"seconds":1.25,')  # a file written before ledger L56
    assert '"seconds"' in old and FrameBoxes.model_validate_json(old) == fb


def test_box_ref_round_trip():
    assert box_ref(154, "b31") == "154:b31"
    assert parse_box_ref("154:b31") == (154, "b31")
    with pytest.raises(ValueError):
        parse_box_ref("b31")


def test_loaders_return_empty_lists_on_a_fresh_run(tmp_path: Path):
    run = Run(tmp_path / "r")
    assert run.load_frames() == [] and run.load_boxes() == [] and run.load_changes() == [] and run.load_lifetimes() == []
    assert run.load_annotations() == []


# spec §5's example record, verbatim
SPEC_EXAMPLE = r"""
{"frame": 155, "targets": ["b33"],
 "containers": [{"id": "c2", "kind": "window", "app": "PowerShell", "name": "Administrator: PowerShell 7-preview (x64)",
                 "owner": null, "covers": ["c1"], "rect": null}],
 "assign": [{"box": "b33", "container": "c2", "pane": null}],
 "links": [{"kind": "pair", "key": ["b28"], "value": ["b29"]},
           {"kind": "run", "boxes": ["b61", "b62"], "joiner": ""},
           {"kind": "record", "members": [["b70"], ["b71"], ["b72"]], "header": ["b64", "b65", "b66"]}],
 "texts": [{"box": "b33", "text": "PS C:\\Users\\msadmin> a login"}],
 "missed": [{"id": "m1", "text": "Networking", "container": "c1"}], "unassigned": [],
 "description": "The Overview item is highlighted in the left navigation; the Properties tab is selected; …",
 "repairs": 0, "model": "claude-opus-5", "prompt_version": "annotate-v1", "usage": {}, "error": null}
"""


def test_spec_example_parses():
    rec = Annotation.model_validate_json(" ".join(line.strip() for line in SPEC_EXAMPLE.strip().splitlines()))
    assert rec.targets == ["b33"]
    assert rec.containers[0].covers == ["c1"] and rec.containers[0].rect is None
    assert [l.kind for l in rec.links] == ["pair", "run", "record"]
    assert rec.links[1].joiner == ""
    assert rec.links[2].header == ["b64", "b65", "b66"]
    assert rec.missed[0].id == "m1"
    assert rec.repair_counts == {}


def test_annotation_round_trip_unicode(tmp_path: Path):
    a = Annotation(frame=1, targets=["b1", "b2"],
                   containers=[Container(id="c1", kind="window", app="x", name='He said "hi" — 区')],
                   links=[RunLink(boxes=["b1", "b2"], joiner="")],
                   texts=[TextReading(box="b1", text="PS C:\\Users\\msadmin> az login")],
                   missed=[Missed(id="m1", text="two\nlines")], description="d", model="m", prompt_version="annotate-v1")
    b = Annotation(frame=2, targets=[], texts=None, model="m", prompt_version="annotate-v1")
    write_jsonl(tmp_path / "annotations.jsonl", [a, b])
    assert read_jsonl(tmp_path / "annotations.jsonl", Annotation) == [a, b]
    first = (tmp_path / "annotations.jsonl").read_text(encoding="utf-8").splitlines()[0]
    assert '"kind":"run"' in first and '"key"' not in first


def test_link_members_and_refs():
    rec = RecordLink(members=[["b70"], ["b71", "b73"], ["b72"]], header=["b64"])
    assert link_members(rec) == ["b70", "b71", "b73", "b72"]
    assert link_refs(rec) == ["b70", "b71", "b73", "b72", "b64"]
    assert link_members(PairLink(key=["b1"], value=["b2", "b3"])) == ["b1", "b2", "b3"]


def test_interpretation_round_trip(tmp_path: Path):
    rec = Interpretation(id="T2", action="a", result="r", description="", confidence=0.9, entered_text="git status",
                         submitted="yes", citations=["12:b4"], invalid_citations=2, usage={"input_tokens": 1})
    write_jsonl(tmp_path / "interpretations.jsonl", [rec])
    assert read_jsonl(tmp_path / "interpretations.jsonl", Interpretation) == [rec]
    with pytest.raises(pydantic.ValidationError):
        Interpretation(id="T9", submitted="maybe")
