import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from web3 import Web3

from veriabstain_eval.mainnet_preflight import (
    OFFICIAL_AGENT_ID_REGISTRY,
    load_deployment_package,
    preflight_mainnet,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'artifacts/mvp/deployment-package'
DEPLOYER = '0xb16b77C16773DEF8fA279A1228Eba9308eCD7841'


def package_plan():
    return load_deployment_package(PACKAGE)[0]


def fake_w3(*, balance=10**18, holder_balance=0, chain_id=56):
    plan = package_plan()
    w3 = MagicMock()
    w3.eth.chain_id = chain_id
    block = {'number': 123, 'hash': bytes.fromhex('ab' * 32)}
    w3.eth.get_block.side_effect = lambda key: block
    w3.eth.get_code.return_value = b'agent-id-code'
    registry = MagicMock()
    registry.functions.name.return_value.call.return_value = 'SPACE ID Agent ID'
    registry.functions.symbol.return_value.call.return_value = 'AI'
    registry.functions.balanceOf.return_value.call.return_value = holder_balance
    w3.eth.contract.return_value = registry
    # eth_call contract creation returns the linked runtime bytes whose hash is pinned.
    # MagicMock cannot invert keccak, so return a marker and align the expected plan hash.
    runtime = b'linked-runtime'
    adjusted = copy.deepcopy(plan)
    adjusted['expected_runtime_keccak256'] = Web3.to_hex(Web3.keccak(runtime))
    w3.eth.call.return_value = runtime
    w3.eth.estimate_gas.return_value = 100_000
    w3.eth.gas_price = 3_000_000_000
    w3.eth.get_balance.return_value = balance
    return w3, adjusted


def test_funded_preflight_is_read_only_and_agent_id_is_not_a_deployer_requirement():
    w3, plan = fake_w3(balance=10**18, holder_balance=0)
    result = preflight_mainnet(w3, DEPLOYER, plan)
    assert result['status'] == 'MAINNET_PREFLIGHT_READY'
    assert result['balance_sufficient'] is True
    assert result['deployer_holds_agent_id'] is False
    assert result['proposed_gas_limit'] == 120_000
    assert result['maximum_estimated_cost_wei'] == 360_000_000_000_000
    assert result['transactions_sent'] == 0
    w3.eth.send_transaction.assert_not_called()


def test_unfunded_preflight_reports_need_without_sending():
    w3, plan = fake_w3(balance=1)
    result = preflight_mainnet(w3, DEPLOYER, plan)
    assert result['status'] == 'MAINNET_PREFLIGHT_NEEDS_BNB'
    assert result['balance_sufficient'] is False
    assert result['transactions_sent'] == 0


@pytest.mark.parametrize('change', ['chain', 'identity', 'runtime'])
def test_wrong_chain_registry_identity_or_runtime_fails_closed(change):
    w3, plan = fake_w3()
    if change == 'chain':
        w3.eth.chain_id = 97
    elif change == 'identity':
        w3.eth.contract.return_value.functions.name.return_value.call.return_value = 'Other'
    else:
        plan['expected_runtime_keccak256'] = '0x' + '00' * 32
    with pytest.raises(ValueError):
        preflight_mainnet(w3, DEPLOYER, plan)


def test_package_digest_tampering_is_rejected(tmp_path):
    copied = tmp_path / 'package'
    copied.mkdir()
    for name in ('deployment-plan.json', 'verification-manifest.json'):
        (copied / name).write_bytes((PACKAGE / name).read_bytes())
    plan = json.loads((copied / 'deployment-plan.json').read_text())
    plan['native_value_wei'] = 1
    (copied / 'deployment-plan.json').write_text(json.dumps(plan), encoding='utf-8')
    with pytest.raises(ValueError, match='digest mismatch'):
        load_deployment_package(copied)


def test_current_package_digest_is_exact():
    plan_bytes = (PACKAGE / 'deployment-plan.json').read_bytes()
    _, manifest = load_deployment_package(PACKAGE)
    assert hashlib.sha256(plan_bytes).hexdigest() == manifest['deployment_plan_sha256']
