# Terra Controlled Trial: Phase 2 Batch 3A

**Status:** Temporary experiment instruction; not project authority
**Model target:** GPT-5.6 Terra, medium reasoning
**Repository:** `C:\Users\MineTrackerWorker\repos\worker-lab`
**Trial branch:** `experiment/terra-batch3-verification`
**Starting main checkpoint:** `c2126c93a95d3253925fde53b794cd9bceb391be`

## Purpose

This is a controlled trial of Terra as a bounded coding agent. Implement only Phase 2 Batch 3A:
restart verification of an already prepared synthetic workspace. Do not implement workspace
disposal, quarantine deletion, worker execution, or any later-phase behavior.

The trusted programmer will review every change. Your changes are proposals, not accepted project
authority.

## Mandatory starting checks

Before editing:

1. Confirm the repository path, current branch, current HEAD, and working-tree cleanliness with
   non-mutating Git commands.
2. The branch must be `experiment/terra-batch3-verification`.
3. The working tree must be clean and HEAD must contain this instruction file.
4. If any check differs, stop and report the exact discrepancy without editing.
5. Record the starting branch and HEAD in `TERRA_REPORT.md` when work begins.

Do not fetch, pull, push, contact a remote, install dependencies, or read credentials.

## Authority and required reading

Current user and platform instructions outrank repository documents. Within the repository, read in
this order:

1. `docs/START_HERE.md`
2. `docs/CURRENT_STATE.md`
3. `docs/PHASE2_READINESS_REVIEW.md`
4. `docs/PHASE2_SPEC.md`
5. `docs/POLICY_MODEL.md`
6. `docs/TEST_CATALOG.md`
7. `worker_lab/workspace.py`
8. `worker_lab/models.py`
9. `worker_lab/validation.py`
10. `worker_lab/attempt_store.py`
11. `worker_lab/lifecycle.py`
12. `worker_lab/storage.py`
13. `worker_lab/cli.py`
14. `tests/test_workspace_receipt.py`
15. `tests/test_cli.py`

Do not reinterpret or weaken permanent authority, lifecycle, receipt identity, containment, or
numbered-test meanings. Historical text and this trial file do not override the authoritative
documents above.

## Exact task

Implement restart-safe workspace verification for a previously prepared attempt.

Add a public `verify_workspace` operation in `worker_lab/workspace.py` and expose it through the
operator command:

```text
worker-lab verify-workspace <attempt-id> --workspace-root <path>
```

Successful verification returns the validated existing `WorkspaceReceipt`. It performs no writes
and does not change the attempt, receipt, repository, or filesystem.

Verification must:

1. Resolve Worker Lab and the operator-supplied workspace root as real local directories without
   symlink, junction, or reparse-point indirection.
2. Reload the attempt and require the exact prepared state: `READY`, with no runtime identity,
   candidate digest, or cleanup outcome.
3. Reload the strict receipt from `state/workspaces/<attempt-id>.json` and require `PREPARED`.
4. Reload and validate the attempt's exact exercise, policy, role, context manifest, and immutable
   catalog binding using the existing authority-validation seam.
5. Verify every receipt binding against the protected attempt and exercise: attempt, exercise,
   template identity, exact starting commit, canonical root digest, derived child-path digest, and
   exact relative path.
6. Derive the only permitted workspace as `<workspace-root>/<attempt-id>`. Never accept a free-form
   workspace target.
7. Verify the exact Git root, detached HEAD, exact starting commit, clean tracked and untracked
   status, no remotes, no alternate object store, and exact assigned context bytes.
8. Explicitly reject a nested Git repository even when it is ignored and would not make ordinary
   Git status dirty.
9. Reject missing, malformed, stale, moved, substituted, linked, dirty, branched, changed-commit,
   changed-context, remote-added, alternate-object, and nested-repository states.
10. Stop at the first failed boundary with a stable `LabValidationError` code.

Reuse existing verified helpers where their contracts fit. Keep new logic small and cohesive. Do not
create a generalized permission system, recovery engine, new schema, or new durable record.

## Required tests

Add focused cases to the existing catalog-bound workspace tests. At minimum prove:

- successful verification through a newly constructed controller/store after preparation;
- success leaves the attempt and receipt byte-for-byte unchanged;
- wrong root or workspace-path substitution fails;
- missing, malformed, or identity-altered receipt fails;
- non-`READY` attempt or non-`PREPARED` receipt fails;
- missing workspace fails;
- dirty tracked and untracked content fails;
- branch checkout and changed HEAD fail;
- added remote and alternate object store fail;
- changed assigned context fails;
- nested Git repository fails even if ignored;
- workspace/root reparse indirection fails when Windows permits creating the test fixture;
- CLI success and stable CLI failure output.

Tests must assert the attempt state, receipt state, and filesystem postcondition after failures. A
failed verification must not repair, delete, rename, quarantine, or mutate anything.

## Allowed files

You may modify only:

- `worker_lab/workspace.py`
- `worker_lab/cli.py`
- `worker_lab/__init__.py`
- `tests/test_workspace_receipt.py`
- `tests/test_cli.py`
- `TERRA_REPORT.md` (create this report)

Do not modify `TERRA.md`. Treat every other file as read-only. If the task appears to require another
file, stop and explain why in the report instead of widening scope.

## Explicit prohibitions

Do not:

- implement `discard_workspace`, quarantine, recursive deletion, or cleanup recovery;
- alter `AttemptRecord`, `WorkspaceReceipt`, lifecycle transitions, policy, roles, catalogs, or
  authoritative phase documents;
- use the generic transition command to simulate verification;
- enter `RUNNING` or invoke Codex/the Autonomous Worker Framework;
- access or modify Mine Tracker or any other repository;
- add dependencies;
- run network commands;
- commit, push, merge, tag, reset, restore, or delete branches;
- suppress, skip, weaken, or rewrite existing tests to make the change pass.

## Efficient validation

Use the smallest applicable loop:

1. Compile changed Python files.
2. Run the directly affected workspace and CLI tests while developing.
3. After focused tests pass, run the existing catalog-selected union needed for
   `WORKSPACE_CHANGE:v1` plus `T012` because the CLI changes.
4. Do not run the complete milestone suite.
5. Stop at the first failed required boundary; diagnose and correct only in-scope defects.

## Required report

Create `TERRA_REPORT.md` before finishing. It must include:

- model and reasoning effort, if visible;
- starting branch and HEAD;
- concise implementation summary;
- every file created or modified;
- every behavior and stable error code added;
- exact commands run and their outcomes;
- tests passed, failed, and skipped;
- assumptions and judgment calls;
- unresolved risks or requested scope expansions;
- confirmation that no commit, push, remote access, deletion, or external-repository access occurred;
- final `git status --short` and `git diff --stat` output.

Do not claim success if a required test did not run or pass. Leave all proposed changes uncommitted so
the trusted programmer can inspect the complete diff.
