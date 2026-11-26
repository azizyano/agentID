"""Export cancellation of the reconciled OPEN/zero-budget job for wallet review."""
import json
import sys
from pathlib import Path
from web3 import Web3
from bnbagent.core.abis import load_abi
from bnbagent.erc8183.negotiation import build_job_description

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'packages/evaluation'))
from veriabstain_eval.testnet_deployment import PINNED, REVIEWED_COMMERCE_CODE_HASH
from veriabstain_eval.testnet_plan import IMPLEMENTATION_SLOT


def cancel_script(report, spec):
    if (report.get("job_status") != "OPEN" or report.get("budget_raw") != 0
            or report.get("quote_expired") is not True or report.get("commerce_allowance_raw") != 0
            or report.get("client") != spec["client"] or report.get("provider") != spec["provider"]
            or report.get("payment_token") != spec["payment_token"]):
        raise ValueError("Only the exact reconciled unfunded expired-quote job can be cancelled")
    tx = report["unsigned_cancellation_for_review"]
    abi = load_abi("AgenticCommerce.json")
    contract = Web3().eth.contract(address=spec["commerce"], abi=abi)
    expected = contract.encode_abi("reject", args=[report["job_id"], Web3.keccak(text="VERIABSTAIN_EXPIRED_UNFUNDED_QUOTE"), b""])
    if tx != {"chainId":97,"from":spec["client"],"to":spec["commerce"],"value":0,"data":expected}:
        raise ValueError("Cancellation calldata differs from reviewed intent")
    config = {"jobId": str(report["job_id"]), "client":spec["client"],"provider":spec["provider"],
              "token":spec["payment_token"],"description":build_job_description(spec["quote"]),
              "implementation":PINNED.commerce_impl,"implementationHash":REVIEWED_COMMERCE_CODE_HASH,
              "implementationSlot":hex(IMPLEMENTATION_SLOT),
              "abi":abi,"tx":{**tx,"chainId":"0x61","value":"0x0"}}
    return """// CANCEL the unused OPEN job only. User reviews a gas-only MetaMask confirmation.
(async () => {
  const c = CONFIG;
  if(!navigator.locks||location.origin!=='https://united-coin-u.github.io')throw new Error('Use HTTPS U faucet with Web Locks');
  return navigator.locks.request('veriabstain:97:cancel:'+c.jobId,{ifAvailable:true},async lock=>{
  if(!lock)throw new Error('Cancellation already active');
  const p=window.ethereum, E=window.ethers;
  if(!p||!E) throw new Error('Use the U faucet tab with MetaMask');
  const rpc=(method,params=[])=>p.request({method,params});
  const same=(a,b)=>a.toLowerCase()===b.toLowerCase();
  const key='veriabstain:97:cancel:'+c.jobId;
  const old=localStorage.getItem(key);
  if(old){console.log('EXISTING_CANCEL_ATTEMPT',old);return;}
  if(await rpc('eth_chainId')!=='0x61')throw new Error('Select BSC testnet97');
  const accounts=await rpc('eth_requestAccounts');
  if(!accounts[0]||!same(accounts[0],c.client))throw new Error('Select CLIENT wallet ending7841');
  const a=new E.Interface(c.abi);
  const b=await rpc('eth_getBlockByNumber',['finalized',false]);
  const slot=await rpc('eth_getStorageAt',[c.tx.to,c.implementationSlot,b.number]);
  if(!same('0x'+slot.slice(-40),c.implementation))throw new Error('Implementation changed');
  const code=await rpc('eth_getCode',[c.implementation,b.number]);
  if(!same(E.keccak256(code),c.implementationHash))throw new Error('Implementation code changed');
  const raw=await rpc('eth_call',[{to:c.tx.to,data:a.encodeFunctionData('getJob',[BigInt(c.jobId)])},b.number]);
  const j=a.decodeFunctionResult('getJob',raw)[0];
  if(j.id!==BigInt(c.jobId)||j.status!==0n||j.budget!==0n||!same(j.client,c.client)||!same(j.provider,c.provider)||j.description!==c.description)
    throw new Error('Job changed: do not cancel; reconcile');
  await rpc('eth_call',[c.tx,b.number]);
  const again=await rpc('eth_getBlockByNumber',[b.number,false]);
  if(!same(again.hash,b.hash))throw new Error('Pinned block changed');
  console.log('Review cancellation of unfunded job',c.jobId,'native value0 plus gas; no U transfer');
  localStorage.setItem(key,JSON.stringify({state:'AWAITING_WALLET_CONFIRMATION'}));
  try{
    const hash=await rpc('eth_sendTransaction',[c.tx]);
    localStorage.setItem(key,JSON.stringify({state:'SUBMITTED',transactionHash:hash}));
    console.log('PUBLIC_CANCEL_JOB_TXHASH',hash);return hash;
  }catch(error){
    if(error.code===4001)localStorage.removeItem(key);
    else localStorage.setItem(key,JSON.stringify({state:'UNKNOWN_RECONCILE_BEFORE_RETRY'}));
    throw error;
  }
  });
})();
""".replace("CONFIG",json.dumps(config))


if __name__ == '__main__':
    report=json.loads((ROOT/'artifacts/testnet/job-reconciliation.json').read_text())
    spec=json.loads((ROOT/'artifacts/testnet/quote/signed-job.json').read_text())
    output=ROOT/'artifacts/testnet/cancel-unused-job.js'
    output.write_text(cancel_script(report,spec),encoding='utf-8')
    print('Exact unfunded-job cancellation helper exported; no transaction sent.')
