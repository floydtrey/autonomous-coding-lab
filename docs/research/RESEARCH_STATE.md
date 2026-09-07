# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 19 — Gemini CLI deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Completed campaign checkpoints
- Tasks 1–4: recurring sources, active projects/people, ranked research priority, and failed/abandoned/heavily redesigned attempts.
- Task 5: **Pydantic AI / official Harness** — `projects/pydantic-ai.md`.
- Task 6: **Cline** — `projects/cline.md`.
- Task 7: **LangGraph** — `projects/langgraph.md`.
- Task 8: **promptfoo** — `projects/promptfoo.md`.
- Task 9: **Strands Harness SDK** — `projects/strands-harness-sdk.md`.
- Task 10: **Codex** — `projects/codex.md`.
- Task 11: **OpenHands** — `projects/openhands.md`.
- Task 12: **SWE-agent / SWE-ReX / mini-swe-agent transition** — `projects/swe-agent-mini-swe-agent.md`.
- Task 13: **llama.cpp** — `projects/llama-cpp.md`.
- Task 14: **OpenAI Agents SDK** — `projects/openai-agents-sdk.md`.
- Task 15: **Model Context Protocol** — `projects/model-context-protocol.md`.
- Task 16: **Goose** — `projects/goose.md`.
- Task 17: **Ollama** — `projects/ollama.md`.
- Task 18: **Letta Code** — `projects/letta-code.md`.
- Task 19: **Gemini CLI** — `projects/gemini-cli.md`.

## Task 19 work completed
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, and `watchlist.md` before research.
- Began from finalized Task 18 checkpoint `4de1e731748820d0a07d77a2f7c86f74956b01e0`.
- Verified canonical current upstream `google-gemini/gemini-cli` and inspected revision `85aca163f6c73ac6ce380b5447359146b8adcae4` on 2026-09-06.
- Kept stable release `v0.58.0` distinct from inspected current main where current-version issue evidence required that distinction.
- Deep-researched current PolicyEngine behavior, including deterministic `ALLOW`, `DENY`, and `ASK_USER` outcomes; trust tiers; tool/MCP-server/subagent/mode/interaction matching; argument matching; headless behavior; safety checkers; and fail-closed checker errors.
- Recorded that unresolved non-interactive tool calls deny by default while YOLO intentionally widens unmatched authority; policy outcome remains different from realized OS/process authority.
- Deep-researched shell command safety/normalization and cross-platform classification.
- Verified open #29189 as a current Windows failure fixture: stable `v0.58.0` can classify `git diff --output=...` as read-only while allowing a write, and inspected current main still treats `status`, `log`, `diff`, `show`, and `branch` as safe by subcommand without full argument validation. Proposed PR #29184 remained open during Task 19.
- Derived the reusable rule that shell authorization must bind normalized command semantics, flags/redirection/config/hooks/aliases/nested interpreters where relevant rather than executable/subcommand labels alone.
- Deep-researched sandbox ownership and capability expansion through platform SandboxManager implementations.
- Verified explicit filesystem/network permission expansion and Linux Bubblewrap controls including protected governance paths, environment sanitization and ptrace restriction.
- Preserved the distinction `PolicyDecision != CapabilityGrant != RealizedSandbox != EffectSettlement`.
- Deep-researched environment/credential handling, including sensitive/runtime-altering environment sanitization and sanitized MCP subprocess environment construction.
- Retained ACL's stronger rule that worker/tool processes receive minimal explicit environments and provider/control-plane credentials remain outside worker authority.
- Recorded closed-stale #23136 only as bounded evidence about whole-process sandbox/provider-credential coupling, not a universal current exploit claim.
- Deep-researched provider/model architecture and routing/fallback.
- Verified current first-class content-generator/provider paths are Gemini / Code Assist / Vertex / Gateway oriented.
- Found no first-class Ollama, direct llama.cpp, vLLM, or generic OpenAI-compatible local-model provider in the main current content-generator surface; `GOOGLE_GEMINI_BASE_URL` remains Gemini/Google GenAI protocol semantics.
- Classified Gemini CLI as a useful Gemini/cloud harness reference rather than evidence of direct local-model portability for ACL's eventual 32K local benchmark.
- Deep-researched MCP client/server integration across stdio, SSE and Streamable HTTP plus filtering, trust/auth, prompts/resources and extension-provided MCP surfaces.
- Deep-researched executable extensions: extensions can contribute MCP servers, policy/checkers, context, commands, hooks, agents and skills; install consent exposes behavior-bearing configuration and a SHA-256 configuration signature.
- Derived that configuration hashing is useful approval identity but is not publisher/artifact provenance or proof executed code equals reviewed config.
- Deep-researched local subagents and remote A2A agents.
- Verified local subagents use isolated context/tool/prompt/resource registries, subagent-specific policy and recursion prevention.
- Verified omission of a local subagent tool list inherits parent tools; derived a stricter ACL default of no effect tools unless explicitly granted.
- Preserved the boundary that registry/context isolation is not process/user/filesystem/network/credential isolation.
- Deep-researched remote A2A authentication and retained credential resolution as a trusted broker responsibility rather than arbitrary project-defined command authority.
- Deep-researched ACP connection/session lifecycle.
- Verified authentication occurs before full config/MCP initialization, a useful ordering property.
- Verified current `loadSession()` initializes requested session configuration before resolving stored session state and launches history replay without awaiting it.
- Preserved open #28693/#28775 as current load-corruption fixtures consistent with that ordering and derived a read-before-create resume invariant: resolve/validate candidate state, acquire authoritative ownership and bind current authority before mutating active runtime state.
- Deep-researched `ChatRecordingService` append-oriented JSONL semantic state with metadata/message/tool/thought/set/rewind records and transactional repair behavior.
- Recorded that ENOSPC/durability failure can disable further recording while a live session continues; live progress and durable resumability are therefore separate states.
- Recorded open #29198 on stable `v0.58.0` as a current resume/retention failure fixture where resume followed by immediate exit can remove future resumability; Task 19 did not claim a complete root cause without a fresh runtime reproduction.
- Derived that required-durability loss must become an explicit ACL execution state rather than an invisible logging degradation.
- Deep-researched optional checkpointing with shadow Git project snapshots plus conversation/tool-call metadata before modifying file tools.
- Verified shadow Git isolates user/system Git config and restoration uses Git restore/clean behavior.
- Preserved checkpoint limits: `.gitignore` exclusions, processes, databases, network/API effects, credentials and other non-Git state remain outside the snapshot.
- Deep-researched auto-memory extraction with per-workspace state, atomic lock creation, PID/age stale detection, throttling, session versions and bounded batches.
- Preserved Task 18's stronger memory result: extracted memory and compacted context are not canonical truth/evidence; local PID/age locks are coordination rather than multi-host writer fencing.
- Deep-researched deterministic integration tests versus non-deterministic model behavioral evals.
- Recorded Gemini CLI's `USUALLY_PASSES` versus `ALWAYS_PASSES` reliability classes and repeated/nightly evidence as strong reference material for ACL's eventual benchmark-lab promotion semantics.
- Preserved separation of deterministic harness correctness, stochastic model reliability, end-to-end task success, runtime telemetry and verifier-owned acceptance evidence.
- Deep-researched OpenTelemetry observability and retained sensitive prompt/tool trace audience/redaction/retention boundaries.
- Deep-researched protected system configuration and extension security hardening, including current ownership/permission checks and consent around environment-changing extensions.
- Derived the invariant that high-trust policy/checker/verifier/hook artifacts must be structurally outside worker write authority and version/provenance checked.
- Wrote detailed source-backed findings, current/open failure fixtures, reusable mechanisms and explicit non-conclusions to `projects/gemini-cli.md`.
- Appended exactly 14 Task 19 records to the research catalog after the 153 Task 18 records; no earlier catalog record was deleted or rewritten.
- Preserved task boundary: no Graphiti research, cross-project winner selection, dependency/adoption decision, benchmark execution, architecture/governance redesign, or worker/model execution was begun.

## Highest-value Gemini CLI findings for later comparison
1. Deterministic tiered policy with explicit deny/ask/allow and fail-closed checker behavior is strong ACL authority reference material.
2. Argument-aware policy is necessary; executable/subcommand labels are not sufficient shell-effect identity.
3. #29189 is a concrete cross-platform command-semantics regression fixture because `git diff --output` can turn an apparently read-only subcommand into a write.
4. Policy decision, approval, capability grant, realized sandbox and effect settlement are distinct state/evidence domains.
5. Incremental filesystem/network sandbox permission expansion is preferable to globally disabling isolation when a worker needs one additional resource.
6. Configured sandbox mode is not proof of realized isolation; record backend and realized mount/read/write/network/process authority.
7. Protected system policy/config/checker roots are strong precedent for ACL verifier/policy artifacts living outside worker write authority.
8. Worker/tool processes should not inherit model-provider/control-plane credentials or the supervisor environment by default.
9. Gemini CLI's main provider surface is a cloud/Gemini harness reference, not a first-class Ollama/llama.cpp/vLLM local-runtime reference.
10. Executable extensions require approval over all behavior-bearing configuration; a config digest helps identity but does not replace signed provenance/artifact verification.
11. MCP server/tool origin and extension provenance belong in canonical capability identity.
12. Subagent context/tool-registry isolation is useful, but ACL should default child effect authority to none rather than inheriting all parent tools.
13. Local subagent/remote A2A identity does not itself establish OS/credential isolation or global task/effect authority.
14. ACP authentication-before-initialization is useful, but resume must be read-before-create and ownership-fenced before mutating the namespace being recovered.
15. #28693/#28775 provide current resume/load ordering fixtures.
16. Append-oriented semantic session history with explicit supersede/rewind semantics is useful durability reference material.
17. Live execution may outlive durable recording; durability failure must be an explicit lifecycle state rather than a logging-only event.
18. #29198 provides a current stable-release resume/retention fixture.
19. Shadow-Git checkpointing is a strong pre-modification workspace pattern but is not a complete continuation/effect checkpoint.
20. Auto-memory extraction requires provenance and authoritative-writer semantics; PID/age locks remain local coordination only.
21. Deterministic integration correctness and stochastic model behavioral reliability should be measured separately.
22. Repeated pass distributions such as `USUALLY_PASSES`/`ALWAYS_PASSES` are useful inspiration for model-role promotion but do not define ACL thresholds by themselves.
23. Runtime OpenTelemetry is operational evidence, not independent acceptance authority.
24. Gemini CLI does not replace ACL's outer scheduler, distributed writer fencing, external-effect ledger/reconciliation, credential broker, independent verifier, Vera epistemic-memory governance or exact local-runtime qualification.

## Queue status
- **Pydantic AI (#1): complete.**
- **Cline (#2): complete.**
- **LangGraph (#3): complete.**
- **promptfoo (#4): complete.**
- **Strands Harness SDK (#5): complete.**
- **Codex (#6): complete.**
- **OpenHands (#7): complete.**
- **SWE-agent / mini-swe-agent (#8): complete.**
- **llama.cpp (#9): complete.**
- **OpenAI Agents SDK (#10): complete.**
- **Model Context Protocol (#11): complete.**
- **Goose (#12): complete.**
- **Ollama (#13): complete.**
- **Letta Code (#14): complete.**
- **Gemini CLI (#15): complete.** Detailed evidence: `projects/gemini-cli.md`.
- **Graphiti (#16): next task only.** No Graphiti research was begun in Task 19.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **Graphiti** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant temporal/episodic/semantic memory architecture, provenance and contradiction handling, write/read authority, graph identity and multi-tenant boundaries, persistence/concurrency/recovery, model/provider/embedding dependencies, local-model compatibility where present, observability/evaluation, security/failure evidence, and reusable mechanisms. Save report/catalog/state/watchlist, make a research-only commit, and stop before Microsoft Agent Framework.

## Later tasks
1. Graphiti, then the remaining ranked active-project queue one task at a time.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after individual work is complete.

## Stop point

Task 19 ended after Gemini CLI's deterministic policy/approval model, shell-command semantics, sandbox capability expansion, environment/credential boundary, Gemini/provider architecture, MCP/extensions, local/remote subagents and A2A, ACP session loading, append-oriented durable history, shadow-Git checkpointing, auto-memory/context state, behavioral evaluation/telemetry and current recovery/security failures were researched. No Graphiti research, cross-project winner selection, dependency decision, benchmark execution, ACL/Vera architecture/governance change or worker/model execution was begun.
