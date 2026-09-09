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

This permits:

- rollback/recovery from mistaken updates;
- historical truth queries;
- historical-belief queries;
- auditability;
- conflict preservation;
- provenance of corrections;
- safe experimentation and early implementation changes.

Derived current-state projections may be replaced/rebuilt because they are not canonical history. Privacy erasure is also a separate governed process and may intentionally remove/fence data according to deletion requirements; it is not ordinary "undo."

**Reason:** an overwrite-only design would destroy fallback state and make mistakes difficult or impossible to reverse safely. The validated architecture requires both world-time history and knowledge/transaction-time history.

---

## KC-D007 — Assertion semantics use typed relational fields with bounded JSON extensibility

**Status:** Accepted

Canonical ASSERTION records must not be implemented as an opaque generic JSON document or an untyped entity-attribute-value bucket.

Semantics that Knowledge Core must reliably query, constrain, authorize against, reconstruct historically, or use for provenance are represented through explicit typed relational fields and/or governed relational child records.

These include at minimum the physical equivalents of:

- assertion identity;
- governed predicate/profile identity;
- subject/referent identity;
- typed object/value identity or scalar value;
- epistemic basis and polarity/value state;
- world-valid time;
- record/knowledge time and revision identity;
- applicability/scope needed for selection;
- lifecycle/currentness/supersession relationships;
- sensitivity/ownership classification references used by external policy;
- semantic profile revision.

PostgreSQL `JSONB` may be used as a **bounded extension area** for profile-specific or uncommon metadata when doing so avoids needless schema churn. JSONB must not replace the typed core fields above, hide authority-critical semantics, or become an alternate ungoverned source of canonical meaning.

Profile-defined JSON extensions, if canonical, must be validated against the applicable semantic-profile revision so their meaning is explicit and replayable.

The exact table split and the exact representation of assertion subjects/objects/participants remain open; this decision establishes the typing boundary, not the final SQL schema.

**Reason:** a JSON-everything design is initially convenient but would make temporal queries, constraints, conflict handling, provenance, authorization filtering, migrations, and indexing increasingly dependent on application conventions. A fully rigid table for every domain concept would create the opposite problem. Typed core semantics plus governed bounded extensions preserves both correctness and extensibility.

---

## KC-D008 — Canonical records use a universal internal reference registry for cross-family links

**Status:** Accepted

Knowledge Core will use a small physical identity/reference registry so every addressable canonical record can have one stable internal reference regardless of its semantic family.

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

The registry is a **physical addressing mechanism**, not a seventh conceptual knowledge primitive and not evidence that all referenced records have the same semantics.

Specialized canonical tables retain their own typed fields and constraints. Their primary identity is tied to a valid registry reference of the appropriate physical kind.

Assertions may therefore point safely to a `subject_ref_id`, and reference-valued assertion objects may point to an `object_ref_id`, without using unsafe application-only polymorphic pairs such as `subject_type='entity', subject_id=123` that PostgreSQL cannot fully validate with ordinary foreign keys.

The same reference mechanism may also be used by provenance/evidence links where a source or target can legitimately belong to different canonical families.

Scalar assertion values remain typed rather than being converted into fake reference objects merely for uniformity. The physical assertion-value representation should support governed types such as text, number, boolean, date/time and canonical-record reference, with constraints ensuring the declared type and populated value agree.

For genuinely multi-part or n-ary propositions, additional governed participant/role records may be used rather than serializing the proposition into opaque JSON. The exact participant/value table layout remains part of detailed schema design.

A registry reference by itself grants no ownership, truth, sensitivity level, relationship meaning or authority. Those remain properties of the referenced semantic records and external policy.

**Reason:** this preserves relational foreign-key integrity across the six conceptual families while avoiding both a sprawling matrix of nullable family-specific foreign keys and weak polymorphic IDs validated only by application code. It also gives provenance and assertion references one stable address space without turning the canonical model into an untyped graph.

---

## KC-D009 — Temporal model uses independent world-valid time and immutable knowledge-record time

**Status:** Accepted

Knowledge Core will represent at least two independent temporal axes:

1. **World-valid time** — when an assertion is claimed to be true or applicable in the external world.
2. **Knowledge-record time** — when Knowledge Core learned, accepted, or recorded that assertion/transition.

These axes must never be collapsed into one timestamp.

World-valid applicability will use PostgreSQL temporal/range-capable fields where appropriate, normally an interval equivalent to `tstzrange` for timestamp-granularity state. Open-ended applicability is represented explicitly rather than by inventing a distant future date. The schema must preserve source precision/uncertainty when the evidence only establishes a day, coarse interval, unknown boundary, or other non-exact time.

Every canonical assertion, occurrence, correction, supersession, reversal, and other lifecycle transition receives immutable record-time identity including:

- a database-recorded timestamp; and
- a stable revision/order identity sufficient to deterministically order/replay records when timestamps alone are not enough.

Ordinary correction does not update an old assertion to make it appear that Knowledge Core knew the corrected fact earlier. Instead, a new record is appended at the actual knowledge-record time and may carry an earlier world-valid interval.

Example:

```text
May 15 world time:   Robert actually started at Contoso
June 2:              Knowledge Core records "Robert started June 2"
September 8:         correction arrives saying the start was May 15

Current historical reconstruction:
  May 15 onward -> Contoso

Historical belief as of July 1:
  Knowledge Core still believed June 2

The September correction does not rewrite the June record time.
```

Lifecycle changes such as `supersedes`, `invalidates`, `corrects`, or `restores` are themselves timestamped/revisioned canonical transitions. Historical-belief queries reconstruct state using only canonical records/transitions that existed by the requested knowledge-record time.

The **current-state projection is derived and rebuildable**. It may be maintained transactionally for fast reads, but it is not the only record of history and may be regenerated from canonical assertions plus lifecycle transitions.

Internally, absolute instants should use timezone-aware timestamps. Original timezone, date-only precision, uncertain boundaries, or source temporal wording are retained where materially necessary for faithful interpretation rather than being silently promoted to false precision.

PostgreSQL temporal constraints may be used where they enforce a real semantic invariant, but the architecture will not assume that every assertion for a subject/predicate must have non-overlapping world-valid ranges because conflicting assertions are intentionally representable.

**Reason:** this directly supports both "what do we now believe was true at T?" and "what did Knowledge Core believe at T?" while preserving late corrections, conflicts, replay, rollback, and auditability. It also avoids forcing expensive historical reconstruction into every ordinary current-state query.

---

## KC-D010 — Provenance is a typed, traversable lineage model separate from semantic relationships and lifecycle state

**Status:** Accepted

Knowledge Core will store provenance/evidence as explicit typed directed links among addressable records, anchored to exact source/version and occurrence identity where applicable.

A provenance link has physical equivalents of:

- stable link identity;
- source reference;
- target reference;
- governed provenance relation type and semantic-profile revision;
- record/revision identity;
- optional occurrence/activity reference that explains the derivation or attribution event;
- bounded qualifiers required by the governed relation.

Representative governed provenance relations include concepts such as:

- `wasDerivedFrom`;
- `supportedBy`;
- `wasAttributedTo`;
- `usedSource`;
- `wasGeneratedBy`.

Free-text relation names are not sufficient canonical provenance semantics.

Where a source is mutable, provenance must point to the **exact resource version/representation consumed**, not only to a mutable URL, file path, branch name, `latest` alias, or logical resource identity.

Transformation/derivation OCCURRENCE records should be used when the system needs to explain that a process used particular inputs under a particular profile/model/configuration and produced particular outputs. This avoids pretending that a direct source-to-output edge captures the full activity context.

Provenance links are indexed/traversable in both directions so Knowledge Core can answer:

- backward explanation: "What evidence/source/activity produced this?"
- forward impact: "What assertions, summaries, extractions, embeddings, or other derivatives depend on this source/version?"

Forward impact is required for correction, invalidation, deletion/restriction reconciliation, and rebuilding stale derived data.

Provenance is **not** used as the canonical mechanism for ordinary domain relationships such as `works_for` or `located_in`; those remain governed ASSERTION semantics. It is also not the lifecycle mechanism for `supersedes`, `corrects`, `invalidates`, or `restores` when those transitions determine assertion currentness. Those lifecycle transitions remain explicitly distinguishable even when they themselves have provenance.

Likewise, provenance never grants truth, confidence, sensitivity clearance, permission, or execution authority merely because one record points to another.

Derived/rebuildable records must retain sufficient lineage metadata to identify their canonical source revision(s), derivation/generation identity, and profile/model/configuration revision even when the derived payload itself is stored outside the canonical tables.

**Reason:** a single untyped "edges" table would blur evidence, domain relationships, correction state, and authority. Typed lineage plus occurrence anchoring preserves explanation and impact analysis while keeping those semantics separate.

---

## KC-D011 — Initial artifact store is a local immutable content-addressed filesystem

**Status:** Accepted

The initial artifact/file store will be a local filesystem directory managed by Knowledge Core rather than a separate object-storage service.

Artifact bytes are stored by cryptographic content digest, initially SHA-256, under a configurable storage root. The on-disk content-addressed path is an implementation locator for exact bytes; it is not the logical RESOURCE identity.

Conceptually:

```text
artifact-root/
  sha256/
    ab/
      cd/
        abcdef...full-digest
```

Exact directory fan-out may change during implementation without changing this decision.

Artifact blobs are immutable after successful ingestion. Changed bytes create a new digest/blob and a new RESOURCE-version record rather than modifying the old blob in place.

PostgreSQL stores the canonical logical resource/version metadata, including at minimum:

- logical RESOURCE identity;
- exact resource-version identity;
- content digest and digest algorithm;
- byte size;
- media/type metadata;
- original/mutable locator(s) and filenames where relevant;
- observation/ingestion identity;
- ownership/sensitivity references;
- provenance/derivation links;
- current artifact-store locator/backend identity.

Identical bytes may be physically deduplicated to one content-addressed blob, but **hash equality does not merge logical resources, provenance, ownership, sensitivity, authority, or history**. Multiple logical/resource-version records may legitimately reference the same digest.

The ingestion order should prefer:

1. write to a temporary/staging location;
2. compute and verify digest/size;
3. atomically move/commit immutable bytes to the final content-addressed location;
4. commit the PostgreSQL resource-version metadata that references the completed blob;
5. reconcile/garbage-collect orphaned temporary or unreferenced blobs separately.

This ordering prefers a harmless orphaned blob after a crash over a canonical database record that points to bytes that were never durably committed.

The artifact storage root must be configurable so it may later move to another local drive, NAS, or object-storage backend behind the same Knowledge Core storage interface.

A separate S3/MinIO-style service is not required initially. It should be introduced only if measured capacity, replication, remote access, concurrency, or operations requirements justify the added complexity.

**Reason:** a content-addressed local store gives immutable exact-version identity, deduplication, reproducibility, integrity checking, straightforward backup, and low operational complexity while preserving a clean migration path to another backend later.

---

# Open physical-design decisions

These remain deliberately unresolved and should be decided before freezing the deep Knowledge Core folder/package layout:

1. Detailed PostgreSQL table split for entities, assertions, occurrences, resources, resource versions, semantic profiles, assertion values/participants, reference-registry subtype constraints, provenance links, and lifecycle transitions.
2. Semantic-profile/vocabulary physical representation and migration rules.
3. Knowledge Core service API and operation classes.
4. Retrieval pipeline: structured, relationship, full-text, semantic, composite, and context-construction boundary.
5. Derived-data generation, invalidation, rebuild, and versioning.
6. Identity-resolution workflow, ambiguity, merge/split, replacement, and reversal mechanics.
7. Deletion/retention/reconciliation workflow across canonical and derived planes.
8. Concurrency, revision/precondition, and stale-write protection.
9. Backup, recovery, restore, and deletion-ledger reconciliation.
10. Initial OS process/service identities and permission boundaries.
11. Secret/credential storage and access boundaries.
12. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

During physical architecture design:

1. Record meaningful accepted decisions here as they are made.
2. Do not rewrite previous decisions silently; supersede them explicitly when necessary.
3. Avoid building a deep code/folder skeleton before the structural decisions that determine it are settled.
4. After the major physical-design decisions are complete, perform one bounded documentation synthesis pass covering:
   - final service/component boundaries;
   - data flows;
   - PostgreSQL physical design;
   - artifact storage;
   - security and authority boundaries;
   - API boundaries;
   - package/folder layout;
   - backup/recovery;
   - build order and validation gates.

---

# Current next decision

The next design discussion should define how SEMANTIC PROFILE / VOCABULARY definitions are physically versioned and activated. The design must let ACL, Vera, research, device, software, and future domains add governed predicates/kinds without changing the universal core or retroactively changing the meaning of old assertions.
