# Pydantic AI Deep Research

**Task:** ranked project deep research #1  
**Project:** Pydantic AI + the official Pydantic AI Harness where directly relevant  
**Canonical core:** https://github.com/pydantic/pydantic-ai  
**Official harness:** https://github.com/pydantic/pydantic-ai-harness  
**Accessed:** 2026-09-05  
**Scope boundary:** extract architecture, failure surfaces, reusable mechanisms and ACL/Vera lessons; do not make an adoption decision and do not begin Cline research.

## Direct answer

Pydantic AI earned its #1 research position. The important finding is not that ACL should simply adopt it wholesale. The important finding is that the Pydantic ecosystem now exposes a unusually dense set of concrete implementations for problems ACL has already identified: typed tool contracts, provider/model capability normalization, bounded retries, cancellation ownership, local Ollama support, trace-based evaluation, workspace-scoped file tools, shell environment controls, model-owned planning, bounded persistent memory, sub-agent budgets, compaction, durable operations and crash evidence.

The strongest architectural boundary is:

- **Pydantic AI core** is primarily a typed agent/model/tool execution layer.
- **Pydantic AI Harness** is an official, separate capability layer that adds coding-agent and long-running-agent concerns.
- **Application/OS security remains above or below both layers.** Typed schemas, approval flows, command allowlists and rooted file APIs are not substitutes for process/container isolation, credential scoping or project-level authority policy.

For ACL/Vera, the highest-value output of this task is therefore a set of mechanisms and invariants to compare later, not a dependency decision.

## 1. Current project health and maturity

### Pydantic AI core

Observed:

- Public MIT-licensed repository; not archived.
- Very active release cadence when checked: v2.38.0 on 2026-09-03, v2.39.0 on 2026-09-04 and v2.40.0 on 2026-09-05.
- Current development includes explicit concurrency/cancellation guidance and lifecycle refactoring driven by real production bugs.
- The codebase separates agent orchestration, tool management, normalized messages, model adapters, provider clients, model-family profiles, capabilities, durable-execution adapters and UI/event conversion.

Primary sources:

- https://github.com/pydantic/pydantic-ai
- https://github.com/pydantic/pydantic-ai/releases
- https://github.com/pydantic/pydantic-ai/blob/main/LICENSE
- https://github.com/pydantic/pydantic-ai/blob/main/agent_docs/pydantic-ai-slim.md

### Official Pydantic AI Harness

Observed:

- Separate official repository: `pydantic/pydantic-ai-harness`.
- Package description: "The official capability library and harness for Pydantic AI."
- MIT licensed, but explicitly classified **Development Status :: 3 - Alpha**.
- Requires `pydantic-ai-slim>=2.38.0` at the inspected revision.
- 0.x version policy explicitly allows API changes between minor releases.
- Fast release cadence: v0.27.0 on 2026-08-27, v0.28.0 on 2026-08-31/09-01, v0.28.1 on 2026-09-02/03 and v0.29.0 on 2026-09-03/04.
- CI configuration requires 100% branch coverage; filesystem and shell are additionally mutation-tested.

Primary sources:

- https://github.com/pydantic/pydantic-ai-harness
- https://github.com/pydantic/pydantic-ai-harness/blob/main/pyproject.toml
- https://github.com/pydantic/pydantic-ai-harness/releases
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/mutation-testing.md

**Interpretation:** core project health is strong. The Harness is technically serious but young and fast-moving. That combination makes it valuable research material and a plausible selective component source, but whole-harness coupling/pinning/forking is a later decision.

## 2. Architecture: keep provider quirks out of orchestration

The core architecture has explicit seams rather than a single agent class owning every concern.

Important layers observed in current source/docs:

| Layer | Responsibility | ACL/Vera relevance |
|---|---|---|
| `Agent` / prepared run | Public configuration and lifecycle entry | clear run ownership boundary |
| `_agent_graph.py` | model/tool loop, request assembly, usage limits, finalization | harness-controlled state machine |
| tool manager / toolsets | discovery, schema validation, execution, retries, approval/defer | typed tool boundary |
| output layer | output schemas, processors, validation | structured task-result contracts |
| normalized messages | provider-independent history/protocol | stable evidence/state format |
| models | normalized model requests/responses to provider wire format | local/cloud interchange seam |
| providers | clients, base URLs, auth, HTTP lifecycle | provider plumbing stays isolated |
| profiles | model-family capabilities and quirks | explicit capability matrix |
| capabilities | cross-cutting run/tool behavior | composable harness extensions |
| durable execution | Temporal/DBOS/Prefect integrations | long-running recovery seam |

A particularly relevant current refactor is that run setup/resource ownership is no longer allowed to grow indefinitely in one `Agent.iter()` seam. Current architecture exposes `_prepare_run()` and `_PreparedAgentRun.open()` to separate run preparation from entered-resource lifetime.

**ACL lesson:** use narrow named owners for lifecycle responsibilities. Do not let one planner/worker object accumulate model selection, tool authority, process cleanup, checkpointing, telemetry and recovery merely because they happen in one run.

Primary source:
- https://github.com/pydantic/pydantic-ai/blob/main/agent_docs/pydantic-ai-slim.md

## 3. Tool contracts: schemas are useful but are not authority

Pydantic AI generates tool schemas from Python callables or explicit definitions, validates tool arguments before execution and can return validation feedback to the model as a retry prompt. Output tools use the same typed machinery.

Current output approaches include:

- tool-based structured output;
- provider-native structured output when the model/profile supports it;
- prompted structured output;
- ordinary text.

Tool calls may execute concurrently; individual function tools can be marked sequential. Usage limits can bound tool calls and logical model requests. Importantly, a parallel batch that exceeds the remaining tool-call allowance is checked before execution rather than partially executing an over-budget batch.

**What this buys ACL:**

- malformed calls can be rejected before side effects;
- tool and result contracts can be deterministic/testable;
- the model can receive precise corrective feedback;
- output type checking can remain outside the model's prose.

**What it does not buy ACL:**

Core function tools are still ordinary Python functions. If a tool can access the host filesystem, network, process environment or privileged API credentials, schema validation does not reduce that authority. Approval/defer flow decides whether to execute a call; it does not isolate the execution.

**ACL invariant candidate:** treat `valid call`, `approved call` and `authorized/sandboxed effect` as three separate facts.

Primary sources:
- https://github.com/pydantic/pydantic-ai/tree/main/pydantic_ai_slim/pydantic_ai/toolsets
- https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/toolsets/function.py
- https://github.com/pydantic/pydantic-ai/tree/main/pydantic_ai_slim/pydantic_ai/output.py

## 4. Retry architecture: bounded correction, not "retry more"

Pydantic AI's current retry documentation distinguishes multiple retry layers that can otherwise be confused:

1. transport retry;
2. provider SDK retry;
3. durable-execution retry of a model-request step;
4. model fallback;
5. tool retry, where the model is asked to correct a bad call;
6. output retry, where the model corrects invalid final output;
7. model-request hook retry.

The key operational detail is that these layers can multiply. A logical `request_limit` does not necessarily count every underlying HTTP attempt, and per-attempt timeouts may re-arm under lower-level retries. Durable systems can also add their own retry policy.

Historical issues demonstrate the local-model failure mode directly. Earlier Ollama integrations could repeatedly return the same invalid output; raising `retries` simply consumed more turns until `UnexpectedModelBehavior` because the underlying behavior was deterministic rather than transient.

Examples:
- https://github.com/pydantic/pydantic-ai/issues/739
- https://github.com/pydantic/pydantic-ai/issues/200
- https://github.com/pydantic/pydantic-ai/issues/667
- https://github.com/pydantic/pydantic-ai/issues/877

These are historical evidence, not a claim that the current implementation still has the same bugs.

**ACL lesson:** every retry layer needs an owner, a reason category, a hard budget and telemetry. Validation feedback should retry only when the model can plausibly change the call. Transport/provider failures and deterministic capability mismatches belong to different recovery paths.

Primary source:
- https://github.com/pydantic/pydantic-ai/blob/main/docs/retries.md

## 5. Local/Ollama support: compatibility must be capability-based

Current Pydantic AI explicitly supports self-hosted Ollama through its OpenAI-compatible chat endpoint and exposes direct Ollama model configuration.

The more important finding is how current docs treat structured output:

- local Ollama versions that can enforce JSON schema through the llama.cpp grammar-constrained decoder can support provider-native structured output;
- Ollama Cloud can accept a JSON-schema-shaped request without enforcing the same grammar constraint;
- Pydantic AI detects this difference and disables the unsupported native-output capability rather than assuming all nominally compatible endpoints behave identically.

This is exactly the failure class that earlier local-model issues exposed.

**ACL invariant candidate:** keep an explicit, versioned `Model/RuntimeCapabilityProfile` for each worker/runtime combination. "OpenAI-compatible" must never be treated as proof of tool calling, JSON-schema enforcement, streaming behavior or cancellation semantics.

Primary sources:
- https://github.com/pydantic/pydantic-ai/blob/main/docs/models/ollama.md
- https://github.com/pydantic/pydantic-ai/tree/main/pydantic_ai_slim/pydantic_ai/profiles

## 6. Concurrency, cancellation and teardown ownership

Current Pydantic guidance reflects a large amount of paid-for-by-bugs lifecycle work. The recurring rules are directly relevant to long-running ACL workers:

- every task, cancel scope, lock, stream, span and connection needs a teardown owner;
- prefer structured task groups over loose background tasks;
- cancelling is not cleanup: cancel, then await/drain;
- do not assume asyncio edge-triggered cancellation and AnyIO level-triggered cancellation behave identically;
- give tool timeouts one owner rather than stacking hidden timeouts;
- blocking sync work moved to a thread cannot be forcibly stopped merely because the async caller was cancelled;
- shared async objects still need concurrency discipline;
- tests should assert cleanup/pending-task state, not merely final output.

The core now exposes first-party run cancellation concepts such as cancellation tokens/run cancellation, but durable workflow boundaries still require separate semantics.

Historical/current lifecycle issue families include cancellation cleanup races, broken/closed stream resource races, Temporal cancellation livelocks, abandoned event-stream ownership and nested/sub-agent cancellation attribution. The value to ACL is the pattern, not any single resolved issue.

**ACL invariant candidate:** a worker is not `stopped` until owned child tasks/processes/streams are accounted for and drained or explicitly classified unresolved.

Primary sources:
- https://github.com/pydantic/pydantic-ai/blob/main/docs/timeouts.md
- https://github.com/pydantic/pydantic-ai/blob/main/docs/concurrency.md
- https://github.com/pydantic/pydantic-ai/issues?q=cancellation

## 7. Evaluation and observability: evaluate trajectories, not just answers

`pydantic-evals` is code-first and supports deterministic evaluators, custom evaluators and LLM judges. The feature most relevant to ACL is span-based evaluation: OpenTelemetry traces can be evaluated for internal behavior such as tool calls and execution flow instead of judging only the final answer.

Pydantic AI instrumentation can emit a trace per agent run with spans around model calls and tool execution, and Logfire is an optional visualization/analysis destination rather than the only trace concept.

**ACL lesson:** test both result and trajectory. Examples of deterministic trajectory assertions ACL will likely need later:

- forbidden tool never called;
- expected validation/check tool called before completion;
- retries stayed within budget;
- blocked upstream task did not execute downstream work;
- no unapproved destructive action occurred;
- expected handoff/evidence record exists.

For high-trust validation, this does not eliminate the need for logically independent checks; worker-generated telemetry can be evidence without becoming the sole authority over its own correctness.

Primary sources:
- https://github.com/pydantic/pydantic-ai/blob/main/docs/evals.md
- https://github.com/pydantic/pydantic-ai/blob/main/docs/logfire.md

# Beneficial scope expansion: official Pydantic AI Harness

The core project's own ecosystem now includes a separate official harness directly aimed at the class of long-running/coding-agent problems ACL is studying. Ignoring it would have made the Pydantic AI assessment materially incomplete. The sections below are limited to mechanisms that overlap ACL/Vera.

## 8. FileSystem: strong application-level workspace guard, not hostile-code isolation

The official `FileSystem` capability scopes file operations to one `root_dir` and provides:

- path normalization/realpath containment;
- symlink escape checks;
- allowed/denied/protected patterns;
- bounded reads/search/listing;
- hashes on reads and optional `expected_hash` stale-write rejection;
- protected defaults for `.git`, `.env`, key/certificate and secret-like paths;
- model-correctable filesystem errors surfaced as retries.

The docs also state its limits:

- containment is pathname-based and has a check/use race if another process mutates the tree between resolution and I/O;
- the sandbox is only as tight as the configured root;
- protected paths are read-only, not necessarily invisible;
- application-level pathname checks do not become an OS sandbox.

A reported absolute-host-path leak in filesystem retry messages (#616) was closed on 2026-08-19. That history is useful because it shows that even a correct access boundary can still leak information through its error channel.

**Possible ACL reuse:** rooted file API, realpath/symlink containment, protected patterns, bounded enumeration and optimistic-write hashes.

**Do not infer:** that these checks safely contain arbitrary model-generated executables. Privileged workers still need OS/container/process isolation appropriate to their threat model.

Primary sources:
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/filesystem.md
- https://github.com/pydantic/pydantic-ai-harness/issues/616

## 9. Shell: accident guard plus explicit environment hygiene; not a sandbox

The Harness `Shell` capability provides command controls, timeouts, output limits, process cleanup and environment filtering. Current docs explicitly call the command allow/deny policy **best-effort rather than a security boundary**: tools such as `python`, `git`, `uv` and `make` can indirectly execute far more than their first executable name implies.

A strong historical dogfooding lesson is issue #281. A team agent could not safely migrate to the generic shell because child processes inherited the parent environment containing model-provider and GitHub credentials. The issue was closed after environment controls were added. Current controls include explicit environment replacement/filtering and API-key-pattern stripping options.

A second adversarial issue (#622) found model-correctable spawn failures that escaped as run-aborting exceptions; it was closed on 2026-08-26.

**ACL invariant candidates:**

- child process environment should be explicit/minimal by default for privileged agents;
- model-visible process errors should be sanitized;
- shell allowlists are workflow guardrails, not hostile-code isolation;
- process-group ownership and teardown should be explicit;
- untrusted code should execute behind a stronger sandbox/container boundary.

Primary sources:
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/shell.md
- https://github.com/pydantic/pydantic-ai-harness/issues/281
- https://github.com/pydantic/pydantic-ai-harness/issues/622

## 10. Planning: useful model-owned working state, not ACL's authoritative scheduler

Harness `Planning` gives the model a structured task list with stable IDs, statuses, optional subtasks/dependencies, persistence and events. A valuable context/cost design is that the mutable plan is surfaced as an ephemeral tail reminder rather than rewritten into durable system-prompt history every turn.

It supports separate planner/executor runs sharing a plan store. This makes model specialization possible without carrying the planner's complete conversation into the executor.

The critical boundary is explicitly documented: planner read-only discipline is a property of the tools/instructions assigned to the planner. The Planning capability itself does **not** enforce that discipline. Likewise, the convention that one task is `in_progress` is guidance, not the same thing as ACL's authoritative dependency gate.

**Possible ACL reuse:** stable task IDs, dependency model, persistent plan store, event stream and ephemeral plan reminder.

**Do not copy as authority:** a model-owned plan should not decide whether blocked downstream repo work is allowed to proceed. ACL's project/task state and dependency gate should remain outside the model's editable working plan.

Primary source:
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/planning.md

## 11. SubAgents: isolated context and budgets, with explicit inheritance decisions

`SubAgents` exposes one delegation tool and gives each child its own run/history. Important defaults and controls include:

- child context does not automatically include parent conversation history;
- tools are not inherited by default;
- capability sharing is explicit;
- the delegation tool is not inherited, preventing recursion by default;
- usage, wall-clock timeout and max-call budgets can be set per delegate;
- failures can be hard or explicitly contained;
- model selection can come from a bounded menu rather than arbitrary model names.

The parent dependency object is forwarded to children, which is convenient but should not be confused with least privilege.

**ACL invariant candidate:** child agents should receive an explicit capability grant, not ambient parent authority. Context isolation, tool isolation, model menu and per-child budgets are useful patterns; forwarded dependencies/credentials must be separately scoped.

Primary source:
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/subagents.md

## 12. Capability composition: generic config merge can become privilege escalation

One of the most directly reusable lessons came from a recent Harness hardening change. Generic composition/merge of repeated capability configuration could accidentally widen authority: unioning `FileSystem` or `Shell` allowlists, inherited tools or shared sub-agent capabilities could give one composed harness reach intended only for another.

Maintainers changed composition behavior so ambiguous authority-bearing merges are refused or require explicit semantics rather than being generically unioned.

**ACL invariant candidate:** authority-bearing configuration must never use a generic "merge dictionaries/lists" rule. Permission composition needs explicit field-by-field semantics and should fail closed when the result is ambiguous.

This applies directly to:

- parent → child worker capabilities;
- project → global tool policy;
- local worker → cloud reviewer capability handoff;
- filesystem roots;
- command allowlists;
- credential scopes;
- network destinations.

Primary evidence:
- Pydantic AI Harness commit `ec4b8615ac820bd5b93f19c00c52db29682a6e96`
- https://github.com/pydantic/pydantic-ai-harness/commit/ec4b8615ac820bd5b93f19c00c52db29682a6e96

## 13. StepPersistence: the strongest direct ACL checkpoint/evidence reference

`StepPersistence` is the most directly relevant mechanism found in this task because it **separates evidence persistence from safe resume**.

It records:

1. append-only step events at run/model/tool/failure boundaries;
2. continuable snapshots at settled boundaries;
3. snapshot state as `complete` or `interrupted`;
4. a tool-effect lifecycle ledger (`started`, `completed`, `failed`);
5. `conversation_id`, `run_id`, `step_index` and `parent_run_id` lineage.

The critical recovery rule is explicit: if a crash occurs after a tool effect is recorded `started` but before a terminal record, that effect is **unknown after crash**. It may or may not have happened. The default continuation path therefore prefers complete settled snapshots; interrupted frontiers require deliberate handling.

The docs also refuse to overclaim: StepPersistence is **not a full graph-state checkpoint**. Capability-state restore, workspace snapshots and graph-node resume are separate concerns. Side-effect deduplication remains the orchestrator's responsibility, though tools can annotate idempotency keys/effect summaries.

This maps almost exactly onto ACL's documentation/recovery concern.

**ACL invariant candidates:**

- append evidence before/around side effects rather than only at task end;
- record `started` separately from `completed`;
- after crash, represent uncertain effects explicitly rather than guessing success/failure;
- distinguish transcript/history continuation from full checkpoint recovery;
- use stable run/conversation/parent IDs;
- make idempotency/effect identity first-class for destructive external tools;
- never automatically continue downstream work from an uncertain upstream effect.

Primary source:
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/step-persistence.md

## 14. Persistent Memory: bounded and concurrency-safe, but still untrusted

Harness `Memory` provides a persistent notebook model with bounded injection/search and several useful storage invariants:

- `MEMORY.md` plus auxiliary Markdown files;
- finite injected token/line/file/search budgets;
- current memory injected as delimited **user-role** content rather than system instructions;
- namespaces resolved by application code and hidden from model-facing tool args;
- optimistic compare-and-swap updates;
- idempotency keys derived from run/tool operation;
- local FileStore journal for crash recovery/cross-process conflict detection;
- SQLite/Postgres backends with transactional mutation semantics.

The docs explicitly identify the trust boundary:

- model-written memory is untrusted content that can re-enter later prompts;
- user-role delimiters reduce authority but are **not** a hard prompt-injection boundary;
- namespace selection is not a complete authorization system;
- memory entries do not automatically carry source citations or verified provenance.

Issue #103 remains open as of this task and proposes scanning persistent agent-written artifacts for delayed prompt injection, exfiltration patterns and similar threats before persistence/reload.

An optional `PromptInjectionDefender` exists for normal local tool results, but its own docs list gaps: provider-native tools, deferred external results, some failure messages, unrecognized fields and referenced media are outside its coverage.

**Vera/ACL invariant candidates:**

- persistent memory must remain a lower-trust data plane, not silently become system authority;
- every memory write should have origin/provenance where factual audit matters;
- namespace/tenant resolution should be application-owned and hidden from model args;
- memory mutations need concurrency/idempotency semantics;
- delayed prompt injection requires write-time and/or read-time policy beyond delimiters;
- memory used for decisions should be distinguishable from durable project facts/evidence.

Primary sources:
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/memory.md
- https://github.com/pydantic/pydantic-ai-harness/issues/103
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/prompt-injection-defender.md

## 15. Compaction: deterministic reclamation before lossy summarization

The Harness compaction system is useful because it does not treat "summarize old context" as the only answer.

Strategies include:

- clamp a single oversized part;
- sliding window;
- clear old tool results;
- deduplicate superseded file reads;
- model-generated summarization;
- tiered escalation;
- near-limit warnings and usage reporting.

The recommended pattern is cheap/deterministic first, expensive/lossy summarization last. Strategies preserve tool-call/tool-return pairing, which avoids producing invalid provider histories.

The docs also expose a subtle local-model/runtime problem: context-window metadata can be missing or wrong. A generic registry value, cloud model maximum or self-hosted deployment may not match the endpoint actually in use; a fraction-based compaction threshold can therefore trigger too early or too late.

**ACL lesson:** context management needs the same capability-profile discipline as tool calling. Clear redundant/re-fetchable evidence before summarizing durable facts, preserve causal tool pairs, and label summary-derived state as lossy.

Primary source:
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/compaction.md

## 16. Guardrails/approval composition: human approval is not automatically monotonic safety

An open Harness design issue (#519) is unusually instructive. Chaining tool guardrails is not a mechanical list operation because an `approve` decision can terminate a chain. If later guards are skipped before approval and still skipped after resume, a human-approved call could execute without having passed every intended guard.

The issue remains open because maintainers explicitly treat the semantics as a security-policy decision rather than guessing.

**ACL invariant candidate:** approval should never silently bypass another independent policy gate. ACL should define whether approval is additive (`all required policies still pass`) or substitutive (`human approval overrides named policies`) per policy, rather than allow control-flow order to decide.

Primary source:
- https://github.com/pydantic/pydantic-ai-harness/issues/519

## 17. Repo context: useful compatibility feature, also a trust input

`RepoContext` can automatically load `CLAUDE.md`/`AGENTS.md` files and inventory `.agents`, `.claude`, `.codex` and `.grok` assets. This is useful for ACL because existing repositories increasingly carry assistant-specific instructions and skills.

But automatic instruction loading creates a trust question: repository content can influence agent behavior. `RepoContext` discovers/loads context; it does not itself prove that those instructions are authorized governance rather than untrusted content.

**ACL lesson:** repo instructions need provenance/trust classification. A checked-in project policy approved by ACL governance is not the same trust class as arbitrary text found in a cloned third-party repository.

Primary source:
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/repo-context.md

# Reusable mechanisms to carry forward

These are **research candidates**, not adopted architecture decisions.

## Highest-value candidates

1. **Model/runtime capability profiles** rather than provider-name conditionals.
2. **Typed tool arguments and result contracts** with validation before side effects.
3. **Separate retry categories and budgets** with telemetry for logical vs wire attempts.
4. **Fail-closed authority composition** instead of generic config merging.
5. **Explicit child-agent capability grants** plus per-child time/token/call budgets.
6. **Rooted/symlink-safe filesystem API** plus optimistic stale-write hashes.
7. **Minimal child-process environment** and sanitized errors.
8. **StepPersistence-style event/effect ledger** with `complete` vs `interrupted` recovery points.
9. **Explicit `unknown_after_crash` side-effect state**.
10. **Conversation/run/step/parent lineage IDs**.
11. **Bounded memory with CAS/idempotency and app-owned namespace**.
12. **Memory treated as untrusted data with explicit provenance gap**.
13. **Deterministic compaction tiers before lossy summarization**.
14. **OpenTelemetry/span-based trajectory evaluation**.
15. **Mutation/adversarial testing of authority boundaries**, not branch coverage alone.

## Mechanisms that need ACL-specific strengthening

- Planning is model-owned working state; ACL needs a separate authoritative project/task gate.
- Shell allowlists are not isolation; ACL needs process/OS/container policy where code is untrusted.
- FileSystem is a strong pathname guard but not a hostile same-user-process sandbox.
- Approval is a decision workflow, not permission isolation.
- Memory delimiters are not a prompt-injection boundary.
- Step history is not full checkpoint state.
- Provider compatibility is not model/runtime capability proof.

# Failure surfaces that should become ACL test fixtures later

The Pydantic evidence suggests several concrete deterministic fixtures for ACL's future benchmark/harness tests:

1. local model repeatedly emits the same invalid tool args; retry budget must stop without runaway looping;
2. parallel tool batch would exceed remaining tool-call budget; no partial side effects occur;
3. child worker is cancelled while a tool/process is active; cleanup and unresolved effects are visible;
4. process crashes after side-effect start but before acknowledgement; state becomes `unknown_after_crash` rather than guessed;
5. child agent receives two capability configurations whose union would widen file/shell reach; composition fails closed;
6. stale file hash prevents overwriting a newer edit;
7. symlink/path traversal attempts cannot escape workspace;
8. model-generated script cannot inherit supervisor/API credentials by default;
9. persistent memory contains adversarial instructions; it cannot become higher-authority governance merely by being remembered;
10. repo-provided `AGENTS.md` conflicts with trusted project governance; trusted authority wins and conflict is visible;
11. approval from a human does not skip remaining mandatory policy checks;
12. context-window metadata is wrong for a local endpoint; context management uses an explicit deployment profile rather than silently trusting registry metadata.

# Assessment for the research queue

**Pydantic AI remains a justified high-priority reference after deep research.** The official Harness materially increases its relevance to ACL because it already implements several features ACL expected to design itself.

At the same time, the research argues against a simplistic "adopt Pydantic AI and we're done" conclusion:

- Harness is Alpha/0.x and changing rapidly.
- Recent hardening work still touches replay safety, cancellation, authority composition and security-sensitive tools.
- Core execution contracts and Harness capabilities are useful layers, but ACL still needs a project-level authority/recovery model and possibly stronger OS isolation.
- The most valuable concepts can be compared/reused independently of whether ACL eventually depends on the whole stack.

The later **reusable components versus custom-build** task should therefore compare at least three options for each high-value mechanism: direct dependency, thin adapter/pinned subset, or independent implementation informed by the same invariant. This task does not choose among them.

# Questions left deliberately open

These should not be answered by drifting into later tasks:

- Would ACL be better served by adopting Pydantic AI core, the Harness, both, or selected ideas only?
- Which Harness APIs are stable enough to pin for a long-running worker lab?
- How does Pydantic AI compare directly with Cline/LangGraph/Strands on the same ACL fixtures?
- What exact OS/container sandbox should ACL use?
- What is the final ACL memory trust/provenance model?
- Which component should own the authoritative project backlog and dependency gate?
- What licensing/dependency/maintenance policy should control third-party harness adoption?

Those belong to later comparative/security/component-selection work.

# Source index

Core:
- https://github.com/pydantic/pydantic-ai
- https://github.com/pydantic/pydantic-ai/releases
- https://github.com/pydantic/pydantic-ai/blob/main/LICENSE
- https://github.com/pydantic/pydantic-ai/blob/main/agent_docs/pydantic-ai-slim.md
- https://github.com/pydantic/pydantic-ai/blob/main/docs/retries.md
- https://github.com/pydantic/pydantic-ai/blob/main/docs/timeouts.md
- https://github.com/pydantic/pydantic-ai/blob/main/docs/models/ollama.md
- https://github.com/pydantic/pydantic-ai/blob/main/docs/evals.md
- https://github.com/pydantic/pydantic-ai/blob/main/docs/logfire.md
- https://github.com/pydantic/pydantic-ai/tree/main/pydantic_ai_slim/pydantic_ai/profiles
- https://github.com/pydantic/pydantic-ai/tree/main/pydantic_ai_slim/pydantic_ai/toolsets

Historical/provider failure evidence:
- https://github.com/pydantic/pydantic-ai/issues/739
- https://github.com/pydantic/pydantic-ai/issues/200
- https://github.com/pydantic/pydantic-ai/issues/667
- https://github.com/pydantic/pydantic-ai/issues/877

Official Harness:
- https://github.com/pydantic/pydantic-ai-harness
- https://github.com/pydantic/pydantic-ai-harness/releases
- https://github.com/pydantic/pydantic-ai-harness/blob/main/pyproject.toml
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/filesystem.md
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/shell.md
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/planning.md
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/subagents.md
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/step-persistence.md
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/memory.md
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/compaction.md
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/repo-context.md
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/prompt-injection-defender.md
- https://github.com/pydantic/pydantic-ai-harness/blob/main/docs/mutation-testing.md
- https://github.com/pydantic/pydantic-ai-harness/issues/281
- https://github.com/pydantic/pydantic-ai-harness/issues/616
- https://github.com/pydantic/pydantic-ai-harness/issues/622
- https://github.com/pydantic/pydantic-ai-harness/issues/519
- https://github.com/pydantic/pydantic-ai-harness/issues/103
- https://github.com/pydantic/pydantic-ai-harness/commit/ec4b8615ac820bd5b93f19c00c52db29682a6e96

## Stop boundary

This file completes the Pydantic AI project-level research task. It does not deep-research Cline, select a dependency, change ACL/Vera architecture/governance, or authorize worker/model execution.
