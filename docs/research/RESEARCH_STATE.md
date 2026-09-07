# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 23 — LiteLLM deep research complete
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
- Task 20: **Graphiti** — `projects/graphiti.md`.
- Task 21: **Microsoft Agent Framework** — `projects/microsoft-agent-framework.md`.
- Task 22: **Google ADK** — `projects/google-adk.md`.
- Task 23: **LiteLLM** — `projects/litellm.md`.

## Task 23 work completed
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `watchlist.md`, and `sources.md` before beginning Task 23.
- Began from finalized Task 22 checkpoint `6d2ca64aadb96d8da6ff818f6ce0bb14f70759d3`.
- Confirmed Task 23 scope as LiteLLM only and preserved vLLM as Task 24 next-only.
- Verified canonical `BerriAI/litellm`, observed default branch `litellm_internal_staging`, pinned revision `168a0055a244acdcf97c330c52e085ab40b1424c`, and stable release `v1.100.0`.
- Verified non-enterprise source is MIT licensed and current release notes expose Cosign-signed Docker-image provenance.
- Deep-researched Python SDK versus Proxy/AI Gateway authority/deployment boundaries.
- Deep-researched provider-specific request/response transformation, supported-parameter mapping, native versus emulated structured output and `drop_params` downgrade behavior.
- Derived that common OpenAI-shaped APIs are translation contracts, not provider/model/backend semantic equivalence.
- Deep-researched LiteLLM local Ollama adapter paths and current source behavior.
- Verified current `ollama_chat` declares `tool_choice` while deliberately removing it because it can hang requests.
- Cross-checked open #35711 against pinned `ollama/` streaming source and verified non-streaming JSON tool-call reconstruction remains absent from the streaming iterator.
- Preserved `ollama/` versus `ollama_chat/`, streaming versus non-streaming, native versus emulated tool transport as separate capability identities.
- Deep-researched LiteLLM's `hosted_vllm` adapter boundary only; vLLM itself was not researched.
- Retained open #32281 as a LiteLLM MCP-to-OpenAI tool-schema compatibility fixture without attributing it to vLLM independently.
- Deep-researched structured-output emulation and retained open #35677 as a schema-envelope leakage fixture.
- Deep-researched Router deployment identity, load-balancing/retry/fallback/cooldown settings and distributed health state.
- Verified request-local fallback attempt identity prevents cyclic/re-walked deterministic failures.
- Verified provider-scoped file/batch/fine-tuning resource semantics can block inappropriate cross-provider/model-group fallback.
- Derived effect/resource-aware replay/fallback as a high-value ACL invariant.
- Verified Proxy can re-authorize router-configured fallback targets against the caller's key/team/project model access through `enforce_fallback_model_access`; current lookup failure fails closed when enforcement applies.
- Deep-researched current cooldown causality safeguards that prevent caller-scoped 404/tiny-timeout failures and caller metadata from poisoning shared deployment health.
- Verified dynamic client-side credential requests can carry effective deployment identity so one tenant's bad credentials do not cool a shared deployment for others.
- Deep-researched current `CooldownCache` / DualCache state and its Redis-versus-local TTL reconciliation.
- Cross-checked open #38927 against current Langfuse header-metadata mutation source and retained observability/retry-state contamination as an open current-source seam without claiming a fresh runtime reproduction.
- Deep-researched open #38142 and derived an ordered per-attempt routing evidence requirement; final success alone does not prove the initial/preferred provider path was healthy.
- Deep-researched open #33371 and kept provider error classification separate from ACL effect replay authorization.
- Deep-researched open #38610 as a v1.100.0-era stream-commit fixture: HTTP 200/message_start can become irreversible before a fallback failure is known.
- Deep-researched open #37140 as a non-streaming client-disconnect/upstream-cancellation fixture.
- Deep-researched Proxy authentication/model-access and preserved gateway key/team/project identity as distinct from ACL/Vera principal/task/effect identity.
- Deep-researched current endpoint/credential/nested-config/fallback-target hardening in `auth_utils.py`.
- Compared current source with reviewed historical 2026 SSRF/provider-credential, Host-header auth-route and MCP-auth advisories; retained them as fixed security regression classes rather than current-v1.100 vulnerabilities.
- Derived outbound destination plus credential selection as one authority decision and authoritative server-dispatch route identity as the auth input.
- Deep-researched observability/redaction boundaries and preserved logging/tracing as sensitive operator evidence rather than authoritative acceptance.
- Preserved mutable model capability/context/cost maps and caches as gateway metadata/performance state rather than measured 32K runtime truth.
- Wrote detailed evidence, current/fixed failure matrix, 40 candidate invariants, 18 regression fixtures, reuse candidates, primary sources and explicit non-conclusions to `projects/litellm.md`.
- Prepared exactly 20 Task 23 catalog records for append after the 215 Task 22 records.
- Preserved task boundary: no vLLM project research, dependency selection, local-model benchmark, gateway adoption or ACL/Vera implementation was begun.

## Highest-value LiteLLM findings for later comparison
1. LiteLLM SDK and Proxy are materially different authority/deployment profiles.
2. Provider normalization is adapter code; a common OpenAI wire shape does not establish semantic parity.
3. Required parameters silently dropped by `drop_params` cannot retain a verified capability label.
4. Native and tool-emulated structured output require separate qualification and final authoritative schema validation.
5. Local capability includes exact LiteLLM provider path and streaming mode; `ollama/` and `ollama_chat/` are not interchangeable.
6. Current pinned `ollama/` streaming source corroborates #35711's missing tool-call reconstruction path.
7. Current `ollama_chat` source demonstrates capability metadata may advertise a parameter the adapter deliberately strips.
8. Strict OpenAI-compatible backends can reveal malformed LiteLLM tool/schema translations hidden by lenient providers.
9. Router strategy/deployment list/retry/fallback/cooldown/cache state are benchmark identity fields.
10. Fallback attempt identity should be bounded and cycle-resistant.
11. Provider-scoped resources/effects can make cross-provider fallback invalid even when plain inference fallback is safe.
12. Reliability fallback must never widen caller authority; LiteLLM's fallback authorization hook is strong reference material.
13. Caller-attributable failures and dynamic credentials must not poison shared deployment health.
14. Distributed cooldown state is operational coordination, not task/effect checkpoint state.
15. Observability must not mutate canonical request/retry/authorization state; #38927 is a high-value fixture.
16. Final success does not preserve complete route history; ordered attempt evidence is needed (#38142).
17. Gateway/provider retryability is separate from ACL effect replay safety.
18. HTTP/stream commitment, semantic completion and durable success are different states (#38610).
19. Client disconnect is not upstream generation/resource settlement (#37140).
20. A credential-bearing gateway must jointly authorize outbound destination and credential selection.
21. Security validation must cover nested/normalized values and use the server's authoritative dispatch identity.
22. Exact security-patched LiteLLM revision/container/configuration is part of deployment qualification.
23. Gateway logs/traces are sensitive operational evidence, not independent verification.
24. Cache hits and gateway context/capability metadata must not be mistaken for fresh measured 32K model behavior.
25. LiteLLM remains beneath ACL-owned task/effect identity, idempotency/reconciliation, protected policy/verifier state and independent acceptance.

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
- **Gemini CLI (#15): complete.**
- **Graphiti (#16): complete.**
- **Microsoft Agent Framework (#17): complete.**
- **Google ADK (#18): complete.**
- **LiteLLM (#19): complete.** Detailed evidence: `projects/litellm.md`.
- **vLLM (#20): next task only.** No vLLM project research was begun in Task 23.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **vLLM** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant inference/runtime architecture, serving APIs, scheduler/concurrency/KV-cache/context behavior, structured output/tool calling, cancellation/timeouts, local hardware/quantization/backend compatibility, observability/metrics, distributed execution, security/current failures, reproducibility and reusable mechanisms. Save report/catalog/state/watchlist, make a research-only commit, and stop before OpenCode.

## Later tasks
1. vLLM, then the remaining ranked active-project queue one task at a time.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after individual work is complete.

## Stop point

Task 23 ended after LiteLLM's current identity/release, SDK-versus-Proxy boundary, provider/local adapter translation, structured-output/tool semantics, router/retry/fallback/resource identity, fallback authorization, cooldown/health state, routing evidence, streaming/cancellation, proxy network/credential security, observability and reproducibility were researched. No vLLM project research, cross-project winner selection, dependency decision, benchmark execution, ACL/Vera architecture/governance change or worker/model execution was begun.
