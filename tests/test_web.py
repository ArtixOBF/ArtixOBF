"""Tests for the store layer and Flask routes."""

import pytest

from campaignflow.core import check_plan
from campaignflow.web import store
from campaignflow.web.app import app


@pytest.fixture
def st():
    return store.seed_demo(store.empty_state("2026-11-18"))


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, DATA_PATH=tmp_path / "state.json")
    with app.test_client() as c:
        yield c


def test_demo_plan_is_valid(st):
    rec = store.recommend(st)
    assert not rec["plan"].errors
    assert rec["plan"].assignments
    assert check_plan(rec["tasks"], rec["staff"], rec["commitments"], rec["plan"]) == []
    # The unconfirmed junior editor gets no work.
    assert all(a.staff_id != "S4" for a in rec["plan"].assignments)
    # Urgent ad-hoc fix is proposed first.
    first = min(rec["plan"].assignments, key=lambda a: (a.start, a.task_id))
    assert rec["tasks"][first.task_id].urgency == "urgent"


def test_template_creates_linked_steps_with_inherited_deadlines(st):
    cid = store.add_campaign(st, "article", "ACME", "Post", "2026-11-25T17:00")
    steps = [t for t in st["tasks"].values() if t["campaign"] == cid]
    assert [t["kind"] for t in steps] == ["task", "task", "gate"]
    assert steps[1]["prereqs"] == [steps[0]["id"]]
    assert steps[0]["deadline"] == "2026-11-23T17:00"     # due_offset_days = -2


def test_accept_then_replan_keeps_commitments(st):
    rec = store.recommend(st)
    store.remember_proposal(st, rec["plan"])
    chosen = [a.task_id for a in rec["plan"].assignments[:2]]
    store.accept(st, chosen, st["version"])
    rec2 = store.recommend(st)
    assert {c.task_id for c in rec2["commitments"]} == set(chosen)
    assert not any(a.task_id in chosen for a in rec2["plan"].assignments)


def test_accept_refuses_stale_recommendation(st):
    rec = store.recommend(st)
    store.remember_proposal(st, rec["plan"])
    v = st["version"]
    store.bulk(st, ["C1-2"], "confirm")          # inputs change after viewing
    with pytest.raises(store.InputError, match="changed"):
        store.accept(st, [rec["plan"].assignments[0].task_id], v)


def test_request_changes_adds_revision_without_cycle(st):
    review = "C2-5"
    st["tasks"]["C2-4"]["status"] = "done"
    rev = store.request_changes(st, review)
    new_gate = f"{review}-V2"
    assert st["tasks"][review]["status"] == "done"
    assert st["tasks"][rev]["prereqs"] == [review]
    assert st["tasks"]["C2-6"]["prereqs"] == [new_gate]   # final approval waits for round 2
    rec = store.recommend(st)
    assert not rec["plan"].errors
    assert rec["plan"].assignment_for(rev) is not None


def test_editing_into_a_cycle_is_rejected_and_rolled_back(st):
    form = dict(st["tasks"]["C4-1"], prereqs=["C4-2"])
    with pytest.raises(store.InputError, match="circular"):
        store.update_task(st, "C4-1", form)
    assert st["tasks"]["C4-1"]["prereqs"] == []


def test_meeting_over_commitment_flags_conflict(st):
    rec = store.recommend(st)
    store.remember_proposal(st, rec["plan"])
    a = rec["plan"].assignments[0]
    store.accept(st, [a.task_id], st["version"])
    from campaignflow.core import hhmm
    store.add_exception(st, a.staff_id, hhmm(a.start), hhmm(a.end), "Surprise meeting")
    assert any("outside" in e for e in store.recommend(st)["plan"].errors)


def test_new_day_resets_availability_and_releases_unfinished(st):
    rec = store.recommend(st)
    store.remember_proposal(st, rec["plan"])
    store.accept(st, [rec["plan"].assignments[0].task_id], st["version"])
    store.start_day(st, "2026-11-19")
    _, staff, commits = store.engine_inputs(st)
    assert not any(s.availability_confirmed for s in staff)
    assert commits == [] and st["notices"]


@pytest.mark.parametrize("bad", [
    {"name": "", "kind": "task", "skill": "editing"},
    {"name": "x", "kind": "task", "skill": ""},
    {"name": "x", "kind": "task", "skill": "editing", "effort_min_h": "3", "effort_max_h": "1"},
    {"name": "x", "kind": "task", "skill": "editing", "effort_max_h": "abc"},
    {"name": "x", "kind": "task", "skill": "editing", "prereqs": ["NOPE"]},
])
def test_task_input_validation(st, bad):
    with pytest.raises(store.InputError):
        store.add_task(st, bad)


# ---------------------------------------------------------------- routes
def test_pages_render(client):
    for url in ("/today", "/plan", "/intake", "/plan?policy=entry", "/tasks/C1-1/edit"):
        r = client.get(url)
        assert r.status_code == 200, url
    assert b"Daily review" in client.get("/today").data


def test_full_flow_through_routes(client):
    client.get("/plan")
    r = client.post("/campaigns", data={"template": "social", "client": "Test",
                                        "name": "Promo", "deadline": "2030-01-01T12:00"},
                    follow_redirects=True)
    assert b"created from template" in r.data
    r = client.post("/tasks/bulk", data={"ids": ["C1-2"], "action": "confirm"},
                    follow_redirects=True)
    assert b"confirmed" in r.data
    page = client.get("/plan").data.decode()
    import re
    version = re.search(r'name="version" value="(\d+)"', page).group(1)
    ids = re.findall(r'name="ids" value="([^"]+)" checked', page)
    r = client.post("/plan/accept", data={"ids": ids[:1], "version": version},
                    follow_redirects=True)
    assert b"Committed 1" in r.data
    r = client.post(f"/commitments/{ids[0]}/unlock", follow_redirects=True)
    assert b"Unlocked" in r.data


def test_bad_input_shows_error_not_crash(client):
    r = client.post("/staff", data={"name": "", "skills": ""}, follow_redirects=True)
    assert r.status_code == 200 and b"required" in r.data


def test_htmx_confirm_returns_partial(client):
    client.get("/today")
    r = client.post("/staff/S4/confirm", data={"confirmed": "1"},
                    headers={"HX-Request": "true", "HX-Target": "staff-S4"})
    assert b'id="staff-S4"' in r.data and b"<html" not in r.data


def test_scenario_b_matches_demo_structure():
    """The usability study's Scenario B must be exactly as hard as the demo."""
    a = store.seed_demo(store.empty_state("2026-11-18"))
    b = store.seed_demo(store.empty_state("2026-11-18"), "B")
    ra, rb = store.recommend(a), store.recommend(b)
    shape = lambda r: sorted((x.task_id, x.staff_id, x.start, x.end) for x in r["plan"].assignments)
    assert shape(ra) == shape(rb)
    assert {x.task_id for x in ra["plan"].blocked} == {x.task_id for x in rb["plan"].blocked}
    names_b = " ".join(t["name"] for t in b["tasks"].values()) + " ".join(s["name"] for s in b["staff"].values())
    for old in ("Kape Manila", "Carlo", "Fix typo", "BuildPH"):
        assert old not in names_b


def test_reset_route_loads_scenario_b(client):
    client.get("/today")
    client.post("/reset-demo", data={"variant": "B"})
    assert b"Habi Textiles" in client.get("/today").data
