# Knowledge Core Architecture Decision Log

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Component:** Knowledge Core  
**Status:** active decision log; Kernel V1/RF/RI foundations accepted; section retrieval governed by audit-amended SR-1 and KC-D025

---

# Purpose

This file records accepted architecture decisions for Knowledge Core. Detailed design and execution-governance artifacts include:

- `ARCHITECTURE_V1.md`
- `PHYSICAL_SCHEMA_V1.md`
- `IMPLEMENTATION_PLAN_V1.md`
- `EXECUTION_GOVERNANCE.md`
- `SECTION_RETRIEVAL_SR1.md`

The completed Knowledge Architecture Evidence Campaign remains the requirements/evidence base. Physical choices must not weaken it.

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

## KC-D023 — V1 physical database uses canonical, control, and derived PostgreSQL schemas with an atomic-proposition assertion model
**Status:** Accepted
`PHYSICAL_SCHEMA_V1.md` is the current physical-schema candidate. One PostgreSQL database uses `kc` for canonical semantic/history records, `kc_control` for safe operation/idempotency/deletion/backup control, and `kc_derived` for rebuildable current/search/semantic projections. Assertions are normally atomic typed propositions. UUID references identify records; monotonic BIGINT revisions order canonical commits. Exact table/column names remain subject to implementation validation, but the semantic split is accepted.

## KC-D024 — First implementation is a bounded Knowledge Core Kernel validation slice

**Status:** Accepted

The first build follows `IMPLEMENTATION_PLAN_V1.md` and is a kernel validation lab rather than a production Vera/ACL memory deployment.

It includes enough real PostgreSQL, FastAPI/Pydantic, local immutable artifact storage, semantic profile loading, canonical history, projections, identity transitions, provenance, deletion fencing, concurrency/idempotency, and tests to falsify the V1 architecture. It excludes Vera/ACL integration, real Authority/Effect Executor implementation, autonomous workers, embeddings/vector indexes, external graph/vector/search services, full domain profiles, production backup, and UI.

The Kernel V1 slice passed its accepted gates and is frozen. Later bounded work must preserve those invariants unless explicitly superseded here.

---

## KC-D025 — Section structure is content-derived; retrieval lifecycle is governed-snapshot-derived

**Status:** Accepted — 2026-09-10 bounded SR-1 audit amendment

This decision supersedes contradictory section-retrieval wording in the original accepted SR-1 contract and clarifies older RI-1/RI-2 shorthand without invalidating their historical qualification evidence.

### Structural segmentation identity

Structural segmentation is a deterministic projection of exactly:

```text
exact canonical ResourceVersion artifact/media
+ exact structural segmentation profile
```

It determines source-aligned segment boundaries, ordinals, structural kinds, heading paths, byte/line coordinates, exact source-slice digests, and structural segment keys.

Document lifecycle, classification, authority rank, path observation, or later retirement does **not** alter structural segment identity for unchanged canonical bytes under the same structural profile.

### Governed retrieval projection identity

Effective lifecycle, inherited source/ranking annotations, and complete retrieval-generation reproducibility additionally depend on an exact governed observation/classification snapshot and retrieval-projection configuration.

A derived generation must preserve enough immutable lineage to identify the exact governed snapshot set that supplied parent lifecycle, classification, authority, repository/path/source-version annotations, and related governed retrieval metadata. `resource_version_ref` alone is not sufficient for that claim because the same exact canonical bytes may be observed later under different governed metadata.

### Declared versus effective lifecycle

Section declarations are source-derived evidence and remain unchanged with their source coordinates.

Lifecycle restrictiveness is:

```text
current < unknown < superseded
```

Effective lifecycle is the most restrictive value across:

1. governed parent-document lifecycle;
2. all applicable ancestor-section declarations;
3. the section's own declaration.

A less-restrictive child declaration cannot promote the effective lifecycle, but it is not rejected solely for being less restrictive than inherited state. Consequently a later document downgrade, including retirement to `superseded`, can publish a new retrieval projection over the same structural segments without rewriting source evidence or failing structural segmentation.

### Lifecycle-control recognition

The reserved lifecycle control is recognized only through the exact eligible standalone HTML-comment grammar defined by `SECTION_RETRIEVAL_SR1.md`.

Ordinary prose, inline code, Markdown block quotes/quoted explanations, and fenced code containing `kc:retrieval-lifecycle` remain ordinary content.

A standalone non-fenced HTML-comment line beginning with the reserved control prefix is an attempted directive. If malformed, duplicated, or misplaced, lifecycle projection fails explicitly so likely control typos do not silently inherit a permissive lifecycle.

### Exact-version re-observation

`ResourceVersion` remains content-addressed within one logical `Resource`. A previously unseen exact representation creates a version; a later re-observation of bytes matching an existing version reuses that version. Therefore A → B → A reuses A's original exact `ResourceVersion` and, under the same structural profile, A's original structural segment identities. The later event is represented by a new governed observation/receipt/generation, not a duplicate exact version.

### Deterministic size termination

An indivisible ordinary UTF-8 source line, like an indivisible fenced block, cannot be split internally. If it exceeds `hard_max_bytes` with no legal external boundary, structural segmentation fails closed. If the final remaining suffix is at or below hard max, it is emitted whole and splitting terminates.

### Privacy derivative reconciliation

Repository/import supersession and retirement-retain are historical retrieval classification, not privacy deletion.

Privacy `RESTRICT`/`ERASE` fences serving access first for the parent and all children. Derivative cleanup is deterministic/idempotent reconciliation and may occur eagerly. If an exact parent version is actually physically purged/erased, its segment derivatives must not remain. Serving-time parent eligibility remains mandatory defense in depth against stale derivatives.

### Acceptance consequence

The original SR2-G11/G12 semantics are superseded. G12 now proves that declarations cannot promote **effective** lifecycle rather than expecting less-restrictive declarations to fail. G1/G7/G8/G9/G17/G21/G22 are also amended as defined in `SECTION_RETRIEVAL_SR1.md`.

The pre-audit SR-2 candidate `2c48a0e73c560fad62028776f375c94162e138be` is not an accepted SR-2 checkpoint and must be aligned to the amended contract before qualification.

**Reason:** these rules keep canonical source structure stable, preserve governed temporal/classification history, allow safe retirement without source rewrites, make self-documenting technical files valid inputs, preserve content-addressed identity, and retain privacy anti-resurrection guarantees without conflating historical supersession with erasure.

---

# Open physical-design decisions

No new broad physical-design decision is authorized by KC-D025. SR-2 may choose the smallest physical fields/lineage representation needed to satisfy the amended contract, but a material architecture departure must return here before implementation.

---

# Documentation and execution workflow

All future bounded Knowledge Core tasks must follow `EXECUTION_GOVERNANCE.md`. Documentation/checkpoint capacity remains part of the task budget.

For SR-2 specifically, `CURRENT_STATE.md`, KC-D025, and audit-amended `SECTION_RETRIEVAL_SR1.md` must be read before the pre-audit implementation or tests are treated as guidance.

---

# Current next task

**SR-2 contract-alignment implementation — paused until documentation correction is checkpointed.**

The existing pre-audit SR-2 candidate is intentionally not accepted. When implementation resumes, compare it against amended SR2-G1 through G22 and make only the bounded changes required to conform. Do not broaden into embeddings, RAG, Authority, execution, broad corpus import, or unrelated deployment work.