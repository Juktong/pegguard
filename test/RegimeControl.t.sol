// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Deployers} from "v4-core/test/utils/Deployers.sol";
import {HookMiner} from "v4-periphery/test/shared/HookMiner.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {PoolId} from "v4-core/src/types/PoolId.sol";

import {PegGuardHook} from "../src/PegGuardHook.sol";
import {IRegimeSignal} from "../src/interfaces/IRegimeSignal.sol";
import {RegimeReceiver} from "../src/reactive/RegimeReceiver.sol";
import {MockPyth} from "./mocks/MockPyth.sol";

contract RegimeControlTest is Deployers {
    MockPyth pyth;
    PegGuardHook hook;
    RegimeReceiver receiver;

    address callbackProxy;
    address rvm;

    function setUp() public {
        vm.warp(1_000);
        callbackProxy = makeAddr("callbackProxy");
        rvm = makeAddr("rvm");
        pyth = new MockPyth();

        deployFreshManager();

        uint160 flags = uint160(Hooks.BEFORE_INITIALIZE_FLAG | Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_SWAP_FLAG);
        (, bytes32 salt) =
            HookMiner.find(address(this), flags, type(PegGuardHook).creationCode, abi.encode(manager, pyth, address(this)));
        hook = new PegGuardHook{salt: salt}(manager, pyth, address(this));

        vm.prank(rvm);
        receiver = new RegimeReceiver(callbackProxy, hook);
        hook.setRegimeSource(address(receiver));
    }

    function test_receiverForwardsRegimeSignal() public {
        vm.prank(callbackProxy);
        receiver.onSignal(rvm, uint8(IRegimeSignal.Regime.VOLATILE), uint64(block.timestamp + 30 minutes));

        assertEq(uint256(hook.effectiveRegime()), uint256(IRegimeSignal.Regime.VOLATILE));
    }

    function test_receiverRejectsUnauthorizedSender() public {
        vm.prank(address(0xBEEF));
        vm.expectRevert("Authorized sender only");
        receiver.onSignal(rvm, uint8(IRegimeSignal.Regime.VOLATILE), uint64(block.timestamp + 30 minutes));
    }

    function test_receiverRejectsWrongRvmId() public {
        vm.prank(callbackProxy);
        vm.expectRevert("Authorized RVM ID only");
        receiver.onSignal(address(0xCAFE), uint8(IRegimeSignal.Regime.VOLATILE), uint64(block.timestamp + 30 minutes));
    }

    function test_receiverForwardsBreakerSignal() public {
        bytes32 rawPoolId = keccak256("pool");

        vm.prank(callbackProxy);
        receiver.onBreaker(rvm, rawPoolId, true);

        (,,, PegGuardHook.Breaker breaker,) = hook.states(PoolId.wrap(rawPoolId));
        assertEq(uint256(breaker), uint256(PegGuardHook.Breaker.ARMED));
    }
}
