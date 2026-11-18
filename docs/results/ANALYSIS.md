# Analysis results

## Optimality gap (120 random 7-task days per regime, brute force over 5,040 orders)

| regime | policy | matches optimum | same late count | extra late tasks (mean) | extra lateness min (mean) | extra unplaced (mean) |
|---|---|---|---|---|---|---|
| overloaded morning (4 h) | deadline | 24.2% | 30.8% | 0.45 | 31.3 | 0.38 |
| overloaded morning (4 h) | entry | 15.8% | 30.0% | 0.42 | 33.4 | 0.34 |
| normal day (8 h) | deadline | 35.8% | 53.3% | 0.56 | 37.7 | 0.05 |
| normal day (8 h) | entry | 21.7% | 36.7% | 0.79 | 81.4 | 0.02 |

## Search pruning (identical schedules asserted)

| n | naive ms | pruned ms | speedup |
|---|---|---|---|
| 1000 | 17.4 | 13.1 | 1.33x |
| 2500 | 92.3 | 71.8 | 1.29x |
| 5000 | 418.4 | 304.4 | 1.37x |
| 10000 | 1446.8 | 1089.5 | 1.33x |
