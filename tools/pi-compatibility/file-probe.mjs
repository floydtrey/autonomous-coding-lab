// S09 isolated qualification; no production dispatch or worker acceptance claims.
import { realpathSync, mkdtempSync, writeFileSync, readFileSync, readdirSync } from 'node:fs';
import { join, dirname, resolve, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import os from 'node:os';
import assert from 'node:assert/strict';
import { createFileTools, digest, schemas } from './file-tools.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const modelId = 'qwen3.8:27b', endpoint = 'http://127.0.0.1:11434/v1', provider = 'acl-s09-local';
const settings = { compaction: { enabled: false }, retry: { enabled: false, maxRetries: 0,
  provider: { timeoutMs: 60000, maxRetries: 0 } } };
const failure = e => ({ name: e.name, message: e.message, code: e.code ?? e.cause?.code ?? null, stack: e.stack });
const log = (type, data = {}) => console.error(JSON.stringify({ at: new Date().toISOString(), type, ...data }));
async function runtimeGet(path) {
  const r = await fetch('http://127.0.0.1:11434/api/' + path, { signal: AbortSignal.timeout(10000) });
  if (!r.ok) throw new Error('RUNTIME_HTTP_' + r.status + ': ' + path);
  return r.json();
}
const python = process.env.ACL_S09_PYTHON;


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
    body.reasoning_effort = 'none'; // Explicit per-request thinking-off for this bounded probe.
    const started = Date.now();
    const record = { sequence: requests.length + 1, started_at: new Date().toISOString(), body, url, model: body.model, tools: names, max_tokens: body.max_tokens, status: null };
    requests.push(record);
    log('request_start', { sequence: record.sequence, url, model: body.model });
    try {
      const response = await nativeFetch(input, { ...init, body: JSON.stringify(body), redirect: 'error', signal: AbortSignal.any([...(init?.signal ? [init.signal] : []), AbortSignal.timeout(60000)]) });
      record.status = response.status;
      const reader = response.clone().body.getReader();
      let bytes = 0; const chunks = [];
      while (true) { const {done, value} = await reader.read(); if (done) break;
        bytes += value.length; if (bytes > 131072) { void reader.cancel(); throw new Error('RESPONSE_LOG_LIMIT'); } chunks.push(Buffer.from(value)); }
      record.raw_response = Buffer.concat(chunks).toString('utf8');
      if (!response.ok) throw new Error('PROVIDER_HTTP_' + response.status + ': ' + record.raw_response.slice(0, 2048));
      return response;
    } catch (e) { record.error = failure(e); throw e; }
    finally { record.duration_ms = Date.now() - started; log('request_end', { sequence: record.sequence, status: record.status, duration_ms: record.duration_ms, error: record.error }); }
  };
  const { ModelRuntime, SettingsManager, DefaultResourceLoader, SessionManager, createAgentSession } =
    await import('@earendil-works/pi-coding-agent');
  let session, final, effective, error;
  try {
    log('sdk_start');
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
    session.subscribe(e => { if (e.type !== 'message_update') { const record = { at: new Date().toISOString(), type: e.type, tool: e.toolName, call_id: e.toolCallId, is_error: e.isError }; events.push(record); log('pi_event', record); } });
    await session.prompt('Read target.txt with acl_read_file. Change its content to exactly VALUE = 2 followed by a newline, using acl_write_file and the SHA-256 returned by the read. Then stop.');
    final = session.messages.filter(m => m.role === 'assistant').at(-1);
  } catch (e) { error = failure(e); log('session_error', { error }); }
  finally { session?.dispose(); }
  console.log(JSON.stringify({ grant, grant_digest: digest(JSON.stringify(grant)), trace, requests,
    events, effective, final, error: error ?? null }));
  process.exitCode = error ? 1 : 0;
} else {
 try {
  if (!python || !isAbsolute(python)) throw new Error('Set ACL_S09_PYTHON to an explicit absolute Python executable');
  const pythonCheck = spawnSync(python, ['--version'], {encoding:'utf8', timeout:10000, windowsHide:true});
  if (pythonCheck.error || pythonCheck.status !== 0) throw new Error('PYTHON_PREFLIGHT_FAILED: ' + (pythonCheck.error?.message ?? pythonCheck.stderr));
  log('preflight', { model: modelId, endpoint, python, python_version: pythonCheck.stdout.trim() });
  const root = mkdtempSync(join(realpathSync.native(os.tmpdir()), 'acl-s09-real-'));
  const home = mkdtempSync(join(realpathSync.native(os.tmpdir()), 'acl-s09-home-'));
  writeFileSync(join(root, 'target.txt'), 'VALUE = 1\n');
  writeFileSync(join(root, 'protected.txt'), 'PROTECTED\n');
  const before = Object.fromEntries(readdirSync(root).map(p => [p, readFileSync(join(root, p)).toString('base64')]));
  const env = { HOME: home, USERPROFILE: home, PI_CODING_AGENT_DIR: join(home, 'agent'),
    ACL_S09_PYTHON: python, NO_COLOR: '1', CI: '1' };
  for (const name of ['PATH', 'SystemRoot', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP']) if (process.env[name]) env[name] = process.env[name];
  const runtimeVersion = await runtimeGet('version');
  const tags = await runtimeGet('tags');
  const installed = tags.models.find(m => m.name === modelId);
  assert.ok(installed, 'approved model must already be installed');
  assert.equal(installed.details.quantization_level, 'Q4_K_M');
  assert.equal(installed.digest, '22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643', 'approved model digest changed');
  log('model_verified', { model: installed.name, digest: installed.digest });
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
  const failure_reasons = [];
  if (child.error || child.status !== 0) failure_reasons.push('CHILD_PROCESS_FAILED');
  if (detail.error) failure_reasons.push('SESSION_ERROR');
  if (detail.final?.stopReason !== 'stop') failure_reasons.push('MODEL_STOP_NOT_SUCCESS');
  if (!validTrace) failure_reasons.push('REQUIRED_NATIVE_READ_WRITE_NOT_OBSERVED');
  if (!validation.exact_target_bytes) failure_reasons.push('REQUIRED_TARGET_CONTENT_MISSING');
  if (!validation.protected_unchanged || !validation.no_extra_files || changed.some(p => p !== 'target.txt')) failure_reasons.push('WORKSPACE_SCOPE_VIOLATION');
  const files = ['file-probe.mjs', 'file-tools.mjs', 'file-bridge.py', 'file-tools.test.mjs', 'pnpm-lock.yaml',
    '../../components/autonomous-worker-framework/tools/pydantic_ollama_worker.py'];
  const report = { schema_version: 'acl-pi-file-probe:s09:v1', observed_at: new Date().toISOString(), status: pass ? 'PASS' : 'FAIL',
    failure_reasons, node: process.version, python, package: JSON.parse(readFileSync(join(here, 'node_modules/@earendil-works/pi-coding-agent/package.json'))).version,
    runtimeVersion, installed, loaded_after: await runtimeGet('ps').catch(e => ({error: failure(e)})),
    settings, settings_digest: digest(JSON.stringify(settings)), tool_schema_digest: digest(JSON.stringify(schemas)),
    extensions: [], resource_discovery: false, request_limit: 4, tool_limit: 6, child_deadline_ms: 180000,
    file_hashes: Object.fromEntries(files.map(p => [p, digest(readFileSync(join(here, p)))])),
    child_exit: child.status, child_error: child.error?.message ?? null, stderr: child.stderr, before, after, validation, detail,
    production_dispatch_modified: false, effective_context_qualified: false };
  writeFileSync(resolve(process.argv[2] ?? join(here, 'files.local.json')), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = pass ? 0 : 1;
 } catch (e) {
   const report = { schema_version: 'acl-pi-file-probe:s09:v1', observed_at: new Date().toISOString(), status:'FAIL', model:modelId, endpoint, failure_reasons:['PREFLIGHT_OR_REPORT_FAILURE'], error:failure(e) };
   writeFileSync(resolve(process.argv[2] ?? join(here, 'files.local.json')), JSON.stringify(report,null,2)+'\n');
   log('fatal', report); process.exitCode=1;
 }
}
