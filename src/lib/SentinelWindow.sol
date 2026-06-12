// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title SentinelWindow - range trigger math for Reactive Network volatility sentinel
/// @notice Kept separate from the RSC so tests can calibrate TRIG_BPS/WINDOW
///         against immutable event fixtures without deploying RN plumbing.
library SentinelWindow {
    uint8 internal constant RING_SIZE = 64;

    struct Obs {
        uint64 ts;
        uint192 priceX96sq;
    }

    function priceX96SqFromSqrt(uint256 sqrtPriceX96) internal pure returns (uint192) {
        return uint192((sqrtPriceX96 * sqrtPriceX96) >> 96);
    }

    function write(Obs[RING_SIZE] storage ring, uint8 head, uint64 ts, uint192 priceX96sq)
        internal returns (uint8)
    {
        ring[head] = Obs({ts: ts, priceX96sq: priceX96sq});
        return uint8((head + 1) % RING_SIZE);
    }

    function rangeInWindow(Obs[RING_SIZE] storage ring, uint64 nowTs, uint256 windowSec)
        internal view returns (uint192 lo, uint192 hi)
    {
        uint64 cutoff = _cutoff(nowTs, windowSec);
        for (uint256 i = 0; i < RING_SIZE; i++) {
            Obs memory o = ring[i];
            if (o.ts < cutoff || o.priceX96sq == 0) continue;
            if (lo == 0 || o.priceX96sq < lo) lo = o.priceX96sq;
            if (o.priceX96sq > hi) hi = o.priceX96sq;
        }
    }

    function rangeInWindowMemory(Obs[RING_SIZE] memory ring, uint64 nowTs, uint256 windowSec)
        internal pure returns (uint192 lo, uint192 hi)
    {
        uint64 cutoff = _cutoff(nowTs, windowSec);
        for (uint256 i = 0; i < RING_SIZE; i++) {
            Obs memory o = ring[i];
            if (o.ts < cutoff || o.priceX96sq == 0) continue;
            if (lo == 0 || o.priceX96sq < lo) lo = o.priceX96sq;
            if (o.priceX96sq > hi) hi = o.priceX96sq;
        }
    }

    function moveBps(uint192 lo, uint192 hi) internal pure returns (uint256) {
        if (lo == 0) return 0;
        return (uint256(hi - lo) * 1e4) / lo;
    }

    function _cutoff(uint64 nowTs, uint256 windowSec) private pure returns (uint64) {
        if (windowSec >= nowTs) return 0;
        return nowTs - uint64(windowSec);
    }
}
