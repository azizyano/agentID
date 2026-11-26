// Each write below opens a separate MetaMask confirmation. No key access or relay.
(async () => {
  const cfg = __CONFIG__;
  if (!navigator.locks || location.origin !== 'https://united-coin-u.github.io')
    throw new Error('Use the HTTPS U faucet tab in a browser supporting Web Locks');
  return navigator.locks.request('veriabstain:97:session:' + cfg.quoteHash, {ifAvailable:true}, async lock => {
  if (!lock) throw new Error('A funding session is already active; do not start another');
  const wallet = window.ethereum, E = window.ethers;
  if (!wallet || !E || !E.version.startsWith('6.')) throw new Error('Use the connected U faucet tab with MetaMask and ethers6');
  const same = (a, b) => typeof a === 'string' && typeof b === 'string' && a.toLowerCase() === b.toLowerCase();
  const need = (condition, message) => { if (!condition) throw new Error(message); };
  const rpc = (method, params = []) => wallet.request({method, params});
  const abi = Object.fromEntries(Object.entries(cfg.abis).map(([k,v]) => [k, new E.Interface(v)]));
  const key = 'veriabstain:97:funding:' + cfg.quoteHash;
  let saved = JSON.parse(localStorage.getItem(key) || '{"steps":{}}');
  need(saved && typeof saved.steps === 'object', 'Corrupt session state: reconcile before retry');
  const persist = () => localStorage.setItem(key, JSON.stringify(saved));
  const now = () => Math.floor(Date.now() / 1000);
  const remaining = minimum => need(cfg.validUntil - now() >= minimum, 'Quote window too short or expired: stop and reconcile, do not fund');
  need(same(E.verifyMessage(cfg.quoteHash, cfg.providerSignature), cfg.provider), 'Provider signature mismatch');
  async function account() {
    need(await rpc('eth_chainId') === '0x61', 'Select BSC testnet97');
    const accounts = await rpc('eth_requestAccounts');
    need(accounts[0] && same(accounts[0], cfg.client), 'Select CLIENT wallet ending7841');
  }
  async function read(to, kind, method, args, block) {
    const raw = await rpc('eth_call', [{to, data: abi[kind].encodeFunctionData(method, args)}, block]);
    return abi[kind].decodeFunctionResult(method, raw)[0];
  }
  async function canonical(block) {
    const fresh = await rpc('eth_getBlockByNumber', [block.number, false]);
    need(fresh && same(fresh.hash, block.hash), 'Pinned block changed');
  }
  async function snapshot() {
    await account();
    const block = await rpc('eth_getBlockByNumber', ['finalized', false]);
    need(block && /^0x[0-9a-f]{64}$/i.test(block.hash), 'Missing finalized block');
    need(now() - Number(BigInt(block.timestamp)) >= 0 && now() - Number(BigInt(block.timestamp)) <= 120, 'Stale finalized block');
    for (const name of ['commerce','router','policy','payment_token']) {
      const code = await rpc('eth_getCode', [cfg[name], block.number]);
      need(code !== '0x' && same(E.keccak256(code), cfg.codeHashes[name]), 'Contract code changed: ' + name);
    }
    for (const name of ['commerce','router']) {
      const stored = await rpc('eth_getStorageAt', [cfg[name], cfg.implementationSlot, block.number]);
      need(/^0x0{24}[0-9a-f]{40}$/i.test(stored), 'Invalid implementation slot');
      const address = '0x' + stored.slice(-40);
      need(same(address, cfg.implementations[name]), 'Implementation changed: ' + name);
      need(same(E.keccak256(await rpc('eth_getCode', [address, block.number])), cfg.codeHashes[name + '_implementation']), 'Implementation code changed');
    }
    need(await read(cfg.commerce, 'commerce', 'paused', [], block.number) === false, 'Commerce paused');
    need(await read(cfg.router, 'router', 'paused', [], block.number) === false, 'Router paused');
    need(same(await read(cfg.router,'router','commerce',[],block.number), cfg.commerce), 'Wrong router commerce');
    need(same(await read(cfg.commerce,'commerce','paymentToken',[],block.number), cfg.payment_token), 'Wrong default token');
    need(await read(cfg.commerce,'commerce','isPaymentTokenSupported',[cfg.payment_token],block.number) === true, 'Token disabled');
    need(await read(cfg.router,'router','policyWhitelist',[cfg.policy],block.number) === true, 'Policy not whitelisted');
    need(same(await read(cfg.policy,'policy','commerce',[],block.number), cfg.commerce), 'Wrong policy commerce');
    need(same(await read(cfg.policy,'policy','router',[],block.number), cfg.router), 'Wrong policy router');
    const dispute = await read(cfg.policy,'policy','disputeWindow',[],block.number);
    need(BigInt(cfg.expired_at) > BigInt(block.timestamp) + dispute + 60n, 'Submission deadline passed');
    await canonical(block);
    return block;
  }
  async function finalizedReceipt(hash) {
    for (let i = 0; i < 60; i++) {
      const receipt = await rpc('eth_getTransactionReceipt', [hash]);
      if (receipt) {
        need(receipt.status === '0x1', 'Transaction reverted; reconcile before retry');
        const final = await rpc('eth_getBlockByNumber', ['finalized', false]);
        if (BigInt(receipt.blockNumber) <= BigInt(final.number)) {
          const block = await rpc('eth_getBlockByNumber', [receipt.blockNumber, false]);
          need(same(block.hash, receipt.blockHash), 'Receipt reorg');
          return {receipt, block};
        }
      }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    throw new Error('Transaction pending: checkpoint retained; reconcile before retry');
  }
  async function boundTransaction(hash, to, data) {
    const tx = await rpc('eth_getTransactionByHash', [hash]);
    need(tx && same(tx.from,cfg.client) && same(tx.to,to) && BigInt(tx.value) === 0n
         && same(tx.input,data), 'Recorded transaction differs from the exact approved step');
  }
  async function stage(name, to, data, minimum) {
    const prior = saved.steps[name];
    if (prior) {
      need(prior.hash, 'Ambiguous wallet request: reconcile before retry');
      const result = await finalizedReceipt(prior.hash);
      await boundTransaction(prior.hash,to,data);
      return result;
    }
    remaining(minimum);
    const block = await snapshot();
    const tx = {chainId:'0x61', from:cfg.client, to, value:'0x0', data};
    await rpc('eth_call', [tx, block.number]);
    await canonical(block);
    remaining(minimum);
    console.log('REVIEW IN METAMASK', name, {from:cfg.client, to, nativeValue:'0', jobBudgetU:'1'});
    saved.steps[name] = {state:'AWAITING_WALLET_CONFIRMATION', to, data}; persist();
    try {
      const hash = await rpc('eth_sendTransaction', [tx]);
      saved.steps[name] = {state:'SUBMITTED', hash, to, data}; persist();
      console.log('SUBMITTED', name, hash);
      const result = await finalizedReceipt(hash);
      await boundTransaction(hash,to,data);
      saved.steps[name].state = 'FINALIZED'; persist();
      return result;
    } catch (error) {
      if (error.code === 4001 && !saved.steps[name].hash) { delete saved.steps[name]; persist(); }
      // Every other unknown effect or known hash stays journaled; never retry blindly.
      throw error;
    }
  }
  await account();
  // Adopt a known legacy create hash, never create again for the same quote.
  const legacy = JSON.parse(localStorage.getItem('veriabstain:97:create:' + cfg.quoteHash) || 'null');
  if (legacy && !saved.steps.CREATE_JOB) {
    need(legacy.transactionHash, 'Existing create attempt is ambiguous');
    saved.steps.CREATE_JOB = {state:'SUBMITTED', hash:legacy.transactionHash}; persist();
  }
  if (!saved.steps.CREATE_JOB) {
    remaining(300);
    const b = await snapshot();
    need(await read(cfg.payment_token,'token','balanceOf',[cfg.client],b.number) >= BigInt(cfg.budget), 'Insufficient test U');
  }
  const creation = await stage('CREATE_JOB', cfg.commerce, cfg.createData, 300);
  const creationTx = await rpc('eth_getTransactionByHash', [saved.steps.CREATE_JOB.hash]);
  need(same(creationTx.from,cfg.client) && same(creationTx.to,cfg.commerce) && BigInt(creationTx.value) === 0n
       && same(creationTx.input,cfg.createData), 'Create transaction differs from approved intent');
  const created = creation.receipt.logs.filter(log => same(log.address,cfg.commerce)).map(log => {
    try { return abi.commerce.parseLog(log); } catch (_) { return null; }
  }).filter(event => event && event.name === 'JobCreated');
  need(created.length === 1, 'Expected one JobCreated event');
  const event = created[0].args;
  need(same(event.client,cfg.client) && same(event.provider,cfg.provider) && same(event.evaluator,cfg.router)
       && same(event.hook,cfg.router) && event.expiredAt === BigInt(cfg.expired_at), 'Wrong created job');
  const jobId = event.jobId;
  for (let pass = 0; pass < 8; pass++) {
    const b = await snapshot();
    const job = await read(cfg.commerce,'commerce','getJob',[jobId],b.number);
    need(job.id === jobId && same(job.client,cfg.client) && same(job.provider,cfg.provider)
         && same(job.evaluator,cfg.router) && same(job.hook,cfg.router) && job.description === cfg.description
         && job.expiredAt === BigInt(cfg.expired_at), 'Job context changed');
    need(same(await read(cfg.commerce,'commerce','jobPaymentToken',[jobId],b.number),cfg.payment_token), 'Wrong job token');
    const policy = await read(cfg.router,'router','jobPolicy',[jobId],b.number);
    if (job.status === 1n) {
      need(job.budget === BigInt(cfg.budget) && same(policy,cfg.policy), 'Funded context mismatch');
      need(saved.steps.FUND_JOB && saved.steps.FUND_JOB.hash, 'Funded externally: reconcile its funding timestamp');
      const funding = await finalizedReceipt(saved.steps.FUND_JOB.hash);
      await boundTransaction(saved.steps.FUND_JOB.hash,cfg.commerce,abi.commerce.encodeFunctionData('fund',[jobId,BigInt(cfg.budget),'0x']));
      need(Number(BigInt(funding.block.timestamp)) < cfg.validUntil, 'Funding occurred after quote expiry; reconcile');
      const result = {jobId:jobId.toString(), creationHash:saved.steps.CREATE_JOB.hash, fundingHash:saved.steps.FUND_JOB.hash};
      saved.completed = result; persist();
      console.log('PUBLIC_FUNDED_JOB', JSON.stringify(result)); return result;
    }
    need(job.status === 0n, 'Job is not OPEN: reconcile');
    remaining(120);
    if (same(policy,E.ZeroAddress)) {
      await stage('REGISTER_JOB',cfg.router,abi.router.encodeFunctionData('registerJob',[jobId,cfg.policy]),120); continue;
    }
    need(same(policy,cfg.policy), 'Wrong registered policy');
    const hasBudget = await read(cfg.commerce,'commerce','jobHasBudget',[jobId],b.number);
    if (!hasBudget) {
      await stage('SET_BUDGET',cfg.commerce,abi.commerce.encodeFunctionData('setBudget',[jobId,BigInt(cfg.budget),'0x']),120); continue;
    }
    need(job.budget === BigInt(cfg.budget), 'Wrong budget');
    const allowance = await read(cfg.payment_token,'token','allowance',[cfg.client,cfg.commerce],b.number);
    if (allowance !== BigInt(cfg.budget)) {
      if (allowance !== 0n) await stage('RESET_APPROVAL',cfg.payment_token,abi.token.encodeFunctionData('approve',[cfg.commerce,0n]),120);
      else await stage('APPROVE_EXACT',cfg.payment_token,abi.token.encodeFunctionData('approve',[cfg.commerce,BigInt(cfg.budget)]),120);
      continue;
    }
    need(await read(cfg.payment_token,'token','balanceOf',[cfg.client],b.number) >= BigInt(cfg.budget), 'Insufficient U');
    await stage('FUND_JOB',cfg.commerce,abi.commerce.encodeFunctionData('fund',[jobId,BigInt(cfg.budget),'0x']),120);
  }
  throw new Error('Unexpected state transition limit: stop and reconcile');
  });
})();
