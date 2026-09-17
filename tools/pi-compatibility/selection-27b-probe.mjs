// S08 qualification only. No tools, persisted sessions, resource discovery, or production dispatch.
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import os from 'node:os';

const root = dirname(fileURLToPath(import.meta.url));
const modelId = 'qwen3.8:27b';
const baseUrl = 'http://127.0.0.1:11434/v1';
const provider = 'acl-s08-local';
const settings = { compaction: { enabled: false }, retry: { enabled: false,
  maxRetries: 0, provider: { timeoutMs: 60000, maxRetries: 0 } } };
const hash = value => createHash('sha256').update(value).digest('hex');
const cases = [
  { name: 'exact_pair', model: modelId, endpoint: baseUrl, expectSuccess: true },
  { name: 'wrong_model', model: 'acl-s08-nonexistent-model:missing', endpoint: baseUrl, expectSuccess: false },
  { name: 'wrong_endpoint', model: modelId, endpoint: 'http://127.0.0.1:11434/acl-s08-invalid/v1', expectSuccess: false },
];

if (process.argv[2] === '--child') {
  const selected = cases.find(c => c.name === process.argv[3]);
  if (!selected) throw new Error('unknown probe case');
  const requests = [];
  const nativeFetch = globalThis.fetch;
  globalThis.fetch = async (input, init) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    const body = init?.body ?? (input instanceof Request ? await input.clone().text() : undefined);
    const parsed = typeof body === 'string' && body ? JSON.parse(body) : null;
    const item = { url, method: init?.method ?? input.method ?? 'GET', model: parsed?.model ?? null,
      max_tokens: parsed?.max_tokens ?? parsed?.max_completion_tokens ?? null, status: null };
    requests.push(item);
    // Observe and constrain the actual SDK transport, including any attempted fallback.
    if (url !== `${selected.endpoint}/chat/completions` || parsed?.model !== selected.model)
      throw new Error('S08_TRANSPORT_SELECTION_MISMATCH');
    parsed.reasoning_effort = 'none';
    const response = await nativeFetch(input, { ...init, body: JSON.stringify(parsed), redirect: 'error' });
    item.status = response.status;
    return response;
  };
  const { createAgentSession, DefaultResourceLoader, ModelRuntime, SessionManager, SettingsManager } =
    await import('@earendil-works/pi-coding-agent');
  const cwd = process.cwd();
  const agentDir = join(cwd, 'agent');
  let session;
  let error = null;
  let effective = null;
  let final = null;
  const events = [];
  try {
    const runtime = await ModelRuntime.create({ authPath: join(agentDir, 'auth.json'),
      modelsPath: null, modelsStorePath: join(agentDir, 'models-cache.json'),
      allowModelNetwork: false, refreshOnCreate: false, signal: AbortSignal.timeout(10000) });
    runtime.registerProvider(provider, { api: 'openai-completions', baseUrl: selected.endpoint,
      apiKey: 'ollama-local-placeholder', authHeader: false, models: [{ id: selected.model,
        name: selected.model, reasoning: false, input: ['text'],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 32768, maxTokens: 32,
        compat: { supportsDeveloperRole: false, supportsStore: false, maxTokensField: 'max_tokens' } }] });
    const model = runtime.getModel(provider, selected.model);
    if (!model) throw new Error('exact registered model missing');
    const manager = SettingsManager.inMemory(settings);
    const loader = new DefaultResourceLoader({ cwd, agentDir, settingsManager: manager,
      noExtensions: true, noSkills: true, noPromptTemplates: true, noThemes: true,
      noContextFiles: true, systemPromptOverride: () => 'Reply with the requested short literal text.' });
    await loader.reload();
    const created = await createAgentSession({ cwd, agentDir, modelRuntime: runtime, model,
      thinkingLevel: 'off', scopedModels: [{ model, thinkingLevel: 'off' }],
      noTools: 'all', tools: [], customTools: [], resourceLoader: loader,
      sessionManager: SessionManager.inMemory(cwd), settingsManager: manager });
    session = created.session;
    if (created.modelFallbackMessage) throw new Error(`fallback: ${created.modelFallbackMessage}`);
    effective = { id: session.model.id, provider: session.model.provider, api: session.model.api,
      baseUrl: session.model.baseUrl, contextWindow_metadata_only: session.model.contextWindow,
      maxTokens: session.model.maxTokens, tools: session.getActiveToolNames() };
    if (effective.id !== selected.model || effective.provider !== provider || effective.baseUrl !== selected.endpoint
        || effective.tools.length) throw new Error('effective selection differs');
    session.subscribe(event => { if (['agent_end', 'agent_settled'].includes(event.type)) events.push(event.type); });
    await session.prompt('Reply with exactly ACL_S08_OK.');
    const last = session.messages.filter(m => m.role === 'assistant').at(-1);
    final = last ? { model: last.model, provider: last.provider, stopReason: last.stopReason,
      errorMessage: last.errorMessage ?? null, content: last.content, usage: last.usage } : null;
  } catch (failure) { error = failure.stack ?? String(failure); }
  finally { session?.dispose(); }
  const success = !error && final?.stopReason === 'stop' && final?.model === selected.model
    && final?.provider === provider && final.content.some(c => c.type === 'text' && c.text.includes('ACL_S08_OK'));
  const verified = requests.length === 1 && requests[0].url === `${selected.endpoint}/chat/completions`
    && requests[0].model === selected.model && requests[0].max_tokens === 32
    && (selected.expectSuccess ? success && requests[0].status === 200 : !success && requests[0].status === 404);
  console.log(JSON.stringify({ ...selected, verified, success, effective, requests, final, events, error }));
  process.exitCode = verified ? 0 : 1;
} else {
  const before = await Promise.all(['version', 'tags', 'ps'].map(async name => {
    const response = await fetch(`http://127.0.0.1:11434/api/${name}`, { signal: AbortSignal.timeout(5000) });
    if (!response.ok) throw new Error(`runtime ${name} unavailable`);
    return response.json();
  }));
  const installedModel = before[1].models.find(m => m.name === modelId);
  if (!installedModel) throw new Error('approved model is not installed; no automatic pull');
  const results = [];
  for (const item of cases) {
    const home = mkdtempSync(join(os.tmpdir(), 'acl-s08-'));
    const env = { HOME: home, USERPROFILE: home, PI_CODING_AGENT_DIR: join(home, 'agent'), NO_COLOR: '1', CI: '1' };
    for (const name of ['SystemRoot', 'WINDIR', 'COMSPEC', 'PATH', 'TEMP', 'TMP']) if (process.env[name]) env[name] = process.env[name];
    const child = spawnSync(process.execPath, [fileURLToPath(import.meta.url), '--child', item.name],
      { cwd: home, env, windowsHide: true, encoding: 'utf8', timeout: 90000, maxBuffer: 262144 });
    let detail;
    try { detail = JSON.parse(child.stdout.trim()); } catch { detail = { raw_stdout: child.stdout }; }
    results.push({ case: item.name, exit_code: child.status, error: child.error?.message ?? null,
      stderr: child.stderr, detail });
    console.log(`${item.name}: ${child.status === 0 ? 'PASS' : 'FAIL'}`);
    if (child.status !== 0) break; // Stop on incompatibility; do not absorb a larger harness problem.
  }
  const pkg = JSON.parse(readFileSync(join(root, 'node_modules/@earendil-works/pi-coding-agent/package.json'), 'utf8'));
  const loadedAfter = await (await fetch('http://127.0.0.1:11434/api/ps', { signal: AbortSignal.timeout(5000) })).json();
  const report = { schema_version: 'acl-pi-selection:s08:v1', observed_at: new Date().toISOString(),
    status: results.length === 3 && results.every(r => r.exit_code === 0) ? 'PASS' : 'FAIL',
    package: { name: pkg.name, version: pkg.version }, node: process.version, platform: process.platform,
    architecture: process.arch, runtime_version: before[0], installed_model: installedModel,
    loaded_models_before: before[2], loaded_models_after: loadedAfter,
    approved_selection: { model: modelId, endpoint: baseUrl },
    settings, settings_sha256: hash(JSON.stringify(settings)), tools: [], extensions: [],
    resource_discovery: false, resource_config_sha256: hash(JSON.stringify({ tools: [], extensions: [], resource_discovery: false })),
    lock_sha256: hash(readFileSync(join(root, 'pnpm-lock.yaml'))), probe_sha256: hash(readFileSync(fileURLToPath(import.meta.url))),
    effective_context_qualified: false, production_dispatch_modified: false, results };
  writeFileSync(resolve(process.argv[2] ?? join(root, 'selection-27b.local.json')), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = report.status === 'PASS' ? 0 : 1;
}
