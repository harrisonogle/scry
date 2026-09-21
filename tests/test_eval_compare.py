import pytest

from scry.evaluation.compare import (all_pairs, compare_configs, floor_single, noise_table, paired_difference,
                                     same_config_diffs, scaled_floor)


def card(config_id: str, repeat: int, units: dict, frames=(155, 187), span: str = "span2",
         per_frame: float = 0.1, per_video: float = 22.1) -> dict:
    """A scorecard as Task 7 writes it, cut to what a comparison reads."""
    return {"run": {"phase": "p1", "name": f"{config_id}-r{repeat}", "config_id": config_id, "span": span,
                    "frames": list(frames), "repeat": repeat},
            "units": units, "cost": {"per_frame": per_frame, "per_video": per_video}}


def cards(config_id: str, metric: str, units_per_repeat: list[dict], **kw) -> list[dict]:
    return [card(config_id, i, {metric: units}, **kw) for i, units in enumerate(units_per_repeat, start=1)]


def row(rows, metric):
    [r] = [r for r in rows if r.metric == metric]
    return r


A_FOUND = [{"1": 1, "2": 1, "3": 1}, {"1": 1, "2": 1, "3": 1}, {"1": 1, "2": 1, "3": 0}]
B_FOUND = [{"1": 1, "2": 0, "3": 0}] * 3


def test_paired_difference():
    assert paired_difference({"1": 1, "2": 1, "3": 0}, {"1": 1, "2": 0, "3": 0}) == (-0.333333, 3, 0)
    assert paired_difference({"1": 1, "2": 0}, {"1": 1, "2": 1, "3": 1}) == (0.5, 2, 1)
    assert paired_difference({"1": 1}, {"2": 1}) == (None, 0, 2)


def test_floor_from_three_repeats_and_scaling():
    three = cards("span2-a", "found", [{"1": 1, "2": 1, "3": 0}, {"1": 1, "2": 0, "3": 0}, {"1": 1, "2": 1, "3": 0}])
    diffs = same_config_diffs(three, "found")
    assert diffs == [0.333333, 0.0, 0.333333]
    assert floor_single(diffs) == 0.333333
    table = noise_table(three + cards("span2-solo", "found", [{"1": 1, "2": 1, "3": 0}]))
    assert table["span2-a"]["found"] == {"values": [0.6667, 0.3333, 0.6667], "max": 0.333333}
    assert "span2-solo" not in table
    assert floor_single([]) is None
    assert scaled_floor(0.3, 1, 1) == 0.3
    assert scaled_floor(0.3, 2, 2) == 0.212132
    assert scaled_floor(0.3, 3, 3) == 0.173205
    assert scaled_floor(0.3, 3, 1) == 0.244949


def test_outside_the_noise():
    r = row(compare_configs(cards("span2-a", "found", A_FOUND), cards("span2-b", "found", B_FOUND)), "found")
    assert (r.better, r.n_a, r.n_b, r.units, r.dropped) == ("higher", 3, 3, 3, 0)
    assert (r.mean_a, r.mean_b, r.diff) == (0.888889, 0.333333, -0.555556)
    assert (r.floor_single, r.floor) == (0.333333, 0.19245)
    assert (r.verdict, r.reason, r.favours) == ("outside", None, "a")
    assert r.flips == ["2: A only"]


def test_inside_identical_and_unknown():
    metric = "first_frame_error_abs.any"  # lower is better
    a = cards("span2-a", metric, [{"1": 2, "2": 0}, {"1": 4, "2": 0}])
    b = cards("span2-b", metric, [{"1": 3, "2": 1}, {"1": 3, "2": 0}])
    r = row(compare_configs(a, b), metric)
    assert (r.diff, r.floor_single, r.floor, r.verdict, r.favours) == (0.25, 1.0, 0.707107, "inside", None)
    same = [{"1": 2, "2": 0}] * 2
    r = row(compare_configs(cards("span2-a", metric, same), cards("span2-b", metric, same)), metric)
    assert (r.diff, r.floor, r.verdict) == (0.0, 0.0, "inside")  # 0 is not strictly larger than 0
    r = row(compare_configs(cards("span2-a", metric, [{"1": 1, "2": 1}]), cards("span2-b", metric, [{"1": 1, "2": 0}])), metric)
    assert (r.diff, r.floor_single, r.floor, r.verdict, r.favours) == (-0.5, None, None, "unknown", None)


def test_missing_units_and_absent_metrics():
    a = cards("span2-a", "found", [A_FOUND[0], {"1": 1, "2": 1}, A_FOUND[2]])
    b = cards("span2-b", "found", B_FOUND)
    r = row(compare_configs(a, b), "found")
    assert (r.units, r.dropped) == (2, 1)

    for c in a:
        c["units"]["exact.vlm"] = {"1": 1}
    r = row(compare_configs(a, b), "exact.vlm")
    assert (r.verdict, r.reason, r.n_a, r.n_b) == ("not comparable", "absent in B", 3, 0)

    with pytest.raises(ValueError, match="same frames"):
        compare_configs(cards("span2-a", "found", A_FOUND, frames=(155, 187)),
                        cards("smoke-b", "found", B_FOUND, frames=(145, 155)))

    a = [card("span2-a", 1, {"found": A_FOUND[0], "exact.vlm": {"1": 1}}, per_frame=0.12, per_video=26.52),
         card("span2-a", 2, {"found": A_FOUND[1], "exact.vlm": {"1": 1}}, per_frame=0.14, per_video=30.94)]
    rows = compare_configs(a, b)
    assert [r.metric for r in rows] == ["found", "exact.vlm"]
    assert all(r.cost_a == {"per_frame": 0.13, "per_video": 28.73} for r in rows)
    assert all(r.cost_b == {"per_frame": 0.1, "per_video": 22.1} for r in rows)


def test_all_pairs_per_span():
    deck = []
    for span, frames in (("smoke", (145, 155)), ("span2", (155, 187))):
        for base in ("transcribing", "grouponly", "none"):
            deck += cards(f"{span}-{base}", "found", B_FOUND, frames=frames, span=span)
    pairs = all_pairs(deck)
    assert [(span, a, b) for span, a, b, _ in pairs] == [
        ("smoke", "smoke-transcribing", "smoke-grouponly"), ("smoke", "smoke-transcribing", "smoke-none"),
        ("smoke", "smoke-grouponly", "smoke-none"),
        ("span2", "span2-transcribing", "span2-grouponly"), ("span2", "span2-transcribing", "span2-none"),
        ("span2", "span2-grouponly", "span2-none")]
    assert all(row(rows, "found").verdict == "inside" for *_, rows in pairs)
