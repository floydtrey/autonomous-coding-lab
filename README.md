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

For Knowledge Core, read [current state](docs/architecture/knowledge-core/CURRENT_STATE.md), [architecture](docs/architecture/knowledge-core/ARCHITECTURE.md), then [operations/evidence](docs/architecture/knowledge-core/OPERATIONS.md). These are its three authoritative current documents. `docs/architecture/knowledge-core/legacy/` preserves historical evidence outside the default read order. Research under `docs/research/` is evidence/reference material, not runtime authority.

## Reconstruction status

Runtime reconstruction Tasks 1–9 are complete in the accepted architecture. The deterministic reconstruction gate has passed on the exact checkpoint bytes.

**Execution authority remains `DISABLED`.** Actual provider/model host qualification, supervised disposable vertical-slice execution, or persistent activation requires separate explicit user authorization after reconstruction.
