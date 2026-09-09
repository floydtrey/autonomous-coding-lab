# Knowledge Core Architecture Decision Log

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Component:** Knowledge Core  
**Status:** active physical-architecture decision log  

---

# Purpose

This file records accepted physical-architecture decisions for Knowledge Core as they are made.

It is intentionally concise. Detailed architecture documentation will be synthesized after the major structural decisions are complete.

The completed Knowledge Architecture Evidence Campaign under `docs/research/knowledge-architecture/` remains the evidence base. Decisions here must not weaken those requirements merely to fit a preferred implementation technology.

The conceptual primitive families remain semantic roles rather than mandatory database tables:

- ENTITY
- ASSERTION
- OCCURRENCE
- RESOURCE
- EVIDENCE / PROVENANCE LINK
- SEMANTIC PROFILE / VOCABULARY DEFINITION

The governing separation remains:

> **Knowledge does not grant authority. Authority does not prove execution. Execution acknowledgement does not prove world settlement.**

---

# Decision status

- **Accepted** — current architecture decision; later changes require an explicit superseding decision.
- **Open** — deliberately unresolved and still to be designed.
- **Superseded** — retained for history but replaced by a later decision.

Architecture decisions are not silently rewritten when they change. A later decision should explicitly supersede the earlier one so the reasoning remains recoverable.

---

# Accepted decisions

## KC-D001 — Knowledge Core is a standalone service

**Status:** Accepted

Knowledge Core will be designed as its own local/network-capable service rather than as code owned directly by Vera or ACL.

Vera, ACL, and future clients interact with Knowledge Core through a defined interface. They do not directly own or manipulate the canonical knowledge database.

The initial deployment may run on the same physical computer as Vera and ACL, but the interface must allow Knowledge Core to move to another process, VM, or machine later without redesigning its clients.

**Reason:** preserves storage independence, establishes a clean trust/component boundary, supports reuse by multiple clients, and allows later physical isolation.

---

## KC-D002 — PostgreSQL is the initial canonical knowledge store

**Status:** Accepted

PostgreSQL will be the initial physical database for canonical Knowledge Core state.

PostgreSQL is the source of canonical semantic state. Search-oriented structures such as embeddings, vector indexes, full-text indexes, summaries, caches, graph projections, and current-state projections are derived/rebuildable where practical and do not become independent sources of truth merely because they are optimized for retrieval.

This decision does not require the six conceptual primitive families to map one-to-one to six PostgreSQL tables.

**Reason:** the validated architecture requires strong structured constraints, transactions, temporal/history support, provenance, concurrency control, and mixed retrieval without prematurely operating several independent data systems.

---

## KC-D003 — Large artifact bytes live outside PostgreSQL

**Status:** Accepted

Knowledge Core stores canonical RESOURCE identity, metadata, exact observed version/digest, lineage, locators, ownership/sensitivity references, and related semantics in PostgreSQL.

Large raw bytes such as PDFs, images, archives, model files, large source bundles, video, and similar artifacts will normally live outside PostgreSQL in a separately managed artifact/file store.

The exact artifact-storage mechanism remains open.

**Reason:** preserves the conceptual distinction:

`logical resource != locator != representation != exact content/version`

and avoids making the relational database the bulk binary store.

---

## KC-D004 — Authority is a separate deterministic service boundary

**Status:** Accepted

AI reasoning does not grant itself authority.

Vera or another AI/client may request an operation. A separate Authority service evaluates whether that exact operation is permitted for the authenticated principal, purpose, context, policy version, freshness requirements, and relevant obligations.

Knowledge retrieval does not itself grant execution permission.

The Authority service may initially live on the same physical computer, but it must be separable later without redesigning Vera or Knowledge Core.

**Reason:** prevents knowledge, prompt content, model reasoning, or retrieved instructions from becoming authorization merely because the AI can see them.

---

## KC-D005 — Architecture supports a physically read-only Authority Root

**Status:** Accepted

Static or slowly changing root authority material should be capable of living on controller-enforced hardware write-protected media.

Candidate contents include:

- root authority policy;
- trusted-principal definitions or verification roots;
- capability/confirmation rules;
- policy-version metadata;
- cryptographic verification material that does not itself need to be writable during normal operation.

Normal writable operational data such as requests, approvals, denials, attempts, results, audit records, and effect settlement do not belong on the read-only authority medium merely because they relate to authority.

The architecture must not assume physical write protection alone prevents a compromised host from bypassing the Authority service. OS/process isolation and credential separation remain required defense layers.

**Reason:** creates a low-cost physical barrier against software or an AI modifying the root rules that constrain it, while preserving the option to move Authority onto a separate machine later.

---

## KC-D006 — Canonical knowledge history is non-destructive and supports explicit undo/reversal

**Status:** Accepted

Knowledge Core must not normally overwrite prior canonical knowledge in a way that destroys the previous state.

When new information corrects, contradicts, supersedes, invalidates, or replaces earlier knowledge, the system records a new assertion/version/transition while retaining the earlier canonical history and its provenance.

Conceptually:

```text
old assertion/state
        |
        +-- remains historically addressable
        |
        v
new correction/supersession
        |
        v
current projection now selects the newer applicable state
```

If the correction itself is later discovered to be wrong, Knowledge Core requires an explicit **undo/reversal capability**. Undo does not delete the mistaken correction or silently rewrite history. It records another transition that makes the appropriate earlier state (or a newly corrected state) current again while preserving the complete sequence of what happened.

Example:

```text
A1: Robert works_for Acme            recorded Jan 1
A2: Robert works_for BetaCorp        recorded Mar 1, supersedes A1
A3: correction: A2 was erroneous     recorded Mar 2
    current view returns A1 again where applicable

History still contains A1 -> A2 -> A3.
```

This permits rollback/recovery, historical truth and belief queries, auditability, conflict preservation, provenance of corrections, and safe experimentation.

Derived current-state projections may be replaced/rebuilt because they are not canonical history. Privacy erasure is a separate governed process and may intentionally remove/fence data according to deletion requirements; it is not ordinary undo.

**Reason:** an overwrite-only design would destroy fallback state and make mistakes difficult or impossible to reverse safely. The validated architecture requires both world-time history and knowledge/transaction-time history.

---

## KC-D007 — Assertion semantics use typed relational fields with bounded JSON extensibility

**Status:** Accepted

Canonical ASSERTION records must not be implemented as an opaque generic JSON document or an untyped entity-attribute-value bucket.

Semantics that Knowledge Core must reliably query, constrain, authorize against, reconstruct historically, or use for provenance are represented through explicit typed relational fields and/or governed relational child records.

These include assertion identity; governed predicate/profile identity; subject/referent identity; typed object/value; epistemic basis and polarity/value state; world-valid time; record/knowledge time and revision identity; applicability/scope; lifecycle relationships; sensitivity/ownership references; and semantic profile revision.

PostgreSQL `JSONB` may be used as a bounded extension area for profile-specific or uncommon metadata when doing so avoids needless schema churn. JSONB must not replace typed core fields, hide authority-critical semantics, or become an alternate ungoverned source of canonical meaning.

Profile-defined JSON extensions, if canonical, must be validated against the applicable semantic-profile revision so their meaning is explicit and replayable.

The exact table split and exact representation of assertion subjects/objects/participants remain detailed-schema questions.

**Reason:** typed core semantics plus governed bounded extensions preserves correctness and extensibility without creating either a JSON-everything model or a table for every domain concept.

---

## KC-D008 — Canonical records use a universal internal reference registry for cross-family links

**Status:** Accepted

Knowledge Core will use a small physical identity/reference registry so every addressable canonical record can have one stable internal reference regardless of semantic family.

Conceptually:

```text
knowledge_ref
  ref_id
  physical_kind

        +--> entity
        +--> assertion
        +--> occurrence
        +--> resource
        +--> exact resource version
        +--> semantic profile/revision
```

The registry is a physical addressing mechanism, not a seventh conceptual primitive and not evidence that all referenced records have the same semantics.

Specialized canonical tables retain their own typed fields and constraints. Assertions may point to a `subject_ref_id`, reference-valued objects may point to an `object_ref_id`, and provenance links may use the same stable address space.

Scalar assertion values remain typed rather than being converted into fake reference objects. Genuinely multi-part propositions may use governed participant/role records rather than opaque JSON.

A registry reference by itself grants no ownership, truth, sensitivity level, relationship meaning, or authority.

**Reason:** preserves foreign-key integrity across conceptual families while avoiding sprawling family-specific nullable foreign keys or weak application-only polymorphic IDs.

---

## KC-D009 — Temporal model uses independent world-valid time and immutable knowledge-record time

**Status:** Accepted

Knowledge Core will represent at least two independent temporal axes:

1. **World-valid time** — when an assertion is claimed to be true/applicable in the external world.
2. **Knowledge-record time** — when Knowledge Core learned, accepted, or recorded that assertion/transition.

These axes must never be collapsed into one timestamp.

World-valid applicability will use PostgreSQL temporal/range-capable fields where appropriate, normally an interval equivalent to `tstzrange` for timestamp-granularity state. Open-ended applicability is represented explicitly. Source precision/uncertainty must be preserved when evidence only establishes a day, coarse interval, unknown boundary, or other non-exact time.

Every canonical assertion, occurrence, correction, supersession, reversal, and lifecycle transition receives immutable record-time identity including a database-recorded timestamp plus a stable revision/order identity sufficient for deterministic replay.

Late correction appends a new record at the actual knowledge-record time and may carry an earlier world-valid interval. It does not rewrite when the earlier record was learned.

Lifecycle changes are themselves timestamped/revisioned canonical transitions. Historical-belief queries use only records/transitions that existed by the requested knowledge-record time.

The current-state projection is derived/rebuildable and may be maintained transactionally for fast reads.

Absolute instants use timezone-aware timestamps internally; original timezone, date precision, uncertain boundaries, or source temporal wording are retained where materially necessary to avoid false precision.

PostgreSQL temporal constraints may enforce real invariants, but the architecture will not prohibit overlapping world-valid assertion ranges merely because they conflict; conflict is intentionally representable.

**Reason:** supports both "what do we now believe was true at T?" and "what did Knowledge Core believe at T?" while preserving late corrections, conflicts, replay, rollback, and auditability.

---

## KC-D010 — Provenance is a typed, traversable lineage model separate from semantic relationships and lifecycle state

**Status:** Accepted

Knowledge Core will store provenance/evidence as explicit typed directed links among addressable records, anchored to exact source/version and occurrence identity where applicable.

A provenance link has stable identity, source and target references, governed provenance relation type/profile revision, record/revision identity, optional activity/occurrence reference, and bounded qualifiers.

Representative governed relations include `wasDerivedFrom`, `supportedBy`, `wasAttributedTo`, `usedSource`, and `wasGeneratedBy`. Free-text relation names are not sufficient canonical semantics.

Mutable sources must be linked through the exact resource version consumed, not only a mutable URL, path, branch, `latest` alias, or logical resource identity.

Transformation OCCURRENCE records carry the activity context when a process used particular inputs under a particular profile/model/configuration and produced outputs.

Provenance is traversable backward for explanation and forward for impact analysis. Forward impact supports correction, invalidation, deletion/restriction reconciliation, and stale-derivative rebuild.

Provenance does not replace ordinary domain relationships, assertion lifecycle transitions, truth/confidence, sensitivity clearance, permission, or authority.

Derived/rebuildable records retain enough lineage to identify canonical source revisions and derivation/model/profile/configuration revisions.

**Reason:** avoids a single untyped edge model that would blur evidence, domain relationships, correction state, and authority.

---

## KC-D011 — Initial artifact store is a local immutable content-addressed filesystem

**Status:** Accepted

The initial artifact/file store will be a local filesystem directory managed by Knowledge Core rather than a separate object-storage service.

Artifact bytes are stored by cryptographic content digest, initially SHA-256, under a configurable storage root. The content-addressed path is an implementation locator for exact bytes, not the logical RESOURCE identity.

Artifact blobs are immutable after successful ingestion. Changed bytes create a new digest/blob and new RESOURCE-version record rather than modifying the old blob.

PostgreSQL stores logical resource/version metadata, digest, size, media metadata, locators/filenames, ingestion identity, ownership/sensitivity references, provenance, and current artifact-backend locator.

Identical bytes may be physically deduplicated, but hash equality does not merge logical resources, provenance, ownership, sensitivity, authority, or history.

Ingestion should stage bytes, compute/verify digest and size, atomically commit immutable bytes, then commit the PostgreSQL resource-version metadata. Orphaned temporary/unreferenced blobs are reconciled separately.

The storage root is configurable so it may later move to another drive, NAS, or object-storage backend behind the same interface. A separate S3/MinIO-style service is not required initially.

**Reason:** gives immutable exact-version identity, deduplication, reproducibility, integrity checking, straightforward backup, and low operational complexity while preserving a migration path.

---

## KC-D012 — Semantic profiles and vocabulary are immutable, explicitly versioned, and pinned by assertions

**Status:** Accepted

Knowledge Core will represent semantic vocabulary through explicit logical profile identities and immutable profile revisions in PostgreSQL.

At minimum the physical model will distinguish:

- `semantic_profile` — stable logical profile identity, such as the core profile, ACL profile, Vera household/device profile, research profile, or software profile;
- `semantic_profile_revision` — immutable exact revision/snapshot of that profile;
- stable semantic identities for predicates, kinds, participant roles, applicability concepts, and governed inference/validation rules;
- revision-specific definitions of those semantic identities.

Every assertion and other record whose interpretation depends on vocabulary must retain the exact profile revision under which it was created/interpreted. A mutable "current profile" pointer may be used for new writes, but old records are never reinterpreted merely because that pointer changes.

Compatible metadata/documentation changes may create a new profile revision while retaining the same stable predicate/kind semantic identity. A **material meaning change** creates a new semantic identity or explicit migration/mapping rather than silently redefining the old identifier.

Profile dependencies/imports must be pinned to exact revisions rather than mutable `latest` references where those dependencies affect interpretation.

Profile revisions are immutable once activated for canonical use. Changes are introduced as new revisions. Deprecation does not delete historical definitions.

If existing assertions are intentionally transformed to a new semantic meaning/profile, that transformation is explicit, provenance-bearing, and replayable; it creates new records/derivations rather than retroactively rewriting the old assertions.

Profile-specific validation schemas or bounded extension definitions may use structured JSON where useful, but the profile revision that governs them remains explicit and immutable.

The universal core will not add `HomeAssistantEntity`, `GitCommit`, `ACLWorker`, `EmailThread`, or similar domain-specific primitives. Those meanings are introduced through domain profiles over the existing core.

**Reason:** this lets Vera, ACL, research, software, devices, and future domains evolve independently while preserving historical meaning and preventing vocabulary changes from silently changing the interpretation of old knowledge.

---

# Open physical-design decisions

These remain deliberately unresolved and should be decided before freezing the deep Knowledge Core folder/package layout:

1. Detailed PostgreSQL table split for entities, assertions, occurrences, resources, resource versions, semantic profiles, assertion values/participants, reference-registry subtype constraints, provenance links, and lifecycle transitions.
2. Knowledge Core service API and operation classes.
3. Retrieval pipeline: structured, relationship, full-text, semantic, composite, and context-construction boundary.
4. Derived-data generation, invalidation, rebuild, and versioning.
5. Identity-resolution workflow, ambiguity, merge/split, replacement, and reversal mechanics.
6. Deletion/retention/reconciliation workflow across canonical and derived planes.
7. Concurrency, revision/precondition, and stale-write protection.
8. Backup, recovery, restore, and deletion-ledger reconciliation.
9. Initial OS process/service identities and permission boundaries.
10. Secret/credential storage and access boundaries.
11. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

During physical architecture design:

1. Record meaningful accepted decisions here as they are made.
2. Do not rewrite previous decisions silently; supersede them explicitly when necessary.
3. Avoid building a deep code/folder skeleton before the structural decisions that determine it are settled.
4. After the major physical-design decisions are complete, perform one bounded documentation synthesis pass covering final service/component boundaries, data flows, PostgreSQL physical design, artifact storage, security/authority boundaries, API boundaries, package/folder layout, backup/recovery, and build/validation order.

---

# Current next decision

The next design discussion should define the Knowledge Core service API by semantic operation classes rather than exposing generic database CRUD. It must keep read/search/explain, append knowledge, correction/reversal, identity transitions, resource ingestion, and privacy/deletion operations distinct so Authority can govern them separately.
