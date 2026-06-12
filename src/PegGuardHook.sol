// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IHooks} from "v4-core/src/interfaces/IHooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {PoolId, PoolIdLibrary} from "v4-core/src/types/PoolId.sol";
import {BeforeSwapDelta, BeforeSwapDeltaLibrary} from "v4-core/src/types/BeforeSwapDelta.sol";
import {BalanceDelta} from "v4-core/src/types/BalanceDelta.sol";
import {LPFeeLibrary} from "v4-core/src/libraries/LPFeeLibrary.sol";
import {StateLibrary} from "v4-core/src/libraries/StateLibrary.sol";
import {FullMath} from "v4-core/src/libraries/FullMath.sol";

import {IPyth} from "./interfaces/IPyth.sol";
import {IRegimeSignal} from "./interfaces/IRegimeSignal.sol";
import {SignalMath} from "./lib/SignalMath.sol";

/// @title PegGuardHook - "Measured IL Insurance"
/// @notice Dual-mode dynamic-fee hook. Every parameter is calibrated from
///         real on-chain backtests (research/PARAMETERS.md):
///
///   HARVEST (volatile/LST pairs): toxic (correcting-direction) flow pays an
///   IL-insurance premium priced off the measured oracle deviation.
///   Corrected event-level replay baseline: 92.42% premium-weighted precision
///   in calm and 98.86% in the 5/23 volatile hot window under selected defaults.
///
///   GUARD (stable/anchored pairs): directional harvesting is provably
///   fuel-less (cross-venue deviations 0.000-0.35bps <= feed noise), so the
///   hook only runs a depeg circuit breaker.
///
///   INVARIANT - never revert, never trade worse than a static-fee pool:
///   any oracle failure (stale, anomalous conf, missing) degrades to the
///   symmetric base fee.
contract PegGuardHook is IHooks, IRegimeSignal {
    using PoolIdLibrary for PoolKey;
    using StateLibrary for IPoolManager;
    using LPFeeLibrary for uint24;

    enum Mode { DISABLED, HARVEST, GUARD }
    enum Breaker { NORMAL, ARMED, TRIPPED }

    struct PoolConfig {
        Mode    mode;
        bytes32 pythFeedId;     // e.g. ETH/USD for WETH/USDC (basis EMA absorbs USD-vs-quote)
        bool    oracleIsToken0PerQuote; // orientation flag: fair quotes token0 in quote units
        uint24  baseFeePips;    // symmetric base fee, e.g. 500 = 5bps
        uint24  capPips;        // premium clamp; research: 5000 = 50bps
        uint16  alphaNum;       // alpha = num/den; research: 1/2
        uint16  alphaDen;
        uint32  tauSec;         // basis EMA time constant; calibrated in research/PARAMETERS.md
        uint32  deadbandCalmE2;     // bps*100; protects benign flow (see PARAMETERS.md)
        uint32  deadbandVolE2;
        uint32  tripBps;        // guard mode: depeg trip threshold, e.g. 50bps (SNR>>feed noise 0.2bps)
        uint24  guardFeePips;   // fee on depeg-deepening direction when TRIPPED
    }

    struct PoolState {
        uint256 basisWad;       // pool-mid-units per oracle-unit EMA (absorbs decimals+basis)
        uint64  lastObsTime;
        uint64  confEmaE2;      // conf/price in bps*100, EMA - relative anomaly gate
        Breaker breaker;
        uint64  lastDisarmReq;
    }

    // ---- staleness guards (data-derived; see PARAMETERS.md) ----
    uint256 public constant MAX_STALENESS_CALM = 5;  // precision >=95% in calm sweep
    uint256 public constant MAX_STALENESS_VOL  = 2;  // vol sweep: 5s already decays to 87%
    uint256 public constant CONF_ANOMALY_NUM   = 3;  // conf > 3x its EMA => anomaly fallback
    uint64  public constant MIN_DISARM_DELAY   = 30 minutes;
    uint64  public constant REGIME_COOLDOWN    = 10 minutes;
    // Default deadbands are calibrated in research/PARAMETERS.md via EventDiff.
    uint32  public constant DEFAULT_DEADBAND_CALM_E2 = 50; // 0.5 bp
    uint32  public constant DEFAULT_DEADBAND_VOL_E2  = 50; // 0.5 bp

    IPoolManager public immutable poolManager;
    IPyth   public immutable pyth;
    address public regimeSource;   // RegimeReceiver (RN callback adapter)
    address public owner;

    Regime  public regime;         // IRegimeSignal.Regime
    uint64  public regimeExpiry;
    uint64  public lastTighten;

    mapping(PoolId => PoolConfig) public configs;
    mapping(PoolId => PoolState)  public states;

    error HookNotImplemented();
    error NotPoolManager();

    event RegimeChanged(Regime regime, uint64 expiry, address source);
    event BreakerChanged(PoolId indexed id, Breaker state);
    event PremiumCharged(PoolId indexed id, int256 devE2, uint24 feePips);
    event OracleFallback(PoolId indexed id, bytes32 reason);

    constructor(IPoolManager _manager, IPyth _pyth, address _owner) {
        require(_owner != address(0), "PegGuard: owner zero");
        poolManager = _manager;
        pyth = _pyth;
        owner = _owner;
        Hooks.validateHookPermissions(IHooks(address(this)), getHookPermissions());
    }

    modifier onlyPoolManager() {
        if (msg.sender != address(poolManager)) revert NotPoolManager();
        _;
    }

    // -------------------------------------------------- hook permissions
    function getHookPermissions() public pure returns (Hooks.Permissions memory) {
        return Hooks.Permissions({
            beforeInitialize: true,
            afterInitialize: false,
            beforeAddLiquidity: false,
            afterAddLiquidity: false,
            beforeRemoveLiquidity: false,
            afterRemoveLiquidity: false,
            beforeSwap: true,
            afterSwap: true,
            beforeDonate: false,
            afterDonate: false,
            beforeSwapReturnDelta: false,
            afterSwapReturnDelta: false,
            afterAddLiquidityReturnDelta: false,
            afterRemoveLiquidityReturnDelta: false
        });
    }

    function beforeInitialize(address, PoolKey calldata key, uint160)
        external
        onlyPoolManager
        returns (bytes4)
    {
        require(key.fee.isDynamicFee(), "PegGuard: pool must use dynamic fee flag");
        return IHooks.beforeInitialize.selector;
    }

    function afterInitialize(address, PoolKey calldata, uint160, int24)
        external
        onlyPoolManager
        returns (bytes4)
    {
        revert HookNotImplemented();
    }

    function beforeAddLiquidity(
        address,
        PoolKey calldata,
        IPoolManager.ModifyLiquidityParams calldata,
        bytes calldata
    ) external onlyPoolManager returns (bytes4) {
        revert HookNotImplemented();
    }

    function afterAddLiquidity(
        address,
        PoolKey calldata,
        IPoolManager.ModifyLiquidityParams calldata,
        BalanceDelta,
        BalanceDelta,
        bytes calldata
    ) external onlyPoolManager returns (bytes4, BalanceDelta) {
        revert HookNotImplemented();
    }

    function beforeRemoveLiquidity(
        address,
        PoolKey calldata,
        IPoolManager.ModifyLiquidityParams calldata,
        bytes calldata
    ) external onlyPoolManager returns (bytes4) {
        revert HookNotImplemented();
    }

    function afterRemoveLiquidity(
        address,
        PoolKey calldata,
        IPoolManager.ModifyLiquidityParams calldata,
        BalanceDelta,
        BalanceDelta,
        bytes calldata
    ) external onlyPoolManager returns (bytes4, BalanceDelta) {
        revert HookNotImplemented();
    }

    // -------------------------------------------------- hot path
    function beforeSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata params, bytes calldata)
        external
        onlyPoolManager
        returns (bytes4, BeforeSwapDelta, uint24)
    {
        PoolId id = key.toId();
        PoolConfig memory c = configs[id];
        if (c.mode == Mode.DISABLED) {
            return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
        }

        (uint256 fairWad, bool ok, bytes32 reason) = _readOracle(id, c, false);
        if (!ok) {
            emit OracleFallback(id, reason);
            return _beforeSwapFee(c.baseFeePips);
        }

        return _beforeSwapFee(_feeForOracle(id, c, fairWad, params.zeroForOne));
    }

    function _beforeSwapFee(uint24 fee) internal pure returns (bytes4, BeforeSwapDelta, uint24) {
        return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, fee | LPFeeLibrary.OVERRIDE_FEE_FLAG);
    }

    function _feeForOracle(PoolId id, PoolConfig memory c, uint256 fairWad, bool zeroForOne)
        internal
        returns (uint24)
    {
        PoolState storage s = states[id];
        if (s.basisWad == 0) {
            // basis not seeded yet: cannot price deviation - symmetric fee
            return c.baseFeePips;
        }

        (int256 devE2,) = SignalMath.deviationBps(_poolMidWad(id), fairWad, s.basisWad);
        return _feeForSignal(id, c, s, devE2, zeroForOne);
    }

    function _feeForSignal(
        PoolId id,
        PoolConfig memory c,
        PoolState storage s,
        int256 devE2,
        bool zeroForOne
    ) internal returns (uint24 fee) {
        fee = c.baseFeePips;
        if (c.mode == Mode.HARVEST) {
            if (SignalMath.isCorrecting(devE2, zeroForOne)) {
                uint256 absE2 = uint256(devE2 < 0 ? -devE2 : devE2);
                uint32 db = effectiveRegime() == Regime.VOLATILE ? c.deadbandVolE2 : c.deadbandCalmE2;
                uint24 prem = SignalMath.premiumPips(absE2, db, c.alphaNum, c.alphaDen, c.capPips);
                if (prem > 0) {
                    fee = c.baseFeePips + prem;
                    emit PremiumCharged(id, devE2, fee);
                }
            }
        } else {
            // GUARD: no directional harvesting (measured: no fuel) - breaker only
            uint256 absE2 = uint256(devE2 < 0 ? -devE2 : devE2);
            if (s.breaker != Breaker.TRIPPED && absE2 > uint256(c.tripBps) * 100) {
                s.breaker = Breaker.TRIPPED; // trip is monotone-tightening: on-chain, instant
                s.lastDisarmReq = 0;
                emit BreakerChanged(id, Breaker.TRIPPED);
            }
            if (s.breaker == Breaker.TRIPPED) {
                // deepening direction pays guardFee; correcting (re-pegging) flow pays base
                if (!SignalMath.isCorrecting(devE2, zeroForOne)) fee = c.guardFeePips;
            }
        }
    }

    /// @dev Basis/conf EMA upkeep AFTER the swap (matches research methodology:
    ///      slow basis estimated on post-swap gap; deviation priced on pre-swap mid).
    ///      Skipped when oracle is stale - a stale observation poisons the basis.
    function afterSwap(address, PoolKey calldata key, IPoolManager.SwapParams calldata, BalanceDelta, bytes calldata)
        external
        onlyPoolManager
        returns (bytes4, int128)
    {
        PoolId id = key.toId();
        PoolConfig memory c = configs[id];
        if (c.mode == Mode.DISABLED) return (IHooks.afterSwap.selector, 0);

        (uint256 fairWad, bool ok,) = _readOracle(id, c, true);
        if (ok) {
            PoolState storage s = states[id];
            uint256 midWad = _poolMidWad(id);
            uint256 obs = FullMath.mulDiv(midWad, SignalMath.WAD, fairWad);
            uint256 dt = block.timestamp - s.lastObsTime;
            s.basisWad = SignalMath.emaUpdate(s.basisWad, obs, dt, c.tauSec);
            s.lastObsTime = uint64(block.timestamp);
        }
        return (IHooks.afterSwap.selector, 0);
    }

    function beforeDonate(address, PoolKey calldata, uint256, uint256, bytes calldata)
        external
        onlyPoolManager
        returns (bytes4)
    {
        revert HookNotImplemented();
    }

    function afterDonate(address, PoolKey calldata, uint256, uint256, bytes calldata)
        external
        onlyPoolManager
        returns (bytes4)
    {
        revert HookNotImplemented();
    }

    // -------------------------------------------------- oracle plumbing
    function _readOracle(PoolId id, PoolConfig memory c, bool updateConfEma)
        internal returns (uint256 fairWad, bool ok, bytes32 reason)
    {
        uint256 maxAge = effectiveRegime() == Regime.VOLATILE ? MAX_STALENESS_VOL : MAX_STALENESS_CALM;
        try pyth.getPriceNoOlderThan(c.pythFeedId, maxAge) returns (IPyth.Price memory p) {
            if (p.price <= 0) return (0, false, "BAD_PRICE");
            // conf relative-anomaly gate. Research: conf (~10bps) >> signal (~1bps),
            // so an ABSOLUTE conf gate would never fire - gate on conf vs its own EMA.
            PoolState storage s = states[id];
            uint64 confE2 = uint64(FullMath.mulDiv(p.conf, 1e6, uint64(p.price))); // bps*100
            if (s.confEmaE2 != 0 && confE2 > s.confEmaE2 * CONF_ANOMALY_NUM) {
                return (0, false, "CONF_SPIKE");
            }
            if (updateConfEma) {
                s.confEmaE2 = s.confEmaE2 == 0 ? confE2 : uint64((uint256(s.confEmaE2) * 9 + confE2) / 10);
            }
            fairWad = _toWad(p.price, p.expo);
            if (!c.oracleIsToken0PerQuote) fairWad = (SignalMath.WAD * SignalMath.WAD) / fairWad;
            return (fairWad, true, "");
        } catch {
            return (0, false, "STALE_OR_MISSING");
        }
    }

    function _toWad(int64 price, int32 expo) internal pure returns (uint256) {
        uint256 p = uint256(uint64(price));
        // wad = p * 10^(18+expo)
        if (expo >= -18) return p * (10 ** uint32(int32(18) + expo));
        return p / (10 ** uint32(-(int32(18) + expo)));
    }

    function _poolMidWad(PoolId id) internal view returns (uint256) {
        (uint160 sqrtPriceX96,,,) = poolManager.getSlot0(id);
        uint256 px = FullMath.mulDiv(uint256(sqrtPriceX96), uint256(sqrtPriceX96), 1 << 96);
        return FullMath.mulDiv(px, SignalMath.WAD, 1 << 96); // token1-per-token0, raw decimals (basis absorbs)
    }

    // -------------------------------------------------- control plane (RN)
    /// @inheritdoc IRegimeSignal
    function onRegimeSignal(Regime r, uint64 expiry) external {
        require(msg.sender == regimeSource || msg.sender == owner, "PegGuard: not regime source");
        if (r == Regime.VOLATILE) {
            require(expiry > block.timestamp, "PegGuard: bad expiry");
            if (expiry < regimeExpiry) expiry = regimeExpiry;
            regime = r; regimeExpiry = expiry; lastTighten = uint64(block.timestamp); // tighten: instant
        } else {
            // loosen: only after expiry or cooldown - forged callback can't relax the guard
            require(block.timestamp >= regimeExpiry || block.timestamp >= lastTighten + REGIME_COOLDOWN,
                    "PegGuard: loosen blocked");
            regime = Regime.CALM; regimeExpiry = 0;
        }
        emit RegimeChanged(regime, regimeExpiry, msg.sender);
    }

    /// @inheritdoc IRegimeSignal
    function onBreakerSignal(bytes32 poolId, bool armed) external {
        require(msg.sender == regimeSource || msg.sender == owner, "PegGuard: not regime source");
        PoolState storage s = states[PoolId.wrap(poolId)];
        if (armed) {
            s.lastDisarmReq = 0;
            if (s.breaker == Breaker.NORMAL) s.breaker = Breaker.ARMED;       // tighten: instant
        } else {
            if (s.breaker == Breaker.NORMAL) { s.lastDisarmReq = 0; return; }
            // disarm hysteresis: control plane must hold the request for MIN_DISARM_DELAY
            if (s.lastDisarmReq == 0) { s.lastDisarmReq = uint64(block.timestamp); return; }
            require(block.timestamp >= s.lastDisarmReq + MIN_DISARM_DELAY, "PegGuard: disarm delay");
            s.breaker = Breaker.NORMAL; s.lastDisarmReq = 0;
        }
        emit BreakerChanged(PoolId.wrap(poolId), s.breaker);
    }

    /// @dev VOLATILE auto-expires to CALM. Expiry-as-loosening is safe because
    ///      the expiry was set by the tightening callback itself; if vol
    ///      persists the sentinel re-tightens, and if RN is fully down the
    ///      conf-spike gate still degrades pricing to symmetric under stress.
    function effectiveRegime() public view returns (Regime) {
        if (regime == Regime.VOLATILE && block.timestamp >= regimeExpiry) return Regime.CALM;
        return regime;
    }

    // -------------------------------------------------- admin
    function setPoolConfig(PoolKey calldata key, PoolConfig calldata c) external {
        require(msg.sender == owner, "PegGuard: not owner");
        configs[key.toId()] = c;
    }
    function setRegimeSource(address src) external {
        require(msg.sender == owner, "PegGuard: not owner");
        regimeSource = src;
    }
}
