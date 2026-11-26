import copy
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from hexbytes import HexBytes
from web3 import Web3

from veriabstain_eval.mainnet_deployment import (
    EXPECTED_DEPLOYER,
    OFFICIAL_REGISTRY,
    confirm_deployment,
)
from veriabstain_eval.mainnet_preflight import load_deployment_package

ROOT = Path(__file__).resolve().parents[2]
PLAN = load_deployment_package(ROOT / 'artifacts/mvp/deployment-package')[0]
ABI = json.loads((ROOT / 'artifacts/mvp/contract-build.json').read_text())['contracts']['VeriAbstainEvidenceRegistry']['abi']
TX_HASH = '0x' + '12' * 32
CONTRACT = Web3.to_checksum_address('0x' + '34' * 20)


def fixture():
    w3 = MagicMock()
    w3.eth.chain_id = 56
    runtime = b'exact-runtime'
    plan = copy.deepcopy(PLAN)
    plan['expected_runtime_keccak256'] = Web3.to_hex(Web3.keccak(runtime))
    transaction = {'from': EXPECTED_DEPLOYER, 'to': None, 'value': 0,
                   'input': HexBytes(plan['deployment_data'])}
    receipt = {'status': 1, 'to': None, 'contractAddress': CONTRACT,
               'blockNumber': 100, 'blockHash': HexBytes('0x' + 'ab' * 32),
               'logs': [], 'gasUsed': 300_000, 'effectiveGasPrice': 50_000_000}
    final = {'number': 102, 'hash': HexBytes('0x' + 'cd' * 32)}
    deployment_block = {'number': 100, 'hash': receipt['blockHash']}
    w3.eth.get_transaction.return_value = transaction
    w3.eth.get_transaction_receipt.return_value = receipt
    w3.eth.get_block.side_effect = lambda key: final if key in ('finalized', 102) else deployment_block
    w3.eth.get_code.return_value = runtime
    contract = MagicMock()
    for name, value in (
        ('agentIdRegistry', OFFICIAL_REGISTRY), ('BSC_AGENT_ID_REGISTRY', OFFICIAL_REGISTRY),
        ('BSC_MAINNET_CHAIN_ID', 56), ('receiptCount', 0), ('uniqueAgentCount', 0),
    ):
        getattr(contract.functions, name).return_value.call.return_value = value
    w3.eth.contract.return_value = contract
    return w3, plan, transaction, receipt, contract


def test_exact_finalized_deployment_is_confirmed_without_sending():
    w3, plan, _, _, _ = fixture()
    result = confirm_deployment(w3, TX_HASH, plan, ABI)
    assert result['status'] == 'MVP_MAINNET_DEPLOYMENT_CONFIRMED'
    assert result['contract_address'] == CONTRACT
    assert result['agent_id_registry'] == OFFICIAL_REGISTRY
    assert result['receipt_count'] == result['unique_agent_count'] == 0
    assert result['actual_gas_cost_wei'] == 15_000_000_000_000
    assert result['transactions_sent_by_verifier'] == 0
    w3.eth.send_transaction.assert_not_called()


@pytest.mark.parametrize('change', [
    'chain', 'status', 'sender', 'value', 'input', 'recipient', 'logs',
    'unfinalized', 'reorg', 'runtime', 'registry', 'count',
])
def test_any_deployment_or_state_mismatch_fails_closed(change):
    w3, plan, transaction, receipt, contract = fixture()
    if change == 'chain': w3.eth.chain_id = 97
    elif change == 'status': receipt['status'] = 0
    elif change == 'sender': transaction['from'] = '0x' + '11' * 20
    elif change == 'value': transaction['value'] = 1
    elif change == 'input': transaction['input'] = HexBytes('0x00')
    elif change == 'recipient': transaction['to'] = '0x' + '11' * 20
    elif change == 'logs': receipt['logs'] = [{'unexpected': True}]
    elif change == 'unfinalized': receipt['blockNumber'] = 103
    elif change == 'reorg': receipt['blockHash'] = HexBytes('0x' + 'ef' * 32)
    elif change == 'runtime': plan['expected_runtime_keccak256'] = '0x' + '00' * 32
    elif change == 'registry': contract.functions.agentIdRegistry.return_value.call.return_value = '0x' + '11' * 20
    else: contract.functions.receiptCount.return_value.call.return_value = 1
    with pytest.raises(ValueError):
        confirm_deployment(w3, TX_HASH, plan, ABI)


@pytest.mark.parametrize('value', ['', '0x12', True, None])
def test_invalid_transaction_hash_is_rejected(value):
    w3, plan, _, _, _ = fixture()
    with pytest.raises(ValueError):
        confirm_deployment(w3, value, plan, ABI)
