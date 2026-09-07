# Agno deep research

**Task:** 28
**Project:** `agno-agi/agno`
**Research date:** 2026-09-07
**Scope:** research only; no adoption, model assignment, benchmark execution, or ACL/Vera implementation decision

## Executive assessment

Agno is a broad agent-platform framework and runtime rather than a narrow agent loop. Its current architecture spans `Agent`, `Team`, `Workflow`, persistent storage, memory/knowledge, human-in-the-loop continuation, AgentOS service interfaces, MCP, A2A, authentication/authorization, tracing/evaluation, scheduling, and a stateful CodeMode execution environment.

For ACL/Vera, Agno is especially valuable as reference material for three classes of mechanism:

1. **Explicit orchestration surfaces.** Agents, teams, workflows and AgentOS are distinct runtime layers, with multiple team modes and structured workflow primitives.
2. **Capability-aware state machinery.** DB-backed Agno FileSystem supports atomic compare-and-set while local filesystem backends explicitly reject unsupported CAS; Studio uses immutable versions plus optional `expected_version` guards.
3. **Fail-closed protocol publication.** Current AgentOS MCP configuration refuses approval-dependent tools rather than exposing them through a direct MCP path that bypasses the normal approval machinery.

Agno is not a substitute for ACL's control plane. Current 2026 failures show unresolved or recently fixed correctness/security boundaries in same-session concurrent persistence, mixed sync/async cancellation, parent/child pause/cancel consistency, destructive memory scoping, credential forwarding to model-selected destinations, async cleanup settlement, provider-adapter error classification, and raw tool-content trust.

Latest stable observed release is **v3.0.6**, published 2026-09-04. Current `main` observed during Task 28 is `d703c34f3abf3c41275d3fb2da6e0518a8881f24`, also reporting package version **3.0.6**, but containing post-release fixes. Release tag and current main are therefore separate qualification profiles despite sharing the package version string.

## 1. Project identity and current generation

### Observed fact

- Latest stable release observed: **v3.0.6**, published 2026-09-04.
- Current `main` observed: `d703c34f3abf3c41275d3fb2da6e0518a8881f24`, dated 2026-09-07.
- `libs/agno/pyproject.toml` reports `version = "3.0.6"`.
- The project describes itself as a framework and runtime for agent platforms, with the Agno SDK, AgentOS runtime and AgentOS UI.
- AgentOS exposes production APIs, persistent storage, integrations/context providers, HITL, observability, authentication/authorization, scheduling and protocol/interface surfaces.

### ACL implication

The package version string alone is insufficient benchmark/deployment identity. A useful manifest must retain the exact release/tag or commit because current main can contain behavior-bearing fixes while still identifying as the same package version.

### Candidate invariant

Record at minimum:
- Agno release/tag and commit;
- `Agent`/`Team`/`Workflow` topology and TeamMode;
- AgentOS/runtime interface profile;
- model adapter class and exact provider/runtime/model;
- session/storage/database backend;
- memory/knowledge configuration;
- MCP/A2A protocol/profile;
- tool/hook/HITL configuration;
- code-execution profile;
- tracing/eval profile;
- authorization and user-isolation profile.

## 2. Runtime architecture: Agent, Team, Workflow and AgentOS

Agno deliberately separates several layers that ACL should also keep conceptually distinct.

### Agent

`Agent` owns model interaction, tools, session/history options, memory/knowledge integration, callbacks/hooks, run lifecycle and persistent storage integration.

### Team

Current `TeamMode` defines four orchestration profiles:
- `coordinate`: supervisor selects members, crafts tasks and synthesizes results;
- `route`: leader routes to a specialist and returns that member response;
- `broadcast`: sends the same task to all members; async execution is concurrent while sync is sequential;
- `tasks`: leader decomposes into a shared task list and continues delegation until completion.

These are behavior-bearing harness profiles, not cosmetic modes.

### Workflow

Current workflow primitives include `Step`, `Steps`, `Loop`, `Parallel`, `Condition`, `Router` and nested `Workflow` execution. Workflows also support pause/continue behavior around HITL and persist run/executor state.

### AgentOS

AgentOS is the service/control-plane layer. It can expose REST/SSE/WebSocket interfaces, MCP, A2A and other channels, apply authentication/authorization, manage registry/configuration, serve sessions/runs and store traces/evals.

### ACL implication

Do not collapse these identities:
- component definition;
- team/workflow topology;
- one component invocation;
- session/conversation;
- protocol request;
- remote task;
- ACL task/run;
- external effect.

A team member's run ID or workflow step ID is not automatically an ACL effect/idempotency ID.

## 3. Team delegation and durable writer ownership

Agno's team design exposes both a useful principle and a current failure mode.

### Useful principle: root-owned durable session writes

Issue #9348's root-cause analysis describes an intentional guard in nested teams: only the root team reads/writes persistent session state, avoiding duplicate database writes from nested subteams. This is directionally aligned with ACL's one-authoritative-writer invariant.

### Current problem: readable state does not follow the hierarchy correctly

Issue #9348 reports nested subteams losing multi-turn history because:
- nested teams skip DB loading when `parent_team_id` is present;
- delegation propagates a session ID rather than the live session object/read view;
- the nested session begins with an empty run list;
- history traversal is shallow and does not recursively find deeper member responses.

### ACL implication

**Single writer does not mean single reader.** A durable domain can retain one writer while children receive immutable/read-only snapshots or parent-linked views. Writer authority and read visibility are separate concerns.

### Candidate invariant

For each shared state domain define:
- authoritative writer;
- immutable version/read view supplied to children;
- child mutation proposal mechanism;
- merge/commit owner;
- revision/CAS/lease/fencing rule;
- audit trail.

## 4. Same-session persistence and concurrent writers — issue #7479

Open issue #7479 reports silent run loss when concurrent `arun()` calls share one `session_id` on PostgreSQL.

Reported sequence:
1. each run loads the same session snapshot;
2. each appends its own run in memory;
3. each later writes the complete JSONB `runs` array;
4. the last writer overwrites the other run without an error.

This is a storage-layer lost-update race rather than a model failure.

### ACL implication

Append-oriented history cannot safely use stale-snapshot + whole-document last-writer-wins writes under concurrency.

For ACL/Vera authoritative history, prefer one of:
- append-only run/event rows with unique IDs;
- database transaction + row lock;
- compare-and-set revision;
- one serialized session writer;
- lease/generation fencing for distributed writers.

### Regression fixture

Two concurrent runs with the same durable session ID must leave both immutable run records present or return an explicit conflict/retry state. Silent loss is failure.

## 5. Cancellation ownership — issue #10015

Open issue #10015, filed 2026-09-07, is reproduced against Agno 3.0.6/main. The in-memory cancellation manager uses a `threading.Lock` for synchronous methods and a separate `asyncio.Lock` for asynchronous methods while both mutate the same dictionaries.

A legal interleaving can therefore:
- register a run asynchronously;
- cancel it synchronously;
- let the async registration overwrite the cancellation flag back to false.

The same class can lose team-member cancellation mappings.

### ACL implication

A single logical state domain cannot be protected by independent synchronization domains merely because callers are sync versus async.

Cancellation intent should be monotonic or atomically versioned. Once a valid cancellation wins, a stale registration must not resurrect the run.

### Candidate invariant

`cancel_epoch >= registration_epoch` or equivalent CAS/fencing semantics must survive mixed API access. Cancellation request, cancellation acknowledgement, worker/process termination, effect settlement and final durable state remain distinct.

## 6. Parent/child completion and stream settlement — issue #7294

Issue #7294 reports team members completing normally while parent `delegate_task_to_member` tool-call completion events remain open for roughly 60 seconds before the enclosing run proceeds.

### ACL implication

Preserve distinct lifecycle markers for:
- child content completion;
- child run completion;
- parent delegation/tool-call completion;
- parent stream closure;
- parent run completion;
- external-effect settlement.

A finished child does not prove the delegation edge has settled, and an open stream does not prove the child is still working.

## 7. Workflow pause/cancel/resume consistency — issues #8910 and #9278

Current 2026 issues document inconsistent composite workflow state around HITL:
- workflow remains `PAUSED`;
- executor sub-run becomes `CANCELLED`;
- resume finds the cancelled sub-run and rejects continuation with `RunNotContinuableError`.

One issue states the invariant directly: a `PAUSED` workflow must not contain a `CANCELLED` executor sub-run when that child is the continuation target.

### ACL implication

Durable state can still be internally inconsistent. Persisting a status does not make it a safe continuation checkpoint.

Before resume, ACL should validate cross-level invariants across:
- parent task/run;
- child executions;
- outstanding approvals/HITL requirements;
- process settlement;
- workspace revision;
- effect ledger;
- current credentials/policy.

### Candidate invariant

Composite lifecycle transitions commit atomically where possible; otherwise reconciliation produces an explicit `inconsistent_requires_repair` state rather than attempting normal resume.

## 8. Memory architecture and authority

Agno has a first-class `MemoryManager` backed by database `UserMemory` records and an LLM-based memory-management path. The manager can add, update and delete memories and can expose model-facing memory-management tools.

If no memory-management model is provided, current source defaults to OpenAI `gpt-4o`.

### ACL/Vera implications

1. Memory model selection is deployment/data-egress identity. A local/offline system must explicitly configure the memory model; setting only the primary agent model is insufficient.
2. `user_id` is storage partition metadata unless tied to authenticated host identity.
3. Falling back to a generic/default user can be convenient for single-user development but must not define an authoritative multi-user domain.
4. LLM-produced memory remains an evidence-derived claim, not verified truth.

Vera still requires provenance, source trust, confidence, conflict and supersession policy outside the backend.

## 9. Destructive memory scope — issue #9983

Open issue #9983 is one of the highest-value Task 28 fixtures. It demonstrates the current model-facing `clear_memory` closure calling unscoped `db.clear_memories()`.

The issue reproduces two users sharing one database. A call made through one user's memory-management tool removes the other user's memories as well. Current source corroborates the unscoped closure.

The exact enablement defaults vary by construction path, so the important conclusion is narrower:

**when this LLM-facing clear tool is enabled, its current effect target is database-global rather than caller-scoped.**

### ACL/Vera implication

Destructive memory effects must bind:
- authenticated principal;
- memory domain/tenant;
- target object or collection scope;
- operation kind;
- current policy/approval;
- effect ID and audit record.

A low-level global database API must not become model authority merely because a toolkit exposes it.

### Candidate regression fixture

Seed two principals, authorize a clear for one, and prove the second principal's state survives. Test every sync/async, REST/MCP/tool surface separately.

## 10. CodeMode: persistent execution is not a sandbox

Current `CodeMode` is a persistent per-session IPython kernel. It can execute Python and shell, preserve variables/imports/functions across turns, and optionally snapshot state.

Upstream states explicitly:
- CodeMode executes with the permissions of the hosting process;
- it is **not a sandbox**;
- use it with a trusted operator or in an isolated container.

### Executable snapshots

CodeMode snapshots use `dill` pickles. Restoring a snapshot is code execution, so the snapshot store itself is an executable trust artifact.

### Namespace behavior

The kernel/snapshot is keyed by `session_id`. A team leader and members sharing one CodeMode instance and team session can share the same kernel namespace. Multiple CodeMode instances using the same FileSystem/session namespace can restore each other's variables unless separated intentionally.

### ACL implication

CodeMode is useful as a reference for stateful worker execution, but ACL must own:
- OS/container isolation;
- process user/capabilities;
- mounts/workspace;
- network policy;
- credentials/environment;
- kernel/process ownership;
- snapshot provenance/signing/trust;
- teardown settlement.

Persistent interpreter state is runtime state, not a safe checkpoint.

## 11. Positive concurrency pattern: FileSystem CAS and immutable Studio versions

Current Agno FileSystem has a useful capability-aware design.

### DB-backed FileSystem

DB-backed writes support:
- atomic upsert;
- optional compare-and-set via `expected_version`;
- serialized/guarded append;
- concurrency tests.

### Local FileSystem

The local backend explicitly rejects `expected_version` rather than pretending to supply an atomic guarantee it does not have.

### Studio

Studio editing uses immutable draft/published versions and optional `expected_version` CAS to detect concurrent edits. A mutable current-version pointer can select among immutable versions.

### ACL reuse candidate

Borrow two patterns:
1. **capability honesty:** unsupported concurrency guarantees fail explicitly;
2. **immutable revisions + guarded head update:** mutating a logical object creates a new revision, while moving the current pointer requires revision-aware validation.

Do not generalize this to Agno sessions: issue #7479 shows ordinary session/run persistence has different concurrency semantics.

## 12. Tool authority and credential-to-destination binding — issue #8620

Open issue #8620 reproduces a URL-capable toolkit where constructor-level `Authorization`/`Cookie` headers are reused with a URL selected by the tool call.

The consequence is an authority composition problem: the model controls destination while the host-supplied toolkit carries credentials.

### ACL implication

Credential selection and destination authorization are one decision.

A service grant should bind at least:
- credential/service identity;
- allowed host/audience;
- method/action;
- data scope;
- expiry;
- principal/task/effect identity.

Never attach reusable credentials to a generic model-controlled URL capability without destination enforcement.

## 13. External-send authority — issue #8847

Issue #8847 raises a closely related design concern for an email-sending toolkit: the model can supply arbitrary recipients/content while the toolkit holds the host's sending credential.

The report is largely static-analysis/design evidence rather than a demonstrated framework escape, so Task 28 does **not** classify it as a proven Agno security vulnerability.

It is still a useful ACL threat fixture:
- sending external data is an effect;
- destination is authority-bearing;
- content may contain sensitive data;
- confirmation/allowlisting/declassification policy can be appropriate depending on risk.

## 14. Tool results and prompt injection — issue #8494

Issue #8494 highlights the ordinary agentic risk that external tool output becomes later model context and can carry adversarial instructions.

Boundary markers or escaping can improve representation clarity but do not make the content semantically trustworthy.

### ACL/Vera invariant

Tool output, retrieved documents, memory, MCP resources and remote-agent messages remain **untrusted data**. They may influence reasoning but cannot directly acquire:
- policy authority;
- credential authority;
- tool/effect authorization;
- verifier authority;
- trusted memory status.

Prompt injection defense should rely primarily on capability separation, least privilege, provenance, explicit effect authorization and independent verification—not a claim that text sanitization makes arbitrary external content safe.

## 15. Provider/local-model portability

Agno has broad model adapters including native Ollama support and multiple cloud/provider classes.

Current source includes:
- native Ollama chat adapter;
- Ollama Responses adapter using Ollama's OpenAI-compatible `/v1/responses` surface;
- Ollama embeddings;
- many OpenAI-style and provider-specific adapters.

### Exact profile matters

Native Ollama chat, Ollama Responses, OpenAI-compatible adapters and other providers are distinct profiles. Tool/schema/streaming/context/compression behavior may differ.

### Current provider regression: #9034 / #10031

Issue #9034 documented an adapter `_format_message` signature mismatch. Current main commit #10031 fixes the same class of defect for `LlamaOpenAI` and states that the model layer had swallowed the `TypeError` into the response, returning error text as the assistant answer instead of failing loudly.

This is a critical benchmark lesson:

**provider/harness failure must never be reclassified as successful model output simply because text was produced.**

### ACL fixture

Inject an adapter exception at request formatting/stream parsing/tool compression and require:
- typed provider/harness failure;
- no semantic success result;
- no verifier pass;
- no automatic effect replay;
- complete attempt provenance.

## 16. Tool-result compression/offloading is behavior-bearing state

The current #10031 fix specifically forwards `compress_tool_results`; accepting the new parameter without forwarding it would avoid a crash while silently disabling compression and increasing context size.

Issue #9680 further documents that Agno currently refuses to enable tool-result offloading and compression together because combining them could corrupt result references.

### ACL implication

Context-management features belong in benchmark identity. A profile includes:
- history policy;
- compression policy/model;
- result offloading/storage;
- truncation limits;
- retained result IDs/references.

Failing loudly on an unsupported feature combination is preferable to silently changing semantics.

## 17. Cleanup and persistence settlement — issues #9680 and #9829

Maintainer-tracked #9680 records several lifecycle gaps relevant to ACL:
- deleting a run does not necessarily cascade stored result payload deletion;
- custom filesystem payloads can remain orphaned when cleanup lacks backend reconstruction;
- one-shot async processes can lose the final CodeMode snapshot;
- result-store access can be weaker when caller identity is absent.

Focused issue #9829 explains the async cleanup problem: async Agent/Team execution may call synchronous `close()` on connectable tools. For CodeMode, that can schedule the final snapshot flush in the background; immediate process/event-loop shutdown can then lose the snapshot.

### ACL implication

`run returned` is not synonymous with `durable state settled`.

Async lifecycle completion should await:
- tool/resource close;
- subprocess/kernel termination or deliberate retention;
- snapshot/checkpoint flush;
- output/evidence persistence;
- external-effect reconciliation.

If any required settlement fails, the run should end in an explicit degraded/uncertain state.

## 18. MCP: protocol generation, surface identity and fail-closed publication

Agno v3.0.6 introduced important MCP profile distinctions.

### Protocol/transport profiles

- `MCPTools(protocol_mode="legacy")` preserves session-based behavior by default.
- `protocol_mode="auto"` can negotiate modern sessionless behavior beginning with the 2026-07-28 protocol era.
- `MCPConfig(stateless=True)` removes transport session tracking so any replica can serve a request, but sacrifices session-dependent capabilities such as server notifications/SSE resumability.

MCP mode therefore belongs in deployment/benchmark identity.

### Strong fail-closed pattern

Current `MCPConfig` documentation/source states direct MCP custom-tool calls bypass normal `FunctionCall` approval machinery. Instead of silently losing safeguards, AgentOS refuses to publish functions requiring confirmation/user input/external execution on that surface.

This is a strong reuse candidate:

**if a transport cannot faithfully preserve a required control, reject the capability rather than silently downgrade it.**

### Additional identity controls

Current MCP surface also:
- collision-checks tool names;
- can inject authenticated caller `user_id` into hidden parameters;
- supports an explicit `authorize` callback;
- can validate Host/Origin for DNS-rebinding defense;
- distinguishes trimmed versus full result projection.

### ACL boundary

MCP transport/session identity still does not equal Agno session/run identity or ACL task/effect authority.

## 19. A2A and remote lifecycle status

Agno includes A2A server/client support with Agent Cards and send/stream operations.

Current cookbook material notes a non-streaming remote A2A case where content maps correctly while status can retain `RUNNING` from the task while it was in flight.

### ACL implication

Remote content and remote lifecycle status are separately validated. A valid final-looking payload does not prove remote task settlement.

A2A task/context IDs remain protocol-routing identifiers rather than bearer credentials, effect IDs or continuation authority.

## 20. AgentOS authorization and user isolation

Agno exposes JWT/RBAC support and user-isolation middleware. Current source makes an important distinction: `AuthorizationConfig(user_isolation=True)` is opt-in; without it, or for admins, the DB can remain unscoped by user.

### ACL implication

Authentication, RBAC and data-domain isolation are separate controls. A valid identity/token does not automatically imply every database/tool query is principal-scoped.

### Issue #9741

Open issue #9741 reports two AgentOS security-key comparison paths using ordinary string equality rather than the constant-time comparison already used elsewhere in the codebase.

This is a narrower service-auth regression fixture, but it reinforces a broader rule: REST, WebSocket, MCP and A2A auth paths must be qualified independently and share authoritative security primitives rather than drift.

## 21. Missing identity must not weaken access control

Several Agno paths make the semantics of absent identity consequential:
- MemoryManager often has a convenient `"default"` user fallback.
- #9680 documents a result-store read rule that can allow access when the stored row has a user but the caller provides no user ID.
- MCP `authorize` receives `None` if JWT auth is not configured, leaving application policy to decide whether anonymous access is acceptable.

### Vera/ACL invariant

In authoritative multi-user domains, identity absence fails closed or maps only to a deliberately isolated anonymous/dev domain. It must never broaden access relative to an authenticated principal.

## 22. Observability and evaluations

Agno has first-class tracing using OpenInference/OpenTelemetry and can persist traces/spans to database backends separate from transactional session storage.

Its evaluation subsystem includes at least:
- accuracy evaluation;
- performance evaluation;
- reliability evaluation.

These are useful evidence and benchmarking mechanisms.

### ACL boundary

The system under test cannot own authoritative pass/fail. ACL should preserve:
- verifier/evaluator definition/version;
- exact model/harness/runtime profile;
- deterministic host evidence;
- stochastic trial distribution;
- separate transport/harness/model/effect failure classification.

Operational traces may contain sensitive prompts, tool data, memory and identifiers and need separate audience/retention policy.

Agno's README also states its own product telemetry sends a per-agent-run event but does not send prompts, messages or outputs; deployments requiring no telemetry should still pin/configure `AGNO_TELEMETRY=false` and verify realized behavior.

## 23. Reproducibility and benchmark identity

For any future ACL evaluation of Agno, record:
- Agno exact tag/commit;
- Python/dependency lock and OS/container;
- Agent versus Team versus Workflow topology;
- TeamMode/workflow graph;
- AgentOS versus direct SDK surface;
- model adapter class and provider endpoint;
- exact model/runtime artifact;
- native versus compatible API path;
- session/storage database and concurrency mode;
- history/memory/knowledge configuration;
- compression/offload settings;
- tool set + origin/schema/revision;
- HITL/hook profile;
- MCP protocol/stateless/auth configuration or A2A profile;
- CodeMode/sandbox profile;
- credentials/network/mount policy;
- tracing/eval configuration.

Do not score #7479/#10015/#9034-class harness failures against the model.

## 24. Candidate ACL/Vera invariants derived from Agno

1. One package version string is not sufficient identity when post-release commits retain that version.
2. Agent definition, team definition, workflow definition, invocation, session and effect are distinct IDs.
3. Team/workflow mode is benchmark identity.
4. One durable state domain has one authoritative writer or an explicit CAS/lease/fencing protocol.
5. Single writer and child read visibility are separate concerns.
6. Append history is atomic/event-oriented; whole-array last-writer-wins is not authoritative concurrency control.
7. Sync and async entry points mutating one state domain share one synchronization authority.
8. Cancellation intent is monotonic/versioned and cannot be overwritten by stale registration.
9. Parent and child lifecycle states satisfy explicit cross-level invariants before resume.
10. `PAUSED` state is not sufficient continuation evidence without child/workspace/effect validation.
11. Destructive memory operations bind to authenticated scope; database-global clears are admin-only effects.
12. Missing identity does not broaden access or silently join unrelated users in a default authoritative domain.
13. LLM-produced memory is a claim, not truth.
14. Memory-management model/provider is part of data-egress and reproducibility identity.
15. Stateful Python/shell execution is never treated as containment merely because it has a kernel/session abstraction.
16. Pickle/dill snapshots are executable artifacts requiring trusted provenance and protected storage.
17. Persistent execution state is not a continuation checkpoint by itself.
18. Backends explicitly declare whether CAS/atomic append is supported; unsupported guarantees fail closed.
19. Mutable logical configuration points to immutable versions where practical.
20. Credential grant and outbound destination are one authorization decision.
21. External-send destinations/content are effect-bearing inputs.
22. Tool/retrieved/memory/remote-agent content remains untrusted data regardless of formatting.
23. Provider/adapter exceptions are typed failures, never successful assistant text.
24. Context compression/offloading/history policy is benchmark identity.
25. Unsupported combinations of context/state features fail loudly rather than silently corrupting references.
26. Async run completion awaits required resource close and durable flush.
27. Run deletion and erasure account for detached payload/index/snapshot state.
28. Same logical tool exposed through Agent/REST/MCP/A2A is a distinct surface profile if hooks/approval/auth/lifecycle differ.
29. Required controls that cannot survive a protocol surface cause capability rejection rather than silent downgrade.
30. Protocol task/session IDs remain distinct from effect/idempotency/auth identities.
31. Authentication, RBAC, tenant isolation and effect authorization are separate controls.
32. Runtime traces/evals are evidence, not independent acceptance authority.

## 25. Regression fixture shortlist

1. **#7479** — same-session concurrent persistence loses one run.
2. **#9348** — nested subteam history disappears despite shared higher-level session.
3. **#10015** — mixed sync/async locks lose cancellation intent/member mapping.
4. **#7294** — child completion precedes parent delegation completion by timeout-scale delay.
5. **#8910/#9278** — workflow PAUSED while continuation child is CANCELLED.
6. **#9983** — one principal's memory clear reaches other principals.
7. **CodeMode** — prove local process authority is not mistaken for sandboxing.
8. **CodeMode snapshot** — reject untrusted dill snapshot and verify snapshot provenance policy.
9. **#8620** — credential-bearing headers cannot follow a model-selected untrusted URL.
10. **#8494** — hostile tool content cannot grant effect/policy/credential authority.
11. **#9034/#10031** — adapter exception cannot become semantic success output.
12. **#9680/#9829** — async completion cannot precede required snapshot/result-store settlement.
13. **MCP direct-tool publication** — approval-required tool must fail closed on a surface that cannot preserve approval.
14. **MCP protocol profile** — legacy/sessionful versus auto/stateless behavior is separately qualified.
15. **A2A remote status** — content completion cannot imply lifecycle settlement when status remains running.
16. **#9741** — all service-auth surfaces use the intended secret-validation primitive.
17. **FileSystem CAS** — stale expected version returns conflict, not silent overwrite.
18. **Local FileSystem CAS** — unsupported atomic guarantee fails explicitly.

## 26. Reuse candidates

High-value mechanisms for later comparison, without adopting Agno wholesale:
- explicit Agent/Team/Workflow layering;
- TeamMode as named orchestration profiles;
- structured workflow primitives;
- root-authoritative durable writer concept for nested execution;
- DB FileSystem CAS/atomic append semantics;
- immutable component versions + guarded current-version pointer;
- MCP fail-closed refusal when required FunctionCall controls cannot execute;
- hidden authenticated-user injection into tool arguments;
- explicit MCP protocol/stateless profile knobs;
- trimmed versus full remote result projection;
- OpenTelemetry/OpenInference trace model;
- separate accuracy/performance/reliability eval classes;
- CodeMode's explicit warning that persistent execution is not containment.

## 27. Explicit non-conclusions

Task 28 does **not** conclude that:
- ACL should adopt, fork or reject Agno;
- Agno is the preferred harness or orchestration framework;
- AgentOS should become ACL's control plane;
- Agno Team `tasks` mode should become ACL's foreman;
- Agno memory should become Vera's memory backend;
- CodeMode should execute ACL worker code;
- Agno's current RBAC/user-isolation configuration is sufficient for ACL/Vera;
- Agno's eval subsystem is ACL's verifier;
- any Agno-supported model/provider has passed ACL's future 32K qualification;
- Ollama support implies exact local-model/tool/context correctness;
- MCP/A2A interoperability implies authority or checkpoint equivalence;
- current open issues affect every Agno deployment/profile equally.

Agno remains below ACL-owned task/effect identity, sandbox/process custody, credential broker, durable checkpoint/reconciliation authority, writer fencing and independent verifier. Vera additionally retains epistemic provenance/truth/supersession and privacy/erasure authority.

## 28. Sources

Primary upstream sources reviewed on 2026-09-07:

- Repository: https://github.com/agno-agi/agno
- README: https://github.com/agno-agi/agno/blob/main/README.md
- v3.0.6 release: https://github.com/agno-agi/agno/releases/tag/v3.0.6
- Current package config: https://github.com/agno-agi/agno/blob/main/libs/agno/pyproject.toml
- Team modes: https://github.com/agno-agi/agno/blob/main/libs/agno/agno/team/mode.py
- AgentOS/MCP configuration: https://github.com/agno-agi/agno/blob/main/libs/agno/agno/os/config.py
- CodeMode: https://github.com/agno-agi/agno/blob/main/libs/agno/agno/tools/code/code_mode.py
- MemoryManager: https://github.com/agno-agi/agno/blob/main/libs/agno/agno/memory/manager.py
- FileSystem base/DB/local: https://github.com/agno-agi/agno/tree/main/libs/agno/agno/fs
- OpenTelemetry tracing: https://github.com/agno-agi/agno/tree/main/libs/agno/agno/tracing
- Evaluations: https://github.com/agno-agi/agno/tree/main/libs/agno/agno/eval
- Issue #7479: https://github.com/agno-agi/agno/issues/7479
- Issue #9348: https://github.com/agno-agi/agno/issues/9348
- Issue #10015: https://github.com/agno-agi/agno/issues/10015
- Issue #7294: https://github.com/agno-agi/agno/issues/7294
- Issues #8910/#9278: https://github.com/agno-agi/agno/issues/8910 and https://github.com/agno-agi/agno/issues/9278
- Issue #9983: https://github.com/agno-agi/agno/issues/9983
- Issue #8620: https://github.com/agno-agi/agno/issues/8620
- Issue #8494: https://github.com/agno-agi/agno/issues/8494
- Issue #8847: https://github.com/agno-agi/agno/issues/8847
- Issue #9741: https://github.com/agno-agi/agno/issues/9741
- Issue #9680: https://github.com/agno-agi/agno/issues/9680
- Issue #9829: https://github.com/agno-agi/agno/issues/9829
- Issue #9034: https://github.com/agno-agi/agno/issues/9034
- Current main fix #10031: https://github.com/agno-agi/agno/pull/10031

## Stop boundary

Task 28 ends with Agno research and documentation. No LlamaIndex research, comparative winner selection, model/runtime assignment, 32K benchmark execution, or ACL/Vera implementation/governance change is included.