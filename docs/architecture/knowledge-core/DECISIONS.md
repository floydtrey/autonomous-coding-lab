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

---

## KC-D022 — Initial service implementation uses Python 3.12+ with FastAPI/Pydantic over versioned HTTP/JSON

**Status:** Accepted

Knowledge Core's initial service implementation will use the existing repository ecosystem rather than introducing another language/runtime without demonstrated need.

### Runtime/framework

- Python `>=3.12`, aligned with the current Worker Lab runtime baseline;
- FastAPI for the service/application interface;
- Pydantic models for typed request/response validation and generated API schema;
- HTTP/JSON as the initial transport;
- versioned semantic API paths/contracts, beginning with a `/v1` surface or equivalent version marker.

The exact ASGI server/process wrapper may be selected during implementation; it does not change the semantic API decision.

### Local-first binding

Initial deployment binds the Knowledge Core API to loopback/local access by default rather than exposing it broadly on every network interface.

Moving the service to another VM/machine later may enable a network listener with explicit authentication, transport encryption, firewall rules, and service identity/certificate handling. Clients continue using the same semantic API rather than gaining direct PostgreSQL access.

### Typed contract

FastAPI/Pydantic schemas represent semantic request/response objects for the operation classes in KC-D013. The generated OpenAPI contract may be used for client generation/testing, but OpenAPI itself does not become the source of semantic authority; profile and operation rules remain in the architecture/domain model.

### No generic data endpoint

The HTTP layer does not expose generic SQL, arbitrary table CRUD, or a "patch any JSON record" endpoint merely because FastAPI makes it easy to create one.

### Authentication versus authorization

Transport/client authentication proves which service/principal is calling. Authority remains a separate decision boundary for what that principal may read/disclose/mutate/use/automate. The web framework's dependency/authentication features do not replace Authority.

### Streaming is optional

Normal request/response JSON is sufficient for the first vertical slice. SSE, JSON-lines streaming, WebSockets, or gRPC are not introduced until an actual workload requires them.

**Reason:** Python already matches the repository, FastAPI/Pydantic gives a strongly typed and debuggable service boundary with generated documentation/testing support, and ordinary HTTP/JSON is easy to inspect locally while naturally extending across a future VM/machine boundary.

---

# Open physical-design decisions

1. Detailed PostgreSQL table split for canonical and derived structures.
2. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should convert the accepted semantic/storage rules into the first concrete PostgreSQL schema shape: tables for reference identities, entities, assertions and typed values/participants, lifecycle transitions, occurrences, resources/versions/locators, provenance links, semantic profiles/revisions/definitions, operation/idempotency records, deletion-control state, and rebuildable current/derived projections.
