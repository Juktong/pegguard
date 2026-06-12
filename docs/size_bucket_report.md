# Trade-Size Buckets

This report segments measured economics by quote-notional trade size. It
checks whether precision, capture, and net PnL survive outside the aggregate
average.

| Window | Bucket | Rows | Notional | Base | Extra | Markout | Net | Net bps | Extra bps | Markout bps | Precision | Capture | Positive rows |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| live shadow | <$1k | 38176 | $15,809,321.18 | $7,904.64 | $414.71 | $8,939.15 | -$619.79 | -0.39 | 0.26 | 5.65 | 98.37% | 4.64% | 53.81% |
| live shadow | $1k-$10k | 23496 | $48,381,017.03 | $24,190.50 | $1,637.56 | $30,259.58 | -$4,431.53 | -0.92 | 0.34 | 6.25 | 99.15% | 5.41% | 54.22% |
| live shadow | $10k-$50k | 202 | $3,411,862.46 | $1,705.93 | $501.53 | $2,442.02 | -$234.55 | -0.69 | 1.47 | 7.16 | 99.98% | 20.54% | 41.09% |
| live shadow | >=$50k | 9 | $726,752.48 | $363.38 | $350.44 | $223.82 | $490.00 | 6.74 | 4.82 | 3.08 | 100.00% | 156.57% | 44.44% |
| calm | <$1k | 295 | $120,049.95 | $60.02 | $9.09 | $53.60 | $15.52 | 1.29 | 0.76 | 4.46 | 84.00% | 16.96% | 62.37% |
| calm | $1k-$10k | 331 | $890,731.82 | $445.37 | $86.06 | $352.99 | $178.43 | 2.00 | 0.97 | 3.96 | 93.25% | 24.38% | 79.15% |
| calm | $10k-$50k | 2 | $21,271.74 | $10.64 | $0.72 | $10.44 | $0.92 | 0.43 | 0.34 | 4.91 | 100.00% | 6.93% | 50.00% |
| calm | >=$50k | 0 | $0.00 | $0.00 | $0.00 | $0.00 | $0.00 | 0.00 | 0.00 | 0.00 | n/a | n/a | 0.00% |
| vol | <$1k | 958 | $339,677.86 | $169.84 | $51.26 | $198.38 | $22.71 | 0.67 | 1.51 | 5.84 | 99.09% | 25.84% | 49.90% |
| vol | $1k-$10k | 2663 | $9,991,107.76 | $4,995.55 | $1,602.11 | $6,857.68 | -$260.02 | -0.26 | 1.60 | 6.86 | 98.65% | 23.36% | 44.80% |
| vol | $10k-$50k | 254 | $4,070,026.23 | $2,035.01 | $734.62 | $4,029.90 | -$1,260.27 | -3.10 | 1.80 | 9.90 | 98.70% | 18.23% | 37.80% |
| vol | >=$50k | 7 | $404,983.94 | $202.49 | $395.03 | -$199.79 | $797.31 | 19.69 | 9.75 | -4.93 | 100.00% | 197.73% | 57.14% |

## Interpretation

- Buckets use absolute quote notional, so they are comparable across fixtures and live shadow.
- Empty buckets remain in the table to make missing size coverage visible.
- Precision is premium-weighted and only defined for buckets with charged premium.
