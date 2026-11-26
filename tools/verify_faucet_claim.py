"""Read-only receipt check for the client's expected test U claim."""
import json
from pathlib import Path
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

CLIENT = Web3.to_checksum_address("0xb16b77C16773DEF8fA279A1228Eba9308eCD7841")
FAUCET = Web3.to_checksum_address("0x86e9197CC0F76E4e4aaa7082180945196bBAb5D3")
TOKEN = Web3.to_checksum_address("0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565")
TX = "0x4df3a5c278996a53a95bf856e4ef0f8589a967c975c32d4dd9abdd47f22067d6"

if __name__ == "__main__":
    w3 = Web3(Web3.HTTPProvider("https://bsc-testnet-dataseed.bnbchain.org", request_kwargs={"timeout": 15}))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if w3.eth.chain_id != 97:
        raise ValueError("Wrong chain")
    receipt = w3.eth.get_transaction_receipt(TX)
    tx = w3.eth.get_transaction(TX)
    finalized = w3.eth.get_block("finalized")
    if (receipt["status"] != 1 or receipt["blockNumber"] > finalized["number"]
            or w3.eth.get_block(receipt["blockNumber"])["hash"] != receipt["blockHash"]
            or tx["from"] != CLIENT or tx["to"] != FAUCET or tx["value"] != 0
            or Web3.to_hex(tx["input"]) != "0x359cf2b7"):
        raise ValueError("Receipt does not establish the expected finalized claim")
    transfer = Web3.keccak(text="Transfer(address,address,uint256)")
    amount = sum(int.from_bytes(log["data"], "big") for log in receipt["logs"]
                 if log["address"] == TOKEN and len(log["topics"]) == 3
                 and log["topics"][0] == transfer
                 and Web3.to_checksum_address(log["topics"][1][-20:]) == FAUCET
                 and Web3.to_checksum_address(log["topics"][2][-20:]) == CLIENT)
    if amount != 10 * 10**18:
        raise ValueError("Expected 10 test U transfer was not found")
    result = {"chain_id": 97, "assurance": "RPC_FINALIZED_READ", "transaction_hash": TX,
              "status": "CLAIM_CONFIRMED", "client": CLIENT, "token": TOKEN,
              "received_raw": amount, "received_u": "10", "block_number": receipt["blockNumber"],
              "block_hash": Web3.to_hex(receipt["blockHash"]), "transactions_sent_by_project": 0}
    output = Path(__file__).resolve().parents[1] / "artifacts/testnet/claim-confirmed.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
