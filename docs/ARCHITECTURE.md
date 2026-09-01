# Architecture

## System model

Autonomous Coding Lab is one local-first system composed of three peers with different trust levels:

```text
human scope and approvals
          |
          v
Worker Lab control plane
policy -> role -> exercise -> attempt -> evidence -> acceptance
          |
          | authorized, versioned invocation contract
          v
Autonomous Worker Framework
identity -> credentials -> sandbox -> subprocess -> repository boundary -> result
          |
          v
isolated disposable target/workspace

Local Model Bench -----------------------------------+
prompt/model evidence -> human or Worker Lab review -+
```

Local Model Bench informs model and prompt choices. It is deliberately outside the execution chain.

## Component responsibilities

### Worker Lab: control plane

Worker Lab owns:

- curricula and immutable exercise definitions;
- policy and role limits;
- task authority and requirement identity;
- attempts, invocations, lifecycle, retries, and failures;
- workspace receipts and durable state;
- evaluator catalogs, evidence identity, acceptance, and graduation.

Policy, role, curriculum, and evaluator definitions are authority-bearing runtime records. Treating them as ordinary editable preferences would let a worker redefine its own boundaries.

Worker Lab's application service is the client boundary above those records and policies. The CLI uses it now, and the future GUI must use the same service rather than reading or writing storage directly. It exposes strict, versioned, non-mutating health, installation-status, list, and show DTOs; operation-result DTOs for attempt/workspace lifecycle and guarded invocation decisions; backup-result DTOs for create, verify, and restore; and a recovery-result DTO binding the terminal attempt, invocation, custody, and unchanged-workspace evidence. Operation-result v2 carries the immutable invocation identity required for exact authorization, rejection, and controller-bound pre-dispatch cancellation. Later methods remain responsible for general dispatch, complete timelines, and candidate review.

### Autonomous Worker Framework: execution and security

The framework owns:

- Codex authentication and forbidden-key rejection;
- removal of GitHub credential-like variables;
- allowed sandbox modes and Windows process custody;
- subprocess timeouts and bounded output capture;
- target-repository identity, path, and cleanliness enforcement;
- trusted validation transport;
- candidate publication and handoff mechanisms controlled outside the worker.

The framework must not invent tasks or approve its own results. Worker Lab must not copy or weaken framework security logic.

### Local Model Bench: advisory peer

Local Model Bench owns:

- deterministic model and case ordering;
- Ollama, managed llama.cpp/GGUF, and OpenAI-compatible provider adapters;
- isolated or explicitly preserved prompt context;
- per-case checkpointing, resumability, and error capture;
- raw response, token, timing, throughput, and model metadata;
- deterministic contract evaluation and reviewable reports.

Its outputs are observations, not task contracts. A planner response becomes actionable only after a trusted controller validates it and Worker Lab records the authorized form.

## Root integration layer

The repository root supplies installation identity, shared integration configuration, current documentation, and structural inventory tools. It does not own worker policy or execution authority.

Current integration files include:

- `config/monorepo-identity.json` — accepted source/import and component-scope identity evidence;
- `config/installation-manifest.json` — strict installed-file, runtime, and disabled-activation identity candidate;
- `migration/inventory/` — source/current structure and connection evidence;
- `tools/` — deterministic inventory, query, and repair-plan utilities.

## Identity model

Four identities must not be conflated:

| Identity | Meaning |
|---|---|
| Source identity | Which original component commit/tree was imported |
| Installation identity | Which installed ACL files and entrypoints are being invoked now |
| Target repository identity | Which clean repository/commit a task may inspect or modify |
| Candidate identity | Which exact result bytes/commit were validated for possible acceptance |

Development Git state helps audit changes, but an installed runtime cannot safely assume every component directory is a standalone Git repository. Installation-manifest v2 therefore preserves source commit/tree provenance separately from SHA-256 installed-file sets. Worker Lab verifies its production tree and the expected framework/runtime identities; the framework adapter independently verifies its entrypoint and adjacent Codex runtime dependency before loading that dependency. Both sides enforce the manifest's disabled/deferred activation policy before preflight or execution. The candidate remains unaccepted until the Phase 1 clean-tree and remote gates are satisfied.

## Trust and data flow

1. A human or trusted controller supplies a scope.
2. A planner may propose decomposition, but the proposal remains untrusted.
3. Worker Lab resolves the policy, role, context, evaluator catalog, task digest, and target identity.
4. Only an authorized attempt may produce an invocation contract.
5. The framework rechecks runtime and repository boundaries before executing.
6. Results return as structured evidence; they do not self-approve.
7. Trusted evaluation determines acceptance. Publication and merge remain separate actions.

Every boundary fails closed. Availability of a provider, model, executable, configuration entry, or prior successful run never skips a later authority check.
