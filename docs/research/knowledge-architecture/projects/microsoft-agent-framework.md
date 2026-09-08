# Microsoft Agent Framework Knowledge-Architecture Revisit

**Campaign task:** KA-8  
**Project:** Microsoft Agent Framework (MAF)  
**Canonical repository:** `microsoft/agent-framework`  
**Research date:** 2026-09-08  
**Status:** complete within the user-authorized KA-7 + KA-8 bounded block  
**Historical project report:** `docs/research/projects/microsoft-agent-framework.md`

## Scope and stop boundary

This revisit studies Microsoft Agent Framework as evidence for the general ACL/Vera knowledge architecture. It does **not** select MAF as ACL's execution framework, does not select a memory/database backend, and does not implement anything.

Unlike KA-7 Google ADK, KA-8 includes a meaningful upstream delta. The historical Task 21 report used `afdc0db...`; current `main` was verified at:

`44dc76ce818b779a2ccf4ed73e0be505ec1552c8`

Current Python `agent-framework-core` reports version:

`1.17.0`

The source now includes materially richer workflow checkpointing/recovery behavior and an experimental Harness memory subsystem that did not dominate the historical architecture review. KA-8 therefore covers both the prior workflow/recovery themes and the newer knowledge-specific memory path.

The user explicitly authorized KA-7 and KA-8 together as one bounded research block. Evidence attribution remains project-specific. This report contains Microsoft Agent Framework evidence only.

The block stops before OpenAI Agents SDK research, final cross-project synthesis, storage selection, schema selection or implementation.

---

# 1. Executive assessment

MAF is unusually valuable for this campaign because the current source exposes both sides of the ACL/Vera boundary:

- replayable workflow state, checkpoints, staged writes, approvals and recovery;
- persistent memory, transcripts, derived topic records, indexes and context construction.

The strongest architectural evidence is not that these should be unified. It is the opposite: MAF demonstrates why **execution state, durable memory, projections, authority state and effects need explicit boundaries and identities**.

Highest-value findings:

1. Current workflow checkpoints distinguish committed user state, executor state, edge-runner delivery state, pending HITL requests, checkpoint lineage and graph signature.
2. `iteration_count` is explicitly **not unique**; checkpoint lineage identifies order. This is a positive warning against reusing a convenient counter as occurrence identity.
3. Merged PR #7948 adds fan-in edge delivery state to checkpoints and resets old runner state during restore, because omitted/stale in-flight edge state could either vanish or contaminate a restored run.
4. Current delivery code cancels and **awaits sibling tasks** after failure because orphan tasks otherwise mutate restored state after checkpoint restoration.
5. Open #7859 shows staged `State._pending` writes from a failed superstep can survive and become committed by a later successful run when failure paths do not discard them.
6. Current Harness memory separates raw transcripts, topic records, `MEMORY.md`, context selection and maintenance state.
7. Topic records preserve contributing `session_ids`, but LLM extraction/consolidation still lacks claim-level evidence links, verification state and derivation identity.
8. Memory consolidation is deliberately model-driven and may drop items judged stale; this is a provenance-bearing semantic transform, not mere formatting.
9. MAF exposes memory read, write, delete and forced-consolidation tools to the model; in the current Harness memory provider those tools use `approval_mode="never_require"`. This is evidence that **knowledge mutation authority must be separately governed**, not inferred from the ability to retrieve memory.
10. File-access autoapproval rules explicitly warn that local tools are approved by **tool name only**, so another local implementation using the same name can inherit approval. This independently supports origin/implementation-bound authority identity.
11. Reproduced #8140 shows model-facing messages can be deduplicated while the durable AG-UI snapshot remains duplicated; after refresh, the persisted corruption can reopen an approval for a call that already executed.
12. Open #7872 and reproduced #7890 show pending tool/approval state needs explicit closure, expiration/drain semantics; otherwise abandoned authority-bearing state can remain indefinitely.
13. Current `AgentIsolationKeyProvider` issue #8147 shows storage isolation scope has its own lifetime/hosting semantics and should not be confused with authenticated principal or canonical knowledge identity.

MAF is therefore strong evidence for lifecycle/recovery contracts and for layered memory architecture. It is not a complete epistemic ontology or general world-relationship model.

---

# 2. Current knowledge and execution planes

## Observed

Current MAF exposes materially distinct planes.

### 2.1 Agent session / history

`AgentSession`, `HistoryProvider`, `SessionStore`, `FileSessionStore` and related providers maintain invocation/session continuity and persisted message history.

### 2.2 Workflow state

Workflow `State` uses staged `_pending` writes and committed state. Writes become committed at a successful superstep boundary.

### 2.3 Workflow checkpoints

`WorkflowCheckpoint` records:

- `workflow_name`;
- `graph_signature_hash`;
- unique `checkpoint_id`;
- `previous_checkpoint_id` lineage;
- timestamp;
- per-executor messages;
- committed state;
- reserved executor state (`_executor_state`);
- reserved edge delivery state (`_edge_state`);
- pending request-info/HITL events;
- iteration count;
- metadata;
- checkpoint format version.

### 2.4 Harness durable memory

`MemoryContextProvider` uses a `MemoryStore` containing:

- raw transcript archive;
- topic memory records;
- `MEMORY.md` index;
- maintenance state;
- selected recent transcript turns;
- extracted memory candidates;
- model-driven consolidation.

### 2.5 File/resource workspace

`FileAccessProvider` uses a separate shared persistent `AgentFileStore` for files. Its own documentation explicitly distinguishes this from session-scoped memory.

### 2.6 Authority / tool approval

`ToolApprovalMiddleware`, policy-enforcement approval state and tool approval modes are separate from memory and checkpoint truth.

### 2.7 External effects

Tool execution and external systems remain another plane. Workflow checkpoint completion does not become an exactly-once effect ledger.

## Architectural lesson

This directly supports the campaign invariant:

**Knowledge != Authority != Execution.**

It also shows that one product can legitimately contain several persistent stores without any one of them being "the canonical knowledge database."

## Confidence

High.

---

# 3. Stable identity: checkpoint lineage, operation identity and semantic identity are different

## Observed

MAF uses several operational identities:

- agent/session IDs;
- workflow definition name;
- graph signature hash;
- checkpoint ID;
- previous checkpoint ID;
- iteration/superstep count;
- executor IDs;
- topology-derived edge-runner state keys;
- message IDs;
- tool/function call IDs;
- approval IDs;
- memory owner/source/topic/session IDs.

The current `WorkflowCheckpoint` documentation makes an important distinction explicit: `iteration_count` is not guaranteed unique. A HITL pause and response-entry checkpoint can share the same iteration. Ordering is defined by checkpoint lineage (`previous_checkpoint_id`) and timestamp, not by the counter.

## Architectural lesson

A convenient sequence number, tool name or workflow name should not be promoted into occurrence identity unless the lifecycle contract actually guarantees uniqueness.

ACL/Vera should distinguish:

- semantic entity/resource identity;
- definition/capability identity;
- operation occurrence identity;
- run/attempt/generation identity;
- checkpoint/revision identity;
- presentation/display name.

## Confidence

High.

---

# 4. Positive recovery pattern: checkpoint the hidden delivery state that actually affects behavior

## Evidence: merged PR #7948/current source

A fan-in edge can hold some source messages in an internal buffer across supersteps. Before #7948, that buffer was not checkpointed or reliably reset.

The resulting failures had two opposite forms:

- **lost state:** a buffered message had already been drained from the runner context, so omitting the fan-in buffer from the checkpoint caused the restored workflow to wait forever for a message that had already happened;
- **stale state:** a failed pre-checkpoint run could leave buffered messages in memory; restoring an older checkpoint onto the same process could combine those stale messages with replayed messages and fire the fan-in too early.

Current source carries edge-runner delivery state under `_edge_state`, and restore resets runners before reapplying checkpointed edge state.

## Architectural lesson

A checkpoint is only replay-correct if it includes **all hidden mutable state that changes future transition behavior**, not merely the obvious user dictionary.

For ACL/Vera this generalizes to:

- reducer buffers;
- unresolved approvals;
- pending messages;
- retry counters;
- tool continuation state;
- read-set/revision state;
- context derivation state when replay semantics depend on it.

## Confidence

High.

---

# 5. Positive generation-fencing pattern: cancel and join old work before restore proceeds

## Observed

Current `_edge_runner.py` includes `gather_cancelling_siblings_on_error()`.

The source comment states the reason: plain `asyncio.gather()` can leave sibling tasks executing after another task fails. Those orphan tasks can mutate fan-in buffers or pending-message queues **after** checkpoint restore has reset state, corrupting the resumed generation with output from the failed never-checkpointed superstep.

The helper creates tasks, awaits them together, and on failure cancels every sibling then awaits all of them before re-raising. The current implementation is used across relevant edge-delivery concurrency points.

## Architectural lesson

This independently supports the same cross-project invariant found in Google ADK #7058:

> Every background/mutating occurrence needs run/generation identity, and a generation transition must settle, cancel-and-join, detach with explicit ownership, or fence all prior-generation occurrences before the new generation is considered active.

The key is not merely "cancel." The old work must no longer be able to mutate the new generation.

## Confidence

High.

---

# 6. Failure: staged writes from a failed generation can leak into a later successful run

## Evidence: reproduced open #7859

MAF workflow `State` has explicit superstep semantics:

- `set()` writes into `_pending`;
- `get()` sees pending then committed;
- `commit()` moves pending values to committed state;
- `discard()` removes pending values without commit.

Issue #7859 reports a reproduced path where an executor stages a pending state write and then fails. The runner re-raises without calling `discard()`. The workflow instance is later reused. A successful later superstep calls `commit()`, causing the stale pending write from the failed run to become committed even though the later run never wrote it.

## Architectural lesson

Pending/candidate mutation state must be scoped to an exact operation generation and receive an explicit terminal disposition:

- committed;
- discarded;
- retried as the same semantic operation;
- or reconciled.

"The operation threw an exception" is not itself proof that all staged mutations were rolled back.

This becomes a hostile fixture for ACL/Vera: failed-run staged knowledge/state must never silently settle under a later run identity.

## Confidence

High for the issue's reproduced source path.

---

# 7. Raw transcripts, derived topic memory and presentation index are separate

## Observed

Current experimental `MemoryContextProvider` provides a clean layered shape:

1. **raw transcript archive** through `FileHistoryProvider`;
2. **extracted topic records** (`MemoryTopicRecord`);
3. **derived `MEMORY.md` index** rebuilt from current topic records;
4. **selected topic/recent-turn context** injected into the model;
5. **maintenance state** tracking consolidation timing/session participation.

A `MemoryTopicRecord` contains:

- topic;
- stable topic slug;
- summary;
- list of memory strings;
- `updated_at`;
- contributing `session_ids`.

The index pointer is derived from the topic record and can be rebuilt.

## Architectural lesson

This is strong independent support for:

- raw evidence separately addressable from derived semantic memory (KA-I-001);
- canonical/derived/presentation identity separation (KA-I-036);
- derived indexes being rebuildable rather than treated as sole canonical truth (KA-I-011).

It is a good reference architecture shape, even though its topic records are not sufficient as Vera's canonical assertion type.

## Confidence

High.

---

# 8. Topic/session provenance is useful but not claim-level derivation provenance

## Observed

Topic records preserve which `session_ids` contributed to the topic. Context injection also surfaces cross-session origin information so downstream observers can distinguish loaded memory from content native to the current session.

This is materially better than an unattributed summary.

However, after extraction and especially consolidation, an individual memory sentence does not universally carry:

- exact source message IDs/line references;
- exact evidence spans;
- extractor model/prompt/version;
- consolidation model/prompt/version;
- verification state;
- confidence;
- transformation decision lineage;
- claim-level supersession relation.

## Architectural lesson

Coarse topic/session provenance is valuable but does not replace claim-level evidence/derivation provenance when a memory can influence consequential automation.

## Confidence

High.

---

# 9. LLM extraction and consolidation are semantic mutations, not formatting

## Observed

The default memory extraction prompt asks a model to select durable facts/preferences/decisions/patterns from a transcript delta.

The consolidation prompt asks a model to:

- preserve durable facts/preferences/decisions;
- remove duplicates/overlap;
- **drop stale or obviously transient items**;
- tighten the summary/memory list.

If consolidation succeeds, the rewritten topic record replaces the previous record. If the model call fails or produces malformed output, the existing record is retained and the maintenance window is not advanced when every topic fails.

## Architectural lesson

"Consolidate memory" can change what future reasoning believes is worth seeing. It therefore requires transformation provenance, restraint and appropriate mutation authority.

For Vera, a consolidation event should be traceable as:

`source knowledge revision -> transform profile -> proposed/new revision -> settlement`

and should not be mistaken for a neutral index rebuild.

## Confidence

High.

---

# 10. Concurrency around memory merge is profile-qualified

## Observed

`MemoryContextProvider` creates asynchronous locks keyed by event loop, backing `MemoryStore`, owner, source, operation kind and topic/state key.

This serializes concurrent merge/consolidation operations **within the relevant process/event-loop/store-object context**.

The file-backed implementation still performs ordinary file read/write operations. The broader file-access source separately documents that process-local locking or an expected-line check is not a cross-process conditional write guarantee; true multi-process integrity requires conditional/versioned writes at the backing-store layer.

## Architectural lesson

Application-level locks are not a universal concurrency contract.

For any future Vera store, concurrency claims must be qualified by:

- process boundary;
- replica boundary;
- store/backend atomicity;
- conditional-write/version support;
- transaction/isolation semantics.

This reinforces KA-I-012 and KA-F-023 rather than creating a new concept.

## Confidence

High.

---

# 11. Memory scope/owner is routing and isolation, not authenticated principal

## Observed

`MemoryFileStore` can derive an owner-specific storage root from a configured session-state owner key plus source ID. Values are encoded into storage-safe segments.

Separately, current .NET issue #8147 concerns the lifetime contract of `AgentIsolationKeyProvider` used across hosted session/task/storage surfaces. The issue discusses claims-based isolation, request/execution scope and long-lived hosting services.

## Architectural lesson

A storage isolation key answers:

> which storage partition should this operation address?

It does not by itself answer:

> who is the authenticated principal, what are they allowed to read/write, and for what purpose?

ACL/Vera should keep principal identity, authorization decision and storage routing key separate even when one is derived from the other.

## Confidence

High.

---

# 12. Persistent knowledge mutation authority is distinct from retrieval authority

## Observed

In the current experimental `MemoryContextProvider`, the model receives tools including:

- `list_memory_topics`;
- `read_memory_topic`;
- `write_memory`;
- `delete_memory_topic`;
- `search_memory_transcripts`;
- `consolidate_memories`.

These tools are declared with `approval_mode="never_require"` inside the provider.

The provider instructions explicitly encourage the model to write durable facts/decisions/preferences and allow forced consolidation when the user asks.

## Architectural lesson

This is not a claim that MAF's design is universally unsafe; applications can wrap or constrain the agent. The knowledge-architecture lesson is more general:

**permission to retrieve/read persistent knowledge must not imply permission to mutate, delete or semantically consolidate it.**

Vera should have separately policyable action classes such as:

- read/search;
- append candidate memory;
- promote/verify;
- revise/supersede;
- delete/forget;
- consolidate/rewrite;
- change sensitivity/ownership.

This is new candidate KA-I-043.

## Confidence

High for current Harness source; policy conclusions are architectural extrapolation.

---

# 13. Tool autoapproval by name creates a concrete authority-identity hazard

## Observed

Current `FileAccessProvider` exposes read-only and all-tools autoapproval rules.

Its own source documentation warns:

- hosted calls carrying `server_label` are excluded;
- local tool calls are classified by tool name;
- another local tool registered under one of those names (for example a caller-configurable shell tool) may also be auto-approved;
- such a collision can bypass the human approval boundary.

## Architectural lesson

This independently supports Google ADK #6721's same-name/origin problem.

Authority-bearing classification should bind to trusted capability identity such as:

- provider/origin;
- implementation registration identity;
- tool schema/signature;
- occurrence ID;
- policy profile;
- arguments;

—not only the model-visible tool name.

This reinforces cross-project KA-I-042 and KA-F-044.

## Confidence

High; the warning is explicit in current source.

---

# 14. Approval should bind to exact invocation content and consume once

## Positive evidence: merged PR #6966

MAF's Python policy-enforcement path previously tracked approval too weakly. PR #6966 hardened the flow so an approval binds to the reviewed invocation:

- call ID;
- function name;
- arguments;
- security label;
- session;
- response ID / embedded function call.

The approval is consumed on first use. Reused call ID, changed function/args, escalated label, different session or mismatched response requires a new approval.

## Architectural lesson

This is strong independent support for occurrence-bound, context-bound approval state.

It complements rather than replaces the name-collision lesson: the operation must first be identified as the correct trusted capability, then the approval must bind to the exact occurrence/content/principal/policy context.

## Confidence

High.

---

# 15. Pending authority state needs an explicit terminal lifecycle

## Evidence: open #7872 and reproduced #7890

### #7872

Issue #7872 argues that tool call/approval lifecycles can be left dangling when a user cancels, a process exits, a browser refreshes or streaming is interrupted between function call and terminal function result/rejection/cancellation.

The issue requests public enumeration/drain/closure semantics and warns against accepting a new user turn while prior tool work remains unresolved.

### #7890

Reproduced #7890 shows policy-enforcement pending approvals retained indefinitely when a policy violation requests approval but the approval is never successfully consumed. The middleware has no TTL, maximum bound or general cleanup path for rejected/abandoned/unconsumed entries, so a long-lived middleware instance can accumulate them without bound.

## Architectural lesson

Authority-bearing pending state should have explicit lifecycle states and bounded retention:

- pending;
- approved/consumed;
- rejected;
- cancelled;
- expired;
- superseded;
- orphaned/reconciled.

Before accepting a new normal turn/run when semantics require closure, the framework should drain, explicitly carry forward, or close prior pending authority state.

This becomes candidate KA-I-045 and observed KA-F-048.

## Confidence

Medium-high. #7890 is reproduced; #7872 is a design/bug report describing a reproducible lifecycle gap.

---

# 16. Durable projection can be corrupt while the live/model projection looks correct

## Evidence: reproduced open #8140

Issue #8140 reports an AG-UI resume path where a client replays its transcript. MAF prepends the stored snapshot and persists the concatenation without de-duplication on that resume path.

A separate model-facing path **does** deduplicate messages before sending them to the provider. The live resumed run can therefore look correct and the gated tool can execute normally.

But the durable snapshot is built from the unreconciled raw list. After refresh/hydration, the duplicated assistant tool call lacks a matching tool result and an approval UI can reopen for a call that already executed.

## Architectural lesson

Model-visible context, UI projection and durable/canonical evidence must not silently use incompatible reconciliation rules.

If multiple projections intentionally differ, their lineage and reconciliation contract must be explicit.

This reinforces:

- KA-I-036 source/derived/presentation identity separation;
- KA-I-023 transformation/reconciliation provenance;
- KA-F-032 runtime/projection non-canonicity;
- KA-F-038 historical/consumed authority evidence becoming actionable.

The mechanism is retained in the detailed report rather than assigned a new failure ID because the cumulative ledger already covers the underlying projection/authority families.

## Confidence

High; issue is labeled reproduced.

---

# 17. Model-visible context is a projection, not durable truth

## Observed

The memory provider builds context from:

- `MEMORY.md`;
- selected topic records based on keyword overlap;
- optionally recent transcript turns;
- context instructions;
- raw transcript search only when explicitly invoked.

Only a subset of topics is auto-loaded each turn. Tool-call turns can be omitted from recent history depending on configuration.

## Architectural lesson

A model's current prompt cannot be used as proof that:

- all relevant knowledge was considered;
- the prompt contains the canonical record;
- absent information is false;
- a topic was not known;
- the context revision is fully current.

This reinforces KA-I-024 and KA-F-027.

## Confidence

High.

---

# 18. Retrieval is composite in practice but not an epistemic truth engine

## Observed

MAF current memory/file surfaces expose several retrieval styles:

- transcript text search;
- topic/index lookup;
- keyword-based topic selection;
- recent-turn history;
- optional external memory providers such as Cosmos semantic memory integrations;
- file grep/search.

The Harness memory provider's automatic topic selection is a simple relevance heuristic over topic/summary keywords.

## Architectural lesson

Retrieval mechanism determines candidate visibility, not truth.

A future Vera retrieval contract should name:

- candidate introducers;
- rerankers;
- hard permission/sensitivity gates;
- current/historical query intent;
- provenance requirements;
- semantic score interpretation.

## Confidence

High.

---

# 19. Unknown, false, stale and hidden remain under-modeled

## Observed

`MemoryTopicRecord` stores text memories and a summary but does not require a typed epistemic status.

The consolidation prompt may tell the LLM to drop stale items, but the record model itself does not structurally encode:

- verified;
- inferred;
- disputed;
- false;
- unknown;
- not established;
- historically true;
- no longer current;
- hidden by permission.

## Architectural lesson

A textual memory bullet is not sufficient for Vera's consequential knowledge state.

The canonical substrate still needs explicit epistemic/currentness fields independent of how a summary model phrases the memory.

## Confidence

High.

---

# 20. Temporal truth is not first-class in topic memory

## Observed

Topic records have `updated_at`; transcripts/message records have their own message/event ordering/time; checkpoint records have timestamp and lineage.

`updated_at` indicates record maintenance time, not necessarily the interval when each remembered proposition was true in the world.

A consolidation model can call a memory "stale" based on textual/contextual reasoning without a required structured valid-until time.

## Architectural lesson

Record update time, evidence event time, world-valid interval and retention/consolidation time should remain separate.

## Confidence

High.

---

# 21. Schema and semantic-profile evolution remain explicit concerns

## Observed

Current source includes:

- checkpoint `version`;
- graph signature compatibility;
- stable registered type IDs for session state restoration;
- explicit warnings about globally unique type IDs;
- decision records around session serialization;
- experimental feature boundaries.

Memory extraction/consolidation semantics are partly defined by prompts/configuration rather than only by the serialized record shape.

## Architectural lesson

Successful deserialization is not proof of semantic equivalence.

A knowledge revision should carry enough profile identity to know how derived memories were produced, and schema/prompt changes should trigger explicit migration/re-derivation decisions when semantics change.

This reinforces KA-I-017, KA-I-018 and KA-I-023.

## Confidence

High.

---

# 22. File/resource identity is still distinct from knowledge identity

## Observed

`FileAccessProvider` presents shared persistent files across sessions/agents through path-based tools. The store abstraction can be in-memory, filesystem or remote-blob backed.

The source takes significant care around path normalization, root containment, symlinks/reparse points and storage-key encoding.

These are resource-locator and storage-integrity concerns. They do not make file path the canonical identity of the real-world resource or the truth claims extracted from it.

## Architectural lesson

Vera still needs separate representation for:

- logical resource identity;
- locator(s);
- observed content/version digest;
- extraction/derivation identity;
- claims derived from the resource.

This is adjacent to KA-I-037 but does not independently establish a complete content-digest model in MAF, so KA-I-037 remains a candidate.

## Confidence

High.

---

# 23. Workflow/control relationships are not canonical world relationships

## Observed

MAF has rich operational relationships:

- graph edges;
- fan-in/fan-out topology;
- checkpoint parent lineage;
- executor ownership;
- tool call/result pairing;
- approval/request pairing;
- session/message history.

These relationships are essential for execution and recovery.

They are not a general canonical world relationship system for ownership, location, social relationships, device topology, project dependencies or epistemic contradiction/supersession.

## Architectural lesson

An execution graph should not become Vera's world graph merely because both are graphs.

## Confidence

High.

---

# 24. Deletion/retention remains multi-plane

## Observed

Memory topics can be deleted; transcripts are stored separately; `MEMORY.md` is rebuilt; session stores and workflow checkpoints are separate; file-access storage is separate; external memory integrations may have their own retention/indexing.

Deleting one topic record does not by itself establish privacy erasure of:

- raw transcript evidence;
- derived indexes/caches;
- session snapshots;
- external provider copies;
- backups/audit planes.

## Architectural lesson

Delete/forget must remain a reconciled multi-plane operation.

This reinforces KA-I-016 and KA-F-026.

## Confidence

High.

---

# 25. Recovery lineage is stronger than "latest state," but still not effect settlement

## Observed

MAF checkpoints explicitly chain through `previous_checkpoint_id` and include graph signature/versioned state needed for restoration.

The framework has invested in preserving hidden edge state and cancelling orphan tasks that could mutate the restored generation.

None of this makes an external tool side effect exactly-once. A checkpoint can say what the workflow believes about its internal transition state; the outside world may require a separate idempotency/effect ledger/reconciliation path.

## Architectural lesson

Workflow recovery and effect settlement should remain separate ACL/Vera subsystems even when they correlate through common operation IDs.

## Confidence

High.

---

# 26. Full 26-question evidence matrix

| # | Evidence question | KA-8 assessment |
|---|---|---|
| 1 | Stable identity | Strong operational IDs/lineage; iteration/tool names are insufficient occurrence identity. No universal semantic entity ID. |
| 2 | Identity vs namespace/principal | Session IDs, memory owner/source IDs and isolation keys are routing/storage scope, not authenticated principal identity. |
| 3 | Provenance | Raw transcripts + topic `session_ids` are useful; claim-level evidence and complete extraction/consolidation profile are not universally required. |
| 4 | Epistemic state | Topic memories are prose; verified/inferred/disputed/false/unknown are not first-class generic fields. |
| 5 | Temporal truth | Checkpoint/message/update times exist; no generic world-valid interval for memory claims. |
| 6 | Conflict/supersession | Consolidation can rewrite/drop memory, but no canonical typed conflict/supersession transition model. |
| 7 | Relationships | Rich execution/control relationships; no general canonical world relationship assertion substrate. |
| 8 | Permissions/sensitivity | Tool approval/policy/isolation are separate systems. Memory owner/routing is not full principal-purpose-sensitivity policy. |
| 9 | Actionability | Strong exact-invocation approval binding exists; name-only autoapproval warning exposes capability-identity hazard. |
| 10 | Knowledge vs authority | Separate systems. Current memory mutation tools show why read vs write/delete/consolidate authority needs explicit policy. |
| 11 | Resources | File access is a separate persistent resource plane; not a complete logical-resource/version/evidence model. |
| 12 | Canonical vs derived | Raw transcripts -> topic records -> `MEMORY.md` -> selected context is explicit and highly informative. |
| 13 | Structured retrieval | Topic/session lookup and provider-specific structured storage exist; not a universal world-query language. |
| 14 | Relationship retrieval | Operational graph traversal exists; not canonical world relationship retrieval. |
| 15 | Full-text retrieval | Transcript/file text search exists. |
| 16 | Semantic retrieval | Available through external memory integrations; Harness topic selection itself is keyword-based. Score/relevance remains separate from truth. |
| 17 | Composite retrieval | Multiple retrieval modes exist, but no universal candidate/rerank/hard-gate truth contract. |
| 18 | Context construction | Explicitly separate: recent turns, topic selection, index and instructions are assembled per run. |
| 19 | Poisoning/injection | Persisted memory becomes model-visible content; provenance/policy must remain outer layers. Tool-name autoapproval is a separate authority-injection hazard. |
| 20 | Concurrency | Strong workflow orphan-task fencing; #7859 exposes pending-state rollback gap; process-local memory locks remain backend-qualified. |
| 21 | Derived integrity | `MEMORY.md` rebuild is positive; consolidation changes semantics; #8140 shows live/durable projection reconciliation can diverge. |
| 22 | Deletion/retention | Topic delete is not transcript/session/checkpoint/external-provider privacy erasure. |
| 23 | Schema evolution | Checkpoint versions, graph signatures and stable registered state type IDs help; derived memory profile/prompt still needs provenance. |
| 24 | Recovery | Checkpoint lineage + hidden edge state + task fencing are strong; internal recovery remains distinct from external effect settlement. |
| 25 | Unknown/negative | Not first-class in generic memory topic model. |
| 26 | Scope of truth | Owner/source/session storage scope is too coarse to encode arbitrary proposition applicability. |

---

# 27. Highest-value positive patterns for ACL/Vera

These are reference patterns, not framework adoption decisions.

## 27.1 Checkpoint hidden behavior-bearing state

If a buffer/reducer/continuation affects future behavior, either persist it or explicitly declare it non-replayable.

## 27.2 Cancel and join old generation work

Do not restore into mutable state while failed-generation tasks can still write into it.

## 27.3 Distinguish raw transcript, semantic memory and presentation index

Keep source evidence searchable after summarization; rebuild lightweight indexes from stronger records.

## 27.4 Preserve cross-session provenance

Topic-level contributing session IDs are a useful minimum lineage layer.

## 27.5 Bind approvals to exact invocation content

Call ID + implementation + args + security/policy context + session/principal is substantially safer than sticky name-level approval.

## 27.6 Keep failed consolidation from silently advancing maintenance state

A maintenance window should not be marked complete merely because a consolidation attempt was made.

---

# 28. Highest-value warnings for ACL/Vera

## 28.1 Pending mutation state must die with the failed operation

#7859 shows staged writes can otherwise commit under a later run.

## 28.2 Model-visible clean state does not prove durable clean state

#8140 shows different reconciliation pipelines can hide persisted corruption until reload.

## 28.3 Read memory authority != rewrite/delete authority

Knowledge mutation actions need their own policy classes.

## 28.4 Tool display name != trusted capability identity

Current MAF source explicitly warns name collisions can bypass autoapproval.

## 28.5 Pending approval state needs terminal closure and bounded retention

#7872/#7890 show unresolved authority state can outlive the interaction that created it.

## 28.6 Local locks != distributed concurrency guarantee

File-backed memory integrity remains dependent on backend/write semantics across processes/replicas.

---

# 29. Hostile / acceptance fixtures derived from KA-8

Future test ideas only:

1. **Failed superstep pending write** — stage a write, fail, run a later successful turn; stale value must not commit.
2. **Restore while sibling task still running** — old task attempts a post-restore mutation; it must be cancelled/joined or generation-fenced.
3. **Fan-in partial buffer restore** — checkpoint with one fan-in branch buffered; restore must neither lose nor duplicate it.
4. **Counter collision** — two checkpoints at same iteration; lineage must still identify exact order.
5. **Tool-name collision** — untrusted/local shell tool adopts a trusted read-only tool name; autoapproval must bind provider/implementation identity and reject the collision.
6. **Approval mutation mismatch** — approved call ID reused with changed args/security label/session; must require fresh approval.
7. **Abandoned approval** — pending approval is never answered; it must expire/close and not accumulate forever.
8. **New turn with prior dangling tool call** — host must drain/close/carry forward explicitly before normal processing where lifecycle requires it.
9. **Model projection deduped, durable snapshot not** — reconciliation must be consistent or durable write must fail.
10. **Reload after executed approval** — historical duplicated tool call cannot reopen current authority state.
11. **Memory read-only principal** — retrieval succeeds; `write_memory`, delete and consolidate are denied.
12. **Memory consolidation provenance** — dropped memory must have a traceable transform/revision event.
13. **Cross-session topic provenance** — every loaded durable topic exposes contributing sessions/evidence boundary.
14. **Concurrent topic writers across replicas** — process-local locks must not be treated as distributed atomicity.
15. **Delete topic vs forget person** — topic deletion cannot report privacy erasure while transcripts/session/external copies remain.
16. **Context omission** — a topic not auto-loaded must not be interpreted as unknown/false.
17. **Storage isolation key spoof** — routing key alone cannot grant another principal's memory access.
18. **Checkpoint/effect split** — crash after external side effect but before internal checkpoint; reconciliation/idempotency prevents duplicate effect.

---

# 30. Contributions to cumulative invariants

## Existing invariant reinforcement

KA-8 adds evidence to:

- **KA-I-001** — raw transcripts remain separately addressable from topic memory/index.
- **KA-I-003** — storage/session/isolation scope is not authenticated principal.
- **KA-I-008** — record/update/checkpoint time differs from world-valid truth time.
- **KA-I-011** — `MEMORY.md`/selected context are derived/rebuildable projections.
- **KA-I-012** — concurrency/storage semantics depend on realized backend/process profile.
- **KA-I-014** — protected knowledge must be filtered by principal/purpose policy before context.
- **KA-I-015** — persisted memory remains content, not policy.
- **KA-I-016** — deletion/forget is multi-plane.
- **KA-I-017** — checkpoint/state/profile evolution requires explicit compatibility/migration semantics.
- **KA-I-018** — realized capability includes version/backend/prompt/profile.
- **KA-I-019** — security/provenance metadata must survive persistence/projection.
- **KA-I-020** — knowing/retrieving memory does not grant execution authority.
- **KA-I-021** — generic memory needs explicit unknown/false/conflict/current-state semantics above prose.
- **KA-I-023** — extraction/consolidation/reconciliation decisions need provenance.
- **KA-I-024** — context construction is separate from retrieval/canonical memory.
- **KA-I-025** — attribution/session provenance is not verification state.
- **KA-I-027** — derived summaries/projections need coverage/generation semantics.
- **KA-I-028** — staged/settled mutation state must drive success and downstream state.
- **KA-I-029** — session/episode differs from persistent memory owner/domain scope.
- **KA-I-032** — consolidation maintenance state should advance based on successful integration, not mere attempt.
- **KA-I-036** — raw source, derived topic and model/UI projection identities are distinct.

## New cross-project reinforced invariant

**KA-I-041 — reinforced**

> Every concurrent/background operation that can mutate state, knowledge or effects must have stable occurrence identity bound to a run/generation, and teardown/restore/generation change must settle, cancel or fence every prior-generation occurrence before the new generation becomes active.

Independent evidence:

- KA-7 Google ADK #7058;
- KA-8 MAF current sibling-cancellation/restore source and PR #7948 follow-up race coverage.

## New cross-project reinforced invariant

**KA-I-042 — reinforced**

> Authority-bearing tool/continuation classification must bind to trusted origin/implementation/occurrence and relevant schema/profile, not a display/function name alone.

Independent evidence:

- KA-7 Google ADK #6721;
- KA-8 MAF current file-access autoapproval name-collision warning.

## New MAF-derived candidate

**KA-I-043 — candidate**

> Persistent knowledge mutation authority must be policy-distinct from knowledge read/retrieval authority; append, revise/supersede, delete/forget, consolidate/rewrite and sensitivity/ownership changes require separately governable action classes.

Evidence:

- current Harness `MemoryContextProvider` exposes read/search/write/delete/consolidate memory tools under one model context, with `approval_mode="never_require"` at tool definition.

## ADK-derived candidate retained from KA-7

**KA-I-044 — candidate**

> Transport/connection liveness is distinct from logical remote-session or continuation validity; retries must validate or reacquire the logical session generation rather than reusing it solely because the transport remains open.

Evidence:

- KA-7 Google ADK #7060.

## New MAF-derived candidate

**KA-I-045 — candidate**

> Pending authority/effect-continuation records require explicit terminal or expiry semantics and bounded retention; unresolved prior work must be drained, explicitly carried forward or closed before later turns can safely treat it as inactive.

Evidence:

- MAF #7872 and reproduced #7890.

No candidate is promoted to a final architecture rule in KA-8.

---

# 31. Contributions to cumulative failure patterns

KA-8 adds recurrence to:

- **KA-F-001** — storage/session/isolation key treated as authority.
- **KA-F-013** — package name alone is insufficient realized deployment identity.
- **KA-F-019** — an intermediate state/operation is mistaken for fully settled transition.
- **KA-F-020** — coarse source provenance without complete semantic transformation provenance.
- **KA-F-023** — read/modify/write plus process-local locks treated as distributed-safe integrity.
- **KA-F-026** — memory-topic deletion interpreted as privacy erasure.
- **KA-F-027** — selected/summary projection treated as exhaustive knowledge.
- **KA-F-032** — model/UI/runtime projection treated as canonical despite different durable reconciliation (#8140).
- **KA-F-038** — historical/consumed approval state becomes actionable after reload (#8140 adjacent recurrence).

## New cross-project reinforced failure

**KA-F-043 — reinforced**

> Background/mutating operation lifecycle is coarsened to a capability name or left unfenced across generation change, so orphan/stale work can mutate state after run teardown or restore.

Independent evidence:

- KA-7 Google ADK #7058;
- KA-8 MAF current orphan-sibling restore race prevention/source commentary.

## New cross-project reinforced failure

**KA-F-044 — reinforced**

> Authority-bearing tool/continuation handling classifies by function/tool name alone, so a colliding implementation or same-named different-origin occurrence inherits or loses approval semantics.

Independent evidence:

- KA-7 Google ADK #6721;
- KA-8 MAF current file-access autoapproval name-collision warning.

## New MAF-derived observed failure

**KA-F-045 — observed**

> A model/runtime that is allowed to retrieve persistent knowledge is also implicitly allowed to append, delete or semantically consolidate that knowledge without an independently evaluated knowledge-mutation authority decision.

Evidence:

- current Harness memory tool definitions and approval modes.

## ADK-derived observed failure retained from KA-7

**KA-F-046 — observed**

> Remote logical-session validity is inferred from transport liveness, so retries reuse a dead server-side continuation/session generation.

Evidence:

- KA-7 Google ADK #7060.

## New MAF-derived observed failure

**KA-F-047 — observed**

> Staged mutation state from a failed/cancelled operation survives its generation and is later committed by an unrelated successful run.

Evidence:

- reproduced MAF #7859.

## New MAF-derived observed failure

**KA-F-048 — observed**

> Pending approval/tool-continuation state has no complete terminal/expiry/drain lifecycle, so abandoned authority-bearing state remains actionable or accumulates without bound after the interaction that created it.

Evidence:

- #7872; reproduced #7890.

No failure pattern is promoted to a final architecture rule.

---

# 32. Non-conclusions

KA-8 does **not** conclude that:

- MAF is unsafe overall;
- the experimental Harness memory provider is intended to be a complete security boundary;
- every application using `MemoryContextProvider` grants unrestricted model mutation in practice;
- all workflow-state failures are unresolved on current main;
- process-local file storage is intended for multi-replica production use without additional concurrency controls;
- every AG-UI client corrupts durable history;
- every pending approval survives forever;
- Microsoft Agent Framework should or should not be adopted by ACL/Vera;
- a workflow checkpoint should contain external effect results instead of a separate effect ledger;
- topic markdown is a poor human-readable memory format;
- all memory consolidation should require human approval;
- final Vera storage must be graph-native, relational, document or file based.

The findings are narrower architecture evidence about identity, lifecycle, provenance, authority and projection boundaries.

---

# 33. Primary/current sources inspected

Current source pinned to `44dc76ce818b779a2ccf4ed73e0be505ec1552c8` included:

- `python/packages/core/pyproject.toml`
- `python/packages/core/agent_framework/_workflows/_checkpoint.py`
- `python/packages/core/agent_framework/_workflows/_state.py`
- `python/packages/core/agent_framework/_workflows/_edge_runner.py`
- workflow runner/executor sources and relevant tests
- `python/packages/core/agent_framework/_sessions.py`
- `python/packages/core/agent_framework/_harness/_memory.py`
- `python/packages/core/agent_framework/_harness/_file_access.py`
- `python/packages/core/agent_framework/_harness/_tool_approval.py`
- current Harness samples/docs and source warnings
- current session/serialization decision records

Current issue/PR evidence included:

- merged PR #6966 — exact policy-approval invocation binding/consume-once;
- reproduced #7859 — failed-superstep pending state leak;
- #7872 — dangling tool/approval closure semantics;
- reproduced #7890 — unbounded pending policy approvals;
- merged PR #7948 — fan-in edge state checkpoint/restore and stale-buffer handling;
- reproduced #8140 — AG-UI durable resume transcript duplication despite clean model projection;
- #8147 — isolation-key provider lifetime/hosting contract.

The current upstream revision is materially newer than the historical Task 21 checkpoint, so all delta claims are scoped to source/issues inspected here rather than inferred from package version alone.

---

# 34. Stop condition

KA-8 is complete when:

- current upstream identity/version was verified;
- meaningful source delta from the historical report was inspected;
- all 26 evidence questions were evaluated;
- workflow checkpoint/recovery and the new Harness memory layer were both analyzed;
- current issue/PR evidence was incorporated with scoped claims;
- new invariant/failure contributions were identified without selecting architecture;
- no Google evidence was attributed to Microsoft inside this report except where explicitly named as independent cross-project reinforcement;
- no OpenAI Agents SDK work began.

The user-authorized KA-7 + KA-8 research block is therefore ready for one cumulative ledger/state reconciliation and one atomic research-only commit, after which the campaign stops before OpenAI Agents SDK.
