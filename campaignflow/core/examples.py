"""The worked example from the proposal (Section 3.1, Table 1)."""

from __future__ import annotations

from .models import GATE, PENDING, Staff, Task


def table1():
    tasks = {
        "T1": Task("T1", "Edit A", skill="editing", effort_min=60, effort_max=120,
                   deadline=12 * 60, entry_order=1),
        "T2": Task("T2", "Edit B", skill="editing", effort_min=30, effort_max=60,
                   deadline=10 * 60, entry_order=2),
        "G1": Task("G1", "Film C", kind=GATE, status=PENDING, entry_order=3),
        "T4": Task("T4", "Edit C", skill="editing", effort_min=30, effort_max=60,
                   deadline=13 * 60, prereqs=["G1"], entry_order=4),
    }
    staff = [Staff("E1", "Editor", {"editing"}, windows=[(9 * 60, 12 * 60)])]
    return tasks, staff
