# Phase 2 Readiness Review

**Decision date:** 2026-08-27
**Decision:** Approved to begin Phase 2 specification and implementation
**Starting milestone:** `v0.1.2-phase1`
**Completion date:** 2026-08-28
**Completion decision:** All Phase 2 conditions passed for `v0.2.0-phase2`

## Purpose

Phase 2 proves isolated exercise workspace creation, verification, and safe disposal. It does not
invoke Codex, the Autonomous Worker Framework, an evaluator, or any external product repository.
Framework integration remains Phase 3.

## Required outcome

Worker Lab can create a disposable workspace from an explicit, clean, local, versioned synthetic Git
template at an exact commit; verify it after process restart; detect mutation or substitution; and
remove only the exact workspace bound to the attempt. Every failed boundary stops immediately.

## Fixed boundaries

- Keep all templates synthetic and project-agnostic. Mine Tracker and other product repositories are
  excluded.
- Use explicit local Git template paths only. Network templates and inherited credentials are
  excluded.
- Place workspaces outside Worker Lab, the framework, the template source, and product repositories.
- Clone with independent Git objects, check out an exact detached commit, and verify a clean tree.
- Create through a sibling staging directory and publish only after complete verification.
- Bind the attempt, exact template commit, workspace root, and exact workspace path in a strict
  ephemeral receipt. Do not create a second authority system.
- Never accept an arbitrary deletion target. Cleanup may remove only the receipt-bound workspace and
  must detect links, junctions, replacement, and path escape.
- Make interrupted cleanup safe to retry and retain enough state to report the real outcome.
- Keep workspaces and receipts out of durable backup scope. A restored active attempt without its
  workspace cannot resume and must be retried as a new linked attempt.
- Use the existing attempt lifecycle. Preparation may advance `DRAFT` to `READY`; disposal may advance
  `READY` to `ABORTED`. Phase 2 does not enter `RUNNING`.
- Keep single-user, single-process operation. Scheduling, queues, generalized locking, and a broad
  permission service are excluded.

## Implementation batches

1. Specification, strict receipt contract, and permanent test bindings.
2. Staged workspace preparation and `DRAFT` to `READY` transition.
3. Restart verification, safe disposal, retry behavior, and `READY` to `ABORTED` transition.
4. CLI acceptance, full milestone validation, backup/rollback drill, and handoff documentation.

## Completion conditions

- P2-C01 — The specification records authority, lifecycle, path, failure, backup, and exclusion rules.
- P2-C02 — Receipt parsing is strict and deterministic and the receipt remains ephemeral.
- P2-C03 — Template validation rejects URLs, links, junctions, overlaps, dirty trees, context mismatch,
  and commits other than the explicitly recorded starting commit.
- P2-C04 — Staged cloning uses independent Git objects and publishes an exact clean detached commit
  without changing the source.
- P2-C05 — Receipt and attempt identity bind the exact canonical workspace root and attempt directory;
  missing, moved, or substituted paths fail closed.
- P2-C06 — Preparation failure leaves the attempt in `DRAFT` and publishes no workspace or receipt.
- P2-C07 — The attempt enters `READY` only after the workspace and receipt pass verification; runtime
  and candidate identity remain unset.
- P2-C08 — Verification works after restart and rejects dirty contents, changed commits, path changes,
  and context changes.
- P2-C09 — Cleanup operates only on the receipt-bound workspace and is interruption-safe and
  idempotent.
- P2-C10 — Cleanup records its actual outcome before a valid `READY` to `ABORTED` transition; retries
  create a new linked attempt.
- P2-C11 — Backup and restore exclude ephemeral workspaces and receipts and cannot silently resume an
  unrestored active attempt.
- P2-C12 — Synthetic CLI acceptance, numbered profiles, the full suite, an external rollback drill,
  current-state updates, and a named milestone all pass.

## Deferred to later phases

Codex execution, framework adapters, candidate digests, evaluator execution, approval packets,
failure classification automation, repair loops, dashboards, curricula applications, graduation,
GitHub publishing by workers, concurrent attempts, and product-repository work are not Phase 2.
