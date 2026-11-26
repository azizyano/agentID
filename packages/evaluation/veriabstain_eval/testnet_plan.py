"""Testnet-only read preflight and single-stage unsigned ERC-8183 drafts.

No wallet, signing, broadcast, deployment, or mainnet path exists here. A draft
must be reviewed and signed externally by its explicitly configured client.
"""

import time
import copy
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from web3 import Web3
from web3.logs import DISCARD

from bnbagent.core.abis import load_abi
from bnbagent.erc8183.commerce import _decode_job
from bnbagent.erc8183.negotiation import NegotiationHandler, build_job_description
from bnbagent.erc8183.quote_verify import verify_quote_signature
from bnbagent.erc8183.types import JobStatus, ZERO_ADDRESS

from .dataset import REVISION
from .testnet_deployment import PINNED, REVIEWED_COMMERCE_CODE_HASH, SOURCE_REVISION

IMPLEMENTATION_SLOT = int.from_bytes(Web3.keccak(text="eip1967.proxy.implementation"), "big") - 1
UINT256_MAX = 2**256 - 1
ADDRESS_FIELDS = ("client", "provider", "commerce", "router", "policy", "payment_token")
TOKEN_ABI = [
    {"type": "function", "name": name, "stateMutability": "view",
     "inputs": [{"name": key, "type": "address"} for key in arguments],
     "outputs": [{"name": "", "type": "uint256"}]}
    for name, arguments in (("balanceOf", ("owner",)), ("allowance", ("owner", "spender")))
] + [{"type": "function", "name": "approve", "stateMutability": "nonpayable",
      "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
      "outputs": [{"name": "", "type": "bool"}]}]


class TestnetJobSpec(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    chain_id: Literal[97]
    client: str
    provider: str
    commerce: str
    router: str
    policy: str
    payment_token: str
    budget: Annotated[int, Field(gt=0, le=UINT256_MAX)]
    expired_at: Annotated[int, Field(gt=0, le=UINT256_MAX)]
    quote: dict

    @field_validator("chain_id", mode="before")
    @classmethod
    def exact_chain(cls, value):
        if type(value) is not int or value != 97:
            raise ValueError("Chain ID must be the integer 97")
        return value

    @field_validator(*ADDRESS_FIELDS)
    @classmethod
    def valid_address(cls, value):
        if not Web3.is_address(value) or value.lower() == ZERO_ADDRESS:
            raise ValueError("A nonzero public address is required")
        return Web3.to_checksum_address(value)

    @model_validator(mode="after")
    def pinned_deployments(self):
        expected = {"commerce": PINNED.commerce_proxy, "router": PINNED.router_proxy,
                    "policy": PINNED.policy, "payment_token": PINNED.payment_token}
        if any(getattr(self, field) != value for field, value in expected.items()):
            raise ValueError("Only the pinned chain-97 deployment and default payment token are supported")
        if self.client == self.provider:
            raise ValueError("Use distinct, explicitly authorized client and provider addresses")
        return self


def _integer(value, label, minimum=0):
    if type(value) is not int or not minimum <= value <= UINT256_MAX:
        raise ValueError(f"Invalid {label}")
    return value


def _address(value):
    if not Web3.is_address(value):
        raise ValueError("Invalid address in chain response")
    return Web3.to_checksum_address(value)


def _hash(value):
    if isinstance(value, str):
        import re
        if re.fullmatch(r"0x[0-9a-fA-F]{64}", value) is None:
            raise ValueError("Invalid block or transaction hash")
        raw = bytes.fromhex(value[2:])
    elif isinstance(value, bytes):
        raw = value
    else:
        raise ValueError("Invalid block or transaction hash")
    if len(raw) != 32:
        raise ValueError("Invalid block or transaction hash")
    return Web3.to_hex(raw)


def _read(contract, name, arguments, block):
    return getattr(contract.functions, name)(*arguments).call(block_identifier=block)


def _check_snapshot(w3, report):
    if _hash(w3.eth.get_block(report["block_number"])["hash"]) != report["block_hash"]:
        raise ValueError("Pinned finalized block changed during preflight")
    return report


def _unsigned(w3, spec, report, contract, name, arguments, stage):
    transaction = {"chainId": 97, "from": spec.client, "to": contract.address,
                   "value": 0, "data": contract.encode_abi(name, args=arguments)}
    # Read-only EVM simulation; does not sign, send, or reserve a nonce.
    w3.eth.call(transaction, block_identifier=report["block_number"])
    _check_snapshot(w3, report)
    return {**report, "status": "UNSIGNED_PLAN", "stage": stage,
            "next_transaction": transaction, "requires_manual_confirmation": True}


def _quote_description(w3, spec, block, now):
    quote = spec.quote
    response = quote.get("response")
    if (not isinstance(response, dict) or response.get("accepted") is not True
            or not isinstance(response.get("terms"), dict)):
        raise ValueError("An accepted signed provider quote is required")
    terms = response["terms"]
    price = terms.get("price")
    if type(price) is int:
        parsed_price = _integer(price, "signed quote price")
    elif isinstance(price, str) and price.isascii() and price.isdecimal() and str(int(price)) == price:
        parsed_price = int(price)
    else:
        raise ValueError("Signed quote price must be an exact atomic-unit integer")
    if parsed_price != spec.budget or _address(terms.get("currency")) != spec.payment_token:
        raise ValueError("Signed quote price or currency does not match original budget")
    if type(quote.get("chain_id")) is not int or quote["chain_id"] != 97:
        raise ValueError("Signed quote chain must be 97")
    verdict = verify_quote_signature(envelope=quote, provider=spec.provider, w3=w3,
                                     expected_verifying_contract=spec.commerce, block_number=block)
    if not verdict.valid:
        raise ValueError("Provider quote signature or signed content is invalid")
    description = build_job_description(quote)
    import json
    content = json.loads(description)
    negotiated = _integer(content.get("negotiated_at"), "quote negotiation time")
    expires = _integer(content.get("quote_expires_at"), "quote expiry")
    if not (negotiated <= now < expires and 0 < expires - negotiated <= NegotiationHandler.MAX_QUOTE_TTL_SECONDS):
        raise ValueError("Provider quote is expired, future-dated, or has an unsupported lifetime")
    return description, expires


def _confirmed_job_id(w3, spec, commerce, receipt_hash, create_data, finalized_block):
    receipt_hash = _hash(receipt_hash)
    receipt = w3.eth.get_transaction_receipt(receipt_hash)
    transaction = w3.eth.get_transaction(receipt_hash)
    block_number = _integer(receipt.get("blockNumber"), "creation block", 1)
    if (type(receipt.get("status")) is not int or receipt["status"] != 1 or block_number > finalized_block
            or _hash(receipt.get("transactionHash")) != receipt_hash
            or _hash(w3.eth.get_block(block_number)["hash"]) != _hash(receipt.get("blockHash"))):
        raise ValueError("Creation transaction is failed, unfinalized, or inconsistent")
    data = transaction.get("input", transaction.get("data"))
    data = data.lower() if isinstance(data, str) else Web3.to_hex(data)
    if (_address(transaction.get("from")) != spec.client
            or _address(transaction.get("to")) != spec.commerce
            or _integer(transaction.get("value"), "creation native value") != 0
            or data != create_data.lower()):
        raise ValueError("Confirmed creation transaction does not match this exact job intent")
    logs = commerce.events.JobCreated().process_receipt(receipt, errors=DISCARD)
    logs = [log for log in logs if _address(log["address"]) == spec.commerce]
    if len(logs) != 1:
        raise ValueError("Creation receipt must contain exactly one matching JobCreated event")
    event = logs[0]["args"]
    if (any(_address(event[field]) != expected for field, expected in (
            ("client", spec.client), ("provider", spec.provider),
            ("evaluator", spec.router), ("hook", spec.router)))
            or event["expiredAt"] != spec.expired_at):
        raise ValueError("Creation event fields do not match original intent")
    return _integer(event["jobId"], "created job ID", 1)


def build_testnet_plan(w3, spec, *, creation_tx_hash=None, now=None):
    """Return one draft for the next stage, or a blocker; never execute writes.

    All storage/code/call reads use one provider-selected finalized block.
    Provider trust is explicit. Any source implementation drift blocks drafts.
    """
    spec = TestnetJobSpec.model_validate(copy.deepcopy(spec.model_dump() if isinstance(spec, TestnetJobSpec) else spec))
    now = _integer(int(time.time()) if now is None else now, "current time", 1)
    if type(w3.eth.chain_id) is not int or w3.eth.chain_id != 97:
        raise ValueError("RPC must serve BSC testnet chain 97")
    block = w3.eth.get_block("finalized")
    number = _integer(block.get("number"), "finalized block number", 1)
    timestamp = _integer(block.get("timestamp"), "finalized block timestamp", 1)
    block_hash = _hash(block.get("hash"))
    if not 0 <= now - timestamp <= 120:
        raise ValueError("Finalized state is stale or future-dated")
    report = {"mode": "UNSIGNED_TESTNET_PREFLIGHT", "sdk_revision": REVISION,
              "reviewed_contract_source_revision": SOURCE_REVISION,
              "chain_id": 97, "block_number": number, "block_hash": block_hash,
              "block_timestamp": timestamp, "assurance": "RPC_FINALIZED_READ",
              "transactions_sent": 0, "next_transaction": None,
              "status": "BLOCKED", "stage": "PREFLIGHT", "blockers": [],
              "code_hashes": {}, "implementations": {}}
    for name in ("commerce", "router", "policy", "payment_token"):
        code = w3.eth.get_code(getattr(spec, name), block_identifier=number)
        if not isinstance(code, bytes) or not code:
            raise ValueError("Configured testnet contract has no readable code")
        report["code_hashes"][name] = Web3.to_hex(Web3.keccak(code))
    for name, expected in (("commerce", PINNED.commerce_impl), ("router", PINNED.router_impl)):
        slot = w3.eth.get_storage_at(getattr(spec, name), IMPLEMENTATION_SLOT, block_identifier=number)
        if not isinstance(slot, bytes) or len(slot) != 32 or any(slot[:12]):
            raise ValueError("Proxy implementation slot is unreadable or malformed")
        implementation = _address(Web3.to_hex(slot[-20:]))
        report["implementations"][name] = {"expected": expected, "observed": implementation}
        if implementation != expected:
            report["blockers"].append(f"IMPLEMENTATION_DRIFT:{name}")
        else:
            implementation_code = w3.eth.get_code(implementation, block_identifier=number)
            if not implementation_code:
                raise ValueError("Pinned implementation has no readable code")
            code_hash = Web3.to_hex(Web3.keccak(implementation_code))
            report["code_hashes"][name + "_implementation"] = code_hash
            if name == "commerce" and code_hash != REVIEWED_COMMERCE_CODE_HASH:
                report["blockers"].append("IMPLEMENTATION_CODE_DRIFT:commerce")
    native_balance = _integer(w3.eth.get_balance(spec.client, block_identifier=number), "native balance")
    report["native_balance_wei"] = native_balance
    if native_balance == 0:
        report["blockers"].append("TESTNET_GAS_BALANCE_REQUIRED")
    if report["blockers"]:
        return _check_snapshot(w3, report)

    commerce = w3.eth.contract(address=spec.commerce, abi=load_abi("AgenticCommerce.json"))
    router = w3.eth.contract(address=spec.router, abi=load_abi("EvaluatorRouter.json"))
    policy = w3.eth.contract(address=spec.policy, abi=load_abi("OptimisticPolicy.json"))
    token = w3.eth.contract(address=spec.payment_token, abi=TOKEN_ABI)
    if (any(_read(contract, "paused", [], number) is not False for contract in (commerce, router))
            or _read(router, "policyWhitelist", [spec.policy], number) is not True
            or _address(_read(commerce, "paymentToken", [], number)) != spec.payment_token
            or _read(commerce, "isPaymentTokenSupported", [spec.payment_token], number) is not True
            or _address(_read(router, "commerce", [], number)) != spec.commerce
            or _address(_read(policy, "commerce", [], number)) != spec.commerce
            or _address(_read(policy, "router", [], number)) != spec.router):
        raise ValueError("Testnet contracts are paused or routing/token state diverges")
    dispute_window = _integer(_read(policy, "disputeWindow", [], number), "dispute window")
    maximum_expiry = _integer(_read(commerce, "MAX_EXPIRY_DURATION", [], number), "maximum expiry", 1)
    if not dispute_window + 60 < spec.expired_at - now <= maximum_expiry:
        raise ValueError("Job deadline is incompatible with the configured dispute window")
    description, quote_expiry = _quote_description(w3, spec, number, now)
    report["valid_until"] = min(quote_expiry, spec.expired_at - dispute_window - 60)
    report["submit_deadline"] = spec.expired_at - dispute_window
    create_arguments = [spec.provider, spec.router, spec.expired_at, description, spec.router]
    if creation_tx_hash is None:
        return _unsigned(w3, spec, report, commerce, "createJob", create_arguments, "CREATE_JOB")
    job_id = _confirmed_job_id(w3, spec, commerce, creation_tx_hash,
                               commerce.encode_abi("createJob", args=create_arguments), number)
    report["job_id"] = job_id
    job = _decode_job(_read(commerce, "getJob", [job_id], number))
    if (job.id != job_id or job.client != spec.client or job.provider != spec.provider
            or job.evaluator != spec.router or job.hook != spec.router
            or job.description != description or job.expired_at != spec.expired_at
            or _address(_read(commerce, "jobPaymentToken", [job_id], number)) != spec.payment_token):
        raise ValueError("Created job or job token differs from the original signed intent")
    registered_policy = _address(_read(router, "jobPolicy", [job_id], number))
    if job.status == JobStatus.FUNDED:
        if job.budget != spec.budget or registered_policy != spec.policy:
            raise ValueError("Funded job budget or policy differs from original intent")
        return _check_snapshot(w3, {**report, "status": "FUNDED_CONFIRMED", "stage": "FUNDED_CONFIRMED"})
    if job.status != JobStatus.OPEN:
        raise ValueError("Job is no longer OPEN; reconcile instead of retrying")
    if registered_policy == Web3.to_checksum_address(ZERO_ADDRESS):
        return _unsigned(w3, spec, report, router, "registerJob", [job_id, spec.policy], "REGISTER_JOB")
    if registered_policy != spec.policy:
        raise ValueError("Job is registered with another policy")
    has_budget = _read(commerce, "jobHasBudget", [job_id], number)
    if has_budget is False:
        return _unsigned(w3, spec, report, commerce, "setBudget", [job_id, spec.budget, b""], "SET_BUDGET")
    if has_budget is not True or job.budget != spec.budget:
        raise ValueError("Existing job budget differs from original authorized budget")
    balance = _integer(_read(token, "balanceOf", [spec.client], number), "payment-token balance")
    if balance < spec.budget:
        return _check_snapshot(w3, {**report, "blockers": ["TESTNET_PAYMENT_TOKEN_BALANCE_REQUIRED"]})
    allowance = _integer(_read(token, "allowance", [spec.client, spec.commerce], number), "allowance")
    if allowance != spec.budget:
        amount = 0 if allowance else spec.budget
        return _unsigned(w3, spec, report, token, "approve", [spec.commerce, amount],
                         "RESET_APPROVAL" if allowance else "APPROVE_EXACT")
    return _unsigned(w3, spec, report, commerce, "fund", [job_id, spec.budget, b""], "FUND_JOB")
