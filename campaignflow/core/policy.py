"""Priority policies: each one is just a heap key function.

The allocator is identical for every policy; only the order in which ready
tasks leave the heap changes. That isolates the effect of the ordering rule
when the deadline policy is compared with the entry-order baseline.
"""

from __future__ import annotations

from typing import Callable

from .models import URGENT, Task

NO_DEADLINE = 10**9


def _urgency_rank(t: Task) -> int:
    return 0 if t.urgency == URGENT else 1


def deadline_key(t: Task):
    """Urgent before normal, then earliest deadline, then task ID."""
    return (_urgency_rank(t), t.deadline if t.deadline is not None else NO_DEADLINE, t.id)


def entry_order_key(t: Task):
    """Baseline: urgent before normal, then the order tasks were entered."""
    return (_urgency_rank(t), t.entry_order, t.id)


POLICIES: dict[str, Callable[[Task], tuple]] = {
    "deadline": deadline_key,
    "entry": entry_order_key,
}

POLICY_LABELS = {
    "deadline": "Deadline-first (CampaignFlow)",
    "entry": "Entry order (baseline)",
}
