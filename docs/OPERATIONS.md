# Knowledge Core operations

## Required service environment

`KNOWLEDGE_CORE_DATABASE_URL` — PostgreSQL SQLAlchemy URL.

`KNOWLEDGE_CORE_ARTIFACT_ROOT` — local artifact root used for exact immutable source bytes.

`KNOWLEDGE_CORE_BOOTSTRAP_KEY` — owner/bootstrap migration credential. Treat this as high privilege and keep it outside source control and prompts.

Optional:

`KNOWLEDGE_CORE_BIND_HOST` — service bind host. Default remains loopback unless explicitly changed.

`KNOWLEDGE_CORE_PORT` — service port.

## Graph runtime

Graph augmentation is opt-in.

`KNOWLEDGE_CORE_GRAPH_ENABLED=true` enables normal-service Graphiti wiring.

Relevant settings include:

- `KNOWLEDGE_CORE_GRAPH_NAMESPACE`
- `KNOWLEDGE_CORE_GRAPH_MAX_SEGMENTS`
- `KNOWLEDGE_CORE_GRAPH_MAX_ATTEMPTS`
- `FALKORDB_HOST`
- `FALKORDB_PORT`
- optional `FALKORDB_USERNAME` / `FALKORDB_PASSWORD`
- `GRAPHITI_OLLAMA_BASE_URL`
- `GRAPHITI_OLLAMA_API_KEY` or `OLLAMA_API_KEY`
- `GRAPHITI_LLM_MODEL`
- `GRAPHITI_LLM_MAX_TOKENS`
- `GRAPHITI_TEMPERATURE`
- `GRAPHITI_EMBED_MODEL`
- `GRAPHITI_EMBED_DIM`

When graph support is disabled, the service remains lexical-only and does not require Graphiti.

## Database migration

```bash
python -m alembic upgrade head
```

Applied migrations are history. Do not rewrite migration semantics to simplify a later design.

## Test tiers

Fast tests:

```bash
python -m pytest -q -m "not postgresql and not sr2_real_pilot"
```

PostgreSQL tests:

```bash
python -m pytest -q -m "postgresql and not sr2_real_pilot"
```

The standalone extraction intentionally does not carry historical monorepo corpus pilots that pin commits/blobs from the former parent repository. Those records remain historical evidence in the source monorepo; new standalone real-corpus qualification should use KC-owned fixtures or standalone-repo commits.

## Starting the service

```bash
python tools/kc_bootstrap_service.py
```

The normal service creates/resolves the durable owner principal and enables the hardened consumer admission layer. Graph runtime construction occurs only when explicitly enabled.

## Deployment rule

External clients receive KC API credentials only.

Do not provide clients with:

- PostgreSQL credentials;
- artifact-root filesystem access;
- FalkorDB credentials;
- Graphiti maintenance access;
- local model/embedder server credentials.

## Public-hosting gate

The consumer authorization path is implemented and PostgreSQL-backed. Raw PostgreSQL Row Level Security with a genuinely restricted non-owner runtime DB role remains a separate defense-in-depth deployment requirement before treating an Internet-hosted installation as fully hardened.

A table-owner PostgreSQL connection can bypass ordinary RLS, so enabling superficial policies under the owner role is not accepted as completion.
