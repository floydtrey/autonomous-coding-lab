# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 3 — watchlist ranked for research priority
**Execution:** research only; no worker/model execution authorized by this branch

## Completed
- Research workspace initialized and research process/evidence ladder established.
- Mapped recurring sources for ACL/Vera across upstream development, research, local models, benchmarks, security, standards/protocols, observability and practitioner discovery.
- Verified 27 confirmed-active projects and 10 recurring current contributors in Task 2; preserved Aider and AutoGen as status-deferred without cause analysis.
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, `watchlist.md`, and the Task 2 active-project/person evidence before beginning Task 3.
- Ranked the 27 confirmed-active projects by ACL/Vera-specific **research information value**, using explicit criteria: unresolved-problem overlap, distinctive implementation/failure evidence, local/provider portability, safety/reliability/lifecycle depth, reuse leverage, and evidence inspectability/current signal.
- Ranked the 10 recurring contributors by expected technical-signal value rather than reputation or presumed authority.
- Ranked the 15 recurring source channels by primary-evidence authority, ACL/Vera relevance, actionability/reproducibility, cadence and auditability while preserving the evidence ladder in `sources.md`.
- Performed targeted upstream verification for ranking-sensitive claims, including local/Ollama paths, sandbox/approval controls, checkpoint/retry/interruption mechanics, structured-output/tool validation, memory provenance/history and coding-agent red-team/evaluation primitives.
- Recorded detailed project ranking in `projects/ranked-projects.md`, contributor ranking in `people/ranked-people.md`, source ranking in `ranked-sources.md`, and updated `watchlist.md` / `catalog.jsonl`.
- Preserved the critical interpretation: **rank means investigate/watch sooner, not adopt, depend on, fork, or declare superior**.
- Excluded status-deferred Aider and AutoGen from the active ranking so Task 3 did not infer failure, abandonment, replacement, transition causes or successor relationships.

## Highest-priority queues established in Task 3

### Projects — first deep-research tranche
1. Pydantic AI
2. Cline
3. LangGraph
4. promptfoo
5. Strands Harness SDK
6. Codex
7. OpenHands
8. SWE-agent
9. llama.cpp
10. OpenAI Agents SDK

### Recurring contributor streams — first five
1. Saoud Rizwan (`saoudrizwan`)
2. Nick Hollon (`nick-hollon-lc`)
3. Jesús Samuel (`jesussamuel-byte`)
4. Graham Neubig (`neubig`)
5. Johannes Gäßler (`JohannesGaessler`)

### Recurring sources — first five
1. Upstream GitHub repositories
2. OWASP GenAI Security Project / Agentic Security Initiative
3. SWE-bench + Berkeley Function Calling Leaderboard (BFCL)
4. arXiv cs.SE / cs.MA / cs.CR recent feeds
5. Model Context Protocol specification + upstream repository

## Next task

Find failed, abandoned, or heavily redesigned attempts.

Do not begin this task until separately instructed. Investigate relevant historical/current projects and transitions for evidence of what failed, was abandoned, was substantially redesigned, or moved into a successor architecture. Separate observable status/transition facts from inferred causes. Prioritize lessons that could prevent ACL/Vera from repeating known mistakes. Do **not** begin the ranked project-by-project deep research queue during that task unless needed narrowly to establish a documented redesign/successor relationship.

## Later tasks
1. Deep-research ranked projects one at a time.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 3 ended after the active project, recurring-contributor and recurring-source watchlists were ranked and documented. No failure/redesign investigation, adoption decision, collaboration analysis, architecture change, local worker/model execution, or individual deep-research task was begun.
