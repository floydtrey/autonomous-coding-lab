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

# Open physical-design decisions

These remain deliberately unresolved and should be decided before freezing the deep Knowledge Core folder/package layout:

1. Detailed PostgreSQL table split for entities, assertions, occurrences, resources, resource versions, semantic profiles, assertion values/participants, and reference-registry subtype constraints.
2. Exact temporal representation for world-valid time, transaction/knowledge time, current projections, corrections, and supersession.
3. Provenance-link physical representation and traversal strategy.
4. Artifact/file-store mechanism and content/version layout.
5. Semantic-profile/vocabulary physical representation and migration rules.
6. Knowledge Core service API and operation classes.
7. Retrieval pipeline: structured, relationship, full-text, semantic, composite, and context-construction boundary.
8. Derived-data generation, invalidation, rebuild, and versioning.
9. Identity-resolution workflow, ambiguity, merge/split, replacement, and reversal mechanics.
10. Deletion/retention/reconciliation workflow across canonical and derived planes.
11. Concurrency, revision/precondition, and stale-write protection.
12. Backup, recovery, restore, and deletion-ledger reconciliation.
13. Initial OS process/service identities and permission boundaries.
14. Secret/credential storage and access boundaries.
15. The first implementation vertical slice and its validation gates.

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

The next design discussion should settle the exact temporal representation: how PostgreSQL distinguishes when something was true in the world from when Knowledge Core learned/recorded it, how corrections preserve both histories, and how a fast current projection is rebuilt from canonical history.
