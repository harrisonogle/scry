"""The command metrics (spec §9), scored without a model call against a hand-made command list. Every comparison with
the list is by frame number, never by seconds: the list rounds its times, so a time window can exclude the very frame
it names. Found and exact are primary; first-appearance error, submitted with its error, and false run are secondary.
Nothing here reads a lifetime's duration or sighting count as evidence that a command ran: submitted and false run read
`interpret`'s `submitted` and `entered_text` and nothing else. Nothing orders, weights or combines the scores."""
from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Callable

from scry.config import Config
from scry.evaluation import adapters
from scry.groundtruth import Entry, parse_commands, scorable, score_exact
from scry.run import Run
from scry.schemas import Change, Interpretation, Lifetime
from scry.textdiff import norm

COUNTING_LEVELS = ("lifetime", "frame", "transition")  # a summary entry spans many frames: its range says nothing about where


def window(e: Entry) -> tuple[int, int] | None:
    """The entry's frames from first visible to submitted; None when the list gives neither."""
    frames = [f for f in (e.first_frame, e.submitted_frame) if f is not None]
    return (min(frames), max(frames)) if frames else None


# ---------- found (primary) ----------
def score_found(entries: list[Entry], hits_for: Callable[[str], list[dict]]) -> list[dict]:
    """Found: a search for the command's exact text, as a phrase, returns an entry at a localising level whose frame range
    meets the entry's window. A covering summary hit never counts; its level is shown when nothing else covers."""
    rows = []
    for e in entries:
        row = {"n": e.n, "text": e.text, "scorable": scorable(e), "found": None, "rank": None, "level": None, "node_id": None}
        rows.append(row)
        w = window(e)
        if not row["scorable"] or w is None:
            continue  # no search is made
        covering = [(rank, h) for rank, h in enumerate(hits_for(f'"{e.text}"'), start=1)
                    if h["frames"][0] <= w[1] and h["frames"][1] >= w[0]]
        counting = next(((rank, h) for rank, h in covering if h["level"] in COUNTING_LEVELS), None)
        row["found"] = counting is not None
        if counting is not None:
            row.update(rank=counting[0], level=counting[1]["level"], node_id=counting[1]["node_id"])
        elif covering:
            row["level"] = covering[0][1]["level"]  # "only a summary quotes it"
    return rows


# ---------- exact per reader (primary) and the first-appearance error (secondary) ----------
def reader_views(lifetimes: list[Lifetime], vlm: dict[str, str]) -> dict[str, list[Lifetime]]:
    """`ocr`: the lifetimes as loaded. `vlm`, only with a second reader: the lifetimes it read, their text replaced by
    the model's majority reading."""
    views = {"ocr": lifetimes}
    if vlm:
        views["vlm"] = [l.model_copy(update={"text": vlm[l.id]}) for l in lifetimes if l.id in vlm]
    return views


def score_exact_by_reader(entries: list[Entry], views: dict[str, list[Lifetime]]) -> list[dict]:
    """Plan 1's scorer once per reader, merged by entry. `any` is what compares bases that have different readers."""
    by_reader = {reader: score_exact(entries, view) for reader, view in views.items()}
    rows = []
    for i, e in enumerate(entries):
        mine = {reader: scored[i] for reader, scored in by_reader.items()}
        exact = {reader: r["exact"] for reader, r in mine.items()}
        errors = {reader: r["frame_error"] for reader, r in mine.items()}
        # the smallest absolute error among the readers that are exact; `ocr` comes first, so it wins a tie
        errors["any"] = min((err for reader, err in errors.items() if exact[reader] and err is not None), key=abs, default=None)
        exact["any"] = any(exact.values())
        rows.append({"n": e.n, "text": e.text, "scorable": scorable(e), "exact": exact,
                     "lifetime": {reader: r["lifetime"] for reader, r in mine.items()}, "first_frame_error": errors,
                     "first_t_error": {reader: r["t_error"] for reader, r in mine.items()}})  # for a person reading one run
    return rows


# ---------- submitted and false run (secondary) ----------
def claims(changes: list[Change], interps: dict[str, Interpretation]) -> list[dict]:
    """A claim: a change whose interpretation says `submitted: yes`, has no error and a non-blank `entered_text`."""
    out = []
    for c in changes:
        ip = interps.get(c.id)
        if ip is not None and ip.submitted == "yes" and ip.error is None and ip.entered_text and ip.entered_text.strip():
            out.append({"change": c.id, "to_frame": c.to_frame, "text": norm(ip.entered_text)})
    return out


def score_claims(executed: list[Entry], never_run: list[Entry], claims: list[dict]) -> tuple[list[dict], list[dict]]:
    """One claim per ground-truth row, by text equality (case-sensitive, whitespace collapsed). Executed entries choose
    first, in list order: the free claim nearest their submitted frame, a tie going to the earlier. Then each never-run
    row takes the earliest claim left over, with no frame condition: that is a false run."""
    free = list(claims)

    def take(text: str, near: int | None) -> dict | None:
        equal = [c for c in free if c["text"] == norm(text)]
        if not equal:
            return None
        best = min(equal, key=lambda c: (abs(c["to_frame"] - near) if near is not None else 0, c["to_frame"]))
        free.remove(best)
        return best

    submit_rows = []
    for e in executed:
        claim = take(e.text, e.submitted_frame)
        late = claim["to_frame"] - e.submitted_frame if claim is not None and e.submitted_frame is not None else None
        submit_rows.append({"n": e.n, "text": e.text, "scorable": scorable(e), "submitted": claim is not None,
                            "claim": claim["change"] if claim else None, "submit_frame_error": late})
    false_rows = []
    for e in never_run:
        claim = take(e.text, None)
        false_rows.append({"text": e.text, "false_run": claim is not None, "claim": claim["change"] if claim else None})
    return submit_rows, false_rows


# ---------- assembly ----------
def _abs_mean(values: list[int]) -> float | None:
    return round(mean(abs(v) for v in values), 2) if values else None


def command_scores(executed: list[Entry], never_run: list[Entry], found_rows: list[dict] | None, exact_rows: list[dict],
                   submit_rows: list[dict] | None, false_rows: list[dict] | None) -> dict:
    """Rows, rates as (k, n), mean absolute frame errors with their counts, and the per-unit values that pair two runs.
    Entries that are not scorable (`Y`, `y`) are shown in the rows and enter no rate and no unit: reported, not rated."""
    no_found = {"found": None, "rank": None, "level": None, "node_id": None}
    no_submit = {"submitted": None, "claim": None, "submit_frame_error": None}
    entries = [exact_rows[i] | (found_rows[i] if found_rows is not None else no_found)
               | (submit_rows[i] if submit_rows is not None else no_submit) for i in range(len(executed))]
    rated = [(str(row["n"]), row, e) for row, e in zip(entries, executed) if row["scorable"]]
    readers = list(exact_rows[0]["exact"]) if exact_rows else ["ocr", "any"]
    units: dict[str, dict[str, float]] = {}
    rates: dict = {"found": None, "exact": {}, "submitted": None, "false_run": None}
    error_mean, error_n = {}, {}
    for reader in readers:
        units[f"exact.{reader}"] = {u: float(row["exact"][reader]) for u, row, _ in rated}
        rates["exact"][reader] = (sum(row["exact"][reader] for _, row, _ in rated), len(rated))
        errors = [row["first_frame_error"][reader] for _, row, _ in rated if row["first_frame_error"][reader] is not None]
        error_mean[reader], error_n[reader] = _abs_mean(errors), len(errors)
    units["first_frame_error_abs.any"] = {u: float(abs(row["first_frame_error"]["any"])) for u, row, _ in rated
                                          if row["first_frame_error"]["any"] is not None}
    if found_rows is not None:
        searched = [(u, row) for u, row, _ in rated if row["found"] is not None]
        units["found"] = {u: float(row["found"]) for u, row in searched}
        rates["found"] = (sum(row["found"] for _, row in searched), len(searched))
    submit_mean, submit_n = None, 0
    if submit_rows is not None:
        units["submitted"] = {u: float(row["submitted"]) for u, row, _ in rated}
        listed = [row for _, row, e in rated if e.submitted_frame is not None]  # a submission the list places
        rates["submitted"] = (sum(row["submitted"] for row in listed), len(listed))
        units["submit_frame_error_abs"] = {u: float(abs(row["submit_frame_error"])) for u, row, _ in rated
                                           if row["submit_frame_error"] is not None}
        submit_mean, submit_n = _abs_mean(list(units["submit_frame_error_abs"].values())), len(units["submit_frame_error_abs"])
    if false_rows is not None:
        units["false_run"] = {f"N{i}": float(row["false_run"]) for i, row in enumerate(false_rows, start=1)}
        rates["false_run"] = (sum(row["false_run"] for row in false_rows), len(false_rows))
    if false_rows is None:  # the rows are shown either way
        false_rows = [{"text": e.text, "false_run": None, "claim": None} for e in never_run]
    return {"entries": entries, "never_run": false_rows, "rates": rates, "first_frame_error_abs_mean": error_mean, "first_frame_error_abs_n": error_n,
            "submit_frame_error_abs_mean": submit_mean, "submit_frame_error_abs_n": submit_n, "units": units}


def score_commands(run: Run, cfg: Config, ground_truth: Path) -> dict | None:
    """A run's command scores against a command list in the format of docs/ground-truth/span2-commands.md. None when the
    run has no lifetimes; without an index found is not scored, without interpretations submitted and false run are not."""
    lifetimes = adapters.lifetimes(run)
    if not lifetimes:
        return None
    executed, never_run = parse_commands(Path(ground_truth).read_text())
    hits_for = adapters.search_fn(run, cfg)
    interps = adapters.interpretations(run)
    submit_rows, false_rows = score_claims(executed, never_run, claims(adapters.changes(run), interps)) if interps else (None, None)
    return command_scores(executed, never_run, score_found(executed, hits_for) if hits_for is not None else None,
                          score_exact_by_reader(executed, reader_views(lifetimes, adapters.vlm_majority(run))), submit_rows, false_rows)
