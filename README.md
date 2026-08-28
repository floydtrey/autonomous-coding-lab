# Worker Lab

Local-first learning, proving, and evaluation platform for bounded software workers.

Worker Lab retains curricula, versioned exercises, attempt history, evidence identity, evaluation results, failures, approved playbooks, and graduation records. The separate Autonomous Worker Framework remains responsible for Codex authentication, sandboxing, repository boundaries, and execution.

## Start here

Read [`docs/START_HERE.md`](docs/START_HERE.md).

## Current phase

Phase 2 is complete at `v0.2.0-phase2`. Worker Lab can prepare, restart-verify, and safely dispose of
a receipt-bound detached workspace made from a synthetic local Git template. Durable backup excludes
ephemeral workspaces and receipts, and the milestone was recovered and validated from an independent
Git bundle checkout. Worker execution remains unavailable.

## Operator interface

```powershell
python -m worker_lab.cli --help
python -m worker_lab.cli validate-definition <path>
python -m worker_lab.cli --root <lab-root> list-curricula
python -m worker_lab.cli --root <lab-root> create-attempt --exercise <id> --version <n> --target-repository <path>
python -m worker_lab.cli --root <lab-root> prepare-workspace <attempt-id> --template-repository <path> --workspace-root <path>
python -m worker_lab.cli --root <lab-root> verify-workspace <attempt-id> --workspace-root <path>
python -m worker_lab.cli --root <lab-root> discard-workspace <attempt-id> --workspace-root <path> --cleanup-outcome <text>
python -m worker_lab.cli --root <lab-root> verify-evidence <sha256:digest>
python -m worker_lab.cli --root <lab-root> backup <destination>
python -m worker_lab.cli verify-backup <backup>
python -m worker_lab.cli restore <backup> <empty-destination>
```

Failures return a nonzero status and a stable `ERROR <CODE>:` diagnostic.

Backups include only durable `curricula/` and `state/` content. Repository internals, source code,
caches, temporary files, and disposable workspaces are outside backup scope.

## Tests

```powershell
python -m pytest -q
```

Use [`docs/TEST_CATALOG.md`](docs/TEST_CATALOG.md) to choose the smallest trusted profile.
