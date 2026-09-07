# Research Watchlist

Task 3 established the research-priority queues. Task 4 added transition/status evidence. Tasks 5–19 completed one-project-at-a-time deep research through **Gemini CLI**. Rank continues to mean **study/watch sooner because the candidate is expected to reduce ACL/Vera uncertainty**; completed research is not an adoption list.

Detailed evidence remains authoritative in the dedicated reports. This watchlist is the compact queue and cross-project invariant index.

## Completed project deep research
- `projects/pydantic-ai.md`
- `projects/cline.md`
- `projects/langgraph.md`
- `projects/promptfoo.md`
- `projects/strands-harness-sdk.md`
- `projects/codex.md`
- `projects/openhands.md`
- `projects/swe-agent-mini-swe-agent.md`
- `projects/llama-cpp.md`
- `projects/openai-agents-sdk.md`
- `projects/model-context-protocol.md`
- `projects/goose.md`
- `projects/ollama.md`
- `projects/letta-code.md`
- `projects/gemini-cli.md`

## Task 15 — Model Context Protocol research result

**Status:** current MCP deep research complete; no dependency/adoption/fork decision made.

High-value findings retained for later comparison:
- MCP `2026-07-28` moved the modern core toward stateless request/response semantics; explicit handles/IDs carry application state across requests.
- Transport connection, JSON-RPC request, MCP Task, ACL task/run/effect and Vera conversation/memory remain distinct identities.
- The host should retain trust, consent, cross-server context and authorization ownership; protocol-valid tools/prompts/resources do not gain governance authority automatically.
- Canonical remote-tool identity needs trusted server origin plus protocol/profile and tool-definition/schema identity; names and annotations alone are insufficient.
- MRTR continuation state can become authority-bearing attacker-controlled input; integrity, replay protection and idempotency remain separate.
- Cancellation/progress/subscription semantics remain cooperative/transport-level and do not prove backing computation/effects settled.
- The Tasks extension is useful durable remote-job interoperability, but remote task handles are not ACL continuation checkpoints and task TTL/cancel does not prove computation ended.
- HTTP authorization is service/audience scoped; token passthrough is forbidden, strongly supporting Vera's future credential-broker/service-grant boundary.
- Authorization/discovery/resource/schema fetches are SSRF/network-policy surfaces.
- Optional extensions are independently versioned/negotiated capability; core conformance does not imply Tasks/UI/auth-extension parity.
- Current issue fixtures #2920, #3348, #3207/#3213 and ext-tasks #11/#20 remain version-scoped interoperability/security test inputs.
- MCP is strongest as interoperability beneath ACL/Vera-owned scheduling, sandbox/process custody, credential governance, memory, effect ledger, checkpoints and independent verification.

See `projects/model-context-protocol.md` for primary sources and explicit non-conclusions.

## Task 16 — Goose research result

**Status:** current Goose deep research complete; no dependency/adoption/fork decision made.

High-value findings retained for later comparison:
- `goose-agent` re-derives loop transitions from persisted conversation state rather than hidden loop progress, a useful restart-safe runtime pattern.
- ACP separates replaceable clients from the full runtime, but ACP/session identity is still not ACL project/run/effect identity.
- Goose has a small provider boundary, direct Ollama support and built-in llama.cpp-based/MLX local inference; exact harness/provider/backend/model/template/parser/tool-mode identity matters.
- MCP extension lifecycle/namespacing and secret-triggered restart behavior are useful, while inherited stdio subprocess environment remains broader than ACL should allow.
- Smart Approval/tool permissions/security inspectors are layered policy, not an OS sandbox; Goose currently does not provide a general OS sandbox.
- Versioned SQLite sessions and an in-process active-run registry are useful reconstruction/race-control patterns but not durable distributed writer fencing.
- Recipes are executable configuration; content hashing is useful approval identity, while conversation reset on retry does not roll back workspace/API effects.
- Internal subagent restrictions and Code Mode provide useful delegation/context-pressure patterns without constituting process isolation.
- Harbor evidence demonstrates the harness/tool mode itself is a benchmark variable.
- Current issue fixtures #10325, #11500 and #11399 remain valuable for executable-manifest trust ordering, authenticated redirects and argument-level shell authorization.
- Goose is strongest as a source of state/provider/MCP/context/eval mechanisms beneath ACL-owned authority, credential, effect and verifier layers.

See `projects/goose.md` for primary sources and explicit non-conclusions.

## Task 17 — Ollama research result

**Status:** current Ollama deep research complete; no dependency/adoption/runtime-winner decision made.

High-value findings retained for later comparison:
- Ollama deployment identity includes exact release/build, embedded engine/patch profile, immutable model artifact, template/parser, API route, context/KV settings, backend/device and realized offload.
- Current Ollama pins and patches llama.cpp, while MLX is a materially different runner profile; direct llama.cpp and Ollama are separately qualified runtimes.
- SHA-256 artifact identity is stronger benchmark identity than mutable tags.
- Context defaults are hardware-derived and can diverge from ACL's intended 32K baseline; requested and realized context must be recorded.
- KV/cache/parallelism/flash-attention/GPU-fit decisions are behavior/performance-bearing state.
- Scheduler reachability is not scheduler forward progress; cold-load health requires explicit probes.
- Capability discovery nominates tests but is not verified end-to-end capability.
- Native tool schema transport loses some general JSON-Schema constraints; ACL must retain and validate against its original authoritative schema.
- Tools and structured output are separate feature paths; capability composition requires its own fixtures.
- Native and OpenAI-compatible API routes need separate qualification; `runtime=ollama` also does not prove offline/local execution.
- Debug request replay is useful but sensitive operational evidence.
- Current issue fixtures #17099, #17142, #17408, #17444, #17597 and #17957 remain runtime/schema/scheduler/integration tests.
- Ollama is strongest as inference/runtime beneath ACL-owned scheduling, sandbox/process authority, credentials, state/effects, checkpoints and verification.

See `projects/ollama.md` for primary sources and explicit non-conclusions.

## Task 18 — Letta Code research result

**Status:** current Letta Code deep research complete; no dependency/adoption/memory-architecture winner decision made.

High-value findings retained for later comparison:
- Persistent agent identity, conversation thread and live runtime connection are distinct; multiple conversations may share one agent-owned long-term memory.
- Git-backed MemFS is a distinct curated memory plane from full recall/history.
- Git gives strong mutation provenance but not truth, source authority, confidence or verification.
- Persistent memory needs provenance/evidence/trust/conflict/supersession semantics; chronological recency is not an authority hierarchy.
- Background reflection worktrees expose explicit integration settlement states; generated/committed reflection is not automatically authoritative parent memory.
- Learned memory, skills and executable mods/security policy are distinct trust classes; learning must not silently deploy code or expand authority.
- Configured memory sandbox and realized sandbox differ; ordinary internal memory-subagent launch can degrade to unsandboxed operation.
- Raw provider evidence, canonical semantic messages, stored projections, UI and reflection inputs are separate representations requiring tests.
- Secret references/substitution are preferable to prompt plaintext, but runtime plaintext still constitutes authority exposure.
- Side-effect-aware subagent retry is useful: ambiguous failure after possible effects is not automatically replayed.
- App Server correlation/trajectory ingestion are useful, but runtime idempotency and imported trajectories are not exactly-once effects or trusted truth.
- Current issue fixtures #4029, #4195, #4249, #4247, #3132 and #3523 preserve separate epistemic/projection/integration/restore/context/retention failure classes.
- Letta is strongest as persistent identity/memory/runtime reference beneath Vera/ACL-owned provenance policy, authority, effects and verification.

See `projects/letta-code.md` for primary sources and explicit non-conclusions.

## Task 19 — Gemini CLI research result

**Status:** current Gemini CLI deep research complete; no dependency/adoption/model/runtime/sandbox decision made.

High-value findings to carry into later comparison:
- **Deterministic tiered policy:** current PolicyEngine resolves `ALLOW`, `DENY` and `ASK_USER` from protected rule layers using tool, MCP server, normalized arguments, annotations, subagent identity, approval mode and interactive/headless state. Unresolved headless calls deny and checker failures fail closed.
- **Policy != sandbox:** approval/policy outcome, capability grant, realized sandbox and external-effect settlement are separate authority/evidence domains.
- **Argument semantics matter:** open #29189 reproduces on stable `v0.58.0` that Windows can treat `git diff` as read-only while `--output` writes a file. Current main still classifies a safe-git subcommand set without full argument validation; proposed PR #29184 remained open during Task 19.
- **Shell authorization cannot be name-only:** normalize flags, redirects, aliases/hooks/config and nested interpreters where they can alter effects.
- **Incremental capability expansion is strong reference material:** sandbox tooling can request explicit filesystem/network permission expansion rather than globally disabling isolation.
- **Realized sandbox evidence matters:** Linux Bubblewrap implementation includes protected governance paths, environment sanitization and ptrace restriction; configured mode alone is not proof those controls were realized on another platform/backend.
- **Credential/control-plane separation remains necessary:** Gemini CLI sanitizes sensitive/runtime-altering environment values and MCP subprocess environments, but ACL workers should receive minimal explicit environments with provider/supervisor credentials kept outside worker authority.
- **Provider boundary is cloud/Gemini oriented:** current first-class ContentGenerator routes are Gemini / Code Assist / Vertex / Gateway. Task 19 found no first-class Ollama, direct llama.cpp, vLLM or generic OpenAI-compatible local provider in that surface.
- **Custom Gemini base URL is not generic local-provider parity:** a translation gateway would need its own exact capability qualification.
- **MCP and extensions are executable trust surfaces:** extensions can add MCP servers, policy/checkers, context, commands, hooks, agents and skills.
- **Configuration hash helps approval identity but not provenance:** extension consent exposes behavior-bearing config and SHA-256 identity, but that is not a publisher signature or proof executed artifacts match reviewed configuration.
- **Subagent shaping is useful but default inheritance is too broad for ACL:** local subagents isolate registries/context/policy and prevent recursion, yet omission of tools inherits parent tools. ACL should default child effect tools to none and grant explicit subsets.
- **A2A identity/auth is useful interoperability, not global task authority:** remote-agent auth does not establish ACL project/effect ownership or OS/credential isolation.
- **Read-before-create resume is critical:** current ACP authenticates early, but `loadSession()` initializes requested-session config before resolving stored state and launches history replay without awaiting it.
- **Open #28693/#28775 are current recovery fixtures:** their load-corruption reports align with the current ordering seam and should become ACL/Vera resume regression tests.
- **Append-oriented session state is strong reference material:** `ChatRecordingService` uses semantic JSONL records and transactional repair, separating active context from recoverable durable history.
- **Live progress can diverge from durable evidence:** ENOSPC can disable future recording while a session continues. ACL should make required-durability loss an explicit pause/degraded lifecycle state.
- **Open #29198 is a current stable-release retention fixture:** resume then immediate exit can remove later resumability; Task 19 preserved symptom evidence without claiming an unverified complete root cause.
- **Shadow-Git checkpointing is pre-effect workspace evidence, not full continuation:** it snapshots Git-visible project state plus conversation/tool metadata before modifying file tools but excludes ignored/process/database/network/API/credential state.
- **Auto-memory extraction is coordination, not truth:** per-workspace atomic locks, PID/age stale detection and bounded batches are useful local coordination, but memory still needs provenance and multi-host writer fencing where applicable.
- **Deterministic versus stochastic evaluation should remain separate:** Gemini CLI distinguishes integration correctness from model behavioral evals and uses repeated `USUALLY_PASSES` versus `ALWAYS_PASSES` reliability classes.
- **Harness/model role promotion should use distributions, not one pass:** exact model/runtime/harness/fixture identity and repeated trials belong in ACL's eventual benchmark evidence.
- **Telemetry is operator evidence:** OpenTelemetry logs/metrics/traces can contain sensitive model/tool context and do not define verifier-owned acceptance.
- **Protected policy/config is a structural requirement:** recent system-config and extension hardening reinforces that worker-constraining policy/checker/hook/verifier artifacts must be outside worker mutation authority and provenance/version checked.
- **Boundary:** Gemini CLI is strongest as a mature execution-policy, host-integration, checkpoint/session and eval reference. It does not replace ACL's outer scheduler, distributed writer fencing, external-effect ledger/reconciliation, credential broker, independent verifier, Vera epistemic-memory governance or exact local-runtime qualification.

See `projects/gemini-cli.md` for primary sources, current issue evidence, candidate ACL/Vera regression fixtures and explicit non-conclusions.

## Ranked active-project queue — live status

### Tier A — completed
1. **Pydantic AI** — `pydantic/pydantic-ai` — **Task 5 complete**.
2. **Cline** — `cline/cline` — **Task 6 complete**.
3. **LangGraph** — `langchain-ai/langgraph` — **Task 7 complete**.
4. **promptfoo** — `promptfoo/promptfoo` — **Task 8 complete**.
5. **Strands Harness SDK** — `strands-agents/harness-sdk` — **Task 9 complete**.
6. **Codex** — `openai/codex` — **Task 10 complete**.
7. **OpenHands** — `OpenHands/OpenHands` / `OpenHands/software-agent-sdk` — **Task 11 complete**.
8. **SWE-agent / mini-swe-agent** — `SWE-agent/SWE-agent`, `SWE-agent/SWE-ReX`, `SWE-agent/mini-swe-agent` — **Task 12 complete**.
9. **llama.cpp** — `ggml-org/llama.cpp` — **Task 13 complete**.
10. **OpenAI Agents SDK** — `openai/openai-agents-python` — **Task 14 complete**.

### Tier B — high-value follow-up
11. **Model Context Protocol** — `modelcontextprotocol/modelcontextprotocol` (+ directly relevant `modelcontextprotocol/ext-tasks`) — **Task 15 complete**.
12. **Goose** — `aaif-goose/goose` — **Task 16 complete**.
13. **Ollama** — `ollama/ollama` — **Task 17 complete**.
14. **Letta Code** — `letta-ai/letta-code` — **Task 18 complete**.
15. **Gemini CLI** — `google-gemini/gemini-cli` — **Task 19 complete**.
16. **Graphiti** — `getzep/graphiti` — **next task only**.
17. **Microsoft Agent Framework** — `microsoft/agent-framework`.
18. **Google ADK** — `google/adk-python`.
19. **LiteLLM** — `BerriAI/litellm`.
20. **vLLM** — `vllm-project/vllm`.

### Tier C — comparative / situational watch
21. **OpenCode** — `anomalyco/opencode`.
22. **Mem0** — `mem0ai/mem0`.
23. **smolagents** — `huggingface/smolagents`.
24. **Agno** — `agno-agi/agno`.
25. **LlamaIndex** — `run-llama/llama_index`.
26. **CrewAI** — `crewAIInc/crewAI`.
27. **Mastra** — `mastra-ai/mastra`.

## Ranked recurring-contributor queue — Task 3 snapshot

This ranks public technical signal, not formal authority, seniority, employment status or outreach priority.

1. **Saoud Rizwan** — Cline.
2. **Nick Hollon** — LangGraph.
3. **Jesús Samuel** — Gemini CLI.
4. **Graham Neubig** — OpenHands.
5. **Johannes Gäßler** — llama.cpp.
6. **Douwe Maan** — Pydantic AI.
7. **Anas Khan** — SWE-agent.
8. **Kazuhiro Sera** — OpenAI Agents SDK.
9. **Jack Amadeo** — Goose.
10. **Kartik Labhshetwar** — Mem0.

## Ranked recurring source queue — Task 3 snapshot

1. Upstream GitHub repositories
2. OWASP GenAI Security Project / Agentic Security Initiative
3. SWE-bench + Berkeley Function Calling Leaderboard (BFCL)
4. arXiv cs.SE / cs.MA / cs.CR recent feeds
5. Model Context Protocol specification + upstream repository
6. Hugging Face function-calling model filter + Daily Papers
7. GitHub Advisory Database + OSV
8. MITRE ATLAS
9. NIST AI / Agentic AI
10. OpenTelemetry GenAI semantic conventions
11. Agent2Agent (A2A) protocol
12. r/LocalLLaMA
13. Hugging Face Forums
14. Hacker News
15. Public project Discords / chat communities

`sources.md` remains the governing evidence ladder; review rank is not universal source authority.

## Cross-project rules to preserve

### Model-facing simplicity vs deterministic infrastructure
- Model proposals and role labels are not authority boundaries.
- Make model-facing scaffold complexity earn its place; lifecycle, policy, evidence and recovery belong in explicit runtime owners rather than prompt prose.
- A tiny/general tool interface can still carry broad authority; interface simplicity and least privilege are independent dimensions.
- On-demand meta-tool discovery can reduce context/schema pressure, but generated coordination code must cross the same deterministic effect-authorization boundary as direct tool calls.

### Identity, policy, memory and authority
- Persistent agent/persona identity, conversation/thread identity, project/task/run identity, runtime/transport identity, provider request identity and external-effect identity remain distinct.
- Personal/identity memory, shared/project memory, task memory, recall/history and trusted policy/configuration are separate state/authority domains.
- Persistent memory is not verified truth merely because it is durable or Git-tracked.
- Important memory needs provenance/evidence/trust/confidence/conflict/supersession semantics appropriate to domain risk.
- Chronological recency is not an authority hierarchy; newer lower-trust evidence cannot silently replace stronger verified memory.
- Compaction summaries and extracted memory are context/learning products, not canonical evidence.
- Learned memory, skills/procedures, trusted executable configuration and security policy are distinct trust classes.
- Learning/background reflection must not silently expand tools, credentials, network/filesystem authority or deploy trusted code.
- Imported transcripts/trajectories remain lower-trust data until provenance/trust is evaluated.
- Canonical effect capability identity includes authoritative origin plus definition/version/schema identity; name-only dispatch is unsafe across providers/servers.
- Approval/no-approval policy, argument validation, capability grant and realized sandbox authority are separate dimensions.
- Persisted approvals bind to exact call/origin/task/objective/tool/policy versions; incompatible semantic changes invalidate them.
- Malformed/uninspectable effect parameters fail closed.
- Revalidate mutable policy immediately before irreversible effects after waits/approval.
- Shell/command policy includes behavior-bearing arguments and redirection; apparently read-only executable/subcommand names are not enough.
- Child roles may reduce authority but must not widen the parent ceiling; default child effect authority should be explicit rather than inherited by omission.
- Reviewer/verifier capability should be minimized independently from worker capability.
- Self-reported server/model/provider names and read-only/tool annotations are metadata/advisory inputs, not security identity or authority.
- Shared recipes/extensions/configuration that can launch processes, add tools or run hooks/checkers are executable authority artifacts, not passive prompt templates.
- Configuration hashes are useful identity but do not replace artifact/publisher provenance, review and immutable versioning.
- High-trust policy/checker/verifier/hook roots must be structurally outside worker write authority.
- Mutable model tags are aliases, not immutable runtime/model authority or benchmark identity; retain content/manifests/digests where available.

### Workspace, sandbox and credentials
- Workspace isolation, Git/ref authority, secrets, verifier roots, memory roots and external effects are separate trust domains.
- Container/sandbox/runtime selection is not a complete permission profile; mounts/network/user/resources/credentials/capabilities are separate.
- Configured sandbox and realized sandbox are distinct evidence; required isolation should fail closed when not realized.
- Incremental capability expansion should request the smallest missing filesystem/network permission rather than disable the entire isolation boundary where practical.
- Cross-agent memory namespace guards and subagent registry isolation do not replace OS/process/filesystem/network/credential isolation.
- Local-host worker/tool execution should not inherit ambient supervisor environment/credentials.
- Model-provider/control-plane credentials should remain outside worker effect planes wherever architecture permits.
- Native inference services that spawn engine subprocesses should run under a deliberate service environment; this does not weaken the stronger minimal-environment rule for worker/tool processes.
- Durable state should reference credentials; live authority is rebound from current trusted policy after resume.
- Runtime-visible plaintext credentials cannot later be made secret from arbitrary worker code by revocation.
- Model-facing secret references/substitution are preferable to prompt-visible plaintext but do not eliminate runtime credential exposure.
- Persistent learned memory should not contain reusable secrets.
- MCP Roots/workspace hints are not access control.
- Approval modes, safety classifiers and command policies are not substitutes for OS/process/filesystem/network isolation.

### State, recovery, durability and effects
- Logical request/idempotency, run/attempt, process, protocol request, remote task handle and durable session identities remain separate.
- Transport/session/stream continuity is not authoritative project/task/effect state.
- Resume/load operations resolve and validate existing authoritative state before creating/mutating state in the same namespace.
- Each durable state domain needs one authoritative writer; multi-process/multi-host state requires leases/generation/CAS/fencing.
- Local PID/age locks and in-process session registries are coordination, not distributed writer fencing.
- A saved transcript/trajectory/inference cache/remote task handle is not automatically an ACL checkpoint.
- Re-deriving agent-loop transitions from persisted semantic state is preferable to hidden in-memory loop progress, but state still needs separate workspace/effect/authority evidence before safe continuation.
- A durable checkpoint still does not imply exactly-once external effects.
- Durable action/result relationships are atomic semantic state; orphan results/calls are corruption.
- Raw provider evidence, canonical semantic messages, persisted projections, UI representations and reflection inputs are separately testable representations.
- Background memory generation, Git commit and authoritative parent-memory integration are separate settlement states.
- Reflection conflicts/dirty parents/failed integration remain visible rather than silently counting as learned memory.
- A restore operation stages and verifies replacement before destroying/switching authoritative current state.
- Pre-effect shadow-Git/source checkpoints are useful workspace evidence but do not cover ignored files, processes, databases, APIs/network or credentials unless explicitly added.
- Partial/in-progress work stays visibly interrupted/uncertain after crash/recovery.
- Lost/expired remote handles do not prove backing computation stopped.
- Physical persistence retention is separate from model-context compaction and execution settlement.
- Live execution and required durable recording are separate lifecycle dimensions; loss of required durability must become explicit degraded/paused state rather than invisible logging failure.
- Runtime model residency/keep-alive and KV/prompt cache are performance state, not durable agent continuation authority.

### Cancellation, timeouts and retry
- Every blocking plane needs an explicit timeout/cancellation owner: provider request/stream, prompt/prefill/generation, tool process, remote runtime/task and whole run.
- Progress/heartbeats may control idle timeout but never remove hard maximum deadlines.
- Cancellation acknowledgment is not process termination or effect settlement.
- Immediate abort and stop-at-safe-boundary are distinct controls.
- Retry is not authority to replay a possibly already-executed effect/request.
- Ambiguous child/provider output after possible effects is not automatically retryable; reconcile before replay.
- Provider/request IDs are correlation identifiers, not automatically idempotency/effect IDs.
- Broken transport retry of an effect-bearing request needs durable reconciliation/idempotency policy.
- Resetting conversation/task messages for retry is not workspace rollback or external-effect rollback.
- Resource schedulers need explicit transition states plus bounded waits; an alive service/already-loaded model is not proof a cold-load path is healthy.

### Model/runtime capability and protocol compatibility
- Local-model capability is an exact model + runtime + adapter + protocol/tool schema/namespace + configuration property.
- For llama.cpp-class deployments, include build/backend/driver, GGUF/quantization, template/parser/constraint backend, context/KV/cache and optimization/sampling settings.
- For Goose-like deployments, also record exact Goose/GDK/provider revision, local backend path and extension/tool mode such as direct MCP versus Code Mode.
- For Ollama deployments, record exact Ollama release/commit/package digest, embedded engine kind/revision/patch profile, immutable model/manifest/template identity, API route, context/KV/parallel/fit settings and realized offload/context.
- For Letta-like stateful harnesses, record exact harness/backend/provider/model/runtime endpoint, dynamic toolset/model settings, requested/realized context and memory/runtime mode.
- Gemini CLI's provider support is Gemini-protocol/cloud-harness evidence and must not be generalized into local/OpenAI-compatible provider parity.
- Requested runtime settings and realized runtime state are separate evidence; context/offload/device placement must be observed rather than inferred from configuration.
- Template/schema/protocol capability discovery is not verified end-to-end behavior.
- MCP capability identity includes protocol era/version, transport, SDK/adapter revision, auth mode and negotiated extensions.
- Core protocol conformance does not imply optional extension parity.
- Native provider APIs and nominal OpenAI-compatible APIs are separately qualified capability surfaces.
- Silent modern/legacy/provider fallback must not preserve the same verified-capability label.
- Local versus remote/cloud inference is an explicit deployment profile and cannot be inferred from a generic runtime brand/name.

### Schema, network and content trust
- Tool schemas, validation, authorization, execution and evaluation are distinct contracts.
- Preserve the authoritative complete tool schema outside provider/runtime-specific down-conversions; generated arguments are validated against the authoritative schema before authorization/effects.
- A model-visible tool schema can be advisory even when structured-output decoding uses a grammar; do not infer one path's enforcement semantics from the other.
- Test required capability combinations, not only individual capability flags.
- Schema converters/parsers/constraint compilers are trusted code and require adversarial regression fixtures.
- Remote schema/resource/auth/discovery URL dereference is a network/SSRF authority surface with private/loopback/redirect/size/time policy.
- Redirect behavior for authenticated remote tool clients is itself a credential/network policy surface and should be explicitly configured/tested rather than inherited from HTTP-client defaults.
- Remote prompts, resources, memory and server instructions remain lower-trust model content regardless of valid protocol shape.
- Cache TTL is freshness guidance, not authorization, provenance or immutable state version.
- Server-declared public cacheability cannot override ACL/Vera trust isolation.
- Loopback binding/CORS/Host-header checks and service authentication are separate controls; exposing a local inference API beyond loopback requires an explicit outer network/auth policy.

### Verification, evaluation and evidence
- The system under test does not own the authoritative definition of pass/fail.
- Deterministic host/verifier evidence precedes semantic model grading when machine-observable.
- Deterministic harness/integration correctness and stochastic model behavioral reliability are separate scores.
- Model-role promotion uses repeated trials/pass distributions and exact model/runtime/harness/fixture identity rather than one successful run.
- Reliability classes such as `USUALLY_PASSES`/`ALWAYS_PASSES` are useful reference patterns, not preselected ACL thresholds.
- Missing required evidence yields explicit invalid/failure rather than implicit pass.
- Verifier tests/hashes/sidecars/control roots stay outside worker mutation authority.
- Trace/model/tool data may contain secrets; raw traces, operational telemetry and product analytics have separate audiences/retention.
- Provider/runtime request-replay logs are sensitive evidence when they contain full prompts/tool schemas/project data.
- Evidence export/delivery has its own settlement state.
- Protocol/SDK/harness/evaluator failures are classified separately from model failures.
- Memory failures are additionally classified as epistemic, transcript-projection, integration, restore, retention or runtime/configuration failures rather than one generic memory/model failure.
- Runtime/adapter/schema/compiler/scheduler/hardware/harness failures are separately classified from model-decision failures.
- Harness/runtime build, tool/extension mode and model/provider configuration are benchmark identity fields; same-model scores under different harnesses are not interchangeable.
- Realized context, GPU/CPU placement and runtime cache/load metrics supplement independent host performance and verifier-owned success evidence.

## Historical failure/redesign controls retained

- AutoGen — heavy rewrite, then maintenance-only; Microsoft Agent Framework successor.
- SWE-agent — rewrite/runtime extraction, then mini-swe-agent successor.
- OpenAI Swarm — experimental predecessor replaced by Agents SDK.
- AutoGPT Classic — unsupported legacy; maintained direction moved toward explicit workflow/block platform.
- BabyAGI original — archived generation/reconceptualization.
- GPT-Engineer — archived.
- GPT Pilot — unmaintained with documented supply-chain compromise.
- AgentGPT — archived; cause/successor unresolved.
- Aider — status unresolved; do not infer abandonment from silence/community forks.

Explicit continuity controls:
- OpenDevin → OpenHands.
- Block Goose → AAIF Goose.
- Strands `sdk-python` → `harness-sdk` monorepo.

## Next research task boundary

Task 19 is complete once `projects/gemini-cli.md`, catalog, state and watchlist are committed. The next task is **Graphiti deep research only**. Do not begin it until separately instructed, and when it is begun, stop before Microsoft Agent Framework.
