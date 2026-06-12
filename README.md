# PegGuard - Measured IL Insurance (Uniswap v4 Hook)

LVR is the systematic, priceable part of impermanent loss. PegGuard makes the
flow that causes IL pay for it: a dual-mode dynamic-fee hook whose parameters
are calibrated from real on-chain backtests.

- Harvest mode (volatile/LST pairs): correcting-direction flow pays an
  insurance premium `alpha * |Delta|` priced off the de-trended Pyth deviation.
  Measured recovery: about 17% of LP markout bleed in calm conditions and about
  25% in the original centered-median research. The corrected event-level hook
  replay is baselined on premium-weighted precision: 92.42% on the calm window
  and 98.86% on the volatile hot window under the selected defaults.
- Guard mode (stable/anchored pairs): measurements showed no harvestable
  directional fuel for stables. Cross-venue deviations were 0.000-0.35 bps,
  below feed noise, so the hook only provides a depeg circuit breaker.
- Invariant: never worse than a static pool. Stale oracle data, confidence
  anomalies, or unseeded basis all fall back to the symmetric base fee. The hook
  should never revert a swap.

## Why this design

1. Slow-basis de-trending is mandatory. 62% of the raw pool-vs-CEX gap is slow
   venue/quote basis. A naive deviation hook taxes it, inflating fake capture
   from the real 17% result to 224%. On-chain, PegGuard uses a trailing basis
   EMA (`tauSec = 450`), the physical trailing equivalent of the research
   centered +/-300 s median.
2. The oracle race is winnable. The relevant clock is the pool's roughly 14 s
   update staleness, not the arbitrageur's sub-2 s execution. Pyth at 2 s
   staleness retains 88% of edge.
3. The staleness trap matters. In volatility, a staler oracle raises measured
   revenue from 25% to 41% while precision collapses from 95% to 72%. Revenue
   metrics can reward bad operation, so live Pyth pull staleness guards are hard
   rules: 5 s in calm conditions and 2 s in volatile conditions. Historical
   fixture `stale_s` is benchmark sampling granularity, not this live guard.
4. Confidence is a relative signal. Pyth confidence, around +/-10 bps, is much
   larger than the target signal, around 1 bps. Absolute confidence gates never
   fire in these windows, so PegGuard gates on confidence relative to its own EMA
   at 3x.

Full provenance: [`research/PARAMETERS.md`](research/PARAMETERS.md).

## Architecture

```text
Hot path, 2-5 s budget:
  beforeSwap
    - Pyth pull plus staleness guard
    - confidence relative-anomaly gate
    - basis EMA de-trending
    - directional premium in harvest mode
    - depeg breaker in guard mode
  afterSwap
    - basis and confidence EMA upkeep, skipped if stale

Control plane, minutes budget:
  Reactive Network
    - VolSentinelRSC watches mainnet canonical pool swaps
    - 40 bps / 3 min trigger, calibrated to zero calm false positives
    - cross-chain callback to RegimeReceiver
    - hook.onRegimeSignal(VOLATILE, ttl)

Safety rule:
  Tighten instantly, loosen with delay. TTL expiry means a Reactive Network
  outage degrades gracefully.
```

## Partner integrations

| Partner | What | Where in code |
|---|---|---|
| Pyth | Pull-oracle fair value, staleness gates, and confidence gates on the hot path | `src/PegGuardHook.sol` (`_readOracle`, `MAX_STALENESS_*`, `CONF_ANOMALY_NUM`) and `src/interfaces/IPyth.sol` |
| Reactive Network | Cross-chain volatility sentinel and breaker control plane | `src/reactive/VolSentinelRSC.sol`, `src/reactive/RegimeReceiver.sol`, and `src/interfaces/IRegimeSignal.sol` |

PegGuard deliberately does not use Reactive Network as a price oracle because
precision collapses beyond 2-5 s staleness in volatility. It also does not use
confidence as an absolute gate because that gate did not fire in the measured
windows.

The selected sentinel trigger arms the volatile regime 74 minutes before the
measured heavy-bleed window begins. Bleed during the unmeasured ramp, where
180s ranges stay below 40 bps throughout, is expected to be small but was not
measured. The slower 60 bps trigger bleeds about $2,399 before firing in-window.

## Tests

Real swap sequences are included as fixtures:

- `test/fixtures/calm_0530.json`: 629 real Arbitrum WETH/USDC swaps plus
  Binance 1 s fair prices.
- `test/fixtures/vol_0523_hot90m.json`: 3,882 swaps from the 430 bps episode
  plus Pyth benchmark prices with per-swap sampling interval.
- `test/fixtures/calm_0530_truth.json` and
  `test/fixtures/vol_0523_truth.json`: per-swap research ground truth.
- `test/fixtures/sentinel_mainnet_calm.json` and
  `test/fixtures/sentinel_mainnet_vol.json`: mainnet event streams for RSC
  trigger calibration; the volatile file is the corrected 1,108-swap,
  418 bps window (SHA-256 pinned in `research/PARAMETERS.md`).

`test/EventDiff.t.sol` owns the precision-first regression baseline against the
truth fixtures. `test/SignalReplay.t.sol` still logs aggregate economics as a
diagnostic. `test/SentinelCalibration.t.sol` calibrates the RSC trigger.
`test/PegGuardHook.t.sol` wires the v4 harness and covers oracle fallback gates,
monotone safety, breaker behavior, and stale-basis hygiene.
`test/RegimeControl.t.sol` covers the Reactive Network callback path from
`RegimeReceiver` into the hook.

## Quickstart

```bash
git clone <repo-url> pegguard
cd pegguard
forge build
forge test -vv --match-contract EventDiffTest
forge test -vv --match-contract SentinelCalibrationTest
forge test
```

Dependencies are vendored under `lib/` for a reproducible public release.
The exact upstream refs are recorded in [`docs/dependencies.md`](docs/dependencies.md).

## Shadow Forward Test

The live shadow daemon is a read-only forward-test harness. It does not trade,
send transactions, or calibrate constants from live data. At boot it first runs
the offline parity gate against the repo fixtures and refuses live mode unless
the Python pipeline reproduces the EventDiff baseline within +/-1pp:
92.42% calm precision / 22.98% calm truth-capture and 98.86% volatile precision /
25.56% volatile truth-capture.

Runtime dependencies are Python 3.11+, `aiohttp`, and `websockets`; the ledger
uses stdlib `sqlite3`. `pytest` is only needed for the parity test command.

```bash
python -m pip install aiohttp websockets pytest
pytest shadow/test_parity.py
python -m shadow.run --config shadow/config.toml
```

For a bounded smoke run:

```bash
python -m shadow.run --config shadow/config.toml --duration-sec 1800
```

The daemon records `shadow/shadow.sqlite3` locally with WAL enabled and emits
`docs/shadow/daily/YYYY-MM-DD.md` plus `docs/shadow/summary.md`. Reports present
truth-denominated capture and premium-weighted precision; raw capture is not a
calibration target. The fixed caveat is included in every report: same-swaps
upper bound; route-away elasticity is not observable in shadow mode.

Capital sizing and LP-return assumptions are modeled in
[`docs/capital_model.md`](docs/capital_model.md), built from the calibrated
calm and volatile backtest windows. Regenerate it with
`python -m shadow.capital_model`.

## Known limitations

All capture figures are same-swaps upper bounds; route-away elasticity is not
modeled. The volatile pricing calibration uses a single episode, and RSC
false-positive coverage is limited to the supplied 250-event calm sentinel
fixture. Guard mode is currently single-feed; stable pairs need a dual-feed
ratio such as USDC/USD divided by USDT/USD.

Economics are calibrated from real on-chain backtests. The calm window is
net-positive for LPs at about +1.89 bps after markout (versus +0.97 bps for a
static-fee pool) at 92.4% premium-weighted precision, and the volatile window
holds 98.9% precision at 25.6% truth-capture (see
[`docs/base_fee_report.md`](docs/base_fee_report.md) and
[`docs/alpha_sweep.json`](docs/alpha_sweep.json)). Net LP economics are tier- and
pair-dependent; the analysis identifies the base-fee tier, not the premium, as
the binding lever.
