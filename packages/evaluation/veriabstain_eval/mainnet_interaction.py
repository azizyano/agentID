"""Fail-closed preparation of one unsigned Agent ID MVP interaction."""
from web3 import Web3

from .mvp_receipt import validate_receipt_plan

CHAIN_ID = 56
CONTRACT = Web3.to_checksum_address('0x8ACF294c769e25dAb44aCbEb83fc401cA0702388')
OFFICIAL_REGISTRY = Web3.to_checksum_address('0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F')
EXPECTED_RUNTIME_HASH = '0x9d92959c3d3facfa24ad21299ecd27f69c001f4576fd540a9a6b93dabfc4eb8c'
MAX_GAS_ESTIMATE = 300_000


def _read(contract, name, block_number, *arguments):
    return getattr(contract.functions, name)(*arguments).call(block_identifier=block_number)


def prepare_interaction(w3, participant, receipt_plan, contract_abi, registry_abi):
    """Check finalized eligibility/state and return one unsigned zero-value call."""
    if type(w3.eth.chain_id) is not int or w3.eth.chain_id != CHAIN_ID:
        raise ValueError('BSC mainnet chain 56 required')
    if not isinstance(participant, str) or not Web3.is_address(participant):
        raise ValueError('Participant address is invalid')
    participant = Web3.to_checksum_address(participant)
    plan = validate_receipt_plan(receipt_plan)

    finalized = w3.eth.get_block('finalized')
    if type(finalized['number']) is not int or finalized['number'] < 0:
        raise ValueError('Finalized block is invalid')
    block_number = finalized['number']
    runtime = w3.eth.get_code(CONTRACT, block_identifier=block_number)
    if Web3.to_hex(Web3.keccak(runtime)).lower() != EXPECTED_RUNTIME_HASH:
        raise ValueError('MVP contract runtime differs from the approved deployment')
    registry_code = w3.eth.get_code(OFFICIAL_REGISTRY, block_identifier=block_number)
    if not registry_code:
        raise ValueError('Official Agent ID registry has no code')

    contract = w3.eth.contract(address=CONTRACT, abi=contract_abi)
    registry = w3.eth.contract(address=OFFICIAL_REGISTRY, abi=registry_abi)
    configured_registry = _read(contract, 'agentIdRegistry', block_number)
    configured_constant = _read(contract, 'BSC_AGENT_ID_REGISTRY', block_number)
    configured_chain = _read(contract, 'BSC_MAINNET_CHAIN_ID', block_number)
    balance = _read(registry, 'balanceOf', block_number, participant)
    holder = _read(contract, 'isAgentIdHolder', block_number, participant)
    already_recorded = _read(
        contract, 'recorded', block_number, participant, plan.evidence_digest,
    )
    has_participated = _read(contract, 'hasParticipated', block_number, participant)
    receipt_count = _read(contract, 'receiptCount', block_number)
    unique_agent_count = _read(contract, 'uniqueAgentCount', block_number)
    if (
        Web3.to_checksum_address(configured_registry) != OFFICIAL_REGISTRY
        or Web3.to_checksum_address(configured_constant) != OFFICIAL_REGISTRY
        or configured_chain != CHAIN_ID
    ):
        raise ValueError('MVP contract configuration differs from the approved deployment')
    if type(balance) is not int or balance <= 0 or holder is not True:
        raise ValueError('Participant does not currently hold an Agent ID')
    if already_recorded is not False:
        raise ValueError('Participant already recorded this evidence digest')
    if (
        type(has_participated) is not bool
        or type(receipt_count) is not int or receipt_count < 0
        or type(unique_agent_count) is not int or unique_agent_count < 0
        or unique_agent_count > receipt_count
    ):
        raise ValueError('MVP contract counters are malformed')

    transaction = {
        'from': participant,
        'to': CONTRACT,
        'data': plan.calldata,
        'value': 0,
    }
    w3.eth.call(transaction, block_identifier=block_number)
    gas_estimate = w3.eth.estimate_gas(transaction)
    if type(gas_estimate) is not int or gas_estimate <= 0 or gas_estimate > MAX_GAS_ESTIMATE:
        raise ValueError('Interaction gas estimate is outside the reviewed bound')
    proposed_gas_limit = (gas_estimate * 120 + 99) // 100
    if w3.eth.get_block(block_number)['hash'] != finalized['hash']:
        raise ValueError('Finalized observation changed')

    return {
        'status': 'MVP_INTERACTION_READY',
        'assurance': 'RPC_FINALIZED_READ',
        'chain_id': CHAIN_ID,
        'participant': participant,
        'contract_address': CONTRACT,
        'agent_id_registry': OFFICIAL_REGISTRY,
        'agent_id_balance': balance,
        'eligible_at_observation': True,
        'evidence_digest': plan.evidence_digest,
        'assessment_digest': plan.assessment_digest,
        'function_signature': plan.function_signature,
        'calldata': plan.calldata,
        'native_value_wei': 0,
        'finalized_block_number': block_number,
        'finalized_block_hash': Web3.to_hex(finalized['hash']),
        'runtime_code_keccak256': EXPECTED_RUNTIME_HASH,
        'already_recorded': False,
        'has_participated': has_participated,
        'expected_first_interaction': not has_participated,
        'current_receipt_count': receipt_count,
        'current_unique_agent_count': unique_agent_count,
        'gas_estimate': gas_estimate,
        'proposed_gas_limit': proposed_gas_limit,
        'unsigned_transaction': {
            'from': participant,
            'to': CONTRACT,
            'data': plan.calldata,
            'value': '0x0',
            'chainId': '0x38',
            'gas': hex(proposed_gas_limit),
        },
        'transactions_sent': 0,
        'limitations': (
            'Eligibility and simulation are provider-trusted observations; the wallet must '
            'recheck chain, account, value, calldata and gas before explicit confirmation'
        ),
    }
