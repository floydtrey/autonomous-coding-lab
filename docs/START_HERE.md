# Start Here

**Status:** Active routing authority
**Current phase:** Phase 3B Worker Lab contracts integrated; framework execution remains disabled
**Integrated checkpoint:** `b280a62` / PR `#5`
**Rollback milestone:** `v0.2.0-phase2`

## Purpose

Use this file to select the minimum authoritative context needed for the current task. Do not read
every project document merely because it exists. Historical reports and conversation exports are not
current authority.

## First boundary

Before acting, confirm the repository path, branch, HEAD, and working-tree status with non-mutating
Git commands. Preserve every existing change and untracked file. Never clean, reset, restore, stash,
or overwrite another participant's work to satisfy a starting check.

## Context reuse contract

Within one active session, an agent may reuse a document it already read when all of these remain
true:

- repository path, branch, and HEAD are unchanged;
- the document itself is unchanged;
- the active task and authority boundary are unchanged; and
- no new instruction conflicts with the remembered contract.

Do not reread an unchanged file in that situation. Record the consulted HEAD and documents in the
task report or handoff.

Reread a document when HEAD changed, its bytes changed, the task crosses a phase or authority
boundary, a failure calls an assumption into question, or the remembered detail is uncertain. Reuse
is an efficiency rule, not permission to guess.

## Minimum routing

Read only the row that matches the current task, plus the directly changed code and tests.

| Task | Required context |
|---|---|
| Current status or handoff | Relevant sections of `CURRENT_STATE.md` and the active task file |
| Phase 2 workspace behavior | Relevant sections of `PHASE2_SPEC.md` and completion conditions in `PHASE2_READINESS_REVIEW.md` |
| Policy, roles, authority, or protected records | `POLICY_MODEL.md`, then the directly affected schemas/code |
| Test selection or milestone validation | Relevant profile/IDs in `TEST_CATALOG.md` and the active immutable catalog |
| Backup, restore, or rollback | Backup section of `PHASE2_SPEC.md`, P2-C11/P2-C12, `worker_lab/backup.py`, `tests/test_backup.py`, and prior milestone evidence only as a format reference |
| Phase 1 audit or historical rollback | `PHASE1_AUDIT_CHECKLIST.md` and `MILESTONE_EVIDENCE.md` |
| Phase 3 or cross-repository interface | Active Worker Lab state plus the relevant Autonomous Worker Framework specifications |

Do not read Phase 1 evidence for ordinary Phase 2 implementation. Do not read Autonomous Worker
Framework specifications during Phase 2 unless the task changes a cross-repository contract. Do not
read old Terra reports unless reviewing that exact attempt.

## Files that are not routine context

Do not open ZIP backups, exported conversations, pasted chat histories, old reports, temporary
artifacts, caches, or unrelated branches unless the task explicitly requires them. Their presence does
not grant authority and their contents may be stale or misleading.

## Testing rule

Select the smallest applicable numbered profile while developing. Run directly affected tests first.
Run the complete active suite only at a named phase milestone or after an explicitly approved
cross-cutting change. Do not repeat a passing broad suite after a narrow correction when focused tests
fully cover the changed boundary; record the ordering honestly.

## Current boundary

Phase 2 is complete at `v0.2.0-phase2`. The accepted Phase 3B Worker Lab checkpoint adds strict
invocation/result contracts, protected invocation custody, immutable `worker-lab-v3` test bindings,
and a fake-only adapter preparation seam.

The next boundary is the separately reviewed framework adapter checkpoint and the reserved Phase 3C
security decisions. No current authority permits Codex/framework execution, `READY -> RUNNING`,
candidate evaluation, publication, real curricula, Mine Tracker changes, or another product
repository.
- Stop on stale or conflicting repository identity.
