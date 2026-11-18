"""Behavioural tests for validation and greedy allocation."""

import copy

import pytest

from campaignflow.bench.generator import generate
from campaignflow.core import (
    DONE, GATE, URGENT, Commitment, Staff, Task, allocate, check_plan, hhmm,
)
from campaignflow.core.examples import table1
from campaignflow.core.metrics import replay, summarize

H = 60


def _slots(plan):
    return [(a.task_id, a.staff_id, hhmm(a.start), hhmm(a.end)) for a in plan.assignments]


def _reason(plan, tid):
    return next(b for b in plan.blocked if b.task_id == tid)


# ------------------------------------------------- the proposal's example
def test_table1_deadline_policy_matches_proposal():
    tasks, staff = table1()
    plan = allocate(tasks, staff, policy="deadline")
    assert _slots(plan) == [("T2", "E1", "09:00", "10:00"), ("T1", "E1", "10:00", "12:00")]
    assert not any(a.at_risk for a in plan.assignments)
    assert "Film C" in _reason(plan, "T4").reason
    assert check_plan(tasks, staff, [], plan) == []


def test_table1_entry_baseline_makes_t2_late():
    tasks, staff = table1()
    plan = allocate(tasks, staff, policy="entry")
    assert _slots(plan) == [("T1", "E1", "09:00", "11:00"), ("T2", "E1", "11:00", "12:00")]
    assert plan.assignment_for("T2").at_risk


def test_confirming_gate_releases_dependent_work():
    tasks, staff = table1()
    tasks["G1"].status = DONE
    staff[0].windows = [(9 * H, 13 * H)]
    plan = allocate(tasks, staff)
    assert plan.assignment_for("T4") is not None


# ------------------------------------------------- readiness rules
def _chain():
    tasks = {
        "W": Task("W", "Write", skill="writing", effort_max=60, deadline=17 * H, entry_order=1),
        "E": Task("E", "Edit", skill="editing", effort_max=60, deadline=17 * H,
                  prereqs=["W"], entry_order=2),
    }
    staff = [Staff("A", "Ana", {"writing"}, [(9 * H, 17 * H)]),
             Staff("B", "Ben", {"editing"}, [(9 * H, 17 * H)])]
    return tasks, staff


def test_same_day_release_chains_internal_tasks():
    tasks, staff = _chain()
    plan = allocate(tasks, staff, same_day_release=True)
    assert plan.assignment_for("E").start == plan.assignment_for("W").end == 10 * H
    assert check_plan(tasks, staff, [], plan) == []


def test_strict_mode_waits_for_completion():
    tasks, staff = _chain()
    plan = allocate(tasks, staff, same_day_release=False)
    assert plan.assignment_for("E") is None
    assert "Write to be completed" in _reason(plan, "E").reason
    assert check_plan(tasks, staff, [], plan, same_day_release=False) == []


def test_unscheduled_prerequisite_blocks_successor():
    tasks, staff = _chain()
    tasks["W"].effort_max = 10 * H   # cannot fit in an 8-hour day
    plan = allocate(tasks, staff)
    assert _reason(plan, "W").category == "capacity"
    assert "not scheduled today" in _reason(plan, "E").reason


# ------------------------------------------------- priority and tie-breaks
def test_urgent_beats_earlier_deadline():
    tasks = {
        "N": Task("N", "Normal", skill="editing", effort_max=60, deadline=10 * H),
        "U": Task("U", "Urgent", skill="editing", effort_max=60, deadline=16 * H, urgency=URGENT),
    }
    staff = [Staff("E", "Ed", {"editing"}, [(9 * H, 17 * H)])]
    plan = allocate(tasks, staff)
    assert plan.assignments[0].task_id == "U"


def test_staff_tie_break_prefers_fewer_skills_then_id():
    tasks = {"T": Task("T", "Edit", skill="editing", effort_max=60)}
    staff = [Staff("A", "Generalist", {"editing", "writing"}, [(9 * H, 17 * H)]),
             Staff("Z", "Specialist", {"editing"}, [(9 * H, 17 * H)]),
             Staff("Y", "Specialist 2", {"editing"}, [(9 * H, 17 * H)])]
    plan = allocate(tasks, staff)
    assert plan.assignments[0].staff_id == "Y"


def test_earliest_finish_wins_over_staff_order():
    tasks = {"T": Task("T", "Edit", skill="editing", effort_max=60)}
    staff = [Staff("A", "Busy", {"editing"}, [(13 * H, 17 * H)]),
             Staff("B", "Free", {"editing", "writing"}, [(9 * H, 17 * H)])]
    plan = allocate(tasks, staff)
    assert plan.assignments[0].staff_id == "B"


def test_blocked_task_does_not_stop_lower_priority_work():
    tasks = {
        "Big": Task("Big", "Long edit", skill="editing", effort_max=5 * H, deadline=10 * H),
        "Small": Task("Small", "Short edit", skill="editing", effort_max=H, deadline=16 * H),
    }
    staff = [Staff("E", "Ed", {"editing"}, [(9 * H, 12 * H), (13 * H, 17 * H)])]
    plan = allocate(tasks, staff)
    assert _reason(plan, "Big").category == "capacity"
    assert plan.assignment_for("Small") is not None


def test_meetings_and_now_are_respected():
    tasks = {"T": Task("T", "Edit", skill="editing", effort_max=90)}
    staff = [Staff("E", "Ed", {"editing"}, [(9 * H, 17 * H)], exceptions=[(10 * H, 11 * H)])]
    plan = allocate(tasks, staff, now=9 * H + 30)
    assert _slots(plan) == [("T", "E", "11:00", "12:30")]


# ------------------------------------------------- missing information
def test_missing_estimate_skill_staff_and_availability():
    tasks = {
        "NoEst": Task("NoEst", "x", skill="editing", effort_max=None),
        "NoSkill": Task("NoSkill", "x", skill="animation", effort_max=60),
        "Unconf": Task("Unconf", "x", skill="writing", effort_max=60),
    }
    staff = [Staff("E", "Ed", {"editing"}, [(9 * H, 17 * H)]),
             Staff("W", "Wes", {"writing"}, [(9 * H, 17 * H)], availability_confirmed=False)]
    plan = allocate(tasks, staff)
    assert _reason(plan, "NoEst").category == "missing_info"
    assert _reason(plan, "NoSkill").category == "no_staff"
    assert "Wes" in _reason(plan, "Unconf").reason
    assert plan.assignments == []


# ------------------------------------------------- commitments
def test_commitments_are_preserved_and_block_time():
    tasks, staff = table1()
    commit = [Commitment("T1", "E1", 9 * H, 11 * H)]
    plan = allocate(tasks, staff, commit)
    assert plan.assignment_for("T1") is None             # never re-proposed
    assert _slots(plan) == [("T2", "E1", "11:00", "12:00")]
    assert check_plan(tasks, staff, commit, plan) == []


def test_committed_prerequisite_releases_successor_after_its_end():
    tasks, staff = _chain()
    commit = [Commitment("W", "A", 13 * H, 14 * H)]
    plan = allocate(tasks, staff, commit)
    assert plan.assignment_for("E").start == 14 * H


def test_done_commitment_is_not_double_released():
    tasks, staff = _chain()
    tasks["X"] = Task("X", "Second writing", skill="writing", effort_max=60, entry_order=3)
    tasks["E"].prereqs.append("X")
    tasks["W"].status = DONE
    commit = [Commitment("W", "A", 9 * H, 10 * H)]
    plan = allocate(tasks, staff, commit)
    # E still needs X; marking W done must not count twice toward E's release.
    assert plan.assignment_for("E").start >= plan.assignment_for("X").end
    assert check_plan(tasks, staff, commit, plan) == []


@pytest.mark.parametrize("commit,needle", [
    ([Commitment("T1", "E1", 9 * H, 11 * H), Commitment("T2", "E1", 10 * H, 11 * H)], "overlap"),
    ([Commitment("T1", "E1", 8 * H, 10 * H)], "outside"),
    ([Commitment("G1", "E1", 9 * H, 10 * H)], "gate"),
    ([Commitment("T1", "NOPE", 9 * H, 10 * H)], "unknown staff"),
])
def test_conflicting_commitments_stop_allocation(commit, needle):
    tasks, staff = table1()
    plan = allocate(tasks, staff, commit)
    assert plan.assignments == []
    assert any(needle in e for e in plan.errors)


# ------------------------------------------------- validation
def test_cycle_rejected_with_readable_path():
    tasks, staff = _chain()
    tasks["W"].prereqs.append("E")
    plan = allocate(tasks, staff)
    assert plan.assignments == []
    assert any("Circular dependency" in e and "Write" in e and "Edit" in e for e in plan.errors)


def test_unknown_prereq_and_bad_range_rejected():
    tasks, staff = _chain()
    tasks["E"].prereqs.append("GHOST")
    tasks["W"].effort_min = 120   # min > max
    errs = allocate(tasks, staff).errors
    assert any("GHOST" in e for e in errs)
    assert any("minimum exceeds" in e for e in errs)


# ------------------------------------------------- randomized invariants
@pytest.mark.parametrize("seed", range(40))
@pytest.mark.parametrize("policy", ["deadline", "entry"])
@pytest.mark.parametrize("release", [True, False])
def test_random_workloads_never_violate_hard_constraints(seed, policy, release):
    wl = generate(60 + seed * 5, seed=seed, load=1.0 + (seed % 4) * 0.3,
                  fragmented=seed % 2 == 0, dep_density=0.3 + (seed % 3) * 0.6)
    # Lock a few proposals as commitments, then replan around them.
    first = allocate(wl.tasks, wl.staff, policy=policy, same_day_release=release)
    commits = [Commitment(a.task_id, a.staff_id, a.start, a.end) for a in first.assignments[::4]]
    plan = allocate(wl.tasks, wl.staff, commits, policy=policy, same_day_release=release)
    assert not plan.errors
    assert check_plan(wl.tasks, wl.staff, commits, plan, same_day_release=release) == []
    # Every pending, uncommitted task is either assigned or explained.
    accounted = {a.task_id for a in plan.assignments} | {b.task_id for b in plan.blocked}
    pending = {t.id for t in wl.tasks.values()
               if not t.is_gate and not t.is_done} - {c.task_id for c in commits}
    assert accounted == pending


def test_generator_cycle_is_detected():
    wl = generate(50, seed=1, inject_cycle=True)
    assert any("Circular" in e for e in allocate(wl.tasks, wl.staff).errors)


def test_checker_catches_injected_violations():
    """Mutation test: the invariant checker must not be a rubber stamp."""
    tasks, staff = table1()
    good = allocate(tasks, staff)
    bad = copy.deepcopy(good)
    bad.assignments[1].start -= 30       # T1 now overlaps T2 and is too long
    out = check_plan(tasks, staff, [], bad)
    assert any("overlap" in v for v in out)
    assert any("upper estimate" in v for v in out)

    bad = copy.deepcopy(good)
    bad.assignments[0].staff_id = "E1"
    tasks["T2"].skill = "writing"
    assert any("skill mismatch" in v for v in check_plan(tasks, staff, [], bad))


def test_deadline_policy_not_worse_on_average_tight_workloads():
    better = worse = 0
    for seed in range(20):
        wl = generate(100, seed=seed, load=1.3)
        d = summarize(wl.tasks, allocate(wl.tasks, wl.staff, policy="deadline"))
        e = summarize(wl.tasks, allocate(wl.tasks, wl.staff, policy="entry"))
        better += d.at_risk < e.at_risk
        worse += d.at_risk > e.at_risk
    assert better > worse


def test_replay_is_deterministic():
    tasks, staff = table1()
    plan = allocate(tasks, staff)
    assert replay(tasks, plan, seed=1, error=0.3) == replay(tasks, plan, seed=1, error=0.3)
