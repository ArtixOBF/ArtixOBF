"""Unit tests for the hand-written data structures."""

import heapq
import random
import sys

import pytest

from campaignflow.core.graph import DiGraph
from campaignflow.core.heap import MinHeap
from campaignflow.core import windows as W


# ---------------------------------------------------------------- heap
def test_heap_matches_heapq_on_random_operations():
    rng = random.Random(7)
    ours = MinHeap(key=lambda x: x)
    ref: list[int] = []
    for _ in range(5000):
        if ref and rng.random() < 0.4:
            assert ours.pop() == heapq.heappop(ref)
        else:
            x = rng.randint(-1000, 1000)
            ours.push(x)
            heapq.heappush(ref, x)
        assert len(ours) == len(ref)
        assert ours.is_valid()
    assert [ours.pop() for _ in range(len(ours))] == sorted(ref)


def test_heapify_builds_valid_heap_and_sorts():
    rng = random.Random(3)
    data = [rng.random() for _ in range(1000)]
    h = MinHeap(key=lambda x: x, items=data)
    assert h.is_valid()
    assert [h.pop() for _ in range(len(data))] == sorted(data)


def test_heap_tuple_keys_break_ties_by_id():
    items = [("b", 5), ("a", 5), ("c", 1)]
    h = MinHeap(key=lambda t: (t[1], t[0]), items=items)
    assert [h.pop()[0] for _ in range(3)] == ["c", "a", "b"]


def test_heap_empty_errors():
    h = MinHeap(key=lambda x: x)
    with pytest.raises(IndexError):
        h.pop()
    with pytest.raises(IndexError):
        h.peek()
    assert not h


# ---------------------------------------------------------------- graph
def _graph(edges):
    g = DiGraph()
    for u, v in edges:
        g.add_edge(u, v)
    return g


def test_acyclic_graph_has_no_cycle():
    g = _graph([("a", "b"), ("b", "c"), ("a", "c")])
    assert g.find_cycle() is None


def test_diamond_is_not_a_cycle():
    # d is reached twice; the second visit sees it BLACK, not GRAY.
    g = _graph([("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")])
    assert g.find_cycle() is None


def test_cycle_path_is_reported():
    g = _graph([("a", "b"), ("b", "c"), ("c", "a"), ("x", "a")])
    cyc = g.find_cycle()
    assert cyc[0] == cyc[-1]
    assert set(cyc) == {"a", "b", "c"}
    for u, v in zip(cyc, cyc[1:]):
        assert v in g.successors(u)


def test_self_loop_is_cycle():
    g = _graph([("a", "a")])
    assert g.find_cycle() == ["a", "a"]


def test_long_chain_does_not_recurse():
    n = sys.getrecursionlimit() * 5
    g = _graph([(i, i + 1) for i in range(n)])
    assert g.find_cycle() is None
    g.add_edge(n, 0)
    assert len(g.find_cycle()) == n + 2


def test_downstream():
    g = _graph([("a", "b"), ("b", "c"), ("x", "y")])
    assert set(g.downstream("a")) == {"b", "c"}
    assert g.downstream("c") == []


# ---------------------------------------------------------------- windows
def test_subtract_basic_and_edges():
    assert W.subtract([(540, 1080)], [(720, 780)]) == [(540, 720), (780, 1080)]
    assert W.subtract([(540, 1080)], [(0, 600), (1000, 2000)]) == [(600, 1000)]
    assert W.subtract([(540, 600)], [(540, 600)]) == []
    assert W.subtract([(0, 100), (200, 300)], [(50, 250)]) == [(0, 50), (250, 300)]
    assert W.subtract([(0, 100)], []) == [(0, 100)]


def test_subtract_matches_bruteforce():
    rng = random.Random(11)
    for _ in range(300):
        free = [(a, a + rng.randint(1, 40)) for a in rng.sample(range(0, 200), 5)]
        cuts = [(a, a + rng.randint(1, 30)) for a in rng.sample(range(0, 200), 4)]
        minutes = {m for s, e in free for m in range(s, e)} - {m for s, e in cuts for m in range(s, e)}
        got = W.subtract(free, cuts)
        assert {m for s, e in got for m in range(s, e)} == minutes
        assert all(a[1] < b[0] for a, b in zip(got, got[1:]))   # disjoint, merged


def test_earliest_fit_and_reserve():
    free = [(540, 600), (660, 900)]
    assert W.earliest_fit(free, 540, 60) == 540
    assert W.earliest_fit(free, 541, 60) == 660    # first piece too short now
    assert W.earliest_fit(free, 540, 300) is None  # no continuous slot
    assert W.reserve(free, 700, 760) == [(540, 600), (660, 700), (760, 900)]
