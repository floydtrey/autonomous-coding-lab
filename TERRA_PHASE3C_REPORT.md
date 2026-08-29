# Terra Phase 3C Report

## Status

This is a non-executing candidate, not Phase 3C acceptance or execution readiness. Worker Lab began
at trusted handoff checkpoint `3c5a7e343c7c23046b1ec3bb369d8e03ec9bc4f8` on `main`; the framework
began clean on `main` at `135373d24837f5d5b0da0650c9c00fc086fcb991`. The only Worker Lab untracked
path was the permitted unopened `docs/8_27_26_ChatGPT_History` export.

## Implemented candidate scope

- Added strict `worker-lab-process-custody:v1` records and atomic storage under
  `state/process-custody/`.
- Added a fixed-command, fake-runner-only Worker Lab client that accepts only the approved framework
  commit, configured CPython path, adapter path, contract version, and read-only profile.
- Strengthened attempt parsing, lifecycle, and persistence to bind a runtime identity exactly once
  at `READY -> RUNNING` and retain it through a later abort.
- Added focused Worker Lab client/custody and lifecycle tests.

The framework current-state document was stale under the handoff's explicit override. It is updated
in the companion framework candidate to describe the same non-executing status; no framework
execution occurred.

## Validation

- Framework adapter/runtime focused tests: `25 passed`.
- Worker Lab integration, framework-client, custody, Windows Job Object, lifecycle, and
  attempt-store focused tests: `36 passed`.
- Changed Python modules compiled successfully in both repositories; `git diff --check` passed.

No Codex command, authentication status, live adapter request, real attempt, full suite, backup,
rollback, remote, product repository, commit, tag, push, or publication was run.

## Remaining trusted-review boundary

The candidate now includes the native Windows Job Object runner, bounded streaming capture,
creation-time identity, guarded custody storage/recovery, strict request parsing, and exact
framework/Python/adapter identity checks. It remains non-executing and uncommitted: trusted review
must inspect the two-repository diff and evidence before any framework milestone or execution
authority is considered. The CLI adapter deliberately keeps preflight and execution disabled because
only focused tests may inject their fake seams in Batch 3C.

## Correction record and validation order

The initial focused run exposed one fixture-only false failure: Git's Windows line-ending conversion
made the fixture adapter appear dirty after commit. The fixture now disables that conversion, while
the production identity check continues to reject any real working-tree/blob difference. The
framework-client path comparison also normalizes Windows case spelling only after the inspector has
already rejected missing, linked, or reparse-substituted components.

Validation was run in this order: Worker Lab focused tests (first run: one fixture failure),
framework focused tests (`25 passed`), corrected Worker Lab focused tests (`36 passed`), changed
Python compilation in each repository, and `git diff --check` in each repository. Pytest emitted
only cache-directory access warnings. No broad/full suite was run. The consulted authority was
Worker Lab `AGENTS.md`, `docs/START_HERE.md`, this handoff, the Phase 3C decision record, routed
Phase 3 state/spec/readiness files, and the directly affected Worker Lab/framework source and tests.

## Trusted-review correction addendum

The correction adds bounded successful-proposal retention at 32,768 UTF-8 bytes with atomic
content-addressed storage, rejects NUL, absolute/UNC-path and credential-marker proposal content,
and requires `ResultRecord.process_identity` to be the final custody digest. Framework/Worker Lab
runtime identity evidence now carries the verified audited launcher version rather than a bare
hard-coded field. `AttemptStore.bind_authorized_invocation` reloads the durable AUTHORIZED invocation
and requires its expected stable identity digest before the one-time READY-to-RUNNING bind.

Changed Worker Lab files are `docs/CURRENT_STATE.md`, `TERRA_PHASE3C_REPORT.md`,
`TERRA_PHASE3C_FRAMEWORK_REPORT.md`, `worker_lab/attempt_store.py`,
`worker_lab/framework_adapter.py`, `worker_lab/framework_client.py`,
`worker_lab/integration.py`, `worker_lab/lifecycle.py`, `worker_lab/models.py`,
`worker_lab/process_custody.py`, `worker_lab/windows_job.py`, and the focused integration,
framework-client, lifecycle, attempt-store, process-custody, and Windows-Job tests. Changed
framework files are `docs/CURRENT_STATE.md`, `docs/DECISIONS.md`, `tools/codex_runtime.py`,
`tools/worker_lab_adapter.py`, and their focused adapter/runtime tests. The native containment
failure/recovery matrix still awaits the trusted reviewer’s deeper inspection; no statement here
claims Phase 3C acceptance, milestone readiness, or permission for a live attempt.

The final focused correction slices were framework `tests/test_worker_lab_adapter.py` plus
`tests/test_codex_runtime.py` (`35 passed`), and Worker Lab `test_integration`,
`test_framework_client`, `test_process_custody`, `test_windows_job`, `test_lifecycle`, and
`test_attempt_store` (`46 passed`), each with a repository-local `--basetemp`. An earlier framework
run failed only because pytest used a 32,769-character parameter value as a Windows test-directory
name; assigning short test IDs corrected the test harness without changing the limit assertion.
Changed Python then compiled successfully and both diff checks passed. No broad suite or live action
was run.

## VS Code Correction Handoff

The correction handoff treated the inherited dirty candidate and its reports as untrusted input.
It recorded the existing changes without reset or cleanup, preserved the unopened history export,
and reviewed the directly affected authority, custody, client, adapter, integration, lifecycle,
storage, and focused test files. The correction found that `UNCERTAIN` custody could be promoted to
`ABSENCE_VERIFIED`, and that a launch failure could fall through generic cleanup and invent absence
evidence. It removed that transition, requires adapter identity plus request evidence for restart
absence, and records Job creation and launch failures as non-dispatching `UNCERTAIN` custody.

`WindowsJobAdapterRunner` now provides injected kernel, process-launch, creation-time, active-count,
and platform seams for deterministic containment tests while retaining production defaults. Focused
tests prove Job creation failure prevents launch and records no activity count, and adapter launch
failure remains non-dispatching uncertainty. The correction-focused commands completed in order:
`tests/test_process_custody.py` (`6 passed`), `tests/test_windows_job.py` (`3 passed` then `4
passed` then `5 passed` as the seams and failure tests were added), framework compile plus
`tests/test_worker_lab_adapter.py tests/test_codex_runtime.py` (`37 passed`), and Worker Lab compile
plus `test_integration`, `test_framework_client`, `test_process_custody`, `test_windows_job`,
`test_lifecycle`, `test_invocation_store`, and `test_attempt_store` (`53 passed`).

No catalog/protected-definition tests were run because the correction did not alter protected
definitions or catalog compatibility. No complete suite, milestone profile, live Codex/authentication
check, real adapter, real attempt, backup/rollback, cleanup, commit, tag, push, PR, remote, or
product-repository action was run. The Worker Lab candidate remains non-executing and uncommitted,
ready for Sol review only.

## Codex continuation after VS Code Terra limit

VS Code Terra reached its usage limit while adding the framework bounded-runtime reader-failure
work. With explicit user direction, Codex continued the same correction handoff without invoking a
Codex worker, authentication, a real adapter, or an attempt.

The continuation completed the remaining bounded changes:

- canonical request and strict-result parsing with duplicate-key rejection and finite-value checks;
- exact Worker Lab adapter mode/state and canonical per-mode response checks;
- contained atomic proposal-byte storage through `AtomicRecordStore`, including reparse-point checks;
- strict independent workspace/test evidence and complete durable-custody checks before accepting an
  adapter execution response;
- authoritative stream-reader failures in the framework bounded runtime; and
- fake-only coverage for output limits, invalid UTF-8, timeout, nonzero exit, blocked readers, and
  injected launcher-version identity.

Final focused validation, in order, compiled every changed Python module and ran Worker Lab
integration, framework-client, process-custody, Windows-Job, lifecycle, invocation-store,
attempt-store, and storage tests: `82 passed, 2 skipped`. The skips were only the two existing
symlink-creation tests, because this Windows environment cannot create symlinks. Framework adapter
and bounded-runtime tests then passed: `44 passed`. Pytest emitted only its cache-directory access
warning. `git diff --check` was subsequently clean in both repositories. No catalog/protected-
definition tests were needed because no protected definition changed.

The candidate remains non-executing, uncommitted, and subject to the final Sol diff review before a
checkpoint decision. The known history export remains unopened and unchanged.

## Sol high-review correction completion

The final high-level review found four remaining contract gaps and Codex corrected them with the
user's authorization. Successful response acceptance no longer accepts caller-built workspace or
test-success objects; after exact durable zero-process custody is reloaded, it invokes required
Worker Lab-owned read-only workspace and validation verifiers. The concrete workspace verifier
reloads the protected receipt and independently checks the canonical Git root, path digests, HEAD,
and complete tracked/untracked status.

The Windows Job runner now requires the strict invocation record and derives its target path digest
and starting commit from that record. Before custody creation or process launch it independently
checks the required canonical, non-reparse, clean Git workspace and uses only that verified path as
the adapter working directory. Framework request validation now enforces identifier, positive-
version, test-catalog, and sorted exact test-ID types. Worker Lab result validation now enforces the
2,048-byte `expected`/`observed` limits and normalized 256-byte content-reference limit.

Final focused validation compiled the changed Python in both repositories. Worker Lab's exact
integration, framework-client, process-custody, Windows-Job, lifecycle, invocation-store,
attempt-store, and storage slice passed `86 passed, 2 skipped`; the skips were the two Windows
symlink-creation capability tests. The framework adapter/runtime slice passed `53 passed`.
`git diff --check` was clean in both repositories. Pytest emitted only its existing cache-directory
permission warning. No full suite, live Codex/authentication/adapter/attempt operation, commit, tag,
push, PR, remote operation, backup, or product-repository action occurred. The history export was
not opened or changed.

## Trusted checkpoint record

The complete framework suite passed `158 tests` and the reviewed framework changes were committed at
`2d8c93312103015125f0eef9e2afdc697a45d244`, then tagged with the immutable annotated milestone
`v0.2.0-worker-lab-adapter`. The original `v0.1.0-foundation` tag remains at
`2b31a96a872ee7d042614b5be917b1b4f3c1d57c`.

Worker Lab now pins that exact framework commit and adapter blob digest
`sha256:4014b58bb47689ad0dbb9e13b01a61a60012793c611d371765a2a87975f8d117` in its fixed client
configuration. Any other framework root, commit, adapter digest, or Python path is rejected before
adapter dispatch. After pinning, the final authorized Worker Lab Phase 3C slice compiled and passed
`87 passed, 2 skipped`; the skips remain only unavailable Windows symlink creation. The full Worker
Lab suite and `v0.3.0` remain reserved for the Phase 3E milestone gate. No live execution occurred.
