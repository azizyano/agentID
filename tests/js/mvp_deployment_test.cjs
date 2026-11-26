const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const root = path.resolve(__dirname, '..', '..');
const ethers = require(path.join(root, 'verification', 'wallet-tests', 'node_modules', 'ethers'));
const ganache = require(path.join(root, 'verification', 'wallet-tests', 'node_modules', 'ganache'));
const deployment = require(path.join(root, 'tools', 'prepare_mvp_deployment.cjs'));
const official = '0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F';

test('package recompiles the exact tested bytecode and constructor argument', () => {
  const prepared = deployment.preparePackage();
  const build = JSON.parse(fs.readFileSync(path.join(root, 'artifacts', 'mvp', 'contract-build.json')));
  const tested = build.contracts.VeriAbstainEvidenceRegistry;
  assert.ok(prepared.plan.deployment_data.startsWith(tested.bytecode));
  const suffix = prepared.plan.deployment_data.slice(tested.bytecode.length);
  assert.equal(suffix, official.slice(2).toLowerCase().padStart(64, '0'));
  assert.equal(ethers.getAddress('0x' + suffix.slice(24)), official);
  assert.equal(prepared.plan.unlinked_runtime_keccak256, ethers.keccak256(tested.deployedBytecode));
  assert.notEqual(prepared.plan.expected_runtime_keccak256, prepared.plan.unlinked_runtime_keccak256);
  assert.ok(prepared.plan.immutable_reference_count > 0);
  assert.equal(prepared.plan.deployment_data_keccak256, ethers.keccak256(prepared.plan.deployment_data));
});

test('verification input contains the exact source and tested settings', () => {
  const prepared = deployment.preparePackage();
  const input = JSON.parse(prepared.standardInputBytes);
  const source = fs.readFileSync(path.join(root, 'contracts', 'VeriAbstainEvidenceRegistry.sol'), 'utf8');
  assert.deepEqual(Object.keys(input.sources), ['contracts/VeriAbstainEvidenceRegistry.sol']);
  assert.equal(input.sources['contracts/VeriAbstainEvidenceRegistry.sol'].content, source);
  assert.equal(input.settings.evmVersion, 'paris');
  assert.deepEqual(input.settings.optimizer, {enabled: true, runs: 200});
  assert.equal(prepared.manifest.contract, 'contracts/VeriAbstainEvidenceRegistry.sol:VeriAbstainEvidenceRegistry');
  assert.equal(prepared.manifest.compiler_version, 'v0.8.28+commit.7893614a');
});

test('offline package has no deployer, destination, signature, or submitted action', () => {
  const {plan, manifest} = deployment.preparePackage();
  assert.equal(plan.chain_id, 56);
  assert.equal(plan.native_value_wei, 0);
  assert.equal(plan.deployer, null);
  assert.equal(plan.nonce, null);
  assert.equal(plan.expected_contract_address, null);
  assert.equal(plan.signed_transaction, null);
  assert.equal(plan.transactions_sent, 0);
  assert.equal(manifest.contract_address, null);
  assert.equal(manifest.verification_submitted, false);
  assert.equal(manifest.credentials_stored, false);
  assert.equal(manifest.transactions_sent, 0);
});

test('package files are exclusive and internally hash-bound', t => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'veriabstain-deploy-test-'));
  t.after(() => fs.rmSync(temporary, {recursive: true, force: true}));
  const output = path.join(temporary, 'package');
  const prepared = deployment.writePackage(output);
  const standard = fs.readFileSync(path.join(output, 'standard-input.json'));
  const plan = fs.readFileSync(path.join(output, 'deployment-plan.json'));
  const manifest = JSON.parse(fs.readFileSync(path.join(output, 'verification-manifest.json')));
  const sha = value => require('node:crypto').createHash('sha256').update(value).digest('hex');
  assert.equal(manifest.standard_input_sha256, sha(standard));
  assert.equal(manifest.deployment_plan_sha256, sha(plan));
  assert.equal(prepared.manifest.standard_input_sha256, manifest.standard_input_sha256);
  assert.throws(() => deployment.writePackage(output), /already exists/);
});

test('code sizes remain inside EVM limits', () => {
  const {plan} = deployment.preparePackage();
  assert.ok(plan.init_code_bytes > plan.runtime_bytes);
  assert.ok(plan.init_code_bytes <= 49_152);
  assert.ok(plan.runtime_bytes <= 24_576);
});

test('exact prepared creation data deploys the expected runtime on local chain 56', async () => {
  const eip1193 = ganache.provider({
    chain: {chainId: 56},
    logging: {quiet: true},
    wallet: {totalAccounts: 1},
  });
  try {
    const provider = new ethers.BrowserProvider(eip1193);
    provider.pollingInterval = 50;
    const signer = await provider.getSigner();
    const build = JSON.parse(fs.readFileSync(path.join(root, 'artifacts', 'mvp', 'contract-build.json')));
    await eip1193.request({
      method: 'evm_setAccountCode',
      params: [official, build.contracts.MockAgentIdRegistry.deployedBytecode],
    });
    const {plan} = deployment.preparePackage();
    const transaction = await signer.sendTransaction({data: plan.deployment_data, value: 0});
    const receipt = await transaction.wait();
    assert.ok(receipt.contractAddress);
    const runtime = await provider.getCode(receipt.contractAddress);
    assert.equal(ethers.keccak256(runtime), plan.expected_runtime_keccak256);
    const contract = new ethers.Contract(
      receipt.contractAddress,
      build.contracts.VeriAbstainEvidenceRegistry.abi,
      provider
    );
    assert.equal(await contract.agentIdRegistry(), official);
  } finally {
    await eip1193.disconnect();
  }
});
