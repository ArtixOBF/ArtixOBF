"""Summarize usability-study results for the report.

Usage: python docs/usability/summarize.py [path/to/results.csv]
Prints a Markdown table and a LaTeX table comparing manual planning with
CampaignFlow. With three participants, report these descriptively.
"""

import csv
import statistics as st
import sys
from pathlib import Path

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("results.csv")
rows = [r for r in csv.DictReader(path.open()) if r["setup_min"].strip()]
if not rows:
    sys.exit("results.csv has no filled-in rows yet: run the study first (see protocol.md).")

METRICS = [
    ("setup_min", "Setup time (min)", "{:.1f}"),
    ("update_min", "Update time, 4 disruptions (min)", "{:.1f}"),
    ("corrections", "Self-corrections", "{:.1f}"),
    ("accuracy", "Interpretation accuracy", "{:.0%}"),
    ("overrides", "Manual overrides", "{:.1f}"),
    ("unwanted_changes", "Unwanted assignment changes", "{:.1f}"),
    ("violations", "Hard-constraint violations (total)", "{:.0f}"),
]


def value(r, key):
    if key == "accuracy":
        return float(r["q_correct"]) / float(r["q_total"])
    return float(r[key] or 0)


out = {}
for method in ("manual", "campaignflow"):
    rs = [r for r in rows if r["method"] == method]
    out[method] = {"n": len(rs)}
    for key, _, _ in METRICS:
        vals = [value(r, key) for r in rs]
        out[method][key] = (sum(vals) if key == "violations" else st.mean(vals)) if vals else float("nan")

print(f"Participants: {len({r['participant'] for r in rows})}\n")
print("| Measure | Manual | CampaignFlow |\n|---|---|---|")
for key, label, fmt in METRICS:
    print(f"| {label} | {fmt.format(out['manual'][key])} | {fmt.format(out['campaignflow'][key])} |")

print("\n% LaTeX (paste into the report's evaluation section)")
print("\\begin{table}[t]\n\\centering\n\\caption{Usability study (n = %d participants, means unless noted).}" % len({r['participant'] for r in rows}))
print("\\small\n\\begin{tabular}{@{}lrr@{}}\n\\toprule\n\\textbf{Measure} & \\textbf{Manual} & \\textbf{CampaignFlow} \\\\\n\\midrule")
for key, label, fmt in METRICS:
    m, c = fmt.format(out["manual"][key]), fmt.format(out["campaignflow"][key])
    print(f"{label} & {m.replace('%', chr(92) + '%')} & {c.replace('%', chr(92) + '%')} \\\\")
print("\\bottomrule\n\\end{tabular}\n\\end{table}")
notes = [f"{r['participant']} ({r['method']}): {r['notes']}" for r in rows if r["notes"].strip()]
if notes:
    print("\nParticipant notes:\n- " + "\n- ".join(notes))
