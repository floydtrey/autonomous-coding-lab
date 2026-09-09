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

PostgreSQL is the initial source of canonical semantic state. Search indexes, embeddings, summaries, caches, graph projections, and current-state projections are derived/rebuildable where practical. The six conceptual families need not map one-to-one to six tables.

## KC-D003 — Large artifact bytes live outside PostgreSQL
**Status:** Accepted

PostgreSQL stores RESOURCE identity, metadata, exact version/digest, lineage, locators, ownership/sensitivity references, and semantics; large raw bytes live in a separately managed artifact store.

## KC-D004 — Authority is a separate deterministic service boundary
**Status:** Accepted

AI reasoning requests operations but does not grant authority. Authority evaluates the exact operation for authenticated principal, purpose, context, policy revision, freshness, and obligations. Retrieval never itself grants execution permission.

## KC-D005 — Architecture supports a physically read-only Authority Root
**Status:** Accepted

Static/slow-changing root authority policy and verification material can live on controller-enforced write-protected media. Writable operational authority/effect history remains elsewhere. Physical protection supplements, not replaces, process/OS/credential isolation.

## KC-D006 — Canonical knowledge history is non-destructive and supports explicit undo/reversal
**Status:** Accepted

Ordinary learning/correction appends new assertion/version/transition records rather than destroying prior canonical state. Undo/reversal is another explicit transition that can restore an earlier state as current without erasing mistaken intermediate history. Privacy erasure is separate.

## KC-D007 — Assertion semantics use typed relational fields with bounded JSON extensibility
**Status:** Accepted

Canonical ASSERTION semantics that matter for query, history, provenance, constraints, or authority use explicit typed relational fields/children. `JSONB` is only a bounded, profile-governed extension area and may not replace core semantics or hide authority-critical meaning.

## KC-D008 — Canonical records use a universal internal reference registry for cross-family links
**Status:** Accepted

A small physical reference registry provides stable internal addressing across canonical Entity, Assertion, Occurrence, Resource/version, and Semantic Profile/revision records. Specialized tables retain their own semantics/constraints; the registry is not a seventh conceptual primitive or untyped graph.

## KC-D009 — Temporal model uses independent world-valid time and immutable knowledge-record time
**Status:** Accepted

Knowledge Core separately records when a claim applies in the world and when Knowledge Core learned/recorded it. Late corrections append at the real record time with their supported world-valid interval. Current state is derived/rebuildable; historical belief remains reconstructable.

## KC-D010 — Provenance is a typed, traversable lineage model separate from semantic relationships and lifecycle state
**Status:** Accepted

Evidence/provenance uses governed typed directed links, exact source versions, and occurrence/activity context. It supports backward explanation and forward impact. It never substitutes for domain relationships, correction/currentness state, truth/confidence, sensitivity clearance, permission, or authority.

## KC-D011 — Initial artifact store is a local immutable content-addressed filesystem
**Status:** Accepted

Initial artifact bytes live in a configurable local filesystem store keyed by SHA-256. Blobs are immutable; changed bytes create new versions. Identical bytes may deduplicate physically but do not merge logical identity/provenance/ownership/history. Backend may later move to another drive, NAS, or object store.

## KC-D012 — Semantic profiles and vocabulary are immutable, explicitly versioned, and pinned by assertions
**Status:** Accepted

Logical profiles have immutable exact revisions. Assertions pin the governing revision. Material meaning changes create new semantic identity or explicit migration/mapping rather than silently redefining old semantics. Old records never change meaning because a new profile becomes active.

## KC-D013 — Knowledge Core API exposes semantic operation classes, not generic CRUD or database access
**Status:** Accepted

Clients use meaningful operation families: read/search/explain, append assertion/occurrence/resource/evidence, correction/reversal, identity transition, and privileged restriction/erasure/profile administration. Clients receive no DB credentials, cannot set trusted record-time identity, and cannot issue arbitrary field updates. Responses remain structured and provenance/temporal/conflict-aware.

## KC-D014 — Retrieval is an authorization-first composite pipeline; context construction is a final derived step
**Status:** Accepted

Retrieval carries authenticated principal, purpose/use, and explicit query mode. Hard authority/sensitivity eligibility precedes protected model-facing exposure. Structured/temporal filtering, relationship traversal, full-text/semantic candidate generation, provenance/conflict/currentness evaluation, reranking, and final context construction remain distinguishable. Rank is relevance, not truth/permission/currentness.

## KC-D015 — Derived data is generation-versioned, lineage-bound, explicitly staleable, and rebuildable
**Status:** Accepted

Current-state projections, extracted text, chunks, summaries, FTS materializations, embeddings/vector indexes, relationship closures, aggregates, caches, and context-supporting projections remain derived. Each retains source revision(s), generation identity, relevant profile/model/configuration revision, lifecycle/staleness state, and enough lineage for rebuild/restriction/deletion propagation. New generations build separately and replace settled generations only after validation.

---

## KC-D016 — Identity resolution is non-destructive, transition-based, and reversible

**Status:** Accepted

ENTITY records have stable internal identities independent of names, usernames, email addresses, device registry IDs, paths, IPs, room assignments, or other external identifiers.

External identifiers, aliases, labels, and same-identity clues are evidence/assertions with source namespace and provenance; they are not automatically universal identity.

Knowledge Core must explicitly represent at least these identity-resolution states:

- unresolved/ambiguous candidate;
- resolved different;
- resolved same/equivalent for a stated scope/time;
- merge/equivalence transition;
- split/reversal of a mistaken merge;
- replacement/succession where old and new remain distinct entities;
- reassignment of an external identifier or alias.

A merge/resolved-same operation **does not** rewrite every assertion foreign key from one entity to another and does not delete the losing entity record. Instead it appends a canonical identity-resolution transition with:

- the involved entity references;
- transition type;
- record time/revision;
- world-valid/applicability scope where relevant;
- provenance/evidence;
- authenticated/authorized operation context reference where required.

A derived current identity-resolution projection may choose a representative/current equivalence set for fast lookup. Queries over a currently merged identity can union or otherwise compose knowledge attached to the underlying entity records according to the active resolution state.

Because original entities and their assertions remain intact, reversing a mistaken merge does not require reconstructing which rows were physically moved. A split/reversal appends a new transition invalidating or superseding the prior resolution. Current identity projections then rebuild/recompute.

Assertions are not automatically reattributed simply because an identity resolution changes. If evidence shows a particular assertion belonged to the wrong underlying entity, that reattribution/correction is explicit and provenance-bearing.

Replacement is not treated as equivalence. For example, replacing a physical thermostat, vehicle, account, or worker process creates/uses a distinct ENTITY plus a governed `replaced_by`/successor relationship or identity transition; the history of the old thing remains attached to the old entity.

Identity candidate scores, fuzzy name matches, embedding similarity, or shared identifiers are **candidate evidence**, not final identity truth. Automated resolution may only create a canonical resolution transition when the applicable policy/rules permit it; ambiguity remains representable otherwise.

**Reason:** destructive identity merge is one of the hardest errors to undo in a knowledge system. Transition-based resolution preserves provenance, reversibility, historical belief, and downstream repair while allowing a fast current identity view.

---

# Open physical-design decisions

1. Detailed PostgreSQL table split for canonical and derived structures.
2. Deletion/retention/reconciliation workflow.
3. Concurrency, revision/precondition, retry/idempotency, and stale-write protection.
4. Backup, recovery, restore, and deletion-ledger reconciliation.
5. Initial OS process/service identities and permission boundaries.
6. Secret/credential storage and access boundaries.
7. Exact API transport/framework.
8. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should define privacy deletion/restriction/retention as a multi-stage reconciliation workflow: immediate retrieval fencing, canonical handling, descendant/derived cleanup, artifact handling, backup/restore behavior, settlement proof, and the limited metadata that may remain after erasure without retaining the erased content itself.
