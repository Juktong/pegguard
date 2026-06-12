// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AbstractReactive} from "reactive-lib/abstract-base/AbstractReactive.sol";
import {IReactive} from "reactive-lib/interfaces/IReactive.sol";
import {SentinelWindow} from "../lib/SentinelWindow.sol";

/// @title VolSentinelRSC - cross-chain volatility sentinel (Reactive Network)
/// @notice WHY RN, WHY HERE (measured, see research/PARAMETERS.md):
///   Price discovery among AMMs happens on the mainnet canonical pool
///   (lead-lag matrix), which the hook's chain cannot observe. This RSC
///   watches mainnet Swap events and flips the hook's regime cross-chain.
///   Latency budget is MINUTES (a 60s-late flip costs ~0.4% of episode
///   bleed) - RN's delivery latency is immaterial at this layer.
///   RN is deliberately EXCLUDED from pricing: the hot path needs <=2-5s
///   (precision collapses to 72-87% beyond that in volatility).
contract VolSentinelRSC is AbstractReactive {
    using SentinelWindow for SentinelWindow.Obs[64];

    // --- subscription target: mainnet WETH/USDC 0.05% (canonical price discovery)
    uint256 constant ORIGIN_CHAIN = 1;
    address constant ORIGIN_POOL  = 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640;
    uint256 constant SWAP_TOPIC0  = 0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67;

    // --- trigger calibration (data-derived, PARAMETERS.md):
    // Sentinel replay selected 40bps / 3min: zero calm false positives, $0
    // bled before trigger, and fewer volatile callbacks than lower thresholds.
    uint256 constant TRIG_BPS    = 40;
    uint256 constant WINDOW_SEC  = 180;
    uint64  constant REGIME_TTL  = 30 minutes;

    uint256 constant DEST_CHAIN  = 42161;           // hook chain (Arbitrum)
    address immutable receiverOnDest;                // RegimeReceiver
    uint64  constant CALLBACK_GAS = 250_000;

    SentinelWindow.Obs[64] ring;
    uint8 head;
    uint64 lastFlip;

    constructor(address _receiver) {
        receiverOnDest = _receiver;
        service.subscribe(ORIGIN_CHAIN, ORIGIN_POOL, SWAP_TOPIC0, 0, 0, 0);
    }

    /// @dev RN invokes react() with each matching log.
    function react(IReactive.LogRecord calldata log) external vmOnly {
        require(log.chain_id == ORIGIN_CHAIN, "VolSentinelRSC: wrong chain");
        require(log._contract == ORIGIN_POOL, "VolSentinelRSC: wrong pool");
        require(log.topic_0 == SWAP_TOPIC0, "VolSentinelRSC: wrong topic");
        require(log.data.length >= 96, "VolSentinelRSC: short data");

        // v3 Swap data: amount0|amount1|sqrtPriceX96|liquidity|tick (32B each)
        uint256 sqrtP = uint256(bytes32(log.data[64:96]));
        uint192 pxq = SentinelWindow.priceX96SqFromSqrt(sqrtP); // monotone in price; ratios only
        head = ring.write(head, uint64(block.timestamp), pxq);

        (uint192 lo, uint192 hi) = ring.rangeInWindow(uint64(block.timestamp), WINDOW_SEC);
        uint256 moveBps = SentinelWindow.moveBps(lo, hi);
        if (moveBps > TRIG_BPS && block.timestamp > lastFlip + 5 minutes) {
            lastFlip = uint64(block.timestamp);
            emit Callback(DEST_CHAIN, receiverOnDest, CALLBACK_GAS,
                abi.encodeWithSignature("onSignal(address,uint8,uint64)",
                    address(0), uint8(1) /*VOLATILE*/, uint64(block.timestamp) + REGIME_TTL));
        }
    }
}
