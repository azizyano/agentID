const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..', '..');
const dist = path.join(root, 'apps', 'web', 'dist');
const ethers = require(path.join(root, 'verification', 'wallet-tests', 'node_modules', 'ethers'));
const core = require(path.join(dist, 'core.js'));

function loadConfig() {
  const context = {};
  context.globalThis = context;
  vm.runInNewContext(fs.readFileSync(path.join(dist, 'config.js'), 'utf8'), context);
  return JSON.parse(JSON.stringify(context.VERIABSTAIN_CONFIG));
}

test('generated UI config is pinned to the exact deployed runtime', () => {
  const config = loadConfig();
  assert.equal(config.chainId, 56);
  assert.equal(config.contractAddress, '0x8ACF294c769e25dAb44aCbEb83fc401cA0702388');
  assert.equal(ethers.keccak256(config.expectedRuntime), config.expectedRuntimeKeccak256);
  const sha = crypto.createHash('sha256').update(Buffer.from(config.expectedRuntime.slice(2), 'hex')).digest('hex');
  assert.equal(`0x${sha}`, config.expectedRuntimeSha256);
  assert.equal(config.selectors['recordAssessment(bytes32,bytes32)'], ethers.id('recordAssessment(bytes32,bytes32)').slice(0, 10));
});

test('canonical hashing and calldata match independent implementations', async () => {
  const payload = {z: [2, {b: true, a: 'x'}], a: 1};
  const expectedCanonical = '{"a":1,"z":[2,{"a":"x","b":true}]}';
  assert.equal(core.canonical(payload), expectedCanonical);
  const expectedHash = `0x${crypto.createHash('sha256').update(expectedCanonical).digest('hex')}`;
  assert.equal(await core.sha256Hex(payload), expectedHash);

  const evidence = `0x${'12'.repeat(32)}`;
  const assessment = `0x${'34'.repeat(32)}`;
  const iface = new ethers.Interface(['function recordAssessment(bytes32,bytes32)']);
  assert.equal(
    core.buildRecordCalldata(ethers.id('recordAssessment(bytes32,bytes32)').slice(0, 10), evidence, assessment),
    iface.encodeFunctionData('recordAssessment', [evidence, assessment]),
  );
});

test('strict decoders and encoders reject malformed values', () => {
  const selector = ethers.id('balanceOf(address)').slice(0, 10);
  const address = '0x' + 'ab'.repeat(20);
  assert.equal(core.encodeAddressCall(selector, address), selector + '0'.repeat(24) + 'ab'.repeat(20));
  assert.equal(core.decodeBool('0x' + '0'.repeat(63) + '1'), true);
  assert.equal(core.decodeAddress('0x' + '0'.repeat(24) + 'ab'.repeat(20)), address);
  assert.throws(() => core.decodeBool('0x' + '0'.repeat(63) + '2'));
  assert.throws(() => core.encodeAddressCall(selector, 'bad'));
});

test('page is responsive, accessible, and avoids unsafe DOM injection', () => {
  const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8');
  const css = fs.readFileSync(path.join(dist, 'styles.css'), 'utf8');
  const app = fs.readFileSync(path.join(dist, 'app.js'), 'utf8');
  for (const id of ['proof-console', 'primary-action', 'record-action', 'status-message', 'unique-count']) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(html, /<meta name="viewport"/);
  assert.match(html, /class="skip-link"/);
  assert.match(css, /@media \(max-width: 680px\)/);
  assert.match(css, /prefers-reduced-motion/);
  assert.doesNotMatch(app, /\.innerHTML\s*=/);
  assert.doesNotMatch(app, /\beval\s*\(/);
});

test('page bootstrap performs reads only and never prompts or sends', async () => {
  const calls = [];
  const handlers = {};
  function element(id) {
    return {
      id,
      textContent: '',
      hidden: false,
      disabled: false,
      className: '',
      classList: {add() {}, remove() {}},
      style: {setProperty() {}},
      addEventListener(name, fn) { handlers[`${id}:${name}`] = fn; },
      querySelector() { return {textContent: ''}; },
    };
  }
  const elements = new Map();
  const get = id => elements.get(id) || (elements.set(id, element(id)), elements.get(id));
  const zero = '0x' + '0'.repeat(64);
  const provider = {
    async request({method}) {
      calls.push(method);
      if (method === 'eth_chainId') return '0x38';
      if (method === 'eth_accounts') return [];
      if (method === 'eth_call') return zero;
      throw new Error(`Unexpected bootstrap method: ${method}`);
    },
    on() {},
  };
  const context = {
    globalThis: null,
    ethereum: provider,
    VERIABSTAIN_CONFIG: loadConfig(),
    VeriAbstainCore: core,
    document: {getElementById: get, querySelector: () => element('row')},
    localStorage: {setItem() {}, removeItem() {}},
    setTimeout,
    clearTimeout,
    console,
    Promise,
    BigInt,
  };
  context.globalThis = context;
  vm.runInNewContext(fs.readFileSync(path.join(dist, 'app.js'), 'utf8'), context);
  await new Promise(resolve => setTimeout(resolve, 20));
  assert.ok(handlers['primary-action:click']);
  assert.ok(handlers['record-action:click']);
  assert.ok(calls.includes('eth_chainId'));
  assert.ok(calls.includes('eth_accounts'));
  assert.ok(calls.includes('eth_call'));
  assert.ok(!calls.includes('eth_requestAccounts'));
  assert.ok(!calls.includes('eth_sendTransaction'));
});

for (const scenario of [
  'confirmed', 'pending', 'uncertain', 'stale', 'changed account',
  'non-holder', 'duplicate', 'simulation rejected', 'gas above bound', 'wallet declined',
]) {
test(`receipt records reviewed calldata and handles ${scenario} safely`, async () => {
  const config = loadConfig();
  const participant = '0x' + '34'.repeat(20);
  const calls = [];
  const handlers = {};
  const rows = new Map();
  function element(id) {
    return {
      id,
      textContent: '',
      hidden: id === 'record-action' || id === 'digest-panel',
      disabled: false,
      className: '',
      classList: {add() {}, remove() {}},
      style: {setProperty() {}},
      addEventListener(name, fn) { handlers[`${id}:${name}`] = fn; },
      querySelector() { return {textContent: ''}; },
    };
  }
  const elements = new Map();
  const get = id => elements.get(id) || (elements.set(id, element(id)), elements.get(id));
  const word = value => '0x' + BigInt(value).toString(16).padStart(64, '0');
  const addressWord = address => '0x' + '0'.repeat(24) + address.slice(2).toLowerCase();
  let now = Date.now();
  const block = {number: '0x64', hash: '0x' + 'ab'.repeat(32), timestamp: '0x' + Math.floor(now / 1000).toString(16)};
  const mined = {number: '0x65', hash: '0x' + 'ef'.repeat(32), timestamp: block.timestamp};
  const txHash = '0x' + 'cd'.repeat(32);
  const saved = new Map();
  let account = participant;
  let sent;
  let finalized = false;
  const provider = {
    async request({method, params = []}) {
      calls.push({method, params});
      if (method === 'eth_chainId') return config.chainIdHex;
      if (method === 'eth_accounts' || method === 'eth_requestAccounts') return [account];
      if (method === 'eth_getBlockByNumber') return params[0] === mined.number ||
        (params[0] === 'finalized' && finalized) ? mined : block;
      if (method === 'eth_getCode') return config.expectedRuntime;
      if (method === 'eth_estimateGas') return scenario === 'gas above bound' ? '0x493e1' : '0x186a0';
      if (method === 'eth_sendTransaction') {
        assert.ok([...saved.values()].some(value => JSON.parse(value).hash === null));
        sent = params[0];
        if (scenario === 'uncertain') throw new Error('Connection lost');
        if (scenario === 'wallet declined') throw Object.assign(new Error('Rejected'), {code: 4001});
        finalized = scenario === 'confirmed';
        return txHash;
      }
      if (method === 'eth_getTransactionReceipt') {
        return {status: '0x1', blockNumber: mined.number, blockHash: mined.hash, transactionHash: txHash};
      }
      if (method === 'eth_getTransactionByHash') {
        return {...sent, input: sent.data, hash: txHash, blockHash: mined.hash};
      }
      if (method === 'eth_call') {
        const tx = params[0];
        const data = tx.data.toLowerCase();
        if (data === config.selectors['agentIdRegistry()'].toLowerCase()) return addressWord(config.officialRegistry);
        if (data === config.selectors['BSC_AGENT_ID_REGISTRY()'].toLowerCase()) return addressWord(config.officialRegistry);
        if (data === config.selectors['BSC_MAINNET_CHAIN_ID()'].toLowerCase()) return word(56);
        if (data === config.selectors['receiptCount()'].toLowerCase()) return word(0);
        if (data === config.selectors['uniqueAgentCount()'].toLowerCase()) return word(0);
        if (data.startsWith(config.selectors['balanceOf(address)'].toLowerCase())) return word(scenario === 'non-holder' ? 0 : 1);
        if (data.startsWith(config.selectors['isAgentIdHolder(address)'].toLowerCase())) return word(scenario === 'non-holder' ? 0 : 1);
        if (data.startsWith(config.selectors['hasParticipated(address)'].toLowerCase())) return word(0);
        if (data.startsWith(config.selectors['recorded(address,bytes32)'].toLowerCase())) return word(scenario === 'duplicate' ? 1 : 0);
        if (data.startsWith(config.selectors['recordAssessment(bytes32,bytes32)'].toLowerCase())) {
          if (scenario === 'simulation rejected' && params[1] === 'latest') {
            throw new Error('Simulation rejected by wallet provider');
          }
          return '0x';
        }
      }
      throw new Error(`Unexpected method: ${method}`);
    },
    on() {},
  };
  const context = {
    globalThis: null,
    ethereum: provider,
    VERIABSTAIN_CONFIG: config,
    VeriAbstainCore: core,
    document: {
      getElementById: get,
      querySelector(selector) {
        if (!rows.has(selector)) rows.set(selector, element(selector));
        return rows.get(selector);
      },
    },
    Date: {now: () => now},
    navigator: {locks: {request: (_key, _options, handler) => handler({})}},
    localStorage: {
      getItem: key => saved.get(key) ?? null,
      setItem: (key, value) => saved.set(key, value),
      removeItem: key => saved.delete(key),
    },
    setTimeout,
    clearTimeout,
    console,
    Promise,
    BigInt,
  };
  context.globalThis = context;
  vm.runInNewContext(fs.readFileSync(path.join(dist, 'app.js'), 'utf8'), context);
  await new Promise(resolve => setTimeout(resolve, 20));

  await handlers['primary-action:click']();
  if (scenario === 'non-holder' || scenario === 'duplicate') {
    assert.equal(get('record-action').hidden, true);
    assert.equal(get('digest-panel').hidden, true);
    assert.match(get('status-message').textContent, /does not currently hold|already recorded/);
    await handlers['record-action:click']();
    assert.ok(!calls.some(call => call.method === 'eth_sendTransaction'));
    assert.equal(saved.size, 0);
    return;
  }
  assert.equal(get('record-action').hidden, false);
  assert.equal(get('digest-panel').hidden, false);
  assert.match(get('status-message').textContent, /Integrity matched/);
  assert.ok(!calls.some(call => call.method === 'eth_sendTransaction'));
  const expectedCalldata = core.buildRecordCalldata(
    config.selectors['recordAssessment(bytes32,bytes32)'],
    get('evidence-digest').textContent,
    get('assessment-digest').textContent,
  );

  if (scenario === 'stale') now += 301_000;
  if (scenario === 'changed account') account = '0x' + '56'.repeat(20);
  await handlers['record-action:click']();
  const sends = calls.filter(call => call.method === 'eth_sendTransaction');
  if (['stale', 'changed account', 'simulation rejected', 'gas above bound'].includes(scenario)) {
    assert.equal(sends.length, 0);
    assert.equal(saved.size, 0);
    assert.match(get('status-message').textContent, /Run a new integrity check|Simulation rejected|Gas estimate/);
    return;
  }
  assert.equal(sends.length, 1);
  assert.equal(sent.from, participant);
  assert.equal(sent.to, config.contractAddress);
  assert.equal(sent.value, '0x0');
  assert.equal(sent.data, expectedCalldata);
  if (scenario === 'wallet declined') {
    assert.equal(saved.size, 0);
    assert.match(get('status-message').textContent, /declined the wallet request/);
    assert.ok(!calls.some(call => call.method === 'eth_getTransactionReceipt'));
    return;
  }
  if (scenario !== 'confirmed') {
    assert.equal(saved.size, 1);
    assert.equal(get('record-action').hidden, true);
    assert.equal(get('primary-action').textContent, 'Check previous transaction');
    finalized = true;
    await handlers['primary-action:click']();
    assert.equal(calls.filter(call => call.method === 'eth_sendTransaction').length, 1);
    if (scenario === 'uncertain') {
      assert.equal(saved.size, 1);
      assert.match(get('status-message').textContent, /Review wallet activity/);
      return;
    }
  }
  assert.match(get('status-message').textContent, /Receipt confirmed/);
  assert.equal(saved.size, 0);
});
}
