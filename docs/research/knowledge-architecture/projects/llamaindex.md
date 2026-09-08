# KA-4 — LlamaIndex Knowledge-Architecture Revisit

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-4  
**Research date:** 2026-09-08  
**ACL branch:** `research/agent-landscape`  
**ACL parent checkpoint:** `1869aecfdf97ff25e12b9e4ae77f326018a73742`  
**Canonical upstream:** `run-llama/llama_index`  
**Current upstream revision inspected:** `d2ac544a27c73d2a68e9c57efec4b2ac0ef99892`  
**Current core package version observed:** `0.14.24`  
**Historical Task 29 revision:** `d2ac544a27c73d2a68e9c57efec4b2ac0ef99892`  
**Status:** bounded revisit complete; no architecture, database, storage engine, ontology, framework, retrieval engine, benchmark or implementation selection made.

---

## 1. Task boundary

KA-4 revisits **LlamaIndex only** through the Knowledge Architecture Evidence Campaign question:

> What does current primary evidence from LlamaIndex tell us about building a durable, general knowledge substrate for ACL, Vera and future domains?

The historical Task 29 report studied LlamaIndex primarily as an agent/RAG/workflow platform. KA-4 deliberately does not repeat that campaign. It goes deeper into the knowledge mechanics that matter even if ACL/Vera never adopt LlamaIndex itself:

- source documents and resources;
- derived nodes/chunks and their identities;
- source relationships and locators;
- ingestion transformations and transformation caching;
- document hashes and document management;
- docstore, index store, vector stores, graph stores and property graph stores;
- multi-store mutation and persistence settlement;
- metadata/filter semantics across backends;
- structured, graph, lexical, semantic and composite retrieval;
- context construction and metadata projections;
- citation projections and source traceability;
- property-graph extraction and deletion;
- persistent vector memory scope;
- deletion, replacement, recovery and retention;
- schema/version/derivation evolution;
- epistemic and temporal gaps;
- current/recent failure evidence that exposes architecture-level risks.

KA-4 does **not**:

- choose LlamaIndex for ACL or Vera;
- choose a vector store, graph store, SQL store, document store or filesystem;
- choose a final canonical schema or ontology;
- equate LlamaIndex `Document`/`Node` classes with the future canonical model;
- implement ingestion, retrieval, memory or graph code;
- benchmark models or retrieval engines;
- migrate either historical research catalog;
- start KA-5 Mastra;
- perform final cross-project synthesis.

---

## 2. Evidence discipline

This report separates five evidence categories.

1. **Observed current mechanism** — behavior inspected directly in current source/docs at the pinned revision.
2. **Failure evidence** — issue, merged regression fix, reproduction or current-source defect that exposes a failure mode.
3. **Architectural lesson** — a requirement/warning derived from the mechanism or failure.
4. **Confidence** — how strongly the inspected evidence supports the lesson.
5. **Non-conclusion** — what the evidence does not establish.

Issue status is not treated as proof of current source behavior. This mattered during KA-4: issue #22543 still describes unescaped Managed LanceDB delete predicates, but the pinned current source now escapes apostrophes in document IDs. The issue remains useful historical failure evidence, not a current-main defect. Conversely, issue #22475's PGVector metadata-key interpolation remains visible in the pinned current source and is therefore current evidence.

The upstream `main` revision did not change between historical Task 29 and KA-4. This revisit is therefore a deeper analysis of the same source revision rather than a freshness delta.

---

# 3. Executive assessment

LlamaIndex is one of the campaign's strongest references for **derived knowledge construction and retrieval composition**, but it is not a general epistemic truth substrate.

Its strongest reusable ideas are:

1. **Source documents and derived nodes are explicitly related but separately identified.** Nodes carry a `SOURCE` relationship rather than simply pretending to be the source document.
2. **A source may legitimately produce many derivatives.** Current node parsers support one document → many chunks; merged PR #22133 is concrete evidence that using source identity as derivative uniqueness collapses data.
3. **Presentation projections need their own identity.** Merged PR #22537 fixed citation chunks that inherited the retrieved source node's ID and offsets.
4. **Transformations are first-class pipeline stages.** Parsing, extraction and embedding are explicit operations rather than hidden retrieval magic.
5. **Source lineage, derivation identity and retrieval score are different concerns.** The framework exposes useful pieces of each but does not combine them into an epistemic record.
6. **Storage planes are explicitly separate.** `StorageContext` distinguishes docstore, index store, vector stores, graph store and property graph store.
7. **That separation creates settlement obligations.** Writes, deletes and persistence occur across multiple stores without one atomic cross-store transaction or generation manifest.
8. **High-level metadata/filter objects are not a backend semantic guarantee.** Operators, nesting, query modes and even predicate compilation vary by backend.
9. **Composite retrieval is an execution plan, not a label.** `QueryFusionRetriever` specifies candidate-producing retrievers, query expansion, dedup identity, fusion math, weights and final cutoff order.
10. **Property graphs are derived semantic projections.** Default graph extraction uses an LLM, stores `triplet_source_id`, and provides no generic verification/confidence/world-valid-time state for extracted relations.
11. **Graph-shaped data is not automatically canonical relationship truth.** Typed relation labels can still be model-derived and incomplete.
12. **Deletion is multi-plane and semantics-dependent.** `delete_ref_doc()` can intentionally leave the docstore; PropertyGraph deletion can leave source-derived triples; backend deletion capabilities differ.
13. **Safe replacement is not the same as delete-then-insert.** Current `update_ref_doc()` performs destructive delete followed by insert; open #22733 documents the failure window.
14. **Resource locator and resource content identity are not the same.** `MediaResource.hash` hashes the path string or URL string when only a locator is present; it does not dereference those locators to hash mutable external content.
15. **Persistent retrieval scope must be invocation-local.** Open #22701 and current `VectorMemoryBlock` source show a session filter being written into reusable `query_kwargs`, pinning later sessions to the first one.
16. **Context construction is a separate layer.** Metadata can have different LLM and embedding projections, retrievers can post-process nodes, citation engines re-chunk them, and agent state projection can become stale independently of host state (#22248).
17. **Derived absence is not negative knowledge.** Property-graph extraction can be capped or fail closed to an empty set; missing triples therefore cannot mean “false.”
18. **LlamaIndex's hashes are operational identities, not universal content-addressed truth.** Hash meaning changes by node/resource type and does not include every derivation profile dimension.

The strongest KA-4 synthesis is:

> A durable knowledge substrate must preserve a chain of distinct identities — source/resource, derived record, semantic entity/relation, retrieval hit and presentation projection — while separately tracking transformation profile, settlement state, epistemic state and authority. Reusing one ID or one hash across those layers creates silent corruption.

---

# 4. Current upstream boundary

## 4.1 Revision and package profile

Current upstream `run-llama/llama_index` `main` was verified at:

`d2ac544a27c73d2a68e9c57efec4b2ac0ef99892`

Current core version in `llama-index-core/pyproject.toml`:

`0.14.24`

The historical Task 29 report inspected the same commit. There was no upstream delta to reconcile.

## 4.2 Why “LlamaIndex 0.14.24” is still too coarse

Behavior in the inspected source depends on more than the core package version:

- vector-store integration and version;
- graph-store integration and version;
- embedding provider/model;
- LLM/provider used for extraction/query expansion/synthesis;
- parser/transformation class and configuration;
- metadata/filter backend support;
- whether the vector store stores text;
- whether docstore/document management is attached;
- selected `DocstoreStrategy`;
- query mode, fusion mode, top-k, alpha/weights and postprocessors;
- callback/instrumentation configuration;
- persisted cache generation;
- local versus remote stores and their transaction semantics.

This independently reinforces the campaign's realized-profile principle: project/package version alone cannot identify knowledge behavior.

---

# 5. The useful state planes

A central contribution of LlamaIndex is that it already exposes several planes that should not be collapsed.

## 5.1 External/raw resource plane

Input may originate in:

- files;
- URLs;
- APIs;
- remote object stores;
- databases;
- multimodal data;
- application-created `Document` objects.

LlamaIndex readers often convert those resources into `Document` objects, but the external object remains a different thing from the `Document` representation.

## 5.2 Document/source representation

`Document` is a node subtype intended to connect to data sources. It has an application-visible ID and may carry metadata and multimodal resources.

A `Document` is useful source representation, but it is not automatically a complete resource registry:

- external locator may live in metadata or `MediaResource`;
- source content checksum semantics vary by resource form;
- resource version/ETag/object-version is not a generic required field;
- ownership/sensitivity/retention is not a first-class policy envelope;
- a generated UUID is not external canonical identity.

## 5.3 Derived node/chunk plane

Parsers and transformations turn documents/nodes into other nodes.

Derived nodes can have:

- their own `id_`;
- source relationship;
- character offsets;
- copied/merged metadata;
- previous/next/parent/child structural relationships;
- embeddings;
- transformation-produced metadata.

This is a strong positive separation from source identity.

## 5.4 Docstore plane

The document store maintains:

- serialized nodes;
- node hash metadata;
- document/ref-document mappings;
- source-document → derived-node ID lists;
- document hashes used for duplicate/change management.

This is partly canonical operational state for an index, but it is still not necessarily the application's canonical raw resource.

## 5.5 Vector-store plane

Vector stores hold embeddings and, depending on adapter, text/metadata/node representations.

They are derived retrieval state.

## 5.6 Index-structure plane

Index-specific structures are stored separately in the index store.

They are derived organizational/query state.

## 5.7 Graph/property-graph plane

PropertyGraphIndex can store:

- source chunk nodes;
- extracted semantic entity nodes;
- extracted semantic relations;
- optional embedded KG nodes;
- source markers linking semantic extraction to chunk IDs.

The default semantic graph is derivative, not raw evidence.

## 5.8 Ingestion-cache plane

Transformation outputs can be cached and restored later from local or remote KV storage.

The cache is neither raw evidence nor canonical truth. It is a performance derivative whose generation identity matters.

## 5.9 Retrieval/context/citation plane

Retrieved nodes are scored results, then can be:

- post-processed;
- fused;
- reranked;
- truncated;
- metadata-projected;
- citation-rechunked;
- formatted into LLM prompts.

Each step can change what the model sees without changing the underlying source/store.

---

# 6. Stable identity: source, derivative and projection must differ

## 6.1 Current node IDs

`BaseNode.id_` defaults to a random UUID.

`default_id_func()` used by node parsing also returns a fresh UUID.

Therefore a repeated parse of the same source is not, by default, guaranteed to reproduce the same derived node IDs.

### Architectural lesson

A future canonical design must decide explicitly which IDs are:

- stable semantic identities;
- source/resource identities;
- derivation-run identities;
- derivative-record identities;
- ephemeral retrieval/projection identities.

Random UUIDs are valid record identities, but they do not imply stable semantic identity across re-derivation.

### Non-conclusion

LlamaIndex supports caller-supplied `id_func`, so deterministic derived IDs are possible. KA-4 does not claim random IDs are mandatory.

---

## 6.2 Source relationship instead of identity reuse

`build_nodes_from_splits()` creates a `SOURCE` relationship from each derived split to `ref_doc.as_related_node_info()`.

That relationship carries:

- source node ID;
- source node type;
- source metadata;
- source hash.

This is a useful lineage shape:

`source identity -> derived identity`

rather than:

`source identity == derived identity`

---

## 6.3 Failure evidence: #22133 collapsed one source's many derivatives

Merged PR #22133 fixed an ingestion upsert bug where nodes were collected in a dictionary keyed by `ref_doc_id`.

Multiple chunks from one source share the same ref-document ID. Using that source ID as the dictionary key meant later chunks overwrote earlier chunks, and only one derivative survived to embedding/storage.

The current source uses a list rather than collapsing the nodes by source ID.

### Architectural lesson

A source identity is a **grouping/lineage key**, not the uniqueness key for each derivative.

The relationship is commonly one-to-many:

`source resource -> many chunks -> many extracted assertions/relations -> many retrieval projections`

### Confidence

High. The failure was fixed by a merged maintainer-approved code change and the current source reflects the corrected cardinality.

---

# 7. Presentation identity: citations are not their retrieved parent

Merged PR #22537 fixed `CitationQueryEngine` behavior that copied the full retrieved source node into every citation chunk.

Before the fix:

- all citation chunks cut from one retrieved node inherited the same `id_`;
- all inherited the parent source's character offsets;
- consumers deduplicating by node ID could collapse many citation chunks into one;
- highlighting could point at the entire parent span rather than the cited chunk.

Current source deliberately:

- removes `id_` before constructing each citation chunk, producing a new node ID;
- clears `start_char_idx`/`end_char_idx` because the old offsets no longer describe the re-chunked content;
- preserves metadata, relationships and score;
- therefore preserves source traceability without reusing source/projection identity.

### Architectural lesson

Identity and lineage are different mechanisms.

When content is transformed into a new presentation unit:

- give the projection its own identity;
- preserve an explicit link to its parent/source;
- preserve only locators that still describe the new unit;
- never copy offsets/checksums/IDs whose semantics changed.

### New candidate invariant contribution

This finding combines with #22133 to support a new KA-4 candidate:

**Source, derivative and presentation-projection identities must remain distinct; lineage is represented by relations, not identity reuse.**

---

# 8. Source locators, logical resources and content digests are different

`MediaResource` can carry:

- raw `data`;
- `text`;
- filesystem `path`;
- `url`;
- MIME type;
- embeddings.

Its current `hash` implementation uses:

- actual text when text exists;
- SHA-256 of stored binary data when binary data exists;
- SHA-256 of the **path string** when a path exists;
- SHA-256 of the **URL string** when a URL exists.

It does not read the file/URL to hash the referenced external bytes merely because a locator is present.

`Node.hash` then incorporates the hashes of its media resources plus metadata.

## 8.1 Consequence for mutable locators

For a path-only or URL-only resource:

- the file/object can change at the same locator;
- the locator-derived hash can remain unchanged;
- a caller that treats the hash as a proof of content equality can miss the change.

Similarly, the same bytes moved to a different path/URL receive a different locator-derived hash.

### Architectural lesson

A general resource model needs separate concepts for:

- **logical resource identity**;
- **locator/address**;
- **locator version where available** (ETag, object version, commit, etc.);
- **observed content digest**;
- **observation/fetch time**;
- **media type/size**;
- **extracted representation**;
- **derivation profile**.

A locator fingerprint can be useful, but it must not masquerade as a content checksum.

### Confidence

High for the current source semantics; moderate for operational consequence because many readers also populate text/data whose change would affect the overall node hash.

### Non-conclusion

KA-4 does not claim every LlamaIndex reader uses path-only/URL-only resources or that all ingestion updates are affected.

---

# 9. Provenance: useful source links, incomplete derivation envelopes

LlamaIndex provides several useful provenance pieces.

## 9.1 `SOURCE` relationship

Derived nodes can point to a source node via `RelatedNodeInfo`.

## 9.2 Character offsets

Node parsers can record `start_char_idx` and `end_char_idx` after locating derived text within a source document.

These are valuable source locators when they remain semantically valid.

## 9.3 Ref-document mappings

The docstore tracks source/ref-document ID to derived node IDs.

## 9.4 Callback transformation I/O

`NodeParser` callback events expose input documents and output nodes at the event boundary.

This is useful observability lineage.

## 9.5 Property-graph source markers

PropertyGraphIndex writes `triplet_source_id` onto extracted graph entities/relations, pointing back to the chunk node from which the graph material was extracted.

## 9.6 What is still missing for a general canonical provenance record

The standard core node/relationship objects do not require a generic derivation envelope containing all of:

- exact source resource identity/version/digest;
- source locator/range;
- ingest run ID;
- transformation class + implementation source revision;
- model/provider/runtime identity;
- prompt/schema/parser identity;
- transformation input revision;
- transformation output settlement state;
- explicit/inferred/verified status;
- confidence/trust class;
- reviewer/verification event.

### Architectural lesson

Source provenance and transformation provenance must remain separately addressable.

This independently reinforces KA-I-023 and KA-F-020.

---

# 10. Transformation cache identity is useful but incomplete

`IngestionPipeline` caches transformation results.

`get_transformation_hash()` hashes:

1. node content with metadata;
2. the serialized transformation configuration after removing unstable memory-address strings.

That makes configuration changes part of cache identity, which is useful.

However, the cache key does not generically include an explicit:

- LlamaIndex source commit/package build;
- transformation implementation digest;
- external model artifact revision;
- provider/runtime revision;
- prompt revision unless serialized in the component;
- structured-output/parser revision unless serialized in the component.

The cache itself simply maps the computed key to serialized output nodes.

## 10.1 Architecture risk

If implementation behavior changes while the serialized transformation configuration remains identical, a persisted cache can represent an older derivation profile under a key that still matches.

### Architectural lesson

Derived/cache identity must include every behavior-bearing profile dimension needed for reproducibility, or carry an explicit generation version that invalidates/rebuilds the derivative.

This independently reinforces KA-I-018, KA-I-023 and KA-I-011.

### Confidence

High that the current cache key lacks a generic implementation/source revision field. Moderate on production frequency; KA-4 did not locate a current issue demonstrating this exact stale-cache-after-upgrade failure.

---

# 11. Epistemic state is mostly outside the core node model

Core `BaseNode` provides:

- ID;
- content/resources;
- metadata;
- relationships;
- embedding;
- hash.

It does not require a generic epistemic state such as:

- observed;
- user-explicit;
- inferred;
- model-extracted;
- third-party claim;
- verified;
- disputed;
- provisional;
- confidence;
- source-trust class.

Applications can put such information in arbitrary metadata, but that is not the same as a governed semantic contract.

## 11.1 Property-graph extraction makes the gap concrete

`SimpleLLMPathExtractor` asks an LLM to extract triples from node content.

Extracted results become:

- `EntityNode` objects;
- `Relation` objects.

The default output does not attach generic verification/confidence/dispute state.

Therefore a relation shaped like:

`Alice --WORKS_AT--> ExampleCo`

can be a model extraction from a chunk rather than authenticated canonical truth.

### Architectural lesson

Graph shape and typed relation labels do not confer epistemic authority.

### Non-conclusion

Applications can attach arbitrary metadata or custom extractors. KA-4 does not claim LlamaIndex prevents explicit epistemic metadata.

---

# 12. Temporal truth is not a first-class general model

Core nodes, document hashes and graph relations provide operational storage/derivation state, but the inspected schemas do not define a general bitemporal truth model with:

- observation time;
- world-valid-from;
- world-valid-until;
- record/transaction time;
- correction time;
- supersession relationship;
- current versus historical truth status.

Dates can be stored in metadata and filtered, but arbitrary metadata is not equivalent to consistent temporal semantics.

## 12.1 Update semantics are replacement-oriented

`update_ref_doc()` in `BaseIndex` is explicitly implemented as:

`delete_ref_doc(..., delete_from_docstore=True) -> insert(document)`

That changes current index state. It does not preserve a generic old version as historically true inside the core index model.

### Architectural lesson

Index freshness and temporal truth are different concerns.

A RAG index can correctly replace stale retrieval material while still being insufficient as the canonical historical knowledge record.

---

# 13. Conflict and supersession: replacement is not epistemic reconciliation

LlamaIndex document management detects content/hash change and can remove/reprocess older index material.

That is useful for index freshness.

It does not answer semantic questions such as:

- which claim contradicted which older claim;
- whether both claims are valid in different times/scopes;
- which source is stronger;
- whether a correction is verified;
- whether an older claim must remain searchable as historical truth;
- whether a high-risk conflict should remain unresolved.

### Architectural lesson

The future knowledge model cannot treat document re-indexing or graph upsert as semantic supersession by itself.

This is supporting evidence for KA-I-006 but not a claim that LlamaIndex is intended to be a temporal truth engine.

---

# 14. Semantic entity identity in PropertyGraphIndex

Current `EntityNode.id` is derived from the entity's name string, with quote replacement.

That is convenient for graph construction but does not prove real-world identity.

Consequences of name-as-ID include the familiar identity-resolution risks:

- two different real people/devices/organizations with the same name can collide;
- aliases for one real entity can fragment;
- normalization policy becomes semantic identity policy;
- rename/change history is not automatically identity continuity.

### Architectural lesson

This independently reinforces KA-I-002:

**Internal semantic entity identity is distinct from external/source identity.**

### Non-conclusion

Custom graph stores/extractors can implement richer IDs. The finding is about the default core type semantics inspected here.

---

# 15. Property graphs are derived semantic projections, not canonical relationship truth

`PropertyGraphIndex` runs knowledge-graph extractors over input nodes.

Default behavior includes:

- `SimpleLLMPathExtractor`;
- `ImplicitPathExtractor`.

The index:

1. transforms source chunks;
2. collects extracted KG nodes/relations from metadata;
3. stamps `triplet_source_id` with the source chunk ID;
4. removes duplicates by graph node ID and source-node hash;
5. optionally embeds KG nodes;
6. upserts source chunk nodes;
7. upserts KG nodes;
8. upserts relations.

This is an excellent example of a **derived graph projection**.

The graph can be highly useful for relationship retrieval while remaining epistemically downstream of source evidence.

### Architectural lesson

KA-I-030 should be broadened/reinforced:

Derived semantic/association graphs — even when they contain typed relation labels — are distinct from canonical typed relationship assertions unless provenance, verification, scope and lifecycle semantics establish otherwise.

---

# 16. Graph extraction coverage and failure state

`SimpleLLMPathExtractor` has a maximum paths-per-chunk setting.

Parsing errors can be logged and, with default `raise_on_error=False`, produce an empty extraction for that chunk rather than aborting the whole pipeline.

Therefore graph absence can mean:

- the source truly contained no relevant relationship;
- the extractor did not recognize it;
- the max-path limit excluded it;
- the model produced an unparsable result;
- the extraction silently yielded no triples;
- the data was filtered/deleted later.

### Architectural lesson

Derived absence cannot be treated as `known false`.

Derived graph state needs coverage/error/generation/readiness metadata when downstream reasoning depends on completeness.

This reinforces KA-I-021, KA-I-027 and KA-F-027.

---

# 17. Property-graph deletion exposes derived-state reconciliation risk

`PropertyGraphStore` defines a provenance-aware helper, `delete_llama_nodes()`, which can find graph nodes by `triplet_source_id` or ref-document ID.

However, current `PropertyGraphIndex._delete_node(node_id)` calls the lower-level:

`property_graph_store.delete(ids=[node_id])`

rather than the provenance-aware helper.

Extracted entity/relation records are keyed by semantic graph IDs and carry the chunk source as a **property**, so deleting only the source chunk ID does not necessarily select the graph derivatives whose `triplet_source_id` points to that chunk.

### Architectural lesson

Deleting a source record and deleting everything derived from that source are different operations.

Derived-state cleanup should be driven by explicit provenance links and reconciled/verified across all derivative planes.

This is independent LlamaIndex evidence for KA-F-012 and KA-I-016.

### Confidence

High for the current call-path mismatch. KA-4 does not claim every external property-graph backend will leave exactly the same orphan set; backend behavior must be qualified.

---

# 18. Simple property graph relation deletion can remove shared endpoint nodes

`LabelledPropertyGraph.delete_triplet()` removes:

- the triplet;
- the subject node;
- the object node;
- the relation entry.

There is no reference-count/shared-neighbor test in that method before deleting endpoint nodes.

If an endpoint participates in other relations, deleting one triplet can therefore remove its node entry while other relation records still refer to it.

### Architectural lesson

Relationship lifecycle and entity lifecycle cannot be coupled by a naive “delete edge -> delete both nodes” rule when the model allows many-to-many graphs.

This is adjacent support for KA-I-007's governed relationship semantics.

### Confidence

High for the simple in-memory graph implementation. KA-4 did not find an issue proving the exact defect in a production external graph store, so it remains backend-scoped evidence rather than a new cross-project invariant.

---

# 19. Metadata has three simultaneous roles

Core `BaseNode.metadata` is explicitly described as data that can be:

- injected into text shown to the LLM;
- injected into text used to generate embeddings;
- used for vector-database metadata filtering.

Separate lists can exclude keys from:

- embedding projection;
- LLM projection.

This is a useful mechanism, but it means one metadata field can participate in three different semantics:

1. retrieval eligibility/filtering;
2. semantic embedding content;
3. model-visible prompt content.

### Architectural lesson

Policy/sensitivity/provenance metadata should not be treated as “just metadata.”

Each field needs explicit projection/use semantics:

- stored?
- queryable?
- model-visible?
- embedding-visible?
- exportable?
- authority-bearing?

This reinforces KA-I-019 and KA-I-024.

---

# 20. High-level filter vocabulary is not a backend contract

`MetadataFilter`/`MetadataFilters` expose a broad vocabulary including:

- equality/inequality;
- comparisons;
- IN/NIN;
- ANY/ALL;
- text match;
- contains;
- empty tests;
- nested AND/OR/NOT.

However, backend implementations differ.

## 20.1 Core SimpleVectorStore

The simple store evaluates a subset locally and explicitly rejects nested `MetadataFilters` in its local helper.

Its query modes are also narrower than the global `VectorStoreQueryMode` vocabulary.

## 20.2 SimplePropertyGraphStore

A properties dictionary is matched with `any(...)`, so multiple properties use OR-like matching rather than an implicit conjunction.

That is a concrete example of why a dictionary-shaped filter cannot be assumed to have universal semantics.

## 20.3 PGVector current source

Current PGVector `_build_filter_clause()` constructs SQL expressions from filter keys/values using string interpolation.

Open issue #22475 supplies a PostgreSQL reproduction in which a crafted metadata key changes the WHERE clause and returns every row instead of no rows.

The current pinned source still contains the interpolated filter key/value forms inspected in KA-4.

### Architecture lesson

A high-level filter object must not be used as a security/eligibility contract until the realized backend has been tested for:

- supported operators;
- nesting semantics;
- type coercion;
- null semantics;
- AND/OR/NOT semantics;
- parameter binding/escaping;
- failure behavior for unsupported predicates.

### New failure contribution

KA-4 adds a distinct backend failure class:

**Untrusted resource/filter identifiers are compiled into backend query syntax instead of being bound/escaped as data, altering retrieval/deletion eligibility.**

---

# 21. Recent issue #22543 is historical at current main, not current evidence

Issue #22543 reported Managed LanceDB deletion predicates built by concatenating unescaped document IDs.

The pinned current source now performs apostrophe escaping in:

- `delete_ref_doc()`;
- async delete;
- `delete_nodes()`;
- async delete nodes.

Therefore KA-4 records #22543 as a recent historical backend-adapter failure but does **not** list it as a current-main defect.

This is itself a useful research-process lesson:

> Open issue state can lag source state; architectural evidence must be version-qualified and rechecked against current implementation.

---

# 22. Composite retrieval is an execution contract

`QueryFusionRetriever` can run multiple retrievers over:

- the original query;
- LLM-generated alternate queries.

Every configured retriever can introduce candidates.

Then selected fusion logic:

- reciprocal-rank fusion;
- relative-score fusion;
- distance-based relative fusion;
- simple max-score fusion;

combines/deduplicates results by node hash.

Only after fusion is the final `similarity_top_k` applied.

## 22.1 Why this matters

“Hybrid” or “composite” is not enough to reproduce retrieval behavior.

The behavior identity includes:

- retriever set;
- which retrievers can introduce candidates;
- query-expansion model;
- query-generation prompt;
- generated query count;
- retriever-specific candidate limits;
- dedup key (`node.hash` here);
- score normalization;
- retriever weights;
- fusion mode;
- final top-k cutoff;
- postprocessing stages.

### Recurrence contribution

LlamaIndex independently reinforces KA-I-026, moving it from a Mem0-only candidate to cross-project evidence.

Mem0 demonstrated a hybrid system where semantic retrieval is the sole candidate gate. LlamaIndex demonstrates a contrasting implementation where multiple retrievers contribute candidates before fusion. Together they show why the candidate-entry contract must be explicit.

---

# 23. Retrieval score remains relevance, not truth

`NodeWithScore.score` is reused across:

- vector similarity;
- sparse rank;
- reciprocal rank fusion;
- normalized relative scores;
- distance-based scores;
- postprocessed results.

The same field can therefore contain values with very different mathematical meanings depending on retriever/fusion profile.

### Architectural lesson

Retrieval score must never be overloaded as:

- confidence the statement is true;
- confidence entity resolution is correct;
- verification state;
- permission;
- currentness.

This independently reinforces KA-I-010 and KA-F-016.

---

# 24. Structured, relationship, full-text and semantic retrieval are separate capabilities

LlamaIndex illustrates all four retrieval families but does not make them universally equivalent.

## 24.1 Structured/deterministic

Docstore operations support exact IDs, document hashes and ref-document mappings.

Metadata filters can provide structured restrictions where backend semantics are known.

## 24.2 Relationship

Property graph stores support node/triplet lookup and relationship traversal.

Structural node relationships support source/parent/child/previous/next navigation.

## 24.3 Full-text / lexical

Some backends/retrievers expose text-search/sparse/BM25-style retrieval.

Postgres hybrid search, for example, combines dense retrieval with PostgreSQL text-search ranking.

## 24.4 Semantic

Vector stores and embedding retrievers provide semantic similarity.

## 24.5 Composite

Fusion and backend-specific hybrid queries combine signals.

### Architectural lesson

A future ACL/Vera retriever should expose these as separate query capabilities that can be composed, rather than assuming one index replaces the others.

---

# 25. Context construction is a distinct layer

The material a model sees is not simply “whatever retrieval returned.”

Current LlamaIndex mechanisms include:

- metadata projection modes (`NONE`, `LLM`, `EMBED`, `ALL`);
- separate excluded-key lists;
- node postprocessors;
- citation re-chunking;
- prompt templates;
- response synthesizers;
- retrieval top-k/fusion cutoffs;
- memory block formatting;
- agent/workflow state prompting.

Each can change active context independently of canonical/source data.

## 25.1 Current failure evidence: #22248

Open #22248 reports that a tool can correctly update workflow state while the next LLM call receives a stale/raw state projection because a formatting flag is not refreshed.

The host state and model-visible state diverge.

### Architectural lesson

Context construction has its own freshness/settlement contract.

A canonical state update is not useful to reasoning until the model-visible projection is rebuilt from the correct revision.

This reinforces KA-I-024 and is adjacent evidence for KA-I-031.

---

# 26. VectorMemoryBlock: invocation scope leaked into reusable component state

Current `VectorMemoryBlock._aget()` receives a `session_id` per call.

Instead of building an immutable query filter for that invocation, it mutates `self.query_kwargs`.

If a session filter already exists, it is not replaced.

Open #22701 provides a focused reproducer:

- first call with session A stores `session_id=A` in the block's filter;
- second call with session B still queries with A;
- caller-owned `MetadataFilters` can also be mutated;
- `_aput()` removes `session_id` from caller-owned message metadata via `pop()`.

The current source inspected in KA-4 still matches the issue's described mechanism.

## 26.1 Architecture consequence

A reusable retriever/memory definition has absorbed per-request scope.

This can cause:

- cross-session retrieval;
- stale scope;
- data leakage;
- race-dependent behavior;
- caller-state mutation.

### Recurrence contribution

This independently reinforces KA-I-013.

Graphiti demonstrated mutable shared driver routing across groups. LlamaIndex demonstrates mutable shared retrieval-scope/filter state across sessions. The common invariant is:

> Knowledge-domain/scope routing must be immutable/request-local when concurrent or reused components can occur.

KA-F-002 is correspondingly broadened/reinforced from “mutable shared storage-routing state” to “mutable shared knowledge-scope/routing/filter state.”

---

# 27. Namespace and session are still not principals

LlamaIndex can use:

- vector-store namespaces;
- session IDs;
- document IDs;
- ref-document IDs;
- graph IDs;
- metadata filters.

None of those is inherently an authenticated principal identity.

The VectorMemoryBlock bug is especially instructive: the session filter is intended to isolate retrieval but is not an authorization system.

### Architectural lesson

Partition/routing metadata can support an authorization design, but cannot substitute for authenticated principal + policy evaluation.

This reinforces KA-I-003 and KA-I-014.

---

# 28. Persistent memory remains untrusted content

Vector memory stores conversation text and later retrieves it back into model context.

Open issue #21666 proposes an OWASP-style memory-poisoning guard and explicitly frames persistent user inputs as a potential future influence on agent behavior.

KA-4 treats #21666 as a **security design signal**, not as proof of a confirmed exploit in current LlamaIndex.

The architectural conclusion does not depend on the issue being an exploit report:

- persistent text remains data;
- retrieval does not make it trusted;
- prompt inclusion does not make it policy;
- execution authority must remain in a separate policy/tool layer.

This reinforces KA-I-015 and KA-I-020.

---

# 29. Ingestion settlement spans multiple stores

`IngestionPipeline` and `BaseIndex` perform sequential operations across independent stores.

Examples:

## 29.1 Ingestion pipeline

A run can:

1. determine duplicate/upsert strategy from docstore state;
2. transform nodes;
3. insert transformed nodes into a vector store;
4. update the docstore with source/input document state/hashes.

There is no single transaction spanning arbitrary remote vector store + docstore + transformation cache.

## 29.2 BaseIndex insertion

`insert_nodes()` performs:

1. docstore add;
2. index-specific insertion;
3. index-store update.

## 29.3 StorageContext persistence

`persist()` writes:

- docstore;
- index store;
- graph store;
- optional property graph store;
- every namespaced vector store;

sequentially.

No cross-store generation/snapshot manifest is required by this core code.

### Architectural lesson

“Persisted” or “inserted” is not one bit when a knowledge mutation spans several stores.

A general substrate needs:

- operation identity;
- per-plane settlement state;
- generation/snapshot identity;
- reconciliation/rebuild path;
- read-side rule for partially settled generations.

This reinforces KA-I-028, KA-F-019 and KA-I-011.

---

# 30. Async docstore writes do not automatically create an atomic record

`KVDocumentStore` represents one logical node/reference mapping in several collections:

- node data;
- node metadata/hash/ref ID;
- ref-document info.

Synchronous writes use multiple `put_all()` calls; async writes can issue multiple store operations together.

Unless the concrete KV backend supplies an atomic transaction across those collections, concurrency/failure semantics remain backend-dependent.

### Architectural lesson

An API call that updates multiple internal indexes/collections is not automatically one atomic knowledge transition.

This reinforces KA-I-012, KA-I-028 and KA-F-019.

---

# 31. Safe replacement failure window: current `update_ref_doc()`

Current `BaseIndex.update_ref_doc()` is literally:

1. delete old ref document from index/docstore;
2. insert the new document.

Open #22733 calls out the obvious failure window:

- deletion succeeds;
- new transformation/indexing fails;
- neither valid old nor valid new version remains available.

### Recurrence contribution

This independently reinforces KA-I-035 and KA-F-029 from Letta.

The generalized invariant becomes:

> Replacement/restore of active knowledge must stage and validate the replacement before destructive cutover, then reconcile derived projections.

The generalized failure becomes:

> Delete-first replacement destroys the last good state before the replacement settles.

### Non-conclusion

Applications can implement safer blue/green/versioned index replacement externally. KA-4 describes the current core primitive, not all deployments.

---

# 32. Delete from retrieval is not privacy erasure

`BaseIndex.delete_ref_doc()` defaults `delete_from_docstore=False`.

That means deleting the document from the index can intentionally leave underlying docstore material.

Separately, property graph, vector stores, caches, external resources and backups can have their own deletion semantics.

### Architectural lesson

The word “delete” must be qualified by plane and purpose:

- remove from active retrieval;
- remove current canonical assertion;
- delete derivative;
- delete raw/source resource;
- erase subject data;
- retain/redact audit history;
- expire cache;
- reconcile backups.

This provides independent LlamaIndex support for KA-I-016 and the general risk behind KA-F-026.

---

# 33. Backend delete semantics are part of the contract

The vector-store base interface allows adapters to implement different deletion primitives:

- delete by ref-document ID;
- delete nodes;
- delete by filters;
- sometimes `get_nodes()`/async variants are not implemented.

Property graph stores similarly differ in query/delete capabilities.

Therefore canonical deletion cannot be delegated to “whatever `.delete()` means” without a verified adapter contract.

This reinforces KA-I-012 and KA-I-019.

---

# 34. Node hash is useful dedup/derivation state, not semantic identity

Node hashes are used in several important mechanisms:

- duplicate/change detection;
- graph duplicate suppression;
- retrieval fusion deduplication;
- source relation snapshots.

But hash meaning depends on node type.

Examples:

- `TextNode.hash` hashes text + metadata;
- multimodal `Node.hash` uses metadata + media resource hashes;
- path/URL media hashing uses locator strings;
- graph `ChunkNode` can default to Python `hash(text)` when no ID is supplied.

### Architectural lesson

A “hash” field must state what it proves:

- content digest;
- record-state digest;
- derivation-input digest;
- cache key;
- retrieval dedup key;
- locator fingerprint.

One generic hash should not be assumed to supply every identity/integrity property.

---

# 35. Derived dedup by node hash can be correct only within a declared profile

`QueryFusionRetriever` deduplicates candidates by `node.hash`.

PropertyGraphIndex also checks existing source-node hashes to avoid repeated Llama-node upserts.

This is useful performance behavior.

However, two records can have the same text/metadata hash while still differ in:

- source provenance;
- authorization/sensitivity;
- observation time;
- epistemic state;
- derivation profile;
- applicability scope.

Whether such records should collapse is therefore a semantic choice, not a universally safe property of content similarity.

### Architectural lesson

Dedup identity must be purpose-specific and cannot erase provenance/scope distinctions needed later.

---

# 36. Schema and compatibility mechanisms are partial, not universal migration

Positive mechanisms inspected include:

- stable `class_name()` serialization identifiers intended to survive Python class renames;
- legacy docstore-field compatibility logic;
- backward-compatible metadata keys such as `document_id`, `doc_id`, `ref_doc_id` for different vector stores.

These are useful compatibility techniques.

They do not mean historical embeddings, graph extractions, parser outputs or caches have been semantically re-derived under a new implementation.

### Architectural lesson

Serialization compatibility and semantic migration are separate operations.

This reinforces KA-I-017.

---

# 37. Derived model/profile changes need explicit re-derivation policy

Embeddings and graph extractions depend on models/prompts/configuration.

Changing:

- embedding model;
- chunking algorithm;
- extraction prompt;
- LLM;
- tokenizer;
- metadata projection;
- query fusion behavior;

can change derived state without changing the raw source.

The ingestion cache captures some serialized transformation configuration, but there is no universal derivation-profile manifest spanning all these dimensions.

### Architectural lesson

Derived indexes need an explicit profile/generation identity and a policy for:

- compatible reuse;
- stale-but-readable state;
- mandatory rebuild;
- mixed-generation detection;
- migration/re-derivation.

This reinforces KA-I-011, KA-I-017 and KA-I-018.

---

# 38. Recovery needs cross-plane generation identity

`StorageContext.persist()` writes independent stores to a directory/remote filesystem path.

If a process fails mid-persist, or files from different generations are combined, the inspected code does not provide one required manifest stating:

- snapshot generation ID;
- exact component versions;
- all expected plane revisions/digests;
- completeness/settlement;
- atomic cutover pointer.

### Architectural lesson

Multi-file/multi-backend restore should not infer consistency merely because all files can be opened.

A future substrate should make coherent-generation identity explicit.

### Non-conclusion

External storage layers can offer snapshots/transactions. KA-4 describes what the LlamaIndex core `StorageContext` itself guarantees in the inspected code.

---

# 39. Unknown, false, not-extracted and not-retrieved are different states

LlamaIndex makes this distinction necessary even though the generic node model does not encode it.

A relationship/fact can be absent from results because:

- source did not state it;
- parser failed;
- extractor returned an empty set;
- extraction was capped;
- transformation cache contained older output;
- graph derivative was not reconciled;
- metadata filter excluded it;
- retriever candidate generation missed it;
- fusion top-k removed it;
- context budget/postprocessor removed it;
- source/index was deleted.

None of those means the proposition is known false.

This independently reinforces KA-I-021.

---

# 40. Scope of truth is mostly application metadata

LlamaIndex supports arbitrary metadata and backend filtering, which is useful for application scope such as:

- tenant;
- project;
- date;
- file;
- category;
- session.

But the core node model does not define a normalized applicability envelope for:

- environment;
- machine/device;
- software version;
- person/account;
- physical location;
- role;
- task;
- time interval;
- policy purpose.

### Architectural lesson

Arbitrary metadata is a flexible escape hatch, not a controlled scope-of-truth model.

This reinforces KA-I-022.

---

# 41. Actionability and authority remain outside ordinary nodes

A retrieved node can contain text that looks like:

- an instruction;
- a policy;
- a command;
- a configuration value;
- a user preference;
- an approval statement.

Nothing in ordinary `BaseNode` identity/score turns that text into executable authority.

A safe ACL/Vera architecture must separately decide whether retrieved material is:

- informational;
- planning input;
- automation input;
- policy evidence;
- verification-required;
- explicitly non-authoritative.

This reinforces the campaign invariant:

**Knowledge != Authority != Execution.**

---

# 42. All 26 campaign evidence questions

| # | Evidence question | KA-4 result |
|---:|---|---|
| 1 | Stable identity | **Strong evidence / partial mechanism.** Documents, nodes, ref-doc IDs, graph entities and citation projections have IDs, but default derived IDs are random and entity-name IDs are not real-world identity. #22133/#22537 show why layer identities must differ. |
| 2 | Identity vs namespace | **Strong gap evidence.** Session IDs/vector namespaces/ref-doc IDs route data; none is authenticated principal identity. #22701 shows session scope can itself become stale mutable state. |
| 3 | Provenance | **Strong partial mechanism.** SOURCE relationships, offsets, ref-doc mappings and `triplet_source_id` are useful; full transformation/model/profile/verification provenance is not required end-to-end. |
| 4 | Epistemic state | **Gap.** Core nodes/relations do not require explicit/inferred/verified/disputed/confidence state; LLM graph extraction makes the distinction important. |
| 5 | Temporal truth | **Gap.** Operational hashes/metadata support freshness but no generic world-valid + transaction-time truth model. |
| 6 | Conflict/supersession | **Gap/risk.** Index updates replace/delete old retrieval state; generic contradiction/supersession lineage is not modeled. |
| 7 | Relationships | **Strong partial mechanism.** Structural SOURCE/PARENT/CHILD/PREV/NEXT plus typed property graph relations exist; semantic graph is derivative and lacks governed replacement/cardinality/epistemic semantics. |
| 8 | Permissions/sensitivity | **Outer-layer requirement.** Metadata filters/namespaces are routing/eligibility tools, not principal/purpose authorization. Backend filter behavior varies. |
| 9 | Actionability | **Gap.** Ordinary nodes do not carry a generic actionability/verification-required class. |
| 10 | Knowledge vs authority | **Supports separation.** RAG/memory content informs models but does not inherently carry policy/credential/tool authority. |
| 11 | Resources/artifacts | **Strong partial mechanism.** MediaResource supports bytes/text/path/URL/mimetype/embeddings; locator hash is not universal content/version checksum. |
| 12 | Canonical vs derived | **Strong evidence.** Source representations, docstore, vector stores, graph, index structs, cache, retrieval results and citation projections are distinguishable planes. |
| 13 | Structured retrieval | **Supported but backend-qualified.** IDs/hashes/ref-doc mappings and metadata filters provide deterministic access; filter semantics vary. |
| 14 | Relationship retrieval | **Supported.** Structural node relationships and property graph traversal exist; derived graph provenance/currentness must be respected. |
| 15 | Full-text retrieval | **Supported in profiles.** Sparse/text/BM25-style retrieval exists through retrievers/backends; not universal to every store. |
| 16 | Semantic retrieval | **Strong support.** Embeddings/vector retrieval are central; score remains relevance, not truth. |
| 17 | Composite retrieval | **Strong support.** QueryFusionRetriever exposes multi-retriever candidate generation/fusion; backend hybrid modes add additional profiles. |
| 18 | Context construction | **Strong evidence.** Metadata modes, exclusions, postprocessors, citation chunks and synthesizers transform retrieval into model context; #22248 demonstrates stale projection. |
| 19 | Memory poisoning/injection | **Outer trust boundary.** Persistent memory is model-visible untrusted content; #21666 is current design signal. PGVector filter-key interpolation is a separate backend input-to-query risk. |
| 20 | Concurrency | **Concrete risk.** #22701 mutates reusable filter state; multi-store/docstore operations lack one universal transaction/fence. Backend atomicity varies. |
| 21 | Derived-state integrity | **Strong evidence.** #22133, property-graph deletion, cache profile gaps and multi-store settlement all show derivatives can diverge. |
| 22 | Deletion/retention | **Strong evidence/gap.** Index deletion may retain docstore by default; property graph/vector/cache/backups differ; delete != erasure. |
| 23 | Schema/version evolution | **Partial mechanism/gap.** Serialization compatibility exists, but semantic re-derivation/version manifest is not universal. |
| 24 | Recovery semantics | **Gap.** StorageContext persists planes independently; no required cross-plane snapshot-generation settlement contract. This is knowledge recovery, not exactly-once effect proof. |
| 25 | Unknown/negative | **Strong gap evidence.** Extraction/retrieval absence can have many causes and cannot be interpreted as false. |
| 26 | Scope of truth | **Partial mechanism/gap.** Arbitrary metadata can represent application scope but does not supply governed normalized applicability semantics. |

---

# 43. Highest-value architecture lessons for later synthesis

These are evidence outputs, not final design decisions.

## 43.1 Distinguish at least five identity layers

Later synthesis should be able to represent distinctly:

1. external/logical resource;
2. observed source/version;
3. derived record/chunk/assertion;
4. semantic entity/relationship identity;
5. retrieval/presentation projection.

LlamaIndex #22133 and #22537 are concrete evidence that collapsing these layers causes silent data loss or false source addressing.

## 43.2 Resource content identity must survive relocation and detect in-place mutation

A future resource model should not choose between path identity and content digest; it needs both, with version/observation semantics.

## 43.3 Derived state requires a generation/profile contract

The contract should cover:

- transformation implementation;
- model/provider;
- prompt/schema;
- source revision;
- output schema;
- index/backend profile;
- settlement/completeness;
- rebuild eligibility.

## 43.4 Filter contracts are security/correctness contracts

If a filter determines:

- tenant isolation;
- sensitivity;
- current-only retrieval;
- policy eligibility;
- deletion target;

then unsupported/changed/backend-specific semantics must fail closed rather than degrade silently.

## 43.5 Graph retrieval and graph truth are separate

A property graph can be an excellent derivative retrieval structure without becoming the canonical truth model.

## 43.6 Deletion/replacement must operate over provenance closures

Source deletion should reconcile all derivatives that depend on that source, while safe replacement should not destroy the old current version until the new version settles.

---

# 44. Proposed future acceptance/regression fixtures from KA-4

These are research outputs for later use; no tests are implemented now.

1. **One source, many derivatives** — one document produces N chunks; all N survive ingestion and remain traceable to one source ID.
2. **Stable source / fresh derived IDs** — re-derivation cannot accidentally treat source ID as derivative uniqueness.
3. **Citation projection identity** — citation chunks have unique IDs and valid locators while retaining parent/source lineage.
4. **Mutable file at same path** — source content changes without path change; freshness logic must detect the content/version change.
5. **Same content at new path** — relocation changes locator without necessarily creating a new logical resource/content version.
6. **Graph extraction provenance** — every extracted relation traces to source evidence + derivation profile.
7. **Graph extraction failure** — parser failure produces `incomplete/failed`, not a semantic conclusion of `false/no relationship`.
8. **Graph source deletion** — deleting a source chunk removes/reconciles every derivative whose provenance depends on it.
9. **Shared graph endpoint deletion** — deleting one relation must not remove an entity still referenced by another current relation unless governed semantics say so.
10. **Safe document replacement** — new indexing failure leaves the prior settled version active.
11. **Partial vector/docstore write** — system reports unsettled/reconciliation-needed rather than returning one undifferentiated success.
12. **Interrupted StorageContext persist** — restore detects mixed/incomplete generation rather than loading an incoherent snapshot silently.
13. **Transformation implementation upgrade** — cached old output is invalidated or explicitly marked as old generation even if visible config is unchanged.
14. **Backend filter semantic parity** — required AND/OR/NOT/operator behavior is validated for the realized backend.
15. **Unsupported hard filter** — backend inability to express a hard eligibility predicate fails closed.
16. **Untrusted filter key/value** — crafted metadata key/value cannot alter backend query syntax.
17. **Cross-session vector memory** — reusing one memory block for session A/B cannot persist or leak invocation-specific filters.
18. **Caller immutability** — retrieval/storage does not mutate caller-owned filter/message objects unless contract explicitly says so.
19. **Composite retrieval contract** — candidate introducers, fusion mode, dedup key and cutoff order are observable and reproducible.
20. **Score semantics** — retrieval/fusion score cannot populate epistemic confidence automatically.
21. **Model-visible freshness** — canonical/host state update invalidates/rebuilds the context projection before the next reasoning turn.
22. **Delete versus erase** — index deletion, docstore deletion, derivative cleanup, audit/history and privacy erasure report separately.
23. **Entity name collision** — two real entities with the same name do not silently become one canonical entity.
24. **Entity alias** — two names for one real entity can remain unresolved without forced merge.
25. **Current vs history** — re-index replacement cannot be the only record of a fact whose historical truth matters.
26. **Derived graph not authority** — a model-extracted relationship cannot directly authorize an effect.

---

# 45. Candidate invariant contribution summary

KA-4 independently reinforces or materially extends these existing families:

- **KA-I-001** — source evidence separate from derived semantic knowledge;
- **KA-I-002** — internal semantic entity identity separate from external/source identity;
- **KA-I-003** — routing/session/namespace ID is not authenticated principal;
- **KA-I-006** — semantic supersession requires governed provenance-bearing transition beyond index replacement;
- **KA-I-010** — retrieval/fusion score is not truth/confidence/authority;
- **KA-I-011** — derived state needs generation/profile identity/rebuildability;
- **KA-I-012** — realized backend semantics must be qualified;
- **KA-I-013** — request scope/routing must be immutable/request-local;
- **KA-I-014** — hard eligibility/principal constraints before model exposure;
- **KA-I-015** — persistent/retrieved text remains untrusted content;
- **KA-I-016** — delete/forget is multi-plane reconciliation;
- **KA-I-017** — serialization compatibility is not semantic migration;
- **KA-I-018** — behavior identity includes exact implementation/model/backend/profile;
- **KA-I-019** — policy/provenance metadata must survive every backend/projection path;
- **KA-I-020** — retrieval never grants execution authority;
- **KA-I-021** — unknown/false/not-established/conflict states differ;
- **KA-I-022** — truth applicability requires governed structured scope;
- **KA-I-023** — transformations need provenance;
- **KA-I-024** — context construction is a separate layer;
- **KA-I-025** — epistemic basis/verification separate from storage/retrieval status;
- **KA-I-026** — candidate-introducer/reranker/hard-gate order is part of composite retrieval;
- **KA-I-027** — derived views need coverage/generation/eligibility semantics;
- **KA-I-028** — mutation settlement drives derived updates and success semantics;
- **KA-I-030** — derived semantic/association graphs are not canonical relationship truth;
- **KA-I-035** — replacement must stage/validate before destructive cutover.

KA-4 makes the following previously single-task candidates cross-project reinforced:

- **KA-I-002** — Graphiti + LlamaIndex;
- **KA-I-013** — Graphiti + LlamaIndex;
- **KA-I-026** — Mem0 + LlamaIndex;
- **KA-I-030** — Mem0 + LlamaIndex;
- **KA-I-035** — Letta Code + LlamaIndex.

KA-4 introduces two materially new candidate invariants:

- **KA-I-036** — source/resource identity, derived-record identity and presentation-projection identity are distinct; lineage must not be implemented by identity reuse.
- **KA-I-037** — logical resource identity, locator/address and observed content/version digest are distinct and must be represented separately.

No invariant becomes a final architecture rule during KA-4.

---

# 46. Failure-pattern contribution summary

KA-4 independently reinforces these existing failures:

- **KA-F-002** — broaden/reinforce mutable shared routing/scope/filter state via #22701;
- **KA-F-012** — source deletion can leave derived property-graph state because deletion does not necessarily follow `triplet_source_id`;
- **KA-F-013** — package/project version is too coarse for backend/model/transformation behavior;
- **KA-F-015** — high-level metadata/filter capability is not a governance guarantee;
- **KA-F-016** — relevance/fusion score confused with truth/confidence;
- **KA-F-019** — intermediate store persistence mistaken for multi-plane settlement;
- **KA-F-020** — source provenance without complete transformation provenance;
- **KA-F-026** — index/memory delete confused with data erasure while another data plane remains;
- **KA-F-027** — derivative absence treated as exhaustive source truth;
- **KA-F-029** — broaden/reinforce destructive delete-first replacement via `update_ref_doc()`/#22733.

KA-4 introduces four materially distinct observed/current-source failure classes:

- **KA-F-033** — source/document identity reused as derivative uniqueness key collapses one-to-many derived records (#22133, fixed current source);
- **KA-F-034** — a re-chunked/presentation derivative copies parent identity or stale locators, causing dedup/source-addressing errors (#22537, fixed current source);
- **KA-F-035** — a mutable external resource locator fingerprint is treated as if it were a content/version digest, so same-locator content mutation can be invisible in locator-only hashing;
- **KA-F-036** — untrusted metadata/resource identifiers are interpolated into backend query syntax rather than safely bound/qualified, changing retrieval/deletion predicate semantics (#22475/current PGVector source).

Recent #22543 is recorded in the report but **not** as current evidence for KA-F-036 because current Managed LanceDB source has already added escaping.

---

# 47. Explicit non-conclusions

KA-4 does **not** establish that:

1. LlamaIndex is unsafe or unsuitable for RAG/agent applications.
2. Every vector-store adapter has the same filter/delete behavior.
3. Every application using LlamaIndex loses source evidence.
4. LlamaIndex intends `Document`/`Node` to be a general epistemic truth database.
5. Random derived node UUIDs are inherently wrong.
6. Name-based `EntityNode` IDs cannot be replaced/customized by an application.
7. Every graph extracted by LlamaIndex is hallucinated or unreliable.
8. All property-graph backends exhibit the same simple-store endpoint deletion behavior.
9. Every path/URL-backed resource misses content changes; many readers include text/data that changes the node hash.
10. #21666 proves an active memory-poisoning exploit in current LlamaIndex.
11. #22543 remains unfixed in current source; it does not.
12. #22475 is reachable through every ordinary in-tree caller; the issue itself notes current callers use literal keys, while the current source still lacks a generic trust boundary for externally supplied keys.
13. `StorageContext.persist()` guarantees an incoherent restore; it simply does not itself provide a required cross-plane atomic generation contract.
14. callback events are useless; they are valuable observability but not automatically durable canonical provenance.
15. LlamaIndex retrieval score should never be used for relevance; the warning is only against treating relevance as epistemic confidence/authority.
16. LlamaIndex should implement ACL/Vera's policy engine, credential broker, effect ledger or canonical truth model.
17. a graph database should or should not be selected for ACL/Vera.
18. the final ACL/Vera knowledge schema should mirror LlamaIndex node classes.

---

# 48. Primary sources inspected

Current upstream/source profile:

- `https://github.com/run-llama/llama_index/tree/d2ac544a27c73d2a68e9c57efec4b2ac0ef99892`
- `llama-index-core/pyproject.toml`

Core identity/resource/schema:

- `llama-index-core/llama_index/core/schema.py`
- `llama-index-core/llama_index/core/node_parser/interface.py`
- `llama-index-core/llama_index/core/node_parser/node_utils.py`

Ingestion/derivation/cache:

- `llama-index-core/llama_index/core/ingestion/pipeline.py`
- `llama-index-core/llama_index/core/ingestion/cache.py`
- `docs/src/content/docs/framework/module_guides/loading/ingestion_pipeline/index.md`

Storage/index planes:

- `llama-index-core/llama_index/core/indices/base.py`
- `llama-index-core/llama_index/core/storage/storage_context.py`
- `llama-index-core/llama_index/core/storage/docstore/types.py`
- `llama-index-core/llama_index/core/storage/docstore/keyval_docstore.py`

Vector/filter/retrieval:

- `llama-index-core/llama_index/core/vector_stores/types.py`
- `llama-index-core/llama_index/core/vector_stores/utils.py`
- `llama-index-core/llama_index/core/vector_stores/simple.py`
- `llama-index-core/llama_index/core/retrievers/fusion_retriever.py`
- `llama-index-integrations/vector_stores/llama-index-vector-stores-postgres/llama_index/vector_stores/postgres/base.py`

Context/citations/memory:

- `llama-index-core/llama_index/core/query_engine/citation_query_engine.py`
- `llama-index-core/llama_index/core/memory/memory_blocks/vector.py`

Property graph:

- `llama-index-core/llama_index/core/indices/property_graph/base.py`
- `llama-index-core/llama_index/core/indices/property_graph/transformations/simple_llm.py`
- `llama-index-core/llama_index/core/graph_stores/types.py`
- `llama-index-core/llama_index/core/graph_stores/simple_labelled.py`

Current/recent issue and PR evidence:

- #22133 — ingestion upsert node-loss fix: `https://github.com/run-llama/llama_index/pull/22133`
- #22537 — citation chunk ID/offset fix: `https://github.com/run-llama/llama_index/pull/22537`
- #22701 — VectorMemoryBlock session-filter mutation: `https://github.com/run-llama/llama_index/issues/22701`
- #22733 — safe replacement semantics request: `https://github.com/run-llama/llama_index/issues/22733`
- #22248 — stale agent state prompt: `https://github.com/run-llama/llama_index/issues/22248`
- #21666 — memory-poisoning guard request: `https://github.com/run-llama/llama_index/issues/21666`
- #22475 — PGVector metadata-key SQL interpolation: `https://github.com/run-llama/llama_index/issues/22475`
- #22543 — Managed LanceDB delete-ID interpolation report, already escaped in pinned current source: `https://github.com/run-llama/llama_index/issues/22543`

Historical ACL discovery report re-read:

- `docs/research/projects/llamaindex.md`

---

# 49. Stop boundary

KA-4 LlamaIndex knowledge-architecture research is complete.

The evidence has been recorded for later recurrence/synthesis work.

KA-4 does **not** authorize the next queue item.

**Do not begin KA-5 Mastra until the user explicitly authorizes it.**
