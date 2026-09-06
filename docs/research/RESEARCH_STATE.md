# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 14 — OpenAI Agents SDK deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Completed
- Research workspace initialized and evidence ladder established.
- Tasks 1–4 mapped recurring sources, active projects/people, research priority, and failed/abandoned/heavily redesigned attempts.
- Task 5 deep-researched **Pydantic AI** and the directly relevant official Pydantic AI Harness surfaces.
- Task 6 deep-researched **Cline** and its coding-agent architecture, authority, checkpoints, local-runtime/context and telemetry failure surfaces.
- Task 7 deep-researched **LangGraph** and its state/checkpoint, replay, interrupt, durability and retention failure surfaces.
- Task 8 deep-researched **promptfoo** as an independent evaluation/red-team/evidence layer.
- Task 9 deep-researched **Strands Harness SDK** across lifecycle, authorization, sandbox, persistence, interrupt, local-model and evaluation boundaries.
- Task 10 deep-researched **Codex** across sandbox/approval authority, child inheritance, Guardian authorization provenance, worktrees, thread/fork/resume state, local providers, process-tree cancellation and telemetry/evaluation boundaries.
- Task 11 deep-researched **OpenHands** across runtime/server boundaries, generation-fenced conversation ownership, crash recovery, concurrency/cancellation, workspaces, credentials, local providers and observability.
- Task 12 deep-researched the **SWE-agent / SWE-ReX / mini-swe-agent transition** and the deliberate move toward a smaller model-facing loop plus explicit outer execution/runtime responsibilities.
- Task 13 deep-researched **llama.cpp** across local-runtime/tool-protocol/template/parser/constraint/backend/KV/cache/concurrency and reproducibility boundaries.
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before Task 14.
- Deep-researched **OpenAI Agents SDK** as ranked project #10, using the ACL/Vera end goal to control scope.
- Verified canonical current project identity at `openai/openai-agents-python`, MIT license, active/non-archived status and inspected upstream revision `1d471a4775bf2f40179f411824da383deb4c3fca` from 2026-09-05.
- Verified latest published release observed was `v0.22.0` from 2026-08-19 and current `main` remains materially ahead of that release with continuing lifecycle/sandbox/state hardening.
- Used `openai/swarm` only to verify the predecessor boundary: upstream labels Swarm experimental/educational, says it was replaced by Agents SDK, and describes the successor as the production-ready evolution; no separate Swarm research was begun.
- Verified current Runner retains a small model-facing loop while `RunConfig`, sessions, approvals, guardrails, tracing, provider policy, sandbox/runtime and `RunState` own deterministic operational concerns outside prompt prose.
- Verified local function-tool execution concurrency is a separate control from provider/model `parallel_tool_calls`, preserving protocol concurrency versus real-effect concurrency as distinct contracts.
- Recorded that unnamespaced tool/handoff name collisions default to warning/current dispatch winner while `error` is available; derived a stricter ACL production invariant that authority-bearing identity collisions should fail before model execution.
- Verified `RunState` is explicitly a serializable durable pause/resume snapshot and currently carries schema version `1.17` with a semantic version history covering approval identity, trace reattachment, request IDs, tool origin, programmatic tool calling, hosted-MCP scoping, sanitized mount authority, trusted rebind metadata, Docker network isolation, pending input and pending resumed-session writes.
- Verified unsupported future RunState schema versions fail rather than being guessed forward; derived an ACL checkpoint-version compatibility gate.
- Verified `RunState` serialization/deserialization is treated as a trust boundary and includes defensive handling around JSON-compatible payloads and unsafe/cyclic/ambiguous values.
- Verified human approval is tied to explicit interruptions/call identity and survives serialization/resume rather than being a UI-only boolean.
- Verified sticky hosted-MCP approval is scoped by `(server_label, tool name)` so same-name tools on different origins do not share broad approval automatically.
- Verified malformed/uninspectable approval arguments fail closed to manual approval rather than invoking a policy callback with guessed data.
- Verified pending approvals can be resolved independently; approval state is item-addressed rather than one run-wide yes/no flag.
- Recorded documentation guidance to store an agent-definition/SDK version marker beside parked approvals; strengthened the candidate ACL invariant that approvals bind to task/objective/tool/policy definition versions.
- Verified serialized RunState may contain sensitive application context, approvals, tool input, nested resumptions, trace metadata and server continuation settings; optional tracing credentials can be included explicitly. Classified parked RunState as sensitive executable state.
- Verified agent-level input guardrails only cover the first agent and output guardrails only the final agent; function-tool guardrails cover only ordinary FunctionTool paths rather than all handoffs/hosted/built-in execution tools.
- Verified default parallel input-guardrail mode can allow model/tool execution before a tripwire completes; blocking mode is required when the property is that no effect may begin before validation.
- Verified function-tool preconditions can optionally run before approval and are still rerun immediately after approval before execution, providing a useful time-of-check/time-of-use revalidation pattern.
- Verified output/tool-output guardrails can sanitize/reject durable/model-visible results but cannot undo effects that already executed.
- Verified handoff `is_enabled` is evaluated before model-generated handoff arguments exist and therefore cannot authorize argument-level delegation scope; authorization based on parsed handoff data must run at `on_handoff` before side effects. Function-tool guardrails do not automatically cover the handoff itself.
- Verified local/runtime tool schemas and Python FunctionTools can execute application-owned code; approval/guardrail/schema machinery does not turn arbitrary local functions into an OS sandbox.
- Verified Programmatic Tool Calling keeps generated orchestration inside a restricted hosted V8 environment while actual allowed child tools continue through normal Runner approval/guardrail/session/RunState machinery; recorded this as a useful separation between generated coordination and effect authority.
- Verified Programmatic Tool Calling also tightens model-request replay policy: provider-managed/pre-event retries are disabled and Runner retry requires explicit replay-safe provider advice.
- Verified Sandbox Agents are beta and separate outer-runner responsibilities (approval/tracing/handoff/resume state) from sandbox-session responsibilities (commands/files/environment isolation).
- Verified a Manifest describes fresh workspace intent but is not automatically authoritative live state when an existing sandbox/session/snapshot is reused or resumed.
- Verified default SandboxAgent capabilities include Filesystem, Shell and Compaction, so a default sandbox action surface is broad and not synonymous with least privilege.
- Verified Unix-local, Docker and hosted sandbox clients have different isolation properties; Docker supports explicit `network_mode="none"` and persists/reapplies that state when replacement containers resume a session.
- Verified mount entries default read-only but storage exposure, network, user/resources and credential delivery remain separate authority-bearing configuration.
- Verified current mount-security code explicitly treats some identifiers/configuration as **authority, not merely secrets**, removes opaque authority-bearing third-party mount config from durable state, and uses closed trusted execution-boundary classification rather than trusting arbitrary subclasses/config.
- Verified in-container credential/broad-authority exposure requires explicit current application acknowledgement, that acknowledgement does not confine credential use to a mount path, and acknowledgement is runtime-only rather than serialized.
- Verified persisted sandbox state can contain sanitized/redacted mount authority metadata but `rebind_persisted_mount_authority` requires an exact current trusted manifest; compatibility tests fail when that trusted manifest is absent and verify current secret values are not serialized.
- Derived a high-value Vera/ACL invariant: persist sanitized resource/capability identity and rebind live credentials/network/mount authority from current trusted policy after resume instead of allowing stale snapshots to reactivate prior authority.
- Verified Sessions own client-side conversation history and cannot be combined in one run with overlapping run-level `conversation_id` / `previous_response_id` continuation owners.
- Verified OpenAIResponsesCompactionSession performs clear/rewrite state mutation with recovery attempts; docs explicitly warn a concurrent mutation can complete while remote compaction is in flight and then be overwritten by the later replacement. Derived one-writer/generation fencing requirements for context compaction.
- Verified runner-managed model retry records normalized provider errors and provider advice including `response_started` and `replay_safety`.
- Verified an ordinary `RetryDecision(retry=True)` cannot bypass unsafe-replay protection; repeating a request the provider marks replay-unsafe requires separate explicit `approve_unsafe_replay` authority.
- Verified retry policy callbacks are runtime-only and excluded from serialized retry settings; derived the invariant that restored state rebind executable policy from current trusted code rather than serializing callbacks.
- Verified model/provider portability through direct Model/ModelProvider implementations, custom OpenAI-compatible clients, MultiProvider, Any-LLM and optional LiteLLM, while docs explicitly warn exact provider paths must be tested for tool/structured-output/usage/Responses behavior.
- Verified strict feature validation can turn unsupported feature warnings into errors and Responses-only tool features are rejected on incompatible model paths; retained fail-closed capability qualification for ACL.
- Verified Responses WebSocket reuse is transport/session continuity with one-response-at-a-time and 60-minute connection limits; stateless/ZDR chains may require context rebuild after reconnect. Kept transport state separate from durable task state.
- Verified a streaming run remains incomplete until `stream_events()` drains because session persistence, approval bookkeeping or compaction can continue after the final visible token.
- Verified immediate cancellation and `cancel(mode="after_turn")` are distinct semantics; after-turn cancellation creates a resumable boundary, reinforcing separate "abort now" and "stop at settled turn" controls.
- Recorded open #4805 as reproducible provider-producer cancellation evidence: a cancelled voice transcription producer can leave a consumer blocked forever because no terminal event reaches its queue.
- Verified tracing is comprehensive and enabled by default, but model/tool input/output capture is sensitive by default (`trace_include_sensitive_data=True`); retained explicit evidence audience/redaction/retention policy for ACL/Vera.
- Verified default trace export is buffered/background and `flush_traces()` is available when export settlement must be guaranteed at end of work; trace generation and trace-delivery settlement are separate states.
- Preserved the boundary that comprehensive runtime tracing is evidence, not an independent verifier-owned definition of pass/fail.
- Recorded open #4827 as deterministic approval-resume/session corruption evidence: one path can persist a tool result without its matching deferred function call, poisoning later session use. Derived atomic parent-action/result relationship as a durable-state invariant.
- Recorded open #4839 as evidence that client-managed plain transcript replay can lose program/caller parent identity that the RunState resume path already preserves. Derived `resume_checkpoint != replay_transcript` as a first-class API/authority distinction.
- Recorded open #4889 as sandbox filesystem-identity evidence: case-only `move_to` can delete the newly written file on a case-folding filesystem while reporting an update/move. Derived execution-time filesystem identity and postcondition verification requirements.
- Recorded open #4852 as cross-platform restore evidence: symlink creation failure on ordinary Windows can occur after other archive members were already extracted, leaving partial mutation. Derived staging/rollback or explicit partial-restore state requirements.
- Preserved current-issue boundaries: reports demonstrate their documented configurations/current versions, not universal behavior for all providers/platforms/future releases.
- Recorded detailed primary sources, current failure boundaries, candidate invariants, future ACL regression fixtures and explicit non-conclusions in `projects/openai-agents-sdk.md`.
- Preserved the decision boundary: Task 14 does **not** decide whether ACL should adopt/fork/wrap OpenAI Agents SDK, select a cross-project winner, redesign ACL/Vera governance, or begin Model Context Protocol research.

## Highest-value OpenAI Agents SDK findings for later comparison

1. A durable execution checkpoint needs a versioned semantic contract, not just valid serialization.
2. `RunState` is materially stronger than transcript replay because it carries execution/caller/approval/sandbox/resume identity; the two representations must not be treated as equivalent authority.
3. Unsupported future checkpoint semantics should fail closed.
4. Parked execution state is sensitive executable state; application context and optional trace credentials make storage/transmission policy explicit.
5. Approval is stable call/scope/origin state, not a UI boolean.
6. Sticky approval must be scoped by canonical tool origin and invalidated when task/tool/policy semantics change.
7. Malformed/uninspectable proposed parameters must fail closed rather than receive guessed policy approval.
8. Revalidate mutable safety/policy preconditions immediately before the irreversible effect even if they were checked before human approval.
9. Parallel guardrails are not prevention boundaries when model/tool work may begin before the tripwire settles.
10. Post-effect output guardrails cannot undo effects.
11. Guardrail coverage is tool-surface-specific; handoffs, hosted tools and built-in execution tools need separately defined authorization paths.
12. Handoff availability and handoff argument authorization are separate; model-generated delegation scope remains untrusted until application authorization.
13. For authority-bearing capability identity collisions, fail before model execution rather than warn-and-select a winner.
14. Generated orchestration/program code can remain separate from effect authority; allowed child tools still need canonical identity, approval and effect state.
15. Sandbox/workspace continuation state and live credential/network/mount authority are separate domains.
16. Persist sanitized resource identity, then rebind live authority from current trusted policy/manifest after resume; do not serialize reusable authority acknowledgements.
17. "Sandbox" or "Docker" is not a permission profile; role-specific capabilities, network, mounts, user/resources and credentials remain explicit.
18. Conversation sessions, provider continuation IDs, RunState, sandbox state, workspace state and external-effect evidence require separate owners/identities.
19. Context compaction is a concurrent clear/rewrite state mutation; stale remote compaction results must not overwrite newer state.
20. `retry` is not permission to replay a possibly already-executed request. Unsafe replay needs an independent decision/evidence record.
21. Runtime policy callbacks/clients should be reconstituted from current trusted code rather than treated as durable serializable state.
22. Last visible token is not terminal state; session/approval/compaction/trace/effect settlement may remain.
23. Producer cancellation must terminate or wake every owned consumer; cancellation alone is not lifecycle settlement.
24. Durable action→result relationships must remain atomic; a persisted result without its required parent action is corrupt state.
25. Filesystem lexical path equality is not sufficient object identity across case-folding/symlink/platform boundaries; mutation success requires postconditions.
26. Restore/import operations that partially mutate before failure need transactional staging/rollback or an explicit partial/unsettled state.
27. Traces are sensitive operational evidence, not independent acceptance authority; evidence export itself may need a settlement gate.
28. Exact model/provider/adapter/transport feature behavior must be qualified; OpenAI-compatible and third-party adapters do not imply Responses/tool parity.
29. The SDK is strongest for versioned run-state, approvals, replay-safety and sandbox-authority-rebind patterns; it does not replace ACL's outer project scheduler, effect ledger, protected verifier, distributed state fencing, role authority, process custody or Vera memory governance.
30. Current lifecycle bugs are high-value evidence because they expose cross-plane identity/state failures below model quality.

## Queue status

- **Pydantic AI (#1): complete.** Detailed evidence: `projects/pydantic-ai.md`.
- **Cline (#2): complete.** Detailed evidence: `projects/cline.md`.
- **LangGraph (#3): complete.** Detailed evidence: `projects/langgraph.md`.
- **promptfoo (#4): complete.** Detailed evidence: `projects/promptfoo.md`.
- **Strands Harness SDK (#5): complete.** Detailed evidence: `projects/strands-harness-sdk.md`.
- **Codex (#6): complete.** Detailed evidence: `projects/codex.md`.
- **OpenHands (#7): complete.** Detailed evidence: `projects/openhands.md`.
- **SWE-agent / mini-swe-agent (#8): complete.** Detailed evidence: `projects/swe-agent-mini-swe-agent.md`.
- **llama.cpp (#9): complete.** Detailed evidence: `projects/llama-cpp.md`.
- **OpenAI Agents SDK (#10): complete.** Detailed evidence: `projects/openai-agents-sdk.md`.
- **Model Context Protocol (#11): next task only.** No MCP project deep research was begun in Task 14.
- Remaining ranked queue stays unchanged until its own separately authorized task or later evidence justifies an explicit update.

## Next task

Deep-research **Model Context Protocol** only.

Do not begin this task until separately instructed. For the next task, deep-research the current MCP specification and `modelcontextprotocol/modelcontextprotocol` as ranked project/source #11 with the same end-goal discipline. Cover protocol lifecycle and capability negotiation; tool/resource/prompt boundaries; Tasks/long-running operations; cancellation/progress/error semantics; server/client trust and authorization; roots/filesystem/network implications; session/resume/identity; transport behavior; current security guidance and real failure surfaces; SDK/spec versioning and interoperability; local-first relevance; reusable components and concrete ACL/Vera lessons. Use implementation repositories/issues only where necessary to verify the spec's realized semantics. Save evidence/catalog/state, commit research-only changes, and **stop before Goose**.

## Later tasks
1. Deep-research Goose after MCP, one project per separately authorized task.
2. Continue the remaining ranked active-project queue one task at a time.
3. Deep-research high-value developers/accounts one at a time.
4. Compare reusable components versus custom-build candidates.
5. Analyze collaboration/open-source options.
6. Deep-research agent security and memory safety.
7. Deep-research long-running autonomy and local-model compatibility.
8. Produce final synthesis only after the individual work is complete.

## Stop point

Task 14 ended after OpenAI Agents SDK project health, Swarm predecessor boundary, Runner/lifecycle ownership, versioned RunState semantics, human approval identity, guardrail/handoff/tool authority, Sandbox Agent state and credential rebind, Sessions/compaction, provider retry/replay safety, model/provider portability, streaming/cancellation, tracing/evidence and current state/filesystem failure surfaces were completed. No Model Context Protocol or Goose project research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
