(function () {
  'use strict';

  const cfg = globalThis.VERIABSTAIN_CONFIG;
  const core = globalThis.VeriAbstainCore;
  const provider = globalThis.ethereum;
  const publicRpcUrl = 'https://bsc-dataseed.bnbchain.org/';
  const publicRpcMethods = new Set([
    'eth_chainId', 'eth_getBlockByNumber', 'eth_getCode', 'eth_call',
    'eth_estimateGas', 'eth_gasPrice', 'eth_getTransactionReceipt', 'eth_getTransactionByHash',
  ]);
  const pendingKey = 'veriabstain.pendingReceipt';
  const disconnectKey = 'veriabstain.walletDisconnected';
  const maxSnapshotAge = 300;
  const maxGasEstimate = 300_000n;
  const weiPerBnb = 10n ** 18n;
  const addressPattern = /^0x[0-9a-f]{40}$/i;
  const agentIdNamePattern = /^[a-z0-9]{3,15}\.ai$/i;
  const hashPattern = /^0x[0-9a-f]{64}$/i;
  const quantityPattern = /^0x(?:0|[1-9a-f][0-9a-f]*)$/i;
  const $ = id => document.getElementById(id);
  const state = {account: null, accounts: [], chainId: null, plan: null, busy: false, disconnected: false};
  let agenticPlan = null;
  let agenticBusy = false;

  const elements = {
    headerWallet: $('header-wallet'),
    primary: $('primary-action'),
    record: $('record-action'),
    message: $('status-message'),
    dot: $('connection-dot'),
    connection: $('connection-label'),
    accountDetails: $('wallet-account-details'),
    accountAddress: $('wallet-account-address'),
    accountChoices: $('wallet-account-choices'),
    accountSelect: $('wallet-account-select'),
    session: $('session-id'),
    unique: $('unique-count'),
    receipts: $('receipt-count'),
    progress: $('progress-orb'),
    digestPanel: $('digest-panel'),
    evidence: $('evidence-digest'),
    assessment: $('assessment-digest'),
    block: $('audit-block'),
    agenticForm: $('agentic-prepare'),
    agenticAddress: $('agentic-address'),
    agenticPrepare: $('agentic-prepare-button'),
    agenticNameOutput: $('agentic-name-output'),
    agenticNamePrompt: $('agentic-name-prompt'),
    agenticCopyNamePrompt: $('agentic-copy-name-prompt'),
    agenticOutput: $('agentic-output'),
    agenticSummary: $('agentic-summary'),
    agenticPrompt: $('agentic-prompt'),
    agenticCopyPrompt: $('agentic-copy-prompt'),
    agenticCommand: $('agentic-preview-command'),
    agenticCopy: $('agentic-copy'),
    agenticVerifyForm: $('agentic-verify'),
    agenticHash: $('agentic-hash'),
    agenticVerify: $('agentic-verify-button'),
    agenticStatus: $('agentic-status'),
  };

  function setMessage(text, kind = '') {
    elements.message.textContent = text;
    elements.message.className = `notice${kind ? ` ${kind}` : ''}`;
  }

  function setCheck(name, status, label) {
    const row = document.querySelector(`[data-check="${name}"]`);
    row.classList.remove('pass', 'fail');
    if (status) row.classList.add(status);
    row.querySelector('.check-result').textContent = label;
  }

  function resetChecks() {
    ['runtime', 'registry', 'holder'].forEach(name => setCheck(name, '', 'Waiting'));
    elements.digestPanel.hidden = true;
    elements.record.hidden = true;
    state.plan = null;
  }

  function exposedAddresses(accounts) {
    if (!Array.isArray(accounts)) return [];
    return [...new Set(accounts
      .filter(account => typeof account === 'string' && addressPattern.test(account))
      .map(account => account.toLowerCase()))];
  }

  function applyAccounts(accounts) {
    state.accounts = exposedAddresses(accounts);
    if (!state.accounts.includes(state.account)) state.account = state.accounts[0] ?? null;
    const options = state.accounts.map(account => {
      const option = document.createElement('option');
      option.value = account;
      option.textContent = core.shorten(account, 10, 6);
      return option;
    });
    elements.accountSelect.replaceChildren(...options);
    resetChecks();
  }

  function rememberDisconnect(disconnected) {
    state.disconnected = disconnected;
    try {
      if (disconnected) globalThis.sessionStorage?.setItem(disconnectKey, '1');
      else globalThis.sessionStorage?.removeItem(disconnectKey);
    } catch {
      // The current page can still disconnect if session storage is unavailable.
    }
  }

  async function rpc(method, params = []) {
    if (!provider?.request) throw new Error('A compatible browser wallet is required');
    return provider.request({method, params});
  }

  async function publicRead(method, params = []) {
    if (!publicRpcMethods.has(method)) throw new Error('Only read-only chain requests are supported.');
    const response = await fetch(publicRpcUrl, {
      method: 'POST',
      credentials: 'omit',
      redirect: 'error',
      headers: {'Content-Type': 'application/json'},
      signal: globalThis.AbortSignal?.timeout?.(12_000),
      body: JSON.stringify({jsonrpc: '2.0', id: 1, method, params}),
    });
    if (!response.ok) throw new Error('BNB Chain RPC is unavailable. Try again later.');
    const reply = await response.json();
    if (reply?.jsonrpc !== '2.0' || reply.id !== 1 || reply.error || !Object.hasOwn(reply, 'result')) {
      throw new Error('BNB Chain could not complete the read or simulation.');
    }
    return reply.result;
  }

  async function ethCall(to, data, blockTag = 'latest', from, request = rpc) {
    const transaction = {to, data};
    if (from) transaction.from = from;
    return request('eth_call', [transaction, blockTag]);
  }

  function readPending() {
    const raw = localStorage.getItem(pendingKey);
    return raw === null ? null : JSON.parse(raw) || {};
  }

  function hasPending() {
    try {
      return readPending() !== null;
    } catch {
      return true;
    }
  }

  function checkFreshBlock(block) {
    if (!quantityPattern.test(block?.number) || !hashPattern.test(block?.hash) ||
        !quantityPattern.test(block?.timestamp)) throw new Error('Finalized block unavailable.');
    const age = Math.floor(Date.now() / 1000) - Number(BigInt(block.timestamp));
    if (age < -30 || age > maxSnapshotAge) {
      throw new Error('The finalized snapshot is stale. Run a new integrity check.');
    }
  }

  async function checkWallet(account) {
    const [accounts, chainId] = await Promise.all([rpc('eth_accounts'), rpc('eth_chainId')]);
    if (chainId !== cfg.chainIdHex || state.account !== account || !exposedAddresses(accounts).includes(account)) {
      throw new Error('Wallet account or network changed. Run a new integrity check.');
    }
  }

  async function checkCanonical(block, request = rpc) {
    const current = await request('eth_getBlockByNumber', [block.number, false]);
    if (current?.number !== block.number || current?.hash?.toLowerCase() !== block.hash.toLowerCase()) {
      throw new Error('The snapshot changed. Run a new integrity check.');
    }
  }

  async function readCounters(request = rpc, blockTag = 'latest') {
    if (request === rpc && (!provider?.request || state.chainId !== cfg.chainIdHex)) return;
    try {
      const [receipts, unique] = await Promise.all([
        ethCall(cfg.contractAddress, cfg.selectors['receiptCount()'], blockTag, undefined, request),
        ethCall(cfg.contractAddress, cfg.selectors['uniqueAgentCount()'], blockTag, undefined, request),
      ]);
      const receiptCount = core.decodeUint(receipts);
      const uniqueCount = core.decodeUint(unique);
      if (uniqueCount > receiptCount) throw new Error('Malformed counters');
      elements.receipts.textContent = receiptCount.toString();
      elements.unique.textContent = uniqueCount.toString();
      const progress = Math.min(Number(uniqueCount), cfg.targetUniqueAgents) / cfg.targetUniqueAgents * 360;
      elements.progress.style.setProperty('--progress', `${progress}deg`);
    } catch {
      elements.receipts.textContent = '—';
      elements.unique.textContent = '—';
    }
  }

  function renderConnection() {
    const connected = Boolean(state.account);
    const correctChain = state.chainId === cfg.chainIdHex;
    elements.dot.className = `status-dot${connected && correctChain ? ' online' : connected ? ' warning' : ''}`;
    elements.connection.textContent = connected
      ? correctChain ? `Connected · ${core.shorten(state.account)}` : 'Wrong network'
      : 'Wallet disconnected';
    elements.headerWallet.textContent = connected ? 'Disconnect' : 'Connect wallet';
    elements.accountDetails.hidden = !connected;
    elements.accountAddress.textContent = state.account ?? '';
    elements.accountChoices.hidden = !connected || state.accounts.length < 2;
    elements.accountSelect.value = state.account ?? '';
    elements.accountSelect.disabled = state.busy;
    elements.session.textContent = connected ? `SESSION ${state.account.slice(2, 8).toUpperCase()}` : 'SESSION —';
    elements.primary.textContent = !provider
      ? 'Connect with a wallet browser'
      : !connected
        ? 'Connect wallet'
        : !correctChain
          ? 'Switch to BNB Chain'
          : hasPending() ? 'Check previous transaction' : 'Run integrity check';
    elements.primary.disabled = state.busy;
    elements.headerWallet.disabled = state.busy;
  }

  async function connect() {
    if (state.busy) return;
    if (!provider?.request) {
      setMessage('Open this page in your wallet’s dApp browser or use a compatible wallet extension.', 'error');
      return;
    }
    try {
      state.busy = true;
      renderConnection();
      const accounts = await rpc('eth_requestAccounts');
      if (exposedAddresses(accounts).length === 0) throw new Error('Wallet did not expose an account');
      state.chainId = await rpc('eth_chainId');
      applyAccounts(accounts);
      rememberDisconnect(false);
      if (state.chainId !== cfg.chainIdHex) {
        setMessage('Switch to BNB Smart Chain mainnet to continue.');
      } else {
        setMessage('Confirm this is your Agent ID address, then run the integrity check.');
      }
      await readCounters();
    } catch (error) {
      setMessage(error?.code === 4001 ? 'Wallet connection was declined.' : 'Wallet connection failed. No transaction was sent.', 'error');
    } finally {
      state.busy = false;
      renderConnection();
    }
  }

  function toggleWallet() {
    if (state.busy) return;
    if (!state.account) return connect();
    rememberDisconnect(true);
    applyAccounts([]);
    renderConnection();
    setMessage('Disconnected from VeriAbstain. To switch accounts, select the Agent ID address in your wallet and reconnect.');
  }

  function selectAccount() {
    const account = elements.accountSelect.value;
    if (state.busy || state.disconnected || !state.accounts.includes(account)) return;
    state.account = account;
    resetChecks();
    renderConnection();
    setMessage('Wallet account selected. Run a new integrity check.');
  }

  async function switchNetwork() {
    try {
      state.busy = true;
      renderConnection();
      await rpc('wallet_switchEthereumChain', [{chainId: cfg.chainIdHex}]);
      state.chainId = await rpc('eth_chainId');
      resetChecks();
      setMessage(state.chainId === cfg.chainIdHex ? 'BNB Chain selected. Run the integrity check.' : 'BNB Chain was not selected.');
      await readCounters();
    } catch (error) {
      setMessage(error?.code === 4001 ? 'Network switch was declined.' : 'Could not switch network automatically. Select BNB Smart Chain in your wallet.', 'error');
    } finally {
      state.busy = false;
      renderConnection();
    }
  }

  async function inspectReceipt(account, request, reportCheck = () => {}) {
    if (await request('eth_chainId') !== cfg.chainIdHex) throw new Error('BNB Smart Chain mainnet is required.');
    const call = (to, data, blockTag, from) => ethCall(to, data, blockTag, from, request);
    const block = await request('eth_getBlockByNumber', ['finalized', false]);
    checkFreshBlock(block);
    const code = String(await request('eth_getCode', [cfg.contractAddress, block.number])).toLowerCase();
    const runtimeMatch = code === cfg.expectedRuntime;
    reportCheck('runtime', runtimeMatch ? 'pass' : 'fail', runtimeMatch ? 'Exact match' : 'Mismatch');
    if (!runtimeMatch) throw new Error('Deployed runtime does not match the reviewed build');

    const [registryRaw, constantRaw, chainRaw, balanceRaw, holderRaw, participatedRaw] = await Promise.all([
      call(cfg.contractAddress, cfg.selectors['agentIdRegistry()'], block.number),
      call(cfg.contractAddress, cfg.selectors['BSC_AGENT_ID_REGISTRY()'], block.number),
      call(cfg.contractAddress, cfg.selectors['BSC_MAINNET_CHAIN_ID()'], block.number),
      call(cfg.officialRegistry, core.encodeAddressCall(cfg.selectors['balanceOf(address)'], account), block.number),
      call(cfg.contractAddress, core.encodeAddressCall(cfg.selectors['isAgentIdHolder(address)'], account), block.number),
      call(cfg.contractAddress, core.encodeAddressCall(cfg.selectors['hasParticipated(address)'], account), block.number),
    ]);
    const registry = core.decodeAddress(registryRaw).toLowerCase();
    const registryConstant = core.decodeAddress(constantRaw).toLowerCase();
    const configuredChain = core.decodeUint(chainRaw);
    const registryMatch = registry === cfg.officialRegistry.toLowerCase() && registryConstant === registry && configuredChain === 56n;
    reportCheck('registry', registryMatch ? 'pass' : 'fail', registryMatch ? 'Official' : 'Mismatch');
    if (!registryMatch) throw new Error('Contract registry configuration does not match');

    const balance = core.decodeUint(balanceRaw);
    const holder = core.decodeBool(holderRaw);
    const hasParticipated = core.decodeBool(participatedRaw);
    const eligible = balance > 0n && holder;
    reportCheck('holder', eligible ? 'pass' : 'fail', eligible ? `${balance} Agent ID` : 'Not eligible');
    if (!eligible) throw new Error('This wallet address does not currently hold an Agent ID. Use the address that holds it.');

    const evidencePayload = {
      schema_version: 1,
      domain: cfg.evidenceDomain,
      participant: account.toLowerCase(),
      subject: {
        chain_id: cfg.chainId,
        contract: cfg.contractAddress.toLowerCase(),
        expected_runtime_keccak256: cfg.expectedRuntimeKeccak256,
        official_agent_id_registry: cfg.officialRegistry.toLowerCase(),
      },
      observation: {
        block_number: Number(BigInt(block.number)),
        block_hash: block.hash.toLowerCase(),
        block_timestamp: Number(BigInt(block.timestamp)),
        assurance: 'RPC_FINALIZED_READ',
      },
      checks: {
        exact_runtime: true,
        official_registry_binding: true,
        current_agent_id_holder: true,
      },
    };
    const evidenceDigest = await core.sha256Hex(evidencePayload);
    const assessmentPayload = {
      schema_version: 1,
      domain: cfg.assessmentDomain,
      evidence_digest: evidenceDigest,
      result: 'INTEGRITY_MATCHED',
      current_use_allowed: false,
      execution_authorized: false,
      native_value_wei: 0,
    };
    const assessmentDigest = await core.sha256Hex(assessmentPayload);
    const duplicateRaw = await call(
      cfg.contractAddress,
      core.encodeAddressBytes32Call(cfg.selectors['recorded(address,bytes32)'], account, evidenceDigest),
      block.number,
    );
    if (core.decodeBool(duplicateRaw)) throw new Error('This finalized snapshot was already recorded by this wallet');
    const calldata = core.buildRecordCalldata(cfg.selectors['recordAssessment(bytes32,bytes32)'], evidenceDigest, assessmentDigest);
    if (await call(cfg.contractAddress, calldata, block.number, account) !== '0x') {
      throw new Error('Unexpected simulation response.');
    }
    await checkCanonical(block, request);
    return {account, block, calldata, evidenceDigest, assessmentDigest, hasParticipated};
  }

  async function runAudit() {
    if (!state.account || state.chainId !== cfg.chainIdHex) throw new Error('Connect on BNB Smart Chain first');
    const account = state.account;
    resetChecks();
    setMessage('Reading one finalized BNB Chain snapshot…');
    const {block, calldata, evidenceDigest, assessmentDigest, hasParticipated} =
      await inspectReceipt(account, rpc, setCheck);
    await checkWallet(account);
    state.plan = {account, block, calldata};
    elements.evidence.textContent = evidenceDigest;
    elements.assessment.textContent = assessmentDigest;
    elements.block.textContent = `${Number(BigInt(block.number)).toLocaleString()} · ${core.shorten(block.hash, 10, 8)}`;
    elements.digestPanel.hidden = false;
    elements.record.hidden = false;
    setMessage(hasParticipated ? 'Integrity matched. This wallet has participated before; another receipt will not increase the unique-holder count.' : 'Integrity matched. Review and record your first Agent ID receipt.', 'success');
    return state.plan;
  }

  async function auditAction() {
    if (state.busy) return;
    if (!provider?.request || !state.account) return connect();
    if (state.chainId !== cfg.chainIdHex) return switchNetwork();
    try {
      state.busy = true;
      renderConnection();
      if (hasPending()) {
        await withReceiptLock(async () => {
          const pending = readPending();
          if (pending) await reconcile(pending);
        });
      } else {
        await runAudit();
      }
    } catch (error) {
      setMessage(error?.message || 'Integrity check failed closed.', 'error');
    } finally {
      state.busy = false;
      renderConnection();
    }
  }

  async function withReceiptLock(action) {
    if (!globalThis.navigator?.locks?.request) {
      throw new Error('Open the console in a secure browser that supports Web Locks.');
    }
    return navigator.locks.request(pendingKey, {ifAvailable: true}, lock => {
      if (!lock) throw new Error('A receipt check or wallet request is already open in another tab.');
      return action();
    });
  }

  async function inspectRecordedTransaction(pending, request) {
    const [receipt, tx, finalized] = await Promise.all([
      request('eth_getTransactionReceipt', [pending.hash]),
      request('eth_getTransactionByHash', [pending.hash]),
      request('eth_getBlockByNumber', ['finalized', false]),
    ]);
    if (!receipt || !tx || !quantityPattern.test(finalized?.number) ||
        !quantityPattern.test(receipt.blockNumber) || BigInt(receipt.blockNumber) > BigInt(finalized.number)) {
      return null;
    }
    if (receipt.transactionHash?.toLowerCase() !== pending.hash.toLowerCase() ||
        tx.hash?.toLowerCase() !== pending.hash.toLowerCase() ||
        !hashPattern.test(receipt.blockHash) || tx.blockHash !== receipt.blockHash ||
        tx.from?.toLowerCase() !== pending.account.toLowerCase() ||
        tx.to?.toLowerCase() !== cfg.contractAddress.toLowerCase() ||
        tx.input?.toLowerCase() !== pending.calldata.toLowerCase() ||
        tx.value !== '0x0' || !['0x0', '0x1'].includes(receipt.status)) {
      throw new Error('The prior transaction could not be reconciled with your reviewed receipt.');
    }
    await checkCanonical({number: receipt.blockNumber, hash: receipt.blockHash}, request);
    return receipt;
  }

  async function reconcile(pending) {
    if (!hashPattern.test(pending.hash) || typeof pending.account !== 'string' ||
        typeof pending.calldata !== 'string') {
      throw new Error('The previous request could not be matched. Review wallet activity before retrying.');
    }
    await checkWallet(pending.account);
    const receipt = await inspectRecordedTransaction(pending, rpc);
    if (!receipt) {
      setMessage(`Waiting for finality. Check again shortly. Transaction ${pending.hash}`);
      return;
    }
    await checkWallet(pending.account);
    localStorage.removeItem(pendingKey);
    resetChecks();
    if (receipt.status === '0x0') {
      setMessage('The transaction reverted and is finalized. You can run a fresh check.', 'error');
      return;
    }
    setMessage(`Receipt confirmed in finalized block ${BigInt(receipt.blockNumber).toLocaleString()}.`, 'success');
    await readCounters();
  }

  async function recheckSimulation(plan, request) {
    const transaction = {from: plan.account, to: cfg.contractAddress, data: plan.calldata, value: '0x0'};
    if (await request('eth_call', [transaction, 'latest']) !== '0x') {
      throw new Error('The reviewed receipt could not be simulated.');
    }
    const estimate = await request('eth_estimateGas', [transaction]);
    if (!quantityPattern.test(estimate) || BigInt(estimate) === 0n || BigInt(estimate) > maxGasEstimate) {
      throw new Error('Gas estimate is outside the reviewed range.');
    }
    return {transaction, estimate: BigInt(estimate)};
  }

  function agenticStatus(message, kind = '') {
    elements.agenticStatus.textContent = message;
    elements.agenticStatus.className = `notice${kind ? ' ' + kind : ''}`;
  }

  function setAgenticBusy(busy) {
    agenticBusy = busy;
    elements.agenticAddress.disabled = busy;
    elements.agenticPrepare.disabled = busy;
    elements.agenticVerify.disabled = busy;
    elements.agenticHash.disabled = busy;
    elements.agenticCopyPrompt.disabled = busy || !agenticPlan;
    elements.agenticCopy.disabled = busy || !agenticPlan;
  }

  function resetAgenticPlan() {
    agenticPlan = null;
    elements.agenticNameOutput.hidden = true;
    elements.agenticNamePrompt.value = '';
    elements.agenticOutput.hidden = true;
    elements.agenticPrompt.value = '';
    elements.agenticCommand.value = '';
    elements.agenticHash.value = '';
    agenticStatus('');
  }

  function formatAgenticPrompt(plan, command, feeBnb) {
    const expiresAt = BigInt(plan.block.timestamp) + BigInt(maxSnapshotAge);
    const signature = 'recordAssessment(bytes32,bytes32)';
    return [
      'Preview one VeriAbstain integrity receipt with the official Binance Agentic Wallet tool. This message authorizes a preview only.',
      `First confirm the signed-in BNB Smart Chain Agentic Wallet address is ${plan.account}, it holds Agent ID, and Developer Mode is active. If any check fails or the official tool is unavailable, stop.`,
      `Review the deployed contract source and ABI at https://bscscan.com/address/${cfg.contractAddress}#code. The expected call is ${signature} (selector ${cfg.selectors[signature]}). It checks the sender's Agent ID and emits an AssessmentRecorded event with two public digests. Verify this against the source and decoded calldata before any approval.`,
      `The expected ABI arguments are evidenceDigest = ${plan.evidenceDigest} and assessmentDigest = ${plan.assessmentDigest}. Native value is 0 wei. Network gas is the only expected asset cost. Use this exact preview command.`,
      command,
      `VeriAbstain estimated ${feeBnb} BNB in network gas from the exact call and the BNB Chain RPC gas price. Label this as an independent estimate. It is neither a Binance quote nor a fee cap.`,
      `The VeriAbstain snapshot expires at Unix time ${expiresAt} (seconds). Show me the sender, chain, target, calldata, native value, estimated fee, simulation, risk findings, and balance, allowance and authority changes. Stop if data is missing, fields differ, either the snapshot or Binance preview has expired, a warning is present, assets change beyond gas, or requireConfirmation is not exactly true.`,
      'Wait for my separate explicit approval of this exact preview. Only then may you request confirmation in the Binance App for the same fresh preview. Do not sign a message, grant an approval, transfer assets, change settings, substitute another call or retry automatically.',
      'If submitted, return the public transaction hash so I can verify it in VeriAbstain. If the outcome is unknown, check wallet activity before considering another receipt.',
    ].join('\n\n');
  }

  async function prepareAgenticReceipt(event) {
    event.preventDefault();
    if (agenticBusy) return;
    resetAgenticPlan();
    const input = elements.agenticAddress.value.trim();
    if (agentIdNamePattern.test(input)) {
      elements.agenticNamePrompt.value =
        `Read only: use baw wallet agent-id --json to check my signed-in Binance Agentic Wallet. If its claimed Agent ID is exactly ${input.toLowerCase()}, use baw wallet address --json and return only its full public BNB Smart Chain address (chain 56). Stop if the name or chain cannot be verified. Do not look up another wallet or request any signature or transaction.`;
      elements.agenticNameOutput.hidden = false;
      return agenticStatus('Address prompt ready. Use it in Binance AI Pro to get your own BSC address.', 'success');
    }
    if (!addressPattern.test(input)) return agenticStatus('Enter your Agent ID name, like name.ai, or your full public 0x address.', 'error');
    const account = input.toLowerCase();
    setAgenticBusy(true);
    agenticStatus('Checking Agent ID eligibility and simulating the unsigned receipt…');
    try {
      const plan = await inspectReceipt(account, publicRead);
      const [{estimate}, gasPrice] = await Promise.all([
        recheckSimulation(plan, publicRead),
        publicRead('eth_gasPrice'),
      ]);
      if (typeof gasPrice !== 'string' || !quantityPattern.test(gasPrice) || gasPrice.length > 66 || BigInt(gasPrice) === 0n) {
        throw new Error('BNB Chain did not provide a usable network fee estimate.');
      }
      const feeWei = estimate * BigInt(gasPrice);
      const feeFraction = (feeWei % weiPerBnb).toString().padStart(18, '0');
      const feeBnb = `${feeWei / weiPerBnb}.${feeFraction}`.replace(/\.?0+$/, '');
      checkFreshBlock(plan.block);
      agenticPlan = plan;
      elements.agenticSummary.textContent =
        `Agent ID verified at finalized block ${BigInt(plan.block.number).toLocaleString()}. ` +
        `${plan.hasParticipated ? 'This address already counts toward the unique-holder goal. ' : ''}` +
        `BNB Smart Chain • 0 BNB sent • estimated network fee ${feeBnb} BNB (BNB Chain RPC estimate)`;
      elements.agenticCommand.value =
        `baw contract-call preview --binanceChainId ${cfg.chainId} --from ${account} --to ${cfg.contractAddress} --value 0 --inputData ${plan.calldata} --json`;
      elements.agenticPrompt.value = formatAgenticPrompt(plan, elements.agenticCommand.value, feeBnb);
      elements.agenticOutput.hidden = false;
      agenticStatus('Receipt preview prompt ready. Paste it into your Binance AI Pro chat.', 'success');
      await readCounters(publicRead, plan.block.number);
    } catch (error) {
      agenticStatus(error?.message || 'Could not prepare the receipt.', 'error');
    } finally {
      setAgenticBusy(false);
    }
  }

  async function copyAgenticText(field, label) {
    if (!field.value || agenticBusy) return;
    try {
      await navigator.clipboard.writeText(field.value);
      agenticStatus(`Copied the ${label}.`, 'success');
    } catch {
      field.select();
      agenticStatus(`Copy the selected ${label}.`);
    }
  }

  async function copyAgenticReceiptText(field, label) {
    if (!agenticPlan || agenticBusy) return;
    try {
      checkFreshBlock(agenticPlan.block);
    } catch {
      agenticStatus('The snapshot expired. Prepare a fresh preview before continuing.', 'error');
      return;
    }
    await copyAgenticText(field, label);
  }

  async function verifyAgenticReceipt(event) {
    event.preventDefault();
    if (!agenticPlan || agenticBusy) return;
    const hash = elements.agenticHash.value.trim();
    if (!hashPattern.test(hash)) return agenticStatus('Enter the public transaction hash from the approved receipt.', 'error');
    setAgenticBusy(true);
    try {
      if (await publicRead('eth_chainId') !== cfg.chainIdHex) throw new Error('BNB Smart Chain mainnet is required.');
      const receipt = await inspectRecordedTransaction({...agenticPlan, hash}, publicRead);
      if (!receipt) return agenticStatus('The transaction is not finalized yet. Check the same hash again.');
      if (receipt.status !== '0x1') return agenticStatus('The transaction reverted and did not record a receipt.', 'error');
      agenticStatus(`Receipt confirmed at finalized block ${BigInt(receipt.blockNumber).toLocaleString()}.`, 'success');
      await readCounters(publicRead, receipt.blockNumber);
    } catch (error) {
      agenticStatus(error?.message || 'Could not verify the receipt.', 'error');
    } finally {
      setAgenticBusy(false);
    }
  }

  async function recordProof() {
    if (!state.plan || state.busy) return;
    const plan = state.plan;
    try {
      state.busy = true;
      elements.record.disabled = true;
      renderConnection();
      await withReceiptLock(async () => {
        if (readPending()) throw new Error('Check the previous transaction before recording again.');
        setMessage('Rechecking the receipt you reviewed…');
        await checkWallet(plan.account);
        checkFreshBlock(plan.block);
        await checkCanonical(plan.block);
        const {transaction, estimate} = await recheckSimulation(plan, rpc);
        transaction.gas = '0x' + ((estimate * 120n + 99n) / 100n).toString(16);
        await checkWallet(plan.account);
        checkFreshBlock(plan.block);
        if (state.plan !== plan) throw new Error('Wallet context changed. Run a new integrity check.');
        const pending = {account: plan.account, calldata: plan.calldata, hash: null};
        localStorage.setItem(pendingKey, JSON.stringify(pending));
        setMessage('Review BNB mainnet, the contract address, 0 BNB value, and gas in your wallet.');
        let hash;
        try {
          hash = await rpc('eth_sendTransaction', [transaction]);
        } catch (error) {
          if (error?.code === 4001 && error.data == null) {
            localStorage.removeItem(pendingKey);
            throw new Error('You declined the wallet request.');
          }
          throw new Error('Wallet response was uncertain. Review wallet activity before retrying.');
        }
        if (!hashPattern.test(hash)) throw new Error('Wallet did not return a valid transaction hash.');
        pending.hash = hash;
        localStorage.setItem(pendingKey, JSON.stringify(pending));
        await reconcile(pending);
      });
    } catch (error) {
      setMessage(error?.message || 'Receipt could not be recorded.', 'error');
    } finally {
      if (hasPending()) resetChecks();
      state.busy = false;
      elements.record.disabled = false;
      renderConnection();
    }
  }

  async function bootstrap() {
    try {
      state.disconnected = globalThis.sessionStorage?.getItem(disconnectKey) === '1';
    } catch {
      // Some browsers disallow storage in private contexts.
    }
    renderConnection();
    if (!provider?.request) {
      setMessage('To connect, open this page in your wallet’s dApp browser or use a compatible wallet extension.');
      return;
    }
    state.busy = true;
    renderConnection();
    try {
      state.chainId = await rpc('eth_chainId');
      if (!state.disconnected) applyAccounts(await rpc('eth_accounts'));
      await readCounters();
      if (state.account && state.chainId === cfg.chainIdHex) {
        setMessage(hasPending() ? 'Check your previous wallet request before recording another receipt.' :
          'Wallet already connected. Run the finalized integrity check.');
      }
    } catch {
      setMessage('Wallet state is unavailable. No transaction request was made.', 'error');
    } finally {
      state.busy = false;
      renderConnection();
    }
    provider.on?.('accountsChanged', accounts => {
      if (state.disconnected) return;
      applyAccounts(accounts);
      setMessage(state.account ? 'Account changed. Run a new integrity check.' : 'Wallet disconnected.');
      renderConnection();
      readCounters();
    });
    provider.on?.('chainChanged', chainId => {
      state.chainId = chainId;
      resetChecks();
      if (state.disconnected) {
        readCounters();
        return;
      }
      setMessage(chainId === cfg.chainIdHex ? 'BNB Chain selected. Run a new integrity check.' : 'Select BNB Smart Chain mainnet to continue.');
      renderConnection();
      readCounters();
    });
  }

  elements.headerWallet.addEventListener('click', toggleWallet);
  elements.accountSelect.addEventListener('change', selectAccount);
  elements.primary.addEventListener('click', auditAction);
  elements.record.addEventListener('click', recordProof);
  elements.agenticForm.addEventListener('submit', prepareAgenticReceipt);
  elements.agenticAddress.addEventListener('input', resetAgenticPlan);
  elements.agenticCopyNamePrompt.addEventListener('click', () => copyAgenticText(elements.agenticNamePrompt, 'address prompt'));
  elements.agenticCopyPrompt.addEventListener('click', () => copyAgenticReceiptText(elements.agenticPrompt, 'prompt'));
  elements.agenticCopy.addEventListener('click', () => copyAgenticReceiptText(elements.agenticCommand, 'preview command'));
  elements.agenticVerifyForm.addEventListener('submit', verifyAgenticReceipt);
  bootstrap();
})();
