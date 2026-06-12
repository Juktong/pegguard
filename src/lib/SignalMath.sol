// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title SignalMath - pure signal pipeline for PegGuard
/// @notice On-chain mirror of the research backtest math. Every constant's
///         provenance is documented in research/PARAMETERS.md.
///
/// Pipeline (per swap):
///   1. basis EMA de-trends the slow venue/quote basis between pool mid and
///      oracle fair (research: 62% of raw pool-vs-CEX gap variance is slow
///      basis that MUST NOT be taxed - taxing it inflated fake capture
///      224% -> real 17%).
///   2. deviation = fairLocal vs pre-swap mid, in bps*100 (signed).
///   3. directional premium charged only on the correcting side, linear in
///      |dev| above deadband, clamped.
library SignalMath {
    uint256 internal constant WAD = 1e18;

    /// @notice Trailing EMA update with rational decay k = dt/(dt+tau).
    /// @dev Approximates 1-exp(-dt/tau); tau is calibrated by event-level
    ///      truth agreement in research/PARAMETERS.md.
    ///      Skip updates when the oracle is stale (do not poison the basis).
    function emaUpdate(uint256 basisWad, uint256 obsWad, uint256 dtSec, uint256 tauSec)
        internal pure returns (uint256)
    {
        if (basisWad == 0) return obsWad; // seed on first observation
        if (dtSec == 0) return basisWad;
        uint256 k = (dtSec * WAD) / (dtSec + tauSec);
        return basisWad + ((obsWad * k) / WAD) - ((basisWad * k) / WAD);
    }

    /// @notice Signed deviation of de-trended fair vs pre-swap pool mid, in bps*100.
    /// @param midWad   pre-swap pool mid, token1-per-token0, 1e18
    /// @param fairWad  raw oracle fair (any consistent unit; basis absorbs scale)
    /// @param basisWad pool-units-per-oracle-unit EMA (absorbs decimals + USD/USDC basis)
    function deviationBps(uint256 midWad, uint256 fairWad, uint256 basisWad)
        internal pure returns (int256 devE2, uint256 fairLocalWad)
    {
        fairLocalWad = (fairWad * basisWad) / WAD;
        devE2 = int256((fairLocalWad * 1e6) / midWad) - int256(1e6); // (F/mid - 1) * 1e6
    }

    /// @notice Is this swap in the correcting direction (toward fair)?
    /// @dev dev>0: fair above mid -> price must rise -> buying token0 (zeroForOne=false).
    function isCorrecting(int256 devE2, bool zeroForOne) internal pure returns (bool) {
        if (devE2 > 0) return !zeroForOne;
        if (devE2 < 0) return zeroForOne;
        return false;
    }

    /// @notice Directional premium in pips (1e-6), linear above deadband, clamped.
    /// @dev Research: alpha=0.5, cap=50bps. Backtest charged alpha*|dev| with no
    ///      deadband; deadband added to protect small benign flow (vol-window
    ///      corr% ~50% => noise-direction churn is real). Calibrate via replay.
    function premiumPips(
        uint256 absDevBps_e2,  // |dev| in hundredths of a bp (bps*100) for resolution
        uint256 deadbandBps_e2,
        uint256 alphaNum,      // alpha = alphaNum/alphaDen (0.5 => 1/2)
        uint256 alphaDen,
        uint256 capPips
    ) internal pure returns (uint24) {
        if (absDevBps_e2 <= deadbandBps_e2) return 0;
        // bps*100 -> pips: 1 bp = 100 pips, so bps_e2 == pips exactly.
        uint256 p = ((absDevBps_e2 - deadbandBps_e2) * alphaNum) / alphaDen;
        if (p > capPips) p = capPips;
        return uint24(p);
    }
}
