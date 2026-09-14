# Knowledge Core Retrieval Foundation — RF-2 Completion Record

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**RF-1 design checkpoint:** `bf31baddb8efdc90ce7a1f1f4c6420d7b9f2cd3b`  
**RF-2 validated implementation checkpoint:** `479a918762e919851e19fee3b36cc1d95e78f3e8`  
**GitHub Actions evidence:** run `34371352821` — **success**  
**Status:** **RF-2 complete. Synthetic-first PostgreSQL lexical retrieval is implemented and validated.**

## Scope completed

RF-2 implemented only the synthetic-first retrieval design accepted in `RETRIEVAL_FOUNDATION_RF1.md`.

The implementation adds:

- migration `0009_rf2` with `kc_derived.resource_text_search`;
- PostgreSQL `TSVECTOR` storage plus a GIN full-text index;
- explicit lifecycle and source-authority ranking metadata;
- exact `resource_version_ref` indexing and `generation_source` lineage;
- immutable-artifact integrity verification and strict UTF-8 decoding for `text/plain` and `text/markdown` only;
- PostgreSQL `websearch_to_tsquery('english', ...)`, `@@`, and `ts_rank_cd()` retrieval;
- deterministic lifecycle/authority/revision/ref tie-breaking;
- mandatory service-time `resource_version_serving_eligible()` filtering;
- retrieval-derived row purge when a resource version or logical resource is fenced;
- `POST /v1/retrieval/search` behind the existing `X-Knowledge-Caller` service boundary;
- a controlled PostgreSQL synthetic corpus that exercises RF2-G1 through RF2-G14.

Raw decoded document text is not stored in PostgreSQL. The exact immutable artifact remains the content source; the database stores the rebuildable `tsvector` projection and approved retrieval metadata.

## Exact validation

GitHub Actions run `34371352821` checked out exact commit:

`479a918762e919851e19fee3b36cc1d95e78f3e8`

The workflow provisioned PostgreSQL 18.6 and successfully applied the full Alembic chain:

```text
0001_task1
0002_task2
0003_task3
0004_task4
0005_task5
0006_task6
0007_task8
0008_task9
0009_rf2
```

Validation result:

```text
Fast semantic suite: 47 passed, 9 deselected, 2 upstream warnings
PostgreSQL suite: 9 passed, 47 deselected, 2 upstream warnings
Workflow conclusion: success
```

The PostgreSQL suite now consists of the five previously accepted PostgreSQL qualification tests plus four RF-2 test functions whose assertions cover RF2-G1 through RF2-G14.

The two warnings are upstream FastAPI/Starlette/TestClient deprecation warnings and are not semantic failures. The PostgreSQL log also contains the expected duplicate-operation-key error from the intentional pre-existing same-operation-ID race qualification; that condition is handled by the application and the test passed.

## RF2-G1 through RF2-G14 disposition

- **G1 — Migration/index existence:** passed. `0009_rf2` applied to PostgreSQL and the GIN index exists.
- **G2 — Exact version indexing:** passed. Indexed sources are exact resource-version refs and are recorded in `generation_source`; unsupported media is absent.
- **G3 — Unsupported media exclusion:** passed. Matching bytes in the synthetic PDF do not produce a hit.
- **G4 — Superseded keyword trap:** passed. Default Atlas retrieval returns the explicitly current source; default `amber` does not return the superseded source.
- **G5 — Historical superseded access:** passed. Explicit `include_superseded=true` returns the old Atlas version.
- **G6 — Multiple sources / authority tie-break:** passed. Both CPDM sources return and the stronger explicit authority rank wins the tie.
- **G7 — Stable total order:** passed. The identical tie corpus returns newer canonical revision first across ten repeated queries.
- **G8 — Exact provenance:** passed. Results retain logical resource, exact version, SHA-256 digest, media type, source metadata, and retrieval generation.
- **G9 — Serving fence over stale index:** passed. Normal purge removes the row; a deliberately reintroduced stale derived row still cannot bypass service-time eligibility.
- **G10 — Service-only client:** passed through FastAPI/TestClient plus `X-Knowledge-Caller` only.
- **G11 — Internals hidden:** passed. Retrieval/OpenAPI do not expose database URLs, artifact keys/backends, or artifact-store paths.
- **G12 — Bounded blank/irrelevant behavior:** passed. Blank input is rejected and unrelated text returns no arbitrary fallback matches.
- **G13 — No lifecycle inference:** passed. The superseded Atlas version is deliberately created later than the current version and still remains superseded because fixture classification is explicit.
- **G14 — Current generation only:** passed. A newer settled text generation becomes the sole retrieval generation; old rows remain historical but are not mixed into normal retrieval.

## Frozen boundaries preserved

RF-2 did not modify the canonical meaning of `kc.resource`, `kc.resource_version`, provenance links, Kernel V1 assertion semantics, or the accepted service-only security boundary.

RF-2 also did **not** add:

- real ACL/Vera/RiskCardOCR documents;
- repository-wide import;
- PDF/DOCX/HTML extraction or OCR;
- chunking;
- embeddings/vector search;
- LLM summarization or RAG;
- ACL- or Vera-specific semantic profiles;
- Authority implementation;
- autonomous workers or action execution;
- production deployment/security/backup expansion.

## Remaining retrieval limitations

The accepted RF-2 foundation is deliberately small:

- only PostgreSQL retrieval is supported;
- only strict UTF-8 `text/plain` and `text/markdown` are indexable;
- lifecycle and authority metadata are supplied by the controlled classification/import process rather than inferred;
- search operates at whole-resource-version granularity, not chunks;
- lexical relevance is retrieval rank, not truth, permission, or execution authority;
- the corpus is synthetic only, so real-document messiness remains unqualified.

## Next separately authorized step

Do not begin it from this record alone.

The next sensible retrieval/import slice is a **small curated real-corpus pilot** under the previously documented Knowledge Import Campaign shape. It should begin with bounded inventory/classification and exact provenance/supersession mapping, then ingest only an approved small batch and validate RF-2 behavior against known real-document questions.

That future slice must remain separate from embeddings, RAG, bulk repository import, ACL/Vera semantic expansion, Authority, or execution work unless those are explicitly authorized.

## Stop boundary

**RF-2 is complete. Stop here. Do not ingest real repository documents or begin the next retrieval/import slice without separate authorization.**
