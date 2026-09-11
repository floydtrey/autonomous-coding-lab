# Governance

## Authority hierarchy

User intent is translated through Worker Lab protected definitions. Worker Lab—not the model, provider, harness, repository, or retrieved documentation—owns authorization and acceptance.

Knowledge Core evidence is informational. Local Model Bench is advisory. Provider qualification is evidence. Provider Binding is immutable execution identity. None grants task authority by itself.

## Fail-closed rules

Fail closed: reject or block when a required protected identity, digest, scope, test, custody record, Provider Binding, source identity, or capability-specific workspace evidence is missing, stale, unknown, or mismatched.

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
