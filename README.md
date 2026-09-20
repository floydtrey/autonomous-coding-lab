# Knowledge Core

Knowledge Core (KC) is a standalone governed knowledge service.

It stores canonical knowledge and provenance, controls who may read or write that knowledge, builds deterministic lexical retrieval state, and optionally maintains validated Graphiti/FalkorDB projections as derived evidence.

KC is designed to be consumed by independent clients such as agent controllers, assistants, applications, importers, or human-facing services. It is not tied to any one agent system.

## What KC owns

KC owns:

- PostgreSQL canonical knowledge, history, identity, provenance, and authorization metadata;
- immutable source artifacts referenced by canonical ResourceVersion records;
- governed source observations, decisions, lifecycle evidence, and source-set snapshots;
- principal identity, service credentials, scopes, groups, grants, and resource access policy;
- canonical direct-note admission and non-canonical memory-candidate staging;
- repository/Git source ingestion as one bounded source producer;
- deterministic SR-2 segmentation and PostgreSQL lexical retrieval;
- provider-neutral projection evidence and validation;
- optional Graphiti/FalkorDB relationship projections derived from authorized KC sources;
- the authenticated `/v1/kc/*` consumer service boundary;
- privacy/restriction/deletion fences for KC-managed evidence and derivatives.

PostgreSQL is canonical truth. Graphiti/FalkorDB, lexical indexes, embeddings, summaries, caches, and other retrieval projections are derived and rebuildable.

## What KC does not own

KC does **not** own:

- agent planning, worker execution, review loops, or task completion;
- application tool permissions or filesystem/process/network authority outside KC;
- browser automation, purchasing, messaging, smart-home actions, or payment authority;
- voice identity, MFA, passkeys, device enrollment, or general-purpose identity-provider duties;
- model loading/routing, harness behavior, or context-window management;
- client-specific integrations such as ACL, Vera, MindsHub/Cowork, or ChatGPT UI behavior;
- a secrets vault for reusable passwords, payment credentials, or API keys.

Those systems authenticate to KC as principals and receive only the knowledge operations/scopes granted to them.

## Trust boundary

```text
client / agent / application
        |
        | authenticated KC credential
        | optional active KC scope
        v
+-------------------------------+
| Knowledge Core consumer API   |
| authentication + authorization|
+-------------------------------+
        |
        +--> PostgreSQL canonical state
        |      + authorization metadata
        |      + governed provenance
        |
        +--> immutable artifact store
        |
        +--> PostgreSQL lexical projection
        |
        +--> Graphiti / FalkorDB (optional derived projection)
```

Clients never receive PostgreSQL, artifact-store, FalkorDB, or model-server credentials.

## Current consumer operations

The hardened consumer surface provides bounded KC operations including:

- status;
- search;
- exact source follow-through;
- authorized canonical note storage;
- non-canonical memory-candidate proposal.

The broad historical semantic/kernel API is not published by the hardened consumer service.

## Requirements

- Python 3.12+
- PostgreSQL
- optional Graphiti/FalkorDB + OpenAI-compatible local model/embedder runtime for graph augmentation

Install development/test dependencies:

```bash
python -m pip install -e ".[test]"
```

Apply migrations:

```bash
python -m alembic upgrade head
```

Run tests:

```bash
python -m pytest -q -m "not postgresql and not sr2_real_pilot"
python -m pytest -q -m "postgresql and not sr2_real_pilot"
```

Run the local service after setting the required environment:

```bash
python tools/kc_bootstrap_service.py
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/BOUNDARY.md](docs/BOUNDARY.md), [docs/OPERATIONS.md](docs/OPERATIONS.md), and [SECURITY.md](SECURITY.md).

## Project status

This repository was extracted from an earlier monorepo after the principal/authentication, authorization, hardened consumer API, and production Graphiti-wiring milestones were sealed and qualified. See [docs/ORIGIN.md](docs/ORIGIN.md) for exact provenance.

The next integration milestone is to issue credentials/grants to real clients. Client-specific role definitions belong in those client repositories, not in KC.
