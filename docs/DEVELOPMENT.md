# Development

## Working rule

Make one bounded change against a known starting state, run the smallest meaningful validation once, and stop. Preserve unrelated work in a dirty tree.

## Before editing

1. Read `AGENTS.md`, `docs/START_HERE.md`, and `docs/CURRENT_STATE.md`.
2. Inspect `git status --short --branch` and the relevant diff.
3. Name the component and files in scope.
4. Decide the validation command before changing code.
5. Confirm the task does not implicitly enable workers, models, publication, or an external repository.

Do not regenerate recovery evidence, import histories, or structural inventories unless the corresponding source, tree, or integration paths changed.

## Component ownership

| Area | Primary owner |
|---|---|
| `components/worker-lab/worker_lab/` | Authority, records, lifecycle, workspace/evidence control |
| `components/autonomous-worker-framework/tools/` | Execution security, containment, validation, handoff |
| `components/local-model-bench/src/localbench/` | Provider-independent benchmarking and evaluation |
| `config/` | Installation/integration identity, never task authorization |
| `tools/` and `migration/inventory/` | Consolidation inspection and evidence |
| `docs/` | Current operator/developer truth |

A cross-component change must document its protocol direction and validate both sides. Shared convenience is not a reason to blur ownership.

## Validation commands

### Root inventory tools

From the repository root:

```powershell
python -m pytest -q tests
```

These tests validate the inventory tooling; they do not certify component runtimes.

### Worker Lab

From `components\worker-lab` in Python 3.12:

```powershell
python -m pytest -q
```

Use focused test paths first when only one record or boundary changes. The full component suite is the acceptance gate for a Worker Lab checkpoint.

### Autonomous Worker Framework

From `components\autonomous-worker-framework`:

```powershell
python tools\local_validate.py quick
python tools\local_validate.py full
```

Use `quick` during a bounded edit and `full` once for a framework checkpoint. A successful validation does not authorize worker execution.

### Local Model Bench

From `components\local-model-bench` after bootstrap:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m localbench validate --config .\configs\ollama-16gb.json
```

Unit and schema/config validation do not require running a model. Do not launch a model benchmark merely because benchmark code or documentation changed unless fresh provider behavior is part of the task.

## Cross-component identity changes

An installation-identity change affects a security boundary. Review it as one protocol change:

1. Define the installed file set and digest algorithm.
2. Verify manifest path containment and exact entrypoint bytes.
3. Bind Worker Lab's expected runtime identity to the same representation.
4. Reject missing, malformed, outside-root, or mismatched entries.
5. Run focused tests on both sides.
6. Run the full Worker Lab and framework suites once.
7. Keep execution disabled until a separate authority decision.

Development Git identity, installed-file identity, target-repository identity, and candidate identity must stay separate.

## Documentation maintenance

- Update `docs/CURRENT_STATE.md` only after evidence exists.
- Update `docs/ARCHITECTURE.md` when ownership or protocol direction changes.
- Update `docs/OPERATIONS.md` when an operator command or recovery path changes.
- Update `docs/GOVERNANCE.md` for authority or security decisions.
- Move obsolete material to `docs/legacy/`; do not leave two active sources of truth.
- Do not create a new milestone, handoff, decision log, or checklist when an existing current page can hold the necessary fact.

## Completion report

Report the changed files, validation actually run, known unresolved issues, and actions not taken. Do not claim the working tree is accepted, clean, pushed, or executable unless each statement was verified in the current task.
