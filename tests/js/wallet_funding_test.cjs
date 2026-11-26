// Actual ethers ABI handling; simulated EIP1193 only. No browser or network.
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const E = require(path.join(root,'.research/wallet-tests/node_modules/ethers'));
const script = fs.readFileSync(process.argv[2],'utf8');
const cfg = JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
const A = Object.fromEntries(Object.entries(cfg.abis).map(([k,v])=>[k,new E.Interface(v)]));
const HASH='0x'+'ab'.repeat(32), BAD='0x'+'cd'.repeat(32);
const word=a=>E.zeroPadValue(a,32), zero=E.ZeroAddress;
async function scenario(mode) {
  const saved=new Map(), receipts=new Map(), transactions=new Map(), sent=[];
  const time=cfg.validUntil-(mode==='expired'? -1 : mode==='short_window'?200:800);
  let created=false, registered=false, budgeted=false, funded=false, allowance=mode==='reset'?5n:0n;
  let next=1;
  const block={number:'0x64',timestamp:E.toQuantity(time),hash:HASH};
  const jobId=7n;
  const decodedJob=()=>[jobId,cfg.client,cfg.provider,cfg.router,cfg.description,budgeted?BigInt(cfg.budget):0n,
    BigInt(cfg.expired_at),funded?1:0,cfg.router,0n,E.ZeroHash];
  async function request({method,params=[]}) {
    if(method==='eth_chainId') return mode==='wrong_chain'?'0x38':'0x61';
    if(method==='eth_requestAccounts') return [mode==='wrong_wallet'?'0x'+'99'.repeat(20):cfg.client];
    if(method==='eth_getBlockByNumber') return {...block};
    if(method==='eth_getStorageAt') return word(params[0].toLowerCase()===cfg.commerce.toLowerCase()?cfg.implementations.commerce:cfg.implementations.router);
    if(method==='eth_getCode') {
      if(mode==='wrong_code') return '0xdead';
      const key=Object.keys(cfg).find(k=>typeof cfg[k]==='string'&&cfg[k].toLowerCase()===params[0].toLowerCase());
      return key ? cfg.testCode[key] : cfg.testCode[params[0].toLowerCase()];
    }
    if(method==='eth_getTransactionReceipt') {
      if(mode==='rpc_denied_after_send') throw Object.assign(new Error('RPC denied after send'),{code:4001});
      return receipts.get(params[0])||null;
    }
    if(method==='eth_getTransactionByHash') return transactions.get(params[0]);
    if(method==='eth_call') {
      const tx=params[0];
      if(tx.from) return '0x'; // simulation of a proposed write
      const kind=tx.to.toLowerCase()===cfg.commerce.toLowerCase()?'commerce':tx.to.toLowerCase()===cfg.router.toLowerCase()?'router':tx.to.toLowerCase()===cfg.policy.toLowerCase()?'policy':'token';
      const parsed=A[kind].parseTransaction({data:tx.data});
      let result;
      switch(parsed.name) {
        case 'paused': result=false; break;
        case 'commerce': result=cfg.commerce; break;
        case 'router': result=cfg.router; break;
        case 'paymentToken': case 'jobPaymentToken': result=cfg.payment_token; break;
        case 'policyWhitelist': case 'isPaymentTokenSupported': result=true; break;
        case 'disputeWindow': result=900n; break;
        case 'balanceOf': result=10n**19n; break;
        case 'getJob': result=decodedJob(); if(mode==='wrong_job') result[2]='0x'+'99'.repeat(20); break;
        case 'jobPolicy': result=registered?cfg.policy:zero; break;
        case 'jobHasBudget': result=budgeted; break;
        case 'allowance': result=allowance; break;
        default: throw new Error('Unexpected view '+parsed.name);
      }
      return A[kind].encodeFunctionResult(parsed.name,[result]);
    }
    if(method==='eth_sendTransaction') {
      const tx=params[0]; assert.equal(tx.chainId,'0x61'); assert.equal(tx.value,'0x0');
      assert.equal(tx.from,cfg.client);
      if(mode==='denied') throw Object.assign(new Error('wallet rejected'),{code:4001});
      if(mode==='ambiguous') throw new Error('ambiguous wallet effect');
      const kind=tx.to.toLowerCase()===cfg.commerce.toLowerCase()?'commerce':tx.to.toLowerCase()===cfg.router.toLowerCase()?'router':'token';
      const call=A[kind].parseTransaction({data:tx.data}); sent.push(call.name);
      const hash='0x'+(next++).toString(16).padStart(64,'0'); let logs=[];
      if(call.name==='createJob') {
        assert.equal(created,false); created=true;
        assert.equal(tx.data,cfg.createData);
        const ev=A.commerce.encodeEventLog(A.commerce.getEvent('JobCreated'),[jobId,cfg.client,cfg.provider,cfg.router,BigInt(cfg.expired_at),cfg.router]);
        logs=[{address:cfg.commerce,...ev}];
      } else if(call.name==='registerJob') {assert.equal(call.args[0],jobId); registered=true;}
      else if(call.name==='setBudget') {assert.equal(call.args[1],10n**18n); budgeted=true;}
      else if(call.name==='approve') {assert.equal(call.args[0],cfg.commerce); assert.ok(call.args[1]===0n||call.args[1]===10n**18n); allowance=call.args[1];}
      else if(call.name==='fund') {assert.equal(call.args[0],jobId); assert.equal(call.args[1],10n**18n); assert.equal(allowance,10n**18n); funded=true;}
      else throw new Error('Unexpected write '+call.name);
      receipts.set(hash,{status:'0x1',blockNumber:block.number,blockHash:HASH,logs});
      transactions.set(hash,{...tx,input:tx.data}); return hash;
    }
    throw new Error('Unexpected RPC '+method);
  }
  let locked=false;
  const context={window:{ethereum:{request},ethers:E},Date:{now:()=>time*1000},setTimeout:fn=>fn(),
    location:{origin:'https://united-coin-u.github.io'},navigator:{locks:{request:async(key,options,callback)=>{
      if(locked)return callback(null);locked=true;try{return await callback({name:key});}finally{locked=false;}
    }}},
    console:{log(){}},localStorage:{getItem:k=>saved.get(k)||null,setItem:(k,v)=>saved.set(k,v),removeItem:k=>saved.delete(k)}};
  const patched=script.replace('__CONFIG__',JSON.stringify(cfg));
  if(mode==='parallel') {
    const outcomes=await Promise.allSettled([vm.runInNewContext(patched,context),vm.runInNewContext(patched,context)]);
    assert.equal(outcomes.filter(o=>o.status==='fulfilled').length,1);
    assert.equal(outcomes.filter(o=>o.status==='rejected').length,1);
    assert.equal(sent.length,5);
  } else if(mode==='success'||mode==='reset') {
    const result=await vm.runInNewContext(patched,context); assert.equal(result.jobId,'7');
    assert.deepEqual(sent,mode==='reset'?['createJob','registerJob','setBudget','approve','approve','fund']:['createJob','registerJob','setBudget','approve','fund']);
    const count=sent.length; await vm.runInNewContext(patched,context); assert.equal(sent.length,count);
  } else {
    await assert.rejects(vm.runInNewContext(patched,context));
    if(['wrong_chain','wrong_wallet','wrong_code','expired','short_window'].includes(mode)) assert.equal(sent.length,0);
    if(mode==='denied') assert.ok([...saved.values()].every(v=>!v.includes('AWAITING_WALLET_CONFIRMATION')));
    if(mode==='ambiguous') assert.ok([...saved.values()].some(v=>v.includes('AWAITING_WALLET_CONFIRMATION')));
    if(mode==='rpc_denied_after_send') assert.ok([...saved.values()].some(v=>v.includes('SUBMITTED')&&v.includes('hash')));
    if(mode==='wrong_job') assert.equal(sent.length,1);
  }
}
(async()=>{for(const mode of ['success','reset','wrong_chain','wrong_wallet','wrong_code','expired','short_window','denied','ambiguous','rpc_denied_after_send','wrong_job','parallel']) await scenario(mode); console.log('12 funding-session scenarios passed; real ethers ABI, simulated wallet/RPC only.');})().catch(error=>{console.error(error);process.exitCode=1;});
