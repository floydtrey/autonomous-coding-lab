# LangGraph Knowledge-Architecture Revisit — KA-6

**Task:** KA-6 — LangGraph Knowledge-Architecture Revisit  
**Campaign:** Knowledge Architecture Evidence Campaign  
**Research date:** 2026-09-08  
**ACL starting checkpoint:** `c223920e625305fea8a8b7a7f04b2ffaa40088d2`  
**LangGraph upstream revision inspected:** `81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1`  
**LangGraph package version:** `1.2.11`  
**Historical report revisited:** `docs/research/projects/langgraph.md`

## 1. Scope and stop boundary

This task revisits LangGraph specifically as evidence for ACL/Vera's **general knowledge architecture**. It does not select LangGraph, a checkpoint backend, a Store implementation, a final ontology, a final retrieval architecture, or an execution framework.

The task asks what LangGraph's current persistence/runtime model teaches us about:

- durable identity;
- checkpoint versus long-term knowledge state;
- provenance and record lineage;
- temporal meaning;
- current versus historical state;
- relationship and epistemic gaps;
- namespace and authority boundaries;
- structured and semantic retrieval;
- context construction;
- replay identity;
- concurrency and partial settlement;
- schema/serialization evolution;
- deletion and retention;
- derived-state integrity;
- recovery and human approval state.

The task stops after updating the cumulative knowledge-architecture evidence ledgers and campaign state. Google ADK is not researched here.

---

## 2. Evidence boundary and current-version verification

### 2.1 ACL campaign state

Before research, the ACL branch was verified at:

`research/agent-landscape` → `c223920e625305fea8a8b7a7f04b2ffaa40088d2`

That is the KA-5 Mastra checkpoint. The campaign state named LangGraph as the next candidate but explicitly required separate user authorization. The user supplied that authorization with `Start ka6`.

### 2.2 LangGraph upstream state

Current `langchain-ai/langgraph` `main` was reverified at:

`81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1`

`libs/langgraph/pyproject.toml` reports:

`langgraph = 1.2.11`

This is the **same source revision and package version** inspected in the historical Task 7 report. Therefore KA-6 is not an upstream-code-delta study. It is a deeper knowledge-substrate analysis of the same current source plus issue evidence that appeared after the historical research pass.

### 2.3 Primary evidence inspected

Current source/docs included:

- `libs/langgraph/pyproject.toml`
- `libs/langgraph/langgraph/types.py`
- `libs/langgraph/langgraph/runtime.py`
- `libs/langgraph/langgraph/channels/delta.py`
- `libs/langgraph/langgraph/pregel/_loop.py`
- `libs/langgraph/langgraph/pregel/_algo.py`
- `libs/checkpoint/langgraph/checkpoint/base/__init__.py`
- `libs/checkpoint/langgraph/checkpoint/serde/jsonplus.py`
- `libs/checkpoint/langgraph/store/base/__init__.py`
- `libs/checkpoint/langgraph/store/memory/__init__.py`
- current LangChain/LangGraph Persistence docs
- current LangGraph Memory docs

Concrete current/recent issue evidence included:

- #8039 — sync durability / pending-write versus checkpoint ordering
- #8458 — subgraph time-travel replay namespace identity
- #8579 — scalar resume accepted for multiple child interrupts
- #8653 — config-injected checkpointer hydration and destructive `update_state`
- #8582 — failed `Send` loses `UntrackedValue` input on resume
- #8531 — safe checkpoint pruning and DeltaChannel dependency closure
- #7206 — stale writers can resurrect deleted checkpoint threads
- #8837 — consumed resume payload re-delivered to later interrupt
- #8836 — zero-match interrupt-ID resume map silently ignored
- #8835 — `InMemoryStore` read aliases canonical stored memory
- #8834 — failed conditional routing disappears after state write settles
- #8833 — SQLite mixed-batch retry retains stale special write
- #8831 — backend-dependent default Store ordering/pagination
- #8829 — backend-dependent unsupported filter behavior
- #8826 — timezone rule/fold lost through checkpoint serialization
- #8822 — one semantic embedding reused for multiple targets breaks in-memory indexing
- #8821 — DeltaChannel live update and replay reconstruction diverge

Open issue evidence is treated as failure evidence, not as a maintainer-confirmed universal defect in every deployment. Where an issue contains scope limitations, corrections, or untested backends, those limitations are retained below.

---

## 3. LangGraph has two persistence systems, not one memory substrate

### Observed behavior

Current official persistence documentation explicitly separates:

1. **Checkpointers** — persist a single thread's graph state as checkpoints for short-term/thread-scoped memory, HITL, recovery, and time travel.
2. **Stores** — persist application-defined key/value data outside graph state for long-term/cross-thread memory such as preferences, facts, and shared knowledge.

Current source mirrors that split:

- `BaseCheckpointSaver` persists checkpoint state, parent lineage, versions, pending task writes and replay state keyed primarily by `thread_id` plus checkpoint namespace/ID.
- `BaseStore` persists application records by `(namespace, key)` and optionally adds structured filtering, semantic indexing and TTL.
- `Runtime` injects the Store separately from `ExecutionInfo` and execution/checkpoint metadata.

### Architectural lesson

For ACL/Vera, this is strong positive evidence that **replayable execution state and durable semantic knowledge should not be collapsed into one persistence object**.

A checkpoint answers questions such as:

- what graph state existed at a recovery point?
- what node/task is next?
- which task writes already settled?
- what parent checkpoint produced this state?

A long-term knowledge record answers different questions:

- what durable fact/preference/resource/application datum is stored?
- under what semantic scope?
- from what evidence?
- how current/trusted/verified is it?

LangGraph's Store does not itself provide those richer epistemic answers, but its explicit separation from checkpoints is useful evidence for our layer boundary.

### Confidence

High.

### Non-conclusion

This does not establish that ACL/Vera should use LangGraph Store as its canonical knowledge database.

---

## 4. Checkpoint identity is execution identity, not semantic knowledge identity

### Observed behavior

`Checkpoint` contains:

- format version `v`;
- unique monotonically increasing checkpoint `id`;
- timestamp;
- channel values;
- per-channel versions;
- node/channel versions seen;
- updated-channel list.

`CheckpointMetadata` adds:

- source: `input`, `loop`, `update`, or `fork`;
- step number;
- parent checkpoint IDs by namespace;
- run ID;
- DeltaChannel reconstruction counters.

`CheckpointTuple` adds:

- config;
- checkpoint;
- metadata;
- parent config;
- pending writes.

`ExecutionInfo` separately contains:

- checkpoint ID;
- checkpoint namespace;
- task ID;
- thread ID;
- run ID;
- node attempt number;
- first-attempt time.

### Architectural lesson

This is a strong positive reference for **execution lineage**. ACL/Vera should likewise keep separate stable identities for:

- durable work/thread;
- run;
- attempt;
- checkpoint/recovery point;
- task/tool call;
- parent/child lineage.

But these are not substitutes for semantic entity/assertion/resource identities. A checkpoint ID identifies an execution snapshot, not “the user,” “the device,” “the fact,” or “the source document.”

### Confidence

High.

---

## 5. `thread_id` and Store namespaces are routing scopes, not authenticated principals

### Observed behavior

The checkpoint base documentation calls `thread_id` the primary key used to store and retrieve checkpoints.

`BaseStore` says application data can be organized under arbitrary hierarchical namespaces, including user IDs, assistant IDs, or other application-defined values.

Current memory examples construct namespaces from runtime context such as a `user_id`.

Separately, `Runtime.ServerInfo` contains an authenticated `BaseUser | None` when LangGraph Server injects authenticated server information.

Therefore current source structurally distinguishes:

- checkpoint/thread scope;
- Store namespace;
- runtime application context;
- authenticated server user.

### Architectural lesson

This independently reinforces:

> Namespace/domain/thread identifiers do not become principals merely because they partition persisted data.

For ACL/Vera, a query such as `("users", user_id, "memories")` is useful routing metadata, but access still needs principal/purpose/policy evaluation outside the namespace string itself.

### Confidence

High.

### Non-conclusion

No claim is made that LangGraph Server ignores authorization. The point is narrower: storage identity and authenticated principal identity are separate concepts in the current architecture.

---

## 6. Long-term Store records are operational records, not epistemic assertions

### Observed behavior

A Store `Item` contains:

- `value: dict[str, Any]`;
- key;
- namespace;
- `created_at`;
- `updated_at`.

`SearchItem` adds an optional relevance/similarity score.

`PutOp` can control indexing and TTL.

The value is deliberately application-defined JSON-like data.

### Missing general epistemic structure

The ordinary Store record does not require fields for:

- explicit user statement versus inference;
- observation versus hypothesis;
- verified versus unverified;
- confidence;
- source trust;
- contradiction/dispute state;
- supersession;
- valid-from / valid-until world time;
- known-false / unknown / searched-not-established;
- authority-use eligibility;
- sensitivity/purpose policy;
- transformation/model/prompt lineage.

Applications can place any of these fields in `value`, but the Store does not enforce a common truth model.

### Architectural lesson

LangGraph Store is a useful persistence/retrieval abstraction, not a complete canonical epistemic substrate for Vera.

### Confidence

High.

---

## 7. Record timestamps are not world-valid temporal truth

### Observed behavior

Store items expose `created_at` and `updated_at`.

Checkpoint snapshots expose their creation timestamp.

These describe when records/checkpoints were created or updated. They do not express when a proposition became true in the external world, when it ceased to be true, or when a later correction superseded an earlier belief.

### Architectural lesson

LangGraph independently supports the campaign distinction between:

- system/record/transaction time; and
- world/event-valid time.

A Vera statement such as “front door was unlocked from 03:02 to 03:07” needs semantic validity time even if the memory record was written at 03:10 and later corrected at 03:15.

### Confidence

High.

---

## 8. Store semantic search is retrieval, not truth

### Observed behavior

`SearchOp` supports:

- namespace-prefix scope;
- structured filters;
- limit/offset;
- optional natural-language query.

When semantic indexing is configured, Store records can be embedded and searched by similarity. `SearchItem.score` carries relevance/similarity.

Index configuration includes:

- embedding dimension;
- embedding model/function;
- JSON fields/paths selected for indexing.

### Architectural lesson

Embedding model, field-selection profile, index implementation and query semantics are all **derived retrieval profile**.

A semantic score says “this result ranked as relevant under this retrieval profile.” It does not say:

- the fact is true;
- the fact is current;
- the fact is authorized;
- the source is trustworthy;
- the statement has high epistemic confidence.

### Confidence

High.

---

## 9. Backend semantics are part of realized knowledge behavior

### 9.1 Default ordering and pagination — #8831

Issue #8831 reports the same Store writes followed by an unqualified `search()` return:

- InMemoryStore: insertion order;
- SQLite/Postgres: `updated_at DESC`.

Pagination therefore returns different items per backend for the same logical request.

The issue also notes SQLite timestamp ties can leave relative ordering unspecified.

### 9.2 Filter failure semantics — #8829

Issue #8829 reports unsupported `$and` / `$or` filter combinators produce:

- silent empty result in InMemoryStore;
- explicit `ValueError` in SQLite;
- silent no-match in Postgres under the reporter's corrected analysis.

The BaseStore docs do not advertise `$and`/`$or`, so this is not evidence that an advertised combinator is silently dropped. It is evidence that **invalid/unsupported query behavior differs by backend** and can collapse “unsupported” into “no matching knowledge.”

### 9.3 Pending-write retry semantics — #8833

Issue #8833 reports that repeated special-channel writes behave differently when an ordinary channel is included in the same batch:

- InMemorySaver updates the newer `__error__` value;
- SQLite can preserve the stale `__error__` value because mixed batches use ignore rather than per-write replacement semantics.

The reporter explicitly does not establish how often the default runtime emits this exact mixed retry batch.

### Architectural lesson

A declared high-level interface is not enough. ACL/Vera must qualify persistence/retrieval backends against semantic invariants such as:

- ordering and tie-breaker;
- filtering and unsupported-operator behavior;
- write conflict semantics;
- idempotent retry semantics;
- TTL/delete behavior;
- transaction/atomicity boundaries.

### Confidence

High for the architectural lesson; issue-specific runtime frequency varies.

---

## 10. Read-only retrieval must not alias canonical stored state — #8835

### Failure evidence

Issue #8835 demonstrates a Store-specific backend divergence:

1. Store a profile in `InMemoryStore`.
2. Read it with `get()`.
3. Mutate the returned dictionary only to build a redacted prompt view.
4. Never call `put()`.
5. A later read shows the canonical in-memory Store record has changed.

The same application code against SQLite does not modify the persisted record.

Current source corroborates the mechanism:

- `GetOp` returns the stored `Item` directly;
- search results pass `item.value` into new `SearchItem`s;
- put performs only a shallow `dict(op.value)` copy, so nested containers remain aliased.

### Architectural lesson

This is materially different from ordinary stale-write races.

Canonical knowledge exposed to retrieval/context/projection code needs one of:

- immutable/value semantics;
- explicit snapshots/copies;
- an explicit versioned mutation handle/API.

A caller preparing context must not accidentally mutate canonical knowledge simply by editing a retrieved object in memory.

### New candidate invariant

**KA-I-038:** Canonical knowledge reads exposed to retrieval, projection or context-construction code must have value/snapshot semantics or an explicit mutation contract; incidental object mutation must not alter canonical state.

### New failure pattern

**KA-F-039:** A supposedly read-only retrieval/projection aliases canonical stored memory, so mutating the returned object silently writes knowledge without a mutation event.

### Confidence

High.

---

## 11. Persistence equality is weaker than semantic round-trip fidelity — #8826

### Failure evidence

Issue #8826 reports that `JsonPlusSerializer` serializes `datetime` through `isoformat()` and reconstructs through `fromisoformat()`.

For a `ZoneInfo("America/New_York")` datetime:

- the restored datetime represents the same instant;
- equality can therefore return `True`;
- but the restored timezone becomes a fixed UTC offset rather than the original timezone rule;
- `fold` is lost;
- arithmetic across a DST transition can produce a different future wall-clock result after resume.

Current source corroborates:

- `datetime` is serialized as ISO text;
- `time` separately serializes constructor fields including `tzinfo` and `fold`;
- `ZoneInfo` itself has a dedicated serializer.

### Architectural lesson

A persistence round-trip can pass a value-equality test while still losing behavior-bearing semantics.

This generalizes beyond timezones to:

- units;
- locale/calendars;
- identity classes;
- policy labels;
- cryptographic/key versions;
- source locators versus content digests;
- typed states whose future interpretation depends on metadata.

### New candidate invariant

**KA-I-039:** Persistence/migration round-trips must preserve behavior-bearing semantic metadata required for future interpretation, not merely produce a value that compares equal at the moment of restoration.

### New failure pattern

**KA-F-040:** A serialized value appears equal after restoration but has lost behavior-bearing semantic metadata, so future reasoning or action differs after resume.

### Confidence

High.

### Non-conclusion

The issue is open; this task does not claim a merged upstream correction.

---

## 12. Live transition semantics and replay semantics must agree — #8821

### Failure evidence

`DeltaChannel` explicitly requires deterministic, batching-invariant reducer behavior because it reconstructs state by replaying ancestor writes.

Current source has two code paths:

- `update()` for live execution;
- `replay_writes()` for reconstruction.

Issue #8821 reports that for the same batch containing an `Overwrite(...)` followed by a normal write:

- live `update()` sets the overwrite and returns immediately, dropping the later normal write;
- `replay_writes()` applies the overwrite as the new base and folds later writes, preserving them.

Thus the state that actually ran can differ from the state reconstructed from persisted evidence.

### Architectural lesson

For any state we advertise as replayable/reconstructable:

> the transition algebra used during live execution and the transition algebra used during replay must be semantically equivalent for the same ordered evidence.

This is stronger than “the serializer works.” The same durable writes must reconstruct the state the runtime actually observed.

### New candidate invariant

**KA-I-040:** For replayable state, live transition semantics and replay/reconstruction semantics must be behaviorally equivalent for the same ordered persisted transition evidence.

### New failure pattern

**KA-F-041:** Live execution and replay use different transition semantics, so a recovered state differs from the state produced by the same persisted writes during the original run.

### Confidence

High for the demonstrated DeltaChannel case; DeltaChannel is explicitly beta.

---

## 13. Derived semantic indexes need one-to-many lineage integrity — #8822

### Failure evidence

Issue #8822 reports two records with distinct keys but identical indexed text in one `InMemoryStore.batch()`:

- text extraction deduplicates the identical source text;
- embedding generation correctly produces one embedding;
- insertion flattens two target identities and expects one embedding per target;
- the batch fails with an embedding/target-count mismatch.

Current source corroborates the one-to-many shape: `_extract_texts()` maps one text to multiple `(namespace, key, path)` targets, while `_insertinmem_store()` flattens all targets and zips them against embeddings.

### Architectural lesson

Derived-state identity must distinguish:

- unique source material eligible for one derivation computation; and
- every distinct derived target/attachment that should reference the resulting derivative.

This independently reinforces the existing source/derived/presentation identity invariant rather than creating another ID.

### Confidence

High.

---

## 14. A checkpoint does not pin the long-term Store revision

### Observed behavior

Current official docs and source explicitly model checkpointers and Stores as complementary but independent persistence systems.

A checkpoint captures graph state, task lineage and pending writes. `Runtime.store` is a separately injected long-term Store.

The ordinary checkpoint record does not include a canonical Store snapshot/revision identifier.

### Architectural consequence

A replayed node that reads long-term Store knowledge can observe data different from what the original attempt observed if that Store changed between attempts.

That may be desirable for some workflows. But it means deterministic replay requires an explicit decision:

- pin a knowledge revision/snapshot;
- record knowledge reads as evidence;
- accept fresh-read semantics;
- or mark the operation non-deterministic/non-replayable.

### Cumulative invariant consequence

This independently reinforces **KA-I-033** from Letta Code:

> persistent knowledge revision/profile is part of execution/replay identity whenever reproducibility or deterministic retry matters.

### Cumulative failure consequence

It also independently reinforces **KA-F-031**:

> persistent memory that influences execution can be omitted from the declared replay/task identity.

### Confidence

High for the architectural separation; the consequence depends on whether a node actually reads mutable Store data during replay.

---

## 15. Checkpoint state, pending writes and external effects are separate settlement planes

### Observed behavior

The checkpoint API distinguishes:

- checkpoint snapshots;
- task-level pending/intermediate writes.

The runtime uses pending writes to avoid rerunning some successful task work after sibling failure.

External side effects are not part of the checkpoint transaction.

### Failure evidence — #8039

Issue #8039 reports that under `durability="sync"`, checkpoint persistence and pending-write persistence can race in the background executor. Under an injected crash at the same logical point:

- if pending writes reach durable storage first, resume can replay them and avoid rerunning the node;
- if the checkpoint write wins and pending writes are absent at crash, resume reexecutes the node and duplicates its external side effect.

The issue remains open on the same current source family.

### Architectural lesson

`sync` durability is not a universal exactly-once effect guarantee.

For ACL/Vera:

- graph/checkpoint state;
- pending task-result evidence;
- workspace mutation;
- credential/authority state;
- external effect settlement;

must remain distinct recovery dimensions.

An effect ledger/idempotency mechanism remains necessary above any checkpoint engine.

### Confidence

High for the issue's reproduced paths and the architectural boundary.

---

## 16. A partial step can commit state while losing failed control flow — #8834

### Failure evidence

Issue #8834 constructs a node whose state write succeeds but whose conditional router then raises.

Initial invocation fails as expected. On `invoke(None)`:

- the previously written state is reapplied;
- the failed router is not retried;
- no downstream node runs;
- no pending task remains;
- the graph returns normally with the partially updated state.

The issue reproduces on both InMemorySaver and SQLite in the reporter's scope.

### Architectural lesson

A state mutation and the control-flow decision that makes that mutation operationally complete are separate settlement components.

A recovery substrate must be able to represent states such as:

- data write settled;
- routing/validation not settled;
- effect unknown;
- task still recoverable;
- transition failed after partial state production.

### Ledger treatment

This adds recurrence to **KA-I-028** and **KA-F-019** rather than creating a new failure ID: one successfully persisted part of a transition must not be mistaken for complete multi-plane settlement.

### Confidence

High for the reported sync StateGraph paths; async/subgraph frequency was not established by the issue.

---

## 17. Human input/approval is durable state, not merely a message

### Positive mechanism

Current `Interrupt` carries a stable `id` and value. `Command.resume` can target a mapping from interrupt IDs to response values.

The source explicitly documents that resuming reexecutes the node from its beginning, with prior resume values consumed in task-local interrupt order.

This is a useful reference for approval identity.

### Failure evidence — #8579

Issue #8579 reports a nested subgraph containing two parallel interrupts that become grouped under one parent task. A scalar resume is accepted even though two distinct interrupt IDs are pending, and the scalar value reaches one branch according to internal order.

Architectural lesson: concurrent authority-bearing waits require exact target identity; ambiguous scalar approval must fail closed.

### Failure evidence — #8836

Issue #8836 reports a resume dictionary whose 32-hex key is interpreted as an interrupt-ID map. If the key matches zero currently pending interrupt IDs, the resume is silently ignored and the thread remains interrupted.

The issue was corrected to emphasize that the result still exposes the pending interrupt if the caller inspects it; the defect is the silent zero-match no-op, not an empty response.

Architectural lesson: an authority-bearing response that targets no current request should fail loud/closed rather than being observationally easy to mistake for acceptance.

### New failure pattern

**KA-F-042:** An authority-bearing resume/approval response that matches no currently pending target is silently accepted/no-op rather than failing closed with an explicit target-mismatch result.

### Confidence

High for the reported cases.

---

## 18. Consumed approval/resume state must be durably retired — #8837

### Failure evidence

Issue #8837 demonstrates two sequential interrupts in one node:

1. first interrupt receives resume value `"first"`;
2. second interrupt becomes pending;
3. a later `invoke(None)` supplies no new resume;
4. stale persisted resume data from the first interrupt is reconstructed and delivered to the second interrupt;
5. the thread completes as if the second approval/input had occurred.

The reporter traces this to consumed resume state being removed from a local scratchpad view but remaining in checkpoint pending writes.

### Architectural lesson

Authority/actionability has temporal lifecycle:

- requested;
- pending;
- answered;
- consumed;
- settled/closed;
- historical.

A consumed approval/resume payload must not remain eligible for future action merely because its historical record remains durable.

### Ledger consequence

This is an independent LangGraph recurrence of **KA-F-038**, previously observed in Mastra replayed suspensions. KA-F-038 therefore moves to **reinforced**.

It also reinforces **KA-I-028**: durable mutation/settlement state must drive whether an input remains consumable/actionable.

### Confidence

High.

---

## 19. Untracked runtime input and resumable task are separate claims — #8582

### Failure evidence

Issue #8582 combines:

- `UntrackedValue` runtime-only resource;
- a dynamic `Send` task;
- task failure;
- checkpoint resume.

On the initial attempt the worker receives the runtime resource. Because the value is intentionally untracked, it is absent from the checkpoint. Yet the failed task remains resumable. On resume the task is retried with a structurally different input where the runtime resource is missing.

### Architectural lesson

“Not persisted” and “safe to resume” are different facts.

Every semantics-bearing input to a replayable operation must be one of:

- persisted;
- deterministically reacquirable;
- rebound through an explicit current authority/configuration source;
- or declared to make the operation non-replayable.

This independently supports the campaign's execution/replay profile requirements.

### Confidence

High.

---

## 20. Production-shaped state hydration is part of persistence semantics — #8653

### Failure evidence

Issue #8653 reports a graph compiled without an attached checkpointer but receiving the actual checkpointer through runtime config, matching LangGraph Platform wiring.

The state reader/update paths resolve the configured checkpointer for most operations but hydrate DeltaChannel state using the graph-attached `self.checkpointer`, which is `None` in this shape.

Consequences reported:

- `get_state` can show an empty messages state even when history exists;
- `update_state` can fold against the wrongly empty base and commit the empty projection forward;
- local/dev attached-checkpointer topology behaves correctly while production-shaped config injection fails.

### Architectural lesson

Dependency-injection topology and realization profile are part of persistence semantics.

A test that validates a storage class directly or validates one wiring shape does not establish correctness of the production path that resolves, hydrates, transforms and commits state.

### Ledger treatment

This reinforces:

- KA-I-012 backend/runtime-path qualification;
- KA-I-018 realized capability identity;
- KA-I-019 end-to-end verification of provenance/security-critical metadata/state;
- KA-F-013 project/package version alone is insufficient deployment identity.

### Confidence

High.

---

## 21. Subgraph replay identity must survive hierarchy changes — #8458

### Failure evidence

Issue #8458 reports time travel into a checkpoint inside a subgraph.

An eager parent fork creates a new parent checkpoint ID. Child task IDs are derived from the parent checkpoint identity, and the subgraph checkpoint namespace contains the task ID. The replay therefore lands in a new empty child namespace and reruns the subgraph from its beginning rather than from the caller-selected child checkpoint.

The issue remains open.

### Architectural lesson

Hierarchical recovery requires stable identity across:

- parent fork;
- child task identity;
- child checkpoint namespace;
- selected recovery point.

A caller-selected recovery object must not become unreachable merely because parent execution generated a new derived task ID.

### Confidence

High for the reported versions/source lineage.

---

## 22. Checkpoint pruning requires dependency closure, not “keep newest row”

### Observed source contract

`BaseCheckpointSaver.prune()` explicitly warns that DeltaChannel reconstructs state by walking ancestor checkpoints and pending writes until it reaches a snapshot seed.

A naive `keep_latest` can leave the newest checkpoint present while silently destroying the history required to reconstruct its actual channel value.

`copy_thread()` similarly warns that copying only the head checkpoint can leave the target unreconstructable.

`delete_for_runs()` warns that deleting an ancestor run can break a still-live thread whose DeltaChannel history depends on it.

### Current issue — #8531

#8531 requests safe Postgres prune support and explicitly proposes fail-closed behavior for DeltaChannel threads until dependency-aware pruning exists.

### Architectural lesson

Retention and garbage collection are graph/lineage operations whenever retained state depends on ancestors or derived artifacts.

“Keep the latest” is safe only if the retained recovery point is self-contained or the complete dependency closure is preserved.

### Confidence

High.

---

## 23. Delete requires a generation/tombstone fence — #7206

### Failure evidence

Issue #7206 reports:

1. old checkpoint config retained by a delayed writer;
2. thread is deleted;
3. stale writer later calls `put`/`put_writes` with pre-delete config;
4. thread data is recreated.

SQLite and Postgres paths were cited in the issue.

### Architectural lesson

Deleting rows is not the same as retiring an identity generation.

A durable delete/forget lifecycle needs a tombstone/generation/fencing mechanism such that stale writers cannot resurrect the deleted generation.

This is independently consistent with the campaign's multi-plane deletion and stale-writer protections.

### Confidence

High.

---

## 24. TTL is retention policy, not semantic invalidation or privacy erasure

### Observed behavior

Store `PutOp.ttl` is expressed as minutes from last access. The docs describe expired items as scheduled for deletion on a **best-effort** basis, with backend support explicitly optional.

TTL configuration can also refresh on reads and choose whether expired items are omitted before physical sweep.

### Architectural lesson

The architecture must distinguish:

- semantic valid-until;
- retrieval eligibility;
- cache expiry;
- storage retention;
- privacy erasure;
- physical sweep completion.

A TTL is not automatically any of the other five.

### Confidence

High.

---

## 25. Prompt/context placement does not upgrade memory provenance

### Observed behavior

Current LangGraph memory examples retrieve Store memory and can include it in model context/instructions.

The Store can contain application facts/preferences and semantic-search results.

Nothing about putting those records into a prompt changes how they were sourced or verified.

### Architectural lesson

This independently aligns with the campaign rule:

> retrieved/persistent memory remains content; prompt position does not transform it into governance policy or trusted authority.

### Confidence

High.

---

## 26. Tool descriptions are content, not trust — adjacent evidence from #8818

Issue #8818 reports model selection between two similarly purposed tools where the more aggressively worded description out-competes the correct but plain tool in repeated local-model tests.

This is primarily execution/tool-selection evidence rather than a Store/checkpoint defect, so it does not receive a new knowledge-architecture failure ID.

It does reinforce the broader boundary:

- model-visible descriptions are content;
- trust/provenance/authority must be supplied structurally outside persuasive text.

---

## 27. Schema evolution includes transition algebra and serializer behavior

### Observed behavior

Checkpoint format has a version field, but several behavior-bearing components live outside that one number:

- channel implementation/reducer semantics;
- DeltaChannel beta representation;
- serializer behavior;
- Store backend query semantics;
- graph topology;
- subgraph/task namespace derivation;
- runtime wiring profile.

### Evidence

- #8826: serializer semantics can change future behavior without changing current equality.
- #8821: live/replay transition implementations can diverge.
- #8458: topology/identity derivation can change replay target behavior.
- #8653: injection topology can change hydration semantics.

### Architectural lesson

For ACL/Vera, “schema version” cannot mean only JSON/database shape. A reproducible durable state profile can require:

- serialized schema version;
- reducer/transition implementation version;
- runtime/graph topology signature;
- backend adapter profile;
- model/prompt/derivation profile where model-generated knowledge is involved.

### Confidence

High.

---

## 28. Current/historical/unknown semantics are still not a general Store truth model

### Observed gap

Store has timestamps, keys, namespaces and values. Checkpoint history represents execution history. Neither automatically defines a general knowledge-state taxonomy for:

- current true;
- historical true;
- known false;
- unknown;
- searched and not established;
- disputed;
- stale;
- superseded;
- confidence-bearing inference.

### Architectural lesson

Checkpoint history should not be mistaken for epistemic history, and Store update timestamps should not be mistaken for semantic supersession.

### Confidence

High.

---

## 29. Relationships are not a canonical typed world-relation model

### Observed behavior

LangGraph itself is graph-shaped, but its graph edges express **execution/control flow**.

Store namespaces express hierarchical storage organization.

Checkpoint parent links express execution lineage.

None of these are automatically canonical assertions such as:

- person owns device;
- device located in room;
- finding derived from evidence;
- policy governs action;
- person is member of household;
- claim contradicts claim.

### Architectural lesson

Execution graph, storage hierarchy and epistemic/world relationship graph are distinct graph semantics.

### Confidence

High.

---

## 30. Resource/document provenance remains application-owned

LangGraph Store can persist arbitrary JSON-like resource metadata, but there is no general required resource envelope covering:

- stable resource ID;
- locator;
- content digest;
- media type;
- extraction profile;
- source revision;
- owner/sensitivity;
- provenance;
- retention;
- chunk identity.

Therefore LangGraph can carry such records but does not itself solve ACL/Vera's resource model.

---

## 31. Recovery state is not authority state

### Observed behavior

Checkpoints persist enough state to resume graph execution and interrupts.

`Runtime.ServerInfo.user` can carry authenticated server user information, but checkpoint/thread identity is separate.

### Combined evidence

- #8579: ambiguous scalar resume can be routed incorrectly.
- #8836: targetless resume map can silently no-op.
- #8837: consumed resume can remain durably eligible and answer a later interrupt.

### Architectural lesson

A recoverable interactive workflow needs separate durable records for:

- request identity;
- authorized principal;
- requested operation/action;
- approval payload;
- approval policy/version;
- status: pending/accepted/rejected/expired/consumed;
- consumption/effect settlement.

Knowledge of an old approval is not current approval authority.

---

## 32. Context construction must select from multiple state planes

LangGraph makes several state sources available to node/model code:

- current graph channels;
- checkpoint-restored history;
- long-term Store;
- runtime context;
- current task metadata;
- parent/subgraph state;
- application-supplied prompts/messages.

A general context builder still must decide:

- which knowledge revision is eligible;
- current versus historical intent;
- trust and provenance;
- principal/purpose/sensitivity filters;
- whether Store should be read fresh or pinned to replay revision;
- semantic/structured retrieval composition;
- token budget;
- whether pending/unsettled state should be visible;
- whether content is data versus policy.

LangGraph provides mechanisms for accessing these planes, not the full ACL/Vera context-governance contract.

---

## 33. Evaluation against the 26 campaign questions

### Q1 — Stable identity

**Evidence:** strong for execution identity: thread, run, checkpoint, task, interrupt, namespace. Store uses namespace+key for application records.

**Lesson:** do not reuse execution identities as semantic entity/assertion/resource identities.

**Confidence:** high.

### Q2 — Identity vs namespace

**Evidence:** strong separation among thread ID, Store namespace, runtime user context and authenticated `ServerInfo.user`.

**Lesson:** namespace is routing/storage scope, not principal.

**Confidence:** high.

### Q3 — Provenance

**Evidence:** checkpoint source, parent lineage, run ID, task writes and Store timestamps provide useful operational provenance.

**Gap:** no general per-claim source/evidence/derivation envelope in Store.

**Confidence:** high.

### Q4 — Epistemic state

**Evidence:** not structurally modeled in general Store records.

**Lesson:** application-defined JSON cannot substitute for required epistemic classes without governance.

**Confidence:** high.

### Q5 — Temporal truth

**Evidence:** record/checkpoint timestamps and TTL exist.

**Gap:** no required world-valid time. #8826 shows time representation itself can lose future semantics.

**Confidence:** high.

### Q6 — Conflict/supersession

**Evidence:** execution history/forks exist; Store overwrites by key.

**Gap:** no general fact-conflict/supersession semantics.

**Confidence:** high.

### Q7 — Relationships

**Evidence:** execution edges, checkpoint parent lineage and storage namespaces exist.

**Gap:** not a general typed world-relationship truth model.

**Confidence:** high.

### Q8 — Permissions/sensitivity

**Evidence:** authenticated server user is distinct from runtime/store scope.

**Gap:** BaseStore namespace/filter does not itself enforce principal/purpose/sensitivity policy.

**Confidence:** high.

### Q9 — Actionability

**Evidence:** interrupts/tasks/commands have actionable execution semantics.

**Gap:** Store knowledge has no general actionability/authority class.

**Confidence:** high.

### Q10 — Knowledge vs authority

**Evidence:** strong separation; thread/Store state and server authenticated user/interrupt approval are separate planes. #8579/#8836/#8837 show why exact durable authority state matters.

**Confidence:** high.

### Q11 — Resources

**Evidence:** Store can persist arbitrary resource metadata.

**Gap:** no canonical resource envelope/version/digest/provenance contract.

**Confidence:** high.

### Q12 — Canonical vs derived

**Evidence:** Store records versus optional semantic index; checkpoint snapshot versus pending writes and Delta reconstruction.

**Lesson:** derived search/index/checkpoint representations need explicit lifecycle/profile identity.

**Confidence:** high.

### Q13 — Structured retrieval

**Evidence:** Store filters and namespace prefixes.

**Caution:** #8829/#8831 demonstrate backend/failure/order differences.

**Confidence:** high.

### Q14 — Relationship retrieval

**Evidence:** no general world-relationship retrieval; execution/checkpoint hierarchy is different semantics.

**Confidence:** high.

### Q15 — Full-text retrieval

**Evidence:** BaseStore does not define a universal lexical/full-text contract comparable to semantic query; backend/application-specific composition remains external.

**Confidence:** medium-high.

### Q16 — Semantic retrieval

**Evidence:** optional embedding search over configured JSON paths.

**Lesson:** embedding profile and score are derived relevance mechanisms, not truth.

**Confidence:** high.

### Q17 — Composite retrieval

**Evidence:** applications can combine Store filters/semantic query and graph state, but there is no universal ACL/Vera candidate-introduction/fusion contract.

**Confidence:** medium-high.

### Q18 — Context construction

**Evidence:** graph state, Store, runtime context, messages and task metadata are distinct sources.

**Lesson:** a separate context layer is still required. #8835 shows projection code must not mutate canonical data by alias.

**Confidence:** high.

### Q19 — Poisoning/injection

**Evidence:** long-term Store content can be surfaced to model context; tool descriptions can influence tool choice.

**Lesson:** persistent/retrieved content remains untrusted; prompt channel does not grant authority.

**Confidence:** high.

### Q20 — Concurrency

**Evidence:** pending-write/checkpoint race #8039, backend retry semantics #8833, parallel interrupts #8579, stale writer deletion #7206.

**Lesson:** concurrency semantics are part of storage/recovery contract.

**Confidence:** high.

### Q21 — Derived integrity

**Evidence:** semantic index #8822; Delta live/replay divergence #8821; state hydration #8653.

**Lesson:** derived/reconstructed state requires identity, settlement and equivalence checks.

**Confidence:** high.

### Q22 — Deletion/retention

**Evidence:** checkpoint delete/prune APIs, Delta dependency warnings, #8531, #7206, Store TTL.

**Lesson:** deletion and retention require dependency closure and generation fencing; TTL is not privacy erasure.

**Confidence:** high.

### Q23 — Schema evolution

**Evidence:** checkpoint format version, Delta beta contract, serializer behavior, topology-dependent replay.

**Lesson:** semantic/runtime migration is broader than serialized shape compatibility.

**Confidence:** high.

### Q24 — Recovery

**Evidence:** checkpoint/pending-write replay, time travel, durability modes, interrupts and concrete crash/replay issues.

**Lesson:** graph recovery does not establish effect exactly-once or complete input reproducibility.

**Confidence:** high.

### Q25 — Unknown/negative knowledge

**Evidence:** no general structural epistemic taxonomy. Backend filter misuse can even collapse unsupported query into empty/no-match (#8829), making absence particularly unsafe as “false.”

**Confidence:** high.

### Q26 — Scope of truth

**Evidence:** namespace/thread/context scope exists operationally.

**Gap:** arbitrary location/scope does not provide structured semantic applicability for version/environment/person/role/time with epistemic meaning.

**Confidence:** high.

---

## 34. Positive mechanisms worth carrying forward

Without selecting LangGraph, KA-6 identifies these useful mechanisms:

1. Separate checkpointer and long-term Store planes.
2. Explicit checkpoint lineage and source metadata.
3. Separate checkpoint snapshots and task-level pending writes.
4. Explicit execution IDs: run/checkpoint/task/thread/attempt.
5. Stable interrupt IDs.
6. Explicit durability modes.
7. Structured task/checkpoint event streams.
8. Explicit subgraph checkpoint inheritance/isolation choice.
9. Explicit retry/timeout runtime policy.
10. DeltaChannel's documented reconstruction dependency model.
11. Prune/copy/delete warnings that expose dependency closure rather than pretending all checkpoints are self-contained.
12. Separate authenticated server-user field from arbitrary storage scope.

---

## 35. Failure/anti-pattern inventory from KA-6

### Existing-family recurrence

- Namespace/thread strings are not principals.
- Backend semantics cannot be inferred from one abstract interface.
- Project/package version is insufficient profile identity.
- Successful state/checkpoint operations do not prove complete transition/effect settlement.
- Persistent memory can influence replay while its revision is absent from replay identity.
- Retrieved content does not become policy/authority.
- Deletion needs multi-plane/dependency/fencing semantics.
- Historical approval state must not regain actionability.

### New materially distinct failure patterns

- **KA-F-039:** read-only retrieval/projection aliases canonical memory and mutates it implicitly.
- **KA-F-040:** serialization preserves apparent value equality while losing behavior-bearing semantics.
- **KA-F-041:** live transition and replay reconstruction implement different state semantics.
- **KA-F-042:** authority-bearing response matches no current request but silently no-ops rather than failing closed.

---

## 36. Cumulative invariant recurrence proposed by KA-6

### Reinforced existing candidates

**KA-I-033** moves to reinforced.

Letta supplied direct persistent-memory/reproducibility evidence. LangGraph independently separates long-term Store from checkpoint identity, so a deterministic replay that depends on Store knowledge requires either a pinned revision/read set or an explicit fresh-read/non-deterministic contract.

### New candidates

**KA-I-038** — canonical knowledge reads must not mutate canonical state by incidental aliasing.

**KA-I-039** — persistence round-trip fidelity includes behavior-bearing semantic metadata, not only value equality.

**KA-I-040** — live and replay transition semantics must be behaviorally equivalent for the same persisted evidence.

### Existing reinforced families receiving additional evidence

KA-6 adds independent evidence to:

- KA-I-003 namespace vs principal;
- KA-I-008 record time vs world-valid time;
- KA-I-010 rank vs truth;
- KA-I-011 derived state lifecycle/profile;
- KA-I-012 backend qualification;
- KA-I-014 principal/purpose gating;
- KA-I-015 persistent memory remains content;
- KA-I-016 multi-plane delete/forget;
- KA-I-017 migration/re-derivation;
- KA-I-018 realized capability identity;
- KA-I-019 end-to-end verification;
- KA-I-020 knowledge vs authority;
- KA-I-021 unknown/negative/conflict semantics;
- KA-I-023 transformation provenance;
- KA-I-024 context construction;
- KA-I-025 epistemic basis separation;
- KA-I-028 settlement state;
- KA-I-029 episode vs persistent domain;
- KA-I-036 source/derived/presentation identity.

---

## 37. Cumulative failure recurrence proposed by KA-6

### Status changes

**KA-F-031** moves from observed to reinforced.

- Letta: persistent memory affects reproducible task execution but is omitted from declared task identity.
- LangGraph: long-term Store is explicitly separate from checkpoint/replay identity, so replay can depend on an unpinned persistent knowledge plane.

**KA-F-038** moves from observed to reinforced.

- Mastra: replayed historical approval/suspension could regain actionability.
- LangGraph #8837: consumed resume input remains in persisted pending writes and can answer a later interrupt.

### Additional recurrence

- KA-F-001 — arbitrary scope identifiers vs authenticated user.
- KA-F-012 — retention/deletion dependency closure and stale writers.
- KA-F-013 — current production-wiring/backend profile differences.
- KA-F-015 — Store filtering/ordering semantics vary by backend.
- KA-F-016 — semantic score remains relevance only.
- KA-F-017 — retrieved Store memory/tool descriptions remain untrusted content.
- KA-F-019 — partial step/pending-write/checkpoint settlement.
- KA-F-020 — checkpoint/Store provenance does not supply full derivation provenance for semantic knowledge.
- KA-F-026 — delete/TTL/prune are not synonymous with privacy erasure.
- KA-F-032 — live/runtime representations can differ from persisted/reconstructed state, although KA-F-041 captures the stronger transition-algebra form separately.

---

## 38. Assertion-centric hypothesis reassessment

The campaign has been considering whether a general substrate should be primarily assertion-centric.

LangGraph does not directly answer that question, because its Store is intentionally generic and its graph/checkpoint model is execution-centric.

However KA-6 provides indirect support for keeping **semantic assertions separate from execution snapshots**:

- checkpoint lineage is excellent for “what execution state existed?”;
- Store records are useful for arbitrary durable application data;
- neither automatically expresses “what proposition is believed, on what evidence, under what scope/time/confidence?”

Therefore an assertion-centric canonical layer could coexist with LangGraph-like execution state, but the execution/checkpoint graph should not itself become the canonical truth model.

No final primitive/schema decision is made here.

---

## 39. Hostile scenarios derived from KA-6

These should become later acceptance/regression fixtures where relevant:

1. **Read-only context mutation:** retrieve nested canonical record, redact locally, verify canonical state is unchanged.
2. **Semantic round-trip:** serialize/restore timezone-aware deadline across DST and verify future behavior, not just equality.
3. **Live/replay equivalence:** persist one ordered concurrent-write batch and assert live state equals reconstructed state.
4. **Store-revision replay:** checkpoint a task, mutate long-term knowledge, replay and assert configured fresh-vs-pinned semantics.
5. **Zero-match approval:** send approval for stale/unknown request ID; must fail closed explicitly.
6. **Consumed approval:** consume approval A, create approval B, resume with no input; A must never answer B.
7. **Parallel approvals:** two pending requests; scalar answer must fail closed.
8. **Partial route settlement:** state write succeeds, route fails; recovery must retain unresolved transition rather than report completion.
9. **Checkpoint/pending-write crash:** force both persistence interleavings; external effect remains idempotent/ledger-governed.
10. **Backend filter parity:** same supported/unsupported filter request across memory/SQLite/Postgres must have a defined contract.
11. **Backend ordering parity:** pagination requires explicit order and stable tie-breaker.
12. **Retry-write parity:** special and ordinary retry writes must preserve identical semantics across backends.
13. **Subgraph fork/replay:** selected child recovery point remains reachable after parent fork.
14. **Untracked resource replay:** task must reacquire or refuse replay when runtime-only input is absent.
15. **Prune dependency closure:** retained recovery point remains reconstructable after physical retention cleanup.
16. **Delete vs stale writer:** stale pre-delete writer cannot resurrect retired generation.
17. **Production wiring parity:** attached and runtime-injected persistence paths hydrate the same canonical state.
18. **Index one-to-many lineage:** identical derived content attached to multiple records yields one computation but multiple valid derived links.

---

## 40. Non-conclusions

KA-6 does **not** conclude that:

- LangGraph is unsafe or unsuitable for production;
- every open issue affects every deployment;
- LangGraph should be adopted by ACL/Vera;
- LangGraph should be rejected by ACL/Vera;
- checkpoint storage should be the knowledge database;
- Store should be the canonical knowledge database;
- DeltaChannel should or should not be used;
- exactly-once execution is generally impossible;
- all Store backends are semantically incompatible;
- every replay should pin long-term Store state;
- LangGraph Server lacks authorization;
- a graph database should be selected;
- the final knowledge schema should be assertion-centric.

The evidence is used to extract architecture constraints, not to make a framework-selection decision.

---

## 41. Confidence summary

**High confidence:**

- checkpointer versus Store separation;
- execution identity/lineage structure;
- thread/namespace versus authenticated-user separation;
- Store record model and epistemic gaps;
- semantic score is relevance, not truth;
- backend semantics require qualification;
- read-alias failure mechanism in current InMemoryStore;
- datetime serializer behavior in current source;
- Delta live/replay implementation difference in current source;
- checkpoint/prune dependency warnings;
- replay reexecutes node logic;
- pending-write/checkpoint/effect separation;
- current issue states cited above.

**Medium-high confidence:**

- deterministic replay should include a Store revision when Store reads materially influence execution. This follows directly from architecture separation, but whether to pin or read fresh is an application contract choice.

**Deliberately not concluded:**

- production frequency of every open issue;
- behavior of untested third-party saver/store implementations;
- maintainer acceptance of proposed issue fixes;
- final ACL/Vera storage/runtime choice.

---

## 42. Sources reviewed

### Current primary project material

- https://github.com/langchain-ai/langgraph
- https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/langgraph/pyproject.toml
- https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/langgraph/langgraph/types.py
- https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/langgraph/langgraph/runtime.py
- https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/langgraph/langgraph/channels/delta.py
- https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/checkpoint/langgraph/checkpoint/base/__init__.py
- https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/checkpoint/langgraph/checkpoint/serde/jsonplus.py
- https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/checkpoint/langgraph/store/base/__init__.py
- https://github.com/langchain-ai/langgraph/blob/81bf17b23123e4ef8b9d5f49fa09a0122fc2edd1/libs/checkpoint/langgraph/store/memory/__init__.py
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://docs.langchain.com/oss/python/langgraph/add-memory

### Current/recent failure evidence

- https://github.com/langchain-ai/langgraph/issues/8039
- https://github.com/langchain-ai/langgraph/issues/8458
- https://github.com/langchain-ai/langgraph/issues/8579
- https://github.com/langchain-ai/langgraph/issues/8653
- https://github.com/langchain-ai/langgraph/issues/8582
- https://github.com/langchain-ai/langgraph/issues/8531
- https://github.com/langchain-ai/langgraph/issues/7206
- https://github.com/langchain-ai/langgraph/issues/8837
- https://github.com/langchain-ai/langgraph/issues/8836
- https://github.com/langchain-ai/langgraph/issues/8835
- https://github.com/langchain-ai/langgraph/issues/8834
- https://github.com/langchain-ai/langgraph/issues/8833
- https://github.com/langchain-ai/langgraph/issues/8831
- https://github.com/langchain-ai/langgraph/issues/8829
- https://github.com/langchain-ai/langgraph/issues/8826
- https://github.com/langchain-ai/langgraph/issues/8822
- https://github.com/langchain-ai/langgraph/issues/8821
- https://github.com/langchain-ai/langgraph/issues/8818

---

## 43. Stop condition

KA-6 stops because:

- current upstream source/package identity has been verified;
- the historical LangGraph report has been re-read rather than restarted;
- the current checkpoint and long-term Store models have been analyzed separately;
- all 26 campaign questions have been evaluated;
- post-historical issue evidence materially relevant to knowledge/replay semantics has been inspected;
- recurrence has been mapped to existing invariant/failure IDs before creating new ones;
- three new invariant concepts and four new failure patterns remain genuinely distinct after deduplication;
- additional issue discovery is now more likely to repeat already-supported backend/replay/concurrency themes than to change the architecture conclusions.

**KA-6 completes here. Google ADK is not researched in this task.**
