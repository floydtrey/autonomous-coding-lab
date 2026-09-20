# Knowledge Core architecture

## Architectural rule

PostgreSQL is canonical. Every external or derived representation is subordinate to canonical KC evidence and policy.

```text
source/client
    |
    v
authenticated consumer / producer boundary
    |
    v
authorization + governance
    |
    +----------------------+
    |                      |
    v                      v
PostgreSQL             immutable artifacts
canonical/control      exact source bytes
    |
    v
governed current source set
    |
    +----------------------+
    |                      |
    v                      v
PostgreSQL lexical     Graph projection
derived index          (optional Graphiti/FalkorDB)
    |                      |
    +----------+-----------+
               |
               v
       unified retrieval evidence
```

## PostgreSQL schemas

KC separates semantic/canonical records, control/governance records, and rebuildable derived data. The exact schema is defined by SQLAlchemy models and Alembic migrations.

Authorization metadata is canonical PostgreSQL state. Graphiti does not contain independent authorization truth.

## Identity

Security identity uses immutable UUID principals. Display names and human-readable principal codes are attributes, not primary security identities.

Credentials authenticate principals. A principal ID is not itself a credential.

## Authorization dimensions

Authorization is intentionally not one numeric permission level. Decisions may depend on:

- principal or group;
- operation;
- active scope;
- resource;
- owner/origin;
- visibility;
- sensitivity;
- time-bounded/revoked grants;
- explicit deny;
- owner-locked classification.

Lifecycle/relevance such as current, completed, failed, superseded, or archived is kept separate from secrecy.

## Canonical knowledge and provenance

Logical Resource identity is distinct from exact ResourceVersion bytes. Source identity, observation/admission evidence, governance decisions, project/context membership, and retrieval snapshots retain distinct meanings.

This prevents content hash, repository path, project label, or provider identity from silently becoming universal knowledge identity.

## Retrieval

Lexical retrieval uses the accepted current text generation and applies resource authorization in the PostgreSQL candidate query before ranking/limit for hardened consumer requests.

Exact-source retrieval reauthorizes the logical Resource before reading immutable artifact bytes.

## Graph projection

Graphiti/FalkorDB is an optional derived relationship projection.

Ordinary project graph partitions include only project-eligible public/scoped non-secret canonical resources. Personal/private and credential/financial material is not promoted into normal project partitions.

A graph result is trusted only when every provider source correlation maps back to current serving KC evidence. Hardened consumer retrieval additionally requires authorization to every correlated logical resource. Authorization is rechecked after the external graph-provider call before data is returned.

Provider/build/validation failure must not roll back or invalidate canonical/lexical state.

## Network surface

The normal hardened service exposes the bounded consumer API. Historical broad semantic/kernel endpoints are not part of the hardened network service.

PostgreSQL, artifact storage, FalkorDB, Graphiti internals, and local model/embedder services are backend infrastructure and must not be exposed as client authority surfaces.

## Extension model

New source producers should implement source-specific verification and emit the generic governed evidence contract.

New graph/vector providers should implement provider-neutral projection interfaces and remain rebuildable.

New clients should use the consumer API and live outside this repository.
