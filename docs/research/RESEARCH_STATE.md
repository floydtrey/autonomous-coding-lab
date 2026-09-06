# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 6 — Cline deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Completed
- Research workspace initialized and evidence ladder established.
- Tasks 1–4 mapped recurring sources, active projects/people, research priority, and failed/abandoned/heavily redesigned attempts.
- Task 5 deep-researched **Pydantic AI** and the directly relevant official Pydantic AI Harness surfaces.
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before Task 6.
- Deep-researched **Cline** as ranked project #2, using the ACL/Vera end goal to control scope.
- Verified Cline's current stateless-agent / stateful-core architecture split and local-hub/session lifecycle model.
- Verified Plan mode's evolution from prompt-level restraint toward runtime `beforeTool` blocking because weaker models routinely attempted mutations; preserved the current blacklist's documented bypass limits and open issue #13586.
- Verified approval/auto-approval semantics, including permissive SDK behavior for unlisted tools and the need to distinguish workflow approval from execution authority.
- Verified an open embedded-provider authority mismatch (#13146) showing that wrapping another agent runtime can introduce a second tool/permission/cwd system outside the wrapper's normal controls.
- Verified current `apply_patch` safety behavior and the recent existing-file overwrite regression/fix (`adbfbd97...`).
- Verified `.clineignore` is explicitly not a security boundary and the newer PreToolUse enforcement pattern still documents shell-parser/symlink/YOLO limitations.
- Verified checkpoint design and recent failures/fixes: missed checkpoint creation across surfaces, restart/compaction/run-number identity drift, missing untracked files, safe full-workspace rewind, and branch-history protection during restore.
- Verified checkpoint restore now refuses when HEAD moved and uses Git compare-and-swap to close the check-to-reset race (`89c2efa9...`).
- Verified local Ollama support must use native runtime semantics for `num_ctx`; the generic OpenAI-compatible route previously left Ollama at a 4096-token server default and broke Cline prompts.
- Verified explicit model capability metadata while recording that unknown/empty capability lists can intentionally fail open for tool/image support for compatibility.
- Verified context-overflow recovery that classifies the failure, forces deterministic compaction, proves shrinkage, retries once and then terminates/escalates rather than blindly looping.
- Verified context/compaction is a state-correctness problem, not only token optimization; recent bugs involved wrong provider endpoints, ignored compacted sidecars, legacy history migration and first-prompt truncation.
- Verified abort/restart durability work showing cancellation must flush durable session context and must not kill unrelated resident sessions in the hub.
- Verified runtime `maxConsecutiveMistakes` and repeated-identical-tool-call loop detection with soft recovery and hard escalation thresholds.
- Verified structured telemetry for sessions, agents, tool calls, provider errors, compaction, mistake limits, sub-agents, timeouts and Plan-mode policy blocks.
- Recorded Cline evidence, ACL/Vera implications, candidate invariants, failure fixtures and explicit non-conclusions in `projects/cline.md`.
- Preserved the decision boundary: Task 6 does **not** decide whether ACL should adopt, fork, wrap or independently implement Cline components, and does not rank Cline against Pydantic AI.

## Highest-value Cline findings for later comparison

1. Separate replaceable/stateless model execution from deterministic stateful session/project ownership.
2. A read-only role should receive actually read-only capabilities; prompt rules and shell blacklists are defense-in-depth, not authority boundaries.
3. Approval UI, model command classification and execution authority must remain separate layers.
4. Wrapping another agent runtime creates a second authority system unless tool/cwd/credential/approval ownership is explicitly bridged.
5. File safety rules require authoritative state at execution time; parser intent is insufficient if the executor does not load target state.
6. Workspace checkpoint identity must survive retries, internal continuations, compaction and restart, and restore itself needs fail-closed concurrency/history protection.
7. Conversation state, workspace snapshots and external side-effect evidence should remain separate recovery dimensions.
8. Local compatibility should be recorded as model + runtime + adapter + settings; generic API compatibility can hide critical backend controls such as Ollama `num_ctx`.
9. Deterministic failure recovery should classify the failure, transform state with measurable progress, spend a small retry budget and then stop/escalate.
10. Mistake/loop detection belongs in observable harness behavior rather than a giant prompt rulebook.
11. Stable session/agent/run/tool-call IDs are foundational for multi-worker telemetry, recovery and troubleshooting.
12. Long-running persistence needs both logical retention and physical storage bounds.

## Queue status

- **Pydantic AI (#1): complete.** Detailed evidence: `projects/pydantic-ai.md`.
- **Cline (#2): complete.** Detailed evidence: `projects/cline.md`.
- **LangGraph (#3): next task only.** No LangGraph deep research was begun in Task 6.
- Remaining ranked queue stays unchanged until its own separately authorized task or later evidence justifies an explicit update.

## Next task

Deep-research **LangGraph** only.

Do not begin this task until separately instructed. For the next task, deep-research LangGraph as ranked project #3 with the same end-goal discipline: state/checkpoint model, durable execution, interrupts/resume, retries, lifecycle ownership, concurrency/cancellation, subgraphs/agents, storage, observability/evaluation hooks, failure surfaces, project health, reusable components and concrete ACL/Vera lessons. Save evidence/catalog/state, commit research-only changes, and **stop before promptfoo**.

## Later tasks
1. Deep-research promptfoo, then continue the ranked project queue one project per separately authorized task.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 6 ended after Cline evidence, failure surfaces, reusable mechanism candidates, catalog/watchlist/state updates and next-task definition were completed. No LangGraph or promptfoo research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
