# Current State

**Last updated:** 2026-08-30
**Status:** M0 complete; M1 source audit in progress
**Canonical repository:** Merger governance only; component authority has not transferred

## Target repository

- Local path: `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`
- Remote: private `floydtrey/autonomous-coding-lab`
- Branch: `main`
- Source code imported: none
- Worker execution authority: none

## Preliminary source identities

| Source | Verified HEAD | Observed state | Remote |
|---|---|---|---|
| Worker Lab | `ca55e30ccbcbf2318d73b3ef8a65f66bb9e1e684` | `main` is 9 commits ahead; one untracked history file; unreadable test-temp directories | private GitHub remote |
| Autonomous Worker Framework | `3b03802ced260ac437d7cfd7857a3a3f4b6bbbcd` / `v0.2.6-worker-lab-final-message` | local `main`; unreadable test-temp directories; no remote | none |
| Local Model Bench | `4a023c8230365c3098a6dff71fa9623cac059cdd` | clean and synchronized; one active ignored benchmark run | public GitHub remote |

These are audit observations, not import approvals. The unreadable directories
and untracked history export will not be opened, removed, or copied during M0.

## Existing boundary that must be preserved

The framework has proven bounded execution capabilities. Worker Lab owns
authority, lifecycle, curriculum, and evidence. Local Model Bench owns model and
prompt evaluation. Bringing them into one repository does not allow one
component to silently assume another component's authority.

## M1 findings

- The first integration layout is fixed for review as `components/worker-lab/`,
  `components/autonomous-worker-framework/`, and
  `components/local-model-bench/`. These paths remain stable through M6.
- Worker Lab and the framework have no detected Python imports between them.
  Their live interface is a versioned canonical-JSON subprocess protocol.
- Worker Lab pins the framework's standalone absolute path, standalone Git
  commit, and root-relative adapter blob path.
- The framework adapter independently assumes its component directory is the
  Git repository root and requires the entire repository to be clean.
- Those identity checks cannot be weakened or patched casually. Live execution
  remains disabled after import until a reviewed monorepo identity contract
  provides component-scoped paths, source provenance, blob identity, and scoped
  cleanliness evidence.
- Worker Lab requires Python 3.12. Local Model Bench requires Python 3.10 or
  newer. The framework has no package metadata and is validated as root-relative
  tools. Each component therefore keeps its own environment and commands during
  migration.
- Worker Lab and the framework have no license file. Their consolidation is
  authorized only inside this private repository; public redistribution remains
  undecided. Local Model Bench's MIT license must remain with that component.
- Benchmark profiles contain two machine-local llama.cpp/model paths. They are
  configuration, not portable defaults, and require later local-configuration
  treatment without importing the model binaries.

## Next boundary

Review the M1 source inventory, exact snapshot choices, history import method,
license treatment, identity-contract migration, and per-component parity
commands. No code import starts before that review is accepted.
