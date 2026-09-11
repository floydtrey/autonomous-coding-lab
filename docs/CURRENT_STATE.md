# Current State

**Branch:** `architecture/knowledge-core`  
**Reconstruction status:** Tasks 1–9 complete; deterministic reconstruction accepted  
**Execution authority:** `DISABLED`

`docs/RUNTIME_CORE_RECONSTRUCTION_PLAN.md` is the reconstruction acceptance record and post-reconstruction boundary. No actual provider/model execution occurred during reconstruction.

## Current runtime architecture

ACL has one active runtime architecture:

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

It binds source/component bytes only. It intentionally excludes operating system/CPU identity, Python executable/path requirements, provider/model installation state, capability qualification, local activation, and task authorization. `tools/verify_portable_source.py` verifies the same source closure on a compatible host without claiming that host/provider is qualified or execution-ready.

Accepted component identities remain:

- Autonomous Worker Framework: 8-file closure at `sha256:edac32b728348d6a2e2c7521d1c846e5021fe6e40f33db70e7df625d1ca584c5`;
- Local Model Bench: 10-file production tree at `sha256:139331ea42c914575d1119125a702ac5de2129b9bedc235bfc189700e8265afc`;
- Worker Lab: 29-file production tree at `sha256:08a13548f9e193c85ae1280a56386237e1c3903467eb6681602827340825ab96`.

## Provider qualification separation

Provider installation observation V2 records installed host/provider/model facts only. Controlled capability qualification V2 records tested tool/context capability only. Neither record contains execution authority or claims execution readiness.

Provider Binding seals the exact capability-qualification digest, model identity, adapter/tool surface, runtime requirement, and runtime settings before Worker Lab authorization. Qualification evidence never activates ACL.

There is no default capability-probe runner and the normal CLI does not inject a workspace dispatch runner.

## Task 9 deterministic reconstruction acceptance

Task 9 accepted the exact checkpoint only after the complete deterministic gate proved all required boundaries together:

- complete Autonomous Worker Framework suite passes;
- complete Worker Lab suite passes, with only the known environment-dependent symlink skip where symlink creation is unavailable;
- root portable-source/inventory tests pass;
- portable source identity V2 reports every component `MATCH` against exact committed bytes;
- source identity contains no execution authority, host requirements, Python executable, provider runtime, or execution-readiness claim;
- current operating documentation describes one architecture;
- active production/config/current operating docs contain no obsolete commissioning/runtime identity references;
- repository-specific contracts that remain are bounded Git-workspace mechanics/evidence rather than ACL logical system identity;
- protected catalog pytest paths resolve to existing test files;
- provider capability qualification still requires an explicitly injected probe runner;
- no implicit provider/model/runner fallback exists;
- the exact checkpoint contains no Task 9 temporary validation machinery;
- execution remains `DISABLED`;
- no actual provider/model request or real capability qualification occurred during reconstruction.

Task 9 did not modify production runtime behavior. Its accepted commit changes current operating status/documentation only; the source/component digests above therefore remain unchanged from Task 8.

## Post-reconstruction boundary

Reconstruction is complete, but ACL is **not activated**.

Only after separate explicit user authorization may the next stage perform actual host/provider capability qualification and then a supervised disposable vertical slice. Persistent execution, autonomous retry loops, GUI expansion, Linux containment work, or broader runtime expansion remain separate later decisions.

Benchmark Lab remains a separate advisory system. Benchmark results may inform which model/configuration to qualify for ACL roles, but do not authorize ACL execution or alter Provider Binding/Worker Lab policy by themselves.
