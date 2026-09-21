from scry.metrics import box_stability, fragmentation, incremental_projection, select, totals, touched_share_low_half
from scry.schemas import Box, BoxChange, BoxText, Change, FrameBoxes, FrameTime, Lifetime, PixelStats


def px(changed_fraction=0.01, touched_share=0.1, components=1) -> PixelStats:
    return PixelStats(changed_fraction=changed_fraction, components=components, textless=0, textless_area=0,
                      touched_share=touched_share, rect_only=0)


def change(n: int, a: int | None = None, b: int | None = None, pixels: PixelStats | None = None, **kw) -> Change:
    a = n - 1 if a is None else a
    return Change(id=f"T{n}", from_frame=a, to_frame=a + 1 if b is None else b, t=(0.0, 0.0), kind=kw.pop("kind", "single"),
                  pixels=pixels, **kw)


def rec(kind: str, after: str | None = "1:b1", before: str | None = "0:b1") -> BoxChange:
    if kind == "appeared":
        before = None
    if kind == "removed":
        after = None
    return BoxChange(kind=kind, rect=(0, 0, 1, 1), before=BoxText(box=before, text="x") if before else None,
                     after=BoxText(box=after, text="y") if after else None)


def life(n: int, text: str, boxes: list[str], unstable: bool = False) -> Lifetime:
    return Lifetime(id=f"L{n}", text=text, readings={text: [0]}, unstable=unstable, sightings=len(boxes),
                    first=FrameTime(frame=0, t=0.0), last=FrameTime(frame=0, t=1.0), boxes=boxes)


def test_box_stability():
    changes = [change(1, unchanged=98, variants=2, flicker_lost=["0:b9"]), change(2, unchanged=50)]
    assert box_stability(changes) == 0.9799  # 146 / 149
    assert box_stability([]) is None


def test_touched_share_low_half():
    changes = [change(1, pixels=px(0.001, 0.02)), change(2, pixels=px(0.2, 0.5)), change(3, pixels=px(0.0005, 0.01)),
               change(4, pixels=px(0.3, 0.9)), change(5, pixels=None)]
    assert touched_share_low_half(changes) == 0.015
    assert touched_share_low_half([change(1)]) is None


def test_fragmentation():
    lifetimes = [life(1, "a", ["0:b1"]), life(2, "a", ["1:b1", "2:b1", "3:b1"], unstable=True), life(3, "b", ["0:b2"])]
    assert fragmentation(lifetimes) == {"lifetimes": 3, "distinct_texts": 2, "per_text": 1.5, "unstable": 1, "single_sighting": 2,
                                        "top": [("a", 2), ("b", 1)]}
    assert fragmentation([])["per_text"] is None


def test_incremental_projection():
    def fb(frame: int, n: int) -> FrameBoxes:
        return FrameBoxes(frame=frame, png="", engine={}, boxes=[Box(id=f"b{i}", bbox=(0, 0, 1, 1), text="x", conf=1.0) for i in range(1, n + 1)])

    boxes = [fb(0, 100), fb(1, 101), fb(2, 101), fb(3, 113)]
    changes = [change(1, pixels=px(), records=[rec("appended", "1:b5")]), change(2, pixels=px()),
               change(3, pixels=px(), records=[rec("appeared", f"3:b{i}") for i in range(1, 13)])]
    # a lifetime starts at the after box of each record; every box of the first frame is a target by rule
    lifetimes = [life(1, "y", ["1:b5"])] + [life(1 + i, "y", [f"3:b{i}"]) for i in range(1, 13)]
    assert incremental_projection(boxes, changes, lifetimes) == {"frames": 4, "boxes": 415, "calls": 4, "calls_without_targets": 1, "target_boxes": 113,
                                                                 "share_of_boxes": 0.2723, "targets_per_call": 28.25, "boxes_per_frame": 103.75}
    changes[1].pixels.components = 0
    p = incremental_projection(boxes, changes, lifetimes)
    assert (p["calls"], p["calls_without_targets"], p["target_boxes"], p["targets_per_call"]) == (3, 0, 113, 37.67)


def test_select_by_frames():
    changes = [change(1, 0, 1), change(2, 1, 2), change(3, 2, 3)]
    lifetimes = [life(1, "kept", ["0:b1", "1:b1"]), life(2, "dropped", ["3:b2"])]
    boxes = [FrameBoxes(frame=n, png="", engine={}) for n in range(4)]
    b, c, l = select(boxes, changes, lifetimes, (1, 2))
    assert [x.frame for x in b] == [1, 2] and [x.id for x in c] == ["T2"] and [x.id for x in l] == ["L1"]
    assert select(boxes, changes, lifetimes, None) == (boxes, changes, lifetimes)


def test_totals_sums_kinds():
    changes = [change(1, records=[rec("appended"), rec("changed")]),
               change(2, kind="unsettled", records=[rec("changed")], moved=[("1:b1", "2:b2"), ("1:b3", "2:b4")])]
    t = totals(changes)
    assert t["transitions"] == {"single": 1, "unsettled": 1}
    assert t["records"] == {"appended": 1, "changed": 2}
    assert t["moved"] == 2
