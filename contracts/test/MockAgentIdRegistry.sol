// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

contract MockAgentIdRegistry {
    mapping(address owner => uint256 balance) private balances;
    bool private shouldRevert;

    function setBalance(address owner, uint256 balance) external {
        balances[owner] = balance;
    }

    function setShouldRevert(bool value) external {
        shouldRevert = value;
    }

    function balanceOf(address owner) external view returns (uint256) {
        require(!shouldRevert, "registry unavailable");
        return balances[owner];
    }
}
