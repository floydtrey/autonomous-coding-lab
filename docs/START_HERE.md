# Start Here

This is the routing page for current Autonomous Coding Lab work. It is intentionally short so a new person or AI can acquire the right context without rereading the entire consolidation history.

## Authority order

When information conflicts, use this order:

1. The user's current request and explicit approvals.
2. Root `AGENTS.md`.
3. `docs/CURRENT_STATE.md` for project phase/status, except that portable host-installation identity is governed by `docs/PORTABLE_INSTALLATION_IDENTITY.md` until its planned V2 reconstruction, and the active runtime reconstruction is governed by `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` plus current code/tests/Git evidence.
4. The relevant current design or operating document.
5. Current code, tests, configuration, and Git evidence.
6. `migration/inventory/` only when a current task explicitly requires consolidation evidence.
7. Historical material only when the user explicitly asks for historical investigation.

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
| Continue the approved runtime cleanup/reconstruction | `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` |
| Understand component responsibilities or data flow | `docs/ARCHITECTURE.md` |
| Inspect the Knowledge Core-to-worker informational handoff | `docs/CONTROLLER_TASK_PACKET_V1.md` |
| Verify the current Windows portable-component baseline | `docs/PORTABLE_INSTALLATION_IDENTITY.md` |
| Change code, tests, paths, or integration behavior | `docs/DEVELOPMENT.md` |
| Decide authority, permissions, identity, acceptance, or publication | `docs/GOVERNANCE.md` |
| Select or resume the broader implementation sequence toward workers and the GUI | `docs/WORKPLAN.md` |
| Investigate historical consolidation only when explicitly requested | use Git history first; inspect retained historical material only if still necessary |

## Current-tree rule

The current Git tree should describe the current architecture. Git history is the primary historical record.

Do not preserve obsolete runtime architecture, provider fallbacks, machine-specific paths, or old proof implementations in active/current documentation merely so they remain easy to find. The approved runtime reconstruction will remove stale Codex/Terra/MineTrackerWorker/commissioning material from the active tree once current replacements are accepted.

`migration/inventory/` and any remaining historical files are not current architectural authority and are scheduled for review during the reconstruction cleanup. Do not use them to infer current runtime behavior unless the current task explicitly requires them.

## Freshness rules

- `docs/CURRENT_STATE.md` must identify both the last accepted checkpoint and any unfinished working-tree changes.
- Test counts certify only the commit or working tree on which they ran.
- A prior worker execution proves capability, not permission for another execution.
- A clean source snapshot does not prove the current monorepo working tree is clean.
- Re-run a check only when its inputs changed, its evidence is missing, or the current task requires fresh proof.

## Before acting

State the bounded outcome. Identify which files or component are in scope. Decide what single validation gate is proportionate. Preserve unrelated work. Once the requested outcome and gate are complete, report and stop.
