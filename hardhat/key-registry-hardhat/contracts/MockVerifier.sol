// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract MockVerifier {
    function verifyTx(
        uint[2] calldata,
        uint[2][2] calldata,
        uint[2] calldata,
        uint[] calldata
    ) external pure returns (bool) {
        return true;
    }
}
