"""Export the exact simulated create-job call for manual MetaMask confirmation."""

import json
from pathlib import Path

from web3 import Web3
from bnbagent.core.abis import load_abi
from bnbagent.erc8183.negotiation import build_job_description

ROOT = Path(__file__).resolve().parents[1]


def create_script(plan, spec):
    tx = plan["next_transaction"]
    if (plan.get("status") != "UNSIGNED_PLAN" or plan.get("stage") != "CREATE_JOB"
            or tx["chainId"] != 97 or tx["from"] != spec["client"]
            or tx["to"] != spec["commerce"] or tx["value"] != 0):
        raise ValueError("Expected the exact approved unsigned create step")
    contract = Web3().eth.contract(address=spec["commerce"], abi=load_abi("AgenticCommerce.json"))
    expected = contract.encode_abi("createJob", args=[spec["provider"], spec["router"], spec["expired_at"],
                                                    build_job_description(spec["quote"]), spec["router"]])
    if tx["data"] != expected:
        raise ValueError("Create calldata differs from signed job terms")
    rpc_tx = {**tx, "chainId": "0x61", "value": "0x0"}
    key = "veriabstain:97:create:" + spec["quote"]["negotiation_hash"]
    return """// CREATE_JOB ONLY. Review the client-wallet gas fee; no U funding yet.
(async () => {
  const tx = TRANSACTION;
  const validUntil = EXPIRY;
  const key = STORAGE_KEY;
  const provider = window.ethereum;
  if (!provider) throw new Error('MetaMask not found');
  const previous = localStorage.getItem(key);
  if (previous) { console.log('EXISTING_CREATE_ATTEMPT', previous); return; }
  if (Date.now() / 1000 >= validUntil) throw new Error('Quote expired: do not create this job');
  if (await provider.request({method: 'eth_chainId'}) !== '0x61') throw new Error('Select BSC testnet 97');
  const accounts = await provider.request({method: 'eth_requestAccounts'});
  if (!accounts[0] || accounts[0].toLowerCase() !== tx.from.toLowerCase())
    throw new Error('Connect the CLIENT wallet ending 7841');
  if (Date.now() / 1000 >= validUntil) throw new Error('Quote expired: do not create this job');
  localStorage.setItem(key, JSON.stringify({state: 'AWAITING_WALLET_CONFIRMATION'}));
  try {
    const hash = await provider.request({method: 'eth_sendTransaction', params: [tx]});
    localStorage.setItem(key, JSON.stringify({state: 'SUBMITTED', transactionHash: hash}));
    console.log('PUBLIC_CREATE_JOB_TXHASH', hash);
    return hash;
  } catch (error) {
    if (error.code === 4001) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify({state: 'UNKNOWN_RECONCILE_BEFORE_RETRY'}));
    throw error;
  }
})();
""".replace("TRANSACTION", json.dumps(rpc_tx)).replace("EXPIRY", str(plan["valid_until"])).replace("STORAGE_KEY", json.dumps(key))


if __name__ == "__main__":
    plan = json.loads((ROOT / "artifacts/testnet/create-job-plan.json").read_text())
    spec = json.loads((ROOT / "artifacts/testnet/quote/signed-job.json").read_text())
    output = ROOT / "artifacts/testnet/create-job-metamask.js"
    output.write_text(create_script(plan, spec), encoding="utf-8")
    print("Exact create-job helper exported; no wallet called or transaction sent.")
