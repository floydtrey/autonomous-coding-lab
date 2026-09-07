# Graphiti — Task 20 Deep Research

**Research date:** 2026-09-06  
**Repository:** `getzep/graphiti`  
**Inspected upstream revision:** `b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d`  
**Current source package version:** `0.30.1`  
**License:** Apache-2.0  
**Research status:** complete for Task 20; no dependency, memory-architecture winner, database, model, or implementation decision made.

## Executive assessment

Graphiti is the strongest project examined so far in this campaign for **temporal, provenance-linked semantic memory** rather than curated agent-owned memory. Its architecture distinguishes raw episodes, resolved entities, temporal facts, and higher-level communities; keeps links from semantic facts back to supporting episodes; models both world-valid time and system-ingestion/invalidation time; and supports hybrid semantic, full-text, and graph retrieval.

That makes it highly relevant to Vera's future need to remember a changing world without flattening every observation into one mutable summary. It complements, rather than replaces, the Letta findings from Task 18. Letta is primarily useful as a persistent agent-identity/curated-memory reference; Graphiti is primarily useful as a temporal evidence-and-relationship memory reference.

The important caution is that Graphiti's temporal graph is **not an epistemic truth engine**. Current ingestion delegates entity resolution, fact deduplication, contradiction selection, timestamp extraction, and summaries to LLMs. Current `main` still contains a particularly consequential invalidation path where contradiction candidates are searched broadly within a group and supplied to a small-model judge as bare fact strings; an erroneous contradiction can directly retire a previously valid fact. Open issue #1728 documents production collateral invalidation, and current source confirms the structural path. Open #1666 demonstrates the opposite failure class: non-reasoning small models can miss real contradictions. For Vera, memory invalidation must therefore remain a privileged, reversible, provenance-aware state transition with deterministic structural constraints and source/trust policy above the model.

Graph partitioning also needs care. `group_id` is a graph partition/query-scoping field, not an authentication or authorization mechanism. Neo4j commonly stores groups as properties in one database; FalkorDB maps groups to separate physical graphs. Current read routing has been hardened with call-scoped clones, but `add_episode` still mutates the shared Graphiti driver for a provided group and then crosses many `await` points. Open #1676 demonstrates that concurrent FalkorDB groups can silently write episodes into the wrong physical graph. This is both a concurrency/data-integrity failure and a warning against treating `group_id` as a tenant-security boundary.

Graphiti is also a behavior-bearing stack rather than a provider-neutral abstraction. A deployment's correctness depends on the exact Graphiti revision, database/backend, LLM client/model and structured-output mode, embedding model/dimension, cross-encoder/reranker, concurrency, graph schema, and retention configuration. Local OpenAI-compatible servers including Ollama, vLLM and llama.cpp are supported through `OpenAIGenericClient`, but current documentation and source explicitly acknowledge weaker structured-output reliability on smaller/local models. Graphiti is therefore a strong future **memory benchmark target**, not evidence that a small local model is already safe to own Vera memory writes.

## 1. Project identity, scope, and current-generation boundary

### Observed

- Canonical repository: `getzep/graphiti`.
- Current inspected branch tip: `b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d`.
- Current `pyproject.toml` declares `graphiti-core` version `0.30.1`, Python `>=3.10,<4`, Apache-2.0.
- The release API exposed a `v0.30.0` tag whose release title describes `v0.30.1`; because tag/title/package version can diverge, this report uses the exact commit as the authoritative source identity.
- Graphiti is the open-source temporal graph framework. Zep is a separate managed product built around context graphs and a proprietary Context Graph Engine.
- The Graphiti README explicitly says the OSS framework does **not** supply Zep's built-in user/conversation management, enterprise governance, managed retrieval performance, dashboard, or security guarantees.

### ACL/Vera significance

`Graphiti` should not be shorthand for `Zep`. Benchmarks and enterprise claims from the Zep paper/product must be separated from guarantees of a self-hosted Graphiti deployment. Later component comparison should identify the exact OSS surface under consideration and avoid importing managed-service guarantees into ACL/Vera design decisions.

## 2. The memory model: episodic, semantic, and community planes

Graphiti's central architecture is a hierarchical context graph.

### Episode plane

Current source defines `EpisodicNode` records for raw input in message, text, JSON, and fact-triple forms. Episodes carry:

- stable UUID,
- name,
- `group_id`,
- source/source description,
- raw content,
- creation time,
- event/reference time,
- references to extracted entity edges.

The Zep/Graphiti paper describes episodes as the non-lossy source stream from which semantic graph objects are derived, with `MENTIONS` edges linking episodes to extracted entities. Current Graphiti defaults `store_raw_episode_content=True`, but callers can explicitly disable raw episode storage; `_process_episode_data` then blanks episode content before persistence.

### Semantic entity plane

Entity nodes represent resolved people, systems, products, concepts, and developer-defined types. They carry evolving names/summaries, labels, custom attributes, embeddings, and group membership. Entity edges represent facts/relationships between entities.

Current `EntityEdge` fields include:

- relation `name`,
- natural-language `fact`,
- embedding,
- supporting episode UUID list,
- `valid_at`,
- `invalid_at`,
- `created_at`,
- `expired_at`,
- episode `reference_time`,
- arbitrary typed/custom attributes.

This is a useful separation between **source observations** and **derived semantic beliefs**.

### Community plane

Communities summarize clusters of strongly connected entities. The original paper describes incremental label-propagation updates to reduce latency/cost while warning that incremental communities drift from a full recomputation and therefore require periodic refresh.

### Derived Vera invariant

Vera should not have a single undifferentiated "memory" table. At minimum, keep separate:

1. immutable/raw evidence or observations,
2. resolved entity identity,
3. derived facts/relationships,
4. higher-level summaries/communities,
5. curated personal/agent memory,
6. trusted policy/configuration.

Derived summaries/facts should always be reconstructable or auditable against lower-level evidence where practical.

## 3. Bi-temporal state is a strong reusable concept

The paper and current source expose four important time concepts on semantic facts:

- `valid_at`: when the fact became true in the represented world,
- `invalid_at`: when it stopped being true in the represented world,
- `created_at`: when Graphiti persisted/created it,
- `expired_at`: when Graphiti marked it superseded/invalidated.

Episodes also carry a reference/event timestamp used to interpret relative expressions.

This separates **event time** from **system transaction time**, which is exactly the distinction Vera will need for statements such as:

- "John works day shift now" versus "I learned this on Tuesday."
- "The car was serviced Friday" versus "the receipt arrived Monday."
- "This preference was true last year" versus "this is the current preference."

### Critical caution

Temporal ordering is not source authority. The original paper states that Graphiti prioritizes new information in transactional order when determining edge invalidation. That is reasonable for many conversational updates, but Vera cannot make `newer observation > older verified fact` a universal epistemic rule. A low-trust recent inference must not automatically supersede an authoritative record, explicit user correction, safety policy, credential fact, or other higher-trust source.

### Candidate Vera fields above Graphiti's temporal fields

For important memory, consider preserving:

- source/evidence ID,
- source class,
- observed vs inferred vs user-asserted vs externally verified,
- confidence,
- verification state,
- authority/trust tier,
- conflict/supersession relationship,
- reviewer/approval where required,
- valid-world interval,
- system ingestion/update interval.

## 4. Provenance is valuable but conditional

Graphiti provides unusually useful provenance structure for agent memory:

- facts store supporting episode UUIDs,
- episodes link to mentioned entities,
- episode retrieval can identify associated nodes/edges,
- `get_nodes_and_edges_by_episode` reconstructs semantic artifacts associated with source episodes,
- episode deletion contains cascade-oriented cleanup logic.

This enables a future Vera response such as "Why do you believe this?" to trace a fact back toward one or more observations.

However, provenance strength depends on deployment policy:

- raw episode content can be disabled,
- an episode may itself be untrusted or incorrect,
- LLM extraction can distort the source,
- one derived fact can aggregate multiple supporting episodes,
- provenance says **where the belief came from**, not whether it is true.

Therefore Graphiti-style source linkage should be treated as evidence lineage, not verification.

## 5. Current contradiction/invalidation path is a privileged-memory warning

### Current-main behavior

At `b943c9e...`, `resolve_extracted_edges` builds two search pools:

1. duplicate candidates scoped to edges between the same resolved entity pair;
2. invalidation candidates retrieved with `SearchFilters()` across the entire `group_id`.

`resolve_extracted_edge` then sends the model:

- the new fact as text,
- duplicate candidates as `{idx, fact}`,
- invalidation candidates as `{idx, fact}`.

The candidate context does **not** include endpoint IDs, entity names, relation identity, provenance strength, or trust tier. The `EdgeDuplicate` response supplies integer arrays `duplicate_facts` and `contradicted_facts`. Selected contradiction indexes flow directly into invalidation logic.

`resolve_edge_contradictions` then uses temporal ordering to retire older candidates by writing:

- `edge.invalid_at = resolved_edge.valid_at`,
- `edge.expired_at = utc_now()` if not already set.

The inverse path can also mark the newly extracted edge invalid/expired if a selected contradiction candidate is temporally later.

### Open #1728 — current-main false invalidation fixture

Issue #1728 reports a production graph where semantically similar but unrelated facts were retired because the invalidation candidate search had become group-wide. The report audited examples in which a new relation sharing only one entity with a prior fact caused that still-true prior fact to receive `invalid_at`.

Task 20 cross-checked the key structural claims against current source:

- duplicate candidate search remains scoped;
- invalidation candidate search remains `SearchFilters()` group-wide;
- LLM contradiction context remains bare fact strings/indexes;
- no endpoint/relation structural guard is applied before temporal invalidation.

Therefore the architectural failure surface remains present at the inspected current revision. The production frequency in #1728 remains issue-scoped evidence, not a universal rate claim.

### Open #1666 — missed contradiction fixture

Issue #1666 measures the complementary failure mode. With a non-reasoning `small_model`, the stock contradiction response schema detected contradiction-bearing cases poorly; a reasoning-first schema substantially improved the issue author's controlled evaluation. Duplicate detection remained much stronger.

This matters for ACL/Vera local models because Graphiti deliberately uses a `small_model` in several maintenance stages for cost/latency. A model can therefore fail in both directions:

- false contradiction -> destroys/retires a true memory;
- missed contradiction -> leaves a stale memory active.

### Derived invariant

**Memory invalidation is an authority-bearing effect.** Do not allow an unconstrained LLM classification to directly retire canonical high-value memory.

A Vera-grade invalidation path should combine at least:

1. structurally plausible replacement scope,
2. matching entity identity and relation semantics,
3. source/provenance/trust comparison,
4. temporal compatibility,
5. explicit confidence/reason,
6. reversible state change rather than destructive deletion,
7. audit trail pointing to invalidating evidence,
8. human/authoritative confirmation for high-risk domains.

The desirable failure direction is often to retain a visibly conflicting/stale candidate until reconciliation rather than silently retire a true fact.

## 6. Search semantics must distinguish live facts from history

Graphiti has rich date filters (`valid_at`, `invalid_at`, `created_at`, `expired_at`) in `SearchFilters`, so current-vs-historical retrieval can be expressed by the caller.

However, open MCP issue #1645 documents that the reference `search_memory_facts` experience returns invalidated/superseded facts together with live facts unless the caller explicitly handles liveness. The proposal asks for default exclusion of invalidated facts with an opt-in history flag, configurable result counts/rerankers, and relevance scores.

For Vera, retrieval APIs should make intent explicit:

- `current_fact_search`
- `historical_fact_search`
- `evidence_search`
- `conflict_search`

A generic `search memory` operation that interleaves current and superseded facts pushes temporal interpretation back onto the model and increases the chance of an incorrect action.

## 7. `group_id` is partition metadata, not tenant authorization

Current base nodes define `group_id` as the graph partition. Search/write APIs commonly accept `group_id` or `group_ids` and use it for query scoping.

Graphiti's README explicitly contrasts the OSS framework with Zep's managed user/thread/governance features. The reference MCP server also describes `group_id` as separate knowledge domains, not authenticated principals.

### Backend semantics differ

- Neo4j generally represents groups as properties within one database and filters by `group_id`.
- FalkorDB uses separate physical graph/database names for group IDs in important paths.

The difference is behavior-bearing, not an internal implementation detail.

### Current FalkorDB concurrency hazard

Current `handle_multiple_group_ids` has been improved: read/search paths can use call-scoped cloned drivers for one or many FalkorDB groups.

But current `Graphiti.add_episode` still does:

`self.driver = self.driver.clone(database=group_id)`

and also replaces `self.clients.driver` before proceeding through many asynchronous extraction, embedding, resolution, and write operations.

Open #1676 provides a concrete concurrent reproduction where interleaved group A/group B ingestion on one shared Graphiti instance silently stores episodes in the wrong physical FalkorDB graph. Current source still contains the shared mutation that makes the report architecturally applicable.

### ACL/Vera implications

- Never use `group_id` possession as authentication or authorization.
- Tenant/user/project identity must be bound by a trusted outer policy.
- Per-request database routing should be immutable/call-scoped.
- A memory writer needs stable `principal_id`, `memory_domain_id`, and write authority separate from database/group naming.
- Cross-group concurrency and isolation must be explicit regression fixtures.
- Backend migrations must test group semantics rather than assuming Neo4j/FalkorDB equivalence.

## 8. Persistence is partly transactional, but not one universal memory transaction

### Strong part

`_process_episode_data` ultimately calls `add_nodes_and_edges_bulk`, which opens a driver session and uses `session.execute_write(add_nodes_and_edges_bulk_tx, ...)`. Within that main graph-write transaction, it persists:

- episodic nodes,
- entity nodes,
- episodic/MENTIONS edges,
- entity/fact edges.

This is good reference material: a source episode and its primary derived graph objects should settle together instead of becoming independently visible mid-write.

### Boundaries outside that main transaction

After the bulk write, optional saga association performs additional operations:

- create/get saga,
- save `NEXT_EPISODE`,
- save `HAS_EPISODE`,
- update saga first/last episode fields.

Those are subsequent calls rather than one demonstrated all-or-nothing transaction with the main episode graph write.

`remove_episode` likewise performs a multi-step cleanup:

1. load episode,
2. load its referenced entity edges,
3. identify edges for which this episode was the first creator,
4. count entity episode mentions,
5. delete qualifying entity edges,
6. delete qualifying entity nodes,
7. delete the episode.

Task 20 found no single surrounding transaction in this method. A crash between steps therefore needs explicit consistency testing/reconciliation; this report does not claim a reproduced partial-delete bug without such a fixture.

### Derived recovery rule

Memory lifecycle operations need explicit settlement states:

`proposed -> extracting -> resolved -> durable-write -> derived-maintenance -> settled`

and for deletion:

`delete-requested -> impact-calculated -> deleting-derived -> deleting-source -> settled`

If the process crashes between states, Vera must know whether to resume, reconcile, or escalate rather than infer success from a missing/remaining single record.

## 9. Database backend is part of memory identity

Current documented backend options include Neo4j, FalkorDB, Amazon Neptune/OpenSearch, and deprecated Kuzu.

Current project history shows significant backend-specific correctness work:

- the `v0.30.x` release family fixed Neo4j custom-database routing where some query APIs could use the home database while session writes used the configured database, potentially splitting data;
- `v0.29.3` included FalkorDB group-routing and post-restart/search corrections;
- current FalkorDB concurrent write routing remains an open high-severity surface;
- Kuzu is deprecated because its upstream project is no longer maintained.

Therefore `backend=graphiti` is not a sufficient deployment identity.

Record at least:

- Graphiti commit/package,
- graph driver/provider/version,
- database engine/version,
- configured database/graph name,
- group routing mode,
- index/schema version,
- concurrency configuration,
- migration history.

A memory backend change requires correctness/migration fixtures, not merely connection tests.

## 10. Local-model support exists, but structured extraction quality is the gate

Graphiti supports OpenAI, Anthropic, Gemini, Groq and other providers, and it exposes an `OpenAIGenericClient` for OpenAI-compatible `/chat/completions` servers including Ollama, vLLM and llama.cpp.

Current source makes the compatibility boundary explicit:

- generic client can request native `json_schema` structured output;
- it can fall back to `json_object`, where the schema is inserted into the prompt instead of enforced by the endpoint;
- native strict OpenAI schema mode is intentionally not universally assumed;
- local/OpenAI-compatible models sometimes return fenced JSON even when structured output was requested, so the client strips code fences;
- transient JSON/rate-limit failures are retried with a bounded Tenacity wrapper;
- official README warns smaller/non-structured-output-capable models may produce incorrect schemas and ingestion failures.

### Current small-model memory consequence

This is not only a parse-quality problem. #1666 demonstrates that the model assigned to a small maintenance stage can materially alter temporal contradiction correctness even when it returns schema-valid output.

Therefore local memory qualification must test **semantic maintenance operations**, not just JSON validity:

- entity extraction precision/recall,
- entity resolution/deduplication,
- fact extraction,
- timestamp extraction,
- duplicate classification,
- contradiction classification,
- false invalidation rate,
- stale-fact survival rate,
- custom ontology adherence.

### ACL benchmark identity

For Graphiti/local deployment, record exact:

- Graphiti commit,
- LLM client class,
- model + runtime + endpoint,
- `model` and `small_model`,
- structured-output mode,
- prompt/schema revision,
- embedding model/dimensions/runtime,
- cross-encoder/reranker,
- database backend,
- semaphore/concurrency settings.

This should later become a Vera memory-maintenance benchmark, separate from coding-worker benchmarks.

## 11. Embeddings are durable datastore schema, not a disposable runtime choice

Entity names, edge facts, and community names can carry embeddings. Search combines vector similarity with full-text and graph traversal.

Open #1328 reports Neo4j vector search failing the entire query when a stored edge has a null, invalid, or dimension-mismatched `fact_embedding`. Task 20 checked current Neo4j `edge_similarity_search`: it still computes cosine similarity over matched edge embeddings without an explicit null/dimension guard in the query. Community similarity has the same general unguarded pattern for community embeddings.

This creates a durable compatibility requirement:

- switching embedding models/dimensions is a migration,
- failed/partial embedding generation needs detection,
- stored vectors need dimension/finite-value validation,
- search should fail selectively/degrade explicitly rather than let one corrupt vector poison the whole result set,
- re-embedding jobs need version/state tracking.

A future Vera memory store should attach an `embedding_profile_id` or equivalent to vectorized records and make index migration explicit.

## 12. Retrieval is composable and useful, but ranking is not truth

Graphiti combines:

- vector semantic similarity,
- BM25/full-text retrieval,
- graph/BFS proximity,
- RRF,
- MMR,
- node-distance/episode-mentions reranking,
- optional cross-encoder reranking.

This is excellent reference material for Vera's future memory retrieval because different query intents need different evidence surfaces.

But retrieval score is not confidence/truth. A semantically close stale or false fact can rank highly. Search ranking should operate **after** liveness, authorization, trust, and evidence-domain filtering where those constraints matter.

## 13. Raw episode content is untrusted model input

Current entity extraction explicitly constructs LLM context from:

- current episode content,
- previous episode contents,
- custom extraction instructions,
- entity-type descriptions,
- source description.

This is architecturally necessary for semantic extraction, but it means arbitrary ingested content enters a privileged memory-construction model prompt.

Task 20 found no project claim that Graphiti itself provides a complete prompt-injection/memory-poisoning trust layer around episodes. Absence of an issue is not proof of safety or unsafety; the source topology alone is enough to preserve the boundary:

**episode text is untrusted evidence, not trusted memory instructions.**

Vera should bind source provenance/trust outside the episode body and prevent retrieved/injected text from modifying:

- memory security policy,
- tool permissions,
- trusted code/configuration,
- credential authority,
- verification rules.

## 14. MCP server exposes powerful memory effects and needs an outer authority layer

The reference MCP server exposes effect-bearing operations including:

- add memory/episodes,
- direct triplet/fact writes,
- deletion of episodes/facts,
- graph clearing,
- community construction/summarization,
- search/read operations.

Its own instructions call `group_id` a knowledge partition. Current `ServerConfig` defaults HTTP host to `0.0.0.0` and exposes transport/host/port, while Task 20 did not find a Graphiti-specific principal/authorization policy in that configuration surface.

This should **not** be generalized into a claim that FastMCP or an external deployment cannot add authentication. The narrower conclusion is:

- Graphiti's reference server itself should not be treated as the authorization owner;
- exposing it beyond a trusted local boundary requires explicit outer network authentication/TLS/firewall policy;
- MCP tool calls must be wrapped by ACL/Vera principal/project/memory-domain/effect policy;
- `clear_graph` and deletion/write tools are high-authority effects, regardless of their MCP schemas.

## 15. Observability is useful but intentionally non-authoritative

Graphiti contains an optional tracer abstraction with OpenTelemetry support and a no-op fallback. `add_episode` spans can record fields such as:

- episode UUID/source/reference time,
- group ID,
- node/edge counts,
- invalidated edge count,
- previous episode count,
- entity/edge type counts,
- community counts,
- duration.

LLM generation paths also emit tracing spans and prompt/model metadata.

The tracer intentionally suppresses tracing failures so telemetry does not break memory operations. This is sensible operationally, but it means telemetry cannot be the authoritative proof that a memory transition settled.

Vera needs separate:

- operational traces,
- source/evidence provenance,
- durable memory mutation ledger,
- validation/reconciliation results,
- security/audit evidence.

## 16. Evaluation evidence is encouraging but should not be overgeneralized

The 2025 Zep paper evaluates a Graphiti-powered Zep system on DMR and LongMemEval.

Important reported results include:

- DMR: Zep 94.8% with GPT-4-turbo versus MemGPT 93.4%; full-context baseline 94.4%.
- With GPT-4o-mini, Zep reported 98.2% versus full-context 98.0% on DMR.
- The paper itself argues DMR is too small/easy for modern long-context models and poorly represents complex real-world memory.
- LongMemEval is substantially larger (about 115K tokens average conversation history) and is a more relevant long-term-memory signal.
- The paper reports materially better overall LongMemEval performance and much smaller retrieved context/latency than full-context baselines, but not every subcategory improved.
- Experimental graph construction used GPT-4o-mini; BGE-m3 was used for embedding/reranking in the described experiments.

### Why these are not current Graphiti OSS guarantees

- paper experiments are Zep-system experiments, not a frozen current self-hosted Graphiti v0.30.1 benchmark;
- current extraction/prompt/backend code has evolved;
- model/provider choice strongly affects graph correctness;
- current open bugs show database/concurrency/invalidation behavior can dominate memory quality;
- benchmark answer accuracy does not directly measure memory poisoning, false invalidation, tenant isolation, crash consistency, or local small-model safety.

Later ACL/Vera evaluation should therefore reproduce task-specific memory fixtures under the exact intended local/cloud deployment.

## 17. High-value Graphiti regression fixtures for Vera/ACL

1. **False contradiction / unrelated relation** — new fact shares one endpoint but different relation/target; old true fact must remain live.
2. **True replacement** — same semantic relationship changes; prior fact becomes historical with correct valid/invalid times.
3. **New lower-trust contradiction** — recent low-trust source conflicts with verified high-trust source; do not silently supersede.
4. **Missed contradiction** — small/local judge fails to flag genuine replacement; conflict detector should expose stale/live disagreement.
5. **Born-retired edge** — later candidate must not cause new edge to be retired without structural/trust eligibility.
6. **Cross-group concurrent ingestion** — simultaneous groups must never cross physical/logical memory domains.
7. **Cross-group concurrent read/write** — read results remain in requested domain while other groups ingest.
8. **Backend parity** — same fixture on Neo4j/FalkorDB yields identical logical group/current-history semantics.
9. **Crash during main write** — episode/entities/facts are all committed or all absent.
10. **Crash during post-write saga maintenance** — recovery detects incomplete saga links rather than silently declaring settled.
11. **Crash during episode delete** — partial cleanup is detected/reconcilable.
12. **Embedding null/corrupt vector** — one bad record cannot make all memory retrieval unavailable.
13. **Embedding-dimension migration** — old and new vectors cannot silently mix.
14. **Local structured-output parse** — exact local model/runtime returns valid extraction schemas across repeated runs.
15. **Local semantic maintenance** — duplicate/contradiction correctness is measured independently of syntax validity.
16. **Current vs historical query** — default live-memory retrieval excludes invalidated facts; history query returns them with validity windows.
17. **Provenance round trip** — retrieved fact maps back to the exact source episodes.
18. **Raw-content-retention off** — system accurately reports that semantic provenance cannot reproduce/quote absent raw source content.
19. **Prompt-injection episode** — malicious source text cannot change trusted memory policy/tool/credential authority.
20. **MCP destructive tool authorization** — delete/clear/write require ACL/Vera-owned authority independent of tool visibility.
21. **Community drift/refresh** — incremental communities are detectably refreshed/rebuilt under defined policy.
22. **Telemetry loss** — failed trace exporter does not hide mutation settlement state.

## 18. Candidate architectural invariants carried forward

These are research conclusions/questions for later synthesis, **not implementation decisions**.

1. Raw observation, semantic fact, current belief, summary, and trusted policy are separate classes.
2. Every derived fact retains source/evidence lineage where feasible.
3. Temporal validity and source authority are separate dimensions.
4. Newer evidence does not automatically supersede stronger evidence.
5. Fact invalidation is a privileged reversible state transition.
6. LLM contradiction output is advisory until deterministic/trust constraints pass.
7. Current-memory and historical-memory retrieval are distinct APIs/policies.
8. A group/database name is not authenticated tenant identity.
9. Every memory mutation carries principal + domain + source + operation identity.
10. Per-request backend routing must not mutate shared global state.
11. Memory-domain isolation gets concurrency regression tests.
12. Main episode+semantic persistence should be transactionally settled.
13. Derived maintenance outside the core transaction has explicit pending/recovery states.
14. Delete is a multi-object effect requiring reconciliation after crash.
15. Database/provider/index schema is part of memory deployment identity.
16. Embedding model/dimension is durable schema identity requiring migration.
17. Bad embeddings are quarantined/repaired rather than poisoning all retrieval.
18. Local-model qualification measures semantic memory maintenance, not merely structured JSON generation.
19. Runtime/provider/prompt/schema versions are part of memory benchmark identity.
20. Retrieval rank is not truth/confidence.
21. Ingested episode text remains untrusted even when stored in a trusted database.
22. Retrieved memory cannot overwrite governance/tool/credential policy by textual instruction.
23. MCP memory tools remain below ACL/Vera-owned authorization.
24. Operational OpenTelemetry is not authoritative memory/effect evidence.
25. Community/summary layers are rebuildable derivatives rather than sole evidence.
26. A memory system should expose uncertainty/conflict rather than force premature last-write-wins consolidation.
27. Graphiti-style temporal graph and Letta-style curated persistent memory are complementary candidate planes, not automatically competing one-for-one architectures.

## 19. What Graphiti does not solve for ACL/Vera

Task 20 found no basis to treat Graphiti as a replacement for:

- ACL task/project scheduler,
- distributed writer leases/fencing,
- process/container sandboxing,
- tool/effect authorization,
- credential broker/vault,
- exactly-once external-effect ledger,
- independent verifier-owned acceptance,
- protected governance/policy configuration,
- curated assistant identity/persona memory,
- epistemic source/trust/confidence policy,
- full user/tenant authentication/governance,
- crash-consistent coordination across every derived maintenance operation.

Graphiti is best evaluated as a **temporal semantic memory engine/component** underneath those outer controls.

## 20. Later comparison questions

Do not answer these in Task 20; retain them for component synthesis:

1. Should Vera use Graphiti directly as temporal semantic memory, copy its data model/invariants, or use a simpler custom temporal store?
2. Should Graphiti and Letta-style curated memory coexist as separate planes?
3. Which graph backend is safe/economical on the user's local hardware and Windows/Linux topology?
4. Can a local model reliably perform Graphiti entity/fact/contradiction maintenance at acceptable false-invalidation rates?
5. Which memory operations require a cloud/reasoning model even if normal worker tasks remain local?
6. What source-trust layer should sit above Graphiti's episode/fact model?
7. How should conflicts remain visible instead of auto-invalidating in high-risk domains?
8. What minimal provenance fields are necessary for Vera to explain and repair memory?
9. How should Graphiti memory be backed up, migrated, checked, and repaired across embedding/backend upgrades?
10. Should current/history retrieval be exposed through MCP, an ACL-owned adapter, or a narrower internal API?

## Primary sources inspected

### Canonical repository/current source
- https://github.com/getzep/graphiti
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/README.md
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/pyproject.toml
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/nodes.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/edges.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/graphiti.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/utils/bulk_utils.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/utils/maintenance/node_operations.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/utils/maintenance/edge_operations.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/search/search_filters.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/driver/neo4j/operations/search_ops.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/decorators.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/llm_client/openai_generic_client.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/graphiti_core/tracer.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/mcp_server/src/graphiti_mcp_server.py
- https://github.com/getzep/graphiti/blob/b943c9e8486cdc7fe6cb2f4cfe151ae53f0a884d/mcp_server/src/config/schema.py

### Current/open failure evidence
- https://github.com/getzep/graphiti/issues/1728 — broad invalidation candidates / collateral fact retirement
- https://github.com/getzep/graphiti/issues/1666 — measured contradiction degradation with non-reasoning small model
- https://github.com/getzep/graphiti/issues/1676 — concurrent FalkorDB group write corruption
- https://github.com/getzep/graphiti/issues/1795 — FalkorDB shared-driver/read routing consequences
- https://github.com/getzep/graphiti/issues/1328 — null/dimension-mismatched embeddings can break similarity search
- https://github.com/getzep/graphiti/issues/1645 — current-vs-invalidated fact search behavior/configuration
- https://github.com/getzep/graphiti/issues/868 — Ollama/local structured extraction failure example (older version; retained only as compatibility evidence)
- https://github.com/getzep/graphiti/issues/912 — local DeepSeek/Ollama schema failure example (older version; retained only as compatibility evidence)

### Architecture/evaluation paper
- https://arxiv.org/abs/2501.13956 — *Zep: A Temporal Knowledge Graph Architecture for Agent Memory*

## Explicit non-conclusions

Task 20 does **not** conclude that:

- Graphiti should be adopted or forked;
- Graphiti should replace Letta or vice versa;
- a graph database is necessarily the correct Vera memory store;
- Neo4j, FalkorDB, Neptune, or another backend has won selection;
- any local model is safe enough to perform unattended canonical memory invalidation;
- Zep benchmark results automatically apply to current OSS Graphiti;
- Graphiti `group_id` is an adequate security/tenant boundary;
- Graphiti solves ACL scheduling, tool authority, credentials, external effects, or verification;
- Microsoft Agent Framework has been researched.

**Stop boundary:** Task 20 ends with Graphiti research and documentation. Microsoft Agent Framework is next only after separate authorization.
