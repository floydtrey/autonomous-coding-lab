# Goose — Task 16 Deep Research

**Research date:** 2026-09-06  
**Research target:** current Goose agent/runtime/GDK architecture and directly relevant official project material  
**Canonical repository:** `aaif-goose/goose`  
**Revision inspected:** `5e90925962f05acf8e255032de44d16c4a7768a2` (2026-09-05)  
**Latest release observed:** `v1.49.0` (2026-09-03)  
**Decision status:** research only; no adoption/fork/dependency decision

## Scope

Task 16 studies Goose as a concrete open-source agent product and reusable architecture reference for ACL/Vera. The research focuses on:

- the Goose Development Kit (GDK), agent loop and ACP boundaries;
- provider abstraction and local-model compatibility;
- MCP integration, extensions and tool identity;
- permission, approval, security-inspection and sandbox boundaries;
- persistent sessions, state-machine recovery and concurrency;
- recipes, retries, subagents and executable configuration;
- process and workspace lifecycle;
- Code Mode and context/tool scaling;
- observability, telemetry and evaluation;
- current failure/security surfaces;
- the Block → Agentic AI Foundation (AAIF) transition and current governance.

Task 16 does **not** perform a separate Ollama project deep dive, choose a cross-project winner, redesign ACL/Vera governance, or authorize worker/model execution.

---

## Executive assessment

Goose is one of the strongest architecture references researched so far because it now contains several separable layers that map closely to ACL/Vera’s emerging needs:

1. a minimal provider contract and multiple local/cloud provider paths;
2. a GDK agent state machine whose next behavior is re-derived from durable conversation state rather than hidden in-memory loop state;
3. a full agent runtime that can be hosted behind ACP instead of embedded into every client;
4. MCP-based extension/tool interoperability;
5. persistent SQLite session state with provider/model/extension/recipe/mode metadata;
6. a shared per-session active-run registry that prevents concurrent ACP connections from interleaving two agent loops into one durable session;
7. deterministic recipe success checks and bounded retry mechanics;
8. a subagent system with explicit extension sets and recursion/control-plane restrictions;
9. Code Mode, which reduces model-facing tool-schema pressure by using a small meta-tool interface and on-demand discovery;
10. first-class Harbor benchmark tooling that compares exact Goose builds, models and extension configurations against other harnesses.

Those mechanisms are useful **patterns**, not proof that Goose can replace ACL’s outer authority/evidence system.

The most important negative finding is equally clear: Goose deliberately does not provide a general OS sandbox. Current upstream documentation says the tool-executing server runs with the user account’s permissions. Autonomous mode is the default and allows tools without approval. Local stdio extensions can inherit ambient process environment. Subagents are separate logical agent instances but are ordinarily in-process and inherit parent extensions unless narrowed.

Current open issues also expose boundaries ACL should turn into regression fixtures rather than rediscover later:

- recipe trust can occur after executable extension activation in the Desktop flow;
- the custom Streamable-HTTP MCP client still lacks the explicit redirect policy proposed for an open SSRF/header-forwarding report;
- deterministic argument-level shell authorization remains an open design gap beyond tool-wide allow/ask/deny.

The architectural conclusion is therefore not “use Goose unchanged.” It is:

> Goose provides unusually strong reference implementations for durable agent-state derivation, provider/tool interoperability, session continuity, context/tool scaling, and comparative evaluation, while ACL/Vera still need to own OS/process authority, credential isolation, effect identity/replay safety, protected policy, verifier independence and distributed/durable fencing.

---

# 1. Current project identity, health and governance

## 1.1 Canonical project and release

Observed at the Task 16 checkpoint:

- canonical repository: `aaif-goose/goose`;
- public and active;
- current `main` revision inspected: `5e90925962f05acf8e255032de44d16c4a7768a2` dated 2026-09-05;
- latest release observed: `v1.49.0`, published 2026-09-03;
- Rust is the core implementation language;
- Goose exposes Desktop, CLI/API/ACP and SDK integration surfaces;
- the current repository is not archived.

Primary sources:

- https://github.com/aaif-goose/goose
- https://github.com/aaif-goose/goose/tree/5e90925962f05acf8e255032de44d16c4a7768a2
- https://github.com/aaif-goose/goose/releases/tag/v1.49.0

## 1.2 Block → AAIF transition

Observed:

- the Linux Foundation announced AAIF on 2025-12-09 with founding project contributions including MCP, Goose and AGENTS.md;
- Goose was developed and contributed by Block;
- on 2026-04-07 Goose announced that Block had donated the project to AAIF and that the repository moved from `block/goose` to `aaif-goose/goose`;
- the project statement says its mission/community continued through the move.

Primary sources:

- https://aaif.io/news/linux-foundation-announces-formation-of-aaif
- https://goose-docs.ai/blog/2026/04/07/goose-moves-to-aaif/

### ACL/Vera relevance

The continuity rule recorded in Task 4 is confirmed: current Goose should be evaluated under `aaif-goose/goose`; old `block/goose` references are historical lineage, not a competing project.

The foundation transition is favorable for long-term open-source continuity, but “foundation-hosted” is not a substitute for dependency qualification, version pinning or governance review.

## 1.3 Current technical governance

Current `GOVERNANCE.md` defines:

- contributors, maintainers and core maintainers;
- consensus-oriented day-to-day work through PRs/issues/discussions;
- major changes: public proposal/discussion, at least one week review, majority core-maintainer approval and public announcement;
- merit-based maintainer membership rather than employer affiliation;
- Bradley Axen as tie-breaker for core-maintainer deadlock;
- Goose as a Series of LF Projects, LLC under AAIF;
- governance changes also require LF Projects, LLC approval;
- Apache-2.0 for code/specifications and CC BY 4.0 for documentation.

### ACL lesson

Governance should be recorded as part of dependency risk, but it does not prove interface stability. GDK SDK documentation explicitly calls the SDK alpha, so architectural maturity and API maturity must be qualified separately.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/GOVERNANCE.md

---

# 2. GDK: split the agent product into reusable layers

The Goose Development Kit exposes two materially different integration paths.

## 2.1 SDK path: provider/model layer in process

The GDK SDK is currently documented as **alpha** and should be version pinned.

It exposes the model/provider layer in-process from Rust and generated Python/Kotlin bindings. Current documentation includes:

- provider creation/configuration;
- streaming and non-streaming completion;
- text/reasoning/tool-call chunks;
- context management and compaction;
- provider request logging;
- declarative provider definitions.

### ACL implication

This is a useful comparison candidate when ACL needs a provider abstraction without importing the complete Goose UI/runtime.

But an alpha SDK needs:

- exact version pinning;
- ACL-owned compatibility tests;
- explicit migration gates;
- no assumption that current internal behavior is a long-term stable contract.

Primary sources:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/gdk/index.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/gdk/sdk/index.md

## 2.2 ACP path: full Goose runtime behind a process/network boundary

ACP exposes the full Goose runtime rather than only provider calls.

Current GDK ACP documentation supports:

- stdio: client owns a `goose acp` subprocess;
- HTTP/WebSocket: `goose serve`;
- loopback default binding;
- secret-key authentication;
- explicit browser origin policy;
- Desktop as an ACP client connecting to a local Goose server.

### ACL/Vera reuse candidate

This is a strong reference for a future Vera topology:

`phone/desktop/UI -> authenticated agent-runtime service -> model/providers/tools`

rather than embedding scheduling/model/tool/process logic into every client.

### Boundary

An ACP connection/session is not automatically ACL project/run/effect identity. Network authentication establishes access to the runtime; it does not authorize every model-selected external effect.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/gdk/acp/index.md

---

# 3. Agent loop as a durable conversation-derived state machine

`goose-agent` is one of the highest-value Task 16 findings.

Current README describes the loop as an ordered state machine assembled from operations:

- each operation inspects the conversation;
- the first applicable operation produces effects;
- effects are applied;
- execution starts again from the top;
- the machine reloads the session between passes;
- it does not keep authoritative loop progress only in memory;
- when an operation needs durable “already did this” state, it records metadata on the message;
- runtime-specific persistence is abstracted through `SessionLoader`, `EffectHandler` and `MachineSession`.

The key upstream statement is conceptual: the agent’s behavior is a function of the **persisted conversation**, not hidden in-memory loop state.

## 3.1 Why this matters to ACL

This addresses a recurring long-running-agent failure mode: after a crash/restart, the runtime should not need to guess which internal loop branch it was in.

Candidate ACL pattern:

1. persist authoritative semantic state;
2. reload it before each transition/pass;
3. derive the next legal action from durable state;
4. persist transition effects;
5. keep ephemeral loop variables non-authoritative.

This is closer to a recoverable state machine than “serialize a Python/Rust object and hope its in-memory invariants survive.”

## 3.2 What it does not prove

A conversation-derived state machine is not by itself:

- distributed writer fencing;
- a workspace checkpoint;
- an external-effect ledger;
- exactly-once execution;
- current credential/permission authority;
- independent verification.

Those remain separate ACL state domains.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose-agent/README.md

---

# 4. Provider contract and local-model architecture

## 4.1 Small provider interface

`goose-provider-types` defines a narrow required `Provider` contract. The only required operation is streaming:

- exact model configuration;
- system prompt;
- message history;
- tool definitions;
- a `MessageStream` result.

Defaults cover completion collection, context limits, model inventory, retry and provider-side session state.

A useful detail: streamed text may arrive incrementally while tool calls are emitted only after Goose has assembled complete tool-call objects.

### ACL lesson

Provider/runtime adaptation can remain smaller than the full agent harness. This aligns with the earlier ACL lesson that model-facing/runtime interfaces should be minimal while deterministic lifecycle and authority live outside them.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose-provider-types/README.md

## 4.2 Provider implementations are separate from the contract

Current `goose-providers` contains native provider modules plus declarative definitions.

Observed provider paths include:

- Anthropic;
- OpenAI;
- OpenAI-compatible;
- Gemini;
- Databricks;
- Azure;
- Snowflake;
- Ollama;
- local inference.

Many OpenAI-compatible services are definitions rather than new Rust implementations.

### ACL reuse candidate

Keep:

- provider contract;
- provider implementation/adapter;
- model registry/capability metadata;
- exact runtime deployment qualification

as separate objects.

“OpenAI compatible” or “provider supported” must not become an ACL verified-capability label without fixtures for tool calling, streaming, structured output and long-context behavior.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose-providers/README.md

## 4.3 Built-in local inference

Current `goose-local-inference`:

- runs GGUF through llama.cpp via `llama-cpp-2`;
- supports optional MLX;
- defaults to CPU;
- can compile CUDA/Vulkan/MLX support;
- manages memory/model placement;
- supports local paths and Hugging Face cache/inventory;
- applies model chat templates;
- supports native tool parsing and tool emulation/toolshim;
- separates thinking output;
- supports multimodal input.

Goose’s April 2026 built-in-local-inference writeup emphasizes that this path is embedded in the Goose process rather than requiring a separate local inference daemon.

### ACL capability-profile implication

A local Goose worker result should be identified by substantially more than model name:

`Goose revision/build + provider path + local backend + model/GGUF digest/quantization + accelerator + template/parser/tool mode + context/memory configuration + enabled extensions + fixture set`

This reinforces Task 13’s llama.cpp result rather than replacing it.

Primary sources:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose-local-inference/README.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/blog/2026-04-24-use-goose-with-built-in-local-inference/index.md

---

# 5. MCP integration and extension lifecycle

## 5.1 Current-generation MCP evidence

Current Goose test replays include the modern MCP protocol metadata:

`io.modelcontextprotocol/protocolVersion = 2026-07-28`

for multiple server configurations. Current workspace dependency metadata pins `rmcp 3.2.0`.

### ACL lesson

Task 15’s MCP compatibility profile becomes immediately practical:

- Goose revision;
- rmcp revision/version;
- MCP protocol era/version;
- transport;
- auth mode;
- negotiated extensions;
- server trust identity;
- exact tool definitions;
- regression replay set.

Do not reduce this to `supports_mcp = true`.

Sources:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/Cargo.toml
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/tests/mcp_replays/github-mcp-serverstdio

## 5.2 Secret/config rotation is explicitly recognized

The extension manager keeps:

- the unresolved extension configuration;
- a resolved configuration snapshot where secret references are substituted.

The resolved secret-bearing snapshot is documented in code as memory-only and is used to detect when a secret changed so an extension can be restarted.

### Reuse candidate

Persist references/config identity; keep live secret material outside durable config; re-resolve and restart/rebind when current secret authority changes.

This is compatible with the stronger ACL rule from Task 14: durable state references credentials, while live authority is rebound from current trusted policy.

## 5.3 Local stdio extension environment is broader than ACL should allow

Current local stdio launch constructs a `Command`, adds explicitly configured env values and then spawns it. The path does not call `env_clear()`.

Under normal process semantics, the child can therefore inherit the parent environment in addition to explicit values.

### ACL rule

Do not copy this behavior into production ACL workers.

Construct a minimal child environment from:

- runtime necessities;
- task-scoped non-secret config;
- specifically granted credential references/material;
- no ambient supervisor secrets.

This is a direct example where a convenient agent-product default is weaker than ACL’s intended worker boundary.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/agents/extension_manager.rs

## 5.4 Tool names carry extension origin, but collisions are not a hard failure

Current extension enumeration normally exposes tools as:

`extension__tool`

and injects extension identity into metadata.

This is materially safer for aggregated tools than raw server-local name-only dispatch.

However, when two exposed tools still have the same public name, current code warns and skips the duplicate rather than rejecting the complete capability set.

### ACL candidate invariant

Authority-bearing tool-set activation should be atomic:

- canonical trusted origin;
- tool name;
- definition/schema digest;
- no ambiguous collision;
- exact verified profile.

A collision should fail capability qualification rather than silently remove one contender.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/agents/extension_manager.rs

---

# 6. Permission and security layers

Goose’s current permissions are layered rather than one boolean.

## 6.1 Four user-facing modes

Current documentation defines:

- `auto`: autonomous tool use;
- `approve`: manual approval;
- `smart_approve`: risk/read-only-oriented approval;
- `chat`: no tool execution.

**Autonomous is the documented default.**

That is an important product choice: Goose optimizes for user-controlled autonomy, not for a default least-privilege unattended-worker security model.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/managing-tools/goose-permissions.md

## 6.2 Explicit tool permissions

Users can configure each tool as:

- Always Allow;
- Ask Before;
- Never Allow.

Explicit user tool policy is evaluated before Smart Approval.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/managing-tools/tool-permissions.md

## 6.3 Smart Approval combines metadata and model classification

Current permission code shows:

1. explicit user permission has priority;
2. an unoverridden `read_only_hint=true` can be allowed directly;
3. some management tools require approval;
4. unresolved calls can be sent through an LLM read-only classifier;
5. classifier failure/unknown state trends toward requiring approval;
6. security inspectors can override the baseline decision.

The classifier prompt explicitly treats tool names/IDs/arguments as untrusted data and asks only for IDs deemed read-only.

### Important hardening

The current implementation does **not** persist a positive LLM “safe” result as a name-wide allow rule. It only persists a negative/non-read-only classification as `AskBefore`.

That avoids an obvious vulnerability in which one harmless call could grant all future calls with the same tool name.

### Remaining trust boundary

MCP Task 15 established that remote tool annotations are untrusted unless the server is trusted. Goose Smart Approval can treat `read_only_hint=true` as approval-relevant input.

ACL should therefore qualify annotation provenance separately:

- trusted built-in extension annotation;
- trusted/pinned MCP server definition;
- unknown remote server annotation.

A server-supplied read-only claim should not by itself authorize an irreversible effect.

Primary sources:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/permission/permission_judge.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/permission/permission_inspector.rs

## 6.4 Prompt-injection detection is a separate advisory layer

Current security guidance offers:

- pattern-based prompt-injection detection;
- optional ML classifier;
- tool-call/conversation inspection;
- risk thresholds;
- user pause/approval behavior;
- recipe hidden-Unicode scanning;
- local MCP package malware checks.

Upstream explicitly does not present this as a guarantee.

### ACL lesson

Prompt-injection/security classification is a **signal**. It must not replace:

- deterministic policy;
- process/network sandbox;
- credential scoping;
- effect-specific approval;
- verifier evidence.

If a remote classifier is used, conversation/tool content also crosses a new data/privacy boundary.

Primary sources:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/security/prompt-injection-detection.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/security/security_inspector.rs

---

# 7. No general OS sandbox in current Goose

A historical Goose macOS Seatbelt sandbox was removed.

Current upstream documentation explicitly says the Goose server that executes tools runs with the **same permissions as the user account** and is **not OS-sandboxed**.

### ACL boundary

This is decisive:

- Goose approval mode != OS permission profile;
- Smart Approval != filesystem sandbox;
- extension isolation != credential isolation;
- subagent isolation != process isolation.

ACL unattended workers should run in an explicit execution boundary whose mounts/network/user/resources/credentials are controlled independently from the model’s tool policy.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/blog/2026-02-23-goose-v1-25-0/index.md

---

# 8. Persistent sessions and recovery

## 8.1 Session state is much richer than transcript text

Current `SessionManager` uses SQLite and currently declares schema version 16.

Persistent session data includes, among other fields:

- session ID/type;
- working directory;
- timestamps/name;
- conversation;
- extension data;
- usage/cost;
- provider name;
- model configuration;
- recipe and user recipe values;
- Goose mode;
- schedule/project/parent-session relationships.

### ACL lesson

Durable continuation should preserve behavior-bearing configuration, not only message text.

But a Goose session is still not automatically an ACL checkpoint because it does not prove:

- workspace snapshot identity;
- child process settlement;
- external-effect settlement;
- current credentials/policy;
- protected verifier state.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/session/session_manager.rs

## 8.2 ACP distinguishes durable human session from internal working state

Current ACP server comments/code distinguish the user-visible ACP session from internal agent working state.

The current server also has a shared `ActiveRunRegistry` keyed by session across ACP connections.

The design reason is explicit: separate roaming/ACP connections should not each start an agent loop and interleave writes to the same durable session.

### Strong reuse candidate

A durable state domain needs a single active writer.

The current Goose pattern is valuable:

- shared per-session run ownership;
- explicit run ID;
- cancellation token;
- cleanup guard when a connection/stream disappears.

### Limitation

The registry is in-memory within a server process. It is not a durable distributed lease/generation/fencing token across:

- multiple Goose server processes;
- machine restart;
- partitioned workers.

ACL’s multi-process writer fencing remains a separate requirement.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/acp/server.rs

## 8.3 Session replay protects tool-call boundaries

Current `load_session` replay walks backward to a user-turn boundary rather than slicing history arbitrarily. Tests protect against replay that splits a tool request from its response.

The load path also:

- activates provider/extensions;
- reapplies recipe components;
- restores provider-side continuation when possible;
- reloads durable state;
- resumes a pending state-machine turn when appropriate;
- re-emits pending permission requests.

### ACL reuse candidate

`resume_checkpoint` should rebuild a legal transition from durable semantic state, including pending approvals, rather than simply replaying arbitrary transcript suffixes.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/acp/server/load_session.rs

---

# 9. Process lifecycle and extension cleanup

Current subprocess utilities include useful lifecycle controls.

On Linux/Unix:

- spawned subprocesses can receive their own process group;
- Linux parent-death signaling is configured;
- the race between setting parent-death signal and parent already exiting is checked;
- long-lived MCP processes are spawned on a dedicated runtime/thread so they do not die merely because a temporary Tokio worker thread exits.

Current tests verify:

- an MCP child exits after its parent process dies;
- a “long-lived” child survives its spawning thread ending;
- it still dies when its real parent process is killed.

### ACL reuse candidate

Extension/runtime process custody should be explicit and testable:

- stable owner process;
- parent-death cleanup;
- owned cancellation;
- regression test for orphaning.

### Boundary

These tests do not prove complete arbitrary descendant-tree settlement for every shell/tool graph. ACL should retain process-tree/job-object/cgroup-style custody where external commands can spawn grandchildren.

Primary sources:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/subprocess.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/tests/subprocess_cleanup.rs

---

# 10. Recipes are executable authority artifacts

Recipes can contain:

- instructions and prompt;
- extensions;
- provider/model/settings;
- parameters;
- retry policy;
- shell success checks;
- `on_failure` shell commands.

They can be local, shared by link, or sourced from a configured GitHub recipe repository.

Therefore a recipe is not “just prompt text.” It can carry executable authority.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/recipes/session-recipes.md

## 10.1 Exact-content Desktop trust hash

Desktop stores a SHA-256 hash of the serialized recipe after acceptance. If recipe content changes, the hash changes and the old acceptance no longer matches.

### Strong reuse pattern

Persisted approval should bind to the exact behavior-bearing definition digest.

This parallels Task 14’s approval-version lesson.

### Boundary

The hash only helps if approval occurs **before** authority is exercised.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/ui/desktop/src/utils/recipeHash.ts

## 10.2 Deterministic shell checks and bounded retry

Goose recipe retry can run deterministic shell success checks.

Observed implementation properties:

- checks execute sequentially;
- nonzero status fails the validation set;
- checks and `on_failure` commands have timeouts;
- stderr capture is bounded;
- retry count is bounded;
- optional `on_failure` runs before retry;
- the conversation is reset to the initial message state before the next attempt.

### Useful pattern

Agent success can be decided by machine-observable host checks rather than model self-assertion.

This aligns strongly with ACL’s verifier-first philosophy.

### Critical boundary: retry does not roll back the world

The retry code resets the **conversation**. It does not automatically restore:

- filesystem state;
- Git state;
- external API effects;
- created/deleted resources;
- payments/messages/deployments.

Therefore:

`failed check -> retry`

is not automatically permission to replay an effect-bearing task.

ACL still needs:

- idempotency/effect ID;
- reconciliation;
- rollback/staging where possible;
- explicit uncertain-effect state.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/agents/retry.rs

## 10.3 Recipe checks are not independent verifier authority

The recipe itself can define the shell validator and it runs under the same general host/user environment.

For ACL acceptance:

- worker/recipe author must not control the authoritative definition of success;
- protected verifier fixtures/scripts live outside worker write authority;
- Goose-style recipe checks may be useful task-local evidence, but not the sole acceptance root.

---

# 11. Subagents: logical isolation and capability shaping

Goose subagents provide:

- separate agent/session instances;
- sequential or parallel delegation;
- per-subagent model/provider/turn/time settings;
- selectable extension set;
- live tool-call visibility;
- recursion prevention;
- restrictions on extension-management and schedule-management control-plane actions.

Default subagent values include:

- 25 turns;
- 5-minute timeout;
- inherited parent extensions unless narrowed.

Subagents are automatically available only in Autonomous mode; the docs say they are disabled in manual approval, Smart Approval and chat-only modes.

## 11.1 High-value design idea

Child agents should have explicit capabilities and should not be able to widen the control plane.

Goose blocks:

- subagent spawning from subagents;
- extension management;
- schedule management.

This is a useful example of a child-role capability ceiling.

## 11.2 Important terminology boundary

Current internal subagent code creates new `Agent` instances and background tasks in the same Goose process. Documentation’s “process isolation” wording should not be interpreted as OS-process security isolation.

### ACL candidate invariant

Separate:

- logical agent role/session;
- model context;
- capability list;
- operating-system process;
- filesystem/network/credential sandbox.

A subagent can be context-isolated while still sharing broad host authority.

Primary sources:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/context-engineering/subagents.mdx
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/agents/platform_extensions/summon.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/agents/subagent_handler.rs

---

# 12. Code Mode: reduce model-facing tool complexity without deleting runtime capability

Code Mode is a strong external example of a principle already emerging in ACL research.

Traditional mode sends all enabled tool definitions to the model.

Code Mode instead exposes three meta-tools:

- `list_functions`;
- `get_function_details`;
- `execute_typescript`.

The model writes code that discovers tools on demand and can batch/chains multiple tool calls locally.

### Benefits

Observed upstream goals:

- lower tool-schema context pressure;
- on-demand discovery;
- local intermediate-result processing;
- fewer model round trips for multi-step tool workflows.

Current project-owned Harbor benchmark data shows Code Mode configurations outperforming stock Goose in one current same-model Terminal-Bench snapshot. That is useful evidence that interface/harness structure can matter substantially even when the underlying model is held constant.

### ACL lesson

The correct principle is not “give the model every deterministic mechanism.”

Instead:

- keep the model-facing vocabulary small;
- dynamically expose only needed capabilities;
- leave policy, execution custody, evidence and recovery in deterministic infrastructure.

### Security boundary

A small meta-tool surface can still expose a very large effect surface. `execute_typescript` plus dynamic tool access is not least privilege merely because the model sees only three tool schemas.

Code Mode only supports text tool results in the current documented path; non-text results are ignored.

Primary sources:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/managing-tools/code-mode.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/evals/harbor/README.md

---

# 13. Evaluation and observability

## 13.1 Harbor: harness/model/build comparison tooling

Current `evals/harbor` supports terminal-bench-style comparisons across:

- exact Goose binary builds;
- model/provider selection;
- extension sets;
- Goose versus other harnesses.

The current full Terminal-Bench 2 setup contains 89 tasks and records:

- pass/fail/error/timeout;
- compute duration;
- input/output tokens;
- turns;
- cost where available.

The runner uploads the selected Goose binary into each task container and generates the extension configuration for that run.

### Strong ACL reuse candidate

Benchmark identity should include:

- exact harness binary/revision;
- exact model/provider;
- exact extension/tool profile;
- task dataset/version;
- timeout/turn settings;
- environment image;
- verifier identity.

This directly supports the user’s plan to build ACL’s own model-role benchmark only after external research is complete.

### Caution

Goose’s published scores are project-owned benchmark evidence, not universal proof of production reliability. ACL still needs its own fixtures and its own hardware/runtime qualification.

Primary source:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/evals/harbor/README.md

## 13.2 Product analytics and operational OTel are separate systems

Current PostHog telemetry code is opt-in:

- explicit user choice required;
- environment can disable it;
- current source states only `session_started` events are sent while several other event paths are temporarily disabled.

Separately, Goose can export OpenTelemetry traces/metrics/logs over configured OTel exporters.

Current OTel code includes hardening for runtime/exporter behavior, including avoiding async-export panic paths and declining unsupported gRPC exporter configuration when the build only includes HTTP transport.

### ACL evidence boundary

Keep three systems separate:

1. product analytics;
2. operator observability/logs/traces/metrics;
3. authoritative verifier evidence.

An OTel span showing `tool succeeded` is not independently authoritative acceptance evidence.

Telemetry can also contain sensitive host/user/session/tool/provider context and needs audience/redaction/retention policy.

Primary sources:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/posthog.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/otel/otlp.rs

---

# 14. Current failure / ambiguity surfaces worth turning into ACL fixtures

These are issue-scoped/current-revision evaluation cases. They should not be generalized into claims that every Goose deployment is exploitable.

## 14.1 Shared recipe Desktop pre-consent execution — open #10325

Issue #10325 originally reported that recipes can contain executable stdio extension commands and retry shell checks while the existing recipe warning scan only checks hidden Unicode tags in natural-language fields.

A maintainer clarified an important boundary:

- CLI `goose run --recipe` explicitly executes a recipe, so running an untrusted recipe is comparable to running an untrusted script; the CLI behavior was not accepted as a separate security boundary violation.
- The potentially actionable boundary is the Desktop “Trust and Execute” flow.

The reporter then provided a v1.45 Desktop reproduction where:

- a `goose://recipe` deeplink created a recipe with a stdio extension;
- the extension command wrote a marker before the user clicked the trust dialog;
- the command also executed in a run where the user later clicked Cancel.

Task 16 checked current `main`:

- `Recipe::check_for_security_warnings()` still checks only Unicode tags in instructions/prompt/activities;
- Desktop `BaseChat` still checks recipe acceptance after the session recipe is already loaded;
- backend agent creation still loads session extensions while constructing/restoring the agent.

The issue remains open.

### ACL fixture

- receive a new remotely sourced executable workflow definition;
- ensure no extension/process/tool or retry hook starts before explicit authorization;
- approval binds exact normalized behavior digest;
- denial leaves no already-executed effect;
- UI preview includes the authority-bearing extension/retry fields.

Sources:

- https://github.com/aaif-goose/goose/issues/10325
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/recipe/mod.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/ui/desktop/src/components/BaseChat.tsx
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/execution/manager.rs

## 14.2 MCP Streamable-HTTP redirect SSRF/header-forwarding report — open #11500

Open #11500 reports that Goose’s custom Streamable-HTTP MCP HTTP client uses reqwest’s redirect behavior without an explicit redirect restriction and can follow a malicious redirect to an internal destination while carrying configured headers.

The assigned maintainer responded that the preferred fix is to disable redirects for the custom clients and verify that authenticated/unauthenticated 3xx responses are surfaced without contacting the target.

Task 16 checked current `main` and the relevant `connect_with_auth` path still builds the request client without an explicit `.redirect(...)` policy.

### ACL fixture

For any server-controlled redirect or discovery URL:

- reject by default or revalidate every target;
- never forward Authorization/custom secret headers cross-origin;
- block loopback/link-local/private/cloud-metadata destinations according to policy;
- re-evaluate DNS/IP at connection time;
- bound redirect count;
- record target/origin evidence.

Sources:

- https://github.com/aaif-goose/goose/issues/11500
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/agents/extension_manager.rs

## 14.3 Deterministic command-level permission gap — open #11399

Current Goose has explicit per-tool allow/ask/deny and Smart Approval, but open #11399 captures the need for deterministic **argument-level** shell policy.

The concrete problem:

`developer__shell` is one broad effect tool.

Tool-wide policy cannot express:

- allow `git status`;
- ask/deny `git push` or `git reset`;
- deny destructive disk commands;

without either prompting for every shell invocation or broadly allowing the tool.

An assigned maintainer’s current design direction in the thread favors:

- native tool-scoped rules;
- initially `developer__shell`;
- precedence `deny > ask > allow`;
- Smart Approval for unmatched calls;
- separate consideration of how to protect policy configuration from agent edits.

### ACL candidate invariant

Broad shell/tool dispatch needs deterministic argument/resource policy outside the model.

Policy state must itself be outside worker mutation authority.

String regex can be a guardrail, but shell semantics, aliases, nested interpreters and compound commands mean execution sandbox and effect policy remain separate.

Source:

- https://github.com/aaif-goose/goose/issues/11399

## 14.4 Local tool protocol failures need their own failure class

Goose’s local-provider history contains concrete toolshim/parser/structured-output fixes. The architectural lesson is more important than any one historical issue:

`model failure != provider adapter failure != stream assembler failure != tool parser failure != schema/final-output registration failure`

ACL’s benchmark lab should classify these separately.

This aligns with Task 13’s llama.cpp finding that a deterministic parser/constraint layer can make a capable model look incapable or deterministically wrong.

---

# 15. Concrete ACL/Vera candidate invariants from Goose

1. Keep the provider/model contract smaller than the whole agent runtime.
2. Record exact Goose/GDK/provider/runtime revision; alpha SDK APIs require pinning.
3. A full agent runtime can live behind an authenticated ACP-like service boundary rather than inside every UI/client.
4. Client connection/session identity is not ACL project/run/effect identity.
5. Re-derive next agent transition from durable semantic state rather than hidden in-memory loop state.
6. Reload authoritative session state between state-machine passes.
7. Operation “already executed” markers belong in durable semantic state, not ephemeral flags.
8. A conversation-derived state machine is still not an external-effect ledger.
9. Each durable session has one active writer; current in-process ownership is not distributed fencing.
10. Lost connection must release/cancel active run ownership without silently authorizing replay.
11. Resume must preserve tool request/result and pending approval boundaries.
12. Resume transcript and resume authoritative state-machine turn are distinct operations.
13. Provider-side session resumption is optional optimization/state and cannot replace ACL continuation state.
14. Local capability identity includes exact provider path, engine/backend, model artifact, template/parser/tool mode, context and extensions.
15. Tool-call stream assembly/parser failures are classified separately from model reasoning failure.
16. MCP compatibility includes Goose/rmcp/protocol/transport/auth/extension profile, not a boolean.
17. Extension secrets are re-resolved from current authority; secret-bearing resolved config stays out of durable serialization.
18. Local child processes receive a minimal explicit environment; do not inherit supervisor environment by default.
19. Canonical effect-tool identity includes trusted extension/server origin and definition/schema digest.
20. Ambiguous tool collisions fail capability activation rather than silently dropping a candidate.
21. Autonomous/no-approval mode is a workflow mode, not a security boundary.
22. Tool annotation/read-only hints are untrusted unless the definition/server origin is trusted.
23. LLM risk classifiers can add friction/signal but do not own deterministic irreversible-effect authorization.
24. Positive model “safe” classifications should not become durable broad allow grants.
25. Security/prompt-injection detection is second-line advisory evidence, not a sandbox.
26. Goose role/subagent separation is not OS/process isolation.
27. Child agents cannot widen parent control-plane authority.
28. Child effect capabilities default to explicit/narrowed sets rather than inheriting broad parent tools.
29. OS/container/filesystem/network/credential authority remains separate from tool approval policy.
30. Parent-death and orphan-cleanup behavior is explicitly tested for long-lived extension processes.
31. Shared workflow/recipe definitions are executable authority artifacts, not prompt-only content.
32. Approval of an executable workflow occurs before any extension/process/retry hook starts.
33. Persisted workflow approval binds exact normalized behavior/config digest.
34. Machine-observable success checks are valuable but verifier definitions remain outside worker/recipe mutation authority.
35. Retrying after validation failure does not authorize replay of uncertain external effects.
36. Conversation reset is not workspace/effect rollback.
37. Model-facing tool-schema complexity should be minimized when a small on-demand discovery interface can preserve capability.
38. A small meta-tool interface can still represent broad authority and needs normal effect policy.
39. Benchmark results pin exact harness binary/revision, model/provider, extension set, environment, dataset and verifier.
40. Product analytics, operator telemetry and acceptance/verifier evidence are separate data systems.
41. Remote MCP/discovery/redirect/network behavior requires explicit SSRF and credential-forwarding policy.
42. Broad shell tools need deterministic argument/resource policy outside the LLM.
43. Policy files/configuration must be protected from the worker whose actions they constrain.
44. Current open project issues become versioned regression fixtures, not permanent assumptions about future Goose releases.

---

# 16. What Goose does not solve for ACL/Vera

Task 16 found no basis to delegate these ACL/Vera responsibilities to Goose itself:

- project/backlog/dependency scheduling;
- distributed multi-process writer leases/fencing;
- protected worker workspace snapshots;
- exactly-once external-effect identity;
- effect reconciliation after ambiguous transport/process failure;
- immutable verifier fixtures and acceptance authority;
- OS/container sandbox policy for unattended workers;
- minimal supervisor→worker credential/environment inheritance;
- Vera long-term memory/provenance governance;
- service credential broker;
- durable approval provenance across changing project/tool/policy definitions;
- cross-project role assignment based on ACL-owned model benchmarks.

Goose is strongest as a **reference/product layer** for provider/runtime abstraction, agent state-machine construction, MCP tool integration, sessions, recipes, delegation, context/tool scaling and comparative agent evaluation.

---

# 17. Later comparison questions

When the campaign reaches synthesis:

1. Should ACL reuse `goose-provider-types`/GDK provider contracts, adapt them, or keep its own provider interface?
2. Is the `goose-agent` conversation-derived state machine mature enough to wrap under ACL’s outer effect/checkpoint system?
3. Should ACL expose/consume ACP for Vera clients, or use a smaller custom service API?
4. Which Goose MCP extension-manager mechanisms are worth reuse once ACL’s stronger environment/network/identity policy is wrapped around them?
5. Can Goose Code Mode or its underlying pctx approach reduce 32K-context pressure for local workers without widening effect authority?
6. Which Goose Harbor fixtures/methodology should inform ACL’s later benchmark lab?
7. Which local Goose provider paths should be evaluated against direct llama.cpp and later Ollama/vLLM research?
8. Can Goose recipes serve as a portable task-definition layer if executable authority fields are separately signed/pinned/approved?
9. Which subagent mechanisms are useful once ACL enforces parent/child capability ceilings and OS-level isolation?
10. Does a thin pinned Goose component dependency reduce maintenance enough to justify its alpha/moving API surface versus copying only the architecture pattern?

No answer is selected in Task 16.

---

# 18. Primary source inventory

Canonical project / governance:

- https://github.com/aaif-goose/goose
- https://github.com/aaif-goose/goose/tree/5e90925962f05acf8e255032de44d16c4a7768a2
- https://github.com/aaif-goose/goose/releases/tag/v1.49.0
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/GOVERNANCE.md
- https://aaif.io/news/linux-foundation-announces-formation-of-aaif
- https://goose-docs.ai/blog/2026/04/07/goose-moves-to-aaif/

GDK / ACP / provider architecture:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/gdk/index.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/gdk/sdk/index.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/gdk/acp/index.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose-agent/README.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose-provider-types/README.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose-providers/README.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose-local-inference/README.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/blog/2026-04-24-use-goose-with-built-in-local-inference/index.md

Extensions / permission / security:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/agents/extension_manager.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/permission/permission_judge.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/permission/permission_inspector.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/managing-tools/goose-permissions.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/managing-tools/tool-permissions.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/security/prompt-injection-detection.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/blog/2026-02-23-goose-v1-25-0/index.md

Session / recovery / process lifecycle:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/session/session_manager.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/acp/server.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/acp/server/load_session.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/execution/manager.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/subprocess.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/tests/subprocess_cleanup.rs

Recipes / delegation / context:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/recipes/session-recipes.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/ui/desktop/src/utils/recipeHash.ts
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/agents/retry.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/context-engineering/subagents.mdx
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/agents/platform_extensions/summon.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/agents/subagent_handler.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/documentation/docs/guides/managing-tools/code-mode.md

Evaluation / observability:

- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/evals/harbor/README.md
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/posthog.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/otel/otlp.rs

Current failure / design evidence:

- https://github.com/aaif-goose/goose/issues/10325
- https://github.com/aaif-goose/goose/issues/11500
- https://github.com/aaif-goose/goose/issues/11399
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/crates/goose/src/recipe/mod.rs
- https://github.com/aaif-goose/goose/blob/5e90925962f05acf8e255032de44d16c4a7768a2/ui/desktop/src/components/BaseChat.tsx

---

# Conclusion

Goose is a high-value ACL/Vera reference precisely because it contains both **good reusable mechanisms** and **real operational boundaries**.

The strongest mechanisms are:

- the GDK’s separable provider/runtime surfaces;
- a provider contract small enough to test independently;
- the conversation-derived agent state machine;
- rich versioned session persistence;
- shared per-session active-run ownership;
- pending approval/state-machine resume;
- explicit extension-origin tool naming;
- live secret re-resolution/restart behavior;
- parent-death cleanup tests for extensions;
- exact-content recipe acceptance hashing;
- deterministic recipe validation/retry mechanics;
- subagent capability/control-plane restrictions;
- Code Mode’s on-demand tool discovery;
- Harbor’s same-model/same-task harness comparisons;
- separate product telemetry and OpenTelemetry operator observability.

The strongest warnings are:

- current Goose is not a general OS sandbox;
- Autonomous mode is the default;
- local stdio children may inherit ambient parent environment;
- remote read-only/tool metadata can influence Smart Approval;
- broad shell authorization is still tool-wide rather than deterministic by argument/resource;
- internal subagents are logical/in-process isolation rather than OS security isolation;
- recipes carry executable commands/configuration, not merely prompts;
- retry resets conversation, not external effects;
- Desktop recipe trust ordering has a current open pre-consent execution report consistent with present code structure;
- the current custom MCP HTTP client still lacks the explicit redirect policy proposed for an open SSRF/header-forwarding report;
- runtime traces and recipe checks do not replace independent verifier authority.

Task 16 therefore supports treating Goose as a serious component/reference candidate during later synthesis, especially for **state-machine recovery, provider interoperability, context/tool scaling and benchmark methodology**, while preserving ACL/Vera’s stronger authority, isolation, effect-settlement and verification layers above it.

No Goose dependency, fork, wrapper strategy, model assignment or cross-project winner is selected here.
