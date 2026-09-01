# Current State

**Last updated:** 2026-08-31

**Repository:** `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`

**Branch:** `main`

**Last accepted checkpoint:** `06a7d21f5cf06ef26b489a6e786521feaeb6fd21`

**Remote relationship at acceptance:** local `main` and `origin/main` matched with zero divergence

**Execution authority:** disabled

## Plain-language status

Phase 1 is complete. The consolidated repository now has a clean, remotely recoverable checkpoint with strict installed-component identity, current active documentation, preserved legacy records, and passing root/component validation. No worker or model was run.

Phase 2 readiness is complete. The accepted operator surface now has a non-executing doctor, a guarded synthetic read-only command, explicit controller/run-directory/one-time authorization inputs, durable activation/authorization evidence, and fail-closed interruption recovery. The one-run proof still requires separate explicit worker/model authorization.

## Accepted Phase 1 checkpoint

The accepted checkpoint consists of these bounded commits:

- `4678c87` — strict installation identity v2 and bilateral protocol update;
- `591ae42` — Local Model Bench CRLF Markdown-heading compatibility repair;
- `5f6c41d` — active-documentation consolidation and byte-preserved legacy archive.

At acceptance, the working tree was clean; local `main` and `origin/main` both resolved to `5f6c41da132daa12f0bb8c4be054112d77ef7e54`; remote divergence was `0 0`; and execution remained disabled.

## Phase 1 validation evidence

No worker or model was run. With temporary output placed outside every Git repository:

- root inventory tools: 9 passed;
- framework compile gate: passed;
- framework full suite: 208 passed;
- Worker Lab full suite: 330 passed and seven expected Windows symlink-capability skips;
- Local Model Bench: 13 passed, including the CRLF regression, and the baseline configuration validated;
- framework documentation contract: 5 passed after the active-document update;
- 43 archived documentation files matched their accepted source blobs and were committed as 100% renames;
- both manifest consumers agreed on framework digest `sha256:81cc5608ec465133a8eb0bfe8a14ab744913ec4c35010b8cdf64f8cc9d61a6a3`, Worker Lab digest `sha256:a7d4d4eef3657bdd73f302a9fd11d150aa740bb052f16d083b04868725b9b6b2`, and disabled execution;
- `git diff --check` passed.

This evidence is accepted at checkpoint `5f6c41d`.

## Accepted Phase 2 readiness checkpoint

Commit `06a7d21` adds the operator boundary without enabling execution:

- `worker-lab doctor` verifies the complete manifest, installed component closures, and pinned Python/Codex identities without launching a subprocess;
- the synthetic command requires a new absolute directory outside every Git repository, a validated controller identity, and the exact one-time confirmation phrase;
- disabled policy is checked before the run directory or any subprocess can be created;
- admitted runs persist activation and authorization evidence bound to the controller, run-directory digest, invocation, installed components, and runtimes before adapter preflight;
- recovery grants no new execution authority and accepts only exact durable evidence, an unchanged workspace, and—after dispatch—verified process absence.

Validation for this checkpoint did not run a worker or model:

- Worker Lab full suite: 337 passed and seven expected Windows symlink-capability skips;
- focused operator/CLI/synthetic suite after final hardening: 21 passed;
- framework bilateral adapter suite: 36 passed;
- root inventory plus active-document checks: 14 passed;
- non-executing doctor reported manifest digest `sha256:2ffd73d1a6edf49ea906393de7dd89411a9d94c62d1cddb574f246aa3382a826`;
- doctor reported Worker Lab digest `sha256:a98085ec33a89616e388a490382c25043088c79196c5a3a671d46e07ca5670cf` and `execution_ready: false`;
- local `main` and `origin/main` matched after the readiness commit was pushed.

## Proven component capabilities

### Worker Lab

Worker Lab has strict, versioned records for curricula, policies, roles, exercises, attempts, evidence, failures, and test catalogs. It can validate authority, create attempts, prepare and verify isolated workspaces, manage lifecycle transitions, safely discard workspaces, verify evidence, and create/verify/restore durable backups.

It is the control plane. It decides whether a task is valid and whether evidence is sufficient.

### Autonomous Worker Framework

The framework has tested code for ChatGPT-managed Codex execution, API-key rejection, credential stripping, explicit sandbox modes, target-repository containment, timeouts, bounded output, trusted validation, candidate publication, and repository handoff.

It is the execution/security engine. Capability in the code does not grant current permission to invoke it.

### Local Model Bench

Local Model Bench can run deterministic JSON or Markdown suites model-by-model through Ollama, managed llama.cpp/GGUF, or OpenAI-compatible local endpoints. It captures complete responses and timing/token metadata where supplied, checkpoints each case, resumes interrupted runs, evaluates result contracts, and supports unattended Windows runs.

It is advisory infrastructure. It neither imports Worker Lab nor participates in the worker execution path.

## Benchmark evidence

The committed 24-request smoke run proved the harness and result-capture path. Its manual review found Qwen2.5-Coder 7B provisionally useful for further planner testing, DeepSeek-Coder 6.7B useful for additional narrow-repair tests, and StarCoder2 7B unsuitable for the tested roles.

A later 90-call planning/task-creation run and an 18-case Qwen 14B native-JSON retest were completed in the source benchmark workspace. The consolidation record reports 18/18 completion, 93.33% deterministic mechanical score, and zero hard failures for the Qwen 14B retest. Semantic role fitness remains unaccepted until human review is recorded.

## Not yet available

- An accepted real Worker Lab-to-framework execution proof in this monorepo.
- A general workspace-write bridge from Worker Lab to the framework.
- A shared application-service interface for CLI and GUI clients.
- A functional Worker Lab GUI.
- Unsupervised local-model planning, task authorization, code review, publishing, or merging.
- Production-project access or modification by workers.

## Immediate next gate

Obtain explicit authorization for exactly one synthetic read-only proof. That authorization must name the controller identity, new external run directory, one-time confirmation, temporary activation of Worker Lab/framework only, and the requirement to restore disabled policy immediately afterward. Then verify exact retained evidence, an unchanged disposable workspace, process absence, lifecycle state, and restored disabled installation state.

The trusted dependency-ordered delivery plan for worker execution and the Worker Lab GUI is `docs/WORKPLAN.md`.

Do not restart source recovery, import, or structural inventory work unless the underlying imported history or component paths change.
