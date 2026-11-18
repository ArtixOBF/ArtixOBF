# CampaignFlow presentation: run sheet & demo script

Target length is **14 min 20 s**, inside the 10–15 minute limit. The slides are in the CampaignFlow deck, and every slide has its talking points in the speaker notes.

## Before you start (5 minutes before)

- [ ] Start the app on the presenting laptop: `python -m campaignflow.web.app`. Open http://127.0.0.1:5000 in its own browser window.
- [ ] In the app sidebar, click **Reset demo** so the data matches this script.
- [ ] Set the browser zoom to 100% and close every other tab.
- [ ] Open the trailer (`docs/videos/campaignflow-trailer.mp4`) or embed it on slide 2. **Test the sound on the room's speakers.**
- [ ] Have the backup clips ready to play: `docs/videos/02-plan-and-compare.mp4` and `05-cycle-detection.mp4`.
- [ ] Put the Q&A cheat sheet (`docs/presentation/qa-cheatsheet.md`) on a phone.

## Run sheet

| # | Slide | Time | Running | Who |
|---|---|---|---|---|
| 1 | Cover | 0:20 | 0:20 | A |
| 2 | Trailer (video) | 2:00 | 2:20 | (video) |
| 3 | The problem | 1:00 | 3:20 | A |
| 4 | Why arrival order fails | 1:00 | 4:20 | A |
| 5 | Three steps, every morning | 0:45 | 5:05 | A |
| 6 | Two data structures, two algorithms | 0:45 | 5:50 | B |
| 7 | Graph + DFS | 0:50 | 6:40 | B |
| 8 | Min-heap | 0:50 | 7:30 | B |
| 9 | Greedy allocation | 0:50 | 8:20 | B |
| 10 | **Live demo** | 3:00 | 11:20 | A drives, B narrates |
| 11 | Testing | 0:40 | 12:00 | A |
| 12 | Complexity | 0:50 | 12:50 | B |
| 13 | Schedule quality | 0:50 | 13:40 | B |
| 14 | Limitations & next steps | 0:30 | 14:10 | A |
| 15 | Close + questions | 0:10 | 14:20 | A |

"A" and "B" are placeholders; decide between you who takes which part. **If you're running long**, shorten slide 6 to one sentence, or skip slide 5 (the demo shows the same flow). Don't rush the demo.

## Live demo (3:00)

**0:00 Today page.** "This is Today. Instead of a big form, it asks only what changed."
1. Point at the **"2 things need you"** card.
2. Click **Yes** next to *Script approval*: "The client approved the script."
3. Click **Yes** next to *Ely*: "Ely is in today, so the planner can now use Ely."

**0:30 Plan page.** Click **Plan my day**.
4. Read the headline sentence aloud: *6 tasks scheduled, all on time*.
5. Hover over a couple of timeline bars: "Each person's day, planned around meetings and lunch. That's the greedy allocator, fed by the heap."

**1:10 Compare the two rules.** Switch **Prioritise by** to **Order received**.
6. "Same data, first come, first served." The *Resize banner* bar turns **red**, and the headline now says *1 at risk*.
7. Switch back to **Deadline**: "Deadline-first fixes it. That's the comparison from our proposal, live."

**1:40 Lock in.** Scroll to the schedule.
8. Untick one task and click **Lock in plan**. Let the confetti play.
9. "Locked work never moves when we replan. Unlock gives it back." Optionally click **Unlock** on one task.

**2:20 Break it on purpose.** Go to **Today**, find *Article draft* (Launch article), and click its **edit** (pencil) icon.
10. In *Prerequisites*, search "copy" and tick **Copy edit & layout**, then click **Save changes**.
11. The red error names the loop: *Article draft → Copy edit & layout → Article draft*. Say: "Depth-first search caught the cycle before it could reach the planner, and nothing was saved."

**3:00** Go back to the slides.

### If something breaks
- **App won't start or the page errors:** play `docs/videos/02-plan-and-compare.mp4` and `05-cycle-detection.mp4` and narrate over them.
- **Data looks different from this script:** click **Reset demo** in the sidebar and carry on. The headline numbers return to *6 tasks, all on time*.
- **Confetti doesn't show:** keep going. The "Locked in" list proves the commit worked.
