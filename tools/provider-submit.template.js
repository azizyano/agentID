// Provider reviews one submit transaction; no transfers, approval, or settlement.
(async () => {
  const cfg = __CONFIG__;
  const need = (ok, message) => { if (!ok) throw new Error(message); };
  need(location.origin === 'https://united-coin-u.github.io' && navigator.locks, 'Use original HTTPS faucet tab');
  return navigator.locks.request('veriabstain:97:submit:1766', {ifAvailable:true}, async lock => {
    need(lock, 'Submission session already active');
    const E = window.ethers, wallet = window.ethereum;
    need(E && E.version.startsWith('6.') && wallet, 'MetaMask and ethers6 required');
    const rpc = (method, params=[]) => wallet.request({method,params});
    const same = (a,b) => typeof a==='string' && typeof b==='string' && a.toLowerCase()===b.toLowerCase();
    const interfaces = Object.fromEntries(Object.entries(cfg.abis).map(([k,v])=>[k,new E.Interface(v)]));
    const key='veriabstain:97:submit:1766:'+cfg.deliverableHash;
    const prior=JSON.parse(localStorage.getItem(key)||'null');
    if (prior) { console.log('EXISTING_SUBMISSION_CHECKPOINT',prior); throw new Error('Reconcile existing submission before retry'); }
    need(same(E.keccak256(E.toUtf8Bytes(cfg.resultText)),cfg.deliverableHash),'Report commitment mismatch');
    need(await rpc('eth_chainId')==='0x61','Select BSC testnet97');
    const accounts=await rpc('eth_requestAccounts');
    need(same(accounts[0],cfg.provider),'Select PROVIDER wallet ending B3c1');
    const b=await rpc('eth_getBlockByNumber',['finalized',false]);
    const now=Math.floor(Date.now()/1000);
    need(b && now-Number(BigInt(b.timestamp))>=0 && now-Number(BigInt(b.timestamp))<=120,'Stale finalized block');
    const read=async (name,method,args=[])=>interfaces[name].decodeFunctionResult(method,await rpc('eth_call',[{to:cfg[name==='token'?'payment_token':name],data:interfaces[name].encodeFunctionData(method,args)},b.number]))[0];
    for(const name of ['commerce','router','policy','payment_token'])
      need(same(E.keccak256(await rpc('eth_getCode',[cfg[name],b.number])),cfg.codeHashes[name]),'Code changed: '+name);
    for(const name of ['commerce','router']) {
      const slot=await rpc('eth_getStorageAt',[cfg[name],cfg.implementationSlot,b.number]);
      need(/^0x0{24}[0-9a-f]{40}$/i.test(slot),'Invalid implementation slot');
      const address='0x'+slot.slice(-40);
      need(same(address,cfg.implementations[name]),'Implementation changed');
      need(same(E.keccak256(await rpc('eth_getCode',[address,b.number])),cfg.codeHashes[name+'_implementation']),'Implementation code changed');
    }
    const j=await read('commerce','getJob',[cfg.jobId]);
    need(j.id===BigInt(cfg.jobId) && j.status===1n && j.budget===BigInt(cfg.budget),'Expected exact funded job1766');
    need(same(j.client,cfg.client)&&same(j.provider,cfg.provider)&&same(j.evaluator,cfg.router)&&same(j.hook,cfg.router)&&j.description===cfg.description&&j.expiredAt===BigInt(cfg.expired_at),'Job context changed');
    need(same(await read('commerce','jobPaymentToken',[cfg.jobId]),cfg.payment_token),'Wrong job token');
    need(same(await read('router','jobPolicy',[cfg.jobId]),cfg.policy),'Wrong policy');
    need(await read('commerce','paused')===false && await read('router','paused')===false,'Paused');
    need(same(await read('policy','commerce'),cfg.commerce)&&same(await read('policy','router'),cfg.router),'Wrong policy links');
    const disputeWindowSeconds=Number(await read('policy','disputeWindow'));
    need(now+disputeWindowSeconds+120<cfg.expired_at,'Submission window too short: reconcile');
    const tx={chainId:'0x61',from:cfg.provider,to:cfg.commerce,value:'0x0',data:interfaces.commerce.encodeFunctionData('submit',[cfg.jobId,cfg.deliverableHash,'0x'])};
    await rpc('eth_call',[tx,b.number]);
    need(same((await rpc('eth_getBlockByNumber',[b.number,false])).hash,b.hash),'Pinned block changed');
    need(await rpc('eth_chainId')==='0x61' && same((await rpc('eth_accounts'))[0],cfg.provider),'Account or chain changed');
    need(Math.floor(Date.now()/1000)+disputeWindowSeconds+120<cfg.expired_at,'Submission window too short');
    console.log('REVIEW PROVIDER SUBMIT',{jobId:cfg.jobId,deliverableHash:cfg.deliverableHash,nativeValue:'0',report:JSON.parse(cfg.resultText)});
    localStorage.setItem(key,JSON.stringify({state:'AWAITING_WALLET_CONFIRMATION'}));
    let hash;
    try {
      hash=await rpc('eth_sendTransaction',[tx]);
      localStorage.setItem(key,JSON.stringify({state:'SUBMITTED',hash}));
      console.log('PUBLIC_SUBMIT_JOB_TXHASH',hash);
    } catch(error) {
      if(error.code===4001 && !hash) localStorage.removeItem(key);
      throw error;
    }
  });
})();
