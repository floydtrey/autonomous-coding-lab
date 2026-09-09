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

## KC-D018 — Canonical writes use optimistic preconditions, stable operation identities, and idempotent retry semantics
**Status:** Accepted
Writes that depend on current state carry expected revision/preconditions and fail stale rather than silently winning. Externally requested mutations use stable operation/idempotency identities so uncertain retries return the prior result rather than duplicate semantic intent. Canonical revision identity supports deterministic replay; current projections and required synchronous updates commit transactionally; derived rebuilds use generation fencing.

---

## KC-D019 — Backup/restore uses coordinated checkpoints and a higher-durability deletion/restriction restore fence

**Status:** Accepted

Knowledge Core backups are coordinated across canonical PostgreSQL state and the content-addressed artifact store rather than treating them as unrelated copies.

A backup checkpoint/manifest records enough identity to prove what was captured, including at least:

- Knowledge Core schema/migration revision;
- canonical PostgreSQL revision/high-water mark and database backup identity;
- artifact-store backend identity and a manifest/verification state for blobs required by the captured canonical revision;
- semantic-profile revision state needed to interpret the captured records;
- deletion/restriction-control high-water mark available at backup time;
- backup creation/verification status.

Because artifact blobs are immutable/content-addressed, artifact backup can be incremental and independently verified by digest. A database checkpoint must not be considered recoverable until all artifact blobs referenced by that checkpoint are either present in the backup set or explicitly classified as external/recoverable by another governed mechanism.

### Derived indexes are rebuildable

Full-text/vector indexes, embeddings, summaries, relationship closures, current-state projections, and other derived structures do not have to be authoritative backup payloads if they can be deterministically rebuilt from the captured canonical state and required model/profile/configuration artifacts.

They may optionally be backed up for faster recovery, but a restored copy remains derived and must match its recorded source/generation revision before use.

### Deletion/restriction control has stronger anti-resurrection durability

A restore from an older snapshot can legitimately lose newer ordinary knowledge according to the chosen recovery-point objective. It must **not** resurrect knowledge that was validly deleted or restricted after that snapshot.

Therefore the minimal deletion/restriction control ledger required to fence erased/restricted records is backed up or replicated separately with a higher durability/freshness target than ordinary periodic Knowledge Core snapshots.

That control copy contains only the minimum non-content identifiers/status needed to reapply restrictions and prevent resurrection; it does not become a duplicate store of erased payload.

### Restore is staged and non-serving

A restored Knowledge Core remains offline/non-serving until this sequence settles:

```text
restore PostgreSQL checkpoint
restore/verify required artifact blobs
        |
        v
apply every deletion/restriction control record newer than checkpoint
        |
        v
verify schema + semantic-profile compatibility
        |
        v
reconcile canonical/artifact restrictions
        |
        v
rebuild or validate current-state + derived generations
        |
        v
run integrity/acceptance checks
        |
        v
activate service
```

No model/client can query the restored database during the unsafe pre-fence stage.

### Authority and secrets are separate backup domains

The physically read-only Authority Root, Authority/Effect operational state, and service credentials/secrets are not silently bundled into Knowledge Core backups. They have separate backup/recovery procedures appropriate to their trust and secrecy requirements, while the coordinated restore manifest records any required compatible authority/policy version identifiers.

### Recovery must be tested

A backup procedure is not considered complete merely because files were copied. The implementation plan must include periodic restore tests that verify:

- PostgreSQL recovery;
- artifact digest completeness;
- deletion/restriction anti-resurrection;
- semantic-profile interpretability;
- derived projection rebuild;
- current/historical query behavior;
- service activation gates.

Exact RPO/RTO, backup schedule, PostgreSQL backup tooling, media, encryption, and off-machine/off-site replication frequency remain deployment choices.

**Reason:** the system's safety depends not only on recovering data, but on recovering the *right historical state* without reviving forgotten data or serving partially reconciled projections.

---

# Open physical-design decisions

1. Detailed PostgreSQL table split for canonical and derived structures.
2. Initial OS process/service identities and permission boundaries.
3. Secret/credential storage and access boundaries.
4. Exact API transport/framework.
5. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should define initial same-machine process/service identities and OS permissions: which account owns PostgreSQL, which account runs Knowledge Core, which accounts run Vera/ACL, which account can read/write the artifact store, and how Authority/Effect Executor remain inaccessible to AI-controlled processes even before any VM or second machine is introduced.
