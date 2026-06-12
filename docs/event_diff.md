# Event Diff

Status: completed with the immutable truth fixtures from
`pegguard-truth-fixtures.zip`.

Command:

```bash
forge test --match-contract EventDiffTest -vv
```

`test/EventDiff.t.sol` replays the calm and volatile swap fixtures with the
same causal signal pipeline as the hook:

- pre-swap mid pricing from the previous post-swap pool price
- trailing basis EMA
- e2-resolution deviation and premium math
- post-swap basis update after every replayed benchmark event

The volatile fixture's `stale_s` field is the research benchmark sampling
interval for historical Pyth prices, not live on-chain Pyth pull staleness.
It is used only for stratified reporting, for example the `<=15s` sensitivity
row, and must never gate charging or basis updates in this harness.

The harness verifies index alignment by asserting `t_ms` equality between each
swap row and its truth row. The objective metric is premium-weighted precision:
the share of charged premium landing on `truth_corr == 1` swaps. Raw capture is
not a calibration objective.

## Root Cause

The previous EventDiff harness incorrectly treated fixture `stale_s` as if it
were on-chain oracle staleness and charged only rows with `stale_s <= 2`. That
suppressed volatile pricing to 566 of 3,882 events and produced the false
`0.66%` volatile truth-capture baseline. Removing that gate restores agreement
with the independent mirror.

| Run | tauSec | Deadband e2 | Vol priced rows | Vol precision | Vol truth capture | Vol dev MAE e2 |
|---|---:|---:|---:|---:|---:|---:|
| stale_s-gated artifact | 150 | 50 | 566 | 93.18% | 0.66% | 442 |
| corrected baseline | 450 | 50 | 3,881 | 98.86% | 25.56% | 224 |

## Baseline Metrics

Final selected settings: `tauSec = 450`,
`deadbandCalmE2 = deadbandVolE2 = 50`.

| Window | Rows | Valid | Priced | Charged | Precision | Sign agree | Dev median e2 | Dev p90 e2 | Dev MAE e2 | Truth capture |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| calm 2026-05-30 | 629 | 628 | 628 | 470 | 92.42% | 80.85% | 120 | 334 | 158 | 22.98% |
| volatile 2026-05-23 hot 90m | 3882 | 3882 | 3881 | 1662 | 98.86% | 93.32% | 179 | 467 | 224 | 25.56% |

Denominator decomposition:

| Window | Extra, e6 | Trailing-F markout, e6 | Trailing-F capture | Truth markout, e6 | Truth capture |
|---|---:|---:|---:|---:|---:|
| calm | 95,870,346 | 310,528,829 | 30.87% | 417,029,131 | 22.98% |
| volatile | 2,783,019,326 | 11,341,029,222 | 24.54% | 10,886,183,493 | 25.56% |

Sampling-granularity sensitivity at `tauSec = 450`, deadband `50 e2`:

| Slice | Precision | Truth capture | Dev MAE e2 |
|---|---:|---:|---:|
| volatile rows with `stale_s <= 15` | 98.66% | 31.38% | 238 |

## Tau Sweep

Sweep used the selected 50 e2 deadband.

| tauSec | Calm precision | Calm capture | Calm MAE e2 | Vol precision | Vol capture | Vol MAE e2 |
|---:|---:|---:|---:|---:|---:|---:|
| 150 | 94.41% | 15.22% | 119 | 96.16% | 22.14% | 366 |
| 300 | 93.13% | 20.09% | 137 | 98.15% | 24.67% | 260 |
| 450 | 92.42% | 22.98% | 158 | 98.86% | 25.56% | 224 |
| 600 | 91.48% | 25.16% | 175 | 99.05% | 26.07% | 214 |
| 900 | 89.17% | 28.37% | 201 | 99.03% | 26.70% | 215 |

Selected `tauSec = 450`. The physical provenance is the trailing equivalent of
the centered +/-300s median used in the research de-trend; the allowed range is
300-600s. `450` satisfies the joint constraints: volatile truth-capture is at
least 20%, and both calm and volatile precision are at least 90%.

## Deadband Table

Sweep used `tauSec = 450`.

| Deadband e2 | Calm precision | Calm capture | Vol precision | Vol capture |
|---:|---:|---:|---:|---:|
| 0 | 90.83% | 28.21% | 98.45% | 26.98% |
| 25 | 91.71% | 25.55% | 98.67% | 26.26% |
| 50 | 92.42% | 22.98% | 98.86% | 25.56% |
| 75 | 93.06% | 20.54% | 99.02% | 24.89% |
| 100 | 93.60% | 18.23% | 99.15% | 24.23% |
| 125 | 93.96% | 16.11% | 99.27% | 23.60% |
| 150 | 94.31% | 14.18% | 99.36% | 22.98% |
| 175 | 94.86% | 12.44% | 99.44% | 22.39% |
| 200 | 95.62% | 10.87% | 99.50% | 21.81% |

`deadbandCalmE2 = 50` and `deadbandVolE2 = 50` remain selected. At 50 e2 the
calm window gains precision versus no deadband while retaining most of the
truth-denominated capture; the volatile window is essentially unchanged and
stays well above the economic floor.
