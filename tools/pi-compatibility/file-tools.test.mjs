import { test } from 'node:test';
import assert from 'node:assert/strict';
import { realpathSync, mkdtempSync, writeFileSync, readFileSync, readdirSync, linkSync, mkdirSync, symlinkSync } from 'node:fs';
import { join } from 'node:path';
import os from 'node:os';
import { createFileTools, digest } from './file-tools.mjs';

const python = process.env.ACL_S09_PYTHON;
if (!python) throw new Error('Set ACL_S09_PYTHON to an explicit Python executable');
function fixture(paths = ['target.txt']) {
  const root = mkdtempSync(join(realpathSync.native(os.tmpdir()), 'acl-s09-test-'));
  writeFileSync(join(root, 'target.txt'), 'before\n');
  writeFileSync(join(root, 'protected.txt'), 'protected\n');
  const grant = { root, readable_paths: paths, writable_paths: paths };
  const tools = createFileTools({ python, grant, maxCalls: 100 });
  return { root, grant, read: args => tools[0].execute('test', args), write: args => tools[1].execute('test', args) };
}
const args = (path, content = 'after\n', expected_sha256 = digest('before\n')) => ({ path, content, expected_sha256 });

test('read/digest and atomic replacement; grant copied before caller mutation', async () => {
  const f = fixture();
  f.grant.writable_paths.push('protected.txt');
  const read = await f.read({ path: 'target.txt' });
  assert.equal(read.details.sha256, digest('before\n'));
  await f.write(args('target.txt', 'after\n', read.details.sha256));
  assert.equal(readFileSync(join(f.root, 'target.txt'), 'utf8'), 'after\n');
  assert.deepEqual(readdirSync(f.root).sort(), ['protected.txt', 'target.txt']);
  await assert.rejects(f.write(args('protected.txt')), /SCOPE_DENIED/);
});
test('outside scope and noncanonical paths reject reads/writes without changes', async () => {
  const f = fixture();
  for (const path of ['protected.txt', '../target.txt', '/target.txt', 'C:/target.txt', './target.txt', 'a/../target.txt', 'a\\target.txt', 'target.txt:stream', '.git/config']) {
    await assert.rejects(f.read({ path }), /SCOPE_(DENIED|INVALID)/);
    await assert.rejects(f.write(args(path)), /SCOPE_(DENIED|INVALID)/);
  }
  assert.equal(readFileSync(join(f.root, 'protected.txt'), 'utf8'), 'protected\n');
  assert.equal(readFileSync(join(f.root, 'target.txt'), 'utf8'), 'before\n');
});
test('stale content and absent preconditions reject without overwrite', async () => {
  const f = fixture(['new.txt', 'target.txt']);
  const read = await f.read({ path: 'target.txt' });
  writeFileSync(join(f.root, 'target.txt'), 'external change\n');
  await assert.rejects(f.write(args('target.txt', 'bad', read.details.sha256)), /STALE_WRITE/);
  await assert.rejects(f.write(args('target.txt', 'bad', 'absent')), /STALE_WRITE/);
  await assert.rejects(f.write(args('new.txt')), /STALE_WRITE/);
  await f.write(args('new.txt', 'new\n', 'absent'));
  assert.equal(readFileSync(join(f.root, 'target.txt'), 'utf8'), 'external change\n');
});
test('UTF-8, NUL and byte limits fail closed', async () => {
  const f = fixture();
  for (const content of ['\0', '\ud800', 'x'.repeat(262145)])
    await assert.rejects(f.write(args('target.txt', content)), /FILE_INVALID/);
  assert.equal(readFileSync(join(f.root, 'target.txt'), 'utf8'), 'before\n');
  for (const content of [Buffer.from([255]), Buffer.from([0]), Buffer.alloc(262145, 65)]) {
    writeFileSync(join(f.root, 'target.txt'), content);
    await assert.rejects(f.read({ path: 'target.txt' }), /FILE_INVALID/);
  }
});
test('hardlinked writes and substituted parent junctions reject', async () => {
  const f = fixture(['nested/target.txt', 'target.txt']);
  linkSync(join(f.root, 'target.txt'), join(f.root, 'alias.txt'));
  await assert.rejects(f.write(args('target.txt')), /SCOPE_DENIED/);
  const other = mkdtempSync(join(realpathSync.native(os.tmpdir()), 'acl-s09-outside-'));
  writeFileSync(join(other, 'target.txt'), 'outside\n');
  symlinkSync(other, join(f.root, 'nested'), process.platform === 'win32' ? 'junction' : 'dir');
  await assert.rejects(f.read({ path: 'nested/target.txt' }), /SCOPE_DENIED/);
  await assert.rejects(f.write(args('nested/target.txt')), /SCOPE_DENIED/);
  assert.equal(readFileSync(join(other, 'target.txt'), 'utf8'), 'outside\n');
});
test('model cannot supply authority or arbitrary operations', async () => {
  const f = fixture();
  await assert.rejects(f.read({ path: 'target.txt', grant: {} }), /ARGUMENTS_INVALID/);
  await assert.rejects(f.write({ ...args('target.txt'), root: f.root }), /ARGUMENTS_INVALID/);
});
test('failed bridge launch and rejected calls retain structured diagnostics', async () => {
  const f = fixture();
  const trace = [];
  const tools = createFileTools({ python: join(f.root, 'missing-python.exe'), grant: f.grant, trace });
  await assert.rejects(tools[0].execute('launch-failure', { path: 'target.txt' }), /BRIDGE_PROCESS_ERROR/);
  assert.equal(trace[0].call_id, 'launch-failure');
  assert.equal(trace[0].error.code, 'ENOENT');
  assert.ok(trace[0].duration_ms >= 0);
  await assert.rejects(tools[0].execute('bad-args', { path: 'target.txt', root: 'outside' }), /ARGUMENTS_INVALID/);
  assert.match(trace[1].error.message, /ARGUMENTS_INVALID/);
  assert.equal(readFileSync(join(f.root, 'target.txt'), 'utf8'), 'before\n');
});
