# Phase 3C Synthetic Read-Only Evidence Candidate Report

**Status:** Non-executing candidate awaiting Sol review
**Worker Lab base:** `8ee1d00325b9a345d9bad353405b261e562bbaf6` on `main`
**Execution authority:** Disabled

## Scope completed

This candidate adds a sealed, durable evaluation-plan record and a Worker Lab-owned
`ReadOnlyEvidenceCollector`.  The collector reloads the protected catalog/plan, recomputes the
selection, invokes only an injected sealed test executor, and rechecks independently observed
workspace facts after validation.  `accept_execute_response` now requires this collector instead
of accepting caller-provided workspace and validation-success callbacks.

The adapter launch inspector now also requires detached HEAD, no remotes, and no alternate object
store.  Before any request byte can be sent, it creates a canonical digest of every regular
working-tree file (including ignored files) plus the local Git configuration, and binds that digest
immutably into the custody record. Acceptance requires the collector's post-validation workspace
digest to match it. Structured
retained `expected` and `observed` fields reject path and token-like content.

## Files changed

- `worker_lab/read_only_evidence.py`
- `worker_lab/framework_adapter.py`
- `worker_lab/integration.py`
- `worker_lab/process_custody.py`
- `worker_lab/windows_job.py`
- `tests/test_integration.py`
- `tests/test_process_custody.py`
- `tests/test_windows_job.py`

## Validation performed

1. `python -m pytest -q --basetemp <workspace temporary directory> tests/test_integration.py tests/test_windows_job.py tests/test_process_custody.py`
   - Initial focused collector/containment slice: `46 passed`.
   - Checkpoint gate: `90 passed, 2 skipped` (`tests/test_storage.py` symlink capability
     cases only).
   - Pytest could not write its normal cache because it belongs to the interactive user; this was a
     warning only. The temporary test directory was removed after the run.
2. Compiled every changed Python module successfully.
3. `git diff --check` passed.

## Explicitly not performed

No Codex/authentication check, framework adapter invocation, real lifecycle transition, synthetic
proposal, full suite, backup/restore, rollback, remote operation, commit, tag, PR, push, or cleanup
of any prepared workspace occurred.  The user-owned history export was not opened or modified.

## Remaining boundary

This candidate supplies only fake-testable evidence collection.  It does not authorize or perform
the one synthetic read-only proposal.  Sol must review the uncommitted candidate before a live
synthetic proposal can be considered.
