"""Fixture M, the mini run (plan 3): invented content, four emitted frames of a 400×200 screen. A portal pane whose
`Status` value changes, and a terminal where `git status` is entered with a shell suggestion showing, then submitted.
Every record is written by hand in the committed shapes; the pixel statistics are only rendered, never derived."""
import json
from pathlib import Path

from PIL import Image

from scry.jsonl import write_jsonl
from scry.run import Run
from scry.schemas import (Box, BoxChange, BoxText, Change, Frame, FrameBoxes, FrameTime, Interpretation, Lifetime,
                          ModelBoundaries, ModelElaboration, PixelStats, SegmentStart)

TIMES = {10: (20.0, 20.4, 24.0), 11: (24.0, 24.4, 26.0), 12: (26.0, 26.4, 30.0), 13: (30.0, 30.4, 35.0)}
PROMPT = "C:\\src>"
GIT = "C:\\src> git"
GIT_STATUS = "C:\\src> git status"

_B1 = ("b1", "Status", (10, 10, 70, 28))
_B3 = ("b3", GIT_STATUS, (10, 100, 190, 118))
_B5 = ("b5", PROMPT, (10, 140, 80, 158))
BOXES = {
    10: [_B1, ("b2", "Creating", (200, 10, 280, 28)), ("b3", GIT, (10, 100, 120, 118))],
    11: [_B1, ("b2", "Creating", (200, 10, 280, 28)), _B3],
    12: [_B1, ("b2", "Creating", (200, 10, 280, 28)), _B3, ("b4", "On branch main", (10, 120, 150, 138)), _B5],
    13: [_B1, ("b2", "Succeeded", (200, 10, 290, 28)), _B3, ("b4", "On branch maln", (10, 120, 150, 138)), _B5],
}
MODEL_READS = {"11:b3": "C:\\src> git st", "13:b4": "On branch main"}  # where the second reader differs from OCR
DESCRIPTIONS = {10: "The Overview item is highlighted in the left navigation.",
                11: "The Overview item is highlighted in the left navigation.",
                12: "The terminal shows new output.", 13: "The Status value now reads Succeeded."}


def _png(n: int) -> str:
    return f"frames/000{n}.png"


def _frames() -> list[Frame]:
    return [Frame(video_id="v", frame=n, t_change=tc, t_settled=ts, t_end=te, settled=True, width=400, height=200,
                  sha256=f"sha{n}", png=_png(n)) for n, (tc, ts, te) in TIMES.items()]


def _boxes() -> list[FrameBoxes]:
    return [FrameBoxes(frame=n, png=_png(n), engine={}, boxes=[Box(id=i, bbox=bbox, text=text, conf=1.0) for i, text, bbox in bs])
            for n, bs in BOXES.items()]


def _pixels(changed_fraction: float, components: int, touched_share: float) -> PixelStats:
    return PixelStats(changed_fraction=changed_fraction, components=components, textless=0, textless_area=0,
                      touched_share=touched_share, rect_only=0)


def _bt(ref: str, text: str) -> BoxText:
    return BoxText(box=ref, text=text)


def _changes() -> list[Change]:
    return [
        Change(id="T1", from_frame=10, to_frame=11, t=(24.0, 24.4), kind="single", pixels=_pixels(0.002, 1, 0.3333), unchanged=2,
               records=[BoxChange(kind="appended", rect=(10, 100, 190, 118), before=_bt("10:b3", GIT), after=_bt("11:b3", GIT_STATUS),
                                  char_diff=[["=", GIT], ["+", " status"]])]),
        Change(id="T2", from_frame=11, to_frame=12, t=(26.0, 26.4), kind="single", pixels=_pixels(0.005, 2, 0.25), unchanged=3,
               records=[BoxChange(kind="appeared", rect=(10, 120, 150, 138), before=None, after=_bt("12:b4", "On branch main")),
                        BoxChange(kind="appeared", rect=(10, 140, 80, 158), before=None, after=_bt("12:b5", PROMPT))]),
        Change(id="T3", from_frame=12, to_frame=13, t=(30.0, 30.4), kind="single", pixels=_pixels(0.001, 1, 0.2), unchanged=4,
               variants=1,
               records=[BoxChange(kind="changed", rect=(200, 10, 290, 28), before=_bt("12:b2", "Creating"),
                                  after=_bt("13:b2", "Succeeded"), char_diff=[["-", "Creating"], ["+", "Succeeded"]])]),
    ]


def _life(id: str, readings: dict[str, list[int]], first: tuple[int, float], last: tuple[int, float], box: str,
          unstable: bool = False) -> Lifetime:
    frames = sorted(n for ns in readings.values() for n in ns)
    return Lifetime(id=id, text=next(iter(readings)), readings=readings, unstable=unstable, sightings=len(frames),
                    first=FrameTime(frame=first[0], t=first[1]), last=FrameTime(frame=last[0], t=last[1]),
                    boxes=[f"{n}:{box}" for n in frames])


def _lifetimes() -> list[Lifetime]:
    return [
        _life("L1", {"Status": [10, 11, 12, 13]}, (10, 20.4), (13, 35.0), "b1"),
        _life("L2", {"Creating": [10, 11, 12]}, (10, 20.4), (12, 30.0), "b2"),
        _life("L3", {GIT: [10]}, (10, 20.4), (10, 24.0), "b3"),
        _life("L4", {GIT_STATUS: [11, 12, 13]}, (11, 24.4), (13, 35.0), "b3"),
        _life("L5", {"On branch main": [12], "On branch maln": [13]}, (12, 26.4), (13, 35.0), "b4", unstable=True),
        _life("L6", {PROMPT: [12, 13]}, (12, 26.4), (13, 35.0), "b5"),
        _life("L7", {"Succeeded": [13]}, (13, 30.4), (13, 35.0), "b2"),
    ]


def _annotation(n: int) -> dict:
    """One hand-written annotations.jsonl line with every required field."""
    ids = [i for i, _, _ in BOXES[n]]
    window = {"owner": None, "rect": None}
    return {
        "frame": n, "targets": ids,
        "containers": [{"id": "c1", "kind": "window", "app": "Azure Portal", "name": "Resource overview", "covers": []} | window,
                       {"id": "c2", "kind": "window", "app": "Windows Terminal", "name": "PowerShell", "covers": ["c1"]} | window],
        "assign": [{"box": i, "container": "c1", "pane": "Essentials"} if i in ("b1", "b2") else
                   {"box": i, "container": "c2", "pane": None} for i in ids],
        "links": [{"kind": "pair", "key": ["b1"], "value": ["b2"]}],
        "texts": [{"box": i, "text": MODEL_READS.get(f"{n}:{i}", text)} for i, text, _ in BOXES[n]],
        "missed": [{"id": "m1", "text": "Refresh", "container": "c1"}] if n == 13 else [],
        "unassigned": [], "description": DESCRIPTIONS[n], "repairs": 0, "usage": {}, "error": None,
        "model": "fake-model", "prompt_version": "annotate-v1",
    }


def write_annotations(run: Run) -> None:
    run.annotations.write_text("".join(json.dumps(_annotation(n)) + "\n" for n in BOXES))


def mini_run(tmp_path: Path, labels: bool = False) -> Run:
    run = Run(tmp_path)
    for n in TIMES:
        img = Image.new("RGB", (400, 200), "white")
        k = 5 * (n - 10)
        img.paste((0, 0, 0), (100 + k, 150, 120 + k, 170))
        img.save(run.root / _png(n))
    run.manifest_update(video="v.mp4", video_id="v")
    write_jsonl(run.frames, _frames())
    write_jsonl(run.boxes, _boxes())
    write_jsonl(run.changes, _changes())
    write_jsonl(run.lifetimes, _lifetimes())
    if labels:
        write_annotations(run)
    return run


def mini_interpretations(run: Run) -> None:
    common = dict(description="", model="fake-model", prompt_version="interpret-v1+scaled0.5", usage={}, invalid_citations=0)
    write_jsonl(run.interpretations, [
        Interpretation(id="T1", action='The user typed " st" in the terminal; the shell offers "atus" as a completion.',
                       result="The command line now reads git st with a greyed suggestion.", confidence=0.8,
                       entered_text="git st", submitted="no", citations=["11:b3"], **common),
        Interpretation(id="T2", action="The user pressed Enter.", result='Git printed "On branch main" and a new prompt appeared.',
                       confidence=0.9, entered_text="git status", submitted="yes", citations=["12:b4", "12:b5"], **common),
        Interpretation(id="T3", action="No user action is evident; the portal refreshed.",
                       result="The Status value changed from Creating to Succeeded.", confidence=0.7, entered_text=None,
                       submitted="no", citations=["13:b2"], **common),
    ])


def call_text(kw: dict) -> str:
    """The text blocks of a recorded provider call, joined with newlines."""
    return "\n".join(b["text"] for b in kw["blocks"] if b["type"] == "text")


def summarize_answers(kw: dict):
    """An `AnswerProvider` answer for `summarize` over Fixture M: two steps, one section, the video. Chosen by the call's
    stage and, for the two step elaborations (they run concurrently), by their `Segment S<n>` line."""
    stage, text = kw["stage"], call_text(kw)
    if stage == "summarize-boundary-step":
        return ModelBoundaries(segments=[SegmentStart(start_id="T1", label="Run git status"),
                                         SegmentStart(start_id="T3", label="Watch the deployment")])
    if stage == "summarize-elaborate-step":
        if text.startswith("Segment S1\n"):
            return ModelElaboration(label="Run git status", description="Type `git status` [T1] and run it [T2].", refs=["T1", "T2", "T9"])
        return ModelElaboration(label="", description="The status becomes Succeeded [T3].", refs=["T3"])
    if stage == "summarize-boundary-section":
        return ModelBoundaries(segments=[SegmentStart(start_id="S1", label="Everything")])
    if stage == "summarize-elaborate-section":
        return ModelElaboration(label="Everything", description="All of it [S1] [S2].", refs=["S1", "S2"])
    assert stage == "summarize-elaborate-video", stage
    return ModelElaboration(label="A short demo", description="One section [C1].", refs=["C1"])
