// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {SignalMath} from "../src/lib/SignalMath.sol";

/// @title EventDiff - per-event research truth agreement harness
/// @notice Truth fixtures are immutable real research output. This harness
///         verifies index/time alignment and reports precision-first metrics.
contract EventDiffTest is Test {
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

    struct TruthRow {
        uint256 t_ms;
        uint256 truth_corr;
        int256 truth_dev_e2;
        int256 truth_mk_e6;
        bool valid;
    }

    struct Acc {
        uint256 basis;
        uint256 lastObsT;
        uint256 prevMid;
    }

    struct EventResult {
        int256 devE2;
        int256 markoutE6;
        uint256 extraE6;
        bool charged;
        bool freshAndPriced;
    }

    struct ReplayParams {
        uint256 tauSec;
        uint256 deadbandE2;
    }

    struct Metrics {
        uint256 rows;
        uint256 validRows;
        uint256 pricedRows;
        uint256 chargedRows;
        uint256 chargedAgreeRows;
        uint256 premiumTotalE6;
        uint256 premiumCorrectE6;
        uint256 extraE6;
        int256 trailingMarkoutE6;
        int256 truthMarkoutE6;
        uint256 devMaeE2;
        uint256 devMedianErrE2;
        uint256 devP90ErrE2;
    }

    uint256 constant ALPHA_NUM = 1;
    uint256 constant ALPHA_DEN = 2;
    uint256 constant CAP_PIPS = 5000;
    uint256 constant SAMPLE_FRESH_SEC = 15;
    uint256 constant DEFAULT_TAU_SEC = 450;
    uint256 constant DEFAULT_DEADBAND_E2 = 50;
    uint256 constant PRECISION_FLOOR_BPS = 9_000;
    uint256 constant CALM_CAPTURE_FLOOR_BPS = 800;
    uint256 constant VOL_CAPTURE_FLOOR_BPS = 1_500;
    uint256 constant CALM_PRECISION_MIN_BPS = 8_742; // measured 9_242 - 5pp
    uint256 constant CALM_CAPTURE_TRUTH_BPS = 2_298;
    uint256 constant CALM_DEV_MAE_MAX_E2 = 237; // measured 158 * 1.5
    uint256 constant VOL_PRECISION_MIN_BPS = 9_386; // measured 9_886 - 5pp
    uint256 constant VOL_CAPTURE_TRUTH_BPS = 2_556;
    uint256 constant VOL_DEV_MAE_MAX_E2 = 336; // measured 224 * 1.5

    string constant CALM_PATH = "test/fixtures/calm_0530.json";
    string constant CALM_TRUTH_PATH = "test/fixtures/calm_0530_truth.json";
    string constant VOL_PATH = "test/fixtures/vol_0523_hot90m.json";
    string constant VOL_TRUTH_PATH = "test/fixtures/vol_0523_truth.json";

    function test_eventDiff_baselineAssertions() public {
        if (!_hasTruthFixtures()) {
            vm.skip(true, "truth fixtures missing");
            return;
        }

        Metrics memory calm = _replayCalm(DEFAULT_TAU_SEC, DEFAULT_DEADBAND_E2, true);
        Metrics memory vol = _replayVol(DEFAULT_TAU_SEC, DEFAULT_DEADBAND_E2, true);

        _logMetrics("calm", calm);
        _logMetrics("vol", vol);
        _logSweepRow("vol sampling <=15s", _replayVolSamplingFresh(DEFAULT_TAU_SEC, DEFAULT_DEADBAND_E2, SAMPLE_FRESH_SEC));
        _assertBaseline(
            "calm", calm, CALM_PRECISION_MIN_BPS, CALM_CAPTURE_TRUTH_BPS, CALM_DEV_MAE_MAX_E2,
            CALM_CAPTURE_FLOOR_BPS
        );
        _assertBaseline(
            "vol", vol, VOL_PRECISION_MIN_BPS, VOL_CAPTURE_TRUTH_BPS, VOL_DEV_MAE_MAX_E2,
            VOL_CAPTURE_FLOOR_BPS
        );
    }

    function test_tauSweep_150() public {
        if (!_hasTruthFixtures()) {
            vm.skip(true, "truth fixtures missing");
            return;
        }

        _logTau(150);
    }

    function test_tauSweep_300() public {
        if (!_hasTruthFixtures()) {
            vm.skip(true, "truth fixtures missing");
            return;
        }

        _logTau(300);
    }

    function test_tauSweep_450() public {
        if (!_hasTruthFixtures()) {
            vm.skip(true, "truth fixtures missing");
            return;
        }

        _logTau(450);
    }

    function test_tauSweep_600() public {
        if (!_hasTruthFixtures()) {
            vm.skip(true, "truth fixtures missing");
            return;
        }

        _logTau(600);
    }

    function test_tauSweep_900() public {
        if (!_hasTruthFixtures()) {
            vm.skip(true, "truth fixtures missing");
            return;
        }

        _logTau(900);
    }

    function test_deadbandTruthTable_0() public { _logDeadbandIfReady(0); }
    function test_deadbandTruthTable_25() public { _logDeadbandIfReady(25); }
    function test_deadbandTruthTable_50() public { _logDeadbandIfReady(50); }
    function test_deadbandTruthTable_75() public { _logDeadbandIfReady(75); }
    function test_deadbandTruthTable_100() public { _logDeadbandIfReady(100); }
    function test_deadbandTruthTable_125() public { _logDeadbandIfReady(125); }
    function test_deadbandTruthTable_150() public { _logDeadbandIfReady(150); }
    function test_deadbandTruthTable_175() public { _logDeadbandIfReady(175); }
    function test_deadbandTruthTable_200() public { _logDeadbandIfReady(200); }

    function _logTau(uint256 tauSec) internal view {
        Metrics memory calm = _replayCalm(tauSec, DEFAULT_DEADBAND_E2, false);
        Metrics memory vol = _replayVol(tauSec, DEFAULT_DEADBAND_E2, false);
        console2.log("tau", tauSec);
        _logSweepRow("  calm", calm);
        _logSweepRow("  vol", vol);
    }

    function _logDeadbandIfReady(uint256 deadbandE2) internal {
        if (!_hasTruthFixtures()) {
            vm.skip(true, "truth fixtures missing");
            return;
        }

        console2.log("deadbandE2", deadbandE2);
        _logSweepRow("  calm", _replayCalm(DEFAULT_TAU_SEC, deadbandE2, false));
        _logSweepRow("  vol", _replayVol(DEFAULT_TAU_SEC, deadbandE2, false));
    }

    function _hasTruthFixtures() internal view returns (bool) {
        return vm.exists(CALM_TRUTH_PATH) && vm.exists(VOL_TRUTH_PATH);
    }

    function _replayCalm(uint256 tauSec, uint256 deadbandE2, bool includeQuantiles)
        internal view returns (Metrics memory m)
    {
        bytes memory rawRows = vm.parseJson(vm.readFile(CALM_PATH));
        bytes memory rawTruth = vm.parseJson(vm.readFile(CALM_TRUTH_PATH));
        CalmRow[] memory rows = abi.decode(rawRows, (CalmRow[]));
        TruthRow[] memory truth = abi.decode(rawTruth, (TruthRow[]));
        assertEq(rows.length, truth.length, "calm truth length mismatch");

        uint256[] memory errors = new uint256[](rows.length);
        uint256 errCount;
        Acc memory acc;
        ReplayParams memory params = ReplayParams({tauSec: tauSec, deadbandE2: deadbandE2});
        m.rows = rows.length;

        for (uint256 i = 0; i < rows.length; i++) {
            (acc, errCount) = _applyCalmRow(acc, m, errors, errCount, rows[i], truth[i], params);
        }
        _finishErrors(m, errors, errCount, includeQuantiles);
    }

    function _replayVol(uint256 tauSec, uint256 deadbandE2, bool includeQuantiles)
        internal view returns (Metrics memory m)
    {
        bytes memory rawRows = vm.parseJson(vm.readFile(VOL_PATH));
        bytes memory rawTruth = vm.parseJson(vm.readFile(VOL_TRUTH_PATH));
        VolRow[] memory rows = abi.decode(rawRows, (VolRow[]));
        TruthRow[] memory truth = abi.decode(rawTruth, (TruthRow[]));
        assertEq(rows.length, truth.length, "vol truth length mismatch");

        uint256[] memory errors = new uint256[](rows.length);
        uint256 errCount;
        Acc memory acc;
        ReplayParams memory params = ReplayParams({tauSec: tauSec, deadbandE2: deadbandE2});
        m.rows = rows.length;

        for (uint256 i = 0; i < rows.length; i++) {
            (acc, errCount) = _applyVolRow(acc, m, errors, errCount, rows[i], truth[i], params);
        }
        _finishErrors(m, errors, errCount, includeQuantiles);
    }

    function _replayVolSamplingFresh(uint256 tauSec, uint256 deadbandE2, uint256 maxSamplingSec)
        internal view returns (Metrics memory m)
    {
        bytes memory rawRows = vm.parseJson(vm.readFile(VOL_PATH));
        bytes memory rawTruth = vm.parseJson(vm.readFile(VOL_TRUTH_PATH));
        VolRow[] memory rows = abi.decode(rawRows, (VolRow[]));
        TruthRow[] memory truth = abi.decode(rawTruth, (TruthRow[]));
        assertEq(rows.length, truth.length, "vol truth length mismatch");

        Acc memory acc;
        ReplayParams memory params = ReplayParams({tauSec: tauSec, deadbandE2: deadbandE2});
        m.rows = rows.length;

        for (uint256 i = 0; i < rows.length; i++) {
            require(rows[i].t_ms == truth[i].t_ms, "vol truth t_ms mismatch");
            EventResult memory ev = _eventResult(acc, rows[i].ab_e18, rows[i].aq_e6, rows[i].fair_e18, params.deadbandE2);
            if (truth[i].valid && rows[i].stale_s <= maxSamplingSec) _recordMetricsNoQuantiles(m, ev, truth[i]);
            acc = _updateFresh(acc, rows[i].p_e18, rows[i].fair_e18, rows[i].t_ms, params.tauSec);
        }
        if (m.pricedRows != 0) m.devMaeE2 = m.devMaeE2 / m.pricedRows;
    }

    function _applyCalmRow(
        Acc memory acc,
        Metrics memory m,
        uint256[] memory errors,
        uint256 errCount,
        CalmRow memory row,
        TruthRow memory truth,
        ReplayParams memory params
    ) internal pure returns (Acc memory, uint256) {
        require(row.t_ms == truth.t_ms, "calm truth t_ms mismatch");
        EventResult memory ev = _eventResult(acc, row.ab_e18, row.aq_e6, row.fair_e18, params.deadbandE2);
        if (truth.valid) errCount = _recordMetrics(m, errors, errCount, ev, truth);
        return (_updateFresh(acc, row.p_e18, row.fair_e18, row.t_ms, params.tauSec), errCount);
    }

    function _applyVolRow(
        Acc memory acc,
        Metrics memory m,
        uint256[] memory errors,
        uint256 errCount,
        VolRow memory row,
        TruthRow memory truth,
        ReplayParams memory params
    ) internal pure returns (Acc memory, uint256) {
        require(row.t_ms == truth.t_ms, "vol truth t_ms mismatch");
        // `stale_s` is the research benchmark sampling interval in this fixture,
        // not on-chain Pyth pull freshness. Never gate charging or basis updates on it.
        EventResult memory ev = _eventResult(acc, row.ab_e18, row.aq_e6, row.fair_e18, params.deadbandE2);
        if (truth.valid) errCount = _recordMetrics(m, errors, errCount, ev, truth);
        return (_updateFresh(acc, row.p_e18, row.fair_e18, row.t_ms, params.tauSec), errCount);
    }

    function _eventResult(
        Acc memory acc,
        int256 abE18,
        int256 aqE6,
        uint256 fairE18,
        uint256 deadbandE2
    ) internal pure returns (EventResult memory ev) {
        if (acc.basis == 0) return ev;

        uint256 fairLocal;
        (ev.devE2, fairLocal) = SignalMath.deviationBps(acc.prevMid, fairE18, acc.basis);
        ev.markoutE6 = (abE18 * int256(fairLocal)) / 1e30 + aqE6;
        ev.freshAndPriced = true;

        bool zeroForOne = abE18 > 0;
        if (SignalMath.isCorrecting(ev.devE2, zeroForOne)) {
            uint256 absE2 = uint256(ev.devE2 < 0 ? -ev.devE2 : ev.devE2);
            uint24 prem = SignalMath.premiumPips(absE2, deadbandE2, ALPHA_NUM, ALPHA_DEN, CAP_PIPS);
            uint256 aqAbs = uint256(aqE6 < 0 ? -aqE6 : aqE6);
            ev.extraE6 = (aqAbs * prem) / 1e6;
            ev.charged = prem > 0;
        }
    }

    function _updateFresh(Acc memory acc, uint256 postMidE18, uint256 fairE18, uint256 tMs, uint256 tauSec)
        internal pure returns (Acc memory)
    {
        uint256 obs = (postMidE18 * SignalMath.WAD) / fairE18;
        uint256 dt = acc.lastObsT == 0 ? 0 : (tMs - acc.lastObsT) / 1000;
        acc.basis = SignalMath.emaUpdate(acc.basis, obs, dt == 0 ? 1 : dt, tauSec);
        acc.lastObsT = tMs;
        acc.prevMid = postMidE18;
        return acc;
    }

    function _recordMetrics(
        Metrics memory m,
        uint256[] memory errors,
        uint256 errCount,
        EventResult memory ev,
        TruthRow memory truth
    ) internal pure returns (uint256) {
        m.validRows++;
        m.truthMarkoutE6 += truth.truth_mk_e6;
        if (!ev.freshAndPriced) return errCount;

        m.pricedRows++;
        m.extraE6 += ev.extraE6;
        m.trailingMarkoutE6 += ev.markoutE6;

        uint256 err = _absDiff(ev.devE2, truth.truth_dev_e2);
        errors[errCount++] = err;
        m.devMaeE2 += err;

        if (ev.charged) {
            m.chargedRows++;
            m.premiumTotalE6 += ev.extraE6;
            if (truth.truth_corr == 1) {
                m.chargedAgreeRows++;
                m.premiumCorrectE6 += ev.extraE6;
            }
        }
        return errCount;
    }

    function _recordMetricsNoQuantiles(Metrics memory m, EventResult memory ev, TruthRow memory truth)
        internal pure
    {
        m.validRows++;
        m.truthMarkoutE6 += truth.truth_mk_e6;
        if (!ev.freshAndPriced) return;

        m.pricedRows++;
        m.extraE6 += ev.extraE6;
        m.trailingMarkoutE6 += ev.markoutE6;
        m.devMaeE2 += _absDiff(ev.devE2, truth.truth_dev_e2);

        if (ev.charged) {
            m.chargedRows++;
            m.premiumTotalE6 += ev.extraE6;
            if (truth.truth_corr == 1) {
                m.chargedAgreeRows++;
                m.premiumCorrectE6 += ev.extraE6;
            }
        }
    }

    function _finishErrors(Metrics memory m, uint256[] memory errors, uint256 errCount, bool includeQuantiles)
        internal pure
    {
        if (errCount == 0) return;
        m.devMaeE2 = m.devMaeE2 / errCount;
        if (!includeQuantiles) return;
        _sort(errors, 0, int256(errCount - 1));
        m.devMedianErrE2 = errors[errCount / 2];
        m.devP90ErrE2 = errors[(errCount * 90) / 100];
    }

    function _logMetrics(string memory label, Metrics memory m) internal pure {
        console2.log(label);
        console2.log("  rows", m.rows);
        console2.log("  valid rows", m.validRows);
        console2.log("  priced rows", m.pricedRows);
        console2.log("  charged rows", m.chargedRows);
        console2.log("  precision bps", _ratioBps(m.premiumCorrectE6, m.premiumTotalE6));
        console2.log("  sign agreement bps", _ratioBps(m.chargedAgreeRows, m.chargedRows));
        console2.log("  dev median err e2", m.devMedianErrE2);
        console2.log("  dev p90 err e2", m.devP90ErrE2);
        console2.log("  dev mae e2", m.devMaeE2);
        console2.log("  capture truth bps", _ratioBps(m.extraE6, _abs(m.truthMarkoutE6)));
        console2.log("  trailing extra e6", m.extraE6);
        console2.log("  trailing markout e6", m.trailingMarkoutE6);
        console2.log("  truth extra e6", m.extraE6);
        console2.log("  truth markout e6", m.truthMarkoutE6);
    }

    function _logSweepRow(string memory label, Metrics memory m) internal pure {
        console2.log(label);
        console2.log("    precision bps", _ratioBps(m.premiumCorrectE6, m.premiumTotalE6));
        console2.log("    capture truth bps", _ratioBps(m.extraE6, _abs(m.truthMarkoutE6)));
        console2.log("    dev mae e2", m.devMaeE2);
    }

    function _assertBaseline(
        string memory label,
        Metrics memory m,
        uint256 precisionMinBps,
        uint256 captureTruthBps,
        uint256 devMaeMaxE2,
        uint256 captureFloorBps
    ) internal pure {
        uint256 precisionBps = _ratioBps(m.premiumCorrectE6, m.premiumTotalE6);
        uint256 captureBps = _ratioBps(m.extraE6, _abs(m.truthMarkoutE6));

        assertGe(precisionBps, precisionMinBps, string.concat(label, " precision below baseline"));
        assertGe(precisionBps, PRECISION_FLOOR_BPS, string.concat(label, " precision below economic floor"));
        assertGe(captureBps, (captureTruthBps * 75) / 100, string.concat(label, " capture below baseline"));
        assertLe(captureBps, (captureTruthBps * 125) / 100, string.concat(label, " capture above baseline"));
        assertGe(captureBps, captureFloorBps, string.concat(label, " capture below economic floor"));
        assertLe(m.devMaeE2, devMaeMaxE2, string.concat(label, " dev MAE above baseline"));
    }

    function _sort(uint256[] memory values, int256 left, int256 right) internal pure {
        int256 i = left;
        int256 j = right;
        if (i == j) return;
        uint256 pivot = values[uint256(left + (right - left) / 2)];
        while (i <= j) {
            while (values[uint256(i)] < pivot) i++;
            while (values[uint256(j)] > pivot) j--;
            if (i <= j) {
                (values[uint256(i)], values[uint256(j)]) = (values[uint256(j)], values[uint256(i)]);
                i++;
                j--;
            }
        }
        if (left < j) _sort(values, left, j);
        if (i < right) _sort(values, i, right);
    }

    function _ratioBps(uint256 num, uint256 den) internal pure returns (uint256) {
        if (den == 0) return 0;
        return (num * 10_000) / den;
    }

    function _abs(int256 x) internal pure returns (uint256) {
        return uint256(x < 0 ? -x : x);
    }

    function _absDiff(int256 a, int256 b) internal pure returns (uint256) {
        return a >= b ? uint256(a - b) : uint256(b - a);
    }
}
