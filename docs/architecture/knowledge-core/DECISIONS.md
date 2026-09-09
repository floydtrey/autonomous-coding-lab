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
Valid erasure/restriction fences access first, then reconciles canonical payload, descendants/derivatives, artifacts, backups/restore, and external/exported state where possible. Old backups are never served before newer deletion/restriction controls are reapplied.

## KC-D018 — Canonical writes use optimistic preconditions, stable operation identities, and idempotent retry semantics
**Status:** Accepted
State-dependent writes carry expected revision/preconditions and fail stale rather than silently winning. Stable operation identities make uncertain retries idempotent. Canonical revision identity supports deterministic replay; derived rebuilds use generation fencing.

## KC-D019 — Backup/restore uses coordinated checkpoints and a higher-durability deletion/restriction restore fence
**Status:** Accepted
Backups coordinate PostgreSQL and immutable artifacts through a checkpoint manifest. Minimal deletion/restriction control state has stronger anti-resurrection durability and is reapplied before any restored service is activated. Restore remains non-serving until integrity, restriction, profile, and projection checks pass.

## KC-D020 — Initial same-machine isolation uses separate least-privilege service identities and OS ACL boundaries
**Status:** Accepted
The first Windows deployment uses distinct least-privilege security principals/service identities for Vera/ACL, Knowledge Core, PostgreSQL, Authority, and Effect Executor. NTFS/service ACLs separate trusted install/config, artifact, runtime, policy, and credential access. AI processes do not run as Administrator/LocalSystem in normal operation and cannot rewrite trusted services or policy.

## KC-D021 — Secrets and credentials live outside Knowledge Core and are scoped to the consuming trusted service
**Status:** Accepted
Secrets are not knowledge, prompts, source control, logs, embeddings, or ordinary configuration. Each trusted service receives only its own scoped secrets through a service-specific OS-protected secret provider. Vera/ACL use opaque capability references and never receive downstream Executor credentials. Secret backup/migration is separate and human-controlled.

## KC-D022 — Initial service implementation uses Python 3.12+ with FastAPI/Pydantic over versioned HTTP/JSON
**Status:** Accepted
Knowledge Core initially uses Python 3.12+, FastAPI, Pydantic, and versioned HTTP/JSON. It binds locally by default and becomes network-exposed only with explicit authentication/encryption/firewalling. The typed semantic API remains independent of PostgreSQL and avoids generic CRUD/SQL endpoints.

---

## KC-D023 — V1 physical database uses canonical, control, and derived PostgreSQL schemas with an atomic-proposition assertion model

**Status:** Accepted

The first PostgreSQL implementation follows `PHYSICAL_SCHEMA_V1.md` as the current architecture candidate.

Use one Knowledge Core PostgreSQL database with three physical PostgreSQL schemas:

```text
kc            canonical semantic/history records
kc_control    operational/idempotency/deletion/backup control
kc_derived    rebuildable current/search/semantic projections
```

### Canonical zone

`kc` contains the durable semantic substrate, including the physical equivalents of:

- monotonic canonical revisions;
- universal `knowledge_ref` identity registry;
- entities;
- occurrences;
- assertions;
- typed assertion values;
- governed n-ary participants when needed;
- assertion lifecycle transitions;
- reversible identity transitions;
- typed provenance links;
- logical resources, exact resource versions and mutable locator history;
- semantic profiles/revisions and predicate/kind/role definitions;
- append-oriented record classification history used to rebuild authorization filters.

Ordinary knowledge in `kc` is append-oriented and non-destructive except for the separately governed erasure lifecycle.

### Atomic proposition rule

One ASSERTION row normally represents one atomic proposition occurrence under one exact predicate revision.

Binary relationships are reference-valued assertions. Multi-valued properties normally use multiple assertions. Truly n-ary propositions use explicit governed participant roles rather than opaque arrays/JSON.

Typed values use constrained physical variants such as canonical reference, text, numeric, boolean, date, and timestamp. Profile-governed bounded JSON is the exception, not the default.

### Control zone

`kc_control` stores non-world operational state required to make the service safe and recoverable, including:

- semantic API operation/idempotency records;
- deletion/restriction cases and targets;
- backup checkpoint manifests;
- later maintenance/rebuild control records where useful.

### Derived zone

`kc_derived` stores rebuildable helpers such as:

- current assertion selection;
- current identity resolution;
- current classification/eligibility projection;
- generation/source metadata;
- full-text documents;
- embeddings/vector data when implemented;
- optional inferred relationship closures.

Multiple competing assertions may remain simultaneously current when conflict is unresolved; the physical model must not force false single-valued certainty.

### Identifier strategy

Addressable semantic/control objects use UUID references, with UUIDv7 preferred for new service-generated identifiers on PostgreSQL 18. Canonical mutation ordering uses a separate monotonic `BIGINT` revision identity.

### Minimal erased tombstone

Privileged erasure may remove specialized canonical payload while retaining a minimal opaque `knowledge_ref` tombstone when necessary for anti-resurrection/deletion-control integrity. The tombstone must not retain substantive erased content.

### Derived search

PostgreSQL full-text materialization belongs in `kc_derived`. pgvector embedding rows belong there when semantic retrieval is implemented; vector index choice is benchmarked later and is not required for the first canonical slice.

### Scope of acceptance

This decision accepts the table-family split, semantic constraints, and transaction boundaries in `PHYSICAL_SCHEMA_V1.md`. It does **not** claim every column/table name is permanently frozen before the first DDL validation gates run.

**Reason:** the design is now concrete enough to implement and test without collapsing the conceptual distinctions or introducing unnecessary distributed infrastructure.

---

# Open physical-design decisions

1. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should choose the smallest first implementation vertical slice. It must prove the difficult architecture properties early—append-only correction/reversal, current-view rebuild, bitemporal queries, typed values, provenance to an exact resource version, stale-write/idempotent retry behavior, and service-only access—without implementing Vera, Authority, embeddings, or the full domain vocabulary yet.
