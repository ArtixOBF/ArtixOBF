"""Benchmark and policy-comparison harness.

Usage:
    python -m campaignflow.bench.run            # full run, writes docs/results/
    python -m campaignflow.bench.run --quick    # smaller sizes, fewer reps

Timing follows the proposal: ten fresh repetitions per size, measured with
time.perf_counter_ns(), timing validation and allocation separately and
excluding data generation, copying, output and correctness checks.
Peak memory is measured in a separate run with tracemalloc so the tracing
overhead does not distort the timings.
"""

from __future__ import annotations

import argparse
import copy
import csv
import statistics
import time
import tracemalloc
from pathlib import Path

from ..core.allocator import allocate
from ..core.invariants import check_plan
from ..core.metrics import replay, summarize
from ..core.validate import validate
from .generator import generate

OUT = Path(__file__).resolve().parents[2] / "docs" / "results"


def time_size(n: int, reps: int, seed0: int = 1000) -> dict:
    val_ns, alloc_ns = [], []
    edges = staff = 0
    for r in range(reps):
        wl = generate(n, seed=seed0 + r, load=1.2, fragmented=True)
        tasks, staff_list = wl.tasks, wl.staff
        edges = sum(len(t.prereqs) for t in tasks.values())
        staff = len(staff_list)

        t0 = time.perf_counter_ns()
        errs = validate(tasks, staff_list, [])
        t1 = time.perf_counter_ns()
        plan = allocate(tasks, staff_list, [], skip_validation=True)
        t2 = time.perf_counter_ns()

        assert not errs, errs
        val_ns.append(t1 - t0)
        alloc_ns.append(t2 - t1)
        # Correctness check runs outside the timed region.
        bad = check_plan(tasks, staff_list, [], plan)
        assert not bad, bad[:5]

    wl = generate(n, seed=seed0, load=1.2, fragmented=True)
    tracemalloc.start()
    allocate(wl.tasks, wl.staff, [])
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    def ms(xs):
        return statistics.mean(xs) / 1e6, (statistics.stdev(xs) / 1e6 if len(xs) > 1 else 0.0)

    vm, vs = ms(val_ns)
    am, as_ = ms(alloc_ns)
    return {"n": n, "edges": edges, "staff": staff, "validate_ms": round(vm, 3),
            "validate_sd": round(vs, 3), "allocate_ms": round(am, 3),
            "allocate_sd": round(as_, 3), "peak_kib": round(peak / 1024, 1)}


SCENARIOS = {
    "baseline":   dict(load=1.0, tightness="tight"),
    "overload":   dict(load=1.6, tightness="tight"),
    "slack":      dict(load=0.6, tightness="loose"),
    "dense-deps": dict(load=1.0, tightness="tight", dep_density=1.5),
    "fragmented": dict(load=1.0, tightness="tight", fragmented=True),
}


def compare(sizes, seeds) -> list[dict]:
    rows = []
    for name, kw in SCENARIOS.items():
        for n in sizes:
            for seed in seeds:
                wl = generate(n, seed=seed, **kw)
                for policy in ("deadline", "entry"):
                    tasks = copy.deepcopy(wl.tasks)
                    plan = allocate(tasks, wl.staff, [], policy=policy)
                    assert not check_plan(tasks, wl.staff, [], plan)
                    s = summarize(tasks, plan)
                    late, lateness = replay(tasks, plan, seed=seed, error=0.2)
                    rows.append({
                        "scenario": name, "n": n, "seed": seed, "policy": policy,
                        "allocated": s.allocated, "on_time": s.on_time,
                        "at_risk": s.at_risk, "on_time_rate": round(s.on_time_rate, 4),
                        "projected_lateness_min": s.total_lateness,
                        "capacity_omitted": s.capacity, "blocked": s.blocked,
                        "unmet_demand_min": s.unmet_demand,
                        "replay_late": late, "replay_lateness_min": lateness,
                    })
    return rows


def aggregate(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["scenario"], r["n"], r["policy"]), []).append(r)
    out = []
    for (sc, n, pol), rs in groups.items():
        out.append({
            "scenario": sc, "n": n, "policy": pol,
            "on_time_rate": round(statistics.mean(r["on_time_rate"] for r in rs), 3),
            "at_risk": round(statistics.mean(r["at_risk"] for r in rs), 1),
            "projected_lateness_h": round(statistics.mean(r["projected_lateness_min"] for r in rs) / 60, 1),
            "replay_late": round(statistics.mean(r["replay_late"] for r in rs), 1),
            "allocated": round(statistics.mean(r["allocated"] for r in rs), 1),
            "capacity_omitted": round(statistics.mean(r["capacity_omitted"] for r in rs), 1),
        })
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def md_table(rows: list[dict]) -> str:
    cols = list(rows[0])
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
    return "\n".join(lines)


def plot(timing: list[dict]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot")
        return
    ns = [r["n"] for r in timing]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.errorbar(ns, [r["allocate_ms"] for r in timing],
                yerr=[r["allocate_sd"] for r in timing], marker="o", label="allocate")
    ax.errorbar(ns, [r["validate_ms"] for r in timing],
                yerr=[r["validate_sd"] for r in timing], marker="s", label="validate (DFS)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("tasks (n)")
    ax.set_ylabel("mean time (ms), 10 reps")
    ax.set_title("CampaignFlow runtime scaling")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "runtime.png", dpi=150)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()

    sizes = [10, 50, 100, 250] if args.quick else [10, 50, 100, 250, 1000, 2500, 5000, 10000]
    reps = 3 if args.quick else 10
    timing = []
    for n in sizes:
        row = time_size(n, reps)
        timing.append(row)
        print(row)
    write_csv(OUT / "timing.csv", timing)

    seeds = range(5) if args.quick else range(20)
    rows = compare([10, 50, 100, 250], seeds)
    write_csv(OUT / "comparison_raw.csv", rows)
    agg = aggregate(rows)
    write_csv(OUT / "comparison.csv", agg)

    (OUT / "RESULTS.md").write_text(
        "# Benchmark results (synthetic workloads)\n\n"
        "## Runtime scaling\n\n" + md_table(timing) +
        "\n\n## Policy comparison (means over seeds)\n\n" + md_table(agg) + "\n")
    plot(timing)
    print(f"wrote results to {OUT}")


if __name__ == "__main__":
    main()
