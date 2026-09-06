# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 13 — llama.cpp deep research complete
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
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before Task 13.
- Deep-researched **llama.cpp** as ranked project #9, using the ACL/Vera end goal to control scope.
- Verified canonical current project identity at `ggml-org/llama.cpp`, MIT license, active/non-archived status and inspected upstream revision `9e0e220594af405a62835dc3a27495729fd8506b` from 2026-09-06.
- Verified broad local-runtime/backend portability across CPU and multiple GPU/accelerator paths plus OpenAI-compatible server surfaces, while preserving the distinction between hardware portability and behavioral portability.
- Verified current chat/tool infrastructure explicitly models messages, tool calls, tool choice, parallel-tool flags, grammar/schema input, parser state and streamed tool-call evidence rather than treating all tool use as plain text.
- Verified current Jinja capability analysis actively probes templates for tools, tool calls, parallel calls, system-role behavior, content representation and argument behavior.
- Preserved the distinction between **discovered template capability** and **verified deployment capability**; template analysis does not prove the model/runtime will execute ACL tool fixtures correctly.
- Verified current auto-parser behavior derives protocol structure from differential chat-template renders, making parser/template inference itself part of the versioned runtime capability path.
- Verified built-in GBNF/JSON-Schema conversion is intentionally a subset implementation with documented semantic differences and unsupported features; unsupported schema behavior can include silent skipping in some conversion paths.
- Recorded that built-in `additionalProperties` behavior differs from normal JSON Schema default semantics and therefore constraint-backend identity belongs in the capability profile.
- Verified optional LLGuidance provides a separate structured-output backend with broader/different schema semantics and more explicit unsupported-schema error behavior, but current documentation also notes error handling can continue after reported failures; ACL would need fail-closed outer preflight for authority-bearing schemas.
- Recorded open issue #28429 as a high-value current failure surface: non-ASCII schema property names can collide after grammar rule sanitization, silently losing a distinct parameter and causing constrained decoding to force the wrong tool argument even when the underlying model can produce the correct call through another runtime/path.
- Extracted the candidate invariant that schema normalization/conversion is trusted code and must prove required fields survive uniquely before a worker capability is activated.
- Recorded open issue #25923 as evidence that valid/edge schemas can produce invalid/rejected grammar and that one bad schema can poison a combined multi-tool grammar; did not claim the issue fully fixed because current grammar changes address only part of the reported surface and the issue remained open.
- Extracted the candidate invariant that a worker `ToolCapabilitySet` must be compiled/preflighted atomically before a long-running task begins.
- Verified server architecture separates HTTP/API work, inference context, typed tasks, slots, task/response queues, parser state, continuous batching, prompt/context cache behavior, model routing and resumable streaming.
- Verified server task types include explicit cancellation/control and slot state operations; current source separately carries prompt/generation timing controls and leaves prompt-time maximum duration marked for implementation, reinforcing per-phase timeout ownership rather than one generic worker deadline.
- Verified server development scope explicitly keeps complex server-side agentic/external-API loops out of the inference runtime, supporting ACL's outer-orchestrator ownership of project/task/effect authority.
- Verified resumable generation transport can continue across client detach/reattach with bounded buffering and lifecycle controls; classified this as transport continuity, not durable ACL task state or audit evidence.
- Verified prompt/KV caches and context checkpoints are inference state/optimization and must remain distinct from ACL continuation checkpoints, workspace snapshots and external-effect settlement.
- Recorded open issue #23577 as unresolved long-horizon failure evidence involving pathological repeated output after hours of use; did not attribute root cause to cache, checkpoint, quantization or speculative decoding without evidence.
- Derived that ACL local-model qualification needs endurance/many-turn/pathological-output tests in addition to one-shot benchmark prompts.
- Recorded open `bug-unconfirmed` issue #25618 as configuration-scoped evidence that model-based speculative decoding can diverge from vanilla greedy output for some quantized targets while control paths differ, reinforcing that performance optimizations are behavior-bearing profile settings until equivalence is verified.
- Defined a reproducibility manifest that includes runtime commit/build/backend/driver/hardware, GGUF digest/quantization, tokenizer/template/parser, constraint backend/schema digest, context/KV/cache settings, speculative mode, sampling, server flags and ACL fixture/verifier identity.
- Preserved the authority boundary: llama.cpp can generate/parse/constrain tool calls but does not thereby validate ACL task scope, authorize real-world effects, settle tool side effects or determine independent pass/fail.
- Recorded detailed primary sources, current failure boundaries, candidate invariants, future ACL regression fixtures and explicit non-conclusions in `projects/llama-cpp.md`.
- Preserved the decision boundary: Task 13 does **not** decide whether ACL should adopt/fork/wrap llama.cpp, select a cross-project winner, redesign ACL/Vera governance, or begin OpenAI Agents SDK research.

## Highest-value llama.cpp findings for later comparison

1. Local-model capability is realized at the full deployment stack, not at the model name or nominal OpenAI-compatible endpoint.
2. Record runtime commit/build/backend/driver/hardware, GGUF digest/quantization, tokenizer/template/parser, constraint backend, context/KV/cache, speculative mode and sampling as behavior-bearing profile identity.
3. Template capability discovery and end-to-end deployment verification are separate evidence states.
4. Chat templates, specialized handlers/auto-parser and constraint compiler are part of the trusted tool-call path.
5. `structured_output=true` is too coarse: built-in GBNF and LLGuidance expose different schema semantics and failure behavior.
6. Unsupported/ambiguous schema semantics must fail closed for authority-bearing tools; silent weakening is unacceptable as a production capability signal.
7. Tool-schema registration should be atomic and preflight the complete tool set before execution begins.
8. Schema conversion must prove every required field survived normalization/sanitization uniquely; Unicode/collision fixtures are mandatory.
9. Valid constrained JSON does not establish that the intended schema was represented faithfully.
10. A deterministic constraint layer can make a capable model deterministically wrong; parser/grammar failures need their own failure class separate from model quality.
11. Runtime slots, transport sessions and resumable stream IDs are not ACL project/task/run/effect identities.
12. Continuous batching and inference concurrency can remain below ACL's project/task scheduler.
13. Each blocking inference phase needs its own timeout/cancellation owner; one worker timeout is insufficient.
14. Inference cancellation does not settle worker filesystem/network/API effects.
15. KV/prompt/context checkpoints are inference optimization state, not ACL continuation authority.
16. Performance optimizations such as speculative decoding are behavior-bearing configuration until ACL equivalence tests prove otherwise.
17. Local runtime qualification needs long-horizon endurance/pathology tests, not only one-shot coding accuracy.
18. Bounded/resumable stream buffers are transport continuity, not audit logs or durable evidence.
19. llama.cpp's explicit model-agnostic server boundary supports keeping agent loops, authorization and external-effect orchestration outside the inference runtime.
20. llama.cpp is strongest as an inference/runtime and capability-profiling substrate; it does not replace ACL scheduling, dependency gates, sandbox/process authority, effect ledger, protected verifier, durable recovery, credentials or Vera memory governance.

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
- **OpenAI Agents SDK (#10): next task only.** No OpenAI Agents SDK deep research was begun in Task 13.
- Remaining ranked queue stays unchanged until its own separately authorized task or later evidence justifies an explicit update.

## Next task

Deep-research **OpenAI Agents SDK** only.

Do not begin this task until separately instructed. For the next task, deep-research `openai/openai-agents-python` as ranked project #10 with the same end-goal discipline. Cover the current agent/run lifecycle; tools and handoffs; guardrails/approval and sandbox/authority semantics; serializable run/session state and resume behavior; cancellation/interruption; tracing/evidence; local/custom model/provider boundaries; retry/failure behavior; security/credential implications; recurring current failures; project health; reusable components and concrete ACL/Vera lessons. Use Swarm only insofar as the documented predecessor relationship directly clarifies which operational controls were added; do not start a separate historical project task. Save evidence/catalog/state, commit research-only changes, and **stop before Model Context Protocol**.

## Later tasks
1. Deep-research Model Context Protocol after OpenAI Agents SDK, one project per separately authorized task.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 13 ended after llama.cpp runtime/backend architecture, chat-template/tool parsing, auto-parser capability, built-in GBNF and LLGuidance structured-output behavior, current schema/constraint failure surfaces, server slots/concurrency/cancellation/timeouts, resumable streaming, context/KV/cache checkpoint semantics, long-horizon/speculative-decoding failure evidence, local-runtime reproducibility requirements, catalog/watchlist/state updates and next-task definition were completed. No OpenAI Agents SDK or Model Context Protocol research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
