# Terra Controlled Trial Report

## Trial metadata

- Model: GitHub Copilot (model target specified by trial: GPT-5.6 Terra).
- Reasoning effort: medium (per trial instruction).
- Starting branch: `experiment/terra-batch3-verification`.
- Starting HEAD: `ee574fd0483afa2fcb926462f21ebcc0245555f8`.

## Implementation summary

Implemented read-only, restart-safe verification of the sole attempt-bound prepared workspace and exposed it as `worker-lab verify-workspace <attempt-id> --workspace-root <path>`.

Verification resolves real lab/root directories, rejects reparse indirection in the state, attempt, and receipt paths before reading records, requires a clean `READY` attempt and strict `PREPARED` receipt, revalidates authority, verifies every receipt identity binding, derives only `<workspace-root>/<attempt-id>`, and checks exact detached/clean Git identity, remotes, alternates, context bytes, reparse indirection, and ignored nested repositories. Git verification disables optional locks, and the success test asserts every workspace file remains byte-for-byte unchanged. It does not write, repair, delete, rename, or transition state.

## Files created or modified

- `TERRA_REPORT.md` (created).
- `worker_lab/workspace.py` (modified).
- `worker_lab/cli.py` (modified).
- `worker_lab/__init__.py` (modified).
- `tests/test_workspace_receipt.py` (modified).
- `tests/test_cli.py` (modified).

## Behaviors and stable error codes

- Added public `verify_workspace` and the `verify-workspace` CLI command.
- Added verification coverage for process restart, record byte preservation, invalid or non-prepared receipts, non-ready attempts, root and workspace substitution, missing workspaces, dirty trees, branch and commit changes, remotes, alternate object stores, assigned context mutation, ignored nested repositories, and supported reparse fixtures.
- No new stable error code was introduced. The operation uses the established `WORKSPACE_TIMEOUT_INVALID`, `WORKSPACE_LAB_INVALID`, `WORKSPACE_ROOT_INVALID`, `WORKSPACE_ATTEMPT_STATE_INVALID`, `WORKSPACE_PATH_INDIRECTION`, `WORKSPACE_RECEIPT_MISMATCH`, `WORKSPACE_VERIFY_FAILED`, and strict storage error codes.

## Commands and outcomes

- `Get-Location; git branch --show-current; git rev-parse HEAD; git status --short; git ls-files --error-unmatch TERRA.md` - passed: the repository path, required branch, clean tree, and tracked instruction file were confirmed.
- `python -m py_compile worker_lab/workspace.py` - passed.
- `python -m py_compile worker_lab/cli.py` - passed.
- `python -m pytest tests/test_workspace_receipt.py tests/test_cli.py -q` - first run failed with two local defects: missing workspace was not normalized to `LabValidationError`, and a test transition timestamp moved backward.
- `python -m pytest tests/test_workspace_receipt.py tests/test_cli.py -q` - passed: 63 passed, 2 skipped.
- `python -m py_compile worker_lab/workspace.py worker_lab/cli.py tests/test_workspace_receipt.py tests/test_cli.py` - passed.
- `python -m py_compile worker_lab/__init__.py` - passed.
- `python -m compileall -q worker_lab tests` - passed twice, including the final run.
- `python -m pytest -q tests/test_canonical.py tests/test_models.py tests/test_policy.py tests/test_test_catalog.py tests/test_lifecycle.py tests/test_attempt_store.py tests/test_storage.py tests/test_workspace_receipt.py tests/test_validation.py tests/test_evidence.py tests/test_cli.py` - passed first at 164 passed, 3 skipped; passed finally at 165 passed, 4 skipped.
- `git status --short; git diff --stat; git diff --check` - passed; no whitespace errors.
- `python -m pytest tests/test_workspace_receipt.py -k verify_workspace -q` - correction-pass focused validation passed: 16 passed, 3 skipped, 41 deselected.
- `python -m compileall -q worker_lab tests` - correction-pass catalog compile passed.
- `python -m pytest -q tests/test_canonical.py tests/test_models.py tests/test_policy.py tests/test_test_catalog.py tests/test_lifecycle.py tests/test_attempt_store.py tests/test_storage.py tests/test_workspace_receipt.py tests/test_validation.py tests/test_evidence.py tests/test_cli.py` - correction-pass catalog union passed: 165 passed, 5 skipped.
- Requested `Sol High` final review - not run: that named agent is not registered in this VS Code session, and no substitute was used.

## Verification status

Passed: focused workspace/CLI verification tests (final run: 64 passed, 3 skipped), correction-pass verification tests (16 passed, 3 skipped, 41 deselected), and the runnable catalog-selected union (`T004`, `T006`, `T007`, `T008`, `T009`, `T012`, `T015`, `T017`, `T018`, and `T019`) with their runnable prerequisites.

Failed: one intermediate focused test run, corrected within the allowed scope and rerun successfully.

Skipped: five Windows symlink cases because directory symlink creation is unavailable in this environment: one storage fixture and four workspace state/root/workspace reparse fixtures. The tests explicitly skip only when fixture creation fails.

Not run: framework-evaluator-only `T001` through `T003` and `T011`, because the trial prohibits Autonomous Worker Framework invocation. The full milestone suite was not run, as instructed.

## Assumptions and judgment calls

- Verification will reuse the established authority and prepared-repository validation helpers, with receipt binding checks kept local to the workspace module.
- The supplied verification root can be validated against Worker Lab and Git containment without resolving the exercise template's declared repository identity to a local filesystem path; the receipt and protected authority binding still require its exact declared identity.

## Unresolved risks or requested scope expansions

- Accepted Phase 2 limitation: the receipt schema contains canonical root and path digests but no durable filesystem directory identity. A replacement workspace at the exact attempt-bound path is accepted when it independently satisfies the receipt, commit, detached-HEAD, clean-tree, context, remote, alternates, nested-repository, and reparse checks. Physical NTFS directory identity tracking is deferred because it adds disproportionate complexity without protecting against a present worker capability. Revisit only if the threat model expands.

## Prohibited actions

No commit, push, remote access, deletion, or external-repository access occurred.

## Final Git outputs

`git status --short`:

```text
 M tests/test_cli.py
 M tests/test_workspace_receipt.py
 M worker_lab/__init__.py
 M worker_lab/cli.py
 M worker_lab/workspace.py
?? TERRA_REPORT.md
```

`git diff --stat`:

```text
 tests/test_cli.py               |  29 ++++++
 tests/test_workspace_receipt.py | 226 ++++++++++++++++++++++++++++++++++++++++
 worker_lab/__init__.py          |   3 +-
 worker_lab/cli.py               |  10 +-
 worker_lab/workspace.py         |  80 ++++++++++++++
 5 files changed, 346 insertions(+), 2 deletions(-)
```