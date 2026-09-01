# Start Here

This is the routing page for current Autonomous Coding Lab work. It is intentionally short so a new person or AI can acquire the right context without rereading the entire consolidation history.

## Authority order

When information conflicts, use this order:

1. The user's current request and explicit approvals.
2. Root `AGENTS.md`.
3. `docs/CURRENT_STATE.md` for current repository status.
4. The relevant current design or operating document.
5. Current code, tests, configuration, and Git evidence.
6. `migration/inventory/` as consolidation evidence.
7. `docs/legacy/` as historical context only.

Stop and resolve a conflict instead of silently choosing the more permissive interpretation.

## Minimum startup

For every task:

1. Read root `AGENTS.md` and this file.
2. Read `docs/CURRENT_STATE.md`.
3. Check the working tree before writing.
4. Read one additional document based on the task below.

## Task routing

| Task | Read next |
|---|---|
| Understand component responsibilities or data flow | `docs/ARCHITECTURE.md` |
| Install, inspect, run a benchmark, back up, or recover | `docs/OPERATIONS.md` |
| Change code, tests, paths, or integration behavior | `docs/DEVELOPMENT.md` |
| Decide authority, permissions, identity, acceptance, or publication | `docs/GOVERNANCE.md` |
| Select or resume the implementation sequence toward workers and the GUI | `docs/WORKPLAN.md` |
| Investigate why a consolidation choice was made | `docs/legacy/README.md`, then only the named historical record |

## Current versus historical material

The files directly under `docs/` are current. Files under `docs/legacy/` record earlier standalone repositories and the merger process. A legacy statement may explain a design decision, but it cannot override current code, current documentation, or current authority.

The JSON files under `migration/inventory/` are deterministic evidence about source and integration trees. They are useful for identity and path investigations; they are not a work queue.

## Freshness rules

- `docs/CURRENT_STATE.md` must identify both the last accepted checkpoint and any unfinished working-tree changes.
- Test counts certify only the commit or working tree on which they ran.
- A prior worker execution proves capability, not permission for another execution.
- A clean source snapshot does not prove the current monorepo working tree is clean.
- Re-run a check only when its inputs changed, its evidence is missing, or the current task requires fresh proof.

## Before acting

State the bounded outcome. Identify which files or component are in scope. Decide what single validation gate is proportionate. Preserve unrelated work. Once the requested outcome and gate are complete, report and stop.
