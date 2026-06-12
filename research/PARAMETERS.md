# PARAMETERS.md - Data provenance for every constant

All experiments used real on-chain swaps at `sqrtPriceX96` precision, a
16-anchor piecewise real-time alignment, Binance 1 s candles, and Pyth
benchmark historical prices. The core method de-trends the pool-vs-fair spread
with a +/-300 s rolling median. Slow basis must not be charged: 62% of the raw
spread variance is slow basis, and failing to de-trend inflated fake capture to
224% compared with the real 17% result.

## Calibration windows

| Window | Pool | Reference | Result |
|---|---|---|---|
| calm 2026-05-30 20:04-22:30 UTC | Arbitrum WETH/USDC 0.05% (`0xC696...8D0`) | Binance ETHUSDC 1 s | 629 swaps, median Delta 0.82 bps, capture 17% |
| volatile 2026-05-23 17:00-21:00 UTC, 430 bps | Same pool | Pyth ETH/USD, 12-60 s adaptive | 6,444 swaps, median Delta 3.70 bps, capture about 24-26%, LP bleed 22x per hour |

## Contract constants and experiments

| Constant | Value | Source |
|---|---|---|
| `alphaNum/Den` | 1/2 (`alpha = 0.5`) | Premium slope used in all backtests. Capture is first-order linear in `alpha`. |
| `capPips` | 5000, or 50 bps | Backtest clamp. Limits extreme fees during oracle faults. |
| `MAX_STALENESS_CALM` | 5 s | Calm staleness sweep. 5 s still kept 95% precision; 2 s kept 98%, 10 s kept 91%, and 30 s kept 77%. |
| `MAX_STALENESS_VOL` | 2 s | Live hot-path Pyth pull staleness guard. Volatile staleness sweep showed precision decays about 2x: 2 s kept 95%, 5 s kept 87%, and 30 s kept 72%. Fixture `stale_s` is benchmark sampling granularity and must not be used as this gate. |
| `tauSec` | 450 s | Physical trailing equivalent of the research centered +/-300 s median. Corrected EventDiff sweep at 50 e2: tau 300/450/600 all satisfy volatile truth-capture >=20% and both precisions >=90%; 450 is the pinned midpoint-equivalent provenance value. |
| `CONF_ANOMALY_NUM` | 3x confidence EMA | Pyth confidence was about +/-9.9 bps, far larger than the roughly 1 bps signal. Absolute confidence gates never fired, so the hook uses a relative anomaly gate. |
| `deadbandCalmE2/deadbandVolE2` | 50 / 50 (`0.5` bp each) | Corrected per-regime EventDiff deadband tables at `tauSec = 450`. Calm: 92.42% precision and 22.98% truth capture at 50 e2, versus 90.83% / 28.21% at 0 e2 and 93.60% / 18.23% at 100 e2. Volatile: 98.86% precision and 25.56% truth capture at 50 e2, versus 98.45% / 26.98% at 0 e2 and 99.15% / 24.23% at 100 e2. Selected as the knee in each window. |
| `tripBps` in guard mode | 50 bps | Normal stable-pair cross-venue deviations were 0.000-0.35 bps and feed noise was about 0.2 bps, giving a strong signal-to-noise ratio at 50 bps. |
| Guard mode itself | N/A | Stable pairs showed no directional fuel. AMM basket capture was 0.6%; adding CEX reached only 6.3%, with 58% correlation, roughly random. |
| RSC `TRIG_BPS/WINDOW` | 40 bps / 180 s | SentinelCalibration sweep on corrected `sentinel_mainnet_vol.json` (1,108 swaps, 418 bps; SHA-256 `4eb34aa08f1da2dcd4b668b6ebadbd4329ac1813c3af5c03f8f6b5e2bbae8348`) and 250-event calm sentinel. `40/180` had zero calm false positives, first volatile trigger at +4332 s, and 6 volatile triggers. This arms the volatile regime 74 minutes before the measured heavy-bleed window begins at +8759 s; bleed during the unmeasured ramp, where 180s ranges stay below 40 bps throughout, is expected to be small but was not measured. `60/*` bled about $2,399 before trigger, measured in-window. |
| RSC `REGIME_TTL` | 30 min | A 60 s-late regime change cost about 0.4% of episode bleed, so minute-scale control-plane latency is acceptable. |
| `MIN_DISARM_DELAY` | 30 min | Depeg-disarm hysteresis. Tightening is immediate; loosening is delayed. |

## Architecture conclusions

1. The hot path must use Pyth pull prices. The relevant race clock is the pool's
   roughly 14 s update interval, not the arbitrageur's sub-2 s execution. Pyth
   at 2 s staleness retains 88% of edge.
2. Staleness is a trap. In volatility, older oracle data raises measured revenue
   from 25% to 41% while precision collapses from 95% to 72%. Revenue metrics can
   reward bad operation, so the live Pyth pull staleness guard is a hard rule.
   This is distinct from fixture `stale_s`, which records historical benchmark
   sampling granularity and is not a charging condition.
3. The ceiling for inverse-variance consensus is the best member. An AMM-only
   basket captured 3%; adding CEX reached the pure CEX result of 44%. Pairs with
   CEX feeds should use Pyth directly. Baskets are reserved for long-tail pairs
   without feeds and are not implemented here.
4. Reactive Network belongs only in the control plane. Regime changes, breaker
   signals, and baseline upkeep have minute-scale budgets where delivery latency
   is acceptable, and cross-chain observation is useful.

## Open items

- Broader RSC false-positive coverage beyond the supplied 250-event calm
  sentinel fixture.
- Route-away elasticity; all capture figures are same-swaps upper bounds.
- Guard-mode dual-feed ratio, for example USDC/USD divided by USDT/USD. The
  current skeleton uses a single feed.
