# PegGuard — local agent brief

## What this is
Uniswap v4 dynamic-fee hook "PegGuard — Measured IL Insurance", a UHI9 Hookathon
submission. Deadline: **June 11 23:59 PT** (Progress Update 2: June 8). The repo
is a research-derived skeleton: every constant was calibrated from real on-chain
backtests. `research/PARAMETERS.md` maps each constant to the experiment that
produced it — read it first, treat it as the spec.

Two modes per pool: HARVEST (volatile pairs: correcting-direction "toxic" flow
pays premium = base + α·clamp(|Δ|)) and GUARD (stable pairs: NO directional fee
— measured to have zero fuel — only a depeg circuit breaker).

## Non-negotiable invariants (do not "fix" these)
1. **Hot path = Pyth pull only.** Reactive Network lives ONLY in the control
   plane (regime flips / breaker arm). Measured: pricing precision collapses
   beyond 2–5s oracle staleness; RN latency is minutes-class. Never move RN
   into beforeSwap pricing.
2. **beforeSwap/afterSwap never revert.** Every oracle failure (stale, conf
   spike, unseeded basis) must degrade to the symmetric `baseFeePips`. The hook
   must never be worse than a static-fee pool.
3. **Monotone safety.** Regime/breaker tightening applies instantly; loosening
   only via cooldown/expiry/hysteresis. A forged callback may only make the
   hook MORE conservative.
4. **Basis hygiene.** Never update the basis EMA from a stale oracle reading.
5. **Data-derived constants** (α=1/2, cap=5000 pips, staleness 5s/2s,
   conf anomaly 3×EMA, trip 50bps, tau 450s) must not change without a comment
   citing PARAMETERS.md. Open calibration items you MAY set: deadband values,
   RSC TRIG_BPS — harnesses exist for both.
6. Fee units are pips (1e-6); bps×100 == pips (conversion already in
   SignalMath). Pools must be initialized with LPFeeLibrary.DYNAMIC_FEE_FLAG;
   fee overrides must OR in OVERRIDE_FEE_FLAG.
7. Fixtures in `test/fixtures/` are REAL on-chain sequences — never regenerate,
   edit, or synthesize them. `Row` struct fields stay alphabetical
   (foundry parseJson decodes alphabetically).

## Work order
1. **Build green.** `forge install foundry-rs/forge-std uniswap/v4-core
   uniswap/v4-periphery`. Pin versions; fix import paths in PegGuardHook.sol —
   known drift points: BaseHook (`src/utils/BaseHook.sol` vs `src/base/hooks/`),
   `SwapParams` (`types/PoolOperation.sol` vs `IPoolManager.SwapParams`),
   BaseHook internal hook signatures (`_beforeSwap` override pattern).
2. **Replay baseline.** `forge test --match-contract SignalReplay -vv` (no v4
   harness needed; fs_permissions already set). Record calm/vol capture %,
   then tighten the assert bands to ±40% relative of observed and commit as
   the regression baseline. Expected ballpark: calm ~8–35% (research centered-
   median methodology gave 17%; trailing EMA shifts it), vol higher, vol IL
   bleed rate ≫ calm.
3. **Unit tests.** Wire the v4 test harness (v4-core `Deployers`, periphery
   `HookMiner`; flags = BEFORE_INITIALIZE | BEFORE_SWAP | AFTER_SWAP, must
   match getHookPermissions). Fill every TODO in `test/PegGuardHook.t.sol`.
   Priority: the three fallback-invariant tests, monotone regime tests
   (use vm.warp for cooldown/expiry; MockPyth staleness is timestamp-based),
   breaker trip/deepening-vs-repegging fee, basis-not-poisoned-when-stale.
4. **Deadband.** Run `test_deadband_tradeoff_table`, pick the knee (capture
   retained vs small-flow protection), set `deadbandCalmE2/VolE2` defaults,
   document the choice in PARAMETERS.md.
5. **RN wiring.** Replace the vendored-style bases in `src/reactive/` with
   `Reactive-Network/reactive-lib` AbstractReactive/AbstractCallback (verify
   react()/callback signatures against the pinned lib — skeleton signatures
   are approximations). Keep the `IRegimeSignal` boundary unchanged. Add
   `test/RegimeControl.t.sol` simulating receiver→hook callbacks end-to-end.
   Reactive testnet deploy of the RSC is a stretch goal for the demo video.
6. **Deploy script.** Complete `script/Deploy.s.sol` (HookMiner + CREATE2,
   per-chain addresses as env vars). Testnet deploy is NOT required by rules;
   tests are.
7. **Gas.** `forge snapshot` on beforeSwap path; flag if hook overhead is
   egregious (>~150k incl. Pyth read), optimize storage layout only after
   tests are green.
8. **README truthfulness.** Hookathon binary rule: the partner-integration
   table may only list what is actually built and must point to real code
   locations. Update it if scope changes. No AI voices in the demo video;
   ≤5 min; repo must be public with tests passing.

## Verify before declaring anything done
`forge build` && `forge test -vv` all green; replay numbers logged in the PR
description; PARAMETERS.md updated for any calibration you performed.
