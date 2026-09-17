import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, readFileSync, realpathSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import { createAdmittedTools, runPiAdapter } from '../tools/pi_adapter.mjs';
import { digest, encodeFrame } from '../tools/pi_protocol.mjs';

const worker = JSON.parse(readFileSync(new URL('../../../config/pi-local-worker.json', import.meta.url)));
const python = process.env.ACL_PI_TEST_PYTHON;
assert.ok(python, 'explicit Python test executable is required');
const bytesDigest = s => 'sha256:' + createHash('sha256').update(s).digest('hex');
const model = { name: worker.model_name, digest: worker.model_digest.slice(7), details: { quantization_level: worker.quantization } };
const claim = { status: 'completed', summary: 'fixture claim', remaining_work: null };

function fixture() {
  const root = mkdtempSync(join(realpathSync.native(tmpdir()), 'acl-m02-tools-'));
  writeFileSync(join(root, 'target.txt'), 'before\n');
  writeFileSync(join(root, 'protected.txt'), 'protected\n');
  const binding = { provider_adapter_id: worker.provider_adapter_id, model_name: worker.model_name,
    model_digest: worker.model_digest, model_metadata_digest: digest(model),
    qualification_candidate_digest: digest(worker), runtime_settings_digest: worker.runtime_settings_digest,
    host_provider_qualification_digest: digest({ schema_version: 'acl-pi-readiness:v1', configuration_digest: digest(worker),
      endpoint: worker.endpoint, provider_version: worker.provider_version, model_name: worker.model_name,
      model_digest: worker.model_digest, model_metadata_digest: digest(model), server_context_tokens: worker.required_effective_context_tokens }) };
  const packet = { attempt_id: 'ATTEMPT-001', controller_identity: 'controller-1' };
  const invocation = { invocation_id: 'INVOCATION-001', attempt_id: packet.attempt_id,
    state: 'DISPATCHING', operation: 'workspace-write-code-task', sandbox_mode: 'workspace-write', result_digest: null,
    authorized_by: packet.controller_identity, authorized_at: '2026-09-17T12:00:00Z',
    provider_binding_id: 'BINDING-001', provider_binding_digest: digest({ schema_version: 'worker-lab-provider-binding-identity:v1', binding }),
    runtime_requirement_digest: worker.runtime_requirement_digest, task_digest: digest({ task: 1 }),
    controller_task_packet_digest: digest(packet), prompt_digest: digest(packet),
    readable_paths: [], writable_paths: ['target.txt'] };
  const request = { schema_version: 'acl-pi-request:v1', invocation, prompt: encodeFrame(packet).toString(),
    task: { task_digest: invocation.task_digest }, worker, worker_digest: digest(worker), workspace_root: root,
    grant_digest: digest({ invocation, workspace_root: root }), issued_at_unix_ms: Date.now(), deadline_unix_ms: Date.now() + 30000 };
  const control = { worker_digest: digest(worker), request_digest: digest(request), binding, python,
    agent_dir: root, pi_installation: root };
  const gate = createAdmittedTools(request, control);
  const tools = Object.fromEntries(gate.tools.map(t => [t.name, args => t.execute('fixture', args)]));
  return { root, request, control, gate, tools };
}
const write = { path: 'target.txt', content: 'after\n', expected_sha256: bytesDigest('before\n') };

test('promoted S09 tools preserve allowed read/write, scope and stale preconditions', async () => {
  const f = fixture();
  const read = await f.tools.acl_read_file({ path: 'target.txt' });
  assert.equal(read.details.sha256, write.expected_sha256);
  await assert.rejects(f.tools.acl_write_file({ ...write, path: 'protected.txt' }), /SCOPE_DENIED/);
  await assert.rejects(f.tools.acl_read_file({ path: '../target.txt' }), /SCOPE_INVALID/);
  await assert.rejects(f.tools.acl_write_file({ ...write, expected_sha256: bytesDigest('wrong') }), /STALE_WRITE/);
  await f.tools.acl_write_file(write);
  assert.equal(readFileSync(join(f.root, 'target.txt'), 'utf8'), 'after\n');
  assert.equal(readFileSync(join(f.root, 'protected.txt'), 'utf8'), 'protected\n');
});

for (const order of ['write-first', 'claim-first']) test('mixed batch freezes deterministically: ' + order, async () => {
  const f = fixture();
  const actions = order === 'write-first'
    ? [f.tools.acl_write_file(write), f.tools.acl_report_outcome(claim)]
    : [f.tools.acl_report_outcome(claim), f.tools.acl_write_file(write)];
  const results = await Promise.allSettled(actions);
  assert.equal(results[0].status, 'fulfilled');
  assert.equal(results[1].status, order === 'write-first' ? 'fulfilled' : 'rejected');
  assert.equal(readFileSync(join(f.root, 'target.txt'), 'utf8'), order === 'write-first' ? 'after\n' : 'before\n');
  await assert.rejects(f.tools.acl_write_file({ ...write, expected_sha256: bytesDigest('after\n') }), /MUTATIONS_FROZEN/);
  assert.equal(f.gate.claim.status, 'completed');
  await f.gate.close();
});

test('malformed or duplicate outcome is a protocol failure, not a replacement claim', async () => {
  const f = fixture();
  await assert.rejects(f.tools.acl_report_outcome({ ...claim, status: 'accepted' }), /OUTCOME_INVALID/);
  assert.equal(f.gate.protocolError, 'ACL_OUTCOME_INVALID');
  await f.tools.acl_report_outcome(claim);
  await assert.rejects(f.tools.acl_report_outcome(claim), /OUTCOME_INVALID/);
});

const readinessFetch = async input => {
  if (String(input).endsWith('/api/version')) return Response.json({ version: worker.provider_version });
  if (String(input).endsWith('/api/tags')) return Response.json({ models: [model] });
  if (String(input).endsWith('/api/ps')) return Response.json({ models: [{ ...model, context_length: worker.required_effective_context_tokens }] });
  throw new Error('unexpected fixture network request');
};

function fakeSdk(scenario, observed) {
  let model;
  return {
    SettingsManager: { inMemory: value => { observed.settings = value; return value; } },
    ModelRuntime: { create: async options => {
      assert.equal(options.allowModelNetwork, false); assert.equal(options.refreshOnCreate, false);
      return { registerProvider: (provider, options) => { model = { ...options.models[0], baseUrl: options.baseUrl, api: options.api, provider }; },
        getModel: () => model };
    } },
    DefaultResourceLoader: class { constructor(options) { observed.loader = options; }
      async reload() { for (const key of ['noExtensions', 'noSkills', 'noPromptTemplates', 'noThemes', 'noContextFiles']) assert.equal(observed.loader[key], true); } },
    SessionManager: { inMemory: () => ({}) },
    createAgentSession: async options => {
      let listener, settleTimer;
      const session = { model, thinkingLevel: 'off', isIdle: false, sessionId: 'fixture-session',
        messages: [{ role: 'assistant', stopReason: scenario === 'error' ? 'error' : 'stop' }],
        getActiveToolNames: () => options.tools,
        subscribe: fn => { listener = fn; return () => {}; },
        prompt: async () => {
          if (observed.beforeClaim) await observed.beforeClaim();
          if (scenario !== 'missing') await options.customTools.find(t => t.name === 'acl_report_outcome').execute('outcome', claim);
          listener({ type: 'agent_end' }); observed.agentEnd = Date.now();
          if (scenario !== 'no-settlement') settleTimer = setTimeout(() => {
            session.isIdle = true; observed.settled = Date.now(); listener({ type: 'agent_settled' });
          }, 30);
        }, abort: async () => {}, dispose: () => clearTimeout(settleTimer),
      };
      return { session };
    },
  };
}

for (const scenario of ['success', 'error', 'missing', 'no-settlement']) test('settlement boundary: ' + scenario, async () => {
  const f = fixture(), observed = {}, events = [];
  if (scenario === 'no-settlement') f.request.deadline_unix_ms = Date.now() + 120;
  f.control.request_digest = digest(f.request);
  const result = JSON.parse(await runPiAdapter(encodeFrame(f.request), f.control, {
    fetchImpl: readinessFetch, sdkLoader: async () => fakeSdk(scenario, observed), onEvent: raw => events.push(JSON.parse(raw)),
  }));
  const expected = { success: 'completed', error: 'failed', missing: 'protocol_error', 'no-settlement': 'timed_out' };
  assert.equal(result.status, expected[scenario]);
  if (scenario === 'success') assert.ok(observed.settled >= observed.agentEnd + 20);
  if (scenario === 'no-settlement') assert.ok(!events.some(e => e.event === 'settled'));
  assert.equal(result.usage.input_tokens, null); assert.equal(result.usage.output_tokens, null);
});

test('wrong model/context prevents SDK import and model dispatch', async () => {
  const f = fixture(); let imported = false;
  const result = JSON.parse(await runPiAdapter(encodeFrame(f.request), f.control, {
    fetchImpl: input => String(input).endsWith('/api/ps') ? Response.json({ models: [{ ...model, context_length: 4096 }] }) : readinessFetch(input),
    sdkLoader: async () => { imported = true; },
  }));
  assert.equal(imported, false); assert.equal(result.status, 'failed'); assert.equal(result.usage.requests, 0);
});

for (const timing of ['before-request', 'after-request']) test('context drift is rejected before tools consume output: ' + timing, async () => {
  const f = fixture(); let drifted = false, observations = 0;
  const observed = { beforeClaim: async () => {
    await assert.rejects(globalThis.fetch(worker.endpoint + '/chat/completions', { body: JSON.stringify({
      model: worker.model_name, max_tokens: worker.max_output_tokens,
      tools: ['acl_read_file', 'acl_write_file', 'acl_report_outcome'].map(name => ({ function: { name } })),
    }) }), /PI_SERVER_CONTEXT_UNREADY/);
  } };
  const result = JSON.parse(await runPiAdapter(encodeFrame(f.request), f.control, {
    sdkLoader: async () => fakeSdk('success', observed),
    fetchImpl: async input => {
      if (String(input).endsWith('/chat/completions')) { drifted = true; return new Response('untrusted tool calls'); }
      if (String(input).endsWith('/api/ps') && ++observations > 1 && timing === 'before-request') drifted = true;
      if (drifted && String(input).endsWith('/api/ps')) return Response.json({ models: [{ ...model, context_length: 4096 }] });
      return readinessFetch(input);
    },
  }));
  assert.equal(result.status, 'failed');
  assert.equal(result.stop_reason, 'PI_SERVER_CONTEXT_UNREADY');
  assert.equal(result.usage.requests, timing === 'before-request' ? 0 : 1);
  assert.equal(readFileSync(join(f.root, 'target.txt'), 'utf8'), 'before\n');
});

test('SDK wrapping a request-budget error cannot hide the actual stop reason', async () => {
  const f = fixture();
  const observed = { beforeClaim: async () => {
    const init = { body: JSON.stringify({ model: worker.model_name, max_tokens: worker.max_output_tokens,
      tools: ['acl_read_file', 'acl_write_file', 'acl_report_outcome'].map(name => ({ function: { name } })) }) };
    for (let i = 0; i < worker.runtime_settings.request_limit; i++) await globalThis.fetch(worker.endpoint + '/chat/completions', init);
    await assert.rejects(globalThis.fetch(worker.endpoint + '/chat/completions', init), /PI_REQUEST_BUDGET/);
  } };
  const result = JSON.parse(await runPiAdapter(encodeFrame(f.request), f.control, {
    sdkLoader: async () => fakeSdk('error', observed),
    fetchImpl: input => String(input).endsWith('/chat/completions') ? new Response('fixture') : readinessFetch(input),
  }));
  assert.equal(result.stop_reason, 'PI_REQUEST_BUDGET');
  assert.equal(result.usage.requests, worker.runtime_settings.request_limit);
});
