// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {HookMiner} from "v4-periphery/test/shared/HookMiner.sol";
import {Hooks} from "v4-core/src/libraries/Hooks.sol";
import {IHooks} from "v4-core/src/interfaces/IHooks.sol";
import {IPoolManager} from "v4-core/src/interfaces/IPoolManager.sol";
import {PoolKey} from "v4-core/src/types/PoolKey.sol";
import {PoolId, PoolIdLibrary} from "v4-core/src/types/PoolId.sol";
import {Currency} from "v4-core/src/types/Currency.sol";
import {BalanceDelta, BalanceDeltaLibrary} from "v4-core/src/types/BalanceDelta.sol";
import {LPFeeLibrary} from "v4-core/src/libraries/LPFeeLibrary.sol";
import {TickMath} from "v4-core/src/libraries/TickMath.sol";
import {PoolModifyLiquidityTest} from "v4-core/src/test/PoolModifyLiquidityTest.sol";
import {PoolSwapTest} from "v4-core/src/test/PoolSwapTest.sol";
import {TestERC20} from "v4-core/src/test/TestERC20.sol";

import {PegGuardHook} from "../src/PegGuardHook.sol";
import {MockPyth} from "../test/mocks/MockPyth.sol";

contract TestnetHookExerciser {
    using BalanceDeltaLibrary for BalanceDelta;

    uint160 constant SQRT_PRICE_1_1 = 79228162514264337593543950336;

    MockPyth public immutable pyth;
    IPoolManager public immutable manager;
    PoolModifyLiquidityTest public immutable modifyLiquidityRouter;
    PoolSwapTest public immutable swapRouter;
    TestERC20 public immutable token0;
    TestERC20 public immutable token1;

    event ExerciseComplete(
        bytes32 indexed poolId,
        int128 seedAmount0,
        int128 seedAmount1,
        int128 premiumAmount0,
        int128 premiumAmount1,
        uint256 token0Balance,
        uint256 token1Balance
    );

    constructor(
        MockPyth _pyth,
        IPoolManager _manager,
        PoolModifyLiquidityTest _modifyLiquidityRouter,
        PoolSwapTest _swapRouter,
        TestERC20 _token0,
        TestERC20 _token1
    ) {
        pyth = _pyth;
        manager = _manager;
        modifyLiquidityRouter = _modifyLiquidityRouter;
        swapRouter = _swapRouter;
        token0 = _token0;
        token1 = _token1;
    }

    function run(PoolKey calldata key) external returns (BalanceDelta seedDelta, BalanceDelta premiumDelta) {
        token0.mint(address(this), 1e30);
        token1.mint(address(this), 1e30);
        token0.approve(address(modifyLiquidityRouter), type(uint256).max);
        token1.approve(address(modifyLiquidityRouter), type(uint256).max);
        token0.approve(address(swapRouter), type(uint256).max);
        token1.approve(address(swapRouter), type(uint256).max);

        manager.initialize(key, SQRT_PRICE_1_1);
        modifyLiquidityRouter.modifyLiquidity(
            key,
            IPoolManager.ModifyLiquidityParams({
                tickLower: -600,
                tickUpper: 600,
                liquidityDelta: 1e21,
                salt: bytes32(0)
            }),
            ""
        );

        PoolSwapTest.TestSettings memory settings =
            PoolSwapTest.TestSettings({takeClaims: false, settleUsingBurn: false});

        pyth.set(100_000_000, 100, -8, block.timestamp);
        seedDelta = swapRouter.swap(
            key,
            IPoolManager.SwapParams({
                zeroForOne: true,
                amountSpecified: -1e16,
                sqrtPriceLimitX96: TickMath.MIN_SQRT_PRICE + 1
            }),
            settings,
            ""
        );

        pyth.set(102_000_000, 100, -8, block.timestamp);
        premiumDelta = swapRouter.swap(
            key,
            IPoolManager.SwapParams({
                zeroForOne: false,
                amountSpecified: -1e16,
                sqrtPriceLimitX96: TickMath.MAX_SQRT_PRICE - 1
            }),
            settings,
            ""
        );

        emit ExerciseComplete(
            PoolId.unwrap(PoolIdLibrary.toId(key)),
            seedDelta.amount0(),
            seedDelta.amount1(),
            premiumDelta.amount0(),
            premiumDelta.amount1(),
            token0.balanceOf(address(this)),
            token1.balanceOf(address(this))
        );
    }
}

contract TestnetExercise is Script {
    using PoolIdLibrary for PoolKey;

    address constant CREATE2_DEPLOYER = 0x4e59b44847b379578588920cA78FbF26c0B4956C;
    bytes32 constant FEED_ID = bytes32("PEGGUARD_TEST");
    uint160 constant HOOK_FLAGS =
        uint160(Hooks.BEFORE_INITIALIZE_FLAG | Hooks.BEFORE_SWAP_FLAG | Hooks.AFTER_SWAP_FLAG);

    function run() external {
        uint256 privateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(privateKey);
        IPoolManager manager = IPoolManager(vm.envAddress("POOL_MANAGER"));

        vm.startBroadcast(privateKey);
        MockPyth pyth = new MockPyth();
        PoolModifyLiquidityTest modifyLiquidityRouter = new PoolModifyLiquidityTest(manager);
        PoolSwapTest swapRouter = new PoolSwapTest(manager);

        (TestERC20 token0, TestERC20 token1) = _deploySortedTokens();
        PegGuardHook hook = _deployHook(manager, pyth, deployer);
        PoolKey memory key = _poolKey(hook, token0, token1);
        bytes32 poolId = PoolId.unwrap(key.toId());

        _configureHook(hook, key);

        TestnetHookExerciser exerciser =
            new TestnetHookExerciser(pyth, manager, modifyLiquidityRouter, swapRouter, token0, token1);
        exerciser.run(key);
        vm.stopBroadcast();

        console2.log("exercise hook", address(hook));
        console2.log("mock pyth", address(pyth));
        console2.log("token0", address(token0));
        console2.log("token1", address(token1));
        console2.log("modify router", address(modifyLiquidityRouter));
        console2.log("swap router", address(swapRouter));
        console2.log("exerciser", address(exerciser));
        console2.logBytes32(poolId);
    }

    function _deployHook(IPoolManager manager, MockPyth pyth, address deployer) internal returns (PegGuardHook hook) {
        bytes memory constructorArgs = abi.encode(manager, pyth, deployer);
        (address expectedHook, bytes32 salt) =
            HookMiner.find(CREATE2_DEPLOYER, HOOK_FLAGS, type(PegGuardHook).creationCode, constructorArgs);
        hook = new PegGuardHook{salt: salt}(manager, pyth, deployer);
        require(address(hook) == expectedHook, "TestnetExercise: hook address mismatch");
    }

    function _poolKey(PegGuardHook hook, TestERC20 token0, TestERC20 token1) internal pure returns (PoolKey memory) {
        return PoolKey({
            currency0: Currency.wrap(address(token0)),
            currency1: Currency.wrap(address(token1)),
            fee: LPFeeLibrary.DYNAMIC_FEE_FLAG,
            tickSpacing: 60,
            hooks: IHooks(address(hook))
        });
    }

    function _configureHook(PegGuardHook hook, PoolKey memory key) internal {
        hook.setPoolConfig(
            key,
            PegGuardHook.PoolConfig({
                mode: PegGuardHook.Mode.HARVEST,
                pythFeedId: FEED_ID,
                oracleIsToken0PerQuote: true,
                baseFeePips: 500,
                capPips: 5000,
                alphaNum: 1,
                alphaDen: 2,
                tauSec: 450,
                deadbandCalmE2: 50,
                deadbandVolE2: 50,
                tripBps: 50,
                guardFeePips: 5000
            })
        );
    }

    function _deploySortedTokens() internal returns (TestERC20 token0, TestERC20 token1) {
        TestERC20 tokenA = new TestERC20(0);
        TestERC20 tokenB = new TestERC20(0);
        (token0, token1) = address(tokenA) < address(tokenB) ? (tokenA, tokenB) : (tokenB, tokenA);
    }
}
