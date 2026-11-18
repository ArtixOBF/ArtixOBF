# Benchmark results (synthetic workloads)

## Runtime scaling

| n | edges | staff | validate_ms | validate_sd | allocate_ms | allocate_sd | peak_kib |
|---|---|---|---|---|---|---|---|
| 10 | 6 | 2 | 0.014 | 0.004 | 0.05 | 0.019 | 5.7 |
| 50 | 25 | 9 | 0.04 | 0.004 | 0.179 | 0.02 | 26.9 |
| 100 | 45 | 15 | 0.076 | 0.006 | 0.392 | 0.035 | 48.5 |
| 250 | 134 | 38 | 0.199 | 0.024 | 1.662 | 0.873 | 118.3 |
| 1000 | 584 | 150 | 0.743 | 0.044 | 13.395 | 0.897 | 472.5 |
| 2500 | 1505 | 370 | 2.041 | 0.036 | 71.014 | 5.177 | 1269.8 |
| 5000 | 3014 | 745 | 4.726 | 0.743 | 276.94 | 38.703 | 2328.0 |
| 10000 | 6077 | 1480 | 14.811 | 5.834 | 1113.214 | 73.095 | 5141.1 |

## Policy comparison (means over seeds)

| scenario | n | policy | on_time_rate | at_risk | projected_lateness_h | replay_late | allocated | capacity_omitted |
|---|---|---|---|---|---|---|---|---|
| baseline | 10 | deadline | 0.696 | 1.8 | 3.3 | 1.8 | 5.8 | 1.1 |
| baseline | 10 | entry | 0.708 | 1.8 | 3.9 | 1.6 | 5.8 | 0.9 |
| baseline | 50 | deadline | 0.72 | 9.1 | 20.6 | 8.8 | 32.6 | 3.1 |
| baseline | 50 | entry | 0.679 | 10.6 | 25.0 | 10.4 | 33.0 | 3 |
| baseline | 100 | deadline | 0.754 | 15 | 33.6 | 14.9 | 60.8 | 6.3 |
| baseline | 100 | entry | 0.708 | 18.3 | 42.0 | 18.1 | 62.4 | 5.2 |
| baseline | 250 | deadline | 0.767 | 36.4 | 82.0 | 36.5 | 155.8 | 15.1 |
| baseline | 250 | entry | 0.701 | 47.6 | 108.3 | 47.0 | 159 | 12.2 |
| overload | 10 | deadline | 0.672 | 1.9 | 3.5 | 1.9 | 5.8 | 1.1 |
| overload | 10 | entry | 0.709 | 1.8 | 4.1 | 1.6 | 5.7 | 1 |
| overload | 50 | deadline | 0.604 | 10.5 | 21.2 | 10.3 | 26.6 | 6.5 |
| overload | 50 | entry | 0.595 | 10.6 | 29.7 | 10.6 | 26.1 | 6.9 |
| overload | 100 | deadline | 0.662 | 17.1 | 33.2 | 16.9 | 50.4 | 12.5 |
| overload | 100 | entry | 0.632 | 18.4 | 48.2 | 17.7 | 49.8 | 12.5 |
| overload | 250 | deadline | 0.668 | 43.4 | 88.6 | 43.1 | 130.3 | 31.2 |
| overload | 250 | entry | 0.619 | 48.9 | 132.6 | 48.8 | 128.3 | 31 |
| slack | 10 | deadline | 0.966 | 0.2 | 0.5 | 0.2 | 6.8 | 0.6 |
| slack | 10 | entry | 0.954 | 0.3 | 0.7 | 0.3 | 6.8 | 0.6 |
| slack | 50 | deadline | 0.981 | 0.7 | 1.7 | 0.7 | 33.9 | 2.3 |
| slack | 50 | entry | 0.978 | 0.8 | 1.9 | 0.8 | 34.0 | 2.2 |
| slack | 100 | deadline | 0.984 | 1.1 | 2.1 | 0.9 | 66.0 | 4.0 |
| slack | 100 | entry | 0.98 | 1.3 | 2.4 | 1.2 | 65.8 | 4.2 |
| slack | 250 | deadline | 0.982 | 3.1 | 8.9 | 3.1 | 168.3 | 9.4 |
| slack | 250 | entry | 0.977 | 4.0 | 9.5 | 4 | 168.4 | 9.6 |
| dense-deps | 10 | deadline | 0.678 | 1.9 | 4.0 | 1.8 | 5.8 | 1.1 |
| dense-deps | 10 | entry | 0.694 | 1.9 | 4.1 | 1.8 | 5.8 | 1.1 |
| dense-deps | 50 | deadline | 0.698 | 6.0 | 19.0 | 6.1 | 20 | 3.7 |
| dense-deps | 50 | entry | 0.694 | 6.3 | 19.3 | 6.2 | 20.1 | 3.7 |
| dense-deps | 100 | deadline | 0.731 | 10.2 | 28.4 | 10.1 | 37.1 | 4.7 |
| dense-deps | 100 | entry | 0.714 | 10.8 | 29.6 | 10.6 | 37.1 | 4.5 |
| dense-deps | 250 | deadline | 0.767 | 21.6 | 58.6 | 21.6 | 92.4 | 9.3 |
| dense-deps | 250 | entry | 0.757 | 22.8 | 61.1 | 22.6 | 93.3 | 9.1 |
| fragmented | 10 | deadline | 0.676 | 1.6 | 3.4 | 1.6 | 5.0 | 1.8 |
| fragmented | 10 | entry | 0.737 | 1.4 | 3.7 | 1.4 | 5.0 | 1.6 |
| fragmented | 50 | deadline | 0.719 | 8.0 | 18.2 | 7.8 | 28.2 | 6 |
| fragmented | 50 | entry | 0.677 | 9.3 | 23.7 | 9.1 | 28.6 | 5.5 |
| fragmented | 100 | deadline | 0.74 | 14.1 | 31.5 | 14 | 53.9 | 10.7 |
| fragmented | 100 | entry | 0.702 | 16.6 | 38.5 | 15.8 | 55.4 | 9.7 |
| fragmented | 250 | deadline | 0.737 | 37.1 | 80.9 | 36.9 | 141.2 | 24.4 |
| fragmented | 250 | entry | 0.692 | 44.3 | 104.0 | 43.9 | 143.7 | 21.6 |
