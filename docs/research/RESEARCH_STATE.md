# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 16 — Goose deep research complete
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

## Task 16 work completed
- Re-read the governing research state/process context and began from finalized Task 15 checkpoint `42f7d5db051d0701f089eb2c2785defa01ea303f`.
- Verified canonical current project identity at `aaif-goose/goose`, active/non-archived, and inspected upstream revision `5e90925962f05acf8e255032de44d16c4a7768a2` dated 2026-09-05.
- Verified latest release observed was `v1.49.0` from 2026-09-03.
- Verified the Block → AAIF continuity boundary: Goose moved from `block/goose` to `aaif-goose/goose`; current governance places Goose under AAIF/LF Projects while retaining open technical-maintainer governance.
- Recorded GDK as two separable integration surfaces: an alpha in-process SDK/provider layer and ACP exposing the full Goose runtime behind stdio or HTTP/WebSocket.
- Verified the `goose-agent` state machine re-derives behavior from persisted conversation state, reloads sessions between passes, and stores durable operation markers in messages instead of relying on hidden loop state.
- Derived the reusable ACL pattern: durable semantic state -> reload -> derive next legal transition -> persist effects; ephemeral loop variables remain non-authoritative.
- Preserved the boundary that conversation-derived state is not distributed fencing, workspace checkpointing, current authorization, exactly-once effect evidence or independent verification.
- Verified the provider contract is intentionally small and current provider implementations include cloud, OpenAI-compatible, Ollama and built-in on-device local inference paths.
- Verified `goose-local-inference` runs GGUF through llama.cpp (`llama-cpp-2`) and optionally MLX, with CUDA/Vulkan/MLX feature paths, model lifecycle, templates and native/emulated tool parsing.
- Derived that Goose local capability is an exact Goose revision/build + provider + backend + model artifact/template/parser/tool mode + configuration property, not merely `provider=local` or model name.
- Verified MCP extensions are runtime-discovered and namespaced by extension, with duplicate public tool names skipped rather than silently dispatched to multiple providers.
- Verified extension configuration/secret changes can trigger extension restart and resolved secret-bearing configuration is held in memory rather than durably expanded.
- Verified current local stdio extension launch does not clear ambient environment before applying configured variables; retained ACL's stronger rule to construct minimal explicit child environments instead of inheriting supervisor `os.environ`.
- Verified Goose permissions are layered: explicit per-tool rules, Smart Approval/read-only hints or classifier decisions, security inspectors, and Goose execution mode interact rather than one boolean gate.
- Verified positive LLM Smart Approval classifications are not persisted name-wide; negative/unsafe classifications can fall back to AskBefore.
- Preserved the trust boundary that MCP/tool read-only annotations and classifier output are advisory inputs, not authoritative least-privilege policy.
- Verified Autonomous mode is the documented default and permits tools without approval; Goose permission controls are therefore not equivalent to an OS sandbox.
- Verified current upstream removed its prior macOS OS sandbox and documents that the Goose server/tool process runs with the user's permissions.
- Derived the ACL requirement that approval UI, command policy and actual process/filesystem/network/credential isolation remain separate controls.
- Verified session persistence uses a versioned SQLite schema and carries conversation plus working directory, enabled extensions/config, recipe/input state, provider/model/mode and usage/cost metadata.
- Verified ACP session load replays persisted history, restores provider session state, resends pending tool confirmations and can resume an interrupted state-machine turn.
- Verified current ACP uses a shared per-session active-run registry/run ID to prevent concurrent ACP clients from interleaving two active prompt runs into one durable session.
- Recorded that this is strong in-process single-writer reference material but not distributed durable lease/generation fencing.
- Verified agent creation itself is serialized per session to avoid duplicate agent/MCP initialization races.
- Verified recipes are executable configuration: they may carry provider/model/settings, extensions, parameters, retry checks and on-failure shell commands.
- Verified recipe retry uses deterministic shell success checks, bounded retries/timeouts and resets conversation state to the initial messages before another attempt.
- Preserved the boundary that resetting conversation is not workspace/effect rollback and retry does not authorize repeating an uncertain external effect.
- Verified Desktop recipe acceptance is content-hash based: accepted recipes are SHA-256 hashed and a changed recipe requires a new acceptance hash.
- Recorded open issue #10325 as current executable-recipe/trust-ordering evidence, including a v1.45 Desktop reproduction where a stdio recipe extension executed before the user clicked `Trust and Execute`; current main still loads session extensions during agent construction while the UI acceptance check occurs after session load.
- Verified current `Recipe::check_for_security_warnings()` still checks hidden Unicode tags only in natural-language recipe fields, not executable extension/retry fields; classified this as an open trust-surface fixture, not a universal exploit claim.
- Verified subagents can be sequential/parallel, inherit parent extensions by default unless explicitly narrowed, and are blocked from spawning nested subagents, extension management and schedule management.
- Recorded that Goose documentation calls subagents process-isolated conceptually, but internal subagents are ordinary Goose instances within the runtime and therefore should not be treated as OS isolation.
- Derived child-authority rule: inherited extensions are an authority ceiling only when the outer runtime also enforces filesystem/process/network/credential ceilings; natural-language narrowing is not sufficient.
- Verified Code Mode exposes three meta-tools and discovers/calls broader MCP tools programmatically on demand, reducing tool-schema context pressure and allowing batched/chained tool execution.
- Recorded Code Mode's text-only tool-result limitation and classified the generated code runtime as coordination machinery, not a replacement for effect authorization.
- Verified current Harbor evaluation tooling compares exact Goose binaries/builds, models and extension sets against other harnesses on terminal-bench-style tasks and records pass/fail/error/timeout, turns, compute, tokens and cost.
- Recorded current project-owned Harbor snapshot evidence that changing harness/tool mode with the same model materially changes success rate; kept those results as project benchmark evidence rather than universal model rankings.
- Derived ACL benchmark rule: benchmark manifest must include harness/runtime revision, extension/tool mode and exact model/provider configuration; model name alone is not a valid comparison identity.
- Verified Goose exposes opt-in PostHog product telemetry and optional OpenTelemetry/OTLP traces, logs and metrics; current PostHog path is explicit opt-in and only session-start emission is currently active in inspected source.
- Preserved telemetry/evidence separation: operational OTel, product analytics, raw model/tool data and independent verifier evidence have different authority, sensitivity and retention requirements.
- Recorded open #11500 as current Streamable-HTTP MCP SSRF/header-forwarding evidence. The current authenticated client still builds `reqwest::Client` with default headers and no explicit redirect policy; the assigned maintainer favored disabling redirects and testing authenticated/unauthenticated 3xx handling.
- Recorded open #11399 as current deterministic shell-policy gap evidence: current permissions are tool-wide, while maintainers are discussing argument-level `deny > ask > allow` rules outside Smart Approval and how to protect policy configuration from agent edits.
- Preserved issue-scope discipline: #10325, #11500 and #11399 are current open failure/design surfaces with concrete evidence, not proof every Goose deployment/version is exploitable or unsafe.
- Wrote detailed primary-source research, reusable mechanisms, failure surfaces, candidate ACL/Vera invariants, regression-fixture ideas and explicit non-conclusions to `projects/goose.md`.
- Preserved the task boundary: no separate Ollama deep research, cross-project winner selection, dependency/fork decision, ACL/Vera governance redesign or worker/model execution was begun.

## Highest-value Goose findings for later comparison
1. Conversation-derived state-machine behavior is strong reference material for restart-safe agent-loop semantics.
2. ACP enables a clean client/runtime boundary appropriate for remote Vera clients, while transport/session identity must stay separate from ACL task/effect identity.
3. A small provider contract plus built-in local inference offers useful reuse options below the full Goose product.
4. Local capability must be qualified as an exact Goose/provider/backend/model/template/parser/tool-mode/configuration tuple.
5. MCP extension namespacing/discovery is useful, but remote annotations and extension metadata must not become authority.
6. Secret/config restart handling is useful, but ambient stdio child-environment inheritance is weaker than ACL's required explicit environment projection.
7. Goose permission modes and Smart Approval are workflow/policy layers, not OS isolation; Autonomous mode defaults to broad tool execution.
8. Positive Smart Approval classifications not becoming persistent name-wide grants is a useful hardening pattern.
9. Current Goose provides no general OS sandbox; ACL must retain separate worker process/filesystem/network/credential containment.
10. SQLite session persistence plus ACP pending-confirmation replay is meaningful durable-session reference material.
11. Per-session active-run and creation locks are useful single-writer/race-control patterns, but distributed persistence still needs generation/lease/CAS fencing.
12. Recipe hashes are useful exact-change acceptance identity; recipe configuration itself must be treated as executable code/authority.
13. Recipe retry success checks are useful deterministic validation mechanics, but conversation reset is not effect/workspace rollback.
14. Subagents provide bounded delegation/extension subsets and useful anti-recursion/control-plane restrictions, but inherited tools do not imply OS isolation.
15. Code Mode is a strong model-context/tool-scaling pattern: keep the model-facing meta-interface small and discover capabilities on demand.
16. Harbor demonstrates that harness/tool interface is a first-class benchmark variable, not noise around a model score.
17. OTel support is useful for ACL observability vocabulary, while runtime telemetry remains distinct from independent acceptance evidence.
18. Open recipe trust-ordering, HTTP redirect/SSRF and shell argument-policy gaps are high-value ACL regression fixtures.
19. Goose's Block→AAIF move is continuity, not abandonment; foundation governance improves continuity signal but does not replace version/dependency qualification.
20. Goose is strongest as a mechanism/reference layer under ACL/Vera-owned authority, sandbox/process custody, credential governance, effect ledger and verifier state rather than as an unchanged whole-system replacement.

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
- **Goose (#12): complete.** Detailed evidence: `projects/goose.md`.
- **Ollama (#13): next task only.** No separate Ollama deep research was begun in Task 16.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **Ollama** only.

Do not begin until separately instructed. When begun, inspect the canonical `ollama/ollama` project, exact model/runtime/API behavior, llama.cpp relationship and divergences, context/KV/memory/resource management, tool/function/structured-output behavior, model manifests/templates, concurrency/scheduling, local hardware/backend behavior, process/service lifecycle, security/network boundaries, reproducibility/evaluation and current failure surfaces. Extract reusable mechanisms/invariants and concrete ACL/Vera lessons, save research/catalog/state/watchlist, commit research-only changes, and **stop before Letta Code**.

## Later tasks
1. Ollama, then the remaining ranked active-project queue one task at a time.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after individual work is complete.

## Stop point

Task 16 ended after current Goose GDK/ACP architecture, provider/local-inference paths, MCP extensions, permissions/sandbox boundaries, session/recovery/concurrency, recipes/retries, subagents, Code Mode, process/environment behavior, telemetry/evaluation, current security/failure surfaces and AAIF governance continuity were researched. No separate Ollama research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
