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
Backups coordinate PostgreSQL and required immutable artifacts through a checkpoint manifest. Derived indexes may rebuild. Minimal deletion/restriction control state has stronger anti-resurrection durability and is reapplied before any restored service is activated. Restore remains non-serving until integrity, restriction, profile, and projection checks pass.

---

## KC-D020 — Initial same-machine isolation uses separate least-privilege service identities and OS ACL boundaries

**Status:** Accepted

The first Windows deployment may run Vera, ACL, Knowledge Core, PostgreSQL, Authority, and Effect Executor on one physical computer, but they will not run as one shared fully privileged identity.

The architecture requires distinct security principals/service identities for trust boundaries, mapped initially through Windows service identities/local service accounts/service SIDs and NTFS ACLs as appropriate to the implementation.

### Human administrator

A human-controlled administrator identity owns installation, trusted binary/configuration updates, service registration, OS permission changes, and emergency recovery.

AI-controlled processes do not receive this administrative token as part of normal operation.

### Vera / ACL / worker identities

Vera reasoning and ACL worker processes run without Administrator/LocalSystem authority and have no direct credentials or file permissions for:

- PostgreSQL canonical database administration;
- Knowledge Core database credentials;
- Authority Root policy files beyond any explicitly exposed read result;
- Authority service executable/configuration write access;
- Effect Executor executable/configuration write access;
- downstream action credentials/secrets;
- trusted service installation directories.

ACL workers that execute arbitrary/generated code are treated as the least-trusted ordinary runtime tier. Their project/workspace permissions do not imply permission to modify trusted service binaries, policy, secrets, or OS configuration.

A later VM/container/second-machine boundary may strengthen this isolation without changing the service/API architecture.

### Knowledge Core service identity

Knowledge Core runs under its own service identity. It may:

- connect to PostgreSQL using its scoped application database role;
- read/write the Knowledge Core artifact root;
- write its designated logs/runtime directories;
- call Authority for protected Knowledge Core operations as designed.

It does not receive Authority Root write permission, Effect Executor downstream credentials, PostgreSQL superuser credentials, or arbitrary write access to Vera/ACL workspaces.

The Knowledge Core service binary/configuration install directory should be writable only by the human/admin deployment path, not by the running Knowledge Core service itself unless a narrowly justified update mechanism is designed later.

### PostgreSQL service/database identities

The PostgreSQL server runs under its own service identity and owns its database data directory according to the PostgreSQL/Windows installation model.

Database roles remain separated from OS identity:

- Knowledge Core application role: only runtime SQL privileges required by the service;
- migration/owner role: schema-change privileges, unavailable to ordinary runtime clients and preferably unavailable to the normal Knowledge Core runtime process;
- PostgreSQL administrative role: retained for human/admin maintenance and recovery, never given to Vera/ACL.

Vera and ACL never connect directly to PostgreSQL.

### Authority service identity

Authority runs under a separate least-privilege trusted service identity. It receives read access to the physically read-only Authority Root and only the writable operational state required for authorization decisions/audit.

Vera/ACL cannot write Authority binaries, configuration, policy, or operational database merely because they can submit authorization requests.

### Effect Executor identity

Effect Executor is separate from Authority and Vera. It receives only the downstream credentials/capabilities needed for the action adapters it is responsible for. Vera/ACL do not receive those secrets. Authority decides; Executor performs the specifically authorized operation.

Executor does not receive permission to rewrite root Authority policy.

### File-system ACL model

NTFS ACLs/service SIDs are used so each service sees only the directories/files it requires. Broad write permissions such as granting all AI processes access to a shared application root are rejected.

Writable runtime/log/cache directories are separate from trusted executable/configuration directories.

### No unnecessary LocalSystem

Trusted services should not run as `LocalSystem` merely for convenience. If a specific component later proves it requires a privilege unavailable under a lower-privilege identity, that privilege is added narrowly and documented rather than elevating the whole stack by default.

**Reason:** one physical machine can still have meaningful trust boundaries if the AI cannot modify the policy engine, executor, service binaries, credentials, or database directly. This provides a practical starting boundary while preserving a straightforward upgrade path to stronger VM or physical isolation.

---

# Open physical-design decisions

1. Detailed PostgreSQL table split for canonical and derived structures.
2. Secret/credential storage and access boundaries.
3. Exact API transport/framework.
4. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should define secrets/credential handling: secrets must remain outside Knowledge Core knowledge/context, outside source control, inaccessible to Vera/ACL, and scoped to the service that needs them, while still being practical to rotate, back up, and migrate if Authority/Executor later move to another machine.
