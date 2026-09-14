# Knowledge Core Graphiti Live Adapter V1

**Status:** implementation candidate; repository CI and real-host qualification required before promotion into the public KC API

## Purpose

This gate connects the accepted Knowledge Core projection-attempt and projection-validation ledgers to the **real** local Graphiti stack. It does not introduce a fake graph backend. The intended qualification path is:

```text
current governed SR-2 canonical source
  -> durable KC projection attempt
  -> Graphiti 0.30.2
  -> FalkorDB isolated physical graph
  -> Ollama qwen3.5 9B extraction + nomic embeddings
  -> durable KC provider-source binding evidence
  -> durable KC projection disposition
  -> live deterministic projection validation
  -> Authority admission
  -> real Graphiti search
  -> exact KC source correlation
  -> trusted graph result + canonical provenance
```

PostgreSQL remains canonical. Graphiti remains a rebuildable derived projection and retrieval backend. No Graphiti identifier becomes canonical KC identity.

## Qualified local profile

The live adapter defaults to the already-proven host profile:

- `graphiti-core==0.30.2`
- FalkorDB at `localhost:6379`
- Ollama OpenAI-compatible endpoint `http://localhost:11434/v1`
- LLM alias `graphiti-qwen35-9b-32k`
- maximum generation allowance `12288`
- governed projection policy `governed-document-v1`
- explicit LLM temperature `0.0`
- `reasoning_effort="none"`
- native `json_schema` structured output
- embedding model `nomic-embed-text:latest`
- embedding dimension `768`

The adapter contains the reasoning-disabled `OpenAIGenericClient` specialization. Upstream Graphiti source is not patched.

The policy identity and temperature are configuration-bound and included in the adapter behavioral digest used by qualification evidence. Unknown policy identities fail closed rather than inheriting Graphiti semantic defaults.

For `governed-document-v1`, edge resolution is conservative and deterministic. It consolidates only case/whitespace-normalized exact facts with the same partition, endpoints, and relation, while preserving every active contributing episode ID. Paraphrases and merely similar facts remain separate. The governed path does not call Graphiti's semantic duplicate/contradiction judge, does not submit broad invalidation searches, and clears model-derived `invalid_at` or `expired_at` values before any edge write. Existing retired edges are never revived or reused as active duplicates. KC canonical lifecycle/version state remains the only basis for retirement.

## Source boundary

Graphiti projection can only be built from resource versions that are governed sources of the **current accepted SR-2 text generation**. Before any external call, KC re-reads the immutable artifact and verifies:

1. resource version is serving-eligible;
2. artifact byte size matches canonical metadata;
3. artifact SHA-256 matches the immutable ResourceVersion;
4. segment coordinates remain within the canonical artifact;
5. segment slice SHA-256 matches SR-2 evidence;
6. segment is strict UTF-8;
7. effective lifecycle is not `superseded`.

The projection attempt stores exact ResourceVersion refs and canonical revision IDs. The attempt profile binds the current SR-2 generation and generation config digest.

## Namespace and generation isolation

Logical `namespace_key` and `scope_key` remain KC-owned policy/correlation fields. The Graphiti adapter derives a FalkorDB physical graph name from:

```text
SHA-256(namespace_key || scope_key || current SR-2 projection_profile_id)
```

The generation/profile component intentionally rotates the physical graph when KC publishes a new SR-2 generation. Old derived graph state can remain present without being searched by the new generation. This prevents a stale provider episode from silently becoming current graph context.

The live validator also queries a fresh sibling physical graph without writing a synthetic sentinel. Any result from that empty sibling scope is a namespace-isolation failure.

## Provider-source correlation evidence

Graphiti 0.30.2 treats `add_episode(uuid=...)` as lookup/update of an existing episode. KC therefore does **not** attempt to force a KC-derived UUID into Graphiti. Graphiti mints its normal provider episode UUID and returns it from `add_episode()`.

For every projected canonical segment, KC persists a `kc_control.projection_source_binding` evidence row containing:

- projection attempt ID;
- exact canonical ResourceVersion ref;
- canonical source revision ID;
- SR-2 segment key;
- exact source-slice SHA-256;
- physical provider partition key;
- Graphiti-minted episode UUID.

These rows are operational correlation evidence. The Graphiti UUID is not a KC semantic identity and cannot confer trust by itself.

A `SUCCEEDED` projection receipt is rejected/quarantined unless it contains exactly one provider-source binding for every planned canonical segment, with no reused provider source ID and no wrong physical partition.

Graphiti relationship search results carry their sourcing episode UUIDs. Trusted KC graph retrieval rejects a result unless **every** sourcing episode maps through a validated current provider-source binding and then back to a currently serving exact KC segment. A graph hit with no source episodes, an unknown source episode, a stale ResourceVersion, a superseded segment, or the wrong partition is not returned as trusted context.

## Projection disposition

The adapter preserves Graphiti warning evidence. In particular, the previously observed missing-endpoint warnings:

```text
Target entity not found in nodes for edge relation
Source entity not found in nodes for edge relation
```

cause the projection attempt to settle `INCOMPLETE` rather than `SUCCEEDED`.

An exception after the durable attempt is opened settles the attempt `QUARANTINED`; KC does not automatically replay a pending attempt after an ambiguous process failure because external side effects may already exist.

## Live validation

A successful provider call is still `UNVALIDATED`. `GraphitiProjectionValidator` independently checks:

1. attempt/backend/config/namespace/scope/profile contract;
2. exact durable provider-source binding coverage;
3. known projection-integrity warnings;
4. presence of every bound provider episode in the real Falkor graph;
5. physical namespace isolation using a fresh sibling graph;
6. source attribution on any probe-search results.

Zero probe results do not make the projection untrustworthy by themselves. The host qualification gate separately requires at least one final **trusted** Graphiti result for the selected query before the end-to-end gate passes.

## Authority-first trusted retrieval

`GraphProjectionRetrievalKnowledgeKernel.search_validated_projection()` evaluates `retrieval.search_graph` Authority before sending the query to Graphiti, the embedder, the reranker, or any other projection component. Graph search requires explicit namespace and scope.

Only attempts matching the current SR-2 generation, exact adapter config, `SUCCEEDED` disposition, and `VALIDATED` validation state contribute provider-source bindings. After the external search returns, KC re-checks that the current SR-2 generation did not change during the call.

The existing PostgreSQL lexical retrieval path remains independent and unchanged in this gate.

## Host qualification

Install the optional live dependency from `components/knowledge-core` and apply the new operational-evidence migration:

```powershell
python -m pip install -e ".[test,graphiti]"
python -m alembic upgrade head
```

The tool uses the existing `KNOWLEDGE_CORE_DATABASE_URL` and an existing KC artifact root. It can enumerate the **real sources already in the current SR-2 generation** without touching Graphiti:

```powershell
python tools\graphiti_host_phase.py `
  --artifact-root "<existing KC artifact root>" `
  --list-sources
```

Choose one or more returned source paths and a query grounded in those sources, then run the real path:

```powershell
python tools\graphiti_host_phase.py `
  --artifact-root "<existing KC artifact root>" `
  --source-path "<existing SR-2 source path>" `
  --query "<question grounded in that source>"
```

The tool exits non-zero if projection is incomplete/quarantined, validation is not `VALIDATED`, or the final Authority-gated correlated Graphiti search returns no trusted result.

Exact replay uses the same deterministic KC attempt identity and does not rerun an already-settled projection. `--attempt-salt` exists only as an explicit recovery discriminator after prior evidence has been inspected; changing it creates a new projection attempt and must not be used casually because Graphiti will mint another provider episode for the reissued projection.

## Promotion gate

Do **not** call this V1 accepted merely because repository CI passes. Repository CI can verify the provider-neutral contracts, migrations, and deterministic partition identity without having the user's FalkorDB/Ollama services.

Promotion into the normal/public KC retrieval API requires a real-host PASS showing:

- real Graphiti ingestion;
- real isolated FalkorDB graph;
- durable exact provider-source binding evidence;
- no known integrity warning;
- all bound provider episodes present;
- validation `VALIDATED`;
- Authority admission before graph search;
- at least one trusted graph result;
- exact KC ResourceVersion/segment provenance on that result.

ACL execution remains disabled throughout this gate.
