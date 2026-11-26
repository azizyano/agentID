"""Export a bounded, explicitly confirmed MetaMask funding session; never execute it."""

import json
from pathlib import Path

from bnbagent.core.abis import load_abi
from bnbagent.erc8183.negotiation import build_job_description
from bnbagent.erc8183.quote_verify import quote_content_error
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from .testnet_deployment import PINNED, REVIEWED_COMMERCE_CODE_HASH
from .testnet_plan import TestnetJobSpec, IMPLEMENTATION_SLOT


def funding_script(plan, spec, approved):
    spec = TestnetJobSpec.model_validate(spec)
    if (plan.get("status") != "UNSIGNED_PLAN" or plan.get("stage") != "CREATE_JOB"
            or spec.budget != 10**18 or plan.get("chain_id") != 97
            or quote_content_error(spec.quote) is not None):
        raise ValueError("An approved one-U signed create plan is required")
    if (approved.get("status") != "APPROVED_BY_OWNER" or approved.get("proposed_budget_raw") != str(spec.budget)
            or any(str(approved.get(field, "")).lower() != getattr(spec, field).lower()
                   for field in ("client", "provider", "payment_token"))):
        raise ValueError("Participants or budget differ from owner approval")
    signer = Account.recover_message(encode_defunct(text=spec.quote["negotiation_hash"]),
                                     signature=spec.quote["provider_sig"])
    if signer.lower() != spec.provider.lower():
        raise ValueError("Wrong provider signature")
    description = build_job_description(spec.quote)
    content = json.loads(description)
    if (content["price"] != str(spec.budget) or content["currency"].lower() != spec.payment_token.lower()
            or content.get("chain_id") != 97 or content.get("verifying_contract", "").lower() != spec.commerce.lower()):
        raise ValueError("Signed quote price, asset or domain mismatch")
    commerce_abi = load_abi("AgenticCommerce.json")
    commerce = Web3().eth.contract(address=spec.commerce, abi=commerce_abi)
    create_data = commerce.encode_abi("createJob", args=[spec.provider, spec.router, spec.expired_at, description, spec.router])
    tx = plan.get("next_transaction", {})
    if tx != {"chainId": 97, "from": spec.client, "to": spec.commerce, "value": 0, "data": create_data}:
        raise ValueError("Plan transaction differs from signed context")
    if plan["code_hashes"].get("commerce_implementation") != REVIEWED_COMMERCE_CODE_HASH:
        raise ValueError("Unreviewed commerce runtime")
    expiry = spec.quote["response"]["quote_expires_at"]
    if plan["valid_until"] > expiry or spec.expired_at - spec.quote["response"]["negotiated_at"] != 3600:
        raise ValueError("Deadline expansion is not allowed")
    needed = {
        "commerce": {"getJob","JobCreated","createJob","paused","paymentToken","isPaymentTokenSupported","jobPaymentToken","jobHasBudget","setBudget","fund"},
        "router": {"paused","commerce","policyWhitelist","jobPolicy","registerJob"},
        "policy": {"commerce","router","disputeWindow"},
        "token": {"balanceOf","allowance","approve"},
    }
    abis = {"commerce": commerce_abi, "router": load_abi("EvaluatorRouter.json"),
            "policy": load_abi("OptimisticPolicy.json"), "token": load_abi("ERC20.json")}
    abis = {name: [entry for entry in entries if entry.get("name") in needed[name]] for name, entries in abis.items()}
    config = {**spec.model_dump(exclude={"quote"}), "budget": str(spec.budget),
              "description": description, "createData": create_data, "validUntil": plan["valid_until"],
              "quoteHash": spec.quote["negotiation_hash"], "providerSignature": spec.quote["provider_sig"],
              "implementationSlot": hex(IMPLEMENTATION_SLOT),
              "implementations": {"commerce": PINNED.commerce_impl, "router": PINNED.router_impl},
              "codeHashes": plan["code_hashes"],
              "abis": abis}
    template = Path(__file__).with_name("wallet_funding.js").read_text(encoding="utf-8")
    return template.replace("__CONFIG__", json.dumps(config))
