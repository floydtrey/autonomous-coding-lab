// Wire contract only: no Pi import, resource discovery, model request or tools.
import { createHash } from 'node:crypto';
import { isAbsolute, win32 } from 'node:path';

export const MAX_FRAME_BYTES = 262144;
export const REQUEST_SCHEMA = 'acl-pi-request:v1';
export const RESULT_SCHEMA = 'acl-pi-result:v1';
export const EVENT_SCHEMA = 'acl-pi-event:v1';
const require = (ok, message) => { if (!ok) throw new Error(`PI_PROTOCOL_INVALID: ${message}`); };
const object = (v, fields) => require(v !== null && typeof v === 'object' && !Array.isArray(v)
  && JSON.stringify(Object.keys(v).sort()) === JSON.stringify(fields.split(' ').sort()), 'missing or unknown fields');
const text = v => require(typeof v === 'string' && v.trim().length > 0 && !v.includes('\0')
  && Buffer.byteLength(v) <= 32768, 'invalid text');
const integer = (v, minimum = 0) => require(Number.isSafeInteger(v) && v >= minimum, 'invalid integer');
const hash = v => require(typeof v === 'string' && /^sha256:[0-9a-f]{64}$/.test(v), 'invalid digest');

// Manual object serialization also sorts integer-looking keys lexically, like
// Python canonical_json (JSON.stringify(object) would reorder those keys).
function canonical(v, depth = 0) {
  require(depth <= 64, 'nesting limit exceeded');
  if (v === null || typeof v === 'boolean') return JSON.stringify(v);
  if (typeof v === 'number') {
    require(Number.isSafeInteger(v), 'unsafe or noninteger number');
    return JSON.stringify(v);
  }
  if (typeof v === 'string') {
    require(v.isWellFormed(), 'invalid Unicode');
    return JSON.stringify(v);
  }
  if (Array.isArray(v)) return '[' + v.map(x => canonical(x, depth + 1)).join(',') + ']';
  require(typeof v === 'object', 'unsupported JSON value');
  return '{' + Object.keys(v).sort().map(k => {
    require(/^[\x00-\x7f]*$/.test(k), 'object keys must be ASCII');
    return JSON.stringify(k) + ':' + canonical(v[k], depth + 1);
  }).join(',') + '}';
}
export function encodeFrame(value) {
  const raw = Buffer.from(canonical(value), 'utf8');
  require(raw.length <= MAX_FRAME_BYTES, 'frame size limit exceeded');
  return raw;
}
export const digest = value => 'sha256:' + createHash('sha256').update(encodeFrame(value)).digest('hex');
export function decodeFrame(raw) {
  require(Buffer.isBuffer(raw) && raw.length > 0 && raw.length <= MAX_FRAME_BYTES, 'invalid frame size/type');
  try {
    const value = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(raw));
    require(value !== null && typeof value === 'object' && !Array.isArray(value)
      && encodeFrame(value).equals(raw), 'noncanonical JSON, duplicate fields or trailing bytes');
    return value;
  } catch (e) { throw new Error('PI_PROTOCOL_INVALID: invalid canonical UTF-8 JSON frame', { cause: e }); }
}

export function parseRequest(raw, { expectedRequestDigest, expectedWorkerDigest, nowUnixMs }) {
  // These pins come separately from the trusted parent, NEVER from the frame.
  // Python validates existing Invocation/Packet/Task contracts before sealing.
  const r = decodeFrame(raw);
  object(r, 'schema_version invocation prompt task worker worker_digest workspace_root grant_digest issued_at_unix_ms deadline_unix_ms' + (r.schema_version === 'acl-pi-request:v2' ? ' execution_prompt' : ''));
  require([REQUEST_SCHEMA, 'acl-pi-request:v2'].includes(r.schema_version), 'unsupported request version');
  if (r.schema_version === 'acl-pi-request:v2') text(r.execution_prompt);
  hash(expectedRequestDigest); hash(expectedWorkerDigest);
  require(digest(r) === expectedRequestDigest, 'request differs from trusted parent admission');
  require(r.worker_digest === expectedWorkerDigest && digest(r.worker) === expectedWorkerDigest, 'worker configuration differs');
  require(r.worker.schema_version === 'worker-lab-pi-local-configuration:v1', 'unsupported worker version');
  const inv = r.invocation;
  require(inv !== null && typeof inv === 'object', 'invalid invocation');
  require(inv.state === 'DISPATCHING' && inv.operation === 'workspace-write-code-task'
    && inv.sandbox_mode === 'workspace-write' && inv.result_digest === null, 'invocation is not dispatchable');
  text(inv.invocation_id); text(inv.attempt_id); text(inv.authorized_by); text(inv.authorized_at);
  hash(inv.provider_binding_digest); text(inv.provider_binding_id);
  require(inv.runtime_requirement_digest === r.worker.runtime_requirement_digest, 'runtime requirement differs');
  text(r.prompt);
  const packet = decodeFrame(Buffer.from(r.prompt));
  require(digest(packet) === inv.controller_task_packet_digest && digest(packet) === inv.prompt_digest
    && packet.attempt_id === inv.attempt_id && packet.controller_identity === inv.authorized_by, 'packet differs');
  require(r.task.task_digest === inv.task_digest, 'task differs');
  text(r.workspace_root);
  require((isAbsolute(r.workspace_root) || win32.isAbsolute(r.workspace_root))
    && !r.workspace_root.replaceAll('\\', '/').split('/').includes('..'), 'invalid workspace root');
  require(r.grant_digest === digest({ invocation: inv, workspace_root: r.workspace_root }), 'grant differs');
  integer(r.issued_at_unix_ms, 1); integer(r.deadline_unix_ms, 1); integer(nowUnixMs, 1);
  require(r.issued_at_unix_ms <= nowUnixMs && nowUnixMs < r.deadline_unix_ms
    && r.deadline_unix_ms - r.issued_at_unix_ms <= r.worker.attempt_timeout_seconds * 1000, 'expired, future or excessive deadline');
  return r;
}

export function encodeResult(value, request) {
  object(value, 'schema_version request_digest status stop_reason summary remaining_work session_reference usage candidate');
  require([RESULT_SCHEMA, 'acl-pi-result:v2'].includes(value.schema_version) && value.request_digest === digest(request), 'result identity differs');
  require(['completed', 'needs_continuation', 'blocked', 'failed', 'cancelled', 'timed_out', 'protocol_error'].includes(value.status), 'unsupported status');
  text(value.stop_reason); text(value.summary);
  if (value.remaining_work !== null) text(value.remaining_work);
  if (value.session_reference !== null) text(value.session_reference);
  require(!['needs_continuation', 'blocked'].includes(value.status) || value.remaining_work !== null, 'missing remaining work/blocker');
  if (value.usage !== null) {
    object(value.usage, 'input_tokens output_tokens requests tool_calls');
    Object.entries(value.usage).forEach(([key, v]) => {
      if (!(value.schema_version === 'acl-pi-result:v2' && ['input_tokens', 'output_tokens'].includes(key) && v === null)) integer(v);
    });
    require(value.status !== 'completed' || (value.usage.requests <= request.worker.runtime_settings.request_limit
      && value.usage.tool_calls <= request.worker.runtime_settings.tool_calls_limit), 'completed claim exceeds budget');
  }
  if (value.candidate !== null) {
    object(value.candidate, 'digest artifacts'); hash(value.candidate.digest);
    require(Array.isArray(value.candidate.artifacts), 'invalid artifacts');
    const seen = new Set();
    for (const artifact of value.candidate.artifacts) {
      object(artifact, 'path digest'); text(artifact.path); hash(artifact.digest);
      require(request.invocation.writable_paths.includes(artifact.path) && !seen.has(artifact.path), 'artifact outside grant or duplicated');
      seen.add(artifact.path);
    }
  }
  return encodeFrame(value);
}

export function encodeEvent(value, request, expectedSequence) {
  object(value, 'schema_version request_digest sequence event detail');
  require(value.schema_version === EVENT_SCHEMA && value.request_digest === digest(request), 'event identity differs');
  integer(value.sequence); integer(expectedSequence);
  require(value.sequence === expectedSequence, 'event sequence differs');
  require(['started', 'settled', 'stopped', 'error'].includes(value.event), 'unsupported event');
  text(value.detail);
  return encodeFrame(value);
}
