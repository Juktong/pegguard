# Event-Level Validation & Calibration Round

The aggregate-capture numbers hide implementation divergence; this round
replaces aggregate assertions with per-event ground-truth agreement. New fixtures
are in `test/fixtures/`: `calm_0530_truth.json` and `vol_0523_truth.json` hold
per-swap research ground truth (centered ±300s median methodology),
index-aligned to the existing fixtures (verify `t_ms` matches on join; abort if
any mismatch). Fields: `truth_dev_e2` (signed bps*100), `truth_corr` (0/1),
`truth_mk_e6`, `valid`. `sentinel_mainnet_calm.json` /
`sentinel_mainnet_vol.json` are mainnet swap-event streams for RSC trigger
calibration (vol one has ±tens-of-seconds timestamp error — acceptable for a
minutes-budget trigger; note it in docs).

## Objective Function

Read carefully: the target metric is PRECISION (premium-weighted share of
charged fees landing on `truth_corr==1` swaps) and truth-denominated capture
(`extra / |Σ truth_mk|`), NOT raw capture. Research showed staler/looser signals
RAISE raw capture while precision collapses — raw capture alone rewards bad
behavior. Never tune anything to maximize raw capture.

## P0 — Fix Deviation Quantization

`SignalMath.deviationBps` truncates to whole bps; calm median signal is 0.82bp,
and 85 charged-range signals (0.5–1bp) are currently zeroed. Return deviation at
e2 resolution (`dev_e2 = fairLocal*1e6/mid - 1e6`, signed int). Update all call
sites, premium math (`bps_e2 == pips` already), and unit tests.

## P1 — Per-Event Diff Harness

New test/EventDiff.t.sol: replay each fixture through `SignalMath` exactly as
the hook would (trailing EMA, post-swap basis update, pre-swap mid pricing),
join truth by index, and log per window:

(a) precision as defined above; (b) sign agreement rate on charged swaps; (c)
dev error stats: median/p90 of `|dev_solidity - truth_dev|` in bp*100; (d)
`capture_truthdenom = extra / |Σ truth_mk_e6|`; (e) decomposition of the current
39%-vs-23%-vs-17% calm split: report extra and markout separately under (i)
trailing-F valuation and (ii) `truth_mk` valuation, so the denominator artifact
is isolated and documented in `docs/event_diff.md`.

## P2 — Tau Sweep For Precision

Sweep `tauSec` in `{150,300,450,600,900}` on both windows; report precision,
`capture_truthdenom`, dev MAE per tau. Pick tau maximizing calm precision subject
to vol precision >= 90%; update the constant with a `PARAMETERS.md` provenance
note.

## P3 — Per-Regime Deadband Recalibration

This replaces the previous selection, which was calibrated on the volatile
window only and then applied to calm. Run the deadband table per window with
truth-denominated capture AND precision columns. Choose `deadbandCalmE2` from
the calm table (expect well below 100; calm medΔ is 82 e2) and `deadbandVolE2`
from the vol table. Align hook defaults and replay-test parameters — they
currently diverge (hook 1bp vs replay 0).

## P4 — Re-Baseline

Replace the ±40%-around-observed bands with assertions on: precision >=
`[measured-5pp]` per window, `capture_truthdenom` within ±25% relative of the
post-P0..P3 measurement, dev MAE <= `[measured*1.5]`. Document the new baseline
in `docs/replay_baseline.md` with the P1 table.

## P5 — RSC Trigger Event-To-Event Calibration

Feed sentinel fixtures through `VolSentinelRSC`'s window logic (extract the
range/window code into a pure lib if needed for testability): on
`sentinel_mainnet_calm` assert zero triggers (false-positive check, 250 events);
on `sentinel_mainnet_vol` report first trigger time vs window start, and price
trigger lateness using the vol truth bleed timeline (cumulative
`truth_mk_e6`): $ bled before trigger at `TRIG_BPS` in `{40,60,80}` x `WINDOW`
in `{180,300,600}`. Pick the pair minimizing bled-before-trigger subject to zero
calm false positives; update `VolSentinelRSC` constants with provenance. Add
`docs/sentinel_calibration.md`.

## Guardrails

All existing fixtures and the four new truth/sentinel fixtures are immutable real
data — never regenerate or edit. Hot-path constants (`MAX_STALENESS_*`, alpha,
cap, conf anomaly 3x) stay fixed; this round calibrates only tau, deadbands, and
RSC trigger params. While refactoring `_readOracle`, check whether `confEma` is
updated twice per swap (`beforeSwap` + `afterSwap` both reading the oracle) and
dedupe if so.

Verify: `forge build && forge test -vv` green; `docs/event_diff.md`,
`replay_baseline.md`, `sentinel_calibration.md` updated; `PARAMETERS.md` notes
every changed constant with its measurement.
