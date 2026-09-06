# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 11 — OpenHands deep research complete
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
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before Task 11.
- Deep-researched **OpenHands** as ranked project #7, using the ACL/Vera end goal to control scope.
- Verified the current OpenHands system is split across product/control-center, runtime/Agent Server and automation responsibilities rather than one monolith.
- Verified `OpenHands/software-agent-sdk` owns the canonical agent runtime surfaces: agents, tools, conversations, workspaces, events, REST/WebSocket API and browser-compatible TypeScript client.
- Verified current conversation state explicitly persists lifecycle/status, workspace, agent configuration, branch HEAD, stats, secret registry, hooks and agent-specific state outside prompt prose.
- Verified branch-aware append-oriented event history with an authoritative active `leaf_event_id` and derived active-branch view.
- Recorded closed high-priority issue #4487 as crash-recovery evidence that persisting an action event without the matching advanced HEAD can orphan a recovery result/error onto the wrong branch and make future turns unrecoverable.
- Extracted the candidate invariant that every tool result/rejection/recovery error must remain paired with its originating action on the authoritative branch.
- Verified Agent Server `ConversationLease` uses owner identity, monotonic generation, TTL, host/PID evidence, file locking and guarded-write fencing.
- Connected current lease/fencing design to closed split-brain issue #2966, where multiple Agent Server processes could previously attach to the same active persisted conversation.
- Verified startup can lazily retain idle conversation metadata while applying special recovery treatment to conversations persisted as `RUNNING`.
- Verified `ParallelToolExecutor` uses explicit declared-resource locking for concurrent tools and warns that tool resource declarations must be correct for the mechanism to be safe.
- Recorded open issue #4777 as deterministic evidence that cancellation can become stale while a tool waits for a resource lock, allowing a queued file/terminal/browser action to start after user interruption.
- Recorded current runtime main `fe91d7dfc94d299e3751acb2b0c80ccbc582623c`, whose regression tests demonstrate that async cancellation cannot forcibly stop synchronous work blocked in worker threads and can leave zombie-thread/lifecycle failures.
- Preserved the distinction between cancellation request and actual execution settlement.
- Verified OpenHands workspace backends include local, Docker, Apptainer, cloud and API-remote implementations.
- Verified Docker workspace configuration can forward environment variables, mount arbitrary volumes, select networks, expose ports/GPU and manage container lifecycle; recorded that container transport is not itself a least-privilege policy.
- Verified optional conversation-specific Git worktree creation reduces checkout collision but remains distinct from sandboxing, worker identity and external-effect recovery.
- Verified explicit confirmation policy (`AlwaysConfirm`, `NeverConfirm`, `ConfirmRisky`) and security analyzer surfaces; preserved that confirmation/risk classification does not replace actual filesystem/process/network authority.
- Deep-researched credential design issue #4288 because it directly overlaps Vera: durable state should converge toward credential references while runtime-visible delivery is an explicit bounded plaintext authority decision and brokered delivery keeps the provider secret outside the worker.
- Kept #4288 correctly labeled as design/target architecture rather than a fully shipped guarantee.
- Recorded the design's catalog of historical credential leak/coupling paths as evidence that redaction-only fixes do not solve secret-bearing serializable state structurally.
- Verified current Agent Server code does include credential-binding and persisted-secret scrubbing paths, while avoiding the unsupported claim that the full reference-only design is complete.
- Recorded closed issue #3815 as evidence that hidden ambient profile state under `~/.openhands` can defeat a supposedly fresh persistence root unless all state roots participate in isolation.
- Verified the current LLM abstraction adds canonical model identity, feature/capability lookup/overrides, provider runtime metadata, retry/timeout configuration and an explicit minimum-context expectation on top of LiteLLM.
- Recorded open Ollama issue #4255 as evidence that configured timeout state and realized wire/provider behavior can diverge.
- Verified Agent Server observability deliberately separates high-fidelity LLM completion logging, Laminar/OpenTelemetry tracing and allowlisted product telemetry with different sensitivity/purpose.
- Verified the SDK critic can score events/Git patches and drive iterative refinement, but preserved the boundary that runtime-owned critic feedback is not automatically independent acceptance evidence.
- Recorded current prompt-memory behavior that can treat repository-root `AGENTS.md` as persistent model-visible project memory; classified worker-writable repository memory as lower trust than protected ACL governance.
- Recorded detailed primary sources, failure boundaries, candidate invariants, ACL regression-fixture ideas and explicit non-conclusions in `projects/openhands.md`.
- Preserved the decision boundary: Task 11 does **not** decide whether ACL should adopt/fork/wrap OpenHands, compare a cross-project winner, or begin SWE-agent/mini-swe-agent research.

## Highest-value OpenHands findings for later comparison

1. Separate control-center/UI, automation/scheduling and agent-runtime truth rather than allowing one surface to own everything.
2. Give each durable active conversation/task one fenced writer using owner identity, monotonic generation, TTL/renewal and guarded writes.
3. Persisting events is insufficient; active branch/HEAD and action→result relationships must remain consistent under crashes.
4. A run persisted as `RUNNING` deserves stronger recovery treatment than known idle/settled state.
5. Concurrent tool safety needs explicit shared-resource identity; resource declarations are privileged contract code.
6. Re-check cancellation/authorization/lease state immediately before an irreversible action, especially after blocking waits.
7. Cancellation is a request; a task is not safely stopped until its owned thread/process/job is actually settled or explicitly unresolved.
8. Workspace/container/worktree abstraction is execution transport/collision control, not proof of least-privilege filesystem/network/secret policy.
9. Confirmation/risk classification, authorization and real execution authority are separate contracts.
10. Durable task/conversation/checkpoint state should converge toward credential references rather than reusable secret material.
11. `runtime_visible` credentials must be treated honestly: arbitrary worker code can copy/exfiltrate already-delivered plaintext.
12. Brokered credentials and runtime-visible credentials are different authority models and should be explicit per binding/use.
13. Every ambient configuration/state root must participate in isolation; a clean workspace/persistence root can still be contaminated by HOME/global profile state.
14. Local-model compatibility is exact model + runtime + adapter + endpoint mode + context/tool/timeout/retry capability, verified at realized behavior.
15. Separate raw sensitive traces, operational tracing and product analytics by schema/audience/retention.
16. Runtime critics/refinement are useful but do not replace verifier-owned protected acceptance evidence.
17. Worker-writable persistent repository memory/instructions must remain lower trust than ACL/Vera governance and verified project truth.
18. OpenHands remains a runtime/server/workspace/credential/recovery reference; it does not replace ACL's outer project/backlog scheduler, external-effect ledger, independent verifier or Vera memory governance.

## Queue status

- **Pydantic AI (#1): complete.** Detailed evidence: `projects/pydantic-ai.md`.
- **Cline (#2): complete.** Detailed evidence: `projects/cline.md`.
- **LangGraph (#3): complete.** Detailed evidence: `projects/langgraph.md`.
- **promptfoo (#4): complete.** Detailed evidence: `projects/promptfoo.md`.
- **Strands Harness SDK (#5): complete.** Detailed evidence: `projects/strands-harness-sdk.md`.
- **Codex (#6): complete.** Detailed evidence: `projects/codex.md`.
- **OpenHands (#7): complete.** Detailed evidence: `projects/openhands.md`.
- **SWE-agent / mini-swe-agent (#8): next task only.** This ranked slot is transition-aware because SWE-agent is maintenance-only and names mini-swe-agent as successor.
- Remaining ranked queue stays unchanged until its own separately authorized task or later evidence justifies an explicit update.

## Next task

Deep-research the **SWE-agent / mini-swe-agent transition-aware slot** only.

Do not begin this task until separately instructed. For the next task, preserve Task 4's established transition evidence and determine which SWE-agent mechanisms were intentionally discarded, moved into SWE-ReX or retained in mini-swe-agent. Cover architecture/harness simplicity, execution backend/process isolation, repository/file/tool semantics, state/context/recovery, provider/local-model behavior, timeout/cancellation/process cleanup, evaluation/reproducibility, maintenance boundaries, recurring current failures, reusable components and concrete ACL/Vera lessons. Save evidence/catalog/state, commit research-only changes, and **stop before llama.cpp**.

## Later tasks
1. Deep-research llama.cpp, then OpenAI Agents SDK, one project per separately authorized task.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 11 ended after OpenHands system/repository boundaries, conversation/event-tree persistence, generation-fenced ownership, crash recovery, concurrent tool locking, cancellation/thread settlement, workspace/worktree authority boundaries, confirmation/security analysis, credential architecture, ambient-state isolation, local-provider capability, observability/critic boundaries, catalog/watchlist/state updates and next-task definition were completed. No SWE-agent/mini-swe-agent or llama.cpp research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
