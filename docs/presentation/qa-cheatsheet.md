# CampaignFlow Q&A cheat sheet

Short answers first; the detail is underneath in case of follow-ups. Every number here comes from our own tests and benchmarks (`docs/results/`, report §6–8).

## Data structures

**Why a min-heap instead of keeping a sorted list?**
Each placement can release new ready tasks. A heap handles that with push and pop in O(log n), and builds the initial set in O(n). A sorted Python list needs O(n) per insert because elements shift, even with `bisect`, and re-sorting after every placement costs O(n log n) each time.

**Why write your own heap instead of using `heapq`?**
The course asks us to implement the structures. We use `heapq` only as a test oracle: our heap matches it over 5,000 random push/pop operations, with the heap property checked after each one.

**Why adjacency lists and not an adjacency matrix?**
The dependency graph is sparse (fewer than one edge per task on average). Lists use O(n + e) space, versus Θ(n²) for a matrix, and iterating a task's successors costs only as much as there are successors. We store both successor and predecessor lists, so "what does finishing this release?" and "what is this waiting on?" are both instant.

**What does the heap key look like?**
`(urgency rank, deadline, task ID)`, where urgent = 0 and normal = 1. The task ID makes ties deterministic. The baseline policy uses `(urgency rank, entry order, task ID)`. Changing the key is the *only* difference between the two policies, which makes the comparison fair.

## Algorithms

**Why DFS for cycle detection rather than Kahn's topological sort?**
Both are O(n + e). Three-colour DFS points straight at the loop: reaching a gray node means an edge back into the current path, and parent pointers give the exact cycle to show the user. Kahn's algorithm tells you a cycle exists (some nodes never reach in-degree 0), but finding *which* loop takes extra work. For readiness we still use Kahn-style counters inside the allocator.

**Why iterative DFS?**
Python's default recursion limit is 1,000. A long dependency chain would crash a recursive DFS. We use an explicit stack of (node, next-child index) frames, and a test checks a 5,000-task chain.

**How does the allocator know a task is ready?**
Each task keeps a count of unfinished prerequisites, like in-degree in Kahn's algorithm. When a prerequisite is placed (with same-day release on) or is marked done, its successors' counts go down. A task enters the heap when its count reaches zero. External gates (filming, approvals) never count down until the manager confirms them.

**Is the greedy schedule optimal?**
No. Scheduling with dependencies, skills and limited people is a form of the resource-constrained project scheduling problem, which is NP-hard (Błażewicz et al., 1983). We measured the gap by brute-forcing all 5,040 orders of 7-task days:
- **Normal days:** deadline-first reached the optimal late-task count on **53%** of days, versus **37%** for first-come, first-served, and its excess lateness was about half (38 vs 81 minutes).
- **Deliberately overloaded mornings:** both rules reach the optimum on only about 30% of days, because greedy doesn't look ahead to pack the day.

**Why earliest-deadline-first?**
It's simple, easy to explain, and optimal for maximum lateness on a *single* machine (Jackson's rule, 1955). With several people, skills and dependencies there's no such guarantee. That's why we tested it rather than assumed it; Türkakın et al. (2021) found priority rules perform differently under different resource conditions.

**How are ties between people broken?**
Earliest finish first, then the person with *fewer* skills, then ID. Preferring the specialist keeps generalists free for work only they can do.

**Do the pruning rules change the answer?**
No, and we assert identical schedules in the benchmark.
1. Skipping someone whose longest free block is shorter than the task is safe: they can't fit it.
2. Staff are scanned in tie-break order, so once someone can start at the earliest possible moment, nobody later can beat them.

The two rules made allocation 1.2–1.4× faster.

## Complexity

**What's the overall complexity?**
- **Validation:** O(n + e).
- **Allocation:** O(n log n + e + n·s·w). Each task is pushed and popped at most once (n log n), each dependency is resolved once (e), and each task scans its qualified staff's free intervals (n·s·w).
- **Space:** O(n + e + s·w).

**Your chart shows allocation growing like n^1.9. Isn't that quadratic?**
In the benchmark the team grows with the workload: s is proportional to n. Plotted against tasks × staff, the slope is **0.96**, which is linear in n·s, exactly as the analysis predicts. For a fixed team size it grows roughly linearly in n.

**How did you measure?**
We used `time.perf_counter_ns` over 10 fresh workloads per size, timing validation and allocation separately. Data generation and correctness checks are excluded from the timings. Memory was measured in a separate run with `tracemalloc`, so the tracing overhead doesn't distort the times.

**Headline numbers?**
- **250 tasks, 38 staff:** validation 0.20 ms, allocation 1.66 ms.
- **10,000 tasks, 1,480 staff:** validation 15 ms, allocation 1.1 s.
- **Memory:** grows linearly (slope 1.02).

## Correctness & testing

**How do you know the schedules are valid?**
An *independent* invariant checker re-derives every hard rule from the raw inputs, without using the allocator's bookkeeping:
- no overlaps for any person
- inside working hours, minus meetings
- skill match
- reserved time equals the upper estimate
- prerequisites finish before dependents start
- gates confirmed before dependent work starts
- locked work unchanged
- every pending task either placed or explained

It runs on 160 randomized workloads (40 seeds × 2 policies × 2 release modes). A mutation test confirms it catches injected errors.

**Hardest bug?**
If a committed task was later marked done, its successors were released twice. That could start a task before its *other* prerequisite was finished. We found it while building the web store, fixed it, and added a regression test.

## Design & honesty

**What if the estimates are wrong?**
We reserve the *upper* estimate, so plans are conservative. The interface says plans are conditional, not promises. In a replay where real durations ran 20% longer than the estimates, deadline-first still had fewer late tasks: 36.5 vs 47.0 per 250-task day. The trade-off is that capacity can go unused when work finishes early.

**What's "same-day release", and why did you change it from the proposal?**
The proposal released dependent work only after a prerequisite was *confirmed* complete. That left most chained work unscheduled for the day. Same-day release lets a follow-up task start after its prerequisite's *planned* finish. External gates still always wait for confirmation. It's a visible setting, and the report records the deviation.

**Why not just use Asana?**
Asana tracks dependencies and workload very well. CampaignFlow's narrower job is to *recommend* a feasible sequence for today, with reasons for anything that can't start. We don't claim to outperform Asana; the project applies and measures course algorithms on that decision.

**Is this tested with real agencies?**
Not yet. All quantitative results use clearly labelled synthetic workloads. The three-person usability study planned in our proposal wasn't run within the project period, so we make no claims about time saved for coordinators.

**What happens if someone adds a meeting over a locked commitment?**
Validation flags it as a hard conflict and planning pauses until the manager reviews it or unlocks the commitment. We never silently move locked work.

**Can several people use it at once? Does it scale to a bigger agency?**
Version 1 is single-agency, with one JSON file written atomically. Every change bumps a version number, so a stale plan can't be accepted. A real deployment would need a database and user accounts (listed in future work).

**How was the trailer made?**
It's rendered from code: real app footage captured with Playwright, motion graphics in GSAP, and a frame-by-frame render through ffmpeg. **The voiceover is AI-generated** (the open-source Kokoro text-to-speech model), and the music is synthesized. Say so plainly if asked.
