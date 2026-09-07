# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 21 — Microsoft Agent Framework deep research complete
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

## Task 21 work completed
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `watchlist.md`, and `sources.md` before beginning Task 21.
- Began from finalized Task 20 checkpoint `e61ff13cb040319c89d200e190c72411f4cdbcd5`, whose ancestry preserves the separate `docs/research/IDEAS.md` commit.
- Confirmed Task 21 scope as Microsoft Agent Framework only and preserved Google ADK as next-task-only.
- Verified canonical current upstream `microsoft/agent-framework` and pinned research to revision `afdc0db172d57edd50976d6f15168898f2284916`.
- Verified current Python umbrella release `1.17.0`, published 2026-09-03.
- Verified Microsoft Agent Framework is a supported GA successor/convergence path for AutoGen and Semantic Kernel, while preserving the distinction between predecessor transition evidence and claims of technical failure.
- Inspected current package/feature maturity and preserved mixed maturity below the GA umbrella: released core/orchestration surfaces coexist with beta provider/protocol packages and feature-level experimental Harness/Evals/Agent Hooks/FIDES/session-store/functional-workflow surfaces.
- Deep-researched `AgentSession` and provider/service continuation state.
- Preserved framework session identity, provider/service conversation identity, protocol task/context identity, ACL task/run identity and external-effect identity as separate domains.
- Deep-researched restart-safe session serialization, explicit state-type registration, file/session storage and portable opaque-ID handling.
- Deep-researched graph workflow execution as a modified Pregel/Bulk-Synchronous-Parallel superstep runtime with structured edge concurrency, ordered per-edge delivery, staged writes, commit boundaries and checkpoints.
- Deep-researched shared workflow state semantics: pending writes, committed state, commit, discard and current deep-copy isolation.
- Rechecked closed reproduced #7683 against current source and retained checkpoint/state aliasing as a fixed regression fixture rather than a current bug.
- Cross-checked open reproduced #7859 against current runner/state source and retained failed/cancelled-superstep pending-write leakage into later reused runs as a current-main state-consistency fixture.
- Deep-researched standard `WorkflowCheckpoint`: graph signature, checkpoint/parent IDs, committed state, messages, pending requests, iteration, metadata and version.
- Verified checkpoint restore fails on graph-signature mismatch and replaces state rather than blindly merging into arbitrary current state.
- Verified current file checkpoint storage uses root containment and temporary-write/`os.replace` behavior and restricts complex state restoration through known/registered state types.
- Recorded that iteration count is not unique checkpoint identity; parent-linked immutable checkpoint lineage is the stronger ordering identity.
- Recorded current runner behavior where checkpoint creation failure is warned/logged without failing the workflow, preserving a later ACL question about which task/effect classes may continue under degraded durability.
- Deep-researched open #7863 as a current resume API gap: checkpoint hydration and new input are two operations rather than one atomic restore+validate+continue transition.
- Deep-researched open #7809 as a separate Foundry-hosted long-running recovery gap between workflow checkpoint progress and durable/client-visible response progress.
- Derived that execution-state durability, output/evidence delivery durability, workspace state and external-effect settlement are separate recovery planes.
- Deep-researched the first-party Durable Extension and verified Microsoft explicitly distinguishes ordinary workflow checkpoint storage from distributed Durable Task execution.
- Recorded Durable Extension capabilities for distributed persistent sessions, workflow/orchestration recovery, long waits, durable workers, deterministic orchestration and reliable streaming with an appropriate broker.
- Preserved the boundary that durable orchestration replay is not universal proof that arbitrary external effects occurred exactly once.
- Deep-researched the Python function/tool loop and occurrence identity.
- Preserved provider/service `call_id` as correlation while framework `Content.id` identifies one locally actionable occurrence.
- Deep-researched `ToolApprovalMiddleware`, including standing rules scoped by tool name, exact canonicalized arguments and hosted `server_label`.
- Verified current documented Harness/Skills warning that built-in auto-approval helpers can match solely by tool name, allowing a colliding registered tool name to bypass the intended human approval boundary.
- Derived that ACL authority-bearing tool identity must include trusted origin/provider/extension and schema/argument identity rather than display name alone.
- Deep-researched experimental AGENT-HOOKS-0.1 enforcement.
- Verified current Python support for fail-closed interception, transform write-back, buffered streaming and verdict-before-durability behavior.
- Inspected current .NET Agent Hooks source and proposed ADR 0035; preserved maturity accurately as alpha/experimental/proposed while extracting the useful structural principle of indivisible host-owned enforcement composition.
- Preserved Agent Hooks as cooperative policy/interception rather than OS/process isolation.
- Deep-researched experimental FIDES current failure evidence.
- Cross-checked open reproduced #7890 against current source and retained unbounded abandoned pending-policy-approval state as a scoped current lifecycle/availability fixture.
- Deep-researched open reproduced .NET #7872 as a related but distinct dangling tool/approval closure problem after cancellation/restart.
- Derived explicit pending approval/effect/job states including pending, approved/rejected, expired, abandoned, cancelled, consumed/reconciled and garbage-collectable.
- Deep-researched Agent Harness execution boundaries.
- Verified current `ShellPolicy` explicitly states regex command allow/deny is not a security boundary and intentionally ships no default denylist.
- Deep-researched .NET LocalCodeAct defense-in-depth: subprocess execution, no host env inheritance by default, explicit env projection, no shell invocation, AST validation and resource limits while explicitly rejecting the claim that it is a security sandbox.
- Preserved Docker/Hyperlight/external containment as separate realized sandbox tiers.
- Deep-researched local/provider portability through current Ollama/native and OpenAI-compatible paths.
- Preserved exact provider/model/runtime/tool/stream/context behavior as deployment-profile state rather than assuming common Agent Framework APIs imply parity.
- Re-read closed #6942 and maintainer resolution; recorded Ollama automatic retry parity as an intentional host-owned design boundary, not a current bug.
- Derived that retry behavior belongs in the exact deployment/effect profile and must distinguish pre-response retry from partial-stream/effect replay ambiguity.
- Deep-researched MCP integration and modern Tasks support.
- Rechecked still-open #7824 and found its original current-status implication partly stale.
- Inspected merged/released PR #7774, which explicitly migrates .NET long-running MCP tasks to the 2026-07-28 `io.modelcontextprotocol/tasks` extension, upgrades the C# MCP SDK and adds task polling/cancellation bounds.
- Preserved #7824 only as an interoperability confirmation/follow-up rather than claiming current MAF lacks MCP 2026.
- Deep-researched A2A client/hosting boundaries and current documentation that task/thread/context/session IDs are routing handles rather than bearer credentials.
- Deep-researched accepted hosting ADR 0027 and preserved application/host ownership of routes, authentication, authorization, externally supplied state IDs, destructive command effects, background work and durable state placement.
- Preserved immutable continuation IDs versus mutable conversation heads as distinct concurrency models; mutable heads require single-writer coordination.
- Deep-researched native OpenTelemetry and sensitive-data controls; preserved runtime telemetry as operator evidence rather than independent acceptance proof.
- Deep-researched current experimental provider-agnostic evaluation API, including local deterministic checks, expected tool calls/output, last-turn/full-trajectory evaluation and custom splitters.
- Derived separate ACL benchmark evidence classes for deterministic harness correctness, stochastic model reliability, semantic quality and runtime telemetry.
- Wrote detailed evidence, current/fixed failure matrix, candidate invariants, reuse candidates, primary sources and explicit non-conclusions to `projects/microsoft-agent-framework.md`.
- Prepared 16 Task 21 catalog records to append after the 181 Task 20 records.
- Preserved task boundary: no Google ADK research, framework adoption, Durable Task choice, model/provider assignment, sandbox selection, benchmark execution, ACL/Vera architecture/governance redesign or worker/model execution was begun.

## Highest-value Microsoft Agent Framework findings for later comparison
1. Framework-local session identity and provider/service continuation identity are explicitly separate; this maps well to ACL/Vera identity design.
2. Package/feature maturity must be tracked below the umbrella GA framework label.
3. Pregel-like supersteps provide useful deterministic state boundaries without scripting model reasoning.
4. Checkpoint identity is immutable and parent-linked; iteration number alone is not authoritative continuation identity.
5. Checkpoints are bound to a workflow graph signature and fail on incompatible graph restore.
6. Fixed #7683 is a strong immutable-snapshot regression fixture; current deep-copy behavior shows active hardening.
7. Current #7859 demonstrates failed/cancelled transactional state must be explicitly discarded before a workflow/state owner is reused.
8. Current #7809 demonstrates execution checkpoint durability and output/evidence delivery durability are separate settlement planes.
9. Current #7863 reinforces resume as a first-class atomic transition rather than a loose load/mutate/run sequence.
10. Standard workflow checkpoints and the first-party Durable Task extension are explicitly different durability levels.
11. Distributed durable replay still does not replace effect-level idempotency/reconciliation.
12. Provider `call_id` is not globally stable effect identity; locally actionable occurrences need their own durable identity.
13. Tool approvals can use exact arguments/server boundaries, but current name-only auto-approval helpers provide a concrete authorization-identity warning.
14. Agent Hooks provide high-value fail-closed/verdict-before-durability patterns, while remaining experimental/cooperative rather than sandbox security.
15. Current #7890/#7872 show pending approval/tool state needs explicit terminal/expiry/cleanup/drain semantics.
16. Shell regex filtering is explicitly rejected upstream as a security boundary; sandbox/process/credential authority remains separate.
17. Local CodeAct demonstrates useful minimal-env/process/resource controls while explicitly requiring external containment for untrusted generated code.
18. Native Ollama support is real, but provider/model capabilities and retry behavior are not normalized; exact deployment profiling remains required.
19. Merged #7774 updates .NET MCP Tasks to 2026-07-28; protocol-era/extension support must be checked against current code rather than stale issue descriptions.
20. A2A/MCP/hosting identifiers are routing/state handles, not authentication; host-owned principal authorization must precede state lookup/mutation.
21. Immutable continuation points can branch; mutable conversation/project heads require single-writer fencing.
22. OpenTelemetry and evaluation are useful evidence substrates but do not replace an independent ACL verifier.
23. Full-trajectory evaluation is directly relevant to the user's future long-horizon 32K model/harness benchmark.
24. Microsoft Agent Framework does not replace ACL project/task/effect ownership, external-effect ledger, independent verifier, credential broker, workspace policy or Vera epistemic memory governance.

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
- **Microsoft Agent Framework (#17): complete.** Detailed evidence: `projects/microsoft-agent-framework.md`.
- **Google ADK (#18): next task only.** No Google ADK research was begun in Task 21.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **Google ADK** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant agent/runtime architecture, tool/capability boundaries, workflows/multi-agent execution, sessions/state/memory, local/provider portability, MCP/A2A/interoperability, evaluation/observability, safety/security/current failure evidence, deployment/runtime boundaries, and reusable mechanisms. Save report/catalog/state/watchlist, make a research-only commit, and stop before LiteLLM.

## Later tasks
1. Google ADK, then the remaining ranked active-project queue one task at a time.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after individual work is complete.

## Stop point

Task 21 ended after Microsoft Agent Framework's current identity/maturity, AutoGen/Semantic Kernel convergence, session/provider identity, workflow/superstep/state semantics, checkpoint lineage and restore, standard-versus-distributed durability, current/fixed recovery failures, tool/approval occurrence identity, policy/interception, Harness execution/sandbox boundaries, Ollama/provider portability, retry ownership, MCP 2026 Tasks migration, A2A/hosting authority, OpenTelemetry and evaluation evidence were researched. No Google ADK research, cross-project winner selection, dependency decision, benchmark execution, ACL/Vera architecture/governance change or worker/model execution was begun.
