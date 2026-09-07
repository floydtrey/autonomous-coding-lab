# smolagents deep research

**Task:** 27
**Project:** `huggingface/smolagents`
**Research date:** 2026-09-07
**Scope:** research only; no adoption, model assignment, benchmark execution, or ACL implementation decision

## Executive assessment

smolagents is a deliberately small agent framework centered on a multi-step ReAct loop, with two primary action styles: `CodeAgent`, which expresses tool use as Python code, and `ToolCallingAgent`, which emits model-native/JSON-style tool calls. Its value to ACL is strongest as reference material for keeping the model-facing loop thin while externalizing execution, tools, models, callbacks, and verification seams.

It is not a complete ACL control plane. Current upstream explicitly states that `LocalPythonExecutor` is **not a security boundary**. Sandboxed backends such as Docker, E2B, Modal and Blaxel provide stronger isolation profiles, but executor choice, credentials, network/mount policy, cleanup, task/effect identity, durable recovery and independent verification remain external system responsibilities.

The current stable release observed is **v1.26.0** (published 2026-05-29). Current `main` at commit `30bb1161095dbae2271e6bc3cc4c219cc3897a57` reports package version **1.27.0.dev0**. Stable and `main` therefore belong to separate qualification profiles.

Task 27 found several high-value regression fixtures for ACL: an open local-executor timeout path that returns only after underlying work finishes (#2197), managed-agent summary leakage of raw inner tool traffic (#2424), silent managed-agent failure propagation (#2166), shared managed-agent state during parallel calls (#1781), `final_answer_checks` being silently bypassed under `python -O` because validation uses `assert` (#2456), and quadratic context replay as step history grows (#2566). These are harness/runtime defects, not model-quality failures.

## 1. Project identity and maturity

### Observed fact

- Latest GitHub stable release observed: **v1.26.0**, published 2026-05-29.
- Current `main`: `30bb1161095dbae2271e6bc3cc4c219cc3897a57`, with `pyproject.toml` version **1.27.0.dev0**.
- Upstream API documentation continues to label smolagents as experimental and subject to change.
- The repository intentionally keeps the core agent loop small and readable.

### ACL implication

Exact smolagents release/commit is part of benchmark and deployment identity. Results from v1.26.0, current 1.27 development code, or a later executor/plugin architecture must not be treated as interchangeable.

### Candidate invariant

Record at least:
- smolagents release or commit;
- agent class/action profile (`CodeAgent` vs `ToolCallingAgent`);
- model adapter and model artifact;
- executor class/profile;
- tool/MCP origins and schemas;
- prompt/template revision;
- context and sampling settings;
- sandbox realization and credential/network profile.

## 2. Core runtime architecture

### Observed fact

`MultiStepAgent` owns a compact step loop with:
- `max_steps`;
- optional planning intervals;
- a mutable `state` dictionary;
- `AgentMemory` containing task/action/planning steps;
- step callbacks;
- managed sub-agents;
- optional `final_answer_checks`;
- model and tool registries.

A run normally resets the in-memory history. `reset=False` carries prior steps into the next run. `AgentMemory` is a list of semantic step objects and is designed for inspection/replay rather than durable process recovery.

`CodeAgent` converts model output into Python actions. `ToolCallingAgent` follows the more conventional structured tool-call path. They are materially different harness profiles even when model and tool set are otherwise identical.

### ACL implication

This is strong reference material for **model-facing simplicity versus deterministic infrastructure**. The loop can remain small while authority, scheduling, persistence, effects and verification stay outside it.

### Non-conclusion

The in-memory step list is not an ACL checkpoint. It does not prove:
- workspace state settled;
- subprocesses stopped;
- external effects settled;
- current credentials/policy remain valid;
- verifier acceptance occurred.

## 3. Code execution boundary

### Observed fact

The current security policy states unambiguously that `LocalPythonExecutor` is **not a security boundary**. Escaping it, reading host files, or reaching the network is treated as expected documented risk rather than an isolation guarantee.

Upstream recommends sandboxed backends for untrusted model-authored code. Current built-in `CodeAgent` executor types are:
- `local`;
- `blaxel`;
- `e2b`;
- `modal`;
- `docker`.

The secure-execution documentation distinguishes snippet-only sandboxing from placing the whole agent system inside an isolated environment. The latter gives a stronger boundary but raises credential and orchestration complications.

### Security history

The local interpreter has accumulated multiple public sandbox/code-execution findings, including CVE-2025-5120 and later issues around incomplete local-executor restrictions. Current upstream has responded by explicitly removing the local executor from the security-boundary threat model rather than presenting AST/interpreter checks as robust containment.

### ACL implication

This strongly reinforces ACL's existing invariant:

**interpreter restrictions / allowlists / approvals are not OS containment.**

Any ACL worker that executes model-generated code requires an ACL-owned sandbox profile with independently defined:
- filesystem mounts;
- network policy;
- process/user/capability limits;
- resource limits;
- credential injection;
- workspace identity;
- teardown and process-tree settlement.

## 4. Executor abstraction and current redesign direction

### Observed fact

Issue #2722, opened 2026-09-01, is accepted and priority P1. It proposes making executors pluggable through package entry points. Current `executor_type` remains a hardcoded literal and the built-in executor mapping is maintained in core.

The issue notes that hosted-executor integrations currently depend on smolagents core review and are covered largely by mocked tests rather than live provider tests.

### ACL implication

The `PythonExecutor` / `RemotePythonExecutor` shape is a useful boundary to study, but executor implementation identity must remain explicit. A generic `executor_type` string cannot by itself establish isolation quality, API behavior, cleanup correctness or credential handling.

### Candidate reuse

A future ACL harness could borrow the idea of a narrow executor contract while adding a stronger manifest containing:
- executor implementation/package/version/digest;
- realized isolation type;
- allowed mounts/network;
- resource ceiling;
- credential profile;
- cleanup probes;
- process/effect settlement evidence.

## 5. Timeout and cancellation semantics

### Current fixture: #2197

Open issue #2197 demonstrates a local executor configured with a one-second timeout returning only after a three-second worker finishes. The reported root cause is thread-pool cleanup waiting on the worker after `future.result(timeout=...)` raises.

This means timeout declaration and caller control-return can diverge.

### Interrupt behavior

Current user-facing guidance describes `agent.interrupt()` as stopping the agent at the end of the current step. It is therefore a cooperative safe-boundary control rather than guaranteed immediate termination of provider/tool/process work.

### ACL implication

Preserve distinct states for:
1. timeout/interrupt requested;
2. harness loop stopped;
3. underlying provider/tool/process terminated;
4. external effects reconciled;
5. workspace/resources settled.

A timeout exception alone cannot authorize automatic replay of an effect-bearing action.

## 6. Managed agents and delegation

smolagents models managed sub-agents as callable tools exposed to a parent agent. This is lightweight and easy to understand, but current issues expose several important delegation boundaries.

### #1781 — shared managed-agent instance state

Issue #1781 reports that multiple parallel calls to the same managed-agent instance can share and overwrite mutable state, producing identical/misrouted results rather than independent executions.

**ACL lesson:** an agent definition and an agent invocation are separate identities. Parallel calls need independent run state or explicit serialization/leases.

### #2166 — silent sub-agent failure

Open issue #2166 reports cases where a managed agent that hits a tool error or exhausts `max_steps` can yield empty/`None` output to the manager, leaving failure indistinguishable from legitimate empty success.

**ACL lesson:** child completion must be typed. Parent-visible result states should distinguish at least success, rejected, max-steps, timeout, cancelled, tool failure, transport failure and uncertain-after-effect.

### #2424 — summary leaks internal tool traffic

Open issue #2424 reproduces v1.26.0 `provide_run_summary=True` passing inner tool calls and tool responses into the parent observation. The demonstrated data can include secrets/PII returned by tools.

Current `ActionStep.to_messages(summary_mode=True)` suppresses free-form model output but still emits tool calls and observations, explaining the leak class.

**ACL lesson:** a delegation summary is a new information-flow boundary. Child raw observations, credentials, internal IDs and private tool outputs must not automatically flow to the parent merely because the child can see them.

### Candidate invariant

Every delegated run should have:
- immutable parent task/run identity;
- distinct child invocation ID;
- explicit capability ceiling;
- separate mutable state;
- typed completion state;
- explicit export/redaction contract for child-to-parent evidence.

## 7. `final_answer_checks`: useful seam, unsafe as sole authority today

### Observed fact

`MultiStepAgent` exposes `final_answer_checks` and passes the answer, memory and agent object to each check before accepting a final answer. This is a useful deterministic-host seam.

### Current fixture: #2456

Open issue #2456 shows `_validate_final_answer` currently uses Python `assert` to enforce a check's truth value. Under `python -O` or `-OO`, asserts are stripped, so a false-returning final-answer check can be silently disabled.

Current `main` source still contains this `assert`, corroborating the issue against the observed 1.27 development profile.

### ACL implication

The seam is reusable; the implementation is not sufficient for a security/acceptance boundary.

ACL verifier/policy code must:
- use explicit control flow, never `assert`, for production decisions;
- run outside worker mutation authority;
- fail closed if checks cannot run;
- record verifier version/input/evidence/result;
- remain independent from the model/harness under test.

## 8. Agent memory and context growth

### Observed fact

`AgentMemory` stores task, planning and action steps and replays them as model messages. By default a new run resets this list; `reset=False` carries it forward.

Issue #2566 documents that the full accumulated history is replayed on each action step, yielding approximately quadratic cumulative input-token growth as the number/size of steps rises. Large tool observations amplify the effect.

### ACL implication

This is both a cost/performance and reliability concern for ACL's planned 32K evaluation:
- long histories can consume context unexpectedly;
- tool observations can dominate later calls;
- compaction changes behavior and therefore becomes benchmark identity;
- memory replay is not durable state recovery.

### Candidate benchmark rule

Record per step:
- input/output tokens;
- context length;
- retained/compacted observations;
- summary algorithm/revision;
- truncation events;
- exact prompt/tool projections.

A model that succeeds only before history pressure crosses a threshold should not be treated as having equivalent long-horizon reliability.

## 9. Model and local-runtime portability

### Observed fact

Current smolagents supports several model adapters, including:
- `InferenceClientModel`;
- local `TransformersModel`;
- `VLLMModel`;
- `MLXModel`;
- `LiteLLMModel` / router paths;
- `OpenAIModel` for OpenAI-compatible servers;
- cloud-specific adapters.

The README also explicitly advertises local Transformers/Ollama-style usage and broad provider interoperability.

### ACL implication

This makes smolagents potentially valuable as a **harness comparison profile** in the future benchmark lab, not evidence that any model/runtime pair is already qualified.

Exact local capability remains:

`model artifact + tokenizer/template + runtime + adapter + agent action style + tool schema/parser + executor + context/sampling configuration`.

CodeAgent and ToolCallingAgent should be scored separately because code-shaped actions and native tool-call actions impose different model demands.

## 10. Tools, Hub loading and MCP

### Tool trust

smolagents supports tools from local code, Hugging Face Hub, Spaces, LangChain and MCP. Hub/tool loading can execute custom code and therefore exposes an explicit `trust_remote_code` decision.

### MCP behavior

`ToolCollection.from_mcp` / `MCPClient` support stdio, streamable HTTP and legacy SSE. Current docs require `trust_remote_code=True` for loading MCP tool code and note that an asyncio event-loop thread is spawned for MCP handling.

Open issue #2305 requests an additional server-trust layer because current MCP integration does not independently establish that a server/tool definition is trustworthy.

### ACL implication

`trust_remote_code=True` is an operator trust decision, not an ACL authorization primitive. A valid MCP server/tool schema must still sit beneath ACL-owned:
- trusted origin identity;
- principal authorization;
- tool/schema version identity;
- credential/network policy;
- effect classification;
- process/server lifecycle custody.

Tool descriptions and MCP-returned instructions remain untrusted model-facing content.

## 11. State and recovery

### Observed fact

The primary agent state is in-process Python state plus `AgentMemory`. Runs may keep conversation state with `reset=False`, and agent/memory objects can be inspected or serialized for debugging/sharing, but the core execution model is not a durable workflow engine with transactional checkpoints or exactly-once external effects.

### ACL implication

Do not equate:
- saved/replayed agent messages;
- a Hub-saved agent definition;
- Python executor state;
- current task completion

with a safe ACL continuation point.

ACL resume still requires separate validation of:
- repo/workspace generation;
- active process tree;
- external-effect ledger;
- credential/policy generation;
- child-run settlement;
- verifier evidence.

## 12. Tool-error and retry semantics

The agent loop records `AgentError` into memory and often encourages the model to retry with a different approach. This is useful for model self-correction, but it is deliberately generic.

Recent issue #2689 asks for clearer documentation on recoverable versus unrecoverable custom-tool errors, illustrating that tool authors currently need to decide how errors are surfaced and whether the agent should retry.

### ACL implication

Tool/application retryability and **effect replay safety** are distinct.

A transient transport/tool error must not automatically imply that replay is safe after a possible side effect. ACL should classify:
- pre-effect validation failure;
- definitely-no-effect transport failure;
- effect completed;
- effect rejected;
- unknown-after-effect.

## 13. Observability

### Observed fact

smolagents exposes step timing/token usage, replayable memory, callbacks and OpenTelemetry integration through OpenInference/Phoenix-compatible tooling.

This is useful for diagnosing:
- model inputs/outputs;
- tool calls;
- step durations;
- token consumption;
- nested agent behavior.

### ACL implication

Observability is operator evidence, not independent acceptance. Trace data can also contain sensitive prompts, tool results, PII and credentials, so telemetry needs its own access/retention/redaction policy.

## 14. Benchmark design lessons

The upstream benchmark runner is useful reference material because it explicitly compares:
- code-agent action mode;
- tool-calling action mode;
- vanilla model mode.

It records model ID, answer, true answer, intermediate steps, token counts and timing, and can run examples concurrently.

However, ACL's later benchmark requires stronger identity/reproducibility controls than the example runner captures.

### Required ACL additions

Record:
- exact smolagents commit/release;
- exact model artifact/digest and tokenizer/template;
- provider/runtime/adapter revision;
- executor profile and realized sandbox;
- host hardware/driver/runtime;
- requested and realized context;
- tool/MCP schema versions;
- prompt/template revision;
- retry/timeouts;
- cache state;
- environment/credential profile;
- deterministic harness failure classification separate from model behavior.

### Harness-specific fixtures from Task 27

At minimum preserve:
1. #2197 — timeout returns after worker completion;
2. #1781 — shared managed-agent state during parallel calls;
3. #2166 — silent child failure / empty result;
4. #2424 — child summary leaks raw internal tool I/O;
5. #2456 — `final_answer_checks` bypassed under optimized Python;
6. #2566 — quadratic full-memory replay/context pressure;
7. #2305 — MCP trust/origin remains external;
8. local-executor escape/host-access behavior as an expected non-sandbox profile.

These should be scored as **harness/runtime/integration** failures, not model failures.

## 15. Reuse candidates for ACL

Useful mechanisms to consider later, without making an adoption decision:

1. **Thin MultiStepAgent-style loop** — model-facing logic stays simple.
2. **Separate CodeAgent and ToolCallingAgent profiles** — useful benchmark comparison surface.
3. **Narrow executor abstraction** — good place to inject ACL-owned containment.
4. **Step callbacks** — useful telemetry/policy/evidence hooks if protected externally.
5. **Final-answer check seam** — conceptually useful if reimplemented fail-closed outside worker authority.
6. **Explicit in-memory step objects** — useful semantic event representation, though not a durable checkpoint.
7. **Managed-agent-as-tool interface** — simple delegation syntax, provided invocation state and information-flow boundaries are strengthened.
8. **Broad model adapters** — useful harness portability surface for later qualification.
9. **MCP/Hub tool adapters** — useful interoperability beneath ACL trust and effect controls.
10. **OpenTelemetry instrumentation** — useful runtime evidence vocabulary.

## 16. Candidate ACL invariants derived from smolagents

1. Local interpreter restrictions never satisfy required sandboxing.
2. Executor implementation/profile is part of task and benchmark identity.
3. A timeout signal does not prove backing worker termination.
4. `interrupt`/cancel intent does not prove external effect settlement.
5. One managed-agent definition may have many child invocation identities; mutable state is invocation-scoped.
6. Child failure status is typed and never collapsed into empty success.
7. Child-to-parent summaries are explicit redacted exports, not raw-memory concatenation.
8. Parent capability cannot exceed child ceiling through delegation, and child cannot widen parent authority.
9. Production verifier/policy decisions never depend on Python `assert`.
10. Verifier failure/unavailability fails closed.
11. Agent memory is runtime context, not durable continuation authority.
12. Context compaction/truncation/summarization is behavior-bearing benchmark state.
13. Tool/provider/model/executor labels are not sufficient identity without exact revision/profile.
14. MCP/Hub tool origin is a trust and effect identity field.
15. Tool errors and effect replay safety are independently classified.
16. Telemetry is evidence, not acceptance authority.
17. Harness defects are scored separately from model-decision failures.

## 17. Explicit non-conclusions

Task 27 does **not** conclude that:
- smolagents should be adopted or forked;
- CodeAgent is superior for ACL;
- ToolCallingAgent is inferior or superior;
- any executor backend is the ACL sandbox choice;
- any model/provider/runtime should be assigned to an ACL role;
- upstream benchmark scores transfer to the user's future 32K benchmark;
- smolagents memory replaces ACL checkpoints or Vera persistent memory;
- MCP/Hub tools are trustworthy merely because smolagents can load them;
- `final_answer_checks` currently form a sufficient security/verifier boundary.

No Agno research was performed.

## Primary sources

- Repository: https://github.com/huggingface/smolagents
- Current main identity: https://github.com/huggingface/smolagents/tree/30bb1161095dbae2271e6bc3cc4c219cc3897a57
- Latest observed stable release v1.26.0: https://github.com/huggingface/smolagents/releases/tag/v1.26.0
- Package metadata: https://github.com/huggingface/smolagents/blob/main/pyproject.toml
- README / architecture and model/executor overview: https://github.com/huggingface/smolagents/blob/main/README.md
- Agent runtime: https://github.com/huggingface/smolagents/blob/main/src/smolagents/agents.py
- Agent memory: https://github.com/huggingface/smolagents/blob/main/src/smolagents/memory.py
- Security policy: https://github.com/huggingface/smolagents/blob/main/SECURITY.md
- Secure code execution docs: https://huggingface.co/docs/smolagents/en/tutorials/secure_code_execution
- Model docs: https://huggingface.co/docs/smolagents/reference/models
- Tool/MCP docs: https://huggingface.co/docs/smolagents/reference/tools
- Memory docs: https://huggingface.co/docs/smolagents/main/tutorials/memory
- Benchmark runner: https://github.com/huggingface/smolagents/blob/main/examples/smolagents_benchmark/run.py
- #2197 timeout lifecycle: https://github.com/huggingface/smolagents/issues/2197
- #1781 managed-agent shared state: https://github.com/huggingface/smolagents/issues/1781
- #2166 silent managed-agent failure: https://github.com/huggingface/smolagents/issues/2166
- #2305 MCP server trust: https://github.com/huggingface/smolagents/issues/2305
- #2424 managed-agent summary leakage: https://github.com/huggingface/smolagents/issues/2424
- #2456 optimized-Python final-answer-check bypass: https://github.com/huggingface/smolagents/issues/2456
- #2566 quadratic context replay: https://github.com/huggingface/smolagents/issues/2566
- #2689 custom-tool error/recovery semantics: https://github.com/huggingface/smolagents/issues/2689
- #2722 accepted pluggable-executor proposal: https://github.com/huggingface/smolagents/issues/2722

## Stop point

Task 27 stops after smolagents research, catalog/state/watchlist updates and research-only checkpoint verification. Agno remains the next task only.