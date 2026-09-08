# Knowledge Architecture Evidence Campaign State

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `research/agent-landscape`  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Status:** KA-4 complete; stopped before next task  
**Historical starting checkpoint:** `76a262889a4577613520931cc475e8888844f8fc`

## Governing plan

Read `CAMPAIGN_PLAN.md` before doing any work in this campaign.

The completed Tasks 1–31 project-by-project campaign remains historical evidence. Do not restart it and do not rewrite its catalogs.

## Completed tasks

### KA-1 — Graphiti Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/graphiti.md`

### KA-2 — Mem0 Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/mem0.md`

### KA-3 — Letta Code Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/letta-code.md`

### KA-4 — LlamaIndex Knowledge-Architecture Revisit

**Status:** complete.  
Detailed report: `projects/llamaindex.md`

Cumulative ledgers updated:

- `invariants.md`
- `failure-patterns.md`

## KA-4 boundary and verification

- Re-read root research governance, campaign plan/state, cumulative invariant/failure ledgers and the historical Task 29 LlamaIndex report.
- Verified the clean ACL starting branch head at `1869aecfdf97ff25e12b9e4ae77f326018a73742` before final KA-4 writes.
- Reverified `run-llama/llama_index` current `main` at `d2ac544a27c73d2a68e9c57efec4b2ac0ef99892`, with `llama-index-core` version `0.14.24`.
- Confirmed that this is the same upstream revision used by historical Task 29, so KA-4 is a deeper knowledge-substrate analysis rather than an upstream-delta study.
- Inspected current document/node/resource identity, node parsing/source relationships, ingestion/document management, transformation caching, docstore/index/vector/graph/property-graph storage planes, metadata/filter semantics, retrieval fusion, citation projection, vector memory, persistence and replacement/delete behavior.
- Rechecked current/recent issue/PR evidence relevant to identity, derivation, filtering, multi-store settlement, context freshness, memory scope, deletion and replacement.
- Evaluated LlamaIndex against all 26 campaign evidence questions.
- Distinguished current defects from historical reports: notably, #22543 describes a recent Managed LanceDB delete-predicate defect, but pinned current source already escapes document IDs; it is not recorded as a current-main defect.
- Treated #21666 as memory-poisoning design/security signal rather than proof of a confirmed exploit.
- Updated recurrence instead of duplicating existing Graphiti/Mem0/Letta concepts.
- Added 2 materially distinct LlamaIndex-derived invariant candidates: KA-I-036–037.
- Added 4 materially distinct LlamaIndex-derived failure patterns: KA-F-033–036.
- Moved KA-I-002, KA-I-013, KA-I-026, KA-I-030 and KA-I-035 from single-task candidates to cross-project **reinforced** status.
- Reinforced/broadened KA-F-002, KA-F-012 and KA-F-029 with independent LlamaIndex evidence and added recurrence to several existing backend/filter/settlement/deletion/projection families.
- Did not select LlamaIndex, a vector store, graph store, SQL store, document store, filesystem, final schema, ontology, retrieval engine or conceptual architecture.
- Did not modify historical `catalog.jsonl`, `catalog-part2.jsonl`, root research state or historical project reports.
- Did not begin Mastra research.

## Highest-value KA-4 findings

1. **Source, derivative and presentation identities must remain distinct.** LlamaIndex uses source relationships between documents and derived nodes; #22133 shows one-to-many derivatives are lost when source/ref-document ID is reused as derivative uniqueness, while #22537 shows citation chunks break downstream source addressing when parent IDs/offsets are copied into a new projection.
2. **Lineage is not identity reuse.** A derived chunk/citation should have its own identity and retain an explicit relation to its source/parent.
3. **Resource identity, locator and observed content digest differ.** Current `MediaResource.hash` hashes the path/URL string when only a locator is available; a mutable object at the same locator therefore has different semantics from a content-addressed version.
4. **Source provenance is useful but incomplete without derivation provenance.** SOURCE relations, offsets, ref-doc mappings and `triplet_source_id` are valuable, but a general derivation record still needs model/prompt/parser/runtime/source-revision/settlement identity.
5. **Transformation caches are generation-sensitive derived state.** LlamaIndex hashes node content plus serialized transformation configuration, but no universal implementation/model/prompt generation manifest covers every behavior-bearing dependency.
6. **Property graphs are derived semantic projections, not automatically canonical relationship truth.** Default extraction is model-driven and lacks generic verification/confidence/world-valid-time semantics.
7. **Graph absence is not false.** Extraction can be capped, fail parsing, be filtered or be deleted; missing derived triples therefore cannot establish negative knowledge.
8. **Property-graph source deletion can miss derivatives.** Current `PropertyGraphIndex._delete_node()` deletes by source node ID rather than using the provenance-aware `delete_llama_nodes()` path that follows `triplet_source_id`.
9. **Relationship and entity lifecycles need governed cardinality semantics.** The simple property graph can delete relation endpoints along with one triplet, which is unsafe as a universal many-to-many lifecycle rule.
10. **High-level filter vocabulary is not a backend semantic guarantee.** Core/local and external stores differ in supported operators/nesting/query modes, and current PGVector source plus #22475 demonstrate backend query construction can alter intended predicate behavior.
11. **Composite retrieval is an execution contract.** `QueryFusionRetriever` makes candidate-producing retrievers, query expansion, dedup identity, fusion math, weights and final cutoff order part of realized retrieval behavior; this independently reinforces KA-I-026.
12. **Retrieval/fusion scores remain relevance signals.** LlamaIndex reuses one score field across vector, sparse and multiple fusion algorithms; that does not encode truth, confidence, verification or authority.
13. **Context construction is separate from host state and retrieval.** Metadata projection, postprocessors, citation re-chunking, synthesizers and state prompts alter model-visible context; #22248 shows host workflow state can change while the next LLM prompt remains stale.
14. **Request scope must be invocation-local.** Current `VectorMemoryBlock` plus #22701 show a session filter written into reusable query state, causing later sessions to remain pinned to the first session and mutating caller-owned objects.
15. **Namespace/session IDs are routing state, not principals.** They can support isolation but are not an authorization model.
16. **Persistent memory remains untrusted content.** Retrieval/persistence does not make model-visible content policy or execution authority.
17. **Multi-store mutation/persistence has settlement phases.** Docstore, vector store, index store, graph store, cache and persisted files are independent planes without one universal cross-store transaction/generation contract.
18. **Safe replacement cannot be delete-then-insert.** Current `update_ref_doc()` deletes the old active version before inserting the new one; #22733 documents the failure window, independently reinforcing Letta's staged-replacement invariant.
19. **Delete from an index is not erasure.** `delete_ref_doc()` can intentionally retain docstore state, while vector/graph/cache/source/backups have separate lifecycle semantics.
20. **Serialization compatibility is not semantic re-derivation.** Historical embeddings, graph extractions and caches do not become equivalent to newly derived state merely because their serialized records still load.
21. **Hash meaning must be explicit.** Node/resource hashes are used for dedup, change detection and retrieval fusion, but they can represent content+metadata state, locator fingerprints or other operational identities rather than one universal semantic identity.
22. **LlamaIndex is strongest as a reference for derivation/retrieval architecture, not as a complete epistemic truth substrate.** Temporal validity, verification/conflict state, normalized applicability and authority remain outside the ordinary core node/index model.

## Current task

**No task is currently assigned.**

The campaign is stopped after KA-4.

## Planned next candidate

**KA-5 — Mastra Knowledge-Architecture Revisit**

This is the next planned revisit in `CAMPAIGN_PLAN.md`, but it is **not authorized merely by queue order**.

Do not begin KA-5 until the user explicitly instructs the next bounded task to start.

When authorized, Mastra must be researched as its own task and then stopped before LangGraph.

## Prohibited work at this state

Do not:

- begin Mastra or any later revisit without explicit authorization;
- synthesize the final conceptual schema;
- select a database/storage engine;
- implement retrieval;
- create embeddings;
- migrate the old catalogs;
- benchmark models;
- implement ACL or Vera;
- run autonomous workers.

## Planned revisit queue

For orientation only; queue order is not authorization:

1. ~~KA-1 Graphiti~~ — complete
2. ~~KA-2 Mem0~~ — complete
3. ~~KA-3 Letta Code~~ — complete
4. ~~KA-4 LlamaIndex~~ — complete
5. KA-5 Mastra — not started / not authorized
6. LangGraph
7. Google ADK
8. Microsoft Agent Framework
9. OpenAI Agents SDK
10. Model Context Protocol

After these, the campaign plan requires a bounded coverage scan before any additional project revisit is promoted.

## Stop point

KA-4 LlamaIndex research is complete and saved. No Mastra research, cross-project synthesis, gap research, retrieval-requirements task, architecture selection or implementation work has begun.
