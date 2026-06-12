// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {HookMiner} from "v4-periphery/test/shared/HookMiner.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";

import {PegGuardHook} from "../src/PegGuardHook.sol";
import {IPyth} from "../src/interfaces/IPyth.sol";
import {RegimeReceiver} from "../src/reactive/RegimeReceiver.sol";

/// Deploy PegGuardHook and its Reactive Network callback receiver.
///
/// Required env:
/// - `PRIVATE_KEY`: broadcaster private key
/// - `POOL_MANAGER`: v4 PoolManager address
/// - `PYTH`: Pyth contract address on the hook chain
/// - `RN_CALLBACK_PROXY`: Reactive Network callback proxy on the hook chain
contract Deploy is Script {
    address constant CREATE2_DEPLOYER = 0x4e59b44847b379578588920cA78FbF26c0B4956C;

    uint160 constant HOOK_FLAGS =
        uint160(Hooks.BEFORE_INITIALIZE_FLAG | Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_SWAP_FLAG);

    function run() external returns (PegGuardHook hook, RegimeReceiver receiver) {
        uint256 privateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(privateKey);
        IPoolManager poolManager = IPoolManager(vm.envAddress("POOL_MANAGER"));
        IPyth pyth = IPyth(vm.envAddress("PYTH"));
        address callbackProxy = vm.envAddress("RN_CALLBACK_PROXY");

        bytes memory constructorArgs = abi.encode(poolManager, pyth, deployer);
        (address expectedHook, bytes32 salt) =
            HookMiner.find(CREATE2_DEPLOYER, HOOK_FLAGS, type(PegGuardHook).creationCode, constructorArgs);

        vm.startBroadcast(privateKey);
        hook = new PegGuardHook{salt: salt}(poolManager, pyth, deployer);
        require(address(hook) == expectedHook, "Deploy: hook address mismatch");

        receiver = new RegimeReceiver(callbackProxy, hook);
        hook.setRegimeSource(address(receiver));
        vm.stopBroadcast();
    }
}
