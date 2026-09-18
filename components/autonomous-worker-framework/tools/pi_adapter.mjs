// ACL owns authority/tools/outcome interpretation; Pi owns the model/session loop.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { parseRequest, digest, encodeEvent, encodeResult } from './pi_protocol.mjs';
import { createFileTools } from './pi_file_tools.mjs';

const fail = (code, message = code) => Object.assign(new Error(message), { code });
const check = (ok, code) => { if (!ok) throw fail(code); };
const TOOL_NAMES = ['acl_read_file', 'acl_report_outcome', 'acl_write_file'];
const ownKeys = (value, names) => value && typeof value === 'object' && !Array.isArray(value)
  && JSON.stringify(Object.keys(value).sort()) === JSON.stringify([...names].sort());
const nonempty = s => typeof s === 'string' && s.trim() && !s.includes('\0') && s.isWellFormed() && Buffer.byteLength(s) <= 2048;

export function createAdmittedTools(request, { python, beforeTool = async () => {} }) {
  const inv = request.invocation, settings = request.worker.runtime_settings;
  const grant = { root: request.workspace_root,
    readable_paths: [...new Set([...inv.readable_paths.map(p => p.path), ...inv.writable_paths])].sort(),
    writable_paths: [...inv.writable_paths] };
  const fileTools = createFileTools({ python, grant, maxCalls: settings.tool_calls_limit,
    timeoutMs: settings.tool_timeout_seconds * 1000, deadlineUnixMs: request.deadline_unix_ms });
  let tail = Promise.resolve(), frozen = false, closed = false, claim = null, protocolError = null, protocolErrorDetail = null, calls = 0;
  function validateOutcome(args) {
    try {
      const valid = (ok, detail) => { if (!ok) throw fail('ACL_OUTCOME_INVALID', 'ACL_OUTCOME_INVALID: ' + detail); };
      valid(ownKeys(args, ['status', 'summary', 'remaining_work']), 'expected exactly status, summary and remaining_work');
      valid(['completed', 'needs_continuation', 'blocked', 'failed'].includes(args.status), 'unsupported status');
      valid(nonempty(args.summary), 'summary must be non-empty bounded text');
      valid(args.remaining_work === null || nonempty(args.remaining_work), 'remaining_work must be null or non-empty bounded text');
      valid(!['blocked', 'needs_continuation'].includes(args.status) || args.remaining_work !== null, 'incomplete claim requires remaining work or a blocker');
      return args;
    } catch (error) { protocolError = error.code; protocolErrorDetail = error.message; throw error; }
  }
  function serial(action, mutation = false) {
    const result = tail.then(async () => {
      check(!closed && Date.now() < request.deadline_unix_ms, 'ACL_TOOL_STOPPED');
      check(++calls <= settings.tool_calls_limit, 'ACL_TOOL_BUDGET_EXCEEDED');
      check(!(mutation && frozen), 'ACL_MUTATIONS_FROZEN');
      await beforeTool();
      check(!closed && Date.now() < request.deadline_unix_ms, 'ACL_TOOL_STOPPED');
      return action();
    });
    tail = result.catch(() => {});
    return result;
  }
  const tools = fileTools.map(tool => ({ ...tool, execute: (...args) =>
    serial(() => tool.execute(...args), tool.name === 'acl_write_file') }));
  tools.push({ name: 'acl_report_outcome', label: 'ACL outcome',
    description: 'Report exactly one final work claim. Use remaining_work: null when nothing remains. This freezes writes; it does not accept the task. After this tool succeeds, respond DONE without further tool calls.',
    parameters: { type: 'object', additionalProperties: false,
      required: ['status', 'summary', 'remaining_work'], properties: {
        status: { type: 'string', enum: ['completed', 'needs_continuation', 'blocked', 'failed'] },
        summary: { type: 'string', minLength: 1, maxLength: 2048, pattern: '\\S', description: 'Brief description of the work performed.' },
        remaining_work: { anyOf: [{ type: 'null' }, { type: 'string', minLength: 1, maxLength: 2048, pattern: '\\S' }],
          description: 'null when no work remains; otherwise non-empty remaining work or blocker. Never an empty string.' },
      } },
    // Pi's schema validator coerces primitives (including empty text to null).
    // Preserve ACL's strict raw claim contract before that conversion occurs.
    prepareArguments: validateOutcome,
    execute: (_id, args) => serial(() => {
      try {
        const valid = (ok, detail) => { if (!ok) throw fail('ACL_OUTCOME_INVALID', 'ACL_OUTCOME_INVALID: ' + detail); };
        valid(!claim, 'duplicate terminal claim');
        validateOutcome(args);
        claim = structuredClone(args);
        frozen = true;
        return { content: [{ type: 'text', text: 'Claim recorded; mutations frozen. This is not acceptance. Make no further tool calls; respond DONE.' }], details: { frozen: true } };
      } catch (error) { protocolError = error.code; protocolErrorDetail = error.message; throw error; }
    }),
  });
  return { tools, get claim() { return claim && structuredClone(claim); },
    get protocolError() { return protocolError; }, get protocolErrorDetail() { return protocolErrorDetail; },
    rejectOutcome(detail) { protocolError = 'ACL_OUTCOME_INVALID'; protocolErrorDetail ??= detail || 'Pi rejected outcome tool arguments'; }, get calls() { return calls; },
    async close() { closed = true; await tail; frozen = true; } };
}

export async function loadPinnedSdk(installation, worker) {
  check(process.versions.node === worker.node_version, 'PI_NODE_VERSION_MISMATCH');
  const packageRoot = join(installation, 'node_modules/@earendil-works/pi-coding-agent');
  const pkg = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8'));
  const lock = 'sha256:' + createHash('sha256').update(readFileSync(join(installation, 'pnpm-lock.yaml'))).digest('hex');
  check(pkg.name === worker.pi_package && pkg.version === worker.pi_version && lock === worker.pi_lockfile_digest, 'PI_INSTALLATION_MISMATCH');
  return import(pathToFileURL(join(packageRoot, 'dist/index.js')).href);
}

export async function checkPrestartedRuntime(worker, binding, fetchImpl) {
  const base = worker.endpoint.replace(/\/v1$/, '');
  async function get(route) {
    const response = await fetchImpl(base + '/api/' + route, {
      redirect: 'error', signal: AbortSignal.timeout(10000),
    });
    check(response.ok, 'PI_READINESS_HTTP_ERROR');
    return response.json();
  }
  const version = await get('version'), tags = await get('tags'), ps = await get('ps');
  check(version.version === worker.provider_version, 'PI_PROVIDER_VERSION_MISMATCH');
  const installed = tags.models?.filter(m => m.name === worker.model_name) ?? [];
  check(installed.length === 1 && 'sha256:' + installed[0].digest === worker.model_digest
    && installed[0].details?.quantization_level === worker.quantization
    && digest(installed[0]) === binding.model_metadata_digest, 'PI_MODEL_MISMATCH');
  const loaded = ps.models?.filter(m => m.name === worker.model_name) ?? [];
  check(loaded.length === 1 && 'sha256:' + loaded[0].digest === worker.model_digest
    && Number.isSafeInteger(loaded[0].context_length)
    && loaded[0].context_length >= worker.required_effective_context_tokens, 'PI_SERVER_CONTEXT_UNREADY');
  check(digest({ schema_version: 'acl-pi-readiness:v1', configuration_digest: digest(worker),
    endpoint: worker.endpoint, provider_version: version.version, model_name: worker.model_name,
    model_digest: worker.model_digest, model_metadata_digest: digest(installed[0]),
    server_context_tokens: loaded[0].context_length }) === binding.host_provider_qualification_digest, 'PI_READINESS_CHANGED');

}

export async function runPiAdapter(raw, control, { fetchImpl = globalThis.fetch,
  sdkLoader = loadPinnedSdk, onEvent = () => {}, onDiagnostic = () => {} } = {}) {
  const request = parseRequest(raw, { expectedRequestDigest: control.request_digest,
    expectedWorkerDigest: control.worker_digest, nowUnixMs: Date.now() });
  const worker = request.worker, binding = control.binding;
  check(binding?.provider_adapter_id === worker.provider_adapter_id && binding.provider_adapter_id === 'pi-local-files:v1'
    && binding.qualification_candidate_digest === request.worker_digest
    && binding.runtime_settings_digest === worker.runtime_settings_digest
    && binding.model_name === worker.model_name && binding.model_digest === worker.model_digest
    && digest({ schema_version: 'worker-lab-provider-binding-identity:v1', binding }) === request.invocation.provider_binding_digest,
  'PI_BINDING_MISMATCH');
  let transportFailure = null;
  const verifyRuntime = async () => {
    try { await checkPrestartedRuntime(worker, binding, fetchImpl); }
    catch (error) { transportFailure ??= error.code ?? 'PI_READINESS_HTTP_ERROR'; throw error; }
  };
  const gate = createAdmittedTools(request, { ...control, beforeTool: verifyRuntime });
  let session, sequence = 0, requests = 0, timer, rejectDeadline, unsubscribe;
  const requestDigest = digest(request);
  const event = (kind, detail) => onEvent(encodeEvent({ schema_version: 'acl-pi-event:v1',
    request_digest: requestDigest, sequence: sequence, event: kind, detail }, request, sequence++));
  const originalFetch = globalThis.fetch;
  const deadline = new Promise((_, reject) => { rejectDeadline = reject; });
  deadline.catch(() => {});
  const abortController = new AbortController();
  let settled = false;
  const settledPromise = new Promise(resolve => {
    control = { ...control, settle: () => { settled = true; resolve(); } };
  });
  let outcome;
  try {
    timer = setTimeout(() => {
      abortController.abort();
      void session?.abort().catch(() => {});
      rejectDeadline(fail('PI_DEADLINE_EXCEEDED'));
    }, Math.max(1, request.deadline_unix_ms - Date.now()));
    const work = async () => {
      await verifyRuntime();
      // Installed Pi/provider libraries see only this allowlisted transport.
      globalThis.fetch = async (input, init) => {
        try {
        check(!transportFailure, transportFailure);
        check(!abortController.signal.aborted, 'PI_DEADLINE_EXCEEDED');
        const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
        check(url === worker.endpoint + '/chat/completions', 'PI_ENDPOINT_SUBSTITUTION');
        const body = JSON.parse(init?.body ?? await input.clone().text());
        check(body.model === worker.model_name, 'PI_MODEL_SUBSTITUTION');
        check(Number.isSafeInteger(body.max_tokens) && body.max_tokens > 0 && body.max_tokens <= worker.max_output_tokens, 'PI_OUTPUT_BUDGET');
        check(JSON.stringify((body.tools ?? []).map(t => t.function.name).sort()) === JSON.stringify(TOOL_NAMES), 'PI_TOOL_SUBSTITUTION');
        check(requests < worker.runtime_settings.request_limit, 'PI_REQUEST_BUDGET');
        body.reasoning_effort = worker.reasoning_effort;
        await verifyRuntime();
        requests++;
        const response = await fetchImpl(input, { ...init, body: JSON.stringify(body), redirect: 'error',
          signal: AbortSignal.any([abortController.signal, AbortSignal.timeout(worker.provider_timeout_seconds * 1000),
            ...(init?.signal ? [init.signal] : [])]) });
        // Ollama can reload a preloaded model with different defaults when the
        // OpenAI request arrives. Reject drift before Pi can consume tool calls.
        try { await verifyRuntime(); }
        catch (error) { await response.body?.cancel(); throw error; }
        return response;
        } catch (error) {
          transportFailure ??= error.code ?? 'PI_TRANSPORT_ERROR';
          throw error;
        }
      };
      const sdk = await sdkLoader(control.pi_installation, worker);
      const manager = sdk.SettingsManager.inMemory({ compaction: { enabled: false },
        retry: { enabled: false, maxRetries: 0, provider: { timeoutMs: worker.provider_timeout_seconds * 1000, maxRetries: 0 } } });
      const runtime = await sdk.ModelRuntime.create({ authPath: join(control.agent_dir, 'auth.json'), modelsPath: null,
        modelsStorePath: join(control.agent_dir, 'models.json'), allowModelNetwork: false, refreshOnCreate: false });
      const provider = 'acl-local-pi';
      runtime.registerProvider(provider, { api: worker.api, baseUrl: worker.endpoint,
        apiKey: 'ollama-local-placeholder', authHeader: false, models: [{ id: worker.model_name, name: worker.model_name,
          reasoning: false, input: ['text'], cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
          contextWindow: worker.required_effective_context_tokens, maxTokens: worker.max_output_tokens,
          compat: { supportsDeveloperRole: false, supportsStore: false, maxTokensField: 'max_tokens' } }] });
      const model = runtime.getModel(provider, worker.model_name);
      check(model, 'PI_EXACT_MODEL_UNAVAILABLE');
      const loader = new sdk.DefaultResourceLoader({ cwd: request.workspace_root, agentDir: control.agent_dir,
        settingsManager: manager, noExtensions: true, noSkills: true, noPromptTemplates: true, noThemes: true, noContextFiles: true,
        appendSystemPromptOverride: () => [], agentsFilesOverride: () => ({ agentsFiles: [] }),
        systemPromptOverride: () => `You are an ACL bounded coding worker. Use only the admitted ACL tools. Inspect the authorized context needed for the task. Make the required changes within the granted files. Re-read changed or relevant files when useful. Work within the supplied request, tool-call, output, context, and time budgets, leaving sufficient allowance to report the final outcome. You have at most ${worker.runtime_settings.request_limit} model requests and ${worker.runtime_settings.tool_calls_limit} tool calls for this attempt. Independent tests and acceptance remain the controller's responsibility. Do not run shell, tests, Git, network operations, or use unapproved resources. Do not discover resources, switch models, retry automatically, reopen sessions, or compact context. Call acl_report_outcome exactly once with status "completed", "needs_continuation", "blocked", or "failed"; summarize work performed and report remaining work honestly. For completed work remaining_work must be null. Once the claim succeeds, make no further tool calls and respond DONE. Writes are frozen after the claim. A completed claim is not acceptance.` });
      await loader.reload();
      check(!abortController.signal.aborted, 'PI_DEADLINE_EXCEEDED');
      const created = await sdk.createAgentSession({ cwd: request.workspace_root, agentDir: control.agent_dir,
        modelRuntime: runtime, model, scopedModels: [{ model, thinkingLevel: worker.thinking_level }],
        thinkingLevel: worker.thinking_level, tools: TOOL_NAMES, customTools: gate.tools,
        resourceLoader: loader, settingsManager: manager, sessionManager: sdk.SessionManager.inMemory(request.workspace_root) });
      session = created.session;
      check(!created.modelFallbackMessage && session.model?.id === worker.model_name
        && session.model?.baseUrl === worker.endpoint && session.model?.api === worker.api
        && session.model?.contextWindow === worker.required_effective_context_tokens
        && session.thinkingLevel === worker.thinking_level
        && JSON.stringify(session.getActiveToolNames().sort()) === JSON.stringify(TOOL_NAMES), 'PI_EFFECTIVE_CONFIGURATION_MISMATCH');
      check(!abortController.signal.aborted, 'PI_DEADLINE_EXCEEDED');
      unsubscribe = session.subscribe(e => {
        if (e.type === 'agent_settled') control.settle();
        if (e.type === 'tool_execution_start') onDiagnostic({ event: e.type, tool: e.toolName,
          path: e.args?.path ?? null, outcome: e.toolName === 'acl_report_outcome' ? e.args : undefined });
        if (e.type === 'tool_execution_end' && e.isError) onDiagnostic({ event: e.type, tool: e.toolName,
          error: e.result?.content?.filter(c => c.type === 'text').map(c => c.text).join('\n').slice(0, 2048) });
        if (e.type === 'tool_execution_end' && e.toolName === 'acl_report_outcome' && e.isError)
          gate.rejectOutcome(e.result?.content?.filter(c => c.type === 'text').map(c => c.text).join('\n').slice(0, 2048));
      });
      event('started', 'Pinned Pi session started with admitted ACL tools');
      // agent_end and a resolved prompt alone are intentionally insufficient.
      await Promise.race([Promise.all([session.prompt(request.execution_prompt ?? request.prompt), settledPromise]), deadline]);
      check(settled && session.isIdle, 'PI_NOT_SETTLED');
      event('settled', 'Pi reported agent_settled');
      check(!transportFailure, transportFailure);
      await verifyRuntime();
      const final = session.messages.filter(m => m.role === 'assistant').at(-1);
      if (!final || final.stopReason !== 'stop') throw fail('PI_SETTLED_' + (final?.stopReason ?? 'MISSING_MESSAGE'), final?.errorMessage || 'Pi did not settle successfully');
      if (gate.protocolError) throw fail(gate.protocolError, gate.protocolErrorDetail);
      check(gate.claim, 'PI_OUTCOME_MISSING');
      return { ...gate.claim, stop_reason: final.stopReason };
    };
    outcome = await work();
  } catch (error) {
    outcome = { status: error.code === 'PI_DEADLINE_EXCEEDED' ? 'timed_out' :
      ['PI_OUTCOME_MISSING', 'ACL_OUTCOME_INVALID'].includes(error.code) ? 'protocol_error' : 'failed',
      stop_reason: error.code ?? 'PI_ADAPTER_ERROR', summary: String(error.message).slice(0, 2048) || 'Pi adapter failed', remaining_work: null };
    event('error', outcome.stop_reason);
  } finally {
    clearTimeout(timer);
    abortController.abort();
    await gate.close();
    unsubscribe?.();
    session?.dispose();
    globalThis.fetch = originalFetch;
  }
  const messages = session?.messages?.filter(m => m.role === 'assistant') ?? [];
  const measured = field => messages.length && messages.every(m => Number.isSafeInteger(m.usage?.[field]) && m.usage[field] >= 0)
    ? messages.reduce((sum, m) => sum + m.usage[field], 0) : null;
  return encodeResult({ schema_version: 'acl-pi-result:v2', request_digest: requestDigest, ...outcome,
    session_reference: session?.sessionId ?? null,
    usage: { input_tokens: measured('input'), output_tokens: measured('output'), requests, tool_calls: gate.calls },
    candidate: null }, request);
}
