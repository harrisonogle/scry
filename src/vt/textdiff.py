from __future__ import annotations

import re
from typing import Sequence

from rapidfuzz.distance import Levenshtein

from vt.schemas import DiffOp

_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})
_CLOCK = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?(?: ?[AP]M)?")


def norm(s: str) -> str:
    return " ".join(s.translate(_QUOTES).split())


def similarity(a: str, b: str) -> float:
    return float(Levenshtein.normalized_similarity(norm(a), norm(b)))


def levenshtein(a: str, b: str) -> int:
    return int(Levenshtein.distance(norm(a), norm(b)))


def lcp_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def myers(a: Sequence, b: Sequence) -> list[tuple[str, int, int]]:
    """Myers O(ND) diff. Returns per-element runs ('equal'|'insert'|'delete', i, j):
    for equal/delete, i indexes a; for insert, j indexes b (i is the insertion point in a)."""
    n, m = len(a), len(b)
    max_d = n + m
    v = {1: 0}
    trace: list[dict[int, int]] = []
    for d in range(max_d + 1):
        trace.append(dict(v))
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
                x = v.get(k + 1, 0)
            else:
                x = v.get(k - 1, 0) + 1
            y = x - k
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            v[k] = x
            if x >= n and y >= m:
                return _backtrack(trace, a, b)
    return _backtrack(trace, a, b)


def _backtrack(trace, a, b) -> list[tuple[str, int, int]]:
    x, y = len(a), len(b)
    ops: list[tuple[str, int, int]] = []
    for d in range(len(trace) - 1, -1, -1):
        v = trace[d]
        k = x - y
        if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
            prev_k = k + 1
        else:
            prev_k = k - 1
        prev_x = v.get(prev_k, 0)
        prev_y = prev_x - prev_k
        while x > prev_x and y > prev_y:
            x -= 1
            y -= 1
            ops.append(("equal", x, y))
        if d > 0:
            if x == prev_x:
                y -= 1
                ops.append(("insert", x, y))
            else:
                x -= 1
                ops.append(("delete", x, y))
    ops.reverse()
    return ops


def line_ops(prev: list[str], cur: list[str]) -> list[dict]:
    out: list[dict] = []
    for op, i, j in myers(prev, cur):
        if op == "delete":
            out.append({"op": "delete", "old": prev[i], "old_index": i})
        elif op == "insert":
            out.append({"op": "insert", "new": cur[j], "new_index": j})
    return out


def char_diff(a: str, b: str) -> list[list[str]]:
    runs: list[list[str]] = []
    for op, i, j in myers(list(a), list(b)):
        sym = {"equal": "=", "insert": "+", "delete": "-"}[op]
        ch = b[j] if op == "insert" else a[i]
        if runs and runs[-1][0] == sym:
            runs[-1][1] += ch
        else:
            runs.append([sym, ch])
    return runs


def pair_modifies(ops: list[dict], prev_y: list[int], cur_y: list[int], line_h: float, sim_threshold: float) -> list[DiffOp]:
    """Pair adjacent (delete a, insert b) into modify(a→b) when they overlap vertically or are similar."""
    out: list[DiffOp] = []
    i = 0
    while i < len(ops):
        o = ops[i]
        nxt = ops[i + 1] if i + 1 < len(ops) else None
        if o["op"] == "delete" and nxt is not None and nxt["op"] == "insert":
            ya, yb = prev_y[o["old_index"]], cur_y[nxt["new_index"]]
            if abs(ya - yb) < 0.5 * line_h or similarity(o["old"], nxt["new"]) >= sim_threshold:
                out.append(DiffOp(op="modify", old=o["old"], new=nxt["new"], old_index=o["old_index"],
                                  new_index=nxt["new_index"], char_diff=char_diff(o["old"], nxt["new"]), y=yb,
                                  clock=is_clock_change(o["old"], nxt["new"])))
                i += 2
                continue
        if o["op"] == "delete":
            out.append(DiffOp(op="delete", old=o["old"], old_index=o["old_index"], y=prev_y[o["old_index"]]))
        else:
            out.append(DiffOp(op="insert", new=o["new"], new_index=o["new_index"], y=cur_y[o["new_index"]]))
        i += 1
    return out


def is_clock_change(a: str, b: str) -> bool:
    """True when a and b differ only inside a clock-like token at the same position."""
    if a == b:
        return False
    ma, mb = list(_CLOCK.finditer(a)), list(_CLOCK.finditer(b))
    if not ma or len(ma) != len(mb):
        return False
    stripped_a = _CLOCK.sub("\x00", a)
    stripped_b = _CLOCK.sub("\x00", b)
    return stripped_a == stripped_b
