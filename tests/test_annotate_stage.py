import base64
import io
import re
from pathlib import Path

import pytest
from annotate_fixtures import fb, fixture_e, fixture_t, record_a10, record_a11, write_run
from fakes import AnswerProvider, call_frame
from PIL import Image

from scry.annotate import run_annotate
from scry.annotate.output import output_model
from scry.annotate.stage import mark_match
from scry.config import Config
from scry.prompts.annotate import system_prompt
from scry.schemas import Annotation, PairLink, RunLink, TextReading


def standard(kw: dict, second: str = "b2", empty: bool = False):
    """The standard answer for the frame a call is about, built with the call's own answer class."""
    model = kw["output_model"]
    data = {"containers": [{"id": "c1", "kind": "window", "app": "x", "name": "w", "owner": None, "covers": []}],
            "assign": [{"box": "b1", "container": "c1"}, {"box": second, "container": "c1"}], "unassigned": [], "runs": [],
            "pairs": [{"key": ["b1"], "value": ["b2"]}], "records": [], "description": f"d{call_frame(kw)}"}
    if empty:
        data |= {"containers": [], "assign": [], "pairs": []}
    if "texts" in model.model_fields:
        data |= {"texts": [] if empty else [{"box": "b1", "text": "a"}, {"box": "b2", "text": "B"}], "missed": []}
    return model.model_validate(data)


def answer_from(record: Annotation, kw: dict):
    """A stored record's content as the model's answer, built with the call's own answer class."""
    links = {kind: [l.model_dump(exclude={"kind"}) for l in record.links if l.kind == kind] for kind in ("run", "pair", "record")}
    return kw["output_model"].model_validate({
        "containers": [c.model_dump(include={"id", "kind", "app", "name", "owner", "covers"}) for c in record.containers],
        "assign": [a.model_dump(include={"box", "container"}) for a in record.assign], "unassigned": record.unassigned,
        "runs": links["run"], "pairs": links["pair"], "records": links["record"],
        "texts": [t.model_dump() for t in record.texts], "missed": [m.model_dump(include={"text", "container"}) for m in record.missed],
        "description": record.description})


def _run(tmp_path: Path):
    frames, boxes = fixture_e()
    return write_run(tmp_path, frames, boxes)


def _cfg(**annotate) -> Config:
    """Every-frame unless a test says otherwise: the config's own default is incremental (ledger L59)."""
    return Config.model_validate({"annotate": {"mode": "every_frame"} | annotate})


def _entry(run) -> dict:
    return run.manifest_read()["stages"]["annotate"]


def _image_sizes(kw: dict) -> list[tuple[int, int]]:
    return [Image.open(io.BytesIO(base64.standard_b64decode(b["source"]["data"]))).size for b in kw["blocks"] if b["type"] == "image"]


def test_every_frame_arm_a_end_to_end(tmp_path: Path):
    run, provider = _run(tmp_path), AnswerProvider(standard)
    run_annotate(run, _cfg(), provider)
    records = run.load_annotations()
    assert [r.frame for r in records] == [0, 1]
    r0 = records[0]
    assert r0.targets == ["b1", "b2"] and len(r0.containers) == 1 and len(r0.assign) == 2
    assert r0.links == [PairLink(key=["b1"], value=["b2"])]
    assert r0.texts == [TextReading(box="b1", text="a"), TextReading(box="b2", text="B")]
    assert (r0.description, r0.repairs, r0.repair_counts, r0.label_clashes) == ("d0", 0, {}, 0)
    assert (r0.model, r0.prompt_version, r0.error) == ("fake-model", "annotate-v4", None)
    for kw in provider.calls:
        assert kw["stage"] == "annotate" and kw["effort"] == "low" and kw["system"] == system_prompt()
        assert kw["output_model"] is output_model("A", True)
        assert _image_sizes(kw) == [(128, 64), (128, 64)]
    for n in (0, 1):
        assert Image.open(run.overlays_dir / f"{n:05d}.png").size == (128, 64)
    m = _entry(run)
    assert (m["mode"], m["reference"], m["arm"]) == ("every_frame", "ids", "A")
    assert (m["frames"], m["calls"], m["boxes"], m["targets"]) == (2, 2, 4, 4)
    assert (m["errors"], m["transient_errors"], m["usage_lost"]) == (0, 0, 0)
    assert m["mark_match"] == {"hits": 2, "total": 4}  # "a" against "a" is 1.0; "B" against "b" is 0.0
    assert m["usage"] == {"input_tokens": 200, "output_tokens": 40, "cache_read_input_tokens": 2000, "cache_creation_input_tokens": 800}
    assert (m["cost_usd"], m["cost_per_frame_usd"], m["cost_per_call_usd"]) == (0.008, 0.004, 0.004)
    assert "cost_usd_batch" not in m  # one cost figure per stage (ledger L52)


def test_group_only(tmp_path: Path):
    run, provider = _run(tmp_path), AnswerProvider(standard)
    run_annotate(run, _cfg(transcribe=False), provider)
    kw = provider.calls[0]
    assert kw["system"] == system_prompt(transcribe=False) and kw["output_model"] is output_model("A", False)
    assert kw["prompt_version"] == "annotate-v4+grouponly"
    record = run.load_annotations()[0]
    assert record.texts is None and record.missed == []
    assert _entry(run)["mark_match"] is None


def test_repairs_are_counted_not_fatal(tmp_path: Path):
    run = _run(tmp_path)
    run_annotate(run, _cfg(), AnswerProvider(lambda kw: standard(kw, second="b9")))
    for record in run.load_annotations():
        assert record.unassigned == ["b2"] and record.repairs == 2
        assert record.repair_counts == {"unknown_box": 1, "unplaced": 1}
        assert record.links == [PairLink(key=["b1"], value=["b2"])]  # the slip in assign does not cost the link
    assert _entry(run)["repairs"] == 4


def test_error_record_and_the_run_continues(tmp_path: Path):
    run = _run(tmp_path)
    run_annotate(run, _cfg(), AnswerProvider(lambda kw: "refusal" if call_frame(kw) == 1 else standard(kw)))
    whole, failed = run.load_annotations()
    assert (failed.error, failed.targets, failed.description, failed.texts, failed.links) == ("refusal", ["b1", "b2"], None, None, [])
    assert whole.error is None and whole.description == "d0"
    m = _entry(run)
    assert (m["errors"], m["transient_errors"], m["failed_targets"]) == (1, 0, 2)
    again = AnswerProvider(standard)
    run_annotate(run, _cfg(), again)
    assert again.calls == []  # a refusal is final


def test_transient_error_is_retried_on_the_next_run(tmp_path: Path):
    run, error = _run(tmp_path), "api: APIConnectionError: down"
    run_annotate(run, _cfg(), AnswerProvider(lambda kw: error if call_frame(kw) == 1 else standard(kw)))
    assert run.load_annotations()[1].error == error
    assert (_entry(run)["errors"], _entry(run)["transient_errors"]) == (1, 1)
    second = AnswerProvider(standard)
    run_annotate(run, _cfg(), second)
    assert len(second.calls) == 2  # this fake has no call cache; the real provider would pay for frame 1 only
    assert run.load_annotations()[1].error is None and run.load_annotations()[1].description == "d1"
    assert (_entry(run)["errors"], _entry(run)["transient_errors"]) == (0, 0)
    third = AnswerProvider(standard)
    run_annotate(run, _cfg(), third)
    assert third.calls == []


def test_frame_without_boxes_still_gets_a_call(tmp_path: Path):
    frames, boxes = fixture_e()
    run = write_run(tmp_path, frames, [boxes[0], fb(1, [])])
    provider = AnswerProvider(lambda kw: standard(kw, empty=call_frame(kw) == 1))
    run_annotate(run, _cfg(), provider)
    assert "Boxes: none." in [b["text"] for b in provider.calls[1]["blocks"] if b["type"] == "text"]
    record = run.load_annotations()[1]
    assert record.targets == [] and record.description == "d1"


def test_missing_png_is_an_error_record_without_a_call(tmp_path: Path):
    run, provider = _run(tmp_path), AnswerProvider(standard)
    (run.root / "frames" / "00001.png").unlink()
    run_annotate(run, _cfg(), provider)
    assert len(provider.calls) == 1
    assert run.load_annotations()[1].error == "missing_png"


def test_scale_reaches_the_version_and_both_images(tmp_path: Path):
    run, provider = _run(tmp_path), AnswerProvider(standard)
    run_annotate(run, _cfg(scale=0.5), provider)
    assert provider.calls[0]["prompt_version"] == "annotate-v4+s0.5"
    assert _image_sizes(provider.calls[0]) == [(64, 32), (64, 32)]


def test_skips_when_up_to_date_and_reruns_on_config_change(tmp_path: Path):
    run = _run(tmp_path)
    run_annotate(run, _cfg(), AnswerProvider(standard))
    again = AnswerProvider(standard)
    run_annotate(run, _cfg(), again)
    assert again.calls == []
    run_annotate(run, _cfg(transcribe=False), again)
    assert len(again.calls) == 2


def test_mode_off_removes_the_file_and_calls_nothing(tmp_path: Path):
    run = _run(tmp_path)
    run_annotate(run, _cfg(), AnswerProvider(standard))
    off = AnswerProvider(standard)
    run_annotate(run, _cfg(mode="off"), off)
    assert not run.annotations.exists() and off.calls == []
    assert _entry(run)["skipped"] is True and _entry(run)["usage"]["input_tokens"] == 0


def test_writes_only_its_own_files(tmp_path: Path):
    run = _run(tmp_path)
    before = (run.frames.read_bytes(), run.boxes.read_bytes())
    run_annotate(run, _cfg(), AnswerProvider(standard))
    assert (run.frames.read_bytes(), run.boxes.read_bytes()) == before


def _texts(kw: dict) -> list[str]:
    return [b["text"] for b in kw["blocks"] if b["type"] == "text"]


def test_incremental_run(tmp_path: Path):
    stored = {10: record_a10(), 11: record_a11()}

    def answer(kw: dict):
        return answer_from(stored.get(call_frame(kw), stored[11]), kw)

    run, provider = write_run(tmp_path / "incremental", *fixture_t()), AnswerProvider(answer)
    run_annotate(run, _cfg(mode="incremental"), provider)
    calls = {call_frame(kw): kw for kw in provider.calls}
    assert sorted(calls) == [10, 11]  # no changed pixel into frame 12: no call
    for kw in calls.values():  # the every-frame call: one prompt, one schema, one version
        assert kw["system"] == system_prompt() and kw["output_model"] is output_model("A", True)
        assert kw["prompt_version"] == "annotate-v4" and len(_image_sizes(kw)) == 2
    assert "Targets: all boxes." in _texts(calls[10]) and "Targets: b1, b5." in _texts(calls[11])
    # the sentence about the description is in the shared system prompt, not in any user turn (ledger L59)
    assert "never mention" in system_prompt() and not any("never mention" in t for n in (10, 11) for t in _texts(calls[n]))
    records = run.load_annotations()
    assert [r.frame for r in records] == [10, 11]
    for got in records:
        want = stored[got.frame]
        for field in ("targets", "containers", "assign", "links", "texts", "missed", "description", "repairs"):
            assert getattr(got, field) == getattr(want, field), (got.frame, field)  # repairs 0: repair cannot know that b2 is linked
    m = _entry(run)
    assert (m["mode"], m["calls"], m["frames"], m["skipped_frames"], m["targets"]) == ("incremental", 2, 3, 1, 6)
    labels = run.load_labels()
    assert labels.frame(12).links == [PairLink(key=["12:b2"], value=["12:b3"]), RunLink(boxes=["12:b4", "12:b5"], joiner=" ")]
    assert labels.relinked == 1
    # cache-key behaviour: the call for a first frame is the every-frame call, so a paid every-frame answer is reused
    every = AnswerProvider(answer)
    run_annotate(write_run(tmp_path / "every_frame", *fixture_t()), _cfg(), every)
    first = next(kw for kw in every.calls if call_frame(kw) == 10)
    assert _texts(first) == _texts(calls[10])
    assert (first["prompt_version"], first["input_hashes"]) == (calls[10]["prompt_version"], calls[10]["input_hashes"])


def test_incremental_needs_track(tmp_path: Path):
    run = write_run(tmp_path, *fixture_t())
    run.lifetimes.unlink()
    with pytest.raises(ValueError, match="scry track"):
        run_annotate(run, _cfg(mode="incremental"), AnswerProvider(standard))


def test_mark_match():
    _, frames, _, _ = fixture_t()
    assert mark_match([record_a10(), record_a11()], frames) == (6, 6)  # "PS C:\> a" against "PS C:\> az" is 0.9
    wrong = record_a11()
    wrong.texts[0] = TextReading(box="b1", text="PowerShell 7")
    assert mark_match([record_a10(), wrong], frames) == (5, 6)
    nothing = [Annotation(frame=12, targets=["b1"], texts=[TextReading(box="b1", text="")], model="m", prompt_version="v"),
               Annotation(frame=12, targets=["b1"], texts=None, model="m", prompt_version="v")]
    assert mark_match(nothing, frames) == (0, 0)


# ---------- reference = "coords": one image, rectangles out and back; downstream sees ids ----------
def _rect(box) -> list[int]:
    return list(box.bbox)


def coords_answer_from(record: Annotation, boxes, kw: dict):
    """A stored record's content as a coords answer: every box id replaced by that box's rectangle on its frame."""
    at = {b.id: _rect(b) for b in boxes[record.frame].boxes}
    links = {"run": [], "pair": [], "record": []}
    for l in record.links:
        if l.kind == "run":
            links["run"].append({"boxes": [at[b] for b in l.boxes], "joiner": l.joiner})
        elif l.kind == "pair":
            links["pair"].append({"key": [at[b] for b in l.key], "value": [at[b] for b in l.value]})
        else:
            links["record"].append({"members": [[at[b] for b in cell] for cell in l.members], "header": [at[b] for b in l.header]})
    data = {"containers": [c.model_dump(include={"id", "kind", "app", "name", "owner", "covers"}) for c in record.containers],
            "assign": [{"rect": at[a.box], "container": a.container} for a in record.assign],
            "unassigned": [at[b] for b in record.unassigned], "runs": links["run"], "pairs": links["pair"], "records": links["record"],
            "description": record.description}
    if "texts" in kw["output_model"].model_fields:
        data |= {"texts": [{"rect": at[t.box], "text": t.text} for t in record.texts],
                 "missed": [m.model_dump(include={"text", "container"}) for m in record.missed]}
    return kw["output_model"].model_validate(data)


def test_coords_incremental_group_only_end_to_end(tmp_path: Path):
    frames, boxes, changes, lifetimes = fixture_t()
    by_frame = {fb.frame: fb for fb in boxes}
    stored = {10: record_a10(), 11: record_a11()}
    provider = AnswerProvider(lambda kw: coords_answer_from(stored[call_frame(kw)], by_frame, kw))
    run = write_run(tmp_path, frames, boxes, changes, lifetimes)
    run_annotate(run, _cfg(mode="incremental", transcribe=False, reference="coords"), provider)
    calls = {call_frame(kw): kw for kw in provider.calls}
    assert sorted(calls) == [10, 11]
    for kw in calls.values():
        assert kw["system"] == system_prompt(transcribe=False, reference="coords")
        assert kw["output_model"] is output_model("A", False, reference="coords")
        assert kw["prompt_version"] == "annotate-v4+coords+grouponly"
        assert _image_sizes(kw) == [(400, 200)] and kw["input_hashes"][1] == "-"
        assert not any(re.search(r"\bb\d+\b", t) for t in _texts(kw))
    assert "Targets: all boxes." in _texts(calls[10])
    assert "Targets: 10,10,110,26; 10,100,200,116." in _texts(calls[11])  # b1 and b5 of frame 11, by rectangle
    assert "Boxes, as x0,y0,x1,y1 in reading order: 10,10,110,26; 10,40,110,56; 130,40,200,56; 10,80,110,96; 10,100,200,116." in _texts(calls[11])
    assert not run.overlays_dir.exists() or not any(run.overlays_dir.iterdir())  # no overlay drawn
    records = run.load_annotations()
    assert [r.frame for r in records] == [10, 11]
    for got in records:  # the rectangles came back as today's ids: the record is the stored one, but for what group-only lacks
        want = stored[got.frame]
        for field in ("targets", "containers", "assign", "unassigned", "links", "description"):
            assert getattr(got, field) == getattr(want, field), (got.frame, field)
        assert got.texts is None and got.missed == [] and got.repairs == 0 and got.label_clashes == 0
    m = _entry(run)
    assert (m["mode"], m["reference"], m["transcribe"], m["prompt_version"]) == ("incremental", "coords", False, "annotate-v4+coords+grouponly")
    assert (m["calls"], m["frames"], m["targets"], m["label_clashes"], m["mark_match"]) == (2, 3, 6, 0, None)
    labels = run.load_labels()  # the join reads ids and knows nothing of the reference mode
    assert labels.frame(12).links == [PairLink(key=["12:b2"], value=["12:b3"]), RunLink(boxes=["12:b4", "12:b5"], joiner=" ")]
    assert labels.relinked == 1


def test_coords_every_frame_transcribing_at_half_scale(tmp_path: Path):
    frames, boxes = fixture_e()
    by_frame = {fb.frame: fb for fb in boxes}

    def answer(kw: dict):
        at = {b.id: _rect(b) for b in by_frame[call_frame(kw)].boxes}
        return kw["output_model"].model_validate({
            "containers": [{"id": "c1", "kind": "window", "app": "x", "name": "w", "owner": None, "covers": []}],
            "assign": [{"rect": at["b1"], "container": "c1"}, {"rect": [70, 40, 110, 56], "container": "c1"}], "unassigned": [],
            "runs": [], "pairs": [{"key": [at["b1"]], "value": [[72, 6, 108, 18]]}], "records": [],
            "texts": [{"rect": at["b1"], "text": "a"}, {"rect": at["b2"], "text": "B"}], "missed": [],
            "description": f"d{call_frame(kw)}"})

    run, provider = write_run(tmp_path, frames, boxes), AnswerProvider(answer)
    run_annotate(run, _cfg(scale=0.5, reference="coords"), provider)
    kw = provider.calls[0]
    assert kw["prompt_version"] == "annotate-v4+coords+s0.5" and _image_sizes(kw) == [(64, 32)]
    assert kw["output_model"] is output_model("A", True, reference="coords") and kw["system"] == system_prompt(reference="coords")
    assert "Coordinates are pixels of the 128x64 frame: top-left origin, x1 and y1 exclusive. The image is scaled by 0.5; " \
           "every coordinate is in the unscaled 128x64 frame." in _texts(kw)
    r0 = run.load_annotations()[0]
    assert [(a.box, a.container) for a in r0.assign] == [("b1", "c1")] and r0.unassigned == ["b2"]
    assert r0.repair_counts == {"rect_unplaced": 1, "unplaced": 1} and r0.repairs == 2  # 70,40,110,56 is a box height below b2
    assert r0.links == [PairLink(key=["b1"], value=["b2"])]  # 72,6,108,18 overlaps b2: matched
    assert r0.texts == [TextReading(box="b1", text="a"), TextReading(box="b2", text="B")]
    assert (r0.description, r0.prompt_version, r0.label_clashes) == ("d0", "annotate-v4+coords+s0.5", 0)
    m = _entry(run)
    assert m["reference"] == "coords" and m["mark_match"] == {"hits": 2, "total": 4}
    assert m["repair_counts"] == {"rect_unplaced": 2, "unplaced": 2}
    assert not (run.overlays_dir.exists() and any(run.overlays_dir.iterdir()))
