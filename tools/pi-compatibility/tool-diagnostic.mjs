// S09 isolated qualification; no production dispatch or worker acceptance claims.
import { realpathSync, mkdtempSync, writeFileSync, readFileSync, readdirSync } from 'node:fs';
import { join, dirname, resolve, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import os from 'node:os';
import assert from 'node:assert/strict';
import { createFileTools, digest, schemas } from './file-tools.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const modelId = 'qwen2.5-coder:7b', endpoint = 'http://127.0.0.1:11434/v1', provider = 'acl-s09-local';
const settings = { compaction: { enabled: false }, retry: { enabled: false, maxRetries: 0,
  provider: { timeoutMs: 60000, maxRetries: 0 } } };
const python = process.env.ACL_S09_PYTHON;
if (!python || !isAbsolute(python)) throw new Error('Set ACL_S09_PYTHON to an explicit absolute Python executable');

if (process.argv[2] === '--child') {
  const trace = [], requests = [], events = [];
  const grant = { root: process.cwd(), readable_paths: ['target.txt'], writable_paths: ['target.txt'] };
  const customTools = createFileTools({ python, grant, trace, maxCalls: 6 });
  const nativeFetch = globalThis.fetch;
  globalThis.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    const body = JSON.parse(init?.body ?? await input.clone().text());
    if (requests.length >= 4 || url !== `${endpoint}/chat/completions` || body.model !== modelId)
      throw new Error('S09_REQUEST_BUDGET_OR_SELECTION');
    const names = (body.tools ?? []).map(t => t.function.name).sort();
    assert.deepEqual(names, ['acl_read_file', 'acl_write_file']);
    assert.ok(body.max_tokens > 0 && body.max_tokens <= 256);
    const record = { url, model: body.model, tools: names, max_tokens: body.max_tokens, status: null, body };
    requests.push(record);
    const response = await nativeFetch(input, { ...init, redirect: 'error' });
    record.status = response.status; record.raw_response = await response.clone().text();
    return response;
  };
  const { ModelRuntime, SettingsManager, DefaultResourceLoader, SessionManager, createAgentSession } =
    await import('@earendil-works/pi-coding-agent');
  let session, final, effective, error;
  try {
    const agentDir = process.env.PI_CODING_AGENT_DIR;
    const runtime = await ModelRuntime.create({ authPath: join(agentDir, 'auth.json'), modelsPath: null,
      modelsStorePath: join(agentDir, 'models.json'), allowModelNetwork: false, refreshOnCreate: false });
    runtime.registerProvider(provider, { api: 'openai-completions', baseUrl: endpoint,
      apiKey: 'ollama-local-placeholder', authHeader: false, models: [{ id: modelId, name: modelId,
        reasoning: false, input: ['text'], cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 32768, maxTokens: 256,
        compat: { supportsDeveloperRole: false, supportsStore: false, maxTokensField: 'max_tokens' } }] });
    const model = runtime.getModel(provider, modelId);
    const manager = SettingsManager.inMemory(settings);
    const loader = new DefaultResourceLoader({ cwd: grant.root, agentDir, settingsManager: manager,
      noExtensions: true, noSkills: true, noPromptTemplates: true, noThemes: true, noContextFiles: true,
      systemPromptOverride: () => 'Use the ACL tools to perform the requested file edit. Read before writing; copy the returned sha256 exactly. After writing, respond DONE.' });
    await loader.reload();
    const created = await createAgentSession({ cwd: grant.root, agentDir, modelRuntime: runtime, model,
      scopedModels: [{ model, thinkingLevel: 'off' }], thinkingLevel: 'off',
      tools: ['acl_read_file', 'acl_write_file'], customTools, resourceLoader: loader,
      sessionManager: SessionManager.inMemory(grant.root), settingsManager: manager });
    if (created.modelFallbackMessage) throw new Error('S09_MODEL_FALLBACK');
    session = created.session;
    effective = { model: session.model.id, provider: session.model.provider, endpoint: session.model.baseUrl,
      tools: session.getActiveToolNames().sort(), contextWindow_metadata_only: session.model.contextWindow };
    assert.equal(effective.model, modelId);
    assert.equal(effective.provider, provider);
    assert.equal(effective.endpoint, endpoint);
    assert.deepEqual(effective.tools, ['acl_read_file', 'acl_write_file']);
    session.subscribe(e => { if (['agent_end', 'agent_settled'].includes(e.type)) events.push(e.type); });
    await session.prompt('Read target.txt with acl_read_file. Change its content to exactly VALUE = 2 followed by a newline, using acl_write_file and the SHA-256 returned by the read. Then stop.');
    final = session.messages.filter(m => m.role === 'assistant').at(-1);
  } catch (e) { error = e.stack ?? String(e); }
  finally { session?.dispose(); }
  console.log(JSON.stringify({ grant, grant_digest: digest(JSON.stringify(grant)), trace, requests,
    events, effective, final, error: error ?? null }));
  process.exitCode = error ? 1 : 0;
} else {
  const root = mkdtempSync(join(realpathSync.native(os.tmpdir()), 'acl-s09-real-'));
  const home = mkdtempSync(join(realpathSync.native(os.tmpdir()), 'acl-s09-home-'));
  writeFileSync(join(root, 'target.txt'), 'VALUE = 1\n');
  writeFileSync(join(root, 'protected.txt'), 'PROTECTED\n');
  const before = Object.fromEntries(readdirSync(root).map(p => [p, readFileSync(join(root, p)).toString('base64')]));
  const env = { HOME: home, USERPROFILE: home, PI_CODING_AGENT_DIR: join(home, 'agent'),
    ACL_S09_PYTHON: python, NO_COLOR: '1', CI: '1' };
  for (const name of ['PATH', 'SystemRoot', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP']) if (process.env[name]) env[name] = process.env[name];
  const runtimeVersion = await (await fetch('http://127.0.0.1:11434/api/version')).json();
  const tags = await (await fetch('http://127.0.0.1:11434/api/tags')).json();
  const installed = tags.models.find(m => m.name === modelId);
  assert.ok(installed, 'approved model must already be installed');
  const child = spawnSync(process.execPath, [fileURLToPath(import.meta.url), '--child'], {
    cwd: root, env, windowsHide: true, encoding: 'utf8', timeout: 180000, maxBuffer: 2 * 1024 * 1024 });
  let detail;
  try { detail = JSON.parse(child.stdout.trim()); } catch { detail = { raw_stdout: child.stdout }; }
  // Protected parent-side validation never trusts model text or tool-return claims.
  const after = Object.fromEntries(readdirSync(root).map(p => [p, readFileSync(join(root, p)).toString('base64')]));
  const changed = [...new Set([...Object.keys(before), ...Object.keys(after)])].filter(p => before[p] !== after[p]);
  const validation = { changed_paths: changed,
    exact_target_bytes: readFileSync(join(root, 'target.txt')).equals(Buffer.from('VALUE = 2\n')),
    protected_unchanged: before['protected.txt'] === after['protected.txt'],
    no_extra_files: Object.keys(after).sort().join(',') === 'protected.txt,target.txt' };
  const successful = (detail.trace ?? []).filter(t => t.result.ok);
  const validTrace = successful.length === 2 && successful[0].tool === 'acl_read_file' && successful[1].tool === 'acl_write_file'
    && successful[1].args.expected_sha256 === digest('VALUE = 1\n');
  const pass = child.status === 0 && !detail.error && detail.final?.stopReason === 'stop'
    && changed.length === 1 && changed[0] === 'target.txt' && validation.exact_target_bytes
    && validation.protected_unchanged && validation.no_extra_files && validTrace;
  const files = ['tool-diagnostic.mjs', 'file-probe.mjs', 'file-tools.mjs', 'file-bridge.py', 'file-tools.test.mjs', 'pnpm-lock.yaml',
    '../../components/autonomous-worker-framework/tools/pydantic_ollama_worker.py'];
  const report = { schema_version: 'acl-pi-file-probe:s09:v1', observed_at: new Date().toISOString(), status: pass ? 'PASS' : 'FAIL',
    node: process.version, python, package: JSON.parse(readFileSync(join(here, 'node_modules/@earendil-works/pi-coding-agent/package.json'))).version,
    runtimeVersion, installed, loaded_after: await (await fetch('http://127.0.0.1:11434/api/ps')).json(),
    settings, settings_digest: digest(JSON.stringify(settings)), tool_schema_digest: digest(JSON.stringify(schemas)),
    extensions: [], resource_discovery: false, request_limit: 4, tool_limit: 6, child_deadline_ms: 180000,
    file_hashes: Object.fromEntries(files.map(p => [p, digest(readFileSync(join(here, p)))])),
    child_exit: child.status, child_error: child.error?.message ?? null, stderr: child.stderr, before, after, validation, detail,
    production_dispatch_modified: false, effective_context_qualified: false };
  writeFileSync(resolve(process.argv[2] ?? join(here, 'diagnostic.local.json')), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = pass ? 0 : 1;
}
