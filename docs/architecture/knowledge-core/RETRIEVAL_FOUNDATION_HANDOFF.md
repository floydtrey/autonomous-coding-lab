# Knowledge Core — Retrieval Foundation Handoff

**Repository:** `floydtrey/autonomous-coding-lab`  
**Branch:** `architecture/knowledge-core`  
**Status:** ready to begin Post-Kernel Slice 2 — Retrieval Foundation  
**Previous completed slice:** Post-Kernel Slice 1 — PostgreSQL Qualification  

## Purpose

This file is the durable restart point for the next chat. The next chat should not rely on prior conversation context; it should recover state from the repository and perform only the bounded retrieval task defined here.

## Accepted baseline

Knowledge Core Kernel V1 remains frozen and accepted at:

`9e904f49480055615bb0cf32360dbdc8400e117c`

The Kernel acceptance gates 1–19 are complete. Do not reopen or redesign them unless new evidence demonstrates a concrete defect.

Post-Kernel Slice 1 — PostgreSQL Qualification is also complete. The validated PostgreSQL qualification implementation checkpoint is:

`2bd9b1b1288c109b89bb60dde1b7f0f4400d1341`

Exact CI evidence: GitHub Actions run `34364589918`.

That qualification proved the real Alembic chain through `0008_task9`, application-layer PostgreSQL use, stale-writer serialization, same-operation-ID contention/replay, advisory-lock blocking, generation late-finisher fencing, and transactional rollback.

Read `CURRENT_STATE.md` and `POSTGRES_QUALIFICATION.md` for the controlling details.

## Why bulk repository/document import is deferred

Do **not** begin by copying all ACL, Vera, RiskCardOCR, benchmark, research, or legacy documentation into Knowledge Core.

The repository corpus contains a mixture of:

- current authoritative documentation;
- current supporting documentation;
- historical records;
- superseded designs;
- completed plans;
- research/evidence;
- temporary handoffs/debug notes;
- duplicate or renamed material.

Indiscriminate ingestion would make retrieval quality impossible to diagnose because contradictory and obsolete sources could be returned as though they were equally authoritative.

A later **Knowledge Import Campaign** will review repositories one at a time, classify documents, preserve exact source provenance, identify supersession/currentness, and ingest only approved material in bounded batches.

That campaign is **not authorized in this slice**.

## Retrieval strategy for this slice

Use a **synthetic-first** corpus.

The first retrieval implementation should operate on deliberately controlled data whose correct answers are known in advance. The synthetic corpus should contain enough conflict to test the difficult cases, for example:

- a current document and an older superseded document that disagree;
- two resources that are both relevant but have different authority/currentness;
- exact resource-version provenance;
- at least one query whose correct answer requires selecting the current source instead of merely matching keywords.

After deterministic retrieval works on synthetic data, a later separately authorized step may introduce a small curated real corpus (roughly tens of documents, not the whole repo) to expose real-world messiness.

## Core objective

Build the smallest deterministic lexical/full-text retrieval foundation that can answer:

> Given a query, which stored Knowledge Core resources are relevant, and exactly which source/version/provenance produced each result?

The first slice should establish retrieval mechanics and validation, not build a complete knowledge-import system.

## Required properties

The retrieval foundation should be designed so that it can eventually support:

1. deterministic lexical/full-text search over PostgreSQL;
2. exact logical-resource and resource-version provenance in every result;
3. service-only client access — normal clients must not need database credentials;
4. current/superseded source handling without destroying historical evidence;
5. stable, testable ranking behavior;
6. later filtering/ranking by source metadata such as lifecycle, authority, repository, path, commit/version, and time;
7. later addition of embeddings/vector retrieval without making vectors the source of canonical truth.

Do not assume all of these must be implemented in the first task. They are design constraints for the direction of travel.

## Explicit non-goals

Do not do any of the following as part of the first Retrieval Foundation task:

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

## Startup instructions for the next chat

Before changing code:

1. Work from branch `architecture/knowledge-core`.
2. Read:
   - `docs/architecture/knowledge-core/CURRENT_STATE.md`
   - `docs/architecture/knowledge-core/POSTGRES_QUALIFICATION.md`
   - `docs/architecture/knowledge-core/RETRIEVAL_FOUNDATION_HANDOFF.md`
   - `docs/architecture/knowledge-core/EXECUTION_GOVERNANCE.md`
   - `components/knowledge-core/README.md`
3. Verify the current branch/HEAD and inspect the existing Knowledge Core resource/provenance models and service boundary before proposing changes.
4. Preserve the frozen Kernel acceptance boundary.
5. Keep the work bounded and stop after the single task below.

## First bounded task

### RF-1 — Retrieval design and falsifiable acceptance plan

**Do not implement retrieval yet.**

Perform only a design/inspection task:

1. Inspect the existing Knowledge Core resource/version/provenance schema, migrations, application layer, and API routes relevant to retrieval.
2. Determine the smallest PostgreSQL-native lexical/full-text design that fits the existing architecture rather than duplicating it.
3. Define the synthetic corpus needed to falsify the design, including at minimum:
   - current vs superseded conflicting sources;
   - multiple relevant sources;
   - exact resource-version provenance;
   - deterministic expected ranking/results.
4. Define the service contract needed for a normal client to query retrieval without database credentials.
5. Identify any schema/index/migration changes that would be required, but do not write them yet.
6. Write the resulting design and acceptance gates to a new durable document under `docs/architecture/knowledge-core/`.
7. Update the handoff/state only enough to identify RF-1 as complete and point to the next separately authorized task.
8. Commit documentation-only changes and stop.

## RF-1 acceptance condition

RF-1 is complete only when another chat/model could read the resulting design and know exactly:

- what gets indexed;
- what does not;
- how resource/version provenance survives retrieval;
- how current vs superseded sources are represented or ranked;
- what SQL/PostgreSQL mechanisms are intended;
- what API contract is intended;
- what synthetic fixtures will prove or falsify the design;
- what the next implementation task is.

No retrieval code should be written during RF-1.

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

**Stop after RF-1 design/acceptance documentation.** Do not proceed to retrieval implementation, real-document ingestion, embeddings, ACL/Vera semantics, or repository-wide import without separate authorization.
