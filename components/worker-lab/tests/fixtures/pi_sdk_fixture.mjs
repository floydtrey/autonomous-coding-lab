// Real installed Pi SDK, deterministic in-process HTTP responses; no model/network.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runPiAdapter } from '../../../autonomous-worker-framework/tools/pi_adapter.mjs';

const control = JSON.parse(Buffer.from(process.argv[2], 'base64url').toString());
const raw = readFileSync(0);
const request = JSON.parse(raw);
const scenario = process.argv[3] ?? 'success';
const targetPath = process.argv[4] ?? 'target.py';
const model = { name: request.worker.model_name, digest: request.worker.model_digest.slice(7),
  details: { quantization_level: request.worker.quantization } };
let count = 0;
const fixtureFetch = async (input, init) => {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
  if (url.endsWith('/api/version')) return Response.json({ version: request.worker.provider_version });
  if (url.endsWith('/api/tags')) return Response.json({ models: [model] });
  if (url.endsWith('/api/ps')) return Response.json({ models: [{ ...model, context_length: request.worker.required_effective_context_tokens }] });
  assert.equal(url, request.worker.endpoint + '/chat/completions');
  const body = JSON.parse(init.body);
  assert.equal(body.model, model.name);
  assert.equal(body.reasoning_effort, 'none');
  assert.deepEqual(body.tools.map(t => t.function.name).sort(), ['acl_read_file', 'acl_report_outcome', 'acl_write_file']);
  assert.ok(!JSON.stringify(body).includes('UNAPPROVED_MARKER'));
  count++;
  if (scenario === 'provider_error') return new Response('fixture provider error', { status: 500 });
  let delta = { content: 'DONE' }, reason = 'stop';
  if (scenario !== 'missing_claim' && count <= 3) {
    const name = ['acl_read_file', 'acl_write_file', 'acl_report_outcome'][count - 1];
    let args = { path: targetPath };
    if (count === 2) {
      const toolResult = [...body.messages].reverse().find(m => m.role === 'tool');
      const parsed = JSON.parse(toolResult.content);
      args = { path: targetPath, content: 'VALUE = 2\n', expected_sha256: parsed.sha256 };
    }
    if (count === 3) args = { status: scenario === 'malformed_claim' ? 'accepted' : 'completed', summary: 'Updated target', remaining_work: scenario === 'empty_remaining' ? '' : null };
    delta = { role: 'assistant', tool_calls: [{ index: 0, id: 'call-' + count, type: 'function',
      function: { name, arguments: JSON.stringify(args) } }] };
    reason = 'tool_calls';
  }
  const chunk = (data, finish) => ({ id: 'fixture-' + count, object: 'chat.completion.chunk', created: 1,
    model: model.name, choices: [{ index: 0, delta: data, finish_reason: finish }] });
  const end = chunk({}, reason);
  end.usage = { prompt_tokens: 100, completion_tokens: 15, total_tokens: 115 };
  return new Response('data: ' + JSON.stringify(chunk(delta, null)) + '\n\ndata: ' + JSON.stringify(end) + '\n\ndata: [DONE]\n\n',
    { headers: { 'content-type': 'text/event-stream' } });
};
const fetchImpl = async (...args) => { try { return await fixtureFetch(...args); } catch (error) { console.error(error); throw error; } };
try {
  const result = await runPiAdapter(raw.subarray(0, -1), control, { fetchImpl,
    onEvent: frame => process.stdout.write(Buffer.concat([frame, Buffer.from('\n')])) });
  process.stdout.write(Buffer.concat([result, Buffer.from('\n')]));
} catch (error) { console.error(error); process.exitCode = 2; }
