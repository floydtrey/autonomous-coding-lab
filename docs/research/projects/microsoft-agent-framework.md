# Microsoft Agent Framework — Task 21 Deep Research

**Research date:** 2026-09-06 / 2026-09-07  
**Canonical upstream:** https://github.com/microsoft/agent-framework  
**Inspected upstream revision:** `afdc0db172d57edd50976d6f15168898f2284916`  
**Latest Python umbrella release observed:** `python-1.17.0` (published 2026-09-03)  
**Research status:** deep research complete; no adoption, dependency, provider, model, or architecture winner selected.

## Scope

This task investigates Microsoft Agent Framework (MAF) as a current agent/runtime/orchestration reference for ACL and the future Vera controller. It covers:

- agent/runtime and session identity;
- tool calling, approvals, middleware, and policy authority;
- graph workflows, supersteps, shared state, checkpointing, resume, and recovery;
- distributed durable execution and the boundary between standard workflow checkpoints and Durable Task;
- concurrency, cancellation, pending work, and replay/settlement semantics;
- local model/provider portability, especially Ollama;
- shell/code execution and sandbox boundaries;
- MCP and A2A integration;
- hosting/auth/isolation ownership;
- observability and evaluation;
- current security/reliability failure evidence;
- the AutoGen/Semantic Kernel convergence only where it clarifies the current design;
- reusable mechanisms and ACL/Vera candidate invariants.

Google ADK is explicitly out of scope for Task 21.

## Executive assessment

Microsoft Agent Framework is a high-value ACL/Vera reference because it now combines several mechanisms previously studied separately: a provider-agnostic agent abstraction, lightweight durable session state, a typed function/tool loop, explicit human approval state, graph workflows with Pregel-like supersteps, checkpoint lineage, middleware/interception seams, local/cloud model providers, MCP/A2A integration, OpenTelemetry, an evaluation API, a coding-oriented Agent Harness, and a separate first-party Durable Task extension for distributed execution.

The strongest architectural lesson is not that ACL should adopt MAF wholesale. It is that **several kinds of state and authority that appear similar at the API level are intentionally separate**:

1. framework-local `AgentSession` state;
2. provider/service continuation identity such as `service_session_id`;
3. workflow committed state and pending superstep writes;
4. standard workflow checkpoints;
5. distributed durable orchestration state;
6. model-visible transcript/history;
7. pending tool/approval state;
8. host/application authentication and authorization state;
9. local execution/sandbox authority;
10. external effects and delivery/stream settlement.

Current failures show why these distinctions matter. A failed workflow superstep can currently leave pending state that is committed by a later run (#7859). Foundry-hosted long-running workflows have an open checkpoint/response-stream durability gap (#7809). .NET has an open request for explicit closure of dangling tool/approval lifecycles after cancellation/restart (#7872). An experimental Python policy-enforcement middleware can retain abandoned pending approvals without bound (#7890). By contrast, a prior checkpoint aliasing bug (#7683) has been fixed on current `main`, showing active hardening around state isolation.

For ACL, MAF is especially valuable as a reference for:

- logical occurrence identity for approvals versus provider `call_id`;
- graph-signature-checked checkpoint lineage;
- separation of committed and pending superstep state;
- read/copy isolation for session/checkpoint snapshots;
- host-owned auth/isolation above protocol-derived IDs;
- tool policy/approval separated from real sandbox/process authority;
- explicit experimental/stable feature maturity labels;
- provider-specific capability and retry behavior rather than assuming generic parity;
- a separate distributed durability layer rather than pretending ordinary checkpoints solve multi-host recovery;
- local deterministic evaluation plus trajectory/model-based evaluation under one provider-agnostic API.

MAF still does **not** replace ACL’s need for an ACL-owned project/task/run/effect identity model, external-effect ledger and reconciliation, protected independent verifier, least-privilege process/credential boundary, distributed writer fencing, workspace checkpoint ownership, or Vera’s future epistemic memory governance.

---

# 1. Project identity, maturity, and AutoGen/Semantic Kernel convergence

## 1.1 Current project identity

Observed current upstream:

- repository: `microsoft/agent-framework`;
- current `main` inspected at `afdc0db172d57edd50976d6f15168898f2284916`;
- Python umbrella release observed: `1.17.0` on 2026-09-03;
- project is active and not archived;
- Python and .NET are the primary released language families in the monorepo; Go exists in a separate Microsoft repository.

Primary sources:

- https://github.com/microsoft/agent-framework
- https://github.com/microsoft/agent-framework/releases/tag/python-1.17.0
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/README.md

## 1.2 GA status is real, but package/feature maturity is mixed

Microsoft announced MAF 1.0 GA in April 2026 as the production-ready convergence of AutoGen and Semantic Kernel. Current package status is more granular than the umbrella GA label.

Current Python package status at the inspected revision classifies examples such as:

- `agent-framework` — released;
- `agent-framework-core` — released;
- `agent-framework-openai` — released;
- `agent-framework-orchestrations` — released;
- `agent-framework-foundry` — released;
- `agent-framework-a2a` — beta;
- `agent-framework-ollama` — beta;
- `agent-framework-tools` — beta;
- hosting protocol packages — often alpha;
- the Harness, Evals, Agent Hooks, FIDES, functional workflows, session store, and MCP long-running tasks — feature-level experimental surfaces even when hosted in a released package.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/PACKAGE_STATUS.md

ACL implication: dependency identity must include **feature/package maturity**, not only framework version. “MAF 1.x” is too coarse for qualification.

## 1.3 Convergence is a supported successor event, not evidence that prior ideas were discarded

Microsoft’s current materials explicitly describe MAF as the convergence of:

- Semantic Kernel’s enterprise/provider/runtime foundations; and
- AutoGen’s multi-agent/orchestration experimentation.

Current migration guides exist for both AutoGen and Semantic Kernel.

AutoGen migration material notes that multi-agent patterns move toward MAF’s data-flow/workflow model rather than preserving every event-driven abstraction unchanged. Semantic Kernel migration maps prior agent/thread/tool/provider concepts into the new common agent/session model.

Primary sources:

- https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/
- https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/
- https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-semantic-kernel/

This extends Task 4’s prior finding that AutoGen was heavily redesigned and then succeeded by Agent Framework. It does not justify saying “multi-agent failed.” Instead, it shows production pressure favored clearer runtime/state/provider/workflow ownership.

---

# 2. Agent/runtime architecture and identity

## 2.1 `AgentSession` is intentionally lightweight

Current Python `AgentSession` is a lightweight conversation/session state container. Provider instances belong to the agent/client layer rather than being serialized into the session.

The session subsystem distinguishes:

- session-local state;
- history-provider state;
- service/provider continuation state;
- provider-owned live objects;
- file/in-memory session snapshots.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_sessions.py

## 2.2 Framework session identity is not necessarily provider conversation identity

Current provider implementations expose a useful boundary: a framework-local session can carry provider-specific `service_session_id` state. For example, current Claude integration documentation in source explicitly notes that the isolation boundary for an injected Claude client is the Claude conversation identified by `service_session_id`, not merely the local framework `session_id`.

A2A likewise stores typed durable continuation state in `AgentSession.service_session_id`.

Primary sources:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_sessions.py
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/a2a/AGENTS.md
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/claude/agent_framework_claude/_agent.py

ACL/Vera implication: preserve separate durable IDs for at least:

- principal/user;
- controller/agent;
- conversation/session;
- provider-side conversation/thread;
- ACL project/task/run;
- tool-call occurrence;
- external effect;
- remote job/task.

Do not use one generic `session_id` for all of these.

## 2.3 Session persistence uses explicit serialization boundaries

Current `_sessions.py` includes:

- JSON/MessagePack support;
- explicit state-type registration for restart-safe deserialization;
- stable type IDs;
- fail-fast duplicate/conflicting registrations;
- file-backed session/history stores;
- filename-safe encoding for opaque session IDs, including Windows-reserved names;
- message deduplication identity based on message ID where available or canonicalized role/content fallback.

This is useful for ACL because live provider/client objects should not be serialized into durable task state. Persist stable descriptors and reconstruct runtime handles under current policy.

---

# 3. Workflow execution model

## 3.1 Pregel/Bulk Synchronous Parallel style supersteps

MAF graph workflows use a modified Pregel/Bulk Synchronous Parallel model. A superstep broadly consists of:

1. collect/drain pending messages;
2. route through edges;
3. execute target paths concurrently where possible;
4. synchronize at the superstep boundary;
5. commit shared state;
6. checkpoint if configured;
7. move to the next superstep or converge.

Current Python runner source confirms edge runners operate concurrently while preserving ordered delivery per edge runner.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_workflows/_runner.py

This is valuable for ACL because the workflow model gives deterministic state-transition boundaries without scripting model reasoning itself.

## 3.2 Parallelism is structured but synchronization can still couple branches

Current runner comments describe Python concurrency semantics explicitly:

- different target paths may execute concurrently;
- messages through one edge runner preserve order;
- multiple sources targeting the same executor are serialized in some cases;
- a superstep does not advance until the relevant concurrent work settles.

Therefore fan-out does not imply independent progress of every branch across superstep boundaries. A slow branch may delay the next global step.

ACL implication: if workers have very different durations, avoid forcing unrelated long-lived workers into one global barrier unless that synchronization is semantically required.

---

# 4. Shared state semantics and current failure evidence

## 4.1 Committed versus pending workflow state

Current Python `State` implements explicit staged writes:

- `set()` writes to `_pending`;
- `get()` sees pending first, then committed;
- `commit()` moves pending into committed;
- `discard()` clears pending without committing;
- `get`, `set`, `export_state`, and `import_state` deep-copy values on current `main`.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_workflows/_state.py

This is a useful transaction-like state model at a superstep boundary.

## 4.2 Fixed regression: checkpoint/state aliasing (#7683)

Issue #7683 demonstrated that earlier releases used shallow copies across checkpoint construction/restore and in-memory storage reads. A resumed workflow could silently mutate a checkpoint snapshot by mutating a nested list/dict.

The issue was reproduced across Windows/Linux and multiple Python versions and was closed completed.

Current `main` now deep-copies at the state and in-memory checkpoint boundaries.

Primary sources:

- https://github.com/microsoft/agent-framework/issues/7683
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_workflows/_state.py
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_workflows/_checkpoint.py

ACL regression lesson: a checkpoint must be immutable-by-observation. Reading/restoring it must not create mutable aliases into authoritative stored state.

## 4.3 Current open regression: failed-superstep pending state leaks into later runs (#7859)

Open reproduced issue #7859 identifies a different state lifecycle problem:

1. executor stages a write in `_pending`;
2. executor fails or run is cancelled;
3. runner propagates the failure without calling `State.discard()`;
4. same workflow instance is reused;
5. later successful superstep calls `commit()`;
6. stale write from failed run silently becomes committed.

Current `main` runner at `afdc0db...` still propagates iteration failure/cancellation without an observed `State.discard()` path, while `discard()` appears in the state class/tests.

Primary sources:

- https://github.com/microsoft/agent-framework/issues/7859
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_workflows/_runner.py

ACL invariant candidate:

> Every failed/cancelled transaction/superstep must explicitly retire or roll back pending state before the state owner becomes reusable.

This is distinct from checkpoint correctness.

---

# 5. Standard workflow checkpointing

## 5.1 Checkpoint structure

Current `WorkflowCheckpoint` captures:

- workflow name;
- graph signature hash;
- unique checkpoint ID;
- previous checkpoint ID;
- timestamp;
- messages;
- committed workflow state;
- pending request-info events;
- iteration count;
- metadata;
- format version.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_workflows/_checkpoint.py

## 5.2 Checkpoint lineage is more authoritative than iteration number

The current code explicitly warns that `iteration_count` is not a unique checkpoint identity, particularly in HITL flows. Multiple checkpoints can exist at the same superstep boundary. Ordering follows checkpoint lineage (`previous_checkpoint_id`) and timestamp.

ACL implication: never identify continuation state by a human-readable sequence number alone. Use immutable checkpoint IDs and parent lineage.

## 5.3 Graph compatibility is checked before restore

Restore rejects a checkpoint whose `graph_signature_hash` differs from the active workflow graph.

This is a strong pattern for ACL:

- bind continuation/checkpoint identity to executable workflow/harness definition identity;
- fail closed when the execution definition changed incompatibly;
- do not blindly replay old state under new code.

## 5.4 File checkpoint storage has useful hardening

Current `FileCheckpointStorage`:

- validates checkpoint-derived paths stay inside the storage root;
- writes through a temporary file and `os.replace` for atomic replacement;
- encodes complex objects through a controlled checkpoint encoding layer;
- restricts deserialization to a built-in allowed set plus explicitly registered application types.

This is important because persisted checkpoints are a code/data trust boundary, not passive text.

## 5.5 Checkpoint creation failure does not fail the workflow

Current runner source catches checkpoint creation exceptions, logs a warning, and continues the workflow. The next successful checkpoint keeps lineage from the last successful checkpoint.

This is a deliberate availability choice, but ACL should not inherit it blindly. For unattended ACL work, whether execution may continue after durability failure should be a policy decision by task/effect class.

Possible ACL states:

- `durability_ok`;
- `durability_degraded_but_allowed`;
- `durability_required_pause`;
- `checkpoint_failed_unsettled`.

---

# 6. Resume semantics and current gaps

## 6.1 Restore validates and replaces workflow state

Current restore flow:

- loads checkpoint;
- validates graph signature;
- clears current state;
- imports checkpoint state;
- restores executor state;
- applies checkpoint messages/events;
- restores checkpoint iteration/parent lineage.

This is preferable to merging restored state into arbitrary current state.

## 6.2 Current API gap: atomic restore plus new input (#7863)

Open issue #7863 documents that Python applications currently need separate workflow calls to:

1. hydrate/restore a checkpoint;
2. submit new input and continue.

The requested design is one atomic lifecycle that validates/restores first, then applies new input.

Primary source:

- https://github.com/microsoft/agent-framework/issues/7863

ACL implication: a resume API should be a first-class transition, not an ad hoc sequence of “load, mutate, run” calls exposed to clients.

## 6.3 Current hosting recovery gap: checkpoint versus delivered response (#7809)

Open issue #7809 records two Foundry-hosted long-running-agent recovery gaps:

- a workflow that emits no output until the end may not produce a host response checkpoint useful for recovery and may restart from the beginning;
- workflow checkpoint persistence can advance while a response update is still not durably associated with the client-visible response stream, creating a window where the workflow will not rerun a superstep yet the client permanently misses an output.

Primary source:

- https://github.com/microsoft/agent-framework/issues/7809

This is a strong ACL/Vera lesson:

> execution-state durability and output/evidence-delivery durability are separate settlement planes.

A task cannot be declared safely resumed merely because internal state is checkpointed if required outputs/effects/evidence have not settled.

---

# 7. Distributed durable execution is a separate first-party layer

## 7.1 Standard checkpoints are explicitly not Durable Task

Microsoft’s current Durable Extension documentation explicitly distinguishes:

- **standard workflow checkpoint storage** — resumes a workflow within Agent Framework runtime semantics;
- **Durable Extension** — runs agents/workflows on Durable Task infrastructure across distributed workers/process restarts.

Primary source:

- https://learn.microsoft.com/en-us/agent-framework/integrations/durable-extension

This explicit distinction is one of Task 21’s strongest architectural findings.

## 7.2 Durable Extension capabilities

Current official docs describe:

- persistent agent sessions;
- durable entities per agent session;
- checkpointed workflow/orchestration progress;
- restart/failure recovery;
- distributed stateless workers;
- human waits lasting hours/days/weeks without occupied compute;
- durable workflow graphs;
- reliable streaming when paired with a broker such as Redis;
- session TTL/cleanup;
- self-hosted or Azure Functions modes.

The docs state completed executor/agent steps are not repeated after a process restart/failure under the durable workflow model.

Important boundary: this is orchestration replay behavior. It is **not sufficient evidence that arbitrary external effects are exactly once** unless those effect calls themselves use appropriate durable activity/idempotency/reconciliation semantics.

ACL should preserve:

- durable task/workflow progress;
- external effect identity/settlement;
- output delivery settlement;
- workspace state;

as separate evidence domains.

---

# 8. Function/tool loop and occurrence identity

## 8.1 The function loop is explicitly treated as high-risk state machinery

Current proposed cross-package function-loop contract documents risks including:

- duplicate side effects;
- orphaned calls/results;
- invalid provider histories;
- invisible streamed results;
- stale approval authority;
- loops that never terminate;
- provider-specific reasoning/function-call grouping corruption.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/docs/specs/004-python-function-calling-loop.md

Although the spec document is marked proposed, it describes current implementation/test ownership and is useful design evidence. Treat normative maturity separately from source behavior.

## 8.2 Provider `call_id` versus framework occurrence ID

A particularly valuable distinction in the function-loop design:

- provider/service `call_id` is a correlation identifier and may be reused over time;
- `Content.id` on a function call is the framework identity for one locally actionable occurrence.

Approval requests for new local calls bind to the occurrence ID. Matching a nested provider `call_id` is not accepted as a generic occurrence identity alias in the occurrence-aware path.

ACL implication: external/provider IDs may be useful evidence, but ACL must own a stable logical action/effect occurrence identity.

## 8.3 Pending approval state is itself trusted state

The function-loop spec explicitly states pending approval state is a trusted session-state boundary and that hosts must authorize/tenant-scope the session store. Consume-on-bind protects one session state, but the spec does not claim durable exactly-once behavior across crashes/concurrent workers without external coordination.

This maps directly to ACL mobile/remote approvals.

---

# 9. ToolApprovalMiddleware

## 9.1 Standing approvals can be scoped by exact arguments

Current Python `ToolApprovalMiddleware` supports session-backed approval rules by:

- tool name;
- optional exact canonicalized argument set;
- hosted `server_label` boundary.

Argument serialization uses sorted JSON for exact matching, and a no-argument rule is distinguished from a tool-wide wildcard.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_harness/_tool_approval.py

Useful ACL pattern: “approve this exact invocation pattern” is safer than broad “approve everything named X.”

## 9.2 Built-in Harness/Skills auto-approval has a documented name-collision weakness

Current samples/documentation explicitly warn that some built-in auto-approval helpers match local tools **solely by tool name**. A different registered tool using the same reserved name can also become auto-approved, bypassing the intended human approval boundary.

Examples include read-only file tools and skill tools.

Primary sources:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/samples/02-agents/skills/skills_auto_approval/README.md
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/samples/02-agents/harness/build_your_own_claw/README.md

ACL invariant candidate:

> A privileged tool identity must include trusted origin/provider/extension identity plus tool/schema identity, and when authority depends on parameters, normalized parameter identity. Tool display name alone is never an authorization principal.

---

# 10. Agent Hooks: protected interception and verdict-before-durability

## 10.1 Python shipped experimental Agent Hooks

Current Python core includes experimental `AGENT_HOOKS` support implementing the AGENT-HOOKS-0.1 interception contract.

Current package status describes eight interception points and an experimental middleware bundle.

Primary sources:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/PACKAGE_STATUS.md
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_agent_hooks.py

## 10.2 High-value enforcement properties

The design emphasizes:

- fail-closed interceptor errors/timeouts;
- allow/deny/transform verdicts;
- transformed output written back;
- streaming buffered until output verdict;
- persistence gated behind verdicts so denied output does not become durable;
- pre/post model and pre/post tool interception in addition to agent input/output lifecycle.

These are highly relevant to ACL’s protected verifier/policy layer.

## 10.3 .NET structural-enforcement design is useful but maturity must be stated accurately

Current source contains a .NET Agent Hooks package, while ADR `0035-dotnet-agent-hooks-enforcement.md` remains `status: proposed` and describes the package as alpha/experimental.

The design intentionally makes enforcement composition indivisible through one factory rather than exposing bypassable middleware pieces. It rejects pipeline-replacement configurations that would place tool execution below enforcement.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/docs/decisions/0035-dotnet-agent-hooks-enforcement.md

Most important ACL pattern:

> enforcement that constrains a worker should be structurally outside the worker’s replaceable pipeline, not merely a convention the same worker/runtime may bypass.

## 10.4 Hooks are explicitly not a security sandbox

The ADR states the contract is cooperative and not an in-process adversarial security boundary. This matters: interception/policy and OS/process isolation remain separate controls.

---

# 11. Experimental FIDES policy enforcement and current lifecycle failure

## 11.1 FIDES is experimental

Current package status marks FIDES security labeling, policy enforcement, content indirection, and secure MCP surfaces as experimental.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/PACKAGE_STATUS.md

## 11.2 Current reproduced issue #7890: abandoned policy approvals can accumulate indefinitely

Open reproduced issue #7890 shows `PolicyEnforcementFunctionMiddleware` storing pending approval records in `_pending_policy_approvals` keyed by call ID. Entries are removed when successfully consumed, but the issue demonstrates no general TTL/bound/cleanup for approvals that are abandoned/ignored/unconsumed.

Current `main` search still shows the map and consume-on-success logic.

Primary sources:

- https://github.com/microsoft/agent-framework/issues/7890
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/security.py

ACL invariant candidate:

Every pending approval/effect/remote-job record needs explicit lifecycle states and retention:

- pending;
- approved/rejected;
- expired;
- abandoned;
- cancelled;
- consumed;
- reconciled;
- garbage-collectable.

Correct approval binding alone is insufficient.

---

# 12. Dangling tool work and cancellation

## 12.1 Current open .NET issue #7872

Open reproduced #7872 argues the framework currently lacks one public closure contract for dangling tool/approval work after user cancellation/process interruption/restore.

The issue covers lifecycle pairs such as:

- function call;
- approval request;
- approval response;
- function result.

It requests a way to enumerate/drain/close pending work before accepting a new normal user turn.

Primary source:

- https://github.com/microsoft/agent-framework/issues/7872

The exact proposal is not a shipped guarantee, but the reproduced failure class is valuable.

ACL implication:

> after cancellation/restart, unresolved effect-bearing work must be reconciled before a new independent turn/run can assume a clean state.

## 12.2 Async cancellation is not external-effect settlement

Current workflow runner propagates asyncio cancellation into the active iteration task to reduce orphaned coroutine work. MCP task wrappers also contain explicit remote-cancellation behavior. These are useful, but none prove arbitrary subprocess/network/database effects have settled.

ACL should track separately:

- cancel requested;
- coroutine stopped;
- process tree stopped;
- remote task cancelled/terminal;
- effect reconciled;
- state discarded/rolled back;
- output stream settled.

---

# 13. Agent Harness and execution boundaries

## 13.1 Harness is a relevant coding-agent reference, but experimental

Current MAF Harness surfaces include planning/execution modes, file access, todo/planning, compaction, looping, background agents, approvals, memory/context helpers, shell/tool execution, and observability.

Package status marks important Harness features experimental; shell tooling is separately packaged.

Primary sources:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/PACKAGE_STATUS.md
- https://github.com/microsoft/agent-framework/tree/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_harness

## 13.2 ShellPolicy explicitly rejects the idea that regex command filtering is security

Current `ShellPolicy` documentation is unusually explicit:

- regex allow/deny is a UX pre-filter;
- it is “not a security boundary; not even a security feature”;
- shell expansion, interpreters, encoding, absolute paths, variable substitution, etc. trivially bypass string-pattern assumptions;
- no default deny patterns are shipped to avoid a false impression of security;
- default policy permits every non-empty command;
- actual safety relies on approval and trusted/sandboxed execution environment.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/tools/agent_framework_tools/shell/_policy.py

This strongly corroborates prior Cline/Goose/Gemini findings: shell command classification cannot substitute for process/filesystem/network/credential isolation.

## 13.3 Local CodeAct defense-in-depth versus containment

Current .NET LocalCodeAct README explicitly says it runs generated Python locally and is **not** a security sandbox.

It provides useful defense-in-depth:

- AST validation;
- subprocess rather than in-process execution;
- no shell invocation;
- explicit Python path;
- no host environment inheritance by default;
- explicit environment projection;
- time/output/result limits;
- typed host-tool gating;
- file-mount controls.

But it does not claim protection from allowed malicious Python/network/exfiltration/resource/log abuse. An external sandbox remains required.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/dotnet/src/Microsoft.Agents.AI.LocalCodeAct/README.md

This is a useful ACL execution-profile reference even if LocalCodeAct itself is not adopted.

## 13.4 Hyperlight/Docker are separate sandbox tiers

MAF also has Docker shell and Hyperlight CodeAct paths. Package status currently marks Hyperlight beta. Their existence reinforces the architectural separation:

- model tool interface;
- approval/policy;
- execution adapter;
- realized OS/VM/container authority.

ACL should record realized sandbox backend/profile, not merely a `sandboxed=true` flag.

---

# 14. Local model/provider portability

## 14.1 Native Ollama plus OpenAI-compatible path

Current MAF documentation supports local Ollama through:

- native Python `OllamaChatClient` (`agent-framework-ollama`);
- OpenAI-compatible endpoint path;
- .NET `OllamaSharp` / `IChatClient` path.

Official docs explicitly state actual tool capability depends on the selected model.

Primary sources:

- https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/model-providers/ollama
- https://github.com/microsoft/agent-framework/tree/afdc0db172d57edd50976d6f15168898f2284916/python/packages/ollama

This is relevant to ACL’s 32K local-worker plan, but support must be qualified per exact model/runtime/adapter/settings tuple.

## 14.2 Provider feature parity is intentionally not universal

Current provider tables show materially different support for tools, hosted tools, search, code execution, etc. “Agent Framework provider” is a common API, not a guarantee of identical backend behavior.

ACL should maintain a verified deployment profile containing at least:

- MAF version/commit;
- provider package/version;
- runtime endpoint/backend;
- model artifact/version/digest where possible;
- context configuration and realized context;
- tool/structured-output capability;
- streaming behavior;
- retry policy;
- timeout/cancellation behavior;
- sandbox/execution mode;
- benchmark fixture version.

## 14.3 Ollama retry behavior is deliberately host-owned

Issue #6942 documented that the native Ollama SDK/provider path had no automatic transient retry while OpenAI SDK clients had their own built-in retry behavior.

The issue was closed after a maintainer explicitly said the framework chose **not to bake in one retry behavior** because there are multiple valid approaches and pointed users to an `auto_retry.py` sample.

Primary sources:

- https://github.com/microsoft/agent-framework/issues/6942
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/samples/02-agents/auto_retry.py

This is not a current bug claim. It is a deliberate abstraction boundary.

ACL implication: provider abstraction should not hide retry/replay semantics. Retry belongs in the exact deployment/effect profile and must distinguish:

- pre-response safe transport retry;
- partial-stream ambiguity;
- model retry;
- tool retry;
- external-effect replay.

---

# 15. MCP integration

## 15.1 MCP is an integration boundary, not an authority owner

MAF supports MCP client/tool integration across local/remote providers. Current code also includes explicit sampling guardrails in Python because a remote MCP server can request sampling and therefore create confused-deputy risk.

The host must still govern remote server trust, network access, credentials, and effect authorization.

## 15.2 Current .NET Tasks support was upgraded to MCP 2026-07-28

Open issue #7824 originally reported the .NET connector behaving like MCP 2025-11-25 and lacking the 2026 Tasks extension.

Task 21 found that this report is partly stale:

- merged PR #7774 explicitly migrated `.NET Microsoft.Agents.AI.Mcp` long-running tasks from experimental 2025-11-25 semantics to the official MCP `2026-07-28` `io.modelcontextprotocol/tasks` extension;
- the PR upgraded the C# MCP SDK to 2.1.0 and added the Tasks extension package;
- task wrappers now opt into Tasks per invocation, retain task handles, bound polling/input behavior, and send best-effort remote cancellation in abandonment/failure paths;
- a Microsoft maintainer stated the code was released and asked the issue reporter to confirm whether the latest package resolves #7824;
- the issue remains open pending confirmation.

Primary sources:

- https://github.com/microsoft/agent-framework/issues/7824
- https://github.com/microsoft/agent-framework/pull/7774

Correct Task 21 conclusion:

- do **not** claim current MAF .NET definitely lacks MCP 2026 support;
- do treat exact protocol/extension interoperability as a versioned qualification target;
- separately test modern stateless transport conformance and Tasks extension behavior.

## 15.3 Remote task handles are not ACL effect settlement

MAF’s task wrapper may transparently poll/cancel an MCP task and return its result through a normal function loop. ACL still needs to bind that remote task handle to its own principal/project/task/run/effect identity and reconcile disappearance/unknown remote state.

---

# 16. A2A integration and remote-agent trust

## 16.1 A2A client and hosting bridge

Current Python package provides:

- `A2AAgent` to call remote A2A agents;
- `A2AExecutor` to expose an Agent Framework agent through A2A;
- typed A2A service continuation state in `AgentSession.service_session_id`.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/a2a/README.md

## 16.2 Current docs explicitly separate protocol IDs from authorization

The A2A README warns:

- the example protocol host does not add auth/authz by itself;
- production hosts must protect HTTP/JSON-RPC endpoints;
- task/thread/context/session IDs are routing handles, not bearer credentials;
- client-supplied IDs must be bound to authenticated user/tenant/workspace before loading/mutating state.

This is a strong Vera/ACL invariant and aligns with MCP research.

---

# 17. Hosting and protocol boundary ownership

## 17.1 Accepted ADR keeps authentication and route authority in application/host code

Accepted ADR `0027-hosting-channels.md` deliberately chooses protocol conversion helpers plus optional execution-state helpers rather than a framework-owned universal channel host.

Application/host code remains responsible for:

- route declaration;
- authentication;
- authorization;
- middleware;
- background tasks;
- native protocol clients;
- command dispatch;
- isolation/session ID source;
- externally supplied session/checkpoint/task/context/conversation ID authorization;
- destructive command effects such as reset/cancel/approve/submit;
- durable state decisions for transient hosting.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/docs/decisions/0027-hosting-channels.md

## 17.2 Session IDs are explicitly partition keys, not proof of identity

The ADR repeatedly requires request-derived IDs to be treated as untrusted candidate keys until bound to authenticated principal/tenant/workspace context.

This directly supports Vera’s future mobile/web/service design.

## 17.3 Immutable continuation points versus mutable conversation heads

The hosting ADR makes another useful distinction:

- immutable response/continuation IDs can safely support branching if each branch writes under a new immutable ID;
- a stable mutable `conversation_id` acts like a mutable head and therefore needs explicit single-writer coordination.

ACL analogue:

- immutable checkpoint/run/evidence objects can branch;
- project/task “current head” pointers require CAS/lease/generation fencing.

---

# 18. Observability

## 18.1 Native OpenTelemetry

Current Python core provides native OpenTelemetry instrumentation for agent/model/tool/workflow operations.

Current default configuration keeps sensitive data disabled unless explicitly enabled in general observability setup.

Primary sources:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/observability.py
- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/samples/02-agents/observability/README.md

## 18.2 Sensitive traces are a separate security decision

When sensitive telemetry is enabled, prompts/responses/tool arguments/results may be exported. Some hosted samples enable it for detailed operational visibility.

ACL should classify evidence audiences separately:

- operator telemetry;
- sensitive raw trace;
- verifier evidence;
- user-visible history;
- product analytics.

No one stream should automatically serve all purposes.

## 18.3 Operational traces are not independent verification

MAF instrumentation is generated by the runtime under test. It is valuable for diagnosis and correlation but does not replace independent workspace/effect/output validation.

---

# 19. Evaluation

## 19.1 Provider-agnostic evaluation API

Current experimental evaluation framework supports:

- `evaluate_agent`;
- `evaluate_workflow`;
- local evaluators/checks;
- Foundry/cloud evaluators;
- expected output and expected tool calls;
- full-conversation versus last-turn splitting;
- custom conversation splitters;
- evaluation failure aggregation/raising.

Primary source:

- https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_evaluation.py

## 19.2 Local deterministic evaluators are especially relevant to ACL

The core docs demonstrate API-free local checks such as:

- keyword checks;
- expected tool-called checks;
- custom local evaluator functions.

This is useful for ACL’s future benchmark lab because deterministic harness correctness can be evaluated separately from semantic/model-graded quality.

## 19.3 Whole-trajectory versus last-turn evaluation is explicit

Current evaluation API can evaluate either:

- latest-turn behavior; or
- the full trajectory against the original request.

A custom splitter can also evaluate around a specific event such as memory retrieval.

This maps well to ACL’s need for checkpoint-level and long-horizon evaluation rather than only final answer scoring.

## 19.4 Evals are currently experimental

The evaluation API is feature-staged as experimental. It is a high-value reference, not yet a reason to bind ACL’s acceptance layer to its API.

---

# 20. Current failure/regression matrix

| Surface | Status at Task 21 | Evidence | ACL/Vera lesson |
| --- | --- | --- | --- |
| Checkpoint nested-state aliasing | Fixed | #7683 + current deep-copy source | Checkpoint reads/restores must not alias authoritative stored state. |
| Failed/cancelled superstep pending writes | Open/reproduced/current-main structure consistent | #7859 + runner/state source | Abort must discard/retire uncommitted state before reuse. |
| Foundry hosted checkpoint vs response durability | Open | #7809 | Execution durability != delivery/evidence durability. |
| Restore + new input atomic lifecycle | Open feature gap | #7863 | Resume should be a first-class atomic transition. |
| Dangling tool/approval closure after cancel/restart | Open/reproduced .NET | #7872 | Pending effects/approvals require drain/reconcile semantics before new work. |
| Experimental policy approval retention | Open/reproduced | #7890 + current security source | Approval state needs expiry/abandonment/cleanup bounds. |
| Name-only built-in auto-approval collision | Documented current warning | Harness/Skills READMEs | Tool display name alone is not authority identity. |
| MCP 2026 .NET Tasks support | Prior report partly stale; implementation upgraded/released | #7824 + merged #7774 | Qualify exact protocol era/extensions; recheck open issues against current code. |
| Ollama automatic retry parity | Deliberately not normalized | #6942 maintainer resolution | Provider abstraction does not imply identical resilience/replay behavior. |
| Shell regex policy | Explicitly not security | current `_policy.py` | Put real authority in sandbox/process/credential layer. |

---

# 21. Cross-project comparison notes

Task 21 should not choose winners, but several mechanisms align or contrast strongly with earlier research.

## 21.1 Compared with LangGraph

Both expose graph/checkpoint/replay concepts. MAF’s current failure #7859 reinforces LangGraph’s prior lesson: durable graph state does not eliminate transition-level replay/state corruption risks.

## 21.2 Compared with Pydantic AI Harness

Pydantic StepPersistence’s explicit `unknown_after_crash` effect state remains stronger evidence for external-effect ambiguity. MAF’s workflow checkpoints and Durable Task layer provide useful workflow durability, but Task 21 found no basis to treat them as a universal external-effect ledger.

## 21.3 Compared with Codex/Gemini CLI

MAF has stronger generic agent/workflow abstraction breadth. Codex/Gemini remain stronger direct references for protected coding-agent sandbox/command authority. MAF’s Agent Hooks and shell documentation support the same separation of policy from OS authority.

## 21.4 Compared with OpenHands

OpenHands’ generation-fenced conversation leases remain a stronger direct reference for distributed single-writer state ownership. MAF hosting ADR explicitly acknowledges mutable conversation heads need coordination but does not make ordinary SessionStore a universal run lease.

## 21.5 Compared with Letta/Graphiti

MAF provides context/history/memory integrations but Task 21 does not establish a competing epistemic long-term-memory architecture. Letta and Graphiti remain more directly relevant to Vera persistent-memory truth/provenance design.

## 21.6 Compared with MCP research

MAF validates the need for exact protocol-version/extension profiles and provides a concrete modern Tasks adapter. MCP still remains the protocol authority; MAF is an implementation/integration reference.

---

# 22. Candidate ACL/Vera invariants derived from Task 21

These are research-derived candidates for later comparison, not implementation authorization.

1. **Separate framework session and provider conversation identity.**
2. **Persist descriptors, not live provider/client handles.**
3. **Make workflow/task checkpoint identity immutable and parent-linked.**
4. **Bind checkpoints to executable graph/harness definition identity.**
5. **Do not use iteration number as checkpoint identity.**
6. **Reading/restoring durable state must not create mutable aliases into stored snapshots.**
7. **Failed/cancelled supersteps must explicitly discard or quarantine pending writes before reuse.**
8. **Resume is a first-class transition: validate state, acquire ownership, bind current authority, then accept new input.**
9. **Execution durability, output delivery, workspace state, and external-effect settlement are separate planes.**
10. **Ordinary workflow checkpoints and distributed durable execution are separate capabilities.**
11. **Durable orchestration replay does not eliminate the need for effect idempotency/reconciliation.**
12. **Provider `call_id` is evidence/correlation, not ACL’s permanent action/effect identity.**
13. **Approvals bind to one trusted occurrence; reusable approvals require explicit scope.**
14. **Tool authorization identity must include trusted origin, not display name alone.**
15. **Pending approvals/jobs/effects require terminal states, expiry, cleanup, and retention policy.**
16. **New work should not silently proceed across unresolved prior effect/approval lifecycles.**
17. **Policy/interception should be structurally outside replaceable worker/model pipelines.**
18. **Policy/interception is not an OS/process sandbox.**
19. **Regex/string command policy is not a security boundary.**
20. **Generated-code execution requires explicit environment projection and a real containment tier for untrusted input.**
21. **Protocol session/task/context IDs are routing handles, not authentication.**
22. **Host/application code owns principal authentication and authorization before state lookup.**
23. **Mutable conversation/project heads require single-writer/CAS/lease/generation fencing.**
24. **Local model qualification includes provider adapter and resilience behavior, not only model/runtime name.**
25. **Retry semantics are part of the deployment/effect profile and must distinguish pre-stream retry from ambiguous replay.**
26. **MCP/A2A capability support is versioned/negotiated and must be tested by exact protocol era/extensions.**
27. **Runtime OpenTelemetry is operator evidence, not independent acceptance proof.**
28. **Sensitive trace content needs separate audience/retention policy.**
29. **Evaluate deterministic harness correctness separately from stochastic/semantic model quality.**
30. **Long-horizon evaluation should support whole-trajectory and intermediate-boundary scoring.**
31. **Feature-level maturity belongs in dependency qualification even when the umbrella framework is GA.**

---

# 23. What Microsoft Agent Framework does not solve for ACL/Vera

Task 21 found no basis to delegate the following ACL/Vera responsibilities wholesale to MAF:

- authoritative project/task/run/effect identity;
- external-effect exactly-once/reconciliation ledger;
- verifier independence from the worker runtime;
- protected governance storage beyond cooperative in-process middleware;
- least-privilege credential broker;
- universal OS/container/process-tree isolation;
- distributed writer fencing for every mutable ACL state domain;
- Git/workspace checkpoint policy for coding tasks;
- crash reconciliation of arbitrary subprocess/API/database effects;
- dependency provenance/security governance;
- Vera’s epistemic long-term memory truth/conflict policy;
- canonical research/governance ownership;
- cross-runtime local-model qualification under the user’s actual hardware and 32K baseline.

MAF can supply or inspire components underneath those boundaries, but Task 21 does not support transferring ownership of them.

---

# 24. Reuse candidates for later comparison

High-value mechanisms to compare after the research queue completes:

### Direct or thin-adapter candidates

- common agent/provider/session abstraction;
- `AgentSession` serialization/type-registry patterns;
- occurrence-aware function/approval identity;
- `ToolApprovalMiddleware` exact-argument/server-label standing approvals;
- workflow graph and checkpoint lineage;
- standard checkpoint storage interface;
- Durable Task extension as a distributed runtime option;
- MCP 2026 Tasks adapter;
- A2A adapter/continuation-state patterns;
- OpenTelemetry semantic fields;
- provider-agnostic local/Foundry evaluation interface;
- Docker/Hyperlight/explicit-environment execution adapter patterns.

### Pattern-only candidates unless maturity improves

- Agent Hooks enforcement, especially verdict-before-durability and indivisible composition;
- Harness background/file/memory/loop surfaces;
- FIDES labeling/policy concepts;
- file/session stores and functional workflows currently marked experimental;
- local/provider packages still beta where ACL depends on strong stability guarantees.

### Strong regression fixtures to retain even if upstream fixes them

- #7683 checkpoint aliasing;
- #7859 failed-superstep stale pending state;
- #7809 checkpoint/response delivery gap;
- #7872 dangling tool/approval closure;
- #7890 abandoned approval retention;
- tool-name-only auto-approval collision;
- provider retry non-parity;
- MCP version/extension migration.

---

# 25. Final Task 21 assessment

Microsoft Agent Framework deserves its high research priority. It is no longer merely an AutoGen/Semantic Kernel transition project; by September 2026 it is a broad GA agent/workflow platform with an unusually transparent set of source, ADRs, migration material, package maturity declarations, samples, and current issue evidence.

Its strongest relevance to ACL/Vera is the combination of:

- common agent/provider abstraction without pretending providers are behaviorally identical;
- explicit portable session state separated from provider continuation identity;
- graph/superstep state transitions;
- checkpoint lineage and graph compatibility;
- host-owned auth/isolation above protocol IDs;
- occurrence-aware approval identity;
- policy/interception seams that can gate persistence;
- separate execution/sandbox tiers;
- a separate distributed durability extension;
- MCP/A2A interoperability;
- OpenTelemetry plus provider-agnostic evaluation.

Its current failures are equally useful. They demonstrate that even a production-supported framework can suffer silent state leakage across failed runs, gaps between internal checkpointing and client-visible delivery, dangling effect/approval state after interruption, and lifecycle leaks in experimental security middleware. Those are exactly the transition boundaries ACL must test rather than assuming framework labels solve them.

**Task 21 conclusion:** Microsoft Agent Framework is a high-value component/pattern reference and a plausible future benchmark/integration candidate. Task 21 does not select it as ACL’s framework, does not select Durable Task as ACL’s scheduler, does not select Ollama/any model through MAF, does not select its sandbox paths, and does not authorize implementation.

Stop after Task 21. Google ADK remains the next project and is not researched here.

## Primary source index

- MAF repository: https://github.com/microsoft/agent-framework
- Current revision: https://github.com/microsoft/agent-framework/commit/afdc0db172d57edd50976d6f15168898f2284916
- Python package status: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/PACKAGE_STATUS.md
- Session state: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_sessions.py
- Workflow state: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_workflows/_state.py
- Workflow runner: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_workflows/_runner.py
- Workflow checkpointing: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_workflows/_checkpoint.py
- Tool approvals: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_harness/_tool_approval.py
- Shell policy: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/tools/agent_framework_tools/shell/_policy.py
- Local CodeAct: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/dotnet/src/Microsoft.Agents.AI.LocalCodeAct/README.md
- Agent Hooks ADR: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/docs/decisions/0035-dotnet-agent-hooks-enforcement.md
- Hosting/auth ADR: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/docs/decisions/0027-hosting-channels.md
- Function-loop contract: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/docs/specs/004-python-function-calling-loop.md
- Evaluation source: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/_evaluation.py
- Observability source: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/core/agent_framework/observability.py
- A2A package: https://github.com/microsoft/agent-framework/blob/afdc0db172d57edd50976d6f15168898f2284916/python/packages/a2a/README.md
- MCP modern Tasks migration: https://github.com/microsoft/agent-framework/pull/7774
- Fixed checkpoint aliasing: https://github.com/microsoft/agent-framework/issues/7683
- Current failed-state leak: https://github.com/microsoft/agent-framework/issues/7859
- Current hosted recovery gap: https://github.com/microsoft/agent-framework/issues/7809
- Current restore+input gap: https://github.com/microsoft/agent-framework/issues/7863
- Current dangling tool lifecycle: https://github.com/microsoft/agent-framework/issues/7872
- Current experimental approval retention: https://github.com/microsoft/agent-framework/issues/7890
- Ollama retry boundary: https://github.com/microsoft/agent-framework/issues/6942
- MCP compatibility follow-up: https://github.com/microsoft/agent-framework/issues/7824
- Microsoft 1.0 announcement: https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/
- Build 2026 update: https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-at-build-2026-announce/
- Durable Extension: https://learn.microsoft.com/en-us/agent-framework/integrations/durable-extension
- Ollama provider docs: https://learn.microsoft.com/en-us/agent-framework/integrations/by-component/model-providers/ollama
- AutoGen migration: https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/
- Semantic Kernel migration: https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-semantic-kernel/
