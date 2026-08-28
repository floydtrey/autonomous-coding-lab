# Worker Lab

Local-first learning, proving, and evaluation platform for bounded software workers.

Worker Lab retains curricula, versioned exercises, attempt history, evidence identity, evaluation results, failures, approved playbooks, and graduation records. The separate Autonomous Worker Framework remains responsible for Codex authentication, sandboxing, repository boundaries, and execution.

## Start here

Read [`docs/START_HERE.md`](docs/START_HERE.md).

## Current phase

The Phase 1 governance and publication milestone is complete at `v0.1.2-phase1`. It preserves the
validated implementation and recovery evidence from `v0.1.1-phase1` while adding the durable Phase 2
readiness boundary and private remote checkpoint. Phase 2 Batch 3 adds restart verification and
quarantine-backed disposal for a receipt-bound, detached synthetic workspace. Worker execution
remains unavailable.

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
