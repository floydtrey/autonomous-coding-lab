# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 8 — promptfoo deep research complete
**Execution:** research only; no worker/model execution authorized by this branch

## Completed
- Research workspace initialized and evidence ladder established.
- Tasks 1–4 mapped recurring sources, active projects/people, research priority, and failed/abandoned/heavily redesigned attempts.
- Task 5 deep-researched **Pydantic AI** and the directly relevant official Pydantic AI Harness surfaces.
- Task 6 deep-researched **Cline** and its coding-agent architecture, authority, checkpoints, local-runtime/context and telemetry failure surfaces.
- Task 7 deep-researched **LangGraph** and its state/checkpoint, replay, interrupt, durability and retention failure surfaces.
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before Task 8.
- Deep-researched **promptfoo** as ranked project #4, using the ACL/Vera end goal to control scope.
- Verified promptfoo's distinct architectural role as an independent evaluation/red-team layer rather than an owner of agent task/session/checkpoint state.
- Verified current active/open-source status, MIT licensing, rapid release activity and the 2026-03-09 announcement that promptfoo had agreed to be acquired by OpenAI while remaining open source; preserved the announcement's closing-condition caveat rather than inferring unverified ownership details.
- Verified deterministic assertion families for outputs, tool calls, traces and trajectories, including exact/partial tool-argument matching, tool sequence/count constraints and trace error/duration/count checks.
- Verified that semantic trajectory goal success is model-graded and should remain a lower-trust complement to deterministic observable evidence.
- Verified OpenTelemetry test-case/target/grading correlation, agent/tool/turn evidence and current cache/subagent caveats relevant to trajectory assertions.
- Verified `failOnReceiverStartFailure` and regression tests demonstrating why trace-dependent high-confidence evals should fail/invalid when their evidence channel disappears instead of silently degrading.
- Verified coding-agent-specific red-team coverage for repository/terminal injection, secret reads, sandbox escape, verifier sabotage, network/procfs access, delayed CI exfiltration, automation poisoning and generated vulnerabilities.
- Verified the coding-agent failure taxonomy separating model behavior, harness-boundary, verifier-integrity and eval-design failure classes.
- Verified disposable per-row workspace/reset guidance and synthetic canaries to prevent mutable coding-agent tests from contaminating later rows.
- Verified verifier-first evidence ordering: host-side canaries, hashes, traces, command evidence, network traps and sidecar reports before semantic rubric fallback; configured missing sidecar verifier evidence fails closed.
- Verified the distinction between unsafe willingness, attempted unsafe behavior and action-verified exploit/effect.
- Verified that red-team trace summaries can be exposed separately to attackers and graders (`includeInAttack` vs `includeInGrading`), making evaluation telemetry itself an information-flow boundary.
- Verified native Ollama target, tool-call and embedding support plus local Ollama grading providers; serial evaluation can reduce local-model memory/switching pressure.
- Verified reproducibility controls around pinned configuration, max concurrency, repeats, cache/`--no-cache`, rerunning failures, CI tags and result exports while preserving that reproducibility is not automatic.
- Verified CI quality-gate support and recorded the need to distinguish infrastructure errors, deterministic failures, security/verifier-integrity failures and semantic scores rather than averaging them into one pass rate.
- Verified JavaScript and Python assertions are executable privileged code, so third-party eval packs/extensions require provenance and containment rather than being treated as passive YAML/data.
- Verified open issue #10166 as evidence that native model graders currently need a cleaner bounded/provenance-preserving structured-evidence seam.
- Verified open issue #10501 as a current evaluator failure surface where live target-provider objects can cross into grader/test configuration and break clone/serialization assumptions; recorded the broader invariant separating serializable descriptors from live credential-bearing runtime objects.
- Recorded detailed evidence, candidate invariants, ACL fixture ideas and explicit non-conclusions in `projects/promptfoo.md`.
- Preserved the decision boundary: Task 8 does **not** decide whether ACL should depend on promptfoo, nor rank promptfoo against prior projects or begin Strands Harness SDK research.

## Highest-value promptfoo findings for later comparison

1. Keep the system under test separate from the authority that decides whether it passed.
2. Prefer deterministic observable evidence before semantic LLM judgment.
3. Missing required evidence is an explicit failure/invalid result, not an implicit pass.
4. Keep verifier roots, protected tests and sidecar evidence outside worker write authority.
5. Distinguish model failure, harness-boundary failure, verifier-integrity failure and eval-design failure.
6. Distinguish unsafe willingness, attempted action and verified effect when labeling security behavior.
7. Run mutable coding-agent rows in isolated/resettable workspaces with unique synthetic canaries and recorded fixture identity.
8. Treat attacker-visible, grader-visible and operator-only telemetry as separate information-flow policies.
9. Record both target model/runtime identity and grader model/runtime identity as part of the benchmark definition.
10. Cache, concurrency, repeats, workspace/reset identity and trace availability are part of reproducibility evidence.
11. Treat evaluator scripts/plugins as privileged executable dependencies requiring provenance/containment.
12. Keep serializable test/config descriptors separate from live provider/client/session/credential objects.
13. High-severity security/verifier-integrity failures should gate independently from aggregate quality metrics.
14. promptfoo is an evaluation/security reference; it does not replace ACL runtime state, workspace/effect recovery, sandboxing, authority, scheduling or acceptance-policy ownership.

## Queue status

- **Pydantic AI (#1): complete.** Detailed evidence: `projects/pydantic-ai.md`.
- **Cline (#2): complete.** Detailed evidence: `projects/cline.md`.
- **LangGraph (#3): complete.** Detailed evidence: `projects/langgraph.md`.
- **promptfoo (#4): complete.** Detailed evidence: `projects/promptfoo.md`.
- **Strands Harness SDK (#5): next task only.** No Strands deep research was begun in Task 8.
- Remaining ranked queue stays unchanged until its own separately authorized task or later evidence justifies an explicit update.

## Next task

Deep-research **Strands Harness SDK** only.

Do not begin this task until separately instructed. For the next task, deep-research Strands Harness SDK as ranked project #5 with the same end-goal discipline: harness architecture and model/runtime boundaries, tool/capability contracts, structured-output validation/retry, local/Ollama support, workspace/process authority, session/state/context handling, concurrency/cancellation, observability/evaluation, recurring failure surfaces, project health, reusable components and concrete ACL/Vera lessons. Save evidence/catalog/state, commit research-only changes, and **stop before Codex**.

## Later tasks
1. Deep-research Codex, then continue the ranked project queue one project per separately authorized task.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 8 ended after promptfoo evaluation architecture, deterministic/trajectory assertions, coding-agent red-team/verifier integrity, local-model support, reproducibility/CI behavior, evaluator failure surfaces, catalog/watchlist/state updates and next-task definition were completed. No Strands Harness SDK or Codex research, cross-project winner selection, dependency/fork decision, ACL/Vera architecture/governance change, or worker/model execution was begun.
