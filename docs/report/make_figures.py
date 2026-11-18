"""Generate the report's figures from docs/results/*.csv.

Usage: python docs/report/make_figures.py   -> docs/report/figures/*.pdf
Palette: categorical slots 1 (blue) and 2 (orange), validated for CVD/contrast.
"""

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "docs" / "results"
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID, AXIS = "#1f1f1c", "#6b6a63", "#e1e0d9", "#c3c2b7"
plt.rcParams.update({
    "font.family": "serif", "font.size": 7.5, "axes.titlesize": 8, "axes.labelsize": 7.5,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.5, "axes.axisbelow": True, "legend.frameon": False,
})


def rows(name):
    with (RES / name).open() as f:
        return list(csv.DictReader(f))


def scaling():
    r = rows("timing.csv")
    n = np.array([float(x["n"]) for x in r])
    val = np.array([float(x["validate_ms"]) for x in r])
    alloc = np.array([float(x["allocate_ms"]) for x in r])
    mem = np.array([float(x["peak_kib"]) for x in r]) / 1024
    fig, (a, b) = plt.subplots(1, 2, figsize=(3.4, 1.75), constrained_layout=True)
    a.loglog(n, alloc, "-o", color=BLUE, lw=1.5, ms=3.2, label="allocate")
    a.loglog(n, val, "-s", color=ORANGE, lw=1.5, ms=3.2, label="validate (DFS)")
    a.set_xlabel("tasks $n$")
    a.set_ylabel("mean time (ms)")
    a.set_title("Runtime (10 runs each)", loc="left")
    a.set_ylim(5e-3, 3e5)
    a.legend(loc="upper left", handlelength=1.4, borderaxespad=0.2)
    b.loglog(n, mem, "-o", color=BLUE, lw=1.5, ms=3.2)
    b.set_xlabel("tasks $n$")
    b.set_ylabel("peak memory (MiB)")
    b.set_title("Allocation memory", loc="left")
    fig.savefig(OUT / "scaling.pdf")


def policies():
    r = [x for x in rows("comparison.csv") if x["n"] == "250"]
    scen = ["baseline", "overload", "fragmented", "dense-deps", "slack"]
    d = [float(next(x for x in r if x["scenario"] == s and x["policy"] == "deadline")["projected_lateness_h"]) for s in scen]
    e = [float(next(x for x in r if x["scenario"] == s and x["policy"] == "entry")["projected_lateness_h"]) for s in scen]
    y = np.arange(len(scen))
    fig, ax = plt.subplots(figsize=(3.4, 1.9), constrained_layout=True)
    h = 0.36
    ax.barh(y - h / 2 - 0.01, d, h, color=BLUE, label="deadline-first")
    ax.barh(y + h / 2 + 0.01, e, h, color=ORANGE, label="entry order")
    for yy, v in zip(y, d):
        ax.text(v + 1.5, yy - h / 2, f"{v:.0f}", va="center", fontsize=6.3, color=INK)
    for yy, v in zip(y, e):
        ax.text(v + 1.5, yy + h / 2, f"{v:.0f}", va="center", fontsize=6.3, color=INK)
    ax.set_yticks(y, scen)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("projected lateness (hours)")
    ax.set_xlim(0, max(e) * 1.15)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, handlelength=1.2, columnspacing=1.0)
    fig.savefig(OUT / "policies.pdf")


def optimality():
    r = rows("optimality.csv")
    out = {}
    for hours, label in (("4", "overloaded\nmorning (4 h)"), ("8", "normal\nday (8 h)")):
        rr = [x for x in r if x["hours"] == hours]
        for p in ("deadline", "entry"):
            same = sum(1 for x in rr if x[f"{p}_unplaced"] == x["opt_unplaced"] and x[f"{p}_late"] == x["opt_late"])
            out[(label, p)] = 100 * same / len(rr)
    labels = list(dict.fromkeys(k[0] for k in out))
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(3.4, 1.7), constrained_layout=True)
    w = 0.34
    for i, (p, col, lab) in enumerate((("deadline", BLUE, "deadline-first"), ("entry", ORANGE, "entry order"))):
        vals = [out[(l, p)] for l in labels]
        xs = x + (i - 0.5) * (w + 0.02)
        ax.bar(xs, vals, w, color=col, label=lab)
        for xx, v in zip(xs, vals):
            ax.text(xx, v + 2, f"{v:.0f}%", ha="center", fontsize=6.5, color=INK)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 100)
    ax.set_ylabel("days with optimal\nlate-task count (%)")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left")
    fig.savefig(OUT / "optimality.pdf")


if __name__ == "__main__":
    scaling()
    policies()
    optimality()
    print("figures written to", OUT)
