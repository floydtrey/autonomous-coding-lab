# Terra Phase 3B Report - Strict Integration Contracts

## Starting identities and authority

- Worker Lab repository: `C:\Users\MineTrackerWorker\repos\worker-lab`.
- Required and verified branch: `phase3/framework-contracts-v1`.
- Starting HEAD: `48f594ff38aaec0e569ebac73789201f4b55a888`.
- Approved Phase 3 specification commit verified in ancestry:
  `eee9c7f2a4ab210dd6f22c774a7969e40a2a5a3d`.
- Framework read-only authority: clean local `main` at
  `135373d24837f5d5b0da0650c9c00fc086fcb991`.
- The only starting untracked Worker Lab item was the permitted user-owned
  `docs/8_27_26_ChatGPT_History`; it was not opened or changed.

Session authority explicitly superseded stale framework `START_HERE.md` and `CURRENT_STATE.md`
references to the prior Phase 3A boundary. Those framework documents were not changed. The conflict
is recorded here as directed; the supplied Batch 3B handoff and clean framework checkpoint governed
this work.

## Context read

- Worker Lab: `docs/START_HERE.md`, `TERRA_PHASE3B.md`, Phase 3 portions of
  `docs/CURRENT_STATE.md`, `docs/PHASE3_SPEC.md`, `docs/PHASE3_READINESS_REVIEW.md`,
  `worker_lab/models.py`, `worker_lab/storage.py`, `worker_lab/attempt_store.py`,
  `worker_lab/test_catalog.py`, `worker_lab/canonical.py`, the v2 catalog, and the focused catalog
  tests.
- Framework, read-only: `tools/codex_runtime.py`, `tools/context_probe.py`,
  `tools/code_task.py`, and `tools/worker_result.py`.

No framework source, historical reports, backups, ZIPs, product repositories, remotes, network,
credentials, API keys, user configuration, or chat export content was accessed.

## Changes

- Added `worker_lab/integration.py`: strict versioned invocation and result records, operation/state
  enums, canonical identities, field/path/digest validation, and explicit invocation transitions.
- Added `worker_lab/invocation_store.py`: atomic create/read and immutable guarded state transitions
  under `state/invocations/`.
- Added `worker_lab/framework_adapter.py`: a fixed canonical-JSON preparation command and strict
  response/result parsing. It has no default runner and returns
  `INTEGRATION_EXECUTION_DISABLED` without an injected test fake.
- Added focused `tests/test_integration.py` and `tests/test_invocation_store.py`.
- Added immutable `curricula/catalogs/worker-lab-v3.json`, preserving v2 entries and adding T016,
  T022, and the four specified Phase 3 profiles.
- Updated the minimum protected-definition assertion, test-catalog documentation, and Phase 3B
  candidate status in `docs/CURRENT_STATE.md`.

No Phase 1/2 schema, workspace, lifecycle, backup, CLI, policy, role, exercise, prior catalog, or
framework file changed. No function introduced in this batch imports or calls `subprocess`, Codex,
or a framework execution function.

## Validation and correction record

1. `python -m py_compile worker_lab/integration.py worker_lab/invocation_store.py
   worker_lab/framework_adapter.py` passed.
2. Initial focused invocation tests exposed tuple serialization that strict JSON loaders correctly
   rejected. The record serializers were corrected to emit JSON arrays.
3. The next run exposed that `PREPARED -> REJECTED` must be possible before authorization. The
   authorization invariant was narrowed to leave that documented rejection path available.
4. `python -m pytest -q tests/test_integration.py tests/test_invocation_store.py` passed:
   `6 passed in 4.30s`.
5. Initial catalog/definition validation exposed a UTF-8 BOM emitted while mechanically deriving
   the new catalog. The BOM was removed without changing JSON content.
6. `python -m pytest -q tests/test_integration.py tests/test_invocation_store.py
   tests/test_test_catalog.py tests/test_protected_definitions.py` passed:
   `28 passed in 0.30s`.

7. Final candidate compilation of all changed Python files passed with no output.
8. The required final focused command passed: `28 passed in 0.29s` for
  `tests/test_integration.py`, `tests/test_invocation_store.py`, `tests/test_test_catalog.py`, and
  `tests/test_protected_definitions.py`.
9. `git diff --check` passed with no output. The final changed paths are limited to this report,
  `worker_lab/integration.py`, `worker_lab/invocation_store.py`,
  `worker_lab/framework_adapter.py`, the two focused tests, `worker-lab-v3.json`,
  `tests/test_protected_definitions.py`, `docs/TEST_CATALOG.md`, and
  `docs/CURRENT_STATE.md`. The permitted untracked chat export remains untouched.

No broad suite or runtime profile has been run.

## Post-review correction

The following accepted Batch 3B corrections were applied after review without changing the batch
authority or enabling execution:

- `ResultRecord` now requires request, prompt, catalog, test-plan, workspace root/path, process
  timing, workspace state, expected/observed, and output-digest evidence, and the adapter verifies
  every corresponding invocation identity before accepting a parsed result.
- Normalized path `.` now fails with `INTEGRATION_PATH_INVALID` rather than reaching an unsafe path
  component access.
- `InvocationStore.read()` validates an invocation ID before path construction, and
  `save_transition()` requires the caller's expected current digest, rejecting stale snapshots with
  `INTEGRATION_STALE_WRITE`.
- Result parsing now bounds inputs to the adapter response limit and maps invalid types, encodings,
  empty, oversized, and malformed inputs to `INTEGRATION_RESULT_INVALID`.
- Validation stage identities must be unique and follow the sealed test-plan prefix; directly
  constructed `REJECTED` invocations cannot carry authorization fields.

Focused regression validation passed after these corrections:
`10 passed in 0.27s` for `tests/test_integration.py` and
`tests/test_invocation_store.py`. No execution-capable dependency was introduced.

## Limitations and handoff

This candidate does not invoke Codex or the framework, create/transition a Worker Lab attempt,
enter `RUNNING`, retain prompts or worker output, execute validation commands through an adapter,
create candidates, or implement process containment, non-mutation proof, or interruption recovery.
Those remain Batch 3C+ review decisions. The generated adapter command is an inert contract shape;
it cannot execute because a caller must inject a test runner.

The planned `READ_ONLY_INVOCATION:v1`, `CODE_INVOCATION:v1`, and
`PHASE3_MILESTONE:v1` profiles name future work and do not claim it is executable or authorized.
Terra left all changes uncommitted for trusted review.

## Trusted completion review

The trusted review accepted Terra's repaired contract, storage, parser, and focused regression
changes. Two final specification-alignment corrections were added before checkpointing:

- `terra-medium:v1` now enforces the exact `gpt-5.6-terra`, medium-reasoning, 900-second values;
- authorization and process timestamps now require canonical UTC second precision.

Only the two new regression nodes for those corrections were run after Terra's passing repair slice:
`6 passed in 0.15s`. Pytest reported only that its optional cache could not be written in the
restricted review environment; test execution and results were unaffected. The routing documents
now identify the accepted Worker Lab-side Phase 3B checkpoint and keep framework execution,
`READY -> RUNNING`, and Phase 3C authority disabled.
