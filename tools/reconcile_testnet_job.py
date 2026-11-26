"""Read-only reconciliation of the submitted create transaction; no quote bypass."""

import json
import sys
import time
from pathlib import Path
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from bnbagent.core.abis import load_abi
from bnbagent.erc8183.commerce import _decode_job
from bnbagent.erc8183.negotiation import build_job_description
from bnbagent.erc8183.quote_verify import verify_quote_signature

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/evaluation"))
from veriabstain_eval.testnet_plan import TestnetJobSpec, _confirmed_job_id, _hash
from veriabstain_eval.testnet_deployment import PINNED, REVIEWED_COMMERCE_CODE_HASH

CREATE_TX = "0x20876edfa2217bf193f3135fec8ee603643ce08dedecc8f25b096993e83cf0a9"


def reconcile(w3, spec, creation_hash, now):
    spec = TestnetJobSpec.model_validate(spec)
    if type(w3.eth.chain_id) is not int or w3.eth.chain_id != 97:
        raise ValueError("BSC testnet97 required")
    block = w3.eth.get_block("finalized")
    number = block["number"]
    slot = int.from_bytes(Web3.keccak(text="eip1967.proxy.implementation"), "big") - 1
    implementation = Web3.to_checksum_address(w3.eth.get_storage_at(spec.commerce, slot, block_identifier=number)[-20:])
    if implementation != PINNED.commerce_impl or Web3.to_hex(Web3.keccak(w3.eth.get_code(implementation, block_identifier=number))) != REVIEWED_COMMERCE_CODE_HASH:
        raise ValueError("Reviewed implementation changed")
    commerce = w3.eth.contract(address=spec.commerce, abi=load_abi("AgenticCommerce.json"))
    description = build_job_description(spec.quote)
    data = commerce.encode_abi("createJob", args=[spec.provider, spec.router, spec.expired_at, description, spec.router])
    job_id = _confirmed_job_id(w3, spec, commerce, creation_hash, data, number)
    receipt = w3.eth.get_transaction_receipt(creation_hash)
    verified = verify_quote_signature(envelope=spec.quote, provider=spec.provider, w3=w3,
                                      expected_verifying_contract=spec.commerce, block_number=receipt["blockNumber"])
    if not verified.valid:
        raise ValueError("Original quote was invalid at creation")
    job = _decode_job(commerce.functions.getJob(job_id).call(block_identifier=number))
    if (job.client != spec.client or job.provider != spec.provider or job.evaluator != spec.router
            or job.hook != spec.router or job.description != description or job.expired_at != spec.expired_at):
        raise ValueError("Job differs from the approved intent")
    token = w3.eth.contract(address=spec.payment_token, abi=load_abi("ERC20.json"))
    job_token = commerce.functions.jobPaymentToken(job_id).call(block_identifier=number)
    if job_token.lower() != spec.payment_token.lower():
        raise ValueError("Unexpected job token")
    allowance = token.functions.allowance(spec.client, spec.commerce).call(block_identifier=number)
    balance = token.functions.balanceOf(spec.client).call(block_identifier=number)
    expiry = spec.quote["response"]["quote_expires_at"]
    report = {"status": "CREATE_CONFIRMED", "assurance": "RPC_FINALIZED_READ", "chain_id": 97,
              "creation_transaction_hash": creation_hash, "job_id": job_id,
              "job_status": job.status.name, "budget_raw": job.budget,
              "client": spec.client, "provider": spec.provider, "payment_token": job_token,
              "client_u_balance_raw": balance, "commerce_allowance_raw": allowance,
              "quote_expired": now >= expiry, "quote_expires_at": expiry,
              "block_number": number, "block_hash": _hash(block["hash"]), "transactions_sent": 0}
    if report["quote_expired"] and job.status.name == "OPEN" and job.budget == 0:
        cancel = {"chainId": 97, "from": spec.client, "to": spec.commerce, "value": 0,
                  "data": commerce.encode_abi("reject", args=[job_id, Web3.keccak(text="VERIABSTAIN_EXPIRED_UNFUNDED_QUOTE"), b""])}
        w3.eth.call(cancel, block_identifier=number)
        report["unsigned_cancellation_for_review"] = cancel
        report["cancellation_sent"] = False
    if _hash(w3.eth.get_block(number)["hash"]) != report["block_hash"]:
        raise ValueError("Reconciliation snapshot changed")
    return report


if __name__ == "__main__":
    spec = json.loads((ROOT / "artifacts/testnet/quote/signed-job.json").read_text())
    w3 = Web3(Web3.HTTPProvider("https://bsc-testnet-dataseed.bnbchain.org", request_kwargs={"timeout": 15}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    report = reconcile(w3, spec, CREATE_TX, int(time.time()))
    (ROOT / "artifacts/testnet/job-reconciliation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
