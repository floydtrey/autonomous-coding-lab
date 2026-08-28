# Terra Controlled Trial: Phase 2 Batch 3B

**Status:** Temporary experiment instruction; not project authority
**Model target:** GPT-5.6 Terra, medium reasoning
**Repository:** `C:\Users\MineTrackerWorker\repos\worker-lab`
**Trial branch:** `experiment/terra-batch3-verification`
**Baseline HEAD:** `ee574fd0483afa2fcb926462f21ebcc0245555f8`

## Purpose

Implement only Phase 2 Batch 3B: safe disposal and retry recovery for the synthetic workspace prepared by Batch 2 and verified by Batch 3A. Batch 3A proposed changes are an accepted, uncommitted baseline for this trial. The user-provided `docs/8_27_26_ChatGPT_History` is an untracked read-only historical reference, not authority.

The trusted programmer will review every proposed change. Leave all changes uncommitted.

## Required starting record

Record the current branch, HEAD, and complete `git status --short` output in `TERRA_3B_REPORT.md` before implementation. The permitted baseline is the existing uncommitted Batch 3A proposal plus `docs/8_27_26_ChatGPT_History`; stop if another unrelated change appears.

Do not fetch, pull, push, contact a remote, install dependencies, read credentials, commit, reset, restore, delete branches, access another repository, invoke a framework, or invoke a coding worker.

## Authority and scope

Current user and platform instructions outrank repository documents. Read and preserve the active Phase 2 authority, policy, lifecycle, receipt, storage-containment, and catalog contracts. This instruction narrows work to disposal; it cannot weaken permanent authority.

## Exact task

Add public `discard_workspace` in `worker_lab/workspace.py` and expose:

```text
worker-lab discard-workspace <attempt-id> --workspace-root <path> --cleanup-outcome <text>
```

The operation accepts no free-form deletion target. It derives only:

```text
final: <workspace-root>/<attempt-id>
quarantine: <workspace-root>/.worker-lab-quarantine-<attempt-id>
```

It must:

1. Resolve the Lab, state/attempt/receipt paths, workspace root, final, and quarantine identities without symlink, junction, or reparse indirection.
2. Require a clean `READY` attempt with no runtime identity, candidate digest, or existing cleanup outcome; validate its exact authority binding.
3. Load a strict receipt and validate all attempt, exercise, root, and path bindings.
4. For a `PREPARED` receipt: require only the final workspace to exist, fully verify it using the existing prepared-repository checks, atomically rename it to the deterministic quarantine path, then write and reread an exact `QUARANTINED` receipt before any deletion.
5. For a `QUARANTINED` receipt: require only the quarantine workspace to exist, validate its receipt/root binding and contained tree, then resume deletion. Do not require it to remain Git-clean after the receipt was durably quarantined.
6. If a prior rename left a `PREPARED` receipt with only quarantine present, validate the quarantined directory as the exact moved workspace and durably promote the receipt to `QUARANTINED` before deletion.
7. Remove only a validated quarantine tree. Reject every link/reparse entry before recursion and tolerate read-only Git files through the existing removal helper.
8. Persist `READY -> ABORTED` only after deletion is confirmed absent, with the exact non-empty operator cleanup outcome. Remove the receipt only after the transition succeeds.
9. Resume a known deletion-complete state (`READY` + `QUARANTINED` receipt + neither directory) by persisting the terminal transition and then removing the stale receipt.
10. Fail closed, without repair or deletion, for ambiguous/moved/substituted states: missing receipt, both final and quarantine, `PREPARED` receipt with neither directory, `QUARANTINED` receipt with final present, malformed receipt, invalid root, or non-ready attempt.
11. Handle `ABORTED` only as a stale-receipt finalization state: no final or quarantine directory and one valid `QUARANTINED` receipt may be removed. Any remaining final/quarantine directory must fail closed.
12. Stop at the first failed boundary with stable `LabValidationError` codes. Do not add a schema, generalized recovery service, filesystem-ID tracking, worker execution, or a new lifecycle transition.

Same-path workspace replacement remains the accepted Phase 2 limitation recorded in `TERRA_REPORT.md`: physical filesystem identity is not tracked when all existing receipt, Git, context, and containment checks independently pass.

## Required tests

Add focused catalog-bound tests in `tests/test_workspace_receipt.py` and `tests/test_cli.py` for:

- successful final workspace quarantine, deletion, `ABORTED` transition, and receipt removal;
- CLI success and stable failure output;
- `PREPARED` rename-interruption recovery;
- `QUARANTINED` deletion-interruption recovery;
- deletion-complete transition recovery;
- transition-write failure leaves a verified stale quarantine receipt and no terminal transition;
- missing/malformed/substituted receipt and all ambiguous final/quarantine combinations;
- dirty/reparse/substituted final workspace fails before rename;
- read-only files are removed when supported;
- reparse root/final/quarantine cases skip only when Windows cannot create the fixture;
- every failure asserts attempt state, receipt state/bytes, and final/quarantine filesystem postcondition.

## Allowed files

Modify only:

- `worker_lab/workspace.py`
- `worker_lab/cli.py`
- `worker_lab/__init__.py`
- `tests/test_workspace_receipt.py`
- `tests/test_cli.py`
- `TERRA_3B.md`
- `TERRA_3B_REPORT.md`

Do not modify `TERRA.md`, `TERRA_REPORT.md`, `docs/`, protected definitions, models, lifecycle, storage, catalogs, or other files.

## Validation

Use `python -m pytest tests/test_workspace_receipt.py -k discard_workspace -q` while developing. Compile changed Python files after implementation. After focused tests pass, run the de-duplicated runnable `WORKSPACE_CHANGE:v1` plus `T012` union exactly once. Do not run the complete milestone suite.

## Required report

Create `TERRA_3B_REPORT.md` before finishing. Include the starting record, implementation and stable-code summary, all changed files, exact commands/outcomes, passed/failed/skipped tests, assumptions, accepted limitations, unresolved risks, confirmation of prohibited actions, and final `git status --short` plus `git diff --stat` output.
