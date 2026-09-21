"""Shared fixtures for the annotate tests (plan 2): hand-written frames, boxes, changes, lifetimes and records."""
from pathlib import Path

from PIL import Image

from scry.jsonl import write_jsonl
from scry.run import Run
from scry.schemas import (Annotation, Assign, Box, Change, Container, Frame, FrameBoxes, FrameTime, Lifetime, Missed,
                          PairLink, PixelStats, RunLink, TextReading, parse_box_ref)


def mk(id: str, x0: int, y0: int, x1: int, y1: int, text: str, in_churn: bool = False) -> Box:
    return Box(id=id, bbox=(x0, y0, x1, y1), text=text, conf=1.0, in_churn=in_churn)


def frame(n: int, w: int, h: int, settled: bool = True) -> Frame:
    return Frame(video_id="v", frame=n, t_change=float(n), t_settled=float(n), t_end=n + 1.0, settled=settled,
                 width=w, height=h, sha256=f"sha-{n}", png=f"frames/{n:05d}.png")


def fb(n: int, boxes: list[Box]) -> FrameBoxes:
    return FrameBoxes(frame=n, png=f"frames/{n:05d}.png", engine={"engine": "fake"}, boxes=boxes)


def write_run(tmp_path: Path, frames, frame_boxes, changes=(), lifetimes=()) -> Run:
    """A run directory written by hand: a solid grey PNG of each frame's size plus the four JSONL files."""
    run = Run(tmp_path)
    for f in frames:
        Image.new("RGB", (f.width, f.height), (128, 128, 128)).save(run.root / f.png)
    write_jsonl(run.frames, frames)
    write_jsonl(run.boxes, frame_boxes)
    write_jsonl(run.changes, changes)
    write_jsonl(run.lifetimes, lifetimes)
    return run


def change(id: str, a: int, b: int, components: int | None) -> Change:
    """components None = no pixel evidence."""
    pixels = None if components is None else PixelStats(changed_fraction=0.0, components=components, textless=0,
                                                         textless_area=0, touched_share=0.0, rect_only=0)
    return Change(id=id, from_frame=a, to_frame=b, t=(float(a), float(b)), kind="single", pixels=pixels)


def life(id: str, text: str, refs: list[str]) -> Lifetime:
    ns = [parse_box_ref(r)[0] for r in refs]
    return Lifetime(id=id, text=text, readings={text: ns}, unstable=False, sightings=len(refs),
                    first=FrameTime(frame=ns[0], t=float(ns[0])), last=FrameTime(frame=ns[-1], t=ns[-1] + 1.0), boxes=refs)


# ---------- Fixture E (every frame): frames 0 and 1, 128×64, the same two boxes ----------
def fixture_e() -> tuple[list[Frame], list[FrameBoxes]]:
    return ([frame(0, 128, 64), frame(1, 128, 64)],
            [fb(n, [mk("b1", 4, 4, 40, 20, "a"), mk("b2", 70, 4, 110, 20, "b")]) for n in (0, 1)])


# ---------- Fixture S (a screen): frame 7, 400×200 ----------
def fixture_s() -> tuple[Frame, FrameBoxes, list[Container]]:
    boxes = [mk("b1", 10, 10, 110, 26, "Browser tab"), mk("b2", 260, 10, 390, 26, "PowerShell"),
             mk("b3", 10, 40, 90, 56, "Resource group"), mk("b4", 120, 40, 240, 56, "RG1-Kode"),
             mk("b5", 260, 40, 390, 56, "PS C:\\> az login"), mk("b6", 150, 100, 230, 116, "Cloud Shell")]
    containers = [Container(id="c1", kind="window", app="Browser", name="Azure portal", rect=(0, 0, 250, 200)),
                  Container(id="c2", kind="window", app="PowerShell", name="PowerShell 7", rect=(250, 0, 400, 200)),
                  Container(id="c3", kind="popup", app="Browser", name="tooltip", owner="c1", rect=(140, 90, 300, 130))]
    return frame(7, 400, 200), fb(7, boxes), containers


# ---------- Fixture T (typing): frames 10, 11, 12, 400×200 ----------
def fixture_t() -> tuple[list[Frame], list[FrameBoxes], list[Change], list[Lifetime]]:
    def later(n: int) -> FrameBoxes:
        return fb(n, [mk("b1", 10, 10, 110, 26, "Banner"), mk("b2", 10, 40, 110, 56, "Resource group"),
                      mk("b3", 130, 40, 200, 56, "RG1"), mk("b4", 10, 80, 110, 96, "PowerShell 7"),
                      mk("b5", 10, 100, 200, 116, "PS C:\\> az login")])
    boxes = [fb(10, [mk("b1", 10, 40, 110, 56, "Resource group"), mk("b2", 130, 40, 200, 56, "RG1"),
                     mk("b3", 10, 80, 110, 96, "PowerShell 7"), mk("b4", 10, 100, 200, 116, "PS C:\\> az")]),
             later(11), later(12)]
    changes = [change("T1", 10, 11, 2), change("T2", 11, 12, 0)]
    lifetimes = [life("L1", "Resource group", ["10:b1", "11:b2", "12:b2"]), life("L2", "RG1", ["10:b2", "11:b3", "12:b3"]),
                 life("L3", "PowerShell 7", ["10:b3", "11:b4", "12:b4"]), life("L4", "PS C:\\> az", ["10:b4"]),
                 life("L5", "Banner", ["11:b1", "12:b1"]), life("L6", "PS C:\\> az login", ["11:b5", "12:b5"])]
    return [frame(n, 400, 200) for n in (10, 11, 12)], boxes, changes, lifetimes


def record_a10() -> Annotation:
    """Frame 10, every box a target."""
    return Annotation(
        frame=10, targets=["b1", "b2", "b3", "b4"],
        containers=[Container(id="c1", kind="window", app="Browser", name="Azure portal"),
                    Container(id="c2", kind="window", app="PowerShell", name="PowerShell 7")],
        assign=[Assign(box="b1", container="c1"), Assign(box="b2", container="c1"),
                Assign(box="b3", container="c2"), Assign(box="b4", container="c2")],
        links=[PairLink(key=["b1"], value=["b2"])],
        texts=[TextReading(box="b1", text="Resource group"), TextReading(box="b2", text="RG1"),
               TextReading(box="b3", text="PowerShell 7"), TextReading(box="b4", text="PS C:\\> a")],
        missed=[Missed(id="m1", text="Networking", container="c1")], description="d10",
        model="fake-model", prompt_version="annotate-v1")


def record_a11() -> Annotation:
    """Frame 11, targets b1 and b5: what an incremental call stores. Its container ids are its own (D3)."""
    return Annotation(
        frame=11, targets=["b1", "b5"],
        containers=[Container(id="c1", kind="window", app="PowerShell", name="PowerShell 7"),
                    Container(id="c2", kind="window", app="Browser", name="Azure portal")],
        assign=[Assign(box="b1", container="c2"), Assign(box="b5", container="c1")],
        links=[RunLink(boxes=["b4", "b5"], joiner=" "), PairLink(key=["b1"], value=["b2"])],
        texts=[TextReading(box="b1", text="Banner"), TextReading(box="b5", text="PS C:\\> az login")],
        description="d11", model="fake-model", prompt_version="annotate-v1")
