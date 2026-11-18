"""Agency state, persistence and the operations the web pages call.

State lives in one JSON file (data/state.json). The web layer never touches
the engine directly; it calls these functions, which convert stored records
(ISO dates, hours, "HH:MM") into engine records (integer minutes) and back.

Every mutation bumps `version`. A recommendation remembers the version it
was computed from, and accepting it is refused if inputs changed since, so a
manager never commits a plan built on stale data.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from ..core import (
    DONE, GATE, NORMAL, PENDING, TASK, URGENT,
    Commitment, Staff, Task, allocate, parse_hhmm,
)
from ..core.graph import DiGraph
from ..core.metrics import summarize
from .campaign_templates import TEMPLATES

DATA_PATH = Path(os.environ.get(
    "CAMPAIGNFLOW_DATA", Path(__file__).resolve().parents[2] / "data" / "state.json"))


class InputError(ValueError):
    """Raised for invalid manager input; the message is shown to the user."""


# ------------------------------------------------------------------ persistence
def empty_state(plan_date: Optional[str] = None) -> dict:
    return {
        "plan_date": plan_date or date.today().isoformat(),
        "version": 0,
        "counters": {"campaign": 0, "task": 0, "staff": 0, "entry": 0},
        "settings": {"policy": "deadline", "same_day_release": True},
        "campaigns": {},
        "tasks": {},
        "staff": {},
        "commitments": [],
        "last_proposal": None,
        "notices": [],
    }


def load(path: Path = DATA_PATH) -> dict:
    if not path.exists():
        st = seed_demo(empty_state())
        save(st, path)
        return st
    with path.open() as f:
        return json.load(f)


def save(st: dict, path: Path = DATA_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(st, f, indent=1)
    tmp.replace(path)   # atomic on POSIX: never leaves a half-written file


def touch(st: dict) -> None:
    st["version"] += 1


def _next(st: dict, kind: str) -> int:
    st["counters"][kind] += 1
    return st["counters"][kind]


# ------------------------------------------------------------------ conversions
def deadline_minutes(st: dict, iso: Optional[str]) -> Optional[int]:
    """'YYYY-MM-DDTHH:MM' -> minutes from 00:00 of the planning day."""
    if not iso:
        return None
    dt = datetime.fromisoformat(iso)
    day0 = datetime.fromisoformat(st["plan_date"])
    return int((dt - day0).total_seconds() // 60)


def minutes_to_iso(st: dict, minutes: int) -> str:
    day0 = datetime.fromisoformat(st["plan_date"])
    return (day0 + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M")


def _hours_to_min(h) -> Optional[int]:
    if h is None or h == "":
        return None
    return int(round(float(h) * 60))


def engine_inputs(st: dict):
    """Build engine records for the planning day."""
    tasks: dict[str, Task] = {}
    for r in st["tasks"].values():
        tasks[r["id"]] = Task(
            id=r["id"], name=r["name"], kind=r["kind"], skill=r.get("skill") or None,
            effort_min=_hours_to_min(r.get("effort_min_h")),
            effort_max=_hours_to_min(r.get("effort_max_h")),
            deadline=deadline_minutes(st, r.get("deadline")),
            urgency=r.get("urgency", NORMAL), status=r["status"],
            prereqs=list(r.get("prereqs", [])), entry_order=r["entry_order"],
            campaign=r.get("campaign", ""))
    staff: list[Staff] = []
    for r in st["staff"].values():
        exc = [(parse_hhmm(e["start"]), parse_hhmm(e["end"])) for e in r.get("recurring", [])]
        exc += [(parse_hhmm(e["start"]), parse_hhmm(e["end"])) for e in r.get("exceptions", [])]
        staff.append(Staff(
            id=r["id"], name=r["name"], skills=set(r["skills"]),
            windows=[(parse_hhmm(r["window"][0]), parse_hhmm(r["window"][1]))],
            exceptions=exc,
            availability_confirmed=r.get("confirmed_on") == st["plan_date"]))
    commits = [Commitment(c["task_id"], c["staff_id"], c["start"], c["end"])
               for c in st["commitments"] if c["date"] == st["plan_date"]]
    return tasks, staff, commits


# ------------------------------------------------------------------ recommendations
def recommend(st: dict, policy: Optional[str] = None):
    """Run the allocator for the chosen policy and the other one for comparison."""
    policy = policy or st["settings"]["policy"]
    tasks, staff, commits = engine_inputs(st)
    release = st["settings"]["same_day_release"]
    plan = allocate(tasks, staff, commits, policy=policy, same_day_release=release)
    other = "entry" if policy == "deadline" else "deadline"
    alt = allocate(tasks, staff, commits, policy=other, same_day_release=release)
    return {
        "plan": plan,
        "tasks": tasks,
        "staff": staff,
        "commitments": commits,
        "summary": summarize(tasks, plan) if not plan.errors else None,
        "alt_summary": summarize(tasks, alt) if not alt.errors else None,
        "policy": policy,
        "other_policy": other,
        "version": st["version"],
        "changes": _diff(st.get("last_proposal"), plan),
    }


def _diff(previous: Optional[dict], plan) -> list[dict]:
    """What moved compared with the last recommendation the manager saw."""
    if not previous or plan.errors:
        return []
    prev = previous.get("slots", {})
    now = {a.task_id: [a.staff_id, a.start, a.end] for a in plan.assignments}
    out = []
    for tid in sorted(set(prev) | set(now)):
        if prev.get(tid) != now.get(tid):
            out.append({"task_id": tid, "before": prev.get(tid), "after": now.get(tid)})
    return out


def remember_proposal(st: dict, plan) -> None:
    st["last_proposal"] = {
        "version": st["version"],
        "slots": {a.task_id: [a.staff_id, a.start, a.end] for a in plan.assignments},
    }


def accept(st: dict, task_ids: list[str], version: int) -> int:
    """Turn selected proposals into locked commitments."""
    if version != st["version"]:
        raise InputError("Inputs changed since this recommendation was made. "
                         "Review the refreshed recommendation before accepting.")
    lp = st.get("last_proposal") or {}
    slots = lp.get("slots", {})
    chosen = [t for t in task_ids if t in slots]
    if not chosen:
        raise InputError("Select at least one proposed assignment to accept.")
    for tid in chosen:
        sid, start, end = slots[tid]
        st["commitments"].append({"task_id": tid, "staff_id": sid,
                                  "date": st["plan_date"], "start": start, "end": end})
    touch(st)
    return len(chosen)


def unlock(st: dict, task_id: str) -> None:
    before = len(st["commitments"])
    st["commitments"] = [c for c in st["commitments"] if c["task_id"] != task_id]
    if len(st["commitments"]) == before:
        raise InputError(f"{task_id} has no commitment to unlock.")
    touch(st)


# ------------------------------------------------------------------ campaigns & tasks
def _graph(st: dict) -> DiGraph:
    g = DiGraph()
    for t in st["tasks"].values():
        g.add_vertex(t["id"])
        for p in t["prereqs"]:
            if p in st["tasks"]:
                g.add_edge(p, t["id"])
    return g


def _check_acyclic(st: dict) -> None:
    cycle = _graph(st).find_cycle()
    if cycle:
        names = " → ".join(st["tasks"][v]["name"] for v in cycle)
        raise InputError(f"That link would create a circular dependency: {names}.")


def add_campaign(st: dict, template: str, client: str, name: str, deadline: str) -> str:
    if template not in TEMPLATES:
        raise InputError("Unknown template.")
    if not client.strip() or not name.strip():
        raise InputError("Client and campaign name are required.")
    try:
        due = datetime.fromisoformat(deadline)
    except ValueError:
        raise InputError("Enter a valid campaign deadline.")
    cid = f"C{_next(st, 'campaign')}"
    st["campaigns"][cid] = {"id": cid, "client": client.strip(), "name": name.strip(),
                            "template": template, "deadline": deadline}
    keymap: dict[str, str] = {}
    for step in TEMPLATES[template]["steps"]:
        tid = f"{cid}-{len(keymap) + 1}"
        keymap[step["key"]] = tid
        offset = step.get("due_offset_days", 0)
        step_due = due + timedelta(days=offset)
        # An offset must not push a step's deadline before the planning day;
        # fall back to the campaign deadline for rushed campaigns.
        if step_due.date() < date.fromisoformat(st["plan_date"]):
            step_due = due
        rec = _new_task(
            st, tid, f"{step['name']} – {name.strip()}", step["kind"], cid,
            skill=step.get("skill"),
            effort=step.get("effort"),
            deadline=step_due.strftime("%Y-%m-%dT%H:%M") if step["kind"] == TASK else None,
            prereqs=[keymap[k] for k in step.get("prereqs", [])])
        if step.get("review"):
            rec["review"] = True
            rec["revision_skill"] = step.get("revision_skill")
            rec["revision_effort"] = list(step.get("revision_effort", (1, 2)))
            rec["round"] = 1
    touch(st)
    return cid


def _new_task(st, tid, name, kind, campaign, skill=None, effort=None,
              deadline=None, prereqs=(), urgency=NORMAL) -> dict:
    rec = {
        "id": tid, "name": name, "kind": kind, "campaign": campaign,
        "skill": skill if kind == TASK else None,
        "effort_min_h": effort[0] if effort else None,
        "effort_max_h": effort[1] if effort else None,
        "deadline": deadline, "urgency": urgency, "status": PENDING,
        "prereqs": list(prereqs), "entry_order": _next(st, "entry"),
    }
    st["tasks"][tid] = rec
    return rec


def _clean_task_fields(st: dict, form: dict, current_id: Optional[str] = None) -> dict:
    name = (form.get("name") or "").strip()
    if not name:
        raise InputError("Task name is required.")
    kind = form.get("kind", TASK)
    if kind not in (TASK, GATE):
        raise InputError("Kind must be task or gate.")
    out = {"name": name, "kind": kind, "urgency": form.get("urgency", NORMAL)}
    if out["urgency"] not in (NORMAL, URGENT):
        raise InputError("Urgency must be normal or urgent.")
    if kind == TASK:
        skill = (form.get("skill") or "").strip().lower()
        if not skill:
            raise InputError("A production task needs a required skill.")
        lo, hi = form.get("effort_min_h"), form.get("effort_max_h")
        try:
            lo = float(lo) if lo not in (None, "") else None
            hi = float(hi) if hi not in (None, "") else None
        except ValueError:
            raise InputError("Effort must be a number of hours.")
        if hi is not None and hi <= 0:
            raise InputError("Upper effort must be greater than zero.")
        if lo is not None and hi is not None and lo > hi:
            raise InputError("Minimum effort cannot exceed the maximum.")
        if lo is not None and lo < 0:
            raise InputError("Effort cannot be negative.")
        out.update(skill=skill, effort_min_h=lo, effort_max_h=hi)
    else:
        out.update(skill=None, effort_min_h=None, effort_max_h=None)
    dl = (form.get("deadline") or "").strip()
    if dl:
        try:
            datetime.fromisoformat(dl)
        except ValueError:
            raise InputError("Enter a valid deadline.")
    out["deadline"] = dl or None
    prereqs = [p for p in form.get("prereqs", []) if p]
    for p in prereqs:
        if p not in st["tasks"]:
            raise InputError(f"Unknown prerequisite {p}.")
        if p == current_id:
            raise InputError("A task cannot depend on itself.")
    out["prereqs"] = prereqs
    out["campaign"] = form.get("campaign") or ""
    return out


def add_task(st: dict, form: dict) -> str:
    fields = _clean_task_fields(st, form)
    tid = f"T{_next(st, 'task')}"
    rec = _new_task(st, tid, fields["name"], fields["kind"], fields["campaign"])
    rec.update(fields)
    _check_acyclic(st)   # cannot fail for a new vertex, kept for safety
    touch(st)
    return tid


def update_task(st: dict, tid: str, form: dict) -> None:
    if tid not in st["tasks"]:
        raise InputError("Unknown task.")
    fields = _clean_task_fields(st, form, current_id=tid)
    backup = deepcopy(st["tasks"][tid])
    st["tasks"][tid].update(fields)
    try:
        _check_acyclic(st)
    except InputError:
        st["tasks"][tid] = backup
        raise
    touch(st)


def delete_task(st: dict, tid: str) -> None:
    if tid not in st["tasks"]:
        raise InputError("Unknown task.")
    del st["tasks"][tid]
    for t in st["tasks"].values():
        if tid in t["prereqs"]:
            t["prereqs"].remove(tid)
    st["commitments"] = [c for c in st["commitments"] if c["task_id"] != tid]
    touch(st)


def bulk(st: dict, ids: list[str], action: str) -> int:
    ids = [i for i in ids if i in st["tasks"]]
    if not ids:
        raise InputError("Select at least one task.")
    for tid in ids:
        t = st["tasks"][tid]
        if action in ("done", "confirm"):
            t["status"] = DONE
        elif action == "reopen":
            t["status"] = PENDING
        elif action in (URGENT, NORMAL):
            t["urgency"] = action
        else:
            raise InputError("Unknown action.")
    touch(st)
    return len(ids)


def request_changes(st: dict, gate_id: str) -> str:
    """Client asked for changes: close this review and add revision + new review.

    Completed work is never reopened, and the new nodes only point forward,
    so a revision loop can never introduce a circular dependency.
    """
    g = st["tasks"].get(gate_id)
    if not g or not g.get("review"):
        raise InputError("Only client review gates can request changes.")
    if g["status"] == DONE:
        raise InputError("This review is already closed.")
    g["status"] = DONE
    g["outcome"] = "changes requested"
    rnd = g.get("round", 1)
    camp = st["campaigns"].get(g["campaign"], {})
    base = g["name"].split(" (round")[0]
    rev = _new_task(st, f"{gate_id}-R{rnd}", f"Revision {rnd} – {camp.get('name', base)}",
                    TASK, g["campaign"], skill=g.get("revision_skill") or "editing",
                    effort=g.get("revision_effort") or (1, 2),
                    deadline=camp.get("deadline"), prereqs=[gate_id])
    new_gate = _new_task(st, f"{gate_id}-V{rnd + 1}", f"{base} (round {rnd + 1})",
                         GATE, g["campaign"], prereqs=[rev["id"]])
    new_gate.update(review=True, round=rnd + 1, revision_skill=g.get("revision_skill"),
                    revision_effort=g.get("revision_effort"))
    # Downstream steps (e.g. final approval) now wait for the new review.
    for t in st["tasks"].values():
        if t["id"] not in (rev["id"], new_gate["id"]) and gate_id in t["prereqs"]:
            t["prereqs"] = [new_gate["id"] if p == gate_id else p for p in t["prereqs"]]
    _check_acyclic(st)
    touch(st)
    return rev["id"]


# ------------------------------------------------------------------ staff
def _parse_window(start: str, end: str):
    try:
        s, e = parse_hhmm(start), parse_hhmm(end)
    except (ValueError, AttributeError):
        raise InputError("Times must be HH:MM.")
    if e <= s:
        raise InputError("End time must be after start time.")
    return s, e


def add_staff(st: dict, name: str, skills: str, start: str, end: str,
              lunch: bool = True) -> str:
    if not name.strip():
        raise InputError("Name is required.")
    skill_set = sorted({s.strip().lower() for s in skills.split(",") if s.strip()})
    if not skill_set:
        raise InputError("List at least one skill (comma separated).")
    _parse_window(start, end)
    sid = f"S{_next(st, 'staff')}"
    st["staff"][sid] = {
        "id": sid, "name": name.strip(), "skills": skill_set, "window": [start, end],
        "recurring": [{"start": "12:00", "end": "13:00", "label": "Lunch"}] if lunch else [],
        "exceptions": [], "confirmed_on": None,
    }
    touch(st)
    return sid


def delete_staff(st: dict, sid: str) -> None:
    if sid not in st["staff"]:
        raise InputError("Unknown staff member.")
    del st["staff"][sid]
    st["commitments"] = [c for c in st["commitments"] if c["staff_id"] != sid]
    touch(st)


def add_exception(st: dict, sid: str, start: str, end: str, label: str) -> None:
    s = st["staff"].get(sid)
    if not s:
        raise InputError("Unknown staff member.")
    _parse_window(start, end)
    s["exceptions"].append({"start": start, "end": end, "label": label.strip() or "Meeting"})
    s["exceptions"].sort(key=lambda e: e["start"])
    touch(st)


def remove_exception(st: dict, sid: str, index: int) -> None:
    s = st["staff"].get(sid)
    if not s or not (0 <= index < len(s["exceptions"])):
        raise InputError("Unknown exception.")
    s["exceptions"].pop(index)
    touch(st)


def set_confirmed(st: dict, sid: str, confirmed: bool) -> None:
    s = st["staff"].get(sid)
    if not s:
        raise InputError("Unknown staff member.")
    s["confirmed_on"] = st["plan_date"] if confirmed else None
    touch(st)


def set_absent(st: dict, sid: str) -> None:
    """Whole-day absence: one exception covering the full window."""
    s = st["staff"].get(sid)
    if not s:
        raise InputError("Unknown staff member.")
    s["exceptions"] = [{"start": s["window"][0], "end": s["window"][1], "label": "Absent"}]
    s["confirmed_on"] = st["plan_date"]
    touch(st)


# ------------------------------------------------------------------ days
def start_day(st: dict, new_date: str) -> None:
    """Move planning to another day.

    Daily exceptions and availability confirmations are cleared (they were for
    the old day). Unfinished commitments from earlier days are released back
    to the queue with a notice, rather than silently carried over.
    """
    try:
        date.fromisoformat(new_date)
    except ValueError:
        raise InputError("Enter a valid date.")
    st["plan_date"] = new_date
    for s in st["staff"].values():
        s["exceptions"] = []
    released = [c for c in st["commitments"]
                if c["date"] < new_date and st["tasks"].get(c["task_id"], {}).get("status") != DONE]
    st["commitments"] = [c for c in st["commitments"]
                         if c["date"] >= new_date or c not in released]
    st["notices"] = [f"Released unfinished commitment {c['task_id']} from {c['date']}."
                     for c in released]
    st["last_proposal"] = None
    touch(st)


# ------------------------------------------------------------------ demo data
def seed_demo(st: dict) -> dict:
    """Synthetic demo agency (clearly illustrative, not real client data)."""
    today = date.fromisoformat(st["plan_date"])

    def at(days: int, hhmm: str) -> str:
        return f"{(today + timedelta(days=days)).isoformat()}T{hhmm}"

    add_staff(st, "Bea (writer)", "writing", "09:00", "18:00")
    add_staff(st, "Carlo (editor)", "editing", "09:00", "18:00")
    add_staff(st, "Dani (editor/writer)", "editing, writing", "10:00", "19:00")
    add_staff(st, "Ely (junior editor)", "editing", "13:00", "18:00", lunch=False)

    add_campaign(st, "video", "Sari-Sari Co.", "Holiday promo video", at(5, "17:00"))
    add_campaign(st, "video", "Kape Manila", "Brand story", at(2, "12:00"))
    add_campaign(st, "social", "Kape Manila", "December posts", at(1, "15:00"))
    add_campaign(st, "article", "BuildPH", "Launch article", at(3, "17:00"))

    t = st["tasks"]
    # Kape Manila brand story: script approved and filming done -> editing ready.
    t["C2-1"]["status"] = DONE
    t["C2-2"]["status"] = DONE
    t["C2-3"]["status"] = DONE
    # Holiday promo: script written, awaiting client approval (external gate).
    t["C1-1"]["status"] = DONE
    # An urgent ad-hoc request that arrived this morning.
    add_task(st, {"name": "Fix typo in live ad – Sari-Sari Co.", "kind": TASK,
                  "skill": "editing", "effort_min_h": 0.25, "effort_max_h": 0.5,
                  "deadline": at(0, "11:00"), "urgency": URGENT, "campaign": "C1"})
    # Two ad-hoc edits: the earlier request is less urgent than the later one,
    # which is where a deadline-aware order and an entry-order queue diverge.
    add_task(st, {"name": "Thumbnail set – Kape Manila", "kind": TASK, "skill": "editing",
                  "effort_min_h": 1.5, "effort_max_h": 2, "deadline": at(1, "17:00"),
                  "campaign": "C2"})
    add_task(st, {"name": "Resize launch banner – BuildPH", "kind": TASK, "skill": "editing",
                  "effort_min_h": 1, "effort_max_h": 1.5, "deadline": at(0, "12:00"),
                  "campaign": "C4"})
    s = st["staff"]
    s["S1"]["exceptions"].append({"start": "10:00", "end": "11:00", "label": "Client call"})
    s["S2"]["exceptions"].append({"start": "15:00", "end": "15:30", "label": "Team huddle"})
    for sid in ("S1", "S2", "S3"):
        s[sid]["confirmed_on"] = st["plan_date"]   # S4 left unconfirmed on purpose
    st["version"] = 0
    return st
