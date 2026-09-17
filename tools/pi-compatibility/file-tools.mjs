// Qualification adapter: authority is captured here, never accepted from a tool call.
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';

export const digest = bytes => 'sha256:' + createHash('sha256').update(bytes).digest('hex');
export const schemas = [
  { name: 'acl_read_file', label: 'ACL read', description: 'Read an exact authorized UTF-8 file. Returns content and sha256 for a subsequent write.',
    parameters: { type: 'object', properties: { path: { type: 'string' } }, required: ['path'], additionalProperties: false } },
  { name: 'acl_write_file', label: 'ACL write', description: 'Atomically replace an exact authorized UTF-8 file. Supply expected_sha256 from read, or absent for an authorized new file.',
    parameters: { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' }, expected_sha256: { type: 'string' } },
      required: ['path', 'content', 'expected_sha256'], additionalProperties: false } },
];

export function createFileTools({ python, grant, trace = [], maxCalls = 8 }) {
  const sealedGrant = JSON.parse(JSON.stringify(grant));
  let calls = 0;
  return schemas.map(schema => ({ ...schema, async execute(_id, args, signal) {
    const started = Date.now();
    const record = { tool: schema.name, call_id: _id, started_at: new Date().toISOString(), args,
      result: { ok: false }, exit_code: null };
    trace.push(record);
    try {
    if (signal?.aborted) throw new Error('ACL_TOOL_ABORTED');
    if (++calls > maxCalls) throw new Error('ACL_TOOL_BUDGET_EXCEEDED');
    const permitted = schema.parameters.required;
    if (!args || Object.keys(args).length !== permitted.length || permitted.some(k => typeof args[k] !== 'string'))
      throw new Error('ACL_TOOL_ARGUMENTS_INVALID');
    // A fixed interpreter/script and JSON stdin, never a shell or model-supplied command.
    const child = spawnSync(python, ['-I', '-B', fileURLToPath(new URL('./file-bridge.py', import.meta.url))], {
      input: JSON.stringify({ grant: sealedGrant, operation: schema.name, args }),
      encoding: 'utf8', timeout: 10000, maxBuffer: 2 * 1024 * 1024, windowsHide: true,
    });
    record.exit_code = child.status;
    record.stderr = child.stderr?.slice(0, 8192);
    record.signal = child.signal;
    if (child.error) throw new Error(`ACL_BRIDGE_PROCESS_ERROR: ${child.error.message}`, { cause: child.error });
    let result;
    try { result = JSON.parse(child.stdout); } catch { throw new Error('ACL_BRIDGE_PROTOCOL_ERROR'); }
    record.result = result;
    if (child.status !== 0 || !result.ok) throw new Error(`${result.code ?? 'ACL_BRIDGE_FAILED'}: ${result.message ?? ''}`);
    return { content: [{ type: 'text', text: JSON.stringify(result.result) }], details: result.result };
    } catch (error) {
      record.error = { name: error.name, message: error.message, code: error.code ?? error.cause?.code ?? null };
      throw error;
    } finally { record.duration_ms = Date.now() - started; }
  } }));
}
