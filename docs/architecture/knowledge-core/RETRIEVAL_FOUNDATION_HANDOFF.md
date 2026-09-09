# Knowledge Core — Retrieval Foundation Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** **RF-1 complete — awaiting separate authorization for RF-2 implementation**  
**Previous completed slice:** Post-Kernel Slice 1 — PostgreSQL Qualification  
**RF-1 design:** `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`

## Purpose

This file is the durable restart point for Retrieval Foundation work. A fresh chat should recover state from the repository rather than relying on prior conversation context.

## Accepted baseline

Knowledge Core Kernel V1 remains frozen and accepted at:

`9e904f49480055615bb0cf32360dbdc8400e117c`

The Kernel acceptance gates 1–19 are complete. Do not reopen or redesign them unless new evidence demonstrates a concrete defect.

Post-Kernel Slice 1 — PostgreSQL Qualification is complete. The validated PostgreSQL qualification implementation checkpoint is:

`2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`

Exact CI evidence: GitHub Actions run `34364589918`.

That qualification proved the real Alembic chain through `0008_task9`, application-layer PostgreSQL use, stale-writer serialization, same-operation-ID contention/replay, advisory-lock blocking, generation late-finisher fencing, and transactional rollback.

Read `CURRENT_STATE.md` and `POSTGRES_QUALIFICATION.md` for the controlling details.

## RF-1 completion

RF-1 — **Retrieval design and falsifiable acceptance plan** — is complete as documentation only.

The controlling RF-1 design is:

`docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`

RF-1 inspected the existing resource/version/provenance schema, migration history, artifact-store boundary, derived-generation machinery, deletion serving fences, application service layer, and HTTP resource routes.

The accepted direction is:

- synthetic-first, not real repository import;
- exact `resource_version_ref` as the retrieval unit;
- PostgreSQL native `tsvector`/GIN lexical retrieval;
- one rebuildable derived lexical projection reusing existing `kc_derived.generation` / `generation_source` lineage;
- explicit lifecycle/current-vs-superseded and source-authority ranking metadata, never inferred from keyword score or recency;
- default exclusion of superseded material with explicit historical access;
- deterministic ranking with stable tie-breaks;
- exact resource/version/digest/generation provenance in every result;
- mandatory reuse of existing resource-version serving eligibility so stale search rows cannot bypass restriction/deletion fences;
- service-only client access through a bounded HTTP retrieval contract;
- a controlled synthetic corpus and RF2-G1 through RF2-G14 as the falsifiable implementation gates.

RF-1 added **no retrieval code, migration, test, real document, embedding, or semantic-domain implementation**.

## Why bulk repository/document import remains deferred

Do **not** copy all ACL, Vera, RiskCardOCR, benchmark, research, or legacy documentation into Knowledge Core yet.

The repository corpus contains a mixture of current authoritative documentation, supporting material, historical records, superseded designs, completed plans, research/evidence, temporary handoffs/debug notes, and duplicates/renames. Indiscriminate ingestion would make retrieval quality impossible to diagnose because contradictory and obsolete sources could be returned as though they were equally authoritative.

A later **Knowledge Import Campaign** will review repositories one at a time, classify documents, preserve exact source provenance, identify supersession/currentness, and ingest only approved material in bounded batches.

That campaign is still **not authorized**.

## Next separately authorized task

### RF-2 — Implement the synthetic-first PostgreSQL lexical retrieval foundation

RF-2 is **not started** and requires separate authorization.

When authorized, RF-2 must implement only the design in `RETRIEVAL_FOUNDATION_RF1.md`, including:

1. the bounded derived lexical migration/model;
2. exact-version text generation/indexing using the existing immutable artifact store;
3. current-generation PostgreSQL full-text query/ranking;
4. service-time resource-version serving eligibility;
5. the bounded normal-client HTTP retrieval contract;
6. deletion/restriction derived-row purge integration;
7. the synthetic PostgreSQL corpus and RF2-G1 through RF2-G14 acceptance gates.

Do not broaden RF-2 into real-document import, format extraction beyond the accepted text media, chunking, embeddings, RAG/summarization, ACL/Vera semantic profiles, Authority, production deployment, or autonomous execution.

## Startup instructions for the next retrieval chat

Before changing code for an authorized RF-2:

1. Work from branch `architecture/knowledge-core`.
2. Read:
   - `docs/architecture/knowledge-core/CURRENT_STATE.md`
   - `docs/architecture/knowledge-core/POSTGRES_QUALIFICATION.md`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_RF1.md`
   - `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
   - `components/knowledge-core/README.md`
3. Verify the current branch/HEAD before any write.
4. Inspect the current exact resource/provenance, generation, deletion-serving, and API code again before implementation so concurrent changes are not overwritten.
5. Preserve the frozen Kernel V1 acceptance boundary.
6. Implement only RF-2 and stop after its documented synthetic acceptance gates and durable checkpoint are complete.

## Explicit non-goals still in force

Do not do any of the following as part of RF-2 unless separately authorized later:

- bulk-import repository documentation;
- review all ACL/Vera/RiskCardOCR documentation;
- build embeddings/vector search;
- add an LLM summarization/RAG layer;
- add ACL-specific semantic profiles;
- add Vera-specific semantic profiles;
- implement Authority;
- add autonomous workers or action execution;
- redesign Kernel V1;
- broaden into production deployment/security/backup work.

## Later import campaign shape

Do not start this now, but preserve this intended decomposition for later:

- repository documentation inventory;
- document classification;
- import-candidate selection;
- provenance/supersession mapping;
- small approved ingest;
- retrieval validation;
- gradual expansion.

The durable state should live in repository files rather than depending on one giant chat context.

## Stop boundary

**RF-1 is complete. Stop here unless RF-2 is separately authorized. Do not implement retrieval, ingest real documents, add embeddings, or begin repository-wide import from this handoff alone.**
