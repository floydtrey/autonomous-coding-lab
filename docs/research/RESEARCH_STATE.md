# Research State

**Branch:** `research/agent-landscape`
**Status:** current task complete; stopped before next task
**Current phase:** 20 — Graphiti deep research complete
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

## Task 20 work completed
- Re-read `README.md`, `PROCESS.md`, `RESEARCH_STATE.md`, `watchlist.md`, and the evidence-source rules before research.
- Began from branch checkpoint `626f627648e437720941289e28308e5cda67ad8f`, preserving the separate `docs/research/IDEAS.md` documentation commit.
- Verified canonical project identity `getzep/graphiti`, active/non-archived and Apache-2.0 licensed.
- Inspected current upstream revision `b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d` on 2026-09-06.
- Recorded current package metadata `graphiti-core 0.30.1` and kept exact commit identity authoritative because tag/release title/package version can diverge.
- Distinguished open-source Graphiti from the separately managed Zep product so Zep governance/user-management/performance/security guarantees are not silently attributed to self-hosted Graphiti.
- Deep-researched Graphiti's hierarchical memory structure: episodic/raw source records, semantic entity nodes/fact edges, and community summaries.
- Verified fact-to-episode provenance through supporting episode UUIDs and episode-to-entity `MENTIONS` relationships.
- Verified raw episode content is stored by default but can be deliberately omitted through `store_raw_episode_content=False`; provenance structure therefore does not always imply reconstructable raw evidence.
- Deep-researched Graphiti's bi-temporal model: `valid_at`/`invalid_at` model world validity while `created_at`/`expired_at` model system ingestion/invalidation time.
- Derived the critical Vera distinction that temporal recency is not epistemic/source authority; newer lower-trust evidence cannot automatically supersede stronger verified evidence.
- Deep-researched current edge extraction, deduplication and contradiction/invalidation behavior.
- Verified current duplicate candidates are scoped to the same resolved entity pair while invalidation candidates are searched group-wide with empty `SearchFilters()`.
- Verified current LLM contradiction context supplies candidate indexes/fact strings without endpoint/relation/provenance/trust context and selected contradiction IDs directly feed temporal invalidation.
- Cross-checked open #1728 against current source and retained it as a current-main false-invalidation regression fixture: semantically similar unrelated facts can be nominated and model-selected for retirement.
- Derived the Vera/ACL invariant that canonical memory invalidation is a privileged reversible effect requiring structural replacement eligibility, provenance/trust comparison, audit evidence and stronger gates for high-risk domains.
- Deep-researched open #1666 as the complementary small-model failure class: non-reasoning `small_model` contradiction detection can miss genuine contradictions even when duplicate detection remains strong.
- Derived that local-memory qualification must measure semantic maintenance correctness, not only structured JSON validity.
- Deep-researched current search filtering and preserved current-state versus historical-state retrieval as separate intent; open #1645 records reference MCP search returning invalidated historical facts with live facts absent explicit caller filtering.
- Deep-researched group/partition behavior and backend-specific routing.
- Verified `group_id` is graph partition/query metadata, not an authenticated principal or authorization boundary.
- Verified current FalkorDB read routing has call-scoped single/multiple-group clones but `add_episode` still reassigns shared `self.driver`/`self.clients.driver` before many awaits.
- Cross-checked open #1676 against current source and retained concurrent cross-group FalkorDB write corruption as a current-main data-integrity/isolation fixture.
- Preserved backend identity as behavior-bearing: Neo4j, FalkorDB, Neptune and deprecated Kuzu do not have interchangeable routing/search/concurrency semantics.
- Recorded recent Neo4j custom-database routing and FalkorDB routing fixes as evidence that database/driver/schema/migration identity belongs in the memory deployment profile.
- Deep-researched persistence boundaries.
- Verified the primary episode/entity/episodic-edge/fact-edge save uses one driver `execute_write` transaction.
- Verified optional saga/link maintenance occurs after that main graph transaction and `remove_episode` spans several cleanup/delete calls without one demonstrated surrounding transaction.
- Derived explicit memory-operation settlement/reconciliation states for post-write and deletion recovery rather than equating one durable record with complete operation success.
- Deep-researched local/provider behavior through `OpenAIGenericClient`.
- Verified OpenAI-compatible `/chat/completions` paths include Ollama, vLLM and llama.cpp and can use native `json_schema` or prompt-guided `json_object` structured-output modes.
- Recorded current source/docs warnings that smaller/local provider structured-output and semantic extraction behavior varies; older Ollama issues were retained only as compatibility evidence rather than current universal regressions.
- Deep-researched embedding durability and search integrity.
- Cross-checked open #1328 against current Neo4j similarity source and verified current edge/community cosine-search paths still lack an explicit null/dimension guard before similarity calculation.
- Derived that embedding model/dimension/profile is durable memory schema requiring validation, migration and re-embedding state rather than a disposable runtime setting.
- Deep-researched episode-content trust: raw/current/prior episode content and custom extraction instructions enter LLM memory-construction context.
- Preserved raw episodes/retrieved content as untrusted evidence that must never become policy/tool/credential authority merely because it was persisted.
- Deep-researched the reference Graphiti MCP server and its high-authority add/direct-write/delete/clear memory effects.
- Recorded that reference server configuration defaults HTTP host to `0.0.0.0` and that Task 20 found no Graphiti-specific principal/authorization owner in the inspected configuration; preserved the narrower conclusion that ACL/Vera must wrap Graphiti memory effects with its own authority/network policy.
- Deep-researched optional OpenTelemetry tracing and recorded it as operational evidence, not authoritative memory-settlement/verification evidence.
- Re-read the Zep/Graphiti architecture paper for the three memory planes, bi-temporal semantics, source provenance, retrieval design, community refresh limitations and DMR/LongMemEval evaluation evidence.
- Preserved the paper's own critique of DMR and separated historical Zep-system benchmark results from current self-hosted Graphiti guarantees.
- Wrote detailed evidence, 27 candidate architectural invariants, 22 regression fixtures, primary sources and explicit non-conclusions to `projects/graphiti.md`.
- Prepared exactly 14 Task 20 catalog records for append after the 167 Task 19 records.
- Preserved task boundary: no Microsoft Agent Framework research, cross-project winner selection, dependency/adoption decision, benchmark execution, architecture/governance redesign, or worker/model execution was begun.

## Highest-value Graphiti findings for later comparison
1. Episode evidence, semantic facts/entities and community summaries are distinct memory planes; this is strong Vera reference material.
2. Fact-to-episode links provide evidence lineage, but provenance is not truth and raw episode retention can be disabled.
3. Bi-temporal valid-world time versus system-mutation time is valuable and should remain separate from source trust/confidence.
4. Newer information is not automatically stronger information; recency cannot be Vera's epistemic authority policy.
5. Current false-invalidation path (#1728 + current source) makes memory invalidation a critical privileged-effect regression fixture.
6. Current small-model contradiction evidence (#1666) shows syntax-valid model output can still make memory semantically unsafe.
7. Current-state and historical-state retrieval should be explicit APIs/policies rather than one mixed search result.
8. `group_id` is partition metadata rather than authentication/authorization.
9. Current FalkorDB shared-write routing (#1676) makes memory-domain isolation and concurrency part of backend qualification.
10. Primary episode/entity/fact persistence is transaction-scoped, but complete memory lifecycle includes post-write/delete operations that need independent settlement/recovery evidence.
11. Database/driver/schema/routing/migration identity is part of the memory deployment profile.
12. OpenAI-compatible/local support is a starting integration path, not proof that a local model can safely extract/deduplicate/invalidate memory.
13. Embedding dimension/model is durable datastore schema; bad or mixed vectors can make retrieval unavailable.
14. Retrieval relevance is not fact truth/confidence; liveness/trust/authority filters precede ranking for action-sensitive memory.
15. Raw episode content is untrusted model input and must not be allowed to rewrite governance, tools or credentials.
16. Graphiti MCP mutation tools remain below ACL/Vera-owned principal/domain/effect authorization.
17. OpenTelemetry is useful operational evidence but not independent memory-verification authority.
18. Graphiti and Letta-style curated memory appear complementary research references rather than one automatically replacing the other.
19. Zep paper benchmarks are encouraging retrieval evidence but not current Graphiti OSS production guarantees.
20. Graphiti does not replace ACL scheduling/fencing/effect ledger/verifier/credential policy or Vera's epistemic/trust layer.

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
- **Graphiti (#16): complete.** Detailed evidence: `projects/graphiti.md`.
- **Microsoft Agent Framework (#17): next task only.** No Microsoft Agent Framework research was begun in Task 20.
- Remaining ranked queue stays unchanged until separately authorized.

## Next task

Deep-research **Microsoft Agent Framework** only.

Do not begin until separately instructed. When begun, inspect canonical current upstream and focus on ACL/Vera-relevant agent/runtime architecture, tool and authority boundaries, workflows/orchestration, state/checkpoint/recovery, concurrency/cancellation, provider/local-model portability, MCP/A2A or other protocol integration, observability/evaluation, security/current failure evidence, project transition from AutoGen where relevant, and reusable mechanisms. Save report/catalog/state/watchlist, make a research-only commit, and stop before Google ADK.

## Later tasks
1. Microsoft Agent Framework, then the remaining ranked active-project queue one task at a time.
2. Deep-research high-value developers/accounts one at a time.
3. Compare reusable components versus custom-build candidates.
4. Analyze collaboration/open-source options.
5. Deep-research agent security and memory safety.
6. Deep-research long-running autonomy and local-model compatibility.
7. Produce final synthesis only after individual work is complete.

## Stop point

Task 20 ended after Graphiti's episodic/semantic/community memory architecture, bi-temporal validity, provenance, contradiction/invalidation authority, live-versus-historical search, graph/domain identity, backend routing/concurrency, persistence/recovery, local structured-output behavior, embedding integrity, MCP memory authority, content trust, observability and evaluation evidence were researched. No Microsoft Agent Framework research, cross-project winner selection, dependency decision, benchmark execution, ACL/Vera architecture/governance change or worker/model execution was begun.
