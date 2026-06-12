# Base-Fee Adequacy

This report measures whether the configured base fee is sufficient after
truth markout and PegGuard dynamic premium. It is measurement only and does
not change hook constants.

- Source: `/home/matseoi/workstation/uniswap/pegguard/docs/live-shadow-20260607T082122Z/economic_tests.json`
- Current base fee: 5.00 bps

| Window | Strategy | Current net bps | Required base for 0 bps net | Required base for 1 bps net | Required base for 5 bps net | Surplus vs 0 bps | Surplus vs 1 bps | Surplus vs 5 bps |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| live shadow | PegGuard live shadow | -0.62 | 5.62 bps | 6.62 bps | 10.62 bps | -0.62 bps | -1.62 bps | -5.62 bps |
| calm | PegGuard selected | 1.89 | 3.12 bps | 4.12 bps | 8.12 bps | +1.88 bps | +0.88 bps | -3.12 bps |
| vol | PegGuard selected | -0.47 | 5.48 bps | 6.48 bps | 10.48 bps | -0.48 bps | -1.48 bps | -5.48 bps |

## Interpretation

- Required base fee is computed after applying the measured PegGuard extra premium.
- Negative surplus means the current 5 bps base fee is below the required level for that target.
- A high required base fee may not be routeable; compare this with route-away proxy and controlled route-away results.
