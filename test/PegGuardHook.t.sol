// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Deployers} from "v4-core/test/utils/Deployers.sol";
import {HookMiner} from "v4-periphery/test/shared/HookMiner.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IHooks} from "v4-core/src/interfaces/IHooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {LPFeeLibrary} from "v4-core/src/libraries/LPFeeLibrary.sol";
import {PoolId} from "v4-core/src/types/PoolId.sol";
import {BalanceDelta} from "v4-core/src/types/BalanceDelta.sol";
import {StateLibrary} from "v4-core/src/libraries/StateLibrary.sol";

import {PegGuardHook} from "../src/PegGuardHook.sol";
import {IRegimeSignal} from "../src/interfaces/IRegimeSignal.sol";
import {SignalMath} from "../src/lib/SignalMath.sol";
import {MockPyth} from "./mocks/MockPyth.sol";

/// @title PegGuardHook unit tests
contract PegGuardHookTest is Deployers {
    using StateLibrary for IPoolManager;

    bytes32 constant FEED_ID = bytes32("ETH/USD");
    uint24 constant BASE_FEE = 500;
    uint24 constant CAP_PIPS = 5000;
    uint24 constant GUARD_FEE = 10_000;
    uint32 constant DEFAULT_DEADBAND_E2 = 50;

    MockPyth pyth;
    PegGuardHook hook;
    PoolId poolId;

    function setUp() public {
        vm.warp(1_000);
        pyth = new MockPyth();

        deployFreshManagerAndRouters();
        deployMintAndApprove2Currencies();

        uint160 flags = uint160(Hooks.BEFORE_INITIALIZE_FLAG | Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_SWAP_FLAG);
        (address expectedHook, bytes32 salt) =
            HookMiner.find(address(this), flags, type(PegGuardHook).creationCode, abi.encode(manager, pyth, address(this)));

        hook = new PegGuardHook{salt: salt}(manager, pyth, address(this));
        assertEq(address(hook), expectedHook, "hook address flags");

        (key, poolId) =
            initPoolAndAddLiquidity(currency0, currency1, IHooks(address(hook)), LPFeeLibrary.DYNAMIC_FEE_FLAG, SQRT_PRICE_1_1);
        hook.setPoolConfig(key, _harvestConfig());
    }

    function _harvestConfig() internal pure returns (PegGuardHook.PoolConfig memory) {
        return PegGuardHook.PoolConfig({
            mode: PegGuardHook.Mode.HARVEST,
            pythFeedId: FEED_ID,
            oracleIsToken0PerQuote: true,
            baseFeePips: BASE_FEE,
            capPips: CAP_PIPS,
            alphaNum: 1,
            alphaDen: 2,
            tauSec: 450,
            deadbandCalmE2: DEFAULT_DEADBAND_E2,
            deadbandVolE2: DEFAULT_DEADBAND_E2,
            tripBps: 50,
            guardFeePips: GUARD_FEE
        });
    }

    function _guardConfig() internal pure returns (PegGuardHook.PoolConfig memory c) {
        c = _harvestConfig();
        c.mode = PegGuardHook.Mode.GUARD;
    }

    function _params(bool zeroForOne) internal view returns (IPoolManager.SwapParams memory) {
        return IPoolManager.SwapParams({
            zeroForOne: zeroForOne,
            amountSpecified: -100,
            sqrtPriceLimitX96: zeroForOne ? MIN_PRICE_LIMIT : MAX_PRICE_LIMIT
        });
    }

    function _setFreshPrice(int64 price) internal {
        pyth.set(price, 100, -8, block.timestamp);
    }

    function _beforeSwapFee(bool zeroForOne) internal returns (uint24 fee) {
        vm.prank(address(manager));
        (,, fee) = hook.beforeSwap(address(this), key, _params(zeroForOne), ZERO_BYTES);
    }

    function _afterSwap() internal {
        vm.prank(address(manager));
        hook.afterSwap(address(this), key, _params(true), BalanceDelta.wrap(0), ZERO_BYTES);
    }

    function _overrideFee(uint24 fee) internal pure returns (uint24) {
        return fee | LPFeeLibrary.OVERRIDE_FEE_FLAG;
    }

    function _basis() internal view returns (uint256 basisWad) {
        (basisWad,,,,) = hook.states(poolId);
    }

    function _breaker() internal view returns (PegGuardHook.Breaker breaker) {
        (,,, breaker,) = hook.states(poolId);
    }

    // ---- INVARIANT: never worse than a static pool ----
    function test_staleOracle_fallsBackToBaseFee() public {
        pyth.set(100_000_000, 100, -8, block.timestamp - 10);

        uint24 fee = _beforeSwapFee(true);

        assertEq(fee, _overrideFee(BASE_FEE));
    }

    function test_confSpike_fallsBackToBaseFee() public {
        _setFreshPrice(100_000_000);
        _afterSwap();

        pyth.set(100_000_000, 400, -8, block.timestamp);
        uint24 fee = _beforeSwapFee(true);

        assertEq(fee, _overrideFee(BASE_FEE));
    }

    function test_unseededBasis_fallsBackToBaseFee() public {
        _setFreshPrice(100_000_000);

        uint24 fee = _beforeSwapFee(true);

        assertEq(fee, _overrideFee(BASE_FEE));
        assertEq(_basis(), 0);
    }

    // ---- directional premium ----
    function test_correctingSide_paysPremium_otherSideDoesNot() public {
        _setFreshPrice(100_000_000);
        _afterSwap();

        _setFreshPrice(100_020_000); // fair is 2 bps above pool mid, 1.5 bps over deadband

        assertEq(_beforeSwapFee(false), _overrideFee(BASE_FEE + 75));
        assertEq(_beforeSwapFee(true), _overrideFee(BASE_FEE));
    }

    function test_premium_respectsDeadbandAndCap() public pure {
        assertEq(SignalMath.premiumPips(100, 0, 1, 2, 5000), 50);
        assertEq(SignalMath.premiumPips(50, 100, 1, 2, 5000), 0);
        assertEq(SignalMath.premiumPips(100000, 0, 1, 2, 5000), 5000);
    }

    function test_deviationBps_keepsE2Resolution() public pure {
        (int256 devE2,) = SignalMath.deviationBps(1_000_000e18, 1_000_082e18, 1e18);

        assertEq(devE2, 82);
        assertEq(SignalMath.premiumPips(uint256(devE2), 0, 1, 2, 5000), 41);
    }

    // ---- monotone safety (regime) ----
    function test_tighten_appliesImmediately() public {
        hook.onRegimeSignal(IRegimeSignal.Regime.VOLATILE, uint64(block.timestamp + 30 minutes));

        assertEq(uint256(hook.effectiveRegime()), uint256(IRegimeSignal.Regime.VOLATILE));
    }

    function test_loosen_blockedDuringCooldown() public {
        hook.onRegimeSignal(IRegimeSignal.Regime.VOLATILE, uint64(block.timestamp + 30 minutes));

        vm.expectRevert("PegGuard: loosen blocked");
        hook.onRegimeSignal(IRegimeSignal.Regime.CALM, 0);
    }

    function test_regimeExpiry_revertsToCalm() public {
        hook.onRegimeSignal(IRegimeSignal.Regime.VOLATILE, uint64(block.timestamp + 10));

        vm.warp(block.timestamp + 10);

        assertEq(uint256(hook.effectiveRegime()), uint256(IRegimeSignal.Regime.CALM));
    }

    function test_volatileSignal_cannotUseExpiredOrShorterExpiry() public {
        vm.expectRevert("PegGuard: bad expiry");
        hook.onRegimeSignal(IRegimeSignal.Regime.VOLATILE, uint64(block.timestamp));

        hook.onRegimeSignal(IRegimeSignal.Regime.VOLATILE, uint64(block.timestamp + 30 minutes));
        hook.onRegimeSignal(IRegimeSignal.Regime.VOLATILE, uint64(block.timestamp + 1 minutes));

        assertEq(hook.regimeExpiry(), uint64(block.timestamp + 30 minutes));
        assertEq(uint256(hook.effectiveRegime()), uint256(IRegimeSignal.Regime.VOLATILE));
    }

    function test_unauthorizedRegimeSource_reverts() public {
        vm.prank(address(0xBEEF));
        vm.expectRevert("PegGuard: not regime source");
        hook.onRegimeSignal(IRegimeSignal.Regime.VOLATILE, uint64(block.timestamp + 30 minutes));
    }

    // ---- guard mode / breaker ----
    function test_breakerTrips_onChain_aboveThreshold() public {
        hook.setPoolConfig(key, _guardConfig());
        _setFreshPrice(100_000_000);
        _afterSwap();

        _setFreshPrice(101_000_000);
        _beforeSwapFee(true);

        assertEq(uint256(_breaker()), uint256(PegGuardHook.Breaker.TRIPPED));
    }

    function test_tripped_deepeningPaysGuardFee_repeggingPaysBase() public {
        hook.setPoolConfig(key, _guardConfig());
        _setFreshPrice(100_000_000);
        _afterSwap();

        _setFreshPrice(101_000_000);

        assertEq(_beforeSwapFee(true), _overrideFee(GUARD_FEE));
        assertEq(_beforeSwapFee(false), _overrideFee(BASE_FEE));
    }

    function test_disarm_requiresHysteresisDelay() public {
        hook.onBreakerSignal(PoolId.unwrap(poolId), true);
        hook.onBreakerSignal(PoolId.unwrap(poolId), false);

        vm.expectRevert("PegGuard: disarm delay");
        hook.onBreakerSignal(PoolId.unwrap(poolId), false);

        vm.warp(block.timestamp + hook.MIN_DISARM_DELAY());
        hook.onBreakerSignal(PoolId.unwrap(poolId), false);

        assertEq(uint256(_breaker()), uint256(PegGuardHook.Breaker.NORMAL));
    }

    function test_disarmRequestWhileNormal_cannotPreseedHysteresis() public {
        hook.onBreakerSignal(PoolId.unwrap(poolId), false);
        vm.warp(block.timestamp + hook.MIN_DISARM_DELAY());
        hook.onBreakerSignal(PoolId.unwrap(poolId), true);
        hook.onBreakerSignal(PoolId.unwrap(poolId), false);

        vm.expectRevert("PegGuard: disarm delay");
        hook.onBreakerSignal(PoolId.unwrap(poolId), false);
    }

    // ---- basis hygiene ----
    function test_basisEma_notUpdated_whenOracleStale() public {
        _setFreshPrice(100_000_000);
        _afterSwap();
        uint256 beforeBasis = _basis();

        pyth.set(200_000_000, 100, -8, block.timestamp - 10);
        _afterSwap();

        assertEq(_basis(), beforeBasis);
    }
}
