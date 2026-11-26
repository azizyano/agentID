"""Read public pinned SDK deployment state; never sign or broadcast."""

import argparse
import json
import sys
from pathlib import Path

from bnbagent.core.abis import load_abi
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/evaluation"))
from veriabstain_eval.testnet_deployment import PINNED, REVIEWED_COMMERCE_CODE_HASH, SOURCE_REVISION


def inspect(w3, client=None):
    if w3.eth.chain_id != 97:
        raise ValueError("Only BSC testnet chain 97 is supported")
    block = w3.eth.get_block("finalized")
    number = block["number"]
    addresses = PINNED
    contracts = {}
    for name in ("commerce_proxy", "router_proxy", "policy", "payment_token", "commerce_impl", "router_impl"):
        address = getattr(addresses, name)
        code = w3.eth.get_code(address, block_identifier=number)
        contracts[name] = {"address": address, "code_bytes": len(code),
                           "code_keccak256": Web3.to_hex(Web3.keccak(code))}
    commerce = w3.eth.contract(address=addresses.commerce_proxy, abi=load_abi("AgenticCommerce.json"))
    router = w3.eth.contract(address=addresses.router_proxy, abi=load_abi("EvaluatorRouter.json"))
    policy = w3.eth.contract(address=addresses.policy, abi=load_abi("OptimisticPolicy.json"))
    def read(fn):
        return fn.call(block_identifier=number)
    checks = {"commerce_payment_token": read(commerce.functions.paymentToken()),
              "router_commerce": read(router.functions.commerce()),
              "policy_whitelisted": read(router.functions.policyWhitelist(addresses.policy)),
              "router_paused": read(router.functions.paused()),
              "commerce_paused": read(commerce.functions.paused()),
              "policy_commerce": read(policy.functions.commerce()),
              "policy_router": read(policy.functions.router()),
              "dispute_window_seconds": read(policy.functions.disputeWindow())}
    implementation_slot = int.from_bytes(Web3.keccak(text="eip1967.proxy.implementation"), "big") - 1
    for name in ("commerce", "router"):
        stored = w3.eth.get_storage_at(getattr(addresses, name + "_proxy"), implementation_slot, block_identifier=number)
        checks[name + "_implementation"] = Web3.to_checksum_address(stored[-20:])
        actual_code = w3.eth.get_code(checks[name + "_implementation"], block_identifier=number)
        checks[name + "_implementation_code_keccak256"] = Web3.to_hex(Web3.keccak(actual_code))
    result = {"mode": "READ_ONLY_TESTNET_INSPECTION", "chain_id": 97,
              "block_number": number, "block_hash": Web3.to_hex(block["hash"]),
              "block_timestamp": block["timestamp"], "assurance": "RPC_FINALIZED_READ",
              "sdk_revision": "260e16196931780d0370bd3a9d9b67ece744bb9d",
              "reviewed_contract_source_revision": SOURCE_REVISION,
              "contracts": contracts, "checks": checks,
              "transactions": 0, "funded_job_created": False}
    if client:
        client = Web3.to_checksum_address(client)
        token = w3.eth.contract(address=addresses.payment_token, abi=load_abi("ERC20.json"))
        result["client"] = {"address": client,
                            "native_balance_wei": w3.eth.get_balance(client, block_identifier=number),
                            "payment_token_balance_raw": read(token.functions.balanceOf(client)),
                            "payment_token_decimals": read(token.functions.decimals()),
                            "payment_token_symbol": read(token.functions.symbol())}
    if w3.eth.get_block(number)["hash"] != block["hash"]:
        raise ValueError("Pinned block changed")
    result["compatible_read_surface"] = (
        all(item["code_bytes"] for item in contracts.values())
        and checks["commerce_payment_token"].lower() == addresses.payment_token.lower()
        and checks["router_commerce"].lower() == addresses.commerce_proxy.lower()
        and checks["policy_commerce"].lower() == addresses.commerce_proxy.lower()
        and checks["policy_router"].lower() == addresses.router_proxy.lower()
        and all(checks[name + "_implementation"].lower() == getattr(addresses, name + "_impl").lower()
                for name in ("commerce", "router"))
        and checks["commerce_implementation_code_keccak256"] == REVIEWED_COMMERCE_CODE_HASH
        and checks["policy_whitelisted"] is True and checks["router_paused"] is False
        and checks["commerce_paused"] is False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpc-url", default="https://bsc-testnet-dataseed.bnbchain.org")
    parser.add_argument("--client")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/testnet/inspection.json")
    args = parser.parse_args()
    w3 = Web3(Web3.HTTPProvider(args.rpc_url, request_kwargs={"timeout": 15}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    try:
        result = inspect(w3, args.client)
    except Exception as error:
        result = {"mode": "READ_ONLY_TESTNET_INSPECTION", "status": "BLOCKED",
                  "error_type": type(error).__name__, "transactions": 0,
                  "message": "Public deployment inspection could not be completed; no transaction prepared."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result.get("compatible_read_surface") else 1


if __name__ == "__main__":
    raise SystemExit(main())
