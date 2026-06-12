# Market-Regime Segments

This report segments economic performance by realized event markout intensity
and live oracle-lag/fallback rows. It also overlays low-L2 and stressed-L2
gas costs on each segment. Historical per-event gas is not available, so the
high-gas view is a scenario overlay, not an event classifier.

- Status: complete
- Live database: `/home/matseoi/workstation/uniswap/pegguard/shadow/live_shadow_20260607T082122Z.sqlite3`
- High-gas model: event-level historical gas is not available; high-gas is modeled with the existing stressed L2 gas scenario

| Window | Segment | Rows | Notional | Extra | Markout | Net | Net bps | Capture | Precision | Charged rows | Low L2 gas bps | Low L2 net bps | Stressed L2 gas bps | Stressed L2 net bps | Source |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| live shadow | all | 61883 | $68,328,953.14 | $2,904.24 | $41,864.56 | -$4,795.88 | -0.70 | 6.94% | 99.28% | 20141 | 0.0361 | -0.74 | 0.3608 | -1.06 | live DB truth |
| live shadow | quiet <1bp | 1359 | $1,623,550.04 | $252.07 | $52.00 | $1,011.84 | 6.23 | 484.71% | 100.00% | 1017 | 0.0333 | 6.20 | 0.3334 | 5.90 | live DB truth |
| live shadow | normal 1-5bp | 30885 | $31,466,454.90 | $1,861.98 | $9,961.90 | $7,633.30 | 2.43 | 18.69% | 100.00% | 17609 | 0.0391 | 2.39 | 0.3910 | 2.03 | live DB truth |
| live shadow | high-vol >=5bp | 29639 | $35,238,948.20 | $790.19 | $31,850.66 | -$13,441.02 | -3.81 | 2.48% | 97.37% | 1515 | 0.0335 | -3.85 | 0.3350 | -4.15 | live DB truth |
| live shadow | oracle-lag/fallback | 24794 | $27,017,658.56 | $0.00 | $17,319.50 | -$3,810.68 | -1.41 | 0.00% | n/a | 0 | 0.0366 | -1.45 | 0.3656 | -1.78 | live DB truth |
| calm | all | 628 | $1,032,053.51 | $95.87 | $417.03 | $194.87 | 1.89 | 22.99% | 92.42% | 470 | 0.0242 | 1.86 | 0.2424 | 1.65 | fixture truth |
| calm | quiet <1bp | 14 | $22,912.75 | $1.75 | $0.31 | $12.90 | 5.63 | 570.52% | 100.00% | 14 | 0.0243 | 5.60 | 0.2434 | 5.39 | fixture truth |
| calm | normal 1-5bp | 378 | $700,356.11 | $84.25 | $233.38 | $201.05 | 2.87 | 36.10% | 99.52% | 352 | 0.0215 | 2.85 | 0.2150 | 2.66 | fixture truth |
| calm | high-vol >=5bp | 236 | $308,784.65 | $9.87 | $183.34 | -$19.08 | -0.62 | 5.39% | 30.54% | 104 | 0.0304 | -0.65 | 0.3044 | -0.92 | fixture truth |
| calm | oracle-lag/fallback | 0 | $0.00 | $0.00 | $0.00 | $0.00 | 0.00 | n/a | n/a | 0 | 0.0000 | 0.00 | 0.0000 | 0.00 | not measured in fixture |
| vol | all | 3882 | $14,805,795.80 | $2,783.02 | $10,886.18 | -$700.27 | -0.47 | 25.56% | 98.86% | 1662 | 0.0104 | -0.48 | 0.1044 | -0.58 | fixture truth |
| vol | quiet <1bp | 244 | $810,303.77 | $199.42 | -$0.59 | $605.16 | 7.47 | 33740.28% | 100.00% | 222 | 0.0120 | 7.46 | 0.1199 | 7.35 | fixture truth |
| vol | normal 1-5bp | 958 | $3,444,955.01 | $647.85 | $404.59 | $1,965.73 | 5.71 | 160.12% | 100.00% | 777 | 0.0111 | 5.70 | 0.1108 | 5.60 | fixture truth |
| vol | high-vol >=5bp | 2680 | $10,550,537.02 | $1,935.75 | $10,482.18 | -$3,271.16 | -3.10 | 18.47% | 98.37% | 663 | 0.0101 | -3.11 | 0.1012 | -3.20 | fixture truth |
| vol | oracle-lag/fallback | 0 | $0.00 | $0.00 | $0.00 | $0.00 | 0.00 | n/a | n/a | 0 | 0.0000 | 0.00 | 0.0000 | 0.00 | not measured in fixture |

## Interpretation

- Markout regimes use absolute truth markout bps per event: quiet `<1bp`, normal `1-5bp`, high-vol `>=5bp`.
- Oracle-lag/fallback is measured only for live shadow because fixtures do not contain hot-path oracle freshness fields.
- Gas overlays reuse the economic-suite gas scenarios; they are cost stress tests, not claims about historical gas at each swap.
