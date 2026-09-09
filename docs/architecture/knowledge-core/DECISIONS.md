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
The first Windows deployment uses distinct least-privilege security principals/service identities for Vera/ACL, Knowledge Core, PostgreSQL, Authority, and Effect Executor. NTFS/service ACLs separate trusted install/config, artifact, runtime, policy, and credential access. AI processes do not run as Administrator/LocalSystem in normal operation and cannot rewrite trusted services or policy. Stronger VM/machine isolation may be added later without redesign.

---

## KC-D021 — Secrets and credentials live outside Knowledge Core and are scoped to the consuming trusted service

**Status:** Accepted

Passwords, API tokens, OAuth refresh/access tokens, database administrative credentials, private cryptographic keys, device/home/car service credentials, remote-service cookies/tokens, and similar secret material are **not Knowledge Core knowledge**.

They must not be stored in:

- canonical ASSERTION/RESOURCE payloads merely because Vera knows a service exists;
- embeddings, summaries, chunks, vector/full-text indexes, or context packages;
- model prompts or conversational context;
- source control or committed configuration files;
- ordinary logs, traces, error messages, crash reports, or provenance payloads;
- the hardware read-only Authority Root unless a specific secret is deliberately designed to reside there and can be used without exposing it to AI/client processes.

Knowledge Core may store **non-secret references/metadata** such as `credential_ref=toyota_primary`, credential type, owning service, rotation timestamp/version, or capability identifier when needed for orchestration/audit, but the secret value itself remains in the trusted secret provider.

### Service-scoped secret ownership

Secrets are divided by the service that actually needs them:

- **Knowledge Core** — only its runtime PostgreSQL application credential and any narrowly required storage/service credentials;
- **Authority** — only secrets needed for Authority authentication/verification/operational state; static public verification roots may live on read-only media because they are not secret;
- **Effect Executor** — downstream action credentials for the adapters it executes, scoped as narrowly as the external service permits;
- **Vera / ACL** — no raw downstream Authority/Executor secrets merely because they request actions;
- **migration/admin tooling** — separate schema/administrative credentials unavailable to normal runtime services.

No shared master secret is introduced merely for convenience.

### Initial Windows secret provider

The implementation will use a **secret-provider abstraction**. The initial Windows backend uses OS-protected secret storage or an equivalently ACL/DPAPI-protected service-specific secret file/store bound to the trusted service identity.

The exact Windows API/library may be selected during implementation, but plaintext `.env` files, repository files, or broadly readable configuration directories are not the normal production secret store.

Environment variables may be used for ephemeral development bootstrap only when the risk is understood; they are not the long-term design for high-value credentials because child processes, diagnostics, or misconfiguration can expose them.

### Retrieval by reference, not model text

When Vera requests an action, it refers to an opaque target/capability/credential reference. The Effect Executor resolves the actual secret internally after Authority approves the exact operation.

Example:

```text
Vera:       request start_vehicle(vehicle=V1)
Authority:  approve exact operation O123
Executor:   resolve credential_ref internally
            call vehicle service

Vera never receives the password/token.
```

### Rotation and migration

Secret rotation creates a new secret-provider version/reference and updates the consuming service configuration atomically. Knowledge Core/audit may record non-secret rotation metadata but never the prior/new secret values.

The secret-provider interface must allow later migration when Authority/Executor move to another VM/machine. Migration/export of secrets is a privileged human/admin workflow and is not performed by autonomous AI workers.

### Backup and recovery

Secrets are backed up separately from normal Knowledge Core backups using encryption and human-controlled recovery appropriate to their sensitivity. Restore of Knowledge Core data does not automatically restore or expose service credentials.

If a secret cannot be safely backed up, the recovery plan uses credential reissuance/rotation rather than storing an unsafe duplicate.

### Whole-disk encryption is supplementary

Device/volume encryption such as BitLocker is desirable for the host and backup media but does not replace service-level secret separation or ACLs; a running compromised process must still be prevented from reading another service's credentials.

**Reason:** an AI that can retrieve or rewrite the secret behind an authorized adapter can often bypass the intended Authority boundary. Keeping credentials out of knowledge/model context and scoped to the trusted executor/service preserves the distinction between knowing an action exists and possessing the power to perform it.

---

# Open physical-design decisions

1. Detailed PostgreSQL table split for canonical and derived structures.
2. Exact API transport/framework.
3. The first implementation vertical slice and its validation gates.

---

# Documentation workflow

Record accepted decisions here as they are made; supersede rather than silently rewrite. Avoid freezing a deep code/folder skeleton until structural decisions settle. After the major physical-design choices, perform one bounded architecture synthesis covering service boundaries, flows, PostgreSQL schema, artifact storage, security, API, package/folder layout, backup/recovery, build order, and validation gates.

---

# Current next decision

The next design discussion should select the initial service transport/framework. The goal is a typed, easy-to-debug local interface that naturally becomes network-capable later without exposing PostgreSQL or tying Vera/ACL directly to the Knowledge Core implementation.
