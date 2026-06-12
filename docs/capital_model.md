# Capital Model

This model converts measured PegGuard economics into LP-capital return.
It does not change hook constants and should not be used as calibration input.

Core formula:

```text
net APR = (base_fee_bps + PegGuard_extra_bps - truth_markout_bps)
          / 10_000 * daily_volume_per_active_capital * 365
```

Uniswap v3/v4 fees accrue only to in-range active liquidity. Capital size
therefore matters through `daily_volume_per_active_capital`, not just the
absolute dollars deposited.

Capital capacity formula:

```text
capital_capacity = expected_daily_volume_through_your_range
                   / target_daily_volume_per_active_capital
```

If the range sees $1,000,000/day and the strategy needs 5x turnover,
capacity for that range is about $200,000 of active capital.

## Measured Windows

| Window | Notional | Base fees | Truth markout | Extra | Extra bps | Markout bps | Precision | Capture | Static net bps | PegGuard net bps |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| calibrated calm | $1,034,588 | $517 | $417 | $96 | 0.93 | 4.03 | 92.42% | 22.98% | 0.97 | 1.90 |
| calibrated vol | $14,805,796 | $7,403 | $10,886 | $2,783 | 1.88 | 7.35 | 98.86% | 25.56% | -2.35 | -0.47 |

## APR Sensitivity

| Scenario | Net bps after markout | 1x turnover | 3x turnover | 5x turnover | 10x turnover |
|---|---:|---:|---:|---:|---:|
| calibrated calm | 1.90 | 6.92% | 20.76% | 34.60% | 69.20% |
| calibrated vol | -0.47 | -1.73% | -5.18% | -8.63% | -17.26% |

## Required Turnover

| Scenario | 10% APR | 20% APR | 30% APR | Comment |
|---|---:|---:|---:|---|
| calibrated calm | 1.4x/day | 2.9x/day | 4.3x/day | achievable only if active range gets this turnover |
| calibrated vol | n/a | n/a | n/a | avoid or hedge; net bps are negative |

## Capital Classes

Dollar results below use the live-shadow net rate because it is the most
conservative current forward-test measurement. The calibrated calm and
volatile rows above show what the same capital looks like under research
windows.

| Class | Capital | Target daily turnover | Indicative annual net $ | Range half-width | Operating parameter | Gate |
|---|---:|---:|---:|---|---|---|
| micro | $2,500 | 0.5-1.5x | $86-$259 | 3-5% | manual, at most weekly | do not scale; use shadow data and only deploy if fees exceed ops cost |
| small | $10,000 | 2-5x | $1,384-$3,460 | 1.5-3% | daily check, rebalance only when out of range | good pilot size; require >90% precision and >8% capture |
| focused | $25,000 | 3-6x | $5,190-$10,379 | 1-2% | active range manager | best small-capital fit if p90 oracle staleness stays <=5s |
| serious | $100,000 | 2-5x | $13,839-$34,598 | 1-3% ladder | ladder + inventory limits | scale only after multi-day capture >=15% at >=95% precision |
| large | $500,000 | 1-3x | $34,598-$103,794 | 2-5% ladder | market-maker process | capacity constrained; route-away and hedging matter more than hook alpha |

## Good Parameters

- Precision target: >=95% for scale-up; >=90% is the minimum economic floor.
- Capture target: >=15% before serious capital; >=20% is good.
- Oracle-health target: p90 observed staleness <=5s in calm and materially
  below the 2s volatile guard before relying on volatile-mode economics.
- Active turnover target: small capital needs >=3x daily volume/capital to be
  interesting; below 1x, the hook premium is too small to matter.
- Capacity cap: do not size so large that daily turnover/capital falls below
  2x unless the position is being run as a hedged market-making book.
- Rebalance discipline: narrow ranges create fee density but also inventory
  churn; rebalance only when out of range or when oracle health/capture gates
  say the strategy is live.

## Practical Conclusion

For small capital, the best strategy is not a passive wide LP. Use a tight,
active WETH/USDC range, keep capital modest until multi-day shadow reports
show >=15% capture at >=95% precision, and judge return by net fees after
truth markout rather than raw fee income.

