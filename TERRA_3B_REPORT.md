# Terra Controlled Trial Report: Phase 2 Batch 3B

## Trial metadata

- Model: GitHub Copilot (trial target: GPT-5.6 Terra).
- Reasoning effort: medium.
- Branch: `experiment/terra-batch3-verification`.
- Baseline HEAD: `ee574fd0483afa2fcb926462f21ebcc0245555f8`.

## Starting working tree

```text
 M tests/test_cli.py
 M tests/test_workspace_receipt.py
 M worker_lab/__init__.py
 M worker_lab/cli.py
 M worker_lab/workspace.py
?? TERRA_REPORT.md
?? docs/8_27_26_ChatGPT_History
```

This is the expressly authorized uncommitted Batch 3A baseline plus the user-provided history file.

## Status

Complete: safe workspace disposal and restart recovery.

## Implementation summary

- Added public `discard_workspace` and `worker-lab discard-workspace <attempt-id> --workspace-root <path> --cleanup-outcome <text>`.
- Disposal derives only the attempt-bound final and quarantine paths; it never accepts a deletion target from the operator.
- A valid final workspace is verified, atomically renamed to its deterministic quarantine path, and represented by a durably written and reread `QUARANTINED` receipt before recursive deletion starts.
- Recovery resumes only known `READY` states: an interrupted rename with a `PREPARED` receipt and quarantine directory, a durable `QUARANTINED` receipt with a remaining quarantine directory, or confirmed prior deletion with only the durable quarantined receipt remaining.
- `READY -> ABORTED` persists only after quarantine deletion is confirmed. The receipt is removed only after that transition succeeds. A stale quarantined receipt on a terminal `ABORTED` attempt is the sole terminal cleanup path.
- Ambiguous path combinations, invalid records, invalid roots, reparse indirection, and non-ready attempts fail closed. Filesystem removal errors use `WORKSPACE_DISPOSAL_FAILED`.

## Files created or modified

- `TERRA_3B.md` (created).
- `TERRA_3B_REPORT.md` (created).
- `worker_lab/workspace.py` (modified).
- `worker_lab/cli.py` (modified).
- `worker_lab/__init__.py` (modified).
- `tests/test_workspace_receipt.py` (modified).
- `tests/test_cli.py` (modified).

## Stable behaviors and error codes

- Added `WORKSPACE_CLEANUP_OUTCOME_INVALID`, `WORKSPACE_DISPOSAL_STATE_INVALID`, `WORKSPACE_DISPOSAL_AMBIGUOUS`, and `WORKSPACE_DISPOSAL_FAILED`.
- Reused strict storage, authority, receipt, path-indirection, and prepared-repository error contracts.

## Commands and outcomes

- `Get-Location; git branch --show-current; git rev-parse HEAD; git status --short; git diff --check` - passed: expected branch, baseline HEAD, permitted dirty state, and whitespace integrity confirmed.
- `python -m py_compile worker_lab/workspace.py worker_lab/cli.py worker_lab/__init__.py` - passed twice during implementation.
- `python -m pytest tests/test_workspace_receipt.py tests/test_cli.py -k discard_workspace -q` - initial runs exposed only Windows test-fixture issues and a deletion-complete receipt digest defect; both were corrected within scope.
- `python -m pytest tests/test_workspace_receipt.py tests/test_cli.py -k discard_workspace -q` - final focused result: 14 passed, 1 skipped, 68 deselected.
- `python -m compileall -q worker_lab tests` - passed.
- `python -m pytest -q tests/test_canonical.py tests/test_models.py tests/test_policy.py tests/test_test_catalog.py tests/test_lifecycle.py tests/test_attempt_store.py tests/test_storage.py tests/test_workspace_receipt.py tests/test_validation.py tests/test_evidence.py tests/test_cli.py` - passed: 179 passed, 6 skipped.
- `git status --short; git diff --stat; git diff --check` - passed with no whitespace errors.

## Tests and limitations

- Passed: normal quarantine/deletion, CLI success and stable failure, interrupted rename, interrupted/deletion-complete quarantine recovery, failed terminal-state persistence, ambiguous combinations, missing/malformed receipts, dirty-workspace refusal before rename, read-only Git-file deletion, stale terminal receipt finalization, and supported reparse fixture coverage.
- Skipped: six explicit Windows symlink fixture cases because directory symlink creation is unavailable. The skipped cases cover storage plus workspace state/root/final/quarantine reparse checks.
- Accepted Phase 2 limitation: no filesystem directory identifier is tracked. A same-path replacement remains acceptable only when it independently satisfies the existing receipt, Git, context, containment, reparse, remote, alternates, and nested-repository checks.

## Unresolved risks

- Host-administrator replacement races outside the worker capability model remain outside this phase. Quarantine, durable receipt state, direct-child containment, and reparse rejection constrain the supported threat model without introducing a generalized permissions system.

## Prohibited actions

No commit, push, remote access, deletion outside synthetic test fixtures, dependency installation, credential access, framework invocation, worker execution, or external-repository access occurred.

## Final Git outputs

`git status --short`:

```text
 M tests/test_cli.py
 M tests/test_workspace_receipt.py
 M worker_lab/__init__.py
 M worker_lab/cli.py
 M worker_lab/workspace.py
?? TERRA_3B.md
?? TERRA_3B_REPORT.md
?? TERRA_REPORT.md
?? docs/8_27_26_ChatGPT_History
```

`git diff --stat`:

```text
 tests/test_cli.py               |  69 +++++++
 tests/test_workspace_receipt.py | 409 ++++++++++++++++++++++++++++++++++++++++
 worker_lab/__init__.py          |   4 +-
 worker_lab/cli.py               |  21 ++-
 worker_lab/workspace.py         | 253 +++++++++++++++++++++++++
 5 files changed, 754 insertions(+), 2 deletions(-)
```
