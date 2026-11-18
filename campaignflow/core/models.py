"""Plain data records used by the CampaignFlow engine.

All times inside the engine are integer minutes measured from 00:00 of the
planning day. A deadline on a later day is simply a value above 1440. Using
integers avoids floating-point drift when windows are split and compared.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

URGENT = "urgent"
NORMAL = "normal"

TASK = "task"   # single-person writing/editing work the engine may allocate
GATE = "gate"   # external step (filming, client approval) confirmed by the manager

PENDING = "pending"
DONE = "done"   # for gates this means "confirmed"


@dataclass
class Task:
    """A unit of production work or an external gate.

    effort_min / effort_max are minutes. Capacity checks always reserve
    effort_max (the conservative upper estimate). effort_max is None when the
    manager has not confirmed an estimate yet; such tasks are never proposed.
    """

    id: str
    name: str
    kind: str = TASK
    skill: Optional[str] = None
    effort_min: Optional[int] = None
    effort_max: Optional[int] = None
    deadline: Optional[int] = None
    urgency: str = NORMAL
    status: str = PENDING
    prereqs: list[str] = field(default_factory=list)
    entry_order: int = 0
    campaign: str = ""

    @property
    def is_gate(self) -> bool:
        return self.kind == GATE

    @property
    def is_done(self) -> bool:
        return self.status == DONE


@dataclass
class Staff:
    """An employee with skills and confirmed working windows for the day.

    windows: recurring working hours, e.g. [(540, 1080)] for 09:00-18:00.
    exceptions: meetings or absences that remove time from those windows.
    availability_confirmed: False means the manager has not reviewed today's
    availability, so the engine will not propose work for this person.
    """

    id: str
    name: str
    skills: set[str] = field(default_factory=set)
    windows: list[tuple[int, int]] = field(default_factory=list)
    exceptions: list[tuple[int, int]] = field(default_factory=list)
    availability_confirmed: bool = True


@dataclass(frozen=True)
class Commitment:
    """An assignment the manager has accepted. Locked commitments never move."""

    task_id: str
    staff_id: str
    start: int
    end: int


@dataclass
class Assignment:
    """A proposed (not yet accepted) placement produced by the allocator."""

    task_id: str
    staff_id: str
    start: int
    end: int
    at_risk: bool = False   # finishes after the deadline under the upper estimate


@dataclass
class Blocked:
    """A task the allocator could not place, with a human-readable reason."""

    task_id: str
    category: str   # "blocked" | "missing_info" | "capacity" | "no_staff"
    reason: str


@dataclass
class Plan:
    """The full allocator output."""

    assignments: list[Assignment] = field(default_factory=list)
    blocked: list[Blocked] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)   # validation failures
    policy: str = ""

    def assignment_for(self, task_id: str) -> Optional[Assignment]:
        for a in self.assignments:
            if a.task_id == task_id:
                return a
        return None


def hhmm(minutes: Optional[int]) -> str:
    """Format engine minutes as HH:MM (with a +Nd suffix for later days)."""
    if minutes is None:
        return "-"
    day, rem = divmod(int(minutes), 1440)
    text = f"{rem // 60:02d}:{rem % 60:02d}"
    if day == 0:
        return text
    return f"{text} {'+' if day > 0 else ''}{day}d"


def parse_hhmm(text: str) -> int:
    """Parse 'HH:MM' into minutes since midnight."""
    hours, mins = text.strip().split(":")
    h, m = int(hours), int(mins)
    if not (0 <= h <= 24 and 0 <= m < 60) or h * 60 + m > 1440:
        raise ValueError(f"invalid time {text!r}")
    return h * 60 + m
