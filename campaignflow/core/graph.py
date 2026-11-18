"""Directed dependency graph stored as adjacency lists, plus DFS cycle detection.

An edge u -> v means "u is a prerequisite of v" (e.g. Filming -> Editing).
Both directions are stored so the engine can ask for successors (who is
released when u finishes) and predecessors (what v is waiting on) in time
proportional to the answer.

Complexities, with V vertices and E edges:
    add_vertex / add_edge     O(1)
    successors / predecessors O(1) to return the list
    find_cycle                O(V + E) time, O(V) extra space
    downstream                O(V + E)
Space: O(V + E).
"""

from __future__ import annotations

from typing import Iterable, Optional

WHITE, GRAY, BLACK = 0, 1, 2   # unvisited, active (on the DFS path), finished


class DiGraph:
    def __init__(self) -> None:
        self._succ: dict[str, list[str]] = {}
        self._pred: dict[str, list[str]] = {}

    def add_vertex(self, v: str) -> None:
        if v not in self._succ:
            self._succ[v] = []
            self._pred[v] = []

    def add_edge(self, u: str, v: str) -> None:
        self.add_vertex(u)
        self.add_vertex(v)
        self._succ[u].append(v)
        self._pred[v].append(u)

    def __contains__(self, v: str) -> bool:
        return v in self._succ

    def __len__(self) -> int:
        return len(self._succ)

    def vertices(self) -> Iterable[str]:
        return self._succ.keys()

    def successors(self, v: str) -> list[str]:
        return self._succ[v]

    def predecessors(self, v: str) -> list[str]:
        return self._pred[v]

    def edge_count(self) -> int:
        return sum(len(s) for s in self._succ.values())

    # ----- algorithms -------------------------------------------------
    def find_cycle(self) -> Optional[list[str]]:
        """Return one directed cycle as [v0, v1, ..., v0], or None if acyclic.

        Iterative DFS with an explicit stack of (vertex, next-child-index)
        frames, so deep dependency chains cannot hit Python's recursion limit.
        A vertex is GRAY while it is on the current path and turns BLACK only
        after all of its successors have been explored. Reaching a GRAY vertex
        again means we followed an edge back into the current path: a cycle.
        """
        color = {v: WHITE for v in self._succ}
        parent: dict[str, Optional[str]] = {}

        for root in self._succ:
            if color[root] != WHITE:
                continue
            color[root] = GRAY
            parent[root] = None
            stack: list[list] = [[root, 0]]
            while stack:
                frame = stack[-1]
                v, idx = frame
                children = self._succ[v]
                if idx < len(children):
                    frame[1] = idx + 1
                    w = children[idx]
                    if color[w] == WHITE:
                        color[w] = GRAY
                        parent[w] = v
                        stack.append([w, 0])
                    elif color[w] == GRAY:
                        return self._build_cycle(parent, v, w)
                    # BLACK: already fully explored, no cycle through it.
                else:
                    color[v] = BLACK
                    stack.pop()
        return None

    @staticmethod
    def _build_cycle(parent: dict, tail: str, head: str) -> list[str]:
        """Walk parents from `tail` back to `head` to recover the cycle path."""
        path = [tail]
        while path[-1] != head:
            path.append(parent[path[-1]])
        path.reverse()
        path.append(head)
        return path

    def downstream(self, v: str) -> list[str]:
        """All vertices reachable from v (tasks affected if v slips)."""
        seen = {v}
        order: list[str] = []
        stack = [v]
        while stack:
            u = stack.pop()
            for w in self._succ[u]:
                if w not in seen:
                    seen.add(w)
                    order.append(w)
                    stack.append(w)
        return order
