// Each write below opens a separate MetaMask confirmation. No key access or relay.
(async () => {
  const cfg = {"chain_id": 97, "client": "0xb16b77C16773DEF8fA279A1228Eba9308eCD7841", "provider": "0x7d5E9Fc2D79ed404fbfDe64f93b199cFCC1bB3c1", "commerce": "0xa206c0517B6371C6638CD9e4a42Cc9f02A33B0DE", "router": "0xD7d36D66d2F1B608A0F943f722D27e3744f66F25", "policy": "0xd6a4217588F6B1F5657a92A3e94E6422aD771cEA", "payment_token": "0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565", "budget": "1000000000000000000", "expired_at": 1795195025, "description": "{\"chain_id\":97,\"currency\":\"0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565\",\"negotiated_at\":1795191425,\"negotiation_hash\":\"0xbc28a7536b463b2bb53b7992935a4a7660ab2dde36a1b5387b1962d12d7f684b\",\"price\":\"1000000000000000000\",\"provider_sig\":\"0xe2f72baa89590da02950923634e4721139314b8ac26cb378049cdb104b6f0af474af25b089c8835000b00f22e1463b0fd49a6ea05487924c6af8a2dacc40a4bd1b\",\"quote_expires_at\":1795192325,\"task\":\"Read-only analysis of the client's test U allowance to the commerce proxy at a finalized BSC testnet block. Token=0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565; owner=0xb16b77C16773DEF8fA279A1228Eba9308eCD7841; spender=0xa206c0517B6371C6638CD9e4a42Cc9f02A33B0DE. Analysis only; no worker asset actions.\",\"terms\":{\"deliverables\":\"JSON: chain_id, block_number, block_hash, token, owner, spender, allowance_raw\",\"quality_standards\":\"Exact read-only allowance at one finalized BSC testnet block; include its hash.\"},\"verifying_contract\":\"0xa206c0517B6371C6638CD9e4a42Cc9f02A33B0DE\",\"version\":1}", "createData": "0x415288120000000000000000000000007d5e9fc2d79ed404fbfde64f93b199cfcc1bb3c1000000000000000000000000d7d36d66d2f1b608a0f943f722d27e3744f66f25000000000000000000000000000000000000000000000000000000006b00809100000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000d7d36d66d2f1b608a0f943f722d27e3744f66f2500000000000000000000000000000000000000000000000000000000000003df7b22636861696e5f6964223a39372c2263757272656e6379223a22307863373042383734314238423037413664363145353466643442323066323246613634384535353635222c226e65676f7469617465645f6174223a313739353139313432352c226e65676f74696174696f6e5f68617368223a22307862633238613735333662343633623262623533623739393239333561346137363630616232646465333661316235333837623139363264313264376636383462222c227072696365223a2231303030303030303030303030303030303030222c2270726f76696465725f736967223a22307865326637326261613839353930646130323935303932333633346534373231313339333134623861633236636233373830343963646231303462366630616634373461663235623038396338383335303030623030663232653134363362306664343961366561303534383739323463366166386132646163633430613462643162222c2271756f74655f657870697265735f6174223a313739353139323332352c227461736b223a22526561642d6f6e6c7920616e616c79736973206f662074686520636c69656e7427732074657374205520616c6c6f77616e636520746f2074686520636f6d6d657263652070726f787920617420612066696e616c697a65642042534320746573746e657420626c6f636b2e20546f6b656e3d3078633730423837343142384230374136643631453534666434423230663232466136343845353536353b206f776e65723d3078623136623737433136373733444546386641323739413132323845626139333038654344373834313b207370656e6465723d3078613230366330353137423633373143363633384344396534613432436339663032413333423044452e20416e616c79736973206f6e6c793b206e6f20776f726b657220617373657420616374696f6e732e222c227465726d73223a7b2264656c6976657261626c6573223a224a534f4e3a20636861696e5f69642c20626c6f636b5f6e756d6265722c20626c6f636b5f686173682c20746f6b656e2c206f776e65722c207370656e6465722c20616c6c6f77616e63655f726177222c227175616c6974795f7374616e6461726473223a22457861637420726561642d6f6e6c7920616c6c6f77616e6365206174206f6e652066696e616c697a65642042534320746573746e657420626c6f636b3b20696e636c7564652069747320686173682e227d2c22766572696679696e675f636f6e7472616374223a22307861323036633035313742363337314336363338434439653461343243633966303241333342304445222c2276657273696f6e223a317d00", "validUntil": 1795192325, "quoteHash": "0xbc28a7536b463b2bb53b7992935a4a7660ab2dde36a1b5387b1962d12d7f684b", "providerSignature": "0xe2f72baa89590da02950923634e4721139314b8ac26cb378049cdb104b6f0af474af25b089c8835000b00f22e1463b0fd49a6ea05487924c6af8a2dacc40a4bd1b", "implementationSlot": "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc", "implementations": {"commerce": "0x55c3826B39a0F671B2C3E5D0F1372CaD0B911421", "router": "0x40c0254610d92F1EB9c2D7d5D2114Bc4c99d935E"}, "codeHashes": {"commerce": "0x1f1858db4825be798342d4c094630bf5ddc685bd802a083d8d88f15a6cdb2a89", "router": "0x1f1858db4825be798342d4c094630bf5ddc685bd802a083d8d88f15a6cdb2a89", "policy": "0xe06798700c986d4387898a1dfde009d52c75f77c7d8dd1a3e179c02d5138cb9b", "payment_token": "0xae12b1d61f7ed4febf649ccf319cb49a0e921cca3739dcb01b47d316049d46ff", "commerce_implementation": "0xb42935ea4e89b470ea5049cf66d7f1003a5c8d452aef72d78c666577e828380b", "router_implementation": "0xb523939a51d980e6bb482b6362806d06b2d75cee4e230d4ccb25f9acf0e44d18"}, "abis": {"commerce": [{"anonymous": false, "inputs": [{"indexed": true, "internalType": "uint256", "name": "jobId", "type": "uint256"}, {"indexed": true, "internalType": "address", "name": "client", "type": "address"}, {"indexed": true, "internalType": "address", "name": "provider", "type": "address"}, {"indexed": false, "internalType": "address", "name": "evaluator", "type": "address"}, {"indexed": false, "internalType": "uint256", "name": "expiredAt", "type": "uint256"}, {"indexed": false, "internalType": "address", "name": "hook", "type": "address"}], "name": "JobCreated", "type": "event"}, {"inputs": [{"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "address", "name": "evaluator", "type": "address"}, {"internalType": "uint256", "name": "expiredAt", "type": "uint256"}, {"internalType": "string", "name": "description", "type": "string"}, {"internalType": "address", "name": "hook", "type": "address"}], "name": "createJob", "outputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"}, {"inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}, {"internalType": "uint256", "name": "expectedBudget", "type": "uint256"}, {"internalType": "bytes", "name": "optParams", "type": "bytes"}], "name": "fund", "outputs": [], "stateMutability": "nonpayable", "type": "function"}, {"inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}], "name": "getJob", "outputs": [{"components": [{"internalType": "uint256", "name": "id", "type": "uint256"}, {"internalType": "address", "name": "client", "type": "address"}, {"internalType": "address", "name": "provider", "type": "address"}, {"internalType": "address", "name": "evaluator", "type": "address"}, {"internalType": "string", "name": "description", "type": "string"}, {"internalType": "uint256", "name": "budget", "type": "uint256"}, {"internalType": "uint256", "name": "expiredAt", "type": "uint256"}, {"internalType": "enum IACP.JobStatus", "name": "status", "type": "uint8"}, {"internalType": "address", "name": "hook", "type": "address"}, {"internalType": "uint256", "name": "submittedAt", "type": "uint256"}, {"internalType": "bytes32", "name": "deliverable", "type": "bytes32"}], "internalType": "struct IACP.Job", "name": "", "type": "tuple"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"internalType": "address", "name": "token", "type": "address"}], "name": "isPaymentTokenSupported", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}], "name": "jobHasBudget", "outputs": [{"internalType": "bool", "name": "hasBudget", "type": "bool"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}], "name": "jobPaymentToken", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "paused", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "paymentToken", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}, {"internalType": "uint256", "name": "amount", "type": "uint256"}, {"internalType": "bytes", "name": "optParams", "type": "bytes"}], "name": "setBudget", "outputs": [], "stateMutability": "nonpayable", "type": "function"}], "router": [{"inputs": [], "name": "commerce", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}], "name": "jobPolicy", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "paused", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"internalType": "address", "name": "policy", "type": "address"}], "name": "policyWhitelist", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}, {"internalType": "address", "name": "policy", "type": "address"}], "name": "registerJob", "outputs": [], "stateMutability": "nonpayable", "type": "function"}], "policy": [{"inputs": [], "name": "commerce", "outputs": [{"internalType": "contract IACP", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "disputeWindow", "outputs": [{"internalType": "uint64", "name": "", "type": "uint64"}], "stateMutability": "view", "type": "function"}, {"inputs": [], "name": "router", "outputs": [{"internalType": "address", "name": "", "type": "address"}], "stateMutability": "view", "type": "function"}], "token": [{"inputs": [{"internalType": "address", "name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"internalType": "address", "name": "owner", "type": "address"}, {"internalType": "address", "name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}, {"inputs": [{"internalType": "address", "name": "spender", "type": "address"}, {"internalType": "uint256", "name": "value", "type": "uint256"}], "name": "approve", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"}]}};
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
