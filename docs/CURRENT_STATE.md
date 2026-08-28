# Current State

**Last updated:** 2026-08-28
**Status:** Phase 2 complete at `v0.2.0-phase2`; Phase 3A specification handoff prepared; worker
execution remains unavailable.

## Repository

- Path: `C:\Users\MineTrackerWorker\repos\worker-lab`
- Integrated branch: `main`
- Starting checkpoint: `b7f5bac` / `v0.1.0-phase1`
- Corrected validation milestone: `v0.1.1-phase1`
- Governance/publication milestone: `v0.1.2-phase1`
- Integrated Phase 2 Batch 1: `12048ea` / PR `#1`
- Integrated Phase 2 Batch 2: `97ecb34` / PR `#2`
- Integrated Phase 2 Batch 3: `0e01168` / PR `#3`
- Phase 2 milestone: `v0.2.0-phase2`
- Active development branch: `phase3/framework-interface-spec-v1`
- Private remote: `https://github.com/floydtrey/worker-lab`

## Audit conclusion

The original Phase 1 checkpoint remains a useful historical pre-audit foundation and its tag was
not moved. Batches 1–4 corrected its authority identity, record integrity, test planning, evidence,
backup/restore, acceptance coverage, and recovery evidence. `v0.1.1-phase1` remains the immutable
validation basis. `v0.1.2-phase1` adds the Phase 2 readiness decision and private publication
checkpoint and is the trusted starting point for new work.

## Completed correction batches

Follow `PHASE1_AUDIT_CHECKLIST.md`. Batch 1 establishes:

- authoritative permanent test meanings with a strict Worker Lab binding;
- non-overridable policy invariants and versioned role maxima;
- deny-wins task restrictions and structured role mismatch;
- exact read-only context manifests verified against a separate clean Git repository;
- attempt identities bound to resolved policy, role, sandbox, context, and evaluator digests.

Batch 2 establishes:

- structured, non-mutating storage failures and pure read/list operations;
- lifecycle-aware attempt storage with immutable terminal history and linked retry records;
- exact relationship validation across curricula, exercises, authority, attempts, evidence, failures,
  and evaluator identity;
- canonical path and writable/protected scope validation; and
- preserved curriculum exercise order with deterministic set-like fields.

Batch 3 establishes:

- dependency-respecting test plans with cost-aware selection among currently eligible tests;
- retained-content evidence identities bound directly to attempt, candidate, base, environment,
  exact catalog digest, and test;
- backup scope limited to durable `curricula/` and `state/` content; and
- staged, verified, empty-destination-only backup publication and restore with failure cleanup.

Batch 4 establishes:

- a uniform acceptance matrix for every protected record;
- a complete synthetic CLI workflow through attempt closure, evidence verification, backup, and
  restored inspection;
- external durable-data backup and restore evidence; and
- an independently cloned Git rollback checkout that passed the complete suite.

All four correction batches are committed and validated. See `MILESTONE_EVIDENCE.md` for exact
recovery artifacts. The Phase 2 review is recorded in `PHASE2_READINESS_REVIEW.md`.

## Phase 2 workspace checkpoints

- `PHASE2_SPEC.md` defines the preparation, restart verification, safe-disposal, recovery, and backup
  contracts without authorizing framework or worker execution.
- `worker-lab-workspace-receipt:v1` strictly binds attempt, exercise/template, starting commit,
  canonical root/path digests, attempt-bound relative path, timestamp, and receipt state.
- Receipts contain no usable absolute path and remain excluded from durable backup under
  `state/workspaces/`.
- Permanent T015 and T018 meanings now have immutable `worker-lab-v2` bindings, and
  `WORKSPACE_CHANGE:v1` selects
  the focused workspace security/lifecycle/runtime boundary.
- Active catalog digest:
  `sha256:fe3d50c4c0692a3d0fee0ea97690a3f1d0272a31052c0afe0489cd4e6fce44aa`.
- Batch 2 added strict attempt-authority revalidation, local-template and workspace-root validation,
  independent staged cloning, detached exact-commit checkout, remote removal, context verification,
  atomic publication, an ephemeral receipt, failure compensation, and `DRAFT` to `READY`.
- Git subprocesses ignore inherited Git configuration, run non-interactively with finite timeouts,
  and receive no GitHub credential-like or Git path-redirection variables.
- Preparation rejects dirty or changed templates, linked/reparse paths, submodules, alternate object
  stores, protected-root overlap, preexisting targets or receipts, and non-clean `DRAFT` attempts.
- Batch 3 was merged through PR #3 at `0e01168`: restart verification fails closed without mutation,
  and receipt-bound disposal quarantines before deletion, recovers interruptions, records the actual
  cleanup outcome, and transitions `READY` to `ABORTED` without entering `RUNNING`.
- Batch 4 completed synthetic public CLI and durable backup/restore acceptance coverage. The complete
  active suite passed 257 tests with six expected Windows symlink capability skips both in Terra's
  candidate workspace and in an independent checkout reconstructed from the preflight bundle.
- External durable-data backup and restore verified seven files. The complete recovery identities and
  paths are recorded in `PHASE2_MILESTONE_EVIDENCE.md`.

## Still unavailable

- worker execution or framework invocation;
- dashboard, real curricula, worker attempts, or graduation decisions.

## Next boundary

Phase 3A is a documentation-only specification of the bounded Worker Lab-to-Autonomous Worker
Framework interface and the first synthetic worker exercise. `TERRA_PHASE3A.md` is the active bounded
handoff. Its output requires trusted review before implementation. The Phase 2 milestone and Phase 3A
handoff do not authorize worker execution, framework invocation, or work in an external product
repository.

## Drift boundary

Do not invoke workers or modify external product repositories until Phase 3 authority is explicitly
approved. Ordinary polish and speculative abstractions remain deferred.
