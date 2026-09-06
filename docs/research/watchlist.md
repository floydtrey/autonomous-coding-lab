# Research Watchlist

Task 3 established the research-priority queues. Task 4 added transition/status evidence. Tasks 5–11 completed deep research on Pydantic AI, Cline, LangGraph, promptfoo, Strands Harness SDK, Codex, and **OpenHands**. Rank still means **study/watch sooner because the candidate is expected to reduce ACL/Vera uncertainty**; completed research does not convert the queue into an adoption list.

Detailed historical artifacts remain in:
- `projects/ranked-projects.md`
- `people/ranked-people.md`
- `ranked-sources.md`
- `failures/failed-redesigned-attempts.md`
- `projects/active-projects.md`
- `people/active-people.md`

Completed project deep research:
- `projects/pydantic-ai.md`
- `projects/cline.md`
- `projects/langgraph.md`
- `projects/promptfoo.md`
- `projects/strands-harness-sdk.md`
- `projects/codex.md`
- `projects/openhands.md`

## Task 11 — OpenHands research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings to carry into later comparison:

- **System boundaries:** current OpenHands separates Agent Canvas/control-center, `software-agent-sdk` runtime/Agent Server, and automation scheduling/dispatch responsibilities; UI and scheduler do not need to own runtime truth.
- **Explicit conversation state:** lifecycle status, workspace, agent configuration, branch HEAD, hooks, stats and agent-specific state are durable runtime data rather than prompt-only instructions.
- **Generation-fenced writer ownership:** `ConversationLease` uses owner identity, monotonic generation, TTL/renewal, host/PID evidence and guarded writes; this addresses prior same-persistence split-brain behavior.
- **Crash relationship invariant:** closed issue #4487 showed that a tool action durably written before a stale branch HEAD was advanced could receive recovery output on the wrong branch and permanently poison later turns. Event persistence must preserve action→result relationship and authoritative branch identity.
- **Selective recovery:** known idle state can remain lazily hydrated while state persisted as `RUNNING` receives stronger crash-recovery treatment.
- **Resource-aware concurrency:** parallel tools use declared-resource locks; correctness depends on truthful resource declarations and safe fallback locking.
- **Open cancellation race #4777:** a tool cancelled while waiting for a resource lock can reportedly begin after the lock becomes available because cancellation is not rechecked at the side-effect boundary.
- **Blocking-work settlement:** current runtime main `fe91d7df...` adds regression tests demonstrating that cancelling async wrappers cannot forcibly stop blocking synchronous worker-thread code and can leave zombie-thread/lifecycle failures.
- **Cancellation != settlement:** a task is not safely stopped merely because a coroutine/UI state says cancelled; owned execution must actually terminate or remain explicitly unresolved.
- **Workspace != authority:** Docker/remote workspaces are execution transports. Mounts, environment projection, network, ports, GPU and credentials remain separate authority decisions.
- **Worktree != sandbox:** optional per-conversation Git worktrees reduce checkout collision but do not enforce filesystem escape, secret boundaries or external-effect rollback.
- **Confirmation != sandbox:** confirmation policies and security analyzers classify/approve actions but do not replace actual OS/filesystem/network/tool authority.
- **Credential architecture:** design issue #4288 argues for durable credential references plus explicit `brokered` versus `runtime_visible` delivery. It also documents why repeated redaction patches cannot structurally fix secret-bearing serializable state.
- **Runtime-visible credential honesty:** arbitrary code in a worker that receives plaintext can copy/exfiltrate it; later revocation cannot recall already-delivered material.
- **Design/shipped distinction:** #4288 is a target design, not a claim that every proposed credential-service/grant mechanism is already shipped; current code does contain credential-binding and persisted-secret scrubbing paths.
- **Ambient-state isolation:** closed issue #3815 showed a supposedly fresh persistence root could inherit model/profile settings from `~/.openhands`; all state/config roots must participate in isolation.
- **Model/runtime capability metadata:** current LLM layer carries canonical model identity, capability overrides, runtime metadata, retry/timeout and context expectations on top of LiteLLM.
- **Open Ollama timeout report #4255:** configured timeout and realized provider behavior can diverge; local-model benchmark probes must verify wire behavior.
- **Telemetry audience separation:** full LLM completion logs, Laminar/OTEL traces and allowlisted product telemetry are distinct channels with different sensitivity/purpose.
- **Critic boundary:** runtime critic/refinement can improve work but remains lower-trust than verifier-owned protected acceptance evidence.
- **Persistent repository memory:** model-visible `AGENTS.md`/repository memory can be useful but worker-writable persistent context must remain lower trust than ACL/Vera governance.
- **Boundary:** OpenHands does not replace ACL's outer project/backlog dependency scheduler, external-effect ledger, independent verifier, Vera long-term memory governance or final deployment-specific credential/network policy.

See `projects/openhands.md` for primary sources, current failure surfaces, design-vs-shipped distinctions, candidate invariants and ACL regression-fixture ideas.

## Task 10 — Codex research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings to carry into later comparison:

- **Permission-profile control roots:** Codex treats workspace source writability separately from `.git`, `.agents` and `.codex` control-plane metadata. ACL should similarly protect Git authority, worker/policy definitions, verifier fixtures and evidence roots inside otherwise writable projects.
- **Approval != authority:** approval policy and sandbox authority are independent. `approval_policy="never"` does not mean full access, and an action that requires an unavailable approval does not silently escalate.
- **Narrow persistent approvals:** reusable command-rule suggestions deliberately reject dangerously broad prefixes such as generic shells/interpreters, package runners, `git`, `rm` and `sudo`.
- **One-way child authority:** live child config refreshes parent sandbox/approval/cwd state, while custom roles can change model/instructions or reduce capability but cannot replace parent sandbox, approval, provider/base URL, MCP, apps or notification authority.
- **Hostile-role regression testing:** current role tests deliberately try danger-full-access, approval never, attacker provider URLs/MCP servers and other authority-expanding configuration and assert the parent authority survives.
- **Docs/code mismatch:** current subagent docs contain wording broad enough to suggest per-agent sandbox overrides, while shipped role code/tests are stricter. Current source/tests control this finding.
- **Capability inheritance is separate:** current main fix #43147 prevents fresh children from inheriting parent experimental-context activation when the child's own model does not support it. Child capability must be recomputed after model/runtime changes.
- **Reviewer least privilege:** Guardian review delegation uses a smaller extension surface than ordinary worker delegation, reinforcing that validator/reviewer roles should not inherit every worker capability.
- **Versioned authorization evidence:** Guardian hardening retains/reconstructs root user/verified authorization evidence after compaction and invalidates prior allow state when that root authorization version changes.
- **Compaction fail-closed:** review/checkpoint reuse fails closed when required compatible authorization evidence cannot be recovered after compaction.
- **Adapter realization:** recent Windows sandbox fixes show deny/environment policy can be correct at the high-level object and lost at a platform/wrapper bridge. Realized child authority needs direct regression probes.
- **Trust exceptions are operator-owned:** `allow_symlinked_codex_home` is narrow, default-off and intended for top-level user config, not project-controlled authority escalation.
- **Worktree != secret isolation:** managed worktrees give separate working directories, but `.worktreeinclude` can intentionally copy ignored `.env`/secret setup files. Secret projection must be a separate least-privilege policy.
- **Workspace identity:** Codex managed worktrees use detached HEADs by default and snapshot before automatic cleanup; ACL should retain explicit workspace/run identity distinct from branch/ref identity.
- **Thread/turn/item protocol:** current app-server state has durable thread/turn/item identities, version-specific generated schemas and bounded queues/backpressure.
- **Restore provenance:** omitted runtime settings such as cwd are restored from thread-owned retained settings, not arbitrary matching older history.
- **Visible partial forks:** when a source is mid-turn, fork semantics can preserve an explicit interruption marker rather than silently presenting a partial suffix as completed continuity.
- **Idempotent persistent mutations:** experimental project create/import paths use caller idempotency keys; logical project deletion is separately defined from deleting every thread/directory/file.
- **Native local providers:** Ollama and LM Studio are first-class Responses-provider paths, but compatibility still depends on exact provider/runtime/tool semantics.
- **Open local-provider failure #30994:** local Ollama setup can reportedly write top-level provider/catalog state and affect later unrelated OpenAI model routing; provider/profile state must remain scoped.
- **Open tool-routing failure #42488:** custom/Ollama providers can reportedly emit flattened dotted multi-agent tool names that the router rejects as unsupported; API compatibility does not establish identical tool namespace semantics.
- **Process-tree cancellation:** command cancellation/timeout targets process groups, uses terminate-then-kill escalation and bounds stdout/stderr drain tasks so orphaned pipes cannot hang completion indefinitely.
- **Effect boundary:** process death does not roll back already-completed filesystem/network/API/database effects; external-effect settlement remains a separate ACL responsibility.
- **Telemetry boundary:** Codex provides OTEL runtime evidence and sensitive prompt logging controls, but Task 10 did not find a promptfoo-like independent acceptance subsystem; ACL still needs independent validation authority.
- **Boundary:** Codex does not replace ACL's outer project/backlog scheduler, external-effect ledger, independent acceptance verifier, long-term memory governance, dependency governance or deployment-specific credential/network policy.

See `projects/codex.md` for primary sources, current failure surfaces, documentation/code distinction, candidate invariants and ACL regression-fixture ideas.

## Task 9 — Strands Harness SDK research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings retained for later comparison:
- composable model-loop/lifecycle/authorization/sandbox/persistence control planes;
- turn/token limits and explicit stop reasons outside prompt prose;
- separate provider/structured-output/intervention retry classes;
- typed fail-open/fail-closed intervention semantics;
- shipped Cedar authorization before tool execution;
- action authorization separate from objective integrity;
- explicit sandbox-vs-host execution boundary;
- application-owned sandbox provisioning/network/mount/credential lifecycle;
- single-live-writer limitation in built-in session persistence;
- restored message/checkpoint state as trusted executable input;
- provider-side durable conversation state separate from local messages;
- exactly-once interrupt IDs and replay/idempotency concerns;
- model-visible context management separate from authoritative task/effect state;
- native Python Ollama support plus OTEL/evaluation identity requirements.

See `projects/strands-harness-sdk.md` for the complete evidence.

## Task 8 — promptfoo research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings retained for later comparison:
- independent evaluation/red-team role rather than authoritative agent runtime ownership;
- deterministic tool/trace/trajectory assertions before semantic grading;
- required evidence channels should fail/invalid when unavailable rather than silently degrade;
- coding-agent failure taxonomy separates model behavior, harness boundary, verifier integrity and eval-design failures;
- host-side canaries, hashes, sidecars and traces can provide worker-independent evidence;
- mutable coding-agent rows need isolated/resettable workspaces;
- unsafe willingness, attempted action and verified effect are distinct labels;
- target and grader model/runtime identity both belong in reproducibility evidence;
- evaluator scripts/plugins are privileged executable dependencies;
- serializable evaluator descriptors should remain separate from live provider/client/session/credential objects.

See `projects/promptfoo.md` for the complete evidence.

## Task 7 — LangGraph research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings retained for later comparison:
- checkpoints, pending task writes, thread/checkpoint lineage, subgraphs, interrupts, retries/timeouts and typed task/checkpoint/debug streams;
- explicit durability modes without an implied exactly-once external-effect guarantee;
- external-effect settlement needs separate evidence/idempotency handling;
- concurrent approvals need stable interrupt IDs and ambiguous resume should fail closed;
- subgraph replay identity must survive parent forks/retries;
- state mutation must hydrate from one authoritative persistence source/version;
- replayable tasks need persisted or deterministically reacquirable inputs;
- physical checkpoint retention/deletion fencing is separate from model-context compaction.

See `projects/langgraph.md` for the complete evidence.

## Task 6 — Cline research result

**Status:** project deep research complete; no dependency/adoption/fork decision made.

High-value findings retained for later comparison:
- stateless agent/model loop separated from stateful core/session ownership;
- runtime enforcement is stronger than prompt-only Plan-mode restraint but shell blacklists remain defense-in-depth;
- approval UI, model classification and execution authority are separate layers;
- embedded agent runtimes can create a second permission/tool/cwd system;
- file mutation requires authoritative execution-time state;
- checkpoint identity must survive retries/compaction/restart and restore needs fail-closed concurrency/history protection;
- local compatibility must include model + runtime + adapter + backend settings;
- deterministic recovery should prove progress and use bounded retry;
- loop/mistake detection belongs in runtime telemetry.

See `projects/cline.md` for the complete evidence.

## Task 5 — Pydantic AI research result

**Status:** project deep research complete; no dependency/adoption decision made.

High-value findings retained for later comparison:
- typed agent/tool/output execution with explicit provider/model/profile seams;
- model/runtime capability profiles rather than endpoint compatibility assumptions;
- separate retry categories/budgets;
- validation, approval and authority as separate facts;
- fail-closed authority-bearing configuration composition;
- `StepPersistence` settled/interrupted snapshots plus `unknown_after_crash` effects;
- persistent memory is bounded but lower-trust on later re-entry;
- filesystem/shell application controls do not replace OS/container isolation;
- trajectory/span evaluation complements final-output checks.

See `projects/pydantic-ai.md` for the complete evidence.

## Task 4 transition/status updates

- **SWE-agent** — upstream-declared maintenance-only and superseded by mini-swe-agent. Its ranked slot is transition-aware.
- **OpenAI Agents SDK** — Swarm is its explicit experimental predecessor.
- **AutoGen** — maintenance mode; Microsoft Agent Framework is the named successor.
- **Aider** — status unresolved, not abandoned; community forks/concerns are discovery evidence only until an authoritative status change.

## Ranked active-project queue — Task 3 snapshot with live research status

### Tier A — immediate deep-research queue
1. **Pydantic AI** — `pydantic/pydantic-ai` — **Task 5 complete**; `projects/pydantic-ai.md`.
2. **Cline** — `cline/cline` — **Task 6 complete**; `projects/cline.md`.
3. **LangGraph** — `langchain-ai/langgraph` — **Task 7 complete**; `projects/langgraph.md`.
4. **promptfoo** — `promptfoo/promptfoo` — **Task 8 complete**; `projects/promptfoo.md`.
5. **Strands Harness SDK** — `strands-agents/harness-sdk` — **Task 9 complete**; `projects/strands-harness-sdk.md`.
6. **Codex** — `openai/codex` — **Task 10 complete**; `projects/codex.md`.
7. **OpenHands** — `OpenHands/OpenHands` / runtime `OpenHands/software-agent-sdk` — **Task 11 complete**; `projects/openhands.md`.
8. **SWE-agent / mini-swe-agent** — `SWE-agent/SWE-agent` / `SWE-agent/mini-swe-agent` — **next task; transition-aware** because SWE-agent is maintenance-only and names mini-swe-agent as successor.
9. **llama.cpp** — `ggml-org/llama.cpp` — local runtime, constrained JSON/tool-call grammars, parsers, backend/KV behavior.
10. **OpenAI Agents SDK** — `openai/openai-agents-python` — serializable run state, approvals, sandbox state, traces and lifecycle tests.

### Tier B — high-value follow-up
11. **Model Context Protocol** — `modelcontextprotocol/modelcontextprotocol`
12. **Goose** — `aaif-goose/goose`
13. **Ollama** — `ollama/ollama`
14. **Letta Code** — `letta-ai/letta-code`
15. **Gemini CLI** — `google-gemini/gemini-cli`
16. **Graphiti** — `getzep/graphiti`
17. **Microsoft Agent Framework** — `microsoft/agent-framework`
18. **Google ADK** — `google/adk-python`
19. **LiteLLM** — `BerriAI/litellm`
20. **vLLM** — `vllm-project/vllm`

### Tier C — comparative / situational watch
21. **OpenCode** — `anomalyco/opencode`
22. **Mem0** — `mem0ai/mem0`
23. **smolagents** — `huggingface/smolagents`
24. **Agno** — `agno-agi/agno`
25. **LlamaIndex** — `run-llama/llama_index`
26. **CrewAI** — `crewAIInc/crewAI`
27. **Mastra** — `mastra-ai/mastra`

## Ranked recurring-contributor queue — Task 3 snapshot

This ranks public technical signal, not formal authority, seniority, employment status or outreach priority.

1. **Saoud Rizwan** — `saoudrizwan` — Cline — file/checkpoint/permission/provider safety.
2. **Nick Hollon** — `nick-hollon-lc` — LangGraph — durable/remote runtime lifecycle, checkpoint/state and streaming.
3. **Jesús Samuel** — `jesussamuel-byte` — Gemini CLI — path/symlink/configuration authorization and command safety.
4. **Graham Neubig** — `neubig` — OpenHands — provider/evidence/repository-boundary and lifecycle decisions.
5. **Johannes Gäßler** — `JohannesGaessler` — llama.cpp — local runtime backends, quantization/KV and multi-device behavior.
6. **Douwe Maan** — `DouweM` — Pydantic AI — cancellation/concurrency/session lifecycle.
7. **Anas Khan** — `anxkhn` — SWE-agent — harness/evaluation correctness and regression discipline.
8. **Kazuhiro Sera** — `seratch` — OpenAI Agents SDK — verification, CI and realtime lifecycle testing.
9. **Jack Amadeo** — `jamadeo` — Goose — MCP/GDK integration and packaging.
10. **Kartik Labhshetwar** — `kartik-mem0` — Mem0 — memory release/integration/configuration signal.

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

`sources.md` remains the governing evidence ladder; `ranked-sources.md` only sets review priority.

## Historical failure/redesign set — Task 4

1. AutoGen — ground-up v0.4 rewrite, then maintenance-only with Microsoft Agent Framework named successor.
2. SWE-agent — near-total 1.0 rewrite, then maintenance-only with mini-swe-agent named successor.
3. OpenAI Swarm — experimental predecessor replaced by OpenAI Agents SDK.
4. AutoGPT Classic — unsupported legacy experiment; maintained direction moved to workflow/block Platform architecture.
5. BabyAGI original — archived snapshot; project reconceived around a self-building function framework.
6. GPT-Engineer — owner-archived experimentation CLI / precursor to managed-product direction.
7. GPT Pilot — explicitly unmaintained with an upstream-documented prolonged credential-stealing supply-chain compromise.
8. AgentGPT — owner-archived/read-only; authoritative cause/successor unresolved.

See `failures/failed-redesigned-attempts.md` for evidence and causal boundaries.

## Status unresolved

- **Aider** — `Aider-AI/aider` — not archived; no authoritative abandonment/successor declaration. Recheck only on authoritative status change.

## Explicit non-failure identity controls

- OpenDevin → OpenHands — rename/continuity; active.
- Block Goose → AAIF Goose — governance/org migration with active development.
- Strands `sdk-python` → consolidated `harness-sdk` monorepo — canonical repository consolidation/continuity; not evidence of abandonment.

## Security / governance anchors retained regardless of ordinal source rank

- OWASP AI Agent Security Cheat Sheet
- OWASP Agent Memory Guard
- OWASP GenAI Security Project / Agentic Security Initiative
- MITRE ATLAS
- NIST AI / Agentic AI guidance

## Rules to preserve in later work

- Rank is information value, not adoption preference.
- Deep research extracts mechanisms/invariants first; dependency/fork/build decisions remain later comparative work.
- Model proposals and role labels are not authority boundaries.
- Protect control-plane metadata/definitions/evidence inside otherwise writable worker roots.
- Approval/no-approval policy and sandbox/tool authority are separate dimensions.
- Persisted approvals must be narrow; generic interpreter/shell/package-runner approval is equivalent to large future authority.
- Child roles/config can reduce authority but must not widen the live parent authority ceiling.
- Child model/runtime capability must be recomputed after model/provider changes rather than inherited blindly.
- Authorization evidence is versioned state; task/objective/instruction changes can invalidate prior approvals.
- Compaction/replay must preserve required authorization evidence or fail closed.
- Reviewer/validator capability should be minimized independently from worker capability.
- Realized sandbox restrictions must be tested after every adapter/platform bridge, not assumed from parent configuration.
- Path/symlink/trust exceptions must be explicit and operator-owned rather than project-controlled.
- Workspace isolation, Git/ref authority, secret projection, verifier roots and external effects are separate trust domains.
- Workspace/run identity is separate from branch/ref identity and needs a recorded source baseline.
- Persistent protocol/state schemas must be pinned to runtime version when authority semantics depend on them.
- Bounded queues/backpressure and explicit overload state are preferable to unbounded long-running buffering.
- Resume/fork state must be provenance-owned; matching arbitrary history is not authoritative state.
- Partial/in-progress execution must remain visibly interrupted/uncertain on fork/recovery.
- Durable create/import/enqueue operations require stable idempotency identity.
- Logical deletion/retirement is separate from physical evidence/workspace/file destruction.
- Local-model capability means exact model + runtime + adapter + protocol/tool namespace + configuration.
- Provider/profile selection is scoped state; temporary local setup must not mutate unrelated/global provider identity.
- Cancellation must target process trees/jobs and bounded pipe/output settlement.
- Process settlement is separate from filesystem/network/API/database effect settlement.
- Runtime limits, cancellation and retry policy belong in observable harness state rather than prompt prose.
- Retry classes need separate reasons/budgets/progress tests.
- Tool schema, runtime validation, authorization, execution and evaluation are distinct contracts.
- Typed policy decisions should have explicit fail-open/fail-closed error semantics; authority-bearing controls should fail closed on ambiguity.
- Action authorization does not replace principal-approved objective/task-scope provenance.
- Logical request/idempotency identity, run/attempt identity, agent/process identity and durable session identity must remain separate.
- Each durable state domain needs one authoritative owner; nested components must not persist competing versions.
- Persistent state requires distributed writer/fencing/lease semantics when multiple processes are possible.
- A stale writer that lost its lease/generation may not commit authoritative task/effect/checkpoint state.
- Persisted event/effect evidence must preserve action→result relationships and authoritative branch identity after crash recovery.
- Cancellation/authority/lease state must be rechecked at the irreversible boundary after blocking waits.
- Async cancellation does not prove blocking thread/process settlement; terminal state must reflect actual custody.
- Restored history/checkpoints are trusted execution input; valid serialization does not prove provenance or permission to resume.
- UI stream, persisted replay history, model-visible context and audit/effect evidence are distinct representations with explicit consistency contracts.
- Context trimming/summarization/offloading is model-state mutation, not authoritative project/effect truth.
- Durable state should reference credentials rather than carry reusable secret material as ordinary serializable configuration.
- Runtime-visible credential delivery is an explicit authority grant; already-delivered plaintext cannot be made secret from arbitrary worker code by later revocation.
- All ambient state roots (HOME/profiles/env/global caches/config) must participate in isolation; a fresh workspace alone is not a fresh runtime.
- Telemetry may contain secrets/system prompts/tool data; evidence audience/redaction is separate policy.
- Raw model/tool traces, operational tracing and product analytics should have separate schemas/audiences/retention.
- Evaluation evidence must bind to stable project/task/run/test identity; wrong correlation invalidates otherwise valid spans.
- The system under test should not own the authoritative definition of whether it passed.
- Deterministic evidence should precede semantic model grading when the property is machine-observable.
- Missing required evidence should produce an explicit invalid/failure state rather than an implicit pass.
- Verifier-owned tests/hashes/sidecars should remain outside worker mutation authority.
- Conversation/graph state, workspace state and external-effect evidence are separate recovery dimensions.
- A durable checkpoint does not imply exactly-once external side effects.
- Physical persistence retention is separate from model-context compaction.
- Worker-writable persistent repository memory/instructions remain lower trust than protected governance and verified project truth.
- Current bugs/regression fixes can be more valuable than feature lists because they expose actual failure surfaces.
- Preserve documentation claims, design proposals, shipped behavior, architectural generations and canonical aliases separately so mismatches/migrations remain auditable.

## Next research task boundary

Task 11 is complete once the OpenHands research file, catalog, watchlist and state are committed. The next task is the **SWE-agent / mini-swe-agent transition-aware slot only**. Do not begin it until separately instructed, and when it is begun, stop before llama.cpp.
