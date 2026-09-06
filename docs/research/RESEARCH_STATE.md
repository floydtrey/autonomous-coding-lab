# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 9 — Strands Harness SDK deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Completed
- Research workspace initialized and evidence ladder established.
- Tasks 1–4 mapped recurring sources, active projects/people, research priority, and failed/abandoned/heavily redesigned attempts.
- Task 5 deep-researched **Pydantic AI** and the directly relevant official Pydantic AI Harness surfaces.
- Task 6 deep-researched **Cline** and its coding-agent architecture, authority, checkpoints, local-runtime/context and telemetry failure surfaces.
- Task 7 deep-researched **LangGraph** and its state/checkpoint, replay, interrupt, durability and retention failure surfaces.
- Task 8 deep-researched **promptfoo** as an independent evaluation/red-team/evidence layer.
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before Task 9.
- Deep-researched **Strands Harness SDK** as ranked project #5, using the ACL/Vera end goal to control scope.
- Verified current canonical project identity at `strands-agents/harness-sdk`; the former `sdk-python` path redirects to the consolidated monorepo rather than representing abandonment.
- Verified current active status, Apache-2.0 licensing, Python `Production/Stable` package classification, and current main `e3f3ee49d4f5e1f94bc489df6f8603ce26442c31` when examined.
- Verified Strands' model-driven loop plus harness-owned turn/token limits, explicit stop reasons, cancellation checkpoints, single-invocation ownership and Python idempotency-token behavior.
- Verified provider retry as a separate layer from structured-output correction and intervention/Guide retry; recorded that Guide-triggered retry has no framework-imposed cap and therefore needs application convergence/budget policy.
- Verified Python/TypeScript tool schema paths and preserved the distinction between schema exposure and runtime validation strength (for example TypeScript Zod validation versus plain JSON Schema callback input).
- Verified structured-output correction through a schema-backed tool: Pydantic/Zod validation errors are surfaced back to the model as concrete tool feedback so it can self-correct in the visible agent loop.
- Verified typed intervention actions (`Proceed`, `Deny`, `Guide`, `Confirm`, `Transform`) and explicit handler failure policies, including fail-closed `deny` behavior for security-sensitive controls.
- Verified the shipped Python Cedar authorization intervention: principal resolution, argument/runtime context, call-count state, policy/schema validation, and deny behavior on missing identity, evaluation error, no-decision or policy refusal.
- Recorded open goal-fencing issue #3877 as a separate objective-integrity gap; action authorization does not by itself prove continued alignment to the principal-approved task.
- Verified current sandbox abstraction and its security boundary: Docker/SSH/custom execution routes shell/file operations away from the trusted agent process, while omitting the sandbox runs those operations on the host with the agent process's full permissions.
- Verified that Docker/SSH provisioning, mounts, network, credentials, user, resources, cleanup and environment lifecycle remain application-owned rather than being guaranteed by the sandbox interface.
- Verified current SSH option allowlisting that blocks dangerous options such as host-side command execution unless the explicit unsafe bypass is enabled.
- Verified file-editor regression fix `e448bea9...` preserving untouched bytes/line endings/tabs around local edits and recorded open sandbox UTF-8 stream corruption issue #4156.
- Verified session/snapshot state ownership, immutable UUIDv7 history, multi-agent orchestrator persistence ownership, and the explicit limitation that built-in session managers assume one live writer with no distributed lock.
- Verified session-storage trust/symlink warning and the trusted-message-history security rule that restored Python history ending in `toolUse` can dispatch that tool on the next invocation without another model call.
- Verified open snapshot enumeration issue #4198, where list results can expose malformed IDs that restore rejects, reinforcing identical identity validation across enumerate/consume boundaries.
- Verified provider-side state as a separate durable state plane through current stateful-model architecture/evidence and open #4102; local message history is not necessarily the only state that affects future model behavior.
- Verified open #4004 as evidence that live streamed text and durable replay history can diverge and therefore need explicit consistency tests.
- Verified interrupt IDs, batch/per-tool approval semantics, and replay behavior; recorded that `AfterToolsEvent` can run more than once around an interrupt/resume split and side-effecting callbacks therefore need idempotency.
- Verified open #4171 where re-answering an already completed TypeScript interrupt can be accepted and trigger an extra model call, reinforcing exactly-once active approval/request validation.
- Verified sliding-window/summarizing context managers, tool-pair preservation, truncation/pinning/proactive compression and the boundary that model-visible context reduction is not authoritative project/effect state.
- Verified native **Python Ollama** support with tools/streaming/configuration and retained the requirement to benchmark exact model + runtime + adapter + settings rather than infer capability from provider name.
- Verified OpenTelemetry agent/cycle/model/tool traces and the separate Strands Evaluation package with deterministic, semantic and trace-based evaluators.
- Verified the eval quickstart warning that missing session trace identity can mix spans from separate test cases, reinforcing stable identity as part of evidence validity.
- Verified recent cancellation trace fix `ed05dcff...`, preserving cancellation as a distinct telemetry state rather than an incomplete/successful span.
- Recorded detailed evidence, candidate invariants, ACL fixture ideas, shipped-vs-proposed boundaries and explicit non-conclusions in `projects/strands-harness-sdk.md`.
- Preserved the decision boundary: Task 9 does **not** decide whether ACL should adopt/fork/wrap Strands, rank it against prior projects, or begin Codex research.

## Highest-value Strands findings for later comparison

1. Keep the model loop relatively free; put budgets, stop reasons, retries, cancellation and authority in deterministic runtime state.
2. Treat tool schema, runtime validation, authorization, sandboxing and evaluation as distinct control planes.
3. Use typed policy outcomes and fail closed for authority-bearing policy errors/no-decision/missing identity.
4. Action authorization does not replace immutable task/objective provenance.
5. Keep logical request/idempotency identity separate from run/attempt/agent/process identity.
6. Give every retry class its own reason, budget and progress/escalation rule.
7. Make execution environment explicit; “no sandbox” is a named full-host-authority mode, not an assumption.
8. Own sandbox provisioning, mounts/network/credentials/user/resources/cleanup separately from the execution API.
9. Preserve bytes outside intended file-edit regions and preserve stream decoder state across chunks.
10. Give each durable state domain one authoritative persistence owner; nested session owners create conflicting truth.
11. Built-in in-process/session guards do not provide distributed single-writer safety; ACL needs fencing/lease/version semantics.
12. Restored message/checkpoint state is trusted execution input. Valid JSON/schema does not establish provenance or permission to resume.
13. Every enumerated handle must satisfy the same identity validation as the consuming API.
14. Inventory every durable state plane, including provider/server-side conversation state, not only local messages.
15. UI stream, model-visible context, persisted replay history and audit/effect evidence are separate representations.
16. Approval/interrupt responses are exactly-once state transitions against active stable IDs; stale responses fail closed.
17. Interrupt/retry lifecycle callbacks may replay; side-effecting callbacks require stable idempotency/effect identity.
18. Context trimming/summarization/offloading is observable model-state mutation, not authoritative task/effect truth.
19. Local capability is exact model + Ollama/runtime + adapter + config + SDK-language behavior.
20. OpenTelemetry is useful evidence but may contain secrets/system prompts/tool data; telemetry audience/redaction is separate policy.
21. Evaluation evidence must bind to stable test/run/session identity; valid spans with wrong correlation are invalid evidence.
22. Rich design documents reveal intent, but only shipped code/tests/docs establish current guarantees.
23. Strands does not replace an outer ACL-owned project scheduler, distributed task authority, workspace/effect recovery ledger, dependency governance, acceptance policy or independent hostile verifier.

## Queue status

- **Pydantic AI (#1): complete.** Detailed evidence: `projects/pydantic-ai.md`.
- **Cline (#2): complete.** Detailed evidence: `projects/cline.md`.
- **LangGraph (#3): complete.** Detailed evidence: `projects/langgraph.md`.
- **promptfoo (#4): complete.** Detailed evidence: `projects/promptfoo.md`.
- **Strands Harness SDK (#5): complete.** Detailed evidence: `projects/strands-harness-sdk.md`.
- **Codex (#6): next task only.** No Codex deep research was begun in Task 9.
- Remaining ranked queue stays unchanged until its own separately authorized task or later evidence justifies an explicit update.

## Next task

Deep-research **Codex** only.

Do not begin this task until separately instructed. For the next task, deep-research Codex as ranked project #6 with the same end-goal discipline: runtime/agent architecture, command/file authority, sandbox and approval policy, workspace/Git boundaries, child/sub-agent permission inheritance, local/Ollama support, tool/protocol contracts, session/state/recovery, concurrency/cancellation, telemetry/evaluation, recurring failure surfaces, project health, reusable components and concrete ACL/Vera lessons. Save evidence/catalog/state, commit research-only changes, and **stop before OpenHands**.

## Later tasks
1. Deep-research OpenHands, then continue the ranked project queue one project per separately authorized task.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 9 ended after Strands architecture/lifecycle, structured output, intervention/authorization, sandbox/process authority, persistence/trusted-state, interrupt identity, context/local-model, observability/evaluation, failure-surface, catalog/watchlist/state updates and next-task definition were completed. No Codex or OpenHands research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
