// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

/// @notice Minimal interface published by the Agent ID hackathon rules.
interface IAgentIdRegistry {
    function balanceOf(address owner) external view returns (uint256);
}

/// @title VeriAbstain Evidence Registry
/// @notice Records content-addressed evidence assessments from Agent ID holders.
/// @dev A receipt proves only that an eligible address recorded two digests. It
///      does not prove the evidence or assessment is true and grants no authority.
contract VeriAbstainEvidenceRegistry {
    uint256 public constant BSC_MAINNET_CHAIN_ID = 56;
    address public constant BSC_AGENT_ID_REGISTRY =
        0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F;

    address public immutable agentIdRegistry;
    uint256 public receiptCount;
    uint256 public uniqueAgentCount;

    mapping(address agent => bool participated) public hasParticipated;
    mapping(address agent => mapping(bytes32 evidenceDigest => bool recorded))
        public recorded;

    error InvalidAgentIdRegistry();
    error WrongMainnetAgentIdRegistry();
    error InvalidDigest();
    error AgentIdRegistryCheckFailed();
    error AgentIdRequired();
    error DuplicateEvidenceReceipt();

    event AssessmentRecorded(
        address indexed agent,
        bytes32 indexed evidenceDigest,
        bytes32 indexed assessmentDigest,
        uint256 receiptIndex,
        bool firstInteraction
    );

    constructor(address agentIdRegistry_) {
        if (agentIdRegistry_ == address(0) || agentIdRegistry_.code.length == 0) {
            revert InvalidAgentIdRegistry();
        }
        if (
            block.chainid == BSC_MAINNET_CHAIN_ID &&
            agentIdRegistry_ != BSC_AGENT_ID_REGISTRY
        ) {
            revert WrongMainnetAgentIdRegistry();
        }
        agentIdRegistry = agentIdRegistry_;
    }

    /// @notice Returns false if the registry is unavailable or malformed.
    function isAgentIdHolder(address account) public view returns (bool) {
        try IAgentIdRegistry(agentIdRegistry).balanceOf(account) returns (
            uint256 balance
        ) {
            return balance > 0;
        } catch {
            return false;
        }
    }

    /// @notice Record one assessment for one evidence digest.
    /// @param evidenceDigest Digest of the exact evidence envelope or package.
    /// @param assessmentDigest Digest of the exact validator assessment.
    function recordAssessment(
        bytes32 evidenceDigest,
        bytes32 assessmentDigest
    ) external {
        if (evidenceDigest == bytes32(0) || assessmentDigest == bytes32(0)) {
            revert InvalidDigest();
        }

        uint256 balance;
        try IAgentIdRegistry(agentIdRegistry).balanceOf(msg.sender) returns (
            uint256 currentBalance
        ) {
            balance = currentBalance;
        } catch {
            revert AgentIdRegistryCheckFailed();
        }
        if (balance == 0) revert AgentIdRequired();
        if (recorded[msg.sender][evidenceDigest]) {
            revert DuplicateEvidenceReceipt();
        }

        bool firstInteraction = !hasParticipated[msg.sender];
        recorded[msg.sender][evidenceDigest] = true;
        receiptCount += 1;
        if (firstInteraction) {
            hasParticipated[msg.sender] = true;
            uniqueAgentCount += 1;
        }

        emit AssessmentRecorded(
            msg.sender,
            evidenceDigest,
            assessmentDigest,
            receiptCount,
            firstInteraction
        );
    }
}
