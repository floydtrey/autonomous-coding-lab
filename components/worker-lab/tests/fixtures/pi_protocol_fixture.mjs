// Serialization fixture ONLY. Never imports Pi or invokes a model/file tool.
import { readFileSync } from 'node:fs';
import { parseRequest, encodeFrame, encodeResult, encodeEvent, digest } from '../../../autonomous-worker-framework/tools/pi_protocol.mjs';

try {
  const [requestPin, workerPin, now, mode] = process.argv.slice(2);
  const request = parseRequest(readFileSync(0), {
    expectedRequestDigest: requestPin, expectedWorkerDigest: workerPin, nowUnixMs: Number(now),
  });
  if (mode === 'echo') process.stdout.write(encodeFrame(request));
  else if (mode === 'event') process.stdout.write(encodeEvent({
    schema_version: 'acl-pi-event:v1', request_digest: digest(request),
    sequence: 0, event: 'started', detail: 'serialization fixture only',
  }, request, 0));
  else process.stdout.write(encodeResult({
    schema_version: 'acl-pi-result:v1', request_digest: digest(request),
    status: 'completed', stop_reason: 'fixture_stop', summary: 'Fixture: café 😀',
    remaining_work: null, session_reference: 'fixture-session:001',
    usage: { input_tokens: 17, output_tokens: 3, requests: 1, tool_calls: 0 },
    candidate: { digest: 'sha256:' + 'a'.repeat(64), artifacts: [
      { path: request.invocation.writable_paths[0], digest: 'sha256:' + 'b'.repeat(64) },
    ] },
  }, request));
} catch (error) {
  console.error(error.message); process.exitCode = 2;
}
