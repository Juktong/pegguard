// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IPyth} from "../../src/interfaces/IPyth.sol";

contract MockPyth is IPyth {
    Price internal p;

    function set(int64 price, uint64 conf, int32 expo, uint256 publishTime) external {
        p = Price(price, conf, expo, publishTime);
    }

    function getPriceNoOlderThan(bytes32, uint256 age) external view returns (Price memory) {
        require(block.timestamp - p.publishTime <= age, "StalePrice");
        return p;
    }

    function getPriceUnsafe(bytes32) external view returns (Price memory) { return p; }
    function updatePriceFeeds(bytes[] calldata) external payable {}
    function getUpdateFee(bytes[] calldata) external pure returns (uint256) { return 0; }
}
