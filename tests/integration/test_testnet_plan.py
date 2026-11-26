"""Actual SDK ABI/signature logic with injected reads; no chain writes."""

import copy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from bnbagent.core.abis import load_abi
from bnbagent.erc8183.negotiation import NegotiationHandler, build_job_description
from veriabstain_eval.testnet_plan import (
    IMPLEMENTATION_SLOT, PINNED, TestnetJobSpec as JobSpec, build_testnet_plan,
)
import veriabstain_eval.testnet_plan as planner

NOW = 1_795_171_733
CLIENT = "0x" + "11" * 20
TX_HASH = "0x" + "ab" * 32
BLOCK_HASH = bytes.fromhex("cd" * 32)
CREATION_HASH = bytes.fromhex("ef" * 32)


@pytest.fixture(autouse=True)
def simulated_runtime_pin(monkeypatch):
    # Unit RPC returns synthetic code, not the production-reviewed bytecode.
    monkeypatch.setattr(planner, "REVIEWED_COMMERCE_CODE_HASH", Web3.to_hex(Web3.keccak(b"fixture code")))


def make_fixture():
    account = Account.create()
    signer = SimpleNamespace(address=account.address, sign_message=lambda message: {
        "signature": account.sign_message(encode_defunct(text=message)).signature,
    })
    handler = NegotiationHandler(service_price="1000", currency=PINNED.payment_token,
                                 wallet_provider=signer, chain_id=97, verifying_contract=PINNED.commerce_proxy,
                                 quote_ttl_seconds=900)
    with patch("bnbagent.erc8183.negotiation.time.time", return_value=NOW - 60):
        quote = handler.negotiate({"task_description": "Analyze public testnet allowance",
                                   "terms": {"deliverables": "public JSON analysis", "quality_standards": "accurate"}}).to_dict()
    spec = JobSpec(chain_id=97, client=CLIENT, provider=account.address,
                          commerce=PINNED.commerce_proxy, router=PINNED.router_proxy,
                          policy=PINNED.policy, payment_token=PINNED.payment_token,
                          budget=1000, expired_at=NOW + 3600, quote=quote)
    description = build_job_description(quote)
    w3 = MagicMock()
    w3.eth.chain_id = 97
    w3.eth.get_block.side_effect = lambda block: {
        "number": 500 if block in ("finalized", 500) else 499,
        "hash": BLOCK_HASH if block in ("finalized", 500) else CREATION_HASH,
        "timestamp": NOW - 5,
    }
    w3.eth.get_code.side_effect = lambda address, block_identifier: b"" if address in (spec.provider, spec.client) else b"fixture code"
    w3.eth.get_storage_at.side_effect = lambda address, slot, block_identifier: b"\0" * 12 + bytes.fromhex(
        (PINNED.commerce_impl if address == PINNED.commerce_proxy else PINNED.router_impl)[2:])
    w3.eth.get_balance.return_value = 10**18
    w3.eth.call.return_value = b""
    contracts = {}
    for address, abi in ((spec.commerce, "AgenticCommerce.json"), (spec.router, "EvaluatorRouter.json"),
                         (spec.policy, "OptimisticPolicy.json"), (spec.payment_token, "ERC20.json")):
        real = Web3().eth.contract(address=address, abi=load_abi(abi))
        contract = MagicMock()
        contract.address = address
        contract.encode_abi.side_effect = real.encode_abi
        contract.events = real.events
        contracts[address] = contract
    w3.eth.contract.side_effect = lambda address, abi: contracts[address]
    commerce, router, policy, token = (contracts[a] for a in (spec.commerce, spec.router, spec.policy, spec.payment_token))
    for contract in (commerce, router):
        contract.functions.paused.return_value.call.return_value = False
    router.functions.policyWhitelist.return_value.call.return_value = True
    router.functions.commerce.return_value.call.return_value = spec.commerce
    policy.functions.commerce.return_value.call.return_value = spec.commerce
    policy.functions.router.return_value.call.return_value = spec.router
    commerce.functions.paymentToken.return_value.call.return_value = spec.payment_token
    commerce.functions.isPaymentTokenSupported.return_value.call.return_value = True
    commerce.functions.MAX_EXPIRY_DURATION.return_value.call.return_value = 86400
    policy.functions.disputeWindow.return_value.call.return_value = 900
    commerce.functions.jobPaymentToken.return_value.call.return_value = spec.payment_token
    router.functions.jobPolicy.return_value.call.return_value = spec.policy
    commerce.functions.jobHasBudget.return_value.call.return_value = True
    commerce.functions.getJob.return_value.call.return_value = (
        7, spec.client, spec.provider, spec.router, description, spec.budget,
        spec.expired_at, 0, spec.router, 0, b"\0" * 32,
    )
    token.functions.balanceOf.return_value.call.return_value = 1000
    token.functions.allowance.return_value.call.return_value = 1000
    create_data = commerce.encode_abi("createJob", args=[spec.provider, spec.router, spec.expired_at, description, spec.router])
    w3.eth.get_transaction.return_value = {"from": spec.client, "to": spec.commerce,
                                         "value": 0, "input": create_data}
    # Encode a real JobCreated event using the pinned upstream ABI.
    event = next(e for e in load_abi("AgenticCommerce.json") if e.get("name") == "JobCreated")
    values = {"jobId": 7, "client": spec.client, "provider": spec.provider,
              "evaluator": spec.router, "expiredAt": spec.expired_at, "hook": spec.router}
    signature = "JobCreated(" + ",".join(i["type"] for i in event["inputs"]) + ")"
    indexed = [i for i in event["inputs"] if i["indexed"]]
    plain = [i for i in event["inputs"] if not i["indexed"]]
    log = {"address": spec.commerce, "topics": [Web3.keccak(text=signature)] + [encode([i["type"]], [values[i["name"]]]) for i in indexed],
           "data": encode([i["type"] for i in plain], [values[i["name"]] for i in plain]),
           "logIndex": 0, "transactionIndex": 0, "transactionHash": bytes.fromhex(TX_HASH[2:]),
           "blockNumber": 499, "blockHash": CREATION_HASH}
    w3.eth.get_transaction_receipt.return_value = {"status": 1, "blockNumber": 499,
                                                  "blockHash": CREATION_HASH, "transactionHash": bytes.fromhex(TX_HASH[2:]), "logs": [log]}
    return w3, spec, contracts


@pytest.mark.parametrize("stage", ["CREATE_JOB", "REGISTER_JOB", "SET_BUDGET", "APPROVE_EXACT", "RESET_APPROVAL", "FUND_JOB", "FUNDED_CONFIRMED"])
def test_one_unsigned_stage_with_real_signature_and_abi(stage):
    w3, spec, contracts = make_fixture()
    commerce, router, token = (contracts[a] for a in (spec.commerce, spec.router, spec.payment_token))
    if stage == "REGISTER_JOB":
        router.functions.jobPolicy.return_value.call.return_value = "0x" + "00" * 20
    elif stage == "SET_BUDGET":
        commerce.functions.jobHasBudget.return_value.call.return_value = False
    elif stage in ("APPROVE_EXACT", "RESET_APPROVAL"):
        token.functions.allowance.return_value.call.return_value = 0 if stage == "APPROVE_EXACT" else 999999
    elif stage == "FUNDED_CONFIRMED":
        raw = list(commerce.functions.getJob.return_value.call.return_value)
        raw[7] = 1
        commerce.functions.getJob.return_value.call.return_value = tuple(raw)
    result = build_testnet_plan(w3, spec, now=NOW, creation_tx_hash=None if stage == "CREATE_JOB" else TX_HASH)
    assert result["stage"] == stage
    assert result["transactions_sent"] == 0
    assert w3.eth.send_raw_transaction.call_count == w3.eth.send_transaction.call_count == 0
    if stage == "FUNDED_CONFIRMED":
        assert result["next_transaction"] is None
    else:
        tx = result["next_transaction"]
        assert tx["chainId"] == 97 and tx["from"] == spec.client and tx["value"] == 0
        assert result["requires_manual_confirmation"] is True
        if stage in ("APPROVE_EXACT", "RESET_APPROVAL"):
            real = Web3().eth.contract(address=spec.payment_token, abi=load_abi("ERC20.json"))
            _, arguments = real.decode_function_input(tx["data"])
            assert list(arguments.values()) == [spec.commerce, 1000 if stage == "APPROVE_EXACT" else 0]


@pytest.mark.parametrize("mutation", ["mainnet", "drift", "code_drift", "no_gas", "bad_quote", "quote_budget", "expired_quote", "wrong_route", "too_short", "no_tokens", "receipt_sender", "receipt_data", "receipt_unfinalized", "receipt_reorg", "failed_creation", "job_budget", "job_provider"])
def test_invalid_conditions_block_or_reject_without_writes(mutation):
    w3, spec, contracts = make_fixture()
    commerce, router, token = (contracts[a] for a in (spec.commerce, spec.router, spec.payment_token))
    creation = TX_HASH
    if mutation == "mainnet":
        w3.eth.chain_id = 56
    elif mutation == "drift":
        w3.eth.get_storage_at.side_effect = None
        w3.eth.get_storage_at.return_value = b"\0" * 12 + bytes.fromhex("99" * 20)
    elif mutation == "no_gas":
        w3.eth.get_balance.return_value = 0
    elif mutation == "code_drift":
        w3.eth.get_code.side_effect = None
        w3.eth.get_code.return_value = b"unreviewed code"
    elif mutation == "bad_quote":
        spec.quote["provider_sig"] = "0x" + "00" * 65
    elif mutation == "quote_budget":
        spec = spec.model_copy(update={"budget": 1001})
    elif mutation == "expired_quote":
        spec = spec.model_copy(update={"quote": copy.deepcopy(spec.quote)})
        spec.quote["response"]["quote_expires_at"] = NOW - 1
    elif mutation == "wrong_route":
        router.functions.commerce.return_value.call.return_value = "0x" + "99" * 20
    elif mutation == "too_short":
        spec = spec.model_copy(update={"expired_at": NOW + 899})
    elif mutation == "no_tokens":
        token.functions.balanceOf.return_value.call.return_value = 0
    elif mutation == "receipt_sender":
        w3.eth.get_transaction.return_value["from"] = "0x" + "99" * 20
    elif mutation == "receipt_data":
        w3.eth.get_transaction.return_value["input"] = "0x00"
    elif mutation == "receipt_unfinalized":
        w3.eth.get_transaction_receipt.return_value["blockNumber"] = 501
    elif mutation == "receipt_reorg":
        w3.eth.get_transaction_receipt.return_value["blockHash"] = bytes.fromhex("99" * 32)
    elif mutation == "failed_creation":
        w3.eth.get_transaction_receipt.return_value["status"] = 0
    else:
        raw = list(commerce.functions.getJob.return_value.call.return_value)
        raw[5 if mutation == "job_budget" else 2] = 999999 if mutation == "job_budget" else "0x" + "99" * 20
        commerce.functions.getJob.return_value.call.return_value = tuple(raw)
    if mutation in ("drift", "code_drift", "no_gas", "no_tokens"):
        result = build_testnet_plan(w3, spec, now=NOW, creation_tx_hash=creation)
        assert result["status"] == "BLOCKED" and result["next_transaction"] is None
    else:
        with pytest.raises((ValueError, TypeError)):
            build_testnet_plan(w3, spec, now=NOW, creation_tx_hash=creation)
    w3.eth.send_transaction.assert_not_called()
    w3.eth.send_raw_transaction.assert_not_called()


def test_implementation_slot_is_derived_not_transcribed():
    assert IMPLEMENTATION_SLOT == int.from_bytes(Web3.keccak(text="eip1967.proxy.implementation"), "big") - 1


def test_draft_is_rejected_if_pinned_snapshot_changes_during_simulation():
    w3, spec, _ = make_fixture()
    original_block = w3.eth.get_block.side_effect
    simulated = []
    w3.eth.call.side_effect = lambda *args, **kwargs: simulated.append(True) or b""
    def block_after_simulation(block):
        result = original_block(block)
        return {**result, "hash": bytes.fromhex("99" * 32)} if simulated else result
    w3.eth.get_block.side_effect = block_after_simulation
    with pytest.raises(ValueError, match="block changed"):
        build_testnet_plan(w3, spec, now=NOW)


@pytest.mark.parametrize("chain", [56, 97.0, "97", True])
def test_input_chain_is_strictly_testnet(chain):
    _, spec, _ = make_fixture()
    data = spec.model_dump()
    data["chain_id"] = chain
    with pytest.raises(ValueError):
        JobSpec.model_validate(data)
