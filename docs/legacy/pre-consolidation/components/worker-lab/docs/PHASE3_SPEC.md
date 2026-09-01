# Worker Lab Phase 3 Specification

**Status:** Candidate specification; implementation requires trusted approval
**Starting milestone:** `v0.2.0-phase2`
**Framework authority checkpoint:** `135373d24837f5d5b0da0650c9c00fc086fcb991`
**Scope:** Synthetic read-only proposals and one bounded workspace-write task

## Objective

Phase 3 connects Worker Lab to the existing Autonomous Worker Framework through one strict local
adapter. Worker Lab remains the curriculum, attempt, lifecycle, test-plan, evidence, failure, and
evaluation authority. The framework remains the only owner of Codex authentication, credential
sanitization, sandbox enforcement, runtime configuration, subprocess execution, target-repository
boundaries, and execution timeout.

Phase 3 first proves a read-only proposal against a verified synthetic workspace. Only after that
boundary passes may it prove one workspace-write task against a fresh synthetic workspace. Neither
operation targets an external product repository.

## Fixed authority boundary

| Decision or record | Owner | Required boundary |
|---|---|---|
| Curriculum, exercise, policy, role, context, test catalog, and test plan | Worker Lab | Exact protected record versions and digests |
| Attempt and workspace lifecycle | Worker Lab | Existing legal transitions; no framework writes to Lab state |
| Workspace creation, verification, quarantine, and disposal | Worker Lab | Receipt-bound Phase 2 operations only |
| Invocation authorization | Trusted controller through Worker Lab | Exact invocation digest; no worker self-authorization |
| Codex version and ChatGPT-managed authentication | Framework | `OPENAI_API_KEY` and `CODEX_API_KEY` fail closed |
| Worker environment | Framework | GitHub credential-like variables stripped |
| Sandbox and runtime command | Framework | Only fixed `read-only` or `workspace-write`; never danger/full access |
| Worker subprocess and timeout | Framework | Separate target repository and finite timeout |
| Changed-path and Git boundary observations | Framework and Worker Lab independently | Both must agree; either may reject |
| Trusted validation selection | Worker Lab | Exact catalog and test-plan digest |
| Trusted validation execution | Framework adapter | Sealed commands only; stop at first required failure |
| Result acceptance, failure classification, and evaluation | Worker Lab/trusted controller | Structured result plus independent evidence |
| Commit, remote, publication, approval, and merge | Nobody in Phase 3 | Explicitly excluded |

The worker is untrusted. It cannot read Worker Lab state, alter its exercise or evaluator, change the
invocation envelope, grant itself paths, select tests, commit, publish, approve, merge, retry, or
change lifecycle state. Worker text is evidence content, never authority.

## Selected integration mechanism

### Decision

Use a fixed, framework-owned local process adapter with canonical JSON on standard input and one
canonical JSON response on standard output. The first implementation target is a single explicit
framework entry point such as `tools/worker_lab_adapter.py`; the final filename is fixed in Batch 3B.

Worker Lab invokes an exact absolute adapter path from an exact clean framework Git commit using the
trusted configured Python runtime. The command shape is fixed in Worker Lab configuration. Exercises,
workers, prompts, and invocation records cannot supply executable paths, command-line flags,
environment variables, working directories, or arbitrary Codex options.

The adapter:

1. strictly parses one supported request schema and rejects unknown fields;
2. recomputes request identity and framework identity;
3. maps the approved operation to its fixed sandbox and runtime profile;
4. uses existing framework runtime functions for authentication, sanitization, sandboxing, and Codex
   execution;
5. performs framework-owned boundary and trusted-validation checks;
6. emits exactly one strict result object; and
7. returns nonzero on a boundary failure while still emitting a parseable failure result when safe.

### Rejected mechanisms

- Direct cross-repository imports or `sys.path` mutation: couples internal modules and bypasses a
  versioned process boundary.
- Reusing `context_probe.py` directly: its default consumer profile is Mine Tracker-specific and its
  result lacks Phase 3 invocation, runtime, non-mutation, and failure identities.
- Reusing `code_task.py` or `worker-result:v1` unchanged: the former raises unstructured exceptions
  and omits candidate content identity; the latter is coupled to existing framework handoff semantics
  and does not bind a Worker Lab invocation or workspace receipt.
- Network service, RPC framework, plugin system, queue, daemon, or scheduler: unnecessary for the
  local single-user first integration.

The adapter is transport, not a new authority service.

## Versioned invocation contract

Batch 3B adds a strict `worker-lab-framework-invocation:v1` record persisted under
`state/invocations/<invocation-id>.json`. It is durable evidence and therefore included in backup.
It contains no credentials, usable secret, or arbitrary executable configuration.

Required fields:

| Field | Source and validation |
|---|---|
| `schema_version` | Exact `worker-lab-framework-invocation:v1` |
| `invocation_id` | Immutable Worker Lab-generated identity |
| `attempt_id` | Exact existing attempt |
| `operation` | Exactly `read-only-proposal` or `workspace-write-code-task` |
| `exercise_id`, `exercise_version`, `exercise_digest` | Recomputed from the protected exercise |
| `policy_id`, `policy_version`, `policy_digest` | Must equal the attempt and protected policy |
| `role_id`, `role_version`, `role_digest` | Must equal the attempt and protected role |
| `context_manifest_id`, `context_manifest_version`, `context_digest` | Recomputed against current assigned bytes |
| `task_digest` | Must equal the attempt's sealed task identity |
| `test_catalog_version`, `test_catalog_digest` | Exact immutable catalog binding |
| `test_plan_digest`, `test_ids` | Recomputed prerequisite-complete ordered plan |
| `worker_lab_commit` | Exact clean Worker Lab implementation commit |
| `worker_lab_contract_version` | Exact supported client contract version |
| `framework_commit` | Exact clean framework commit containing the adapter |
| `framework_contract_version` | Exact supported adapter contract version |
| `workspace_receipt_digest` | Recomputed strict Phase 2 receipt identity |
| `workspace_root_digest`, `workspace_path_digest` | Must equal receipt and current canonical paths |
| `starting_commit` | Must equal attempt, exercise, context, receipt, and current workspace HEAD |
| `sandbox_mode` | Derived from operation and must equal the exercise |
| `runtime_profile_id` | Approved framework-owned profile, initially one Terra-medium profile |
| `model`, `reasoning_effort`, `timeout_seconds` | Resolved fixed profile values; framework recomputes them |
| `readable_paths` | Exact normalized context/authority paths and digests |
| `writable_paths` | Empty for proposal; exact exercise paths for code task |
| `prompt_digest` | Returned by deterministic non-executing adapter preparation and then sealed |
| `authorized_by` | Exact trusted-controller authority label, never a worker identity |
| `authorized_at` | Canonical UTC timestamp |
| `state` | Strict invocation state described below |
| `result_digest` | Null until a strict result is accepted |

Worker Lab persists all fields. The framework receives the full envelope, independently recomputes
framework-controlled values, workspace Git identity, path boundaries, prompt digest, and runtime
profile, and returns those observations. Worker Lab then independently recomputes protected record,
receipt, workspace, changed-path, candidate, catalog, and result identities.

Missing fields, unknown fields, unsupported versions, stale commits, dirty authority repositories,
digest mismatches, and unsupported operations fail closed.

## Runtime profile

Worker Lab does not control raw Codex options. Phase 3 begins with one framework-owned profile whose
resolved values are persisted in the invocation. The profile uses:

- the framework's audited Codex version;
- `gpt-5.6-terra`;
- medium reasoning;
- a finite framework-approved timeout; and
- sandbox derived solely from the operation.

Changing the audited Codex version, model, reasoning effort, timeout policy, Windows sandbox setting,
authentication policy, or environment sanitization is a separate framework security change. Adding
a runtime profile requires trusted review and a new supported contract version when compatibility is
not exact.

## Invocation preparation and prompt identity

The adapter exposes a non-executing preparation operation in Batch 3B. It strictly validates the
envelope, constructs the deterministic prompt from structured fields, and returns the prompt digest
and resolved runtime identity without invoking Codex. Worker Lab seals those values before execution.

The prompt contains only the exact synthetic objective, authority/context paths and digests, allowed
or writable paths, acceptance criteria, invariants, test-plan identity, and prohibitions. It does not
contain credentials, usable absolute Lab-state paths, arbitrary shell commands, or authority not
already present in protected records.

The execution operation must reconstruct the same prompt. A different digest fails before Codex
starts.

## Lifecycle and invocation-state custody

The existing attempt lifecycle remains authoritative. Phase 3 adds invocation states, not new attempt
states:

```text
PREPARED -> AUTHORIZED -> DISPATCHING -> COMPLETED
                         \-> UNCERTAIN -> ABORTED
              \-> REJECTED
```

`REJECTED` and `ABORTED` are terminal invocation states. The exact transition set is made strict in
Batch 3B.

### Before `READY -> RUNNING`

Worker Lab must, in order:

1. reload and cross-validate the attempt, exercise, policy, role, context, catalog, and test plan;
2. verify the prepared workspace and receipt without mutation;
3. verify Worker Lab and framework repository commits and clean tracked state;
4. prove the operation, role, sandbox, paths, and runtime profile are mutually consistent;
5. receive the adapter's non-executing prepared identity and prompt digest;
6. persist the exact `PREPARED` invocation;
7. receive trusted-controller authorization for that digest;
8. persist `AUTHORIZED`; and
9. run the framework's version/auth/environment preflight without starting a worker.

A failure before `AUTHORIZED` leaves the attempt `READY` and grants no execution permission. A
failure after authorization is retained as the first failed boundary; the workspace is safely
disposed and the attempt becomes `ABORTED`. Phase 3 provides no automatic retry. A new linked attempt
is required for another authorized run.

### Dispatch ordering

Worker Lab transitions `READY -> RUNNING` and sets `runtime_identity` to the invocation digest before
the framework process can execute Codex. It then persists `DISPATCHING` before process creation.

This ordering is intentionally conservative:

- `READY` plus `PREPARED` means no authorization existed;
- `READY` plus `AUTHORIZED` means execution never received lifecycle authority;
- `RUNNING` plus `AUTHORIZED` means the transition occurred but dispatch was never permitted;
- `RUNNING` plus `DISPATCHING` and no terminal result is uncertain, even if process creation may not
  have completed; and
- `RUNNING` plus a verified terminal result can advance normally.

No state claims that a process started unless durable evidence proves it. The unavoidable gap between
persisting `DISPATCHING` and process creation is treated as uncertain rather than guessed away.

### Interruption recovery

An uncertain invocation is never rerun. Worker Lab remains `RUNNING` while the adapter or Codex
process may still be alive and does not verify, mutate, quarantine, or delete the workspace.

The future adapter must expose durable process identity sufficient for the trusted controller to
determine that the adapter and its worker child are no longer active. On Windows, implementation must
either provide a tested kill-on-parent-close containment mechanism or retain exact process identity
and require trusted termination verification. This is a trusted security decision in Batch 3C.

Only after process absence and workspace state are independently established may Worker Lab record
the first failure, dispose of the receipt-bound workspace, and transition `RUNNING -> ABORTED` with an
actual cleanup outcome. Ambiguity remains visible; it is not converted to success or retried.

### Successful proposal

A read-only result can advance `RUNNING -> CANDIDATE` only when:

- the strict result binds the invocation and all input identities;
- the repository HEAD, index, worktree, Git configuration, remotes, alternate-object configuration,
  receipt, attempt bytes, and complete workspace byte snapshot are unchanged;
- changed paths are exactly empty;
- the proposal content is valid bounded UTF-8 text and its content digest is recomputed; and
- `candidate_digest` is the digest of the strict proposal result, not worker prose alone.

### Successful code task

A workspace-write result can advance `RUNNING -> CANDIDATE` only when:

- HEAD remains the detached starting commit;
- Git configuration, index authority, remotes, alternates, receipt, and protected paths are intact;
- observed changed paths exactly equal the sorted exercise writable paths required by the task;
- Worker Lab independently computes the candidate content digest from those exact paths;
- the framework-reported digest matches;
- diff integrity and every required focused/full validation stage pass in sealed test-plan order; and
- the strict result digest is persisted before the attempt transition.

Phase 3 does not commit the candidate.

### Failure-state mapping

Runtime, contract, boundary, timeout, malformed-result, interruption, or validation failures use
`ABORTED` after safe containment and cleanup. Existing attempt `FAILED` remains reserved for a
candidate that reached `EVALUATING` and failed evaluation; it is not a runtime-error bucket.

## Strict result contract

Batch 3B adds `worker-lab-framework-result:v1`. It contains:

- schema, result, invocation, attempt, operation, request, prompt, framework, runtime, workspace,
  starting-commit, and test-plan identities;
- process start/end times and durable process identity evidence;
- base and observed HEAD;
- exact normalized changed paths;
- workspace state and candidate content digest;
- proposal content digest for read-only operation;
- ordered validation stage outcomes;
- worker outcome with normalized failure code;
- first-failure boundary, expected/observed summary, containment status, and retryability fixed to
  false for Phase 3;
- worker output digest and bounded content reference when retained; and
- a canonical result digest.

The result uses strict fields and enums. Worker stdout, stderr, and prose cannot directly establish a
pass, validation outcome, candidate identity, state transition, or publication readiness.

### Current framework contract gaps

| Existing contract | Useful precedent | Insufficient for Worker Lab |
|---|---|---|
| `worker-context:v1` | Context and repository identity | Defaults to a consumer-specific profile and lacks Lab attempt/receipt/test-plan identity |
| `ContextProbeResult` | Read-only sandbox and response | No invocation/runtime/framework/result identity or complete non-mutation evidence |
| `code-task:v1` | Exact paths and validation commands | No strict failure result, process evidence, candidate content digest, or Lab lifecycle binding |
| `worker-task:v1` | Strict task fields and assertions | Limited to the commissioning fixture |
| `worker-result:v1` | Boundary/validation/failure structure | No invocation or receipt identity; permits repair attempts and repository handoff semantics excluded here |

These contracts remain unchanged. The adapter translates from a new project-agnostic contract and
may reuse their internal implementation only where all Phase 3 invariants still hold.

## Stable failure categories

| First boundary | Stable category | Required outcome |
|---|---|---|
| Protected record, version, digest, framework, or context mismatch | `INTEGRATION_IDENTITY_INVALID` | No execution; reject/abort according to authorization point |
| Receipt, path, workspace, or starting-commit verification | `INTEGRATION_WORKSPACE_INVALID` | No execution; retain exact mismatch |
| API-key variable present | `API_KEY_AUTH_FORBIDDEN` | No execution; sanitized failure evidence only |
| ChatGPT login absent or Codex version differs | `CHATGPT_AUTH_REQUIRED` or `CODEX_VERSION_INVALID` | No execution |
| Sandbox, runtime profile, or credential environment mismatch | `INTEGRATION_RUNTIME_FORBIDDEN` | No execution |
| Adapter/Codex unavailable or nonzero | `INTEGRATION_EXECUTION_FAILED` | Stop; contain; no retry |
| Timeout | `CODEX_TIMEOUT` | Stop; prove process absence before cleanup |
| Missing, unknown, oversized, non-UTF-8, or malformed result | `INTEGRATION_RESULT_INVALID` | Treat output as untrusted; no candidate |
| HEAD, index, config, remote, alternate, receipt, or protected mutation | `INTEGRATION_BOUNDARY_FAILED` | No candidate; preserve evidence then contain |
| Unexpected changed paths | `INTEGRATION_SCOPE_FAILED` | No candidate |
| Focused or full validation failure | Existing test ID plus `INTEGRATION_VALIDATION_FAILED` | Stop at first required failure |
| Controller interruption or incomplete durable result | `INTEGRATION_OUTCOME_UNCERTAIN` | Never rerun; wait for process-absence proof |

Worker Lab maps these to its existing failure classifications (`contract`, `context`, `framework`,
`environment`, `test`, or `controller-judgment`) without losing the exact framework code.

## Evidence retention

Invocation and strict result records are durable. Workspace receipts remain ephemeral. Candidate or
proposal content evidence is content-addressed and bound to attempt, invocation, base commit,
environment, test catalog, and test plan.

Initial synthetic exercises may retain bounded proposal text and worker response content only after
UTF-8, size, and digest validation. Raw stderr, environment dumps, credentials, login output, absolute
user paths, and unrestricted prompts are not retained. The final size limits and redaction policy are
reserved for trusted review before Batch 3C.

## Test binding and cadence

Phase 3 creates immutable `worker-lab-v3`; it does not add `tests/test_profiles.yml` or mutate
`worker-lab-v2`. The new catalog binds new adapter/invocation paths, adds T016 evidence substitution
coverage and T022 exact integration-candidate verification, and defines:

- `FRAMEWORK_ADAPTER_CHANGE:v1` for strict schemas and non-executing adapter/client seams;
- `READ_ONLY_INVOCATION:v1` for auth/runtime mapping, complete non-mutation, interruption, and strict
  proposal result;
- `CODE_INVOCATION:v1` for exact writable paths, candidate identity, validations, and containment;
- `PHASE3_MILESTONE:v1` for the full Worker Lab and framework gates plus T021/T022.

Planned coverage:

| Boundary | Permanent tests |
|---|---|
| Record/schema/digest | T003, T004, T005, T006, T011 |
| Lifecycle and restart | T007, T009, T017, T019 |
| Paths/workspace isolation | T002, T008, T015, T017 |
| Auth, credential, sandbox, runtime | T015, T018, T019 |
| Result/evidence substitution | T006, T016, T019 |
| CLI contract when added | T012 |
| Full phase candidate | T020, T021, T022 after all prerequisites |

Development runs the smallest applicable profile, prerequisite-first and cheapest-first. The complete
Worker Lab suite, complete affected framework suite, cross-repository acceptance, backup/restore,
and rollback drill run once at the Phase 3 milestone. Exact passing evidence is not repeated when
identity inputs are unchanged.

## Delivery batches

### Batch 3B — Contracts and non-executing seam

Entry: this specification approved. Add strict invocation/result records, invocation storage and
state validation, `worker-lab-v3`, a Worker Lab client, and a framework adapter preparation mode.
Use injected/fake process execution only. No Codex invocation and no attempt reaches `RUNNING`.

Exit: unknown fields and all identity mismatches fail closed; deterministic prompt/runtime identity
round-trips across repositories; focused adapter/schema/catalog tests pass.

### Batch 3C — Read-only proposal

Entry: 3B integrated and exact framework/runtime checkpoints approved. Implement one synthetic
read-only proposal, `READY -> RUNNING -> CANDIDATE`, complete Git/filesystem non-mutation proof,
process/interruption evidence, failure containment, and CLI acceptance.

Exit: one authorized synthetic proposal succeeds; every injected auth, sandbox, mutation, malformed
result, timeout, and interruption boundary fails safely without rerun.

### Batch 3D — Workspace-write code task

Entry: 3C milestone candidate accepted. Use a fresh synthetic workspace and one exact-path task.
Implement independent candidate digest, exact changed/protected path enforcement, sealed focused/full
validation, and `RUNNING -> CANDIDATE`. No commit or publication.

Exit: one bounded code candidate succeeds and all scope, Git, test, result, and cleanup failures are
contained with exact evidence.

### Batch 3E — Recovery and milestone

Entry: 3D accepted. Complete restart recovery, restored-attempt behavior, end-to-end CLI acceptance,
full catalog validation, external durable backup/restore, independent Git rollback for both changed
repositories, current documentation, and a named milestone.

Exit: every Phase 3 completion condition passes and trusted review accepts the exact integration.

## Explicit exclusions

No external product repository, real curriculum, worker commit, GitHub/remote access, publisher,
approval packet, evaluator implementation, playbook promotion, graduation, automatic retry/repair,
queue, concurrency, task graph, daemon, network service, plugin system, dashboard, or generalized
permission service belongs in Phase 3.

`workspace.py` modularization, CLI cleanup, and shared test-helper extraction are maintenance work,
not implicit parts of the integration. They require separate bounded review and must not be mixed with
security-sensitive adapter behavior.
