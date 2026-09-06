# Strands Harness SDK Deep Research

**Task:** ranked project deep research #5  
**Project:** Strands Agents / Strands Harness SDK  
**Canonical repository:** https://github.com/strands-agents/harness-sdk  
**Research date:** 2026-09-06  
**Upstream main examined:** `e3f3ee49d4f5e1f94bc489df6f8603ce26442c31`  
**Status:** deep research complete; no adoption/fork/build decision made

## Why Strands is being studied

Strands is relevant to ACL/Vera because it exposes many of the boundaries a long-running agent harness eventually has to make explicit: model/tool orchestration, invocation limits, retries, cancellation, structured output, authorization, human intervention, sandboxed execution, sessions/snapshots, context management, local-model adapters, tracing, and evaluation.

The research question is not whether ACL should adopt Strands. It is:

> Which Strands mechanisms and failure lessons are worth carrying into ACL/Vera without importing architecture that does not fit the project?

This task stays on Strands only. It does not begin Codex research or compare projects to choose a winner.

---

## Executive assessment

Strands remains a justified Tier-A research target and is one of the strongest current references found so far for **composable in-process control planes around a model-driven agent loop**.

The most useful idea is not a single API. It is the separation of concerns:

1. the model decides what it wants to do;
2. lifecycle limits decide whether execution may continue;
3. retry policy decides whether a provider/model call may be attempted again;
4. tool schemas define callable contracts;
5. interventions can inspect, guide, confirm, transform, or deny actions;
6. Cedar authorization can deterministically decide whether a principal may execute a specific tool call;
7. interrupts bind human responses to explicit interrupt IDs;
8. a sandbox determines where shell/file execution occurs;
9. session/snapshot layers persist selected state;
10. conversation managers determine what state remains model-visible;
11. OpenTelemetry records execution evidence;
12. a separate evaluation package can score outputs, trajectories, state, and traces.

That separation closely matches the ACL direction that has emerged from earlier research: keep model reasoning relatively unconstrained, but make authority, state, recovery, and validation explicit outside the prompt.

The open and recently fixed failures are equally informative. They cluster where two otherwise-reasonable representations or identities meet:

- streamed transcript vs durable transcript;
- local history vs provider-owned stateful history;
- an interrupt response vs the set of currently active interrupts;
- snapshot enumeration vs snapshot restore validation;
- in-process invocation ownership vs another process writing the same session;
- command/file output bytes vs decoded streaming text;
- a text-local edit vs preservation of untouched file bytes;
- cancelled execution vs trace/waiter settlement.

This suggests a high-value ACL design rule:

> Most dangerous harness bugs are not only inside a component; they occur where identity, authority, or state crosses component boundaries.

Strands also leaves important responsibilities to the application. Its built-in session persistence is not a distributed concurrency protocol. Its sandbox abstraction does not provision or govern the container/remote machine for you. A snapshot does not prove external effects. A valid restored message history is trusted executable state. Local Ollama support is real but language/model/runtime specific. The evaluation SDK does not replace an independent hostile verifier such as the promptfoo patterns studied in Task 8.

**Bottom line:** Strands is a high-value mechanism/reference set for ACL, especially for lifecycle control, typed intervention, deterministic authorization, sandbox routing, interrupt identity, and traceable execution. It does not eliminate the need for an outer ACL-owned project/task/effect/evidence authority layer.

---

## 1. Project identity, repository transition, health, and license

### Observed

The canonical repository is `strands-agents/harness-sdk`. GitHub reported it as public, active, not archived, and not disabled when checked. Main was at `e3f3ee49d4f5e1f94bc489df6f8603ce26442c31`, dated 2026-09-04.

The repository now contains both Python and TypeScript implementations, documentation, design/governance material, tooling, and other tightly coupled SDK assets.

The old `strands-agents/sdk-python` path returns a permanent-move response to the current repository identity. This is continuity/consolidation evidence, not abandonment.

The Python package metadata declares:

- package: `strands-agents`;
- Python `>=3.10`;
- Apache-2.0 license;
- `Development Status :: 5 - Production/Stable`;
- optional provider integrations including Ollama, OpenAI, Anthropic, Gemini, LiteLLM, Mistral, A2A, Cedar, and OpenTelemetry.

The repo-level license metadata is also Apache-2.0.

Primary sources:
- https://github.com/strands-agents/harness-sdk
- https://github.com/strands-agents/harness-sdk/blob/main/strands-py/pyproject.toml
- https://api.github.com/repos/strands-agents/sdk-python

### Monorepo transition

`team/designs/0009-mono-repository.md` is marked **Proposed** and explains a plan to consolidate Python, TypeScript, docs, samples, and related work to reduce cross-repository friction, improve cross-language feature parity, and give coding agents fuller project context.

The current repository demonstrates that consolidation occurred. However, this report does **not** treat every motivation or forecast in the proposal as a proven result.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/team/designs/0009-mono-repository.md

### ACL/Vera relevance

The repository move is useful for project-identity tracking and for our own repo-structure thinking, but it is not evidence that Strands was “rewritten because the old design failed.”

Candidate invariant:

> Track canonical repository identity separately from architectural generation and project health.

### Warning

High activity and broad surface area imply churn as well as health. Current issues and recent fixes show active hardening of persistence, context, interrupts, cancellation, and sandbox behavior.

**Confidence:** high.

---

## 2. Design tenets: simple model-driven core, explicit extension seams

### Observed

The project tenets emphasize:

- simple at any scale;
- extensible by design;
- composability;
- making the obvious path the happy path;
- accessibility to both humans and agents;
- common standards.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/team/TENETS.md

### ACL/Vera relevance

This aligns with ACL’s earlier experimental lesson: a harness should not consume most of a small model’s context with rigid meta-instructions merely to compensate for missing runtime controls.

The Strands pattern is generally:

- model reasoning stays in the loop;
- runtime contracts and lifecycle rules live in code;
- custom policy attaches through tools/hooks/plugins/interventions rather than an ever-growing monolithic system prompt.

### Warning

“Simple” public APIs can still hide a large internal surface. ACL should judge mechanisms by failure behavior and testability, not by constructor brevity.

**Confidence:** high.

---

## 3. Agent loop: model-driven reasoning with harness-owned stop conditions

### Observed

The documented event loop is model-driven:

1. invoke the model;
2. inspect the model’s response;
3. if tools were requested, validate/execute them;
4. return results/errors into the conversation;
5. call the model again;
6. stop on an explicit terminal condition.

Tool errors can be returned to the model as structured feedback so the model can recover in a later turn rather than every tool failure automatically terminating the agent.

The runtime exposes stop reasons for conditions including:

- natural end turn;
- tool use / provider stop semantics;
- cancellation;
- turn limits;
- total-token limits;
- output-token limits;
- provider max-token limits;
- stop sequences;
- content filtering;
- guardrail/intervention conditions.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/agent-loop.mdx

### Important limit semantics

Invocation limits are not magic hard-kill quotas in the middle of arbitrary work.

The docs describe checks at loop boundaries. Consequences include:

- a single model turn can overshoot a configured token budget;
- tools already requested by the previous model response may run before the next limit check;
- when multiple invocation limits are reached, precedence rules determine the reported stop reason;
- per-invocation counters reset on a new invocation.

### ACL/Vera relevance

This is a better model for ACL than prompt-only instructions such as “do not take more than N steps.”

Possible ACL runtime fields:

- `turn_budget`;
- `input_token_budget`;
- `output_token_budget`;
- `wall_clock_deadline`;
- `idle_progress_deadline`;
- `tool_effect_budget`;
- `retry_budget_by_class`;
- terminal reason code.

Candidate invariant:

> Execution budgets belong in runtime state, with explicit boundary semantics and terminal reasons, not in model prose alone.

### Warning

A limit checked only between cycles cannot revoke a side effect already in progress. External effects need their own authority/cancellation/idempotency design.

**Confidence:** high.

---

## 4. Cancellation: explicit but cooperative at several boundaries

### Observed

Strands supports cancellation across the agent loop, but the exact semantics vary by where cancellation is observed.

The Python docs describe checkpoints during model streaming, before tool execution, during MCP execution, and after tool execution. External cancellation can be driven through a signal/event.

Important behavior includes:

- partial model output may be discarded when cancellation interrupts streaming;
- token accounting may be incomplete for a cancelled provider stream;
- pending tools can be converted into skipped/error results so conversation structure remains valid;
- MCP cancellation acknowledgement is best-effort beyond the local runtime;
- ordinary tool functions are generally cooperative once executing unless they participate in cancellation;
- nested agent/tool layers can compound polling/propagation latency;
- provider cancellation forwarding varies by provider.

TypeScript exposes corresponding `AbortSignal` patterns.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/agent-loop.mdx

### Recent cancellation/trace regression fix

Commit `ed05dcff0223fa30593988ebc4eb36d4eb01fb63` fixed a Python path where `BaseException`-style cancellation could leave the root agent trace span unclosed.

The fix:

- ends the span on cancellation;
- records cancellation type;
- leaves the OpenTelemetry status UNSET rather than pretending success/failure;
- avoids incorrectly propagating cancellation into unrelated waiting invocations.

Primary source:
- https://github.com/strands-agents/harness-sdk/commit/ed05dcff0223fa30593988ebc4eb36d4eb01fb63

### ACL/Vera relevance

Cancellation is not one boolean. ACL should distinguish:

- cancellation requested;
- model stream stopped;
- tool dispatch prevented;
- in-flight process termination requested;
- process actually exited;
- remote API/MCP acknowledgement received;
- external effect settlement unknown;
- durable state flushed;
- trace/evidence closure completed.

Candidate invariant:

> A cancelled run is not complete until runtime ownership, durable state, child processes, and evidence channels are settled or explicitly marked uncertain.

### Warning

Cooperative cancellation is insufficient for arbitrary native/CPU/subprocess work. ACL will still need process-level ownership and kill/lease semantics for some workers/tools.

**Confidence:** high.

---

## 5. Concurrent invocation and idempotency: logical request identity matters

### Observed

A normal agent instance owns mutable conversation/state and rejects overlapping invocations by default.

Python also exposes idempotency-token behavior for duplicate logical requests:

- the first request owns execution;
- a duplicate request with the same token can wait for the original;
- the duplicate receives the original final `AgentResult` rather than starting the work again;
- if the original aborts before producing a result, the duplicate receives an aborted/idempotency error rather than silently starting a second execution;
- a different request arriving while the same agent is busy is rejected by the safe mode.

Python also exposes an explicitly unsafe reentrant mode with warnings about conversation corruption.

TypeScript currently rejects overlapping invocation but does not expose the same Python idempotency-token shape.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/agent-loop.mdx

### ACL/Vera relevance

This supports separating:

- logical job/task ID;
- request/idempotency key;
- run/attempt ID;
- agent instance ID;
- worker process ID.

A network retry or GUI double-click should not accidentally become a second coding job.

Candidate invariant:

> Duplicate transport requests for the same logical operation should converge on the same owned execution, not create duplicate side effects.

### Warning

In-process invocation ownership does not protect a persistent session from a second process. Strands documents that gap explicitly in session management.

**Confidence:** high.

---

## 6. Retry taxonomy: provider retry is separate from model correction and policy retry

### Observed

Strands has more than one retry path.

### Provider/model retry

The documented default retry strategy retries throttling failures with exponential backoff. Python defaults to six total attempts unless configured otherwise. Other exception types are not automatically retried unless the application extends the policy.

Retry strategy instances carry per-turn state and should not be shared across agents.

TypeScript additionally exposes configurable backoff strategies/jitter.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/retry-strategies.mdx

### Structured-output correction

Structured output validation feeds schema errors back to the model inside the normal agent/tool loop so the model can correct its output. This is not the same as replaying a network call after throttling.

### Intervention Guide retry

After-model interventions can return `Guide` feedback that causes another model attempt. Current intervention documentation states that the framework does not impose a retry cap for Guide-driven retry; the handler is responsible for convergence/bounds/escalation.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/interventions/index.mdx

### ACL/Vera relevance

Every retry class should be separately observable:

- provider throttling/transport retry;
- schema/structured-output correction;
- policy/guardrail retry;
- task-level repair retry;
- crash/restart replay;
- human-requested retry.

Candidate invariant:

> Do not expose one undifferentiated `retry_count`; each retry class needs its own reason, budget, progress test, and terminal behavior.

### Warning

Unlimited or nested retry layers can multiply actual model/tool attempts dramatically. A policy that can request another attempt needs an explicit upper bound or escalation condition at the application level.

**Confidence:** high.

---

## 7. Tool contracts: schema exposure and runtime validation are not identical

### Observed

Python custom tools can derive tool specifications from function type hints/docstrings or accept explicit JSON Schema.

TypeScript supports:

- Zod schemas, which provide runtime input validation and typed callback input;
- plain JSON Schema, which is passed as schema but leaves callback input as `unknown`.

Tool names are constrained to a provider-compatible character/length pattern; invalid names can be normalized/replaced before being sent to the model.

Async tools may run concurrently.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/tools/custom-tools.mdx

### ACL/Vera relevance

A model seeing a JSON schema is not, by itself, proof that the executor will enforce it.

ACL should record separately:

- advertised schema;
- runtime validator implementation;
- authorization policy;
- executor/tool version;
- side-effect class.

Candidate invariant:

> Tool-schema publication, runtime input validation, authorization, and effect execution are separate facts and should be testable independently.

### Warning

Cross-language APIs can have similar-looking schemas with different runtime enforcement strength.

**Confidence:** high.

---

## 8. Structured output: validation feedback remains inside the visible agent loop

### Observed

Strands supports structured output with Pydantic in Python and Zod in TypeScript.

The Python implementation constructs a special structured-output tool whose schema corresponds to the requested output model. When the model calls that tool:

- input is validated against the Pydantic schema;
- successful validation captures the structured object;
- validation failure is converted into a detailed tool-error message describing the fields/problems;
- that error returns to the model so it can self-correct on a subsequent cycle;
- terminal inability to produce a valid object surfaces as a structured-output exception.

Primary sources:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/structured-output.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/strands-py/src/strands/tools/structured_output/structured_output_tool.py

### ACL/Vera relevance

This is well aligned with local/smaller models because corrective information is concrete and task-local instead of being buried in a generic “invalid JSON” wrapper.

Candidate invariant:

> When a model can correct an invalid tool/output payload, return narrow machine-derived validation feedback into the next turn rather than silently reparsing or guessing.

### Warning

Repeated schema correction is still model-loop work. It needs an outer turn/retry budget, especially for a model/runtime combination that cannot satisfy the schema reliably.

**Confidence:** high.

---

## 9. Interventions: typed policy actions instead of raw hook mutation

### Observed

Strands’ intervention system provides typed actions around lifecycle points. Documented actions include:

- `Proceed`;
- `Deny`;
- `Guide`;
- `Confirm`;
- `Transform`.

Interventions can operate before/after model calls and before/after tool calls/invocations.

The typed layer is intended to avoid some ambiguity that can occur when several independent hooks all mutate the same state.

Important semantics include:

- handlers execute in defined order;
- denial can short-circuit;
- Guide feedback can accumulate;
- Confirm can integrate with interrupt/HITL flow;
- Transform changes the observed content/data;
- handler error policy can be configured to throw, proceed (fail open), or deny (fail closed).

Current docs recommend fail-closed behavior for security-sensitive handlers.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/interventions/index.mdx

### ACL/Vera relevance

This is a strong reference for ACL policy composition. It provides a vocabulary more precise than a generic pre-tool hook.

Potential ACL decision shape:

```text
ALLOW
DENY
REQUIRE_APPROVAL
GUIDE_AND_RETRY
TRANSFORM_UNTRUSTED_INPUT
ESCALATE
```

Candidate invariant:

> Security/policy handlers should produce explicit typed decisions with deterministic composition rules rather than implicitly fighting over mutable hook state.

### Warning

A `Proceed` error policy is appropriate for observability/convenience handlers but dangerous for authority-bearing controls. Policy failure mode is itself part of the trust model.

**Confidence:** high.

---

## 10. Cedar authorization: deterministic principal-aware enforcement before tool calls

### Observed

The initial Cedar design document explicitly argues that prompts are not authorization boundaries and identifies the tool/action boundary as a natural enforcement point.

More importantly, current shipped Python source implements a vended Cedar authorization intervention.

`CedarAuthorization`:

- evaluates before tool calls;
- resolves a principal either statically or from invocation state;
- denies missing/empty principal identity;
- denies malformed principal/tool identity cases;
- can include tool input and runtime context in the authorization request;
- tracks per-tool call count in agent state;
- can enrich authorization context;
- validates policies/schema before accepting updates;
- denies when policy evaluation errors;
- denies on no-decision;
- denies explicit policy refusal;
- keeps call-count state in agent state so persistence can carry it across snapshots/sessions;
- warns that one handler instance should be associated with one agent because sharing can leak rate/count state between agents.

Primary sources:
- https://github.com/strands-agents/harness-sdk/blob/main/team/designs/0006-cedar-authorization.md
- https://github.com/strands-agents/harness-sdk/blob/main/strands-py/src/strands/vended_interventions/cedar/cedar_authorization.py

### ACL/Vera relevance

This is a concrete external implementation of a central ACL principle:

> The model proposes an action; deterministic policy decides whether the authenticated/authorized principal may execute it.

It can evaluate not just a tool name but arguments and runtime context.

Possible ACL policy inputs:

- user/project principal;
- worker role;
- project ID;
- task ID;
- requested tool;
- tool arguments;
- workspace root;
- effect class;
- prior call count;
- time/risk context.

### Strong pattern: fail closed on identity/policy ambiguity

Missing principal, evaluation error, and no-decision do not become implicit permission.

### Warning

Authorization of each action is not the same as preserving the principal’s intended objective over a long agent run.

**Confidence:** high.

---

## 11. Open goal-fencing gap: action authorization does not prove objective integrity

### Observed

Open issue #3877 proposes “goal fencing” as a distinct control from existing Cedar action authorization, HITL, steering, or loop mechanisms.

The issue argues that an agent can potentially drift from or have its objective redirected away from the principal’s original goal while still making individually authorized tool calls.

Primary source:
- https://github.com/strands-agents/harness-sdk/issues/3877

### ACL/Vera relevance

This is important for Vera and autonomous coding workers.

Action-level policy can answer:

> Is this worker allowed to write this file?

but may not answer:

> Is this write still in service of the user-approved task and project scope?

Candidate future ACL invariant:

> Persist the principal-approved objective/scope separately from mutable model context and include stable task/scope identity in high-authority policy checks.

### Warning

Goal fencing is an open proposal here, not a shipped Strands guarantee. Do not cite it as an existing protection.

**Confidence:** high that the gap/proposal exists; no conclusion on final design.

---

## 12. Sandbox: explicit execution boundary separated from the trusted agent runtime

### Observed

Strands’ current sandbox abstraction keeps the agent/model/hooks/state on the trusted host while routing shell/file execution into a pluggable execution environment.

The shared interface includes:

- streaming command execution;
- code execution;
- file reads/writes/removal/listing;
- optional timeout;
- working directory override;
- environment variables;
- TypeScript abort signal support.

When a sandbox is configured, Strands automatically vends:

- `sandbox_shell`;
- `sandbox_file_editor`.

The shell uses a fresh shell per call, so ordinary shell state such as current directory/environment mutation does not automatically persist between calls.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/sandbox/index.mdx

### Critical default boundary

The documentation is explicit:

> Omitting the sandbox is **not** sandboxing.

Without an explicit sandbox, command/file operations run on the host with the permissions of the agent process. The docs frame this as trusted local-development convenience rather than a production security boundary.

TypeScript can explicitly set `sandbox: false` to make the opt-out intentional.

### ACL/Vera relevance

This explicitness is valuable. ACL should never encode “sandboxed” as an assumption inferred from which tool name happens to be called.

Candidate invariant:

> Every worker run has an explicit execution-environment descriptor; absence of isolation is a named high-authority mode, not an invisible default.

**Confidence:** high.

---

## 13. Docker and SSH sandboxes: routing is provided, environment governance is application-owned

### Observed

Built-in backends include:

### DockerSandbox

- executes into an already-running container via `docker exec`;
- Strands does not create/provision the container;
- application chooses working directory and container user.

### SshSandbox

- uses fresh SSH processes;
- requires key-based auth/BatchMode behavior;
- working directory is explicit;
- host-key behavior configurable;
- additional SSH options are restricted by an allowlist unless explicitly bypassed.

The option allowlist protects against dangerous options such as `ProxyCommand` / `LocalCommand` that could execute on the local host.

`allowUnsafeSshOptions` deliberately removes that protection, and docs warn not to combine it with model-generated/untrusted options.

Neither backend establishes long-lived environment variables at construction; command-specific environment can be supplied per call.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/sandbox/available-sandboxes.mdx

### ACL/Vera relevance

Strands gives a useful execution transport abstraction, but ACL still needs policy for:

- container image/hash;
- container creation and teardown;
- filesystem mounts;
- host UID/GID;
- network egress;
- CPU/RAM/time quotas;
- credential injection;
- package installation;
- artifact extraction;
- post-run verification and destruction.

Candidate invariant:

> A sandbox API is not the same thing as a fully governed worker environment lifecycle.

**Confidence:** high.

---

## 14. File-edit correctness: preserve bytes outside the intended edit

### Observed

Commit `e448bea9e42298b31047ac8d2a616b29819563c1` fixed a TypeScript file-editor defect where `str_replace` / insertion behavior could rewrite content outside the intended region.

Regression coverage added cases for preserving:

- tabs;
- CRLF line endings;
- content around the target region;
- repeated multiline matches;
- binary-like bytes/content;
- exact start/end-of-file behavior.

Primary source:
- https://github.com/strands-agents/harness-sdk/commit/e448bea9e42298b31047ac8d2a616b29819563c1

### ACL/Vera relevance

This is another example of destructive-edit safety being more subtle than “the model selected the right text.”

Candidate invariant:

> A localized edit operation must prove that bytes outside its intended mutation region remain unchanged unless broader normalization is explicitly requested.

Possible ACL fixture:
- mixed CRLF/LF file;
- tabs + non-ASCII content;
- one targeted replacement;
- assert exact byte equality outside replacement span.

**Confidence:** high.

---

## 15. Open sandbox streaming failure: bytes-to-text boundaries matter

### Observed report

Open issue #4156 reports that TypeScript sandbox process streaming decodes each `Buffer` chunk independently. If a multibyte UTF-8 sequence is split across pipe chunks, it can become replacement characters (`�`).

The issue states the common streaming helper is used by local, Docker, and SSH sandbox paths and provides a small reproducible example plus a proposed `setEncoding('utf8')` style correction.

Primary source:
- https://github.com/strands-agents/harness-sdk/issues/4156

### ACL/Vera relevance

A coding worker may treat stdout/stderr as evidence, test output, compiler output, or even untrusted prompt input. Silent corruption can change both decisions and evaluation evidence.

Candidate invariant:

> Preserve byte-stream decoding state across chunks; never assume process chunk boundaries align with character boundaries.

### Warning

This is an open issue report observed during research, not a claim that every later Strands build remains affected.

**Confidence:** medium-high in the reported reproduction/current issue state.

---

## 16. Sessions and snapshots: portable state with explicit persistence scopes

### Observed

Current Strands session management can persist agent state across interactions and restarts. Snapshot-based session managers store complete point-in-time snapshots and can also create immutable history snapshots.

Python’s recommended `SnapshotSessionManager` for new single-agent sessions can persist state including:

- messages;
- agent state;
- conversation-manager state;
- interrupt state;
- model state;
- other versioned snapshot data.

TypeScript has a similar snapshot-oriented shape.

Immutable snapshot IDs use UUIDv7 and can be listed/restored.

Primary sources:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/snapshots.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/session-management.mdx

### Multi-agent ownership rule

Current docs explicitly warn:

- Python `SnapshotSessionManager` does not support Graph/Swarm;
- use the orchestrator’s compatible session manager for those cases;
- child agents inside a multi-agent system should not also own separate session managers because that conflicts with orchestrator persistence.

This is a useful ownership principle independent of implementation.

Candidate invariant:

> For every piece of durable state, define one authoritative persistence owner; nested components must not independently persist competing versions of the same lifecycle state.

### Warning

Snapshot/session state is not a workspace snapshot or external-effect ledger. It represents the SDK state it owns.

**Confidence:** high.

---

## 17. Session persistence is single-live-writer, not distributed concurrency control

### Observed

The current session-management docs explicitly state that built-in persistence is designed around a single live writer per conversation.

They also state:

- built-in session managers take no distributed lock;
- the invocation guard is process-local;
- another process can target the same session/agent identity without the first process detecting it.

Documented failure modes include:

1. two live agents with the same session ID + agent ID can overwrite/merge turns without an error;
2. concurrent cold creation is effectively check-then-write and can allow both creators to “succeed,” with later write winning.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/session-management.mdx

### ACL/Vera relevance

ACL workers may run on multiple processes/machines. An in-memory busy flag is not enough.

Candidate invariants:

- project/task/run lease ownership;
- generation/version on persistent state;
- compare-and-swap on mutation;
- lease expiry/recovery;
- stale writer rejection;
- one authoritative writer unless explicit merge semantics exist.

### Strong cross-project connection

This echoes LangGraph’s stale-writer/deletion concerns and Cline’s compare-and-swap checkpoint restore lesson, but no cross-project winner is selected here.

### Warning

Do not treat a JSON snapshot store as safe concurrent orchestration merely because writes are individually successful.

**Confidence:** high.

---

## 18. Session storage is itself a trust boundary; symlink behavior is documented

### Observed

The session-management best-practices section treats storage as trusted and recommends restrictive filesystem permissions.

It also explicitly warns that, in shared/multi-tenant filesystem storage, the SDK does not prevent symlinks inside the session-storage directory. An attacker who can mutate that directory could create a message-file symlink pointing at another file; the session loader may follow it and load sensitive file content into agent history.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/session-management.mdx

### ACL/Vera relevance

This reinforces that checkpoint provenance is not just cryptographic/file-format correctness.

Candidate invariant:

> Persistent agent state is high-trust input. Its storage root requires filesystem ownership, canonical-path/symlink policy, provenance, and integrity controls at least as strong as the worker’s code/configuration store.

### Warning

A worker sandbox does not automatically protect a host-side session store if the session store itself is writable or path-confused.

**Confidence:** high.

---

## 19. Trusted message history can directly trigger tool execution

### Observed

Strands’ trusted-message-history security documentation is unusually explicit: restored message history is **trusted execution input**, not passive chat data.

In the Python behavior described by the docs, if imported/restored history ends with an assistant `toolUse` block, the next invocation can execute that pending tool call directly with the stored arguments before another model decision.

The docs warn that forged tool-result history can also lie to the model about what actions occurred.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/safety-security/trusted-message-history.mdx

### ACL/Vera relevance

This is a critical finding for ACL checkpoint/handoff design.

Candidate invariant:

> “Valid JSON” or “valid session schema” never establishes that restored state is authorized to continue execution.

ACL checkpoint/resume records should eventually include:

- origin/provenance;
- project/task/run identity;
- schema version;
- trusted writer identity;
- integrity digest/signature/MAC as appropriate;
- active effect/interrupt state;
- authority/capability version;
- restore policy decision.

### Warning

Simply stripping a trailing tool call is not a complete provenance system; the rest of history can still contain poisoned claims/instructions.

**Confidence:** high.

---

## 20. Snapshot enumeration must validate the same contract as restore

### Observed report

Open issue #4198 reports that Python `SnapshotSessionManager.list_snapshot_ids()` can expose malformed foreign/corrupt storage keys as public snapshot IDs, while `restore_snapshot()` applies UUIDv7 validation and rejects those same IDs.

Because listing also sorts/limits results, malformed entries can affect pagination and displace valid handles.

Primary source:
- https://github.com/strands-agents/harness-sdk/issues/4198

### ACL/Vera relevance

This is a small bug with a broad lesson:

> Every public handle produced by enumeration should satisfy the same identity/validation contract as the API that consumes that handle.

Apply this to ACL:

- project IDs;
- task IDs;
- checkpoint IDs;
- artifact IDs;
- worker IDs;
- approval IDs;
- model/runtime profile IDs.

### Warning

The report does not claim normal Strands writes generate malformed snapshot names; the trust issue appears when storage contains manually created, migrated, corrupted, or foreign objects.

**Confidence:** high in the reported contract mismatch.

---

## 21. Provider-owned state creates another durable state plane

### Observed report

Open issue #4102 reports a stateful-model interaction where a `ContextInjector`-style block documented as ephemeral can remain in server-side conversation state even though it does not persist in local `agent.messages`.

The report’s scenario uses a stateful OpenAI Responses-style provider where the server stores/chains conversation state via response IDs. The issue is source-derived and notes that local history can be cleared while provider-side history remains authoritative to future model calls.

Primary source:
- https://github.com/strands-agents/harness-sdk/issues/4102

### Related proposed design evidence

`team/designs/0004-stateful-models.md` (status **Proposed**) explicitly describes the architectural direction of keeping provider conversation identifiers in framework-managed model state while the remote provider may own the full conversation chain.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/team/designs/0004-stateful-models.md

### ACL/Vera relevance

A worker’s model-visible state may be distributed across:

- local conversation messages;
- summarization/compaction state;
- server-side model conversation/history;
- tool/MCP state;
- ACL project/task state.

Candidate invariant:

> Every durable state plane that can affect future model behavior must be identified and included in reproducibility, reset, privacy, and recovery semantics.

### Warning

Issue #4102 is an open/source-derived report, not a live provider reproduction performed in this task. Treat the specific bug as current reported evidence, and the multi-state-plane lesson as the stronger architecture conclusion.

**Confidence:** medium on exact current provider behavior; high on the architectural risk class.

---

## 22. Streamed/UI transcript can diverge from durable replay history

### Observed report

Open issue #4004 reports a path where text content accompanying pending tool use can be visible during streaming but omitted from the durable message representation due to control-flow handling.

Primary source:
- https://github.com/strands-agents/harness-sdk/issues/4004

### ACL/Vera relevance

A GUI/chat log is not necessarily authoritative replay state.

Candidate invariant:

> Treat live UI events, persisted transcript, model-visible context, and audit/evidence log as separate representations and test explicit consistency contracts between them.

Potential ACL fixture:
- stream text + tool request in same model turn;
- persist run;
- restart;
- assert replay model-visible history preserves all semantically relevant content.

### Warning

This is an open issue report. Recheck before dependency decisions.

**Confidence:** medium-high in the reported failure class.

---

## 23. Interrupts: human responses bind to explicit interrupt IDs

### Observed

Strands supports human-in-the-loop interruptions from lifecycle hooks and tool implementations.

An interrupt contains:

- a human-readable name;
- optional serializable reason/context;
- a unique interrupt ID.

Resume content references the specific interrupt ID.

Before-tool and before-tools interception can:

- pause one call;
- pause a whole batch;
- cancel one tool;
- cancel an entire tool batch.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/interrupts.mdx

### ACL/Vera relevance

This is exactly the shape ACL needs for approvals:

- approval request ID;
- task/run/worker identity;
- proposed effect/tool + arguments;
- reason/risk summary;
- response bound to request ID;
- request state: active/answered/cancelled/expired.

Candidate invariant:

> Human approval must target a stable active request ID, never “the most recent pending question” by position or ambiguous scalar state.

**Confidence:** high.

---

## 24. Interrupt/resume can replay lifecycle hooks; side-effecting hooks require idempotency

### Observed

The interrupt docs note that a per-tool interrupt can split one logical assistant tool batch across multiple event-loop cycles.

As a consequence, `AfterToolsEvent` can fire more than once for what a human might think of as one logical assistant action: once on the interrupt cycle with completed results so far, and again after resume.

The docs explicitly warn that an `AfterToolsEvent` hook with side effects may run more than once for one assistant message.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/interrupts.mdx

### ACL/Vera relevance

This generalizes beyond Strands:

> A lifecycle callback is not automatically exactly-once merely because it has a name like “after tools.”

ACL side-effecting hooks/listeners should be keyed by stable logical event/effect IDs and tolerate replay.

### Potential fixture

- two tools in one model response;
- first succeeds;
- second triggers approval interrupt;
- resume;
- assert post-tool bookkeeping/notification is not duplicated.

**Confidence:** high.

---

## 25. Open stale interrupt-response failure: active-state validation must fail closed

### Observed report

Open issue #4171 reports that TypeScript can accept a second response for an interrupt that was already answered/completed.

The report states that the stale second response can trigger an extra/“phantom” model call and create consecutive assistant messages that violate provider role expectations.

Primary source:
- https://github.com/strands-agents/harness-sdk/issues/4171

### ACL/Vera relevance

This is a direct approval-system lesson.

Candidate invariant:

> An approval/interrupt response is a one-time state transition. A response for an ID that is not currently active must be rejected loudly and must not trigger execution.

Approval states should likely include:

```text
PENDING -> APPROVED | DENIED | CANCELLED | EXPIRED
```

with no transition back to PENDING and no second terminal response.

### Warning

This is an open issue report observed during Task 9; recheck before dependency adoption.

**Confidence:** high in the reported reproduction.

---

## 26. Context management is a state mutation, not merely token optimization

### Observed

Current Strands conversation managers include:

- `NullConversationManager`;
- `SlidingWindowConversationManager` (default);
- `SummarizingConversationManager`.

Important semantics:

- omitting a conversation manager selects the sliding-window default; it does not mean “preserve everything”;
- sliding-window logic can trim old messages, repair dangling tool/message sequences, truncate oversized tool results, pin selected messages, and proactively compress context;
- Python can run management per model turn / every N turns;
- summarization can use the agent/model to replace older conversation content with a model-generated summary;
- tool-use/result pairing is treated as a structural invariant while reducing context.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/conversation-management.mdx

The main commit examined in this task itself concerns Python context-offloading work, showing this area is actively evolving.

### ACL/Vera relevance

A compressed context is not merely a cheaper serialization of the same state. It can change what the model knows/remembers.

Candidate invariants:

- record context-manager version/config;
- record when compression/offload occurred;
- preserve source references/provenance for summarized facts;
- keep authoritative task/project state outside model-generated summaries;
- distinguish model-visible context from audit/effect truth.

### Warning

A model-generated summary can omit or distort details. It should not become the authoritative source for approvals, completed effects, task dependencies, or governance state.

**Confidence:** high.

---

## 27. Ollama/local model support is real but capability- and language-specific

### Observed

Current Strands documentation includes a native Ollama provider for Python.

The provider supports local Ollama interaction including:

- chat/generation;
- streaming;
- tool/function calling for capable models;
- image input where supported;
- runtime/model configuration;
- structured-output workflows when the underlying model supports the required tool behavior.

The package has an `ollama` optional dependency, and integration tests include an Ollama model path.

Primary sources:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/model-providers/ollama.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/strands-py/src/strands/models/ollama.py
- https://github.com/strands-agents/harness-sdk/blob/main/strands-py/tests_integ/models/test_model_ollama.py

### ACL/Vera relevance

This keeps Strands relevant for ACL’s local-worker objective.

But “Strands supports Ollama” is still too coarse. Benchmark identity should include:

- Strands Python version;
- Ollama version;
- model exact tag/digest;
- quantization;
- context size/runtime options;
- tool-call capability;
- schema/structured-output behavior;
- streaming behavior;
- host hardware.

Candidate invariant:

> Local compatibility is a verified model + runtime + adapter + configuration property, not a framework/provider checkbox.

### Warning

Current docs scope native Ollama support to Python; do not assume identical TypeScript behavior or feature parity.

**Confidence:** high.

---

## 28. Observability: OpenTelemetry exposes detailed model/tool/runtime evidence

### Observed

Strands uses OpenTelemetry for hierarchical agent traces.

The documented trace hierarchy includes:

- top-level agent invocation;
- event-loop cycles;
- model invocation spans;
- tool execution spans.

Attributes can include:

- model/provider identity;
- system prompt;
- user/assistant content;
- tool name;
- tool call ID;
- tool result/status;
- prompt/output/total tokens;
- cache token metrics;
- timing;
- cycle identity.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/observability-evaluation/traces.mdx

### ACL/Vera relevance

This is a useful candidate substrate for the worker GUI and external evaluator:

- stable tool-call IDs;
- token/resource accounting;
- runtime failure locations;
- per-cycle status;
- cancellation evidence;
- correlation with task/run/project IDs.

### Security warning

Trace attributes can include sensitive system prompts, raw messages, tool arguments/results, and other operational data.

Candidate invariant:

> Observability is not automatically a redaction/security boundary; define telemetry audience and sensitive-field policy separately.

**Confidence:** high.

---

## 29. Strands Evaluation: framework-native deterministic and semantic evaluation

### Observed

Strands maintains a separate `strands-agents-evals` package/framework for evaluating agents and LLM applications.

Current documentation describes:

- output evaluation;
- trajectory evaluation;
- tool-use evaluation;
- interaction evaluation;
- deterministic evaluators such as equals/contains/tool-called/state-equals;
- LLM-as-a-judge evaluators;
- trace-based evaluation;
- simulators/test generation;
- experiment serialization/versioning;
- CLI validation/run/report/CI workflows;
- detectors/root-cause tooling.

Primary source:
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/evals-sdk/quickstart.mdx

### Critical identity warning

The trace-based quickstart warns that in-memory trace evaluation needs session/conversation IDs on traces so spans from separate test cases do not get mixed together. The provided traced handler automates that correlation.

### ACL/Vera relevance

Again, this is a “valid evidence, wrong identity” class of failure.

Candidate invariant:

> Every evaluation artifact must bind to one explicit project/task/run/test-case identity; evidence with ambiguous correlation is invalid, not merely lower confidence.

### Boundary vs promptfoo

Strands Evaluation is valuable as framework-native evaluation. Task 8 showed promptfoo’s distinct strength as an independent/adversarial verifier around a coding-agent runtime. This task does not choose between them.

**Confidence:** high.

---

## 30. Cross-plane failure pattern: valid state in the wrong authority/identity domain

The strongest synthesis from current Strands failures is that many defects appear at boundaries between control planes rather than within one isolated feature.

### Examples

| Failure surface | Boundary crossed | ACL lesson |
|---|---|---|
| #4171 stale interrupt response | response ID ↔ active interrupt state | exactly-once active-ID validation |
| #4198 malformed listed snapshot ID | storage key ↔ public restore handle | enumeration/consumer validation must agree |
| #4102 ephemeral context persisting remotely | local history ↔ provider-owned durable history | inventory every durable state plane |
| #4004 streamed text missing durably | live stream ↔ replay history | UI/evidence/history are separate representations |
| #4156 split UTF-8 corruption | byte stream ↔ decoded text | preserve decoder state across chunks |
| #4013 cancellation trace fix | execution cancellation ↔ telemetry/waiter settlement | cancellation must settle every owner/evidence path |
| #4014 file editor fix | logical text edit ↔ physical byte preservation | destructive mutation needs exact pre/post invariants |
| documented multi-process session collision | in-process owner ↔ persistent state writer | distributed fencing/lease required |

### ACL/Vera relevance

This supports a design-review question to apply later:

> For each boundary, what stable identity crosses it, who owns the authoritative state, and what proves the transition occurred exactly once?

Possible boundary checklist:

- model → tool proposal;
- policy → authorization;
- approval → execution;
- runtime → sandbox;
- sandbox → filesystem/process;
- tool effect → durable effect ledger;
- run → checkpoint;
- checkpoint → restore;
- local state → provider state;
- runtime → telemetry;
- telemetry → evaluator;
- evaluator → acceptance decision.

**Confidence:** high as cross-case synthesis; not proof that every boundary is currently defective.

---

## 31. Current shipped mechanisms vs design proposals

Strands has unusually rich design documents. This is useful, but the research process must not collapse proposals into current guarantees.

### Confirmed current/shipped surfaces used in this report

- model-driven agent loop;
- lifecycle limits/stop reasons;
- cancellation;
- provider retry strategies;
- custom tool schemas;
- structured output correction;
- typed interventions;
- Python Cedar authorization implementation;
- interrupts;
- sandbox abstraction + Docker/SSH backends;
- session/snapshot management;
- conversation managers;
- native Python Ollama provider;
- OpenTelemetry tracing;
- Strands Evaluation package/docs.

### Proposed/open ideas explicitly kept separate

- the rationale/details in monorepo design #0009 beyond the fact consolidation exists;
- full stateful-model design #0004 as written;
- goal-fencing proposal #3877;
- other team/design documents not verified against shipped code.

### ACL/Vera relevance

Candidate research rule:

> Design documents reveal intent and pressure; shipped source/tests/issues establish current behavior.

**Confidence:** high.

---

## 32. Reusable mechanism candidates for later comparison

No adoption decision is made here. These are mechanisms worth carrying into the later build-vs-reuse task.

### A. Explicit runtime invocation budgets

Why:
- reliable, model-independent stop conditions;
- useful local-worker guardrail;
- clear terminal reason.

Need to compare:
- hard/idle wall-clock timeout support;
- how child processes/effects are handled at limit;
- persistence of budget state across restart.

### B. Idempotency-token invocation ownership

Why:
- prevents duplicate logical jobs on retry/double submit;
- clean separation of request vs run.

Need to compare:
- distributed implementation;
- persistence across process restart;
- side-effect identity.

### C. Typed intervention decisions

Why:
- avoids raw hook ambiguity;
- makes allow/deny/guide/confirm/transform explicit;
- supports fail-closed error policy.

Need to compare:
- policy composition and audit trail;
- latency/complexity;
- cross-language parity.

### D. Cedar authorization at tool boundary

Why:
- principal-aware deterministic enforcement;
- arguments/context included;
- no-decision/error deny.

Need to compare:
- ACL-specific policy model complexity;
- principal/task/scope representation;
- local dependency footprint;
- how policy versions bind to evidence/checkpoints.

### E. Interrupt IDs and explicit resume content

Why:
- better than positional/implicit approval state;
- supports batch/per-tool approval.

Need to add:
- exactly-once active-state validation;
- expiry/cancellation;
- durable ownership;
- signed/user-authenticated response if remote.

### F. Sandbox interface

Why:
- separates trusted agent host from execution target;
- portable Docker/SSH/custom backend concept;
- tools can share one environment.

Need to add/own:
- environment provisioning;
- mounts/network/credential policy;
- process-tree termination;
- workspace snapshots;
- post-run verification;
- cleanup.

### G. Snapshot schema + immutable history

Why:
- explicit versioned portable state;
- immutable restore points.

Need to add:
- state provenance/integrity;
- distributed writer fencing;
- workspace/effect state;
- safe-restore preconditions;
- trusted-history validation.

### H. OpenTelemetry hierarchy

Why:
- existing ecosystem;
- model/cycle/tool IDs and metrics;
- useful GUI/eval substrate.

Need to add:
- ACL project/task/run/effect IDs;
- redaction/trust classes;
- evidence durability requirements;
- verifier-only channels.

### I. Native Ollama provider

Why:
- directly supports local-worker experimentation.

Need to validate:
- exact target models;
- structured-output reliability;
- tool-call fidelity;
- cancellation;
- long context;
- streaming;
- performance on ACL hardware.

---

## 33. What ACL should not copy blindly

### 1. Host execution as an invisible convenience default

Strands documents it clearly, but ACL’s autonomous-worker product should likely make unsandboxed mode an explicit/high-friction development choice.

### 2. In-process-only ownership for persistent sessions

ACL’s long-running workers can outlive/restart/move between processes. Persistent project/task state requires distributed fencing or equivalent versioned ownership.

### 3. Treating valid restored history as trusted merely because it parses

History can contain executable pending tool calls and poisoned claims.

### 4. One broad retry counter

Provider retry, schema correction, policy guidance, crash replay, and task repair need different semantics.

### 5. Model-generated summaries as project truth

Conversation compression is useful for model context, but not an authoritative task/effect/audit store.

### 6. Assuming a sandbox backend equals a full security policy

Docker/SSH routing does not decide mounts, network, credentials, user, image, or cleanup.

### 7. Assuming action authorization proves task intent

A permitted tool call can still serve a drifted or injected objective. Goal/scope provenance remains separate.

### 8. Assuming traces equal trustworthy evaluation

Trace correlation and audience/redaction must be controlled, and an independent verifier still matters.

---

## 34. Candidate ACL/Vera invariants extracted from Strands

These are research-derived candidates for later comparison/governance work, **not adopted ACL policy in this task**.

1. **Model proposals are non-authoritative.** Runtime policy decides what executes.
2. **Lifecycle budgets are runtime state.** Turn/token/time/effect limits have explicit semantics and terminal reasons.
3. **Retry classes are separate.** Provider, schema, policy, crash, and task retries have independent budgets/reasons.
4. **Logical request identity is distinct from run identity.** Duplicate transport requests should not duplicate work.
5. **Tool schema, runtime validation, authorization, and execution are separate contracts.**
6. **Policy decisions are typed.** Allow/deny/guide/confirm/transform semantics are explicit and composable.
7. **Security-policy errors fail closed.** Missing identity/no decision/evaluation failure do not imply permission.
8. **Action authorization does not replace objective/scope provenance.**
9. **Execution environment is explicit.** Sandboxed vs host mode is recorded, never inferred.
10. **Sandbox lifecycle is owned.** Image, mounts, network, credentials, user, resources, cleanup, and evidence are part of the run definition.
11. **Destructive editors preserve untouched bytes.**
12. **Process stream decoding preserves character boundaries across chunks.**
13. **Exactly one durable owner exists for a state domain.** Nested components do not maintain competing authoritative copies.
14. **Persistent state needs distributed single-writer/fencing semantics.** In-process busy flags are insufficient.
15. **Checkpoint/history provenance matters.** Valid syntax/schema is not authorization to resume.
16. **Every enumerated handle satisfies the consuming API’s validation contract.**
17. **All durable state planes are inventoried.** Local history, provider history, context summaries, workspace, effects, and memory are distinct.
18. **UI stream and replay state are separate representations with explicit consistency tests.**
19. **Approval responses are one-time transitions against active stable IDs.** Stale/duplicate responses fail closed.
20. **Lifecycle callbacks may replay around interrupts/retries.** Side-effecting callbacks require idempotency identity.
21. **Context trimming/summarization/offloading is observable model-state mutation.** It does not rewrite project truth.
22. **Local-model capability is verified per model/runtime/adapter/configuration.**
23. **Telemetry is evidence, not a secret boundary.** Raw prompt/tool fields need audience/redaction policy.
24. **Evaluation evidence must bind to stable test/run/session identity.** Mis-correlated valid spans are invalid evidence.
25. **Proposed designs are not shipped guarantees.** Intent and implementation evidence stay separate.

---

## 35. High-value ACL regression fixtures suggested by Strands evidence

These are future test ideas only; this research branch does not implement them.

### Lifecycle and cancellation

- cancel during model stream;
- cancel immediately before tool dispatch;
- cancel a long-running subprocess/tool;
- assert trace closes and run/effect state is explicit;
- duplicate same idempotency key during execution;
- different key while single-writer worker busy.

### Retry

- throttling retry with exact attempt count/backoff record;
- deterministic invalid structured output that cannot self-correct;
- intervention/policy Guide loop that must stop at explicit ACL limit.

### Tool contracts

- schema advertised but runtime validation disabled/mismatched;
- forbidden extra argument;
- unknown tool name;
- exact principal/tool/args authorization deny.

### Authorization

- missing principal;
- no matching policy;
- policy-engine exception;
- allowed tool but wrong project/task scope;
- repeated call exceeding policy count.

### Sandbox

- accidental unsandboxed run should be detectable before execution;
- SSH unsafe option injection;
- network egress outside allowlist;
- file write outside workspace/mount;
- subprocess survives tool timeout/cancellation;
- multibyte stdout split across chunks.

### File editing

- mixed CRLF/LF;
- tabs;
- non-ASCII;
- binary-ish bytes;
- repeated target string;
- verify exact unchanged byte regions.

### Persistence

- two processes write same task/session;
- stale writer after lease/version change;
- corrupted/foreign snapshot key in list;
- tampered snapshot with trailing pending tool call;
- symlink in state store;
- restore under changed capability/policy version.

### Interrupts

- answer correct interrupt ID;
- answer stale/previously answered ID;
- answer wrong task/run ID;
- cancel during resume then resend;
- batch with one completed tool + one interrupted tool;
- assert post-tool side effects are not duplicated.

### Context/state consistency

- streamed text + toolUse must survive durable replay;
- provider-side stateful conversation reset vs local reset;
- summarization must not overwrite authoritative task/effect facts;
- two eval cases with identical content but distinct IDs must never share trace spans.

---

## 36. Questions deliberately deferred to later comparison

1. Does ACL need Strands as a runtime dependency or only selected patterns?
2. Is Cedar worth the dependency/policy complexity versus a narrower custom ACL policy engine?
3. Should ACL use Strands’ intervention layer directly or implement a smaller typed decision interface?
4. Can Strands snapshots be wrapped safely enough, or should ACL own its task/effect checkpoint schema entirely?
5. Is the sandbox abstraction sufficient as ACL’s execution backend interface after adding provisioning/leases/evidence?
6. How does Strands compare with Codex/OpenHands on process-tree cleanup, mount/network isolation, Git/workspace safety, and approval inheritance?
7. How reliable is Strands + Ollama on the exact local 7B/14B workers selected by ACL benchmarks?
8. Should Strands Evaluation be used alongside promptfoo, or only for framework-native tests?
9. What controls are needed if provider-side stateful conversation is enabled in a reproducible autonomous coding worker?
10. Which current Strands APIs are stable enough to pin behind a thin adapter?

These questions belong to later project comparison after Codex/OpenHands and remaining Tier-A work.

---

## 37. Primary source index

### Project / package / design
- https://github.com/strands-agents/harness-sdk
- https://github.com/strands-agents/harness-sdk/blob/main/strands-py/pyproject.toml
- https://github.com/strands-agents/harness-sdk/blob/main/team/TENETS.md
- https://github.com/strands-agents/harness-sdk/blob/main/team/designs/0009-mono-repository.md
- https://github.com/strands-agents/harness-sdk/blob/main/team/designs/0006-cedar-authorization.md
- https://github.com/strands-agents/harness-sdk/blob/main/team/designs/0004-stateful-models.md

### Runtime / tools / intervention
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/agent-loop.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/retry-strategies.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/structured-output.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/strands-py/src/strands/tools/structured_output/structured_output_tool.py
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/tools/custom-tools.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/interventions/index.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/strands-py/src/strands/vended_interventions/cedar/cedar_authorization.py
- https://github.com/strands-agents/harness-sdk/issues/3877

### Sandbox / execution
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/sandbox/index.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/sandbox/available-sandboxes.mdx
- https://github.com/strands-agents/harness-sdk/issues/4156
- https://github.com/strands-agents/harness-sdk/commit/e448bea9e42298b31047ac8d2a616b29819563c1

### Persistence / context / interrupts
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/snapshots.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/session-management.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/safety-security/trusted-message-history.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/interrupts.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/agents/conversation-management.mdx
- https://github.com/strands-agents/harness-sdk/issues/4198
- https://github.com/strands-agents/harness-sdk/issues/4102
- https://github.com/strands-agents/harness-sdk/issues/4004
- https://github.com/strands-agents/harness-sdk/issues/4171

### Local models / observability / evaluation
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/concepts/model-providers/ollama.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/strands-py/src/strands/models/ollama.py
- https://github.com/strands-agents/harness-sdk/blob/main/strands-py/tests_integ/models/test_model_ollama.py
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/observability-evaluation/traces.mdx
- https://github.com/strands-agents/harness-sdk/blob/main/site/src/content/docs/user-guide/evals-sdk/quickstart.mdx
- https://github.com/strands-agents/harness-sdk/commit/ed05dcff0223fa30593988ebc4eb36d4eb01fb63

---

## Final assessment

Strands earned its #5 research position.

It provides the clearest current example in this campaign of a model-driven harness surrounded by **separable deterministic control planes**:

- lifecycle limits;
- retry control;
- typed tool contracts;
- structured correction;
- typed interventions;
- principal-aware action authorization;
- explicit HITL interrupt IDs;
- pluggable execution isolation;
- state snapshots/session persistence;
- context management;
- local-model adapters;
- standardized traces;
- framework-native evaluation.

The most reusable lesson is architectural rather than framework-specific:

> Give the model freedom to propose and reason, but force every important transition—authority, execution, persistence, resume, approval, and acceptance—through a deterministic, observable boundary with stable identity.

The strongest warnings are equally concrete:

- persistence needs a distributed writer/lease story;
- restored state is trusted execution input and must have provenance/integrity controls;
- action authorization does not guarantee objective integrity;
- an explicit sandbox still needs environment provisioning/governance;
- remote/provider state can outlive local state;
- interrupt/hook replay can duplicate behavior unless transitions are idempotent;
- traces and UI streams are representations, not automatically authoritative truth;
- local model support must be benchmarked as an exact model/runtime/adapter/configuration combination.

For later build-versus-reuse work, Strands should remain a serious candidate for selective mechanism reuse or a thin pinned adapter. This task does **not** establish that ACL should adopt the framework wholesale, and it does not rank Strands against Pydantic AI, Cline, LangGraph, or promptfoo.

**Task boundary:** Strands research is complete. Codex research has not begun.
