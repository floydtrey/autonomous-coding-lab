# Knowledge Core PostgreSQL Physical Schema V1

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Component:** Knowledge Core  
**Status:** accepted physical-schema architecture candidate; not yet implementation DDL  
**Decision source:** `DECISIONS.md` KC-D001 through KC-D022

---

# Purpose

This document converts the validated conceptual architecture and accepted physical decisions into the first concrete PostgreSQL shape.

It is intentionally **not** an Alembic migration or production SQL script yet. Names, indexes, and a few column splits may change during the first vertical-slice implementation if validation demonstrates a better physical representation, but the semantic boundaries in this document are the current architecture contract.

The physical design must continue to satisfy:

- non-destructive ordinary knowledge history;
- explicit undo/reversal;
- separate world-valid and knowledge-record time;
- conflict preservation;
- typed assertion semantics;
- exact resource-version provenance;
- reversible identity resolution;
- authorization-first retrieval;
- derived-data rebuildability;
- deletion/restriction anti-resurrection;
- stale-write and retry safety;
- Knowledge != Authority != Execution.

---

# High-level PostgreSQL layout

Use one PostgreSQL database with three logical PostgreSQL schemas:

```text
knowledge_core database
|
+-- kc              canonical semantic/history records
|
+-- kc_control      operational/idempotency/deletion/backup control
|
+-- kc_derived      rebuildable current/search/semantic projections
```

This split is physical/operational. It does not create new conceptual primitive families.

## `kc`

Contains the durable semantic/history substrate:

- canonical revision identity;
- universal record references;
- entities;
- assertions and typed values/participants;
- occurrences;
- lifecycle and identity transitions;
- resources, exact versions and locator history;
- provenance/evidence links;
- semantic profiles, revisions and definitions;
- canonical classification/history required to rebuild authorization filters.

Ordinary records in `kc` are append-oriented and not silently overwritten.

## `kc_control`

Contains state required to operate the service safely but which is not itself ordinary world knowledge:

- API operation/idempotency state;
- privacy deletion/restriction cases and anti-resurrection targets;
- backup checkpoint manifests;
- maintenance/rebuild job control where appropriate.

Some control records intentionally outlive erased knowledge because their purpose is to prevent resurrection or prove bounded settlement without retaining erased payload.

## `kc_derived`

Contains data that may be dropped and rebuilt from `kc` plus required model/profile/configuration artifacts:

- current assertion selection;
- current identity-resolution view;
- current classification/eligibility view;
- derived generation metadata;
- text/search materializations;
- chunks/summaries;
- embeddings/vector data;
- inferred relationship closures;
- caches used by retrieval/context construction.

Loss of `kc_derived` must not destroy canonical knowledge.

---

# Identifier strategy

## Stable record references

Addressable record identities use UUIDs, with UUIDv7 preferred for new service-generated identities on PostgreSQL 18.

Reasons:

- globally unique across future processes/machines/imports;
- safe to expose as opaque service references;
- avoids central integer-ID allocation for semantic objects;
- timestamp-ordered UUID generation improves index locality compared with fully random UUIDs;
- identity does not encode domain meaning.

## Canonical revision order

Canonical committed mutations also receive a monotonic PostgreSQL `BIGINT` revision ID.

```text
UUID ref     = "which semantic/control object is this?"
BIGINT rev   = "in what committed Knowledge Core revision did this appear?"
```

Do not use wall-clock timestamps alone as the total canonical order.

---

# `kc` canonical schema

## 1. `kc.revision`

One immutable record per settled canonical mutation transaction.

Candidate fields:

```text
revision_id          BIGINT primary key / generated sequence
operation_id         UUID unique nullable
recorded_at          TIMESTAMPTZ not null
schema_revision      TEXT not null
authority_decision   TEXT/UUID nullable opaque reference
```

Purpose:

- deterministic ordering/replay;
- groups multiple canonical rows committed by one semantic operation;
- gives projections a source high-water mark;
- supports historical-belief cutoffs.

The Authority reference is an opaque audit link, not a stored authorization decision payload unless separately governed.

---

## 2. `kc.knowledge_ref`

Universal physical address registry.

Candidate fields:

```text
ref_id               UUID primary key
ref_kind             governed physical-kind code
created_revision_id  BIGINT -> kc.revision
created_at            TIMESTAMPTZ not null
payload_state         active | restricted | erased_tombstone
```

`ref_kind` examples:

- entity
- assertion
- occurrence
- resource
- resource_version
- semantic_profile
- semantic_profile_revision
- semantic_predicate
- semantic_predicate_revision
- semantic_kind
- semantic_kind_revision
- semantic_role
- semantic_role_revision

The registry does not state truth or semantic equivalence. It lets cross-family foreign keys remain real PostgreSQL foreign keys.

### Erasure behavior

A minimal `knowledge_ref` tombstone may remain after privileged payload erasure when required to:

- keep deletion-control foreign keys valid;
- prevent stale references from silently becoming another object;
- prove that an opaque identity was erased/restricted;
- stop backup resurrection.

The tombstone contains no substantive erased payload.

---

## 3. `kc.entity`

Persistent semantic things.

Candidate fields:

```text
ref_id               UUID PK -> kc.knowledge_ref
kind_revision_ref    UUID -> kc.semantic_kind_revision
created_revision_id  BIGINT -> kc.revision
extension            JSONB nullable, profile-governed
```

Do not put mutable names, email addresses, usernames, locations, device IDs, employers, etc. directly on the entity row as intrinsic identity. Those are assertions/evidence.

An ENTITY row should remain intentionally boring.

---

## 4. `kc.occurrence`

Bounded event/activity/observation/operation anchors.

Candidate fields:

```text
ref_id                UUID PK -> kc.knowledge_ref
kind_revision_ref     UUID -> kc.semantic_kind_revision
happened_at            TIMESTAMPTZ nullable
happened_during        TSTZRANGE nullable
world_time_precision   governed code
created_revision_id    BIGINT -> kc.revision
extension              JSONB nullable, profile-governed
```

Constraints should prevent contradictory temporal shapes unless the profile permits them.

Examples:

- user statement occurrence;
- sensor observation;
- ingestion run;
- model derivation run;
- identity merge decision;
- assertion correction transition;
- deletion reconciliation pass.

---

# Assertions

## Atomic assertion rule

The default physical rule is:

> **One ASSERTION row represents one atomic proposition occurrence under one governed predicate revision.**

Multi-valued properties normally become multiple assertions rather than arrays hidden in a value blob.

Examples:

```text
A1: E-person has_alias "Bob"
A2: E-person has_alias "Robert"
```

not:

```text
A1: aliases = ["Bob", "Robert"]
```

unless the profile explicitly defines an indivisible collection-valued predicate.

N-ary propositions use governed participants/roles rather than opaque JSON serialization.

---

## 5. `kc.assertion`

Candidate fields:

```text
ref_id                  UUID PK -> kc.knowledge_ref
subject_ref_id          UUID -> kc.knowledge_ref
predicate_revision_ref  UUID -> kc.semantic_predicate_revision
profile_revision_ref    UUID -> kc.semantic_profile_revision

value_state             present | explicit_negative | known_no_value |
                        some_value_unknown | not_established

epistemic_basis         stated | observed | imported | configured |
                        inferred | derived | verified | other-governed

valid_during            TSTZRANGE nullable
world_time_precision    governed code

created_revision_id     BIGINT -> kc.revision

extension               JSONB nullable, profile-governed
```

Additional physically explicit fields may be added for applicability/scope once the first semantic profiles prove the reusable dimensions.

### Important

`created_revision_id` gives knowledge-record time through `kc.revision`.

`valid_during` gives world-valid time.

They are independent.

### Conflict

The schema intentionally permits multiple assertions with the same subject/predicate and overlapping valid ranges.

Conflict is represented/evaluated rather than prevented by a uniqueness constraint.

---

## 6. `kc.assertion_value`

Typed value/object storage for assertions whose `value_state` requires a value.

Candidate fields:

```text
assertion_ref_id       UUID PK -> kc.assertion
value_kind             reference | text | numeric | boolean | date |
                       timestamp | bounded_json

reference_value        UUID nullable -> kc.knowledge_ref
text_value             TEXT nullable
numeric_value          NUMERIC nullable
boolean_value          BOOLEAN nullable
date_value             DATE nullable
timestamp_value        TIMESTAMPTZ nullable
json_value             JSONB nullable

unit_term_ref          UUID nullable -> governed semantic term
a_language_tag         TEXT nullable
```

A CHECK constraint ensures exactly one value column matches `value_kind`.

`bounded_json` is allowed only when the applicable predicate/profile explicitly defines/validates that structured value shape. It is not a generic escape hatch.

### Relationship assertions

A direct relationship is an ordinary assertion with `value_kind=reference`.

```text
subject = Robert
predicate = works_for
reference_value = Acme
```

This means relationship semantics remain governed ASSERTION semantics rather than a separate graph truth store.

---

## 7. `kc.assertion_participant`

Optional governed participants for genuinely n-ary propositions.

Candidate fields:

```text
assertion_ref_id       UUID -> kc.assertion
role_revision_ref      UUID -> kc.semantic_role_revision
participant_ref_id     UUID -> kc.knowledge_ref
ordinal                INTEGER nullable
PRIMARY KEY (assertion_ref_id, role_revision_ref, participant_ref_id, ordinal)
```

Example:

```text
Alice gave Book to Bob

subject = Alice
predicate = gave
value/reference = Book
participant(role=recipient) = Bob
```

Do not use participants for ordinary binary relationships unnecessarily.

---

# Assertion lifecycle

## 8. `kc.assertion_transition`

Lifecycle-changing relationship among assertions, physically anchored by an OCCURRENCE.

Candidate fields:

```text
occurrence_ref_id       UUID PK -> kc.occurrence
transition_type         supersedes | corrects | invalidates | restores
source_assertion_ref    UUID -> kc.assertion
replacement_assertion_ref UUID nullable -> kc.assertion
reverses_transition_ref UUID nullable -> kc.assertion_transition
created_revision_id     BIGINT -> kc.revision
extension               JSONB nullable, governed
```

The transition OCCURRENCE carries when/why/by-what-process the change happened and its provenance.

### Why this is separate from provenance

`wasDerivedFrom` explains origin.

`supersedes` changes lifecycle/current selection.

Those are not interchangeable edges.

### Contradiction

A contradiction that does not itself invalidate either assertion can be represented as an ordinary governed ASSERTION about assertion references, rather than forcing every conflict into lifecycle state.

---

# Identity resolution

## 9. `kc.identity_transition`

Subtype of OCCURRENCE for current identity-resolution changes.

Candidate fields:

```text
occurrence_ref_id       UUID PK -> kc.occurrence
transition_type         resolve_same | resolve_different | merge |
                        split | replace | reassign_identifier
reverses_transition_ref UUID nullable -> kc.identity_transition
created_revision_id     BIGINT -> kc.revision
extension               JSONB nullable, governed
```

## 10. `kc.identity_transition_member`

Candidate fields:

```text
transition_ref_id       UUID -> kc.identity_transition
entity_ref_id           UUID -> kc.entity
member_role             source | member | representative | old | new |
                        split_member | governed-other
ordinal                 INTEGER nullable
PRIMARY KEY (...)
```

No merge physically rewrites every assertion foreign key.

The current identity view is derived in `kc_derived`.

---

# Provenance/evidence

## 11. `kc.provenance_link`

Candidate fields:

```text
link_id                 UUID primary key
relation_revision_ref   UUID -> governed provenance predicate/relation definition
source_ref_id           UUID -> kc.knowledge_ref
target_ref_id           UUID -> kc.knowledge_ref
activity_occurrence_ref UUID nullable -> kc.occurrence
created_revision_id     BIGINT -> kc.revision
extension               JSONB nullable, governed
```

Required indexes:

- `(source_ref_id, relation_revision_ref)`
- `(target_ref_id, relation_revision_ref)`
- activity occurrence

This supports both backward explanation and forward impact traversal.

Mutable sources must normally enter lineage through an exact RESOURCE VERSION ref, not only logical resource/URL/path.

---

# Resources

## 12. `kc.resource`

Logical information/artifact identity.

Candidate fields:

```text
ref_id                UUID PK -> kc.knowledge_ref
kind_revision_ref     UUID -> kc.semantic_kind_revision
created_revision_id   BIGINT -> kc.revision
extension             JSONB nullable, profile-governed
```

Logical resource examples:

- a document that receives revisions;
- a repository;
- a web resource;
- a dataset;
- a configuration artifact.

---

## 13. `kc.resource_version`

Exact observed representation/content version.

Candidate fields:

```text
ref_id                 UUID PK -> kc.knowledge_ref
resource_ref_id        UUID -> kc.resource
content_digest_algo    TEXT not null
content_digest         BYTEA/TEXT not null
byte_size              BIGINT nullable
media_type             TEXT nullable
artifact_backend       TEXT nullable
artifact_key           TEXT nullable
observed_occurrence_ref UUID nullable -> kc.occurrence
created_revision_id    BIGINT -> kc.revision
extension              JSONB nullable, governed
```

Candidate uniqueness:

```text
UNIQUE(resource_ref_id, content_digest_algo, content_digest)
```

Do **not** globally merge logical resources merely because digest matches.

`artifact_key` is a locator to the immutable content-addressed storage backend; it is not semantic identity.

---

## 14. `kc.resource_locator`

Historical mutable locators/aliases for resources or versions.

Candidate fields:

```text
locator_id             UUID primary key
resource_ref_id        UUID -> kc.resource
resource_version_ref   UUID nullable -> kc.resource_version
locator_kind           path | url | git_ref | mailbox_locator | governed-other
locator_text           TEXT not null
valid_during           TSTZRANGE nullable
created_revision_id    BIGINT -> kc.revision
observed_occurrence_ref UUID nullable -> kc.occurrence
extension              JSONB nullable, governed
```

A Git branch such as `main`, a URL, or a filesystem path is therefore historical locator information rather than exact artifact identity.

---

# Semantic profiles/vocabulary

## 15. `kc.semantic_profile`

Logical profile identity.

Candidate fields:

```text
ref_id               UUID PK -> kc.knowledge_ref
stable_name          TEXT unique
created_revision_id  BIGINT -> kc.revision
```

Examples:

- core
- acl
- vera-household
- research
- software

---

## 16. `kc.semantic_profile_revision`

Immutable exact profile snapshot.

Candidate fields:

```text
ref_id                  UUID PK -> kc.knowledge_ref
profile_ref_id          UUID -> kc.semantic_profile
version_label           TEXT
manifest_digest         BYTEA/TEXT nullable
created_revision_id     BIGINT -> kc.revision
extension_schema        JSONB nullable
status                  active-capable | deprecated | retired-for-new-use
```

An "active for new writes" pointer is operational/current configuration, not a rewrite of old assertions.

Profile dependency/import rows must pin exact revision refs.

---

## 17. `kc.semantic_profile_dependency`

```text
profile_revision_ref    UUID -> kc.semantic_profile_revision
dependency_revision_ref UUID -> kc.semantic_profile_revision
PRIMARY KEY (...)
```

No mutable `latest` dependency.

---

## 18. `kc.semantic_predicate`

Stable semantic predicate identity.

```text
ref_id                UUID PK -> kc.knowledge_ref
profile_ref_id        UUID -> kc.semantic_profile
stable_name           TEXT
created_revision_id   BIGINT -> kc.revision
UNIQUE(profile_ref_id, stable_name)
```

---

## 19. `kc.semantic_predicate_revision`

Exact meaning/validation revision.

Candidate fields:

```text
ref_id                   UUID PK -> kc.knowledge_ref
predicate_ref_id         UUID -> kc.semantic_predicate
profile_revision_ref_id  UUID -> kc.semantic_profile_revision
value_shape              reference | scalar | nary | governed-structured
cardinality              single | set | governed
allows_negative          BOOLEAN
allows_unknown           BOOLEAN
inference_flags          governed typed columns / bounded JSON
validation_schema        JSONB nullable
created_revision_id      BIGINT -> kc.revision
```

Material meaning change creates a new `semantic_predicate` identity, not merely a new revision under the same identity.

---

## 20. `kc.semantic_kind`

Stable kind identity for Entity/Occurrence/Resource/etc.

```text
ref_id                UUID PK -> kc.knowledge_ref
profile_ref_id        UUID -> kc.semantic_profile
stable_name           TEXT
created_revision_id   BIGINT -> kc.revision
```

## 21. `kc.semantic_kind_revision`

```text
ref_id                   UUID PK -> kc.knowledge_ref
kind_ref_id              UUID -> kc.semantic_kind
profile_revision_ref_id  UUID -> kc.semantic_profile_revision
validation_schema        JSONB nullable
created_revision_id      BIGINT -> kc.revision
```

Hierarchy/inheritance, if introduced, is governed/versioned and not inferred from names.

---

## 22. `kc.semantic_role`

Stable n-ary participant role identity.

```text
ref_id                UUID PK -> kc.knowledge_ref
profile_ref_id        UUID -> kc.semantic_profile
stable_name           TEXT
created_revision_id   BIGINT -> kc.revision
```

## 23. `kc.semantic_role_revision`

```text
ref_id                   UUID PK -> kc.knowledge_ref
role_ref_id              UUID -> kc.semantic_role
profile_revision_ref_id  UUID -> kc.semantic_profile_revision
validation_schema        JSONB nullable
created_revision_id      BIGINT -> kc.revision
```

---

# Record classification / retrieval eligibility

Authorization requires a deterministic pre-model eligibility filter. Sensitivity/ownership metadata therefore cannot exist only in prose or vectors.

## 24. `kc.record_classification`

Append-oriented classification history for addressable records.

Candidate fields:

```text
classification_id       UUID primary key
target_ref_id           UUID -> kc.knowledge_ref
owner_scope_ref         TEXT/UUID opaque governed principal/scope reference
sensitivity_class       governed code
purpose_constraints     JSONB nullable, tightly governed
valid_during            TSTZRANGE nullable
created_revision_id     BIGINT -> kc.revision
source_assertion_ref    UUID nullable -> kc.assertion
```

Changing classification appends a new record; it does not destroy classification history.

The fast current filter is derived as `kc_derived.current_classification`.

Authority still decides permission; this table supplies trusted classification inputs.

---

# `kc_control` operational schema

## 25. `kc_control.operation`

Stable idempotency/retry state for semantic API mutations.

Candidate fields:

```text
operation_id            UUID primary key
caller_principal_ref    TEXT/UUID
operation_class         governed code
request_digest          BYTEA/TEXT not null
status                  received | running | committed | failed | conflict
started_at              TIMESTAMPTZ
settled_at              TIMESTAMPTZ nullable
result_revision_id      BIGINT nullable -> kc.revision
error_code              TEXT nullable
response_metadata       JSONB nullable, no secrets
```

Same operation ID + materially different digest is rejected.

---

## 26. `kc_control.deletion_case`

Privileged privacy/restriction lifecycle.

Candidate fields:

```text
case_id                 UUID primary key
operation_id            UUID -> kc_control.operation
action_type             restrict | erase | retention_exception
policy_scope_id         TEXT/UUID
status                  requested | fenced | canonical_pending |
                        derivatives_pending | backup_fenced |
                        settled | blocked | failed
requested_at            TIMESTAMPTZ
settled_at              TIMESTAMPTZ nullable
minimal_metadata        JSONB bounded, no erased payload
```

---

## 27. `kc_control.deletion_target`

```text
case_id                 UUID -> kc_control.deletion_case
target_ref_id           UUID -> kc.knowledge_ref
reconciliation_state    governed state
last_checked_at         TIMESTAMPTZ
PRIMARY KEY(case_id, target_ref_id)
```

The target can remain a minimal erased tombstone in `kc.knowledge_ref` after specialized payload removal.

---

## 28. `kc_control.backup_checkpoint`

Candidate fields:

```text
checkpoint_id              UUID primary key
canonical_revision_highwater BIGINT
postgres_backup_identity   TEXT
artifact_manifest_digest   BYTEA/TEXT
profile_state_digest       BYTEA/TEXT nullable
deletion_control_highwater TEXT/BIGINT
created_at                 TIMESTAMPTZ
verified_at                TIMESTAMPTZ nullable
status                     building | verified | failed
metadata                   JSONB bounded
```

---

# `kc_derived` rebuildable schema

## 29. `kc_derived.generation`

Generation fencing / provenance for derived families.

Candidate fields:

```text
generation_id           UUID primary key
derived_kind            current_state | identity | classification |
                        text | chunks | embeddings | relation_closure | other
source_revision_highwater BIGINT
profile_revision_ref    UUID nullable
model_identity          TEXT nullable
model_version           TEXT nullable
config_digest           BYTEA/TEXT nullable
status                  building | current | stale | failed | superseded |
                        restricted | deletion_pending
created_at              TIMESTAMPTZ
settled_at              TIMESTAMPTZ nullable
supersedes_generation   UUID nullable
```

Only validated settled generations can become current.

---

## 30. `kc_derived.generation_source`

Exact lineage for generations/items when a high-water mark is insufficient.

```text
generation_id           UUID -> kc_derived.generation
source_ref_id           UUID -> kc.knowledge_ref
source_revision_id      BIGINT nullable
PRIMARY KEY (...)
```

---

## 31. `kc_derived.current_assertion`

One row per assertion presently selected as current/applicable under the active selection logic.

Candidate fields:

```text
assertion_ref_id        UUID PK -> kc.assertion
subject_ref_id          UUID -> kc.knowledge_ref
predicate_revision_ref  UUID -> kc.semantic_predicate_revision
conflict_group_id       UUID nullable
source_revision_id      BIGINT
projection_revision_id  BIGINT/UUID
generation_id           UUID nullable
selection_reason        governed code
```

Multiple current rows for the same subject/predicate are permitted when unresolved conflict legitimately remains.

This table is a fast projection, not truth.

---

## 32. `kc_derived.current_identity_member`

```text
entity_ref_id           UUID -> kc.entity
resolution_group_id     UUID
representative_ref_id   UUID -> kc.entity
source_transition_ref   UUID -> kc.identity_transition
source_revision_id      BIGINT
generation_id           UUID nullable
PRIMARY KEY(entity_ref_id, resolution_group_id)
```

Rebuildable from identity transitions.

---

## 33. `kc_derived.current_classification`

Fast pre-model eligibility input.

```text
target_ref_id           UUID primary key -> kc.knowledge_ref
classification_id       UUID -> kc.record_classification
owner_scope_ref         TEXT/UUID
sensitivity_class       governed code
source_revision_id      BIGINT
generation_id           UUID nullable
```

This projection may be updated synchronously with classification writes while remaining rebuildable.

---

## 34. `kc_derived.search_document`

Full-text/search materialization.

Candidate fields:

```text
search_item_id          UUID primary key
source_ref_id           UUID -> kc.knowledge_ref
source_revision_id      BIGINT
generation_id           UUID -> kc_derived.generation
text_content            TEXT
search_vector           TSVECTOR
profile_revision_ref    UUID nullable
status                  current | stale | restricted
```

Index `search_vector` using PostgreSQL full-text indexing.

Do not expose restricted rows even if the text index still physically exists pending reconciliation.

---

## 35. `kc_derived.embedding`

Introduced when semantic retrieval is implemented.

Candidate fields:

```text
embedding_id            UUID primary key
source_ref_id           UUID -> kc.knowledge_ref
source_revision_id      BIGINT
generation_id           UUID -> kc_derived.generation
chunk_ordinal           INTEGER nullable
embedding_model         TEXT
embedding_model_version TEXT
config_digest           BYTEA/TEXT
vector_value            VECTOR(...)  -- pgvector, dimension fixed per generation/table strategy
status                  current | stale | restricted
```

Exact vector table partitioning by model/dimension is deferred to semantic-retrieval implementation.

Embeddings are derived candidate-generation data, never truth.

---

## 36. `kc_derived.relationship_closure`

Optional inferred/path projection, introduced only when traversal workload justifies materialization.

Candidate fields:

```text
closure_id              UUID primary key
subject_ref_id          UUID
predicate_revision_ref  UUID
object_ref_id           UUID
path_length             INTEGER
supporting_assertions   UUID[]/separate support rows
generation_id           UUID
source_revision_id      BIGINT
```

Direct asserted relationship retrieval never silently substitutes closure rows.

---

# Foreign-key / integrity principles

1. Cross-family semantic references use `kc.knowledge_ref`.
2. Specialized tables must enforce that their `ref_id` corresponds to the expected `ref_kind` through migration/service constraints or database enforcement chosen during DDL implementation.
3. Assertion typed values use CHECK constraints so declared `value_kind` agrees with exactly one populated value representation.
4. Exact source lineage uses resource-version refs when a mutable resource was consumed.
5. Profile-dependent records pin immutable semantic revision refs.
6. Canonical append records always identify `created_revision_id`.
7. Current/derived rows identify the canonical revision/generation they represent.
8. No derived table is required to reconstruct canonical history.
9. Deletion fences can operate through the stable `knowledge_ref` even after specialized payload erasure.
10. No canonical uniqueness rule should prevent legitimate conflicting sourced assertions merely because their subject/predicate/time overlap.

---

# Indexing plan — first-pass architecture

Exact indexes will be benchmarked, but V1 should expect:

### `kc.assertion`

- subject + predicate revision
- subject + created revision
- predicate + valid range (GiST where appropriate)
- created revision

### `kc.assertion_value`

- reference values
- common scalar value indexes introduced only when query requirements justify them

### `kc.provenance_link`

- source -> descendants
- target -> sources
- activity occurrence

### `kc.resource_version`

- resource + digest
- digest lookup

### `kc.resource_locator`

- locator kind + normalized locator text
- resource

### semantic tables

- profile + stable name
- profile revision

### current projections

- current assertion subject + predicate
- current classification target/sensitivity/owner scope
- identity member/representative

### full text

- GIN on `TSVECTOR`

### semantic

- pgvector HNSW/IVFFlat choice deferred to actual benchmark/workload; vector index is not required for the first canonical vertical slice.

---

# Transaction boundaries

## Append assertion

One semantic append transaction should normally create:

```text
kc_control.operation        (received/running operational state)
        |
        v
kc.revision                 one committed revision
kc.knowledge_ref            assertion ref
kc.assertion
kc.assertion_value/participants as required
kc.provenance_link(s)       if evidence supplied
kc.record_classification    if required
kc_derived.current_*        synchronous projection update where required
        |
        v
commit
        |
        v
kc_control.operation -> committed/result_revision
```

Operational state may be updated around the transaction, but the canonical semantic rows and required synchronous projections settle atomically.

## Correction/reversal

Creates new assertion/ref when a new proposition is introduced plus an OCCURRENCE + `assertion_transition`. It does not update the old proposition payload to pretend it never existed.

## Resource ingestion

Filesystem commit precedes canonical `resource_version` metadata commit so a crash prefers an orphan blob to a database row pointing at nonexistent bytes.

## Identity merge/split

Creates OCCURRENCE + `identity_transition` + members; does not rewrite every historical assertion row.

---

# What is deliberately not in V1

Do not introduce these until a measured requirement earns them:

- Neo4j as a second canonical store;
- Qdrant as a separate vector service;
- Elasticsearch/OpenSearch;
- Kafka/event bus;
- S3/MinIO service;
- distributed database cluster;
- RDF triple store;
- generic ontology reasoner;
- generic EAV/JSON-everything table;
- database triggers that embed complex domain reasoning impossible to replay/test in service code;
- a table for every Vera/ACL domain concept.

The core is designed so these can later become projections/integrations without replacing canonical semantics.

---

# V1 validation gates before implementation expands

The first DDL/prototype must prove at minimum:

1. a stable entity can receive append-only assertions;
2. reference-valued and scalar-valued assertions enforce type integrity;
3. current projection can be destroyed and rebuilt from canonical records;
4. a correction appends a transition and changes current selection without erasing old state;
5. a reversal restores prior current state while retaining the correction history;
6. world-valid time and record time answer different queries correctly;
7. two conflicting assertions can coexist;
8. provenance reaches an exact resource version;
9. backward explanation and forward impact both work;
10. a stale expected revision is rejected;
11. retrying the same operation ID does not duplicate canonical state;
12. identity merge does not rewrite source assertions and can be reversed;
13. restriction fencing removes data from current/search exposure before cleanup;
14. erasure can leave a minimal ref tombstone without substantive payload;
15. an old backup/fixture cannot become serving state until newer restriction controls are reapplied;
16. a profile revision change does not reinterpret older assertions;
17. a derived generation can be marked stale and replaced without becoming canonical;
18. Vera/ACL-style clients can perform the slice entirely through the service API without database credentials.

Failure of a gate requires correcting the physical model before adding more domain features.

---

# Result

This V1 schema deliberately favors:

- explicit history over destructive convenience;
- typed semantics over blobs;
- PostgreSQL constraints over application-only guesses;
- one canonical store over premature distributed infrastructure;
- projections that can be rebuilt;
- stable references that survive corrections/deletion control;
- service/API boundaries that can later move across machines.

It is now detailed enough to determine the initial package/folder skeleton and first implementation vertical slice without claiming the table names/DDL are immutable forever.
