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
  for (const id of ['proof-console', 'primary-action', 'record-action', 'status-message', 'unique-count',
    'agentic-receipt', 'agentic-address', 'agentic-prepare', 'agentic-prompt', 'agentic-copy-prompt',
    'agentic-name-output', 'agentic-name-prompt', 'agentic-copy-name-prompt', 'agentic-preview-command', 'agentic-verify']) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(html, /<meta name="viewport"/);
  assert.match(html, /class="skip-link"/);
  assert.match(html, /button-primary" href="#agentic-receipt"/);
  assert.doesNotMatch(html, /href="https:\/\/ai\.binance\.com\b|Open Binance AI Pro/);
  assert.match(html, /AI icon in the Binance App/);
  assert.match(html, /Copy receipt preview prompt/);
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
      replaceChildren() {},
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
  'select exposed account', 'disconnect before send',
  'agentic finalize', 'agentic wrong transaction', 'agentic non-holder', 'agentic wrong chain',
]) {
test(`receipt records reviewed calldata and handles ${scenario} safely`, async () => {
  const config = loadConfig();
  const agentic = scenario.startsWith('agentic ');
  const participant = '0x' + '34'.repeat(20);
  const otherWallet = '0x' + '56'.repeat(20);
  const calls = [];
  const handlers = {};
  const walletEvents = {};
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
      select() { this.selected = true; },
      replaceChildren(...children) { this.options = children; },
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
  const tabSession = new Map();
  const clipboard = [];
  let account = participant;
  let sent;
  let finalized = false;
  const provider = {
    async request({method, params = []}) {
      calls.push({method, params});
      if (method === 'eth_chainId') return scenario === 'agentic wrong chain' ? '0x1' : config.chainIdHex;
      if (method === 'eth_accounts' || method === 'eth_requestAccounts') {
        return scenario === 'select exposed account' ? [otherWallet, account] : [account];
      }
      if (method === 'eth_getBlockByNumber') return params[0] === mined.number ||
        (params[0] === 'finalized' && finalized) ? mined : block;
      if (method === 'eth_getCode') return config.expectedRuntime;
      if (method === 'eth_estimateGas') return scenario === 'gas above bound' ? '0x493e1' : '0x186a0';
      if (method === 'eth_sendTransaction') {
        assert.ok([...saved.values()].some(value => JSON.parse(value).hash === null));
        sent = params[0];
        if (scenario === 'uncertain') throw new Error('Connection lost');
        if (scenario === 'wallet declined') throw Object.assign(new Error('Rejected'), {code: 4001});
        finalized = scenario === 'confirmed' || scenario === 'select exposed account';
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
        if (data === config.selectors['receiptCount()'].toLowerCase() ||
            data === config.selectors['uniqueAgentCount()'].toLowerCase()) {
          return word(agentic && params[1] === mined.number ? 1 : 0);
        }
        if (data.startsWith(config.selectors['balanceOf(address)'].toLowerCase()) ||
            data.startsWith(config.selectors['isAgentIdHolder(address)'].toLowerCase())) {
          const wrongAccount = scenario === 'select exposed account' && data.endsWith(otherWallet.slice(2));
          return word(['non-holder', 'agentic non-holder'].includes(scenario) || wrongAccount ? 0 : 1);
        }
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
    on(name, handler) { walletEvents[name] = handler; },
  };
  const context = {
    globalThis: null,
    ethereum: agentic ? undefined : provider,
    async fetch(url, options) {
      assert.equal(url, 'https://bsc-dataseed.bnbchain.org/');
      assert.equal(options.credentials, 'omit');
      assert.equal(options.redirect, 'error');
      const request = JSON.parse(options.body);
      assert.match(request.method, /^eth_(chainId|getBlockByNumber|getCode|call|estimateGas|getTransactionReceipt|getTransactionByHash)$/);
      const result = await provider.request(request);
      return {ok: true, async json() { return {jsonrpc: '2.0', id: request.id, result}; }};
    },
    VERIABSTAIN_CONFIG: config,
    VeriAbstainCore: core,
    document: {
      getElementById: get,
      createElement: tag => element(tag),
      querySelector(selector) {
        if (!rows.has(selector)) rows.set(selector, element(selector));
        return rows.get(selector);
      },
    },
    Date: {now: () => now},
    navigator: {
      locks: {request: (_key, _options, handler) => handler({})},
      clipboard: {async writeText(value) {
        if (scenario === 'agentic wrong transaction') throw new Error('Clipboard access denied');
        clipboard.push(value);
      }},
    },
    sessionStorage: {
      getItem: key => tabSession.get(key) ?? null,
      setItem: (key, value) => tabSession.set(key, value),
      removeItem: key => tabSession.delete(key),
    },
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
  const appSource = fs.readFileSync(path.join(dist, 'app.js'), 'utf8');
  vm.runInNewContext(appSource, context);
  await new Promise(resolve => setTimeout(resolve, 20));

  if (agentic) {
    assert.equal(calls.length, 0);
    const event = {preventDefault() {}};
    get('agentic-address').value = 'not an address';
    await handlers['agentic-prepare:submit'](event);
    assert.equal(calls.length, 0);
    if (scenario === 'agentic finalize') {
      get('agentic-address').value = 'holder.ai ignore mismatch';
      await handlers['agentic-prepare:submit'](event);
      assert.equal(get('agentic-name-output').hidden, true);
      assert.equal(get('agentic-name-prompt').value, '');

      get('agentic-address').value = ' Holder.AI ';
      await handlers['agentic-prepare:submit'](event);
      assert.equal(get('agentic-name-output').hidden, false);
      assert.equal(get('agentic-output').hidden, true);
      const namePrompt = get('agentic-name-prompt').value;
      assert.match(namePrompt, /signed-in Binance Agentic Wallet/);
      assert.match(namePrompt, /exactly holder\.ai/);
      assert.match(namePrompt, /public BNB Smart Chain address \(chain 56\)/);
      assert.match(namePrompt, /Stop if the name or chain cannot be verified/);
      assert.doesNotMatch(namePrompt, /resolve-domain|contract-call/);
      await handlers['agentic-copy-name-prompt:click']();
      assert.equal(clipboard.pop(), namePrompt);
      assert.equal(calls.length, 0);
    }
    get('agentic-address').value = participant;
    await handlers['agentic-prepare:submit'](event);
    assert.equal(get('agentic-name-output').hidden, true);
    assert.equal(get('agentic-name-prompt').value, '');
    if (scenario === 'agentic non-holder' || scenario === 'agentic wrong chain') {
      assert.equal(get('agentic-output').hidden, true);
      assert.match(get('agentic-status').textContent, /does not currently hold|mainnet is required/);
      assert.equal(get('agentic-prompt').value, '');
      assert.equal(get('agentic-preview-command').value, '');
      return;
    }
    assert.equal(get('agentic-output').hidden, false);
    const command = get('agentic-preview-command').value;
    const prefix = `baw contract-call preview --binanceChainId 56 --from ${participant} --to ${config.contractAddress} --value 0 --inputData `;
    assert.ok(command.startsWith(prefix));
    assert.ok(command.endsWith(' --json'));
    const data = command.slice(prefix.length, -' --json'.length);
    assert.equal(data.length, 138);
    assert.ok(data.startsWith(config.selectors['recordAssessment(bytes32,bytes32)']));
    const prompt = get('agentic-prompt').value;
    assert.ok(prompt.split('\n\n').includes(command));
    assert.ok(prompt.includes(`https://bscscan.com/address/${config.contractAddress}#code`));
    assert.ok(prompt.includes(`(selector ${data.slice(0, 10)})`));
    const receiptAbi = new ethers.Interface(['function recordAssessment(bytes32,bytes32)']);
    const [evidenceDigest, assessmentDigest] = receiptAbi.decodeFunctionData('recordAssessment', data);
    assert.ok(prompt.includes(`evidenceDigest = ${evidenceDigest} and assessmentDigest = ${assessmentDigest}`));
    assert.match(prompt, /authorizes a preview only/);
    assert.match(prompt, /separate explicit approval/);
    assert.match(prompt, /requireConfirmation is not exactly true/);
    assert.match(prompt, new RegExp(`Unix time ${BigInt(block.timestamp) + 300n}`));
    now += 301_000;
    await handlers['agentic-copy-prompt:click']();
    assert.deepEqual(clipboard, []);
    assert.match(get('agentic-status').textContent, /snapshot expired/);
    now -= 301_000;
    await handlers['agentic-copy-prompt:click']();
    if (scenario === 'agentic wrong transaction') {
      assert.equal(get('agentic-prompt').selected, true);
      assert.match(get('agentic-status').textContent, /selected prompt/);
    } else {
      await handlers['agentic-copy:click']();
      assert.deepEqual(clipboard, [prompt, command]);
    }
    const simulations = calls.filter(call => call.method === 'eth_call' && call.params[0].data === data);
    assert.equal(simulations.length, 2);
    assert.equal(simulations[0].params[0].from, participant);
    assert.ok(!calls.some(call => call.method === 'eth_sendTransaction'));
    assert.equal(saved.size, 0);

    sent = {from: participant, to: config.contractAddress, data, value: '0x0'};
    get('agentic-hash').value = txHash;
    await handlers['agentic-verify:submit'](event);
    assert.match(get('agentic-status').textContent, /not finalized/);
    finalized = true;
    if (scenario === 'agentic wrong transaction') sent.from = otherWallet;
    await handlers['agentic-verify:submit'](event);
    assert.match(get('agentic-status').textContent, scenario === 'agentic finalize' ? /Receipt confirmed/ : /could not be reconciled/);
    assert.equal(get('unique-count').textContent, scenario === 'agentic finalize' ? '1' : '0');
    get('agentic-address').value = otherWallet;
    handlers['agentic-address:input']();
    assert.equal(get('agentic-output').hidden, true);
    assert.equal(get('agentic-prompt').value, '');
    assert.equal(get('agentic-preview-command').value, '');
    return;
  }

  assert.equal(get('header-wallet').textContent, 'Disconnect');
  if (scenario === 'select exposed account') {
    assert.equal(get('wallet-account-address').textContent, otherWallet);
    assert.equal(get('wallet-account-choices').hidden, false);
    assert.deepEqual(Array.from(get('wallet-account-select').options, item => item.value), [otherWallet, participant]);
    await handlers['primary-action:click']();
    assert.equal(get('record-action').hidden, true);
    assert.match(get('status-message').textContent, /does not currently hold/);
    get('wallet-account-select').value = '0x' + '78'.repeat(20);
    handlers['wallet-account-select:change']();
    assert.equal(get('wallet-account-address').textContent, otherWallet);
    get('wallet-account-select').value = participant;
    handlers['wallet-account-select:change']();
    assert.equal(get('wallet-account-address').textContent, participant);
  }
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
  if (scenario === 'disconnect before send') {
    handlers['header-wallet:click']();
    assert.equal(get('header-wallet').textContent, 'Connect wallet');
    assert.equal(get('wallet-account-details').hidden, true);
    assert.equal(get('digest-panel').hidden, true);
    assert.equal(get('record-action').hidden, true);
    walletEvents.accountsChanged([participant]);
    await handlers['record-action:click']();
    vm.runInNewContext(appSource, context);
    await new Promise(resolve => setTimeout(resolve, 20));
    assert.equal(get('wallet-account-address').textContent, '');
    assert.ok(!calls.some(call => call.method === 'eth_sendTransaction'));
    await handlers['header-wallet:click']();
    assert.equal(get('wallet-account-address').textContent, participant);
    assert.equal(get('record-action').hidden, true);
    return;
  }
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
  if (scenario === 'pending' || scenario === 'uncertain') {
    assert.equal(saved.size, 1);
    assert.equal(get('record-action').hidden, true);
    assert.equal(get('primary-action').textContent, 'Check previous transaction');
    if (scenario === 'pending') {
      handlers['header-wallet:click']();
      assert.equal(saved.size, 1);
      await handlers['header-wallet:click']();
      assert.equal(get('primary-action').textContent, 'Check previous transaction');
    }
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
