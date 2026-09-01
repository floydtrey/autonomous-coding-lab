# Current State

**Last updated:** 2026-08-31

**Repository:** `C:\Users\MineTrackerWorker\repos\autonomous-coding-lab`

**Branch:** `main`

**Last accepted checkpoint:** `d3e67b970e90eeb52dd854b5eda1f812232b05fe`

**Remote relationship at inspection:** local `main` was 107 commits ahead of `origin/main`

**Execution authority:** disabled

## Plain-language status

The consolidation succeeded: the complete histories and selected trees for the framework, Worker Lab, and Local Model Bench are in one repository. Their responsibilities remain separate internal trust boundaries.

The repository is not yet at an accepted post-consolidation runtime checkpoint. The working tree now contains a completed documentation/archive replacement and a validated installation-identity v2 candidate, but neither has been committed or pushed. Nothing in those changes authorizes worker execution.

## Accepted checkpoint evidence

At or before the accepted checkpoint:

- The framework source was imported with recoverable history and tags.
- Its monorepo prefix repair was validated; the full framework gate recorded 197 passing tests at the identity milestone.
- Worker Lab source was imported with recoverable history and tags.
- Four stale test fixtures were repaired without weakening the production runtime-identity requirement. The accepted Worker Lab parity run recorded 329 passes and seven expected Windows capability skips.
- The deterministic integration inventory parsed 40 framework files and 68 Worker Lab files with no parser failures at checkpoint `d28cbbb`.
- Local Model Bench was imported as an exact component history at `d3e67b9` from source commit `4a023c8230365c3098a6dff71fa9623cac059cdd`.

These figures are checkpoint evidence, not results from the current dirty working tree.

## Current uncommitted work

The working tree observed during this documentation rebuild contains:

- archived former root and component documentation under `docs/legacy/`;
- this replacement active documentation set;
- an untracked strict `config/installation-manifest.json` v2;
- modifications to the framework adapter and Worker Lab integration files that replace standalone Git-root assumptions and content-as-commit compatibility fields with SHA-256 installed-component identities;
- independent manifest parsers in Worker Lab and the framework adapter;
- a Local Model Bench CRLF Markdown-heading repair and regression test;
- deletion of the former component-local READMEs and design documents after their relocation to legacy storage.

The v2 manifest separates source commit/tree provenance from installed content. It records the complete two-file framework adapter dependency closure, the complete Worker Lab and Local Model Bench Python production trees, and exact Python/Codex paths, versions, and SHA-256 digests. Its activation policy keeps execution `DISABLED`, keeps Worker Lab `DEFERRED`, and is enforced independently by both sides before preflight or execution. Protocol v2 uses `worker_lab_installation_digest` and `framework_installation_digest`; it no longer places content hashes in `*_commit` fields.

## Current working-tree validation

No worker or model was run. With temporary output placed outside every Git repository:

- root inventory tools: 9 passed;
- framework compile gate: passed;
- framework full suite: 208 passed;
- Worker Lab full suite: 330 passed and seven expected Windows symlink-capability skips;
- Local Model Bench: 13 passed, including the CRLF regression, and the baseline configuration validated;
- 43 archived documentation files matched their accepted HEAD blobs;
- both manifest consumers agreed on framework digest `sha256:81cc5608ec465133a8eb0bfe8a14ab744913ec4c35010b8cdf64f8cc9d61a6a3`, Worker Lab digest `sha256:a7d4d4eef3657bdd73f302a9fd11d150aa740bb052f16d083b04868725b9b6b2`, and disabled execution;
- `git diff --check` passed.

This is working-tree evidence only. The Phase 1 clean-tree and remote-recovery gates remain unsatisfied because staging, committing, and pushing were not authorized.

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

- A reviewed, accepted installed-component identity contract across both Worker Lab and the framework.
- Authorized Worker Lab-to-framework worker execution in this monorepo.
- Unsupervised local-model planning, task authorization, code review, publishing, or merging.
- Production-project access or modification by workers.
- A single packaged installer or unified operator interface.

## Immediate next gate

Review the documentation/archive replacement and installation-identity v2 candidate as separate bounded changes. If accepted and explicitly authorized, commit them without enabling execution, push the private remote, verify the clean working tree and remote checkpoint, and stop at the Phase 1 completion gate. Do not begin the Phase 2 read-only proof in the same change.

The trusted dependency-ordered delivery plan for worker execution and the Worker Lab GUI is `docs/WORKPLAN.md`.

Do not restart source recovery, import, or structural inventory work unless the underlying imported history or component paths change.
