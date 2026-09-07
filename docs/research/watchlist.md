# Research Watchlist

Task 3 established the research-priority queues. Task 4 added transition/status evidence. Tasks 5–20 completed one-project-at-a-time deep research through **Graphiti**. Rank continues to mean **study/watch sooner because the candidate is expected to reduce ACL/Vera uncertainty**; completed research is not an adoption list.

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
- `projects/graphiti.md`

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

High-value findings retained for later comparison:
- Deterministic tiered policy with protected `ALLOW`/`DENY`/`ASK_USER`, headless fail-closed behavior and checker failures is strong authority reference material.
- Policy/approval, capability grant, realized sandbox and effect settlement are separate domains.
- Shell policy must bind behavior-bearing arguments, not only executable/subcommand labels; #29189 is the current Windows `git diff --output` regression fixture.
- Incremental filesystem/network sandbox expansion is preferable to disabling isolation globally when practical.
- Provider/control-plane credentials should remain outside worker effect environments.
- Current first-class provider surface is Gemini/cloud oriented rather than a direct Ollama/llama.cpp/vLLM local-provider reference.
- Extensions/MCP are executable trust surfaces; config hashing helps identity but not publisher/artifact provenance.
- Subagent registry/context isolation is useful but does not create OS/credential isolation; child effect authority should be explicit.
- ACP resume must be read-before-create and ownership-fenced; #28693/#28775 remain current fixtures.
- Append-oriented semantic JSONL history is useful, while live progress and durable recording can diverge; #29198 is a stable-release resume/retention fixture.
- Shadow-Git checkpoints are valuable pre-effect workspace evidence but not full continuation/effect checkpoints.
- Auto-memory locks are local coordination rather than truth or distributed writer fencing.
- Deterministic integration correctness and stochastic behavioral reliability should be measured separately; repeated pass distributions are preferable to one successful run.
- Protected policy/checker/verifier/hook roots belong outside worker mutation authority.
- Gemini CLI is strongest as execution-policy, host-integration, checkpoint/session and eval reference beneath ACL-owned scheduling/effects/credentials/verification.

See `projects/gemini-cli.md` for primary sources and explicit non-conclusions.

## Task 20 — Graphiti research result

**Status:** current Graphiti deep research complete; no dependency/adoption/memory-architecture/database/model decision made.

High-value findings to carry into later comparison:
- **Three memory planes:** raw episodes/evidence, resolved semantic entities/facts and derived communities are distinct. This is strong Vera reference material for keeping observation, belief and summary separate.
- **Provenance is first-class:** semantic facts retain supporting episode IDs and episodes link to mentioned entities. Provenance still establishes origin rather than truth, and raw episode retention can be disabled.
- **Bi-temporal memory is high value:** `valid_at`/`invalid_at` represent world validity while `created_at`/`expired_at` represent system mutation time. Vera should preserve this distinction.
- **Temporal recency is not authority:** Graphiti's new-information invalidation model must sit below Vera source/trust/confidence policy; newer low-trust evidence cannot automatically supersede verified memory.
- **Current invalidation path is a critical fixture:** current main still searches invalidation candidates group-wide and sends bare fact strings to a small-model contradiction judge. #1728 reports collateral retirement of unrelated still-true facts.
- **Memory invalidation is a privileged effect:** require structural replacement eligibility, provenance/trust comparison, audit/reversibility and stronger confirmation in high-risk domains.
- **Small-model syntax validity is not semantic safety:** #1666 records severe contradiction-detection degradation for one non-reasoning small-model setup while duplicate detection remained strong.
- **Current versus historical retrieval should be explicit:** core supports temporal filters, while open #1645 records the reference MCP search mixing invalidated and live facts absent explicit filtering.
- **`group_id` is partition metadata, not authentication:** do not use a graph/group name as user/project authority.
- **FalkorDB concurrency is a current isolation fixture:** read paths have call-scoped routing improvements, but current `add_episode` still mutates shared driver state; #1676 demonstrates concurrent groups silently writing into the wrong physical graph.
- **Backend is memory identity:** Neo4j/FalkorDB/Neptune/Kuzu paths have materially different routing/search/concurrency behavior and migration history; Kuzu is currently deprecated upstream in Graphiti.
- **Primary graph save has useful transactional scope:** episode/entities/MENTIONS/facts are saved through one `execute_write` transaction.
- **Full memory operation settlement is broader:** optional saga/link updates happen afterward and episode removal spans separate cleanup calls, so crash recovery needs explicit derived-maintenance/delete reconciliation.
- **Local/OpenAI-compatible support is real but conditional:** `OpenAIGenericClient` supports Ollama, vLLM and llama.cpp-style endpoints with `json_schema` or prompt-guided `json_object`, while current docs/source explicitly acknowledge local/small-model structured-output variability.
- **Memory benchmark must test semantic maintenance:** entity resolution, dedupe, contradiction, temporal extraction, false invalidation and stale-fact survival matter more than JSON parsing alone.
- **Embeddings are durable schema:** #1328 plus current Neo4j search source show null/dimension-invalid vectors can poison similarity retrieval; model/dimension changes require versioned migration/re-embedding.
- **Raw source text is untrusted:** current extraction puts episode/prior-episode content into memory-construction prompts. Ingested/retrieved text must not gain policy/tool/credential authority.
- **MCP exposes high-authority memory effects:** add/direct-write/delete/clear must remain behind ACL/Vera principal/domain/effect authorization. Reference server `group_id` is not that authorization layer.
- **OpenTelemetry is operational evidence:** useful spans/metrics do not prove a memory mutation or reconciliation settled.
- **Paper benchmarks are encouraging but bounded:** Zep/Graphiti DMR/LongMemEval results show retrieval value, while the paper itself critiques DMR and the results do not constitute current self-hosted Graphiti guarantees.
- **Graphiti complements Letta:** current evidence suggests Graphiti-style temporal semantic/evidence memory and Letta-style curated persistent agent memory are potentially complementary planes rather than one automatically replacing the other.
- **Boundary:** Graphiti does not replace ACL scheduling/fencing/effect ledger/verifier/credential authority or Vera's epistemic truth/provenance policy.

See `projects/graphiti.md` for primary sources, current failure evidence, 22 regression fixtures, candidate invariants and explicit non-conclusions.

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
16. **Graphiti** — `getzep/graphiti` — **Task 20 complete**.
17. **Microsoft Agent Framework** — `microsoft/agent-framework` — **next task only**.
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
- Personal/identity memory, shared/project memory, task memory, recall/history, raw episodic evidence, semantic facts and trusted policy/configuration are separate state/authority domains.
- Persistent memory is not verified truth merely because it is durable, Git-tracked or graph-linked.
- Important memory needs provenance/evidence/trust/confidence/conflict/supersession semantics appropriate to domain risk.
- Chronological recency is not an authority hierarchy; newer lower-trust evidence cannot silently replace stronger verified memory.
- Temporal world-valid time and system-ingestion/invalidation time are separate from epistemic/source authority.
- Canonical memory invalidation is a privileged reversible effect; unconstrained model contradiction output is advisory rather than sufficient authority.
- Current-state memory retrieval and historical/evidence retrieval should be explicit intent/policies rather than silently mixed.
- Compaction summaries, community summaries and extracted memory are context/learning products, not canonical evidence.
- Learned memory, skills/procedures, trusted executable configuration and security policy are distinct trust classes.
- Learning/background reflection must not silently expand tools, credentials, network/filesystem authority or deploy trusted code.
- Imported transcripts/trajectories/raw episodes remain lower-trust data until provenance/trust is evaluated.
- A memory `group_id`/database/graph namespace is not authenticated principal identity or authorization.
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
- Per-request database/memory-domain routing should not mutate shared global driver state across asynchronous/concurrent work.
- Local PID/age locks and in-process session registries are coordination, not distributed writer fencing.
- A saved transcript/trajectory/inference cache/remote task handle is not automatically an ACL checkpoint.
- Re-deriving agent-loop transitions from persisted semantic state is preferable to hidden in-memory loop progress, but state still needs separate workspace/effect/authority evidence before safe continuation.
- A durable checkpoint still does not imply exactly-once external effects.
- Durable action/result relationships are atomic semantic state; orphan results/calls are corruption.
- Raw provider/episode evidence, canonical semantic facts/messages, persisted projections, summaries/UI and reflection inputs are separately testable representations.
- Primary memory graph writes and post-write derived maintenance can have different transaction/settlement boundaries; full operation success requires both to settle or reconcile.
- Memory deletion is a multi-object effect and needs crash reconciliation rather than inference from one missing record.
- Background memory generation, Git commit and authoritative parent-memory integration are separate settlement states.
- Reflection conflicts/dirty parents/failed integration remain visible rather than silently counting as learned memory.
- A restore operation stages and verifies replacement before destroying/switching authoritative current state.
- Pre-effect shadow-Git/source checkpoints are useful workspace evidence but do not cover ignored files, processes, databases, APIs/network or credentials unless explicitly added.
- Partial/in-progress work stays visibly interrupted/uncertain after crash/recovery.
- Lost/expired remote handles do not prove backing computation stopped.
- Physical persistence retention is separate from model-context compaction and execution settlement.
- Live execution and required durable recording are separate lifecycle dimensions; loss of required durability must become explicit degraded/paused state rather than invisible logging failure.
- Runtime model residency/keep-alive and KV/prompt cache are performance state, not durable agent continuation authority.
- Embedding model/dimension/profile is durable memory schema; changing it requires validation/migration rather than silent replacement.

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
- For Graphiti-like memory deployments, record exact Graphiti revision, database/driver/schema/routing profile, LLM and small-model runtime/client/structured-output mode, prompt/schema revision, embedder model/dimension and reranker.
- Local memory maintenance qualification must test semantic entity resolution/deduplication/contradiction/temporal correctness, not only schema-valid output.
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
- Remote prompts, resources, graph episodes, memory and server instructions remain lower-trust model content regardless of valid protocol/storage shape.
- Ingested episode text is evidence content, never trusted memory/tool/credential-policy instructions by virtue of persistence.
- Cache TTL is freshness guidance, not authorization, provenance or immutable state version.
- Server-declared public cacheability cannot override ACL/Vera trust isolation.
- Loopback binding/CORS/Host-header checks and service authentication are separate controls; exposing a local inference or memory API beyond loopback requires explicit outer network/auth policy.

### Verification, evaluation and evidence
- The system under test does not own the authoritative definition of pass/fail.
- Deterministic host/verifier evidence precedes semantic model grading when machine-observable.
- Deterministic harness/integration correctness and stochastic model behavioral reliability are separate scores.
- Model-role promotion uses repeated trials/pass distributions and exact model/runtime/harness/fixture identity rather than one successful run.
- Memory-maintenance promotion also measures false invalidation, missed contradictions, provenance and current/history retrieval correctness.
- Reliability classes such as `USUALLY_PASSES`/`ALWAYS_PASSES` are useful reference patterns, not preselected ACL thresholds.
- Missing required evidence yields explicit invalid/failure rather than implicit pass.
- Verifier tests/hashes/sidecars/control roots stay outside worker mutation authority.
- Trace/model/tool/memory data may contain secrets; raw traces, operational telemetry and product analytics have separate audiences/retention.
- OpenTelemetry and runtime metrics are operational evidence, not authoritative memory/effect settlement or independent acceptance.
- Provider/runtime request-replay logs are sensitive evidence when they contain full prompts/tool schemas/project data.
- Evidence export/delivery has its own settlement state.
- Protocol/SDK/harness/evaluator failures are classified separately from model failures.
- Memory failures are classified as epistemic, contradiction/invalidation, transcript-projection, integration, restore, retention, routing/isolation, embedding/retrieval or runtime/configuration failures rather than one generic memory/model failure.
- Runtime/adapter/schema/compiler/scheduler/hardware/harness failures are separately classified from model-decision failures.
- Harness/runtime build, tool/extension mode and model/provider configuration are benchmark identity fields; same-model scores under different harnesses are not interchangeable.
- Historical managed-product benchmark scores are evidence, not current self-hosted component guarantees.
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

Task 20 is complete once `projects/graphiti.md`, catalog, state and watchlist are committed. The next task is **Microsoft Agent Framework deep research only**. Do not begin it until separately instructed, and when it is begun, stop before Google ADK.
