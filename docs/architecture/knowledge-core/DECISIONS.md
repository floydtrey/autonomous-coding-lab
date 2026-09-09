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
Entity IDs stay stable. Aliases/identifiers are evidence, not identity. Merge/split/replacement/reassignment are explicit provenance-bearing transitions; merges do not destructively rewrite underlying assertions.

## KC-D017 — Privacy deletion/restriction is a privileged staged reconciliation lifecycle, not ordinary supersession
**Status:** Accepted
Valid erasure/restriction fences access first, then reconciles canonical payload, descendants/derivatives, artifacts, backups/restore, and external/exported state where possible. Minimal non-content control state may remain to prevent resurrection and prove scoped settlement. Old backups are never served before newer deletion/restriction controls are reapplied.

---

## KC-D018 — Canonical writes use optimistic preconditions, stable operation identities, and idempotent retry semantics

**Status:** Accepted

Knowledge Core will not use silent last-writer-wins behavior for semantically conflicting canonical changes.

### Stable operation identity

Every externally requested mutation receives a stable `operation_id` / idempotency identity scoped to the authenticated caller/action class.

If a client experiences an uncertain result, such as a network timeout after submitting a write, it retries using the **same operation identity**.

Knowledge Core must then:

- return the already-settled result if that operation previously committed successfully with the same canonical request payload;
- continue/return the known pending state if the operation is still legitimately in progress;
- return the prior failure if it is terminal and retry semantics do not permit a new attempt under the same identity;
- reject reuse of the same operation identity with materially different request semantics/payload.

This prevents a timeout from becoming a duplicate assertion, duplicate correction, duplicate identity transition, or duplicate deletion request.

### Optimistic revision/precondition checks

Operations that depend on a particular current state—correction, supersession, reversal, identity transition, classification change, profile activation, deletion/restriction scope change, etc.—carry an `expected_revision`, expected current target reference, or equivalent semantic precondition.

The service checks that precondition inside the same PostgreSQL transaction that appends the new canonical record/transition.

If the expected state is stale, the operation fails as a **conflict/stale-precondition result** rather than silently applying to a different current state.

Example:

```text
Revision 100: A1 is current

Vera reads revision 100
ACL reads revision 100

Vera corrects A1 -> A2 with expected revision 100
commit produces revision 101

ACL attempts A1 -> A3 with expected revision 100
Knowledge Core returns STALE/CONFLICT
ACL must reread revision 101 and reconsider
```

Independent append-only claims that do not require exclusive current-state assumptions may proceed concurrently; the model should not serialize all knowledge writes unnecessarily.

### Canonical revision/order identity

Committed canonical mutations receive stable record/revision identity sufficient for deterministic replay/order. Timestamp alone is not relied upon to establish total ordering where multiple writes may occur at the same timestamp resolution.

### Current projection transactionality

When a canonical write has a synchronous current-state/identity projection update, both commit in one PostgreSQL transaction or the canonical write remains authoritative and the projection is clearly marked/rebuilt. The service may not return a settled success that implies a new current state while knowingly committing only half of a required transactional pair.

### Generation fencing

Background derived rebuilds use the generation-fencing rule from KC-D015. A worker building from source revision N cannot overwrite a newer settled generation built from revision N+1 merely because the older job finishes later.

### No ambiguous replay as new semantic intent

A fresh attempt after a terminal conflict or intentional user/model reconsideration receives a **new operation identity** and explicitly references the newer base revision. Reusing the old operation ID is reserved for retry/recovery of the same semantic intent.

### Database locks are an implementation detail

PostgreSQL transactions, constraints, row/advisory locks, and isolation levels may be selected per operation during implementation. The architecture requirement is semantic: preconditions and idempotency must be enforced atomically. A global lock over all Knowledge Core writes is not required.

**Reason:** autonomous clients, network retries, background workers, and late-arriving evidence make concurrency inevitable. Stable operation identity plus optimistic preconditions prevents duplicated intent and stale writers without sacrificing append throughput.

---

# Open physical-design decisions

1. Detailed PostgreSQL table split for canonical and derived structures.
2. Backup/recovery implementation details and coordinated checkpoint manifests.
3. Initial OS process/service identities and permission boundaries.
4. Secret/credential storage and access boundaries.
5. Exact API transport/framework.
6. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should define backup/recovery as a coordinated Knowledge Core checkpoint: PostgreSQL canonical state, content-addressed artifacts, immutable semantic-profile revisions, deletion/restriction control state, and the rules for excluding/rebuilding derived indexes while proving a restored system is safe before it serves requests.
