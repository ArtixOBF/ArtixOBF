"""Independent checker for hard scheduling constraints.

This module deliberately does not reuse the allocator's bookkeeping. It
re-derives every rule from the raw inputs, so a bug in the allocator cannot
hide itself. Every generated workload in tests and benchmarks passes through
check_plan(); a correct allocator must always return an empty list.
"""

from __future__ import annotations

from . import windows as W
from .models import Commitment, Plan, Staff, Task


def check_plan(
    tasks: dict[str, Task],
    staff: list[Staff],
    commitments: list[Commitment],
    plan: Plan,
    now: int = 0,
    same_day_release: bool = True,
) -> list[str]:
    v: list[str] = []
    staff_by_id = {s.id: s for s in staff}
    committed = {c.task_id: c for c in commitments}
    placed: dict[str, tuple[int, int]] = {c.task_id: (c.start, c.end) for c in commitments}

    seen: set[str] = set()
    for a in plan.assignments:
        t = tasks.get(a.task_id)
        s = staff_by_id.get(a.staff_id)
        if t is None or s is None:
            v.append(f"{a.task_id}: unknown task or staff")
            continue
        if a.task_id in seen:
            v.append(f"{a.task_id}: assigned more than once")
        seen.add(a.task_id)
        if a.task_id in committed:
            v.append(f"{a.task_id}: locked commitment was re-proposed")
        if t.is_gate:
            v.append(f"{a.task_id}: external gate assigned to staff")
        if t.is_done:
            v.append(f"{a.task_id}: completed task re-assigned")
        if t.skill not in s.skills:
            v.append(f"{a.task_id}: skill mismatch ({t.skill} not in {s.name})")
        if not s.availability_confirmed:
            v.append(f"{a.task_id}: staff availability not confirmed")
        if t.effort_max is None or a.end - a.start != t.effort_max:
            v.append(f"{a.task_id}: reserved time differs from upper estimate")
        if a.start < now:
            v.append(f"{a.task_id}: starts in the past")
        placed[a.task_id] = (a.start, a.end)

    # Each placement must lie inside working hours minus meetings/absences.
    for a in plan.assignments:
        s = staff_by_id.get(a.staff_id)
        if s is None:
            continue
        avail = W.subtract(s.windows, s.exceptions)
        if not any(x <= a.start and a.end <= y for x, y in avail):
            v.append(f"{a.task_id}: outside {s.name}'s available hours")

    # No two pieces of work (proposed or committed) overlap for one person.
    per_staff: dict[str, list[tuple[int, int, str]]] = {}
    for c in commitments:
        per_staff.setdefault(c.staff_id, []).append((c.start, c.end, c.task_id))
    for a in plan.assignments:
        per_staff.setdefault(a.staff_id, []).append((a.start, a.end, a.task_id))
    for sid, items in per_staff.items():
        items.sort()
        for (s1, e1, t1), (s2, e2, t2) in zip(items, items[1:]):
            if s2 < e1:
                v.append(f"overlap for {sid}: {t1} and {t2}")

    # Prerequisites must be finished (or, with same-day release, planned to
    # finish before the dependent task starts). Pending gates never qualify.
    for a in plan.assignments:
        t = tasks.get(a.task_id)
        if t is None:
            continue
        for p in t.prereqs:
            pt = tasks[p]
            if pt.is_done:
                continue
            if pt.is_gate:
                v.append(f"{a.task_id}: started before gate {p} was confirmed")
            elif not same_day_release:
                v.append(f"{a.task_id}: prerequisite {p} not completed")
            elif p not in placed or placed[p][1] > a.start:
                v.append(f"{a.task_id}: starts before prerequisite {p} finishes")
    return v
