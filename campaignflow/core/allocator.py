"""Greedy priority-based allocation of ready tasks to qualified staff.

This is a serial schedule-generation scheme: tasks are taken one at a time
from a priority queue (min-heap) and each is placed in the earliest feasible
continuous window of a qualified staff member. Tasks that cannot be placed
are labelled with a reason and skipped, so lower-priority work can still use
the remaining capacity.

Readiness rules
    * A task is ready when every prerequisite is resolved.
    * A DONE task or a CONFIRMED gate resolves immediately (release time = now).
    * A pending external gate never resolves: dependent work waits for the
      manager to confirm it. Expected approval dates are ignored.
    * With same_day_release=True, an internal task that is committed or
      proposed today resolves at its planned finish, so a successor may start
      after that time on the same day. With False, only completed work counts.

Complexity, with n tasks, e dependency edges, s staff, w free intervals per
staff:
    validation        O(n + e)
    heap operations   O(n log n)  (each task pushed and popped at most once)
    window search     O(n * s * w) worst case
    total             O(n log n + e + n*s*w) time, O(n + e + s*w) space

Two pruning rules (prune=True) leave the result unchanged but cut the
average cost of the window search: staff whose longest free block is shorter
than the task are skipped in O(1), and the scan stops at the first person (in
tie-break order) who can start at the earliest possible time.
"""

from __future__ import annotations

from typing import Optional

from . import windows as W
from .heap import MinHeap
from .models import (
    Assignment, Blocked, Commitment, Plan, Staff, Task, hhmm,
)
from .policy import POLICIES
from .validate import build_graph, validate


def _fmt_hours(minutes: int) -> str:
    h = minutes / 60
    return f"{h:g}h"


def free_windows(s: Staff, commitments: list[Commitment], now: int) -> list[W.Interval]:
    """Working windows minus meetings/absences, existing commitments, and the past."""
    busy = list(s.exceptions)
    busy.extend((c.start, c.end) for c in commitments if c.staff_id == s.id)
    busy.append((0, now))
    return W.subtract(s.windows, busy)


def allocate(
    tasks: dict[str, Task],
    staff: list[Staff],
    commitments: Optional[list[Commitment]] = None,
    policy: str = "deadline",
    now: int = 0,
    same_day_release: bool = True,
    skip_validation: bool = False,
    prune: bool = True,
) -> Plan:
    commitments = list(commitments or [])
    plan = Plan(policy=policy)

    if not skip_validation:
        plan.errors = validate(tasks, staff, commitments)
        if plan.errors:
            return plan

    key = POLICIES[policy]
    graph = build_graph(tasks)
    committed = {c.task_id: c for c in commitments}

    free = {s.id: free_windows(s, commitments, now) for s in staff}
    # Longest continuous free block per person: an O(1) test that lets the
    # search skip anyone who cannot possibly fit the task.
    longest = {sid: max((e - b for b, e in iv), default=0) for sid, iv in free.items()}

    # Pre-group staff by skill, sorted in tie-break order (fewer skills, then
    # ID), so each task scans only qualified, confirmed people.
    by_skill: dict[str, list[Staff]] = {}
    confirmed_by_skill: dict[str, list[Staff]] = {}
    for s in sorted(staff, key=lambda s: (len(s.skills), s.id)):
        for sk in s.skills:
            by_skill.setdefault(sk, []).append(s)
            if s.availability_confirmed:
                confirmed_by_skill.setdefault(sk, []).append(s)

    unresolved = {tid: 0 for tid in tasks}
    release = {tid: now for tid in tasks}
    for tid in tasks:
        for p in graph.predecessors(tid):
            if not tasks[p].is_done:
                unresolved[tid] += 1

    def is_candidate(t: Task) -> bool:
        return not t.is_gate and not t.is_done and t.id not in committed

    def resolve(tid: str, finish: int) -> None:
        """Mark `tid` as finishing at `finish` and release successors that become ready."""
        for v in graph.successors(tid):
            unresolved[v] -= 1
            if finish > release[v]:
                release[v] = finish
            if unresolved[v] == 0 and is_candidate(tasks[v]):
                heap.push(tasks[v])

    # Initial ready set, built in O(n) with bottom-up heapify. `resolve`
    # (defined above) pushes later arrivals into this same heap.
    heap: MinHeap[Task] = MinHeap(key, (t for t in tasks.values()
                         if is_candidate(t) and unresolved[t.id] == 0))

    if same_day_release:
        for c in commitments:
            # Done tasks were already excluded from `unresolved` above.
            if not tasks[c.task_id].is_done:
                resolve(c.task_id, c.end)

    handled: set[str] = set()
    while heap:
        t = heap.pop()
        handled.add(t.id)

        if not t.skill:
            plan.blocked.append(Blocked(t.id, "missing_info", "No required skill set."))
            continue
        if t.effort_max is None:
            plan.blocked.append(Blocked(t.id, "missing_info",
                                        "Needs a confirmed effort estimate."))
            continue
        qualified = by_skill.get(t.skill, [])
        if not qualified:
            plan.blocked.append(Blocked(t.id, "no_staff",
                                        f"No staff member has the '{t.skill}' skill."))
            continue
        confirmed = confirmed_by_skill.get(t.skill, [])
        if not confirmed:
            names = ", ".join(s.name for s in qualified)
            plan.blocked.append(Blocked(t.id, "missing_info",
                                        f"Availability not confirmed today for: {names}."))
            continue

        earliest = release[t.id]
        best = None   # (finish, skill_count, staff_id, start)
        for s in confirmed:
            if prune and longest[s.id] < t.effort_max:
                continue
            start = W.earliest_fit(free[s.id], earliest, t.effort_max)
            if start is None:
                continue
            cand = (start + t.effort_max, len(s.skills), s.id, start)
            if best is None or cand < best:
                best = cand
                # Staff are scanned in tie-break order, so once someone can
                # start at the earliest possible moment nobody later can win.
                if prune and start == earliest:
                    break

        if best is None:
            after = f" after {hhmm(earliest)}" if earliest > now else ""
            plan.blocked.append(Blocked(
                t.id, "capacity",
                f"No continuous {_fmt_hours(t.effort_max)} slot{after} "
                f"for qualified staff."))
            continue

        finish, _, sid, start = best
        free[sid] = W.reserve(free[sid], start, finish)
        longest[sid] = max((e - b for b, e in free[sid]), default=0)
        at_risk = t.deadline is not None and finish > t.deadline
        plan.assignments.append(Assignment(t.id, sid, start, finish, at_risk))
        if same_day_release:
            resolve(t.id, finish)

    # Explain every candidate that never became ready.
    assigned = {a.task_id for a in plan.assignments}
    for t in tasks.values():
        if is_candidate(t) and t.id not in handled:
            plan.blocked.append(Blocked(t.id, "blocked",
                                        _waiting_reason(t, tasks, graph, committed, assigned)))
    return plan


def _waiting_reason(t, tasks, graph, committed, assigned) -> str:
    parts = []
    for p in graph.predecessors(t.id):
        pt = tasks[p]
        if pt.is_done:
            continue
        if pt.is_gate:
            parts.append(f"awaiting {pt.name} (external, unconfirmed)")
        elif p in committed or p in assigned:
            parts.append(f"waiting for {pt.name} to be completed")
        else:
            parts.append(f"waiting on {pt.name} (not scheduled today)")
    if not parts:
        return "Not ready."
    text = "; ".join(parts)
    return text[0].upper() + text[1:] + "."
