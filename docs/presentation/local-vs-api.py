"""Draw docs/presentation/local-vs-api.png from docs/presentation/local-vs-api.json, so the final numbers drop in
without redrawing by hand. Two panels: annotate dollars per frame (API Opus 5 against a local open-weight model at a
hosted rate) and reference pairs reproduced % (the API's own repeat floor against the local model), both as bands.

    uv run --with matplotlib python docs/presentation/local-vs-api.py [path/to/other.json] [out.png]

Same style and palette as the other presentation charts: 1920x1080 at 2x, light background, large type, text in ink.
Every number comes from the JSON; the JSON names its source files and the dataset it describes.
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "local-vs-api.json"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "local-vs-api.png"

SURFACE, INK, INK2, MUTED, GRID, BAND = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8985", "#e6e5e1", "#f0efec"
BLUE, ORANGE, BLUE_LIGHT, ORANGE_LIGHT = "#2a78d6", "#eb6834", "#9ec5f4", "#f5b79c"  # API blue, local orange

plt.rcParams.update({
    "font.family": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.linewidth": 1.5, "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "axes.labelcolor": INK2,
    "grid.color": GRID, "grid.linewidth": 1.2, "axes.grid": False,
})


def main() -> None:
    d = json.loads(DATA.read_text())
    labels = [d["api_label"], d["local_label"]]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(19.2, 10.8), gridspec_kw={"wspace": 0.35})
    fig.subplots_adjust(left=0.07, right=0.96, top=0.76, bottom=0.27)

    # panel 1: dollars per frame, two bars, direct labels
    c = d["cost_per_frame"]
    vals = [c["api"], c["local"]]
    ymax = max(vals) * 1.25
    ax1.bar([0, 1], vals, width=0.58, color=[BLUE, ORANGE], edgecolor="none")
    for x, v in zip([0, 1], vals):
        ax1.text(x, v + ymax * 0.02, f"\\${v:.3f}", ha="center", va="bottom", fontsize=28, color=INK, fontweight="bold")
    if vals[1] > 0:
        ax1.text(1, vals[1] + ymax * 0.12, f"{vals[0] / vals[1]:.1f}x cheaper", ha="center", va="bottom", fontsize=22, color=INK2)
    ax1.set_ylim(0, ymax)
    ax1.set_yticks([])
    ax1.set_title(c["title"], fontsize=26, color=INK, pad=18)

    # panel 2: pairs reproduced, a band per arm (low to high) on a 0 to 100 scale
    q = d["pairs_reproduced_pct"]
    bands = [(q["api_low"], q["api_high"]), (q["local_low"], q["local_high"])]
    for x, ((lo, hi), col, light) in enumerate(zip(bands, [BLUE, ORANGE], [BLUE_LIGHT, ORANGE_LIGHT])):
        ax2.bar(x, 100, width=0.58, color=BAND, edgecolor="none")
        ax2.bar(x, lo, width=0.58, color=col, edgecolor="none")
        ax2.bar(x, hi - lo, bottom=lo, width=0.58, color=light, edgecolor="none")
        text = f"{lo:g} to {hi:g} %" if lo != hi else f"{lo:g} %"
        ax2.text(x, 103, text, ha="center", va="bottom", fontsize=28, color=INK, fontweight="bold")
    ax2.set_ylim(0, 118)
    ax2.set_yticks([0, 50, 100])
    ax2.set_yticklabels(["0", "50", "100 %"], fontsize=20)
    ax2.yaxis.grid(True)
    ax2.set_axisbelow(True)
    ax2.set_title(q["title"], fontsize=26, color=INK, pad=18)

    for ax in (ax1, ax2):
        ax.set_xticks([0, 1])
        ax.set_xticklabels(labels, fontsize=22, color=INK)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="both", length=0)

    fig.text(0.05, 0.955, "A local open-weight model on annotate, against the API", fontsize=36, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.05, 0.895, f"{d['dataset']}; group-only annotation, one run each", fontsize=24, color=INK2, ha="left", va="top")
    fig.text(0.05, 0.085, "\n".join(textwrap.wrap(d["caption"], 120)), fontsize=21, color=INK, ha="left", va="bottom", linespacing=1.4)
    fig.text(0.05, 0.03, "\n".join(textwrap.wrap(f"Source: {d['source']}. {q['note']}.", 175)), fontsize=15, color=MUTED, ha="left", va="bottom", linespacing=1.4)
    fig.savefig(OUT, dpi=200)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
