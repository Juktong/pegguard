// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Minimal Pyth pull-oracle interface (vendored subset).
/// For production use the official pyth-sdk-solidity; this subset keeps the
/// repo compiling without the dep. Struct layout matches IPyth.
interface IPyth {
    struct Price {
        int64 price;
        uint64 conf;
        int32 expo;
        uint256 publishTime;
    }

    /// @dev Reverts if no price or if older than `age` seconds.
    ///      maxStaleness provenance: calm sweep keeps precision >=95% at 5s;
    ///      volatile sweep needs <=2-3s for ~90%+ (see PARAMETERS.md).
    function getPriceNoOlderThan(bytes32 id, uint256 age) external view returns (Price memory);

    function getPriceUnsafe(bytes32 id) external view returns (Price memory);

    function updatePriceFeeds(bytes[] calldata updateData) external payable;

    function getUpdateFee(bytes[] calldata updateData) external view returns (uint256);
}
