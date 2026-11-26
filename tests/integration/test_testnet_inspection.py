import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from veriabstain_eval.testnet_deployment import PINNED
from web3 import Web3

spec = importlib.util.spec_from_file_location("inspect_testnet", Path(__file__).resolve().parents[2] / "tools/inspect_testnet.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture(autouse=True)
def simulated_runtime_pin(monkeypatch):
    monkeypatch.setattr(module, "REVIEWED_COMMERCE_CODE_HASH", Web3.to_hex(Web3.keccak(b"fixture code")))


def fixture():
    w3 = MagicMock()
    addresses = PINNED
    w3.eth.chain_id = 97
    w3.eth.get_block.return_value = {"number": 10, "hash": bytes.fromhex("ab" * 32), "timestamp": 1000}
    w3.eth.get_code.return_value = b"fixture code"
    contracts = {}
    for key in ("commerce_proxy", "router_proxy", "policy", "payment_token"):
        contracts[getattr(addresses, key)] = MagicMock()
    commerce, router, policy = (contracts[getattr(addresses, k)] for k in ("commerce_proxy", "router_proxy", "policy"))
    commerce.functions.paymentToken.return_value.call.return_value = addresses.payment_token
    commerce.functions.paused.return_value.call.return_value = False
    router.functions.commerce.return_value.call.return_value = addresses.commerce_proxy
    router.functions.policyWhitelist.return_value.call.return_value = True
    router.functions.paused.return_value.call.return_value = False
    policy.functions.commerce.return_value.call.return_value = addresses.commerce_proxy
    policy.functions.router.return_value.call.return_value = addresses.router_proxy
    policy.functions.disputeWindow.return_value.call.return_value = 900
    w3.eth.contract.side_effect = lambda address, abi: contracts[address]
    w3.eth.get_storage_at.side_effect = lambda address, slot, block_identifier: b"\0" * 12 + bytes.fromhex(
        (addresses.commerce_impl if address == addresses.commerce_proxy else addresses.router_impl)[2:])
    return w3


def test_inspection_uses_pinned_reads_and_manifest_implementations():
    w3 = fixture()
    result = module.inspect(w3)
    assert result["compatible_read_surface"] is True
    assert result["transactions"] == 0
    for call in w3.eth.get_code.call_args_list:
        assert call.kwargs["block_identifier"] == 10
    assert result["assurance"] == "RPC_FINALIZED_READ"


def test_inspection_detects_proxy_upgrade():
    w3 = fixture()
    w3.eth.get_storage_at.side_effect = None
    w3.eth.get_storage_at.return_value = b"\0" * 12 + bytes.fromhex("99" * 20)
    assert module.inspect(w3)["compatible_read_surface"] is False


def test_inspection_rejects_other_chains_before_contract_reads():
    w3 = fixture()
    w3.eth.chain_id = 56
    with pytest.raises(ValueError, match="97"):
        module.inspect(w3)
    w3.eth.get_code.assert_not_called()


def test_inspection_rejects_reorged_snapshot():
    w3 = fixture()
    first = w3.eth.get_block.return_value
    w3.eth.get_block.side_effect = [first, {**first, "hash": bytes.fromhex("cd" * 32)}]
    with pytest.raises(ValueError, match="block changed"):
        module.inspect(w3)
