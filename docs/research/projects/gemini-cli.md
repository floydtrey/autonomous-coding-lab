# Gemini CLI — Task 19 Deep Research

**Research date:** 2026-09-06  
**Research target:** current Gemini CLI agent/runtime architecture and directly relevant official project material  
**Canonical repository:** `google-gemini/gemini-cli`  
**Revision inspected:** `85aca163f6c73ac6ce380b5447359146b8adcae4` (2026-09-04)  
**Latest stable release observed:** `v0.58.0` (2026-09-01)  
**License:** Apache-2.0  
**Decision status:** research only; no adoption, dependency, model, or implementation decision

## Scope

Task 19 studies Gemini CLI as a concrete coding-agent product and architecture reference for ACL/Vera.

The research focuses on:

- tool/execution authority and deterministic policy;
- approval modes and safety-checker layering;
- OS/tool sandboxing and sandbox-expansion permissions;
- environment and credential boundaries;
- provider/model routing and local-model boundaries;
- session persistence, resume, rewind and workspace checkpointing;
- subagents and capability shaping;
- MCP, ACP and A2A interoperability;
- extensions, hooks, skills and executable configuration;
- context/auto-memory state;
- telemetry and behavioral evaluation;
- current security/recovery failure surfaces;
- reusable mechanisms and non-conclusions for ACL/Vera.

Task 19 does **not** deep-research Graphiti, select a cross-project winner, start the benchmark lab, run Gemini models, redesign ACL/Vera governance, or authorize worker execution.

---

# Executive assessment

Gemini CLI is one of the strongest **execution-authority and host-integration references** in the campaign.

Its highest-value mechanisms are not the Gemini model itself. They are the deterministic layers around it:

1. a tiered policy engine whose rule identity can include tool, MCP server, arguments, annotations, subagent, approval mode and interactive/headless state;
2. fail-closed policy behavior for non-interactive execution and policy-checker errors;
3. platform-specific tool sandbox managers with filesystem/network expansion rather than one global “sandbox on/off” bit;
4. explicit distinction between tool policy and sandbox permissions;
5. protected governance paths and recent hardening of system configuration ownership;
6. a narrow content-generator/provider interface with model routing/fallback separated from tool execution;
7. append-oriented JSONL session records with rewind/metadata records and atomic repair of unreadable files;
8. shadow-Git workspace snapshots created before modifying file tools;
9. isolated local-subagent tool registries and subagent-specific policy matching;
10. MCP, ACP and A2A adapters around the same runtime;
11. extension-install consent that exposes behavior-bearing MCP configuration and hashes the configuration;
12. behavioral evaluations that explicitly model LLM non-determinism rather than pretending every model-steering test is deterministic.

Those mechanisms are useful reference material, but Gemini CLI is **not** a replacement for ACL’s outer authority/evidence system.

The strongest boundaries found in Task 19 are equally concrete:

- YOLO mode deliberately allows unmatched tool calls and bypasses several interactive safeguards.
- Full-process sandboxing can co-locate model-provider credentials/network identity with model-selected shell execution.
- environment redaction is configurable and ordinary non-sandbox execution can retain a broad inherited environment;
- persistent sandbox expansion is keyed primarily by root command plus resources, not ACL effect identity;
- subagents default to all parent tools when no tool list is supplied, and logical subagent isolation is not automatically OS-process isolation;
- checkpointing captures a Git-visible workspace snapshot, not ignored files or external effects;
- session persistence is not equivalent to safe resume;
- current ACP `session/load` still initializes configuration before resolving the requested session, matching an open corruption report;
- current Windows “known-safe git” classification still approves `git diff` based only on the subcommand, matching open #29189 where `--output` can overwrite a file without prompting;
- latest stable `v0.58.0` has an open report (#29198) where resuming then exiting without interaction can remove the session from future resume;
- a session can continue running after ENOSPC disables chat recording, creating a live-but-not-durable state;
- the local provider surface is Gemini/Vertex/Gateway-oriented, not a first-class Ollama/llama.cpp/OpenAI-compatible local-model runtime.

The architectural conclusion is therefore:

> Gemini CLI is a high-value reference for deterministic policy composition, sandbox permission expansion, executable-extension consent, workspace checkpointing, protocol adapters, subagent capability shaping, and non-deterministic behavioral evaluation. ACL/Vera should reuse or emulate those patterns only inside stronger project/run/effect identity, minimal environment/credential isolation, durable writer fencing, transactional recovery and independent verification.

---

# 1. Project identity, activity and version boundary

## 1.1 Canonical project

Observed at the Task 19 checkpoint:

- canonical repository: `google-gemini/gemini-cli`;
- repository is public and not archived;
- default branch: `main`;
- implementation is predominantly TypeScript;
- license: Apache-2.0.

Primary sources:

- https://github.com/google-gemini/gemini-cli
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/LICENSE

## 1.2 Revision inspected

Current revision inspected:

`85aca163f6c73ac6ce380b5447359146b8adcae4`

Commit message:

`fix(config): enforce strict permission and ownership checks on system-wide configuration paths (#29115)`

This revision is newer than the latest stable `v0.58.0`.

Recent security-relevant main-branch work immediately before the checkpoint also includes:

- workspace/path/symlink boundary hardening;
- extension environment-change consent and runtime-altering environment sanitization;
- credential/key cleanup;
- system configuration ownership/permission checks.

### ACL lesson

Gemini CLI’s security boundary is moving quickly enough that an ACL qualification profile must include the **exact Gemini CLI revision/build**, not only `v0.x`.

Primary source:

- https://github.com/google-gemini/gemini-cli/commit/85aca163f6c73ac6ce380b5447359146b8adcae4

## 1.3 Latest stable release

Latest stable observed:

- `v0.58.0`;
- published 2026-09-01;
- bundled artifact exposes SHA-256 release digests;
- release notes include sandbox socket/binary isolation hardening, write-policy safety checkers, A2A lifecycle fixes and history rollback/retry changes.

Primary source:

- https://github.com/google-gemini/gemini-cli/releases/tag/v0.58.0

---

# 2. Runtime decomposition

A useful conceptual decomposition for ACL is:

`UI / headless / ACP client`
→ `Gemini CLI Config + agent loop`
→ `PolicyEngine`
→ `ToolRegistry / subagent registry / MCP / A2A`
→ `confirmation + safety checkers`
→ `SandboxManager / shell/file services`
→ `host process / OS sandbox`
→ `external effects`

In parallel:

`agent loop`
→ `ContentGenerator`
→ `Gemini API / Code Assist / Vertex / Gateway`

And separately:

`agent loop`
→ `ChatRecordingService`
→ JSONL durable conversation record

while modifying tools can additionally trigger:

`tool approval`
→ `GitService`
→ shadow-Git workspace checkpoint.

This separation is valuable because it avoids treating “the agent” as one monolithic authority boundary.

---

# 3. Deterministic Policy Engine

The current Policy Engine is one of Gemini CLI’s strongest reusable mechanisms.

## 3.1 Decisions

Rules resolve to:

- `ALLOW`;
- `DENY`;
- `ASK_USER`.

The engine has explicit interactive/non-interactive behavior:

- interactive default: `ASK_USER`;
- non-interactive default: `DENY`.

That is a strong fail-closed default for unattended/headless execution.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/policy/policy-engine.ts

## 3.2 Rule identity is richer than tool name

A rule can match on combinations of:

- tool name;
- MCP server identity;
- stable-serialized arguments / regex;
- shell command prefix/regex;
- tool annotations;
- subagent identity;
- approval mode;
- interactive versus non-interactive execution.

### ACL reuse candidate

Authority should be represented by an explicit deterministic tuple rather than model intent.

A later ACL policy object should be able to bind at least:

`actor role + tool origin + operation + normalized arguments/resources + run/task + mode + current policy version`.

Gemini CLI is strong precedent for the first half of that tuple.

## 3.3 Priority tiers

Current documentation defines ordered policy trust tiers:

- Default;
- Extension;
- Workspace;
- User;
- Admin.

Higher-trust tiers override lower tiers.

Current documentation also warns that the Workspace policy tier is presently non-functional.

### ACL lesson

Policy precedence must be structural, not just “last file wins.”

Extension-provided policy should never outrank ACL administrator/project-owner policy.

The documentation’s disabled Workspace tier is also a useful reminder that **documented policy location is itself a capability that must be verified**, not assumed.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/reference/policy-engine.md

## 3.4 MCP origin participates in policy

The engine can match explicit MCP server identity.

Current code prefers explicit server metadata and falls back to parsing fully-qualified tool names.

The current documentation recommends `mcpName` rather than relying on FQN wildcards.

### ACL lesson

This strongly reinforces Task 15:

`tool_name` alone is not authority identity.

ACL should bind MCP effect authority to:

`trusted server identity + tool definition/schema digest + operation + normalized arguments`.

## 3.5 Parser failures trend fail-closed

The shell-policy path handles parser failure conservatively.

Important current behavior:

- a matching deny still denies;
- constrained YOLO rules that cannot validate their argument restriction deny;
- ordinary parse uncertainty falls back to confirmation or non-interactive denial.

### ACL reuse candidate

When a deterministic guard cannot establish that an effect is within policy, uncertainty should not become permission.

---

# 4. Approval modes are workflow modes, not security boundaries

Current modes include:

- `default`;
- `autoEdit`;
- `plan`;
- `yolo`.

## 4.1 Plan mode

Plan mode is documented as read-only-oriented research/design.

Policies can explicitly bind to approval modes.

This is useful role/mode shaping.

### Boundary

Plan mode is still implemented through policy/tool behavior, not an independent OS security boundary.

ACL should not encode “planner” as merely a prompt or UI mode. The planner’s write/effect capability should be absent at the deterministic execution layer.

## 4.2 YOLO mode

YOLO is deliberately auto-approval-oriented.

Current policy behavior allows unmatched calls in YOLO.

Several safeguards that otherwise downgrade to confirmation are bypassed or relaxed in YOLO.

### ACL rule

No production ACL worker should be considered safe merely because its model prompt says “be careful” while the deterministic execution layer is equivalent to YOLO.

Unattended autonomy should come from **pre-authorized narrow capabilities**, not universal auto-approval.

---

# 5. Safety checkers are a second deterministic layer

After baseline rule matching, the Policy Engine can invoke safety checkers.

Observed behavior:

- checker `DENY` overrides;
- checker `ASK_USER` can downgrade;
- checker exception fails closed to deny;
- a baseline deny is not overridden by a permissive checker.

### Reuse candidate

Use layered guards:

1. static policy;
2. normalized-argument/resource policy;
3. contextual safety checker;
4. OS/process sandbox;
5. effect-specific verifier/reconciler.

### Boundary

A safety checker is still part of the authorization path.

It does not provide independent post-effect verification.

---

# 6. Shell authorization and command semantics

Gemini CLI has substantially more deterministic shell handling than a naive command-prefix allowlist.

Current behavior includes:

- shell wrapper stripping;
- command splitting;
- root-command extraction;
- redirection detection;
- command-substitution detection;
- known-safe and known-dangerous command classifiers;
- workspace/cwd checks;
- Git trust checks;
- sandbox-specific filesystem/network permission evaluation.

This is strong implementation reference material.

## 6.1 Redirection is effect-bearing

Current policy handling can downgrade a nominally allowed command to confirmation when shell redirection is present unless specifically authorized/mode-relaxed.

### ACL lesson

Effect semantics cannot be inferred from executable name alone.

`grep` can become a write through redirection.

`git diff` can become a write through flags.

A safe policy requires normalized **operation semantics**, not a binary executable allowlist.

## 6.2 Current Windows `git diff --output` failure — open #29189

Open issue #29189 reports:

- Gemini CLI 0.58.0 on Windows;
- `git diff` is treated as read-only;
- `git diff --no-index ... --output=<path>` can truncate/overwrite a file;
- no permission prompt appears.

Task 19 checked current `main`.

Current Windows source still contains:

> “For simplicity in this branch, we'll allow standard git read operations”

and returns safe for these subcommands by name:

- `status`;
- `log`;
- `diff`;
- `show`;
- `branch`.

It does not validate the write-capable flags in that Windows branch.

Proposed PR #29184 remains open/unmerged at the Task 19 checkpoint.

### ACL regression fixture

A command classified read-only by subcommand must be retested with:

- output flags;
- config overrides;
- external diff/textconv;
- hooks/aliases;
- redirection;
- nested interpreters;
- destructive sub-options.

### Candidate invariant

“Read-only executable/subcommand” is not an authority category.

Authorization must classify the **normalized command invocation**.

Primary sources:

- https://github.com/google-gemini/gemini-cli/issues/29189
- https://github.com/google-gemini/gemini-cli/pull/29184
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/sandbox/windows/commandSafety.ts

---

# 7. Tool sandboxing and OS isolation

Gemini CLI now has multiple sandbox layers.

The important distinction is:

`policy decision`
!=
`sandbox permission`
!=
`full process/container isolation`.

## 7.1 SandboxManager abstraction

The core SandboxManager supplies:

- command preparation;
- environment preparation;
- known-safe/dangerous classification;
- denial parsing;
- workspace identity;
- sandbox options and permission data.

The execution policy can include:

- allowed paths;
- filesystem read/write permissions;
- network permission;
- environment sanitization configuration.

### Reuse candidate

Represent filesystem and network grants as explicit runtime capabilities rather than inferring them from tool names.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/sandboxManager.ts

## 7.2 Linux Bubblewrap

Current Linux tool sandbox uses Bubblewrap.

Observed controls include:

- workspace read/write shaping;
- explicit filesystem path grants;
- network control;
- protected governance files;
- seccomp denial of `ptrace`;
- environment sanitization;
- dynamic additional permission expansion.

The implementation protects governance paths such as `.git` / ignore files from ordinary writes while selectively enabling Git metadata when necessary.

### ACL reuse candidate

A worker sandbox profile should explicitly describe:

- workspace mount;
- read/write mounts;
- forbidden paths;
- network;
- credentials;
- system-call/process constraints;
- realized backend/version.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/sandbox/linux/LinuxSandboxManager.ts

## 7.3 macOS and Windows

Current project architecture also contains:

- macOS Seatbelt integration;
- Windows Job Object / Low Integrity / helper-based sandboxing.

Current issue evidence demonstrates that platform parity is not automatic.

Examples:

- Windows command-safety argument validation currently differs from POSIX;
- open #28598 reports a Seatbelt/Git startup compatibility failure on 0.53.0.

### ACL lesson

`Sandbox = enabled` is not sufficient evidence.

Qualification needs:

`OS + sandbox backend + exact build + policy profile + regression fixtures`.

## 7.4 Tool sandboxing versus full-process sandbox

Current documentation distinguishes:

- sandboxing individual tools;
- running the CLI itself inside a larger Docker/Podman/Seatbelt environment.

These are different authority architectures.

A full-process sandbox may contain both:

- the agent process that must contact Gemini/Vertex;
- model-selected execution.

That creates credential/network coupling not present in a brokered design.

---

# 8. Provider credential isolation gap in full-process sandboxing

Issue #23136 describes a concrete architectural concern:

When Gemini CLI uses full-process sandboxing with Vertex/ADC-style credentials, the agent needs credentials/network access to call its provider. If model-selected shell commands execute in that same container/security identity, they can share access to those credentials/network paths.

The issue requested separation between:

- agent API network/identity;
- untrusted execution network/identity.

It was closed as stale/not planned rather than resolved.

### ACL/Vera lesson

This reinforces a core ACL design rule:

**The model-provider control plane and the worker effect plane should not need the same credential namespace.**

Preferred topology:

`trusted supervisor/provider client`
→ model request

separate from:

`worker sandbox`
→ narrowly authorized tools/effects.

Provider credentials should remain inaccessible to worker code unless a task explicitly requires them.

Primary source:

- https://github.com/google-gemini/gemini-cli/issues/23136

---

# 9. Sandbox expansion is explicit capability negotiation

Current shell behavior can request extra sandbox permissions when a command requires:

- filesystem read;
- filesystem write;
- network.

The UI can support:

- one-time/temporary continuation;
- session approval;
- persisted approval.

Current implementation records persistent/session sandbox permissions by root command and resource permissions.

### High-value pattern

When execution fails because a capability is absent, the correct response is not automatically “disable the sandbox.”

Instead:

1. identify the missing capability;
2. display it;
3. authorize the smallest expansion;
4. retry under the expanded capability;
5. preserve evidence of the grant.

This is highly relevant to Vera’s future service/device permissions.

## 9.1 Boundary: root-command grant is broader than effect identity

A persisted expansion is primarily retrieved by root command.

That is useful convenience policy, but it is not ACL effect authorization.

Example:

granting `npm` network access is a capability grant to a command family, not permission for every future package install to create arbitrary external effects.

### ACL rule

Persisted capability grants and effect-specific approval must remain separate.

Primary sources:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/tools/shell.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/policy/sandboxPolicyManager.ts

---

# 10. Environment sanitization

Gemini CLI has a dedicated environment-sanitization service.

Current logic includes:

- explicit always-allowed names;
- never-allowed names;
- sensitive-name patterns;
- sensitive-value patterns;
- runtime-altering variable blocking;
- policy-configurable allowlists.

Sensitive patterns cover classes such as:

- token;
- secret;
- password;
- key;
- auth;
- credential;
- private/certificate data.

Runtime-altering variables include classes such as:

- `NODE_OPTIONS`;
- `NODE_PATH`;
- `PYTHONPATH`;
- preload/dynamic-loader variables;
- shell startup injection variables.

Recent main-branch work specifically hardens extension environment changes.

## 10.1 Important default boundary

The sanitizer can return a broad copy of the inherited process environment when environment-variable redaction is not enabled for that execution context.

The Noop/no-sandbox path therefore does not establish a minimal child environment merely by invoking the sanitizer.

### ACL rule

Production ACL workers should use a **minimal explicit allowlist** generated from task authority, not a broad parent environment plus heuristic secret deletion.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/environmentSanitization.ts

---

# 11. Provider/runtime boundary

## 11.1 Narrow ContentGenerator contract

Current Gemini CLI separates model access through a `ContentGenerator`-style contract that supports:

- generated content;
- streaming;
- token counting;
- embedding.

Supported authentication/provider routes include:

- Google login / Code Assist;
- Gemini API;
- Vertex AI;
- Google Cloud/ADC variants;
- Gateway/custom Gemini base URL.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/core/contentGenerator.ts

## 11.2 Model routing/fallback is separate from tool execution

The core runtime includes routing and fallback services rather than hardcoding one static model call in every tool/agent.

### ACL reuse candidate

Separate:

- provider adapter;
- model/routing policy;
- tool authority;
- task scheduler.

A model fallback is a model/runtime decision, not permission to widen tool authority.

## 11.3 Local-model boundary

Task 19 found no first-class current provider implementation equivalent to:

- Ollama;
- direct llama.cpp;
- vLLM;
- generic OpenAI-compatible local inference

inside Gemini CLI’s main content-generator provider surface.

`GOOGLE_GEMINI_BASE_URL` / Gateway allows a custom endpoint, but the runtime still speaks Gemini/Google GenAI semantics.

### ACL implication

Gemini CLI is primarily a **Gemini harness/reference**, not a candidate direct local-model runtime for the user’s later 32K local worker benchmark.

A third-party translation gateway could theoretically adapt another model, but Task 19 found no basis to treat that as supported native local-model equivalence.

No local-model winner or adapter choice is selected here.

---

# 12. MCP integration

Gemini CLI supports:

- stdio;
- SSE;
- Streamable HTTP.

It discovers and registers:

- tools;
- prompts;
- resources.

Current MCP configuration can control:

- allowed/excluded server names;
- per-server tool include/exclude lists;
- working directory;
- timeout;
- headers;
- environment;
- trust;
- OAuth/auth provider.

## 12.1 MCP environment handling is stronger than generic ambient inheritance

Current documentation says base inherited environment is sanitized when spawning MCP servers, and explicit per-server environment values are treated as deliberate grants.

### ACL lesson

This is closer to the right credential pattern:

ambient supervisor environment should not automatically become extension/server environment.

However, an explicit env value is still live credential authority and should be scoped/audited.

## 12.2 `trust=true` is broad

A server can be configured as trusted such that confirmations are bypassed.

### ACL rule

MCP server trust must bind to:

- canonical server identity;
- exact transport/auth profile;
- code/package/revision where local;
- tool-definition/schema digest;
- allowed effect classes.

A mutable human server name plus `trust=true` is too weak for production unattended ACL.

## 12.3 MCP resources are data authority too

Remote resources can be read and injected into model context.

That means MCP is not only a tool/effect surface; it is also a **context/provenance surface**.

Vera/ACL must retain origin metadata when external resources become model context or learned memory.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/tools/mcp-server.md

---

# 13. Extensions are executable authority artifacts

Gemini CLI extensions can contribute materially more than prompt text.

Current extension lifecycle can alter:

- MCP servers;
- tool availability;
- policy rules;
- safety checkers;
- context/memory;
- custom commands;
- hooks;
- agents;
- skills.

### ACL trust classification

`Extension != ordinary data`

An extension is closer to a signed/deployed capability package.

Lower-trust extension code should not be allowed to silently become administrator policy.

## 13.1 Install consent is unusually informative

Current install consent can display:

- local MCP command;
- remote endpoint;
- working directory;
- environment names/values with sensitive values masked;
- headers with sensitive values masked;
- transport/auth details;
- include/exclude tool sets;
- trust setting;
- context injection;
- excluded core tools;
- hook warning;
- skills/system-prompt warning.

It also shows a deterministic SHA-256 **configuration signature** for MCP configuration.

### Strong reuse pattern

Approval UI should show the **behavior-bearing configuration**, not only package name/version.

### Boundary

The configuration hash is not:

- publisher identity;
- package-code signature;
- supply-chain provenance;
- proof that the executed binary matches the configuration.

ACL later needs both:

`definition digest`
and
`artifact/provenance identity`.

Primary sources:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/cli/src/config/extensions/consent.ts
- https://github.com/google-gemini/gemini-cli/commit/60d35f48a84a32115dc7095f2a59ab47ab467988

---

# 14. System configuration is part of the security boundary

Current main revision explicitly hardens system-wide configuration paths.

Observed behavior:

- insecure system settings/defaults can be skipped;
- ownership/permission checks protect high-trust config;
- Windows path normalization/ACL handling is hardened;
- warnings are emitted when configuration is rejected.

### ACL/Vera lesson

A policy hierarchy is meaningless if a lower-privileged worker can rewrite the file that defines higher-level policy.

Protected policy requires:

- correct precedence;
- protected storage;
- owner/permission validation;
- version/digest evidence;
- worker exclusion from write authority.

This current commit is useful direct precedent for ACL’s “policy cannot be worker-writable” rule.

Primary source:

- https://github.com/google-gemini/gemini-cli/commit/85aca163f6c73ac6ce380b5447359146b8adcae4

---

# 15. Hooks are deterministic interception points — and trusted code

Gemini CLI hooks can run at lifecycle points around:

- session;
- agent;
- model;
- tool selection;
- tool execution.

They can:

- add context;
- validate/block actions;
- log;
- alter control flow.

### Reuse candidate

ACL can benefit from deterministic hooks around:

`before_model`
`before_tool`
`after_tool`
`before_acceptance`
`before_effect_commit`
`on_checkpoint`
`on_resume`.

### Boundary

Hooks are executable code with significant authority.

They should be:

- versioned;
- provenance tracked;
- protected from worker mutation;
- capability scoped;
- unable to silently weaken higher-level policy.

A hook event log is not independent verification if the same worker can mutate the hook or its evidence.

---

# 16. Local subagents: strong logical capability shaping

Gemini CLI’s current local-subagent architecture provides:

- independent model context;
- independent tool registry;
- independent prompt/resource registries;
- a distinct subagent identity;
- model/run-limit overrides;
- recursion protection;
- subagent-specific policy matching;
- optional agent-private MCP servers.

## 16.1 Explicit tools narrow capability

Agent definitions can name tools and MCP wildcard subsets.

Agent tools are excluded from child registries to prevent recursive agent spawning.

This is strong role/capability shaping.

## 16.2 Dangerous default: omission means inherit all parent tools

Current docs and source establish:

- if a subagent’s tools are omitted, it inherits all available parent tools;
- the built-in `generalist` is explicitly intended to inherit broad/full capability.

### ACL rule

Production child roles should default to **no effect capability**, then receive an explicit minimum set.

Inheritance-by-omission is convenient for an interactive product but too broad for ACL’s unattended workers.

## 16.3 Logical isolation is not OS isolation

Current local subagents create separate agent objects/registries/context loops inside the runtime.

This does not by itself establish:

- separate OS user;
- separate process tree;
- separate filesystem sandbox;
- separate environment/credentials.

### ACL rule

Use distinct terminology:

- context isolation;
- tool-registry isolation;
- process isolation;
- filesystem/network isolation;
- credential isolation.

Primary sources:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/core/subagents.md
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/agents/local-executor.ts

---

# 17. Subagent lifecycle limits and explicit completion

Current local-agent execution includes:

- maximum turns;
- maximum wall time;
- cancellation/abort signals;
- a mandatory `complete_task` protocol;
- a bounded final recovery/grace turn when normal completion fails.

### Reuse candidate

A child agent should terminate through a machine-observable protocol, not “the model stopped talking.”

If the model fails to call its completion tool, that is a protocol failure.

### Boundary

`complete_task` is still model-produced completion.

ACL acceptance still requires independent verifier/effect evidence.

A subagent saying “complete” cannot promote its own work.

---

# 18. Remote subagents and A2A

Gemini CLI supports remote subagents via Agent-to-Agent (A2A).

Current remote-agent configuration can bind:

- agent card URL/JSON;
- API key;
- HTTP auth;
- Google credentials;
- OAuth;
- dynamic secret values;
- proxy.

Google credential mode restricts token forwarding to recognized Google-host patterns.

### Strong reference

This is useful Vera precedent for:

`local controller`
→ `remote specialized service/agent`

with an explicit protocol/auth boundary.

## 18.1 Dynamic `!command` secrets are executable credential acquisition

Remote-agent credentials can be resolved using a shell command such as token-generation commands.

That is convenient, but it means credential resolution itself has execution authority.

### ACL rule

Credential acquisition belongs in a trusted broker/control-plane process, not arbitrary project agent definitions.

Project files should reference named credential grants, not execute arbitrary token commands under worker authority.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/core/remote-agents.md

---

# 19. ACP: useful client/runtime boundary with current recovery hazards

Gemini CLI exposes an experimental Agent Client Protocol path.

Current ACP session manager supports:

- session create;
- session load;
- authentication;
- model/mode exposure;
- client filesystem capability;
- client-supplied MCP servers.

## 19.1 Good security ordering for new/loaded session initialization

Current code explicitly authenticates **before** full config initialization/MCP startup in `initializeSessionConfig`.

The code comment states the reason: avoid executing potentially unsafe server definitions before authentication.

### Vera reuse candidate

An authenticated client/runtime boundary should validate caller/session authority before activating externally supplied tools/extensions.

## 19.2 Current ACP load ordering remains unsafe — open #28693 / #28775

Open reports describe a same-minute failure where `session/load` can make the session it intends to load non-resumable.

Task 19 checked current main.

Current `loadSession()` still:

1. calls `initializeSessionConfig(sessionId, ...)`;
2. initializes config;
3. only afterward constructs `SessionSelector`;
4. resolves the stored session.

This matches the core ordering described in the issue.

Current code also invokes history replay as a floating promise:

`session.streamHistory(sessionData.messages)`

without awaiting completion before returning the load response.

### ACL/Vera regression fixture

A resume/load operation must:

1. locate/read immutable candidate state;
2. validate it;
3. acquire writer/continuation ownership;
4. bind current authority;
5. only then mutate active runtime state;
6. never write into the source checkpoint as a side effect of “find/load.”

### Candidate invariant

**Read-before-create** for recovery.

A resume operation is not allowed to create/overwrite the namespace it is trying to discover.

Primary sources:

- https://github.com/google-gemini/gemini-cli/issues/28693
- https://github.com/google-gemini/gemini-cli/issues/28775
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/cli/src/acp/acpSessionManager.ts

---

# 20. Session persistence: append-oriented semantic history

Current `ChatRecordingService` stores per-project conversation data in JSONL.

The log can contain:

- metadata;
- messages;
- tool-call records;
- thoughts;
- token metadata;
- `$set` metadata updates/checkpoints;
- `$rewindTo` events;
- summary;
- directories;
- session/subagent kind;
- memory scratchpad metadata.

The loader folds those records into current semantic state.

### Strong pattern

Durable session state can be represented as an append-oriented event/history stream rather than rewriting one large JSON object every turn.

This is useful for:

- crash forensics;
- repair;
- rewind;
- incremental append.

## 20.1 Rewind is semantic, not destructive log erasure

`$rewindTo` allows the loader to derive a previous logical history while retaining the historical log record.

### ACL reuse candidate

For operator/audit history, prefer append-only transition records plus explicit supersession/rewind over destructive history rewriting.

---

# 21. Session-file repair is transactional

When a resumed session file cannot be reloaded, current code can:

1. preserve the unreadable existing file under a backup name;
2. reconstruct from in-memory session data;
3. write a temporary replacement;
4. rename it atomically;
5. clean the temp file on failure.

### Strong reuse pattern

This is substantially safer than delete-then-copy.

It directly contrasts with the destructive restore ordering found in Letta Task 18.

### ACL/Vera invariant

Authoritative state replacement:

`stage -> validate -> atomic switch`

never:

`delete current -> attempt copy`.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/chatRecordingService.ts

---

# 22. Durability can silently degrade on disk-full

Current chat recorder has explicit ENOSPC behavior.

When disk is full:

- it warns;
- disables further chat recording;
- the conversation can continue live.

### Product rationale

For an interactive user, continuing may be preferable to crashing.

### ACL boundary

For an unattended worker, “live but no longer durably checkpointed” is a major state transition.

ACL should not silently continue checkpoint-dependent work.

Candidate states:

- `durable`;
- `durability_degraded`;
- `pause_required`;
- `recovery_required`.

### Candidate invariant

If durable evidence/checkpoint persistence is required by the task contract, loss of persistence is a **hard execution gate**, not only a log warning.

---

# 23. Current stable resume deletion report — open #29198

Open #29198 reports on stable Gemini CLI `0.58.0`:

- resume an existing session;
- exit immediately without issuing a new instruction;
- the session then disappears from resume/list behavior.

Current code includes cleanup logic that deletes a current session when the recorder determines it contains no resumable content.

Task 19 does not claim the full root cause of #29198 without a fresh runtime reproduction, but the current cleanup/resume boundary makes it a high-value fixture.

### ACL regression fixture

- load a durable session;
- make **zero** new semantic mutations;
- close normally;
- assert original checkpoint/history remains unchanged and still resumable.

Primary sources:

- https://github.com/google-gemini/gemini-cli/issues/29198
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/chatRecordingService.ts

---

# 24. Workspace checkpointing via shadow Git

Gemini CLI’s checkpointing feature can create a project snapshot before modifying file tools.

Current documentation records three associated pieces:

1. Git workspace snapshot;
2. conversation history;
3. original tool call.

The workspace snapshot lives in a separate “shadow” Git repository so it does not mutate the project’s own Git history.

### Strong pattern

This is useful ACL precedent for **pre-effect workspace checkpointing**.

Tool-call evidence and workspace snapshot should be linked.

## 24.1 Current checkpointing is disabled by default

It must be explicitly enabled.

### ACL difference

For an unattended ACL role authorized to modify code, pre-effect checkpoints may need to be mandatory by policy rather than optional product preference.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/cli/checkpointing.md

---

# 25. Shadow-Git checkpoint is not complete machine/effect state

Current implementation:

- copies the project `.gitignore` into the shadow repository;
- stages with `git add .`;
- commits the snapshot;
- restore uses Git restore;
- then `git clean -f -d`.

### Derived limitation

Ignored files are not normal snapshot content.

`git clean -f -d` also does not remove ignored files.

Therefore the documentation phrase “complete state of your project files” should not be interpreted as:

- all ignored/generated files;
- environment;
- processes;
- database/service state;
- network effects;
- credentials;
- external APIs.

### ACL rule

A code workspace checkpoint is one state domain only.

Required checkpoint manifest may need:

- workspace tree/digest;
- Git/index state;
- dependency/runtime manifest;
- process settlement;
- external effect ledger;
- verification state;
- current authority references.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/gitService.ts

---

# 26. Shadow Git explicitly isolates Git configuration

Current `GitService` takes meaningful precautions:

- dedicated shadow-repo author identity;
- disables GPG signing;
- replaces global/system Git config paths;
- clears `GIT_DIR` / `GIT_WORK_TREE`;
- sanitizes environment.

### Reuse candidate

Internal deterministic infrastructure should not unknowingly inherit user/project Git aliases, hooks, credential helpers, signing configuration or environment behavior.

This is especially important when an agent can edit local Git configuration.

---

# 27. Auto-memory is background extraction, not canonical truth

Current Gemini CLI includes background memory/skill extraction logic.

Observed implementation includes:

- per-workspace extraction state;
- an exclusive create-if-not-exists lock;
- stale lock cleanup;
- PID/age checks;
- throttling;
- session version tracking;
- batch limits;
- extraction run metadata.

This is useful long-running-agent infrastructure.

## 27.1 Lock is coordination, not distributed durable fencing

The lock is a local filesystem/PID/age mechanism.

It does not prove safe distributed multi-host ownership.

### ACL lesson

For one machine/process family, a lockfile can be useful.

For ACL’s authoritative project/run writer, retain generation/lease/fencing semantics if multiple supervisors/processes can contend.

## 27.2 Learned memory still needs provenance/trust

Auto-memory can learn from session history.

That does not make extracted statements verified truth.

Task 18’s Letta result still applies:

`learned memory != evidence != security policy`.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/memoryService.ts

---

# 28. Context compression and persisted history are different state representations

Gemini CLI has active-context compression in addition to durable session recording.

Current/open issue #21335 documents a case where `/compress` can alter in-memory context but not persist the same compressed state to disk for resume.

Task 19 treats this as an issue-scoped representation-boundary warning rather than a universal current failure claim.

### ACL/Vera rule

Separate:

- canonical interaction/evidence history;
- current active model context;
- summary/compaction artifact;
- UI history;
- learned long-term memory.

A summary is not a replacement for canonical evidence unless an explicit irreversible retention policy says so.

---

# 29. Behavior/state identity must stay unified across resume

Gemini CLI’s historical/current issue set contains multiple cases where parts of resumed state can diverge:

- conversation history;
- task/plan/tracker state;
- ACP session state;
- active UI/session listing;
- compressed versus durable context.

Even when individual bugs are fixed, the architectural lesson is durable.

### ACL invariant

A resume checkpoint references one versioned manifest of all authoritative state domains.

Subsystems do not independently guess “latest.”

At minimum:

`project_id`
`run_id`
`task_id`
`workspace_checkpoint_id`
`conversation/evidence_id`
`policy_version`
`capability_profile`
`pending_effect_set`
`verifier_state`.

---

# 30. Behavioral evaluation architecture

Gemini CLI’s eval system makes an important distinction:

- deterministic integration tests;
- model behavioral evals.

Behavioral evals are explicitly non-deterministic.

Current policies:

- `ALWAYS_PASSES`;
- `USUALLY_PASSES`.

New behavioral evals start as `USUALLY_PASSES`.

Promotion requires observed stability across repeated nightly runs/models.

Current nightly evaluation runs repeat tests and retain model-specific pass rates.

The project also uses dynamic-baseline regression checks.

### Very strong ACL benchmark lesson

Do not collapse these into one score:

1. deterministic runtime correctness;
2. model behavioral reliability;
3. end-to-end task success.

A local model can be good while its harness/parser fails.

A deterministic runtime can be correct while model behavior is probabilistic.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/evals/README.md

---

# 31. `USUALLY_PASSES` is a useful qualification state

Gemini’s evaluation process is useful precedent for ACL’s later model-role benchmark.

Rather than immediately declaring:

`capability=true`

a deployment can progress through:

- discovered;
- works once;
- usually reliable;
- verified stable under exact fixture/profile;
- production-qualified.

### ACL candidate

For model/harness behavior, store:

- trial count;
- pass distribution;
- failure taxonomy;
- exact model/runtime/harness;
- fixture version;
- confidence threshold.

This aligns with the user’s plan to benchmark local models at 32K only after the external research campaign is complete.

---

# 32. OpenTelemetry observability

Gemini CLI provides OpenTelemetry support for:

- logs;
- metrics;
- traces.

Telemetry is opt/config controlled.

Telemetry configuration includes destination/protocol and detailed tracing options.

### ACL reuse candidate

Instrument:

- model request;
- tool request;
- policy decision;
- confirmation;
- sandbox grant/denial;
- effect start/end;
- checkpoint;
- verifier result;
- retry/recovery.

### Boundary

Operator telemetry is not authoritative acceptance evidence.

A trace is written by the runtime being observed.

Independent verifier artifacts still need protected provenance.

Primary source:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/cli/telemetry.md

---

# 33. Sensitive telemetry/logging boundary

Prompt, tool and model traces can contain:

- user content;
- code;
- tool arguments;
- tool results;
- paths;
- provider metadata;
- credential-adjacent values.

### ACL/Vera rule

Telemetry needs:

- audience classification;
- redaction;
- retention;
- local/cloud destination policy;
- opt-in/required categories.

Never enable maximal debugging as a default production evidence strategy.

---

# 34. Browser agent shows capability-specific safety policy

Current built-in browser agent includes explicit controls for:

- allowed domains;
- blocked URL schemes;
- form-fill confirmation;
- optional upload/script confirmation;
- hard file-upload blocking;
- max actions per task;
- session/profile modes.

### Useful ACL/Vera lesson

Different effect domains need **domain-specific policy**, not one universal “tool approved” bit.

Browser/navigation authority should be expressed as:

- allowed origins;
- credential/profile identity;
- upload/download policy;
- script execution;
- sensitive form action;
- action count/rate.

This will matter later for Vera’s browser/service integrations.

## 34.1 Persistent browser profile is durable authority

The browser agent’s default persistent profile preserves cookies/history/settings across sessions.

That is a credential/session authority boundary.

A “browser subagent” can therefore inherit real logged-in external authority even if its model context is isolated.

### ACL/Vera rule

Browser profile identity belongs in capability/effect identity.

---

# 35. Current failure fixtures

Task 19 records current/open failures as versioned fixtures, not permanent universal claims.

## 35.1 Windows `git diff --output` bypass — #29189

Status:

- open;
- stable v0.58 reproduction;
- current main source retains subcommand-only Windows Git safe classification;
- fix PR #29184 open/unmerged.

Fixture:

`safe-looking command + effect-bearing flag`

must not bypass policy.

## 35.2 ACP read-to-load corruption — #28693 / #28775

Status:

- open;
- reproduced on prior releases;
- current main retains initialization-before-resolution ordering and floating history replay.

Fixture:

resume/load must not mutate candidate session before candidate resolution.

## 35.3 Resume then immediate exit deletes resumability — #29198

Status:

- open;
- reproduction against stable 0.58.0.

Fixture:

resume + zero new actions + exit must be observationally idempotent.

## 35.4 Full-process sandbox credential/control-plane coupling — #23136

Status:

- closed stale/not-planned, not fixed by a recorded architectural replacement in the issue.

Fixture:

worker execution cannot read/use model-provider credentials merely because the supervisor must use them.

## 35.5 macOS sandbox compatibility — #28598

Status:

- open issue against 0.53.0 reporting Seatbelt startup crash when launched in a Git repository.

Fixture:

each supported OS/backend must pass startup, Git, checkpoint and effect tests.

## 35.6 Model obeying natural-language “hold” is not authority

Issues such as #26390/#27090 report model attempts to continue/edit or find broader shell paths despite natural-language/user-intent boundaries.

These are anecdotal issue evidence, not deterministic proof of current model behavior.

The architectural lesson is still firm:

**Natural-language instruction is not an authorization mechanism.**

If a user says “research only” or “do not modify,” the runtime should be able to remove/deterministically deny modification capabilities for that state.

---

# 36. Failure taxonomy for ACL derived from Gemini CLI

Gemini CLI reinforces the need to distinguish:

1. model reasoning/action-selection failure;
2. provider/API failure;
3. model routing/fallback failure;
4. tool-schema/parser failure;
5. policy classification failure;
6. safety-checker failure;
7. sandbox-realization failure;
8. environment/credential leakage;
9. extension/plugin trust failure;
10. subagent capability inheritance failure;
11. session-recording failure;
12. resume/state-join failure;
13. checkpoint/workspace recovery failure;
14. effect-settlement failure;
15. telemetry/evidence failure;
16. behavioral eval instability.

Do not score all of those as “model failed.”

---

# 37. Concrete ACL/Vera candidate invariants from Gemini CLI

1. Tool authorization is deterministic and independent of model intent.
2. Non-interactive unresolved authority defaults to deny.
3. Policy identity includes trusted tool origin, normalized arguments/resources, actor/subagent and execution mode.
4. Higher-trust policy tiers structurally override lower-trust extension/project policy.
5. Policy storage ownership/mutability is part of policy correctness.
6. Worker-writeable policy is not policy.
7. MCP server identity is part of tool authority.
8. MCP server human name alone is insufficient; bind trusted origin/config/schema digest.
9. Shell redirection is an effect capability.
10. Executable/subcommand allowlists are insufficient without flag/argument semantics.
11. Parser uncertainty does not become permission.
12. Safety-checker failure fails closed.
13. YOLO/auto-approval is workflow convenience, not production sandboxing.
14. Planner/read-only roles remove effect tools deterministically rather than relying on prompt compliance.
15. Sandbox configuration and realized sandbox backend are separate evidence.
16. Sandbox identity includes OS/backend/version/profile/mounts/network/credentials.
17. Filesystem and network permissions are explicit capabilities.
18. Capability expansion is shown and granted minimally instead of disabling isolation.
19. Persisted capability expansion is not effect-specific approval.
20. Model-provider credentials stay outside worker execution namespaces.
21. Worker environments are minimal explicit allowlists, not parent-env copies with heuristic redaction.
22. MCP child environment receives only deliberate grants.
23. Extensions are executable authority packages, not prompt data.
24. Extension approval binds behavior-bearing configuration digest.
25. Definition hash and publisher/artifact provenance are separate requirements.
26. Extension policy/checkers cannot outrank administrator/project-owner authority.
27. Hooks are trusted executable code and live outside worker mutation authority.
28. Local child agents default to no effects; capabilities are added explicitly.
29. Child tool-registry isolation is not OS/process/credential isolation.
30. Child agents cannot recursively widen the agent control plane.
31. Completion protocol is distinct from independent acceptance verification.
32. Remote-agent credential resolution belongs to a trusted broker.
33. Remote protocol authentication does not authorize every downstream effect.
34. ACP/client authentication occurs before activating client-supplied executable server definitions.
35. Resume/load locates and validates source state before creating/mutating active state.
36. Read-only recovery operations do not mutate candidate checkpoint namespaces.
37. Session event logs favor append/supersede/rewind over destructive history mutation.
38. Unreadable-state repair preserves source bytes and uses stage→atomic-switch.
39. Loss of durable recording is an explicit execution-state transition.
40. Unattended checkpoint-required work pauses on persistence failure.
41. Workspace checkpoint is distinct from process/effect/provider/verification state.
42. Pre-effect code modification checkpointing is policy-mandatory for designated ACL roles.
43. Checkpoint manifests disclose ignored/untracked/external state exclusions.
44. Internal Git infrastructure does not inherit user aliases/hooks/credential helpers implicitly.
45. Active model context, canonical conversation/evidence, UI projection and learned memory are separate.
46. Auto-memory extraction lock is coordination, not distributed writer fencing.
47. Learned memory never becomes security policy merely because it was extracted repeatedly.
48. Resume binds all authoritative state domains through one versioned checkpoint manifest.
49. Model routing/fallback does not widen tool authority.
50. Provider/harness identity includes exact CLI revision, model, auth/provider route and routing configuration.
51. Gemini Gateway compatibility is not generic local-model compatibility.
52. Behavioral model capability is probabilistic and separately qualified from deterministic runtime correctness.
53. Capability promotion requires repeated evidence, not one successful run.
54. Benchmark/eval identity includes exact model/runtime/harness/fixture.
55. Operator telemetry is separate from protected verifier evidence.
56. Sensitive telemetry has explicit destination/redaction/retention policy.
57. Browser/session profile identity is an authority-bearing capability.
58. Domain-specific effects receive domain-specific policy (filesystem, shell, browser, service APIs).
59. Current upstream security/recovery issues become versioned regression fixtures.
60. No current project is trusted because of brand/vendor; deployment behavior is verified empirically.

---

# 38. High-value regression fixtures for later ACL work

## Fixture A — effect-bearing “read-only” flag

- mark a base subcommand read-only;
- add output/write flag;
- assert deterministic policy detects effect;
- assert no silent write.

Based on Gemini #29189.

## Fixture B — resume is observationally safe

- create durable session;
- stop;
- resume with zero mutation;
- exit;
- assert source session bytes/state remain resumable.

Based on #29198.

## Fixture C — ACP load ordering

- create session;
- attempt load immediately;
- assert load does not create/overwrite the namespace before resolving candidate;
- assert history replay ordering completes before success response if protocol requires it.

Based on #28693/#28775.

## Fixture D — provider credential isolation

- supervisor has provider credential;
- worker tool environment does not;
- worker attempts env/file/metadata/token retrieval;
- must fail while model calls continue.

Based on #23136.

## Fixture E — sandbox expansion

- command needs one external path;
- deny initially;
- request one path;
- grant one path;
- verify unrelated paths/network remain denied.

## Fixture F — policy hierarchy

- low-trust extension says allow;
- admin says deny;
- deny must win;
- worker cannot rewrite admin policy.

## Fixture G — subagent omission default

ACL expected behavior:

- child definition omits tools;
- child receives no effect tools.

This intentionally differs from Gemini CLI’s convenient inherit-all default.

## Fixture H — persistence loss

- fill/checkpoint storage to ENOSPC;
- runtime detects inability to persist;
- ACL pauses before additional effect-bearing work.

## Fixture I — checkpoint ignored-file disclosure

- create ignored file and nonignored file;
- take code checkpoint;
- mutate both;
- recovery must either restore both or explicitly prove ignored file is outside checkpoint contract.

## Fixture J — behavior eval promotion

- run same exact model/harness/fixture repeatedly;
- distinguish deterministic harness failure from stochastic model behavior;
- promote only after defined reliability threshold.

---

# 39. What Gemini CLI does not solve for ACL/Vera

Task 19 found no basis to delegate these responsibilities to Gemini CLI itself:

- ACL project/backlog/dependency scheduling;
- local-model role benchmarking across Ollama/llama.cpp/vLLM;
- distributed multi-process durable writer fencing;
- exact worker process-tree settlement;
- minimal service credential broker;
- external-effect identity and reconciliation;
- exactly-once irreversible-effect semantics;
- protected independent verifier fixtures;
- cross-run acceptance authority;
- Vera personal-memory epistemic provenance;
- safety-critical memory conflict resolution;
- complete device/service permission governance;
- final ACL/Vera architecture or dependency selection.

Gemini CLI is strongest as a reference for:

- policy;
- sandbox capability negotiation;
- host-tool execution;
- protocol adapters;
- session/checkpoint UX;
- subagent capability shaping;
- extension consent;
- behavioral evaluation methodology.

---

# 40. Later comparison questions

When the research campaign reaches synthesis:

1. Should ACL adapt a PolicyEngine-like tier/rule/checker structure?
2. Which parts of Gemini’s shell normalization are reusable versus too CLI-specific?
3. Should ACL use per-tool Bubblewrap/Seatbelt/Windows isolation, containers, or a different worker boundary?
4. Can Gemini’s sandbox-expansion UX/policy model inform Vera service/device permissions?
5. Which checkpoint features should ACL preserve beyond Git-visible source files?
6. Should ACL use an append-oriented semantic run/event log similar to ChatRecordingService?
7. Which session repair/rewind mechanisms complement, rather than replace, ACL checkpoints/effect state?
8. Can the GDK/Goose ACP pattern and Gemini ACP pattern share one Vera client abstraction?
9. Which A2A mechanisms remain useful after Google ADK research?
10. Should ACL import Gemini-style extension config signatures while adding package/provenance signatures?
11. How should ACL prevent extension/checker packages from becoming hidden policy-escalation channels?
12. Which subagent capability defaults should deliberately differ from Gemini’s inherit-all convenience?
13. Which Gemini behavioral eval methods should inform the later 32K local-model benchmark lab?
14. Which current Gemini security/recovery fixtures should become cross-harness fixtures for Cline/OpenHands/Goose/Codex?
15. Is Gemini CLI useful as a cloud/Gemini comparison harness even if it is not a local worker runtime?

No answer is selected in Task 19.

---

# 41. Primary source inventory

Canonical project / revision / release:

- https://github.com/google-gemini/gemini-cli
- https://github.com/google-gemini/gemini-cli/tree/85aca163f6c73ac6ce380b5447359146b8adcae4
- https://github.com/google-gemini/gemini-cli/commit/85aca163f6c73ac6ce380b5447359146b8adcae4
- https://github.com/google-gemini/gemini-cli/releases/tag/v0.58.0
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/LICENSE

Policy / shell authority:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/policy/policy-engine.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/reference/policy-engine.md
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/tools/shell.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/policy/sandboxPolicyManager.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/sandbox/windows/commandSafety.ts

Sandbox / environment:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/sandboxManager.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/sandbox/linux/LinuxSandboxManager.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/environmentSanitization.ts
- https://github.com/google-gemini/gemini-cli/issues/23136
- https://github.com/google-gemini/gemini-cli/issues/28598

Provider/model:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/core/contentGenerator.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/core/client.ts

MCP / extensions / hooks:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/tools/mcp-server.md
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/utils/extensionLoader.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/cli/src/config/extensions/consent.ts
- https://github.com/google-gemini/gemini-cli/commit/60d35f48a84a32115dc7095f2a59ab47ab467988
- https://github.com/google-gemini/gemini-cli/tree/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/hooks

Subagents / A2A:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/core/subagents.md
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/agents/local-executor.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/core/remote-agents.md

ACP/session:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/cli/src/acp/acpSessionManager.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/chatRecordingService.ts
- https://github.com/google-gemini/gemini-cli/issues/28693
- https://github.com/google-gemini/gemini-cli/issues/28775
- https://github.com/google-gemini/gemini-cli/issues/29198
- https://github.com/google-gemini/gemini-cli/issues/21335

Checkpointing / memory:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/cli/checkpointing.md
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/gitService.ts
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/packages/core/src/services/memoryService.ts

Evals / telemetry:

- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/evals/README.md
- https://github.com/google-gemini/gemini-cli/blob/85aca163f6c73ac6ce380b5447359146b8adcae4/docs/cli/telemetry.md

Current security/recovery fixtures:

- https://github.com/google-gemini/gemini-cli/issues/29189
- https://github.com/google-gemini/gemini-cli/pull/29184
- https://github.com/google-gemini/gemini-cli/issues/29198
- https://github.com/google-gemini/gemini-cli/issues/28693
- https://github.com/google-gemini/gemini-cli/issues/28775
- https://github.com/google-gemini/gemini-cli/issues/23136
- https://github.com/google-gemini/gemini-cli/issues/28598
- https://github.com/google-gemini/gemini-cli/issues/26390
- https://github.com/google-gemini/gemini-cli/issues/27090

---

# Conclusion

Gemini CLI is a high-value architecture reference because it combines a sophisticated agent product with increasingly explicit deterministic controls.

The strongest reusable mechanisms are:

- tiered deterministic policy;
- argument/resource-aware shell policy;
- safety-checker layering;
- fail-closed noninteractive behavior;
- platform sandbox managers;
- explicit filesystem/network expansion;
- protected governance/config paths;
- provider/runtime abstraction;
- isolated subagent registries;
- MCP/ACP/A2A adapters;
- extension behavior disclosure and config signatures;
- append-oriented session records;
- transactional unreadable-session repair;
- pre-modification shadow-Git checkpoints;
- behavioral eval reliability classes;
- OpenTelemetry instrumentation.

The strongest warnings are:

- YOLO intentionally trades policy friction for broad execution;
- full-process sandboxing can conflate provider credentials and worker execution identity;
- broad inherited environment remains possible outside strict sanitization profiles;
- capability persistence and effect authorization are different problems;
- child agents can inherit the parent’s full tool surface when unspecified;
- logical subagent isolation is not OS/credential isolation;
- checkpointing is Git-visible workspace recovery, not complete state/effect recovery;
- ignored/external state is outside the shadow-Git snapshot contract;
- session persistence does not guarantee safe resume;
- current ACP load ordering remains consistent with an open self-corrupting resume bug;
- stable v0.58 has a current resume/exit deletion report;
- current Windows command safety still has an open write-via-`git diff --output` bypass;
- loss of disk persistence can allow live conversation to continue without durable recording;
- Gemini CLI does not supply a native local-model runtime comparable to Ollama/llama.cpp/vLLM.

Task 19 therefore supports treating Gemini CLI as a serious reference for **ACL/Vera authority mechanics, sandbox permission negotiation, session/checkpoint UX, protocol integration, and behavioral evaluation**, while retaining ACL/Vera’s stronger outer layers for least-privilege worker environments, provider credential separation, durable cross-process state, external-effect settlement, independent verification, and provenance-aware long-term memory.

No Gemini CLI dependency, model assignment, provider choice, policy design, sandbox implementation or cross-project winner is selected in Task 19.

**Stopped before Graphiti.**
