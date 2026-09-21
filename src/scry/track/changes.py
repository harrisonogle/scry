"""What changed between two consecutive frames, per box, from boxes and pixels only (spec §6 `track`, §12).

The order is the spec's: touched boxes; untouched boxes are unchanged; same place, same text; moves; pairing; leftovers.
There are no groups, no connected components and no pools: a change record is one pair of boxes, or one appeared or
removed box."""
from __future__ import annotations

from scry.schemas import BBox, Box
from scry.track.pixels import PixelDiff, touched


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
