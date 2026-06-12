// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {SignalMath} from "../src/lib/SignalMath.sol";

/// @title SignalReplay - research-as-regression-tests
/// @notice Replays REAL on-chain swap sequences through the on-chain signal
///         pipeline (trailing basis EMA + directional premium). Aggregate
///         economics are diagnostic only; EventDiff.t.sol owns truth-denominated
///         precision/capture regression assertions.
///
/// Fixtures (real data, see research/PARAMETERS.md for provenance):
///   calm_0530.json      - Arbitrum WETH/USDC 0.05%, 2026-05-30 20:04-22:30 UTC,
///                         629 swaps, fair = Binance ETHUSDC 1s.
///                         Research (centered-median de-trend): capture ~17%.
///   vol_0523_hot90m.json - same pool, 2026-05-23 episode (430bps/4h), hottest
///                         90min, 3,882 swaps, fair = Pyth benchmark sampling
///                         interval in `stale_s`.
///                         Research: capture ~24-26%, LP bleed x22 calm rate.
///
/// The on-chain pipeline is TRAILING (causal) while research de-trend was
/// centered, so aggregate capture alone is not a calibration objective.
contract SignalReplayTest is Test {
    struct CalmRow {
        int256 ab_e18;
        int256 aq_e6;
        uint256 fair_e18;
        uint256 p_e18;
        uint256 t_ms;
    }

    struct VolRow {
        int256 ab_e18;
        int256 aq_e6;
        uint256 fair_e18;
        uint256 p_e18;
        uint256 stale_s;
        uint256 t_ms;
    }

    struct ReplayAcc {
        int256 staticMk_e6;
        uint256 extra_e6;
        uint256 basis;
        uint256 lastT;
        uint256 prevMid;
    }
    // NOTE: foundry's parseJson maps struct fields ALPHABETICALLY - rows are
    // declared in alphabetical field order to match their fixture keys.

    uint256 constant ALPHA_NUM = 1;
    uint256 constant ALPHA_DEN = 2;
    uint256 constant CAP_PIPS  = 5000;  // 50bps
    uint256 constant TAU_SEC   = 450;   // trailing equivalent of centered +/-300s median; see PARAMETERS.md
    uint256 constant DEFAULT_DEADBAND_E2 = 50;  // hook default; calibrated in EventDiff truth harness

    function _rowDeltas(
        int256 ab_e18,
        int256 aq_e6,
        uint256 fair_e18,
        uint256 prevMid,
        uint256 basis,
        uint256 deadbandE2
    ) internal pure returns (int256 markout_e6, uint256 extra_e6) {
        (int256 devE2, uint256 fLocal) = SignalMath.deviationBps(prevMid, fair_e18, basis);
        markout_e6 = (ab_e18 * int256(fLocal)) / 1e30 + aq_e6;

        bool zf1 = ab_e18 > 0;
        if (SignalMath.isCorrecting(devE2, zf1)) {
            uint256 absE2 = uint256(devE2 < 0 ? -devE2 : devE2);
            uint24 prem = SignalMath.premiumPips(absE2, deadbandE2, ALPHA_NUM, ALPHA_DEN, CAP_PIPS);
            uint256 aqAbs = uint256(aq_e6 < 0 ? -aq_e6 : aq_e6);
            extra_e6 = (aqAbs * prem) / 1e6;
        }
    }

    function _applyCalmRow(ReplayAcc memory acc, CalmRow memory r, uint256 deadbandE2)
        internal
        pure
        returns (ReplayAcc memory)
    {
        if (acc.basis != 0) {
            (int256 markout, uint256 extra) =
                _rowDeltas(r.ab_e18, r.aq_e6, r.fair_e18, acc.prevMid, acc.basis, deadbandE2);
            acc.staticMk_e6 += markout;
            acc.extra_e6 += extra;
        }
        uint256 obs = (r.p_e18 * SignalMath.WAD) / r.fair_e18;
        uint256 dt = acc.lastT == 0 ? 0 : (r.t_ms - acc.lastT) / 1000;
        acc.basis = SignalMath.emaUpdate(acc.basis, obs, dt == 0 ? 1 : dt, TAU_SEC);
        acc.lastT = r.t_ms;
        acc.prevMid = r.p_e18;
        return acc;
    }

    function _applyVolRow(ReplayAcc memory acc, VolRow memory r, uint256 deadbandE2)
        internal
        pure
        returns (ReplayAcc memory)
    {
        // `stale_s` is research benchmark sampling granularity, not on-chain
        // Pyth pull freshness. Do not gate replay charging or basis on it.
        if (acc.basis != 0) {
            (int256 markout, uint256 extra) =
                _rowDeltas(r.ab_e18, r.aq_e6, r.fair_e18, acc.prevMid, acc.basis, deadbandE2);
            acc.staticMk_e6 += markout;
            acc.extra_e6 += extra;
        }
        uint256 obs = (r.p_e18 * SignalMath.WAD) / r.fair_e18;
        uint256 dt = acc.lastT == 0 ? 0 : (r.t_ms - acc.lastT) / 1000;
        acc.basis = SignalMath.emaUpdate(acc.basis, obs, dt == 0 ? 1 : dt, TAU_SEC);
        acc.lastT = r.t_ms;
        acc.prevMid = r.p_e18;
        return acc;
    }

    function _replayCalm(string memory path, uint256 deadbandE2)
        internal view returns (int256 staticMk_e6, uint256 extra_e6, uint256 n)
    {
        bytes memory raw = vm.parseJson(vm.readFile(path));
        CalmRow[] memory rows = abi.decode(raw, (CalmRow[]));
        n = rows.length;

        ReplayAcc memory acc;
        for (uint256 i = 0; i < n; i++) {
            acc = _applyCalmRow(acc, rows[i], deadbandE2);
        }
        return (acc.staticMk_e6, acc.extra_e6, n);
    }

    function _replayVol(string memory path, uint256 deadbandE2)
        internal view returns (int256 staticMk_e6, uint256 extra_e6, uint256 n)
    {
        bytes memory raw = vm.parseJson(vm.readFile(path));
        VolRow[] memory rows = abi.decode(raw, (VolRow[]));
        n = rows.length;

        ReplayAcc memory acc;
        for (uint256 i = 0; i < n; i++) {
            acc = _applyVolRow(acc, rows[i], deadbandE2);
        }
        return (acc.staticMk_e6, acc.extra_e6, n);
    }

    function test_calmWindow_logsAggregateCapture() public view {
        (int256 mk, uint256 ex, uint256 n) = _replayCalm("test/fixtures/calm_0530.json", DEFAULT_DEADBAND_E2);
        uint256 capPct = (ex * 100) / uint256(mk < 0 ? -mk : mk);
        console2.log("calm: swaps", n);
        console2.log("calm: static markout (USDC e6)", mk);
        console2.log("calm: extra premium (USDC e6)", ex);
        console2.log("calm: capture pct", capPct);
        // Diagnostic only. EventDiff.t.sol asserts the precision-first baseline.
    }

    function test_volWindow_capture_and_claim_scale() public view {
        (int256 mkC,, ) = _replayCalm("test/fixtures/calm_0530.json", DEFAULT_DEADBAND_E2);
        (int256 mkV, uint256 exV, uint256 nV) = _replayVol("test/fixtures/vol_0523_hot90m.json", DEFAULT_DEADBAND_E2);
        uint256 capPct = (exV * 100) / uint256(mkV < 0 ? -mkV : mkV);
        console2.log("vol: swaps", nV);
        console2.log("vol: static markout (USDC e6)", mkV);
        console2.log("vol: capture pct", capPct);
        // Diagnostic only. EventDiff.t.sol asserts the precision-first baseline.
        // IL claim rate must be an order of magnitude above calm (research: x22/h)
        uint256 calmPerH = uint256(mkC < 0 ? -mkC : mkC) * 10 / 24; // 2.4h window
        uint256 volPerH  = uint256(mkV < 0 ? -mkV : mkV) * 10 / 15; // 1.5h window
        assertGt(volPerH, calmPerH * 5, "vol IL claim rate should dwarf calm");
    }

    function test_deadband_tradeoff_table() public view {
        // emits the deadband calibration table (open research item):
        // capture vs deadband - pick the knee that sheds benign noise flow.
        for (uint256 db = 0; db <= 300; db += 100) { // 0, 1, 2, 3 bps
            (int256 mk, uint256 ex,) = _replayVol("test/fixtures/vol_0523_hot90m.json", db);
            console2.log("deadband (bps*100):", db);
            console2.log("  capture pct:", (ex * 100) / uint256(mk < 0 ? -mk : mk));
        }
    }
}
