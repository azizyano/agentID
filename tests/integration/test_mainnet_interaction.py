import copy
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from web3 import Web3

import veriabstain_eval.mainnet_interaction as interaction
from veriabstain_eval.mainnet_interaction import (
    CHAIN_ID,
    CONTRACT,
    OFFICIAL_REGISTRY,
    prepare_interaction,
)

ROOT = Path(__file__).resolve().parents[2]
PARTICIPANT = Web3.to_checksum_address('0x' + '34' * 20)


def receipt_plan():
    return json.loads(
        (ROOT / 'artifacts/mvp/receipt-example/receipt-plan.json').read_text(encoding='utf-8')
    )


def fixture(monkeypatch):
    w3 = MagicMock()
    w3.eth.chain_id = CHAIN_ID
    finalized = {'number': 123, 'hash': bytes.fromhex('ab' * 32)}
    w3.eth.get_block.side_effect = lambda key: finalized
    runtime = b'approved-runtime'
    monkeypatch.setattr(interaction, 'EXPECTED_RUNTIME_HASH', Web3.to_hex(Web3.keccak(runtime)))
    w3.eth.get_code.side_effect = lambda address, **_: runtime if address == CONTRACT else b'registry'

    contract = MagicMock()
    contract.functions.agentIdRegistry.return_value.call.return_value = OFFICIAL_REGISTRY
    contract.functions.BSC_AGENT_ID_REGISTRY.return_value.call.return_value = OFFICIAL_REGISTRY
    contract.functions.BSC_MAINNET_CHAIN_ID.return_value.call.return_value = CHAIN_ID
    contract.functions.isAgentIdHolder.return_value.call.return_value = True
    contract.functions.recorded.return_value.call.return_value = False
    contract.functions.hasParticipated.return_value.call.return_value = False
    contract.functions.receiptCount.return_value.call.return_value = 0
    contract.functions.uniqueAgentCount.return_value.call.return_value = 0
    registry = MagicMock()
    registry.functions.balanceOf.return_value.call.return_value = 1
    w3.eth.contract.side_effect = lambda address, **_: contract if address == CONTRACT else registry
    w3.eth.call.return_value = b''
    w3.eth.estimate_gas.return_value = 100_000
    return w3, contract, registry, finalized


def test_eligible_holder_gets_exact_unsigned_zero_value_interaction(monkeypatch):
    w3, _, _, _ = fixture(monkeypatch)
    plan = receipt_plan()
    result = prepare_interaction(w3, PARTICIPANT, plan, [], [])
    assert result['status'] == 'MVP_INTERACTION_READY'
    assert result['participant'] == PARTICIPANT
    assert result['contract_address'] == CONTRACT
    assert result['calldata'] == plan['calldata']
    assert result['native_value_wei'] == 0
    assert result['expected_first_interaction'] is True
    assert result['proposed_gas_limit'] == 120_000
    assert result['unsigned_transaction'] == {
        'from': PARTICIPANT,
        'to': CONTRACT,
        'data': plan['calldata'],
        'value': '0x0',
        'chainId': '0x38',
        'gas': hex(120_000),
    }
    assert result['transactions_sent'] == 0
    w3.eth.send_transaction.assert_not_called()


def test_existing_participant_is_not_miscounted_as_first(monkeypatch):
    w3, contract, _, _ = fixture(monkeypatch)
    contract.functions.hasParticipated.return_value.call.return_value = True
    contract.functions.receiptCount.return_value.call.return_value = 9
    contract.functions.uniqueAgentCount.return_value.call.return_value = 7
    result = prepare_interaction(w3, PARTICIPANT, receipt_plan(), [], [])
    assert result['expected_first_interaction'] is False
    assert result['current_receipt_count'] == 9
    assert result['current_unique_agent_count'] == 7


@pytest.mark.parametrize('change', [
    'chain', 'address', 'runtime', 'registry_code', 'configuration', 'balance',
    'holder', 'duplicate', 'counters', 'simulation', 'gas', 'reorg',
])
def test_any_eligibility_code_state_or_simulation_mismatch_fails_closed(monkeypatch, change):
    w3, contract, registry, finalized = fixture(monkeypatch)
    participant = PARTICIPANT
    if change == 'chain':
        w3.eth.chain_id = 97
    elif change == 'address':
        participant = 'not-an-address'
    elif change == 'runtime':
        monkeypatch.setattr(interaction, 'EXPECTED_RUNTIME_HASH', '0x' + '00' * 32)
    elif change == 'registry_code':
        w3.eth.get_code.side_effect = lambda address, **_: b'approved-runtime' if address == CONTRACT else b''
        monkeypatch.setattr(
            interaction, 'EXPECTED_RUNTIME_HASH', Web3.to_hex(Web3.keccak(b'approved-runtime')),
        )
    elif change == 'configuration':
        contract.functions.BSC_MAINNET_CHAIN_ID.return_value.call.return_value = 97
    elif change == 'balance':
        registry.functions.balanceOf.return_value.call.return_value = 0
    elif change == 'holder':
        contract.functions.isAgentIdHolder.return_value.call.return_value = False
    elif change == 'duplicate':
        contract.functions.recorded.return_value.call.return_value = True
    elif change == 'counters':
        contract.functions.uniqueAgentCount.return_value.call.return_value = 1
    elif change == 'simulation':
        w3.eth.call.side_effect = ValueError('revert')
    elif change == 'gas':
        w3.eth.estimate_gas.return_value = 300_001
    else:
        changed = copy.deepcopy(finalized)
        changed['hash'] = bytes.fromhex('cd' * 32)
        w3.eth.get_block.side_effect = lambda key: finalized if key == 'finalized' else changed
    with pytest.raises(ValueError):
        prepare_interaction(w3, participant, receipt_plan(), [], [])


def test_tampered_receipt_plan_is_rejected_before_contract_reads(monkeypatch):
    w3, _, _, _ = fixture(monkeypatch)
    plan = receipt_plan()
    plan['assessment_digest'] = '0x' + '00' * 32
    with pytest.raises(ValueError, match='does not match'):
        prepare_interaction(w3, PARTICIPANT, plan, [], [])
    w3.eth.get_block.assert_not_called()
