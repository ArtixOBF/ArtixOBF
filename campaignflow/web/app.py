"""Flask + HTMX front end.

Three pages mirror the proposal's workflow:
    /today   daily review: bulk status updates, gates, staff availability
    /plan    recommendation: proposals, blockers, policy comparison, accept
    /intake  template intake: campaigns, ad-hoc tasks, staff

The whole site uses hx-boost, so links and forms swap the page body without
a full reload. A few controls (availability toggles) swap only their own row.

Run:  python -m campaignflow.web.app   (then open http://127.0.0.1:5000)
"""

from __future__ import annotations

import os
from datetime import date, datetime

from flask import (
    Flask, flash, g, redirect, render_template, request, url_for,
)

from ..core import GATE, hhmm
from ..core.policy import POLICY_LABELS
from . import store
from .campaign_templates import TEMPLATES

app = Flask(__name__)
app.secret_key = os.environ.get("CAMPAIGNFLOW_SECRET", "dev-only-not-secret")


# ------------------------------------------------------------------ helpers
def _state():
    # Loaded once per request; template filters reuse the same object.
    if "st" not in g:
        g.st = store.load(app.config.get("DATA_PATH", store.DATA_PATH))
    return g.st


def _save(st):
    store.save(st, app.config.get("DATA_PATH", store.DATA_PATH))


def _mutate(fn, ok_message=None, to=None):
    """Run a state change, persist it, and flash success or the input error."""
    st = _state()
    try:
        result = fn(st)
        _save(st)
        if ok_message:
            flash(ok_message(result) if callable(ok_message) else ok_message, "ok")
    except store.InputError as e:
        flash(str(e), "error")
    return redirect(to or request.referrer or url_for("today"))


@app.template_filter("hhmm")
def _hhmm(m):
    return hhmm(m)


@app.template_filter("relday")
def _relday(minutes):
    """Engine minutes -> 'Today 11:00', 'Tomorrow 12:00', 'Fri 20 Nov 17:00'."""
    if minutes is None:
        return "—"
    st = _state()
    return _due(store.minutes_to_iso(st, minutes))


@app.template_filter("hours")
def _hours(h):
    if h is None or h == "":
        return "?"
    return f"{float(h):g}"


@app.template_filter("due")
def _due(iso):
    if not iso:
        return "—"
    st = _state()
    dt = datetime.fromisoformat(iso)
    days = (dt.date() - date.fromisoformat(st["plan_date"])).days
    if days == 0:
        return f"Today {dt:%H:%M}"
    if days == 1:
        return f"Tomorrow {dt:%H:%M}"
    if days < 0:
        return f"{dt:%a %d %b %H:%M} (overdue)"
    return f"{dt:%a %d %b %H:%M}"


@app.template_filter("due_class")
def _due_class(iso):
    """'overdue' | 'today' | '' for colouring deadlines."""
    if not iso:
        return ""
    st = _state()
    days = (datetime.fromisoformat(iso).date() - date.fromisoformat(st["plan_date"])).days
    return "overdue" if days < 0 else "today" if days == 0 else ""


@app.template_filter("initials")
def _initials(name):
    words = [w for w in (name or "?").replace("(", " ").split() if w[:1].isalpha()]
    return "".join(w[0] for w in words[:2]).upper() or "?"


@app.template_filter("hue")
def _hue(text):
    """Stable avatar colour derived from a name or ID."""
    return sum(ord(c) * (i + 1) for i, c in enumerate(text or "")) % 360


@app.template_filter("longdate")
def _longdate(iso):
    return f"{date.fromisoformat(iso):%A, %d %B %Y}"


def task_state(st, t, committed):
    """Classify a task for badges and filters on the Today page."""
    if t["status"] == "done":
        return "done"
    if t["id"] in committed:
        return "committed"
    prereqs_done = all(st["tasks"].get(p, {}).get("status") == "done" for p in t["prereqs"])
    if t["kind"] == GATE:
        return "gate-ready" if prereqs_done else "gate-upcoming"
    if t.get("effort_max_h") in (None, ""):
        return "needs-info"
    return "ready" if prereqs_done else "waiting"


def attention(st, committed=None):
    """Items the manager should act on today (the sidebar badge and inbox)."""
    if committed is None:
        committed = {c["task_id"] for c in st["commitments"] if c["date"] == st["plan_date"]}
    gates = [t for t in st["tasks"].values() if task_state(st, t, committed) == "gate-ready"]
    staff = [s for s in st["staff"].values() if s.get("confirmed_on") != st["plan_date"]]
    info = [t for t in st["tasks"].values() if task_state(st, t, committed) == "needs-info"]
    return {"gates": gates, "staff": staff, "info": info,
            "count": len(gates) + len(staff) + len(info)}


@app.context_processor
def _globals():
    st = _state()
    return {"POLICY_LABELS": POLICY_LABELS, "TEMPLATES": TEMPLATES, "GATE": GATE,
            "nav_attention": attention(st)["count"],
            "nav_commitments": sum(1 for c in st["commitments"] if c["date"] == st["plan_date"])}


# ------------------------------------------------------------------ pages
@app.get("/")
def index():
    return redirect(url_for("today"))


@app.get("/today")
def today():
    st = _state()
    tasks, staff, commits = store.engine_inputs(st)
    from ..core.validate import validate
    errors = validate(tasks, staff, commits)
    committed = {c.task_id: c for c in commits}
    staff_names = {s["id"]: s["name"] for s in st["staff"].values()}
    groups: dict[str, list] = {}
    for t in sorted(st["tasks"].values(), key=lambda t: t["entry_order"]):
        groups.setdefault(t["campaign"] or "", []).append(t)
    waiting = {tid: [st["tasks"][p]["name"] for p in t["prereqs"]
                     if p in st["tasks"] and st["tasks"][p]["status"] != "done"]
               for tid, t in st["tasks"].items()}
    states = {tid: task_state(st, t, committed) for tid, t in st["tasks"].items()}
    counts = {k: 0 for k in ("ready", "waiting", "committed", "done")}
    for v in states.values():
        bucket = {"ready": "ready", "gate-ready": "ready", "committed": "committed",
                  "done": "done"}.get(v, "waiting")
        counts[bucket] += 1
    pending = [t for t in st["tasks"].values()
               if t["status"] != "done" and t["kind"] != GATE]
    due_soon = sum(1 for t in pending if _due_class(t.get("deadline")) in ("today", "overdue"))
    confirmed = sum(1 for s in st["staff"].values() if s.get("confirmed_on") == st["plan_date"])
    return render_template(
        "today.html", st=st, groups=groups, committed=committed, staff_names=staff_names,
        waiting=waiting, errors=errors, states=states, counts=counts,
        att=attention(st, set(committed)), due_soon=due_soon, confirmed=confirmed,
        ready_tasks=sum(1 for v in states.values() if v == "ready"),
        gate_waits=sum(1 for v in states.values() if v in ("gate-ready", "gate-upcoming")))


@app.get("/plan")
def plan():
    st = _state()
    policy = request.args.get("policy") or st["settings"]["policy"]
    if policy not in POLICY_LABELS:
        policy = "deadline"
    rec = store.recommend(st, policy)
    if not rec["plan"].errors:
        store.remember_proposal(st, rec["plan"])
        _save(st)
    # Timeline bounds: earliest window start to latest window end.
    starts = [s.windows[0][0] for s in rec["staff"]] or [540]
    ends = [s.windows[0][1] for s in rec["staff"]] or [1080]
    lo, hi = min(starts), max(ends)
    now = None
    if st["plan_date"] == date.today().isoformat():
        n = datetime.now()
        now = n.hour * 60 + n.minute
        if not lo <= now <= hi:
            now = None
    return render_template("plan.html", st=st, rec=rec, t0=lo, t1=hi, now=now,
                           hours=list(range(lo // 60, hi // 60 + 1)))


@app.get("/intake")
def intake():
    st = _state()
    return render_template("intake.html", st=st)


@app.get("/tasks/<tid>/edit")
def edit_task(tid):
    st = _state()
    if tid not in st["tasks"]:
        flash("Unknown task.", "error")
        return redirect(url_for("today"))
    return render_template("edit_task.html", st=st, t=st["tasks"][tid])


# ------------------------------------------------------------------ task actions
@app.post("/tasks/bulk")
def tasks_bulk():
    ids = request.form.getlist("ids")
    action = request.form.get("action", "")
    labels = {"done": "marked done", "confirm": "confirmed", "reopen": "reopened",
              "urgent": "marked urgent", "normal": "marked normal"}
    return _mutate(lambda st: store.bulk(st, ids, action),
                   lambda n: f"{n} item(s) {labels.get(action, 'updated')}.")


@app.post("/tasks/<tid>/changes")
def tasks_changes(tid):
    return _mutate(lambda st: store.request_changes(st, tid),
                   lambda rid: f"Revision task {rid} and a new review gate were created.")


@app.post("/tasks")
def tasks_add():
    form = request.form.to_dict()
    form["prereqs"] = request.form.getlist("prereqs")
    return _mutate(lambda st: store.add_task(st, form), lambda tid: f"Added {tid}.",
                   to=url_for("intake"))


@app.post("/tasks/<tid>/edit")
def tasks_edit(tid):
    form = request.form.to_dict()
    form["prereqs"] = request.form.getlist("prereqs")
    st = _state()
    try:
        store.update_task(st, tid, form)
        _save(st)
        flash(f"Saved {tid}.", "ok")
        return redirect(url_for("today"))
    except store.InputError as e:
        flash(str(e), "error")
        return redirect(url_for("edit_task", tid=tid))


@app.post("/tasks/<tid>/delete")
def tasks_delete(tid):
    return _mutate(lambda st: store.delete_task(st, tid), f"Deleted {tid}.",
                   to=url_for("today"))


@app.post("/campaigns")
def campaigns_add():
    f = request.form
    return _mutate(lambda st: store.add_campaign(st, f.get("template", ""), f.get("client", ""),
                                                 f.get("name", ""), f.get("deadline", "")),
                   lambda cid: f"Campaign {cid} created from template.", to=url_for("today"))


# ------------------------------------------------------------------ staff actions
@app.post("/staff")
def staff_add():
    f = request.form
    return _mutate(lambda st: store.add_staff(st, f.get("name", ""), f.get("skills", ""),
                                              f.get("start", "09:00"), f.get("end", "18:00"),
                                              lunch=bool(f.get("lunch"))),
                   lambda sid: f"Added staff {sid}.", to=url_for("intake"))


@app.post("/staff/<sid>/confirm")
def staff_confirm(sid):
    st = _state()
    try:
        store.set_confirmed(st, sid, request.form.get("confirmed") == "1")
        _save(st)
    except store.InputError as e:
        flash(str(e), "error")
    if request.headers.get("HX-Request") and request.headers.get("HX-Target", "").startswith("staff-"):
        return render_template("_staff_row.html", s=st["staff"][sid], st=st)
    return redirect(url_for("today"))


@app.post("/staff/<sid>/exceptions")
def staff_exception(sid):
    f = request.form
    return _mutate(lambda st: store.add_exception(st, sid, f.get("start", ""), f.get("end", ""),
                                                  f.get("label", "")), "Exception added.")


@app.post("/staff/<sid>/exceptions/<int:i>/delete")
def staff_exception_delete(sid, i):
    return _mutate(lambda st: store.remove_exception(st, sid, i), "Exception removed.")


@app.post("/staff/<sid>/absent")
def staff_absent(sid):
    return _mutate(lambda st: store.set_absent(st, sid), "Marked absent today.")


@app.post("/staff/<sid>/delete")
def staff_delete(sid):
    return _mutate(lambda st: store.delete_staff(st, sid), "Staff member removed.")


# ------------------------------------------------------------------ plan actions
@app.post("/plan/accept")
def plan_accept():
    ids = request.form.getlist("ids")
    version = int(request.form.get("version", -1))
    return _mutate(lambda st: store.accept(st, ids, version),
                   lambda n: f"Committed {n} assignment(s). They stay fixed until unlocked.",
                   to=url_for("plan"))


@app.post("/commitments/<tid>/unlock")
def commitment_unlock(tid):
    return _mutate(lambda st: store.unlock(st, tid), f"Unlocked {tid}.")


@app.post("/settings")
def settings():
    f = request.form

    def apply(st):
        if f.get("policy") in POLICY_LABELS:
            st["settings"]["policy"] = f["policy"]
        st["settings"]["same_day_release"] = f.get("same_day_release") == "1"
        store.touch(st)

    return _mutate(apply, "Settings saved.", to=url_for("plan"))


@app.post("/day")
def day():
    return _mutate(lambda st: store.start_day(st, request.form.get("date", "")),
                   "Planning day changed. Review availability before planning.",
                   to=url_for("today"))


@app.post("/reset-demo")
def reset_demo():
    def apply(st):
        fresh = store.seed_demo(store.empty_state())
        st.clear()
        st.update(fresh)
    return _mutate(apply, "Demo data restored.", to=url_for("today"))


def main():
    app.run(debug=bool(os.environ.get("FLASK_DEBUG")), port=int(os.environ.get("PORT", 5000)))


if __name__ == "__main__":
    main()
