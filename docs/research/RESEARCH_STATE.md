# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 15 — Model Context Protocol deep research complete
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

## Task 15 work completed
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before research.
- Verified `research/agent-landscape` was at Task 14 checkpoint `1b7e36b2fb2ffbac389558e39c2538312f33049d` before Task 15 writes.
- Verified canonical MCP core repository `modelcontextprotocol/modelcontextprotocol`, public/active, and inspected core revision `e76e9c572c6f2bfcb730357101acc90f2f802e02` dated 2026-09-04.
- Verified current released protocol revision is `2026-07-28` and used that generation as authoritative for current semantics.
- Verified the 2026-07-28 revision intentionally changed MCP from a stateful/bidirectional protocol into a stateless request/response protocol.
- Verified modern MCP removed the `initialize`/`initialized` handshake and protocol-level `Mcp-Session-Id`; every request carries protocol version/capabilities and application state spanning calls needs explicit handles/IDs.
- Recorded the modern-vs-legacy protocol-era boundary: `2026-07-28+` per-request metadata versus `2025-11-25` and earlier initialization/session semantics; dual-era fallback is behavior-bearing compatibility state.
- Verified the host/client/server topology keeps cross-server security, user consent, model integration and context aggregation at the host while each MCP client talks to one server.
- Verified tool/resource/prompt trust distinctions: tools are model-controlled protocol primitives, resources application-driven, prompts user-selected but server-authored; none of these labels constitutes execution/governance authority.
- Verified tool names are only server-local, `serverInfo` is self-reported and explicitly not security identity, and tool annotations are untrusted unless the server is trusted.
- Derived canonical MCP tool identity as server/trust identity + protocol/profile + tool name + definition/schema digest rather than name-only dispatch.
- Verified current `x-mcp-header` can project primitive tool parameters into HTTP headers, making schema-provided routing metadata a gateway/policy surface that ACL must allowlist rather than trust automatically.
- Verified remote resources and resource links can create network-fetch/SSRF surfaces and remain lower-trust model context with provenance requirements.
- Verified MCP prompt/discovery natural-language guidance remains server-authored content and must not silently inherit ACL/Vera system/governance authority.
- Deep-researched Multi Round-Trip Requests (MRTR): server returns `input_required`, client retries with a new JSON-RPC ID, and opaque `requestState` is echoed by the client.
- Verified `requestState` must be treated attacker-controlled if it affects authorization/resource/business logic; integrity protection should bind principal, expiry, method and salient parameters, while true single-use still requires server-side state.
- Recorded open #2920 as an unresolved MRTR URL-mode waiting/cancel usability/lifecycle ambiguity rather than a settled protocol failure.
- Verified request cancellation is cooperative/racy; progress can extend idle deadlines but a hard maximum timeout should remain; progress is advisory rather than success/effect evidence.
- Verified `subscriptions/listen` is a transport observation stream and reconnect requires resubscription; server does not retain subscription continuity as durable application state.
- Recorded same-day open issue #3348 as current spec-consistency evidence: cancellation and subscription documents disagree on server-initiated subscription teardown semantics while official SDK behavior reportedly follows the subscription-result path.
- Verified Streamable HTTP uses new per-request POSTs, current headers (`MCP-Protocol-Version`, `Mcp-Method`, `Mcp-Name`), Origin validation/DNS-rebinding guidance, and no modern `Last-Event-ID` resumability.
- Derived that a broken-stream retry is a new MCP request and cannot automatically authorize replay of an uncertain external effect.
- Verified current Tasks extension lives in `modelcontextprotocol/ext-tasks`; inspected revision `9263312d11a682ac83f83fe84794d4627efd22f5` dated 2026-09-04.
- Verified Tasks extension creates durable remote-operation handles only after the task is durably findable; current supported task-augmented method is `tools/call`.
- Verified task states `working`, `input_required`, `completed`, `failed`, `cancelled`; terminal task states are immutable.
- Verified task mid-flight input keys must remain unique for the task lifetime and clients should deduplicate repeated requests across polls.
- Verified `tasks/cancel` is an intent acknowledgement, eventually consistent and cooperative; it does not prove work stopped and a task may still finish non-cancelled.
- Verified contributor response on ext-tasks #11 explicitly confirms that retention/visibility lifecycle is intentionally distinct from termination of underlying computation.
- Verified task IDs may serve as bearer handles but current Tasks security also requires authentication/authorization checks on each task-related request and removes `tasks/list` to reduce cross-caller enumeration.
- Recorded open ext-tasks #20 plus contributor response as a current protocol-wide gap/ambiguity in representing authorization denials consistently outside HTTP OAuth-specific error handling.
- Verified elicitation separates form mode from URL mode; passwords/API keys/access tokens/payment credentials must not be requested through form mode and sensitive interaction moves out of band.
- Derived Vera pattern: keep credential collection/auth/payment outside model-visible content, expose requesting server/domain clearly, and return only bounded completion/grant evidence.
- Verified Roots are deprecated and were informational guidance rather than access control even before deprecation; ACL must not use roots as filesystem sandbox policy.
- Verified Sampling is deprecated and current guidance points new implementations to direct model-provider APIs; MCP should not become ACL's model-runtime owner.
- Verified HTTP authorization uses OAuth resource-server semantics, resource/audience binding, PKCE, issuer validation, protected-resource/authorization-server discovery, least-privilege scope challenges, and CIMD preference over deprecated DCR.
- Verified token passthrough is forbidden: inbound MCP access tokens are not to be forwarded to downstream APIs; downstream services need separate audience-correct tokens.
- Derived strong Vera credential-broker implication: service-specific grant/reference -> MCP service access -> separate downstream token when required.
- Verified OAuth/discovery URL fetching is itself an SSRF surface and current guidance calls out localhost/private/cloud-metadata/DNS-rebinding/redirect risks.
- Preserved stronger ACL local rule than generic stdio guidance: do not inherit supervisor `os.environ`; construct minimal explicit child environments.
- Verified JSON Schema 2020-12 current semantics and external `$ref` network dereference must not happen automatically; opt-in dereference needs private/loopback blocking, limits and fail-closed unresolved references.
- Verified cache TTL is freshness hint rather than state-version guarantee; `cacheScope` is separate from access control, public cache can cross authorization contexts, and MRTR retries are not cacheable.
- Recorded open #3207 and #3213 only as current warning/evaluation cases: server-controlled `cacheScope` / server discovery instructions can create provenance/prompt-injection concerns if an intermediary/client elevates them; no maintainer resolution was found in inspected discussion.
- Verified `serverInfo` is self-reported/not security identity and current discovery `instructions` is optional server-authored natural-language LLM guidance.
- Verified extensions are namespaced, disabled by default, explicitly negotiated, can evolve independently, and SDK support for extensions is not required by core conformance.
- Verified Tier 1 TypeScript, Python, Go and C# SDKs were stated by lead maintainers to support `2026-07-28` at GA; extension support still requires separate qualification.
- Recorded candidate MCP capability profile fields: server trust identity, endpoint/transport, protocol era/version, client adapter/SDK revision, auth mode, extensions/settings, tool/resource/prompt definition digests, Tasks/MRTR/cache semantics and verified fixture set.
- Wrote detailed source-backed research and regression-fixture ideas to `projects/model-context-protocol.md`.
- Preserved task boundary: no Goose research, cross-project winner selection, dependency/fork decision, ACL/Vera governance redesign or worker/model execution was begun.

## Highest-value MCP findings for later comparison
1. Modern MCP deliberately removes implicit protocol sessions; transport/process identity is not application task/run/effect identity.
2. Protocol era/version and extension profile are behavior-bearing compatibility state and must be recorded.
3. MCP host topology fits ACL/Vera only if host-owned policy/credential/task/evidence authority remains above remote servers.
4. Tool identity needs authoritative server origin + definition/schema identity; remote names/annotations are insufficient authority.
5. Remote prompts, resources and discovery instructions are untrusted content even when selected by the user or syntactically valid.
6. MRTR continuation state that affects authority needs integrity binding to principal/operation/parameters/expiry, while replay/single-use remains separate.
7. Broken-stream/request retry is a new request, not proof an uncertain effect is safe to repeat.
8. Request/task cancellation is cooperative intent, not process/effect settlement.
9. MCP Tasks are valuable durable remote-job handles but are not ACL continuation checkpoints/effect ledgers.
10. Task handle retention/TTL/disappearance is distinct from termination of underlying computation.
11. Lost task IDs cannot be rediscovered through `tasks/list`; ACL must durably retain remote handles until settlement/retirement.
12. Sensitive elicitation should stay out of model-visible form data and use explicit out-of-band user flows.
13. Roots are not access control and Sampling is not a future-proof model-runtime abstraction.
14. HTTP OAuth/resource indicators support audience-bound service authority; token passthrough is explicitly forbidden.
15. Remote URL/schema/authorization discovery requires SSRF/network policy.
16. Cache freshness/scope is not provenance, authorization or immutable capability state.
17. `serverInfo` is explicitly not security identity; server-authored discovery instructions cannot become protected prompt authority.
18. Extension/core/SDK support must be qualified separately; “supports MCP” is too coarse.
19. Current open specification/task issues remain high-value interoperability fixtures independent of model quality.
20. MCP is strongest as an interoperability layer below ACL/Vera governance, not as scheduler, sandbox, verifier, memory, credential vault or exactly-once effect manager.

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
- **Model Context Protocol (#11): complete.** Detailed evidence: `projects/model-context-protocol.md`.
- **Goose (#12): next task only.** No Goose deep research was begun in Task 15.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **Goose** only.

Do not begin until separately instructed. When begun, inspect the current canonical `aaif-goose/goose` project, its GDK/MCP/provider/runtime architecture, local-model compatibility, tool/permission/sandbox boundaries, sessions/recipes/extensions, process/workspace lifecycle, telemetry/evaluation, current failure surfaces and governance/AAIF transition. Extract reusable mechanisms/invariants and concrete ACL/Vera lessons, save research/catalog/state/watchlist, commit research-only changes, and **stop before Ollama**.

## Later tasks
1. Goose, then the remaining ranked active-project queue one task at a time.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after individual work is complete.

## Stop point

Task 15 ended after current MCP architecture/versioning, primitives, MRTR, cancellation/progress/subscriptions, Streamable HTTP, Tasks, elicitation, deprecated Roots/Sampling, authorization/security, schema/network boundaries, caching/provenance and current interoperability/failure surfaces were researched. No Goose/Ollama research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
