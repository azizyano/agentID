const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..', '..');
const ethers = require(path.join(root, 'verification', 'wallet-tests', 'node_modules', 'ethers'));
const ganache = require(path.join(root, 'verification', 'wallet-tests', 'node_modules', 'ganache'));
const build = JSON.parse(fs.readFileSync(path.join(root, 'artifacts', 'mvp', 'contract-build.json')));
const receiptPlan = JSON.parse(fs.readFileSync(
  path.join(root, 'artifacts', 'mvp', 'receipt-example', 'receipt-plan.json')
));
const registryArtifact = build.contracts.MockAgentIdRegistry;
const evidenceArtifact = build.contracts.VeriAbstainEvidenceRegistry;

async function setup(chainId = 31337) {
  const eip1193 = ganache.provider({
    chain: {chainId},
    logging: {quiet: true},
    wallet: {totalAccounts: 4},
  });
  const provider = new ethers.BrowserProvider(eip1193);
  provider.pollingInterval = 50;
  const signers = await Promise.all([0, 1, 2].map(index => provider.getSigner(index)));
  const registry = await new ethers.ContractFactory(
    registryArtifact.abi,
    registryArtifact.bytecode,
    signers[0]
  ).deploy();
  await registry.waitForDeployment();
  return {eip1193, provider, signers, registry};
}

async function deployEvidence(signer, registryAddress) {
  const contract = await new ethers.ContractFactory(
    evidenceArtifact.abi,
    evidenceArtifact.bytecode,
    signer
  ).deploy(registryAddress);
  await contract.waitForDeployment();
  return contract;
}

const evidenceOne = ethers.keccak256(ethers.toUtf8Bytes('evidence-1'));
const evidenceTwo = ethers.keccak256(ethers.toUtf8Bytes('evidence-2'));
const assessment = ethers.keccak256(ethers.toUtf8Bytes('assessment'));

test('constructor rejects zero and non-contract registries', async () => {
  const {signers, eip1193} = await setup();
  const factory = new ethers.ContractFactory(evidenceArtifact.abi, evidenceArtifact.bytecode, signers[0]);
  await assert.rejects(factory.deploy(ethers.ZeroAddress));
  await assert.rejects(factory.deploy(await signers[1].getAddress()));
  await eip1193.disconnect();
});

test('BSC mainnet deployment rejects any registry except the official address', async () => {
  const {signers, registry, eip1193} = await setup(56);
  await assert.rejects(deployEvidence(signers[0], await registry.getAddress()));
  const official = '0x60B9262456dE011F7d15a54CdD8c48bAaa8B022F';
  await eip1193.request({
    method: 'evm_setAccountCode',
    params: [official, registryArtifact.deployedBytecode],
  });
  const evidence = await deployEvidence(signers[0], official);
  assert.equal(await evidence.agentIdRegistry(), official);
  await eip1193.disconnect();
});

test('non-holder and zero digests fail closed', async () => {
  const {signers, registry, eip1193} = await setup();
  const evidence = await deployEvidence(signers[0], await registry.getAddress());
  await assert.rejects(evidence.connect(signers[1]).recordAssessment(evidenceOne, assessment));
  await registry.setBalance(await signers[1].getAddress(), 1);
  await assert.rejects(evidence.connect(signers[1]).recordAssessment(ethers.ZeroHash, assessment));
  await assert.rejects(evidence.connect(signers[1]).recordAssessment(evidenceOne, ethers.ZeroHash));
  assert.equal(await evidence.receiptCount(), 0n);
  await eip1193.disconnect();
});

test('holder records a content-addressed receipt and duplicates are rejected', async () => {
  const {signers, registry, eip1193} = await setup();
  const address = await signers[1].getAddress();
  await registry.setBalance(address, 1);
  const evidence = await deployEvidence(signers[0], await registry.getAddress());
  const transaction = await evidence.connect(signers[1]).recordAssessment(evidenceOne, assessment);
  const receipt = await transaction.wait();
  const event = receipt.logs.map(log => {
    try { return evidence.interface.parseLog(log); } catch { return null; }
  }).find(item => item && item.name === 'AssessmentRecorded');
  assert.equal(event.args.agent, address);
  assert.equal(event.args.evidenceDigest, evidenceOne);
  assert.equal(event.args.assessmentDigest, assessment);
  assert.equal(event.args.receiptIndex, 1n);
  assert.equal(event.args.firstInteraction, true);
  assert.equal(await evidence.recorded(address, evidenceOne), true);
  assert.equal(await evidence.receiptCount(), 1n);
  assert.equal(await evidence.uniqueAgentCount(), 1n);
  await assert.rejects(evidence.connect(signers[1]).recordAssessment(evidenceOne, assessment));
  await eip1193.disconnect();
});

test('unique-agent count is stable across receipts and increments for another holder', async () => {
  const {signers, registry, eip1193} = await setup();
  const first = await signers[1].getAddress();
  const second = await signers[2].getAddress();
  await registry.setBalance(first, 1);
  await registry.setBalance(second, 2);
  const evidence = await deployEvidence(signers[0], await registry.getAddress());
  await (await evidence.connect(signers[1]).recordAssessment(evidenceOne, assessment)).wait();
  await (await evidence.connect(signers[1]).recordAssessment(evidenceTwo, assessment)).wait();
  await (await evidence.connect(signers[2]).recordAssessment(evidenceOne, assessment)).wait();
  assert.equal(await evidence.receiptCount(), 3n);
  assert.equal(await evidence.uniqueAgentCount(), 2n);
  await eip1193.disconnect();
});

test('current Agent ID balance is rechecked and registry errors fail closed', async () => {
  const {signers, registry, eip1193} = await setup();
  const address = await signers[1].getAddress();
  await registry.setBalance(address, 1);
  const evidence = await deployEvidence(signers[0], await registry.getAddress());
  assert.equal(await evidence.isAgentIdHolder(address), true);
  await registry.setBalance(address, 0);
  assert.equal(await evidence.isAgentIdHolder(address), false);
  await assert.rejects(evidence.connect(signers[1]).recordAssessment(evidenceOne, assessment));
  await registry.setShouldRevert(true);
  assert.equal(await evidence.isAgentIdHolder(address), false);
  await assert.rejects(evidence.connect(signers[1]).recordAssessment(evidenceOne, assessment));
  await eip1193.disconnect();
});

test('Python-prepared unsigned calldata records the exact two digests', async () => {
  const {signers, registry, eip1193} = await setup();
  const address = await signers[1].getAddress();
  await registry.setBalance(address, 1);
  const evidence = await deployEvidence(signers[0], await registry.getAddress());
  const transaction = await signers[1].sendTransaction({
    to: await evidence.getAddress(),
    data: receiptPlan.calldata,
    value: 0,
  });
  await transaction.wait();
  assert.equal(await evidence.recorded(address, receiptPlan.evidence_digest), true);
  assert.equal(await evidence.receiptCount(), 1n);
  const parsed = evidence.interface.parseTransaction({data: receiptPlan.calldata});
  assert.equal(parsed.args.evidenceDigest, receiptPlan.evidence_digest);
  assert.equal(parsed.args.assessmentDigest, receiptPlan.assessment_digest);
  await eip1193.disconnect();
});

test('public ABI exposes no owner, asset, approval, or transfer operation', () => {
  const functions = new Set(evidenceArtifact.abi.filter(item => item.type === 'function').map(item => item.name));
  for (const forbidden of ['owner', 'approve', 'transfer', 'transferFrom', 'withdraw', 'pause', 'mint']) {
    assert.equal(functions.has(forbidden), false, forbidden);
  }
  assert.deepEqual([...functions].sort(), [
    'BSC_AGENT_ID_REGISTRY',
    'BSC_MAINNET_CHAIN_ID',
    'agentIdRegistry',
    'hasParticipated',
    'isAgentIdHolder',
    'receiptCount',
    'recordAssessment',
    'recorded',
    'uniqueAgentCount',
  ].sort());
});
