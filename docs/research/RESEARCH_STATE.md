# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 12 — SWE-agent / mini-swe-agent transition-aware deep research complete
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
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before Task 12.
- Deep-researched the **SWE-agent / mini-swe-agent transition-aware slot** as ranked project #8, including SWE-ReX because upstream SWE-agent explicitly moved execution infrastructure into that runtime during its 1.0 redesign.
- Verified authoritative status: SWE-agent is maintenance-only and explicitly names mini-swe-agent as its successor for new use.
- Verified SWE-agent 1.0 was nearly rewritten from scratch and moved code execution into SWE-ReX, reducing the former `SWEEnv` to a thin runtime wrapper and separating agent logic from infrastructure.
- Verified SWE-ReX exposes a deployment/runtime boundary supporting local/remote execution, file operations, one-off commands and persistent interactive sessions while allowing the agent layer to remain replaceable.
- Verified current mini-swe-agent main `04d809ceab9df28f9adaed044884180159172930` remains active and package metadata classifies the project as Alpha.
- Resolved a current-generation documentation mismatch: older FAQ language describes text/fenced-code parsing, while mini v2 migration docs and current source establish native Bash tool calling as the default; legacy text parsing remains available as a compatibility path.
- Verified current mini default control flow is deliberately small: model query → execute action(s) → format observation → append history, with deterministic step/cost/run/format limits outside prompt prose.
- Verified the current default model advertises one typed `bash(command)` tool, validates tool name/JSON arguments, returns corrective `FormatError` feedback and preserves provider `tool_call_id` into the result relationship.
- Preserved the critical boundary that a single Bash schema is low scaffold complexity, not least privilege: Bash can invoke arbitrary accessible interpreters, files, network, Git and subprocesses.
- Verified independent per-action execution remains a deliberate simplification: cwd/environment changes are not persistent by default, while richer persistent sessions remain available underneath through SWE-ReX when explicitly needed.
- Verified mini's default `local` environment is explicitly unsandboxed and executes with the host process environment (`os.environ` plus configured additions); recorded this as an unacceptable ambient-credential default for a future privileged ACL/Vera production worker.
- Verified Docker execution forwards only explicitly selected environment variables but still accepts caller-controlled Docker run arguments; recorded that container transport and permission policy are separate contracts.
- Recorded that current Docker cleanup is launched asynchronously/background rather than synchronously proving container settlement; derived `cleanup_requested != cleanup_settled` as a future ACL invariant.
- Recorded closed issue #826 as concrete process-tree failure evidence: the earlier timeout path could kill the shell while leaving agent-spawned grandchildren running; current local execution now creates a POSIX session and kills the process group on timeout.
- Recorded a later process-group disappearance race report as a useful cleanup regression fixture but did **not** classify it as a confirmed production bug because the upstream discussion disputed whether the reproduction demonstrated an encountered failure.
- Recorded open issue #874 as version-scoped evidence that an OpenAI-compatible provider can stall mid tool-call stream beyond mini's bounded outer run, showing loop-level deadlines cannot replace provider/transport idle/request timeouts.
- Recorded open issue #872 as version-scoped evidence that the same provider-issued tool-call ID can produce repeated completed results, reinforcing that transcript correlation IDs are not durable exactly-once/effect identities.
- Recorded open issue #889 as current evidence of intentional single-tool simplicity creating extensibility pressure because `[BASH_TOOL]` is hardcoded in the default LiteLLM query path.
- Recorded open RFC #953 as current discussion evidence that default mini has no comprehensive deterministic pre-execution authorization layer; kept community proposals/comments distinct from shipped behavior and did not attribute maintainer authority without evidence.
- Recorded open issue #950 as evidence that raw timeout wording can shape model behavior into compensation/gaming loops; separated operator telemetry from model-facing actionable feedback.
- Verified local-model support through LiteLLM plus provider/api-base/model-registry configuration, including Ollama and concrete vLLM examples; preserved exact model + runtime + adapter + endpoint + context/tool/timeout/retry identity as the real capability unit.
- Verified mini retains both native tool-calling and text-based action encodings, making capability-based fallback possible for local runtimes rather than assuming native tool calling always works.
- Verified model retry is bounded/configurable and separate from action/effect retry; default helper uses exponential backoff and abort classes for authentication/permission/context/unsupported-param failures.
- Verified mini saves rich trajectories after loop iterations, including model/environment config, raw provider/tool evidence and terminal status, but found no durable resume/checkpoint mechanism; classified trajectory persistence as evidence, not safe continuation authority.
- Verified model-facing command output is bounded/truncated while richer raw output can remain in evidence fields, supporting separate context-budget and audit-retention planes.
- Recorded current SWE-agent maintenance commit `3ea751c087f32b16e039a2233dd6eefecef325d5` as evaluation-harness correctness evidence: a bad SWE-bench subset mapping could invalidate evaluation independently of agent quality.
- Recorded mini's explicit dependency exclusion of compromised LiteLLM versions 1.82.7/1.82.8 as direct supply-chain-maintenance evidence without drifting into the later LiteLLM research slot.
- Recorded detailed sources, current failure boundaries, migration mechanisms, candidate invariants, future ACL regression fixtures and explicit non-conclusions in `projects/swe-agent-mini-swe-agent.md`.
- Preserved the decision boundary: Task 12 does **not** decide whether ACL should adopt/fork/wrap mini-swe-agent or SWE-ReX, choose a cross-project winner, redesign ACL governance, or begin llama.cpp research.

## Highest-value SWE-agent / mini-swe-agent findings for later comparison

1. Simplifying the agent loop can be a deliberate successful redesign when deterministic complexity is moved into explicit runtime owners rather than prompt prose.
2. SWE-agent first extracted execution infrastructure into SWE-ReX; mini then reduced the model-facing scaffold further. The responsibilities did not disappear.
3. Keep the worker action vocabulary small enough to preserve model-native reasoning; make every added abstraction justify its cost with ACL-specific evidence.
4. Backend sophistication does not need to become model-facing sophistication: local, Docker, remote and richer runtimes can sit under the same small action contract.
5. Independent actions are a strong default; persistent shell/REPL/browser sessions should be explicit leased resources rather than hidden ambient state.
6. One Bash tool is low schema complexity, not narrow authority.
7. Local execution is not automatically trusted or safe; mini's default local path is full host execution with ambient environment access.
8. Child/worker environment should be explicit and minimal rather than inheriting the supervisor's entire environment.
9. Container/runtime selection and permission policy are separate; mounts, network, credentials, user and resource settings remain authority-bearing configuration.
10. `cleanup_requested` is not `cleanup_settled`; environment teardown needs observable completion/error state.
11. Tool timeout must settle the whole owned process tree. Returning a timeout message while grandchildren survive is false completion.
12. Every blocking plane needs its own timeout/cancellation owner; an outer agent-loop wall clock cannot interrupt a stalled provider stream by itself.
13. Provider/tool correlation IDs are not enough for external effects; ACL needs durable idempotency/effect state.
14. Keep deterministic authorization around the effect boundary rather than enlarging the reasoning prompt to describe permissions.
15. Model-facing error/timeout feedback and operator/audit telemetry are distinct representations.
16. Native tool calling is a verified capability, not a universal requirement; retain a fallback action encoding for local runtimes that fail tool-call probes.
17. Retry layers remain separate: provider retry cannot silently become tool/effect replay.
18. Trajectory evidence is valuable but is not a checkpoint, workspace snapshot or permission to resume.
19. Bounded model context and richer audit evidence can coexist; do not feed every raw log back into a small local model.
20. Evaluator/benchmark adapters are trusted evidence code and their failures must be classified separately from worker/model failures.
21. Minimal worker code still has a large dependency/runtime trust base; dependency provenance and blocked versions remain security controls.
22. mini is strongest as a minimal worker-loop/reference baseline; SWE-ReX is strongest as an execution-runtime separation reference. Neither replaces ACL's scheduler, dependency gates, effect ledger, protected verifier, credential governance, durable recovery or Vera memory governance.

## Queue status

- **Pydantic AI (#1): complete.** Detailed evidence: `projects/pydantic-ai.md`.
- **Cline (#2): complete.** Detailed evidence: `projects/cline.md`.
- **LangGraph (#3): complete.** Detailed evidence: `projects/langgraph.md`.
- **promptfoo (#4): complete.** Detailed evidence: `projects/promptfoo.md`.
- **Strands Harness SDK (#5): complete.** Detailed evidence: `projects/strands-harness-sdk.md`.
- **Codex (#6): complete.** Detailed evidence: `projects/codex.md`.
- **OpenHands (#7): complete.** Detailed evidence: `projects/openhands.md`.
- **SWE-agent / mini-swe-agent (#8): complete.** Detailed evidence: `projects/swe-agent-mini-swe-agent.md`.
- **llama.cpp (#9): next task only.** No llama.cpp deep research was begun in Task 12.
- Remaining ranked queue stays unchanged until its own separately authorized task or later evidence justifies an explicit update.

## Next task

Deep-research **llama.cpp** only.

Do not begin this task until separately instructed. For the next task, deep-research llama.cpp as ranked project #9 with the same end-goal discipline: local-runtime architecture, constrained JSON/tool-call grammar and parser behavior, model/template/tool compatibility, context/KV/cache semantics, cancellation/concurrency/server behavior, backend/hardware portability, version/config reproducibility, recurring failure surfaces, project health, reusable components and concrete ACL/Vera lessons. Save evidence/catalog/state, commit research-only changes, and **stop before OpenAI Agents SDK**.

## Later tasks
1. Deep-research OpenAI Agents SDK after llama.cpp, one project per separately authorized task.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 12 ended after the SWE-agent→SWE-ReX→mini-swe-agent transition, current mini v2 tool/control-flow architecture, independent-action design, execution/sandbox/ambient-environment boundaries, process-tree timeout and cleanup semantics, provider-stream and duplicate-tool-call failure evidence, local-model adapter behavior, trajectory-versus-checkpoint distinction, benchmark/evaluator correctness, supply-chain evidence, catalog/watchlist/state updates and next-task definition were completed. No llama.cpp or OpenAI Agents SDK research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
