# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 18 — Letta Code deep research complete
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

## Task 18 work completed
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before research.
- Began from finalized Task 17 checkpoint `5366e7bd0b2402b3338679bd7c9fc2bb5556fe17`.
- Verified canonical project identity `letta-ai/letta-code`, active/non-archived, Apache-2.0 licensed.
- Inspected current upstream revision `701f2a5367828847313876c735ade27b9df97689` dated 2026-09-06.
- Verified package/release boundary `0.31.12` / `v0.31.12`.
- Verified Letta's central identity split: persistent `agent_id`, multiple `conversation_id` threads, and live runtime/App Server connections are separate state domains.
- Recorded that multiple conversations of one agent share long-term agent memory; conversation isolation is therefore not memory isolation.
- Deep-researched local MemFS: one agent owns a persistent Git-backed memory filesystem; `system/` memory can enter future system prompts while other files remain out of context until read.
- Verified recall/full message history remains separate from the persistent memory filesystem.
- Verified current memory prompt explicitly warns not to store secrets in Git-backed memory.
- Verified versioned memory constraints with bounded file/depth defaults.
- Recorded personal-agent memory and shared/organization memory as distinct ownership/authority domains rather than one undifferentiated store.
- Derived a core Vera rule: persistent memory mutation is not verified truth; Git commit history provides mutation provenance but not epistemic provenance or authority.
- Recorded that durable memory needs source/evidence identity, trust/confidence/verification/conflict semantics for high-value facts rather than recency alone.
- Deep-researched dreaming/reflection: background memory workers operate in Git worktrees and current integration exposes `merged`, `no_changes`, `parent_dirty`, `merge_conflict`, `dirty_uncommitted`, and `failed` outcomes.
- Verified successful reflection generation/commit is distinct from successful parent-memory integration; transcript consumption is tied to settlement states rather than model output alone.
- Recorded open #4029 as prompt/evaluation-scoped epistemic evidence: conflict resolution can lack restraint when newer evidence should not automatically supersede stronger older evidence.
- Derived stronger Vera contradiction rules for safety/security/identity-critical memories.
- Distinguished memory from skills and trusted executable mods/configuration; current mods can register tools/providers/events/permission overlays/UI and are therefore trusted code rather than ordinary learned memory.
- Derived `LearnedMemory != TrustedCode != SecurityPolicy`; memory workers must not silently expand authority or deploy trusted code.
- Deep-researched memory confinement and found two materially different realized-sandbox behaviors.
- Verified exported memory-confinement API fails closed when its required kernel sandbox cannot be realized.
- Verified ordinary internal `memory-subagent` sandbox path can warn and proceed unsandboxed if disabled/unavailable/no writable root is available.
- Derived `ConfiguredSandbox != RealizedSandbox` and retained ACL's fail-closed requirement for unattended production memory workers requiring isolation.
- Verified cross-agent memory guards are useful namespace authority but do not replace process/filesystem/network/credential isolation.
- Deep-researched context/compaction/recall: full history remains separately recoverable while active context can be summarized; compaction summary is context optimization, not canonical evidence.
- Deep-researched local message projection and fork handling, including preserved tool-call/result parent relationships and cleanup of orphan projected results.
- Recorded open #4247 as current-main transcript-projection evidence: reasoning chunks are joined with `\n\n`, which can corrupt word continuity and therefore contaminate downstream reflection input.
- Derived explicit representation boundaries: raw provider evidence, canonical semantic message, stored projection, UI, and reflection input need separate correctness tests.
- Recorded open #3132 as current configuration-propagation fixture: local new-conversation context can fall through a `128000` legacy fallback; current backend still contains the representation/fallback seam, though Task 18 did not rerun every current UI path.
- Verified local/provider support includes Ollama, LM Studio, llama.cpp/OpenAI-compatible and cloud paths; exact Letta/provider/model/runtime/context/tool configuration remains the capability identity.
- Deep-researched permission/tool boundaries: model-facing tool availability, approval mode, deterministic allow/deny rules, and actual process capability are separate controls.
- Deep-researched secret substitution: model-facing references/names are preferable to prompt plaintext and execution results are scrubbed, but runtime plaintext exposure remains real authority.
- Verified Letta MemFS warns not to persist secrets and retained Vera's stronger credential-broker/reference model.
- Deep-researched subagents: headless child processes receive filtered tool surfaces and side-effect-aware bounded retry behavior.
- Recorded the strong retry rule that clearly truncated output may be retried but ambiguous parse/stream failure after possible effects is not automatically replayed.
- Verified child subagent environment currently begins from the parent process environment and forwards Letta credentials/settings; retained ACL's stronger minimal-explicit-environment rule.
- Verified child cancellation uses process signaling but does not prove process-tree or external-effect settlement.
- Recorded open #3523 as issue-scoped retention evidence for supposedly stateless subagent records persisting after work ends; no universal current leak claim was made.
- Deep-researched App Server Protocol V2: runtime scope carries agent/conversation identity plus request/event/idempotency metadata useful for reconnect and approval correlation.
- Preserved boundary that runtime request/event/idempotency keys are not ACL external-effect IDs or exactly-once settlement evidence.
- Deep-researched `@letta-ai/trajectory` ingestion for normalized historical coding-agent sessions and memory analysis.
- Derived that imported trajectories remain provenance-labeled lower-trust data and must not automatically become privileged memory/policy.
- Recorded open #4195 as a current-main destructive restore failure: active memory can be deleted before replacement backup copy succeeds; inspected source still retains the relevant delete-before-copy ordering.
- Derived transactional restore invariant: stage and verify replacement before switching/destroying authoritative current state.
- Recorded open #4249 as current Windows reflection-integration evidence where a reflection commit can exist while parent memory refresh fails; preserved the issue as settlement evidence without asserting an unresolved universal root cause.
- Classified Letta memory failures separately as epistemic, projection, integration, restore, retention, and runtime-configuration failures rather than generic model-memory failure.
- Wrote detailed evidence, 40 candidate ACL/Vera invariants, regression fixtures, primary sources and explicit non-conclusions to `projects/letta-code.md`.
- Preserved task boundary: no Gemini CLI research, cross-project winner selection, benchmark execution, architecture/governance redesign, or worker/model execution was begun.

## Highest-value Letta Code findings for later comparison
1. Persistent assistant identity, conversation thread, runtime connection, task/run and effect identity should be separate domains.
2. Letta's agent-owned Git-backed MemFS is the strongest distinct persistent-memory architecture reference found so far in this campaign.
3. Recall/history and curated persistent memory should remain separate.
4. Personal identity memory and shared/project memory require distinct ownership/authorization semantics.
5. Git history is strong mutation provenance but does not establish truth, confidence, authority or source quality.
6. Memory needs provenance/evidence/trust/conflict semantics before Vera can rely on it for high-authority decisions.
7. Newer evidence is not automatically stronger evidence; #4029 is a concrete epistemic-restraint fixture.
8. Reflection worktrees provide strong explicit settlement states for background memory integration.
9. Reflection commit and authoritative parent-memory integration are separate states.
10. Memory, skills, trusted executable mods/configuration and security policy must remain separate trust classes.
11. Learning must not silently deploy trusted code or expand authority.
12. Configured memory sandboxing and realized sandboxing are different evidence; internal memory-subagent launch can degrade to unsandboxed execution.
13. Cross-agent memory guards do not replace process/network/filesystem/credential isolation.
14. Compaction summary is context optimization, not canonical historical evidence.
15. Transcript projection correctness is memory integrity because reflection may learn from persisted projections.
16. #4247 provides a current transcript-projection regression fixture at the inspected revision.
17. Exact provider/model/runtime/context/tool configuration remains a verified deployment profile; nominal Letta/local support is insufficient.
18. #3132 provides a context-setting propagation fixture; realized context must be observed.
19. Tool visibility, approval policy, validation and process authority remain separate.
20. Secret references/substitution are useful, but runtime plaintext remains authority exposure.
21. Letta subagent retry logic provides a strong pattern: ambiguous outcome after possible effects is not automatically replayed.
22. Letta subagents inherit ambient parent environment; ACL should not copy that behavior.
23. Process cancellation signal is not process-tree/effect settlement.
24. App Server runtime/request/idempotency identity is useful for Vera clients but is not an exactly-once effect ledger.
25. Imported trajectories are useful learning evidence but remain lower-trust data with source provenance.
26. #4195 is a current transactional-restore failure fixture: never delete authoritative state before replacement is staged/verified.
27. #4249 shows background reflection commit can exist while authoritative parent-memory integration remains unsettled.
28. Memory failure categories should distinguish epistemic, projection, integration, restore, retention and runtime-configuration faults.
29. Letta Code is a strong memory/runtime component reference, not ACL/Vera's scheduler, verifier, effect ledger, credential broker or complete sandbox.

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
- **Letta Code (#14): complete.** Detailed evidence: `projects/letta-code.md`.
- **Gemini CLI (#15): next task only.** No Gemini CLI research was begun in Task 18.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **Gemini CLI** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant tool/execution authority, sandbox/permissions, provider/runtime behavior, context/state/recovery, local-model or adapter boundaries where present, extensibility/protocol surfaces, observability/evaluation, current failure evidence, and reusable mechanisms. Save report/catalog/state/watchlist, make a research-only commit, and stop before Graphiti.

## Later tasks
1. Gemini CLI, then the remaining ranked active-project queue one task at a time.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after individual work is complete.

## Stop point

Task 18 ended after Letta Code's persistent identity/memory architecture, MemFS/Git/reflection settlement, epistemic memory risk, confinement/sandbox realization, context/transcript projection, provider/local-model boundary, permissions/secrets/mods, subagent retry/environment/cancellation/retention, App Server protocol, trajectory ingestion and current recovery failures were researched. No Gemini CLI/Graphiti research, cross-project winner selection, dependency decision, benchmark execution, ACL/Vera architecture/governance change or worker/model execution was begun.
