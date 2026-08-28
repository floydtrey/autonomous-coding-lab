# Terra Medium Handoff: Phase 2 Batch 4A

**Status:** Bounded implementation instruction; not permanent project authority
**Model:** GPT-5.6 Terra, medium reasoning
**Repository:** `C:\Users\MineTrackerWorker\repos\worker-lab`
**Required branch:** `phase2/batch4-acceptance-v1`

## Objective

Prepare the codebase for the Phase 2 milestone by completing synthetic CLI acceptance, proving
backup/restore exclusions and restored-attempt behavior, running the complete suite once, and updating
pre-milestone documentation accurately.

This is Batch 4A. Stop before external rollback artifacts, commits, pushes, pull requests, tags, or a
claim that the Phase 2 milestone is complete. The trusted manager performs those Batch 4B closure
actions after reviewing the proposal.

## Starting checks

Before editing:

1. Confirm the repository path, required branch, HEAD, and `git status --short`.
2. Confirm this file exists in `HEAD`; that commit is the approved starting checkpoint.
3. The only permitted pre-existing untracked files are:
   - `Worker-Lab_8_28_26.zip`
   - `docs/8_27_26_ChatGPT_History`
4. Do not open, modify, stage, move, or delete either permitted untracked file.
5. Stop and report any other discrepancy before editing.

Do not fetch, pull, push, contact a remote, install dependencies, access credentials, access another
repository, or invoke a worker/framework.

## Efficient context loading

Follow `docs/START_HERE.md`. This is a new session, so read only:

1. `docs/START_HERE.md`
2. Phase 2 status and next-boundary sections in `docs/CURRENT_STATE.md`
3. Backup, operator-interface, testing, delivery-batch, and exclusion sections of
   `docs/PHASE2_SPEC.md`
4. P2-C11 and P2-C12 in `docs/PHASE2_READINESS_REVIEW.md`
5. milestone profile and T010/T012/T020/T021 meanings in `docs/TEST_CATALOG.md`
6. `README.md`
7. `worker_lab/backup.py`
8. `tests/test_backup.py`
9. the existing workspace and CLI acceptance tests directly relevant to this task

Do not read Phase 1 audit documents except the concise milestone evidence file if its format is needed.
Do not read old Terra reports, the exported conversation, or the ZIP. Record the starting HEAD and the
files consulted once in `TERRA_BATCH4_REPORT.md`; do not reread unchanged files in this session.

## Exact implementation task

Add the minimum acceptance coverage needed to prove the integrated Phase 2 workflow through public
operator commands. Reuse existing fixtures and helpers where practical without making tests dependent
on execution order.

### A. Complete synthetic CLI workflow

Prove one temporary synthetic attempt can:

1. be created as `DRAFT` from the exact local template;
2. be prepared through `prepare-workspace` and become `READY`;
3. be verified through `verify-workspace` without mutation;
4. be disposed through `discard-workspace` and become `ABORTED` with the exact cleanup outcome;
5. be discarded again with the same outcome as an idempotent no-write success; and
6. finish with no prepared workspace, quarantine directory, or ephemeral receipt.

Assert that Phase 2 never enters `RUNNING`, never creates candidate/runtime identity, and never adds a
remote or alternate object store to the prepared workspace.

### B. Backup and restored-attempt boundary

Using only temporary test directories, prove that a backup taken while an attempt is `READY`:

- includes the durable attempt and protected definitions;
- excludes `state/workspaces/`, receipt files, workspace/staging/quarantine content, caches, and
  repository internals;
- verifies and restores only into an empty destination;
- restores the durable attempt as `READY` without manufacturing a receipt or workspace;
- cannot pass `verify-workspace` or resume execution after restore; and
- can be terminally recorded through the existing trusted recovery path with a precise
  `workspace not restored` cleanup outcome, after which a new retry would require a new linked
  attempt.

Do not add disposable workspace content to the durable backup format. Do not create a second recovery
authority system merely for this acceptance test.

### C. Documentation preparation

After the focused and complete tests pass:

- update `README.md` with the integrated `verify-workspace` and `discard-workspace` commands and an
  accurate Phase 2 Batch 3 status;
- update `docs/CURRENT_STATE.md` to record the integrated Batch 3 PR/merge and Batch 4A validation
  candidate;
- do not claim the Phase 2 milestone, external rollback drill, tag, final bundle, or Batch 4B is
  complete;
- create `TERRA_BATCH4_REPORT.md` with exact evidence and remaining manager-owned closure work.

## Production-code boundary

This batch is acceptance and documentation work. Do not modify production Python files, schemas,
catalogs, policies, lifecycle rules, or workspace behavior. If an acceptance test exposes a genuine
production defect, stop at that first failed boundary and record the smallest reproducible defect in
the report for the trusted manager.

## Allowed files

You may modify only:

- `tests/test_cli.py`
- `tests/test_backup.py`
- `README.md`
- `docs/CURRENT_STATE.md`
- `TERRA_BATCH4_REPORT.md` (create)

Treat `TERRA_BATCH4.md`, `docs/START_HERE.md`, `LIMITED_TO_DO.md`, all production code, catalogs,
authority documents, historical exports, and backup files as read-only.

## Validation plan

Use the smallest loop:

1. Run only the new/changed CLI and backup acceptance tests while developing.
2. Run compilation for changed Python test files.
3. Once focused tests pass, run the complete active test suite exactly once for the Phase 2 milestone
   candidate.
4. Run `git diff --check` and non-mutating final status/diff summaries.
5. Do not rerun the full suite after documentation-only edits.

Stop at the first required failure. Diagnose only the failing boundary and do not widen scope.

## Report requirements

`TERRA_BATCH4_REPORT.md` must contain:

- model/reasoning effort, starting branch, HEAD, and status;
- the exact context files consulted and confirmation that unchanged files were not reread;
- every file changed;
- acceptance behaviors added;
- exact commands and results, including pass/fail/skip counts and elapsed time;
- confirmation that the ZIP and chat export were not opened or modified;
- assumptions, limitations, and any defect requiring manager authority;
- confirmation of no production-code, remote, external-repository, commit, push, tag, or external
  backup mutation;
- final `git status --short`, `git diff --stat`, and `git diff --check` results; and
- a precise Batch 4B handoff: trusted review, selected commit/PR, external backup and rollback clone,
  rollback-suite evidence, final documentation, merge, tag, and final bundle.

Leave the complete proposal uncommitted for trusted review.
