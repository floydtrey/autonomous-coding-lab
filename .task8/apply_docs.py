from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.strip() + "\n", encoding="utf-8")


for stale in (ROOT / "docs" / "legacy", ROOT / "migration" / "inventory"):
    if stale.exists():
        shutil.rmtree(stale)
old_portable = ROOT / "docs" / "PORTABLE_INSTALLATION_IDENTITY.md"
if old_portable.exists():
    old_portable.unlink()

write("README.md", r'''
# Autonomous Coding Lab

Autonomous Coding Lab (ACL) is a supervised local-agent system for bounded work. It combines a protected authority plane, governed knowledge context, a provider-neutral execution framework, and an advisory model benchmark. Git is one coding-workspace backend; it is not ACL's system identity.

## Current architecture

- **Worker Lab** owns policy, roles, exercises, lifecycle, test selection, authorization, Provider Binding, and independent result acceptance.
- **Autonomous Worker Framework** executes one bounded task inside the exact supplied workspace/tool scope and returns evidence; it does not grant itself authority.
- **Knowledge Core** supplies governed informational context through Controller Task Packet V1; retrieved content never expands authority.
- **Local Model Bench** is advisory. Benchmark scores may inform model selection but never authorize execution.
- **Provider adapters and containment backends** are replaceable implementations beneath the protected contracts. The current first provider adapter is Pydantic AI + Ollama; the current first containment backend is Windows Job Objects.

The current runtime path is Invocation/Result V3 and Provider Binding V1. A different qualified model/provider must be selectable through qualification and binding data rather than source edits.

## Identity boundaries

`config/portable-source-manifest.json` is **portable source identity V2**. It binds reviewed ACL source/component bytes only. It deliberately does not contain host requirements, provider qualification, local activation, or task authorization.

These are separate layers:

1. portable source identity;
2. host/provider installation observation;
3. controlled provider capability qualification;
4. immutable Provider Binding;
5. local operator activation/containment state;
6. one-invocation Worker Lab authorization.

A repository URL, branch, checkout path, remote, or `.git` directory is never ACL target identity. Git facts appear only where a Git-backed coding workspace needs exact source-state evidence.

## Start here

Read these current documents in order:

1. `AGENTS.md`
2. `docs/START_HERE.md`
3. `docs/CURRENT_STATE.md`
4. `docs/ARCHITECTURE.md`
5. `docs/GOVERNANCE.md`

Operational references:

- `docs/OPERATIONS.md`
- `docs/DEVELOPMENT.md`
- `docs/PORTABLE_SOURCE_IDENTITY.md`
- `docs/CONTROLLER_TASK_PACKET_V1.md`
- `docs/REPOSITORY_COUPLING_INVENTORY.md`
- `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md`

Knowledge Core design/evidence lives under `docs/architecture/knowledge-core/`. Research under `docs/research/` is evidence/reference material, not runtime authority.

## Reconstruction status

Runtime reconstruction Tasks 1–8 are represented by the current tree. Task 9 is the remaining deterministic acceptance gate before any real provider/model qualification or supervised model execution is authorized.

**Execution authority remains `DISABLED`.**
''')

write("AGENTS.md", r'''
# ACL Agent Instructions

This file is the repository-level router for work in Autonomous Coding Lab.

## Read order

Before modifying the current runtime, read:

1. `AGENTS.md`
2. `docs/START_HERE.md`
3. `docs/CURRENT_STATE.md`
4. the governing architecture/plan named by `CURRENT_STATE.md`
5. only the component files required by the bounded task

Do not load all research or historical Git material by default. Git history is the archive. `docs/research/` is advisory evidence and is read only when the task explicitly needs it.

## Authority

Worker Lab owns policy, role, exercise, lifecycle, test-plan selection, task authorization, Provider Binding, and result acceptance. Knowledge Core provides informational context only. Autonomous Worker Framework executes bounded work but does not grant execution authority. Local Model Bench outputs are advisory and do not grant execution authority.

Do not allow a model, provider, harness, repository, workspace, or retrieved document to expand authorized scope.

## Execution safety

Execution authority remains `DISABLED` during reconstruction. Do not run a provider/model, perform actual capability qualification, or add an implicit provider/runner fallback unless a later accepted gate and explicit user authorization permit it.

No shell, process, network, Git publication, approval, or arbitrary filesystem authority exists unless a protected task capability explicitly grants it. Fail closed on missing or mismatched identity/evidence.

## Identity rules

Portable source identity is `config/portable-source-manifest.json`. It is source-byte identity only. Host qualification, provider capability qualification, local activation, and task authorization are separate evidence/state layers.

Logical ACL target/workspace identity must not be a repository locator. Repository paths/remotes/commits are permitted only as bounded Git-workspace mechanics or evidence.

## Work discipline

Keep tasks bounded. Verify branch/HEAD/tree before and after consequential changes. Prefer deterministic tests and exact-byte evidence. Do not repeat a check when a stronger already-current result proves the same fact, but rerun gates when behavior-bearing bytes change.

Do not preserve obsolete runtime behavior through compatibility shims merely because Git history contains it. Do not recreate removed legacy documentation inside the active tree.
''')

write("docs/START_HERE.md", r'''
# Start Here

This is the routing page for current ACL work.

## Current authority order

1. `AGENTS.md` — repository work rules.
2. `docs/CURRENT_STATE.md` — exact current runtime/reconstruction state.
3. `docs/ARCHITECTURE.md` — current system boundaries and execution path.
4. `docs/GOVERNANCE.md` — authority/security rules.
5. `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` — remaining reconstruction acceptance work.

For source portability, read `docs/PORTABLE_SOURCE_IDENTITY.md`. For Controller/Knowledge Core handoff, read `docs/CONTROLLER_TASK_PACKET_V1.md`. For Git/repository boundaries, read `docs/REPOSITORY_COUPLING_INVENTORY.md`.

## Component ownership

- Worker Lab: protected authority, lifecycle, Provider Binding, dispatch preparation, independent acceptance.
- Autonomous Worker Framework: bounded execution/workspace containment and provider adapter surface.
- Knowledge Core: governed informational context only.
- Local Model Bench: advisory evaluation only.

## Current identity model

Portable source identity is host-independent and lives in `config/portable-source-manifest.json`. It contains reviewed component byte closures, not host/runtime activation facts.

Host/provider installation observation, capability qualification, Provider Binding, local activation, and per-invocation authorization are separate. A source checkout is not enabled by editing committed identity data.

ACL target identity is logical (`target:*` / `workspace:*`). Git repository facts are optional coding-workspace evidence beneath that boundary.

## Current reconstruction gate

Tasks 1–8 have established the current architecture. Task 9 is the final deterministic reconstruction acceptance gate. Until it passes and the user separately authorizes a supervised run:

- do not execute a provider/model;
- do not perform real capability qualification;
- do not enable persistent execution;
- do not introduce provider/model fallback;
- do not broaden current bounded workspace/tool authority.

## Research and Knowledge Core docs

`docs/research/` is non-authoritative research/reference material. `docs/architecture/knowledge-core/` contains accepted Knowledge Core design/evidence; its retrieval output remains informational to Worker Lab.

Git history is the historical archive. There is no active `docs/legacy/` documentation tree.
''')

write("docs/CURRENT_STATE.md", r'''
# Current State

**Branch:** `architecture/knowledge-core`  
**Accepted parent checkpoint:** Task 7 `2f07f80e07ac280f911b02e71199a482357cf669`  
**Reconstruction status:** Tasks 1–8 current; Task 9 next  
**Execution authority:** `DISABLED`

`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` is the remaining reconstruction acceptance plan. No actual provider/model execution occurs during reconstruction.

## Current runtime architecture

ACL now has one active runtime architecture:

- Worker Lab is the authority plane.
- Controller Task Packet V1 carries user request plus governed Knowledge Core evidence as informational context.
- Invocation/Result V3 binds logical target/workspace identity, exact protected scope/tests, source identity, runtime requirement, and exact Provider Binding before dispatch.
- Autonomous Worker Framework dispatch is provider-neutral and requires an explicitly supplied bound provider executor.
- Provider installation observation and controlled capability qualification are separate from source identity and separate again from authorization.
- Pydantic AI + Ollama is the first qualified-adapter design, not a hard-coded permanent provider choice.
- Windows Job Objects are the first containment backend, not a universal ACL identity requirement.
- Candidate/result acceptance independently checks custody, authorized changed paths, protected tests, and Git workspace evidence when the selected task capability is Git-backed.

There is no active compatibility path for the removed commissioning/V2 runtime.

## Portable source identity V2

`config/portable-source-manifest.json` uses `acl-portable-source-manifest:v2` and identifies `acl-runtime-source:v2`.

It binds source/component bytes only. It intentionally excludes:

- operating system or CPU architecture;
- Python executable/path/version requirements;
- provider/model installation state;
- capability qualification;
- local activation/kill-switch state;
- task authorization.

Those concerns are separate evidence/state layers. `tools/verify_portable_source.py` verifies the same source closure on any compatible host without claiming that host or provider is qualified or execution-ready.

Task 8 preserves the accepted Task 7 Autonomous Worker Framework closure (8 files) and Local Model Bench production tree (10 files). Worker Lab source identity is recomputed from its current production tree after the Task 8 separation changes.

## Provider qualification separation

Provider installation observation V2 records installed host/provider/model facts only. Controlled capability qualification V2 records tested tool/context capability only. Neither record contains execution authority or claims execution readiness.

Provider Binding still seals the exact capability-qualification digest, model identity, adapter/tool surface, runtime requirement, and runtime settings before Worker Lab authorization. Qualification evidence never activates ACL.

There is no default capability-probe runner and the normal CLI does not inject a workspace dispatch runner.

## Current source/document surface

Current operating documents are the root files linked from `README.md`. Historical runtime documentation and consolidation snapshots are removed from the active tree; Git history remains the archive. Knowledge Core architecture/evidence and explicit research documents remain because they have current analytical or governing purpose.

`docs/REPOSITORY_COUPLING_INVENTORY.md` records only the currently justified Git-workspace mechanics/evidence and the target/workspace identity boundary.

## Validation status

Task 8 focused source-identity/V3 validation passes on Linux CI, demonstrating that source identity does not require Windows host claims. The final Task 8 checkpoint still requires the complete surviving component suites, source-manifest verification, current-document scan, and exact-byte validation before publication.

## Immediate next gate

Perform only **Task 9 — full deterministic reconstruction acceptance** after Task 8 is published.

Task 9 must prove:

- complete relevant component tests pass;
- portable source identity V2 matches exact committed bytes;
- current operating docs describe one architecture;
- no obsolete active-runtime references remain in production/config/current operating docs;
- no unjustified repository-as-system identity remains;
- execution remains disabled;
- no provider/model request has been sent.

Only after Task 9 and separate user authorization may actual provider/model qualification or a supervised disposable vertical slice begin.
''')

write("docs/ARCHITECTURE.md", r'''
# Architecture

ACL is a supervised system for turning a user objective into one bounded, independently verified task execution. Repository mechanics are optional backend details, not the system abstraction.

## Authority plane

Worker Lab owns the protected definition and lifecycle of work:

- curriculum/exercise, policy, role, context manifest, and test catalog;
- attempts and workspace receipts;
- Controller Task Packet identity;
- runtime requirement and sealed runtime settings;
- provider capability qualification and Provider Binding;
- Invocation/Result V3 lifecycle;
- containment/custody evidence;
- independent result/candidate acceptance.

A provider, model, harness, or worker cannot self-authorize or self-certify acceptance.

## Informational knowledge plane

Knowledge Core stores and retrieves governed information. Controller Task Packet V1 binds exact Knowledge Core evidence into the task prompt while marking it informational-only. Retrieved content cannot add readable/writable paths, tools, tests, capabilities, publication authority, or lifecycle authority.

## Execution plane

Autonomous Worker Framework receives one canonical dispatch envelope and independently validates the protected identities/scope. It reconstructs the bounded task and invokes one explicitly supplied provider executor whose adapter, tool surface, Provider Binding, and runtime settings match the sealed request.

The provider receives only ACL-owned tools. Current bounded coding tools are exact-file read/write operations. Shell, process, arbitrary network, Git publication, approval, and unrestricted directory traversal are not implied provider capabilities.

## Provider model

The provider path is data-driven:

```text
installation observation
  -> controlled capability qualification
  -> Provider Binding
  -> Worker Lab task authorization
  -> bounded dispatch
```

Observation describes installed facts. Qualification proves the required controlled tool/context behavior. Provider Binding freezes the exact qualified combination for authorization. None of these layers is local activation by itself.

Pydantic AI + Ollama is the first adapter implementation. Another supported provider/model should require new observation/qualification/binding data, not changes to Worker Lab authority contracts.

## Containment

Durable process custody uses a provider-neutral V2 contract. Windows Job Objects implement the current Windows backend. A future Linux backend must fit the same authority/custody contract rather than changing Invocation/Result identity.

## Identity layers

1. **Portable source identity** — reviewed ACL component bytes (`acl-portable-source-manifest:v2`).
2. **Host/provider observation** — platform, Python/harness, provider executable/API, model metadata.
3. **Capability qualification** — controlled proof that the exact observed configuration satisfies required behavior.
4. **Provider Binding** — immutable provider/model/settings identity used before task authorization.
5. **Local activation/containment state** — operator/host state, never committed source identity.
6. **Task authorization** — one exact Worker Lab invocation and controller decision.

## Target/workspace boundary

Invocation V3 uses logical target/workspace identities. For the current coding slice, Git-backed source state is nested capability-specific evidence: base commit, workspace receipt/root/path digests, observed head, content digest, and changed paths.

Repository names, URLs, remotes, branch names, checkout paths, and `.git` are not logical ACL target identity.

## Acceptance boundary

Worker success is only a claim. Worker Lab independently checks durable custody, exact request/binding identities, authorized changed paths, sealed tests, candidate/result identity, and workspace evidence before lifecycle promotion.

Workers do not commit, push, merge, publish, or approve their own result unless a separate protected publication capability is explicitly introduced and authorized.

## Advisory benchmark

Local Model Bench is independent and advisory. Its measurements can help choose which model/configuration to qualify for a role. Benchmark output never modifies Worker Lab policy, Provider Binding, or task authorization.
''')

write("docs/GOVERNANCE.md", r'''
# Governance

## Authority hierarchy

User intent is translated through Worker Lab protected definitions. Worker Lab—not the model, provider, harness, repository, or retrieved documentation—owns authorization and acceptance.

Knowledge Core evidence is informational. Local Model Bench is advisory. Provider qualification is evidence. Provider Binding is immutable execution identity. None grants task authority by itself.

## Fail-closed rules

Reject or block when a required protected identity, digest, scope, test, custody record, Provider Binding, source identity, or capability-specific workspace evidence is missing, stale, unknown, or mismatched.

Do not silently fall back to another provider, model, tool surface, runtime setting, workspace, or target.

## Tool and effect boundary

The model receives only ACL-owned tools explicitly allowed by the task contract. Read-only and workspace-write are distinct authority classes. Shell, arbitrary process execution, unrestricted network access, Git publication, approval, and unrestricted filesystem enumeration are forbidden unless a future protected capability explicitly grants them.

Workers do not commit, push, merge, publish, or approve their own work under the current coding slice.

## Credential boundary

Secrets are host/operator concerns and must not be committed into source identity, prompts, evidence, benchmark fixtures, or candidate output. Provider adapters should use only the credentials required by their explicitly qualified transport. ACL must not expose unrelated environment secrets to a worker.

## Source, host, activation, and authorization separation

Portable source identity binds only reviewed source bytes. It is not a host qualification record and is not an activation switch.

Host/provider installation observation and capability qualification are separate evidence. Local activation or a future kill switch must live in local operator state outside committed source identity. Per-task authorization remains a Worker Lab lifecycle transition over one exact Provider Binding.

Changing source identity must never be the mechanism for enabling execution.

## Logical target identity

ACL target identity is logical and stable across repository relocation. Git repository mechanics are allowed only inside a Git-backed coding-workspace backend. A repository URL/path/branch/remote must not substitute for system identity or authorization.

## Provider/model changes

A new provider/model/configuration requires observation, controlled qualification, and a new Provider Binding. The change must not require rewriting Worker Lab authority, Knowledge Core, Controller Task Packet, result acceptance, or lifecycle semantics.

## Publication

Execution and publication are separate. A valid candidate does not authorize commit, push, merge, deployment, or external side effects. Publication requires its own future protected capability and human/controller policy.

## Reconstruction safety

Execution remains `DISABLED` until Task 9 passes and the user separately authorizes the next supervised step. No actual provider/model qualification or model request is part of Tasks 1–9 unless explicitly authorized outside this reconstruction plan.
''')

write("docs/DEVELOPMENT.md", r'''
# Development

## Bounded changes

Make one architectural change at a time. Verify branch/HEAD/tree, preserve fail-closed semantics, run focused tests first, then the relevant full suites. Do not restore obsolete compatibility paths to satisfy stale tests; update tests to the current contract when equivalent coverage exists.

## Portable source identity

`config/portable-source-manifest.json` is behavior-bearing source identity. When a production component in its closure changes, recompute that component's exact file-set digest in the same bounded change.

Use:

```text
python tools/verify_portable_source.py
```

The verifier checks source bytes only. It must work independently of operating system, Python executable path, provider installation, local activation, and task authorization.

Do not add host fields or activation state back to the source manifest.

## Component testing

- Autonomous Worker Framework tests run from `components/autonomous-worker-framework`.
- Worker Lab tests run from `components/worker-lab`.
- portable source tests run from repository root.
- Knowledge Core has its own governed test/qualification workflow.

Use injected/mock provider runners for deterministic reconstruction tests. A test that needs a real model/provider is outside Tasks 1–9 unless separately authorized.

## Contract evolution

Version a durable schema when behavior-bearing semantics change. Keep logical target/workspace identity independent of repository location. Keep provider/model/settings inside qualification/binding. Keep host/process facts inside host/containment evidence.

Do not use a broad field rename to hide responsibility ambiguity; move the fact to the layer that owns it.

## Documentation

Current operating truth belongs in the root documents linked by `README.md`. Git history is historical documentation. Do not create a second legacy operating tree.

Research under `docs/research/` must be clearly treated as advisory evidence. Knowledge Core architecture/evidence under `docs/architecture/knowledge-core/` remains current for that component, but root `docs/CURRENT_STATE.md` controls ACL runtime status.

## Git workspace mechanics

The first coding slice uses Git for exact source-state evidence and optional publication tooling. Those mechanics must remain behind the coding-workspace/backend boundary and must not become universal ACL target identity.
''')

write("docs/OPERATIONS.md", r'''
# Operations

This guide describes the current reconstructed ACL runtime. It does not authorize model execution.

## 1. Verify portable source identity

From the repository root:

```text
python tools/verify_portable_source.py
```

A valid report uses `acl-portable-source-report:v2` and reports every component as `MATCH`. The report intentionally contains no host qualification, provider qualification, activation, or execution-readiness claim.

## 2. Inspect Worker Lab source status

From `components/worker-lab` with the package importable:

```text
python -m worker_lab.cli source-status
python -m worker_lab.cli doctor
```

Both validate the same committed source identity. They do not qualify the host/provider and do not enable execution.

## 3. Host/provider qualification boundary

Provider installation observation records the actual host/Python/harness/provider/model facts. Controlled capability qualification additionally proves the protected bounded-file tool fixture and requested context target.

There is no default capability probe runner. Do not perform real capability qualification during reconstruction unless separately authorized.

After qualification, create a Provider Binding for the exact model/configuration and sealed runtime settings. Qualification and binding still do not authorize a task.

## 4. Prepare a V3 invocation

The current CLI preparation surface requires a logical target and exact Provider Binding:

```text
python -m worker_lab.cli --root <lab-root> prepare-invocation <attempt-id> \
  --workspace-root <workspace> \
  --prompt-file <controller-task-packet.json> \
  --logical-target-id target:<logical-name> \
  --provider-binding-id <binding-id> \
  --provider-binding-digest sha256:<digest>
```

The prompt must be the canonical Controller Task Packet expected by the protected attempt. Git checkout paths are workspace locators, not logical target IDs.

## 5. Authorization and dispatch

Authorization requires the exact prepared invocation identity and controller identity. Dispatch additionally requires the exact workspace and an injected current V3 dispatch runner.

The normal CLI constructs no provider runner. Therefore source verification, doctor, preparation, and authorization do not silently start a model/provider. Missing runner/provider/custody evidence fails closed.

## 6. Candidate review and evidence

A provider/framework success response is not acceptance. Worker Lab reruns protected tests and independently observes capability-specific workspace evidence before producing Result V3 and promoting an attempt to candidate state.

## 7. Containment

Windows Job Objects are the current Windows containment backend. Durable custody is backend-neutral. A different OS requires a compatible containment backend plus qualification; it must not require changing portable source identity.

## 8. Backup and restore

Worker Lab backup/verify/restore commands remain available for durable state. Always verify a backup before relying on it for recovery.

## 9. Benchmarking

Local Model Bench is advisory and separate from runtime authority. Benchmark a model/configuration before role assignment when useful, then qualify the chosen exact runtime through the provider qualification path. Benchmark scores alone are never Provider Binding evidence.

## Current stop condition

Task 9 is the remaining deterministic reconstruction acceptance gate. Until it passes and the user separately authorizes a supervised run, do not perform real model execution or persistent activation.
''')

write("docs/PORTABLE_SOURCE_IDENTITY.md", r'''
# Portable Source Identity V2

## Purpose

Portable Source Identity V2 answers one question: **which reviewed ACL source/component bytes are this runtime built from?**

It does not answer whether a host, provider, model, containment backend, or task is qualified or authorized.

## Contract

Manifest: `config/portable-source-manifest.json`  
Schema: `acl-portable-source-manifest:v2`  
Source identity: `acl-runtime-source:v2`  
Verifier: `tools/verify_portable_source.py`

The manifest contains:

- Autonomous Worker Framework current runtime dependency closure;
- Worker Lab Python production tree;
- Local Model Bench Python production tree;
- exact SHA-256 file-set digests;
- an explicit separation policy declaring host qualification, provider capability qualification, local activation, and task authorization external to source identity.

It contains no Windows requirement, CPU architecture, Python executable path/version, provider/model state, participant activation state, or execution-ready flag.

## Digest model

Each component digest is the canonical SHA-256 of ordered entries:

```text
{"path": <component-relative path>, "sha256": <file bytes digest>}
```

The framework uses an explicit current runtime closure. Worker Lab and Local Model Bench use their production Python trees. Paths are checkout-relative and path traversal/symlink indirection is rejected at the verification boundary.

## Separation policy

- `host_qualification = separate-evidence`
- `provider_capability_qualification = separate-evidence`
- `local_activation = local-operator-state`
- `task_authorization = worker-lab-invocation-v3`

A source checkout is never enabled by editing this manifest. If a host-level kill switch/activation mechanism is introduced, it must be local operator state outside committed source identity.

## Verification

Run from any compatible checkout:

```text
python tools/verify_portable_source.py
```

A `MATCH` report proves exact source bytes only. It does **not** prove host compatibility, provider capability, local activation, or task authorization.

## Portability meaning

Moving ACL to another compatible host should require host/containment/provider qualification, not edits to source identity merely because paths, OS details, Python executable location, GPU/runtime, or provider installation differ.
''')

write("docs/CONTROLLER_TASK_PACKET_V1.md", r'''
# Controller Task Packet V1

Controller Task Packet V1 is the canonical informational handoff from the controller/Knowledge Core boundary into the current Invocation V3 workspace-write path.

## Contents

The packet binds:

- attempt/controller identity;
- user request;
- protected exercise identity and starting Git source state for the current coding capability;
- exact governed Knowledge Core segment evidence/content/provenance.

## Authority boundary

Knowledge Core evidence is informational only. Packet content cannot grant or modify writable/readable scope, sandbox mode, tools, policy/role, test plan, acceptance criteria, provider/model selection, Provider Binding, publication authority, or lifecycle transitions.

Worker Lab protected definitions remain authoritative for those facts.

## Current V3 handoff

The packet is canonical JSON. Worker Lab binds its digest into Invocation V3 and the provider-neutral dispatch envelope. The framework independently validates packet/invocation linkage before bounded execution can be reached.

Current public V3 preparation does not use a plain-text compatibility prompt path. A packet mismatch or provenance/content mismatch fails closed.

## Knowledge evidence

`worker-lab-knowledge-core-segment-evidence:v1` preserves generation/profile identity, source/version references, lifecycle state, exact byte/line coordinates, source-slice digest, and exact content. Only evidence accepted by the current consumer contract may be served into the packet.

Repository/source fields inside Knowledge Core provenance describe governed source evidence; they do not become ACL target identity or execution authority.
''')

write("docs/REPOSITORY_COUPLING_INVENTORY.md", r'''
# Repository Coupling Inventory

**Status:** current after runtime reconstruction Task 8.

ACL is a system with optional task/workspace backends. A Git repository is the substrate for the first coding-workspace capability, not ACL target identity.

## Logical identity

Invocation V3 requires logical `target:*` and `workspace:*` identities. Repository names, URLs, branches, remotes, local checkout paths, and `.git` forms are rejected as logical target identity.

## Justified Git-backed workspace mechanics/evidence

The following remain intentionally Git-specific because the current coding slice requires exact source-state evidence:

- Autonomous Worker Framework `repository_state.py`, `repository_handoff.py`, and optional `local_git_publisher.py` mechanics;
- Worker Lab workspace preparation/verification and workspace receipt records;
- Invocation V3 nested Git source state (base commit and workspace receipt/root/path digests);
- Result V3 Git workspace evidence (base/observed head, content digest, changed paths);
- attempt/exercise fields that identify the exact template/base commit for the Git-backed coding capability;
- CLI repository/workspace path arguments used to locate that backend.

These facts are capability/backend evidence. They do not authorize work and do not identify the logical target system.

## Backend-only locators

Local checkout paths supplied to workspace preparation, verification, dispatch, recovery, or publication are process/backend locators. They are not durable universal ACL identity.

## Removed repo-as-system coupling

The current runtime no longer has a monorepo identity contract or repository URL/name as universal ACL identity. Portable source identity uses checkout-relative component paths only to hash the reviewed ACL source tree; it does not identify the task target.

## Task 9 audit rule

Any remaining production/domain field named `repository`, `template_repository`, `target_repository`, branch, remote, or `.git` must be explainable as one of the Git-workspace mechanics/evidence above. If it is used as logical target identity, provider selection, authority, or portable host identity, Task 9 must fail.
''')

write("docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md", r'''
# Runtime Core Reconstruction Plan

**Status:** Tasks 1–8 complete in the current architecture; Task 9 next.  
**Execution authority:** `DISABLED`

## Goal

Reconstruct ACL around one provider-neutral, target-system-centered authority/execution path before any real model run.

## Current invariants

1. Worker Lab owns policy, role, exercise, lifecycle, test selection, task authorization, Provider Binding, and result acceptance.
2. Knowledge Core is informational and cannot grant execution authority.
3. Autonomous Worker Framework performs bounded execution and does not self-authorize.
4. Provider/model/runtime settings are sealed by exact qualification/binding before authorization; no implicit fallback exists.
5. Portable source identity is host-independent and separate from host/provider qualification, local activation, and task authorization.
6. Logical target/workspace identity is not a repository locator. Git facts are coding-workspace evidence only.
7. Durable containment/custody is backend-neutral; Windows Job Objects are the current first backend.
8. Workers receive only ACL-owned protected tool scope. Shell/network/process/publication/approval authority is not implied.
9. Worker success is independently verified before acceptance.
10. Execution remains disabled through reconstruction.

## Current execution path

```text
User objective
  -> Controller / Foreman
  -> governed Knowledge Core retrieval
  -> Controller Task Packet V1
  -> Worker Lab protected authority
  -> Invocation V3 + exact Provider Binding
  -> generic dispatch client
  -> containment backend
  -> generic dispatch adapter
  -> exact qualified provider/model + sealed settings
  -> WorkerExecution
  -> independent Worker Lab verification
  -> verified / retry / blocked / human review
```

## Completed reconstruction tasks

- **Task 1:** provider-neutral repository-state boundary and repository-coupling audit.
- **Task 2:** platform-neutral custody V2 with Windows containment backend.
- **Task 3:** Invocation/Result V3 and immutable Provider Binding foundation.
- **Task 4:** provider-neutral dispatch client/adapter with explicit executor and no fallback.
- **Task 5:** current application service/result acceptance migrated to V3.
- **Task 6:** installation observation separated from controlled capability qualification; sealed settings consumed by provider adapter.
- **Task 7:** obsolete active-tree runtime/config/test paths removed; current V3 path only.
- **Task 8:** portable source identity V2 separated from host/provider/activation/authorization state; current operating documentation reduced to one architecture.

Git history contains the detailed implementation history of Tasks 1–8.

## Task 9 — full deterministic reconstruction acceptance

Before any model run, prove on the exact candidate commit:

- current complete Autonomous Worker Framework tests pass;
- current complete Worker Lab tests pass;
- portable source identity V2 verification and tests pass;
- current source/component digests match exact committed bytes;
- current operating documentation describes one architecture only;
- obsolete active-runtime references are absent from production/config/current operating docs;
- any surviving repository-specific contract is explicitly justified as Git-workspace/backend mechanics or evidence;
- working tree/checkpoint contains no temporary validation machinery;
- local activation has not been smuggled into committed source identity;
- no implicit provider/model/runner fallback exists;
- execution remains `DISABLED`;
- no actual provider/model request or capability qualification has occurred during reconstruction.

**Stop gate:** only after Task 9 passes may the user separately authorize actual provider/model host qualification and a supervised disposable vertical slice.

## Out of scope until after Task 9

Do not run a local model, call chat/completion endpoints, enable persistent execution, add autonomous retry loops, add GUI work, expand Knowledge Core retrieval, build a Linux containment backend, or start a new broad model/harness campaign as part of reconstruction acceptance.
''')

write("docs/architecture/knowledge-core/CURRENT_STATE.md", r'''
# Knowledge Core Current State

Knowledge Core's accepted segment retrieval/consumer architecture remains intact and is not being reconstructed by ACL runtime Tasks 1–9.

## Current boundary

Knowledge Core provides governed informational evidence to Controller Task Packet V1. It does not choose providers/models, grant file/tool scope, authorize execution, or accept worker results.

Root `docs/CURRENT_STATE.md` is authoritative for ACL runtime/reconstruction status. This page is authoritative only for the Knowledge Core component boundary.

## Accepted Knowledge Core foundations

Current accepted design/evidence remains documented in this directory, including:

- Frozen Kernel and PostgreSQL qualification lineage;
- governed repository import and persistence/recovery qualification;
- `SECTION_RETRIEVAL_SR1.md` and KC-D025;
- SR-2 G1–G22 coverage/qualification artifacts;
- intended-host SR-2 qualification;
- KC Consumer V1 exact segment-content serving.

Canonical source evidence and derived retrieval projections remain distinct. Derived indexes remain generation/profile-bound and rebuildable. Provenance remains explicit and exact.

## Runtime integration rule

When ACL consumes Knowledge Core evidence, only the accepted Controller Task Packet/consumer contract may cross the boundary. Retrieved text remains informational-only and cannot alter protected Worker Lab authority.

For current runtime status and next work, return to `docs/CURRENT_STATE.md` and `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md`.
''')

write("components/autonomous-worker-framework/tests/test_project_documentation.py", r'''from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _read(path: str) -> str:
    return (REPOSITORY_ROOT / path).read_text(encoding="utf-8")


def test_current_document_set_exists_and_is_linked_from_readme():
    readme = _read("README.md")
    for path in (
        "docs/START_HERE.md",
        "docs/CURRENT_STATE.md",
        "docs/ARCHITECTURE.md",
        "docs/OPERATIONS.md",
        "docs/DEVELOPMENT.md",
        "docs/GOVERNANCE.md",
        "docs/PORTABLE_SOURCE_IDENTITY.md",
    ):
        assert (REPOSITORY_ROOT / path).is_file()
        assert path in readme


def test_agent_router_enforces_current_scope_and_authority_boundaries():
    agents = _read("AGENTS.md")
    assert "Git history is the archive" in agents
    assert "Do not repeat a check" in agents
    assert "do not grant execution authority" in agents
    assert "Local Model Bench outputs are advisory" in agents


def test_current_state_records_reconstruction_authority_and_remaining_work():
    current = _read("docs/CURRENT_STATE.md")
    assert "# Current State" in current
    assert "**Execution authority:** `DISABLED`" in current
    assert "docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md" in current
    assert "Task 9" in current
    assert "no actual provider/model execution occurs during reconstruction" in current


def test_architecture_and_governance_preserve_security_boundaries():
    combined = (_read("docs/ARCHITECTURE.md") + _read("docs/GOVERNANCE.md")).lower()
    for requirement in (
        "read-only",
        "workspace-write",
        "fail closed",
        "provider binding",
        "local activation",
        "workers do not commit, push, merge",
    ):
        assert requirement in combined


def test_no_active_legacy_documentation_tree():
    assert not (REPOSITORY_ROOT / "docs" / "legacy").exists()
    assert not (REPOSITORY_ROOT / "migration" / "inventory").exists()
''')

print("Task 8 current documentation surface materialized")
