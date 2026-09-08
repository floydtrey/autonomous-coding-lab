# Google ADK Knowledge-Architecture Revisit

**Campaign task:** KA-7  
**Project:** Google Agent Development Kit (ADK)  
**Canonical repository:** `google/adk-python`  
**Research date:** 2026-09-08  
**Status:** complete within the user-authorized KA-7 + KA-8 bounded block  
**Historical project report:** `docs/research/projects/google-adk.md`

## Scope and stop boundary

This revisit studies Google ADK as evidence for the general ACL/Vera knowledge architecture. It does **not** decide whether ACL or Vera should adopt ADK, does not select a database or memory backend, and does not implement anything.

The historical Task 22 report already established ADK's broad agent/session/tool/workflow model. KA-7 therefore asks the campaign's knowledge-architecture questions more directly:

- what ADK treats as persistent session state versus long-term memory;
- which identifiers are persistence scope, occurrence identity, remote-session identity or authority identity;
- what provenance survives into memory;
- how temporal and epistemic state are represented;
- how memory mutation settles;
- how confirmation binds to an exact tool call;
- how remote A2A/MCP boundaries alter state, identity and approval semantics;
- which failures should become ACL/Vera hostile fixtures.

The user explicitly authorized KA-7 and KA-8 together as one bounded research block after the campaign had matured enough to support two-project units. Evidence attribution remains project-specific. This report contains Google ADK evidence only.

The task stops before OpenAI Agents SDK research, cross-project architecture synthesis, storage selection or implementation.

---

## 1. Upstream verification and delta from the historical report

### Observed

The canonical repository is `google/adk-python`.

Current `main` was verified at:

`b0180620f4c2f4f4467a89c37a30f75bf849700b`

Current source reports:

`google-adk 2.8.0`

The historical Task 22 report used the same upstream commit. Consequently KA-7 is **not an implementation-delta study**. It is a deeper knowledge-substrate analysis plus verification of issue evidence that appeared or changed after the historical pass.

Current public ADK documentation also continues to describe session continuity, memory services and best-effort resumability as distinct concerns.

### Architectural lesson

A stable source revision can still justify a new research pass when the question changes. The historical report focused on framework/runtime architecture; KA-7 asks whether those same primitives satisfy a general knowledge model's identity, truth, provenance, recovery and authority requirements.

### Confidence

High.

### Non-conclusion

No inference is made that an unchanged source tree means unchanged deployment behavior in every managed Google service. Managed Memory Bank and remote services remain profile-dependent.

---

## 2. Executive assessment

Google ADK provides strong evidence for **separating operational state planes**, but not for collapsing them into a universal knowledge object.

The most important current distinctions are:

1. `Session` is conversation/execution continuity, not a person/entity record.
2. `BaseMemoryService` is long-term memory/retrieval scoped by `(app_name, user_id)`, distinct from session event history.
3. `MemoryEntry` carries useful content, author, timestamp, ID and arbitrary metadata, but lacks a required epistemic truth envelope.
4. database session storage has an explicit storage revision marker and stale-writer rejection, which is a strong positive concurrency pattern.
5. resumability is explicitly best-effort and at-least-once; in-memory state disappears across resume.
6. exact-call tool confirmation is materially stronger than a name-only approval, but an event merely authored as `"user"` is not itself authenticated principal evidence.
7. managed Memory Bank generation/ingestion is a derived-memory plane and can continue asynchronously after the caller returns.
8. current issue #7058 shows that a capability name is not sufficient identity for concurrent background occurrences.
9. current issue #7060 shows transport liveness is not logical remote-session validity.
10. A2A issues show that identical function names can carry different origin/continuation semantics and that remote state projections can diverge from in-process behavior.

For Vera, ADK is therefore useful evidence for session, memory-service, call, event and remote-session boundaries. It is not evidence that `(app_name, user_id, content, timestamp)` is a sufficient canonical truth schema.

---

## 3. State planes: session, events, memory, tools and external services

### Observed

Current ADK exposes several materially different state planes.

### 3.1 Session

`Session` contains:

- `id`;
- `app_name`;
- `user_id`;
- session `state`;
- ordered `events`;
- `last_update_time`;
- a private `_storage_update_marker` used by storage implementations to identify the exact stored revision.

### 3.2 Event history

Events carry authored conversation/tool/workflow evidence and are the primary session-history substrate. They are used by confirmation processing to resolve original function calls and prior responses.

### 3.3 Long-term memory

`BaseMemoryService` is a separate abstraction. Its generic operations include:

- add a whole session to memory;
- add event deltas to memory;
- add explicit memory entries;
- search memory.

Its generic scope is `(app_name, user_id)` rather than `session_id`.

### 3.4 Managed Memory Bank

`VertexAiMemoryBankService` can ingest events, directly create memories, generate/consolidate memories and use backend-specific metadata such as revision TTL, allowed topics, consolidation and revision controls.

### 3.5 Tool confirmation

Confirmation is represented through function calls/responses and resolved against session history. It is not stored as a generic memory fact.

### 3.6 Remote A2A/MCP state

Remote agents and MCP sessions introduce additional continuation/session identities whose lifetime can differ from local session and transport lifetime.

### Architectural lesson

For ACL/Vera, these planes should remain semantically named. A conversation session, long-term memory record, tool approval, external continuation and authenticated principal are not interchangeable simply because all can be represented as dictionaries and strings.

### Confidence

High.

---

## 4. Stable identity: operational identities are useful but not universal semantic identities

### Observed

ADK provides many operational identifiers:

- session ID;
- event ID;
- function-call ID;
- confirmation function-call ID;
- optional memory ID;
- MCP session/cache key;
- A2A task/remote continuation identities;
- storage update marker.

These identifiers solve different problems.

A `Session.id` identifies one conversational continuity object. A function-call ID identifies one call occurrence. A `MemoryEntry.id` may identify one memory item in a backend. `_storage_update_marker` identifies one storage revision of a session.

None is a general identity for a person, device, place, project, assertion or resource across domains.

### Failure evidence

Current #7058 demonstrates a concrete identity collapse. Parallel calls to the same async-generator tool are tracked under `active_streaming_tools[tool.name]`. The second occurrence overwrites the first task reference. Teardown can cancel only the last registered occurrence while the earlier task continues.

The bug exists precisely because **capability identity (`tool.name`) was reused as occurrence identity**.

### Architectural lesson

ACL/Vera should distinguish at least:

- capability/tool definition identity;
- invocation/call occurrence identity;
- run/attempt identity;
- external continuation/session generation identity;
- semantic entity identity.

A name is often a presentation/discovery field, not a lifecycle key.

### Confidence

High for the source/issue mechanism; medium on production prevalence outside the reported live-tool path.

### Non-conclusion

This does not mean tool names should never be unique. It means uniqueness of a tool definition does not make the name sufficient to identify concurrent calls to that tool.

---

## 5. Namespace and persistence scope are not authenticated principal identity

### Observed

Memory APIs are scoped by strings such as:

`(app_name, user_id)`

Sessions also carry `user_id`.

Those values are useful application routing/scope fields. They do not establish how the caller was authenticated, whether the caller may act as that user, or which purpose authorizes access.

### Failure evidence: #6461

Open/reopened issue #6461 reports an A2A path where tool confirmation can be forged by a peer because confirmation processing treats an event authored as `"user"` as the human response source. A remote peer can construct the content shape expected by the confirmation processor.

Current confirmation source does contain strong exact-call checks, but the author role string does not independently establish the real-world principal who supplied the approval.

### Architectural lesson

A robust Vera/ACL request should carry authenticated principal identity separately from:

- memory namespace;
- `user_id` routing key;
- message author role;
- session ID;
- A2A peer identity.

The authority layer can use those values, but none becomes authority merely by being named `user`.

### Confidence

High for the architectural distinction; issue scope remains A2A-specific.

---

## 6. Positive pattern: exact storage revision markers and stale-session rejection

### Observed

Current `DatabaseSessionService` uses an exact `_storage_update_marker` when loading and updating sessions. Its write path coordinates:

- a per-session lock;
- database row locking where supported;
- app/user shared-state rows;
- session deltas;
- event persistence;
- stale marker validation.

If the caller's session object was loaded from an older persisted revision, the storage marker mismatch can raise `StaleSessionError` instead of applying the stale mutation.

A backward-compatibility path exists for older marker-less sessions.

### Architectural lesson

This is strong positive evidence for an ACL/Vera **storage revision token** distinct from semantic truth metadata.

A mutable canonical object should usually be written against a known version/generation when concurrent writers are possible.

However:

`storage revision != epistemic revision != world-valid time`.

A successful compare-and-write tells us which stored version was updated. It does not tell us that the new content is true.

### Confidence

High.

### Non-conclusion

This does not prove every ADK session backend provides identical transaction/locking semantics. Backend capability remains part of realized deployment identity.

---

## 7. Session state versus long-term memory

### Observed

ADK's architecture clearly separates session event/state persistence from `BaseMemoryService`.

A session may contain temporary/current continuity required for an invocation. Long-term memory can outlive an individual session and is queried through `(app_name, user_id)`.

This separation is useful for Vera because transient task context and durable knowledge should not share the same retention and contamination behavior.

### Architectural lesson

A future Vera canonical model should not treat "everything remembered" as conversation state.

At minimum:

- transient session state;
- raw historical events;
- durable extracted/explicit knowledge;
- external-resource state;
- execution effects;
- authority/approval state

should remain separately governed even if one retrieval layer can combine them.

### Confidence

High.

---

## 8. MemoryEntry is provenance scaffolding, not a complete truth assertion

### Observed

`MemoryEntry` contains:

- `content`;
- optional `id`;
- optional `author`;
- optional `timestamp`;
- arbitrary `custom_metadata`.

The timestamp is described as when the original content happened and can be forwarded to the model.

This is useful. It can distinguish some source/event timing from storage timing.

But the generic type does not require:

- explicit versus inferred basis;
- verification state;
- confidence;
- disputed/conflicting state;
- supersession/invalidated state;
- valid-from / valid-until;
- authority-use classification;
- structured environment/person/project applicability;
- evidence links;
- derivation profile;
- canonical relationship semantics.

### Architectural lesson

ADK's memory record is compatible with being an adapter or retrieval-plane record inside Vera, but it is too permissive to be the canonical truth envelope without an application-defined schema layered over it.

### Confidence

High.

---

## 9. Temporal semantics: event time helps, but bitemporal truth is absent

### Observed

ADK has several time-like fields:

- event timestamps;
- `MemoryEntry.timestamp` for original content/event timing;
- session `last_update_time`;
- database/storage revision markers;
- managed Memory Bank revision TTL/expiry controls.

These have different meanings.

`last_update_time` is an operational record-time concept. A memory/event timestamp can approximate event time. TTL/revision expiry governs backend retention/lifecycle.

None provides a generic first-class interval for:

> "this proposition was valid in the world from T1 until T2, was recorded at T3, and corrected at T4."

### Architectural lesson

Vera needs explicit time semantics rather than a generic `timestamp` field whose meaning changes by record family.

Recommended separation remains:

- observation/event time;
- world-valid interval;
- record/transaction time;
- last verification time;
- retention/expiry time.

### Confidence

High.

---

## 10. Epistemic state and conflict handling remain application concerns

### Observed

The generic memory interfaces do not require a structured epistemic state. They can store text such as a user's statement, a model extraction or a managed Memory Bank result without a universal typed distinction among them.

There is no general ADK memory-level contract for:

- verified;
- explicit user statement;
- inferred;
- observation;
- disputed;
- contradicted;
- historically true but no longer current;
- unknown/not established.

Likewise there is no general cross-backend supersession model.

### Architectural lesson

Speaker attribution and extraction source should feed epistemic reasoning, but neither should substitute for an explicit epistemic field.

### Confidence

High.

---

## 11. Managed Memory Bank is a derived-memory system with profile-dependent semantics

### Observed

`VertexAiMemoryBankService` can:

- ingest events;
- generate memories;
- directly create memory records;
- consolidate direct memories;
- configure revision TTL;
- enable/disable consolidation;
- enable/disable memory revisions;
- constrain allowed topics;
- attach backend-specific metadata.

Which API path is used can depend on metadata keys and installed Vertex SDK capabilities.

### Architectural lesson

"Google ADK memory" is not one realized semantic profile.

Realized identity includes at least:

- ADK source/package revision;
- selected memory-service implementation;
- managed service/API generation;
- backend configuration;
- generation/consolidation options;
- relevant model/service profile;
- metadata/TTL/revision configuration.

This reinforces the campaign rule that capability identity cannot stop at package name.

### Confidence

High.

---

## 12. Asynchronous Memory Bank ingest: accepted work is not settled knowledge

### Observed

The current `VertexAiMemoryBankService` ingest path can create an `asyncio` task for `memories.ingest_events`, retain it in a module-level background-task set, attach error logging callbacks, and return without awaiting the operation.

The API call that initiated memory ingestion therefore does not necessarily mean the remote ingestion/generation has completed successfully.

### Architectural lesson

For Vera, a mutation lifecycle needs statuses such as:

- requested;
- accepted/queued;
- running;
- externally settled;
- derived/indexed;
- failed;
- uncertain;
- reconciled.

A context refresh should not assume the new memory is canonical/available merely because the producer method returned.

### Confidence

High for current source behavior.

### Non-conclusion

The background task is retained and failures are logged; this is not the claim that ADK loses every ingest failure. The lesson is narrower: caller completion is not derivation settlement.

---

## 13. Generic delete/forget coverage is incomplete

### Observed

The generic `BaseMemoryService` surface exposes addition and search but no universal delete/forget contract was found in the current generic API.

Managed backends may support retention, TTL, revisions or separate administration APIs.

### Architectural lesson

A Vera privacy/forget operation cannot be defined only in terms of one memory-provider method. It requires a cross-plane lifecycle covering:

- raw session events;
- extracted memories;
- indexes;
- managed service copies/revisions;
- caches;
- derived summaries;
- backups/audit retention subject to policy.

### Confidence

High for the generic API surface inspected; not a claim that Google Cloud has no deletion APIs.

---

## 14. Retrieval: useful service abstraction, not a universal composite truth query

### Observed

`BaseMemoryService.search_memory()` takes `(app_name, user_id, query)`.

Specific backends can implement different retrieval semantics. Managed Memory Bank can provide semantic retrieval. Other implementations may use lexical or simpler matching.

The generic result is still a memory retrieval result, not a universal query over canonical people/devices/resources/policies/relationships/events.

### Architectural lesson

Vera's retrieval layer should be able to invoke an ADK-like memory backend, but the canonical retrieval contract needs explicit modes and hard eligibility semantics above it.

The existing campaign model remains:

1. deterministic structured lookup/filter;
2. relationship traversal;
3. full-text;
4. semantic;
5. controlled composition/reranking.

### Confidence

High.

---

## 15. Retrieval rank is not truth or authority

### Observed

Semantic memory search returns relevance-oriented results. Nothing in ADK's generic memory contract turns a high-ranked memory into a verified fact or an authorized instruction.

### Architectural lesson

The assistant should separately evaluate:

- whether the memory is eligible to retrieve;
- provenance/trust;
- currentness;
- epistemic state;
- relevance/rank;
- actionability;
- authority.

### Confidence

High.

---

## 16. Context construction remains a separate layer

### Observed

ADK memory retrieval is not automatically identical to the final model context. Tools/processors load or present memories into the model-visible request.

Session events, remote content and memory search can therefore all be inputs to context construction without becoming equivalent canonical evidence.

### Architectural lesson

This independently supports a separate context-construction contract that records which knowledge revision/profile was used and why each item was included.

### Confidence

High.

---

## 17. Persistent memory remains untrusted model-visible content

### Observed

A stored memory can ultimately be surfaced as content to the model. ADK does not make the text itself a host policy simply because it came from a memory provider.

The A2A confirmation issue also demonstrates why content-role and authority must remain separate.

### Architectural lesson

Memory may say:

> "always run tool X without asking"

but that statement should remain knowledge/content until an outer policy engine independently authorizes that behavior.

### Confidence

High.

---

## 18. Tool confirmation: strong exact-call binding

### Observed

Current `request_confirmation.py` performs several important checks.

It:

- finds confirmation responses in the latest user-authored event;
- tracks confirmation function-call IDs;
- maps them back to the original function-call ID;
- resolves the original call from session history;
- checks agent authorship/ownership routing;
- checks the tool is still registered;
- checks the tool actually requires confirmation, statically or dynamically;
- checks the original tool name;
- checks original arguments match history;
- maps the approval to the exact original call ID;
- filters confirmations already consumed by subsequent function responses.

### Architectural lesson

This is a strong reference for **approval as occurrence-bound state**, not a sticky boolean associated with a tool name.

An approval should generally bind to:

- exact call occurrence ID;
- tool implementation/capability identity;
- arguments;
- relevant authority/policy context;
- principal;
- time/expiry;
- one-shot/sticky semantics.

### Confidence

High.

---

## 19. Exact call binding is still insufficient without authenticated principal binding

### Failure evidence: #6461

The confirmation mechanism's exact-call checks do not solve the separate question of who supplied the approval. If an A2A peer can create an event that the local processor treats as user-authored, then the content can satisfy the confirmation shape while the real principal is wrong.

### Architectural lesson

Approval identity has two independent axes:

1. **what exact operation is being approved?**
2. **which authenticated principal, under which authority, approved it?**

ADK's exact function-call validation is useful evidence for axis 1. #6461 is evidence that axis 2 cannot be inferred from a message role.

### Confidence

High as an architecture lesson.

---

## 20. A2A state projection: remote boundaries can silently change semantics

### Failure evidence: #6854

Open issue #6854 reports that session state does not transparently cross `RemoteA2aAgent` boundaries in either direction. Remote `output_key` state can remain in the remote session rather than caller session state, while caller state deltas are not automatically transported to the remote session.

The issue also reports a state-only event shape whose `content=None` handling can result in previous content being relayed instead of the intended state-only signal.

### Architectural lesson

In-process equivalence is not enough for a distributed knowledge/state contract.

A remote boundary needs explicit declarations for:

- which state fields cross;
- which are local only;
- how state-only events are represented;
- which projection is authoritative;
- correlation IDs;
- settlement/acknowledgement;
- schema/version profile.

### Confidence

Medium-high: current issue evidence is concrete, but deployment/protocol versions matter.

---

## 21. A2A confirmation relay: function name is not origin/continuation identity

### Failure evidence: #6721

Issue #6721 reports a relayed human-input/confirmation pause where local and remote pause flows share the same function name. Response transformation classifies by that shared name, so a human response intended for the remote pending continuation can be flattened as ordinary text rather than preserved as the function response required to resume the remote occurrence.

In the worst legacy path, downstream behavior can continue as though useful progress occurred even though the gated remote tool did not execute.

### Architectural lesson

Authority-bearing continuation handling must bind to more than a function name.

Required identity may include:

- origin server/agent;
- protocol profile;
- call/interrupt occurrence ID;
- parent run/task;
- expected response schema;
- authority state.

This supports a cross-project invariant with Microsoft Agent Framework's current name-collision autoapproval warning.

### Confidence

High for the issue's reported mechanism.

---

## 22. Concurrent streaming tools: operation occurrence identity and teardown fencing

### Failure evidence: #7058

Current issue #7058 reproduces on current main.

Two simultaneous calls to the same streaming tool start separate tasks but are registered under the same `tool.name` key. The second task overwrites the first task pointer. Run teardown later sees only one and cancels only one.

The orphan can remain pending after the agent run ends and can continue writing to the live request queue.

### Architectural lesson

This is broader than streaming tools.

Every background operation that can mutate:

- run state;
- context queues;
- knowledge;
- workspace;
- external effects

needs a stable **occurrence identity bound to run/generation**.

A generation transition should not declare the old run gone until every prior-generation mutable occurrence has either:

- settled;
- been cancelled and joined;
- become durably detached with explicit ownership;
- or been fenced from writing into the new generation.

### Confidence

High.

---

## 23. MCP cache/session failure: transport liveness is not logical session validity

### Failure evidence: #7060

Current #7060 reports an MCP server scaling to zero and losing server-side in-memory sessions. The HTTP transport remains healthy. ADK's cached `MCPSession` can therefore appear connected under a transport-stream check while the remote server no longer recognizes the logical session ID.

Retry logic obtains the same cached logical session again and repeats the failure.

### Architectural lesson

A remote integration needs distinct state for:

- transport connection/liveness;
- authenticated service relationship;
- logical remote session/continuation identity;
- server generation/epoch if available;
- resumability status.

Retry should invalidate/reacquire the logical continuation when the server tells us that session generation is gone, even if TCP/HTTP remains fine.

### Confidence

High for the reported path; backend-specific response classification still matters.

---

## 24. Best-effort at-least-once resumability is explicit

### Observed

Current `ResumabilityConfig` documentation explicitly states:

- ADK resumes best-effort;
- a resumed tool call must be idempotent because execution is at-least-once;
- temporary/in-memory state is lost upon resumption.

### Architectural lesson

This is a valuable explicit contract. ACL/Vera should be equally explicit rather than using a vague word like "resume."

For any resumable task, required input must be either:

- durably persisted;
- deterministically reacquirable;
- revalidated fresh;
- or designated non-replayable.

External effects need separate idempotency/effect evidence.

### Confidence

High.

---

## 25. Execution replay and semantic memory mutation are separate

### Observed

ADK resumability is about invocation/tool/workflow progress. Memory Bank ingestion/generation is a separate background/managed state plane.

A resumed agent can therefore encounter memory state that is:

- older than the original attempt;
- newer than the original attempt;
- still processing;
- generated under a different managed service configuration.

### Architectural lesson

If deterministic replay matters, the execution record needs an explicit contract for persistent knowledge reads:

- pinned knowledge revision;
- recorded read-set;
- always-fresh read;
- or declared nondeterministic replay.

This is adjacent to KA-I-033 and reinforces it conceptually even though ADK does not provide a single concrete replay bug matching Letta/LangGraph's prior evidence.

### Confidence

High on the separation; replay policy remains application-specific.

---

## 26. Resources/artifacts are adjacent systems, not the memory truth model

### Observed

ADK provides artifact/resource/tool integrations outside `BaseMemoryService`.

A memory can refer to resource content, but the generic memory entry does not provide a universal resource identity/version/digest envelope.

### Architectural lesson

Vera's resource model still needs stable logical resource ID, locator, observed version/content digest, media type, provenance and access policy independent of memory text.

### Confidence

High.

---

## 27. Relationships: orchestration relationships are not world relationships

### Observed

ADK can represent agent hierarchies, session/event ordering, tool-call/result association and remote task relationships.

These are important operational links.

They are not a canonical relationship assertion substrate for world claims such as:

- person owns device;
- device located in room;
- project depends on repository;
- claim contradicts claim;
- preference applies to household member;
- capability governed by policy.

### Architectural lesson

Do not infer that an agent/workflow graph solves the knowledge graph problem.

### Confidence

High.

---

## 28. Unknown/negative/conflicting knowledge remains under-modeled

### Observed

The generic memory schema does not distinguish:

- false;
- unknown;
- searched but not established;
- disputed;
- obsolete;
- not applicable;
- hidden by permission.

An empty search result can therefore have several possible meanings depending on backend and policy.

### Architectural lesson

Vera should represent important negative/unknown states directly where they affect decisions.

### Confidence

High.

---

## 29. Scope of truth is richer than `(app_name, user_id)`

### Observed

ADK's memory scope is intentionally application/user-oriented. That is a useful storage boundary.

A proposition may additionally apply only to:

- a particular project;
- machine;
- environment;
- software version;
- mine/portal;
- household;
- time interval;
- task;
- device generation;
- role.

### Architectural lesson

Storage namespace and proposition applicability should be separate fields.

### Confidence

High.

---

# 30. Full 26-question evidence matrix

| # | Evidence question | KA-7 assessment |
|---|---|---|
| 1 | Stable identity | Strong operational IDs for session/event/call/memory; no universal semantic entity ID. #7058 shows tool definition name cannot identify concurrent occurrences. |
| 2 | Identity vs namespace | `app_name`, `user_id`, session and A2A routing values are scope, not authenticated principal. #6461 is direct authority evidence. |
| 3 | Provenance | Events, author, timestamps, call IDs and memory metadata help. Managed derivation profile and exact source/evidence chains are not universally required. |
| 4 | Epistemic state | Generic memory lacks required explicit/inferred/verified/disputed/confidence semantics. |
| 5 | Temporal truth | Event/memory timestamps exist; storage/update/TTL concepts exist; no generic bitemporal world-valid interval. |
| 6 | Conflict/supersession | Managed Memory Bank may revise/consolidate, but no universal typed conflict/supersession contract in BaseMemoryService. |
| 7 | Relationships | Operational associations exist; no canonical typed world relationship assertion system. |
| 8 | Permissions/sensitivity | Auth/plugins/policy remain outside memory scope. `(app,user)` is not a full access-control model. |
| 9 | Actionability | Confirmation can bind exact call name/args/ID; principal binding remains separate. |
| 10 | Knowledge vs authority | Architecturally separate; #6461 proves role/content cannot confer tool authority. |
| 11 | Resources/artifacts | Separate integrations; generic memory not a complete stable resource/version model. |
| 12 | Canonical vs derived | Session events/source evidence are distinct from generated/managed memories; backend derivation profile matters. |
| 13 | Structured retrieval | Backend-specific filters/metadata and direct memory service APIs; not a universal structured world query. |
| 14 | Relationship retrieval | Not first-class for canonical world relations. |
| 15 | Full-text retrieval | Implementation dependent. Generic contract does not standardize a full-text mode. |
| 16 | Semantic retrieval | Supported by managed Memory Bank/profile. Score is relevance, not truth. |
| 17 | Composite retrieval | No single generic cross-mode candidate-introducer/reranker/hard-gate contract. |
| 18 | Context construction | Separate from memory storage/search; processors/tools decide what enters model context. |
| 19 | Poisoning/injection | Retrieved memory and A2A content remain untrusted content; author role does not upgrade authority. |
| 20 | Concurrency | Database revision markers/locks are a positive pattern; #7058 exposes occurrence-tracking failure. |
| 21 | Derived integrity | Managed ingest/generation can be asynchronous; method return can precede settlement. |
| 22 | Deletion/retention | Generic memory API has no universal delete/forget; managed TTL/revisions are backend-specific, not privacy erasure. |
| 23 | Schema/version evolution | Exact source/backend/SDK profile matters; metadata capabilities vary. No universal semantic migration contract. |
| 24 | Recovery | Explicit best-effort, at-least-once resume; temp state lost. MCP/A2A logical-session state adds more recovery identity. |
| 25 | Unknown/negative | Not a first-class generic memory state. |
| 26 | Scope of truth | Storage scope `(app,user)` is too coarse to represent arbitrary proposition applicability. |

---

# 31. Highest-value positive patterns for ACL/Vera

These are reference patterns, not adoption decisions.

## 31.1 Exact storage revision marker

Use a known persisted revision/generation to reject stale mutation rather than silently merging arbitrary stale session state.

## 31.2 Exact-call approval binding

Bind approval to the original function call ID, name and arguments, then consume it.

## 31.3 Explicit at-least-once recovery contract

Document replay limitations and require idempotency rather than implying exactly-once behavior.

## 31.4 Session versus long-term memory separation

Keep transient conversation continuity separate from durable memory retrieval.

## 31.5 Event IDs and event time into managed ingestion

Preserve original event identity/time where possible when producing derived memory.

---

# 32. Highest-value warnings for ACL/Vera

## 32.1 Scope strings do not authenticate principals

`user_id` and `author="user"` are not proofs of human authority.

## 32.2 Capability name is not occurrence identity

Concurrent identical tools require separate call/task lifecycle records.

## 32.3 Transport alive does not mean continuation alive

Remote logical sessions can die independently of HTTP/MCP transport.

## 32.4 Returned memory write is not necessarily settled memory

Background managed ingestion can still be pending or fail later.

## 32.5 Generic memory text lacks a truth envelope

Explicit, inferred, verified, disputed and historical states need outer structure.

## 32.6 Remote projections can differ from local semantics

A2A state/confirmation behavior must be tested at the protocol boundary, not inferred from in-process behavior.

---

# 33. Hostile / acceptance fixtures derived from KA-7

These are future test ideas only.

1. **Same capability, two concurrent calls** — start two identical streaming tools with different call IDs; teardown must settle/cancel both.
2. **Old run orphan writes** — terminate run generation A while a background tool is pending, start generation B, ensure A cannot mutate B queues/state.
3. **Forged user role** — remote peer sends a syntactically valid approval response authored `user`; authority layer must reject without authenticated principal binding.
4. **Exact-call mismatch** — same tool name but different args/call ID; prior approval cannot authorize it.
5. **Consumed approval reuse** — approval consumed once; later model step/run cannot reuse it.
6. **Server session lost, transport alive** — remote server restarts while transport survives; retry must invalidate/reacquire logical session.
7. **A2A same-name pause origins** — local and remote confirmation share function name; response must route by occurrence/origin, not name.
8. **State-only remote event** — remote state delta with no text must not be substituted by stale prior content.
9. **Async memory ingest failure** — caller returns before remote ingest failure; context must not report memory settled until reconciled.
10. **Stale session writer** — two session revisions race; older revision must fail or rebase explicitly.
11. **Replay with temp input** — resumable operation depends on in-memory-only state; recovery reacquires or refuses.
12. **Delete/forget audit** — generic memory deletion cannot report privacy completion while session events/managed revisions remain.
13. **Timestamp semantics** — distinguish event timestamp from storage update/TTL.
14. **Memory conflict** — two contradictory memories for same subject; retrieval must not silently newest-win.
15. **Permission-limited empty search** — distinguish no match from not authorized/hidden where policy requires.

---

# 34. Contributions to cumulative invariants

## Existing invariant reinforcement

KA-7 adds evidence to:

- **KA-I-003** — namespace/domain IDs are not principals (#6461, `(app,user)` scope).
- **KA-I-008** — event/memory time and storage/update/TTL time are distinct.
- **KA-I-011** — managed memory generations are derived state with profile-dependent behavior.
- **KA-I-012** — backend/service behavior must be qualified.
- **KA-I-014** — protected memory/tool authority requires current principal/purpose policy.
- **KA-I-015** — remote/persistent memory remains content, not policy.
- **KA-I-018** — realized capability includes exact backend/profile/config.
- **KA-I-019** — security/provenance semantics must survive remote projection.
- **KA-I-020** — memory/content retrieval does not grant tool authority.
- **KA-I-023** — managed memory generation/consolidation is itself a provenance-bearing transform.
- **KA-I-024** — context construction remains separate from memory retrieval.
- **KA-I-025** — memory attribution/timestamp is not epistemic verification.
- **KA-I-028** — asynchronous managed-memory ingest requires settlement state.
- **KA-I-029** — session/episode identity differs from persistent app/user memory domain.
- **KA-I-036** — remote/projection identity differs from source occurrence identity.

## New invariant evidence

KA-7 contributes one half of cross-project **KA-I-041**:

> Every concurrent/background operation that can mutate state, knowledge or effects must have stable occurrence identity bound to a run/generation, and teardown/restore/generation change must settle, cancel or fence every prior-generation occurrence before the new generation becomes active.

Evidence: current #7058.

KA-7 contributes one half of cross-project **KA-I-042**:

> Authority-bearing tool/continuation classification must bind to trusted origin/implementation/occurrence and relevant schema/profile, not a display/function name alone.

Evidence: #6721.

KA-7 contributes new candidate **KA-I-044**:

> Transport/connection liveness is distinct from logical remote-session or continuation validity; retries must validate or reacquire the logical session generation rather than reusing it solely because the transport remains open.

Evidence: current #7060.

No final invariant is adopted by this report.

---

# 35. Contributions to cumulative failure patterns

KA-7 adds recurrence to:

- **KA-F-001** — routing/user strings treated as authorization (#6461).
- **KA-F-013** — package/project name insufficient deployment identity.
- **KA-F-019** — method/API completion mistaken for mutation settlement (async Memory Bank ingestion).
- **KA-F-020** — source metadata without complete derivation profile.
- **KA-F-032** — remote/runtime projection not complete/canonical (#6854/#6721).

KA-7 contributes one half of cross-project **KA-F-043**:

> Background/mutating operation lifecycle is coarsened to a capability name or left unfenced across generation change, so orphan/stale work can mutate state after run teardown or restore.

Evidence: #7058.

KA-7 contributes one half of cross-project **KA-F-044**:

> Authority-bearing tool/continuation handling classifies by function/tool name alone, so a colliding implementation or same-named different-origin occurrence inherits or loses approval semantics.

Evidence: #6721.

KA-7 contributes new observed **KA-F-046**:

> Remote logical-session validity is inferred from transport liveness, so retries reuse a dead server-side continuation/session generation.

Evidence: #7060.

---

# 36. Non-conclusions

KA-7 does **not** conclude that:

- ADK is unsafe overall;
- every A2A deployment permits forged confirmations;
- every Memory Bank write is unreliable;
- Vertex Memory Bank lacks deletion capabilities outside the generic ADK service interface;
- ADK should or should not be adopted by ACL/Vera;
- Google-managed services share identical semantics with local implementations;
- the current open issues reproduce on every provider/version;
- a canonical Vera knowledge system must be relational, graph-native or stored in one database;
- `(app_name, user_id)` is a bad application storage scope;
- all memory extraction should require a human approval;
- every replay must be deterministic.

The conclusions are narrower architectural lessons about identity, provenance, truth, settlement and authority boundaries.

---

# 37. Primary/current sources inspected

Current source, pinned to `b0180620f4c2f4f4467a89c37a30f75bf849700b`:

- `src/google/adk/version.py`
- `src/google/adk/sessions/session.py`
- `src/google/adk/sessions/database_session_service.py`
- `src/google/adk/memory/memory_entry.py`
- `src/google/adk/memory/base_memory_service.py`
- `src/google/adk/memory/vertex_ai_memory_bank_service.py`
- `src/google/adk/apps/_configs.py`
- `src/google/adk/flows/llm_flows/request_confirmation.py`
- `src/google/adk/tools/mcp_tool/mcp_session_manager.py`
- A2A/remote-agent source paths surfaced through current issue/source trace.

Current issue evidence:

- #6461 — A2A confirmation principal/role problem.
- #6099 — decision-ledger feature/design gap.
- #6854 — RemoteA2aAgent session-state projection.
- #6721 — relayed confirmation same-name/origin classification.
- #7058 — concurrent same-name streaming tool orphan task.
- #7060 — transport-alive / logical-MCP-session-dead retry loop.

Current public ADK documentation was also rechecked for memory/session/resumability context. Source code remains the primary evidence for this report.

---

# 38. Stop condition

KA-7 is complete when:

- current upstream identity was verified;
- historical findings were not merely repeated without current validation;
- all 26 evidence questions were explicitly evaluated;
- current session/memory/confirmation/recovery/remote-session mechanisms were inspected;
- new issue evidence was incorporated with scoped claims;
- invariant/failure contributions were identified without selecting architecture;
- no Microsoft evidence was attributed to Google in this report.

The block proceeds to its separately documented KA-8 Microsoft Agent Framework report, then updates the cumulative campaign ledgers once for the user-authorized two-project block.
