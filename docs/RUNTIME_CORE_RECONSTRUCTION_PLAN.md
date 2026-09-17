# Runtime Core Reconstruction Plan

**Status:** Tasks 1–9 complete; deterministic reconstruction accepted.  
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
10. Reconstruction completion does not grant execution authority; activation/qualification still require separate user authorization.

## Intended V1 execution path

The execution/authority foundations below exist, but the sequential Controller / Foreman does **not** exist yet. This diagram describes the intended composition, not an operational controller loop. The next implementation milestone is that sequential controller, with exact-file worker authority and controller-side validation through Worker Lab. No provider or Pi integration is declared qualified here.

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
- **Task 9:** full deterministic reconstruction acceptance on the exact checkpoint, with source identity, documentation, repository-boundary, no-fallback, clean-checkpoint, and disabled-execution gates all passing.

Git history contains the detailed implementation history of Tasks 1–9.

## Task 9 — accepted deterministic reconstruction gate

The exact accepted checkpoint was required to prove:

- current complete Autonomous Worker Framework tests pass;
- current complete Worker Lab tests pass;
- portable source identity V2 verification and tests pass;
- current source/component digests match exact committed bytes;
- current operating documentation describes one architecture only;
- obsolete active-runtime references are absent from production/config/current operating docs;
- any surviving repository-specific contract is explicitly justified as Git-workspace/backend mechanics or evidence;
- the checkpoint contains no temporary Task 9 validation machinery;
- local activation has not been smuggled into committed source identity;
- provider capability qualification requires an explicit injected probe runner;
- no implicit provider/model/runner fallback exists;
- execution remains `DISABLED`;
- no actual provider/model request or real capability qualification occurred during reconstruction.

Task 9 changes only the accepted reconstruction status/documentation. It does not alter production runtime behavior or portable component byte closures.

## Post-reconstruction stop gate

Reconstruction is complete, but this is **not** authorization to run a model or activate ACL.

The next implementation milestone is the missing sequential controller. Actual host/provider capability qualification and a supervised disposable vertical slice require separate explicit user authorization. Provider/model choice should be informed by qualification and, where useful, separate Benchmark Lab evidence; benchmark output remains advisory and cannot authorize ACL work. Authentication is provider-neutral and uses operator-approved credentials for the selected transport.

Persistent execution, autonomous retry loops, GUI work, Knowledge Core expansion, Linux containment, publication authority, and broader model/harness campaigns remain separate later tasks.
