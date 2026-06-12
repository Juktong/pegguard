// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Control-plane -> hook boundary. Implemented by PegGuardHook,
///         called by RegimeReceiver (Reactive Network callback adapter).
///
/// Latency-budget split (measured, see PARAMETERS.md):
///   - hot path (beforeSwap pricing): <=2-5s budget -> Pyth pull ONLY.
///   - control plane (regime flips, breaker arm/disarm, basis upkeep):
///     minutes-scale budget -> Reactive Network RSC callbacks.
///   A 60s-late VOLATILE flip costs ~$63 of $15K window bleed (~0.4%):
///   minute-scale latency is immaterial at this layer - that is why RN
///   belongs here and not in pricing.
interface IRegimeSignal {
    enum Regime { CALM, VOLATILE }

    /// @notice Flip global regime. MONOTONE SAFETY:
    ///   - tightening (-> VOLATILE) applies immediately;
    ///   - loosening (-> CALM) only applies if current regime expired or
    ///     cooldown elapsed (a forged/buggy callback can only make the hook
    ///     MORE conservative, never less).
    /// @param expiry unix time after which regime auto-reverts to the
    ///        conservative default (RN outage => graceful degradation).
    function onRegimeSignal(Regime regime, uint64 expiry) external;

    /// @notice Arm/disarm the depeg breaker for a guard-mode pool.
    ///         Arm is immediate; disarm requires sustained in-band time
    ///         enforced by the control plane (hysteresis lives off-chain-ish,
    ///         the hook only accepts disarm after minDisarmDelay).
    function onBreakerSignal(bytes32 poolId, bool armed) external;
}
