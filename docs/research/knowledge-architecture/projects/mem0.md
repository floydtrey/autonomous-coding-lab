# Mem0 — Knowledge-Architecture Revisit (KA-2)

**Research date:** 2026-09-07  
**Repository:** `mem0ai/mem0`  
**Inspected upstream revision:** `dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3`  
**Inspected Python package version:** `2.0.20`  
**Campaign task:** KA-2 — Mem0 Knowledge-Architecture Revisit  
**Research status:** complete for KA-2; no architecture, database, storage engine, framework, provider, or implementation decision made.

## Executive assessment

Mem0 v3 is useful reference material for a **derived semantic-memory plane**: it extracts compact memories from conversations, scopes them to user/agent/run identifiers, retrieves them with semantic/BM25/entity signals, records mutation history, and—on the managed Platform—adds non-destructive lifecycle states and background consolidation.

The most important current-generation change is architectural rather than cosmetic. The inspected Python OSS write path is explicitly a **V3 phased batch pipeline** whose inference path is ADD-only. Existing memories are retrieved as context, but the current OSS extraction path no longer asks the model to perform ADD/UPDATE/DELETE/NONE maintenance in one decision. New semantic memories accumulate; exact-text hashes suppress some duplicates; explicit `update()` and `delete()` remain separate APIs. Managed Mem0 then adds a separate Dream lifecycle layer for supersession, merging and synthesis.

That separation is valuable evidence for ACL/Vera: **fast capture, current-state resolution, and derived synthesis do not have to be the same operation or the same plane**. But Mem0 is not a complete general-purpose knowledge substrate. OSS primarily preserves derived semantic memories rather than durable raw evidence; its history table is mutation history rather than extraction provenance; graph/entity structures are retrieval derivatives rather than typed canonical relationships; epistemic state is thin; scope identifiers are not authorization principals; and write/delete/retrieval correctness still depends materially on backend and concurrency behavior.

Several current failures are especially relevant to a general substrate:

- concurrent ADD-only dedup uses a stale pre-write snapshot and can create duplicate memories;
- derived entity links use read-modify-write behavior with independent race/cleanup failure modes;
- OpenSearch can silently drop advanced metadata filters while accepting the high-level filter request;
- a batch-write fallback can log failed individual inserts yet still write history, build entity links and return `ADD` results for the full intended record set;
- `delete()`/`delete_all()` remove vector memories but intentionally retain old plaintext in history, while entity cleanup is best-effort;
- a short-term message buffer is keyed by stable user/agent/run scope, so reusing that scope across conversational episodes can leak stale context into a new extraction.

These are not arguments against Mem0. They are strong evidence that the eventual ACL/Vera architecture must distinguish **canonical evidence, derived semantic memory, current-state/lifecycle interpretation, retrieval indexes, scope, authorization, context caches, audit history and effect settlement**.

## 1. Current-generation boundary: “Mem0” is not one semantic profile

### Observed upstream behavior

Current `main` is pinned here to `dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3`. The repository declares Python package version `2.0.20`.

The current migration documentation describes a major v2→v3 redesign:

- extraction changed to one ADD-only pass;
- retrieval changed to semantic + BM25 + entity-aware scoring;
- external graph-store integration was removed from OSS;
- native Graph Memory is now a managed Platform capability;
- several defaults and method contracts changed;
- Platform and OSS now intentionally expose different temporal, lifecycle, graph, scoping and management capabilities.

The Platform-vs-OSS documentation makes the split explicit. OSS uses caller-selected vector stores, LLMs and embedders and supports `user_id`, `agent_id`, `run_id`. Platform additionally exposes `app_id`, org/project identity, Graph Memory, Temporal Reasoning, Memory Decay, Dream, project event feeds and other managed operations.

Python and TypeScript also retain some representation differences. The migration guide specifically warns that their lemmatized-text payload keys differ, so sharing a vector collection across SDK languages can break BM25 behavior.

### Architectural lesson

A deployment cannot be identified adequately as “Mem0 v3.” For reproducible knowledge behavior, a profile needs at least:

- exact source/package revision;
- OSS versus Platform;
- language SDK/runtime;
- vector-store provider/version;
- LLM and embedding provider/model/runtime;
- filter/operator support profile;
- extraction prompt/schema revision;
- retrieval/reranking/decay settings;
- lifecycle/consolidation features enabled;
- migration history.

This independently reinforces the campaign rule that realized capability identity is more specific than a package/project name.

### Confidence

**High** for inspected OSS source and first-party migration/product documentation. Platform internals are proprietary; Platform behavior below is treated as documented product behavior, not independently source-verified implementation.

## 2. OSS v3 stores derived semantic memory, not a durable raw-evidence corpus

### Observed upstream behavior

The current Python OSS write path starts by building a short context window and extracting semantic memories with an LLM. The resulting vector-memory records contain compact memory text plus metadata such as scope IDs, timestamps, hash, speaker attribution and optional caller metadata.

The local SQLite manager persists two relevant tables:

- `history`: memory mutation history (`old_memory`, `new_memory`, event, timestamps, actor/role);
- `messages`: recent source messages by a derived `session_scope`.

The message table intentionally evicts older rows beyond the most recent ten messages for that scope.

No inspected OSS record provides a general first-class source/evidence envelope containing, for example:

- stable source resource ID;
- original message/document ID;
- byte/line/chunk locator;
- source checksum/version;
- extraction-run ID;
- prompt/model profile;
- confidence;
- source trust class;
- evidence fragment list.

`history` tells how a derived memory changed. It does not identify the complete raw evidence from which the memory was inferred.

### Architectural lesson

Mem0 is strong reference material for a **semantic-memory derivative**, not sufficient evidence that a semantic-memory database should be the canonical evidence store.

ACL/Vera should preserve raw/source evidence separately enough that a semantic memory can later answer:

- What exact source produced this?
- What was the original wording?
- Was this one statement or a derived combination?
- Which extraction/profile created it?
- Can we re-derive it under a new schema/model?
- Can we prove the source was deleted or retained?

The last-10-message buffer is context-cache state, not durable provenance.

### Non-conclusion

This does not mean an application cannot store raw evidence elsewhere and reference Mem0 memories from it. It means the inspected OSS memory model does not itself establish that source-addressable evidence layer.

## 3. Attribution is useful, but it is not epistemic state

### Observed upstream behavior

The v3 additive extraction prompt requires `attributed_to`, distinguishing memories derived from user versus assistant content. It explicitly scans both sides of a conversation. The prompt can preserve:

- user preferences/facts/plans;
- assistant recommendations;
- confirmations;
- researched information;
- agent configuration/instructions in agent-scoped mode.

This is more informative than a memory string with no speaker context.

However, an inspected memory record does not generally distinguish:

- explicit user assertion;
- assistant inference;
- authenticated configuration;
- sensor observation;
- verified external record;
- third-party claim;
- research finding;
- model-derived summary;
- disputed claim;
- known false;
- unknown/not-established;
- confidence or verification state.

An assistant statement and a user statement can both become the same broad MemoryItem class with attribution metadata.

### Architectural lesson

**Who said it is not the same as why it should be believed or how it may be used.**

The general knowledge substrate should separate:

- attribution/source speaker;
- epistemic basis;
- confidence/verification;
- dispute/lifecycle state;
- actionability/authority-use class.

A recommendation remembered from an assistant does not become verified fact. A text saying “Agent is configured to X” does not become authoritative configuration merely because the memory extractor saved it.

### Candidate invariant contribution

This task supports a new cross-project invariant: epistemic basis/verification is independent of speaker attribution, storage status and retrieval score.

## 4. Scope IDs are storage/query dimensions, not authenticated principal identity

### Observed upstream behavior

Current OSS `_build_filters_and_metadata()` requires at least one of:

- `user_id`;
- `agent_id`;
- `run_id`.

Those IDs are stamped into memory metadata and reused as query filters.

Current Platform documentation extends this model with `app_id` and explicitly describes all four as **entity-scoping identifiers**. It also explicitly distinguishes them from graph entities extracted from memory text.

Mem0 has fixed important historical bugs in this boundary:

- #6277: `update()` once allowed caller metadata to overwrite `user_id`/`agent_id`/`run_id`, moving a memory across scopes;
- #6655: `add()` once allowed freeform metadata to inject unset identity-scope fields.

Current source strips identity keys from freeform metadata during creation and protects them during updates.

The self-hosted server has also been hardened. PR #5360 added admin checks to destructive/global operations. But the reference server is still a single-admin topology; Mem0 `user_id` remains an application memory scope, not the authenticated API principal itself.

### Architectural lesson

This is strong independent evidence for three separate concepts:

1. **authenticated principal** — who is making the request;
2. **knowledge domain/scope** — which user/agent/run/app records are eligible;
3. **semantic entity** — the person/device/project/concept the knowledge is about.

Scope identity should be host-stamped and protected from ordinary metadata mutation. Possession of a scope string must not confer authority to read/write that scope.

### Non-conclusion

The current single-admin self-hosted server should not be described as a demonstrated multi-user tenant-escape vulnerability. The lesson is architectural separation, not a claim about an unsupported topology.

## 5. Stable knowledge scope and conversational episode identity are different

### Observed upstream behavior

Current `_build_session_scope()` constructs the context-buffer key only from the selected `user_id`, `agent_id`, and `run_id`.

`SQLiteManager.save_messages()` stores and retains the last ten messages for that scope.

Open issue #7195 reports a concrete consequence: when a later conversational session reused the same scope, tail messages from the earlier session remained in `Last k Messages` and entered the new extraction prompt. The report describes intimate/personal content from one session appearing in a later technical-session extraction context.

### Architectural lesson

A stable knowledge namespace is not necessarily one coherent observation episode, conversation, workflow, or source transaction.

ACL/Vera should separately identify:

- persistent subject/domain scope;
- conversation/session/episode;
- source event/observation;
- retrieval/context-building run.

Context caches should be keyed to the correct transient boundary rather than merely the broader knowledge namespace.

This becomes especially important for Vera, where one person may produce many unrelated conversations, sensor events, locations and tasks inside the same long-lived user scope.

## 6. Current OSS extraction is ADD-only; current truth is a separate concern

### Observed upstream behavior

Current Python OSS `_add_to_vector_store()` is explicitly labeled `V3 PHASED BATCH PIPELINE`.

Its inferred write flow is:

1. load recent message context;
2. retrieve up to ten existing semantic memories under the selected scope;
3. call one LLM extraction prompt;
4. embed extracted memory texts;
5. suppress exact-text hash duplicates against the retrieved snapshot and current batch;
6. persist new records;
7. maintain derived entity links;
8. save recent messages and return `ADD` results.

The current additive extraction prompt states that its sole operation is ADD. It prefers preserving historical changes as new memories rather than overwriting older memories in this extraction phase.

Explicit `update()` and `delete()` APIs still exist, but inference-time maintenance is not the old ADD/UPDATE/DELETE/NONE model.

### Architectural lesson

This is a useful design separation:

- **capture** new semantic observations quickly;
- **resolve** current truth/lifecycle separately;
- **synthesize** higher-order patterns separately.

For ACL/Vera, ingestion should not be forced to decide every contradiction, replacement, merge and current-state interpretation synchronously.

However, append-only capture alone does not answer “what is true now?” That requires a separate lifecycle/current-state model.

## 7. Dream is strong evidence for non-destructive lifecycle state, with important coverage boundaries

### Documented Platform behavior

The current Dream documentation defines three operations:

- **Supersede** — mark an older contradicted memory superseded and link it to the newer replacement;
- **Merge** — retain a duplicate/older representation but mark/link it as merged into a canonical memory;
- **Synthesis** — create higher-order pattern memories alongside source memories and link patterns back to their evidence.

The documentation states these are non-destructive.

It also defines explicit read intents:

- default: active + superseded; merged hidden;
- `latest_only=true`: active only;
- `include_merged=true`: active + superseded + merged.

Synthesis has explicit non-universal coverage:

- forward-only from the time it is enabled;
- user-only scope eligibility;
- minimum-memory threshold;
- scheduled rather than real-time execution;
- plan-dependent cadence.

### Architectural lesson

Two lessons recur strongly:

**First:** current-state and history are different retrieval intents. A lifecycle label is better than deleting or overwriting prior information.

**Second:** derived summaries/patterns must carry a **coverage contract**. A derived aggregate can be incomplete because of:

- enablement date;
- eligible scopes;
- source selection;
- schedule/cadence;
- processing failures;
- model/version.

Therefore, absence from a synthesis/summary cannot be interpreted as absence from canonical evidence.

### Non-conclusion

“Active” in a product lifecycle is not proof of epistemic truth. The proprietary contradiction/merge implementation was not inspected, so this report does not assume Dream’s lifecycle decisions are infallible.

## 8. Temporal ranking, record time, event time and expiration are different semantics

### Observed/documented behavior

OSS stores `created_at`/`updated_at` on memories and supports `expiration_date`. Expiration controls visibility unless `show_expired=True`.

OSS explicitly rejects Platform-only:

- `timestamp`;
- `reference_date`.

Platform Temporal Reasoning documents:

- `timestamp` for preserving original event/conversation time on import;
- temporal extraction/boosting for expressions such as “last week” or “as of …”;
- `reference_date` for evaluating a query relative to a chosen simulated current time.

### Architectural lesson

These are at least three different clocks/semantics:

1. **record/transaction time** — when the knowledge system stored/updated a record;
2. **world/event validity or observation time** — when the described fact/event applied;
3. **retention/expiration time** — when a record should cease appearing under a retention/display policy.

They must not be collapsed into one `created_at`.

Mem0 Platform’s temporal ranking is useful evidence for time-aware retrieval, but it is not itself a full bitemporal truth model.

## 9. Graph Memory is a derived association/retrieval graph, not a typed canonical relationship model

### Documented Platform behavior

Current Graph Memory documentation explicitly distinguishes:

- graph entities extracted from text;
- memory nodes;
- entity↔memory connections.

Shared entities connect memories and contribute a ranking boost.

The documentation also explicitly says Graph Memory does **not** assign typed labeled entity relationships such as `MANAGES`. Connections arise through co-occurrence/entity mention.

Current OSS v3 removed the former external graph-store integration. OSS still extracts entities into a separate vector/entity store and uses them as a retrieval boost, but does not expose a queryable relationship graph.

### Architectural lesson

“Graph memory” and “canonical knowledge relationships” are different concepts.

A co-occurrence/entity-memory graph is useful derived retrieval state. It does not replace typed, temporally scoped, provenance-bearing relationships such as:

- owns;
- located-in;
- member-of;
- depends-on;
- authorized-for;
- supersedes;
- derived-from.

This is additional evidence against selecting a graph database merely because graph-shaped retrieval is useful.

## 10. OSS entity identity is heuristic derived state, not durable external identity

### Observed upstream behavior

The OSS entity store:

- extracts named entities from memory text;
- normalizes exact entity text;
- otherwise searches semantically;
- accepts a semantic entity match around a 0.95 score in the inspected path;
- maintains `linked_memory_ids` on the derived entity record.

Entity matching is therefore useful for retrieval but should not be interpreted as identity proof for a real-world person/device/account.

Entity IDs in this store are also distinct from `user_id`/`agent_id`/`run_id`.

### Architectural lesson

ACL/Vera should keep stable real-world identity resolution separate from retrieval-oriented entity clustering.

A face observation, email, device serial, GitHub account and friendly name may all be evidence about one entity without any single embedding/text match becoming the authoritative merge decision.

## 11. Prompt-produced memory links are not demonstrated as durable OSS provenance

### Observed upstream behavior

The additive extraction prompt tells the model to return `linked_memory_ids` when a new memory relates to an existing memory.

In the inspected Python OSS persistence path, extracted records are subsequently used to persist text and `attributed_to`; the report did not find an end-to-end path that stores those prompt-produced memory-to-memory `linked_memory_ids` into the vector memory payload.

The same field name is heavily used elsewhere for a different derived purpose: entity records contain lists of memory IDs that mention/match that entity.

### Architectural lesson

A field appearing in a prompt schema is not provenance until the system demonstrates:

- validation;
- persistence;
- read projection;
- migration;
- deletion/reconciliation.

If semantic lineage matters, it should be modeled and verified end-to-end rather than assumed from model output.

### Confidence

**Moderate-high** for the inspected Python path. This is explicitly not a claim that managed Platform fails to retain lifecycle/source links; Dream documentation says it does retain such links.

## 12. “Hybrid retrieval” needs a candidate-generation contract, not merely a list of signals

### Observed upstream behavior

Current `_search_vector_store()` computes three signals:

- semantic vector similarity;
- BM25 keyword score;
- entity boost.

But candidate construction is asymmetric:

1. vector search creates the candidate pool;
2. keyword results are converted to scores by memory ID;
3. entity matches produce boosts by memory ID;
4. only semantic candidates are passed to `score_and_rank()`.

`score_and_rank()` applies the semantic threshold **before** adding BM25/entity scores.

Therefore a memory that is an excellent lexical/entity match but absent from the semantic candidate pool cannot be introduced by those other retrievers in this path.

### Architectural lesson

A composite-retrieval specification should define:

- which retriever can introduce candidates;
- which retrievers only rerank;
- hard filters before/after retrieval;
- union/intersection behavior;
- thresholds and their stage;
- fallback/degraded modes;
- score meaning.

“Uses vector + BM25 + graph/entity” is not precise enough to guarantee recall or deterministic behavior.

## 13. Backend filter semantics are part of the security/correctness contract

### Current failure evidence

Open issue #7214 documents a current OpenSearch adapter mismatch.

The high-level OSS filter processor accepts operators such as:

- `gte`, `lte`, etc.;
- `in`, `nin`;
- `contains`, `icontains`;
- logical OR/NOT.

The inspected OpenSearch `_build_filter_clauses()` currently ignores non-scalar values on non-identity metadata keys and logs only at debug level.

Thus a request such as:

`{"user_id": "alice", "priority": {"gte": 3}}`

can retain the `user_id` term while silently dropping the priority condition.

### Architectural lesson

A hard eligibility condition is safe only if the concrete backend proves it enforced the same semantics.

This matters for future filters such as:

- sensitivity ≤ caller clearance;
- purpose = permitted purpose;
- valid_at/current state;
- project/environment;
- retention state;
- verification status.

Protected retrieval should **fail closed** when a backend cannot express a required hard predicate. Silent weakening is not acceptable.

### Non-conclusion

The cited OpenSearch issue does not show that the basic `user_id` identity term is dropped. The failure is the silent loss of advanced non-scalar conditions.

## 14. Retrieval score is relevance, not truth—and may combine very different signals

### Observed/documented behavior

OSS’s combined score can include:

- vector similarity;
- normalized BM25;
- entity association boost.

Platform Memory Decay can additionally scale retrieval rank based on access recency/frequency.

Decay is explicitly documented as a soft ranking bias, not a truth mechanism. It can even produce a public final score below the request threshold because the threshold is applied earlier in the pipeline.

### Architectural lesson

A single score may encode:

- topical similarity;
- lexical overlap;
- graph/entity proximity;
- recency;
- usage frequency;
- reranker preference.

None of these is epistemic confidence.

ACL/Vera should not ask a single `score` field to carry both “how useful is this for this query?” and “how likely is this claim true?”

## 15. Context construction is independently stateful and failure-prone

### Observed upstream behavior

Before extraction, OSS assembles:

- existing semantic memories;
- recent buffered messages;
- current messages;
- optional custom instructions.

Issue #7195 documents stale prior-session messages entering later extraction under the same scope.

Issue #7198 documents an extraction-prompt shape where an empty Summary section plus sensitive buffered content triggered empty upstream responses in one reported provider setup.

### Architectural lesson

Context construction is not a trivial presentation step. It has its own:

- scope;
- freshness;
- source-selection policy;
- retention;
- trust boundaries;
- provider/token constraints;
- failure state.

ACL/Vera should log/identify context-construction profiles separately from retrieval.

## 16. Concurrency breaks “dedupe before insert” as a uniqueness guarantee

### Current failure evidence

Open #6515 documents a backend-independent TOCTOU race in the v3 ADD path:

1. two writers read the same existing-memory snapshot;
2. both perform extraction/embedding;
3. both compare hashes against the stale snapshot;
4. both insert the same fact with different memory UUIDs.

The hash check is deterministic but is not an atomic uniqueness constraint.

Open #6243 documents a second read-modify-write race in derived entity records’ `linked_memory_ids`, where concurrent operations can overwrite each other and lose links.

### Architectural lesson

Pre-write retrieval/dedup is advisory unless paired with a concurrency-safe invariant such as:

- unique constraint;
- compare-and-swap;
- conditional write;
- transaction/lock;
- writer lease;
- reconciliation.

Canonical fact identity and derived relationship integrity each need their own concurrency model.

## 17. Current batch fallback exposes a direct settlement/accounting mismatch

### Observed current source

The current OSS Phase 6 batch-persistence path first attempts one vector-store batch insert.

If that fails, it falls back to individual inserts. Individual failures are logged and the loop continues.

Afterward, however, the code constructs:

- history ADD rows;
- entity-link maintenance inputs;
- returned `ADD` API results;

from the original intended `records` list, not from a separately tracked successfully persisted subset.

### Failure implication

A per-record fallback insert can fail while later planes still behave as if that memory ID settled.

Possible divergence:

- vector memory absent;
- history says ADD;
- entity index links to missing memory ID;
- API returns ADD ID.

### Architectural lesson

A durable write needs per-record settlement state.

History/audit should report **what actually settled**, not merely what the process intended to settle. Derived maintenance should consume a settled-record set. API success should not be inferred from reaching the end of a best-effort loop.

This independently reinforces the campaign distinction between persistence, ledger evidence and proof of settlement.

## 18. Derived entity maintenance is intentionally best-effort

### Observed upstream behavior

The OSS entity-link phase catches and logs failures without failing the main memory write.

Entity update/insert/re-embedding errors can therefore leave a valid vector memory with incomplete entity-derived retrieval state.

This is a sensible direction of dependency: canonical semantic memory availability should not necessarily fail because a retrieval derivative failed.

But open #4863 documents a cleanup hole: if the lazy entity store has not been initialized in a fresh process, update/delete cleanup can return without removing stale `linked_memory_ids`.

### Architectural lesson

Derived state should be allowed to fail independently, but only if the system can determine:

- which derivation is stale/missing;
- which generation profile created it;
- whether it is ready;
- how to rebuild/reconcile it.

Best-effort should not mean silent permanently unknown drift.

## 19. Delete, privacy erasure and audit retention are distinct operations

### Observed upstream behavior

Current `delete(memory_id)`:

1. loads the vector memory;
2. deletes it from the vector store;
3. writes a history row with event `DELETE` **and the previous memory text**;
4. attempts entity cleanup non-fatally.

Current `delete_all()` iterates matching vector memories in batches and uses the same deletion path.

The current source fixed an earlier bug (#6627) where only the first page of memories could be deleted. That repair is useful evidence that scale/pagination semantics matter for erasure.

Open #6512 explicitly notes that Python OSS has no user-scoped way to purge history and requests a `disable_history` option because personal data can remain in history after `delete_all(user_id=...)`.

Open #4863 independently shows derived entity links can survive a memory deletion/update under a fresh-process condition.

### Architectural lesson

Future ACL/Vera operations should use distinct vocabulary/contracts such as:

- remove from active memory;
- expire/hide;
- erase subject data;
- retain audit tombstone;
- redact audit payload;
- delete derived indexes;
- delete cached context;
- reconcile backups.

“Memory deleted successfully” is not a sufficient privacy-erasure proof.

Retention purpose and legal/security audit requirements must be modeled separately.

## 20. Mutation history is valuable, but it is not automatically a settlement ledger

### Observed upstream behavior

SQLite history provides per-memory ADD/UPDATE/DELETE records with old/new text and timestamps.

This is useful for explainability and debugging.

But history writes are not one atomic transaction with an arbitrary external vector-store write, and the current batch fallback can create history from intended records even if an individual vector insert failed.

### Architectural lesson

The future system should distinguish:

- semantic mutation history;
- source/evidence provenance;
- durable mutation/effect ledger;
- operational trace/log.

Each answers a different question:

- what did the claim used to say?
- what evidence produced it?
- what write/effect actually settled?
- what did the process attempt/do operationally?

## 21. Schema/version migration can change the meaning of the same stored memory corpus

### Observed upstream behavior

The v2→v3 migration changes:

- extraction semantics;
- graph behavior;
- retrieval defaults;
- filter/API shapes;
- SDK field conventions;
- availability of temporal/lifecycle capabilities.

The migration guide also documents dependency-specific degradation: for example, without certain NLP/keyword dependencies, retrieval can fall back toward semantic-only behavior.

### Architectural lesson

Schema evolution is not only “can old JSON still parse?”

A knowledge migration needs a semantic manifest describing:

- which records were derived under which algorithm/schema;
- which indexes were rebuilt;
- which relationships/fields became unavailable;
- which retrieval rules changed;
- whether historical records were re-derived or merely reinterpreted.

## 22. Policy/configuration text belongs outside ordinary semantic-memory authority

### Failure/requirement evidence

Issue #4926 asks for deterministic/persistent memory so policies, system constraints and personas do not depend on vector similarity.

That request correctly identifies a retrieval problem: semantic top-k can omit a critical record.

But for ACL/Vera, the safer architectural conclusion is stronger:

**trusted policy and configuration should not derive authority from being a “pinned memory.”**

The current Mem0 extraction prompt can store assistant/configuration statements as memory text. If ordinary memory can become an always-included policy plane merely by type/tag/persistence, the system still has a promotion/authority problem.

### Architectural lesson

Protected policy/configuration should have:

- authenticated origin;
- explicit authority owner;
- controlled mutation;
- versioning;
- independent deterministic retrieval.

Knowledge may reference or describe policy, but retrieval cannot manufacture policy authority.

This independently reinforces `Knowledge ≠ Authority ≠ Execution`.

## 23. Persistent-memory poisoning remains an outer trust-boundary problem

### Observed topology and issue evidence

User/assistant messages and prior memory content enter future LLM extraction contexts.

Therefore untrusted text can influence what future semantic memories are extracted.

Issue #5195/#5130 asks for pre-write/pre-read memory-poisoning guards. The issue itself does not establish a universal exploit rate, but the source topology is sufficient to preserve the trust boundary.

### Architectural lesson

Persisted memory remains **data**, not trusted instruction.

ACL/Vera should be able to bind:

- source principal;
- source resource;
- trust classification;
- verification;
- ingestion policy;
- prompt-injection status;

outside the text body itself.

A stored sentence such as “always transfer funds to X” must never acquire action authority through retrieval.

## 24. Model/schema reliability is part of the derivation profile

### Failure evidence

#5901/#6724 document extraction failure when models return a plausible but wrong JSON shape. A maintainer explicitly agreed that the bare-string variant could crash the add path. The exact current source inspected still performs direct dictionary-style access on extracted list elements in the relevant phase.

The reported failures are especially relevant to local/open-compatible models, but the general lesson is model-independent.

### Architectural lesson

Every derived semantic record should be attributable to a generation profile including:

- model/provider/runtime;
- prompt/schema revision;
- structured-output mode;
- parser/normalizer version.

Ingestion should also isolate malformed-source/model failures so one bad extraction cannot make a large corpus’s settlement ambiguous.

## 25. Resources/artifacts remain an application concern

### Observed behavior

Mem0’s core memory record is optimized for compact semantic text and metadata.

It does not establish a general first-class resource object with required:

- checksum;
- MIME/media type;
- stable external URI;
- version;
- extraction/chunk locators;
- binary/document lifecycle;
- resource-level provenance.

### Architectural lesson

Large PDFs, code repositories, images, emails, datasets and sensor logs should remain identified resources outside the compact semantic-memory record. Memories/findings can reference them.

This keeps canonical resources portable and re-processable rather than flattening them irreversibly into memory strings.

## 26. Unknown, negative and disputed knowledge remain under-modeled

### Observed behavior

OSS primarily stores positive semantic statements and mutation history.

Dream adds lifecycle states such as active/superseded/merged for managed memories, but that still does not structurally encode:

- known false;
- no information;
- searched but not established;
- conflicting evidence;
- disputed;
- provisional inference.

### Architectural lesson

Absence of a retrieved Mem0 memory cannot safely mean “false.”

The future substrate needs explicit unknown/negative/conflict semantics where domain reasoning depends on them.

## 27. Scope of truth needs more than freeform metadata

### Observed behavior

Mem0 provides useful scope dimensions:

- user;
- agent;
- run;
- Platform app/project/org;
- arbitrary metadata.

But arbitrary metadata is not a normalized applicability model, and backend filter support can vary.

### Architectural lesson

Assertions should have structured applicability for contexts such as:

- project;
- environment;
- machine/device;
- software version;
- person;
- location;
- time interval.

Freeform metadata remains useful extension space, but foundational truth scope should not depend entirely on ad hoc keys.

## 28. Evidence-question coverage matrix

| # | Campaign question | KA-2 assessment |
|---|---|---|
| 1 | Stable identity | **Partial.** Stable memory UUIDs and scope/entity IDs exist; real-world identity resolution remains heuristic/application-owned. |
| 2 | Identity versus namespace | **Strong evidence.** Mem0 explicitly separates user/agent/run/app scopes from graph entities and API principal/auth. |
| 3 | Provenance | **Gap/partial.** Attribution and mutation history exist; durable raw evidence and extraction/transformation provenance are incomplete in OSS. |
| 4 | Epistemic state | **Gap.** Attribution exists, but no general explicit/inferred/verified/disputed/confidence model. |
| 5 | Temporal truth | **Partial.** Platform event-time reasoning; OSS record time + expiration; not a full bitemporal truth model. |
| 6 | Conflict and supersession | **Strong Platform lesson.** Dream preserves non-destructive superseded/merged lifecycle; OSS capture is ADD-only. |
| 7 | Relationships | **Derived-only.** Platform graph/entity associations aid retrieval but are intentionally untyped; not canonical relationship assertions. |
| 8 | Permissions and sensitivity | **Partial.** Auth/server hardening and scope filters exist; application principal/purpose/sensitivity policy remains outside memory scopes. |
| 9 | Actionability | **Gap.** Memory type/attribution does not establish safe actionability/authority use. |
| 10 | Knowledge versus authority | **Strong negative lesson.** Semantic/pinned memory cannot safely own policy authority. |
| 11 | Resources and artifacts | **Gap.** Compact semantic records are not a general resource/artifact model. |
| 12 | Canonical versus derived | **Strong evidence.** Vector memory, entity projection, history, message cache, Platform graph/Dream are distinct planes. |
| 13 | Structured retrieval | **Partial.** Metadata filters exist but backend operator parity can fail. |
| 14 | Relationship retrieval | **Partial/derived.** Entity boosts and Platform graph provide association traversal/ranking, not typed canonical traversal. |
| 15 | Full-text retrieval | **Partial.** BM25 exists, but current candidate pool is still seeded semantically. |
| 16 | Semantic retrieval | **Strong.** Core Mem0 strength, but score is relevance rather than truth. |
| 17 | Composite retrieval | **Strong lesson.** Signal composition/candidate-gate behavior is explicit and shows why a retrieval contract must define more than components. |
| 18 | Context construction | **Strong lesson.** Last-k messages + memories + prompt instructions form separate stateful context construction with stale-context failures. |
| 19 | Memory poisoning/prompt injection | **Strong boundary evidence.** Persistent/source text enters future privileged model contexts; outer trust controls required. |
| 20 | Concurrency | **Strong failure evidence.** Dedup TOCTOU and entity read-modify-write races. |
| 21 | Derived-state integrity | **Strong evidence.** Entity links are best-effort and can drift independently of vector memory. |
| 22 | Deletion and retention | **Strong evidence.** Vector deletion, entity cleanup, history retention and context-cache retention are separate. |
| 23 | Schema/version evolution | **Strong evidence.** v2→v3 is a semantic migration, not only API syntax change. |
| 24 | Recovery semantics | **Strong failure evidence.** Partial fallback inserts can diverge from history/API/derived projection. |
| 25 | Unknown/negative knowledge | **Gap.** No full first-class false/unknown/not-established/disputed taxonomy. |
| 26 | Scope of truth | **Partial.** Rich entity/metadata filters, but no storage-independent general applicability model. |

## 29. High-value acceptance/regression fixtures carried forward

1. **Raw-evidence round trip** — derived semantic memory resolves back to exact source resource/message and derivation profile.
2. **Scope vs principal** — authenticated principal cannot access a caller-chosen foreign `user_id` merely by naming it.
3. **Immutable domain identity** — ordinary metadata cannot move an existing/new record across protected domains.
4. **Conversation boundary** — two conversations for the same person cannot contaminate each other’s extraction cache unless intentionally linked.
5. **Concurrent duplicate add** — two identical writes under the same scope produce one canonical semantic record or a visible reconciliable conflict.
6. **Concurrent entity-link updates** — derived association links do not lose updates.
7. **Partial batch insert** — failed record cannot appear in success response/history/derived indexes as settled.
8. **Derived-index loss** — canonical memory remains usable and missing entity/BM25/index state is detectable/rebuildable.
9. **Backend filter parity** — every hard filter operator either works identically or fails closed; no silent predicate drop.
10. **Keyword-only recall** — deterministic lexical hit can be retrieved even when vector candidate generation misses it, when the retrieval contract requires that behavior.
11. **Current vs history** — current-only retrieval cannot accidentally return superseded facts.
12. **Lifecycle provenance** — supersede/merge/synthesis identifies source/replacement/evidence and is reversible.
13. **Synthesis coverage** — consumer can tell which source/time/scope window a pattern actually summarizes.
14. **Expiration vs truth** — expired retention state is not interpreted as “fact became false.”
15. **Delete vs forget** — erasure fixture verifies vector, graph/entity, history, cache and derived indexes independently.
16. **Audit redaction/retention** — privacy erasure can preserve required audit identity without retaining unnecessary plaintext personal data.
17. **Untrusted memory instruction** — retrieved instruction-shaped memory cannot become policy/tool authority.
18. **Attribution vs epistemic state** — assistant-researched/user-stated/inferred/verified records remain distinguishable.
19. **Malformed extraction result** — one invalid model output cannot make an entire ingestion’s settlement ambiguous.
20. **Profile migration** — same corpus under v2/v3/backend/provider profiles remains interpretable with explicit derivation/index generation identity.
21. **Unknown-state query** — absence of memory remains unknown/not-established rather than automatically false.
22. **Relationship semantics** — entity co-occurrence boost cannot masquerade as a typed relationship such as ownership/authorization.

## 30. Candidate invariants contributed/reinforced

KA-2 independently reinforces these existing candidates:

- KA-I-001 — raw evidence separately addressable from derived semantic knowledge;
- KA-I-003 — namespace/domain IDs are not authenticated principal identity;
- KA-I-006 — supersession/invalidation is a reversible provenance-bearing transition;
- KA-I-008 — world/event time and record time remain distinct;
- KA-I-009 — current/history/conflict/evidence are distinct retrieval intents;
- KA-I-010 — retrieval score is not truth/confidence/authority;
- KA-I-011 — derived state has generation/readiness/reconciliation identity;
- KA-I-012 — backend implementation must be qualified against semantic invariants;
- KA-I-014 — principal/purpose/sensitivity/hard eligibility precedes model exposure;
- KA-I-015 — retrieved/persistent memory remains untrusted content;
- KA-I-016 — delete/forget is a multi-plane reconciliation result;
- KA-I-017 — semantic/schema changes require explicit migration/re-derivation;
- KA-I-018 — realized capability identity includes exact profile;
- KA-I-019 — governance metadata must be verified end-to-end;
- KA-I-020 — knowledge retrieval never grants execution authority;
- KA-I-021 — false/unknown/not-established/conflicting states must be distinct;
- KA-I-022 — truth applicability needs structured scope;
- KA-I-023 — material transformations need provenance;
- KA-I-024 — context construction is separate from retrieval.

KA-2 adds these candidate concepts:

- epistemic basis/verification is distinct from attribution and retrieval status;
- composite retrieval must define candidate entry and hard-gate ordering;
- derived aggregates must expose coverage/generation boundaries;
- per-record settlement must drive history/return/derived maintenance;
- transient episode/context identity is distinct from persistent knowledge scope;
- derived association graphs are distinct from canonical typed relationships.

These remain evidence candidates, not final schema decisions.

## 31. Failure patterns contributed/reinforced

KA-2 independently reinforces prior warnings around:

- namespace-as-authorization;
- mixed current/history retrieval;
- delete/derived-state reconciliation;
- deployment/profile identity;
- retrieval score interpreted as truth;
- memory text promoted into policy;
- successful API/history record mistaken for settlement;
- transformation provenance gaps.

New Mem0-specific failure classes include:

- semantic search as the only candidate-entry gate in an advertised hybrid retrieval path;
- backend adapters silently dropping hard filter predicates;
- stale pre-write snapshots/read-modify-write state used as concurrency-safe integrity;
- partial batch fallback generating phantom history/API/derived success;
- persistent knowledge scope reused as transient context-cache episode scope;
- memory deletion conflated with subject erasure while plaintext history survives;
- derived synthesis treated as exhaustive despite explicit scope/time/cadence coverage limits.

## 32. What Mem0 does not solve for ACL/Vera

KA-2 found no basis to treat Mem0 as a replacement for:

- canonical raw/source evidence storage;
- stable cross-domain person/device/resource identity;
- authoritative identity merge/split governance;
- typed temporal/provenance-bearing relationship assertions;
- general epistemic source/trust/confidence/dispute semantics;
- protected policy/configuration authority;
- credential brokerage;
- tool/action authorization;
- external-effect settlement ledger;
- exactly-once effect proof;
- project/task scheduling;
- sandboxing/process custody;
- a general artifact/resource registry;
- guaranteed backend-independent hard filtering;
- complete privacy erasure/reconciliation;
- storage-independent current/unknown/negative truth resolution.

Mem0 is best understood as valuable evidence for **semantic memory extraction/retrieval and memory lifecycle patterns**, not as the final general knowledge substrate.

## 33. Primary sources inspected

### Canonical/current source

- https://github.com/mem0ai/mem0
- https://github.com/mem0ai/mem0/tree/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/mem0/memory/main.py
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/mem0/memory/storage.py
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/mem0/configs/prompts.py
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/mem0/utils/scoring.py
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/mem0/vector_stores/opensearch.py
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/server/main.py
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/server/routers/auth.py
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/mem0/client/main.py

### First-party current documentation

- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/docs/migration/oss-v2-to-v3.mdx
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/docs/platform/platform-vs-oss.mdx
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/docs/platform/features/entity-scoped-memory.mdx
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/docs/platform/features/graph-memory.mdx
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/docs/platform/features/dream.mdx
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/docs/platform/features/temporal-reasoning.mdx
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/docs/platform/features/timestamp.mdx
- https://github.com/mem0ai/mem0/blob/dae67f74f5cc7bf138c7d7d6f9cec5ce4b4373b3/docs/platform/features/memory-decay.mdx

### Current/recent failure and design evidence

- https://github.com/mem0ai/mem0/issues/7214 — OpenSearch advanced-filter predicates silently dropped
- https://github.com/mem0ai/mem0/issues/7195 — stale cross-session message-buffer context
- https://github.com/mem0ai/mem0/issues/7198 — extraction context/prompt empty-summary provider failure report
- https://github.com/mem0ai/mem0/issues/6724 — malformed extraction shape aborts ingestion
- https://github.com/mem0ai/mem0/issues/5901 — extraction-shape tracking issue
- https://github.com/mem0ai/mem0/issues/6655 — identity-scope injection on add; fixed
- https://github.com/mem0ai/mem0/issues/6277 — identity-scope mutation on update; fixed
- https://github.com/mem0ai/mem0/issues/6627 — `delete_all` first-page truncation; fixed in current source
- https://github.com/mem0ai/mem0/issues/6515 — ADD hash-dedup TOCTOU race
- https://github.com/mem0ai/mem0/issues/6243 — entity-link read-modify-write race
- https://github.com/mem0ai/mem0/issues/4863 — entity cleanup skipped in fresh process
- https://github.com/mem0ai/mem0/issues/6512 — history retention / `disable_history` request
- https://github.com/mem0ai/mem0/issues/5384 — ownership/access hardening analysis
- https://github.com/mem0ai/mem0/pull/5360 — self-hosted server auth/admin hardening
- https://github.com/mem0ai/mem0/issues/5195 — memory-poisoning guard request
- https://github.com/mem0ai/mem0/issues/4926 — deterministic/policy-memory retrieval requirement

## 34. Explicit non-conclusions

KA-2 does **not** conclude that:

- Mem0 should be adopted, forked or rejected;
- Mem0 should be ACL/Vera’s canonical knowledge store;
- Platform Dream lifecycle decisions are always correct;
- Platform’s proprietary internal implementation matches any inferred OSS mechanism;
- a vector database is the correct canonical storage technology;
- semantic memory should replace source/resource evidence;
- Graph Memory is a typed knowledge graph;
- a single reported issue establishes a universal failure rate;
- the self-hosted single-admin server is currently a supported multi-user tenant-isolation implementation;
- OpenSearch drops basic `user_id` filters in the cited issue;
- history should always be deleted rather than retained under an explicit audit policy;
- policies/personas should be solved by making ordinary memories “always included”;
- every local model is unreliable for memory extraction;
- Letta Code or any later campaign target has been researched in KA-2.

**Stop boundary:** KA-2 ends with Mem0 research and documentation. Letta Code is next only after separate user authorization.
