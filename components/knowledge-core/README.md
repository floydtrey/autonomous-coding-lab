# Knowledge Core

This component contains the frozen Knowledge Core Kernel plus accepted PostgreSQL, lexical-retrieval, governed repository-import, and bounded persistence qualification slices.

## Current state

**Branch:** `architecture/knowledge-core`  
**Frozen Kernel V1:** `9e904f49480055615bb0cf32360dbdc8400e117c`  
**RF-2 lexical retrieval:** `479a918762e919851e19fee3b36cc1d95e78f3e8` — CI `34371352821`  
**RI-2 governed repository import:** `c2aa14ca5429ccaf5149e0a8a4321ae7a440d8ad` — CI `34416061086`  
**RI-3 persistent operational pilot:** `de77c2707b283b9765ebde1a369a8da78a5a847c` — CI `34417659798`  
**Status:** **RI-3 application-process persistence and exact replay are qualified. No broad or production corpus is imported.**

Controlling state is `docs/architecture/knowledge-core/CURRENT_STATE.md`. Detailed RI-3 evidence is in `docs/architecture/knowledge-core/REPOSITORY_IMPORT_RI3.md`.

## Accepted foundation

Kernel V1 remains frozen. RF-2 provides PostgreSQL whole-ResourceVersion lexical retrieval with explicit lifecycle/authority metadata, deterministic ranking, current-generation-only serving, and exact provenance.

RI-2 provides stable governed repository document identity:

```text
(source_repository_key, source_document_key) -> Knowledge Core Resource
```

Manifest V2 is an explicit fail-closed allowlist. The host-configured Git reader accepts only exact listed regular blobs and is qualified for SHA-1 Git repositories. RI-2 covers exact replay, edits, renames, explicit retirements, stale source/state rejection, publication fencing, and exact provenance.

## RI-3 persistent operational pilot

RI-3 changes no production Knowledge Core Python. The fixed manifest `docs/architecture/knowledge-core/RI3_PERSISTENT_PILOT_MANIFEST.json` pins exactly three Knowledge Core Markdown documents to source commit `3e675f0ffb584d6b270e0a7c52428c74a5496be3`: two current sources and the RI-1 design as superseded history.

The PostgreSQL acceptance test runs two separate Python processes against the same database and filesystem-backed `LocalArtifactStore`. Process 1 plans/applies and verifies retrieval, provenance, and three persisted SHA-256 artifacts. Process 2 reconstructs the application, proves the same generation serves before replay, reapplies the exact manifest, and confirms no durable state changes.

Accepted snapshot:

```text
3 document bindings
1 settled import receipt
3 source observations
3 Resources
3 ResourceVersions
3 RF-2 search rows
3 persisted SHA-256 artifact files
```

Exact validation at `de77c2707b283b9765ebde1a369a8da78a5a847c`, run `34417659798`:

```text
PostgreSQL 18
Alembic through 0010_ri2: passed
Fast: 48 passed, 1 expected historical-fixture skip, 18 deselected
PostgreSQL: 16 passed, 2 expected historical-fixture skips, 49 deselected
Workflow: success
```

Knowledge Core CI retains full Git history (`fetch-depth: 0`) because RI-3 intentionally verifies an immutable historical source commit. The importer itself remains limited to manifest-listed exact paths.

## Current boundary

RI-3 proves persistence across application-process reconstruction while the same PostgreSQL database and artifact directory remain intact. It does not qualify database-server restart, machine reboot, store recreation, backup/restore, broad corpus import, automatic discovery/classification, chunking, document extraction, vector retrieval/RAG, or production hosting.

## Development

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
alembic upgrade head
```

Set `KNOWLEDGE_CORE_DATABASE_URL` before applying PostgreSQL migrations.

## Next boundary

The next separately authorized candidate is **RI-4 — local-host persistence/recovery qualification** using another tiny explicitly reviewed manifest and deliberately persistent PostgreSQL/artifact locations on the intended host. It should prove application reconstruction and database/service restart against the same stores, exact replay, retrieval, artifact integrity, and provenance, then stop.
