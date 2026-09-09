# Knowledge Core Architecture Decision Log

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Component:** Knowledge Core  
**Status:** active physical-architecture decision log  

---

# Purpose

This file records accepted physical-architecture decisions for Knowledge Core as they are made. Detailed architecture documentation will be synthesized after the major structural decisions are complete. The completed Knowledge Architecture Evidence Campaign remains the evidence base; physical choices must not weaken it.

Conceptual primitive families remain semantic roles rather than mandatory tables: ENTITY, ASSERTION, OCCURRENCE, RESOURCE, EVIDENCE/PROVENANCE LINK, and SEMANTIC PROFILE/VOCABULARY DEFINITION.

> **Knowledge does not grant authority. Authority does not prove execution. Execution acknowledgement does not prove world settlement.**

---

# Decision status

- **Accepted** — current architecture decision; later changes require an explicit superseding decision.
- **Open** — deliberately unresolved.
- **Superseded** — retained for history but replaced by a later decision.

Decisions are not silently rewritten when they change.

---

# Accepted decisions

## KC-D001 — Knowledge Core is a standalone service
**Status:** Accepted
Knowledge Core is its own local/network-capable service. Vera, ACL, and future clients use a defined interface and never directly own/manipulate the canonical database. Initial co-location on one PC must not prevent later process/VM/machine separation.

## KC-D002 — PostgreSQL is the initial canonical knowledge store
**Status:** Accepted
PostgreSQL is the initial source of canonical semantic state. Search indexes, embeddings, summaries, caches, graph projections, and current-state projections are derived/rebuildable where practical.

## KC-D003 — Large artifact bytes live outside PostgreSQL
**Status:** Accepted
PostgreSQL stores RESOURCE identity/metadata/version/lineage; large bytes live in a separately managed artifact store.

## KC-D004 — Authority is a separate deterministic service boundary
**Status:** Accepted
AI reasoning requests operations but does not grant authority. Authority evaluates exact operations; retrieval does not itself grant execution permission.

## KC-D005 — Architecture supports a physically read-only Authority Root
**Status:** Accepted
Root authority policy/verification material can live on controller-enforced write-protected media. Writable operational state remains elsewhere. Hardware protection supplements process/OS/credential isolation.

## KC-D006 — Canonical knowledge history is non-destructive and supports explicit undo/reversal
**Status:** Accepted
Ordinary learning/correction appends new records instead of destroying prior canonical state. Undo/reversal is explicit and preserves mistaken intermediate history. Privacy erasure is separate.

## KC-D007 — Assertion semantics use typed relational fields with bounded JSON extensibility
**Status:** Accepted
Core assertion semantics use typed relational fields/children. `JSONB` is a bounded profile-governed extension and may not replace core or authority-critical semantics.

## KC-D008 — Canonical records use a universal internal reference registry for cross-family links
**Status:** Accepted
A physical reference registry supplies stable internal addressing across canonical families while specialized tables retain semantics/constraints. It is not a seventh conceptual primitive or generic graph.

## KC-D009 — Temporal model uses independent world-valid time and immutable knowledge-record time
**Status:** Accepted
World-valid time and knowledge-record time are separate. Late correction appends at real record time. Current state is derived/rebuildable; historical belief remains reconstructable.

## KC-D010 — Provenance is a typed, traversable lineage model separate from semantic relationships and lifecycle state
**Status:** Accepted
Typed provenance links exact sources/versions/activities and supports backward explanation and forward impact without becoming domain relationship, truth, lifecycle, or authority.

## KC-D011 — Initial artifact store is a local immutable content-addressed filesystem
**Status:** Accepted
Artifact bytes initially live in a configurable SHA-256-addressed immutable local store. Physical deduplication does not merge logical identity/provenance/ownership/history; backend remains replaceable.

## KC-D012 — Semantic profiles and vocabulary are immutable, explicitly versioned, and pinned by assertions
**Status:** Accepted
Assertions pin immutable profile revisions. Material meaning changes create new semantic identity or explicit migration, never silent reinterpretation.

## KC-D013 — Knowledge Core API exposes semantic operation classes, not generic CRUD or database access
**Status:** Accepted
Clients use read/search/explain, append, correction/reversal, identity transition, resource/evidence, and privileged governance operations. No raw DB credentials or arbitrary field updates.

## KC-D014 — Retrieval is an authorization-first composite pipeline; context construction is a final derived step
**Status:** Accepted
Hard eligibility precedes protected model-facing content. Structured/temporal/relationship/full-text/semantic retrieval and provenance/conflict/currentness evaluation remain distinguishable; rank is not truth or permission.

## KC-D015 — Derived data is generation-versioned, lineage-bound, explicitly staleable, and rebuildable
**Status:** Accepted
Derived projections/indexes/summaries/embeddings/caches retain source/generation/profile/model/config lineage and lifecycle state. They can become stale/restricted and rebuild under generation fencing; they never outrank canonical sources.

## KC-D016 — Identity resolution is non-destructive, transition-based, and reversible
**Status:** Accepted
Entity IDs stay stable. Aliases/identifiers are evidence, not identity. Merge/split/replacement/reassignment are explicit provenance-bearing transitions. Merges do not rewrite all assertion foreign keys or delete original entities; a derived current resolution view composes them and can be reversed.

---

## KC-D017 — Privacy deletion/restriction is a privileged staged reconciliation lifecycle, not ordinary supersession

**Status:** Accepted

Privacy restriction/erasure is separate from ordinary correction, undo, supersession, or invalidation. It may intentionally remove or render inaccessible canonical payloads that ordinary non-destructive history would otherwise preserve.

A deletion/restriction operation creates a privileged lifecycle case/occurrence with explicit authorized scope and a state machine that can distinguish at least:

- requested;
- immediately fenced/restricted from ordinary retrieval/use;
- canonical reconciliation pending;
- canonical payload erased or retained under an explicit bounded exception;
- descendant/derived reconciliation pending;
- artifact reconciliation pending;
- backup/restore fence active;
- external/exported recipient reconciliation pending/unknown where applicable;
- settled in declared scope;
- failed/blocked and requiring intervention.

### Access fence first

Once a valid restriction/erasure request is accepted, affected knowledge must be fenced from ordinary reads, semantic retrieval, summaries, embeddings, caches, context construction, and automation **before** all physical cleanup necessarily finishes.

The system must prefer "temporarily unavailable while deletion reconciles" over continuing to expose data because a background cleanup job has not completed.

### Canonical handling

Depending on the authorized deletion/retention policy, canonical records may have payload fields erased, rows physically removed, references severed, or retained only under a narrowly defined exempt purpose. Ordinary append-only preservation does not override a valid erasure requirement.

Any minimal tombstone/settlement metadata retained after erasure must be limited to what is necessary to prevent resurrection, prove/reconcile lifecycle state, and satisfy an authorized retention purpose. It must not retain the erased substantive payload merely to preserve an audit trail.

### Descendants and derived data

Forward provenance/lineage is used to identify dependent summaries, extracted text, chunks, embeddings, vector/full-text projections, relationship closures, caches, context packages, and other derivatives.

Affected descendants are immediately fenced or marked deletion/restriction-pending and are then erased, rebuilt without the deleted source, or otherwise reconciled according to their storage plane.

A vector index, cache, or summary may not remain searchable simply because it is "only derived."

### Artifact blobs and physical deduplication

Deletion of one logical resource/version does not automatically delete a shared content-addressed blob if that exact blob is still legitimately referenced by another independently authorized logical resource/version.

Conversely, physical deduplication is never used as a reason to keep a logical deleted record reachable. Logical references, permissions, provenance, and lifecycle are reconciled independently from whether bytes are physically shared.

When no legitimate retained reference requires a blob, the artifact-store reconciliation process may remove it after the applicable retention/settlement rules permit.

### Backup and restore fence

Backups may be immutable or impractical to surgically rewrite. Therefore Knowledge Core maintains enough deletion/restriction control state, separate from erased payload, to fence forgotten data during any restore.

Restore follows this order:

```text
restore old canonical/artifact snapshot
        |
        v
DO NOT SERVE IT YET
        |
        v
apply every newer deletion/restriction control record
        |
        v
reconcile canonical + derived + artifact state
        |
        v
validate fences/settlement
        |
        v
only then activate restored service
```

An old backup can never become authoritative merely because it predates a deletion request.

Backup retention and eventual physical expiry are handled separately from live-data accessibility. If external exports/recipients cannot be controlled, their state is represented honestly as pending/unknown rather than falsely claiming global erasure.

### Settlement proof without payload retention

The final system should be able to prove that a scoped erasure/restriction workflow settled using opaque record/case identities, timestamps/revisions, policy/scope identifiers, reconciliation statuses, and non-content operational evidence where needed, without requiring retention of the erased personal/substantive content itself.

**Reason:** deletion is a multi-plane systems problem. Treating it as a Boolean flag or an ordinary supersession would permit data to survive in embeddings, summaries, caches, artifacts, or restored backups and later reappear.

---

# Open physical-design decisions

1. Detailed PostgreSQL table split for canonical and derived structures.
2. Concurrency, revision/precondition, retry/idempotency, and stale-write protection.
3. Backup/recovery implementation details and coordinated checkpoint manifests.
4. Initial OS process/service identities and permission boundaries.
5. Secret/credential storage and access boundaries.
6. Exact API transport/framework.
7. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should define concurrency/retry safety: optimistic revision preconditions, stable operation/idempotency identities, current-projection transactional updates, generation fencing, and what happens when two clients attempt conflicting corrections or the same request is retried after an uncertain network/tool result.
