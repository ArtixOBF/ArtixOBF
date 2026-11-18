# CampaignFlow usability study: protocol

This implements the evaluation promised in our proposal: three people with coordination experience each plan one scenario **by hand** and a matched scenario **with CampaignFlow**, alternating which comes first. They then handle the same four disruptions in each. We measure effort, accuracy and stability, and require zero hard-constraint violations.

**Time needed:** about 35 minutes per participant. You need two of you (facilitator + timer/observer), a laptop running the app, two printed briefing sheets and a stopwatch.

> **Before you start:** ask your instructor whether a short, anonymous usability test with classmates or acquaintances needs any ethics clearance in your course. Record no names: use P1, P2, P3.

## Participants

- Three people who have coordinated schedules or tasks: org officers, event or project leads, someone who has worked at an agency.
- Use the order sheet below, so each method goes first at least once.

| Participant | First | Second |
|---|---|---|
| P1 | Manual · Scenario A | CampaignFlow · Scenario B |
| P2 | CampaignFlow · Scenario A | Manual · Scenario B |
| P3 | Manual · Scenario B | CampaignFlow · Scenario A |

The scenarios have the same structure and difficulty, with different names. This is checked by an automated test, `test_scenario_b_matches_demo_structure`.

## Setup

1. Print `scenario-A.md` and `scenario-B.md`. Any Markdown viewer can print them, or paste them into a Google Doc.
2. Start the app: `python -m campaignflow.web.app`.
3. **Before each CampaignFlow session, load the right scenario.** For Scenario A, click *Reset demo* in the sidebar. For Scenario B, run this in a second terminal:

```bash
curl -s -X POST -d variant=B http://127.0.0.1:5000/reset-demo > /dev/null
```

4. Have `results.csv` open to fill in as you go.

## Consent script (read aloud)

> "We're testing our class project, not you. It takes about 35 minutes. We'll time how long planning takes and note any mistakes, but we won't record your name, voice or screen. You can stop at any time. Is that okay?"

## Procedure (per participant)

**1. Warm-up (3 min).** Show the CampaignFlow Today and Plan pages using the *other* scenario. Explain the rules on the briefing sheet: one person per task, one continuous block, the upper estimate, and that ⚑ steps must be confirmed first.

**2. Session 1 (≈12 min).**
- **Setup:** "Make today's plan." Start the timer. Stop it when they say they're done: a written plan for Manual, or *Lock in plan* for CampaignFlow. Record this as **setup time**.
- **Questions:** ask Q1–Q5 (below). Record the number correct.
- **Disruptions:** read D1–D4 one at a time. Time each update from the end of reading the card to "done", and add the four times together as **update time**.
  - For CampaignFlow, they make the change in the app, open Plan and lock the result.
  - For Manual, they edit their written plan.
- **Corrections:** count every time they fix their own mistake.
- **Overrides** (CampaignFlow only): count every time they untick or unlock a proposal to do something different.

**3. Session 2.** Repeat with the other method and the other scenario.

**4. Observer check (after each session).** Go through the checklist below on the final plan. Count **violations** (hard-rule breaks) and **unwanted changes**: assignments from the locked or written plan that moved although no disruption forced them to.

**5. Debrief (2 min).** "Which way was easier? Was anything confusing?" Write a one-line note.

## Disruption cards

Read each card exactly as written. In Scenario B, use the names in brackets.

| Card | Read aloud | In CampaignFlow |
|---|---|---|
| D1 | "The client just approved the script for the Holiday promo video [Anniversary video]." | Today › *Did it happen? Yes* |
| D2 | "Ely [Tess] messages: working today, 13:00 to 18:00." | Today › *Working today? Yes* |
| D3 | "New urgent request: *Swap logo on banner*, editing, 0.5 h, due today 16:00." | Campaigns › Add an ad-hoc task, set to Urgent |
| D4 | "Carlo [Paolo] is pulled into a client meeting from 14:00 to 15:00." | Today › Team › Carlo [Paolo] › Block time |

## Interpretation questions (ask after the setup plan)

| # | Question | Correct answer (both scenarios) |
|---|---|---|
| Q1 | Which task has the earliest deadline today? | The urgent fix (typo [price] in the live ad [post]), due 11:00 |
| Q2 | Who can do writing work today? | Bea and Dani [Mika and Rina] |
| Q3 | What must happen before the video's Editing can start? | Script approval **and** Filming must both be confirmed |
| Q4 | Name one task that can't be done today, and why. | Any one of: video *Editing* (waiting for filming); *Graphic/video cut-downs* (no free 3-hour block); *Copy edit & layout* (its article draft finishes too late in the day) |
| Q5 | Which task is due at 12:00, and is it on time in your plan? | *Resize launch [event] banner*. Correct if their plan finishes it by 12:00 |

## Observer checklist (count each break as one violation)

- [ ] Nobody does two tasks at the same time.
- [ ] Nobody works outside their hours, during lunch, or during a meeting.
- [ ] Every task is done by someone with the required skill.
- [ ] Each task's block is at least its **upper** estimate.
- [ ] Nothing starts before its prerequisites finish. Nothing that depends on a ⚑ step starts before that step is confirmed.
- [ ] Ely [Tess] gets no work before D2.

## After all three participants

Fill in `results.csv` and run:

```bash
python docs/usability/summarize.py
```

It prints a summary table and paragraph for the report. **Report what you observe, including results where CampaignFlow is slower or no better.** With three people, describe the results; don't claim statistical significance.
