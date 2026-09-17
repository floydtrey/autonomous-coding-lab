// S07 only: load the installed SDK and start the CLI's version path; no session/model.
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import os from 'node:os';

const root = dirname(fileURLToPath(import.meta.url));
const entry = fileURLToPath(import.meta.resolve('@earendil-works/pi-coding-agent'));
const packageRoot = resolve(dirname(entry), '..');
const installed = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8'));
const home = mkdtempSync(join(os.tmpdir(), 'acl-s07-'));
const env = { HOME: home, USERPROFILE: home, PI_CODING_AGENT_DIR: join(home, '.pi'),
  NO_COLOR: '1', CI: '1' };
for (const name of ['SystemRoot', 'WINDIR', 'COMSPEC', 'PATH', 'TEMP', 'TMP']) {
  if (process.env[name]) env[name] = process.env[name];
}
function check(args) {
  const result = spawnSync(process.execPath, args, {
    cwd: home, env, encoding: 'utf8', timeout: 30000, maxBuffer: 131072,
    windowsHide: true,
  });
  return { exit_code: result.status, signal: result.signal,
    error: result.error?.message ?? null, stdout: result.stdout ?? '', stderr: result.stderr ?? '' };
}
const sdk = check(['--input-type=module', '-e',
  `const sdk = await import(${JSON.stringify(new URL(import.meta.resolve('@earendil-works/pi-coding-agent')).href)}); ` +
  `if (typeof sdk.createAgentSession !== 'function') throw new Error('createAgentSession export missing'); ` +
  `console.log(JSON.stringify({createAgentSession: typeof sdk.createAgentSession}));`]);
const cli = check([join(packageRoot, installed.bin.pi), '--version']);
const [major, minor] = process.versions.node.split('.').map(Number);
const nodeCompatible = major > 22 || (major === 22 && minor >= 19);
const passed = installed.name === '@earendil-works/pi-coding-agent' && installed.version === '0.85.1'
  && installed.engines.node === '>=22.19.0' && nodeCompatible
  && sdk.exit_code === 0 && cli.exit_code === 0 && cli.stdout.trim() === '0.85.1';
const report = {
  schema_version: 'acl-pi-host-compatibility:s07:v1', observed_at: new Date().toISOString(),
  status: passed ? 'PASS' : 'FAIL', platform: process.platform, architecture: process.arch,
  os_release: os.release(), node_version: process.version, node_executable: process.execPath,
  package_name: installed.name, package_version: installed.version, node_requirement: installed.engines.node,
  node_requirement_satisfied: nodeCompatible, package_root: packageRoot,
  lock_sha256: createHash('sha256').update(readFileSync(join(root, 'pnpm-lock.yaml'))).digest('hex'),
  probe_sha256: createHash('sha256').update(readFileSync(fileURLToPath(import.meta.url))).digest('hex'),
  install_policy: 'pnpm install --ignore-scripts; exact package pin and committed lockfile',
  isolated_home: home, sdk_import: sdk, cli_version: cli,
  model_session_created: false, model_request_made: false, production_dispatch_modified: false,
};
const output = resolve(process.argv[2] ?? join(root, 'evidence.local.json'));
writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
process.exitCode = passed ? 0 : 1;
