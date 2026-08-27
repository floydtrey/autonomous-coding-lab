# Worker Lab Phase 2 Specification

**Status:** Active implementation authority
**Approved by:** `PHASE2_READINESS_REVIEW.md`
**Starting milestone:** `v0.1.2-phase1`
**Scope:** Synthetic local exercise workspaces only

## Objective

Phase 2 adds a trusted exercise-workspace factory around the protected Phase 1 records. It prepares
an isolated disposable Git workspace from an explicit local synthetic template, verifies the exact
workspace after process restart, and safely disposes of only the workspace bound to the attempt.

Phase 2 does not invoke Codex or the Autonomous Worker Framework. It does not run a coding worker,
evaluate a candidate, publish code, or use an external product repository. Those boundaries remain
closed.

## Authority

The trusted controller selects the attempt, local template repository, and workspace root and runs
the operator commands. A worker has no access to Worker Lab state, receipts, template sources, Git
configuration, credentials, cleanup authority, or publication authority.

Current user/platform instructions and verified Git/filesystem state outrank this document. The
permanent policy, role, lifecycle, canonical identity, and test-ID meanings remain protected. Phase 2
may extend their project binding but may not weaken or redefine them.

## Inputs and repository separation

Preparation requires:

- an existing `DRAFT` attempt whose exercise and authority relations validate;
- an explicit local filesystem path to the template repository;
- an explicit local workspace-root path; and
- the exercise's exact full lowercase template commit.

The template source must be a real local directory and Git work tree, not a URL, symlink, junction,
or other reparse-point indirection. It must be clean, resolve to the context repository identity, and
contain the exact exercise commit and context bytes. Preparation must not change it.

The workspace root must be a real local directory, not a link or reparse point. It must not equal,
contain, or be contained by Worker Lab, the template repository, or another protected repository
known to the caller. The final workspace is exactly `<workspace-root>/<attempt-id>` and must not
already exist. Phase 3 must additionally prove separation from the framework before invocation.

## Git workspace construction

The factory must:

1. Revalidate the attempt, exercise, template, commit, context, and paths.
2. Create a uniquely named sibling staging directory under the supplied workspace root.
3. Clone locally with independent Git objects (`git clone --no-local`).
4. Check out the exact starting commit in detached-HEAD state.
5. Verify the repository root, exact HEAD, detached state, clean status, and assigned context bytes.
6. Write and verify the ephemeral receipt through a staged atomic operation.
7. Atomically publish the staging directory as `<workspace-root>/<attempt-id>`.
8. Reverify the published workspace and receipt.
9. Advance the attempt from `DRAFT` to `READY` only after every prior boundary succeeds.

Git subprocesses are non-interactive, receive no inherited GitHub credential-like variables, and
have finite timeouts. Network sources, submodule fetching, Git LFS fetching, hooks, and shared local
object stores are out of scope. The first failed boundary stops the operation. Preparation failure
leaves the attempt in `DRAFT`, publishes no receipt or final workspace, and removes only its own
validated staging path.

## Ephemeral workspace receipt

Receipts use `worker-lab-workspace-receipt:v1` and live at
`state/workspaces/<attempt-id>.json`. This directory is explicitly ephemeral even though it is below
`state/`; backup and restore must exclude it.

The strict receipt fields are:

| Field | Contract |
|---|---|
| `schema_version` | Exact receipt schema. |
| `attempt_id` | Existing protected attempt identity. |
| `exercise_id`, `exercise_version` | Exact exercise identity. |
| `template_repository` | Declared template repository identity from the exercise/context. |
| `template_commit` | Exact starting commit. |
| `workspace_root_digest` | Canonical digest of the resolved operator-supplied root. |
| `workspace_path_digest` | Canonical digest of the resolved current workspace/quarantine path. |
| `workspace_relative_path` | Exact attempt ID when prepared; deterministic attempt-bound quarantine name when quarantined. |
| `created_at` | UTC, second precision, `Z` suffix. |
| `state` | `PREPARED` or `QUARANTINED`. |

The receipt stores no usable absolute path. The operator supplies the workspace root again for every
verify or discard operation; its canonical digest and the derived child-path digest must match the
receipt. The receipt is evidence for exact targeting, not a new grant of authority. Missing,
malformed, stale, moved, or substituted receipts and paths fail closed.

## Verification after restart

Verification reloads protected records and the strict receipt, resolves the supplied root again, and
checks all receipt bindings. It then verifies the exact Git root, detached starting commit, clean
status, and assigned context content. It rejects a missing workspace, dirty content, branch checkout,
changed HEAD, nested repository, path substitution, link/reparse point, or context mismatch.

Successful verification does not change attempt state. Phase 2 leaves `runtime_identity` and
`candidate_digest` unset.

## Safe disposal

Disposal never accepts a free-form target path. It accepts the attempt ID and workspace root, derives
the only permitted target, and requires the receipt, protected attempt, root digest, child digest,
directory identity, and link/reparse checks to agree.

The prepared directory is atomically renamed to the deterministic attempt-bound quarantine path
before recursive deletion. Only that validated quarantine path may be removed. The receipt is
updated to `QUARANTINED` when possible and retained until deletion and the attempt transition are
known. Retry logic must recognize an interrupted rename, receipt update, deletion, or attempt write
without widening the deletion target.

After confirmed disposal, the attempt may advance from `READY` to `ABORTED` with an actual cleanup
outcome. A new run uses a new linked attempt. Phase 2 never advances an attempt to `RUNNING`.

## Backup and restore

Disposable workspaces are outside the Lab repository. `state/workspaces/` receipts, staging paths,
and quarantine paths are excluded from durable backups. Durable attempt history remains in scope.

After restore, an attempt that was `READY` without a verified local receipt and workspace cannot
resume. The trusted controller records the workspace-not-restored outcome, aborts it through the
defined recovery path, and creates a new linked attempt when retry is desired.

## Operator interface target

Later Phase 2 batches add these bounded commands:

```text
worker-lab prepare-workspace <attempt-id> --template-repository <path> --workspace-root <path>
worker-lab verify-workspace <attempt-id> --workspace-root <path>
worker-lab discard-workspace <attempt-id> --workspace-root <path> --cleanup-outcome <text>
```

Failures use the existing nonzero status and stable `ERROR <CODE>:` contract. Commands stop at the
first failed boundary and do not silently continue, repair, select a different path, or broaden scope.

## Test selection

The immutable `worker-lab-v2` catalog is the active Phase 2 binding. `WORKSPACE_CHANGE:v1` is the
routine profile for workspace receipt, preparation, verification, and
cleanup changes. It includes permanent security regression (`T015`), cleanup (`T017`), runtime
compatibility (`T018`), containment, lifecycle, canonical identity, and focused integration. Add
`T012` when the CLI changes. Run the full `MILESTONE:v1` gate only at the Phase 2 milestone.

## Delivery batches

1. Specification, strict receipt schema, T015/T018 bindings, and `WORKSPACE_CHANGE:v1`.
2. Staged preparation, verification before publication, compensation, and `DRAFT` to `READY`.
3. Restart verification, quarantine cleanup, idempotent recovery, and `READY` to `ABORTED`.
4. CLI acceptance, full suite, external backup/rollback drill, handoff update, and named milestone.

The completion conditions in `PHASE2_READINESS_REVIEW.md` are the finish line. Work that does not
advance one of them or fix a blocking correctness/security defect is deferred.

## Explicit exclusions

No Codex invocation, framework adapter, worker execution, candidate digest, evaluator execution,
approval packet, failure-classification automation, repair loop, dashboard, real curriculum
application, graduation, remote template fetch, concurrent-attempt scheduler, generalized permission
system, worker GitHub action, or external product-repository work belongs in Phase 2.
