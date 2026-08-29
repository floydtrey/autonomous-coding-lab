# Terra Phase 3B Handoff — Strict Integration Contracts

## Objective

Implement the Worker Lab half of Phase 3B: strict invocation/result records, durable invocation
storage, immutable `worker-lab-v3` test bindings, and a fake-only framework preparation seam.

This batch must not invoke Codex, execute the framework, transition an attempt to `RUNNING`, or modify
the Autonomous Worker Framework. The framework adapter implementation is a later separately reviewed
batch.

## Required start

- Repository: `C:\Users\MineTrackerWorker\repos\worker-lab`
- Branch: `phase3/framework-contracts-v1`
- Approved specification commit in ancestry: `eee9c7f2a4ab210dd6f22c774a7969e40a2a5a3d`
- Framework read-only authority: clean local `main` at
  `135373d24837f5d5b0da0650c9c00fc086fcb991`
- This tracked handoff must exist in starting `HEAD`.
- Preserve and do not open `docs/8_27_26_ChatGPT_History` if present.

Stop on any identity difference, tracked starting change, unexpected untracked file, or conflict with
the approved specification.

## Minimum reading

Read once:

1. `docs/START_HERE.md`
2. Phase 3 section of `docs/CURRENT_STATE.md`
3. `docs/PHASE3_SPEC.md`
4. `docs/PHASE3_READINESS_REVIEW.md`
5. relevant contracts in `worker_lab/models.py`, `worker_lab/storage.py`,
   `worker_lab/attempt_store.py`, `worker_lab/test_catalog.py`, and `worker_lab/canonical.py`
6. read-only framework public shapes in `tools/codex_runtime.py`, `tools/context_probe.py`,
   `tools/code_task.py`, and `tools/worker_result.py`

Do not read history, backups, reports other than this task's report, product repositories, or broad
unrelated tests.

## Allowed implementation

Use focused new modules rather than enlarging `workspace.py`:

- `worker_lab/integration.py` — strict invocation/result schemas, enums, canonical identities, and
  non-executing preparation request/response validation.
- `worker_lab/invocation_store.py` — atomic create/read and protected invocation-state transitions.
- `worker_lab/framework_adapter.py` — fixed command/envelope construction and response parsing with a
  required injected runner; no default subprocess runner and no execution-capable CLI.
- focused new tests for those modules.
- `curricula/catalogs/worker-lab-v3.json` plus the minimum catalog/definition tests and
  `docs/TEST_CATALOG.md` update needed to bind it.
- minimal exports in `worker_lab/__init__.py` only if a tested public API requires them.
- `docs/CURRENT_STATE.md` and `TERRA_PHASE3B_REPORT.md` for accurate candidate status/reporting.

Do not change existing Phase 1/2 schemas, lifecycle transitions, workspace behavior, backup behavior,
CLI, policies, roles, exercises, `worker-lab-v1/v2`, framework files, or test-ID meanings.

## Required contract behavior

Implement the exact Phase 3 specification with these Batch 3B limits:

- Invocation schema: `worker-lab-framework-invocation:v1` with strict fields, types, enums,
  timestamps, normalized paths, digests, and supported versions.
- Invocation states: `PREPARED`, `AUTHORIZED`, `DISPATCHING`, `COMPLETED`, `UNCERTAIN`, `REJECTED`,
  and `ABORTED`, with a minimal explicit legal-transition table.
- Result schema: `worker-lab-framework-result:v1` with strict invocation/input/runtime/workspace/test
  identities, process evidence, changed paths, proposal/candidate identities, validation stages,
  first failure, containment, content reference, and canonical result digest.
- Unknown/missing fields, invalid paths, unsupported operations/runtime profiles, inconsistent
  success/failure fields, repair attempts, retryable results, and identity mismatches fail closed with
  stable `LabValidationError` codes.
- `read-only-proposal` requires `read-only` sandbox and no writable paths.
- `workspace-write-code-task` requires `workspace-write` and nonempty exact writable paths.
- Phase 3 initially accepts only the specification's single Terra-medium runtime profile.
- Invocation storage is immutable on create, atomic, rejects substitution, and permits only the
  protected state transitions. Terminal records cannot reopen.
- The client seam must require an explicitly injected runner. Production calls without one fail with
  `INTEGRATION_EXECUTION_DISABLED`. Tests use fakes only.
- The client constructs a fixed adapter command from trusted configuration, sends canonical JSON,
  accepts bounded UTF-8 output, parses exactly one strict response, and cannot accept exercise- or
  worker-supplied executable/flags/environment/cwd.
- No function in this batch may call Codex, `subprocess.run/Popen`, or existing framework execution
  functions.

Do not implement `READY -> RUNNING`, actual process containment, prompt retention, worker output
retention, workspace mutation checks, validation execution, or candidate creation yet.

## Test catalog

Create immutable `worker-lab-v3` by preserving every v2 definition and adding Phase 3 paths and
profiles without changing permanent meanings. Include T016 and T022 bindings required by the
approved specification. Add:

- `FRAMEWORK_ADAPTER_CHANGE:v1`
- `READ_ONLY_INVOCATION:v1`
- `CODE_INVOCATION:v1`
- `PHASE3_MILESTONE:v1`

Commands may initially point only to implemented Batch 3B focused tests. Later execution profiles may
retain planned evaluator locators, but they must not claim executable coverage that does not exist.
Published v1/v2 files remain byte-for-byte unchanged.

## Validation

Develop with exact new test nodes. At the candidate boundary run once:

1. compile only changed Python files;
2. the new integration and invocation-store test files;
3. `tests/test_test_catalog.py` and `tests/test_protected_definitions.py`;
4. `git diff --check`.

Do not run the complete suite, framework tests, Codex, a runtime profile, or a milestone drill. Stop at
the first failed required boundary; correct the cause and rerun only the affected failed slice.

## Report and stopping rules

Create `TERRA_PHASE3B_REPORT.md` recording identities, context read, every changed file, design
choices, commands/results, failures/corrections, limitations, and final status.

Stop without compensating action if safe implementation requires:

- modifying the framework or current workspace/lifecycle behavior;
- adding a real/default process runner;
- resolving a reserved Batch 3C security decision;
- changing a permanent test meaning or prior catalog;
- accessing credentials, a remote, network, backup, chat export, or product repository.

Do not commit, push, merge, tag, publish, back up, delete, reset, restore, clean, or stash. Leave the
candidate uncommitted for trusted review.
