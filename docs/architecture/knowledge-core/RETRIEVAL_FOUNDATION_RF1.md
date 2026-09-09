# Knowledge Core Retrieval Foundation — RF-1 Design and Falsifiable Acceptance Plan

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**RF-1 inspection baseline HEAD:** `4ae900277a48b93e83a3b267718fa35cc601e4a7`  
**Status:** **RF-1 complete — design/acceptance only; no retrieval implementation is authorized by this document.**

## Purpose

RF-1 defines the smallest PostgreSQL-native lexical/full-text retrieval foundation that fits the accepted Knowledge Core architecture and can be falsified with a controlled synthetic corpus before any real repository import begins.

The design must answer one bounded question:

> Given a query, which stored Knowledge Core resource versions are relevant, and exactly which logical resource, exact version, source metadata, and derived retrieval generation produced each result?

This document deliberately does not implement retrieval, ingest real project documentation, add embeddings, add RAG/summarization, or reopen the frozen Kernel V1 boundary.

## Controlling baseline inspected

RF-1 inspected the required restart/state documents plus the existing retrieval-relevant implementation:

- `docs/architecture/knowledge-core/CURRENT_STATE.md`
- `docs/architecture/knowledge-core/POSTGRES_QUALIFICATION.md`
- `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
- `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
- `docs/architecture/knowledge-core/DECISIONS.md`
- `components/knowledge-core/README.md`
- `knowledge_core/storage/resource_models.py`
- migration `0004_task4_resource_provenance.py`
- `knowledge_core/domain/resources.py`
- `knowledge_core/application/resources.py`
- `knowledge_core/application/resource_service.py`
- `knowledge_core/application/deletion.py`
- `knowledge_core/storage/generation_models.py`
- `knowledge_core/api/resource_schemas.py`
- `knowledge_core/api/app.py`
- Task 4 and Task 10 resource/provenance tests.

The inspection confirms that retrieval should extend existing resource/provenance and derived-generation machinery rather than invent a parallel canonical document system.

## Existing architecture that RF-2 must reuse

### Exact resource identity already exists

`kc.resource` is the logical resource identity. `kc.resource_version` is the exact immutable version identity and is unique per logical resource plus content digest. The artifact bytes remain outside PostgreSQL in the immutable SHA-256 artifact store.

Retrieval results must therefore be keyed to **`resource_version_ref`**, not merely `resource_ref`, path, filename, or a mutable locator.

### Provenance already survives version changes

`kc.resource_locator` records locator history against a logical resource and, when known, an exact resource version. `kc.provenance_link` can pin downstream claims to exact resource versions. Existing tests prove that later bytes at the same mutable path do not rewrite earlier evidence provenance.

Retrieval must preserve this behavior: a result from version A may never silently become version B because a path later changed.

### Derived data already has a lifecycle

`kc_derived.generation` and `kc_derived.generation_source` already provide generation identity, source-revision high water, source refs, config/model lineage, one-current-generation fencing, stale/superseded states, and late-finisher protection.

The lexical index should be a **rebuildable derived projection** and use this machinery. It is not canonical truth.

### Serving fences already exist

`resource_version_serving_eligible()` rejects a resource version when either the version itself or its logical resource is restricted/erased/fenced. Existing resource HTTP routes enforce this service-side policy.

Retrieval must use the same serving eligibility. A stale search row must never re-expose a resource version after a privacy/restriction fence.

### Normal clients are already service-only

The accepted API requires `X-Knowledge-Caller` and exposes semantic HTTP routes without database credentials, artifact-store paths, `artifact_key`, or `artifact_backend` details. Retrieval must follow the same boundary.

## RF-1 design decisions

### 1. Retrieval unit

The initial lexical retrieval unit is **one exact `ResourceVersion`**.

A search hit must always retain:

- logical `resource_ref`;
- exact `resource_version_ref`;
- exact content digest and digest algorithm;
- media type;
- source observation/creation provenance available from the resource version;
- explicit retrieval source metadata used for lifecycle/ranking;
- the derived retrieval `generation_id` that produced the hit.

The logical resource groups versions; it is not sufficient provenance by itself.

### 2. What gets indexed in RF-2

RF-2 should index only deliberately supported, exact text resource versions:

- `text/plain`, strict UTF-8;
- `text/markdown`, strict UTF-8.

The index input is the exact immutable artifact addressed by the selected `ResourceVersion`. The server reads it through the artifact store, whose existing `read_bytes()` integrity check verifies the SHA-256 content address before text is indexed.

Both current and superseded text versions may be present in the derived index. Historical preservation is intentional; default serving policy decides whether superseded material participates in an ordinary query.

### 3. What does not get indexed in RF-2

RF-2 must not index:

- PDF, DOCX, HTML, images, OCR output, or arbitrary binary formats;
- assertion values or semantic relationships;
- locator/path text as lexical body content;
- provenance-link labels as lexical body content;
- raw artifact bytes inside PostgreSQL;
- embeddings/vectors;
- generated summaries or LLM output;
- ACL/Vera-specific semantic data;
- repository-wide real documentation.

Unsupported media is simply ineligible for the RF-2 lexical projection. Later extraction/chunking tasks may add bounded format support as separate derived stages.

### 4. PostgreSQL text-search mechanism

Use PostgreSQL native full-text search:

- `to_tsvector('english', <exact decoded text>)` when building the derived projection;
- `websearch_to_tsquery('english', :query)` for the initial query parser;
- `@@` for candidate matching;
- `ts_rank_cd()` for lexical relevance;
- a GIN index over the stored `tsvector`.

The text-search configuration is fixed to `english` for RF-2 and must be represented in the retrieval generation `config_digest` so a later configuration change requires a new derived generation rather than silently reinterpreting an old one.

RF-2 does not store the raw decoded body text in PostgreSQL. PostgreSQL stores the derived `tsvector`; the immutable artifact remains the exact content source.

### 5. Derived table shape

RF-2 should add one derived table, conceptually:

`kc_derived.resource_text_search`

Required columns:

| Column | Purpose |
| --- | --- |
| `generation_id UUID` | FK to `kc_derived.generation`; part of PK. |
| `resource_version_ref UUID` | FK to exact `kc.resource_version`; part of PK. |
| `lifecycle_state VARCHAR(32)` | Explicit source classification for retrieval; `current`, `unknown`, or `superseded`. |
| `authority_rank INTEGER NULL` | Source-authority ranking annotation; lower number means more preferred; NULL means unclassified. This is **not** an authorization decision. |
| `repository TEXT NULL` | Optional approved source repository label for later filtering. |
| `source_path TEXT NULL` | Optional source path/locator label for later filtering/provenance. This is not the artifact-store key. |
| `source_version TEXT NULL` | Optional commit/tag/version label for later filtering/provenance. |
| `observed_at TIMESTAMPTZ NULL` | Optional approved source-observation time for later filtering. |
| `search_vector TSVECTOR` | PostgreSQL lexical projection of the exact supported artifact text. |

Required constraints/indexes:

- primary key `(generation_id, resource_version_ref)`;
- lifecycle check constraint limited to `current`, `unknown`, `superseded`;
- GIN index on `search_vector`;
- B-tree support for `generation_id` and lifecycle/authority filtering as needed by the accepted query plan.

Do **not** duplicate the resource digest, media type, logical resource ID, artifact backend, or artifact key into this table; join those from canonical `kc.resource_version`/`kc.resource` at query time.

### 6. Generation lineage

The lexical projection uses existing `kc_derived.generation` with `derived_kind='text'` for this first bounded slice.

For each indexed exact version, RF-2 also records that `resource_version_ref` in `kc_derived.generation_source` for the generation. `source_revision_highwater` records the canonical revision boundary used to build the generation, and `config_digest` identifies the fixed lexical configuration and projection rules.

A new rebuild creates a new generation. Existing generation settlement/fencing determines which `text` generation is current. Old derived rows remain historical/rebuildable until separately cleaned up; they are not canonical source evidence.

If later work needs independent lifecycle for extracted text versus lexical search, that later task may introduce a more specific derived kind. RF-2 must not broaden into that redesign.

### 7. Lifecycle/currentness is explicit, never inferred from keyword score

RF-2 must not infer `current` or `superseded` from:

- lexical score;
- newest `created_revision_id` alone;
- filename/path;
- locator order;
- content digest;
- the fact that a version was indexed later.

For the synthetic RF-2 corpus, lifecycle metadata is deliberate fixture input. In the later Knowledge Import Campaign, lifecycle must come from the approved document-classification/supersession process or another separately accepted canonical metadata source before indexing.

The derived retrieval row is a ranking/filtering projection of that classification, not the canonical authority for document lifecycle.

### 8. Source authority is ranking metadata, not permission or truth

`authority_rank` is an explicit source-ranking annotation supplied by the controlled fixture/import classification. Smaller values are more preferred. It does not grant execution authority, bypass privacy fences, or convert a source into truth.

This preserves KC-D004/KC-D014: retrieval rank is not permission, and permission is not knowledge.

### 9. Default current/superseded behavior

Initial request behavior:

- `include_superseded=false` by default;
- default queries exclude rows whose `lifecycle_state='superseded'`;
- `current` and `unknown` remain eligible, with `current` preferred to `unknown` when other ranking dimensions tie;
- `include_superseded=true` is an explicit historical/diagnostic mode and does not delete or rewrite old evidence.

This makes ordinary retrieval resistant to an obsolete document winning merely because it contains stronger keyword matches while preserving a way to inspect historical material.

### 10. Deterministic ranking

After lexical matching and the default lifecycle filter, results use this total ordering:

1. `ts_rank_cd(search_vector, query)` descending;
2. lifecycle priority: `current`, then `unknown`, then `superseded`;
3. `authority_rank` ascending, NULL last;
4. canonical `resource_version.created_revision_id` descending;
5. `resource_version.ref_id` ascending as the final stable tie-break.

The service returns the lexical score and lifecycle/authority fields separately. It must not collapse them into a claim of confidence/truth.

Tests should assert exact result order/refs, not an exact floating-point `ts_rank_cd` value.

### 11. Serving eligibility is checked before a result is emitted

Search rows are derived and may become stale between rebuilds. Therefore RF-2 must not trust index membership alone.

Before emitting each candidate, the application layer must call the existing resource-version serving eligibility logic. A restricted/erased/fenced version is omitted even if its old search row still exists.

For the small synthetic RF-2 corpus, the application may retrieve the ordered matching candidate set, apply serving eligibility, and apply `limit` **after** the eligibility pass. This favors semantic correctness over premature optimization. A later scale task may push equivalent eligibility predicates deeper into SQL only if it preserves the same service semantics.

The deletion/restriction purge path should also be extended to remove retrieval-derived rows for a fenced target, but service-time eligibility remains mandatory defense in depth.

## Intended query shape

The intended SQL semantics are approximately:

```sql
WITH q AS (
    SELECT websearch_to_tsquery('english', :query) AS tsq
)
SELECT
    s.generation_id,
    s.resource_version_ref,
    s.lifecycle_state,
    s.authority_rank,
    s.repository,
    s.source_path,
    s.source_version,
    s.observed_at,
    ts_rank_cd(s.search_vector, q.tsq) AS lexical_score,
    rv.resource_ref_id,
    rv.content_digest_algo,
    rv.content_digest,
    rv.media_type,
    rv.observed_occurrence_ref,
    rv.created_revision_id
FROM kc_derived.resource_text_search AS s
JOIN kc_derived.generation AS g
  ON g.generation_id = s.generation_id
JOIN kc.resource_version AS rv
  ON rv.ref_id = s.resource_version_ref
CROSS JOIN q
WHERE g.derived_kind = 'text'
  AND g.status = 'current'
  AND s.search_vector @@ q.tsq
  AND (:include_superseded OR s.lifecycle_state <> 'superseded')
ORDER BY
  lexical_score DESC,
  CASE s.lifecycle_state
    WHEN 'current' THEN 0
    WHEN 'unknown' THEN 1
    ELSE 2
  END ASC,
  s.authority_rank ASC NULLS LAST,
  rv.created_revision_id DESC,
  rv.ref_id ASC;
```

Application-layer serving eligibility is applied to the ordered candidates before the final response limit.

## Service contract

Add one normal-client semantic search route in RF-2:

`POST /v1/retrieval/search`

It uses the existing `X-Knowledge-Caller` boundary and requires no database/artifact credentials.

### Request

```json
{
  "query": "Atlas emergency shutdown token",
  "limit": 10,
  "include_superseded": false
}
```

RF-2 request rules:

- `query` must contain non-whitespace text;
- `limit` default `10`, minimum `1`, maximum `50`;
- `include_superseded` default `false`;
- no arbitrary SQL, table names, raw filters, or artifact-store addresses.

A stop-word-only query may return an empty result set; it need not fall back to substring search.

### Response

Conceptual response:

```json
{
  "query": "Atlas emergency shutdown token",
  "generation_id": "...",
  "source_revision_highwater": 123,
  "results": [
    {
      "rank": 1,
      "resource_ref": "...",
      "resource_version_ref": "...",
      "content_digest_algo": "sha256",
      "content_digest": "...",
      "media_type": "text/markdown",
      "observed_occurrence_ref": "...",
      "created_revision_id": 117,
      "lifecycle_state": "current",
      "authority_rank": 10,
      "repository": "synthetic/ops",
      "source_path": "docs/atlas-runbook.md",
      "source_version": "commit-new",
      "observed_at": null,
      "lexical_score": 0.0
    }
  ]
}
```

The response must not expose:

- `KNOWLEDGE_CORE_DATABASE_URL` or any database credential;
- `artifact_key`;
- `artifact_backend`;
- filesystem location of the immutable artifact store;
- raw SQL;
- raw artifact bytes.

The exact version ref + digest + logical resource ref + retrieval generation + approved source metadata form the initial retrieval provenance contract.

## Synthetic falsification corpus

RF-2 must use a controlled corpus whose expected answers are known before search is implemented. No real ACL/Vera/RiskCardOCR documentation is required.

| Fixture | Lifecycle | Authority | Media | Content / purpose |
| --- | --- | ---: | --- | --- |
| `atlas-old` | superseded | 10 | `text/markdown` | `Atlas emergency shutdown token is amber. Atlas restart requires supervisor acknowledgement.` |
| `atlas-current` | current | 10 | `text/markdown` | `Atlas emergency shutdown token is cedar. Atlas restart requires supervisor acknowledgement.` |
| `cpdm-standard` | current | 5 | `text/plain` | `CPDM calibration window begins thirty minutes before shift start.` |
| `cpdm-notes` | current | 50 | `text/plain` | Same relevant sentence as `cpdm-standard`; proves authority tie-break. |
| `unrelated` | current | 20 | `text/plain` | Unrelated cafeteria/schedule text; proves non-match exclusion. |
| `unsupported-pdf` | current | 1 | `application/pdf` | Bytes deliberately contain the Atlas keywords; proves unsupported media is not silently indexed. |
| `restricted-atlas` | current | 1 | `text/plain` | Atlas keyword match that is indexed, then fenced before retrieval assertions; proves stale derived rows cannot bypass serving fences. |
| `tie-older` | current | 25 | `text/plain` | `Deterministic tie marker echo.` |
| `tie-newer` | current | 25 | `text/plain` | Same text as `tie-older`, ingested later; proves canonical revision tie-break. |

`atlas-old` and `atlas-current` should carry distinct exact version refs/digests and explicit source versions such as `commit-old` / `commit-new`. They may share a logical document/path classification if convenient, but the test must assert the exact returned `resource_version_ref` and digest rather than relying on path identity.

## RF-2 falsifiable acceptance gates

RF-2 is acceptable only if all applicable gates below pass on real PostgreSQL. A failure means the retrieval design/implementation must be repaired before real document ingestion.

### RF2-G1 — Migration/index existence

A fresh PostgreSQL database upgrades through the existing chain plus the new retrieval migration. `kc_derived.resource_text_search` and its PostgreSQL GIN `tsvector` index exist. Existing Kernel/PostgreSQL qualification tests remain green.

### RF2-G2 — Exact version indexing

Each index row references one exact `resource_version_ref`, and each indexed version appears in `generation_source` for the current text generation. No result is keyed only by path or logical resource.

### RF2-G3 — Unsupported media exclusion

`unsupported-pdf` contains matching bytes but produces no lexical hit because RF-2 does not have a PDF extraction path.

### RF2-G4 — Superseded keyword trap

Query `Atlas emergency shutdown token` with default options returns `atlas-current` and does not return `atlas-old`.

Query `amber` with default options returns no result even though the superseded document is an exact keyword match.

### RF2-G5 — Historical superseded access is explicit

The same `amber` query with `include_superseded=true` returns `atlas-old`. Historical evidence therefore remains inspectable rather than being destroyed.

### RF2-G6 — Multiple relevant sources and authority tie-break

Query `CPDM calibration window` returns both `cpdm-standard` and `cpdm-notes`, with `cpdm-standard` first because the lexical/lifecycle conditions tie and its explicit authority rank is stronger.

### RF2-G7 — Stable total order

Query `Deterministic tie marker echo` returns `tie-newer` before `tie-older` by the documented canonical revision tie-break. Repeating the same query at least ten times against the same current generation yields the same ordered version-ref list.

### RF2-G8 — Exact provenance in the response

For `atlas-current`, the result contains the expected logical resource ref, exact version ref, exact SHA-256 digest, media type, lifecycle metadata, approved source version/path metadata, and the current retrieval generation ID. It never substitutes the old version's digest/ref.

### RF2-G9 — Serving fence overrides stale index membership

`restricted-atlas` is indexed and then fenced through the existing deletion/restriction mechanism without first rebuilding the lexical generation. Retrieval must omit it. The stale search row may exist physically, but it is not serving-eligible.

### RF2-G10 — Service-only client

A simulated normal client can perform retrieval with only HTTP/TestClient transport plus `X-Knowledge-Caller`. The client has no SQLAlchemy session, DB URL, artifact-store object/path, or direct repository object.

### RF2-G11 — Secret/storage internals remain hidden

The retrieval response and OpenAPI schema contain no database URL/credential, `artifact_key`, `artifact_backend`, or artifact-store filesystem path.

### RF2-G12 — Blank/irrelevant behavior is bounded

Whitespace-only query input is rejected by request validation. An unrelated query returns an empty result list rather than arbitrary fallback matches.

### RF2-G13 — No lifecycle inference from recency/keywords

The fixture classification explicitly supplies lifecycle state. The implementation must not rewrite lifecycle based on a later-created row, stronger lexical score, or mutable path observation. Test setup should include at least one ordering condition that would fail if the implementation silently used “latest wins” instead of the supplied lifecycle classification.

### RF2-G14 — Generation identity is observable and current-only

Search responses identify the current `text` generation. If a newer text generation is settled current, normal retrieval uses that generation rather than mixing rows from old/stale/superseded generations.

## Required RF-2 implementation changes identified by RF-1

The next implementation task is expected to require only the bounded changes below:

1. a new Alembic migration after `0008_task9` for the derived lexical table/constraints/GIN index;
2. a SQLAlchemy storage model for the derived lexical row, including PostgreSQL `TSVECTOR` handling;
3. an application-layer generation builder for controlled text resource versions using the existing artifact store and existing generation/generation-source lifecycle;
4. an application-layer lexical query that selects only the current text generation, applies the documented deterministic rank, rechecks resource-version serving eligibility, and limits after eligibility;
5. Pydantic request/response schemas for the bounded retrieval contract;
6. `POST /v1/retrieval/search` using the existing caller context and service-only boundary;
7. deletion/restriction derived-row purge support for retrieval while retaining mandatory service-time eligibility checks;
8. PostgreSQL synthetic acceptance tests implementing RF2-G1 through RF2-G14.

RF-2 should not require changes to the frozen canonical `resource` / `resource_version` / provenance meaning. If implementation reveals that it does, stop and record the design failure instead of silently broadening the schema.

## Explicit RF-1 non-goals preserved

RF-1 does not authorize:

- retrieval implementation;
- real-document import;
- repository-wide documentation review;
- PDF/DOCX/HTML extraction;
- chunking;
- embeddings/vector search;
- LLM summarization/RAG;
- ACL-specific semantic profiles;
- Vera-specific semantic profiles;
- Authority implementation;
- autonomous workers/action execution;
- production deployment/security/backup expansion;
- redesign of Kernel V1.

## Next separately authorized task

### RF-2 — Implement the synthetic-first PostgreSQL lexical retrieval foundation

When separately authorized, RF-2 should implement only the design and acceptance gates in this document using the synthetic corpus. It should stop after the PostgreSQL lexical/service-only acceptance gates pass and durable state is updated.

Do not begin the Knowledge Import Campaign, curated real-corpus validation, embeddings, or semantic domain expansion in RF-2.

## RF-1 stop boundary

**Stop after committing this design/acceptance document plus the minimal state/handoff updates marking RF-1 complete. No retrieval code, migration, test, or real data changes belong in RF-1.**
