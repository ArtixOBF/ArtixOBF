"""Operations on sorted lists of disjoint half-open time intervals [start, end).

A staff member's free time for the day is represented this way. Lists are
kept sorted by start and non-overlapping so every operation is a single
linear scan.

Complexities, with w = number of intervals:
    normalize      O(w log w)  (sort, then merge)
    subtract       O(w + c log c) for c cuts
    earliest_fit   O(w)
    reserve        O(w)
"""

from __future__ import annotations

from typing import Iterable, Optional

Interval = tuple[int, int]


def normalize(intervals: Iterable[Interval]) -> list[Interval]:
    """Sort, drop empty intervals, and merge overlapping/touching ones."""
    out: list[Interval] = []
    for s, e in sorted(i for i in intervals if i[1] > i[0]):
        if out and s <= out[-1][1]:
            if e > out[-1][1]:
                out[-1] = (out[-1][0], e)
        else:
            out.append((s, e))
    return out


def subtract(free: list[Interval], cuts: Iterable[Interval]) -> list[Interval]:
    """Remove every cut interval from `free` (both normalized on the way in)."""
    cuts = normalize(cuts)
    result: list[Interval] = []
    j = 0
    for s, e in normalize(free):
        # Skip cuts that end before this interval starts.
        while j < len(cuts) and cuts[j][1] <= s:
            j += 1
        k = j
        cur = s
        while k < len(cuts) and cuts[k][0] < e:
            cs, ce = cuts[k]
            if cs > cur:
                result.append((cur, cs))
            cur = max(cur, ce)
            if cur >= e:
                break
            k += 1
        if cur < e:
            result.append((cur, e))
    return result


def earliest_fit(free: list[Interval], earliest: int, length: int) -> Optional[int]:
    """Earliest start >= `earliest` with `length` continuous free minutes."""
    for s, e in free:
        start = max(s, earliest)
        if start + length <= e:
            return start
    return None


def reserve(free: list[Interval], start: int, end: int) -> list[Interval]:
    """Return `free` with [start, end) removed. The range must lie in one interval."""
    out: list[Interval] = []
    for s, e in free:
        if s <= start and end <= e:
            if s < start:
                out.append((s, start))
            if end < e:
                out.append((end, e))
        else:
            out.append((s, e))
    return out


def total(free: Iterable[Interval]) -> int:
    return sum(e - s for s, e in free)
