"""CampaignFlow scheduling engine (no third-party dependencies)."""

from .allocator import allocate
from .graph import DiGraph
from .heap import MinHeap
from .invariants import check_plan
from .models import (
    DONE, GATE, NORMAL, PENDING, TASK, URGENT,
    Assignment, Blocked, Commitment, Plan, Staff, Task, hhmm, parse_hhmm,
)
from .validate import validate

__all__ = [
    "allocate", "check_plan", "validate", "DiGraph", "MinHeap",
    "Task", "Staff", "Commitment", "Assignment", "Blocked", "Plan",
    "TASK", "GATE", "PENDING", "DONE", "URGENT", "NORMAL", "hhmm", "parse_hhmm",
]
