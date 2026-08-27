# Worker Lab

Local-first learning, proving, and evaluation platform for bounded software workers.

Worker Lab retains curricula, versioned exercises, attempt history, evidence identity, evaluation results, failures, approved playbooks, and graduation records. The separate Autonomous Worker Framework remains responsible for Codex authentication, sandboxing, repository boundaries, and execution.

## Start here

Read [`docs/START_HERE.md`](docs/START_HERE.md).

## Current phase

The corrected Phase 1 headless milestone is complete at `v0.1.1-phase1`. Its protected contracts,
numbered test selection, local storage, evidence verification, backup/restore, and operator CLI do
not invoke coding workers. Phase 2 remains closed pending separate authorization.

## Operator interface

```powershell
python -m worker_lab.cli --help
python -m worker_lab.cli validate-definition <path>
python -m worker_lab.cli --root <lab-root> list-curricula
python -m worker_lab.cli --root <lab-root> create-attempt --exercise <id> --version <n> --target-repository <path>
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
