# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 7 — LangGraph deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Completed
- Research workspace initialized and evidence ladder established.
- Tasks 1–4 mapped recurring sources, active projects/people, research priority, and failed/abandoned/heavily redesigned attempts.
- Task 5 deep-researched **Pydantic AI** and the directly relevant official Pydantic AI Harness surfaces.
- Task 6 deep-researched **Cline** and its current coding-agent architecture, authority, checkpoints, local-runtime/context and telemetry failure surfaces.
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before Task 7.
- Deep-researched **LangGraph** as ranked project #3, using the ACL/Vera end goal to control scope.
- Verified the current low-level stateful orchestration model: graph checkpoints, pending task writes, thread/checkpoint lineage, state history, subgraphs, interrupts, retries, timeouts and typed task/checkpoint/debug streams.
- Verified explicit durability modes (`sync`, `async`, `exit`) and preserved the boundary that persistence policy does not imply exactly-once external effects.
- Verified current node-level retry and timeout policies, including hard vs idle timeout and the cooperative-cancellation limitation for blocking/CPU-bound work.
- Verified interrupt/resume as replay semantics rather than stack continuation and recorded concurrent interrupt identity as a fail-closed requirement.
- Verified open issue #8579 where a scalar resume can ambiguously target one of multiple child interrupts grouped under a subgraph task.
- Verified open issue #8458 where replay from a checkpoint inside a subgraph can silently rerun the entire subgraph after parent-fork task identity changes break checkpoint namespace lookup.
- Verified open issue #8653 where a production-shaped config-injected checkpointer path can hydrate state from the wrong saver and `update_state` can commit an incorrectly empty base state forward.
- Verified open issue #8582 showing that a failed dynamic task can be considered resumable even though required `UntrackedValue` input was intentionally not checkpointed and cannot be reconstructed.
- Verified open issue #8039 and current loop code showing why `durability="sync"` must not be interpreted as exactly-once external execution; two proposed broad write-order fixes (#8050/#8055) were closed without merge.
- Verified retention/deletion lifecycle gaps: Postgres safe pruning remains open (#8531), and stale late writers can resurrect a deleted thread because deletion lacks generation/tombstone fencing (#7206).
- Verified that logical context management and physical checkpoint retention are separate concerns.
- Verified structured task/checkpoint/debug streaming and node trace policy while preserving the source warning that trace transforms are not a secret-redaction boundary.
- Recorded LangGraph evidence, ACL/Vera implications, candidate invariants, regression-fixture ideas and explicit non-conclusions in `projects/langgraph.md`.
- Preserved the decision boundary: Task 7 does **not** decide whether ACL should adopt, fork, wrap or independently implement LangGraph, and does not rank LangGraph against Pydantic AI or Cline.

## Highest-value LangGraph findings for later comparison

1. Separate replayable graph state from external-effect evidence; a durable checkpoint is not proof of exactly-once side effects.
2. Keep logical work identity, run/attempt identity, checkpoint identity, task/tool-call identity and parent lineage separate.
3. Checkpoint + pending-write separation is valuable because completed work inside a partially failed superstep can be represented independently.
4. Durability should be an explicit policy with precise failure semantics, not a binary checkpoint switch.
5. Human approval/input requests need stable interrupt IDs; concurrent ambiguous scalar resumes should fail closed.
6. Subgraph recovery identity must survive parent forks/retries rather than depend solely on regenerated ephemeral task IDs.
7. State mutation must hydrate and commit against one authoritative persistence source/version; production dependency-injection paths need their own regression tests.
8. Any task that can replay must have all required inputs persisted, deterministically reacquirable, or explicitly classified non-replayable.
9. Retry, hard timeout, idle timeout and cancellation reason belong in observable runtime policy rather than model prompts.
10. Physical checkpoint retention and deletion fencing are separate from model-context trimming/compaction.
11. Replay/time-travel, crash recovery, concurrent approvals and stale-writer deletion are high-value deterministic ACL fixtures.
12. LangGraph does not replace workspace snapshots, effect ledgers, sandboxing, credential policy, local-model capability verification or task acceptance gates.

## Queue status

- **Pydantic AI (#1): complete.** Detailed evidence: `projects/pydantic-ai.md`.
- **Cline (#2): complete.** Detailed evidence: `projects/cline.md`.
- **LangGraph (#3): complete.** Detailed evidence: `projects/langgraph.md`.
- **promptfoo (#4): next task only.** No promptfoo deep research was begun in Task 7.
- Remaining ranked queue stays unchanged until its own separately authorized task or later evidence justifies an explicit update.

## Next task

Deep-research **promptfoo** only.

Do not begin this task until separately instructed. For the next task, deep-research promptfoo as ranked project #4 with the same end-goal discipline: evaluation architecture, deterministic assertions/verifiers, agent/tool trajectory evaluation, red teaming/security testing, coding-agent fixtures, local/provider support, reproducibility, failure surfaces, project health, reusable components and concrete ACL/Vera lessons. Save evidence/catalog/state, commit research-only changes, and **stop before Strands Harness SDK**.

## Later tasks
1. Deep-research Strands Harness SDK, then continue the ranked project queue one project per separately authorized task.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 7 ended after LangGraph evidence, failure surfaces, reusable mechanism candidates, catalog/watchlist/state updates and next-task definition were completed. No promptfoo or Strands Harness SDK research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
