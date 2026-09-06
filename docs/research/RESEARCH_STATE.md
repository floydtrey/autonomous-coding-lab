# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 5 — Pydantic AI deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Completed
- Research workspace initialized and research process/evidence ladder established.
- Mapped recurring sources, verified active projects/people, ranked the watchlist, and mapped failed/abandoned/heavily redesigned attempts in Tasks 1–4.
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, `watchlist.md`, Task 3 ranking evidence and Task 4 transition evidence before beginning Task 5.
- Deep-researched **Pydantic AI** as ranked project #1, including the official `pydantic-ai-harness` only where it directly overlaps ACL/Vera's end goals.
- Verified core architecture boundaries across agent/run lifecycle, graph orchestration, normalized messages, tools/toolsets, structured output, providers/models/profiles, capabilities, durable execution and observability.
- Verified that Pydantic AI distinguishes multiple retry layers and that older Ollama failures demonstrate why deterministic capability mismatches should not be handled by simply increasing model retries.
- Verified current self-hosted Ollama support and the more important capability-profile behavior: nominal OpenAI/API compatibility is not treated as proof of native structured-output enforcement.
- Verified current concurrency/cancellation guidance emphasizing explicit ownership, cancel-and-drain teardown, task groups, bounded timeouts and cleanup assertions.
- Verified code-first Pydantic Evals and OpenTelemetry/Logfire trajectory instrumentation, including span-based evaluation of tool/execution behavior rather than only final outputs.
- Expanded narrowly into the official **Pydantic AI Harness** because it directly implements long-running/coding-agent mechanisms ACL is considering; did not research unrelated Pydantic products.
- Verified Harness maturity: MIT licensed, actively maintained, official, but Alpha/0.x with rapid release/API churn; strict typing, 100% branch coverage and mutation testing on filesystem/shell provide positive engineering signal without proving production maturity.
- Verified FileSystem workspace containment, symlink checks, protected patterns and stale-write hashes, while preserving its documented pathname/OS-isolation limitations.
- Verified Shell command/process/env controls and its explicit warning that command allow/deny lists are not a security boundary. Historical env-secret exposure (#281), filesystem path leakage (#616) and shell recoverability (#622) are closed/fixed examples of dogfooding/adversarial hardening.
- Verified `Planning` as useful model-owned working state but not an authoritative read-only or dependency-control boundary.
- Verified `SubAgents` context isolation, no tool inheritance by default, per-child budgets/timeouts and explicit capability sharing; dependency/credential least privilege remains application-owned.
- Verified a recent capability-composition hardening change showing that generic merging can widen `Shell`/`FileSystem`/sub-agent authority; recorded fail-closed explicit composition as a high-value ACL invariant candidate.
- Verified `StepPersistence` as the strongest direct ACL checkpoint/evidence reference: append-only events, complete/interrupted snapshots, tool-effect lifecycle records, lineage IDs and explicit `unknown_after_crash` handling, while refusing to label message-history persistence a full graph/workspace/capability checkpoint.
- Verified Harness Memory as bounded, CAS/idempotency-aware and application-namespaced but explicitly untrusted on re-entry; open issue #103 confirms delayed prompt-injection/artifact scanning remains a recognized gap.
- Verified compaction strategy that prefers deterministic clear/dedupe/trim before lossy summarization and preserves tool-call/result pairing.
- Verified open tool-guardrail issue #519 as a concrete example that human approval can create a policy hole if approval semantics bypass later mandatory guards.
- Recorded detailed evidence and ACL/Vera implications in `projects/pydantic-ai.md` and added Task 5 catalog/watchlist/state updates.
- Preserved the decision boundary: Pydantic AI remains a high-value reference, but this task did **not** decide whether ACL should depend on, fork, adapt or independently reimplement Pydantic AI/Harness components.

## Highest-value Pydantic AI findings for later comparison

1. Explicit model/runtime capability profiles are preferable to scattered provider-name conditionals.
2. Typed validation, approval and execution authority must remain separate facts.
3. Retry layers need separate reason categories, owners, limits and attempt telemetry.
4. Authority-bearing configuration must compose explicitly and fail closed; generic union/merge is unsafe.
5. Child agents should receive explicit capability grants and budgets rather than ambient parent authority.
6. `StepPersistence`'s settled/interrupted snapshots plus `unknown_after_crash` tool-effect ledger are directly relevant to ACL's documentation/recovery design.
7. Persistent memory should remain lower-trust data with application-owned namespace, concurrency/idempotency semantics and provenance/security controls.
8. Deterministic context reclamation should precede lossy summarization.
9. Trajectory/span evaluation should complement final-result validation.
10. Filesystem/shell application guards are useful, but OS/container/credential isolation remains a separate security layer.

## Queue status

- **Pydantic AI (#1): complete.** Detailed file: `projects/pydantic-ai.md`.
- **Cline (#2): next task only.** No Cline deep research was begun in Task 5.
- Remaining ranked queue stays unchanged until its own separately authorized task or later evidence justifies an explicit update.

## Next task

Deep-research **Cline** only.

Do not begin this task until separately instructed. For the next task, deep-research Cline as ranked project #2 with the same end-goal discipline: coding-agent architecture, model/harness control split, file/edit semantics, destructive-action safety, local-model/provider support, approvals/authority, context/state/recovery, evaluation/telemetry, recurring failure surfaces, project health, reusable components and concrete ACL/Vera lessons. Save evidence/catalog/state, commit research-only changes, and **stop before LangGraph**.

## Later tasks
1. Deep-research LangGraph, then continue the ranked project queue one project per separately authorized task.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 5 ended after Pydantic AI/Pydantic AI Harness evidence, failure surfaces, reusable mechanism candidates, catalog/watchlist updates and next-task definition were completed. No Cline or LangGraph research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
