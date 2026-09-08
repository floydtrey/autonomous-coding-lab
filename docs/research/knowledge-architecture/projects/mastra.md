# KA-5 — Mastra Knowledge-Architecture Revisit

**Campaign:** Knowledge Architecture Evidence Campaign  
**Task:** KA-5 only  
**Project:** Mastra  
**Upstream repository:** `mastra-ai/mastra`  
**Current upstream revision inspected:** `d7bd6f7a91daf528f34d628faede4a916421b0dd`  
**Current core package observed:** `@mastra/core@1.65.0-alpha.9`  
**Historical Task 31 revision:** `685616780ea68e55c23c5980c17d5eee9a8f0aa9`  
**ACL starting checkpoint:** `44a7de7b87ae66fa78431de5085701f9f937f343`  
**Research date:** 2026-09-08

## 1. Task boundary

This is a bounded knowledge-architecture revisit of Mastra. It is not a second general product survey and it does not replace the historical Task 31 report.

The historical report already covered Mastra's agent/workflow/durable-execution surface, tool approval, A2A boundary, memory layers, workspaces, sandbox adapters, storage and observability. KA-5 therefore asks a narrower set of questions:

- What is actually canonical versus derived in Mastra's current memory/runtime model?
- Which identifiers are semantic identity, source identity, routing scope, run identity or merely lookup keys?
- How much provenance survives from raw messages into observations, reflections, semantic recall and model-visible context?
- What temporal semantics exist, and which temporal semantics do not exist?
- How are current, historical, buffered and pending memory states distinguished?
- What does Mastra prove about context construction, concurrency, settlement, deletion, retention and recovery?
- Which behaviors are backend/profile dependent?
- Which current failures or recent fixes should become ACL/Vera design tests?
- Which campaign invariants receive independent support, and which proposed invariants remain unsupported?

This task does **not** select Mastra as ACL/Vera's knowledge store, final ontology, database, retrieval engine, memory framework or execution framework.

## 2. Evidence discipline

For each important conclusion this report distinguishes:

- **Observed behavior** — current source/docs or a concrete current/recent issue/PR.
- **Failure evidence** — a reproduced/reportable defect or an explicit limitation.
- **Architectural lesson** — the narrow implication for ACL/Vera.
- **Confidence** — high, medium or low based on evidence quality.
- **Non-conclusion** — what the evidence does not establish.

Current source was preferred over package-name assumptions. Recent fixes were checked against the pinned current revision so fixed defects are not mislabeled as current-main defects.

## 3. Upstream delta since historical Task 31

The historical Task 31 report was based on `685616780ea68e55c23c5980c17d5eee9a8f0aa9`, with core `1.65.0-alpha.8`. KA-5 reverified `main` at `d7bd6f7a91daf528f34d628faede4a916421b0dd`, core `1.65.0-alpha.9`.

The upstream delta is small in wall-clock time but contains one important architecture signal: durable-agent recovery has been moving toward explicit lease/fencing semantics, while parts of the public documentation still retain the older warning that multi-replica recovery lacks a distributed lease/lock. Current source contains a `RecoveryLease` abstraction, TTL/renewal/loss handling, and Redis/Valkey lease providers. Recent merged PR #22960 describes the dedicated durable-agent recovery path as including leasing, thread-runtime registration and fencing. However, the current durable-agent guide still contains an older paragraph stating that Mastra does not provide a distributed lease/lock and replicas can race.

**Architectural lesson:** capability identity must bind exact source revision, selected PubSub/lease provider, recovery path and configuration. Documentation or package version alone is not sufficient.

**Confidence:** high that the code/docs differ; medium on the exact cross-provider guarantees because KA-5 did not exhaustively certify every PubSub backend.

**Non-conclusion:** this report does not claim Mastra now provides universal distributed fencing across every deployment profile.

## 4. Knowledge and runtime planes

Current Mastra exposes multiple planes that can contain related information without being the same state:

1. **Raw persisted messages** — user, assistant and tool-result records.
2. **Thread records** — conversation identity, owner resource, title/metadata.
3. **Resource records** — longer-lived resource identity and resource-scoped working memory.
4. **Working memory** — persistent structured or Markdown user/project state.
5. **Semantic-recall vectors** — derived embeddings/chunks with message/thread/resource metadata.
6. **Observational-memory active observations** — model-derived compressed current memory.
7. **Observational-memory buffered observation chunks** — derived but not yet active.
8. **Observational-memory reflection generations** — historical/current generations of compressed memory.
9. **Extracted values** — model-derived structured fields produced by observation/reflection.
10. **Model-visible context** — assembled system/conversation messages for one call.
11. **Run-state cached context inputs** — values pinned/loaded within a run.
12. **Durable workflow snapshots** — continuation/recovery state for execution.
13. **Stream/event cache** — replayable presentation/event history.
14. **Run status / registries / live runtime state** — execution coordination.
15. **Approval/suspension state** — authority-relevant interactive state.
16. **External effects** — tool/provider/world changes, outside the memory substrate.

The architecture should not collapse any of these into a single `memory` or `state` object.

## 5. Stable identity: resource, thread, message, observation and run

### Observed behavior

Mastra's memory docs explicitly define:

- `resource` as a stable identifier for the user or entity;
- `thread` as an identifier isolating a conversation/session;
- a thread has an owner `resourceId` that cannot be changed after creation;
- message records have their own IDs;
- Observational Memory records have their own IDs, scope, thread/resource identity and generation count;
- buffered observation chunks have their own IDs and source `messageIds`;
- durable executions use a separate `runId`.

Subagent delegation creates a fresh thread per delegation while deriving a stable subagent resource ID from the parent resource and agent name.

### Architectural lesson

Mastra independently supports the distinction between persistent-domain identity and transient episode/run identity. `resourceId`, `threadId`, `messageId`, OM record ID, buffered-chunk ID and `runId` answer different questions.

### Confidence

High.

### Non-conclusion

None of these IDs is, by itself, a canonical real-world person/device/project identity. They are application/runtime identifiers.

## 6. Identity versus namespace versus principal

### Observed behavior

Memory sharing is intentionally controlled by identifiers:

- same `resourceId` can share resource-scoped working memory, observations and semantic embeddings;
- same `resourceId` + `threadId` can share message history;
- subagent delegation derives separate resource/thread identifiers;
- a thread's resource owner is stable once created.

But Mastra separately implements execution authorization/FGA, tool approval, A2A authorization concerns and request context.

### Failure evidence

Open issue #19911 requests a first-class A2A pre-execution gate that receives the authenticated caller and can authorize who may resume/reject a task. That requirement exists precisely because A2A task/message identity is not sufficient authorization.

### Architectural lesson

A memory scope key can be useful for routing and ownership metadata without being an authenticated principal. ACL/Vera must never infer read, write or execute authority merely from possession of a `resourceId`, `threadId`, `taskId` or similar key.

### Confidence

High.

## 7. Raw evidence versus derived memory

### Observed behavior

Mastra's current OM model is explicitly derivative:

- raw messages are stored;
- the Observer compresses older message history into observations;
- reflections later rewrite the active observation log into a new compressed generation;
- only unobserved recent messages remain in normal model context once observations are active;
- optional OM retrieval mode keeps raw messages addressable behind the compressed observation groups.

Official Mastra material describes OM as compressing raw conversation history into dense observation logs rather than repeatedly injecting raw history.

### Positive mechanism

With OM retrieval enabled, observation groups carry a `range` such as `startId:endId` pointing back to source raw messages. The recall tool can page through the underlying messages. Buffered observation chunks additionally record the exact `messageIds` they observed.

### Architectural lesson

This is strong independent evidence for preserving raw evidence separately from derived semantic memory. The compact memory can be the normal context representation without becoming the only evidence representation.

### Confidence

High.

## 8. Provenance: source addressability is strong, transformation provenance is incomplete

### Observed behavior

Mastra provides useful source-lineage signals:

- observation-group source ranges;
- buffered chunk `messageIds`;
- OM record `originType` (`initial` or `reflection`);
- `generationCount`;
- `createdAt`, `updatedAt`, `lastObservedAt`;
- stored OM configuration;
- observed timezone;
- token counts and lifecycle flags;
- extractor success/failure results.

### Limitation

The ordinary current OM record is still a model-produced prose log plus optional extracted values. It does not structurally attach to each remembered claim all of:

- exact source message/evidence IDs;
- observer/reflector model build/profile for that individual claim;
- exact prompt version;
- parser/extractor version;
- verification/adjudication state;
- confidence/trust class;
- applicability scope;
- supersession relationship.

The source ranges are excellent coarse provenance, but they are not a complete epistemic derivation record.

### Architectural lesson

`Source -> Observation group -> Reflection generation` is useful lineage, but ACL/Vera still needs claim-level derivation provenance for material facts/decisions.

### Confidence

High on what current schemas contain; medium on absence outside the inspected ordinary OM paths.

## 9. Epistemic state remains prose-level

### Observed behavior

The current `ObservationalMemoryRecord` has operational state, scope, generation, source-message tracking, token tracking and configuration. It does not expose a general per-fact type system for:

- explicit user statement;
- inferred preference;
- model hypothesis;
- verified observation;
- disputed claim;
- known false;
- unknown;
- searched-not-established;
- historical fact no longer current;
- confidence/trust class.

Working-memory/extractor schemas can impose application-specific structure, but they do not create a universal epistemic model.

### Architectural lesson

Mastra is strong evidence for memory lifecycle mechanics, not a complete truth substrate. ACL/Vera should not encode epistemic state only inside free-form observation prose.

### Confidence

High for the inspected core memory record model.

## 10. Temporal semantics: useful visibility time, not general world-valid time

### Observed behavior

Mastra records message timestamps, OM record creation/update time, `lastObservedAt`, buffer timestamps and reflection generations. OM can insert temporal-gap markers after meaningful conversation pauses.

Current `getObservationsAsOf(activeObservations, asOf)` reconstructs the portion of an active observation string that would have been visible by a requested time. Observation boundaries carry the source-message `lastObservedAt` timestamp.

### Architectural lesson

This is useful **knowledge-availability / derivation time**. It is not the same as world-valid time of every remembered proposition.

For example, an observation generated on September 8 may say an event happened on September 1, or may summarize a state valid only during a past interval. The generation timestamp does not encode that semantic validity interval.

### Confidence

High.

### Non-conclusion

KA-5 does not claim Mastra has bitemporal truth semantics for arbitrary facts.

## 11. Current, historical, buffered and pending memory are separate

### Observed behavior

OM distinguishes:

- active observations;
- buffered observation chunks waiting for activation;
- buffered reflection;
- current generation;
- prior generations accessible through history;
- observed message IDs;
- unobserved messages;
- observation/reflection in-progress flags.

`swapBufferedToActive()` is documented as an atomic operation that moves selected buffered observations into active memory and moves their message IDs into the observed set while retaining unactivated remainder.

Reflection creates a new generation with incremented `generationCount`; current docs explain that each reflection rewrites the current observation log while older generations remain history.

### Architectural lesson

`derived`, `settled/active`, `historical`, `pending` and `in-progress` are materially different states. A background model output should not become active canonical knowledge merely because it exists in a buffer.

This independently reinforces KA-I-032: consolidation input should be considered consumed only when the derived mutation integrates/activates, with stable source identity for retry protection.

### Confidence

High.

## 12. Reflection is replacement of a current projection, not deletion of evidence

### Observed behavior

Current docs say reflections do not accumulate as a second endless layer. The Reflector rewrites the active observation log; its output becomes the new current log, while historical generations are retained through the OM history mechanism.

### Architectural lesson

This is a useful positive shape for bounded current memory:

`raw messages -> observations -> reflected current projection`, with historical generations retained separately.

However, the semantic transformation is still model-driven. Generation history proves how the memory projection changed, not that the Reflector's semantic decisions were correct.

### Confidence

High.

## 13. Source, derivative and presentation identities remain distinct

### Observed behavior

Mastra's OM model gives buffered observation chunks unique IDs while separately carrying source message IDs. Current retrieval mode exposes a source message range rather than pretending the observation group is the source message itself.

The current live-stream fix #23271 independently demonstrates a related presentation problem: provider content-block IDs restart across steps. The live engine previously retained those IDs across the whole run and appended later-step reasoning/text into an earlier part, while the persisted builder produced separate spans. Current `main` fixes the live projection by ending the span on `text-end` / `reasoning-end` so live and reloaded views have matching part order.

### Architectural lesson

A source event/message, a derived memory record and a UI/live projection require separate identities and lifecycle boundaries. Reusing a local provider block ID outside its valid scope corrupts presentation evidence even when the underlying persisted run is sound.

Mastra therefore independently reinforces KA-I-036.

### Confidence

High for the current fix and OM chunk/source structure.

## 14. Scope of truth versus scope of storage

### Observed behavior

Mastra supports thread-scoped and resource-scoped OM. Resource scope merges observations across threads for one resource.

Current docs explicitly mark resource scope experimental and warn that one thread may continue work another thread started but had not finished, because each thread becomes a perspective on all threads for the resource. Unobserved messages across all threads can be processed together.

### Architectural lesson

A fact's **storage/retrieval scope** is not automatically its semantic applicability scope. User-level memory may be shared while task state, temporary hypotheses, local environment state or one project/thread's unfinished work must remain episode/task scoped.

This independently reinforces the need to separate persistent knowledge-domain scope from transient episode/task identity.

### Confidence

High.

## 15. Multi-agent memory sharing is explicit but not an authorization system

### Observed behavior

Delegated subagents get a fresh thread and deterministic subagent resource. Direct agents can intentionally share memory by using matching resource/thread identifiers. Parent context can be forwarded to a delegated subagent while only the delegation prompt and response are saved to the subagent thread.

### Architectural lesson

Mastra provides a good example of making sharing/episode boundaries explicit. But matching identifiers remains a sharing convention and routing mechanism; ACL/Vera still needs authenticated principals, purpose and explicit read/write policy above it.

### Confidence

High.

## 16. Context construction is a distinct subsystem

### Observed behavior

Current `Memory.getContext()` explicitly assembles model input from separate planes:

- OM observation system messages;
- other-thread context for resource-scoped OM;
- a continuation reminder;
- working-memory system text unless state-signal mode is used;
- unobserved messages after the OM boundary, or recent history when OM is inactive.

Semantic recall can appear as ordinary conversation messages for same-thread matches and as a system message for cross-thread matches. One-call context messages are not persisted.

`runState.load()` can pin/cache several context components during a run.

### Architectural lesson

Retrieval is not context construction. The context builder decides which planes are visible, which channel they occupy, what current boundary applies and how they are ordered.

ACL/Vera's context builder must take trust, permissions, freshness, revision, scope, actionability and token budget explicitly.

### Confidence

High.

## 17. Prompt channel does not upgrade trust

### Observed behavior

Mastra intentionally injects working memory and OM observations into system messages in some profiles; other memory appears as ordinary conversation messages or state signals.

### Architectural lesson

Model-visible placement is a prompting mechanism, not an epistemic or authorization mechanism. A user-derived observation injected as a system message remains user-derived/model-derived knowledge unless separately verified.

This independently reinforces the campaign's persistent-memory poisoning/instruction-boundary concern.

### Confidence

High on placement; medium on exploitability because KA-5 did not attempt an injection exploit.

## 18. Working memory and extractors are structured projections, not canonical truth

### Observed behavior

Working memory can be Markdown or schema-backed structured data. OM can run extractors for built-in or custom values such as current task, suggested response, thread title or a user profile. Schema-backed extractors run structured-output requests; extractor failures are reported independently and do not discard successful extractions.

An Observer can be configured to manage working memory automatically.

### Architectural lesson

Structured extraction improves machine usability but still produces a derived claim/projection. Schema validation proves output shape, not truth. Extractor name/schema/model/prompt/source range should be derivation provenance when the value influences important automation.

### Confidence

High.

## 19. Semantic recall is derived retrieval, not confidence

### Observed behavior

When semantic recall is enabled, current `saveMessages()` persists the messages and separately derives embeddings. Vector metadata includes message, thread and resource identity, role, source text and creation time. The embedding cache is keyed by a content hash.

Current source contains an instructive implementation comment: the embedding cache uses a 64-bit hash because a prior 32-bit hash could collide at realistic entry counts and return another message's cached embedding.

### Architectural lesson

Semantic vectors are derived lookup state. Their identity/hash/model/profile is part of retrieval behavior. A similarity score or cache hit is not epistemic confidence.

### Confidence

High.

## 20. Composite retrieval/context is a contract, even without one fusion score

Mastra's memory stack composes several candidate/context sources:

- recent message history;
- semantic recall;
- working memory;
- OM current observations;
- raw-message recall behind observation ranges;
- cross-thread resource context;
- one-call caller context.

The framework does not reduce these to one universal truth-ranking score. Placement and retrieval rules differ by plane.

### Architectural lesson

ACL/Vera's composite retrieval specification should state which planes may introduce evidence, how hard eligibility is enforced, how current/history intent works and how model-visible context is assembled. “Memory enabled” or “hybrid search” is not a sufficient retrieval contract.

### Confidence

High.

## 21. Local OM versus gateway OM is a realized-profile boundary

### Observed behavior

Current `ObservationalMemoryProcessor` detects a Mastra gateway model and skips local OM processing because the gateway handles OM server-side. The source explicitly says running both would double-process messages and duplicate history. Detection is based on the model rather than inherited request context to avoid leaking the decision into child-agent delegation.

### Architectural lesson

The same high-level feature name, “Observational Memory,” can mean local processing or remote gateway processing. Derivation provenance and deployment identity must include that profile.

### Confidence

High.

## 22. Backend capability flags are semantic, not cosmetic

### Observed behavior

The memory storage abstraction exposes capability distinctions such as `supportsObservationalMemory` and `supportsPartialThreadUpdate`. Some default methods throw because the adapter does not implement resource-scoped listing, message deletion, resource working memory, thread cloning or OM.

Current docs enumerate a subset of adapters supported by OM; a current issue (#23309) requests missing MSSQL OM support.

### Architectural lesson

A common interface does not imply equal semantics. ACL/Vera must qualify backend support for each invariant it depends on and fail closed if a required lifecycle/filter/transaction feature is unavailable.

### Confidence

High.

## 23. Legacy compatibility can preserve old concurrency hazards

### Observed behavior

Current `MemoryStorage.patchThread()` handles legacy adapters that predate partial thread updates by reading the current title/metadata and backfilling omitted fields before calling the legacy update method. Its source explicitly notes that this restores legacy behavior **including its title-clobbering race**.

Merged PR #21041 documents the original defect: metadata-only writers had to read and echo a title; if title generation completed between that read and write, the fresh title was overwritten by stale data.

### Architectural lesson

Backward-compatible adapters can preserve weaker consistency semantics. “Compatible” does not mean “equally safe under concurrency.”

This independently reinforces the read-modify-write concurrency failure family KA-F-023.

### Confidence

High.

## 24. Thread creation and OM generation still provide concurrency failure evidence

### Current issue evidence

- #20148 remains open and describes non-atomic thread creation/read-then-create behavior needing an insert-if-absent/atomic uniqueness path.
- #22188 remains open and describes duplicate generation-zero OM rows under concurrent PostgreSQL creation.
- #19740 remains open and describes reusing an already-ended OM turn in multi-step/subagent loops.

### Architectural lesson

Logical uniqueness and lifecycle flags require storage-level atomicity/fencing, not merely a pre-read or in-memory guard.

### Confidence

Medium-high: these are current open reports with concrete paths, but KA-5 did not independently reproduce each issue locally.

## 25. Buffered-memory activation is a useful atomic integration boundary

### Observed behavior

The storage interface explicitly documents `swapBufferedToActive()` as atomic and describes exactly which state moves together: buffered observations, observed message IDs, remaining buffered content and `lastObservedAt`.

### Architectural lesson

This is a positive reference for background consolidation: derived output can exist in a pending plane, then a single integration transition makes the content and source-consumption markers active together.

It independently reinforces KA-I-032.

### Confidence

High at the contract level; backend-by-backend transaction implementation was not exhaustively certified.

## 26. `settled()` proves quiescence, not successful reconciliation

### Observed behavior

Current `Memory.settled()` documentation says an agent run can return while background memory work continues. The barrier waits for:

- buffered OM observation/reflection work and nested runs;
- vector cleanup started by `deleteThread()` or `deleteMessages()`.

The same reference explicitly states that background work failures do **not** reject the `settled()` promise.

### Architectural lesson

Two states must be separated:

1. **quiesced/joined** — no tracked background work remains in flight;
2. **successfully reconciled** — every intended mutation reached its required settled state, or failures are durably recorded and remediated.

A void drain barrier that absorbs failures is useful for safe shutdown but cannot certify knowledge consistency.

### Confidence

High.

### New failure pattern

KA-5 records this as KA-F-037: treating a background-work join/quiescence barrier that absorbs child failures as proof of successful reconciliation.

## 27. Delete and retention are explicitly multi-plane

### Observed behavior

Mastra exposes primary memory deletion plus separate OM and vector lifecycle operations.

Current MongoDB memory source is unusually explicit:

- age-based retention applies to messages, resources and threads;
- the observational-memory collection is excluded because it has no timestamp anchor to age on;
- `prune()` does not sweep semantic-recall vectors because they live in a separate vector store the memory domain cannot reach;
- vector cleanup is the operator's concern in that retention path.

Separately, ordinary `deleteThread()`/`deleteMessages()` can start vector cleanup asynchronously, which is why `Memory.settled()` exists.

### Architectural lesson

A retention/deletion policy must enumerate every plane: raw messages, working memory, OM current/history, semantic vectors, caches, backups and remote replicas. A primary-store prune is not a complete retention result.

### Confidence

High for current MongoDB source and documented vector-cleanup lifecycle.

## 28. Current removal, historical generation retention and privacy erasure differ

OM exposes a `clearObservationalMemory()` operation documented to remove all OM records/history for a thread/resource, but that is only one plane. Message deletion, resource deletion, semantic vectors, stream caches, workflow snapshots, external logs/backups and provider-held data are separate concerns.

### Architectural lesson

ACL/Vera should model at least:

- remove from current view;
- supersede while retaining history;
- archive/retention expiration;
- privacy erasure request;
- legal/audit retention exception;
- derived/index cleanup;
- backup/replica reconciliation.

### Confidence

High as an architecture distinction; KA-5 did not certify Mastra's end-to-end privacy-erasure behavior.

## 29. Live event projection can disagree with persisted evidence

### Failure/fix evidence

Current head commit #23271 fixes a concrete live/persisted projection mismatch. A live multi-step run could merge later reasoning/text into the first step because provider content-block IDs restarted per response but the live map retained them across the run. The persisted builder already closed spans correctly, so the live UI shape differed from the reloaded persisted shape.

The current fix closes live spans on their end chunks so later reused block IDs open new parts.

### Architectural lesson

A live event projection is not automatically equivalent to persisted evidence. Projection lifecycle/identity must be explicit, and verification should compare live and reload representations where the projection matters.

This independently reinforces KA-F-032.

### Confidence

High for the source/test-level defect and fix. The commit itself notes the full Factory live symptom was not re-verified after the fix.

## 30. Historical replay must not become current action authority

### Failure evidence

Open PR #22767 reports that reconnecting subscribers can replay old approval or tool-suspension events and expose them as actionable after the run has already completed. The proposed fix marks replayed events and checks current durable suspension state before reactivating interactive behavior.

### Architectural lesson

A historical event saying “approval requested” is evidence that a request existed; it is not proof that an approval is currently pending. Actionability must be derived from current authority state, not from presence of historical/replayed content.

### Confidence

Medium-high: the PR contains focused regression tests and a clear current-main failure claim, but it is still open/unmerged.

### New failure pattern

KA-5 records this as KA-F-038: replayed historical approval/suspension events surfaced as currently actionable without validating current durable authority state.

## 31. Knowledge, authority and execution remain separate

Mastra provides independent evidence for the campaign's core separation:

- memory content informs model reasoning;
- execution FGA/authorization is evaluated separately;
- tool approval/suspension is separate durable state;
- A2A pre-execution authorization is a distinct requested boundary;
- tool effects are separate from approval messages and workflow snapshots.

A remembered sentence such as “the user approved deleting old records” cannot safely substitute for the actual current approval state.

## 32. A2A invocation authority and downstream effect authority differ

Open issue #19911 asks for a pre-execution A2A gate that can validate authenticated caller/context before the target Agent starts. Agent-level tool approval occurs after execution begins and therefore cannot supply that boundary.

### Architectural lesson

Authority is layered:

- may this caller invoke/resume this agent/task?
- may the model see this knowledge?
- may this run invoke this tool?
- may this exact tool call/effect execute now?

These should not be compressed into one `approved=true` bit.

## 33. Durable recovery: at-least-once replay remains part of the contract

### Observed behavior

Current durable-agent docs warn that recovery re-runs the agentic loop from the last persisted snapshot, re-issuing LLM calls and re-executing tool calls. Tools therefore need idempotency.

A durable snapshot is a continuation/recovery mechanism, not an effect-settlement ledger.

### Architectural lesson

Knowledge/replay identity must include the persisted state/profile that influenced execution, but external effect settlement still needs stable effect identity and idempotency/fencing outside generic snapshot replay.

### Confidence

High.

## 34. Recovery leasing is now profile-dependent and in transition

### Current source

`durable-agent.ts` defines recovery-lease TTL/renewal/loss behavior and uses a lease-provider abstraction. Redis Streams and Valkey Streams implement atomic lease acquisition. Recent merged PR #22960 says dedicated durable-agent recovery now uses leasing, runtime registration and fencing and prevents generic workflow boot recovery from racing that dedicated path.

### Documentation conflict

The current durable-agent guide also contains an older “multi-instance deployments” warning saying Mastra does not provide a distributed lease/lock and all replicas can race.

### Architectural lesson

Do not turn either sentence into a universal rule. The realized guarantee depends on exact revision, recovery path and backend. The inconsistency itself is evidence for KA-I-018 / KA-F-013.

### Confidence

High that lease machinery exists in current source; medium on universal deployment guarantees.

## 35. Run recovery state and live runtime state are not interchangeable

Current durable source distinguishes serializable persisted model/config entries from live runtime model instances and contains explicit rebinding logic after recovery. Source comments note an inherent limit when explicit IDs are renamed and regenerated UUID identities cannot match persisted IDs.

### Architectural lesson

Serializable replay identity should use stable explicit IDs for behavior-bearing components. Position-based fallback is weaker evidence and should fail closed when ambiguous for authority-sensitive behavior.

### Confidence

High for current source.

## 36. Memory profile belongs in replay identity when reproducibility matters

A Mastra run can differ based on:

- resource/thread scope;
- current OM generation and unobserved-message boundary;
- working-memory contents;
- semantic-recall index/model;
- Observer/Reflector model or token-tier-selected model;
- local versus gateway OM processing;
- memory configuration/read-only/state-signal mode;
- storage/vector backend;
- exact context-construction profile.

Even if two tasks have the same user prompt, these planes can change model-visible context.

### Architectural lesson

This is supporting evidence for KA-I-033, but KA-5 does **not** move it to reinforced because the inspected Mastra material does not provide as clean a deterministic-retry failure case as Letta #3807. It remains a candidate.

## 37. Resource/attachment handling is useful but not a complete resource envelope

Current OM can observe images/files, preserve readable placeholders and forward actual attachments where supported. Message parts can carry filenames, data/URLs, MIME information and token-estimate metadata.

### Limitation

This is not a general canonical resource registry containing every ACL/Vera requirement such as:

- stable logical resource ID independent of location;
- one or more locators;
- observed content digest/version;
- extraction profile;
- source/evidence lineage;
- owner/sensitivity/retention;
- chunk identity;
- replica status.

### Architectural lesson

Mastra can be a consumer of a richer resource layer; its message attachments do not eliminate the need for that layer.

## 38. Typed world relationships are not provided by the ordinary memory model

Resource/thread ownership, message membership, subagent derivation and OM source ranges are operational relationships. They are useful, but they are not a general world-relationship assertion model with governed semantics such as:

- owns;
- located-in;
- member-of;
- depends-on;
- connected-to;
- capable-of;
- governed-by;
- supersedes;
- contradicts.

### Architectural lesson

Do not mistake runtime foreign keys/ownership associations for canonical semantic relationships.

### Confidence

High for the inspected ordinary memory model; no claim is made about every optional Mastra integration.

## 39. Unknown/negative knowledge remains under-modeled

No inspected ordinary Mastra memory record requires a structured distinction among:

- false;
- unknown;
- not checked;
- searched and not established;
- conflicting;
- stale;
- historical but no longer current.

Free-form observations can express those ideas, but downstream code cannot safely rely on consistent prose to enforce them.

### Architectural lesson

Mastra independently supports the campaign conclusion that a general substrate needs explicit epistemic/lifecycle state beyond prose memory.

## 40. Schema evolution is visible and backend-sensitive

Current OM types retain deprecated buffered fields for backward compatibility while introducing structured `bufferedObservationChunks`. Storage abstractions expose feature/capability flags to tolerate older adapters. `patchThread()` contains a compatibility path for adapters lacking partial-update semantics.

### Architectural lesson

Schema compatibility is an explicit runtime concern. Old records/backends do not automatically gain newer semantics merely because the current interface can deserialize or adapt them.

### Confidence

High.

## 41. Model/profile identity is derivation provenance

Current OM can select Observer/Reflector models dynamically based on input token counts. Prompt-cache/provider-change behavior can trigger early activation. Attachment handling and token counting vary with provider/model details. Gateway OM and local OM are different execution profiles.

### Architectural lesson

A durable derived memory record that can materially affect future reasoning should identify at least the behavior-bearing derivation profile: model/provider, prompt/extractor configuration, source range/generation, relevant tokenizer/counting profile and exact implementation/build where reproducibility matters.

## 42. Poisoning/injection boundary

Persistent user/model-derived memory is repeatedly fed back to the model and may occupy a system-message channel. That creates a durable influence path.

Mastra's separate execution authorization/tool-approval machinery is a positive boundary, but the ordinary memory record itself does not prove a remembered instruction is trusted policy.

### Architectural lesson

Persistent memory must remain untrusted content by default. ACL/Vera should represent source trust and authority-use eligibility separately and should never let model-visible memory directly expand tool permissions.

### Confidence

High on the boundary principle; no exploit was attempted.

## 43. Positive mechanisms worth carrying forward

Mastra offers several concrete patterns that are useful independent of whether Mastra is selected later:

1. **Raw-message retention behind compact observations.**
2. **Observation-group source ranges** for coarse source addressability.
3. **Unique buffered-chunk identity plus source message IDs.**
4. **Current versus historical reflection generations.**
5. **Buffered/inactive versus active memory state.**
6. **Atomic activation contract** coupling derived content and source-consumption markers.
7. **Separate thread and persistent resource identity.**
8. **Stable thread owner resource.**
9. **Explicit subagent episode isolation.**
10. **Explicit direct-agent sharing by scope.**
11. **Read-only memory path.**
12. **Context construction as a distinct API.**
13. **Backend capability flags.**
14. **Structured extractor results with independent failures.**
15. **Derived-memory generation/history introspection.**
16. **`asOf` reconstruction for projection visibility.**
17. **Lifecycle flags for observation/reflection/buffering.**
18. **Explicit background-work drain API.**
19. **Separate execution FGA and tool approval.**
20. **Dedicated durable recovery path with evolving lease/fencing support.**
21. **Live-versus-persisted projection regression tests.**

None of these mechanisms alone proves a complete general knowledge architecture.

## 44. Failure / anti-pattern evidence

### 44.1 Scope identifier confused with authority

Memory sharing is driven by resource/thread IDs while authenticated execution policy is separate.

**Ledger:** reinforce KA-F-001.

### 44.2 Primary deletion/retention leaves derived planes outside the operation

Mongo prune excludes OM and cannot reach semantic vectors; vector deletion may continue after the ordinary delete call.

**Ledger:** reinforce KA-F-012 and add Mastra evidence to deletion/retention families.

### 44.3 Package/feature name hides realized profile

Local versus gateway OM, backend feature flags and transitioning lease support differ under the same Mastra feature names.

**Ledger:** reinforce KA-F-013.

### 44.4 Persistent memory occupies privileged prompt channels

Working memory/OM can be injected as system messages even though their content is not authority.

**Ledger:** add Mastra recurrence to KA-F-017.

### 44.5 Intermediate completion mistaken for multi-plane settlement

Run/delete return can precede background memory/vector work; `settled()` itself does not surface child failures.

**Ledger:** reinforce KA-F-019 and add KA-F-037 for the distinct quiescence-versus-success confusion.

### 44.6 Read-modify-write treated as safe concurrency

Open thread/OM concurrency reports and the merged title-clobber race provide independent evidence.

**Ledger:** move KA-F-023 to reinforced.

### 44.7 Persistent scope contaminates transient episodes

Experimental resource-scope OM explicitly warns that one thread can continue unfinished work from another.

**Ledger:** move KA-F-025 to reinforced, interpreted narrowly as episode/task context contamination rather than an argument against legitimate resource-level memory.

### 44.8 Live projection treated as complete/canonical evidence

Current #23271 fixes live/persisted transcript-part divergence.

**Ledger:** move KA-F-032 to reinforced.

### 44.9 Quiescence barrier treated as reconciliation success

`Memory.settled()` resolves after background failures rather than rejecting.

**Ledger:** new KA-F-037.

### 44.10 Historical replay treated as current authority state

Open PR #22767 reports replayed old approval/suspension prompts becoming interactive after settlement unless current durable suspension state is checked.

**Ledger:** new KA-F-038.

## 45. Candidate-invariant recurrence assessment

Mastra independently supports or strongly reinforces many existing invariant families, especially:

- KA-I-001 raw/source evidence separate from derived memory;
- KA-I-003 namespace/domain IDs are not principals;
- KA-I-006 supersession/current-projection transitions require lineage/history;
- KA-I-008 event/visibility time differs from world-valid time;
- KA-I-009 current/history/evidence retrieval intents differ;
- KA-I-010 retrieval rank is not truth;
- KA-I-011 derived state requires profile/generation identity;
- KA-I-012 backend realization must be qualified;
- KA-I-014 protected knowledge requires policy before model exposure;
- KA-I-015 persistent memory remains untrusted content;
- KA-I-016 deletion is multi-plane reconciliation;
- KA-I-017 schema/derivation evolution requires explicit compatibility/migration behavior;
- KA-I-018 exact build/backend/model/profile belongs in capability identity;
- KA-I-019 policy/provenance metadata must survive all projections/backends;
- KA-I-020 retrieval never grants execution authority;
- KA-I-021 unknown/false/conflict/history states need structure;
- KA-I-022 applicability requires structured scope;
- KA-I-023 material transformations need provenance;
- KA-I-024 context construction is separate from retrieval;
- KA-I-025 epistemic basis is distinct from attribution/storage state;
- KA-I-027 derived projections require coverage/generation identity;
- KA-I-028 mutation settlement must govern downstream success/consumption;
- KA-I-029 transient episode identity differs from persistent domain scope.

### Newly reinforced candidates

**KA-I-032** moves from candidate to reinforced. Letta provided consolidation/retry evidence; Mastra independently provides buffered inactive observations plus an atomic activation transition that moves source-consumption markers only when derived content activates.

**KA-I-036** moves from candidate to reinforced. LlamaIndex showed source/derivative/presentation identity failures; Mastra independently models unique buffered derivatives with source message IDs/ranges, and #23271 demonstrates presentation identity/lifecycle corruption when a provider-local block ID is reused beyond its valid scope.

### Still single-task candidates

KA-I-004, KA-I-005, KA-I-007, KA-I-031, KA-I-033, KA-I-034 and KA-I-037 remain candidates. Mastra provides adjacent evidence for some, but not enough to claim an independent full match.

### New invariant IDs

None. The strongest Mastra lessons fit existing invariant families; creating new IDs would duplicate KA-I-028/KA-I-009/KA-I-020 rather than improve the ontology.

## 46. 26-question campaign matrix

| # | Evidence question | Mastra answer | Architectural implication |
|---|---|---|---|
| 1 | Stable identity | Strong operational IDs for resource, thread, message, OM record/generation/chunk and run. | Keep identity domains separate; none is automatically real-world semantic identity. |
| 2 | Identity vs namespace/principal | Resource/thread route/share memory; auth/FGA/approval are separate. | Scope keys are not authenticated principals. |
| 3 | Provenance | Source ranges, message IDs, generation/origin/config/time are strong coarse lineage. | Preserve this shape but add claim-level derivation provenance. |
| 4 | Epistemic state | Mostly prose/application-specific extractors; no universal verified/disputed/unknown taxonomy. | General substrate needs explicit epistemic state. |
| 5 | Temporal truth | Strong record/visibility timing and `asOf` projection; no general world-valid intervals. | Separate transaction/observation/context time from validity time. |
| 6 | Conflict/supersession | Reflection creates new current generation and retains history; semantic reconciliation is model-driven. | Supersession needs provenance and epistemic policy, not just a new summary. |
| 7 | Relationships | Operational resource/thread/source-range associations; no general typed world relationship truth model. | Do not equate runtime foreign keys with semantic assertions. |
| 8 | Permissions/sensitivity | Separate FGA/request context/tool approval; memory scope IDs are not sufficient. | Enforce policy before exposure/action. |
| 9 | Actionability | Durable approvals/suspensions separate; stale replay issue shows actionability must be current. | Historical content cannot grant current actionability. |
| 10 | Knowledge vs authority | Strong separation in architecture; A2A issue shows invocation auth is separate again. | Preserve Knowledge != Authority != Execution. |
| 11 | Resources | Message attachments, placeholders, MIME/data/URL handling exist. | Useful ingestion form, not a complete canonical resource envelope. |
| 12 | Canonical vs derived | Raw messages, working memory, vectors, OM generations, context and stream projections are distinct. | Treat derived planes as rebuildable/auditable where possible. |
| 13 | Structured retrieval | Strong ID/time/resource/thread queries; working memory can be structured. | Useful deterministic retrieval but not a full world-fact schema. |
| 14 | Relationship retrieval | No general graph traversal in ordinary memory model. | Relationship retrieval remains an external/general-substrate requirement. |
| 15 | Full-text retrieval | Raw messages can be browsed/addressed; OM recall focuses source ranges and optional semantic search. | Exact evidence retrieval should remain available independently of semantic recall. |
| 16 | Semantic retrieval | Semantic recall derives vectors from message text. | Embeddings are index state, not truth/confidence. |
| 17 | Composite retrieval | History, OM, working memory, semantic recall, other-thread context and caller context combine. | Specify candidate/eligibility/context-placement rules explicitly. |
| 18 | Context construction | Explicit `getContext()` builds model-visible state and channel placement. | Context builder is a first-class governed layer. |
| 19 | Poisoning/injection | Persistent content can re-enter system prompt; execution policy is separate. | Persisted text remains untrusted unless provenance/trust says otherwise. |
| 20 | Concurrency | Thread creation, OM generation, ended-turn and legacy partial-update races provide evidence. | Use atomic uniqueness/CAS/transactions/leases/idempotency as semantics require. |
| 21 | Derived integrity | Buffered/active generations, source IDs, atomic swap are positive; live projection defect shows drift risk. | Track lifecycle, coverage and reconciliation of derivatives. |
| 22 | Deletion/retention | Primary rows, OM, vectors and background cleanup have separate lifecycle; Mongo retention excludes OM. | Retention/delete is a multi-plane policy and settlement result. |
| 23 | Schema evolution | Deprecated OM fields, adapter capability flags and legacy compatibility paths exist. | Migrations/capability profiles must be explicit. |
| 24 | Recovery | Durable snapshots replay LLM/tools; dedicated lease/fencing support is profile-dependent/currently evolving. | Replay identity and effect settlement remain separate. |
| 25 | Unknown/negative | No universal structural taxonomy in ordinary memory. | Explicit unknown/false/not-established/conflict state still required. |
| 26 | Scope of truth | Thread/resource scope strong operationally; semantic applicability of individual facts is not normalized. | Store applicability scope with assertions, not only storage location. |

## 47. Assertion-centric hypothesis reassessment

Mastra does **not** weaken the campaign's emerging assertion-centric hypothesis.

It strengthens a layered interpretation:

- raw messages/events are evidence/occurrences;
- OM observations/reflections are derived semantic projections;
- structured extracted values are derived candidate assertions;
- resource/thread IDs are scope/ownership routing;
- approval/suspension records are authority state;
- tool calls/effects are execution state.

What Mastra lacks as a general knowledge substrate is the explicit per-assertion envelope that can say:

- what proposition is asserted;
- by/for whom;
- from which evidence;
- through which transformation;
- with what epistemic status;
- valid when/where/for which version/task;
- superseding/contradicting which prior assertion;
- usable for which authority purposes.

Therefore Mastra is best treated here as strong evidence for **memory lifecycle, derivation, context and execution-boundary design**, not as evidence that free-form memory records should replace structured assertions.

## 48. Non-conclusions

KA-5 does **not** conclude that:

- Mastra is unsafe or unsuitable for ACL/Vera;
- Mastra should be selected as the knowledge substrate;
- OM observations are always inaccurate;
- resource scope should never be used;
- system-message memory is always exploitable;
- every Mastra backend has the same concurrency/deletion/retention behavior;
- current recovery lease support works across every PubSub/backend;
- the public durable-agent docs' older no-distributed-lock warning accurately describes every current profile;
- an OM generation is canonical truth;
- a vector similarity score is confidence;
- a thread/resource ID is an authenticated principal;
- `Memory.settled()` is defective merely because it chooses not to reject child failures; it is a drain contract, not a reconciliation certificate;
- open PR #22767 has already fixed current main;
- Mastra's ordinary memory APIs exhaust all optional ecosystem capabilities.

## 49. Confidence summary

**High confidence:** current identity planes, OM record/generation structure, raw-versus-derived separation, source ranges, context construction, buffered-versus-active lifecycle, Mongo retention asymmetry, `Memory.settled()` semantics, current #23271 live/persisted projection fix, backend capability flags, durable replay behavior.

**Medium-high confidence:** current open concurrency reports #20148/#22188/#19740 and open PR #22767 as failure evidence, because they are concrete but were not independently reproduced by KA-5.

**Medium confidence:** exact distributed recovery/fencing guarantee across all profiles, because current source shows lease infrastructure while current docs retain an older contradictory warning and KA-5 did not certify every provider.

**Low/no claim:** exhaustive security posture, full privacy-erasure compliance, or complete behavior of every optional Mastra integration.

## 50. Sources

### Current upstream source/docs

- https://github.com/mastra-ai/mastra/tree/d7bd6f7a91daf528f34d628faede4a916421b0dd
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/packages/core/package.json
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/docs/src/content/en/docs/memory/overview.mdx
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/docs/src/content/en/docs/memory/observational-memory.mdx
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/docs/src/content/en/reference/memory/settled.mdx
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/packages/memory/src/index.ts
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/packages/memory/src/processors/observational-memory/processor.ts
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/packages/memory/src/processors/observational-memory/observation-utils.ts
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/packages/memory/src/processors/observational-memory/constants.ts
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/packages/core/src/storage/types.ts
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/packages/core/src/storage/domains/memory/base.ts
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/stores/mongodb/src/storage/domains/memory/index.ts
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/docs/src/content/en/docs/harness/durable-agents.mdx
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/packages/core/src/agent/durable/durable-agent.ts
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/pubsub/redis-streams/src/index.ts
- https://github.com/mastra-ai/mastra/blob/d7bd6f7a91daf528f34d628faede4a916421b0dd/pubsub/valkey-streams/src/index.ts

### Current/recent issue and PR evidence

- https://github.com/mastra-ai/mastra/issues/22863
- https://github.com/mastra-ai/mastra/issues/20148
- https://github.com/mastra-ai/mastra/issues/22188
- https://github.com/mastra-ai/mastra/issues/19740
- https://github.com/mastra-ai/mastra/issues/19911
- https://github.com/mastra-ai/mastra/pull/21041
- https://github.com/mastra-ai/mastra/pull/22960
- https://github.com/mastra-ai/mastra/pull/22767
- https://github.com/mastra-ai/mastra/commit/d7bd6f7a91daf528f34d628faede4a916421b0dd

### Official Mastra background material

- https://mastra.ai/blog/observational-memory
- https://mastra.ai/blog/agent-memory-layers
- https://mastra.ai/blog/introducing-durable-agents
- https://mastra.ai/blog/what-are-durable-ai-agents

## 51. Stop condition

KA-5 has answered the 26 campaign questions for Mastra deeply enough to update the cumulative invariant/failure ledgers without selecting an architecture or storage technology.

The next planned campaign candidate is **KA-6 — LangGraph Knowledge-Architecture Revisit**.

Queue position is not authorization. KA-5 stops here. No LangGraph research, cross-project synthesis, coverage scan, schema selection, storage selection, retrieval implementation, embedding work, catalog migration, benchmarking or ACL/Vera implementation is authorized by this report.
