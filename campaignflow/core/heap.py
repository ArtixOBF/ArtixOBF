"""Array-backed binary min-heap used as the priority queue of ready tasks.

Implemented by hand (no heapq) so the sift operations and their costs are
explicit. Each entry is stored as (key, item); keys are compared with `<`
only, so any tuple key such as (urgency_rank, deadline, task_id) works.

Complexities, with n = number of entries:
    push      O(log n)  (amortized: the Python list may resize)
    pop       O(log n)
    peek      O(1)
    heapify   O(n)      bottom-up construction
Space: O(n).
"""

from __future__ import annotations

from typing import Any, Callable, Generic, Iterable, TypeVar

T = TypeVar("T")


class MinHeap(Generic[T]):
    def __init__(self, key: Callable[[T], Any], items: Iterable[T] = ()):
        self._key = key
        self._data: list[tuple[Any, T]] = [(key(x), x) for x in items]
        self._heapify()

    # ----- public API -------------------------------------------------
    def __len__(self) -> int:
        return len(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)

    def push(self, item: T) -> None:
        self._data.append((self._key(item), item))
        self._sift_up(len(self._data) - 1)

    def peek(self) -> T:
        if not self._data:
            raise IndexError("peek from empty heap")
        return self._data[0][1]

    def pop(self) -> T:
        if not self._data:
            raise IndexError("pop from empty heap")
        last = self._data.pop()
        if not self._data:
            return last[1]
        top = self._data[0]
        self._data[0] = last
        self._sift_down(0)
        return top[1]

    # ----- internals --------------------------------------------------
    def _heapify(self) -> None:
        # Leaves are already heaps; sift down every internal node, last first.
        for i in range(len(self._data) // 2 - 1, -1, -1):
            self._sift_down(i)

    def _sift_up(self, i: int) -> None:
        data = self._data
        entry = data[i]
        while i > 0:
            parent = (i - 1) // 2
            if entry[0] < data[parent][0]:
                data[i] = data[parent]
                i = parent
            else:
                break
        data[i] = entry

    def _sift_down(self, i: int) -> None:
        data = self._data
        n = len(data)
        entry = data[i]
        while True:
            child = 2 * i + 1
            if child >= n:
                break
            right = child + 1
            if right < n and data[right][0] < data[child][0]:
                child = right
            if data[child][0] < entry[0]:
                data[i] = data[child]
                i = child
            else:
                break
        data[i] = entry

    def is_valid(self) -> bool:
        """Check the heap property (used by tests)."""
        d = self._data
        return all(not (d[i][0] < d[(i - 1) // 2][0]) for i in range(1, len(d)))
