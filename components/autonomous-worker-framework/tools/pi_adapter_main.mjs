// JSONL transport entrypoint. Installed only as an explicitly injected executor.
import { readFileSync } from 'node:fs';
import { runPiAdapter } from './pi_adapter.mjs';
import { MAX_FRAME_BYTES } from './pi_protocol.mjs';

try {
  const control = JSON.parse(Buffer.from(process.argv[2], 'base64url').toString('utf8'));
  const raw = readFileSync(0);
  if (raw.length > MAX_FRAME_BYTES + 1 || raw.at(-1) !== 10 || raw.subarray(0, -1).includes(10))
    throw new Error('PI_PROTOCOL_INVALID: expected exactly one bounded JSONL request');
  const result = await runPiAdapter(raw.subarray(0, -1), control, {
    onEvent: frame => process.stdout.write(Buffer.concat([frame, Buffer.from('\n')])),
    onDiagnostic: value => process.stderr.write(JSON.stringify(value).slice(0, 4096) + '\n'),
  });
  process.stdout.write(Buffer.concat([result, Buffer.from('\n')]));
} catch (error) {
  console.error(error.code ?? 'PI_PROTOCOL_INVALID', error.message);
  process.exitCode = 2;
}
