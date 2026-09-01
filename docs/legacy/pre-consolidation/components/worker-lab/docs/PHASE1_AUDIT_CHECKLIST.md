# Phase 1 Audit Completion Checklist

**Status:** Corrected milestone complete
**Release target:** `v0.1.1-phase1`
**Historical checkpoint:** `v0.1.0-phase1` remains unchanged and is not the corrected release.

All correction conditions are complete. Phase 2 remains closed until separately authorized.

## Batch 1 — Authority and identity

- [x] C01 — Permanent test IDs retain the framework meanings and have a strict project binding.
- [x] C02 — Non-overridable policy, permanent capabilities, versioned roles, deny-wins precedence,
  and `ROLE_UNSUPPORTED` behavior are explicit and digestible.
- [x] C03 — Read-only context manifests bind repository, commit, normalized file paths, purposes,
  and file digests; attempt creation verifies the separate clean Git target and exact content.
- [x] C04 — Attempt identity binds exercise, policy, role, sandbox, context, and evaluator identities;
  unresolved authority fails before state is written.

Batch 1 remains checked only if its focused and complete regression profiles pass at checkpoint.

## Batch 2 — Core correctness and lifecycle integrity

- [x] C05 — Invalid stored records always produce structured failures without mutation.
- [x] C06 — Read-only storage and CLI operations do not create or modify filesystem state.
- [x] C07 — Terminal attempt history and authority-bearing inputs cannot be overwritten; retries use
  new linked attempts without self-links or cycles.
- [x] C08 — Cross-record relationships bind exact curriculum, exercise, attempt, evidence, failure,
  and evaluator identities.
- [x] C09 — Path and writable/protected scope rules consistently reject non-normalized and nested
  conflicts.
- [x] C10 — Ordered curriculum exercise sequences preserve intentional order while true sets remain
  sorted and unique.

## Batch 3 — Test planning, evidence, and backup

- [x] C11 — Test plans use dependency-respecting, cost-aware order and retain exact catalog identity.
- [x] C12 — Evidence verification hashes content and binds attempt, candidate, base, environment,
  catalog, and test identity before reporting `VERIFIED`.
- [x] C13 — Backup scope includes only explicit durable content and excludes repository internals,
  caches, temporary files, and disposable workspaces.
- [x] C14 — Restore is staged, identity-verified, empty-destination-only, and interruption-safe.

## Batch 4 — Acceptance and corrected milestone

- [x] C15 — Every protected record has representative valid, missing, unknown, malformed,
  incompatible, deterministic, and input-immutability coverage.
- [x] C16 — Definition, attempt, transition, evidence, backup, and restore CLI flows pass end to end.
- [x] C17 — Focused/full suites and a real backup/restore/rollback drill pass; a verified Git bundle
  exists outside the repository.
- [x] C18 — Current-state documentation is accurate, framework handoff is updated, and the immutable
  corrected `v0.1.1-phase1` tag is created.

## Explicit exclusions

No worker execution, Phase 2 workspaces, framework invocation, dashboard, SQLite, OCR, generalized
permission system, external product repository change, or graduation automation belongs in this
correction.
