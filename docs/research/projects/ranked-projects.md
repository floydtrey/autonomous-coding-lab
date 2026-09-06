# Ranked Projects — Task 3

**Accessed:** 2026-09-05  
**Task:** Rank the confirmed-active project watchlist for ACL and future Vera research.  
**Interpretation:** this is a **research / deep-research priority ranking**, not an adoption recommendation, product-quality score, benchmark result, or claim that a higher-ranked project is universally better.

## Ranking method

The 27 projects confirmed active in Task 2 were ranked by expected information value for ACL/Vera. The scoring heuristic is intentionally ACL-specific:

1. **Direct overlap with unresolved ACL/Vera problems — 25%**  
   Bounded worker control, tool contracts, validation, local models, lifecycle/recovery, observability, memory, and authority boundaries.
2. **Distinctive hard-problem evidence — 20%**  
   Does the upstream expose concrete implementation work or failure surfaces rather than only a broad feature claim?
3. **Local/open-model compatibility or provider independence — 15%**  
   Concrete local/Ollama/OpenAI-compatible/provider-neutral paths rank above provider lock-in when other factors are similar.
4. **Safety, reliability, and lifecycle depth — 15%**  
   Permissions, sandboxing, approvals, retries, checkpoints, interruption/cancellation, malformed outputs, or recovery.
5. **Potential reuse leverage — 15%**  
   Components, protocols, schemas, test infrastructure, or narrowly reusable abstractions that might save ACL implementation work.
6. **Evidence inspectability and current upstream signal — 10%**  
   Active source, tests/docs/code, stable repository identity, and enough public evidence to support later deep research.

The percentages are a prioritization heuristic, not measurements of project quality. Ties were broken in favor of the candidate that exposes a more distinctive unresolved ACL/Vera problem and then in favor of narrower reusable components over overlapping platform breadth.

**Important:** later project-by-project deep research can reorder this list. A candidate can rank high because it is especially educational even if ACL ultimately should not depend on it.

Aider and AutoGen are excluded from this active-project ranking because Task 2 left them **status deferred**. Their activity changes and any successor/redesign relationships belong to the next task.

## Tier A — immediate deep-research queue

### 1. Pydantic AI — `pydantic/pydantic-ai`
- **Why it ranks here:** unusually direct overlap with ACL's desired typed harness layer: structured tool schemas, validated arguments, retry behavior, dependency injection, async/concurrency handling, and concrete self-hosted Ollama support.
- **Primary evidence:** Pydantic AI explicitly supports self-hosted Ollama and implements an Ollama provider over an OpenAI-compatible API; its tool manager treats regular tool-call arguments as data matching the tool schema.
- **Possible reuse / lesson:** typed tool contracts, structured-output validation, model adapters, retry boundaries, and small-harness composition.
- **Warning:** typing and schema validation do not create filesystem/network authorization or prove local models behave reliably under malformed outputs.
- **Follow-up:** test how much validation/control stays in the harness when weak local models emit invalid tool calls repeatedly.
- **Sources:**
  - https://github.com/pydantic/pydantic-ai
  - https://github.com/pydantic/pydantic-ai/blob/main/docs/models/ollama.md
  - https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/tool_manager.py

### 2. Cline — `cline/cline`
- **Why it ranks here:** combines a real coding-agent edit loop with concrete local-model support and current file-operation safety work. Task 2 found an upstream fix preventing `apply_patch` Add File from silently overwriting an existing file.
- **Primary evidence:** local models are first-class through Ollama/LM Studio and OpenAI-compatible endpoints; current code and commits expose runtime/plugin, untrusted tool-data, edit, and model-routing seams.
- **Possible reuse / lesson:** edit semantics, approval UX, file-operation guards, provider routing, CLI/SDK agent boundaries, and regression cases for destructive operations.
- **Warning:** Cline is an end-user coding product, so its UX and product architecture should not be copied wholesale into ACL.
- **Follow-up:** identify which edit/approval invariants can be extracted without inheriting product-layer complexity.
- **Sources:**
  - https://github.com/cline/cline
  - https://github.com/cline/cline/blob/main/docs/running-models-locally/overview.mdx
  - https://github.com/cline/cline/commit/adbfbd97d352c82f7001273365f6a4bac38b5adb

### 3. LangGraph — `langchain-ai/langgraph`
- **Why it ranks here:** the strongest current source in the watchlist for explicit long-running runtime mechanics: checkpoints, retries, interruptions, durability, streaming, remote execution, subgraphs, and resume behavior.
- **Primary evidence:** current runtime code contains explicit retry/checkpoint policies; a drain path documents saving a checkpoint so a run interrupted by shutdown can resume later.
- **Possible reuse / lesson:** checkpoint schemas, interruption/resume contracts, retry ownership, task lifecycle, state projection, and recovery evidence.
- **Warning:** its graph/runtime surface is much broader than ACL currently needs and could become accidental architecture if copied wholesale.
- **Follow-up:** isolate the smallest durable-run semantics worth reproducing in a bounded local worker harness.
- **Sources:**
  - https://github.com/langchain-ai/langgraph
  - https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/errors.py
  - https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/pregel/_retry.py

### 4. promptfoo — `promptfoo/promptfoo`
- **Why it ranks here:** it is not another orchestration framework; it directly addresses the independent-evaluation layer ACL already knows it needs. Current agent/coding-agent material includes trajectory assertions and deterministic trace-level verifiers.
- **Primary evidence:** agent assertions cover tool use, tool arguments, tool sequence, step count, and goal success; coding-agent red-team guidance explicitly targets repository prompt injection, terminal trust, secret leaks, sandbox escape, CI exfiltration, unsafe automation, and verifier sabotage.
- **Possible reuse / lesson:** regression harnesses, trace assertions, adversarial fixtures, security test organization, and the boundary between final-answer grading and execution-trace verification.
- **Warning:** generic red-team/eval suites still need ACL-specific deterministic fixtures and trusted independent validators.
- **Follow-up:** determine which test primitives can wrap ACL's own benchmark without making promptfoo the source of truth.
- **Sources:**
  - https://github.com/promptfoo/promptfoo
  - https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/llm-agents.md
  - https://github.com/promptfoo/promptfoo/blob/main/site/docs/red-team/coding-agents.md

### 5. Strands Harness SDK — `strands-agents/harness-sdk`
- **Why it ranks here:** its scope is explicitly close to the custom-harness question rather than a broad application platform, and it supports local Ollama models plus schema-driven structured output.
- **Primary evidence:** its `StructuredOutputTool` validates LLM output against a Zod schema and feeds validation errors back for retry; the Python SDK includes an Ollama model adapter. Its own tool documentation also warns that unrestricted filesystem tools inherit full process permissions and should be sandboxed.
- **Possible reuse / lesson:** harness interfaces, structured-output retry loop, provider boundaries, and explicit tool/sandbox responsibilities.
- **Warning:** a warning to sandbox a dangerous tool is not itself a security boundary; ACL must keep authority enforcement outside the model.
- **Follow-up:** compare Strands' harness/model/tool interfaces directly with ACL's existing local-worker harness before deciding whether any component is reusable.
- **Sources:**
  - https://github.com/strands-agents/harness-sdk
  - https://github.com/strands-agents/harness-sdk/blob/main/strands-ts/src/tools/structured-output-tool.ts
  - https://github.com/strands-agents/harness-sdk/blob/main/strands-py/src/strands/models/ollama.py

### 6. Codex — `openai/codex`
- **Why it ranks here:** exceptionally rich implementation evidence around sandboxing, command segmentation, approvals, filesystem/network permissions, child-agent authority inheritance, and terminal execution; it also contains an Ollama integration.
- **Primary evidence:** workspace-write policy distinguishes writable roots from paths requiring approval; approval logic is explicit in core code; child agents are prevented from diverging from parent sandbox/approval/cwd authority.
- **Possible reuse / lesson:** permission policy modeling, approval routing, command parsing/segmentation, sandbox diagnostics, authority inheritance, and defensive terminal design.
- **Warning:** it is a product with OpenAI-specific assumptions and a Rust implementation; architecture lessons may transfer better than code.
- **Follow-up:** extract provider-neutral permission invariants and Windows-relevant sandbox lessons without adopting product-specific control flow.
- **Sources:**
  - https://github.com/openai/codex
  - https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/sandboxing.rs
  - https://github.com/openai/codex/blob/main/codex-rs/core/src/tools/handlers/multi_agents_common.rs

### 7. OpenHands — `OpenHands/OpenHands`
- **Why it ranks here:** broad coding-agent/harness evidence across provider configuration, runtime sandboxing, review/evidence policy, telemetry, repository boundaries, and Ollama support.
- **Primary evidence:** the code exposes runtime-sandbox state and provider mapping including Ollama. Current project documents also make trust limitations explicit in some extension surfaces rather than hiding them.
- **Possible reuse / lesson:** agent runtime separation, evidence/review gates, sandbox integration, provider adapters, and operational telemetry.
- **Warning:** large cloud/product surfaces can obscure which mechanisms are essential to a small bounded local lab.
- **Follow-up:** separate reusable lifecycle/evidence patterns from cloud-service and UI architecture.
- **Sources:**
  - https://github.com/OpenHands/OpenHands
  - https://github.com/OpenHands/OpenHands/blob/main/AGENTS.md
  - https://github.com/OpenHands/OpenHands/blob/main/src/utils/map-provider.ts

### 8. SWE-agent — `SWE-agent/SWE-agent`
- **Why it ranks here:** a relatively small software-engineering harness with strong benchmark/evaluation relevance and concrete local Ollama configuration, useful as a counterweight to larger agent products.
- **Primary evidence:** Task 2 found recurring fixes where benchmark-subset mapping, MIME normalization, URL parsing, and CLI hierarchy could invalidate runs independently of model quality; docs include a local Ollama `api_base` path.
- **Possible reuse / lesson:** minimal agent-computer interface, benchmark harness structure, trajectory/evaluation discipline, and regression fixtures around harness correctness.
- **Warning:** SWE-bench-style issue resolution is narrower than ACL's eventual workload and should not become the only success definition.
- **Follow-up:** identify the minimum harness contracts that made SWE-agent reproducible and compare them with ACL's current task protocol.
- **Sources:**
  - https://github.com/SWE-agent/SWE-agent
  - https://github.com/SWE-agent/SWE-agent/blob/main/docs/config/models.md
  - https://github.com/SWE-agent/SWE-agent/commit/3ea751c087f32b16e039a2233dd6eefecef325d5

### 9. llama.cpp — `ggml-org/llama.cpp`
- **Why it ranks here:** ACL's local workers ultimately depend on runtime behavior beneath any harness. llama.cpp exposes quantization/backend/KV-cache behavior plus JSON-schema grammars, tool-call grammars, parsers, and regression tests.
- **Primary evidence:** grammar types explicitly distinguish JSON-schema output and tool calls; current chat tests assert that lazy tool-call grammar triggers must actually fire so broken constraints cannot silently pass tests.
- **Possible reuse / lesson:** version-pinned local inference, constrained decoding, tool-call parser behavior, runtime regression cases, and hardware-specific failure diagnosis.
- **Warning:** this is an inference runtime, not an agent policy layer; correct constrained output does not validate whether a tool should be allowed.
- **Follow-up:** map which local models and chat templates produce reliable tool calls under ACL's schemas and hardware.
- **Sources:**
  - https://github.com/ggml-org/llama.cpp
  - https://github.com/ggml-org/llama.cpp/blob/master/common/common.h
  - https://github.com/ggml-org/llama.cpp/blob/master/tests/test-chat.cpp

### 10. OpenAI Agents SDK — `openai/openai-agents-python`
- **Why it ranks here:** lightweight Python surface with persisted run state, interruptions, approvals, tool outputs, sandbox state, traces, local-sandbox support, and an Ollama example.
- **Primary evidence:** the repository's run-state schema explicitly tracks approval/tool/sandbox/trace state; sandbox code sanitizes mount authority before serialization; tool definitions expose approval handlers.
- **Possible reuse / lesson:** serializable run state, approval state, trace organization, sandbox snapshots, handoffs, and regression-test organization.
- **Warning:** some abstractions and examples remain provider/product-specific, so local-model parity must be verified rather than assumed.
- **Follow-up:** compare its serialized run-state boundary with ACL's task/checkpoint/evidence records.
- **Sources:**
  - https://github.com/openai/openai-agents-python
  - https://github.com/openai/openai-agents-python/blob/main/.agents/references/runstate-schema.md
  - https://github.com/openai/openai-agents-python/blob/main/docs/sandbox/guide.md

## Tier B — high-value follow-up

### 11. Model Context Protocol — `modelcontextprotocol/modelcontextprotocol`
- **Priority reason:** high cross-cutting value for tool contracts and long-running operations. The current specification includes progress, cancellation, errors and Tasks; task state can be bound to authorization context, and cancellation acknowledgements explicitly have consistency semantics.
- **Why below Tier A:** MCP is a protocol, not ACL's orchestration or authorization policy. It should inform interfaces after concrete harness/safety implementations are understood.
- **Follow-up:** determine which lifecycle primitives ACL can reuse while keeping permission decisions local to the harness.

### 12. Goose — `aaif-goose/goose`
- **Priority reason:** strong provider/extensibility signal, first-class Ollama support, and a 2026 built-in local-inference path powered directly by llama.cpp; active MCP/GDK work adds useful protocol/harness evidence.
- **Why below Tier A:** overlaps Cline/Codex/OpenHands for full-agent behavior and needs deeper evidence on independent validation and bounded authority.
- **Follow-up:** compare built-in local inference and extension authority with ACL's separate worker/runtime design.

### 13. Ollama — `ollama/ollama`
- **Priority reason:** immediate operational dependency candidate for local workers; API supports tools and structured output and is already used by many higher-ranked harnesses.
- **Why below llama.cpp:** convenience/API behavior is important, but lower-level parser/grammar/backend evidence often lives beneath it.
- **Follow-up:** define version-pinned regression tests for tool calls, structured output, context behavior, and model-loading failures.

### 14. Letta Code — `letta-ai/letta-code`
- **Priority reason:** one of the most directly relevant future-Vera projects. Current code projects memory to a local filesystem and uses git-backed memory mutations with commit reasons and agent identity, with the harness handling remote MemFS push.
- **Why not Tier A yet:** its value is stronger for future persistent assistant identity/memory than the immediate ACL coding-worker harness.
- **Follow-up:** study the authority split between agent-authored memory changes, git history, synchronization, rollback, and user review.

### 15. Gemini CLI — `google-gemini/gemini-cli`
- **Priority reason:** excellent current security signal around workspace boundaries, symlink resolution, configuration ownership/permissions, environment mutation, sandbox expansion and approval.
- **Why not higher:** provider/product assumptions are more Google-specific and Task 3 found less concrete local-model portability evidence than the higher coding-agent candidates.
- **Follow-up:** extract filesystem and configuration-trust tests that can be made provider-neutral.

### 16. Graphiti — `getzep/graphiti`
- **Priority reason:** distinctive future-Vera memory architecture: temporal validity plus raw Episodes as provenance/ground-truth, with derived facts traceable back to source episodes.
- **Why below Letta Code:** highly relevant memory semantics, but graph complexity is farther from ACL's immediate coding-worker needs and may be unnecessary for an initial Vera memory layer.
- **Follow-up:** compare provenance/temporal benefits against simpler append-only or git-backed memory designs.

### 17. Microsoft Agent Framework — `microsoft/agent-framework`
- **Priority reason:** active Python/.NET framework with a concrete local Ollama package, tool permission callbacks, approval modes, and sandboxed code-execution components that deny OS/filesystem/network access by default unless exposed.
- **Why here:** substantial useful evidence, but broad enterprise scope overlaps several higher-ranked harness/runtime projects.
- **Follow-up:** isolate its code-execution/sandbox and provider interfaces from enterprise orchestration features.

### 18. Google ADK — `google/adk-python`
- **Priority reason:** concrete state serialization, tool schemas, validation-retry paths, callbacks, MCP tooling, and an Ollama sample that explicitly warns tool-using agents require tool-capable local models.
- **Why here:** strong breadth but some GitHub development is mirrored through Copybara and its platform surface overlaps higher-ranked typed/runtime candidates.
- **Follow-up:** inspect state/tool callback ownership and malformed-tool recovery independently of Gemini-specific behavior.

### 19. LiteLLM — `BerriAI/litellm`
- **Priority reason:** likely useful provider normalization/routing layer with logging, fallback, cost/accounting and broad tool/structured-output support.
- **Why here:** gateway abstraction can hide provider-specific semantics—the exact failures ACL needs to observe while benchmarking local workers.
- **Follow-up:** test whether normalization helps or masks malformed output, retries, stop reasons and tool errors from local endpoints.

### 20. vLLM — `vllm-project/vllm`
- **Priority reason:** strong future serving option for concurrent workers; current docs expose strict tool-calling schemas and structured-output enforcement.
- **Why here:** ACL's present small-machine/single-worker experiments do not yet need high-throughput serving architecture.
- **Follow-up:** revisit when worker concurrency or larger GPU nodes make serving/batching a real bottleneck.

## Tier C — comparative / situational watch

### 21. OpenCode — `anomalyco/opencode`
- **Reason:** highly active coding-agent implementation with provider-neutral and OpenAI-compatible abstractions; useful comparator for routing/protocol behavior.
- **Why lower:** current evidence overlaps higher-ranked coding agents without yet exposing as distinctive an ACL-critical safety/recovery mechanism.

### 22. Mem0 — `mem0ai/mem0`
- **Reason:** clear memory CRUD lifecycle (add/update/delete/get), persistence and integration surface; useful baseline for a conventional memory layer.
- **Why lower:** current evidence is less distinctive on memory provenance, integrity, rollback, and poisoning resistance than Letta Code or Graphiti.

### 23. smolagents — `huggingface/smolagents`
- **Reason:** useful minimalist counterexample for deciding how little framework ACL can get away with.
- **Why lower:** minimalism can push control and safety back into model prompts, which reduces distinctive reusable reliability evidence.

### 24. Agno — `agno-agi/agno`
- **Reason:** active broad framework with Ollama adapters, checkpoint surfaces and resumable examples.
- **Why lower:** platform breadth duplicates multiple higher-ranked candidates and increases review cost before ACL has a need for its full operational layer.

### 25. LlamaIndex — `run-llama/llama_index`
- **Reason:** concrete Ollama function-calling support and a major retrieval/data ecosystem relevant to future Vera.
- **Why lower:** its distinctive value is currently more RAG/data-centric than ACL's bounded coding-worker harness.

### 26. CrewAI — `crewAIInc/crewAI`
- **Reason:** active multi-agent/flow framework and a source of real tool-streaming edge cases.
- **Why lower:** ACL has not established that role-heavy multi-agent decomposition is beneficial; investigating orchestration breadth before basic worker reliability would invert the project's dependency order.

### 27. Mastra — `mastra-ai/mastra`
- **Reason:** active TypeScript framework with workflows/evals/MCP and good comparative value.
- **Why lower:** TypeScript-first application-framework breadth has the weakest immediate fit with ACL's current Python/local-worker experiments among the confirmed-active set.

## Cross-cutting conclusions from the ranking

1. **No single project covers ACL's problem.** The immediate queue intentionally spans typed harnesses, coding-agent authority, durable runtime state, independent evaluation, local inference, and protocol semantics.
2. **Local-model support is necessary but not sufficient.** Many projects now support Ollama or OpenAI-compatible endpoints. The differentiator is whether they expose trustworthy contracts and failure handling around those models.
3. **Safety evidence often appears in ordinary bug fixes.** File overwrite, path/symlink escapes, permission inheritance, invalid tool schemas, cancellation races, and parser constraints are higher-value research signals than feature lists.
4. **Framework breadth is discounted when it duplicates narrower evidence.** ACL should learn the hard mechanisms first, then decide how much framework surface is justified.
5. **Memory has a separate near-future queue.** Letta Code and Graphiti rank above generic memory CRUD because git-backed history/identity and temporal provenance map more directly to Vera's eventual integrity and explainability questions.
6. **A high rank is not a vote to adopt.** It means the project should be studied sooner because it is expected to reduce uncertainty or prevent duplicated mistakes.

## Stop boundary

Task 3 ranks the active project watchlist only. It does **not** determine adoption, fork/collaboration targets, architecture changes, or why status-deferred/older projects slowed, failed, moved, or were redesigned. The failed/abandoned/heavily-redesigned analysis remains the next separately authorized task.
