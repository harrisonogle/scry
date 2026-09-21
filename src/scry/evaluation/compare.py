from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from statistics import mean
from typing import Literal

from scry.evaluation.scorecard import METRICS


def paired_difference(a: dict[str, float], b: dict[str, float]) -> tuple[float | None, int, int]:
    """The mean of b − a over the units both have; the number of common units; the number dropped."""
    common = a.keys() & b.keys()
    dropped = len(a.keys() | b.keys()) - len(common)
    if not common:
        return None, 0, dropped
    return round(mean(b[u] - a[u] for u in common), 6), len(common), dropped


def _config(card: dict) -> tuple[str, str]:
    """Cards are the same configuration when their phase and config id are equal; they differ only in `repeat`."""
    return card["run"]["phase"], card["run"]["config_id"]


def same_config_diffs(cards: list[dict], metric: str, units: set[str] | None = None) -> list[float]:
    """The absolute paired difference of every two cards of one configuration that both hold the metric: what
    identical cold runs differ by (ledger L42)."""
    diffs = []
    for i, j in itertools.combinations([c for c in cards if metric in c["units"]], 2):
        if _config(i) != _config(j):
            continue
        ui, uj = i["units"][metric], j["units"][metric]
        if units is not None:
            ui, uj = ({u: v for u, v in x.items() if u in units} for x in (ui, uj))
        d = paired_difference(ui, uj)[0]
        if d is not None:
            diffs.append(abs(d))
    return diffs


def floor_single(diffs: list[float]) -> float | None:
    """The floor for one run against one run: the biggest difference seen between two runs that should be identical."""
    return max(diffs) if diffs else None


def scaled_floor(f1: float, n_a: int, n_b: int) -> float:
    """Means of repeats are steadier than single runs: the floor for a mean of n_a runs against a mean of n_b."""
    return round(f1 * math.sqrt((1 / n_a + 1 / n_b) / 2), 6)


def _by_config(cards: list[dict]) -> dict[tuple[str, str], list[dict]]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for c in cards:
        groups.setdefault(_config(c), []).append(c)
    return groups


def noise_table(cards: list[dict]) -> dict:
    """Config id → metric → the repeats' values (the mean of the units of each, in repeat order) and the largest
    paired difference between two of them, for every configuration with at least two repeats."""
    table: dict[str, dict] = {}
    for (_, config_id), group in _by_config(cards).items():
        if len(group) < 2:
            continue
        group = sorted(group, key=lambda c: c["run"]["repeat"])
        table[config_id] = {
            metric: {"values": [round(mean(c["units"][metric].values()), 4) for c in group if c["units"].get(metric)],
                     "max": floor_single(same_config_diffs(group, metric))}
            for metric in METRICS if any(metric in c["units"] for c in group)}
    return table


@dataclass
class Row:
    metric: str
    better: Literal["higher", "lower"]
    n_a: int
    n_b: int
    units: int
    dropped: int
    mean_a: float | None
    mean_b: float | None
    diff: float | None
    floor_single: float | None
    floor: float | None
    verdict: Literal["outside", "inside", "unknown", "not comparable"]
    reason: str | None
    favours: Literal["a", "b"] | None
    flips: list[str]
    cost_a: dict
    cost_b: dict


def _cost(cards: list[dict]) -> dict:
    out = {}
    for key, places in (("per_frame", 4), ("per_video", 2)):
        values = [c["cost"][key] for c in cards if c["cost"].get(key) is not None]
        out[key] = round(mean(values), places) if values else None
    return out


def compare_configs(a: list[dict], b: list[dict]) -> list[Row]:
    """One row per metric any card holds: the difference of the two configurations' means, paired over the units every
    card has, beside the noise floor measured from their own repeats. `outside` means only: strictly larger than that."""
    if len({tuple(c["run"]["frames"]) for c in a + b}) > 1:
        raise ValueError("configurations are paired over the same frames or not at all")
    cost_a, cost_b = _cost(a), _cost(b)
    rows = []
    for metric, better in METRICS.items():
        ha, hb = ([c["units"][metric] for c in side if metric in c["units"]] for side in (a, b))
        if not ha and not hb:
            continue
        seen = set().union(*ha, *hb)
        common = set.intersection(*(set(u) for u in ha + hb))
        row = Row(metric=metric, better=better, n_a=len(ha), n_b=len(hb), units=len(common),
                  dropped=len(seen) - len(common), mean_a=None, mean_b=None, diff=None, floor_single=None, floor=None,
                  verdict="not comparable", reason=None, favours=None, flips=[], cost_a=cost_a, cost_b=cost_b)
        rows.append(row)
        if not ha or not hb:
            row.units, row.dropped = 0, len(seen)
            row.reason = "absent in A" if not ha else "absent in B"
            continue
        if not common:
            row.reason = "no common units"
            continue
        order = sorted(common, key=lambda u: (len(u), u))
        au = {u: mean(units[u] for units in ha) for u in order}
        bu = {u: mean(units[u] for units in hb) for u in order}
        row.mean_a, row.mean_b = round(mean(au.values()), 6), round(mean(bu.values()), 6)
        row.diff = round(mean(bu[u] - au[u] for u in order), 6)
        if all(units[u] in (0, 1) for units in ha + hb for u in order):
            for u in order:
                if all(x[u] == 1 for x in ha) and all(x[u] == 0 for x in hb):
                    row.flips.append(f"{u}: A only")
                elif all(x[u] == 0 for x in ha) and all(x[u] == 1 for x in hb):
                    row.flips.append(f"{u}: B only")
        row.floor_single = floor_single(same_config_diffs(a, metric, common) + same_config_diffs(b, metric, common))
        if row.floor_single is None:  # single runs without a measured floor are never evidence of a difference
            row.verdict = "unknown"
            continue
        row.floor = scaled_floor(row.floor_single, row.n_a, row.n_b)
        if abs(row.diff) > row.floor:
            row.verdict = "outside"
            row.favours = "b" if (row.diff > 0) == (better == "higher") else "a"
        else:
            row.verdict = "inside"
    return rows


def all_pairs(cards: list[dict]) -> list[tuple[str, str, str, list[Row]]]:
    """Per span, every pair of configurations, in the order in which the cards first name them."""
    by_span: dict[str, list[dict]] = {}
    for c in cards:
        by_span.setdefault(c["run"]["span"], []).append(c)
    return [(span, ka[1], kb[1], compare_configs(ga, gb))
            for span, group in by_span.items()
            for (ka, ga), (kb, gb) in itertools.combinations(_by_config(group).items(), 2)]
