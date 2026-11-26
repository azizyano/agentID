// Exercise the generated handoff with a simulated wallet; no browser/network.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const script = fs.readFileSync(path.join(root, 'artifacts/testnet/create-job-metamask.js'), 'utf8');
const plan = JSON.parse(fs.readFileSync(path.join(root, 'artifacts/testnet/create-job-plan.json')));
async function run(mode) {
  const saved = new Map(); let sends = 0;
  const context = {Date: {now: () => (plan.valid_until + (mode === 'expired' ? 1 : -1)) * 1000},
    console: {log() {}}, localStorage: {getItem: k => saved.get(k), setItem: (k,v) => saved.set(k,v), removeItem: k => saved.delete(k)},
    window: {ethereum: {request: async request => {
      if (request.method === 'eth_chainId') return mode === 'wrong_chain' ? '0x38' : '0x61';
      if (request.method === 'eth_requestAccounts') return [mode === 'wrong_wallet' ? '0x' + '99'.repeat(20) : plan.next_transaction.from];
      assert.equal(request.method, 'eth_sendTransaction'); sends++;
      assert.equal(request.params[0].data, plan.next_transaction.data);
      assert.equal(request.params[0].value, '0x0');
      if (mode === 'denied' || mode === 'unknown') throw Object.assign(new Error(mode), {code: mode === 'denied' ? 4001 : -1});
      return '0x' + 'ab'.repeat(32);
    }}}};
  if (mode === 'success') {
    await vm.runInNewContext(script, context);
    await vm.runInNewContext(script, context);
    assert.equal(sends, 1);
  } else {
    await assert.rejects(vm.runInNewContext(script, context));
    assert.equal(sends, ['denied', 'unknown'].includes(mode) ? 1 : 0);
    assert.equal(saved.size, mode === 'unknown' ? 1 : 0);
  }
}
(async () => {
  for (const mode of ['success', 'wrong_chain', 'wrong_wallet', 'expired', 'denied', 'unknown']) await run(mode);
  console.log('6 simulated wallet handoff checks passed; no wallet/network called.');
})().catch(error => { console.error(error); process.exitCode = 1; });
