"""Extra experiments for the report.

1. Optimality gap: on small days (n = 7 tasks) every task order is tried by
   brute force (7! = 5,040 orders). Feeding each order through the same serial
   placement as the allocator enumerates all schedules the allocator could
   produce, so the best of them is the optimum for this placement model.
   We then measure how often deadline-first greedy and the entry-order
   baseline reach it.
2. Pruning: allocation time with and without the two search-pruning rules,
   with identical output asserted.

Usage: python -m campaignflow.bench.analysis   (writes docs/results/*)
"""

from __future__ import annotations

import csv
import itertools
import random
import statistics
import time
from pathlib import Path

from ..core.allocator import allocate
from ..core.models import Staff, Task, URGENT
from ..core.policy import POLICIES
from ..core.validate import validate
from .generator import generate

OUT = Path(__file__).resolve().parents[2] / "docs" / "results"
H = 60


def small_day(seed: int, n: int = 7, hours: int = 4):
    """A small day: 2 people working `hours`, n tasks, a few dependencies, real deadlines."""
    rng = random.Random(seed)
    tasks = {}
    for i in range(n):
        tid = f"T{i}"
        hi = rng.choice((30, 45, 60, 60, 90, 120))
        prereqs = [f"T{j}" for j in range(i) if rng.random() < 0.15]
        tasks[tid] = Task(tid, f"Task {i}", skill=rng.choice(("writing", "editing")),
                          effort_min=hi // 2, effort_max=hi,
                          deadline=9 * H + rng.randint(60, 300 if hours <= 4 else 420),
                          urgency=URGENT if rng.random() < 0.1 else "normal",
                          prereqs=prereqs, entry_order=i)
    staff = [Staff("W", "Writer", {"writing"}, [(9 * H, (9 + hours) * H)]),
             Staff("E", "Editor", {"editing"}, [(9 * H, (9 + hours) * H)], exceptions=[(10 * H + 30, 11 * H)])]
    return tasks, staff


def score(tasks, plan):
    """Lexicographic objective: fewer unplaced, then fewer late, then less lateness."""
    late = lateness = 0
    for a in plan.assignments:
        d = tasks[a.task_id].deadline
        if d is not None and a.end > d:
            late += 1
            lateness += a.end - d
    return (len(tasks) - len(plan.assignments), late, lateness)


def optimality(instances: int = 120, n: int = 7, hours: int = 4):
    rows = []
    for seed in range(instances):
        tasks, staff = small_day(seed, n, hours)
        assert not validate(tasks, staff, [])
        ids = list(tasks)
        best = None
        for perm in itertools.permutations(ids):
            rank = {tid: i for i, tid in enumerate(perm)}
            POLICIES["_perm"] = lambda t, rank=rank: (rank[t.id],)
            s = score(tasks, allocate(tasks, staff, policy="_perm", skip_validation=True))
            if best is None or s < best:
                best = s
        POLICIES.pop("_perm", None)
        d = score(tasks, allocate(tasks, staff, policy="deadline"))
        e = score(tasks, allocate(tasks, staff, policy="entry"))
        rows.append({"hours": hours, "seed": seed, "opt_unplaced": best[0], "opt_late": best[1], "opt_lateness": best[2],
                     "deadline_unplaced": d[0], "deadline_late": d[1], "deadline_lateness": d[2],
                     "entry_unplaced": e[0], "entry_late": e[1], "entry_lateness": e[2]})
    return rows


def summarize_opt(rows):
    def pct(pred):
        return round(100 * sum(1 for r in rows if pred(r)) / len(rows), 1)
    out = {}
    for p in ("deadline", "entry"):
        out[p] = {
            "matches_optimum_%": pct(lambda r: (r[f"{p}_unplaced"], r[f"{p}_late"], r[f"{p}_lateness"]) ==
                                     (r["opt_unplaced"], r["opt_late"], r["opt_lateness"])),
            "same_late_count_%": pct(lambda r: r[f"{p}_unplaced"] == r["opt_unplaced"] and r[f"{p}_late"] == r["opt_late"]),
            "mean_extra_late_tasks": round(statistics.mean(r[f"{p}_late"] - r["opt_late"] for r in rows), 2),
            "mean_extra_lateness_min": round(statistics.mean(r[f"{p}_lateness"] - r["opt_lateness"] for r in rows), 1),
            "mean_extra_unplaced": round(statistics.mean(r[f"{p}_unplaced"] - r["opt_unplaced"] for r in rows), 2),
        }
    return out


def pruning(sizes=(1000, 2500, 5000, 10000), reps=3):
    rows = []
    for n in sizes:
        res, schedules = {}, {}
        for prune in (False, True):
            times = []
            for r in range(reps):
                wl = generate(n, seed=1000 + r, load=1.2, fragmented=True)
                t0 = time.perf_counter_ns()
                plan = allocate(wl.tasks, wl.staff, skip_validation=True, prune=prune)
                times.append((time.perf_counter_ns() - t0) / 1e6)
                key = [(a.task_id, a.staff_id, a.start) for a in plan.assignments]
                schedules.setdefault(r, key)
                assert schedules[r] == key, "pruning changed the schedule"
            res[prune] = statistics.mean(times)
        rows.append({"n": n, "naive_ms": round(res[False], 1), "pruned_ms": round(res[True], 1),
                     "speedup": round(res[False] / res[True], 2)})
        print(rows[-1])
    return rows


def write(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    tight, normal = optimality(hours=4), optimality(hours=8)
    write(OUT / "optimality.csv", tight + normal)
    regimes = {"overloaded morning (4 h)": summarize_opt(tight), "normal day (8 h)": summarize_opt(normal)}
    print("optimality", regimes, f"{time.time() - t0:.0f}s")
    prows = pruning()
    write(OUT / "pruning.csv", prows)
    lines = ["# Analysis results", "", "## Optimality gap (120 random 7-task days per regime, brute force over 5,040 orders)", "",
             "| regime | policy | matches optimum | same late count | extra late tasks (mean) | extra lateness min (mean) | extra unplaced (mean) |",
             "|---|---|---|---|---|---|---|"]
    for reg, summ in regimes.items():
        for p, s in summ.items():
            lines.append(f"| {reg} | {p} | {s['matches_optimum_%']}% | {s['same_late_count_%']}% | {s['mean_extra_late_tasks']} | "
                         f"{s['mean_extra_lateness_min']} | {s['mean_extra_unplaced']} |")
    lines += ["", "## Search pruning (identical schedules asserted)", "", "| n | naive ms | pruned ms | speedup |", "|---|---|---|---|"]
    lines += [f"| {r['n']} | {r['naive_ms']} | {r['pruned_ms']} | {r['speedup']}x |" for r in prows]
    (OUT / "ANALYSIS.md").write_text("\n".join(lines) + "\n")
    print("wrote", OUT / "ANALYSIS.md")


if __name__ == "__main__":
    main()
