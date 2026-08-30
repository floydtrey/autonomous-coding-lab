# Current State

**Last updated:** 2026-08-30
**Status:** M0 bootstrap in progress
**Canonical repository:** Not yet transferred

## Target repository

- Local path: `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`
- Intended remote: private `floydtrey/autonomous-coding-lab`
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

## Next boundary

Complete M1 source inventory and update the merger contract. No code import may
start until the directory map, provenance method, exclusions, security-boundary
mapping, and per-component parity commands are reviewed.
