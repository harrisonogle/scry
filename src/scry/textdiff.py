from __future__ import annotations

from typing import Sequence

from rapidfuzz.distance import Levenshtein

_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


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
