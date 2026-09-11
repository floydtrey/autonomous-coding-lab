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
| `components/worker-lab/worker_lab/` | Authority, records, lifecycle, workspace/evidence control, protected runtime requirements |
| `components/autonomous-worker-framework/tools/` | Execution security, containment, validation, provider-neutral worker request/handoff |
| `components/local-model-bench/src/localbench/` | Provider-independent benchmarking and evaluation |
| `config/` | Portable installation identity and legacy installation contracts, never task authorization |
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

### Portable installation identity

From the repository root on a candidate Windows host:

```powershell
python .\tools\verify_portable_installation.py
```

This verifies committed component bytes plus the portable Windows/CPython/architecture requirements. It deliberately does not require a provider and must not report execution ready merely because the component and host checks pass.

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

## Portable identity and provider qualification

Keep four identities distinct:

1. **Git/source identity** — the committed code and tree being reviewed.
2. **Portable component identity** — deterministic protected component bytes recorded in `config/portable-installation-manifest.json`.
3. **Host/provider identity** — the exact provider/harness/runtime/model qualified on one host to satisfy a protected Worker Lab runtime requirement such as `coding-worker:v1`.
4. **Task authorization identity** — the exact invocation/controller decision that permits one bounded execution.

A portable manifest change is a security-boundary change. Review it as follows:

1. Define the protected file set and canonical digest algorithm.
2. Verify containment, deterministic checkout bytes, and exact entrypoint/runtime-closure membership.
3. Verify the intended host requirements separately from any provider executable path.
4. Keep provider qualification out of the committed portable component identity unless the contract is deliberately versioned to say otherwise.
5. Run focused tests on every affected component.
6. Recalculate and record affected portable component digests from canonical worktree bytes.
7. Run `verify_portable_installation.py` on the intended host after the refreshed manifest is committed.
8. Keep execution authority disabled until a separate authorization decision.

Do not edit the legacy `config/installation-manifest.json` merely to make its old Codex paths match a different machine. It remains the disabled historical Codex execution/proof contract until a deliberate migration replaces it.

## Runtime Selection V1

Worker Lab owns the protected capability requirement. The current selected requirement for new bounded coding work is `coding-worker:v1`, capability `bounded-code-task`.

The task/invocation layer may state provider-qualified selectors and timeout constraints, but it must not choose a machine-specific executable path or smuggle provider credentials into task identity. Provider selection belongs behind the host-qualification boundary.

The framework owns the provider-neutral `WorkerRequest` and execution containment. Generic framework code must not regain implicit Terra/Codex defaults. Historical Terra records remain parseable only for compatibility/evidence.

When adding the first local provider adapter, test at least these failure cases before any real model run: wrong provider identity, wrong model identity, missing runtime, substituted executable/path, changed task scope, changed writable paths, provider attempting unauthorized capabilities, and provider-qualified-but-execution-disabled.

## Documentation maintenance

- Update `docs/CURRENT_STATE.md` only after evidence exists.
- Update `docs/ARCHITECTURE.md` when ownership or protocol direction changes.
- Update `docs/OPERATIONS.md` when an operator command, host qualification, or recovery path changes.
- Update `docs/GOVERNANCE.md` for authority or security decisions.
- Move obsolete material to `docs/legacy/`; do not leave two active sources of truth.
- Do not create a new milestone, handoff, decision log, or checklist when an existing current page can hold the necessary fact.

## Completion report

Report the changed files, validation actually run, known unresolved issues, and actions not taken. Do not claim the working tree is accepted, clean, pushed, provider-qualified, or executable unless each statement was verified in the current task.
