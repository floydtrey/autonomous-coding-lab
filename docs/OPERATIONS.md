# Operations

This guide covers safe local inspection and benchmark operation on Windows. Worker execution remains disabled. The synthetic proof command is documented so its authority boundary can be reviewed, but it fails before creating a run directory while the installation policy is disabled.

Run commands from `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab` unless a section says otherwise.

## Prerequisites

- Windows 10 22H2 or newer
- Git
- Python 3.12 for Worker Lab and the unified development environment
- Python 3.10 or newer for Local Model Bench
- Ollama only when running Ollama-backed benchmarks
- `llama-server` and an exact GGUF only when using the managed llama.cpp provider

Each component currently keeps its own environment. Do not assume one virtual environment proves all three components.

## Inspect repository status

```powershell
git status --short --branch
git log -1 --oneline
```

The accepted checkpoint and known unfinished changes are recorded in `docs/CURRENT_STATE.md`. If Git disagrees with that file, stop and reconcile the documentation before relying on either.

## Worker Lab administrative interface

From `components\worker-lab` with a Python 3.12 environment:

```powershell
python -m worker_lab.cli --help
python -m worker_lab.cli doctor
python -m worker_lab.cli --root <lab-data-root> list-curricula
python -m worker_lab.cli validate-definition <definition.json>
python -m worker_lab.cli verify-backup <backup-directory>
```

`doctor` verifies the strict installation manifest, complete component file sets, and pinned Python/Codex identities. It does not launch the framework adapter, Codex, or a local model. An `execution_ready` value of `false` is the expected result while policy is disabled.

Creating attempts or workspaces changes durable state and requires an explicit task. The existence of a CLI command does not authorize framework execution.

Backups include durable `curricula/` and `state/` data only. Source code, repository internals, caches, and disposable workspaces are not backup content.

## Synthetic read-only proof boundary

The supported Phase 2 command requires all three operator inputs: a new absolute run directory outside every Git repository, a stable controller identity, and the exact one-time confirmation phrase.

```powershell
python -m worker_lab.cli synthetic-read-only `
  --run-directory C:\worker-lab-runs\phase2-proof `
  --controller <controller-identity> `
  --authorize-once AUTHORIZE-SYNTHETIC-READ-ONLY-ONCE
```

This command is not standing authority. With the committed disabled policy it returns `INTEGRATION_EXECUTION_DISABLED` before creating the run directory or launching any subprocess. The accepted Phase 2 proof temporarily activated only Worker Lab and the framework, ran once, and restored disabled policy; future runs must preserve the same bounded authority and evidence controls.

When an authorized run is admitted, Worker Lab writes strict activation and one-time authorization evidence before adapter preflight. The authorization is bound to the controller, canonical run-directory digest, invocation identity, installed component digests, and pinned runtime identities. Reusing the same directory is rejected.

For a recorded interrupted run, recovery is explicit and does not activate execution:

```powershell
python -m worker_lab.cli recover-synthetic-read-only `
  --run-directory C:\worker-lab-runs\phase2-proof `
  --controller <same-controller-identity>
```

Pre-dispatch recovery verifies the unchanged workspace, terminates the durable invocation, removes the disposable workspace, and records the aborted attempt. Post-dispatch recovery proceeds only from exact process-custody absence evidence and an unchanged workspace; uncertainty remains fail-closed.

## Local Model Bench setup

From `components\local-model-bench`:

```powershell
.\scripts\bootstrap.ps1
.\scripts\pull-models.ps1
.\.venv\Scripts\python.exe -m localbench validate --config .\configs\ollama-16gb.json
.\.venv\Scripts\python.exe -m localbench doctor --config .\configs\ollama-16gb.json
```

`pull-models.ps1` downloads models named by the baseline setup. Review the configuration before downloading if disk space or model selection has changed.

## Run and watch a benchmark

Start the default unattended benchmark:

```powershell
.\scripts\run-unattended.ps1
```

The launcher prints the exact result directory and watcher command. To follow the newest run:

```powershell
.\scripts\watch-status.ps1
```

For a single status reading:

```powershell
.\scripts\watch-status.ps1 -Once
```

The watcher reads `checkpoint.json`; it does not contact or slow the model. The run is complete only when `manifest.json` records a terminal status. Provider completion alone is not a quality pass.

## Interrupted or failed benchmarks

Each completed case is written immediately. Resume the exact run rather than starting over:

```powershell
.\.venv\Scripts\python.exe -m localbench run `
  --config <same-config.json> `
  --resume <existing-result-directory>
```

Add `--rerun-errors` only when intentionally retrying terminal error cases. A failed case is not appended to preserved conversation history, so later preserved-context cases rebuild from the last successful turn.

Inspect these artifacts in order:

1. `manifest.json` for terminal state.
2. `checkpoint.json` for the last completed/current case.
3. Per-case JSON for the response or structured error.
4. Launcher stderr log for a process-level failure.
5. `evaluation.json` or `evaluation.md` for scoring when evaluation is enabled.

## Commit benchmark evidence

Before committing results:

- confirm configs contain environment-variable names, never credential values;
- keep raw case JSON, manifest, checkpoint, effective redacted config, and evaluation reports together;
- exclude transient PID and launcher log files unless they explain a failure;
- name the run and review so a later reader can identify model order, suite, and purpose;
- record human semantic review separately from deterministic completion/format scoring.

## Worker execution gate

Do not call `worker_lab_adapter.py execute-read-only`, the guarded synthetic command, or any workspace-write path as routine operation. Each run must name the accepted installation identity, controller, one-time authorization, disposable run directory or target, sandbox, test catalog, stop conditions, and applicable authority. The committed default remains disabled even after a successful proof.
