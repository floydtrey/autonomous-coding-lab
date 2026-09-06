# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 10 — Codex deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Completed
- Research workspace initialized and evidence ladder established.
- Tasks 1–4 mapped recurring sources, active projects/people, research priority, and failed/abandoned/heavily redesigned attempts.
- Task 5 deep-researched **Pydantic AI** and the directly relevant official Pydantic AI Harness surfaces.
- Task 6 deep-researched **Cline** and its coding-agent architecture, authority, checkpoints, local-runtime/context and telemetry failure surfaces.
- Task 7 deep-researched **LangGraph** and its state/checkpoint, replay, interrupt, durability and retention failure surfaces.
- Task 8 deep-researched **promptfoo** as an independent evaluation/red-team/evidence layer.
- Task 9 deep-researched **Strands Harness SDK** across lifecycle, authorization, sandbox, persistence, interrupt, local-model and evaluation boundaries.
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before Task 10.
- Deep-researched **Codex** as ranked project #6, using the ACL/Vera end goal to control scope.
- Verified current canonical project identity at `openai/codex`, active Apache-2.0 status, and current main `6af345407d9c2a568da9d01b6c4b81a9e61495c0` when examined.
- Verified explicit sandbox policy variants and permission-profile semantics, including protected control-plane metadata (`.git`, `.agents`, `.codex`) inside otherwise writable workspaces.
- Verified that approval policy and sandbox authority are orthogonal: `approval_policy="never"` does not grant full authority, and an approval-required action that cannot ask does not silently escalate.
- Verified command-policy logic that refuses dangerously broad persistent approval prefixes such as generic shells/interpreters, package runners, `git`, `rm` and `sudo`.
- Verified live child-session authority refresh from the parent turn for sandbox/permissions, approval, cwd and related runtime state.
- Verified current role code/tests enforce one-way authority: roles can customize/reduce child capability but cannot replace parent sandbox, approval, provider/base URL, MCP, apps or notification authority.
- Verified hostile role regression tests that deliberately request danger-full-access, approval never, attacker provider/MCP/config surfaces and prove parent authority survives.
- Recorded a current documentation/code mismatch: subagent docs contain wording suggesting broader per-agent sandbox customization, while shipped role code/tests are more restrictive; source/tests control this task's conclusion.
- Verified current main fix #43147 separating authority inheritance from capability inheritance: fresh child sessions recompute experimental-context capability against the child's own model instead of blindly inheriting parent activation.
- Verified reviewer/delegate surfaces can be narrower than worker surfaces; Guardian reviewer uses a restricted extension surface while ordinary subagents can inherit broader parent extensions.
- Verified Guardian hardening commit `87628df7...`: root authorization evidence is retained/reconstructed across compaction and versioned so prior allows become stale when root instructions/verified authorization evidence changes.
- Verified Guardian hardening commit `4636819a...`: review/checkpoint reuse after compaction fails closed when required evidence is missing, unusable, incompatible or unknown.
- Verified recent sandbox-adapter hardening showing deny/environment semantics can be lost at platform bridges and therefore must be tested at realized child execution, not only in the high-level policy object.
- Verified `allow_symlinked_codex_home` is a narrow explicit trust exception, default-off and intended for top-level user-owned config rather than project-controlled authority.
- Verified current managed worktree behavior: per-chat working directories, detached HEAD by default, bounded cleanup with snapshots, and optional ignored-file copying that can include `.env`/secret files; recorded that workspace isolation and secret isolation are separate policies.
- Verified app-server Thread/Turn/Item identity, version-specific generated schemas, bounded queues/backpressure, durable/ephemeral threads, thread-owned restore state and explicit fork interruption markers for partial in-progress history.
- Verified project create/import APIs use idempotency keys and preserve the distinction between logical project deletion and deleting threads/directories/files.
- Verified current built-in Ollama/LM Studio support through the Responses provider path and explicit provider retry/idle configuration.
- Recorded open issue #30994 as current failure evidence that local Ollama setup can contaminate top-level/global provider/catalog state rather than remaining profile-scoped.
- Recorded open issue #42488 as current failure evidence that custom/Ollama providers can emit flattened dotted tool names that fail Codex namespace routing; no merged fix was claimed.
- Verified cancellation/process custody: command cancellation targets process groups, uses terminate-then-kill escalation, and bounds stdout/stderr drain tasks so orphaned pipes cannot hang completion indefinitely.
- Preserved the boundary that process settlement does not roll back filesystem/network/API/database effects and therefore does not replace ACL's external-effect ledger.
- Verified Codex OpenTelemetry support and sensitive user-prompt tracing control; did not find a promptfoo-like independent acceptance subsystem in Codex and preserved the need for external/ACL-owned validation.
- Recorded detailed evidence, candidate invariants, ACL regression-fixture ideas, open-failure boundaries and explicit non-conclusions in `projects/codex.md`.
- Preserved the decision boundary: Task 10 does **not** decide whether ACL should adopt/fork/wrap Codex, rank it against prior projects, or begin OpenHands research.

## Highest-value Codex findings for later comparison

1. Treat source-workspace writability and control-plane metadata authority as different permissions; protect Git, policy, agent-definition and verifier/evidence roots inside writable projects.
2. Keep approval policy and sandbox authority orthogonal; unattended execution must not imply broad authority.
3. Persist only narrow approval scopes; generic shells/interpreters/package runners are not safe reusable approvals.
4. Child authority is one-way: refresh from the live parent authority and permit only capability reduction/customization, never child-config widening.
5. Child model/runtime capabilities are recomputed separately from authority inheritance.
6. Test malicious role/config attempts explicitly rather than assuming a friendly child definition.
7. Reviewer/validator surfaces should generally be narrower than worker execution surfaces.
8. Bind approvals to versioned root authorization evidence; changes to task/objective/instructions/verified answers stale prior authorization.
9. Context compaction must preserve or invalidate authorization evidence; missing/incompatible evidence fails closed.
10. Test realized sandbox authority after every adapter bridge; deny/read/write/environment policy can be lost in serialization/platform translation.
11. Security/trust exceptions such as symlink allowances belong to user/admin-owned configuration, not repository-controlled state.
12. Worktree isolation and secret isolation are different policies; ignored-file copying requires explicit least-privilege projection.
13. Workspace/run identity should be distinct from Git branch/ref identity and preserve source baseline plus cleanup/restore evidence.
14. Resume may hydrate only owned/provenance-checked runtime settings; matching historical values are not automatically authoritative.
15. Partial/in-progress forks must remain explicitly interrupted/partial rather than being rewritten as clean continuity.
16. Persistent create/import/enqueue operations need caller-stable idempotency IDs; logical deletion and physical evidence/data destruction are separate contracts.
17. Local-model capability is exact model + runtime + adapter + wire/tool namespace + context/stream/retry configuration.
18. Provider/profile selection is scoped state; temporary local-provider setup must not silently mutate unrelated/global provider identity.
19. Cancellation must settle the whole local process tree/job plus pipes; killing the coroutine or top PID is insufficient.
20. Process settlement does not imply external-effect rollback or exactly-once semantics.
21. Bounded supervisor/server queues and explicit overload/backoff are preferable to unbounded buffering.
22. Persist the exact runtime/protocol schema version giving authority/state fields their meaning.
23. Runtime telemetry is useful evidence but sensitive prompt/tool data need explicit audience/redaction controls.
24. Codex remains a runtime/authority/process reference; it does not replace ACL's outer scheduler, effect ledger, independent verifier, memory governance or dependency governance.

## Queue status

- **Pydantic AI (#1): complete.** Detailed evidence: `projects/pydantic-ai.md`.
- **Cline (#2): complete.** Detailed evidence: `projects/cline.md`.
- **LangGraph (#3): complete.** Detailed evidence: `projects/langgraph.md`.
- **promptfoo (#4): complete.** Detailed evidence: `projects/promptfoo.md`.
- **Strands Harness SDK (#5): complete.** Detailed evidence: `projects/strands-harness-sdk.md`.
- **Codex (#6): complete.** Detailed evidence: `projects/codex.md`.
- **OpenHands (#7): next task only.** No OpenHands deep research was begun in Task 10.
- Remaining ranked queue stays unchanged until its own separately authorized task or later evidence justifies an explicit update.

## Next task

Deep-research **OpenHands** only.

Do not begin this task until separately instructed. For the next task, deep-research OpenHands as ranked project #7 with the same end-goal discipline: coding-agent/runtime architecture, sandbox/execution server, workspace/repository authority, tool/action contracts, provider/local-model abstraction, persistence/session/recovery, concurrency/cancellation, telemetry/evaluation/evidence, security and credential boundaries, recurring failure surfaces, project health, reusable components and concrete ACL/Vera lessons. Save evidence/catalog/state, commit research-only changes, and **stop before SWE-agent**.

## Later tasks
1. Deep-research SWE-agent/mini-swe-agent transition-aware slot, then continue the ranked project queue one project per separately authorized task.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 10 ended after Codex permission/sandbox, child authority/capability, Guardian approval provenance, sandbox-adapter, worktree/Git, thread/fork/resume, local-provider, process-cancellation, telemetry/evaluation-boundary, catalog/watchlist/state updates and next-task definition were completed. No OpenHands or SWE-agent research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
