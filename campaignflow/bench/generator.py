"""Seeded synthetic workload generator (clearly synthetic, not agency data).

Knobs mirror the proposal's evaluation plan:
    n              number of tasks and gates
    load           total demand / total staff capacity (1.0 = exactly full)
    tightness      "tight" (deadlines mostly today) or "loose" (up to 3 days)
    dep_density    expected prerequisites per vertex (edges only point forward
                   in creation order, so the graph is a DAG unless a cycle is
                   injected on purpose)
    gate_ratio     share of vertices that are external gates
    pending_gates  share of gates still unconfirmed
    urgent_ratio   share of tasks marked urgent
    fragmented     add random meetings to break staff windows into pieces
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from ..core.models import DONE, GATE, PENDING, URGENT, Staff, Task

SKILLS = ("writing", "editing")
DAY_START, DAY_END = 9 * 60, 18 * 60
LUNCH = (12 * 60, 13 * 60)


@dataclass
class Workload:
    tasks: dict[str, Task]
    staff: list[Staff]
    seed: int


def generate(
    n: int,
    seed: int,
    load: float = 1.0,
    tightness: str = "tight",
    dep_density: float = 0.6,
    gate_ratio: float = 0.15,
    pending_gates: float = 0.3,
    urgent_ratio: float = 0.1,
    done_ratio: float = 0.1,
    fragmented: bool = False,
    inject_cycle: bool = False,
) -> Workload:
    rng = random.Random(seed)
    spread = 8 * 60 if tightness == "tight" else 3 * 1440
    ids = [f"T{i:05d}" for i in range(n)]
    entry = list(range(n))
    rng.shuffle(entry)   # entry order is unrelated to deadlines

    tasks: dict[str, Task] = {}
    demand = 0
    for i, tid in enumerate(ids):
        prereqs: list[str] = []
        if i:
            k = min(i, _poisson(rng, dep_density))
            # Prefer recent vertices so chains look like campaign pipelines.
            window = ids[max(0, i - 20):i]
            prereqs = rng.sample(window, min(k, len(window)))
        if rng.random() < gate_ratio:
            status = PENDING if rng.random() < pending_gates else DONE
            tasks[tid] = Task(tid, f"Gate {i}", kind=GATE, status=status,
                              prereqs=prereqs, entry_order=entry[i])
            continue
        hi = rng.choice((30, 60, 60, 90, 120, 180, 240))
        lo = max(15, int(hi * rng.uniform(0.4, 0.9)) // 15 * 15)
        status = DONE if rng.random() < done_ratio else PENDING
        deadline = DAY_START + hi + rng.randint(0, spread)
        tasks[tid] = Task(
            tid, f"Task {i}", skill=rng.choice(SKILLS), effort_min=lo, effort_max=hi,
            deadline=deadline, status=status, prereqs=prereqs, entry_order=entry[i],
            urgency=URGENT if rng.random() < urgent_ratio else "normal")
        if status != DONE:
            demand += hi

    if inject_cycle and n >= 2:
        a, b = ids[0], ids[-1]
        # a <-> b: each lists the other as a prerequisite (a 2-cycle).
        tasks[a].prereqs.append(b)
        tasks[b].prereqs.append(a)

    per_person = (DAY_END - DAY_START) - (LUNCH[1] - LUNCH[0])
    n_staff = max(len(SKILLS), math.ceil(demand / (max(load, 0.05) * per_person)))
    staff: list[Staff] = []
    for j in range(n_staff):
        skills = {SKILLS[j % len(SKILLS)]}
        if rng.random() < 0.3:
            skills.add(rng.choice(SKILLS))
        exceptions = [LUNCH]
        if fragmented:
            for _ in range(rng.randint(1, 3)):
                s = rng.randrange(DAY_START, DAY_END - 30, 15)
                exceptions.append((s, s + rng.choice((15, 30, 60))))
        staff.append(Staff(f"S{j:04d}", f"Staff {j}", skills,
                           windows=[(DAY_START, DAY_END)], exceptions=exceptions))
    return Workload(tasks, staff, seed)


def _poisson(rng: random.Random, lam: float) -> int:
    # Knuth's method; lam is small here.
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1
