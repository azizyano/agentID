const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const test = require('node:test');

const root = path.resolve(__dirname, '..', '..');
const script = fs.readFileSync(path.join(root, 'artifacts', 'mvp', 'deploy-metamask.js'), 'utf8');
const plan = JSON.parse(fs.readFileSync(path.join(root, 'artifacts', 'mvp', 'deployment-package', 'deployment-plan.json')));
const preflight = JSON.parse(fs.readFileSync(path.join(root, 'artifacts', 'mvp', 'mainnet-preflight-7841.json')));
const expectedName = script.match(/"registryNameResult":"(0x[0-9a-f]+)"/)[1];
const expectedSymbol = script.match(/"registrySymbolResult":"(0x[0-9a-f]+)"/)[1];

function context({origin = 'https://bscscan.com', chain = '0x38', account = preflight.deployer,
                  sendResult = '0x' + '12'.repeat(32), sendError = null} = {}) {
  const calls = [];
  const storage = new Map();
  const block = {number: '0x1', hash: '0x' + 'ab'.repeat(32), timestamp: '0x' + Math.floor(Date.now() / 1000).toString(16)};
  const request = async ({method, params = []}) => {
    calls.push({method, params});
    if (method === 'eth_chainId') return chain;
    if (method === 'eth_requestAccounts' || method === 'eth_accounts') return [account];
    if (method === 'eth_getBlockByNumber') return block;
    if (method === 'eth_getCode') return '0x01';
    if (method === 'eth_call' && params[0].to) {
      return params[0].data === '0x06fdde03' ? expectedName : expectedSymbol;
    }
    if (method === 'eth_call') {
      const cfgRuntime = script.match(/"expectedRuntime":"(0x[0-9a-f]+)"/)[1];
      return cfgRuntime;
    }
    if (method === 'eth_estimateGas') return '0x562ba';
    if (method === 'eth_gasPrice') return '0x2faf080';
    if (method === 'eth_getBalance') return '0xde0b6b3a7640000';
    if (method === 'eth_sendTransaction') {
      if (sendError) throw sendError;
      return sendResult;
    }
    assert.fail('Unexpected RPC ' + method);
  };
  return {
    calls, storage,
    sandbox: {
      location: {origin},
      navigator: {locks: {request: async (_key, _options, callback) => callback({})}},
      localStorage: {
        getItem: key => storage.get(key) || null,
        setItem: (key, value) => storage.set(key, value),
        removeItem: key => storage.delete(key),
      },
      window: {ethereum: {request}},
      console: {log: () => {}},
      Date, BigInt, JSON, Error, Math,
    },
  };
}

test('wrong origin, chain, or account never opens a wallet transaction', async () => {
  for (const options of [
    {origin: 'https://example.com'},
    {chain: '0x61'},
    {account: '0x' + '11'.repeat(20)},
  ]) {
    const state = context(options);
    await assert.rejects(vm.runInNewContext(script, state.sandbox));
    assert.equal(state.calls.some(call => call.method === 'eth_sendTransaction'), false);
  }
});

test('successful path submits exactly the reviewed zero-value creation transaction', async () => {
  const state = context();
  const hash = await vm.runInNewContext(script, state.sandbox);
  assert.equal(hash, '0x' + '12'.repeat(32));
  const sends = state.calls.filter(call => call.method === 'eth_sendTransaction');
  assert.equal(sends.length, 1);
  const tx = sends[0].params[0];
  assert.equal(tx.chainId, '0x38');
  assert.equal(tx.from, preflight.deployer);
  assert.equal(tx.value, '0x0');
  assert.equal(tx.data, plan.deployment_data);
  assert.equal('to' in tx, false);
  assert.match(tx.gas, /^0x[0-9a-f]+$/);
  const checkpoint = JSON.parse([...state.storage.values()][0]);
  assert.equal(checkpoint.state, 'SUBMITTED');
  assert.equal(checkpoint.hash, hash);
});

test('user denial clears checkpoint while unknown errors retain reconciliation stop', async () => {
  const denied = context({sendError: {code: 4001}});
  await assert.rejects(vm.runInNewContext(script, denied.sandbox));
  assert.equal(denied.storage.size, 0);
  const unknown = context({sendError: {code: -1}});
  await assert.rejects(vm.runInNewContext(script, unknown.sandbox));
  const checkpoint = JSON.parse([...unknown.storage.values()][0]);
  assert.equal(checkpoint.state, 'UNKNOWN_RECONCILE_BEFORE_RETRY');
});
