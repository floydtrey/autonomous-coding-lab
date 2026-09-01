# Phase 3 Readiness Review

**Status:** Approved for non-executing Batch 3B only
**Date:** 2026-08-28
**Starting milestone:** `v0.2.0-phase2`
**Decision:** Batch 3B approved; worker execution remains prohibited

## Trusted review decision

The specification preserves repository, authority, credential, sandbox, lifecycle, and failure
boundaries and is proportionate to the first integration. Approve the fixed local JSON adapter,
invocation-digest runtime identity, and immutable `worker-lab-v3` direction for Batch 3B.

Batch 3B may implement strict records, storage, catalog bindings, and fake/injected non-executing
adapter preparation only. Before Batch 3C, trusted review must approve tested Windows child-process
containment, final prompt/result size and redaction limits, exact runtime identity, and a new framework
milestone containing the adapter. No Codex invocation or `READY -> RUNNING` is authorized now.

## Decision summary

The existing repositories support a narrow Phase 3 design without copying framework security or
building a generalized orchestration system. A fixed local canonical-JSON adapter is the smallest
credible boundary because the repositories are separate and the framework is not an installed stable
library.

Current framework contracts are precedents, not sufficient Worker Lab protocols. The read-only probe
uses a consumer-specific default and returns insufficient non-mutation/process identity. The general
code task lacks a strict failure result and candidate content digest. The commissioning task/result
contracts are purposefully narrower or carry repository-handoff/repair semantics excluded from Phase
3. New project-agnostic invocation/result contracts are therefore required.

Approval of this review authorizes only Batch 3B schemas, storage, immutable test binding, and a
non-executing adapter preparation seam using injected executors. It does not authorize Codex,
`READY -> RUNNING`, a real attempt, or an external product repository.

## Phase 3 completion conditions

- P3-C01 — A strict versioned invocation record binds attempt, authority, context, task, catalog,
  test plan, framework, runtime, workspace receipt, path, prompt, and authorization identities.
- P3-C02 — A strict versioned result binds the exact invocation and records structured process,
  workspace, candidate/proposal, validation, first-failure, containment, and content identities.
- P3-C03 — Unknown fields, unsupported versions, stale/dirty repository identities, missing records,
  and every digest mismatch fail closed before worker execution.
- P3-C04 — Worker Lab invokes one fixed framework-owned local adapter; exercises and workers cannot
  control executables, raw arguments, environment, working directory, or Codex options.
- P3-C05 — The adapter continues to enforce ChatGPT-managed authentication, API-key rejection,
  GitHub credential stripping, audited runtime identity, finite timeout, and only read-only or
  workspace-write sandbox modes.
- P3-C06 — Worker Lab does not duplicate framework authentication, credential, sandbox, or Codex
  subprocess logic, and the framework does not write Worker Lab records or decide lifecycle.
- P3-C07 — Deterministic non-executing preparation produces the same prompt and runtime identities
  later required for execution.
- P3-C08 — `READY -> RUNNING` occurs only after workspace/receipt revalidation, exact authorization,
  framework preflight, and durable invocation custody; `runtime_identity` binds the invocation.
- P3-C09 — Restart state distinguishes never-authorized, never-dispatched, uncertain, and terminal
  outcomes without silently rerunning an invocation.
- P3-C10 — An uncertain invocation cannot be retried, verified, mutated, or disposed until trusted
  process-absence evidence proves the adapter and worker are no longer active.
- P3-C11 — A read-only proposal leaves HEAD, index, worktree, Git configuration, remotes, alternates,
  receipt, attempt, and every workspace file byte unchanged.
- P3-C12 — A proposal reaches `CANDIDATE` only through a strict result and independently recomputed
  proposal digest with exactly zero changed paths.
- P3-C13 — A code task operates on a fresh synthetic workspace, preserves detached HEAD and protected
  boundaries, and changes exactly the sealed writable paths.
- P3-C14 — Candidate content identity is independently recomputed by Worker Lab and must match the
  framework result before `RUNNING -> CANDIDATE`.
- P3-C15 — Required validations execute in sealed prerequisite-first order, stop at the first failed
  boundary, and cannot be selected or rewritten by the worker.
- P3-C16 — Every runtime, contract, boundary, timeout, malformed-result, interruption, or validation
  failure retains its first boundary and reaches `ABORTED` only after safe containment and actual
  cleanup; `FAILED` remains an evaluation outcome.
- P3-C17 — `worker-lab-v3` binds adapter, read-only, code-task, evidence-substitution, runtime,
  recovery, CLI, and exact-integration profiles without modifying prior catalogs or adding a second
  profile matrix.
- P3-C18 — Synthetic CLI acceptance, complete affected Worker Lab/framework suites, cross-repository
  integration, durable backup/restore, independent rollback, current documentation, and a named
  milestone all pass once against exact identities.

## Batch approval gates

### 3B gate

Approve only strict records, storage, transition validation, `worker-lab-v3`, the fixed adapter/client
preparation seam, and fake/injected process tests. Reject any code path capable of starting Codex.

### 3C gate

Requires separate trusted approval after 3B review. The review must settle process containment and
termination evidence, output size/redaction, exact framework/runtime checkpoints, and the read-only
non-mutation evaluator before permitting one synthetic proposal.

### 3D gate

Requires accepted 3C evidence. It authorizes one fresh synthetic exact-path code task only. It does
not authorize commit, publication, an evaluator, a real curriculum, or product work.

### 3E gate

Requires accepted 3D evidence. It authorizes milestone verification and recovery actions, not an
authority expansion beyond the Phase 3 specification.

## Decisions reserved for trusted review

1. Confirm the fixed local JSON subprocess adapter instead of a direct Python import boundary.
2. Approve the exact framework adapter filename, configured Python identity, and cross-repository
   commit/digest verification method.
3. Approve a single initial framework-owned Terra-medium runtime profile and timeout.
4. Select and test Windows process containment or exact process-absence proof before Batch 3C.
5. Set maximum prompt/result sizes and a redaction/retention policy for synthetic worker content.
6. Confirm that `runtime_identity` becomes the invocation digest on `READY -> RUNNING` without an
   attempt-schema version change.
7. Approve `worker-lab-v3`, including new T016/T022 bindings and the exact profile commands.
8. Decide whether adapter implementation changes require a new framework milestone before first
   execution.

None of these decisions may be delegated to a worker or inferred from a passing test.

## Principal risks and controls

| Risk | Required control |
|---|---|
| Cross-repository implementation drift | Exact clean commit and contract digest on both sides |
| Worker Lab accidentally owns security behavior | Fixed adapter; framework recomputes runtime-controlled values |
| Framework gains Lab lifecycle authority | Framework returns results only; Worker Lab alone persists transitions |
| Crash between durable state and process creation | Conservative `DISPATCHING` uncertainty; never rerun |
| Orphaned worker mutates a workspace during cleanup | Process containment/absence proof before any workspace operation |
| Worker prose treated as proof | Strict result plus independent filesystem/Git/test evidence |
| Duplicate test-profile authority | Versioned `worker-lab-v3`; no YAML side matrix |
| Refactor obscures security changes | Keep maintenance refactors separate from adapter batches |
| Product data enters proving flow | Synthetic repository requirement and external-product path rejection |

## Recommendation

The trusted review approves Batch 3B under the limits above. Continue to deny worker execution until
a separate 3C approval confirms process containment, result retention, exact runtime identity, and
complete read-only non-mutation coverage.
