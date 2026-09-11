# Operations

This guide covers safe local inspection, portable installation verification, Worker Lab administration, and benchmark operation on Windows. **Worker execution remains disabled.** Provider qualification, installation verification, and successful tests do not authorize a worker or model run.

Run commands from the repository root unless a section says otherwise. The repository path is not authority; the current laptop checkout is `C:\projects\autonomous-coding-lab`, while a fresh tower clone may use a different path.

## Prerequisites

- Windows 10 22H2 or newer
- Git
- CPython 3.12 AMD64 for the current portable ACL host contract
- Ollama only when intentionally running Ollama-backed Local Model Bench work
- `llama-server` and an exact GGUF only when intentionally using the managed llama.cpp benchmark provider

Each component may keep its own environment. A Python environment, installed provider, or benchmark runtime does not by itself qualify the full ACL execution path.

## Inspect repository status

```powershell
git status --short --branch
git log -1 --oneline
```

The current checkpoint and unfinished gate are recorded in `docs/CURRENT_STATE.md`. If Git disagrees with that file, stop and reconcile before relying on either.

## Portable installation verification

For the current provider-neutral vertical-slice path, the active portability contract is `config/portable-installation-manifest.json`.

From the repository root:

```powershell
python .\tools\verify_portable_installation.py
```

This verification checks the protected component bytes and host requirements without requiring Codex or another provider. The intended result while no provider has been qualified is:

```text
provider_runtime_qualified=false
execution_authority=DISABLED
execution_ready=false
```

Those values are not failures. Portable component identity and host/provider qualification are separate, and neither is task authorization.

The current portable manifest records the Autonomous Worker Framework runtime closure, Local Model Bench Python production tree, and Worker Lab Python production tree using the `acl-installed-file-set:v1` canonical digest algorithm. It requires Windows, CPython 3.12, and AMD64, but it does not commit a machine-specific Python path or provider executable path.

## Legacy installation doctor

From `components\worker-lab`:

```powershell
python -m worker_lab.cli doctor
```

`doctor` currently verifies the legacy `config/installation-manifest.json` (`acl-installation-manifest:v2`), including its historical pinned Python and Codex identities. It is retained for the old Codex proof/execution contract and is **not** the current portability check for the new provider-neutral vertical-slice path. Do not install Codex or rewrite its absolute paths merely to make the legacy doctor pass on a new host.

## Worker Lab administrative interface

From `components\worker-lab` with Python 3.12:

```powershell
python -m worker_lab.cli --help
python -m worker_lab.cli --root <lab-data-root> health
python -m worker_lab.cli --root <lab-data-root> installation-status
python -m worker_lab.cli --root <lab-data-root> list-records <collection>
python -m worker_lab.cli --root <lab-data-root> show-record <collection> <identity>
python -m worker_lab.cli --root <lab-data-root> prepare-invocation <attempt-id> --workspace-root <workspace-root> --prompt-file <prompt-file>
python -m worker_lab.cli --root <lab-data-root> authorize-invocation <invocation-id> --expected-identity-digest <sha256-digest> --controller <controller-id>
python -m worker_lab.cli --root <lab-data-root> reject-invocation <invocation-id> --expected-identity-digest <sha256-digest>
python -m worker_lab.cli --root <lab-data-root> cancel-invocation <invocation-id> --expected-identity-digest <sha256-digest> --controller <same-controller-id>
python -m worker_lab.cli --root <lab-data-root> dispatch-invocation <invocation-id> --expected-identity-digest <sha256-digest> --controller <same-controller-id> --workspace-root <workspace-root>
python -m worker_lab.cli --root <lab-data-root> recover-invocation <invocation-id> --expected-identity-digest <sha256-digest> --controller <same-controller-id> --workspace-root <workspace-root>
python -m worker_lab.cli --root <lab-data-root> backup <backup-directory>
python -m worker_lab.cli verify-backup <backup-directory>
python -m worker_lab.cli restore <backup-directory> <empty-destination>
```

Creating attempts, workspaces, or prepared invocations changes durable state and requires an explicit bounded task. The existence of a CLI command never supplies authorization.

`prepare-invocation` seals the prompt, verified workspace receipt, protected definitions, test plan, component identities, writable/readable scope, and immutable invocation identity. Authorization is a separate controller-bound transition. Dispatch is a still-later transition and remains blocked by the committed execution policy.

Recovery now reads `worker-lab-process-custody:v2`. The durable record names a
containment backend and carries opaque backend identities rather than universal
Windows PID fields. Recovery must use the exact named backend and accepts absence
only when durable dispatch evidence, a zero active-workload count, and
backend-produced absence evidence all agree. An active controller, an unknown or
nonzero workload count, a backend mismatch, or missing evidence stops recovery.
The only implemented containment backend remains Windows Job Objects; no Linux
execution backend exists yet.

## Runtime Selection V1

Worker Lab now protects a provider-neutral runtime requirement for new work:

```text
requirement: coding-worker:v1
capability: bounded-code-task
model selector: provider-qualified
reasoning selector: provider-qualified
provider selection: host-qualified-only
```

The requirement is part of task/runtime admission; it is not a provider executable, model name, or authorization token. Historical `terra-medium:v1` invocation records remain parseable for evidence compatibility but are not the selected requirement for newly prepared work.

The Autonomous Worker Framework `WorkerRequest` requires explicit model/reasoning values from a qualified provider boundary. Generic code-task construction no longer silently defaults to Terra.

## Host Provider Qualification V1 — next gate

Host Provider Qualification V1 has not yet been accepted. Its job is to map `coding-worker:v1` to one exact host provider/harness/runtime/model identity while preserving ACL-owned task scope, validation, custody, and authorization boundaries.

The qualification must prove all of the following before any real worker execution:

1. the provider executable/runtime and model identity are exact and reproducible on the host;
2. the provider can consume the ACL bounded `WorkerRequest` contract without gaining scope or approval authority;
3. provider qualification can be verified independently of a task authorization;
4. execution remains disabled after qualification;
5. a later real run still requires one explicit supervised vertical-slice authorization.

Use the existing harness/model research to select the first candidate. Do not start a new broad research campaign merely to complete qualification.

## Worker execution gate

Do not authorize or dispatch the historical prepared Phase 4 invocation. Do not call framework execution adapter modes, run a coding worker, or run a local model as part of routine verification.

Before the first supervised vertical-slice execution, the accepted chain must be:

```text
portable component identity
  -> host/provider qualification
  -> exact bounded task + context
  -> explicit controller/human authorization
  -> one worker dispatch
  -> independent validation
  -> verified/retry/blocked result
```

Passing any earlier gate does not imply permission for the next one. The committed default remains `DISABLED`.

## Local Model Bench setup

Local Model Bench remains advisory and separate from Worker Lab execution authority. From `components\local-model-bench`:

```powershell
.\scripts\bootstrap.ps1
.\scripts\pull-models.ps1
.\.venv\Scripts\python.exe -m localbench validate --config .\configs\ollama-16gb.json
.\.venv\Scripts\python.exe -m localbench doctor --config .\configs\ollama-16gb.json
```

Review a benchmark configuration before downloading or running models. For ACL worker-model evaluation, the intended starting context is 32K; benchmark completion is not semantic acceptance and does not qualify a provider for Worker Lab automatically.

To run an intentionally authorized benchmark:

```powershell
.\scripts\run-unattended.ps1
```

To inspect progress without contacting the model:

```powershell
.\scripts\watch-status.ps1 -Once
```

Resume an interrupted exact run rather than starting over:

```powershell
.\.venv\Scripts\python.exe -m localbench run `
  --config <same-config.json> `
  --resume <existing-result-directory>
```

Benchmark results, provider qualification evidence, Worker Lab execution evidence, and human acceptance are separate evidence classes and must not be substituted for one another.

## Historical proofs

The prior synthetic read-only Codex proof and September 1 Phase 4 prepared packet are retained as historical evidence. Their exact identities and commands are preserved in `docs/legacy/CURRENT_STATE_2026-09-01.md` and Git history. They are not standing authority and are not the current next gate.
