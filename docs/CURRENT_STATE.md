# Current State

**Last updated:** 2026-09-01

**Repository:** `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`

**Branch:** `main`

**Last accepted Phase 3 implementation checkpoint:** `cf9d45fffdc9309e131739aec03586365d634b35`

**Isolated GUI prototype checkpoint:** `a72f026d57b9d938c4ebba1987379482af4e39b3`

**Phase 2 proof record checkpoint:** `01620a817e13ee4032aeee6c2997a1487496d872`

**Remote relationship at acceptance:** local `main` and `origin/main` matched with zero divergence

**Execution authority:** disabled

## Plain-language status

Phase 1 is complete. The consolidated repository now has a clean, remotely recoverable checkpoint with strict installed-component identity, current active documentation, preserved legacy records, and passing root/component validation. No worker or model was run.

Phase 2 is complete. Exactly one authorized synthetic read-only Codex proposal ran through Worker Lab and the framework, reached `CANDIDATE`, retained exact evidence, left the disposable workspace unchanged, and ended with verified process absence. The installation was restored to disabled immediately afterward.

Phase 3 is in progress. Its shared service now provides strict read-only queries plus attempt creation, workspace preparation/verification/disposal, and guarded attempt transitions for CLI and future GUI clients. Invocation preparation, authorization, rejection, recovery, and review operations have not yet moved behind that boundary, and execution remains disabled.

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

## Accepted Phase 2 proof

The bounded proof used controller `codex-primary-controller` and external run directory `C:\Users\MineTrackerWorker\Documents\ChatGPT\Autonomous Coding Lab\phase2-proof-20260831-01`. The retained run contains exactly one attempt, invocation, result, proposal, and process-custody record.

- attempt: `SYNTHETIC-545B69F603DB4806AAB5107A1D8EDCAB`, state `CANDIDATE`;
- invocation: `INVOCATION-3F76D29A63C74917BE8387CCA81EE995`, state `COMPLETED`;
- authorization: `AUTHORIZATION-B2BA9B0F7F364E648C23F48EFF69CB37`, bound to the controller, run-directory digest, activation evidence, and invocation;
- result/candidate digest: `sha256:ae7c1ef757d61bdb89b84b60ea2326d3871113184b3481d7b0298135131d4e2a`;
- proposal digest: `sha256:2b8e11c4a51e5f316132841be9d4aaa116b224078fc7774339ad54cc2d8ee1cc`, matching the retained proposal bytes;
- activation manifest digest: `sha256:3e67ea4937c46deefa90070632c560242fdda1c98ae69033507887a1b58ffbfd`, with only Worker Lab and the framework active and Local Model Bench advisory;
- workspace: detached at synthetic commit `9c97b63df9569848c7f56c5e8df56bfa6b1abd2a`, unchanged, zero changed paths, and no remotes;
- sealed validation: `T001` passed;
- custody: `ABSENCE_VERIFIED`, zero active processes at `2026-09-01T02:31:24Z`;
- external product repositories accessed: none;
- verified durable backup: 14 files under the retained run directory, manifest SHA-256 `3cb8c9a55806d8b858ff1ab6fd3b2220f42563d20214ba5b062868d64eda6a87`;
- post-proof doctor: manifest digest `sha256:2ffd73d1a6edf49ea906393de7dd89411a9d94c62d1cddb574f246aa3382a826`, `execution_ready: false`, Worker Lab deferred, framework available.

Interruption and recovery behavior remains covered by the accepted deterministic tests; recovery was not applied to the successful retained candidate.

## Accepted Phase 3 read-only service checkpoint

Commit `a288a15` establishes the first shared Worker Lab application-service boundary:

- versioned health, installation-status, record-list, and record-detail DTOs;
- non-mutating list/show coverage for all definition and durable attempt, invocation, result, failure, and evidence collections;
- deterministic identity ordering and record digests suitable for future GUI clients;
- strict rejection of invalid roots, substituted storage, corrupt records, duplicate identities, unsupported collections, unsafe identities, and missing records;
- CLI access through `health`, `installation-status`, `list-records`, and `show-record` without private storage calls;
- refreshed Worker Lab installed-tree identity while execution remains disabled.

Validation did not run a worker or model:

- focused service tests after final hardening: 7 passed;
- Worker Lab full suite before the final test-only hardening: 342 passed and seven expected Windows symlink-capability skips;
- framework bilateral adapter suite: 36 passed;
- framework compile gate and full suite: passed, 208 tests;
- root inventory tools: 9 passed;
- live absent-root health query left the root absent and reported `execution_ready: false`;
- installation status reported manifest digest `sha256:79edaae89f8f5b19d8bd12df1c31d8f7161b2b24999e0d8dee4d669e01cb8976` and Worker Lab digest `sha256:2705bb48173bcfff22d43a5014ae75d62513910684a155dba5ba87b8a7564884`;
- local `main` and `origin/main` matched at the code checkpoint with zero divergence.

## Accepted Phase 3 attempt/workspace service checkpoint

Commit `cf9d45f` moves the existing attempt and workspace lifecycle behind the shared service without adding an execution path:

- versioned `worker-lab-service-operation-result:v1` DTOs expose the affected record, identity, type, and digest to future clients;
- `create-attempt`, `prepare-workspace`, `verify-workspace`, `transition-attempt`, and `discard-workspace` route through the service while preserving established CLI JSON;
- malformed command values and unresolved authority fail before durable state is created;
- receipt-bound workspaces cannot be bypassed with a generic abort transition;
- the packet creates no invocation and grants no dispatch authority.

Validation did not run a worker or model:

- focused service/CLI/operator suite: 27 passed;
- Worker Lab full suite: 347 passed and seven expected Windows symlink-capability skips;
- framework compile gate and full suite: passed, 208 tests;
- final bilateral adapter check with a valid short temp path: 36 passed;
- root inventory tools: 9 passed;
- doctor reported manifest digest `sha256:ed71ac462cedba9f96bafd5ee01ab750809e3ec0753b9ed6a6ed021f62e41eae`, Worker Lab digest `sha256:9f51aeb953cc689cd160a9e03fd31575fec3825b0b2b5f14713a028632f34fa4`, and `execution_ready: false`.

Commit `a72f026` preserves the user's 15-file Tkinter design under `components/worker-lab/prototypes/gui-shell/`. It parses and imports as an isolated prototype, has no production entrypoint, does not connect to the application service, and is excluded from the protected production-tree identity.

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

- A general workspace-write bridge from Worker Lab to the framework.
- Mutating application-service operations for invocations, recovery, review, backup, and restore.
- A functional Worker Lab GUI.
- Unsupervised local-model planning, task authorization, code review, publishing, or merging.
- Production-project access or modification by workers.

## Immediate next gate

Continue Phase 3 by adding invocation preparation, authorization, and rejection to the shared application service with controller-bound command DTOs and legal/prohibited transition tests. Do not add dispatch yet. Execution remains disabled.

The trusted dependency-ordered delivery plan for worker execution and the Worker Lab GUI is `docs/WORKPLAN.md`.

Do not restart source recovery, import, or structural inventory work unless the underlying imported history or component paths change.
