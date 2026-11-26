// One exact BSC mainnet contract deployment. MetaMask confirmation is mandatory.
(async () => {
  const cfg = __CONFIG__;
  const need = (condition, message) => { if (!condition) throw new Error(message); };
  need(location.origin === cfg.origin && navigator.locks, 'Use the official HTTPS BscScan tab');
  return navigator.locks.request('veriabstain:56:deploy:' + cfg.deploymentDataHash,
    {ifAvailable: true}, async lock => {
      need(lock, 'A deployment session is already active');
      const wallet = window.ethereum;
      need(wallet, 'MetaMask not found');
      const rpc = (method, params = []) => wallet.request({method, params});
      const same = (a, b) => typeof a === 'string' && typeof b === 'string' && a.toLowerCase() === b.toLowerCase();
      const key = 'veriabstain:56:deploy:' + cfg.deploymentDataHash;
      const prior = JSON.parse(localStorage.getItem(key) || 'null');
      if (prior) {
        console.log('EXISTING_MVP_DEPLOYMENT_CHECKPOINT', prior);
        throw new Error('Reconcile the existing deployment checkpoint before any retry');
      }
      need(await rpc('eth_chainId') === cfg.chainId, 'Select BSC mainnet chain56');
      const accounts = await rpc('eth_requestAccounts');
      need(accounts[0] && same(accounts[0], cfg.deployer), 'Select DEPLOYER wallet ending7841');
      const block = await rpc('eth_getBlockByNumber', ['finalized', false]);
      const now = Math.floor(Date.now() / 1000);
      need(block && /^0x[0-9a-f]{64}$/i.test(block.hash), 'Missing finalized block');
      const age = now - Number(BigInt(block.timestamp));
      need(age >= 0 && age <= 120, 'Finalized block is stale');
      need(await rpc('eth_getCode', [cfg.registry, block.number]) !== '0x', 'Agent ID registry has no code');
      const name = await rpc('eth_call', [{to: cfg.registry, data: '0x06fdde03'}, block.number]);
      const symbol = await rpc('eth_call', [{to: cfg.registry, data: '0x95d89b41'}, block.number]);
      need(same(name, cfg.registryNameResult), 'Agent ID registry name changed');
      need(same(symbol, cfg.registrySymbolResult), 'Agent ID registry symbol changed');
      const tx = {chainId: cfg.chainId, from: cfg.deployer, value: '0x0', data: cfg.deploymentData};
      const runtime = await rpc('eth_call', [tx, block.number]);
      need(same(runtime, cfg.expectedRuntime), 'Exact deployment simulation changed');
      const estimate = BigInt(await rpc('eth_estimateGas', [tx, block.number]));
      const gasLimit = (estimate * 120n + 99n) / 100n;
      const gasPrice = BigInt(await rpc('eth_gasPrice'));
      need(gasLimit <= BigInt(cfg.maxGasLimit), 'Gas estimate exceeds reviewed limit');
      need(gasPrice <= BigInt(cfg.maxGasPriceWei), 'Gas price exceeds reviewed limit');
      const maximumCost = gasLimit * gasPrice;
      need(maximumCost <= BigInt(cfg.maxNativeCostWei), 'Maximum deployment cost exceeds approved cap');
      const balance = BigInt(await rpc('eth_getBalance', [cfg.deployer, block.number]));
      need(balance >= maximumCost, 'Insufficient BNB for deployment gas');
      const canonical = await rpc('eth_getBlockByNumber', [block.number, false]);
      need(canonical && same(canonical.hash, block.hash), 'Pinned finalized block changed');
      need(await rpc('eth_chainId') === cfg.chainId, 'Chain changed before confirmation');
      const current = await rpc('eth_accounts');
      need(current[0] && same(current[0], cfg.deployer), 'Account changed before confirmation');
      tx.gas = '0x' + gasLimit.toString(16);
      console.log('REVIEW MVP DEPLOYMENT IN METAMASK', {
        chainId: 56,
        from: cfg.deployer,
        nativeValueWei: '0',
        maximumGasCostWei: maximumCost.toString(),
        creationDataKeccak256: cfg.deploymentDataHash,
        expectedRuntimeKeccak256: cfg.expectedRuntimeHash,
      });
      localStorage.setItem(key, JSON.stringify({state: 'AWAITING_WALLET_CONFIRMATION'}));
      try {
        const hash = await rpc('eth_sendTransaction', [tx]);
        localStorage.setItem(key, JSON.stringify({state: 'SUBMITTED', hash}));
        console.log('PUBLIC_MVP_DEPLOY_TXHASH', hash);
        return hash;
      } catch (error) {
        if (error.code === 4001) localStorage.removeItem(key);
        else localStorage.setItem(key, JSON.stringify({state: 'UNKNOWN_RECONCILE_BEFORE_RETRY'}));
        throw error;
      }
    });
})();
