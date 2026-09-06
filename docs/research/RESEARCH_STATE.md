# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 4 — failed, abandoned, and heavily redesigned attempts mapped
**Execution:** research only; no worker/model execution authorized by this branch

## Completed
- Research workspace initialized and research process/evidence ladder established.
- Mapped recurring sources for ACL/Vera across upstream development, research, local models, benchmarks, security, standards/protocols, observability and practitioner discovery.
- Verified 27 confirmed-active projects and 10 recurring current contributors in Task 2; ranked projects, people and recurring sources by research information value in Task 3.
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `sources.md`, and `watchlist.md` before beginning Task 4.
- Completed the failure/redesign investigation using primary upstream status declarations, migration guides, archived repositories, maintainers' transition notes, current repository metadata and narrowly scoped issue evidence.
- Documented eight high-value transition cases in `failures/failed-redesigned-attempts.md`:
  1. AutoGen → ground-up v0.4 rewrite → Microsoft Agent Framework maintenance-mode successor transition.
  2. SWE-agent → near-total 1.0 rewrite → maintenance-only status and mini-swe-agent supersession.
  3. OpenAI Swarm → OpenAI Agents SDK production successor.
  4. AutoGPT Classic → unsupported legacy experiment while maintained AutoGPT moved to workflow/block Platform architecture.
  5. Original BabyAGI → archived snapshot and materially reconceived self-building function framework.
  6. GPT-Engineer → archived research CLI / precursor to Lovable-managed product direction.
  7. GPT Pilot → explicitly unmaintained repository with a documented prolonged credential-stealing supply-chain compromise.
  8. AgentGPT → archived repository with no authoritative cause/successor explanation.
- Resolved the prior AutoGen status ambiguity: upstream now explicitly marks AutoGen maintenance-only and names Microsoft Agent Framework as successor.
- Preserved **Aider** as status unresolved: the repository is not archived and no authoritative maintainer statement establishes abandonment or an official successor; community concern/forks are discovery evidence only.
- Recorded OpenDevin→OpenHands and Block→AAIF Goose as explicit **non-failure controls** so repository/org moves are not mistaken for abandonment.
- Extracted recurring lessons without changing ACL governance: scaffold complexity must earn measurable value; runtime observability/cancellation/execution isolation recur as redesign drivers; free-form research autonomy differs from production workflow automation; maintenance state is a security boundary; migrations need behavioral evidence; canonical identity must be separated from architecture generation.
- Updated `watchlist.md` and `catalog.jsonl` with Task 4 transition/status evidence.
- Preserved the research boundary: no ranked project was individually deep-researched for adoption/reuse, no architecture recommendation was finalized, and no ACL runtime/governance code was changed.

## Queue impact discovered in Task 4

- **SWE-agent rank #8 is now a transition-aware historical slot.** When that point in the ranked queue is reached, later research should examine the SWE-agent→mini-swe-agent redesign and current mini-swe-agent implementation rather than treating legacy SWE-agent as the current endpoint.
- **OpenAI Agents SDK rank #10 gains predecessor context** from Swarm, but no project-level deep research was started.
- **AutoGen** moves from status-deferred ambiguity to confirmed maintenance-only/superseded historical evidence; Microsoft Agent Framework remains the active candidate already present in the broader watchlist.
- **Aider** remains outside the confirmed-active ranking until authoritative status changes or a separate later task resolves it.

## Next task

Deep-research ranked projects **one at a time**, beginning with **Pydantic AI** only.

Do not begin this task until separately instructed. For the next task, deep-research Pydantic AI as the #1 research-priority project: architecture, harness/model control boundaries, tool/structured-output contracts, retries, concurrency/cancellation, local/Ollama support, evaluation/observability, security/permission implications, reusable components, recurring upstream failures, maintenance/health and concrete ACL/Vera lessons. Save evidence/catalog/state, commit research-only changes, and **stop before Cline**.

## Later tasks
1. Deep-research Cline, then continue the ranked project queue one project per separately authorized task.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after the individual work is complete.

## Stop point

Task 4 ended after the failure/redesign map, status corrections, cross-cutting lessons, catalog/watchlist updates and next-task definition were completed. No Pydantic AI deep research, Cline research, adoption decision, collaboration analysis, architecture/governance change, or worker/model execution was begun.
