// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {SentinelWindow} from "../src/lib/SentinelWindow.sol";

/// @title SentinelCalibration - event-to-event RSC trigger calibration
/// @notice The volatile sentinel fixture has known timestamp error on the order
///         of tens of seconds, which is acceptable for this minutes-budget
///         trigger. Do not use this harness for hot-path pricing decisions.
contract SentinelCalibrationTest is Test {
    using SentinelWindow for SentinelWindow.Obs[64];

    struct SentinelRow {
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

    struct TriggerResult {
        uint256 triggerCount;
        uint256 firstTriggerMs;
        uint256 firstTriggerOffsetSec;
        uint256 bledBeforeTriggerE6;
    }

    string constant SENTINEL_CALM_PATH = "test/fixtures/sentinel_mainnet_calm.json";
    string constant SENTINEL_VOL_PATH = "test/fixtures/sentinel_mainnet_vol.json";
    string constant VOL_PATH = "test/fixtures/vol_0523_hot90m.json";
    string constant VOL_TRUTH_PATH = "test/fixtures/vol_0523_truth.json";

    function test_sentinelWindow_handlesStartupWindowLongerThanTimestamp() public pure {
        SentinelWindow.Obs[64] memory ring;
        ring[0] = SentinelWindow.Obs({ts: 10, priceX96sq: 100});
        ring[1] = SentinelWindow.Obs({ts: 90, priceX96sq: 110});

        (uint192 lo, uint192 hi) = SentinelWindow.rangeInWindowMemory(ring, 100, 300);

        assertEq(lo, 100);
        assertEq(hi, 110);
        assertEq(SentinelWindow.moveBps(lo, hi), 1000);
    }

    function test_sentinelCurrentParams_zeroCalmFalsePositive() public {
        if (!_hasSentinelFixtures()) {
            vm.skip(true, "sentinel/truth fixtures missing");
            return;
        }

        TriggerResult memory calm = _runSentinel(SENTINEL_CALM_PATH, 40, 180);
        assertEq(calm.triggerCount, 0, "current sentinel params false-positive on calm");
    }

    function test_sentinelTrigger_20_180() public { _logTriggerIfReady(20, 180); }
    function test_sentinelTrigger_20_300() public { _logTriggerIfReady(20, 300); }
    function test_sentinelTrigger_20_600() public { _logTriggerIfReady(20, 600); }
    function test_sentinelTrigger_30_180() public { _logTriggerIfReady(30, 180); }
    function test_sentinelTrigger_30_300() public { _logTriggerIfReady(30, 300); }
    function test_sentinelTrigger_30_600() public { _logTriggerIfReady(30, 600); }
    function test_sentinelTrigger_40_180() public { _logTriggerIfReady(40, 180); }
    function test_sentinelTrigger_40_300() public { _logTriggerIfReady(40, 300); }
    function test_sentinelTrigger_40_600() public { _logTriggerIfReady(40, 600); }
    function test_sentinelTrigger_60_180() public { _logTriggerIfReady(60, 180); }
    function test_sentinelTrigger_60_300() public { _logTriggerIfReady(60, 300); }
    function test_sentinelTrigger_60_600() public { _logTriggerIfReady(60, 600); }

    function _logTriggerIfReady(uint256 trigBps, uint256 windowSec) internal {
        if (!_hasSentinelFixtures()) {
            vm.skip(true, "sentinel/truth fixtures missing");
            return;
        }

        TriggerResult memory calm = _runSentinel(SENTINEL_CALM_PATH, trigBps, windowSec);
        TriggerResult memory vol = _runSentinel(SENTINEL_VOL_PATH, trigBps, windowSec);
        vol.bledBeforeTriggerE6 = _bledBefore(vol.firstTriggerMs);

        console2.log("TRIG_BPS", trigBps);
        console2.log("WINDOW_SEC", windowSec);
        console2.log("  calm triggers", calm.triggerCount);
        console2.log("  vol triggers", vol.triggerCount);
        console2.log("  first trigger offset sec", vol.firstTriggerOffsetSec);
        console2.log("  bled before trigger e6", vol.bledBeforeTriggerE6);
        console2.log("  bled before trigger USD", vol.bledBeforeTriggerE6 / 1e6);
    }

    function _hasSentinelFixtures() internal view returns (bool) {
        return vm.exists(SENTINEL_CALM_PATH) && vm.exists(SENTINEL_VOL_PATH) && vm.exists(VOL_TRUTH_PATH);
    }

    function _runSentinel(string memory path, uint256 trigBps, uint256 windowSec)
        internal view returns (TriggerResult memory result)
    {
        bytes memory raw = vm.parseJson(vm.readFile(path));
        SentinelRow[] memory rows = abi.decode(raw, (SentinelRow[]));
        SentinelWindow.Obs[64] memory ring;
        uint8 head;
        uint64 lastFlip;
        uint256 startMs = rows.length == 0 ? 0 : rows[0].t_ms;

        for (uint256 i = 0; i < rows.length; i++) {
            uint64 ts = uint64(rows[i].t_ms / 1000);
            ring[head] = SentinelWindow.Obs({
                ts: ts,
                priceX96sq: _priceE18ToWindowValue(rows[i].p_e18)
            });
            head = uint8((head + 1) % 64);

            (uint192 lo, uint192 hi) = SentinelWindow.rangeInWindowMemory(ring, ts, windowSec);
            uint256 moveBps = SentinelWindow.moveBps(lo, hi);
            if (moveBps > trigBps && ts > lastFlip + 5 minutes) {
                result.triggerCount++;
                lastFlip = ts;
                if (result.firstTriggerMs == 0) {
                    result.firstTriggerMs = rows[i].t_ms;
                    result.firstTriggerOffsetSec = (rows[i].t_ms - startMs) / 1000;
                }
            }
        }
    }

    function _priceE18ToWindowValue(uint256 priceE18) internal pure returns (uint192) {
        return uint192(priceE18);
    }

    function _bledBefore(uint256 triggerMs) internal view returns (uint256) {
        if (triggerMs == 0) return type(uint256).max;
        bytes memory rawRows = vm.parseJson(vm.readFile(VOL_PATH));
        bytes memory rawTruth = vm.parseJson(vm.readFile(VOL_TRUTH_PATH));
        VolRow[] memory rows = abi.decode(rawRows, (VolRow[]));
        TruthRow[] memory truth = abi.decode(rawTruth, (TruthRow[]));
        assertEq(rows.length, truth.length, "vol truth length mismatch");

        int256 bleed;
        for (uint256 i = 0; i < rows.length; i++) {
            assertEq(rows[i].t_ms, truth[i].t_ms, "vol truth t_ms mismatch");
            if (rows[i].t_ms > triggerMs) break;
            if (truth[i].valid) bleed += truth[i].truth_mk_e6;
        }
        return uint256(bleed < 0 ? -bleed : bleed);
    }
}
