(function () {
  'use strict';

  const cfg = globalThis.VERIABSTAIN_CONFIG;
  const core = globalThis.VeriAbstainCore;
  const provider = globalThis.ethereum;
  const pendingKey = 'veriabstain.pendingReceipt';
  const disconnectKey = 'veriabstain.walletDisconnected';
  const maxSnapshotAge = 300;
  const maxGasEstimate = 300_000n;
  const addressPattern = /^0x[0-9a-f]{40}$/i;
  const hashPattern = /^0x[0-9a-f]{64}$/i;
  const quantityPattern = /^0x(?:0|[1-9a-f][0-9a-f]*)$/i;
  const $ = id => document.getElementById(id);
  const state = {account: null, accounts: [], chainId: null, plan: null, busy: false, disconnected: false};

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

  async function ethCall(to, data, blockTag = 'latest', from) {
    const transaction = {to, data};
    if (from) transaction.from = from;
    return rpc('eth_call', [transaction, blockTag]);
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

  async function checkCanonical(block) {
    const current = await rpc('eth_getBlockByNumber', [block.number, false]);
    if (current?.number !== block.number || current?.hash?.toLowerCase() !== block.hash.toLowerCase()) {
      throw new Error('The snapshot changed. Run a new integrity check.');
    }
  }

  async function readCounters() {
    if (!provider?.request || state.chainId !== cfg.chainIdHex) return;
    try {
      const [receipts, unique] = await Promise.all([
        ethCall(cfg.contractAddress, cfg.selectors['receiptCount()']),
        ethCall(cfg.contractAddress, cfg.selectors['uniqueAgentCount()']),
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

  async function runAudit() {
    if (!state.account || state.chainId !== cfg.chainIdHex) throw new Error('Connect on BNB Smart Chain first');
    const account = state.account;
    resetChecks();
    setMessage('Reading one finalized BNB Chain snapshot…');
    const block = await rpc('eth_getBlockByNumber', ['finalized', false]);
    checkFreshBlock(block);
    const code = String(await rpc('eth_getCode', [cfg.contractAddress, block.number])).toLowerCase();
    const runtimeMatch = code === cfg.expectedRuntime;
    setCheck('runtime', runtimeMatch ? 'pass' : 'fail', runtimeMatch ? 'Exact match' : 'Mismatch');
    if (!runtimeMatch) throw new Error('Deployed runtime does not match the reviewed build');

    const [registryRaw, constantRaw, chainRaw, balanceRaw, holderRaw, participatedRaw] = await Promise.all([
      ethCall(cfg.contractAddress, cfg.selectors['agentIdRegistry()'], block.number),
      ethCall(cfg.contractAddress, cfg.selectors['BSC_AGENT_ID_REGISTRY()'], block.number),
      ethCall(cfg.contractAddress, cfg.selectors['BSC_MAINNET_CHAIN_ID()'], block.number),
      ethCall(cfg.officialRegistry, core.encodeAddressCall(cfg.selectors['balanceOf(address)'], account), block.number),
      ethCall(cfg.contractAddress, core.encodeAddressCall(cfg.selectors['isAgentIdHolder(address)'], account), block.number),
      ethCall(cfg.contractAddress, core.encodeAddressCall(cfg.selectors['hasParticipated(address)'], account), block.number),
    ]);
    const registry = core.decodeAddress(registryRaw).toLowerCase();
    const registryConstant = core.decodeAddress(constantRaw).toLowerCase();
    const configuredChain = core.decodeUint(chainRaw);
    const registryMatch = registry === cfg.officialRegistry.toLowerCase() && registryConstant === registry && configuredChain === 56n;
    setCheck('registry', registryMatch ? 'pass' : 'fail', registryMatch ? 'Official' : 'Mismatch');
    if (!registryMatch) throw new Error('Contract registry configuration does not match');

    const balance = core.decodeUint(balanceRaw);
    const holder = core.decodeBool(holderRaw);
    const hasParticipated = core.decodeBool(participatedRaw);
    const eligible = balance > 0n && holder;
    setCheck('holder', eligible ? 'pass' : 'fail', eligible ? `${balance} Agent ID` : 'Not eligible');
    if (!eligible) throw new Error('This wallet address does not currently hold an Agent ID. Select the address that holds it and reconnect if needed.');

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
    const duplicateRaw = await ethCall(
      cfg.contractAddress,
      core.encodeAddressBytes32Call(cfg.selectors['recorded(address,bytes32)'], account, evidenceDigest),
      block.number,
    );
    if (core.decodeBool(duplicateRaw)) throw new Error('This finalized snapshot was already recorded by this wallet');
    const calldata = core.buildRecordCalldata(cfg.selectors['recordAssessment(bytes32,bytes32)'], evidenceDigest, assessmentDigest);
    if (await ethCall(cfg.contractAddress, calldata, block.number, account) !== '0x') {
      throw new Error('Unexpected simulation response.');
    }
    await checkCanonical(block);
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

  async function reconcile(pending) {
    if (!hashPattern.test(pending.hash) || typeof pending.account !== 'string' ||
        typeof pending.calldata !== 'string') {
      throw new Error('The previous request could not be matched. Review wallet activity before retrying.');
    }
    await checkWallet(pending.account);
    const [receipt, tx, finalized] = await Promise.all([
      rpc('eth_getTransactionReceipt', [pending.hash]),
      rpc('eth_getTransactionByHash', [pending.hash]),
      rpc('eth_getBlockByNumber', ['finalized', false]),
    ]);
    if (!receipt || !tx || !quantityPattern.test(finalized?.number) ||
        !quantityPattern.test(receipt.blockNumber) || BigInt(receipt.blockNumber) > BigInt(finalized.number)) {
      setMessage(`Waiting for finality. Check again shortly. Transaction ${pending.hash}`);
      return;
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
    await checkCanonical({number: receipt.blockNumber, hash: receipt.blockHash});
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
        const transaction = {from: plan.account, to: cfg.contractAddress, data: plan.calldata, value: '0x0'};
        if (await rpc('eth_call', [transaction, 'latest']) !== '0x') {
          throw new Error('The reviewed receipt could not be simulated.');
        }
        const estimate = await rpc('eth_estimateGas', [transaction]);
        if (!quantityPattern.test(estimate) || BigInt(estimate) === 0n || BigInt(estimate) > maxGasEstimate) {
          throw new Error('Gas estimate is outside the reviewed range.');
        }
        transaction.gas = '0x' + ((BigInt(estimate) * 120n + 99n) / 100n).toString(16);
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
  bootstrap();
})();
