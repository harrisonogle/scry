from __future__ import annotations

from typing import Literal

# Every metric that has per-unit values, and which way is better. The keys of a scorecard's `units` are names of this
# table, and a comparison has one row per name. The direction names what `favours` means on one row; nothing orders,
# weights or combines metrics.
METRICS: dict[str, Literal["higher", "lower"]] = {
    "found": "higher",  # unit: the executed entry's n
    "exact.ocr": "higher",
    "exact.vlm": "higher",
    "exact.any": "higher",
    "submitted": "higher",
    "first_frame_error_abs.any": "lower",
    "submit_frame_error_abs": "lower",
    "false_run": "lower",  # unit: N<i>, the never-run row
    "questions.positive": "higher",  # unit: the question key
    "questions.negative": "higher",
    "cost.per_question": "lower",
    "cost.per_frame": "lower",  # unit: "run"
    "seconds.per_frame": "lower",
}
