"""Compare locally built source to testnet runtime and inspect the linked faucet."""

import hashlib
import json
import subprocess
from pathlib import Path

from bnbagent.core.abis import load_abi
from bnbagent.networks.addresses import get_address
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "f6a3c4ff337158a8a66281c565f3f1562e1287b7"
FAUCET_REVISION = "618c47d388c1d21f23ce65e0a186a1f1f9d05e57"
IMPLEMENTATION = "0x55c3826B39a0F671B2C3E5D0F1372CaD0B911421"
FAUCET = "0x86e9197CC0F76E4e4aaa7082180945196bBAb5D3"
CLIENT = "0xb16b77C16773DEF8fA279A1228Eba9308eCD7841"


def without_metadata(code):
    if len(code) < 3:
        raise ValueError("Missing Solidity metadata trailer")
    size = int.from_bytes(code[-2:], "big")
    if not 0 < size < len(code) - 2 or code[-size-2] & 0xE0 != 0xA0:
        raise ValueError("Unsupported Solidity metadata trailer")
    return code[:-size-2]


def linked_runtime(compiled, implementation):
    bytecode = compiled["contract"]["evm"]["deployedBytecode"]
    if bytecode.get("linkReferences"):
        raise ValueError("Unreviewed linked libraries")
    code = bytearray.fromhex(bytecode["object"])
    references = bytecode["immutableReferences"]
    for identifier, entries in references.items():
        if compiled["immutable_names"].get(identifier) != "__self":
            raise ValueError("Unreviewed immutable")
        for item in entries:
            start, length = item["start"], item["length"]
            if length != 32 or start < 0 or start + length > len(code) or any(code[start:start+length]):
                raise ValueError("Unsupported immutable substitution")
            code[start:start+length] = bytes.fromhex("00" * 12 + implementation[2:])
    return bytes(code)


def abi_type(item):
    kind = item["type"]
    return "(" + ",".join(abi_type(c) for c in item["components"]) + ")" + kind[5:] if kind.startswith("tuple") else kind


def function_shapes(abi):
    return {entry["name"] + "(" + ",".join(abi_type(i) for i in entry["inputs"]) + ")":
            ([abi_type(o) for o in entry["outputs"]], entry["stateMutability"])
            for entry in abi if entry["type"] == "function"}


def event_shapes(abi):
    return {entry["name"]: (entry.get("anonymous", False),
            [(item["name"], abi_type(item), item["indexed"]) for item in entry["inputs"]])
            for entry in abi if entry["type"] == "event"}


def verify(w3):
    if type(w3.eth.chain_id) is not int or w3.eth.chain_id != 97:
        raise ValueError("Testnet97 required")
    source_root = ROOT / ".research/apex-contracts"
    revision = subprocess.check_output(["git", "-C", str(source_root), "rev-parse", "HEAD"], text=True).strip()
    if revision != SOURCE_REVISION:
        raise ValueError("Source revision changed")
    subprocess.run(["git", "-C", str(source_root), "diff", "--exit-code", "HEAD", "--", "contracts"], check=True, capture_output=True)
    compiled = json.loads((ROOT / ".research/source-build/commerce.json").read_text())
    source_hash = hashlib.sha256((source_root / compiled["source_path"]).read_bytes()).hexdigest()
    if source_hash != compiled["source_sha256"] or not compiled["compiler"].startswith("0.8.28+commit.7893614a"):
        raise ValueError("Source/compiler binding differs")
    block = w3.eth.get_block("finalized")
    number = block["number"]
    pinned = get_address(97)
    slot = int.from_bytes(Web3.keccak(text="eip1967.proxy.implementation"), "big") - 1
    current = Web3.to_checksum_address(w3.eth.get_storage_at(pinned.commerce_proxy, slot, block_identifier=number)[-20:])
    if current != IMPLEMENTATION:
        raise ValueError("Live implementation changed again")
    live = w3.eth.get_code(current, block_identifier=number)
    built = linked_runtime(compiled, current)
    expected = function_shapes(load_abi("AgenticCommerce.json"))
    actual = function_shapes(compiled["contract"]["abi"])
    incompatible = [name for name, shape in expected.items() if actual.get(name) != shape]
    expected_events = event_shapes(load_abi("AgenticCommerce.json"))
    actual_events = event_shapes(compiled["contract"]["abi"])
    incompatible_events = [name for name, shape in expected_events.items() if actual_events.get(name) != shape]
    commerce = w3.eth.contract(address=pinned.commerce_proxy, abi=compiled["contract"]["abi"])
    default_supported = commerce.functions.isPaymentTokenSupported(pinned.payment_token).call(block_identifier=number)
    source_report = {"chain_id": 97, "block_number": number, "block_hash": Web3.to_hex(block["hash"]),
                     "assurance": "RPC_FINALIZED_READ", "source_repository": "https://github.com/bnb-chain/apex-contracts",
                     "source_revision": revision, "source_sha256": source_hash,
                     "compiler": compiled["compiler"], "settings": compiled["settings"],
                     "compiler_file_sha256": compiled["compiler_file_sha256"], "package_lock_sha256": compiled["package_lock_sha256"],
                     "implementation": current, "runtime_code_keccak256": Web3.to_hex(Web3.keccak(live)),
                     "full_runtime_match": built == live,
                     "executable_runtime_match": without_metadata(built) == without_metadata(live),
                     "comparison": "UUPS __self linked to implementation; Solidity CBOR metadata excluded for executable comparison",
                     "sdk_function_count": len(expected), "sdk_incompatible_functions": incompatible,
                     "sdk_event_count": len(expected_events), "sdk_incompatible_events": incompatible_events,
                     "default_payment_token_supported": default_supported,
                     "transactions_sent": 0}
    abi = [{"type": "function", "name": name, "stateMutability": "view", "inputs": args,
            "outputs": [{"name": "", "type": output}]} for name, args, output in (
                ("tokenInstance", [], "address"), ("tokenAmount", [], "uint256"),
                ("allowedToWithdraw", [{"name": "account", "type": "address"}], "bool"),
                ("waitTime", [], "uint256"))]
    abi.append({"type": "function", "name": "requestTokens", "stateMutability": "nonpayable", "inputs": [], "outputs": []})
    faucet = w3.eth.contract(address=FAUCET, abi=abi)
    def read(fn):
        return fn.call(block_identifier=number)
    token = read(faucet.functions.tokenInstance())
    amount = read(faucet.functions.tokenAmount())
    erc20 = w3.eth.contract(address=token, abi=load_abi("ERC20.json"))
    faucet_report = {"chain_id": 97, "block_number": number, "block_hash": Web3.to_hex(block["hash"]),
                     "assurance": "RPC_FINALIZED_READ", "source_revision": FAUCET_REVISION,
                     "source_repository": "https://github.com/united-coin-u/u-faucet",
                     "sdk_linked_url": "https://united-coin-u.github.io/u-faucet/", "faucet": FAUCET,
                     "faucet_code_keccak256": Web3.to_hex(Web3.keccak(w3.eth.get_code(FAUCET, block_identifier=number))),
                     "token": token, "token_matches_job": token.lower() == pinned.payment_token.lower(),
                     "amount_raw": amount, "token_decimals": read(erc20.functions.decimals()),
                     "faucet_balance_raw": read(erc20.functions.balanceOf(FAUCET)),
                     "client": CLIENT, "client_eligible": read(faucet.functions.allowedToWithdraw(CLIENT)),
                     "wait_seconds": read(faucet.functions.waitTime()), "transactions_sent": 0}
    draft = {"chainId": 97, "from": CLIENT, "to": FAUCET, "value": 0,
             "data": faucet.encode_abi("requestTokens", args=[])}
    if faucet_report["token_matches_job"] and faucet_report["client_eligible"] is True and faucet_report["faucet_balance_raw"] >= amount > 0:
        w3.eth.call(draft, block_identifier=number)
        faucet_report["claim_simulated"] = True
        faucet_report["unsigned_claim"] = draft
    if w3.eth.get_block(number)["hash"] != block["hash"]:
        raise ValueError("Snapshot changed")
    return source_report, faucet_report


if __name__ == "__main__":
    w3 = Web3(Web3.HTTPProvider("https://bsc-testnet-dataseed.bnbchain.org", request_kwargs={"timeout": 15}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    source, faucet = verify(w3)
    out = ROOT / "artifacts/testnet"
    out.mkdir(parents=True, exist_ok=True)
    for name, report in (("source-verification", source), ("faucet-verification", faucet)):
        (out / (name + ".json")).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source": source, "faucet": faucet}, indent=2))
    raise SystemExit(0 if source["executable_runtime_match"] and not source["sdk_incompatible_functions"] and not source["sdk_incompatible_events"] and source["default_payment_token_supported"] is True else 1)
