# Research Watchlist

Task 3 established the research-priority queues. Task 4 added transition/status evidence. Tasks 5–15 completed one-project-at-a-time deep research through **Model Context Protocol**. Rank continues to mean **study/watch sooner because the candidate is expected to reduce ACL/Vera uncertainty**; completed research is not an adoption list.

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

## Task 15 — Model Context Protocol research result

**Status:** current MCP deep research complete; no dependency/adoption/fork decision made.

High-value findings to carry into later comparison:

- **Current-generation boundary:** MCP `2026-07-28` intentionally moved from a bidirectional/stateful protocol to a stateless request/response core. Modern MCP has no protocol-level session/initialize handshake; explicit handles/IDs carry application state across requests.
- **Transport != task identity:** persistent stdio process, HTTP connection, JSON-RPC request, MCP Task, ACL task/run/effect and Vera conversation/memory must remain distinct identities.
- **Protocol era is behavior-bearing:** modern `2026-07-28+`, legacy `2025-11-25` and earlier, and dual-era fallback have different lifecycle semantics. Record realized version/transport/capabilities rather than a generic `mcp=true` flag.
- **Host authority is the useful topology:** the MCP host owns user consent, model integration, cross-server context and security. ACL/Vera should retain those responsibilities rather than delegate global authority to MCP servers.
- **Primitive labels are not authority:** tools are model-controlled protocol primitives; resources are application-driven; prompts are user-selected but server-authored. None should automatically inherit governance or execution authority.
- **Canonical tool identity needs origin:** tool names are server-local, `serverInfo` is self-reported/not security identity, and tool annotations are untrusted unless the server itself is trusted. ACL should bind tool identity to server/trust origin plus definition/schema digest/version.
- **Header routing is a policy surface:** `Mcp-Method`, `Mcp-Name` and tool-schema `x-mcp-header` support gateway routing/authorization, but server-authored schema metadata must not define privileged headers without host policy.
- **Remote resources/prompts remain untrusted context:** resource network fetches need SSRF/size/time policy and prompt/resource/discovery content needs provenance plus injection controls.
- **MRTR continuation is authority-bearing state:** client-echoed `requestState` must be treated as attacker-controlled if it affects authorization/resource/business logic; integrity binding should include principal, operation/parameter digest and expiry. Integrity does not provide single-use/idempotency by itself.
- **Open #2920:** URL-mode MRTR still has an unresolved bounded waiting/retry/cancel UX/lifecycle ambiguity; ACL approvals should use their own explicit stable state machine rather than inherit implicit retry semantics.
- **Cancellation remains cooperative:** request/task cancellation acknowledgment is intent, not proof the backing process/effect stopped. Progress may refresh idle deadlines but a hard maximum deadline remains separate.
- **Subscription streams are transport observation:** reconnect requires resubscription. Open #3348 identifies a same-revision contradiction between cancellation and subscription teardown documentation, making graceful-vs-abrupt end-state a required interoperability fixture.
- **Broken stream replay is a new request:** current Streamable HTTP removed `Last-Event-ID` resumability. Reissuing an effect-bearing call after transport loss needs ACL-owned idempotency/reconciliation evidence.
- **Tasks are durable remote-operation handles:** the official `io.modelcontextprotocol/tasks` extension persists a task before returning its handle, defines explicit working/input-required/terminal states, supports polling/mid-flight input and survives client reconnect if the handle is retained.
- **Task handle != ACL checkpoint:** a remote task does not capture ACL workspace, process custody, credential/policy state, external-effect evidence or permission to resume the broader project task.
- **Task input IDs are strong reference material:** input request keys cannot be reused during a task lifetime, allowing deterministic dedupe and exactly-addressed remote approvals/input.
- **Task cancel/TTL != execution settlement:** `tasks/cancel` is eventually-consistent cooperative intent. Contributor response on ext-tasks #11 confirms storage/retention lifecycle is deliberately separate from terminating the underlying computation.
- **Task handles need authorization binding:** task IDs may be bearer handles, but the spec also requires per-request authorization checks. Open ext-tasks #20 shows denial/error representation remains a broader protocol concern. ACL should bind remote handle to principal/project/task/effect/policy rather than rely on possession.
- **No task enumeration:** `tasks/list` does not exist. This reduces cross-caller discovery but means a client that loses its task IDs cannot recover them through protocol enumeration; ACL must persist handles until settlement/retirement.
- **Out-of-band sensitive elicitation is valuable:** form mode may not request passwords/API keys/access tokens/payment credentials; URL mode keeps those sensitive interactions outside the MCP client/model channel and requires visible destination/consent.
- **Roots are deprecated and never were access control:** do not map MCP roots to worker filesystem authority.
- **Sampling is deprecated:** new implementations are directed to direct LLM-provider APIs, reinforcing that MCP should not own ACL's local/cloud model runtime.
- **Authorization is service-scoped:** HTTP MCP uses OAuth resource-server semantics, PKCE, resource indicators/audience binding, issuer validation and least-privilege scope challenges.
- **Token passthrough is forbidden:** downstream services require their own audience-correct token. This strongly supports Vera's future credential-broker/service-grant architecture.
- **Authorization/discovery is an SSRF surface:** server-controlled discovery URLs require DNS/IP/redirect/private-network policy and bounded fetches.
- **STDIO environment is not permission policy:** even though MCP stdio commonly obtains credentials from environment/config, ACL worker children should receive a minimal explicit environment, not supervisor `os.environ`.
- **Schema validation is trusted code/network surface:** JSON Schema external refs are disabled by default; opt-in dereference needs network restrictions and unresolved authority-bearing schemas should fail closed.
- **Cache freshness != provenance/authority:** TTL is a freshness hint, not state-version guarantee; `cacheScope` does not replace access control. MRTR retries are not cacheable.
- **Open #3207/#3213 are warning fixtures:** current open reports argue that server-controlled public cache scope and discovery `instructions` can amplify cross-user stale/malicious content or prompt injection if clients/intermediaries elevate them. No maintainer resolution was found; preserve these as tests, not universal vulnerability claims.
- **Extensions are independently versioned capability:** optional, namespaced, disabled by default and explicitly negotiated. Core MCP conformance does not imply Tasks/UI/auth-extension parity.
- **Tier 1 current-generation support:** lead-maintainer release notes state TypeScript, Python, Go and C# SDKs support `2026-07-28`, but exact SDK/extension behavior still needs deployment qualification.
- **Boundary:** MCP is strongest as a standardized interoperability layer beneath ACL/Vera-owned scheduling, authorization, credential governance, memory, sandbox/process custody, effect ledger, checkpoints and independent verification.

See `projects/model-context-protocol.md` for primary sources, current open issues, candidate ACL regression fixtures and explicit non-conclusions.

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
12. **Goose** — `aaif-goose/goose` — **next task only**.
13. **Ollama** — `ollama/ollama`.
14. **Letta Code** — `letta-ai/letta-code`.
15. **Gemini CLI** — `google-gemini/gemini-cli`.
16. **Graphiti** — `getzep/graphiti`.
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

### Identity and authority
- Canonical effect capability identity includes authoritative origin plus definition/version; name-only dispatch is unsafe across providers/servers.
- Approval/no-approval policy and actual tool/sandbox authority are separate dimensions.
- Persisted approvals bind to exact call/origin/task/objective/tool/policy versions; incompatible semantic changes invalidate them.
- Malformed/uninspectable effect parameters fail closed.
- Revalidate mutable policy immediately before irreversible effects after waits/approval.
- Child roles may reduce authority but must not widen the parent ceiling.
- Reviewer/verifier capability should be minimized independently from worker capability.
- Self-reported server/model/provider names are metadata, not security identity.

### Workspace, sandbox and credentials
- Workspace isolation, Git/ref authority, secrets, verifier roots and external effects are separate trust domains.
- Container/sandbox/runtime selection is not a complete permission profile; mounts/network/user/resources/credentials/capabilities are separate.
- Local-host worker execution should not inherit ambient supervisor environment/credentials.
- Durable state should reference credentials; live authority is rebound from current trusted policy after resume.
- Runtime-visible plaintext credentials cannot later be made secret from arbitrary worker code by revocation.
- MCP Roots/workspace hints are not access control.

### State, recovery and effects
- Logical request/idempotency, run/attempt, process, protocol request, remote task handle and durable session identities remain separate.
- Transport/session/stream continuity is not authoritative project/task/effect state.
- Each durable state domain needs one authoritative writer; multi-process state requires leases/generation/CAS/fencing.
- A saved transcript/trajectory/inference cache/remote task handle is not automatically an ACL checkpoint.
- A durable checkpoint still does not imply exactly-once external effects.
- Durable action/result relationships are atomic semantic state; orphan results/calls are corruption.
- Partial/in-progress work stays visibly interrupted/uncertain after crash/recovery.
- Lost/expired remote handles do not prove the backing computation stopped.
- Physical persistence retention is separate from model-context compaction and execution settlement.

### Cancellation, timeouts and retry
- Every blocking plane needs an explicit timeout/cancellation owner: provider request/stream, prompt/prefill/generation, tool process, remote runtime/task and whole run.
- Progress/heartbeats may control idle timeout but never remove hard maximum deadlines.
- Cancellation acknowledgment is not process termination or effect settlement.
- Immediate abort and stop-at-safe-boundary are distinct controls.
- Retry is not authority to replay a possibly already-executed effect/request.
- Provider/request IDs are correlation identifiers, not automatically idempotency/effect IDs.
- Broken transport retry of an effect-bearing request needs durable reconciliation/idempotency policy.

### Model/runtime capability and protocol compatibility
- Local-model capability is an exact model + runtime + adapter + protocol/tool schema/namespace + configuration property.
- For llama.cpp-class deployments, include build/backend/driver, GGUF/quantization, template/parser/constraint backend, context/KV/cache and optimization/sampling settings.
- Template/schema/protocol capability discovery is not verified end-to-end behavior.
- MCP capability identity includes protocol era/version, transport, SDK/adapter revision, auth mode and negotiated extensions.
- Core protocol conformance does not imply optional extension parity.
- Silent modern/legacy fallback must not preserve the same verified-capability label.

### Schema, network and content trust
- Tool schemas, validation, authorization, execution and evaluation are distinct contracts.
- Schema converters/parsers/constraint compilers are trusted code and require adversarial regression fixtures.
- Remote schema/resource/auth/discovery URL dereference is a network/SSRF authority surface with private/loopback/redirect/size/time policy.
- Remote prompts, resources, memory and server instructions remain lower-trust model content regardless of valid protocol shape.
- Cache TTL is freshness guidance, not authorization, provenance or immutable state version.
- Server-declared public cacheability cannot override ACL/Vera trust isolation.

### Verification and evidence
- The system under test does not own the authoritative definition of pass/fail.
- Deterministic host/verifier evidence precedes semantic model grading when machine-observable.
- Missing required evidence yields explicit invalid/failure rather than implicit pass.
- Verifier tests/hashes/sidecars/control roots stay outside worker mutation authority.
- Trace/model/tool data may contain secrets; raw traces, operational telemetry and product analytics have separate audiences/retention.
- Evidence export/delivery has its own settlement state.
- Protocol/SDK/harness/evaluator failures are classified separately from model failures.

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

Task 15 is complete once `projects/model-context-protocol.md`, catalog, state and watchlist are committed. The next task is **Goose deep research only**. Do not begin it until separately instructed, and when it is begun, stop before Ollama.
