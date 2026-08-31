# Start Here

**Status:** Active migration router
**Current milestone:** M2-B exact framework import complete; parity not authorized
**Execution authority:** Disabled

## First actions

1. Verify this repository's path, branch, HEAD, remote, and working-tree state.
2. Read `CURRENT_STATE.md`.
3. For migration work, read `MERGER_CONTRACT.md`, `SOURCE_INVENTORY.md`,
   `PATH_MIGRATION_LEDGER.md`, and the active milestone in `MILESTONES.md`.
4. Read `handoffs/CONSOLIDATION_RECONCILIATION.md` for the current M1 evidence,
   conflicts, accepted architecture boundaries, and user decisions.
5. For M2 framework work, read `FRAMEWORK_M2_RECOVERY.md` before any import.
6. Read a source repository's own `AGENTS.md` and routing document before
   inspecting or importing that component.
7. Stop if Git evidence and documentation disagree.

## Authority order

1. Current system, developer, and user instructions.
2. Verified Git and filesystem evidence.
3. This repository's accepted decisions and merger contract.
4. Active source-repository authority until its transfer milestone passes.
5. Historical reports, chats, and prior task summaries.

Historical material is evidence, not current authority.

## Current boundary

The repository shell and M1 merger governance are accepted. The commit containing
the accepted reconciliation is the M1 checkpoint. It authorizes no source import
and no execution.

The framework recovery artifact and source identities passed M2-A. M2-B imported
the exact framework tree with complete reachable ancestry and namespaced tags.
The next gate is an untouched parity run from a disposable standalone
reconstruction; it requires separate authorization. In-monorepo testing,
adaptation, and execution remain disabled.
