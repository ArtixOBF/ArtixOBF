"""Generate the printable briefing sheets for the usability study.

Usage: python docs/usability/make_sheets.py
Writes scenario-A.md and scenario-B.md next to this file, built from the same
seed data the app loads (Reset demo = A; Reset demo with variant B = B), so the
paper version and the app version of a scenario always match.
"""

import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from campaignflow.web import store  # noqa: E402

OUT = Path(__file__).resolve().parent


def due(st, iso):
    if not iso:
        return "—"
    dt = datetime.fromisoformat(iso)
    days = (dt.date() - date.fromisoformat(st["plan_date"])).days
    label = {0: "Today", 1: "Tomorrow"}.get(days, f"Day +{days}")
    return f"{label} {dt:%H:%M}"


def sheet(variant: str) -> str:
    st = store.seed_demo(store.empty_state("2026-11-18"), variant)
    T = st["tasks"]
    lines = [f"# Scenario {variant}: planning briefing", "",
             "You coordinate production for a small agency. Plan **today, 09:00 onwards**.",
             "Each task is done by one person, in one continuous block, by someone with the required skill.",
             "Reserve the **upper** effort estimate. External steps (⚑) happen outside the team: work that",
             "depends on them cannot start until they are confirmed.", "",
             "## Team today", "", "| Person | Skills | Hours | Busy | Confirmed working today? |", "|---|---|---|---|---|"]
    for s in st["staff"].values():
        busy = ", ".join(f"{e['start']}–{e['end']} {e['label']}" for e in s["recurring"] + s["exceptions"]) or "—"
        ok = "Yes" if s["confirmed_on"] == st["plan_date"] else "**Not yet confirmed**"
        lines.append(f"| {s['name']} | {', '.join(s['skills'])} | {s['window'][0]}–{s['window'][1]} | {busy} | {ok} |")
    lines += ["", "## Work", ""]
    for cid, c in st["campaigns"].items():
        lines += [f"### {c['client']}: {c['name']} (due {due(st, c['deadline'])})", "",
                  "| # | Step | Skill | Effort (h) | Due | Status | Waits for |", "|---|---|---|---|---|---|---|"]
        for t in T.values():
            if t["campaign"] != cid:
                continue
            gate = t["kind"] == "gate"
            status = ("done" if t["status"] == "done" else "⚑ not confirmed") if gate else ("done" if t["status"] == "done" else "to do")
            waits = ", ".join(T[p]["name"].split(" – ")[0] for p in t["prereqs"]) or "—"
            eff = "—" if gate else f"{t['effort_min_h']:g}–{t['effort_max_h']:g}"
            urgent = " **(URGENT)**" if t.get("urgency") == "urgent" else ""
            lines.append(f"| {t['id']} | {'⚑ ' if gate else ''}{t['name'].split(' – ')[0]}{urgent} | {t['skill'] or '—'} | {eff} | {due(st, t['deadline'])} | {status} | {waits} |")
        lines.append("")
    lines += ["## Your task", "",
              "Write today’s plan: for each task you schedule, **who**, **start** and **end**. "
              "List anything that cannot be done today and why.", "",
              "| Task # | Person | Start | End |", "|---|---|---|---|"] + ["|  |  |  |  |"] * 9
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    for v in ("A", "B"):
        (OUT / f"scenario-{v}.md").write_text(sheet(v))
        print("wrote", OUT / f"scenario-{v}.md")
