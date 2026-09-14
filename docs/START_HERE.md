# Start Here

This is the routing page for current ACL work.

## Current authority order

1. `AGENTS.md` — repository work rules.
2. `docs/CURRENT_STATE.md` — exact current runtime/reconstruction state.
3. `docs/ARCHITECTURE.md` — current system boundaries and execution path.
4. `docs/GOVERNANCE.md` — authority/security rules.
5. `docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` — reconstruction acceptance record and post-reconstruction boundary.

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

## Reconstruction status

Tasks 1–9 are complete. Task 9 accepted the exact current architecture through the complete deterministic test, source-identity, documentation, repository-boundary, no-fallback, and disabled-execution gates.

Reconstruction completion does **not** activate ACL. Until the user separately authorizes the next supervised stage:

- do not execute a provider/model;
- do not perform real provider capability qualification;
- do not enable persistent execution;
- do not introduce provider/model/runner fallback;
- do not broaden current bounded workspace/tool authority.

The next permitted stage, when separately authorized, is actual host/provider qualification followed by a supervised disposable vertical slice. Benchmark-lab work remains separate and advisory.

## Research and Knowledge Core docs

`docs/research/` is non-authoritative research/reference material. For Knowledge Core, read [current state](architecture/knowledge-core/CURRENT_STATE.md), [architecture](architecture/knowledge-core/ARCHITECTURE.md), then [operations/evidence](architecture/knowledge-core/OPERATIONS.md). These three documents govern current KC work; its retrieval output remains informational to Worker Lab.

`docs/architecture/knowledge-core/legacy/` preserves historical KC documents and accepted evidence outside the default read order. Its old status and next-task prose are not current guidance. Git history remains intact; there is no second legacy runtime to resume.
