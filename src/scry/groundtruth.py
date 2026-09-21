"""The hand-made command list (docs/ground-truth/span2-commands.md is the format) and the exact-reading metric
(spec §9, the OCR reader). Evaluation only: no pipeline stage reads a ground truth."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from scry.schemas import Lifetime
from scry.textdiff import norm

_TEXT = re.compile(r"`([^`]*)`")
_PAIR = re.compile(r"(\d+),\s*(\d+\.\d+)")  # "161, 649.17": frame, time
_FRAME = re.compile(r"(\d+)\s*\(\d+\.\d+\)")  # "172 (668.13)": frame (time)


@dataclass
class Entry:
    n: int | None
    text: str
    first_frame: int | None = None
    first_t: float | None = None
    submitted_frame: int | None = None
    submitted_t: float | None = None
    frames: list[int] = field(default_factory=list)


def _cells(line: str) -> list[str]:
    s = line.strip()
    s = s[1:-1] if s.endswith("|") and len(s) > 1 else s[1:]
    return [c.strip() for c in s.split("|")]


def _tables(md: str) -> dict[str, list[tuple[int, dict[str, str], list[str]]]]:
    """Per `## ` heading (lower-cased): the rows of its table as (line number, cells by header, cells)."""
    out: dict[str, list] = {}
    heading, header = None, None
    for no, line in enumerate(md.split("\n"), start=1):
        if line.startswith("## "):
            heading, header = line[3:].strip().lower(), None
            out[heading] = []
        elif heading is not None and line.lstrip().startswith("|"):
            cells = _cells(line)
            if header is None:
                header = cells
            elif set("".join(cells)) <= set("-: "):
                continue  # the |---| row
            elif len(cells) != len(header):
                raise ValueError(f"line {no}: {len(cells)} cells, the table's header has {len(header)}")
            else:
                out[heading].append((no, dict(zip(header, cells)), cells))
    return out


def _text(no: int, row: dict[str, str]) -> str:
    m = _TEXT.search(row.get("Text as displayed", ""))
    if m is None:
        raise ValueError(f"line {no}: no back-quoted text in the 'Text as displayed' cell")
    return m.group(1)


def parse_commands(md: str) -> tuple[list[Entry], list[Entry]]:
    """(executed, never run). A missing section gives an empty list."""
    tables = _tables(md)
    executed: list[Entry] = []
    for no, row, cells in next((rows for h, rows in tables.items() if h.startswith("executed")), []):
        first, submitted = _PAIR.findall(cells[2]), _PAIR.findall(cells[3])
        e = Entry(n=int(cells[0]), text=_text(no, row))
        if first:
            e.first_frame, e.first_t = int(first[0][0]), float(first[0][1])
        if submitted:
            e.submitted_frame, e.submitted_t = int(submitted[-1][0]), float(submitted[-1][1])
        executed.append(e)
    never = [Entry(n=None, text=_text(no, row), frames=[int(f) for f in _FRAME.findall(cells[1])])
             for no, row, cells in next((rows for h, rows in tables.items() if "never run" in h), [])]
    return executed, never


def scorable(e: Entry) -> bool:
    """At least 4 non-space characters: a one-letter answer such as `y` is a substring of almost any lifetime, so it is
    reported and left out of rates (an evaluation-side cut fitted to this list, stated as such)."""
    return len("".join(e.text.split())) >= 4


def matching_lifetimes(e: Entry, lifetimes: list[Lifetime]) -> list[Lifetime]:
    """Exact: the entry's text, whitespace-collapsed, is a case-sensitive substring of the lifetime's majority reading.
    Ordered by first frame, then id number."""
    want = norm(e.text)
    found = [l for l in lifetimes if want in norm(l.text)]
    return sorted(found, key=lambda l: (l.first.frame, int(l.id[1:])))


def score_exact(entries: list[Entry], lifetimes: list[Lifetime]) -> list[dict]:
    rows = []
    for e in entries:
        found = matching_lifetimes(e, lifetimes)
        best = found[0] if found else None
        timed = best is not None and e.first_frame is not None
        rows.append({"n": e.n, "text": e.text, "scorable": scorable(e), "exact": bool(found), "matches": len(found),
                     "lifetime": best.id if best else None, "first_frame": best.first.frame if best else None,
                     "frame_error": best.first.frame - e.first_frame if timed else None,
                     "t_error": round(best.first.t - e.first_t, 2) + 0.0 if timed else None})  # + 0.0: never "-0.0"
    return rows


def exact_rate(rows: list[dict]) -> tuple[int, int]:
    """(exact, scorable) over the scorable rows."""
    rated = [r for r in rows if r["scorable"]]
    return sum(1 for r in rated if r["exact"]), len(rated)
