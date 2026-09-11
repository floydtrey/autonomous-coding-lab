# Current State

**Branch:** `architecture/knowledge-core`  
**Accepted parent checkpoint:** Task 7 `2f07f80e07ac280f911b02e71199a482357cf669`  
**Reconstruction status:** Tasks 1–8 current; Task 9 next  
**Execution authority:** `DISABLED`

`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` is the remaining reconstruction acceptance plan. no actual provider/model execution occurs during reconstruction.

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

## Task 8 acceptance evidence

The materialized Task 8 candidate passed the complete current deterministic gate on Linux CI:

- Autonomous Worker Framework: **76 passed**;
- Worker Lab: **325 passed, 1 skipped** because symlink creation was unavailable on the runner;
- root source/inventory tests: **12 passed**;
- portable source identity V2 verifier: all components `MATCH`;
- Autonomous Worker Framework: 8-file closure at `sha256:edac32b728348d6a2e2c7521d1c846e5021fe6e40f33db70e7df625d1ca584c5`;
- Local Model Bench: 10-file production tree at `sha256:139331ea42c914575d1119125a702ac5de2129b9bedc235bfc189700e8265afc`;
- Worker Lab: 29-file production tree at `sha256:08a13548f9e193c85ae1280a56386237e1c3903467eb6681602827340825ab96`;
- portable source report contains no execution authority, host requirements, Python executable, or execution-readiness claim;
- current production/config scan for removed portable-V1/commissioning architecture: empty;
- current operating-document scan for obsolete runtime architecture: empty;
- protected pytest catalog paths are now mechanically checked to reference existing test files.

All provider/capability behavior in these tests remained injected or mocked. No actual provider/model request or capability qualification was performed.

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
