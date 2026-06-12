# Replay Baseline

The regression baseline is event-level truth agreement in
`test/EventDiff.t.sol`, not aggregate capture. Aggregate capture is logged by
`test/SignalReplay.t.sol` only as a diagnostic because loose or stale signals
can raise raw capture while precision collapses.

Final selected settings:

- `tauSec = 450`
- `deadbandCalmE2 = 50`
- `deadbandVolE2 = 50`

## Enforced Assertions

Command:

```bash
forge test --match-contract EventDiffTest -vv
```

| Window | Measured precision | Assert precision >= | Measured truth capture | Assert truth capture | Economic capture floor | Measured MAE e2 | Assert MAE e2 <= |
|---|---:|---:|---:|---:|---:|---:|---:|
| calm 2026-05-30 | 92.42% | 90.00% | 22.98% | 17.23-28.72% | 8.00% | 158 | 237 |
| volatile 2026-05-23 hot 90m | 98.86% | 93.86% | 25.56% | 19.17-31.95% | 15.00% | 224 | 336 |

Assertions combine the corrected measured baseline with permanent economic
floors: precision must never fall below 90%, calm truth-capture must never fall
below 8%, and volatile truth-capture must never fall below 15%.

## Baseline Table

| Window | Rows | Valid | Priced | Charged | Precision | Sign agree | Dev median e2 | Dev p90 e2 | Dev MAE e2 | Truth capture |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| calm 2026-05-30 | 629 | 628 | 628 | 470 | 92.42% | 80.85% | 120 | 334 | 158 | 22.98% |
| volatile 2026-05-23 hot 90m | 3882 | 3882 | 3881 | 1662 | 98.86% | 93.32% | 179 | 467 | 224 | 25.56% |

## Aggregate Diagnostics

Command:

```bash
forge test --match-contract SignalReplayTest -vv
```

| Window | Swaps | Static markout, e6 | Extra premium, e6 | Aggregate capture |
|---|---:|---:|---:|---:|
| calm 2026-05-30 | 629 | 310,528,829 | 95,870,346 | 30% |
| volatile 2026-05-23 hot 90m | 3882 | 11,341,029,222 | 2,783,019,326 | 24% |

These aggregate figures are useful for sanity checks and demos, but they are
not pass/fail calibration targets.
