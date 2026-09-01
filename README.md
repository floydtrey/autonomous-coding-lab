# Autonomous Coding Lab

Autonomous Coding Lab (ACL) is a local-first system for defining bounded coding work, running it through a controlled execution boundary, and evaluating local models before trusting them with a role.

The repository contains one system with three deliberately separate responsibilities:

| Component | Responsibility | Authority |
|---|---|---|
| `worker-lab` | Tasks, policies, roles, attempts, lifecycle, evidence, and graduation | Decides what work may occur and what evidence is acceptable |
| `autonomous-worker-framework` | Authentication isolation, sandboxing, subprocess execution, repository boundaries, and validation transport | Executes only an already-authorized contract |
| `local-model-bench` | Repeatable prompt/model comparisons and validation packets | Advisory evidence only; it cannot authorize or execute work |

Local Model Bench is peer/advisory infrastructure, not a runtime dependency of Worker Lab or the framework.

## Current status

The three source histories and component trees have been consolidated. The accepted Phase 1 runtime checkpoint is commit `5f6c41da132daa12f0bb8c4be054112d77ef7e54`; its current-state acceptance record is committed at `8c4f697`.

Worker execution is currently **disabled**. Phase 2's guarded synthetic read-only proof completed successfully with one retained `CANDIDATE`, an unchanged disposable workspace, and verified process absence. Phase 3 is in progress: checkpoint `a288a15` adds the shared read-only application-service and CLI query boundary; mutating lifecycle operations are next.

Read [Start Here](docs/START_HERE.md) before changing the repository. The exact accepted and in-progress state is in [Current State](docs/CURRENT_STATE.md).

## Repository layout

```text
autonomous-coding-lab/
|-- components/
|   |-- autonomous-worker-framework/
|   |-- worker-lab/
|   `-- local-model-bench/
|-- config/                 installation and integration identity
|-- docs/                   current system documentation
|   `-- legacy/             historical evidence, not current instructions
|-- migration/inventory/    deterministic consolidation evidence
|-- tests/                  root inventory-tool tests
`-- tools/                  structural inventory and query utilities
```

## Documentation

- [Start Here](docs/START_HERE.md) — minimum reading route and task startup rules
- [Current State](docs/CURRENT_STATE.md) — accepted checkpoint, unfinished work, and next gate
- [Architecture](docs/ARCHITECTURE.md) — component and trust boundaries
- [Operations](docs/OPERATIONS.md) — Windows setup and safe operator commands
- [Development](docs/DEVELOPMENT.md) — change and validation workflow
- [Governance](docs/GOVERNANCE.md) — authority, identity, and acceptance rules
- [Project Audit and Work Plan](docs/WORKPLAN.md) — trusted delivery sequence for workers and the GUI
- [Legacy index](docs/legacy/README.md) — where the pre-consolidation records went

## Safety summary

- Configuration can make a capability available; it does not authorize a task.
- Planner and model output is untrusted input until Worker Lab accepts it.
- Workers do not commit, push, merge, change Git configuration, or gain publication authority.
- The first failed identity, scope, or evidence boundary stops the operation.
- Source repositories and external product repositories remain outside ACL unless a task explicitly places one in scope.
