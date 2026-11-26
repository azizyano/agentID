// Compile reviewed upstream source only; no Hardhat config, wallets or network.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const sourceRoot = path.join(root, '.research', 'apex-contracts');
const buildRoot = path.join(root, '.research', 'source-build');
const solc = require(path.join(buildRoot, 'node_modules', 'solc'));
const sourcePath = 'contracts/AgenticCommerceUpgradeable.sol';
const source = fs.readFileSync(path.join(sourceRoot, sourcePath), 'utf8');
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const input = {
  language: 'Solidity', sources: {[sourcePath]: {content: source}},
  settings: {evmVersion: 'cancun', optimizer: {enabled: true, runs: 200}, viaIR: true,
    outputSelection: {'*': {'*': ['abi', 'evm.deployedBytecode', 'metadata'], '': ['ast']}}}
};
const output = JSON.parse(solc.compile(JSON.stringify(input), {import: name => {
  const candidates = [path.resolve(sourceRoot, name), path.resolve(buildRoot, 'node_modules', name)];
  const bases = [sourceRoot, path.join(buildRoot, 'node_modules')];
  for (let i = 0; i < candidates.length; i++) {
    if (candidates[i].startsWith(bases[i] + path.sep) && fs.existsSync(candidates[i]))
      return {contents: fs.readFileSync(candidates[i], 'utf8')};
  }
  return {error: 'Import outside reviewed source/dependency roots or missing'};
}}));
const errors = (output.errors || []).filter(error => error.severity === 'error');
if (errors.length) throw new Error(errors.map(error => error.formattedMessage).join('\n'));
const contract = output.contracts[sourcePath].AgenticCommerceUpgradeable;
const immutableNames = {};
function visit(node) {
  if (!node || typeof node !== 'object') return;
  if (node.nodeType === 'VariableDeclaration' && node.mutability === 'immutable') immutableNames[node.id] = node.name;
  for (const value of Object.values(node)) {
    if (Array.isArray(value)) value.forEach(visit); else if (value && typeof value === 'object') visit(value);
  }
}
Object.values(output.sources).forEach(item => visit(item.ast));
const result = {compiler: solc.version(), source_path: sourcePath, source_sha256: sha(source),
  compiler_file_sha256: sha(fs.readFileSync(path.join(buildRoot, 'node_modules', 'solc', 'soljson.js'))),
  package_lock_sha256: sha(fs.readFileSync(path.join(buildRoot, 'package-lock.json'))),
  settings: input.settings, immutable_names: immutableNames, contract};
fs.writeFileSync(path.join(buildRoot, 'commerce.json'), JSON.stringify(result, null, 2));
console.log(JSON.stringify({compiler: result.compiler, source_sha256: result.source_sha256,
  runtime_bytes: contract.evm.deployedBytecode.object.length / 2, immutable_names: immutableNames}));
