# Knowledge Core Architecture V1

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** implementation-ready architecture; Kernel implementation not yet started  

Primary supporting documents:

- `DECISIONS.md` — accepted architecture decisions KC-D001 through KC-D024
- `PHYSICAL_SCHEMA_V1.md` — PostgreSQL physical schema candidate
- `IMPLEMENTATION_PLAN_V1.md` — first bounded Kernel build and acceptance gates
- `../../research/knowledge-architecture/` — requirements/evidence campaign

---

# 1. What Knowledge Core is

Knowledge Core is the shared knowledge substrate for Vera, ACL, and future clients.

It is **not Vera's private database** and it is **not ACL's project store**.

It is a standalone local/network-capable service that owns canonical knowledge semantics and exposes a typed semantic API.

```text
                  +------------------+
                  |      Vera        |
                  +---------+--------+
                            |
                            | semantic API
                            |
                  +---------v--------+
                  |  Knowledge Core  |
                  +---------+--------+
                            |
                            | canonical persistence
                            v
                       PostgreSQL

                  +------------------+
                  |       ACL        |
                  +---------+--------+
                            |
                            +-------> same Knowledge Core API
```

Neither Vera nor ACL receives PostgreSQL credentials.

---

# 2. Governing trust rule

```text
KNOWLEDGE != AUTHORITY != EXECUTION
```

Knowledge Core can know that a vehicle exists and that a user often starts it at 04:00.

That does not give Vera permission to start it.

Authority can approve an exact start request.

That approval still does not prove the vehicle actually started.

External effect settlement is recorded separately and can later become observed knowledge.

---

# 3. Service topology

Initial same-PC topology:

```text
WINDOWS HOST
|
|-- Vera / ACL / worker processes
|      low privilege
|      no DB credentials
|      no Authority policy write
|      no Executor secrets
|
|-- Knowledge Core service
|      Python 3.12+
|      FastAPI / Pydantic
|      loopback HTTP/JSON initially
|      PostgreSQL application role
|      artifact-store access
|
|-- PostgreSQL service
|      separate service identity
|      owns canonical database files
|
|-- Authority service
|      separate trusted identity
|      deterministic authorization
|      reads Authority Root
|
|-- Effect Executor
|      separate trusted identity
|      owns downstream action credentials
|
`-- Hardware write-protected Authority Root
       static/slow-changing policy and verification roots
```

Later, Authority or Knowledge Core may move into a VM or another physical machine without redesigning Vera's semantic requests.

---

# 4. What AI-controlled processes cannot do

Normal Vera/ACL/worker processes cannot directly:

- alter Authority Root files;
- replace Authority/Executor binaries;
- read downstream action credentials;
- use PostgreSQL superuser/migration credentials;
- write the Knowledge Core database outside its API;
- modify trusted service install directories;
- run as Administrator/LocalSystem simply for convenience.

Windows service identities/service SIDs and NTFS ACLs provide the initial one-PC isolation boundary.

---

# 5. Canonical versus derived

## Canonical

PostgreSQL owns durable semantic/history records:

```text
Entity
Assertion
Occurrence
Resource / exact version
Evidence / provenance
Semantic profile / vocabulary revision
Identity/lifecycle transitions
Classification history
```

Ordinary learning is non-destructive.

A correction appends a new record/transition.

An undo appends another transition.

History remains recoverable.

## Derived

These may be dropped and rebuilt:

```text
current-state views
identity-resolution current view
classification eligibility view
full-text materialization
chunks
summaries
embeddings
vector indexes
relationship closures
caches
context packages
```

Derived relevance never becomes stronger truth than canonical sources.

---

# 6. PostgreSQL physical zones

One database, three PostgreSQL schemas:

```text
kc
  canonical semantic/history records

kc_control
  operations/idempotency
  deletion/restriction control
  backup checkpoint manifests

kc_derived
  current projections
  search materialization
  embeddings later
  inferred closures/caches
```

Detailed candidate tables are in `PHYSICAL_SCHEMA_V1.md`.

---

# 7. Assertion model

An assertion is normally one atomic proposition occurrence.

```text
Robert --works_for--> Acme
```

is one reference-valued assertion.

```text
Robert --has_name--> "Robert Smith"
```

is one scalar-valued assertion.

Multiple aliases normally use multiple assertions, not an array hidden in JSON.

Core semantic fields are relationally typed.

`JSONB` is limited to profile-governed bounded extensions.

---

# 8. Time model

Knowledge Core stores two independent clocks:

```text
WORLD TIME
When was this true/applicable?

KNOWLEDGE TIME
When did Knowledge Core learn/record it?
```

Example:

```text
May 15   employee actually starts job
June 2   system records an incorrect June 2 start
Sept 8   late correction establishes May 15
```

Current reconstruction can say May 15.

Historical-belief query for July can still show that the system believed June 2 at that time.

The correction never rewrites the earlier record timestamp.

---

# 9. Current knowledge

Current state is a rebuildable projection over canonical history.

It is optimized for questions such as:

```text
Where does Robert work now?
What device is currently in the kitchen?
What preference is currently applicable?
```

The projection may contain multiple competing current assertions when conflict remains unresolved.

Knowledge Core does not manufacture false certainty merely to keep one row per subject/property.

---

# 10. Identity

Stable internal Entity identity is separate from names and external IDs.

```text
Entity E1 != name "Robert Smith"
```

Same-name people can remain ambiguous.

Merge/split/replacement are transitions, not destructive rewrites.

A mistaken merge can be reversed because original entity rows and assertions were never physically collapsed.

Replacement is not equivalence:

```text
old thermostat --replaced_by--> new thermostat
```

The two devices remain distinct historical entities.

---

# 11. Provenance

Knowledge Core can answer both directions:

```text
BACKWARD
Why do we believe this?
What exact source/version/activity produced it?

FORWARD
What depends on this source/version?
What must be rebuilt/restricted/deleted if it changes?
```

Mutable locators such as URLs, paths, branches, or `latest` are not sufficient provenance when exact content matters.

---

# 12. Artifact storage

Large bytes stay outside PostgreSQL.

Initial backend:

```text
local configurable artifact root
`-- sha256/
    `-- content-addressed immutable blobs
```

PostgreSQL stores the logical RESOURCE and exact RESOURCE VERSION metadata.

Identical bytes may deduplicate physically without merging logical identity, ownership, sensitivity, or provenance.

Changed bytes create a new immutable version.

---

# 13. Semantic profiles

The universal core does not contain Vera/ACL-specific tables such as:

```text
HomeAssistantEntity
ACLWorker
GitCommit
EmailThread
```

Instead, domain vocabularies are immutable versioned Semantic Profiles.

Assertions pin the exact profile/predicate revision that gives them meaning.

A later vocabulary release cannot silently reinterpret historical assertions.

---

# 14. Retrieval

Retrieval is a staged pipeline:

```text
1. authenticate caller / purpose
2. Authority + sensitivity eligibility
3. structured filters
4. temporal filters
5. relationship traversal
6. full-text / semantic candidates
7. provenance + conflict + currentness evaluation
8. reranking
9. model-facing context construction
```

Semantic similarity means "possibly relevant," not "true."

Retrieved imperative text remains content and never becomes Authority policy merely because the model saw it.

---

# 15. API

Initial implementation:

```text
Python >=3.12
FastAPI
Pydantic
HTTP/JSON
versioned /v1-style contract
loopback binding by default
```

The API exposes semantic operations, not arbitrary CRUD.

Operation classes include:

- read/search/explain;
- append assertion/occurrence/resource/evidence;
- correction/reversal;
- identity transition;
- privileged restriction/erasure/profile administration.

Clients do not set canonical record timestamps or revisions.

---

# 16. Concurrency and retries

Every semantic mutation has a stable operation/idempotency identity.

If a network timeout occurs after a successful commit, retrying the same operation does not create a duplicate mutation.

State-dependent mutations use optimistic preconditions.

```text
client reads revision 100
another writer commits revision 101
client attempts correction expecting 100
=> STALE / CONFLICT
```

Knowledge Core does not silently overwrite revision 101.

---

# 17. Deletion and restriction

Ordinary correction preserves history.

Privacy erasure is different.

Deletion/restriction lifecycle:

```text
request accepted
   |
   v
immediate retrieval fence
   |
   v
canonical reconciliation
   |
   v
derived/artifact reconciliation
   |
   v
backup/restore fence verification
   |
   v
settled in declared scope
```

A minimal opaque tombstone may remain where necessary to prevent resurrection, but substantive erased payload does not remain merely for audit convenience.

---

# 18. Backup and restore

A valid Knowledge Core backup coordinates:

- PostgreSQL canonical revision;
- referenced immutable artifact blobs;
- semantic-profile interpretability;
- deletion/restriction-control high-water state.

Derived indexes can be rebuilt.

Restore is offline/non-serving until newer deletion/restriction controls are reapplied and integrity checks pass.

```text
restore old snapshot
        |
        v
DO NOT SERVE
        |
apply newer delete/restrict ledger
        |
reconcile / rebuild / validate
        |
        v
activate
```

---

# 19. Secrets

Secrets are not knowledge.

Do not put passwords, API tokens, private keys, device credentials, or Executor credentials in:

- Knowledge Core assertions;
- prompts/context;
- embeddings;
- Git;
- ordinary logs/config.

Each trusted service receives only its own secrets through an OS-protected secret-provider interface.

Vera asks for a capability; Executor resolves the credential internally after Authority approval.

---

# 20. Initial package layout

```text
components/knowledge-core/
├── README.md
├── pyproject.toml
├── alembic.ini
├── knowledge_core/
│   ├── app.py
│   ├── config.py
│   ├── api/
│   ├── application/
│   ├── domain/
│   ├── storage/
│   ├── artifacts/
│   ├── profiles/
│   ├── projections/
│   └── authority/
├── migrations/
├── profiles/
├── scripts/
└── tests/
    ├── unit/
    ├── integration/
    └── acceptance/
```

Detailed responsibilities are in `IMPLEMENTATION_PLAN_V1.md`.

Folders should be created when the Kernel slice actually needs them rather than filling the repo with empty architecture theater.

---

# 21. First implementation slice

The first build is the **Knowledge Core Kernel**.

It proves storage semantics before product/domain features.

It includes:

- real PostgreSQL migrations;
- real FastAPI typed requests;
- real immutable local artifact ingest;
- append-only assertions;
- correction and reversal;
- current-view rebuild;
- bitemporal queries;
- conflict preservation;
- exact-version provenance;
- reversible identity transitions;
- stale-writer/idempotent retry safety;
- deletion/restriction semantic fencing;
- semantic-profile immutability;
- derived-generation fencing.

It deliberately does not include Vera, ACL, real Authority, effects, embeddings, or UI.

---

# 22. Kernel stop gate

`IMPLEMENTATION_PLAN_V1.md` defines 19 acceptance gates.

Do not expand into Vera/ACL domain features until every required Kernel gate passes or an architecture failure is explicitly returned to `DECISIONS.md` and repaired.

---

# 23. Build order

```text
1. component package/config/test harness
2. PostgreSQL fixture + migrations
3. revision/reference/profile foundations
4. entity/assertion typed values
5. current projection/rebuild
6. correction/reversal + bitemporal queries
7. idempotency + stale preconditions
8. resources/artifacts/provenance
9. identity transitions
10. deletion/restriction semantic fence
11. FastAPI semantic routes
12. acceptance replay
13. checkpoint and stop
```

---

# 24. Current boundary

Architecture work is complete enough to implement.

No production code or database migration has been created on this branch yet as part of this synthesis checkpoint.

The next bounded phase is:

> **Knowledge Core Kernel implementation according to `IMPLEMENTATION_PLAN_V1.md`.**

That phase should begin from an explicit implementation-start checkpoint and stop after the Kernel acceptance gates pass or a design failure requires architecture revision.
