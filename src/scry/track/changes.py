"""What changed between two consecutive frames, per box, from boxes and pixels only (spec §6 `track`, §12).

The order is the spec's: touched boxes; untouched boxes are unchanged; same place, same text; moves; pairing; leftovers.
There are no groups, no connected components and no pools: a change record is one pair of boxes, or one appeared or
removed box."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from scry.schemas import BBox, Box, BoxChange, BoxText, Change, Frame, PixelStats, box_ref
from scry.textdiff import char_diff
from scry.track.pixels import PixelDiff, margin_px, touched, touched_by, touched_by_rect


def intersection(a: BBox, b: BBox) -> int:
    """Area of the intersection of two rectangles; 0 when they do not intersect."""
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def match_one_to_one(cands: list[tuple[int, int, int]]) -> list[tuple[int, int]]:
    """Greedy one-to-one matching. Candidates are (area, index_in_a, index_in_b), indices being positions in reading
    order. Greatest area first, ties by index_in_a then index_in_b; a pair is taken when neither side is taken."""
    taken_a: set[int] = set()
    taken_b: set[int] = set()
    out: list[tuple[int, int]] = []
    for _, i, j in sorted(cands, key=lambda c: (-c[0], c[1], c[2])):
        if i not in taken_a and j not in taken_b:
            taken_a.add(i)
            taken_b.add(j)
            out.append((i, j))
    return out


def touched_flags(boxes: list[Box], diff: PixelDiff | None, m: int) -> list[bool]:
    """Per box, whether a changed pixel lies inside the box grown by m. Without pixel data every box is touched."""
    if diff is None:
        return [True] * len(boxes)
    return [touched(b.bbox, diff, m) for b in boxes]


def match_unchanged(a_boxes: list[Box], b_boxes: list[Box], ta: list[bool], tb: list[bool]) -> list[tuple[int, int]]:
    """Untouched boxes are unchanged (H1): every untouched box of a with every untouched box of b it intersects, matched
    one to one. The texts of a pair may differ: that is a variant reading, never a change. Index pairs, ordered by b."""
    cands = []
    for i, a in enumerate(a_boxes):
        if ta[i]:
            continue
        for j, b in enumerate(b_boxes):
            if not tb[j]:
                area = intersection(a.bbox, b.bbox)
                if area > 0:
                    cands.append((area, i, j))
    return sorted(match_one_to_one(cands), key=lambda p: p[1])


Pairs = tuple[list[tuple[Box, Box]], list[Box], list[Box]]  # pairs (by the later box's reading order), remaining before, remaining after


def _pair_by_intersection(before: list[Box], after: list[Box], ok) -> Pairs:
    """Every before box with every after box it intersects and `ok` accepts, matched one to one (greatest intersection
    first). The lists are in reading order and so are the remaining lists."""
    cands = []
    for i, a in enumerate(before):
        for j, b in enumerate(after):
            if ok(a, b):
                area = intersection(a.bbox, b.bbox)
                if area > 0:
                    cands.append((area, i, j))
    matched = sorted(match_one_to_one(cands), key=lambda p: p[1])
    in_a, in_b = {i for i, _ in matched}, {j for _, j in matched}
    return ([(before[i], after[j]) for i, j in matched], [a for i, a in enumerate(before) if i not in in_a],
            [b for j, b in enumerate(after) if j not in in_b])


def same_place(before: list[Box], after: list[Box], touched_a: set[str], touched_b: set[str]) -> Pairs:
    """Same place, same text: intersecting boxes with exactly equal text, at least one of them touched. Something
    visual changed over unchanged text; no change record."""
    return _pair_by_intersection(before, after, lambda a, b: a.text == b.text and (a.id in touched_a or b.id in touched_b))


def cancel_moves(before: list[Box], after: list[Box], touched_a: set[str], touched_b: set[str]) -> Pairs:
    """Moves (H3): among the touched boxes, the k-th occurrence of a text in `before` pairs with its k-th occurrence in
    `after` (reading order), anywhere in the frame, up to the smaller count. Text equality is exact. An untouched box
    cannot have moved and passes through."""
    waiting: dict[str, list[int]] = {}
    for i, a in enumerate(before):
        if a.id in touched_a:
            waiting.setdefault(a.text, []).append(i)
    matched: list[tuple[int, int]] = []
    for j, b in enumerate(after):
        if b.id in touched_b and waiting.get(b.text):
            matched.append((waiting[b.text].pop(0), j))
    in_a, in_b = {i for i, _ in matched}, {j for _, j in matched}
    return ([(before[i], after[j]) for i, j in matched], [a for i, a in enumerate(before) if i not in in_a],
            [b for j, b in enumerate(after) if j not in in_b])


def kind_of(before: str, after: str) -> Literal["reread", "appended", "truncated", "changed"]:
    """A convenience label computed with all whitespace removed (H4); the recorded strings stay exact."""
    x, y = "".join(before.split()), "".join(after.split())
    if x == y:
        return "reread"
    if y.startswith(x):
        return "appended"
    if x.startswith(y):
        return "truncated"
    return "changed"


def pair_rest(before: list[Box], after: list[Box], touched_a: set[str], touched_b: set[str]) -> Pairs:
    """Pairing (H2): every remaining before box with every remaining after box it intersects, at least one of the two
    touched, matched one to one, so the greatest intersection wins. The partner may be untouched: a growing text's
    shorter self usually lies outside the changed pixels, and so does a shrinking text's shorter self."""
    return _pair_by_intersection(before, after, lambda a, b: a.id in touched_a or b.id in touched_b)


@dataclass
class Pairing:
    """A box of the later frame that continues the lifetime of a box of the earlier frame."""
    a: str  # box id in the earlier frame
    b: str  # box id in the later frame
    how: Literal["unchanged", "same_place", "moved", "reread"]


@dataclass
class PairResult:
    change: Change
    pairings: list[Pairing]  # by the later frame's reading order
    starts: list[str]  # box ids of the later frame whose lifetime starts here, in reading order


def _union(a: BBox, b: BBox) -> BBox:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def track_pair(a: Frame, b: Frame, a_boxes: list[Box], b_boxes: list[Box], diff: PixelDiff | None, margin: float) -> PairResult:
    """One transition. The returned Change has no id, kind "single", no reverts and no `continues`: the stage fills them."""
    m = margin_px(a_boxes, b_boxes, margin)
    ta, tb = touched_flags(a_boxes, diff, m), touched_flags(b_boxes, diff, m)
    touched_a = {x.id for x, t in zip(a_boxes, ta) if t}
    touched_b = {x.id for x, t in zip(b_boxes, tb) if t}
    order_a = {x.id: i for i, x in enumerate(a_boxes)}
    order_b = {x.id: j for j, x in enumerate(b_boxes)}

    unchanged = [(a_boxes[i], b_boxes[j]) for i, j in match_unchanged(a_boxes, b_boxes, ta, tb)]
    un_a, un_b = {x.id for x, _ in unchanged}, {y.id for _, y in unchanged}
    before = [x for x in a_boxes if x.id not in un_a]
    after = [y for y in b_boxes if y.id not in un_b]
    same, before, after = same_place(before, after, touched_a, touched_b)
    moves, before, after = cancel_moves(before, after, touched_a, touched_b)
    pairs, before, after = pair_rest(before, after, touched_a, touched_b)

    ref_a = lambda x: box_ref(a.frame, x.id)
    ref_b = lambda y: box_ref(b.frame, y.id)
    later: list[tuple[int, BoxChange]] = []  # pair and appeared records, keyed by the later box's reading order
    pairings = [(order_b[y.id], Pairing(x.id, y.id, how)) for how, found in (("unchanged", unchanged), ("same_place", same), ("moved", moves))
                for x, y in found]
    starts: list[str] = []
    for x, y in pairs:
        kind = kind_of(x.text, y.text)
        later.append((order_b[y.id], BoxChange(kind=kind, rect=_union(x.bbox, y.bbox), before=BoxText(box=ref_a(x), text=x.text),
                                               after=BoxText(box=ref_b(y), text=y.text), char_diff=char_diff(x.text, y.text),
                                               in_churn=x.in_churn or y.in_churn)))
        if kind == "reread":
            pairings.append((order_b[y.id], Pairing(x.id, y.id, "reread")))
        else:
            starts.append(y.id)
    flicker_new: list[str] = []
    for y in after:  # an after box left without a partner: appeared when touched, flicker when not
        starts.append(y.id)
        if y.id in touched_b:
            later.append((order_b[y.id], BoxChange(kind="appeared", rect=y.bbox, before=None, after=BoxText(box=ref_b(y), text=y.text),
                                                   in_churn=y.in_churn)))
        else:
            flicker_new.append(ref_b(y))
    removed = [BoxChange(kind="removed", rect=x.bbox, before=BoxText(box=ref_a(x), text=x.text), after=None, in_churn=x.in_churn)
               for x in before if x.id in touched_a]
    flicker_lost = [ref_a(x) for x in before if x.id not in touched_a]

    pixels = None
    if diff is not None:
        by_a = [touched_by(x.bbox, diff, m) if t else set() for x, t in zip(a_boxes, ta)]
        by_b = [touched_by(y.bbox, diff, m) if t else set() for y, t in zip(b_boxes, tb)]
        with_text = set().union(*by_a, *by_b)
        textless = [c for k, c in enumerate(diff.components, start=1) if k not in with_text]
        n = len(a_boxes) + len(b_boxes)
        rect_only = sum(1 for x, t in (*zip(a_boxes, ta), *zip(b_boxes, tb)) if not t and touched_by_rect(x.bbox, diff, m))
        pixels = PixelStats(changed_fraction=diff.changed_fraction, components=len(diff.components), textless=len(textless),
                            textless_area=sum(c.area for c in textless),
                            touched_share=round((len(touched_a) + len(touched_b)) / n, 4) if n else 0.0, rect_only=rect_only)

    change = Change(id="", from_frame=a.frame, to_frame=b.frame, t=(a.t_end, b.t_settled), kind="single", pixels=pixels,
                    records=[r for _, r in sorted(later, key=lambda kr: kr[0])] + removed,
                    moved=[(ref_a(x), ref_b(y)) for x, y in moves], same_place=len(same), unchanged=len(unchanged),
                    variants=sum(1 for x, y in unchanged if x.text != y.text), flicker_new=flicker_new, flicker_lost=flicker_lost)
    return PairResult(change, [p for _, p in sorted(pairings, key=lambda kp: kp[0])], sorted(starts, key=order_b.__getitem__))
