"""Input validation that must pass before any allocation is proposed.

Hard errors (unknown prerequisites, circular dependencies, invalid effort
ranges, conflicting commitments) stop the allocator entirely, because a
schedule built on them could not be trusted. Missing estimates or unconfirmed
availability are *not* hard errors; they only hold back the affected tasks.

Cost: O(V + E) for the graph checks plus O(C log C) to sort commitments.
"""

from __future__ import annotations

from .graph import DiGraph
from .models import Commitment, Staff, Task, hhmm
from . import windows as W


def build_graph(tasks: dict[str, Task]) -> DiGraph:
    g = DiGraph()
    for tid in tasks:
        g.add_vertex(tid)
    for t in tasks.values():
        for p in t.prereqs:
            if p in tasks:
                g.add_edge(p, t.id)
    return g


def validate(
    tasks: dict[str, Task],
    staff: list[Staff],
    commitments: list[Commitment],
) -> list[str]:
    errors: list[str] = []

    for t in tasks.values():
        for p in t.prereqs:
            if p not in tasks:
                errors.append(f"{t.id} lists unknown prerequisite {p!r}.")
            # A self-link is reported by the cycle check below as T → T.
        if t.effort_min is not None and t.effort_min < 0:
            errors.append(f"{t.id} has a negative effort estimate.")
        if t.effort_max is not None and t.effort_max <= 0 and not t.is_gate:
            errors.append(f"{t.id} has a non-positive upper effort estimate.")
        if (t.effort_min is not None and t.effort_max is not None
                and t.effort_min > t.effort_max):
            errors.append(f"{t.id} has an effort range whose minimum exceeds its maximum.")

    graph = build_graph(tasks)
    cycle = graph.find_cycle()
    if cycle:
        names = " → ".join(f"{tasks[v].name} ({v})" for v in cycle)
        errors.append(f"Circular dependency: {names}. Remove one of these links.")

    errors.extend(_check_commitments(tasks, staff, commitments))
    return errors


def _check_commitments(tasks, staff, commitments) -> list[str]:
    errors: list[str] = []
    staff_by_id = {s.id: s for s in staff}
    seen_tasks: set[str] = set()
    by_staff: dict[str, list[Commitment]] = {}

    for c in commitments:
        t = tasks.get(c.task_id)
        s = staff_by_id.get(c.staff_id)
        label = f"Commitment {c.task_id} → {c.staff_id} ({hhmm(c.start)}–{hhmm(c.end)})"
        if t is None:
            errors.append(f"{label} refers to an unknown task.")
            continue
        if s is None:
            errors.append(f"{label} refers to an unknown staff member.")
            continue
        if t.is_gate:
            errors.append(f"{label} assigns an external gate to staff.")
        if c.task_id in seen_tasks:
            errors.append(f"{label} duplicates another commitment for the same task.")
        seen_tasks.add(c.task_id)
        if t.skill and t.skill not in s.skills:
            errors.append(f"{label}: {s.name} lacks the '{t.skill}' skill.")
        if c.end <= c.start:
            errors.append(f"{label} has an empty or reversed time range.")
        available = W.subtract(s.windows, s.exceptions)
        if not any(a <= c.start and c.end <= b for a, b in available):
            errors.append(f"{label} falls outside {s.name}'s available hours "
                          f"(check meetings or absences).")
        by_staff.setdefault(c.staff_id, []).append(c)

    for sid, items in by_staff.items():
        items.sort(key=lambda c: c.start)
        for a, b in zip(items, items[1:]):
            if b.start < a.end:
                errors.append(f"Commitments {a.task_id} and {b.task_id} overlap "
                              f"for {staff_by_id[sid].name}.")
    return errors
