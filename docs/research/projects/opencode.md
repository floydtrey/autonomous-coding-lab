# OpenCode deep research

**Task:** 25 — OpenCode only  
**Canonical project:** `anomalyco/opencode`  
**Research date:** 2026-09-07  
**Scope:** research only; no adoption, fork, model assignment, benchmark execution, or ACL/Vera implementation change

## Executive assessment

OpenCode is a high-value ACL reference because it is not merely a coding CLI: it is an agent/harness runtime with sessions, tools, permissions, provider abstraction, MCP integration, server/client surfaces and a fast-moving runtime architecture. The most important qualification finding is that the project is currently crossing a major architecture boundary. The stable line observed during Task 25 is **v1.18.29**, while the default `dev` branch contains an active V2 redesign of runtime, session/event and permission mechanisms. Those two profiles must not be blended into one capability claim.

OpenCode also makes its security boundary unusually clear: its agent is **not sandboxed**. Its permission system is an awareness/confirmation mechanism, not an OS isolation mechanism. That distinction fits the strongest cross-project ACL invariant accumulated so far: model/tool policy and user approval are not containment. Any future OpenCode worker candidate would therefore need to run inside ACL-owned filesystem/process/network/credential isolation.

Two current stable failure reports are especially valuable as future ACL regression fixtures. **#47605** shows a malformed or missing response `Content-Type` can bypass the body watchdog and leave a session busy indefinitely. **#47727** shows `serve` can retain per-directory instances and MCP child processes until memory exhaustion. These are not model-quality failures; they are harness lifecycle/ownership failures.

Task 25 supports selective mechanism comparison. It does **not** support adopting or forking OpenCode, treating V2/dev behavior as stable, replacing ACL's scheduler/effect ledger/sandbox/verifier with OpenCode, or starting Mem0 research.

## 1. Identity, release and architecture-generation boundary

The canonical upstream is `anomalyco/opencode`. The stable release observed during Task 25 is **v1.18.29**. At the same time, the default upstream development branch is carrying an active **V2** redesign. That means `OpenCode` by itself is not a sufficiently precise runtime identity.

For ACL benchmarking or later dependency evaluation, the behavior-bearing identity should include at minimum:

- exact OpenCode release/commit;
- stable-V1 versus V2/dev profile;
- provider adapter/model/runtime endpoint;
- session/runtime mode (CLI/server/client surface);
- enabled tools, permissions and MCP servers;
- workspace/process environment and external sandbox profile;
- timeout/retry/cancellation settings;
- any behavior-bearing feature flags or migration mode.

A mechanism observed only on V2/dev should be labeled **development/proposed/current-main behavior**, not a stable guarantee. Conversely, a stable V1 defect should not automatically be assumed present after the V2 redesign without fresh evidence.

### ACL implication

Harness/version/profile identity belongs beside model/runtime identity in every benchmark and deployment record. A same-model comparison across two OpenCode generations can be a harness comparison, not a model comparison.

## 2. Runtime shape: agent harness rather than thin CLI

OpenCode owns substantially more than prompting. The current project exposes the familiar coding-agent responsibilities expected of a harness/runtime: provider/model interaction, session state, tool execution, permissions, MCP integration, server/client behavior and event/session lifecycle.

This matters for ACL because OpenCode could later be evaluated in several materially different roles:

1. **Full worker harness candidate** — ACL supplies the outer project/task authority and containment while OpenCode owns the inner coding-agent loop.
2. **Pattern/reference only** — borrow lifecycle/session/tool ideas without taking a runtime dependency.
3. **Nested agent surface** — use OpenCode through a server/client boundary, which adds process/resource/network lifecycle that must be qualified independently.

Task 25 makes no choice among those roles.

## 3. Stable V1 versus V2/dev session and event model

The V2 development work is important because it strengthens the explicit runtime/session/event model, but it is still an architecture transition rather than a stable compatibility promise. For ACL, the durable lesson is not a particular V2 API. It is that session history, event delivery, runtime ownership and continuation state are separate responsibilities that need explicit identity and lifecycle.

A durable OpenCode transcript or session should therefore not be treated as an ACL continuation checkpoint. ACL still needs to know whether:

- the workspace is in the expected state;
- subprocesses/MCP servers are settled;
- external effects are completed, failed or uncertain;
- current credentials/policy are still valid;
- the same authoritative worker owns the run;
- required verifier/evidence state is intact.

### Candidate invariant

**Session/event durability is evidence of conversation/runtime state, not permission to continue external work.** ACL continuation remains an outer, explicitly validated state transition.

## 4. Permission model and security boundary

OpenCode's upstream security guidance explicitly states that the agent is **not sandboxed**. Permission prompts/rules therefore belong in the same category as other application-level approval systems researched in Cline, Goose, Gemini CLI, MAF and ADK: useful control/awareness, but not containment.

For ACL this produces a firm boundary:

- OpenCode may propose actions or request permission.
- OpenCode permission state may be useful operator UX/evidence.
- OpenCode must not be the final authority over filesystem/process/network/credential reach.
- ACL-owned OS/container/VM/process boundaries must determine what the worker can actually do.
- Protected ACL policy, verifier, credential and checkpoint roots must remain outside the OpenCode worker's write authority.

### Candidate invariant

**Approval/policy never upgrades confinement.** A permitted tool call is still restricted by the worker's external sandbox/capability ceiling.

## 5. Tool and MCP authority

OpenCode's MCP support is directly relevant because an MCP server is both a tool origin and a child/resource lifecycle boundary. Tool display names alone are not sufficient identity. A future ACL adapter should bind a proposed effect to:

- trusted OpenCode worker identity/profile;
- MCP server origin/instance identity where applicable;
- tool definition/schema digest;
- normalized arguments;
- ACL project/task/run/effect ID;
- current policy/approval state.

MCP child processes also need lifecycle ownership independent of whether the OpenCode session remains logically active. Stable issue #47727 makes that distinction concrete.

## 6. Provider and local-model portability

OpenCode is provider-oriented rather than tied to one hosted model, making it potentially relevant to ACL's local-first worker experiments. But Task 25 does not treat provider labels or OpenAI-compatible endpoints as capability guarantees.

The same rules established by Ollama, llama.cpp, LiteLLM, ADK and vLLM research carry forward:

- exact adapter/runtime/model identity matters;
- tool calling, streaming, structured output and context need separate qualification;
- requested settings and realized wire/runtime behavior can diverge;
- retry/cancellation semantics are adapter-specific;
- harness behavior is part of benchmark identity.

A later OpenCode local-model benchmark would therefore need the same frozen 32K-style deployment manifest as any other harness, rather than comparing by model name alone.

## 7. Timeout and transport lifecycle — issue #47605

**Current stable regression fixture:** `anomalyco/opencode#47605`.

The reported failure class is that a malformed or absent HTTP response `Content-Type` can bypass the body watchdog path, leaving the session in a persistent busy state rather than reaching a terminal error. The high-value point is architectural: a transport metadata branch can accidentally own whether a deadline is enforced.

### ACL candidate invariant

Every blocking plane owns an unconditional terminal deadline independent of response metadata:

- connect/request deadline;
- response-header deadline;
- response-body/stream idle deadline;
- hard request maximum;
- model/harness run maximum;
- cancellation settlement deadline.

`Content-Type`, parser selection or stream framing may choose **how** to consume a response; they must never decide **whether** the request has a watchdog.

### Future regression fixture

A mock provider should return combinations of:

- missing `Content-Type`;
- malformed `Content-Type`;
- unexpected but syntactically valid type;
- headers then no body bytes;
- partial body then stall;
- disconnect during parsing.

The required result is a bounded terminal state with explicit failure classification, no indefinitely busy session, and no orphaned provider/process work.

## 8. Server, workspace and MCP process lifecycle — issue #47727

**Current stable regression fixture:** `anomalyco/opencode#47727`.

The reported `serve` failure retains per-directory instances and associated MCP child processes as new directories/workspaces are touched, causing host memory/process growth until exhaustion. The important ACL lesson is not simply to add a cache limit. It is to make ownership and settlement explicit.

### ACL candidate invariant

Every server/workspace/session instance and spawned MCP child process has:

- one owner;
- bounded retention policy;
- last-use/reference state;
- explicit close/evict transition;
- child-process termination/drain evidence;
- failure state when cleanup does not settle.

A server that remains reachable is not healthy if its workspace/process population grows without bound.

### Future regression fixture

Repeatedly open distinct temporary workspaces that each start an MCP child, then release them. Measure:

- live OpenCode instance count;
- live child-process count;
- RSS/private memory;
- file descriptors/handles;
- cleanup latency;
- residual processes after server shutdown.

The test should fail on monotonic unbounded growth or missing teardown settlement.

## 9. Cancellation, retry and recovery

The two stable defects reinforce a broader lifecycle model:

- **Timeout** is not the same as **cancel intent**.
- **Cancel intent** is not the same as **provider/process termination**.
- **Session no longer waiting** is not the same as **child resource settlement**.
- **Retryable transport failure** is not authority to replay a possibly effect-bearing tool call.

If ACL later embeds OpenCode, it should wrap the runtime with an outer run/effect state machine that can distinguish `running`, `cancel_requested`, `provider_unsettled`, `tool_effect_uncertain`, `cleanup_pending`, `failed`, and `settled` rather than flattening all failures into one session status.

## 10. Workspace and credential isolation

Because OpenCode is not an OS sandbox, a future worker deployment must give it only the workspace and credentials that role requires. In particular:

- run workers under a dedicated OS/container/VM identity;
- mount only authorized project/work roots;
- keep ACL governance/verifier/checkpoint roots worker-unwritable;
- construct a minimal child environment rather than inheriting supervisor secrets;
- broker provider/service credentials where practical;
- apply explicit network policy;
- treat spawned MCP servers as separate principals/processes with their own environment and lifecycle.

A permission prompt cannot compensate for an ambient credential leaked into a subprocess environment.

## 11. Observability and evaluation

OpenCode runtime/session/event data can be valuable operator evidence, but it should not own ACL pass/fail authority. Later benchmarking should preserve at least four separate evidence classes:

1. harness/runtime events and timing;
2. provider/model request evidence;
3. workspace/process/effect observations;
4. verifier-owned acceptance/security results.

Current issues #47605 and #47727 should be scored as **harness lifecycle failures**, not model failures. This classification matters for the user's planned model/harness benchmark lab: otherwise a strong model can be penalized for an orchestration defect, or a weak harness can be hidden by a successful final answer.

## 12. Reproducibility profile for later ACL testing

If OpenCode reaches the later benchmark phase, every result should record:

- OpenCode release/commit and stable-V1 versus V2/dev generation;
- exact provider adapter;
- model/runtime endpoint and immutable model/runtime identity where available;
- requested and realized context;
- tool/MCP inventory and schema/definition digests;
- permission profile;
- workspace/sandbox/process/network/credential profile;
- retry/timeout/cancellation settings;
- server/CLI mode;
- fixture and verifier revision;
- hardware/OS/runtime details relevant to the serving path.

One score labeled only `OpenCode + model-name` is not reproducible evidence.

## 13. Candidate ACL invariants from Task 25

1. Harness generation/revision is part of benchmark/deployment identity.
2. Stable and development architecture generations are separately qualified profiles.
3. Permission/approval is not sandboxing.
4. The worker's realized OS/process/network/credential ceiling is externally owned by ACL.
5. Session/event durability is not an ACL continuation checkpoint.
6. Provider request, session, tool call, MCP process and ACL effect identities remain distinct.
7. Every provider/body/stream path has unconditional hard and idle deadline ownership independent of content type/parser selection.
8. Cancellation intent, coroutine/session termination and backing process/resource settlement are separate states.
9. Every workspace/server instance and MCP child process has explicit ownership, bounded retention and teardown evidence.
10. Server health includes resource/lifecycle health, not only request reachability.
11. Tool identity includes trusted origin plus definition/schema identity, not display name alone.
12. Local/provider capability is exact model + runtime + adapter + OpenCode profile + configuration.
13. Retry cannot replay an ambiguous effect without idempotency/reconciliation evidence.
14. Child/MCP processes receive minimal explicit environments rather than ambient supervisor credentials.
15. Protected ACL policy/verifier/checkpoint roots remain outside worker write authority.
16. Runtime telemetry is operational evidence, not independent acceptance authority.
17. Current harness defects are classified separately from model capability failures.
18. Development/V2 mechanisms never become stable guarantees merely because they exist on default branch.

## 14. Future regression fixtures retained

1. Missing `Content-Type` response must time out and settle.
2. Malformed `Content-Type` response must time out and settle.
3. Header-complete/body-stalled response must hit idle/hard deadline.
4. Partial stream stall must leave no indefinitely busy session.
5. Cancel during provider parse/stream must settle all owned waiters.
6. Repeated distinct workspaces under `serve` must not grow instance state without bound.
7. MCP children must terminate/evict when their owning workspace/session is released.
8. Server shutdown must settle all owned MCP children.
9. Failed MCP cleanup must remain visible rather than disappearing from session state.
10. Worker permission approval must not permit access outside the external ACL sandbox profile.
11. Worker/MCP subprocesses must not inherit prohibited supervisor credentials.
12. Stable V1 and V2/dev must run the same core harness fixtures as separate profiles.
13. Same model/runtime under different OpenCode profiles must retain harness identity in results.
14. Provider retry after ambiguous tool/effect state must fail closed or reconcile before replay.

## 15. Reuse candidates for later comparison

Task 25 does not select any component, but these are worth comparing after the queue is complete:

- OpenCode as a bounded full worker harness inside an ACL-owned sandbox;
- session/event/runtime state patterns from the V2 redesign, once stable enough to qualify;
- provider abstraction/local-model integration;
- MCP lifecycle/integration patterns;
- permission UX as an operator-facing layer above ACL's deterministic authority;
- server/client surfaces for a remote Worker Lab UI;
- current lifecycle defects as regression tests for any selected harness.

## 16. Explicit non-conclusions

Task 25 does **not** conclude that:

- ACL should adopt, fork or wrap OpenCode;
- OpenCode V2/dev is production-stable or feature-equivalent to v1.18.29;
- OpenCode permissions provide sandbox security;
- OpenCode can replace ACL's scheduler, project/task state, effect ledger, credential broker, sandbox, writer fencing or verifier;
- OpenCode is the best coding harness;
- a particular local model/provider should run under OpenCode;
- the 32K benchmark should begin now;
- Mem0 or any later project has been researched.

## Primary sources retained

- Canonical repository: https://github.com/anomalyco/opencode
- Releases: https://github.com/anomalyco/opencode/releases
- Security documentation / project security boundary: https://github.com/anomalyco/opencode (upstream documentation and source tree)
- Stable lifecycle issue #47605: https://github.com/anomalyco/opencode/issues/47605
- Stable resource/process lifecycle issue #47727: https://github.com/anomalyco/opencode/issues/47727
- Current default development branch for V2 architecture: https://github.com/anomalyco/opencode/tree/dev

## Stop point

Task 25 ends with OpenCode only. The reusable results are the stable-versus-V2 identity boundary, the explicit non-sandbox security boundary, provider/harness qualification rules, and the two current lifecycle fixtures around unconditional timeout ownership and bounded workspace/MCP process settlement. **No Mem0 research was begun.**
