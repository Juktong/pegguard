# Demo Script

[HUMAN RECORDS VOICE]

Target length: 4.5 minutes.

## 1. Problem: LVR Is Priceable IL

Shot: README title, then `research/PARAMETERS.md` calibration windows.

Narration:

PegGuard is a Uniswap v4 dynamic-fee hook for measured IL insurance. The
problem is LVR: the priceable part of impermanent loss that appears when pool
prices lag the market. In our volatile 2026-05-23 WETH/USDC episode, ETH moved
about 430 bps over four hours. LP bleed reached roughly $3.8k per hour in the
hot window, about 22 times the calm-window rate.

The hook's job is not to tax every deviation. It charges only correcting flow,
and only when the signal is strong enough to be useful.

## 2. Why Naive Deviation Hooks Fail

Shot: `docs/event_diff.md` root-cause and baseline table.

Narration:

A naive deviation hook fails in two measured ways.

First, basis taxation. In the research data, 62% of the raw pool-versus-fair
spread was slow venue and quote basis. If we tax that slow basis as if it were
LVR, apparent capture inflates from the real 17% result to 224%. PegGuard uses a
trailing basis EMA so only the fast fair-versus-pool deviation is charged.

Second, the staleness trap. In volatility, stale signals can raise measured raw
revenue from 25% to 41% while precision collapses from 95% to 72%. Raw capture
alone rewards bad behavior. Our regression baseline is event-level
premium-weighted precision plus truth-denominated capture.

This correction round also fixed a harness artifact: fixture `stale_s` is
historical benchmark sampling interval, not live Pyth pull staleness. Removing
that mistaken gate restored volatile truth-capture to 25.56% at 98.86%
precision.

## 3. Architecture: Pyth Hot Path, Reactive Control Plane

Shot: `README.md` architecture block, then `src/PegGuardHook.sol` and
`src/reactive/VolSentinelRSC.sol`.

Narration:

The architecture splits by measured latency budget.

The hot path is `beforeSwap` and `afterSwap`. It uses Pyth pull prices, strict
staleness guards, confidence anomaly fallback, basis de-trending, and dynamic
fee overrides. If the oracle is stale, anomalous, or the basis is unseeded, the
hook falls back to the symmetric base fee and never becomes worse than a static
fee pool.

Reactive Network is deliberately not used for swap pricing. It is the control
plane. `VolSentinelRSC` watches the mainnet canonical WETH/USDC pool and calls
`RegimeReceiver`, which flips the hook into volatile mode. The selected
40 bps / 180 second sentinel has zero calm false positives. It arms volatile
mode 74 minutes before the measured heavy-bleed window begins. Bleed during the
unmeasured ramp is expected to be small, but it was not measured; the slower
60 bps trigger bleeds about $2,399 before firing in-window.

## 4. Live: Tests On Real Fixtures

Shot: terminal.

Command:

```bash
forge test -vv --match-contract EventDiffTest
```

Narration:

These are real swap fixtures, not synthetic examples. EventDiff joins each swap
to research ground truth by index and timestamp. The corrected baseline is:
calm precision 92.42%, calm truth-capture 22.98%; volatile precision 98.86%,
volatile truth-capture 25.56%. The test also enforces permanent floors: both
precisions must stay above 90%, calm capture above 8%, and volatile capture
above 15%.

Shot: terminal.

Command:

```bash
forge test -vv
```

Narration:

The full suite runs the event-diff economics, aggregate replay diagnostics,
v4 hook invariants, monotone safety tests, Reactive callback tests, and sentinel
calibration.

## 5. Honest Limits

Shot: README known limitations.

Narration:

The capture numbers are same-swaps upper bounds. Route-away elasticity is not
modeled. The volatile pricing calibration uses one real episode, and RSC
false-positive coverage is limited to the supplied calm sentinel fixture. Guard
mode is currently single-feed; production stable-pair deployment should use a
dual-feed ratio.

PegGuard's core claim is narrow: with fresh Pyth pricing on the hot path and
Reactive Network on the control plane, the hook can charge measured IL-causing
flow without turning ordinary basis, stale signals, or forged callbacks into
unsafe behavior.
