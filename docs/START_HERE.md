# Start Here

**Status:** Active migration router
**Current milestone:** M3 exact import complete; standalone parity failed and repair is pending
**Execution authority:** Disabled

## First actions

1. Verify this repository's path, branch, HEAD, remote, and working-tree state.
2. Read `CURRENT_STATE.md`.
3. For migration work, read `MERGER_CONTRACT.md`, `SOURCE_INVENTORY.md`,
   `PATH_MIGRATION_LEDGER.md`, and the active milestone in `MILESTONES.md`.
4. Read `handoffs/CONSOLIDATION_RECONCILIATION.md` for the current M1 evidence,
   conflicts, accepted architecture boundaries, and user decisions.
5. For M2 framework work, read `FRAMEWORK_M2_RECOVERY.md` before any import.
6. For M3 Worker Lab work, read `WORKER_LAB_M3_RECOVERY.md` before any import.
7. Read a source repository's own `AGENTS.md` and routing document before
   inspecting or importing that component.
8. Query `../migration/inventory/` for exact source-file, path, structure, and
   connection evidence instead of repeating broad repository discovery.
9. Stop if Git evidence and documentation disagree.

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
The untouched full suite passed from an exact disposable standalone
reconstruction, and the prefixed in-monorepo full suite also passed. Focused
testing proved the quick validator falsely selects no stages for monorepo-prefixed
paths. The deterministic structural inventory classifies P-008 as the sole
mechanical failure and records the remaining issues as known semantic/runtime
gaps. P-008 is repaired and validated in the monorepo. The framework-only
identity policy and unwired verifier now bind source provenance, monorepo
integration evidence, exact paths/blobs, and the M2 dependency closure. Worker
Lab identity, bilateral cleanliness, protocol wiring, and all execution remain
deferred. Worker Lab recovery and complete-history reconstruction passed in
M3-A. M3-B then imported the exact source tree, complete ancestry, and
namespaced tags without running or adapting the component. An exact disposable
standalone reconstruction then ran T020: 317 tests passed, seven expected
Windows symlink-capability tests skipped, and 12 tests failed because older
fixtures omit the now-required runtime identity for active attempts. The import
remains exact, but parity is not complete. The next possible gate is a
separately authorized bounded source-parity repair; identity/protocol adaptation
remains blocked.
