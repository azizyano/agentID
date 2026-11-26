// Review request.json first. This requests a public job-quote signature only.
(async () => {
  const expected = "0x7d5E9Fc2D79ed404fbfDe64f93b199cFCC1bB3c1";
  const expires = 1795192325;
  const message = "0xbc28a7536b463b2bb53b7992935a4a7660ab2dde36a1b5387b1962d12d7f684b";
  const provider = window.ethereum;
  if (!provider) throw new Error('MetaMask provider not found');
  if (Date.now() / 1000 >= expires) throw new Error('Quote expired; stop and request a fresh unsigned quote');
  if (await provider.request({method: 'eth_chainId'}) !== '0x61') throw new Error('Select BSC testnet 97');
  const accounts = await provider.request({method: 'eth_requestAccounts'});
  if (!accounts[0] || accounts[0].toLowerCase() !== expected.toLowerCase())
    throw new Error('Select the provider wallet ending B3c1 in MetaMask');
  console.log('Provider quote: 1 test U; read-only allowance analysis; no asset action. Message:', message);
  const hex = '0x' + Array.from(new TextEncoder().encode(message), b => b.toString(16).padStart(2, '0')).join('');
  const signature = await provider.request({method: 'personal_sign', params: [hex, expected]});
  console.log('PUBLIC_PROVIDER_SIGNATURE', signature);
  return signature;
})();
