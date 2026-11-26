// Regression: browser window must remain accessible before wallet checks.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
let template;
async function check(chain, accounts, expected) {
  const calls = [];
  const cfg = {abis:{}, resultText:'{}', deliverableHash:'0xabc', provider:'0xprovider'};
  const context = {
    location:{origin:'https://united-coin-u.github.io'},
    navigator:{locks:{request:async (_key,_options,callback)=>callback({})}},
    localStorage:{getItem:()=>null,setItem:()=>assert.fail('Unexpected checkpoint write')},
    window:{ethers:{version:'6.13.4',keccak256:()=>cfg.deliverableHash,toUtf8Bytes:s=>s},
      ethereum:{request:async ({method})=>{
        calls.push(method);
        if(method==='eth_chainId') return chain;
        if(method==='eth_requestAccounts') return accounts;
        assert.fail('Unexpected RPC: '+method);
      }}},
  };
  await assert.rejects(vm.runInNewContext(template.replace('__CONFIG__',JSON.stringify(cfg)),context),
    error=>error.message===expected);
  assert(!calls.includes('eth_sendTransaction'));
}
(async()=>{
  for (const file of ['tools/provider-submit.template.js','tools/provider-settle.template.js']) {
    template=fs.readFileSync(file,'utf8');
    await check('0x1',[], 'Select BSC testnet97');
    await check('0x61',['0xother'], 'Select PROVIDER wallet ending B3c1');
  }
  console.log('Provider submit/settle startup: 4 regression checks passed; no transactions.');
})().catch(error=>{console.error(error);process.exitCode=1;});
