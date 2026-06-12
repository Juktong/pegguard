// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AbstractCallback} from "reactive-lib/abstract-base/AbstractCallback.sol";
import {IRegimeSignal} from "../interfaces/IRegimeSignal.sol";

/// @title RegimeReceiver - RN callback adapter on the hook chain
/// @notice Thin, auditable boundary between Reactive Network's callback proxy
///         and the hook. Defense-in-depth on top of the hook's own monotone
///         rules (a compromised receiver can still only tighten quickly /
///         loosen slowly - the hook enforces that independently).
contract RegimeReceiver is AbstractCallback {
    address public immutable callbackProxy; // RN's per-chain callback sender
    IRegimeSignal public immutable hook;

    constructor(address _proxy, IRegimeSignal _hook) AbstractCallback(_proxy) {
        callbackProxy = _proxy;
        hook = _hook;
    }

    /// @dev RN injects the RVM id as the first parameter (per reactive-lib
    ///      callback convention) - verify against your pinned lib version.
    function onSignal(address rvm_id, uint8 regime, uint64 expiry)
        external
        authorizedSenderOnly
        rvmIdOnly(rvm_id)
    {
        hook.onRegimeSignal(IRegimeSignal.Regime(regime), expiry);
    }

    function onBreaker(address rvm_id, bytes32 poolId, bool armed)
        external
        authorizedSenderOnly
        rvmIdOnly(rvm_id)
    {
        hook.onBreakerSignal(poolId, armed);
    }
}
