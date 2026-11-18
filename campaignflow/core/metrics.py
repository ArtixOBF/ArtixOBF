"""Outcome metrics for comparing policies on identical inputs.

summarize()  - projected outcomes under upper estimates.
replay()     - re-time the accepted order with "actual" durations to compare
               realized lateness, as the proposal's evaluation describes.
"""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass

from .models import Plan, Task


@dataclass
class Summary:
    policy: str
    allocated: int
    on_time: int
    at_risk: int
    blocked: int
    capacity: int
    missing_info: int
    no_staff: int
    total_lateness: int        # minutes past deadline, summed (upper estimates)
    unmet_demand: int          # minutes of ready work that could not be placed
    utilised_minutes: int

    @property
    def on_time_rate(self) -> float:
        with_deadline = self.on_time + self.at_risk
        return self.on_time / with_deadline if with_deadline else 1.0


def summarize(tasks: dict[str, Task], plan: Plan) -> Summary:
    lateness = 0
    on_time = at_risk = 0
    used = 0
    for a in plan.assignments:
        t = tasks[a.task_id]
        used += a.end - a.start
        if t.deadline is None:
            continue
        if a.end > t.deadline:
            at_risk += 1
            lateness += a.end - t.deadline
        else:
            on_time += 1
    cats = Counter(b.category for b in plan.blocked)
    unmet = sum(tasks[b.task_id].effort_max or 0
                for b in plan.blocked if b.category == "capacity")
    return Summary(plan.policy, len(plan.assignments), on_time, at_risk,
                   cats["blocked"], cats["capacity"], cats["missing_info"],
                   cats["no_staff"], lateness, unmet, used)


def replay(tasks: dict[str, Task], plan: Plan, seed: int, error: float = 0.0):
    """Re-time each staff member's sequence with sampled actual durations.

    Actual duration ~ Uniform(effort_min, effort_max) scaled by (1 + error),
    so error > 0 models estimates that were too optimistic. Work keeps its
    planned order and never starts before its planned start or before its
    (re-timed) prerequisites finish. Returns (late_count, total_lateness).
    """
    rng = random.Random(seed)
    actual_end: dict[str, int] = {}
    order = sorted(plan.assignments, key=lambda a: a.start)
    staff_free: dict[str, int] = {}
    late = lateness = 0
    for a in order:
        t = tasks[a.task_id]
        lo = t.effort_min if t.effort_min is not None else t.effort_max
        dur = round(rng.uniform(lo, t.effort_max) * (1 + error))
        start = max(a.start, staff_free.get(a.staff_id, 0))
        for p in t.prereqs:
            start = max(start, actual_end.get(p, 0))
        end = start + dur
        actual_end[a.task_id] = end
        staff_free[a.staff_id] = end
        if t.deadline is not None and end > t.deadline:
            late += 1
            lateness += end - t.deadline
    return late, lateness
